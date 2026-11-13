"""Standalone dates (D-17): which dates in a text must be labelled DATE.

D-17 follows the benchmark: every **standalone date** is DATE -- in prose,
after `Tarix:`/`tarixi`/`Sənəd tarixi`, in tables, in every format
(dd.mm.yyyy, ISO, spelled-out months). A **date followed by a time** (a log
or record timestamp, `2021-08-22 19:45:12`, `[2031-04-12 10:03]`) is not; it
stays a timestamp look-alike.

This module is the one definition, shared by
  * generation (`quality_filter.screen_record(invented=True)` rejects a
    document with an unlabelled standalone date, as for invented PII), and
  * `scripts/relabel_standalone_dates.py`, which labels them in existing data.

What counts, precision first (a wrong DATE label costs less than a missed
one, but a label on a version number or an impossible day teaches nothing):
  * a full calendar date -- day, month and year -- that exists (`31.02.2020`
    is not a date, nor is `33.08.2009`);
  * numeric `d.m.yyyy` / `d/m/yyyy` / `d-m-yyyy` (either day or month
    first, one separator throughout), ISO `yyyy-mm-dd` and `yyyy/mm/dd`, an
    en or em dash read as a hyphen;
  * with a 2-digit year only in the strict shape `dd.mm.yy` / `dd/mm/yy`
    (P2-6, batch 3: 2,999 such dates in the dated corpus, a sample of 40 all
    real -- table cells, service records, `01.01.23 – 31.03.23`; briefs plan
    them as DATE too);
  * worded, day first or month first, with a month name or abbreviation in
    Azerbaijani, Turkish, English or Russian (`14 noyabr 2016`, `12 марта
    1990`, `March 12, 1990`); an Azerbaijani `-ci il` after the year stays
    outside the span, as other hyphen suffixes do;
  * not inside a longer token (`v2.14.09.1991`, `INV-2016-05-12-7`), and not
    next to a clock time on either side (a timestamp).
A year alone (`2018-ci il`), a month and year, or a 2-digit year in any
other shape (`1.2.16`, `12-05-16`, often a version or a code) is not a full
date and is left alone.
"""

from __future__ import annotations

import datetime
import re

from .text import fold_diacritics

_AZ = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avqust",
       "sentyabr", "oktyabr", "noyabr", "dekabr"]
_TR = ["ocak", "şubat", "mart", "nisan", "mayıs", "haziran", "temmuz", "ağustos",
       "eylül", "ekim", "kasım", "aralık"]
_EN = ["january", "february", "march", "april", "may", "june", "july", "august",
       "september", "october", "november", "december"]
_EN_ABBR = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct",
            "nov", "dec"]
_RU = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август",
       "сентябрь", "октябрь", "ноябрь", "декабрь"]
_RU_GEN = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
           "сентября", "октября", "ноября", "декабря"]
_RU_ABBR = ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт",
            "ноя", "дек"]

MONTH_NUMBER: dict[str, int] = {}
for _names in (_AZ, _TR, _EN, _EN_ABBR, _RU, _RU_GEN, _RU_ABBR):
    for _i, _name in enumerate(_names, 1):
        MONTH_NUMBER[_name] = _i
        MONTH_NUMBER[fold_diacritics(_name)] = _i
MONTH_NUMBER["sept"] = 9


def _month_key(s: str) -> str:
    """Lookup key: `İyun`/`IYUN`/`İYUL` -> `iyun`/`iyul` (Python lower-cases
    `İ` to `i` plus a combining dot, and `re.IGNORECASE` does not pair it
    with `i`)."""
    return s.rstrip(".").replace("İ", "i").replace("I", "i").lower()


def _month_number(s: str) -> int | None:
    return MONTH_NUMBER.get(_month_key(s))


_MONTH_FORMS = set(MONTH_NUMBER) | {n.replace("i", "İ", 1) for n in MONTH_NUMBER if n.startswith("i")}

_MONTH = "(?:" + "|".join(sorted(map(re.escape, _MONTH_FORMS), key=len, reverse=True)) + r")\.?"
_DAY = r"\d{1,2}(?:st|nd|rd|th)?"
_YEAR = r"(?:1[89]|20)\d{2}"

DATE_RE = re.compile(
    r"(?<![\w./-])(?:"
    r"(?P<iso>(?P<iy>" + _YEAR + r")(?P<isep>[-/])(?P<im>\d{1,2})(?P=isep)(?P<id>\d{1,2}))"
    r"|(?P<num>(?P<na>\d{1,2})(?P<nsep>[./-])(?P<nb>\d{1,2})(?P=nsep)(?P<ny>" + _YEAR + r"))"
    r"|(?P<dmy>(?P<dd>" + _DAY + r")\s+(?:of\s+)?(?P<dm>" + _MONTH + r"),?\s+(?P<dy>" + _YEAR + r"))"
    r"|(?P<mdy>(?P<mm>" + _MONTH + r")\s+(?P<md>" + _DAY + r"),?\s+(?P<my>" + _YEAR + r"))"
    r"|(?P<short>(?P<sa>\d{2})(?P<ssep>[./])(?P<sb>\d{2})(?P=ssep)(?P<sy>\d{2}))"
    r")(?![\w/])(?!\.\d)(?![.-]\d)",
    re.IGNORECASE)

