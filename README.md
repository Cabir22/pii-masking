# PII Masking Model

A token-classification model that finds personal data in **Azerbaijani,
English, Turkish and Russian** text so it can be masked before the text leaves
an organisation. It covers 27 labels: names, addresses, dates and ages, phone
numbers and e-mails, cards and IBANs, network addresses, keys and tokens, and
the Azerbaijani national identifiers (FIN, ID card, passport, VÖEN, driving
licence).

The model is a fine-tuned `xlm-roberta-large`. Around it the project built a
synthetic-data generator, a translation pipeline, a scoring and release-check
framework, red-team tooling, and the masking product itself (DOCX, PPTX, TXT,
CSV and XLSX).

## Status: finished

The project is complete. All the work described here is done, and every
number below was measured and is reproducible from the reports in `reports/`.

| Model | Data | Benchmark micro F1 (5,000 AZ docs) | Notes |
|---|---|---|---|
| checkpoint 1 (starting point) | original corpus | 68.4 (raw) / 72.1 (track M) | 44% of PII-free documents get a false alarm |
| v4 | Azerbaijani v4 | 96.1 | cards, CVV, surnames, ID cards, VÖEN and cities fixed |
| **v4.2** | Azerbaijani v4.2 | **97.0** | best Azerbaijani model: 13 of 14 blocking release rules (A6 misses by about 1 point on IPv6 and card recall); real text: 87.3% of values found, precision 92.1% |
| m1 | AZ v4.2 + EN/TR/RU translations | 96.4 | TR 89.4 → 93.8, RU 89.2 → 95.1; known gap: MAC addresses in some contexts |

"Track M" is the product decoding in `model/predict.py`; "raw" is the model
alone, as the original benchmark called it.

- **Benchmark:** `benchmarks/SUMMARY.md` and `reports/benchmark_report/`.
- **Release checks:** `reports/scoreboard/release_check/`, one folder per candidate.
- **Multilingual audit:** `reports/m1_audit/REPORT.md`.
- **Final multilingual build:** `scripts/build_m2.py` assembles the last
  dataset (m1 plus the targeted extra batch and relabels). `scripts/gpu/run_m2.sh`
  trains it.

### Lessons

- **Inject values, don't ask for them.** An LLM asked for "an example card"
  writes Stripe test cards and 555 numbers. The generator mints valid values
  itself and the LLM only writes the text around them.
- **Never let the model return offsets.** Every occurrence is located
  afterwards by the resolver, so offset errors cannot happen.
- **Look-alikes matter as much as positives.** Decoys (invalid checksums,
  dummy values, order numbers next to FIN-like codes) took false alarms on
  PII-free benchmark documents from 44% to 6–13%, depending on the track.
- **Native-speaker review catches what metrics don't.** Case suffixes, names
  that are also ordinary words, and gendered patronymics were all found by
  reading samples, then became rules and tests.
- **Freeze the rules before reading results.** The release rules
  (`eval/release_check.py`) were written before the first candidate was scored.

## Where things are

| Path | What it is |
|---|---|
| `model/` | training (`train.py`) and inference (`predict.py`, with the `validity-2` decoder) |
| `scripts/piigen/` | the Azerbaijani data generator: values, decoys, anchors, noise, validation, the LLM pipeline, targeted sentence frames |
| `scripts/translate/` | the EN/TR/RU translation pipeline (gender, case suffixes and dates kept) |
| `scripts/build_m1.py`, `scripts/build_m2.py` | multilingual dataset builds from pinned inputs, with hash reports |
| `scripts/*.py` | corpus building and repair: splits, relabelling, validation, sweeps |
| `scripts/gpu/` | training recipes, one per model version, with data checksums |
| `eval/` | scoreboard, probe families (`probes/`, `probes_tr/`), metrics, leakage guard, release check |
| `benchmarks/` | the 5,000-document benchmark report and everything extracted from it |
| `redteam/`, `audit/`, `scripts/redteam/` | adversarial probes, red-team findings, the multi-format audit |
| `scripts/pii_guard/`, `formats/` | the masking product: DOCX/PPTX (`pii_guard`) and TXT/CSV/XLSX (`formats`). Known issues: `formats/KNOWN_ISSUES.md` |
| `mask_cli.py`, `demo/` | try the model on one sentence; a manual real-data demo |
| `docs/` | dataset and training references, structure, findings |
| `data/` | label schema, raw and processed corpora, reference and sample files |
| `reports/` | generated evaluation, audit and data-quality reports |

Large data files (`data/**/*.jsonl`) are not in git. They live in a Hugging
Face dataset repo and are fetched with `bash scripts/hf/fetch_data.sh <folders>`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

The model and data names in the code use the placeholder `your-hf-org`.
Replace it with the Hugging Face account that holds your copies.

## Trying the model

```bash
python mask_cli.py "Mənim adım Əli Məmmədovdur"
python mask_cli.py --raw "Mənim adım Əli Məmmədovdur"   # model only, no fallback rules
```

## Scoring a model

```bash
python eval/scoreboard.py --model your-hf-org/<model> --revision <full sha> --name <run>
bash scripts/release_check.sh your-hf-org/<model> <full sha>   # every release rule, one report
```

