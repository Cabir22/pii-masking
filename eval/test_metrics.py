"""Tests for eval/metrics.py on small hand-made examples. No model, no data
files -- same plain-script style as model/test_predict.py.

Run:  python eval/test_metrics.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from metrics import (appendix_replay, boundary_errors, calibration,  # noqa: E402
                     char_leakage, control_fp, decoy_triggers, document_rates,
                     drop_policy_predictions, exact_scores, gold_outcome,
                     gold_recall, new_name_recall, overlap_scores,
                     seen_values, slices)

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond, name, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(f"{name}: {detail}" if detail is not None else name)


def close(a, b, eps=1e-9):
    return a is not None and abs(a - b) < eps


def S(label, start, end, score=None):
    s = {"label": label, "start": start, "end": end}
    if score is not None:
        s["score"] = score
    return s


def doc(gold, pred, decoys=None, meta=None, text=None):
    return {"id": "d", "text": text or "x" * 100, "gold": gold, "pred": pred,
            "decoys": decoys or [], "meta": meta or {}}


# --- exact vs overlap ------------------------------------------------------
# Gold DATE 10-20; prediction 10-18 (right label, narrower). Exact: 1 FP + 1
# FN. Overlap: the prediction counts as correct and the gold as found.
d1 = doc([S("DATE", 10, 20)], [S("DATE", 10, 18)])
ex = exact_scores([d1])
check(ex["micro"]["tp"] == 0 and ex["micro"]["fp"] == 1 and ex["micro"]["fn"] == 1,
      "exact: one-char-short span is FP+FN", ex["micro"])
ov = overlap_scores([d1])
check(close(ov["micro"]["precision"], 1.0) and close(ov["micro"]["recall"], 1.0),
      "overlap: narrower same-label span is a hit", ov["micro"])

# Wrong label on the exact span: FP+FN in both methods.
d2 = doc([S("AZ_DRIVER_LICENSE_NUMBER", 0, 9)], [S("AZ_ID_CARD_NUMBER", 0, 9)])
check(exact_scores([d2])["micro"]["tp"] == 0, "exact: wrong label is not a TP")
check(close(overlap_scores([d2])["micro"]["recall"], 0.0), "overlap: wrong label is not found")

# Exact hit plus a spurious one: P = 1/2, R = 1, F1 = 2/3; per-label and macro.
d3 = doc([S("CITY", 0, 4)], [S("CITY", 0, 4), S("BUILDINGNUM", 10, 13)])
ex = exact_scores([d3])
check(close(ex["micro"]["precision"], 0.5) and close(ex["micro"]["recall"], 1.0)
      and close(ex["micro"]["f1"], 2 / 3), "exact: micro P/R/F1", ex["micro"])
check(close(ex["per_label"]["CITY"]["f1"], 1.0) and close(ex["per_label"]["BUILDINGNUM"]["f1"], 0.0),
      "exact: per-label F1", ex["per_label"])
check(close(ex["macro_f1"], 0.5), "exact: macro F1 = mean over labels seen", ex["macro_f1"])

# Duplicate prediction of one gold span: 1 TP + 1 FP (multiset matching).
d4 = doc([S("AGE", 5, 7)], [S("AGE", 5, 7), S("AGE", 5, 7)])
m = exact_scores([d4])["micro"]
check(m["tp"] == 1 and m["fp"] == 1 and m["fn"] == 0, "exact: duplicates are multiset", m)

# One long prediction covering two gold values: overlap P = 1/1, R = 2/2.
d5 = doc([S("TELEPHONENUM", 0, 5), S("TELEPHONENUM", 6, 10)], [S("TELEPHONENUM", 0, 10)])
ov = overlap_scores([d5])["micro"]
check(ov["n_pred"] == 1 and ov["n_gold"] == 2 and close(ov["recall"], 1.0)
      and close(ov["precision"], 1.0), "overlap: one wide span finds two gold", ov)

# --- leakage ---------------------------------------------------------------
# Gold 10-20 (10 chars) with a prediction covering 10-18: 2 chars leak.
# A second gold 30-34 covered by a WRONG-label span leaks nothing (masked).
d6 = doc([S("IBAN", 10, 20), S("CITY", 30, 34)], [S("IBAN", 10, 18), S("GIVENNAME", 29, 35)])
lk = char_leakage([d6])
check(lk["gold_chars"] == 14 and lk["leaked_chars"] == 2 and close(lk["rate"], 2 / 14),
      "leakage: uncovered gold chars / all gold chars", lk)
check(lk["per_label"]["CITY"]["leaked_chars"] == 0, "leakage: wrong label still masks", lk["per_label"])
# Two overlapping predictions must not double-count coverage.
d7 = doc([S("EMAIL", 0, 10)], [S("EMAIL", 0, 6), S("EMAIL", 4, 8)])
check(char_leakage([d7])["leaked_chars"] == 2, "leakage: overlapping preds counted once")
check(char_leakage([doc([], [])])["rate"] == 0.0, "leakage: no gold -> 0")

# --- boundary --------------------------------------------------------------
d8 = doc([S("PAYMENT_CARD_NUMBER", 10, 29), S("DATE", 40, 50), S("TIME", 60, 65)],
         [S("PAYMENT_CARD_NUMBER", 10, 24),   # narrower
          S("DATE", 38, 50),                  # wider
          S("TIME", 62, 67)])                 # shifted
b = boundary_errors([d8])
check(b["n"] == 3 and b["narrower"] == 1 and b["wider"] == 1 and b["shifted"] == 1,
      "boundary: narrower / wider / shifted", b)
check(close(b["narrower_share"], 1 / 3), "boundary: narrower share", b["narrower_share"])
# Exact matches and other-label overlaps are not boundary errors.
d9 = doc([S("CITY", 0, 4)], [S("CITY", 0, 4), S("GIVENNAME", 1, 3)])
check(boundary_errors([d9])["n"] == 0, "boundary: exact / other-label ignored")
# PEM split in two halves: both halves are narrower.
d10 = doc([S("PRIVATE_KEY", 0, 100)], [S("PRIVATE_KEY", 0, 40), S("PRIVATE_KEY", 41, 100)])
b = boundary_errors([d10])
check(b["narrower"] == 2 and close(b["narrower_share"], 1.0), "boundary: split span is narrower x2", b)

# --- decoy triggers --------------------------------------------------------
dec = [{"start": 0, "end": 5, "resembles": "TIME", "kind": "bad_time"},
       {"start": 10, "end": 13, "resembles": "CARD_SECURITY_CODE", "kind": "cvv", "policy": True},
       {"start": 20, "end": 25, "resembles": "ZIPCODE", "kind": "zip"},
       {"start": 30, "end": 34, "resembles": "TIME", "kind": "bad_time"}]
d11 = doc([], [S("TIME", 0, 5),                   # same-label trigger
               S("CARD_SECURITY_CODE", 10, 13),   # same-label trigger on a policy decoy
               S("BUILDINGNUM", 21, 23)],         # other-label trigger
          decoys=dec)
t = decoy_triggers([d11])
check(t["overall"]["decoys"] == 4 and t["overall"]["triggered_same_label"] == 2
      and t["overall"]["triggered_any_label"] == 3, "trigger: same vs any label", t["overall"])
check(close(t["per_label"]["TIME"]["rate_same_label"], 0.5), "trigger: per resembled label",
      t["per_label"]["TIME"])
t = decoy_triggers([d11], include_policy=False)
check(t["overall"]["decoys"] == 3 and t["overall"]["triggered_same_label"] == 1,
      "trigger: policy decoys excluded", t["overall"])
nop = drop_policy_predictions([d11])[0]
check(len(nop["pred"]) == 2 and all(p["label"] != "CARD_SECURITY_CODE" for p in nop["pred"]),
      "policy bucket: predictions on policy decoys dropped", nop["pred"])

# --- document rates --------------------------------------------------------
docs = [doc([], []), doc([], [S("AGE", 0, 2)]), doc([S("CITY", 0, 4)], [S("CITY", 0, 4)]),
        doc([S("CITY", 0, 4)], [])]
r = document_rates(docs)
check(r["pii_free_documents"] == 2 and r["pii_free_with_fp"] == 1 and close(r["pii_free_fp_rate"], 0.5),
      "doc rates: PII-free FP rate", r)
check(r["perfect_documents"] == 2 and close(r["perfect_rate"], 0.5),
      "doc rates: perfect = empty/empty and exact match", r)

# --- slices and calibration ------------------------------------------------
sl = slices([doc([S("CITY", 0, 4)], [S("CITY", 0, 4)], meta={"format": "csv"}),
             doc([S("CITY", 0, 4)], [], meta={"format": "json"})])
check(close(sl["doc"]["format"]["csv"]["exact"]["f1"], 1.0)
      and close(sl["doc"]["format"]["json"]["exact"]["recall"], 0.0),
      "slices: by format", sl["doc"].get("format"))
check(sl["doc"]["density"]["1"]["documents"] == 2, "slices: density from gold count",
      sl["doc"].get("density"))

# --- D-9: the suffix is inside the gold span --------------------------------
# Text "Bakıda yaşayır": gold CITY = "Bakıda" (0-6). A stem-only prediction
# "Bakı" (0-4) is an overlap hit but an exact miss, and a partial.
text = "Bakıda yaşayır"
gold = {"label": "CITY", "start": 0, "end": 6, "case": "loc"}
check(text[gold["start"]:gold["end"]] == "Bakıda", "D-9 fixture: gold covers stem + suffix")
stem = doc([gold], [S("CITY", 0, 4)], meta={"family": "suffixed_entities"}, text=text)
full = doc([{**gold}], [S("CITY", 0, 6)], meta={"family": "suffixed_entities"}, text=text)
ex = exact_scores([stem])["micro"]
check(ex["tp"] == 0 and ex["fp"] == 1 and ex["fn"] == 1, "D-9: stem-only is an exact miss", ex)
check(close(overlap_scores([stem])["micro"]["recall"], 1.0), "D-9: stem-only is an overlap hit")
gr = gold_recall([(gold, stem["pred"])])
check(gr["exact_recall"] == 0.0 and gr["overlap_recall"] == 1.0 and gr["partial"] == 1
      and gr["per_label"]["CITY"]["partial"] == 1, "D-9: gold_recall exact 0 / overlap 1", gr)
check(close(char_leakage([stem])["rate"], 2 / 6), "D-9: the unmasked suffix leaks 2 chars")
check(boundary_errors([stem])["narrower"] == 1, "D-9: stem-only is a narrower boundary error")
# Sliced by an entity field (`case`) and by a record field (`family`).
sl = slices([stem, full])
loc = sl["entity"]["case"]["loc"]
check(loc["gold"] == 2 and close(loc["exact_recall"], 0.5) and close(loc["overlap_recall"], 1.0),
      "slices: entity-level `case` exact vs overlap recall", loc)
check(close(loc["per_label"]["CITY"]["exact_recall"], 0.5), "slices: per-label inside a slice", loc)
fam = sl["doc"]["family"]["suffixed_entities"]
check(fam["documents"] == 2 and close(fam["recall"]["exact_recall"], 0.5)
      and close(fam["recall"]["overlap_recall"], 1.0) and fam["recall"]["partial"] == 1,
      "slices: doc-level `family` exact vs overlap recall", fam)
# Identifier-like fields (one value per doc, > MAX_SLICE_VALUES) are not slices...
many = [doc([], [], meta={"template_id": f"t{i}"}) for i in range(60)]
check("template_id" not in slices(many)["doc"], "slices: id-like field skipped")
# ...unless asked for explicitly.
check("template_id" in slices(many, ["template_id"])["doc"], "slices: forced key kept")
cal = calibration([doc([S("CITY", 0, 4)], [S("CITY", 0, 4, 0.95), S("AGE", 5, 7, 0.97),
                                            S("TIME", 8, 9, 0.15), S("DATE", 9, 10)])])
check(cal["bins"][9]["n"] == 2 and close(cal["bins"][9]["precision"], 0.5)
      and cal["bins"][1]["n"] == 1 and cal["unscored_predictions"] == 1, "calibration: bins", cal)

# --- appendix replay -------------------------------------------------------
rec = {"data_id": "bench_az_x", "entries": [
    {"kind": "gold", "label": "DATE", "start": 0, "end": 10, "error_class": "missed"},
    {"kind": "gold", "label": "IBAN", "start": 20, "end": 48, "error_class": "boundary_error"},
    {"kind": "pred", "label": "IBAN", "start": 20, "end": 40, "error_class": "boundary_error"},
    {"kind": "pred", "label": "BUILDINGNUM", "start": 60, "end": 63, "error_class": "spurious"},
    {"kind": "hard_negative", "label": "TIME", "start": 70, "end": 75, "error_class": "same_label"},
]}
# Checkpoint-1-like predictions: every listed error reproduced.
same = appendix_replay([rec], {"bench_az_x": [S("IBAN", 20, 40), S("BUILDINGNUM", 60, 63),
                                              S("TIME", 70, 75), S("CITY", 80, 84)]})
check(same["pred_reproduced"] == 2 and same["gold_still_missed"] == 2
      and close(same["pred_reproduced_rate"], 1.0) and close(same["gold_still_missed_rate"], 1.0),
      "replay: baseline reproduces", same)
check(same["decoy_still_triggered"] == 1 and same["decoy_still_triggered_same_label"] == 1,
      "replay: decoy still triggered", same)
check(same["new_pred_unjudgeable"] == 1, "replay: unlisted prediction is unjudgeable, not FP", same)
# A better checkpoint: DATE found, IBAN fixed, spurious gone, decoy cleared.
fixed = appendix_replay([rec], {"bench_az_x": [S("DATE", 0, 10), S("IBAN", 20, 48)]})
check(fixed["gold_fixed"] == 2 and fixed["pred_removed"] == 2 and fixed["decoy_cleared"] == 1,
      "replay: fixes counted", fixed)
check(fixed["by_error_class"]["boundary_error"] == {"gold_fixed": 1, "pred_removed": 1},
      "replay: by error class", fixed["by_error_class"])
check(fixed.get("new_pred_unjudgeable", 0) == 0, "replay: exact gold hit is not unjudgeable", fixed)
# A new prediction overlapping a listed item is counted apart from unjudgeable.
part = appendix_replay([rec], {"bench_az_x": [S("DATE", 0, 8)]})
check(part["new_pred_overlapping_listed"] == 1 and part.get("new_pred_unjudgeable", 0) == 0,
      "replay: overlap with listed is not unjudgeable", part)


# --- RC9: split spans and ordinary-word controls ----------------------------
# "Fidan." -- gold GIVENNAME "Fidan" (0-5), prediction only "dan" (2-5).
text = "Fidan."
g = {"label": "GIVENNAME", "start": 0, "end": 5, "family": "bare_name"}
check(text[2:5] == "dan", "RC9 fixture: prediction covers 'dan'")
fidan = doc([g], [S("GIVENNAME", 2, 5)], meta={"family": "bare_name"}, text=text)
gr = gold_recall([(g, fidan["pred"])])
check(gr["split"] == 1 and gr["missed"] == 0 and gr["exact_hits"] == 0
      and gr["exact_recall"] == 0.0, "RC9: 'dan' of 'Fidan' = 1 split, not recall, not a miss", gr)
check(gr["per_label"]["GIVENNAME"]["split"] == 1, "RC9: split counted per label")
check(gold_outcome(g, fidan["pred"]) == "split", "RC9: gold_outcome split")
# Fragments that cover the whole value ("Fi" + "dan") are still split.
check(gold_outcome(g, [S("GIVENNAME", 0, 2), S("GIVENNAME", 2, 5)]) == "split",
      "outcome: full coverage in fragments is split")
# One wider same-label span covers it all: not split, nothing leaks.
check(gold_outcome(g, [S("GIVENNAME", 0, 6)]) == "covered_inexact", "outcome: wider is covered_inexact")
check(gold_outcome(g, [S("CITY", 0, 5)]) == "wrong_label", "outcome: other label only")
check(gold_outcome(g, []) == "missed", "outcome: nothing touches it = full miss")
check(gold_outcome(g, [S("GIVENNAME", 0, 5)]) == "exact", "outcome: exact")
miss = doc([g], [], meta={"family": "bare_name"}, text=text)
bn = slices([fidan, miss])["doc"]["family"]["bare_name"]["recall"]
check(bn["split"] == 1 and bn["missed"] == 1 and close(bn["split_rate"], 0.5),
      "RC9: split and full miss counted apart per slice", bn)

# Ordinary-word controls (no gold): a record marked `control`, and a span in
# `controls`. No prediction -> 0 FP; any prediction on it -> masked.
ctl_rec = {**doc([], [], meta={"family": "name_homographs", "resembles": "GIVENNAME"},
                 text="Dəniz sakit idi."), "control": True}
check(control_fp([ctl_rec])["record_fp_rate"] == 0.0
      and control_fp([ctl_rec])["records_masked"] == 0, "control: no prediction = 0 FP")
ctl_hit = {**ctl_rec, "pred": [S("GIVENNAME", 0, 5)]}
c = control_fp([ctl_rec, ctl_hit])
check(c["records"] == 2 and c["records_masked"] == 1 and close(c["record_fp_rate"], 0.5)
      and c["per_label"]["GIVENNAME"]["records_masked"] == 1, "control: record FP rate", c)
span_doc = {**doc([S("GIVENNAME", 0, 5)], [S("GIVENNAME", 0, 5), S("GIVENNAME", 20, 25)],
                  meta={"family": "name_homographs"}),
            "controls": [{"start": 20, "end": 25, "resembles": "GIVENNAME", "word": "noun"},
                         {"start": 30, "end": 35, "resembles": "GIVENNAME", "word": "noun"}]}
c = control_fp([span_doc])
check(c["spans"] == 2 and c["spans_masked"] == 1 and close(c["span_fp_rate"], 0.5),
      "control: span FP rate, any label", c)
check(c["records"] == 0, "control: an unmarked record is not a control record")
sl = slices([ctl_rec, ctl_hit, span_doc])
fam = sl["doc"]["family"]["name_homographs"]["controls"]
check(fam["records"] == 2 and fam["records_masked"] == 1 and fam["spans_masked"] == 1,
      "control: per doc slice", fam)
check(close(sl["control"]["word"]["noun"]["span_fp_rate"], 0.5), "control: per control-span slice",
      sl["control"])
# Decoys declared as homograph nouns (`_decoys` kind) get a per-kind rate.
hd = doc([], [S("GIVENNAME", 0, 5)], decoys=[
    {"start": 0, "end": 5, "resembles": "GIVENNAME", "kind": "homograph_noun"},
    {"start": 10, "end": 15, "resembles": "GIVENNAME", "kind": "homograph_noun"}])
check(close(decoy_triggers([hd])["per_kind"]["homograph_noun"]["rate_any_label"], 0.5),
      "decoys: per-kind trigger rate")


# --- "new names": recall on values seen in training vs never seen -----------
train = [{"text": "Əli Nizami küçəsində yaşayır.",
          "entities": [{"label": "GIVENNAME", "start": 0, "end": 3},
                       {"label": "STREET", "start": 4, "end": 20}]},
         {"text": "Bakı", "entities": [{"label": "CITY", "start": 0, "end": 4}]}]
seen = seen_values(train)
check(seen["GIVENNAME"] == {"Əli"} and seen["STREET"] == {"Nizami küçəsində"}
      and seen["SURNAME"] == set() and "CITY" not in seen, "new names: seen values by label", seen)
t = "Əli və Fuad Nizami küçəsinə gəldi."
check(t[7:11] == "Fuad" and t[12:27] == "Nizami küçəsinə", "new names fixture")
nd = doc([S("GIVENNAME", 0, 3), S("GIVENNAME", 7, 11), S("STREET", 12, 27)],
         [S("GIVENNAME", 0, 3), S("STREET", 12, 27)], text=t)
nn = new_name_recall([nd], seen)
check(nn["GIVENNAME"]["seen"]["gold"] == 1 and close(nn["GIVENNAME"]["seen"]["exact_recall"], 1.0),
      "new names: seen GIVENNAME found", nn["GIVENNAME"])
check(nn["GIVENNAME"]["new"]["gold"] == 1 and close(nn["GIVENNAME"]["new"]["exact_recall"], 0.0),
      "new names: unseen GIVENNAME missed", nn["GIVENNAME"])
# A differently inflected form of a seen street is a different exact value (D-9).
check(nn["STREET"]["new"]["gold"] == 1 and nn["STREET"]["seen"]["gold"] == 0,
      "new names: other suffix = new value", nn["STREET"])
check(nn["ALL"]["seen"]["gold"] == 1 and nn["ALL"]["new"]["gold"] == 2
      and close(nn["ALL"]["new"]["exact_recall"], 0.5), "new names: ALL buckets", nn["ALL"])
check(nn["SURNAME"]["seen"]["gold"] == 0 and nn["SURNAME"]["new"]["exact_recall"] is None,
      "new names: empty label bucket is None, not 0")


# --- probes: confusion and targets (P3-3) -------------------------------------
from metrics import baseline_values, confusion_matrix, evaluate_target, score_docs  # noqa: E402

tok_docs = [doc([S("ACCESS_TOKEN", 0, 30)], [S("API_KEY", 0, 30)]),
            doc([S("ACCESS_TOKEN", 0, 30)], [S("ACCESS_TOKEN", 0, 30)]),
            doc([S("API_KEY", 0, 30)], [S("API_KEY", 0, 30)])]
cm = confusion_matrix(tok_docs)
check(cm["ACCESS_TOKEN"] == {"gold": 2, "API_KEY": 1} and cm["API_KEY"] == {"gold": 1},
      "confusion: token read as key counted once", cm)
sc = score_docs(tok_docs)
tgt = {"conditions": [{"metric": "exact_recall", "labels": ["ACCESS_TOKEN"], "op": ">=", "value": 0.8},
                      {"metric": "confusion_rate", "from": "ACCESS_TOKEN", "to": ["API_KEY"], "op": "<", "value": 0.1}]}
ev = evaluate_target(tgt, sc, cm)
check(ev["conditions"][0]["measured"] == 0.5 and ev["conditions"][1]["measured"] == 0.5
      and ev["pass"] is False and ev["shows_failure_at_ckpt1"] is True, "target: absolute conditions", ev)
ok = evaluate_target({"conditions": [{"metric": "exact_f1", "op": ">=", "value": 0.6}]}, sc, cm)
check(ok["pass"] is True and ok["shows_failure_at_ckpt1"] is False and close(ok["conditions"][0]["measured"], 2 / 3),
      "target: exact_f1, a passing probe does not show the failure", ok)
# relative target: needs the checkpoint-1 value, and a sanity condition decides "shows the failure"
ctl_docs = [{**doc([], [S("BUILDINGNUM", 5, 8)]), "controls": [{"start": 5, "end": 8, "resembles": "BUILDINGNUM"}]},
            {**doc([], []), "controls": [{"start": 5, "end": 8, "resembles": "BUILDINGNUM"}]}]
rel = {"conditions": [{"metric": "control_fp_rate", "op": "<=", "relative": 0.3}],
       "sanity": [{"metric": "control_fp_rate", "op": ">=", "value": 0.1}]}
cs = score_docs(ctl_docs)
e1 = evaluate_target(rel, cs, {})
check(e1["pass"] is None and e1["conditions"][0]["note"] and e1["shows_failure_at_ckpt1"] is True,
      "target: relative without a baseline is not judged; sanity shows the failure", e1)
base = baseline_values(rel, cs, {})
better = score_docs([{**d, "pred": []} for d in ctl_docs])
e2 = evaluate_target(rel, better, {}, base)
check(close(base["control_fp_rate:"], 0.5) and e2["pass"] is True and close(e2["conditions"][0]["threshold"], 0.15),
      "target: relative with a baseline (-70%)", e2)


# --- scoreboard: benchmark_v3 look-alikes as decoys, interim gate column (P4-6) --
import scoreboard  # noqa: E402

bt = "AA12 kodu, AA123 deyil; 12:345 və 12:345 və 0501234567"
brec = {"id": "b1", "text": bt, "entities": [S("PHONE_NUMBER", 44, 54)],
        "_spec": {"hard_negatives": ["AA12", "12:345", "0501234567", "yox"],
                  "hard_negative_labels": ["AZ_ID_CARD_NUMBER", "TIME", "PHONE_NUMBER", "TIME"]}}
bd = scoreboard._normalise(brec)["decoys"]
check([(d["start"], d["end"], d["resembles"], d["kind"]) for d in bd]
      == [(0, 4, "AZ_ID_CARD_NUMBER", "benchmark_ambiguous"), (24, 30, "TIME", "benchmark_ambiguous")],
      "benchmark decoys: whole-word first, gold-overlapping and absent values dropped", bd)
check(bt[bd[0]["start"]:bd[0]["end"]] == "AA12" and bt[bd[1]["start"]:bd[1]["end"]] == "12:345",
      "benchmark decoys: offsets land on the value")
check(scoreboard._normalise({"id": "x", "text": "t", "entities": []})["decoys"] == [],
      "records without _spec get no decoys")
bres = {"benchmark": {"tracks": {"R": {"all": score_docs([{**doc([S("TIME", 0, 4)], [S("TIME", 0, 4)]),
                                                         "decoys": [{"start": 5, "end": 9, "resembles": "TIME"}]}])}}}}
grows = {r["gate"]: r for r in scoreboard.gates(bres, None)}
check(close(grows["micro_f1"]["interim"], 1.0) and grows["micro_f1"]["value"] is None
      and grows["micro_f1"]["sprint1_pass"] is None and grows["hard_negative_trigger_rate"]["interim"] == 0.0,
      "gates: benchmark fills the interim column only, never a pass/fail", grows["micro_f1"])


# --- D-34c: exclude_kinds keeps policy items out of the C4 trigger rate -------------
from metrics import _target_metric as _tm  # noqa: E402
xs = {"decoys": {"overall": {"decoys": 10, "triggered_same_label": 6, "triggered_any_label": 7,
                             "rate_same_label": 0.6, "rate_any_label": 0.7},
                 "per_kind": {"policy_d34c": {"decoys": 2, "triggered_same_label": 2, "triggered_any_label": 2},
                              "invalid_shape": {"decoys": 8, "triggered_same_label": 4, "triggered_any_label": 5}}},
      "recall": {"per_label": {}, "gold": 0}}
c_ex = {"metric": "decoy_trigger_rate", "op": "<", "value": 0.15, "exclude_kinds": ["policy_d34c"]}
check(close(_tm(c_ex, xs, {}), 4 / 8), "exclude_kinds: 4 of the 8 non-policy look-alikes", _tm(c_ex, xs, {}))
check(close(_tm({**c_ex, "metric": "decoy_trigger_rate_any"}, xs, {}), 5 / 8), "exclude_kinds: any-label rate")
check(close(_tm({"metric": "decoy_trigger_rate", "op": "<", "value": 0.15}, xs, {}), 0.6),
      "without exclude_kinds: unchanged (all 10 look-alikes)")
check(close(_tm({**c_ex, "exclude_kinds": ["no_such_kind"]}, xs, {}), 0.6), "exclude_kinds: unknown kind changes nothing")

# --- D-41c: exclude_kinds takes PII-free documents holding a policy item out of the count ---
dd = [{"gold": [], "pred": [{"label": "CARD_SECURITY_CODE", "start": 5, "end": 9}],
       "decoys": [{"start": 5, "end": 9, "resembles": "CARD_SECURITY_CODE", "kind": "policy_d39c", "policy": True}]},
      {"gold": [], "pred": [], "decoys": [{"start": 0, "end": 4, "resembles": "CARD_SECURITY_CODE", "kind": "policy_d39c", "policy": True}]},
      {"gold": [], "pred": [{"label": "DATE", "start": 0, "end": 4}], "decoys": []},
      {"gold": [], "pred": [], "decoys": [{"start": 0, "end": 4, "resembles": "AZ_FIN", "kind": "d2_dummy", "policy": True}]},
      {"gold": [{"label": "DATE", "start": 0, "end": 4}], "pred": [], "decoys": []}]
from metrics import document_rates  # noqa: E402
dr = document_rates(dd)
check(dr["pii_free_documents"] == 4 and dr["pii_free_with_fp"] == 2, "document_rates: 4 PII-free, 2 with a prediction", dr)
check(dr["pii_free_policy_kinds"] == {"policy_d39c": {"documents": 2, "with_fp": 1}, "d2_dummy": {"documents": 1, "with_fp": 0}},
      "document_rates: PII-free documents by policy kind", dr["pii_free_policy_kinds"])
sc = {"documents": dr, "recall": {"per_label": {}, "gold": 0}}
c_pf = {"metric": "pii_free_fp_rate", "op": "<", "value": 0.15}
check(close(_tm(c_pf, sc, {}), 0.5), "pii_free_fp_rate without exclude_kinds: 2 of 4")
check(close(_tm({**c_pf, "exclude_kinds": ["policy_d39c"]}, sc, {}), 0.5), "exclude_kinds policy_d39c: 1 of 2 left")
check(close(_tm({**c_pf, "exclude_kinds": ["policy_d39c", "d2_dummy"]}, sc, {}), 1.0), "two kinds: 1 of 1 left")
check(_tm({**c_pf, "exclude_kinds": ["no_such_kind"]}, sc, {}) == 0.5, "unknown kind changes nothing")


if __name__ == "__main__":
    print(f"{PASS} passed, {FAIL} failed")
    for f in FAILURES:
        print("  FAIL", f)
    sys.exit(1 if FAIL else 0)
