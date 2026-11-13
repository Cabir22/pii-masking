"""m1 audit: per-document predictions on the subsets the public report cannot explain.

Uses the scoreboard's own pieces (eval/scoreboard.py: load_set, Engine, score_set), so the
predictions and scores are produced exactly as in the reports (tracks R and M, transformers
4.57.x, the punctuation pre-tokenizer). Subsets:
  golden_en         all 217 documents                  m1, checkpoint 1
  names_list_lines  the 14 probe documents of C13's family   m1, v4.2, checkpoint 1
  bench_mac         benchmark docs (first 5,000) with a gold MAC, plus docs with a MAC-like string
                                                          m1, v4.2
Runs gently (4 threads, pauses, waits while macOS throttles) and resumes from preds/*.json.

  python reports/m1_audit/diag_run.py [--only SUBSET] [--models m1,v42,ckpt1]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT / "eval"), str(ROOT / "model"), str(ROOT / "redteam" / "formats_v42")]

MODELS = {"m1": ("your-hf-org/masking-multi-m1-seed42", "d7493a1634f3aadc4dab5cd3b8103cf070e5eff0"),
          "v42": ("your-hf-org/masking-az-runb-v4.2-seed42", "223e54e8799dc60f6f6b19362191cf7c10c774c7"),
          "ckpt1": ("your-hf-org/masking-multilingual", "2519392a4c7cabc26bfadf1a5ba4c6a6d8c638cf")}
PLAN = {"golden_en": ["m1", "ckpt1"], "names_list_lines": ["m1", "v42", "ckpt1"], "bench_mac": ["m1", "v42"],
        "lang_tr": ["m1", "ckpt1"], "lang_ru": ["m1", "ckpt1"]}  # lang_*: D-74 review candidates (track M only)
MAC_LIKE = re.compile(r"\b(?:[0-9A-Fa-f]{2}[:\-.]){5}[0-9A-Fa-f]{2}\b|\b[0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4}\."
                      r"[0-9A-Fa-f]{4}\b|\b[0-9A-Fa-f]{12}\b")
ARGS = SimpleNamespace(private_dir=str(ROOT / ".no-private-sets"), lang_sample=1000, runb_test=None,
                       runb_v1_test=None, runb_parts=None, limit=None, sample=None)


def subset(name: str) -> list[dict]:
    import scoreboard as S
    if name == "golden_en":
        docs, _ = S.load_set("golden_en", ARGS)
    elif name == "names_list_lines":
        docs, _ = S.load_set("probes", ARGS)
        docs = [d for d in docs if d["meta"].get("family") == "names_list_lines"]
    elif name in ("lang_tr", "lang_ru"):
        docs, _ = S.load_set(name, ARGS)
    elif name == "bench_mac":
        docs, _ = S.load_set("benchmark", ARGS)
        docs = [d for d in docs if any(g["label"] == "MAC_ADDRESS" for g in d["gold"]) or MAC_LIKE.search(d["text"])]
    return docs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--models", default=None)
    ap.add_argument("--tracks", default="R,M")
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args(argv)
    import torch
    torch.set_num_threads(a.threads)
    import scoreboard as S
    from run_cases import throttled
    out = HERE / "preds"
    out.mkdir(exist_ok=True)
    sets = {k: subset(k) for k in PLAN if not a.only or k == a.only}
    for s, docs in sets.items():
        print(f"{s}: {len(docs)} documents", flush=True)
    wanted = a.models.split(",") if a.models else ["m1", "v42", "ckpt1"]
    for mk in wanted:
        todo = [s for s in sets if mk in PLAN[s]]
        if not todo:
            continue
        model, rev = MODELS[mk]
        eng = S.Engine(model, rev, "cpu", a.tracks.split(","))
        for s in todo:
            f = out / f"{s}.{mk}.json"
            done = json.loads(f.read_text()) if f.exists() else {"model": model, "revision": rev, "R": {}, "M": {}}
            for n, d in enumerate(sets[s], 1):
                if d["id"] in done["M"]:
                    continue
                while throttled():
                    print("  throttled: pausing 60 s", flush=True)
                    time.sleep(60)
                for t in a.tracks.split(","):
                    done[t][d["id"]] = eng.run(t, d["text"])
                if n % 20 == 0:
                    f.write_text(json.dumps(done))
                    time.sleep(1)
                if n % 100 == 0:
                    print(f"  {mk} {s}: {n}/{len(sets[s])}; cooling 30 s", flush=True)
                    time.sleep(30)
            f.write_text(json.dumps(done))
            print(f"  {mk} {s}: done", flush=True)
        del eng
        time.sleep(20)
    print("ALL DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
