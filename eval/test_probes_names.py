"""Tests for eval/probes/build_probes_names.py (the given-name shape probes, D-38 step 1).

Run:  python eval/test_probes_names.py

Fixed seed, counts per family, offsets matching the text, the committed files equal to a fresh
build, the list order and patronymic role, validity (scripts/piigen validators, checking only).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "probes"))

import build_probes_names as N  # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond, name, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(f"{name}: {detail}" if detail is not None else name)


def span(rec, s):
    return rec["text"][s["start"]:s["end"]]


out, problems = N.run(35)
again, _ = N.run(35)
other, _ = N.run(36)
dump = lambda o: json.dumps(o, ensure_ascii=False, sort_keys=True)  # noqa: E731
check(dump(out) == dump(again), "seed 35 twice: identical output")
check(dump(out["names_list_lines"]) != dump(other["names_list_lines"]), "seed 36: other names")
check(sorted(out) == sorted(N.FAMILIES), "exactly the four families", sorted(out))
check(problems == [], "no problems without validators", problems[:3])

for fam in N.FAMILIES:
    p = HERE / "probes" / f"{fam}.jsonl"
    disk = p.read_text(encoding="utf-8") if p.exists() else ""
    check(disk == "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out[fam]), f"{fam}.jsonl equals a fresh seed-35 build")

DOCS = {"names_list_lines": 14, "names_after_role": 24, "names_signature": 24, "names_sentence_start": 26}
for fam, rows in out.items():
    gold = [e for r in rows for e in r["entities"]]
    ctl = [c for r in rows for c in r.get("controls", [])]
    check(len(rows) == DOCS[fam], f"{fam}: document count", len(rows))
    check(len(gold) >= 12 and len(ctl) >= 4, f"{fam}: >= 12 names and >= 4 controls", (len(gold), len(ctl)))
    check({e["label"] for e in gold} <= {"GIVENNAME", "SURNAME"}, f"{fam}: only name labels")
    check(len({r["id"] for r in rows}) == len(rows), f"{fam}: unique ids")
    check(all(r["lang"] == "az" and r["family"] == fam and r["role"] for r in rows), f"{fam}: az, family, role")

# offsets, no overlaps, names capitalised
for fam, rows in out.items():
    for r in rows:
        spans = sorted((x["start"], x["end"]) for k in ("entities", "controls") for x in r.get(k, []))
        check(all(0 <= s < e <= len(r["text"]) and r["text"][s:e] == r["text"][s:e].strip() for s, e in spans),
              f"{r['id']}: spans inside the text")
        check(all(b[0] >= a[1] for a, b in zip(spans, spans[1:])), f"{r['id']}: no overlapping spans")
        check(all(span(r, e)[0].isupper() for e in r["entities"]), f"{r['id']}: names capitalised")

# 1. list lines: every person line is Surname Given Father oğlu/qızı
for r in out["names_list_lines"]:
    for line in r["text"].split("\n")[1:]:
        if re.fullmatch(r"\S+ \S+ \S+ (oğlu|qızı)", line):
            s0 = r["text"].index(line)
            labs = [(e["label"], e.get("role")) for e in r["entities"] if s0 <= e["start"] < s0 + len(line)]
            check(labs == [("SURNAME", None), ("GIVENNAME", "given"), ("GIVENNAME", "patronymic")],
                  f"{r['id']}: list line order", labs)
            words = line.split()
            check(words[1] != words[2], f"{r['id']}: father's name differs from the given name")
# 2. after a role word: the word before the name is lowercase
for r in out["names_after_role"]:
    for e in r["entities"][:1]:
        prev = r["text"][:e["start"]].split()[-1]
        check(prev[0].islower(), f"{r['id']}: a lowercase word right before the name", prev)
# 3. signature: the name stands alone on its own line
for r in out["names_signature"]:
    if r["entities"]:
        line = r["text"].split("\n")[1]
        check(" ".join(span(r, e) for e in r["entities"]) == line, f"{r['id']}: the name alone on its line", line)
# 4. sentence start: the first name opens a sentence
for r in out["names_sentence_start"]:
    if r["entities"]:
        s = r["entities"][0]["start"]
        check(s == 0 or r["text"][s - 2:s] == ". ", f"{r['id']}: the name starts a sentence")

_, problems = N.run(35, validators=str(HERE.parent / "scripts"))
check(problems == [], "validators: no problems", problems[:3])
targets = json.loads((HERE / "probes" / "targets.json").read_text(encoding="utf-8"))
check(all(f in targets for f in N.FAMILIES), "every family has a target")

if __name__ == "__main__":
    print(f"{PASS} passed, {FAIL} failed")
    for f in FAILURES:
        print("  FAIL", f)
    sys.exit(1 if FAIL else 0)
