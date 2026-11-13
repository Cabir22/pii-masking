# Scoreboard: ckpt1_appendix_R

| | |
|---|---|
| Model | `your-hf-org/masking-multilingual` |
| Revision SHA | `3a0a6e5df228bdc89dd01312a728e10a78b3e3fb` |
| Requested revision | `None` |
| Code git SHA | `0e92d3f1fba2344c2979f722feff078d03f88ed8` (eval/ or model/ dirty) |
| Date (UTC) | 2026-09-30T19:06:58Z |
| Device | cpu |
| Tracks | R = raw HF pipeline (simple) |
| Data version | appendix `14f875483075d6e0` |

## A6 gates (shadow_dev, track R)

| Gate | Measured | Sprint 1 target | S1 | Sprint 2 target | S2 | Note |
|---|---|---|---|---|---|---|
| micro_f1 | n/a | >= 76.0 | – | >= 82.0 | – | shadow_dev not scored |
| weakest_label_f1 | n/a | >= 50.0 | – | >= 65.0 | – | shadow_dev not scored |
| ACCESS_TOKEN_f1 | n/a | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored |
| IPV6_ADDRESS_f1 | n/a | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored |
| AZ_DRIVER_LICENSE_NUMBER_f1 | n/a | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored |
| hard_negative_trigger_rate | n/a | < 12.0 | – | < 8.0 | – | shadow_dev not scored |
| pii_free_fp_rate | n/a | < 30.0 | – | < 15.0 | – | shadow_dev not scored |
| recall_guard | n/a | no label -1 pt | – | no label -1 pt | – | no --baseline given |
| en_tr_ru_regression | n/a | <= 1 pt drop | – | <= 1 pt drop | – | no --baseline given |
| appendix_known_errors_fixed | FN fixed 0/2592, FP removed 0/4273 | reported by class | – | reported by class | – |  |
| sealed_set | untouched | untouched | PASS | run once | – |  |

## Sets

Percentages. Exact = label+start+end. Trigger = decoy hit with the label it resembles (any label in brackets).

| Set | Track | Docs | Exact P / R / F1 | Macro F1 | Overlap F1 | Char leak | Narrower | Split | Trigger | Control FP | PII-free FP | Perfect |
|---|---|---|---|---|---|---|---|---|---|---|---|---|

## Appendix replay (errors only: no P/R/F1 on this set)

Only the 3347 of 3464 appendix documents whose text was rebuilt exactly can be re-run, so every count below is restricted to them: 4273 of the report's 4482 listed wrong predictions, 2592 of its 2677 listed missed gold and 2555 of its 2688 touched decoys. The other 117 documents have no usable text in the PDF extraction (benchmarks/extract_report.py accepts a rebuild only if every listed span lands on its value).

| Track | Listed FP reproduced | FP removed | Listed FN still missed | FN fixed | Decoys still triggered (same label) | Unjudgeable new preds | New preds on listed |
|---|---|---|---|---|---|---|---|
| R | 4273/4273 (100.0) | 0 | 2592/2592 (100.0) | 0 | 2555/2555 (1650) | 4789 | 0 |

By error class, track R:

| error_class | FP reproduced | FP removed | FN still missed | FN fixed | Decoy still triggered | Decoy cleared |
|---|---|---|---|---|---|---|
| boundary_error | 508 | 0 | 380 | 0 | 0 | 0 |
| hard_negative_other_label | 703 | 0 | 0 | 0 | 0 | 0 |
| hard_negative_trigger | 1713 | 0 | 0 | 0 | 0 | 0 |
| missed | 0 | 0 | 1563 | 0 | 0 | 0 |
| other_label | 0 | 0 | 0 | 0 | 905 | 0 |
| same_label | 0 | 0 | 0 | 0 | 1650 | 0 |
| spurious | 619 | 0 | 0 | 0 | 0 | 0 |
| wrong_label | 592 | 0 | 592 | 0 | 0 | 0 |
| wrong_label_and_boundary | 138 | 0 | 57 | 0 | 0 | 0 |

## Reproduction check (track R): **PASS**

- listed wrong predictions reproduced exactly: 4273/4273 = 100.0% (need ≥ 99%)
- listed gold still missed: 2592/2592 = 100.0% (need ≥ 99%)
- denominators: documents with text only (see the appendix section above)

Calibration (score bins vs precision) is in the JSON. It is reported only and is never used to set a threshold (A2.2).
