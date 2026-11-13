"""Harness tests that need no API: renderer, anchors_en, validator, guard
policy, prompt sizing, and the full sentinelize -> mint -> splice -> validate
round trip against real corpus documents.

Run: python scripts/translate/test_harness.py
"""
from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from piigen.values import ValueFactory, ValuePool  # noqa: E402
from translate.lang import ANCHORS  # noqa: E402
anchors_en, anchors_tr = ANCHORS["en"], ANCHORS["tr"]
from translate.guard import EXPECTED_SCRIPTS, GuardAborted, guarded_stream  # noqa: E402
from translate.prompt import build_messages, system_prompt, token_budget  # noqa: E402
from translate.render import (RendererError, get_renderer,  # noqa: E402
                              render_value)
from translate.sentinel import entity_source_values, sentinelize, splice  # noqa: E402
from translate.validate import validate_record  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
AZ_TRAIN = ROOT / "data" / "processed" / "az" / "train.docs.jsonl"

PASS = FAIL = 0


def ok(cond, msg, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  FAIL {msg}" + (f"  [{detail}]" if detail else ""))


rng = random.Random(7)

# ---------------------------------------------------------------- renderer
print("render")

ok(render_value("CITY", "Bakı", "en", rng) == "Baku", "exonym: Bakı -> Baku")
ok(render_value("CITY", "Gəncə", "en", rng) == "Ganja", "exonym: Gəncə -> Ganja")
ok(render_value("CITY", "Qax", "en", rng) == "Gakh", "no-exonym city transliterated")
ok(render_value("CITY", "Şəmkir", "en", rng) == "Shamkir", "exonym: Şəmkir")
# long tail falls back to the mechanical transliteration
ok(render_value("CITY", "Ağsu", "en", rng) == "Aghsu", "fallback transliterates",
   render_value("CITY", "Ağsu", "en", random.Random(1)))
ok(render_value("STREET", "Nizami küçəsi", "en", rng) == "Nizami Street",
   "street type word translated")
ok(render_value("STREET", "Üzeyir Hacıbəyov prospekti", "en", rng)
   == "Uzeyir Hajibayov Avenue", "street: translit + type word",
   render_value("STREET", "Üzeyir Hacıbəyov prospekti", "en", random.Random(2)))

# The mechanical map is not a guess: it reproduces 25 of the 30 hand-written
# exonyms exactly. The five it misses (Bakı->Baku, Şəki->Sheki, ...) are the
# genuinely irregular ones the table exists to cover.
from translate.lang.en.render import EN_PLACE_MAP, en_translit  # noqa: E402
_agree = sum(1 for az, en in EN_PLACE_MAP.items() if en_translit(az) == en)
ok(_agree >= 24, "transliteration agrees with most hand-written exonyms",
   f"{_agree}/{len(EN_PLACE_MAP)}")
for _az, _en in [("Əli", "Ali"), ("Məmmədov", "Mammadov"), ("Cavid", "Javid"),
                 ("Xanlar", "Khanlar"), ("Qurban", "Gurban"),
                 ("Çingiz", "Chingiz"), ("Şəfa", "Shafa")]:
    ok(en_translit(_az) == _en, f"translit {_az} -> {_en}", en_translit(_az))

# structured values are never touched, whatever the rng does
for label, val in [("TELEPHONENUM", "+994 50 123 45 67"),
                   ("EMAIL", "a.b@mail.az"), ("AZ_FIN", "30LJV5Z"),
                   ("IBAN", "AZ21NABZ00000000137010001944"),
                   ("IPV4_ADDRESS", "192.168.1.20"),
                   ("API_KEY", "sk-ant-a1B2c3D4"),
                   ("ZIPCODE", "AZ 1132"), ("BUILDINGNUM", "23"),
                   ("AGE", "34"), ("CARD_SECURITY_CODE", "047")]:
    ok(render_value(label, val, "en", random.Random(0)) == val,
       f"{label} verbatim")

# DATE/TIME come from the carrier locale already -- must not be re-rendered
ok(render_value("DATE", "21 February 1956", "en", rng) == "21 February 1956",
   "DATE passes through untouched")

# names: both forms appear, and only those two
seen = {render_value("GIVENNAME", "Əli", "en", random.Random(s))
        for s in range(200)}
ok(seen == {"Ali", "Əli"}, "GIVENNAME mixes transliterated and original", seen)
folded = sum(1 for s in range(400)
             if render_value("SURNAME", "Məmmədov", "en", random.Random(s)) == "Mammadov")
ok(150 < folded < 330, "translit rate roughly matches EN_FOLD_NAME_RATE", folded)

# Was: asserted get_renderer("tr") raised RendererError, back when no
# Turkish Renderer existed. render.py's RENDERERS["tr"] now exists (Phase 4),
# so that failure mode is gone -- this now asserts the positive case: the
# renderer resolves, and behaves correctly per label category.
from translate.lang.tr.render import TR_CITY_EXONYMS, tr_translit  # noqa: E402

tr_renderer = get_renderer("tr")
ok(tr_renderer.lang == "tr", "get_renderer('tr') resolves to the tr Renderer")

# structured values are never touched for tr either -- same list as the en
# check above, same reason: every character is load-bearing.
for label, val in [("TELEPHONENUM", "+994 50 123 45 67"),
                   ("EMAIL", "a.b@mail.az"), ("AZ_FIN", "30LJV5Z"),
                   ("IBAN", "AZ21NABZ00000000137010001944"),
                   ("IPV4_ADDRESS", "192.168.1.20"),
                   ("API_KEY", "sk-ant-a1B2c3D4"),
                   ("ZIPCODE", "AZ 1132"), ("BUILDINGNUM", "23"),
                   ("AGE", "34"), ("CARD_SECURITY_CODE", "047")]:
    ok(render_value(label, val, "tr", random.Random(0)) == val,
       f"tr {label} verbatim")

# DATE/TIME come from the carrier locale already -- must not be re-rendered
ok(render_value("DATE", "21 Şubat 1956", "tr", rng) == "21 Şubat 1956",
   "tr DATE passes through untouched")

# names: ə->e by default, a small configured share kept as given -- and,
# CRITICAL, only ever one of those two forms, never a Turkish name cognate
# ("Ali" for Əli, "Mehmet" for Məmməd would change who the person is).
seen_tr = {render_value("GIVENNAME", "Əli", "tr", random.Random(s))
           for s in range(300)}
ok(seen_tr == {"Eli", "Əli"},
   "tr GIVENNAME is folded or original, never a cognate", seen_tr)
kept = sum(1 for s in range(3000)
           if render_value("SURNAME", "Məmmədov", "tr", random.Random(s))
           == "Məmmədov")
ok(200 < kept < 550, "tr keep-schwa rate roughly matches TR_KEEP_SCHWA_RATE",
   kept)
# Turkish keeps ç ş ğ ı ö ü, and folds the three letters its alphabet does
# NOT have: ə->e, q->g, x->h. Folding q/x is a spelling convention (Qurban
# and Gurban are one man); substituting a cognate would not be, which is why
# Əli->Eli and never "Ali".
for _az, _tr in [("Əli", "Eli"), ("Məmmədov", "Memmedov"),
                 ("Çingiz", "Çingiz"), ("Şəfa", "Şefa"),
                 ("Xanlar", "Hanlar"), ("Qurban", "Gurban"),
                 ("Ağaqardaşov", "Ağagardaşov"), ("Saatxan", "Saathan")]:
    ok(tr_translit(_az) == _tr, f"tr_translit {_az} -> {_tr}", tr_translit(_az))
# no q/x/w may survive a fold -- they are not Turkish letters
ok(not re.search(r"[qxwQXW]", "".join(tr_translit(v) for v in
                 ["Qax", "Xocalı", "Zaqatala", "Qubadlı", "Naxçıvan"])),
   "tr_translit leaves no non-Turkish letter behind")
# and the mechanical map must agree with the hand-written exonyms it can
# derive -- the same evidence test en_translit carries (24 of 26 here; the
# misses are Bakı->Bakü and the deliberate Sumqayıt override).
_tr_agree = sum(1 for _az, _tr in TR_CITY_EXONYMS.items()
                if tr_translit(_az) == _tr)
ok(_tr_agree >= 23, "tr transliteration agrees with most Turkish exonyms",
   f"{_tr_agree}/{len(TR_CITY_EXONYMS)}")
ok(TR_CITY_EXONYMS["Qəbələ"] == "Gebele",
   "Qəbələ uses the Turkish form, not the English 'Gabala'")

# cities: exonym table where one exists, mechanical ə->e fold for the rest
ok(render_value("CITY", "Bakı", "tr", rng) == "Bakü",
   "tr CITY exonym: Bakı -> Bakü")
ok(render_value("CITY", "Naxçıvan", "tr", rng) == "Nahçıvan",
   "tr CITY exonym: Naxçıvan -> Nahçıvan (not a character-map result)")
ok("Astara" not in TR_CITY_EXONYMS, "Astara has no exonym entry (sanity)")
ok(render_value("CITY", "Astara", "tr", rng) == "Astara",
   "tr CITY mechanical fallback: no ə, unchanged")

# streets: the AZ-generator's bundled type word is translated, stem is not
ok(render_value("STREET", "Nizami küçəsi", "tr", rng) == "Nizami Caddesi",
   "tr STREET type word: küçəsi -> Caddesi")
ok(render_value("STREET", "Azadlıq prospekti", "tr", rng) == "Azadlıg Bulvarı",
   "tr STREET type word: prospekti -> Bulvarı, stem folded q->g")

# ---------------------------------------------------------------- anchors
print("anchors_en")

A = anchors_en
ok(A.has_anchor("AGE", "The patient is 34 years old.", 15, 17), "AGE: 'years old' after")
ok(A.has_anchor("AGE", "Age: 34", 5, 7), "AGE: 'Age:' before")
ok(not A.has_anchor("AGE", "We ordered 34 units of cable.", 11, 13),
   "AGE: bare number in unrelated prose is unlicensed")
ok(A.has_anchor("CARD_SECURITY_CODE", "check the CVV: 907 code", 15, 18), "CVV")
ok(A.has_anchor("CARD_SECURITY_CODE", "card security code 907", 19, 22),
   "'security code' phrase")
ok(not A.has_anchor("CARD_SECURITY_CODE", "Building 907 is closed.", 9, 12),
   "CVV: unrelated 3-digit number unlicensed")
ok(A.has_anchor("BUILDINGNUM", "Apt 23, Nizami Street", 4, 6), "BUILDINGNUM: Apt")
ok(A.has_anchor("BUILDINGNUM", "84 Nizami Street", 0, 2), "BUILDINGNUM: street after")
ok(A.has_anchor("TIME", "The meeting starts at 14:30.", 22, 27), "TIME: 'at'")
ok(A.has_anchor("DATE", "Date of birth: 21.02.1956", 15, 25), "DATE: numeric self-signals")
ok(A.has_anchor("DATE", "signed on 21 February 1956", 10, 26),
   "DATE: worded form self-signals")
ok(A.has_anchor("DATE", "Friday, 21 February 1956 was the day", 0, 24),
   "DATE: weekday-prefixed self-signals")
ok(A.has_anchor("EMAIL", "whatever", 0, 3), "non-anchor label always licensed")

# ------------------------------------------------------------- anchors_tr
print("anchors_tr")

# For each of the 5 anchor_required labels: clean-spelling anchor before the
# value, clean-spelling anchor after, diacritic-stripped anchor before,
# diacritic-stripped anchor after, and a negative (bare number/value in
# unrelated prose, no anchor -- must NOT fire). Values are chosen to avoid
# SELF_SIGNALLING shapes (a full "12.05.1990" or "14:30" would license
# itself regardless of the anchor word list, which would test the wrong
# thing) so every case genuinely exercises the ported Turkish word lists.


def tr_case(label: str, text: str, value: str, expect: bool, note: str) -> None:
    start = text.index(value)
    end = start + len(value)
    ok(anchors_tr.has_anchor(label, text, start, end) == expect,
       f"anchors_tr {label}: {note}", text)


# AGE
tr_case("AGE", "Yaşı: 34, hastaneye kaldırıldı.", "34", True, "clean, pre")
tr_case("AGE", "Hasta 34 yaşındadır.", "34", True, "clean, post")
tr_case("AGE", "Yasi: 34, hastaneye kaldirildi.", "34", True, "stripped, pre")
tr_case("AGE", "Musteri 34 yasinda.", "34", True, "stripped, post")
tr_case("AGE", "Depoda 34 adet ürün var.", "34", False, "negative: no anchor")

# BUILDINGNUM
tr_case("BUILDINGNUM", "Daire No: 12, üçüncü katta.", "12", True, "clean, pre")
tr_case("BUILDINGNUM", "Nizami Caddesi 45 numaralı binada oturuyoruz.", "45",
        True, "clean, post")
tr_case("BUILDINGNUM", "Kapi No: 7, zemin katta.", "7", True, "stripped, pre")
tr_case("BUILDINGNUM", "Bulvarı 22, kapisinda teslim alınır.", "22", True,
        "stripped, post")
tr_case("BUILDINGNUM", "Siparişte 45 adet kalem listelendi.", "45", False,
        "negative: no anchor")

# CARD_SECURITY_CODE
tr_case("CARD_SECURITY_CODE", "Kartın güvenlik kodu: 483, lütfen doğrulayın.",
        "483", True, "clean, pre")
tr_case("CARD_SECURITY_CODE", "Kartın arkasındaki 907 CVV değeridir.", "907",
        True, "clean, post (bare CVV)")
tr_case("CARD_SECURITY_CODE",
        "Kartin guvenlik kodu: 512, dogrulama icin gereklidir.", "512", True,
        "stripped, pre")
tr_case("CARD_SECURITY_CODE",
        "678 guvenlik kodu olarak sistemde kayitlidir.", "678", True,
        "stripped, post")
tr_case("CARD_SECURITY_CODE", "Fatura toplamı 245 TL'dir.", "245", False,
        "negative: no anchor")

# DATE (values avoid the day.month.year / ISO / worded+year self-signalling
# shape on purpose -- see module note above)
tr_case("DATE", "Doğum tarihi: 1990, kayıt tamamlandı.", "1990", True,
        "clean, pre")
tr_case("DATE", "Kayıt 1990 tarihinde yapılmıştır.", "1990", True,
        "clean, post")
tr_case("DATE", "Gecerlilik tarihi: 1990, sozlesme imzalandi.", "1990", True,
        "stripped, pre")
tr_case("DATE",
        "Sozlesme 1990 yururluk tarihinden itibaren gecerlidir.", "1990",
        True, "stripped, post")
tr_case("DATE", "Toplantıda 1990 kişi vardı.", "1990", False,
        "negative: no anchor")

# TIME (value avoids the HH:MM self-signalling shape on purpose)
tr_case("TIME", "Saat 14'te toplantı başlayacak.", "14", True, "clean, pre")
tr_case("TIME", "Randevu 14 saatinde planlanmıştır.", "14", True,
        "clean, post")
tr_case("TIME", "Baslangic saat 14, katilim zorunludur.", "14", True,
        "stripped, pre")
tr_case("TIME", "Toplanti 14 baslangic saatinde yapilacaktir.", "14", True,
        "stripped, post")
tr_case("TIME", "Ekipte 14 kişi görevlendirildi.", "14", False,
        "negative: no anchor")

ok(anchors_tr.has_anchor("EMAIL", "whatever", 0, 3),
   "anchors_tr: non-anchor label always licensed")

# ---------------------------------------------------------------- prompt
print("prompt")

sp = system_prompt("en")
ok("⟦" in sp and "⟧" in sp, "prompt names the sentinel characters")
ok("English" in sp, "prompt names the target language")
ok("register" in sp.lower(), "prompt asks for register preservation")
ok("Only" in sp or "ONLY" in sp, "prompt forbids preamble")
ok(len(build_messages("x", "ru")) == 2 and "Cyrillic" in system_prompt("ru"),
   "ru prompt mentions Cyrillic")

# The forbidden-letter list must be the letters the TARGET alphabet lacks.
# Turkish has ç ğ ı ö ş ü natively; banning them (as the prompt did until
# 2026-09-06) contradicts the same prompt's "use natural Turkish
# orthography" note and pushes the model to ASCII-fold its Turkish.
_tr_prompt = system_prompt("tr")
_forbidden = re.search(r"must not contain (.+?)\. If", _tr_prompt).group(1)
for _tr_letter in "çğıöşü":
    ok(_tr_letter not in _forbidden,
       f"tr prompt does not forbid the Turkish letter {_tr_letter!r}",
       _forbidden)
for _az_only in "əqx":
    ok(_az_only in _forbidden,
       f"tr prompt forbids {_az_only!r} (absent from the Turkish alphabet)",
       _forbidden)
ok("ğ" in re.search(r"must not contain (.+?)\. If",
                    system_prompt("en")).group(1),
   "en prompt still forbids ğ (English has no such letter)")

# The prompt must not contain a token-SHAPED string that is not a real
# token: the model echoed a literal "⟦N⟧" out of the format description
# into one Turkish document, and "reproduce every one EXACTLY as written"
# applies to the example just as well as to a real token (2026-09-06).
for _lg in ("en", "tr", "ru"):
    _p = system_prompt(_lg)
    ok("\u27e6N\u27e7" not in _p,
       f"{_lg} prompt has no literal token-shaped placeholder example")
    ok(set(re.findall(r"\u27e6(.{0,3}?)\u27e7", _p)) <= {" ", "0", "1", "2"},
       f"{_lg} prompt shows only real numbered tokens",
       sorted(set(re.findall(r"\u27e6(.{0,3}?)\u27e7", _p))))

# Turkish worked examples: names are re-spelled, never swapped for a cognate.
_trn = system_prompt("tr")
ok("Məmmədov->Memmedov" in _trn and "never Mehmet" in _trn,
   "tr prompt shows name RE-SPELLING and forbids the cognate swap")
ok("müştəri->müşteri" in _trn,
   "tr prompt shows a near-Turkish common word being translated")
ok(token_budget("a" * 100) >= 512, "token budget has a floor")
ok(token_budget("a" * 100000) <= 16384, "token budget has a ceiling")
ok(token_budget("a" * 5000) > token_budget("a" * 500), "budget scales with length")

# ---------------------------------------------------------------- guard
print("guard")

ok(EXPECTED_SCRIPTS["ru"] == ("cyrillic",), "ru locked to cyrillic")
ok(EXPECTED_SCRIPTS["en"] == EXPECTED_SCRIPTS["tr"] == ("latin",),
   "en/tr locked to latin")

clean = ["The customer called about the invoice ", "and asked for a callback "
         "regarding the outstanding balance on their account."]
res = guarded_stream(iter(clean), "en")
ok(res.state in ("clean", "suspect") and res.text == "".join(clean),
   "clean stream passes through intact", res.state)

drift = ["The customer called "] + ["и потом всё пошло не так " for _ in range(40)]
try:
    guarded_stream(iter(drift), "en")
    ok(False, "script drift + repetition aborts")
except GuardAborted as exc:
    ok(bool(exc.reasons), "script drift aborts with reasons", exc.reasons[:2])


class _ClosableIter:
    def __init__(self, items):
        self._it = iter(items)
        self.closed = False

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._it)

    def close(self):
        self.closed = True


