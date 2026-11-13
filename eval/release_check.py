"""Judge a candidate against every go/no-go rule (docs/go_no_go.md, D-29 and later decisions)
from the scoreboard reports, and write the result.

    python eval/release_check.py --name TAG --probes-new P --probes-base P --runb-new P --runb-base P \
        [--real-new P --real-base P] [--bench-new P] [--bench-base P] [--shadow-new P --shadow-base P] \
        [--shadow-source TEXT] [--cache-dir DIR] --out-dir DIR [--go-no-go docs/go_no_go.md]

Usually run by scripts/release_check.sh. Writes <out-dir>/release_check.{json,md,pdf} and, with
--go-no-go, replaces this candidate's automatic section in docs/go_no_go.md. Aggregates only:
real-text and shadow-dev numbers are totals and per-label counts (A2.5), never text.

A rule whose set was not scored is "not scored", and the verdict is then "incomplete", never
"release". Blocking rules (F5): A1-A6, B1, B2, C1-C4, C13 (D-32b, D-41b), C14 (D-77, from m2), E3 (D-32c).
C15 (card expiry, D-78) is reported for m2 and left out of C13; it blocks from m3.
C16 (Azerbaijani date forms, D-82: weekdays outside DATE, year-first dates) is reported and left out of C13.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import metrics as M  # noqa: E402

BLOCKING = ["A1", "A2", "A3", "A4", "A5", "A6", "B1", "B2", "B3", "C1", "C2", "C3", "C4", "C13", "C14", "E3"]  # B3: only with --prev-bench
DECOY_FAMILIES = ["decoy_cvv", "decoy_time", "decoy_age", "decoy_date", "decoy_zip", "decoy_fin",
                  "decoy_voen_passport_id", "decoy_ipv4", "decoy_ipv6_mac", "decoy_card_iccid_iban",
                  "decoy_names_as_org"]
REPORTED = {  # C5-C11: A7 families, reported, not blocking
    "C5": ["building_vs_room", "sentence_initial_nouns", "nonpii_ids"],
    "C6": ["prose_card", "prose_date", "prose_iban", "anchor_distance", "inflected_anchor"],
    "C7": ["fmt_csv", "fmt_csv_noheader", "fmt_json", "fmt_pipe", "fmt_log", "fmt_kv", "fmt_dialogue"],
    "C8": ["pem", "spaced_phone", "spaced_card_iban"],
    "C9": ["suffixed_entities"],
    "C10": ["bare_name", "name_homographs"],
    "C11": ["name_transliteration_variants"],
}
REPORT_ONLY = {"card_expiry", "date_forms_az"}  # reported (C15 D-78, C16 D-82) and left out of C13; C15 blocks from m3
COUNT_METRICS = {"split_spans", "wrong_label"}  # counts, not rates
TIE = 1e-9


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8")) if p and Path(p).exists() else None


def pct(v, d=1):
    return "–" if v is None else f"{100 * v:.{d}f}"


DECIDES = "R"   # the track that decides (--track); D-64a (21 Oct): track M from m1 on


def other() -> str:
    return "M" if DECIDES == "R" else "R"


def tr(rep, set_name, track=None):
    return (rep or {}).get("sets", {}).get(set_name, {}).get("tracks", {}).get(track or DECIDES)


def rule(rid, name, blocking, status, result):
    """status: pass | fail | report | flag | n/a | not scored"""
    return {"id": rid, "rule": name, "blocking": blocking, "status": status, "result": result}


# --- probes ---------------------------------------------------------------------------------

def lower_is_better(cond):
    return cond["op"] in ("<", "<=", "==")


def cond_pass(cond, v, base_v):
    """Pass for an absolute or relative condition (relative: measured op f x checkpoint 1)."""
    if v is None:
        return None
    thr = cond.get("value")
    if "relative" in cond:
        if base_v is None:
            return None
        thr = cond["relative"] * base_v
    return {">=": v >= thr - TIE, ">": v > thr, "<": v < thr, "<=": v <= thr + TIE, "==": abs(v - thr) < TIE}[cond["op"]]


def family_rows(new, base, fam, track=None):
    """[(cond, measured new, measured base, pass)] for one family's target."""
    tn = tr(new, "probes", track)["targets"].get(fam)
    tb = tr(base, "probes", track)["targets"].get(fam)
    if not tn:
        return []
    out = []
    for i, c in enumerate(tn["conditions"]):
        b = tb["conditions"][i]["measured"] if tb else None
        out.append((c, c.get("measured"), b, cond_pass(c, c.get("measured"), b)))
    return out


def cond_name(c):
    extra = c.get("labels") or ([f"{c['from']}→{'/'.join(c['to'])}"] if c.get("from") else []) or \
        ([f"worst {c['field']}"] if c.get("field") else [])
    return f"{c['metric']}{' [' + ','.join(extra) + ']' if extra else ''}"


