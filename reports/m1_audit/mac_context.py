"""m1 audit: how much surrounding text makes m1 miss a MAC that it finds in its sentence alone.
Same 40 documents as mac_ablation.py; keeps the MAC plus N characters before it (cut at a word),
or the MAC plus everything after it. Track M, m1; appends to mac_ablation.md."""
import json, sys, time
from pathlib import Path
from collections import Counter
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT / "eval"), str(ROOT / "model"), str(HERE)]
import torch; torch.set_num_threads(4)
import predict, diag_run as D
docs = {d["id"]: d for d in D.subset("bench_mac")}
rows = [json.loads(l) for l in open(HERE / "mac_cases.jsonl")]
fail = [r for r in rows if r["v42"] == "correct" and r["m1"] != "correct"][:40]
model, tok, i2l = predict.load_model("your-hf-org/masking-multi-m1-seed42", revision="d7493a1634f3aadc4dab5cd3b8103cf070e5eff0")
def outcome(t, v):
    s = t.index(v); P = predict._detect_entities_word_consistent(t, model, tok, i2l)
    if any(p["start"] == s and p["end"] == s + len(v) and p["label"] == "MAC_ADDRESS" for p in P): return "exact"
    return "partly" if any(p["start"] < s + len(v) and s < p["end"] for p in P) else "missed"
res = {k: Counter() for k in ("before 100", "before 300", "before 600", "all before, nothing after", "nothing before, all after")}
for n, r in enumerate(fail, 1):
    t = docs[r["doc"]]["text"]; v = r["value"]; s = t.index(v); e = s + len(v)
    endsent = t.find(";", e); endsent = len(t) if endsent < 0 else endsent
    for k, cut in (("before 100", 100), ("before 300", 300), ("before 600", 600)):
        a = max(0, s - cut); a = t.find(" ", a) + 1 if a > 0 else 0
        res[k][outcome(t[a:endsent], v)] += 1
    res["all before, nothing after"][outcome(t[:endsent], v)] += 1
    st = max(t.rfind(". ", 0, s) + 2, t.rfind("\n", 0, s) + 1, 0)
    res["nothing before, all after"][outcome(t[st:], v)] += 1
    time.sleep(0.3)
    if n % 15 == 0: time.sleep(20)
L = ["", "## How much context (40 documents, m1)", "", "| Kept | exact | partly | missed |", "|---|---|---|---|"]
for k, c in res.items(): L.append(f"| {k} | {c['exact']} | {c['partly']} | {c['missed']} |")
with open(HERE / "mac_ablation.md", "a", encoding="utf-8") as f: f.write("\n".join(L) + "\n")
print("\n".join(L))
