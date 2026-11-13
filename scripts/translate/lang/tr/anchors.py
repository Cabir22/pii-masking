"""Turkish licensing words for the `anchor_required` tier.

`scripts/piigen/anchors.py` is the Azerbaijani original and the contract this
mirrors (see `anchors_en.py`, the closer template: same data shapes, same
window logic, same function names). Five labels carry no standalone signal --
a bare "34" is only an AGE because something nearby says so -- and are only
valid if a licensing word sits within +/-80 characters.

That file is entirely Azerbaijani-keyed. Wahoo will happily translate
"doğum tarixi" into "doğum tarihi", and the Azerbaijani validator will not
recognise the result, so every DATE/TIME/AGE/BUILDINGNUM/CARD_SECURITY_CODE
in a translated document would silently fail validation. Hence this port.

**This is the single highest-risk file in a language pack.** An incomplete
list does not error -- it quietly invalidates five labels across an entire
run. Russian needs the same treatment (`anchors_ru.py`); copy the structure,
not the words.

Two properties carried over from the Azerbaijani file deliberately:
  * both pre- and post-position are checked -- "34 yaşında" (after) and
    "yaşı 34" (before) are equally normal, and Turkish puts the licensing
    word on either side, same as Azerbaijani and English;
  * lists are generous rather than minimal, matching `anchors_en.py`'s own
    stance -- tightening here rejects natural text.

Diacritic-stripped spellings (`doğum` -> `dogum`, `güvenlik` -> `guvenlik`)
are added alongside the correct ones, because the noise injector's
`strip_diacritics` kind deliberately produces them and a noised document
must not fail a gate its clean twin passes -- same reasoning as the
Azerbaijani original, and the same technique `piigen/validate.py`'s
`_tr_pattern()` already uses for the reverse (Turkish-contamination) check:
derive the stripped form from the correct one via `fold_diacritics()`
rather than hand-typing both and risking the two drifting apart.

Case-folding note (this is a DIFFERENT problem from diacritic stripping,
and handled differently): Turkish's dotted/dotless pair (İ/I, i/ı) does not
fold correctly under a naive `.lower()`/`.upper()` call --
`"İ".lower() == "i̇"` (two characters, `i` + a combining dot above), which
would silently fail a plain string-equality check against `"i"`. This
module does not use `.lower()`/`.upper()` at all; it relies on `re`'s own
IGNORECASE matching, which was verified directly (not assumed) to unify
`i`/`I`/`ı`/`İ` correctly for pattern matching in this interpreter
(CPython 3.11.16): a bare `imza` IGNORECASE pattern matches all of `imza`,
`Imza`, `İMZA`, and a dotless-i pattern (`ımza`) matches all of `imza`,
`Imza`, `İMZA` too. So ALL-CAPS Turkish form labels (`DOĞUM TARİHİ:`,
`İMZA:`) are covered by plain `re.IGNORECASE`, same as `anchors_en.py`'s
ALL-CAPS coverage -- no custom casefold needed.
"""

from __future__ import annotations

import re

# Same window and threshold as the Azerbaijani original -- these are
# properties of the task, not of the language.
from piigen.anchors import DEFAULT_WINDOW, MIN_UNANCHORED_LEN  # noqa: F401
from piigen.anchors import SELF_SIGNALLING, is_structural_position
from piigen.locales import tr as _tr_locale
from piigen.text import fold_diacritics

# The Turkish ordinal-dot date, `21. Şubat 1956` (locales/tr.py date(), 6% of
# its dates). The shared worded-date shape (piigen.anchors SELF_SIGNALLING)
# takes `21`, `21st` and `March 21` but not a day with a dot, so a bare
# `21. Şubat 1956` with no `tarih`-type word nearby failed the anchor check:
# 321 of 5,000 Turkish dates (19 Oct). Only a real Turkish month name (or its
# abbreviation, with or without diacritics) qualifies, so `3. sınıf 2019`
# does not.
_TR_MONTHS = sorted({m for m in _tr_locale.MONTHS + _tr_locale.MONTHS_ABBR}
                    | {fold_diacritics(m) for m in _tr_locale.MONTHS + _tr_locale.MONTHS_ABBR}, key=len, reverse=True)
