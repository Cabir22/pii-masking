"""Unit and integration tests for the LLM augmentation pipeline.

No network access. `FakeGenerator` duck-types `DSPyGenerator`'s interface
(`.model`, `.generate(spec) -> str`, `.stats()`, `.load_compiled()`) and
synthesizes a plausible document directly from the `DocumentSpec` it is
handed -- which lets the entire pipeline (sampling, assembly, validation,
dedupe, checkpointing, resume) run end to end deterministically.

That the fake is this simple is itself a consequence of the DSPy migration:
the old fake had to regex-parse injected values back out of a rendered prompt
string, because that was the only channel `BaseLLMClient.complete()` had.
`DSPyGenerator.generate(spec)` takes the spec directly, so the fake reads
`spec.entities`/`spec.hard_negatives` like any other caller would.

Run:  python scripts/test_llm_augment.py
"""

from __future__ import annotations

import collections
import dataclasses
import random
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from piigen.config import GeneratorConfig                              # noqa: E402
from piigen.locales import LOCALES                                     # noqa: E402
from piigen.llm import edge_cases as EC                                # noqa: E402
from piigen.llm.checkpoint import (OutputWriter, RunState, decode_rng_state,  # noqa: E402
                                   encode_rng_state, load_existing,
                                   load_state, save_state, state_path_for)
from piigen.llm.dspy_generate import ContentError, build_fields        # noqa: E402
from piigen.llm.pipeline import AugmentConfig, AugmentationPipeline, assemble_document  # noqa: E402
from piigen.llm.quality import (SimilarityIndex, find_judgment_leak,   # noqa: E402
                                find_label_name_leak, find_leaked_pii,
                                normalize_for_similarity)
from piigen.llm.specs import NAME_SHAPE_ROLES, SpecSampler             # noqa: E402
from piigen.resolver import resolve_claims                             # noqa: E402
from piigen.values import ValueFactory, ValuePool                      # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []
SKIPPED: list[str] = []


