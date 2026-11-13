"""Repair pass for a negative_only corpus (see llm_augment_data.py
--negative-only-rate) -- NOT scripts/migrate_dataset.py.

Why this is a separate script, not a `migrate_dataset.py` run
---------------------------------------------------------------
`migrate_dataset.py`'s step 7 has `if not entities: return ...,
"no_valid_positive_entity_after_repair"` -- every negative_only record has
`entities == []` BY DESIGN (that's the whole point of the doc class: real
PII-lookalike decoys, zero real entities). Running the existing tool against
a negative_only file would quarantine all 25,000 records as "broken",
because it has no concept of a legitimately-empty entity list. Its other
repair steps (anchor checks, repeat-mention completion, planned-value
resolution) are meaningless here too -- they all operate on entities that
don't exist for this doc class.

What actually matters for a negative_only record
--------------------------------------------------
1. NFC normalization + zero-width stripping, across the WHOLE text (not
   span-anchored, since there are no spans).
2. `find_leaked_pii(text, [], [])` -- an independent full-text sweep for a
   genuinely checksum/format-valid PII string sitting completely unlabeled.
   This is the one real correctness concern for this doc class: a
   hard_negative/adversarial decoy is SUPPOSED to look plausible but be
   invalid (bad Luhn, truncated key, wrong IBAN check digits); if one
   coincidentally lands on a valid shape, keeping it unlabeled would teach
   the model "don't flag this" for something that actually is real PII.
3. `validate_example(rec, min_native_words=0)` -- same floor
   `pipeline.py`'s `assemble_document` already used to accept these records
   at generation time (see the 2026-08-28 language-evidence fixes). Not a
   new bar, a re-confirmation: catches blocklist hits, Turkish
   contamination, or anything that changed in validate.py since generation.
4. Band metadata recompute, same as migrate_dataset.py's step 5.

Run:  python scripts/repair_negative_corpus.py --dry-run
      python scripts/repair_negative_corpus.py
"""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from migrate_dataset import band_for                       # noqa: E402
from piigen.llm.quality import _LEAK_CONFIRM, find_leaked_pii  # noqa: E402
from piigen.validate import validate_example               # noqa: E402

ZERO_WIDTH_RE = __import__("re").compile(r"[​‌‍﻿]")

# find_leaked_pii's decoy-exemption logic (see its own docstring) needs the
# ACTUAL decoy strings to tell "the near-miss we deliberately injected" apart
# from "PII the model invented on its own" -- and those strings were never
# persisted to the output record, only a count (`_hard_negatives`). Calling
# it with an empty decoy list therefore treats every intended decoy as an
# unlabeled leak, which is wrong by construction for a negative_only corpus.
#
# Measured live on this corpus before trusting it: of 2,954 flagged
# documents, 2,170 were "MAC" and 561 were "IPV4" -- both patterns with NO
# `_LEAK_CONFIRM` checksum/format gate, and manual review confirmed the
# samples were genuine near-miss decoys (a MAC regex catching a prefix of a
# longer hex string, exactly the failure mode find_leaked_pii's own
# docstring already describes) or, for TELEPHONENUM (101, also unconfirmed),
# a substring match inside an unrelated longer digit string (an ISBN's
# "978-0-...-..." matched as a 10-digit phone number). CARD (459) and URL
# (121) were kept -- both require passing a real Luhn/token check, and a
# near-miss decoy is deliberately built to FAIL its checksum
# (`edge_cases.near_miss_value`), so a checksum-VALID match in a negative
# corpus is a real signal, not noise.
#
# Restricting to checksum/format-confirmed kinds only (CARD's confirmation
# is inline in find_leaked_pii itself, not in _LEAK_CONFIRM) is the
# principled fix available without re-generating the corpus with decoys
# persisted.
_TRUSTED_LEAK_KINDS = frozenset({"CARD"}) | frozenset(_LEAK_CONFIRM)

# Even within CARD, 226 of 459 flagged values started with 978/979 -- the
# Bookland/ISBN prefix, never a real card BIN, and confirmed as a real
# generator output: `piigen/negatives.py`'s "ISBN" hard-negative builder
# mints exactly `978-D-DDD-DDDDD-D`, a 13-digit shape that occasionally
# passes Luhn by coincidence. Real cards cannot start with 978/979, so this
# exclusion has no cost on genuine leaks and removes a confirmed false-
# positive source no confirm-function currently catches.
_ISBN_PREFIXES = ("978", "979")

