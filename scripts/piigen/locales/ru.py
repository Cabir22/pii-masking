"""Russian carrier pack.

WORK IN PROGRESS. Under the translation approach (2026-09-03
entry) an en/tr/ru pack is *not* a full locale: the PII stays Azerbaijani and
is spliced from the shared ``az`` pools, so this pack only overrides the
language-facing pieces --

* the calendar layer (``MONTHS`` / ``MONTHS_GEN`` / ``MONTHS_ABBR`` /
  ``WEEKDAYS`` / ``date()``), and
* orthography: ``render_value()`` transliterates a freshly minted Azerbaijani
  name or street into Cyrillic, and ``EXONYMS`` supplies the established
  Russian city names a character map cannot produce (``Gəncə`` -> ``Гянджа``).

Identity / geography / phone / ID fields borrow ``az``'s so the ``Locale``
constructs and ``LOCALES["ru"].date_builder`` resolves; they are not meant to
be sampled from directly.

Still to add before the Russian pack is complete: phrase banks, the
``anchors_ru`` wiring into the shared ``anchors`` dispatch (see
``scripts/piigen/anchors_ru.py``), and a decision on ``pymorphy`` slot-boundary
inflection (accepted as out of scope for v1 -- foreign names in casual Russian
are commonly left undeclined and the span stays exact).

Dates: Russian writes the day first and the month in the **genitive** after a
day number -- ``21 февраля 1956 г.`` -- which is why ``MONTHS_GEN`` exists
alongside the nominative ``MONTHS``. Month-first order and ``MM.DD`` numeric
forms are deliberately absent: they are not Russian conventions. As with
``en.py`` the model only labels the span as DATE, it never has to resolve
which number is the day.

The transliteration table is a deliberately coarse mechanical fallback, not a
standard. Russian rendering of Azerbaijani proper nouns is not fully regular
(``ə`` is usually ``а`` -- ``Əliyev`` -> ``Алиев`` -- but ``я`` in some
established names), so ``EXONYMS`` overrides it for cities and a native-speaker
review pass is still owed on the long tail .
"""

from __future__ import annotations

import random
import re
from datetime import date as _date

from .base import Locale
from . import az

# --------------------------------------------------------------------------- #
# calendar
# --------------------------------------------------------------------------- #
MONTHS = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль",
          "август", "сентябрь", "октябрь", "ноябрь", "декабрь"]

# Genitive -- the form that follows a day number ("21 февраля"). This is the
# common written case for a full date, so most date() styles use it.
MONTHS_GEN = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
              "августа", "сентября", "октября", "ноября", "декабря"]

MONTHS_ABBR = ["янв.", "фев.", "мар.", "апр.", "мая", "июн.", "июл.",
               "авг.", "сен.", "окт.", "ноя.", "дек."]

# Monday-first, to match datetime.date.weekday().
WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница",
            "суббота", "воскресенье"]


def date(day: int, month: int, year: int, rng: random.Random) -> str:
    """Render a Russian date. ``(day, month, year)`` from
    ``ValueFactory.date()`` is always a real calendar date (day capped at
    28/30), so ``datetime.date(...).weekday()`` never raises.
    """
    mg = MONTHS_GEN[month - 1]
    ma = MONTHS_ABBR[month - 1]
    yy = str(year)[2:]
    style = rng.random()

    # --- numeric ------------------------------------------------------------
    if style < 0.30:
        return f"{day:02d}.{month:02d}.{year}"                 # 21.02.1956
    if style < 0.40:
        return f"{day:02d}.{month:02d}.{yy}"                   # 21.02.56
    if style < 0.47:
        return f"{year}-{month:02d}-{day:02d}"                 # 1956-02-21
    if style < 0.53:
        return f"{day:02d}/{month:02d}/{year}"                 # 21/02/1956

    # --- worded, genitive month ------------------------------------------
    # The year word (`года`, `г.`) is NOT part of the DATE value: the real-text
    # guide's Russian notes label `14 октября 2026 года` as `14 октября 2026`,
    # like Azerbaijani `-cı il` (D-51i). The team confirmed the fix (17 Oct).
    # A writer that wants the word puts year_word() after the span; translated
    # text brings its own (`в ⟦3⟧ году`) where the source had `-cı il`, and a
    # value ending in `года` would have read `1956 года году`.
    if style < 0.80:
        return f"{day} {mg} {year}"                            # 21 февраля 1956
    if style < 0.85:
        return f"«{day:02d}» {mg} {year}"                      # «21» февраля 1956  (contracts)
    if style < 0.89:
        return f"{day} {ma} {year}"                            # 21 фев. 1956

    # D-54d: a weekday is outside the DATE span in every language, like
    # `-cı il` and `года`: DATE is the calendar date only. This branch used to
    # return `{wd}, {date}` / `{date}, {wd}`; it keeps its share and its rng
    # draw (so no other value in a build moves) and returns the worded date.
    # A writer that wants the weekday puts weekday() beside the span.
    rng.random()
    return f"{day} {mg} {year}"                                # (пятница,) 21 февраля 1956