_TR_DOT_DATE = re.compile(
    r"^(?:[^\d\s,]+,\s+)?"                                  # optional weekday
    r"\d{1,2}\.\s+(?:" + "|".join(map(re.escape, _TR_MONTHS)) + r")\.?\s+\d{4}"
    r"(?:,\s+[^\d\s,]+)?$", re.IGNORECASE)


def _words(*variants: str) -> str:
    """Alternation matching each variant as a whole word or word-prefix.

    Turkish is agglutinative, like Azerbaijani: "yaş" is followed by any of
    -ında, -ındaki, -ını, -lı, -ı. So a stem must match as a prefix of a
    longer word, but must NOT match inside one (the "im" in "iyimser" must
    not satisfy an "imza" anchor).
    """
    return r"(?<![\w])(?:" + "|".join(variants) + r")"


def _with_stripped(*terms: str) -> tuple[str, ...]:
    """Each term plus its `fold_diacritics()` form, deduplicated and in a
    stable order. A term with no Turkish-specific letters (e.g. "tarih")
    folds to itself and is not duplicated.
    """
    seen: dict[str, None] = {}
    for term in terms:
        seen.setdefault(term, None)
        seen.setdefault(fold_diacritics(term), None)
    return tuple(seen)


ANCHOR_REQUIRED: dict[str, re.Pattern] = {
    # yaş / yaşında / yaşındaki / yaşını / yaşlı / y., plus birth phrasing
    # that licenses an age in the same clause (medical notes, forms).
    "AGE": re.compile(
        _words(*_with_stripped(
            "yaş", "yaşında", "yaşındaki", "yaşını", "yaşlı", "yaşı", "y.",
            "doğdu", "doğumlu", "doğum tarihli", "doğum yılı",
        )) + r"\w*", re.IGNORECASE),

    # Street/building furniture. "no"/"nu"/"numara" are the core (rental
    # contracts, delivery addresses); "daire"/"bina"/"blok"/"kat"/"apt" cover
    # apartment-style addresses, which are the norm in Turkish urban
    # addressing ("... Sok. No: 5 Daire: 3 Kat: 2").
    "BUILDINGNUM": re.compile(
        _words(*_with_stripped(
            "no", "no.", "nu.", "numara", "numarası", "daire", "d.", "bina",
            "blok", "kat", "apt.", "apartman", "site", "mahalle", "sokak",
            "cadde", "adres", "kapı")) + r"\w*|#", re.IGNORECASE),

    # CVV/CVC/CVV2/CVC2 (bare form, common on bank SMS), or a
    # "güvenlik/doğrulama" + flexible joiner (space, underscore -- config/
    # log style) + "kod/numara/değer" phrase, or the fuller "kart güvenlik
    # kodu" form. Deliberately NOT a bare "kod" stem -- matching
    # `anchors_en.py`/the Azerbaijani original's own reasoning, a 3-digit
    # number next to a generic word like "kod" (order code, ticket code) is
    # not reliably a card security code.
    # "emniyet" alongside "güvenlik": both translate Azerbaijani
    # "təhlükəsizlik" (security/safety), same class of gap as the
    # EN-side "safety code" vs "security code" finding (2026-09-05,
    # still unfixed on anchors_en itself) -- "emniyet kodu" is a real,
    # if less common, Turkish phrasing for the same field.
    "CARD_SECURITY_CODE": re.compile(
        _words("cvv2?", "cvc2?") + r"\w*"
        + r"|" + _words(*_with_stripped("güvenlik", "emniyet", "doğrulama"))
        + r"[_\s]+(?:kod\w*|numara\w*|değer\w*|deger\w*)"
        + r"|" + _words(*_with_stripped("kart"))
        + r"[_\s]+(?:" + _words(*_with_stripped("güvenlik", "emniyet", "doğrulama"))
        + r"[_\s]+)?kod\w*", re.IGNORECASE),

    # Date phrasing across registers: contracts (düzenlenme/geçerlilik/
    # yürürlük/fesih tarihi), bank statements (işlem/valör/vade tarihi),
    # medical notes (muayene/teşhis/ameliyat tarihi), logistics/support
    # tickets (kayıt/oluşturulma/teslim/randevu tarihi), plus the bare
    # "tarih"/"doğum"/"imza" stems that catch the rest via suffix matching.
    "DATE": re.compile(
        _words(*_with_stripped(
            "tarih", "tarihi", "tarihli", "doğum tarihi", "d. tarihi",
            "düzenlenme tarihi", "geçerlilik tarihi", "son kullanma tarihi",
            "veriliş tarihi", "yayın tarihi", "imza tarihi", "tanzim tarihi",
            "yürürlük tarihi", "yürürlüğe giriş tarihi", "başlama tarihi",
            "bitiş tarihi", "fesih tarihi", "sözleşme tarihi",
            "işlem tarihi", "valör tarihi", "vade tarihi", "kayıt tarihi",
            "oluşturulma tarihi", "güncelleme tarihi", "muayene tarihi",
            "teşhis tarihi", "ameliyat tarihi", "randevu tarihi",
            "teslim tarihi", "sevkiyat tarihi", "son ödeme tarihi",
            "itibaren", "geçerli", "doğum", "imza",
        )) + r"\w*", re.IGNORECASE),

    # Time phrasing: appointments/support (randevu/görüşme/toplantı saati),
    # logistics (varış/kalkış), operating hours (açılış/kapanış), plus the
    # bare "saat"/"vakit"/"zaman" stems.
    "TIME": re.compile(
        _words(*_with_stripped(
            "saat", "saatinde", "saati", "başlangıç", "bitiş", "açılış",
            "kapanış", "varış", "kalkış", "randevu", "itibariyle", "vakti",
            "vakit", "zaman", "toplantı saati", "görüşme saati", "seans",
            "mesai saati", "çalışma saati",
        )) + r"\w*", re.IGNORECASE),
}


