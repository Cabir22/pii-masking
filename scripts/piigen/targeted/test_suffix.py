"""P2-4c checks: the suffix renderer, the resolver's declared forms, the
apostrophe exemption, the inflected documents and C1 `{v:CASE}` frames.

No network, no model.

    python scripts/piigen/targeted/test_suffix.py
"""

from __future__ import annotations

import collections
import random
import re
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from piigen.locales import az as AZ                                   # noqa: E402
from piigen.resolver import match_key, resolve_claims                 # noqa: E402
from piigen.targeted import builder as B                              # noqa: E402
from piigen.targeted import frames_az_stub as STUB                    # noqa: E402
from piigen.targeted import quotas as Q                               # noqa: E402
from piigen.targeted import suffix as S                               # noqa: E402
from piigen.targeted.suffix_frames import KIND, SUFFIX_FRAMES         # noqa: E402
from piigen.validate import turkish_contamination, validate_example   # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond: bool, msg: str, detail=None) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(msg + (f"  [{detail!r}]"[:300] if detail is not None else ""))


# --------------------------------------------------------------------------- #
def test_renderer() -> None:
    gold = {
        # (value, label, case): form -- harmony, buffers, stacking
        ("Əsgər", "GIVENNAME", "gen"): "Əsgərin", ("Leyla", "GIVENNAME", "gen"): "Leylanın",
        ("Oğuz", "GIVENNAME", "gen"): "Oğuzun", ("Gülnur", "GIVENNAME", "acc"): "Gülnuru",
        ("Leyla", "GIVENNAME", "dat"): "Leylaya", ("Əsgər", "GIVENNAME", "dat"): "Əsgərə",
        ("Leyla", "GIVENNAME", "acc"): "Leylanı", ("Bakı", "CITY", "loc"): "Bakıda",
        ("Gəncə", "CITY", "abl"): "Gəncədən", ("Bakı", "CITY", "ins"): "Bakıyla",
        ("Əsgər", "GIVENNAME", "ins"): "Əsgərlə", ("Bakı", "CITY", "rel"): "Bakıdakı",
        ("Gəncə", "CITY", "rel"): "Gəncədəki", ("Məmmədov", "SURNAME", "pl"): "Məmmədovlar",
        ("Məmmədov", "SURNAME", "pl_abl"): "Məmmədovlardan", ("Əlizadə", "SURNAME", "pl_gen"): "Əlizadələrin",
        ("Oğuz", "GIVENNAME", "cop"): "Oğuzdur", ("Bakı", "CITY", "loc_cop"): "Bakıdadır",
        ("Əsgər", "GIVENNAME", "gil_dat"): "Əsgərgilə", ("Leyla", "GIVENNAME", "gil_abl"): "Leylagildən",
        ("Leyla", "GIVENNAME", "pred1"): "Leylayam", ("Əsgər", "GIVENNAME", "pred1"): "Əsgərəm",
        ("Məmmədov", "SURNAME", "pred_formal"): "Məmmədovsunuz", ("Bakı", "CITY", "loc_pred1"): "Bakıdayam",
        ("Bakı", "CITY", "loc_pred1pl"): "Bakıdayıq", ("Bakı", "CITY", "loc_q"): "Bakıdamı",
        ("Leyla", "GIVENNAME", "past"): "Leylaydı", ("Bakı", "CITY", "loc_past1"): "Bakıdaydım",
        ("Məmmədov", "SURNAME", "gen_ki"): "Məmmədovunku", ("Leyla", "GIVENNAME", "gen_ki"): "Leylanınkı",
        ("Bakı", "CITY", "term_dek"): "Bakıyadək", ("Gəncə", "CITY", "term_can"): "Gəncəyəcən",
        ("Leyla", "GIVENNAME", "poss1"): "Leylam", ("Oğuz", "CITY", "poss1pl"): "Oğuzumuz",
        ("Leyla", "GIVENNAME", "cond"): "Leylaysa", ("Bakı", "CITY", "loc_cond"): "Bakıdaysa",
        # streets: the pronominal n after the possessive -(s)I
        ("Nizami küçəsi", "STREET", "dat"): "Nizami küçəsinə", ("Nizami küçəsi", "STREET", "loc"): "Nizami küçəsində",
        ("Nizami küçəsi", "STREET", "abl"): "Nizami küçəsindən", ("Nizami küçəsi", "STREET", "rel"): "Nizami küçəsindəki",
        ("Nizami küçəsi", "STREET", "gen"): "Nizami küçəsinin", ("Azadlıq prospekti", "STREET", "ins"): "Azadlıq prospektiylə",
        ("Nizami küçəsi", "STREET", "loc_cop"): "Nizami küçəsindədir", ("Nizami küçəsi", "STREET", "term_dek"): "Nizami küçəsinədək",
        # k/q: borrowed names keep it, native-word names soften before a vowel
        ("Tofiq", "GIVENNAME", "gen"): "Tofiqin", ("Lerik", "CITY", "dat"): "Lerikə",
        ("Çiçək", "GIVENNAME", "gen"): "Çiçəyin", ("Çiçək", "GIVENNAME", "loc"): "Çiçəkdə",
        # an all-capitals value keeps its suffix in capitals
        ("BAKI", "CITY", "loc"): "BAKIDA",
    }
    for (v, lab, case), want in gold.items():
        got = S.inflect(v, case, lab)
        check(got == want, f"inflect({v}, {case}) = {want}", got)
    for bad in (("Nizami küç.", "loc", "STREET"), ("Маммадов", "gen", "SURNAME"),
                ("Bakı", "gil", "CITY"), ("Nizami küçəsi", "pred1", "STREET")):
        try:
            S.inflect(*bad)
            check(False, f"refuses {bad}")
        except S.NotInflectable:
            check(True, f"refuses {bad}")
    check(S.surface("Bakı", "Bakıda", "apostrophe") == "Bakı'da", "apostrophe surface")
    check(S.surface("Əsgər", "Əsgərdən", "folded") == "Esgerden", "folded surface")
    check(S.surface("Çiçək", "Çiçəyin", "apostrophe") == "Çiçək'in", "apostrophe keeps a softening name as written (P4-2 round 2)")
    check(S.split("Çiçəyin", "Çiçək") == 5 and S.split("Bakıda", "Bakı") == 4, "split finds the stem")
    check(set(S.C1_CASES) <= set(S.FORMS), "every C1 code is rendered")
    check(set(S.CASE_GROUP) == set(S.FORMS), "every form belongs to a group")
    for lab, cases in S.APPLIES.items():
        missing = [c for c in cases if not SUFFIX_FRAMES[KIND[lab]].get(c)]
        check(not missing, f"{lab}: every case it takes has sentences", missing)
    # every sentence has exactly one {v} and no digits
    for kind, cases in SUFFIX_FRAMES.items():
        for case, ts in cases.items():
            for t in ts:
                check(t.count("{v}") == 1 and not re.search(r"\d", t), f"{kind}/{case}: one slot, no digits", t)
    rows = S.table({"GIVENNAME": ["Leyla"], "CITY": ["Bakı"], "STREET": ["Nizami küçəsi"]})
    check(len(rows) == len(S.APPLIES["GIVENNAME"]) + len(S.APPLIES["CITY"]) + len(S.APPLIES["STREET"]),
          "table() lists every form for the native-speaker check")


