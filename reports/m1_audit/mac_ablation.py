"""m1 audit: take benchmark documents where m1 misses a MAC that v4.2 finds, and change one thing:
(a) as is, (b) the document's declared hard negatives replaced by neutral words, (c) version strings
(1.2.3 / v1.2.3) replaced, (d) only the MAC's own sentence. Track M, m1 only; writes mac_ablation.md."""
import json, re, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT / "eval"), str(ROOT / "model"), str(HERE)]
import torch; torch.set_num_threads(4)
import predict, diag_run as D
docs = {d["id"]: d for d in D.subset("bench_mac")}
raw = {}
for l in open(ROOT / "data/benchmark_v3/pii_az_benchmark_v3_structured_9780.jsonl"):
    r = json.loads(l); raw[r["id"]] = r
    if len(raw) >= 5000: break
rows = [json.loads(l) for l in open(HERE / "mac_cases.jsonl")]
fail = [r for r in rows if r["v42"] == "correct" and r["m1"] != "correct"][:40]
model, tok, i2l = predict.load_model("your-hf-org/masking-multi-m1-seed42", revision="d7493a1634f3aadc4dab5cd3b8103cf070e5eff0")
VER = re.compile(r"\bv?\d{1,2}\.\d{1,2}\.\d{1,3}\b")
def outcome(t, v):
    s = t.index(v); P = predict._detect_entities_word_consistent(t, model, tok, i2l)
    if any(p["start"] == s and p["end"] == s + len(v) and p["label"] == "MAC_ADDRESS" for p in P): return "exact"
    return "partly" if any(p["start"] < s + len(v) and s < p["end"] for p in P) else "missed"
def hn_strings(r):
    out = []
    for h in (r.get("_hard_negatives") or []):
        out.append(h if isinstance(h, str) else (h.get("text") or h.get("value") or ""))
    return [x for x in out if x]
res = []
for n, r in enumerate(fail, 1):
    d = docs[r["doc"]]; t = d["text"]; v = r["value"]
    hn = sorted({t[x["start"]:x["end"]] for x in d["decoys"] if t[x["start"]:x["end"]] and t[x["start"]:x["end"]] != v})
    t_hn = t
    for h in hn: t_hn = t_hn.replace(h, "qeyd")
    t_ver = VER.sub("qeyd", t)
    s = t.index(v); a = max(t.rfind(". ", 0, s), t.rfind("\n", 0, s)) + 1; b = t.find(";", s); b = len(t) if b < 0 else b
    sent = t[a:b].strip()
    res.append({"doc": r["doc"], "value": v, "hard_negatives": hn[:6], "as_is": outcome(t, v),
                "no_hard_negatives": outcome(t_hn, v) if v in t_hn else "n/a",
                "no_versions": outcome(t_ver, v) if v in t_ver else "n/a", "sentence_only": outcome(sent, v)})
    time.sleep(0.3)
    if n % 15 == 0: time.sleep(20)
from collections import Counter
L = ["# MAC ablation on documents where m1 fails and v4.2 is exact (track M, m1)", "",
     f"{len(res)} documents. One change per column.", "", "| Change | exact | partly | missed |", "|---|---|---|---|"]
for k in ("as_is", "no_hard_negatives", "no_versions", "sentence_only"):
    c = Counter(x[k] for x in res); L.append(f"| {k} | {c['exact']} | {c['partly']} | {c['missed']} |")
L += ["", "| doc | MAC | hard negatives replaced | as is | no HN | no versions | sentence only |", "|---|---|---|---|---|---|---|"]
L += [f"| {x['doc']} | `{x['value']}` | {', '.join('`'+h+'`' for h in x['hard_negatives']) or '–'} | {x['as_is']} | {x['no_hard_negatives']} | {x['no_versions']} | {x['sentence_only']} |" for x in res]
(HERE / "mac_ablation.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L[:12]))
