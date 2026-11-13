"""Build results.json, errors.csv, error_analysis.json and sanity_checks.json
from what benchmarks/extract_report.py wrote to benchmarks/extracted/.

Every number carries the PDF page it came from. Every derived number is
recomputed here rather than copied, and each check records the report's
figure, our recomputation, and whether they agree.

Run after extract_report.py:  python benchmarks/analyze_report.py
"""
from __future__ import annotations

import csv
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pymupdf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
PDF = HERE / "masking_multilingual_benchmark_5000_detailed_report.pdf"
OUT = HERE / "extracted"
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "scripts"))

GLOSSARY = [
    ("Tam miss", "full miss: gold entity with no overlapping prediction"),
    ("Span/boundary", "right label, span off (narrower/wider than gold)"),
    ("Yanlış label", "wrong label on (roughly) the right span"),
    ("Label + span", "wrong label and wrong span together"),
    ("Spurious mask", "prediction where no entity is expected"),
    ("Hard-negative trigger", "model masked a planted look-alike that must not be masked"),
    ("HARD-NEGATIVE (maskalanmamalıdır)", "hard negative (must not be masked)"),
    ("Heç nə tapılmayıb", "nothing was found (no prediction)"),
    ("Bu mövqedə entity gözlənilmir", "no entity is expected at this position"),
    ("Səhv növü", "error type"),
    ("Gold / hard-negative gözləntisi", "gold / hard-negative expectation"),
    ("Model cavabı", "model response"),
    ("Tam mətn", "full text"),
    ("Qərar xülasəsi", "decision summary"),
    ("Metodologiya və etibarlılıq", "methodology and reliability"),
    ("Kəsim", "slice / cut"),
    ("Say", "count"), ("Pay", "share"), ("Dəyər", "value"), ("Şərh", "comment"),
    ("İstiqamət", "direction (FP/FN)"), ("Növ", "type"),
    ("Narrower / Wider / Shifted", "predicted span shorter / longer / displaced vs gold"),
    ("Əsas FP səbəbi", "main FP cause"), ("Əsas FN səbəbi", "main FN cause"),
    ("Prioritet", "priority"), ("Diaqnoz", "diagnosis"),
    ("Mövqe", "position in text"),
    ("Təklif edilən gate", "proposed release gate"), ("Cari", "current"),
    ("Yekun qərar", "final decision"),
    ("bütün səhv sənədlər", "all erroneous documents (appendix running header)"),
    ("Əlavə A", "Appendix A"),
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def table(page: int, t: int) -> list[list[str]]:
    with (OUT / "tables" / f"p{page:03d}_t{t}.csv").open(encoding="utf-8") as fh:
        return list(csv.reader(fh))


def num(s: str):
    s = s.strip()
    if re.fullmatch(r"-?\d+(?:\.\d+)?%", s):
        return float(s[:-1])
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d+\.\d+", s):
        return float(s)
    return s


def rows_as_dicts(page: int, t: int, keymap=None) -> list[dict]:
    rows = table(page, t)
    hdr = rows[0]
    out = []
    for r in rows[1:]:
        d = {(keymap or {}).get(h, h): num(v) for h, v in zip(hdr, r)}
        d["pdf_page"] = page
        out.append(d)
    return out


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return 100 * p, 100 * r, 100 * f


def r1(x):
    return round(x + 1e-9, 1)


CHECKS: list[dict] = []


def check(name, pages, reported, computed, ok=None, note=""):
    if ok is None:
        ok = reported == computed
    CHECKS.append({"check": name, "pdf_pages": pages, "reported": reported,
                   "computed": computed, "pass": bool(ok), "note": note})


# Checks that fail as literal equalities for a known, verified reason. They
# stay recorded as failing -- `explained` says why, it does not flip `pass`.
EXPLANATIONS = {
    "by_noise: docs sum to 5000": "Noise slices overlap: a document can carry orthographic AND typo noise (5525 slice-docs over 5000 docs). Not additive by design.",
    "by_noise: TP sums to global": "Overlapping slices, see docs check.",
    "by_noise: FP sums to global": "Overlapping slices, see docs check.",
    "by_noise: FN sums to global": "Overlapping slices, see docs check.",
    "confidence-bin FP counts = appendix score histogram": "Appendix prints scores to 3 decimals, so values near a bin edge (e.g. 0.8996 printed 0.900) fall in the next bin. Totals agree (4482).",
    "p7 'Triggered' = appendix hard negatives touched by a same-label prediction": "Same-label overlap reproduces p7 exactly for 25/27 labels. CARD_SECURITY_CODE is 70 short (478 vs 548) and ZIPCODE 1 short. Unresolved; see SUMMARY 'needs a human'.",
}


def close(a, b):
    """Two 1-decimal percentages that differ only by a .x5 rounding tie."""
    return abs(a - b) <= 0.051


def page_lines(doc, page):
    return [ln.strip() for ln in doc[page - 1].get_text().split("\n") if ln.strip()]


def pairs_after(lines, start_marker, stop_markers, n=None):
    """Chart-style 'LABEL\\nVALUE%' pairs following a marker line."""
    try:
        i = lines.index(start_marker) + 1
    except ValueError:
        return []
    out = []
    while i + 1 < len(lines) and lines[i] not in stop_markers:
        k, v = lines[i], lines[i + 1]
        if not v.endswith("%"):
            break
        out.append({"item": k, "value_pct": num(v)})
        i += 2
        if n and len(out) >= n:
            break
    return out


def narrative(doc, page):
    """Text blocks on a page that are outside every table (the report's prose)."""
    pg = doc[page - 1]
    boxes = [pymupdf.Rect(t.bbox) for t in pg.find_tables().tables]
    out = []
    for b in pg.get_text("blocks"):
        r = pymupdf.Rect(b[:4])
        txt = " ".join(b[4].split())
        if not txt or txt.startswith("masking-multilingual |") or re.fullmatch(r"Səhifə \d+", txt):
            continue
        if any(r.intersects(bx) for bx in boxes):
            continue
        out.append(txt)
    return out


# ---------------------------------------------------------------------------
# results.json
# ---------------------------------------------------------------------------

def build_results(doc) -> dict:
    res: dict = {"source": {
        "pdf": "benchmarks/masking_multilingual_benchmark_5000_detailed_report.pdf",
        "pages": doc.page_count, "pdf_metadata": doc.metadata,
        "model": "your-hf-org/masking-multilingual (checkpoint 1)",
        "extraction_tool": "PyMuPDF find_tables + clipped get_text",
        "note": "Numbers below are the report's own. Recomputations and "
                "disagreements live in sanity_checks.json.",
    }}
    res["glossary"] = [{"term": a, "english": b} for a, b in GLOSSARY]

    p1 = table(1, 1)
    res["global"] = {
        "pdf_page": 1,
        "model": p1[1][0], "documents": num(p1[1][1]), "gold": num(p1[1][2]),
        "predictions": num(p1[1][3]), "matching": p1[1][4],
        "kpis_page1_chart": pairs_after(page_lines(doc, 1), "PII Masking Modeli", {"Model"})
        or None,
    }
    l1 = page_lines(doc, 1)
    kp = {}
    for i, ln in enumerate(l1):
        if ln in ("Micro F1", "Precision", "Recall", "Macro F1") and i > 0 and l1[i - 1].endswith("%"):
            kp[ln] = num(l1[i - 1])
    res["global"]["kpis"] = kp
    res["global"]["page3_metrics"] = rows_as_dicts(3, 1, {"Metric": "metric", "Dəyər": "value", "Şərh": "comment"})
    res["decision_summary"] = rows_as_dicts(1, 2, {"Sahə": "area", "Qiymət": "rating", "Qısa nəticə": "short_conclusion"})
    res["methodology"] = rows_as_dicts(2, 1, {"Yoxlama": "check", "Nəticə": "result"})
    res["error_architecture"] = rows_as_dicts(3, 2, {"İstiqamət": "direction", "Növ": "type", "Say": "count", "Pay": "share_pct"})
    res["per_label"] = rows_as_dicts(4, 1, {"Label": "label", "Precision": "precision_pct", "Recall": "recall_pct", "F1": "f1_pct"})
    l5 = page_lines(doc, 5)
    res["weakest_12_f1_chart"] = [dict(d, pdf_page=5) for d in pairs_after(l5, "Ən zəif 12 label - F1", {"Ən güclü 10 label - F1"})]
    res["strongest_10_f1_chart"] = [dict(d, pdf_page=5) for d in pairs_after(l5, "Ən güclü 10 label - F1", {"Prioritet diaqnoz"})]
    res["priority_diagnosis"] = rows_as_dicts(5, 1, {"Prioritet": "priority", "Label": "label", "Diaqnoz": "diagnosis"})
    res["confusion_pairs"] = rows_as_dicts(6, 1, {"Gold": "gold", "Prediction": "predicted", "Say": "count", "Nəticə": "scoring_effect"})
    res["main_confusions"] = rows_as_dicts(6, 2, {"Cüt": "pair", "Say": "count", "Şərh": "comment"})
    res["example_tables"] = {
        "wrong_label_examples": "tables/p006_t3.csv (page 6)",
        "hard_negative_trigger_examples": "tables/p009_t1.csv (page 9)",
        "spurious_examples": "tables/p009_t2.csv (page 9)",
        "full_miss_examples": "tables/p010_t1.csv (page 10)",
        "boundary_examples": "tables/p011_t2.csv (page 11)",
    }
    res["hard_negative_by_target_label"] = rows_as_dicts(7, 1, {"Target label": "label", "Cases": "cases", "Triggered": "triggered", "Rate": "rate_pct"})
    res["hard_negative_by_value"] = {
        "pdf_page": 8,
        "note": "The page lists 35 rows, all AZ_FIN at 100% trigger: a top-by-rate cut, not the full value table.",
        "rows": rows_as_dicts(8, 1, {"Label": "label", "Dəyər": "value", "Cases": "cases", "Triggered": "triggered", "Rate": "rate_pct"}),
    }
    l9 = page_lines(doc, 9)
    res["fp_taxonomy_chart"] = [dict(d, pdf_page=9) for d in pairs_after(l9, "FP taxonomy payı", {"Hard-negative trigger nümunələri"})]
    l10 = page_lines(doc, 10)
    res["fn_taxonomy_chart"] = [dict(d, pdf_page=10) for d in pairs_after(l10, "FN taxonomy payı", {"Tam miss sayı - maksimuma normallaşdırılıb"})]
    res["full_miss_normalized_chart"] = [dict(d, pdf_page=10) for d in pairs_after(l10, "Tam miss sayı - maksimuma normallaşdırılıb", {"Reprezentativ tam miss nümunələri"})]
    res["boundary_types"] = rows_as_dicts(11, 1, {"Boundary növü": "type", "Say": "count", "Pay": "share_pct"})
    slice_map = {"Kəsim": "slice", "Docs": "docs", "Precision": "precision_pct", "Recall": "recall_pct", "F1": "f1_pct"}
    res["by_source"] = rows_as_dicts(12, 1, slice_map)
    res["by_category"] = rows_as_dicts(12, 2, slice_map)
    res["by_document_type"] = rows_as_dicts(13, 1, slice_map)
    res["weak_labels_within_format"] = rows_as_dicts(14, 1, {"Format": "format", "Ən zəif label-lər (support >= 5)": "weakest_labels_support_ge_5"})
    res["by_noise"] = rows_as_dicts(15, 1, slice_map)
    res["by_register"] = rows_as_dicts(15, 2, slice_map)
    res["by_first_person"] = rows_as_dicts(15, 3, slice_map)
    res["by_length"] = rows_as_dicts(16, 1, slice_map)
    res["by_entity_density"] = rows_as_dicts(16, 2, slice_map)
    res["by_position"] = rows_as_dicts(16, 3, {"Mövqe": "position", "Recall": "recall_pct"})
    res["threshold_simulation"] = rows_as_dicts(17, 1, {"Threshold": "threshold", "Precision": "precision_pct", "Recall": "recall_pct", "F1": "f1_pct"})
    res["confidence_bins"] = rows_as_dicts(17, 2, {"Score": "score_bin", "Bin precision": "bin_precision_pct"})
    res["label_error_causes"] = rows_as_dicts(18, 1, {"Label": "label", "Əsas FP səbəbi": "main_fp_cause", "Əsas FN səbəbi": "main_fn_cause"})
    res["edge_case_map"] = rows_as_dicts(19, 1, {"Edge case": "edge_case", "Müşahidə": "observation", "Risk": "risk"})
    res["recommended_fixes"] = rows_as_dicts(20, 1, {"Prioritet": "priority", "Dəyişiklik": "change", "Gözlənilən təsir": "expected_impact"})
    res["release_gate"] = rows_as_dicts(21, 1, {"Metric": "metric", "Cari": "current", "Təklif edilən gate": "proposed_gate"})
    res["artifacts_listed"] = rows_as_dicts(21, 2, {"Fayl": "file", "Məzmun": "content"})
    res["per_language"] = {
        "note": "No per-language breakdown exists: every document ID in the report is bench_az_*, "
                "so this is an Azerbaijani-only benchmark (checked across all 3464 appendix documents)."}
    res["narrative_by_page"] = {str(p): narrative(doc, p) for p in range(1, 22)}
    return res


# ---------------------------------------------------------------------------
# appendix error classification
# ---------------------------------------------------------------------------

def overlap(a0, a1, b0, b1):
    return a0 < b1 and b0 < a1


def classify(recs):
    """Recreate the report's FP/FN taxonomy from Appendix A entries."""
    fn_rows, fp_rows, hn_rows = [], [], []
    for r in recs:
        golds = [e for e in r["entries"] if e["kind"] == "gold"]
        hns = [e for e in r["entries"] if e["kind"] == "hard_negative"]
        preds = [e for e in r["entries"] if e["kind"] == "pred"]
        for g in golds:
            ov = [p for p in preds if overlap(g["start"], g["end"], p["start"], p["end"])]
            same_span = [p for p in ov if (p["start"], p["end"]) == (g["start"], g["end"])]
            if not ov:
                cls = "missed"
            elif same_span and all(p["label"] != g["label"] for p in same_span):
                cls = "wrong_label"
            elif any(p["label"] == g["label"] for p in ov):
                cls = "boundary_error"
            else:
                cls = "wrong_label_and_boundary"
            fn_rows.append((r, g, ov, cls))
        for p in preds:
            og = [g for g in golds if overlap(g["start"], g["end"], p["start"], p["end"])]
            oh = [h for h in hns if overlap(h["start"], h["end"], p["start"], p["end"])]
            if og:
                # A prediction spanning two golds is judged against the one
                # with its own label when there is one (bench_az_004146:
                # one STREET prediction covering a CITY and a STREET gold).
                g = next((x for x in og if x["label"] == p["label"]), og[0])
                if (p["start"], p["end"]) == (g["start"], g["end"]):
                    cls = "wrong_label"
                elif p["label"] == g["label"]:
                    cls = "boundary_error"
                else:
                    cls = "wrong_label_and_boundary"
                ref = og
            elif oh:
                cls = ("hard_negative_trigger" if any(h["label"] == p["label"] for h in oh)
                       else "hard_negative_other_label")
                ref = oh
            else:
                cls, ref = "spurious", []
            fp_rows.append((r, p, ref, cls))
        for h in hns:
            ov = [p for p in preds if overlap(h["start"], h["end"], p["start"], p["end"])]
            hn_rows.append((r, h, ov, "same_label" if any(p["label"] == h["label"] for p in ov)
                            else "other_label" if ov else "untouched"))
    return fn_rows, fp_rows, hn_rows


def snippet(r, e, w=30):
    t = r["text"]
    if t is None:
        return ""
    return " ".join(t[max(0, e["start"] - w):e["end"] + w].split())


def write_errors_csv(fn_rows, fp_rows, hn_rows):
    cols = ["data_id", "row_kind", "error_type_doc", "error_class", "label",
            "gold_span", "value", "predicted_label", "predicted_span", "score",
            "text_snippet", "pdf_page", "pdf_page_end"]
    n = 0
    with (OUT / "errors.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r, g, ov, cls in fn_rows:
            w.writerow([r["data_id"], "gold_not_matched", "; ".join(r["error_types"]), cls,
                        g["label"], f"{g['start']}:{g['end']}", g["value"],
                        "|".join(p["label"] for p in ov),
                        "|".join(f"{p['start']}:{p['end']}" for p in ov),
                        "|".join(f"{p['score']:.3f}" for p in ov),
                        snippet(r, g), r["page_start"], r["page_end"]]); n += 1
        for r, p, ref, cls in fp_rows:
            w.writerow([r["data_id"], "prediction_not_matched", "; ".join(r["error_types"]), cls,
                        "|".join(x["label"] for x in ref),
                        "|".join(f"{x['start']}:{x['end']}" for x in ref),
                        p["value"], p["label"], f"{p['start']}:{p['end']}",
                        f"{p['score']:.3f}", snippet(r, p), r["page_start"], r["page_end"]]); n += 1
        for r, h, ov, cls in hn_rows:
            w.writerow([r["data_id"], "hard_negative_touched", "; ".join(r["error_types"]), cls,
                        h["label"], f"{h['start']}:{h['end']}", h["value"],
                        "|".join(p["label"] for p in ov),
                        "|".join(f"{p['start']}:{p['end']}" for p in ov),
                        "|".join(f"{p['score']:.3f}" for p in ov),
                        snippet(r, h), r["page_start"], r["page_end"]]); n += 1
    return n


AZ_SUFFIX = re.compile(r"(?:da|də|dan|dən|ın|in|un|ün|nın|nin|a|ə|ya|yə|dır|dir|dur|dür|la|lə|lı|li|lu|lü|ı|i|u|ü|nı|ni)\b", re.I)


def mid_word(text, s, e):
    """Span starts or ends inside a word (the subword-fragmentation signature).
    A trailing Azerbaijani suffix is ordinary grammar, not fragmentation."""
    starts_inside = s > 0 and text[s - 1].isalnum() and text[s].isalnum()
    ends_inside = (e < len(text) and text[e].isalnum() and text[e - 1].isalnum()
                   and not AZ_SUFFIX.match(text, e))
    return starts_inside or ends_inside


def doc_format(t):
    if t is None:
        return "unknown"
    s = t.lstrip()
    if s.startswith("{"):
        return "json"
    if re.search(r"^\[\d{4}-\d{2}-\d{2} ", t, re.M):
        return "log"
    if t.count("|") >= 6:
        return "pipe_table"
    if re.match(r"[a-zəöüğıçş_]+(;[a-zəöüğıçş_]+){2,}", s):
        return "csv"
    if re.search(r"^(Operator|Müştəri|Agent):", t, re.M):
        return "dialogue"
    return "prose"


def error_analysis(recs, fn_rows, fp_rows, hn_rows):
    a: dict = {}
    a["documents"] = len(recs)
    a["doc_error_types"] = Counter(t for r in recs for t in r["error_types"]).most_common()
    a["fn_class_by_label"] = {}
    for r, g, ov, cls in fn_rows:
        a["fn_class_by_label"].setdefault(g["label"], Counter())[cls] += 1
    a["fp_class_by_label"] = {}
    for r, p, ref, cls in fp_rows:
        a["fp_class_by_label"].setdefault(p["label"], Counter())[cls] += 1
    a["fn_by_label"] = Counter(g["label"] for _, g, _, _ in fn_rows).most_common()
    a["fp_by_predicted_label"] = Counter(p["label"] for _, p, _, _ in fp_rows).most_common()
    a["fn_classes"] = Counter(c for *_, c in fn_rows).most_common()
    a["fp_classes"] = Counter(c for *_, c in fp_rows).most_common()
    a["confusion_exact_span"] = Counter(
        f"{g['label']} -> {ov[0]['label']}" for _, g, ov, c in fn_rows if c == "wrong_label").most_common()
    a["confusion_including_boundary"] = Counter(
        f"{ref[0]['label']} -> {p['label']}" for _, p, ref, c in fp_rows
        if c in ("wrong_label", "wrong_label_and_boundary")).most_common()

    scores = defaultdict(list)
    for _, p, _, cls in fp_rows:
        scores[cls].append(p["score"])
    a["fp_score_by_class"] = {
        k: {"n": len(v), "mean": round(statistics.mean(v), 3), "median": round(statistics.median(v), 3),
            "share_below_0.8": round(sum(1 for x in v if x < 0.8) / len(v), 3)}
        for k, v in scores.items()}
    bins = [(0, .5), (.5, .8), (.8, .9), (.9, .95), (.95, .99), (.99, 1.0001)]
    a["fp_score_histogram"] = {f"{lo:.2f}-{min(hi,1):.2f}": sum(1 for _, p, _, _ in fp_rows if lo <= p["score"] < hi)
                               for lo, hi in bins}
    a["hard_negative_lines"] = Counter(c for *_, c in hn_rows).most_common()
    a["hard_negative_same_label_by_target"] = Counter(
        h["label"] for _, h, _, c in hn_rows if c == "same_label").most_common()

    frag = Counter()
    for r, p, _, cls in fp_rows:
        if r["text"] is None or cls not in ("boundary_error", "wrong_label_and_boundary", "spurious"):
            continue
        frag[(cls, mid_word(r["text"], p["start"], p["end"]))] += 1
    a["mid_word_spans_among_fp"] = {f"{c}|{'mid_word' if m else 'word_aligned'}": n for (c, m), n in frag.items()}

    fmt = {r["data_id"]: doc_format(r["text"]) for r in recs}
    a["error_docs_by_detected_format"] = Counter(fmt.values()).most_common()
    a["missed_gold_by_format"] = Counter(fmt[r["data_id"]] for r, g, ov, c in fn_rows if c == "missed").most_common()
    a["missed_gold_by_format_and_label"] = Counter(
        f"{fmt[r['data_id']]}:{g['label']}" for r, g, ov, c in fn_rows if c == "missed").most_common(25)

    inv = re.compile("[​‌‍⁠﻿­]")
    a["docs_containing_invisible_chars_in_extracted_text"] = sum(
        1 for r in recs if inv.search(r["text"] or " ".join(r["text_lines"] or [])))
    a["distinct_fp_values"] = len({(p["label"], p["value"]) for _, p, _, _ in fp_rows})
    top = Counter((p["label"], p["value"]) for _, p, _, _ in fp_rows).most_common(20)
    a["top20_fp_values_share"] = round(sum(n for _, n in top) / len(fp_rows), 4)
    a["top20_fp_values"] = [{"label": l, "value": v, "count": n} for (l, v), n in top]

    def jsonable(o):
        if isinstance(o, Counter):
            return dict(o.most_common())
        if isinstance(o, dict):
            return {k: jsonable(v) for k, v in o.items()}
        return o
    return jsonable(a)


# ---------------------------------------------------------------------------
# sanity checks
# ---------------------------------------------------------------------------

def sanity(res, recs, fn_rows, fp_rows, hn_rows, analysis):
    g = res["global"]
    m = {d["metric"]: d["value"] for d in res["global"]["page3_metrics"]}
    TP, FP, FN = m["TP"], m["FP"], m["FN"]
    check("TP + FP = predictions", [1, 3], g["predictions"], TP + FP)
    check("TP + FN = gold", [1, 3], g["gold"], TP + FN)
    check("FN = gold - TP", [1, 3], FN, g["gold"] - TP)
    p, r, f = prf(TP, FP, FN)
    check("micro precision", [1, 3], g["kpis"].get("Precision"), r1(p))
    check("micro recall", [1, 3], g["kpis"].get("Recall"), r1(r))
    check("micro F1", [1, 3], g["kpis"].get("Micro F1"), r1(f))

    pl = res["per_label"]
    check("per-label rows = 27", [4], 27, len(pl))
    check("per-label TP sums to global", [3, 4], TP, sum(x["TP"] for x in pl))
    check("per-label FP sums to global", [3, 4], FP, sum(x["FP"] for x in pl))
    check("per-label FN sums to global", [3, 4], FN, sum(x["FN"] for x in pl))
    check("per-label support sums to gold", [1, 4], g["gold"], sum(x["Support"] for x in pl))
    bad = [x["label"] for x in pl if x["Support"] != x["TP"] + x["FN"]]
    check("support = TP + FN for every label", [4], [], bad)
    mism = []
    for x in pl:
        pp, rr, ff = prf(x["TP"], x["FP"], x["FN"])
        if (r1(pp), r1(rr), r1(ff)) != (x["precision_pct"], x["recall_pct"], x["f1_pct"]):
            mism.append({"label": x["label"], "reported": [x["precision_pct"], x["recall_pct"], x["f1_pct"]],
                         "computed": [r1(pp), r1(rr), r1(ff)]})
    check("per-label P/R/F1 recompute", [4], [], mism)
    macro = statistics.mean(prf(x["TP"], x["FP"], x["FN"])[2] for x in pl)
    check("macro F1 = mean of per-label F1", [1, 4], g["kpis"].get("Macro F1"), r1(macro))
    wf = sum(prf(x["TP"], x["FP"], x["FN"])[2] * x["Support"] for x in pl) / sum(x["Support"] for x in pl)
    check("weighted F1 = support-weighted F1", [3, 4], m.get("Weighted F1"), r1(wf))

    ea = res["error_architecture"]
    fps = {d["type"]: d["count"] for d in ea if d["direction"] == "FP"}
    fns = {d["type"]: d["count"] for d in ea if d["direction"] == "FN"}
    check("FP error types sum to FP", [3], FP, sum(fps.values()))
    check("FN error types sum to FN", [3], FN, sum(fns.values()))
    check("FP 'wrong_label' = FN 'wrong_label' (same entity counted twice)", [3],
          fps.get("wrong_label"), fns.get("wrong_label"))

    check("perfect docs + appendix docs = 5000", [3, 22], g["documents"],
          m.get("Perfect documents") + len(recs) if isinstance(m.get("Perfect documents"), int) else None,
          ok=(1536 + len(recs) == g["documents"]), note="Perfect documents = 1536 (p3)")
    docs_fp = sum(1 for r in recs if any(e["kind"] == "pred" for e in r["entries"]))
    docs_fn = sum(1 for r in recs if any(e["kind"] == "gold" for e in r["entries"]))
    check("documents with >=1 FP (appendix recount)", [3, 22], 2649, docs_fp)
    check("documents with >=1 FN (appendix recount)", [3, 22], 2054, docs_fn)
    check("appendix gold rows = FN", [3, 22], FN, len(fn_rows))
    check("appendix prediction rows = FP", [3, 22], FP, len(fp_rows))
    check("error_cases.csv size stated on p21 = FP + FN", [21], 7159, FP + FN)

    ours_fp = dict(analysis["fp_classes"])
    ours_fn = dict(analysis["fn_classes"])
    for k in ("missed", "wrong_label", "boundary_error", "wrong_label_and_boundary"):
        check(f"FN '{k}' recomputed from appendix", [3, 22], fns.get(k), ours_fn.get(k, 0))
    for k in ("wrong_label", "boundary_error", "wrong_label_and_boundary"):
        check(f"FP '{k}' recomputed from appendix", [3, 22], fps.get(k), ours_fp.get(k, 0))
    check("FP 'hard_negative_trigger' recomputed (same label as the planted target)", [3, 22],
          fps.get("hard_negative_trigger"), ours_fp.get("hard_negative_trigger", 0))
    check("FP 'spurious' recomputed (no gold, no same-label hard negative)", [3, 22],
          fps.get("spurious"), ours_fp.get("spurious", 0) + ours_fp.get("hard_negative_other_label", 0))

    fn_lab = dict(analysis["fn_by_label"])
    fp_lab = dict(analysis["fp_by_predicted_label"])
    diff = [{"label": x["label"], "FN_p4": x["FN"], "FN_appendix": fn_lab.get(x["label"], 0),
             "FP_p4": x["FP"], "FP_appendix": fp_lab.get(x["label"], 0)}
            for x in pl if x["FN"] != fn_lab.get(x["label"], 0) or x["FP"] != fp_lab.get(x["label"], 0)]
    check("per-label FP/FN on p4 = appendix recount", [4, 22], [], diff)

    hn = res["hard_negative_by_target_label"]
    cases, trig = sum(x["cases"] for x in hn), sum(x["triggered"] for x in hn)
    gate = {d["metric"]: d["current"] for d in res["release_gate"]}
    check("hard-negative overall trigger rate = sum(triggered)/sum(cases)", [7, 21],
          gate.get("Hard-negative trigger"), r1(100 * trig / cases), note=f"{trig}/{cases}")
    rate_bad = [x["label"] for x in hn if r1(100 * x["triggered"] / x["cases"]) != x["rate_pct"]]
    check("hard-negative per-label rate recompute", [7], [], rate_bad)
    same = dict(analysis["hard_negative_same_label_by_target"])
    hdiff = [{"label": x["label"], "triggered_p7": x["triggered"], "same_label_touched_appendix": same.get(x["label"], 0)}
             for x in hn if x["triggered"] != same.get(x["label"], 0)]
    check("p7 'Triggered' = appendix hard negatives touched by a same-label prediction", [7, 22], [], hdiff,
          note="appendix side counts planted hard-negative values that a same-label prediction overlaps")

    bt = {d["type"]: d["count"] for d in res["boundary_types"]}
    check("boundary types sum to FP boundary_error", [3, 11], fps.get("boundary_error"), sum(bt.values()))

    def slice_checks(key, pages, expect_docs=True):
        rows = res[key]
        if expect_docs:
            check(f"{key}: docs sum to 5000", pages, 5000, sum(x["docs"] for x in rows),
                  ok=sum(x["docs"] for x in rows) == 5000)
        for col, tot in (("TP", TP), ("FP", FP), ("FN", FN)):
            s = sum(x[col] for x in rows)
            check(f"{key}: {col} sums to global", pages, tot, s)
        bad, ties = [], []
        for x in rows:
            pp, rr, ff = prf(x["TP"], x["FP"], x["FN"])
            rep = (x["precision_pct"], x["recall_pct"], x["f1_pct"])
            got = (r1(pp), r1(rr), r1(ff))
            if got != rep:
                entry = {"slice": x["slice"], "reported": list(rep), "computed": list(got),
                         "unrounded": [round(pp, 4), round(rr, 4), round(ff, 4)]}
                (ties if all(abs(u - v) <= 0.0501 for u, v in zip((pp, rr, ff), rep))
                 else bad).append(entry)
        check(f"{key}: P/R/F1 recompute", pages, [], bad,
              note=("rounding tie only, value sits exactly on .x5: "
                    + json.dumps(ties, ensure_ascii=False)) if ties else "")

    for key, pages in (("by_source", [12]), ("by_category", [12]), ("by_document_type", [13]),
                       ("by_noise", [15]), ("by_register", [15]), ("by_first_person", [15]),
                       ("by_length", [16]), ("by_entity_density", [16])):
        slice_checks(key, pages)

    pos = res["by_position"]
    check("by_position TP sums to global", [16], TP, sum(x["TP"] for x in pos))
    check("by_position FN sums to global", [16], FN, sum(x["FN"] for x in pos))

    th = res["threshold_simulation"]
    row0 = [x for x in th if x["threshold"] in (0, 0.0)]
    check("threshold 0.0 row = global", [17], [TP, FP, FN], [row0[0]["TP"], row0[0]["FP"], row0[0]["FN"]] if row0 else None)
    bad = [x["threshold"] for x in th if x["TP"] + x["FN"] != g["gold"]]
    check("every threshold row: TP + FN = gold", [17], [], bad)
    bad = []
    for x in th:
        pp, rr, ff = prf(x["TP"], x["FP"], x["FN"])
        if (r1(pp), r1(rr), r1(ff)) != (x["precision_pct"], x["recall_pct"], x["f1_pct"]):
            bad.append({"threshold": x["threshold"], "computed": [r1(pp), r1(rr), r1(ff)]})
    check("threshold rows: P/R/F1 recompute", [17], [], bad)
    cb = res["confidence_bins"]
    check("confidence bins TP sum = TP", [17], TP, sum(x["TP"] for x in cb))
    check("confidence bins FP sum = FP", [17], FP, sum(x["FP"] for x in cb))
    ours_hist = analysis["fp_score_histogram"]
    check("confidence-bin FP counts = appendix score histogram", [17, 22],
          [x["FP"] for x in cb], list(ours_hist.values()))

    cp = res["confusion_pairs"]
    ours_conf = dict(analysis["confusion_including_boundary"])
    cdiff = [{"pair": f"{x['gold']} -> {x['predicted']}", "p6": x["count"],
              "appendix": ours_conf.get(f"{x['gold']} -> {x['predicted']}", 0)}
             for x in cp if x["count"] != ours_conf.get(f"{x['gold']} -> {x['predicted']}", 0)]
    check("p6 confusion counts = appendix wrong-label pairs (exact span + boundary)", [6, 22], [], cdiff,
          note="p6 counts both FP 'wrong_label' and 'wrong_label_and_boundary'")
    check("p6 confusion counts sum = FP wrong_label + wrong_label_and_boundary", [3, 6],
          fps.get("wrong_label", 0) + fps.get("wrong_label_and_boundary", 0), sum(x["count"] for x in cp))

    fp_mean = statistics.mean(p["score"] for _, p, _, _ in fp_rows)
    check("p17 narrative 'FP score ortalaması 0.856' = mean appendix FP score", [17, 22],
          0.856, round(fp_mean, 3), ok=abs(fp_mean - 0.856) < 0.0006,
          note=f"unrounded {fp_mean:.4f}; TP mean 0.986 is not checkable (Appendix A lists no TPs)")

    # p18 "main cause (count)": the report's 'spurious' folds in predictions on a
    # planted value made under a different label than the planted target.
    fp_cls = analysis["fp_class_by_label"]
    fn_cls = analysis["fn_class_by_label"]
    p18_bad = []
    for x in res["label_error_causes"]:
        for col, ours in (("main_fp_cause", fp_cls.get(x["label"], {})),
                          ("main_fn_cause", fn_cls.get(x["label"], {}))):
            m18 = re.fullmatch(r"(\w+) \((\d+)\)", str(x[col]).strip())
            if not m18:
                continue                       # "- (0)" for no FP
            cause, n18 = m18.group(1), int(m18.group(2))
            got = ours.get(cause, 0)
            if cause == "spurious":
                got += ours.get("hard_negative_other_label", 0)
            if got != n18:
                p18_bad.append({"label": x["label"], "column": col, "p18": x[col], "appendix": got})
    check("p18 main FP/FN cause counts = appendix recount", [18, 22], [], p18_bad)

    try:
        from piigen.config import DETECTION_TIERS
        ours = set(DETECTION_TIERS)
    except Exception as exc:                           # noqa: BLE001
        ours = None
        CHECKS.append({"check": "label taxonomy import", "pass": False, "note": repr(exc)})
    if ours is not None:
        used = {x["label"] for x in pl} | {e["label"] for r in recs for e in r["entries"]}
        check("every label in the report is in piigen.config.DETECTION_TIERS", [4, 22], [],
              sorted(used - ours), note=f"{len(ours)} labels in the repo taxonomy")
        check("every repo label appears in the report", [4], [], sorted(ours - {x['label'] for x in pl}))


NARRATIVE_CLAIMS = [
    # (page, quoted claim, what the claim says, table location, table value)
    (5, "DRIVER_LICENSE ... F1 41.1%", 41.1, "per_label AZ_DRIVER_LICENSE_NUMBER f1 (p4)",
     lambda r: next(x["f1_pct"] for x in r["per_label"] if x["label"] == "AZ_DRIVER_LICENSE_NUMBER")),
    (5, "PAYMENT_CARD_NUMBER Recall 43.1%", 43.1, "per_label PAYMENT_CARD_NUMBER recall (p4)",
     lambda r: next(x["recall_pct"] for x in r["per_label"] if x["label"] == "PAYMENT_CARD_NUMBER")),
    (5, "DATE / GIVENNAME ... F1 54-56%", "54-56", "per_label GIVENNAME f1 (p4)",
     lambda r: next(x["f1_pct"] for x in r["per_label"] if x["label"] == "GIVENNAME")),
    (12, "Hard-negative kateqoriyası precision 37.6%", 37.6, "by_category hard_negative precision (p12)",
     lambda r: next(x["precision_pct"] for x in r["by_category"] if x["slice"] == "hard_negative")),
    (12, "positive-control F1 77.3%", 77.3, "by_category positive_control f1 (p12)",
     lambda r: next(x["f1_pct"] for x in r["by_category"] if x["slice"] == "positive_control")),
    (13, "CSV ən zəif formatdır (F1 55.5%)", 55.5, "by_document_type csv f1 (p13)",
     lambda r: next(x["f1_pct"] for x in r["by_document_type"] if x["slice"] == "csv")),
    (13, "JSON/config ... (F1 71.3%)", 71.3, "by_document_type json_config f1 (p13)",
     lambda r: next(x["f1_pct"] for x in r["by_document_type"] if x["slice"] == "json_config")),
    (15, "First-person mətnlərdə F1 65.5%", 65.5, "by_first_person true f1 (p15)",
     lambda r: next(x["f1_pct"] for x in r["by_first_person"] if str(x["slice"]).lower() == "true")),
    (15, "digər mətnlərdə 66.2%", 66.2, "by_first_person false f1 (p15)",
     lambda r: next(x["f1_pct"] for x in r["by_first_person"] if str(x["slice"]).lower() == "false")),
    (15, "Orthographic noise recall-u clean dataya nisbətən təxminən 5.6 bənd azaldır", 5.6,
     "by_noise clean recall - orthographic_noise recall (p15)",
     lambda r: r1(next(x["recall_pct"] for x in r["by_noise"] if x["slice"] == "clean")
                  - next(x["recall_pct"] for x in r["by_noise"] if x["slice"] == "orthographic_noise"))),
    (17, "Global threshold 0.90 micro F1-i 72.7%-ə qaldırır, lakin recall 71.2%-ə enir", 72.7,
     "threshold_simulation 0.9 f1 (p17)",
     lambda r: next(x["f1_pct"] for x in r["threshold_simulation"] if x["threshold"] == 0.9)),
]


def narrative_checks(res):
    out = []
    for page, claim, stated, where, fn in NARRATIVE_CLAIMS:
        try:
            val = fn(res)
        except StopIteration:
            val = None
        agree = (stated == val) if isinstance(stated, (int, float)) else False
        out.append({"pdf_page": page, "claim_verbatim": claim, "claim_value": stated,
                    "table_location": where, "table_value": val, "agree": agree})
        check(f"narrative vs table: {claim}", [page], stated, val, ok=agree)
    return out


def main() -> int:
    doc = pymupdf.open(PDF)
    recs = json.loads((OUT / "records.json").read_text(encoding="utf-8"))
    res = build_results(doc)
    fn_rows, fp_rows, hn_rows = classify(recs)
    n = write_errors_csv(fn_rows, fp_rows, hn_rows)
    analysis = error_analysis(recs, fn_rows, fp_rows, hn_rows)
    sanity(res, recs, fn_rows, fp_rows, hn_rows, analysis)
    res["narrative_vs_table"] = narrative_checks(res)
    for c in CHECKS:
        if not c["pass"] and c["check"] in EXPLANATIONS:
            c["explained"] = EXPLANATIONS[c["check"]]

    (OUT / "results.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "error_analysis.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "sanity_checks.json").write_text(json.dumps(CHECKS, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"errors.csv rows: {n}")
    passed = sum(c["pass"] for c in CHECKS)
    print(f"sanity checks: {passed}/{len(CHECKS)} pass")
    for c in CHECKS:
        if not c["pass"]:
            tag = "EXPLAINED" if c.get("explained") else "FAIL"
            print(f"  {tag} {c['check']}  pages={c.get('pdf_pages')}  reported={c.get('reported')}  "
                  f"computed={c.get('computed')}  {c.get('note','')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
