"""Patch repeat-mention value inconsistency in an already-translated corpus.

Background: `mint_values()` used to draw one independent value per SLOT, with
no idea that several slots come from the same underlying fact stated more
than once in the source (a documented, intentional corpus feature --
`piigen.resolver.complete_occurrences` tags every textual occurrence of a
resolved claim). Fixed in run.py (2026-09-04) to mint once per
(label, source_value) group. This script repairs documents that were
translated with the OLD, buggy minting -- without calling the API again.

How a repair works, per document:
  1. Skip fast if the Azerbaijani source has no repeat-mention group (most
     documents -- nothing to do).
  2. Reconstruct what the OLD code minted (`independent_mint_values`, same
     seed) and what the FIXED code would mint (`mint_values`, grouped). If
     they agree for every slot (the independent draws coincidentally already
     matched), nothing to change.
  3. Otherwise, recover which written English entity came from which AZ
     slot: match by (label, value) between the OLD reconstruction and the
     entities actually on disk. This must be a perfect multiset match (every
     written entity explained by exactly one slot) -- if it is not, the
     document is FLAGGED, never guessed at.
  4. Re-sentinelize the *English* text (its own entities, in their own
     on-disk position order), substitute the corrected value at every slot
     that needs to change, and splice -- exactly the same mechanism that
     built the corpus in the first place, so offsets are exact by
     construction, not by patching around them.
  5. Re-validate the patched record with the same checks translation output
     already goes through.

Usage:
    python scripts/translate/repair_repeat_mentions.py --lang en --split train
    python scripts/translate/repair_repeat_mentions.py --lang en --split train --dry-run
    python scripts/translate/repair_repeat_mentions.py --lang en \
        --input data/golden/golden_en.jsonl --az data/golden/golden_az.jsonl \
        --out data/golden/golden_en.jsonl

Writes to `<out>.new.jsonl` first, verifies it, then swaps it into place and
keeps the pre-repair file as `<out>.prerepair_bak.jsonl`.
"""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from translate.lang import ANCHORS as ANCHOR_MODULES  # noqa: E402
from translate.run import PROCESSED, independent_mint_values, mint_values  # noqa: E402
from translate.sentinel import SENTINEL_RE, SlotError, entity_source_values  # noqa: E402
from translate.sentinel import sentinelize, splice  # noqa: E402
from translate.validate import _leftover_azerbaijani  # noqa: E402

ZERO_WIDTH = set("​‌‍⁠﻿")


def repeat_groups(labels: list[str], source_values: list[str]) -> dict:
    groups = defaultdict(list)
    for i, key in enumerate(zip(labels, source_values)):
        groups[key].append(i)
    return {k: v for k, v in groups.items() if len(v) >= 2}


def match_slots_to_entities(en_entities: list[dict], en_text: str,
                            labels: list[str], old_values: dict[int, str]):
    """Recover slot -> EN-entity-index. None on any ambiguity or mismatch --
    the caller must never guess."""
    want = Counter((labels[i], old_values[i]) for i in range(len(labels)))
    have = Counter((e["label"], en_text[e["start"]:e["end"]]) for e in en_entities)
    if want != have:
        return None
    remaining = defaultdict(list)
    for i in range(len(labels)):
        remaining[(labels[i], old_values[i])].append(i)
    mapping: dict[int, int] = {}       # en-entity-index -> slot
    for idx, e in enumerate(en_entities):
        key = (e["label"], en_text[e["start"]:e["end"]])
        pool = remaining.get(key)
        if not pool:
            return None
        mapping[idx] = pool.pop(0)
    return mapping


def repair_record(en_rec: dict, az_rec: dict, lang: str) -> tuple[dict | None, str]:
    """(patched_record_or_None, status). status in
    {"unchanged", "patched", "flagged:<reason>"}."""
    _, az_labels_all = sentinelize(az_rec["text"], az_rec["entities"])
    src_values = entity_source_values(az_rec["text"], az_rec["entities"])
    if not repeat_groups(az_labels_all, src_values):
        return None, "unchanged"          # no repeat mentions -- nothing to check

    seed = f"{az_rec['id']}|{lang}"
    old_vals = independent_mint_values(az_labels_all, lang, seed)
    new_vals = mint_values(az_labels_all, src_values, lang, seed)
    if all(old_vals[i] == new_vals[i] for i in old_vals):
        return None, "unchanged"          # coincidentally already consistent

    en_entities = sorted(en_rec["entities"], key=lambda e: (e["start"], e["end"]))
    mapping = match_slots_to_entities(en_entities, en_rec["text"],
                                      az_labels_all, old_vals)
    if mapping is None:
        return None, "flagged:slot_reconstruction_failed"

    en_text = en_rec["text"]
    templated_en, en_labels = sentinelize(en_text, en_entities)

    def final_value(rank: int) -> str:
        slot = mapping[rank]
        return new_vals[slot]

    try:
        patched_text, spans = splice(templated_en, final_value)
    except SlotError as exc:
        return None, f"flagged:splice_failed:{exc}"

    placed = sorted(
        ({"start": s["start"], "end": s["end"], "label": en_labels[s["slot"]]}
         for s in spans), key=lambda e: (e["start"], e["end"]))

    patched = dict(en_rec)
    patched["text"] = patched_text
    patched["entities"] = placed

    # Direct safety net, not trust-the-construction: every AZ repeat-group,
    # followed through the reconstructed mapping into the patched EN text,
    # must now hold one value.
    rank_of_slot = {slot: rank for rank, slot in mapping.items()}
    span_of_rank = {s["slot"]: s for s in spans}
    for group in repeat_groups(az_labels_all, src_values).values():
        vals = {patched_text[span_of_rank[rank_of_slot[slot]]["start"]:
                             span_of_rank[rank_of_slot[slot]]["end"]]
                for slot in group if slot in rank_of_slot}
        if len(vals) > 1:
            return None, "flagged:post_patch_group_inconsistent"

    ok, reason = validate_patch(patched, az_labels_all, lang)
    if not ok:
        return None, f"flagged:post_patch_validation:{reason}"

    unchanged = (patched_text == en_text and placed == en_entities)
    return patched, ("unchanged" if unchanged else "patched")


