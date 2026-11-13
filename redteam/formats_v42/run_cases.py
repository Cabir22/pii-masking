"""Run the frozen formats benchmark on v4.2, gently (a fanless MacBook Air).

For every case it records two decodings of the same model:
  R  predict.detect_entities: the raw model, uncorrected
  M  predict._detect_entities_word_consistent: the product path (word consistency, the merge of
     overlapping windows, the validity check) -- what users get and what the rules judge (D-64a)
Writes predictions.jsonl next to this file, one line per case, appending; a rerun skips the
cases already done. Settings: max_length 512, stride 256 (predict's defaults), no truncation:
long texts are split into overlapping windows and merged.

  python redteam/formats_v42/run_cases.py            # all 200
  python redteam/formats_v42/run_cases.py --limit 25 # a portion
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "model"))

MODEL = "your-hf-org/masking-az-runb-v4.2-seed42"
REVISION = "223e54e8799dc60f6f6b19362191cf7c10c774c7"
OUT = HERE / "predictions.jsonl"


def throttled() -> bool:
    """macOS reports a CPU speed limit below 100 when it is thermally throttling."""
    try:
        out = subprocess.run(["pmset", "-g", "therm"], capture_output=True, text=True, timeout=5).stdout
    except Exception:
        return False
    for line in out.splitlines():
        if "CPU_Speed_Limit" in line:
            return int(line.split("=")[-1].strip()) < 100
    return False


def masked(text: str, spans: list[dict]) -> str:
    out, last = [], 0
    for s in sorted(spans, key=lambda s: s["start"]):
        out += [text[last:s["start"]], f"[{s['label']}]"]
        last = s["end"]
    return "".join(out + [text[last:]])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args(argv)

    import torch
    torch.set_num_threads(4)
    import predict

    cases = [json.loads(l) for l in (HERE / "formats_az_v42_200.jsonl").open(encoding="utf-8")]
    done = set()
    if OUT.exists():
        done = {json.loads(l)["id"] for l in OUT.open(encoding="utf-8")}
    todo = [c for c in cases if c["id"] not in done][: a.limit]
    if not todo:
        print("all cases done")
        return 0

    model, tok, id2label = predict.load_model(MODEL, revision=REVISION)
    device = str(next(model.parameters()).device)
    print(f"model {MODEL}@{REVISION[:8]} on {device}; {len(todo)} cases to run", flush=True)
    with OUT.open("a", encoding="utf-8") as f:
        for n, c in enumerate(todo, 1):
            while throttled():
                print("  thermal throttling: pausing 60 s", flush=True)
                time.sleep(60)
            t0 = time.time()
            R = predict.detect_entities(c["text"], model, tok, id2label)
            M = predict._detect_entities_word_consistent(c["text"], model, tok, id2label)
            windows = len(predict._tokenize_windows(c["text"], tok)["input_ids"])
            rec = {"id": c["id"], "model": f"{MODEL}@{REVISION}", "device": device,
                   "settings": {"max_length": 512, "stride": 256, "decoder": predict.DECODER_VERSION},
                   "windows": windows,
                   "R": [{k: s[k] for k in ("start", "end", "label")} for s in R],
                   "M": [{k: s[k] for k in ("start", "end", "label")} for s in M],
                   "masked_M": masked(c["text"], M), "seconds": round(time.time() - t0, 2)}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            time.sleep(0.3)
            if n % 25 == 0:
                print(f"  {n}/{len(todo)} done; cooling 45 s", flush=True)
                time.sleep(45)
    print("finished", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
