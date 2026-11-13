"""Azerbaijani locale pack.

Notes that matter for realism:
  * Surnames take -ov/-ova, -yev/-yeva, -li/-lı, -zadə. Gender marking is real
    and the feminine form is not optional.
  * The national ID (FİN) is 7 alphanumeric characters, uppercase.
  * Plates are `NN-LL-NNN` (region-letters-serial); Baku is 10, 90, 99.
  * Mobile operator codes: 50/51 (Azercell), 55/99 (Bakcell), 70/77 (Nar),
    10 (Azercell). Landline Baku is 012.
  * Azerbaijani is agglutinative with vowel harmony, so phrases are stored
    pre-inflected rather than composed from stems -- composing them naively
    produces text that is subtly wrong in a way a native speaker notices
    immediately.
"""

from __future__ import annotations

import os
import random
import string
from datetime import date as _date

from .base import ForeignNames, Locale, PhraseBank

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def _load_names(filename: str) -> list[str]:
    """One name per line from locales/data/<filename>.

    2026-08-25: replaced the earlier ~250-name hand-authored pool (itself an
    expansion of an original ~110-name pool) with two real external datasets,
    both supplied directly by the user, not generated from memory: a general
    name-registry export (~15,000 given names) and the Azerbaijan Ministry of
    Justice's official names dataset (opendata.az), merged and deduplicated
    -- 8,593 male / 6,881 female given names. The audit that motivated the
    first expansion found 38-46x mean value reuse at 24k documents, projected
    far worse (~280x) at the 100k target; the hand-authored expansion only
    got to ~112x. This clears the ~12,000-name threshold the math actually
    requires for GIVENNAME to reach healthy reuse at 100k scale (measured:
    4.08x). The prior hand-authored names are merged in, not discarded --
    most were already covered by these datasets, but a genuine few were not.
    """
    path = os.path.join(_DATA_DIR, filename)
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def _load_weighted(filename: str) -> tuple[list[str], list[int]]:
    """(names, weights) from tab-separated 'name<TAB>weight' lines."""
    path = os.path.join(_DATA_DIR, filename)
    names, weights = [], []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            name, weight = line.rsplit("\t", 1)
            names.append(name)
            weights.append(int(weight))
    return names, weights


# 2026-08-29 audit (F7): the two given-name files come from a real registry
# export, and a registry contains every string anyone was ever registered
# under -- including strings that are ordinarily a place or a common noun.
# Sampling those as GIVENNAME made the generator write semantically broken
# documents ("Ad: Şamaxı", "Hörmətli Dövlət", "şəxs Məhkəmə Xanbabalı olaraq
# göstərilir") and then annotate them correctly, so no span-level repair can
# fix them -- the TEXT is wrong, not the label. 111 mentions across 62 live
# documents came from these entries.
#
# The list is deliberately narrow. Azerbaijani given names are very often
# ordinary vocabulary -- Sevinc (joy), Aydın (clear), Gözəl (beautiful),
# Ümid (hope), Şirin (sweet), Sadiq (loyal), Bulud (cloud) are all real
# names -- so a frequency cutoff would delete hundreds of legitimate names
# and cause a far worse defect than the one it fixes. Only entries that are
# not personal names in Azerbaijani at all are listed here.
#
# City names that ARE genuine personal names are deliberately kept:
# Laçın, Cəbrayıl, Babək, Füzuli, Şirvan, Oğuz, Sahil. Likewise Cümə, which
# is a real male name as well as "Friday".
#
# Two entries are judgment calls worth a native speaker's review, listed
# here because in this corpus they occur thousands of times as ordinary
# words and a handful of times as names: Qiymət (price / also a female name)
# and Dövlət (state, wealth / also a male name).
NOT_PERSONAL_NAMES = frozenset({
    # --- place names only: rayon and city names with no personal use ------
    "Bakı", "Gəncə", "Lənkəran", "Naxçıvan", "Ordubad", "Quba", "Salyan",
    "Samux", "Tovuz", "Ucar", "Xocalı", "Xudat", "Zərdab", "Şahbuz",
    "Şamaxı", "Şuşa", "Şəki", "Şəmkir", "Şərur",
    # --- calendar words ---------------------------------------------------
    "Yanvar", "Fevral", "Aprel", "Avqust", "Oktyabr", "Noyabr", "Dekabr",
    "Bazar",
    # --- administrative and document vocabulary ---------------------------
    "Cəmi", "Dövlət", "Məhkəmə", "Məlumat", "Müraciət", "Qiymət", "Rəsmi",
    "Saat", "Salam", "Sifariş", "Tarix", "Təsdiq", "Təşəkkür", "Vəzifə",
    "Xidmət", "Yüksək", "Zəhmət", "Ünvan", "Şikayət", "Şəxsiyyət", "Əlavə",
    "Əvvəl",
})


def _drop_non_names(names: list[str]) -> list[str]:
    return [n for n in names if n not in NOT_PERSONAL_NAMES]