def probes_per_doc(cache_dir, rep, track=None):
    """The prediction cache of a probes report (offsets and labels only)."""
    import scoreboard as S
    m = rep["meta"]
    f = Path(cache_dir).expanduser() / S._slug(m["model"]) / S._slug(m["revision_sha"]) / f"probes.{track or DECIDES}.json"
    return json.loads(f.read_text(encoding="utf-8"))["preds"] if f.exists() else None


def c13(new, base, cache_dir, track=None):
    """D-32b + D-41b: a family blocks when a target metric is worse than checkpoint 1 by more
    than 10 points AND more than 3 documents got worse. Documents are compared one by one:
    the same metric on that document alone."""
    import scoreboard as S
    pn, pb = probes_per_doc(cache_dir, new, track), probes_per_doc(cache_dir, base, track)
    docs, _ = S.load_set("probes", argparse.Namespace(private_dir=str(ROOT / ".no-private-sets")))
    by_fam = {}
    for d in docs:
        by_fam.setdefault(d["meta"]["family"], []).append(d)
    blocks, watched = [], []
    for fam in sorted(tr(new, "probes", track)["targets"]):
        if fam in REPORT_ONLY:
            continue
        for c, vn, vb, _ in family_rows(new, base, fam, track):
            if vn is None or vb is None:
                continue
            gap = (vn - vb) if lower_is_better(c) else (vb - vn)
            if c["metric"] in COUNT_METRICS:
                gap = gap / 100  # a count: one more split span = 1 "point" x 100 in the report
            if gap * 100 <= 10:
                continue
            worse = None
            if pn is not None and pb is not None:
                worse = 0
                for d in by_fam.get(fam, []):
                    vals = []
                    for p in (pn, pb):
                        one = [{**d, "pred": p.get(d["id"], [])}]
                        sc = M.score_docs(one)
                        if c["metric"] == "exact_f1":  # F1 is undefined on one PII-free document: count its errors
                            vals.append(sc["exact"]["micro"]["fp"] + sc["exact"]["micro"]["fn"])
                        else:
                            vals.append(M._target_metric(c, sc, M.confusion_matrix(one)))
                    a, b = vals
                    if a is None or b is None:
                        continue
                    if c["metric"] == "exact_f1":
                        worse += a > b
                    else:
                        worse += (a > b + TIE) if lower_is_better(c) else (a < b - TIE)
            item = {"family": fam, "condition": cond_name(c), "base": vb, "new": vn,
                    "points_worse": round(100 * gap, 1), "documents_worse": worse}
            (blocks if worse is None or worse > 3 else watched).append(item)
    return blocks, watched


