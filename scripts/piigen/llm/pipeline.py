"""Orchestration: sample brief -> call model -> validate -> accept or reject.

Concurrency uses a thread pool rather than asyncio. The work is IO-bound with a
small number of in-flight requests, `requests`/`urllib` are synchronous, and a
thread pool keeps the whole pipeline debuggable with ordinary stack traces. At
the target scale (hundreds of thousands of documents at concurrency 5-50) the
GIL is not the bottleneck -- the endpoint is.

Acceptance is strict. Every candidate must pass the *same* `validate_example`
gate the procedural data passes, plus the LLM-specific leak and duplicate
checks. A rejected document is never repaired by hand and never written; the
pipeline simply samples another brief. That is what makes the output file safe
to concatenate with the procedural data with no manual cleanup.
"""

from __future__ import annotations

import json
import logging
import random
import re
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..analyze import DatasetAnalyzer
from ..config import GeneratorConfig
from ..negatives import locate_decoys, planted_decoys
from ..noise import NoiseInjector
from ..provenance import GEN_VERSION
from ..resolver import complete_occurrences, planned_value_present, resolve_planned
from ..validate import span_boundary_problems, validate_example
from ..values import ValueFactory, ValuePool
from . import edge_cases as EC
from .checkpoint import (OutputWriter, RunState, decode_rng_state,
                         encode_rng_state, load_existing, load_state,
                         save_state)
from .dspy_generate import ContentError, DSPyGenerator
from .monitor import BatchMetrics, RunMonitor
from .quality import (GlobalSimilarityIndex, find_judgment_leak,
                      find_label_name_leak, find_leaked_pii,
                      normalize_for_similarity)
from .quality_filter import screen_record
from .specs import DocumentSpec, SpecSampler, steering_labels

log = logging.getLogger("piigen.llm")


class ResumeMismatch(ValueError):
    """A --resume that asks for something the run was not started with (D-38:
    other --doc-types). Raised before anything is generated."""


@dataclass
class AugmentConfig:
    """Everything the CLI can set."""

    num_examples: int = 300
    batch_size: int = 50
    concurrency: int = 5
    seed: int = 42
    output: Path = Path("data/raw/llm_augmented.jsonl")
    resume: bool = False
    similarity_threshold: float = 0.82
    # Stall guards. Without these, a run where every document is rejected
    # (bad model, wrong endpoint, a prompt the model refuses) loops forever
    # instead of failing loudly.
    attempt_multiplier: float = 8.0
    max_empty_batches: int = 6
    noise_rate: float = 0.18
    pool_state: str | None = "data/raw/.valuepool.json"
    # When set, every rejected candidate is written here as JSONL: reason,
    # text, whatever entities/leaks were detected, and the decoys offered.
    # Without this, a rejection is a one-line reason and the actual text is
    # gone -- which is why "leaked unlabeled PII: 21.7%" cannot be diagnosed
    # as a decoy-matching bug vs. genuine model invention without rerunning.
    dump_rejects: Path | None = None
    # Machine-readable per-batch health report. Written at the end of a
    # run and after any stop condition, so a halted run leaves evidence
    # rather than just a log line.
    monitor_report: Path | None = None


@dataclass
class Outcome:
    """Result of one generation attempt."""

    ok: bool
    spec: DocumentSpec
    record: dict | None = None
    reason: str = ""
    latency: float = 0.0
    attempts: int = 1
    normalized: str = ""
    labels: list = field(default_factory=list)
    # Labels that were planned for this document but never made it into the
    # text. Tracked because the drop is not random -- the model omits the
    # values that are hardest to weave into prose, which are systematically
    # the rare labels (VEHICLE, DEVICE_ID, IBAN) the augmentation exists to
    # reinforce. Without this the bias is invisible.
    dropped_labels: list = field(default_factory=list)
    # Best-effort diagnostic payload, populated even on rejection, so
    # --dump-rejects can show what actually happened instead of just why.
    text: str = ""
    entities: list = field(default_factory=list)
    leaks: list = field(default_factory=list)
    decoys: list = field(default_factory=list)


# Acceptance-rate floor and prior for batch sizing.
#
# The measurement itself was wrong before: dividing CUMULATIVE accepted rows
# by CUMULATIVE attempts mixes every prior run into this one, and on a resume
# `accepted_rows` starts at the whole existing corpus while `attempted`
# restarts near zero -- so the ratio was meaningless (0.0001 on a real
# resume, or above 1.0 in other orderings). It is now measured over this
# invocation only.
#
# The FLOOR is deliberately unchanged at 0.15. It is what actually sets the
# headroom: `need / 0.15` requests ~6.7x the shortfall, capped at batch_size
# and 3x need, so the tail of a run does not trickle one short batch at a
# time. An earlier version of this fix raised the no-data prior to 0.5, which
# measured correctly but halved the headroom and left two runs a couple of
# documents short of target. Requesting too many specs costs nothing but a
# few discarded briefs; requesting too few costs a whole extra round-trip.
_RATE_PRIOR = 0.15
_RATE_PRIOR_AFTER = 20        # attempts this run before trusting the measurement

_ID_RE = re.compile(r"^llm_(?P<lang>[a-z]{2})_(?P<index>\d{6,})$")


def parse_record_index(record_id: object) -> int | None:
    """Numeric suffix of a well-formed record id, or None.

    Validates the whole shape rather than splitting on the last underscore
    and hoping: a malformed id must not be read as index 0, because that
    would drag the resume counter backwards into already-used territory --
    exactly the failure this module's resume path exists to prevent.
    """
    if not isinstance(record_id, str):
        return None
    m = _ID_RE.match(record_id)
    return int(m.group("index")) if m else None