def test_resolver_declared() -> None:
    t = "Bayramda Əsgərgilə qonaq getdik."
    s = t.index("Əsgərgilə")
    got, _ = resolve_claims(t, [{"label": "GIVENNAME", "text": "Əsgər"}])
    check(not got, "an undeclared -gil form is not guessed", got)
    got, _ = resolve_claims(t, [{"label": "GIVENNAME", "text": "Əsgər"}], declared=[(s, s + 9)])
    check([(g["start"], g["end"]) for g in got] == [(s, s + 9)], "a declared form resolves from its stem", got)
    # the guards the resolver documents: Əliyev never admits Əli, Adəm is not Ad + əm
    t = "Əliyev və Adəm gəldi."
    got, _ = resolve_claims(t, [{"label": "GIVENNAME", "text": "Əli"}, {"label": "GIVENNAME", "text": "Ad"}])
    check(not got, "Əliyev does not admit Əli; Adəm is not Ad + əm", got)
    got, _ = resolve_claims(t, [{"label": "GIVENNAME", "text": "Ad"}], declared=[(0, 6)])
    check(not got, "a declaration elsewhere changes nothing for Adəm", got)
    # the open fused forms still work, and the softened stem is offered
    got, _ = resolve_claims("Biz Bakıda yaşayırıq.", [{"label": "CITY", "text": "Bakı"}])
    check([g["text"] for g in got] == ["Bakıda"], "Bakıda still resolves without a declaration", got)
    got, _ = resolve_claims("Çiçəyin sənədi gəldi.", [{"label": "GIVENNAME", "text": "Çiçək"}])
    check([g["text"] for g in got] == ["Çiçəyin"], "Çiçək resolves as Çiçəyin (softened stem)", got)
    got, _ = resolve_claims("Bayram Bakı'da keçdi.", [{"label": "CITY", "text": "Bakı"}],
                            declared=[(7, 14)])
    check([g["text"] for g in got] == ["Bakı'da"], "a declared apostrophe form resolves", got)


