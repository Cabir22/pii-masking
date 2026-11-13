"""Tests for D-42: the private policy list (document id + offsets) applied to shadow-dev at load
time, without changing the set's file, and A4/A5 reported with and without the listed items.

Run:  python eval/test_policy_items.py
Synthetic documents only.
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


def hn(s, e, lab, kind="invalid_shape"):
    return {"start": s, "end": e, "resembles": lab, "kind": kind}


DOCS = [  # 1: PII-free, a date-shaped look-alike (listed) and an email look-alike
        {"id": "d1", "text": "Tarix 12.05.2020 idi, poçt a.b-c.d", "lang": "az", "entities": [],
         "hard_negatives": [hn(6, 16, "BUILDINGNUM", "x1"), hn(26, 33, "EMAIL")]},
        # 2: PII-free, a listed FIN look-alike only
        {"id": "d2", "text": "Kod 5OI1A2B burada", "lang": "az", "entities": [],
         "hard_negatives": [hn(4, 11, "AZ_FIN", "x2")]},
        # 3: PII-free, nothing listed
        {"id": "d3", "text": "Saat 25:10 qeyd olunub", "lang": "az", "entities": [],
         "hard_negatives": [hn(5, 10, "TIME")]},
        # 4: with gold
        {"id": "d4", "text": "Ali gəldi", "lang": "az", "entities": [{"label": "GIVENNAME", "start": 0, "end": 3}],
         "hard_negatives": []}]
PREDS = {"d1": [{"label": "DATE", "start": 6, "end": 16}],
         "d2": [{"label": "AZ_FIN", "start": 4, "end": 11}],
         "d3": [{"label": "TIME", "start": 5, "end": 10}],
         "d4": [{"label": "GIVENNAME", "start": 0, "end": 3}]}

with tempfile.TemporaryDirectory() as tmp:
    priv = Path(tmp)
    f = priv / "shadow_dev.jsonl"
    f.write_text("".join(json.dumps(d, ensure_ascii=False) + "\n" for d in DOCS), encoding="utf-8")
    before = f.read_bytes()
    args = argparse.Namespace(private_dir=str(priv))
    docs, info = S.load_set("shadow_dev", args)
    check("policy_items" not in info and not any(x["listed"] for d in docs for x in d["decoys"]),
          "no list: nothing marked")
    sha = info["data_sha256_16"]
    items = [{"id": "d1", "start": 6, "end": 16, "resembles": "BUILDINGNUM", "kind": "policy_d42a"},
             {"id": "d2", "start": 4, "end": 11, "resembles": "AZ_FIN", "kind": "policy_d42b"}]
    (priv / S.POLICY_ITEMS_FILE).write_text(json.dumps({"shadow_dev": {"data_sha256_16": sha, "items": items}}))
    docs, info = S.load_set("shadow_dev", args)
    check(info["policy_items"] == {"policy_d42a": 1, "policy_d42b": 1}, "list applied: counts by kind", info.get("policy_items"))
    d1 = next(d for d in docs if d["id"] == "d1")
    check([(x["kind"], x["policy"], x["listed"]) for x in d1["decoys"]] ==
          [("policy_d42a", True, True), ("invalid_shape", False, False)], "d1: only the listed look-alike changes")
    check(f.read_bytes() == before and info["data_sha256_16"] == sha, "the set's file and its SHA are unchanged")

    res = S.score_set("shadow_dev", docs, PREDS)
    a, x = res["all"], res["excl_listed"]
    check(a["documents"]["pii_free_documents"] == 3 and a["documents"]["pii_free_with_fp"] == 3, "with the items: 3 of 3 PII-free docs masked")
    check(abs(a["decoys"]["overall"]["rate_same_label"] - 2 / 4) < 1e-9, "with the items: trigger 2 of 4", a["decoys"]["overall"])
    check(x["documents"]["pii_free_documents"] == 3 and x["documents"]["pii_free_with_fp"] == 1, "without: 1 of 3 (predictions on listed items dropped)", x["documents"])
    check(x["decoys"]["overall"]["decoys"] == 2 and x["decoys"]["overall"]["triggered_same_label"] == 1, "without: trigger 1 of 2", x["decoys"]["overall"])
    lo = x["documents_listed_docs_out"]
    check(lo["pii_free_documents"] == 1 and lo["pii_free_with_fp"] == 1, "documents with listed items left out: 1 of 1", lo)
    check(res["excl_policy"]["documents"]["pii_free_with_fp"] == 1, "excl_policy agrees (no other policy items)")

    rep = {"meta": {"name": "t", "model": "m", "revision_sha": "x", "revision_requested": None,
                    "git": {"sha": "abc", "dirty": False}, "date_utc": "d", "device": "cpu", "tracks": ["R"],
                    "data_version": {}}, "gates": [], "sets": {"shadow_dev": {"info": info, "tracks": {"R": res}}}}
    md = S.render_md(rep)
    check("Without the private policy list (policy_d42a 1, policy_d42b 1; D-42)" in md and "50.0" in md, "report line with and without")

    bad = dict(items[0], start=7)
    (priv / S.POLICY_ITEMS_FILE).write_text(json.dumps({"shadow_dev": {"data_sha256_16": sha, "items": [bad]}}))
    try:
        S.load_set("shadow_dev", args); check(False, "an item that is not in the file stops the run")
    except SystemExit as e:
        check("not found once" in str(e), "an item that is not in the file stops the run", str(e))
    (priv / S.POLICY_ITEMS_FILE).write_text(json.dumps({"shadow_dev": {"data_sha256_16": "0" * 16, "items": items}}))
    try:
        S.load_set("shadow_dev", args); check(False, "a list built for another file stops the run")
    except SystemExit as e:
        check("built for data" in str(e), "a list built for another file stops the run", str(e))

if __name__ == "__main__":
    print(f"{PASS} passed, {FAIL} failed")
    for f in FAILURES:
        print("  FAIL", f)
    sys.exit(1 if FAIL else 0)
