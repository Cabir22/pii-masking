"""Tests for eval/release_check.py: rule logic, the verdict, the go_no_go.md section and the PDF.

Run:  python eval/test_release_check.py
Synthetic reports only.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import release_check as RC  # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond, name, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(f"{name}: {detail}" if detail is not None else name)


# conditions: absolute and relative
check(RC.cond_pass({"op": ">=", "value": 0.8}, 0.8, None) is True, ">= at the threshold passes")
check(RC.cond_pass({"op": "<", "value": 0.15}, 0.15, None) is False, "< at the threshold fails")
check(RC.cond_pass({"op": "<=", "relative": 0.3}, 0.2, 1.0) is True, "relative: 0.2 <= 0.3 x 1.0")
check(RC.cond_pass({"op": "<", "relative": 1.0}, 0.4, 0.2) is False, "relative: leakage above checkpoint 1 fails")
check(RC.cond_pass({"op": "<", "relative": 1.0}, 0.4, None) is None, "relative without a baseline: unknown")
check(RC.cond_pass({"op": "==", "value": 0}, None, None) is None, "no measurement: unknown")


def lab(tp, fn, fp=0):
    r = tp / (tp + fn) if tp + fn else 0.0
    p = tp / (tp + fp) if tp + fp else 0.0
    return {"tp": tp, "fn": fn, "fp": fp, "recall": r, "precision": p, "f1": 2 * p * r / (p + r) if p + r else 0.0}


def block(labels, trig=0.05, pf=0.10):
    tp = sum(v["tp"] for v in labels.values()); fn = sum(v["fn"] for v in labels.values()); fp = sum(v["fp"] for v in labels.values())
    return {"exact": {"micro": {**lab(tp, fn, fp), "tp": tp, "fn": fn, "fp": fp}, "per_label": labels},
            "decoys": {"overall": {"decoys": 100, "rate_same_label": trig}},
            "documents": {"pii_free_fp_rate": pf}}


good = {l: lab(95, 5) for l in ("ACCESS_TOKEN", "IPV6_ADDRESS", "AZ_DRIVER_LICENSE_NUMBER", "IBAN")}
base = {l: lab(90, 10) for l in good}
rep = lambda b, xl=None: {"sets": {"shadow_dev": {"tracks": {"R": {"all": b, **({"excl_listed": xl} if xl else {})}}}}}  # noqa: E731
rows, _ = RC.shadow_rules(rep(block(good)), rep(block(base)), "test")
check([r["status"] for r in rows] == ["pass"] * 6, "shadow: a good model passes A1-A6", [(r["id"], r["status"]) for r in rows])
worse = dict(good, IBAN=lab(80, 20))
rows, _ = RC.shadow_rules(rep(block(worse)), rep(block(base)), "test")
a6 = next(r for r in rows if r["id"] == "A6")
check(a6["status"] == "fail" and "IBAN 90.0 → 80.0" in a6["result"], "A6: a label 10 points lower fails", a6)
xl = block(good, trig=0.05, pf=0.12); xl["documents_listed_docs_out"] = {"pii_free_fp_rate": 0.11}
rows, _ = RC.shadow_rules(rep(block(good, trig=0.09, pf=0.20), xl), rep(block(base)), "test")
a4, a5 = (next(r for r in rows if r["id"] == k) for k in ("A4", "A5"))
check(a4["status"] == "pass" and "with the policy-list items: 9.0%" in a4["result"], "A4 judged without the policy-list items, both shown", a4)
check(a5["status"] == "pass" and "20.0%" in a5["result"] and "11.0%" in a5["result"], "A5 judged without the policy-list items, both shown", a5)
rows, _ = RC.shadow_rules(None, None, "x")
check(all(r["status"] == "not scored" for r in rows) and len(rows) == 6, "no shadow report: A1-A6 not scored")

# --quick: runb_test not scored yet -> D1-D3 "not scored", report-only, the verdict unaffected
rows, k = RC.runb_rules(None, None, 0.7, 0.9)
check([r["id"] for r in rows] == ["D1", "D2", "D3"] and all(r["status"] == "not scored" and not r["blocking"] for r in rows)
      and k == {}, "no runb_test: D1-D3 not scored, not blocking", rows)

# verdict
mk = lambda st: [RC.rule(i, i, True, st.get(i, "pass"), "") for i in RC.BLOCKING] + [RC.rule("D1", "d", False, "report", "")]  # noqa: E731
check(RC.verdict(mk({}))["verdict"] == "release", "all blocking rules pass: release")
check(RC.verdict(mk({"A1": "not scored"}))["verdict"] == "incomplete", "a blocking rule not scored: incomplete")
v = RC.verdict(mk({"A1": "not scored", "C3": "fail"}))
check(v["verdict"] == "not released" and v["failed"] == ["C3"] and len(v["passed"]) == len(RC.BLOCKING) - 2, "a failure wins over missing", v)

# B3: no label more than 5 points of exact F1 below the previous model on the benchmark
def bench(f1s, support=100):
    pl = {lab: {"f1": f, "tp": support, "fn": 0} for lab, f in f1s.items()}
    return {"sets": {"benchmark": {"tracks": {"R": {"all": {"exact": {"per_label": pl}}}}}}}


r = RC.b3_rule(bench({"IPV6_ADDRESS": 0.722}), None, "v4.1")
check(r["status"] == "n/a" and not r["blocking"], "B3 without a previous model: n/a, not blocking", r)
r = RC.b3_rule(bench({"IPV6_ADDRESS": 0.722, "EMAIL": 0.99}), bench({"IPV6_ADDRESS": 0.978, "EMAIL": 0.99}), "v4.1")
check(r["status"] == "fail" and r["blocking"] and "IPV6_ADDRESS 97.8 → 72.2" in r["result"], "B3 catches the v4.1 -> v4.2 IPv6 drop", r)
r = RC.b3_rule(bench({"IPV6_ADDRESS": 0.93}), bench({"IPV6_ADDRESS": 0.978}), "v4.1")
check(r["status"] == "pass", "B3: a drop of 4.8 points passes", r)
r = RC.b3_rule(bench({"ICCID": 0.5}), bench({"ICCID": 0.9}, support=5), "v4.1")
check(r["status"] == "pass", "B3: labels with under 30 gold values are not judged (D-65b)", r)
r = RC.b3_rule(bench({"ICCID": 0.5}), bench({"ICCID": 0.9}, support=25), "v4.1")
check(r["status"] == "pass", "B3: 25 gold values is under D-65b's 30", r)

# --track M (D-64a): the rules read track M, and the other track is shown beside
two = {"sets": {"benchmark": {"tracks": {"R": {"all": {"exact": {"per_label": {"IPV6_ADDRESS": {"f1": 0.70, "tp": 100, "fn": 0}}}}},
                                         "M": {"all": {"exact": {"per_label": {"IPV6_ADDRESS": {"f1": 0.96, "tp": 100, "fn": 0}}}}}}}}}
prev = bench({"IPV6_ADDRESS": 0.978})
prev["sets"]["benchmark"]["tracks"]["M"] = prev["sets"]["benchmark"]["tracks"]["R"]
RC.DECIDES = "M"
check(RC.b3_rule(two, prev, "v4.1")["status"] == "pass" and RC.other() == "R", "--track M: B3 judges track M")
RC.DECIDES = "R"
check(RC.b3_rule(two, prev, "v4.1")["status"] == "fail", "--track R (default): B3 judges track R")

# go_no_go.md section: added once, replaced on rerun, other text kept
with tempfile.TemporaryDirectory() as tmp:
    g = Path(tmp) / "go_no_go.md"
    g.write_text("# Go/no-go\n\nhand-written rows\n", encoding="utf-8")
    RC.update_go_no_go(g, "rc_a", "first\n")
    RC.update_go_no_go(g, "rc_b", "other\n")
    RC.update_go_no_go(g, "rc_a", "second\n")
    t = g.read_text(encoding="utf-8")
    check(t.count("## Automatic release checks") == 1 and "hand-written rows" in t, "one automatic heading, hand-written text kept")
    check("second" in t and "first" not in t and t.count("release_check:rc_a:start") == 1, "rerun replaces the candidate's section")
    check("other" in t, "another candidate's section stays")
    res = {"meta": {"model": "m/x", "revision": "abcdef1234", "date_utc": "d", "code": "c", "shadow_source": "s"},
           "verdict": RC.verdict(mk({"C3": "fail"})), "rules": mk({"C3": "fail"})}
    pdf = Path(tmp) / "r.pdf"
    fitted = RC.write_pdf(res, pdf)
    b = pdf.read_bytes()
    check(b.startswith(b"%PDF-1.4") and b.rstrip().endswith(b"%%EOF") and b"/Count 1" in b and fitted, "PDF: one page, well formed")
    xref = int(b.rsplit(b"startxref", 1)[1].split()[0])
    check(b[xref:xref + 4] == b"xref", "PDF: startxref points at the xref table")

# D-77: C14 (code_density) blocks from m2; it is no longer a reported group
check("C14" in RC.BLOCKING and "C14" not in RC.REPORTED, "C14 is blocking (D-77)")
fake = {"sets": {"probes": {"tracks": {"M": {"targets": {"code_density": {"conditions": [
    {"metric": "exact_recall", "op": ">=", "value": 0.95, "measured": 0.895, "pass": False},
    {"metric": "slice_exact_recall_min", "field": "cell", "op": ">=", "value": 0.9, "measured": 0.2, "pass": False}]}}}}}}}
rows = RC.family_rows(fake, fake, "code_density", "M")
check([ok for *_, ok in rows] == [False, False], "code_density conditions fail when below D-77", rows)
check(RC.cond_name(rows[1][0]) == "slice_exact_recall_min [worst cell]", "condition name shows the slice", RC.cond_name(rows[1][0]))

# D-78: C15 (card_expiry) is reported for m2: never blocking, and left out of C13
check("C15" not in RC.BLOCKING and "card_expiry" in RC.REPORT_ONLY, "C15 is reported, not blocking (D-78)")
fake = {"meta": {"model": "x", "revision_sha": "y"}, "sets": {"probes": {"tracks": {"M": {"targets": {"card_expiry": {"conditions": [
    {"metric": "exact_recall", "labels": ["DATE"], "op": ">=", "value": 0.9, "measured": 0.0, "pass": False},
    {"metric": "control_fp_rate", "op": "<", "value": 0.1, "measured": 0.5, "pass": False}]}}}}}}}
base = {"meta": {"model": "x", "revision_sha": "z"}, "sets": {"probes": {"tracks": {"M": {"targets": {"card_expiry": {"conditions": [
    {"metric": "exact_recall", "labels": ["DATE"], "op": ">=", "value": 0.9, "measured": 0.9, "pass": True},
    {"metric": "control_fp_rate", "op": "<", "value": 0.1, "measured": 0.0, "pass": True}]}}}}}}}
RC.DECIDES = "M"
blocks, watched = RC.c13(fake, base, "/nonexistent", "M")
check(blocks == [] and watched == [], "a 90-point drop on card_expiry does not block C13 for m2", blocks)

# D-82: C16 (date_forms_az) is reported and left out of C13 (checkpoint 1 finds 28 of 75 exactly, m1 19)
check("C16" not in RC.BLOCKING and "date_forms_az" in RC.REPORT_ONLY, "C16 is reported, not blocking (D-82)")
fake["sets"]["probes"]["tracks"]["M"]["targets"] = {"date_forms_az": fake["sets"]["probes"]["tracks"]["M"]["targets"].pop("card_expiry")}
base["sets"]["probes"]["tracks"]["M"]["targets"] = {"date_forms_az": base["sets"]["probes"]["tracks"]["M"]["targets"].pop("card_expiry")}
blocks, watched = RC.c13(fake, base, "/nonexistent", "M")
check(blocks == [] and watched == [], "a 90-point drop on date_forms_az does not block C13", blocks)

if __name__ == "__main__":
    print(f"{PASS} passed, {FAIL} failed")
    for f in FAILURES:
        print("  FAIL", f)
    sys.exit(1 if FAIL else 0)
