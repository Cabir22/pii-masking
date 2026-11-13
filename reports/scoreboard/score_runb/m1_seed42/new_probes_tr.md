# Scoreboard: new_probes_tr

| | |
|---|---|
| Model | `your-hf-org/masking-multi-m1-seed42` |
| Revision SHA | `d7493a1634f3aadc4dab5cd3b8103cf070e5eff0` |
| Requested revision | `d7493a1634f3aadc4dab5cd3b8103cf070e5eff0` |
| Code git SHA | `a8fa3adb367a97d76418451b00ad59dbe03f928f` (eval/ or model/ dirty) |
| Date (UTC) | 2026-10-24T00:44:56Z |
| Device | cuda |
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
| probes_tr | R | 354 | 87.8 / 94.0 / 90.8 | 93.6 | 95.6 | 3.4 | 15.4 | 1 | 14.6 (14.6) | – | 13.7 | 90.7 |
| probes_tr excl. policy | R | 354 | 87.8 / 94.0 / 90.8 | 93.6 | 95.6 | 3.4 | 15.4 | 1 | 15.7 (15.7) | – | 13.7 | 90.7 |
| probes_tr | M | 354 | 90.2 / 94.4 / 92.2 | 94.5 | 96.5 | 3.4 | 0.0 | 0 | 10.4 (10.4) | – | 9.8 | 92.1 |
| probes_tr excl. policy | M | 354 | 90.2 / 94.4 / 92.2 | 94.5 | 96.5 | 3.4 | 0.0 | 0 | 11.2 (11.2) | – | 9.8 | 92.1 |

### Slices: probes_tr (exact recall / overlap recall / split spans)

| Slice | Value | Gold | R | M |
|---|---|---|---|---|
| entity:case | abl | 6 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:case | acc | 6 | 83.3 / 100.0 / 1 | 100.0 / 100.0 / 0 |
| entity:case | dat | 6 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| entity:case | gen | 6 | 83.3 / 83.3 / 0 | 83.3 / 83.3 / 0 |
| entity:case | ins | 6 | 83.3 / 83.3 / 0 | 83.3 / 83.3 / 0 |
| entity:case | loc | 6 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | decoy_card_iccid_iban_tr | 12 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | decoy_cvv_tr | 12 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | decoy_date_tr | 12 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | decoy_fin_tr | 12 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | decoy_ipv4_tr | 12 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | decoy_time_tr | 12 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | decoy_voen_passport_id_tr | 12 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | decoy_zip_tr | 12 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | dotted_i_caps_tr | 12 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | inflected_names_tr | 36 | 91.7 / 94.4 / 1 | 94.4 / 94.4 / 0 |
| doc:family | ipv6_vs_mac_tr | 24 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | licence_vs_id_tr | 24 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | line_end_ip_email_tr | 12 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | pii_free_places_tr | 0 | – / – / 0 | – / – / 0 |
| doc:family | time_ending_outside_tr | 12 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:family | token_vs_key_tr | 24 | 95.8 / 95.8 / 0 | 95.8 / 95.8 / 0 |
| doc:family | weekday_outside_date_tr | 12 | 8.3 / 100.0 / 0 | 8.3 / 100.0 / 0 |
| doc:lang | tr | 252 | 94.0 / 98.8 / 1 | 94.4 / 98.8 / 0 |
| doc:pair | 0 | 21 | 90.5 / 95.2 / 0 | 90.5 / 95.2 / 0 |
| doc:pair | 1 | 21 | 90.5 / 95.2 / 0 | 90.5 / 95.2 / 0 |
| doc:pair | 10 | 18 | 94.4 / 100.0 / 0 | 94.4 / 100.0 / 0 |
| doc:pair | 11 | 18 | 94.4 / 100.0 / 0 | 94.4 / 100.0 / 0 |
| doc:pair | 12 | 1 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:pair | 13 | 1 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:pair | 14 | 1 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:pair | 15 | 1 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:pair | 16 | 1 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:pair | 17 | 1 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:pair | 18 | 1 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:pair | 19 | 1 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:pair | 2 | 21 | 95.2 / 100.0 / 0 | 95.2 / 100.0 / 0 |
| doc:pair | 20 | 1 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:pair | 21 | 1 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:pair | 22 | 1 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:pair | 23 | 1 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:pair | 24 | 1 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:pair | 25 | 1 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:pair | 26 | 1 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:pair | 27 | 1 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:pair | 28 | 1 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:pair | 29 | 1 | 0.0 / 100.0 / 1 | 100.0 / 100.0 / 0 |
| doc:pair | 3 | 21 | 95.2 / 100.0 / 0 | 95.2 / 100.0 / 0 |
| doc:pair | 30 | 1 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:pair | 31 | 1 | 0.0 / 0.0 / 0 | 0.0 / 0.0 / 0 |
| doc:pair | 32 | 1 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:pair | 33 | 1 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:pair | 34 | 1 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:pair | 35 | 1 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:pair | 4 | 18 | 94.4 / 100.0 / 0 | 94.4 / 100.0 / 0 |
| doc:pair | 5 | 18 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:pair | 6 | 18 | 94.4 / 100.0 / 0 | 94.4 / 100.0 / 0 |
| doc:pair | 7 | 18 | 94.4 / 100.0 / 0 | 94.4 / 100.0 / 0 |
| doc:pair | 8 | 18 | 94.4 / 100.0 / 0 | 94.4 / 100.0 / 0 |
| doc:pair | 9 | 18 | 94.4 / 100.0 / 0 | 94.4 / 100.0 / 0 |
| … | 24 more rows in the JSON | | |

Calibration (score bins vs precision) is in the JSON. It is reported only and is never used to set a threshold (A2.2).
