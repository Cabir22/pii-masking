"""Tests for D-51c: track R's long-document path joins overlapping same-label window pieces
(the same rule as predict._merge_window_spans, D-51b), and a track-R cache written before the
join re-runs only its long documents.

Run:  python eval/test_scoreboard_r_long.py
"""
from __future__ import annotations

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


def ent(label, start, end, score=0.9, word="x"):
    return {"entity_group": label, "start": start, "end": end, "score": score, "word": word}


def spans(out):
    return sorted((e["entity_group"], e["start"], e["end"]) for e in out)


# --- join_window_pieces ----------------------------------------------------------------
# a key longer than one window: three overlapping pieces become one span
out = S.join_window_pieces([ent("PRIVATE_KEY", 0, 1200, 0.8), ent("PRIVATE_KEY", 900, 2500, 0.95),
                            ent("PRIVATE_KEY", 2200, 3900, 0.7)])
check(spans(out) == [("PRIVATE_KEY", 0, 3900)], "three overlapping pieces joined", spans(out))
check(out[0]["score"] == 0.95, "joined score is the highest piece score", out[0]["score"])
check("word" not in out[0], "a joined span drops the first piece's word", out[0])

# containment and duplicates: same result as keep-longest
out = S.join_window_pieces([ent("EMAIL", 10, 30), ent("EMAIL", 12, 20), ent("EMAIL", 10, 30)])
check(spans(out) == [("EMAIL", 10, 30)], "contained and duplicate pieces give the containing span", spans(out))

# touching but not overlapping: two entities
out = S.join_window_pieces([ent("GIVENNAME", 0, 5), ent("GIVENNAME", 5, 9)])
check(spans(out) == [("GIVENNAME", 0, 5), ("GIVENNAME", 5, 9)], "touching same-label spans stay two", spans(out))

# different labels are not joined here
out = S.join_window_pieces([ent("AZ_FIN", 0, 7), ent("AZ_VOEN", 3, 13)])
check(spans(out) == [("AZ_FIN", 0, 7), ("AZ_VOEN", 3, 13)], "different labels are not joined", spans(out))

# order of the input does not matter
a = [ent("PRIVATE_KEY", 2200, 3900), ent("PRIVATE_KEY", 0, 1200), ent("PRIVATE_KEY", 900, 2500)]
check(spans(S.join_window_pieces(a)) == [("PRIVATE_KEY", 0, 3900)], "input order does not matter")
check(a[0]["start"] == 2200 and a[0]["end"] == 3900, "input entities are not changed")

# --- the pipeline subclass: join, then the pipeline's own keep-longest -------------------
try:
    P = S._join_pieces_pipeline()
    agg = lambda ents: P.aggregate_overlapping_entities(object.__new__(P), ents)  # noqa: E731
    out = agg([ent("PRIVATE_KEY", 0, 1200), ent("PRIVATE_KEY", 900, 2500), ent("URL", 2400, 2450),
               ent("EMAIL", 3000, 3020)])
    check(spans(out) == [("EMAIL", 3000, 3020), ("PRIVATE_KEY", 0, 2500)],
          "pipeline: pieces joined, then a shorter other-label overlap dropped", spans(out))
    from transformers import TokenClassificationPipeline
    base = TokenClassificationPipeline.aggregate_overlapping_entities(
        object.__new__(TokenClassificationPipeline), [ent("PRIVATE_KEY", 0, 1200), ent("PRIVATE_KEY", 900, 2500)])
    check(spans(base) == [("PRIVATE_KEY", 900, 2500)], "the stock pipeline keeps one piece (the bug)", spans(base))
except ImportError as exc:  # transformers missing: the join itself is tested above
    print(f"skipped pipeline checks: {exc}")


# --- the prediction cache ----------------------------------------------------------------
class FakeEngine:
    def __init__(self):
        self.ran = []

    def r_is_long(self, text):
        return text.startswith("LONG")

    def run(self, track, text):
        self.ran.append(text)
        return [{"label": "NEW", "start": 0, "end": 1}]


docs = [{"id": "a", "text": "short one"}, {"id": "b", "text": "LONG one"}, {"id": "c", "text": "LONG two"}]
key = {"model": "m", "revision": "r", "set": "s", "track": "R", "data": "d"}
old = {"key": key, "preds": {d["id"]: [{"label": "OLD", "start": 0, "end": 1}] for d in docs},
       "hashes": {d["id"]: S._text_hash(d["text"]) for d in docs}}
with tempfile.TemporaryDirectory() as tmp:
    cf = Path(tmp) / "s.R.json"
    cf.write_text(json.dumps(old))
    eng = FakeEngine()
    preds = S.predict_set(eng, "R", docs, cf, key, "s/R")
    check(sorted(eng.ran) == ["LONG one", "LONG two"], "old track-R cache: only long documents re-run", eng.ran)
    check(preds["a"][0]["label"] == "OLD" and preds["b"][0]["label"] == "NEW", "short kept, long replaced", preds)
    blob = json.loads(cf.read_text())
    check(blob.get("r_long") == S.R_LONG_DECODER, "the cache records the join", blob.get("r_long"))
    eng2 = FakeEngine()
    S.predict_set(eng2, "R", docs, cf, key, "s/R")
    check(eng2.ran == [], "a marked cache re-runs nothing", eng2.ran)

    # an old cache with no long documents is marked without re-running anything
    cf2 = Path(tmp) / "t.R.json"
    short = [docs[0]]
    cf2.write_text(json.dumps({"key": key, "preds": {"a": old["preds"]["a"]}, "hashes": {"a": old["hashes"]["a"]}}))
    eng3 = FakeEngine()
    S.predict_set(eng3, "R", short, cf2, key, "t/R")
    check(eng3.ran == [] and json.loads(cf2.read_text()).get("r_long") == S.R_LONG_DECODER,
          "old cache without long documents: marked, nothing re-run")

    # track M is not affected
    mkey = {**key, "track": "M"}
    cf3 = Path(tmp) / "s.M.json"
    cf3.write_text(json.dumps({**old, "key": mkey}))
    eng4 = FakeEngine()
    S.predict_set(eng4, "M", docs, cf3, mkey, "s/M")
    check(eng4.ran == [] and "r_long" not in json.loads(cf3.read_text()), "track M cache untouched", eng4.ran)

print(f"{PASS} passed, {FAIL} failed")
for f in FAILURES:
    print("  FAIL", f)
sys.exit(1 if FAIL else 0)
