"""Build locales/data/foreign_names.txt, the foreign GIVENNAME and SURNAME
pool (P2-15, D-23d).

    python scripts/piigen/locales/build_foreign_names.py

Sources, all public, none from the benchmark (A2.3):
  * Wikidata (CC0), queried 2026-10-07; the queries and their results are in
    data/sources/wikidata_names_2026-10-07/. For each origin, the 400 given
    names (P735, items of the class male or female given name) and the 400
    family names (P734, of men) borne by the most people with that
    citizenship (P27), with the number of such people:
      ru  Russia                tr  Turkey               ka  Georgia
      fa  Iran                  ar  Egypt, Saudi Arabia, Iraq, Syria, Jordan
      en  United Kingdom, USA   de  Germany              fr  France
    The server's time limit is too short for every person of the larger
    countries, so the English, German and French lists and the Arabic family
    names count over the first 20,000 people of each country instead (a fixed
    subset, see fetch.py); a frequency ranking all the same.

Spelling: the name as it is written in Latin letters in that language's
documents, which is what an Azerbaijani text quotes. Russian names are the
Russian label romanised by scripts/name_transliterators.py, the same
romanisation the generator's Cyrillic name variants use (`Sergey`,
`Kseniya`, `Petrov`), and keep the Russian label as their Cyrillic form
(the English label of a shared item would give `Victor`, `Xenia`); Turkish,
German and French names their own label (`Yılmaz`, `Müller`); Georgian,
Persian, Arabic and English names the English label (`Giorgi`, `Hosseini`).
A Russian family name gets its feminine form by the Russian rule
(Petrov -> Petrova, Ivanovskiy -> Ivanovskaya, Tolstoy -> Tolstaya); every
other family name is the same for women.

Left out: names with a space, hyphen, apostrophe or dot (`Al-Rashid`,
`O'Brien`), with a letter Azerbaijani does not write except `w` (`é`, `ä`,
`ß`, `â`), with a capital inside (`McDonald`), shorter than 3 letters or
with no vowel; names that are an Azerbaijani word or a city of the CITY pool,
which would make a label depend on a reading the model cannot see: a
stopword or homograph (resolver._common_words: `Deniz`), a lowercase word of
the generator's own Azerbaijani text (frames, phrases, decoys: `Uzun`,
`Genç`, `Usta`), or one of AZ_WORDS below (`Adam`, `Aslan`, `Demir`).
There is no Azerbaijani lexicon in the repository, so the last list is
written by hand. A name found for two origins stays with the
one where more people bear it. A name also in the Azerbaijani pools stays
(`Sergey`, `Ali` in `Ali Yılmaz`): it is that origin's name too; the header
counts them.

Weights (draw shares; the file stores them): each origin has a share of the
foreign names, below; inside an origin a name is drawn by sqrt(people who
bear it), so `Aleksandr` is common without crowding out the rest.
"""
from __future__ import annotations

import csv
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SRC = DATA / "sources" / "wikidata_names_2026-10-07"
OUT = DATA / "foreign_names.txt"
sys.path.insert(0, str(HERE.parents[1]))

# Share of each origin among the foreign names drawn. Russian and Turkish
# names are the ones Azerbaijani text meets most; Persian/Arabic and
# English/European 15% each.
SHARES = {"ru": 0.35, "tr": 0.25, "ka": 0.10, "fa": 0.10, "ar": 0.05,
          "en": 0.08, "de": 0.04, "fr": 0.03}
# Frequent Azerbaijani words that foreign names spell (compared by
# match_key, so `Ateş` is `atəş`); see the module docstring.
AZ_WORDS = """adam ana ata ay ağ alma atəş aslan arslan bal bahar bəy bulud can çay çiçək
    dağ daş dəmir dəniz dünya gecə gəl gül gün gümüş günəş kar kişi qadın qara qaya qış qız
    qızıl qurd mavi nur sabah sarı səma su şah şam şirin taş tək toprak torpaq ulduz uzun
    xan yaz yağış yaşıl yol yeni böyük kiçik gənc genç usta zaman tarix""".split()
