### Automatic release check: `your-hf-org/masking-multi-m1-seed42` @ `d7493a1`

`scripts/release_check.sh`, 2026-10-24 00:50 UTC, code `a8fa3ad`. Track M decides; shadow-dev: scored 2026-10-24 on our server, track M (validity-2).

**Verdict: not released.** Passes **13 of 17** blocking rules; fails A6, A7, A10, B3.

| # | Rule | Blocking | Result | Status |
|---|---|---|---|---|
| A1 | Micro F1 ≥ 82 | yes | 93.8 (checkpoint 1 72.4) [scored 2026-10-24 on our server, track M (validity-2)] | **pass** |
| A2 | Weakest label F1 ≥ 65 | yes | 80.9 (CARD_SECURITY_CODE) | **pass** |
| A3 | Token, IPv6, licence F1 ≥ 75 each | yes | ACCESS_TOKEN 94.0, IPV6_ADDRESS 83.1, AZ_DRIVER_LICENSE_NUMBER 98.3 | **pass** |
| A4 | Look-alike trigger rate < 8% | yes | 2.5% (with the policy-list items: 5.6%) | **pass** |
| A5 | PII-free documents masked < 15% | yes | 6.9% (with the policy-list items: 21.0%; their documents out of the count: 7.9%) | **pass** |
| A6 | Recall guard (no label −1 pt) | yes | 1 labels: AZ_ID_CARD_NUMBER 98.7 → 95.8 | **fail** |
| A7 | EN / TR / RU ≤ 1 point below checkpoint 1 (D-46b) | yes | EN: translated 98.7 → 85.7 FAIL, independent 32.7 → 78.3; TR: translated 89.4 → 93.8, independent 19.7 → 60.9; RU: translated 89.1 → 95.1, no independent set yet: translated only | **fail** |
| A10 | Azerbaijani labels vs v3, −1 pt (D-46a) | yes | shadow-dev: 6 labels: MAC_ADDRESS 97.0 → 91.5, STREET 94.6 → 89.8, GIVENNAME 96.9 → 94.0, BUILDINGNUM 92.5 → 90.2, AZ_ID_CARD_NUMBER 98.1 → 95.8, ACCESS_TOKEN 96.7 → 95.4; benchmark: 4 labels: MAC_ADDRESS 95.7 → 67.6, BUILDINGNUM 95.3 → 93.7, AZ_ID_CARD_NUMBER 99.0 → 97.7, ZIPCODE 99.7 → 98.4 | **fail** |
| A8 | Benchmark errors fixed (appendix) | no | not run by this script | report |
| A9 | Sealed set, once, on the final candidate | no | untouched (final candidate only, P3-11) | n/a |
| B1 | Benchmark F1 ≥ checkpoint 1 + 2 | yes | 96.4 vs 72.1 (needs 74.1); with the policy items 95.4 vs 71.4; R 94.8 | **pass** |
| B2 | Benchmark recall guard (−1 pt) | yes | no label drops | **pass** |
| B3 | No label > 5 pt below the previous model | yes | 1 labels: MAC_ADDRESS 95.6 → 74.1 (vs v4.2, policy items out) | **fail** |
| C1 | Access token vs API key | yes | 5 conditions met | **pass** |
| C2 | IPv6 vs MAC | yes | 5 conditions met | **pass** |
| C3 | Licence vs ID card | yes | 4 conditions met | **pass** |
| C4 | Look-alikes: < 15% each, < 10% overall | yes | 0 of 11 families above 15%; overall 0.0%; decoy_cvv: 12345 0/2; random 5-digit 0/5 | **pass** |
| C5 | building_vs_room, sentence_initial_nouns, nonpii_ids | no | 2 of 3 families meet their target | report |
| C6 | prose_card, prose_date, prose_iban… | no | 5 of 5 families meet their target | report |
| C7 | fmt_csv, fmt_csv_noheader, fmt_json… | no | 7 of 7 families meet their target | report |
| C8 | pem, spaced_phone, spaced_card_iban | no | 3 of 3 families meet their target | report |
| C9 | suffixed_entities | no | 0 of 1 families meet their target | report |
| C10 | bare_name, name_homographs | no | 2 of 2 families meet their target | report |
| C11 | name_transliteration_variants | no | 1 of 1 families meet their target | report |
| C12 | All probe families with targets (report) | no | 40 of 53 families meet every absolute target (track R) | report |
| C13 | No family >10 pt and >3 docs worse | yes | none; watched: names_list_lines | **pass** |
| D1 | runb_test vs checkpoint 1 (report) | no | runb_test not scored yet (--quick) | not scored |
| D2 | Template overfitting: gap ≤ 15 points | no | needs runb_test | not scored |
| D3 | Old vs new documents (report) | no | runb_test not scored yet | not scored |
| E1 | Real text per label (report) | no | 206 of 228 found (checkpoint 1 63); labels finding fewer: none | report |
| E2 | Real-text recall guard (report) | no | see E1 | report |
| E3 | Real text: 80% found, labels, precision | yes | (1) 90.4% found ok; (2) CITY 16 vs 12 of 27, GIVENNAME 90 vs 13 of 93, SURNAME 63 vs 15 of 67, TELEPHONENUM 10 vs 10 of 10 ok; (3) precision 92.0% ok | **pass** |
