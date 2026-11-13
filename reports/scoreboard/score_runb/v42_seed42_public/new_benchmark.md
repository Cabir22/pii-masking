# Scoreboard: new_benchmark

| | |
|---|---|
| Model | `your-hf-org/masking-az-runb-v4.2-seed42` |
| Revision SHA | `223e54e8799dc60f6f6b19362191cf7c10c774c7` |
| Requested revision | `223e54e8799dc60f6f6b19362191cf7c10c774c7` |
| Code git SHA | `` |
| Date (UTC) | 2026-10-21T10:50:53Z |
| Device | cuda |
| Libraries | tokenizers 0.22.2, transformers 4.57.6, torch 2.8.0.dev20250319+cu128, python 3.11.11 |
| Tracks | R = raw HF pipeline (simple), M = model-only product path |
| Data version | benchmark `b272b758eb6e4e5e` |

## A6 gates (shadow_dev, track R)

`benchmark` is the same metric on that set, track R: a reference while the shadow numbers are pending, never a gate.

| Gate | Measured | benchmark | Sprint 1 target | S1 | Sprint 2 target | S2 | Note |
|---|---|---|---|---|---|---|---|
| micro_f1 | n/a | 95.4 | >= 76.0 | – | >= 82.0 | – | shadow_dev not scored: shadow pending |
| weakest_label_f1 | n/a | 72.2 | >= 50.0 | – | >= 65.0 | – | shadow_dev not scored: shadow pending |
| ACCESS_TOKEN_f1 | n/a | 99.7 | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| IPV6_ADDRESS_f1 | n/a | 72.2 | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| AZ_DRIVER_LICENSE_NUMBER_f1 | n/a | 100.0 | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| hard_negative_trigger_rate | n/a | 2.4 | < 12.0 | – | < 8.0 | – | shadow_dev not scored: shadow pending |
| pii_free_fp_rate | n/a | 12.6 | < 30.0 | – | < 15.0 | – | shadow_dev not scored: shadow pending |
| recall_guard | n/a | n/a | no label -1 pt | – | no label -1 pt | – | no --baseline given |
| en_tr_ru_regression | n/a | n/a | <= 1 pt drop | – | <= 1 pt drop | – | no --baseline given |
| appendix_known_errors_fixed | n/a | n/a | reported by class | – | reported by class | – | appendix not scored |
| sealed_set | untouched | n/a | untouched | PASS | run once | – |  |

## Sets

Percentages. Exact = label+start+end. Trigger = decoy hit with the label it resembles (any label in brackets).

| Set | Track | Docs | Exact P / R / F1 | Macro F1 | Overlap F1 | Char leak | Narrower | Split | Trigger | Control FP | PII-free FP | Perfect |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| benchmark | R | 5000 | 93.6 / 97.3 / 95.4 | 95.5 | 96.4 | 1.4 | 98.5 | 84 | 2.4 (5.9) | – | 12.6 | 84.9 |
| benchmark excl. policy | R | 5000 | 95.5 / 97.3 / 96.4 | 96.5 | 97.4 | 1.4 | 98.5 | 84 | 1.6 (3.6) | – | 6.5 | 88.8 |
| benchmark | M | 5000 | 94.1 / 97.5 / 95.8 | 95.9 | 96.4 | 1.4 | 97.6 | 54 | 2.2 (5.7) | – | 11.8 | 85.4 |
| benchmark excl. policy | M | 5000 | 96.1 / 97.5 / 96.8 | 96.8 | 97.4 | 1.4 | 97.6 | 54 | 1.4 (3.4) | – | 5.7 | 89.4 |

### Slices: benchmark (exact recall / overlap recall / split spans)

