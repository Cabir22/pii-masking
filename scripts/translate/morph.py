"""What a translated document must keep from the source person, place and date
(D-56c, the TR/RU translation check).

  * gender (item 1): a person's given name and surname are minted with the
    SOURCE person's gender, the same for every name of one person;
  * case (item 2): an Azerbaijani case ending on a name or place span (D-9:
    the span is the whole inflected word, `Zərdabda`) becomes a case tag after
    its placeholder (`⟦0⟧{LOC}`); the model writes the tag the target sentence
    needs, and splice inflects the minted value (`Bakü'de`, `Наримана`); the
    span is the whole inflected form (D-56d);
  * year (item 3): a minted DATE keeps the source DATE's year;
  * masks (item 10): `****0696` takes the new value's last digits;
  * year words (item 6): no `. yıl`, `-ci yıl`, `год` after a full date.

Everything here is a pure function of its arguments; the runners call it.
"""
from __future__ import annotations

import re

from piigen.locales import az as AZ

# --------------------------------------------------------------------------- #
# Lower-casing the Azerbaijani / Turkish way (`I` -> `ı`, `İ` -> `i`)
# --------------------------------------------------------------------------- #

def az_lower(s: str) -> str:
    return s.replace("I", "ı").replace("İ", "i").lower()


def tr_upper(s: str) -> str:
    return s.replace("i", "İ").replace("ı", "I").upper()


# --------------------------------------------------------------------------- #
# Gender (item 1)
# --------------------------------------------------------------------------- #
_MALE = frozenset(az_lower(n) for n in AZ.FIRST_M)
_FEMALE = frozenset(az_lower(n) for n in AZ.FIRST_F)
_SURNAME_F = re.compile(r"(ova|eva|yeva|ina|ına|skaya)$")
_SURNAME_M = re.compile(r"(ov|ev|yev|in|ın|ski|sky)$")
_FEMALE_AFTER = re.compile(r"^\s*(xanım|xanımın|xanıma|xanımı|xanımdan|qızı|qızının|qızına)\b", re.I)
_MALE_AFTER = re.compile(r"^\s*(bəy|bəyin|bəyə|bəyi|bəydən|oğlu|oğlunun|oğluna|müəllim)\b", re.I)


def given_gender(name: str) -> str | None:
    """'f', 'm' or None (both pools, or neither)."""
    k = az_lower(name)
    m, f = k in _MALE, k in _FEMALE
    return "m" if m and not f else "f" if f and not m else None


def surname_gender(name: str) -> str | None:
    k = az_lower(name)
    if _SURNAME_F.search(k):
        return "f"
    if _SURNAME_M.search(k):
        return "m"
    return None


def person_genders(text: str, entities: list[dict], stems: list[str]) -> list[str | None]:
    """The gender of the person each GIVENNAME/SURNAME entity belongs to (None
    for other labels or when it cannot be told). A given name and a surname
    separated only by spaces are one person; a person's gender comes from the
    given-name pools, else the surname ending, else `xanım`/`qızı` or
    `bəy`/`oğlu` right after the name. A given name right before
    `oğlu`/`qızı` is the father's: always male, and not the person's."""
    order = sorted(range(len(entities)), key=lambda i: entities[i]["start"])
    out: list[str | None] = [None] * len(entities)
    people: list[list[int]] = []
    for i in order:
        e = entities[i]
        if e["label"] not in ("GIVENNAME", "SURNAME"):
            continue
        if people:
            j = people[-1][-1]
            gap = text[entities[j]["end"]:e["start"]]
            if gap.strip() == "" and len(gap) <= 2:
                people[-1].append(i)
                continue
        people.append([i])
    for group in people:
        after = text[entities[group[-1]]["end"]:entities[group[-1]]["end"] + 12]
        father = re.match(r"^\s*(oğlu|qızı)\b", after, re.I)
        members = group
        if father and len(group) >= 2 and entities[group[-1]]["label"] == "GIVENNAME":
            out[group[-1]] = "m"                 # the father's given name
            members = group[:-1]
        g = None
        for i in members:
            if entities[i]["label"] == "GIVENNAME":
                g = g or given_gender(stems[i])
        for i in members:
            if entities[i]["label"] == "SURNAME":
                g = g or surname_gender(stems[i])
        if g is None:
            if father:
                g = "m" if father.group(1).lower() == "oğlu" else "f"
            elif _FEMALE_AFTER.match(after):
                g = "f"
            elif _MALE_AFTER.match(after):
                g = "m"
        for i in members:
            out[i] = g
    return out


