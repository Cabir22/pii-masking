"""Tests for the Russian carrier pack: locales/ru.py + anchors/ru.py.

No network, no downloaded model. Mirrors scripts/test_date_builders.py: every
style ru.date() can emit must reconstruct to the exact (day, month, year), be
deterministic under a fixed seed, and -- where anchors_ru.SELF_SIGNALLING
claims to recognise it -- actually match. Plus transliteration spot checks,
exonym coverage of az.CITIES, and the anchor-word patterns.
"""

from __future__ import annotations

import random
import re
import sys
from datetime import date as _date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from piigen.locales import LOCALES, az, ru          # noqa: E402
from piigen.anchors import ru as anchors_ru          # noqa: E402

PASS = 0
FAIL = 0
FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(msg)


# --------------------------------------------------------------------------- #
# date parsing
# --------------------------------------------------------------------------- #
_MONTH_LOOKUP = {}
for _i, _name in enumerate(ru.MONTHS_GEN, 1):
    _MONTH_LOOKUP[_name] = _i
for _i, _name in enumerate(ru.MONTHS, 1):
    _MONTH_LOOKUP.setdefault(_name, _i)
for _i, _name in enumerate(ru.MONTHS_ABBR, 1):
    _MONTH_LOOKUP.setdefault(_name.rstrip("."), _i)

_WD_SET = set(ru.WEEKDAYS)


def parse_ru_date(s: str) -> tuple[int, int, int | None]:
    """Reconstruct (day, month, year) from any string ru.date() emits.
    year is None only for the 2-digit-year numeric style (caller checks the
    suffix instead)."""
    t = s.strip()

    # strip a leading or trailing weekday word + comma
    for wd in ru.WEEKDAYS:
        if t.lower().startswith(wd + ","):
            t = t[len(wd) + 1:].strip()
        if t.lower().endswith(", " + wd):
            t = t[: -(len(wd) + 2)].strip()

    # numeric forms
    m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", t)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{2})", t)
    if m:
        return int(m.group(1)), int(m.group(2)), None
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", t)
    if m:
        return int(m.group(3)), int(m.group(2)), int(m.group(1))
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", t)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))

    # worded: [«]D[»] MONTH[.] YYYY [г.|года]
    t = t.replace("«", "").replace("»", "")
    t = re.sub(r"\s+(г\.|года)$", "", t).strip()
    m = re.fullmatch(r"(\d{1,2})\s+([А-Яа-яЁё]+)\.?\s+(\d{4})", t)
    if not m:
        raise ValueError(f"unparseable ru date: {s!r}")
    month = _MONTH_LOOKUP.get(m.group(2).lower())
    if month is None:
        raise ValueError(f"unknown month {m.group(2)!r} in {s!r}")
    return int(m.group(1)), month, int(m.group(3))


