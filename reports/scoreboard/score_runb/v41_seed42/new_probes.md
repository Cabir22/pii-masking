# Scoreboard: new_probes

| | |
|---|---|
| Model | `your-hf-org/masking-az-runb-v4.1-seed42` |
| Revision SHA | `502598c1d5850958e98b1922ce65d504f700b528` |
| Requested revision | `502598c1d5850958e98b1922ce65d504f700b528` |
| Code git SHA | `3b40bdde519bc0fc5fc62437f5473a7e6fac2f7e` |
| Date (UTC) | 2026-10-19T10:59:44Z |
| Device | cpu |
| Libraries | tokenizers 0.22.2, transformers 4.57.6, torch 2.11.0+cu128, python 3.12.14 |
| Tracks | R = raw HF pipeline (simple), M = model-only product path |
| Data version | probes `3745ab94398c24c8` |

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
| probes | R | 1656 | 90.0 / 96.6 / 93.2 | 90.6 | 94.9 | 0.3 | 100.0 | 22 | 12.2 (13.5) | 0.0 rec, 17.9 span | 20.5 | 90.6 |
| probes excl. policy | R | 1656 | 92.3 / 96.6 / 94.4 | 93.3 | 96.1 | 0.3 | 100.0 | 22 | 5.1 (6.4) | 0.0 rec, 17.9 span | 11.0 | 93.2 |
| probes | M | 1656 | 91.2 / 97.1 / 94.1 | 91.6 | 95.2 | 0.2 | 100.0 | 13 | 11.6 (12.9) | 0.0 rec, 17.1 span | 19.6 | 91.4 |
| probes excl. policy | M | 1656 | 93.3 / 97.1 / 95.2 | 94.2 | 96.3 | 0.2 | 100.0 | 13 | 4.7 (6.0) | 0.0 rec, 17.1 span | 10.3 | 93.9 |

## Probe targets (track R): 32/52 families pass; 15/52 show their failure

