# Scoreboard: new_langs

| | |
|---|---|
| Model | `your-hf-org/masking-multi-m1-seed42` |
| Revision SHA | `d7493a1634f3aadc4dab5cd3b8103cf070e5eff0` |
| Requested revision | `d7493a1634f3aadc4dab5cd3b8103cf070e5eff0` |
| Code git SHA | `a8fa3adb367a97d76418451b00ad59dbe03f928f` (eval/ or model/ dirty) |
| Date (UTC) | 2026-10-24T00:48:10Z |
| Device | cuda |
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
| golden_en | R | 217 | 75.5 / 98.9 / 85.7 | 94.5 | 86.0 | 0.1 | 50.0 | 1 | 0.0 (0.0) | – | – | 52.1 |
| golden_en | M | 217 | 75.5 / 98.9 / 85.7 | 94.5 | 86.0 | 0.1 | 50.0 | 1 | 0.0 (0.0) | – | – | 52.1 |
| lang_tr | R | 1000 | 90.5 / 97.1 / 93.7 | 96.8 | 94.2 | 1.7 | 40.0 | 7 | 0.0 (0.0) | – | 5.2 | 80.0 |
| lang_tr | M | 1000 | 90.7 / 97.1 / 93.8 | 96.8 | 94.3 | 1.7 | 34.8 | 5 | 0.0 (0.0) | – | 5.2 | 80.2 |
| lang_ru | R | 1000 | 93.7 / 96.4 / 95.0 | 97.5 | 95.5 | 2.5 | 78.9 | 14 | 0.0 (0.0) | – | 3.6 | 78.2 |
| lang_ru | M | 1000 | 93.9 / 96.4 / 95.1 | 97.5 | 95.5 | 2.5 | 71.4 | 10 | 0.0 (0.0) | – | 3.6 | 78.4 |

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
