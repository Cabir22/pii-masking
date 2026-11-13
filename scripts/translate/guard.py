"""SIMURG stream-integrity guard around a translation call.

SIMURG (github.com/doofzoff/SIMURG, pinned in requirements.txt) watches an
LLM's token stream and flags degenerate output: script drift, repetition
loops, structural breakdown, template/prompt leakage. It runs live, so a
document that goes bad is abandoned mid-generation rather than paid for in
full and thrown away afterwards.

Deliberately the low-level `Simurg` class rather than its `GuardedLLM`
convenience wrapper: `GuardedLLM` would replace our client entirely and take
the concurrency pool, full-jitter backoff and crash-safe resume with it.

What SIMURG does NOT cover, and the round-trip validator therefore must:
sentinel survival, span exactness, anchor survival, and any mistranslation
that is fluent and in the right script. The two are layered, not redundant.

One caveat worth remembering: SIMURG holds the first ~350 characters before
it judges anything and re-checks every ~400. For the `very_short` bucket
(40-150 chars) it never clears that window and returns `clean` trivially --
so "SIMURG clean" is not evidence of anything on a short document.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator

# Latin for en/tr, Cyrillic for ru. The templated text SIMURG sees is
# PII-free -- values are spliced in afterwards -- so a Latin identifier
# inside Russian output never trips the Cyrillic lock.
EXPECTED_SCRIPTS = {
    "en": ("latin",),
    "tr": ("latin",),
    "ru": ("cyrillic",),
}


class GuardAborted(RuntimeError):
    """SIMURG called the stream corrupt. Carries why, where it started, and
    the partial output so far (for the repair queue)."""

    def __init__(self, reasons, onset_char, partial: str = "") -> None:
        self.reasons = list(reasons or [])
        self.onset_char = onset_char
        self.partial = partial
        super().__init__(f"{'; '.join(self.reasons) or 'corrupt'}"
                         f" (onset_char={onset_char})")


@dataclass
class GuardResult:
    text: str
    state: str            # "clean" | "suspect"
    reasons: list


def make_guard(lang: str):
    """A fresh Simurg for one attempt.

    Fresh per attempt, never reused: it is stateful over a whole stream, so a
    recycled instance would judge the retry against the aborted stream's
    history.
    """
    from simurg import Simurg

    scripts = EXPECTED_SCRIPTS.get(lang)
    return Simurg(expected_scripts=scripts) if scripts else Simurg()


def guarded_stream(chunks: Iterable[str], lang: str) -> GuardResult:
    """Consume a delta stream under SIMURG, aborting the moment it goes bad.

    Raises GuardAborted on `corrupt` -- the caller retries or repair-queues.
    Returns `suspect` rather than raising: SIMURG's "maybe" is not worth
    discarding a document over, and the round-trip validator's deterministic
    checks are better placed to adjudicate.
    """
    guard = make_guard(lang)
    parts: list[str] = []
    numeric_only = False       # SIMURG went corrupt, but on numeric-dump alone
    for chunk in chunks:
        parts.append(chunk)
        if numeric_only:
            continue           # already downgraded; just accumulate the rest
        verdict = guard.feed(chunk)
        if verdict.state == "corrupt":
            if _numeric_dump_only(verdict.reasons):
                numeric_only = True   # and every later feed says "already aborted"
                continue
            _close(chunks)
            raise GuardAborted(verdict.reasons, verdict.onset_char,
                               "".join(parts))

    if numeric_only:
        return GuardResult("".join(parts), "suspect", ["numeric dump (downgraded)"])
    final = guard.finish()
    if final.state == "corrupt":
        if _numeric_dump_only(final.reasons):
            return GuardResult("".join(parts), "suspect", list(final.reasons or []))
        raise GuardAborted(final.reasons, final.onset_char, "".join(parts))
    return GuardResult("".join(parts), final.state, list(final.reasons or []))


def _numeric_dump_only(reasons) -> bool:
    """SIMURG's numeric-dump detector fires when the output is >~28% digits.
    The corpus is full of documents that are legitimately digit-dense --
    identifier lists in negatives, resumes and config dumps in positives --
    and a faithful translation of one stays digit-dense. That is fidelity,
    not degeneration, so we downgrade a numeric-dump-ONLY verdict to
    `suspect` (which warns, does not fail). Repetition loops, script drift
    and template leakage still abort the stream immediately.

    Note the "already aborted" case: once SIMURG is corrupt, every later
    `.feed()` returns that string and the original reason is gone -- so the
    caller latches `numeric_only` on the FIRST corrupt verdict and stops
    consulting the guard for the rest of the stream.
    """
    reasons = [str(r).lower() for r in (reasons or [])]
    return bool(reasons) and all("numeric dump" in r or "digit_frac" in r
                                 for r in reasons)


def _close(chunks) -> None:
    """Stop the underlying generator so the HTTP stream is released rather
    than left to finish generating tokens nobody will read."""
    close = getattr(chunks, "close", None)
    if callable(close):
        try:
            close()
        except Exception:  # noqa: BLE001 -- best effort; never mask the abort
            pass


def guarded_iter(chunks: Iterable[str], lang: str) -> Iterator[str]:
    """Same policy, but re-yields deltas for a caller that wants to display
    them. Not used by the batch harness; here so a future interactive tool
    does not reimplement the abort logic."""
    guard = make_guard(lang)
    for chunk in chunks:
        verdict = guard.feed(chunk)
        if verdict.state == "corrupt":
            _close(chunks)
            raise GuardAborted(verdict.reasons, verdict.onset_char)
        yield chunk
    final = guard.finish()
    if final.state == "corrupt":
        raise GuardAborted(final.reasons, final.onset_char)
