# Scoreboard: probes_ckpt1

| | |
|---|---|
| Model | `your-hf-org/masking-multilingual` |
| Revision SHA | `3a0a6e5df228bdc89dd01312a728e10a78b3e3fb` |
| Requested revision | `None` |
| Code git SHA | `12d721c6fd4955f79085f6063f58cf0aa789c516` (eval/ or model/ dirty) |
| Date (UTC) | 2026-10-01T09:04:06Z |
| Device | cpu |
| Tracks | R = raw HF pipeline (simple) |
| Data version | probes `b4e6a0a8239a13a7` |

## A6 gates (shadow_dev, track R)

| Gate | Measured | Sprint 1 target | S1 | Sprint 2 target | S2 | Note |
|---|---|---|---|---|---|---|
| micro_f1 | n/a | >= 76.0 | – | >= 82.0 | – | shadow_dev not scored |
| weakest_label_f1 | n/a | >= 50.0 | – | >= 65.0 | – | shadow_dev not scored |
| ACCESS_TOKEN_f1 | n/a | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored |
| IPV6_ADDRESS_f1 | n/a | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored |
| AZ_DRIVER_LICENSE_NUMBER_f1 | n/a | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored |
| hard_negative_trigger_rate | n/a | < 12.0 | – | < 8.0 | – | shadow_dev not scored |
| pii_free_fp_rate | n/a | < 30.0 | – | < 15.0 | – | shadow_dev not scored |
| recall_guard | n/a | no label -1 pt | – | no label -1 pt | – | no --baseline given |
| en_tr_ru_regression | n/a | <= 1 pt drop | – | <= 1 pt drop | – | no --baseline given |
| appendix_known_errors_fixed | n/a | reported by class | – | reported by class | – | appendix not scored |
| sealed_set | untouched | untouched | PASS | run once | – |  |

## Sets

Percentages. Exact = label+start+end. Trigger = decoy hit with the label it resembles (any label in brackets).

| Set | Track | Docs | Exact P / R / F1 | Macro F1 | Overlap F1 | Char leak | Narrower | Split | Trigger | Control FP | PII-free FP | Perfect |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| probes | R | 1320 | 45.4 / 65.4 / 53.6 | 56.1 | 74.4 | 22.3 | 96.0 | 150 | 56.0 (74.5) | 0.0 rec, 55.9 span | 61.5 | 49.4 |
| probes excl. policy | R | 1320 | 46.0 / 65.4 / 54.0 | 56.5 | 74.9 | 22.3 | 96.0 | 150 | 54.5 (73.9) | 0.0 rec, 55.9 span | 56.3 | 50.8 |

## Probe targets (track R): 0/40 families pass; 40/40 show their failure

| Family | Docs | Condition | Measured | Target | Pass | Shows the failure |
|---|---|---|---|---|---|---|
| anchor_distance | 24 | exact_recall | 33.3 | >= 80.0 | FAIL | yes |
| bare_name | 43 | exact_recall | 33.3 | >= 90.0 | FAIL | yes |
|  |  | split_spans | 4 | == 0 | FAIL |  |
|  |  | control_fp_rate | 0.0 | < 10.0 | PASS |  |
| building_vs_room | 24 | control_fp_rate | 100.0 | <= ×0.3 ckpt1 | – | yes |
|  |  | sanity: control_fp_rate | 100.0 | >= 10.0 | PASS |  |
| casing_noise | 24 | exact_recall | 37.5 | >= 80.0 | FAIL | yes |
| decoy_age | 24 | decoy_trigger_rate | 100.0 | < 15.0 | FAIL | yes |
| decoy_card_iccid_iban | 24 | decoy_trigger_rate | 33.3 | < 15.0 | FAIL | yes |
| decoy_cvv | 24 | decoy_trigger_rate | 100.0 | < 15.0 | FAIL | yes |
| decoy_date | 24 | decoy_trigger_rate | 100.0 | < 15.0 | FAIL | yes |
| decoy_fin | 24 | decoy_trigger_rate | 66.7 | < 15.0 | FAIL | yes |
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
| inflected_anchor | 24 | exact_recall | 66.7 | >= 80.0 | FAIL | yes |
| ipv6_vs_mac | 24 | exact_recall [IPV6_ADDRESS] | 83.3 | >= 80.0 | PASS | yes |
|  |  | confusion_rate IPV6_ADDRESS→MAC_ADDRESS | 16.7 | < 5.0 | FAIL |  |
| licence_vs_id | 24 | confusion_rate AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER | 100.0 | < 5.0 | FAIL | yes |
|  |  | confusion_rate AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER | 0.0 | < 5.0 | PASS |  |
| name_homographs | 64 | exact_recall [GIVENNAME] | 100.0 | >= 90.0 | PASS | yes |
|  |  | control_fp_rate | 53.1 | < 10.0 | FAIL |  |
| name_transliteration_variants | 80 | exact_recall | 92.5 | >= 90.0 | PASS | yes |
|  |  | wrong_label | 1 | == 0 | FAIL |  |
| nonpii_ids | 24 | control_fp_rate | 58.3 | <= ×0.3 ckpt1 | – | yes |
|  |  | sanity: control_fp_rate | 58.3 | >= 10.0 | PASS |  |
| pem | 20 | char_leakage_rate | 20.5 | < ×1.0 ckpt1 | – | yes |
|  |  | sanity: exact_recall | 0.0 | < 90.0 | PASS |  |
| pii_free | 24 | pii_free_fp_rate | 20.8 | < 15.0 | FAIL | yes |
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

