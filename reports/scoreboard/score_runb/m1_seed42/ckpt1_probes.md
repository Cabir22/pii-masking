# Scoreboard: ckpt1_probes

| | |
|---|---|
| Model | `your-hf-org/masking-multilingual` |
| Revision SHA | `3a0a6e5df228bdc89dd01312a728e10a78b3e3fb` |
| Requested revision | `3a0a6e5df228bdc89dd01312a728e10a78b3e3fb` |
| Code git SHA | `a8fa3adb367a97d76418451b00ad59dbe03f928f` (eval/ or model/ dirty) |
| Date (UTC) | 2026-10-24T00:44:48Z |
| Device | cuda |
| Libraries | tokenizers 0.22.2, transformers 4.57.6, torch 2.11.0+cu128, python 3.12.14 |
| Tracks | R = raw HF pipeline (simple), M = model-only product path |
| Data version | probes `684455a3e6065565` |

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
| probes | R | 1680 | 51.0 / 62.5 / 56.2 | 56.0 | 73.1 | 19.7 | 95.3 | 179 | 50.7 (68.2) | 0.0 rec, 39.8 span | 52.5 | 52.6 |
| probes excl. policy | R | 1680 | 52.2 / 62.5 / 56.9 | 57.9 | 74.0 | 19.7 | 95.3 | 179 | 48.8 (67.7) | 0.0 rec, 39.8 span | 42.5 | 55.2 |
| probes | M | 1680 | 64.3 / 67.6 / 65.9 | 64.5 | 72.6 | 18.2 | 100.0 | 77 | 39.3 (58.6) | 0.0 rec, 39.0 span | 41.8 | 58.3 |
| probes excl. policy | M | 1680 | 65.6 / 67.6 / 66.5 | 66.1 | 73.3 | 18.2 | 100.0 | 77 | 37.9 (59.7) | 0.0 rec, 39.0 span | 34.2 | 60.3 |

## Probe targets (track R): 3/53 families pass; 50/53 show their failure

