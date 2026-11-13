"""DOCX extraction, plus the round-trip path: write masked/rehydrated text
back into the same paragraph/cell objects, and find+redact embedded images.

`document.paragraphs` alone misses two real PII locations: text inside table
cells, and header/footer content (a letterhead's name/address/phone is a very
common PII source, and it lives outside `document.paragraphs` entirely). Both
are walked explicitly here.

## Read vs. round-trip

`extract()` is the read-only path `pipeline.sanitize_document()` already
uses (chathal's failover attachment case: extract text, mask it, send it,
never touch the file again). It returns the same `ExtractedDocument`
`extract/base.py` defines for every format, unchanged.

`extract_for_roundtrip()` is additive, for the "produce a masked/rehydrated
.docx to write back to disk" case (`pipeline.sanitize_document_to_docx()`,
`pipeline.rehydrate_document()`). It calls the exact same segment-building
logic as `extract()` (so segment order/content/offsets are guaranteed
identical -- both are driven by `_build_segments`, not two independently
maintained walks that could drift apart) and additionally keeps, per
segment, a `_SegmentWriter` that knows how to splice edits back into the
actual python-docx object(s) that segment came from. `extract/base.py`'s
shared `Segment`/`ExtractedDocument` contract is deliberately left
untouched -- the writers live alongside it, not inside it, so this does not
risk the stability `mask/pptx` and other sibling branches depend on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .base import ExtractedDocument, ExtractionDependencyMissing, ExtractionError, Segment
from .docx_runs import apply_edits

try:
    import docx as _docx
except ImportError:
    _docx = None


def _require_docx() -> None:
    if _docx is None:
        raise ExtractionDependencyMissing(
            "python-docx is not installed. `pip install python-docx` to "
            "process .docx files.")


@dataclass(slots=True)
class _ParagraphWriter:
    """Splices local edits into one paragraph's runs, preserving formatting."""

    paragraph: object

    def apply(self, edits: list[tuple[int, int, str]]) -> None:
        apply_edits(self.paragraph, edits)


@dataclass(slots=True)
class _RowWriter:
    """Routes edits landing in a `" | "`-joined table-row segment to the
    specific cell paragraph they fall in.

    `cell_spans`: `(local_start, local_end, _ParagraphWriter)` per cell,
    in the same order/offsets `" | ".join(cells)` produced during
    extraction -- so an edit's local offset (already relative to the row
    segment's own text) can be translated to an offset relative to the one
    cell it belongs to.
    """

    cell_spans: list[tuple[int, int, "_ParagraphWriter"]]

    def apply(self, edits: list[tuple[int, int, str]]) -> None:
        by_cell: dict[int, list[tuple[int, int, str]]] = {}
        for start, end, replacement in edits:
            owner = None
            for i, (cs, ce, _writer) in enumerate(self.cell_spans):
                if cs <= start and end <= ce:
                    owner = i
                    break
            if owner is None:
                # Mirrors mask.apply_mask's own "\n\n segment boundary"
                # defense-in-depth check: a detection straddling the " | "
                # cell separator is always a detector bug, never real PII
                # (no PII value legitimately contains this package's own
                # row-joining separator) -- fail loudly rather than write a
                # corrupted cell.
                raise ValueError(
                    f"edit [{start}:{end}) does not fall entirely within one "
                    f"table cell of this row -- this is a detector bug (an "
                    f"entity should never span the ' | ' cell separator), "
                    f"not real PII. Refusing to write it.")
            cs, _ce, _writer = self.cell_spans[owner]
            by_cell.setdefault(owner, []).append((start - cs, end - cs, replacement))
        for i, cell_edits in by_cell.items():
            self.cell_spans[i][2].apply(cell_edits)


