"""Date-builder contract tests, per locale.

Every style a `date_builder` can emit must:
  * be reconstructible to the exact (day, month, year) it was handed -- the
    round-trip validator and any downstream date parsing depend on this;
  * be deterministic under a fixed rng seed;
  * for a value that anchors.SELF_SIGNALLING["DATE"] claims to recognise,
    actually match that pattern (so weekday-prefixed dates stay self-licensing).

Run: python scripts/test_date_builders.py
"""
from __future__ import annotations

import random
import re
import sys

from piigen.locales import az, en, tr
from piigen.anchors import SELF_SIGNALLING

PASS = FAIL = 0


def check(cond: bool, msg: str, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  FAIL {msg}" + (f"  [{detail}]" if detail else ""))


# --- reconstruction -------------------------------------------------------

_MONTH_IDX = {}
for _mod in (az, en, tr):
    for _i, _m in enumerate(_mod.MONTHS, 1):
        _MONTH_IDX[_m.lower()] = _i
for _mod in (en, tr):
    for _i, _m in enumerate(_mod.MONTHS_ABBR, 1):
        _MONTH_IDX[_m.lower()] = _i

_ALL_WEEKDAYS = ({w.lower() for w in az.WEEKDAYS} | {w.lower() for w in en.WEEKDAYS}
                | {w.lower() for w in tr.WEEKDAYS})


def parse_back(s: str) -> tuple[int, int, int]:
    """Recover (day, month, year) from any style either builder emits."""
    raw = s
    # strip a leading or trailing weekday token (1-2 words) and its comma
    for wd in sorted(_ALL_WEEKDAYS, key=len, reverse=True):
        s = re.sub(rf"^{re.escape(wd)},\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(rf",\s*{re.escape(wd)}$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"-ci il$", "", s).strip()
    s = re.sub(r"^the\s+", "", s, flags=re.IGNORECASE)
    s = s.replace(" of ", " ")
    s = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", s, flags=re.IGNORECASE)
    # Turkish ordinal marker ("21. Şubat") -- a trailing period after 1-2
    # digits, but ONLY when followed by a non-digit (a month name), so this
    # never touches the dot-separated numeric style ("21.02.1956").
    s = re.sub(r"(\d{1,2})\.(?=\s+[^\d\s])", r"\1", s)
    s = s.replace(",", " ")
    s = re.sub(r"\s+", " ", s).strip()

    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        y, mo, d = map(int, m.groups())
        return d, mo, y
    m = re.fullmatch(r"(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})", s)
    if m:
        a, b, y = map(int, m.groups())
        if y < 100:
            y += 2000 if y < 50 else 1900
        # day-first unless the first field can't be a day
        if a > 12:
            return a, b, y
        if b > 12:
            return b, a, y
        return a, b, y  # ambiguous -> assume day-first; caller checks both
    m = re.fullmatch(r"(\d{1,2})\s+([^\s]+?)\.?\s+(\d{4})", s)
    if m:
        d, mon, y = m.group(1), m.group(2).lower(), m.group(3)
        return int(d), _MONTH_IDX[mon], int(y)
    m = re.fullmatch(r"([^\s]+?)\.?\s+(\d{1,2})\s+(\d{4})", s)
    if m:
        mon, d, y = m.group(1).lower(), m.group(2), m.group(3)
        return int(d), _MONTH_IDX[mon], int(y)
    raise ValueError(f"unparseable: {raw!r} (reduced to {s!r})")


def test_locale(name: str, mod) -> None:
    print(f"\n{name}: date() reconstruction + determinism")
    rng = random.Random(1)
    seen_styles = set()
    for _ in range(4000):
        d = rng.randint(1, 28)
        mo = rng.randint(1, 12)
        y = rng.randint(1945, 2027)
        s = mod.date(d, mo, y, rng)
        seen_styles.add(re.sub(r"\d+", "#", s))
        try:
            pd, pm, py = parse_back(s)
        except (ValueError, KeyError) as exc:
            check(False, f"{name} parse_back", f"{s!r}: {exc}")
            continue
        two_digit_year = bool(re.search(r"[./-]\d{2}$", s))
        year_ok = (py % 100 == y % 100) if two_digit_year else (py == y)
        ok = (pm == mo) and (pd == d) and year_ok
        # numeric day-first/month-first ambiguity: accept the swap too
        if not ok and re.fullmatch(r"[\d./-]+", s):
            ok = {pd, pm} == {d, mo} and year_ok
        check(ok, f"{name} round-trip", f"{s!r} -> ({pd},{pm},{py}) want ({d},{mo},{y})")
    print(f"  {len(seen_styles)} distinct styles exercised")
    check(len(seen_styles) >= (8 if name == "az" else 12),
          f"{name} style coverage", f"only {len(seen_styles)}")

    # determinism
    a = [mod.date(3, 4, 1972, random.Random(s)) for s in range(50)]
    b = [mod.date(3, 4, 1972, random.Random(s)) for s in range(50)]
    check(a == b, f"{name} determinism under fixed seed")


def test_every_style_self_signals() -> None:
    """Every date en.date() can emit must be recognised by
    anchors.SELF_SIGNALLING["DATE"] -- otherwise a translated DATE that lands
    without a nearby licensing word fails validation for no good reason."""
    print("\nen.date(): every style self-signals")
    pat = SELF_SIGNALLING["DATE"]
    rng = random.Random(99)
    misses = {}
    for _ in range(6000):
        d, mo, y = rng.randint(1, 28), rng.randint(1, 12), rng.randint(1945, 2027)
        s = en.date(d, mo, y, rng)
        if not pat.match(s):
            misses.setdefault(re.sub(r"\d+", "#", s), s)
    check(not misses, "en.date styles all self-signal", str(list(misses.values())))


def test_weekday_outside_date() -> None:
    """D-54d: a weekday is outside the DATE span in every language. No builder
    puts one in the value; weekday() names the date's real weekday for a
    writer that puts it beside the span; and real text that has one inside
    (`Friday, 21 February 1956`) still self-signals as a date."""
    print("\nD-54d: weekday outside the DATE value")
    from piigen.locales import ru
    from datetime import date as _d
    pat = SELF_SIGNALLING["DATE"]
    rng = random.Random(7)
    for mod in (az, en, tr, ru):
        wds = sorted({w.lower() for w in mod.WEEKDAYS}, key=len, reverse=True)
        wd_re = re.compile(r"(?<!\w)(" + "|".join(map(re.escape, wds)) + r")(?!\w)", re.I)
        inside = []
        for _ in range(4000):
            d, mo, y = rng.randint(1, 28), rng.randint(1, 12), rng.randint(1950, 2025)
            s = mod.date(d, mo, y, rng)
            if wd_re.search(s):
                inside.append(s)
        check(not inside, f"{mod.__name__.rsplit('.', 1)[-1]}.date: no weekday inside", repr(inside[:3]))
        check(mod.weekday(21, 2, 1956) == mod.WEEKDAYS[_d(1956, 2, 21).weekday()],
              f"{mod.__name__.rsplit('.', 1)[-1]}.weekday names the real day")
    # Real text that still has one inside keeps self-signalling as a date.
    for s in ("Friday, 21 February 1956", "bazar ertəsi, 19 avqust 1985"):
        check(bool(pat.match(s)), "weekday-prefixed real text still self-signals", repr(s))


if __name__ == "__main__":
    sys.path.insert(0, "scripts")
    test_locale("az", az)
    test_locale("en", en)
    test_locale("tr", tr)
    test_every_style_self_signals()
    test_weekday_outside_date()
    print(f"\n{'='*56}\nPASSED {PASS}   FAILED {FAIL}\n{'='*56}")
    sys.exit(1 if FAIL else 0)
