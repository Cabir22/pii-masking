# Scoreboard: new_benchmark

| | |
|---|---|
| Model | `your-hf-org/masking-az-runb-v4.1-seed42` |
| Revision SHA | `502598c1d5850958e98b1922ce65d504f700b528` |
| Requested revision | `502598c1d5850958e98b1922ce65d504f700b528` |
| Code git SHA | `c5c1614b85b8e2f8922673509b1c87b505e98f8c` |
| Date (UTC) | 2026-10-19T11:29:15Z |
| Device | cuda |
| Libraries | tokenizers 0.22.2, transformers 4.57.6, torch 2.8.0.dev20250319+cu128, python 3.11.11 |
| Tracks | R = raw HF pipeline (simple), M = model-only product path |
| Data version | benchmark `b272b758eb6e4e5e` |

## A6 gates (shadow_dev, track R)

`benchmark` is the same metric on that set, track R: a reference while the shadow numbers are pending, never a gate.

| Gate | Measured | benchmark | Sprint 1 target | S1 | Sprint 2 target | S2 | Note |
|---|---|---|---|---|---|---|---|
| micro_f1 | n/a | 96.0 | >= 76.0 | – | >= 82.0 | – | shadow_dev not scored: shadow pending |
| weakest_label_f1 | n/a | 84.8 | >= 50.0 | – | >= 65.0 | – | shadow_dev not scored: shadow pending |
| ACCESS_TOKEN_f1 | n/a | 99.7 | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| IPV6_ADDRESS_f1 | n/a | 97.8 | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| AZ_DRIVER_LICENSE_NUMBER_f1 | n/a | 99.9 | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| hard_negative_trigger_rate | n/a | 2.3 | < 12.0 | – | < 8.0 | – | shadow_dev not scored: shadow pending |
| pii_free_fp_rate | n/a | 14.5 | < 30.0 | – | < 15.0 | – | shadow_dev not scored: shadow pending |
| recall_guard | n/a | n/a | no label -1 pt | – | no label -1 pt | – | no --baseline given |
| en_tr_ru_regression | n/a | n/a | <= 1 pt drop | – | <= 1 pt drop | – | no --baseline given |
| appendix_known_errors_fixed | n/a | n/a | reported by class | – | reported by class | – | appendix not scored |
| sealed_set | untouched | n/a | untouched | PASS | run once | – |  |

## Sets

Percentages. Exact = label+start+end. Trigger = decoy hit with the label it resembles (any label in brackets).

| Set | Track | Docs | Exact P / R / F1 | Macro F1 | Overlap F1 | Char leak | Narrower | Split | Trigger | Control FP | PII-free FP | Perfect |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| benchmark | R | 5000 | 93.6 / 98.5 / 96.0 | 96.2 | 97.0 | 0.5 | 98.5 | 76 | 2.3 (5.6) | – | 14.5 | 87.2 |
| benchmark excl. policy | R | 5000 | 95.6 / 98.5 / 97.0 | 97.1 | 98.1 | 0.5 | 98.5 | 76 | 1.4 (3.3) | – | 8.5 | 91.3 |
| benchmark | M | 5000 | 94.0 / 98.6 / 96.3 | 96.4 | 97.1 | 0.5 | 97.3 | 57 | 2.2 (5.5) | – | 13.7 | 87.6 |
| benchmark excl. policy | M | 5000 | 96.0 / 98.6 / 97.3 | 97.4 | 98.1 | 0.5 | 97.3 | 57 | 1.4 (3.2) | – | 7.8 | 91.7 |

### Slices: benchmark (exact recall / overlap recall / split spans)

