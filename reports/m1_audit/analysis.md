# m1 audit: analysis of per-document predictions

## 1. Reproduction from per-document predictions

| Subset | Model | Track | Exact P / R / F1 | TP/FP/FN |
|---|---|---|---|---|
| golden_en | m1 | M | 75.5 / 98.9 / 85.7 | 1016/329/11 |
| golden_en | m1 | R | 75.5 / 98.9 / 85.7 | 1016/329/11 |
| golden_en | ckpt1 | M | 98.1 / 99.1 / 98.6 | 1018/20/9 |
| golden_en | ckpt1 | R | 95.7 / 96.7 / 96.2 | 993/45/34 |
| names_list_lines | m1 | M | 96.6 / 100.0 / 98.3 | 171/6/0 |
| names_list_lines | m1 | R | 96.6 / 100.0 / 98.3 | 171/6/0 |
| names_list_lines | v42 | M | 96.6 / 100.0 / 98.3 | 171/6/0 |
| names_list_lines | v42 | R | 96.6 / 100.0 / 98.3 | 171/6/0 |
| names_list_lines | ckpt1 | M | 100.0 / 28.7 / 44.5 | 49/0/122 |
| names_list_lines | ckpt1 | R | 79.2 / 24.6 / 37.5 | 42/11/129 |
| bench_mac | m1 | M | 89.0 / 89.8 / 89.4 | 1141/141/130 |
| bench_mac | m1 | R | 87.6 / 89.7 / 88.6 | 1140/161/131 |
| bench_mac | v42 | M | 93.0 / 97.6 / 95.2 | 1240/94/31 |
| bench_mac | v42 | R | 92.2 / 97.6 / 94.8 | 1240/105/31 |

## 2. English

m1 predicted spans that are not exact gold matches, by category (all labels): standalone date unlabelled in gold (D-17: DATE): 192; GIVENNAME with no gold overlap: 81; SURNAME with no gold overlap: 20; DATE on other text: 8; CITY with no gold overlap: 6; MISSED gold: 6; boundary (same label, other span): 4; AGE with no gold overlap: 3; ACCESS_TOKEN with no gold overlap: 3; BUILDINGNUM with no gold overlap: 3; STREET with no gold overlap: 2; wrong type (gold SURNAME): 2; TIME with no gold overlap: 2; EMAIL with no gold overlap: 2; IPV4_ADDRESS with no gold overlap: 1

Details: `english.md`, `english_review.jsonl`.

## 3. MAC

v4.2 vs m1 per gold MAC (exact): v4.2 ok / m1 ok: 246; v4.2 ok / m1 wrong: 112; v4.2 wrong / m1 wrong: 9; v4.2 wrong / m1 ok: 7

Details: `mac.md`, `mac_cases.jsonl`.

## 4. C13

m1 documents worse than checkpoint 1 on name-list controls: 2 (> 3 needed to block). Details: `c13.md`.

