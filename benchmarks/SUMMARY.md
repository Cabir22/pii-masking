# 5000-document benchmark — extracted results (checkpoint 1)

Source: `benchmarks/masking_multilingual_benchmark_5000_detailed_report.pdf`
(355 pages, Azerbaijani, generated 2026-09-23). Model:
`your-hf-org/masking-multilingual`, **checkpoint 1**. This is not checkpoint 2
(the multinational-name model), which has not been shared.

Every number below carries its PDF page (`p.N`). Everything the report states
is in `extracted/results.json`; every recomputation is in
`extracted/sanity_checks.json`.

## Headline (p.1, p.3)

| Metric | Value | Recomputed from TP/FP/FN |
|---|---|---|
| Micro F1 | 68.4% | 68.4% ✓ |
| Precision | 63.4% | 63.4% ✓ |
| Recall | 74.4% | 74.4% ✓ |
| Macro F1 | 67.6% | 67.6% ✓ (mean of the 27 per-label F1s, p.4) |
| Weighted F1 | 67.9% | 67.9% ✓ |
| TP / FP / FN | 7761 / 4482 / 2677 | TP+FP = 12243 predictions ✓, TP+FN = 10438 gold ✓ |
| Perfect documents | 1536 / 5000 (30.7%) | + 3464 appendix documents = 5000 ✓ |
| Documents with ≥1 FP / FN | 2649 / 2054 | recounted from the appendix ✓ |
| PII-free documents over-masked | 282 / 627 (45.0%) | not checkable from the appendix |

The report's verdict (p.21) is "release not recommended" without three things: a validator layer, a targeted retrain, and confirmation on the frozen 5000 plus a human-gold set. None of its proposed gates are met (p.21).

## What the benchmark corpus is

- **Azerbaijani only.** All 3464 appendix document IDs are `bench_az_*`, and no page has a per-language breakdown. It says nothing about EN, TR or RU.
- **Synthetic.** Addresses use `synthetic-mailN.invalid`. There are two generator sources: `legacy_v2` (4489 docs) and `structured_v3` (511) (p.12).
- **Built around hard negatives.** 13 categories partition the 5000 docs, and 2565 of them are hard-negative categories (p.12). 627 documents contain no PII at all (p.16). 9384 look-alike values are planted as "must not be masked" (sum of p.7).
- **Scoring:** exact label + start + end (p.1). A span one character off counts as one FP and one FN (p.2).
- **Run:** Apple MPS, batch size 1, 851.21 s. 0 hash mismatches between predictions and dataset. No document exceeds 512 tokens (p.2).

## How the model was called — raw, not our pipeline

The report says "raw model" but not how it was invoked. `check_inference_path.py` reruns 80 random appendix documents both ways (`extracted/inference_path_check.json`):

| Inference path | Report's error predictions reproduced (label + exact span) |
|---|---|
| Plain HF `pipeline(aggregation_strategy="simple")` | **94 / 94**, scores within 0.0005 (max 0.00049) |
| Our production path: `predict.load_model` + `hybrid_detect_entities` (from `origin/excel-txt` @ `e88ef69`) | 64 / 94 |

The report therefore measures the raw model through a plain Hugging Face pipeline. That means:

- no punctuation-boundary tokenizer patch,
- no word-consistency fix,
- no `pattern_fallback` regex/checksum layer,
- no `pii_guard` anchors, gazetteer or chunking.

Its numbers are **not comparable** to numbers measured through `hybrid_detect_entities` or `pii_guard`. On the same 80 documents, the production path gets 19 of the report's 56 misses exactly right: IBAN 5/5, driver licence 7/7, DATE 2/2, EMAIL 2/2. It gets none of the ACCESS_TOKEN (0/10), IPv6 (0/8) or card-number (0/5) misses. Production's own extra false positives can't be measured from the appendix, so this is not a re-score. `pii_guard` itself was not run.

The exact score match also shows the Hub weights used today are the ones the benchmark ran. The report records no model revision.

## Per-label results (p.4, weakest first)