| Family | Docs | Condition | Measured | Target | Pass | Shows the failure |
|---|---|---|---|---|---|---|
| anchor_distance | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| bare_name | 43 | exact_recall | 100.0 | >= 90.0 | PASS | **NO** |
|  |  | split_spans | 0 | == 0 | PASS |  |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| building_vs_room | 24 | control_fp_rate | 0.0 | <= ×0.3 ckpt1 | – | **NO** |
|  |  | sanity: control_fp_rate | 0.0 | >= 10.0 | FAIL |  |
| casing_noise | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| contrast_ipv6_mac | 60 | exact_recall [IPV6_ADDRESS] | 100.0 | >= 80.0 | PASS | **NO** |
|  |  | exact_recall [MAC_ADDRESS] | 100.0 | >= 80.0 | PASS |  |
|  |  | confusion_rate IPV6_ADDRESS→MAC_ADDRESS | 0.0 | < 5.0 | PASS |  |
|  |  | confusion_rate MAC_ADDRESS→IPV6_ADDRESS | 0.0 | < 5.0 | PASS |  |
|  |  | decoy_trigger_rate | 13.6 | < 15.0 | PASS |  |
| contrast_licence_id | 26 | confusion_rate AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER | 0.0 | < 5.0 | PASS | **NO** |
|  |  | confusion_rate AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER | 0.0 | < 5.0 | PASS |  |
|  |  | exact_recall [AZ_DRIVER_LICENSE_NUMBER] | 100.0 | >= 80.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | >= 80.0 | PASS |  |
|  |  | decoy_trigger_rate | 0.0 | < 15.0 | PASS |  |
| contrast_token_key | 24 | exact_recall [ACCESS_TOKEN] | 93.8 | >= 80.0 | PASS | **NO** |
|  |  | exact_recall [API_KEY] | 100.0 | >= 80.0 | PASS |  |
|  |  | confusion_rate ACCESS_TOKEN→API_KEY | 0.0 | < 10.0 | PASS |  |
|  |  | confusion_rate API_KEY→ACCESS_TOKEN | 0.0 | < 10.0 | PASS |  |
|  |  | decoy_trigger_rate | 0.0 | < 15.0 | PASS |  |
| date_vs_timestamp | 22 | exact_recall [DATE] | 100.0 | >= 80.0 | PASS | yes |
|  |  | decoy_trigger_rate | 16.7 | < 15.0 | FAIL |  |
| decoy_age | 24 | decoy_trigger_rate | 8.3 | < 15.0 | PASS | **NO** |
| decoy_card_iccid_iban | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_cvv | 24 | decoy_trigger_rate | 14.3 | < 15.0 | PASS | **NO** |
| decoy_date | 24 | decoy_trigger_rate | 25.0 | < 15.0 | FAIL | yes |
| decoy_fin | 24 | decoy_trigger_rate | 40.0 | < 15.0 | FAIL | yes |
| decoy_ipv4 | 24 | decoy_trigger_rate | 16.7 | < 15.0 | FAIL | yes |
| decoy_ipv6_mac | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_names_as_org | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_time | 24 | decoy_trigger_rate | 50.0 | < 15.0 | FAIL | yes |
| decoy_voen_passport_id | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_zip | 24 | decoy_trigger_rate | 8.3 | < 15.0 | PASS | **NO** |
| fmt_csv | 24 | exact_recall | 83.3 | >= 70.0 | PASS | yes |
|  |  | exact_recall [EMAIL] | 33.3 | > 60.0 | FAIL |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_csv_noheader | 24 | exact_recall | 87.5 | >= 70.0 | PASS | yes |
|  |  | exact_recall [EMAIL] | 50.0 | > 60.0 | FAIL |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
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
| foreign_names | 30 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 80.0 | PASS | **NO** |
|  |  | decoy_trigger_rate_any | 0.0 | < 15.0 | PASS |  |
| homograph_pairs | 16 | exact_recall [GIVENNAME] | 93.8 | >= 90.0 | PASS | yes |
|  |  | control_fp_rate | 18.8 | < 10.0 | FAIL |  |
| inflected_anchor | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| ipv6_vs_mac | 24 | exact_recall [IPV6_ADDRESS] | 100.0 | >= 80.0 | PASS | **NO** |
|  |  | confusion_rate IPV6_ADDRESS→MAC_ADDRESS | 0.0 | < 5.0 | PASS |  |
| licence_vs_id | 24 | confusion_rate AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER | 0.0 | < 5.0 | PASS | **NO** |
|  |  | confusion_rate AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER | 0.0 | < 5.0 | PASS |  |
| name_homographs | 64 | exact_recall [GIVENNAME] | 96.9 | >= 90.0 | PASS | yes |
|  |  | control_fp_rate | 25.0 | < 10.0 | FAIL |  |
| name_transliteration_variants | 80 | exact_recall | 98.8 | >= 90.0 | PASS | yes |
|  |  | wrong_label | 1 | == 0 | FAIL |  |
| names_after_role | 24 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 90.0 | PASS | yes |
|  |  | control_fp_rate | 25.0 | < 10.0 | FAIL |  |
| names_list_lines | 14 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 90.0 | PASS | yes |
|  |  | control_fp_rate | 50.0 | < 10.0 | FAIL |  |
| names_sentence_start | 26 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 90.0 | PASS | **NO** |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| names_signature | 24 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 90.0 | PASS | **NO** |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| noisy_suffixes | 36 | exact_recall [GIVENNAME,SURNAME,CITY] | 95.8 | >= 85.0 | PASS | **NO** |
|  |  | control_fp_rate | 8.3 | < 10.0 | PASS |  |
| nonpii_ids | 24 | control_fp_rate | 50.0 | <= ×0.3 ckpt1 | – | yes |
|  |  | sanity: control_fp_rate | 50.0 | >= 10.0 | PASS |  |
| pem | 20 | char_leakage_rate | 0.0 | < ×1.0 ckpt1 | – | **NO** |
|  |  | sanity: exact_recall | 100.0 | < 90.0 | FAIL |  |
| pii_free | 24 | pii_free_fp_rate | 0.0 | < 15.0 | PASS | **NO** |
| prose_card | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| prose_date | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| prose_iban | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| punct_touching | 24 | exact_recall | 100.0 | >= 90.0 | PASS | **NO** |
| sentence_initial_nouns | 24 | control_fp_rate | 0.0 | <= ×0.3 ckpt1 | – | **NO** |
|  |  | sanity: control_fp_rate | 0.0 | >= 10.0 | FAIL |  |
| single_entity | 24 | exact_f1 | 92.3 | >= 80.0 | PASS | **NO** |
| spaced_card_iban | 24 | char_leakage_rate | 0.0 | < ×1.0 ckpt1 | – | **NO** |
|  |  | sanity: exact_recall | 100.0 | < 90.0 | FAIL |  |
| spaced_phone | 24 | char_leakage_rate | 1.9 | < ×1.0 ckpt1 | – | **NO** |
|  |  | sanity: exact_recall | 91.7 | < 90.0 | FAIL |  |
| suffixed_entities | 273 | case_exact_recall_min | 61.9 | >= 85.0 | FAIL | yes |
| token_vs_key | 24 | exact_recall [ACCESS_TOKEN] | 91.7 | >= 80.0 | PASS | **NO** |
|  |  | confusion_rate ACCESS_TOKEN→API_KEY | 0.0 | < 10.0 | PASS |  |
| villages | 34 | exact_recall [CITY] | 88.5 | >= 80.0 | PASS | yes |
|  |  | control_fp_rate | 11.1 | < 10.0 | FAIL |  |

