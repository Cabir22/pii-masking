"""Tests for scripts/relabel_a7_gold.py (D-54c, D-56d): timestamps, year words and weekdays out of DATE/TIME;
Turkish inflected names labelled whole.

Run:  python scripts/test_relabel_a7_gold.py
"""
from __future__ import annotations

import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import relabel_a7_gold as R  # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []
LEX = R.lexicon()


def check(cond, name, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(f"{name}: {detail}" if detail is not None else name)


def doc(text: str, spans: list[tuple[str, str]], lang: str) -> dict:
    ents, at = [], 0
    for label, value in spans:
        s = text.index(value, at)
        ents.append({"start": s, "end": s + len(value), "label": label})
        at = s + len(value)
    return {"id": "x", "lang": lang, "text": text, "entities": ents}


def values(d: dict) -> list[tuple[str, str]]:
    return [(e["label"], d["text"][e["start"]:e["end"]]) for e in d["entities"]]


CASES = [
    ("ru", "Дата рождения: 21 февраля 1956 года.", [("DATE", "21 февраля 1956 года")], [("DATE", "21 февраля 1956")], ["Y"]),
    ("ru", "Выдан 25 октября 1997 г., Баку.", [("DATE", "25 октября 1997 г.")], [("DATE", "25 октября 1997")], ["Y"]),
    ("ru", "с 11 декабря 1960 г., воскресенье не принимаются", [("DATE", "11 декабря 1960 г., воскресенье")],
     [("DATE", "11 декабря 1960")], ["W", "Y"]),
    ("ru", "встреча: понедельник, 6 августа 2001 г. в офисе", [("DATE", "понедельник, 6 августа 2001 г.")],
     [("DATE", "6 августа 2001")], ["W", "Y"]),
    ("tr", "Doğum tarihi: Salı, 16 Ekim 1962", [("DATE", "Salı, 16 Ekim 1962")], [("DATE", "16 Ekim 1962")], ["W"]),
    ("tr", "Toplantı 21 Şubat 1956 Pazartesi günü yapıldı.", [("DATE", "21 Şubat 1956 Pazartesi günü")],
     [("DATE", "21 Şubat 1956")], ["W"]),
    ("tr", "Kayıt 1998 yılında açıldı.", [("DATE", "1998 yılında")], [("DATE", "1998")], ["Y"]),
    ("en", "Born on Monday, 3 March 1990 in Baku.", [("DATE", "Monday, 3 March 1990")], [("DATE", "3 March 1990")], ["W"]),
    ("en", "[2021-08-15 11:45:02] ERROR: retry", [("TIME", "11:45")], [], ["T"]),
    ("ru", "[09:36] Лейла: Уже скоро", [("TIME", "09:36")], [], ["T"]),
    ("tr", "Randevu saat 14:30'da.", [("TIME", "14:30")], [("TIME", "14:30")], []),      # clock time in the text stays
    ("ru", "Договор от 21 февраля 1956 подписан.", [("DATE", "21 февраля 1956")], [("DATE", "21 февраля 1956")], []),
    ("ru", "Пятница", [("DATE", "Пятница")], [("DATE", "Пятница")], []),                 # would leave no digit: not made
    ("tr", "Toplantı Gence'nin merkezinde.", [("CITY", "Gence")], [("CITY", "Gence'nin")], ["I"]),          # D-56d
    ("tr", "Bu Küləşova'nın imzası.", [("SURNAME", "Küləşova")], [("SURNAME", "Küləşova'nın")], ["I"]),
    ("tr", "Randevu 14:30'da.", [("TIME", "14:30")], [("TIME", "14:30")], []),               # not a name: stays
    ("ru", "в Бакинском районе", [("CITY", "Бакинском")], [("CITY", "Бакинском")], []),         # fused: already whole
]
for lang, text, gold, want, rules in CASES:
    sk = collections.Counter()
    d = doc(text, gold, lang)
    new, ch = R.relabel(d, lang, LEX, sk)
    check(values(new) == want, f"{lang} {text!r}: labels", values(new))
    check(sorted({c.rule for c in ch}) == rules, f"{lang} {text!r}: rules", sorted({c.rule for c in ch}))
    check(new["text"] == text, f"{lang} {text!r}: text unchanged")
    if not ch:
        check(new is d, f"{lang} {text!r}: an unchanged record is returned as it was")
    else:
        check(new["_a7_relabel"] == rules, f"{lang} {text!r}: _a7_relabel", new.get("_a7_relabel"))

d = doc("[2021-08-15 11:45:02] ERROR: retry", [("TIME", "11:45")], "en")
new, _ = R.relabel(d, "en", LEX, collections.Counter())
check(any(x["kind"] == "TIMESTAMP" for x in new["_decoys"]), "a removed stamp TIME is declared as a TIMESTAMP look-alike")
sk = collections.Counter()
new, ch = R.relabel(doc("Срок: пятница, среда.", [("DATE", "пятница, среда")], "ru"), "ru", LEX, sk)
check(not ch and sk["W: would leave no digit"] >= 1, "a trim that would leave no digit is not made, and counted", dict(sk))
a = R.relabel(doc("Doğum tarihi: Salı, 16 Ekim 1962", [("DATE", "Salı, 16 Ekim 1962")], "tr"), "tr", LEX, collections.Counter())[0]
b = R.relabel(doc("Doğum tarihi: Salı, 16 Ekim 1962", [("DATE", "Salı, 16 Ekim 1962")], "tr"), "tr", LEX, collections.Counter())[0]
check(a == b, "deterministic")
d = doc("Bu Küləşova'nın imzası.", [("SURNAME", "Küləşova")], "tr"); d["_a7_relabel"] = ["W"]
check(R.relabel(d, "tr", LEX, collections.Counter())[0]["_a7_relabel"] == ["I", "W"], "earlier rule letters are kept")

print(f"{PASS} passed, {FAIL} failed")
for f in FAILURES:
    print("  FAIL", f)
sys.exit(1 if FAIL else 0)