# The label each origin is written with, in order of preference; Russian
# names are romanised from the Russian label instead (_pick).
LABEL_LANGS = {"ru": (), "tr": ("tr", "en"), "ka": ("en",), "fa": ("en",),
               "ar": ("en",), "en": ("en",), "de": ("de", "en"), "fr": ("fr", "en")}
MALE, FEMALE = "Q12308941", "Q11879590"
LOWER = "abcçdeəfgğhxıijkqlmnoöprsştuüvwyz"
UPPER = "ABCÇDEƏFGĞHXIİJKQLMNOÖPRSŞTUÜVWYZ"
NAME = re.compile(f"^[{UPPER}][{LOWER}]{{2,}}$")
# `y` is no vowel to the suffix renderer: `Byrd` could take no suffix
VOWEL = re.compile(r"[aeəıioöuü]")
CYRILLIC = re.compile(r"^[А-ЯЁ][а-яё]+$")


def clean(label: str) -> str | None:
    """`label` as a pool name, or None when it is left out (module docstring)."""
    name = re.sub(r"\s*\(.*?\)\s*", "", label or "").strip()
    if not NAME.match(name) or not VOWEL.search(name.lower()):
        return None
    return name


def clean_ru(label: str) -> str | None:
    name = re.sub(r"\s*\(.*?\)\s*", "", label or "").strip()
    return name if CYRILLIC.match(name) and len(name) >= 3 else None


def feminine_ru(name: str) -> str:
    """The feminine of a Russian family name, Latin or Cyrillic."""
    for masc, fem in (("skiy", "skaya"), ("skii", "skaya"), ("sky", "skaya"),
                      ("ский", "ская"), ("цкий", "цкая"), ("tskiy", "tskaya"),
                      ("oy", "aya"), ("ой", "ая")):
        if name.endswith(masc):
            return name[: -len(masc)] + fem
    if re.search(r"(ov|ev|yov|in|yn|ов|ев|ёв|ин|ын)$", name):
        return name + ("а" if CYRILLIC.match(name) else "a")
    return name