| Label | TP | FP | FN | P | R | F1 |
|---|---|---|---|---|---|---|
| ACCESS_TOKEN | 0 | 0 | 385 | 0.0 | 0.0 | 0.0 |
| IPV6_ADDRESS | 47 | 42 | 399 | 52.8 | 10.5 | 17.6 |
| CARD_SECURITY_CODE | 212 | 872 | 17 | 19.6 | 92.6 | 32.3 |
| AZ_DRIVER_LICENSE_NUMBER | 162 | 227 | 242 | 41.6 | 40.1 | 40.9 |
| MAC_ADDRESS | 224 | 322 | 150 | 41.0 | 59.9 | 48.7 |
| PAYMENT_CARD_NUMBER | 174 | 147 | 216 | 54.2 | 44.6 | 48.9 |
| API_KEY | 233 | 333 | 138 | 41.2 | 62.8 | 49.7 |
| DATE | 188 | 79 | 206 | 70.4 | 47.7 | 56.9 |
| AZ_ID_CARD_NUMBER | 305 | 247 | 79 | 55.3 | 79.4 | 65.2 |
| ZIPCODE | 309 | 253 | 76 | 55.0 | 80.3 | 65.3 |
| BUILDINGNUM | 352 | 345 | 27 | 50.5 | 92.9 | 65.4 |
| AGE | 335 | 277 | 61 | 54.7 | 84.6 | 66.5 |
| TIME | 365 | 289 | 48 | 55.8 | 88.4 | 68.4 |
| IBAN | 254 | 53 | 172 | 82.7 | 59.6 | 69.3 |
| AZ_FIN | 374 | 252 | 21 | 59.7 | 94.7 | 73.3 |
| GIVENNAME | 397 | 257 | 7 | 60.7 | 98.3 | 75.0 |
| IPV4_ADDRESS | 330 | 99 | 94 | 76.9 | 77.8 | 77.4 |
| CITY | 292 | 56 | 93 | 83.9 | 75.8 | 79.7 |
| AZ_VOEN | 298 | 75 | 55 | 79.9 | 84.4 | 82.1 |
| AZ_PASSPORT_NUMBER | 339 | 52 | 27 | 86.7 | 92.6 | 89.6 |
| PRIVATE_KEY | 399 | 53 | 29 | 88.3 | 93.2 | 90.7 |
| TELEPHONENUM | 364 | 40 | 34 | 90.1 | 91.5 | 90.8 |
| EMAIL | 350 | 1 | 53 | 99.7 | 86.8 | 92.8 |
| SURNAME | 382 | 47 | 5 | 89.0 | 98.7 | 93.6 |
| STREET | 348 | 33 | 11 | 91.3 | 96.9 | 94.1 |
| ICCID | 375 | 15 | 24 | 96.2 | 94.0 | 95.1 |
| URL | 353 | 16 | 8 | 95.7 | 97.8 | 96.7 |

All 27 rows recompute exactly, and their TP/FP/FN sum to the global totals. The per-label FP and FN counts also match an independent recount of the 3464-document appendix. All 27 labels are in `piigen.config.DETECTION_TIERS`, and every repo label appears. No foreign labels.

## Biggest failure modes (computed from `extracted/errors.csv`)

The report's error taxonomy (p.3) is reproduced **exactly** from the appendix.

| | Count | Reproduced |
|---|---|---|
| FN: `missed` / `wrong_label` / `boundary_error` / `wrong_label_and_boundary` | 1585 / 620 / 413 / 59 | ✓ all four |
| FP: `hard_negative_trigger` / `spurious` / `wrong_label` / `boundary_error` / `wrong_label_and_boundary` | 1784 / 1362 / 620 / 571 / 145 | ✓ all five |

The report's `spurious` (1362) is made of two things:

- 627 predictions with nothing planted nearby.
- 735 predictions on a planted look-alike, but under a different label than the one it was planted for.

**1. Over-masking of planted look-alikes: 2519 of 4482 FPs (56%).**
- CARD_SECURITY_CODE alone accounts for 872 FPs, and 87.2% of its planted cases trigger (p.7).
- The worst values repeat across many documents: CVV `12345` ×275, TIME `25:81` ×126, ZIPCODE `AZ1994` in an IBAN field ×95.
- The 4482 FPs come from just 1744 distinct values; the top 20 values make up 35.6% of all FPs.
- These FPs are high-confidence: same-label decoy triggers have a median score of 0.979, and only 19% score below 0.8.

**2. ACCESS_TOKEN: 0 of 385 found (p.4, p.6).**
- 229 were masked as API_KEY with the exact span, plus 17 with a different span. 139 were fully missed.
- Page 6 counts 254 ACCESS_TOKEN→API_KEY confusions, because it counts both exact-span and boundary pairs.

**3. IPv6: 399 FN** (246 missed, 131 labelled MAC). All 399 are `::`-compressed.

**4. Driver licence → ID card: 224** (p.6). 210 of these are exact-span wrong labels.

**5. Plain misses of well-formed values** (almost all in prose documents: 177/178, 191/192, 131/133):

| Label | FN | Fully missed |
|---|---|---|
| PAYMENT_CARD_NUMBER | 216 | 178 |
| DATE | 206 | 192 |
| IBAN | 172 | 133 |

**6. Spurious names and building numbers.**
- GIVENNAME: 246 spurious, mostly the word `Ərizənin` ("of the application") and its fragments.
- BUILDINGNUM: 252 spurious, mostly room numbers ("otaq").

