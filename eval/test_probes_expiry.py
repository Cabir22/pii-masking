"""Tests for eval/probes/build_probes_expiry.py (card_expiry, D-78).

Run:  python eval/test_probes_expiry.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / "probes")]

import build_probes_expiry as B  # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond, name, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(f"{name}: {detail!r}" if detail is not None else name)


rows = B.build(78)
committed = [json.loads(l) for l in (HERE / "probes" / "card_expiry.jsonl").read_text(encoding="utf-8").splitlines()]
check(rows == committed, "the committed file is what the builder makes (seed 78)")
check(len(rows) == 90, "90 documents", len(rows))
check(B.check(rows) == [], "builder's own checks", B.check(rows)[:3])
cells = Counter(e["cell"] for x in rows for e in x["entities"] if "cell" in e)
check(len(cells) == 6 and set(cells.values()) == {15}, "6 cells of 15 expiries", cells)
check(all("cell" not in e for x in rows for e in x["entities"] if e["label"] != "DATE"),
      "only the expiry carries slice fields, so the slices are about the expiry")
check(all(x["role"] == e["cell"] for x in rows for e in x["entities"] if "cell" in e), "role = cell")

for x in rows:
    t = x["text"]
    e = next(s for s in x["entities"] if s["label"] == "DATE")
    v = t[e["start"]:e["end"]]
    check(bool(re.fullmatch(r"(0[1-9]|1[0-2])/\d{2}", v)) == (e["form"] == "MM/YY"), f"{x['id']}: form matches the value", v)
    check(not t[e["end"]:e["end"] + 1].isalnum() and not t[e["start"] - 1:e["start"]].isalnum(),
          f"{x['id']}: the expiry stands alone (no glued letters or digits)", v)
    if e["layout"] == "record":
        check(any(s["label"] == "CARD_SECURITY_CODE" for s in x["entities"]), f"{x['id']}: records carry a CVV")
    for c in x.get("controls", []):
        n = t[c["start"]:c["end"]]
        check(int(n.split("/")[0]) > 12, f"{x['id']}: control {n} cannot be a month")
check(sum(len(x.get("controls", [])) for x in rows) == 30, "30 NN/NN controls")
check(len({x["text"] for x in rows}) == 90, "no two documents alike")

tg = json.loads((HERE / "probes" / "targets.json").read_text(encoding="utf-8"))["card_expiry"]
check([(c["metric"], c.get("labels"), c.get("field"), c["op"], c["value"]) for c in tg["conditions"]] ==
      [("exact_recall", ["DATE"], None, ">=", 0.9), ("slice_exact_recall_min", None, "cell", ">=", 0.8),
       ("control_fp_rate", None, None, "<", 0.1)], "targets (D-78)")


if __name__ == "__main__":
    print(f"{PASS} passed, {FAIL} failed")
    for f in FAILURES:
        print("  FAIL", f)
    sys.exit(1 if FAIL else 0)
