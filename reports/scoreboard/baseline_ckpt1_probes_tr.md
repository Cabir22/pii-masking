# Scoreboard: baseline_ckpt1_probes_tr

| | |
|---|---|
| Model | `your-hf-org/masking-multilingual` |
| Revision SHA | `3a0a6e5df228bdc89dd01312a728e10a78b3e3fb` |
| Requested revision | `3a0a6e5df228bdc89dd01312a728e10a78b3e3fb` |
| Code git SHA | `b1ee3ce249aa26f5d8d9ea3c79d1b109628388d7` (eval/ or model/ dirty) |
| Date (UTC) | 2026-10-20T10:40:14Z |
| Device | cpu |
| Libraries | tokenizers 0.22.2, transformers 4.57.6, torch 2.11.0+cu128, python 3.12.14 |
| Tracks | R = raw HF pipeline (simple), M = model-only product path |
| Data version | probes_tr `88b21db1b4945e97` |

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
| probes_tr | R | 354 | 53.6 / 65.5 / 58.9 | 50.7 | 69.3 | 11.2 | 51.7 | 15 | 81.2 (88.5) | – | 83.3 | 51.4 |
| probes_tr excl. policy | R | 354 | 54.8 / 65.5 / 59.7 | 52.1 | 70.2 | 11.2 | 51.7 | 15 | 79.8 (87.6) | – | 76.5 | 53.4 |
| probes_tr | M | 354 | 54.1 / 65.9 / 59.4 | 53.0 | 69.4 | 11.4 | 58.6 | 15 | 79.2 (86.5) | – | 81.4 | 52.3 |
| probes_tr excl. policy | M | 354 | 55.3 / 65.9 / 60.1 | 54.5 | 70.3 | 11.4 | 58.6 | 15 | 77.5 (85.4) | – | 74.5 | 54.2 |

### Slices: probes_tr (exact recall / overlap recall / split spans)