**7. Boundary errors look like subword fragmentation.**
- Page 11 says 86.9% of boundary FPs are *narrower* than the gold span, which can leave part of the PII exposed.
- On documents whose text rebuilds exactly, the predicted span starts or ends inside a word for 51% of boundary FPs (260/508) and 80% of wrong-label-and-boundary FPs (110/138).

## Other breakdowns (p.12–p.17)

- **Format (p.13).** Structured key-value formats have the highest recall: json_config 83.8, pipe_table 82.7, dialogue 81.9. Prose-type documents sit at 70–77, and CSV is lowest at 69.3. EMAIL is 0% F1 in CSV, dialogue, JSON, pipe table and log (n = 6+12+10+14+10 = 52, p.14), which is essentially all 53 EMAIL misses.
- **Entity density (p.16).** Single-entity documents score F1 54.6%; three or more entities score 73.8%.
- **Noise (p.15).** Clean text recall is 75.7%, orthographic noise 72.3%, typo noise 73.6%. These slices overlap, so they don't sum to 5000.
- **Register (p.15)** barely matters (67.3–69.6 F1).
- **Threshold (p.17).** A global 0.90 threshold gives F1 72.7 with recall 71.2. Even at 0.99, 1581 FPs remain. The report's FP mean score of 0.856 matches the appendix (0.8555).

## Extraction method and checks

- **Tool.** PyMuPDF `find_tables` for the table grid, with each cell read by `get_text(clip=cell)`. pdfplumber isn't installed in the venv. PyMuPDF's own cell text drops underscores out of some label cells; the clipped read keeps them.
- **Coverage.** 368 tables were saved: 34 on the analysis pages (1–21) and one per appendix page (22–355). The 3464 appendix documents parsed with 0 unparsed fragments.
- **Sanity checks: 87 of 103 pass.**
  - **6 are explained failures, recorded as failing:**
    - Noise slices overlap (4 checks).
    - The appendix prints scores to 3 decimals, which moves a few FPs across bin edges. The bin totals still agree.
    - Page 7's CVV/ZIPCODE count, still unresolved (see below).
  - **10 are real contradictions inside the report**, listed below.
  - Two P/R/F1 values sit exactly on a .x5 rounding tie (253/400 = 63.25%). The report rounds these down, so they pass with a note.
- **Visual spot-checks.** Rendered pages were compared cell by cell against the CSVs: p.3 (2 tables), p.4, p.6 (2), p.7, p.12 (2), p.13, p.16 (3), p.17 (2) and p.21 (2), which is 18 tables on 9 pages. Appendix pages p.178 (10 documents) and p.355 were also compared against the parsed records. All matched.
- **Known extraction limits:**
  - The 28 multi-line PEM `PRIVATE_KEY` values display one character off, because one line break inside them is real and one is wrapping. Their spans are correct.
  - 117 documents' text can't be rebuilt so that every span lines up; `text` is empty for those.
  - In the example tables (p.6, p.9–p.11), values that wrap inside a cell come out in the CSV with a space inserted.

## Needs a human

1. **Page 7 vs the appendix, CVV.** Page 7 says 478 of 548 planted CVV look-alikes triggered (87.2%). The appendix shows a same-label prediction on all 548.
   - The same rule reproduces page 7 exactly for the other 25 labels; ZIPCODE is off by one (110 vs 111).
   - It isn't explained by values listed under two labels. 126 CVV look-alikes are also listed as AZ_FIN, which doesn't produce 70.
2. **Ten summary sentences contradict the report's own tables.**
   - p.5: driver licence F1 "41.1%" (table: 40.9); card recall "43.1%" (44.6); "DATE / GIVENNAME F1 54–56%" (GIVENNAME is 75.0).
   - p.12: hard-negative precision "37.6%" (38.2); positive-control F1 "77.3%" (79.4).
   - p.13: CSV F1 "55.5%" (65.7); JSON/config F1 "71.3%" (73.8, and pipe_table at 74.2 is actually highest).
   - p.15: first-person F1 "65.5%" / other "66.2%" (67.7 / 68.7); orthographic noise costs "5.6" recall points (3.4).
   - All ten look like prose left over from an earlier run. Treat the tables as current.
3. **Page 8 on separator CVVs.** Page 8 says 3-digit CVVs written with a separator are scored as *positives*, yet `12-3` appears as a planted hard negative 79 times in the appendix. Separately, the page-8 value table is a top-35 cut (all AZ_FIN at 100%), not the full list.
4. **171 planted spans are listed under two target labels.** 126 are AZ_FIN + CVV, e.g. `fin_kodu`/`cvv` both set to `12345` in the JSON of `bench_az_004993`. This inflates per-label hard-negative line counts.
5. **Our policy call, not a report error.** Some planted "must not mask" values are valid under our own schema:
   - 76 × `1234` in a CVV field (our CVV is 3–4 digits),
   - 7-character FINs,
   - `P12345678` as a passport,
   - `4242424242424242`, which passes the Luhn check,
   - `14:30 versiyası`, which contains a valid time.

   Whether masking these counts as an error is for us to decide before tuning against this benchmark.
