# Baseline of checkpoint 1

**Task:** P4-6 (P3-4 + D-18b, reassigned by D-21; scope set by D-23f). **Status: partial.** The benchmark part is done. The internal test (Azerbaijani part), the probes on both tracks, the "new names" slice, real text and shadow are still to come; see [Pending](#pending).

Run B is judged against this document (D-23a, D-23f). The main comparison is the first 5,000 documents of `benchmark_v3`. Compare models only on exactly these documents, with the same scorer.

| | |
|---|---|
| Model | `your-hf-org/masking-multilingual` |
| Hub revision (checkpoint 1) | `3a0a6e5df228bdc89dd01312a728e10a78b3e3fb` |
| Code | `main` @ `601f5f7` (clean) |
| Report | [`reports/scoreboard/baseline_ckpt1_benchmark.md`](../reports/scoreboard/baseline_ckpt1_benchmark.md) (`.json` has every number) |
| Benchmark file | `data/benchmark_v3/pii_az_benchmark_v3_structured_9780.jsonl`, SHA-256 `0613031cc4fa867ae638db78fe331f532c31d9a576b0063d58aeca7077d5452d`, first 5,000 lines (D-6) |
| Run | 2026-10-07, the laptop, CPU, offline from the local Hugging Face cache at the revision above; ~1.06 s/doc per track, 2 × 88 min |
| Tracks | **R** = raw HF pipeline, the benchmark's path and the primary number for every gate; **M** = model-only product path (no regex) |
| Shadow | **shadow-dev scored** 2026-10-12 (3,998 documents, 495 of them PII-free; tracks R and M; `tokenizers` 0.22.2; aggregates only, A2.5); see [A6 gates](#a6-gates) |
| Sealed set SHA-256 | `20fbdb946f28e0f6edcb17e39b5ec91766442e1a8a88efc8fb01b4fd02806455` (`sealed.jsonl`, 1,002 documents; **unscored** until the final go/no-go, P3-11) |

## Sets

| Set | Status | Where |
|---|---|---|
| Benchmark, first 5,000 (main comparison) | **done**, tracks R and M | this document |
| Run B v2 test set, `runb-az-v2` `test.docs.jsonl` (D-28), with old/new and old-corpus/new-data splits | **done**, tracks R and M | [Run B v2 test set](#run-b-v2-test-set) |
| Internal test, Azerbaijani part of `merged_relabeled_swept_dated/test` (D-18b, D-23f) | pending: GPU, before Run B | |
| "New names" slice (internal test) | pending: same run | |
| Probes, `eval/probes/` | track R from P3-3; R and M pending | [`probes_ckpt1.md`](../reports/scoreboard/probes_ckpt1.md) |
| Appendix replay | done (P3-1) | [`ckpt1_appendix_R.md`](../reports/scoreboard/ckpt1_appendix_R.md) |
| Adversarial set and red team | done (P4-6, 2026-10-06) | `eval/adversarial_cases.jsonl` |
| Real text (P4-8) | pending: the set does not exist yet | |
| Shadow-dev (A6 gates) | **done**, tracks R and M (aggregates only) | [A6 gates](#a6-gates) |
| Golden EN, TR and RU sets | not needed: D-23a drops the language regression gate for Run B | |

## A6 gates

The gates are defined on shadow-dev, track R. The shadow-dev column is checkpoint 1's baseline: the run on 2026-10-12, server CPU, code `1f09896`, `tokenizers` 0.22.2, same revision as above (a first run on 2026-10-09 used `tokenizers` 0.23.2 and is discarded, D-37). The set's two files have the combined SHA-256 recorded in `eval/leakage_guard_shadow.json.gz`; shadow texts never leave the private folder (A2.5). The benchmark column is the same metric on the benchmark, track R, for reference.

| Gate | Shadow-dev | Benchmark (R) | Sprint 1 target | Sprint 2 target |
|---|---|---|---|---|
| Micro F1 (exact) | **66.9** | **68.7** | ≥ 76 | ≥ 82 |
| Weakest label F1 | **38.5** (ACCESS_TOKEN) | **0.0** (ACCESS_TOKEN) | ≥ 50 | ≥ 65 |
| ACCESS_TOKEN F1 | **38.5** | **0.0** | ≥ 50 | ≥ 75 |
| IPV6_ADDRESS F1 | **84.4** | **18.0** | ≥ 50 | ≥ 75 |
| AZ_DRIVER_LICENSE_NUMBER F1 | **45.8** | **40.4** | ≥ 50 | ≥ 75 |
| Hard-negative trigger rate (same label) | **34.6%** | **17.0%** | < 12% | < 8% |
| PII-free document FP rate | **73.7%** (365 of 495) | **44.0%** | < 30% | < 15% |
| Recall guard (no label −1 pt) | baseline itself | baseline itself | | |
| Sealed set | untouched | | untouched | run once |

On the benchmark, checkpoint 1 misses every sprint-1 target. On shadow-dev it misses every sprint-1 target except IPv6 F1 (exact P 57.7 / R 79.8). Track M on shadow-dev: micro F1 70.7 (P 62.2 / R 81.9), ACCESS_TOKEN 38.6, IPv6 87.3, licence 52.2, PII-free FP 70.9%. Run B's shadow-dev result and the recall guard against this baseline are recorded in D-39a.

## Benchmark: overall

| | R | M |
|---|---|---|
| Exact P / R / F1 (micro) | 63.7 / 74.6 / **68.7** | 66.5 / 77.0 / **71.4** |
| Macro F1 | 67.7 | 70.5 |
| Overlap F1 | 73.1 | 73.3 |
| PII character leakage | 15.0% | 14.6% |
| Gold: exact / missed / wrong label / split | 7,845 / 1,583 / 677 / 338 | 8,100 / 1,573 / 671 / 171 |
| Hard-negative trigger, same label (any label) | 17.0% (25.9%) | 18.1% (26.6%) |
| PII-free documents with an FP | 269 / 612 = 44.0% | 264 / 612 = 43.1% |
| Perfect documents | 30.9% | 32.2% |

- **Agreement with the benchmark report.** Track R gives 68.7 micro F1; the report gave 68.4. D-6 expects close, not identical, numbers, because this file carries the team's corrections (10,518 gold here vs 10,438 in the report).
- **M is 2.7 points above R.** Most of the gain is boundaries: split spans fall from 338 to 171, and exact hits rise by 255 while overlap hits barely move (8,258 → 8,274). Missed (1,583 vs 1,573) and wrong-label (677 vs 671) counts are almost the same on both tracks, so those are the model's own errors, not the decoding's.

## Benchmark: per label

Sorted by track-R F1. Gold = TP + FN.

| Label | Gold | R: P / R / **F1** | M: P / R / F1 |
|---|---|---|---|
| ACCESS_TOKEN | 385 | 0.0 / 0.0 / **0.0** | 0.0 / 0.0 / 0.0 |
| IPV6_ADDRESS | 446 | 54.5 / 10.8 / **18.0** | 67.7 / 15.0 / 24.6 |
| AZ_DRIVER_LICENSE_NUMBER | 404 | 40.9 / 39.9 / **40.4** | 54.5 / 43.6 / 48.4 |
| CARD_SECURITY_CODE | 309 | 27.6 / 93.9 / **42.6** | 27.5 / 92.2 / 42.3 |
| MAC_ADDRESS | 374 | 41.4 / 60.2 / **49.0** | 35.8 / 59.9 / 44.8 |
| PAYMENT_CARD_NUMBER | 390 | 54.5 / 44.9 / **49.2** | 64.3 / 49.5 / 55.9 |
| API_KEY | 371 | 41.2 / 62.8 / **49.7** | 45.0 / 64.2 / 52.9 |
| DATE | 394 | 71.2 / 48.2 / **57.5** | 69.2 / 54.8 / 61.2 |
| AZ_ID_CARD_NUMBER | 384 | 55.2 / 79.4 / **65.1** | 58.3 / 81.2 / 67.9 |
| BUILDINGNUM | 379 | 50.2 / 92.9 / **65.2** | 50.4 / 93.9 / 65.6 |
| ZIPCODE | 385 | 55.1 / 80.5 / **65.4** | 60.3 / 87.0 / 71.2 |
| AGE | 396 | 54.6 / 84.6 / **66.3** | 63.4 / 82.3 / 71.6 |
| TIME | 413 | 56.0 / 88.4 / **68.5** | 59.0 / 91.8 / 71.8 |
| IBAN | 426 | 82.1 / 59.4 / **68.9** | 99.6 / 64.6 / 78.3 |
| AZ_FIN | 395 | 58.3 / 94.7 / **72.1** | 61.4 / 97.0 / 75.2 |
| GIVENNAME | 404 | 60.8 / 98.3 / **75.1** | 64.4 / 98.8 / 77.9 |
| AZ_VOEN | 353 | 70.4 / 84.4 / **76.8** | 79.0 / 87.5 / 83.1 |
| IPV4_ADDRESS | 424 | 76.8 / 78.1 / **77.4** | 72.4 / 83.5 / 77.5 |
| CITY | 385 | 83.9 / 75.8 / **79.7** | 86.8 / 77.1 / 81.7 |
| TELEPHONENUM | 398 | 84.1 / 91.7 / **87.7** | 89.0 / 97.2 / 92.9 |
| AZ_PASSPORT_NUMBER | 366 | 86.7 / 92.9 / **89.7** | 90.9 / 95.9 / 93.4 |
| PRIVATE_KEY | 428 | 88.3 / 93.2 / **90.7** | 77.9 / 97.2 / 86.5 |
| EMAIL | 403 | 99.7 / 86.8 / **92.8** | 99.4 / 86.8 / 92.7 |
| SURNAME | 387 | 89.0 / 98.7 / **93.6** | 89.7 / 99.0 / 94.1 |
| STREET | 359 | 91.3 / 96.9 / **94.1** | 92.3 / 96.9 / 94.6 |
| ICCID | 399 | 95.9 / 93.7 / **94.8** | 99.2 / 95.5 / 97.3 |
| URL | 361 | 95.7 / 97.8 / **96.7** | 99.4 / 99.7 / 99.6 |

### Where the weakest labels' gold goes

Each gold span is counted once: exact; same label with a wrong boundary; covered by another label (the most frequent one is named); or missed. Counted from the run's prediction cache, track R; M is in brackets where it differs by more than 10 spans.

| Gold label | Exact | Wrong boundary | Another label | Missed |
|---|---|---|---|---|
| ACCESS_TOKEN (385) | 0 | 0 | **246 as API_KEY** | 139 |
| IPV6_ADDRESS (446) | 48 (M 67) | 21 | **130 as MAC_ADDRESS** | 247 |
| AZ_DRIVER_LICENSE_NUMBER (404) | 161 (M 176) | 19 | **213 as AZ_ID_CARD_NUMBER** | 11 |
| PAYMENT_CARD_NUMBER (390) | 175 (M 193) | 37 (M 17) | 0 | **178** |
| DATE (394) | 190 (M 216) | 12 | 0 | **192** (M 163) |
| MAC_ADDRESS (374) | 225 | 31 | 0 | 118 |
| API_KEY (371) | 233 | 43 | 0 | 95 |
| CARD_SECURITY_CODE (309) | 290 | 2 | 3 as AGE | 14 |

- **The model never predicts ACCESS_TOKEN.** The label is in its head (27 labels), but there are 0 predictions: 64% of the tokens are tagged API_KEY, and the rest are missed.
- **IPV6 and driver licences are mostly confusions:** IPv6 read as MAC, licence read as ID card. These are the contrast pairs sprint 1 targets (token/key, IPv6/MAC, licence/ID).
- **CARD_SECURITY_CODE and BUILDINGNUM are a precision problem.** Recall is above 92%, but precision is 28% and 50%: short numbers are masked too often.
- **PAYMENT_CARD_NUMBER and DATE are a recall problem:** about half of the gold is missed outright.

## Benchmark: by category

Exact recall per `_benchmark_category` (doc-level slice). P/R/F1 and trigger rates per category are in the JSON.

| Category | Docs | Gold | Exact recall R / M | Exact P (R) | Trigger, same label (R) |
|---|---|---|---|---|---|
| positive_control | 242 | 871 | 79.8 / 81.5 | 79.0 | 21.7% |
| mixed | 803 | 2,187 | 75.9 / 78.2 | 60.2 | 17.9% |
| natural_variant_positive | 518 | 1,552 | 74.1 / 76.5 | 82.5 | – |
| anchor_variant_positive | 361 | 1,084 | 70.6 / 73.7 | 80.3 | – |
| hard_negative | 1,553 | 1,300 | 70.5 / 72.6 | **39.2** | 13.8% |
| natural_variant_hard_negative | 534 | 1,047 | 71.1 / 72.7 | 68.6 | 20.2% |
| anchor_variant_hard_negative | 414 | 793 | 73.5 / 75.4 | 70.7 | 18.9% |
| corrected_hard_negative | 64 | 151 | 76.8 / 76.8 | 62.4 | **83.6%** |
| structured_json_config | 103 | 309 | 83.8 / 90.0 | 65.9 | 22.8% |
| structured_pipe_table | 112 | 336 | 82.7 / 84.2 | 67.6 | 24.6% |
| structured_dialogue | 103 | 309 | 82.2 / 83.8 | 63.8 | 31.6% |
| structured_technical_log | 93 | 279 | 78.1 / 87.5 | 60.4 | 24.2% |
| structured_csv | 100 | 300 | 69.0 / 70.0 | 60.7 | 8.0% |

- **`hard_negative` documents carry half of all look-alikes** (4,634 of 9,304), and precision there is 39%. They are the largest single source of false positives.
- **`corrected_hard_negative`: 51 of its 61 look-alikes trigger.** These are the documents whose decoys the benchmarking team rewrote (D-6 example: `1234567890` → `Y47-G59`). The rate is computed over only 61 decoys.
- **Structured layouts:** M's largest recall gains are on technical logs (+9.4) and JSON configs (+6.2).

## Benchmark: look-alikes

The benchmark declares its look-alikes as strings without offsets. The scoreboard places each one at its first occurrence that overlaps no gold span (P4-6 task log). All 9,304 are placed.

| Placement | Decoys | Trigger, same label R / M | Any label R / M |
|---|---|---|---|
| unique place | 8,828 | 17.3% / 18.6% | 25.6% / 26.3% |
| ambiguous (more than one free occurrence) | 476 | 11.3% / 10.5% | 32.1% / 31.9% |
| **all** | **9,304** | **17.0% / 18.1%** | **25.9% / 26.6%** |

The ambiguous placements do not move the overall rate.

## Run B v2 test set

**Task:** P3-4 (D-28: the baseline uses v2's `test.docs.jsonl`). **Status: done**, tracks R and M.

**Corrected 2026-10-12.** The first version of this section (PR #34) was scored with `tokenizers` 0.23.2, which keeps only the first 512-token window of a long document: every span after it was lost (2,146 documents are longer than one window; 5,748 of the 57,120 gold spans, 10.1%, end after it). `requirements.txt` already pins `tokenizers<0.23` (D-37). These numbers are a new run with `tokenizers` 0.22.2 and a new prediction cache filled only by that version.

| | |
|---|---|
| Test file | `runb-az-v2` `test.docs.jsonl` (not in git), 15,835 documents, SHA-256 `3254d8ad51cd41e06cb6cf92093d725beafaec2b6e106691feca7ed719c45bd1` (= D-28) |
| Report | [`reports/scoreboard/baseline_ckpt1_runb.md`](../reports/scoreboard/baseline_ckpt1_runb.md) (`.json` has every number, per label and per part) |
| Code | `1f09896` (clean), `transformers` 4.57.6, `tokenizers` 0.22.2 |
| Run | 2026-10-12, server CPU, `nice -n 19`, 8 threads, offline from the local Hugging Face cache, tracks R and M |
| Splits | **old / new**: 9,410 / 6,425 (id list `eval/runb_v2_test_parts.tsv.gz`). **Old corpus / new data**, by id prefix: 8,935 / 6,900 |
| Id list | `eval/runb_v2_test_parts.tsv.gz`: every v2 test id with its part, origin and a text hash (no text). The scoreboard uses it by default (`--runb-parts`) |

Exact-span percentages. PII-free FP = share of documents without gold PII that get at least one prediction.

| Split | Docs | R: P / R / F1 | R: macro F1 | R: PII-free FP | M: P / R / F1 | M: macro F1 | M: PII-free FP |
|---|---|---|---|---|---|---|---|
| Overall | 15,835 | 89.6 / 81.7 / 85.5 | 85.4 | 14.9 | 92.9 / 83.7 / 88.1 | 89.4 | 14.4 |
| Old: same id and text in v1's test split | 9,410 | 96.0 / 82.9 / 89.0 | 92.5 | 1.5 | 98.3 / 84.7 / 91.0 | 95.7 | 1.4 |
| New: v2 only | 6,425 | 79.3 / 79.5 / 79.4 | 76.9 | 45.1 | 84.2 / 81.9 / 83.0 | 81.7 | 43.7 |
| Old corpus (id prefix `repaired.clean__` / `negatives.clean__`) | 8,935 | 96.6 / 83.0 / 89.3 | 93.3 | 0.3 | 98.9 / 84.8 / 91.3 | 96.5 | 0.2 |
| New data (targeted + LLM b1–b5) | 6,900 | 79.8 / 79.7 / 79.8 | 77.2 | 45.1 | 84.4 / 82.0 / 83.2 | 81.8 | 43.7 |

**Weakest labels** (overall exact F1, gold spans in brackets):

- Track R: DATE 38.3 (8,828), PRIVATE_KEY 65.9 (468), ACCESS_TOKEN 67.3 (894), AZ_DRIVER_LICENSE_NUMBER 75.9 (1,064), CARD_SECURITY_CODE 78.8 (600), IPV6_ADDRESS 80.1 (696).
- Track M: DATE 40.2 (8,828), ACCESS_TOKEN 69.9 (894), IPV6_ADDRESS 82.7 (696), CARD_SECURITY_CODE 83.2 (600), AZ_DRIVER_LICENSE_NUMBER 83.2 (1,064), MAC_ADDRESS 85.6 (681).

Per-label F1 for every split is in the report's "Run B test split by part" tables.

**Against the first version:** overall F1 R 81.3 → **85.5**, M 82.0 → **88.1**; almost all of the change is recall (R 74.2 → 81.7, M 73.5 → 83.7), as expected from spans that are no longer cut off. Run B on the same file, same version: R 96.5, M 99.0 (numbers, reproduced).

**Two guesses, both untested** (not checked against the errors yet):

- **New data scores lower** (R micro F1 79.8 against 89.3 on the old corpus), mostly on precision (79.8 against 96.6), and 45.1% of its PII-free documents get a prediction against 0.3% in the old corpus. Possibly because the new data carries the anchored decoys and look-alikes (P2-2, P2-4) that checkpoint 1 never trained on.
- **DATE is the weakest label** (R F1 38.3 on 8,828 gold spans). Possibly because checkpoint 1 was trained before D-17 labelled every standalone date, so it never learned to tag them.

## Earlier checkpoint-1 results

- **Appendix replay (P3-1, track R, CPU):** the scoreboard reproduces **4,273 / 4,273** of the report's listed wrong predictions and still misses **2,592 / 2,592** of its listed gold, on the 3,347 appendix documents with rebuilt text. PASS.
- **Probes (P3-3, track R only):** exact F1 53.6 over 1,320 documents, **0 of 40** families pass their target, and 40 of 40 show their failure. The probes have not changed since (`f45ba16`). R and M are rescored with the GPU run.
- **Adversarial set (model only):** leak rate **65.8%** (48 of 73 expected entities missed). Worst: `suffix_attached` (14/20 missed), `non_digit_form` (5/5), `all_caps` (4/4).
- **Red team:** RT-2 to RT-6 reproduce. They test `pii_guard` code, not the model, so they are regression checks and are not expected to move with training. Model-level: RT-8 has 4 typo pairs that evade; RT-7 and RT-8b are negative.

## Pending

| What | Who | When |
|---|---|---|
| Internal test, Azerbaijani part, tracks R and M, and the "new names" slice. The scoreboard reports P/R/F1 per set; an Azerbaijani-only internal-test set (or per-language P/R/F1) is needed first, because D-23f asks for the Azerbaijani part | the team (code), the team (GPU) | before Run B |
| Probes, tracks R and M | same GPU run | before Run B |
| Real-text set (P4-8) | the team | before Run B is judged |

## How to reproduce

```bash
python eval/scoreboard.py --model your-hf-org/masking-multilingual \
    --revision 3a0a6e5df228bdc89dd01312a728e10a78b3e3fb \
    --name baseline_ckpt1_benchmark --sets benchmark --public-only
```

Without a Hub login for the private repo, set `HF_HUB_OFFLINE=1` and load the model from a local cache that holds this revision. The default tracks are R and M.
