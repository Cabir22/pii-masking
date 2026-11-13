# Scoreboard: probes_runb_v2

| | |
|---|---|
| Model | `your-hf-org/masking-az-runb-v2-seed42-2ep` |
| Revision SHA | `937f29d008f9f99d498e7686aa5e5dddf11ace14` |
| Requested revision | `937f29d008f9f99d498e7686aa5e5dddf11ace14` |
| Code git SHA | `1498e271c1352a8c94b22b4278ed743b2ce0dc4f` |
| Date (UTC) | 2026-10-10T09:23:04Z |
| Device | cpu |
| Tracks | R = raw HF pipeline (simple), M = model-only product path |
| Data version | probes `2e62c579ed7b3d88` |

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
| probes | R | 1568 | 70.6 / 87.2 / 78.0 | 75.3 | 87.3 | 20.5 | 85.9 | 86 | 35.8 (36.7) | 0.0 rec, 15.2 span | 29.5 | 76.1 |
| probes excl. policy | R | 1568 | 70.9 / 87.2 / 78.2 | 75.6 | 87.5 | 20.5 | 85.9 | 86 | 36.3 (37.3) | 0.0 rec, 15.2 span | 28.3 | 76.5 |
| probes | M | 1568 | 79.1 / 92.3 / 85.2 | 82.4 | 88.7 | 23.1 | 96.8 | 37 | 34.6 (35.6) | 0.0 rec, 13.3 span | 27.6 | 80.1 |
| probes excl. policy | M | 1568 | 79.5 / 92.3 / 85.4 | 82.7 | 88.9 | 23.1 | 96.8 | 37 | 35.2 (36.1) | 0.0 rec, 13.3 span | 26.4 | 80.4 |

## Probe targets (track R): 16/48 families pass; 30/48 show their failure

