"""m1 audit: GIVENNAME false alarms on lang_tr / lang_ru (every 3rd document of the scoreboard's
1,000-document sample; track M, m1). Lists every GIVENNAME prediction with no gold
overlap, with context, for review. A sample: counts are not extrapolated. Writes names_trru.jsonl."""
import json, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT / "eval"), str(ROOT / "model"), str(HERE), str(ROOT / "redteam/formats_v42")]
import torch; torch.set_num_threads(4)
import predict, scoreboard as S, diag_run as D
from run_cases import throttled
model, tok, i2l = predict.load_model("your-hf-org/masking-multi-m1-seed42", revision="d7493a1634f3aadc4dab5cd3b8103cf070e5eff0")
out = []
for s in ("lang_tr", "lang_ru"):
    docs, _ = S.load_set(s, D.ARGS)
    for n, d in enumerate(docs[::3], 1):
        while throttled(): time.sleep(60)
        t = d["text"]
        for p in predict._detect_entities_word_consistent(t, model, tok, i2l):
            if p["label"] != "GIVENNAME" or any(g["start"] == p["start"] and g["end"] == p["end"] and g["label"] == "GIVENNAME" for g in d["gold"]):
                continue
            ovl = [(g["label"], t[g["start"]:g["end"]]) for g in d["gold"] if g["start"] < p["end"] and p["start"] < g["end"]]
            out.append({"set": s, "doc": d["id"], "value": t[p["start"]:p["end"]], "gold_overlap": ovl,
                        "context": t[max(0, p["start"] - 50):p["end"] + 35].replace("\n", " ⏎ ")})
        time.sleep(0.2)
        if n % 100 == 0: time.sleep(30)
(HERE / "names_trru.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out), encoding="utf-8")
from collections import Counter
for s in ("lang_tr", "lang_ru"):
    rs = [x for x in out if x["set"] == s]
    kinds = Counter(("no gold overlap" if not x["gold_overlap"] else "overlaps gold " + "/".join(sorted({l for l, _ in x["gold_overlap"]}))) for x in rs)
    print(f"== {s}: {len(rs)} non-exact GIVENNAME predictions in every 3rd document:", dict(kinds))
    for x in rs[:30]: print(f"   {x['value']!r:18} gold: {x['gold_overlap']} … {x['context'][:90]}")
