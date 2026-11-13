"""Context-anchor rules for the `anchor_required` detection tier.

`data/schema.md` defines five labels whose values carry no standalone signal:

    AGE  BUILDINGNUM  CARD_SECURITY_CODE  DATE  TIME

A bare "34" is only an AGE because something nearby says so. The audit found
`DETECTION_TIERS` declared this tier but nothing in the codebase enforced it --
a repository-wide search found `DETECTION_TIERS` referenced only to derive
`STRUCTURED_LABELS`. Measured consequences in the 28,560-record corpus:

    CARD_SECURITY_CODE   401/1,487  (26.97%)  no CVV anchor within +/-90 chars
    TIME                 715/3,046  (23.47%)
    AGE                  412/3,683  (11.19%)
    DATE                 348/5,406  ( 6.44%)
    BUILDINGNUM          228/4,477  ( 5.09%)

Two mechanisms live here because they answer the same question -- "does the
context identify this value?" -- from opposite directions:

  * `has_anchor`  -- is there a licensing word nearby?
  * `is_structural_position` -- is this digit actually document furniture
    (a heading number, a list marker, "Qrup 2") rather than prose?

`resolve_claims` consults both before it will label a value shorter than
`MIN_UNANCHORED_LEN`, which is what stops a planned `AGE=3` from also tagging
the `3` in `### 3. Kritik Ssenari` (32 confirmed documents in the audit).

Design notes
------------
Anchor lists are deliberately generous rather than minimal. The audit's
figures above came from a conservative proxy list and were explicitly stated
as upper bounds on genuine ambiguity, not confirmed errors -- so tightening
here would reject natural Azerbaijani. Both pre- and post-position are
checked because Azerbaijani puts the licensing word on either side:
"yasi 34" (before) and "34 yasindadir" (after) are equally normal.

Diacritic-stripped spellings are listed alongside the correct ones because
the `strip_diacritics` noise kind deliberately produces them, and a noised
document must not fail a gate the un-noised one passes.
"""

from __future__ import annotations

import re

# How far from the value a licensing word may sit. 80 characters is roughly a
# long clause either side -- wide enough for "Musterinin dogum tarixi, senedde
# gosterildiyi kimi, 12.03.1990-dir" and narrow enough that an unrelated
# "yas" two sentences away does not license a random number.
DEFAULT_WINDOW = 80

# Values at or above this length carry enough shape to be resolved on their
# own. Below it, an anchor is required. Three is the same threshold
# `complete_occurrences` has always used; the audit found `resolve_claims`
# lacked it, and that asymmetry was the bug.
MIN_UNANCHORED_LEN = 3


def _words(*variants: str) -> str:
    """Alternation that matches each variant as a whole word or word-prefix.

    Azerbaijani is agglutinative: "yas" is followed by any of -i, -inda,
    -indadir, -li, -lariyla. So a stem must match as a prefix of a longer
    word, but must NOT match inside one (the "ev" in "verilmisdir").
    """
    return r"(?<![\w])(?:" + "|".join(variants) + r")"