| Family | Docs | Condition | Measured | Target | Pass | Shows the failure |
|---|---|---|---|---|---|---|
| anchor_distance | 24 | exact_recall | 75.0 | >= 80.0 | FAIL | yes |
| bare_name | 43 | exact_recall | 100.0 | >= 90.0 | PASS | **NO** |
|  |  | split_spans | 0 | == 0 | PASS |  |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| building_vs_room | 24 | control_fp_rate | 0.0 | <= ×0.3 ckpt1 | – | **NO** |
|  |  | sanity: control_fp_rate | 0.0 | >= 10.0 | FAIL |  |
| casing_noise | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| contrast_ipv6_mac | 60 | exact_recall [IPV6_ADDRESS] | 100.0 | >= 80.0 | PASS | **NO** |
|  |  | exact_recall [MAC_ADDRESS] | 95.5 | >= 80.0 | PASS |  |
|  |  | confusion_rate IPV6_ADDRESS→MAC_ADDRESS | 0.0 | < 5.0 | PASS |  |
|  |  | confusion_rate MAC_ADDRESS→IPV6_ADDRESS | 0.0 | < 5.0 | PASS |  |
|  |  | decoy_trigger_rate | 9.1 | < 15.0 | PASS |  |
| contrast_licence_id | 26 | confusion_rate AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER | 0.0 | < 5.0 | PASS | **NO** |
|  |  | confusion_rate AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER | 0.0 | < 5.0 | PASS |  |
|  |  | exact_recall [AZ_DRIVER_LICENSE_NUMBER] | 91.7 | >= 80.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 91.7 | >= 80.0 | PASS |  |
|  |  | decoy_trigger_rate | 10.0 | < 15.0 | PASS |  |
| contrast_token_key | 24 | exact_recall [ACCESS_TOKEN] | 87.5 | >= 80.0 | PASS | **NO** |
|  |  | exact_recall [API_KEY] | 100.0 | >= 80.0 | PASS |  |
|  |  | confusion_rate ACCESS_TOKEN→API_KEY | 0.0 | < 10.0 | PASS |  |
|  |  | confusion_rate API_KEY→ACCESS_TOKEN | 0.0 | < 10.0 | PASS |  |
|  |  | decoy_trigger_rate | 12.5 | < 15.0 | PASS |  |
| date_vs_timestamp | 22 | exact_recall [DATE] | 93.8 | >= 80.0 | PASS | yes |
|  |  | decoy_trigger_rate | 16.7 | < 15.0 | FAIL |  |
| decoy_age | 24 | decoy_trigger_rate | 41.7 | < 15.0 | FAIL | yes |
| decoy_card_iccid_iban | 24 | decoy_trigger_rate | 33.3 | < 15.0 | FAIL | yes |
| decoy_cvv | 24 | decoy_trigger_rate | 75.0 | < 15.0 | FAIL | yes |
| decoy_date | 24 | decoy_trigger_rate | 100.0 | < 15.0 | FAIL | yes |
| decoy_fin | 24 | decoy_trigger_rate | 33.3 | < 15.0 | FAIL | yes |
| decoy_ipv4 | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_ipv6_mac | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_names_as_org | 24 | decoy_trigger_rate | 16.7 | < 15.0 | FAIL | yes |
| decoy_time | 24 | decoy_trigger_rate | 41.7 | < 15.0 | FAIL | yes |
| decoy_voen_passport_id | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_zip | 24 | decoy_trigger_rate | 66.7 | < 15.0 | FAIL | yes |
| fmt_csv | 24 | exact_recall | 85.4 | >= 70.0 | PASS | yes |
|  |  | exact_recall [EMAIL] | 50.0 | > 60.0 | FAIL |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 91.7 | > 60.0 | PASS |  |
| fmt_csv_noheader | 24 | exact_recall | 56.2 | >= 70.0 | FAIL | yes |
|  |  | exact_recall [EMAIL] | 41.7 | > 60.0 | FAIL |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 58.3 | > 60.0 | FAIL |  |
| fmt_dialogue | 24 | exact_recall | 100.0 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 100.0 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_json | 24 | exact_recall | 83.3 | >= 70.0 | PASS | yes |
|  |  | exact_recall [EMAIL] | 33.3 | > 60.0 | FAIL |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_kv | 24 | exact_recall | 75.0 | >= 70.0 | PASS | yes |
|  |  | exact_recall [EMAIL] | 41.7 | > 60.0 | FAIL |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_log | 24 | exact_recall | 62.5 | >= 70.0 | FAIL | yes |
|  |  | exact_recall [EMAIL] | 33.3 | > 60.0 | FAIL |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_pipe | 24 | exact_recall | 100.0 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 100.0 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| foreign_names | 30 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 80.0 | PASS | yes |
|  |  | decoy_trigger_rate_any | 20.0 | < 15.0 | FAIL |  |
| homograph_pairs | 16 | exact_recall [GIVENNAME] | 87.5 | >= 90.0 | FAIL | yes |
|  |  | control_fp_rate | 12.5 | < 10.0 | FAIL |  |
| inflected_anchor | 24 | exact_recall | 75.0 | >= 80.0 | FAIL | yes |
| ipv6_vs_mac | 24 | exact_recall [IPV6_ADDRESS] | 100.0 | >= 80.0 | PASS | **NO** |
|  |  | confusion_rate IPV6_ADDRESS→MAC_ADDRESS | 0.0 | < 5.0 | PASS |  |
| licence_vs_id | 24 | confusion_rate AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER | 16.7 | < 5.0 | FAIL | yes |
|  |  | confusion_rate AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER | 8.3 | < 5.0 | FAIL |  |
| name_homographs | 64 | exact_recall [GIVENNAME] | 100.0 | >= 90.0 | PASS | yes |
|  |  | control_fp_rate | 15.6 | < 10.0 | FAIL |  |
| name_transliteration_variants | 80 | exact_recall | 100.0 | >= 90.0 | PASS | **NO** |
|  |  | wrong_label | 0 | == 0 | PASS |  |
| noisy_suffixes | 36 | exact_recall [GIVENNAME,SURNAME,CITY] | 100.0 | >= 85.0 | PASS | **NO** |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| nonpii_ids | 24 | control_fp_rate | 50.0 | <= ×0.3 ckpt1 | – | yes |
|  |  | sanity: control_fp_rate | 50.0 | >= 10.0 | PASS |  |
| pem | 20 | char_leakage_rate | 37.4 | < ×1.0 ckpt1 | – | yes |
|  |  | sanity: exact_recall | 0.0 | < 90.0 | PASS |  |
| pii_free | 24 | pii_free_fp_rate | 8.3 | < 15.0 | PASS | **NO** |
| prose_card | 24 | exact_recall | 41.7 | >= 80.0 | FAIL | yes |
| prose_date | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| prose_iban | 24 | exact_recall | 8.3 | >= 80.0 | FAIL | yes |
| punct_touching | 24 | exact_recall | 58.3 | >= 90.0 | FAIL | yes |
| sentence_initial_nouns | 24 | control_fp_rate | 0.0 | <= ×0.3 ckpt1 | – | **NO** |
|  |  | sanity: control_fp_rate | 0.0 | >= 10.0 | FAIL |  |
| single_entity | 24 | exact_f1 | 46.2 | >= 80.0 | FAIL | yes |
| spaced_card_iban | 24 | char_leakage_rate | 20.8 | < ×1.0 ckpt1 | – | yes |
|  |  | sanity: exact_recall | 66.7 | < 90.0 | PASS |  |
| spaced_phone | 24 | char_leakage_rate | 21.4 | < ×1.0 ckpt1 | – | yes |
|  |  | sanity: exact_recall | 66.7 | < 90.0 | PASS |  |
| suffixed_entities | 273 | case_exact_recall_min | 66.7 | >= 85.0 | FAIL | yes |
| token_vs_key | 24 | exact_recall [ACCESS_TOKEN] | 91.7 | >= 80.0 | PASS | **NO** |
|  |  | confusion_rate ACCESS_TOKEN→API_KEY | 0.0 | < 10.0 | PASS |  |
| villages | 34 | exact_recall [CITY] | 84.6 | >= 80.0 | PASS | yes |
|  |  | control_fp_rate | 33.3 | < 10.0 | FAIL |  |