# All 121 "URL" flags in the real corpus were this ONE fixed literal decoy
# from `piigen/negatives.py`'s URL_NO_TOKEN pool -- not a per-call random
# value like the CARD/MAC/IPV4 decoys, so it can be exempted by exact value
# rather than dropping the whole URL kind. Case variants are the `case_glitch`
# noise kind, not a different value. Confirmed zero non-decoy URL leaks in
# this corpus once this one is excluded.
_KNOWN_URL_DECOY = "https://docs.internal.dev/getting-started"


def _trusted_leaks(text: str) -> list[str]:
    out = []
    for leak in find_leaked_pii(text, [], []):
        kind, _, value = leak.partition(":")
        if kind not in _TRUSTED_LEAK_KINDS:
            continue
        if kind == "CARD":
            digits = "".join(c for c in value if c.isdigit())
            if digits.startswith(_ISBN_PREFIXES):
                continue
        if kind == "URL" and value.rstrip(".").lower() == _KNOWN_URL_DECOY:
            continue
        out.append(leak)
    return out


def repair_record(rec: dict) -> tuple[dict, list[str], str | None]:
    repairs: list[str] = []
    text = rec["text"]

    normalized = unicodedata.normalize("NFC", text)
    if normalized != text:
        text = normalized
        repairs.append("nfc_normalized")

    stripped = ZERO_WIDTH_RE.sub("", text)
    if stripped != text:
        text = stripped
        repairs.append("zero_width_stripped")

    rec["text"] = text

    correct_band = band_for(len(text))
    if correct_band and rec.get("_bucket") != correct_band:
        rec["_bucket"] = correct_band
        repairs.append("bucket_recomputed")

    leaks = _trusted_leaks(text)
    if leaks:
        return rec, repairs, f"real_pii_shape_in_decoy: {leaks[0][:70]}"

    problems = validate_example(rec, min_native_words=0)
    if problems:
        return rec, repairs, f"fails_validator: {problems[0][:120]}"

    return rec, repairs, None


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", type=Path,
                   default=ROOT / "data" / "raw" / "llm_augmented_negatives.jsonl")
    p.add_argument("--out", type=Path,
                   default=ROOT / "data" / "repaired" / "negatives.clean.jsonl")
    p.add_argument("--excluded-out", type=Path,
                   default=ROOT / "data" / "repaired" / "excluded_flagged_negatives.jsonl")
    p.add_argument("--dry-run", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.source.exists():
        print(f"source not found: {args.source}", file=sys.stderr)
        return 1

    scanned = repaired_n = quarantined_n = 0
    repair_counts: dict[str, int] = {}
    quarantine_reasons: dict[str, int] = {}

    out_fh = exc_fh = None
    if not args.dry_run:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        out_fh = args.out.open("w", encoding="utf-8")
        exc_fh = args.excluded_out.open("w", encoding="utf-8")

    try:
        for line in args.source.open(encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            scanned += 1
            if rec.get("entities"):
                # Shouldn't happen for a real negative_only file -- surface
                # it rather than silently mis-handling a record this script
                # wasn't built for.
                print(f"warning: {rec.get('id')} has non-empty entities, "
                      f"skipping (not a negative_only record?)",
                      file=sys.stderr)
                continue

            rec, repairs, reason = repair_record(rec)
            for r in repairs:
                repair_counts[r] = repair_counts.get(r, 0) + 1

            if reason:
                quarantined_n += 1
                key = reason.split(":")[0]
                quarantine_reasons[key] = quarantine_reasons.get(key, 0) + 1
                rec["_excluded_reason"] = reason
                if exc_fh:
                    exc_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            else:
                repaired_n += 1
                if out_fh:
                    out_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    finally:
        if out_fh:
            out_fh.close()
        if exc_fh:
            exc_fh.close()

    print(f"scanned      : {scanned:,}")
    print(f"kept         : {repaired_n:,}")
    print(f"quarantined  : {quarantined_n:,}")
    print("\nrepairs applied:")
    for k, v in sorted(repair_counts.items(), key=lambda kv: -kv[1]):
        print(f"  {k:<44}{v:>7,}")
    print("\nquarantine reasons:")
    for k, v in sorted(quarantine_reasons.items(), key=lambda kv: -kv[1]):
        print(f"  {k:<44}{v:>7,}")
    if args.dry_run:
        print("\n--dry-run: nothing written")
    else:
        print(f"\n-> {args.out}")
        print(f"-> {args.excluded_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
