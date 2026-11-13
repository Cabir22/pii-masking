# v4 vs v3 on the public benchmark (same code, same policy rules)

- **Models:**
  - v4: `your-hf-org/masking-az-runb-v4-seed42` @ `e4ca178`, report in `../score_runb/v4_seed42_public/new_benchmark.json`;
  - v3: `your-hf-org/masking-az-runb-v3-seed42` @ `717b010`, re-scored from cached predictions with code `18b2a68` (`v3_bench_today.json`).
- **Scoring:** track R, exact match, first 5,000 benchmark documents, policy items excluded.
- **Totals:** micro F1 94.5 → **96.1**; precision 92.3 → 95.5; recall 96.8 → 96.7.

## Gains

| Label | F1, v3 → v4 | Change |
|---|---|---|
| PAYMENT_CARD_NUMBER | 78.6 → 99.4 | missed 109 → 2 |
| CARD_SECURITY_CODE | 73.0 → 93.6 | false alarms 204 → 40 |
| SURNAME | 90.3 → 99.9 | false alarms 83 → 0 |
| AZ_ID_CARD_NUMBER | 89.6 → 98.8 | missed 60 → 3 |
| AZ_VOEN | 90.0 → 96.7 | |
| CITY | 91.2 → 96.4 | |

## Regressions

| Label | F1, v3 → v4 | How |
|---|---|---|
| IPV6_ADDRESS | 94.5 → 76.5 | missed 5 → 78; split 13 → 45 |
| EMAIL | 99.5 → 91.6 | split 1 → 26 |
| IPV4_ADDRESS | 92.8 → 90.3 | missed 12 → 46 |
| TIME | | −1.5 |
| ZIPCODE | | −1.2 |

Suspected cause, to be confirmed: D-51h's IPv4/MAC fragment look-alikes.

## Probe rules

- **C3, licence vs ID:** now licence → ID, 3 of 12 (v3: ID → licence 8.3%).
- **C4:** 5 families above 15%, overall 18.1%. Each family has only 12 items.
- **Shadow-dev and real text:** the team.