src = _ClosableIter(drift)
try:
    guarded_stream(src, "en")
except GuardAborted:
    pass

# a legitimately digit-dense translation (identifier list) must NOT abort --
# SIMURG's numeric-dump verdict is downgraded to `suspect`
from translate.guard import _numeric_dump_only  # noqa: E402
ok(_numeric_dump_only(["numeric dump digit_frac=0.42"]), "numeric-dump-only detected")
ok(not _numeric_dump_only(["numeric dump digit_frac=0.42", "repetition loop rate=0.7"]),
   "numeric dump + repetition is NOT downgraded")
ok(not _numeric_dump_only([]), "no reasons is not a numeric-dump downgrade")
dense = ["Case FA-2025/6575: ", "AZ1994 and 774021864562 ", "0x49CBD993A91B ",
         "must be submitted, term ***-***-0824."]
res_d = guarded_stream(iter(dense), "en")
ok(res_d.state in ("clean", "suspect"), "digit-dense line does not abort", res_d.state)

# a long digit-dense stream: SIMURG goes corrupt early on numeric-dump, then
# every later feed says "already aborted" -- the latch must hold, not
# re-raise on the follow-up reason
long_dense = [f"[2020-04-{i:02d} 10:15:{i:02d}] ID {1000000+i*7} hash "
              f"{i:08x} status {i%3}\n" for i in range(1, 40)]