| Slice | Value | Gold | R | M |
|---|---|---|---|---|
| doc:_adversarials | 0 | 2908 | 98.9 / 99.4 / 13 | 99.0 / 99.3 / 8 |
| doc:_adversarials | 1 | 2511 | 98.6 / 99.2 / 17 | 98.7 / 99.2 / 13 |
| doc:_adversarials | 2 | 2611 | 98.0 / 99.4 / 35 | 98.1 / 99.3 / 30 |
| doc:_adversarials | 3 | 1332 | 98.8 / 99.2 / 6 | 98.9 / 99.1 / 3 |
| doc:_adversarials | 4 | 1116 | 98.4 / 98.8 / 5 | 98.4 / 98.7 / 3 |
| doc:_adversarials | 5 | 40 | 97.5 / 97.5 / 0 | 97.5 / 97.5 / 0 |
| doc:_benchmark_category | anchor_variant_hard_negative | 793 | 98.7 / 99.2 / 4 | 98.7 / 99.2 / 4 |
| doc:_benchmark_category | anchor_variant_positive | 1084 | 98.8 / 99.4 / 6 | 99.0 / 99.2 / 2 |
| doc:_benchmark_category | corrected_hard_negative | 151 | 98.0 / 98.7 / 1 | 98.0 / 98.0 / 0 |
| doc:_benchmark_category | hard_negative | 1300 | 98.5 / 99.0 / 6 | 98.6 / 98.8 / 3 |
| doc:_benchmark_category | mixed | 2187 | 98.8 / 99.2 / 8 | 98.8 / 99.0 / 4 |
| doc:_benchmark_category | natural_variant_hard_negative | 1047 | 98.5 / 99.3 / 9 | 98.7 / 99.3 / 7 |
| doc:_benchmark_category | natural_variant_positive | 1552 | 99.0 / 99.5 / 6 | 99.1 / 99.5 / 5 |
| doc:_benchmark_category | positive_control | 871 | 98.9 / 99.3 / 4 | 99.0 / 99.3 / 3 |
| doc:_benchmark_category | structured_csv | 300 | 89.3 / 97.3 / 24 | 89.0 / 97.0 / 23 |
| doc:_benchmark_category | structured_dialogue | 309 | 98.7 / 100.0 / 4 | 99.4 / 100.0 / 2 |
| doc:_benchmark_category | structured_json_config | 309 | 99.4 / 100.0 / 2 | 99.4 / 100.0 / 2 |
| doc:_benchmark_category | structured_pipe_table | 336 | 99.4 / 100.0 / 2 | 99.4 / 100.0 / 2 |
| doc:_benchmark_category | structured_technical_log | 279 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_bucket | long | 5640 | 98.6 / 99.1 / 30 | 98.7 / 99.0 / 18 |
| doc:_bucket | medium | 3342 | 99.0 / 99.4 / 14 | 99.0 / 99.4 / 10 |
| doc:_bucket | short | 3 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_bucket | structured | 1533 | 97.4 / 99.5 / 32 | 97.5 / 99.4 / 29 |
| doc:_doc_type | bank_message | 665 | 98.6 / 99.2 / 4 | 99.1 / 99.2 / 1 |
| doc:_doc_type | crm | 704 | 97.6 / 98.9 / 9 | 97.7 / 98.7 / 7 |
| doc:_doc_type | csv | 300 | 89.3 / 97.3 / 24 | 89.0 / 97.0 / 23 |
| doc:_doc_type | dialogue | 309 | 98.7 / 100.0 / 4 | 99.4 / 100.0 / 2 |
| doc:_doc_type | email | 684 | 98.1 / 98.5 / 2 | 98.2 / 98.5 / 1 |
| doc:_doc_type | first_person_chat | 838 | 99.5 / 99.8 / 2 | 99.6 / 99.8 / 1 |
| doc:_doc_type | first_person_email | 912 | 99.6 / 99.8 / 2 | 99.6 / 99.7 / 1 |
| doc:_doc_type | first_person_form | 924 | 99.0 / 99.6 / 4 | 99.0 / 99.5 / 3 |
| doc:_doc_type | form | 744 | 98.4 / 99.1 / 5 | 98.4 / 98.9 / 4 |
| doc:_doc_type | insurance | 628 | 99.2 / 99.5 / 2 | 99.4 / 99.5 / 1 |
| doc:_doc_type | json_config | 309 | 99.4 / 100.0 / 2 | 99.4 / 100.0 / 2 |
| doc:_doc_type | legal | 699 | 98.4 / 99.1 / 5 | 98.4 / 99.0 / 4 |
| doc:_doc_type | pipe_table | 336 | 99.4 / 100.0 / 2 | 99.4 / 100.0 / 2 |
| doc:_doc_type | report | 709 | 98.2 / 99.0 / 6 | 98.3 / 98.7 / 3 |
| doc:_doc_type | support_ticket | 745 | 98.8 / 98.9 / 1 | 98.8 / 98.9 / 1 |
| doc:_doc_type | technical_log | 279 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_doc_type | technical_note | 733 | 99.0 / 99.3 / 2 | 99.0 / 99.2 / 1 |
| doc:_hard_negatives | 0 | 2960 | 98.9 / 99.4 / 14 | 99.0 / 99.3 / 8 |
| doc:_hard_negatives | 1 | 2503 | 98.6 / 99.2 / 16 | 98.7 / 99.2 / 13 |
| doc:_hard_negatives | 2 | 2603 | 98.0 / 99.4 / 35 | 98.1 / 99.3 / 30 |
| doc:_hard_negatives | 3 | 1359 | 98.8 / 99.3 / 6 | 98.9 / 99.1 / 3 |
| doc:_hard_negatives | 4 | 1066 | 98.3 / 98.8 / 5 | 98.3 / 98.6 / 3 |
| doc:_hard_negatives | 5 | 27 | 96.3 / 96.3 / 0 | 96.3 / 96.3 / 0 |
| doc:_register | bureaucratic | 1816 | 99.2 / 99.7 / 8 | 99.2 / 99.6 / 7 |
| doc:_register | casual | 1771 | 98.9 / 99.2 / 6 | 98.9 / 99.2 / 5 |
| doc:_register | formal | 1817 | 98.5 / 99.1 / 9 | 98.7 / 99.0 / 5 |
| doc:_register | neutral | 1686 | 98.6 / 99.3 / 12 | 98.7 / 99.2 / 7 |
| doc:_register | technical | 3428 | 98.0 / 99.2 / 41 | 98.1 / 99.1 / 33 |
| doc:_source | benchmark_structured_v3 | 1533 | 97.4 / 99.5 / 32 | 97.5 / 99.4 / 29 |
| doc:_source | benchmark_synthetic_diverse | 8985 | 98.7 / 99.3 / 44 | 98.8 / 99.2 / 28 |
| doc:lang | az | 10518 | 98.5 / 99.3 / 76 | 98.6 / 99.2 / 57 |
| doc:density | 0 | 0 | – / – / 0 | – / – / 0 |
| doc:density | 1 | 978 | 97.4 / 98.4 / 9 | 97.4 / 98.2 / 7 |
| doc:density | 2-3 | 6966 | 98.7 / 99.5 / 54 | 98.8 / 99.4 / 42 |
| doc:density | 4-6 | 2574 | 98.6 / 99.2 / 13 | 98.8 / 99.1 / 8 |

Calibration (score bins vs precision) is in the JSON. It is reported only and is never used to set a threshold (A2.2).
