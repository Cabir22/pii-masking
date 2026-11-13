# Scoreboard: baseline_ckpt1_langs

| | |
|---|---|
| Model | `your-hf-org/masking-multilingual` |
| Revision SHA | `3a0a6e5df228bdc89dd01312a728e10a78b3e3fb` |
| Requested revision | `3a0a6e5df228bdc89dd01312a728e10a78b3e3fb` |
| Code git SHA | `cc764eceea0aff155bdd2cf4d627fade29218280` |
| Date (UTC) | 2026-10-20T09:11:17Z |
| Device | cpu |
| Libraries | tokenizers 0.22.2, transformers 4.57.6, torch 2.11.0+cu128, python 3.12.14 |
| Tracks | R = raw HF pipeline (simple), M = model-only product path |
| Data version | golden_en `6940dc9e2b95a0dd`; lang_tr `3ef3f93b71cb90d1`; lang_ru `3ef3f93b71cb90d1` |

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
| golden_en | R | 217 | 95.7 / 96.7 / 96.2 | 95.0 | 99.0 | 0.2 | 13.8 | 5 | 0.0 (55.6) | – | – | 82.9 |
| golden_en | M | 217 | 98.2 / 99.2 / 98.7 | 98.3 | 99.0 | 0.2 | 33.3 | 1 | 0.0 (55.6) | – | – | 92.6 |
| lang_tr | R | 1000 | 94.6 / 81.3 / 87.4 | 91.5 | 90.5 | 10.3 | 38.0 | 37 | 61.5 (84.6) | – | 0.0 | 53.7 |
| lang_tr | M | 1000 | 96.8 / 83.0 / 89.4 | 94.7 | 90.4 | 10.3 | 59.0 | 22 | 61.5 (88.5) | – | 0.0 | 55.9 |
| lang_ru | R | 1000 | 94.1 / 80.9 / 87.0 | 92.7 | 90.7 | 10.3 | 14.9 | 13 | 72.7 (90.9) | – | 0.0 | 52.3 |
| lang_ru | M | 1000 | 96.4 / 82.8 / 89.1 | 95.3 | 90.7 | 10.3 | 8.8 | 4 | 72.7 (90.9) | – | 0.6 | 54.4 |

### Slices: golden_en (exact recall / overlap recall / split spans)

| Slice | Value | Gold | R | M |
|---|---|---|---|---|
| doc:_bucket | extreme | 184 | 94.6 / 100.0 / 1 | 99.5 / 100.0 / 0 |
| doc:_bucket | long | 223 | 96.4 / 98.7 / 3 | 99.1 / 99.1 / 0 |
| doc:_bucket | medium | 132 | 97.7 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_bucket | short | 82 | 97.6 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_bucket | very_long | 357 | 97.8 / 99.4 / 0 | 98.9 / 99.2 / 0 |
| doc:_bucket | very_short | 49 | 93.9 / 100.0 / 1 | 98.0 / 100.0 / 1 |
| doc:_register | anxious and confused | 101 | 99.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_register | apologetic | 61 | 95.1 / 98.4 / 0 | 98.4 / 98.4 / 0 |
| doc:_register | bureaucratic and officious | 79 | 97.5 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_register | casual with typos and abbreviations | 64 | 90.6 / 96.9 / 2 | 98.4 / 98.4 / 0 |
| doc:_register | empathetic customer-service | 62 | 98.4 / 98.4 / 0 | 98.4 / 98.4 / 0 |
| doc:_register | formal and businesslike | 75 | 96.0 / 98.7 / 0 | 96.0 / 97.3 / 0 |
| doc:_register | friendly with light humour | 57 | 96.5 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_register | frustrated and complaining | 52 | 98.1 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_register | matter-of-fact administrative | 78 | 97.4 / 100.0 / 1 | 98.7 / 100.0 / 0 |
| doc:_register | polite but firm | 73 | 95.9 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_register | technical and precise | 76 | 98.7 / 100.0 / 1 | 100.0 / 100.0 / 0 |
| doc:_register | terse and clipped | 67 | 95.5 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_register | urgent and escalating | 87 | 98.9 / 100.0 / 1 | 98.9 / 100.0 / 1 |
| doc:_register | warm and conversational | 95 | 94.7 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:lang | en | 1027 | 96.7 / 99.5 / 5 | 99.2 / 99.5 / 1 |
| doc:split |  | 1027 | 96.7 / 99.5 / 5 | 99.2 / 99.5 / 1 |
| doc:density | 1 | 63 | 96.8 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:density | 2-3 | 145 | 95.9 / 100.0 / 1 | 99.3 / 100.0 / 1 |
| doc:density | 4-6 | 202 | 97.0 / 99.5 / 0 | 99.0 / 99.5 / 0 |
| doc:density | 7+ | 617 | 96.8 / 99.4 / 4 | 99.2 / 99.4 / 0 |

