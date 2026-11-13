"""Phase 2: TXT -- the simplest format, proves the full pipeline end to end.

extract() turns a file on disk into a plain string (handling non-UTF-8
encodings). mask_text()/unmask_text() are format-agnostic in themselves --
they only need `detect_fn: (text) -> list[{start,end,label}]` and a key, so
they work identically whether `detect_fn` is the real model
(model.predict.detect_entities) or a stub, which is what makes this testable
without the trained checkpoint.

All 27 taxonomy labels now have a reversible mask in model.masking, so in
practice this reports nothing; the mechanism stays because a label with no
mask must never be silently left in plaintext. A span whose label isn't
reversibly maskable is NOT silently left in plaintext and NOT silently
dropped from the report -- `mask_text` returns it separately as
`unmasked_spans` so the caller always knows exactly what did and didn't get
protected. Silently shipping partial protection labelled "masked" would be
worse than not masking at all, since it would look safe when it isn't.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "model"))
from masking import LABEL_ALPHABET, mask_value, unmask_value  # noqa: E402

DetectFn = Callable[[str], list]


def extract(path: str | Path) -> str:
    """Reads a TXT file into a string, detecting the encoding if it isn't
    UTF-8. Real files are not always UTF-8 -- this is the one genuine gotcha
    for this format."""
    raw = Path(path).read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        import chardet
        detected = chardet.detect(raw)
        encoding = detected.get("encoding")
        if not encoding:
            raise ValueError(
                f"{path}: not valid UTF-8 and chardet could not identify "
                f"the encoding either (confidence data: {detected})")
        return raw.decode(encoding)


def _validate_spans(text: str, spans: list[dict]) -> None:
    """`detect_fn` is a pluggable boundary -- a stub, a future alternate
    detector, anything -- so its output is validated here rather than
    trusted, matching how the rest of this project treats overlapping spans
    as a hard error (resolver.py, validate_corpus.py) rather than something
    to silently tolerate.

    This exists because of a real bug found by deliberately probing with
    overlapping spans: with no check, mask_text ran to completion and
    returned a plausible-looking string with NO error -- but the overlapping
    region had been partially overwritten by the second span's masked value
    (each span's plaintext is read from the untouched original `text`, so
    the corruption is invisible at write time), and `unmask_text` given the
    same two overlapping spans back would decrypt neither one correctly:
    silent, unrecoverable data corruption with no error message.
    """
    n = len(text)
    ordered = sorted(spans, key=lambda s: s["start"])
    prev_end = -1
    for span in ordered:
        s, e = span["start"], span["end"]
        if not (0 <= s < e <= n):
            raise ValueError(
                f"detect_fn returned an out-of-bounds span {span!r} for "
                f"text of length {n}")
        if s < prev_end:
            raise ValueError(
                f"detect_fn returned overlapping spans (one ends at "
                f"{prev_end}, the next starts at {s}) -- masking two "
                f"overlapping regions independently would silently corrupt "
                f"the result and make it unrecoverable, so this is a hard "
                f"error rather than something to paper over")
        prev_end = e


def mask_text(text: str, detect_fn: DetectFn, key: bytes
             ) -> tuple[str, list[dict], list[dict]]:
    """Returns (masked_text, spans, unsupported_spans).

    `spans` is every span that WAS masked -- keep this, it's what
    `unmask_text` needs to reverse the operation on this same text.
    `unsupported_spans` is every detected span whose label has no reversible
    mask yet -- left untouched in `masked_text`, and the caller must decide
    what to do about it (currently: nothing masks these, so a caller sending
    this text anywhere PII-sensitive needs to check this list is empty
    first).

    Offsets are never invalidated mid-loop: `mask_value` always returns a
    same-length replacement (verified in test_masking.py, including the
    chunking path for over-length values), so every span's (start, end)
    stays valid through the whole loop regardless of processing order --
    PROVIDED the spans don't overlap, which `_validate_spans` checks before
    any mutation happens.
    """
    all_spans = detect_fn(text)
    _validate_spans(text, all_spans)

    spans, unsupported = [], []
    chars = list(text)
    for span in all_spans:
        label, s, e = span["label"], span["start"], span["end"]
        if label not in LABEL_ALPHABET:
            unsupported.append(span)
            continue
        chars[s:e] = mask_value(label, text[s:e], key)
        spans.append(span)
    return "".join(chars), spans, unsupported


def unmask_text(masked_text: str, spans: list[dict], key: bytes) -> str:
    """Reverses mask_text on the SAME text it produced, using the spans it
    returned. This is the straightforward case -- unmasking a document you
    masked yourself. Unmasking an EXTERNAL LLM's response (which may not
    preserve these exact offsets at all) is a different problem, scoped to
    Phase 5, not this function.
    """
    chars = list(masked_text)
    for span in spans:
        label, s, e = span["label"], span["start"], span["end"]
        chars[s:e] = unmask_value(label, masked_text[s:e], key)
    return "".join(chars)