# --------------------------------------------------------------------------- #
# Case (item 2): the source span's Azerbaijani case
# --------------------------------------------------------------------------- #
CASES = ("GEN", "DAT", "ACC", "LOC", "ABL", "INS", "REL", "COP")
TR_TAGS = frozenset(CASES)
RU_TAGS = frozenset(("GEN", "DAT", "ACC", "INS", "PREP"))
INFLECTED_LABELS = frozenset(("GIVENNAME", "SURNAME", "CITY", "STREET"))

# (ending, case), longest first; endings after a vowel and after a consonant
_AZ_ENDINGS = sorted([
    ("ndakı", "REL"), ("ndəki", "REL"), ("dakı", "REL"), ("dəki", "REL"),
    ("ndan", "ABL"), ("ndən", "ABL"), ("dan", "ABL"), ("dən", "ABL"),
    ("nda", "LOC"), ("ndə", "LOC"), ("da", "LOC"), ("də", "LOC"),
    ("nın", "GEN"), ("nin", "GEN"), ("nun", "GEN"), ("nün", "GEN"),
    ("ın", "GEN"), ("in", "GEN"), ("un", "GEN"), ("ün", "GEN"),
    ("yla", "INS"), ("ylə", "INS"), ("la", "INS"), ("lə", "INS"),
    ("ya", "DAT"), ("yə", "DAT"), ("na", "DAT"), ("nə", "DAT"), ("a", "DAT"), ("ə", "DAT"),
    ("nı", "ACC"), ("ni", "ACC"), ("nu", "ACC"), ("nü", "ACC"),
    ("ı", "ACC"), ("i", "ACC"), ("u", "ACC"), ("ü", "ACC"),
    ("dır", "COP"), ("dir", "COP"), ("dur", "COP"), ("dür", "COP"),
], key=lambda x: -len(x[0]))
_STREET_TYPES_AZ = ("küçəsi", "prospekti", "döngəsi", "şossesi", "meydanı", "bulvarı")
_CITIES = frozenset(az_lower(c) for c in list(AZ.CITIES) + list(AZ.SETTLEMENTS))
_VOWELS_AZ = "aıoueəiöü"


def _stem_ok(label: str, stem: str) -> bool:
    k = az_lower(stem)
    if len(k) < 2:
        return False
    if label == "GIVENNAME":
        return k in _MALE or k in _FEMALE
    if label == "SURNAME":
        # not `-in`/`-ın` here: that is the Azerbaijani genitive (`Haşımovanın`)
        return len(k) >= 4 and bool(re.search(r"(ov|ova|ev|eva|yev|yeva|lı|li|lu|lü|zadə|zade|ski|skaya|enko)$", k))
    if label == "CITY":
        return k in _CITIES
    return False