FIRST_M = _drop_non_names(_load_names("az_first_names_m.txt"))
FIRST_F = _drop_non_names(_load_names("az_first_names_f.txt"))
# 2026-08-25: same real-dataset treatment as FIRST_M/FIRST_F -- stems
# extracted from the Azerbaijan Ministry of Justice's official names dataset
# (opendata.az) by stripping known surname suffixes (-ov/-ova, -yev/-yeva,
# -li/-lı, -zadə, -oğlu, ...) off each registered surname, e.g. "Abbasov"
# -> "Abbas". Combined with the existing suffix-builder below, this is what
# actually produces the realized surname (which gender-marks correctly and
# varies suffix style), not the raw MoJ surname string itself. Went from 171
# hand-authored stems to 1,169 -- this pool was the weakest of the three
# even after the first expansion, since stems don't get the same
# combinatorial help GIVENNAME does from being reused directly.
#
# 2026-08-25 (audit P1): expanded from 1,169 to 8,724 distinct stems.
#
# Azerbaijani surname formation is productive and patronymic: a father's given
# name plus -ov/-yev/-li/-zade is a well-formed surname (Abbas -> Abbasov,
# Eli -> Eliyev). The evidence that this is the rule the existing list already
# follows is in the list itself -- 1,037 of its 1,169 stems (88.7%) are
# literally entries in az_first_names_m.txt. Extending the stem pool with the
# remaining male given names therefore applies the same rule the verified list
# embodies rather than inventing names: every added stem is a real registered
# Azerbaijani given name from the same Ministry of Justice source.
#
# Female given names are deliberately NOT used: the construction is
# patronymic, so "Aysel" is not a surname stem in the way "Abbas" is.
#
# The two sources are weighted, not merged flat. A stem drawn from an actually
# registered SURNAME is more likely to look like a real surname than one
# derived from a rare given name, so the verified list is repeated
# _VERIFIED_STEM_WEIGHT times. rng.choice over the resulting multiset gives
# each verified stem that many times the probability of each derived one,
# with no change to any call site. At 100k documents this takes SURNAME from
# 9.2x reuse (5,660 distinct realised) to well inside the safe range -- see
# scripts/simulate_pools.py.
_VERIFIED_STEM_WEIGHT = 6

SURNAME_STEMS_VERIFIED = _load_names("az_surname_stems.txt")
# The derived stems are the male given-name list, so they carry the same
# contamination -- left unfiltered they build surnames like "Məhkəməyev"
# off a common noun. Filtered with the same list for the same reason.
SURNAME_STEMS_DERIVED = _drop_non_names(
    _load_names("az_surname_stems_extra.txt"))
SURNAME_STEMS = (SURNAME_STEMS_VERIFIED * _VERIFIED_STEM_WEIGHT
                 + SURNAME_STEMS_DERIVED)
# 2026-08-25: same treatment again -- street-name stems (person/place names
# that a real Azerbaijani street is named after, e.g. "Nizami" in "Nizami
# küçəsi") sourced from a list the user supplied and downloaded from a public
# street-name reference, not generated from memory. Extracted by stripping
# known street-type suffix words (küçəsi/prospekti/döngəsi/yol/massiv/
# meydan and spelling variants) off each raw entry, keeping only the stem --
# the existing `street()` builder below reattaches a suffix at generation
# time. Went from 94 hand-authored stems to 9,253. 4 raw entries that were
# just a bare suffix word with no actual stem ("Küçə", "Meydan", "YOL",
# "yol") were dropped rather than kept as meaningless stems.
STREET_STEMS = _load_names("az_street_stems.txt")


def surname(stem: str, female: bool, rng: random.Random) -> str:
    style = rng.random()
    if style < 0.62:
        base = stem + "ov"
        if stem[-1] in "əeiöüaıou":
            base = stem + "yev"
        return base + ("a" if female else "")
    if style < 0.80:
        # -yev attaches after a vowel; after a consonant the form is -ov/-ev.
        base = stem + ("yev" if stem[-1] in "əeiöüaıou" else "ov")
        return base + ("a" if female else "")
    if style < 0.92:
        # 2026-10-02 (P2-4c): the ending follows vowel harmony -- Qurbanlı,
        # Hüseynli, Oruclu, Gözlü. It used to be a coin flip, which wrote 49%
        # of these surnames with the wrong vowel (Katiblı, Əbdulrəhmanli). The
        # draw is kept so every later value stays exactly as before.
        rng.choice(["li", "lı"])
        return stem + "l" + _harmony4(stem)
    return stem + "zadə"


def _harmony4(stem: str) -> str:
    """The four-way harmony vowel (ı/i/u/ü) after `stem`'s last vowel."""
    for ch in reversed(stem.lower().replace("i̇", "i")):
        if ch in "aı":
            return "ı"
        if ch in "eəi":
            return "i"
        if ch in "ou":
            return "u"
        if ch in "öü":
            return "ü"
    return "i"