### Slices: probes (exact recall / overlap recall / split spans)

| Slice | Value | Gold | R |
|---|---|---|---|
| entity:case | abl | 21 | 52.4 / 52.4 / 0 |
| entity:case | acc_consonant | 21 | 47.6 / 66.7 / 4 |
| entity:case | acc_vowel | 21 | 66.7 / 85.7 / 4 |
| entity:case | apostrophe | 21 | 0.0 / 52.4 / 11 |
| entity:case | ascii_folded | 21 | 47.6 / 66.7 / 4 |
| entity:case | cop | 21 | 33.3 / 47.6 / 3 |
| entity:case | dat | 21 | 81.0 / 100.0 / 4 |
| entity:case | gen | 33 | 87.9 / 87.9 / 0 |
| entity:case | ins | 21 | 0.0 / 0.0 / 0 |
| entity:case | loc | 21 | 100.0 / 100.0 / 0 |
| entity:case | pl | 21 | 85.7 / 100.0 / 3 |
| entity:case | pl_case | 21 | 33.3 / 81.0 / 10 |
| entity:case | rel | 21 | 0.0 / 0.0 / 0 |
| entity:entity_noise | case_or_ascii | 12 | 0.0 / 0.0 / 0 |
| entity:variant | ascii_or_ru_latin | 16 | 93.8 / 100.0 / 1 |
| entity:variant | az_latin | 16 | 100.0 / 100.0 / 0 |
| entity:variant | cyrillic | 16 | 93.8 / 100.0 / 1 |
| entity:variant | en_latin | 16 | 87.5 / 93.8 / 1 |
| entity:variant | tr_or_other | 16 | 87.5 / 87.5 / 0 |
| doc:control | True | 0 | – / – / 0 |
| doc:family | anchor_distance | 12 | 33.3 / 50.0 / 2 |
| doc:family | bare_name | 45 | 33.3 / 42.2 / 4 |
| doc:family | building_vs_room | 12 | 100.0 / 100.0 / 0 |
| doc:family | casing_noise | 24 | 37.5 / 37.5 / 0 |
| doc:family | decoy_age | 12 | 100.0 / 100.0 / 0 |
| doc:family | decoy_card_iccid_iban | 12 | 75.0 / 100.0 / 3 |
| doc:family | decoy_cvv | 12 | 100.0 / 100.0 / 0 |
| doc:family | decoy_date | 12 | 100.0 / 100.0 / 0 |
| doc:family | decoy_fin | 12 | 100.0 / 100.0 / 0 |
| doc:family | decoy_ipv4 | 12 | 100.0 / 100.0 / 0 |
| doc:family | decoy_ipv6_mac | 12 | 100.0 / 100.0 / 0 |
| doc:family | decoy_names_as_org | 12 | 100.0 / 100.0 / 0 |
| doc:family | decoy_time | 12 | 100.0 / 100.0 / 0 |
| doc:family | decoy_voen_passport_id | 12 | 100.0 / 100.0 / 0 |
| doc:family | decoy_zip | 12 | 100.0 / 100.0 / 0 |
| doc:family | fmt_csv | 48 | 75.0 / 95.8 / 10 |
| doc:family | fmt_csv_noheader | 48 | 50.0 / 79.2 / 12 |
| doc:family | fmt_dialogue | 48 | 75.0 / 100.0 / 12 |
| doc:family | fmt_json | 48 | 75.0 / 97.9 / 11 |
| doc:family | fmt_kv | 48 | 77.1 / 100.0 / 11 |
| doc:family | fmt_log | 48 | 54.2 / 100.0 / 12 |
| doc:family | fmt_pipe | 48 | 81.2 / 100.0 / 9 |
| doc:family | inflected_anchor | 12 | 66.7 / 75.0 / 1 |
| doc:family | ipv6_vs_mac | 24 | 83.3 / 87.5 / 1 |
| doc:family | licence_vs_id | 24 | 50.0 / 50.0 / 0 |
| doc:family | name_homographs | 32 | 100.0 / 100.0 / 0 |
| doc:family | name_transliteration_variants | 80 | 92.5 / 96.2 / 3 |
| doc:family | nonpii_ids | 12 | 91.7 / 100.0 / 0 |
| doc:family | pem | 10 | 0.0 / 100.0 / 10 |
| doc:family | pii_free | 0 | – / – / 0 |
| doc:family | prose_card | 12 | 16.7 / 16.7 / 0 |
| doc:family | prose_date | 12 | 16.7 / 16.7 / 0 |
| doc:family | prose_iban | 12 | 0.0 / 8.3 / 1 |
| doc:family | punct_touching | 12 | 66.7 / 100.0 / 1 |
| doc:family | sentence_initial_nouns | 12 | 91.7 / 91.7 / 0 |
| doc:family | single_entity | 12 | 66.7 / 66.7 / 0 |
| doc:family | spaced_card_iban | 12 | 58.3 / 91.7 / 4 |
| doc:family | spaced_phone | 12 | 41.7 / 41.7 / 0 |
| doc:family | suffixed_entities | 273 | 48.7 / 64.5 / 43 |
| doc:family | token_vs_key | 24 | 62.5 / 62.5 / 0 |
| … | 98 more rows in the JSON | | |

Calibration (score bins vs precision) is in the JSON. It is reported only and is never used to set a threshold (A2.2).