def has_anchor(label: str, text: str, start: int, end: int,
               window: int = DEFAULT_WINDOW) -> bool:
    """True if `label` is licensed by the Turkish context around [start:end).

    Identical logic to `piigen.anchors.has_anchor`, against the Turkish word
    lists. `SELF_SIGNALLING` and `is_structural_position` are reused
    unchanged -- a date's *shape* and a heading number's *position* are
    language-independent facts; `SELF_SIGNALLING["DATE"]`'s worded-month
    branch (`_MON = r"[^\\d\\s,.]+\\.?"`) already matches any non-numeric
    month word, Turkish included, without modification.
    """
    pattern = ANCHOR_REQUIRED.get(label)
    if pattern is None:
        return True

    value = text[start:end]
    self_sig = SELF_SIGNALLING.get(label)
    if self_sig is not None and self_sig.match(value):
        return True
    if label == "DATE" and _TR_DOT_DATE.match(value):
        return True

    if is_structural_position(text, start, end):
        return False

    left = text[max(0, start - window):start]
    right = text[end:end + window]
    return bool(pattern.search(left) or pattern.search(right))


def anchor_failures(text: str, entities: list[dict],
                    window: int = DEFAULT_WINDOW) -> list[dict]:
    """Every entity whose label requires an anchor and does not have one."""
    return [e for e in entities
            if e.get("label", "") in ANCHOR_REQUIRED
            and not has_anchor(e["label"], text, e["start"], e["end"], window)]
