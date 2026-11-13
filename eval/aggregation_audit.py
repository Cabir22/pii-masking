"""P2-11 aggregation audit (was P3-6): are the RC5 boundary errors the
pipeline's aggregation or the model?

RC5: spans cut short or split -- `Fidan.` masked as `dan`, a PEM key as two
spans, space-grouped phones and cards cut. P3-3a and P2-12 showed the
training labels are right, so the cause is the model or how token
predictions are merged into spans. This script runs checkpoint 1 ONCE per
document and decodes the same output several ways:

  raw tokenizer (as shipped; the benchmark's path):
    simple, first, max, average   transformers' aggregation strategies
  patched tokenizer (model/predict.load_model: punctuation boundary):
    first, max, average           the word strategies with real word edges
  word_consistent                 predict._detect_entities_word_consistent,
                                  the product path's own decode (track M)

and scores each with eval/metrics.py: exact and overlap P/R/F1, leaked PII
characters, boundary errors (narrower / wider / shifted), plus how often ONE
gold value comes out as two or more same-label pieces ("split").

D-3: nothing is added after the model at inference. This only measures; a
clearly better strategy is proposed to the team as a decision, never wired
into predict.py here. A2.5: public sets only (probes, golden_az); the shadow
and sealed sets are the team's.

Run:
    python eval/aggregation_audit.py [--families pem,spaced_phone,...] [--golden]
        [--md reports/aggregation/p2-11_aggregation.md] [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "model"))
sys.path.insert(0, str(ROOT / "scripts"))

import metrics as M  # noqa: E402

MODEL = "your-hf-org/masking-multilingual"
# The RC5 boundary families, and the suffix and bare-name families whose
# failures are boundary failures too (`Fidan.` -> `dan`, a suffix cut off).
RC5_FAMILIES = ("pem", "spaced_phone", "spaced_card_iban", "punct_touching", "bare_name",
                "suffixed_entities", "prose_card", "prose_iban")
RAW_STRATEGIES = ("simple", "first", "max", "average")
PATCHED_STRATEGIES = ("first", "max", "average")
DECODES = ([f"raw/{s}" for s in RAW_STRATEGIES] + [f"patched/{s}" for s in PATCHED_STRATEGIES]
           + ["word_consistent"])


def splits(docs: list[dict]) -> dict:
    """Gold values that come out as two or more same-label pieces, each
    overlapping the value: no repair after the model glues them (D-3)."""
    n = split = pieces = 0
    per_label = Counter()
    for d in docs:
        for g in d["gold"]:
            n += 1
            hits = [p for p in d["pred"]
                    if p["label"] == g["label"] and p["start"] < g["end"] and g["start"] < p["end"]]
            if len(hits) >= 2:
                split += 1
                pieces += len(hits)
                per_label[g["label"]] += 1
    return {"gold": n, "split": split, "rate": split / n if n else 0.0,
            "pieces": pieces, "per_label": dict(per_label)}


def score(docs: list[dict]) -> dict:
    ex, ov = M.exact_scores(docs), M.overlap_scores(docs)
    leak, bnd = M.char_leakage(docs), M.boundary_errors(docs)
    return {"exact": ex["micro"], "overlap": ov["micro"], "leak_rate": leak["rate"],
            "leaked_chars": leak["leaked_chars"], "gold_chars": leak["gold_chars"],
            "boundary": {k: bnd[k] for k in ("n", "narrower", "wider", "shifted")},
            "split": splits(docs)}


class Decoder:
    """One model, two tokenizers; each document goes through the network once
    per tokenizer, and every aggregation strategy decodes that same output."""

    def __init__(self, model_id: str, device: str = "cpu"):
        from transformers import AutoTokenizer, pipeline
        import predict
        self.predict = predict
        self.model, self.tok_patched, self.id2label = predict.load_model(model_id, device=device)
        self.tok_raw = AutoTokenizer.from_pretrained(model_id)
        self.device = device
        self.pipes = {
            "raw": pipeline("token-classification", model=self.model, tokenizer=self.tok_raw,
                            aggregation_strategy="simple", device=device),
            "patched": pipeline("token-classification", model=self.model,
                                tokenizer=self.tok_patched, aggregation_strategy="simple",
                                device=device),
        }

    def _outputs(self, pipe, text: str):
        pre, _fwd, _post = pipe._sanitize_parameters(aggregation_strategy="simple")
        if len(pipe.tokenizer(text, verbose=False)["input_ids"]) > 512:
            pre, _fwd, _post = pipe._sanitize_parameters(aggregation_strategy="simple", stride=256)
        return [pipe.forward(chunk) for chunk in pipe.preprocess(text, **pre)]

    def decode(self, text: str) -> dict[str, list[dict]]:
        from transformers.pipelines.token_classification import AggregationStrategy
        out = {}
        for tok_name, strategies in (("raw", RAW_STRATEGIES), ("patched", PATCHED_STRATEGIES)):
            pipe = self.pipes[tok_name]
            outs = self._outputs(pipe, text)
            for s in strategies:
                ents = pipe.postprocess(outs, aggregation_strategy=AggregationStrategy(s),
                                        ignore_labels=["O"])
                out[f"{tok_name}/{s}"] = [{"label": e["entity_group"], "start": int(e["start"]),
                                           "end": int(e["end"])} for e in ents]
        ents = self.predict._detect_entities_word_consistent(
            text, self.model, self.tok_patched, self.id2label, device=self.device)
        out["word_consistent"] = [{"label": e["label"], "start": e["start"], "end": e["end"]}
                                  for e in ents]
        return out


def load_docs(families: list[str], golden: bool) -> list[dict]:
    from scoreboard import _read_jsonl
    docs = []
    for fam in families:
        for d in _read_jsonl([HERE / "probes" / f"{fam}.jsonl"]):
            d["meta"]["family"] = fam
            docs.append(d)
    if golden:
        for d in _read_jsonl([ROOT / "data" / "golden" / "golden_az.jsonl"]):
            d["meta"]["family"] = "golden_az"
            docs.append(d)
    return docs


def run(docs: list[dict], decoder: Decoder) -> dict:
    preds: dict[str, dict[str, list]] = defaultdict(dict)
    t0 = time.time()
    for i, d in enumerate(docs, 1):
        for name, ents in decoder.decode(d["text"]).items():
            preds[name][d["id"]] = ents
        if i % 50 == 0 or i == len(docs):
            print(f"  {i}/{len(docs)}  {(time.time() - t0) / i:.2f} s/doc", flush=True)
    groups = defaultdict(list)
    for d in docs:
        groups[d["meta"]["family"]].append(d)
    res: dict = {"overall": {}, "per_family": {}}
    probe_docs = [d for d in docs if d["meta"]["family"] != "golden_az"]
    for name in DECODES:
        with_pred = lambda ds: [{**d, "pred": preds[name][d["id"]]} for d in ds]  # noqa: E731
        res["overall"][name] = score(with_pred(probe_docs))
        for fam, ds in sorted(groups.items()):
            res["per_family"].setdefault(fam, {})[name] = score(with_pred(ds))
    return res


def _p(v: float) -> str:
    return f"{100 * v:.1f}"


def render_md(res: dict, meta: dict) -> str:
    L = ["# P2-11 aggregation audit (was P3-6)", "",
         f"Checkpoint `{meta['model']}` (revision `{meta['revision'][:12]}`), CPU, git `{meta['git'][:10]}`. "
         f"{meta['n_probe_docs']} probe documents ({', '.join(meta['families'])})"
         + (f" and {meta['n_golden']} `golden_az` documents" if meta.get("n_golden") else "") + ". "
         "One network pass per document and tokenizer; every strategy decodes the same output. "
         "Public sets only (A2.5). Measurement only (D-3).", "",
         "## RC5 probes, all families together", "",
         "| Decode | Exact P | Exact R | Exact F1 | Overlap F1 | Leaked PII chars % | Boundary errors (narrower / wider / shifted) | Split values (pieces) |",
         "|---|---|---|---|---|---|---|---|"]
    for name, s in res["overall"].items():
        b, sp = s["boundary"], s["split"]
        L.append(f"| `{name}` | {_p(s['exact']['precision'])} | {_p(s['exact']['recall'])} | "
                 f"**{_p(s['exact']['f1'])}** | {_p(s['overlap']['f1'])} | {_p(s['leak_rate'])} | "
                 f"{b['n']} ({b['narrower']} / {b['wider']} / {b['shifted']}) | "
                 f"{sp['split']} of {sp['gold']} ({sp['pieces']}) |")
    L += ["", "## Per family: exact F1 / split values", "",
          "| Family | Gold | " + " | ".join(f"`{n}`" for n in DECODES) + " |",
          "|---|---|" + "---|" * len(DECODES)]
    for fam, by in res["per_family"].items():
        gold = next(iter(by.values()))["split"]["gold"]
        L.append(f"| {fam} | {gold} | " + " | ".join(
            f"{_p(by[n]['exact']['f1'])} / {by[n]['split']['split']}" for n in DECODES) + " |")
    L += ["", "## Leaked PII characters per family (%)", "",
          "| Family | " + " | ".join(f"`{n}`" for n in DECODES) + " |", "|---|" + "---|" * len(DECODES)]
    for fam, by in res["per_family"].items():
        L.append(f"| {fam} | " + " | ".join(_p(by[n]["leak_rate"]) for n in DECODES) + " |")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    import subprocess
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--families", default=",".join(RC5_FAMILIES))
    ap.add_argument("--golden", action="store_true", help="also score data/golden/golden_az.jsonl")
    ap.add_argument("--limit", type=int, default=0, help="first N documents only (smoke run)")
    ap.add_argument("--md", default=None)
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)

    families = [f for f in args.families.split(",") if f]
    docs = load_docs(families, args.golden)
    if args.limit:
        docs = docs[:args.limit]
    print(f"{len(docs)} documents; loading {args.model}")
    decoder = Decoder(args.model)
    res = run(docs, decoder)
    from scoreboard import resolve_revision
    meta = {"model": args.model, "revision": resolve_revision(args.model, None) or "",
            "git": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                                  capture_output=True, text=True).stdout.strip(),
            "families": families,
            "n_probe_docs": sum(1 for d in docs if d["meta"]["family"] != "golden_az"),
            "n_golden": sum(1 for d in docs if d["meta"]["family"] == "golden_az")}
    res["meta"] = meta
    md = render_md(res, meta)
    print(md)
    if args.md:
        Path(args.md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.md).write_text(md, encoding="utf-8")
    if args.json:
        Path(args.json).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
