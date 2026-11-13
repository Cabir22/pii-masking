"""Build the golden regression corpus from the live dataset.

Two populations, deliberately mixed in one file:

  * `_golden_kind="positive"` -- documents that pass every current gate,
    stratified across document types and length bands. These pin the
    behaviour the pipeline is supposed to have: a change that starts
    rejecting them has broken something.

  * `_golden_kind="defect"` -- one or more real examples of every defect
    class the 100k audit found. These pin the behaviour it is supposed NOT
    to have: a change that starts accepting them has regressed.

Keeping both in one file matters. A suite of only-good examples cannot tell
a working gate from a gate that accepts everything.

Run:  python scripts/build_golden_corpus.py
"""

from __future__ import annotations

import json
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.anchors import structural_kind                       # noqa: E402
from piigen.config import ENTITY_SET                             # noqa: E402
from piigen.llm.quality_filter import check_zero_width_in_spans  # noqa: E402
from piigen.resolver import find_unlabeled_repeats               # noqa: E402
from piigen.validate import validate_example                     # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "raw" / "llm_augmented.jsonl"
OUT_DIR = ROOT / "data" / "golden"
OUT = OUT_DIR / "golden_az.jsonl"

TARGET_POSITIVES = 200
PER_DEFECT_CLASS = 4

CYRILLIC = re.compile(r"[Ѐ-ӿ]")
ZERO_WIDTH = re.compile(r"[​‌‍﻿]")
BANDS = {"very_short": (40, 150), "short": (150, 400), "medium": (400, 1100),
         "long": (1100, 2600), "very_long": (2600, 5500),
         "extreme": (5500, 10000)}


def defect_classes(rec: dict) -> list[str]:
    """Every audited defect class this record exhibits."""
    text, ents = rec["text"], rec["entities"]
    out = []

    if find_unlabeled_repeats(text, ents):
        out.append("repeat_mention_incomplete")
    if unicodedata.normalize("NFC", text) != text:
        out.append("not_nfc")
    if check_zero_width_in_spans(text, ents):
        out.append("zero_width_in_span")
    if CYRILLIC.search(text):
        out.append("cyrillic_present")

    band = rec.get("_bucket")
    if band in BANDS:
        lo, hi = BANDS[band]
        if not (lo <= len(text) <= hi):
            out.append("band_metadata_wrong")

    for e in ents:
        if structural_kind(text, e["start"], e["end"]):
            out.append("structural_number_mislabel")
            break

    if any(len(e["text"]) < 3 for e in ents):
        out.append("short_span")

    spec = rec.get("_spec") or {}
    final_values = {e["text"] for e in ents}
    for pe in (spec.get("entities") or []):
        val = pe.get("value")
        if val and val in text and val not in final_values:
            out.append("planned_value_unlabeled")
            break

    if validate_example(rec):
        out.append("fails_current_validator")

    return out


def main() -> int:
    if not SOURCE.exists():
        print(f"source not found: {SOURCE}")
        return 1

    rng = random.Random(20260825)
    positives_by_key: dict[tuple, list] = defaultdict(list)
    defects: dict[str, list] = defaultdict(list)
    scanned = 0

    for line in SOURCE.open(encoding="utf-8"):
        if not line.strip():
            continue
        rec = json.loads(line)
        scanned += 1

        classes = defect_classes(rec)
        if classes:
            for cls in classes:
                if len(defects[cls]) < PER_DEFECT_CLASS:
                    keep = dict(rec)
                    keep["_golden_kind"] = "defect"
                    keep["_golden_defects"] = classes
                    defects[cls].append(keep)
            continue

        # Reservoir-sample per (doc_type, band) so the positive half stays
        # stratified without holding the whole 81 MB corpus in memory.
        key = (rec.get("_doc_type"), rec.get("_bucket"))
        bucket = positives_by_key[key]
        if len(bucket) < 3:
            bucket.append(rec)
        elif rng.random() < 0.05:
            bucket[rng.randrange(3)] = rec

    keys = sorted(positives_by_key, key=lambda k: (str(k[0]), str(k[1])))
    positives: list[dict] = []
    round_no = 0
    while len(positives) < TARGET_POSITIVES and round_no < 3:
        for key in keys:
            if len(positives) >= TARGET_POSITIVES:
                break
            if len(positives_by_key[key]) > round_no:
                rec = dict(positives_by_key[key][round_no])
                rec["_golden_kind"] = "positive"
                positives.append(rec)
        round_no += 1

    chosen_defects: list[dict] = []
    seen_ids: set[str] = set()
    for cls in sorted(defects):
        for rec in defects[cls]:
            if rec["id"] not in seen_ids:
                seen_ids.add(rec["id"])
                chosen_defects.append(rec)

    rows = positives + chosen_defects
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for rec in rows:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"scanned          : {scanned}")
    print(f"positives        : {len(positives)}")
    print(f"defect examples  : {len(chosen_defects)}")
    print(f"total written    : {len(rows)}  ->  {OUT}")
    print(f"size             : {OUT.stat().st_size / 1024:.0f} KB")
    print()
    print("defect classes represented:")
    for cls in sorted(defects):
        print(f"  {cls:<32} {len(defects[cls])} kept "
              f"(cap {PER_DEFECT_CLASS})")
    print()
    labels = Counter(e["label"] for r in rows for e in r["entities"])
    print(f"labels covered   : {len(labels)}/{len(ENTITY_SET)}")
    missing = sorted(ENTITY_SET - set(labels))
    if missing:
        print(f"  NOT covered    : {missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
