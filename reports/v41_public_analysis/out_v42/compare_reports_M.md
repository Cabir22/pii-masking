# v4.2 M0 (no filter) -> v4.2 M from the scoreboard reports (track M, exact spans)

## Benchmark

| | v4.2 M0 (no filter) | v4.2 M |
|---|---|---|
| all labels, policy items left out | 96.8 (P 96.1, R 97.5) | 97.0 (P 96.6, R 97.5) |
| all labels, with the policy items | 95.8 (P 94.1, R 97.5) | 96.0 (P 94.6, R 97.5) |
| IPV4_ADDRESS | 93.0 (P 88.8, R 97.6) | 97.0 (P 96.3, R 97.6) |
| IPV6_ADDRESS | 74.6 (P 87.6, R 65.0) | 74.6 (P 87.6, R 65.0) |
| EMAIL | 100.0 (P 100.0, R 100.0) | 100.0 (P 100.0, R 100.0) |
| TIME | 97.5 (P 97.3, R 97.6) | 97.6 (P 97.6, R 97.6) |
| ZIPCODE | 93.7 (P 88.3, R 99.7) | 93.7 (P 88.3, R 99.7) |
| AZ_ID_CARD_NUMBER | 99.5 (P 100.0, R 99.0) | 99.5 (P 100.0, R 99.0) |
| AZ_DRIVER_LICENSE_NUMBER | 100.0 (P 100.0, R 100.0) | 100.0 (P 100.0, R 100.0) |
| PRIVATE_KEY | 99.0 (P 98.6, R 99.3) | 99.0 (P 98.6, R 99.3) |
| API_KEY | 99.7 (P 99.5, R 100.0) | 99.7 (P 99.5, R 100.0) |
| ACCESS_TOKEN | 99.7 (P 99.7, R 99.7) | 99.7 (P 99.7, R 99.7) |

## C3 (licence_vs_id + contrast_licence_id)

| condition | v4.2 M0 (no filter) | v4.2 M |
|---|---|---|
| licence_vs_id confusion_rate [AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER] < 0.05 | 0.0 | 0.0 |
| licence_vs_id confusion_rate [AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER] < 0.05 | 0.0 | 0.0 |
| contrast_licence_id confusion_rate [AZ_DRIVER_LICENSE_NUMBER→AZ_ID_CARD_NUMBER] < 0.05 | 0.0 | 0.0 |
| contrast_licence_id confusion_rate [AZ_ID_CARD_NUMBER→AZ_DRIVER_LICENSE_NUMBER] < 0.05 | 0.0 | 0.0 |
| contrast_licence_id exact_recall [AZ_DRIVER_LICENSE_NUMBER] >= 0.8 | 100.0 | 100.0 |
| contrast_licence_id exact_recall [AZ_ID_CARD_NUMBER] >= 0.8 | 100.0 | 100.0 |
| contrast_licence_id decoy_trigger_rate < 0.15 | 10.0 | 10.0 |

## C4 (look-alikes masked with the label they resemble, policy kinds left out)

| family | v4.2 M0 (no filter) | v4.2 M |
|---|---|---|
| decoy_cvv | 14.3% (1/7) | 0.0% (0/7) |
| decoy_time | 25.0% (3/12) | 0.0% (0/12) |
| decoy_age | 0.0% (0/12) | 0.0% (0/12) |
| decoy_date | 25.0% (3/12) | 0.0% (0/12) |
| decoy_zip | 0.0% (0/12) | 0.0% (0/12) |
| decoy_fin | 20.0% (1/5) | 0.0% (0/5) |
| decoy_voen_passport_id | 0.0% (0/12) | 0.0% (0/12) |
| decoy_ipv4 | 0.0% (0/12) | 0.0% (0/12) |
| decoy_ipv6_mac | 0.0% (0/12) | 0.0% (0/12) |
| decoy_card_iccid_iban | 0.0% (0/8) | 0.0% (0/8) |
| decoy_names_as_org | 0.0% (0/12) | 0.0% (0/12) |
| **overall** | **6.9%** (8/116) | **0.0%** (0/116) |

## Key probe families (exact F1 per label)

| family | label | v4.2 M0 (no filter) | v4.2 M |
|---|---|---|---|
| pem | PRIVATE_KEY | 95.2 (P 90.9, R 100.0) | 95.2 (P 90.9, R 100.0) |
| pem | split spans | 0 | 0 |
| token_vs_key | API_KEY | 100.0 (P 100.0, R 100.0) | 100.0 (P 100.0, R 100.0) |
| token_vs_key | ACCESS_TOKEN | 100.0 (P 100.0, R 100.0) | 100.0 (P 100.0, R 100.0) |
| token_vs_key | split spans | 0 | 0 |
| contrast_token_key | API_KEY | 100.0 (P 100.0, R 100.0) | 100.0 (P 100.0, R 100.0) |
| contrast_token_key | ACCESS_TOKEN | 88.2 (P 83.3, R 93.8) | 88.2 (P 83.3, R 93.8) |
| contrast_token_key | split spans | 1 | 1 |
