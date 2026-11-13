# Scoreboard: new_benchmark

| | |
|---|---|
| Model | `your-hf-org/masking-az-runb-v4-seed42` |
| Revision SHA | `e4ca17842f005e5b103f1d32d21859360c92b258` |
| Requested revision | `e4ca17842f005e5b103f1d32d21859360c92b258` |
| Code git SHA | `18b2a6871020f05e169f7f8e3d4ea3c8b2c678a8` |
| Date (UTC) | 2026-10-16T11:01:56Z |
| Device | mps |
| Libraries | tokenizers 0.22.2, transformers 4.57.6, torch 2.14.0, python 3.11.16 |
| Tracks | R = raw HF pipeline (simple), M = model-only product path |
| Data version | benchmark `b272b758eb6e4e5e` |

## A6 gates (shadow_dev, track R)

`benchmark` is the same metric on that set, track R: a reference while the shadow numbers are pending, never a gate.

| Gate | Measured | benchmark | Sprint 1 target | S1 | Sprint 2 target | S2 | Note |
|---|---|---|---|---|---|---|---|
| micro_f1 | n/a | 95.1 | >= 76.0 | – | >= 82.0 | – | shadow_dev not scored: shadow pending |
| weakest_label_f1 | n/a | 76.5 | >= 50.0 | – | >= 65.0 | – | shadow_dev not scored: shadow pending |
| ACCESS_TOKEN_f1 | n/a | 99.1 | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| IPV6_ADDRESS_f1 | n/a | 76.5 | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| AZ_DRIVER_LICENSE_NUMBER_f1 | n/a | 99.1 | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| hard_negative_trigger_rate | n/a | 1.9 | < 12.0 | – | < 8.0 | – | shadow_dev not scored: shadow pending |
| pii_free_fp_rate | n/a | 11.9 | < 30.0 | – | < 15.0 | – | shadow_dev not scored: shadow pending |
| recall_guard | n/a | n/a | no label -1 pt | – | no label -1 pt | – | no --baseline given |
| en_tr_ru_regression | n/a | n/a | <= 1 pt drop | – | <= 1 pt drop | – | no --baseline given |
| appendix_known_errors_fixed | n/a | n/a | reported by class | – | reported by class | – | appendix not scored |
| sealed_set | untouched | n/a | untouched | PASS | run once | – |  |

## Sets

Percentages. Exact = label+start+end. Trigger = decoy hit with the label it resembles (any label in brackets).

| Set | Track | Docs | Exact P / R / F1 | Macro F1 | Overlap F1 | Char leak | Narrower | Split | Trigger | Control FP | PII-free FP | Perfect |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| benchmark | R | 5000 | 93.5 / 96.7 / 95.1 | 95.2 | 96.8 | 1.5 | 98.6 | 143 | 1.9 (4.8) | – | 11.9 | 85.1 |
| benchmark excl. policy | R | 5000 | 95.5 / 96.7 / 96.1 | 96.2 | 97.8 | 1.5 | 98.6 | 143 | 1.1 (2.5) | – | 5.2 | 89.0 |
| benchmark | M | 5000 | 94.5 / 97.0 / 95.7 | 95.8 | 96.8 | 1.5 | 97.7 | 98 | 1.7 (4.6) | – | 11.4 | 86.0 |
| benchmark excl. policy | M | 5000 | 96.5 / 97.0 / 96.7 | 96.8 | 97.8 | 1.5 | 97.7 | 98 | 0.9 (2.3) | – | 4.9 | 89.9 |

### Slices: benchmark (exact recall / overlap recall / split spans)