| Family | Docs | Condition | Measured | Target | Pass | Shows the failure |
|---|---|---|---|---|---|---|
| anchor_distance | 24 | exact_recall | 33.3 | >= 80.0 | FAIL | yes |
| bare_name | 43 | exact_recall | 33.3 | >= 90.0 | FAIL | yes |
|  |  | split_spans | 4 | == 0 | FAIL |  |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| building_vs_room | 24 | control_fp_rate | 100.0 | <= ×0.3 ckpt1 | – | yes |
|  |  | sanity: control_fp_rate | 100.0 | >= 10.0 | PASS |  |
| casing_noise | 24 | exact_recall | 37.5 | >= 80.0 | FAIL | yes |
| contrast_ipv6_mac | 60 | exact_recall [IPV6_ADDRESS] | 53.8 | >= 80.0 | FAIL | yes |
|  |  | exact_recall [MAC_ADDRESS] | 63.6 | >= 80.0 | FAIL |  |
|  |  | confusion_rate IPV6_ADDRESS→MAC_ADDRESS | 15.4 | < 5.0 | FAIL |  |
|  |  | confusion_rate MAC_ADDRESS→IPV6_ADDRESS | 0.0 | < 5.0 | PASS |  |
|  |  | decoy_trigger_rate | 9.1 | < 15.0 | PASS |  |
| contrast_licence_id | 26 | confusion_rate AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER | 58.3 | < 5.0 | FAIL | yes |
|  |  | confusion_rate AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER | 0.0 | < 5.0 | PASS |  |
|  |  | exact_recall [AZ_DRIVER_LICENSE_NUMBER] | 33.3 | >= 80.0 | FAIL |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 91.7 | >= 80.0 | PASS |  |
|  |  | decoy_trigger_rate | 40.0 | < 15.0 | FAIL |  |
| contrast_token_key | 24 | exact_recall [ACCESS_TOKEN] | 25.0 | >= 80.0 | FAIL | yes |
|  |  | exact_recall [API_KEY] | 100.0 | >= 80.0 | PASS |  |
|  |  | confusion_rate ACCESS_TOKEN→API_KEY | 62.5 | < 10.0 | FAIL |  |
|  |  | confusion_rate API_KEY→ACCESS_TOKEN | 0.0 | < 10.0 | PASS |  |
|  |  | decoy_trigger_rate | 0.0 | < 15.0 | PASS |  |
| date_vs_timestamp | 22 | exact_recall [DATE] | 93.8 | >= 80.0 | PASS | yes |
|  |  | decoy_trigger_rate | 22.2 | < 15.0 | FAIL |  |
| decoy_age | 24 | decoy_trigger_rate | 100.0 | < 15.0 | FAIL | yes |
| decoy_card_iccid_iban | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_cvv | 24 | decoy_trigger_rate | 100.0 | < 15.0 | FAIL | yes |
| decoy_date | 24 | decoy_trigger_rate | 100.0 | < 15.0 | FAIL | yes |
| decoy_fin | 24 | decoy_trigger_rate | 100.0 | < 15.0 | FAIL | yes |
| decoy_ipv4 | 24 | decoy_trigger_rate | 41.7 | < 15.0 | FAIL | yes |
| decoy_ipv6_mac | 24 | decoy_trigger_rate | 50.0 | < 15.0 | FAIL | yes |
| decoy_names_as_org | 24 | decoy_trigger_rate | 100.0 | < 15.0 | FAIL | yes |
| decoy_time | 24 | decoy_trigger_rate | 100.0 | < 15.0 | FAIL | yes |
| decoy_voen_passport_id | 24 | decoy_trigger_rate | 33.3 | < 15.0 | FAIL | yes |
| decoy_zip | 24 | decoy_trigger_rate | 100.0 | < 15.0 | FAIL | yes |
| fmt_csv | 24 | exact_recall | 75.0 | >= 70.0 | PASS | yes |
|  |  | exact_recall [EMAIL] | 0.0 | > 60.0 | FAIL |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_csv_noheader | 24 | exact_recall | 50.0 | >= 70.0 | FAIL | yes |
|  |  | exact_recall [EMAIL] | 0.0 | > 60.0 | FAIL |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 75.0 | > 60.0 | PASS |  |
| fmt_dialogue | 24 | exact_recall | 75.0 | >= 70.0 | PASS | yes |
|  |  | exact_recall [EMAIL] | 58.3 | > 60.0 | FAIL |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_json | 24 | exact_recall | 75.0 | >= 70.0 | PASS | yes |
|  |  | exact_recall [EMAIL] | 41.7 | > 60.0 | FAIL |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_kv | 24 | exact_recall | 77.1 | >= 70.0 | PASS | yes |
|  |  | exact_recall [EMAIL] | 25.0 | > 60.0 | FAIL |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_log | 24 | exact_recall | 54.2 | >= 70.0 | FAIL | yes |
|  |  | exact_recall [EMAIL] | 0.0 | > 60.0 | FAIL |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_pipe | 24 | exact_recall | 81.2 | >= 70.0 | PASS | yes |
|  |  | exact_recall [EMAIL] | 25.0 | > 60.0 | FAIL |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| foreign_names | 30 | exact_recall [GIVENNAME,SURNAME] | 65.0 | >= 80.0 | FAIL | yes |
|  |  | decoy_trigger_rate_any | 0.0 | < 15.0 | PASS |  |
| homograph_pairs | 16 | exact_recall [GIVENNAME] | 68.8 | >= 90.0 | FAIL | yes |
|  |  | control_fp_rate | 43.8 | < 10.0 | FAIL |  |
| inflected_anchor | 24 | exact_recall | 66.7 | >= 80.0 | FAIL | yes |
| ipv6_vs_mac | 24 | exact_recall [IPV6_ADDRESS] | 83.3 | >= 80.0 | PASS | yes |
|  |  | confusion_rate IPV6_ADDRESS→MAC_ADDRESS | 16.7 | < 5.0 | FAIL |  |
| licence_vs_id | 24 | confusion_rate AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER | 100.0 | < 5.0 | FAIL | yes |
|  |  | confusion_rate AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER | 0.0 | < 5.0 | PASS |  |
| line_end_ip_email | 24 | exact_recall | 91.7 | >= 80.0 | PASS | **NO** |
| name_homographs | 64 | exact_recall [GIVENNAME] | 100.0 | >= 90.0 | PASS | yes |
|  |  | control_fp_rate | 53.1 | < 10.0 | FAIL |  |
| name_transliteration_variants | 80 | exact_recall | 92.5 | >= 90.0 | PASS | yes |
|  |  | wrong_label | 1 | == 0 | FAIL |  |
| names_after_role | 24 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 90.0 | PASS | yes |
|  |  | control_fp_rate | 50.0 | < 10.0 | FAIL |  |
| names_list_lines | 14 | exact_recall [GIVENNAME,SURNAME] | 24.6 | >= 90.0 | FAIL | yes |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| names_sentence_start | 26 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 90.0 | PASS | **NO** |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| names_signature | 24 | exact_recall [GIVENNAME,SURNAME] | 70.0 | >= 90.0 | FAIL | yes |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| noisy_suffixes | 36 | exact_recall [GIVENNAME,SURNAME,CITY] | 45.8 | >= 85.0 | FAIL | yes |
|  |  | control_fp_rate | 8.3 | < 10.0 | PASS |  |
| nonpii_ids | 24 | control_fp_rate | 58.3 | <= ×0.3 ckpt1 | – | yes |
|  |  | sanity: control_fp_rate | 58.3 | >= 10.0 | PASS |  |
| pem | 20 | char_leakage_rate | 14.9 | < ×1.0 ckpt1 | – | yes |
|  |  | sanity: exact_recall | 0.0 | < 90.0 | PASS |  |
| pii_free | 24 | pii_free_fp_rate | 15.0 | < 15.0 | FAIL | yes |
| prose_card | 24 | exact_recall | 16.7 | >= 80.0 | FAIL | yes |
| prose_date | 24 | exact_recall | 16.7 | >= 80.0 | FAIL | yes |
| prose_iban | 24 | exact_recall | 0.0 | >= 80.0 | FAIL | yes |
| punct_touching | 24 | exact_recall | 66.7 | >= 90.0 | FAIL | yes |
| sentence_initial_nouns | 24 | control_fp_rate | 16.7 | <= ×0.3 ckpt1 | – | yes |
|  |  | sanity: control_fp_rate | 16.7 | >= 10.0 | PASS |  |
| single_entity | 24 | exact_f1 | 64.0 | >= 80.0 | FAIL | yes |
| spaced_card_iban | 24 | char_leakage_rate | 35.8 | < ×1.0 ckpt1 | – | yes |
|  |  | sanity: exact_recall | 58.3 | < 90.0 | PASS |  |
| spaced_phone | 24 | char_leakage_rate | 57.9 | < ×1.0 ckpt1 | – | yes |
|  |  | sanity: exact_recall | 41.7 | < 90.0 | PASS |  |
| suffixed_entities | 273 | case_exact_recall_min | 0.0 | >= 85.0 | FAIL | yes |
| token_vs_key | 24 | exact_recall [ACCESS_TOKEN] | 25.0 | >= 80.0 | FAIL | yes |
|  |  | confusion_rate ACCESS_TOKEN→API_KEY | 75.0 | < 10.0 | FAIL |  |
| villages | 34 | exact_recall [CITY] | 57.7 | >= 80.0 | FAIL | yes |
|  |  | control_fp_rate | 11.1 | < 10.0 | FAIL |  |

