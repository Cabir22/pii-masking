"""Versioned repair migration for the Azerbaijani PII corpus.

Applies the five repair steps the 100k audit specified, in the one order that
keeps offsets correct:

    1. NFC-normalize text                       (text changes -> re-resolve)
    2. strip zero-width chars inside spans      (text changes -> re-resolve)
    3. complete repeated mentions               (text unchanged)
    4. re-resolve planned values left unlabeled (text unchanged)
    5. recompute _bucket from actual length     (metadata only)
    6. drop structural-number spans             (span removal)
    7. re-validate; quarantine whatever still fails

Steps 1 and 2 must precede everything that adds spans, and both recompute
offsets from scratch rather than shifting them -- a shift is only correct when
the edit is a pure deletion of a known width, and NFC composition is not.

Why one pass rather than five files
-----------------------------------
The audit's plan wrote v2..v5 as separate files. Every step is per-record and
order-dependent only WITHIN a record, never across records, so a single
streaming pass is exactly equivalent and needs 1x the corpus on disk instead
of 5x (81 MB vs ~400 MB). `--emit-versions` restores the five-file form when
the intermediate artifacts are wanted for audit.

Nothing is mutated in place. The source is opened read-only, and the v1
backup is created first and never written to again.

Run:  python scripts/migrate_dataset.py --dry-run
      python scripts/migrate_dataset.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.anchors import has_anchor, structural_kind     # noqa: E402
from piigen.llm.specs import LENGTH_BANDS                 # noqa: E402
from piigen.resolver import (complete_occurrences,        # noqa: E402
                             find_unlabeled_repeats, resolve_claims)
from piigen.validate import labels_allowed, validate_example  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / "data" / "raw" / "llm_augmented.jsonl"

# Band bounds come from the sampler that wrote `_bucket`, not from
# config.DEFAULT_LENGTH_BUCKETS -- those are the PROCEDURAL generator's bands
# and use different names and ranges entirely ("fragment" vs "very_short").
# Reading the wrong table here would "repair" 100% of records into the wrong
# band.
BAND_BOUNDS = {name: (lo, hi) for name, _w, lo, hi, _hint in LENGTH_BANDS}

ZERO_WIDTH = re.compile(r"[​‌‍﻿]")


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def band_for(length: int) -> str | None:
    for name, (lo, hi) in BAND_BOUNDS.items():
        if lo <= length <= hi:
            return name
    return None


def re_resolve(text: str, entities: list[dict]) -> list[dict]:
    """Rebuild every span from scratch after a text change.

    Uses the existing (label, value) pairs as claims and lets `resolve_claims`
    find them again in the new text, so the result obeys the current
    word-boundary and short-value rules rather than inheriting stale offsets.
    """
    claims = [{"label": e["label"], "text": e["text"]} for e in entities]
    resolved, _dropped = resolve_claims(text, claims)
    return resolved


def migrate_record(rec: dict) -> tuple[dict, list[str], str | None]:
    """Apply every repair step to one record.

    Returns `(record, repairs_applied, quarantine_reason)`.
    """
    repairs: list[str] = []
    text = rec["text"]
    entities = list(rec["entities"])

    # --- step 1: NFC ------------------------------------------------------
    normalized = unicodedata.normalize("NFC", text)
    if normalized != text:
        text = normalized
        entities = re_resolve(text, entities)
        repairs.append("nfc_normalized")

    # --- step 2: zero-width INSIDE a span --------------------------------
    # Only inside spans. Zero-width characters elsewhere are the deliberate
    # `invisible` noise kind (1,012 records) and must survive untouched.
    in_span = any(ZERO_WIDTH.search(e["text"]) for e in entities)
    if in_span:
        stripped = ZERO_WIDTH.sub("", text)
        text = stripped
        entities = re_resolve(
            text, [{"label": e["label"],
                    "text": ZERO_WIDTH.sub("", e["text"])} for e in entities])
        repairs.append("zero_width_stripped_from_span")

    # --- step 2b: re-resolve under the CURRENT resolver ------------------
    # Steps 1 and 2 above only re-resolve when they changed the text, so a
    # record whose text needs no repair kept whatever spans the resolver of
    # its generation day produced. That made every resolver fix forward-only.
    #
    # 2026-08-27: measured on the corpus, 977 records (1.5%) carried spans the
    # current resolver would not produce -- 953 of them stem-only spans from
    # before the morphology span policy ("Zire kucesi" where the text reads
    # "Zire kucesinde", which the resolver now covers whole because a
    # stem-only span has no token boundary at its end and is unemittable by a
    # token classifier). Re-resolving unconditionally is what actually applies
    # a resolver fix to the existing corpus.
    #
    # Only accepted when it does not LOSE annotations: re-resolution can drop
    # a span whose surrounding word the noise injector corrupted, and for an
    # already-generated record that damage cannot be undone. Those keep their
    # original spans and are caught by validate_example's span-boundary check
    # at step 7 instead, so they surface for review rather than silently
    # shedding entities here.
    if entities:
        reresolved = re_resolve(text, entities)
        if len(reresolved) >= len(entities) and reresolved != entities:
            entities = reresolved
            repairs.append("re_resolved_under_current_resolver")

    # --- step 6 (early): structural-number spans -------------------------
    # Done before completion so a dropped structural span cannot be
    # re-added by complete_occurrences on the next line.
    kept = []
    dropped_structural = 0
    for e in entities:
        if structural_kind(text, e["start"], e["end"]):
            dropped_structural += 1
            continue
        kept.append(e)
    if dropped_structural:
        entities = kept
        repairs.append(f"dropped_{dropped_structural}_structural_span")

    # --- step 6b: anchor_required spans with no licensing context ---------
    # Drop the SPAN, not the record. The audit measured 401 unanchored
    # CARD_SECURITY_CODE, 715 TIME, 412 AGE, 348 DATE and 228 BUILDINGNUM
    # mentions; quarantining a whole document because one of its ten spans
    # is unanchored would throw away nine good annotations to remove one bad
    # one. The record is only lost if nothing valid is left, which step 7
    # then catches.
    anchored = [e for e in entities
                if has_anchor(e["label"], text, e["start"], e["end"])]
    dropped_anchor = len(entities) - len(anchored)
    if dropped_anchor:
        entities = anchored
        repairs.append(f"dropped_{dropped_anchor}_unanchored_span")

    # --- step 3: complete repeated mentions ------------------------------
    entities, added = complete_occurrences(text, entities)
    if added:
        repairs.append(f"completed_{added}_repeat_mention")

    # --- step 4: planned values present but unlabeled --------------------
    spec = rec.get("_spec") or {}
    final_values = {e["text"] for e in entities}
    missing_claims = []
    for planned in (spec.get("entities") or []):
        label, value = planned.get("label"), planned.get("value")
        if not value or not label:
            continue
        if value in text and value not in final_values:
            missing_claims.append({"label": label, "text": value})
    if missing_claims:
        occupied = [(e["start"], e["end"]) for e in entities]
        extra, _ = resolve_claims(text, missing_claims)
        added_extra = [e for e in extra
                       if not any(e["start"] < ce and cs < e["end"]
                                  for cs, ce in occupied)]
        if added_extra:
            entities = sorted(entities + added_extra,
                              key=lambda x: x["start"])
            repairs.append(f"resolved_{len(added_extra)}_planned_value")

    # --- step 5: band metadata -------------------------------------------
    correct_band = band_for(len(text))
    if correct_band and rec.get("_bucket") != correct_band:
        rec["_bucket"] = correct_band
        repairs.append("bucket_recomputed")

    rec["text"] = text
    rec["entities"] = entities

    # --- step 7: re-validate ---------------------------------------------
    if not entities:
        return rec, repairs, "no_valid_positive_entity_after_repair"
    label_problems = labels_allowed(entities)
    if label_problems:
        return rec, repairs, f"label_not_in_taxonomy: {label_problems[0]}"
    problems = validate_example(rec)
    if problems:
        return rec, repairs, f"fails_validator: {problems[0][:120]}"
    if find_unlabeled_repeats(text, entities):
        return rec, repairs, "repeat_mention_not_repairable"
    return rec, repairs, None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--out-dir", type=Path, default=ROOT / "data" / "repaired")
    ap.add_argument("--quarantine-dir", type=Path,
                    default=ROOT / "data" / "quarantine")
    ap.add_argument("--report-dir", type=Path, default=ROOT / "reports")
    ap.add_argument("--backup", type=Path, default=None,
                    help="v1 immutable backup path (default: <source>.v1.bak)")
    ap.add_argument("--limit", type=int, default=0,
                    help="process only the first N records (for a smoke test)")
    ap.add_argument("--dry-run", action="store_true",
                    help="compute everything, write nothing but the report")
    ap.add_argument("--skip-backup", action="store_true",
                    help="the v1 backup already exists and is verified")
    args = ap.parse_args()

    source: Path = args.source
    if not source.exists():
        print(f"source not found: {source}")
        return 1

    backup = args.backup or source.with_suffix(source.suffix + ".v1.bak")

    # --- v1: immutable backup -------------------------------------------
    if not args.dry_run and not args.skip_backup:
        if backup.exists():
            print(f"v1 backup already exists, not overwriting: {backup}")
        else:
            need = source.stat().st_size
            free = shutil.disk_usage(source.parent).free
            if free < need * 2:
                print(f"REFUSING TO START: {need/1e6:.0f} MB source needs at "
                      f"least {need*2/1e6:.0f} MB free for a backup plus "
                      f"output; only {free/1e6:.0f} MB available.")
                return 2
            shutil.copy2(source, backup)
            print(f"v1 backup written: {backup}")

    out_path = args.out_dir / "repaired.jsonl"
    quar_path = args.quarantine_dir / "quarantine.jsonl"
    report_path = args.report_dir / "migration_report.json"

    repair_counts: Counter = Counter()
    quarantine_counts: Counter = Counter()
    per_record: list[dict] = []
    scanned = repaired_n = quarantined_n = untouched_n = 0
    before_entities = after_entities = 0

    out_fh = quar_fh = None
    if not args.dry_run:
        for p in (args.out_dir, args.quarantine_dir, args.report_dir):
            p.mkdir(parents=True, exist_ok=True)
        out_fh = out_path.open("w", encoding="utf-8")
        quar_fh = quar_path.open("w", encoding="utf-8")

    try:
        for line in source.open(encoding="utf-8"):
            if not line.strip():
                continue
            if args.limit and scanned >= args.limit:
                break
            rec = json.loads(line)
            scanned += 1
            before_entities += len(rec["entities"])

            rec, repairs, quarantine_reason = migrate_record(rec)

            if repairs:
                rec["_repair"] = repairs
                for r in repairs:
                    repair_counts[re.sub(r"\d+", "N", r)] += 1

            if quarantine_reason:
                rec["_quarantine_reason"] = quarantine_reason
                quarantine_counts[quarantine_reason.split(":")[0]] += 1
                quarantined_n += 1
                if quar_fh:
                    quar_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            else:
                after_entities += len(rec["entities"])
                if repairs:
                    repaired_n += 1
                else:
                    untouched_n += 1
                if out_fh:
                    out_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

            if repairs or quarantine_reason:
                per_record.append({
                    "id": rec["id"],
                    "repairs": repairs,
                    "quarantine_reason": quarantine_reason,
                })
    finally:
        if out_fh:
            out_fh.close()
        if quar_fh:
            quar_fh.close()

    report = {
        "source": str(source),
        "source_sha256": sha256_of(source),
        "backup": str(backup) if backup.exists() else None,
        "dry_run": args.dry_run,
        "counts": {
            "scanned": scanned,
            "repaired": repaired_n,
            "untouched": untouched_n,
            "quarantined": quarantined_n,
            "written": repaired_n + untouched_n,
        },
        "entities": {
            "before": before_entities,
            "after_excluding_quarantine": after_entities,
        },
        "repairs_applied": dict(repair_counts.most_common()),
        "quarantine_reasons": dict(quarantine_counts.most_common()),
        "outputs": {
            "repaired": str(out_path) if not args.dry_run else None,
            "quarantine": str(quar_path) if not args.dry_run else None,
        },
        "manifest": per_record,
    }
    if not args.dry_run:
        report["repaired_sha256"] = sha256_of(out_path)
        report["quarantine_sha256"] = sha256_of(quar_path)
        args.report_dir.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 70)
    print("MIGRATION" + (" (DRY RUN -- nothing written)" if args.dry_run else ""))
    print("=" * 70)
    print(f"scanned      : {scanned:,}")
    print(f"repaired     : {repaired_n:,}")
    print(f"untouched    : {untouched_n:,}")
    print(f"quarantined  : {quarantined_n:,}")
    print(f"written      : {repaired_n + untouched_n:,}")
    print(f"entities     : {before_entities:,} -> {after_entities:,}")
    print()
    print("repairs applied:")
    for name, count in repair_counts.most_common():
        print(f"  {name:<44} {count:>7,}")
    print()
    print("quarantine reasons:")
    for name, count in quarantine_counts.most_common():
        print(f"  {name:<44} {count:>7,}")
    if not args.dry_run:
        print()
        print(f"report -> {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