def probe_rules(new, base, cache_dir):
    R = []
    def group(rid, name, fams, metrics_ok=None):
        rows = [(f, c, vn, ok) for f in fams for c, vn, vb, ok in family_rows(new, base, f)
                if metrics_ok is None or metrics_ok(c)]
        bad = [f"{f} {cond_name(c)} {pct(vn)}" for f, c, vn, ok in rows if ok is False]
        st = "not scored" if not rows else ("fail" if bad else "pass")
        R.append(rule(rid, name, True, st, "; ".join(bad) if bad else f"{len(rows)} conditions met"))
    group("C1", "Access token vs API key", ["token_vs_key", "contrast_token_key"],
          lambda c: c["metric"] == "confusion_rate" or c.get("labels") == ["ACCESS_TOKEN"])
    group("C2", "IPv6 vs MAC", ["ipv6_vs_mac", "contrast_ipv6_mac"],
          lambda c: c["metric"] == "confusion_rate" or c.get("labels") == ["IPV6_ADDRESS"])
    group("C3", "Licence vs ID card", ["licence_vs_id", "contrast_licence_id"],
          lambda c: c["metric"] == "confusion_rate")
    # D-77: blocking from m2: every technical label >= 9/10 at 0, 2 and 6 unlabelled codes, family >= 95%
    group("C14", "Technical labels among unlabelled codes (D-77)", ["code_density"])
    # D-78: card expiry, reported for m2; from m3 it blocks (add "C15" to BLOCKING, drop it from REPORT_ONLY)
    rows = family_rows(new, base, "card_expiry")
    txt = "; ".join(f"{cond_name(c)} {pct(vn)} ({c['op']} {pct(c['value'], 0)}) {'met' if ok else 'not met'}"
                    for c, vn, vb, ok in rows)
    R.append(rule("C15", "Card expiry dates (D-78, blocking from m3)", "C15" in BLOCKING,
                  "not scored" if not rows else "report", txt or "family not scored"))
    # D-82: Azerbaijani weekday-next-to-date and year-first dates (probe), reported
    rows = family_rows(new, base, "date_forms_az")
    txt = "; ".join(f"{cond_name(c)} {pct(vn)} ({c['op']} {pct(c['value'], 0)}) {'met' if ok else 'not met'}"
                    for c, vn, vb, ok in rows)
    R.append(rule("C16", "Azerbaijani date forms (D-82, report)", "C16" in BLOCKING,
                  "not scored" if not rows else "report", txt or "family not scored"))
    # C4: every decoy family < 15% and < 10% overall (policy kinds left out, F3)
    trn = tr(new, "probes")
    fails, n, hit = [], 0, 0
    for f in DECOY_FAMILIES:
        rows = family_rows(new, base, f)
        for c, vn, vb, ok in rows:
            if ok is False:
                fails.append(f"{f} {pct(vn)}%")
        dec = trn["per_family"][f]["decoys"]
        excl = set(next((c.get("exclude_kinds", []) for c, *_ in rows), []))
        n += dec["overall"]["decoys"] - sum(v["decoys"] for k, v in dec["per_kind"].items() if k in excl)
        hit += dec["overall"]["triggered_same_label"] - sum(v["triggered_same_label"] for k, v in dec["per_kind"].items() if k in excl)
    overall = hit / n if n else None
    ok = not fails and overall is not None and overall < 0.10
    cvv = trn["per_family"]["decoy_cvv"]["decoys"]["per_kind"]
    split = "; ".join(f"{name} {cvv[k]['triggered_same_label']}/{cvv[k]['decoys']}"
                      for k, name in (("d2_dummy", "12345"), ("invalid_shape", "random 5-digit")) if k in cvv)
    R.append(rule("C4", "Look-alikes: < 15% each, < 10% overall", True, "pass" if ok else "fail",
                  f"{len(fails)} of {len(DECOY_FAMILIES)} families above 15%" + (f" ({', '.join(fails)})" if fails else "")
                  + f"; overall {pct(overall)}%" + (f"; decoy_cvv: {split}" if split else "")))
    for rid, fams in REPORTED.items():
        rows = [(f, ok) for f in fams for c, vn, vb, ok in family_rows(new, base, f)]
        met = sum(1 for f in fams if all(ok is not False for g, ok in rows if g == f) and any(g == f for g, _ in rows))
        R.append(rule(rid, f"{', '.join(fams[:3])}{'…' if len(fams) > 3 else ''}", False, "report",
                      f"{met} of {len(fams)} families meet their target"))
    tn = trn["targets"]
    passing = sum(1 for v in tn.values() if all(c.get("pass") is not False for c in v["conditions"])
                  and any(c.get("pass") is True for c in v["conditions"]))
    R.append(rule("C12", "All probe families with targets (report)", False, "report",
                  f"{passing} of {len(tn)} families meet every absolute target (track R)"))
    blocks, watched = c13(new, base, cache_dir)
    txt = "; ".join(f"{b['family']} {b['condition']} {pct(b['base'])} → {pct(b['new'])} "
                    f"({b['documents_worse'] if b['documents_worse'] is not None else '?'} docs worse)" for b in blocks)
    R.append(rule("C13", "No family >10 pt and >3 docs worse", True,
                  "fail" if blocks else "pass", (txt or "none") + (f"; watched: {', '.join(w['family'] for w in watched)}" if watched else "")))
    return R, {"c13_blocks": blocks, "c13_watched": watched, "c4_overall": overall}


# --- shadow-dev, benchmark, runb_test, real text --------------------------------------------

def recall_guard(new_all, base_all):
    viol = []
    for lab, b in base_all["exact"]["per_label"].items():
        if b["tp"] + b["fn"] == 0:
            continue
        c = new_all["exact"]["per_label"].get(lab, {"recall": 0.0})
        if c["recall"] < b["recall"] - 0.01:
            viol.append((lab, b["recall"], c["recall"]))
    return sorted(viol, key=lambda x: x[2] - x[1])


def fmt_viol(v):
    return ", ".join(f"{lab} {pct(b)} → {pct(c)}" for lab, b, c in v)


