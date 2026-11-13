# Scoreboard: m1_public

| | |
|---|---|
| Model | `your-hf-org/masking-multi-m1-seed42` |
| Revision SHA | `d7493a1634f3aadc4dab5cd3b8103cf070e5eff0` |
| Requested revision | `d7493a1634f3aadc4dab5cd3b8103cf070e5eff0` |
| Code git SHA | `` |
| Date (UTC) | 2026-10-24T03:36:05Z |
| Device | cuda |
| Libraries | tokenizers 0.22.2, transformers 4.57.6, torch 2.14.1+cu130, python 3.10.12 |
| Tracks | R = raw HF pipeline (simple), M = model-only product path |
| Data version | benchmark `b272b758eb6e4e5e`; probes `684455a3e6065565`; golden_en `6940dc9e2b95a0dd`; lang_tr `3ef3f93b71cb90d1`; lang_ru `3ef3f93b71cb90d1` |

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
| probes | R | 1680 | 92.8 / 95.6 / 94.2 | 94.4 | 94.7 | 0.4 | 88.9 | 5 | 7.3 (7.7) | 0.0 rec, 13.0 span | 12.3 | 92.1 |
| probes excl. policy | R | 1680 | 94.7 / 95.6 / 95.2 | 96.7 | 95.6 | 0.4 | 88.9 | 5 | 1.1 (1.5) | 0.0 rec, 13.0 span | 4.6 | 94.1 |
| probes | M | 1680 | 93.0 / 95.7 / 94.3 | 94.4 | 94.7 | 0.4 | 85.7 | 3 | 7.1 (7.5) | 0.0 rec, 13.0 span | 12.1 | 92.2 |
| probes excl. policy | M | 1680 | 94.8 / 95.7 / 95.3 | 96.7 | 95.6 | 0.4 | 85.7 | 3 | 1.1 (1.5) | 0.0 rec, 13.0 span | 4.6 | 94.2 |
| golden_en | R | 217 | 75.5 / 98.9 / 85.7 | 94.5 | 86.0 | 0.1 | 50.0 | 1 | 0.0 (0.0) | – | – | 52.1 |
| golden_en | M | 217 | 75.5 / 98.9 / 85.7 | 94.5 | 86.0 | 0.1 | 50.0 | 1 | 0.0 (0.0) | – | – | 52.1 |
| lang_tr | R | 1000 | 90.5 / 97.1 / 93.7 | 96.8 | 94.2 | 1.7 | 40.0 | 7 | 0.0 (0.0) | – | 5.2 | 80.0 |
| lang_tr | M | 1000 | 90.7 / 97.1 / 93.8 | 96.8 | 94.3 | 1.7 | 34.8 | 5 | 0.0 (0.0) | – | 5.2 | 80.2 |
| lang_ru | R | 1000 | 93.7 / 96.4 / 95.0 | 97.5 | 95.5 | 2.5 | 78.9 | 14 | 0.0 (0.0) | – | 3.6 | 78.2 |
| lang_ru | M | 1000 | 93.9 / 96.4 / 95.1 | 97.5 | 95.5 | 2.5 | 71.4 | 10 | 0.0 (0.0) | – | 3.6 | 78.4 |

## Probe targets (track R): 40/53 families pass; 10/53 show their failure