def test_validate_apostrophe() -> None:
    t = "Görüş Bakı'da keçiriləcək, sənədlər hazırdır və hər şey qaydasındadır."
    rec = {"text": t, "lang": "az", "entities": [{"start": 6, "end": 13, "label": "CITY", "text": "Bakı'da"}]}
    check(any("apostrophe" in p for p in validate_example(rec)), "an undeclared apostrophe form is reported")
    rec["_suffixes"] = [{"start": 6, "end": 13, "stem_end": 10, "case": "loc", "surface": "apostrophe"}]
    check(not any("apostrophe" in p for p in validate_example(rec)), "a declared apostrophe form is exempt",
          validate_example(rec))
    check(turkish_contamination("Qax'da yağış var.", exempt=[(20, 30)]) != [], "exemption is span-exact")
    rec["_suffixes"] = [{"start": 0, "end": 5, "stem_end": 3, "case": "loc", "surface": "apostrophe"}]
    check(any(p.startswith("suffix:") for p in validate_example(rec)), "a declaration off an entity is a problem")
    rec["_suffixes"] = [{"start": 6, "end": 13, "case": "loc"}]
    check(any(p.startswith("suffix:") for p in validate_example(rec)), "a malformed declaration is a problem")


def test_build() -> None:
    builder = B.TargetedBuilder(seed=21, n_docs=1500)
    recs = builder.build()
    inflected = [r for r in recs if r["_spec"]["family"] == "inflected"]
    check(len(inflected) > 100, f"inflected documents are built ({len(inflected)})")
    sfx = [(r, x) for r in recs for x in r["_suffixes"]]
    spans_ok = all((x["start"], x["end"]) in {(e["start"], e["end"]) for e in r["entities"]} for r, x in sfx)
    check(spans_ok, "every declared suffix covers an entity")
    words_ok = all(r["text"][x["start"]:x["end"]] for r, x in sfx)
    check(words_ok and all(validate_example(r) == [] for r in inflected), "inflected documents validate")
    fem = [r["text"][x["start"]:x["end"]] for r, x in sfx
           if x["case"].startswith("pl") and re.search(r"(ova|eva)lar", r["text"][x["start"]:x["end"]], re.I)]
    check(not fem, "family plurals use the base surname", fem[:3])
    cases = collections.Counter(x["case"] for _r, x in sfx)
    check(all(cases[c] for c in S.C1_CASES), "every C1 case occurs", cases)
    check(sum(1 for _r, x in sfx if x["surface"] != "plain") > 0, "apostrophe and folded forms occur")
    noisy = sum(1 for r, x in sfx if x["surface"] != "plain"
                and any(c[1] == r["text"][x["start"]:x["end"]] for c in r["_spec"].get("case_noise", [])))
    check(noisy == 0, "an apostrophe or folded form is never case-noised too", noisy)


def _c1_frames_module():
    """The stub's frames plus seven `{v:CASE}` frames: one far frame per label
    (`Hesabata görə {a} {v:loc} ...`), which the 3% cap used to exhaust."""
    mod = types.ModuleType("frames_with_cases")
    for name in ("ANCHORS", "GENERIC_FRAMES", "NEUTRAL", "NEUTRAL_BY_REGISTER", "FRAME_VERSION"):
        if hasattr(STUB, name):
            setattr(mod, name, getattr(STUB, name))
    frames = {k: list(v) for k, v in STUB.FRAMES.items()}
    frames["CITY"] = (frames.get("CITY", [])
                      + [f"Hesabata görə {{a}} {{v:{c}}} qeyd olunub." for c in ("loc", "abl")]
                      + ["Sifariş {v:dat} göndərilib.", "{v:gen} mərkəzində ofis açılıb.",
                         "Kuryer {v:abl} yola düşüb."])
    frames["GIVENNAME"] = frames.get("GIVENNAME", []) + ["Sənədləri {v:dat} təhvil verdik.", "{v:gen} ərizəsi qəbul olunub."]
    mod.FRAMES = frames
    return mod


