"""Azerbaijani suffixes on names, surnames, cities and streets (P2-4c, RC8).

Only 7.8% of GIVENNAME, 10.1% of SURNAME, 12.4% of CITY and 7.6% of STREET
mentions in the Azerbaijani training documents carry any suffix, almost all
genitive/dative on names and locative on places; the instrumental, -dakı,
-gil, "I am in ...", question and "the one of" forms occur 0 times. Real text
inflects these words all the time, so a model trained on bare names misses
or splits them. `inflect(value, case, label)` writes every form.

Rules (Azerbaijani orthography; sources in the P2-4c task log):
  * vowel harmony from the LAST vowel of what is written so far, so stacked
    suffixes harmonise one after another (Bakı-da-dır, Məmmədov-lar-dan):
    two-way A = a | ə, four-way I = ı | i | u | ü, and Q = q | k for the
    final consonant of the 1st-person plural ending (Bakıdayıq, but
    Gəncədəyik: P4-2 round 1);
  * buffer consonants: y before a vowel-initial suffix after a vowel
    (Bakıya, Bakıyla, Leylayam); n for the genitive and accusative after a
    vowel (Bakının, Bakını); the pronominal n after a STREET's possessive
    -(s)I (küçəsinə, küçəsində, küçəsindən, küçəsindəki);
  * k -> y and q -> ğ before a vowel happen only in words of Azerbaijani
    origin; borrowed words never change (official orthography norms). Most
    names are Arabic or Persian borrowings (the corpus writes Rəfiqin, not
    Rəfiğin), so a name keeps its k/q unless it ends in one of the native
    words of NATIVE_KQ_ENDINGS (Alçiçək -> Alçiçəyin, Tapdıq -> Tapdığın:
    P4-2 round 2). With an apostrophe the name stays as written (Çiçək'in);
  * an abbreviated street (`küç.`, `pr.`) is not inflected.

The suffix is part of the labelled span (decision D-9). Forms whose meaning
moves away from the place itself (-lı "native of": bakılı) are not written:
they stay unlabelled by team decision (2026-10-02).
"""

from __future__ import annotations

import re

from ..text import fold_diacritics

BACK, FRONT = set("aıou"), set("eəiöü")
VOWELS = BACK | FRONT

# C1's thirteen codes (A4)
C1_CASES = ("gen", "dat", "acc", "loc", "abl", "ins", "rel",
            "pl", "pl_gen", "pl_dat", "pl_loc", "pl_abl", "cop")

