"""Tests for eval/bug_check.py (D-44b) and the decoy_cvv split by kind (D-44).

Run:  python eval/test_bug_check.py
Synthetic reports and a fake tokenizer only.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bug_check as B  # noqa: E402
import scoreboard as S  # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond, name, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(f"{name}: {detail}" if detail is not None else name)


def lab(tp, fn, fp=0):
    r = tp / (tp + fn) if tp + fn else 0.0
    p = tp / (tp + fp) if tp + fp else 0.0
    return {"tp": tp, "fn": fn, "fp": fp, "recall": r, "precision": p, "f1": 2 * p * r / (p + r) if p + r else 0.0}


def rep(labels, f1=None):
    tp = sum(v["tp"] for v in labels.values()); fn = sum(v["fn"] for v in labels.values())
    micro = {**lab(tp, fn), "tp": tp, "fn": fn}
    if f1 is not None:
        micro["f1"] = f1
    blk = {"all": {"exact": {"micro": micro, "per_label": labels}}}
    return {"sets": {"benchmark": {"tracks": {"R": blk}}, "probes": {"tracks": {"R": blk}}}}


ref = rep({"EMAIL": lab(95, 5), "ACCESS_TOKEN": lab(90, 10), "ZIPCODE": lab(50, 50)}, f1=0.889)
flags, info = B.label_checks(rep({"EMAIL": lab(94, 6), "ACCESS_TOKEN": lab(85, 15), "ZIPCODE": lab(45, 55)}, f1=0.86), ref)
check(flags == [], "a healthy checkpoint: no flag", flags)
flags, _ = B.label_checks(rep({"EMAIL": lab(94, 6), "ACCESS_TOKEN": lab(0, 100), "ZIPCODE": lab(45, 55)}, f1=0.86), ref)
check(any("ACCESS_TOKEN near 0" in f for f in flags), "a label near 0 is flagged", flags)
check(any("ACCESS_TOKEN F1" in f and "below Run B" in f for f in flags), "and far below Run B", flags)
flags, _ = B.label_checks(rep({"EMAIL": lab(94, 6), "ACCESS_TOKEN": lab(1, 9), "ZIPCODE": lab(45, 55)}, f1=0.86), ref)
check(not any("ACCESS_TOKEN near 0" in f for f in flags), "fewer than 20 gold values: never 'near 0'", flags)
flags, _ = B.label_checks(rep({"EMAIL": lab(94, 6), "ACCESS_TOKEN": lab(85, 15), "ZIPCODE": lab(45, 55)}, f1=0.70), ref)
check(any("benchmark micro F1 70.0" in f for f in flags), "benchmark more than 10 points below Run B", flags)
flags, _ = B.label_checks({"sets": {}}, ref)
check(flags == ["benchmark: not scored", "probes: not scored"], "missing sets are reported", flags)

good = {0: "O", 1: "B-EMAIL", 2: "I-EMAIL", 3: "B-ZIPCODE", 4: "I-ZIPCODE"}
f, ents = B.label_map_checks(good, dict(good))
check(f == [] and ents == ["EMAIL", "ZIPCODE"], "the same label map: no flag", f)
f, _ = B.label_map_checks({0: "O", 1: "B-EMAIL", 2: "I-EMAIL", 3: "B-ZIPCODE"}, good)
check(any("ZIPCODE lacks" in x for x in f) and any("differs from Run B" in x for x in f), "a missing I- tag and a different map", f)
f, _ = B.label_map_checks({0: "O", 1: "B-EMAIL", 2: "I-EMAIL", 3: "LABEL_3", 4: "I-ZIPCODE"}, None)
check(any("outside the BIO scheme: LABEL_3" in x for x in f), "a generic LABEL_n tag (lost label map)", f)
f, _ = B.label_map_checks({0: "O", 1: "I-EMAIL", 2: "B-EMAIL", 3: "B-ZIPCODE", 4: "I-ZIPCODE"}, good)
check(any("different ids" in x for x in f), "same tags, different ids", f)


class Tok:  # a whitespace "tokenizer" with offsets
    def __init__(self, shift=0, size=100):
        self.shift, self.size = shift, size

    def __len__(self):
        return self.size

    def __call__(self, text, return_offsets_mapping=False, add_special_tokens=True):
        offs, i = [], 0
        for w in text.split(" "):
            offs.append((i, i + len(w)))
            i += len(w) + 1
        out = {"input_ids": [hash(text[a:b]) % 1000 + self.shift for a, b in offs]}
        if return_offsets_mapping:
            out["offset_mapping"] = offs
        return out


check(B.tokenizer_checks(Tok(), Tok()) == [], "the same tokenizer: no flag")
f = B.tokenizer_checks(Tok(shift=1, size=101), Tok())
check(len(f) == 2, "a different vocabulary and different ids are flagged", f)

texts = {"benchmark": {"d1": "abcdefghij"}}
f, n = B.prediction_checks(texts, {"benchmark.R": {"d1": [{"label": "EMAIL", "start": 0, "end": 3},
                                                          {"label": "EMAIL", "start": 5, "end": 12},
                                                          {"label": "LABEL_7", "start": 1, "end": 2}]}}, {"EMAIL"})
check(n == 3 and any("1 of 3 with impossible offsets" in x for x in f) and any("LABEL_7" in x for x in f),
      "bad offsets and unknown labels are flagged", f)

# a long document: 600 one-letter "tokens"; gold values before and after the 510th token
text = " ".join("x" for _ in range(600))
gold = [{"label": "EMAIL", "start": 2 * i, "end": 2 * i + 1} for i in range(0, 600, 10)]
docs = [{"id": "d", "text": text, "gold": gold}]
cut_found = {"d": [{"label": g["label"], "start": g["start"], "end": g["end"]} for g in gold if g["start"] < 2 * 510]}
f, w = B.window_check(docs * 1, cut_found, Tok())
check(w["values_after_window"] == 9 and w["recall_after_window"] == 0.0, "values after the window counted", w)
check(f == [], "fewer than 30 values after the window: no flag", f)
f, w = B.window_check(docs * 4, cut_found, Tok())
check(any("tokenizers 0.23 pattern" in x for x in f), "after-window values all missed: flagged (D-37)", f)
all_found = {"d": [{"label": g["label"], "start": g["start"], "end": g["end"]} for g in gold]}
f, _ = B.window_check(docs * 4, all_found, Tok())
check(f == [], "all found: no flag", f)

res = {"meta": {"model": "m/x", "revision": "epoch1abcdef", "code": "c", "date_utc": "d"}, "flags": [], "info": {}}
md = B.render_md(res)
check("No clear bug found" in md and "Not a release verdict" in md, "report without flags says so and is not a verdict")
check("possible bug" in B.render_md({**res, "flags": ["x"]}), "report with flags lists them")

# decoy_cvv split by kind in the scoreboard's probe report (D-44)
report = {"sets": {"probes": {"tracks": {"R": {
    "targets": {"decoy_cvv": {"conditions": [{"metric": "decoy_trigger_rate", "op": "<", "value": 0.15, "threshold": 0.15,
                                              "measured": 1.0, "pass": False}], "sanity": [], "shows_failure_at_ckpt1": True, "pass": False}},
    "per_family": {"decoy_cvv": {"documents": {"documents": 24}, "decoys": {"per_kind": {
        "d2_dummy": {"decoys": 2, "triggered_same_label": 2}, "invalid_shape": {"decoys": 5, "triggered_same_label": 4},
        "policy_d39c": {"decoys": 3, "triggered_same_label": 0}}}}}}}}}}
line = "\n".join(S._render_probe_targets(report))
check("`12345` dummies (D-2) 2/2" in line and "random 5-digit codes 4/5" in line and "dashed, policy (D-39c) 0/3" in line,
      "probe report lists 12345 apart from the random 5-digit codes", line[-200:])

if __name__ == "__main__":
    print(f"{PASS} passed, {FAIL} failed")
    for f in FAILURES:
        print("  FAIL", f)
    sys.exit(1 if FAIL else 0)