def test_c1_case_frames() -> None:
    """When the frames carry `{v:CASE}` slots, they are filled through
    the renderer and declared, like the builder's own sentences."""
    mod = _c1_frames_module()
    lib = B.FrameLibrary(mod)
    check(lib.case_frames == 7 and lib.skipped_case_frames == 0, "case frames are kept, none skipped", lib.case_frames)
    # prose spreads over 27 labels: weight the two with case frames so the
    # check does not depend on a lucky seed (2-3 uses in 600 documents)
    q = Q.load()
    q["prose"]["label_weights"].update({"CITY": 12.0, "GIVENNAME": 12.0})
    # ... and a fixed prose share, so a change of the family shares (D-51h
    # took prose 0.035 -> 0.03) does not starve the check
    q["families"]["decoy_pair"] -= 0.07 - q["families"]["prose"]
    q["families"]["prose"] = 0.07
    recs = B.TargetedBuilder(seed=4, n_docs=600, quotas=q, frames_module=mod).build()
    used = [(r, x) for r in recs if r["_spec"]["family"] == "prose" for x in r["_suffixes"]]
    check(len(used) > 0, f"prose documents fill C1 case frames ({len(used)})")
    check(all(r["text"][x["start"]:x["stem_end"]] and x["case"] in ("loc", "abl", "dat", "gen") for r, x in used),
          "the C1 case is what was rendered")
    bad = types.ModuleType("bad_frames")
    for name in ("ANCHORS", "GENERIC_FRAMES", "NEUTRAL", "FRAME_VERSION"):
        setattr(bad, name, getattr(STUB, name))
    bad.FRAMES = {"CITY": ["Gəldik {v:locative}."]}
    try:
        B.FrameLibrary(bad)
        check(False, "an unknown case code fails loudly")
    except ValueError:
        check(True, "an unknown case code fails loudly")


def test_surname_harmony() -> None:
    harm = {"a": "ı", "ı": "ı", "o": "u", "u": "u", "e": "i", "ə": "i", "i": "i", "ö": "ü", "ü": "ü"}
    rng = random.Random(1)
    wrong = []
    for stem in random.Random(2).sample(AZ.SURNAME_STEMS if hasattr(AZ, "SURNAME_STEMS") else
                                        AZ.LOCALE.surname_stems, 3000):
        s = AZ.surname(stem, False, rng)
        if re.search(r"l[ıiuü]$", s) and not s.endswith(("ov", "yev")):
            last = next((c for c in reversed(s[:-2].lower()) if c in harm), None)
            if last and harm[last] != s[-1]:
                wrong.append(s)
    check(not wrong, "-lı/-li/-lu/-lü surnames follow vowel harmony", wrong[:5])


def test_english_spelling_harmony() -> None:
    """An English-spelled name takes the suffix of the letters written (P4-2
    round 2; it followed the Azerbaijani spelling before: `Sarigulü`)."""
    b = B.TargetedBuilder(seed=1, n_docs=10)
    for english, canonical, case, label, want in (
            ("Babullazada", "Babullazadə", "pl_dat", "SURNAME", "Babullazadalara"),
            ("Aronzada", "Aronzadə", "pl", "SURNAME", "Aronzadalar"),
            ("Reala", "Realə", "abl", "GIVENNAME", "Realadan"),
            ("Sarigul", "Sarıgül", "acc", "GIVENNAME", "Sarigulu"),
            ("Huseynova", "Hüseynova", "dat", "SURNAME", "Huseynovaya"),
            ("Gulnar", "Gülnar", "gen", "GIVENNAME", "Gulnarın"),
            ("Ismayil", "İsmayıl", "abl", "GIVENNAME", "Ismayildən")):
        b.values.name_variants[english] = (canonical, "english")
        got = b._inflect(english, case, label)
        check(got == want, f"{english} + {case} follows the letters written", got)
    b.values.name_variants["Chichak"] = ("Çiçək", "english")
    try:
        b._inflect("Chichak", "dat", "GIVENNAME")
        check(False, "a stem that softens (Çiçəyə) is refused in English spelling")
    except S.NotInflectable:
        check(True, "a stem that softens (Çiçəyə) is refused in English spelling")
    check(b._inflect("Bakı", "loc", "CITY") == S.inflect("Bakı", "loc", "CITY"), "a plain value is unchanged")
    builder = B.TargetedBuilder(seed=8, n_docs=1500)
    recs = builder.build()
    seen = bad = 0
    for r in recs:
        for x in r.get("_suffixes", ()):
            stem = r["text"][x["start"]:x["stem_end"]]
            canonical, kind = builder.values.name_variants.get(stem, (None, None))
            if kind != "english" or x["surface"] != "plain":
                continue
            label = next(e["label"] for e in r["entities"] if (e["start"], e["end"]) == (x["start"], x["end"]))
            seen += 1
            bad += r["text"][x["stem_end"]:x["end"]] != S.inflect(stem, x["case"], label)[len(stem):]
    check(seen > 0 and not bad, f"inflected English spellings take the suffix of the letters written ({seen}, {bad} wrong)")


