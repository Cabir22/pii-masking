# Scoreboard: new_probes

| | |
|---|---|
| Model | `/private/tmp/claude-501/-Users-user-HAL-X-pii-masking-model/692921e0-3cc7-4991-bb18-a10eb02fa39f/scratchpad/v3_puncttok` |
| Revision SHA | `local-sha256:6e2f021c5ef3744d` |
| Requested revision | `None` |
| Code git SHA | `c195e64ca5dcc93d8ca5b37d65d6e19fcf55cc0b` |
| Date (UTC) | 2026-10-14T17:40:11Z |
| Device | mps |
| Libraries | tokenizers 0.22.2, transformers 4.57.6, torch 2.14.0, python 3.11.16 |
| Tracks | R = raw HF pipeline (simple), M = model-only product path |
| Data version | probes `94ca93d9b4b51548` |

## A6 gates (shadow_dev, track R)

`benchmark` is the same metric on that set, track R: a reference while the shadow numbers are pending, never a gate.

| Gate | Measured | benchmark | Sprint 1 target | S1 | Sprint 2 target | S2 | Note |
|---|---|---|---|---|---|---|---|
| micro_f1 | n/a | n/a | >= 76.0 | – | >= 82.0 | – | shadow_dev not scored: shadow pending |
| weakest_label_f1 | n/a | n/a | >= 50.0 | – | >= 65.0 | – | shadow_dev not scored: shadow pending |
| ACCESS_TOKEN_f1 | n/a | n/a | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| IPV6_ADDRESS_f1 | n/a | n/a | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| AZ_DRIVER_LICENSE_NUMBER_f1 | n/a | n/a | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| hard_negative_trigger_rate | n/a | n/a | < 12.0 | – | < 8.0 | – | shadow_dev not scored: shadow pending |
| pii_free_fp_rate | n/a | n/a | < 30.0 | – | < 15.0 | – | shadow_dev not scored: shadow pending |
| recall_guard | n/a | n/a | no label -1 pt | – | no label -1 pt | – | no --baseline given |
| en_tr_ru_regression | n/a | n/a | <= 1 pt drop | – | <= 1 pt drop | – | no --baseline given |
| appendix_known_errors_fixed | n/a | n/a | reported by class | – | reported by class | – | appendix not scored |
| sealed_set | untouched | n/a | untouched | PASS | run once | – |  |

## Sets

Percentages. Exact = label+start+end. Trigger = decoy hit with the label it resembles (any label in brackets).

| Set | Track | Docs | Exact P / R / F1 | Macro F1 | Overlap F1 | Char leak | Narrower | Split | Trigger | Control FP | PII-free FP | Perfect |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| probes | R | 1656 | 90.0 / 95.1 / 92.5 | 87.3 | 93.8 | 24.5 | 100.0 | 19 | 9.4 (13.1) | 0.0 rec, 17.1 span | 19.9 | 89.1 |
| probes excl. policy | R | 1656 | 90.7 / 95.1 / 92.9 | 87.9 | 94.2 | 24.5 | 100.0 | 19 | 7.2 (11.2) | 0.0 rec, 17.1 span | 16.7 | 90.0 |
| probes | M | 1656 | 87.8 / 89.7 / 88.7 | 87.2 | 94.0 | 20.9 | 30.9 | 16 | 9.2 (12.5) | 0.0 rec, 15.4 span | 18.9 | 88.9 |
| probes excl. policy | M | 1656 | 88.5 / 89.7 / 89.1 | 88.0 | 94.4 | 20.9 | 30.9 | 16 | 7.0 (10.6) | 0.0 rec, 15.4 span | 15.8 | 89.8 |

## Probe targets (track R): 34/52 families pass; 16/52 show their failure