def shadow_rules(new, base, source):
    n, b = tr(new, "shadow_dev"), tr(base, "shadow_dev")
    if not n:
        return [rule(r, t, True, "not scored", "shadow-dev not scored") for r, t in
                [("A1", "Micro F1 ≥ 82"), ("A2", "Weakest label F1 ≥ 65"), ("A3", "Token, IPv6, licence F1 ≥ 75 each"),
                 ("A4", "Look-alike trigger rate < 8%"), ("A5", "PII-free documents masked < 15%"),
                 ("A6", "Recall guard vs checkpoint 1")]], {}
    a = n["all"]
    pl = {l: v for l, v in a["exact"]["per_label"].items() if v["tp"] + v["fn"]}
    weak = min(pl.items(), key=lambda kv: kv[1]["f1"])
    three = [(l, pl[l]["f1"]) for l in ("ACCESS_TOKEN", "IPV6_ADDRESS", "AZ_DRIVER_LICENSE_NUMBER")]
    xl = n.get("excl_listed")  # D-42, D-51e: without the private policy list
    trig_all = a["decoys"]["overall"]["rate_same_label"]
    pf_all = a["documents"]["pii_free_fp_rate"]
    trig = xl["decoys"]["overall"]["rate_same_label"] if xl else trig_all
    pf = xl["documents"]["pii_free_fp_rate"] if xl else pf_all
    note = (f" (with the policy-list items: {pct(trig_all)}%)" if xl else " (policy list not applied)")
    note5 = (f" (with the policy-list items: {pct(pf_all)}%; their documents out of the count: "
             f"{pct(xl['documents_listed_docs_out']['pii_free_fp_rate'])}%)" if xl else " (policy list not applied)")
    R = [rule("A1", "Micro F1 ≥ 82", True, "pass" if a["exact"]["micro"]["f1"] >= 0.82 else "fail",
              f"{pct(a['exact']['micro']['f1'])} (checkpoint 1 {pct(b['all']['exact']['micro']['f1']) if b else '–'})"),
         rule("A2", "Weakest label F1 ≥ 65", True, "pass" if weak[1]["f1"] >= 0.65 else "fail",
              f"{pct(weak[1]['f1'])} ({weak[0]})"),
         rule("A3", "Token, IPv6, licence F1 ≥ 75 each", True,
              "pass" if all(v >= 0.75 for _, v in three) else "fail", ", ".join(f"{l} {pct(v)}" for l, v in three)),
         rule("A4", "Look-alike trigger rate < 8%", True, "pass" if trig < 0.08 else "fail", f"{pct(trig)}%{note}"),
         rule("A5", "PII-free documents masked < 15%", True, "pass" if pf < 0.15 else "fail", f"{pct(pf)}%{note5}")]
    if b:
        v = recall_guard(a, b["all"])
        vm = recall_guard(tr(new, "shadow_dev", other())["all"], tr(base, "shadow_dev", other())["all"]) \
            if tr(new, "shadow_dev", other()) and tr(base, "shadow_dev", other()) else []
        R.append(rule("A6", "Recall guard (no label −1 pt)", True, "fail" if v else "pass",
                      (f"{len(v)} labels: {fmt_viol(v)}" if v else "no label drops") + (f"; {other()}: {len(vm)} labels" if vm else "")))
    else:
        R.append(rule("A6", "Recall guard vs checkpoint 1", True, "not scored", "no checkpoint-1 shadow report"))
    for r in R:
        r["result"] += f" [{source}]" if r["id"] == "A1" else ""
    return R, {"shadow_f1_R": a["exact"]["micro"]["f1"]}


def bench_rules(new, base):
    n, b = tr(new, "benchmark"), tr(base, "benchmark")
    if not (n and b):
        return [rule("B1", "Benchmark F1 ≥ checkpoint 1 + 2", True, "not scored", "benchmark not scored"),
                rule("B2", "Benchmark recall guard", True, "not scored", "benchmark not scored")], {}
    f_all, fb_all = n["all"]["exact"]["micro"]["f1"], b["all"]["exact"]["micro"]["f1"]
    # D-51e (and the 15 Oct follow-up): judged without the policy items (both models), shown with them
    xp = "excl_policy" in n and "excl_policy" in b
    f, fb = (n["excl_policy"]["exact"]["micro"]["f1"], b["excl_policy"]["exact"]["micro"]["f1"]) if xp else (f_all, fb_all)
    note = (f"; with the policy items {pct(f_all)} vs {pct(fb_all)}" if xp else
            "; policy items not marked in both reports" if "excl_policy" in n or "excl_policy" in b else "")
    v = recall_guard(n["all"], b["all"])
    m = tr(new, "benchmark", other())
    return [rule("B1", "Benchmark F1 ≥ checkpoint 1 + 2", True, "pass" if f >= fb + 0.02 - TIE else "fail",
                 f"{pct(f)} vs {pct(fb)} (needs {pct(fb + 0.02)}){note}"
                 f"{'; ' + other() + ' ' + pct(m['all']['exact']['micro']['f1']) if m else ''}"),
            rule("B2", "Benchmark recall guard (−1 pt)", True, "fail" if v else "pass",
                 f"{len(v)} labels: {fmt_viol(v)}" if v else "no label drops")], {"bench_f1_R": f_all}


