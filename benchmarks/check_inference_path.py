"""Which inference path produced the benchmark's predictions?

The report says "raw model, exact label+start+end" but not how the model was
called. Our numbers are only comparable to the report's if we call it the
same way. This reruns a random sample of Appendix A documents through:

  (a) a plain Hugging Face token-classification pipeline,
      aggregation_strategy="simple", tokenizer loaded as shipped -- the
      obvious way an outside harness calls a Hub model, and the only common
      path that emits a per-entity score
  (b) this repo's production entry point: model/predict.load_model
      (applies the punctuation-boundary tokenizer patch the training data
      was built with) + hybrid_detect_entities (word-consistency fix +
      pattern_fallback regex/checksum layer)

and counts how many of the report's error predictions (label + exact span)
each path reproduces. (a) also has to reproduce the printed scores.

Only documents whose text rebuilds exactly are used (extract_report.py
accepts a rebuild only if every listed span lands on its value).

Run:  python benchmarks/check_inference_path.py [--n 80] [--seed 7]
Output: benchmarks/extracted/inference_path_check.json
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "scripts"))
MODEL = "your-hf-org/masking-multilingual"

# main carries no inference code: model/predict.py and model/pattern_fallback.py
# exist only on feature branches. Export them from one pinned ref into a temp
# dir (same approach as audit/harness.py) rather than switching branches.
INFERENCE_REF = "origin/excel-txt"
INFERENCE_FILES = ["model/predict.py", "model/pattern_fallback.py"]


def export_inference_code() -> tuple[str, str]:
    import subprocess
    import tempfile
    sha = subprocess.run(["git", "-C", str(ROOT), "rev-parse", INFERENCE_REF],
                         capture_output=True, text=True, check=True).stdout.strip()
    dest = Path(tempfile.mkdtemp(prefix="bench_infer_"))
    for f in INFERENCE_FILES:
        blob = subprocess.run(["git", "-C", str(ROOT), "show", f"{sha}:{f}"],
                              capture_output=True, check=True).stdout
        (dest / Path(f).name).write_bytes(blob)
    sys.path.insert(0, str(dest))
    return sha, str(dest)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=80)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    recs = json.loads((HERE / "extracted" / "records.json").read_text(encoding="utf-8"))
    usable = [r for r in recs if r["text"] is not None]
    random.seed(args.seed)
    sample = random.sample(usable, args.n)

    from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline
    tok = AutoTokenizer.from_pretrained(MODEL)
    mdl = AutoModelForTokenClassification.from_pretrained(MODEL)
    hf = pipeline("token-classification", model=mdl, tokenizer=tok,
                  aggregation_strategy="simple", device=-1)

    sha, _ = export_inference_code()
    from predict import hybrid_detect_entities, load_model
    p_model, p_tok, p_id2label = load_model(MODEL)

    stats = Counter()
    score_diffs = []
    gold_exact = Counter()
    gold_total = Counter()
    per_doc = []
    for rec in sample:
        text = rec["text"]
        bench_preds = [e for e in rec["entries"] if e["kind"] == "pred"]
        golds = [e for e in rec["entries"] if e["kind"] == "gold"]

        hf_out = {(o["entity_group"], o["start"], o["end"]): float(o["score"]) for o in hf(text)}
        prod = hybrid_detect_entities(text, p_model, p_tok, p_id2label)
        prod_keys = {(o["label"], o["start"], o["end"]) for o in prod}

        hit_hf = hit_prod = 0
        for bp in bench_preds:
            k = (bp["label"], bp["start"], bp["end"])
            stats["report_error_predictions"] += 1
            if k in hf_out:
                hit_hf += 1
                score_diffs.append(abs(hf_out[k] - bp["score"]))
            if k in prod_keys:
                hit_prod += 1
        stats["reproduced_by_plain_hf_pipeline"] += hit_hf
        stats["reproduced_by_production_hybrid"] += hit_prod

        for g in golds:
            gold_total[g["label"]] += 1
            if (g["label"], g["start"], g["end"]) in prod_keys:
                gold_exact[g["label"]] += 1
        per_doc.append({"data_id": rec["data_id"], "report_preds": len(bench_preds),
                        "plain_hf_hits": hit_hf, "production_hits": hit_prod})

    out = {
        "sample_documents": len(sample), "seed": args.seed,
        "production_path_source": f"{INFERENCE_REF} @ {sha} ({', '.join(INFERENCE_FILES)})",
        "documents_with_exact_text": len(usable), "appendix_documents": len(recs),
        **stats,
        "score_abs_diff_max": round(max(score_diffs), 5) if score_diffs else None,
        "score_abs_diff_mean": round(sum(score_diffs) / len(score_diffs), 6) if score_diffs else None,
        "report_misses_production_gets_exactly_right": {
            lab: f"{gold_exact[lab]}/{gold_total[lab]}"
            for lab in sorted(gold_total, key=lambda l: -gold_total[l])},
        "report_misses_production_total": f"{sum(gold_exact.values())}/{sum(gold_total.values())}",
        "caveat": "Production's own extra false positives cannot be measured from Appendix A "
                  "(it lists only error-related predictions and misses, not correct ones), "
                  "so this is not a re-score of the benchmark.",
        "per_document": per_doc,
    }
    (HERE / "extracted" / "inference_path_check.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "per_document"},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
