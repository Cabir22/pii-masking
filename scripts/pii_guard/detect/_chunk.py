"""Clause-level chunking for the `ml_context` model call.

Exists to work around a measured, evidence-backed behavior of
`your-hf-org/masking-multilingual` (not a bug in this package or in
`model/predict.py`): the model's confidence in a real, correctly-recognized
entity decays as more tokens follow it in the *same inference call*, and can
collapse to ~0 well before any architectural length limit. Confirmed by
reading the model's raw per-token softmax directly on real paragraph text
from this package's own `gen_test_docs.py` fixtures -- see
`docs/pii_guard_model_notes.md` "Context-length collapse" for the full
decay curve and the control experiment that ruled out a tokenizer-offset or
Unicode-normalization bug as the cause instead.

Why this lives here and not in `model/predict.py`: `predict.py`'s own
stride/window machinery (`max_length=512, stride=256`) solves a *different*
problem -- a document longer than one model window. The collapse measured
here happens well *inside* a single window (~47 tokens, against a 512-token
window), so windowing never engages for the paragraphs it affects; splitting
the window differently would not help. This is specifically about how much
text sits *around* a name inside one otherwise-normal-length paragraph, which
is `detect.names`' concern (the only caller that feeds model-scale paragraph
text through a single inference call), not `predict.py`'s generic
long-document contract. `predict.py` is shared with other formats/tracks on
sibling branches; changing its windowing to special-case a short-range
collapse it wasn't built to address is a bigger, riskier change than solving
it at the one call site that has it.
"""

from __future__ import annotations

import re

#: Splits after a sentence-ending or clause-separating punctuation mark
#: followed by whitespace. Commas are included deliberately: real prose in
#: this package's own test fixtures is often one long comma-joined clause
#: with no internal '.'/'!'/'?' at all ("Tələbə: Elvin ..., doğum tarixi ...,
#: FİN ..., ünvan: ..."), which would otherwise stay one oversized chunk.
#: A comma directly followed by a digit (decimal-comma numbers, e.g. Turkish
#: "486,50 TL") is deliberately NOT a split point -- \s+ requires whitespace
#: after the punctuation, and "486,50" has none.
_CLAUSE_SPLIT = re.compile(r"(?<=[.!?,])\s+")

#: Any run of whitespace -- the fallback split unit for a clause with no
#: usable punctuation boundary at all (see `_greedy_pack`).
_WHITESPACE = re.compile(r"\s+")

#: Measured: confidence held through ~90-100 characters (~30-35 tokens) on
#: real paragraph text and only started collapsing beyond that; 100 leaves
#: headroom below where collapse was observed (~140 chars / ~47 tokens).
#: Raising this does not help the model's per-token subword fragmentation
#: on long alphanumeric values (a separate, unrelated behavior, confirmed
#: unaffected by chunk size up to 150 characters) and directly re-triggers
#: the collapse this module exists to avoid -- do not tune it up "for
#: safety" without re-measuring the decay curve.
DEFAULT_MAX_CHUNK_CHARS = 100


def _split_points(text: str, start: int, end: int, pattern: re.Pattern) -> list[int]:
    bounds = {start, end}
    for m in pattern.finditer(text, start, end):
        bounds.add(m.end())
    return sorted(bounds)


def _greedy_pack(text: str, unit_bounds: list[int], max_chars: int,
                 finer_pattern: re.Pattern | None) -> list[tuple[int, int]]:
    """Greedily merge consecutive units into chunks <= max_chars.

    A single unit that alone exceeds max_chars is never cut to fit --
    if `finer_pattern` is given it is re-split at that finer granularity
    and packed recursively (clause -> whitespace); at whitespace
    granularity (finer_pattern=None) a unit is one unbroken run of
    non-whitespace characters and is kept whole even if it overruns the
    target. A long PII value (a JWT, an IBAN, an access token) must never
    be cut mid-value just to satisfy a soft size target -- an early version
    of an equivalent chunker in a since-abandoned prototype did exactly
    that with a blind fixed-character split and corrupted a JWT in testing;
    this greedy/whitespace-safe design is the fix, built in from the start
    here rather than discovered as a regression.
    """
    spans: list[tuple[int, int]] = []
    cur_start: int | None = None
    cur_end: int | None = None
    for i in range(len(unit_bounds) - 1):
        us, ue = unit_bounds[i], unit_bounds[i + 1]
        if us >= ue:
            continue
        if ue - us > max_chars:
            if cur_start is not None:
                spans.append((cur_start, cur_end))
                cur_start = None
            if finer_pattern is not None:
                finer_bounds = _split_points(text, us, ue, finer_pattern)
                spans.extend(_greedy_pack(text, finer_bounds, max_chars, None))
            else:
                spans.append((us, ue))
            continue
        if cur_start is None:
            cur_start, cur_end = us, ue
        elif ue - cur_start <= max_chars:
            cur_end = ue
        else:
            spans.append((cur_start, cur_end))
            cur_start, cur_end = us, ue
    if cur_start is not None:
        spans.append((cur_start, cur_end))
    return spans


def chunk_spans(text: str, max_chars: int = DEFAULT_MAX_CHUNK_CHARS) -> list[tuple[int, int]]:
    """Non-overlapping [start, end) spans that exactly tile `text` (no gaps,
    no overlaps, no dropped characters), each at most `max_chars` long where
    a boundary allows it, preferring clause punctuation and falling back to
    whitespace. Never cuts inside a contiguous non-whitespace run.
    """
    if len(text) <= max_chars:
        return [(0, len(text))]
    clause_bounds = _split_points(text, 0, len(text), _CLAUSE_SPLIT)
    return _greedy_pack(text, clause_bounds, max_chars, _WHITESPACE)