res_ld = guarded_stream(iter(long_dense), "en")
ok(res_ld.state == "suspect",
   "sustained digit-dump stays suspect (no 'already aborted' re-raise)",
   res_ld.state)
ok(src.closed, "aborting closes the underlying stream")

# ---------------------------------------------------------------- validate
print("validate")


def _rec(text, ents, lang="en"):
    return {"text": text, "entities": ents, "lang": lang, "id": "x__en",
            "source_id": "x", "split": "train"}


good_text = "The customer called from +994 70 234 56 78 about the invoice."
good = _rec(good_text, [{"start": 25, "end": 42, "label": "TELEPHONENUM"}])
assert good_text[25:42] == "+994 70 234 56 78"
TEMPLATED_GOOD = "Müştəri ⟦0⟧ nömrəsindən zəng edərək hesab barədə soruşdu."
SOURCE_GOOD = "Müştəri +994501112233 nömrəsindən zəng edərək hesab barədə soruşdu."
r = validate_record(good, source_text=SOURCE_GOOD, templated=TEMPLATED_GOOD,
                    minted={0: "+994 70 234 56 78"})
ok(r.ok, "clean record passes", r.failures)

r = validate_record(good, source_text=SOURCE_GOOD, templated=TEMPLATED_GOOD,
                    minted={0: "+994 70 999 99 99"})
