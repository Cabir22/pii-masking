#!/usr/bin/env python3
"""Compile the generation program with DSPy's BootstrapFewShot.

The actual point of using DSPy instead of calling the API directly: without
this, the Signature in dspy_generate.py only ever follows hand-written
instructions zero-shot. This runs the program against a real trainset (built
by the same SpecSampler llm_augment_data.py uses), keeps whichever outputs
pass the exact same acceptance gate the pipeline uses (assemble_document, so
compilation and real generation can never quietly disagree about what "good"
means), and saves a handful as few-shot demonstrations for future calls.

Biased toward edge_case_rate=0.6 by default (vs. the pipeline's normal 0.15):
compilation should spend its budget learning to do the HARD cases right --
the collisions and near-misses -- not the easy broad-sampled majority the
model already handles fine zero-shot.

Cost note: this calls the LM roughly once per trainset example (default
--trainset-size 60 => ~60 calls).

Usage:
    export COMPANY_API_KEY='...'
    python scripts/dspy_compile.py --model wahoo-1.5-preview

    # then use the compiled program:
    python scripts/llm_augment_data.py --model wahoo-1.5-preview \\
        --compiled scripts/piigen/llm/compiled/program.json
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from piigen.config import GeneratorConfig                              # noqa: E402
from piigen.llm.dspy_generate import (ConfigError, DEFAULT_BASE_URL,   # noqa: E402
                                      ENV_BASE_URL, ENV_MODEL,
                                      DSPyGenerator, build_fields,
                                      build_lm)
from piigen.llm.pipeline import assemble_document                      # noqa: E402
from piigen.llm.specs import DocumentSpec, SpecSampler                 # noqa: E402
from piigen.values import ValueFactory, ValuePool                      # noqa: E402

DEFAULT_OUTPUT = "scripts/piigen/llm/compiled/program.json"
_INPUT_FIELDS = ["language", "doc_type", "tone_register", "length_hint",
                 "entities_to_embed", "decoys", "noise_directives",
                 "document_year", "scenario_note"]


def _fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def build_trainset(sampler: SpecSampler, n: int):
    import dspy

    trainset = []
    specs_by_index: dict[int, DocumentSpec] = {}
    for i in range(n):
        spec = sampler.sample(i)
        specs_by_index[i] = spec
        ex = dspy.Example(spec_index=str(i), **build_fields(spec)) \
            .with_inputs(*_INPUT_FIELDS)
        trainset.append(ex)
    return trainset, specs_by_index


def make_metric(specs_by_index: dict[int, DocumentSpec], gen_cfg: GeneratorConfig,
                noise_rate: float):
    def metric(example, pred, trace=None) -> bool:
        spec = specs_by_index[int(example.spec_index)]
        text = (pred.text or "").strip()
        if not text:
            return False
        return assemble_document(spec, text, gen_cfg, noise_rate).ok
    return metric


def run(args: argparse.Namespace) -> None:
    try:
        import dspy
        from dspy.teleprompt import BootstrapFewShot
    except ImportError:
        _fail("dspy is not installed. Run: .venv/bin/pip install dspy")

    lm = build_lm(args.model, args.base_url, temperature=args.temperature,
                  max_tokens=args.max_tokens, no_think=args.no_think)
    # Same reason as dspy_generate.py's DSPyGenerator.generate(): BootstrapFewShot
    # calls generator.module directly (not through DSPyGenerator.generate()'s own
    # context manager), so the adapter has to be forced here too, or compilation
    # hits the same response_format 500 real generation was fixed for.
    dspy.configure(lm=lm, adapter=dspy.ChatAdapter())
    generator = DSPyGenerator(lm)

    rng = random.Random(args.seed)
    gen_cfg = GeneratorConfig()
    gen_cfg.edge_case_rate = args.edge_case_rate
    sampler = SpecSampler(gen_cfg, ValueFactory(rng, ValuePool()), rng)

    trainset, specs_by_index = build_trainset(sampler, args.trainset_size)
    n_edge = sum(1 for s in specs_by_index.values() if s.edge_case is not None)
    print(f"Trainset: {len(trainset)} documents ({n_edge} edge-case-targeted, "
          f"{len(trainset) - n_edge} broad-sampled)")

    metric = make_metric(specs_by_index, gen_cfg, args.noise_rate)
    optimizer = BootstrapFewShot(
        metric=metric,
        max_bootstrapped_demos=args.max_bootstrapped_demos,
        max_labeled_demos=args.max_labeled_demos,
        max_rounds=args.max_rounds,
        # BootstrapFewShot's own default (5) crashes the whole run the moment
        # a 6th example fails for any reason, including a transient endpoint
        # outage that has nothing to do with our data/prompt -- watched this
        # happen for real (Wahoo 503s, litellm's own num_retries=5 exhausted
        # too). A short bad patch on the server side shouldn't cost the
        # entire compile run.
        max_errors=args.max_errors,
    )
    print("Compiling (this calls the LM roughly once per trainset example)...")
    compiled = optimizer.compile(generator.module, trainset=trainset)
    generator.module = compiled

    print(f"\nSelected {len(compiled.demos)} demo(s):")
    n_edge_demos = 0
    for d in compiled.demos:
        # spec_index (used correctly inside make_metric()) does NOT survive
        # here: a demo is built by BootstrapFewShot from the live predictor
        # TRACE (dspy/teleprompt/bootstrap.py's _bootstrap_one_example --
        # `dspy.Example(augmented=True, **inputs, **outputs)`), which only
        # ever contains the Signature's own declared fields. spec_index was
        # never one of those, so a lookup through it here always misses and
        # previously mislabeled every demo "broad-sampled" regardless of the
        # truth. scenario_note IS a real declared field, and edge_cases.py's
        # build_fields() only ever sets it to non-"none" for an edge-case
        # spec -- use that instead.
        scenario_note = d.get("scenario_note", "none")
        is_edge = scenario_note != "none"
        n_edge_demos += is_edge
        tag = f"edge case ({scenario_note.split(']')[0].lstrip('[')})" if is_edge \
            else "broad-sampled"
        print(f"  - {d.get('doc_type', '?')} / {d.get('tone_register', '?')} ({tag})")
    print(f"({n_edge_demos}/{len(compiled.demos)} demos are edge-case-targeted)")

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    compiled.save(str(out_path), save_program=False)
    print(f"\nSaved compiled program state to {out_path}")
    print(f"Use it: python scripts/llm_augment_data.py --model {args.model} "
          f"--compiled {out_path}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", default=os.environ.get(ENV_MODEL),
                  help=f"model id (or set {ENV_MODEL})")
    p.add_argument("--base-url", default=os.environ.get(ENV_BASE_URL, DEFAULT_BASE_URL))
    p.add_argument("--trainset-size", type=int, default=60)
    p.add_argument("--edge-case-rate", type=float, default=0.6,
                  help="share of the trainset that targets the edge-case "
                       "catalog rather than broad sampling (default: 0.6, "
                       "higher than the pipeline's normal 0.15 -- compilation "
                       "should focus on the hard cases)")
    p.add_argument("--noise-rate", type=float, default=0.18)
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--max-tokens", type=int, default=16384,
                  help="4096 (the old default) truncated most calls under "
                       "thinking mode -- reasoning tokens share this budget, "
                       "same reasoning as llm_augment_data.py's default")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--no-think", action="store_true")
    p.add_argument("--max-bootstrapped-demos", type=int, default=6)
    p.add_argument("--max-labeled-demos", type=int, default=6)
    p.add_argument("--max-rounds", type=int, default=1)
    p.add_argument("--max-errors", type=int, default=15,
                   help="BootstrapFewShot's own default is 5 and crashes the "
                        "whole run past that many failed examples, including "
                        "transient endpoint errors unrelated to our data -- "
                        "raised so a short bad patch (default: 15)")
    p.add_argument("--output", default=DEFAULT_OUTPUT)
    args = p.parse_args()

    if not args.model:
        _fail(f"--model is required (or set {ENV_MODEL})")

    try:
        run(args)
    except ConfigError as exc:
        _fail(str(exc))


if __name__ == "__main__":
    main()
