"""Stage 4: fine-tune a token-classification model for Azerbaijani PII NER.

Terminology note: this is FINE-TUNING (transfer learning) -- starting from
a checkpoint that already has general multilingual language understanding
(FacebookAI/xlm-roberta-large) and continuing
training it, with a new randomly-initialized token-classification head, on
this project's labeled data. Not training from randomly-initialized weights.

Data contract (must match scripts/prepare_splits.py's output exactly):
  <data-dir>/labels.json   (falls back to <data-dir>/../labels.json)
      {"labels": [...], "label2id": {...}, "id2label": {...}}
      55 labels for the current 27-entity taxonomy (v2.0.0).
      Language-independent -- one canonical copy at data/processed/labels.json.
  <data-dir>/{train,val,test}.jsonl
      --data-dir defaults to data/processed/merged (the shuffled union of the
      Azerbaijani split and its EN/TR/RU translations). For an AZ-only run,
      pass --data-dir data/processed/az.
      One row per sliding-window chunk (max_length=512, stride=256):
        {"id": str, "input_ids": [int], "attention_mask": [int],
         "labels": [int]}
      Already tokenized with the xlm-roberta-large fast tokenizer AND the
      punctuation-boundary pre-tokenizer patch from prepare_splits.py -- do
      NOT re-tokenize raw text here, and do NOT point --model at a
      different tokenizer family than whatever produced these files, or
      every offset-derived label is silently wrong. Rows are NOT padded
      (variable length up to 512); padding happens per-batch via
      DataCollatorForTokenClassification. Label id -100 marks special/pad
      tokens, excluded from the loss and from every metric.

Two very different things this script can do, same code path for both:

  --smoke-test
      Tiny real-data slice (64 train / 16 val windows), FORCES
      xlm-roberta-base regardless of --model, a couple of steps, nothing
      real saved. Proves the pipeline itself is correct BEFORE spending
      real time or money -- not a smaller version of training.

      WHY it forces the small model specifically, not just fewer samples:
      full fine-tuning holds the model weights, the gradients (same size
      again), and the AdamW optimizer's own state (two more numbers per
      parameter) all at once -- for xlm-roberta-large's ~560M parameters
      that is ~8.8GB in plain fp32, a fixed floor batch size does NOT
      lower. Verified this is real, not theoretical, twice: this script's
      own smoke test hit a real MPS out-of-memory error on an 8GB M2
      MacBook Air even at this tiny scale; and separately, a colleague's
      draft of this same script that only shrank --max-train-samples
      (kept --model at -large) crashed with the exact same
      "MPS backend out of memory" error on the same machine -- confirmed
      by actually running it, not inferred from reading the code. Shrinking
      sample count alone does not move the weights+gradients+optimizer
      floor; only a smaller model does.

  (no --smoke-test)
      The real run, against whatever --model you point it at, on the full
      split. Needs real GPU memory for anything the size of
      xlm-roberta-large (2026-08-31 measurements show
      why an 8GB machine can't fully fine-tune it, and don't run this
      untuned on such a machine expecting it to work.

Run:
  python model/train.py --smoke-test
  python model/train.py --model FacebookAI/xlm-roberta-large \\
      --output-dir model/checkpoints/xlmr-large --batch-size 32 \\
      --grad-accum 1 --epochs 3 --precision bf16
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------

def _add_punctuation_boundary(tokenizer) -> bool:
    """The same pre-tokenizer patch prepare_splits.py builds the training
    windows with. Imported from there when the repo is present; on a rented
    GPU this file may run on its own (scripts/gpu/run_v3.sh copies only
    train.py), so the identical step is applied inline then: append
    Punctuation() after the existing pre-tokenizer steps."""
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from prepare_splits import add_punctuation_boundary
        return add_punctuation_boundary(tokenizer)
    except ImportError:
        pass
    backend = getattr(tokenizer, "backend_tokenizer", None)
    if backend is None:
        return False
    from tokenizers import pre_tokenizers
    pt, steps = backend.pre_tokenizer, []
    if isinstance(pt, pre_tokenizers.Sequence):
        i = 0
        while True:
            try:
                steps.append(pt[i])
            except Exception:
                break
            i += 1
    elif pt is not None:
        steps = [pt]
    backend.pre_tokenizer = pre_tokenizers.Sequence(steps + [pre_tokenizers.Punctuation()])
    return True


def _labels_path(data_dir: Path) -> Path:
    """labels.json beside the split, else one level up (the canonical,
    language-independent copy at data/processed/labels.json)."""
    here = data_dir / "labels.json"
    return here if here.exists() else data_dir.parent / "labels.json"


def load_labels(data_dir: Path) -> tuple[list[str], dict[str, int], dict[int, str]]:
    d = json.loads(_labels_path(data_dir).read_text(encoding="utf-8"))
    label2id = {k: int(v) for k, v in d["label2id"].items()}
    id2label = {int(k): v for k, v in d["id2label"].items()}
    return d["labels"], label2id, id2label


# ---------------------------------------------------------------------------
# Data loading -- Arrow-backed via `datasets`, not a plain Python list.
# ---------------------------------------------------------------------------

def load_split_datasets(train_file: Path, val_file: Path, test_file: Path | None,
                        num_proc: int):
    """train.jsonl alone is ~428MB (Git LFS) -- `datasets.load_dataset`
    memory-maps it into an Arrow-backed table instead of materializing
    every row as a Python dict, which is the wrong tool for this file size.
    """
    from datasets import load_dataset

    data_files = {"train": str(train_file), "validation": str(val_file)}
    if test_file is not None and test_file.exists():
        data_files["test"] = str(test_file)

    ds = load_dataset("json", data_files=data_files, num_proc=num_proc)

    # DataCollatorForTokenClassification pads model-input keys only
    # (input_ids/attention_mask/labels) -- the "id" string column breaks
    # tensor conversion in the collator, not just gets ignored.
    for split in list(ds.keys()):
        if "id" in ds[split].column_names:
            ds[split] = ds[split].remove_columns(["id"])
    return ds


# ---------------------------------------------------------------------------
# Metrics -- entity-level (seqeval), not token-level
# ---------------------------------------------------------------------------

def _to_tag_sequences(predictions: np.ndarray, label_ids: np.ndarray,
                      id2label: dict[int, str]):
    pred_ids = np.argmax(predictions, axis=-1)
    true_seqs, pred_seqs = [], []
    for pred_row, label_row in zip(pred_ids, label_ids):
        true_seq, pred_seq = [], []
        for p, l in zip(pred_row, label_row):
            if l == -100:
                continue
            true_seq.append(id2label[int(l)])
            pred_seq.append(id2label[int(p)])
        true_seqs.append(true_seq)
        pred_seqs.append(pred_seq)
    return true_seqs, pred_seqs


def build_compute_metrics(id2label: dict[int, str]):
    from seqeval.metrics import accuracy_score, f1_score, precision_score, recall_score

    def compute_metrics(eval_pred) -> dict:
        predictions, label_ids = eval_pred
        true_seqs, pred_seqs = _to_tag_sequences(predictions, label_ids, id2label)
        return {
            "precision": precision_score(true_seqs, pred_seqs),
            "recall": recall_score(true_seqs, pred_seqs),
            "f1": f1_score(true_seqs, pred_seqs),
            "accuracy": accuracy_score(true_seqs, pred_seqs),
        }

    return compute_metrics


def _to_native(obj):
    """seqeval's classification_report(output_dict=True) leaf values are
    numpy float64/int64, not JSON-serializable directly."""
    if isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_native(v) for v in obj]
    if isinstance(obj, np.generic):
        return obj.item()
    return obj


def per_label_report(id2label: dict[int, str], logits: np.ndarray,
                     labels: np.ndarray) -> tuple[str, dict]:
    """Full per-label breakdown, run once against the test set -- not fed
    to the Trainer's own compute_metrics, which runs every eval step; a
    55-label text report every few hundred steps would be noise.
    """
    from seqeval.metrics import classification_report

    true_seqs, pred_seqs = _to_tag_sequences(logits, labels, id2label)
    text = classification_report(true_seqs, pred_seqs, digits=4)
    try:
        as_dict = _to_native(classification_report(true_seqs, pred_seqs,
                                                    digits=4, output_dict=True))
    except TypeError:
        as_dict = None  # older seqeval without output_dict support
    return text, as_dict


# ---------------------------------------------------------------------------
# TrainingArguments across transformers versions
# ---------------------------------------------------------------------------

def build_training_arguments(num_train_windows: int, **kwargs):
    """Builds TrainingArguments defensively against API drift.

    requirements.txt pins transformers>=4.44 with no upper bound, so the
    installed version at run time isn't fixed. Two concrete version-skew
    issues found by actually testing this script against a newer release:
    `evaluation_strategy` was renamed `eval_strategy` in 4.46, and one
    later release dropped `warmup_ratio` entirely (kept only
    `warmup_steps`). Rather than hard-failing on either -- or on some other
    renamed/removed argument in a version not yet tested -- retry with the
    renamed key, or with warmup_ratio converted to an equivalent step
    count, or as a last resort with the offending keyword dropped (falling
    back to that argument's library default) and a warning printed.
    """
    from transformers import TrainingArguments

    def _total_optimizer_steps() -> int:
        per_step = (kwargs.get("per_device_train_batch_size", 8)
                   * kwargs.get("gradient_accumulation_steps", 1))
        steps_per_epoch = max(1, -(-num_train_windows // per_step))  # ceil
        return int(steps_per_epoch * kwargs.get("num_train_epochs", 1))

    for _ in range(20):
        try:
            return TrainingArguments(**kwargs)
        except TypeError as exc:
            msg = str(exc)
            if "eval_strategy" in kwargs and "unexpected keyword argument 'eval_strategy'" in msg:
                kwargs["evaluation_strategy"] = kwargs.pop("eval_strategy")
                continue
            if "warmup_ratio" in kwargs and "unexpected keyword argument 'warmup_ratio'" in msg:
                ratio = kwargs.pop("warmup_ratio")
                steps = round(ratio * _total_optimizer_steps())
                kwargs["warmup_steps"] = steps
                print(f"  note: installed transformers has no warmup_ratio; "
                      f"using warmup_steps={steps} instead "
                      f"(ratio={ratio} x ~{_total_optimizer_steps()} total steps)")
                continue
            m = re.search(r"unexpected keyword argument '(\w+)'", msg)
            if m and m.group(1) in kwargs:
                bad = m.group(1)
                print(f"  warning: installed transformers does not accept "
                      f"'{bad}' -- dropping it, using that argument's "
                      f"library default instead.", file=sys.stderr)
                kwargs.pop(bad)
                continue
            raise
    raise RuntimeError("Could not construct TrainingArguments (repeated fallbacks exhausted)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)

    data = p.add_argument_group("data")
    data.add_argument("--data-dir",
                      default=str(ROOT / "data" / "processed" / "merged"),
                      help="dir holding {train,val,test}.jsonl. Default is the "
                           "multilingual union; use data/processed/az for an "
                           "Azerbaijani-only run.")
    data.add_argument("--skip-test-eval", action="store_true")
    data.add_argument("--num-proc", type=int, default=4,
                      help="parallel workers for the JSONL -> Arrow conversion")

    model_g = p.add_argument_group("model")
    model_g.add_argument("--model", default="FacebookAI/xlm-roberta-large")
    model_g.add_argument("--output-dir", default=str(ROOT / "model" / "checkpoints" / "run"))
    model_g.add_argument("--resume-from-checkpoint", default=None,
                         help="checkpoint dir to resume from, or 'auto' for "
                              "the latest checkpoint already in --output-dir")

    train = p.add_argument_group("training")
    train.add_argument("--epochs", type=float, default=3.0)
    train.add_argument("--batch-size", type=int, default=8)
    train.add_argument("--eval-batch-size", type=int, default=None,
                       help="defaults to --batch-size")
    train.add_argument("--grad-accum", type=int, default=4)
    train.add_argument("--lr", type=float, default=2e-5)
    train.add_argument("--lr-scheduler-type", default="cosine",
                       choices=["linear", "cosine", "cosine_with_restarts",
                               "polynomial", "constant", "constant_with_warmup"])
    train.add_argument("--warmup-ratio", type=float, default=0.1)
    train.add_argument("--weight-decay", type=float, default=0.01)
    train.add_argument("--max-grad-norm", type=float, default=1.0)
    train.add_argument("--label-smoothing-factor", type=float, default=0.0)
    train.add_argument("--seed", type=int, default=42)

    perf = p.add_argument_group("performance")
    perf.add_argument("--precision", choices=["auto", "bf16", "fp16", "fp32"],
                      default="auto",
                      help="'auto' picks bf16 on GPUs that support it, else "
                           "fp16 on CUDA, else fp32. MPS/CPU always fp32 "
                           "regardless -- neither has reliable AMP support here.")
    perf.add_argument("--gradient-checkpointing", dest="gradient_checkpointing",
                      action="store_true", default=True)
    perf.add_argument("--no-gradient-checkpointing", dest="gradient_checkpointing",
                      action="store_false")
    perf.add_argument("--dataloader-num-workers", type=int, default=4)

    sched = p.add_argument_group("evaluation / checkpointing")
    sched.add_argument("--eval-strategy", default="epoch", choices=["epoch", "steps"])
    sched.add_argument("--eval-steps", type=int, default=500)
    sched.add_argument("--save-total-limit", type=int, default=3)
    sched.add_argument("--logging-steps", type=int, default=50)
    sched.add_argument("--early-stopping-patience", type=int, default=3,
                       help="evals with no val-F1 improvement before stopping; "
                            "0 disables early stopping")

    debug = p.add_argument_group("debugging")
    debug.add_argument("--max-train-samples", type=int, default=None)
    debug.add_argument("--max-eval-samples", type=int, default=None)
    debug.add_argument("--report-to", default="none", choices=["none", "wandb"],
                       help="wandb requires `wandb login` (or WANDB_API_KEY "
                            "set) before running -- not handled by this "
                            "script, since it needs a real credential")
    debug.add_argument("--run-name", default=None,
                       help="wandb run name; defaults to the output-dir's name")
    debug.add_argument("--smoke-test", action="store_true",
                       help="tiny real-data slice, forces xlm-roberta-base, "
                            "proves the pipeline runs -- see module docstring")
    debug.add_argument("--smoke-train-n", type=int, default=64)
    debug.add_argument("--smoke-eval-n", type=int, default=16)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    data_dir = Path(args.data_dir)
    train_file, val_file, test_file = (data_dir / "train.jsonl",
                                       data_dir / "val.jsonl",
                                       data_dir / "test.jsonl")
    for name, path in (("train.jsonl", train_file), ("val.jsonl", val_file),
                       ("labels.json", _labels_path(data_dir))):
        if not path.exists():
            print(f"error: {name} not found for --data-dir {data_dir}\n"
                  f"  Run scripts/prepare_splits.py (and, for the merged set, "
                  f"the translation merge step) first.", file=sys.stderr)
            return 1

    import torch
    from transformers import (AutoModelForTokenClassification, AutoTokenizer,
                              DataCollatorForTokenClassification,
                              EarlyStoppingCallback, Trainer, set_seed)

    set_seed(args.seed)
    labels, label2id, id2label = load_labels(data_dir)

    model_name = args.model
    if args.smoke_test:
        model_name = "FacebookAI/xlm-roberta-base"
        print(f"--smoke-test: forcing model={model_name} regardless of --model "
              f"(see module docstring for why)")

    print(f"loading tokenizer + model: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    # 2026-10-14 (v3 root causes, section 1): the training windows were built
    # with prepare_splits.add_punctuation_boundary, so the tokenizer saved with
    # the model must carry the same patch; without it the raw pipeline (track
    # R) feeds token sequences the model never saw at every punctuation mark
    # (v3: benchmark R 89.5 with the plain tokenizer, 93.5 with this one).
    if not _add_punctuation_boundary(tokenizer):
        raise SystemExit("tokenizer has no backend_tokenizer: cannot add the punctuation "
                         "pre-tokenizer the training data was built with")
    model = AutoModelForTokenClassification.from_pretrained(
        model_name, num_labels=len(labels), id2label=id2label, label2id=label2id)

    device = ("cuda" if torch.cuda.is_available()
             else "mps" if torch.backends.mps.is_available()
             else "cpu")
    print(f"device: {device}")

    if args.gradient_checkpointing and not args.smoke_test:
        model.gradient_checkpointing_enable()

    print("loading dataset windows...")
    ds = load_split_datasets(train_file, val_file,
                             None if args.skip_test_eval else test_file,
                             args.num_proc)
    train_ds, eval_ds = ds["train"], ds["validation"]
    test_ds = ds["test"] if "test" in ds else None

    if args.smoke_test:
        train_ds = train_ds.select(range(min(args.smoke_train_n, len(train_ds))))
        eval_ds = eval_ds.select(range(min(args.smoke_eval_n, len(eval_ds))))
        test_ds = None
    else:
        if args.max_train_samples:
            train_ds = train_ds.select(range(min(args.max_train_samples, len(train_ds))))
        if args.max_eval_samples:
            eval_ds = eval_ds.select(range(min(args.max_eval_samples, len(eval_ds))))
            if test_ds is not None:
                test_ds = test_ds.select(range(min(args.max_eval_samples, len(test_ds))))

    print(f"train windows: {len(train_ds):,}   eval windows: {len(eval_ds):,}"
         + (f"   test windows: {len(test_ds):,}" if test_ds is not None else ""))

    collator = DataCollatorForTokenClassification(tokenizer, label_pad_token_id=-100)

    if args.precision == "auto":
        use_bf16 = device == "cuda" and torch.cuda.is_bf16_supported()
        use_fp16 = device == "cuda" and not use_bf16
    else:
        use_bf16 = args.precision == "bf16" and device == "cuda"
        use_fp16 = args.precision == "fp16" and device == "cuda"
    if device != "cuda" and args.precision in ("bf16", "fp16"):
        print(f"note: --precision {args.precision} requested but no CUDA GPU "
              f"detected ({device}) -- training in fp32 instead. Neither MPS "
              f"nor CPU has reliable mixed-precision support here.")
    if device != "cuda" and not args.smoke_test:
        print("warning: no CUDA GPU detected -- training xlm-roberta-large "
              "without one will be extremely slow or may not fit in memory "
              "at all. See module docstring.", file=sys.stderr)

    out_dir = Path(args.output_dir)
    if args.smoke_test:
        out_dir = ROOT / "model" / "checkpoints" / "_smoke_test_scratch"

    eval_strategy = "steps" if args.smoke_test else args.eval_strategy
    ta_kwargs = dict(
        output_dir=str(out_dir),
        num_train_epochs=1 if args.smoke_test else args.epochs,
        max_steps=2 if args.smoke_test else -1,
        per_device_train_batch_size=2 if args.smoke_test else args.batch_size,
        per_device_eval_batch_size=(args.eval_batch_size or args.batch_size),
        gradient_accumulation_steps=1 if args.smoke_test else args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler_type=args.lr_scheduler_type,
        warmup_ratio=args.warmup_ratio,
        weight_decay=args.weight_decay,
        max_grad_norm=args.max_grad_norm,
        label_smoothing_factor=args.label_smoothing_factor,
        eval_strategy=eval_strategy,
        # Must match eval_strategy when load_best_model_at_end=True (a real
        # HF Trainer constraint) -- previously hardcoded to "epoch"
        # unconditionally here, which broke --eval-strategy steps.
        save_strategy="no" if args.smoke_test else eval_strategy,
        save_total_limit=None if args.smoke_test else args.save_total_limit,
        load_best_model_at_end=not args.smoke_test,
        metric_for_best_model="f1" if not args.smoke_test else None,
        greater_is_better=True if not args.smoke_test else None,
        logging_steps=1 if args.smoke_test else args.logging_steps,
        bf16=use_bf16,
        fp16=use_fp16,
        dataloader_num_workers=0 if args.smoke_test else args.dataloader_num_workers,
        report_to="none" if args.smoke_test else args.report_to,
        run_name=((args.run_name or out_dir.name)
                 if (not args.smoke_test and args.report_to == "wandb") else None),
        seed=args.seed,
        remove_unused_columns=False,
    )
    if eval_strategy == "steps" and not args.smoke_test:
        ta_kwargs["eval_steps"] = args.eval_steps
        ta_kwargs["save_steps"] = args.eval_steps
    elif args.smoke_test:
        ta_kwargs["eval_steps"] = 1

    training_args = build_training_arguments(num_train_windows=len(train_ds), **ta_kwargs)

    callbacks = []
    if args.early_stopping_patience > 0 and not args.smoke_test:
        callbacks.append(EarlyStoppingCallback(
            early_stopping_patience=args.early_stopping_patience))

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        data_collator=collator,
        compute_metrics=build_compute_metrics(id2label),
        callbacks=callbacks,
    )

    resume = args.resume_from_checkpoint
    if resume == "auto":
        resume = True  # Trainer resolves this to the latest checkpoint in output_dir

    print("starting training...")
    trainer.train(resume_from_checkpoint=None if args.smoke_test else resume)

    print("\nfinal eval on the val set:")
    metrics = trainer.evaluate()
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    if args.smoke_test:
        print("\nSMOKE TEST PASSED -- pipeline runs end to end on real data.")
        return 0

    final_dir = out_dir / "final"
    trainer.save_model(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))
    (final_dir / "labels.json").write_text(
        json.dumps({"labels": labels, "label2id": label2id, "id2label": id2label},
                  indent=2, ensure_ascii=False),
        encoding="utf-8")
    print(f"\nmodel saved to {final_dir}")

    if test_ds is not None:
        print(f"\nrunning final test-set evaluation ({len(test_ds):,} windows)...")
        pred_output = trainer.predict(test_ds)
        report_text, report_dict = per_label_report(
            id2label, pred_output.predictions, pred_output.label_ids)
        print("\nper-label report (test set):")
        print(report_text)
        (out_dir / "test_classification_report.txt").write_text(report_text, encoding="utf-8")
        if report_dict is not None:
            (out_dir / "test_classification_report.json").write_text(
                json.dumps(report_dict, indent=2), encoding="utf-8")
        print(f"\nwrote test_classification_report.{{txt,json}} to {out_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
