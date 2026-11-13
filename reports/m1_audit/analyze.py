"""m1 audit: analyse the per-document predictions written by diag_run.py.

1. Reproduce the saved report numbers from the per-document predictions (scoreboard.score_set).
2. English: every m1 prediction on golden_en that is not an exact gold match, grouped.
3. MAC: per gold MAC on the benchmark, v4.2's and m1's outcome; the patterns of the failures.
4. C13: the name-list control spans per model, and the documents worse than checkpoint 1.
Writes english_review.jsonl, english.md, mac_cases.jsonl, mac.md, c13.md.

  python reports/m1_audit/analyze.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT / "eval"), str(HERE), str(ROOT / "redteam" / "formats_v42")]
import diag_run as D  # noqa: E402
import metrics as M  # noqa: E402
import scoreboard as S  # noqa: E402
from evaluate import score_case  # noqa: E402

PRED = HERE / "preds"
MONTHS = ("January|February|March|April|May|June|July|August|September|October|November|December|"
          "Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec")
DATE_RX = re.compile(rf"^(?:\d{{4}}-\d{{2}}-\d{{2}}|\d{{1,2}}[./-]\d{{1,2}}[./-]\d{{2,4}}|\d{{1,2}}(?:st|nd|rd|th)?\s(?:{MONTHS})\.?(?:,?\s\d{{4}})?|"
                     rf"(?:{MONTHS})\.?\s\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s\d{{4}})?)$", re.I)
STAMP_AFTER = re.compile(r"^[ T,]*\d{1,2}:\d{2}")


def preds(subset: str, mk: str, track: str = "M") -> dict:
    return json.loads((PRED / f"{subset}.{mk}.json").read_text())[track]


def ov(a, b) -> bool:
    return a["start"] < b["end"] and b["start"] < a["end"]


def reproduce(L: list[str]) -> None:
    L += ["## 1. Reproduction from per-document predictions", "",
          "| Subset | Model | Track | Exact P / R / F1 | TP/FP/FN |", "|---|---|---|---|---|"]
    for s, mks in D.PLAN.items():
        docs = D.subset(s)
        for mk in mks:
            for t in ("M", "R"):
                p = preds(s, mk, t)
                rep = S.score_set("probes" if s == "names_list_lines" else s, docs, p)
                m = rep["all"]["exact"]["micro"]
                L.append(f"| {s} | {mk} | {t} | {100*m['precision']:.1f} / {100*m['recall']:.1f} / {100*m['f1']:.1f} | "
                         f"{m['tp']}/{m['fp']}/{m['fn']} |")
    L.append("")


def english(L: list[str]) -> None:
    docs = {d["id"]: d for d in D.subset("golden_en")}
    rows = []
    for mk in ("m1", "ckpt1"):
        P = preds("golden_en", mk)
        for did, d in docs.items():
            t = d["text"]
            gold = d["gold"]
            for p in P[did]:
                if any(g["start"] == p["start"] and g["end"] == p["end"] and g["label"] == p["label"] for g in gold):
                    continue
                v = t[p["start"]:p["end"]]
                over = [g for g in gold if ov(g, p)]
                if over and any(g["label"] == p["label"] for g in over):
                    cat = "boundary (same label, other span)"
                elif over:
                    cat = f"wrong type (gold {'/'.join(sorted({g['label'] for g in over}))})"
                elif p["label"] == "DATE":
                    after = t[p["end"]:p["end"] + 12]
                    if STAMP_AFTER.match(after) or re.search(r"\d{1,2}:\d{2}", v):
                        cat = "DATE inside a date+time stamp (D-17: not DATE)"
                    elif DATE_RX.match(v.strip()):
                        cat = "standalone date unlabelled in gold (D-17: DATE)"
                    else:
                        cat = "DATE on other text"
                else:
                    cat = f"{p['label']} with no gold overlap"
                rows.append({"model": mk, "doc": did, "label": p["label"], "value": v, "category": cat,
                             "context": t[max(0, p["start"] - 45):p["end"] + 30].replace("\n", " ⏎ ")})
        # gold the model misses entirely
        for did, d in docs.items():
            for g in d["gold"]:
                if not any(ov(g, p) for p in P[did]):
                    rows.append({"model": mk, "doc": did, "label": g["label"], "value": d["text"][g["start"]:g["end"]],
                                 "category": "MISSED gold", "context": d["text"][max(0, g["start"] - 45):g["end"] + 30].replace("\n", " ⏎ ")})
    with (HERE / "english_review.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    E = ["# English (golden_en, 217 documents): every m1 prediction that is not an exact gold match", "",
         "Track M. Counts are **predicted spans (occurrences)**, not unique values or documents.", ""]
    for mk in ("m1", "ckpt1"):
        c = Counter((r["label"], r["category"]) for r in rows if r["model"] == mk)
        E += [f"## {mk}", "", "| Label | Category | Spans |", "|---|---|---|"]
        for (lab, cat), n in sorted(c.items(), key=lambda x: (-x[1])):
            E.append(f"| {lab} | {cat} | {n} |")
        E.append("")
    E += ["## m1 examples per category (first 12)", ""]
    by = defaultdict(list)
    for r in rows:
        if r["model"] == "m1":
            by[(r["label"], r["category"])].append(r)
    for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
        E.append(f"**{k[0]} — {k[1]}** ({len(v)})")
        for r in v[:12]:
            E.append(f"- `{r['value']}` … {r['context']}")
        E.append("")
    (HERE / "english.md").write_text("\n".join(E) + "\n", encoding="utf-8")
    m1 = Counter(r["category"] for r in rows if r["model"] == "m1")
    L += ["## 2. English", "", "m1 predicted spans that are not exact gold matches, by category (all labels): " +
          "; ".join(f"{k}: {n}" for k, n in m1.most_common()), "", "Details: `english.md`, `english_review.jsonl`.", ""]


def mac_features(text: str, s: int, e: int) -> dict:
    v = text[s:e]
    sep = ":" if ":" in v else "-" if "-" in v else "." if "." in v else "none"
    case = "upper" if v.upper() == v and re.search("[A-F]", v) else "lower" if v.lower() == v and re.search("[a-f]", v) else \
        "digits only" if not re.search("[A-Fa-f]", v) else "mixed"
    group = "4x3 (aabb.ccdd.eeff)" if re.fullmatch(r"[0-9A-Fa-f]{4}(\.[0-9A-Fa-f]{4}){2}", v) else \
        "2x6" if re.fullmatch(r"[0-9A-Fa-f]{2}([:\-.][0-9A-Fa-f]{2}){5}", v) else "12 bare" if re.fullmatch(r"[0-9A-Fa-f]{12}", v) else "other"
    before = text[max(0, s - 25):s]
    return {"value": v, "separator": sep, "case": case, "grouping": group,
            "label_word_near": bool(re.search(r"(?i)mac|fiziki ünvan|physical", before)),
            "prev_char": repr(text[s - 1]) if s else "^", "next_char": repr(text[e]) if e < len(text) else "$",
            "line_start": s == 0 or text[s - 1] == "\n", "chars_in_doc": len(text)}


def mac(L: list[str]) -> None:
    docs = D.subset("bench_mac")
    out = []
    fps = defaultdict(list)
    for d in docs:
        t = d["text"]
        gold = [g for g in d["gold"] if g["label"] == "MAC_ADDRESS"]
        res = {}
        for mk in ("v42", "m1"):
            P = preds("bench_mac", mk)[d["id"]]
            spans = [{"start": g["start"], "end": g["end"], "label": g["label"], "value": t[g["start"]:g["end"]]} for g in gold]
            r = score_case(t, spans, P)
            res[mk] = r
            for p in P:
                if p["label"] == "MAC_ADDRESS" and not any(ov(p, g) for g in d["gold"] if g["label"] == "MAC_ADDRESS"):
                    other = [g["label"] for g in d["gold"] if ov(p, g)]
                    fps[mk].append({"doc": d["id"], "value": t[p["start"]:p["end"]], "gold_there": other,
                                    "context": t[max(0, p["start"] - 35):p["end"] + 20].replace("\n", " ⏎ ")})
        for i, g in enumerate(gold):
            out.append({"doc": d["id"], **mac_features(t, g["start"], g["end"]),
                        "v42": res["v42"]["expected"][i]["category"], "m1": res["m1"]["expected"][i]["category"],
                        "m1_pred_labels": res["m1"]["expected"][i]["pred_labels"],
                        "m1_visible": res["m1"]["expected"][i]["visible"],
                        "context": t[max(0, g["start"] - 40):g["end"] + 25].replace("\n", " ⏎ ")})
    with (HERE / "mac_cases.jsonl").open("w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    ok = lambda c: c == "correct"  # noqa: E731
    quad = Counter(("v4.2 ok" if ok(r["v42"]) else "v4.2 wrong") + " / " + ("m1 ok" if ok(r["m1"]) else "m1 wrong") for r in out)
    Mx = ["# MAC addresses on the benchmark (374 gold values in the first 5,000 documents)", "",
          "Track M. Outcome per gold MAC (exact = correct; boundary = fully masked, right label, other span; "
          "wrong_type = fully masked, other label; partly_masked = some characters visible; missed = nothing masked).", "",
          "| v4.2 vs m1 | Values |", "|---|---|", *[f"| {k} | {n} |" for k, n in quad.most_common()], ""]
    for mk in ("v42", "m1"):
        Mx += [f"**{mk} outcome:** " + "; ".join(f"{k}: {n}" for k, n in Counter(r[mk] for r in out).most_common()), ""]
    for feat in ("separator", "case", "grouping", "label_word_near", "line_start", "next_char", "prev_char"):
        Mx += [f"## by {feat}", "", "| Value | Gold | v4.2 not exact | m1 not exact | m1 missed | m1 partly | m1 wrong type |",
               "|---|---|---|---|---|---|---|"]
        g = defaultdict(list)
        for r in out:
            g[str(r[feat])].append(r)
        for k, rs in sorted(g.items(), key=lambda kv: -len(kv[1])):
            Mx.append(f"| {k} | {len(rs)} | {sum(not ok(r['v42']) for r in rs)} | {sum(not ok(r['m1']) for r in rs)} | "
                      f"{sum(r['m1']=='missed' for r in rs)} | {sum(r['m1']=='partly_masked' for r in rs)} | "
                      f"{sum(r['m1']=='wrong_type' for r in rs)} |")
        Mx.append("")
    conf = Counter(tuple(r["m1_pred_labels"]) for r in out if r["m1"] == "wrong_type")
    Mx += ["m1 wrong-type predictions: " + "; ".join(f"{'/'.join(k)} ×{n}" for k, n in conf.most_common()), ""]
    for mk in ("v42", "m1"):
        Mx += [f"## {mk}: MAC predictions on non-MAC text ({len(fps[mk])})", ""]
        Mx += [f"- `{x['value']}` (gold there: {x['gold_there'] or 'none'}) … {x['context']}" for x in fps[mk][:25]]
        Mx.append("")
    Mx += ["## m1 failures where v4.2 is exact (first 30)", ""]
    Mx += [f"- {r['m1']}: `{r['value']}` sep {r['separator']}, {r['case']}, {r['grouping']} … {r['context']}"
           for r in out if ok(r["v42"]) and not ok(r["m1"])][:30]
    (HERE / "mac.md").write_text("\n".join(Mx) + "\n", encoding="utf-8")
    L += ["## 3. MAC", "", "v4.2 vs m1 per gold MAC (exact): " + "; ".join(f"{k}: {n}" for k, n in quad.most_common()),
          "", "Details: `mac.md`, `mac_cases.jsonl`.", ""]


def c13(L: list[str]) -> None:
    docs = [d for d in D.subset("names_list_lines")]
    C = ["# C13: names_list_lines control spans", "",
         "C13 (go_no_go.md): a family blocks when it is worse than checkpoint 1 on a target metric by more than 10 points "
         "**and** by more than 3 documents (D-41b). The control metric is span_fp_rate: a control span counts as masked "
         "if any prediction overlaps it.", "", "| Document | Control span | ckpt1 | v4.2 | m1 (M) | m1 predictions overlapping |",
         "|---|---|---|---|---|---|"]
    worse = 0
    for d in docs:
        for c in d.get("controls", []):
            row = []
            for mk in ("ckpt1", "v42", "m1"):
                P = preds("names_list_lines", mk)[d["id"]]
                row.append([p for p in P if ov(p, c)])
            txt = d["text"][c["start"]:c["end"]]
            m1hits = ", ".join(f"`{d['text'][p['start']:p['end']]}` {p['label']}" for p in row[2])
            C.append(f"| {d['id']} | `{txt}` | {'masked' if row[0] else 'clean'} | {'masked' if row[1] else 'clean'} | "
                     f"{'masked' if row[2] else 'clean'} | {m1hits or '–'} |")
            worse += bool(row[2]) and not row[0]
    C += ["", f"Documents worse than checkpoint 1 on the control metric (m1, M): **{worse}** (blocks only if > 3).", ""]
    (HERE / "c13.md").write_text("\n".join(C) + "\n", encoding="utf-8")
    L += ["## 4. C13", "", f"m1 documents worse than checkpoint 1 on name-list controls: {worse} (> 3 needed to block). "
          "Details: `c13.md`.", ""]


def main() -> int:
    L = ["# m1 audit: analysis of per-document predictions", ""]
    reproduce(L)
    english(L)
    mac(L)
    c13(L)
    (HERE / "analysis.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
