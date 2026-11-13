### Automatic release check: `your-hf-org/masking-az-runb-v4.1-seed42` @ `502598c`

`scripts/release_check.sh`, 2026-10-19 11:29 UTC, code `c5c1614`. Track R decides; shadow-dev: not scored (shadow-dev not restored, no saved report).

**Verdict: not released.** Passes **6 of 14** blocking rules; fails C4; not scored: A1, A2, A3, A4, A5, A6, E3.

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
| B1 | Benchmark F1 ≥ checkpoint 1 + 2 | yes | 97.0 vs 69.5 (needs 71.5); with the policy items 96.0 vs 68.7; M 96.3 | **pass** |
| B2 | Benchmark recall guard (−1 pt) | yes | no label drops | **pass** |
| C1 | Access token vs API key | yes | 5 conditions met | **pass** |
| C2 | IPv6 vs MAC | yes | 5 conditions met | **pass** |
| C3 | Licence vs ID card | yes | 4 conditions met | **pass** |
| C4 | Look-alikes: < 15% each, < 10% overall | yes | 4 of 11 families above 15% (decoy_time 50.0%, decoy_date 25.0%, decoy_fin 40.0%, decoy_ipv4 16.7%); overall 13.8%; decoy_cvv: 12345 0/2; random 5-digit 1/5 | **fail** |
| C5 | building_vs_room, sentence_initial_nouns, nonpii_ids | no | 2 of 3 families meet their target | report |
| C6 | prose_card, prose_date, prose_iban… | no | 5 of 5 families meet their target | report |
| C7 | fmt_csv, fmt_csv_noheader, fmt_json… | no | 5 of 7 families meet their target | report |
| C8 | pem, spaced_phone, spaced_card_iban | no | 3 of 3 families meet their target | report |
| C9 | suffixed_entities | no | 0 of 1 families meet their target | report |
| C10 | bare_name, name_homographs | no | 1 of 2 families meet their target | report |
| C11 | name_transliteration_variants | no | 0 of 1 families meet their target | report |
| C12 | All probe families with targets (report) | no | 32 of 52 families meet every absolute target (track R) | report |
| C13 | No family >10 pt and >3 docs worse | yes | none; watched: names_list_lines | **pass** |
| D1 | runb_test vs checkpoint 1 (report) | no | R 99.0 / M 99.1 (checkpoint 1 81.7 / 84.5); PII-free FP 1.1% | report |
| D2 | Template overfitting: gap ≤ 15 points | no | vs benchmark 3.0 points | report |
| D3 | Old vs new documents (report) | no | old 99.2 / new 99.0 | report |
| E1 | Real text per label (report) | no | real text not scored | not scored |
| E2 | Real-text recall guard (report) | no |  | not scored |
| E3 | Real text: 80% found, labels, precision | yes | real text not scored | not scored |
