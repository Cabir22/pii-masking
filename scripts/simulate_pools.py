"""Project value-pool reuse at 30k / 50k / 100k documents.

Drives the REAL `ValueFactory` against the REAL pools, because the only
honest answer to "what happens at 100k" is to draw 100k documents' worth of
values and count. Estimating from list sizes misses the two things that
actually bite: weighting concentration (a 97-entry list where one entry takes
45% of the draws behaves like a 15-entry list) and the `max_share` cap.

READ-ONLY with respect to the repository's own state: every pool here is
constructed with `state_path=None`, so `data/raw/.valuepool.json` is never
read or written.

Run:  python scripts/simulate_pools.py
      python scripts/simulate_pools.py --temperature 0.5 --targets 50000
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.config import ENTITY_TYPES, GeneratorConfig  # noqa: E402
from piigen.locales import LOCALES                       # noqa: E402
from piigen.values import (ValueFactory, ValuePool,      # noqa: E402
                           FINITE_BY_NATURE)
import piigen.locales.az as AZ                           # noqa: E402

# Mentions per document, per label, measured from the audited corpus. Used to
# scale the number of draws so the simulation reflects the real request mix
# rather than an even split across labels.
DEFAULT_MENTIONS_PER_DOC = {
    "GIVENNAME": 0.7063, "SURNAME": 0.5186, "EMAIL": 0.4914,
    "TELEPHONENUM": 0.4039, "CITY": 0.3143, "DATE": 0.1893,
    "STREET": 0.1838, "BUILDINGNUM": 0.1568, "ZIPCODE": 0.1474,
    "AGE": 0.1290, "TIME": 0.1066, "API_KEY": 0.1030, "URL": 0.1017,
    "AZ_FIN": 0.0927, "IPV4_ADDRESS": 0.0845, "PAYMENT_CARD_NUMBER": 0.0771,
    "AZ_ID_CARD_NUMBER": 0.0685, "IBAN": 0.0619, "ACCESS_TOKEN": 0.0600,
    "AZ_PASSPORT_NUMBER": 0.0572, "CARD_SECURITY_CODE": 0.0521,
    "AZ_DRIVER_LICENSE_NUMBER": 0.0506, "AZ_VOEN": 0.0506,
    "MAC_ADDRESS": 0.0411, "PRIVATE_KEY": 0.0410, "ICCID": 0.0322,
    "IPV6_ADDRESS": 0.0321,
}

# FINITE_BY_NATURE (imported from piigen.values, the single source of truth
# -- 2026-08-26 wired the same judgment into ValuePool.health()'s live stop
# gate, which previously judged these by raw over_cap_share and halted a
# real resumed run on AGE after one batch): labels whose value space is
# genuinely finite in the world, not merely small in our data. There are
# ~97 Azerbaijani cities, ~95 plausible human ages and 253 real postal
# codes; no amount of pool engineering creates more.
#
# Judging these by mean reuse is a category error, and doing so is what made
# the first pass of this simulation report CITY as CRITICAL at every
# temperature: reuse = draws/distinct, and distinct is capped by reality at
# 97, so reuse at 100k is ~324x whatever the weights do. Reuse is only a
# meaningful risk signal for labels whose space is combinatorial or
# algorithmic, where a high number really does mean the generator is
# repeating itself unnecessarily.
#
# What matters for a closed class is instead:
#   * concentration -- is one value swallowing the label? (memorisation)
#   * tail coverage -- does the RAREST value still appear often enough to be
#     learned? (the 80 smallest cities being invisible was the real defect)
# Exactly the three the audit identified. DATE, TIME, BUILDINGNUM and
# CARD_SECURITY_CODE were in this set on the first pass and had to come
# out: their values are combinatorial (17,825 distinct DATEs from 18,930
# draws), and a "rarest value seen once" reading is expected there, not a
# risk. Their real exposure is contextual, not diversity -- which is what
# the anchor gate (piigen/anchors.py) addresses.

# A value seen fewer times than this across the whole corpus is not reliably
# learnable as an example of its class. Deliberately modest: NER models
# generalise across contexts, so this is a floor, not a target.
MIN_LEARNABLE_OCCURRENCES = 20

# Concentration ceiling. Above this share, one value dominates its label
# enough that the model can shortcut to memorising it.
MAX_CONCENTRATION = 0.10

REUSE_VERDICTS = [(5, "OK"), (15, "WATCH"), (60, "RISK"),
                  (float("inf"), "CRITICAL")]


def verdict(row: dict) -> str:
    """Risk verdict, judged on the right axis for the label's kind."""
    if row["label"] in FINITE_BY_NATURE:
        if row["top_share"] > MAX_CONCENTRATION:
            return "CRITICAL"          # one value swallowing the label
        if row["rarest_count"] < MIN_LEARNABLE_OCCURRENCES:
            return "RISK"              # tail present but too thin to learn
        if row["coverage"] < 0.90:
            return "WATCH"             # part of the real space never drawn
        return "OK"
    for limit, name in REUSE_VERDICTS:
        if row["reuse"] <= limit:
            return name
    return "CRITICAL"


def effective_size(weights) -> float:
    """exp(Shannon entropy) -- how many entries the pool BEHAVES like.

    A 97-city list where the capital takes 45% of the mass does not give 97
    cities' worth of diversity, and the raw length hides that completely.
    """
    total = sum(weights)
    if not total:
        return 0.0
    probs = [w / total for w in weights if w > 0]
    return math.exp(-sum(p * math.log(p) for p in probs))