def weekday(day: int, month: int, year: int) -> str:
    """The weekday of a real calendar date, for a writer that puts it next to
    a DATE span, outside it (D-54d): `{wd}, ⟦date⟧` or `⟦date⟧, {wd}`."""
    return WEEKDAYS[_date(year, month, day).weekday()]


def year_word(rng: random.Random) -> str:
    """The year word a writer may put AFTER a worded DATE span, outside it
    (` г.` or ` года`), as `az.year_suffix` does for `-cı il` (D-51i)."""
    return rng.choice((" г.", " года"))


# --------------------------------------------------------------------------- #
# transliteration  (mechanical fallback -- see module docstring)
# --------------------------------------------------------------------------- #
# Applied longest-key-first, then the single-character map. Word-initial
# iotated vowels and the "y + vowel" glide are handled before the plain map so
# "Yaşar" -> "Яшар" and "Əliyev" -> "Алиев" rather than "Йашар" / "Алийев".
_DIGRAPHS = [
    # M1 (re-check): `iyə`/`iya` is Russian `ия` (`Сания`,
    # `Зияратов`), not `ийа`
    ("iyə", "ия"), ("iya", "ия"),
    ("ya", "я"), ("yə", "я"), ("yu", "ю"), ("yü", "ю"),
    ("yo", "ё"), ("yö", "ё"), ("ye", "е"),
    ("iy", "ий"), ("əy", "ай"), ("ey", "ей"), ("oy", "ой"), ("uy", "уй"),
]

_CHARMAP = {
    "a": "а", "b": "б", "c": "дж", "ç": "ч", "d": "д", "e": "е", "ə": "а",
    "f": "ф", "g": "г", "ğ": "г", "h": "г", "x": "х", "ı": "ы", "i": "и",
    "j": "ж", "k": "к", "q": "г", "l": "л", "m": "м", "n": "н", "o": "о",
    "ö": "ё", "p": "п", "r": "р", "s": "с", "ş": "ш", "t": "т", "u": "у",
    "ü": "ю", "v": "в", "y": "й", "z": "з", "'": "", "`": "",
    "w": "в",          # foreign names only (`Sawsan` -> `Савсан`); Azerbaijani has no `w`
}

# "-yev/-yeva/-yeva" and "-iyev/-iyeva" name endings: the glide is absorbed in
# Russian ("Алиев", not "Алийев"). Handled as a suffix rewrite before the
# general pass so it wins over the _DIGRAPHS "ye" -> "е" (which would give
# "Алиев" too here, but the explicit suffix keeps intent obvious and covers
# "-yov").
_NAME_SUFFIX = [
    # M1 (re-check): `-bəyov` is Russian `-беков` (`Гаджибеков`),
    # not `-баов`
    (re.compile(r"bəyov(a)?$", re.I), lambda m: "бекова" if m.group(1) else "беков"),
    # ... and a vowel + `yov` keeps its glide as Russian `-аев` (`Abayov` ->
    # `Абаев`, not `Абаов`)
    (re.compile(r"([aə])yov(a)?$", re.I), lambda m: "аева" if m.group(2) else "аев"),
    (re.compile(r"iyev(a)?$", re.I), lambda m: "иева" if m.group(1) else "иев"),
    (re.compile(r"yev(a)?$", re.I),  lambda m: "ева" if m.group(1) else "ев"),
    (re.compile(r"yov(a)?$", re.I),  lambda m: "ова" if m.group(1) else "ов"),
]


