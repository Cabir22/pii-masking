# Scoreboard: new_benchmark

| | |
|---|---|
| Model | `your-hf-org/masking-multi-m1-seed42` |
| Revision SHA | `d7493a1634f3aadc4dab5cd3b8103cf070e5eff0` |
| Requested revision | `d7493a1634f3aadc4dab5cd3b8103cf070e5eff0` |
| Code git SHA | `a8fa3adb367a97d76418451b00ad59dbe03f928f` (eval/ or model/ dirty) |
| Date (UTC) | 2026-10-24T00:46:44Z |
| Device | cuda |
| Libraries | tokenizers 0.22.2, transformers 4.57.6, torch 2.11.0+cu128, python 3.12.14 |
| Tracks | R = raw HF pipeline (simple), M = model-only product path |
| Data version | benchmark `b272b758eb6e4e5e` |

## A6 gates (shadow_dev, track R)

`benchmark` is the same metric on that set, track R: a reference while the shadow numbers are pending, never a gate.

| Gate | Measured | benchmark | Sprint 1 target | S1 | Sprint 2 target | S2 | Note |
|---|---|---|---|---|---|---|---|
| micro_f1 | n/a | 94.8 | >= 76.0 | – | >= 82.0 | – | shadow_dev not scored: shadow pending |
| weakest_label_f1 | n/a | 73.3 | >= 50.0 | – | >= 65.0 | – | shadow_dev not scored: shadow pending |
| ACCESS_TOKEN_f1 | n/a | 99.7 | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| IPV6_ADDRESS_f1 | n/a | 73.6 | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| AZ_DRIVER_LICENSE_NUMBER_f1 | n/a | 100.0 | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| hard_negative_trigger_rate | n/a | 2.4 | < 12.0 | – | < 8.0 | – | shadow_dev not scored: shadow pending |
| pii_free_fp_rate | n/a | 10.6 | < 30.0 | – | < 15.0 | – | shadow_dev not scored: shadow pending |
| recall_guard | n/a | n/a | no label -1 pt | – | no label -1 pt | – | no --baseline given |
| en_tr_ru_regression | n/a | n/a | <= 1 pt drop | – | <= 1 pt drop | – | no --baseline given |
| appendix_known_errors_fixed | n/a | n/a | reported by class | – | reported by class | – | appendix not scored |
| sealed_set | untouched | n/a | untouched | PASS | run once | – |  |

## Sets

Percentages. Exact = label+start+end. Trigger = decoy hit with the label it resembles (any label in brackets).

| Set | Track | Docs | Exact P / R / F1 | Macro F1 | Overlap F1 | Char leak | Narrower | Split | Trigger | Control FP | PII-free FP | Perfect |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| benchmark | R | 5000 | 93.3 / 96.5 / 94.8 | 94.9 | 96.4 | 2.0 | 99.0 | 127 | 2.4 (5.4) | – | 10.6 | 83.8 |
| benchmark excl. policy | R | 5000 | 95.2 / 96.5 / 95.8 | 95.8 | 97.4 | 2.0 | 99.0 | 127 | 1.7 (3.2) | – | 5.6 | 87.5 |
| benchmark | M | 5000 | 94.2 / 96.7 / 95.4 | 95.4 | 96.6 | 2.0 | 98.6 | 97 | 2.2 (5.0) | – | 9.8 | 84.8 |
| benchmark excl. policy | M | 5000 | 96.1 / 96.7 / 96.4 | 96.4 | 97.5 | 2.0 | 98.6 | 97 | 1.5 (2.8) | – | 4.7 | 88.6 |

### Slices: benchmark (exact recall / overlap recall / split spans)