ok(not r.ok and any("span_not_exact" in f for f in r.failures),
   "span mismatch caught", r.failures)

# entity_count must count ENTITY slots, not every sentinel in `templated` --
# once sentinelize_protected() adds decoy/shadow sentinels, the two diverge
# and counting all of them fails ~every negative record (the 2026-09-05 bug).
TEMPLATED_WITH_DECOYS = "Order ⟦0⟧ ref ⟦1⟧: customer ⟦2⟧ called."   # 2 decoys + 1 entity
r = validate_record(good, source_text=SOURCE_GOOD,
                    templated=TEMPLATED_WITH_DECOYS,
                    minted={0: "+994 70 234 56 78"}, expected_entities=1)
ok(r.ok, "entity_count uses expected_entities, not the sentinel count",
   r.failures)
r = validate_record(good, source_text=SOURCE_GOOD,
                    templated=TEMPLATED_WITH_DECOYS,
                    minted={0: "+994 70 234 56 78"}, expected_entities=2)
ok(not r.ok and any("entity_count" in f for f in r.failures),
   "entity_count still catches a genuine drift", r.failures)

bad = _rec("Text with ⟦0⟧ left in it and a number +994 70 234 56 78 here.",
           [{"start": 37, "end": 54, "label": "TELEPHONENUM"}])
