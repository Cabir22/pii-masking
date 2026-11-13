"""English licensing words for the `anchor_required` tier.

`scripts/piigen/anchors.py` is the Azerbaijani original and the contract this
mirrors. Five labels carry no standalone signal -- a bare "34" is only an AGE
because something nearby says so -- and are only valid if a licensing word
sits within +/-80 characters.

That file is entirely Azerbaijani-keyed. Wahoo will happily translate
"doğum tarixi" into "date of birth", but the Azerbaijani validator will not
recognise the result, so every DATE/TIME/AGE/BUILDINGNUM/CARD_SECURITY_CODE
in a translated document would silently fail validation. Hence this port.

**This is the single highest-risk file in a language pack.** An incomplete
list does not error -- it quietly invalidates five labels across an entire
run. Turkish and Russian need the same treatment (`anchors_tr.py`,
`anchors_ru.py`); copy the structure, not the words.

Two properties carried over from the Azerbaijani file deliberately:
  * both pre- and post-position are checked -- "aged 34" and "34 years old"
    are equally normal, and English puts the licensing word on either side;
  * lists are generous rather than minimal. The audit that motivated the
    original was explicit that its figures were upper bounds on genuine
    ambiguity, not confirmed errors, so tightening here rejects natural text.

English needs no diacritic-stripped variants (the noise injector's
`strip_diacritics` is a no-op on ASCII), which is the one place this port is
simpler than the original.
"""
from __future__ import annotations

import re

# Same window and threshold as the Azerbaijani original -- these are
# properties of the task, not of the language.
from piigen.anchors import DEFAULT_WINDOW, MIN_UNANCHORED_LEN  # noqa: F401
from piigen.anchors import SELF_SIGNALLING, is_structural_position


def _words(*variants: str) -> str:
    """Alternation matching each variant as a whole word or word-prefix.

    English is not agglutinative, but it does inflect ("sign" -> "signed",
    "expire" -> "expires"/"expiry"), so a stem still has to match as a prefix
    -- while never matching inside an unrelated word.
    """
    return r"(?<![\w])(?:" + "|".join(variants) + r")"


ANCHOR_REQUIRED: dict[str, re.Pattern] = {
    # age / aged / ages / aging, plus birth verbs that license an age in the
    # same clause. "y/o" and "yrs" are the common abbreviations.
    "AGE": re.compile(
        _words("age", "aged", "ages", "aging", "ageing", "year", "years",
               "yr", "yrs", "y/o", "yo", "born", "birth", "dob", "old",
               "elderly", "senior", "pensioner", "retiree", "minor",
               "teenager", "adult", "infant", "toddler", "octogenarian",
               "nonagenarian")
        + r"\w*", re.IGNORECASE),

    # Street/building furniture. "apt"/"flat"/"unit"/"suite" are the core;
    # street-type words are included because "84 Nizami Street" is a complete
    # address with no separate "building".
    "BUILDINGNUM": re.compile(
        _words("apartment", "apt", "flat", "unit", "suite", "ste", "building",
               "bldg", "block", "house", "no", "number", "street", "st",
               "avenue", "ave", "road", "rd", "lane", "ln", "drive", "dr",
               "boulevard", "blvd", "court", "ct", "place", "plaza", "square",
               "floor", "fl", "address", "addr", "residence", "premises")
        + r"\w*|#", re.IGNORECASE),

    # CVV/CVC, plus "security/verification code" and its underscored form
    # (security_code: in a YAML block) and "security credentials". Still
    # deliberately narrow -- a bare "code" next to a 3-digit number is not
    # licensed, which is why this label had the highest unanchored rate in
    # the original audit. NOT licensed: a plain "login code" / "access
    # code" -- those translate faithfully from Azerbaijani login-code labels
    # that the taxonomy arguably shouldn't have tagged as CARD_SECURITY_CODE
    # in the first place, and over-licensing here would hide that.
    "CARD_SECURITY_CODE": re.compile(
        _words("cvv", "cvc", "cvv2", "cvc2", "cid", "csc") + r"\w*"
        + r"|" + _words("security", "verification")
        + r"[_\s]+(?:code|codes|value|number|digit)"
        + r"|" + _words("security") + r"[_\s]+credential"
        + r"|card[_\s]+(?:security[_\s]+)?code", re.IGNORECASE),

    "DATE": re.compile(
        _words("date", "dated", "dating", "born", "birth", "dob", "birthday",
               "signed", "signature", "issued", "issue", "expire", "expires",
               "expiry", "expiration", "valid", "effective", "commencing",
               "commenced", "registered", "registration", "filed", "logged",
               "recorded", "occurred", "on", "since", "until", "till",
               "deadline", "due", "as\\s+of", "renewal", "renewed")
        + r"\w*", re.IGNORECASE),

    "TIME": re.compile(
        _words("time", "times", "at", "hour", "hours", "hr", "hrs", "clock",
               "oclock", "am", "pm", "scheduled", "schedule", "starts",
               "start", "starting", "begins", "begin", "ends", "end",
               "ending", "arrives", "arrival", "departs", "departure",
               "opens", "opening", "closes", "closing", "appointment",
               "meeting", "shift", "deadline", "logged", "timestamp")
        + r"\w*", re.IGNORECASE),
}


def has_anchor(label: str, text: str, start: int, end: int,
               window: int = DEFAULT_WINDOW) -> bool:
    """True if `label` is licensed by the English context around [start:end).

    Identical logic to `piigen.anchors.has_anchor`, against the English word
    lists. `SELF_SIGNALLING` and `is_structural_position` are reused
    unchanged -- a date's *shape* and a heading number's *position* are
    language-independent facts, and the SELF_SIGNALLING patterns were
    already widened to cover the month-first and ordinal forms English
    produces (see that module).
    """
    pattern = ANCHOR_REQUIRED.get(label)
    if pattern is None:
        return True

    value = text[start:end]
    self_sig = SELF_SIGNALLING.get(label)
    if self_sig is not None and self_sig.match(value):
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