## Probe targets (track M): 24/48 families pass; 22/48 show their failure

| Family | Docs | Condition | Measured | Target | Pass | Shows the failure |
|---|---|---|---|---|---|---|
| anchor_distance | 24 | exact_recall | 83.3 | >= 80.0 | PASS | **NO** |
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
|  |  | decoy_trigger_rate | 9.1 | < 15.0 | PASS |  |
| contrast_licence_id | 26 | confusion_rate AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER | 0.0 | < 5.0 | PASS | **NO** |
|  |  | confusion_rate AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER | 0.0 | < 5.0 | PASS |  |
|  |  | exact_recall [AZ_DRIVER_LICENSE_NUMBER] | 100.0 | >= 80.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | >= 80.0 | PASS |  |
|  |  | decoy_trigger_rate | 10.0 | < 15.0 | PASS |  |
| contrast_token_key | 24 | exact_recall [ACCESS_TOKEN] | 93.8 | >= 80.0 | PASS | **NO** |
|  |  | exact_recall [API_KEY] | 100.0 | >= 80.0 | PASS |  |
|  |  | confusion_rate ACCESS_TOKEN→API_KEY | 0.0 | < 10.0 | PASS |  |
|  |  | confusion_rate API_KEY→ACCESS_TOKEN | 0.0 | < 10.0 | PASS |  |
|  |  | decoy_trigger_rate | 12.5 | < 15.0 | PASS |  |
| date_vs_timestamp | 22 | exact_recall [DATE] | 100.0 | >= 80.0 | PASS | yes |
|  |  | decoy_trigger_rate | 16.7 | < 15.0 | FAIL |  |
| decoy_age | 24 | decoy_trigger_rate | 8.3 | < 15.0 | PASS | **NO** |
| decoy_card_iccid_iban | 24 | decoy_trigger_rate | 33.3 | < 15.0 | FAIL | yes |
| decoy_cvv | 24 | decoy_trigger_rate | 58.3 | < 15.0 | FAIL | yes |
| decoy_date | 24 | decoy_trigger_rate | 100.0 | < 15.0 | FAIL | yes |
| decoy_fin | 24 | decoy_trigger_rate | 33.3 | < 15.0 | FAIL | yes |
| decoy_ipv4 | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_ipv6_mac | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_names_as_org | 24 | decoy_trigger_rate | 16.7 | < 15.0 | FAIL | yes |
| decoy_time | 24 | decoy_trigger_rate | 41.7 | < 15.0 | FAIL | yes |
| decoy_voen_passport_id | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_zip | 24 | decoy_trigger_rate | 66.7 | < 15.0 | FAIL | yes |
| fmt_csv | 24 | exact_recall | 87.5 | >= 70.0 | PASS | yes |
|  |  | exact_recall [EMAIL] | 50.0 | > 60.0 | FAIL |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_csv_noheader | 24 | exact_recall | 87.5 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 75.0 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 83.3 | > 60.0 | PASS |  |
| fmt_dialogue | 24 | exact_recall | 100.0 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 100.0 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_json | 24 | exact_recall | 100.0 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 100.0 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_kv | 24 | exact_recall | 87.5 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 91.7 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_log | 24 | exact_recall | 100.0 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 100.0 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_pipe | 24 | exact_recall | 100.0 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 100.0 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| foreign_names | 30 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 80.0 | PASS | yes |
|  |  | decoy_trigger_rate_any | 20.0 | < 15.0 | FAIL |  |
| homograph_pairs | 16 | exact_recall [GIVENNAME] | 87.5 | >= 90.0 | FAIL | yes |
|  |  | control_fp_rate | 12.5 | < 10.0 | FAIL |  |
| inflected_anchor | 24 | exact_recall | 91.7 | >= 80.0 | PASS | **NO** |
| ipv6_vs_mac | 24 | exact_recall [IPV6_ADDRESS] | 100.0 | >= 80.0 | PASS | **NO** |
|  |  | confusion_rate IPV6_ADDRESS→MAC_ADDRESS | 0.0 | < 5.0 | PASS |  |
| licence_vs_id | 24 | confusion_rate AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER | 16.7 | < 5.0 | FAIL | yes |
|  |  | confusion_rate AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER | 8.3 | < 5.0 | FAIL |  |
| name_homographs | 64 | exact_recall [GIVENNAME] | 100.0 | >= 90.0 | PASS | yes |
|  |  | control_fp_rate | 12.5 | < 10.0 | FAIL |  |
| name_transliteration_variants | 80 | exact_recall | 100.0 | >= 90.0 | PASS | **NO** |
|  |  | wrong_label | 0 | == 0 | PASS |  |
| noisy_suffixes | 36 | exact_recall [GIVENNAME,SURNAME,CITY] | 100.0 | >= 85.0 | PASS | **NO** |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| nonpii_ids | 24 | control_fp_rate | 41.7 | <= ×0.3 ckpt1 | – | yes |
|  |  | sanity: control_fp_rate | 41.7 | >= 10.0 | PASS |  |
| pem | 20 | char_leakage_rate | 43.9 | < ×1.0 ckpt1 | – | yes |
|  |  | sanity: exact_recall | 0.0 | < 90.0 | PASS |  |
| pii_free | 24 | pii_free_fp_rate | 8.3 | < 15.0 | PASS | **NO** |
| prose_card | 24 | exact_recall | 50.0 | >= 80.0 | FAIL | yes |
| prose_date | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| prose_iban | 24 | exact_recall | 8.3 | >= 80.0 | FAIL | yes |
| punct_touching | 24 | exact_recall | 100.0 | >= 90.0 | PASS | **NO** |
| sentence_initial_nouns | 24 | control_fp_rate | 0.0 | <= ×0.3 ckpt1 | – | **NO** |
|  |  | sanity: control_fp_rate | 0.0 | >= 10.0 | FAIL |  |
| single_entity | 24 | exact_f1 | 52.2 | >= 80.0 | FAIL | yes |
| spaced_card_iban | 24 | char_leakage_rate | 20.4 | < ×1.0 ckpt1 | – | yes |
|  |  | sanity: exact_recall | 75.0 | < 90.0 | PASS |  |
| spaced_phone | 24 | char_leakage_rate | 27.0 | < ×1.0 ckpt1 | – | yes |
|  |  | sanity: exact_recall | 66.7 | < 90.0 | PASS |  |
| suffixed_entities | 273 | case_exact_recall_min | 66.7 | >= 85.0 | FAIL | yes |
| token_vs_key | 24 | exact_recall [ACCESS_TOKEN] | 91.7 | >= 80.0 | PASS | **NO** |
|  |  | confusion_rate ACCESS_TOKEN→API_KEY | 0.0 | < 10.0 | PASS |  |
| villages | 34 | exact_recall [CITY] | 76.9 | >= 80.0 | FAIL | yes |
|  |  | control_fp_rate | 33.3 | < 10.0 | FAIL |  |

