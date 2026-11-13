"""Tests for the multilingual mode (D-46): A7 and A10 in eval/release_check.py, the real_text_<lang>
sets in eval/scoreboard.py and the merged barrier files in eval/leakage_guard.py.

Run:  python eval/test_multilingual.py
Synthetic data only.
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import leakage_guard as LG  # noqa: E402
import release_check as RC  # noqa: E402
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


def blk(f1, labels=None):
    return {"all": {"exact": {"micro": {"f1": f1}, "per_label": labels or {}}}}


def rep(**sets):
    return {"sets": {k: {"tracks": {"R": v}} for k, v in sets.items()}}


base = rep(golden_en=blk(0.964), lang_tr=blk(0.884), lang_ru=blk(0.884))
good = rep(golden_en=blk(0.96), lang_tr=blk(0.88), lang_ru=blk(0.90))
r = RC.a7_rule(good, base, None, None)
check(r["status"] == "pass" and r["blocking"], "A7: within 1 point on every translated set passes", r)
check(r["result"].count("no independent set yet: translated only") == 3, "A7 says it blocks on the translated sets only", r["result"])
r = RC.a7_rule(rep(golden_en=blk(0.96), lang_tr=blk(0.86), lang_ru=blk(0.90)), base, None, None)
check(r["status"] == "fail" and "TR: translated 88.4 → 86.0 FAIL" in r["result"], "A7: TR 2.4 points lower fails", r["result"])
rn, rb = rep(real_text_tr=blk(0.60)), rep(real_text_tr=blk(0.70))
r = RC.a7_rule(good, base, rn, rb)
check(r["status"] == "fail" and "independent 70.0 → 60.0 FAIL" in r["result"], "A7 blocks on the independent set too (D-46b)", r["result"])
check("EN: translated 96.4 → 96.0, no independent set yet" in r["result"], "other languages still say translated only", r["result"])
r = RC.a7_rule(rep(golden_en=blk(0.96)), base, None, None)
check(r["status"] == "not scored", "A7: a missing translated set is not scored", r)


def lab(tp, fn):
    return {"tp": tp, "fn": fn, "recall": tp / (tp + fn)}


v3 = {"sets": {"shadow_dev": {"tracks": {"R": blk(0.9, {"IBAN": lab(90, 10), "AZ_FIN": lab(95, 5)})}},
               "benchmark": {"tracks": {"R": blk(0.9, {"IBAN": lab(80, 20)})}}}}
new_ok = {"sets": {"shadow_dev": {"tracks": {"R": blk(0.9, {"IBAN": lab(90, 10), "AZ_FIN": lab(95, 5)})}},
                   "benchmark": {"tracks": {"R": blk(0.9, {"IBAN": lab(80, 20)})}}}}
new_bad = {"sets": {"shadow_dev": {"tracks": {"R": blk(0.9, {"IBAN": lab(87, 13), "AZ_FIN": lab(95, 5)})}},
                    "benchmark": {"tracks": {"R": blk(0.9, {"IBAN": lab(80, 20)})}}}}
r = RC.a10_rule(None, None, None, None)
check(r["status"] == "n/a" and not r["blocking"] and "checkpoint 1" in r["result"], "A10 without v3: n/a, the bar is checkpoint 1")
r = RC.a10_rule(new_ok, v3, new_ok, v3)
check(r["status"] == "pass" and r["blocking"], "A10: no label lower than v3 passes", r)
r = RC.a10_rule(new_bad, v3, new_ok, v3)
check(r["status"] == "fail" and "IBAN 90.0 → 87.0" in r["result"], "A10: a label 3 points below v3 fails", r["result"])
r = RC.a10_rule(new_ok, v3, None, None)
check(r["status"] == "not scored" and "benchmark not scored" in r["result"],
      "A10 needs both sets (D-46a): with shadow-dev only it is not scored", r)

# scoreboard: the independent real-text sets
check(all(f"real_text_{l}" in S.PRIVATE_SETS for l in ("en", "tr", "ru")), "real_text_en/_tr/_ru are private sets")
with tempfile.TemporaryDirectory() as tmp:
    priv = Path(tmp)
    (priv / "real_text_tr").mkdir()
    (priv / "real_text_tr" / "real_text.jsonl").write_text(json.dumps(
        {"id": "rt_tr_001", "text": "Ahmet Yılmaz Ankara'da konuştu.", "lang": "tr",
         "entities": [{"label": "GIVENNAME", "start": 0, "end": 5}, {"label": "SURNAME", "start": 6, "end": 12},
                      {"label": "CITY", "start": 13, "end": 19}]}, ensure_ascii=False) + "\n", encoding="utf-8")
    docs, info = S.load_set("real_text_tr", argparse.Namespace(private_dir=str(priv)))
    check(len(docs) == 1 and info["source"] == "private: real_text_tr/", "real_text_tr loads from its private folder", info)
    check(docs[0]["text"][docs[0]["gold"][2]["start"]:docs[0]["gold"][2]["end"]] == "Ankara", "the TR apostrophe suffix stays outside the span")
    docs, info = S.load_set("real_text_ru", argparse.Namespace(private_dir=str(priv)))
    check(docs is None and info["skipped"] == "not found", "a language without a set is skipped")

    # leakage guard: barrier files merged with the shadow hashes
    def hashes(path, grams, values):
        with gzip.open(path, "wt", encoding="utf-8") as fh:
            json.dump({"format": LG.SHADOW_FORMAT, "n": LG.N, "source": {"documents": 1}, "ngram_sha1": grams, "values": values}, fh)
        return path
    a = hashes(priv / "a.json.gz", ["g1", "g2"], [{"sha1": "v1", "anchor_sha1": "x", "offset": 0, "length": 3}])
    b = hashes(priv / "b.json.gz", ["g2", "g3"], [{"sha1": "v2", "anchor_sha1": "y", "offset": 0, "length": 3}])
    m = LG.merge_barriers([(a, LG.load_shadow(a)), (b, LG.load_shadow(b)), (priv / "none.json.gz", LG.load_shadow(priv / "none.json.gz"))])
    check(m["ngram_sha1"] == ["g1", "g2", "g3"] and [v["sha1"] for v in m["values"]] == ["v1", "v2"] and len(m["source"]) == 2,
          "barriers merge: union of hashes, a missing file ignored", m)
    check(LG.merge_barriers([(priv / "none.json.gz", LG.load_shadow(priv / "none.json.gz"))])["missing"], "no file at all: missing")
    # a training text copying an 8-gram of the barrier set is a leak
    text = "bu cümle gizli gerçek metin setinden aynen kopyalanmış uzun bir cümledir"
    g8 = [LG.sha1(x) for x in LG.ngrams(LG.words(text))][:1]
    c = hashes(priv / "c.json.gz", g8, [])
    guard = LG.Guard({}, {}, set(), set(), LG.merge_barriers([(c, LG.load_shadow(c))]))
    guard.scan("train_1", "önce " + text)
    check(not guard.clean(), "a copied 8-gram from a barrier set is caught")
check(all(p.name.startswith("leakage_guard_barrier_") for p in LG.barrier_files()), "barrier files are found by name")

# the barrier builder: names, places and dates are never value-hashed, phones and e-mails are; it says why
import build_shadow_hashes as BH  # noqa: E402
with tempfile.TemporaryDirectory() as tmp:
    f = Path(tmp) / "set.jsonl"
    t = "Mehmet Yılmaz Ankara'da 14.10.2026 tarihinde konuştu, tel. +90 312 507 10 00, e-posta mehmet.yilmaz@ankara.bel.tr"
    ents = [("GIVENNAME", "Mehmet"), ("SURNAME", "Yılmaz"), ("CITY", "Ankara"), ("DATE", "14.10.2026"),
            ("TELEPHONENUM", "+90 312 507 10 00"), ("EMAIL", "mehmet.yilmaz@ankara.bel.tr")]
    f.write_text(json.dumps({"id": "x", "text": t, "entities": [{"label": l, "start": t.index(v), "end": t.index(v) + len(v)}
                                                               for l, v in ents]}, ensure_ascii=False) + "\n", encoding="utf-8")
    d = BH.build([f])
    check(len(d["values"]) == 2 and sum(d["values_skipped"].values()) == 4,
          "builder: the phone and the e-mail hashed, the 4 names/places/dates skipped and counted", (len(d["values"]), d["values_skipped"]))
# D-48 follow-up: value hashing is decided by label, not by casing
with tempfile.TemporaryDirectory() as tmp:
    f = Path(tmp) / "caps.jsonl"
    t = "QABALA RAYON ICRA HAKIMIYYETI, rəhbər ELVIN MAMMADOV, FİN AUJAKHM, tel. +994 50 123 45 67"
    ents = [("CITY", "QABALA"), ("GIVENNAME", "ELVIN"), ("SURNAME", "MAMMADOV"), ("AZ_FIN", "AUJAKHM"),
            ("TELEPHONENUM", "+994 50 123 45 67")]
    f.write_text(json.dumps({"id": "c", "text": t, "entities": [{"label": l, "start": t.index(v), "end": t.index(v) + len(v)}
                                                               for l, v in ents]}, ensure_ascii=False) + "\n", encoding="utf-8")
    d = BH.build([f])
    hashed = {v["sha1"] for v in d["values"]}
    check(LG.sha1("QABALA") not in hashed and LG.sha1("ELVIN") not in hashed and LG.sha1("MAMMADOV") not in hashed,
          "an all-capitals CITY, GIVENNAME and SURNAME are never value-hashed", d["values_skipped"])
    check(LG.sha1("AUJAKHM") in hashed, "an all-capitals FIN (a code) is still value-hashed")
    check(LG.sha1("+994 50 123 45 67") in hashed, "a phone is still value-hashed")
    check(d["values_skipped"]["name, place or date label"] == 3, "the 3 name/place values are skipped by label", d["values_skipped"])
check({"GIVENNAME", "SURNAME", "CITY", "STREET", "BUILDINGNUM", "ZIPCODE", "DATE", "TIME", "AGE"}.isdisjoint(BH.VALUE_LABELS),
      "no name, place or date label is a value label")
for name in ("leakage_guard_barrier_real_az.json.gz", "leakage_guard_barrier_real_tr.json.gz", "leakage_guard_barrier_real_en.json.gz"):
    d = LG.load_shadow(HERE / name)
    check(not d.get("missing") and d["ngram_sha1"] and "values_skipped" in d, f"{name}: present, with 8-grams and skip counts")

if __name__ == "__main__":
    print(f"{PASS} passed, {FAIL} failed")
    for f in FAILURES:
        print("  FAIL", f)
    sys.exit(1 if FAIL else 0)
