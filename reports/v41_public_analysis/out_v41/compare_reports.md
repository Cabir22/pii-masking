# v4 -> v4.1 from the scoreboard reports (track R, exact spans)

## Benchmark

| | v4 | v4.1 |
|---|---|---|
| all labels, policy items left out | 96.1 (P 95.5, R 96.7) | 97.0 (P 95.6, R 98.5) |
| all labels, with the policy items | 95.1 (P 93.5, R 96.7) | 96.0 (P 93.6, R 98.5) |
| IPV4_ADDRESS | 90.3 (P 95.1, R 86.1) | 84.8 (P 76.3, R 95.5) |
| IPV6_ADDRESS | 76.5 (P 81.2, R 72.4) | 97.8 (P 97.1, R 98.4) |
| EMAIL | 91.6 (P 89.8, R 93.5) | 98.5 (P 98.0, R 99.0) |
| TIME | 96.5 (P 95.5, R 97.6) | 97.4 (P 96.4, R 98.3) |
| ZIPCODE | 88.7 (P 85.2, R 92.5) | 94.7 (P 90.7, R 99.0) |
| AZ_ID_CARD_NUMBER | 98.8 (P 98.4, R 99.2) | 97.2 (P 98.7, R 95.8) |
| AZ_DRIVER_LICENSE_NUMBER | 99.1 (P 99.5, R 98.8) | 99.9 (P 99.8, R 100.0) |
| PRIVATE_KEY | 97.7 (P 95.7, R 99.8) | 97.8 (P 96.2, R 99.5) |
| API_KEY | 99.3 (P 98.7, R 100.0) | 100.0 (P 100.0, R 100.0) |
| ACCESS_TOKEN | 99.1 (P 99.0, R 99.2) | 99.7 (P 99.7, R 99.7) |

## C3 (licence_vs_id + contrast_licence_id)

| condition | v4 | v4.1 |
|---|---|---|
| licence_vs_id confusion_rate [AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER] < 0.05 | 25.0 | 0.0 |
| licence_vs_id confusion_rate [AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER] < 0.05 | 0.0 | 0.0 |
| contrast_licence_id confusion_rate [AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER] < 0.05 | 0.0 | 0.0 |
| contrast_licence_id confusion_rate [AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER] < 0.05 | 0.0 | 0.0 |
| contrast_licence_id exact_recall [AZ_DRIVER_LICENSE_NUMBER] >= 0.8 | 100.0 | 100.0 |
| contrast_licence_id exact_recall [AZ_ID_CARD_NUMBER] >= 0.8 | 100.0 | 100.0 |
| contrast_licence_id decoy_trigger_rate < 0.15 | 0.0 | 0.0 |

## C4 (look-alikes masked with the label they resemble, policy kinds left out)

| family | v4 | v4.1 |
|---|---|---|
| decoy_cvv | 42.9% (3/7) | 14.3% (1/7) |
| decoy_time | 50.0% (6/12) | 50.0% (6/12) |
| decoy_age | 8.3% (1/12) | 8.3% (1/12) |
| decoy_date | 58.3% (7/12) | 25.0% (3/12) |
| decoy_zip | 25.0% (3/12) | 8.3% (1/12) |
| decoy_fin | 20.0% (1/5) | 40.0% (2/5) |
| decoy_voen_passport_id | 0.0% (0/12) | 0.0% (0/12) |
| decoy_ipv4 | 0.0% (0/12) | 16.7% (2/12) |
| decoy_ipv6_mac | 0.0% (0/12) | 0.0% (0/12) |
| decoy_card_iccid_iban | 0.0% (0/8) | 0.0% (0/8) |
| decoy_names_as_org | 0.0% (0/12) | 0.0% (0/12) |
| **overall** | **18.1%** (21/116) | **13.8%** (16/116) |

## Key probe families (exact F1 per label)

| family | label | v4 | v4.1 |
|---|---|---|---|
| pem | PRIVATE_KEY | 100.0 (P 100.0, R 100.0) | 100.0 (P 100.0, R 100.0) |
| pem | split spans | 0 | 0 |
| token_vs_key | API_KEY | 100.0 (P 100.0, R 100.0) | 100.0 (P 100.0, R 100.0) |
| token_vs_key | ACCESS_TOKEN | 88.0 (P 84.6, R 91.7) | 88.0 (P 84.6, R 91.7) |
| token_vs_key | split spans | 1 | 1 |
| contrast_token_key | API_KEY | 100.0 (P 100.0, R 100.0) | 100.0 (P 100.0, R 100.0) |
| contrast_token_key | ACCESS_TOKEN | 90.9 (P 88.2, R 93.8) | 90.9 (P 88.2, R 93.8) |
| contrast_token_key | split spans | 1 | 1 |
