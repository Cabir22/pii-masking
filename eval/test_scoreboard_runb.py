"""Tests for the scoreboard's runb_test set (Run B's test split, old/new parts).

Run:  python eval/test_scoreboard_runb.py

Synthetic records written for this test; no model, corpus or shadow text.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

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


def rec(i, text, ents=()):
    return {"id": i, "text": text, "lang": "az", "_source": "llm",
            "entities": [{"start": s, "end": e, "label": l, "text": text[s:e]} for s, e, l in ents]}


V2 = [rec("repaired.clean__a", "Zəng: Orxan", [(6, 11, "GIVENNAME")]),   # same id+text as v1 -> old; old corpus
      rec("runb_targeted__b", "Şəhər: Quba", [(7, 11, "CITY")]),        # text changed -> new; new data
      rec("sprint1_llm_b5.clean__c", "Heç nə yoxdur."),                # only in v2, PII-free -> new
      rec("negatives.clean__d", "Tarix yoxdur.")]                      # same id+text, PII-free -> old
V2[0]["_old"] = V2[3]["_old"] = True
V1 = [rec("repaired.clean__a", "Zəng: Orxan", [(6, 11, "GIVENNAME")]),
      rec("runb_targeted__b", "Şəhər: Bakı", [(7, 11, "CITY")]),
      rec("negatives.clean__d", "Tarix yoxdur."),
      rec("z", "Yalnız v1-də.")]

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    for name, rows in (("v2.docs.jsonl", V2), ("v1.docs.jsonl", V1)):
        (td / name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    args = argparse.Namespace(private_dir=str(td / "none"), runb_test=str(td / "v2.docs.jsonl"),
                              runb_v1_test=str(td / "v1.docs.jsonl"))
    docs, info = S.load_set("runb_test", args)
    part = {d["id"].split("__")[1]: d["meta"].get("runb_part") for d in docs}
    check(part == {"a": "old", "b": "new", "c": "new", "d": "old"}, "old = same id and same text as v1", part)
    origin = {d["id"].split("__")[1]: d["meta"].get("runb_origin") for d in docs}
    check(origin == {"a": "old_corpus", "b": "new_data", "c": "new_data", "d": "old_corpus"},
          "origin by id prefix", origin)
    check(info["origins"] == {"old_corpus": 2, "new_data": 2, "disagree_with__old": 0},
          "origin counts agree with _old", info.get("origins"))
    check(info["parts"] == {"old": 2, "new": 2}, "part counts in info", info.get("parts"))
    check(len(info["file_sha256"]) == 64 and len(info["v1_file_sha256"]) == 64, "both files' SHA-256 recorded")
    check(all("text" not in g for d in docs for g in d["gold"]), "entity text never carried into gold")

    # Predictions: a correct, b wrong label, c one false positive, d nothing.
    preds = {"repaired.clean__a": [{"start": 6, "end": 11, "label": "GIVENNAME"}],
             "runb_targeted__b": [{"start": 7, "end": 11, "label": "STREET"}],
             "sprint1_llm_b5.clean__c": [{"start": 0, "end": 3, "label": "GIVENNAME"}],
             "negatives.clean__d": []}
    out = S.score_set("runb_test", docs, preds)
    bp = out.get("by_part", {})
    check(sorted(bp) == ["new", "old"], "by_part has old and new", sorted(bp))
    old, new = bp["old"], bp["new"]
    check(old["exact"]["micro"]["f1"] == 1.0 and old["documents"]["documents"] == 2, "old: perfect, 2 docs")
    check(old["documents"]["pii_free_fp_rate"] == 0.0, "old: PII-free doc d not masked")
    check(new["exact"]["micro"]["tp"] == 0 and new["exact"]["micro"]["fp"] == 2, "new: 0 TP, 2 FP", new["exact"]["micro"])
    check(new["documents"]["pii_free_fp_rate"] == 1.0, "new: PII-free doc c masked")
    check(new["exact"]["per_label"]["CITY"]["fn"] == 1, "new: per-label counts", new["exact"]["per_label"])
    bo = out.get("by_origin", {})
    check(sorted(bo) == ["new_data", "old_corpus"], "by_origin has both origins", sorted(bo))
    check(bo["old_corpus"]["exact"]["micro"]["f1"] == 1.0 and bo["new_data"]["exact"]["micro"]["fp"] == 2,
          "by_origin scores each group")
    check(out["all"]["exact"]["micro"]["tp"] == 1 and out["all"]["documents"]["pii_free_documents"] == 2,
          "overall block covers all four documents")

    report = {"meta": {}, "sets": {"runb_test": {"info": info, "tracks": {"R": out}}}}
    md = "\n".join(S._render_runb_parts(report))
    check("## Run B test split by part (track R)" in md and "| old | 2 |" in md and "| new | 2 |" in md
          and "| old_corpus | 2 |" in md and "| new_data | 2 |" in md,
          "markdown: part table", md[:300])
    check("| CITY |" in md and "| GIVENNAME |" in md, "markdown: per-label table")
    check("Orxan" not in md and "Quba" not in md, "markdown: no document text")

    # Without --runb-v1-test there are no parts and no by_part block.
    args.runb_v1_test = None
    docs2, info2 = S.load_set("runb_test", args)
    out2 = S.score_set("runb_test", docs2, preds)
    check("parts" not in info2 and "by_part" not in out2, "no v1: no parts")
    check("by_origin" in out2, "no v1: origin split still there")
    check("runb_test" not in S.PUBLIC_SETS + S.PRIVATE_SETS, "runb_test is scored only when named")

    # Saved id list instead of the v1 file: same parts; changed text or unknown id -> "unlisted".
    import gzip
    pf = td / "parts.tsv.gz"
    with gzip.open(pf, "wt", encoding="utf-8") as fh:
        fh.write("# test\nid\tpart\torigin\ttext_sha1_16\n")
        for d in docs:
            if not d["id"].endswith("__d"):  # d left out on purpose
                fh.write(f"{d['id']}\t{d['meta']['runb_part']}\t{d['meta']['runb_origin']}\t{S._text_hash(d['text'])}\n")
    args.runb_v1_test, args.runb_parts = None, str(pf)
    docs3, info3 = S.load_set("runb_test", args)
    part3 = {d["id"].split("__")[1]: d["meta"].get("runb_part") for d in docs3}
    check(part3 == {"a": "old", "b": "new", "c": "new", "d": "unlisted"}, "parts from the saved list", part3)
    check(info3["parts"] == {"old": 1, "new": 2, "unlisted": 1}, "parts file counts", info3.get("parts"))
    args.runb_parts = str(td / "missing.tsv.gz")
    check("parts" not in S.load_set("runb_test", args)[1], "missing parts file: no parts")

    # The committed list: 15,835 v2 test ids, 9,410 old / 6,425 new, origins as by prefix.
    saved = S.read_runb_parts(S.RUNB_PARTS)
    from collections import Counter
    check(len(saved) == 15835 and Counter(p for p, _ in saved.values()) == {"old": 9410, "new": 6425},
          "committed parts file: counts", (len(saved), Counter(p for p, _ in saved.values())))
    with gzip.open(S.RUNB_PARTS, "rt", encoding="utf-8") as fh:
        rows = [l.rstrip("\n").split("\t") for l in fh if not l.startswith(("#", "id\t"))]
    check(all((r[2] == "old_corpus") == r[0].startswith(S.RUNB_OLD_PREFIXES) for r in rows)
          and Counter(r[2] for r in rows) == {"old_corpus": 8935, "new_data": 6900}, "committed parts file: origins")


if __name__ == "__main__":
    print(f"{PASS} passed, {FAIL} failed")
    for f in FAILURES:
        print("  FAIL", f)
    sys.exit(1 if FAIL else 0)