### Slices: lang_tr (exact recall / overlap recall / split spans)

| Slice | Value | Gold | R | M |
|---|---|---|---|---|
| doc:_bucket | extreme | 203 | 71.9 / 76.4 / 5 | 72.9 / 76.8 / 5 |
| doc:_bucket | long | 1376 | 82.1 / 84.2 / 9 | 83.5 / 84.0 / 4 |
| doc:_bucket | medium | 976 | 81.8 / 83.9 / 11 | 82.7 / 83.9 / 6 |
| doc:_bucket | short | 476 | 84.2 / 87.0 / 5 | 85.9 / 87.2 / 4 |
| doc:_bucket | very_long | 831 | 79.3 / 83.4 / 6 | 82.7 / 83.3 / 2 |
| doc:_bucket | very_short | 154 | 85.1 / 88.3 / 1 | 87.7 / 88.3 / 1 |
| doc:_register | anxious and confused | 274 | 89.8 / 92.7 / 6 | 90.9 / 92.7 / 4 |
| doc:_register | apologetic | 203 | 88.2 / 91.1 / 3 | 90.1 / 91.1 / 2 |
| doc:_register | bureaucratic and officious | 197 | 77.7 / 80.2 / 1 | 79.7 / 79.7 / 0 |
| doc:_register | casual with typos and abbreviations | 389 | 80.7 / 87.1 / 3 | 86.4 / 86.9 / 0 |
| doc:_register | empathetic customer-service | 206 | 87.4 / 89.8 / 1 | 88.8 / 90.3 / 1 |
| doc:_register | formal and businesslike | 322 | 76.7 / 78.9 / 2 | 78.3 / 78.9 / 1 |
| doc:_register | friendly with light humour | 293 | 86.7 / 89.4 / 3 | 88.4 / 89.4 / 3 |
| doc:_register | frustrated and complaining | 265 | 83.0 / 84.9 / 0 | 84.2 / 84.9 / 0 |
| doc:_register | matter-of-fact administrative | 343 | 76.4 / 79.9 / 3 | 79.0 / 79.9 / 0 |
| doc:_register | polite but firm | 294 | 80.3 / 83.3 / 8 | 80.6 / 83.3 / 8 |
| doc:_register | technical and precise | 301 | 78.1 / 79.1 / 0 | 78.7 / 79.1 / 0 |
| doc:_register | terse and clipped | 334 | 68.0 / 70.4 / 3 | 70.1 / 70.1 / 0 |
| doc:_register | urgent and escalating | 325 | 86.8 / 87.4 / 0 | 87.1 / 87.4 / 1 |
| doc:_register | warm and conversational | 270 | 85.2 / 88.1 / 4 | 85.6 / 88.1 / 2 |
| doc:lang | tr | 4016 | 81.3 / 84.1 / 37 | 83.0 / 84.0 / 22 |
| doc:split | test | 4016 | 81.3 / 84.1 / 37 | 83.0 / 84.0 / 22 |
| doc:density | 0 | 0 | – / – / 0 | – / – / 0 |
| doc:density | 1 | 177 | 62.7 / 66.1 / 3 | 65.5 / 66.1 / 1 |
| doc:density | 2-3 | 669 | 77.3 / 80.3 / 5 | 79.4 / 80.3 / 2 |
| doc:density | 4-6 | 936 | 84.1 / 86.5 / 12 | 85.1 / 86.6 / 9 |
| doc:density | 7+ | 2234 | 82.8 / 85.6 / 17 | 84.6 / 85.5 / 10 |

