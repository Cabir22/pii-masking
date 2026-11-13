# v4.1 -> v4.2 from the scoreboard reports (track R, exact spans)

## Benchmark

| | v4.1 | v4.2 |
|---|---|---|
| all labels, policy items left out | 97.0 (P 95.6, R 98.5) | 96.4 (P 95.5, R 97.3) |
| all labels, with the policy items | 96.0 (P 93.6, R 98.5) | 95.4 (P 93.6, R 97.3) |
| IPV4_ADDRESS | 84.8 (P 76.3, R 95.5) | 92.9 (P 88.7, R 97.6) |
| IPV6_ADDRESS | 97.8 (P 97.1, R 98.4) | 72.2 (P 82.7, R 64.1) |
| EMAIL | 98.5 (P 98.0, R 99.0) | 100.0 (P 100.0, R 100.0) |
| TIME | 97.4 (P 96.4, R 98.3) | 97.5 (P 97.3, R 97.6) |
| ZIPCODE | 94.7 (P 90.7, R 99.0) | 93.2 (P 87.5, R 99.7) |
| AZ_ID_CARD_NUMBER | 97.2 (P 98.7, R 95.8) | 99.1 (P 99.5, R 98.7) |
| AZ_DRIVER_LICENSE_NUMBER | 99.9 (P 99.8, R 100.0) | 100.0 (P 100.0, R 100.0) |
| PRIVATE_KEY | 97.8 (P 96.2, R 99.5) | 99.0 (P 98.6, R 99.3) |
| API_KEY | 100.0 (P 100.0, R 100.0) | 99.7 (P 99.5, R 100.0) |
| ACCESS_TOKEN | 99.7 (P 99.7, R 99.7) | 99.7 (P 99.7, R 99.7) |

## C3 (licence_vs_id + contrast_licence_id)

| condition | v4.1 | v4.2 |
|---|---|---|
| licence_vs_id confusion_rate [AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER] < 0.05 | 0.0 | 0.0 |
| licence_vs_id confusion_rate [AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER] < 0.05 | 0.0 | 0.0 |
| contrast_licence_id confusion_rate [AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER] < 0.05 | 0.0 | 0.0 |
| contrast_licence_id confusion_rate [AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER] < 0.05 | 0.0 | 0.0 |
| contrast_licence_id exact_recall [AZ_DRIVER_LICENSE_NUMBER] >= 0.8 | 100.0 | 100.0 |
| contrast_licence_id exact_recall [AZ_ID_CARD_NUMBER] >= 0.8 | 100.0 | 100.0 |
| contrast_licence_id decoy_trigger_rate < 0.15 | 0.0 | 10.0 |

## C4 (look-alikes masked with the label they resemble, policy kinds left out)

| family | v4.1 | v4.2 |
|---|---|---|
| decoy_cvv | 14.3% (1/7) | 28.6% (2/7) |
| decoy_time | 50.0% (6/12) | 25.0% (3/12) |
| decoy_age | 8.3% (1/12) | 0.0% (0/12) |
| decoy_date | 25.0% (3/12) | 25.0% (3/12) |
| decoy_zip | 8.3% (1/12) | 0.0% (0/12) |
| decoy_fin | 40.0% (2/5) | 20.0% (1/5) |
| decoy_voen_passport_id | 0.0% (0/12) | 0.0% (0/12) |
| decoy_ipv4 | 16.7% (2/12) | 0.0% (0/12) |
| decoy_ipv6_mac | 0.0% (0/12) | 0.0% (0/12) |
| decoy_card_iccid_iban | 0.0% (0/8) | 0.0% (0/8) |
| decoy_names_as_org | 0.0% (0/12) | 0.0% (0/12) |
| **overall** | **13.8%** (16/116) | **7.8%** (9/116) |

## Key probe families (exact F1 per label)

| family | label | v4.1 | v4.2 |
|---|---|---|---|
| pem | PRIVATE_KEY | 100.0 (P 100.0, R 100.0) | 95.2 (P 90.9, R 100.0) |
| pem | split spans | 0 | 0 |
| token_vs_key | API_KEY | 100.0 (P 100.0, R 100.0) | 100.0 (P 100.0, R 100.0) |
| token_vs_key | ACCESS_TOKEN | 88.0 (P 84.6, R 91.7) | 100.0 (P 100.0, R 100.0) |
| token_vs_key | split spans | 1 | 0 |
| contrast_token_key | API_KEY | 100.0 (P 100.0, R 100.0) | 100.0 (P 100.0, R 100.0) |
| contrast_token_key | ACCESS_TOKEN | 90.9 (P 88.2, R 93.8) | 88.2 (P 83.3, R 93.8) |
| contrast_token_key | split spans | 1 | 1 |
