# SLM test data card (task 2.1)

Generated 2026-10-01 11:37 UTC by `scripts/slm/export.py`. Plan: the SLM test plan (sections 2, 4 and task 2.1).

| | |
|---|---|
| Seed | `20261001` |
| Source | `data/processed/merged_relabeled_swept` |
| train ids hash (sha256 of sorted ids, one per line) | `b5ca8d0c799db298c828ab67ce409fea309889789d52a7616f172eef5a1c3bb8` |
| val ids hash (sha256 of sorted ids, one per line) | `16b716f07ec30e513653f009bd9a818b1a9fc9550decf2cded3d5b2d5ec5575e` |
| Combined ids hash | `5728662a72bfca2030d26291bfb110b6d9d6f6520c45f49dc0560fe739760fae` |
| Source `train.docs.jsonl` sha256 | `b4c737c162f8374a3eaf098fb614c68839ff7f3210bd2846e33d67e348dfc014` |
| Source `val.docs.jsonl` sha256 | `a4e65ecbcb6e38b0335e115a5459876cdb8a92dbdb3ec357094666b24a8a4379` |

## Round trip through grounding

Pool documents whose gold spans do not come back exactly were removed before sampling, so they are out of every arm. Ids in `ids/roundtrip_dropped_<split>.txt`.

| split | pool | dropped | share | reasons |
|---|---:|---:|---:|---|
| train | 332888 | 362 | 0.109% | grounded to another occurrence 362 |
| val | 41727 | 57 | 0.137% | grounded to another occurrence 57 |

Values containing a line break (multi-line PEM keys and a few names, streets, dates) are written on one line with each line-break run replaced by a space; the plan's grounding tier 3 (whitespace collapse) maps them back to the exact span. Train values written this way: 1259.

## Counts

### train

| | az | en | ru | tr | all |
|---|---:|---:|---:|---:|---:|
| documents | 16000 | 16000 | 16000 | 16000 | 64000 |
| no-PII documents | 3761 (23.5%) | 3777 (23.6%) | 3799 (23.7%) | 3800 (23.8%) | 15137 |
| API_KEY | 1293 | 1315 | 1293 | 1336 | 5237 |
| ACCESS_TOKEN | 781 | 734 | 736 | 732 | 2983 |
| PRIVATE_KEY | 501 | 503 | 512 | 493 | 2009 |
| PAYMENT_CARD_NUMBER | 940 | 946 | 970 | 964 | 3820 |
| IBAN | 760 | 760 | 736 | 763 | 3019 |
| CARD_SECURITY_CODE | 568 | 566 | 559 | 577 | 2270 |
| IPV4_ADDRESS | 935 | 1024 | 963 | 1017 | 3939 |
| IPV6_ADDRESS | 388 | 383 | 362 | 391 | 1524 |
| MAC_ADDRESS | 528 | 489 | 493 | 519 | 2029 |
| URL | 1241 | 1247 | 1222 | 1235 | 4945 |
| ICCID | 401 | 404 | 409 | 417 | 1631 |
| GIVENNAME | 8940 | 8723 | 8732 | 8876 | 35271 |
| SURNAME | 7412 | 7177 | 6974 | 7214 | 28777 |
| EMAIL | 6159 | 6064 | 6087 | 6084 | 24394 |
| TELEPHONENUM | 5008 | 4848 | 4854 | 4933 | 19643 |
| DATE | 2365 | 2224 | 2284 | 2179 | 9052 |
| TIME | 1454 | 1382 | 1356 | 1447 | 5639 |
| AGE | 1560 | 1471 | 1481 | 1553 | 6065 |
| CITY | 3878 | 3616 | 3747 | 3723 | 14964 |
| STREET | 2541 | 2387 | 2456 | 2506 | 9890 |
| BUILDINGNUM | 1800 | 1781 | 1808 | 1874 | 7263 |
| ZIPCODE | 1917 | 1813 | 1791 | 1828 | 7349 |
| AZ_FIN | 1149 | 1113 | 1039 | 1130 | 4431 |
| AZ_ID_CARD_NUMBER | 836 | 856 | 834 | 838 | 3364 |
| AZ_PASSPORT_NUMBER | 711 | 710 | 697 | 700 | 2818 |
| AZ_VOEN | 596 | 610 | 602 | 579 | 2387 |
| AZ_DRIVER_LICENSE_NUMBER | 629 | 603 | 600 | 599 | 2431 |

### val

