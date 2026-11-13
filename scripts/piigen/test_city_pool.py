"""P2-14 (D-23c): the CITY pool is the Azerbaijani settlement list.

    python scripts/piigen/test_city_pool.py
"""
from __future__ import annotations

import collections
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.locales import LOCALES  # noqa: E402
from piigen.locales import az as AZ  # noqa: E402
from piigen.targeted import suffix as S  # noqa: E402
from piigen.values import ValueFactory, ValuePool  # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond, msg, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(msg + (f"  [{detail!r}]"[:300] if detail is not None else ""))


# the file: provenance header, sizes, kinds
path = ROOT / "scripts/piigen/locales/data/az_settlements.txt"
header = [l for l in path.read_text(encoding="utf-8").splitlines() if l.startswith("#")]
check(any("Wikidata" in l for l in header) and any("Never from the benchmark" in l for l in header),
      "the file header names its public source and says it is not the benchmark")
kinds = collections.Counter(AZ.SETTLEMENT_KINDS)
check(len(AZ.SETTLEMENTS) > 4000 and kinds["settlement"] > 3500 and kinds["foreign"] > 200
      and kinds["capital"] == 1, "over 4,000 names: settlements, the old cities, foreign cities", dict(kinds))
check(set(AZ.CITIES) <= set(AZ.SETTLEMENTS), "the 97 old cities are all in the pool")
check(len(set(AZ.SETTLEMENTS)) == len(AZ.SETTLEMENTS), "no duplicate names")
for name in ("Moskva", "İstanbul", "Tbilisi", "Tehran"):
    check(name in AZ.SETTLEMENTS, f"foreign city {name}")
check(not [n for n in AZ.SETTLEMENTS if "(" in n or "yaşayış yeri" in n or "rayonu" in n
           or any(c.isdigit() for c in n) or len(n.split()) > 3],
      "no disambiguators, archaeological sites, Baku districts, numbers or long names")

# frozen consumers keep the 97 cities
check(len(AZ.CITIES) == 97 and LOCALES["az"].cities == AZ.CITIES,
      "locale.cities is still the 97 (the frozen pii_guard gazetteer reads it)")

# draws: Bakı stays common, all groups appear, many distinct places
f = ValueFactory(random.Random(7), ValuePool(state_path=None))
draws = [f.city("az") for _ in range(20000)]
c = collections.Counter(draws)
kind_of = dict(zip(AZ.SETTLEMENTS, AZ.SETTLEMENT_KINDS))
share = {k: v / len(draws) for k, v in collections.Counter(kind_of.get(d, "?") for d in draws).items()}
check(0.04 <= c["Bakı"] / len(draws) <= 0.06, "Bakı stays about 5% of CITY draws", c["Bakı"] / len(draws))
check(abs(share.get("settlement", 0) - 0.42) < 0.02 and abs(share.get("foreign", 0) - 0.08) < 0.01
      and abs(share.get("city", 0) - 0.45) < 0.02, "group shares as built", share)
check(len(c) > 3000, "over 3,000 distinct places in 20,000 draws (97 before)", len(c))
check(f.make("CITY", "az") in AZ.SETTLEMENTS, "ValueFactory.make('CITY') draws from the pool (the LLM path)")

# every name takes every CITY case
bad = []
for n in AZ.SETTLEMENTS:
    for case in sorted(S.APPLIES["CITY"]):
        try:
            S.inflect(n, case, "CITY")
        except S.NotInflectable:
            bad.append((n, case))
check(not bad, "the renderer inflects every name in every CITY case", bad[:5])

print(f"PASSED {PASS}   FAILED {FAIL}")
for x in FAILURES:
    print("  FAIL:", x)
sys.exit(1 if FAIL else 0)
