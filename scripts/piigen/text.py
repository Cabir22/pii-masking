"""TextBuilder -- the invariant the whole pipeline rests on.

Character offsets are recorded at the moment text is appended, never recovered
afterwards by string search. This is what makes tokenizer/label alignment bugs
structurally impossible to originate here, and it is the
one piece of the previous generator's design worth keeping. The difference is
that it now works at document scale rather than one-template scale, and it
knows how to remap spans when a finished document is transformed (indented,
quoted, wrapped, noised).

Why not just `text.find(value)` afterwards? Because a value can legitimately
occur more than once, can occur inside another entity, and can occur inside
text that merely resembles it. Searching is a guess; recording is a fact.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Azerbaijani/Turkish diacritic folding, single source of truth.
#
# Lives here (the lowest-level module, which imports nothing internal) because
# two unrelated consumers must agree on it exactly:
#   * noise.py's `strip_diacritics` kind, which PRODUCES folded text
#   * resolver.py's suffix matchers, which must RECOGNISE the folded surface
#     forms that kind produces
# 2026-08-27 audit: they had diverged. The noise injector rewrote "-də" to
# "-de", a form no suffix list contained, so noised documents silently lost
# annotations ("Saat 14:35-de"). Deriving the folded variants from this map
# instead of hand-listing them is what stops that from recurring.
DIACRITIC_MAP = {
    "ə": "e", "Ə": "E", "ı": "i", "I": "I", "İ": "I", "ş": "s", "Ş": "S",
    "ğ": "g", "Ğ": "G", "ö": "o", "Ö": "O", "ü": "u", "Ü": "U",
    "ç": "c", "Ç": "C", "ё": "е", "Ё": "Е", "й": "и",
}


def fold_diacritics(value: str) -> str:
    """The `strip_diacritics` surface form of `value`."""
    return "".join(DIACRITIC_MAP.get(ch, ch) for ch in value)


@dataclass
class Span:
    start: int
    end: int
    label: str

    def as_dict(self, text: str) -> dict:
        return {"start": self.start, "end": self.end,
                "label": self.label, "text": text[self.start:self.end]}


class TextBuilder:
    """Append-only buffer that records entity spans as they are written."""

    __slots__ = ("_parts", "_len", "_spans")

    def __init__(self) -> None:
        self._parts: list[str] = []
        self._len = 0
        self._spans: list[Span] = []

    # -- writing ----------------------------------------------------------
    def write(self, s: str) -> "TextBuilder":
        """Append literal text that contains no entity."""
        if s:
            self._parts.append(s)
            self._len += len(s)
        return self

    def entity(self, label: str, value: str) -> "TextBuilder":
        """Append `value` and record it as an entity of `label`."""
        if not value:
            return self
        start = self._len
        self._parts.append(value)
        self._len += len(value)
        self._spans.append(Span(start, self._len, label))
        return self

    def nl(self, n: int = 1) -> "TextBuilder":
        return self.write("\n" * n)

    # -- inspection -------------------------------------------------------
    def __len__(self) -> int:
        return self._len

    @property
    def text(self) -> str:
        # Collapse lazily so repeated len() calls stay O(1).
        if len(self._parts) > 1:
            joined = "".join(self._parts)
            self._parts = [joined]
        return self._parts[0] if self._parts else ""

    @property
    def spans(self) -> list[Span]:
        return list(self._spans)

    def entity_values(self) -> list[tuple[str, str]]:
        t = self.text
        return [(s.label, t[s.start:s.end]) for s in self._spans]

    # -- composition ------------------------------------------------------
    def extend(self, other: "TextBuilder") -> "TextBuilder":
        """Append another builder's content, shifting its spans into place."""
        offset = self._len
        other_text = other.text
        if other_text:
            self._parts.append(other_text)
            self._len += len(other_text)
        for sp in other._spans:
            self._spans.append(Span(sp.start + offset, sp.end + offset, sp.label))
        return self

    def append_block(self, text: str, entities: list[dict]) -> "TextBuilder":
        """Append already-rendered text plus its spans, shifted into place.

        Used when a block was built separately and then transformed (email
        quoting, indentation). The spans arrive already correct relative to
        `text`, so they only need the current offset added -- never re-found.
        """
        offset = self._len
        if text:
            self._parts.append(text)
            self._len += len(text)
        for e in entities:
            self._spans.append(Span(e["start"] + offset, e["end"] + offset,
                                    e["label"]))
        return self

    def result(self) -> tuple[str, list[dict]]:
        text = self.text
        ents = [s.as_dict(text) for s in sorted(self._spans, key=lambda x: x.start)]
        return text, ents