r = validate_record(bad, source_text="x", templated="⟦0⟧", minted=None)
ok(any("sentinel_survived" in f for f in r.failures), "surviving sentinel caught",
   r.failures)

r = validate_record(_rec("Müştəri və sifariş üçün ödəniş edilmişdir tamam.", []),
                    source_text="The customer and the order have been paid in full now.", templated="a b c", minted={})
ok(any("leftover_azerbaijani" in f for f in r.failures),
   "untranslated Azerbaijani caught", r.failures)

# a transliterated email is fine -- its local part must not trip the folded
# marker-word list
r = validate_record(_rec("Forwarded from: musteri_sikayet@mail.az about the order.", []),
                    source_text="Yönləndirilmiş: musteri_sikayet@mail.az sifariş barədə.", templated="a" * 40, minted={})
ok(not any("leftover_azerbaijani" in f for f in r.failures),
   "transliterated email local part is not flagged", r.failures)
# but an UN-transliterated one still is (the ə survives)
r = validate_record(_rec("Forwarded from: mərkəzi@mail.az about the order.", []),
                    source_text="Yönləndirilmiş: mərkəzi@mail.az sifariş barədə məsələ.", templated="a" * 40, minted={})
ok(any("leftover_azerbaijani" in f for f in r.failures),
   "email still carrying ə is caught", r.failures)

r = validate_record(_rec("Here is the translation: the customer called.", []),
                    source_text="Budur tərcümə: müştəri zəng etdi filan.", templated="a" * 40, minted={})
ok(any("preamble" in f for f in r.failures), "preamble caught", r.failures)

r = validate_record(_rec("short", []), source_text="x" * 500,
                    templated="a" * 500, minted={})
ok(any("length_ratio" in f for f in r.failures), "truncation caught", r.failures)

# X-TOK: a re-minted value of another length is not the translation's length. A 47-char token in the source,
# a 400-char JWT spliced into a faithful translation: no length_ratio failure. A truncated translation with a
# short new token is still caught.
_src_tok = "pat_" + "a1B2" * 10 + "c3D"
_src = f"Sessiya üçün yeni token {_src_tok} yaradılıb və tətbiqə ötürülüb."
_new_tok = "eyJ" + "x9Y8" * 99 + "z"
_out = f"A new token {_new_tok} was created for the session and passed to the app."
_i = _out.index(_new_tok)
r = validate_record(_rec(_out, [{"start": _i, "end": _i + len(_new_tok), "label": "ACCESS_TOKEN"}]),
                    source_text=_src, templated="Sessiya üçün yeni token ⟦0⟧ yaradılıb və tətbiqə ötürülüb.",
                    minted={0: _new_tok}, source_values=[_src_tok])
ok(not any("length_ratio" in f for f in r.failures), "a long re-minted token is not a length failure", r.failures)
_short = "x9Y8" * 3
_cut = f"Token {_short}."
r = validate_record(_rec(_cut, [{"start": 6, "end": 6 + len(_short), "label": "ACCESS_TOKEN"}]),
                    source_text=_src + " " + "Əlavə izahat burada uzun bir cümlə kimi davam edir. " * 4,
                    templated="x", minted={0: _short}, source_values=[_src_tok])
ok(any("length_ratio" in f for f in r.failures), "truncation still caught with a short new token", r.failures)

# Was: asserted lang="tr" hard-failed with no_anchor_module, back when no
# Turkish anchor module existed. anchors_tr.py now exists and is registered
# in ANCHOR_MODULES (Phase 3), so that failure mode is gone -- this now
# asserts the positive case instead: a real, anchored AGE entity in a
# Turkish record validates successfully end-to-end through validate_record.
tr_age_text = "Hasta 34 yaşındadır."
tr_age_start = tr_age_text.index("34")
tr_age_end = tr_age_start + 2
assert tr_age_text[tr_age_start:tr_age_end] == "34"
r = validate_record(
    _rec(tr_age_text, [{"start": tr_age_start, "end": tr_age_end,
                        "label": "AGE", "text": "34"}], lang="tr"),
    source_text="O 34 yaşındadır.", templated="O ⟦0⟧ yaşındadır.",
    minted={0: "34"})
ok(r.ok, "tr: anchored AGE validates successfully (anchors_tr registered)",
   r.failures)

unanchored = "We shipped 34 units of cable to the depot this morning."
r = validate_record(_rec(unanchored, [{"start": 11, "end": 13, "label": "AGE"}]),
                    source_text="x", templated=unanchored, minted={0: "34"})
ok(any("anchor_missing" in f for f in r.failures),
   "unanchored AGE caught", r.failures)

r = validate_record(good, source_text=SOURCE_GOOD, templated=TEMPLATED_GOOD,
                    minted={0: "+994 70 234 56 78"}, guard_state="suspect")
ok(r.ok and any("simurg_suspect" in w for w in r.warnings),
   "SIMURG 'suspect' warns but does not fail", r.warnings)

# --- English-track checks ---------------------------------------------- #
# invented, untagged PII -- the model completing a signature block or a
# "Sender:" header it was never given. 884 records (0.84%) shipped with this
# before the check was ported from validate_corpus.py (2026-09-04 audit).
_inv = _rec("Respectfully,\nAli Valiyev\nCoordinator\nali.veliyev@numune.az", [])
r = validate_record(_inv, source_text="Hörmətlə,\nKoordinator" * 2,
                    templated="a" * 55, minted={})
ok(any("unlabeled_pii_leak" in f for f in r.failures),
   "invented untagged email is caught", r.failures)

# a decoy is PII-shaped ON PURPOSE and must not count as a leak
_dec_text = "Ref 4539578763621486 is an invalid card used as a decoy."
_dec = _rec(_dec_text, [])
r = validate_record(_dec, source_text=_dec_text, templated=_dec_text,
                    minted={}, decoys=["4539578763621486"])