def check(cond: bool, name: str, detail: object = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(f"{name}: {detail}")


# ---------------------------------------------------------------------------
# Fake generator
# ---------------------------------------------------------------------------

_LABEL_KEY = {
    "GIVENNAME": "name", "SURNAME": "name", "EMAIL": "email",
    "TELEPHONENUM": "phone", "DATE": "date", "AZ_FIN": "id",
    "PAYMENT_CARD_NUMBER": "card", "IBAN": "account",
    "IPV4_ADDRESS": "ip", "IPV6_ADDRESS": "ip", "PRIVATE_KEY": "password",
}


class FakeGenerator:
    """Builds a plausible document containing exactly the injected values."""

    def __init__(self, *, fail_first: int = 0, empty_every: int = 0,
                 leak: bool = False, duplicate: bool = False,
                 drop_values: bool = False, seed: int = 1) -> None:
        self.model = "fake-model"
        self.fail_first = fail_first
        self.empty_every = empty_every
        self.leak = leak
        self.duplicate = duplicate
        self.drop_values = drop_values
        self.seed = seed
        self.calls = 0
        self.last_spec = None
        self.latencies: list[float] = []

    def load_compiled(self, path: str) -> None:                        # pragma: no cover
        pass

    def stats(self) -> dict:
        return {"calls": self.calls, "retries": 0, "prompt_tokens": 0,
                "completion_tokens": 0, "total_tokens": 0,
                "latency_mean": 0.0, "latency_p50": 0.0, "latency_p95": 0.0}

    def generate(self, spec) -> str:
        self.calls += 1
        self.last_spec = spec
        if self.calls <= self.fail_first:
            raise ContentError("simulated failure")
        if self.empty_every and self.calls % self.empty_every == 0:
            raise ContentError("model returned empty text")

        loc = LOCALES[spec.lang]
        # Keyed on the SPEC, never on `self.calls`. `self.calls` is a shared
        # counter bumped from every worker thread, so under concurrency the
        # same spec drew a different rng seed on each run -- different body
        # text, different length, different quality verdict, and therefore a
        # different set of accepted ids. That made F2/N7 (the determinism
        # regressions) fail against a pipeline that was in fact
        # deterministic: the fixture was the only nondeterministic part.
        # This matches the contract the pipeline documents for real
        # generators -- everything stochastic derives from `spec.seed`.
        rng = random.Random(
            0 if self.duplicate else self.seed * 1000 + spec.seed)

        if self.duplicate:
            # A long, VARIED fixed body. Length alone is not enough: shingles
            # are a set, so repeating one sentence adds no new n-grams and the
            # differing entity lines still dominate the union.
            body = " ".join(
                loc.phrases.sentences(register, random.Random(0), 3)
                for register in ("note", "policy", "shipping", "confirmation")
            ) + "\n"
        else:
            body = loc.phrases.sentences("note", rng, 2) + ".\n"

        for i, ent in enumerate(spec.entities):
            if self.drop_values and i > 0:
                continue
            # D-17: about 60% of briefs now plan the document's own date. In
            # `duplicate` mode that extra line alone made skeletons differ,
            # and this mode tests the similarity index on identical ones.
            if self.duplicate and getattr(ent, "role", "") == "document_date":
                continue
            body += f"{loc.label(_LABEL_KEY.get(ent.label, 'reference'))}: {ent.value}\n"

        # Decoys, as the Signature demands: present in the text, absent from
        # entities. Skipped in `duplicate` mode -- normalize_for_similarity
        # masks entity spans and digits but NOT decoy text, so varying decoys
        # make two otherwise-identical skeletons look less alike than they are
        # (a real, documented limitation of the similarity index; this mode
        # exists to test the index, so it must not also be testing that).
        if not self.duplicate:
            for decoy in spec.hard_negatives:
                body += f"{loc.label('reference')}: {decoy}\n"
            body += loc.phrases.sentences("closing", rng, 1) + "\n"
            body += loc.phrases.sentences("policy", rng, 2) + "."

        # Pad toward the requested band. Without this the fake generator emits
        # the same ~3 sentences whether the spec asked for 40 characters or
        # 10,000, which no real generation does (the real model respected its
        # band in 1000/1000 documents of the reference batch) -- and a "long"
        # brief answered with three sentences is a value-dump by
        # quality_filter's carrier-word measure, so the fixture, not the
        # model, would be what fails the gate.
        if not self.duplicate:
            guard = 0
            while len(body) < spec.min_chars and guard < 60:
                body += "\n" + loc.phrases.sentences("note", rng, 2) + "."
                guard += 1

        if self.leak:
            body += "\nAlso contact sneaky.leak@notlisted.example.org for more."

        return body


# ---------------------------------------------------------------------------
print("1. Configuration parsing")
# ---------------------------------------------------------------------------
import llm_augment_data as cli                                    # noqa: E402

parser = cli.build_parser()
args = parser.parse_args([])
check(args.num_examples == 300, "default num-examples is 300", args.num_examples)
check(args.batch_size == 50, "default batch size 50", args.batch_size)
check(args.concurrency == 5, "default concurrency 5", args.concurrency)
check(args.edge_case_rate is None, "edge-case-rate unset by default falls back "
      "to GeneratorConfig", args.edge_case_rate)

args = parser.parse_args(["--num-examples", "1000", "--batch-size", "10",
                          "--concurrency", "20", "--seed", "7",
                          "--temperature", "0.5", "--max-tokens", "2048",
                          "--model", "m1", "--resume", "--edge-case-rate", "0.3",
                          "--output", "/tmp/x.jsonl"])
check(args.num_examples == 1000 and args.batch_size == 10, "overrides parse")
check(args.concurrency == 20 and args.seed == 7, "concurrency/seed parse")
check(args.temperature == 0.5 and args.max_tokens == 2048, "sampling parse")
check(args.model == "m1" and args.resume, "model/resume parse")
check(args.edge_case_rate == 0.3, "edge-case-rate parse")
check(args.output == "/tmp/x.jsonl", "output parse", args.output)

_parser_defaults = cli.build_parser().parse_args([])
check(_parser_defaults.max_tokens >= 8192,
      "default max-tokens can express the 'extreme' length band",
      _parser_defaults.max_tokens)

# ---------------------------------------------------------------------------
print("2. Spec sampling: broad and edge-case-targeted")
# ---------------------------------------------------------------------------
cfg = GeneratorConfig()
rng = random.Random(5)
factory = ValueFactory(rng, ValuePool())
sampler = SpecSampler(cfg, factory, rng)

specs = [sampler.sample(i) for i in range(400)]
broad = [s for s in specs if s.edge_case is None]
targeted = [s for s in specs if s.edge_case is not None]

check(all(s.lang in cfg.lang_weights for s in specs), "langs valid")
check(len({s.doc_type for s in broad}) > 20, "doc types varied",
      len({s.doc_type for s in broad}))
check(len({s.band for s in broad}) >= 5, "length bands varied",
      {s.band for s in broad})
check(not any(s.negative_only for s in broad),
      "negative_only_rate=0.0 (2026-08-21, true-positive-only instruction) "
      "means no negative-only specs")
check(not any(s.hard_negatives for s in broad),
      "hard_negative_rate=0.0 (same instruction) means no hard negatives sampled")

# edge_case_rate=0.15 default -- with n=400, expect roughly 40-80 targeted.
check(20 < len(targeted) < 150,
      "edge_case_rate produces a plausible share of targeted specs",
      len(targeted))
for s in targeted:
    check(not EC.is_negative(s.edge_case),
          "edge-case sampling is restricted to positive-family cases",
          (s.edge_case.id, s.edge_case.status))
    # one entity, or the two values of a contrast lesson (P2-6: token vs key,
    # IPv6 vs MAC, licence vs ID card), and never a decoy
    contrast = {c.case.id: c.labels for c in EC.CONTRAST_CASES}
    want = contrast.get(s.edge_case.id)
    check((len(s.entities) == 1 if want is None
           else tuple(e.label for e in s.entities) == want) and not s.hard_negatives,
          "positive edge case carries its one entity (or its contrast pair), no decoys",
          (s.entities, s.hard_negatives))

with_entities = [s for s in broad if s.entities]
check(with_entities, "broad specs carry injected values")
# Injected values must already be valid -- that is the whole point.
from piigen.blocklist import is_blocked                            # noqa: E402
from piigen.validate import value_valid                            # noqa: E402
from piigen.config import STRUCTURED_LABELS                        # noqa: E402
bad_value = None
for spec in specs:
    for ent in spec.entities:
        if is_blocked(ent.value):
            bad_value = ("blocked", ent.label, ent.value)
        if ent.label in STRUCTURED_LABELS and not value_valid(ent.label, ent.value)[0]:
            bad_value = ("invalid", ent.label, ent.value)
check(bad_value is None, "every injected value (broad and edge-case) is clean "
      "and checksum-valid", bad_value)

# Steering: rare labels must actually get sampled in broad mode.
label_hits: dict = {}
for spec in broad:
    for ent in spec.entities:
        label_hits[ent.label] = label_hits.get(ent.label, 0) + 1
for rare in ("MAC_ADDRESS", "IPV6_ADDRESS", "ICCID"):
    check(label_hits.get(rare, 0) > 0, f"rare label {rare} sampled",
          label_hits.get(rare, 0))

# Every one of the 27 labels has a usable catalog entry -- if one raised
# KeyError, edge-case sampling would silently skip that label forever.
from piigen.config import ENTITY_TYPES                             # noqa: E402
missing_catalog = sorted(set(ENTITY_TYPES) - set(EC.LABEL_CASES))
check(not missing_catalog, "every label has edge-case catalog entries",
      missing_catalog)

# ---------------------------------------------------------------------------
print("3. dspy_generate.build_fields")
# ---------------------------------------------------------------------------
spec_with_entity = next(s for s in broad if s.entities)
fields = build_fields(spec_with_entity)
check(set(fields) == {"language", "doc_type", "tone_register", "length_hint",
                      "entities_to_embed", "decoys", "noise_directives",
                      "document_year", "scenario_note"},
      "build_fields returns the expected keys", sorted(fields))
check(all(f"{e.label}: {e.value}" in fields["entities_to_embed"]
          for e in spec_with_entity.entities),
      "every planned entity appears in entities_to_embed", fields["entities_to_embed"])
check(fields["document_year"] == str(spec_with_entity.reference_year),
      "document_year reflects the spec's reference_year", fields["document_year"])
check(2015 <= spec_with_entity.reference_year <= 2026,
      "reference_year falls within the intended ambient-date range",
      spec_with_entity.reference_year)
check(fields["scenario_note"] == "none",
      "broad-sampled spec has no scenario note", fields["scenario_note"])


# negative_only_rate=0.0 by default now, so no organically-sampled spec has
# negative_only=True -- construct one directly. build_fields still needs to
# handle it correctly (this capability stays available, just unused by
# default -- see config.py's 2026-08-21 comment).
neg_only = dataclasses.replace(broad[0], entities=[], hard_negatives=[],
                               adversarials=[], negative_only=True)
nf = build_fields(neg_only)
check("NO personal data" in nf["entities_to_embed"],
      "negative_only spec's entities_to_embed says so explicitly",
      nf["entities_to_embed"])

if targeted:
    ef = build_fields(targeted[0])
    check(ef["scenario_note"] != "none" and targeted[0].edge_case.status in ef["scenario_note"],
          "edge-case spec's scenario_note carries the case status", ef["scenario_note"])
    check("correctness" in ef["scenario_note"],
          "scenario_note instructs against commenting on correctness",
          ef["scenario_note"])

# ---------------------------------------------------------------------------
print("4. Leaked-PII detection")
# ---------------------------------------------------------------------------
text = "Write to ada@example-corp.io about it."
ents = [{"start": text.index("ada@example-corp.io"),
         "end": text.index("ada@example-corp.io") + len("ada@example-corp.io"),
         "label": "EMAIL", "text": "ada@example-corp.io"}]
check(find_leaked_pii(text, ents) == [], "labeled email is not a leak")

leaky = text + " And also cc unlisted@other.net please."
check(find_leaked_pii(leaky, ents), "unlabeled email detected as leak")

ip_text = "server at 203.0.113.45 responded"
check(find_leaked_pii(ip_text, []), "unlabeled IP detected")

order = "Order 1234567890123456 shipped."
check(find_leaked_pii(order, []) == [], "non-Luhn digit run is not a card leak",
      find_leaked_pii(order, []))
card = "Paid with 4539578763621486 today."      # Luhn-valid
check(find_leaked_pii(card, []), "Luhn-valid unlabeled card is a leak")
check(find_leaked_pii(card, [], decoys=["4539578763621486"]) == [],
      "declared decoy is exempt")

# ---------------------------------------------------------------------------
print("5. Judgment-word leak detection")
# ---------------------------------------------------------------------------
check(find_judgment_leak("Kod AB1234 sistemə daxil edildi.") == [],
      "ordinary sentence has no judgment leak")
check(find_judgment_leak("Bu format yanlışdır, düzgün deyil.") != [],
      "judgment words detected")
check("wrong" in find_judgment_leak("this value looks wrong to me"),
      "english judgment word detected")
check(set(EC.LABEL_CASES) == set(ENTITY_TYPES),
      "edge_cases catalog covers exactly the current taxonomy")

# ---------------------------------------------------------------------------
print("6. Similarity / deduplication")
# ---------------------------------------------------------------------------
index = SimilarityIndex(threshold=0.82)
a = "Dear customer, your order has shipped and will arrive on Tuesday morning."
b = "Dear customer, your order has shipped and will arrive on Tuesday morning."
c = "Completely different content about server maintenance windows and backups."

na = normalize_for_similarity(a, [])
index.add(na)
check(index.check(normalize_for_similarity(b, []))[0], "exact duplicate caught")
check(not index.check(normalize_for_similarity(c, []))[0],
      "distinct document allowed")

t1 = "Client: Ayse Yilmaz. Phone: 0501112233. Please confirm the appointment."
t2 = "Client: Mehmet Demir. Phone: 0559998877. Please confirm the appointment."
e1 = [{"start": 8, "end": 20, "label": "NAME", "text": "Ayse Yilmaz"},
      {"start": 29, "end": 39, "label": "PHONE", "text": "0501112233"}]
e2 = [{"start": 8, "end": 21, "label": "NAME", "text": "Mehmet Demir"},
      {"start": 30, "end": 40, "label": "PHONE", "text": "0559998877"}]
idx2 = SimilarityIndex(threshold=0.82)
idx2.add(normalize_for_similarity(t1, e1))
dupe, score = idx2.check(normalize_for_similarity(t2, e2))
check(dupe, f"same skeleton with different values is a duplicate (score {score:.2f})")
check(len(idx2) == 1, "index size tracked", len(idx2))

# ---------------------------------------------------------------------------
print("6b. ValuePool.health(): FINITE_BY_NATURE labels judged correctly")
# ---------------------------------------------------------------------------
# 2026-08-26: a resumed live run halted after batch 1 on
# "pool_over_cap_share=1 ... value pool over-cap beyond the stop share for:
# AGE" with only 4,376 cumulative AGE draws on record -- nowhere near real
# generation volume. Root cause: AGE has only 95 possible values, so even a
# perfectly uniform draw already puts every value at 1/95 = 1.053% share,
# which is already 2.6x over the global 0.4% max_share -- over_cap_share
# approaches 100% by construction for a small closed vocabulary, regardless
# of how healthy the actual distribution is. Fixed by judging
# FINITE_BY_NATURE labels (CITY/ZIPCODE/AGE) on concentration (top_share)
# instead, matching scripts/simulate_pools.py's already-correct methodology.
from piigen.values import FINITE_BY_NATURE, MIN_CONCENTRATION_SAMPLE      # noqa: E402

check(FINITE_BY_NATURE == {"CITY", "ZIPCODE", "AGE"},
      "FINITE_BY_NATURE covers exactly the three closed-vocabulary labels",
      FINITE_BY_NATURE)

# A perfectly uniform AGE pool at real volume must NOT trip stop, even
# though every value is structurally over the flat max_share cap.
pool_age = ValuePool(max_share=0.004, state_path=None)
rng_age = random.Random(7)
for _ in range(6000):
    pool_age.record("AGE", str(rng_age.randint(1, 95)))
for _ in range(300):
    pool_age.fresh("AGE", lambda: str(rng_age.randint(1, 95)))
h_age = pool_age.health("AGE")
check(h_age["over_cap_share"] > 0.5,
      "sanity: this AGE scenario really is over the flat cap on paper",
      h_age["over_cap_share"])
check(h_age["status"] == "ok",
      "a healthy (uniform, high-volume) AGE pool is NOT judged unhealthy",
      h_age["status"])
check(h_age["judged_share"] < 0.10,
      "judged_share reflects concentration, not the flat cap", h_age)

# A handful of draws (what a tiny test/fake-generator batch produces) must
# not self-trip on sample-size noise -- one value drawn once out of one
# total draw is trivially "100% of the total" and means nothing.
pool_tiny = ValuePool(max_share=0.004, state_path=None)
pool_tiny.fresh("AGE", lambda: "42")
h_tiny = pool_tiny.health("AGE")
check(h_tiny["status"] == "ok",
      "a tiny sample (below MIN_CONCENTRATION_SAMPLE) is not judged at all",
      h_tiny)

# Genuine memorisation -- one value swallowing the label -- must still stop,
# even at real volume. The fix must not make this check toothless.
pool_bad = ValuePool(max_share=0.004, state_path=None)
for _ in range(200):
    pool_bad.record("AGE", "35")
for _ in range(50):
    pool_bad.record("AGE", str(random.randint(1, 95)))
h_bad = pool_bad.health("AGE")
check(h_bad["status"] == "stop",
      "genuine concentration (one value >80% of a real-volume label) "
      "still trips stop", h_bad)

# Non-finite labels (e.g. GIVENNAME) must be completely unaffected --
# still judged on over_cap_share, not concentration.
pool_name = ValuePool(max_share=0.004, state_path=None)
for _ in range(200):
    pool_name.record("GIVENNAME", "Kamil")
for _ in range(50):
    pool_name.fresh("GIVENNAME", lambda: f"Name{random.randint(1, 1000)}")
h_name = pool_name.health("GIVENNAME")
check(h_name["judged_share"] == h_name["over_cap_share"],
      "a non-FINITE_BY_NATURE label's judged_share is still over_cap_share",
      h_name)

# ---------------------------------------------------------------------------
print("7. Checkpoint save/load/atomicity")
# ---------------------------------------------------------------------------
tmp = Path(tempfile.mkdtemp())
out = tmp / "aug.jsonl"

state = RunState(model="m", seed=3, requested=10, accepted=4,
                 next_spec_index=9, rejections={"parse": 2})
save_state(out, state)
check(state_path_for(out).exists(), "state file written")
loaded = load_state(out)
check(loaded is not None and loaded.accepted == 4, "state round-trips", loaded)
check(loaded.rejections == {"parse": 2}, "rejections round-trip")

state.merge_rejections({"parse": 3, "leak": 1})
check(state.rejections == {"parse": 5, "leak": 1}, "rejection merge",
      state.rejections)

with OutputWriter(out) as writer:
    writer.write_many([{"id": "a", "text": "one", "lang": "az", "entities": []},
                       {"id": "b", "text": "two", "lang": "az", "entities": []}])
check(len(load_existing(out)) == 2, "written rows reload")

with out.open("a", encoding="utf-8") as handle:
    handle.write('{"id": "c", "text": "trunc')
rows = load_existing(out)
check(len(rows) == 2, "partial trailing line dropped", len(rows))

state_path_for(out).write_text("{not json", encoding="utf-8")
check(load_state(out) is None, "corrupt state returns None")

shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------------------
print("8. assemble_document (the pipeline's acceptance gate)")
# ---------------------------------------------------------------------------
gen_cfg = GeneratorConfig()
rng = random.Random(9)
factory = ValueFactory(rng, ValuePool())
sampler = SpecSampler(gen_cfg, factory, rng)

pos_spec = next(s for s in (sampler.sample(i) for i in range(200)) if s.entities)
good_text = "Sənəd üzrə " + ", ".join(e.value for e in pos_spec.entities) + \
    " bu gün qeydə alındı və təsdiqləndi."
outcome = assemble_document(pos_spec, good_text, gen_cfg, 0.0)
check(outcome.ok, "clean positive document accepted", outcome.reason)

missing_text = "Bu sənəddə heç bir dəyər yoxdur, tamamilə əlaqəsiz mətndir."
outcome = assemble_document(pos_spec, missing_text, gen_cfg, 0.0)
check(not outcome.ok and "missing values" in outcome.reason,
      "document dropping its planned value is rejected", outcome.reason)


# negative_only_rate=0.0 by default now, so no organically-sampled spec has
# empty entities or hard_negatives -- construct these directly.
# negative_only=True is required to reach the leak-detection code at all --
# with planned entities empty and negative_only=False, "no entities resolved"
# fires first (correctly: an ordinary document with nothing to say is not
# what these cases are testing). This still tests a real capability
# (assemble_document's leak detection doesn't care how a spec was built), it
# is just not reachable through the default sampling config any more -- see
# config.py's 2026-08-21 comment.
leak_spec = dataclasses.replace(sampler.sample(1000), entities=[],
                                hard_negatives=[], adversarials=[],
                                negative_only=True, edge_case=None)
leak_text = "Əlaqə üçün john.doe.unlisted@leaky-example.org ünvanına yazın."
outcome = assemble_document(leak_spec, leak_text, gen_cfg, 0.0)
check(not outcome.ok and "leaked" in outcome.reason,
      "document with unlabeled leaked PII is rejected", outcome.reason)

# Same reasoning: pick a negative-status case directly from the catalog
# (still there, just never sampled by _sample_edge_case any more) to build a
# synthetic edge-case-negative spec and confirm the judgment-leak/decoy-
# embedding checks still work on it.
_neg_label = next(l for l in EC.LABEL_CASES
                  if any(EC.is_negative(c) for c in EC.LABEL_CASES[l]))
_neg_case = next(c for c in EC.LABEL_CASES[_neg_label] if EC.is_negative(c))
_decoy = EC.near_miss_value(_neg_case, _neg_label, rng)
judgment_spec = dataclasses.replace(
    sampler.sample(2000), entities=[], hard_negatives=[_decoy],
    adversarials=[_decoy], negative_only=True, edge_case=_neg_case)

judgment_text = f"Qeyd olunan {_decoy} dəyəri yanlışdır, düzgün deyil."
outcome = assemble_document(judgment_spec, judgment_text, gen_cfg, 0.0)
check(not outcome.ok and "judgment leak" in outcome.reason,
      "editorializing about a decoy's correctness is rejected", outcome.reason)

not_embedded_text = "Bu sənəddə tamamilə fərqli və əlaqəsiz məzmun var."
outcome = assemble_document(judgment_spec, not_embedded_text, gen_cfg, 0.0)
check(not outcome.ok and "not embedded" in outcome.reason,
      "edge-case decoy that never appears in the text is rejected",
      outcome.reason)

# ---------------------------------------------------------------------------
print("9. End-to-end pipeline (fake generator)")
# ---------------------------------------------------------------------------
tmp = Path(tempfile.mkdtemp())
out = tmp / "aug.jsonl"

cfg = AugmentConfig(num_examples=25, batch_size=8, concurrency=4, seed=11,
                    output=out, pool_state=None, noise_rate=0.5)
pipe = AugmentationPipeline(FakeGenerator(seed=1), cfg)
rows, state = pipe.run()

check(len(rows) == 25, "produced the requested count", len(rows))
check(out.exists(), "output file created")
check(len(load_existing(out)) == 25, "all rows persisted")

from piigen.validate import validate_example                       # noqa: E402
bad = [(r["id"], validate_example(r)[0]) for r in rows if validate_example(r)]
check(not bad, "every accepted row passes the shared validator", bad[:3])

offsets_ok = all(r["text"][e["start"]:e["end"]] == e["text"]
                 for r in rows for e in r["entities"])
check(offsets_ok, "offsets exact after noise injection")

ids = [r["id"] for r in rows]
check(len(ids) == len(set(ids)), "ids unique")
check(all(r["lang"] == "az" for r in rows), "langs valid")

from piigen.resolver import find_unlabeled_repeats                 # noqa: E402
missed = sum(find_unlabeled_repeats(r["text"], r["entities"]) for r in rows)
check(missed == 0, "no unlabeled repeat mentions", missed)

# ---------------------------------------------------------------------------
print("10. Resume never regenerates completed work")
# ---------------------------------------------------------------------------
before = load_existing(out)
cfg2 = AugmentConfig(num_examples=40, batch_size=8, concurrency=4, seed=11,
                     output=out, resume=True, pool_state=None)
gen2 = FakeGenerator(seed=2)
pipe2 = AugmentationPipeline(gen2, cfg2)
rows2, state2 = pipe2.run()

check(len(rows2) == 40, "resumed run reaches the new target", len(rows2))
kept = rows2[:len(before)]
check([r["id"] for r in kept] == [r["id"] for r in before],
      "existing rows preserved in order")
check(all(a == b for a, b in zip(before, kept)), "existing rows unmodified")
# Headroom raised from +12 to +24 (2026-08-25, audit P0-2/P0-3), then to
# +30 (2026-08-28). The point of this check is that the resumed run
# generates the SHORTFALL and not the whole target -- 40 calls would mean
# it regenerated everything already on disk. The allowance is not a
# throughput assertion. It grew the first time because the anchor and
# short-span gates legitimately reject more candidates than before
# (record-level rejection 1.85% -> 3.76% on 8,001 real documents). It grew
# again because `validate.language_evidence`'s az branch now also credits a
# diacritic-folded stopword match (fixing a real false-positive: genuine but
# diacritic-light/casual Azerbaijani, e.g. "gore"/"uzr" for "görə"/"üzr",
# scored 0 native words before). FakeGenerator's fixed synthetic text passes
# the language gate slightly more often now, so a few more of its attempts
# reach -- and get rejected by -- a later gate (near-duplicate/repeat-
# mention) instead, before 40 accepted are reached. Measured: 42 calls
# against the old 39-call ceiling (25 + 24) -- +30 leaves real margin, not
# just enough to cover the measured shift.
check(gen2.calls <= 40 - len(before) + 30,
      "only the shortfall was generated, not the whole target", gen2.calls)

ids2 = [r["id"] for r in rows2]
check(len(ids2) == len(set(ids2)), "no duplicate ids after resume")

cfg3 = AugmentConfig(num_examples=40, batch_size=8, seed=11, output=out,
                     resume=True, pool_state=None)
gen3 = FakeGenerator(seed=3)
rows3, _ = AugmentationPipeline(gen3, cfg3).run()
check(gen3.calls == 0, "completed run makes no generation calls", gen3.calls)
check(len(rows3) == 40, "completed run returns existing rows", len(rows3))

shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------------------
print("11. Bad model output is rejected, never written")
# ---------------------------------------------------------------------------
tmp = Path(tempfile.mkdtemp())

out_leak = tmp / "leak.jsonl"
cfg_leak = AugmentConfig(num_examples=6, batch_size=6, concurrency=2, seed=4,
                         output=out_leak, pool_state=None)
rows_leak, state_leak = AugmentationPipeline(
    FakeGenerator(leak=True, seed=4), cfg_leak).run()
check(len(rows_leak) == 0, "documents leaking PII are all rejected",
      len(rows_leak))
check(any("leaked" in k for k in state_leak.rejections),
      "leak recorded as the rejection reason", state_leak.rejections)

out_dup = tmp / "dup.jsonl"
cfg_dup = AugmentConfig(num_examples=8, batch_size=8, concurrency=2, seed=5,
                        output=out_dup, pool_state=None,
                        max_empty_batches=2, attempt_multiplier=4.0)
one_lang = GeneratorConfig()
one_lang.lang_weights = {"az": 1.0}
rows_dup, state_dup = AugmentationPipeline(
    FakeGenerator(duplicate=True, seed=5), cfg_dup, one_lang).run()
check(len(rows_dup) <= 3, "near-identical documents are collapsed",
      len(rows_dup))
check(state_dup.rejections.get("near-duplicate", 0) > 0,
      "near-duplicate recorded as the rejection reason", state_dup.rejections)

out_empty = tmp / "empty.jsonl"
cfg_empty = AugmentConfig(num_examples=4, batch_size=4, concurrency=2, seed=6,
                          output=out_empty, pool_state=None,
                          max_empty_batches=2, attempt_multiplier=4.0)
rows_empty, state_empty = AugmentationPipeline(
    FakeGenerator(empty_every=1, seed=6), cfg_empty).run()
check(len(rows_empty) == 0, "empty model output never reaches the output")
check(any("api" in k for k in state_empty.rejections),
      "empty-output failure recorded", state_empty.rejections)

shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------------------
print("12. Regressions for audited defects")
# ---------------------------------------------------------------------------
# Each check here corresponds to a bug the suite previously did NOT catch.

# --- F2 + N7: determinism under concurrency.
def _run_seeded(concurrency: int, seed: int = 4242):
    tmpdir = Path(tempfile.mkdtemp())
    try:
        cfg = AugmentConfig(num_examples=12, batch_size=6,
                            concurrency=concurrency, seed=seed,
                            output=tmpdir / "d.jsonl", pool_state=None,
                            noise_rate=0.9)
        rows, _ = AugmentationPipeline(FakeGenerator(seed=1), cfg).run()
        return [(r["id"], r["text"], tuple(r.get("_noise") or [])) for r in rows]
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

check(_run_seeded(1) == _run_seeded(1), "F2: same seed, serial -> identical")
check(_run_seeded(8) == _run_seeded(8),
      "F2: same seed, concurrency=8 -> identical (was nondeterministic)")
check(_run_seeded(1) == _run_seeded(8),
      "N7: concurrency does not change the output at all")

# --- F4: noise must be applied at the configured rate, not rate x rate.
_tmp = Path(tempfile.mkdtemp())
_cfg = AugmentConfig(num_examples=120, batch_size=60, concurrency=4, seed=21,
                     output=_tmp / "n.jsonl", pool_state=None, noise_rate=1.0)
_rows, _ = AugmentationPipeline(FakeGenerator(seed=3), _cfg).run()
_noised = sum(1 for r in _rows if r.get("_noise"))
check(_noised >= len(_rows) * 0.9,
      "F4: noise_rate=1.0 noises ~every document", f"{_noised}/{len(_rows)}")
_cfg0 = AugmentConfig(num_examples=30, batch_size=30, concurrency=2, seed=22,
                      output=_tmp / "n0.jsonl", pool_state=None, noise_rate=0.0)
_rows0, _ = AugmentationPipeline(FakeGenerator(seed=4), _cfg0).run()
check(not any(r.get("_noise") for r in _rows0), "F4: noise_rate=0.0 noises none")
check(all(r["text"][e["start"]:e["end"]] == e["text"]
          for r in _rows for e in r["entities"]),
      "F4: offsets stay exact at 100% noise")
shutil.rmtree(_tmp, ignore_errors=True)

# --- F6: a decoy we asked for must never be reported as a leak.
_hash = "66:02:8d:e7:11:59:b4:2b"
check(find_leaked_pii(f"trace {_hash} logged", [], decoys=[_hash]) == [],
      "F6: decoy longer than the matched pattern is exempt",
      find_leaked_pii(f"trace {_hash} logged", [], decoys=[_hash]))
_card = "4539578763621486"
for _form in (_card, "4539 5787 6362 1486", "4539-5787-6362-1486"):
    check(find_leaked_pii(f"order {_form} ok", [], decoys=[_card]) == [],
          f"F6: reformatted card decoy is exempt ({_form})")
check(find_leaked_pii(f"paid {_card} today", [], decoys=[]),
      "F6: real unlabeled card is still a leak")
check(find_leaked_pii("ref TR330006100519786457841399 ok", []) == [],
      "F6: bad-checksum IBAN-shaped string is not a leak")
check(find_leaked_pii("acct GB29NWBK60161331926819 ok", []),
      "F6: mod-97-valid IBAN is still a leak")

# --- F9: refuse to append to a file this run did not read.
_tmp = Path(tempfile.mkdtemp())
_out = _tmp / "guard.jsonl"
_r1, _ = AugmentationPipeline(FakeGenerator(seed=1), AugmentConfig(
    num_examples=6, batch_size=6, concurrency=1, seed=9, output=_out,
    pool_state=None)).run()
_r2, _ = AugmentationPipeline(FakeGenerator(seed=1), AugmentConfig(
    num_examples=6, batch_size=6, concurrency=1, seed=9, output=_out,
    pool_state=None)).run()
_ids = [r["id"] for r in load_existing(_out)]
check(len(_ids) == len(set(_ids)),
      "F9: a non-resume rerun cannot leave duplicate ids on disk", _ids[:4])
check(len(load_existing(_out)) == 6,
      "F9: a non-resume rerun replaces rather than appends",
      len(load_existing(_out)))
shutil.rmtree(_tmp, ignore_errors=True)

# --- F16: resume must not inherit the previous run's attempt count as spend.
_tmp = Path(tempfile.mkdtemp())
_out = _tmp / "budget.jsonl"
AugmentationPipeline(FakeGenerator(seed=1), AugmentConfig(
    num_examples=10, batch_size=10, concurrency=1, seed=5, output=_out,
    pool_state=None)).run()
_st = load_state(_out)
_st.attempted = 100_000
save_state(_out, _st)
_rows_r, _ = AugmentationPipeline(FakeGenerator(seed=2), AugmentConfig(
    num_examples=14, batch_size=10, concurrency=1, seed=5, output=_out,
    resume=True, pool_state=None)).run()
check(len(_rows_r) == 14,
      "F16: resume reaches its target despite a large restored attempt count",
      len(_rows_r))
shutil.rmtree(_tmp, ignore_errors=True)

# --- F17: the exhaustion fallback must never return a blocklisted value.
_pool = ValuePool(attempts=3)
_blocked_only = _pool.fresh("PASSWORD_SECRET_PRIVATE_KEY", lambda: "password123")
check(_blocked_only == "" or not is_blocked(_blocked_only),
      "F17: exhausted pool never emits a blocked value", _blocked_only)
_ok = _pool.fresh("NAME", lambda: "Rəşad Məmmədov")
check(_ok == "Rəşad Məmmədov", "F17: normal path unaffected", _ok)

# --- F15: adversarial coverage must be observed, not hardcoded to zero.
# hard_negative_rate/adversarial_rate default to 0.0 now (true-positive-only,
# 2026-08-21), so this needs its own GeneratorConfig with them restored --
# this tests that the COUNTING MECHANISM reports real observed counts
# instead of a hardcoded 0, a property of the code, not of the default policy.
_tmp = Path(tempfile.mkdtemp())
_gen_cfg_neg = GeneratorConfig()
_gen_cfg_neg.hard_negative_rate = 0.9
_gen_cfg_neg.adversarial_rate = 0.5
_cfg_a = AugmentConfig(num_examples=60, batch_size=30, concurrency=4, seed=31,
                       output=_tmp / "a.jsonl", pool_state=None)
_rows_a, _state_a = AugmentationPipeline(FakeGenerator(seed=7), _cfg_a,
                                         _gen_cfg_neg).run()
check(any(r.get("_adversarials") for r in _rows_a),
      "F15: _adversarials reflects reality instead of always 0",
      collections.Counter(r.get("_adversarials") for r in _rows_a))
check(any(r.get("_hard_negatives") for r in _rows_a),
      "F15: _hard_negatives counts decoys present in the text")
shutil.rmtree(_tmp, ignore_errors=True)

# --- dump_rejects: rejected candidates land on disk with enough to diagnose.
_tmp = Path(tempfile.mkdtemp())
_rej = _tmp / "r.jsonl"
_cfg_r = AugmentConfig(num_examples=40, batch_size=20, concurrency=2, seed=55,
                       output=_tmp / "d.jsonl", pool_state=None,
                       dump_rejects=_rej)
_rows_r, _state_r = AugmentationPipeline(FakeGenerator(seed=9), _cfg_r).run()
_total_rejections = sum(_state_r.rejections.values())
check(_rej.exists(), "dump_rejects: file is created when configured")
import json as _json                                                # noqa: E402
_lines = [_json.loads(l) for l in _rej.read_text(encoding="utf-8").splitlines()]
check(len(_lines) == _total_rejections,
      "dump_rejects: one line per rejection, matching state.rejections",
      (len(_lines), _total_rejections))
check(all({"doc_type", "lang", "reason", "text"} <= set(l) for l in _lines),
      "dump_rejects: every line carries enough to diagnose")
shutil.rmtree(_tmp, ignore_errors=True)

# --- the DSPy Signature field named "register" was renamed to "tone_register"
# after it silently shadowed abc.ABCMeta.register (DSPy's Signature metaclass
# inherits from ABCMeta) -- a UserWarning on every run, twice reintroduced in
# the same session. Regression-test it stays gone.
import warnings                                                     # noqa: E402
from piigen.llm.dspy_generate import build_signature                # noqa: E402
try:
    with warnings.catch_warnings(record=True) as _w:
        warnings.simplefilter("always")
        build_signature()
        _shadow = [x for x in _w if "shadow" in str(x.message)]
    check(not _shadow, "GenerateTrainingDocument field names do not shadow "
          "Signature/ABCMeta attributes", [str(x.message) for x in _shadow])
except ImportError as _dspy_exc:
    # `dspy` is an optional dependency for this suite -- every section above
    # runs without it. Previously this raised and killed the process before
    # the PASS/FAIL tally printed, so a minimal environment reported no
    # result at all instead of "everything offline passed".
    SKIPPED.append(f"DSPy signature shadow check ({_dspy_exc})")

# --- resolve_claims must not trim characters that are part of the searched-
# for value itself. Found in the first real run against Wahoo: resolver.py's
# normalize_span (now removed) blindly stripped a leading '(' from a
# TELEPHONENUM value and a trailing '.' from a two-letter STREET abbreviation
# ("pr.", "küç." -- ValueFactory.street() bundles these into the value), even
# though `text.find(value, ...)` already gives an exact, correct match: the
# found span's own edge characters are always literally value[0]/value[-1],
# so there is never a legitimate reason to trim them further.
_phone_text = "Elaqe nomresi 1: (050) 218-43-32"
_phone_ents, _ = resolve_claims(_phone_text, [{"label": "TELEPHONENUM",
                                               "text": "(050) 218-43-32"}])
check(_phone_ents and _phone_ents[0]["text"] == "(050) 218-43-32",
      "a parenthesized phone number keeps its leading '('", _phone_ents)

_street_text = "filialda: Mirzə İbrahimov pr. ünvanında"
_street_ents, _ = resolve_claims(_street_text, [{"label": "STREET",
                                                 "text": "Mirzə İbrahimov pr."}])
check(_street_ents and _street_ents[0]["text"] == "Mirzə İbrahimov pr.",
      "a two-letter street abbreviation ('pr.') keeps its trailing period",
      _street_ents)

# --- a truncated LM response must be rejected, not silently accepted.
# Found by hand in a real compile run under thinking mode: dspy.Predict does
# not surface finish_reason on its return value, so a response cut off mid-
# document (a real one ended "...[2025-11-04", mid-timestamp) passed every
# other check -- whatever entity value was needed had already been written
# before the cutoff -- and got selected as a demo. DSPyGenerator.generate()
# now checks finish_reason via the LM's own history instead of trusting that
# coincidence.
class _FakeChoice:
    def __init__(self, finish_reason):
        self.finish_reason = finish_reason


class _FakeResponse:
    def __init__(self, finish_reason):
        self.choices = [_FakeChoice(finish_reason)]


class _TruncatingLM:
    """Minimal stand-in exposing exactly what DSPyGenerator.generate() reads
    off a real dspy.LM after a call: .history[-1]['response'].choices[*]
    .finish_reason. dspy.utils.DummyLM does not populate 'response' at all
    (verified above), so it cannot exercise this path -- this fakes just
    enough of the real dspy.LM history shape to test it in isolation."""

    def __init__(self, finish_reason):
        self.model = "fake-truncating-model"
        self.history = [{"response": _FakeResponse(finish_reason)}]

    def __call__(self, *a, **kw):
        return ["some text"]


from piigen.llm.dspy_generate import DSPyGenerator as _DSPyGen           # noqa: E402

try:
    _trunc_gen = _DSPyGen(_TruncatingLM("length"))
    _trunc_gen.module = lambda **kw: type("P", (), {"text": "cut off mid-sen"})()
    try:
        _trunc_gen.generate(broad[0])
        check(False, "truncated response (finish_reason=length) is rejected")
    except ImportError:
        raise
    except Exception as exc:
        check("truncat" in str(exc).lower(), "truncated response is rejected", exc)

    _ok_gen = _DSPyGen(_TruncatingLM("stop"))
    _ok_gen.module = lambda **kw: type("P", (), {"text": "a complete sentence."})()
    check(_ok_gen.generate(broad[0]) == "a complete sentence.",
          "a normal finish_reason='stop' response is not rejected")
except ImportError as _dspy_exc:
    # Same optional-dependency reasoning as the signature check above:
    # DSPyGenerator builds its default module eagerly, which needs dspy.
    SKIPPED.append(f"DSPy truncation-detection checks ({_dspy_exc})")

# --- taxonomy label leak (2026-08-24): found by manual review of real
# --compiled output -- the model sometimes echoes entities_to_embed's own
# 'LABEL: value' formatting into the document ("Ad: GIVENNAME: Fatimə",
# "AZ_PASSPORT_NUMBER: O69367632") instead of a natural field label. 5 of
# the committed program.json's 12 demos carried this exact defect.
_t1 = "Şəxsiyyət vəsiqəsi: AZ_PASSPORT_NUMBER: O69367632"
_v1 = "O69367632"
check(find_label_name_leak(
    _t1, [{"start": _t1.index(_v1), "end": _t1.index(_v1) + len(_v1),
          "label": "AZ_PASSPORT_NUMBER", "text": _v1}]),
    "label leak: internal-only label token flags even right next to its own value")
_t2 = "Ad: GIVENNAME: Fatimə"
_v2 = "Fatimə"
check(find_label_name_leak(
    _t2, [{"start": _t2.index(_v2), "end": _t2.index(_v2) + len(_v2),
          "label": "GIVENNAME", "text": _v2}]),
    "label leak: double-labeled field ('Ad:' + 'GIVENNAME:') still flags")
check(find_label_name_leak(
    "Möhtərəm müştəri, sənədiniz qeydə alındı, təşəkkür edirik.", []) == [],
    "label leak: ordinary prose with no label tokens does not flag")
# Real-world/technical terms are deliberately NOT checked -- a genuine
# document (including a config/log snippet) can say these verbatim.
for _term in ("IBAN", "ICCID", "URL", "EMAIL", "MAC_ADDRESS", "API_KEY",
             "ACCESS_TOKEN", "PRIVATE_KEY"):
    check(find_label_name_leak(f"{_term}: some-value-here", []) == [],
          f"label leak: {_term} is a real term, deliberately not flagged")
_leaky_text = "Ad: GIVENNAME: Fatimə | Soyad: SURNAME: İbrahimov"
outcome_leak = assemble_document(
    dataclasses.replace(pos_spec, entities=[
        type(pos_spec.entities[0])("GIVENNAME", "Fatimə"),
        type(pos_spec.entities[0])("SURNAME", "İbrahimov"),
    ]),
    _leaky_text, gen_cfg, 0.0)
check(not outcome_leak.ok and "taxonomy label leaked" in (outcome_leak.reason or ""),
      "assemble_document rejects a document carrying the label leak",
      outcome_leak.reason)

# --- GIVENNAME/SURNAME gender agreement (2026-08-24): found by manual
# review -- ValueFactory.givenname()/.surname() each independently coin-
# flipped gender when SpecSampler planned both for one document, producing
# real training examples like "Ad: Aqil / Soyad: Rüstəmova" (male given
# name + feminine-suffixed surname). Fixed by settling one female bool per
# document and passing it to both draws.
_female_az = {n for n in LOCALES["az"].first_names_f} - set(LOCALES["az"].first_names_m)
_male_az = {n for n in LOCALES["az"].first_names_m} - set(LOCALES["az"].first_names_f)
check(not (_female_az & _male_az), "az.py: no name is listed as both m and f")


def _surname_gender(s: str) -> str | None:
    if s.endswith(("ova", "yeva")):
        return "f"
    if s.endswith(("ov", "yev")):
        return "m"
    return None


_mismatch = 0
_checked = 0
_gcfg = GeneratorConfig()
for _i in range(400):
    _rng = random.Random(_i)
    _factory = ValueFactory(_rng, ValuePool())
    _sampler = SpecSampler(_gcfg, _factory, _rng)
    _spec = _sampler.sample(_i)
    # the brief's own person; a D-39b name construction plans separate people,
    # each paired on its own (test_name_shapes.py)
    _own = [e for e in _spec.entities if not getattr(e, "role", "") in NAME_SHAPE_ROLES]
    _givens = [e.value for e in _own if e.label == "GIVENNAME"]
    _surs = [e.value for e in _own if e.label == "SURNAME"]
    if not _givens or not _surs:
        continue
    _g_gender = {("m" if g in _male_az else "f" if g in _female_az else None)
                 for g in _givens} - {None}
    _s_gender = {_surname_gender(s) for s in _surs} - {None}
    if _g_gender and _s_gender:
        _checked += 1
        if not (_g_gender & _s_gender):
            _mismatch += 1
check(_checked > 0, "gender test: sampled at least one doc with both entities",
      _checked)
check(_mismatch == 0,
      "GIVENNAME/SURNAME gender agreement holds across sampled documents",
      f"{_mismatch}/{_checked} mismatched")

# ---------------------------------------------------------------------------
print("13. quality_filter: hard-reject screen for harness artifacts")
# ---------------------------------------------------------------------------
# Every threshold in quality_filter is derived from the 1,000-document
# reference batch (llm_augmented_batch_colleague.jsonl), where this screen
# deletes exactly 1 document -- a real `[[ ## completed ]]` adapter artifact --
# and keeps the other 999. These tests pin both halves of that: the rules fire
# on genuine defects, and the shapes that were verified LEGITIMATE in that
# batch are not touched.
from piigen.llm.quality_filter import (screen_record, carrier_word_count,   # noqa: E402
                                       pii_density)

_PROSE = ("Hörmətli müştəri, sizin müraciətiniz sistemdə qeydə alınmışdır və "
          "texniki komandamız tərəfindən araşdırılır. Zəhmət olmasa bir neçə "
          "gün gözləyin, nəticə barədə sizə mütləq məlumat verəcəyik. "
          "Anlayışınız üçün təşəkkür edirik, xidmətimizdən razı qalacaqsınız.")

def _doc(text, ents=None, band="medium"):
    return {"text": text, "lang": "az", "entities": ents or [], "_bucket": band}

def _screen(text, ents=None, band="medium", planned=None):
    return screen_record(_doc(text, ents, band), run_base_gates=False, planned=planned)

# --- the defect actually found in the real batch ---
check(_screen(_PROSE + "\n\n[[ ## completed ]]"),
      "quality_filter: DSPy adapter artifact is rejected")
check(_screen(_PROSE + "\nscenario_note: none"),
      "quality_filter: prompt field name in text is rejected")
check(_screen("Here is the document you requested.\n" + _PROSE),
      "quality_filter: assistant-voice opening is rejected")
check(_screen("```\n" + _PROSE + "\n```"),
      "quality_filter: whole document wrapped in a fence is rejected")
check(_screen(_PROSE + "\x07"),
      "quality_filter: control characters are rejected")
check(_screen(_PROSE + "\n-----BEGIN PRIVATE KEY-----\nabc"),
      "quality_filter: unbalanced PEM block is rejected")
check(_screen("   "), "quality_filter: empty document is rejected")

# --- degenerate output shapes ---
_loop = "Bu mətn təkrarlanan bir cümlədir və sistem tərəfindən yoxlanılmalıdır."
check(_screen("\n".join([_loop] * 6)),
      "quality_filter: repeated prose line (decoding loop) is rejected")
_phr = "sistem tərəfindən yoxlanılan məlumatlar bazaya daxil edilmişdir və təsdiqlənmişdir"
check(_screen((_phr + " ") * 6),
      "quality_filter: repeated prose phrase (decoding loop) is rejected")
check(_screen("Ad: Elvin qeyd",
              [{"start": 4, "end": 9, "label": "GIVENNAME", "text": "Elvin"}],
              band="long"),
      "quality_filter: value-dump (too little carrier text for band) is rejected")

# --- contradictions and bad labels ---
_c = "Yaş 86 və bina 86 qeyd olundu."
check(_screen(_c, [{"start": 4, "end": 6, "label": "AGE", "text": "86"},
                   {"start": 15, "end": 17, "label": "BUILDINGNUM", "text": "86"}]),
      "quality_filter: same string with two labels in ONE doc is rejected")
check(_screen(_PROSE, [{"start": 0, "end": 8, "label": "NOPE", "text": "Hörmətli"}]),
      "quality_filter: unknown label is rejected")

# --- visible-but-unlabeled planned PII (2026-08-24: real bug, 35 confirmed
# instances across 1,100 real documents, 18 of them TIME). Root cause was
# resolver.py's documented gap: a value followed directly by a
# hyphen-attached Azerbaijani suffix ("10:17-də") made _is_word_boundary
# treat the suffix as continuing the token, so resolve_claims discarded a
# real, present, verbatim match. Fixed at the source 2026-08-25
# (_AZ_HYPHEN_SUFFIX in resolver.py) -- kept as a quality_filter test too,
# as defense-in-depth in case the resolver fix regresses independently.
_time_doc = "Görüş saat 10:17-də başladı və uğurla keçdi."
check(_screen(_time_doc, [], band="very_short", planned=[("TIME", "10:17")]),
      "quality_filter: a planned value present in text but never labeled "
      "(the real TIME/hyphen-suffix bug) is rejected")
check(not _screen(_time_doc,
                  [{"start": 11, "end": 16, "label": "TIME", "text": "10:17"}],
                  band="very_short", planned=[("TIME", "10:17")]),
      "quality_filter: control -- the same value correctly labeled passes")

# --- the actual fix, tested at the source: resolve_claims must now find and
# label "10:17" in "10:17-də" on its own, not just be caught downstream.
_resolved_time, _dropped_time = resolve_claims(
    _time_doc, [{"label": "TIME", "text": "10:17"}])
check(len(_resolved_time) == 1 and _resolved_time[0]["text"] == "10:17",
      "resolve_claims labels a value followed by an AZ locative suffix "
      "(-də) at the source, not just via the quality_filter safety net",
      _resolved_time)
# These fixtures now carry an age/building anchor. Since the 100k audit added
# the short-value guard (resolver._occurrence_allowed), a value under 3
# characters is only resolved where context licenses it -- so the original
# fixtures ("Cavab 67-dir." = "the answer is 67") no longer resolve as AGE.
# That is the guard working, not a regression: none of those three sentences
# actually contains an age. The hyphen-suffix boundary rule and the anchor
# rule are separate concerns, so they are now tested separately -- the same
# three suffixes (-dir copula, -ci ordinal, -dan ablative) are still covered.
for _suffix_doc, _val, _lab in [
    ("Müştərinin yaşı 67-dir.", "67", "AGE"),
    ("Bina 5-ci küçədə yerləşir.", "5", "BUILDINGNUM"),
    ("Yaş həddi 10-dan başlayır.", "10", "AGE"),
]:
    _r, _ = resolve_claims(_suffix_doc, [{"label": _lab, "text": _val}])
    check(len(_r) == 1 and _r[0]["text"] == _val,
          f"resolve_claims labels a value before an AZ hyphen-suffix: {_suffix_doc!r}",
          _r)

# The other half of the same rule: an unanchored short value must NOT be
# labeled, however well-formed the hyphen-suffix around it is. This is the
# audit's structural-number defect (32 documents where a planned AGE=3 also
# tagged the "3" in "### 3. Kritik Ssenari").
for _unanchored_doc, _val in [
    ("Cavab 67-dir.", "67"),
    ("Bu 5-ci sinifdir.", "5"),
    ("10-dan başlayaraq sadalayıram.", "10"),
    ("### 3. Kritik Ssenari", "3"),
]:
    _r, _ = resolve_claims(_unanchored_doc, [{"label": "AGE", "text": _val}])
    check(not _r,
          f"resolve_claims refuses an UNANCHORED short value: {_unanchored_doc!r}",
          _r)

# --- must NOT over-fire: a genuine longer token (not a suffix) must still
# be rejected as "inside a longer token", exactly as before this fix.
_r_neg, _ = resolve_claims("Əli Əliyevdən soruşdum.", [{"label": "GIVENNAME", "text": "Əli"}])
check(len(_r_neg) == 1,
      "resolve_claims still finds the standalone 'Əli', not a second false "
      "match inside 'Əliyevdən'", _r_neg)
_r_phone, _ = resolve_claims("nömrə 050-123-45-67 budur",
                             [{"label": "TELEPHONENUM", "text": "050"}])
check(len(_r_phone) == 0,
      "resolve_claims still rejects '050' as inside a longer hyphen-joined "
      "token (a real phone grouping), not a suffix", _r_phone)

# --- 2026-08-26: fused (no-hyphen) AZ noun-case suffix on a proper noun --
# the far more common way real Azerbaijani inflects a name/place than the
# hyphen case above. Measured against the real corpus: of 55,935
# GIVENNAME/SURNAME/CITY/STREET mentions, the genuine rate of this pattern
# was 0% before this fix -- not because it's rare in real Azerbaijani, but
# because resolve_claims had no way to recognize "Bakıda" as "Bakı" + a
# suffix, so a document containing it either lost the mention (leaked
# unlabeled PII) or, more often per the reject-log cross-check, the model
# just never wrote it that way in the first place. Paired with a prompt
# change (dspy_generate.py's _INFLECTION_HINT) that gives the model
# something to write for this fix to have something to recognize.
#
# 2026-08-26 (tokenizer audit, span policy): the resolved SPAN now includes
# the suffix, not just the stem. A stem-only span ("Bakı" inside "Bakıda")
# has no token boundary at its own end -- "Bakıda" is a single token in the
# real xlm-roberta-large tokenizer -- so it was structurally unemittable by
# a token classifier even when correctly detected. `expected` below is the
# full inflected surface form the span must now cover; each case also
# checks `end` lands exactly at the end of that surface form, not the stem.
for _text, _label, _val, _expected in [
    ("Mən Bakıda yaşayıram.", "CITY", "Bakı", "Bakıda"),            # locative
    ("Bakıdan gəlmişəm.", "CITY", "Bakı", "Bakıdan"),                # ablative
    ("Bakıya gedirəm.", "CITY", "Bakı", "Bakıya"),                   # dative (glide)
    ("Bakının mərkəzi gözəldir.", "CITY", "Bakı", "Bakının"),        # genitive
    ("Bakını çox sevirəm.", "CITY", "Bakı", "Bakını"),               # accusative (glide)
    ("Qonaqlar Bakılar haqqında danışdı.", "CITY", "Bakı", "Bakılar"),  # plural
    ("Elnarə Nəsirlini tanıyıram.", "SURNAME", "Nəsirli", "Nəsirlini"),  # accusative
    ("Elnarə Nəsirlidən eşitdim.", "SURNAME", "Nəsirli", "Nəsirlidən"),  # ablative
    ("Məmmədovun evi.", "SURNAME", "Məmmədov", "Məmmədovun"),        # genitive
]:
    _r, _ = resolve_claims(_text, [{"label": _label, "text": _val}])
    _start = _text.index(_val)
    check(len(_r) == 1 and _r[0]["text"] == _expected
          and _r[0]["start"] == _start
          and _r[0]["end"] == _start + len(_expected),
          f"resolve_claims's span for a fused-suffix mention covers the "
          f"whole inflected word, not just the stem: {_text!r}", _r)

# STREET values end in the possessive marker "-i" (locales/az.py's
# street() always appends "küçəsi"/"prospekti"/"döngəsi"), which takes the
# separate "n"-buffered surface form for dative/locative/ablative
# ("küçəsinə"/"küçəsində"/"küçəsindən"), not the bare/glide form CITY uses
# ("Bakıya"/"Bakıda"/"Bakıdan") -- a real, distinct gap caught by testing
# against an actual STREET value rather than assuming CITY's forms transfer.
# Span policy note above applies here too: `_expected` is the full
# suffixed form, not the bare STREET value.
for _text, _val, _expected in [
    ("Nizami küçəsində oturmuşam.", "Nizami küçəsi", "Nizami küçəsində"),
    ("Nizami küçəsindən keçdim.", "Nizami küçəsi", "Nizami küçəsindən"),
    ("Nizami küçəsinə getdim.", "Nizami küçəsi", "Nizami küçəsinə"),
]:
    _r, _ = resolve_claims(_text, [{"label": "STREET", "text": _val}])
    check(len(_r) == 1 and _r[0]["text"] == _expected,
          f"resolve_claims's STREET span before an 'n'-buffered suffix "
          f"covers the whole inflected phrase: {_text!r}", _r)

# --- extension must not fire beyond the recognized suffix: a bare stem
# mention with NO following letter at all must resolve to exactly the
# stem, unchanged, not silently grow.
_r_bare, _ = resolve_claims("Mən Bakı şəhərində yaşayıram.",
                            [{"label": "CITY", "text": "Bakı"}])
check(len(_r_bare) == 1 and _r_bare[0]["text"] == "Bakı",
      "a bare (uninflected) CITY mention resolves to exactly the stem, "
      "no suffix to swallow", _r_bare)

# --- the hyphen-suffix case (tested above) must NOT be extended: measured
# directly against the real tokenizer, the hyphen already tokenizes as its
# own piece, so a stem-only span ending right before it already lands on a
# real token boundary -- extending it would only lengthen the span for no
# benefit. Reuses a case from the hyphen-suffix block above.
check(_resolved_time[0]["text"] == "10:17",
      "hyphen-suffix span is NOT extended to include '-də' -- the hyphen "
      "already gives a real token boundary, unlike the fused case",
      _resolved_time)

# --- must still reject: fused-suffix leniency must not create a new
# false-accept path for a genuinely different, unrelated word.
for _text, _label, _val in [
    ("Bir neçə Bakılı tanıyıram.", "CITY", "Bakı"),      # compound word "Bakılı"
    ("Bu, Əliağa adlı adamdır.", "GIVENNAME", "Əli"),    # compound name "Əliağa"
]:
    _r, _ = resolve_claims(_text, [{"label": _label, "text": _val}])
    check(len(_r) == 0,
          f"fused-suffix leniency does not admit a different real word: "
          f"{_text!r}", _r)

# --- must not apply outside the 4 ml_context labels: a structured value
# (phone/IBAN/key/...) is never grammatically inflected in real text, and
# checking _AZ_FUSED_NOUN_SUFFIX for one would only add false-accept risk.
_r_struct, _ = resolve_claims("kod 417a görünür",
                              [{"label": "CARD_SECURITY_CODE", "text": "417"}])
check(len(_r_struct) == 0,
      "fused-suffix leniency is scoped to GIVENNAME/SURNAME/CITY/STREET "
      "only -- a non-inflectable label followed by a letter is still "
      "rejected as inside a longer token", _r_struct)

from piigen.llm.dspy_generate import build_fields as _build_fields          # noqa: E402
from piigen.llm.dspy_generate import _INFLECTABLE_LABELS as _INFLECT_LABELS  # noqa: E402
from piigen.llm.specs import DocumentSpec as _DocSpec                       # noqa: E402
from piigen.llm.specs import PlannedEntity as _PlannedEnt                   # noqa: E402

check(_INFLECT_LABELS == {"GIVENNAME", "SURNAME", "CITY", "STREET"},
      "dspy_generate's inflectable-label set matches resolver.py's "
      "(both derived from the same DETECTION_TIERS source)", _INFLECT_LABELS)

_infl_spec = _DocSpec(
    index=0, lang="az", doc_type="complaint_letter", doc_type_hint="t",
    register="formal", band="short", min_chars=100, max_chars=500,
    length_hint="short",
    entities=[_PlannedEnt(label="CITY", value="Bakı"),
             _PlannedEnt(label="PAYMENT_CARD_NUMBER", value="4111111111111111")])
_infl_fields = _build_fields(_infl_spec)
check("fused directly onto this word" in _infl_fields["entities_to_embed"],
      "build_fields attaches the inflection hint to a CITY entity line",
      _infl_fields["entities_to_embed"])
check("fused directly onto this word" not in
      _infl_fields["entities_to_embed"].split("\n")[1],
      "build_fields does NOT attach the inflection hint to a "
      "non-inflectable label's entity line",
      _infl_fields["entities_to_embed"])
check(not _screen(_PROSE, [{"start": 0, "end": 8, "label": "GIVENNAME",
                            "text": "Hörmətli"}],
                  planned=[("GIVENNAME", "Hörmətli"), ("AGE", "45")]),
      "quality_filter: a planned value the model never wrote at all is NOT "
      "flagged by this check (a milder, separately-handled case)")

# --- shapes verified legitimate in the real batch: must NOT be rejected ---
check(not _screen(_PROSE, [{"start": 0, "end": 8, "label": "GIVENNAME",
                            "text": "Hörmətli"}]),
      "quality_filter: an ordinary clean document passes")
# 19/1000 real documents carry strip_diacritics noise and contain no ə/ğ/ş at all.
check(not _screen("Hormetli musteri, sizin muracietiniz sistemde qeyde alinmisdir "
                  "ve texniki komandamiz terefinden arasdirilir. Zehmet olmasa "
                  "bir nece gun gozleyin, netice barede melumat verilecek."),
      "quality_filter: diacritic-stripped document passes (real noise directive)")
# a fleet log repeating a short field label on every record -- 8x in the real batch
check(not _screen("\n".join([f"Vasitə {i}: baxış tamamlandı.\nStatus: Tamamlandı."
                             for i in range(8)])),
      "quality_filter: repeated short field label (structured log) passes")
# markdown table rules repeat once per table -- 3x in the real batch
check(not _screen(_PROSE + "\n" + "\n".join(
          ["| Göstərici | Nəticə | Normal diapazon | Status |",
           "| :--- | :--- | :--- | :--- |"] * 3)),
      "quality_filter: repeated markdown table rules pass")
# a fenced JSON payload inside api_documentation is realistic -- 6x in the real batch
check(not _screen(_PROSE + '\n```json\n{"ad": "Gülnar"}\n```'),
      "quality_filter: fenced code block INSIDE a document passes")
# a letter ending on a signature block, no terminal punctuation -- 86x in the batch
check(not _screen(_PROSE + "\n\nHörmətlə,\nİnsan Resursları Komandası"),
      "quality_filter: signature-block ending passes")
# a very_short document is allowed to be terse -- band-aware floor
check(not _screen("Tələbə: Yeganə – qeydiyyat vaxtı 04:26 oldu.",
                  [{"start": 8, "end": 14, "label": "GIVENNAME", "text": "Yeganə"}],
                  band="very_short"),
      "quality_filter: terse very_short document passes (band-aware floor)")

# --- metrics behave ---
check(carrier_word_count("Ad Elvin qeyd olundu",
                         [{"start": 3, "end": 8, "label": "GIVENNAME",
                           "text": "Elvin"}]) == 3,
      "quality_filter: carrier_word_count excludes words inside entity spans")
check(abs(pii_density("abcdefghij", [{"start": 0, "end": 5}]) - 0.5) < 1e-9,
      "quality_filter: pii_density measures covered character share")

# --- the screen is wired into the real pipeline gate ---
_qf_cfg = GeneratorConfig()
_qf_rng = random.Random(9)
_qf_sampler = SpecSampler(_qf_cfg, ValueFactory(_qf_rng, ValuePool()), _qf_rng)
_qf_spec = next(s for s in (_qf_sampler.sample(i) for i in range(200)) if s.entities)
_qf_text = ("Sənəd üzrə " + ", ".join(e.value for e in _qf_spec.entities) +
            " bu gün qeydə alındı və təsdiqləndi.")
_qf_clean = assemble_document(_qf_spec, _qf_text, _qf_cfg, 0.0)
_qf_dirty = assemble_document(_qf_spec, _qf_text + "\n[[ ## completed ]]",
                              _qf_cfg, 0.0)
check(_qf_clean.ok,
      "assemble_document control: the same document without the artifact is accepted",
      _qf_clean.reason)
check(not _qf_dirty.ok and "quality" in _qf_dirty.reason,
      "assemble_document rejects an adapter artifact via quality_filter",
      _qf_dirty.reason)

# --- zero-width-in-span (2026-08-25): found by audit of the real 24k batch --
# a zero-width character sitting inside an entity's own span, e.g. a real
# STREET value "28 May \u200bprospekti". Legitimate in ordinary carrier text
# (noise injection adds these on purpose); never legitimate inside a value.
from piigen.llm.quality_filter import check_zero_width_in_spans  # noqa: E402

_zw_val = "28 May \u200bprospekti"
check(check_zero_width_in_spans("x", [{"label": "STREET", "text": _zw_val}]),
      "quality_filter: zero-width char inside an entity span is flagged")
check(check_zero_width_in_spans(
    "Salam, \u200bnec\u0259siniz?", [{"label": "GIVENNAME", "text": "Kamil"}]) == [],
    "quality_filter: zero-width char in ordinary carrier text is NOT flagged "
    "(noise injection puts them there on purpose)")

# planned value must contain the SAME zero-width char, or this fails at the
# earlier "missing values" check instead of reaching quality_filter at all.
_zw_planned = "May \u200bk\u00fc\u00e7\u0259si"
_zw_spec = dataclasses.replace(pos_spec, entities=[
    type(pos_spec.entities[0])("STREET", _zw_planned)])
_zw_text = f"S\u0259n\u0259dd\u0259 {_zw_planned} g\u00f6st\u0259rilib v\u0259 bura yaz\u0131n."
_zw_outcome = assemble_document(_zw_spec, _zw_text, gen_cfg, 0.0)
check(not _zw_outcome.ok and "quality" in (_zw_outcome.reason or ""),
      "assemble_document rejects a zero-width char inside a resolved span",
      _zw_outcome.reason)

# --- NFC normalization (2026-08-25): found by the same audit -- 1/24,085 real
# documents was not in NFC form. A decomposed accented character (base letter
# + combining mark, 2 codepoints) and its composed form (1 codepoint) look
# identical but have different lengths; normalizing must happen before any
# offset is computed, or the normalization itself would shift every offset
# past the changed character.
import unicodedata as _ud                                    # noqa: E402
_composed_name = "K" + _ud.normalize("NFC", "o\u0308") + "nul"   # o-umlaut, composed (1 codepoint)
_decomposed_o = _ud.normalize("NFD", _composed_name)               # same text, o + combining mark (2 codepoints)
assert _composed_name != _decomposed_o and len(_composed_name) < len(_decomposed_o), \
    "test fixture bug: these must actually differ in codepoint count"
_nfc_spec = dataclasses.replace(pos_spec, entities=[
    type(pos_spec.entities[0])("GIVENNAME", _composed_name)])
_decomposed_text = (f"S\u0259n\u0259dd\u0259 {_decomposed_o} g\u00f6st\u0259rilib "
                    "v\u0259 burada b\u0259zi \u0259lav\u0259 m\u0259tn d\u0259 var.")
_nfc_outcome = assemble_document(_nfc_spec, _decomposed_text, gen_cfg, 0.0)
check(_nfc_outcome.ok,
      "assemble_document accepts a decomposed-Unicode match after NFC normalization",
      _nfc_outcome.reason)
if _nfc_outcome.ok:
    _e = _nfc_outcome.record["entities"][0]
    check(_nfc_outcome.record["text"][_e["start"]:_e["end"]] == _e["text"],
          "normalized text's offsets are internally consistent (composed form, "
          "not the length the decomposed input would have produced)")

# --- pool exhaustion alarm (2026-08-25): found by audit -- ValuePool.exhausted
# was tracked but had zero readers anywhere in the codebase, so a pool too
# small for the requested volume degraded silently. A tiny pool (2 possible
# values from the factory) under real demand must exhaust fast and warn once.
import logging as _logging                                       # noqa: E402


class _TinyFactory:
    def __init__(self):
        self._toggle = False

    def __call__(self):
        self._toggle = not self._toggle
        return "alpha" if self._toggle else "beta"


_exh_pool = ValuePool(max_share=0.004, attempts=24)
_warn_records = []


class _CaptureHandler(_logging.Handler):
    def emit(self, record):
        _warn_records.append(record.getMessage())


_capture = _CaptureHandler()
_values_log = _logging.getLogger("piigen.values")
_values_log.addHandler(_capture)
_values_log.setLevel(_logging.WARNING)
try:
    _factory = _TinyFactory()
    for _ in range(50):
        _exh_pool.fresh("TESTLABEL", _factory)
finally:
    _values_log.removeHandler(_capture)

check(_exh_pool.exhausted["TESTLABEL"] > 0,
      "ValuePool.exhausted increments once a tiny pool cannot cover demand",
      _exh_pool.exhausted["TESTLABEL"])
check(len(_warn_records) == 1,
      "exactly one warning logged per label, not once per exhausted draw",
      len(_warn_records))
check(_warn_records and "TESTLABEL" in _warn_records[0],
      "the warning names the exhausted label", _warn_records)

# --- and it's actually visible in the real CLI report, not just internal state
import io as _io                                                  # noqa: E402
import contextlib as _contextlib                                  # noqa: E402
from llm_augment_data import print_report as _print_report        # noqa: E402


class _FakeState:
    attempted = 50
    rejections: dict = {}
    dropped_labels: dict = {}
    label_counts: dict = {}
    model = "fake"


class _FakePipeline:
    pool = _exh_pool


_buf = _io.StringIO()
with _contextlib.redirect_stdout(_buf):
    _print_report([], _FakeState(), None,
                  AugmentConfig(num_examples=50, output=Path("x")), _FakePipeline())
check("Value pool exhaustion" in _buf.getvalue() and "TESTLABEL" in _buf.getvalue(),
      "exhaustion is surfaced in the printed run report, not just internal state")

# --- CITY population weighting (2026-08-25): found by audit -- uniform CITY
# sampling gave 45.9x mean reuse and a Baku-vs-village distortion that was an
# artifact of a small pool, not a deliberate choice. Real population is not
# uniform either, so the fix is weighted sampling, not just a bigger list.
_city_rng = random.Random(3)
_city_pool = ValuePool()
_city_factory = ValueFactory(_city_rng, _city_pool)
for _ in range(3000):
    _city_factory.city("az")
_baku_share = _city_pool.counts["CITY"]["Bakı"] / sum(_city_pool.counts["CITY"].values())
_uniform_share = 1.0 / len(LOCALES["az"].cities)
# Two-sided, because the 100k audit found BOTH failure modes are real. The
# original assertion here was one-sided (`> 0.15`) and guarded only against
# silently-uniform sampling. It passed at 45.5% -- which the pool simulation
# then showed was itself the problem: at 100k that is 324x reuse on CITY and
# an effective pool of 15 of 97, so the 80 smallest cities never appear often
# enough to be learned. az.WEIGHT_TEMPERATURE now tempers the weights, and
# both bounds below are load-bearing.
check(_baku_share > 2.0 * _uniform_share,
      "Bakı is still sampled well above an average city (weighting is "
      "taking effect, not silently uniform)",
      f"{_baku_share:.4f} vs uniform {_uniform_share:.4f}")
check(_baku_share < 0.10,
      "Bakı does not dominate CITY (tempering is taking effect, so the "
      "long tail stays learnable at 100k)", _baku_share)
check(_city_pool.counts["CITY"].most_common(1)[0][0] == "Bakı",
      "tempering preserves rank ordering -- the capital is still first",
      _city_pool.counts["CITY"].most_common(3))
check(len(_city_pool.counts["CITY"]) > 20,
      "CITY still uses a real spread of towns, not just the capital",
      len(_city_pool.counts["CITY"]))

# --- weighted cap doesn't fight weighted sampling (the bug caught before
# shipping): a flat max_share cap would hit a heavily-sampled value's ceiling
# almost immediately and force it back toward uniform, defeating the whole
# point of weighting it. A constant-value factory can't exercise this (every
# call succeeds via the exhaustion fallback regardless of cap, since there is
# no alternative candidate to reject in favor of) -- needs real candidates to
# choose among, mirroring how city() actually calls this.
_candidates = ["A", "B", "C", "D", "E"]


def _weight_fn(v):
    return 20.0 if v == "A" else 1.0


def _make_weighted_pick(seed):
    rng = random.Random(seed)
    return lambda: rng.choices(_candidates, weights=[20, 1, 1, 1, 1])[0]


_weighted_cap_pool = ValuePool(max_share=0.004)
_pick_a = _make_weighted_pick(2)
for _ in range(3000):
    _weighted_cap_pool.fresh("WTEST", _pick_a, weight_fn=_weight_fn)
_share_a_weighted = (_weighted_cap_pool.counts["WTEST"]["A"]
                    / sum(_weighted_cap_pool.counts["WTEST"].values()))
check(_share_a_weighted > 0.5,
      "a value proposed 20x as often keeps a correspondingly high share "
      "when the cap scales with its weight", _share_a_weighted)
# (A flat-cap "contrast" version of this test was tried and dropped: with
# only 5 candidates and 3000 draws the pool exhausts constantly regardless of
# weighting, so the exhaustion fallback -- which bypasses any cap -- swamps
# the comparison and makes both scenarios converge. That's a confound in a
# 5-candidate synthetic setup, not evidence against the fix; the real CITY
# measurement above (55 real candidates, Bakı landing at ~32% share matching
# its intended weight) is the actual proof the fix works at realistic scale.)

# --- GIVENNAME dataset scale (2026-08-25): the pool went from ~250
# hand-authored names to ~15,000 real ones supplied by the user, specifically
# to get GIVENNAME's 100k-doc-scale mean reuse under the 5x target (measured
# separately at 4.08x with this dataset, was 112.6x with the prior
# hand-authored expansion). A regression here -- an accidentally truncated or
# corrupted data file -- would silently undo the actual fix, so pin the scale
# directly rather than only testing loader mechanics.
from piigen.locales.az import FIRST_M as _AZ_FIRST_M, FIRST_F as _AZ_FIRST_F  # noqa: E402

check(len(_AZ_FIRST_M) > 5000,
      "FIRST_M loaded from the real dataset, not a small fallback list",
      len(_AZ_FIRST_M))
check(len(_AZ_FIRST_F) > 5000,
      "FIRST_F loaded from the real dataset, not a small fallback list",
      len(_AZ_FIRST_F))
check(len(_AZ_FIRST_M) == len(set(_AZ_FIRST_M)),
      "FIRST_M has no duplicate entries")
check(len(_AZ_FIRST_F) == len(set(_AZ_FIRST_F)),
      "FIRST_F has no duplicate entries")
check(all(n.strip() == n and n for n in _AZ_FIRST_M[:50] + _AZ_FIRST_F[:50]),
      "sampled entries are clean (no stray whitespace/empty lines from "
      "the data file loader)")

# ---------------------------------------------------------------------------
print("14. RunMonitor: rate thresholds smoothed across batch history")
# ---------------------------------------------------------------------------
# 2026-08-26: a live resumed run halted on "english_contamination=0.09 is
# above its stop level 0.08" -- one single ~100-attempt batch, whose
# rejected documents, read directly, were genuine Azerbaijani text
# (informal/diacritic-free spelling), not contamination. Root cause: five
# rate thresholds (acceptance_rate, near_duplicate_rate,
# english_contamination, validator_failure_rate, api_error_rate) all have
# `min_samples` gating whether they're judged at all, and the class's own
# docstring says the question is "is this run drifting?", not "was this one
# batch unlucky?" -- but the VALUE being judged was still
# `metrics.as_metric_values()`'s raw single-batch ratio. The gate opens
# after ~2 batches (cumulative attempts clear min_samples fast); the value
# it gated stayed noisy forever after that, because nothing accumulated it.
from piigen.llm.monitor import RunMonitor, BatchMetrics, DEFAULT_THRESHOLDS  # noqa: E402

_only_english = {"english_contamination": DEFAULT_THRESHOLDS["english_contamination"]}

_mon_spike = RunMonitor(thresholds=_only_english)
for _i in range(1, 19):
    _mon_spike.observe(BatchMetrics(
        batch_no=_i, attempted=100, accepted=65, english_rejects=1,
        total_attempted=_i * 100, throughput_per_hour=500))
_status_spike = _mon_spike.observe(BatchMetrics(
    batch_no=19, attempted=100, accepted=62, english_rejects=9,
    total_attempted=19 * 100, throughput_per_hour=500))
check(_status_spike == "ok",
      "a single noisy batch (9%) buried in 18 clean batches (1% each) "
      "does not trip stop", _status_spike)
check(abs(_mon_spike.history[-1]["values"]["english_contamination"] - 0.0142) < 0.001,
      "the smoothed value reflects the run's real cumulative rate, not "
      "the one noisy batch", _mon_spike.history[-1]["values"]["english_contamination"])

_mon_regression = RunMonitor(thresholds=_only_english)
_stopped_at = None
for _i in range(1, 40):
    _status_reg = _mon_regression.observe(BatchMetrics(
        batch_no=_i, attempted=100, accepted=60, english_rejects=9,
        total_attempted=_i * 100, throughput_per_hour=500))
    if _status_reg == "stop":
        _stopped_at = _i
        break
check(_stopped_at is not None and _stopped_at <= 3,
      "a genuinely persistent regression (9% from batch 1) still stops "
      "quickly -- the fix must not make the check toothless", _stopped_at)

# ---------------------------------------------------------------------------
print("15. Resume restores the sampler's RNG state, not just the counter")
# ---------------------------------------------------------------------------
# 2026-08-26: a live resumed run's very first batch hit acceptance_rate=0.18
# against a 0.675 baseline, driven by a burst of near-duplicate rejections
# (49/82 rejects in that batch) matching document ids scattered across a
# wide swath of the corpus's history. Traced to the actual mechanism:
# `next_spec_index` only numbers documents for id-collision purposes (see
# its own docstring) -- it was never used to fast-forward the RNG. Every
# `--resume` constructed a fresh `random.Random(seed)` and started drawing
# from the beginning of that seed's sequence again, independent of how far
# any prior invocation (this machine or another) had already walked it.
# Silently absorbed by the near-duplicate detector on every single resume
# this project has ever done, until enough overlap concentrated in one
# batch to trip a stop condition, which is what surfaced it.
_rng_check = random.Random(2)
_state = _rng_check.getstate()
_encoded = encode_rng_state(_rng_check)
check(isinstance(_encoded, list) and len(_encoded) == 3,
      "encode_rng_state produces a JSON-safe 3-element structure", _encoded[:1])
_json_roundtrip = _json.loads(_json.dumps(_encoded))
_decoded = decode_rng_state(_json_roundtrip)
check(_decoded == _state,
      "encode/decode round-trips through JSON to the exact original state")

_rng_a, _rng_b = random.Random(2), random.Random(2)
[_rng_a.random() for _ in range(37)]           # simulate mid-run progress
_saved = encode_rng_state(_rng_a)
_rng_b.setstate(decode_rng_state(_json.loads(_json.dumps(_saved))))
check([_rng_a.random() for _ in range(10)] == [_rng_b.random() for _ in range(10)],
      "a restored rng produces the identical future sequence to the "
      "original, not a restart from the seed's beginning")


class _MiniGenerator:
    """Minimal deterministic generator: prose plus each entity's raw value,
    with no literal label names (avoids tripping the taxonomy-leak check)
    and enough sentence variety (keyed on spec.seed) to avoid every doc
    reading as a near-duplicate of every other."""

    model = "fake-model"

    def __init__(self) -> None:
        self.calls = 0

    def load_compiled(self, path: str) -> None:                    # pragma: no cover
        pass

    def stats(self) -> dict:
        return {"calls": self.calls, "retries": 0, "prompt_tokens": 0,
                "completion_tokens": 0, "total_tokens": 0,
                "latency_mean": 0.0, "latency_p50": 0.0, "latency_p95": 0.0}

    def generate(self, spec) -> str:
        self.calls += 1
        loc = LOCALES[spec.lang]
        rng = random.Random(spec.seed)
        body = loc.phrases.sentences("note", rng, 2) + ".\n"
        for ent in spec.entities:
            body += f"{loc.label(_LABEL_KEY.get(ent.label, 'reference'))}: {ent.value}\n"
        return body


def _run_mini(output: Path, num_examples: int, batch_size: int,
             resume: bool = False):
    cfg = AugmentConfig(num_examples=num_examples, batch_size=batch_size,
                        concurrency=1, seed=99, output=output, resume=resume,
                        pool_state=None, noise_rate=0.0)
    pipe = AugmentationPipeline(_MiniGenerator(), cfg)
    rows, state = pipe.run()
    return pipe, rows, state


# Isolate the exact mechanism: the rng state _checkpoint() saved at the end
# of run A must be exactly what _prepare_resume() restores at the start of
# run B -- checked right at that boundary, before B's own batch-pacing
# heuristics (over-request multipliers, acceptance-rate-driven batch
# sizing) have a chance to consume any further draws and make a
# later-in-time comparison sensitive to pacing differences unrelated to
# this fix.
_tmp_split = Path(tempfile.mkdtemp()) / "aug.jsonl"
_pipe_a, _rows_a, _ = _run_mini(_tmp_split, 10, 10)
_state_after_a = _pipe_a.rng.getstate()

_cfg_b = AugmentConfig(num_examples=20, batch_size=10, concurrency=1, seed=99,
                       output=_tmp_split, resume=True, pool_state=None,
                       noise_rate=0.0)
_pipe_b = AugmentationPipeline(_MiniGenerator(), _cfg_b)
_pipe_b._prepare_resume()

check(_state_after_a == _pipe_b.rng.getstate(),
      "the rng state _prepare_resume() restores is exactly what "
      "_checkpoint() saved at the end of the prior invocation -- the "
      "resume genuinely continues the sequence rather than restarting it")

# ---------------------------------------------------------------------------
print("16. Rate-smoothing history survives a resume, bounded")
# ---------------------------------------------------------------------------
# 2026-08-26: the smoothing fix in section 14 (RunMonitor) was scoped to
# ONE RunMonitor instance, i.e. reset on every resume -- which meant a
# fresh process's batch 1 had nothing to smooth against yet and was judged
# alone again, exactly like before that fix existed. Confirmed live: the
# false stop it targets recurred on batch 1 of resumes on the same day the
# fix shipped. Persisting the smoothing state across a resume (bounded by
# _SMOOTHING_CEILING, so it still cannot mask a genuine new regression
# indefinitely) closes that gap.
_only_english = {"english_contamination": DEFAULT_THRESHOLDS["english_contamination"]}

_mon_before = RunMonitor(thresholds=_only_english)
for _i in range(1, 19):
    _mon_before.observe(BatchMetrics(
        batch_no=_i, attempted=100, accepted=65, english_rejects=1,
        total_attempted=85000 + _i * 100, throughput_per_hour=500))
_saved_smoothing = _mon_before.export_smoothing_state()
check(_saved_smoothing["cum_attempted"] == 1800,
      "export_smoothing_state captures this run's real accumulated weight",
      _saved_smoothing)

# A fresh RunMonitor (simulating a new process after --resume) restored
# from that state must NOT re-trip on its own noisy first batch.
_mon_restored = RunMonitor(thresholds=_only_english,
                           smoothing_state=_saved_smoothing)
_status_restored = _mon_restored.observe(BatchMetrics(
    batch_no=1, attempted=100, accepted=62, english_rejects=9,
    total_attempted=85800, throughput_per_hour=500))
check(_status_restored == "ok",
      "a fresh process restored from a healthy checkpoint does not "
      "re-trip on one noisy batch (the exact live false-stop pattern)",
      _status_restored)

# The same batch, same fresh process, WITHOUT restoration -- confirms the
# comparison above is meaningful (i.e. this really is what was failing).
_mon_unrestored = RunMonitor(thresholds=_only_english)
_status_unrestored = _mon_unrestored.observe(BatchMetrics(
    batch_no=1, attempted=100, accepted=62, english_rejects=9,
    total_attempted=85800, throughput_per_hour=500))
check(_status_unrestored == "stop",
      "...confirmed: the identical batch WITHOUT restoration does "
      "reproduce the live false stop", _status_unrestored)

# A genuine, sustained NEW regression starting right after a restore must
# still eventually stop -- restoring healthy history must not make the
# check permanently toothless.
_mon_regression = RunMonitor(thresholds=_only_english,
                             smoothing_state=_saved_smoothing)
_stopped_at = None
for _i in range(1, 200):
    _s = _mon_regression.observe(BatchMetrics(
        batch_no=_i, attempted=100, accepted=60, english_rejects=9,
        total_attempted=85800 + _i * 100, throughput_per_hour=500))
    if _s == "stop":
        _stopped_at = _i
        break
check(_stopped_at is not None and _stopped_at < 100,
      "a genuinely persistent new regression still stops within a "
      "bounded number of batches even after restoring healthy history",
      _stopped_at)

# Round-trips through RunState/JSON exactly like rng_state does.
_rs = RunState(rate_smoothing=_saved_smoothing)
_rs_json = _json.loads(_json.dumps(dataclasses.asdict(_rs)))
check(_rs_json["rate_smoothing"] == _saved_smoothing,
      "rate_smoothing round-trips through RunState -> JSON unchanged")

# ---------------------------------------------------------------------------
print("17. 2026-08-27 audit fixes")
# ---------------------------------------------------------------------------
from piigen.llm.quality import find_leaked_pii as _leak                  # noqa: E402
from piigen.validate import (span_boundary_problems as _sbp,             # noqa: E402
                             turkish_contamination as _turk)
from piigen import checksums as _CK                                      # noqa: E402

# --- the five resolver gaps the audit named, each with the real failing text
for _t, _lab, _val, _why in [
    ("Ümid Fərəcovdur, məni eşidirsən?", "SURNAME", "Fərəcov",
     "copula suffix fused directly onto a surname"),
    ("Mən Kazımli-yəm! Amma mənim", "SURNAME", "Kazımli",
     "1st-person copula behind a hyphen"),
    ("Yeniden deyirem, Saat 14:35-de bu kodlari", "TIME", "14:35",
     "diacritic-FOLDED suffix (-de for -də), which strip_diacritics emits"),
    ("@Şirinlı, qeyd etdiyiniz API xətası", "SURNAME", "Şirinlı",
     "@mention: a leading @ is a boundary for ml_context labels"),
    ("Saat 07:34 AM-da bildiriş gəldi.", "TIME", "7:34 AM",
     "TIME zero-padding disagreement between planner and model"),
]:
    _r, _ = resolve_claims(_t, [{"label": _lab, "text": _val}])
    check(len(_r) == 1, f"resolver gap closed -- {_why}: {_t!r}", _r)

# The @ relaxation must NOT reopen the email case: the trailing rule still
# rejects a name that continues into a domain.
_r_mail, _ = resolve_claims("john@Şirinli.az yazın",
                            [{"label": "SURNAME", "text": "Şirinli"}])
check(len(_r_mail) == 0,
      "a leading @ does not make an email domain resolvable as a SURNAME",
      _r_mail)

# Copula in the FUSED set must not bite into an ordinary short name.
_r_adem, _ = resolve_claims("Adəm gəldi.", [{"label": "GIVENNAME", "text": "Ad"}])
check(len(_r_adem) == 0,
      "fused copula/case leniency does not split 'Adəm' into 'Ad' + suffix",
      _r_adem)

# A planned value present verbatim always beats a surface variant.
_r_pad, _ = resolve_claims("Saat 7:34 və 07:34 arasında.",
                           [{"label": "TIME", "text": "7:34"}])
check(len(_r_pad) == 1 and _r_pad[0]["start"] == 5,
      "the exact planned TIME wins over its zero-padded variant", _r_pad)

# --- apostrophe delimiter: third surface form, span covers the whole word
for _t, _val, _exp in [("Qax'da yaşayıram.", "Qax", "Qax'da"),
                       ("Salyan'ın mərkəzi", "Salyan", "Salyan'ın")]:
    _r, _ = resolve_claims(_t, [{"label": "CITY", "text": _val}])
    check(len(_r) == 1 and _r[0]["text"] == _exp,
          f"apostrophe-suffix span covers the whole word: {_t!r}", _r)

# --- diacritic folding is DERIVED from the same table noise.py uses
from piigen.text import DIACRITIC_MAP as _DMAP, fold_diacritics as _fold  # noqa: E402
from piigen.noise import _DIACRITIC_MAP as _NOISE_MAP                     # noqa: E402
check(_NOISE_MAP is _DMAP,
      "noise.py and resolver.py share ONE diacritic table, so the folded "
      "suffix forms the noise injector emits can never drift out of the "
      "forms the resolver recognises")
check(_fold("də") == "de" and _fold("ilə") == "ile",
      "fold_diacritics reproduces the strip_diacritics surface form")

# --- leak detection now covers every pattern-tier label
_ICCID = "899408715035678901" + _CK.luhn_check_digit("899408715035678901")
for _t, _kind in [
    ("Şəxsiyyət vəsiqəsi də AB6947773-dür.", "AZ_ID_CARD_NUMBER"),
    ("Pasport nömrəm N23662824-dir.", "AZ_PASSPORT_NUMBER"),
    ("VÖEN: 9727925204 qeyd edin.", "AZ_VOEN"),
    ("FIN kodu VU7PGPP olaraq görünür.", "AZ_FIN"),
    ("Sürücülük vəsiqəsi BA154675 nömrəlidir.", "AZ_DRIVER_LICENSE_NUMBER"),
    ("Telefon nömrəsi 0501234567 yazın.", "TELEPHONENUM"),
    ("Açar: sk-ant-api03-AbCdEfGhIjKlMnOpQrStUv", "API_KEY"),
    ("Açar: ghp_AbCdEfGhIjKlMnOpQrStUvWxYz012345", "API_KEY"),
    (f"SIM ICCID {_ICCID} qeydiyyatda.", "ICCID"),
    ("Server 2001:0db8::1 unvani.", "IPV6"),
]:
    _hits = _leak(_t, [], [])
    check(any(h.startswith(_kind) for h in _hits),
          f"leak detector now covers {_kind} (was one of the 21 uncovered "
          f"labels): {_t!r}", _hits)

# ...without becoming trigger-happy. Every one of these is ordinary content.
for _t, _why in [
    ("Saat 14:02:10-da xəta baş verdi.", "a timestamp is not an IPv6 address"),
    ("Saat 16::40-da.", "a noise-mangled timestamp is not an IPv6 address"),
    ("Sifariş kodu HEADERS ilə göndərildi.", "an uppercase word is not an AZ_FIN"),
    ("Sifariş nömrəsi 1234567890 hazırdır.", "10 digits with no VÖEN anchor"),
    ("Ətraflı: https://example.com/haqqimizda", "a URL carrying no token"),
]:
    check(_leak(_t, [], []) == [],
          f"leak detector stays quiet -- {_why}: {_t!r}", _leak(_t, [], []))

# A bare PEM header next to a labeled key is a span-boundary question, not a
# leaked secret -- rejecting the document for it would cost yield for nothing.
_pem = ("Konfiqurasiya:\n-----BEGIN RSA PRIVATE KEY-----\nssh-rsa AAAAB3NzaC1yc2E")
_key_at = _pem.index("ssh-rsa")
check(_leak(_pem, [{"start": _key_at, "end": len(_pem),
                    "label": "PRIVATE_KEY", "text": _pem[_key_at:]}], []) == [],
      "a PEM armour header adjacent to a labeled PRIVATE_KEY is not a leak")
check(any(h.startswith("PRIVATE_KEY") for h in _leak(_pem, [], [])),
      "...but the same header with no labeled key anywhere IS reported")

# Decoys stay exempt under the widened patterns.
check(_leak(f"SIM ICCID {_ICCID} var.", [], [_ICCID]) == [],
      "a deliberately injected decoy is still exempt from the wider leak set")

# --- Turkish contamination, which language_ok structurally cannot see
check(_turk("AZERTECH HIZMET COZUMLERI - HESAB") != [],
      "Turkish lexis is detected")
check(_turk("Qax'da yasayiram.") != [],
      "Turkish apostrophe-before-suffix orthography is detected")
check(_turk("Salam, hər şey əladır və yaxşıdır.") == [],
      "correct Azerbaijani is not flagged as Turkish")
check(_turk("Her sey eladir ve xidmet yaxsidir, mence.") == [],
      "diacritic-FOLDED Azerbaijani is not mistaken for Turkish -- bare "
      "'ve'/'ile' are what strip_diacritics produces from 'və'/'ilə', and "
      "flagging them would condemn ~2,000 deliberately noised records")

# --- span boundary policy
check(_sbp("Xüsusilə, Qubar egionunda problem var.",
           [{"start": 10, "end": 14, "label": "CITY"}]) != [],
      "a span ending mid-word is reported (noise-injector damage)")
check(_sbp("Mən Bakıda yaşayıram.",
           [{"start": 4, "end": 10, "label": "CITY"}]) == [],
      "a span covering the whole inflected word is fine")
check(_sbp("Mən Bakı şəhərində.",
           [{"start": 4, "end": 8, "label": "CITY"}]) == [],
      "a span followed by a space is fine")

# The LEADING edge matters just as much. The first version of this check
# looked only at the trailing edge; the resolver_drift corpus gate then
# surfaced 996 records where the `whitespace` noise kind had glued the
# previous word's last letter onto the FRONT of the span.
_glued = "IP ünvan ı172.30.233.243 kimi"
_gi = _glued.index("172.30.233.243")
check(_sbp(_glued, [{"start": _gi, "end": _gi + 14,
                     "label": "IPV4_ADDRESS"}]) != [],
      "a span glued to the previous word is reported (leading-edge damage)")
check(_sbp("vAxt ı13:41 olaraq", [{"start": 6, "end": 11, "label": "TIME"}]) != [],
      "leading-edge damage is caught for TIME too")
check(_sbp("@Şirinlı, qeyd", [{"start": 1, "end": 8, "label": "SURNAME"}]) == [],
      "an @mention is not leading-edge damage -- @ is not a letter")
check(_sbp("Email: a@b.az yazın",
           [{"start": 7, "end": 13, "label": "EMAIL"}]) == [],
      "a span after 'label: ' is fine")

# --- realized-vs-target label drift
_mon = RunMonitor()
_mon.record_label_outcome(["GIVENNAME", "SURNAME", "CITY"],
                          ["GIVENNAME", "GIVENNAME", "SURNAME"])
_mon.record_label_outcome(["CITY", "STREET"], ["CITY"])
_drift = _mon.label_drift()
check(_drift["STREET"]["realized_pct_of_planned"] == 0.0
      and _drift["CITY"]["realized_pct_of_planned"] == 50.0,
      "label drift measures realized against planned per label", _drift)
check(list(_drift)[0] == "STREET",
      "the worst shortfall sorts first, so it is the first thing read",
      list(_drift)[:3])
check("label_drift" in _mon.report(),
      "label drift is carried in the monitor report that gets written out")


# ---------------------------------------------------------------------------
print()
print("=" * 62)
print(f"PASSED {PASS}   FAILED {FAIL}"
      + (f"   SKIPPED {len(SKIPPED)}" if SKIPPED else ""))
for _s in SKIPPED:
    print("  SKIP", _s)
for failure in FAILURES[:25]:
    print("  FAIL:", failure)
print("=" * 62)

sys.exit(1 if FAIL else 0)
