"""D-27 check: real-length PEM keys in long documents of the targeted builder.

No network, no model.

    python scripts/piigen/targeted/test_long_pem.py
"""

from __future__ import annotations

import logging
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
logging.disable(logging.WARNING)

from piigen.llm.quality_filter import MAX_PII_DENSITY, MIN_CARRIER_WORDS, screen_record  # noqa: E402
from piigen.llm.specs import LENGTH_BANDS                                    # noqa: E402
from piigen.targeted import builder as B                                      # noqa: E402
from piigen.targeted import long_docs as LD                                   # noqa: E402
from piigen.targeted import quotas as Q                                       # noqa: E402
from piigen.validate import validate_example, value_valid                    # noqa: E402
from piigen.values import PEM_KINDS, ValueFactory, ValuePool, pem_max_length  # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond: bool, msg: str, detail=None) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(msg + (f"  [{detail!r}]"[:300] if detail is not None else ""))


def test_key_kinds() -> None:
    f = ValueFactory(random.Random(7), ValuePool(state_path=None))
    q = Q.load()["boundary"]
    lengths = []
    for _ in range(300):
        key = f.private_key_varied(min_chars=q["pem_long_min_chars"], max_chars=q["pem_long_max_chars"])
        lengths.append(len(key))
        check(value_valid("PRIVATE_KEY", key), "a long key is a valid PRIVATE_KEY")
    check(min(lengths) >= 1500, "every long key is 1,500+ characters", min(lengths))
    check(max(lengths) <= 2000, "RSA-4096 stays out (it cannot pass the density cap)", max(lengths))
    # the default call is unchanged: short kinds only, below pem_max_chars
    short = [len(f.private_key_varied(max_chars=700)) for _ in range(100)]
    check(max(short) <= 700, "max_chars alone still keeps keys short", max(short))
    check(any(pem_max_length(k) > 3000 for k in PEM_KINDS), "the 4,096-bit kind exists, only filtered out")


def test_long_documents() -> None:
    quotas = Q.load()
    builder = B.TargetedBuilder(11, 400, quotas)
    top = max(x[3] for x in LENGTH_BANDS if x[0] == "extreme")
    docs = [builder._compose("pem_long") for _ in range(40)]
    for d, spec in docs:
        text = d.text
        keys = [e for e in d.entities if e["label"] == "PRIVATE_KEY"]
        check(len(keys) == 1 and not [e for e in d.entities if e["label"] != "PRIVATE_KEY"],
              "one PRIVATE_KEY and no other entity")
        n = keys[0]["end"] - keys[0]["start"]
        check(n >= 1500, "the key is real length", n)
        check(4200 <= len(text) <= top, "the document is inside the extreme band", len(text))
        density = n / len(text)
        check(density <= MAX_PII_DENSITY["extreme"], "under the unchanged 25% cap", round(density, 3))
        check(spec.get("long_kind") in LD.KINDS, "the document kind is recorded")
    check(len({spec["long_kind"] for _, spec in docs}) == 3, "runbook, deployment note and ticket all appear")


def test_build_gates() -> None:
    """A real build: the family's share, the gates, no document without a band."""
    quotas = Q.load()
    records = B.TargetedBuilder(3, 6000, quotas).build()
    longs = [r for r in records if r["_spec"].get("long_kind")]
    check(len(longs) >= 20, "the family is present at its share", len(longs))
    keys = [e for r in records for e in r["entities"] if e["label"] == "PRIVATE_KEY"]
    long_keys = [e for e in keys if e["end"] - e["start"] >= 1500]
    check(len(long_keys) / len(keys) >= 0.30, "30% of PRIVATE_KEY spans are real length",
          round(len(long_keys) / len(keys), 3))
    for r in longs:
        check(r["_bucket"] == "extreme", "the record has its band", r["_bucket"])
        check(not validate_example(r), "validate_example passes", validate_example(r)[:1])
        check(not screen_record(r), "the quality gate passes", screen_record(r)[:1])
        check(r["text"].count("-----BEGIN") == 1, "one key per document")
    top = max(x[3] for x in LENGTH_BANDS)
    check(not [r for r in records if len(r["text"]) > top],
          "no document is longer than the longest band, where the gate's default cap would apply")
    check(len(records) == 6000, "the corpus size is unchanged", len(records))
    for words in (len(r["text"].split()) for r in longs):
        check(words >= MIN_CARRIER_WORDS["extreme"], "enough carrier words", words)


TESTS = [("long key kinds", test_key_kinds), ("long documents", test_long_documents),
         ("a build with the family", test_build_gates)]

if __name__ == "__main__":
    for name, fn in TESTS:
        print(name)
        fn()
    print("=" * 60)
    print(f"PASSED {PASS}   FAILED {FAIL}")
    print("=" * 60)
    for f in FAILURES[:12]:
        print("  FAIL:", f)
    sys.exit(1 if FAIL else 0)
