# Scoreboard: new_benchmark

| | |
|---|---|
| Model | `your-hf-org/masking-az-runb-v3-seed42` |
| Revision SHA | `c9d03581b8a3c8347e6f3ec933a74ff8ac906b98` |
| Requested revision | `c9d03581b8a3c8347e6f3ec933a74ff8ac906b98` |
| Code git SHA | `` |
| Date (UTC) | 2026-10-14T16:52:29Z |
| Device | mps |
| Libraries | tokenizers 0.22.2, transformers 4.57.6, torch 2.14.0, python 3.11.16 |
| Tracks | R = raw HF pipeline (simple), M = model-only product path |
| Data version | benchmark `b272b758eb6e4e5e` |

## A6 gates (shadow_dev, track R)

`benchmark` is the same metric on that set, track R: a reference while the shadow numbers are pending, never a gate.

| Gate | Measured | benchmark | Sprint 1 target | S1 | Sprint 2 target | S2 | Note |
|---|---|---|---|---|---|---|---|
| micro_f1 | n/a | 89.5 | >= 76.0 | – | >= 82.0 | – | shadow_dev not scored: shadow pending |
| weakest_label_f1 | n/a | 52.5 | >= 50.0 | – | >= 65.0 | – | shadow_dev not scored: shadow pending |
| ACCESS_TOKEN_f1 | n/a | 99.7 | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| IPV6_ADDRESS_f1 | n/a | 95.9 | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| AZ_DRIVER_LICENSE_NUMBER_f1 | n/a | 94.1 | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| hard_negative_trigger_rate | n/a | 3.6 | < 12.0 | – | < 8.0 | – | shadow_dev not scored: shadow pending |
| pii_free_fp_rate | n/a | 23.0 | < 30.0 | – | < 15.0 | – | shadow_dev not scored: shadow pending |
| recall_guard | n/a | n/a | no label -1 pt | – | no label -1 pt | – | no --baseline given |
| en_tr_ru_regression | n/a | n/a | <= 1 pt drop | – | <= 1 pt drop | – | no --baseline given |
| appendix_known_errors_fixed | n/a | n/a | reported by class | – | reported by class | – | appendix not scored |
| sealed_set | untouched | n/a | untouched | PASS | run once | – |  |

## Sets

Percentages. Exact = label+start+end. Trigger = decoy hit with the label it resembles (any label in brackets).

| Set | Track | Docs | Exact P / R / F1 | Macro F1 | Overlap F1 | Char leak | Narrower | Split | Trigger | Control FP | PII-free FP | Perfect |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| benchmark | R | 5000 | 86.3 / 92.9 / 89.5 | 89.8 | 94.2 | 2.6 | 86.3 | 309 | 3.6 (8.7) | – | 23.0 | 72.3 |
| benchmark | M | 5000 | 91.5 / 97.1 / 94.2 | 94.2 | 94.9 | 1.5 | 96.8 | 59 | 3.7 (8.3) | – | 23.7 | 79.8 |

### Slices: benchmark (exact recall / overlap recall / split spans)