`decoy_cvv` look-alikes masked as CVV, by kind: `12345` dummies (D-2) 2/2; random 5-digit codes 5/5; dashed, policy (D-34c) 2/2; dashed, policy (D-39c) 3/3

## Probe targets (track M): 10/53 families pass; 43/53 show their failure

| Family | Docs | Condition | Measured | Target | Pass | Shows the failure |
|---|---|---|---|---|---|---|
| anchor_distance | 24 | exact_recall | 41.7 | >= 80.0 | FAIL | yes |
| bare_name | 43 | exact_recall | 33.3 | >= 90.0 | FAIL | yes |
|  |  | split_spans | 1 | == 0 | FAIL |  |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| building_vs_room | 24 | control_fp_rate | 100.0 | <= ×0.3 ckpt1 | – | yes |
|  |  | sanity: control_fp_rate | 100.0 | >= 10.0 | PASS |  |
| casing_noise | 24 | exact_recall | 37.5 | >= 80.0 | FAIL | yes |
| contrast_ipv6_mac | 60 | exact_recall [IPV6_ADDRESS] | 61.5 | >= 80.0 | FAIL | yes |
|  |  | exact_recall [MAC_ADDRESS] | 72.7 | >= 80.0 | FAIL |  |
|  |  | confusion_rate IPV6_ADDRESS→MAC_ADDRESS | 15.4 | < 5.0 | FAIL |  |
|  |  | confusion_rate MAC_ADDRESS→IPV6_ADDRESS | 0.0 | < 5.0 | PASS |  |
|  |  | decoy_trigger_rate | 9.1 | < 15.0 | PASS |  |
| contrast_licence_id | 26 | confusion_rate AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER | 58.3 | < 5.0 | FAIL | yes |
|  |  | confusion_rate AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER | 0.0 | < 5.0 | PASS |  |
|  |  | exact_recall [AZ_DRIVER_LICENSE_NUMBER] | 41.7 | >= 80.0 | FAIL |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | >= 80.0 | PASS |  |
|  |  | decoy_trigger_rate | 40.0 | < 15.0 | FAIL |  |
| contrast_token_key | 24 | exact_recall [ACCESS_TOKEN] | 25.0 | >= 80.0 | FAIL | yes |
|  |  | exact_recall [API_KEY] | 100.0 | >= 80.0 | PASS |  |
|  |  | confusion_rate ACCESS_TOKEN→API_KEY | 62.5 | < 10.0 | FAIL |  |
|  |  | confusion_rate API_KEY→ACCESS_TOKEN | 0.0 | < 10.0 | PASS |  |
|  |  | decoy_trigger_rate | 0.0 | < 15.0 | PASS |  |
| date_vs_timestamp | 22 | exact_recall [DATE] | 100.0 | >= 80.0 | PASS | yes |
|  |  | decoy_trigger_rate | 16.7 | < 15.0 | FAIL |  |
| decoy_age | 24 | decoy_trigger_rate | 83.3 | < 15.0 | FAIL | yes |
| decoy_card_iccid_iban | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_cvv | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_date | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_fin | 24 | decoy_trigger_rate | 80.0 | < 15.0 | FAIL | yes |
| decoy_ipv4 | 24 | decoy_trigger_rate | 33.3 | < 15.0 | FAIL | yes |
| decoy_ipv6_mac | 24 | decoy_trigger_rate | 50.0 | < 15.0 | FAIL | yes |
| decoy_names_as_org | 24 | decoy_trigger_rate | 100.0 | < 15.0 | FAIL | yes |
| decoy_time | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_voen_passport_id | 24 | decoy_trigger_rate | 33.3 | < 15.0 | FAIL | yes |
| decoy_zip | 24 | decoy_trigger_rate | 100.0 | < 15.0 | FAIL | yes |
| fmt_csv | 24 | exact_recall | 75.0 | >= 70.0 | PASS | yes |
|  |  | exact_recall [EMAIL] | 0.0 | > 60.0 | FAIL |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_csv_noheader | 24 | exact_recall | 75.0 | >= 70.0 | PASS | yes |
|  |  | exact_recall [EMAIL] | 0.0 | > 60.0 | FAIL |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_dialogue | 24 | exact_recall | 75.0 | >= 70.0 | PASS | yes |
|  |  | exact_recall [EMAIL] | 58.3 | > 60.0 | FAIL |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_json | 24 | exact_recall | 100.0 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 100.0 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_kv | 24 | exact_recall | 87.5 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 66.7 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_log | 24 | exact_recall | 75.0 | >= 70.0 | PASS | yes |
|  |  | exact_recall [EMAIL] | 0.0 | > 60.0 | FAIL |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_pipe | 24 | exact_recall | 81.2 | >= 70.0 | PASS | yes |
|  |  | exact_recall [EMAIL] | 25.0 | > 60.0 | FAIL |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| foreign_names | 30 | exact_recall [GIVENNAME,SURNAME] | 70.0 | >= 80.0 | FAIL | yes |
|  |  | decoy_trigger_rate_any | 0.0 | < 15.0 | PASS |  |
| homograph_pairs | 16 | exact_recall [GIVENNAME] | 68.8 | >= 90.0 | FAIL | yes |
|  |  | control_fp_rate | 37.5 | < 10.0 | FAIL |  |
| inflected_anchor | 24 | exact_recall | 75.0 | >= 80.0 | FAIL | yes |
| ipv6_vs_mac | 24 | exact_recall [IPV6_ADDRESS] | 83.3 | >= 80.0 | PASS | yes |
|  |  | confusion_rate IPV6_ADDRESS→MAC_ADDRESS | 16.7 | < 5.0 | FAIL |  |
| licence_vs_id | 24 | confusion_rate AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER | 100.0 | < 5.0 | FAIL | yes |
|  |  | confusion_rate AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER | 0.0 | < 5.0 | PASS |  |
| line_end_ip_email | 24 | exact_recall | 91.7 | >= 80.0 | PASS | **NO** |
| name_homographs | 64 | exact_recall [GIVENNAME] | 100.0 | >= 90.0 | PASS | yes |
|  |  | control_fp_rate | 53.1 | < 10.0 | FAIL |  |
| name_transliteration_variants | 80 | exact_recall | 96.2 | >= 90.0 | PASS | yes |
|  |  | wrong_label | 1 | == 0 | FAIL |  |
| names_after_role | 24 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 90.0 | PASS | yes |
|  |  | control_fp_rate | 50.0 | < 10.0 | FAIL |  |
| names_list_lines | 14 | exact_recall [GIVENNAME,SURNAME] | 28.7 | >= 90.0 | FAIL | yes |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| names_sentence_start | 26 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 90.0 | PASS | **NO** |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| names_signature | 24 | exact_recall [GIVENNAME,SURNAME] | 72.5 | >= 90.0 | FAIL | yes |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| noisy_suffixes | 36 | exact_recall [GIVENNAME,SURNAME,CITY] | 50.0 | >= 85.0 | FAIL | yes |
|  |  | control_fp_rate | 8.3 | < 10.0 | PASS |  |
| nonpii_ids | 24 | control_fp_rate | 58.3 | <= ×0.3 ckpt1 | – | yes |
|  |  | sanity: control_fp_rate | 58.3 | >= 10.0 | PASS |  |
| pem | 20 | char_leakage_rate | 12.6 | < ×1.0 ckpt1 | – | yes |
|  |  | sanity: exact_recall | 0.0 | < 90.0 | PASS |  |
| pii_free | 24 | pii_free_fp_rate | 5.0 | < 15.0 | PASS | **NO** |
| prose_card | 24 | exact_recall | 25.0 | >= 80.0 | FAIL | yes |
| prose_date | 24 | exact_recall | 16.7 | >= 80.0 | FAIL | yes |
| prose_iban | 24 | exact_recall | 0.0 | >= 80.0 | FAIL | yes |
| punct_touching | 24 | exact_recall | 100.0 | >= 90.0 | PASS | **NO** |
| sentence_initial_nouns | 24 | control_fp_rate | 16.7 | <= ×0.3 ckpt1 | – | yes |
|  |  | sanity: control_fp_rate | 16.7 | >= 10.0 | PASS |  |
| single_entity | 24 | exact_f1 | 66.7 | >= 80.0 | FAIL | yes |
| spaced_card_iban | 24 | char_leakage_rate | 35.2 | < ×1.0 ckpt1 | – | yes |
|  |  | sanity: exact_recall | 58.3 | < 90.0 | PASS |  |
| spaced_phone | 24 | char_leakage_rate | 57.2 | < ×1.0 ckpt1 | – | yes |
|  |  | sanity: exact_recall | 41.7 | < 90.0 | PASS |  |
| suffixed_entities | 273 | case_exact_recall_min | 0.0 | >= 85.0 | FAIL | yes |
| token_vs_key | 24 | exact_recall [ACCESS_TOKEN] | 25.0 | >= 80.0 | FAIL | yes |
|  |  | confusion_rate ACCESS_TOKEN→API_KEY | 75.0 | < 10.0 | FAIL |  |
| villages | 34 | exact_recall [CITY] | 61.5 | >= 80.0 | FAIL | yes |
|  |  | control_fp_rate | 11.1 | < 10.0 | FAIL |  |

