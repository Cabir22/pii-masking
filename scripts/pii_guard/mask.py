"""Turn detected spans into placeholders, and placeholders back into values.

Masking is a pure text edit over non-overlapping spans, applied right to left
so earlier offsets stay valid while later ones are being replaced. That is the
same arithmetic `piigen.sentinel` uses for the translation harness; the reason
this module does not simply call `sentinelize` is that the translation harness
needs opaque numbered slots (`⟦0⟧`) whose whole point is to carry *no* meaning,
whereas here the placeholder must carry the entity kind so the external model
can still reason (STEP 6). The offset handling is deliberately identical.

## Placeholder numbering

Numbers are allocated per family, in order of first appearance:

    [PERSON_001] met [PERSON_002] at [ADDRESS_001]

This is deterministic for a given document + config: run it twice, get the
same placeholders. It is *not* a hash of the value -- a hash would be stable
across documents, which leaks that two documents mention the same person, and
for a low-entropy value (a first name, a city) a hash is reversible by anyone
who can guess the input.

## Coreference: when is the same string the same entity?

With `coreference_by_value` (the default), two spans with the same family and
the same casefolded value get the same placeholder inside one document. So
"John Smith contacted John Smith" -> "[PERSON_001] contacted [PERSON_001]".

This is a *document-scoped heuristic and it is sometimes wrong*: two different
people can share a name, and "Baku" as a city and "Baku" inside a company name
are different referents. It is the right default anyway, because the failure
is asymmetric --

* merging two distinct people costs the model some precision;
* splitting one person across two placeholders tells the model there are two
  parties where there is one, which corrupts the reasoning the pipeline
  exists to enable, and on rehydration produces text that reads as if two
  people were involved.

Set `coreference_by_value=False` to allocate one placeholder per occurrence.
Keys are scoped per document; nothing is shared between documents or sessions.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .config import GuardConfig
from .entities import Detection, resolve_overlaps
from .logging_ import safe_excerpt
from .vault import Vault


@dataclass(slots=True)
class MaskResult:
    """Sanitised text plus everything needed to reverse it locally."""

    text: str
    vault: Vault
    detections: list[Detection]

    @property
    def masked_count(self) -> int:
        return len(self.detections)

    def __repr__(self) -> str:  # never show text: it is post-mask but be terse
        return (f"MaskResult({len(self.text)} chars, "
                f"{len(self.detections)} spans, {self.vault!r})")


def _norm_key(value: str) -> str:
    """Coreference key for a value: NFKC, casefolded, whitespace collapsed.

    Casefold rather than lower so 'İ' and 'ß' behave; NFKC so a full-width or
    decomposed form of the same name does not get a second placeholder.
    """
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip().casefold()


def assign_placeholders(
    text: str, detections: list[Detection], config: GuardConfig | None = None,
) -> tuple[list[tuple[Detection, str]], Vault, list[Detection]]:
    """The placeholder-numbering half of `apply_mask`, split out so a caller
    that cannot work with one flat string (`extract/docx.py`'s write-back
    needs to splice each placeholder into the specific paragraph/cell run
    it came from, preserving formatting, not into a rejoined string) can
    still get the exact same (family, coreference, numbering) decisions
    `apply_mask` makes, instead of re-implementing them. `apply_mask` itself
    is now a thin wrapper around this plus the flat-string splice below --
    behavior for existing callers is unchanged (see test_pii_guard.py,
    still green after this split).

    Returns `(assigned, vault, kept)`: `assigned` pairs each kept Detection
    (left to right, so numbering reads naturally) with its placeholder
    string; `kept` is the same list, exposed separately because
    `MaskResult.detections` wants it without the placeholder tuple.
    """
    cfg = config or GuardConfig()
    kept = resolve_overlaps([d for d in detections
                             if d.label in cfg.labels and d.score >= cfg.min_score])

    vault = Vault()
    counters: dict[str, int] = {}
    assigned: list[tuple[Detection, str]] = []

    for det in kept:
        if text[det.start:det.end] != det.text:
            raise ValueError(
                f"detection does not match the text it indexes at "
                f"[{det.start}:{det.end}) for {det.label} -- refusing to mask "
                f"with stale offsets.")
        # Defense in depth: a span crossing a segment boundary is always a
        # detector bug, never legitimate PII (see `_CAPRUN` in detect/names.py
        # for the concrete case this caught -- a name-shaped regex whose
        # separator matched newlines walked straight across
        # `extract.base.SEGMENT_JOIN` and fused unrelated text from two
        # different PPTX/DOCX segments into one placeholder). Catching it
        # here means any current or future detector with the same class of
        # bug fails loudly instead of silently mismasking.
        if "\n\n" in det.text:
            raise ValueError(
                f"a {det.label} detection spans a segment boundary "
                f"({safe_excerpt(det.text)}) -- this is a detector bug, not "
                f"real PII. Refusing to mask it.")
        family = det.family
        key = (family, _norm_key(det.text)) if cfg.coreference_by_value else None

        placeholder = vault.placeholder_for(key) if key is not None else None
        if placeholder is None:
            counters[family] = counters.get(family, 0) + 1
            placeholder = cfg.placeholder_format.format(family=family, n=counters[family])
            vault.put(placeholder, det.text, key=key)
        assigned.append((det, placeholder))

    return assigned, vault, kept


def apply_mask(text: str, detections: list[Detection],
               config: GuardConfig | None = None) -> MaskResult:
    """Replace every detection with a placeholder. Offsets must index `text`."""
    cfg = config or GuardConfig()
    assigned, vault, kept = assign_placeholders(text, detections, cfg)

    out = text
    for det, placeholder in reversed(assigned):   # right to left: offsets stay valid
        out = out[:det.start] + placeholder + out[det.end:]

    return MaskResult(text=out, vault=vault, detections=kept)


def rehydrate(text: str, vault: Vault) -> str:
    """Put real values back, locally, after the model has replied.

    Longest placeholder first so `[PERSON_1]` cannot eat the prefix of
    `[PERSON_10]` under a non-zero-padded custom format. Values are inserted
    verbatim and are never re-scanned for placeholders, so a value that
    happens to look like a placeholder cannot trigger a second substitution.
    """
    if not vault:
        return text
    out = text
    for placeholder in sorted(vault.placeholders(), key=len, reverse=True):
        value = vault.reveal(placeholder)
        if value is not None and placeholder in out:
            out = out.replace(placeholder, value)
    return out


def placeholder_pattern(config: GuardConfig | None = None) -> re.Pattern[str]:
    """Regex matching any placeholder this config can emit.

    Built by rendering the configured format with sentinels and escaping the
    literal parts, so a custom `placeholder_format` stays matchable.
    """
    cfg = config or GuardConfig()
    rendered = cfg.placeholder_format.format(family="\x00FAM\x00", n=0)
    # the numeric field may be zero-padded; match any run of digits there
    literal = re.escape(rendered)
    literal = literal.replace(re.escape("\x00FAM\x00"), r"[A-Z_]+")
    literal = re.sub(r"0+", r"\\d+", literal, count=1)
    return re.compile(literal)
