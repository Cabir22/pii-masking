"""Run the model against the adversarial / real-world eval set.

WHY
---
The held-out synthetic test split is produced by the same generator as the
training data, so a high F1 there mostly proves the model can pass its own
kind of exam. This set is different in kind: every case is a shape the
model was *observed* to handle wrongly during manual probing, or an
ordinary-looking string it must NOT mask.

Cases live in eval/adversarial_cases.jsonl. Each carries the text, the
entities that must be found, and a category. Cases in the
`false_positive_probe` category additionally fail if anything beyond the
expected entities is detected -- the corpus is generated with
`adversarial_rate = 0.0` and `negative_only_rate = 0.0`, so the model has
never been shown a negative example and over-masking is untested.

OUTCOMES (per expected entity)
  pass        a span with the right label covers the whole value
  partial     right label, but the span covers only part of the value
  mislabeled  a span covers the value under a different label
  missed      nothing covers the value  <- a leak; the costly error here

Run:
  python eval/run_adversarial.py
  python eval/run_adversarial.py --raw          # model only, no regex layer
  python eval/run_adversarial.py --json out.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))

from predict import load_model, hybrid_detect_entities, detect_entities  # noqa: E402

MODEL_NAME = "your-hf-org/masking-multilingual"
CASES = ROOT / "eval" / "adversarial_cases.jsonl"


def locate(text: str, value: str) -> tuple[int, int] | None:
    idx = text.find(value)
    return (idx, idx + len(value)) if idx >= 0 else None


def judge_expected(text: str, spans: list[dict], label: str,
                   value: str) -> tuple[str, str | None]:
    """Classify one expected entity against what the model produced."""
    where = locate(text, value)
    if where is None:
        return "bad_case", None           # value not present in text at all
    vstart, vend = where

    covering = [s for s in spans if s["start"] < vend and s["end"] > vstart]
    if not covering:
        return "missed", None

    right_label = [s for s in covering if s["label"] == label]
    if not right_label:
        return "mislabeled", covering[0]["label"]

    full = [s for s in right_label if s["start"] <= vstart and s["end"] >= vend]
    return ("pass", None) if full else ("partial", None)


def extra_detections(text: str, spans: list[dict],
                     expected: list[dict]) -> list[dict]:
    """Spans that do not overlap any expected value -- over-masking."""
    ranges = []
    for exp in expected:
        where = locate(text, exp["value"])
        if where:
            ranges.append(where)
    out = []
    for s in spans:
        if not any(s["start"] < e and s["end"] > b for b, e in ranges):
            out.append(s)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", default=str(CASES))
    ap.add_argument("--raw", action="store_true",
                    help="raw model only, no regex/checksum fallback layer")
    ap.add_argument("--json", dest="json_out", default=None,
                    help="write full per-case results to this file")
    ap.add_argument("--quiet", action="store_true",
                    help="summary tables only, no per-case lines")
    args = ap.parse_args(argv)

    cases = [json.loads(line) for line in
             Path(args.cases).read_text(encoding="utf-8").splitlines() if line.strip()]

    print(f"loading {MODEL_NAME} ...", file=sys.stderr)
    model, tokenizer, id2label = load_model(MODEL_NAME)
    detect = detect_entities if args.raw else hybrid_detect_entities
    mode = "RAW MODEL ONLY" if args.raw else "HYBRID (model + regex/checksum)"

    results = []
    outcome_counts: Counter = Counter()
    by_category: dict[str, Counter] = defaultdict(Counter)
    false_positives = 0
    fp_examples: list[str] = []

    for case in cases:
        text = case["text"]
        spans = detect(text, model, tokenizer, id2label)
        case_outcomes = []

        for exp in case.get("expect", []):
            outcome, got = judge_expected(text, spans, exp["label"], exp["value"])
            outcome_counts[outcome] += 1
            by_category[case["category"]][outcome] += 1
            case_outcomes.append({
                "label": exp["label"], "value": exp["value"],
                "outcome": outcome, "got_label": got,
            })

        extras = []
        if case["category"] == "false_positive_probe":
            extras = extra_detections(text, spans, case.get("expect", []))
            if extras:
                false_positives += len(extras)
                by_category[case["category"]]["false_positive"] += len(extras)
                for s in extras[:2]:
                    fp_examples.append(
                        f"{case['id']}: {s['label']} <- "
                        f"{text[s['start']:s['end']]!r}")

        results.append({
            "id": case["id"], "lang": case["lang"],
            "category": case["category"], "text": text,
            "expected": case_outcomes,
            "over_masked": [{"label": s["label"],
                             "text": text[s["start"]:s["end"]]} for s in extras],
            "detected": [{"label": s["label"],
                          "text": text[s["start"]:s["end"]]} for s in spans],
        })

        if not args.quiet:
            worst = ("missed" if any(o["outcome"] == "missed" for o in case_outcomes)
                     else "mislabeled" if any(o["outcome"] == "mislabeled" for o in case_outcomes)
                     else "partial" if any(o["outcome"] == "partial" for o in case_outcomes)
                     else "false_positive" if extras
                     else "pass")
            flag = {"pass": "  ok  ", "partial": " PART ", "mislabeled": " MISL ",
                    "missed": " MISS ", "false_positive": " FPOS ",
                    "bad_case": " ???? "}.get(worst, "  ?   ")
            print(f"[{flag}] {case['id']:<14} {text[:58]!r}")

    total_expected = sum(outcome_counts.values())
    print("\n" + "=" * 62)
    print(f"MODE: {mode}")
    print(f"cases: {len(cases)}   expected entities: {total_expected}")
    print("=" * 62)

    print("\noverall outcomes:")
    for outcome in ("pass", "partial", "mislabeled", "missed", "bad_case"):
        n = outcome_counts[outcome]
        if n or outcome in ("pass", "missed"):
            share = n / total_expected if total_expected else 0
            print(f"  {outcome:<11} {n:>4}  ({share:.1%})")
    print(f"  {'over-masked':<11} {false_positives:>4}  (false-positive probes)")

    leaks = outcome_counts["missed"]
    print(f"\nLEAK RATE (missed / expected): {leaks}/{total_expected} = "
          f"{(leaks/total_expected if total_expected else 0):.1%}")

    print("\nby category:")
    width = max(len(c) for c in by_category) if by_category else 10
    for cat in sorted(by_category):
        counts = by_category[cat]
        tot = sum(v for k, v in counts.items() if k != "false_positive")
        bits = "  ".join(f"{k}={v}" for k, v in sorted(counts.items()) if v)
        print(f"  {cat:<{width}}  (n={tot})  {bits}")

    if fp_examples:
        print("\nover-masking examples:")
        for ex in fp_examples[:10]:
            print(f"  {ex}")

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps({"mode": mode, "results": results,
                        "outcomes": dict(outcome_counts),
                        "false_positives": false_positives},
                       ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
