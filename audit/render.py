"""Renders audit/spec.py's content into all six formats.

Each renderer returns the path written AND the text that renderer believes
it put in the file, so audit/run_audit.py can measure EXTRACTION FIDELITY
(did the format's own extractor get back what the renderer put in?)
separately from DETECTION (did the model find the entities in whatever came
back?). Those are different failures and conflating them is exactly what
this audit exists to avoid.
"""

from __future__ import annotations

from pathlib import Path

import spec


# --------------------------------------------------------------------------
# TXT
# --------------------------------------------------------------------------

def render_txt(path: Path, lang: str, register: str, labels=None) -> str:
    if register == "prose":
        text = spec.prose_text(lang)
    elif register == "labeled":
        text = "\n".join(spec.labeled_lines(lang, labels))
    else:
        header, rows = spec.table_rows(lang, labels)
        # A table in a plain-text file is a delimited table; " | " matches
        # how the existing data/testing_samples row fixtures flatten one.
        text = "\n".join(" | ".join(r) for r in [header] + rows)
    path.write_text(text, encoding="utf-8")
    return text


# --------------------------------------------------------------------------
# CSV
# --------------------------------------------------------------------------

def render_csv(path: Path, lang: str, register: str, labels=None) -> str:
    import csv
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if register == "table":
            header, rows = spec.table_rows(lang, labels)
            w.writerow(header)
            for r in rows:
                w.writerow(r)
        elif register == "labeled":
            # Two columns: field name, field value -- the other natural CSV
            # shape for the same content.
            lbls = labels or spec.FIELD_LABELS[lang]
            w.writerow(["field", "value"])
            for r in spec.records(lang):
                for k in spec.FIELD_ORDER:
                    w.writerow([lbls[k], r[k]])
        else:
            # Section 8 Test 7: one flowing sentence inside a single cell,
            # one record per row.
            w.writerow(["note"])
            for r in spec.records(lang):
                w.writerow([spec._PROSE[lang].format(**r)])
    return ""  # cell-structured; fidelity is measured cell-wise, not as text


# --------------------------------------------------------------------------
# XLSX
# --------------------------------------------------------------------------

def render_xlsx(path: Path, lang: str, register: str, labels=None) -> str:
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    if register == "table":
        header, rows = spec.table_rows(lang, labels)
        ws.append(header)
        for r in rows:
            ws.append(r)
    elif register == "labeled":
        lbls = labels or spec.FIELD_LABELS[lang]
        ws.append(["field", "value"])
        for r in spec.records(lang):
            for k in spec.FIELD_ORDER:
                ws.append([lbls[k], r[k]])
    else:
        # Section 9 Test A: one cell holding a whole flowing sentence.
        ws.append(["note"])
        for r in spec.records(lang):
            ws.append([spec._PROSE[lang].format(**r)])
    wb.save(path)
    return ""  # not a flat-text format; fidelity measured cell-wise instead


# --------------------------------------------------------------------------
# DOCX
# --------------------------------------------------------------------------

def render_docx(path: Path, lang: str, register: str, labels=None) -> str:
    import docx
    d = docx.Document()
    if register == "prose":
        d.add_paragraph(spec.prose_text(lang))
        expected = spec.prose_text(lang)
    elif register == "labeled":
        lines = spec.labeled_lines(lang, labels)
        for ln in lines:
            d.add_paragraph(ln)
        expected = "\n".join(lines)
    else:
        header, rows = spec.table_rows(lang, labels)
        t = d.add_table(rows=1 + len(rows), cols=len(header))
        for j, h in enumerate(header):
            t.cell(0, j).text = h
        for i, r in enumerate(rows, start=1):
            for j, v in enumerate(r):
                t.cell(i, j).text = v
        expected = "\n".join(" | ".join(r) for r in [header] + rows)
    d.save(path)
    return expected


# --------------------------------------------------------------------------
# PPTX
# --------------------------------------------------------------------------

def render_pptx(path: Path, lang: str, register: str, labels=None) -> str:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    prs = Presentation()
    blank = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank)

    def textbox(left, top, width, height, text):
        tb = slide.shapes.add_textbox(Inches(left), Inches(top),
                                      Inches(width), Inches(height))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.text = text
        for p in tf.paragraphs:
            for r in p.runs:
                r.font.size = Pt(14)
        return tb

    if register == "prose":
        expected = spec.prose_text(lang)
        textbox(0.5, 0.5, 9.0, 4.0, expected)
    elif register == "labeled":
        lines = spec.labeled_lines(lang, labels)
        # One text box holding all lines -- the "body placeholder" shape.
        textbox(0.5, 0.5, 9.0, 5.0, "\n".join(lines))
        expected = "\n".join(lines)
    else:
        # A real PPTX table shape.
        header, rows = spec.table_rows(lang, labels)
        shape = slide.shapes.add_table(1 + len(rows), len(header),
                                       Inches(0.2), Inches(0.5),
                                       Inches(9.5), Inches(1.5))
        tbl = shape.table
        for j, h in enumerate(header):
            tbl.cell(0, j).text = h
        for i, r in enumerate(rows, start=1):
            for j, v in enumerate(r):
                tbl.cell(i, j).text = v
        expected = "\n".join(" | ".join(r) for r in [header] + rows)
    prs.save(path)
    return expected


