### Automatic release check: `/private/tmp/claude-501/-Users-user-HAL-X-pii-masking-model/692921e0-3cc7-4991-bb18-a10eb02fa39f/scratchpad/v3_puncttok` @ `local-s`

`scripts/release_check.sh`, 2026-10-14 17:42 UTC, code `c195e64`. Track R decides; shadow-dev: not scored.

**Verdict: not released.** Passes **4 of 14** blocking rules; fails C3, C4, C13; not scored: A1, A2, A3, A4, A5, A6, E3.

| # | Rule | Blocking | Result | Status |
|---|---|---|---|---|
| A1 | Micro F1 ≥ 82 | yes | shadow-dev not scored | not scored |
| A2 | Weakest label F1 ≥ 65 | yes | shadow-dev not scored | not scored |
| A3 | Token, IPv6, licence F1 ≥ 75 each | yes | shadow-dev not scored | not scored |
| A4 | Look-alike trigger rate < 8% | yes | shadow-dev not scored | not scored |
| A5 | PII-free documents masked < 15% | yes | shadow-dev not scored | not scored |
| A6 | Recall guard vs checkpoint 1 | yes | shadow-dev not scored | not scored |
| A7 | EN / TR / RU regression | no | not applied: Azerbaijani-only model (D-23a) | n/a |
| A8 | Benchmark errors fixed (appendix) | no | not run by this script | report |
| A9 | Sealed set, once, on the final candidate | no | untouched (final candidate only, P3-11) | n/a |
| B1 | Benchmark F1 ≥ checkpoint 1 + 2 | yes | 93.5 vs 68.7 (needs 70.7); M 94.2 | **pass** |
| B2 | Benchmark recall guard (−1 pt) | yes | no label drops | **pass** |
| C1 | Access token vs API key | yes | 5 conditions met | **pass** |
| C2 | IPv6 vs MAC | yes | 5 conditions met | **pass** |
| C3 | Licence vs ID card | yes | licence_vs_id confusion_rate [AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER] 8.3 | **fail** |
| C4 | Look-alikes: < 15% each, < 10% overall | yes | 4 of 11 families above 15% (decoy_time 25.0%, decoy_date 33.3%, decoy_fin 44.4%, decoy_card_iccid_iban 33.3%); overall 12.1%; decoy_cvv: 12345 0/2; random 5-digit 0/5 | **fail** |
| C5 | building_vs_room, sentence_initial_nouns, nonpii_ids | no | 2 of 3 families meet their target | report |
| C6 | prose_card, prose_date, prose_iban… | no | 4 of 5 families meet their target | report |
| C7 | fmt_csv, fmt_csv_noheader, fmt_json… | no | 7 of 7 families meet their target | report |
| C8 | pem, spaced_phone, spaced_card_iban | no | 2 of 3 families meet their target | report |
| C9 | suffixed_entities | no | 0 of 1 families meet their target | report |
| C10 | bare_name, name_homographs | no | 1 of 2 families meet their target | report |
| C11 | name_transliteration_variants | no | 1 of 1 families meet their target | report |
| C12 | All probe families with targets (report) | no | 34 of 52 families meet every absolute target (track R) | report |
| C13 | No family >10 pt and >3 docs worse | yes | pem char_leakage_rate 20.5 → 51.7 (10 docs worse); watched: names_list_lines | **fail** |
| D1 | runb_test vs checkpoint 1 (report) | no | runb_test not scored yet (--quick) | not scored |
| D2 | Template overfitting: gap ≤ 15 points | no | needs runb_test | not scored |
| D3 | Old vs new documents (report) | no | runb_test not scored yet | not scored |
| E1 | Real text per label (report) | no | real text not scored | not scored |
| E2 | Real-text recall guard (report) | no |  | not scored |
| E3 | Real text: 80% found, labels, precision | yes | real text not scored | not scored |
