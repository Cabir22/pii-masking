"""Contract tests for placeholder slotting.

The whole harness's span-exactness guarantee rests on this module, so it is
tested hard even before the harness around it exists.

Run: python scripts/translate/test_sentinel.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from translate.sentinel import (SlotError, check_round_trip, sentinelize,  # noqa: E402
                                splice)

PASS = FAIL = 0


def ok(cond, msg, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  FAIL {msg}" + (f"  [{detail}]" if detail else ""))


def raises(fn, msg):
    global PASS, FAIL
    try:
        fn()
        FAIL += 1
        print(f"  FAIL {msg}  [no exception]")
    except SlotError:
        PASS += 1
    except Exception as e:  # noqa: BLE001
        FAIL += 1
        print(f"  FAIL {msg}  [wrong exception: {type(e).__name__}]")


# --- sentinelize ---------------------------------------------------------
print("sentinelize")

txt = "Zəng: +994501234567, e-poçt: a@b.az"
ents = [{"start": 6, "end": 19, "label": "TELEPHONENUM"},
        {"start": 29, "end": 35, "label": "EMAIL"}]
assert txt[6:19] == "+994501234567" and txt[29:35] == "a@b.az"
tmpl, labels = sentinelize(txt, ents)
ok(tmpl == "Zəng: ⟦0⟧, e-poçt: ⟦1⟧", "two entities", repr(tmpl))
ok(labels == ["TELEPHONENUM", "EMAIL"], "labels positional", labels)
ok("+994" not in tmpl and "a@b.az" not in tmpl, "no PII in templated text")

# unsorted input is sorted by position, not input order
tmpl2, labels2 = sentinelize(txt, list(reversed(ents)))
ok(tmpl2 == tmpl and labels2 == labels, "input order does not matter")

# entity at string start and end
e2 = [{"start": 0, "end": 3, "label": "GIVENNAME"},
      {"start": 4, "end": 7, "label": "SURNAME"}]
t3, _ = sentinelize("Əli Alı", e2)
ok(t3 == "⟦0⟧ ⟦1⟧", "spans at both ends", repr(t3))

# adjacent entities keep whatever separated them
t4, _ = sentinelize("AB", [{"start": 0, "end": 1, "label": "X"},
                            {"start": 1, "end": 2, "label": "Y"}])
ok(t4 == "⟦0⟧⟦1⟧", "adjacent spans", repr(t4))

raises(lambda: sentinelize("abc", [{"start": 0, "end": 2, "label": "X"},
                                   {"start": 1, "end": 3, "label": "Y"}]),
       "overlapping entities rejected")

ok(sentinelize("no entities here", []) == ("no entities here", []),
   "zero entities")


# --- check_round_trip --------------------------------------------------
print("check_round_trip")

ok(check_round_trip("Call ⟦0⟧ then email ⟦1⟧", 2) == (True, ""), "all present")
ok(check_round_trip("⟦1⟧ ⟦0⟧", 2)[0], "reordered is fine (matched by number)")
ok(not check_round_trip("Call ⟦0⟧", 2)[0], "dropped slot caught")
ok("dropped" in check_round_trip("Call ⟦0⟧", 2)[1], "dropped slot classified")
ok(not check_round_trip("⟦0⟧ ⟦0⟧ ⟦1⟧", 2)[0], "duplicate caught")
ok("dup" in check_round_trip("⟦0⟧ ⟦0⟧ ⟦1⟧", 2)[1].lower(), "duplicate classified")
ok("mangled" in check_round_trip("Call ⟦ 0 ⟧ then ⟦1⟧", 2)[1],
   "inner-space sentinel flagged as mangled, not just missing")
ok("mangled" in check_round_trip("Call [0] then ⟦1⟧", 2)[1],
   "bracket-swapped sentinel flagged as mangled")
ok(not check_round_trip("⟦0⟧ ⟦1⟧ ⟦2⟧", 2)[0], "invented slot caught")


# --- splice ----------------------------------------------------------
print("splice")

vals = {0: "+994 55 111 22 33", 1: "new.person@mail.az"}
translated = "The customer called from ⟦0⟧ and emailed ⟦1⟧ about it."
final, spans = splice(translated, lambda i: vals[i])
ok(final == "The customer called from +994 55 111 22 33 and emailed "
   "new.person@mail.az about it.", "values spliced", repr(final))
for i, sp in enumerate(spans):
    got = final[sp["start"]:sp["end"]]
    ok(got == vals[i], f"span {i} byte-exact", f"{got!r} != {vals[i]!r}")

# reordered slots -> spans still exact, and each span carries its slot number
# so the caller pairs it with labels[slot], not labels[nth-span]
final2, spans2 = splice("email ⟦1⟧ / phone ⟦0⟧", lambda i: vals[i])
ok(spans2[0]["slot"] == 1 and spans2[1]["slot"] == 0, "reorder: spans carry slot index")
ok(final2[spans2[0]["start"]:spans2[0]["end"]] == vals[1], "reorder: first span is slot 1")
ok(final2[spans2[1]["start"]:spans2[1]["end"]] == vals[0], "reorder: second span is slot 0")

# the bug this guards: model swaps ⟦0⟧/⟦1⟧, a CITY and a BUILDINGNUM. Pairing
# by span position instead of slot silently mislabels both.
_labels = ["CITY", "BUILDINGNUM"]
_vals = {0: "Baku", 1: "184C"}
_text, _spans = splice("building ⟦1⟧ in ⟦0⟧", lambda i: _vals[i])
_ents = sorted(({"start": s["start"], "end": s["end"], "label": _labels[s["slot"]]}
                for s in _spans), key=lambda e: e["start"])
ok([_text[e["start"]:e["end"]] for e in _ents] == ["184C", "Baku"],
   "reordered: values land left-to-right")
ok([e["label"] for e in _ents] == ["BUILDINGNUM", "CITY"],
   "reordered: labels follow the slot, not the position")

# multibyte carrier text (Cyrillic) -- offsets are char offsets, must hold
final3, spans3 = splice("Клиент ⟦0⟧ звонил", lambda i: "Иван Иванов")
ok(final3[spans3[0]["start"]:spans3[0]["end"]] == "Иван Иванов",
   "span exact under non-ASCII carrier text", repr(final3))

raises(lambda: splice("⟦0⟧ ⟦0⟧", lambda i: "x"), "splice rejects duplicate slot")
raises(lambda: splice("⟦0⟧ ⟦2⟧", lambda i: "x"), "splice rejects gap in slots")

# a value that itself contains a bracket char must not confuse a re-scan
final4, spans4 = splice("key ⟦0⟧", lambda i: "sk-a[0]b")
ok(final4[spans4[0]["start"]:spans4[0]["end"]] == "sk-a[0]b",
   "value containing brackets spliced exactly", repr(final4))


# --- decoy protection -------------------------------------------------
print("sentinelize_protected (decoys)")

from translate.sentinel import decoy_spans, sentinelize_protected  # noqa: E402

_t = "Order PRJ-3422 for Əli, code IJZ885"
_e = [{"start": 19, "end": 22, "label": "GIVENNAME"}]
ok(_t[19:22] == "Əli", "fixture offsets")
_tmpl, _slots = sentinelize_protected(_t, _e, ["PRJ-3422", "IJZ885"])
ok("PRJ-3422" not in _tmpl and "IJZ885" not in _tmpl,
   "decoys removed from the text sent to the model", _tmpl)
ok([s["kind"] for s in _slots] == ["decoy", "entity", "decoy"],
   "slots ordered by position, kinds tagged", [s["kind"] for s in _slots])
ok(_slots[1]["label"] == "GIVENNAME" and _slots[0]["label"] is None,
   "only entity slots carry a label")

_out, _sp = splice(_tmpl, lambda i: {0: "PRJ-3422", 1: "Rashad", 2: "IJZ885"}[i])
ok("PRJ-3422" in _out and "IJZ885" in _out,
   "decoys spliced back VERBATIM -- their broken shape is the signal", _out)
_ent = [s for s in _sp if _slots[s["slot"]]["kind"] == "entity"]
ok(len(_ent) == 1 and _out[_ent[0]["start"]:_ent[0]["end"]] == "Rashad",
   "entity slot re-minted, span exact")

# a decoy overlapping a real entity must not be double-claimed
_, _s2 = sentinelize_protected("call a@b.az now",
                               [{"start": 5, "end": 11, "label": "EMAIL"}],
                               ["a@b.az", "b.az"])
ok([s["kind"] for s in _s2] == ["entity"],
   "decoy overlapping an entity is not claimed twice")

# longest-first: an id nested inside a URL decoy must not steal the region
_sp3 = decoy_spans("see https://x.az/AB123 end", ["https://x.az/AB123", "AB123"], [])
ok(len(_sp3) == 1 and _sp3[0][2] == "https://x.az/AB123",
   "longest decoy wins over its own substring", _sp3)

# with no decoys and no repeats, behaviour is identical to sentinelize()
_ta, _la = sentinelize(_t, _e)
_tb, _sb = sentinelize_protected(_t, _e, [])
ok(_ta == _tb and _la == [s["label"] for s in _sb],
   "no-decoy path is identical to sentinelize()")

# --- shadow slots: untagged repeat occurrences ------------------------
print("shadow slots")

# the audit's stale_az_value failure mode: value present 4x, tagged 3x. The
# untagged one used to ride through translation as raw Azerbaijani, so the
# document ended up naming two different people.
_st = "Contact Naqilov now. Naqilov approved. See Naqilov. Inform Naqilov."
_se = [{"start": 8, "end": 15, "label": "SURNAME"},
       {"start": 21, "end": 28, "label": "SURNAME"},
       {"start": 43, "end": 50, "label": "SURNAME"}]
ok(all(_st[e["start"]:e["end"]] == "Naqilov" for e in _se), "fixture offsets")
_stmpl, _sslots = sentinelize_protected(_st, _se, [])
ok("Naqilov" not in _stmpl,
   "the untagged 4th occurrence is protected too", _stmpl)
ok([s["kind"] for s in _sslots] == ["entity", "entity", "entity", "shadow"],
   "extra occurrence is a shadow, not an entity",
   [s["kind"] for s in _sslots])

_sout, _ssp = splice(_stmpl, lambda i: "Jalalov")
ok("Naqilov" not in _sout and _sout.count("Jalalov") == 4,
   "every occurrence gets the group's fresh value", _sout)
ok(len([s for s in _ssp if _sslots[s["slot"]]["kind"] == "entity"]) == 3,
   "shadow occurrence does NOT become an entity")

# short values must not shadow-match -- "34" would match half the document
_, _shorts = sentinelize_protected("Age 34 and 34 items and 34",
                                   [{"start": 4, "end": 6, "label": "AGE"}], [])
ok([s["kind"] for s in _shorts] == ["entity"],
   "values under SHADOW_MIN_LEN are not shadow-matched",
   [s["kind"] for s in _shorts])

print(f"\n{'='*52}\nPASSED {PASS}   FAILED {FAIL}\n{'='*52}")
sys.exit(1 if FAIL else 0)