def b3_rule(new, prev, prev_name, track=None, drop=0.05, min_support=30):
    """B3 (23 Oct; the per-label check, v4.1 -> v4.2 IPv6 97.8 -> 72.2): on the
    benchmark, no label more than 5 points of exact F1 below the previous model (labels with at
    least `min_support` gold values in the previous model's report). Policy items out when both
    reports mark them. Without a previous model's report the rule does not apply (n/a)."""
    if prev is None:
        return rule("B3", "No label > 5 pt below the previous model", False, "n/a", "no previous model given (--prev-bench)")
    n, p = tr(new, "benchmark", track), tr(prev, "benchmark", track)
    if not (n and p):
        return rule("B3", "No label > 5 pt below the previous model", True, "not scored", "benchmark not scored")
    sub = "excl_policy" if "excl_policy" in n and "excl_policy" in p else "all"
    viol = []
    for lab, b in p[sub]["exact"]["per_label"].items():
        if b["tp"] + b["fn"] < min_support:
            continue
        c = n[sub]["exact"]["per_label"].get(lab, {"f1": 0.0})
        if c["f1"] < b["f1"] - drop - TIE:
            viol.append((lab, b["f1"], c["f1"]))
    viol.sort(key=lambda x: x[2] - x[1])
    where = f"vs {prev_name}" + (", policy items out" if sub == "excl_policy" else "")
    return rule("B3", "No label > 5 pt below the previous model", True, "fail" if viol else "pass",
                (f"{len(viol)} labels: {fmt_viol(viol)} ({where})" if viol else f"no label drops more than 5 points ({where})"))


def runb_rules(new, base, real_f1, bench_f1):
    n, b = tr(new, "runb_test"), tr(base, "runb_test")
    if not (n and b):  # --quick: runb_test is scored afterwards (D1-D3 are report-only)
        return [rule("D1", "runb_test vs checkpoint 1 (report)", False, "not scored", "runb_test not scored yet (--quick)"),
                rule("D2", "Template overfitting: gap ≤ 15 points", False, "not scored", "needs runb_test"),
                rule("D3", "Old vs new documents (report)", False, "not scored", "runb_test not scored yet")], {}
    nm, bm = tr(new, "runb_test", other()), tr(base, "runb_test", other())
    f = n["all"]["exact"]["micro"]["f1"]
    R = [rule("D1", "runb_test vs checkpoint 1 (report)", False, "report",
              f"{DECIDES} {pct(f)} / {other()} {pct(nm['all']['exact']['micro']['f1']) if nm else '–'} "
              f"(checkpoint 1 {pct(b['all']['exact']['micro']['f1'])} / {pct(bm['all']['exact']['micro']['f1']) if bm else '–'}); "
              f"PII-free FP {pct(n['all']['documents']['pii_free_fp_rate'])}%")]
    gaps = [(k, f - v) for k, v in (("real text", real_f1), ("benchmark", bench_f1)) if v is not None]
    flag = [k for k, g in gaps if g > 0.15]
    R.append(rule("D2", "Template overfitting: gap ≤ 15 points", False, "flag" if flag else "report",
                  "; ".join(f"vs {k} {100 * g:.1f} points" for k, g in gaps) or "no other set"))
    bp = n.get("by_part", {})
    R.append(rule("D3", "Old vs new documents (report)", False, "report",
                  f"old {pct(bp.get('old', {}).get('exact', {}).get('micro', {}).get('f1'))} / "
                  f"new {pct(bp.get('new', {}).get('exact', {}).get('micro', {}).get('f1'))}" if bp else "no split"))
    return R, {"runb_f1_R": f}


def real_rules(new, base):
    n, b = tr(new, "real_text"), tr(base, "real_text")
    if not (n and b):
        return [rule("E1", "Real text per label (report)", False, "not scored", "real text not scored"),
                rule("E2", "Real-text recall guard (report)", False, "not scored", ""),
                rule("E3", "Real text: 80% found, labels, precision", True, "not scored",
                     "real text not scored")], {}
    e, eb = n["all"]["exact"], b["all"]["exact"]
    tp, gold = e["micro"]["tp"], e["micro"]["tp"] + e["micro"]["fn"]
    prec = e["micro"]["precision"]
    found = tp / gold if gold else None
    big = [(l, v["tp"], eb["per_label"].get(l, {"tp": 0})["tp"], v["tp"] + v["fn"])
           for l, v in e["per_label"].items() if v["tp"] + v["fn"] >= 10]
    worse_big = [x for x in big if x[1] < x[2]]
    worse_any = [l for l, v in e["per_label"].items() if v["tp"] < eb["per_label"].get(l, {"tp": 0})["tp"]]
    ok = found is not None and found >= 0.80 and not worse_big and prec >= 0.70
    return [rule("E1", "Real text per label (report)", False, "report",
                 f"{tp} of {gold} found (checkpoint 1 {eb['micro']['tp']}); labels finding fewer: {', '.join(worse_any) or 'none'}"),
            rule("E2", "Real-text recall guard (report)", False, "report", "see E1"),
            rule("E3", "Real text: 80% found, labels, precision", True, "pass" if ok else "fail",
                 f"(1) {pct(found)}% found {'ok' if found and found >= 0.80 else 'FAIL'}; "
                 f"(2) {', '.join(f'{l} {a} vs {c} of {g}' for l, a, c, g in big)} {'FAIL' if worse_big else 'ok'}; "
                 f"(3) precision {pct(prec)}% {'ok' if prec >= 0.70 else 'FAIL'}")], {"real_f1_R": e["micro"]["f1"]}


