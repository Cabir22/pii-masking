"""Turkish carrier pack.

WORK IN PROGRESS -- only the calendar layer is populated, matching `en.py`'s
own shape exactly. Under the translation approach (
2026-09-03 entry) an EN/TR/RU pack is *not* a full locale: the PII stays
Azerbaijani and is spliced from the shared `az` pools, so this pack only
overrides the language-facing pieces -- months, weekday names and the date
format repertoire. Identity/geography/phone/ID fields borrow `az`'s so the
`Locale` is constructible and `LOCALES["tr"].date_builder` resolves; they
are not meant to be sampled from directly.

`TIME` needs no locale work at all: `ValueFactory.time_of_day()`
(`scripts/piigen/values.py`, around line 461) ignores `lang` entirely and
always emits a plain `HH:MM` (or, 15% of the time, `H:MM AM/PM`) -- confirmed
by reading it, not assumed. Nothing to override here.

Date repertoire is day-first throughout, unlike `en.py`'s mixed US/international
spread -- Turkish does not use month-first dates, so those forms are dropped
rather than reweighted. `"21. Şubat 1956"` (a trailing period as an ordinal
marker) is genuine, standard Turkish numeral-ordinal notation -- the same
convention as `"3. kat"` (3rd floor) -- given a modest share since it's more
at home marking a rank/position than a calendar date, but it is correct
Turkish, not invented.
"""

from __future__ import annotations

import random
from datetime import date as _date

from .base import Locale
from . import az

MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
          "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
MONTHS_ABBR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu",
               "Eyl", "Eki", "Kas", "Ara"]
WEEKDAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma",
            "Cumartesi", "Pazar"]


def date(day: int, month: int, year: int, rng: random.Random) -> str:
    mf, ma, yy = MONTHS[month - 1], MONTHS_ABBR[month - 1], str(year)[2:]
    style = rng.random()
    # --- worded, day-first (the only order Turkish uses) -----------------
    if style < 0.24:
        return f"{day} {mf} {year}"                       # 21 Şubat 1956
    if style < 0.34:
        return f"{day} {ma} {year}"                        # 21 Şub 1956
    if style < 0.40:
        # D-56c (9), the team: `21. Şubat 1956` is not a Turkish date form (the
        # dot makes an ordinal: `21. yüzyıl`); the share goes to the plain form
        return f"{day} {mf} {year}"                         # 21 Şubat 1956
    # --- numeric ----------------------------------------------------------
    if style < 0.58:
        return f"{day:02d}.{month:02d}.{year}"              # 21.02.1956
    if style < 0.72:
        return f"{day:02d}/{month:02d}/{year}"              # 21/02/1956
    if style < 0.80:
        return f"{day:02d}.{month:02d}.{yy}"                # 21.02.56
    if style < 0.88:
        return f"{year}-{month:02d}-{day:02d}"              # 1956-02-21
    # D-54d: a weekday is outside the DATE span in every language, like
    # `-cı il` and `года`: DATE is the calendar date only. This branch used to
    # return `{wd}, {date}` / `{date}, {wd}`; it keeps its share and its rng
    # draw (so no other value in a build moves) and returns the worded date.
    # A writer that wants the weekday puts weekday() beside the span.
    rng.random()
    return f"{day} {mf} {year}"                             # (Pazartesi,) 21 Şubat 1956


def weekday(day: int, month: int, year: int) -> str:
    """The weekday of a real calendar date, for a writer that puts it next to
    a DATE span, outside it (D-54d): `{wd}, ⟦date⟧` or `⟦date⟧, {wd}`."""
    return WEEKDAYS[_date(year, month, day).weekday()]


LOCALE = Locale(
    code="tr", name="Turkish",
    # Borrowed from `az` -- see module docstring. Not for direct sampling.
    first_names_m=az.FIRST_M, first_names_f=az.FIRST_F,
    surname_stems=az.SURNAME_STEMS, surname_builder=az.surname,
    months=MONTHS, weekdays=WEEKDAYS, date_builder=date,
    distinctive_chars="",
)