| Slice | Value | Gold | R | M |
|---|---|---|---|---|
| entity:case | abl | 6 | 0.0 / 66.7 / 4 | 0.0 / 66.7 / 4 |
| entity:case | acc | 6 | 0.0 / 16.7 / 1 | 0.0 / 16.7 / 1 |
| entity:case | dat | 6 | 0.0 / 0.0 / 0 | 0.0 / 0.0 / 0 |
| entity:case | gen | 6 | 0.0 / 33.3 / 2 | 0.0 / 33.3 / 2 |
| entity:case | ins | 6 | 0.0 / 33.3 / 2 | 0.0 / 16.7 / 1 |
| entity:case | loc | 6 | 0.0 / 66.7 / 4 | 0.0 / 66.7 / 4 |
| doc:family | decoy_card_iccid_iban_tr | 12 | 58.3 / 75.0 / 1 | 75.0 / 75.0 / 0 |
| doc:family | decoy_cvv_tr | 12 | 91.7 / 91.7 / 0 | 91.7 / 91.7 / 0 |
| doc:family | decoy_date_tr | 12 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | decoy_fin_tr | 12 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | decoy_ipv4_tr | 12 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | decoy_time_tr | 12 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | decoy_voen_passport_id_tr | 12 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | decoy_zip_tr | 12 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | dotted_i_caps_tr | 12 | 25.0 / 25.0 / 0 | 25.0 / 25.0 / 0 |
| doc:family | inflected_names_tr | 36 | 0.0 / 36.1 / 13 | 0.0 / 33.3 / 12 |
| doc:family | ipv6_vs_mac_tr | 24 | 100.0 / 100.0 / 0 | 95.8 / 100.0 / 1 |
| doc:family | licence_vs_id_tr | 24 | 45.8 / 50.0 / 0 | 50.0 / 50.0 / 0 |
| doc:family | line_end_ip_email_tr | 12 | 91.7 / 91.7 / 0 | 91.7 / 100.0 / 1 |
| doc:family | pii_free_places_tr | 0 | – / – / 0 | – / – / 0 |
| doc:family | time_ending_outside_tr | 12 | 91.7 / 100.0 / 1 | 83.3 / 91.7 / 1 |
| doc:family | token_vs_key_tr | 24 | 62.5 / 62.5 / 0 | 62.5 / 62.5 / 0 |
| doc:family | weekday_outside_date_tr | 12 | 0.0 / 100.0 / 0 | 0.0 / 100.0 / 0 |
| doc:lang | tr | 252 | 65.5 / 77.0 / 15 | 65.9 / 76.6 / 15 |
| doc:pair | 0 | 21 | 81.0 / 85.7 / 0 | 76.2 / 85.7 / 1 |
| doc:pair | 1 | 21 | 71.4 / 90.5 / 2 | 76.2 / 90.5 / 2 |
| doc:pair | 10 | 18 | 72.2 / 77.8 / 0 | 72.2 / 77.8 / 0 |
| doc:pair | 11 | 18 | 77.8 / 83.3 / 0 | 77.8 / 83.3 / 0 |
| doc:pair | 12 | 1 | 0.0 / 100.0 / 1 | 0.0 / 100.0 / 1 |
| doc:pair | 13 | 1 | 0.0 / 100.0 / 1 | 0.0 / 100.0 / 1 |
| doc:pair | 14 | 1 | 0.0 / 100.0 / 1 | 0.0 / 100.0 / 1 |
| doc:pair | 15 | 1 | 0.0 / 100.0 / 1 | 0.0 / 100.0 / 1 |
| doc:pair | 16 | 1 | 0.0 / 0.0 / 0 | 0.0 / 0.0 / 0 |
| doc:pair | 17 | 1 | 0.0 / 0.0 / 0 | 0.0 / 0.0 / 0 |
| doc:pair | 18 | 1 | 0.0 / 0.0 / 0 | 0.0 / 0.0 / 0 |
| doc:pair | 19 | 1 | 0.0 / 100.0 / 1 | 0.0 / 100.0 / 1 |
| doc:pair | 2 | 21 | 61.9 / 71.4 / 0 | 66.7 / 76.2 / 1 |
| doc:pair | 20 | 1 | 0.0 / 100.0 / 1 | 0.0 / 100.0 / 1 |
| doc:pair | 21 | 1 | 0.0 / 0.0 / 0 | 0.0 / 0.0 / 0 |
| doc:pair | 22 | 1 | 0.0 / 100.0 / 1 | 0.0 / 100.0 / 1 |
| doc:pair | 23 | 1 | 0.0 / 100.0 / 1 | 0.0 / 100.0 / 1 |
| doc:pair | 24 | 1 | 0.0 / 0.0 / 0 | 0.0 / 0.0 / 0 |
| doc:pair | 25 | 1 | 0.0 / 100.0 / 1 | 0.0 / 100.0 / 1 |
| doc:pair | 26 | 1 | 0.0 / 0.0 / 0 | 0.0 / 0.0 / 0 |
| doc:pair | 27 | 1 | 0.0 / 0.0 / 0 | 0.0 / 0.0 / 0 |
| doc:pair | 28 | 1 | 0.0 / 0.0 / 0 | 0.0 / 0.0 / 0 |
| doc:pair | 29 | 1 | 0.0 / 0.0 / 0 | 0.0 / 0.0 / 0 |
| doc:pair | 3 | 21 | 76.2 / 81.0 / 0 | 76.2 / 81.0 / 0 |
| doc:pair | 30 | 1 | 0.0 / 0.0 / 0 | 0.0 / 0.0 / 0 |
| doc:pair | 31 | 1 | 0.0 / 0.0 / 0 | 0.0 / 0.0 / 0 |
| doc:pair | 32 | 1 | 0.0 / 0.0 / 0 | 0.0 / 0.0 / 0 |
| doc:pair | 33 | 1 | 0.0 / 0.0 / 0 | 0.0 / 0.0 / 0 |
| doc:pair | 34 | 1 | 0.0 / 100.0 / 1 | 0.0 / 100.0 / 1 |
| doc:pair | 35 | 1 | 0.0 / 100.0 / 1 | 0.0 / 0.0 / 0 |
| doc:pair | 4 | 18 | 77.8 / 88.9 / 1 | 77.8 / 88.9 / 1 |
| doc:pair | 5 | 18 | 61.1 / 66.7 / 0 | 61.1 / 66.7 / 0 |
| doc:pair | 6 | 18 | 72.2 / 77.8 / 0 | 72.2 / 77.8 / 0 |
| doc:pair | 7 | 18 | 72.2 / 77.8 / 0 | 72.2 / 77.8 / 0 |
| doc:pair | 8 | 18 | 66.7 / 77.8 / 1 | 72.2 / 77.8 / 0 |
| doc:pair | 9 | 18 | 77.8 / 83.3 / 0 | 72.2 / 77.8 / 0 |
| … | 24 more rows in the JSON | | |

Calibration (score bins vs precision) is in the JSON. It is reported only and is never used to set a threshold (A2.2).
