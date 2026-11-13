"""Label the standalone dates our data left unlabelled (D-17).

WHY
---
D-17 follows the benchmark: every standalone date is DATE, including a
document's own date after `Tarix:`/`tarixi`; a date followed by a time (a
log or record timestamp) is not. Our generator asked for "incidental" dates
and left them unlabelled, so the data taught the opposite: in the old
corpus's Azerbaijani LLM documents a `Tarix:` date is unlabelled 24,597
times against 8,255 labelled, and half of the cleaned LLM batches carry one.
An unlabelled date beside a labelled one is a counter-example, the
false-negative lesson a masking model must not learn (benchmark DATE F1 56.9).

WHAT IS LABELLED
----------------
`piigen.standalone_dates` decides, the same definition generation now
enforces: a real calendar date with day, month and a 4-digit year (numeric,
ISO or worded, in az/tr/en/ru), not inside a longer token, not next to a
clock time. A span is added only if it passes, on its own, every check the
gates apply to a DATE span (valid value, anchor or self-signalling shape,
not a structural number, re-placed exactly by the resolver).

Then the whole record is checked with the per-record gates a new label can
change (`validate_corpus`'s repeat-mention, resolver-drift, span-boundary and
anchor checks, and for LLM batch records `validate_example`): the record must
fail nothing it did not fail before. If a new date would break one -- almost
always the same date string written a second time inside a timestamp, which
the repeat-mention check would then demand be labelled too -- that date is
left alone and counted, never forced.

Deterministic: same input, same output. Text is never changed; a record
gaining no label is written back byte for byte.

Run:
  python scripts/relabel_standalone_dates.py --batch data/raw/sprint1_llm_b2.clean.jsonl --in-place
  python scripts/relabel_standalone_dates.py --data-dir data/processed/merged_relabeled_swept \\
      --out data/processed/merged_relabeled_swept_dated
Without --in-place/--out it only reports.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.anchors import ANCHOR_REQUIRED, has_anchor                  # noqa: E402
from piigen.resolver import find_unlabeled_repeats, resolve_claims      # noqa: E402
from piigen.standalone_dates import find_unlabelled_dates, is_timestamp  # noqa: E402
from piigen.validate import (declared_decoy_spans, span_boundary_problems,  # noqa: E402
                             validate_example)

SPLITS = ("train", "val", "test")


def _with_text(text: str, ents: list[dict]) -> list[dict]:
    """The old corpus stores `text` on only half of its entities."""
    return [e if "text" in e else {**e, "text": text[e["start"]:e["end"]]} for e in ents]


def gate_state(rec: dict, ents: list[dict], decoys, full: bool):
    """What the per-record gates say about `rec` with entities `ents`."""
    text = rec["text"]
    ents = _with_text(text, ents)
    reclaimed, _ = resolve_claims(text, [{"label": e["label"], "text": e["text"]} for e in ents],
                                  blocked=decoys)
    drift = ({(e["start"], e["end"], e["label"]) for e in reclaimed}
             ^ {(e["start"], e["end"], e["label"]) for e in ents})
    state = {
        "repeats": find_unlabeled_repeats(text, ents, exempt=decoys),
        "drift": frozenset(drift),
        "boundary": len(span_boundary_problems(text, ents)),
        "anchor": sum(1 for e in ents if e["label"] in ANCHOR_REQUIRED
                      and not has_anchor(e["label"], text, e["start"], e["end"])),
    }
    if full:
        state["validator"] = len(validate_example({**rec, "entities": ents}))
    return state


def no_new_failure(before: dict, after: dict) -> bool:
    return all((after[k] <= before[k]) for k in before)      # drift: a subset


def relabel(rec: dict, full: bool) -> tuple[list[dict], list[dict], Counter, list[dict]]:
    """(DATE spans added, standalone dates left unlabelled, why each was left,
    DATE labels removed because they sit inside a timestamp)."""
    text = rec["text"]
    original = rec.get("entities") or []
    # D-17: a date with a clock time is a timestamp, never DATE. The old
    # corpus labels 181 of them; today's resolver would not place them.
    removed = [e for e in original if e["label"] == "DATE" and is_timestamp(text, e["start"], e["end"])]
    ents = [e for e in original if e not in removed]
    decoys, _ = declared_decoy_spans(rec)
    found = find_unlabelled_dates(text, _with_text(text, ents), decoys)
    why = Counter(f["why_not"] for f in found if f["why_not"])
    adds = [{"start": f["start"], "end": f["end"], "label": "DATE", "text": f["text"]}
            for f in found if not f["why_not"]]
    if not adds:
        return [], found, why, removed
    before = gate_state(rec, original, decoys, full)
    # Drop, one at a time and in text order, any date whose label would make
    # the record fail a gate it passed before; keep the rest.
    kept = list(adds)
    if not no_new_failure(before, gate_state(rec, ents + kept, decoys, full)):
        kept = []
        for a in adds:
            if no_new_failure(before, gate_state(rec, ents + kept + [a], decoys, full)):
                kept.append(a)
            else:
                why["would fail a gate (same date in a timestamp, or drift)"] += 1
    left = [f for f in found if not any(k["start"] == f["start"] for k in kept)]
    return kept, left, why, removed


def process(lines, full: bool, stats: Counter, why_all: Counter, langs: Counter,
            examples: list, n_examples: int):
    for line in lines:
        rec = json.loads(line)
        stats["documents"] += 1
        stats["date_labels_before"] += sum(e["label"] == "DATE" for e in rec.get("entities") or [])
        kept, left, why, removed = relabel(rec, full)
        found = len(kept) + len(left)
        stats["unlabelled_dates_before"] += found
        stats["docs_with_unlabelled_before"] += bool(found)
        stats["unlabelled_dates_after"] += len(left)
        stats["docs_with_unlabelled_after"] += bool(left)
        why_all.update(why)
        if removed:
            stats["timestamp_date_labels_removed"] += len(removed)
            rec["entities"] = [e for e in rec["entities"] if e not in removed]
        if kept or removed:
            stats["docs_changed"] += 1
            stats["spans_added"] += len(kept)
            langs[rec.get("lang", "?")] += 1
            if kept and len(examples) < n_examples:
                k = kept[0]
                examples.append(rec["text"][max(0, k["start"] - 40):k["end"] + 20].replace("\n", " "))
            rec["entities"] = sorted((rec.get("entities") or []) + kept, key=lambda e: e["start"])
            line = json.dumps(rec, ensure_ascii=False) + "\n"
        stats["date_labels_after"] += sum(e["label"] == "DATE" for e in rec.get("entities") or [])
        yield line


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--batch", type=Path, help="one LLM batch file (.jsonl)")
    src.add_argument("--data-dir", type=Path, help="a corpus folder with train/val/test.docs.jsonl")
    ap.add_argument("--out", type=Path, help="write here (a file for --batch, a folder for --data-dir)")
    ap.add_argument("--in-place", action="store_true", help="--batch only: rewrite the file")
    ap.add_argument("--report", type=Path, help="write the counts as JSON")
    ap.add_argument("--examples", type=int, default=12)
    args = ap.parse_args(argv)

    stats, why, langs, examples = Counter(), Counter(), Counter(), []
    if args.batch:
        dst = args.batch if args.in_place else args.out
        tmp = dst.with_name(dst.name + ".tmp") if dst else None
        with args.batch.open(encoding="utf-8") as fh, \
                (tmp.open("w", encoding="utf-8", newline="") if tmp else open(os.devnull, "w", encoding="utf-8")) as out:
            for line in process(fh, True, stats, why, langs, examples, args.examples):
                out.write(line)
        if tmp:
            os.replace(tmp, dst)
    else:
        if args.out:
            args.out.mkdir(parents=True, exist_ok=True)
        for split in SPLITS:
            path = args.data_dir / f"{split}.docs.jsonl"
            target = args.out / path.name if args.out else None
            with path.open(encoding="utf-8") as fh, \
                    (target.open("w", encoding="utf-8", newline="") if target else open(os.devnull, "w", encoding="utf-8")) as out:
                for line in process(fh, True, stats, why, langs, examples, args.examples):
                    out.write(line)
        labels = args.data_dir / "labels.json"
        if args.out and labels.exists():
            (args.out / "labels.json").write_bytes(labels.read_bytes())

    n = stats["documents"] or 1
    print(f"documents: {stats['documents']:,}")
    print(f"DATE labels: {stats['date_labels_before']:,} -> {stats['date_labels_after']:,}")
    print(f"unlabelled standalone dates: {stats['unlabelled_dates_before']:,} in "
          f"{stats['docs_with_unlabelled_before']:,} documents "
          f"({stats['docs_with_unlabelled_before'] / n:.1%}) -> {stats['unlabelled_dates_after']:,} in "
          f"{stats['docs_with_unlabelled_after']:,} ({stats['docs_with_unlabelled_after'] / n:.1%})")
    print(f"DATE spans added: {stats['spans_added']:,}; DATE labels removed (inside a timestamp): "
          f"{stats['timestamp_date_labels_removed']:,}; documents changed: {stats['docs_changed']:,}")
    print("left unlabelled, by reason:", dict(why.most_common()))
    print("documents changed, by language:", dict(langs.most_common()))
    for ex in examples:
        print("  e.g.", ex)
    if args.report:
        args.report.write_text(json.dumps({"stats": stats, "left_by_reason": why,
                                           "changed_by_language": langs, "examples": examples},
                                          ensure_ascii=False, indent=1), encoding="utf-8")
    if not (args.out or args.in_place):
        print("(report only -- pass --in-place or --out to write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
