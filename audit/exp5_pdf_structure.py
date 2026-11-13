"""EXPERIMENT 5 -- PDF layout variants (brief section 10).

PDF is the only format in the brief with NO extractor anywhere in the
repository, on any branch (scripts/pii_guard/extract/base.py records that one
was built and then removed from scope on 2026-09-14). So there is no product
behaviour to audit here -- only the question of what a PDF does to the text
before any detector can see it, which decides how hard building that
extractor will be.

Eight layouts, each holding the SAME five records, so any difference is
layout and nothing else. For each, three things are measured separately:

  EXTRACTION  -- do the entity values survive verbatim in the extracted text?
                 (a value split by a line break or a lost space is destroyed
                 before any model runs, and must be charged to extraction)
  ORDER       -- does the extracted reading order match the intended order?
                 (the multi-column case exists to break this)
  DETECTION   -- raw model recall on whatever came back

Both pdfplumber modes are run: default (layout-unaware) and layout=True.
"""

from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness  # noqa: E402

harness.setup_paths()

import spec          # noqa: E402
import extract_all   # noqa: E402

from reportlab.lib.pagesizes import A4          # noqa: E402
from reportlab.pdfgen import canvas             # noqa: E402
from reportlab.pdfbase import pdfmetrics        # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont    # noqa: E402

import render  # noqa: E402

FONT = render._register_unicode_font(pdfmetrics, TTFont)


def _lines(lang):
    labels = spec.FIELD_LABELS[lang]
    out = []
    for r in spec.records(lang):
        out.append([f"{labels[k]}: {r[k]}" for k in spec.FIELD_ORDER])
    return out


def build(kind: str, lang: str, path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    W, H = A4
    blocks = _lines(lang)
    c.setFont(FONT, 9)

    if kind == "one_paragraph":
        text = " ".join(spec._PROSE[lang].format(**r) for r in spec.records(lang))
        y = H - 60
        for ln in render._wrap(text, 95):
            c.drawString(50, y, ln); y -= 13

    elif kind == "multi_paragraph":
        y = H - 60
        for r in spec.records(lang):
            for ln in render._wrap(spec._PROSE[lang].format(**r), 95):
                c.drawString(50, y, ln); y -= 13
            y -= 10

    elif kind == "multi_page":
        for i, r in enumerate(spec.records(lang)):
            y = H - 60
            for ln in render._wrap(spec._PROSE[lang].format(**r), 95):
                c.drawString(50, y, ln); y -= 13
            if i < len(blocks) - 1:
                c.showPage(); c.setFont(FONT, 9)

    elif kind == "headings":
        y = H - 60
        for i, blk in enumerate(blocks, 1):
            c.setFont(FONT, 13)
            c.drawString(50, y, f"Record {i}"); y -= 20
            c.setFont(FONT, 9)
            for ln in blk:
                c.drawString(60, y, ln); y -= 13
            y -= 8

    elif kind == "two_column":
        # The reading-order stress case: two independent columns side by
        # side. A layout-unaware extractor reads ACROSS both columns line by
        # line, interleaving them.
        y0 = H - 60
        left, right = blocks[0] + blocks[1], blocks[2] + blocks[3]
        y = y0
        for ln in left:
            c.drawString(40, y, ln); y -= 13
        y = y0
        for ln in right:
            c.drawString(320, y, ln); y -= 13

    elif kind == "header_footer":
        y = H - 40
        c.drawString(50, y, "ACME LLC -- Confidential -- Page 1 of 1")
        y -= 30
        for blk in blocks:
            for ln in blk:
                c.drawString(50, y, ln); y -= 12
            y -= 6
        c.drawString(50, 30, "Printed 2026-09-16 | internal use only")

    elif kind == "narrow_wrap":
        # A narrow text frame, so long values (URL, email) are forced to
        # wrap mid-token. This is the case that actually destroys values.
        y = H - 60
        for blk in blocks:
            for ln in blk:
                for piece in render._wrap(ln, 28):
                    c.drawString(50, y, piece); y -= 11
            y -= 6

    elif kind == "table":
        header = [spec.FIELD_LABELS[lang][k] for k in spec.FIELD_ORDER]
        rows = [[r[k] for k in spec.FIELD_ORDER] for r in spec.records(lang)]
        c.setPageSize((H, W))
        c.setFont(FONT, 5)
        xs, acc = [], 20.0
        for j, h in enumerate(header):
            xs.append(acc)
            acc += max(len(h), max(len(r[j]) for r in rows)) * 5 * 0.62
        y = W - 50
        for j, h in enumerate(header):
            c.drawString(xs[j], y, h)
        y -= 11
        for r in rows:
            for j, v in enumerate(r):
                c.drawString(xs[j], y, v)
            y -= 11
    else:
        raise ValueError(kind)
    c.save()


KINDS = ["one_paragraph", "multi_paragraph", "multi_page", "headings",
         "two_column", "header_footer", "narrow_wrap", "table"]


def nfc(s):
    return unicodedata.normalize("NFC", s)


def main() -> None:
    detect = harness.detect_fn_factory()
    harness.FIXTURES.mkdir(parents=True, exist_ok=True)
    results = []

    for kind in KINDS:
        for lang in spec.LANGS:
            p = harness.FIXTURES / f"pdf5_{kind}_{lang}.pdf"
            build(kind, lang, p)
            expected = spec.expected_entities(lang)
            for mode, fn in [("default", extract_all.extract_pdf),
                             ("layout", extract_all.extract_pdf_layout)]:
                text = fn(p)
                survived = [(l, v) for l, v in expected if nfc(v) in nfc(text)]
                destroyed = [(l, v) for l, v in expected if nfc(v) not in nfc(text)]
                found = [(s["label"], text[s["start"]:s["end"]])
                         for s in detect(text)]
                sc = harness.score_values(found, survived)
                # reading order: are the first record's values all before the
                # last record's values in the extracted text?
                recs = spec.records(lang)
                pos = [nfc(text).find(nfc(r["EMAIL"])) for r in recs]
                order_ok = all(a < b for a, b in zip(pos, pos[1:])
                               if a >= 0 and b >= 0)
                results.append({
                    "kind": kind, "lang": lang, "mode": mode,
                    "survived": len(survived), "expected": len(expected),
                    "destroyed": [list(x) for x in destroyed],
                    "order_ok": order_ok,
                    "recall": sc["recall"], "precision": sc["precision"],
                })

    out = harness.RESULTS / "exp5_pdf.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2),
                   encoding="utf-8")

    print(f"{'layout':17s} {'mode':8s} {'extract_survival':>17s} {'order':>7s} "
          f"{'detect_R':>9s}")
    print("-" * 66)
    for kind in KINDS:
        for mode in ["default", "layout"]:
            rs = [r for r in results if r["kind"] == kind and r["mode"] == mode]
            surv = sum(r["survived"] for r in rs)
            exp = sum(r["expected"] for r in rs)
            ordok = sum(1 for r in rs if r["order_ok"])
            rec = sum(r["recall"] for r in rs) / len(rs)
            print(f"{kind:17s} {mode:8s} {surv/exp:>16.0%} "
                  f"{ordok}/{len(rs):<5} {rec:>8.0%}")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