# --------------------------------------------------------------------------- #
# 1. date builder: reconstruct, determinism, genitive
# --------------------------------------------------------------------------- #
def test_dates() -> None:
    styles_seen: set[str] = set()
    rng_iter = random.Random(1)
    for _ in range(4000):
        y = rng_iter.randint(1950, 2035)
        mth = rng_iter.randint(1, 12)
        d = rng_iter.randint(1, 28)
        seed = rng_iter.randint(0, 10_000_000)

        s = ru.date(d, mth, y, random.Random(seed))
        s2 = ru.date(d, mth, y, random.Random(seed))
        check(s == s2, f"non-deterministic: seed {seed} gave {s!r} then {s2!r}")

        styles_seen.add(re.sub(r"\d", "#", s))
        try:
            pd, pm, py = parse_ru_date(s)
        except ValueError as exc:
            check(False, str(exc))
            continue
        check(pd == d, f"day: {s!r} parsed day {pd}, want {d}")
        check(pm == mth, f"month: {s!r} parsed month {pm}, want {mth}")
        check(py in (y, None), f"year: {s!r} parsed year {py}, want {y}")
        if py is None:
            check(s.endswith(str(y)[2:]), f"2-digit year mismatch in {s!r} (want ..{str(y)[2:]})")

    print(f"  {len(styles_seen)} distinct date styles exercised")
    check(len(styles_seen) >= 8, f"expected >=8 date styles, saw {len(styles_seen)}")

    # genitive month must appear in a worded date, nominative must not
    hits = 0
    r = random.Random(7)
    for _ in range(400):
        s = ru.date(21, 2, 1956, r)
        if "февраля" in s:
            hits += 1
        check("февраль " not in s, f"nominative month leaked into {s!r}")
    check(hits > 0, "genitive 'февраля' never produced for a worded date")

    # the year word is never inside the DATE value (real-text guide, Russian
    # notes: `14 октября 2026 года` -> `14 октября 2026`, like `-cı il`)
    r = random.Random(11)
    inside = [s for s in (ru.date(r.randint(1, 28), r.randint(1, 12), r.randint(1950, 2035), r)
                          for _ in range(3000)) if re.search(r"\d{4}\s*(?:г\.|года)", s)]
    check(not inside, f"the year word is inside a DATE value: {inside[:3]}")
    words = {ru.year_word(random.Random(i)) for i in range(50)}
    check(words == {" г.", " года"}, f"year_word() gives {words}")


# --------------------------------------------------------------------------- #
# 2. self-signalling: worded ru dates need no anchor
# --------------------------------------------------------------------------- #
def test_self_signalling() -> None:
    pat = anchors_ru.SELF_SIGNALLING["DATE"]
    r = random.Random(3)
    worded = 0
    for _ in range(600):
        s = ru.date(r.randint(1, 28), r.randint(1, 12), r.randint(1950, 2035), r)
        if re.search(r"[А-Яа-яЁё]", s):          # a worded style
            worded += 1
            check(bool(pat.match(s)), f"SELF_SIGNALLING['DATE'] missed {s!r}")
    check(worded > 50, f"only {worded} worded dates sampled")
    check(not pat.match("34"), "SELF_SIGNALLING['DATE'] matched a bare '34'")
    check(not pat.match("в отделе 12 человек"),
          "SELF_SIGNALLING['DATE'] matched prose")


# --------------------------------------------------------------------------- #
# 3. transliteration + exonyms
# --------------------------------------------------------------------------- #
def test_translit() -> None:
    # regular cases the mechanical map is expected to get right
    exact = {
        "Əli": "Али",
        "Əliyev": "Алиев",
        "Yaşar": "Яшар",
        "Nurlan": "Нурлан",
        "Aygün": "Айгюн",
    }
    for src, want in exact.items():
        got = ru.transliterate(src)
        check(got == want, f"transliterate({src!r}) = {got!r}, want {want!r}")

    # names whose conventional Russian spelling is irregular (Мамедов, Гусейн).
    # The mechanical fallback is deliberately lossy here -- a name-exonym table
    # or the owed native-speaker review would override these. These asserts
    # only pin current behaviour so a change is noticed.
    mechanical = {
        "Məmmədov": "Маммадов",       # conventional: Мамедов
        "Hüseyn": "Гюсейн",           # conventional: Гусейн
    }
    for src, want in mechanical.items():
        got = ru.transliterate(src)
        check(got == want, f"transliterate({src!r}) = {got!r}, want {want!r} (mechanical)")

    # non-letters pass through
    check(ru.transliterate("küç. 12") == "кюч. 12",
          f"punctuation/digits not preserved: {ru.transliterate('küç. 12')!r}")

    # output is pure Cyrillic (+ spaces/punct/digits), no Latin or AZ chars
    latin_az = re.compile(r"[A-Za-zƏəÇçĞğIıİÖöŞşÜü]")
    for name in az.FIRST_M[:200] + az.FIRST_F[:200]:
        out = ru.transliterate(name)
        check(not latin_az.search(out), f"transliterate({name!r}) left Latin/AZ: {out!r}")