| Slice | Value | Gold | R | M |
|---|---|---|---|---|
| doc:_adversarials | 0 | 2908 | 97.2 / 98.1 / 26 | 97.2 / 98.0 / 24 |
| doc:_adversarials | 1 | 2511 | 96.0 / 97.2 / 30 | 96.3 / 97.1 / 20 |
| doc:_adversarials | 2 | 2611 | 97.3 / 98.7 / 37 | 97.6 / 98.7 / 29 |
| doc:_adversarials | 3 | 1332 | 95.2 / 96.3 / 15 | 95.4 / 96.3 / 12 |
| doc:_adversarials | 4 | 1116 | 95.2 / 96.9 / 19 | 95.6 / 96.7 / 12 |
| doc:_adversarials | 5 | 40 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_benchmark_category | anchor_variant_hard_negative | 793 | 95.3 / 96.3 / 8 | 95.7 / 96.3 / 5 |
| doc:_benchmark_category | anchor_variant_positive | 1084 | 96.7 / 97.7 / 11 | 96.7 / 97.7 / 11 |
| doc:_benchmark_category | corrected_hard_negative | 151 | 97.4 / 98.0 / 1 | 97.4 / 97.4 / 0 |
| doc:_benchmark_category | hard_negative | 1300 | 93.6 / 95.4 / 23 | 94.3 / 95.3 / 13 |
| doc:_benchmark_category | mixed | 2187 | 96.8 / 97.9 / 21 | 97.0 / 97.8 / 17 |
| doc:_benchmark_category | natural_variant_hard_negative | 1047 | 95.1 / 96.8 / 17 | 95.4 / 96.6 / 12 |
| doc:_benchmark_category | natural_variant_positive | 1552 | 97.2 / 98.2 / 15 | 97.2 / 98.1 / 13 |
| doc:_benchmark_category | positive_control | 871 | 98.4 / 98.9 / 4 | 98.4 / 98.7 / 3 |
| doc:_benchmark_category | structured_csv | 300 | 96.7 / 98.7 / 6 | 98.0 / 98.7 / 2 |
| doc:_benchmark_category | structured_dialogue | 309 | 97.1 / 99.4 / 7 | 97.1 / 99.4 / 7 |
| doc:_benchmark_category | structured_json_config | 309 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_benchmark_category | structured_pipe_table | 336 | 96.4 / 100.0 / 12 | 96.4 / 100.0 / 12 |
| doc:_benchmark_category | structured_technical_log | 279 | 99.3 / 100.0 / 2 | 99.3 / 100.0 / 2 |
| doc:_bucket | long | 5640 | 96.4 / 97.5 / 58 | 96.6 / 97.4 / 45 |
| doc:_bucket | medium | 3342 | 95.9 / 97.2 / 42 | 96.1 / 97.0 / 29 |
| doc:_bucket | short | 3 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_bucket | structured | 1533 | 97.8 / 99.6 / 27 | 98.1 / 99.6 / 23 |
| doc:_doc_type | bank_message | 665 | 95.6 / 96.4 / 5 | 95.6 / 96.4 / 5 |
| doc:_doc_type | crm | 704 | 95.6 / 96.3 / 5 | 95.7 / 96.3 / 4 |
| doc:_doc_type | csv | 300 | 96.7 / 98.7 / 6 | 98.0 / 98.7 / 2 |
| doc:_doc_type | dialogue | 309 | 97.1 / 99.4 / 7 | 97.1 / 99.4 / 7 |
| doc:_doc_type | email | 684 | 95.5 / 96.6 / 7 | 95.6 / 96.3 / 4 |
| doc:_doc_type | first_person_chat | 838 | 98.2 / 98.7 / 4 | 98.3 / 98.7 / 3 |
| doc:_doc_type | first_person_email | 912 | 98.2 / 98.9 / 6 | 98.2 / 98.6 / 3 |
| doc:_doc_type | first_person_form | 924 | 98.1 / 99.4 / 11 | 98.3 / 99.2 / 8 |
| doc:_doc_type | form | 744 | 95.2 / 96.5 / 10 | 95.4 / 96.5 / 8 |
| doc:_doc_type | insurance | 628 | 97.0 / 98.6 / 10 | 97.5 / 98.6 / 7 |
| doc:_doc_type | json_config | 309 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_doc_type | legal | 699 | 94.1 / 95.6 / 10 | 94.4 / 95.6 / 8 |
| doc:_doc_type | pipe_table | 336 | 96.4 / 100.0 / 12 | 96.4 / 100.0 / 12 |
| doc:_doc_type | report | 709 | 94.9 / 96.9 / 14 | 95.3 / 96.8 / 10 |
| doc:_doc_type | support_ticket | 745 | 95.8 / 97.2 / 10 | 96.1 / 97.0 / 7 |
| doc:_doc_type | technical_log | 279 | 99.3 / 100.0 / 2 | 99.3 / 100.0 / 2 |
| doc:_doc_type | technical_note | 733 | 95.2 / 96.3 / 8 | 95.4 / 96.3 / 7 |
| doc:_hard_negatives | 0 | 2960 | 97.2 / 98.1 / 26 | 97.2 / 98.1 / 24 |
| doc:_hard_negatives | 1 | 2503 | 96.0 / 97.2 / 30 | 96.2 / 97.0 / 20 |
| doc:_hard_negatives | 2 | 2603 | 97.3 / 98.8 / 37 | 97.6 / 98.8 / 29 |
| doc:_hard_negatives | 3 | 1359 | 95.1 / 96.3 / 16 | 95.4 / 96.3 / 13 |
| doc:_hard_negatives | 4 | 1066 | 95.1 / 96.8 / 18 | 95.6 / 96.6 / 11 |
| doc:_hard_negatives | 5 | 27 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_register | bureaucratic | 1816 | 96.4 / 97.4 / 19 | 96.4 / 97.4 / 17 |
| doc:_register | casual | 1771 | 95.7 / 96.8 / 19 | 96.1 / 96.7 / 11 |
| doc:_register | formal | 1817 | 95.8 / 97.4 / 27 | 96.1 / 97.1 / 17 |
| doc:_register | neutral | 1686 | 96.9 / 97.7 / 14 | 96.9 / 97.7 / 12 |
| doc:_register | technical | 3428 | 97.1 / 98.5 / 48 | 97.3 / 98.5 / 40 |
| doc:_source | benchmark_structured_v3 | 1533 | 97.8 / 99.6 / 27 | 98.1 / 99.6 / 23 |
| doc:_source | benchmark_synthetic_diverse | 8985 | 96.2 / 97.4 / 100 | 96.4 / 97.3 / 74 |
| doc:lang | az | 10518 | 96.5 / 97.7 / 127 | 96.7 / 97.6 / 97 |
| doc:density | 0 | 0 | – / – / 0 | – / – / 0 |
| doc:density | 1 | 978 | 92.1 / 94.6 / 24 | 93.4 / 94.4 / 10 |
| doc:density | 2-3 | 6966 | 96.7 / 97.9 / 79 | 96.9 / 97.8 / 66 |
| doc:density | 4-6 | 2574 | 97.4 / 98.4 / 24 | 97.5 / 98.3 / 21 |

Calibration (score bins vs precision) is in the JSON. It is reported only and is never used to set a threshold (A2.2).