ANCHOR_REQUIRED: dict[str, re.Pattern] = {
    # yas / yasi / yasinda / yasindadir / yasli / yaslarinda, plus birth verbs
    # that license an age in the same clause.
    "AGE": re.compile(
        _words("yaş", "yas", "yaşlı", "yasli", "yaşın", "yasin", "yaşı", "yasi",
               "anadan", "doğul", "dogul", "təvəllüd", "tevellud", "sinni")
        + r"\w*", re.IGNORECASE),

    # Street/building furniture. "ev" and "bina" are the core; the street-type
    # words are included because "Nizami kucesi 84" is a complete address with
    # no separate "bina".
    "BUILDINGNUM": re.compile(
        _words("bina", "ev", "mənzil", "menzil", "küçə", "kuce", "kücə",
               "prospekt", "döngə", "donge", "blok", "korpus", "ünvan", "unvan",
               "məhəllə", "mehelle", "qəsəbə", "qesebe", "yaşayış", "yasayis",
               "mkr", "microrayon", "mikrorayon")
        + r"\w*", re.IGNORECASE),

    # CVV/CVC only. Deliberately narrow: a 3-digit number next to a generic
    # word like "kod" is not reliably a card security code, and this label
    # had the highest unanchored rate in the audit precisely because the
    # model was writing bare 3-digit numbers.
    "CARD_SECURITY_CODE": re.compile(
        _words("cvv", "cvc", "cvv2", "təhlükəsizlik", "tehlukesizlik")
        + r"\w*|kart\w*\s+kod\w*", re.IGNORECASE),

    "DATE": re.compile(
        _words("tarix", "doğum", "dogum", "anadan", "təvəllüd", "tevellud",
               "imzalan", "bağlan", "baglan", "sənədləş", "senedles",
               "qeydiyyat", "etibarlı", "etibarli", "bitmə", "bitme",
               "verilmə", "verilme", "il", "ilin", "tarixi")
        + r"\w*", re.IGNORECASE),

    "TIME": re.compile(
        _words("saat", "vaxt", "zaman", "vaxtı", "vaxti", "başla", "basla",
               "bitir", "görüş", "gorus", "qeydə", "qeyde", "time")
        + r"\w*", re.IGNORECASE),
}

# Formats that identify themselves. A value matching one of these needs no
# lexical anchor: "12.03.1990" is a date wherever it appears, and rejecting it
# for lack of a nearby "tarix" would throw away correct annotations. This is
# the "carefully justified format-aware handling" the tier allows -- scoped to
# DATE and TIME, and to shapes that carry a 4-digit year plus either a
# month word or two separators, which no ordinary quantity does.
#
# The worded branch covers, in one expression: day-first ("12 March 1990"),
# month-first ("March 12, 1990"), abbreviations, ordinals ("21st", "the 21st
# of March"), and an optional leading OR trailing weekday (1-2 words, for
# Azerbaijani "cümə axşamı") -- i.e. every shape az.date() and en.date() can
# emit EXCEPT the bare "5 fevral 1992-ci il" style, which stays
# anchor-required exactly as it was before weekday support was added.
_WD = r"[^\d\s,]+(?:\s+[^\d\s,]+)?"          # weekday, 1-2 words
_MON = r"[^\d\s,.]+\.?"                       # month name or abbr ("Feb.")
_DAY = r"\d{1,2}(?:st|nd|rd|th)?"
SELF_SIGNALLING: dict[str, re.Pattern] = {
    "DATE": re.compile(
        r"^(?:"
        r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}"                       # 12.03.1990
        r"|\d{4}-\d{2}-\d{2}"                                    # 1990-03-12
        r"|(?:" + _WD + r",\s+)?"                                # [Friday, ]
        r"(?:the\s+)?"
        r"(?:"
        + _DAY + r"\s+(?:of\s+)?" + _MON + r",?\s+\d{4}"         # 21[st] [of] March[,] 1990
        + r"|" + _MON + r"\s+" + _DAY + r",?\s+\d{4}"            # March 21[,] 1990
        + r")"
        r"(?:,\s+" + _WD + r")?"                                 # [, Friday]
        r")$",
        re.IGNORECASE),
    "TIME": re.compile(r"^\d{1,2}[:.]\d{2}(?:[:.]\d{2})?(?:\s?[AaPp][Mm])?$"),
}