## Generating data

The key is read from the environment only — never from argv, where it would
land in shell history and `ps` output.

```bash
export COMPANY_API_KEY="<key>"       # PowerShell: $env:COMPANY_API_KEY="<key>"
python scripts/llm_augment_data.py --list-models
python scripts/llm_augment_data.py --model <id> --num-examples 300
python scripts/llm_augment_data.py --model <id> --num-examples 300 --resume

# optional: compile few-shot demonstrations against a real trainset before a big run
python scripts/dspy_compile.py --model <id>
python scripts/llm_augment_data.py --model <id> --num-examples 300 \
    --compiled scripts/piigen/llm/compiled/program.json

python scripts/test_llm_augment.py   # 229 assertions, no network required
```


The pipeline: **Taxonomy → SpecSampler (decides WHAT: broad realistic
sampling, plus some share of documents deliberately targeting a case from the
edge-case catalog) → DSPy generation (decides HOW: one Signature, routed at
the endpoint via litellm) → validation → quality filtering (dedup, leaked-PII
detection, judgment-word-leak detection) → dataset.**

| Module | Role |
|---|---|
| `llm/dspy_generate.py` | the Signature, `dspy.LM` construction, and `DSPyGenerator` — the only file that knows the endpoint/model config |
| `llm/edge_cases.py` | catalog of specific per-label cases (valid + collision/near-miss), sourced from the (repo-external) PII Edge Case Specification |
| `llm/specs.py` | `SpecSampler` — the brief: broad sampling (deficit-weights rare labels) plus edge-case-catalog targeting |
| `llm/quality.py` | leaked-PII detector, judgment-word-leak detector, near-duplicate rejection |
| `llm/checkpoint.py` | atomic state writes, crash-safe resume |
| `llm/pipeline.py` | `assemble_document` (the acceptance gate) + concurrent batches, per-batch checkpoints, stall guards |

**Values are injected, not requested.** `ValueFactory` mints the PII and the
model writes text around it. An earlier version asked the model to invent
example PII and got Stripe test cards, the verbatim AWS documentation key, and
555 numbers in 33% / 82 / 152 cases respectively — the predictable result of
asking a model for "an example credit card," not a wording problem.

**The model never returns offsets, or even a list of what it embedded.** It
returns plain text; we already know which values were planned (`spec.entities`)
and locate every occurrence with `resolver.resolve_claims`. Offset errors
become structurally impossible, every repeat mention is labeled for free, and
there is no JSON envelope for the model to get wrong in the first place —
DSPy's own adapter handles response structure.

Every generated example is checked against `validate.py`'s full structural
gate (span offsets, no overlaps, checksum validity per label, Azerbaijani
language authenticity, Turkish contamination, span-boundary policy) plus
three LLM-specific checks: unlabeled PII the model invented (which would
teach false negatives), the model editorializing about a decoy/entity's
correctness instead of just using it (a real defect found in early
edge-case-catalog runs), and near-duplicates.

**Leak detection covers every `pattern`-tier label.** The model does invent
PII despite being told not to, and an unlabeled real entity is worse than a
rejected document — it teaches the detector that this exact shape is *not*
PII. High-precision shapes are rejected on sight; collision-prone ones
(`AZ_FIN` vs. an order ID, a bare `AZ_VOEN` vs. a national phone number)
additionally require a licensing word nearby, so the gate cannot collapse
generation yield. Measured cost on the existing corpus: 0.61% of records.

`scripts/validate_corpus.py` runs the same rules over a whole committed
corpus, plus two gates that only make sense at corpus scale: an independent
full-text PII sweep (deliberately *not* anchored to the planned-value list —
that is what makes it able to find PII nothing planned) and `resolver_drift`,
which asserts every record still reproduces under the current resolver. The
second is what keeps resolver fixes from being forward-only; without it,
records annotated before a fix keep their stale spans indefinitely.

### Support library — `piigen`

| Module | Role |
|---|---|
| `config.py` | locked taxonomy (`ENTITY_TYPES`, `DETECTION_TIERS`) + every tunable generation distribution in one place |
| `checksums.py` | Luhn / IBAN mod-97 / VIN / IMEI / MAC / IP — used to *generate* and to *verify* |
| `blocklist.py` | placeholder denylist (test cards, doc keys, 555 numbers, fictional names) |
| `locales/` | one file per language (currently just `az`): name morphology, address grammar, phone plan, national ID, phrase banks |
| `values.py` | `ValueFactory` — checksum-valid, high-entropy, deduplicated across runs |
| `negatives.py` | hard negatives + adversarial near-misses (invalid checksums, truncated keys, masked values) |
| `noise.py` | OCR / typo / diacritic-strip / encoding corruption with exact offset repair |
| `resolver.py` | labels **every** occurrence; longest-match-first overlap resolution |
| `validate.py` | full structural validation for every label |
| `analyze.py` | quality metrics + generalization estimate |

**The invariant everything protects:** a span is recorded at the moment its
text is appended to the buffer. Offsets are never recovered afterwards by
string search, so tokenizer/label-alignment bugs cannot originate here. Any
transformation applied later (noise, quoting, indentation) remaps spans
arithmetically through an explicit edit stream.