# A clock time right after (or right before) the date makes it a timestamp:
# `2016-11-05 14:22:01`, `[12.05.2021 10:15]`, `2025-03-12T10:15`,
# `14 may 2021, 09:30`, `10:15 12.05.2021`. Only a space, a `T` or ", " may
# sit between them: a bare comma or a `|` is a column border (a CSV row
# `14:02,24.07.1973`, a table cell after a MAC address `…75:85 | 20 iyun 1946`),
# and the time must be a real clock time.
_CLOCK = r"(?:[01]?\d|2[0-3]):[0-5]\d"
# After a date the time may be noised or malformed and still be one:
# `[2018-09-14 22:1O:05]`, `15.09.2017 l4:10`, `10:60:12` (369 such dates in
# the old corpus were first taken for standalone ones), and, D-18d, a digit
# too many or too few: `[2017-11-15 09:122:50]` (batch 2, llm_az_006627),
# `008:15:00`, `0:905:44`, `16:0:35`, `14:3022`, `l4:2Z1:0`, `11:OZ:42`
# (about 333 more in the dated corpus). So any colon-joined token of 1-4
# digit-like characters a side, with at least one real digit, counts. A
# number with a dot or a comma is not a time: `2025-04-15\t8500.50` is a date
# and an amount in a table, `08.08.1996 4.24.43.624` a date and an address.
_NOISY_CLOCK = r"(?P<clock>[0-9OoIlZSGB]{1,4}:[0-9OoIlZSGB]{1,4})"
# D-51g (2): the gap between the date and the time is any run of horizontal
# space on the line, not only 1-3 spaces or tabs: the copy-paste noise writes
# a non-breaking, narrow non-breaking or thin space (`[08.09.2026\xa015:25]`),
# and log and table rows pad with 4+ spaces or tabs (`2018-11-4     17:20`).
# 35 DATE labels and their TIME labels sat in such stamps (v3 label-noise R5).
# A newline is never a gap: a date on one line and a time on the next stay
# two values.
STAMP_SPACE = "[ \t\u00a0\u2000-\u200a\u202f\u205f\u3000]"
_TIME_AFTER = re.compile(r"(?:" + STAMP_SPACE + r"+|T|," + STAMP_SPACE + r"{1,2})" + _NOISY_CLOCK)
_TIME_BEFORE = re.compile(r"(?<![\w:.])" + _CLOCK + r"(?::[0-5]\d)?(?:\s?[AaPp][Mm])?"
                          + STAMP_SPACE + r"+$")


def _real(y: int, m: int, d: int) -> bool:
    try:
        datetime.date(y, m, d)
    except ValueError:
        return False
    return True


def _day(s: str) -> int:
    return int(re.match(r"\d+", s).group(0))


def calendar_ok(m: re.Match) -> bool:
    """Does the matched string name a day that exists?"""
    if m.group("iso"):
        return _real(int(m.group("iy")), int(m.group("im")), int(m.group("id")))
    if m.group("num"):
        a, b, y = int(m.group("na")), int(m.group("nb")), int(m.group("ny"))
        return _real(y, b, a) or _real(y, a, b)
    if m.group("dmy"):
        month = _month_number(m.group("dm"))
        return bool(month) and _real(int(m.group("dy")), month, _day(m.group("dd")))
    if m.group("short"):
        a, b, yy = int(m.group("sa")), int(m.group("sb")), int(m.group("sy"))
        return any(_real(c + yy, mo, d) for c in (1900, 2000) for d, mo in ((a, b), (b, a)))
    month = _month_number(m.group("mm"))
    return bool(month) and _real(int(m.group("my")), month, _day(m.group("md")))


def is_timestamp(text: str, s: int, e: int) -> bool:
    after = _TIME_AFTER.match(text, e)
    if after and any(ch.isdigit() for ch in after.group("clock")):
        return True
    return bool(_TIME_BEFORE.search(text[max(0, s - 64):s]))


def standalone_dates(text: str) -> list[tuple[int, int]]:
    """Every standalone date in `text`, as (start, end): real, full, not a
    timestamp, and not the front of a longer token (`№ 2026/08/12-X`,
    `2018-09-12-X99`), by the resolver's own word-boundary rule."""
    from .resolver import _is_word_boundary
    # An en or em dash is a hyphen here (`Tarix: 12–11–2022`, `[2015–04-10]`,
    # often the copy_paste noise kind): one character for one, so the
    # offsets found in the translated copy are the text's own.
    scan = text.translate(_DASHES)
    return [m.span() for m in DATE_RE.finditer(scan)
            if calendar_ok(m) and not is_timestamp(text, *m.span())
            and _is_word_boundary(text, *m.span(), "DATE")]


_DASHES = str.maketrans("–—", "--")


def labelable(text: str, s: int, e: int) -> str:
    """'' if a DATE span at (s, e) passes every check the gates apply to a
    span on its own; otherwise the first reason it would not."""
    from .anchors import has_anchor, structural_kind
    from .resolver import _reproducible
    from .validate import value_valid
    if not value_valid("DATE", text[s:e])[0]:
        return "not a valid DATE value"
    if structural_kind(text, s, e):
        return "structural position"
    if not has_anchor("DATE", text, s, e):
        return "no anchor"
    if not _reproducible(text, s, e, "DATE"):
        return "resolver would not place it"
    return ""


def find_unlabelled_dates(text: str, entities: list[dict], decoy_spans=()) -> list[dict]:
    """Standalone dates no label and no declared decoy covers. Should be [] in
    a training record (D-17). Each: start, end, text, why_not ('' when it
    can be labelled as it stands)."""
    covered = [(e["start"], e["end"]) for e in entities] + [tuple(d) for d in decoy_spans]
    out = []
    for s, e in standalone_dates(text):
        if any(a < e and s < b for a, b in covered):
            continue
        out.append({"start": s, "end": e, "text": text[s:e], "why_not": labelable(text, s, e)})
    return out
