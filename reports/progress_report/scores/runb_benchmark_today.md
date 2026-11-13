# Scoreboard: runb_benchmark_today

| | |
|---|---|
| Model | `your-hf-org/masking-az-runb-v2-seed42-2ep` |
| Revision SHA | `937f29d008f9f99d498e7686aa5e5dddf11ace14` |
| Requested revision | `937f29d008f9f99d498e7686aa5e5dddf11ace14` |
| Code git SHA | `2207eb5d038ed482e9b3d7b9e56a26ce75d6a92f` |
| Date (UTC) | 2026-10-16T11:18:56Z |
| Device | mps |
| Libraries | tokenizers 0.22.2, transformers 4.57.6, torch 2.14.0, python 3.11.16 |
| Tracks | R = raw HF pipeline (simple), M = model-only product path |
| Data version | benchmark `b272b758eb6e4e5e` |

## A6 gates (shadow_dev, track R)

`benchmark` is the same metric on that set, track R: a reference while the shadow numbers are pending, never a gate.

| Gate | Measured | benchmark | Sprint 1 target | S1 | Sprint 2 target | S2 | Note |
|---|---|---|---|---|---|---|---|
| micro_f1 | n/a | 88.9 | >= 76.0 | – | >= 82.0 | – | shadow_dev not scored: shadow pending |
| weakest_label_f1 | n/a | 56.2 | >= 50.0 | – | >= 65.0 | – | shadow_dev not scored: shadow pending |
| ACCESS_TOKEN_f1 | n/a | 98.7 | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| IPV6_ADDRESS_f1 | n/a | 95.3 | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| AZ_DRIVER_LICENSE_NUMBER_f1 | n/a | 92.9 | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| hard_negative_trigger_rate | n/a | 4.1 | < 12.0 | – | < 8.0 | – | shadow_dev not scored: shadow pending |
| pii_free_fp_rate | n/a | 15.5 | < 30.0 | – | < 15.0 | – | shadow_dev not scored: shadow pending |
| recall_guard | n/a | n/a | no label -1 pt | – | no label -1 pt | – | no --baseline given |
| en_tr_ru_regression | n/a | n/a | <= 1 pt drop | – | <= 1 pt drop | – | no --baseline given |
| appendix_known_errors_fixed | n/a | n/a | reported by class | – | reported by class | – | appendix not scored |
| sealed_set | untouched | n/a | untouched | PASS | run once | – |  |

## Sets

Percentages. Exact = label+start+end. Trigger = decoy hit with the label it resembles (any label in brackets).

| Set | Track | Docs | Exact P / R / F1 | Macro F1 | Overlap F1 | Char leak | Narrower | Split | Trigger | Control FP | PII-free FP | Perfect |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| benchmark | R | 5000 | 87.4 / 90.3 / 88.9 | 88.7 | 93.3 | 4.0 | 86.0 | 295 | 4.1 (7.3) | – | 15.5 | 71.4 |
| benchmark excl. policy | R | 5000 | 89.0 / 90.3 / 89.6 | 89.4 | 94.1 | 4.0 | 86.0 | 295 | 3.7 (5.5) | – | 10.6 | 74.0 |
| benchmark | M | 5000 | 90.5 / 93.4 / 92.0 | 92.0 | 93.1 | 3.1 | 99.3 | 92 | 5.0 (8.3) | – | 15.8 | 74.8 |
| benchmark excl. policy | M | 5000 | 92.0 / 93.4 / 92.7 | 92.7 | 93.9 | 3.1 | 99.3 | 92 | 4.7 (6.7) | – | 11.3 | 77.2 |

### Slices: benchmark (exact recall / overlap recall / split spans)

