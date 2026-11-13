"""v4.1 analysis: how sure is each model of a benchmark value?
The mean probability of the gold label (B- + I-) over the value's tokens, in
the whole document and in its sentence alone, for v3 and v4. A value v4
misses in the document but finds alone should sit just under 0.5 in the
document if the cause is a thin margin rather than an unknown shape.

    python reports/v41_public_analysis/margin.py --label IPV6_ADDRESS --label IPV4_ADDRESS \
        [--controls 60] [--out reports/v41_public_analysis/out/margin.md]
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from pathlib import Path

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import perturb as P  # noqa: E402
import read_errors as R  # noqa: E402


def gold_prob(tok, model, text: str, s: int, e: int, label: str) -> float:
    enc = tok(text, return_offsets_mapping=True, truncation=True, max_length=512, return_tensors="pt")
    offs = enc.pop("offset_mapping")[0].tolist()
    with torch.no_grad():
        probs = model(**enc).logits[0].softmax(-1)
    ids = [i for l, i in model.config.label2id.items() if l in (f"B-{label}", f"I-{label}")]
    rows = [k for k, (a, b) in enumerate(offs) if b > a and a < e and b > s]
    return float(probs[rows][:, ids].sum(-1).mean()) if rows else 0.0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--label", action="append", required=True)
    ap.add_argument("--controls", type=int, default=60)
    ap.add_argument("--errors-dir", default=str(R.OUT))
    ap.add_argument("--out", default=str(R.OUT / "margin.md"))
    a = ap.parse_args()
    O, N = R.OLD, R.NEW
    docs = R.load_docs("benchmark")
    rng = random.Random(20261017)
    cases = []
    for lab in a.label:
        res = json.loads((Path(a.errors_dir) / f"benchmark_R_{lab}.json").read_text(encoding="utf-8"))
        bad = {(i["id"], i["value"]) for i in res["items"] if i["outcomes"][N] != "exact"}
        good = []
        for d in docs:
            for g in d["gold"]:
                if g["label"] == lab:
                    key = (d["id"], d["text"][g["start"]:g["end"]])
                    (cases if key in bad else good).append((lab, f"{N} misses" if key in bad else f"{N} finds",
                                                            d["text"], g["start"], g["end"]))
        cases += rng.sample(good, min(a.controls, len(good)))
    out = {}
    for m, (mid, sha) in R.MODELS.items():
        tok = AutoTokenizer.from_pretrained(mid, revision=sha)
        model = AutoModelForTokenClassification.from_pretrained(mid, revision=sha).eval()
        for k, (lab, grp, text, s, e) in enumerate(cases):
            sent, off = P.sentence(text, s, e)
            out[(m, k, "doc")] = gold_prob(tok, model, text, s, e, lab)
            out[(m, k, "sentence")] = gold_prob(tok, model, sent, off, off + (e - s), lab)
        del model
    L = ["# Probability of the gold label on the value's tokens (mean over tokens)", "",
         f"| label | spans | n | {O} doc | {N} doc | {O} sentence | {N} sentence | {N} doc in 0.2-0.5 |",
         "|---|---|---|---|---|---|---|---|"]
    for lab in a.label:
        for grp in (f"{N} misses", f"{N} finds"):
            ks = [k for k, c in enumerate(cases) if c[0] == lab and c[1] == grp]
            if not ks:
                continue
            med = lambda m, v: statistics.median(out[(m, k, v)] for k in ks)
            near = sum(0.2 <= out[(N, k, "doc")] < 0.5 for k in ks)
            L.append(f"| {lab} | {grp} | {len(ks)} | {med(O, 'doc'):.2f} | {med(N, 'doc'):.2f} | "
                     f"{med(O, 'sentence'):.2f} | {med(N, 'sentence'):.2f} | {near} |")
    L += ["", f"Medians. `{N} finds` is a random sample of the spans {N} finds exactly."]
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
