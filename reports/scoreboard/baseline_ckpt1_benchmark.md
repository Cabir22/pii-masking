# Scoreboard: baseline_ckpt1_benchmark

| | |
|---|---|
| Model | `your-hf-org/masking-multilingual` |
| Revision SHA | `3a0a6e5df228bdc89dd01312a728e10a78b3e3fb` |
| Requested revision | `3a0a6e5df228bdc89dd01312a728e10a78b3e3fb` |
| Code git SHA | `b227f67b7fd4315d2d6cdf36d32b6bdf3bac4327` |
| Date (UTC) | 2026-10-15T13:22:11Z |
| Device | cpu |
| Libraries | tokenizers 0.22.2, transformers 4.57.6, torch 2.11.0+cu128, python 3.12.14 |
| Tracks | R = raw HF pipeline (simple), M = model-only product path |
| Data version | benchmark `b272b758eb6e4e5e` |

## A6 gates (shadow_dev, track R)

`benchmark` is the same metric on that set, track R: a reference while the shadow numbers are pending, never a gate.

| Gate | Measured | benchmark | Sprint 1 target | S1 | Sprint 2 target | S2 | Note |
|---|---|---|---|---|---|---|---|
| micro_f1 | n/a | 68.7 | >= 76.0 | – | >= 82.0 | – | shadow_dev not scored: shadow pending |
| weakest_label_f1 | n/a | 0.0 | >= 50.0 | – | >= 65.0 | – | shadow_dev not scored: shadow pending |
| ACCESS_TOKEN_f1 | n/a | 0.0 | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| IPV6_ADDRESS_f1 | n/a | 18.0 | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| AZ_DRIVER_LICENSE_NUMBER_f1 | n/a | 40.4 | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| hard_negative_trigger_rate | n/a | 17.0 | < 12.0 | – | < 8.0 | – | shadow_dev not scored: shadow pending |
| pii_free_fp_rate | n/a | 44.0 | < 30.0 | – | < 15.0 | – | shadow_dev not scored: shadow pending |
| recall_guard | n/a | n/a | no label -1 pt | – | no label -1 pt | – | no --baseline given |
| en_tr_ru_regression | n/a | n/a | <= 1 pt drop | – | <= 1 pt drop | – | no --baseline given |
| appendix_known_errors_fixed | n/a | n/a | reported by class | – | reported by class | – | appendix not scored |
| sealed_set | untouched | n/a | untouched | PASS | run once | – |  |

## Sets

Percentages. Exact = label+start+end. Trigger = decoy hit with the label it resembles (any label in brackets).

| Set | Track | Docs | Exact P / R / F1 | Macro F1 | Overlap F1 | Char leak | Narrower | Split | Trigger | Control FP | PII-free FP | Perfect |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| benchmark | R | 5000 | 63.7 / 74.6 / 68.7 | 67.7 | 73.1 | 15.0 | 86.9 | 338 | 17.0 (25.9) | – | 44.0 | 30.9 |
| benchmark excl. policy | R | 5000 | 65.0 / 74.6 / 69.5 | 68.4 | 73.9 | 15.0 | 86.9 | 338 | 16.4 (24.6) | – | 42.2 | 32.0 |
| benchmark | M | 5000 | 66.5 / 77.0 / 71.4 | 70.5 | 73.3 | 14.6 | 98.9 | 171 | 18.1 (26.6) | – | 43.1 | 32.2 |
| benchmark excl. policy | M | 5000 | 67.8 / 77.0 / 72.1 | 71.3 | 74.1 | 14.6 | 98.9 | 171 | 17.6 (25.3) | – | 41.0 | 33.5 |

### Slices: benchmark (exact recall / overlap recall / split spans)