6. **The report records no model revision or hash.** Exact score reproduction today shows the Hub weights haven't changed since the run.

## Cross-check against earlier work

| Earlier finding | What the report shows | Verdict |
|---|---|---|
| ~98.7% F1 on `data/golden/golden_{az,en}.jsonl` | 68.4% micro-F1 on longer, adversarial, hard-negative-heavy AZ documents. Even the **positive_control** category is only 79.4 F1 (p.12). Several labels use value shapes our generator never produces (next row). | Consistent with a distribution gap. Not only "harder documents": format mismatches too. |
| Our training corpus (this session's audit of `data/processed/merged`) | Benchmark ACCESS_TOKENs are 100% `at_`/`bearer_`/`tok_`; our 15,455 training tokens are 100% JWT-shaped. Benchmark IPv6 is 100% `::`-compressed; 0 of 8,033 training IPv6 values contain `::`. Benchmark driver licences use `AA`/`AB`, which training uses almost only for ID cards (21,909 vs 40). | Explains ACCESS_TOKEN (0%), IPv6 (17.6%) and the driver licence ↔ ID card confusion. |
| Recall depends on a value sitting beside its field label (`Label: value` > prose > bare cell) | Key-value formats (JSON 83.8, pipe 82.7, dialogue 81.9) > prose formats (70–77) > CSV bare cells (69.3) (p.13) | **Agrees** directionally; absolute levels are lower. |
| BUILDINGNUM ~0% as a bare cell | Recall 92.9% (p.4), but the benchmark's BUILDINGNUMs almost always have an anchor ("bina 73"). New: 345 FPs, mostly unlabeled room numbers. | Not tested either way. |
| Clause chunking (`detect/_chunk.py`) +12 recall | Raw HF pipeline, no chunking; no document exceeds 512 tokens (p.2) | Not testable from this report. |
| RT-2: invisible Unicode evades regex/checksum detectors | 0 of 3464 error documents contain zero-width characters in the extracted text (PDF extraction may drop them) | Not exercised by the benchmark. |
| "Span/boundary" = subword fragmentation | 51% of boundary FPs and 80% of wrong-label-and-boundary FPs start or end mid-word; the plain HF pipeline has no word-consistency fix | **Agrees**. |
| Raw model vs full `pii_guard` pipeline | Raw model via a plain HF pipeline, reproduced 94/94 with matching scores | **Confirmed raw.** Not comparable to `pii_guard` or `hybrid_detect_entities` numbers. |
| Label taxonomy (earlier fixture used POSTAL_CODE/ORGANIZATION/ACCOUNT_NUMBER) | All labels are within the repo's 27 | **No issue.** |

## Files

| Path | Contents |
|---|---|
| `extract_report.py` | PDF → `page_index.json`, `tables/`, `records.json` |
| `analyze_report.py` | → `results.json`, `errors.csv`, `error_analysis.json`, `sanity_checks.json` |
| `check_inference_path.py` | → `inference_path_check.json` (needs the model) |
| `extracted/page_index.json` | per page: section, kind, tables |
| `extracted/tables/pNNN_tK.csv` | all 368 tables, verbatim |
| `extracted/errors.csv` | 9847 rows: 2677 unmatched gold + 4482 unmatched predictions + 2688 touched hard negatives, each with its PDF page |
| `extracted/results.json` | every report table and chart value, with page numbers, plus a glossary (AZ term → English) |
| `extracted/error_analysis.json` | counts by error class × label, score distributions, concentration, fragmentation |
| `extracted/sanity_checks.json` | 103 checks: reported vs recomputed, pass/fail, explanations |
| `extracted/records.json` | Appendix A parsed per document |

### Glossary (full list in `results.json`)

| Term | English |
|---|---|
| Tam miss | full miss (no overlapping prediction) |
| Span/boundary | right label, wrong span edges |
| Yanlış label | wrong label |
| Label + span | wrong label and wrong span |
| Spurious mask | mask where no entity is expected |
| Hard-negative trigger | model masked a planted look-alike |
| HARD-NEGATIVE (maskalanmamalıdır) | hard negative (must not be masked) |
| Heç nə tapılmayıb | nothing found |
| Bu mövqedə entity gözlənilmir | no entity expected at this position |
| Əsas FP/FN səbəbi | main FP/FN cause |
| Təklif edilən gate | proposed release gate |