def _rows(name: str) -> list[dict]:
    path = SRC / name
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _translit():
    import importlib.util
    path = HERE.parents[1] / "name_transliterators.py"
    spec = importlib.util.spec_from_file_location("name_transliterators", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_NT = None


def romanise_ru(cyrillic: str) -> str:
    global _NT
    _NT = _NT or _translit()
    return _NT.transliterate(cyrillic, "ru", "latin")


def _pick(row: dict, origin: str) -> str | None:
    if origin == "ru":
        native = clean_ru(row.get("ru", ""))
        return clean(romanise_ru(native)) if native else None
    for lang in LABEL_LANGS[origin]:
        name = clean(row.get(lang, ""))
        if name:
            return name
    return None


def _azerbaijani_keys() -> tuple[set, set]:
    """match_keys of (names already in the Azerbaijani pools, in both
    spellings; common words, homographs and CITY-pool names)."""
    from piigen.locales import az as AZ
    from piigen.resolver import _common_words, match_key
    from piigen.values import az_english_spelling
    names = set(AZ.FIRST_M) | set(AZ.FIRST_F)
    for stem in set(AZ.SURNAME_STEMS):
        if not stem:
            continue
        ov = stem + ("yev" if stem[-1] in "əeiöüaıou" else "ov")
        names |= {ov, ov + "a", stem + "ov", stem + "ova", stem + "l" + AZ._harmony4(stem),
                  stem + "zadə"}
    keys = {match_key(n) for n in names} | {match_key(az_english_spelling(n)) for n in names}
    words = set(_common_words()) | {match_key(c) for c in AZ.CITIES + AZ.SETTLEMENTS}
    words |= {match_key(w) for w in AZ_WORDS} | _template_words()
    return keys, words


# The generator's Azerbaijani text: lowercase words in its string literals.
TEXT_MODULES = ("targeted/frames_az.py", "targeted/suffix_frames.py", "targeted/formats.py",
                "targeted/homographs_az.py", "targeted/builder.py", "locales/az.py",
                "negatives.py", "llm/edge_cases.py")


def _template_words() -> set:
    from piigen.resolver import match_key
    out = set()
    for rel in TEXT_MODULES:
        path = HERE.parent / rel
        if not path.exists():
            continue
        for s in re.findall(r'"([^"\n]*)"', path.read_text(encoding="utf-8")):
            out |= {match_key(w) for w in re.findall(r"(?<!\w)[a-zçəğıöşü]{3,}(?!\w)", s)}
    return out


def build() -> tuple[list[tuple], dict, dict]:
    from piigen.resolver import match_key
    az_names, az_words = _azerbaijani_keys()
    dropped = defaultdict(int)
    # (kind, match_key) -> best (people, origin, name, feminine, native)
    best: dict[tuple, tuple] = {}
    for origin in SHARES:
        for kind_file in ("given", "family"):
            for row in _rows(f"{origin}_{kind_file}.csv"):
                n = int(row["n"])
                name = _pick(row, origin)
                native = clean_ru(row.get("ru", "")) if origin == "ru" else ""
                if name is None:
                    dropped["spelling"] += 1
                    continue
                key = match_key(name)
                if key in az_words:
                    dropped["common word or city"] += 1
                    continue
                if kind_file == "given":
                    kind = "given_f" if row["cls"].endswith(FEMALE) else "given_m"
                    fem = name
                else:
                    kind = "surname"
                    fem = name
                    if origin == "ru":
                        fem = clean(romanise_ru(feminine_ru(native))) or name
                        native = native + "|" + feminine_ru(native)
                    if match_key(fem) in az_words:
                        dropped["common word or city"] += 1
                        continue
                prev = best.get((kind, key))
                if prev is not None:
                    dropped["other origin"] += 1
                    if prev[0] >= n:
                        continue
                best[(kind, key)] = (n, origin, name, fem, native)
    # kept names that are also in the Azerbaijani pools (module docstring)
    overlap = defaultdict(int)
    for kind, key in best:
        if key in az_names:
            overlap[kind] += 1
    # weights: the origin's share, split by sqrt(people) inside it, per kind
    rows = []
    for kind in ("given_m", "given_f", "surname"):
        by_origin = defaultdict(list)
        for (k, _key), v in best.items():
            if k == kind:
                by_origin[v[1]].append(v)
        for origin, items in by_origin.items():
            total = sum(math.sqrt(v[0]) for v in items)
            for n, _o, name, fem, native in sorted(items, key=lambda v: (-v[0], v[2])):
                rows.append((kind, origin, name, fem, native or "-",
                             SHARES[origin] * math.sqrt(n) / total))
    return rows, dict(dropped), dict(overlap)


def write(rows: list[tuple], dropped: dict, overlap: dict) -> None:
    counts = defaultdict(int)
    for kind, origin, *_ in rows:
        counts[(kind, origin)] += 1
    head = __doc__.strip().splitlines()
    lines = ["# " + h if h else "#" for h in head]
    lines += ["#", "# Generated by build_foreign_names.py; do not edit by hand.",
              "# Columns: kind<TAB>origin<TAB>name<TAB>feminine<TAB>cyrillic<TAB>weight",
              "#   kind      given_m, given_f or surname",
              "#   feminine  the surname for a woman (the name itself for a given name)",
              "#   cyrillic  the Russian form, masculine|feminine for a surname; - if none",
              "#   weight    the draw share inside its kind (each kind sums to 1)",
              "# Counts: " + ", ".join(
                  f"{k} {sum(c for (kk, _o), c in counts.items() if kk == k)}"
                  for k in ("given_m", "given_f", "surname")),
              "# Left out: " + ", ".join(f"{k} {v}" for k, v in sorted(dropped.items())),
              "# Also in the Azerbaijani pools (kept): " + ", ".join(
                  f"{k} {v}" for k, v in sorted(overlap.items()))]
    lines += ["\t".join([k, o, n, f, c, f"{w:.6g}"]) for k, o, n, f, c, w in rows]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    rows, dropped, overlap = build()
    write(rows, dropped, overlap)
    counts = defaultdict(int)
    for kind, origin, *_ in rows:
        counts[(kind, origin)] += 1
    for k in sorted(counts):
        print(*k, counts[k])
    print("left out:", dropped)
    print("also in the az pools (kept):", overlap)