def next_spec_index(existing: list[dict],
                    state_next_index: int = 0) -> tuple[int, bool]:
    """Where a resumed run must start issuing spec indices.

    Returns `(index, diverged)`.

    The audited line was::

        self._spec_counter = max(self.state.next_spec_index, len(existing))

    `len(existing)` counts ACCEPTED rows. Indices are consumed by every
    attempt, accepted or not, and the corpus ran at a 67.5% acceptance rate --
    so the row count always understates the highest index actually used, and
    `state.next_spec_index` understates it too whenever the checkpoint is
    behind the output file. Resuming from either re-issues ids that already
    exist, and every collision discards a completed API call.

    Measured on this repository's own data (2026-08-25): 32,535 accepted rows
    carrying indices up to 48,595, against a checkpoint claiming 24,902
    accepted and next_spec_index=27,585. The old expression would have
    resumed at 32,535 and re-issued 16,061 used indices before reaching
    fresh ground. The corpus already carries 1,583 duplicate-id rejections
    from two earlier occurrences of this -- 50.7% of all rejections.

    The high-water mark of ids actually present is the only value that cannot
    understate what has been used, so it is the floor. The checkpoint still
    participates via `max`, so a checkpoint that ran ahead of the output
    (attempts that produced no accepted row) is never walked backwards either.
    """
    highest = -1
    malformed = 0
    for row in existing:
        idx = parse_record_index(row.get("id") if isinstance(row, dict) else None)
        if idx is None:
            malformed += 1
            continue
        highest = max(highest, idx)

    state_at = int(state_next_index or 0)
    from_output = highest + 1
    resume_at = max(state_at, from_output)
    # Divergence in EITHER direction is worth reporting, because the two mean
    # different things and both are diagnostic:
    #   output ahead  -- the dangerous one; resuming from the checkpoint would
    #                    re-issue live ids and discard completed generations.
    #   state ahead   -- benign and expected after a crash or a truncated
    #                    final write: the checkpoint counted attempts whose
    #                    rows never landed. No id is at risk, but the gap is
    #                    still evidence the two files were not written
    #                    together, which is what the monitor wants to know.
    diverged = bool(existing) and from_output != state_at

    if malformed:
        log.warning("resume: %d output row(s) had an unparseable id; they "
                    "cannot contribute to the high-water mark", malformed)
    if from_output > state_at and existing:
        log.warning(
            "resume: checkpoint/output DIVERGENCE -- checkpoint says next "
            "index %d, but the output file already contains index %d. "
            "Resuming at %d (the output high-water mark). Resuming at the "
            "checkpoint value would have re-issued %d used id(s), each one "
            "discarding a completed generation.",
            state_at, highest, resume_at, from_output - state_at)
    elif from_output < state_at and existing:
        log.warning(
            "resume: checkpoint is %d index/indices ahead of the output file "
            "(checkpoint next=%d, highest id present=%d). Harmless for id "
            "safety -- resuming at %d -- but the two files were not written "
            "together, most likely an interrupted run.",
            state_at - from_output, state_at, highest, resume_at)
    return resume_at, diverged


def assert_index_monotonic(previous: int, nxt: int) -> None:
    """Invariant: a spec index may never move backward within a run."""
    if nxt < previous:
        raise RuntimeError(
            f"spec index regressed: {previous} -> {nxt}. This is the "
            "duplicate-id defect (see next_spec_index); refusing to continue "
            "and overwrite already-issued ids.")


def _pairs(decoy_spans: list[dict]) -> list[tuple[int, int]]:
    return [(d["start"], d["end"]) for d in decoy_spans]