def test_exonyms() -> None:
    known = {
        "Bakı": "Баку", "Gəncə": "Гянджа", "Sumqayıt": "Сумгаит",
        "Naxçıvan": "Нахичевань", "Lənkəran": "Ленкорань", "Şamaxı": "Шемаха",
    }
    for src, want in known.items():
        check(ru.EXONYMS.get(src) == want,
              f"EXONYMS[{src!r}] = {ru.EXONYMS.get(src)!r}, want {want!r}")

    # every city in the pool renders to pure Cyrillic (exonym or translit)
    latin_az = re.compile(r"[A-Za-zƏəÇçĞğIıİÖöŞşÜü]")
    for city in az.CITIES:
        out = ru.render_value("CITY", city)
        check(bool(out) and not latin_az.search(out),
              f"render_value('CITY', {city!r}) = {out!r} (not pure Cyrillic)")


# --------------------------------------------------------------------------- #
# 4. render_value: names transliterated, structured values untouched
# --------------------------------------------------------------------------- #
def test_render_value() -> None:
    check(ru.render_value("CITY", "Gəncə") == "Гянджа", "CITY exonym not applied")
    check(ru.render_value("GIVENNAME", "Yaşar") == "Яшар", "GIVENNAME not transliterated")
    check(ru.render_value("SURNAME", "Əliyev") == "Алиев", "SURNAME not transliterated")

    untouched = {
        "TELEPHONENUM": "+994 51 234 56 78",
        "EMAIL": "yaqubovn@bakusteel.az",
        "AZ_FIN": "6X9P7Q2",
        "IBAN": "AZ21NABZ00000000137010001944",
        "IPV4": "192.168.10.4",
        "CARD_SECURITY_CODE": "483",
        "URL": "http://www.zirve.az/magic?t=D5vvvU0k",
    }
    for label, val in untouched.items():
        check(ru.render_value(label, val) == val,
              f"render_value({label!r}) altered a structured value: {ru.render_value(label, val)!r}")


# --------------------------------------------------------------------------- #
# 5. anchor-required word patterns
# --------------------------------------------------------------------------- #
def test_anchor_patterns() -> None:
    positives = {
        "AGE": ["Клиент, 34 года, обратился", "в возрасте 34 лет",
                "родился в семье", "ему исполнилось 40"],
        "BUILDINGNUM": ["проживает по адресу, дом 12", "ул. Низами, 84",
                        "кв. 15, корпус 2", "в микрорайоне 8"],
        "CARD_SECURITY_CODE": ["код CVV: 483", "введите cvc2 карты",
                               "трёхзначный код на обороте карты",
                               "код проверки подлинности карты"],
        "DATE": ["дата рождения указана как", "договор подписан",
                 "паспорт выдан", "срок действия до", "зарегистрирован по месту"],
        "TIME": ["встреча назначена на", "время начала сеанса",
                 "в 14 часов", "приём окончен"],
    }
    negatives = ["в отделе работает 34 человека", "версия 2 системы",
                 "страница 12 отчёта", "ошибка номер 500"]

    for label, phrases in positives.items():
        pat = anchors_ru.ANCHOR_REQUIRED[label]
        for ph in phrases:
            check(bool(pat.search(ph)),
                  f"ANCHOR_REQUIRED[{label!r}] missed {ph!r}")
        for ph in negatives:
            # a negative may legitimately hit some label; only assert AGE,
            # which the negatives were written to dodge
            if label == "AGE":
                check(not pat.search(ph),
                      f"ANCHOR_REQUIRED['AGE'] false-matched {ph!r}")


def test_structural_words() -> None:
    pat = anchors_ru.STRUCTURAL_GROUP_WORDS
    for w in ["Раздел ", "Пункт ", "Статья ", "Таблица ", "Глава "]:
        check(bool(pat.search(w)), f"STRUCTURAL_GROUP_WORDS missed {w!r}")
    check(not pat.search("возраст "), "STRUCTURAL_GROUP_WORDS matched 'возраст '")


