"""D-33a: dashed CVVs become labelled; FIN look-alikes with I or O are dropped.

WHY
---
D-30b: Run B found 4 of the benchmark's 80 dashed CVVs (`12-3`). Its data had
none as values and ~250 in the LLM batches declared as look-alikes (kind
`cvv_separator`), so it learned that a dashed CVV is not PII. A dash is a
real CVV now (`checksums.card_security_code_valid`, part 1), and D-33a turns
those look-alikes into labelled CVVs, deterministically, as D-17 did for
dates. They already sit beside a CVV anchor: each was planted in one.

D-33c drops the look-alike kind `fin_with_i_or_o` (a 7-character FIN with an
I or O): that FINs exclude I and O is not established, so such a look-alike
may be a real FIN. The LLM documents that carry one are dropped (D-33a).

WHAT CHANGES
------------
* A `cvv_separator` look-alike whose text is a valid CVV (one dash, digits
  around it) leaves `_decoys` and becomes a CARD_SECURITY_CODE entity. It is
  kept only if the record then fails no gate it passed before
  (`relabel_standalone_dates.gate_state`: repeat mentions, resolver drift,
  span boundaries, the CVV anchor, `validate_example`); otherwise it stays a
  look-alike and is counted. Slashed and dotted look-alikes are untouched.
* A record with a `fin_with_i_or_o` look-alike is dropped.
* A record that gains its first entity is no longer `_pii_free`.

Text is never changed; an untouched record is written back byte for byte.

Run:
  python scripts/relabel_dashed_cvv.py --batch data/raw/sprint1_llm_b1.clean.jsonl --in-place
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

from piigen.checksums import card_security_code_valid                     # noqa: E402
from piigen.validate import declared_decoy_spans                          # noqa: E402
from relabel_standalone_dates import gate_state, no_new_failure           # noqa: E402

DROPPED_KINDS = ("fin_with_i_or_o",)       # D-33c; --drop-kind adds more (D-34b)


def relabel(rec: dict) -> tuple[list[dict], int]:
    """(CVV entities added, dashed look-alikes left because a gate objected)."""
    text = rec["text"]
    dashed = [d for d in rec.get("_decoys") or []
              if d.get("kind") == "cvv_separator" and "-" in text[d["start"]:d["end"]]
              and card_security_code_valid(text[d["start"]:d["end"]])]
    if not dashed:
        return [], 0
    ents = rec.get("entities") or []
    before = gate_state(rec, ents, declared_decoy_spans(rec)[0], True)
    kept, left = [], 0
    remaining = list(rec["_decoys"])
    for d in dashed:
        add = {"start": d["start"], "end": d["end"], "label": "CARD_SECURITY_CODE",
               "text": text[d["start"]:d["end"]]}
        trial = {**rec, "_decoys": [x for x in remaining if x is not d]}
        if no_new_failure(before, gate_state(trial, ents + kept + [add],
                                             declared_decoy_spans(trial)[0], True)):
            kept.append(add)
            remaining = trial["_decoys"]
        else:
            left += 1
    return kept, left


def process(lines, stats: Counter, examples: list, n_examples: int, dropped=DROPPED_KINDS):
    for line in lines:
        rec = json.loads(line)
        stats["documents in"] += 1
        hit = next((d["kind"] for d in rec.get("_decoys") or [] if d.get("kind") in dropped), None)
        if hit:
            stats[f"documents dropped ({hit})"] += 1
            continue
        kept, left = relabel(rec)
        stats["dashed CVV look-alikes left (a gate objected)"] += left
        if kept:
            spans = {(k["start"], k["end"]) for k in kept}
            rec["_decoys"] = [d for d in rec["_decoys"] if (d["start"], d["end"]) not in spans]
            rec["entities"] = sorted((rec.get("entities") or []) + kept, key=lambda e: e["start"])
            if rec.get("_pii_free") is True:
                rec["_pii_free"] = False
                stats["documents no longer PII-free"] += 1
            stats["documents changed"] += 1
            stats["CVVs labelled"] += len(kept)
            if len(examples) < n_examples:
                k = kept[0]
                examples.append(rec["text"][max(0, k["start"] - 40):k["end"] + 15].replace("\n", " "))
            line = json.dumps(rec, ensure_ascii=False) + "\n"
        stats["documents out"] += 1
        yield line


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch", type=Path, required=True, help="one LLM batch file (.jsonl)")
    ap.add_argument("--out", type=Path, help="write the result here")
    ap.add_argument("--in-place", action="store_true", help="rewrite the file")
    ap.add_argument("--report", type=Path, help="write the counts as JSON")
    ap.add_argument("--examples", type=int, default=5)
    ap.add_argument("--drop-kind", action="append", default=[],
                    help="also drop documents carrying a look-alike of this kind (e.g. fin_6_chars, D-34b)")
    args = ap.parse_args(argv)

    stats, examples = Counter(), []
    dropped = DROPPED_KINDS + tuple(args.drop_kind)
    dst = args.batch if args.in_place else args.out
    tmp = dst.with_name(dst.name + ".tmp") if dst else None
    with args.batch.open(encoding="utf-8") as fh, \
            (tmp.open("w", encoding="utf-8", newline="") if tmp else open(os.devnull, "w", encoding="utf-8")) as out:
        for line in process(fh, stats, examples, args.examples, dropped):
            out.write(line)
    if tmp:
        os.replace(tmp, dst)

    for k in ("documents in", *(f"documents dropped ({k})" for k in dropped), "documents out",
              "documents changed", "CVVs labelled", "dashed CVV look-alikes left (a gate objected)",
              "documents no longer PII-free"):
        print(f"{k}: {stats[k]:,}")
    for ex in examples:
        print("  e.g.", ex)
    if args.report:
        args.report.write_text(json.dumps({"stats": stats, "examples": examples},
                                          ensure_ascii=False, indent=1), encoding="utf-8")
    if not (args.out or args.in_place):
        print("(report only -- pass --in-place or --out to write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