| Slice | Value | Gold | R | M |
|---|---|---|---|---|
| doc:_adversarials | 0 | 2908 | 94.5 / 98.0 / 72 | 98.3 / 98.7 / 11 |
| doc:_adversarials | 1 | 2511 | 93.3 / 96.7 / 70 | 97.6 / 98.0 / 10 |
| doc:_adversarials | 2 | 2611 | 91.7 / 95.7 / 89 | 95.5 / 96.3 / 20 |
| doc:_adversarials | 3 | 1332 | 92.3 / 96.5 / 45 | 96.9 / 97.5 / 8 |
| doc:_adversarials | 4 | 1116 | 91.5 / 95.5 / 33 | 96.5 / 97.5 / 10 |
| doc:_adversarials | 5 | 40 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_benchmark_category | anchor_variant_hard_negative | 793 | 92.6 / 96.6 / 29 | 97.5 / 98.0 / 4 |
| doc:_benchmark_category | anchor_variant_positive | 1084 | 94.2 / 97.7 / 28 | 98.5 / 98.7 / 2 |
| doc:_benchmark_category | corrected_hard_negative | 151 | 94.7 / 96.7 / 1 | 96.7 / 96.7 / 0 |
| doc:_benchmark_category | hard_negative | 1300 | 91.2 / 95.4 / 40 | 96.2 / 97.0 / 10 |
| doc:_benchmark_category | mixed | 2187 | 93.1 / 96.5 / 58 | 97.2 / 97.9 / 14 |
| doc:_benchmark_category | natural_variant_hard_negative | 1047 | 92.8 / 96.4 / 28 | 97.5 / 98.0 / 5 |
| doc:_benchmark_category | natural_variant_positive | 1552 | 94.7 / 98.4 / 40 | 98.1 / 98.7 / 8 |
| doc:_benchmark_category | positive_control | 871 | 94.9 / 97.5 / 18 | 98.2 / 98.4 / 2 |
| doc:_benchmark_category | structured_csv | 300 | 84.3 / 88.0 / 11 | 87.3 / 89.3 / 6 |
| doc:_benchmark_category | structured_dialogue | 309 | 90.0 / 95.5 / 17 | 93.5 / 95.1 / 5 |
| doc:_benchmark_category | structured_json_config | 309 | 95.8 / 99.0 / 10 | 98.4 / 98.4 / 0 |
| doc:_benchmark_category | structured_pipe_table | 336 | 94.3 / 96.7 / 8 | 95.8 / 96.4 / 2 |
| doc:_benchmark_category | structured_technical_log | 279 | 86.7 / 98.2 / 21 | 97.1 / 97.5 / 1 |
| doc:_bucket | long | 5640 | 92.4 / 96.5 / 183 | 97.0 / 97.7 / 34 |
| doc:_bucket | medium | 3342 | 94.9 / 97.6 / 59 | 98.4 / 98.7 / 11 |
| doc:_bucket | short | 3 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_bucket | structured | 1533 | 90.4 / 95.5 / 67 | 94.5 / 95.4 / 14 |
| doc:_doc_type | bank_message | 665 | 94.0 / 96.8 / 19 | 97.6 / 98.3 / 5 |
| doc:_doc_type | crm | 704 | 92.0 / 96.0 / 28 | 96.7 / 97.3 / 4 |
| doc:_doc_type | csv | 300 | 84.3 / 88.0 / 11 | 87.3 / 89.3 / 6 |
| doc:_doc_type | dialogue | 309 | 90.0 / 95.5 / 17 | 93.5 / 95.1 / 5 |
| doc:_doc_type | email | 684 | 91.8 / 94.6 / 18 | 96.3 / 97.1 / 4 |
| doc:_doc_type | first_person_chat | 838 | 93.4 / 98.4 / 25 | 98.7 / 98.9 / 2 |
| doc:_doc_type | first_person_email | 912 | 92.8 / 98.5 / 25 | 98.7 / 98.7 / 0 |
| doc:_doc_type | first_person_form | 924 | 92.6 / 98.7 / 27 | 98.6 / 99.0 / 2 |
| doc:_doc_type | form | 744 | 95.2 / 97.3 / 16 | 97.7 / 98.4 / 5 |
| doc:_doc_type | insurance | 628 | 93.3 / 96.8 / 22 | 96.7 / 97.3 / 4 |
| doc:_doc_type | json_config | 309 | 95.8 / 99.0 / 10 | 98.4 / 98.4 / 0 |
| doc:_doc_type | legal | 699 | 93.8 / 95.4 / 11 | 97.0 / 97.9 / 6 |
| doc:_doc_type | pipe_table | 336 | 94.3 / 96.7 / 8 | 95.8 / 96.4 / 2 |
| doc:_doc_type | report | 709 | 94.6 / 96.2 / 10 | 98.0 / 98.0 / 0 |
| doc:_doc_type | support_ticket | 745 | 94.4 / 97.0 / 20 | 96.5 / 97.6 / 8 |
| doc:_doc_type | technical_log | 279 | 86.7 / 98.2 / 21 | 97.1 / 97.5 / 1 |
| doc:_doc_type | technical_note | 733 | 92.6 / 95.5 / 21 | 96.7 / 97.4 / 5 |
| doc:_hard_negatives | 0 | 2960 | 94.6 / 98.0 / 72 | 98.3 / 98.7 / 11 |
| doc:_hard_negatives | 1 | 2503 | 93.2 / 96.7 / 72 | 97.6 / 98.0 / 10 |
| doc:_hard_negatives | 2 | 2603 | 91.8 / 95.8 / 87 | 95.5 / 96.4 / 20 |
| doc:_hard_negatives | 3 | 1359 | 92.1 / 96.5 / 49 | 97.0 / 97.6 / 8 |
| doc:_hard_negatives | 4 | 1066 | 91.6 / 95.4 / 29 | 96.3 / 97.4 / 10 |
| doc:_hard_negatives | 5 | 27 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_register | bureaucratic | 1816 | 93.8 / 97.6 / 50 | 98.1 / 98.7 / 11 |
| doc:_register | casual | 1771 | 93.6 / 96.7 / 39 | 97.5 / 97.8 / 6 |
| doc:_register | formal | 1817 | 92.8 / 96.4 / 52 | 97.0 / 97.7 / 10 |
| doc:_register | neutral | 1686 | 93.9 / 97.2 / 42 | 97.6 / 98.2 / 9 |
| doc:_register | technical | 3428 | 91.7 / 96.1 / 126 | 96.1 / 96.7 / 23 |
| doc:_source | benchmark_structured_v3 | 1533 | 90.4 / 95.5 / 67 | 94.5 / 95.4 / 14 |
| doc:_source | benchmark_synthetic_diverse | 8985 | 93.4 / 96.9 / 242 | 97.5 / 98.1 / 45 |
| doc:lang | az | 10518 | 92.9 / 96.7 / 309 | 97.1 / 97.7 / 59 |
| doc:density | 0 | 0 | – / – / 0 | – / – / 0 |
| doc:density | 1 | 978 | 90.4 / 94.6 / 34 | 95.6 / 96.4 / 7 |
| doc:density | 2-3 | 6966 | 92.8 / 96.7 / 213 | 97.0 / 97.6 / 38 |
| doc:density | 4-6 | 2574 | 94.4 / 97.6 / 62 | 97.7 / 98.3 / 14 |

Calibration (score bins vs precision) is in the JSON. It is reported only and is never used to set a threshold (A2.2).
