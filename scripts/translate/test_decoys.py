"""What the translation keeps verbatim (D-54b, problem B): translate/decoys.py.

Every case is a shape found in runb-az-v4.1's train split.

Run: python scripts/translate/test_decoys.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from translate.decoys import protected_ranges, value_parts  # noqa: E402
from translate.sentinel import sentinelize_protected  # noqa: E402

PASS = FAIL = 0


def ok(cond, msg, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  FAIL {msg}" + (f"  [{detail}]" if detail else ""))


def kept(rec):
    return [rec["text"][a:b] for a, b in protected_ranges(rec)]


def rec(text, *, hn=(), decoys=(), entities=()):
    """`decoys`: (value, kind) pairs, located in `text` by their first occurrence."""
    d = []
    for v, kind in decoys:
        i = text.index(v)
        d.append({"start": i, "end": i + len(v), "kind": kind})
    return {"text": text, "entities": list(entities), "_decoys": d,
            "_spec": {"hard_negatives": list(hn)}}


# 1. The LLM batches: a phrase in `_spec.hard_negatives`, the value in `_decoys`.
r = rec("Kampaniya kodu: kampaniya CMP-3287 bitib.", hn=["kampaniya CMP-3287"],
        decoys=[("CMP-3287", "campaign_code")])
ok(kept(r) == ["CMP-3287"], "phrase with a declared value keeps the value only", kept(r))

r = rec("SIM kartın ICCID nömrəsi 891 ilə başlayır, hesab 89123456.",
        hn=["SIM kartın ICCID nömrəsi 891"], decoys=[("891", "iccid_short_prefix")])
ok(kept(r) == ["891"], "a 3-digit declared value is kept at its position only", kept(r))

# 2. Word look-alikes are translated, never kept.
for v, kind in [("Bölmədə", "sentence_initial_locative"), ("SUMQAYIT", "policy_city_in_institution"),
                ("Bakı klubu", "policy_city_as_project"), ("Nokia", "policy_foreign_brand"),
                ("Suretli", "common_word_surname"), ("azad", "homograph_noun")]:
    r = rec(f"Mətn: {v} burada.", hn=[v], decoys=[(v, kind)])
    ok(kept(r) == [], f"word look-alike {kind} is translated", kept(r))

# 3. Shape look-alikes without Azerbaijani letters are kept whole.
for v, kind in [("CNE", "cvv_letters"), ("ERR_MLINTR", "ERROR_CODE"), ("a***.b***@c******.com", "MASKED_EMAIL"),
                ("ukhk(at)oidti(dot)net", "OBFUSCATED_EMAIL"), ("XPYPZPVV", "fin_8_9_chars"),
                ("-----BEGIN ENCRYPTED PRIVATE KEY----- XXXXXXXXXXXX", "private_key_placeholder")]:
    r = rec(f"Qeyd: {v} yoxlanıldı.", decoys=[(v, kind)])
    ok(kept(r) == [v], f"shape look-alike {kind} is kept whole", kept(r))

# 3b. `policy_*` dummy values have digits and are kept (19 Oct re-run: a
#     translated `kart nömrəsi 5555555555554444` failed the card-leak check).
for v, kind in [("5555555555554444", "policy_test_card"), ("P12345678", "policy_passport_dummy"),
                ("20:16", "policy_version_time"), ("1234", "policy_sequential")]:
    r = rec(f"Test: kart nömrəsi {v} yoxlanıldı.", hn=[f"kart nömrəsi {v}"], decoys=[(v, kind)])
    ok(kept(r) == [v], f"policy dummy value {kind} is kept", kept(r))

# 4. A declared span with Azerbaijani words keeps only its digit-bearing part.
v = "-----BEGIN RSA PRIVATE KEY-----\n<açarı bura daxil edin>"
r = rec(f"Açar: {v}", decoys=[(v, "private_key_placeholder")])
ok(kept(r) == [], "an Azerbaijani placeholder without digits keeps nothing", kept(r))

# 5. An undeclared phrase with Azerbaijani words keeps its value tokens.
r = rec("Ödəniş: kartın CVV kodu 96-0, təsdiqləyin.", hn=["kartın CVV kodu 96-0"])
ok(kept(r) == ["96-0"], "undeclared phrase keeps its value", kept(r))
r = rec("Zəng edin: 878 saylı kabinet.", hn=["878 saylı kabinet"])
ok(kept(r) == ["878"], "undeclared phrase, value first", kept(r))
r = rec("Kart: kart nömrəsi 5555 1234 5678 9999.", hn=["kart nömrəsi 5555 1234 5678 9999"])
ok(kept(r) == ["5555 1234 5678 9999"], "space-separated value stays one range", kept(r))

# 6. Old corpus: single values, every occurrence, as before.
r = rec("IP 794.169.0.625 və yenə 794.169.0.625.", hn=["794.169.0.625"])
ok(kept(r) == ["794.169.0.625", "794.169.0.625"], "every occurrence of a single value", kept(r))
r = rec("Silinib: [PII REMOVED] və tralp AT ognnbu DOT org", hn=["[PII REMOVED]", "tralp AT ognnbu DOT org"])
ok(kept(r) == ["[PII REMOVED]", "tralp AT ognnbu DOT org"], "multi-word ASCII shapes kept whole", kept(r))

# 7. Never overlaps an entity; malformed spans are skipped.
t = "FIN 5ABC123 və kod 5ABC12"
ent = [{"start": 4, "end": 11, "label": "AZ_FIN", "text": "5ABC123"}]
j = t.rindex("5ABC12")
r = {"text": t, "entities": ent, "_spec": {},
     "_decoys": [{"start": 4, "end": 10, "kind": "fin_short"},       # inside the entity
                 {"start": j, "end": j + 6, "kind": "fin_short"}]}
ok(protected_ranges(r) == [(j, j + 6)], "a span inside an entity is skipped, the other kept",
   protected_ranges(r))
r = {"text": "abc", "entities": [], "_decoys": [{"start": 2, "end": 9, "kind": "x"}, {"start": "a"}]}
ok(protected_ranges(r) == [], "out-of-range and malformed spans skipped")

# 8. A phrase not in the text keeps nothing; a declared word span inside a
#    phrase means the phrase is translated.
r = rec("Mətn burada.", hn=["vəsiqə nömrəsi AB-5115"])
ok(kept(r) == [], "phrase absent from the text")
r = rec("Əhmədbəy Ağayev haqqında mühazirə 12 mayda.", hn=["Əhmədbəy Ağayev haqqında mühazirə"],
        decoys=[("Əhmədbəy Ağayev haqqında mühazirə", "policy_street_as_topic")])
ok(kept(r) == [], "policy phrase is translated", kept(r))

# 9. value_parts trims punctuation.
t = "kod (12-34), sonra"
ok([t[a:b] for a, b in value_parts(t + " ə", 0, len(t) + 2)] == ["12-34"], "punctuation trimmed")

# 10. sentinelize_protected takes positions; slots carry the values back.
r = rec("Kampaniya: kampaniya CMP-3287 və Bakı.", hn=["kampaniya CMP-3287"],
        decoys=[("CMP-3287", "campaign_code")],
        entities=[{"start": 33, "end": 37, "label": "CITY", "text": "Bakı"}])
templ, slots = sentinelize_protected(r["text"], r["entities"], decoy_ranges=protected_ranges(r))
ok(templ == "Kampaniya: kampaniya ⟦0⟧ və ⟦1⟧." and [s["kind"] for s in slots] == ["decoy", "entity"]
   and slots[0]["value"] == "CMP-3287", "templated text keeps the Azerbaijani word outside the slot", templ)

print("=" * 60)
print(f"PASSED {PASS}   FAILED {FAIL}")
print("=" * 60)
sys.exit(1 if FAIL else 0)