def universe_size(label: str) -> int:
    """How many distinct values the real world offers for this label."""
    loc = LOCALES["az"]
    return {
        "CITY": len(loc.cities),
        "ZIPCODE": len(AZ._ZIPCODES),
        "AGE": 95,                      # ValueFactory.age() range
    }.get(label, 0)


def simulate(label: str, draws: int, cfg: GeneratorConfig,
             seed: int) -> dict:
    rng = random.Random(seed)
    pool = ValuePool(max_share=cfg.max_value_share, state_path=None)
    factory = ValueFactory(rng, pool, cfg.password_keyword_share)
    got: Counter = Counter()
    for _ in range(draws):
        try:
            value = factory.make(label, "az")
        except Exception:            # noqa: BLE001
            value = ""
        if value:
            got[value] += 1
    distinct = len(got)
    top_value, top_count = (got.most_common(1) or [("", 0)])[0]
    rarest_count = min(got.values()) if got else 0
    universe = universe_size(label)
    return {
        "rarest_count": rarest_count,
        "universe": universe,
        "coverage": (distinct / universe) if universe else 1.0,
        "label": label,
        "draws": draws,
        "distinct": distinct,
        "reuse": (draws / distinct) if distinct else 0.0,
        "top_value": top_value,
        "top_share": (top_count / draws) if draws else 0.0,
        "over_cap": pool.over_cap[label],
        "over_cap_share": pool.health(label)["over_cap_share"],
        "exhausted": pool.exhausted[label],
        "status": pool.health(label)["status"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--targets", type=int, nargs="+",
                    default=[30_000, 50_000, 100_000])
    ap.add_argument("--seed", type=int, default=20260825)
    ap.add_argument("--temperature", type=float, default=None,
                    help="override az.WEIGHT_TEMPERATURE for this run")
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()

    if args.temperature is not None:
        AZ.CITY_WEIGHTS = AZ._temper(AZ._CITY_WEIGHTS_RAW, args.temperature)
        AZ._ZIPCODE_WEIGHTS = AZ._temper(AZ._ZIPCODE_WEIGHTS_RAW,
                                         args.temperature)
        LOCALES["az"].city_weights = AZ.CITY_WEIGHTS

    cfg = GeneratorConfig()
    loc = LOCALES["az"]
    temperature = (args.temperature if args.temperature is not None
                   else AZ.WEIGHT_TEMPERATURE)

    print("=" * 92)
    print("VALUE-POOL PROJECTION")
    print("=" * 92)
    print(f"weight temperature : {temperature}")
    print(f"max_value_share    : {cfg.max_value_share}")
    print(f"seed               : {args.seed}")
    print()
    print("--- weighted pools: raw size vs. what they behave like ---")
    for name, values, weights in (
            ("cities", loc.cities, AZ.CITY_WEIGHTS),
            ("zipcodes", AZ._ZIPCODES, AZ._ZIPCODE_WEIGHTS)):
        eff = effective_size(weights)
        top_i = max(range(len(weights)), key=lambda i: weights[i])
        print(f"  {name:<10} raw={len(values):<5} effective={eff:6.1f}  "
              f"top={values[top_i]!r} share={weights[top_i]/sum(weights)*100:5.2f}%")
    print(f"  {'givennames':<10} raw={len(loc.first_names_m) + len(loc.first_names_f)}")
    print(f"  {'surnames':<10} raw={len(loc.surname_stems)} stems "
          f"(x suffix builder)")
    print(f"  {'streets':<10} raw={len(loc.street_stems)} stems "
          f"(x 5 street types)")
    print()

    results: dict = {}
    for target in args.targets:
        print(f"--- {target:,} documents ---")
        print(f"  {'label':<26}{'draws':>9}{'distinct':>9}{'reuse':>8}"
              f"{'top%':>8}{'rarest':>8}{'cover':>8}  verdict")
        rows = []
        for label in ENTITY_TYPES:
            per_doc = DEFAULT_MENTIONS_PER_DOC.get(label, 0.0)
            draws = int(round(per_doc * target))
            if draws <= 0:
                continue
            row = simulate(label, draws, cfg, args.seed)
            row["verdict"] = verdict(row)
            rows.append(row)
        rows.sort(key=lambda r: -r["reuse"])
        for r in rows:
            flag = "" if r["verdict"] == "OK" else "  <<<"
            cover = (f"{r['coverage']*100:>7.0f}%" if r["universe"]
                     else "      -")
            print(f"  {r['label']:<26}{r['draws']:>9,}{r['distinct']:>9,}"
                  f"{r['reuse']:>7.0f}x{r['top_share']*100:>7.2f}%"
                  f"{r['rarest_count']:>8,}{cover}  {r['verdict']}{flag}")
        worst = [r for r in rows if r["verdict"] in ("RISK", "CRITICAL")]
        print(f"  -> {len(worst)} label(s) at RISK or worse"
              + (f": {', '.join(r['label'] for r in worst)}" if worst else ""))
        print()
        results[str(target)] = rows

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(
            {"temperature": temperature, "seed": args.seed,
             "max_value_share": cfg.max_value_share, "targets": results},
            ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"json written to {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