| Slice | Value | Gold | R | M |
|---|---|---|---|---|
| doc:_adversarials | 0 | 2908 | 97.7 / 98.4 / 19 | 97.8 / 98.3 / 13 |
| doc:_adversarials | 1 | 2511 | 97.4 / 98.0 / 16 | 97.5 / 97.8 / 9 |
| doc:_adversarials | 2 | 2611 | 97.4 / 98.5 / 30 | 97.5 / 98.5 / 23 |
| doc:_adversarials | 3 | 1332 | 96.5 / 97.4 / 12 | 96.8 / 97.3 / 6 |
| doc:_adversarials | 4 | 1116 | 96.7 / 97.3 / 7 | 97.0 / 97.2 / 3 |
| doc:_adversarials | 5 | 40 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_benchmark_category | anchor_variant_hard_negative | 793 | 97.9 / 98.9 / 8 | 98.0 / 98.6 / 5 |
| doc:_benchmark_category | anchor_variant_positive | 1084 | 97.8 / 98.3 / 6 | 97.9 / 98.2 / 3 |
| doc:_benchmark_category | corrected_hard_negative | 151 | 96.0 / 96.7 / 1 | 96.0 / 96.7 / 1 |
| doc:_benchmark_category | hard_negative | 1300 | 96.5 / 97.1 / 7 | 96.8 / 97.1 / 4 |
| doc:_benchmark_category | mixed | 2187 | 96.9 / 97.9 / 20 | 97.2 / 97.7 / 9 |
| doc:_benchmark_category | natural_variant_hard_negative | 1047 | 97.1 / 97.7 / 6 | 97.2 / 97.5 / 3 |
| doc:_benchmark_category | natural_variant_positive | 1552 | 97.4 / 98.3 / 12 | 97.6 / 98.3 / 10 |
| doc:_benchmark_category | positive_control | 871 | 98.0 / 98.4 / 3 | 98.0 / 98.2 / 1 |
| doc:_benchmark_category | structured_csv | 300 | 92.7 / 95.0 / 7 | 93.3 / 95.0 / 5 |
| doc:_benchmark_category | structured_dialogue | 309 | 97.4 / 99.7 / 7 | 97.7 / 99.7 / 6 |
| doc:_benchmark_category | structured_json_config | 309 | 99.4 / 99.7 / 1 | 99.4 / 99.7 / 1 |
| doc:_benchmark_category | structured_pipe_table | 336 | 98.2 / 100.0 / 6 | 98.2 / 100.0 / 6 |
| doc:_benchmark_category | structured_technical_log | 279 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_bucket | long | 5640 | 97.2 / 98.0 / 42 | 97.4 / 97.8 / 23 |
| doc:_bucket | medium | 3342 | 97.3 / 98.0 / 21 | 97.5 / 97.9 / 13 |
| doc:_bucket | short | 3 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_bucket | structured | 1533 | 97.5 / 98.9 / 21 | 97.7 / 98.9 / 18 |
| doc:_doc_type | bank_message | 665 | 97.0 / 97.6 / 4 | 97.0 / 97.4 / 3 |
| doc:_doc_type | crm | 704 | 96.4 / 97.3 / 6 | 96.6 / 97.0 / 3 |
| doc:_doc_type | csv | 300 | 92.7 / 95.0 / 7 | 93.3 / 95.0 / 5 |
| doc:_doc_type | dialogue | 309 | 97.4 / 99.7 / 7 | 97.7 / 99.7 / 6 |
| doc:_doc_type | email | 684 | 97.1 / 97.8 / 4 | 97.2 / 97.7 / 2 |
| doc:_doc_type | first_person_chat | 838 | 99.8 / 99.8 / 0 | 99.8 / 99.8 / 0 |
| doc:_doc_type | first_person_email | 912 | 99.5 / 99.8 / 3 | 99.5 / 99.8 / 3 |
| doc:_doc_type | first_person_form | 924 | 99.2 / 99.7 / 3 | 99.2 / 99.6 / 2 |
| doc:_doc_type | form | 744 | 95.0 / 96.2 / 9 | 95.4 / 96.0 / 4 |
| doc:_doc_type | insurance | 628 | 97.3 / 97.8 / 3 | 97.3 / 97.8 / 3 |
| doc:_doc_type | json_config | 309 | 99.4 / 99.7 / 1 | 99.4 / 99.7 / 1 |
| doc:_doc_type | legal | 699 | 95.3 / 96.9 / 11 | 96.0 / 96.7 / 5 |
| doc:_doc_type | pipe_table | 336 | 98.2 / 100.0 / 6 | 98.2 / 100.0 / 6 |
| doc:_doc_type | report | 709 | 96.3 / 97.6 / 9 | 96.5 / 97.3 / 6 |
| doc:_doc_type | support_ticket | 745 | 96.5 / 97.2 / 5 | 96.8 / 97.0 / 2 |
| doc:_doc_type | technical_log | 279 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_doc_type | technical_note | 733 | 96.0 / 96.9 / 6 | 96.3 / 96.7 / 3 |
| doc:_hard_negatives | 0 | 2960 | 97.7 / 98.4 / 19 | 97.8 / 98.3 / 13 |
| doc:_hard_negatives | 1 | 2503 | 97.4 / 98.1 / 16 | 97.5 / 97.9 / 9 |
| doc:_hard_negatives | 2 | 2603 | 97.3 / 98.5 / 30 | 97.5 / 98.5 / 23 |
| doc:_hard_negatives | 3 | 1359 | 96.5 / 97.4 / 12 | 96.9 / 97.4 / 6 |
| doc:_hard_negatives | 4 | 1066 | 96.5 / 97.2 / 7 | 96.8 / 97.1 / 3 |
| doc:_hard_negatives | 5 | 27 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_register | bureaucratic | 1816 | 97.5 / 97.7 / 5 | 97.6 / 97.6 / 1 |
| doc:_register | casual | 1771 | 97.1 / 98.0 / 16 | 97.4 / 98.0 / 10 |
| doc:_register | formal | 1817 | 97.4 / 98.0 / 11 | 97.5 / 97.8 / 5 |
| doc:_register | neutral | 1686 | 97.4 / 98.2 / 13 | 97.5 / 98.2 / 10 |
| doc:_register | technical | 3428 | 97.2 / 98.3 / 39 | 97.4 / 98.2 / 28 |
| doc:_source | benchmark_structured_v3 | 1533 | 97.5 / 98.9 / 21 | 97.7 / 98.9 / 18 |
| doc:_source | benchmark_synthetic_diverse | 8985 | 97.3 / 98.0 / 63 | 97.4 / 97.8 / 36 |
| doc:lang | az | 10518 | 97.3 / 98.1 / 84 | 97.5 / 98.0 / 54 |
| doc:density | 0 | 0 | – / – / 0 | – / – / 0 |
| doc:density | 1 | 978 | 96.7 / 97.5 / 8 | 97.0 / 97.4 / 4 |
| doc:density | 2-3 | 6966 | 97.4 / 98.2 / 59 | 97.6 / 98.1 / 37 |
| doc:density | 4-6 | 2574 | 97.3 / 98.0 / 17 | 97.4 / 97.9 / 13 |

Calibration (score bins vs precision) is in the JSON. It is reported only and is never used to set a threshold (A2.2).
