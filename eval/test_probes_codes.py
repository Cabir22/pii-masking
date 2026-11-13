"""Tests for eval/probes/build_probes_codes.py (code_density) and the slice metrics it uses.

Run:  python eval/test_probes_codes.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / "probes")]

import build_probes_codes as B  # noqa: E402
from metrics import _target_metric  # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond, name, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(f"{name}: {detail!r}" if detail is not None else name)


rows = B.build(35)
committed = [json.loads(l) for l in (HERE / "probes" / "code_density.jsonl").read_text(encoding="utf-8").splitlines()]
check(rows == committed, "the committed file is what the builder makes (seed 35)")
check(len(rows) == 210, "210 documents", len(rows))
check(B.check(rows) == [], "builder's own checks", B.check(rows)[:3])
cells = Counter(e["cell"] for x in rows for e in x["entities"])
check(len(cells) == 21 and set(cells.values()) == {10}, "21 cells of 10 values", cells)
check(all(len(x["entities"]) == 1 for x in rows), "one gold value per document")

by = {}
for x in rows:
    by.setdefault(x["pair"], {})[x["role"]] = x
for p, t in by.items():
    v = {r: x["text"][x["entities"][0]["start"]:x["entities"][0]["end"]] for r, x in t.items()}
    check(set(t) == {"codes_0", "codes_2", "codes_6"}, f"pair {p}: three densities")
    check(len(set(v.values())) == 1, f"pair {p}: same value")
    c2 = {x["text"][c["start"]:c["end"]] for c in t["codes_2"].get("controls", [])}
    c6 = {x["text"][c["start"]:c["end"]] for x in [t["codes_6"]] for c in x.get("controls", [])}
    c2 = {t["codes_2"]["text"][c["start"]:c["end"]] for c in t["codes_2"]["controls"]}
    check(c2 <= c6, f"pair {p}: the 2 codes are among the 6")
    # only the code sentences differ: drop them and the three texts agree
    strip = lambda x: re.sub(r"\s+", " ", " ".join(s for s in re.split(r"(?<=\.)\s", x["text"])
                                                  if not any(x["text"][c["start"]:c["end"]] in s for c in x.get("controls", []))))
    check(len({strip(x) for x in t.values()}) == 1, f"pair {p}: the documents differ only by code sentences")

VERSION = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
for x in rows:
    for c in x.get("controls", []):
        code = x["text"][c["start"]:c["end"]]
        m = VERSION.match(code)
        if m:
            check(13 <= int(m.group(2)) <= 49, f"version {code} never reads as a date")
        check(not re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", code), f"code {code} is not an IPv4")
        check("@" not in code and "://" not in code and ":" not in code, f"code {code} is no e-mail, URL, MAC or IPv6")

# slice metrics
sc = {"slices": {"entity": {"codes": {"0": {"exact_recall": 0.9}, "2": {"exact_recall": 0.85}, "6": {"exact_recall": 0.6}}}},
      "recall": {}}
check(abs(_target_metric({"metric": "slice_exact_recall_min", "field": "codes"}, sc, {}) - 0.6) < 1e-9, "slice min")
check(abs(_target_metric({"metric": "slice_exact_recall_spread", "field": "codes"}, sc, {}) - 0.3) < 1e-9, "slice spread")
check(_target_metric({"metric": "slice_exact_recall_min", "field": "cell"}, sc, {}) is None, "missing field -> not scored")
tg = json.loads((HERE / "probes" / "targets.json").read_text(encoding="utf-8"))["code_density"]
check([(c["metric"], c.get("field"), c["value"]) for c in tg["conditions"]] ==
      [("exact_recall", None, 0.95), ("slice_exact_recall_min", "cell", 0.9)], "targets (D-77)")


if __name__ == "__main__":
    print(f"{PASS} passed, {FAIL} failed")
    for f in FAILURES:
        print("  FAIL", f)
    sys.exit(1 if FAIL else 0)