# --------------------------------------------------------------------------- #
# 6. locale wiring
# --------------------------------------------------------------------------- #
def test_street_rendering() -> None:
    """Streets are Russian addresses, not transliterated Azerbaijani ones.

    "Nizami küçəsi" was coming out "Низами кючаси" -- Cyrillic, but "küçə" is
    an Azerbaijani noun, so the address stayed Azerbaijani inside a Russian
    document. It landed in the entity value the model trains on rather than in
    the prose around it, which makes it worse than ordinary residue. Russian
    puts the type first and translates it.
    """
    for az, want in [
        ("Nizami küçəsi", "улица Низами"),
        ("Qomuşçu küçəsi", "улица Гомушчу"),
        ("Zaur Səmədov döngəsi", "переулок Заур Самадов"),
        ("Telman Həsənov prospekti", "проспект Телман Гасанов"),
        # the abbreviation style is kept rather than expanded
        ("Eyvaz Hümbətov küç.", "ул. Ейваз Гюмбатов"),
        ("Cümhuriyyət pr.", "пр. Джюмгурийят"),
        # diacritic-stripped spellings the noise injector produces
        ("Nizami kucesi", "улица Низами"),
        # a stripped name transliterates by what is actually written --
            # plain "e" is "е", where "ə" would have given "а" -- so the type
            # word is what this case is really asserting
            ("Zaur Semedov dongesi", "переулок Заур Семедов"),
    ]:
        check(ru.render_value("STREET", az) == want,
              f"street {az!r} -> {ru.render_value('STREET', az)!r}, want {want!r}")

    # a bare name with no type word is transliterated whole
    # (M1, the re-check: `iya` is Russian `ия`, so `Хиябан`, not `Хийабан`)
    check(ru.render_value("STREET", "Fəxri Xiyaban") == "Фахри Хиябан",
          "street with no type word is transliterated whole")

    # restyle_street repairs values already written the wrong way round
    for was, want in [
        ("Гомушчу кючаси", "улица Гомушчу"),
        ("Ейваз Гюмбатов кюч.", "ул. Ейваз Гюмбатов"),
        ("Заур Самадов дёнгаси", "переулок Заур Самадов"),
        ("Телман Гасанов проспекти", "проспект Телман Гасанов"),
        ("Солтан Гаджыбаов кючм.", "ул. Солтан Гаджыбаов"),
    ]:
        check(ru.restyle_street(was) == want,
              f"restyle {was!r} -> {ru.restyle_street(was)!r}, want {want!r}")

    # anything already correct, or not a street, is left alone. "Бабакюча" is
    # the trap: the name itself contains "küçə", so a substring rule would
    # mangle it.
    for o in ["улица Низами", "проспект Гейдар Алиев", "Хырдалан",
              "Бабакюча", "Фахри Хийабан"]:
        check(ru.restyle_street(o) is None, f"restyle leaves {o!r} alone")

    az_type = re.compile(r"кюч|куч|проспект[иы]|дёнг|донг")
    for az in ["Nizami küçəsi", "Heydər Əliyev prospekti",
               "Zaur Səmədov döngəsi", "Eyvaz Hümbətov küç.", "Cümhuriyyət pr."]:
        check(not az_type.search(ru.render_value("STREET", az)),
              f"no Azerbaijani type word left in {az!r}")