def test_p4_2_round1() -> None:
    """The native-speaker check, round 1 (P4-2)."""
    # 1. the 1st-person plural ending is -(y)IQ: q after a back vowel, k after
    #    a front one (Gəncədəyiq was wrong)
    gold = {"Bakı": "Bakıdayıq", "Şuşa": "Şuşadayıq", "Gəncə": "Gəncədəyik",
            "Şəmkir": "Şəmkirdəyik", "Lerik": "Lerikdəyik", "Ələt": "Ələtdəyik",
            "Mingəçevir": "Mingəçevirdəyik", "Göygöl": "Göygöldəyik", "Oğuz": "Oğuzdayıq"}
    for city, form in gold.items():
        check(S.inflect(city, "loc_pred1pl", "CITY") == form, f"{city} -> {form}",
              S.inflect(city, "loc_pred1pl", "CITY"))
    check(S.inflect("GƏNCƏ", "loc_pred1pl", "CITY") == "GƏNCƏDƏYİK", "capitals keep the k")
    wrong = [S.inflect(c, "loc_pred1pl", "CITY") for c in AZ.CITIES + AZ.SETTLEMENTS
             if (S.inflect(c, "loc_pred1pl", "CITY")[-1] == "q") != (S.inflect(c, "loc_pred1pl", "CITY")[-2] in "ıu")]
    check(not wrong, "every city in the pool: q after ı/u, k after i/ü", wrong[:5])
    # 2. the family -gil is built on the base surname, as the plural is
    builder = B.TargetedBuilder(seed=3, n_docs=10)
    forms = [builder._mint_inflectable("SURNAME", case)
             for case in ("gil", "gil_gen", "gil_dat", "gil_loc", "gil_abl") for _ in range(40)]
    feminine = [w for v, w in forms if re.search(r"(?:ov|yev|ev|in)a$", v)]
    check(not feminine, "surname + -gil uses the base surname (Məmmədovgil, not Məmmədovagil)",
          feminine[:5])
    # 3. "baxılması üçün", the officialese form, in every frame
    texts = [t for frames in SUFFIX_FRAMES.values() for ts in frames.values() for t in ts]
    texts += [t for v in vars(STUB).values() if isinstance(v, (list, tuple))
              for t in v if isinstance(t, str)]
    check(not [t for t in texts if "baxılmaq üçün" in t], "no frame says 'baxılmaq üçün'")
    # ...and in a 5,000-document build (measure)
    docs = B.TargetedBuilder(seed=11, n_docs=5000).build()
    city = {match_key(c): c for c in AZ.CITIES + AZ.SETTLEMENTS}   # the CITY pool (P2-14)
    pred, fem = [], []
    for r in docs:
        for x in r.get("_suffixes") or []:
            word = r["text"][x["start"]:x["end"]]
            if x["case"] == "loc_pred1pl" and x["surface"] == "plain":
                pred.append((word, city.get(match_key(r["text"][x["start"]:x["stem_end"]]))))
            if x["case"].startswith("gil") and any(
                    e["label"] == "SURNAME" and e["start"] == x["start"] for e in r["entities"]):
                stem = r["text"][x["start"]:x["stem_end"]]
                if re.search(r"(?:ov|yev|ev|in)a$", stem, re.IGNORECASE):
                    fem.append(word)
    # q after a back vowel, judged on the pool city: a folded or case-glitched
    # document writes `GoycAydayiQ` for Göyçaydayıq, its `ı` now an `i`
    back = lambda c: [ch for ch in c.lower() if ch in "aıoueəiöü"][-1] in "aıou"   # noqa: E731
    bad = [w for w, c in pred if c is None or w[-1].lower() not in "qk"
           or (w[-1].lower() == "q") != back(c)]
    check(pred and not bad, f"5,000-document build: {len(pred)} -dAyIQ forms, none with the wrong q/k", bad)
    check(not fem, "5,000-document build: no feminine surname takes -gil", fem[:5])