def source_case(label: str, value: str) -> tuple[str, str | None]:
    """(bare form, case) of a source span; case None when the span is not
    inflected or the ending cannot be told safely. Only accepted when what
    is left is a known given name, a surname shape, a known place, or a
    street whose type word took the ending (`küçəsində`)."""
    if label not in INFLECTED_LABELS:
        return value, None
    v = value
    if label != "STREET" and _stem_ok(label, v):
        return value, None                        # the whole span is itself a name or place
    # an apostrophe or hyphen before the ending (`Bakı'da`, `Səməd-ə`)
    m = re.match(r"^(.*\w)['’-]([a-zəıöüçşğ]{1,5})$", v, re.I)
    if m:
        stem, end = m.group(1), az_lower(m.group(2))
        case = dict(_AZ_ENDINGS).get(end)
        if case and (label == "STREET" or _stem_ok(label, stem)):
            return stem, case
        return value, None
    low = az_lower(v)
    if label == "STREET":
        for t in _STREET_TYPES_AZ:
            i = low.rfind(t)
            if i > 0 and low[i - 1] == " ":
                rest = low[i + len(t):]
                if not rest:
                    return value, None
                case = dict(_AZ_ENDINGS).get(rest) or (dict(_AZ_ENDINGS).get(rest[1:]) if rest.startswith("n") else None)
                return (value[:i + len(t)], case) if case else (value, None)
        return value, None
    for end, case in _AZ_ENDINGS:
        if low.endswith(end) and len(low) > len(end) + 1:
            stem = v[:-len(end)]
            k = az_lower(stem)
            # the buffer consonant goes with a vowel-final stem only
            if end[0] in "ny" and len(end) >= 2 and end not in ("nda", "ndə", "ndan", "ndən", "ndakı", "ndəki"):
                if k[-1] not in _VOWELS_AZ:
                    continue
            elif end in ("ın", "in", "un", "ün", "ı", "i", "u", "ü", "a", "ə") and k[-1] in _VOWELS_AZ:
                continue
            if _stem_ok(label, stem):
                return stem, case
    return value, None


# --------------------------------------------------------------------------- #
# Turkish inflection: apostrophe + a harmonised ending
# --------------------------------------------------------------------------- #
# M3 (re-check): `ə`, kept in names in 12% of documents
# (TR_KEEP_SCHWA_RATE), is a front vowel for harmony and a vowel for the
# buffer `n`/`y` (`Fərayət'e`, `Nadiyə'nin`, `Nadiyə'ye`)
_TR_VOWELS = "aeıioöuüə"
_TR_HARD = "fstkçşhp"
_TR_POSSESSIVE_TYPES = ("Caddesi", "Sokağı", "Bulvarı", "Meydanı", "Yolu")


def tr_inflect(value: str, case: str) -> str:
    """`Bakü` + LOC -> `Bakü'de`; `Köçeriyeva` + GEN -> `Köçeriyeva'nın`;
    `Nizami Caddesi` + LOC -> `Nizami Caddesi'nde`. An abbreviated street
    type (`Cad.`) or an unknown case is returned unchanged."""
    if case not in TR_TAGS or not value or value.endswith("."):
        return value
    word = value.split()[-1]
    w = az_lower(word)
    vowels = [c for c in w if c in _TR_VOWELS]
    last = vowels[-1] if vowels else "e"
    two = "a" if last in "aıou" else "e"
    four = {"a": "ı", "ı": "ı", "o": "u", "u": "u", "e": "i", "i": "i", "ö": "ü", "ü": "ü", "ə": "i"}[last]
    possessive = word in _TR_POSSESSIVE_TYPES
    ev = w[-1] in _TR_VOWELS
    d = "t" if w[-1] in _TR_HARD else "d"
    if possessive:
        suffix = {"GEN": f"n{four}n", "DAT": f"n{two}", "ACC": f"n{four}", "LOC": f"nd{two}",
                  "ABL": f"nd{two}n", "INS": f"yl{two}", "REL": f"nd{two}ki", "COP": f"d{four}r"}[case]
    else:
        suffix = {"GEN": f"{'n' if ev else ''}{four}n", "DAT": f"{'y' if ev else ''}{two}",
                  "ACC": f"{'y' if ev else ''}{four}", "LOC": f"{d}{two}", "ABL": f"{d}{two}n",
                  "INS": f"{'y' if ev else ''}l{two}", "REL": f"{d}{two}ki", "COP": f"{d}{four}r"}[case]
    if word.isupper() and len(word) > 1:
        suffix = tr_upper(suffix)
    return f"{value}'{suffix}"


# --------------------------------------------------------------------------- #
# Russian declension: an explicit ending table, no guessing
# --------------------------------------------------------------------------- #
_RU_SIBILANT = "жшщчц"
_RU_VELAR_SIB = "гкхжшщч"
_RU_STREET_CASE = {"GEN": "gent", "DAT": "datv", "ACC": "accs", "INS": "ablt", "PREP": "loct"}