| | az | en | ru | tr | all |
|---|---:|---:|---:|---:|---:|
| documents | 1000 | 1000 | 1000 | 1000 | 4000 |
| no-PII documents | 235 (23.5%) | 236 (23.6%) | 237 (23.7%) | 238 (23.8%) | 946 |
| API_KEY | 84 | 76 | 82 | 69 | 311 |
| ACCESS_TOKEN | 53 | 52 | 47 | 48 | 200 |
| PRIVATE_KEY | 31 | 35 | 29 | 32 | 127 |
| PAYMENT_CARD_NUMBER | 50 | 46 | 51 | 55 | 202 |
| IBAN | 52 | 56 | 44 | 49 | 201 |
| CARD_SECURITY_CODE | 38 | 35 | 36 | 31 | 140 |
| IPV4_ADDRESS | 83 | 57 | 62 | 62 | 264 |
| IPV6_ADDRESS | 24 | 21 | 27 | 25 | 97 |
| MAC_ADDRESS | 30 | 31 | 31 | 30 | 122 |
| URL | 70 | 76 | 79 | 81 | 306 |
| ICCID | 22 | 20 | 23 | 25 | 90 |
| GIVENNAME | 707 | 449 | 501 | 513 | 2170 |
| SURNAME | 467 | 406 | 427 | 460 | 1760 |
| EMAIL | 347 | 372 | 397 | 381 | 1497 |
| TELEPHONENUM | 308 | 289 | 297 | 335 | 1229 |
| DATE | 124 | 134 | 114 | 150 | 522 |
| TIME | 81 | 62 | 89 | 81 | 313 |
| AGE | 92 | 99 | 81 | 114 | 386 |
| CITY | 180 | 191 | 224 | 233 | 828 |
| STREET | 160 | 159 | 176 | 157 | 652 |
| BUILDINGNUM | 118 | 102 | 110 | 104 | 434 |
| ZIPCODE | 101 | 115 | 119 | 102 | 437 |
| AZ_FIN | 76 | 68 | 77 | 74 | 295 |
| AZ_ID_CARD_NUMBER | 59 | 44 | 54 | 49 | 206 |
| AZ_PASSPORT_NUMBER | 42 | 37 | 47 | 46 | 172 |
| AZ_VOEN | 41 | 42 | 39 | 33 | 155 |
| AZ_DRIVER_LICENSE_NUMBER | 51 | 41 | 36 | 32 | 160 |

## Files

| split | format | rows | sha256 |
|---|---|---:|---|
| train | docs | 64000 | `9d877ccbacbd119c…` |
| train | xlmr | 88586 | `175bb3caeab52d7e…` |
| train | qwen3 | 64305 | `041f1d1765fa9ec9…` |
| train | chat | 64000 | `923f57e6ee9d705c…` |
| train | opf | 64000 | `001ae7060987ec7c…` |
| val | docs | 4000 | `427ea975b1894017…` |
| val | xlmr | 5545 | `ae7bc45ec490f529…` |
| val | qwen3 | 4014 | `60b3414fe9b1d273…` |
| val | chat | 4000 | `8eb7b08042530433…` |
| val | opf | 4000 | `3e2993190c6e8653…` |

## Same ids in every format, round trip on the written files

| split | format | same id list | failures |
|---|---|---|---:|
| train | docs | yes | 0 |
| train | xlmr | yes | 0 |
| train | qwen3 | yes | 0 |
| train | chat | yes | 0 |
| train | opf | yes | 0 |
| val | docs | yes | 0 |
| val | xlmr | yes | 0 |
| val | qwen3 | yes | 0 |
| val | chat | yes | 0 |
| val | opf | yes | 0 |

## Token edges (train)

Entities with a start or end inside a token, and documents longer than one window.

| tokenizer | window | entities | edge inside a token | docs over one window |
|---|---:|---:|---:|---:|
| xlmr | 512 | 217144 | 1 (0.00%) | 13173 (20.6%) |
| qwen3 | 2048 | 217144 | 2063 (0.95%) | 283 (0.4%) |

## Tools

```
{
  "python": "3.13.14",
  "transformers": "4.57.6",
  "tokenizers": "0.22.2",
  "tokenizer_revisions": {
    "xlm-roberta-large": "c23d21b0620b635a76227c604d44e43a9f0ee389",
    "Qwen/Qwen3-1.7B": "70d244cc86ccca08cf5af4e1e306ecf908b1ad5e"
  }
}
```
