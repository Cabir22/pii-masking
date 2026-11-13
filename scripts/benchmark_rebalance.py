# -*- coding: utf-8 -*-
"""Benchmark the rebalanced model (trained on merged_rebalanced -- 60/40
native/foreign name substitution) against the original production model
(trained with AZ-only names), on the same held-out test set.

Both models are scored with the identical entity-level exact-span
precision/recall/F1, per label, over data/processed/merged_rebalanced/
test.docs.jsonl. GIVENNAME/SURNAME get a second cut, split by whether the
document rolled "native" or "foreign" names -- that split is the actual
point of this benchmark: did rebalancing improve foreign-name recall
without regressing native-name recall?

Native/foreign per document is NOT re-guessed from the name text (that
would require reversing the substitution's transliteration). It is read
back from audit_substitution.replay_native_flags(), which replays the exact
RNG stream substitute_names.py used -- already built and verified by the
teammate who did the rebalancing (2026-09-10). Reusing
it here instead of reimplementing name-origin detection.

Usage:
    # 1. Sanity-check data alignment only, no model calls, seconds to run:
    python scripts/benchmark_rebalance.py --dry-run

    # 2. Fast pass on a sample once both models are wired up:
    python scripts/benchmark_rebalance.py \
        --rebalanced-model model/checkpoints/run/final --n 300

    # 3. Full test set for the final numbers:
    python scripts/benchmark_rebalance.py \
        --rebalanced-model model/checkpoints/run/final --n 0 \
        --out reports/benchmark_rebalance.md
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "model"))

from audit_substitution import replay_native_flags  # noqa: E402

ORIG_DIR = ROOT / "data" / "processed" / "merged_original"
REBAL_DIR = ROOT / "data" / "processed" / "merged_rebalanced"
RUN_ORDER = ["train", "val", "test"]  # order substitute_names.py processed splits
NAME_LABELS = {"GIVENNAME", "SURNAME"}


def load_docs(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def entity_spans(doc: dict) -> set[tuple[str, int, int]]:
    out = set()
    for e in doc.get("entities", doc.get("labels", [])):
        label = e.get("label") or e.get("type")
        s, en = e.get("start"), e.get("end")
        if label is not None and s is not None and en is not None:
            out.add((label, s, en))
    return out


def pred_spans(preds: list[dict]) -> set[tuple[str, int, int]]:
    out = set()
    for p in preds:
        out.add((p["label"], p["start"], p["end"]))
    return out


def prf1(gold: set, pred: set) -> tuple[float, float, float, int, int, int]:
    tp = len(gold & pred)
    fp = len(pred - gold)
    fn = len(gold - pred)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1, tp, fp, fn


# Bucket keys that are diagnostic cuts (native/foreign), not real taxonomy
# labels -- excluded from micro/macro/weighted averages so they don't
# double-count spans already covered by the GIVENNAME/SURNAME rows.
_EXTRA_BUCKET_PREFIX = "GIVENNAME+SURNAME/"


class Scoreboard:
    """Accumulates gold/pred spans per bucket (label, or a custom key like
    'GIVENNAME+SURNAME/native'), then reports P/R/F1 per bucket at the end."""

    def __init__(self):
        self.gold: dict[str, set] = defaultdict(set)
        self.pred: dict[str, set] = defaultdict(set)
        self._counter = 0

    def add_doc(self, doc_idx: int, gold_spans: set[tuple[str, int, int]],
                pred_spans_: set[tuple[str, int, int]], is_native: bool | None):
        # Namespace spans by doc index so identical (label,start,end) tuples
        # in different documents never collide in the accumulated sets.
        def tag(spans):
            return {(doc_idx, s) for s in spans}

        labels_here = {s[0] for s in gold_spans} | {s[0] for s in pred_spans_}
        for label in labels_here:
            g = {s for s in gold_spans if s[0] == label}
            p = {s for s in pred_spans_ if s[0] == label}
            self.gold[label] |= tag(g)
            self.pred[label] |= tag(p)

        if is_native is not None:
            bucket = "GIVENNAME+SURNAME/" + ("native" if is_native else "foreign")
            g = {s for s in gold_spans if s[0] in NAME_LABELS}
            p = {s for s in pred_spans_ if s[0] in NAME_LABELS}
            self.gold[bucket] |= tag(g)
            self.pred[bucket] |= tag(p)

    def report(self) -> list[tuple[str, float, float, float, int, int, int]]:
        rows = []
        for key in sorted(set(self.gold) | set(self.pred)):
            precision, recall, f1, tp, fp, fn = prf1(self.gold[key], self.pred[key])
            rows.append((key, precision, recall, f1, tp, fp, fn))
        return rows


def format_report(title: str, rows: list) -> str:
    """sklearn-classification_report-style table: per-label precision/
    recall/f1-score/support, then micro/macro/weighted avg -- computed only
    over real taxonomy labels (the GIVENNAME+SURNAME/native|foreign cuts are
    diagnostic subsets of those same labels and would double-count if
    folded into the averages, so they're listed separately below)."""
    label_rows = [r for r in rows if not r[0].startswith(_EXTRA_BUCKET_PREFIX)]
    extra_rows = [r for r in rows if r[0].startswith(_EXTRA_BUCKET_PREFIX)]

    lines = [f"## {title}", "",
             "| label | precision | recall | f1-score | support |",
             "|---|---|---|---|---|"]
    for key, p, r, f1, tp, fp, fn in label_rows:
        support = tp + fn
        lines.append(f"| {key} | {p:.4f} | {r:.4f} | {f1:.4f} | {support} |")

    if label_rows:
        total_tp = sum(r[4] for r in label_rows)
        total_fp = sum(r[5] for r in label_rows)
        total_fn = sum(r[6] for r in label_rows)
        micro_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 0.0
        micro_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 0.0
        micro_f1 = (2 * micro_p * micro_r / (micro_p + micro_r)
                    if (micro_p + micro_r) else 0.0)
        total_support = total_tp + total_fn
        macro_p = sum(r[1] for r in label_rows) / len(label_rows)
        macro_r = sum(r[2] for r in label_rows) / len(label_rows)
        macro_f1 = sum(r[3] for r in label_rows) / len(label_rows)
        wp = sum(r[1] * (r[4] + r[6]) for r in label_rows) / total_support if total_support else 0.0
        wr = sum(r[2] * (r[4] + r[6]) for r in label_rows) / total_support if total_support else 0.0
        wf1 = sum(r[3] * (r[4] + r[6]) for r in label_rows) / total_support if total_support else 0.0

        lines.append("| | | | | |")
        lines.append(f"| micro avg | {micro_p:.4f} | {micro_r:.4f} | {micro_f1:.4f} | {total_support} |")
        lines.append(f"| macro avg | {macro_p:.4f} | {macro_r:.4f} | {macro_f1:.4f} | {total_support} |")
        lines.append(f"| weighted avg | {wp:.4f} | {wr:.4f} | {wf1:.4f} | {total_support} |")

    if extra_rows:
        lines.append("")
        lines.append("| native/foreign cut | precision | recall | f1-score | support |")
        lines.append("|---|---|---|---|---|")
        for key, p, r, f1, tp, fp, fn in extra_rows:
            support = tp + fn
            lines.append(f"| {key} | {p:.4f} | {r:.4f} | {f1:.4f} | {support} |")

    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rebalanced-model", default=None,
                     help="Local checkpoint dir or HF Hub repo ID for the "
                          "rebalanced model. Required unless --dry-run.")
    ap.add_argument("--n", type=int, default=300,
                     help="Sample size from the test split. 0 = full split.")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--workers", type=int, default=4,
                     help="Thread pool size for the original model's API calls.")
    ap.add_argument("--device", default=None)
    ap.add_argument("--max-length", type=int, default=510,
                     help="Sliding-window max token length for the local "
                          "rebalanced model (XLM-R's real budget is 512 "
                          "incl. special tokens; 510 leaves headroom).")
    ap.add_argument("--stride", type=int, default=256,
                     help="Sliding-window stride for the local rebalanced "
                          "model, must be >= the longest entity in tokens.")
    ap.add_argument("--out", default=str(ROOT / "reports" / "benchmark_rebalance.md"))
    ap.add_argument("--dry-run", action="store_true",
                     help="Load data, replay native/foreign flags, verify "
                          "alignment between merged_original and "
                          "merged_rebalanced test splits -- no model calls.")
    args = ap.parse_args()

    print("Loading merged_original (train/val/test, for RNG replay order)...",
          file=sys.stderr)
    orig_by_split = {s: load_docs(ORIG_DIR / f"{s}.docs.jsonl") for s in RUN_ORDER}
    flags_by_split = replay_native_flags(
        [(s, orig_by_split[s]) for s in RUN_ORDER], args.seed)
    native_flags = flags_by_split["test"]

    print("Loading merged_rebalanced/test.docs.jsonl...", file=sys.stderr)
    rebal_test = load_docs(REBAL_DIR / "test.docs.jsonl")
    orig_test = orig_by_split["test"]

    assert len(rebal_test) == len(orig_test) == len(native_flags), (
        f"length mismatch: rebalanced={len(rebal_test)} "
        f"original={len(orig_test)} flags={len(native_flags)}")

    # Defensive: confirm merged_original/test and merged_rebalanced/test are
    # the same documents in the same order before trusting index-aligned
    # native/foreign tags. If IDs are absent, fall back to a text-length
    # sanity check instead of silently mis-tagging every document.
    orig_ids = [d.get("id") for d in orig_test]
    rebal_ids = [d.get("id") for d in rebal_test]
    if all(orig_ids) and all(rebal_ids):
        mismatches = sum(1 for a, b in zip(orig_ids, rebal_ids) if a != b)
        assert mismatches == 0, (
            f"{mismatches}/{len(orig_ids)} doc-id order mismatches between "
            "merged_original/test and merged_rebalanced/test -- native/"
            "foreign tags would be misattributed. Aborting.")
    else:
        print("WARNING: doc ids missing on one side, skipping id-order check",
              file=sys.stderr)

    n_native = sum(native_flags)
    print(f"test split: {len(rebal_test)} docs, {n_native} native / "
          f"{len(rebal_test) - n_native} foreign", file=sys.stderr)

    if args.dry_run:
        print("dry run OK -- data loads and aligns. Nothing else checked.")
        return

    if not args.rebalanced_model:
        ap.error("--rebalanced-model is required unless --dry-run")

    indices = list(range(len(rebal_test)))
    if args.n and args.n < len(indices):
        rng = random.Random(args.seed)
        indices = sorted(rng.sample(indices, args.n))
    print(f"scoring on {len(indices)} sampled docs", file=sys.stderr)

    print(f"Loading rebalanced model: {args.rebalanced_model}", file=sys.stderr)
    from predict import load_model, detect_entities  # noqa: E402
    model, tokenizer, id2label = load_model(args.rebalanced_model, device=args.device)

    def predict_rebalanced(text: str) -> list[dict]:
        return detect_entities(text, model, tokenizer, id2label,
                                max_length=args.max_length, stride=args.stride)

    import original_model_client  # noqa: E402
    predict_original = original_model_client.predict

    board_rebal = Scoreboard()
    board_orig = Scoreboard()

    def run_original(idx: int, text: str):
        try:
            return idx, predict_original(text)
        except Exception as exc:  # noqa: BLE001
            print(f"  original-model call failed on doc {idx}: {exc}",
                  file=sys.stderr)
            return idx, []

    texts = {i: rebal_test[i]["text"] for i in indices}

    print("Running original model (via API, threaded)...", file=sys.stderr)
    orig_preds: dict[int, list[dict]] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for idx, preds in pool.map(lambda i: run_original(i, texts[i]), indices):
            orig_preds[idx] = preds

    print("Running rebalanced model (local, sequential)...", file=sys.stderr)
    for n_done, idx in enumerate(indices, 1):
        rebal_preds = predict_rebalanced(texts[idx])
        gold = entity_spans(rebal_test[idx])
        is_native = native_flags[idx]

        board_rebal.add_doc(idx, gold, pred_spans(rebal_preds), is_native)
        board_orig.add_doc(idx, gold, pred_spans(orig_preds.get(idx, [])), is_native)

        if n_done % 50 == 0:
            print(f"  {n_done}/{len(indices)}", file=sys.stderr)

    report = "\n\n".join([
        f"# Rebalance benchmark ({len(indices)} docs, seed={args.seed})",
        format_report("Rebalanced model", board_rebal.report()),
        format_report("Original model", board_orig.report()),
    ])
    print(report)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"\nwritten to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