def render_pptx_scattered(path: Path, lang: str) -> str:
    """Section 12 Test E: the SAME labeled fields, but every field in its own
    separate text box, one slide per record, which is how a real slide deck
    is actually built. This is the PPTX-specific structural variable -- one
    box vs. many -- held against render_pptx('labeled'), which puts identical
    text in a single box. Any difference between the two is attributable to
    text-box fragmentation alone.
    """
    from pptx import Presentation
    from pptx.util import Inches, Pt
    prs = Presentation()
    out_lines = []
    for r in spec.records(lang):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        lbls = spec.FIELD_LABELS[lang]
        for i, k in enumerate(spec.FIELD_ORDER):
            ln = f"{lbls[k]}: {r[k]}"
            out_lines.append(ln)
            tb = slide.shapes.add_textbox(
                Inches(0.3 + 4.7 * (i % 2)), Inches(0.3 + 0.65 * (i // 2)),
                Inches(4.5), Inches(0.6))
            tb.text_frame.text = ln
            for p in tb.text_frame.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(12)
    prs.save(path)
    return "\n".join(out_lines)


# --------------------------------------------------------------------------
# PDF
# --------------------------------------------------------------------------

def render_pdf(path: Path, lang: str, register: str, labels=None) -> str:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font = _register_unicode_font(pdfmetrics, TTFont)
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    c.setFont(font, 11)
    y = height - 60

    if register == "prose":
        expected = spec.prose_text(lang)
        for line in _wrap(expected, 88):
            c.drawString(50, y, line)
            y -= 16
    elif register == "labeled":
        lines = spec.labeled_lines(lang, labels)
        for ln in lines:
            c.drawString(50, y, ln)
            y -= 18
        expected = "\n".join(lines)
    else:
        header, rows = spec.table_rows(lang, labels)
        # A real laid-out table: fixed x positions per column, not a
        # pre-joined string. This is what makes PDF table extraction hard
        # and is the whole point of testing it.
        #
        # Values are NEVER truncated to fit. An earlier version of this
        # renderer clipped each cell to 14 characters, which destroyed the
        # email/phone/URL values in the file itself and then showed up in
        # the results as a PDF "extraction failure" -- a fabricated finding
        # caused by the test rig, not the pipeline. Instead the page is
        # turned landscape and the font shrunk until the widest row fits,
        # and _assert_fits below hard-fails if it still would not.
        c.setPageSize((height, width))          # landscape
        page_w = height
        col_w = [max(len(h), max((len(r[j]) for r in rows), default=0))
                 for j, h in enumerate(header)]
        total = sum(col_w)
        size = min(7.0, (page_w - 60) / (total * 0.62))
        c.setFont(font, size)
        xs, acc = [], 20.0
        for w_ in col_w:
            xs.append(acc)
            acc += w_ * size * 0.62
        _assert_fits(acc, page_w - 20, lang)
        y = width - 50
        for j, h in enumerate(header):
            c.drawString(xs[j], y, h)
        y -= size * 2
        for r in rows:
            for j, v in enumerate(r):
                c.drawString(xs[j], y, v)
            y -= size * 2
        expected = "\n".join(" | ".join(r) for r in [header] + rows)
    c.save()
    return expected


def _assert_fits(used: float, available: float, lang: str) -> None:
    if used > available:
        raise RuntimeError(
            f"PDF table for {lang} does not fit ({used:.0f}pt of "
            f"{available:.0f}pt). Refusing to render a clipped table: "
            f"clipped cells would be scored as a PDF extraction failure "
            f"that this renderer, not the pipeline, caused.")


_FONT_CACHE: list[str] = []


def _register_unicode_font(pdfmetrics, TTFont) -> str:
    """reportlab's built-in Helvetica cannot encode Azerbaijani (ə, ğ, ş) or
    Cyrillic -- characters silently become black boxes, which would show up
    as an EXTRACTION failure that this audit introduced itself rather than
    one the pipeline has. A real system font is registered instead, and
    run_audit.py asserts the extracted text round-trips.
    """
    if _FONT_CACHE:
        return _FONT_CACHE[0]
    candidates = [
        ("DejaVuSans", "/opt/homebrew/share/fonts/DejaVuSans.ttf"),
        ("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ("ArialUnicode", "/Library/Fonts/Arial Unicode.ttf"),
        ("Arial", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        ("Verdana", "/System/Library/Fonts/Supplemental/Verdana.ttf"),
        ("Tahoma", "/System/Library/Fonts/Supplemental/Tahoma.ttf"),
    ]
    for name, p in candidates:
        if Path(p).exists():
            try:
                pdfmetrics.registerFont(TTFont(name, p))
                _FONT_CACHE.append(name)
                return name
            except Exception:
                continue
    raise RuntimeError(
        "no Unicode-capable TTF found; PDF rendering would silently corrupt "
        "Azerbaijani/Cyrillic text and invalidate the PDF results")


def _wrap(text: str, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


RENDERERS = {
    "txt": render_txt, "csv": render_csv, "xlsx": render_xlsx,
    "docx": render_docx, "pptx": render_pptx, "pdf": render_pdf,
}
EXT = {"txt": ".txt", "csv": ".csv", "xlsx": ".xlsx",
       "docx": ".docx", "pptx": ".pptx", "pdf": ".pdf"}