def ru_decline(value: str, label: str, case: str, female: bool | None = None) -> str:
    """The Russian form of a minted name or place in `case`. Only the shapes
    the table covers are declined (`-ов`/`-ова`/`-ин`/`-ина` surnames; names
    and places ending in `-а`, `-я`, `-й`, `-ь` or a consonant); anything else
    is left as it is, which is ordinary Russian for a foreign name. Streets
    decline their type word (`decline_street`)."""
    if case not in RU_TAGS or not value or " " in value.strip() and label != "STREET":
        return value
    if label == "STREET":
        from piigen.locales.ru import decline_street
        return decline_street(value, _RU_STREET_CASE[case])
    w = value
    low = w.lower()
    person = label in ("GIVENNAME", "SURNAME")
    if label == "SURNAME":
        if re.search(r"(ова|ева|ёва|ина|ына)$", low):
            return w[:-1] + ("у" if case == "ACC" else "ой")
        if re.search(r"(ов|ев|ёв|ин|ын)$", low):
            return w + {"GEN": "а", "DAT": "у", "ACC": "а", "INS": "ым", "PREP": "е"}[case]
        return w
    last, prev = low[-1], low[-2] if len(low) > 1 else ""
    if last == "а":
        return w[:-1] + {"GEN": "и" if prev in _RU_VELAR_SIB else "ы", "DAT": "е", "ACC": "у",
                         "INS": "ей" if prev in _RU_SIBILANT else "ой", "PREP": "е"}[case]
    if last == "я":
        ia = low.endswith("ия")
        return w[:-1] + {"GEN": "и", "DAT": "и" if ia else "е", "ACC": "ю", "INS": "ей",
                         "PREP": "и" if ia else "е"}[case]
    if last == "й":
        return w[:-1] + {"GEN": "я", "DAT": "ю", "ACC": "я" if person else "й", "INS": "ем",
                         "PREP": "е"}[case]
    if last == "ь":
        if female:
            return w[:-1] + {"GEN": "и", "DAT": "и", "ACC": "ь", "INS": "ью", "PREP": "и"}[case]
        return w[:-1] + {"GEN": "я", "DAT": "ю", "ACC": "я" if person else "ь", "INS": "ем",
                         "PREP": "е"}[case]
    if last in "бвгджзклмнпрстфхцчшщ":
        if label == "GIVENNAME" and female:
            return w                              # Айсел, Нигяр: not declined
        return w + {"GEN": "а", "DAT": "у", "ACC": "а" if person else "", "PREP": "е",
                    "INS": "ем" if last in _RU_SIBILANT else "ом"}[case]
    return w                                      # Баку, Шеки, -заде, -ли


# --------------------------------------------------------------------------- #
# Tags in the text the model returns
# --------------------------------------------------------------------------- #
# braces optional: the model sometimes writes the tag bare (`⟦0⟧LOC`)
TAG_AFTER_SLOT = re.compile(r"⟦(\d+)⟧\{?(GEN|DAT|ACC|LOC|ABL|INS|REL|COP|PREP)\}?(?![A-Za-z])")
STRAY_TAG = re.compile(r"\{(?:GEN|DAT|ACC|LOC|ABL|INS|REL|COP|PREP|NOM)\}")


def take_tags(text: str) -> tuple[str, dict[int, str]]:
    """Strip each `{TAG}` written right after a placeholder; slot -> tag."""
    tags: dict[int, str] = {}

    def keep(m: re.Match) -> str:
        tags[int(m.group(1))] = m.group(2)
        return f"⟦{m.group(1)}⟧"
    return TAG_AFTER_SLOT.sub(keep, text), tags