def test_p4_2_round2() -> None:
    """The round-2 findings (renderer, frames, values, decoys)."""
    import random as _random
    from piigen import negatives as N
    from piigen.values import ValueFactory, ValuePool
    # 1. with an apostrophe the name stays as written: Çiçək'in, not Çiçəy'in
    for case, tail in (("gen", "in"), ("dat", "ə"), ("acc", "i")):
        word = S.inflect("Çiçək", case, "GIVENNAME")
        got = S.surface("Çiçək", word, "apostrophe")
        check(got == "Çiçək'" + tail, f"apostrophe keeps Çiçək: {case}", got)
    check(S.surface("Bakı", S.inflect("Bakı", "loc", "CITY"), "apostrophe") == "Bakı'da", "Bakı'da is unchanged")
    check(S.surface("Çiçək", "Çiçəyin", "folded") == "Ciceyin", "a folded form is the softened word, folded")
    # 2. k/q softening by ending: P4's gold forms and the names that stay
    soft = {"Çiçək": "Çiçəyin", "Alçiçək": "Alçiçəyin", "Mələk": "Mələyin", "Tapdıq": "Tapdığın",
            "Sevdik": "Sevdiyin", "Bəyəndik": "Bəyəndiyin", "Qıvraq": "Qıvrağın", "Ayçiçək": "Ayçiçəyin",
            "Sönməzçiçək": "Sönməzçiçəyin", "İşıq": "İşığın", "Bulaq": "Bulağın", "Ocaq": "Ocağın",
            "Yaraq": "Yarağın", "Gülçiçək": "Gülçiçəyin", "Göyçək": "Göyçəyin", "Bayraq": "Bayrağın"}
    for name, form in soft.items():
        got = S.inflect(name, "gen", "GIVENNAME")
        check(got == form, f"{name} softens", got)
    for name in ("Tofiq", "Müşfiq", "Natiq", "Sadıq", "Xalıq", "Məlik", "Müdrik", "Mübarək", "Layiq", "Qutluq",
                 "Saltıq", "Ayıq", "Sayıq", "Aybək", "Özbək", "Beyrək", "Rövnək", "Sədərək"):
        got = S.inflect(name, "gen", "GIVENNAME")
        check(got.startswith(name), f"{name} keeps its k/q", got)
    check(S.inflect("Qıvraq", "dat", "CITY") == "Qıvrağa", "the city Qıvraq softens")
    check(S.inflect("Lerik", "dat", "CITY") == "Lerikə" and S.inflect("Babək", "dat", "CITY") == "Babəkə",
          "Lerik and Babək do not")
    check(S.inflect("ÇİÇƏK", "gen", "GIVENNAME") == "ÇİÇƏYİN", "a capitalised name softens in capitals")
    check(S.inflect("Bakı", "loc", "CITY") == "Bakıda" and S.inflect("Çiçək", "q", "GIVENNAME") == "Çiçəkmi",
          "no change before a consonant or on other words")
    kq = sorted({v for n in (AZ.FIRST_M, AZ.FIRST_F, AZ.CITIES) for v in n if v and v[-1].lower() in "kq"})
    softened = [v for v in kq if not S.inflect(v, "gen", "CITY" if v in AZ.CITIES else "GIVENNAME").startswith(v)]
    check(len(kq) > 300 and 100 <= len(softened) <= 130,
          f"the pool: {len(softened)} of {len(kq)} k/q-final names soften (the old list: 7)")
    # 3. the sentences: a question without a person ending is the 3rd person; a train is not late "from" a city
    texts = [x for kinds in SUFFIX_FRAMES.values() for case in ("loc_q", "q") for x in kinds.get(case, [])]
    check(not [x for x in texts if x.startswith(("Sən ", "Siz "))], "no `Sən/Siz ... -mı?` without a person ending")
    check(SUFFIX_FRAMES["place"]["abl"][0] == "{v} gələn qatar gecikir.", "the train comes from the city")
    check(not [x for x in SUFFIX_FRAMES["place"]["abl"] if x.startswith("Qatar {v}")], "no `Qatar Gəncədən gecikir`")
    # 4. English spellings take the suffix of the letters written (test above); no softening is invented
    b = B.TargetedBuilder(seed=1, n_docs=10)
    b.values.name_variants["Cicek"] = ("Çiçək", "english")
    try:
        b._inflect("Cicek", "gen", "GIVENNAME")
        check(False, "an English spelling of a softening name is refused")
    except S.NotInflectable:
        check(True, "an English spelling of a softening name is refused")
    # 5. a Cyrillic name that must take a Latin suffix is written in Latin letters, never `Юнусовdur`
    factory = ValueFactory(_random.Random(2), ValuePool(state_path=None))
    factory.name_variants["Юнусов"] = ("Yunusov", "cyrillic")
    check(factory.name_spellings("Yunusov").get("english") is None, "the fixture: Yunusov has no separate English spelling")
    check(factory.latin_spelling("Юнусов") == "Yunusov", "the Azerbaijani spelling when the English one is the same")
    check("Yunusov" not in factory.name_variants, "...and it is not recorded as a variant of itself")
    # 6. AGE decoys carry no verb of their own
    check(not [a for a in N._AGE if "olunub" in a or "edilib" in a], "no AGE decoy phrase has its own verb", N._AGE)
    # the C1 fixture builds at every seed: a frame at the 3% cap is not a candidate
    errors = []
    for seed in range(1, 13):
        q = Q.load()
        q["prose"]["label_weights"].update({"CITY": 12.0, "GIVENNAME": 12.0})
        try:
            B.TargetedBuilder(seed=seed, n_docs=600, quotas=q, frames_module=_c1_frames_module()).build()
        except B.BuildError as exc:
            errors.append((seed, str(exc)[:50]))
    check(not errors, "the C1 fixture builds at seeds 1-12", errors)
    # in a 5,000-document build (measure: seed 1)
    docs = B.TargetedBuilder(seed=1, n_docs=5000).build()
    bare = [d["kind"] for r in docs if r["_spec"]["family"] == "structured"
            for d in r.get("_decoys", []) if d["kind"].startswith("policy_")]
    check(not bare, "no policy decoy stands bare in a structured document", bare[:5])
    double = [r["id"] for r in docs if re.search("kimi qeyd olunub [a-zəıöüçşğ]", r["text"])]
    check(not double, "no `kimi qeyd olunub` followed by a second verb", double[:3])
    cyr, lat = re.compile("[Ѐ-ӿ]"), re.compile("[A-Za-z]")
    mixed = [w for r in docs for w in re.findall(r"\w+", r["text"]) if cyr.search(w) and lat.search(w)]
    check(not mixed, f"no word mixes Cyrillic and Latin letters ({len(mixed)})", mixed[:5])
    apo = wrong_apo = 0
    for r in docs:
        for x in r.get("_suffixes") or []:
            if x["surface"] == "apostrophe":
                apo += 1
                word = r["text"][x["start"]:x["end"]]
                stem = r["text"][x["start"]:x["stem_end"]]
                wrong_apo += not word.startswith(stem + "'") or len(word) <= len(stem) + 1
    check(apo > 0 and not wrong_apo, f"apostrophe forms are the name as written, an apostrophe, the ending ({apo})", wrong_apo)
    # 7. the value pools: no brackets in a given name, no invisible characters, no pasted type words
    names = AZ.FIRST_M + AZ.FIRST_F
    check(not [n for n in names if "(" in n or ")" in n], "no bracket in a given name")
    ctrl = chr(0x200E)
    check(not [s for s in AZ.STREET_STEMS
               if ctrl in s or "yplu" in s or s.endswith((" str.", " külç.")) or re.match("^[0-9]+o-", s)],
          "no hidden character, typo or pasted type word in a street stem")


