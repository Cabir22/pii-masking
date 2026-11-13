"""Tests for eval/build_redteam_barrier.py and the guard's short-text check, on
synthetic findings written for this test.

Run:  python eval/test_redteam_barrier.py
"""
from __future__ import annotations

import contextlib
import csv
import io
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build_redteam_barrier as R  # noqa: E402
from leakage_guard import Guard, load_shadow, main, merge_barriers  # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond, name, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(f"{name}: {detail!r}" if detail is not None else name)


def guard(barrier: dict) -> Guard:
    return Guard({}, {}, set(), [], barrier)


def hits(g: Guard, text: str) -> int:
    before = g.counts["shadow_ngrams"] + g.counts["shadow_values"]
    g.scan("doc", text)
    return g.counts["shadow_ngrams"] + g.counts["shadow_values"] - before


# --- parsing `expected` ---------------------------------------------------------
check(R.expected_values("(nothing)") == [], "(nothing) gives no values")
check(R.expected_values("") == [], "empty gives no values")
check(R.expected_values("AB12CD34EF=API_KEY; Rauf=GIVENNAME") == [("AB12CD34EF", "API_KEY"), ("Rauf", "GIVENNAME")],
      "two values", R.expected_values("AB12CD34EF=API_KEY; Rauf=GIVENNAME"))
check(R.expected_values("tok==x9Q=ACCESS_TOKEN") == [("tok==x9Q", "ACCESS_TOKEN")], "'=' inside a value")
check(R.expected_values("should not be masked") == [], "free text gives no values")

COLS = ["id", "date", "area", "language", "text", "expected", "model_output",
        "problem", "note", "model", "split"]
ROWS = [
    # 8+ words: 8-grams
    {"id": "RT-t-0001", "text": "omeqa psi xi pi ro siqma tau ipsilon fi", "expected": "(nothing)", "split": ""},
    # 4 words: hashed whole
    {"id": "RT-t-0002", "text": "Alfa beta 120 qamma.", "expected": "(nothing)", "split": "test"},
    # 2 words: too short
    {"id": "RT-t-0003", "text": "Salam dost", "expected": "", "split": ""},
    # a code value (hashed) and a name (never hashed)
    {"id": "RT-t-0004", "text": "Açar QX7ZK2M9WP4T verildi, Rauf.", "expected": "QX7ZK2M9WP4T=API_KEY; Rauf=GIVENNAME",
     "split": ""},
    # marked training: left out
    {"id": "RT-t-0005", "text": "Delta epsilon zeta eta.", "expected": "(nothing)", "split": "training"},
    # value not in the text: skipped
    {"id": "RT-t-0006", "text": "Kod yoxdur burada heç.", "expected": "ZZ9QK3M8PL2X=API_KEY", "split": ""},
]

with tempfile.TemporaryDirectory() as tmp:
    td = Path(tmp)
    (td / "f").mkdir()
    with open(td / "f" / "t.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        for r in ROWS:
            w.writerow({c: r.get(c, "") for c in COLS})
    out = td / "b.json.gz"
    with contextlib.redirect_stdout(io.StringIO()):
        R.main(["--findings", str(td / "f"), "--out", str(out)])
    b = load_shadow(out)
    s = b["source"]
    check((s["findings"], s["test_rows"], s["training_rows"], s["too_short"]) == (6, 5, 1, 1),
          "row counts", (s["findings"], s["test_rows"], s["training_rows"], s["too_short"]))
    check(len(b["ngram_sha1"]) == 2, "9 words -> 2 8-grams", len(b["ngram_sha1"]))
    check(sorted(x["n"] for x in b["short_sha1"]) == [4, 4, 4], "three 4-word texts hashed whole",
          [x["n"] for x in b["short_sha1"]])
    check(len(b["values"]) == 1, "one code value hashed", len(b["values"]))
    check(b["values_skipped"]["name, place or date label"] == 1 and b["values_skipped"]["not found in the text"] == 1,
          "name and missing value skipped", b["values_skipped"])
    blob = out.read_bytes()
    check(b"Alfa" not in blob and b"QX7ZK2M9WP4T" not in blob, "no text in the clear")

    g = guard(merge_barriers([(out, b)]))
    check(hits(g, "Bu gün, alfa beta 120 qamma, dedi.") == 1, "a short finding inside a longer text is caught")
    check(hits(g, "ALFA   BETA 120 QAMMA") == 1, "case and spacing do not hide it")
    check(hits(g, "Alfa beta 121 qamma.") == 0, "another number is a different text")
    check(hits(g, "Alfa beta 120.") == 0, "three of the four words are not a hit")
    check(hits(g, "Delta epsilon zeta eta.") == 0, "a row marked training is not a barrier")
    check(hits(g, "Salam dost, necəsən?") == 0, "two-word findings block nothing")
    check(hits(g, "Yeni açar: QX7ZK2M9WP4T.") == 1, "the code value is caught in other words")
    check(hits(g, "Rauf gəldi.") == 0, "a name is never a barrier value")
    check(hits(g, "x omeqa psi xi pi ro siqma tau ipsilon") == 1, "8-gram of a long finding")

    # Old barrier files without short_sha1 still merge and load.
    old = {"ngram_sha1": [], "values": [], "source": {"files": 0}}
    m = merge_barriers([(Path("old.json.gz"), old), (out, b)])
    check(len(m["short_sha1"]) == 3, "merge keeps short hashes next to an old-format file", len(m["short_sha1"]))

    # End to end: a training file that copies a short finding fails the guard.
    (td / "train.docs.jsonl").write_text(
        json.dumps({"id": "d1", "text": "Hesabatda yazılıb: alfa beta 120 qamma."}, ensure_ascii=False) + "\n",
        encoding="utf-8")
    (td / "clean.docs.jsonl").write_text(json.dumps({"id": "d2", "text": "Sadə mətn."}) + "\n", encoding="utf-8")
    with contextlib.redirect_stdout(io.StringIO()):
        rc_dirty = main([str(td / "train.docs.jsonl"), "--barrier-hashes", str(out)])
        rc_clean = main([str(td / "clean.docs.jsonl"), "--barrier-hashes", str(out)])
    check(rc_dirty == 1 and rc_clean == 0, "guard exit codes with the red-team barrier", (rc_dirty, rc_clean))


if __name__ == "__main__":
    print(f"{PASS} passed, {FAIL} failed")
    for f in FAILURES:
        print("  FAIL", f)
    sys.exit(1 if FAIL else 0)