# 2026-08-25: replaced the 55-city hand-authored list and its coarse
# 40/8/4/1 guessed population tiers with a real dataset the user supplied --
# 97 cities/towns with actual per-place figures. Some of the smallest
# entries (e.g. Qəbələ at 73 despite being a well-known regional town) read
# more like source-dataset mention-counts than a census population, so this
# is not claimed as verified census data -- but used directly as a sampling
# weight it still captures the real order-of-magnitude skew toward Bakı and
# the handful of major secondary cities far better than a hand-picked tier
# ever could, which is the only thing CITY_WEIGHTS actually needs.
#
# 2026-08-25 (later, audit P0-5): the raw figures are used TEMPERED, not
# directly. Driving the real ValueFactory for 100,000 documents' worth of
# CITY draws against the untempered weights produced:
#
#     Baki                45.19% of every CITY mention
#     effective pool      15.0 of 97 (exp-entropy of the weight vector)
#     reuse at 100k       324x, with 31,322 draws past the max_share cap
#
# which is a memorisation risk, not a realism gain: the 80 smallest cities
# become effectively invisible to the model. The list itself is not the
# problem -- Azerbaijan really does have ~100 cities -- the concentration is.
# Raising every weight to a fractional power preserves the rank ordering and
# the order-of-magnitude story while restoring tail coverage. Measured:
#
#     exponent   top share   effective pool
#     1.0 (raw)     45.5%      15.0 / 97
#     0.5           10.5%      65.8 / 97
#     0.3 <-         4.6%      84.0 / 97
#     0.0 (flat)     1.0%      97.0 / 97   (loses all realism)
#
# See scripts/simulate_pools.py, which reproduces every number above.
WEIGHT_TEMPERATURE = 0.3


def _temper(weights: list[int], temperature: float = WEIGHT_TEMPERATURE
            ) -> list[float]:
    """Flatten a weight vector while preserving its ordering.

    `temperature` 1.0 returns the weights unchanged, 0.0 returns a uniform
    vector, and values in between interpolate. Applied to counts, not to
    normalized probabilities, because `random.choices` normalizes anyway and
    working on the raw figures keeps this readable against the source file.
    """
    if temperature >= 1.0:
        return [float(w) for w in weights]
    if temperature <= 0.0:
        return [1.0 for _ in weights]
    return [float(w) ** temperature if w > 0 else 0.0 for w in weights]


CITIES, _CITY_WEIGHTS_RAW = _load_weighted("az_cities.txt")
CITY_WEIGHTS = _temper(_CITY_WEIGHTS_RAW)