`decoy_cvv` look-alikes masked as CVV, by kind: `12345` dummies (D-2) 0/2; random 5-digit codes 1/5; dashed, policy (D-34c) 2/2; dashed, policy (D-39c) 3/3

## Probe targets (track M): 33/52 families pass; 14/52 show their failure

| Family | Docs | Condition | Measured | Target | Pass | Shows the failure |
|---|---|---|---|---|---|---|
| anchor_distance | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| bare_name | 43 | exact_recall | 100.0 | >= 90.0 | PASS | **NO** |
|  |  | split_spans | 0 | == 0 | PASS |  |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| building_vs_room | 24 | control_fp_rate | 0.0 | <= ×0.3 ckpt1 | – | **NO** |
|  |  | sanity: control_fp_rate | 0.0 | >= 10.0 | FAIL |  |
| casing_noise | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| contrast_ipv6_mac | 60 | exact_recall [IPV6_ADDRESS] | 100.0 | >= 80.0 | PASS | **NO** |
|  |  | exact_recall [MAC_ADDRESS] | 100.0 | >= 80.0 | PASS |  |
|  |  | confusion_rate IPV6_ADDRESS→MAC_ADDRESS | 0.0 | < 5.0 | PASS |  |
|  |  | confusion_rate MAC_ADDRESS→IPV6_ADDRESS | 0.0 | < 5.0 | PASS |  |
|  |  | decoy_trigger_rate | 13.6 | < 15.0 | PASS |  |
| contrast_licence_id | 26 | confusion_rate AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER | 0.0 | < 5.0 | PASS | **NO** |
|  |  | confusion_rate AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER | 0.0 | < 5.0 | PASS |  |
|  |  | exact_recall [AZ_DRIVER_LICENSE_NUMBER] | 100.0 | >= 80.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | >= 80.0 | PASS |  |
|  |  | decoy_trigger_rate | 0.0 | < 15.0 | PASS |  |
| contrast_token_key | 24 | exact_recall [ACCESS_TOKEN] | 93.8 | >= 80.0 | PASS | **NO** |
|  |  | exact_recall [API_KEY] | 100.0 | >= 80.0 | PASS |  |
|  |  | confusion_rate ACCESS_TOKEN→API_KEY | 0.0 | < 10.0 | PASS |  |
|  |  | confusion_rate API_KEY→ACCESS_TOKEN | 0.0 | < 10.0 | PASS |  |
|  |  | decoy_trigger_rate | 0.0 | < 15.0 | PASS |  |
| date_vs_timestamp | 22 | exact_recall [DATE] | 100.0 | >= 80.0 | PASS | yes |
|  |  | decoy_trigger_rate | 16.7 | < 15.0 | FAIL |  |
| decoy_age | 24 | decoy_trigger_rate | 8.3 | < 15.0 | PASS | **NO** |
| decoy_card_iccid_iban | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_cvv | 24 | decoy_trigger_rate | 14.3 | < 15.0 | PASS | **NO** |
| decoy_date | 24 | decoy_trigger_rate | 25.0 | < 15.0 | FAIL | yes |
| decoy_fin | 24 | decoy_trigger_rate | 20.0 | < 15.0 | FAIL | yes |
| decoy_ipv4 | 24 | decoy_trigger_rate | 16.7 | < 15.0 | FAIL | yes |
| decoy_ipv6_mac | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_names_as_org | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_time | 24 | decoy_trigger_rate | 50.0 | < 15.0 | FAIL | yes |
| decoy_voen_passport_id | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_zip | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| fmt_csv | 24 | exact_recall | 83.3 | >= 70.0 | PASS | yes |
|  |  | exact_recall [EMAIL] | 33.3 | > 60.0 | FAIL |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_csv_noheader | 24 | exact_recall | 95.8 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 83.3 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
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
| foreign_names | 30 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 80.0 | PASS | **NO** |
|  |  | decoy_trigger_rate_any | 0.0 | < 15.0 | PASS |  |
| homograph_pairs | 16 | exact_recall [GIVENNAME] | 93.8 | >= 90.0 | PASS | yes |
|  |  | control_fp_rate | 18.8 | < 10.0 | FAIL |  |
| inflected_anchor | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| ipv6_vs_mac | 24 | exact_recall [IPV6_ADDRESS] | 100.0 | >= 80.0 | PASS | **NO** |
|  |  | confusion_rate IPV6_ADDRESS→MAC_ADDRESS | 0.0 | < 5.0 | PASS |  |
| licence_vs_id | 24 | confusion_rate AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER | 0.0 | < 5.0 | PASS | **NO** |
|  |  | confusion_rate AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER | 0.0 | < 5.0 | PASS |  |
| name_homographs | 64 | exact_recall [GIVENNAME] | 96.9 | >= 90.0 | PASS | yes |
|  |  | control_fp_rate | 25.0 | < 10.0 | FAIL |  |
| name_transliteration_variants | 80 | exact_recall | 98.8 | >= 90.0 | PASS | yes |
|  |  | wrong_label | 1 | == 0 | FAIL |  |
| names_after_role | 24 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 90.0 | PASS | yes |
|  |  | control_fp_rate | 25.0 | < 10.0 | FAIL |  |
| names_list_lines | 14 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 90.0 | PASS | yes |
|  |  | control_fp_rate | 50.0 | < 10.0 | FAIL |  |
| names_sentence_start | 26 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 90.0 | PASS | **NO** |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| names_signature | 24 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 90.0 | PASS | **NO** |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| noisy_suffixes | 36 | exact_recall [GIVENNAME,SURNAME,CITY] | 100.0 | >= 85.0 | PASS | **NO** |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| nonpii_ids | 24 | control_fp_rate | 50.0 | <= ×0.3 ckpt1 | – | yes |
|  |  | sanity: control_fp_rate | 50.0 | >= 10.0 | PASS |  |
| pem | 20 | char_leakage_rate | 0.0 | < ×1.0 ckpt1 | – | **NO** |
|  |  | sanity: exact_recall | 100.0 | < 90.0 | FAIL |  |
| pii_free | 24 | pii_free_fp_rate | 0.0 | < 15.0 | PASS | **NO** |
| prose_card | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| prose_date | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| prose_iban | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| punct_touching | 24 | exact_recall | 100.0 | >= 90.0 | PASS | **NO** |
| sentence_initial_nouns | 24 | control_fp_rate | 0.0 | <= ×0.3 ckpt1 | – | **NO** |
|  |  | sanity: control_fp_rate | 0.0 | >= 10.0 | FAIL |  |
| single_entity | 24 | exact_f1 | 92.3 | >= 80.0 | PASS | **NO** |
| spaced_card_iban | 24 | char_leakage_rate | 0.0 | < ×1.0 ckpt1 | – | **NO** |
|  |  | sanity: exact_recall | 100.0 | < 90.0 | FAIL |  |
| spaced_phone | 24 | char_leakage_rate | 1.9 | < ×1.0 ckpt1 | – | **NO** |
|  |  | sanity: exact_recall | 91.7 | < 90.0 | FAIL |  |
| suffixed_entities | 273 | case_exact_recall_min | 66.7 | >= 85.0 | FAIL | yes |
| token_vs_key | 24 | exact_recall [ACCESS_TOKEN] | 91.7 | >= 80.0 | PASS | **NO** |
|  |  | confusion_rate ACCESS_TOKEN→API_KEY | 0.0 | < 10.0 | PASS |  |
| villages | 34 | exact_recall [CITY] | 88.5 | >= 80.0 | PASS | yes |
|  |  | control_fp_rate | 11.1 | < 10.0 | FAIL |  |