| Family | Docs | Condition | Measured | Target | Pass | Shows the failure |
|---|---|---|---|---|---|---|
| anchor_distance | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| bare_name | 43 | exact_recall | 100.0 | >= 90.0 | PASS | **NO** |
|  |  | split_spans | 0 | == 0 | PASS |  |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| building_vs_room | 24 | control_fp_rate | 16.7 | <= ×0.3 ckpt1 | – | yes |
|  |  | sanity: control_fp_rate | 16.7 | >= 10.0 | PASS |  |
| casing_noise | 24 | exact_recall | 79.2 | >= 80.0 | FAIL | yes |
| contrast_ipv6_mac | 60 | exact_recall [IPV6_ADDRESS] | 100.0 | >= 80.0 | PASS | **NO** |
|  |  | exact_recall [MAC_ADDRESS] | 100.0 | >= 80.0 | PASS |  |
|  |  | confusion_rate IPV6_ADDRESS→MAC_ADDRESS | 0.0 | < 5.0 | PASS |  |
|  |  | confusion_rate MAC_ADDRESS→IPV6_ADDRESS | 0.0 | < 5.0 | PASS |  |
|  |  | decoy_trigger_rate | 9.1 | < 15.0 | PASS |  |
| contrast_licence_id | 26 | confusion_rate AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER | 0.0 | < 5.0 | PASS | **NO** |
|  |  | confusion_rate AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER | 0.0 | < 5.0 | PASS |  |
|  |  | exact_recall [AZ_DRIVER_LICENSE_NUMBER] | 100.0 | >= 80.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | >= 80.0 | PASS |  |
|  |  | decoy_trigger_rate | 0.0 | < 15.0 | PASS |  |
| contrast_token_key | 24 | exact_recall [ACCESS_TOKEN] | 100.0 | >= 80.0 | PASS | **NO** |
|  |  | exact_recall [API_KEY] | 100.0 | >= 80.0 | PASS |  |
|  |  | confusion_rate ACCESS_TOKEN→API_KEY | 0.0 | < 10.0 | PASS |  |
|  |  | confusion_rate API_KEY→ACCESS_TOKEN | 0.0 | < 10.0 | PASS |  |
|  |  | decoy_trigger_rate | 0.0 | < 15.0 | PASS |  |
| date_vs_timestamp | 22 | exact_recall [DATE] | 100.0 | >= 80.0 | PASS | yes |
|  |  | decoy_trigger_rate | 16.7 | < 15.0 | FAIL |  |
| decoy_age | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_card_iccid_iban | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_cvv | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_date | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_fin | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_ipv4 | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_ipv6_mac | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_names_as_org | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_time | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_voen_passport_id | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_zip | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| fmt_csv | 24 | exact_recall | 100.0 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 100.0 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_csv_noheader | 24 | exact_recall | 100.0 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 100.0 | > 60.0 | PASS |  |
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
| homograph_pairs | 16 | exact_recall [GIVENNAME] | 75.0 | >= 90.0 | FAIL | yes |
|  |  | control_fp_rate | 6.2 | < 10.0 | PASS |  |
| inflected_anchor | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| ipv6_vs_mac | 24 | exact_recall [IPV6_ADDRESS] | 100.0 | >= 80.0 | PASS | **NO** |
|  |  | confusion_rate IPV6_ADDRESS→MAC_ADDRESS | 0.0 | < 5.0 | PASS |  |
| licence_vs_id | 24 | confusion_rate AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER | 0.0 | < 5.0 | PASS | **NO** |
|  |  | confusion_rate AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER | 0.0 | < 5.0 | PASS |  |
| line_end_ip_email | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| name_homographs | 64 | exact_recall [GIVENNAME] | 96.9 | >= 90.0 | PASS | **NO** |
|  |  | control_fp_rate | 9.4 | < 10.0 | PASS |  |
| name_transliteration_variants | 80 | exact_recall | 100.0 | >= 90.0 | PASS | **NO** |
|  |  | wrong_label | 0 | == 0 | PASS |  |
| names_after_role | 24 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 90.0 | PASS | yes |
|  |  | control_fp_rate | 25.0 | < 10.0 | FAIL |  |
| names_list_lines | 14 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 90.0 | PASS | yes |
|  |  | control_fp_rate | 50.0 | < 10.0 | FAIL |  |
| names_sentence_start | 26 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 90.0 | PASS | **NO** |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| names_signature | 24 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 90.0 | PASS | **NO** |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| noisy_suffixes | 36 | exact_recall [GIVENNAME,SURNAME,CITY] | 95.8 | >= 85.0 | PASS | **NO** |
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
| single_entity | 24 | exact_f1 | 96.0 | >= 80.0 | PASS | **NO** |
| spaced_card_iban | 24 | char_leakage_rate | 0.0 | < ×1.0 ckpt1 | – | **NO** |
|  |  | sanity: exact_recall | 100.0 | < 90.0 | FAIL |  |
| spaced_phone | 24 | char_leakage_rate | 18.9 | < ×1.0 ckpt1 | – | yes |
|  |  | sanity: exact_recall | 75.0 | < 90.0 | PASS |  |
| suffixed_entities | 273 | case_exact_recall_min | 66.7 | >= 85.0 | FAIL | yes |
| token_vs_key | 24 | exact_recall [ACCESS_TOKEN] | 100.0 | >= 80.0 | PASS | **NO** |
|  |  | confusion_rate ACCESS_TOKEN→API_KEY | 0.0 | < 10.0 | PASS |  |
| villages | 34 | exact_recall [CITY] | 69.2 | >= 80.0 | FAIL | yes |
|  |  | control_fp_rate | 11.1 | < 10.0 | FAIL |  |