def _translit_token(tok: str) -> str:
    # D-56c (5), the team: Python lowercases `İ` to `i` + U+0307, which came
    # out as `И̇сиф`. `I` (= ı) is left alone: foreign names (`Igor`) pass here too
    low = tok.replace("İ", "i").lower()
    for pat, repl in _NAME_SUFFIX:
        if pat.search(low):
            low = pat.sub(repl, low)
            break
    out: list[str] = []
    i = 0
    while i < len(low):
        for src, dst in _DIGRAPHS:
            if low.startswith(src, i):
                out.append(dst)
                i += len(src)
                break
        else:
            ch = low[i]
            out.append(_CHARMAP.get(ch, ch))
            i += 1
    res = "".join(out)
    # M1: Russian writes `и` after `ж ш ч щ`, never `ы` (`Гаджи`, `Маши`)
    res = re.sub(r"([жшчщ])ы", r"\1и", res)
    # title-case if the source token was capitalised
    if tok[:1].isupper():
        res = res[:1].upper() + res[1:]
    return res


_TOKEN_RE = re.compile(r"[A-Za-zƏəÇçĞğIıİiÖöŞşÜü]+|[^A-Za-zƏəÇçĞğIıİiÖöŞşÜü]+")

# M1 (re-check): a foreign name with no Russian form in
# foreign_names.txt (Georgian, Persian, Arabic, Turkish) is written in an
# English-style romanisation; read with Azerbaijani rules its digraphs came out
# `Кгинтибидзе`, `Имнаисгвили`, `Малкгаз`. The digraphs are mapped first, and
# `h` is Russian `х` and `j` is `дж` (`Mehmet` -> `Мехмет`, `Jaba` -> `Джаба`)
_FOREIGN_DIGRAPHS = [("sh", "ş"), ("kh", "x"), ("ch", "ç"), ("zh", "j"), ("gh", "ğ"), ("ts", "ц")]


def transliterate_foreign(name: str, digraphs: bool = True) -> str:
    """A foreign name's Russian spelling, from its Latin romanisation.
    `digraphs=False` for a Turkish name, written in Turkish letters (`ş`, `ç`,
    `ğ`), not English digraphs (`Oğuzhan` is `z` + `h`): only `h` -> `х`."""
    def one(tok: str) -> str:
        cap = tok[:1].isupper()
        low = tok.lower()
        if digraphs:
            low = low.replace("j", "c")                   # j -> дж, before `zh` -> ж
            for src, dst in _FOREIGN_DIGRAPHS:
                low = low.replace(src, dst)
            low = re.sub(r"ia$", "iya", low)              # Zhvania -> Жвания
        low = low.replace("h", "x")                       # h -> х (after the digraphs)
        out = _translit_token(low)
        return out[:1].upper() + out[1:] if cap else out
    return "".join(one(m.group()) if m.group()[:1].isalpha() else m.group()
                   for m in _TOKEN_RE.finditer(name))


def transliterate(text: str) -> str:
    """Azerbaijani-Latin -> Russian-Cyrillic, token by token. Non-letter runs
    (spaces, digits, punctuation, ``küç.`` dots) pass through untouched."""
    return "".join(
        _translit_token(m.group()) if m.group()[:1].isalpha() or
        m.group()[:1] in "ƏəÇçĞğIıİiÖöŞşÜü" else m.group()
        for m in _TOKEN_RE.finditer(text)
    )