ok(not any("unlabeled_pii_leak" in f for f in r.failures),
   "declared decoys are exempt from the leak sweep", r.failures)
r = validate_record(_dec, source_text=_dec_text, templated=_dec_text,
                    minted={}, decoys=[])
ok(any("unlabeled_pii_leak" in f for f in r.failures),
   "the same string with no decoy declaration IS a leak", r.failures)

# an email the AZ source itself carries UNTAGGED (a header/signature the AZ
# corpus never tagged, invisible to its ASCII-only find_leaked_pii because of
# the AZ letters) is not a translation defect -- it is an inherited gap, and
# holding EN to a stricter standard than its own source loses 0.7% of the
# corpus for nothing (2026-09-05 audit).
from translate.validate import inherited_leak_exemptions
_az_hdr = "Göndərən: hüquq_dep@barama.io\nMüştəri sifariş barədə yazdı."
_en_hdr = _rec("From: huquq_dep@barama.io\nThe customer wrote about the order.", [])
_exempt = inherited_leak_exemptions(_az_hdr, [])
r = validate_record(_en_hdr, source_text=_az_hdr, templated="a" * 55, minted={})
ok(any("unlabeled_pii_leak" in f for f in r.failures),
   "inherited header email IS a leak without the exemption", r.failures)
r = validate_record(_en_hdr, source_text=_az_hdr, templated="a" * 55, minted={},
                    inherited_leak_domains=_exempt)
ok(not any("unlabeled_pii_leak" in f for f in r.failures),
   "inherited header email is exempt when its domain is in the AZ source",
   r.failures)
# a different domain, not present in the AZ source, is still a genuine leak
_en_other = _rec("From: invented@fabricated-co.net\nThe customer wrote in.", [])
r = validate_record(_en_other, source_text=_az_hdr, templated="a" * 55,
                    minted={}, inherited_leak_domains=_exempt)
ok(any("unlabeled_pii_leak" in f for f in r.failures),
   "an email whose domain is NOT in the AZ source stays a leak", r.failures)

# --- Turkish-track checks ---------------------------------------------- #
# --- Turkish is Azerbaijani's sister language: six folded markers are
# ordinary Turkish and must not read as "untranslated Azerbaijani". These
# six accounted for 25 of 28 repair-queue entries on the 2026-09-06
# calibration set, every one a correct translation.
from translate.validate import (MARKER_WORDS_BY_LANG,  # noqa: E402
                                TR_UNUSABLE_MARKERS,
                                _leftover_azerbaijani,
                                inherited_leak_exemptions)

_tr_good = ("Tüm işlemler kontrol edilmelidir ve talep kabul edilir. "
            "Müşteri soyadı kayıtlıdır, rica olunur.")
ok(_leftover_azerbaijani(_tr_good, [], "tr") == [],
   "tr: fluent Turkish passives are not 'leftover Azerbaijani'",
   _leftover_azerbaijani(_tr_good, [], "tr"))
ok(_leftover_azerbaijani(_tr_good, [], "en") != [],
   "en: the same folded words DO still flag for an English target")
ok(TR_UNUSABLE_MARKERS < MARKER_WORDS_BY_LANG["en"],
   "the Turkish drop-set is a subset of the full marker list")
ok(not (MARKER_WORDS_BY_LANG["tr"] & TR_UNUSABLE_MARKERS),
   "the Turkish marker list contains none of the collisions")
# ə is not a Turkish letter, so schwa-carrying markers stay usable and the
# hard ə signal still fires for Turkish.
ok(_leftover_azerbaijani("Sənəd təsdiq edilməlidir.", [], "tr") != [],
   "tr: real untranslated Azerbaijani is still caught")
ok(_leftover_azerbaijani("Ödəniş üçün müraciət olunur.", [], "tr") != [],
   "tr: schwa alone is enough to catch untranslated Azerbaijani")

# --- invented, untagged PII (ported from the English track, where 0.84% of
# records shipped with a model-invented Sender:/signature block).
_inv = _rec("Saygılarımızla,\nAli Veliyev\nKoordinatör\nali.veliyev@ornek.az",
            [], lang="tr")
r = validate_record(_inv, source_text="Hörmətlə,\nKoordinator" * 2,
                    templated="a" * 55, minted={})
ok(any("unlabeled_pii_leak" in f for f in r.failures),
   "tr: invented untagged email is caught", r.failures)

# a decoy is PII-shaped ON PURPOSE and must not count as a leak
_dec_text = "Sipariş 4539578763621486 numarası geçersizdir."
_dec = _rec(_dec_text, [], lang="tr")
r = validate_record(_dec, source_text=_dec_text, templated=_dec_text,
                    minted={}, decoys=["4539578763621486"])
ok(not any("unlabeled_pii_leak" in f for f in r.failures),
   "tr: declared decoys are exempt from the leak sweep", r.failures)

# an email the AZ source itself carries UNTAGGED is an inherited gap, not a
# translation defect -- holding Turkish to a stricter standard than its own
# source would drop good records (727 of them on the English track).
_az_hdr = "Göndərən: ən-yaxşı-vətəndaş@mail.com\nMüştəri sifariş barədə yazdı."
_tr_hdr = _rec("Gönderen: en-iyi-vatandas@mail.com\nMüşteri sipariş hakkında "
               "yazdı.", [], lang="tr")
_exempt = inherited_leak_exemptions(_az_hdr, [], "tr")
r = validate_record(_tr_hdr, source_text=_az_hdr, templated="a" * 55,
                    minted={})
ok(any("unlabeled_pii_leak" in f for f in r.failures),
   "tr: inherited header email IS a leak without the exemption", r.failures)
r = validate_record(_tr_hdr, source_text=_az_hdr, templated="a" * 55,
                    minted={}, inherited_leak_domains=_exempt)
