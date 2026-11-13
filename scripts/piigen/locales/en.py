"""English carrier pack.

WORK IN PROGRESS -- only the calendar layer is populated. Under the
translation approach (2026-09-03 entry) an EN/TR/RU pack is
*not* a full locale: the PII stays Azerbaijani and is spliced from the shared
`az` pools, so this pack only overrides the language-facing pieces -- months,
weekday names and the date format repertoire. Identity/geography/phone/ID
fields borrow `az`'s so the `Locale` is constructible and
`LOCALES["en"].date_builder` resolves; they are not meant to be sampled from
directly.

Still to add before the English pack is complete: `render_value()` (diacritic
folding), the city exonym table, phrase banks, `expected_scripts`, and
`anchors_en.py`.

Date repertoire deliberately spans US, international and ISO conventions --
Azerbaijani-context English business text mixes all three. Day/month order
varies on purpose; the model only labels the span as DATE, it never has to
resolve which number is the day, so an ambiguous `03/04/1972` is not a
problem. `MM.DD.YYYY` (month-first with dots) is omitted -- almost nobody
writes it deliberately.
"""

from __future__ import annotations

import random
from datetime import date as _date

from .base import Locale
from . import az

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
MONTHS_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
               "Oct", "Nov", "Dec"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
            "Saturday", "Sunday"]


def _ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(
        n % 10, "th")
    return f"{n}{suffix}"


def date(day: int, month: int, year: int, rng: random.Random) -> str:
    mf, ma, yy = MONTHS[month - 1], MONTHS_ABBR[month - 1], str(year)[2:]
    style = rng.random()
    # --- worded, international / US long ---------------------------------
    if style < 0.14:
        return f"{day} {mf} {year}"                       # 21 February 1956
    if style < 0.26:
        return f"{mf} {day}, {year}"                      # February 21, 1956
    if style < 0.33:
        return f"{_ordinal(day)} {mf} {year}"             # 21st February 1956
    if style < 0.38:
        return f"the {_ordinal(day)} of {mf}, {year}"     # the 21st of February, 1956
    if style < 0.44:
        return f"{day} {ma} {year}"                       # 21 Feb 1956
    if style < 0.49:
        return f"{ma} {day}, {year}"                      # Feb 21, 1956
    # --- numeric, international -----------------------------------------
    if style < 0.60:
        return f"{day:02d}.{month:02d}.{year}"            # 21.02.1956
    if style < 0.69:
        return f"{day:02d}/{month:02d}/{year}"            # 21/02/1956
    if style < 0.75:
        return f"{year}-{month:02d}-{day:02d}"            # 1956-02-21
    if style < 0.80:
        return f"{day:02d}.{month:02d}.{yy}"              # 21.02.56
    # --- numeric, US --------------------------------------------------
    if style < 0.87:
        return f"{month:02d}/{day:02d}/{year}"            # 02/21/1956
    if style < 0.91:
        return f"{month}/{day}/{year}"                    # 2/21/1956
    if style < 0.94:
        return f"{month:02d}-{day:02d}-{year}"            # 02-21-1956
    # D-54d: a weekday is outside the DATE span in every language, like
    # `-cı il` and `года`: DATE is the calendar date only. This branch used to
    # return `{wd}, {date}` / `{date}, {wd}`; it keeps its share and its rng
    # draw (so no other value in a build moves) and returns the worded date.
    # A writer that wants the weekday puts weekday() beside the span.
    if rng.random() < 0.7:
        return f"{day} {mf} {year}"                       # (Friday,) 21 February 1956
    return f"{mf} {day}, {year}"                          # (Friday,) February 21, 1956


def weekday(day: int, month: int, year: int) -> str:
    """The weekday of a real calendar date, for a writer that puts it next to
    a DATE span, outside it (D-54d): `{wd}, ⟦date⟧` or `⟦date⟧, {wd}`."""
    return WEEKDAYS[_date(year, month, day).weekday()]


LOCALE = Locale(
    code="en", name="English",
    # Borrowed from `az` -- see module docstring. Not for direct sampling.
    first_names_m=az.FIRST_M, first_names_f=az.FIRST_F,
    surname_stems=az.SURNAME_STEMS, surname_builder=az.surname,
    months=MONTHS, weekdays=WEEKDAYS, date_builder=date,
    distinctive_chars="",
)