def _load_settlements(filename: str) -> tuple[list[str], list[str], list[float]]:
    """(names, kinds, draw weights) from `name<TAB>kind<TAB>weight` lines;
    `#` lines are the provenance header. The weights are final draw shares
    (build_az_settlements.py), so they are not tempered again."""
    names, kinds, weights = [], [], []
    with open(os.path.join(_DATA_DIR, filename), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name, kind, weight = line.split("\t")
            names.append(name)
            kinds.append(kind)
            weights.append(float(weight))
    return names, kinds, weights


# P2-14 (D-23c): the CITY pool. 4,415 names from Wikidata (CC0, 2026-10-07):
# Azerbaijani cities, district centres, qəsəbə and villages, plus common
# foreign cities, and the 97 cities above. Only 4 of the benchmark's 736 CITY
# mentions were among the 97; most are villages. Provenance and weights:
# build_az_settlements.py and the file header. CITIES above stays as it was:
# the frozen pii_guard gazetteer reads it.
SETTLEMENTS, SETTLEMENT_KINDS, SETTLEMENT_WEIGHTS = _load_settlements("az_settlements.txt")


def _load_foreign_names(filename: str) -> ForeignNames:
    """`kind<TAB>origin<TAB>name<TAB>feminine<TAB>cyrillic<TAB>weight` lines
    (build_foreign_names.py); `#` lines are the provenance header. An empty
    pool when the file is missing, so the build script can import this
    module before it has written the file."""
    out = ForeignNames()
    path = os.path.join(_DATA_DIR, filename)
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            kind, origin, name, fem, cyr, weight = line.split("\t")
            table = {"given_m": out.given_m, "given_f": out.given_f,
                     "surname": out.surnames}[kind]
            names, weights = table.setdefault(origin, ([], []))
            names.append((name, fem) if kind == "surname" else name)
            weights.append(float(weight))
            if cyr != "-":
                if kind == "surname":
                    cm, cf = cyr.split("|")
                    out.cyrillic[name], out.cyrillic[fem] = cm, cf
                else:
                    out.cyrillic[name] = cyr
    return out


# P2-15 (D-23d): Russian, Turkish, Georgian, Persian, Arabic, English, German
# and French given names and surnames, the most common ones by citizenship on
# Wikidata (CC0, 2026-10-07). A minority of persons get them
# (ValueFactory.FOREIGN_NAME_RATE); FIRST_M/FIRST_F/SURNAME_STEMS above stay
# the Azerbaijani pools, which the frozen pii_guard reads. Provenance and
# weights: build_foreign_names.py and the file header.
FOREIGN_NAMES = _load_foreign_names("foreign_names.txt")
# 2026-08-25: 230 real district/neighbourhood names (all of Azerbaijan, not
# just Baku), replacing a 23-entry Baku-only hand-authored list. Source data
# had the same casing-duplicate pattern as the name lists (e.g. "20-ci Sahə"
# / "20-ci sahə") plus 10 "PrimaryName \ AltName" entries recording two real
# names for the same place -- deduped case-insensitively and split into
# separate entries respectively. Not currently wired into active entity
# generation (no DISTRICT label exists; `address()` below, which references
# it, is itself not called by the value pipeline) -- kept clean and ready
# for if/when that changes rather than left messy.
DISTRICTS = _load_names("az_districts.txt")


def street(stem: str, rng: random.Random) -> str:
    return stem + " " + rng.choice(["küçəsi", "küç.", "prospekti", "pr.", "döngəsi"])


def address(rng: random.Random) -> str:
    st = street(rng.choice(STREET_STEMS), rng)
    city = rng.choice(CITIES)
    num = rng.randint(1, 180)
    apt = rng.randint(1, 220)
    blk = rng.randint(1, 40)
    style = rng.random()
    if style < 0.20:
        return f"{city}, {st} {num}"
    if style < 0.38:
        return f"{city} şəhəri, {rng.choice(DISTRICTS)}, {st} {num}, mənzil {apt}"
    if style < 0.52:
        return f"{st} {num}, {rng.choice(DISTRICTS)}, {city}"
    if style < 0.64:
        return f"{city}, {st}, ev {num}, mən. {apt}"
    if style < 0.74:
        return f"{postal(rng)}, {city}, {st} {num}"
    if style < 0.84:
        return f"{rng.choice(DISTRICTS)}, {blk}-ci blok, {st} {num}/{apt}"
    if style < 0.92:
        return f"{st} {num}, {city}"
    return f"{city}, {rng.choice(DISTRICTS)}, {st}, bina {num}, mənzil {apt}"


# 2026-08-25: was a fully synthetic `AZ{random 4-digit}` -- most values in
# that 6,000-code space are not real occupied Azerbaijani postal codes at
# all. Replaced with 253 real codes (user-supplied dataset) drawn weighted
# by the source's per-code frequency, same treatment as CITY_WEIGHTS.
#
# Tempered on the same grounds and by the same exponent as CITY_WEIGHTS
# (audit P0-5). Replacing the old random AZ1000-AZ6999 draw with 253 real
# codes was a large realism win but cut distinct values roughly 10x
# (2,537 realized -> 253 possible); the frequency weighting then concentrated
# 13.4% of all draws on a single code. Measured at exponent 0.3: top share
# 13.4% -> 1.5%, effective pool 72.7 -> 229.9 of 253.
_ZIPCODES, _ZIPCODE_WEIGHTS_RAW = _load_weighted("az_zipcodes.txt")
_ZIPCODE_WEIGHTS = _temper(_ZIPCODE_WEIGHTS_RAW)


def postal(rng: random.Random) -> str:
    return rng.choices(_ZIPCODES, weights=_ZIPCODE_WEIGHTS)[0]


# Mobile: 50/51 (Azercell), 55/99 (Bakcell), 70/77 (Nar) are each operator's
# primary+secondary range; 10 is Azercell's supplementary range, weighted
# lower since supplementary ranges are opened after the primary ones near
# exhaustion and so have had less time to fill up. "60" was in this list
# before but is not one of the codes this locale's own research notes above
# verify -- dropped as unverified rather than left in unweighted.
_MOBILE_CODES = ["50", "51", "55", "99", "70", "77", "10"]
_MOBILE_WEIGHTS = [0.17, 0.13, 0.17, 0.13, 0.17, 0.13, 0.10]
# Landline: 012 is Baku, which holds a large, disproportionate share of
# Azerbaijan's population relative to the other regional codes -- weighted
# accordingly. No equivalent basis to differentiate 18/22/24/26 from each
# other, so those stay even.
_LANDLINE_CODES = ["12", "18", "22", "24", "26"]
_LANDLINE_WEIGHTS = [0.45, 0.1375, 0.1375, 0.1375, 0.1375]


def phone(rng: random.Random) -> str:
    mobile = rng.random() < 0.78
    if mobile:
        op = rng.choices(_MOBILE_CODES, weights=_MOBILE_WEIGHTS)[0]
    else:
        op = rng.choices(_LANDLINE_CODES, weights=_LANDLINE_WEIGHTS)[0]
    a, b, c = rng.randint(100, 999), rng.randint(10, 99), rng.randint(10, 99)
    style = rng.random()
    # D-42c: `+994 (55) 123-45-67`, the operator code in brackets and dashes.
    # Run B missed 33 of 49 on shadow-dev, and no source had one; its share
    # comes from the two most common styles (were 0.24 and 0.16)
    if style < 0.12:
        return f"+994 ({op}) {a}-{b}-{c}"
    if style < 0.30:
        return f"+994 {op} {a} {b} {c}"
    if style < 0.40:
        return f"+994{op}{a}{b}{c}"
    if style < 0.54:
        return f"0{op} {a} {b} {c}"
    if style < 0.66:
        return f"(0{op}) {a}-{b}-{c}"
    if style < 0.76:
        return f"+994-{op}-{a}-{b}-{c}"
    if style < 0.85:
        return f"0{op}-{a}-{b}-{c}"
    if style < 0.93:
        return f"994{op}{a}{b}{c}"
    return f"0{op} {a} {b}-{c}"


def gov_id(rng: random.Random) -> str:
    """FİN: 7 uppercase alphanumerics. Also passport series AA1234567."""
    style = rng.random()
    alnum = string.ascii_uppercase + string.digits
    if style < 0.62:
        return "".join(rng.choice(alnum) for _ in range(7))
    if style < 0.82:
        return ("AZE" if rng.random() < 0.4 else
                "".join(rng.choice(string.ascii_uppercase) for _ in range(2))) \
            + f"{rng.randint(1000000, 9999999)}"
    return f"{rng.randint(1000000000, 9999999999)}"


def plate(rng: random.Random) -> str:
    region = rng.choice([10, 90, 99, 77, 20, 21, 22, 23, 24, 25, 26, 27, 28,
                         30, 31, 32, 33, 34, 35, 40, 41, 42, 43, 50, 51, 52,
                         55, 60, 61, 62, 65, 70, 71, 72, 73, 75, 80, 85])
    letters = "".join(rng.choice("ABCDEFGHJKLMNPRSTVXYZ") for _ in range(2))
    serial = rng.randint(100, 999)
    style = rng.random()
    if style < 0.68:
        return f"{region:02d}-{letters}-{serial}"
    if style < 0.85:
        return f"{region:02d}{letters}{serial}"
    return f"{region:02d} {letters} {serial}"


MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul",
          "avqust", "sentyabr", "oktyabr", "noyabr", "dekabr"]
