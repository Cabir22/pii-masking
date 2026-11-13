# Scoreboard: new_benchmark

| | |
|---|---|
| Model | `/private/tmp/claude-501/-Users-user-HAL-X-pii-masking-model/692921e0-3cc7-4991-bb18-a10eb02fa39f/scratchpad/v3_puncttok` |
| Revision SHA | `local-sha256:6e2f021c5ef3744d` |
| Requested revision | `None` |
| Code git SHA | `c195e64ca5dcc93d8ca5b37d65d6e19fcf55cc0b` |
| Date (UTC) | 2026-10-14T17:36:08Z |
| Device | mps |
| Libraries | tokenizers 0.22.2, transformers 4.57.6, torch 2.14.0, python 3.11.16 |
| Tracks | R = raw HF pipeline (simple), M = model-only product path |
| Data version | benchmark `b272b758eb6e4e5e` |

## A6 gates (shadow_dev, track R)

`benchmark` is the same metric on that set, track R: a reference while the shadow numbers are pending, never a gate.

| Gate | Measured | benchmark | Sprint 1 target | S1 | Sprint 2 target | S2 | Note |
|---|---|---|---|---|---|---|---|
| micro_f1 | n/a | 93.5 | >= 76.0 | – | >= 82.0 | – | shadow_dev not scored: shadow pending |
| weakest_label_f1 | n/a | 72.9 | >= 50.0 | – | >= 65.0 | – | shadow_dev not scored: shadow pending |
| ACCESS_TOKEN_f1 | n/a | 99.7 | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| IPV6_ADDRESS_f1 | n/a | 94.5 | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| AZ_DRIVER_LICENSE_NUMBER_f1 | n/a | 96.2 | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| hard_negative_trigger_rate | n/a | 3.7 | < 12.0 | – | < 8.0 | – | shadow_dev not scored: shadow pending |
| pii_free_fp_rate | n/a | 23.9 | < 30.0 | – | < 15.0 | – | shadow_dev not scored: shadow pending |
| recall_guard | n/a | n/a | no label -1 pt | – | no label -1 pt | – | no --baseline given |
| en_tr_ru_regression | n/a | n/a | <= 1 pt drop | – | <= 1 pt drop | – | no --baseline given |
| appendix_known_errors_fixed | n/a | n/a | reported by class | – | reported by class | – | appendix not scored |
| sealed_set | untouched | n/a | untouched | PASS | run once | – |  |

## Sets

Percentages. Exact = label+start+end. Trigger = decoy hit with the label it resembles (any label in brackets).

| Set | Track | Docs | Exact P / R / F1 | Macro F1 | Overlap F1 | Char leak | Narrower | Split | Trigger | Control FP | PII-free FP | Perfect |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| benchmark | R | 5000 | 90.4 / 96.8 / 93.5 | 93.5 | 94.9 | 1.5 | 98.9 | 119 | 3.7 (8.4) | – | 23.9 | 79.1 |
| benchmark | M | 5000 | 91.5 / 97.1 / 94.2 | 94.2 | 94.9 | 1.5 | 96.8 | 59 | 3.7 (8.3) | – | 23.7 | 79.8 |

### Slices: benchmark (exact recall / overlap recall / split spans)