# --- structural-number detection -------------------------------------------
# A digit in one of these positions is document furniture, never PII. Each
# pattern matches the text immediately BEFORE the value.
_STRUCTURAL_BEFORE = [
    ("md_heading",   re.compile(r"(?:^|\n)[ \t]*#{1,6}[ \t]*$")),
    ("bold_head",    re.compile(r"(?:^|\n)[ \t]*\*\*[ \t]*$")),
    ("list_marker",  re.compile(r"(?:^|\n)[ \t]*[-*+][ \t]+$")),
    ("line_start",   re.compile(r"(?:^|\n)[ \t]*$")),
    ("group_word",   re.compile(
        r"(?:Qrup|Bənd|Bend|Addım|Addim|Mərhələ|Merhele|Bölmə|Bolme|Fəsil|"
        r"Fesil|Maddə|Madde|Cədvəl|Cedvel|Şəkil|Sekil|Səhifə|Sehife|Versiya|"
        r"Sinif|Kurs|Səviyyə|Seviyye|Variant|Nümunə|Numune|Sual|Punkt|Nöqtə|"
        r"Noqte|Hissə|Hisse|Paraqraf|Abzas)[ \t]+$", re.IGNORECASE)),
]

# After a heading/list number: ". " or ") ". Required for the positional
# patterns (a line may legitimately start with an age) but not for
# `group_word`, where the preceding word already settles it.
_STRUCTURAL_AFTER = re.compile(r"^[ \t]*[.)](?:\s|$)")
_POSITIONAL = {"md_heading", "bold_head", "list_marker", "line_start"}


# Longest digit run that can plausibly be document furniture. Headings and
# list markers run "1." to "999."; nothing numbers its sections in the
# thousands, let alone the quintillions.
#
# Without this bound the positional patterns misfire on any long digit string
# that happens to start a line and end in a period -- found by the corpus
# validator on a real record, where a 20-digit ICCID written on its own line
# ("89994198779617092365.") was classified as a list marker and its span
# dropped. Structural numbers are short by nature; long ones are data.
MAX_STRUCTURAL_DIGITS = 3


def structural_kind(text: str, start: int, end: int) -> str | None:
    """Name the structural role of the digit at [start:end), or None.

    Returns the matched pattern name so a rejection can carry an explainable
    reason code rather than a bare boolean.
    """
    value = text[start:end]
    if not value.isdigit():
        return None
    if len(value) > MAX_STRUCTURAL_DIGITS:
        return None
    before = text[:start]
    after = text[end:]
    for name, pat in _STRUCTURAL_BEFORE:
        if not pat.search(before):
            continue
        if name in _POSITIONAL and not _STRUCTURAL_AFTER.match(after):
            continue
        return name
    return None


def is_structural_position(text: str, start: int, end: int) -> bool:
    return structural_kind(text, start, end) is not None


def has_anchor(label: str, text: str, start: int, end: int,
               window: int = DEFAULT_WINDOW) -> bool:
    """True if `label` is licensed by context around [start:end).

    Labels outside the anchor_required tier are always licensed -- their
    values carry their own signal (a checksum, a pattern, a curated pool).
    """
    pattern = ANCHOR_REQUIRED.get(label)
    if pattern is None:
        return True

    value = text[start:end]
    self_sig = SELF_SIGNALLING.get(label)
    if self_sig is not None and self_sig.match(value):
        return True

    # A structural number is never licensed, even if an anchor word happens
    # to sit within the window -- "Bolme 3" inside a document about ages.
    if is_structural_position(text, start, end):
        return False

    left = text[max(0, start - window):start]
    right = text[end:end + window]
    return bool(pattern.search(left) or pattern.search(right))


def anchor_failures(text: str, entities: list[dict],
                    window: int = DEFAULT_WINDOW) -> list[dict]:
    """Every entity whose label requires an anchor and does not have one.

    Returns the offending entity dicts so the caller can drop just those
    spans and keep the document when other valid positives remain.
    """
    out = []
    for e in entities:
        label = e.get("label", "")
        if label not in ANCHOR_REQUIRED:
            continue
        if not has_anchor(label, text, e["start"], e["end"], window):
            out.append(e)
    return out


def resolvable_unanchored(label: str, value: str) -> bool:
    """May this value be located globally without checking its context?

    Long values are self-identifying by sheer improbability of collision. A
    one- or two-character value is not: it collides with heading numbers,
    list markers and ordinary quantities throughout the document.
    """
    return len(value) >= MIN_UNANCHORED_LEN