# --- multilingual (D-46) -------------------------------------------------------------------

TRANSLATED = {"en": "golden_en", "tr": "lang_tr", "ru": "lang_ru"}


def a7_rule(lang_new, lang_base, real_new, real_base):
    """D-46b: per language, exact micro F1 (R) at most 1 point below checkpoint 1 on the translated
    set and, once it exists, on the independent real-text set; until then the translated set alone."""
    parts, bad, missing = [], [], []
    for lang, tset in TRANSLATED.items():
        rows = []
        for kind, sname, new, base in (("translated", tset, lang_new, lang_base),
                                       ("independent", f"real_text_{lang}", real_new, real_base)):
            n, b = tr(new, sname), tr(base, sname)
            if not (n and b):
                if kind == "translated":
                    missing.append(f"{lang} translated")
                rows.append(f"{kind} not scored" if kind == "translated" else "no independent set yet: translated only")
                continue
            fn, fb = n["all"]["exact"]["micro"]["f1"], b["all"]["exact"]["micro"]["f1"]
            ok = fn >= fb - 0.01 - TIE
            if not ok:
                bad.append(f"{lang} {kind}")
            rows.append(f"{kind} {pct(fb)} → {pct(fn)}{'' if ok else ' FAIL'}")
        parts.append(f"{lang.upper()}: " + ", ".join(rows))
    st = "fail" if bad else ("not scored" if missing else "pass")
    return rule("A7", "EN / TR / RU ≤ 1 point below checkpoint 1 (D-46b)", True, st, "; ".join(parts))


def a10_rule(new_shadow, v3_shadow, new_bench, v3_bench):
    """D-46a: no Azerbaijani label loses more than 1 point of recall against v3 (shadow-dev, benchmark)."""
    if not (v3_shadow or v3_bench):
        return rule("A10", "Azerbaijani labels vs v3 (D-46a)", False, "n/a",
                    "v3 not given (not released): the Azerbaijani bar is checkpoint 1, rules A1-E3")
    out, viol, missing = [], False, []
    for name, new, ref in (("shadow-dev", new_shadow, v3_shadow), ("benchmark", new_bench, v3_bench)):
        sname = "shadow_dev" if name == "shadow-dev" else "benchmark"
        n, r = tr(new, sname), tr(ref, sname)
        if not (n and r):
            missing.append(name)
            continue
        v = recall_guard(n["all"], r["all"])
        viol = viol or bool(v)
        out.append(f"{name}: " + (f"{len(v)} labels: {fmt_viol(v)}" if v else "no label drops"))
    st = "fail" if viol else ("not scored" if missing else "pass")
    return rule("A10", "Azerbaijani labels vs v3, −1 pt (D-46a)", True, st,
                "; ".join(out + [f"{m} not scored" for m in missing]))


# --- outputs --------------------------------------------------------------------------------

def verdict(rules):
    blk = [r for r in rules if r["blocking"]]
    missing = [r["id"] for r in blk if r["status"] == "not scored"]
    failed = [r["id"] for r in blk if r["status"] == "fail"]
    passed = [r["id"] for r in blk if r["status"] == "pass"]
    v = "not released" if failed else ("incomplete" if missing else "release")
    return {"verdict": v, "passed": passed, "failed": failed, "missing": missing, "blocking_total": len(blk)}


STATUS_MD = {"pass": "**pass**", "fail": "**fail**", "flag": "**flagged**", "report": "report", "n/a": "n/a",
             "not scored": "not scored"}


def render_md(res):
    m, v = res["meta"], res["verdict"]
    L = [f"### Automatic release check: `{m['model']}` @ `{m['revision'][:7]}`", "",
         f"`scripts/release_check.sh`, {m['date_utc']}, code `{m['code']}`. Track {m.get('track', 'R')} decides; shadow-dev: {m['shadow_source']}.", "",
         f"**Verdict: {v['verdict']}.** Passes **{len(v['passed'])} of {v['blocking_total']}** blocking rules"
         + (f"; fails {', '.join(v['failed'])}" if v["failed"] else "")
         + (f"; not scored: {', '.join(v['missing'])}" if v["missing"] else "") + ".", "",
         "| # | Rule | Blocking | Result | Status |", "|---|---|---|---|---|"]
    for r in res["rules"]:
        L.append(f"| {r['id']} | {r['rule']} | {'yes' if r['blocking'] else 'no'} | {r['result']} | {STATUS_MD[r['status']]} |")
    return "\n".join(L) + "\n"