| Slice | Value | Gold | R | M |
|---|---|---|---|---|
| doc:_adversarials | 0 | 2908 | 98.2 / 98.9 / 18 | 98.3 / 98.7 / 11 |
| doc:_adversarials | 1 | 2511 | 97.4 / 98.2 / 20 | 97.6 / 98.0 / 10 |
| doc:_adversarials | 2 | 2611 | 95.3 / 96.7 / 39 | 95.5 / 96.3 / 20 |
| doc:_adversarials | 3 | 1332 | 96.2 / 97.7 / 20 | 96.9 / 97.5 / 8 |
| doc:_adversarials | 4 | 1116 | 95.8 / 97.8 / 22 | 96.5 / 97.5 / 10 |
| doc:_adversarials | 5 | 40 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_benchmark_category | anchor_variant_hard_negative | 793 | 97.4 / 98.1 / 6 | 97.5 / 98.0 / 4 |
| doc:_benchmark_category | anchor_variant_positive | 1084 | 98.4 / 99.0 / 6 | 98.5 / 98.7 / 2 |
| doc:_benchmark_category | corrected_hard_negative | 151 | 96.7 / 96.7 / 0 | 96.7 / 96.7 / 0 |
| doc:_benchmark_category | hard_negative | 1300 | 95.2 / 97.2 / 24 | 96.2 / 97.0 / 10 |
| doc:_benchmark_category | mixed | 2187 | 96.8 / 98.1 / 28 | 97.2 / 97.9 / 14 |
| doc:_benchmark_category | natural_variant_hard_negative | 1047 | 97.2 / 98.2 / 10 | 97.5 / 98.0 / 5 |
| doc:_benchmark_category | natural_variant_positive | 1552 | 98.1 / 98.8 / 11 | 98.1 / 98.7 / 8 |
| doc:_benchmark_category | positive_control | 871 | 98.0 / 98.6 / 5 | 98.2 / 98.4 / 2 |
| doc:_benchmark_category | structured_csv | 300 | 87.0 / 89.3 / 7 | 87.3 / 89.3 / 6 |
| doc:_benchmark_category | structured_dialogue | 309 | 93.2 / 95.5 / 7 | 93.5 / 95.1 / 5 |
| doc:_benchmark_category | structured_json_config | 309 | 98.1 / 99.4 / 4 | 98.4 / 98.4 / 0 |
| doc:_benchmark_category | structured_pipe_table | 336 | 95.5 / 97.3 / 6 | 95.8 / 96.4 / 2 |
| doc:_benchmark_category | structured_technical_log | 279 | 96.8 / 98.6 / 5 | 97.1 / 97.5 / 1 |
| doc:_bucket | long | 5640 | 96.6 / 97.9 / 71 | 97.0 / 97.7 / 34 |
| doc:_bucket | medium | 3342 | 98.2 / 98.8 / 19 | 98.4 / 98.7 / 11 |
| doc:_bucket | short | 3 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_bucket | structured | 1533 | 94.1 / 96.0 / 29 | 94.5 / 95.4 / 14 |
| doc:_doc_type | bank_message | 665 | 97.4 / 98.3 / 6 | 97.6 / 98.3 / 5 |
| doc:_doc_type | crm | 704 | 96.6 / 97.7 / 8 | 96.7 / 97.3 / 4 |
| doc:_doc_type | csv | 300 | 87.0 / 89.3 / 7 | 87.3 / 89.3 / 6 |
| doc:_doc_type | dialogue | 309 | 93.2 / 95.5 / 7 | 93.5 / 95.1 / 5 |
| doc:_doc_type | email | 684 | 95.8 / 97.4 / 10 | 96.3 / 97.1 / 4 |
| doc:_doc_type | first_person_chat | 838 | 98.6 / 99.0 / 4 | 98.7 / 98.9 / 2 |
| doc:_doc_type | first_person_email | 912 | 98.2 / 98.8 / 5 | 98.7 / 98.7 / 0 |
| doc:_doc_type | first_person_form | 924 | 98.6 / 99.1 / 4 | 98.6 / 99.0 / 2 |
| doc:_doc_type | form | 744 | 97.3 / 98.8 / 11 | 97.7 / 98.4 / 5 |
| doc:_doc_type | insurance | 628 | 96.5 / 97.6 / 7 | 96.7 / 97.3 / 4 |
| doc:_doc_type | json_config | 309 | 98.1 / 99.4 / 4 | 98.4 / 98.4 / 0 |
| doc:_doc_type | legal | 699 | 96.7 / 97.9 / 8 | 97.0 / 97.9 / 6 |
| doc:_doc_type | pipe_table | 336 | 95.5 / 97.3 / 6 | 95.8 / 96.4 / 2 |
| doc:_doc_type | report | 709 | 97.2 / 98.2 / 7 | 98.0 / 98.0 / 0 |
| doc:_doc_type | support_ticket | 745 | 96.2 / 97.9 / 12 | 96.5 / 97.6 / 8 |
| doc:_doc_type | technical_log | 279 | 96.8 / 98.6 / 5 | 97.1 / 97.5 / 1 |
| doc:_doc_type | technical_note | 733 | 96.5 / 97.5 / 8 | 96.7 / 97.4 / 5 |
| doc:_hard_negatives | 0 | 2960 | 98.2 / 98.9 / 18 | 98.3 / 98.7 / 11 |
| doc:_hard_negatives | 1 | 2503 | 97.4 / 98.2 / 20 | 97.6 / 98.0 / 10 |
| doc:_hard_negatives | 2 | 2603 | 95.3 / 96.8 / 39 | 95.5 / 96.4 / 20 |
| doc:_hard_negatives | 3 | 1359 | 96.2 / 97.7 / 20 | 97.0 / 97.6 / 8 |
| doc:_hard_negatives | 4 | 1066 | 95.6 / 97.7 / 22 | 96.3 / 97.4 / 10 |
| doc:_hard_negatives | 5 | 27 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_register | bureaucratic | 1816 | 97.8 / 99.0 / 21 | 98.1 / 98.7 / 11 |
| doc:_register | casual | 1771 | 97.0 / 98.0 / 19 | 97.5 / 97.8 / 6 |
| doc:_register | formal | 1817 | 96.7 / 97.9 / 19 | 97.0 / 97.7 / 10 |
| doc:_register | neutral | 1686 | 97.5 / 98.5 / 16 | 97.6 / 98.2 / 9 |
| doc:_register | technical | 3428 | 95.8 / 97.1 / 44 | 96.1 / 96.7 / 23 |
| doc:_source | benchmark_structured_v3 | 1533 | 94.1 / 96.0 / 29 | 94.5 / 95.4 / 14 |
| doc:_source | benchmark_synthetic_diverse | 8985 | 97.2 / 98.2 / 90 | 97.5 / 98.1 / 45 |
| doc:lang | az | 10518 | 96.8 / 97.9 / 119 | 97.1 / 97.7 / 59 |
| doc:density | 0 | 0 | – / – / 0 | – / – / 0 |
| doc:density | 1 | 978 | 94.9 / 96.5 / 15 | 95.6 / 96.4 / 7 |
| doc:density | 2-3 | 6966 | 96.8 / 97.9 / 76 | 97.0 / 97.6 / 38 |
| doc:density | 4-6 | 2574 | 97.5 / 98.6 / 28 | 97.7 / 98.3 / 14 |

Calibration (score bins vs precision) is in the JSON. It is reported only and is never used to set a threshold (A2.2).
