"""Screen minted values against the leakage guard, at generation time.

The leakage guard (`eval/leakage_guard.py`, contract C4) fails a corpus when
a training text contains a distinctive benchmark value or a value of Person
3's shadow set. Real values were only checked by the guard *after* a build,
so with thousands of documents a few random collisions on short ID formats
(a driver licence is two letters + six digits) were certain, and every
build failed the gate.

`is_forbidden(value)` says whether the guard would fail on `value`, using the
guard's own loaders and rules, so the two cannot disagree:
  - benchmark values: `benchmarks/extracted/records.json`, `errors.csv` and
    `data/benchmark_v3/` (D-6), restricted exactly as check 1 restricts them
    (distinctive, not a D-2 allowlisted value, not low-entropy, not a
    fragment);
  - shadow values: by SHA-1 only, as check 3 compares them. The shadow texts
    never leave the machine (A2 rule 5).

`ValuePool.fresh()` and `negatives.make_decoy()` re-draw a forbidden value
the same way they re-draw a blocklisted placeholder. Loaded once, lazily
(~1.5 s). If the guard's inputs are missing (a checkout without
`benchmarks/` or `eval/`), screening is off and a warning says so: the guard
itself still runs as the gate before training.

One input that cannot be read does not switch the rest off (P4-2 round 2).
A benchmark file that is still a Git LFS pointer (`git lfs pull` was not run)
is skipped with an ERROR naming it, and the other inputs keep screening;
with the whole screen off, random licence numbers collide with benchmark
values and the guard fails the build.
"""
from __future__ import annotations

import functools
import hashlib
import logging
import sys
from pathlib import Path

log = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parents[2]
_BENCH_DOCS = [_ROOT / "data" / "benchmark_v3" / "pii_az_benchmark_v3_structured_9780.jsonl"]


def _is_lfs_pointer(path: Path) -> bool:
    with open(path, "rb") as fh:
        return fh.read(40).startswith(b"version https://git-lfs")


def _readable_docs() -> list[Path]:
    """The benchmark documents that can be read: a file that is missing is
    left out quietly (the guard says so itself); one that is an LFS pointer is
    left out with an ERROR, because its values are then not screened."""
    out = []
    for p in _BENCH_DOCS:
        if not p.exists():
            continue
        if _is_lfs_pointer(p):
            log.error("leak_screen: %s is a Git LFS pointer, not the file (run `git lfs pull`); "
                      "its values are NOT screened and the leakage guard may fail this build", p)
            continue
        out.append(p)
    return out


@functools.lru_cache(maxsize=None)
def _guard():
    """The leakage guard itself, built from its own inputs (benchmark values
    and 8-grams, D-2 allowlist, 8-gram stoplist, shadow hashes), or None."""
    try:
        sys.path.insert(0, str(_ROOT / "eval"))
        import leakage_guard as lg
    except ImportError:
        log.warning("leak_screen: eval/leakage_guard.py not found; values are not screened")
        return None
    finally:
        if sys.path and sys.path[0] == str(_ROOT / "eval"):
            sys.path.pop(0)
    try:
        values, grams = lg.load_benchmark(_readable_docs())
        allow, _ = lg.load_allowlist()
        shadow = lg.load_shadow(lg.SHADOW_HASHES)
        return lg.Guard(values, grams, allow, lg.load_stoplist(), shadow)
    except (OSError, ValueError, SystemExit) as exc:
        log.warning("leak_screen: guard inputs unavailable (%s); values are not screened", exc)
        return None


@functools.lru_cache(maxsize=None)
def _sets() -> tuple[frozenset[str], frozenset[str]]:
    """-> (forbidden benchmark values, SHA-1 hex of shadow values)."""
    guard = _guard()
    if guard is None:
        return frozenset(), frozenset()
    bench = frozenset(v for v in guard.checked
                      if v not in guard.allowlist and v not in guard.low_entropy)
    shadow_sha1 = frozenset(v[2] for vs in guard.sh_values.values() for v in vs)
    return bench, shadow_sha1


def forbidden_ngrams(text: str) -> list[str]:
    """The 8-grams of `text` the guard's checks 2 and 3 would fail: a benchmark
    8-gram, or the SHA-1 of a shadow 8-gram, minus the reviewed stoplist.

    Values are screened one by one, but an 8-gram can span a value and the
    words around it: a minted URL (`https://secure.bakusteel.az/oauth/callback
    ?reset_token=...`) gives seven fixed words, and the frame word before it
    (`link`) made a benchmark 8-gram in a 5,000-document build (D-19e). The
    builder rejects such a document and builds another."""
    guard = _guard()
    if guard is None:
        return []
    import leakage_guard as lg  # imported by _guard(); cached in sys.modules
    ws = lg.words(text)
    out = []
    for i in range(len(ws) - lg.N + 1):
        if ws[i] in guard.first:
            g = " ".join(ws[i:i + lg.N])
            if g in guard.grams:
                out.append(g)
    if guard.sh_grams:
        out += [g for g in lg.ngrams(ws)
                if hashlib.sha1(g.encode("utf-8")).digest() in guard.sh_grams]
    return out


def is_forbidden(value: str) -> bool:
    """True if the leakage guard would fail a corpus containing `value`."""
    bench, shadow = _sets()
    if value in bench:
        return True
    if not shadow or _is_vocabulary(value):
        return False  # the guard never fails on words and names (check 3)
    return hashlib.sha1(value.encode("utf-8")).hexdigest() in shadow


def forbidden_values(text: str) -> list[str]:
    """The values the guard's check 1 (benchmark values) and check 3 (shadow
    values) would fail in `text`: found INSIDE the text, bounded by any
    non-word character, not only as a whole minted value.

    `is_forbidden` compares a minted value with the benchmark values by
    equality, but the guard finds a benchmark value wherever it sits between
    non-word characters, and `:` is one: the P4-3 build (seed 20261001)
    failed on `2001:db8::e486:33b:959d`, whose prefix `2001:db8::e486` is a
    benchmark value. Allowlisted (D-2) and low-entropy values are reported by
    the guard, not failed, so they are not returned here either. Shadow
    values come back as their SHA-1."""
    guard = _guard()
    if guard is None:
        return []
    import leakage_guard as lg  # imported by _guard(); cached in sys.modules
    out = []
    for m in lg.WORD.finditer(text):
        for v, off in guard.index.get(m.group(), ()):
            s = m.start() - off
            if (s >= 0 and text[s:s + len(v)] == v and lg._bounded(text, s, s + len(v))
                    and v not in guard.allowlist and v not in guard.low_entropy):
                out.append(v)
    if guard.sh_values:
        for m in lg.WORD.finditer(text):
            cands = guard.sh_values.get(hashlib.sha1(m.group().encode("utf-8")).digest())
            for off, length, vh in cands or ():
                s = m.start() - off
                if (s >= 0 and lg._bounded(text, s, s + length)
                        and not lg.is_vocabulary(text[s:s + length])
                        and lg.sha1(text[s:s + length]) == vh):
                    out.append(vh)
    return out


def _is_vocabulary(value: str) -> bool:
    _guard()
    import leakage_guard as lg  # imported by _guard(); cached in sys.modules
    return lg.is_vocabulary(value)