# Morphemes in archiphoneme notation: A = a|ə, I = ı|i|u|ü, Q = q|k (after a
# back | front vowel), (y)/(n) = buffer
# after a vowel, {n} = the pronominal n after a possessive stem (streets).
FORMS: dict[str, tuple[str, ...]] = {
    # --- C1: the task document's cases
    "gen": ("(n)In",), "dat": ("{n}(y)A",), "acc": ("(n)I",),
    "loc": ("{n}dA",), "abl": ("{n}dAn",), "ins": ("(y)lA",),
    "rel": ("{n}dA", "kI"), "cop": ("dIr",),
    "pl": ("lAr",), "pl_gen": ("lAr", "In"), "pl_dat": ("lAr", "A"),
    "pl_loc": ("lAr", "dA"), "pl_abl": ("lAr", "dAn"),
    # --- tier 2: common in real text, never generated before (research, 2026-10-02)
    "gil": ("gil",), "gil_gen": ("gil", "In"), "gil_dat": ("gil", "A"),
    "gil_loc": ("gil", "dA"), "gil_abl": ("gil", "dAn"),            # Əsgərgilə: to Əsgər's family
    "pred1": ("(y)Am",), "pred_formal": ("sInIz",),                  # Mən Əsgərəm; Siz Əsgərsiniz?
    "loc_pred1": ("{n}dA", "(y)Am"), "loc_pred2": ("{n}dA", "sAn"),  # Bakıdayam, Bakıdasan
    "loc_pred1pl": ("{n}dA", "(y)IQ"),                               # Bakıdayıq, Gəncədəyik
    "loc_cop": ("{n}dA", "dIr"),                                     # Bakıdadır, küçəsindədir
    "q": ("mI",), "loc_q": ("{n}dA", "mI"),                          # Əsgərmi? Bakıdamı?
    "past": ("(y)dI",), "loc_past": ("{n}dA", "(y)dI"),              # Leylaydı, Bakıdaydı
    "loc_past1": ("{n}dA", "(y)dIm"),                                # Bakıdaydım
    "gen_ki": ("(n)In", "kI"),                                       # Əsgərinki: Əsgər's one
    "term_dek": ("{n}(y)A", "dək"), "term_can": ("{n}(y)A", "cAn"),  # Bakıyadək, Bakıyacan
    "poss1": ("(I)m",), "poss1pl": ("(I)mIz",),                      # Əziz Leylam; doğma Bakımız
    "cond": ("(y)sA",), "loc_cond": ("{n}dA", "(y)sA"),              # Əsgərsə; Bakıdaysa
}
TIER2_GROUPS = {
    "gil": ("gil", "gil_gen", "gil_dat", "gil_loc", "gil_abl"),
    "personal": ("pred1", "pred_formal", "loc_pred1", "loc_pred2", "loc_pred1pl"),
    "loc_cop": ("loc_cop",), "question": ("q", "loc_q"),
    "past": ("past", "loc_past", "loc_past1"), "gen_ki": ("gen_ki",),
    "terminative": ("term_dek", "term_can"), "possessive": ("poss1", "poss1pl"),
    "conditional": ("cond", "loc_cond"),
}
CASE_GROUP = {c: c for c in C1_CASES} | {c: g for g, cs in TIER2_GROUPS.items() for c in cs}

_PERSON = set(C1_CASES) - {"pl", "pl_gen", "pl_dat", "pl_loc", "pl_abl"} | {
    "gil", "gil_gen", "gil_dat", "gil_loc", "gil_abl", "pred1", "pred_formal",
    "q", "past", "gen_ki", "cond"}
APPLIES: dict[str, frozenset[str]] = {
    "GIVENNAME": frozenset(_PERSON | {"poss1"}),
    # the family plural: Məmmədovlar, Məmmədovlardan
    "SURNAME": frozenset(_PERSON | {"pl", "pl_gen", "pl_dat", "pl_loc", "pl_abl"}),
    "CITY": frozenset({"gen", "dat", "acc", "loc", "abl", "ins", "rel", "cop",
                       "loc_cop", "loc_pred1", "loc_pred2", "loc_pred1pl", "q", "loc_q",
                       "loc_past", "loc_past1", "term_dek", "term_can", "poss1pl",
                       "loc_cond"}),
    "STREET": frozenset({"gen", "dat", "acc", "loc", "abl", "ins", "rel", "cop",
                         "loc_cop", "loc_pred1", "loc_q", "term_dek"}),
}
# The case suffixes the Turkish-style apostrophe is written before (Bakı'da);
# never before a personal ending or a particle, never on a street.
APOSTROPHE_CASES = frozenset({"gen", "dat", "acc", "loc", "abl", "pl", "pl_gen",
                              "pl_dat", "pl_loc", "pl_abl"})

# Names that are, or end in, an ordinary Azerbaijani word keep the native
# k -> y, q -> ğ change (Çiçək -> Çiçəyin, Alçiçək -> Alçiçəyin). Every other
# name is treated as a borrowing. The list is the (P4-2 round 2); it
# replaces a list of 9 whole names that covered 7 of the 331 k/q-final
# names in the pool, where these endings cover 116.
NATIVE_KQ_ENDINGS = (
    "çiçək", "birçək", "mixək", "bəzək", "dilək", "kömək", "gerçək", "gərək", "tənək",
    "külək", "kəklik", "kiçik", "böyük", "çiyələk", "örnək", "ipək", "istək", "şimşək",
    "əmək", "zirək", "gənclik", "şənlik", "şenlik", "mələk", "fələk", "göyçək", "sevdik",
    "sevindik", "bəyəndik", "güvəndik",
    "yanaq", "ışıq", "işıq", "qabaq", "bayraq", "budaq", "bulaq", "dayaq", "fındıq",
    "moruq", "muncuq", "muştuluq", "sandıq", "pambıq", "parlaq", "qapaq", "qaçaq",
    "qonaq", "qoçaq", "aşıq", "soraq", "sumaq", "sınaq", "ufaq", "yarlıq", "yarpaq",
    "yaylaq", "yeylaq", "zanbaq", "zambaq", "çıraq", "şadlıq", "şahlıq", "ocaq", "yaraq",
    "tapdıq", "qıvraq",
)