ok(not any("unlabeled_pii_leak" in f for f in r.failures),
   "tr: inherited header email is exempt when its domain is in the source",
   r.failures)
_tr_other = _rec("Gönderen: uydurma@olmayan-sirket.net\nMüşteri yazdı.",
                 [], lang="tr")
r = validate_record(_tr_other, source_text=_az_hdr, templated="a" * 55,
                    minted={}, inherited_leak_domains=_exempt)
ok(any("unlabeled_pii_leak" in f for f in r.failures),
   "tr: an email absent from the AZ source stays a leak", r.failures)

# --- entity_count must count ENTITY slots, not every sentinel: once decoys
# and shadows are sentinelized the two diverge, and counting all of them
# fails ~every negative record.
_TEMPL_DECOYS = "Sipariş ⟦0⟧ ref ⟦1⟧: müşteri ⟦2⟧ aradı."   # 2 decoys + 1 entity
r = validate_record(good, source_text=SOURCE_GOOD, templated=_TEMPL_DECOYS,
                    minted={0: "+994 70 234 56 78"}, expected_entities=1)
ok(r.ok, "entity_count uses expected_entities, not the sentinel count",
   r.failures)
r = validate_record(good, source_text=SOURCE_GOOD, templated=_TEMPL_DECOYS,
                    minted={0: "+994 70 234 56 78"}, expected_entities=2)
ok(not r.ok and any("entity_count" in f for f in r.failures),
   "entity_count still catches a genuine drift", r.failures)

# --- decoy and shadow protection
from translate.sentinel import sentinelize_protected  # noqa: E402

_sp_text = "Sipariş ABC-123 ve tekrar ABC-123. Müşteri Elnur Kasımov aradı."
_sp_ents = [{"start": _sp_text.index("Elnur"), "end": _sp_text.index("Elnur") + 5,
             "label": "GIVENNAME"}]
_t, _slots = sentinelize_protected(_sp_text, _sp_ents, ["ABC-123"])
_kinds = [s["kind"] for s in _slots]
ok(_kinds.count("decoy") == 2, "both decoy occurrences are protected", _kinds)
ok(_kinds.count("entity") == 1, "the tagged entity is one entity slot", _kinds)
ok("ABC-123" not in _t, "decoy text is replaced by a sentinel", _t)

_sh_text = "Elnur geldi. Dosya: Elnur.pdf"     # 2nd Elnur untagged in AZ
_sh_ents = [{"start": 0, "end": 5, "label": "GIVENNAME"}]
_t2, _slots2 = sentinelize_protected(_sh_text, _sh_ents, [])
ok([s["kind"] for s in _slots2] == ["entity", "shadow"],
   "an untagged repeat occurrence becomes a shadow slot",
   [s["kind"] for s in _slots2])
ok("Elnur" not in _t2, "the shadow occurrence is protected too", _t2)

# --- characters that are never legitimate in training text. The Azerbaijani
# source contains none of them (0 across all 84,339 train records), so any
# occurrence is corruption introduced by the model or the transport -- two
# Turkish records picked up a U+FFFD before this check existed (2026-09-06).
_AZ_SRC = "Emeliyyat tamamlandi, lutfen bir az gozleyin." * 3
for _name, _bad in [("U+FFFD replacement", "\ufffd"),
                    ("private-use", "\ue000"),
                    ("unassigned", "\u0378")]:
    _r = validate_record(
        _rec(f"Islem tamamlandi.{_bad} Lutfen bekleyin ve tekrar deneyiniz.",
             [], lang="tr"),
        source_text=_AZ_SRC, templated="a" * 40, minted={})
    ok(any("corrupt_char" in f for f in _r.failures),
       f"{_name} character is rejected", _r.failures)
_r = validate_record(
    _rec("Islem tamamlandi. Lutfen bekleyin ve tekrar deneyiniz.", [], lang="tr"),
    source_text=_AZ_SRC, templated="a" * 40, minted={})
ok(not any("corrupt_char" in f for f in _r.failures),
   "clean Turkish text has no corrupt_char failure", _r.failures)

# --- an ORIGINAL Azerbaijani entity value still in the output means the
# document names the same fact twice: once as the fresh value, once as the
# Azerbaijani original. This was audit-only until 2026-09-06, so run.py
# accepted such records and 29 reached the Turkish corpus.
_STALE_AZ = "Men Astarada yasayan biriyem, uzun illerdir musterinizem." * 2
_r = validate_record(
    _rec("Ben Astara (hayır, Şeki) bölgesinde yaşayan biriyim.",
         [{"start": 18, "end": 22, "label": "CITY"}], lang="tr"),
    source_text=_STALE_AZ, templated="a" * 40, minted=None,
    source_values=["Astara"])
ok(any("stale_az_value" in f for f in _r.failures),
   "an untagged original AZ value is caught", _r.failures)
# the same value INSIDE a tagged span is a minting collision, not a leak
_coll = "Ben Astara bölgesinde yaşayan biriyim, uzun yıllardır müşterinizim."
_r = validate_record(
    _rec(_coll, [{"start": 4, "end": 10, "label": "CITY"}], lang="tr"),
    source_text=_STALE_AZ, templated="a" * 40, minted=None,
    source_values=["Astara"])
ok(not any("stale_az_value" in f for f in _r.failures),
   "a minting collision (value IS the tagged span) is exempt", _r.failures)
# and a match inside a decoy is the decoy, spliced back verbatim by design
_r = validate_record(
    _rec(_coll, [], lang="tr"), source_text=_STALE_AZ, templated="a" * 40,
    minted=None, source_values=["Astara"], decoys=["Astara bölgesinde"])
ok(not any("stale_az_value" in f for f in _r.failures),
   "a value inside a declared decoy is exempt", _r.failures)