# --------------------------------------------------------------------------- #
# city exonyms  (a character map cannot produce these)
# --------------------------------------------------------------------------- #
# Established Russian names for Azerbaijani places. Where a town's Russian name
# is just the transliteration it is omitted -- render_value() falls through to
# transliterate(). Keys are exactly as they appear in az.CITIES.
EXONYMS: dict[str, str] = {
    "Bakı": "Баку",
    "Gəncə": "Гянджа",
    "Sumqayıt": "Сумгаит",
    "Mingəçevir": "Мингечаур",
    "Şirvan": "Ширван",
    "Naxçıvan": "Нахичевань",
    "Şəki": "Шеки",
    "Yevlax": "Евлах",
    "Xankəndi": "Ханкенди",
    "Lənkəran": "Ленкорань",
    "Cəlilabad": "Джалилабад",
    "Şəmkir": "Шамкир",
    "Xaçmaz": "Хачмаз",
    "Ağcabədi": "Агджабеди",
    "Şamaxı": "Шемаха",
    "Bərdə": "Барда",
    "Salyan": "Сальяны",
    "Göyçay": "Гёйчай",
    "İmişli": "Имишли",
    "Ağdaş": "Агдаш",
    "Sabirabad": "Сабирабад",
    "Hacıqabul": "Гаджикабул",
    "Masallı": "Масаллы",
    "Siyəzən": "Сиазань",
    "İsmayıllı": "Исмаиллы",
    "Quba": "Губа",
    "Biləsuvar": "Билясувар",
    "Qazax": "Газах",
    "Zaqatala": "Загатала",
    "Saatlı": "Саатлы",
    "Tərtər": "Тертер",
    "Kürdəmir": "Кюрдамир",
    "Qusar": "Гусар",
    "Ucar": "Уджар",
    "Göygöl": "Гёйгёль",
    "Beyləqan": "Бейлаган",
    "Astara": "Астара",
    "Ağstafa": "Агстафа",
    "Qax": "Гах",
    "Tovuz": "Товуз",
    "Balakən": "Балакен",
    "Culfa": "Джульфа",
    "Gədəbəy": "Гедабек",
    "Zərdab": "Зардоб",
    "Daşkəsən": "Дашкесан",
    "Ordubad": "Ордубад",
    "Naftalan": "Нафталан",
    "Lerik": "Лерик",
    "Yardımlı": "Ярдымлы",
    "Horadiz": "Горадиз",
    "Oğuz": "Огуз",
    "Şərur": "Шарур",
    "Goranboy": "Геранбой",
    "Babək": "Бабек",
    "Xocavənd": "Ходжавенд",
    "Şahbuz": "Шахбуз",
    "Füzuli": "Физули",
    "Laçın": "Лачин",
    "Xızı": "Хызы",
    "Şuşa": "Шуша",
    "Cəbrayıl": "Джебраил",
    "Ağdam": "Агдам",
    "Kəlbəcər": "Кельбаджар",
    "Xocalı": "Ходжалы",
    "Qəbələ": "Габала",
    "Zəngilan": "Зангилан",
    "Qubadlı": "Кубатлы",
    "Əsgəran": "Аскеран",
    "Samux": "Самух",
    "Xırdalan": "Хырдалан",
    "Neftçala": "Нефтечала",
    "Ağsu": "Агсу",
    "Şabran": "Шабран",
}

# labels whose minted value is a Cyrillic-script word in the Russian carrier
NAME_LABELS = frozenset({"GIVENNAME", "SURNAME", "STREET"})

# Azerbaijani street types and their Russian equivalents.
#
# Azerbaijani puts the type last and Russian puts it first -- "Nizami küçəsi"
# is "улица Низами", not "Низами кючаси". Transliterating the type word leaves
# an Azerbaijani noun sitting in a Russian address, which is the one thing the
# carrier translation exists to avoid, and it lands in the entity value itself
# rather than the prose around it.
#
# Keys cover what the corpus actually emits: the full and abbreviated forms,
# the diacritic-stripped spellings the noise injector produces (kucesi,
# dongesi), and the locative "-də/-da" that an inflected mention carries.
# The abbreviation style is preserved, so "küç." becomes "ул." and not
# "улица".
_STREET_TYPES: dict[str, str] = {
    "küçəsi": "улица", "kücəsi": "улица", "kucesi": "улица",
    "kuçesi": "улица", "kucəsi": "улица", "küçəsində": "улица",
    "küç.": "ул.", "kuç.": "ул.", "kuc.": "ул.", "küç.də": "ул.",
    # the noise injector damages the abbreviation too
    "küçm.": "ул.", "kuçm.": "ул.", "kücm.": "ул.",
    "prospekti": "проспект", "prospektində": "проспект",
    "pr.": "пр.", "pr.da": "пр.", "pr.də": "пр.",
    "döngəsi": "переулок", "dongesi": "переулок", "dongəsi": "переулок",
    "döngəsində": "переулок",
    "meydanı": "площадь", "meydani": "площадь",
    "şosesi": "шоссе", "sosesi": "шоссе",
    # v4.2 native review: the standard spelling (`şosse` -> `şossesi`)
    "şossesi": "шоссе", "şossesində": "шоссе",
}

