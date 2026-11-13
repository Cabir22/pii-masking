### Automatic release check: `your-hf-org/masking-az-runb-v4.2-seed42` @ `223e54e`

`scripts/release_check.sh`, 2026-10-23 09:02 UTC, code `a8fa3ad`. Track M decides; shadow-dev: track M with validity-2, scored 2026-10-23.

**Verdict: not released.** Passes **13 of 14** blocking rules; fails A6.

| # | Rule | Blocking | Result | Status |
|---|---|---|---|---|
| A1 | Micro F1 ≥ 82 | yes | 93.8 (checkpoint 1 72.4) [track M with validity-2, scored 2026-10-23] | **pass** |
| A2 | Weakest label F1 ≥ 65 | yes | 80.7 (CARD_SECURITY_CODE) | **pass** |
| A3 | Token, IPv6, licence F1 ≥ 75 each | yes | ACCESS_TOKEN 94.1, IPV6_ADDRESS 82.5, AZ_DRIVER_LICENSE_NUMBER 97.5 | **pass** |
| A4 | Look-alike trigger rate < 8% | yes | 2.6% (with the policy-list items: 5.6%) | **pass** |
| A5 | PII-free documents masked < 15% | yes | 9.3% (with the policy-list items: 23.2%; their documents out of the count: 10.5%) | **pass** |
| A6 | Recall guard (no label −1 pt) | yes | 2 labels: IPV6_ADDRESS 83.1 → 81.4, PAYMENT_CARD_NUMBER 92.5 → 91.5 | **fail** |
| A7 | EN / TR / RU regression | no | not applied: Azerbaijani-only model (D-23a) | n/a |
| A8 | Benchmark errors fixed (appendix) | no | not run by this script | report |
| A9 | Sealed set, once, on the final candidate | no | untouched (final candidate only, P3-11) | n/a |
| B1 | Benchmark F1 ≥ checkpoint 1 + 2 | yes | 97.0 vs 72.1 (needs 74.1); with the policy items 96.0 vs 71.4 | **pass** |
| B2 | Benchmark recall guard (−1 pt) | yes | no label drops | **pass** |
| B3 | No label > 5 pt below the previous model | no | no previous model given (--prev-bench) | n/a |
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
| C12 | All probe families with targets (report) | no | 42 of 53 families meet every absolute target (track R) | report |
| C13 | No family >10 pt and >3 docs worse | yes | none; watched: names_list_lines | **pass** |
| D1 | runb_test vs checkpoint 1 (report) | no | runb_test not scored yet (--quick) | not scored |
| D2 | Template overfitting: gap ≤ 15 points | no | needs runb_test | not scored |
| D3 | Old vs new documents (report) | no | runb_test not scored yet | not scored |
| E1 | Real text per label (report) | no | 199 of 228 found (checkpoint 1 63); labels finding fewer: AZ_VOEN | report |
| E2 | Real-text recall guard (report) | no | see E1 | report |
| E3 | Real text: 80% found, labels, precision | yes | (1) 87.3% found ok; (2) CITY 14 vs 12 of 27, GIVENNAME 88 vs 13 of 93, SURNAME 62 vs 15 of 67, TELEPHONENUM 10 vs 10 of 10 ok; (3) precision 92.1% ok | **pass** |
