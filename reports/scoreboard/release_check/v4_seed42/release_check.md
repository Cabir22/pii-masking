### Automatic release check: `your-hf-org/masking-az-runb-v4-seed42` @ `e4ca178`

`scripts/release_check.sh`, 2026-10-19 08:22 UTC, code `42be032`. Track R decides; shadow-dev: scored 2026-10-19, policy list with the 15 Oct rules.

**Verdict: not released.** Passes **11 of 14** blocking rules; fails A5, C3, C4.

| # | Rule | Blocking | Result | Status |
|---|---|---|---|---|
| A1 | Micro F1 ≥ 82 | yes | 90.6 (checkpoint 1 67.1) [scored 2026-10-19, policy list with the 15 Oct rules] | **pass** |
| A2 | Weakest label F1 ≥ 65 | yes | 77.2 (CARD_SECURITY_CODE) | **pass** |
| A3 | Token, IPv6, licence F1 ≥ 75 each | yes | ACCESS_TOKEN 86.6, IPV6_ADDRESS 79.9, AZ_DRIVER_LICENSE_NUMBER 92.9 | **pass** |
| A4 | Look-alike trigger rate < 8% | yes | 6.7% (with the policy-list items: 9.8%) | **pass** |
| A5 | PII-free documents masked < 15% | yes | 23.2% (with the policy-list items: 36.4%; their documents out of the count: 24.3%) | **fail** |
| A6 | Recall guard (no label −1 pt) | yes | no label drops; M: 1 labels | **pass** |
| A7 | EN / TR / RU regression | no | not applied: Azerbaijani-only model (D-23a) | n/a |
| A8 | Benchmark errors fixed (appendix) | no | not run by this script | report |
| A9 | Sealed set, once, on the final candidate | no | untouched (final candidate only, P3-11) | n/a |
| B1 | Benchmark F1 ≥ checkpoint 1 + 2 | yes | 96.1 vs 69.5 (needs 71.5); with the policy items 95.1 vs 68.7; M 95.7 | **pass** |
| B2 | Benchmark recall guard (−1 pt) | yes | no label drops | **pass** |
| C1 | Access token vs API key | yes | 5 conditions met | **pass** |
| C2 | IPv6 vs MAC | yes | 5 conditions met | **pass** |
| C3 | Licence vs ID card | yes | licence_vs_id confusion_rate [AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER] 25.0 | **fail** |
| C4 | Look-alikes: < 15% each, < 10% overall | yes | 5 of 11 families above 15% (decoy_cvv 42.9%, decoy_time 50.0%, decoy_date 58.3%, decoy_zip 25.0%, decoy_fin 20.0%); overall 18.1%; decoy_cvv: 12345 1/2; random 5-digit 2/5 | **fail** |
| C5 | building_vs_room, sentence_initial_nouns, nonpii_ids | no | 2 of 3 families meet their target | report |
| C6 | prose_card, prose_date, prose_iban… | no | 5 of 5 families meet their target | report |
| C7 | fmt_csv, fmt_csv_noheader, fmt_json… | no | 7 of 7 families meet their target | report |
| C8 | pem, spaced_phone, spaced_card_iban | no | 3 of 3 families meet their target | report |
| C9 | suffixed_entities | no | 0 of 1 families meet their target | report |
| C10 | bare_name, name_homographs | no | 2 of 2 families meet their target | report |
| C11 | name_transliteration_variants | no | 1 of 1 families meet their target | report |
| C12 | All probe families with targets (report) | no | 34 of 52 families meet every absolute target (track R) | report |
| C13 | No family >10 pt and >3 docs worse | yes | none; watched: names_list_lines | **pass** |
| D1 | runb_test vs checkpoint 1 (report) | no | runb_test not scored yet (--quick) | not scored |
| D2 | Template overfitting: gap ≤ 15 points | no | needs runb_test | not scored |
| D3 | Old vs new documents (report) | no | runb_test not scored yet | not scored |
| E1 | Real text per label (report) | no | 202 of 228 found (checkpoint 1 68); labels finding fewer: none | report |
| E2 | Real-text recall guard (report) | no | see E1 | report |
| E3 | Real text: 80% found, labels, precision | yes | (1) 88.6% found ok; (2) CITY 15 vs 12 of 27, GIVENNAME 88 vs 18 of 93, SURNAME 62 vs 14 of 67, TELEPHONENUM 10 vs 9 of 10 ok; (3) precision 93.1% ok | **pass** |
