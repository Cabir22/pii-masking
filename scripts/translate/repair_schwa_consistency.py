"""Patch GIVENNAME/SURNAME schwa-fold disagreement in an already-translated
Turkish corpus.

Background: `render.py`'s `_tr_name()` used to roll an independent
Bernoulli(TR_KEEP_SCHWA_RATE) decision on every call, with no idea that a
document's names should share one keep/fold convention (a document is either
"pasted from an ID/database export" -- every name keeps its schwa -- or
ordinary Turkish prose -- every name folds; a document mixing both looks like
two transcription sources spliced together). Two independent draws disagree
2*p*(1-p) of the time -- confirmed empirically at 20.8% for p=0.12. Fixed by
making the decision once per document (see `_tr_name`'s docstring). This
script repairs documents translated with the OLD, per-call mechanism --
without calling the API again.

Only Turkish is affected: EN/RU never had a `_tr_name`-shaped decision.

How a repair works, per document:
  1. Reconstruct what the OLD code minted (independent per-call schwa
     rolls, held under the ALREADY-SHIPPED repeat-mention grouping -- that
     fix landed first and is not what this script is repairing) and what
     the FIXED code mints (one decision per document). If every GIVENNAME/
     SURNAME slot agrees, nothing to change.
  2. Otherwise, recover which written entity came from which slot: match by
     (label, value) between the OLD reconstruction and the entities
     actually on disk, requiring a PERFECT multiset match -- if it is not
     one, the document is FLAGGED, never guessed at.
  3. Re-sentinelize the translated text (its own entities, in their own
     on-disk position order), substitute the corrected value at every slot
     that needs to change, and splice -- the same mechanism that built the
     corpus, so offsets are exact by construction.
  4. Re-validate the patched record with the same checks translation output
     already goes through.

Usage:
    python scripts/translate/repair_schwa_consistency.py \
        --input data/processed/tr/calibration_sample.tr.docs.jsonl \
        --az data/processed/tr/calibration_sample.docs.jsonl \
        --out data/processed/tr/calibration_sample.tr.docs.jsonl
    ... --dry-run to preview without writing

Writes to `<out>.new.jsonl` first, verifies it, then swaps it into place and
keeps the pre-repair file as `<out>.preschwarepair_bak.jsonl`.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from translate.lang import ANCHORS  # noqa: E402
from translate.lang.tr.render import TR_KEEP_SCHWA_RATE, tr_translit  # noqa: E402
from translate.render import RENDERERS  # noqa: E402
from translate.run import mint_values  # noqa: E402
from translate.sentinel import SENTINEL_RE, SlotError, entity_source_values  # noqa: E402
from translate.sentinel import sentinelize, splice  # noqa: E402
from translate.validate import _leftover_azerbaijani  # noqa: E402

ANCHOR_MODULES = {"tr": ANCHORS["tr"]}
ZERO_WIDTH = set("​‌‍⁠﻿")
NAME_LABELS = {"GIVENNAME", "SURNAME"}


def _old_tr_name(value: str, rng: random.Random) -> str:
    """The ORIGINAL (pre-schwa-consistency-fix) _tr_name -- one independent
    roll per call. Kept ONLY so this script can reconstruct, byte-for-byte,
    what an already-translated document's name values were minted from.
    """
    if rng.random() < TR_KEEP_SCHWA_RATE:
        return value
    return tr_translit(value)


def _mint_with_name_fn(labels, source_values, seed, name_fn):
    """mint_values(), but with RENDERERS["tr"].name_fn swapped for the
    duration of the call. Not thread-safe (module-level mutation) -- this
    script processes one file sequentially, same as repair_repeat_mentions.py.
    """
    tr_renderer = RENDERERS["tr"]
    orig = tr_renderer.name_fn
    tr_renderer.name_fn = name_fn
    try:
        return mint_values(labels, source_values, "tr", seed)
    finally:
        tr_renderer.name_fn = orig


def match_slots_to_entities(entities: list[dict], text: str,
                            labels: list[str], old_values: dict[int, str]):
    """Recover slot -> entity-index for the NAME-labeled slots only (the
    only ones this bug can affect). None on any ambiguity -- never guess."""
    name_slots = [i for i, lab in enumerate(labels) if lab in NAME_LABELS]
    want = Counter((labels[i], old_values[i]) for i in name_slots)
    name_entities = [e for e in entities if e["label"] in NAME_LABELS]
    have = Counter((e["label"], text[e["start"]:e["end"]]) for e in name_entities)
    if want != have:
        return None
    remaining = defaultdict(list)
    for i in name_slots:
        remaining[(labels[i], old_values[i])].append(i)
    mapping: dict[int, int] = {}       # entity-index (into `entities`) -> slot
    for idx, e in enumerate(entities):
        if e["label"] not in NAME_LABELS:
            continue
        key = (e["label"], text[e["start"]:e["end"]])
        pool = remaining.get(key)
        if not pool:
            return None
        mapping[idx] = pool.pop(0)
    return mapping


def repair_record(rec: dict, az_rec: dict) -> tuple[dict | None, str]:
    """(patched_record_or_None, status). status in
    {"unchanged", "patched", "flagged:<reason>"}."""
    templated, labels = sentinelize(az_rec["text"], az_rec["entities"])
    source_values = entity_source_values(az_rec["text"], az_rec["entities"])
    if not any(lab in NAME_LABELS for lab in labels):
        return None, "unchanged"          # no names -- nothing to check

    seed = f"{az_rec['id']}|tr"
    old_vals = _mint_with_name_fn(labels, source_values, seed, _old_tr_name)
    new_vals = mint_values(labels, source_values, "tr", seed)  # current, fixed
    name_slots = [i for i, lab in enumerate(labels) if lab in NAME_LABELS]
    if all(old_vals[i] == new_vals[i] for i in name_slots):
        return None, "unchanged"          # coincidentally already consistent

    entities = sorted(rec["entities"], key=lambda e: (e["start"], e["end"]))
    mapping = match_slots_to_entities(entities, rec["text"], labels, old_vals)
    if mapping is None:
        return None, "flagged:slot_reconstruction_failed"

    text = rec["text"]
    templated_tr, tr_labels = sentinelize(text, entities)
    # sentinelize assigns slot i to entities[i] (both sorted left-to-right
    # by the same key), so "slot" and "index into `entities`" coincide here.

    # Build the splice function directly from entity index -> corrected value.
    corrected_value_by_entity_idx: dict[int, str] = {}
    for entity_idx, slot in mapping.items():
        corrected_value_by_entity_idx[entity_idx] = new_vals[slot]

    def splice_value(slot: int) -> str:
        # slot here is the position in `entities` (sentinelize assigns
        # slots 0..n-1 in the same left-to-right order `entities` is in).
        if slot in corrected_value_by_entity_idx:
            return corrected_value_by_entity_idx[slot]
        return text[entities[slot]["start"]:entities[slot]["end"]]

    try:
        patched_text, spans = splice(templated_tr, splice_value)
    except SlotError as exc:
        return None, f"flagged:splice_failed:{exc}"

    placed = sorted(
        ({"start": s["start"], "end": s["end"], "label": tr_labels[s["slot"]]}
         for s in spans), key=lambda e: (e["start"], e["end"]))

    patched = dict(rec)
    patched["text"] = patched_text
    patched["entities"] = placed

    # Direct safety net: every NAME slot's group must now agree with every
    # other NAME slot's group in the SAME document (this bug's whole point).
    span_of_slot = {s["slot"]: s for s in spans}
    kept_flags = set()
    for i in name_slots:
        entity_idx = [k for k, v in mapping.items() if v == i]
        if entity_idx:
            sp = span_of_slot[entity_idx[0]]
            val = patched_text[sp["start"]:sp["end"]]
            src_val = source_values[i]
            # "kept" iff the value equals its own pre-fold source value
            # (schwa-bearing) or trivially both-empty-of-schwa (ambiguous
            # but harmless -- consistency, not detection, is the property
            # under test).
            kept_flags.add(val == src_val)
    if len(kept_flags) > 1:
        return None, "flagged:post_patch_still_inconsistent"

    ok, reason = validate_patch(patched, labels)
    if not ok:
        return None, f"flagged:post_patch_validation:{reason}"

    unchanged = (patched_text == text and placed == entities)
    return patched, ("unchanged" if unchanged else "patched")


def validate_patch(rec: dict, az_labels: list[str]) -> tuple[bool, str]:
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
    if ANCHORS["tr"].anchor_failures(text, entities):
        return False, "anchor_missing"
    return True, ""


def run(docs_path: Path, az_path: Path, out_path: Path, dry_run: bool) -> int:
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
        patched, status = repair_record(r, src)
        status_counts[status.split(":")[0]] += 1
        if status.startswith("flagged"):
            flagged.append((r["id"], status))
            out_records.append(r)
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

    check = [json.loads(l) for l in new_path.open(encoding="utf-8") if l.strip()]
    if len(check) != len(docs):
        print(f"  ABORT: line count mismatch {len(check)} != {len(docs)}, "
              f"not swapping in {new_path}", file=sys.stderr)
        return 1

    bak_path = out_path.with_name(out_path.stem + ".preschwarepair_bak.jsonl")
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
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--az", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    for p in (args.input, args.az):
        if not p.exists():
            print(f"error: {p} not found", file=sys.stderr)
            return 1
    return run(args.input, args.az, args.out, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
