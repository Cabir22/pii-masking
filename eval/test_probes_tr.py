"""Tests for the Turkish probes (D-58): the files are what the builder writes, every family has a
target, spans are exact and trimmed, the Turkish-specific conventions hold, and the scoreboard
loads them as their own set (never mixed into the Azerbaijani `probes`).

Run:  python eval/test_probes_tr.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "probes_tr"))

import build_probes_tr as T  # noqa: E402
import scoreboard as S  # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond, name, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(f"{name}: {detail}" if detail is not None else name)


D = HERE / "probes_tr"
r = subprocess.run([sys.executable, str(D / "build_probes_tr.py"), "--check"], capture_output=True, text=True)
check(r.returncode == 0, "the committed files are exactly what the builder writes", r.stdout + r.stderr)

targets = json.loads((D / "targets.json").read_text(encoding="utf-8"))
fams = {p.stem: [json.loads(l) for l in p.open(encoding="utf-8")] for p in sorted(D.glob("*.jsonl"))}
check(set(fams) == set(targets), "every family has a target and every target a family", set(fams) ^ set(targets))
check(all(f.endswith("_tr") for f in fams), "family names end in _tr (never collide with Azerbaijani ones)")
for f, rows in fams.items():
    for x in rows:
        check(x["lang"] == "tr" and x["family"] == f, f"{x['id']}: lang and family")
        for e in x["entities"] + x.get("hard_negatives", []):
            v = x["text"][e["start"]:e["end"]]
            check(v and v == v.strip(), f"{x['id']}: exact, trimmed span", repr(v))

for x in fams["inflected_names_tr"]:
    v = x["text"][x["entities"][0]["start"]:x["entities"][0]["end"]]
    check("'" in v and v.startswith(x["stem"]), f"{x['id']}: whole inflected form labelled (D-56d)", v)
for x in fams["time_ending_outside_tr"]:
    e = x["entities"][0]
    check(re.fullmatch(r"\d\d:\d\d", x["text"][e["start"]:e["end"]]) and x["text"][e["end"]] == "'",
          f"{x['id']}: the time only, its ending outside")
for x in fams["weekday_outside_date_tr"]:
    v = x["text"][x["entities"][0]["start"]:x["entities"][0]["end"]]
    check(not any(w.lower() in v.lower() for w in T.TR_WEEKDAYS), f"{x['id']}: no weekday inside DATE (D-54d)", v)
import datetime  # noqa: E402
TR_M = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
for x in fams["weekday_outside_date_tr"]:
    d, m, y = x["text"][x["entities"][0]["start"]:x["entities"][0]["end"]].split()
    w = [w for w in T.TR_WEEKDAYS if re.search(rf"\b{w}\b", x["text"])]
    check(w == [T.TR_WEEKDAYS[datetime.date(int(y), TR_M.index(m) + 1, int(d)).weekday()]],
          f"{x['id']}: the weekday is the date's real weekday (S1)", w)
for hhmm, case, want in (("14:02", "LOC", "'de"), ("23:03", "LOC", "'te"), ("10:30", "LOC", "'da"), ("09:40", "ABL", "'tan"),
                         ("18:00", "DAT", "'e"), ("15:20", "DAT", "'ye"), ("12:06", "DAT", "'ya"), ("17:45", "ABL", "'ten")):
    check(T.tr_ending(hhmm, case) == want, f"tr_ending({hhmm}, {case}) == {want}", T.tr_ending(hhmm, case))

check("probes_tr" in S.PUBLIC_SETS, "probes_tr is a scoreboard set")


class A:
    private_dir = "/nonexistent"
    runb_test = runb_v1_test = runb_parts = None
    sample = limit = 0
    lang_sample = 1000


docs, info = S.load_set("probes_tr", A)
check(docs is not None and len(docs) == sum(len(v) for v in fams.values()) and info["source"] == "eval/probes_tr/",
      "the scoreboard loads all Turkish probes from their own folder", info)
check(docs is not None and {d["meta"]["family"] for d in docs} == set(fams), "family = file name")
az, _ = S.load_set("probes", A)
check(az is not None and not any(d["meta"]["family"].endswith("_tr") for d in az), "the Azerbaijani probes stay Azerbaijani")

print(f"{PASS} passed, {FAIL} failed")
for f in FAILURES:
    print("  FAIL", f)
sys.exit(1 if FAIL else 0)
