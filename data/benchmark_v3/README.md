# benchmark_v3 — the benchmarking dataset, for evaluation only

**Use: evaluation only. Never train on it, replay it, mine frames from it, or
put it under `data/processed/` or into any training mix** (decision D-6,
rule A2.3). Its values
and 8-grams belong in the leakage guard (`eval/leakage_guard.py`, P3-5).

## Which documents to score (D-6, 2026-10-02)

**Score models on the first 5,000 documents only** (ids `bench_az_000001` … `bench_az_005000`, the first 5,000 lines). Those are the documents the benchmarking team scored. Counted against the report:

| | First 5,000 | Report |
|---|---|---|
| Gold values | 10,518 | 10,438 |
| Planted look-alikes | 9,304 | 9,384 |
| PII-free documents | 612 | 627 |

The differences are the team's corrections. The other 4,780 documents are not part of the benchmark. Keep all 9,780 in the leakage guard.

## What it is

`pii_az_benchmark_v3_structured_9780.jsonl`: 9,780 Azerbaijani documents with
gold entity spans and declared hard negatives, from the benchmarking team's
generator. Added to the repo on 2026-10-01 so the Gemma 4 vs BERT benchmark can
score against it. It is **not** the exact file behind the 355-page report.

| | |
|---|---|
| SHA-256 | `0613031cc4fa867ae638db78fe331f532c31d9a576b0063d58aeca7077d5452d` |
| Documents | 9,780 (ids `bench_az_000001` … `bench_az_009780`, all unique) |
| Gold entities | 20,602 mentions, all 27 labels; 1,188 documents with none; 7,803 with declared hard negatives |
| Spans | `text[start:end] == entity text` on every entity (checked) |
| Sources | `benchmark_synthetic_diverse` 8,780, `benchmark_structured_v3` 1,000 |

**Categories** (`_benchmark_category`): hard_negative 3,000; mixed 1,500;
natural_variant_hard_negative 1,080; natural_variant_positive 1,021;
anchor_variant_hard_negative 810; anchor_variant_positive 768; positive_control
465; corrected_hard_negative 136; structured (json_config, csv, technical_log,
pipe_table, dialogue) 200 each.

## How it relates to the report

- It contains **all 3,464 documents** listed in the report's appendix (same ids).
- For 843 of the 3,347 appendix documents that carry text, **the text differs**
  from the report. These are corrected hard negatives and structured documents
  (for example `bench_az_000005`: the decoy `1234567890` is now `Y47-G59`).
- It adds **4,780 documents** the report never listed (ids above 5,000).

So a score on this file is **not directly comparable** with the report's 68.4
micro F1. To compare models, score them all on this same file with the same
scorer. To reproduce the report's numbers, use the appendix replay instead.

## Record schema

`id`, `text`, `lang` (`"az"`), `entities` (`start`, `end` exclusive, `label`,
`text`), and metadata: `_doc_type`, `_bucket`, `_register`, `_noise`,
`_hard_negatives`, `_adversarials`, `_source`, `_benchmark_category`, `_spec`
(planned entities, `hard_negatives` with `hard_negative_labels`, `distractors`,
noise settings). Scoring is exact: label, start and end must all match.

## Notes

- Secret-shaped strings (`sk_test_…` keys, PEM blocks) occur only inside gold
  entities. They are the benchmark's own synthetic values.
- Stored through Git LFS like every `.jsonl` under `data/`.
- Where this folder lives is the decision (D-6); `git mv` it if they
  prefer another place outside `data/processed/`.