def update_go_no_go(path, tag, block):
    text = Path(path).read_text(encoding="utf-8") if Path(path).exists() else "# Release checks\n"
    start, end = f"<!-- release_check:{tag}:start -->", f"<!-- release_check:{tag}:end -->"
    body = f"{start}\n{block}{end}"
    if start in text:
        text = re.sub(re.escape(start) + r".*?" + re.escape(end), lambda _: body, text, flags=re.S)
    else:
        head = "## Automatic release checks"
        if head not in text:
            text = text.rstrip("\n") + f"\n\n{head}\n\nWritten by `scripts/release_check.sh`; rerun it to refresh. " \
                "The hand-written rows above stay the record of what was decided.\n"
        text = text.rstrip("\n") + f"\n\n{body}\n"
    Path(path).write_text(text, encoding="utf-8")


def _pdf_text(s):
    s = (s.replace("≥", ">=").replace("≤", "<=").replace("→", "->").replace("−", "-").replace("…", "...")
         .replace("ə", "e").replace("Ə", "E"))
    s = s.encode("cp1252", "replace").decode("cp1252")
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_pdf(res, path):
    """One A4 page, built by hand (no PDF library on the server): Helvetica headings, Courier table."""
    W, H, X = 595, 842, 36
    ops, y = [], H - 44

    def line(txt, font="F1", size=8.0, color=(0, 0, 0), x=X, lead=None):
        nonlocal y
        ops.append(f"BT /{font} {size} Tf {color[0]} {color[1]} {color[2]} rg {x} {y:.1f} Td ({_pdf_text(txt)}) Tj ET")
        y -= lead or size + 3

    m, v = res["meta"], res["verdict"]
    line("Release check", "F2", 16, lead=20)
    line(f"{m['model']} @ {m['revision'][:7]}   vs checkpoint 1 (your-hf-org/masking-multilingual @ 3a0a6e5)", "F1", 9)
    line(f"{m['date_utc']}   code {m['code']}   track R decides   shadow-dev: {m['shadow_source']}", "F1", 8, lead=16)
    col = (0.0, 0.5, 0.0) if v["verdict"] == "release" else ((0.75, 0.0, 0.0) if v["verdict"] == "not released" else (0.6, 0.4, 0.0))
    line(f"Verdict: {v['verdict'].upper()}   -   passes {len(v['passed'])} of {v['blocking_total']} blocking rules",
         "F2", 12, col, lead=15)
    if v["failed"]:
        line("Fails: " + ", ".join(v["failed"]), "F1", 9, (0.75, 0, 0))
    if v["missing"]:
        line("Not scored: " + ", ".join(v["missing"]), "F1", 9, (0.6, 0.4, 0))
    y -= 6
    cw = 7.2 * 0.6  # Courier advance width at 7.2 pt
    line(f"{'#':<4}{'Rule':<42}{'Status':<9}Result", "F3", 7.2, lead=10)
    for r in res["rules"]:
        st = r["status"].upper() if r["blocking"] else r["status"]
        c = {"pass": (0, 0.5, 0), "fail": (0.75, 0, 0), "flag": (0.6, 0.4, 0)}.get(r["status"], (0.25, 0.25, 0.25))
        name = r["rule"] if len(r["rule"]) <= 39 else r["rule"][:38] + "…"
        name += "*" if r["blocking"] else ""
        chunks = textwrap.wrap(r["result"], 66, break_long_words=True, break_on_hyphens=False) or [""]
        for i, chunk in enumerate(chunks):
            if i == 0:
                ops.append(f"BT /F3 7.2 Tf 0 0 0 rg {X} {y:.1f} Td ({_pdf_text(r['id'].ljust(4) + name)}) Tj ET")
                ops.append(f"BT /F3 7.2 Tf {c[0]} {c[1]} {c[2]} rg {X + 46 * cw:.1f} {y:.1f} Td ({_pdf_text(st)}) Tj ET")
            ops.append(f"BT /F3 7.2 Tf 0 0 0 rg {X + 55 * cw:.1f} {y:.1f} Td ({_pdf_text(chunk)}) Tj ET")
            y -= 9
        if y < 40:
            break
    y -= 4
    line("* blocking rule (F5). Aggregates only; real-text and shadow-dev texts never leave the private folder (A2.5).",
         "F1", 7, (0.3, 0.3, 0.3))
    stream = "\n".join(ops).encode("cp1252", "replace")
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {W} {H}] /Resources << /Font << /F1 4 0 R /F2 5 0 R /F3 6 0 R >> >> /Contents 7 0 R >>".encode(),
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>",
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"]
    out, offs = bytearray(b"%PDF-1.4\n"), []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offs)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    Path(path).write_bytes(bytes(out))
    return y >= 40  # everything fitted on the page


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ("probes-new", "probes-base", "runb-new", "runb-base", "real-new", "real-base",
              "bench-new", "shadow-new", "shadow-base"):
        ap.add_argument(f"--{k}")
    ap.add_argument("--bench-base", default=str(ROOT / "reports" / "scoreboard" / "baseline_ckpt1_benchmark.json"))
    ap.add_argument("--shadow-source", default="not scored")
    ap.add_argument("--track", choices=("R", "M"), default="R", help="the track that decides (D-64a: M from m1 on)")
    ap.add_argument("--prev-bench", help="the previous model's benchmark report, for B3 (no label > 5 pt below it)")
    ap.add_argument("--prev-name", default="the previous model", help="its name in B3's result")
    ap.add_argument("--multilingual", action="store_true", help="a multilingual candidate: A7 and A10 apply (D-46)")
    for k in ("lang-new", "real-lang-new", "real-lang-base", "v3-bench", "v3-shadow"):
        ap.add_argument(f"--{k}")
    ap.add_argument("--lang-base", default=str(ROOT / "reports" / "scoreboard" / "baseline_ckpt1_langs.json"))
    ap.add_argument("--cache-dir", default=str(Path.home() / ".cache" / "pii-scoreboard"))
    ap.add_argument("--name", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--go-no-go")
    a = ap.parse_args(argv)
    global DECIDES
    DECIDES = a.track
    pn, pb = load(a.probes_new), load(a.probes_base)
    rn, rb = load(a.runb_new), load(a.runb_base)
    if not (pn and pb):
        raise SystemExit("probes reports for both models are required")
    import scoreboard as S
    meta = {"name": a.name, "model": pn["meta"]["model"], "revision": pn["meta"]["revision_sha"],
            "date_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "code": S.git_info()["sha"][:7], "shadow_source": a.shadow_source, "track": DECIDES}
    rules, keys = [], {}
    rs, k = shadow_rules(load(a.shadow_new), load(a.shadow_base), a.shadow_source); rules += rs; keys.update(k)
    if a.multilingual:
        rules.append(a7_rule(load(a.lang_new), load(a.lang_base), load(a.real_lang_new), load(a.real_lang_base)))
        rules.append(a10_rule(load(a.shadow_new), load(a.v3_shadow), load(a.bench_new), load(a.v3_bench)))
    else:
        rules.append(rule("A7", "EN / TR / RU regression", False, "n/a", "not applied: Azerbaijani-only model (D-23a)"))
    rules += [rule("A8", "Benchmark errors fixed (appendix)", False, "report", "not run by this script"),
              rule("A9", "Sealed set, once, on the final candidate", False, "n/a", "untouched (final candidate only, P3-11)")]
    rs, k = bench_rules(load(a.bench_new), load(a.bench_base)); rules += rs; keys.update(k)
    rules.append(b3_rule(load(a.bench_new), load(a.prev_bench), a.prev_name))
    rs, k = probe_rules(pn, pb, a.cache_dir); rules += rs; keys.update(k)
    real_rows, k = real_rules(load(a.real_new), load(a.real_base)); keys.update(k)
    rs, k = runb_rules(rn, rb, keys.get("real_f1_R"), keys.get("bench_f1_R")); rules += rs; keys.update(k)
    rules += real_rows
    order = {r: i for i, r in enumerate(["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A10", "A8", "A9", "B1", "B2", "B3", "C1", "C2", "C3",
                                         "C4", "C5", "C6", "C7", "C8", "C9", "C10", "C11", "C12", "C13", "C14", "C15", "C16", "D1", "D2", "D3",
                                         "E1", "E2", "E3"])}
    rules.sort(key=lambda r: order[r["id"]])
    res = {"meta": meta, "verdict": verdict(rules), "rules": rules, "key_numbers": keys}
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "release_check.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    md = render_md(res)
    (out / "release_check.md").write_text(md, encoding="utf-8")
    fitted = write_pdf(res, out / "release_check.pdf")
    if a.go_no_go:
        update_go_no_go(a.go_no_go, a.name, md)
    v = res["verdict"]
    print(f"verdict: {v['verdict']}; passes {len(v['passed'])} of {v['blocking_total']} blocking rules; "
          f"fails {', '.join(v['failed']) or 'none'}; not scored {', '.join(v['missing']) or 'none'}")
    print(f"wrote {out}/release_check.{{json,md,pdf}}{' (PDF cut at one page)' if not fitted else ''}"
          + (f" and the automatic section in {a.go_no_go}" if a.go_no_go else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
