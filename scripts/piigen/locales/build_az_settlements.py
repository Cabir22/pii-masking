"""Build locales/data/az_settlements.txt, the CITY pool (P2-14, D-23c).

    python scripts/piigen/locales/build_az_settlements.py

Sources, all public, none from the benchmark (A2.3):
  * Wikidata (CC0), queried 2026-10-07; the queries and their results are in
    data/sources/wikidata_2026-10-07/:
      az_settlements  every settlement in Azerbaijan (P17 = Q227) of the types
                      human settlement, village, city, town, urban-type
                      settlement (qəsəbə), big city, capital, with its
                      Azerbaijani label (rdfs:label @az) and population (P1082)
      capitals        every sovereign state's capital, Azerbaijani label
      big_cities      cities over 500,000 in 17 countries Azerbaijani text
                      often names (Russia, Turkey, Georgia, Iran, Ukraine,
                      Kazakhstan, Uzbekistan, Turkmenistan, Germany, UK,
                      France, USA, UAE, Italy, Spain, Belarus, Armenia)
  * the 97 cities and district centres already in az_cities.txt, with
    their populations; az_cities.txt itself stays unchanged because the
    frozen pii_guard gazetteer reads it (A2 rule 1)

Cleaning: the disambiguator in parentheses is dropped (`Qum (Qax)` -> `Qum`);
archaeological sites (`... yaşayış yeri`), Baku city districts (`... rayonu`),
numbered camps (`1 №-li ...`), names with quotes, digits or Roman numerals, names
with no vowel (acronyms) and names of more than three words are left out; a trailing `kəndi` ("village")
is removed. Only Azerbaijani letters, spaces, hyphens and apostrophes.

Weights (draw shares; the file stores them, az.py does not temper them):
  Bakı 5%                 the capital stays common (4.7% in the old pool)
  the other 96 old cities 45%, by their old tempered population weights
  the other settlements   42%, by sqrt(population, capped at 50,000); one
                          without a population gets the median
  foreign cities           8%, 3x for neighbours' and diaspora capitals
"""
from __future__ import annotations

import csv
import math
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SRC = DATA / "sources" / "wikidata_2026-10-07"
OUT = DATA / "az_settlements.txt"
sys.path.insert(0, str(HERE.parents[1]))

SHARES = {"capital": 0.05, "city": 0.45, "settlement": 0.42, "foreign": 0.08}
POP_CAP = 50_000
# Foreign cities that Azerbaijani text names most: neighbours' and diaspora
# capitals and the largest Russian and Turkish cities.
FOREIGN_COMMON = {"Moskva", "İstanbul", "Ankara", "Tbilisi", "Tehran", "Sankt-Peterburq", "Kiyev",
                  "Astana", "Daşkənd", "Aşqabad", "Minsk", "Berlin", "London", "Paris", "Dubay",
                  "İzmir", "Təbriz", "Antalya", "Bursa", "Kazan", "Novosibirsk", "Yekaterinburq",
                  "Vaşinqton", "Roma", "Vyana", "Praqa", "Varşava", "Brüssel", "Amsterdam", "Doha"}
LETTERS = re.compile(r"^[A-Za-zÇçƏəĞğIıİiÖöŞşÜü][A-Za-zÇçƏəĞğIıİiÖöŞşÜü' -]*$")
DROP = re.compile(r"yaşayış yeri|rayonu$|qəsəbəsi|sovxoz|yanında|stansiya|\d|№|[“”\"«»]|"
                  r"(?:^|[\s-])(?:I|II|III|IV|V)(?:$|[\s-])")


def clean(label: str) -> str | None:
    name = re.sub(r"\s*\(.*?\)\s*", " ", label).strip()
    name = re.sub(r"\s+kəndi$", "", name)
    name = re.sub(r"\s+", " ", name)
    # a name with no vowel (an acronym such as `NZS`) cannot take a suffix
    if (not name or DROP.search(name) or not LETTERS.match(name) or len(name.split()) > 3
            or not re.search(r"[AaƏəIıİiOoÖöUuÜüEe]", name)):
        return None
    return name


def _rows(name: str) -> list[dict]:
    with open(SRC / name, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def build() -> tuple[list[tuple[str, str, int]], dict]:
    from piigen.locales import az as AZ           # the old pool and its tempering
    old = dict(zip(AZ.CITIES, AZ.CITY_WEIGHTS))   # tempered old weights
    pops: dict[str, float] = {}
    dropped = 0
    for r in _rows("az_settlements.csv"):
        name = clean(r["az"])
        if name is None:
            dropped += 1
            continue
        pop = float(r["pop"]) if r["pop"] else 0.0
        pops[name] = max(pops.get(name, 0.0), pop)
    settle = {n: p for n, p in pops.items() if n not in old}
    foreign = {clean(r["az"]) for r in _rows("capitals.csv") + _rows("big_cities.csv")}
    foreign = {n for n in foreign if n and n not in old and n not in pops}
    known = [math.sqrt(min(p, POP_CAP)) for p in settle.values() if p > 0]
    median = statistics.median(known)

    raw: dict[str, dict[str, float]] = defaultdict(dict)
    raw["capital"]["Bakı"] = 1.0
    for n, w in old.items():
        if n != "Bakı":
            raw["city"][n] = w
    for n, p in settle.items():
        raw["settlement"][n] = math.sqrt(min(p, POP_CAP)) if p > 0 else median
    for n in foreign:
        raw["foreign"][n] = 3.0 if n in FOREIGN_COMMON else 1.0
    out = []
    for kind, share in SHARES.items():
        total = sum(raw[kind].values())
        for n, w in sorted(raw[kind].items()):
            out.append((n, kind, max(1, round(10_000_000 * share * w / total))))
    stats = {"settlement_rows": len(_rows("az_settlements.csv")), "dropped": dropped,
             "counts": {k: len(v) for k, v in raw.items()},
             "settlements_with_population": sum(1 for p in settle.values() if p > 0)}
    return out, stats


def main() -> int:
    rows, stats = build()
    header = [
        "# CITY pool for the generator (P2-14, D-23c): Azerbaijani settlements and common foreign cities.",
        "# Built by scripts/piigen/locales/build_az_settlements.py; edit the script, not this file.",
        "# Sources: Wikidata (CC0), queried 2026-10-07 (queries and results in",
        "#   data/sources/wikidata_2026-10-07/), and the 97 cities of az_cities.txt.",
        "#   Never from the benchmark (A2.3).",
        f"# Counts: {stats['counts']}; {stats['dropped']} source rows left out by the cleaning rules.",
        "# Columns: name <TAB> kind (capital | city | settlement | foreign) <TAB> draw weight.",
        "# Shares: " + ", ".join(f"{k} {int(v * 100)}%" for k, v in SHARES.items()) + ".",
    ]
    OUT.write_text("\n".join(header + [f"{n}\t{k}\t{w}" for n, k, w in rows]) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"wrote {OUT.name}: {len(rows)} names {stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
