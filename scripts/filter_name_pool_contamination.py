"""Drop records whose GIVENNAME or SURNAME value is not a personal name.

2026-08-29 audit finding F7. The given-name pools are a registry export and
contained 49 strings that are a place name, a calendar word or ordinary
administrative vocabulary in Azerbaijani -- "Məhkəmə" (court), "Ünvan"
(address), "Tarix" (date), "Şamaxı", "Noyabr". `locales/az.NOT_PERSONAL_NAMES`
now filters them out of the pools, which stops new documents being generated
this way. This script deals with the documents already generated.

Why the records are dropped rather than re-labeled
--------------------------------------------------
The annotation is not the broken part. The generator planned
`GIVENNAME = Şamaxı`, and the model wrote a document that genuinely uses it
as a person's name -- "Ad: Şamaxı", "Alıcı: Şamaxı Zahiddinova",
"Hörmətli Dövlət", "şəxs Məhkəmə Xanbabalı olaraq göstərilir". The span is
labeled correctly for the sentence it sits in; the sentence itself is wrong.

That rules out both alternatives:

  * Re-labeling to CITY contradicts the document -- "Ad:" is a name field,
    and "Məhkəmə" is not a city under any reading.
  * Deleting just the span leaves a name-field value with no annotation,
    which is the unlabeled-PII defect (F1) this corpus already has too much
    of.

There is no correct annotation for these documents, so the record goes. This
is a different case from dropping a valid-but-hard example, and the
distinction matters: nothing here is a difficult positive being discarded
for convenience.

Scope is small and measured: 111 mentions across 62 of 80,694 documents
(0.077%). City names that are also genuine Azerbaijani personal names --
Laçın, Cəbrayıl, Babək, Füzuli, Şirvan, Oğuz, Sahil -- are NOT in the filter
list, so the 184 mentions of those keep their documents.

Run:  python scripts/filter_name_pool_contamination.py --dry-run
      python scripts/filter_name_pool_contamination.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.locales.az import NOT_PERSONAL_NAMES   # noqa: E402

NAME_LABELS = ("GIVENNAME", "SURNAME")
REASON = "name_pool_contamination"


def offending(rec: dict) -> list[str]:
    """Values in this record that a person is never actually called."""
    return sorted({e["text"] for e in (rec.get("entities") or [])
                   if e.get("label") in NAME_LABELS
                   and e.get("text") in NOT_PERSONAL_NAMES})


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", type=Path,
                   default=ROOT / "data" / "repaired" / "repaired.clean.jsonl",
                   help="corpus to filter (rewritten in place)")
    p.add_argument("--excluded-out", type=Path,
                   default=ROOT / "data" / "repaired" / "excluded_flagged.jsonl",
                   help="audit trail; dropped records are APPENDED here")
    p.add_argument("--dry-run", action="store_true",
                   help="report what would be dropped, write nothing")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.source.exists():
        print(f"source not found: {args.source}", file=sys.stderr)
        return 1

    tmp = args.source.with_suffix(args.source.suffix + ".tmp")
    kept = dropped = 0
    by_value: Counter = Counter()
    by_doc_type: Counter = Counter()
    dropped_records: list[dict] = []

    with args.source.open(encoding="utf-8") as f_in, \
            tmp.open("w", encoding="utf-8") as f_out:
        for line in f_in:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            bad = offending(rec)
            if bad:
                dropped += 1
                by_doc_type[rec.get("_doc_type")] += 1
                for v in bad:
                    by_value[v] += sum(
                        1 for e in rec["entities"]
                        if e["label"] in NAME_LABELS and e["text"] == v)
                rec["_excluded_reason"] = REASON
                rec["_excluded_values"] = bad
                dropped_records.append(rec)
            else:
                kept += 1
                f_out.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"source        : {args.source}")
    print(f"kept          : {kept:,}")
    print(f"dropped       : {dropped:,} "
          f"({100 * dropped / max(1, kept + dropped):.3f}%)")
    print(f"mentions      : {sum(by_value.values()):,}")
    print("\nby value:")
    for v, n in by_value.most_common():
        print(f"  {v:<14}{n:>5}")
    print("\nby doc type (top 10):")
    for d, n in by_doc_type.most_common(10):
        print(f"  {d:<26}{n:>5}")

    if args.dry_run:
        tmp.unlink(missing_ok=True)
        print("\n--dry-run: nothing written")
        return 0

    with args.excluded_out.open("a", encoding="utf-8") as f_exc:
        for rec in dropped_records:
            f_exc.write(json.dumps(rec, ensure_ascii=False) + "\n")

    os.replace(tmp, args.source)
    print(f"\n-> {args.source} rewritten ({kept:,} records)")
    print(f"-> {dropped:,} record(s) appended to {args.excluded_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