### Slices: probes (exact recall / overlap recall / split spans)

| Slice | Value | Gold | R | M |
|---|---|---|---|---|
| entity:case | abl | 21 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:case | acc_consonant | 21 | 85.7 / 85.7 / 0 | 85.7 / 85.7 / 0 |
| entity:case | acc_vowel | 21 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:case | apostrophe | 21 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:case | ascii_folded | 21 | 85.7 / 85.7 / 0 | 85.7 / 85.7 / 0 |
| entity:case | cop | 21 | 66.7 / 85.7 / 4 | 66.7 / 66.7 / 0 |
| entity:case | dat | 21 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:case | gen | 33 | 78.8 / 90.9 / 4 | 81.8 / 81.8 / 0 |
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
| entity:form | worded | 3 | 66.7 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:noise | buffer | 6 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:noise | colloquial | 6 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:noise | double | 6 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:noise | harmony | 6 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:origin | en_eu | 10 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:origin | fa_ar | 8 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:origin | ka | 6 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:origin | ru | 10 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:origin | tr | 6 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:sep | colon | 8 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:sep | dot | 7 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:sep | hyphen | 7 | 85.7 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:variant | ascii_or_ru_latin | 16 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:variant | az_latin | 16 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:variant | cyrillic | 16 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:variant | en_latin | 16 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:variant | tr_or_other | 16 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:control | True | 0 | – / – / 0 | – / – / 0 |
| doc:family | anchor_distance | 12 | 75.0 / 75.0 / 0 | 83.3 / 83.3 / 0 |
| doc:family | bare_name | 45 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | building_vs_room | 12 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | casing_noise | 24 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | contrast_ipv6_mac | 48 | 97.9 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | contrast_licence_id | 24 | 91.7 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | contrast_token_key | 28 | 92.9 / 100.0 / 1 | 96.4 / 100.0 / 1 |
| doc:family | date_vs_timestamp | 16 | 93.8 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | decoy_age | 12 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | decoy_card_iccid_iban | 12 | 58.3 / 83.3 / 2 | 75.0 / 83.3 / 1 |
| doc:family | decoy_cvv | 12 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | decoy_date | 12 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | decoy_fin | 12 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | decoy_ipv4 | 12 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | decoy_ipv6_mac | 12 | 91.7 / 100.0 / 1 | 100.0 / 100.0 / 0 |
| doc:family | decoy_names_as_org | 12 | 66.7 / 66.7 / 0 | 66.7 / 66.7 / 0 |
| … | 58 more rows in the JSON | | |

Calibration (score bins vs precision) is in the JSON. It is reported only and is never used to set a threshold (A2.2).