# ---------------------------------------------------------------------------
# Offset-preserving transforms
#
# Any transformation of finished text must go through an OffsetMap so spans are
# remapped arithmetically instead of being re-found. Every noise transform and
# every quoting/indentation transform uses this.
# ---------------------------------------------------------------------------

class OffsetMap:
    """Maps positions in an original string to positions in a rewritten one.

    Built by replaying the rewrite as a sequence of (consume, emit) steps.
    """

    def __init__(self) -> None:
        # mapping[i] = position in the new string corresponding to original i
        self._map: list[int] = []
        self._out: list[str] = []
        self._out_len = 0

    def keep(self, s: str) -> None:
        """Text carried over unchanged."""
        for _ in s:
            self._map.append(self._out_len)
            self._out_len += 1
        self._out.append(s)

    def replace(self, original: str, new: str) -> None:
        """`original` characters become `new` characters."""
        # Every original char maps to the start of the replacement, so a span
        # boundary inside the replaced region lands consistently.
        for _ in original:
            self._map.append(self._out_len)
        self._out.append(new)
        self._out_len += len(new)

    def insert(self, s: str) -> None:
        """Text added with no original counterpart."""
        self._out.append(s)
        self._out_len += len(s)

    def delete(self, original: str) -> None:
        for _ in original:
            self._map.append(self._out_len)

    # -- results ----------------------------------------------------------
    @property
    def text(self) -> str:
        return "".join(self._out)

    def map_pos(self, pos: int) -> int:
        if pos < len(self._map):
            return self._map[pos]
        return self._out_len

    def remap(self, entities: list[dict], new_text: str) -> list[dict]:
        """Remap spans, dropping any that the transform destroyed."""
        out = []
        for e in entities:
            s = self.map_pos(e["start"])
            en = self.map_pos(e["end"])
            if s < en <= len(new_text):
                out.append({"start": s, "end": en, "label": e["label"],
                            "text": new_text[s:en]})
        return out


def transform(text: str, entities: list[dict], edits) -> tuple[str, list[dict]]:
    """Apply an ordered edit stream to text, remapping entity spans.

    `edits` is an iterable of (kind, original, replacement) where kind is one of
    "keep", "replace", "insert", "delete" and the originals concatenate back to
    `text` exactly. This contract is what guarantees offsets stay exact.
    """
    om = OffsetMap()
    for kind, original, replacement in edits:
        if kind == "keep":
            om.keep(original)
        elif kind == "replace":
            om.replace(original, replacement)
        elif kind == "insert":
            om.insert(replacement)
        elif kind == "delete":
            om.delete(original)
        else:
            raise ValueError(f"unknown edit kind {kind!r}")
    new_text = om.text
    return new_text, om.remap(entities, new_text)


def prefix_lines(text: str, entities: list[dict], prefix: str,
                 skip_first: bool = False) -> tuple[str, list[dict]]:
    """Prefix every line (email quoting, indentation, diff markers).

    Implemented through the edit stream so spans move by exactly the number of
    inserted characters preceding them.
    """
    edits = []
    at_line_start = True
    first_line = True
    for ch in text:
        if at_line_start:
            if not (skip_first and first_line):
                edits.append(("insert", "", prefix))
            at_line_start = False
            first_line = False
        edits.append(("keep", ch, ch))
        if ch == "\n":
            at_line_start = True
    return transform(text, entities, edits)
