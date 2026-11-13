# Split by template: 89,891 new documents (seed 20261001)

| | one by one (v4) | by template (v4.1) |
|---|---|---|
| train documents | 71,913 | 71,912 |
| train: targeted / llm | 19,944 / 51,969 | 20,174 / 51,738 |
| val documents | 8,989 | 8,986 |
| val: targeted / llm | 2,567 / 6,422 | 2,372 / 6,614 |
| test documents | 8,989 | 8,993 |
| test: targeted / llm | 2,489 / 6,500 | 2,454 / 6,539 |
| **val documents whose template is also in train** | **212** (targeted 212) | **0** (targeted 0) |
| **test documents whose template is also in train** | **212** (targeted 212) | **0** (targeted 0) |

## Labels in test (share of the label's mentions)

| Label | one by one (v4) | by template (v4.1) |
|---|---|---|
| ACCESS_TOKEN | 518 (10.1%) | 516 (10.1%) |
| AGE | 626 (10.1%) | 607 (9.8%) |
| API_KEY | 711 (10.0%) | 684 (9.6%) |
| AZ_DRIVER_LICENSE_NUMBER | 758 (9.8%) | 786 (10.2%) |
| AZ_FIN | 532 (10.5%) | 529 (10.4%) |
| AZ_ID_CARD_NUMBER | 910 (9.6%) | 976 (10.3%) |
| AZ_PASSPORT_NUMBER | 354 (9.7%) | 352 (9.7%) |
| AZ_VOEN | 340 (9.6%) | 345 (9.7%) |
| BUILDINGNUM | 759 (9.7%) | 743 (9.5%) |
| CARD_SECURITY_CODE | 421 (10.1%) | 425 (10.2%) |
| CITY | 1,803 (10.2%) | 1,720 (9.7%) |
| DATE | 3,729 (10.1%) | 3,582 (9.7%) |
| EMAIL | 2,210 (9.9%) | 2,358 (10.5%) |
| GIVENNAME | 6,098 (10.0%) | 6,222 (10.2%) |
| IBAN | 379 (10.0%) | 367 (9.7%) |
| ICCID | 258 (10.3%) | 234 (9.3%) |
| IPV4_ADDRESS | 475 (9.8%) | 484 (10.0%) |
| IPV6_ADDRESS | 438 (10.0%) | 425 (9.7%) |
| MAC_ADDRESS | 444 (9.5%) | 481 (10.3%) |
| PAYMENT_CARD_NUMBER | 479 (9.8%) | 490 (10.0%) |
| PRIVATE_KEY | 248 (9.9%) | 241 (9.6%) |
| STREET | 1,076 (10.1%) | 1,067 (10.0%) |
| SURNAME | 4,533 (10.0%) | 4,657 (10.3%) |
| TELEPHONENUM | 1,975 (10.0%) | 1,972 (10.0%) |
| TIME | 750 (10.2%) | 723 (9.8%) |
| URL | 469 (9.8%) | 502 (10.5%) |
| ZIPCODE | 839 (10.0%) | 831 (9.9%) |

## Targeted families in test

| Family | one by one (v4) | by template (v4.1) |
|---|---|---|
| clerical | 48 | 62 |
| contrast | 145 | 137 |
| cross_anchor | 84 | 92 |
| decoy_pair | 576 | 566 |
| edges | 49 | 38 |
| form | 153 | 151 |
| homograph | 88 | 115 |
| inflected | 209 | 203 |
| key_placeholder | 13 | 22 |
| locative | 40 | 34 |
| minimal | 112 | 0 |
| namelist | 91 | 109 |
| pem_long | 34 | 39 |
| pii_free | 170 | 195 |
| place_verbs | 24 | 21 |
| postal | 55 | 39 |
| prose | 49 | 51 |
| punct | 39 | 29 |
| short_keys | 22 | 21 |
| slot_invalid | 33 | 22 |
| structured | 392 | 411 |
| time_seconds | 33 | 56 |
| village | 30 | 41 |