`decoy_cvv` look-alikes masked as CVV, by kind: `12345` dummies (D-2) 0/2; random 5-digit codes 0/5; dashed, policy (D-34c) 2/2; dashed, policy (D-39c) 3/3

## Probe targets (track M): 40/53 families pass; 10/53 show their failure

| Family | Docs | Condition | Measured | Target | Pass | Shows the failure |
|---|---|---|---|---|---|---|
| anchor_distance | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| bare_name | 43 | exact_recall | 100.0 | >= 90.0 | PASS | **NO** |
|  |  | split_spans | 0 | == 0 | PASS |  |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| building_vs_room | 24 | control_fp_rate | 16.7 | <= ×0.3 ckpt1 | – | yes |
|  |  | sanity: control_fp_rate | 16.7 | >= 10.0 | PASS |  |
| casing_noise | 24 | exact_recall | 79.2 | >= 80.0 | FAIL | yes |
| contrast_ipv6_mac | 60 | exact_recall [IPV6_ADDRESS] | 100.0 | >= 80.0 | PASS | **NO** |
|  |  | exact_recall [MAC_ADDRESS] | 100.0 | >= 80.0 | PASS |  |
|  |  | confusion_rate IPV6_ADDRESS→MAC_ADDRESS | 0.0 | < 5.0 | PASS |  |
|  |  | confusion_rate MAC_ADDRESS→IPV6_ADDRESS | 0.0 | < 5.0 | PASS |  |
|  |  | decoy_trigger_rate | 9.1 | < 15.0 | PASS |  |
| contrast_licence_id | 26 | confusion_rate AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER | 0.0 | < 5.0 | PASS | **NO** |
|  |  | confusion_rate AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER | 0.0 | < 5.0 | PASS |  |
|  |  | exact_recall [AZ_DRIVER_LICENSE_NUMBER] | 100.0 | >= 80.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | >= 80.0 | PASS |  |
|  |  | decoy_trigger_rate | 0.0 | < 15.0 | PASS |  |
| contrast_token_key | 24 | exact_recall [ACCESS_TOKEN] | 100.0 | >= 80.0 | PASS | **NO** |
|  |  | exact_recall [API_KEY] | 100.0 | >= 80.0 | PASS |  |
|  |  | confusion_rate ACCESS_TOKEN→API_KEY | 0.0 | < 10.0 | PASS |  |
|  |  | confusion_rate API_KEY→ACCESS_TOKEN | 0.0 | < 10.0 | PASS |  |
|  |  | decoy_trigger_rate | 0.0 | < 15.0 | PASS |  |
| date_vs_timestamp | 22 | exact_recall [DATE] | 100.0 | >= 80.0 | PASS | yes |
|  |  | decoy_trigger_rate | 16.7 | < 15.0 | FAIL |  |
| decoy_age | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_card_iccid_iban | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_cvv | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_date | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_fin | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_ipv4 | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_ipv6_mac | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_names_as_org | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_time | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_voen_passport_id | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| decoy_zip | 24 | decoy_trigger_rate | 0.0 | < 15.0 | PASS | **NO** |
| fmt_csv | 24 | exact_recall | 100.0 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 100.0 | > 60.0 | PASS |  |
|  |  | exact_recall [AZ_ID_CARD_NUMBER] | 100.0 | > 60.0 | PASS |  |
| fmt_csv_noheader | 24 | exact_recall | 100.0 | >= 70.0 | PASS | **NO** |
|  |  | exact_recall [EMAIL] | 100.0 | > 60.0 | PASS |  |
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
| homograph_pairs | 16 | exact_recall [GIVENNAME] | 75.0 | >= 90.0 | FAIL | yes |
|  |  | control_fp_rate | 6.2 | < 10.0 | PASS |  |
| inflected_anchor | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| ipv6_vs_mac | 24 | exact_recall [IPV6_ADDRESS] | 100.0 | >= 80.0 | PASS | **NO** |
|  |  | confusion_rate IPV6_ADDRESS→MAC_ADDRESS | 0.0 | < 5.0 | PASS |  |
| licence_vs_id | 24 | confusion_rate AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER | 0.0 | < 5.0 | PASS | **NO** |
|  |  | confusion_rate AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER | 0.0 | < 5.0 | PASS |  |
| line_end_ip_email | 24 | exact_recall | 100.0 | >= 80.0 | PASS | **NO** |
| name_homographs | 64 | exact_recall [GIVENNAME] | 96.9 | >= 90.0 | PASS | **NO** |
|  |  | control_fp_rate | 9.4 | < 10.0 | PASS |  |
| name_transliteration_variants | 80 | exact_recall | 100.0 | >= 90.0 | PASS | **NO** |
|  |  | wrong_label | 0 | == 0 | PASS |  |
| names_after_role | 24 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 90.0 | PASS | yes |
|  |  | control_fp_rate | 25.0 | < 10.0 | FAIL |  |
| names_list_lines | 14 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 90.0 | PASS | yes |
|  |  | control_fp_rate | 50.0 | < 10.0 | FAIL |  |
| names_sentence_start | 26 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 90.0 | PASS | **NO** |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| names_signature | 24 | exact_recall [GIVENNAME,SURNAME] | 100.0 | >= 90.0 | PASS | **NO** |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| noisy_suffixes | 36 | exact_recall [GIVENNAME,SURNAME,CITY] | 95.8 | >= 85.0 | PASS | **NO** |
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
| single_entity | 24 | exact_f1 | 96.0 | >= 80.0 | PASS | **NO** |
| spaced_card_iban | 24 | char_leakage_rate | 0.0 | < ×1.0 ckpt1 | – | **NO** |
|  |  | sanity: exact_recall | 100.0 | < 90.0 | FAIL |  |
| spaced_phone | 24 | char_leakage_rate | 18.9 | < ×1.0 ckpt1 | – | yes |
|  |  | sanity: exact_recall | 75.0 | < 90.0 | PASS |  |
| suffixed_entities | 273 | case_exact_recall_min | 66.7 | >= 85.0 | FAIL | yes |
| token_vs_key | 24 | exact_recall [ACCESS_TOKEN] | 100.0 | >= 80.0 | PASS | **NO** |
|  |  | confusion_rate ACCESS_TOKEN→API_KEY | 0.0 | < 10.0 | PASS |  |
| villages | 34 | exact_recall [CITY] | 69.2 | >= 80.0 | FAIL | yes |
|  |  | control_fp_rate | 11.1 | < 10.0 | FAIL |  |

