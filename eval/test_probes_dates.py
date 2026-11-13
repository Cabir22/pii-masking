"""Tests for eval/probes/build_probes_dates.py (date_forms_az, D-82).

Run:  python eval/test_probes_dates.py
"""
from __future__ import annotations

import datetime
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / "probes")]

import build_probes_dates as B  # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond, name, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(f"{name}: {detail!r}" if detail is not None else name)


rows = B.build(82)
committed = [json.loads(l) for l in (HERE / "probes" / "date_forms_az.jsonl").read_text(encoding="utf-8").splitlines()]
check(rows == committed, "the committed file is what the builder makes (seed 82)")
check(len(rows) == 75, "75 documents", len(rows))
check(B.check(rows) == [], "builder's own checks", B.check(rows)[:3])
cells = Counter(e["cell"] for x in rows for e in x["entities"])
check(set(cells) == set(B.CELLS) and set(cells.values()) == {15}, "5 cells of 15 dates", cells)
check(all(x["role"] == x["entities"][0]["cell"] for x in rows), "role = cell")
check(sum(len(x.get("controls", [])) for x in rows) == 25, "25 weekday-alone controls")
check(len({x["text"] for x in rows}) == 75, "no two documents alike")

# suffixes by the last number word
check([B.year_suffix(y) for y in (2023, 2020, 2010, 1990, 2000, 1900, 1964, 1959, 1986, 2025)] ==
      ["cü", "ci", "cu", "cı", "ci", "cü", "cü", "cu", "cı", "ci"], "year suffixes")
check([B._POSS[B.day_key(d)] for d in (1, 2, 3, 6, 9, 10, 15, 16, 20, 30)] == ["i", "si", "ü", "sı", "u", "u", "i", "sı", "si", "u"],
      "day possessive suffixes")
check([B._LOC[B.day_key(d)] for d in (3, 6, 9, 10, 12, 26, 30)] == ["də", "da", "da", "da", "də", "da", "da"], "day locative suffixes")

MON = {m: i + 1 for i, m in enumerate(B.MONTHS)} | {m: i + 1 for i, m in enumerate(B.MONTHS_GEN)}
for x in rows:
    t, e = x["text"], x["entities"][0]
    v = t[e["start"]:e["end"]]
    check(not t[e["start"] - 1:e["start"]].isalnum(), f"{x['id']}: nothing glued before the date", v)
    if e["cell"].startswith("weekday"):
        m = re.fullmatch(r"(\d{1,2}) ([a-z]+) (\d{4})", v) or re.fullmatch(r"(\d{2})\.(\d{2})\.(\d{4})", v)
        d, mo, y = int(m[1]), (MON[m[2]] if m[2].isalpha() else int(m[2])), int(m[3])
        wd = B.WEEKDAYS[datetime.date(y, mo, d).weekday()]
        near = t[:e["start"]] if e["cell"] == "weekday_before" else t[e["end"]:]
        check(wd in (near[-20:] if e["cell"] == "weekday_before" else near[:20]).lower(),
              f"{x['id']}: the weekday is the date's real one, on the {e['cell'][8:]} side", v)
    if e["cell"] == "year_first_gen":
        y, rest = v.split("-", 1)
        check(rest.startswith(B.year_suffix(int(y)) + " il "), f"{x['id']}: year suffix", v)
        day = int(v.rsplit(" ", 1)[1])
        check(t[e["end"]:].startswith("-" + B._POSS[B.day_key(day)] + " ") or t[e["end"]:].startswith("-" + B._LOC[B.day_key(day)] + " "),
              f"{x['id']}: the day's suffix is outside the span", t[e["end"]:e["end"] + 4])

tg = json.loads((HERE / "probes" / "targets.json").read_text(encoding="utf-8"))["date_forms_az"]
check([(c["metric"], c.get("labels"), c.get("field"), c["op"], c["value"]) for c in tg["conditions"]] ==
      [("exact_recall", ["DATE"], None, ">=", 0.85), ("slice_exact_recall_min", None, "cell", ">=", 0.8),
       ("control_fp_rate", None, None, "<", 0.1)], "targets")


if __name__ == "__main__":
    print(f"{PASS} passed, {FAIL} failed")
    for f in FAILURES:
        print("  FAIL", f)
    sys.exit(1 if FAIL else 0)