`decoy_cvv` look-alikes masked as CVV, by kind: `12345` dummies (D-2) 0/2; random 5-digit codes 1/5; dashed, policy (D-34c) 2/2; dashed, policy (D-39c) 3/3

### Slices: probes (exact recall / overlap recall / split spans)

| Slice | Value | Gold | R | M |
|---|---|---|---|---|
| entity:case | abl | 21 | 61.9 / 81.0 / 4 | 81.0 / 81.0 / 0 |
| entity:case | acc_consonant | 21 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:case | acc_vowel | 21 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:case | apostrophe | 21 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:case | ascii_folded | 21 | 66.7 / 66.7 / 0 | 66.7 / 66.7 / 0 |
| entity:case | cop | 21 | 81.0 / 81.0 / 0 | 81.0 / 81.0 / 0 |
| entity:case | dat | 21 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:case | gen | 33 | 75.8 / 75.8 / 0 | 75.8 / 75.8 / 0 |
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
| entity:noise | buffer | 6 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:noise | colloquial | 6 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:noise | double | 6 | 83.3 / 100.0 / 1 | 100.0 / 100.0 / 0 |
| entity:noise | harmony | 6 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:origin | en_eu | 10 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:origin | fa_ar | 8 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:origin | ka | 6 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:origin | ru | 10 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:origin | tr | 6 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:role | given | 57 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:role | patronymic | 57 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:sep | colon | 8 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:sep | dot | 7 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:sep | hyphen | 7 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:variant | ascii_or_ru_latin | 16 | 93.8 / 93.8 / 0 | 93.8 / 93.8 / 0 |
| entity:variant | az_latin | 16 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:variant | cyrillic | 16 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:variant | en_latin | 16 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:variant | tr_or_other | 16 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:control | True | 0 | – / – / 0 | – / – / 0 |
| doc:lang | az | 1644 | 96.6 / 97.9 / 22 | 97.1 / 97.9 / 13 |
| doc:resembles | GIVENNAME | 0 | – / – / 0 | – / – / 0 |
| doc:same_body | False | 8 | 87.5 / 100.0 / 1 | 87.5 / 100.0 / 1 |
| doc:same_body | True | 16 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:density | 0 | 0 | – / – / 0 | – / – / 0 |
| doc:density | 1 | 1019 | 96.0 / 96.7 / 7 | 96.5 / 96.7 / 2 |
| doc:density | 2-3 | 454 | 96.7 / 100.0 / 15 | 97.6 / 100.0 / 11 |
| doc:density | 7+ | 171 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| control:kind | common_noun | 6 spans | FP 0.0 | FP 0.0 |
| control:kind | common_word | 4 spans | FP 0.0 | FP 0.0 |
| control:kind | department_signature | 4 spans | FP 0.0 | FP 0.0 |
| control:kind | generic_place | 5 spans | FP 20.0 | FP 20.0 |
| control:kind | homograph_word | 48 spans | FP 22.9 | FP 22.9 |
| control:kind | noisy_suffix_noun | 12 spans | FP 8.3 | FP 0.0 |
| … | 18 more rows in the JSON | | |

Calibration (score bins vs precision) is in the JSON. It is reported only and is never used to set a threshold (A2.2).