def _build_segments(document) -> tuple[list[Segment], list[object], list[str]]:
    """The one segment walk both `extract()` and `extract_for_roundtrip()`
    call, so the two paths can never disagree about segment order, content,
    or offsets -- see the module docstring for why that guarantee matters.

    Returns `(segments, writers, warnings)`, `writers[i]` corresponding to
    `segments[i]` (a `_ParagraphWriter` or `_RowWriter`); `extract()`
    discards `writers`, `extract_for_roundtrip()` keeps them.
    """
    segments: list[Segment] = []
    writers: list[object] = []
    warnings: list[str] = []

    for i, para in enumerate(document.paragraphs, start=1):
        if para.text.strip():
            segments.append(Segment(kind="paragraph", text=para.text, index=i))
            writers.append(_ParagraphWriter(para))

    # One segment per ROW, not per cell. A 2-column table is very often a
    # label/value pair in adjacent cells ("Phone" | "+994 50 123 45 67"),
    # and detection needs to see them together -- the anchor/cue tier's
    # phone/CVV/date detectors specifically look for a licensing word near
    # the value, and a label cell is exactly that word. Splitting each cell
    # into its own segment (the original design) put a hard boundary
    # between "Phone" and its own number, so the anchor could never see it
    # -- found by testing this exact "Phone | <number>" layout, the single
    # most common real-world table shape, not by inspection. Joined with
    # " | " so the row's structure is still legible in the sanitised output
    # (STEP 6 -- this doubles as a real quality improvement: previously a
    # label and its value had NO structural relationship in the extracted
    # text at all).
    #
    # Round-trip note: a cell with more than one paragraph (python-docx's
    # `cell.text` already joins them with "\n") is written back through its
    # FIRST paragraph only -- rare in practice (every table this project
    # generates, including gen_test_docs.py's own fixtures, uses
    # single-paragraph cells) and flagged here rather than silently
    # mishandled: a genuinely multi-paragraph cell would need per-paragraph
    # sub-offsets this format doesn't currently track.
    for ti, table in enumerate(document.tables, start=1):
        for ri, row in enumerate(table.rows, start=1):
            cell_texts = [(c.text, c) for c in row.cells if c.text.strip()]
            if not cell_texts:
                continue
            joined = " | ".join(t for t, _c in cell_texts)
            segments.append(Segment(kind="table_row", text=joined,
                                    index=ti * 10_000 + ri))
            cell_spans = []
            pos = 0
            for text, cell in cell_texts:
                cell_spans.append((pos, pos + len(text),
                                   _ParagraphWriter(cell.paragraphs[0])))
                pos += len(text) + 3          # + len(" | ")
            writers.append(_RowWriter(cell_spans))

    try:
        for si, section in enumerate(document.sections, start=1):
            for kind, part in (("header", section.header), ("footer", section.footer)):
                for para in part.paragraphs:
                    if para.text.strip():
                        segments.append(Segment(kind=kind, text=para.text, index=si))
                        writers.append(_ParagraphWriter(para))
    except Exception as exc:                    # header/footer access can fail on odd files
        warnings.append(f"header/footer extraction incomplete: {exc}")

    return segments, writers, warnings


def extract(path: str | Path) -> ExtractedDocument:
    _require_docx()
    path = Path(path)
    try:
        document = _docx.Document(str(path))
    except Exception as exc:
        raise ExtractionError(
            f"could not open {path.name} as a DOCX file "
            f"({type(exc).__name__}: {exc})") from exc

    segments, _writers, warnings = _build_segments(document)

    doc = ExtractedDocument(source=path.name, format="docx",
                            segments=segments, warnings=warnings)
    if doc.is_empty and not warnings:
        warnings.append("no extractable text found (empty or image-only document)")
        doc.warnings = warnings
    return doc


