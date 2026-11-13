# m1 audit: verified public scorecard

Source: the saved reports (`~/m1_public_out/`, `reports/scoreboard/…`), rules from `eval/release_check.py`. Exact-span micro scores: an entity counts only with the exact start, end and label.

## Benchmark (Azerbaijani, first 5,000 documents of benchmark_v3, D-6)

| Model | Track | Population | TP | FP | FN | P | R | F1 |
|---|---|---|---|---|---|---|---|---|
| checkpoint 1 | M | policy items out (B1's number) | 8100 | 3849 | 2418 | 67.8 | 77.0 | **72.1** |
| checkpoint 1 | M | policy items in | 8100 | 4077 | 2418 | 66.5 | 77.0 | **71.4** |
| checkpoint 1 | R | policy items out (B1's number) | 7845 | 4227 | 2673 | 65.0 | 74.6 | **69.5** |
| checkpoint 1 | R | policy items in | 7845 | 4473 | 2673 | 63.7 | 74.6 | **68.7** |
| v4.2 | M | policy items out (B1's number) | 10251 | 414 | 267 | 96.1 | 97.5 | **96.8** |
| v4.2 | M | policy items in | 10251 | 637 | 267 | 94.1 | 97.5 | **95.8** |
| v4.2 | R | policy items out (B1's number) | 10233 | 478 | 285 | 95.5 | 97.3 | **96.4** |
| v4.2 | R | policy items in | 10233 | 703 | 285 | 93.6 | 97.3 | **95.4** |
| m1 | M | policy items out (B1's number) | 10169 | 412 | 349 | 96.1 | 96.7 | **96.4** |
| m1 | M | policy items in | 10169 | 625 | 349 | 94.2 | 96.7 | **95.4** |
| m1 | R | policy items out (B1's number) | 10147 | 516 | 371 | 95.2 | 96.5 | **95.8** |
| m1 | R | policy items in | 10147 | 734 | 371 | 93.3 | 96.5 | **94.8** |

**96.4 vs 95.4:** the same 5,000 Azerbaijani documents, track M; 96.4 leaves the policy items out (B1's definition), 95.4 keeps them in. Both are Azerbaijani. Compare m1 with v4.2 within one row type only.

## Rules (public part)

| Rule | Track | Status | Result |
|---|---|---|---|
| B1 | M | pass | 96.4 vs 72.1 (needs 74.1); with the policy items 95.4 vs 71.4; R 94.8 |
| B2 | M | pass | no label drops |
| B3 | M | fail | 1 labels: MAC_ADDRESS 95.6 → 74.1 (vs v4.2, policy items out) |
| C1 | M | pass | 5 conditions met |
| C2 | M | pass | 5 conditions met |
| C3 | M | pass | 4 conditions met |
| C4 | M | pass | 0 of 11 families above 15%; overall 0.0%; decoy_cvv: 12345 0/2; random 5-digit 0/5 |
| C13 | M | fail | names_list_lines control_fp_rate 0.0 → 50.0 (? docs worse) |
| A7 | M | fail | EN: translated 98.6 → 85.7 FAIL, no independent set yet: translated only; TR: translated 89.4 → 93.8, no independent set yet: translated only; RU: translated 89.2 → 95.1, no independent set yet: translated only |
| B1 | R | pass | 95.8 vs 69.5 (needs 71.5); with the policy items 94.8 vs 68.7; M 95.4 |
| B2 | R | pass | no label drops |
| B3 | R | fail | 1 labels: MAC_ADDRESS 95.2 → 73.3 (vs v4.2, policy items out) |
| C1 | R | pass | 5 conditions met |
| C2 | R | pass | 5 conditions met |
| C3 | R | pass | 4 conditions met |
| C4 | R | pass | 0 of 11 families above 15%; overall 0.0%; decoy_cvv: 12345 0/2; random 5-digit 0/5 |
| C13 | R | fail | names_list_lines control_fp_rate 0.0 → 50.0 (? docs worse) |
| A7 | R | fail | EN: translated 96.2 → 85.7 FAIL, no independent set yet: translated only; TR: translated 87.4 → 93.7, no independent set yet: translated only; RU: translated 87.0 → 95.0, no independent set yet: translated only |

## Translated sets (A7: exact micro F1, ≤ 1 point below checkpoint 1)

| Set | Docs | Track | checkpoint 1 P / R / F1 | m1 P / R / F1 | TP/FP/FN m1 |
|---|---|---|---|---|---|
| golden_en | 217 | M | 98.1 / 99.1 / 98.6 | 75.5 / 98.9 / **85.7** | 1016/329/11 |
| golden_en | 217 | R | 95.7 / 96.7 / 96.2 | 75.5 / 98.9 / **85.7** | 1016/329/11 |
| lang_tr | 1000 | M | 96.8 / 83.1 / 89.4 | 90.7 / 97.1 / **93.8** | 3898/401/118 |
| lang_tr | 1000 | R | 94.6 / 81.3 / 87.4 | 90.5 / 97.1 / **93.7** | 3898/408/118 |
| lang_ru | 1000 | M | 96.4 / 82.9 / 89.2 | 93.9 / 96.4 / **95.1** | 3850/251/143 |
| lang_ru | 1000 | R | 94.1 / 80.9 / 87.0 | 93.7 / 96.4 / **95.0** | 3850/259/143 |
