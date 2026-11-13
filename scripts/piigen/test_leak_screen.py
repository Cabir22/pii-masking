# -*- coding: utf-8 -*-
"""Tests for leak_screen: no minted value may be one the leakage guard fails.

Run: python scripts/piigen/test_leak_screen.py
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from piigen import leak_screen                                  # noqa: E402
from piigen.leak_screen import is_forbidden                     # noqa: E402
from piigen.negatives import active_decoy_kinds, make_decoy     # noqa: E402
from piigen.values import ValueFactory, ValuePool               # noqa: E402

PASSED = FAILED = 0


def check(cond, msg):
    global PASSED, FAILED
    if cond:
        PASSED += 1
    else:
        FAILED += 1
        print("FAIL", msg)


bench, shadow = leak_screen._sets()
check(len(bench) > 10_000, f"benchmark values loaded ({len(bench)})")
check(len(shadow) > 1_000, f"shadow value hashes loaded ({len(shadow)})")

# The two licence numbers that collided in the 2026-10-02 build.
for v in ("AA036449", "AA352785"):
    check(is_forbidden(v), f"{v} is a benchmark value")
# D-2 allowlisted dummies stay allowed; low-entropy values are not failures.
for v in ("4242424242424242", "P12345678", "A12B34", "1234"):
    check(not is_forbidden(v), f"{v} is allowlisted (D-2)")
check(not is_forbidden("ZQ918273"), "an unused licence-shaped value is allowed")

# Words and names are vocabulary, also with an apostrophe suffix (P2-4c), so
# a real city in the shadow set is no leak; codes stay distinctive.
import leakage_guard as lg                                      # noqa: E402
for v in ("Ordubad'ı", "Bakı'da", "Əsgər\u2019in", "Məmmədov", "BUZoVNA"):
    check(lg.is_vocabulary(v), f"{v} is vocabulary")
for v in ("AUJAKHM", "AA036449", "'quoted'", "O'Brien1"):
    check(not lg.is_vocabulary(v), f"{v} is not vocabulary")

# fresh() re-draws a forbidden value and counts it.
seq = iter(["AA036449", "AA352785", "ZQ918273"])
pool = ValuePool(state_path=None)
check(pool.fresh("AZ_DRIVER_LICENSE_NUMBER", lambda: next(seq)) == "ZQ918273",
      "fresh() skips forbidden values")
check(pool.leak_redraws["AZ_DRIVER_LICENSE_NUMBER"] == 2, "redraws counted")

# Every label's minted values are clean (40,000 draws in total).
factory = ValueFactory(random.Random(11), ValuePool(state_path=None))
labels = [m for m in dir(factory) if not m.startswith("_") and callable(getattr(factory, m))]
minted = 0
for name in labels:
    fn = getattr(factory, name)
    try:
        sample = [fn() for _ in range(1500)]
    except TypeError:
        continue  # needs arguments: not a plain minting method
    for v in sample:
        if isinstance(v, str) and v:
            minted += 1
            check(not is_forbidden(v), f"{name} minted forbidden value")
check(minted > 20_000, f"enough values minted ({minted})")

# Decoys: never forbidden unless allowlisted.
rng = random.Random(3)
for kind in active_decoy_kinds():
    for _ in range(100):
        v = make_decoy(kind, rng)
        check(not is_forbidden(v), f"decoy {kind.kind} is forbidden")

# One unreadable input does not switch the whole screen off (P4-2 round 2): a
# benchmark file that is still a Git LFS pointer is skipped with an ERROR, and
# the benchmark records and the shadow hashes keep screening.
import logging                                                  # noqa: E402
import tempfile                                                 # noqa: E402


class _Records(logging.Handler):
    def __init__(self):
        super().__init__(logging.ERROR)
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


with tempfile.TemporaryDirectory() as tmp:
    pointer = Path(tmp) / "bench.jsonl"
    pointer.write_text("version https://git-lfs.github.com/spec/v1\noid sha256:00\nsize 1\n", encoding="utf-8")
    saved = leak_screen._BENCH_DOCS
    handler = _Records()
    leak_screen.log.addHandler(handler)
    try:
        leak_screen._BENCH_DOCS = [pointer]
        leak_screen._guard.cache_clear()
        leak_screen._sets.cache_clear()
        bench_p, shadow_p = leak_screen._sets()
    finally:
        leak_screen._BENCH_DOCS = saved
        leak_screen._guard.cache_clear()
        leak_screen._sets.cache_clear()
        leak_screen.log.removeHandler(handler)
    check(len(bench_p) > 1_000, f"an LFS-pointer benchmark file: records still screen ({len(bench_p)})")
    check(len(shadow_p) > 1_000, "an LFS-pointer benchmark file: shadow hashes still screen")
    check(any("LFS pointer" in m and "bench.jsonl" in m for m in handler.messages),
          "the pointer is reported as an ERROR naming the file")
    check(len(bench_p) < len(bench), "and the file's own values are the ones not screened")
check(len(leak_screen._sets()[0]) == len(bench), "the real file is read again afterwards")

# D-19e: an 8-gram can span a value and the words around it. forbidden_ngrams
# runs the guard's checks 2-3 on a whole text, and the builder rebuilds a
# document that has one (a 5,000-document build at seed 3 failed on this one).
d19e = "Keçid: link https://secure.bakusteel.az/oauth/callback?reset_token=Qw3rTy9UiOp4AsDf"
check(leak_screen.forbidden_ngrams(d19e) == ["link https secure bakusteel az oauth callback reset_token"],
      "the D-19e URL sentence is a benchmark 8-gram")
check(leak_screen.forbidden_ngrams("Keçid: https://app.bakusteel.az/verify?token=Qw3rTy9UiOp4AsDf") == [],
      "the same host in another URL is not")
check(leak_screen.forbidden_ngrams("Salam, sənədləri sabah göndərəcəyik, zəhmət olmasa gözləyin.") == [],
      "an ordinary sentence is not")
stop = leak_screen._guard().stop
if stop:
    check(leak_screen.forbidden_ngrams(sorted(stop)[0]) == [], "a stoplisted 8-gram is ignored, as by the guard")
from piigen.targeted import builder as TB                       # noqa: E402
calls = {"n": 0}
real = TB.forbidden_ngrams


def _first_three(text):
    calls["n"] += 1
    return ["x"] if calls["n"] <= 3 else []


TB.forbidden_ngrams = _first_three
try:
    b = TB.TargetedBuilder(seed=2, n_docs=20)
    recs = b.build()
finally:
    TB.forbidden_ngrams = real
check(len(recs) == 20 and sum(v for k, v in b.rejections.items() if k.endswith("benchmark_ngram")) == 3,
      "the builder rebuilds a document with a benchmark 8-gram")

# P4-3: the guard's check 1 finds a benchmark value INSIDE the text, between
# non-word characters; `:` is one, so a minted IPv6 can contain a benchmark
# IPv6 as its prefix. forbidden_values runs checks 1 and 3 (values) on a text.
check(leak_screen.forbidden_values("IPv6 ünvanı 2001:db8::e486:33b:959d qeydə alınıb.") == ["2001:db8::e486"],
      "a benchmark IPv6 inside a longer minted IPv6 is found")
check(not is_forbidden("2001:db8::e486:33b:959d"), "...which the value screen alone cannot see")
check(leak_screen.forbidden_values("IPv6 ünvanı 2001:db8::e487:33b:959d qeydə alınıb.") == [],
      "a near miss is not")
check(leak_screen.forbidden_values("Test kartı 4242424242424242 və P12345678 istifadə olundu.") == [],
      "allowlisted (D-2) values are not, as in the guard")
check(leak_screen.forbidden_values("Bu gün hava çox gözəldir, sabah görüşərik.") == [], "an ordinary sentence is not")
calls = {"n": 0}
real_v = TB.forbidden_values


def _first_two(text):
    calls["n"] += 1
    return ["x"] if calls["n"] <= 2 else []


TB.forbidden_values = _first_two
try:
    b = TB.TargetedBuilder(seed=2, n_docs=20)
    recs = b.build()
finally:
    TB.forbidden_values = real_v
check(len(recs) == 20 and sum(v for k, v in b.rejections.items()
                              if k.endswith("benchmark_value_in_text")) == 2,
      "the builder rebuilds a document with a benchmark value inside its text")

print(f"PASSED {PASSED}   FAILED {FAILED}")
sys.exit(1 if FAILED else 0)