# The Turkish ending a model glued on itself (`⟦0⟧ye`, `⟦0⟧'nin`), read back as
# its case: it is removed and written again with the apostrophe and harmony of
# the minted value (`Şirinhan` + DAT -> `Şirinhan'a`, not `Şirinhanye`)
_TR_OWN_SUFFIX = sorted([
    (s, c) for c, forms in {
        "REL": "daki deki taki teki ndaki ndeki",
        "ABL": "dan den tan ten ndan nden",
        "LOC": "da de ta te nda nde",
        "GEN": "nın nin nun nün ın in un ün",
        "INS": "yla yle la le",
        "COP": "dır dir dur dür tır tir tur tür",
        "DAT": "ya ye na ne a e",
        "ACC": "yı yi yu yü nı ni nu nü ı i u ü",
    }.items() for s in forms.split()], key=lambda x: -len(x[0]))
_TR_OWN = re.compile(r"⟦(\d+)⟧'?([a-zçğıöşü]{1,5})(?![a-zçğıöşüA-Za-z])")


def take_tr_suffixes(text: str, inflectable: set[int], tags: dict[int, str]) -> str:
    """For the name/place slots in `inflectable`: an ending written straight
    after the placeholder becomes that slot's tag (unless it has one) and is
    removed. Other slots keep what the model wrote (`⟦3⟧'te` after a time)."""
    def fix(m: re.Match) -> str:
        slot, suf = int(m.group(1)), m.group(2)
        if slot not in inflectable:
            return m.group(0)
        case = next((c for s, c in _TR_OWN_SUFFIX if s == suf), None)
        if case is None:
            return m.group(0)
        tags.setdefault(slot, case)
        return f"⟦{slot}⟧"
    return _TR_OWN.sub(fix, text)


_AZ_ACCORDING = re.compile(r"əsas(?:ən|ında)|uyğun olaraq|müvafiq olaraq|uyğun\b", re.I)
_TR_UYARINCA = re.compile(r"\buyarınca\b")


def tr_uyarinca_edits(source_text: str, text: str, entities: list[dict]) -> list[tuple[int, int, str]]:
    """M6 (re-check): `üzrə` is never `uyarınca` ("in accordance
    with"); the prompt line alone left 5 of 6 in the sample. When the source
    says "in accordance with" nowhere (`əsasən`, `əsasında`, `uyğun olaraq`,
    `müvafiq olaraq`), every `uyarınca` outside the spans becomes `kapsamında`
    (`sipariş kapsamında`, `dava kapsamında`). When it does, the text is left
    as it is: which one is which can't be told."""
    if _AZ_ACCORDING.search(source_text):
        return []
    return [(m.start(), m.end(), "kapsamında") for m in _TR_UYARINCA.finditer(text)
            if not any(e["start"] <= m.start() < e["end"] for e in entities)]


def drop_gen_before_tarafindan(text: str, tags: dict[int, str]) -> None:
    """M6 (re-check): Turkish takes the bare name before
    `tarafından` (`Memmedhanov tarafından`, never `Memmedhanov'un
    tarafından`); a genitive tag there, the model's or read back from its own
    ending, is dropped."""
    for slot, tag in list(tags.items()):
        if tag == "GEN" and re.search(rf"⟦{slot}⟧\s+tarafından", text):
            del tags[slot]


_PERSON_RUN = re.compile(r"⟦(\d+)⟧(?: ⟦(\d+)⟧)+")


def spread_person_tags(text: str, tags: dict[int, str], person_slots: set[int], lang: str) -> None:
    """A full name written as adjacent placeholders (`⟦7⟧ ⟦8⟧`) takes one
    case. Russian declines every part (`Рашада Мамедова`), so a tag on any
    part applies to all; Turkish puts the ending on the last word only
    (`Reşad Memmedov'un`), so the tag moves there. The model sometimes tags
    the other part than the source did."""
    for m in _PERSON_RUN.finditer(text):
        run = [int(x) for x in re.findall(r"⟦(\d+)⟧", m.group(0))]
        if not all(s in person_slots for s in run):
            continue
        tag = next((tags[s] for s in reversed(run) if s in tags), None)
        if tag is None:
            continue
        for s in run:
            tags.pop(s, None)
        if lang == "ru":
            for s in run:
                tags[s] = tag
        else:
            tags[run[-1]] = tag