| Family | Docs | Condition | Measured | Target | Pass | Shows the failure |
|---|---|---|---|---|---|---|
| anchor_distance | 24 | exact_recall | 83.3 | >= 80.0 | PASS | **NO** |
| bare_name | 43 | exact_recall | 100.0 | >= 90.0 | PASS | **NO** |
|  |  | split_spans | 0 | == 0 | PASS |  |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| building_vs_room | 24 | control_fp_rate | 25.0 | <= ×0.3 ckpt1 | – | yes |
|  |  | sanity: control_fp_rate | 25.0 | >= 10.0 | PASS |  |
| casing_noise | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| contrast_ipv6_mac | 60 | exact_recall [IPV6_ADDRESS] | 100.0 | >= 80.0 | PASS | **NO** |
|  |  | exact_recall [MAC_ADDRESS] | 100.0 | >= 80.0 | PASS |  |
|  |  | confusion_rate IPV6_ADDRESS→MAC_ADDRESS | 0.0 | < 5.0 | PASS |  |
|  |  | confusion_rate MAC_ADDRESS→IPV6_ADDRESS | 0.0 | < 5.0 | PASS |  |
|  |  | decoy_trigger_rate | 9.1 | < 15.0 | PASS |  |
| contrast_licence_id | 26 | confusion_rate AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER | 0.0 | < 5.0 | PASS | **NO** |
|  |  | confusion_rate AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER | 0.0 | < 5.0 | PASS |  |
|  |  | exact_recall [AZ_DRIVER_LICENSE_NUMBER] | 100.0 | >= 80.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | >= 80.0 | PASS |  |
|  |  | decoy_trigger_rate | 10.0 | < 15.0 | PASS |  |
| contrast_token_key | 24 | exact_recall [ACCESS_TOKEN] | 100.0 | >= 80.0 | PASS | **NO** |
|  |  | exact_recall [API_KEY] | 100.0 | >= 80.0 | PASS |  |
|  |  | confusion_rate ACCESS_TOKEN→API_KEY | 0.0 | < 10.0 | PASS |  |
|  |  | confusion_rate API_KEY→ACCESS_TOKEN | 0.0 | < 10.0 | PASS |  |
|  |  | decoy_trigger_rate | 0.0 | < 15.0 | PASS |  |
| date_vs_timestamp | 22 | exact_recall [DATE] | 100.0 | >= 80.0 | PASS | yes |
|  |  | decoy_trigger_rate | 16.7 | < 15.0 | FAIL |  |
| decoy_age | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_card_iccid_iban | 24 | decoy_trigger_rate | 33.3 | < 15.0 | FAIL | yes |
| decoy_cvv | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_date | 24 | decoy_trigger_rate | 33.3 | < 15.0 | FAIL | yes |
| decoy_fin | 24 | decoy_trigger_rate | 44.4 | < 15.0 | FAIL | yes |
| decoy_ipv4 | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_ipv6_mac | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_names_as_org | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_time | 24 | decoy_trigger_rate | 25.0 | < 15.0 | FAIL | yes |
| decoy_voen_passport_id | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_zip | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| fmt_csv | 24 | exact_recall | 100.0 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 100.0 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_csv_noheader | 24 | exact_recall | 97.9 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 100.0 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 91.7 | > 60.0 | PASS |  |
| fmt_dialogue | 24 | exact_recall | 100.0 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 100.0 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_json | 24 | exact_recall | 100.0 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 100.0 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_kv | 24 | exact_recall | 100.0 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 100.0 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_log | 24 | exact_recall | 100.0 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 100.0 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_pipe | 24 | exact_recall | 100.0 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 100.0 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| foreign_names | 30 | exact_recall [GIVENNAME,SURNAME] | 95.0 | >= 80.0 | PASS | **NO** |
|  |  | decoy_trigger_rate_any | 0.0 | < 15.0 | PASS |  |
| homograph_pairs | 16 | exact_recall [GIVENNAME] | 93.8 | >= 90.0 | PASS | **NO** |
|  |  | control_fp_rate | 6.2 | < 10.0 | PASS |  |
| inflected_anchor | 24 | exact_recall | 91.7 | >= 80.0 | PASS | **NO** |
| ipv6_vs_mac | 24 | exact_recall [IPV6_ADDRESS] | 100.0 | >= 80.0 | PASS | **NO** |
|  |  | confusion_rate IPV6_ADDRESS→MAC_ADDRESS | 0.0 | < 5.0 | PASS |  |
| licence_vs_id | 24 | confusion_rate AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER | 0.0 | < 5.0 | PASS | yes |
|  |  | confusion_rate AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER | 8.3 | < 5.0 | FAIL |  |
| name_homographs | 64 | exact_recall [GIVENNAME] | 100.0 | >= 90.0 | PASS | yes |
|  |  | control_fp_rate | 21.9 | < 10.0 | FAIL |  |
| name_transliteration_variants | 80 | exact_recall | 100.0 | >= 90.0 | PASS | **NO** |
|  |  | wrong_label | 0 | == 0 | PASS |  |
| names_after_role | 24 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 90.0 | PASS | yes |
|  |  | control_fp_rate | 25.0 | < 10.0 | FAIL |  |
| names_list_lines | 14 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 90.0 | PASS | yes |
|  |  | control_fp_rate | 50.0 | < 10.0 | FAIL |  |
| names_sentence_start | 26 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 90.0 | PASS | **NO** |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| names_signature | 24 | exact_recall [GIVENNAME,SURNAME] | 97.5 | >= 90.0 | PASS | **NO** |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| noisy_suffixes | 36 | exact_recall [GIVENNAME,SURNAME,CITY] | 91.7 | >= 85.0 | PASS | **NO** |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| nonpii_ids | 24 | control_fp_rate | 50.0 | <= ×0.3 ckpt1 | – | yes |
|  |  | sanity: control_fp_rate | 50.0 | >= 10.0 | PASS |  |
| pem | 20 | char_leakage_rate | 51.7 | < ×1.0 ckpt1 | – | yes |
|  |  | sanity: exact_recall | 0.0 | < 90.0 | PASS |  |
| pii_free | 24 | pii_free_fp_rate | 0.0 | < 15.0 | PASS | **NO** |
| prose_card | 24 | exact_recall | 16.7 | >= 80.0 | FAIL | yes |
| prose_date | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| prose_iban | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| punct_touching | 24 | exact_recall | 100.0 | >= 90.0 | PASS | **NO** |
| sentence_initial_nouns | 24 | control_fp_rate | 0.0 | <= ×0.3 ckpt1 | – | **NO** |
|  |  | sanity: control_fp_rate | 0.0 | >= 10.0 | FAIL |  |
| single_entity | 24 | exact_f1 | 82.8 | >= 80.0 | PASS | **NO** |
| spaced_card_iban | 24 | char_leakage_rate | 0.0 | < ×1.0 ckpt1 | – | **NO** |
|  |  | sanity: exact_recall | 100.0 | < 90.0 | FAIL |  |
| spaced_phone | 24 | char_leakage_rate | 35.2 | < ×1.0 ckpt1 | – | yes |
|  |  | sanity: exact_recall | 41.7 | < 90.0 | PASS |  |
| suffixed_entities | 273 | case_exact_recall_min | 66.7 | >= 85.0 | FAIL | yes |
| token_vs_key | 24 | exact_recall [ACCESS_TOKEN] | 83.3 | >= 80.0 | PASS | **NO** |
|  |  | confusion_rate ACCESS_TOKEN→API_KEY | 0.0 | < 10.0 | PASS |  |
| villages | 34 | exact_recall [CITY] | 80.8 | >= 80.0 | PASS | yes |
|  |  | control_fp_rate | 11.1 | < 10.0 | FAIL |  |

