### Automatic release check: `your-hf-org/masking-az-runb-v2-seed42-2ep` @ `937f29d`

`scripts/release_check.sh`, 2026-10-13 10:00 UTC, code `0259ef8`. Track R decides; shadow-dev: scored 2026-10-13 with the D-42 list.

**Verdict: not released.** Passes **5 of 14** blocking rules; fails A2, A4, A5, A6, B2, C3, C4, C13, E3.

| # | Rule | Blocking | Result | Status |
|---|---|---|---|---|
| A1 | Micro F1 ≥ 82 | yes | 82.9 (checkpoint 1 66.9) [scored 2026-10-13 with the D-42 list] | **pass** |
| A2 | Weakest label F1 ≥ 65 | yes | 36.6 (IBAN) | **fail** |
| A3 | Token, IPv6, licence F1 ≥ 75 each | yes | ACCESS_TOKEN 78.8, IPV6_ADDRESS 79.3, AZ_DRIVER_LICENSE_NUMBER 87.5 | **pass** |
| A4 | Look-alike trigger rate < 8% | yes | 16.3% (with the D-42 items: 16.4%) | **fail** |
| A5 | PII-free documents masked < 15% | yes | 47.3% (with the D-42 items: 49.5%; their documents out of the count: 47.5%) | **fail** |
| A6 | Recall guard (no label −1 pt) | yes | 6 labels: IBAN 52.4 → 32.8, AZ_FIN 94.7 → 83.0, PAYMENT_CARD_NUMBER 90.1 → 78.9, AZ_VOEN 91.5 → 88.1, BUILDINGNUM 85.9 → 83.3, AZ_PASSPORT_NUMBER 95.1 → 93.4; M: 6 labels | **fail** |
| A7 | EN / TR / RU regression | no | not applied: Azerbaijani-only model (D-23a) | n/a |
| A8 | Benchmark errors fixed (appendix) | no | not run by this script | report |
| A9 | Sealed set, once, on the final candidate | no | untouched (final candidate only, P3-11) | n/a |
| B1 | Benchmark F1 ≥ checkpoint 1 + 2 | yes | 88.9 vs 68.7 (needs 70.7); M 92.0 | **pass** |
| B2 | Benchmark recall guard (−1 pt) | yes | 3 labels: AZ_FIN 94.7 → 68.1, CARD_SECURITY_CODE 93.9 → 70.6, ZIPCODE 80.5 → 79.5 | **fail** |
| C1 | Access token vs API key | yes | 5 conditions met | **pass** |
| C2 | IPv6 vs MAC | yes | 5 conditions met | **pass** |
| C3 | Licence vs ID card | yes | licence_vs_id confusion_rate [AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER] 16.7; licence_vs_id confusion_rate [AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER] 8.3 | **fail** |
| C4 | Look-alikes: < 15% each, < 10% overall | yes | 7 of 11 families above 15% (decoy_cvv 100.0%, decoy_time 41.7%, decoy_age 41.7%, decoy_date 100.0%, decoy_zip 66.7%, decoy_card_iccid_iban 33.3%, decoy_names_as_org 16.7%); overall 35.5% | **fail** |
| C5 | building_vs_room, sentence_initial_nouns, nonpii_ids | no | 2 of 3 families meet their target | report |
| C6 | prose_card, prose_date, prose_iban… | no | 1 of 5 families meet their target | report |
| C7 | fmt_csv, fmt_csv_noheader, fmt_json… | no | 2 of 7 families meet their target | report |
| C8 | pem, spaced_phone, spaced_card_iban | no | 2 of 3 families meet their target | report |
| C9 | suffixed_entities | no | 0 of 1 families meet their target | report |
| C10 | bare_name, name_homographs | no | 1 of 2 families meet their target | report |
| C11 | name_transliteration_variants | no | 1 of 1 families meet their target | report |
| C12 | All probe families with targets (report) | no | 19 of 52 families meet every absolute target (track R) | report |
| C13 | No family >10 pt and >3 docs worse | yes | pem char_leakage_rate 20.5 → 37.4 (8 docs worse); single_entity exact_f1 64.0 → 46.2 (7 docs worse); watched: contrast_token_key, fmt_csv_noheader, foreign_names, names_list_lines, villages | **fail** |
| D1 | runb_test vs checkpoint 1 (report) | no | R 96.5 / M 99.0 (checkpoint 1 85.5 / 88.1); PII-free FP 1.8% | report |
| D2 | Template overfitting: gap ≤ 15 points | no | vs real text 23.2 points; vs benchmark 7.6 points | **flagged** |
| D3 | Old vs new documents (report) | no | old 96.5 / new 96.6 | report |
| E1 | Real text per label (report) | no | 144 of 228 found (checkpoint 1 68); labels finding fewer: none | report |
| E2 | Real-text recall guard (report) | no | see E1 | report |
| E3 | Real text: 80% found, labels, precision | yes | (1) 63.2% found FAIL; (2) CITY 22 vs 12 of 27, GIVENNAME 26 vs 18 of 93, SURNAME 60 vs 14 of 67, TELEPHONENUM 10 vs 9 of 10 ok; (3) precision 87.3% ok | **fail** |