# short values are not matched (too collision-prone)
_r = validate_record(
    _rec("Bina 12 numarada bulunmaktadır, lütfen oraya gidiniz efendim.",
         [], lang="tr"),
    source_text=_STALE_AZ, templated="a" * 40, minted=None,
    source_values=["Bina"])
ok(not any("stale_az_value" in f for f in _r.failures),
   "values shorter than STALE_MIN_LEN are not matched", _r.failures)

# ------------------------------------------------ mint order-independence
print("mint determinism")

from translate.run import mint_values  # noqa: E402

_labels = ["GIVENNAME", "SURNAME", "CITY", "TELEPHONENUM", "DATE", "STREET"]
_srcvals = ["Əli", "Məmmədov", "Bakı", "+994501234567", "12.03.1990", "Nizami küçəsi"]
_v1 = mint_values(_labels, _srcvals, "en", "src123|en")
_v2 = mint_values(_labels, _srcvals, "en", "src123|en")
ok(_v1 == _v2, "same seed -> identical values")
ok(mint_values(_labels, _srcvals, "en", "other|en") != _v1, "different seed -> different values")

# repeat mentions: two slots with the same (label, source value) must mint
# to the SAME fresh value -- this is the corpus-wide bug the 5000-doc golden
# check surfaced (2026-09-04): independent per-slot minting gave 5 different
# times for one incident, two different names for one person.
_rep_labels = ["TIME", "GIVENNAME", "TIME", "SURNAME", "TIME"]
_rep_src = ["18:53", "Fatimə", "18:53", "Ramazanova", "18:53"]
_rep_vals = mint_values(_rep_labels, _rep_src, "en", "rep-doc|en")
ok(_rep_vals[0] == _rep_vals[2] == _rep_vals[4],
   "three mentions of the same source TIME mint identically", _rep_vals)
ok(_rep_vals[1] != _rep_vals[0] and _rep_vals[3] != _rep_vals[0],
   "different labels/values still mint independently", _rep_vals)
# same label, DIFFERENT source values -- must be independent draws, not merged
_distinct_vals = mint_values(["TIME", "TIME"], ["18:53", "09:12"], "en", "x|en")
ok(_distinct_vals[0] != _distinct_vals[1],
   "different source values stay independent groups even with the same label",
   _distinct_vals)
# the point of minting in slot order: splicing in ANY order gives the same
# text, because splice() looks each value up by slot, not draw order
from translate.sentinel import splice as _spl  # noqa: E402
_, _sp2 = _spl("A ⟦5⟧ B ⟦0⟧ C ⟦3⟧ D ⟦1⟧ E ⟦4⟧ F ⟦2⟧ G", lambda i: _v1[i])
by_slot = {s["slot"]: s for s in _sp2}
_txt2, _ = _spl("A ⟦5⟧ B ⟦0⟧ C ⟦3⟧ D ⟦1⟧ E ⟦4⟧ F ⟦2⟧ G", lambda i: _v1[i])
ok(all(_txt2[by_slot[i]["start"]:by_slot[i]["end"]] == _v1[i] for i in range(6)),
   "reordered splice: each slot's span holds exactly its own value")

# ------------------------------------------------- end-to-end on real docs
print("end-to-end (real corpus documents, no API)")

if not AZ_TRAIN.exists():
    print(f"  SKIP -- {AZ_TRAIN} not present")
else:
    from translate.run import mint_values as _mint_values  # noqa: E402
    checked = spans_exact = repeat_docs = repeat_consistent = 0
    with AZ_TRAIN.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if not rec["entities"]:
                continue
            checked += 1
            if checked > 300:
                break
            templated, labels = sentinelize(rec["text"], rec["entities"])
            source_values = entity_source_values(rec["text"], rec["entities"])

            # every value removed
            for e in rec["entities"]:
                val = rec["text"][e["start"]:e["end"]]
                # Only values occurring once can be asserted absent: the
                # corpus legitimately contains repeat mentions where just one
                # occurrence is annotated (a known, tracked class -- see
                # validate_corpus.py's repeat_mention_incomplete check).
                if len(val) > 4 and rec["text"].count(val) == 1:
                    ok(val not in templated,
                       "value removed from templated text", f"{rec['id']}: {val!r}")

            # use the REAL mint_values, not a hand-rolled stand-in -- this is
            # the test that would have caught the 2026-09-04 repeat-mention
            # bug (independent per-slot minting) before 28k documents shipped
            # with it. See mint_values' own tests above for the isolated
            # case; this is the same property against real corpus documents.
            values = _mint_values(labels, source_values, "en", f"{rec['id']}|en")
            text, spans = splice(templated, lambda i: values[i])
            good_doc = all(text[sp["start"]:sp["end"]] == values[sp["slot"]]
                           for sp in spans)
            if not good_doc:
                print(f"  FAIL span in {rec['id']}")
            spans_exact += good_doc

            groups = {}
            for i, key in enumerate(zip(labels, source_values)):
                groups.setdefault(key, []).append(i)
            repeats = [g for g in groups.values() if len(g) >= 2]
            if repeats:
                repeat_docs += 1
                if all(len({values[i] for i in g}) == 1 for g in repeats):
                    repeat_consistent += 1
                else:
                    print(f"  FAIL repeat-group inconsistent in {rec['id']}")
    ok(spans_exact == min(checked, 300),
       f"all {min(checked, 300)} real docs splice with byte-exact spans",
       f"{spans_exact} ok")
    ok(repeat_docs > 0, "sample actually includes repeat-mention documents",
       repeat_docs)
    ok(repeat_consistent == repeat_docs,
       "every repeat-mention document mints its repeats identically",
       f"{repeat_consistent}/{repeat_docs}")
    print(f"  {min(checked, 300)} documents round-tripped, "
         f"{repeat_docs} had repeat mentions")

print(f"\n{'=' * 56}\nPASSED {PASS}   FAILED {FAIL}\n{'=' * 56}")
sys.exit(1 if FAIL else 0)