# --------------------------------------------------------------------------- #
# Year (item 3)
# --------------------------------------------------------------------------- #
def source_year(value: str) -> int | None:
    """The year a source DATE names: 4 digits 1900-2099, else a final
    2-digit year (`21.02.56`) read as 19xx above 30, 20xx otherwise."""
    m = re.search(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)", value)
    if m:
        return int(m.group(1))
    m = re.search(r"[./-](\d{2})$", value.strip())
    if m:
        yy = int(m.group(1))
        return 2000 + yy if yy <= 30 else 1900 + yy
    return None


_AZ_MONTHS = {m: i + 1 for i, m in enumerate(AZ.MONTHS)}
_AZ_MONTHS.update({m[:3]: i + 1 for i, m in enumerate(AZ.MONTHS)})


def _two_digit_year(yy: int) -> int:
    return 2000 + yy if yy <= 30 else 1900 + yy


def parse_full_date(value: str) -> tuple[int, int, int] | None:
    """(day, month, year) of a source DATE that names all three -- numeric
    (`22.05.2016`, `2016-05-22`, `22/05/16`) or worded (`22 may 2016`,
    `22 May 2016-cı il`) -- else None."""
    v = az_lower(value)
    m = re.search(r"(?<!\d)(\d{4})[-./](\d{1,2})[-./](\d{1,2})(?!\d)", v)
    if m:
        d, mo, y = int(m.group(3)), int(m.group(2)), int(m.group(1))
    else:
        m = re.search(r"(?<!\d)(\d{1,2})[-./](\d{1,2})[-./](\d{4}|\d{2})(?!\d)", v)
        if m:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            y = y if y > 99 else _two_digit_year(y)
        else:
            day = re.search(r"(?<!\d)(\d{1,2})(?!\d)", v)
            year = re.search(r"(?<!\d)(\d{4})(?!\d)", v)
            mon = next((_AZ_MONTHS[w.rstrip(".")] for w in re.findall(r"[^\W\d_]+\.?", v)
                        if w.rstrip(".") in _AZ_MONTHS), None)
            if not (day and year and mon):
                return None
            d, mo, y = int(day.group(1)), mon, int(year.group(1))
    try:
        import datetime
        datetime.date(y, mo, d)
    except ValueError:
        return None
    return d, mo, y


def _numeric_dates(text: str) -> set[tuple[int, int, int]]:
    """Every numeric full date in a text, labelled or not (a log line's stamp)."""
    out = set()
    for m in re.finditer(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)", text):
        out.add((int(m.group(3)), int(m.group(2)), int(m.group(1))))
    for m in re.finditer(r"(?<!\d)(\d{2})[./-](\d{2})[./-](\d{4})(?!\d)", text):
        out.add((int(m.group(1)), int(m.group(2)), int(m.group(3))))
    return out


def source_date(text: str, start: int, end: int) -> int | tuple[int, int, int] | None:
    """What a minted DATE must keep of the source DATE at text[start:end]:
    the whole date (day, month, year) when the text repeats it in a numeric
    form elsewhere (M4, the re-check: a log line `[2016-05-22 14:02]`
    under `Tarix: 22.05.2016` -- the new date must not contradict it), else
    its year (D-56c item 3), else None."""
    v = text[start:end]
    full = parse_full_date(v)
    if full and full in _numeric_dates(text[:start] + " " + text[end:]):
        return full
    return source_year(v)


# --------------------------------------------------------------------------- #
# Masks (item 10)
# --------------------------------------------------------------------------- #
_MASK = re.compile(r"(?:[*xX•·]{2,}|…|\.{3})[ -]?(\d{2,4})(?!\d)")


def mask_edits(source_text: str, source_values: list[str], new_values: list[str]) -> dict[str, str]:
    """mask -> rewritten mask, for every mask in the source whose digits are
    the last digits of a labelled source value; it takes the new value's."""
    out: dict[str, str] = {}
    for m in _MASK.finditer(source_text):
        digits = m.group(1)
        for old, new in zip(source_values, new_values):
            od, nd = re.sub(r"\D", "", old), re.sub(r"\D", "", new)
            if len(od) > len(digits) and od.endswith(digits) and len(nd) >= len(digits):
                whole = m.group(0)
                out[whole] = whole[:-len(digits)] + nd[-len(digits):]
                break
    return out


