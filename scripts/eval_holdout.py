"""Standard held-out dataset evaluation for your-hf-org/masking-multilingual.

Companion to (NOT a replacement for) scripts/redteam/'s adversarial
harness: that harness hand-builds edge-case stress tests and does not
represent typical-case performance. This script instead measures the
model against real held-out documents -- data/processed/<lang>/test.docs.jsonl
-- that were never seen during training (see model/train.py's docstring:
train/val/test are prepare_splits.py's held-out split, not this script's
concern to re-derive).

Methodology (matches model/train.py's own validation-metric approach,
confirmed by reading it before writing this script):
  * Metric library: seqeval, entity-level (BIO-scheme-aware), not raw
    token-accuracy -- same as model/train.py's build_compute_metrics /
    per_label_report.
  * Alignment: the model's own tokenizer, called with
    return_offsets_mapping=True, split into CONSECUTIVE NON-OVERLAPPING
    windows of up to 512 tokens (tokenizer's return_overflowing_tokens
    with stride=0). This differs from training's sliding window (stride
    256, overlapping) -- see "Known limitations" in the generated report.
    Gold entities (character-offset spans from the corpus) are converted
    to one BIO tag per token by character-range overlap with that token's
    offset (first overlapping token of an entity = B-, the rest = I-).
    Predicted tags are the model's own per-token argmax, decoded through
    its own id2label. Both tag sequences, built the same way, are what
    seqeval actually compares.
  * data/golden/ was investigated and is NOT used here: it is a frozen,
    deliberately-defective regression corpus for the data-generation/
    translation pipeline (
    scripts/test_100k_readiness.py check 10.x) -- not a held-out set for
    model evaluation, has no `tr` file, and scoring the model against its
    known-wrong labels would corrupt precision/recall.

Every number `--report` prints is re-derivable from `eval_results.jsonl`
alone (plus the model's own tokenizer, itself a versioned deterministic
artifact) -- it stores each sampled document's id/lang/text/gold
entities/predicted entities, not just the score.

Run:
    export HF_TOKEN="<token>"
    python scripts/eval_holdout.py --run --per-lang 200
    python scripts/eval_holdout.py --report
"""

from __future__ import annotations

import argparse
import collections
import datetime
import json
import os
import random
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "processed"
OUT_DIR = ROOT / "scripts" / "eval_holdout_out"
RESULTS_PATH = OUT_DIR / "eval_results.jsonl"
CHECKPOINT_PATH = OUT_DIR / "checkpoint.json"
REPORT_PATH = ROOT / "docs" / "holdout_eval_results.md"

from piigen.config import ENTITY_TYPES               # noqa: E402

DEFAULT_MODEL = "your-hf-org/masking-multilingual"
LANGS = ["az", "en", "tr", "ru"]
DEFAULT_PER_LANG = 200
DEFAULT_SEED = 20260916
MAX_LENGTH = 512

RISK_TIER = {
    "AZ_FIN": "high", "AZ_ID_CARD_NUMBER": "high", "AZ_PASSPORT_NUMBER": "high",
    "AZ_VOEN": "high", "AZ_DRIVER_LICENSE_NUMBER": "high",
    "PAYMENT_CARD_NUMBER": "high", "IBAN": "high", "CARD_SECURITY_CODE": "high",
    "API_KEY": "high", "ACCESS_TOKEN": "high", "PRIVATE_KEY": "high",
    "EMAIL": "medium", "TELEPHONENUM": "medium", "GIVENNAME": "medium",
    "SURNAME": "medium", "ICCID": "medium", "MAC_ADDRESS": "medium",
    "IPV4_ADDRESS": "medium", "IPV6_ADDRESS": "medium",
    "CITY": "low", "STREET": "low", "BUILDINGNUM": "low", "ZIPCODE": "low",
    "DATE": "low", "TIME": "low", "AGE": "low", "URL": "low",
}


