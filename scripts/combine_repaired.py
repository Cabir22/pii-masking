"""Combine the repaired true-positive and negative-class corpora into one
file, for a full `validate_corpus.py` audit across both at once.

Not a `prepare_splits.py` substitute -- that script does this same merge
(plus dedup/split/tokenization) when it's run for real. This is just the
audit step, standalone, so the combined corpus can be checked before
committing to a full Stage 3 run.

id collision: both source files independently number their own records
`llm_az_000000`, `llm_az_000001`, ... from a separate generation run, so
combining verbatim would manufacture thousands of `duplicate_id` false
positives that are really just a naming coincidence. Prefixed by source
filename stem, same convention `prepare_splits.py.load_records()` already
uses, so a record's id is traceable back to which corpus it came from.

Run:  python scripts/combine_repaired.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("inputs", nargs="*", default=[
        str(ROOT / "data" / "repaired" / "repaired.clean.jsonl"),
        str(ROOT / "data" / "repaired" / "negatives.clean.jsonl"),
    ])
    p.add_argument("--out", type=Path,
                   default=ROOT / "data" / "repaired" / "combined.jsonl")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_paths = [Path(p) for p in args.inputs]
    missing = [p for p in input_paths if not p.exists()]
    if missing:
        print(f"error: input file(s) not found: {missing}", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with args.out.open("w", encoding="utf-8") as out_fh:
        for p in input_paths:
            n = 0
            with p.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    rec["id"] = f"{p.stem}__{rec.get('id', n)}"
                    out_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    n += 1
            print(f"  {p.name:<32}{n:>8,} record(s)")
            total += n

    print(f"\n-> {args.out} ({total:,} record(s) total)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