def test_street_declension() -> None:
    """A street takes the case its preposition demands -- type word only.

    "недалеко от переулок Мюбариз" is broken Russian. The type word is an
    ordinary Russian noun that pymorphy3 declines exactly; the transliterated
    name is left alone on purpose, because pymorphy3 has no entry for it and
    guesses from the ending -- it reads "Гуйчу" as a verb and offers
    "гуйчившего". Those values are the spans the model trains on.
    """
    for before, want in [
        ("недалеко от ", "gent"), ("территорий вокруг ", "gent"),
        ("обратились к ", "datv"), ("встреча перед ", "ablt"),
        ("написано о ", "loct"), ("документ для ", "gent"),
    ]:
        check(ru.governing_case(before) == want,
              f"governing_case({before!r}) -> {ru.governing_case(before)!r}, want {want!r}")

    # ambiguous prepositions are left alone in general...
    check(ru.governing_case("положил на ") is None,
          "'на' alone is ambiguous and governs nothing")
    # ...but before a STREET they are locative in practice
    check(ru.governing_case("живу на ", "STREET") == "loct",
          "'на' before a street is locative")
    check(ru.governing_case("офис в ", "STREET") == "loct",
          "'в' before a street is locative")

    for value, case, want in [
        ("переулок Мюбариз Исмайилов", "gent", "переулка Мюбариз Исмайилов"),
        ("проспект Гуйчу", "gent", "проспекта Гуйчу"),
        ("улица Низами", "datv", "улице Низами"),
        ("площадь Азадлыг", "ablt", "площадью Азадлыг"),
        ("улица Баллабур", "loct", "улице Баллабур"),
    ]:
        check(ru.decline_street(value, case) == want,
              f"decline {value!r} to {case} -> "
              f"{ru.decline_street(value, case)!r}, want {want!r}")

    # the NAME never moves, whatever pymorphy3 thinks of it
    for value in ["проспект Гуйчу", "улица Сабзиханым", "переулок Гюсейнзада"]:
        tail = value.split(" ", 1)[1]
        check(ru.decline_street(value, "gent").endswith(tail),
              f"the name in {value!r} is left in the nominative")

    # an abbreviated type does not decline in writing
    check(ru.decline_street("ул. Ширин Мирзаев", "gent") == "ул. Ширин Мирзаев",
          "abbreviated type is left as written")
    check(ru.decline_street("пр. Гуйчу", "datv") == "пр. Гуйчу",
          "abbreviated prospekt is left as written")
    # and a bare name has nothing to decline
    check(ru.decline_street("Фахри Хийабан", "gent") == "Фахри Хийабан",
          "a street with no type word is unchanged")


def test_locale_object() -> None:
    check("ru" in LOCALES, "LOCALES has no 'ru' entry")
    loc = LOCALES["ru"]
    check(loc.code == "ru" and loc.name == "Russian", "ru Locale mislabelled")
    check(callable(loc.date_builder), "ru Locale.date_builder not callable")
    s = loc.date_builder(21, 2, 1956, random.Random(0))
    check(isinstance(s, str) and s, f"date_builder returned {s!r}")
    check(len(loc.months) == 12 and len(loc.weekdays) == 7, "calendar arrays wrong length")

    # SIMURG script names are lower-case; capitalised names make it flag every
    # clean Russian document as corrupt (verified against simurg 1.0.3).
    check(tuple(ru.EXPECTED_SCRIPTS) == tuple(s.lower() for s in ru.EXPECTED_SCRIPTS),
          f"EXPECTED_SCRIPTS must be lower-case: {ru.EXPECTED_SCRIPTS}")
    check("cyrillic" in ru.EXPECTED_SCRIPTS, "EXPECTED_SCRIPTS missing 'cyrillic'")


TESTS = [
    ("date builder: reconstruct + deterministic + genitive", test_dates),
    ("self-signalling worded ru dates", test_self_signalling),
    ("transliteration spot checks + pure-Cyrillic output", test_translit),
    ("city exonyms + every az.CITIES renders to Cyrillic", test_exonyms),
    ("render_value: names transliterated, structured untouched", test_render_value),
    ("anchor-required word patterns", test_anchor_patterns),
    ("structural group words", test_structural_words),
    ("street rendering: type-first, translated", test_street_rendering),
    ("street declension: type word only", test_street_declension),
    ("LOCALES['ru'] wiring", test_locale_object),
]

if __name__ == "__main__":
    for name, fn in TESTS:
        print(name)
        fn()
    print()
    print("=" * 60)
    print(f"PASSED {PASS}   FAILED {FAIL}")
    print("=" * 60)
    for f in FAILURES:
        print("  FAIL:", f)
    sys.exit(1 if FAIL else 0)
