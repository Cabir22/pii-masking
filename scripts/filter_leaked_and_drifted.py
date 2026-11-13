"""Drop records that fail `validate_corpus.py`'s `unlabeled_pii_leak` or
`resolver_drift` checks -- the two MUST-BE-ZERO checks `migrate_dataset.py`
does not (yet) repair on its own (2026-08-28 session).

Uses the exact same detection logic those checks use (imported, not
reimplemented), so the result matches `validate_corpus.py` precisely.

Run:  python scripts/filter_leaked_and_drifted.py
      python scripts/filter_leaked_and_drifted.py --source data/repaired/repaired.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from piigen.llm.quality import find_leaked_pii   # noqa: E402
from piigen.resolver import resolve_claims       # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", type=Path,
                   default=ROOT / "data" / "repaired" / "repaired.jsonl",
                   help="migrate_dataset.py output to filter")
    p.add_argument("--out", type=Path,
                   default=ROOT / "data" / "repaired" / "repaired.clean.jsonl",
                   help="where the kept (clean) records go")
    p.add_argument("--excluded-out", type=Path,
                   default=ROOT / "data" / "repaired" / "excluded_flagged.jsonl",
                   help="where the dropped records go, with a reason tag, "
                        "for audit")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.source.exists():
        print(f"source not found: {args.source} -- run migrate_dataset.py first",
              file=sys.stderr)
        return 1

    kept = dropped = drop_leak = drop_drift = 0
    args.out.parent.mkdir(parents=True, exist_ok=True)

    with args.source.open(encoding="utf-8") as f_in, \
         args.out.open("w", encoding="utf-8") as f_out, \
         args.excluded_out.open("w", encoding="utf-8") as f_exc:
        for line in f_in:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            text = rec.get("text", "")
            entities = rec.get("entities") or []

            reason = None
            if find_leaked_pii(text, entities, []):
                reason = "unlabeled_pii_leak"
                drop_leak += 1
            elif entities:
                reclaimed, _ = resolve_claims(
                    text, [{"label": e["label"], "text": e["text"]}
                           for e in entities])
                now = {(e["start"], e["end"], e["label"]) for e in reclaimed}
                was = {(e["start"], e["end"], e["label"]) for e in entities}
                if now != was:
                    reason = "resolver_drift"
                    drop_drift += 1

            if reason:
                rec["_excluded_reason"] = reason
                f_exc.write(json.dumps(rec, ensure_ascii=False) + "\n")
                dropped += 1
            else:
                f_out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                kept += 1

    print(f"kept          : {kept:,}")
    print(f"dropped       : {dropped:,}")
    print(f"  unlabeled_pii_leak : {drop_leak:,}")
    print(f"  resolver_drift     : {drop_drift:,}")
    print(f"-> {args.out}")
    print(f"-> {args.excluded_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
