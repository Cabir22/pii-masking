# -*- coding: utf-8 -*-
"""Transliteration functions for cross-language name substitution.

Supports:
  - AZ (Latin) → Cyrillic (for Russian documents)
  - RU (Cyrillic) → Latin (for English/Turkish/Azerbaijani documents)
  - EN (Latin) → Cyrillic (for Russian documents; mostly pass-through)
  - TR (Latin) → Cyrillic (for Russian documents)
"""

from __future__ import annotations
import re
import unicodedata


def _clean(s: str) -> str:
    """Drop the stray combining dot-above that ``İ``/``I``.lower() leaves
    behind (U+0307), then NFC-normalise. Turkish/Azerbaijani dotted-I is the
    only source of a bare U+0307 in this pipeline, so removing it is safe."""
    return unicodedata.normalize("NFC", s.replace("̇", ""))

# ============================================================================
# AZ → CYRILLIC (adapted from scripts/piigen/locales/ru.py)
# ============================================================================

_AZ_CYR_DIGRAPHS = [
    ("ya", "я"), ("yə", "я"), ("yu", "ю"), ("yü", "ю"),
    ("yo", "ё"), ("yö", "ё"), ("ye", "е"),
    ("iy", "ий"), ("əy", "ай"), ("ey", "ей"), ("oy", "ой"), ("uy", "уй"),
]

_AZ_CYR_CHARMAP = {
    "a": "а", "b": "б", "c": "дж", "ç": "ч", "d": "д", "e": "е", "ə": "а",
    "f": "ф", "g": "г", "ğ": "г", "h": "г", "x": "х", "ı": "ы", "i": "и",
    "j": "ж", "k": "к", "q": "г", "l": "л", "m": "м", "n": "н", "o": "о",
    "ö": "ё", "p": "п", "r": "р", "s": "с", "ş": "ш", "t": "т", "u": "у",
    "ü": "ю", "v": "в", "y": "й", "z": "з", "'": "", "`": "",
}

_AZ_CYR_NAME_SUFFIX = [
    (re.compile(r"iyev(a)?$", re.I), lambda m: "иева" if m.group(1) else "иев"),
    (re.compile(r"yev(a)?$", re.I),  lambda m: "ева" if m.group(1) else "ев"),
    (re.compile(r"yov(a)?$", re.I),  lambda m: "ова" if m.group(1) else "ов"),
]

_AZ_CYR_TOKEN_RE = re.compile(r"[A-Za-zƏəÇçĞğIıİiÖöŞşÜü]+|[^A-Za-zƏəÇçĞğIıİiÖöŞşÜü]+")


def _az_cyr_translit_token(tok: str) -> str:
    """Transliterate a single token from Azerbaijani Latin to Cyrillic."""
    low = _clean(tok.lower())
    for pat, repl in _AZ_CYR_NAME_SUFFIX:
        if pat.search(low):
            low = pat.sub(repl, low)
            break
    out: list[str] = []
    i = 0
    while i < len(low):
        for src, dst in _AZ_CYR_DIGRAPHS:
            if low.startswith(src, i):
                out.append(dst)
                i += len(src)
                break
        else:
            ch = low[i]
            out.append(_AZ_CYR_CHARMAP.get(ch, ch))
            i += 1
    res = "".join(out)
    if tok[:1].isupper():
        res = res[:1].upper() + res[1:]
    return _clean(res)


def az_to_cyrillic(text: str) -> str:
    """Azerbaijani-Latin → Russian-Cyrillic, token by token."""
    return "".join(
        _az_cyr_translit_token(m.group()) if m.group()[:1].isalpha() or
        m.group()[:1] in "ƏəÇçĞğIıİiÖöŞşÜü" else m.group()
        for m in _AZ_CYR_TOKEN_RE.finditer(text)
    )


# ============================================================================
# RU → LATIN (GOST 16876-71 variant, commonly used)
# ============================================================================

_RU_LAT_CHARMAP = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
    "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}

_RU_LAT_TOKEN_RE = re.compile(r"[а-яёА-ЯЁ]+|[^а-яёА-ЯЁ]+")


def _ru_lat_translit_token(tok: str) -> str:
    """Transliterate a single Cyrillic token to Latin."""
    low = tok.lower()
    out = []
    for ch in low:
        out.append(_RU_LAT_CHARMAP.get(ch, ch))
    res = "".join(out)
    if tok[:1].isupper():
        res = res[:1].upper() + res[1:]
    return res


def ru_to_latin(text: str) -> str:
    """Russian-Cyrillic → Latin, token by token."""
    return "".join(
        _ru_lat_translit_token(m.group()) if m.group()[:1].isalpha() else m.group()
        for m in _RU_LAT_TOKEN_RE.finditer(text)
    )


# ============================================================================
# EN → CYRILLIC (English→Russian practical transcription, for English names
# landing in a Russian document)
# ============================================================================

# Multi-letter rules, tried longest-first at each position before the single
# -letter map. Covers the digraphs that a letter-by-letter map gets wrong
# ("Smith"→"Смитх", "Jackson"→"Джакксон", "Hutchins"→"Хуткхинс").
_EN_CYR_RULES = [
    ("ght", "т"),
    ("sch", "ш"), ("tch", "ч"), ("dge", "дж"),
    ("sh", "ш"), ("ch", "ч"), ("th", "т"), ("ph", "ф"),
    ("kh", "х"), ("zh", "ж"), ("ck", "к"), ("qu", "кв"),
    ("tz", "ц"), ("wr", "р"), ("kn", "н"),
    ("ce", "се"), ("ci", "си"), ("cy", "си"),
    ("ee", "и"), ("oo", "у"), ("ow", "оу"),
    ("ai", "ай"), ("ay", "ей"), ("ey", "ей"),
    ("oi", "ой"), ("oy", "ой"), ("ou", "у"),
    ("ya", "я"), ("yu", "ю"), ("yo", "ё"),
]

