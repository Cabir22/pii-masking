"""PPTX extraction.

Slide body text and speaker notes are genuinely separate PII surfaces (STEP
9): a presenter's notes routinely contain things ("call John at +994... to
confirm before this slide") that never appear on the visible slide. Kept as
distinct segment kinds so a caller can decide whether notes should even be
part of what gets sent externally -- see `pipeline.py`'s `include_kinds`
parameter (`slide_notes` is excluded by default via
`DEFAULT_EXCLUDED_SEGMENT_KINDS`).

Text boxes and placeholders are walked the same way (`shape.text_frame`);
python-pptx exposes both through the same API, so there is no separate case
needed for "placeholder vs. text box" as the brief's table suggested.
"""

from __future__ import annotations

from pathlib import Path

from .base import ExtractedDocument, ExtractionDependencyMissing, ExtractionError, Segment

try:
    import pptx as _pptx
except ImportError:
    _pptx = None


def _require_pptx() -> None:
    if _pptx is None:
        raise ExtractionDependencyMissing(
            "python-pptx is not installed. `pip install python-pptx` to "
            "process .pptx files.")


def _shape_text(shape) -> list[str]:
    """Every text run in a shape, recursing into grouped shapes and tables."""
    out: list[str] = []
    if getattr(shape, "has_text_frame", False) and shape.has_text_frame:
        t = shape.text_frame.text
        if t.strip():
            out.append(t)
    if getattr(shape, "has_table", False) and shape.has_table:
        for row in shape.table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    out.append(cell.text)
    if getattr(shape, "shape_type", None) is not None and hasattr(shape, "shapes"):
        for sub in shape.shapes:                  # grouped shapes
            out.extend(_shape_text(sub))
    return out


def extract(path: str | Path) -> ExtractedDocument:
    _require_pptx()
    path = Path(path)
    try:
        presentation = _pptx.Presentation(str(path))
    except Exception as exc:
        raise ExtractionError(
            f"could not open {path.name} as a PPTX file "
            f"({type(exc).__name__}: {exc})") from exc

    segments: list[Segment] = []
    warnings: list[str] = []

    for si, slide in enumerate(presentation.slides, start=1):
        try:
            for shape in slide.shapes:
                for text in _shape_text(shape):
                    segments.append(Segment(kind="slide_body", text=text, index=si))
        except Exception as exc:
            warnings.append(f"slide {si}: shape extraction incomplete: {exc}")

        try:
            if slide.has_notes_slide:
                notes = slide.notes_slide.notes_text_frame.text
                if notes.strip():
                    segments.append(Segment(kind="slide_notes", text=notes, index=si))
        except Exception as exc:
            warnings.append(f"slide {si}: notes extraction incomplete: {exc}")

    doc = ExtractedDocument(source=path.name, format="pptx",
                            segments=segments, warnings=warnings)
    if doc.is_empty and not warnings:
        warnings.append("no extractable text found (empty or image-only slides)")
        doc.warnings = warnings
    return doc
