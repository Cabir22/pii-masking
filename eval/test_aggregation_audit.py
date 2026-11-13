"""Tests for eval/aggregation_audit.py's scoring (no model, no tokenizer).

    python eval/test_aggregation_audit.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aggregation_audit import DECODES, render_md, score, splits  # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond, name, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(f"{name}  {detail!r}"[:300])


g = {"label": "TELEPHONENUM", "start": 5, "end": 22}          # "+994 50 123 45 67"
doc = {"id": "a", "text": "Tel: +994 50 123 45 67.", "gold": [g], "decoys": [], "control": False,
       "controls": [], "meta": {}}

# one exact span: no split, no boundary error, nothing leaked
s = score([{**doc, "pred": [dict(g)]}])
check(s["exact"]["f1"] == 1.0 and s["split"]["split"] == 0 and s["leak_rate"] == 0.0
      and s["boundary"]["n"] == 0, "an exact span is a clean hit", s)

# the value as two same-label pieces: a split, two narrower boundary errors, a leaked space
two = [{"label": "TELEPHONENUM", "start": 5, "end": 12}, {"label": "TELEPHONENUM", "start": 13, "end": 22}]
s = score([{**doc, "pred": two}])
check(s["split"] == {"gold": 1, "split": 1, "rate": 1.0, "pieces": 2, "per_label": {"TELEPHONENUM": 1}},
      "two same-label pieces are one split value", s["split"])
check(s["exact"]["f1"] == 0.0 and s["overlap"]["f1"] == 1.0, "split: exact miss, overlap hit", s)
check(s["boundary"]["narrower"] == 2, "split: both pieces are narrower", s["boundary"])
check(0 < s["leak_rate"] < 0.1, "split: only the gap leaks", s["leak_rate"])

# a piece of another label does not count as a split piece
mixed = [two[0], {"label": "PAYMENT_CARD_NUMBER", "start": 13, "end": 22}]
check(splits([{**doc, "pred": mixed}])["split"] == 0, "pieces of another label are not a split")

# cut short (`Fidan.` -> `dan`): narrower, leaks, not a split
f = {"id": "b", "text": "Fidan.", "gold": [{"label": "GIVENNAME", "start": 0, "end": 5}],
     "decoys": [], "control": False, "controls": [], "meta": {}}
s = score([{**f, "pred": [{"label": "GIVENNAME", "start": 2, "end": 5}]}])
check(s["boundary"]["narrower"] == 1 and s["split"]["split"] == 0
      and abs(s["leak_rate"] - 0.4) < 1e-9, "a cut-short name: narrower, 2 of 5 characters leak", s)

# the report renders every decode
res = {"overall": {n: score([{**doc, "pred": [dict(g)]}]) for n in DECODES},
       "per_family": {"spaced_phone": {n: score([{**doc, "pred": two}]) for n in DECODES}}}
md = render_md(res, {"model": "m", "revision": "r" * 40, "git": "g" * 40, "families": ["spaced_phone"],
                     "n_probe_docs": 1, "n_golden": 0})
check(all(f"`{n}`" in md for n in DECODES) and "spaced_phone" in md, "report lists every decode")

print(f"{PASS} passed, {FAIL} failed")
for x in FAILURES:
    print("  FAIL", x)
sys.exit(1 if FAIL else 0)