`decoy_cvv` look-alikes masked as CVV, by kind: `12345` dummies (D-2) 0/2; random 5-digit codes 0/5; dashed, policy (D-34c) 2/2; dashed, policy (D-39c) 3/3

## Probe targets (track M): 34/52 families pass; 16/52 show their failure

| Family | Docs | Condition | Measured | Target | Pass | Shows the failure |
|---|---|---|---|---|---|---|
| anchor_distance | 24 | exact_recall | 91.7 | >= 80.0 | PASS | **NO** |
| bare_name | 43 | exact_recall | 100.0 | >= 90.0 | PASS | **NO** |
|  |  | split_spans | 0 | == 0 | PASS |  |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| building_vs_room | 24 | control_fp_rate | 25.0 | <= ×0.3 ckpt1 | – | yes |
|  |  | sanity: control_fp_rate | 25.0 | >= 10.0 | PASS |  |
| casing_noise | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| contrast_ipv6_mac | 60 | exact_recall [IPV6_ADDRESS] | 100.0 | >= 80.0 | PASS | **NO** |
|  |  | exact_recall [MAC_ADDRESS] | 100.0 | >= 80.0 | PASS |  |
|  |  | confusion_rate IPV6_ADDRESS→MAC_ADDRESS | 0.0 | < 5.0 | PASS |  |
|  |  | confusion_rate MAC_ADDRESS→IPV6_ADDRESS | 0.0 | < 5.0 | PASS |  |
|  |  | decoy_trigger_rate | 9.1 | < 15.0 | PASS |  |
| contrast_licence_id | 26 | confusion_rate AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER | 0.0 | < 5.0 | PASS | **NO** |
|  |  | confusion_rate AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER | 0.0 | < 5.0 | PASS |  |
|  |  | exact_recall [AZ_DRIVER_LICENSE_NUMBER] | 100.0 | >= 80.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | >= 80.0 | PASS |  |
|  |  | decoy_trigger_rate | 10.0 | < 15.0 | PASS |  |
| contrast_token_key | 24 | exact_recall [ACCESS_TOKEN] | 100.0 | >= 80.0 | PASS | **NO** |
|  |  | exact_recall [API_KEY] | 100.0 | >= 80.0 | PASS |  |
|  |  | confusion_rate ACCESS_TOKEN→API_KEY | 0.0 | < 10.0 | PASS |  |
|  |  | confusion_rate API_KEY→ACCESS_TOKEN | 0.0 | < 10.0 | PASS |  |
|  |  | decoy_trigger_rate | 0.0 | < 15.0 | PASS |  |
| date_vs_timestamp | 22 | exact_recall [DATE] | 100.0 | >= 80.0 | PASS | yes |
|  |  | decoy_trigger_rate | 16.7 | < 15.0 | FAIL |  |
| decoy_age | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_card_iccid_iban | 24 | decoy_trigger_rate | 33.3 | < 15.0 | FAIL | yes |
| decoy_cvv | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_date | 24 | decoy_trigger_rate | 33.3 | < 15.0 | FAIL | yes |
| decoy_fin | 24 | decoy_trigger_rate | 33.3 | < 15.0 | FAIL | yes |
| decoy_ipv4 | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_ipv6_mac | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_names_as_org | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_time | 24 | decoy_trigger_rate | 25.0 | < 15.0 | FAIL | yes |
| decoy_voen_passport_id | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_zip | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| fmt_csv | 24 | exact_recall | 100.0 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 100.0 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_csv_noheader | 24 | exact_recall | 97.9 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 100.0 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 91.7 | > 60.0 | PASS |  |
| fmt_dialogue | 24 | exact_recall | 100.0 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 100.0 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_json | 24 | exact_recall | 100.0 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 100.0 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_kv | 24 | exact_recall | 100.0 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 100.0 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_log | 24 | exact_recall | 100.0 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 100.0 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_pipe | 24 | exact_recall | 100.0 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 100.0 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| foreign_names | 30 | exact_recall [GIVENNAME,SURNAME] | 90.0 | >= 80.0 | PASS | **NO** |
|  |  | decoy_trigger_rate_any | 0.0 | < 15.0 | PASS |  |
| homograph_pairs | 16 | exact_recall [GIVENNAME] | 93.8 | >= 90.0 | PASS | **NO** |
|  |  | control_fp_rate | 6.2 | < 10.0 | PASS |  |
| inflected_anchor | 24 | exact_recall | 91.7 | >= 80.0 | PASS | **NO** |
| ipv6_vs_mac | 24 | exact_recall [IPV6_ADDRESS] | 100.0 | >= 80.0 | PASS | **NO** |
|  |  | confusion_rate IPV6_ADDRESS→MAC_ADDRESS | 0.0 | < 5.0 | PASS |  |
| licence_vs_id | 24 | confusion_rate AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER | 0.0 | < 5.0 | PASS | yes |
|  |  | confusion_rate AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER | 8.3 | < 5.0 | FAIL |  |
| name_homographs | 64 | exact_recall [GIVENNAME] | 100.0 | >= 90.0 | PASS | yes |
|  |  | control_fp_rate | 18.8 | < 10.0 | FAIL |  |
| name_transliteration_variants | 80 | exact_recall | 100.0 | >= 90.0 | PASS | **NO** |
|  |  | wrong_label | 0 | == 0 | PASS |  |
| names_after_role | 24 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 90.0 | PASS | yes |
|  |  | control_fp_rate | 25.0 | < 10.0 | FAIL |  |
| names_list_lines | 14 | exact_recall [GIVENNAME,SURNAME] | 47.4 | >= 90.0 | FAIL | yes |
|  |  | control_fp_rate | 50.0 | < 10.0 | FAIL |  |
| names_sentence_start | 26 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 90.0 | PASS | **NO** |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| names_signature | 24 | exact_recall [GIVENNAME,SURNAME] | 97.5 | >= 90.0 | PASS | **NO** |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| noisy_suffixes | 36 | exact_recall [GIVENNAME,SURNAME,CITY] | 91.7 | >= 85.0 | PASS | **NO** |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| nonpii_ids | 24 | control_fp_rate | 41.7 | <= ×0.3 ckpt1 | – | yes |
|  |  | sanity: control_fp_rate | 41.7 | >= 10.0 | PASS |  |
| pem | 20 | char_leakage_rate | 43.9 | < ×1.0 ckpt1 | – | yes |
|  |  | sanity: exact_recall | 0.0 | < 90.0 | PASS |  |
| pii_free | 24 | pii_free_fp_rate | 0.0 | < 15.0 | PASS | **NO** |
| prose_card | 24 | exact_recall | 25.0 | >= 80.0 | FAIL | yes |
| prose_date | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| prose_iban | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| punct_touching | 24 | exact_recall | 100.0 | >= 90.0 | PASS | **NO** |
| sentence_initial_nouns | 24 | control_fp_rate | 0.0 | <= ×0.3 ckpt1 | – | **NO** |
|  |  | sanity: control_fp_rate | 0.0 | >= 10.0 | FAIL |  |
| single_entity | 24 | exact_f1 | 82.8 | >= 80.0 | PASS | **NO** |
| spaced_card_iban | 24 | char_leakage_rate | 0.0 | < ×1.0 ckpt1 | – | **NO** |
|  |  | sanity: exact_recall | 100.0 | < 90.0 | FAIL |  |
| spaced_phone | 24 | char_leakage_rate | 35.2 | < ×1.0 ckpt1 | – | yes |
|  |  | sanity: exact_recall | 41.7 | < 90.0 | PASS |  |
| suffixed_entities | 273 | case_exact_recall_min | 66.7 | >= 85.0 | FAIL | yes |
| token_vs_key | 24 | exact_recall [ACCESS_TOKEN] | 83.3 | >= 80.0 | PASS | **NO** |
|  |  | confusion_rate ACCESS_TOKEN→API_KEY | 0.0 | < 10.0 | PASS |  |
| villages | 34 | exact_recall [CITY] | 80.8 | >= 80.0 | PASS | yes |
|  |  | control_fp_rate | 11.1 | < 10.0 | FAIL |  |

