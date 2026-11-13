"""One extract() per format, using the REAL shipped extractor wherever one
exists, so the audit measures the actual system and not a reimplementation.

Where no shipped extractor exists, that is recorded as a finding rather than
silently papered over with an ad-hoc one:

  txt   -> formats/txt.py
  csv   -> formats/csv_format.py
  xlsx  -> formats/excel_format.py
  docx  -> scripts/pii_guard/extract/docx.py
  pptx  -> scripts/pii_guard/extract/pptx.py
  pdf   -> NO SHIPPED EXTRACTOR ANYWHERE. pdfplumber is used here, flagged
           as ad-hoc, because extract/base.py records PDF was built and then
           deliberately removed from pii_guard's scope on 2026-09-14.

All of these live in this tree since the 2026-09-28 branch consolidation
(see docs/branches.md); before that no single branch held all six formats.
"""

from __future__ import annotations

import sys
from pathlib import Path


def extract_txt(path: Path) -> str:
    import txt as txt_mod
    return txt_mod.extract(path)


def extract_csv_cells(path: Path):
    """Returns (fieldnames, rows) exactly as the shipped handler does."""
    import csv_format
    return csv_format.extract(path)


def extract_csv_text(path: Path) -> str:
    """Flattened view of the CSV, for raw-model comparison only. The shipped
    pipeline never builds this string -- it works cell-wise -- so any number
    measured on it describes the model, not the product."""
    fieldnames, rows = extract_csv_cells(path)
    lines = [" | ".join(fieldnames)]
    for r in rows:
        lines.append(" | ".join(str(r.get(c, "")) for c in fieldnames))
    return "\n".join(lines)


def extract_xlsx_cells(path: Path):
    """Every non-empty cell as (sheet, row, col, value)."""
    import openpyxl
    from openpyxl.cell.cell import MergedCell
    wb = openpyxl.load_workbook(path)
    out = []
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell, MergedCell):
                    continue
                if cell.value in (None, ""):
                    continue
                out.append((ws.title, cell.row, cell.column, str(cell.value)))
    return out


def extract_xlsx_text(path: Path) -> str:
    """Flattened view -- raw-model comparison only, same caveat as CSV."""
    import openpyxl
    wb = openpyxl.load_workbook(path)
    lines = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            cells = [str(c) if c is not None else "" for c in row]
            if any(c.strip() for c in cells):
                lines.append(" | ".join(cells))
    return "\n".join(lines)


def extract_docx(path: Path) -> tuple[str, list]:
    """Real pii_guard DOCX extractor. Returns (joined_text, segments)."""
    from pii_guard.extract.docx import extract as dx
    from pii_guard.extract.base import SEGMENT_JOIN
    doc = dx(path)
    segs = list(doc.segments)
    return SEGMENT_JOIN.join(s.text for s in segs), segs


def extract_pptx(path: Path) -> tuple[str, list]:
    """Real pii_guard PPTX extractor. Returns (joined_text, segments)."""
    from pii_guard.extract.pptx import extract as px
    from pii_guard.extract.base import SEGMENT_JOIN
    doc = px(path)
    segs = list(doc.segments)
    return SEGMENT_JOIN.join(s.text for s in segs), segs


def extract_pdf(path: Path) -> str:
    """AD HOC -- there is no PDF extractor anywhere in this repository.
    pdfplumber's default layout-unaware text extraction, which is what the
    earlier PDF benchmarking in this project also used."""
    import pdfplumber
    parts = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            parts.append(t)
    return "\n".join(parts)


def extract_pdf_layout(path: Path) -> str:
    """Layout-preserving variant, to test whether reading order / column
    mixing is what hurts PDF rather than the model."""
    import pdfplumber
    parts = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            t = page.extract_text(layout=True) or ""
            parts.append(t)
    return "\n".join(parts)


#: Which formats have a real, shipped extractor, and where.
PROVENANCE = {
    "txt":  ("formats/txt.py", "main"),
    "csv":  ("formats/csv_format.py", "main"),
    "xlsx": ("formats/excel_format.py", "main"),
    "docx": ("scripts/pii_guard/extract/docx.py", "main"),
    "pptx": ("scripts/pii_guard/extract/pptx.py", "main"),
    "pdf":  (None, None),
}
