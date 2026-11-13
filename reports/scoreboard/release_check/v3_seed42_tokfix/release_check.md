### Automatic release check: `your-hf-org/masking-az-runb-v3-seed42` @ `717b010`

`scripts/release_check.sh`, 2026-10-15 15:54 UTC, code `ff70e89`. Track R decides; shadow-dev: saved report 2026-10-15 (not restored).

**Verdict: not released.** Passes **9 of 14** blocking rules; fails A4, A5, A6, C3, C4.

| # | Rule | Blocking | Result | Status |
|---|---|---|---|---|
| A1 | Micro F1 ≥ 82 | yes | 89.3 (checkpoint 1 67.1) [saved report 2026-10-15 (not restored)] | **pass** |
| A2 | Weakest label F1 ≥ 65 | yes | 71.1 (CARD_SECURITY_CODE) | **pass** |
| A3 | Token, IPv6, licence F1 ≥ 75 each | yes | ACCESS_TOKEN 80.2, IPV6_ADDRESS 77.9, AZ_DRIVER_LICENSE_NUMBER 94.7 | **pass** |
| A4 | Look-alike trigger rate < 8% | yes | 9.3% (with the D-42/D-51e items: 9.9%) | **fail** |
| A5 | PII-free documents masked < 15% | yes | 35.8% (with the D-42/D-51e items: 40.6%; their documents out of the count: 36.5%) | **fail** |
| A6 | Recall guard (no label −1 pt) | yes | 2 labels: PAYMENT_CARD_NUMBER 90.1 → 76.5, TIME 75.7 → 73.5; M: 2 labels | **fail** |
| A7 | EN / TR / RU regression | no | not applied: Azerbaijani-only model (D-23a) | n/a |
| A8 | Benchmark errors fixed (appendix) | no | not run by this script | report |
| A9 | Sealed set, once, on the final candidate | no | untouched (final candidate only, P3-11) | n/a |
| B1 | Benchmark F1 ≥ checkpoint 1 + 2 | yes | 94.5 vs 69.2 (needs 71.2); with the D-51e items 93.5 vs 68.7; M 94.2 | **pass** |
| B2 | Benchmark recall guard (−1 pt) | yes | no label drops | **pass** |
| C1 | Access token vs API key | yes | 5 conditions met | **pass** |
| C2 | IPv6 vs MAC | yes | 5 conditions met | **pass** |
| C3 | Licence vs ID card | yes | licence_vs_id confusion_rate [AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER] 8.3 | **fail** |
| C4 | Look-alikes: < 15% each, < 10% overall | yes | 3 of 11 families above 15% (decoy_time 25.0%, decoy_date 33.3%, decoy_fin 44.4%); overall 9.2%; decoy_cvv: 12345 0/2; random 5-digit 0/5 | **fail** |
| C5 | building_vs_room, sentence_initial_nouns, nonpii_ids | no | 2 of 3 families meet their target | report |
| C6 | prose_card, prose_date, prose_iban… | no | 4 of 5 families meet their target | report |
| C7 | fmt_csv, fmt_csv_noheader, fmt_json… | no | 7 of 7 families meet their target | report |
| C8 | pem, spaced_phone, spaced_card_iban | no | 3 of 3 families meet their target | report |
| C9 | suffixed_entities | no | 0 of 1 families meet their target | report |
| C10 | bare_name, name_homographs | no | 1 of 2 families meet their target | report |
| C11 | name_transliteration_variants | no | 1 of 1 families meet their target | report |
| C12 | All probe families with targets (report) | no | 35 of 52 families meet every absolute target (track R) | report |
| C13 | No family >10 pt and >3 docs worse | yes | none; watched: names_list_lines | **pass** |
| D1 | runb_test vs checkpoint 1 (report) | no | R 98.8 / M 98.9 (checkpoint 1 85.5 / 88.1); PII-free FP 3.7% | report |
| D2 | Template overfitting: gap ≤ 15 points | no | vs real text 10.1 points; vs benchmark 5.4 points | report |
| D3 | Old vs new documents (report) | no | old 98.9 / new 98.7 | report |
| E1 | Real text per label (report) | no | 196 of 228 found (checkpoint 1 68); labels finding fewer: none | report |
| E2 | Real-text recall guard (report) | no | see E1 | report |
| E3 | Real text: 80% found, labels, precision | yes | (1) 86.0% found ok; (2) CITY 21 vs 12 of 27, GIVENNAME 79 vs 18 of 93, SURNAME 61 vs 14 of 67, TELEPHONENUM 10 vs 9 of 10 ok; (3) precision 91.6% ok | **pass** |
