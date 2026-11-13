"""Builds the brief's section-28 summary matrices from the experiment JSON.

Only cells that were actually measured are populated. Anything not measured
is printed as '--' rather than estimated.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness  # noqa: E402

R = harness.RESULTS


def load(name):
    p = R / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def main() -> None:
    e1 = load("exp1_cross_format.json")
    e2 = load("exp2_representation.json")
    e5 = load("exp5_pdf.json")
    e6 = load("exp6_context.json")

    out = []
    w = out.append

    # --- Table A: format x register (recall), raw model on real extracted text
    w("TABLE A -- recall by FORMAT x REGISTER (raw model, real extracted text,")
    w("          all 4 languages pooled, 50 expected entities per document)")
    w("")
    agg = defaultdict(lambda: [0, 0])
    for r in e1:
        a = agg[(r["format"], r["register"])]
        a[0] += r["tp"]; a[1] += r["fn"]
    fmts = ["txt", "csv", "xlsx", "docx", "pptx", "pdf"]
    w(f"{'register':10s} " + " ".join(f"{f:>7s}" for f in fmts))
    w("-" * 62)
    for reg in ["prose", "labeled", "table"]:
        cells = []
        for f in fmts:
            tp, fn = agg[(f, reg)]
            cells.append(f"{tp/(tp+fn):>6.0%} " if (tp + fn) else "    -- ")
        w(f"{reg:10s} " + " ".join(cells))
    w("")

    # --- Table B: representation ablation
    w("TABLE B -- recall by TEXTUAL REPRESENTATION (same content, model only)")
    w("")
    by = defaultdict(lambda: [0, 0])
    langs = ["az", "en", "ru", "tr"]
    for r in e2:
        a = by[(r["kind"], r["lang"])]
        a[0] += r["tp"]; a[1] += r["fn"]
    kinds = []
    for r in e2:
        if r["kind"] not in kinds:
            kinds.append(r["kind"])
    w(f"{'representation':16s} " + " ".join(f"{l:>6s}" for l in langs) + f"{'  MEAN':>9s}")
    w("-" * 56)
    for k in kinds:
        tp = sum(by[(k, l)][0] for l in langs)
        fn = sum(by[(k, l)][1] for l in langs)
        cells = " ".join(f"{by[(k,l)][0]/(by[(k,l)][0]+by[(k,l)][1]):>5.0%} "
                         for l in langs)
        w(f"{k:16s} " + cells + f"{tp/(tp+fn):>8.0%}")
    w("")

    # --- Table C: entity type x context (the mechanism)
    w("TABLE C -- recall by ENTITY TYPE x CONTEXT (all 4 languages pooled)")
    w("")
    lad = e6["context_ladder"]
    w(f"{'entity':26s} {'bare':>7s} {'Label: v':>9s} {'sentence':>9s} {'paragraph':>10s}")
    w("-" * 66)
    order = ["GIVENNAME", "SURNAME", "CITY", "STREET", "BUILDINGNUM",
             "ZIPCODE", "AZ_VOEN", "EMAIL", "TELEPHONENUM", "URL"]
    for k in order:
        d = lad[k]
        w(f"{k:26s} {d['bare']:>6.0%} {d['label_colon']:>8.0%} "
          f"{d['short_sent']:>8.0%} {d['paragraph']:>9.0%}")
    means = {c: sum(lad[k][c] for k in order) / len(order)
             for c in ["bare", "label_colon", "short_sent", "paragraph"]}
    w("-" * 66)
    w(f"{'MEAN':26s} {means['bare']:>6.0%} {means['label_colon']:>8.0%} "
      f"{means['short_sent']:>8.0%} {means['paragraph']:>9.0%}")
    w("")

    # --- Table D: language x register
    w("TABLE D -- recall by LANGUAGE x REGISTER (raw model; formats pooled,")
    w("          which is valid because Table A shows format has no effect)")
    w("")
    agg2 = defaultdict(lambda: [0, 0])
    for r in e1:
        a = agg2[(r["lang"], r["register"])]
        a[0] += r["tp"]; a[1] += r["fn"]
    w(f"{'lang':6s} " + " ".join(f"{x:>9s}" for x in ["prose", "labeled", "table"])
      + f"{'  ALL':>9s}")
    w("-" * 46)
    for l in langs:
        cells, ttp, tfn = [], 0, 0
        for reg in ["prose", "labeled", "table"]:
            tp, fn = agg2[(l, reg)]
            ttp += tp; tfn += fn
            cells.append(f"{tp/(tp+fn):>8.0%} ")
        w(f"{l:6s} " + " ".join(cells) + f"{ttp/(ttp+tfn):>8.0%}")
    w("")

    # --- Table E: PDF layouts
    w("TABLE E -- PDF layout: extraction survival vs. detection")
    w("")
    w(f"{'layout':18s} {'values survived':>16s} {'order kept':>11s} {'detect recall':>14s}")
    w("-" * 64)
    kinds5 = []
    for r in e5:
        if r["kind"] not in kinds5:
            kinds5.append(r["kind"])
    for k in kinds5:
        rs = [r for r in e5 if r["kind"] == k and r["mode"] == "default"]
        surv = sum(r["survived"] for r in rs) / sum(r["expected"] for r in rs)
        ordk = sum(1 for r in rs if r["order_ok"])
        rec = sum(r["recall"] for r in rs) / len(rs)
        w(f"{k:18s} {surv:>15.0%} {ordk}/{len(rs):<9} {rec:>13.0%}")
    w("")

    text = "\n".join(out)
    (R / "tables.txt").write_text(text, encoding="utf-8")
    print(text)
    print(f"\nwrote {R/'tables.txt'}")


if __name__ == "__main__":
    main()