def validate_patch(rec: dict, az_labels: list[str], lang: str) -> tuple[bool, str]:
    text, entities = rec["text"], rec["entities"]
    if len(entities) != len(az_labels):
        return False, "entity_count"
    prev = -1
    for e in entities:
        if not (0 <= e["start"] < e["end"] <= len(text)):
            return False, "span_out_of_range"
        if e["start"] < prev:
            return False, "spans_overlap"
        prev = e["end"]
    if SENTINEL_RE.search(text):
        return False, "sentinel_survived"
    if _leftover_azerbaijani(text, entities):
        return False, "leftover_azerbaijani"
    if unicodedata.normalize("NFC", text) != text:
        return False, "not_nfc"
    if any(c in ZERO_WIDTH for c in text):
        return False, "zero_width"
    mod = ANCHOR_MODULES.get(lang)
    if mod and mod.anchor_failures(text, entities):
        return False, "anchor_missing"
    return True, ""


def run(lang: str, docs_path: Path, az_path: Path, out_path: Path,
       dry_run: bool) -> int:
    az = {json.loads(l)["id"]: json.loads(l) for l in az_path.open(encoding="utf-8")
          if l.strip()}
    docs = [json.loads(l) for l in docs_path.open(encoding="utf-8") if l.strip()]

    status_counts = Counter()
    flagged: list[tuple[str, str]] = []
    out_records = []
    for r in docs:
        src = az.get(r["source_id"])
        if src is None:
            status_counts["flagged:no_az_source"] += 1
            flagged.append((r["id"], "no_az_source"))
            out_records.append(r)
            continue
        patched, status = repair_record(r, src, lang)
        status_counts[status.split(":")[0]] += 1
        if status.startswith("flagged"):
            flagged.append((r["id"], status))
            out_records.append(r)             # keep original untouched
        elif status == "patched":
            out_records.append(patched)
        else:
            out_records.append(r)

    print(f"{docs_path.name}: {len(docs)} docs")
    for k, v in status_counts.most_common():
        print(f"  {k:<10} {v}")
    if flagged:
        print(f"  flagged records (left untouched):")
        for id_, why in flagged[:30]:
            print(f"    {id_}: {why}")
        if len(flagged) > 30:
            print(f"    ... and {len(flagged) - 30} more")

    if dry_run:
        print("  (dry run -- nothing written)")
        return 0

    if status_counts["patched"] == 0:
        print("  nothing to write (no patches)")
        return 0

    new_path = out_path.with_name(out_path.stem + ".new.jsonl")
    with new_path.open("w", encoding="utf-8") as f:
        for r in out_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # verify the new file line-for-line against the intended output before
    # touching the original
    check = [json.loads(l) for l in new_path.open(encoding="utf-8") if l.strip()]
    if len(check) != len(docs):
        print(f"  ABORT: line count mismatch {len(check)} != {len(docs)}, "
              f"not swapping in {new_path}", file=sys.stderr)
        return 1

    bak_path = out_path.with_name(out_path.stem + ".prerepair_bak.jsonl")
    if out_path.exists() and not bak_path.exists():
        out_path.replace(bak_path)
    elif out_path.exists():
        out_path.unlink()
    new_path.replace(out_path)
    print(f"  wrote {out_path} ({status_counts['patched']} patched, "
         f"backup at {bak_path.name})")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lang", required=True, choices=["en", "tr", "ru"])
    ap.add_argument("--split", choices=["train", "val", "test"])
    ap.add_argument("--input", type=Path)
    ap.add_argument("--az", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if bool(args.split) == bool(args.input):
        print("error: pass exactly one of --split or (--input + --az + --out)",
              file=sys.stderr)
        return 1
    if args.split:
        docs_path = PROCESSED / args.lang / f"{args.split}.docs.jsonl"
        az_path = PROCESSED / "az" / f"{args.split}.docs.jsonl"
        out_path = docs_path
    else:
        if not (args.az and args.out):
            print("error: --input needs --az and --out", file=sys.stderr)
            return 1
        docs_path, az_path, out_path = args.input, args.az, args.out

    for p in (docs_path, az_path):
        if not p.exists():
            print(f"error: {p} not found", file=sys.stderr)
            return 1
    return run(args.lang, docs_path, az_path, out_path, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