def assemble_document(spec: DocumentSpec, text: str, gen_cfg: GeneratorConfig,
                      noise_rate: float) -> Outcome:
    """Locate entities, apply noise, validate. No offsets from the model.

    A free function, not a method, so dspy_compile.py's BootstrapFewShot
    metric can run the exact same acceptance logic the pipeline uses at
    generation time, without needing a whole AugmentationPipeline instance.
    """
    # Normalize to NFC before any offset-based work begins. A decomposed
    # accented character (base letter + combining mark, 2 codepoints) and its
    # composed form (1 codepoint) look identical but have different lengths --
    # normalizing after entities are resolved would shift every offset past
    # the normalized character. Doing it first means every offset computed
    # below is already against the exact text that gets kept. Found by audit:
    # 1/24,085 real documents was not in NFC form.
    text = unicodedata.normalize("NFC", text)

    # Injected values are authoritative: we know their labels are right.
    # Model-supplied claims are accepted only as extra evidence for values
    # we already planned, so a mislabeled claim cannot enter the dataset.
    planned = {e.value: e.label for e in spec.entities}

    # P2-6 fix 1 (batch 1): a value the model wrote in another form --
    # `küçəsində` for `küç.`, `İsağın` for `İsaq`, capitals, no Azerbaijani
    # letters -- is present, and is labelled below (resolver.resolve_planned).
    # Counting it as missing left it in the text unlabelled.
    missing = [v for v, lab in planned.items()
               if v not in text and not planned_value_present(text, lab, v)]
    if not spec.negative_only and planned:
        # A document that dropped most of its values is not the document we
        # asked for; regenerating is cheaper than accepting a thin example.
        if len(missing) > max(1, len(planned) // 2):
            return Outcome(False, spec, text=text,
                           reason=f"missing values: {len(missing)}/{len(planned)} "
                                  "supplied values absent from text")

    # Declared decoys (C2 `_decoys`, P2-3). Located BEFORE entities are
    # resolved, so a planned value is never labeled inside one -- the planned
    # CITY `Bakı` inside the policy decoy `Bakı layihəsi` stays a project
    # name. Every gate below exempts exactly these spans and nothing else.
    decoy_spans = locate_decoys(
        text, planted_decoys(spec.anchored_decoys, spec.plain_decoys,
                             spec.hard_negatives),
        planned_values=list(planned))

    entities, dropped = resolve_planned(text, [(lab, val) for val, lab in planned.items()],
                                        blocked=_pairs(decoy_spans))
    if not entities and not spec.negative_only:
        return Outcome(False, spec, text=text, reason="no entities resolved")

    # Optional post-hoc noise, with exact offset repair.
    #
    # A per-document RNG and a per-document injector: the injector holds
    # RNG state, so sharing one across worker threads would reintroduce the
    # nondeterminism this function exists to avoid. They are cheap objects.
    #
    # `rate=` is passed explicitly because `maybe_apply` also gates on
    # `cfg.noise_rate` by default -- gating here as well multiplied the two
    # and produced 1.8% noised documents against a configured 18%.
    #
    # Declared decoys ride through protected: a typo inside one could turn a
    # proven-invalid look-alike into a valid, unlabeled value.
    noise_kinds: list = []
    rng = random.Random(spec.seed ^ 0x5EED)
    pre_noise = (text, entities, decoy_spans)
    text, entities, decoy_spans, noise_kinds = NoiseInjector(gen_cfg, rng).apply_protected(
        text, entities, decoy_spans, spec.lang, rate=noise_rate)

    # 2026-08-27 audit: the `typos` and `whitespace` kinds can split a word
    # ACROSS a span edge -- CITY "Quba" left sitting inside "Qubar egionunda".
    # Offsets are repaired after noise, so the span stays structurally valid
    # and every existing check passes; what breaks is that the span now ends
    # mid-token, which a token classifier can never reproduce. 52 such spans
    # reached the live corpus.
    #
    # Reverting the noise (rather than rejecting the document) is deliberate:
    # the un-noised text is already a perfectly good example, so throwing it
    # away would cost yield for no gain. The document simply ships clean.
    if noise_kinds and span_boundary_problems(text, entities):
        (text, entities, decoy_spans), noise_kinds = pre_noise, []

    entities, _added = complete_occurrences(text, entities, blocked=_pairs(decoy_spans))

    decoys = list(spec.hard_negatives)          # the strings, for --dump-rejects
    leaks = find_leaked_pii(text, entities, decoy_spans=decoy_spans)
    if leaks:
        return Outcome(False, spec, text=text, entities=entities,
                       leaks=leaks, decoys=decoys,
                       reason=f"leaked unlabeled PII: {leaks[0]}")

    label_leaks = find_label_name_leak(text, entities)
    if label_leaks:
        return Outcome(False, spec, text=text, entities=entities,
                       decoys=decoys,
                       reason=f"taxonomy label leaked into text: {label_leaks[0]}")

    if decoys:
        judgment = find_judgment_leak(text)
        if judgment:
            return Outcome(False, spec, text=text, entities=entities,
                           decoys=decoys,
                           reason=f"judgment leak: {judgment}")

    # A deliberately-targeted negative edge case is the whole point of the
    # document -- if its decoy never made it into the text, this is not a
    # usable negative example, it is a broken one. Organic hard_negatives
    # from ordinary broad sampling are not held to this (some are expected
    # not to survive verbatim; that has never been required there).
    if spec.edge_case is not None and EC.is_negative(spec.edge_case):
        decoy = spec.hard_negatives[0] if spec.hard_negatives else ""
        if decoy and decoy not in text:
            return Outcome(False, spec, text=text, entities=entities,
                           decoys=decoys,
                           reason=f"edge case decoy {decoy!r} not embedded")

    record = {
        "id": f"llm_{spec.lang}_{spec.index:06d}",
        "text": text,
        "lang": spec.lang,
        "entities": entities,
        # Before validate_example/screen_record: both read it.
        "_decoys": sorted(decoy_spans, key=lambda d: d["start"]),
    }

    # A negative_only document is decoy-dominated by construction -- most of
    # its content is intentionally non-linguistic (codes, hashes, IDs), not
    # prose, so language_ok's normal per-length scaling (tuned against the
    # true-positive corpus's much higher prose density) structurally
    # under-credits it. Measured live on the 2026-08-28 negative-only run:
    # genuinely Azerbaijani technical/log-style documents ("[LOG] Başladı...
    # Cəmi: 7628.79 AZN... K0D: ...") scored 0-3 native words against a
    # threshold of 4, tripping english_contamination on real Azerbaijani
    # text. First relaxed to a flat floor of 1 -- fixed 79% of that batch's
    # language rejects, but the residual (checked again after resuming) was
    # still all genuine Azerbaijani: pure log/error-style documents (doc_type
    # technical_log/config_snippet) with so little surrounding prose that
    # even 1 word of evidence isn't always there ("npm@latest xetasidir"
    # alone in an ERR_ log has no stopword or ə/distinctive-char match at
    # all). Dropped to 0 for this spec class specifically -- not a blanket
    # change, `lang` is still asserted elsewhere and only negative_only
    # documents lose this particular floor. Sanity-checked first: of the
    # 235 documents already accepted under floor=1, only 3% (7) carry zero
    # AZ-specific characters anywhere, so this was never functioning as a
    # meaningful English-drift guard for this doc class -- it was rejecting
    # real Azerbaijani almost every time it fired.
    #
    # P2-6 fix 3 (LLM batch 1, 2026-10-03): that floor of 0 is gone. The gate
    # (validate_corpus.py's validator_failure) never had it, so the 33 short
    # PII-free documents it let through all failed corpus validation and had
    # to be dropped after the API calls were paid for. Generation now applies
    # the gate's own rule -- the gate is not lowered to meet generation (A2
    # rule 4) -- and the negative-only brief asks for real Azerbaijani
    # sentences around the codes (dspy_generate.build_fields).
    problems = validate_example(record)
    if problems:
        return Outcome(False, spec, text=text, entities=entities,
                       decoys=decoys,
                       reason=f"validation: {problems[0].split('(')[0].strip()}")

    # Final screen: generation-harness artifacts, degenerate output shapes, and
    # planned PII that made it into the text but was never labeled (e.g. a
    # value followed directly by an Azerbaijani grammatical suffix --
    # "10:17-də" -- defeats resolve_claims's word-boundary check; see
    # quality_filter.check_unlabeled_planned_pii). `run_base_gates=False`
    # because everything it would re-run has already run above on this exact
    # document. `band` and `planned` are passed explicitly because `_bucket`/
    # `_spec` are only written onto the record further down, after this point.
    screen = screen_record(record, run_base_gates=False, band=spec.band,
                           planned=[(e.label, e.value) for e in spec.entities],
                           invented=True,        # D-15c: no PII the model made up
                           doc_type=spec.doc_type)   # D-51i: chat speakers count by type
    if screen:
        return Outcome(False, spec, text=text, entities=entities,
                       decoys=decoys,
                       reason=f"quality: {screen[0].split(':')[0].strip()}")

    # NOTE: the near-duplicate check deliberately does NOT happen here.
    # `_assemble` runs in a worker thread, and `SimilarityIndex` is only
    # updated when a document is accepted -- so checking here would compare
    # every member of a batch against an index that does not yet contain
    # any of its siblings, letting a whole batch of near-identical
    # documents through. It is done serially in `run()` instead, which is
    # also what makes the index safe without a lock.
    normalized = normalize_for_similarity(text, entities)

    record["_doc_type"] = spec.doc_type
    record["_bucket"] = spec.band
    record["_register"] = spec.register
    record["_noise"] = noise_kinds
    # Count decoys/adversarials that actually SURVIVED into the text, not
    # the number requested. The previous code recorded the request count
    # for hard negatives and a hardcoded 0 for adversarials, so the
    # analyzer's "adversarials" metric could never read anything but zero.
    record["_hard_negatives"] = sum(1 for d in spec.hard_negatives if d in text)
    record["_adversarials"] = sum(1 for d in spec.adversarials if d in text)
    record["_source"] = "llm"
    # The code this process imported (C2): a long-running generator keeps its
    # old code in memory after a merge, and this is how its records say so.
    record["_gen_version"] = GEN_VERSION
    # A deliberately PII-free document (D-1), so a gate can tell it from a
    # document that lost its entities by accident (validate_corpus.py).
    record["_pii_free"] = bool(spec.negative_only)
    # The brief that produced this record -- entity label/value pairs,
    # decoy strings, formatting directives, register, length band. Not
    # reconstructable from the final record alone (e.g. decoy strings and
    # noise directives leave no trace in `text`/`entities`), and DSPy's
    # BootstrapFewShot needs real input->output pairs, not just outputs.
    # `--strip-meta` already drops every `_`-prefixed key generically, so
    # this needs no special-casing there.
    record["_spec"] = asdict(spec)

    dropped_labels = [planned[v] for v in missing]
    return Outcome(True, spec, record=record, normalized=normalized,
                   labels=steering_labels(entities, spec),   # D-17: not the document date
                   dropped_labels=dropped_labels)


# Minimum expected mentions of a label before its share drift is judged.
DRIFT_MIN_EXPECTED = 30


class AugmentationPipeline:
    def __init__(self, generator: DSPyGenerator, cfg: AugmentConfig,
                 gen_cfg: GeneratorConfig | None = None) -> None:
        self.generator = generator
        self.cfg = cfg
        self.gen_cfg = gen_cfg or GeneratorConfig()
        self.rng = random.Random(cfg.seed)

        self.pool = ValuePool(max_share=self.gen_cfg.max_value_share,
                              state_path=cfg.pool_state)
        self.factory = ValueFactory(self.rng, self.pool,
                                    self.gen_cfg.password_keyword_share)
        self.sampler = SpecSampler(self.gen_cfg, self.factory, self.rng)
        self.noiser = NoiseInjector(self.gen_cfg, self.rng)
        # Global, not windowed. `SimilarityIndex` only compares against the
        # last 600 accepted documents, so it is structurally incapable of
        # catching a duplicate pair separated by more than that -- a failure
        # mode that is silent and gets likelier as the corpus grows.
        self.similarity = GlobalSimilarityIndex(
            threshold=cfg.similarity_threshold)
        self.analyzer = DatasetAnalyzer(self.gen_cfg)

        self.state = RunState(model=generator.model, seed=cfg.seed,
                              requested=cfg.num_examples,
                              doc_types=self.gen_cfg.doc_types)
        self.seen_ids: set = set()
        self._lock = threading.Lock()
        self._spec_counter = 0
        self._highest_issued = -1
        self._resume_diverged = False
        self._divergence_batches = 0
        self._start = 0.0
        self.monitor = RunMonitor(report_path=cfg.monitor_report)

    # -- resume -----------------------------------------------------------
    def _prepare_resume(self) -> list[dict]:
        """Rebuild in-memory indexes from a previous run's output."""
        existing = load_existing(self.cfg.output)
        if not existing:
            return []

        prior = load_state(self.cfg.output)
        if prior and sorted(prior.doc_types or []) != sorted(self.gen_cfg.doc_types or []):
            raise ResumeMismatch(
                f"this run was started with --doc-types {','.join(prior.doc_types or []) or '(all)'}, "
                f"the resume asks for {','.join(self.gen_cfg.doc_types or []) or '(all)'}; "
                f"resume with the same --doc-types")
        if prior:
            self.state = prior
            self.state.requested = self.cfg.num_examples
        self.state.accepted = len(existing)

        # 2026-08-26: restore the sampler's actual random state, not just
        # next_spec_index (a document-numbering counter only -- see its
        # docstring). Without this, every resume re-seeds random.Random(seed)
        # and starts drawing from the beginning of that seed's sequence
        # again, regardless of how far a prior invocation (this machine or
        # another) had already walked it -- silently absorbed by the
        # near-duplicate detector until two runs' fresh restarts overlap
        # enough to spike a batch's near-duplicate rate and trip
        # acceptance_rate's stop condition, which is what surfaced this.
        # self.rng is the SAME object self.factory/self.sampler/self.noiser
        # already hold a reference to, so mutating it here (before any
        # sampling has happened this run) takes effect for all of them.
        if self.state.rng_state is not None:
            try:
                self.rng.setstate(decode_rng_state(self.state.rng_state))
            except (TypeError, ValueError) as exc:
                log.warning("could not restore rng_state (%s); continuing "
                            "with a freshly-seeded generator, matching "
                            "pre-fix behaviour", exc)

        # 2026-08-26: restore the rate-smoothing history too, for the same
        # reason as rng_state above -- without this, batch 1 of every
        # resume is judged on its own single-batch sample again, which is
        # exactly the false-stop pattern the smoothing fix (monitor.py)
        # exists to prevent. Nothing else holds a reference to the
        # just-constructed self.monitor yet, so replacing it outright
        # (matching how self.state is replaced above, not mutated) is safe.
        self.monitor = RunMonitor(report_path=self.cfg.monitor_report,
                                  smoothing_state=self.state.rate_smoothing)

        for row in existing:
            self.seen_ids.add(row.get("id", ""))
            entities = row.get("entities", [])
            normalized = normalize_for_similarity(row["text"], entities)
            self.similarity.add(normalized, row.get("id", ""))
            self.analyzer.add(row)
            # D-17: the planned document date is outside the label mix
            self.sampler.record(steering_labels(entities, row.get("_spec")),
                                row.get("lang", ""), row.get("_doc_type", ""))

        # Ensure new specs cannot collide with old ids. Derived from the
        # highest id actually present, not the accepted-row count -- see
        # next_spec_index for why the row count is always an undercount.
        self._spec_counter, diverged = next_spec_index(
            existing, self.state.next_spec_index)
        self._resume_diverged = diverged
        if diverged:
            self.state.rejections.setdefault("checkpoint divergence", 0)
            self.state.rejections["checkpoint divergence"] += 1
        log.info("Resuming: %d example(s) already accepted in %s; "
                 "next spec index %d", len(existing), self.cfg.output,
                 self._spec_counter)
        return existing

    # -- one document -----------------------------------------------------
    def _next_spec(self) -> DocumentSpec:
        with self._lock:
            index = self._spec_counter
            assert_index_monotonic(self._highest_issued, index)
            self._highest_issued = index
            self._spec_counter += 1
        return self.sampler.sample(index)

    def _generate_one(self, spec: DocumentSpec) -> Outcome:
        """Call the model and validate.

        Runs in a worker thread, so it must not touch `self.rng`: a shared
        `random.Random` consumed from several threads is not corrupted (the GIL
        makes each draw atomic) but the interleaving is nondeterministic, which
        silently voids `--seed`. Everything stochastic here derives from
        `spec.seed`.

        No repair-on-bad-envelope retry loop here (the old client.py path had
        one): DSPy's adapter parses its own field structure natively, so the
        envelope-format failures that loop existed for are structurally
        impossible now. A content-level rejection (missing values, a leak) is
        cheaper to recover from by sampling a fresh spec in the outer batch
        loop than by re-prompting this one.
        """
        started = time.monotonic()
        try:
            text = self.generator.generate(spec)
        except ContentError as exc:
            return Outcome(False, spec, reason=f"api: {exc}",
                           latency=time.monotonic() - started, attempts=1)
        except Exception as exc:                          # noqa: BLE001
            return Outcome(False, spec, reason=f"api: {type(exc).__name__}: {exc}",
                           latency=time.monotonic() - started, attempts=1)

        outcome = self._assemble(spec, text)
        outcome.latency = time.monotonic() - started
        outcome.attempts = 1
        return outcome

    def _assemble(self, spec: DocumentSpec, text: str) -> Outcome:
        return assemble_document(spec, text, self.gen_cfg, self.cfg.noise_rate)

    # -- monitoring -------------------------------------------------------
    def _observe_batch(self, batch_no: int, results: list, fresh: list,
                       accepted_rows: list, write_failures: int,
                       batch_seconds: float) -> str:
        """Score this batch against the stop conditions."""
        reasons = [(o.reason or "") for o in results if not o.ok]

        def count(prefix: str) -> int:
            return sum(1 for r in reasons if r.startswith(prefix))

        # Label-share drift, measured against the configured targets. Only
        # meaningful once enough mentions have accumulated for a share to be
        # a share rather than noise.
        # A label is judged only once it is EXPECTED at least
        # DRIFT_MIN_EXPECTED times: at 500 mentions a 0.6% label (ICCID) is
        # expected ~3 times, so one or two extra draws read as a 3x "drift"
        # and halted a real run (2026-10-02, batch 6). Common labels are
        # judged from 500 mentions as before; rare ones a little later.
        drift: dict = {}
        total_mentions = self.sampler.total_mentions
        if total_mentions >= 500:
            for label, target in self.gen_cfg.entity_weights.items():
                if not target or target * total_mentions < DRIFT_MIN_EXPECTED:
                    continue
                actual = self.sampler.label_counts.get(label, 0) / total_mentions
                drift[label] = actual / target

        pool_health = self.pool.health_report()
        # judged_share, not over_cap_share: for FINITE_BY_NATURE labels
        # (CITY/ZIPCODE/AGE) raw over_cap_share runs near 100% by
        # construction regardless of health -- see values.py's ValuePool
        # for the full reasoning. judged_share is whichever metric that
        # label's status was actually decided on.
        worst_over_cap = max(
            (h["judged_share"] for h in pool_health["labels"].values()),
            default=0.0)

        elapsed = max(1e-6, time.monotonic() - self._start)
        metrics = BatchMetrics(
            batch_no=batch_no,
            attempted=len(results),
            accepted=len(fresh),
            span_mismatch=count("validation: ") and sum(
                1 for r in reasons if "text/offset mismatch" in r) or 0,
            forbidden_label=sum(1 for r in reasons
                                if "invalid label" in r
                                or "REMOVED label" in r),
            duplicate_id_rejects=count("duplicate id"),
            near_duplicate_rejects=count("near-duplicate"),
            validator_rejects=count("validation"),
            api_errors=count("api"),
            english_rejects=sum(1 for r in reasons if "language:" in r),
            output_write_failure=write_failures,
            pool_over_cap_share=worst_over_cap,
            pool_stop_labels=pool_health["stop_labels"],
            label_share_drift=drift,
            throughput_per_hour=len(accepted_rows) / elapsed * 3600.0,
            checkpoint_divergence_batches=self._divergence_batches,
            mean_text_length=(
                sum(len(r["text"]) for r in fresh) / len(fresh)
                if fresh else 0.0),
            elapsed=batch_seconds,
            total_attempted=self.state.attempted,
            total_mentions=total_mentions,
            total_pool_draws=sum(self.pool.draws.values()),
        )
        # Count only UNRESOLVED divergence. The one-off gap found at resume
        # time is reconciled by next_spec_index before the first batch runs,
        # so counting it every batch would halt a perfectly healthy resumed
        # run after three batches. What matters here is the checkpoint
        # failing to track the output file *during* the run, which means a
        # crash would lose more than the last batch.
        if self.state.accepted != len(accepted_rows):
            self._divergence_batches += 1
            log.warning(
                "checkpoint has not kept up with the output file: state "
                "says %d accepted, %d row(s) written",
                self.state.accepted, len(accepted_rows))
        else:
            self._divergence_batches = 0
        return self.monitor.observe(metrics)

    # -- batch loop -------------------------------------------------------
    def run(self) -> tuple[list[dict], RunState]:
        cfg = self.cfg
        self._start = time.monotonic()
        accepted_rows: list[dict] = []

        if cfg.resume:
            accepted_rows = self._prepare_resume()

        remaining = cfg.num_examples - len(accepted_rows)
        if remaining <= 0:
            log.info("Nothing to do: %d/%d already accepted.",
                     len(accepted_rows), cfg.num_examples)
            return accepted_rows, self.state

        log.info("Generating %d example(s) | batch=%d concurrency=%d "
                 "model=%s seed=%d",
                 remaining, cfg.batch_size, cfg.concurrency,
                 self.generator.model or "<unset>", cfg.seed)

        # Only append when resuming. Appending to a file this run did not read
        # re-issues ids from 0 (the spec counter restarts), skips every dedup
        # check against the existing rows, and leaves `--strip-meta` about to
        # rewrite the file from memory -- silently destroying the earlier run.
        writer = OutputWriter(cfg.output, append=cfg.resume)
        reject_handle = None
        if cfg.dump_rejects:
            cfg.dump_rejects.parent.mkdir(parents=True, exist_ok=True)
            # Always fresh, even under --resume: a rejects file is a diagnostic
            # sample of THIS invocation's model behaviour, not a ledger that
            # needs to survive across runs the way the output file does.
            reject_handle = cfg.dump_rejects.open("w", encoding="utf-8")
        batch_no = 0
        interrupted = False
        empty_batches = 0
        # Budget the attempts THIS invocation may spend, not the lifetime total.
        # `state.attempted` is restored on resume, so a cumulative comparison
        # made a resumed run abort instantly while reporting a stall it never
        # had ("5000 attempts for 20 accepted exceeds the budget (200)").
        attempts_at_start = self.state.attempted
        rows_at_start = len(accepted_rows)
        attempt_budget = max(remaining * cfg.attempt_multiplier,
                             cfg.batch_size * 2)

        try:
            while len(accepted_rows) < cfg.num_examples:
                spent = self.state.attempted - attempts_at_start
                if spent >= attempt_budget:
                    log.error(
                        "Stopping: %d attempts this run for %d accepted "
                        "example(s) exceeds the budget (%.0f). Top rejection "
                        "reasons: %s", spent, len(accepted_rows),
                        attempt_budget, self._top_rejections())
                    break
                if empty_batches >= cfg.max_empty_batches:
                    log.error(
                        "Stopping: %d consecutive batches produced nothing. "
                        "Top rejection reasons: %s",
                        empty_batches, self._top_rejections())
                    break
                batch_no += 1
                need = cfg.num_examples - len(accepted_rows)
                # Over-request against the observed acceptance rate so the tail
                # of a run does not trickle one short batch at a time. Capped
                # at batch_size, and never more than 3x the shortfall.
                # Measure the acceptance rate over THIS invocation only.
                # Dividing cumulative accepted rows by cumulative attempts
                # mixes in every prior run: on a resume, `accepted_rows`
                # starts at the full existing corpus while `attempted`
                # restarts near zero, so the ratio reads far above 1.0 and
                # the inflation does nothing. Worse, once duplicate-id
                # collisions depressed the rate (they were 50.7% of all
                # rejections), the shortfall got *smaller* batches exactly
                # when it needed larger ones.
                accepted_this_run = len(accepted_rows) - rows_at_start
                spent_this_run = self.state.attempted - attempts_at_start
                if spent_this_run >= _RATE_PRIOR_AFTER:
                    accept_rate = accepted_this_run / spent_this_run
                else:
                    # Not enough evidence yet. Assume a conservative rate
                    # rather than a perfect one: the whole purpose of
                    # inflating is headroom for rejections, and requesting
                    # exactly `need` on the first batch guarantees a second
                    # round-trip for the tail of every run.
                    accept_rate = _RATE_PRIOR
                accept_rate = max(0.15, min(1.0, accept_rate))
                inflated = need / accept_rate
                size = int(min(cfg.batch_size, max(1, need * 3), max(1, inflated)))
                specs = [self._next_spec() for _ in range(size)]

                batch_started = time.monotonic()
                results = self._run_batch(specs)

                fresh: list[dict] = []
                for outcome in results:
                    self.state.attempted += 1
                    # `outcome.attempts` is always 1: this pipeline has no
                    # re-prompt loop, and litellm's internal retries are not
                    # exposed per call. The counter is kept (the state schema
                    # is versioned and read by older reports) but it can only
                    # ever be 0, so nothing should read it as evidence that
                    # no retry happened. See DSPyGenerator.stats().
                    self.state.api_retries += max(0, outcome.attempts - 1)
                    if not outcome.ok or outcome.record is None:
                        key = outcome.reason.split(":")[0].strip() or "unknown"
                        self.state.rejections[key] = \
                            self.state.rejections.get(key, 0) + 1
                        log.debug("rejected [%s] %s", outcome.spec.doc_type,
                                  outcome.reason)
                        if reject_handle is not None:
                            _write_reject(reject_handle, outcome)
                        continue
                    record = outcome.record
                    if record["id"] in self.seen_ids:
                        self.state.rejections["duplicate id"] = \
                            self.state.rejections.get("duplicate id", 0) + 1
                        # This was the single largest rejection class in the
                        # audited corpus (1,583 = 50.7%) and the only one that
                        # never reached --dump-rejects, which is why it went
                        # undiagnosed. A discarded completed generation is
                        # exactly what a rejects dump is for.
                        if reject_handle is not None:
                            outcome.reason = (
                                f"duplicate id: {record['id']} already present "
                                "in output (resume index collision)")
                            outcome.text = record["text"]
                            outcome.entities = record["entities"]
                            _write_reject(reject_handle, outcome)
                        continue

                    # Serial duplicate check: compares against everything
                    # accepted so far, including earlier members of this batch.
                    is_dupe, score, match_id = self.similarity.check(
                        outcome.normalized)
                    if is_dupe:
                        self.state.rejections["near-duplicate"] = \
                            self.state.rejections.get("near-duplicate", 0) + 1
                        log.debug("rejected near-duplicate (jaccard %.2f, matches %s)", score, match_id or "<unknown>")
                        if reject_handle is not None:
                            outcome.reason = (
                                f"near-duplicate: jaccard={score:.2f} "
                                f"matches={match_id or '<unknown>'}")
                            outcome.text = record["text"]
                            outcome.entities = record["entities"]
                            _write_reject(reject_handle, outcome)
                        continue

                    self.seen_ids.add(record["id"])
                    self.similarity.add(outcome.normalized, record["id"])
                    for lab in outcome.dropped_labels:
                        self.state.dropped_labels[lab] = \
                            self.state.dropped_labels.get(lab, 0) + 1
                    self.sampler.record(outcome.labels, record["lang"],
                                        outcome.spec.doc_type)
                    # Realized-vs-target drift (2026-08-27 audit): a document
                    # may ship having silently dropped up to half its planned
                    # values, so the corpus's label mix diverges from the
                    # configured entity_weights with nothing aggregating it.
                    self.monitor.record_label_outcome(
                        [e.label for e in outcome.spec.entities],
                        [e["label"] for e in record["entities"]])
                    self.analyzer.add(record)
                    fresh.append(record)
                    if len(accepted_rows) + len(fresh) >= cfg.num_examples:
                        break

                write_failures = 0
                if fresh:
                    try:
                        writer.write_many(fresh)
                    except OSError as exc:
                        # Disk full, permissions, a vanished directory. The
                        # rows are already accepted in memory; losing them
                        # silently is the one outcome worth halting for.
                        write_failures = 1
                        log.error("output write FAILED for %d row(s): %s",
                                  len(fresh), exc)
                        raise
                    accepted_rows.extend(fresh)
                    empty_batches = 0
                else:
                    empty_batches += 1

                self._checkpoint(accepted_rows)
                # 2026-08-26: was only saved once, in the `finally` block
                # below -- durable on a clean exit or a caught
                # KeyboardInterrupt, but NOT on an abrupt kill (crash,
                # force-quit, terminal closed), unlike the output file and
                # checkpoint just above, which are durable every batch.
                # Confirmed as the cause of a real false CITY-concentration
                # stop: after repeated interrupted runs, .valuepool.json had
                # only 3,163 of the real corpus's 10,582 CITY draws on
                # record (health() judging concentration against a stale,
                # unrepresentative 30% slice, not the true distribution,
                # which was a healthy 8.5% top share). Saving every batch
                # closes the same durability gap the checkpoint already
                # closed for the output file.
                try:
                    self.pool.save()
                except OSError as exc:                     # noqa: BLE001
                    log.warning("could not persist the value pool: %s", exc)
                self._log_batch(batch_no, len(fresh), len(results),
                                len(accepted_rows),
                                time.monotonic() - batch_started)

                # --- health monitoring and stop conditions -----------------
                status = self._observe_batch(
                    batch_no, results, fresh, accepted_rows,
                    write_failures, time.monotonic() - batch_started)
                if status == "stop":
                    log.error(
                        "Halting after batch %d on a stop condition. The "
                        "batch just completed has been written and "
                        "checkpointed; nothing is lost. Reasons:\n  - %s",
                        batch_no, "\n  - ".join(self.monitor.stop_reasons))
                    break

                if not fresh and results:
                    log.warning("Batch %d produced nothing (%d/%d empty in a "
                                "row). Top reasons: %s", batch_no,
                                empty_batches, cfg.max_empty_batches,
                                self._top_rejections())

        except KeyboardInterrupt:
            interrupted = True
            log.warning("Interrupted. %d example(s) saved; rerun with --resume "
                        "to continue.", len(accepted_rows))
        finally:
            writer.close()
            if reject_handle is not None:
                reject_handle.close()
            self._checkpoint(accepted_rows)
            # Persist the value pool. Loading it without saving meant the
            # documented "deduplicated across runs" guarantee held for the
            # procedural generator and silently did not for augmentation.
            try:
                self.pool.save()
            except OSError as exc:                     # noqa: BLE001
                log.warning("could not persist the value pool: %s", exc)
            # A halted or interrupted run must leave machine-readable
            # evidence, not only a log line that scrolls away.
            try:
                written = self.monitor.write_report()
                if written:
                    log.info("monitor report written to %s", written)
            except OSError as exc:            # noqa: BLE001
                log.warning("could not write the monitor report: %s", exc)

        if interrupted:
            raise KeyboardInterrupt
        return accepted_rows, self.state

    def _run_batch(self, specs: list[DocumentSpec]) -> list[Outcome]:
        """Run a batch concurrently, return results in SPEC order.

        Sorting matters for reproducibility. `as_completed` yields in network-
        completion order, and the accept loop stops as soon as the target is
        met -- so without this, which documents survive depends on latency
        jitter rather than on the seed. Fixing the RNG alone does not make a
        run reproducible; this is the other half.
        """
        outcomes: list[Outcome] = []
        with ThreadPoolExecutor(max_workers=self.cfg.concurrency) as pool:
            futures = {pool.submit(self._generate_one, s): s for s in specs}
            for future in as_completed(futures):
                try:
                    outcomes.append(future.result())
                except Exception as exc:               # noqa: BLE001
                    log.exception("worker raised")
                    outcomes.append(Outcome(False, futures[future],
                                            reason=f"worker: {type(exc).__name__}"))
        outcomes.sort(key=lambda o: o.spec.index)
        return outcomes

    def _top_rejections(self, k: int = 3) -> str:
        top = sorted(self.state.rejections.items(), key=lambda kv: -kv[1])[:k]
        return ", ".join(f"{key}={count}" for key, count in top) or "none"

    def _checkpoint(self, accepted_rows: list[dict]) -> None:
        stats = self.generator.stats()
        self.state.accepted = len(accepted_rows)
        self.state.next_spec_index = self._spec_counter
        self.state.rng_state = encode_rng_state(self.rng)
        self.state.rate_smoothing = self.monitor.export_smoothing_state()
        self.state.model = self.generator.model
        self.state.label_counts = dict(self.sampler.label_counts)
        self.state.lang_counts = dict(self.sampler.lang_counts)
        self.state.doc_type_counts = dict(self.sampler.doc_type_counts)
        self.state.prompt_tokens = stats["prompt_tokens"]
        self.state.completion_tokens = stats["completion_tokens"]
        self.state.api_calls = stats["calls"]
        self.state.elapsed_seconds = time.monotonic() - self._start
        save_state(self.cfg.output, self.state)

    def _log_batch(self, batch_no: int, accepted: int, attempted: int,
                   total: int, seconds: float) -> None:
        target = self.cfg.num_examples
        elapsed = max(1e-6, time.monotonic() - self._start)
        rate = total / elapsed
        eta = (target - total) / rate if rate > 0 else 0.0
        accept_pct = (accepted / attempted * 100) if attempted else 0.0
        log.info(
            "batch %-4d | +%3d/%-3d (%5.1f%% accepted) | total %d/%d (%4.1f%%) "
            "| %.2f doc/s | batch %.1fs | ETA %s",
            batch_no, accepted, attempted, accept_pct, total, target,
            total / target * 100, rate, seconds, _fmt_eta(eta))


def _write_reject(handle, outcome: Outcome) -> None:
    """One JSON line per rejected candidate, for --dump-rejects.

    Text is truncated to keep the file skimmable; the point is triage across
    hundreds of rejections, not a byte-perfect record (the checkpoint/output
    file already keeps everything that was accepted).
    """
    row = {
        "doc_type": outcome.spec.doc_type,
        "lang": outcome.spec.lang,
        "band": outcome.spec.band,
        "reason": outcome.reason,
        "text": outcome.text[:4000],
        "entities": outcome.entities,
        "leaks": outcome.leaks,
        "decoys": outcome.decoys,
    }
    handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _fmt_eta(seconds: float) -> str:
    if seconds <= 0 or seconds != seconds:
        return "--"
    seconds = int(seconds)
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h{minutes:02d}m"
    if minutes:
        return f"{minutes}m{secs:02d}s"
    return f"{secs}s"
