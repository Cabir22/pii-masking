"""Extract every table and error case from the 5000-document benchmark PDF.

Input:  benchmarks/masking_multilingual_benchmark_5000_detailed_report.pdf
Output: benchmarks/extracted/
          page_index.json     one entry per PDF page: section, kind, tables
          tables/pNNN_tK.csv  every table the PDF contains, verbatim cells
          errors.csv          one row per error entity from Appendix A
          records.json        Appendix A parsed per document (for analysis)

Tool: PyMuPDF (`pymupdf`). pdfplumber is not installed in this repo's venv;
PyMuPDF's `find_tables` gives the same cell grid. Its own cell-text
extraction drops underscores out of some label cells ("ACCESS TOKEN\\n_"),
so each cell's text is instead read with `page.get_text(clip=cell_bbox)`,
which returns the underscores intact.

Appendix values can wrap across lines inside a cell. The report gives every
value's character span, so `end - start` is used as ground truth to decide
whether a line break inside a value was a real space or a wrap.

Run:  python benchmarks/extract_report.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

import pymupdf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
PDF = HERE / "masking_multilingual_benchmark_5000_detailed_report.pdf"
OUT = HERE / "extracted"
TABLES = OUT / "tables"

APPENDIX_FIRST_PAGE = 22

LABELS = [
    "ACCESS_TOKEN", "API_KEY", "AZ_DRIVER_LICENSE_NUMBER", "AZ_FIN",
    "AZ_ID_CARD_NUMBER", "AZ_PASSPORT_NUMBER", "AZ_VOEN", "AGE",
    "BUILDINGNUM", "CARD_SECURITY_CODE", "CITY", "DATE", "EMAIL",
    "GIVENNAME", "IBAN", "ICCID", "IPV4_ADDRESS", "IPV6_ADDRESS",
    "MAC_ADDRESS", "PAYMENT_CARD_NUMBER", "PRIVATE_KEY", "STREET",
    "SURNAME", "TELEPHONENUM", "TIME", "URL", "ZIPCODE",
]
J = "\u0001"                       # marks a line break inside a cell
WS = f"[ {J}]"
LAB = "|".join(sorted(LABELS, key=len, reverse=True))
ENTRY = re.compile(
    rf"(?P<kind>GOLD{WS}+|HARD-NEGATIVE{WS}+\(maskalanmamalıdır\){WS}+)?"
    rf"(?P<label>{LAB}):{WS}*"
    rf"(?P<value>(?:(?!\[\d+:\d+\]).)*?){WS}*"
    rf"\[(?P<s>\d+):(?P<e>\d+)\]"
    rf"(?:;{WS}*score=(?P<score>[0-9.]+))?",
    re.S,
)
FILLER = re.compile(rf"Heç{WS}+nə{WS}+tapılmayıb|Bu{WS}+mövqedə{WS}+entity{WS}+gözlənilmir")
SPACES = re.compile(f"{WS}*")
HEADING = re.compile(r"^(\d{1,2}\.\s+\S.*|Əlavə\s+[A-Z]\..*)$")


def cell_lines(page, bbox) -> list[str]:
    if bbox is None:
        return []
    txt = page.get_text("text", clip=pymupdf.Rect(bbox))
    return [ln.strip() for ln in txt.split("\n") if ln.strip()]


def table_rows(page, table) -> list[list[list[str]]]:
    return [[cell_lines(page, bb) for bb in row.cells] for row in table.rows]


def clean_value(raw: str, s: int, e: int) -> tuple[str, bool]:
    """(value, span_length_matches). Uses end-start to undo PDF wrapping."""
    want = e - s
    spaced = raw.replace(J, " ").strip()
    if len(spaced) == want:
        return spaced, True
    joined = raw.replace(J, "").strip()
    if len(joined) == want:
        return joined, True
    return spaced, False


def parse_entries(cell_text: str) -> list[dict]:
    out, pos = [], 0
    while pos < len(cell_text):
        pos = SPACES.match(cell_text, pos).end()
        if pos >= len(cell_text):
            break
        f = FILLER.match(cell_text, pos)
        if f:
            pos = f.end()
            continue
        m = ENTRY.match(cell_text, pos)
        if not m:
            out.append({"kind": "UNPARSED", "raw": cell_text[pos:].replace(J, " ")})
            break
        kind = (m.group("kind") or "").replace(J, " ").strip()
        s, e = int(m.group("s")), int(m.group("e"))
        value, ok = clean_value(m.group("value"), s, e)
        out.append({
            "kind": ("gold" if kind.startswith("GOLD")
                     else "hard_negative" if kind.startswith("HARD") else "pred"),
            "label": m.group("label"), "value": value, "start": s, "end": e,
            "score": float(m.group("score")) if m.group("score") else None,
            "span_len_ok": ok,
        })
        pos = m.end()
    return out


def reconstruct_text(lines: list[str], entries: list[dict]) -> str | None:
    """The document's original text, rebuilt so the report's character
    offsets line up -- accepted only if EVERY listed span lands exactly on
    its listed value. None if neither join works (PDF wrapping is ambiguous
    for that document)."""
    for joiner in (" ", "\n"):
        t = joiner.join(lines)
        if all(e["kind"] == "UNPARSED" or t[e["start"]:e["end"]] == e["value"]
               for e in entries):
            return t
    return None


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(PDF)

    page_index = []
    records: list[dict] = []
    current_section = None
    table_files = 0

    for pno in range(doc.page_count):
        page = doc[pno]
        pdf_page = pno + 1
        text = page.get_text("text")
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        headings = [ln for ln in lines if HEADING.match(ln)]
        if pdf_page == 1:
            headings = [lines[2]] if len(lines) > 2 else headings
        if headings:
            current_section = headings[0]

        tabs = page.find_tables().tables
        table_meta = []
        for ti, t in enumerate(tabs, start=1):
            rows = table_rows(page, t)
            path = TABLES / f"p{pdf_page:03d}_t{ti}.csv"
            with path.open("w", encoding="utf-8", newline="") as fh:
                w = csv.writer(fh)
                for r in rows:
                    w.writerow([" ".join(c) for c in r])
            table_files += 1
            table_meta.append({
                "file": f"tables/{path.name}", "rows": t.row_count,
                "cols": t.col_count,
                "header": [" ".join(c) for c in rows[0]] if rows else [],
            })

            if pdf_page >= APPENDIX_FIRST_PAGE:
                for r in rows:
                    first = " ".join(r[0]) if r else ""
                    if first == "Data ID":
                        continue
                    if re.fullmatch(r"bench_[a-z]{2}_\d{6}", first):
                        records.append({
                            "data_id": first, "page_start": pdf_page,
                            "page_end": pdf_page, "cells": [list(c) for c in r[1:]],
                        })
                    elif records and not first:
                        prev = records[-1]           # row continued from the previous page
                        prev["page_end"] = pdf_page
                        for i, c in enumerate(r[1:]):
                            prev["cells"][i].extend(c)
                    else:
                        print(f"WARN p{pdf_page}: unrecognised row start {first!r}")

        kind = ("title_and_summary" if pdf_page == 1
                else "methodology" if pdf_page == 2
                else "appendix_error_documents" if pdf_page >= APPENDIX_FIRST_PAGE
                else "results_and_breakdowns")
        page_index.append({
            "page": pdf_page, "section": current_section,
            "headings_on_page": headings, "kind": kind,
            "chars": len(text), "tables": table_meta,
        })

    parsed = []
    for rec in records:
        err_cell, gold_cell, model_cell, text_cell = (rec["cells"] + [[]] * 4)[:4]
        error_types = [t.strip() for t in " ".join(err_cell).split(";") if t.strip()]
        entries = parse_entries(J.join(gold_cell)) + parse_entries(J.join(model_cell))
        text = reconstruct_text(text_cell, entries)
        parsed.append({
            "data_id": rec["data_id"], "page_start": rec["page_start"],
            "page_end": rec["page_end"], "error_types": error_types,
            "entries": entries, "text": text,
            # raw cell lines only where the exact rebuild failed
            "text_lines": None if text is not None else list(text_cell),
        })

    (OUT / "page_index.json").write_text(
        json.dumps(page_index, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "records.json").write_text(
        json.dumps(parsed, ensure_ascii=False), encoding="utf-8")
    print(f"pages: {doc.page_count}  table files: {table_files}  "
          f"appendix documents: {len(parsed)}")
    unparsed = sum(1 for r in parsed for e in r["entries"] if e["kind"] == "UNPARSED")
    bad_len = sum(1 for r in parsed for e in r["entries"]
                  if e["kind"] != "UNPARSED" and not e["span_len_ok"])
    print(f"unparsed cell fragments: {unparsed}  values whose length != span: {bad_len}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