def get_hf_token() -> str:
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("HF_TOKEN is not set in the environment. Export it and re-run:\n"
              '  export HF_TOKEN="<token>"', file=sys.stderr)
        raise SystemExit(1)
    return token


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------
def load_test_docs(lang: str) -> list[dict]:
    path = DATA_DIR / lang / "test.docs.jsonl"
    if not path.exists():
        raise FileNotFoundError(path)
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def sample_docs(rows: list[dict], n: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    k = min(n, len(rows))
    return rng.sample(rows, k)


# --------------------------------------------------------------------------
# Tokenization / alignment
# --------------------------------------------------------------------------
def tokenize_windows(text: str, tokenizer) -> list[dict]:
    """Consecutive non-overlapping windows of up to MAX_LENGTH tokens,
    each carrying its own char offset_mapping. Verified empirically
    (see commit message / investigation notes) to tile the full document
    with contiguous, non-overlapping char ranges."""
    if not text:
        return []
    enc = tokenizer(text, return_offsets_mapping=True, truncation=True,
                    max_length=MAX_LENGTH, stride=0, return_overflowing_tokens=True,
                    padding=False)
    windows = []
    for i in range(len(enc["input_ids"])):
        windows.append({
            "input_ids": enc["input_ids"][i],
            "attention_mask": enc["attention_mask"][i],
            "offsets": enc["offset_mapping"][i],
        })
    return windows


def spans_to_tags(offsets: list[tuple[int, int]], entities: list[dict]) -> list[str]:
    """BIO tag per (non-special) offset, from character-offset entities."""
    tags = ["O"] * len(offsets)
    for ent in entities:
        first = True
        for i, (s, e) in enumerate(offsets):
            if s == e:
                continue
            if s < ent["end"] and e > ent["start"]:
                tags[i] = ("B-" if first else "I-") + ent["label"]
                first = False
    return tags


def tags_to_entities(offsets: list[tuple[int, int]], tags: list[str]) -> list[dict]:
    """Inverse of spans_to_tags -- merges a token-tag sequence back into
    char-offset entities, for the human-readable eval_results.jsonl dump."""
    out = []
    cur_label = cur_start = cur_end = None

    def flush():
        nonlocal cur_label, cur_start, cur_end
        if cur_label is not None:
            out.append({"start": cur_start, "end": cur_end, "label": cur_label})
        cur_label = cur_start = cur_end = None

    for (s, e), tag in zip(offsets, tags):
        if s == e:
            continue
        if tag == "O":
            flush()
            continue
        prefix, label = tag.split("-", 1)
        if prefix == "B" or label != cur_label:
            flush()
            cur_label, cur_start, cur_end = label, s, e
        else:
            cur_end = e
    flush()
    return out


def predict_document(text: str, tokenizer, model, id2label: dict[int, str]):
    """Returns (offsets, pred_tags) concatenated across all non-overlapping
    windows, non-special tokens only, in document order."""
    import torch

    windows = tokenize_windows(text, tokenizer)
    all_offsets: list[tuple[int, int]] = []
    all_tags: list[str] = []
    with torch.no_grad():
        for w in windows:
            input_ids = torch.tensor([w["input_ids"]])
            attn = torch.tensor([w["attention_mask"]])
            logits = model(input_ids=input_ids, attention_mask=attn).logits[0]
            pred_ids = logits.argmax(-1).tolist()
            for (s, e), pid in zip(w["offsets"], pred_ids):
                if s == e:
                    continue
                all_offsets.append((s, e))
                all_tags.append(id2label[pid])
    return all_offsets, all_tags


# --------------------------------------------------------------------------
# Model + schema check
# --------------------------------------------------------------------------
def load_model(model_id: str, token: str):
    from transformers import AutoConfig, AutoModelForTokenClassification, AutoTokenizer

    config = AutoConfig.from_pretrained(model_id, token=token)
    tokenizer = AutoTokenizer.from_pretrained(model_id, token=token)
    model = AutoModelForTokenClassification.from_pretrained(model_id, token=token)
    model.eval()
    revision = getattr(config, "_commit_hash", None) or "unknown"
    id2label = {int(k): v for k, v in config.id2label.items()}
    return tokenizer, model, id2label, revision


def schema_mismatch(id2label: dict[int, str]) -> dict | None:
    model_labels = {v.split("-", 1)[1] for v in id2label.values() if v != "O"}
    expected = set(ENTITY_TYPES)
    missing = sorted(expected - model_labels)
    extra = sorted(model_labels - expected)
    if not missing and not extra:
        return None
    return {"missing": missing, "extra": extra}


# --------------------------------------------------------------------------
# Crash-safe state
# --------------------------------------------------------------------------
def _atomic_write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def load_checkpoint() -> dict:
    if CHECKPOINT_PATH.exists():
        try:
            return json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"completed_ids": [], "model_id": None, "model_revision": None,
            "per_lang": None, "seed": None}


def save_checkpoint(ckpt: dict) -> None:
    _atomic_write_json(CHECKPOINT_PATH, ckpt)


