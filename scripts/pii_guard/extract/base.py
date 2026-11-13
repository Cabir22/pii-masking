"""The extraction contract every format adapter implements.

This module is the seam right after "extraction": every adapter (`docx.py`,
`pptx.py`) turns its format into one `ExtractedDocument`, and everything
downstream (detect -> mask -> LLM) is format-agnostic from here on. Adding
another format means adding one adapter that returns this shape -- nothing
in `detect/`, `mask.py`, or `pipeline.py` changes. (PDF was built and then
removed from this service's scope 2026-09-14 -- a different contributor
owns it -- entirely by deleting `extract/pdf.py` and its one line in
`extract/__init__.py`'s dispatch table; this contract needed no change at
all, which is the reason it is shaped this way.)

A document is a list of `Segment`s rather than one flat string because:

* **offsets must stay attributable.** A `Detection`'s `start`/`end` are only
  meaningful within the segment they came from -- concatenating first and
  detecting second would need every detector to also track which page/slide/
  cell an offset fell in, for no benefit.
* **some segments are optional to send.** Speaker notes (PPTX), headers/
  footers (DOCX), and table cells often carry different sensitivity than
  slide/paragraph body text. Keeping them separate lets a caller filter
  before anything is masked or sent, rather than after.
* **a document can be processed per-segment or joined.** `pipeline.py` joins
  segments with a stable separator for masking (so cross-segment repeat
  mentions still get the same placeholder) but keeps the per-segment
  boundaries so a corrupted or unparseable segment cannot silently swallow
  the ones around it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

#: Segments are joined with this before detection, and re-split after, so an
#: entity can never straddle a segment boundary undetected.
SEGMENT_JOIN = "\n\n"


class ExtractionError(RuntimeError):
    """A document could not be safely extracted.

    Deliberately NOT caught anywhere in this package's own code and left to
    propagate to the caller: STEP 15's rule is "if we cannot confidently
    sanitise the text, do not send potentially unmasked PII" -- and text that
    failed to extract cleanly cannot be confidently sanitised, so the safe
    response is to stop, not to send whatever partial text was recovered.
    """


class ExtractionDependencyMissing(ExtractionError):
    """The format library is not installed.

    A distinct subclass from `ExtractionError` because the fix is different
    (install a package) and a caller may want to report it differently --
    e.g. a 503 "feature unavailable" rather than a 422 "this specific file
    is broken".
    """


@dataclass(slots=True)
class Segment:
    """One unit of extracted text with its provenance.

    `kind` values in use: "paragraph"/"table_row"/"header"/"footer" (DOCX),
    "slide_body"/"slide_notes" (PPTX). Not an enum on purpose -- new adapters
    can introduce a new kind without touching this module, and
    `pipeline.py`'s segment filter matches on the string.
    """

    kind: str
    text: str
    #: 1-indexed slide/paragraph number, for a human-readable report.
    index: int


@dataclass(slots=True)
class ExtractedDocument:
    """The output of every format adapter."""

    source: str                              # filename, for logging/reports
    format: str                              # "docx" | "pptx"
    segments: list[Segment] = field(default_factory=list)
    #: Non-fatal problems (an unparseable table, an unreadable shape). Never
    #: populated silently in strict mode -- see pipeline.py.
    warnings: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        """All segments joined. What actually gets sanitised."""
        return SEGMENT_JOIN.join(s.text for s in self.segments if s.text)

    @property
    def is_empty(self) -> bool:
        return not any(s.text.strip() for s in self.segments)

    def __repr__(self) -> str:  # never include text -- this may be logged
        return (f"ExtractedDocument({self.source!r}, format={self.format!r}, "
                f"{len(self.segments)} segments, {len(self.warnings)} warnings)")


def suffix_format(path: str | Path) -> str:
    """Map a filename to the adapter it needs, or raise."""
    suffix = Path(path).suffix.lower().lstrip(".")
    mapping = {"docx": "docx", "pptx": "pptx"}
    fmt = mapping.get(suffix)
    if fmt is None:
        raise ExtractionError(
            f"unsupported file type {suffix!r}. This service handles "
            f"docx, pptx. (PDF is owned by a different contributor's "
            f"workstream, not this package.)")
    return fmt
