"""The translation test run (19 Oct): ~300 documents of runb-az-v4.1's
train split, in the split's source proportions (old corpus, LLM, targeted).

    python reports/translation_test/make_sample.py <runb-az-v4.1 train.docs.jsonl> <out.jsonl> [--n 300]
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import sys


def source(r: dict) -> str:
    if r.get("_source") == "targeted" or str(r["id"]).startswith("runb_targeted"):
        return "targeted"
    return "old" if r.get("_old") else "llm"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("train")
    ap.add_argument("out")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--seed", type=int, default=20261019)
    a = ap.parse_args()
    by = collections.defaultdict(list)
    for line in open(a.train, encoding="utf-8"):
        r = json.loads(line)
        by[source(r)].append(r)
    total = sum(len(v) for v in by.values())
    rng = random.Random(a.seed)
    out = []
    for s in sorted(by):
        k = round(a.n * len(by[s]) / total)
        out += rng.sample(by[s], k)
    rng.shuffle(out)
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    c = collections.Counter(source(r) for r in out)
    free = collections.Counter(source(r) for r in out if not r["entities"])
    print(f"{len(out)} documents: " + ", ".join(f"{s} {c[s]} ({free[s]} PII-free)" for s in sorted(c)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