# ---------------------------------------------------------------------------
# round-trip: write masked/rehydrated text back into the same document
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class DocxRoundTrip:
    """Everything `pipeline.sanitize_document_to_docx()`/`rehydrate_document()`
    need: the open Document (kept alive for `.save()`), the same
    `ExtractedDocument` `extract()` would have produced, and each segment's
    position within the joined text plus its writer.
    """

    document: object
    extracted: ExtractedDocument
    #: [start, end) of each segment within `extracted.text` (the same
    #: SEGMENT_JOIN-joined string `pipeline.py` runs detection over).
    segment_ranges: list[tuple[int, int]]
    writers: list[object]

    def apply_joined_edits(self, edits: list[tuple[int, int, str]]) -> int:
        """Edits as `(start, end, replacement)` in `extracted.text`
        (joined-document) coordinates -- translates each to its segment's
        local coordinates and dispatches to that segment's writer. An edit
        spanning two segments is refused (mirrors `mask.apply_mask`'s own
        "\\n\\n segment boundary" check) rather than silently corrupting
        one of them.
        """
        by_segment: dict[int, list[tuple[int, int, str]]] = {}
        for start, end, replacement in edits:
            owner = None
            for i, (rs, re_) in enumerate(self.segment_ranges):
                if rs <= start and end <= re_:
                    owner = i
                    break
            if owner is None:
                raise ValueError(
                    f"edit [{start}:{end}) does not fall entirely within one "
                    f"segment -- this is a detector bug (an entity should "
                    f"never span extract.base.SEGMENT_JOIN), not real PII. "
                    f"Refusing to write it.")
            rs, _re = self.segment_ranges[owner]
            by_segment.setdefault(owner, []).append(
                (start - rs, end - rs, replacement))
        applied = 0
        for i, seg_edits in by_segment.items():
            self.writers[i].apply(seg_edits)
            applied += len(seg_edits)
        return applied

    def save(self, output_path: str | Path) -> None:
        self.document.save(str(output_path))


def extract_for_roundtrip(path: str | Path) -> DocxRoundTrip:
    """Like `extract()`, but keeps what's needed to write edits back."""
    _require_docx()
    path = Path(path)
    try:
        document = _docx.Document(str(path))
    except Exception as exc:
        raise ExtractionError(
            f"could not open {path.name} as a DOCX file "
            f"({type(exc).__name__}: {exc})") from exc

    segments, writers, warnings = _build_segments(document)

    doc = ExtractedDocument(source=path.name, format="docx",
                            segments=segments, warnings=warnings)
    if doc.is_empty and not warnings:
        warnings.append("no extractable text found (empty or image-only document)")
        doc.warnings = warnings

    from .base import SEGMENT_JOIN
    ranges: list[tuple[int, int]] = []
    pos = 0
    for i, seg in enumerate(segments):
        if i > 0:
            pos += len(SEGMENT_JOIN)
        ranges.append((pos, pos + len(seg.text)))
        pos += len(seg.text)

    return DocxRoundTrip(document=document, extracted=doc,
                         segment_ranges=ranges, writers=writers)


# ---------------------------------------------------------------------------
# embedded images
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class EmbeddedImage:
    """One image actually referenced by the document body or a header/
    footer part (inline or floating -- `part.rels` walks package
    *relationships*, not the drawing XML, so this doesn't need to
    special-case `wp:inline` vs `wp:anchor`)."""

    blob: bytes
    content_type: str
    _part: object = field(repr=False)

    def replace(self, new_bytes: bytes) -> None:
        """Overwrite this image's pixel data in place. Relationship IDs,
        placement and dimensions in document.xml are untouched -- only the
        bytes `document.save()` writes out for this part change."""
        self._part._blob = new_bytes
        if hasattr(self._part, "_image"):
            self._part._image = None


def _content_parts(document):
    yield document.part
    seen: set[int] = set()
    for section in document.sections:
        for part in (getattr(section, "header", None), getattr(section, "footer", None)):
            if part is None or part.part is None or id(part.part) in seen:
                continue
            seen.add(id(part.part))
            yield part.part


def find_embedded_images(document) -> list[EmbeddedImage]:
    """Every embedded image in the document body or a header/footer.

    Deliberately does NOT look at `docProps/thumbnail.jpeg`: that is an
    OS-generated preview reachable only from the package-level
    `_rels/.rels`, not from any content part, and is not guaranteed to
    reflect the document as edited.
    """
    found: list[EmbeddedImage] = []
    seen_partnames: set = set()
    for part in _content_parts(document):
        for rel in part.rels.values():
            if rel.is_external:
                continue
            target = rel.target_part
            if not target.content_type.startswith("image/"):
                continue
            if target.partname in seen_partnames:
                continue
            seen_partnames.add(target.partname)
            found.append(EmbeddedImage(blob=target.blob,
                                       content_type=target.content_type,
                                       _part=target))
    return found