def apply_text_edits(text: str, entities: list[dict], edits: list[tuple[int, int, str]]) -> tuple[str, list[dict]]:
    """Replace text[a:b] with s for each (a, b, s) outside every span, and
    shift the spans after it. Edits must not overlap one another or a span."""
    for a, b, s in sorted(edits, reverse=True):
        if any(a < e["end"] and e["start"] < b for e in entities):
            continue
        text = text[:a] + s + text[b:]
        delta = len(s) - (b - a)
        for e in entities:
            if e["start"] >= b:
                e["start"] += delta
                e["end"] += delta
    return text, entities


def apply_masks(text: str, entities: list[dict], masks: dict[str, str]) -> tuple[str, list[dict]]:
    edits = []
    for old, new in masks.items():
        for m in re.finditer(re.escape(old), text):
            edits.append((m.start(), m.end(), new))
    return apply_text_edits(text, entities, edits)


# --------------------------------------------------------------------------- #
# Year words after a full DATE (item 6)
# --------------------------------------------------------------------------- #
# M5 (re-check) adds ` yılında`/`yılına`/`yılının` (written as
# `tarihinde` etc., the full date's own noun), the apostrophe `'ci yıl`, and
# `. Yıl` in any case
_TR_YEAR_WORD = re.compile(r"^(?:\. ?yıl\b|\. ?(?:Yıl|YIL)(?=[ \t]*(?:\n|$))"
                           r"|[-'’]?(?:ci|cı|cu|cü|nci|ncı|ncu|ncü)(?: yıl(?:ı)?)?\b| yılı\b(?!n)"
                           r"| yıl(?![a-zçğıöşü])(?! (?:önce|sonra|içinde|boyunca)))")
_TR_YEAR_CASE = re.compile(r"^ yıl(ında|ına|ının)\b")
_TR_YEAR_CASE_NOUN = {"ında": " tarihinde", "ına": " tarihine", "ının": " tarihinin"}
# ... and Russian `-го года` after a numeric date
_RU_YEAR_NUMERIC = re.compile(r"^(?:-й год\b|-го года\b| год\b| г\.)")
_RU_YEAR_WORDED = re.compile(r"^(?:-й)? год\b")


def _full_date(v: str) -> bool:
    """Day, month and year: a numeric date with two separators, or a worded one."""
    return bool(re.search(r"\d{1,4}[./-]\d{1,2}[./-]\d{2,4}", v)
                or (re.search(r"\b\d{1,2}\b", v) and re.search(r"(19|20)\d{2}", v) and re.search(r"[^\W\d_]{3,}", v)))


def year_word_edits(text: str, entities: list[dict], lang: str) -> list[tuple[int, int, str]]:
    edits = []
    for e in entities:
        if e["label"] != "DATE":
            continue
        v = text[e["start"]:e["end"]]
        if not _full_date(v):
            continue
        rest = text[e["end"]:e["end"] + 12]
        if lang == "tr":
            m = _TR_YEAR_WORD.match(rest)
            if m:
                edits.append((e["end"], e["end"] + m.end(), ""))
            m = _TR_YEAR_CASE.match(rest)
            if m:
                # after a field label (`Tarih: … yılında`) the word goes; in a
                # sentence it becomes the full date's noun (`… tarihinde`)
                line = text[text.rfind("\n", 0, e["start"]) + 1:e["start"]]
                noun = "" if re.search(r":\s*$", line) else _TR_YEAR_CASE_NOUN[m.group(1)]
                edits.append((e["end"], e["end"] + m.end(), noun))
        elif lang == "ru":
            worded = bool(re.search(r"[а-яё]{3,}", v, re.I))
            if worded:
                m = _RU_YEAR_WORDED.match(rest)
                if m:
                    edits.append((e["end"], e["end"] + m.end(), " года"))
            else:
                m = _RU_YEAR_NUMERIC.match(rest)
                if m:
                    edits.append((e["end"], e["end"] + m.end(), ""))
    return edits