| Slice | Value | Gold | R | M |
|---|---|---|---|---|
| doc:_adversarials | 0 | 2908 | 73.2 / 77.2 / 93 | 75.9 / 77.6 / 50 |
| doc:_adversarials | 1 | 2511 | 74.4 / 77.6 / 66 | 76.1 / 77.3 / 31 |
| doc:_adversarials | 2 | 2611 | 77.2 / 81.8 / 99 | 80.0 / 81.9 / 47 |
| doc:_adversarials | 3 | 1332 | 73.6 / 77.1 / 38 | 76.0 / 77.6 / 22 |
| doc:_adversarials | 4 | 1116 | 74.0 / 78.2 / 40 | 76.3 / 78.1 / 19 |
| doc:_adversarials | 5 | 40 | 65.0 / 70.0 / 2 | 70.0 / 75.0 / 2 |
| doc:_benchmark_category | anchor_variant_hard_negative | 793 | 73.5 / 77.0 / 24 | 75.4 / 76.7 / 10 |
| doc:_benchmark_category | anchor_variant_positive | 1084 | 70.6 / 75.2 / 41 | 73.7 / 75.6 / 20 |
| doc:_benchmark_category | corrected_hard_negative | 151 | 76.8 / 79.5 / 3 | 76.8 / 78.1 / 2 |
| doc:_benchmark_category | hard_negative | 1300 | 70.5 / 74.5 / 43 | 72.6 / 74.6 / 25 |
| doc:_benchmark_category | mixed | 2187 | 75.9 / 79.8 / 73 | 78.2 / 80.1 / 40 |
| doc:_benchmark_category | natural_variant_hard_negative | 1047 | 71.1 / 74.3 / 28 | 72.7 / 73.8 / 11 |
| doc:_benchmark_category | natural_variant_positive | 1552 | 74.1 / 77.8 / 43 | 76.5 / 78.0 / 24 |
| doc:_benchmark_category | positive_control | 871 | 79.8 / 82.8 / 22 | 81.5 / 83.4 / 16 |
| doc:_benchmark_category | structured_csv | 300 | 69.0 / 74.3 / 16 | 70.0 / 73.3 / 10 |
| doc:_benchmark_category | structured_dialogue | 309 | 82.2 / 84.5 / 7 | 83.8 / 84.5 / 2 |
| doc:_benchmark_category | structured_json_config | 309 | 83.8 / 88.7 / 15 | 90.0 / 90.6 / 2 |
| doc:_benchmark_category | structured_pipe_table | 336 | 82.7 / 85.4 / 9 | 84.2 / 85.7 / 5 |
| doc:_benchmark_category | structured_technical_log | 279 | 78.1 / 88.5 / 14 | 87.5 / 88.9 / 4 |
| doc:_bucket | long | 5640 | 72.7 / 76.6 / 187 | 75.0 / 76.9 / 105 |
| doc:_bucket | medium | 3342 | 75.7 / 79.1 / 90 | 77.6 / 78.9 / 43 |
| doc:_bucket | short | 3 | 66.7 / 66.7 / 0 | 66.7 / 66.7 / 0 |
| doc:_bucket | structured | 1533 | 79.3 / 84.3 / 61 | 83.1 / 84.6 / 23 |
| doc:_doc_type | bank_message | 665 | 75.9 / 78.8 / 19 | 76.7 / 78.2 / 10 |
| doc:_doc_type | crm | 704 | 72.9 / 76.6 / 26 | 74.7 / 76.4 / 12 |
| doc:_doc_type | csv | 300 | 69.0 / 74.3 / 16 | 70.0 / 73.3 / 10 |
| doc:_doc_type | dialogue | 309 | 82.2 / 84.5 / 7 | 83.8 / 84.5 / 2 |
| doc:_doc_type | email | 684 | 74.6 / 77.2 / 18 | 76.2 / 77.8 / 11 |
| doc:_doc_type | first_person_chat | 838 | 75.7 / 79.6 / 21 | 78.5 / 80.4 / 15 |
| doc:_doc_type | first_person_email | 912 | 74.3 / 80.2 / 29 | 78.1 / 79.9 / 16 |
| doc:_doc_type | first_person_form | 924 | 74.4 / 80.1 / 30 | 78.8 / 81.4 / 23 |
| doc:_doc_type | form | 744 | 71.1 / 74.1 / 22 | 72.6 / 74.3 / 13 |
| doc:_doc_type | insurance | 628 | 76.9 / 79.3 / 15 | 77.9 / 78.3 / 3 |
| doc:_doc_type | json_config | 309 | 83.8 / 88.7 / 15 | 90.0 / 90.6 / 2 |
| doc:_doc_type | legal | 699 | 70.2 / 73.8 / 25 | 72.1 / 73.8 / 12 |
| doc:_doc_type | pipe_table | 336 | 82.7 / 85.4 / 9 | 84.2 / 85.7 / 5 |
| doc:_doc_type | report | 709 | 72.4 / 75.9 / 24 | 74.5 / 75.6 / 8 |
| doc:_doc_type | support_ticket | 745 | 73.7 / 77.6 / 29 | 75.6 / 77.3 / 13 |
| doc:_doc_type | technical_log | 279 | 78.1 / 88.5 / 14 | 87.5 / 88.9 / 4 |
| doc:_doc_type | technical_note | 733 | 73.3 / 75.9 / 19 | 74.6 / 76.3 / 12 |
| doc:_hard_negatives | 0 | 2960 | 73.2 / 77.2 / 94 | 75.8 / 77.6 / 52 |
| doc:_hard_negatives | 1 | 2503 | 74.4 / 77.6 / 66 | 76.0 / 77.3 / 32 |
| doc:_hard_negatives | 2 | 2603 | 77.3 / 81.8 / 98 | 80.2 / 81.9 / 44 |
| doc:_hard_negatives | 3 | 1359 | 74.1 / 77.7 / 40 | 76.6 / 78.3 / 23 |
| doc:_hard_negatives | 4 | 1066 | 73.3 / 77.5 / 38 | 75.6 / 77.4 / 18 |
| doc:_hard_negatives | 5 | 27 | 59.3 / 66.7 / 2 | 66.7 / 74.1 / 2 |
| doc:_register | bureaucratic | 1816 | 73.8 / 77.9 / 59 | 76.3 / 77.8 / 26 |
| doc:_register | casual | 1771 | 73.1 / 76.3 / 43 | 75.1 / 76.8 / 30 |
| doc:_register | formal | 1817 | 73.8 / 77.6 / 61 | 75.7 / 77.4 / 30 |
| doc:_register | neutral | 1686 | 74.4 / 78.6 / 59 | 76.9 / 78.9 / 34 |
| doc:_register | technical | 3428 | 76.3 / 80.4 / 116 | 79.1 / 80.7 / 51 |
| doc:_source | benchmark_structured_v3 | 1533 | 79.3 / 84.3 / 61 | 83.1 / 84.6 / 23 |
| doc:_source | benchmark_synthetic_diverse | 8985 | 73.8 / 77.5 / 277 | 76.0 / 77.7 / 148 |
| doc:lang | az | 10518 | 74.6 / 78.5 / 338 | 77.0 / 78.7 / 171 |
| doc:density | 0 | 0 | – / – / 0 | – / – / 0 |
| doc:density | 1 | 978 | 67.0 / 71.1 / 36 | 69.0 / 71.0 / 18 |
| doc:density | 2-3 | 6966 | 74.9 / 78.9 / 225 | 77.5 / 79.0 / 101 |
| doc:density | 4-6 | 2574 | 76.5 / 80.2 / 77 | 78.7 / 80.8 / 52 |

Calibration (score bins vs precision) is in the JSON. It is reported only and is never used to set a threshold (A2.2).