`decoy_cvv` look-alikes masked as CVV, by kind: `12345` dummies (D-2) 0/2; random 5-digit codes 0/5; dashed, policy (D-34c) 2/2; dashed, policy (D-39c) 3/3

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

### Slices: probes (exact recall / overlap recall / split spans)

| Slice | Value | Gold | R | M |
|---|---|---|---|---|
| entity:case | abl | 21 | 81.0 / 81.0 / 0 | 81.0 / 81.0 / 0 |
| entity:case | acc_consonant | 21 | 85.7 / 85.7 / 0 | 85.7 / 85.7 / 0 |
| entity:case | acc_vowel | 21 | 66.7 / 66.7 / 0 | 66.7 / 66.7 / 0 |
| entity:case | apostrophe | 21 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:case | ascii_folded | 21 | 85.7 / 85.7 / 0 | 85.7 / 85.7 / 0 |
| entity:case | cop | 21 | 66.7 / 66.7 / 0 | 66.7 / 66.7 / 0 |
| entity:case | dat | 21 | 85.7 / 85.7 / 0 | 85.7 / 85.7 / 0 |
| entity:case | gen | 33 | 60.6 / 63.6 / 1 | 63.6 / 63.6 / 0 |
| entity:case | ins | 21 | 81.0 / 81.0 / 0 | 81.0 / 81.0 / 0 |
| entity:case | loc | 21 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:case | pl | 21 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:case | pl_case | 21 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:case | rel | 21 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:entity_noise | case_or_ascii | 12 | 75.0 / 75.0 / 0 | 75.0 / 75.0 / 0 |
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
| entity:noise | colloquial | 6 | 83.3 / 83.3 / 0 | 83.3 / 83.3 / 0 |
| entity:noise | double | 6 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
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
| entity:variant | ascii_or_ru_latin | 16 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:variant | az_latin | 16 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:variant | cyrillic | 16 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:variant | en_latin | 16 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:variant | tr_or_other | 16 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:control | True | 0 | – / – / 0 | – / – / 0 |
| doc:lang | az | 1668 | 95.6 / 96.0 / 5 | 95.7 / 95.9 / 3 |
| doc:resembles | GIVENNAME | 0 | – / – / 0 | – / – / 0 |
| doc:same_body | False | 8 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:same_body | True | 16 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:density | 0 | 0 | – / – / 0 | – / – / 0 |
| doc:density | 1 | 1043 | 93.0 / 93.6 / 5 | 93.1 / 93.5 / 3 |
| doc:density | 2-3 | 454 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:density | 7+ | 171 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| control:kind | common_noun | 6 spans | FP 0.0 | FP 0.0 |
| control:kind | common_word | 4 spans | FP 0.0 | FP 0.0 |
| control:kind | department_signature | 4 spans | FP 0.0 | FP 0.0 |
| control:kind | generic_place | 5 spans | FP 20.0 | FP 20.0 |
| control:kind | homograph_word | 48 spans | FP 8.3 | FP 8.3 |
| control:kind | noisy_suffix_noun | 12 spans | FP 0.0 | FP 0.0 |
| … | 18 more rows in the JSON | | |