# The street words that end in the 3rd-person possessive -(s)I.
POSSESSIVE_STREET_WORDS = ("küçəsi", "prospekti", "döngəsi", "şossesi", "meydanı",
                           "xiyabanı", "dalanı", "keçidi", "bulvarı", "massivi",
                           "qəsəbəsi", "yolu", "sahəsi")

_LOWER = {"İ": "i", "I": "ı"}
_UPPER = {"i": "İ", "ı": "I"}
_CYRILLIC = re.compile(r"[Ѐ-ӿ]")


class NotInflectable(ValueError):
    """The value cannot take this suffix (abbreviated street, Cyrillic name,
    a case the label does not use)."""


def _low(ch: str) -> str:
    return _LOWER.get(ch, ch.lower())


def _last_vowel(s: str) -> str | None:
    for ch in reversed(s):
        low = _low(ch)
        if low in VOWELS:
            return low
    return None


def _a(prev: str) -> str:
    v = _last_vowel(prev)
    if v is None:
        raise NotInflectable(f"no vowel to harmonise with in {prev!r}")
    return "a" if v in BACK else "ə"


def _i(prev: str) -> str:
    v = _last_vowel(prev)
    if v is None:
        raise NotInflectable(f"no vowel to harmonise with in {prev!r}")
    return {"a": "ı", "ı": "ı", "o": "u", "u": "u", "e": "i", "ə": "i", "i": "i",
            "ö": "ü", "ü": "ü"}[v]


def _ends_vowel(s: str) -> bool:
    return bool(s) and _low(s[-1]) in VOWELS


def _possessive_stem(value: str, label: str | None) -> bool:
    return label == "STREET" and value.split()[-1].lower() in POSSESSIVE_STREET_WORDS


def _soften(stem: str) -> str:
    if stem[-1:] in ("k", "q", "K", "Q") and "".join(map(_low, stem)).endswith(NATIVE_KQ_ENDINGS):
        soft = "y" if stem[-1] in "kK" else "ğ"
        return stem[:-1] + (soft.upper() if stem.isupper() else soft)
    return stem


def _morph(prev: str, morph: str, pronominal: bool) -> str:
    """One morpheme written after `prev` (everything written so far)."""
    out = morph
    if out.startswith("{n}"):
        out = out[3:]
        if pronominal:
            return "n" + _morph(prev + "n", out.replace("(y)", ""), False)
    vowel_final = _ends_vowel(prev)
    for buf in ("(y)", "(n)", "(I)"):
        if out.startswith(buf):
            out = out[len(buf):]
            if vowel_final:
                if buf in ("(y)", "(n)"):
                    out = buf[1] + out
            elif buf == "(I)":
                out = "I" + out
    res = ""
    for ch in out:
        if ch == "A":
            res += _a(prev + res)
        elif ch == "I":
            res += _i(prev + res)
        elif ch == "Q":
            res += "q" if _last_vowel(prev + res) in BACK else "k"
        else:
            res += ch
    return res


