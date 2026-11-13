"""Tests for the repeated-mention repair.

The defect it fixes: one source entity minted to several different values
inside a single document, so "Sahil ... Sahil" came back as two different
cities. The repair rewrites the finished file without retranslating, so its
one absolute requirement is that spans stay byte-exact afterwards.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import translate.repair_repeat_mentions_ru as M  # noqa: E402
from translate.run_ru import az_stem  # noqa: E402

PASS = FAIL = 0


def check(name: str, got: object, want: object) -> None:
    global PASS, FAIL
    if got == want:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL {name}\n     got  {got!r}\n     want {want!r}")


def truthy(name: str, got: object, want: bool) -> None:
    check(name, bool(got), want)


def _doc(text: str, ents: list[tuple[int, int, str, str]]) -> dict:
    return {"id": "d__ru", "source_id": "d", "lang": "ru", "split": "test",
            "text": text,
            "entities": [{"start": s, "end": e, "label": lab, "text": t}
                         for s, e, lab, t in ents]}


# --------------------------------------------------------------------------- #
# az_stem: the same entity inflected, versus two different entities
# --------------------------------------------------------------------------- #
for a, b in [("Göygöl", "Göygöldə"), ("Balakən", "Balakəndə"),
             ("Dilrubə", "Dilrubənin"), ("Səidrzayev", "Səidrzayevin"),
             ("Bakı", "Bakıda"), ("Qusarda", "Qusardan"),
             ("Kərim", "Kərimdir"), ("Fayizov", "Fayizovun")]:
    check(f"az_stem unifies {a}/{b}", az_stem(a), az_stem(b))
for a, b in [("Elçin", "Orxan"), ("Bakı", "Gəncə"), ("Sahil", "Sumqayıt")]:
    truthy(f"az_stem keeps {a}/{b} apart", az_stem(a) != az_stem(b), True)
check("az_stem keeps a short word whole", az_stem("Ali"), "ali")


# --------------------------------------------------------------------------- #
# the repair itself
# --------------------------------------------------------------------------- #
src = {"id": "d", "text": "Sahil şəhəri. Yenə Sahildə.",
       "entities": [{"start": 0, "end": 5, "label": "CITY", "text": "Sahil"},
                    {"start": 19, "end": 26, "label": "CITY", "text": "Sahildə"}]}
rec = _doc("Нефтечала город. Снова Ордубад.",
           [(0, 9, "CITY", "Нефтечала"), (23, 30, "CITY", "Ордубад")])
fixed, changed = M.repair_record(rec, src)
check("repair: one mention rewritten", changed, 1)
check("repair: both mentions now agree",
      {e["text"] for e in fixed["entities"]}, {"Нефтечала"})
for e in fixed["entities"]:
    check(f"repair: span exact for {e['text']!r}",
          fixed["text"][e["start"]:e["end"]], e["text"])
check("repair: carrier text is otherwise untouched",
      fixed["text"], "Нефтечала город. Снова Нефтечала.")

# a document that is already consistent must come back byte-identical
ok = _doc("Нефтечала город. Снова Нефтечала.",
          [(0, 9, "CITY", "Нефтечала"), (23, 32, "CITY", "Нефтечала")])
same, changed = M.repair_record(ok, src)
check("repair: consistent document untouched", changed, 0)
check("repair: consistent document identical", same["text"], ok["text"])

# two genuinely different entities must NOT be merged
src2 = {"id": "d", "text": "Bakı və Gəncə şəhərləri.",
        "entities": [{"start": 0, "end": 4, "label": "CITY", "text": "Bakı"},
                     {"start": 8, "end": 13, "label": "CITY", "text": "Gəncə"}]}
rec2 = _doc("Шеки и Губа города.",
            [(0, 4, "CITY", "Шеки"), (7, 11, "CITY", "Губа")])
out2, changed2 = M.repair_record(rec2, src2)
check("repair: different entities left alone", changed2, 0)

# the elected value is the commonest, so the fewest edits are made
src3 = {"id": "d", "text": "Sahil Sahil Sahil",
        "entities": [{"start": 0, "end": 5, "label": "CITY", "text": "Sahil"},
                     {"start": 6, "end": 11, "label": "CITY", "text": "Sahil"},
                     {"start": 12, "end": 17, "label": "CITY", "text": "Sahil"}]}
rec3 = _doc("Куба Шеки Шеки",
            [(0, 4, "CITY", "Куба"), (5, 9, "CITY", "Шеки"),
             (10, 14, "CITY", "Шеки")])
out3, changed3 = M.repair_record(rec3, src3)
check("repair: elects the commonest value", changed3, 1)
check("repair: kept the majority value",
      {e["text"] for e in out3["entities"]}, {"Шеки"})

# a length change must shift every later offset
src4 = {"id": "d", "text": "Sahil x Sahil y",
        "entities": [{"start": 0, "end": 5, "label": "CITY", "text": "Sahil"},
                     {"start": 8, "end": 13, "label": "CITY", "text": "Sahil"}]}
rec4 = _doc("Гянджа x Куба y",
            [(0, 6, "CITY", "Гянджа"), (9, 13, "CITY", "Куба")])
out4, _ = M.repair_record(rec4, src4)
for e in out4["entities"]:
    check(f"repair: offsets shifted correctly for {e['text']!r}",
          out4["text"][e["start"]:e["end"]], e["text"])

# a mismatched entity count is left alone rather than guessed at
bad = _doc("Нефтечала.", [(0, 9, "CITY", "Нефтечала")])
_out, ch = M.repair_record(bad, src)
check("repair: mismatched entity counts skipped", ch, 0)

# --------------------------------------------------------------------------- #
# label/value shape, and realigning labels from the source
#
# An older revision let labels rotate against values, so a ZIPCODE held a
# street name and a SURNAME held an IP address -- in 60 documents across val
# and test. Every value was individually well-formed and every span byte-exact,
# so nothing saw it.
# --------------------------------------------------------------------------- #
from translate.run_ru import label_shape_errors  # noqa: E402

check("shape: a well-formed record has no errors",
      label_shape_errors([{"label": "AGE", "text": "42"},
                          {"label": "CITY", "text": "Баку"},
                          {"label": "EMAIL", "text": "a.b@mail.az"},
                          {"label": "ZIPCODE", "text": "AZ1046"}]), [])
truthy("shape: a surname in an AGE slot is caught",
       label_shape_errors([{"label": "AGE", "text": "Ягиналиев"}]), True)
truthy("shape: a street name in a ZIPCODE slot is caught",
       label_shape_errors([{"label": "ZIPCODE", "text": "Ататюрк дёнгаси"}]), True)
truthy("shape: a Latin given name is caught",
       label_shape_errors([{"label": "GIVENNAME", "text": "AA0971919"}]), True)
# IBAN is deliberately unchecked -- the corpus mints AZ, TR, AE and GE
# accounts in both cases, exactly as the Azerbaijani source does
for _iban in ["AZ15AIVL25169218409602525126", "TR303723018675523544316722",
              "GE90ER5116801234498663", "tr512246847974907915688883"]:
    check(f"shape: IBAN {_iban[:6]} accepted",
          label_shape_errors([{"label": "IBAN", "text": _iban}]), [])

_src = {"id": "d", "text": "78 yaşlı Ərzan hümamov, AZ0113, bina 45",
        "entities": [{"start": 0, "end": 2, "label": "AGE", "text": "78"},
                     {"start": 9, "end": 14, "label": "GIVENNAME", "text": "Ərzan"},
                     {"start": 15, "end": 22, "label": "SURNAME", "text": "hümamov"},
                     {"start": 24, "end": 30, "label": "ZIPCODE", "text": "AZ0113"},
                     {"start": 37, "end": 39, "label": "BUILDINGNUM", "text": "45"}]}
# labels rotated by one against the values, exactly as observed
_rot = _doc("13 Мирелхан Ягиналиев AZ1074 44",
            [(0, 2, "GIVENNAME", "13"), (3, 11, "SURNAME", "Мирелхан"),
             (12, 21, "AGE", "Ягиналиев"), (22, 28, "BUILDINGNUM", "AZ1074"),
             (29, 31, "ZIPCODE", "44")])
truthy("relabel: the rotated record is detected as malformed",
       label_shape_errors(_rot["entities"]), True)
_fix, _n = M.realign_labels(_rot, _src)
check("relabel: every label restored", _n, 5)
check("relabel: no shape errors remain", label_shape_errors(_fix["entities"]), [])
check("relabel: values untouched",
      [e["text"] for e in _fix["entities"]],
      [e["text"] for e in _rot["entities"]])
check("relabel: offsets untouched",
      [(e["start"], e["end"]) for e in _fix["entities"]],
      [(e["start"], e["end"]) for e in _rot["entities"]])

# a clean record is left exactly alone
_clean = _doc("42 Баку", [(0, 2, "AGE", "42"), (3, 7, "CITY", "Баку")])
_src2 = {"id": "d", "text": "42 Bakı",
         "entities": [{"start": 0, "end": 2, "label": "AGE", "text": "42"},
                      {"start": 3, "end": 7, "label": "CITY", "text": "Bakı"}]}
check("relabel: clean record untouched", M.realign_labels(_clean, _src2)[1], 0)

# and where the source labels do NOT explain the damage, nothing is guessed
_weird = _doc("Ягиналиев", [(0, 9, "AGE", "Ягиналиев")])
_src3 = {"id": "d", "text": "78",
         "entities": [{"start": 0, "end": 2, "label": "AGE", "text": "78"}]}
check("relabel: refuses to guess when the source does not explain it",
      M.realign_labels(_weird, _src3)[1], 0)

print("=" * 60)
print(f"PASSED {PASS}   FAILED {FAIL}")
print("=" * 60)
sys.exit(1 if FAIL else 0)