WEEKDAYS = ["bazar ertəsi", "çərşənbə axşamı", "çərşənbə", "cümə axşamı",
            "cümə", "şənbə", "bazar"]


# D-51i: the ordinal suffix after a year (`2016-cı il`) is not part of the
# DATE (the real-text guide and the benchmark leave it outside the span), and
# it follows the vowel of the year's LAST SPOKEN WORD, as every suffix after
# a number does (`builder.suffix_after_number`): 2016 "altı" -> -cı, 2021
# "bir" -> -ci, 2023 "üç" -> -cü, 2010 "on" -> -cu, 1900 "yüz" -> -cü,
# 2000 "min" -> -ci. The old style always wrote `-ci` inside the value.
_UNIT_WORDS = ("sıfır", "bir", "iki", "üç", "dörd", "beş", "altı", "yeddi", "səkkiz", "doqquz")
_TEN_WORDS = ("", "on", "iyirmi", "otuz", "qırx", "əlli", "altmış", "yetmiş", "səksən", "doxsan")
_ORDINAL_VOWEL = {"a": "ı", "ı": "ı", "e": "i", "ə": "i", "i": "i", "o": "u", "u": "u",
                  "ö": "ü", "ü": "ü"}


def last_spoken_word(n: int) -> str:
    """The last word of `n` read aloud in Azerbaijani (`2016` -> `altı`)."""
    if n % 10 or n == 0:
        return _UNIT_WORDS[n % 10]
    if n % 100:
        return _TEN_WORDS[(n // 10) % 10]
    if n % 1000:
        return "yüz"
    return "min"


def year_suffix(year: int) -> str:
    """`-cı`, `-ci`, `-cu` or `-cü` after a year written in digits."""
    word = last_spoken_word(year)
    vowel = next(c for c in reversed(word) if c in _ORDINAL_VOWEL)
    return "-c" + _ORDINAL_VOWEL[vowel]


def date(day: int, month: int, year: int, rng: random.Random) -> str:
    style = rng.random()
    if style < 0.25:
        return f"{day:02d}.{month:02d}.{year}"
    if style < 0.42:
        return f"{day} {MONTHS[month - 1]} {year}"
    if style < 0.56:
        return f"{year}-{month:02d}-{day:02d}"
    if style < 0.67:
        return f"{day}.{month}.{year}"
    if style < 0.77:
        return f"{day:02d}/{month:02d}/{year}"
    if style < 0.85:
        # D-51i: was `{year}-ci il` inside the value; a writer that wants
        # the official `-cı il` puts year_suffix(year) + " il" after the span
        return f"{day} {MONTHS[month - 1]} {year}"
    if style < 0.92:
        return f"{day:02d}.{month:02d}.{str(year)[2:]}"
    # D-54d: a weekday is outside the DATE span in every language, like
    # `-cı il` and `года`: DATE is the calendar date only. This branch used to
    # return `{wd}, {date}` / `{date}, {wd}`; it keeps its share and its rng
    # draw (so no other value in a build moves) and returns the worded date.
    # A writer that wants the weekday puts weekday() beside the span.
    rng.random()
    return f"{day} {MONTHS[month - 1]} {year}"


def weekday(day: int, month: int, year: int) -> str:
    """The weekday of a real calendar date, for a writer that puts it next to
    a DATE span, outside it (D-54d): `{wd}, ⟦date⟧` or `⟦date⟧, {wd}`."""
    return WEEKDAYS[_date(year, month, day).weekday()]


COMPANIES = [
    "Bakı Texnologiya MMC", "Xəzər Logistika", "AzSoft MMC", "Kaspi Trade",
    "Zəfər İnşaat ASC", "Günəş Market MMC", "Alov Enerji", "Turan Holding",
    "İpək Yolu Nəqliyyat", "Bakı Ticarət Mərkəzi", "Azər Telekom MMC",
    "Şəfa Aptek Şəbəkəsi", "Yeni Nəsil Media", "Optimal Elektronika",
    "Kür Aqro MMC", "Xəzər Neft Servis", "Bakı Steel MMC", "Araz Mebel",
    "Nur Tekstil ASC", "Zirvə Konsaltinq", "Qafqaz Sığorta", "Barama Tech",
]
BANKS = [
    "Kapital Bank", "Paşa Bank", "Bank Respublika", "Xalq Bank",
    "Azərbaycan Beynəlxalq Bankı", "Unibank", "Rabitəbank", "Bank of Baku",
    "Yelo Bank", "Turanbank", "AccessBank", "Muğanbank", "Expressbank",
]
HOSPITALS = [
    "Mərkəzi Klinika", "Bona Dea Beynəlxalq Xəstəxanası", "Şəfa Xəstəxanası",
    "Respublika Klinik Xəstəxanası", "Bakı Sağlamlıq Mərkəzi",
    "Liv Bona Dea", "MediClub", "Caspian International Hospital",
    "Yeni Klinika", "Şəhər Poliklinikası №7",
]
UNIVERSITIES = [
    "Bakı Dövlət Universiteti", "Azərbaycan Dövlət Neft və Sənaye Universiteti",
    "ADA Universiteti", "Azərbaycan Texniki Universiteti", "Xəzər Universiteti",
    "Azərbaycan Dillər Universiteti", "UNEC", "Bakı Mühəndislik Universiteti",
]
EMAIL_DOMAINS = [
    "gmail.com", "mail.az", "box.az", "outlook.com", "inbox.az", "yahoo.com",
    "azdata.az", "bakutech.az", "list.az", "mail.ru", "yandex.ru", "icloud.com",
]
CORPORATE_DOMAINS = [
    "sirket.az", "company.az", "azsoft.az", "kaspitrade.az", "turanholding.az",
    "azertelekom.az", "bakusteel.az", "araz-mebel.az", "zirve.az", "barama.io",
    "xezerlog.az", "alovenerji.az", "optimal.az", "nurtekstil.az",
]

PHRASES = PhraseBank({
    "greeting": [
        "Salam", "Salam, necəsiniz", "Hörmətli həmkar", "Sabahınız xeyir",
        "Xoş gördük", "Hörmətli müştəri", "Hörmətli cənab", "Hörmətli xanım",
        "Günortanız xeyir", "Axşamınız xeyir", "Salam, əziz həmkarlar",
    ],
    "closing": [
        "Təşəkkürlər", "Hörmətlə", "Əvvəlcədən təşəkkür edirəm", "Uğurlar",
        "Sağ olun", "Hörmətlə, komandamız", "Cavabınızı gözləyirik",
        "Yaxşı iş günü arzulayıram", "Ən xoş arzularla",
    ],
    "request": [
        "aşağıdakı məlumatları təsdiq edə bilərsinizmi",
        "vaxtınız olanda qeydi yeniləyə bilərsinizmi",
        "bunu yoxlayıb mənə cavab verə bilərsinizmi",
        "səhv bir şey varsa, xahiş edirəm bildirin",
        "zəhmət olmasa sənədləri bu gün göndərin",
        "hesabınızın təsdiqlənməsi üçün məlumatları yeniləyin",
        "müqavilənin surətini mənə göndərə bilərsinizmi",
        "ödənişin statusunu yoxlaya bilərsinizmi",
        "bu məsələni təcili nəzərdən keçirməyinizi xahiş edirik",
        "xahiş edirəm əlaqə məlumatlarınızı dəqiqləşdirin",
    ],
    "note": [
        "müştəri hesab-faktura ilə bağlı zəng etdi və geri zəng istədi",
        "namizəd müsahibə üçün hazır olduğunu təsdiqlədi",
        "müqavilənin yenilənməsi müzakirə olundu, qərar bu həftə gözlənilir",
        "sənədlər arxivə köçürüldü, nüsxə şöbədə saxlanılır",
        "müştəri çatdırılma ünvanını dəyişdirmək istəyir",
        "ödəniş gecikməsi ilə bağlı xəbərdarlıq göndərildi",
        "yeni sifariş qeydiyyata alındı və anbara ötürüldü",
        "texniki qrup problemi araşdırır, nəticə sabah məlum olacaq",
        "müştəri xidmətdən razı qaldığını bildirdi",
        "hesabın bağlanması üçün ərizə qəbul edildi",
    ],
    "log_msg": [
        "istifadəçi girişi uğursuz oldu, doğrulama yenidən sınanır",
        "bu müştəri üçün ödəniş emal edilə bilmədi",
        "sessiyanın vaxtı bitdi və istifadəçi sistemdən çıxdı",
        "bu hesab üçün yeni cihaz qeydə alındı",
        "müştəri şifrənin sıfırlanmasını tələb etdi",
        "verilənlər bazasına qoşulma vaxtı bitdi",
        "təhlükəsizlik yoxlaması uğurla tamamlandı",
        "icazəsiz giriş cəhdi bloklandı",
        "ehtiyat nüsxə yaradılması tamamlandı",
        "sorğu limiti aşıldı, müraciət dayandırıldı",
        "konfiqurasiya faylı yenidən yükləndi",
        "şəbəkə bağlantısı bərpa olundu",
    ],
    "code_comment": [
        "bu faylı commit etməyin, müştəri məlumatları var",
        "sınaq mühiti üçün müvəqqəti giriş məlumatları",
        "bu qeyd ixracdan əvvəl maskalanmalıdır",
        "dəyişməzdən əvvəl təhlükəsizlik komandası ilə razılaşdırın",
        "köhnə API ilə uyğunluq üçün saxlanılıb",
        "burada şəxsi məlumatlar loglanmamalıdır",
        "istehsalat mühitində bu dəyər əvəz olunmalıdır",
        "müvəqqəti həll, sonra düzəldiləcək",
        "bu funksiya köhnəlib, istifadə etməyin",
        "giriş məlumatlarını mühit dəyişənlərindən oxuyun",
    ],
    "ticket_subject": [
        "yenilənmədən sonra hesabıma daxil ola bilmirəm",
        "son sifarişimdə çatdırılma ünvanı səhvdir",
        "geri ödəniş hələ də hesabıma keçməyib",
        "təsdiq kodu heç vaxt gəlmir",
        "kartımdan iki dəfə pul çıxılıb",
        "mobil tətbiq açılmır və xəta verir",
        "e-poçt ünvanımı dəyişə bilmirəm",
        "abunəliyimi ləğv etmək istəyirəm",
    ],
    "complaint": [
        "iki həftədir cavab gözləyirəm, hələ də həll olunmayıb",
        "dəstək xidməti ilə əlaqə saxlaya bilmirəm",
        "problem təkrarlanır, artıq üçüncü dəfədir",
        "verilən vədə baxmayaraq heç nə dəyişməyib",
    ],
    "confirmation": [
        "sifarişiniz uğurla qeydə alındı",
        "ödənişiniz təsdiqləndi, təşəkkür edirik",
        "məlumatlarınız yeniləndi",
        "müraciətiniz qəbul edildi və baxılır",
    ],
    "medical": [
        "mövsümi allergiya, antihistamin preparat təyin edildi",
        "növbəti qəbul iki həftə sonraya təyin olundu",
        "son müayinədə təzyiq normal həddədir",
        "qan analizinin nəticələri normadadır",
        "xəstəyə istirahət və maye qəbulu tövsiyə olunur",
        "müalicə kursu on gün davam edəcək",
        "əməliyyatdan sonrakı bərpa dövrü problemsiz keçir",
    ],
    "legal": [
        "müştəri sənədlərin təqdim edilmə müddətinin uzadılmasını xahiş edir",
        "sənədlər dünən qarşı tərəfə təqdim edildi",
        "razılaşma şərtləri tərəflər arasında məxfi qalır",
        "iddia ərizəsi məhkəməyə göndərilib",
        "müqavilənin 5-ci bəndinə əsasən tərəflər öhdəlik daşıyır",
        "vəkil müvəkkilin adından çıxış edir",
    ],
    "banking": [
        "hesabda vəsait çatışmadığı üçün köçürmə rədd edildi",
        "davam etməzdən əvvəl vəsait alanın məlumatlarını təsdiq edin",
        "daimi ödəniş tapşırığı ayın birində icra olunacaq",
        "kart müvəqqəti bloklanıb, filiala müraciət edin",
        "əməliyyat limiti gün ərzində aşılıb",
        "valyuta məzənnəsi əməliyyat anına görə tətbiq olunur",
    ],
    "hr": [
        "yeni əməkdaş sınaq müddətini uğurla başa vurdu",
        "məzuniyyət ərizəsi təsdiqlənib",
        "vakansiya üzrə müsahibələr gələn həftə keçiriləcək",
        "əmək müqaviləsinə əlavə razılaşma imzalanıb",
    ],
    "shipping": [
        "bağlama anbardan çıxarılıb və yoldadır",
        "çatdırılma sabah səhər saatlarında planlaşdırılır",
        "kuryer əlaqə saxlaya bilmədi, yenidən cəhd ediləcək",
        "sifariş qəbul məntəqəsinə çatdırılıb",
    ],
    "meeting": [
        "iclasda büdcə məsələləri müzakirə olundu",
        "növbəti görüş cümə gününə təyin edildi",
        "layihənin gedişatı barədə hesabat təqdim olundu",
    ],
    "policy": [
        "şəxsi məlumatların emalı qanunvericiliyə uyğun aparılır",
        "məlumatlar üçüncü tərəflərlə paylaşılmır",
        "istifadəçi istənilən vaxt razılığını geri ala bilər",
    ],
    "escalation": [
        "məsələ ikinci səviyyə dəstəyə ötürüldü",
        "təcili baxılması üçün rəhbərliyə eskalasiya edilib",
        "SLA müddəti bitmək üzrədir",
    ],
    "sysadmin": [
        "server yenidən başladıldı, xidmət bərpa olundu",
        "disk sahəsi kritik həddə çatıb",
        "yedəkləmə cədvəli yenilənib",
        "sertifikatın müddəti bir həftədən sonra bitir",
    ],
    "release_note": [
        "bu buraxılışda təhlükəsizlik düzəlişləri var",
        "performans yaxşılaşdırılıb və xətalar aradan qaldırılıb",
        "yeni funksionallıq sınaq rejimində əlçatandır",
    ],
    "review_comment": [
        "burada girişin yoxlanması əlavə edilməlidir",
        "dəyişiklik təsdiqlənir, birləşdirə bilərsiniz",
        "test əhatəsi kifayət deyil, əlavə testlər lazımdır",
    ],
})

LABELS = {
    "name": "Ad Soyad", "phone": "Telefon", "email": "E-poçt", "address": "Ünvan",
    "dob": "Doğum tarixi", "id": "FİN kod", "user": "İstifadəçi adı",
    "card": "Kart", "account": "Hesab", "order": "Sifariş", "invoice": "Faktura",
    "device": "Cihaz", "plate": "Dövlət nişanı", "note": "Qeyd", "subject": "Mövzu",
    "status": "Status", "amount": "Məbləğ", "diagnosis": "Diaqnoz",
    "patient": "Xəstə", "case": "İş", "client": "Müştəri", "position": "Vəzifə",
    "start": "Başlama tarixi", "experience": "İş təcrübəsi", "skills": "Bacarıqlar",
    "tracking": "İzləmə nömrəsi", "delivery": "Çatdırılma", "support": "Dəstək müraciəti",
    "password": "Şifrə", "company": "Şirkət", "department": "Şöbə", "ip": "IP ünvanı",
    "date": "Tarix", "signature": "İmza", "reference": "İstinad", "total": "Cəmi",
}

STOPWORDS = {
    "və", "üçün", "ilə", "mən", "sən", "biz", "siz", "bu", "olan", "olub",
    "edir", "deyil", "xahiş", "zəhmət", "olmasa", "nömrə", "ünvan", "hesab",
    "müştəri", "sifariş", "təsdiq", "göndər", "göndərildi", "yeni", "köhnə",
    "gün", "saat", "tarix", "soyad", "şəxsi", "məlumat", "giriş", "şifrə",
    "istifadəçi", "server", "xəta", "uğurla", "qeyd", "sənəd", "bank", "kart",
    "zəng", "etdi", "edin", "olunub", "aşağıdakı", "yuxarıda", "lütfən",
    "salam", "hörmətli", "cavab", "sual", "problem", "əlaqə", "təşəkkür",
    "artıq", "yenidən", "bütün", "daxil", "çıxış", "istifadə", "sistem",
    "təhlükəsizlik", "yoxlama", "təcili", "olaraq", "sonra", "əvvəl", "hər",
    "kimi", "görə", "qədər", "haqqında", "barədə", "tərəfindən", "vasitəsilə",
}

LOCALE = Locale(
    code="az", name="Azerbaijani",
    first_names_m=FIRST_M, first_names_f=FIRST_F,
    surname_stems=SURNAME_STEMS, surname_builder=surname,
    foreign_names=FOREIGN_NAMES,
    cities=CITIES, city_weights=CITY_WEIGHTS, districts=DISTRICTS,
    settlements=SETTLEMENTS, settlement_weights=SETTLEMENT_WEIGHTS,
    street_stems=STREET_STEMS,
    street_builder=street, address_builder=address, postal_builder=postal,
    phone_builder=phone, email_domains=EMAIL_DOMAINS,
    corporate_domains=CORPORATE_DOMAINS,
    companies=COMPANIES, banks=BANKS, hospitals=HOSPITALS,
    universities=UNIVERSITIES,
    gov_id_builder=gov_id, plate_builder=plate,
    iban_countries=["AZ", "AZ", "AZ", "AZ", "TR", "GE", "AE"],
    months=MONTHS, weekdays=WEEKDAYS, date_builder=date,
    phrases=PHRASES, labels=LABELS, stopwords=STOPWORDS,
    surname_first_rate=0.22, patronymic_rate=0.0,
    distinctive_chars="əƏ",
)
