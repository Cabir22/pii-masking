"""Recover repair-queue records using the raw output already on disk --
zero API calls.

A repair-queue entry saves `output`: the model's response from its LAST
attempt, already zero-width-stripped, from the point it passed
`check_round_trip` (i.e. translation succeeded; only splice/validate is
worth re-trying). If a record failed there because of a VALIDATOR BUG (not a
translation-quality problem -- e.g. the entity_count miscount fixed
2026-09-05), re-running today's validate_record against that same saved
output recovers it for free.

Only attempts entries whose last recorded failure was "validator: ..." --
those are exactly the ones that have a usable saved `output`. Entries that
failed earlier (dropped slots, SIMURG abort, call failure) never reached
splice/validate and have no output to replay; they still need a real retry.

Run:
    python scripts/translate/recover_from_repair_queue.py --lang en --split train
    python scripts/translate/recover_from_repair_queue.py --lang en --split train --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from translate.run import (PROCESSED, entity_source_values, mint_values,  # noqa: E402
                           out_paths)
from translate.sentinel import (SlotError, check_round_trip,  # noqa: E402
                                sentinelize_protected, splice)
from translate.validate import (inherited_leak_exemptions,  # noqa: E402
                                validate_record)


def try_recover(entry: dict, az: dict, lang: str) -> dict | None:
    if not entry["reason"].startswith("validator:"):
        return None
    output = entry.get("output", "")
    if not output:
        return None

    src_id = az["id"]
    decoys = (az.get("_spec") or {}).get("hard_negatives") or []
    templated, slots = sentinelize_protected(az["text"], az["entities"], decoys)
    entity_slots = [i for i, s in enumerate(slots) if s["kind"] == "entity"]
    labels = [slots[i]["label"] for i in entity_slots]
    source_values = [slots[i]["value"] for i in entity_slots]
    n = len(slots)

    ok, _ = check_round_trip(output, n)
    if not ok:
        return None   # slot set on the saved output no longer matches
                      # today's protected sentinelizing -- needs a real retry

    entity_values = mint_values(labels, source_values, lang, f"{src_id}|{lang}")
    by_slot: dict[int, str] = {}
    group_value: dict[tuple[str, str], str] = {}
    for k, slot_i in enumerate(entity_slots):
        by_slot[slot_i] = entity_values[k]
        group_value[(labels[k], source_values[k])] = entity_values[k]
    for i, s in enumerate(slots):
        if s["kind"] == "decoy":
            by_slot[i] = s["value"]
        elif s["kind"] == "shadow":
            by_slot[i] = group_value.get((s["label"], s["value"]), s["value"])

    try:
        final_text, spans = splice(output, lambda i: by_slot[i])
    except SlotError:
        return None

    placed = sorted(
        ({"start": sp["start"], "end": sp["end"],
          "label": slots[sp["slot"]]["label"], "_val": by_slot[sp["slot"]]}
         for sp in spans if slots[sp["slot"]]["kind"] == "entity"),
        key=lambda e: (e["start"], e["end"]))
    entities = [{k: v for k, v in e.items() if k != "_val"} for e in placed]
    minted_by_pos = {i: e["_val"] for i, e in enumerate(placed)}

    out = {
        "id": f"{src_id}__{lang}", "source_id": src_id, "lang": lang,
        "split": entry.get("split", az.get("_split", "")),
        "text": final_text, "entities": entities,
        "_bucket": az.get("_bucket"), "_register": az.get("_register"),
    }
    report = validate_record(out, source_text=az["text"], templated=templated,
                             minted=minted_by_pos, decoys=decoys,
                             source_values=source_values,
                             expected_entities=len(entity_slots),
                             inherited_leak_domains=inherited_leak_exemptions(
                                 az["text"], az["entities"], lang),
                             guard_state="clean")
    if not report.ok:
        return None
    return out


def run(lang: str, docs_path: Path, repair_path: Path, az_path: Path,
       dry_run: bool) -> int:
    az = {json.loads(l)["id"]: json.loads(l) for l in az_path.open(encoding="utf-8")
          if l.strip()}

    # The repair queue is append-only across --resume runs and was, until
    # 2026-09-05, never pruned when a source_id later succeeded -- so it can
    # hold stale duplicates. Latest entry per source_id wins, and anything
    # already sitting in docs.jsonl (a prior run or --resume recovered it
    # since) is dropped outright rather than risking a second copy.
    already_done: set[str] = set()
    if docs_path.exists():
        for line in docs_path.open(encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    already_done.add(json.loads(line)["source_id"])
                except json.JSONDecodeError:
                    continue

    latest: dict[str, dict] = {}
    raw_count = 0
    for line in repair_path.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        raw_count += 1
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        latest[e["source_id"]] = e
    entries = [e for sid, e in latest.items() if sid not in already_done]
    if raw_count != len(entries):
        print(f"  (queue had {raw_count} raw lines, {len(latest)} distinct "
             f"source_ids, {len(entries)} not already in {docs_path.name})")

    recovered, unrecoverable = [], []
    seen_this_pass: set[str] = set()
    for e in entries:
        if e["source_id"] in seen_this_pass:
            continue                      # belt-and-braces; latest{} already dedupes
        seen_this_pass.add(e["source_id"])
        src = az.get(e["source_id"])
        if src is None:
            unrecoverable.append(e)
            continue
        r = try_recover(e, src, lang)
        (recovered if r else unrecoverable).append(r or e)

    print(f"{repair_path.name}: {len(entries)} in queue")
    print(f"  recoverable from saved output (no API call): {len(recovered)}")
    print(f"  still need a real retry:                     {len(unrecoverable)}")

    if dry_run:
        return 0

    # Always rewrite the repair queue, even with zero recoveries: `entries`
    # is already deduplicated-by-source_id and stale-filtered against
    # docs.jsonl, and that cleanup is worth keeping regardless of whether
    # anything new got recovered this pass.
    if recovered:
        with docs_path.open("a", encoding="utf-8") as f:
            for r in recovered:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"  appended {len(recovered)} to {docs_path}")
    with repair_path.open("w", encoding="utf-8") as f:
        for e in unrecoverable:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"  {repair_path} now holds {len(unrecoverable)}"
         + ("" if raw_count == len(unrecoverable) + len(recovered)
            else f" (was {raw_count} raw lines before dedup/cleanup)"))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lang", required=True)
    ap.add_argument("--split", choices=["train", "val", "test"])
    ap.add_argument("--docs", type=Path)
    ap.add_argument("--repair", type=Path)
    ap.add_argument("--az", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if args.split:
        docs_path, repair_path = out_paths(args.lang, args.split)
        az_path = PROCESSED / "az" / f"{args.split}.docs.jsonl"
    else:
        if not (args.docs and args.repair and args.az):
            print("error: pass --split, or --docs/--repair/--az", file=sys.stderr)
            return 1
        docs_path, repair_path, az_path = args.docs, args.repair, args.az

    for p in (repair_path, az_path):
        if not p.exists():
            print(f"error: {p} not found", file=sys.stderr)
            return 1
    return run(args.lang, docs_path, repair_path, az_path, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