def inflect(value: str, case: str, label: str | None = None) -> str:
    """`value` with the suffix chain of `case`.

    `label` decides what is allowed (APPLIES) and the pronominal n after a
    street's possessive. Raises NotInflectable when the value cannot take it.
    """
    if case not in FORMS:
        raise KeyError(f"unknown case {case!r}")
    if label is not None and case not in APPLIES.get(label, ()):
        raise NotInflectable(f"{label} does not take {case}")
    if not value or value != value.strip() or value.endswith(".") or _CYRILLIC.search(value):
        raise NotInflectable(f"cannot inflect {value!r}")
    pronominal = _possessive_stem(value, label)
    out = value
    for morph in FORMS[case]:
        out += _morph(out, morph, pronominal and morph.startswith("{n}"))
    suffix = out[len(value):]
    stem = value
    # k -> y / q -> ğ only before a vowel, and only in native words; the
    # change never alters the harmony, so the suffix stays as written
    if _low(suffix[0]) in VOWELS:
        stem = _soften(value)
    if value.isupper():
        suffix = "".join(_UPPER.get(c, c.upper()) for c in suffix)
    return stem + suffix


def split(inflected: str, value: str) -> int:
    """Where the stem ends in an inflected word (the stem may have softened)."""
    if inflected.startswith(value):
        return len(value)
    soft = _soften(value)
    if inflected.startswith(soft):
        return len(soft)
    raise ValueError(f"{inflected!r} is not an inflection of {value!r}")


def surface(value: str, inflected: str, kind: str) -> str:
    """A variant spelling of the inflected word: `apostrophe` (Bakı'da,
    Turkish orthography; the stem is the name as written) or `folded` (Bakida, Esgerden: no Azerbaijani
    letters, as typed without the keyboard layout)."""
    if kind == "plain":
        return inflected
    if kind == "apostrophe":
        # the apostrophe keeps the name as written: Çiçək'in, not Çiçəy'in
        return value + "'" + inflected[split(inflected, value):]
    if kind == "folded":
        return fold_diacritics(inflected)
    raise KeyError(kind)


# Noisy grammar (2026-10-05): people do not always write the suffix right, and
# a name with a wrong suffix is still the name. Four misspellings real text
# has; each changes only the suffix, never the name:
#   harmony     the other vowel class: Bakıdə, Gəncədan, Məmmədovlərdən
#   buffer      the buffer consonant dropped: Bakıa, Gəncəin, Leylaın
#   double      the suffix's first consonant doubled: Bakıdda, Əsgərrin
#   colloquial  the spoken instrumental -(y)nAn: Leylaynan, Əsgərnən
NOISE_KINDS = ("harmony", "buffer", "double", "colloquial")
_FLIP = str.maketrans("aəıiuüAƏIİUÜ", "əaiıüuƏAİIÜU")


def noisy(value: str, case: str, label: str | None = None) -> dict[str, str]:
    """{kind: word}: misspellings of `inflect(value, case, label)` in the
    suffix only, each different from the correct form. Empty when the value
    takes no suffix for `case`."""
    try:
        word = inflect(value, case, label)
    except NotInflectable:
        return {}
    cut = split(word, value)
    stem, suf = word[:cut], word[cut:]
    upper = value.isupper()
    out: dict[str, str] = {}
    if any(_low(c) in VOWELS for c in suf):
        out["harmony"] = stem + suf.translate(_FLIP)
    if (_ends_vowel(stem) and len(suf) > 1 and _low(suf[0]) in "yn" and _low(suf[1]) in VOWELS
            and not _possessive_stem(value, label)):
        out["buffer"] = stem + suf[1:]
    if suf and _low(suf[0]) not in VOWELS:
        out["double"] = stem + suf[0] + suf
    if case == "ins":
        tail = ("y" if _ends_vowel(stem) else "") + "n" + _a(stem) + "n"
        out["colloquial"] = stem + (tail.upper() if upper else tail)
    return {k: w for k, w in out.items() if w != word}


def table(values: dict[str, list[str]]) -> list[tuple[str, str, str, str]]:
    """(label, value, case, form) for every value and every case it takes:
    the suffix table for the native-speaker check (P4-2)."""
    rows = []
    for label, vals in values.items():
        for v in vals:
            for case in FORMS:
                if case in APPLIES[label]:
                    try:
                        rows.append((label, v, case, inflect(v, case, label)))
                    except NotInflectable:
                        pass
    return rows
