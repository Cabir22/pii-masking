"""D-56c translation fixes (TR/RU check): translate/morph.py and
how the runners use it. Every case is one the team reported or its rule.

Run: python scripts/translate/test_morph.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from translate import morph as M  # noqa: E402

PASS = FAIL = 0


def ok(cond, msg, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  FAIL {msg}" + (f"  [{detail}]" if detail else ""))


def ents_of(text, items):
    out, pos = [], 0
    for v, lab in items:
        i = text.index(v, pos)
        out.append({"start": i, "end": i + len(v), "label": lab})
        pos = i + len(v)
    return out


# -- (1) gender ----------------------------------------------------------------------
t = "Müraciət edən: Aysel Məmmədova, Hadiyev Şadalı Möhkəm oğlu, Nərmin xanım, Elvin Babayev."
e = ents_of(t, [("Aysel", "GIVENNAME"), ("Məmmədova", "SURNAME"), ("Hadiyev", "SURNAME"), ("Şadalı", "GIVENNAME"),
                ("Möhkəm", "GIVENNAME"), ("Nərmin", "GIVENNAME"), ("Elvin", "GIVENNAME"), ("Babayev", "SURNAME")])
g = M.person_genders(t, e, [t[x["start"]:x["end"]] for x in e])
ok(g[0] == g[1] == "f", "Aysel Məmmədova: female, both parts", g[:2])
ok(g[2] == g[3] == "m" and g[4] == "m", "Hadiyev Şadalı Möhkəm oğlu: male, the father's name male", g[2:5])
ok(g[5] == "f" and g[6] == g[7] == "m", "Nərmin (pool), Elvin Babayev male", g[5:])
ok(M.surname_gender("Əliyeva") == "f" and M.surname_gender("Həsənov") == "m" and M.surname_gender("Kərimli") is None,
   "surname endings")

# -- (2) case: the source span's case ------------------------------------------------
for lab, v, want in [("CITY", "Zərdabda", ("Zərdab", "LOC")), ("CITY", "Zərdabdakı", ("Zərdab", "REL")),
                     ("GIVENNAME", "Seyidalıya", ("Seyidalı", "DAT")), ("SURNAME", "Haşımovanın", ("Haşımova", "GEN")),
                     ("GIVENNAME", "Nadiri", ("Nadir", "ACC")), ("CITY", "Cəlilabadın", ("Cəlilabad", "GEN")),
                     ("STREET", "Dənizkənarı küçəsində", ("Dənizkənarı küçəsi", "LOC")), ("CITY", "Bakı'da", ("Bakı", "LOC")),
                     ("GIVENNAME", "Leyla", ("Leyla", None)), ("CITY", "Bakı", ("Bakı", None)),
                     ("SURNAME", "Məmmədov", ("Məmmədov", None)), ("GIVENNAME", "Aysel", ("Aysel", None))]:
    ok(M.source_case(lab, v) == want, f"source case of {v}", M.source_case(lab, v))

# -- (2) Turkish inflection -----------------------------------------------------------
for v, c, want in [("Bakü", "LOC", "Bakü'de"), ("Köçeriyeva", "GEN", "Köçeriyeva'nın"), ("Şirinhan", "DAT", "Şirinhan'a"),
                   ("Nizami Caddesi", "LOC", "Nizami Caddesi'nde"), ("Ahmet", "ABL", "Ahmet'ten"),
                   ("Gence", "ACC", "Gence'yi"), ("Hurşidov", "INS", "Hurşidov'la"), ("BAKÜ", "LOC", "BAKÜ'DE"),
                   ("Şeki", "REL", "Şeki'deki"), ("Nizami Cad.", "LOC", "Nizami Cad."), ("Sumgayıt", "COP", "Sumgayıt'tır")]:
    ok(M.tr_inflect(v, c) == want, f"tr {v}+{c}", M.tr_inflect(v, c))

# -- (2) Russian declension -----------------------------------------------------------
for v, lab, c, f, want in [("Нариман", "GIVENNAME", "INS", False, "Нариманом"), ("Гасанова", "SURNAME", "GEN", True, "Гасановой"),
                           ("Гасанова", "SURNAME", "ACC", True, "Гасанову"), ("Гасанов", "SURNAME", "DAT", False, "Гасанову"),
                           ("Гянджа", "CITY", "PREP", None, "Гяндже"), ("Сумгаит", "CITY", "PREP", None, "Сумгаите"),
                           ("Сумгаит", "CITY", "ACC", None, "Сумгаит"), ("Баку", "CITY", "PREP", None, "Баку"),
                           ("Айсел", "GIVENNAME", "GEN", True, "Айсел"), ("Лейла", "GIVENNAME", "GEN", True, "Лейлы"),
                           ("Гусейнзаде", "SURNAME", "GEN", False, "Гусейнзаде"), ("улица Низами", "STREET", "PREP", None, "улице Низами"),
                           ("ул. Низами", "STREET", "PREP", None, "ул. Низами")]:
    ok(M.ru_decline(v, lab, c, f) == want, f"ru {v}+{c}", M.ru_decline(v, lab, c, f))

# -- (2) tags in the model's text -----------------------------------------------------
t = "Adres ⟦0⟧COP. ⟦1⟧{INS} iletişim. ⟦2⟧ye de ki. ⟦4⟧'nin raporu. Saat ⟦5⟧'te. ⟦6⟧LOCAL"
t2, tags = M.take_tags(t)
t3 = M.take_tr_suffixes(t2, {0, 1, 2, 4, 6}, tags)
ok(tags == {0: "COP", 1: "INS", 2: "DAT", 4: "GEN"}, "tags with or without braces, and a glued Turkish ending", tags)
ok("⟦5⟧'te" in t3 and "⟦6⟧LOCAL" in t3 and "ye" not in t3.split("⟦2⟧")[1][:2], "a time keeps its ending; a word is no tag", t3)
ok(M.STRAY_TAG.search("bir {GEN} kelime") and not M.STRAY_TAG.search(t3), "a tag away from a marker is stray")
tg = {8: "GEN"}
M.spread_person_tags("Hesab ⟦7⟧ ⟦8⟧ adına.", tg, {7, 8}, "ru")
ok(tg == {7: "GEN", 8: "GEN"}, "ru: a full name declines every part", tg)
tg = {7: "GEN"}
M.spread_person_tags("Hesab ⟦7⟧ ⟦8⟧ adına.", tg, {7, 8}, "tr")
ok(tg == {8: "GEN"}, "tr: the ending goes on the last part", tg)

# -- (3) year ---------------------------------------------------------------------------
ok([M.source_year(x) for x in ("15.10.2019", "21.02.56", "5 aprel 2008", "2024-05-10", "10:30")] == [2019, 1956, 2008, 2024, None],
   "the source year")

# -- (10) masks -------------------------------------------------------------------------
m = M.mask_edits("Kart: 4885 1234 5678 0696 ... Kart son: ****0696", ["4885 1234 5678 0696"], ["5202-4014-9838-1123"])
ok(m == {"****0696": "****1123"}, "a mask of a value's last digits follows the new value", m)
ok(M.mask_edits("Kart son: ****9999", ["4885 1234 5678 0696"], ["5202"]) == {}, "a mask of no value in the document stays")
text, ents = M.apply_masks("A [X] ****0696 B", [{"start": 2, "end": 5, "label": "PAYMENT_CARD_NUMBER"}], m)
ok(text == "A [X] ****1123 B" and ents[0]["start"] == 2, "applied outside the spans", text)

# -- (6) year words ---------------------------------------------------------------------
t = "Дата: 23 апр. 2023-й год. и 18.05.1997 год, 1 мая 2008 год"
e = ents_of(t, [("23 апр. 2023", "DATE"), ("18.05.1997", "DATE"), ("1 мая 2008", "DATE")])
out, e2 = M.apply_text_edits(t, [dict(x) for x in e], M.year_word_edits(t, e, "ru"))
ok(out == "Дата: 23 апр. 2023 года. и 18.05.1997, 1 мая 2008 года"
   and all(out[x["start"]:x["end"]] == t[y["start"]:y["end"]] for x, y in zip(e2, e)), "ru year words, spans kept", out)
t = "Tarih: 1 Nisan 1968-ci yıl ve 5 Mart 2008. yıl, 17 Ağustos 2006 yılı ve 2006 yılı"
e = ents_of(t, [("1 Nisan 1968", "DATE"), ("5 Mart 2008", "DATE"), ("17 Ağustos 2006", "DATE")])
out, _ = M.apply_text_edits(t, [dict(x) for x in e], M.year_word_edits(t, e, "tr"))
ok(out == "Tarih: 1 Nisan 1968 ve 5 Mart 2008, 17 Ağustos 2006 ve 2006 yılı", "tr year words after a full date only", out)

# -- the runners --------------------------------------------------------------------------
from piigen.locales import ru as RU                     # noqa: E402
ok(all("̇" not in RU.render_value(lab, v) for lab, v in [("GIVENNAME", "İsif"), ("CITY", "İsmayıllı")]),
   "(5) no U+0307 after İ")
from translate.prompt import system_prompt              # noqa: E402
tr = system_prompt("tr")
ok("qiymət->fiyat" in tr and "sənəd->belge" in tr and "Əliyev->Aliyev" in tr and "Xətai->Hatai" in tr
   and "məlumat bazası->veritabanı" in tr and "{GEN}" in tr and "never a hyphen" in tr, "(9) Turkish prompt: table fixes, tags")
from translate.lang.tr.render import TR_CITY_EXONYMS     # noqa: E402
ok(TR_CITY_EXONYMS["Sumqayıt"] == "Sumgayıt", "(9) Sumgayıt")
from translate.validate import _leftover_azerbaijani     # noqa: E402
ok(_leftover_azerbaijani("Bu prosedurlar bilgi tabanında, TEKNİKİ ekip.", [], "tr") == ["prosedurlar", "tekniki", "bilgi tabanı"]
   and not _leftover_azerbaijani("Bu prosedürler veritabanında, TEKNİK ekip.", [], "tr"), "(9) Turkish calques rejected")
from piigen.locales import tr as TRL                     # noqa: E402
rng = random.Random(3)
ok(not any(". " in TRL.date(d, 2, 1990, rng).split(" ")[0] + " " for d in range(1, 29) for _ in range(20)),
   "(9) no `21. Şubat` date form")
import translate.run_ru as R                             # noqa: E402
ok("оглы" in R.SYSTEM_PROMPT and "ИНН" in R.SYSTEM_PROMPT and "{PREP}" in R.SYSTEM_PROMPT, "(4)(8)(2) Russian prompt")
chk = R._body_validator("⟦1⟧ ⟦2⟧ ⟦3⟧ oğlu, VÖEN: ⟦0⟧")
ok(chk("⟦1⟧ ⟦2⟧ ⟦3⟧ сын, ИНН: ⟦0⟧") == "patronymic", "(4) сын instead of оглы is rejected")
ok(chk("⟦1⟧ ⟦2⟧ ⟦3⟧ оглы, VÖEN: ⟦0⟧") == "voen_form", "(8) VÖEN must be ИНН")
ok(chk("⟦1⟧ ⟦2⟧ {GEN} ⟦3⟧ оглы, ИНН: ⟦0⟧") == "stray case tag", "(2) a tag away from a marker")
chk2 = R._body_validator("⟦0⟧ ⟦1⟧ ⟦2⟧ oğlu")
ok(chk2("оглы ⟦0⟧ ⟦1⟧ ⟦2⟧") == "patronymic order" and chk2("⟦0⟧ ⟦1⟧ ⟦2⟧ оглы") is None,
   "(4) оглы stays after the father's name")
from translate.lang.tr.render import _tr_place, _tr_name   # noqa: E402
ok(_tr_place("Camal Əliyev küçəsi") == "Camal Aliyev Caddesi" and _tr_name("Əliyeva", random.Random(1)) in ("Aliyeva", "Əliyeva")
   and _tr_name("Əli", random.Random(1)) in ("Eli", "Əli"), "(9) the surname Aliyev; the given name Eli")
from translate.run import mint_values, source_facts      # noqa: E402
doc = {"id": "t1", "text": "Aysel Məmmədova 12.03.2019 tarixində, 2019-cu ildə Zərdabda.",
       "entities": ents_of("Aysel Məmmədova 12.03.2019 tarixində, 2019-cu ildə Zərdabda.",
                           [("Aysel", "GIVENNAME"), ("Məmmədova", "SURNAME"), ("12.03.2019", "DATE"), ("Zərdabda", "CITY")])}
genders, years, cases = source_facts(doc)
ok(genders[:2] == ["f", "f"] and years[2] == 2019 and cases[3] == "LOC", "source facts", (genders, years, cases))
for lang in ("en", "tr"):
    vals = mint_values(["GIVENNAME", "SURNAME", "DATE", "CITY"], ["Aysel", "Məmmədova", "12.03.2019", "Zərdabda"],
                       lang, f"t1|{lang}", genders=genders, years=years)
    # -zadə/-li surnames are for either gender; a female person never gets a male one
    ok(M.surname_gender(vals[1]) != "m" and "2019" in vals[2], f"{lang}: no male surname, and the source year", vals)

# --------------------------------------------------------------------------- #
# The re-check of D-56c: M1-M6, and the splits of the full run (D-64c)
# --------------------------------------------------------------------------- #
import re as _re  # noqa: E402

# M3: `ə` is a front vowel and a vowel for the buffer `n`/`y`
ok(M.tr_inflect("Fərayət", "DAT") == "Fərayət'e" and M.tr_inflect("Nadiyə", "GEN") == "Nadiyə'nin"
   and M.tr_inflect("Nadiyə", "DAT") == "Nadiyə'ye" and M.tr_inflect("Bakü", "LOC") == "Bakü'de",
   "M3: ə in Turkish endings", (M.tr_inflect("Fərayət", "DAT"), M.tr_inflect("Nadiyə", "GEN")))

# M5: year words after a full date
def _yw(text, date, lang):
    e = [{"start": text.index(date), "end": text.index(date) + len(date), "label": "DATE"}]
    out, _ = M.apply_text_edits(text, e, M.year_word_edits(text, e, lang))
    return out
ok(_yw("Tarih: 27 Mayıs 2015 yılında\nSüre", "27 Mayıs 2015", "tr") == "Tarih: 27 Mayıs 2015\nSüre"
   and _yw("üzerine 22 Mart 2016 yılında yerinde", "22 Mart 2016", "tr") == "üzerine 22 Mart 2016 tarihinde yerinde"
   and _yw("Olay 22 Haziran 2017'ci yıl tarihinde", "22 Haziran 2017", "tr") == "Olay 22 Haziran 2017 tarihinde"
   and _yw("TARİH: 18/04/2022. Yıl\nX", "18/04/2022", "tr") == "TARİH: 18/04/2022\nX"
   and _yw("Bitti 18/04/2022. Yıl sonunda ödeme", "18/04/2022", "tr") == "Bitti 18/04/2022. Yıl sonunda ödeme"
   and _yw("от 18.03.2020-го года", "18.03.2020", "ru") == "от 18.03.2020"
   and _yw("от 5 марта 2020-го года", "5 марта 2020", "ru") == "от 5 марта 2020-го года",
   "M5: yılında / 'ci yıl / . Yıl at a line end; RU -го года after a numeric date only")

ok(_yw("Tarih: 1 Nisan 2019 yıl\n\nMüşteri", "1 Nisan 2019", "tr") == "Tarih: 1 Nisan 2019\n\nMüşteri"
   and _yw("Olay 22 Haziran 2017ci yıl tarihinde", "22 Haziran 2017", "tr") == "Olay 22 Haziran 2017 tarihinde"
   and _yw("12 Mart 2019 yıllık plan", "12 Mart 2019", "tr") == "12 Mart 2019 yıllık plan",
   "M5: a bare `yıl` and a glued `ci yıl` after a full date; `yıllık` left alone")
_src = "Bütün sənədlər sifariş №2919933 üzrə qeydiyyata alınmışdır."
_txt = "Tüm belgeler 2919933 numaralı sipariş uyarınca kaydedilmiştir."
_out, _ = M.apply_text_edits(_txt, [], M.tr_uyarinca_edits(_src, _txt, []))
ok(_out == "Tüm belgeler 2919933 numaralı sipariş kapsamında kaydedilmiştir."
   and not M.tr_uyarinca_edits("Müayinələr protokol əsasında davam etdirilir.", "protokol uyarınca devam", []),
   "M6: `uyarınca` for `üzrə` becomes `kapsamında`; kept where the source says `əsasında`", _out)

# M4: the whole date when the text repeats it
t = "Tarix: 22.05.2016\n[2016-05-22 14:02:11] LOG"
ok(M.source_date(t, 7, 17) == (22, 5, 2016) and M.source_date("Tarix: 22.05.2016 imza", 7, 17) == 2016
   and M.parse_full_date("22 may 2016-cı il") == (22, 5, 2016) and M.parse_full_date("30.02.2016") is None,
   "M4: source_date gives the whole date only when the text repeats it")
from translate.run import mint_values as _mv  # noqa: E402
for lang in ("tr", "en"):
    v = _mv(["DATE"], ["22.05.2016"], lang, f"m4|{lang}", years=[(22, 5, 2016)])[0]
    ok(("22" in v and "2016" in v) and any(m in v.lower() for m in ("05", "5", "may", "mayıs")),
       f"M4: {lang} mints the repeated date", v)

# M6: no genitive before `tarafından`
tags = {0: "GEN", 1: "GEN"}
M.drop_gen_before_tarafindan("⟦0⟧ tarafından ve ⟦1⟧ adına", tags)
ok(tags == {1: "GEN"}, "M6: a genitive tag before tarafından is dropped", tags)
from translate.prompt import build_messages  # noqa: E402
_tr_prompt = " ".join(m["content"] for m in build_messages("x", "tr"))
ok("never uyarınca" in _tr_prompt and "tarafından takes no tag" in _tr_prompt, "M6: the two Turkish prompt lines")

# M2: no Cyrillic name in Turkish
_cy = _re.compile(r"[Ѐ-ӿ]")
_tr_names = [v for i in range(2000) for v in _mv(["GIVENNAME", "SURNAME"], [f"a{i}", f"b{i}"], "tr", f"m2{i}|tr").values()]
ok(not any(_cy.search(v) for v in _tr_names), "M2: no Cyrillic in minted Turkish names")

# M1: Russian names
from piigen.locales import ru as _ru  # noqa: E402
ok([_ru.transliterate(n) for n in ("Hacıbəyov", "Hacıbəyova", "Saniyə", "Ziyaratov", "Liliya", "Hacırza", "Maşı")]
   == ["Гаджибеков", "Гаджибекова", "Сания", "Зияратов", "Лилия", "Гаджирза", "Маши"], "M1: -беков, ия, жи/ши")
from translate.run_ru import _FOREIGN, _FOREIGN_ORIGIN, _mint_factory, mint as _ru_mint  # noqa: E402
_ru_names = []
for i in range(2000):
    vf = _mint_factory(f"m1-{i}")
    _ru_names += [_ru_mint(vf, lab, female=bool(i % 2)) for lab in ("GIVENNAME", "SURNAME")]
_cyr_forms = set(_FOREIGN.cyrillic.values())
ok(not any(_re.search(r"[A-Za-z]", v) for v in _ru_names), "M1: no Latin letter in a Russian name",
   [v for v in _ru_names if _re.search(r"[A-Za-z]", v)][:3])
ok(not any(_re.search(r"бао?в", v) for v in _ru_names), "M1: no -баов (-беков, -аев)")
# (Azerbaijani names keep their own `сг`/`кг`: `Исгандар`, `Аббасгулу`; a
# foreign romanisation's `sh`/`kh` never comes out that way)
_rom = [n for n, o in _FOREIGN_ORIGIN.items() if o in ("ka", "fa", "ar") and not _FOREIGN.cyrillic.get(n)]
_bad_rom = [(n, _ru.transliterate_foreign(n)) for n in _rom
            if _re.search(r"(sh|kh|ch|zh)", n.lower()) and _re.search(r"(сг|кг|чг|зг)", _ru.transliterate_foreign(n).lower())]
ok(_rom and not _bad_rom, "M1: foreign romanisations' sh/kh/ch/zh -> ш/х/ч/ж", _bad_rom[:3])
ok([_ru.transliterate_foreign(n) for n in ("Malkhaz", "Imnaishvili", "Kintibidze", "Jaba", "Zhvania")]
   == ["Малхаз", "Имнаишвили", "Кинтибидзе", "Джаба", "Жвания"]
   and _ru.transliterate_foreign("Oğuzhan", digraphs=False) == "Огузхан", "M1: foreign names read as romanisations")
ok(any(v in _cyr_forms for v in _ru_names), "M1: Russian-origin foreign names take their own Cyrillic form")
_en = [n for n, o in _FOREIGN_ORIGIN.items() if o in ("en", "fr", "de") and not _FOREIGN.cyrillic.get(n)]
ok(not any(_ru.transliterate(n) in _ru_names for n in _en[:400]), "M1: no English/French/German name without a Russian form")

# D-64c: the split is stamped from --split-name, and check_splits catches every mistake
import subprocess as _sp, tempfile as _tf  # noqa: E401,E402
from pathlib import Path as _P  # noqa: E402
_root = _P(__file__).resolve().parents[2]
with _tf.TemporaryDirectory() as d:
    d = _P(d)
    (d / "src").mkdir()
    for s, ids in (("train", ["a", "b"]), ("val", ["c"]), ("test", ["d"])):
        (d / "src" / f"{s}.docs.jsonl").write_text("".join(json.dumps({"id": i}) + "\n" for i in ids), encoding="utf-8")
    def _out(rows_by_split):
        o = d / "out"
        for lang in ("tr",):
            (o / lang).mkdir(parents=True, exist_ok=True)
            for s, rows in rows_by_split.items():
                (o / lang / f"{s}.docs.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        return _sp.run([sys.executable, str(_root / "scripts/translate/check_splits.py"), "--source-dir", str(d / "src"),
                        "--out-dir", str(o), "--langs", "tr"], capture_output=True, text=True).returncode
    good = {"train": [{"source_id": "a", "split": "train"}, {"source_id": "b", "split": "train"}],
            "val": [{"source_id": "c", "split": "val"}], "test": [{"source_id": "d", "split": "test"}]}
    ok(_out(good) == 0, "D-64c: check_splits passes a clean translation")
    ok(_out({**good, "val": [{"source_id": "c", "split": ""}]}) == 1, "D-64c: an empty split fails")
    ok(_out({**good, "test": [{"source_id": "c", "split": "test"}]}) == 1, "D-64c: a source_id in two splits fails")
    ok(_out({**good, "val": [{"source_id": "c", "split": "sample300b"}]}) == 1, "D-64c: a file-stem split fails")
_fr = (_root / "scripts/translate/full_run.py").read_text(encoding="utf-8")
ok('"--split-name", split' in _fr and 'f"{split}.docs.jsonl"' in _fr and "check_splits.py" in _fr,
   "D-64c: full_run translates each split into <lang>/<split>.docs.jsonl and checks the splits")

print("=" * 60)
print(f"PASSED {PASS}   FAILED {FAIL}")
print("=" * 60)
sys.exit(1 if FAIL else 0)