def test_noisy_suffixes() -> None:
    """People misspell suffixes; the name is still the name (2026-10-05)."""
    from piigen.resolver import noisy_forms, planned_forms
    gold = {("Bakı", "loc", "CITY"): {"harmony": "Bakıdə", "double": "Bakıdda"},
            ("Gəncə", "gen", "CITY"): {"harmony": "Gəncənın", "buffer": "Gəncəin", "double": "Gəncənnin"},
            ("Leyla", "ins", "GIVENNAME"): {"harmony": "Leylaylə", "double": "Leylayyla", "colloquial": "Leylaynan"},
            ("Əsgər", "ins", "GIVENNAME"): {"harmony": "Əsgərla", "double": "Əsgərllə", "colloquial": "Əsgərnən"},
            ("BAKI", "dat", "CITY"): {"harmony": "BAKIYƏ", "buffer": "BAKIA", "double": "BAKIYYA"}}
    for (v, case, lab), want in gold.items():
        got = S.noisy(v, case, lab)
        check(got == want, f"noisy forms of {v} + {case}", got)
    check(S.noisy("Nizami küçəsi", "loc", "STREET").get("buffer") is None, "a street keeps its pronominal n")
    check(all(w.startswith(v) for (v, c, lab) in gold for w in S.noisy(v, c, lab).values()),
          "only the suffix changes, never the name")
    # a misspelling that spells another real name is not one: Ad + -am with the wrong vowel is Adəm
    check(not [w for w in noisy_forms("Ad", "pred1", "GIVENNAME").values() if w == "Adəm"], "Adəm is not a misspelt Ad")
    for lab, val, word in (("GIVENNAME", "Leyla", "Leylaynan"), ("CITY", "Bakı", "Bakıdda"),
                           ("CITY", "Bakı", "Bakıdə"), ("CITY", "Gəncə", "Gəncəin"), ("SURNAME", "Məmmədov", "Məmmədovlərdən")):
        text = f"Sənədlər dünən {word} göndərilib."
        forms = [(text[f.start:f.end], f.labelable) for f in planned_forms(text, lab, val)]
        check((word, True) in forms, f"a planned {val} written {word} is labelled whole", forms)
    for lab, val, text in (("GIVENNAME", "Ad", "Adəm gəldi."), ("GIVENNAME", "Əli", "Əliyev gəldi."),
                           ("CITY", "Bakı", "Bakılı oğlan gəldi.")):
        check(not [f for f in planned_forms(text, lab, val) if f.labelable],
              f"{text!r} is not a form of {val}")
    builder = B.TargetedBuilder(seed=6, n_docs=1500)
    recs = builder.build()
    sfx = [(r, x) for r in recs for x in r["_suffixes"]]
    noisy = [(r, x) for r, x in sfx if x["surface"] == "noisy"]
    # ~340 suffixed mentions: one standard deviation is 1.2 points; the build's
    # own --stats check holds the share at 5% +/- 2 on 5,000+ documents
    check(0.02 <= len(noisy) / len(sfx) <= 0.08, f"noisy suffixes are ~5% of suffixed mentions ({len(noisy)}/{len(sfx)})")
    wrong = []
    for r, x in noisy:
        try:
            if r["text"][x["start"]:x["end"]] == S.inflect(r["text"][x["start"]:x["stem_end"]], x["case"]):
                wrong.append(r["text"][x["start"]:x["end"]])
        except S.NotInflectable:
            pass
    check(not wrong, "a noisy form is never the correct one", wrong[:3])
    check(all(any((e["start"], e["end"]) == (x["start"], x["end"]) for e in r["entities"]) for r, x in noisy),
          "each noisy word is labelled whole (D-9)")


TESTS = [("renderer", test_renderer), ("resolver: declared forms and guards", test_resolver_declared),
         ("validate: apostrophe exemption", test_validate_apostrophe), ("inflected documents", test_build),
         ("C1 {v:CASE} frames", test_c1_case_frames), ("surname -lI harmony", test_surname_harmony),
         ("English spellings harmonise by the written letters", test_english_spelling_harmony),
         ("P4-2 round 1: -dAyIQ, surname -gil, baxılması", test_p4_2_round1),
         ("P4-2 round 2: apostrophe, k/q endings, frames, spellings, decoys, pools", test_p4_2_round2),
         ("noisy suffixes: misspelt, still labelled", test_noisy_suffixes)]

if __name__ == "__main__":
    for name, fn in TESTS:
        print(name)
        fn()
    print("=" * 60)
    print(f"PASSED {PASS}   FAILED {FAIL}")
    print("=" * 60)
    for f in FAILURES:
        print("  FAIL:", f)
    sys.exit(1 if FAIL else 0)