`decoy_cvv` look-alikes masked as CVV, by kind: `12345` dummies (D-2) 0/2; random 5-digit codes 0/5; dashed, policy (D-34c) 2/2; dashed, policy (D-39c) 1/3

### Slices: probes (exact recall / overlap recall / split spans)

| Slice | Value | Gold | R | M |
|---|---|---|---|---|
| entity:case | abl | 21 | 52.4 / 52.4 / 0 | 52.4 / 52.4 / 0 |
| entity:case | acc_consonant | 21 | 47.6 / 66.7 / 4 | 47.6 / 47.6 / 0 |
| entity:case | acc_vowel | 21 | 66.7 / 85.7 / 4 | 66.7 / 66.7 / 0 |
| entity:case | apostrophe | 21 | 0.0 / 52.4 / 11 | 0.0 / 33.3 / 7 |
| entity:case | ascii_folded | 21 | 47.6 / 66.7 / 4 | 47.6 / 47.6 / 0 |
| entity:case | cop | 21 | 33.3 / 47.6 / 3 | 47.6 / 47.6 / 0 |
| entity:case | dat | 21 | 81.0 / 100.0 / 4 | 81.0 / 81.0 / 0 |
| entity:case | gen | 33 | 87.9 / 87.9 / 0 | 87.9 / 87.9 / 0 |
| entity:case | ins | 21 | 0.0 / 0.0 / 0 | 0.0 / 0.0 / 0 |
| entity:case | loc | 21 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:case | pl | 21 | 85.7 / 100.0 / 3 | 100.0 / 100.0 / 0 |
| entity:case | pl_case | 21 | 33.3 / 81.0 / 10 | 61.9 / 61.9 / 0 |
| entity:case | rel | 21 | 0.0 / 0.0 / 0 | 0.0 / 0.0 / 0 |
| entity:entity_noise | case_or_ascii | 12 | 0.0 / 0.0 / 0 | 0.0 / 0.0 / 0 |
| entity:form | dmy_dot | 4 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:form | dmy_dot_short | 3 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:form | dmy_slash | 3 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:form | end | 4 | 25.0 / 75.0 / 2 | 25.0 / 75.0 / 2 |
| entity:form | full | 2 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:form | iso | 3 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:form | link_local | 4 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:form | mapped | 4 | 0.0 / 0.0 / 0 | 0.0 / 0.0 / 0 |
| entity:form | mid | 6 | 83.3 / 100.0 / 1 | 100.0 / 100.0 / 0 |
| entity:form | prefix_one | 4 | 25.0 / 25.0 / 0 | 50.0 / 50.0 / 0 |
| entity:form | upper | 2 | 50.0 / 50.0 / 0 | 50.0 / 50.0 / 0 |
| entity:form | worded | 3 | 66.7 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:noise | buffer | 6 | 66.7 / 83.3 / 1 | 66.7 / 66.7 / 0 |
| entity:noise | colloquial | 6 | 33.3 / 33.3 / 0 | 33.3 / 33.3 / 0 |
| entity:noise | double | 6 | 16.7 / 66.7 / 3 | 16.7 / 16.7 / 0 |
| entity:noise | harmony | 6 | 66.7 / 83.3 / 1 | 83.3 / 83.3 / 0 |
| entity:origin | en_eu | 10 | 70.0 / 70.0 / 0 | 70.0 / 70.0 / 0 |
| entity:origin | fa_ar | 8 | 75.0 / 75.0 / 0 | 75.0 / 75.0 / 0 |
| entity:origin | ka | 6 | 50.0 / 66.7 / 1 | 50.0 / 50.0 / 0 |
| entity:origin | ru | 10 | 60.0 / 90.0 / 3 | 80.0 / 80.0 / 0 |
| entity:origin | tr | 6 | 66.7 / 83.3 / 1 | 66.7 / 66.7 / 0 |
| entity:role | given | 57 | 24.6 / 29.8 / 3 | 26.3 / 26.3 / 0 |
| entity:role | patronymic | 57 | 5.3 / 7.0 / 1 | 5.3 / 5.3 / 0 |
| entity:sep | colon | 8 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:sep | dot | 7 | 14.3 / 14.3 / 0 | 14.3 / 14.3 / 0 |
| entity:sep | hyphen | 7 | 71.4 / 85.7 / 0 | 100.0 / 100.0 / 0 |
| entity:variant | ascii_or_ru_latin | 16 | 93.8 / 100.0 / 1 | 100.0 / 100.0 / 0 |
| entity:variant | az_latin | 16 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:variant | cyrillic | 16 | 93.8 / 100.0 / 1 | 100.0 / 100.0 / 0 |
| entity:variant | en_latin | 16 | 87.5 / 93.8 / 1 | 93.8 / 93.8 / 0 |
| entity:variant | tr_or_other | 16 | 87.5 / 87.5 / 0 | 87.5 / 87.5 / 0 |
| doc:control | True | 0 | – / – / 0 | – / – / 0 |
| doc:lang | az | 1668 | 62.5 / 74.5 / 179 | 67.6 / 72.2 / 77 |
| doc:resembles | GIVENNAME | 0 | – / – / 0 | – / – / 0 |
| doc:same_body | False | 8 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:same_body | True | 16 | 50.0 / 50.0 / 0 | 50.0 / 50.0 / 0 |
| doc:density | 0 | 0 | – / – / 0 | – / – / 0 |
| doc:density | 1 | 1043 | 67.1 / 76.6 / 87 | 70.9 / 73.6 / 28 |
| doc:density | 2-3 | 454 | 66.3 / 85.9 / 81 | 74.4 / 85.2 / 49 |
| doc:density | 7+ | 171 | 24.6 / 31.0 / 11 | 28.7 / 28.7 / 0 |
| control:kind | common_noun | 6 spans | FP 0.0 | FP 0.0 |
| control:kind | common_word | 4 spans | FP 25.0 | FP 25.0 |
| control:kind | department_signature | 4 spans | FP 0.0 | FP 0.0 |
| control:kind | generic_place | 5 spans | FP 0.0 | FP 0.0 |
| control:kind | homograph_word | 48 spans | FP 50.0 | FP 47.9 |
| control:kind | noisy_suffix_noun | 12 spans | FP 8.3 | FP 8.3 |
| … | 18 more rows in the JSON | | |

Calibration (score bins vs precision) is in the JSON. It is reported only and is never used to set a threshold (A2.2).