| Slice | Value | Gold | R | M |
|---|---|---|---|---|
| doc:_adversarials | 0 | 2908 | 93.9 / 96.1 / 37 | 96.6 / 96.9 / 10 |
| doc:_adversarials | 1 | 2511 | 91.2 / 94.1 / 59 | 93.9 / 94.6 / 17 |
| doc:_adversarials | 2 | 2611 | 87.3 / 93.0 / 132 | 91.5 / 93.2 / 43 |
| doc:_adversarials | 3 | 1332 | 89.6 / 92.7 / 34 | 92.1 / 93.0 / 12 |
| doc:_adversarials | 4 | 1116 | 87.1 / 91.1 / 33 | 90.6 / 91.4 / 9 |
| doc:_adversarials | 5 | 40 | 85.0 / 85.0 / 0 | 85.0 / 87.5 / 1 |
| doc:_benchmark_category | anchor_variant_hard_negative | 793 | 91.3 / 94.2 / 20 | 93.9 / 95.0 / 8 |
| doc:_benchmark_category | anchor_variant_positive | 1084 | 92.7 / 95.2 / 17 | 95.8 / 96.1 / 4 |
| doc:_benchmark_category | corrected_hard_negative | 151 | 84.1 / 86.1 / 2 | 85.4 / 85.4 / 0 |
| doc:_benchmark_category | hard_negative | 1300 | 86.6 / 90.2 / 34 | 89.7 / 90.5 / 11 |
| doc:_benchmark_category | mixed | 2187 | 90.9 / 93.8 / 49 | 93.6 / 94.3 / 15 |
| doc:_benchmark_category | natural_variant_hard_negative | 1047 | 89.4 / 92.8 / 27 | 92.6 / 93.2 / 7 |
| doc:_benchmark_category | natural_variant_positive | 1552 | 94.8 / 97.0 / 17 | 97.1 / 97.5 / 5 |
| doc:_benchmark_category | positive_control | 871 | 94.0 / 96.0 / 14 | 96.6 / 96.9 / 3 |
| doc:_benchmark_category | structured_csv | 300 | 75.0 / 84.7 / 29 | 78.7 / 84.7 / 18 |
| doc:_benchmark_category | structured_dialogue | 309 | 86.7 / 91.9 / 16 | 88.3 / 91.3 / 9 |
| doc:_benchmark_category | structured_json_config | 309 | 88.3 / 97.4 / 28 | 96.1 / 97.1 / 3 |
| doc:_benchmark_category | structured_pipe_table | 336 | 92.0 / 95.2 / 11 | 93.2 / 94.9 / 6 |
| doc:_benchmark_category | structured_technical_log | 279 | 81.4 / 96.8 / 31 | 95.7 / 96.8 / 3 |
| doc:_bucket | long | 5640 | 90.8 / 93.6 / 120 | 93.7 / 94.3 / 35 |
| doc:_bucket | medium | 3342 | 92.0 / 94.6 / 60 | 94.4 / 95.0 / 18 |
| doc:_bucket | short | 3 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_bucket | structured | 1533 | 84.9 / 93.2 / 115 | 90.4 / 93.0 / 39 |
| doc:_doc_type | bank_message | 665 | 91.0 / 92.9 / 13 | 93.5 / 94.3 / 5 |
| doc:_doc_type | crm | 704 | 89.3 / 91.3 / 14 | 91.5 / 92.5 / 7 |
| doc:_doc_type | csv | 300 | 75.0 / 84.7 / 29 | 78.7 / 84.7 / 18 |
| doc:_doc_type | dialogue | 309 | 86.7 / 91.9 / 16 | 88.3 / 91.3 / 9 |
| doc:_doc_type | email | 684 | 89.3 / 91.5 / 14 | 92.3 / 92.8 / 3 |
| doc:_doc_type | first_person_chat | 838 | 93.6 / 96.8 / 11 | 96.8 / 97.0 / 2 |
| doc:_doc_type | first_person_email | 912 | 93.6 / 97.9 / 15 | 97.5 / 97.6 / 1 |
| doc:_doc_type | first_person_form | 924 | 93.3 / 97.5 / 13 | 96.8 / 96.9 / 1 |
| doc:_doc_type | form | 744 | 91.0 / 93.7 / 20 | 93.0 / 93.7 / 5 |
| doc:_doc_type | insurance | 628 | 91.6 / 94.4 / 18 | 93.0 / 93.9 / 6 |
| doc:_doc_type | json_config | 309 | 88.3 / 97.4 / 28 | 96.1 / 97.1 / 3 |
| doc:_doc_type | legal | 699 | 89.4 / 91.7 / 16 | 91.6 / 92.7 / 8 |
| doc:_doc_type | pipe_table | 336 | 92.0 / 95.2 / 11 | 93.2 / 94.9 / 6 |
| doc:_doc_type | report | 709 | 89.3 / 91.4 / 14 | 92.5 / 92.8 / 2 |
| doc:_doc_type | support_ticket | 745 | 90.3 / 92.9 / 19 | 92.9 / 93.7 / 6 |
| doc:_doc_type | technical_log | 279 | 81.4 / 96.8 / 31 | 95.7 / 96.8 / 3 |
| doc:_doc_type | technical_note | 733 | 91.4 / 93.2 / 13 | 93.9 / 94.8 / 7 |
| doc:_hard_negatives | 0 | 2960 | 93.4 / 95.6 / 38 | 95.9 / 96.3 / 11 |
| doc:_hard_negatives | 1 | 2503 | 91.1 / 94.0 / 58 | 94.0 / 94.6 / 16 |
| doc:_hard_negatives | 2 | 2603 | 87.4 / 93.2 / 132 | 91.5 / 93.2 / 43 |
| doc:_hard_negatives | 3 | 1359 | 88.5 / 91.8 / 36 | 91.5 / 92.4 / 12 |
| doc:_hard_negatives | 4 | 1066 | 89.2 / 93.2 / 31 | 92.4 / 93.2 / 9 |
| doc:_hard_negatives | 5 | 27 | 96.3 / 96.3 / 0 | 96.3 / 100.0 / 1 |
| doc:_register | bureaucratic | 1816 | 91.7 / 94.5 / 33 | 94.5 / 94.9 / 8 |
| doc:_register | casual | 1771 | 91.1 / 94.2 / 42 | 94.2 / 95.0 / 14 |
| doc:_register | formal | 1817 | 90.6 / 93.6 / 41 | 93.3 / 93.9 / 9 |
| doc:_register | neutral | 1686 | 91.6 / 94.1 / 30 | 94.2 / 94.7 / 8 |
| doc:_register | technical | 3428 | 88.4 / 93.4 / 149 | 92.2 / 93.8 / 53 |
| doc:_source | benchmark_structured_v3 | 1533 | 84.9 / 93.2 / 115 | 90.4 / 93.0 / 39 |
| doc:_source | benchmark_synthetic_diverse | 8985 | 91.2 / 94.0 / 180 | 94.0 / 94.6 / 53 |
| doc:lang | az | 10518 | 90.3 / 93.9 / 295 | 93.4 / 94.3 / 92 |
| doc:density | 0 | 0 | – / – / 0 | – / – / 0 |
| doc:density | 1 | 978 | 86.8 / 90.7 / 31 | 90.2 / 91.0 / 8 |
| doc:density | 2-3 | 6966 | 89.9 / 93.9 / 223 | 93.2 / 94.3 / 71 |
| doc:density | 4-6 | 2574 | 92.8 / 95.1 / 41 | 95.3 / 95.8 / 13 |

Calibration (score bins vs precision) is in the JSON. It is reported only and is never used to set a threshold (A2.2).