# The same types after our own transliteration, for repairing values that were
# already written the wrong way round.
_TRANSLITERATED_TYPES: dict[str, str] = {
    "кючаси": "улица", "кючеси": "улица", "кучаси": "улица",
    "кучеси": "улица", "кюч.": "ул.", "куч.": "ул.",
    "кючм.": "ул.", "кучм.": "ул.",
    "проспекти": "проспект", "проспектинде": "проспект",
    "пр.": "пр.",
    "дёнгаси": "переулок", "донгаси": "переулок", "дöнгаси": "переулок",
    "мейданы": "площадь", "шосеси": "шоссе", "шоссеси": "шоссе",
}


def street(minted: str) -> str:
    """Render an Azerbaijani street name as a Russian address.

    Type-first, and the type translated rather than transliterated. A value
    with no recognised type word is transliterated whole, which is right for
    the handful that are a bare name.
    """
    parts = minted.rsplit(" ", 1)
    if len(parts) == 2:
        stem, tail = parts
        ru_type = _STREET_TYPES.get(tail) or _STREET_TYPES.get(tail.lower())
        if ru_type:
            return f"{ru_type} {transliterate(stem)}"
    return transliterate(minted)


# Russian prepositions grouped by the case they govern. Only the ones that
# take a single case unambiguously are listed: "в"/"на"/"за"/"под" alternate
# between accusative and locative depending on meaning, and guessing wrong is
# worse than leaving the phrase alone.
_PREP_CASE: dict[str, str] = {}
for _case, _preps in {
    "gent": ("без", "близ", "вдоль", "вместо", "вне", "возле", "вокруг",
             "впереди", "для", "до", "из", "из-за", "из-под", "кроме", "мимо",
             "около", "от", "позади", "после", "против", "ради", "среди", "у",
             "насчёт", "насчет"),
    "datv": ("благодаря", "вопреки", "навстречу", "наперекор", "подобно",
             "согласно", "к", "ко"),
    "accs": ("про", "сквозь", "через", "спустя", "включая"),
    "ablt": ("над", "перед", "между", "меж", "с", "со"),
    "loct": ("при", "о", "об", "обо"),
}.items():
    for _p in _preps:
        _PREP_CASE[_p] = _case

_GOVERNING = re.compile(
    r"(?:^|[\s(«\"'\u2014-])(" + "|".join(sorted(_PREP_CASE, key=len, reverse=True))
    + r")\s+$", re.IGNORECASE)

# The Russian street types, as produced by street(). Only these are declined.
_TYPE_WORDS = {"улица", "проспект", "переулок", "площадь", "шоссе"}
_ABBREVIATED = {"ул.", "пр.", "пер.", "пл."}

_MORPH = None


def _morph():
    """pymorphy3, loaded once and only if a declension is actually wanted."""
    global _MORPH
    if _MORPH is None:
        import pymorphy3
        _MORPH = pymorphy3.MorphAnalyzer()
    return _MORPH


# "в" and "на" alternate between accusative and locative in general, so they
# are left out of _PREP_CASE -- but before a STREET they are locative in
# practice ("на улице Низами", "в переулке Мирзагышлаг"). 192 street mentions
# in val and test sit behind one, more than every unambiguous preposition
# combined, and "в улица Баллабур" is the worst-reading case of all.
_LOCATIVE_BEFORE_STREET = re.compile(
    r"(?:^|[\s(«\"'—-])(на|в|во)\s+$", re.IGNORECASE)