### Slices: golden_en (exact recall / overlap recall / split spans)

| Slice | Value | Gold | R | M |
|---|---|---|---|---|
| doc:_bucket | extreme | 184 | 99.5 / 100.0 / 0 | 99.5 / 100.0 / 0 |
| doc:_bucket | long | 223 | 98.2 / 98.2 / 0 | 98.2 / 98.2 / 0 |
| doc:_bucket | medium | 132 | 99.2 / 99.2 / 0 | 99.2 / 99.2 / 0 |
| doc:_bucket | short | 82 | 98.8 / 98.8 / 0 | 98.8 / 98.8 / 0 |
| doc:_bucket | very_long | 357 | 99.2 / 99.4 / 0 | 99.2 / 99.4 / 0 |
| doc:_bucket | very_short | 49 | 98.0 / 100.0 / 1 | 98.0 / 100.0 / 1 |
| doc:_register | anxious and confused | 101 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_register | apologetic | 61 | 98.4 / 98.4 / 0 | 98.4 / 98.4 / 0 |
| doc:_register | bureaucratic and officious | 79 | 97.5 / 97.5 / 0 | 97.5 / 97.5 / 0 |
| doc:_register | casual with typos and abbreviations | 64 | 95.3 / 95.3 / 0 | 95.3 / 95.3 / 0 |
| doc:_register | empathetic customer-service | 62 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_register | formal and businesslike | 75 | 97.3 / 98.7 / 0 | 97.3 / 98.7 / 0 |
| doc:_register | friendly with light humour | 57 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_register | frustrated and complaining | 52 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_register | matter-of-fact administrative | 78 | 98.7 / 100.0 / 0 | 98.7 / 100.0 / 0 |
| doc:_register | polite but firm | 73 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_register | technical and precise | 76 | 98.7 / 98.7 / 0 | 98.7 / 98.7 / 0 |
| doc:_register | terse and clipped | 67 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_register | urgent and escalating | 87 | 98.9 / 100.0 / 1 | 98.9 / 100.0 / 1 |
| doc:_register | warm and conversational | 95 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:lang | en | 1027 | 98.9 / 99.2 / 1 | 98.9 / 99.2 / 1 |
| doc:split |  | 1027 | 98.9 / 99.2 / 1 | 98.9 / 99.2 / 1 |
| doc:density | 1 | 63 | 98.4 / 98.4 / 0 | 98.4 / 98.4 / 0 |
| doc:density | 2-3 | 145 | 99.3 / 100.0 / 1 | 99.3 / 100.0 / 1 |
| doc:density | 4-6 | 202 | 99.0 / 99.5 / 0 | 99.0 / 99.5 / 0 |
| doc:density | 7+ | 617 | 98.9 / 99.0 / 0 | 98.9 / 99.0 / 0 |