class _JsonlAppender:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(path, "a", encoding="utf-8")

    def append(self, obj: dict) -> None:
        self._fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
        self._fh.flush()
        os.fsync(self._fh.fileno())

    def close(self) -> None:
        self._fh.close()


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# --------------------------------------------------------------------------
# Run
# --------------------------------------------------------------------------
def run_eval(model_id: str, per_lang: int, seed: int) -> None:
    token = get_hf_token()
    print(f"loading {model_id} ...")
    tokenizer, model, id2label, revision = load_model(model_id, token)
    mismatch = schema_mismatch(id2label)
    if mismatch:
        print("SCHEMA MISMATCH -- refusing to score:")
        print(json.dumps(mismatch, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    print(f"id2label matches data/schema.md's {len(ENTITY_TYPES)}-label taxonomy -- OK")

    ckpt = load_checkpoint()
    done = set(ckpt.get("completed_ids", []))
    ckpt.update({"model_id": model_id, "model_revision": revision,
                "per_lang": per_lang, "seed": seed})

    appender = _JsonlAppender(RESULTS_PATH)
    try:
        for lang in LANGS:
            rows = load_test_docs(lang)
            sampled = sample_docs(rows, per_lang, seed)
            print(f"\n{lang}: {len(rows)} records in test.docs.jsonl, "
                 f"sampled {len(sampled)} (seed={seed})")
            for i, rec in enumerate(sampled, 1):
                uid = f"{lang}:{rec['id']}"
                if uid in done:
                    continue
                offsets, pred_tags = predict_document(rec["text"], tokenizer, model, id2label)
                gold_tags = spans_to_tags(offsets, rec["entities"])
                pred_entities = tags_to_entities(offsets, pred_tags)
                appender.append({
                    "uid": uid, "id": rec["id"], "lang": lang,
                    "text": rec["text"],
                    "gold_entities": rec["entities"],
                    "pred_entities": pred_entities,
                    "n_gold": len(rec["entities"]), "n_pred": len(pred_entities),
                    "n_windows": -(-len(offsets) // MAX_LENGTH) if offsets else 0,
                    "timestamp": _now(),
                })
                done.add(uid)
                ckpt["completed_ids"] = sorted(done)
                save_checkpoint(ckpt)
                if i % 20 == 0 or i == len(sampled):
                    print(f"  [{lang} {i}/{len(sampled)}] {uid}")
    finally:
        appender.close()
    print(f"\nDone. Wrote {RESULTS_PATH}")


def self_test(model_id: str) -> None:
    token = get_hf_token()
    tokenizer, model, id2label, revision = load_model(model_id, token)
    mismatch = schema_mismatch(id2label)
    print("SCHEMA MISMATCH" if mismatch else f"id2label OK ({len(id2label)} entries)")
    if mismatch:
        print(json.dumps(mismatch, ensure_ascii=False, indent=2))
        return
    for lang in LANGS:
        rows = load_test_docs(lang)
        rec = next(r for r in rows if r["entities"])
        offsets, pred_tags = predict_document(rec["text"], tokenizer, model, id2label)
        gold_tags = spans_to_tags(offsets, rec["entities"])
        from seqeval.metrics import f1_score
        f1 = f1_score([gold_tags], [pred_tags])
        print(f"  {lang} {rec['id']}: {len(rec['entities'])} gold entities, "
              f"{len(offsets)} tokens, f1={f1:.3f}")


# --------------------------------------------------------------------------
# Report -- recomputes everything from eval_results.jsonl, not from memory
# --------------------------------------------------------------------------
def _load_results() -> list[dict]:
    if not RESULTS_PATH.exists():
        return []
    rows = []
    with open(RESULTS_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _to_native(obj):
    if isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_native(v) for v in obj]
    try:
        import numpy as np
        if isinstance(obj, np.generic):
            return obj.item()
    except ImportError:
        pass
    return obj


def generate_report(model_id: str) -> str:
    from transformers import AutoTokenizer
    from seqeval.metrics import (precision_score, recall_score, f1_score,
                                 classification_report)

    rows = _load_results()
    ckpt = load_checkpoint()
    lines = []
    lines.append(f"# Held-out dataset evaluation -- `{model_id}`")
    lines.append("")
    lines.append(f"Model: `{ckpt.get('model_id') or model_id}` "
                 f"(revision `{ckpt.get('model_revision') or 'unknown'}`). "
                 "Generated from `scripts/eval_holdout_out/eval_results.jsonl` by "
                 "`scripts/eval_holdout.py --report` -- do not hand-edit. Every "
                 "number below is recomputed directly from that file (re-running "
                 "the model's own tokenizer to rebuild BIO tag sequences from "
                 "the stored gold/predicted character-offset entities -- not "
                 "re-run through the model itself), not asserted in prose.")
    lines.append("")
    lines.append("**Companion to, not a replacement for, the adversarial results "
                 "on `redteam/adversarial-eval` (commit `78e8f78`)**: this "
                 "evaluates typical-case performance on real held-out documents "
                 "sampled from `data/processed/<lang>/test.docs.jsonl`; that "
                 "branch hand-builds edge-case stress tests and does not "
                 "represent typical-case performance.")
    lines.append("")

    if not rows:
        lines.append("## Status: no evaluation run yet")
        lines.append("")
        lines.append("Run `python scripts/eval_holdout.py --run --per-lang 200`.")
        return "\n".join(lines) + "\n"

    tokenizer = AutoTokenizer.from_pretrained(model_id, token=get_hf_token())

    by_lang_gold: dict[str, list] = collections.defaultdict(list)
    by_lang_pred: dict[str, list] = collections.defaultdict(list)
    all_gold: list = []
    all_pred: list = []
    lang_counts = collections.Counter()

    for r in rows:
        offsets, _ = tokenize_windows_flat(r["text"], tokenizer)
        gold_tags = spans_to_tags(offsets, r["gold_entities"])
        pred_tags = spans_to_tags(offsets, r["pred_entities"])
        by_lang_gold[r["lang"]].append(gold_tags)
        by_lang_pred[r["lang"]].append(pred_tags)
        all_gold.append(gold_tags)
        all_pred.append(pred_tags)
        lang_counts[r["lang"]] += 1

    lines.append("## Sample sizes")
    lines.append("")
    lines.append(f"- **Sampling seed:** {ckpt.get('seed')}")
    lines.append(f"- **Requested per language:** {ckpt.get('per_lang')}")
    lines.append("")
    lines.append("| Language | Documents evaluated | Total gold entities | "
                 "Total predicted entities |")
    lines.append("|---|---|---|---|")
    for lang in LANGS:
        n_gold = sum(r["n_gold"] for r in rows if r["lang"] == lang)
        n_pred = sum(r["n_pred"] for r in rows if r["lang"] == lang)
        lines.append(f"| {lang} | {lang_counts[lang]} | {n_gold} | {n_pred} |")
    lines.append(f"| **all** | **{len(rows)}** | "
                 f"**{sum(r['n_gold'] for r in rows)}** | "
                 f"**{sum(r['n_pred'] for r in rows)}** |")
    lines.append("")

    lines.append("## Overall (all languages combined)")
    lines.append("")
    lines.append("| Average | Precision | Recall | F1 |")
    lines.append("|---|---|---|---|")
    for avg in ("micro", "macro"):
        p = precision_score(all_gold, all_pred, average=avg, zero_division=0)
        r = recall_score(all_gold, all_pred, average=avg, zero_division=0)
        f = f1_score(all_gold, all_pred, average=avg, zero_division=0)
        lines.append(f"| {avg} | {p:.4f} | {r:.4f} | {f:.4f} |")
    lines.append("")

    lines.append("## Per-language (micro-averaged across that language's labels)")
    lines.append("")
    lines.append("| Language | Precision | Recall | F1 |")
    lines.append("|---|---|---|---|")
    for lang in LANGS:
        if not by_lang_gold[lang]:
            continue
        p = precision_score(by_lang_gold[lang], by_lang_pred[lang], zero_division=0)
        r = recall_score(by_lang_gold[lang], by_lang_pred[lang], zero_division=0)
        f = f1_score(by_lang_gold[lang], by_lang_pred[lang], zero_division=0)
        lines.append(f"| {lang} | {p:.4f} | {r:.4f} | {f:.4f} |")
    lines.append("")

    lines.append("## Per-label (all languages combined)")
    lines.append("")
    report_dict = _to_native(classification_report(all_gold, all_pred, output_dict=True,
                                                    zero_division=0))
    lines.append("| Label | Risk | Precision | Recall | F1 | Support |")
    lines.append("|---|---|---|---|---|---|")
    label_rows = {k: v for k, v in report_dict.items()
                 if k not in ("micro avg", "macro avg", "weighted avg")}
    for label in sorted(label_rows):
        m = label_rows[label]
        lines.append(f"| {label} | {RISK_TIER.get(label, 'n/a')} | "
                     f"{m['precision']:.4f} | {m['recall']:.4f} | {m['f1-score']:.4f} | "
                     f"{int(m['support'])} |")
    lines.append("")

    missing_labels = sorted(set(ENTITY_TYPES) - set(label_rows))
    if missing_labels:
        lines.append(f"*No gold instance of these labels appeared in the sample "
                     f"(precision/recall undefined, not zero): "
                     f"{', '.join(missing_labels)}.*")
        lines.append("")

    # -- comparison to Task 8's adversarial findings -----------------------
    lines.append("## Comparison to the adversarial (Task 8) findings")
    lines.append("")
    lines.append("Task 8's headline finding (`redteam/adversarial-eval`, commit "
                 "`78e8f78`): 24/29 `partial_span` failures were the model "
                 "over-capturing by exactly one trailing character (usually "
                 "sentence-final punctuation), across 13 labels. seqeval's "
                 "entity-level scoring here is EXACT-MATCH on both boundaries, "
                 "so that exact bug -- if it occurs at the same rate on typical "
                 "held-out text as it did in Task 8's short, punctuation-adjacent "
                 "stress sentences -- would show up here as reduced precision "
                 "(over-wide predicted spans) rather than reduced recall (the "
                 "entity is still found, just not exactly bounded), concentrated "
                 "on the same labels Task 8 flagged "
                 "(AZ_DRIVER_LICENSE_NUMBER, AZ_ID_CARD_NUMBER, "
                 "AZ_PASSPORT_NUMBER, IBAN, CARD_SECURITY_CODE, ICCID, AGE, "
                 "BUILDINGNUM, DATE, TELEPHONENUM, IPV6_ADDRESS, URL, ZIPCODE).")
    lines.append("")
    task8_labels = ["AZ_DRIVER_LICENSE_NUMBER", "AZ_ID_CARD_NUMBER",
                    "AZ_PASSPORT_NUMBER", "IBAN", "CARD_SECURITY_CODE", "ICCID",
                    "AGE", "BUILDINGNUM", "DATE", "TELEPHONENUM", "IPV6_ADDRESS",
                    "URL", "ZIPCODE"]
    lines.append("| Label (flagged by Task 8) | Precision here | Recall here | "
                 "Support |")
    lines.append("|---|---|---|---|")
    for label in task8_labels:
        m = label_rows.get(label)
        if m is None:
            lines.append(f"| {label} | *(no instances in this sample)* | -- | 0 |")
            continue
        lines.append(f"| {label} | {m['precision']:.4f} | {m['recall']:.4f} | "
                     f"{int(m['support'])} |")
    lines.append("")
    lines.append("*(A precision score here noticeably below that label's recall "
                 "would be consistent with Task 8's boundary bug generalizing to "
                 "typical held-out text; support=0 means this sample happened to "
                 "contain no gold instance of that label and this comparison is "
                 "inconclusive for it, not evidence either way.)*")
    lines.append("")

    lines.append("## Known methodology limitations")
    lines.append("")
    lines.append("- **Sampled, not exhaustive.** `test.docs.jsonl` holds "
                 f"{{az: 10540, en: 10485, tr: 10380, ru: 10237}} held-out "
                 f"documents; running the full corpus through the model on CPU "
                 f"was impractical, so a fixed-seed random sample "
                 f"(`--per-lang {ckpt.get('per_lang')}`, seed `{ckpt.get('seed')}`) "
                 "was used instead. Re-running with the same seed and "
                 "`--per-lang` reproduces the identical sample.")
    lines.append("- **Non-overlapping windows, not sliding.** Documents longer "
                 "than 512 tokens are split into consecutive non-overlapping "
                 "chunks (see module docstring), unlike training's overlapping "
                 "stride-256 windows. An entity that straddles a window boundary "
                 "loses its `I-` continuation across that boundary and is scored "
                 "as two shorter spans instead of one -- a real, disclosed source "
                 "of undercounted recall on long documents, not hidden by "
                 "sampling only short ones.")
    lines.append("- **`data/golden/` was investigated and deliberately excluded** "
                 "-- it is a frozen regression corpus for the data-generation/"
                 "translation pipeline with known, intentionally-uncorrected "
                 "defects, has no "
                 "`tr` file, and is not a held-out set for model evaluation.")
    return "\n".join(lines) + "\n"


def tokenize_windows_flat(text: str, tokenizer) -> tuple[list[tuple[int, int]], None]:
    """Same windowing as predict_document, offsets only (report-time reuse,
    no model needed)."""
    offsets: list[tuple[int, int]] = []
    for w in tokenize_windows(text, tokenizer):
        for s, e in w["offsets"]:
            if s != e:
                offsets.append((s, e))
    return offsets, None


def write_report(model_id: str) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(generate_report(model_id), encoding="utf-8")
    print(f"wrote {REPORT_PATH}")


# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--per-lang", type=int, default=DEFAULT_PER_LANG)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = ap.parse_args()

    if args.report:
        write_report(args.model)
        return 0
    if args.self_test:
        self_test(args.model)
        return 0
    if args.run:
        run_eval(args.model, args.per_lang, args.seed)
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
