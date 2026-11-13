"""Build the targeted corpus (P2-4): fast, exact contrast documents.

    python scripts/build_targeted_corpus.py -n 40000 --seed 20261001 \\
        -o data/raw/sprint1_targeted.jsonl [--quotas quotas.json] [--stats]

Every record passes the same gates as the rest of the corpus (validate_example,
the quality screen, the leak gate, the resolver) before it is written; see
scripts/piigen/targeted/builder.py. Frames come from the team's
`piigen/targeted/frames_az.py` once it exists, otherwise from the stub.

Exit status 1 if any single frame is used in more than 3% of documents
(the frame diversity rule), or if the build cannot meet its quotas.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from piigen.targeted import quotas as Q                              # noqa: E402
from piigen.targeted.builder import BuildError, TargetedBuilder     # noqa: E402
from piigen.targeted.stats import compute_stats, format_stats      # noqa: E402


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-n", type=int, required=True, help="number of documents")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("-o", "--output", required=True, help="output JSONL")
    p.add_argument("--quotas", help="JSON merged over piigen/targeted/quotas.json")
    p.add_argument("--stats", action="store_true", help="print the P2-4 statistics")
    p.add_argument("--stats-json", help="also write the statistics as JSON here")
    args = p.parse_args(argv)

    # the value pool warns once per exhausted finite label (CITY, AGE, ...);
    # expected at this volume, and it would bury the statistics
    logging.getLogger("piigen.values").setLevel(logging.ERROR)
    started = time.time()
    try:
        builder = TargetedBuilder(args.seed, args.n, Q.load(args.quotas))
        records = builder.build()
    except BuildError as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        return 1

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(records)} documents to {out} in {time.time() - started:.1f}s")

    stats = compute_stats(records, builder)
    if args.stats:
        print(format_stats(stats))
    if args.stats_json:
        Path(args.stats_json).write_text(json.dumps(stats, ensure_ascii=False, indent=2),
                                         encoding="utf-8")
    if not stats["checks"]["max frame share <= 3%"]["ok"]:
        print("BUILD FAILED: a frame exceeds the 3% share", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