### Slices: lang_tr (exact recall / overlap recall / split spans)

| Slice | Value | Gold | R | M |
|---|---|---|---|---|
| doc:_bucket | extreme | 203 | 97.5 / 99.0 / 0 | 97.0 / 98.5 / 0 |
| doc:_bucket | long | 1376 | 96.4 / 96.7 / 1 | 96.4 / 96.7 / 1 |
| doc:_bucket | medium | 976 | 96.9 / 97.3 / 0 | 96.9 / 97.3 / 0 |
| doc:_bucket | short | 476 | 98.1 / 98.9 / 2 | 98.1 / 98.9 / 2 |
| doc:_bucket | very_long | 831 | 97.1 / 97.8 / 3 | 97.2 / 97.8 / 2 |
| doc:_bucket | very_short | 154 | 99.4 / 100.0 / 1 | 99.4 / 99.4 / 0 |
| doc:_register | anxious and confused | 274 | 97.8 / 99.3 / 3 | 97.8 / 99.3 / 3 |
| doc:_register | apologetic | 203 | 99.0 / 99.0 / 0 | 99.0 / 99.0 / 0 |
| doc:_register | bureaucratic and officious | 197 | 96.4 / 96.4 / 0 | 96.4 / 96.4 / 0 |
| doc:_register | casual with typos and abbreviations | 389 | 97.9 / 98.5 / 0 | 97.7 / 98.2 / 0 |
| doc:_register | empathetic customer-service | 206 | 96.1 / 97.1 / 0 | 96.1 / 97.1 / 0 |
| doc:_register | formal and businesslike | 322 | 95.3 / 96.0 / 1 | 95.3 / 96.0 / 1 |
| doc:_register | friendly with light humour | 293 | 98.3 / 98.3 / 0 | 98.3 / 98.3 / 0 |
| doc:_register | frustrated and complaining | 265 | 96.6 / 97.4 / 0 | 96.6 / 97.4 / 0 |
| doc:_register | matter-of-fact administrative | 343 | 93.9 / 95.6 / 3 | 94.2 / 95.3 / 1 |
| doc:_register | polite but firm | 294 | 95.6 / 95.6 / 0 | 95.6 / 95.6 / 0 |
| doc:_register | technical and precise | 301 | 98.7 / 99.0 / 0 | 98.7 / 99.0 / 0 |
| doc:_register | terse and clipped | 334 | 99.4 / 99.4 / 0 | 99.4 / 99.4 / 0 |
| doc:_register | urgent and escalating | 325 | 96.3 / 96.3 / 0 | 96.3 / 96.3 / 0 |
| doc:_register | warm and conversational | 270 | 97.8 / 98.9 / 0 | 97.8 / 98.9 / 0 |
| doc:lang | tr | 4016 | 97.1 / 97.6 / 7 | 97.1 / 97.6 / 5 |
| doc:split | test | 4016 | 97.1 / 97.6 / 7 | 97.1 / 97.6 / 5 |
| doc:density | 0 | 0 | – / – / 0 | – / – / 0 |
| doc:density | 1 | 177 | 96.0 / 96.0 / 0 | 96.0 / 96.0 / 0 |
| doc:density | 2-3 | 669 | 95.5 / 96.4 / 2 | 95.5 / 96.3 / 1 |
| doc:density | 4-6 | 936 | 97.0 / 97.8 / 4 | 97.0 / 97.8 / 4 |
| doc:density | 7+ | 2234 | 97.6 / 98.0 / 1 | 97.6 / 98.0 / 0 |

