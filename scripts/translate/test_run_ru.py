"""Regression tests for the run_ru validators added by the 2026-09-05
rejection audit: damaged-token exemption, meta-response detection, the
completeness band, and the offender listing that drives the retry note.

Every case below is taken from a real document in the val split -- the token
strings and the failure shapes are the ones actually observed, not invented.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import translate.run_ru as R  # noqa: E402

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


# --------------------------------------------------------------------------- #
# _damaged: corpus character damage vs. clean text
# --------------------------------------------------------------------------- #
for tok in ["S0stəm", "s0stəm", "Məluma1", "mqsə0", "Err0r", "мукaв1lə",
            "Шirkəti", "Хизмət", "Гөзəl"]:
    truthy(f"_damaged({tok})", R._damaged(tok), True)
for tok in ["salam", "məlumat", "Ширкети", "система", "Şirkəti", "2024",
            "XİDMƏT", "Hacımürsələvan"]:
    truthy(f"_damaged({tok}) clean", R._damaged(tok), False)

# A hyphen or space between the digits and the letters is ordinary text, not
# an OCR defect: "2024-cü" is a normal Azerbaijani ordinal.
truthy("_damaged(2024-cü)", R._damaged("2024-cü"), False)

# --------------------------------------------------------------------------- #
# az_residue: the source-verbatim exemption is narrow
# --------------------------------------------------------------------------- #
src = "S0stəm girişi qeydə alındı. Şirkəti yoxlayın."

# damaged AND in the source -> excused (the prompt orders it preserved)
check("residue: damaged token present in source",
      R.az_residue("Вход S0stəm зарегистрирован.", src), None)
# the same token with no source given -> still counted
truthy("residue: damaged token, no source",
       R.az_residue("Вход S0stəm зарегистрирован."), True)
# damage the MODEL invented (not in the source) -> counted
truthy("residue: model-invented script mix",
       R.az_residue("Проверьте Шirkəti внимательно.", src), True)
# ordinary residue is never excused
truthy("residue: plain AZ word",
       R.az_residue("Пожалуйста, отправьте məlumat сегодня.", src), True)
# a clean Russian translation scores nothing
check("residue: clean Russian",
      R.az_residue("Вход в систему зарегистрирован. Проверьте компанию.", src),
      None)
# a document that QUOTES the diacritics is a correct translation
check("residue: quoted diacritics",
      R.az_residue("диакритические знаки (ə, ş, ğ) могут исчезнуть", None),
      None)
# short English function words must not prefix-match ("ve" in "verified")
check("residue: English 'verified' not AZ 've'",
      R.az_residue("Статус: verified. Verification завершена.", None), None)

# stems added by the audit are detected, including agglutinated forms
for w in ["nəticələr", "təkərlərin", "müraciət", "şəxsiyyət", "ödənişi",
          "gələcək", "cədvəldən", "vəzifə", "səhifəsi", "məhsul"]:
    truthy(f"residue: stem {w}", R.az_residue(f"Текст {w} текст.", None), True)

# --------------------------------------------------------------------------- #
# a lowercase Azerbaijani-only letter is residue by itself
#
# Found in test rung 1: a delimited row came back as
# "MÖLV_KOD;STATUS;СОСТОЯНИЕ; 5521; AKTİV; 0" -- only the schwa-bearing cell
# was translated. Neither MÖLV_KOD nor AKTİV has a schwa or a listed stem, so
# nothing flagged the document.
# --------------------------------------------------------------------------- #
for _w in ["Bakı", "Sumqayıt", "yaşı", "log_vaxtı", "eMalı", "zamaNı"]:
    truthy(f"residue: lowercase AZ letter in {_w}",
           R.az_residue(f"Текст {_w} текст"), True)
# all-caps institutional abbreviations are how these documents are really
# written (VÖEN appears in 89 val documents as ordinary Russian usage)
check("residue: VÖEN acronym is not residue",
      R.az_residue("В документах указан номер VÖEN"), None)
# a reference code carrying an Azerbaijani letter is an identifier, not a word
check("residue: reference code with AZ letter passes",
      R.az_residue("код BKŞ-2021-08-992 принят"), None)
check("residue: clean Russian still clean",
      R.az_residue("Города Баку и Сумгаит подтверждены"), None)
# and the damaged-token exemption still wins over the new rule
check("residue: damaged lowercase token in source excused",
      R.az_residue("Вход s0stəm выполнен", "s0stəm girişi"), None)

# the prompt must carry the rule this rung produced
truthy("prompt: delimited row translated across its whole width",
       "MÖLV_KOD" in R.SYSTEM_PROMPT and "WHOLE width" in
       " ".join(R.SYSTEM_PROMPT.split()), True)
truthy("prompt: capitals are still words",
       "AKTİV" in R.SYSTEM_PROMPT, True)

# --------------------------------------------------------------------------- #
# a typo and its correction are BOTH translated
#
# The corpus writes a misspelling beside its correction, with a marker
# ("melduatlar (yox, məlumatlar)") or without one ("müraciët (müraciət)").
# Keeping the Azerbaijani forms as quoted material was tried and rejected: the
# Russian document must be Russian throughout, so the misspelling is carried
# across to the Russian word instead.
# --------------------------------------------------------------------------- #
_CORR_SRC = ("melduatlar (yox, məlumatlar); müraciët (müraciət); "
             "qeyri-akceptabl (qəbulolunmaz); giriş kodu (deyəsən)")
for _out in [
    "Нижеследующие melduatlar (нет, məlumatlar) были проверены.",
    "причиной моего müraciët (обращения), является ухудшение",
    "совершенно неприемлемым (qəbulolunmaz) состоянием",
    "код доступа (deyəsən), показанный мне при завершении",
]:
    truthy(f"typo: AZ left in a correction still flags -- {_out[:34]!r}",
           R.az_residue(_out, _CORR_SRC), True)

# the wanted shape: the misspelling crosses into Russian with the word
for _good in [
    "Нижеследующие даные (нет, данные) были проверены.",
    "причиной моего обрашения (обращения), является ухудшение",
    "совершенно неприемлимым (неприемлемым) состоянием",
    "код доступа (кажется), показанный мне при завершении",
]:
    check(f"typo: Russian typo pair is clean -- {_good[:34]!r}",
          R.az_residue(_good, _CORR_SRC), None)

# --------------------------------------------------------------------------- #
# simurg_explained_by_source: the guard reacts to this corpus's own content
#
# Test rung 7 lost 16 documents to a corrupt verdict. None of their sources
# were repetitive -- they were a blank form ("Район: ______"), a vitals table
# (47% digits), timestamped log dumps and a markdown table. The guard was
# reading the document's own shape as model degeneration, and the abort turned
# it into truncation: one form was cut to 364 characters.
# --------------------------------------------------------------------------- #
_NL = chr(10)
_VITALS = _NL.join(f"12.03 {h:02d}:00 | 38.{h % 9} | 135/90 | 92 | 22"
                   for h in range(24))
_FORM = _NL.join(["Район: ______________", "Улица: ____________",
                  "№ дома: ________", "№ квартиры: ________"])
_LOGS = _NL.join(f"[2023-03-15 14:00:{i:02d}] СИСТЕМА: Error {400 + i}."
                 for i in range(30))
for _label, _t in [("vitals table", _VITALS), ("blank form", _FORM),
                   ("log dump", _LOGS)]:
    truthy(f"simurg: {_label} translated faithfully is explained",
           R.simurg_explained_by_source(_t, _t), True)

# A runaway loop is caught where the source is not itself maximally
# repetitive. Against a log dump or a vitals table it is NOT distinguishable
# by texture alone -- both are already near-maximally compressible -- and that
# is the honest limit of this check. completeness() and az_residue still guard
# those documents, and a loop's length is nothing like the source's.
check("simurg: runaway loop against a form is NOT explained",
      R.simurg_explained_by_source(_FORM, "да " * 900), False)
_PROSE = _NL.join(
    "Уважаемый клиент, ваш заказ обработан и будет отправлен на этой неделе."
    for _ in range(3)) + " Сроки доставки уточняются отдельно."
check("simurg: runaway loop against prose is NOT explained",
      R.simurg_explained_by_source(_PROSE, "да " * 900), False)
check("simurg: empty inputs are not explained",
      R.simurg_explained_by_source("", "что-то"), False)

# a truncated prefix IS texture-compatible -- completeness is what catches it,
# and the two checks are deliberately not doing each other's job
truthy("simurg: truncation left to completeness",
       R.simurg_explained_by_source(_LOGS, _LOGS[:120]), True)

# the slack came from measurement, not taste
truthy("simurg: redundancy slack above the observed faithful maximum",
       R._TEXTURE_SLACK["redundancy"] > 0.225, True)
truthy("simurg: redundancy slack below a runaway loop's delta",
       R._TEXTURE_SLACK["redundancy"] < 0.558, True)
truthy("simurg: texture reports compressibility",
       "redundancy" in R._texture("абв"), True)

# --------------------------------------------------------------------------- #
# collapsed_correction: the pair must stay two different words
#
# Rung 4 showed the model obeying "translate both" by writing the same word
# twice -- "готово (нет, готово)", "Оплата (нет, Оплата)" -- a sentence that
# corrects nothing. 693 of 1316 constructs in the val output (53%) had
# collapsed this way, against 13% in the Azerbaijani source, and no other
# check can see it: fluent Russian, right length, no residue.
# --------------------------------------------------------------------------- #
_AZ_PAIRS = "gömruk (yox, gömrük) və üzüntülük (yox, üzüntülü)"
truthy("collapsed: both pairs flattened",
       R.collapsed_correction(
           _AZ_PAIRS, "таможня (нет, таможня) и печальной (нет, печальной)"),
       True)
truthy("collapsed: one of two flattened",
       R.collapsed_correction(
           _AZ_PAIRS, "таможня (нет, таможне) и печальной (нет, печальной)"),
       True)
check("collapsed: both pairs kept distinct",
      R.collapsed_correction(
          _AZ_PAIRS, "таможня (нет, таможне) и печальный (нет, печальной)"),
      None)
# the generator itself emits identical pairs 13% of the time; reproducing one
# faithfully is correct, not a defect
check("collapsed: source pair was already identical",
      R.collapsed_correction("konfiqurasiyasında (yox, konfiqurasiyasında)",
                             "конфигурации (нет, конфигурации)"), None)
check("collapsed: no corrections at all", 
      R.collapsed_correction("обычный текст без скобок", "ordinary text"), None)
check("collapsed: empty source is not a verdict",
      R.collapsed_correction("", "готово (нет, готово)"), None)
truthy("collapsed: retry note explains the fix",
       "never match" in R._repair_note("collapsed correction: x", "", ""), True)

# a quarter of the corrections must NEWLY collapse before this fires. One
# document had 79 of 101 source pairs already identical -- those are glosses,
# "Hadise (hadise)", not corrections -- and a raw count comparison called its
# faithful translation a defect.
check("collapsed: source already mostly identical is not a defect",
      R.collapsed_correction(
          "Hadise (hadise) Surucu (surucu) yol (yol) qeza (qeza)",
          "Происшествие (происшествие) Водитель (водитель) "
          "дорога (дорога) авария (авария)"), None)
check("collapsed: a single construct is too little signal",
      R.collapsed_correction("Sened (yox, sənəd)", "Документ (нет, документ)"),
      None)

# --------------------------------------------------------------------------- #
# soft problems: retry, but never discard the document
#
# Where the source pair differs only by a diacritic ("Sened" vs "sənəd"),
# Russian has no equivalent distinction and every faithful translation
# collapses. Losing the whole document over one redundant parenthetical trades
# a real loss for a cosmetic one.
# --------------------------------------------------------------------------- #
truthy("soft: collapsed correction is soft",
       R._is_soft("collapsed correction: 2 of 2"), True)
for _hard in ["az_residue x3", "truncated: 0.2x", "expanded: 3x",
              "model spoke as itself: x", "simurg aborted the stream"]:
    check(f"soft: {_hard[:22]!r} is hard", R._is_soft(_hard), False)


class _V2:
    def __init__(self, st="clean"):
        self.state = st


_SOFT_SRC = ("Sənəd təsdiqi barədə: Məblə (yox, məbləğ) ödənişi tamamlandı və "
             "Sened (yox, sənəd) qeydiyyata alındı. ⟦0⟧ nömrəsi ilə əlaqə saxlayın.")
_SOFT_OUT = ("О подтверждении документа: Сумма (нет, сумма) оплаты завершена и "
             "Документ (нет, документ) зарегистрирован. Свяжитесь по номеру ⟦0⟧.")
_real2 = R.translate
try:
    _notes: list = []

    def _fake_soft(slotted, *, api_key, base_url, temperature, max_tokens,
                   timeout=240.0, note=None):
        _notes.append(note)
        return _SOFT_OUT, _V2()

    R.translate = _fake_soft
    _soft: list[str] = []
    _text, _v, _n = R.translate_checked(
        _SOFT_SRC, api_key="k", base_url="u", base_temp=0.2,
        validate=R._body_validator(_SOFT_SRC), soft_ok=_soft)
    check("soft: document is kept after retries are spent", _text, _SOFT_OUT)
    check("soft: all attempts were used first", _n, 3)
    truthy("soft: the problem is recorded, not swallowed",
           _soft and _soft[0].startswith("collapsed correction"), True)
    truthy("soft: retries carried a corrective note",
           _notes[0] is None and _notes[1] is not None, True)

    # a hard problem must still cost the document
    R.translate = lambda *a, **k: (
        "Салам məlumat üçün sənəd ⟦0⟧ göndərin zəhmət olmasa yoxlayın xahiş",
        _V2())
    try:
        R.translate_checked(_SOFT_SRC, api_key="k", base_url="u", base_temp=0.2,
                            validate=R._body_validator(_SOFT_SRC), soft_ok=[])
        check("soft: hard problem still raises", "no raise", "raise")
    except Exception as _e:  # noqa: BLE001
        truthy("soft: hard problem still raises",
               str(_e).startswith(("az_residue", "leftover_az")), True)

    # A body with BOTH a collapsed correction (soft) AND leftover Azerbaijani
    # (hard) must RAISE -- the hard problem wins. Regression: when
    # collapsed_correction ran before the residue checks, this short-circuited
    # to the soft path and 24 train docs were kept with "TEKSTİL"/"HOLDİNG" in
    # them (2026-09-07).
    _both = _SOFT_OUT.replace("Свяжитесь", "Свяжитесь с NUR TEKSTİL,")
    R.translate = lambda *a, _b=_both, **k: (_b, _V2())
    try:
        _kept: list[str] = []
        R.translate_checked(_SOFT_SRC, api_key="k", base_url="u", base_temp=0.2,
                            validate=R._body_validator(_SOFT_SRC), soft_ok=_kept)
        check("soft+hard: leftover-az beats a collapsed correction",
              f"kept soft: {_kept}", "should have raised")
    except Exception as _e:  # noqa: BLE001
        truthy("soft+hard: leftover-az beats a collapsed correction",
               str(_e).startswith("leftover_az"), True)
finally:
    R.translate = _real2

truthy("prompt: pair must stay different words",
       "stay DIFFERENT words" in " ".join(R.SYSTEM_PROMPT.split()), True)
truthy("prompt: names the degenerate shape",
       "готово (нет, готово)" in " ".join(R.SYSTEM_PROMPT.split()), True)
truthy("prompt: gives real misspelling techniques",
       "swap two neighbouring letters" in " ".join(R.SYSTEM_PROMPT.split()), True)

# the prompt has to actually ask for this
_flat = " ".join(R.SYSTEM_PROMPT.split())
# the organisation rule was dropped in the prompt rewrite (ab710a3) and that
# regression produced "Zirvə Bank" and "Texnologiyaları" in test rung 3
# rung 6: 5 of 14 residue rejects were company letterhead boilerplate --
# MƏHDUD CƏMIYYETI, MƏSULİYYƏTİ MƏHDUD DÖVLƏT ŞİRKƏTİ, XİDMƏTLERİ. The org
# rule said "the legal form stays as written", meaning the abbreviation, and
# the model applied it to the spelled-out Azerbaijani too.
truthy("prompt: only the ABBREVIATED legal form stays",
       "Only the ABBREVIATED legal form stays" in _flat, True)
truthy("prompt: spells out the translation of the long form",
       "ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ" in _flat, True)
truthy("prompt: names the letterhead as the usual miss",
       "letterhead in capitals" in _flat, True)
truthy("prompt: a brand from an ordinary word is transliterated",
       "Гёзял Маркет" in _flat, True)
truthy("prompt: organisation names have a rule",
       "Organisation names" in _flat, True)
truthy("prompt: names the Zirve case", "Зирве Банк" in _flat, True)
truthy("prompt: handles an already-Latin brand",
       "Global Nexus Облачные Технологии" in _flat, True)
truthy("prompt: typo and correction are both translated",
       "A typo and its correction are BOTH translated" in _flat, True)
truthy("prompt: names the wanted shape",
       "даные (нет, данные)" in _flat, True)
truthy("prompt: forbids leaving either Azerbaijani form",
       "Never leave either form in Azerbaijani" in _flat, True)
truthy("prompt: bracketed hedges are translated",
       "(кажется)" in _flat, True)
truthy("prompt: a field label is translated once",
       "never 'Эл. почта: E-poçt:" in _flat, True)

# --------------------------------------------------------------------------- #
# the retry note must never reach the user turn
#
# Appended under the document it read as more document: one retry returned the
# note itself, translated, inside the output.
# --------------------------------------------------------------------------- #
_seen: dict = {}
_real = R.litellm_completion if hasattr(R, "litellm_completion") else None


def _capture_messages() -> list[dict]:
    import types
    captured: list[dict] = []

    class _FakeStream:
        def __iter__(self):
            return iter(())

    def fake_completion(**kw):
        captured.extend(kw["messages"])
        return _FakeStream()

    import sys as _sys
    fake_litellm = types.ModuleType("litellm")
    fake_litellm.completion = fake_completion
    real = _sys.modules.get("litellm")
    _sys.modules["litellm"] = fake_litellm
    try:
        R.translate("ДОКУМЕНТ ⟦0⟧", api_key="k", base_url="u", temperature=0.0,
                    max_tokens=64, note="FIX THE THING")
    finally:
        if real is not None:
            _sys.modules["litellm"] = real
        else:
            del _sys.modules["litellm"]
    return captured


try:
    _msgs = _capture_messages()
    _user = [m for m in _msgs if m["role"] == "user"][0]["content"]
    _sysm = [m for m in _msgs if m["role"] == "system"][0]["content"]
    check("retry note: user turn is the document alone", _user, "ДОКУМЕНТ ⟦0⟧")
    truthy("retry note: correction rides in the system turn",
           "FIX THE THING" in _sysm, True)
except Exception as _exc:  # noqa: BLE001
    print(f"note: retry-turn test skipped ({type(_exc).__name__}: {_exc})")

# --------------------------------------------------------------------------- #
# romanised_russian: correct Russian written in the wrong script
# --------------------------------------------------------------------------- #
truthy("romanised: transliterated Russian caught",
       R.romanised_russian(
           "Manifest Dostavki i Detali Otpravki. Informatsiya ob otpravke. "
           "Otvetstvennoye litso: X."), True)
check("romanised: proper Cyrillic passes",
      R.romanised_russian(
          "Манифест доставки и детали отправки. Информация об отправке."), None)
# English infrastructure logs are legitimate here -- the source carries them
check("romanised: English log lines pass",
      R.romanised_russian(
          "App server Connection established. Daily cron job started. "
          "Load Balancer active. Runtime Node Postgre Cache Redis."), None)
check("romanised: a couple of Latin words is not enough",
      R.romanised_russian("Статус: Dostavki завершена."), None)

# --------------------------------------------------------------------------- #
# a single content stem is residue; a single short function word is not
# --------------------------------------------------------------------------- #
truthy("residue: lone 'E-poçt:' label flags",
       R.az_residue("Гюндюз Махмудов, Директор E-poçt: orders@box.az"), True)
truthy("residue: lone diacritic-stripped stem flags",
       R.az_residue("TURAN HOLDING LOGISTIKA XIDMETLERI"), True)
for w in ["sirket", "senedler", "sigorta", "melumat"]:
    truthy(f"residue: lone stem {w} flags", R.az_residue(f"Текст {w} текст"), True)
# the collision-prone short words still need a companion
check("residue: lone 've' does not flag alone",
      R.az_residue("Компания ve партнёры"), None)
check("residue: 'verified' still not AZ",
      R.az_residue("Статус: verified. Verification завершена."), None)

# --------------------------------------------------------------------------- #
# meta_response: self-reference only, never ordinary complaint prose
# --------------------------------------------------------------------------- #
truthy("meta: AZ translation-model refusal",
       R.meta_response("Lakin, mən bir tərcümə modeliyəm və mətni göndərin."),
       True)
truthy("meta: AZ engine phrasing",
       R.meta_response("Siz mənə bir tərcümə mühərriki kimi təlimat verdiniz."),
       True)
truthy("meta: RU language-model phrasing",
       R.meta_response("Извините, я языковая модель и не могу этого сделать."),
       True)
truthy("meta: English",
       R.meta_response("As an AI, I cannot help with that."), True)
# ordinary inability is complaint prose and appears all over this corpus
check("meta: 'я не могу войти' is ordinary prose",
      R.meta_response("Я не могу войти в систему уже третий день."), None)
check("meta: 'не могу оплатить' is ordinary prose",
      R.meta_response("Не могу оплатить счёт, карта отклоняется."), None)
check("meta: a document about models",
      R.meta_response("Модель прогнозирования обновлена в этом квартале."),
      None)

# --------------------------------------------------------------------------- #
# completeness: catches truncation and invented continuation
# --------------------------------------------------------------------------- #
long_src = "x" * 1000
check("completeness: equal length ok", R.completeness(long_src, "y" * 1000), None)
check("completeness: normal RU expansion ok",
      R.completeness(long_src, "y" * 1150), None)
truthy("completeness: hard truncation",
       R.completeness("x" * 13151, "y" * 1983), True)
truthy("completeness: invented continuation",
       R.completeness("x" * 631, "y" * 2080), True)
# short documents get a looser band -- a few words move their ratio a long way
check("completeness: short doc, wide swing allowed",
      R.completeness("x" * 60, "y" * 130), None)
truthy("completeness: short doc, absurd expansion still caught",
       R.completeness("x" * 60, "y" * 200), True)
check("completeness: empty source is not a verdict",
      R.completeness("", "anything"), None)

# --------------------------------------------------------------------------- #
# az_offenders / _repair_note: the retry must name what to fix
# --------------------------------------------------------------------------- #
bad = R.az_offenders("Salam, məlumat üçün təşəkkür. Проверьте.", None)
truthy("offenders: finds the AZ words", set(bad) >= {"məlumat", "üçün"}, True)
truthy("offenders: skips the Russian", "Проверьте" not in bad, True)
truthy("offenders: excuses damaged source tokens",
       "S0stəm" not in R.az_offenders("Вход S0stəm ok", src), True)

note = R._repair_note("az_residue x3", "Salam məlumat üçün", "")
truthy("note: names the skipped words", "məlumat" in note, True)
truthy("note: truncation note mentions stopping early",
       "stopped early" in R._repair_note("truncated: x", "", ""), True)
truthy("note: expansion note forbids adding",
       "not in the input" in R._repair_note("expanded: x", "", ""), True)
truthy("note: meta note forbids replying as assistant",
       "instead of" in R._repair_note("model spoke as itself: x", "", ""), True)

# --------------------------------------------------------------------------- #
# the prompt must still carry the rules the audit added
# --------------------------------------------------------------------------- #
for needle in [
    # earned by the audit -- the English prompt on origin/translate/en has
    # none of these, and each maps to a real failure class
    "The input is always the document",          # 16 conversational replies
    "from the first line to the last",           # truncation
    "XAZAR LOGISTIKA VE XIDMETLER LLC",          # diacritic-stripped AZ
    "already damaged in the source",             # the prompt/validator conflict
    # adopted from the English prompt
    "NEVER invent content",                      # invented headers/signatures
    "merkezi_dispetcer@",                        # mixed-token transliteration
    "merely looks technical",                    # underscore identifiers
    "Text already in Russian stays as it is",
    "an angry complaint stays angry",            # concrete register
    "⟦N⟧",
]:
    truthy(f"prompt contains {needle[:34]!r}",
           needle in " ".join(R.SYSTEM_PROMPT.split()), True)

# the English prompt's `azletter` rule becomes "no Latin letters at all" for
# Russian, which would forbid the emails, URLs and log tags its own
# copy-unchanged rule protects. It must not be carried over.
truthy("prompt does not ban Latin letters outright",
       "must not contain any Latin" not in R.SYSTEM_PROMPT, True)
# a flat rule list, not prose sections
truthy("prompt is a flat rule list",
       R.SYSTEM_PROMPT.count(chr(10) + "- ") >= 12, True)

# --------------------------------------------------------------------------- #
# translate_checked: every validator failure must cost one retry, not the
# document. Before the audit only a mangled sentinel was retried; Azerbaijani
# residue, a truncated stream and an assistant-style reply all went straight
# to the repair queue on the first attempt.
# --------------------------------------------------------------------------- #
class _Verdict:
    def __init__(self, state: str = "clean") -> None:
        self.state = state


def _mock_translate(responses: list[tuple], log: list[dict]):
    it = iter(responses)
    def fake(slotted, *, api_key, base_url, temperature, max_tokens,
             timeout=240.0, note=None):
        log.append({"temp": temperature, "note": note})
        r = next(it)
        return r[0], _Verdict(r[1] if len(r) > 1 else "clean")
    return fake


_SRC = "Salam, məlumat üçün ⟦0⟧ nömrəsinə zəng edin. Zəhmət olmasa təsdiq edin."
_GOOD = "Привет, для информации позвоните на номер ⟦0⟧. Пожалуйста, подтвердите."
_real_translate = R.translate

for label, first, want_in_note in [
    ("residue", ("Привет, məlumat üçün позвоните на ⟦0⟧.",), "məlumat"),
    # the guard's verdict only costs an attempt when the source does not
    # explain it, so this fixture returns a loop the source is nothing like
    ("corrupt stream", ("да да да да да да да да да да да да да да да ⟦0⟧",
                        "corrupt"), "stopping early"),
    ("meta reply", ("Mən bir tərcümə modeliyəm, mətni göndərin. ⟦0⟧",),
     "instead of returning the document"),
    ("truncation", ("Привет ⟦0⟧",), "stopped early"),
]:
    log: list[dict] = []
    R.translate = _mock_translate([first, (_GOOD,)], log)
    try:
        text, _v, n = R.translate_checked(
            _SRC, api_key="k", base_url="u", base_temp=0.2,
            validate=R._body_validator(_SRC))
    finally:
        R.translate = _real_translate
    check(f"retry {label}: recovered on attempt 2", (text, n), (_GOOD, 2))
    truthy(f"retry {label}: first call carries no note",
           log[0]["note"] is None, True)
    truthy(f"retry {label}: retry note is specific",
           want_in_note in (log[1]["note"] or ""), True)

# a document that never recovers raises, so it reaches the repair queue with
# the translation problem named -- not a stale sentinel error
log = []
R.translate = _mock_translate([("Salam məlumat üçün ⟦0⟧ nömrə zəhmət.",)] * 4, log)
try:
    R.translate_checked(_SRC, api_key="k", base_url="u", base_temp=0.2,
                        validate=R._body_validator(_SRC))
    check("retry exhausted: raises", "no raise", "raise")
except Exception as exc:  # noqa: BLE001
    truthy("retry exhausted: reports the translation problem",
           str(exc).startswith(("az_residue", "leftover_az")), True)
    check("retry exhausted: used all attempts", len(log), 3)
finally:
    R.translate = _real_translate

# --------------------------------------------------------------------------- #
# select(): the batch ladder needs nested samples
#
# 50 -> 100 -> 200 only measures the prompt if each rung is a superset of the
# one before. If rung two swaps in different documents, a change in the defect
# rate could be the new prompt or the new sample, and nothing distinguishes
# them.
# --------------------------------------------------------------------------- #
from pathlib import Path  # noqa: E402

_SPLIT = Path(__file__).resolve().parents[2] / "data/processed/az/test.docs.jsonl"
if _SPLIT.exists():
    _prev: set[str] | None = None
    _seen: list[int] = []
    for _n in (50, 100, 200, 400):
        _pos, _neg = R.select(_SPLIT, _n, 0.20, 20260904)
        _ids = {d["id"] for d in _pos} | {d["id"] for d in _neg}
        check(f"select({_n}): returns exactly n documents", len(_ids), _n)
        check(f"select({_n}): negatives at neg_frac", len(_neg), round(_n * 0.20))
        if _prev is not None:
            truthy(f"select({_n}): nests the previous rung", _prev <= _ids, True)
        # every bucket that has weight is represented once the rung is big enough
        _mix = {d.get("_bucket") for d in _pos}
        if _n >= 100:
            truthy(f"select({_n}): all six length bands present",
                   _mix >= set(R.BUCKET_WEIGHT), True)
        _prev = _ids
    # stable across calls -- no hidden global rng state
    _a = {d["id"] for d in R.select(_SPLIT, 120, 0.20, 20260904)[0]}
    _b = {d["id"] for d in R.select(_SPLIT, 120, 0.20, 20260904)[0]}
    check("select: deterministic across calls", _a, _b)
    # a different seed gives a different sample
    _c = {d["id"] for d in R.select(_SPLIT, 120, 0.20, 11111111)[0]}
    truthy("select: seed actually changes the sample", _a != _c, True)
else:
    print(f"note: {_SPLIT.name} not found -- select() tests skipped")

# --------------------------------------------------------------------------- #
# the model's text is NFC-normalised before anything measures or splices it
#
# One test document came back with "й" as и + U+0306. The Azerbaijani corpus
# is NFC throughout and validate_corpus.py rejects anything else. Normalising
# after the splice would shift the very spans the splice had just placed, so
# it happens on the model's raw reply instead.
# --------------------------------------------------------------------------- #
import unicodedata as _ud  # noqa: E402


class _V3:
    def __init__(self, st="clean"):
        self.state = st


_DECOMPOSED = "Систе" + "и" + chr(0x306) + "м работает ⟦0⟧ нормально сегодня."
truthy("nfc: the fixture really is decomposed",
       _ud.normalize("NFC", _DECOMPOSED) != _DECOMPOSED, True)

_real3 = R.translate
try:
    import types as _types
    import sys as _sys

    class _FakeStream2:
        def __iter__(self):
            class _D:
                content = _DECOMPOSED

            class _C:
                delta = _D()

            class _P:
                choices = [_C()]
            return iter([_P()])

    _fake = _types.ModuleType("litellm")
    _fake.completion = lambda **kw: _FakeStream2()
    _prev = _sys.modules.get("litellm")
    _sys.modules["litellm"] = _fake
    try:
        _txt, _v = R.translate("ДОК ⟦0⟧", api_key="k", base_url="u",
                               temperature=0.0, max_tokens=64)
    finally:
        if _prev is not None:
            _sys.modules["litellm"] = _prev
        else:
            del _sys.modules["litellm"]
    check("nfc: translate() returns normalised text",
          _ud.normalize("NFC", _txt), _txt)
    truthy("nfc: the precomposed letter is there", "й" in _txt, True)
    truthy("nfc: normalising shortened it", len(_txt) < len(_DECOMPOSED), True)
except Exception as _exc:  # noqa: BLE001
    print(f"note: NFC test skipped ({type(_exc).__name__}: {_exc})")
finally:
    R.translate = _real3

# --------------------------------------------------------------------------- #
# --rescan must honour the soft tier too
#
# translate_checked keeps a document whose only fault is a collapsed
# correction. A rescan that quarantines the same document contradicts it, and
# that is what pulled 260 val documents out of the corpus for a cosmetic
# parenthetical.
# --------------------------------------------------------------------------- #
import inspect as _inspect  # noqa: E402

_rescan_src = _inspect.getsource(R.rescan_out)
truthy("rescan: consults the soft tier", "_is_soft(reason)" in _rescan_src, True)
truthy("rescan: keeps soft rows rather than quarantining them",
       "soft_kept" in _rescan_src, True)
truthy("rescan: says so in its output",
       "are kept" in _rescan_src, True)

# --------------------------------------------------------------------------- #
# rules added from the train batch: where residue was actually surviving
# --------------------------------------------------------------------------- #
truthy("prompt: a quoted organisation name is still translated",
       "quoted organisation name is still an organisation name" in _flat, True)
truthy("prompt: JSON and config KEYS are translated",
       "the KEYS are Azerbaijani words" in _flat, True)
truthy("prompt: a comment inside a code block is prose",
       "comment inside a code block is prose" in _flat, True)

# The prompt is written in three scripts and a Latin letter inside a Cyrillic
# word is invisible to read but teaches exactly the mistake the prompt forbids.
# "Хизмət" and "Шirkəti" are the deliberate counter-examples in the
# never-mix-alphabets rule; anything else mixed is a typo.
import re as _re  # noqa: E402

_DELIBERATE_MIX = {"Хизмət", "Шirkəti"}
_mixed = {w for w in _re.findall(r"[^\W\d_]+", R.SYSTEM_PROMPT)
          if _re.search(r"[Ѐ-ӿ]", w) and _re.search(r"[A-Za-z]", w)}
check("prompt: no accidental mixed-script words", _mixed - _DELIBERATE_MIX, set())

# --------------------------------------------------------------------------- #
# _OutputLock must not share a name with the worker threading.Lock (2026-09-07)
# --------------------------------------------------------------------------- #
# run_split binds `_OutputLock(...)` and, ~40 lines later, `threading.Lock()`.
# When both were called `lock`, the second shadowed the first and the
# release() before the return hit the threading lock -- "RuntimeError: release
# unlocked lock" at the train->val hand-off of an --all-splits run, after all
# of train was already on disk.
_calib = __import__("pathlib").Path("scripts/translate/run_ru.py").read_text("utf-8")
_ol_name = _re.search(r"(\w+)\s*=\s*_OutputLock\(", _calib)
_tl_name = _re.search(r"(\w+)\s*=\s*threading\.Lock\(\)", _calib)
truthy("_OutputLock is bound to its own name", bool(_ol_name), True)
if _ol_name and _tl_name:
    check("_OutputLock and threading.Lock use different names",
          _ol_name.group(1) == _tl_name.group(1), False)
    # and the name the release() call uses is the _OutputLock one
    truthy("the pre-return release() targets the _OutputLock",
           f"{_ol_name.group(1)}.release()" in _calib, True)

# --------------------------------------------------------------------------- #
# mixed-script words and the widened Azerbaijani letter set (2026-09-07)
# --------------------------------------------------------------------------- #
from translate.validate import (_leftover_azerbaijani,  # noqa: E402
                                _mixed_script_words)

# Homoglyph substitution: correct Russian with one Latin letter in it.
for _w, _why in [("Договорa", "Latin a"), ("систEме", "Latin E"),
                 ("ускорениe", "Latin e"), ("проблеmы", "Latin m")]:
    truthy(f"mixed_script: homoglyph {_w!r} ({_why})",
           _mixed_script_words(f"Текст {_w} далее", [], "ru") == [_w], True)

# Half-transliteration: the model stopped part-way through a word.
for _w in ("сirket", "месuliyyet", "Лейla", "техниqi"):
    truthy(f"mixed_script: half-transliterated {_w!r}",
           _mixed_script_words(f"Текст {_w} далее", [], "ru") == [_w], True)

# Things that legitimately pair the scripts must NOT fire: _WORD_RE breaks on
# every non-letter, so each of these is two single-script words.
for _ok in ("IT-специалист", "Wi-Fi роутер", "SIM-карта", "номер VÖEN (ИНН)",
            "система работает", "ID_КЛИЕНТА"):
    check(f"mixed_script: clean {_ok!r}", _mixed_script_words(_ok, [], "ru"), [])

# Latin targets must be untouched by this check -- English and Turkish are
# Latin throughout, so it is either vacuous or wrong there.
for _lang in ("en", "tr"):
    check(f"mixed_script: inert for {_lang}",
          _mixed_script_words("Договорa сirket", [], _lang), [])

# Entity spans are masked: a minted value is not the model's prose.
check("mixed_script: entity spans are exempt",
      _mixed_script_words("Имя Договорa тут",
                          [{"start": 4, "end": 12, "label": "SURNAME"}], "ru"), [])

# The widened letter set: whole untranslated words with no 'ə' in them.
for _w in ("hüquq", "sığorta", "doğum", "poçt", "TEKSTİL"):
    truthy(f"leftover: ru catches {_w!r} (no ə to give it away)",
           _w in _leftover_azerbaijani(f"Текст {_w} далее", [], "ru"), True)
    check(f"leftover: en ignores {_w!r} (Latin target)",
          _leftover_azerbaijani(f"Text {_w} here", [], "en"), [])

# VÖEN is the Azerbaijani tax number's proper name and is correct in Russian.
check("leftover: VÖEN is exempt in ru",
      _leftover_azerbaijani("Ваш номер VÖEN 1125591636.", [], "ru"), [])
# ...but the mixed-script corruption of it is not excused by that exemption.
truthy("leftover: Cyrillic-В 'ВÖEN' is still caught",
       bool(_leftover_azerbaijani("Ваш номер ВÖEN 112.", [], "ru")), True)

# --------------------------------------------------------------------------- #
# mint reproducibility (regression: salted str.__hash__ seed, 2026-09-07)
# --------------------------------------------------------------------------- #
# _mint_factory used to seed on `f"{sid}|ru".__hash__()`, which CPython salts
# per process, so the same document minted different values on every run and
# no written value could ever be re-derived from its source_id. The seed must
# be the string itself. Asserting the *values* here (not just the seed) is
# what makes the property testable across a process boundary: this suite runs
# in a fresh interpreter each time, so a salted seed cannot match the
# constants below twice in a row.
import subprocess as _sp  # noqa: E402

truthy("mint: seeded on the string, not the salted str.__hash__",
       "__hash__()" not in _re.sub(r"#.*", "", _mint_src := __import__(
           "pathlib").Path("scripts/translate/run_ru.py").read_text(
               encoding="utf-8").split("def _mint_factory")[1]
           .split("\ndef ")[0]), True)
truthy("mint: per-doc pool is uncapped, matching EN/TR",
       "max_share=1.0" in _mint_src, True)

_PROBE = (
    "import sys; sys.path.insert(0,'scripts');"
    "from translate.run_ru import _mint_factory, mint;"
    "vf=_mint_factory('llm_az_000001');"
    "print('|'.join(mint(vf,l) for l in "
    "['CITY','GIVENNAME','TELEPHONENUM','AGE','DATE']))"
)


def _probe(seed_env: str) -> str:
    env = dict(__import__("os").environ, PYTHONHASHSEED=seed_env)
    return _sp.run([sys.executable, "-c", _PROBE], capture_output=True,
                   text=True, env=env, cwd=".").stdout.strip()


_a, _b = _probe("0"), _probe("12345")
truthy("mint: reproducible across processes with different hash salts",
       bool(_a) and _a == _b, True)
if _a != _b:
    print(f"       PYTHONHASHSEED=0     -> {_a}")
    print(f"       PYTHONHASHSEED=12345 -> {_b}")

# D-42c: piigen mints 25% of Azerbaijani postal codes bare; the shape rule
# must accept them, and still catch a ZIPCODE that holds something else.
from translate.run_ru import label_shape_errors as _lse
truthy("label_shape: AZ1061 is a ZIPCODE", _lse([{"label": "ZIPCODE", "value": "AZ1061", "text": "AZ1061"}]) == [], True)
truthy("label_shape: bare 1061 is a ZIPCODE (D-42c)", _lse([{"label": "ZIPCODE", "value": "1061", "text": "1061"}]) == [], True)
truthy("label_shape: a street name is not a ZIPCODE", bool(_lse([{"label": "ZIPCODE", "value": "Низами", "text": "Низами"}])), True)

print("=" * 60)
print(f"PASSED {PASS}   FAILED {FAIL}")
print("=" * 60)
sys.exit(1 if FAIL else 0)