`decoy_cvv` look-alikes masked as CVV, by kind: `12345` dummies (D-2) 0/2; random 5-digit codes 0/5; dashed, policy (D-34c) 2/2; dashed, policy (D-39c) 3/3

### Slices: probes (exact recall / overlap recall / split spans)

| Slice | Value | Gold | R | M |
|---|---|---|---|---|
| entity:case | abl | 21 | 81.0 / 81.0 / 0 | 81.0 / 81.0 / 0 |
| entity:case | acc_consonant | 21 | 85.7 / 85.7 / 0 | 85.7 / 85.7 / 0 |
| entity:case | acc_vowel | 21 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:case | apostrophe | 21 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:case | ascii_folded | 21 | 85.7 / 85.7 / 0 | 85.7 / 85.7 / 0 |
| entity:case | cop | 21 | 66.7 / 66.7 / 0 | 66.7 / 66.7 / 0 |
| entity:case | dat | 21 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:case | gen | 33 | 72.7 / 72.7 / 0 | 72.7 / 72.7 / 0 |
| entity:case | ins | 21 | 81.0 / 81.0 / 0 | 81.0 / 81.0 / 0 |
| entity:case | loc | 21 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:case | pl | 21 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:case | pl_case | 21 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:case | rel | 21 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:entity_noise | case_or_ascii | 12 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:form | dmy_dot | 4 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:form | dmy_dot_short | 3 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:form | dmy_slash | 3 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:form | end | 4 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:form | full | 2 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:form | iso | 3 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:form | link_local | 4 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:form | mapped | 4 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:form | mid | 6 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:form | prefix_one | 4 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:form | upper | 2 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:form | worded | 3 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:noise | buffer | 6 | 83.3 / 83.3 / 0 | 83.3 / 83.3 / 0 |
| entity:noise | colloquial | 6 | 83.3 / 83.3 / 0 | 83.3 / 83.3 / 0 |
| entity:noise | double | 6 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:noise | harmony | 6 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:origin | en_eu | 10 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:origin | fa_ar | 8 | 87.5 / 87.5 / 0 | 75.0 / 87.5 / 0 |
| entity:origin | ka | 6 | 83.3 / 83.3 / 0 | 66.7 / 83.3 / 0 |
| entity:origin | ru | 10 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:origin | tr | 6 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:role | given | 57 | 100.0 / 100.0 / 0 | 21.1 / 100.0 / 0 |
| entity:role | patronymic | 57 | 100.0 / 100.0 / 0 | 21.1 / 100.0 / 0 |
| entity:sep | colon | 8 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:sep | dot | 7 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:sep | hyphen | 7 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:variant | ascii_or_ru_latin | 16 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:variant | az_latin | 16 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:variant | cyrillic | 16 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:variant | en_latin | 16 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:variant | tr_or_other | 16 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:control | True | 0 | – / – / 0 | – / – / 0 |
| doc:lang | az | 1644 | 95.1 / 96.3 / 19 | 89.7 / 96.2 / 16 |
| doc:resembles | GIVENNAME | 0 | – / – / 0 | – / – / 0 |
| doc:same_body | False | 8 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:same_body | True | 16 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:density | 0 | 0 | – / – / 0 | – / – / 0 |
| doc:density | 1 | 1019 | 92.5 / 94.3 / 18 | 92.7 / 94.3 / 16 |
| doc:density | 2-3 | 454 | 99.1 / 99.3 / 1 | 98.7 / 99.1 / 0 |
| doc:density | 7+ | 171 | 100.0 / 100.0 / 0 | 47.4 / 100.0 / 0 |
| control:kind | common_noun | 6 spans | FP 0.0 | FP 0.0 |
| control:kind | common_word | 4 spans | FP 0.0 | FP 0.0 |
| control:kind | department_signature | 4 spans | FP 0.0 | FP 0.0 |
| control:kind | generic_place | 5 spans | FP 20.0 | FP 20.0 |
| control:kind | homograph_word | 48 spans | FP 16.7 | FP 14.6 |
| control:kind | noisy_suffix_noun | 12 spans | FP 0.0 | FP 0.0 |
| … | 18 more rows in the JSON | | |

Calibration (score bins vs precision) is in the JSON. It is reported only and is never used to set a threshold (A2.2).