### Slices: lang_ru (exact recall / overlap recall / split spans)

| Slice | Value | Gold | R | M |
|---|---|---|---|---|
| doc:_bucket | extreme | 249 | 98.4 / 98.4 / 0 | 98.4 / 98.4 / 0 |
| doc:_bucket | long | 1406 | 95.7 / 96.2 / 6 | 95.7 / 96.2 / 4 |
| doc:_bucket | medium | 1019 | 96.4 / 96.8 / 4 | 96.4 / 96.7 / 3 |
| doc:_bucket | short | 429 | 98.1 / 98.8 / 2 | 98.1 / 98.8 / 2 |
| doc:_bucket | very_long | 775 | 96.0 / 96.3 / 2 | 95.9 / 96.0 / 1 |
| doc:_bucket | very_short | 115 | 98.3 / 98.3 / 0 | 98.3 / 98.3 / 0 |
| doc:_register | anxious and confused | 305 | 97.7 / 98.0 / 1 | 97.7 / 97.7 / 0 |
| doc:_register | apologetic | 269 | 95.9 / 95.9 / 0 | 95.9 / 95.9 / 0 |
| doc:_register | bureaucratic and officious | 273 | 94.9 / 95.2 / 1 | 94.9 / 94.9 / 0 |
| doc:_register | casual with typos and abbreviations | 356 | 97.5 / 97.8 / 1 | 97.5 / 97.8 / 1 |
| doc:_register | empathetic customer-service | 304 | 97.0 / 97.4 / 1 | 96.7 / 97.0 / 1 |
| doc:_register | formal and businesslike | 289 | 93.8 / 94.1 / 1 | 93.8 / 94.1 / 1 |
| doc:_register | friendly with light humour | 265 | 96.6 / 97.7 / 1 | 97.0 / 97.7 / 0 |
| doc:_register | frustrated and complaining | 244 | 98.4 / 99.2 / 2 | 98.4 / 99.2 / 2 |
| doc:_register | matter-of-fact administrative | 390 | 96.4 / 96.7 / 1 | 96.4 / 96.7 / 1 |
| doc:_register | polite but firm | 284 | 96.1 / 96.5 / 1 | 96.1 / 96.1 / 0 |
| doc:_register | technical and precise | 206 | 94.2 / 94.7 / 1 | 94.2 / 94.7 / 1 |
| doc:_register | terse and clipped | 293 | 98.3 / 98.6 / 1 | 98.3 / 98.6 / 1 |
| doc:_register | urgent and escalating | 295 | 96.6 / 97.3 / 1 | 96.6 / 97.3 / 1 |
| doc:_register | warm and conversational | 220 | 95.5 / 95.9 / 1 | 95.5 / 95.9 / 1 |
| doc:lang | ru | 3993 | 96.4 / 96.8 / 14 | 96.4 / 96.7 / 10 |
| doc:split | test | 3993 | 96.4 / 96.8 / 14 | 96.4 / 96.7 / 10 |
| doc:density | 0 | 0 | – / – / 0 | – / – / 0 |
| doc:density | 1 | 197 | 93.4 / 93.4 / 0 | 93.4 / 93.4 / 0 |
| doc:density | 2-3 | 638 | 95.6 / 96.6 / 3 | 95.6 / 96.4 / 2 |
| doc:density | 4-6 | 945 | 96.4 / 96.7 / 3 | 96.4 / 96.7 / 3 |
| doc:density | 7+ | 2213 | 96.9 / 97.3 / 8 | 96.9 / 97.2 / 5 |

Calibration (score bins vs precision) is in the JSON. It is reported only and is never used to set a threshold (A2.2).
