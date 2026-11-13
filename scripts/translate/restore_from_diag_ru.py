"""Put back documents that were rejected by a check that has since been fixed.

Every document the harness processes is written to `<out>.diag.jsonl`,
including ones that were then withheld from the corpus. Several checks have
since been corrected -- `--rescan` was quarantining soft problems it was meant
to keep, the residue check has had false-positive classes removed, and the
stream guard no longer fails a document for the shape of its own source. The
translations behind those rejections are on disk and were never bad.

This re-runs the CURRENT hard checks over each withheld document and restores
the ones that pass. Nothing is loosened: a document comes back only if it
satisfies span integrity, label/value shape, residue, completeness, romanised
Russian and meta-response as they stand today. Anything that still fails stays
out and is left for retranslation.

    python scripts/translate/restore_from_diag_ru.py --out data/processed/ru/val.docs.jsonl \
        --input data/processed/az/val.docs.jsonl [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import translate.run_ru as R  # noqa: E402
from piigen.sentinel import SlotError, sentinelize  # noqa: E402


def hard_problem(rec: dict, source: dict) -> str | None:
    """The current hard checks, in the order the harness applies them."""
    for e in rec.get("entities") or []:
        if rec["text"][e["start"]:e["end"]] != e["text"]:
            return "span_not_exact"
    shape = R.label_shape_errors(rec.get("entities") or [])
    if shape:
        return "label_shape: " + ", ".join(shape[:3])

    src_text = source["text"]
    try:
        slotted, _, _ = sentinelize(src_text, source.get("entities") or [])
    except SlotError:
        slotted = src_text
    body = R._reslot(rec) if rec.get("entities") else rec["text"]

    n = R.az_residue(rec["text"], src_text)
    return (R.meta_response(rec["text"])
            or R.completeness(slotted, body)
            or R.romanised_russian(rec["text"], rec.get("entities"))
            or (f"az_residue x{n}" if n else None))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True,
                    help="the corpus file to restore into, rewritten in place")
    ap.add_argument("--input", type=Path, required=True,
                    help="the Azerbaijani split it was translated from")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    stem = args.out.name[:-len(".jsonl")]
    diag_path = args.out.parent / f"{stem}.diag.jsonl"
    rq_path = args.out.parent / f"{stem}.repair_queue.jsonl"
    if not diag_path.exists():
        print(f"no diagnostics at {diag_path} -- nothing to restore from")
        return 2

    src = {}
    for line in args.input.open(encoding="utf-8"):
        if line.strip():
            d = json.loads(line)
            src[d["id"]] = d
    rows = [json.loads(l) for l in args.out.open(encoding="utf-8") if l.strip()]
    have = {r["source_id"] for r in rows}
    queued = {}
    if rq_path.exists():
        for line in rq_path.open(encoding="utf-8"):
            if line.strip():
                d = json.loads(line)
                queued[d["source_id"]] = d

    missing = [sid for sid in queued if sid not in have]
    restored: list[dict] = []
    still = Counter()
    for line in diag_path.open(encoding="utf-8"):
        if not line.strip():
            continue
        rec = json.loads(line)
        sid = rec.get("source_id")
        if sid not in queued or sid in have or sid in {r["source_id"] for r in restored}:
            continue
        source = src.get(sid)
        if source is None:
            still["no source record"] += 1
            continue
        problem = hard_problem(rec, source)
        if problem is None:
            rec.pop("_diag", None)
            restored.append(rec)
        else:
            still[problem.split(":")[0].split(" x")[0]] += 1

    print(f"{args.out.name}: {len(rows)} documents, {len(missing)} withheld")
    print(f"  pass the current hard checks -> restored : {len(restored)}")
    for reason, n in still.most_common():
        print(f"  still failing ({reason}): {n}")
    if args.dry_run:
        print(f"  --dry-run: would leave {len(rows) + len(restored)} documents")
        return 0
    if not restored:
        print("  nothing to restore")
        return 0

    with args.out.open("a", encoding="utf-8") as f:
        for rec in restored:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    back = {r["source_id"] for r in restored}
    if rq_path.exists():
        kept = [d for d in queued.values() if d["source_id"] not in back]
        with rq_path.open("w", encoding="utf-8") as f:
            for d in kept:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"  corpus is now {len(rows) + len(restored)} documents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
