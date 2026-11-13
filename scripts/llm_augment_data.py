"""Generate additional training examples via DSPy against the internal LLM.

Complements `generate_dataset.py`. The procedural generator owns structure and
volume; this owns naturalistic prose that no template produces. Output is
schema-identical and drops straight into the training pipeline -- no manual
conversion, no cleanup.

The design decision that matters, from `docs/generator_redesign_plan.md` §2.6:
**entity values are injected, not requested.** `ValueFactory` mints
checksum-valid, blocklist-screened values and the model writes text around
them. The previous version asked the model to invent PII and got Stripe test
cards, the AWS documentation key, and 555 numbers -- not a wording failure, but
the predictable result of asking a model for "an example credit card".

The full pipeline: Taxonomy -> SpecSampler (decides WHAT: broad realistic
sampling, plus some share of documents deliberately targeting a case from the
edge-case catalog) -> DSPy generation (decides HOW: one Signature, routed at
the endpoint via litellm) -> validation -> quality filtering (dedup,
leaked-PII detection, judgment-word-leak detection) -> dataset.

Credentials come from the environment, never from argv or the repo:

    export COMPANY_API_KEY='...'          # HALX_API_KEY also accepted

Typical use:

    python scripts/llm_augment_data.py --list-models
    python scripts/llm_augment_data.py --model <id> --num-examples 300
    python scripts/llm_augment_data.py --model <id> --num-examples 300 --resume

Then merge and validate before splitting:

    python scripts/validate_data.py data/raw/synthetic.jsonl \\
        data/raw/llm_augmented.jsonl --write-clean data/raw/merged.jsonl
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from piigen.config import ENTITY_TYPES, GeneratorConfig                # noqa: E402
from piigen.llm.checkpoint import state_path_for                       # noqa: E402
from piigen.llm.dspy_generate import (ConfigError, ContentError,       # noqa: E402
                                      DEFAULT_BASE_URL, ENV_BASE_URL,
                                      ENV_KEY, ENV_MODEL, DSPyGenerator,
                                      build_lm, list_models, preflight)
from piigen.llm.pipeline import (AugmentConfig, AugmentationPipeline,  # noqa: E402
                                 ResumeMismatch)
from piigen.llm.specs import DOC_TYPES, SpecSampler                    # noqa: E402
from piigen.values import ValueFactory, ValuePool                      # noqa: E402

log = logging.getLogger("piigen.llm")


def setup_logging(verbose: bool, quiet: bool) -> None:
    level = logging.DEBUG if verbose else (
        logging.WARNING if quiet else logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-7s  %(message)s",
        datefmt="%H:%M:%S",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="llm_augment_data.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    gen = p.add_argument_group("generation")
    gen.add_argument("--num-examples", "-n", type=int, default=300,
                     help="accepted examples to produce (default: 300)")
    gen.add_argument("--batch-size", type=int, default=50,
                     help="documents per checkpointed batch (default: 50)")
    gen.add_argument("--concurrency", type=int, default=5,
                     help="in-flight requests (default: 5)")
    gen.add_argument("--seed", type=int, default=42,
                     help="RNG seed; logged and stored in the checkpoint")
    gen.add_argument("--edge-case-rate", type=float, default=None,
                     help="share of documents that deliberately target one "
                          "case from the edge-case catalog instead of broad "
                          "sampling (default: GeneratorConfig.edge_case_rate, "
                          "currently 0.15)")
    gen.add_argument("--negative-only-rate", type=float, default=None,
                     help="share of documents with NO true-positive entities "
                          "at all -- only hard-negative/adversarial decoys. "
                          "1.0 = every document in this run is negative-only "
                          "(default: GeneratorConfig.negative_only_rate, "
                          "currently 0.0 -- true-positive-only policy)")
    gen.add_argument("--hard-negative-rate", type=float, default=None,
                     help="share of ALL documents carrying >=1 hard-negative "
                          "decoy; negative-only documents always carry decoys "
                          "and count towards it (P2-6 fix 4; default: "
                          "GeneratorConfig.hard_negative_rate, currently 0.0)")
    gen.add_argument("--adversarial-rate", type=float, default=None,
                     help="share of ALL documents carrying >=1 adversarial "
                          "near-miss decoy; negative-only documents count "
                          "towards it (P2-6 fix 4; default: "
                          "GeneratorConfig.adversarial_rate, currently 0.0)")
    gen.add_argument("--doc-types", default=None, metavar="TYPE[,TYPE...]",
                     help="sample only these document types, comma-separated names "
                          "from piigen/llm/specs.py DOC_TYPES (default: all of them). "
                          "D-38: batch 6 uses the published-text genres news_article, "
                          "press_release, official_notice, procurement_announcement, "
                          "court_announcement, plus legal_notice, government_form, court_filing")
    gen.add_argument("--output", "-o", default="data/raw/llm_augmented.jsonl")
    gen.add_argument("--resume", action="store_true",
                     help="continue a previous run, never regenerating work")
    gen.add_argument("--overwrite", action="store_true",
                     help="discard an existing output file and start again")
    gen.add_argument("--dump-rejects", nargs="?", const=True, default=None,
                     metavar="PATH",
                     help="write every rejected candidate (text, detected "
                          "leaks, decoys offered) to PATH as JSONL, for "
                          "diagnosing rejection reasons. Defaults to "
                          "<output>.rejects.jsonl if PATH is omitted.")

    model = p.add_argument_group("model")
    model.add_argument("--model", default=None,
                       help=f"model id (or set {ENV_MODEL}); see --list-models")
    model.add_argument("--base-url", default=None,
                       help=f"endpoint base URL (or set {ENV_BASE_URL})")
    model.add_argument("--temperature", type=float, default=0.9,
                       help="high by default: diversity matters more than "
                            "determinism here (default: 0.9)")
    # 4096 could not express the two longest length bands: `extreme` asks for
    # up to 10,000 characters, which is ~2,500 tokens of English and ~8,300 of
    # Russian/Azerbaijani. 13% of briefs were therefore impossible to satisfy
    # and were truncated into rejections.
    model.add_argument("--max-tokens", type=int, default=16384,
                       help="visible-output budget (default: 16384; the two "
                            "longest length bands need >4096)")
    model.add_argument("--timeout", type=float, default=120.0)
    model.add_argument("--max-retries", type=int, default=5,
                       help="litellm's own retry/backoff attempt count")
    model.add_argument("--no-think", action="store_true",
                       help="send chat_template_kwargs={enable_thinking: false} "
                            "-- for vLLM/SGLang-style thinking models (e.g. "
                            "wahoo-1.5-preview) that otherwise burn the whole "
                            "token budget on reasoning and return no content")
    model.add_argument("--no-preflight", action="store_true",
                       help="skip the startup check that the model returns "
                            "usable content")
    model.add_argument("--compiled", default=None,
                       help="path to a BootstrapFewShot-compiled program "
                            "state (see dspy_compile.py) to load before "
                            "generating")
    model.add_argument("--list-models", action="store_true",
                       help="GET /models and exit")

    quality = p.add_argument_group("quality")
    quality.add_argument("--similarity-threshold", type=float, default=0.82,
                         help="reject a document this Jaccard-similar to an "
                              "earlier one (default: 0.82)")
    quality.add_argument("--noise-rate", type=float, default=0.18,
                         help="share of documents given post-hoc noise")
    quality.add_argument("--no-pool-state", action="store_true",
                         help="do not share the cross-run value dedup pool")

    out = p.add_argument_group("output")
    out.add_argument("--strip-meta", action="store_true",
                     help="omit _doc_type/_register/_noise/_spec etc. from the JSONL")
    out.add_argument("--verbose", "-v", action="store_true")
    out.add_argument("--quiet", "-q", action="store_true")
    return p


def parse_doc_types(value: str | None) -> list[str] | None:
    """`--doc-types a,b,c` as a list of known document types (D-38), or None
    for all of them. An unknown name is an error, not a silent no-op: a typo
    would otherwise sample nothing of that genre."""
    if not value:
        return None
    names = [v.strip() for v in value.split(",") if v.strip()]
    unknown = sorted(set(names) - set(DOC_TYPES))
    if unknown:
        raise ValueError(f"unknown document type(s): {', '.join(unknown)}\n"
                         f"known: {', '.join(sorted(DOC_TYPES))}")
    return sorted(set(names))


def _resolve_dump_rejects(value, output: Path) -> Path | None:
    if not value:
        return None
    if value is True:
        # llm_augmented.jsonl -> llm_augmented.rejects.jsonl
        return output.with_suffix(".rejects.jsonl") if output.suffix \
            else output.with_name(output.name + ".rejects.jsonl")
    return Path(value)


def cmd_list_models(base_url: str | None) -> int:
    models = list_models(base_url)
    if not models:
        print("The endpoint returned no models.", file=sys.stderr)
        return 1
    print(f"Models available at {base_url or DEFAULT_BASE_URL}:")
    for name in models:
        print(f"  {name}")
    print(f"\nUse one with --model <id>, or set {ENV_MODEL}.")
    return 0


def print_report(rows: list, state, generator: DSPyGenerator, cfg: AugmentConfig,
                 pipeline: AugmentationPipeline) -> None:
    n = len(rows)
    line = "=" * 78
    print()
    print(line)
    print("LLM AUGMENTATION REPORT")
    print(line)

    attempted = max(1, state.attempted)
    rejected = sum(state.rejections.values())
    print(f"Requested          : {cfg.num_examples}")
    print(f"Accepted           : {n}")
    print(f"Attempted          : {state.attempted}")
    print(f"Rejected           : {rejected} "
          f"({rejected / attempted * 100:.1f}% of attempts)")
    print(f"Seed               : {cfg.seed}")
    print(f"Model              : {state.model or '<unset>'}")

    if state.rejections:
        print("\nRejection reasons:")
        for key, count in sorted(state.rejections.items(), key=lambda kv: -kv[1]):
            print(f"  {key:<44}{count:6d}  "
                  f"({count / attempted * 100:5.1f}% of attempts)")

    # Planned-but-absent labels in ACCEPTED documents. The drop is not random:
    # the model omits what is hardest to weave into prose, which is
    # systematically the rare labels augmentation exists to reinforce. A label
    # high in this table is under-delivered no matter what the entity
    # distribution below says.
    if state.dropped_labels:
        print("\nLabels planned but dropped by the model (in accepted docs):")
        for key, count in sorted(state.dropped_labels.items(),
                                 key=lambda kv: -kv[1]):
            emitted = state.label_counts.get(key, 0)
            rate = count / max(1, count + emitted) * 100
            print(f"  {key:<32}{count:6d} dropped  "
                  f"({rate:4.1f}% of planned)")

    if pipeline.pool.exhausted:
        print("\nValue pool exhaustion (label's pool too small for this "
              "volume -- values now repeat past their configured cap):")
        for key, count in sorted(pipeline.pool.exhausted.items(),
                                 key=lambda kv: -kv[1]):
            print(f"  {key:<32}{count:6d} over-cap draw(s)  "
                  f"({pipeline.pool.distinct(key)} distinct value(s) in pool)")

    if not n:
        print(line)
        return

    lengths = [len(r["text"]) for r in rows]
    mentions = sum(len(r["entities"]) for r in rows)
    print("\nDocuments:")
    print(f"  mean length      : {statistics.mean(lengths):.0f} chars")
    print(f"  median length    : {statistics.median(lengths):.0f} chars")
    print(f"  min / max        : {min(lengths)} / {max(lengths)}")
    print(f"  entity mentions  : {mentions}  ({mentions / n:.1f}/doc)")

    langs: dict = {}
    for row in rows:
        langs[row["lang"]] = langs.get(row["lang"], 0) + 1
    print("\nLanguages:")
    for lang, count in sorted(langs.items(), key=lambda kv: -kv[1]):
        print(f"  {lang:<6}{count:6d}  ({count / n * 100:5.1f}%)")

    labels: dict = {}
    for row in rows:
        for ent in row["entities"]:
            labels[ent["label"]] = labels.get(ent["label"], 0) + 1
    if labels:
        print("\nEntity distribution:")
        gen_cfg = GeneratorConfig()
        for label in ENTITY_TYPES:
            count = labels.get(label, 0)
            share = count / mentions * 100 if mentions else 0.0
            target = gen_cfg.entity_weights[label] * 100
            print(f"  {label:<30}{count:6d}{share:7.1f}%  (target {target:4.1f}%)")

    types: dict = {}
    edge_cases = 0
    for row in rows:
        key = row.get("_doc_type", "?")
        types[key] = types.get(key, 0) + 1
        if (row.get("_spec") or {}).get("edge_case"):
            edge_cases += 1
    print(f"\nDocument types ({len(types)} distinct), top 12:")
    for key, count in sorted(types.items(), key=lambda kv: -kv[1])[:12]:
        print(f"  {key:<28}{count:5d}  ({count / n * 100:4.1f}%)")
    print(f"\nEdge-case-catalog-targeted: {edge_cases}/{n} "
          f"({edge_cases / n * 100:.1f}%)")

    stats = generator.stats()
    elapsed = max(1e-6, state.elapsed_seconds)
    print("\nAPI:")
    print(f"  calls            : {stats['calls']}")
    print(f"  latency mean/p50/p95 : {stats['latency_mean']:.2f}s / "
          f"{stats['latency_p50']:.2f}s / {stats['latency_p95']:.2f}s")

    print("\nThroughput:")
    print(f"  elapsed          : {elapsed:.1f}s")
    print(f"  accepted/second  : {n / elapsed:.2f}")
    dupes = state.rejections.get("near-duplicate", 0)
    print(f"  duplicate rate   : {dupes / attempted * 100:.1f}%")

    print()
    print(pipeline.analyzer.report())


def main() -> int:
    args = build_parser().parse_args()
    setup_logging(args.verbose, args.quiet)

    if args.list_models:
        try:
            return cmd_list_models(args.base_url)
        except (ConfigError, Exception) as exc:            # noqa: BLE001
            print(f"Could not list models: {exc}", file=sys.stderr)
            return 1

    if not args.model:
        print(f"No model selected. Run --list-models, then pass --model <id> "
              f"or set {ENV_MODEL}.", file=sys.stderr)
        return 2

    # checked before the model is loaded: a typo stops the run at once
    try:
        doc_types = parse_doc_types(args.doc_types)
    except ValueError as exc:
        print(f"--doc-types: {exc}", file=sys.stderr)
        return 2

    try:
        lm = build_lm(args.model, args.base_url, temperature=args.temperature,
                      max_tokens=args.max_tokens, no_think=args.no_think,
                      num_retries=args.max_retries, timeout=args.timeout)
    except ConfigError as exc:
        print(f"Configuration error:\n{exc}", file=sys.stderr)
        return 2

    generator = DSPyGenerator(lm)
    if args.compiled:
        generator.load_compiled(args.compiled)
        log.info("loaded compiled program from %s", args.compiled)

    gen_cfg = GeneratorConfig()
    if args.edge_case_rate is not None:
        gen_cfg.edge_case_rate = args.edge_case_rate
    if args.negative_only_rate is not None:
        gen_cfg.negative_only_rate = args.negative_only_rate
    if args.hard_negative_rate is not None:
        gen_cfg.hard_negative_rate = args.hard_negative_rate
    if args.adversarial_rate is not None:
        gen_cfg.adversarial_rate = args.adversarial_rate
    gen_cfg.doc_types = doc_types
    if gen_cfg.doc_types:
        log.info("doc types: %s", ", ".join(gen_cfg.doc_types))

    cfg = AugmentConfig(
        num_examples=args.num_examples,
        batch_size=args.batch_size,
        concurrency=args.concurrency,
        seed=args.seed,
        output=Path(args.output),
        resume=args.resume,
        similarity_threshold=args.similarity_threshold,
        noise_rate=args.noise_rate,
        pool_state=None if args.no_pool_state else "data/raw/.valuepool.json",
        dump_rejects=_resolve_dump_rejects(args.dump_rejects, Path(args.output)),
    )

    out_path = Path(args.output)
    if out_path.exists() and out_path.stat().st_size and not args.resume \
            and not args.overwrite:
        print(f"{out_path} already exists and is not empty.\n"
              f"  --resume     continue it, never regenerating completed work\n"
              f"  --overwrite  discard it and start again\n"
              f"Refusing to append blindly: that would re-issue ids from zero, "
              f"skip deduplication against the existing rows, and let "
              f"--strip-meta overwrite them.", file=sys.stderr)
        return 2

    if args.overwrite and out_path.exists() and out_path.stat().st_size:
        # `--overwrite` used to truncate immediately via OutputWriter(append=
        # False), before a single document was generated. If the run was then
        # interrupted, crashed, or simply produced zero accepted documents --
        # all of which are ordinary outcomes, not edge cases -- the previous,
        # good output was already gone with nothing to show for it. .gitignore
        # already carves out `data/raw/*.bak` for exactly this; nothing ever
        # wrote one. Rename-don't-truncate closes that gap: the old file is
        # never destroyed, only ever renamed aside.
        backup = out_path.with_name(
            out_path.name + f".bak-{time.strftime('%Y%m%dT%H%M%S')}")
        out_path.rename(backup)
        state_path = state_path_for(out_path)
        if state_path.exists():
            state_path.rename(state_path_for(backup))
        print(f"--overwrite: moved the existing {out_path.name} "
              f"({backup.stat().st_size:,} bytes) to {backup.name} rather "
              f"than deleting it.", file=sys.stderr)

    random.seed(args.seed)
    log.info("seed=%d output=%s edge_case_rate=%.2f", cfg.seed, cfg.output,
             gen_cfg.edge_case_rate)

    if not args.no_preflight:
        probe_rng = random.Random(args.seed)
        probe_sampler = SpecSampler(gen_cfg, ValueFactory(probe_rng, ValuePool()),
                                    probe_rng)
        try:
            preflight(generator, probe_sampler.sample(0))
            log.info("preflight ok: %s returns usable content", generator.model)
        except (ContentError, Exception) as exc:            # noqa: BLE001
            print(f"Preflight failed for model {args.model!r}:\n{exc}\n\n"
                  f"No documents were generated. Fix the model configuration "
                  f"before starting a long run.", file=sys.stderr)
            return 2

    pipeline = AugmentationPipeline(generator, cfg, gen_cfg)

    try:
        rows, state = pipeline.run()
    except ResumeMismatch as exc:
        print(f"Cannot resume: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nInterrupted. Rerun the same command with --resume to continue.",
              file=sys.stderr)
        return 130

    if args.strip_meta:
        with cfg.output.open("w", encoding="utf-8") as handle:
            for row in rows:
                clean = {k: v for k, v in row.items() if not k.startswith("_")}
                handle.write(json.dumps(clean, ensure_ascii=False) + "\n")

    print_report(rows, state, generator, cfg, pipeline)
    print(f"\nWrote {len(rows)} example(s) to {cfg.output}")
    if cfg.dump_rejects:
        print(f"Wrote rejected candidates to {cfg.dump_rejects}")

    if len(rows) < cfg.num_examples:
        print(f"Note: produced {len(rows)} of {cfg.num_examples} requested. "
              f"Rerun with --resume to top up.", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
