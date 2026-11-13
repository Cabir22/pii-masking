"""One fresh value per entity, however the source inflected or cased it
(translate/stem.py; run.py's mint_values).

Run: python scripts/translate/test_stem.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from translate.run import mint_values  # noqa: E402
from translate.stem import az_lower, az_stem  # noqa: E402

PASS = FAIL = 0


def ok(cond, msg, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  FAIL {msg}" + (f"  [{detail}]" if detail else ""))


ok(az_lower("ELDARLI") == "eldarlı", "I lowers to ı", az_lower("ELDARLI"))
ok(az_lower("İLQAR") == "ilqar", "İ lowers to i", az_lower("İLQAR"))

# Pairs found in v4.1 train: one entity, two mentions.
for a, b in [("Eldarlı", "ELDARLI"), ("Ərkixanım", "Ərkixanımı"), ("Sumqayıt", "Sumqayıtda"),
             ("ASTARA", "Astaranın"), ("Tukayov", "Tukayovun"), ("Yoğunbulaq", "Yoğunbulaqda")]:
    ok(az_stem(a) == az_stem(b), f"az_stem unifies {a}/{b}", (az_stem(a), az_stem(b)))
for a, b in [("Bakı", "Gəncə"), ("Əli", "Ələsgər"), ("Səbinə", "Səbinəxanım")]:
    ok(az_stem(a) != az_stem(b), f"az_stem keeps {a}/{b} apart")

for lang in ("en", "tr"):
    labels = ["GIVENNAME", "SURNAME", "GIVENNAME", "SURNAME", "GIVENNAME", "CITY", "CITY"]
    src = ["Cövri", "Eldarlı", "Ərkixanım", "ELDARLI", "Ərkixanımı", "Sumqayıt", "Sumqayıtda"]
    v = mint_values(labels, src, lang, f"llm_az_015101|{lang}")
    ok(v[2] == v[4], f"{lang}: Ərkixanım / Ərkixanımı get one name", (v[2], v[4]))
    ok(v[1] == v[3], f"{lang}: Eldarlı / ELDARLI get one surname", (v[1], v[3]))
    ok(v[5] == v[6], f"{lang}: Sumqayıt / Sumqayıtda get one city", (v[5], v[6]))
    ok(v[0] != v[2], f"{lang}: two different people keep two names", (v[0], v[2]))
    ok(v == mint_values(labels, src, lang, f"llm_az_015101|{lang}"), f"{lang}: deterministic")

print("=" * 60)
print(f"PASSED {PASS}   FAILED {FAIL}")
print("=" * 60)
sys.exit(1 if FAIL else 0)
