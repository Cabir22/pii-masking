"""Sweep the built corpus for spans that end or start mid-word.

WHY
---
`piigen/validate.py::span_boundary_problems` catches spans the noise
injector split across a word edge -- CITY "Quba" left sitting inside
"Qubar egionunda", or "vAxtı 13:41" glued into "vAxt ı13:41". Such a span
is structurally valid (offsets were repaired) and passes every other
check, but it ends where no token boundary exists, so a token classifier
can never reproduce it. It is unlearnable by construction and it teaches
the model a boundary that does not exist.

`llm/pipeline.py::assemble_document` now reverts noise when this check
fires, so newly generated documents are clean. That guard was added AFTER
the current corpus was built -- prior audits counted 52 and then 996 such
records -- and the already-generated corpus was never re-swept. This
script is that sweep.

REPAIR POLICY
-------------
Affected documents are DROPPED, not repaired, and never merely stripped of
the offending entity. Deleting the span while leaving the value in the text
would convert a broken label into unlabelled real PII, which is precisely
the contamination that teaches the model to ignore a name -- a false
negative, the costlier error for a masking model. The underlying text is
corrupted by noise, so no correct span exists to repair it to.

Run:
  python scripts/sweep_span_defects.py
  python scripts/sweep_span_defects.py --drop --out data/processed/merged_swept
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):      # Windows consoles default to cp125x
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from piigen.validate import span_boundary_problems  # noqa: E402

SPLITS = ("train", "val", "test")


def kind_of(problem: str) -> str:
    return problem.split(":", 1)[0]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=str(ROOT / "data" / "processed" / "merged"))
    ap.add_argument("--out", default=str(ROOT / "data" / "processed" / "merged_swept"))
    ap.add_argument("--drop", action="store_true",
                    help="write a cleaned copy with affected documents removed")
    ap.add_argument("--examples", type=int, default=15)
    args = ap.parse_args(argv)

    data_dir = Path(args.data_dir)
    out_dir = Path(args.out)
    if args.drop:
        out_dir.mkdir(parents=True, exist_ok=True)

    kind_counts: Counter = Counter()
    label_counts: Counter = Counter()
    lang_counts: Counter = Counter()
    per_split_bad: Counter = Counter()
    per_split_total: Counter = Counter()
    examples: list[str] = []

    for split in SPLITS:
        src = data_dir / f"{split}.docs.jsonl"
        if not src.exists():
            print(f"error: {src} not found")
            return 1
        out_fh = (out_dir / f"{split}.docs.jsonl").open("w", encoding="utf-8") if args.drop else None
        try:
            with src.open(encoding="utf-8") as fh:
                for line in fh:
                    doc = json.loads(line)
                    per_split_total[split] += 1
                    problems = span_boundary_problems(doc["text"], doc["entities"])
                    if problems:
                        per_split_bad[split] += 1
                        lang_counts[doc.get("lang", "?")] += 1
                        for p in problems:
                            kind_counts[kind_of(p)] += 1
                            label_counts[p.split(": ", 1)[0].split()[-1]
                                         if " " in p else "?"] += 1
                            if len(examples) < args.examples:
                                examples.append(f"[{doc.get('lang','?')}] {p}")
                        continue          # dropped
                    if out_fh is not None:
                        out_fh.write(line)
        finally:
            if out_fh is not None:
                out_fh.close()

    total = sum(per_split_total.values())
    bad = sum(per_split_bad.values())
    print(f"scanned {total:,} documents in {data_dir}")
    print(f"documents with a mid-word span defect: {bad:,} ({bad/total:.3%})\n")

    print("by split:")
    for split in SPLITS:
        n, d = per_split_bad[split], per_split_total[split]
        print(f"  {split:<5} {n:>6,} / {d:>8,}  ({(n/d if d else 0):.3%})")

    print("\nby defect kind:")
    for kind, n in kind_counts.most_common():
        print(f"  {kind}: {n:,}")

    print("\nby language:")
    for lang, n in lang_counts.most_common():
        print(f"  {lang}: {n:,}")

    print(f"\nexamples (up to {args.examples}):")
    for ex in examples:
        print(f"  {ex}")

    if args.drop:
        labels_src = data_dir / "labels.json"
        if labels_src.exists():
            (out_dir / "labels.json").write_text(
                labels_src.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"\nwrote cleaned corpus to {out_dir} ({total - bad:,} documents kept)")
    else:
        print("\n(report only -- pass --drop to write a cleaned corpus)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