### Slices: lang_ru (exact recall / overlap recall / split spans)

| Slice | Value | Gold | R | M |
|---|---|---|---|---|
| doc:_bucket | extreme | 249 | 70.3 / 75.9 / 0 | 75.9 / 75.9 / 0 |
| doc:_bucket | long | 1406 | 80.9 / 84.0 / 2 | 82.4 / 84.0 / 1 |
| doc:_bucket | medium | 1019 | 79.7 / 82.7 / 5 | 80.9 / 82.6 / 2 |
| doc:_bucket | short | 429 | 80.9 / 85.1 / 4 | 83.4 / 84.8 / 0 |
| doc:_bucket | very_long | 775 | 85.2 / 87.9 / 1 | 87.0 / 88.0 / 1 |
| doc:_bucket | very_short | 115 | 87.8 / 92.2 / 1 | 91.3 / 93.0 / 0 |
| doc:_register | anxious and confused | 305 | 91.5 / 93.1 / 2 | 92.1 / 93.1 / 1 |
| doc:_register | apologetic | 269 | 81.4 / 84.4 / 0 | 83.6 / 84.4 / 0 |
| doc:_register | bureaucratic and officious | 273 | 76.2 / 81.0 / 1 | 80.2 / 81.0 / 0 |
| doc:_register | casual with typos and abbreviations | 356 | 87.1 / 93.3 / 0 | 91.3 / 93.3 / 0 |
| doc:_register | empathetic customer-service | 304 | 85.5 / 88.5 / 2 | 86.8 / 88.5 / 0 |
| doc:_register | formal and businesslike | 289 | 79.9 / 82.0 / 0 | 81.3 / 82.0 / 0 |
| doc:_register | friendly with light humour | 265 | 85.3 / 89.8 / 2 | 86.0 / 89.8 / 1 |
| doc:_register | frustrated and complaining | 244 | 85.7 / 89.3 / 0 | 87.3 / 89.3 / 0 |
| doc:_register | matter-of-fact administrative | 390 | 77.2 / 81.0 / 3 | 79.7 / 81.0 / 1 |
| doc:_register | polite but firm | 284 | 83.1 / 84.5 / 1 | 84.2 / 84.2 / 0 |
| doc:_register | technical and precise | 206 | 79.6 / 83.5 / 0 | 80.6 / 83.5 / 0 |
| doc:_register | terse and clipped | 293 | 64.5 / 65.5 / 0 | 64.8 / 65.5 / 0 |
| doc:_register | urgent and escalating | 295 | 74.9 / 77.3 / 1 | 76.3 / 77.6 / 0 |
| doc:_register | warm and conversational | 220 | 81.4 / 86.8 / 1 | 85.0 / 86.8 / 1 |
| doc:lang | ru | 3993 | 80.9 / 84.3 / 13 | 82.8 / 84.3 / 4 |
| doc:split | test | 3993 | 80.9 / 84.3 / 13 | 82.8 / 84.3 / 4 |
| doc:density | 0 | 0 | – / – / 0 | – / – / 0 |
| doc:density | 1 | 197 | 61.4 / 62.9 / 0 | 62.9 / 62.9 / 0 |
| doc:density | 2-3 | 638 | 78.2 / 82.6 / 5 | 80.6 / 82.6 / 0 |
| doc:density | 4-6 | 945 | 80.5 / 83.7 / 6 | 82.0 / 83.6 / 3 |
| doc:density | 7+ | 2213 | 83.6 / 86.9 / 2 | 85.6 / 86.9 / 1 |

Calibration (score bins vs precision) is in the JSON. It is reported only and is never used to set a threshold (A2.2).