def governing_case(text_before: str, label: str | None = None) -> str | None:
    """The case demanded by a preposition immediately before a span."""
    m = _GOVERNING.search(text_before)
    if m:
        return _PREP_CASE.get(m.group(1).lower())
    if label == "STREET" and _LOCATIVE_BEFORE_STREET.search(text_before):
        return "loct"
    return None


def decline_street(value: str, case: str) -> str:
    """Put a street value into `case` by declining its TYPE WORD only.

    "от переулок Мюбариз" reads as broken Russian; "от переулка Мюбариз" does
    not. The type word is an ordinary Russian noun and pymorphy3 handles it
    exactly -- переулок -> переулка, улица -> улицы, площадь -> площади.

    The NAME is deliberately left in the nominative, and that is not laziness.
    pymorphy3 has no entry for a transliterated Azerbaijani name and guesses a
    paradigm from the ending, usually wrongly: it reads "Гуйчу" as a verb and
    offers "гуйчившего", "Сабзиханым" as an adjective and offers
    "сабзиханого", and it lowercases what it returns. Those values are the
    spans the model trains on, so corrupting them is far worse than an
    undeclined name -- which is ordinary in Russian for foreign names anyway,
    and what the multilingual spec accepts for v1.

    An abbreviated type ("ул.", "пр.") does not decline in writing and is
    returned unchanged.
    """
    parts = value.split(" ", 1)
    if len(parts) != 2:
        return value
    head, rest = parts
    if head in _ABBREVIATED:
        return value
    if head.lower() not in _TYPE_WORDS:
        return value
    parsed = _morph().parse(head.lower())
    if not parsed:
        return value
    inflected = parsed[0].inflect({case})
    if inflected is None:
        return value
    return f"{inflected.word} {rest}"


def restyle_street(value: str) -> str | None:
    """Repair a street value already written type-last in transliteration.

    Returns the corrected form, or None if the value needs no change. Used to
    fix the documents written before ``street()`` existed, without
    regenerating them -- the name is already correctly transliterated and only
    the type word is wrong and in the wrong place.
    """
    parts = value.rsplit(" ", 1)
    if len(parts) != 2:
        return None
    stem, tail = parts
    ru_type = (_TRANSLITERATED_TYPES.get(tail)
               or _TRANSLITERATED_TYPES.get(tail.lower()))
    if not ru_type:
        return None
    return f"{ru_type} {stem}"


def render_value(label: str, minted: str, rng: random.Random | None = None) -> str:
    """Orthography hook: how a freshly minted Azerbaijani value is written in
    Russian carrier text. Structured values (phones, emails, IBANs, all
    ``AZ_*`` identifiers, IPs, MACs, URLs, cards, tokens) are returned
    unchanged in every language.
    """
    if label == "CITY":
        return EXONYMS.get(minted) or transliterate(minted)
    if label == "STREET":
        return street(minted)
    if label in NAME_LABELS:
        return transliterate(minted)
    return minted


# Script tags for Simurg(expected_scripts=...). SIMURG's names are lower-case
# ("latin", "cyrillic"); "latin" already covers ASCII digits, punctuation, the
# ⟦N⟧ sentinels and structured tokens/URLs, so no third entry is needed.
# Passing capitalised names makes SIMURG treat Cyrillic as foreign and mark
# every clean Russian document `corrupt` -- verified against simurg 1.0.3.
EXPECTED_SCRIPTS = ("cyrillic", "latin")


# --------------------------------------------------------------------------- #
# locale object
# --------------------------------------------------------------------------- #
LOCALE = Locale(
    code="ru", name="Russian",
    # Borrowed from `az` -- see module docstring. Not for direct sampling.
    first_names_m=az.FIRST_M, first_names_f=az.FIRST_F,
    surname_stems=az.SURNAME_STEMS, surname_builder=az.surname,
    months=MONTHS, weekdays=WEEKDAYS, date_builder=date,
    distinctive_chars="",
)