| Slice | Value | Gold | R | M |
|---|---|---|---|---|
| doc:_adversarials | 0 | 2908 | 97.6 / 98.3 / 20 | 97.7 / 98.2 / 15 |
| doc:_adversarials | 1 | 2511 | 97.0 / 98.0 / 26 | 97.1 / 97.7 / 14 |
| doc:_adversarials | 2 | 2611 | 95.9 / 98.5 / 66 | 96.5 / 98.3 / 46 |
| doc:_adversarials | 3 | 1332 | 96.2 / 97.1 / 12 | 96.4 / 97.1 / 9 |
| doc:_adversarials | 4 | 1116 | 96.1 / 97.8 / 19 | 96.4 / 97.7 / 14 |
| doc:_adversarials | 5 | 40 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_benchmark_category | anchor_variant_hard_negative | 793 | 96.8 / 98.0 / 9 | 96.8 / 97.6 / 6 |
| doc:_benchmark_category | anchor_variant_positive | 1084 | 97.5 / 98.2 / 8 | 97.6 / 98.1 / 5 |
| doc:_benchmark_category | corrected_hard_negative | 151 | 96.0 / 98.7 / 3 | 96.7 / 98.0 / 1 |
| doc:_benchmark_category | hard_negative | 1300 | 95.8 / 96.9 / 14 | 96.0 / 96.7 / 9 |
| doc:_benchmark_category | mixed | 2187 | 96.2 / 97.9 / 36 | 96.6 / 97.7 / 23 |
| doc:_benchmark_category | natural_variant_hard_negative | 1047 | 96.7 / 98.0 / 14 | 96.9 / 97.6 / 7 |
| doc:_benchmark_category | natural_variant_positive | 1552 | 97.5 / 98.3 / 12 | 97.6 / 98.3 / 10 |
| doc:_benchmark_category | positive_control | 871 | 97.9 / 98.3 / 3 | 97.9 / 98.2 / 2 |
| doc:_benchmark_category | structured_csv | 300 | 91.3 / 95.7 / 13 | 92.3 / 95.3 / 9 |
| doc:_benchmark_category | structured_dialogue | 309 | 98.1 / 100.0 / 6 | 98.7 / 100.0 / 4 |
| doc:_benchmark_category | structured_json_config | 309 | 98.1 / 100.0 / 6 | 98.4 / 100.0 / 5 |
| doc:_benchmark_category | structured_pipe_table | 336 | 95.5 / 100.0 / 15 | 96.1 / 100.0 / 13 |
| doc:_benchmark_category | structured_technical_log | 279 | 98.6 / 100.0 / 4 | 98.6 / 100.0 / 4 |
| doc:_bucket | long | 5640 | 96.9 / 98.0 / 61 | 97.1 / 97.8 / 37 |
| doc:_bucket | medium | 3342 | 96.6 / 97.8 / 38 | 96.8 / 97.6 / 26 |
| doc:_bucket | short | 3 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_bucket | structured | 1533 | 96.3 / 99.2 / 44 | 96.8 / 99.1 / 35 |
| doc:_doc_type | bank_message | 665 | 96.2 / 97.7 / 10 | 96.5 / 97.4 / 6 |
| doc:_doc_type | crm | 704 | 95.9 / 97.3 / 10 | 96.3 / 97.2 / 6 |
| doc:_doc_type | csv | 300 | 91.3 / 95.7 / 13 | 92.3 / 95.3 / 9 |
| doc:_doc_type | dialogue | 309 | 98.1 / 100.0 / 6 | 98.7 / 100.0 / 4 |
| doc:_doc_type | email | 684 | 94.6 / 96.2 / 10 | 95.0 / 96.1 / 6 |
| doc:_doc_type | first_person_chat | 838 | 99.5 / 99.9 / 3 | 99.5 / 99.9 / 3 |
| doc:_doc_type | first_person_email | 912 | 99.1 / 99.8 / 6 | 99.3 / 99.6 / 2 |
| doc:_doc_type | first_person_form | 924 | 99.1 / 99.8 / 5 | 99.2 / 99.7 / 3 |
| doc:_doc_type | form | 744 | 95.7 / 96.8 / 8 | 96.0 / 96.6 / 5 |
| doc:_doc_type | insurance | 628 | 96.7 / 97.3 / 4 | 96.8 / 97.3 / 3 |
| doc:_doc_type | json_config | 309 | 98.1 / 100.0 / 6 | 98.4 / 100.0 / 5 |
| doc:_doc_type | legal | 699 | 95.9 / 97.1 / 9 | 96.0 / 96.9 / 6 |
| doc:_doc_type | pipe_table | 336 | 95.5 / 100.0 / 15 | 96.1 / 100.0 / 13 |
| doc:_doc_type | report | 709 | 95.8 / 97.3 / 11 | 95.9 / 97.0 / 8 |
| doc:_doc_type | support_ticket | 745 | 96.4 / 98.3 / 13 | 96.5 / 97.9 / 9 |
| doc:_doc_type | technical_log | 279 | 98.6 / 100.0 / 4 | 98.6 / 100.0 / 4 |
| doc:_doc_type | technical_note | 733 | 94.8 / 96.2 / 10 | 95.0 / 95.8 / 6 |
| doc:_hard_negatives | 0 | 2960 | 97.6 / 98.3 / 20 | 97.7 / 98.2 / 15 |
| doc:_hard_negatives | 1 | 2503 | 96.9 / 98.0 / 27 | 97.1 / 97.7 / 14 |
| doc:_hard_negatives | 2 | 2603 | 96.0 / 98.5 / 65 | 96.5 / 98.3 / 46 |
| doc:_hard_negatives | 3 | 1359 | 96.3 / 97.2 / 12 | 96.5 / 97.1 / 9 |
| doc:_hard_negatives | 4 | 1066 | 96.0 / 97.7 / 19 | 96.2 / 97.6 / 14 |
| doc:_hard_negatives | 5 | 27 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_register | bureaucratic | 1816 | 97.2 / 98.4 / 22 | 97.3 / 98.2 / 16 |
| doc:_register | casual | 1771 | 96.4 / 97.5 / 20 | 96.7 / 97.3 / 12 |
| doc:_register | formal | 1817 | 97.0 / 98.0 / 18 | 97.2 / 97.8 / 9 |
| doc:_register | neutral | 1686 | 97.4 / 98.2 / 12 | 97.4 / 98.1 / 10 |
| doc:_register | technical | 3428 | 96.2 / 98.3 / 71 | 96.6 / 98.1 / 51 |
| doc:_source | benchmark_structured_v3 | 1533 | 96.3 / 99.2 / 44 | 96.8 / 99.1 / 35 |
| doc:_source | benchmark_synthetic_diverse | 8985 | 96.8 / 97.9 / 99 | 97.0 / 97.7 / 63 |
| doc:lang | az | 10518 | 96.7 / 98.1 / 143 | 97.0 / 97.9 / 98 |
| doc:density | 0 | 0 | – / – / 0 | – / – / 0 |
| doc:density | 1 | 978 | 95.7 / 97.2 / 15 | 96.1 / 96.8 / 7 |
| doc:density | 2-3 | 6966 | 96.5 / 98.0 / 103 | 96.8 / 97.9 / 75 |
| doc:density | 4-6 | 2574 | 97.6 / 98.6 / 25 | 97.7 / 98.4 / 16 |

Calibration (score bins vs precision) is in the JSON. It is reported only and is never used to set a threshold (A2.2).