_EN_CYR_CHARMAP = {
    "a": "а", "b": "б", "c": "к", "d": "д", "e": "е", "f": "ф", "g": "г",
    "h": "х", "i": "и", "j": "дж", "k": "к", "l": "л", "m": "м", "n": "н",
    "o": "о", "p": "п", "q": "к", "r": "р", "s": "с", "t": "т", "u": "у",
    "v": "в", "w": "в", "x": "кс", "y": "и", "z": "з",
}

_EN_CYR_DOUBLE_CONS = re.compile(r"([бвгджзйклмнпрстфхцчшщ])\1+")

_EN_CYR_TOKEN_RE = re.compile(r"[A-Za-z]+|[^A-Za-z]+")


def _en_cyr_translit_token(tok: str) -> str:
    """Transliterate a single English token to Cyrillic via practical
    transcription: digraph rules first, then the single-letter map, then
    collapse doubled consonants ("Джакксон" -> "Джаксон")."""
    low = _clean(tok.lower())
    out: list[str] = []
    i = 0
    while i < len(low):
        for src, dst in _EN_CYR_RULES:
            if low.startswith(src, i):
                out.append(dst)
                i += len(src)
                break
        else:
            out.append(_EN_CYR_CHARMAP.get(low[i], low[i]))
            i += 1
    res = _EN_CYR_DOUBLE_CONS.sub(r"\1", "".join(out))
    if tok[:1].isupper() and res:
        res = res[0].upper() + res[1:]
    return _clean(res)


def en_to_cyrillic(text: str) -> str:
    """English-Latin → Cyrillic, phonetic-style, token by token."""
    return "".join(
        _en_cyr_translit_token(m.group()) if m.group()[:1].isalpha() else m.group()
        for m in _EN_CYR_TOKEN_RE.finditer(text)
    )


# ============================================================================
# TR → CYRILLIC (Turkish-specific, for Turkish names in Russian)
# ============================================================================

_TR_CYR_DIGRAPHS = [
    ("ya", "я"), ("yə", "я"), ("yu", "ю"), ("yü", "ю"),
    ("yo", "ё"), ("yö", "ё"), ("ye", "е"),
    ("iy", "ий"), ("əy", "ай"), ("ey", "ей"), ("oy", "ой"), ("uy", "уй"),
]

_TR_CYR_CHARMAP = {
    "a": "а", "b": "б", "c": "дж", "ç": "ч", "d": "д", "e": "е", "ə": "а",
    "f": "ф", "g": "г", "ğ": "г", "h": "г", "x": "х", "ı": "ы", "i": "и",
    "j": "ж", "k": "к", "q": "г", "l": "л", "m": "м", "n": "н", "o": "о",
    "ö": "ё", "p": "п", "r": "р", "s": "с", "ş": "ш", "t": "т", "u": "у",
    "ü": "ю", "v": "в", "y": "й", "z": "з", "'": "", "`": "",
}

_TR_CYR_TOKEN_RE = re.compile(r"[A-Za-zƏəÇçĞğIıİiÖöŞşÜü]+|[^A-Za-zƏəÇçĞğIıİiÖöŞşÜü]+")


def _tr_cyr_translit_token(tok: str) -> str:
    """Transliterate a single Turkish token to Cyrillic."""
    low = _clean(tok.lower())
    out: list[str] = []
    i = 0
    while i < len(low):
        for src, dst in _TR_CYR_DIGRAPHS:
            if low.startswith(src, i):
                out.append(dst)
                i += len(src)
                break
        else:
            ch = low[i]
            out.append(_TR_CYR_CHARMAP.get(ch, ch))
            i += 1
    res = "".join(out)
    if tok[:1].isupper():
        res = res[:1].upper() + res[1:]
    return _clean(res)


def tr_to_cyrillic(text: str) -> str:
    """Turkish-Latin → Cyrillic, token by token."""
    return "".join(
        _tr_cyr_translit_token(m.group()) if m.group()[:1].isalpha() or
        m.group()[:1] in "ƏəÇçĞğIıİiÖöŞşÜü" else m.group()
        for m in _TR_CYR_TOKEN_RE.finditer(text)
    )


# ============================================================================
# AZ → LATIN (simple ASCII pass-through, mostly for symmetry)
# ============================================================================

def az_to_latin(text: str) -> str:
    """Azerbaijani is already Latin-script; return as-is."""
    return text


# ============================================================================
# Dispatcher
# ============================================================================

TRANSLITERATORS = {
    ("az", "latin"): az_to_latin,
    ("az", "cyrillic"): az_to_cyrillic,
    ("en", "latin"): lambda x: x,  # English is already Latin
    ("en", "cyrillic"): en_to_cyrillic,
    ("ru", "latin"): ru_to_latin,
    ("ru", "cyrillic"): lambda x: x,  # Russian is already Cyrillic
    ("tr", "latin"): lambda x: x,  # Turkish is already Latin
    ("tr", "cyrillic"): tr_to_cyrillic,
}


def transliterate(text: str, from_lang: str, to_script: str) -> str:
    """Transliterate text from one language to a target script.

    Args:
        text: Text to transliterate
        from_lang: Source language code ('az', 'en', 'ru', 'tr')
        to_script: Target script ('latin' or 'cyrillic')

    Returns:
        Transliterated text, or original if no conversion needed
    """
    fn = TRANSLITERATORS.get((from_lang.lower(), to_script.lower()))
    return fn(text) if fn else text
