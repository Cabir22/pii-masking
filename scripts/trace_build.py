"""Trace the targeted build attempt by attempt (D-49: Windows vs Mac).

    python scripts/trace_build.py --seed 20261001 -n 25000 --upto 920 > trace.tsv

Runs the same build as `build_targeted_corpus.py -n N --seed S` and writes one
line per attempt until `--upto` documents are accepted: document index,
attempt, family, verdict (ok or the gate's reason), a hash of the composed
text, and hashes of the four random generators' states after the attempt.
Two traces from different machines show the first attempt where they part:
the same text with a different verdict means a gate behaves differently; a
different text means composition does; equal texts and verdicts with
different generator states mean a value or noise draw does.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.targeted import quotas as Q  # noqa: E402
from piigen.targeted.builder import TargetedBuilder  # noqa: E402


class Stop(Exception):
    pass


def h(x) -> str:
    return hashlib.sha256(repr(x).encode("utf-8")).hexdigest()[:12]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("-n", type=int, required=True)
    ap.add_argument("--upto", type=int, required=True)
    args = ap.parse_args()
    b = TargetedBuilder(args.seed, args.n, Q.load(None))
    state = {"doc": 0, "attempt": 0}
    check, accept = b._check, b._accept

    def traced_check(d, spec):
        record, reason = check(d, spec)
        rngs = "\t".join(h(r.getstate()) for r in (b.rng, b.values.rng, b.value_rng, b.noise_rng))
        print(f"{state['doc']}\t{state['attempt']}\t{spec.get('family')}\t{'ok' if record else reason}\t"
              f"{h(d.text)}\t{rngs}", flush=True)
        state["attempt"] += 1
        return record, reason

    def traced_accept(record):
        accept(record)
        state["doc"] += 1
        state["attempt"] = 0
        if state["doc"] >= args.upto:
            raise Stop

    b._check, b._accept = traced_check, traced_accept
    print("doc\tattempt\tfamily\tverdict\ttext\trng\tvalues_rng\tvalue_rng\tnoise_rng")
    try:
        b.build()
    except Stop:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
