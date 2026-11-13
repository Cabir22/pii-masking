# Scoreboard: ckpt1_runb_test

| | |
|---|---|
| Model | `your-hf-org/masking-multilingual` |
| Revision SHA | `2519392a4c7cabc26bfadf1a5ba4c6a6d8c638cf` |
| Requested revision | `2519392a4c7cabc26bfadf1a5ba4c6a6d8c638cf` |
| Code git SHA | `c5c1614b85b8e2f8922673509b1c87b505e98f8c` |
| Date (UTC) | 2026-10-19T11:08:22Z |
| Device | cuda |
| Libraries | tokenizers 0.22.2, transformers 4.57.6, torch 2.8.0.dev20250319+cu128, python 3.11.11 |
| Tracks | R = raw HF pipeline (simple), M = model-only product path |
| Data version | runb_test `c68ace4065e8c53d` |

## A6 gates (shadow_dev, track R)

`benchmark` is the same metric on that set, track R: a reference while the shadow numbers are pending, never a gate.

| Gate | Measured | benchmark | Sprint 1 target | S1 | Sprint 2 target | S2 | Note |
|---|---|---|---|---|---|---|---|
| micro_f1 | n/a | n/a | >= 76.0 | – | >= 82.0 | – | shadow_dev not scored: shadow pending |
| weakest_label_f1 | n/a | n/a | >= 50.0 | – | >= 65.0 | – | shadow_dev not scored: shadow pending |
| ACCESS_TOKEN_f1 | n/a | n/a | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| IPV6_ADDRESS_f1 | n/a | n/a | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| AZ_DRIVER_LICENSE_NUMBER_f1 | n/a | n/a | >= 50.0 | – | >= 75.0 | – | shadow_dev not scored: shadow pending |
| hard_negative_trigger_rate | n/a | n/a | < 12.0 | – | < 8.0 | – | shadow_dev not scored: shadow pending |
| pii_free_fp_rate | n/a | n/a | < 30.0 | – | < 15.0 | – | shadow_dev not scored: shadow pending |
| recall_guard | n/a | n/a | no label -1 pt | – | no label -1 pt | – | no --baseline given |
| en_tr_ru_regression | n/a | n/a | <= 1 pt drop | – | <= 1 pt drop | – | no --baseline given |
| appendix_known_errors_fixed | n/a | n/a | reported by class | – | reported by class | – | appendix not scored |
| sealed_set | untouched | n/a | untouched | PASS | run once | – |  |

## Sets

Percentages. Exact = label+start+end. Trigger = decoy hit with the label it resembles (any label in brackets).

| Set | Track | Docs | Exact P / R / F1 | Macro F1 | Overlap F1 | Char leak | Narrower | Split | Trigger | Control FP | PII-free FP | Perfect |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| runb_test | R | 16848 | 85.6 / 78.2 / 81.7 | 81.2 | 85.6 | 11.3 | 70.8 | 1229 | 34.8 (42.1) | – | 20.5 | 46.3 |
| runb_test | M | 16848 | 89.3 / 80.2 / 84.5 | 85.1 | 85.6 | 11.1 | 79.9 | 374 | 34.1 (41.0) | – | 20.2 | 49.1 |

## Run B test split by part (track R)

old / new = same id and text as in v1's test split / v2 only; old_corpus / new_data = by id prefix (merged_relabeled_swept_dated vs targeted + LLM b1-b5). Exact-span percentages.

| Part | Docs | Micro P / R / F1 | Macro F1 | PII-free docs | PII-free FP |
|---|---|---|---|---|---|
| all | 16848 | 85.6 / 78.2 / 81.7 | 81.2 | 1691 | 20.5 |
| new | 353 | 86.5 / 83.3 / 84.9 | 81.7 | 23 | 30.4 |
| old | 7854 | 95.5 / 80.0 / 87.1 | 91.1 | 1017 | 1.7 |
| unlisted | 8641 | 77.1 / 76.1 / 76.6 | 74.2 | 651 | 49.5 |
| new_data | 9029 | 77.6 / 76.5 / 77.0 | 74.5 | 677 | 48.9 |
| old_corpus | 7819 | 95.6 / 79.9 / 87.1 | 91.1 | 1014 | 1.5 |

| Label | all F1 (gold) | new F1 (gold) | old F1 (gold) | unlisted F1 (gold) | new_data F1 (gold) | old_corpus F1 (gold) |
|---|---|---|---|---|---|---|
| ACCESS_TOKEN | 64.3 (911) | 48.0 (19) | 98.2 (383) | 23.4 (509) | 24.2 (531) | 98.6 (380) |
| AGE | 91.8 (1457) | 97.1 (33) | 94.1 (823) | 88.5 (601) | 89.0 (637) | 94.1 (820) |
| API_KEY | 84.7 (1344) | 77.4 (26) | 99.1 (603) | 75.4 (715) | 75.5 (744) | 99.3 (600) |
| AZ_DRIVER_LICENSE_NUMBER | 69.1 (1228) | 66.7 (20) | 93.5 (328) | 60.9 (880) | 61.3 (907) | 93.7 (321) |
| AZ_FIN | 86.8 (1060) | 88.3 (34) | 97.6 (556) | 76.2 (470) | 77.1 (506) | 97.6 (554) |
| AZ_ID_CARD_NUMBER | 73.5 (1543) | 88.9 (36) | 94.1 (409) | 64.9 (1098) | 65.8 (1135) | 94.1 (408) |
| AZ_PASSPORT_NUMBER | 82.7 (648) | 80.0 (16) | 95.5 (287) | 74.3 (345) | 74.6 (362) | 95.5 (286) |
| AZ_VOEN | 84.8 (629) | 68.3 (14) | 97.1 (276) | 76.9 (339) | 76.4 (353) | 97.1 (276) |
| BUILDINGNUM | 92.0 (1431) | 97.1 (35) | 96.5 (690) | 87.8 (706) | 88.2 (744) | 96.4 (687) |
| CARD_SECURITY_CODE | 74.7 (739) | 59.6 (16) | 94.6 (305) | 64.2 (418) | 64.2 (437) | 94.5 (302) |
| CITY | 90.1 (3502) | 90.8 (79) | 98.6 (1821) | 79.9 (1602) | 80.4 (1688) | 98.6 (1814) |
| DATE | 37.8 (8727) | 41.9 (199) | 32.7 (5050) | 43.3 (3478) | 43.1 (3699) | 32.8 (5028) |
| EMAIL | 97.9 (5249) | 100.0 (125) | 99.9 (2974) | 95.2 (2150) | 95.5 (2295) | 99.9 (2954) |
| GIVENNAME | 83.1 (11474) | 93.7 (194) | 86.7 (5245) | 79.8 (6035) | 80.3 (6257) | 86.6 (5217) |
| IBAN | 87.2 (739) | 96.8 (15) | 93.2 (352) | 81.3 (372) | 81.9 (387) | 93.2 (352) |
| ICCID | 95.0 (469) | 100.0 (21) | 95.2 (218) | 94.4 (230) | 94.9 (251) | 95.2 (218) |
| IPV4_ADDRESS | 89.4 (1038) | 87.0 (10) | 95.4 (519) | 83.7 (509) | 83.7 (520) | 95.5 (518) |
| IPV6_ADDRESS | 71.1 (716) | 59.5 (23) | 98.5 (202) | 59.1 (491) | 59.2 (515) | 98.5 (201) |
| MAC_ADDRESS | 78.1 (792) | 77.3 (30) | 97.4 (252) | 70.4 (510) | 70.9 (543) | 97.4 (249) |
| PAYMENT_CARD_NUMBER | 86.7 (950) | 86.5 (18) | 95.1 (445) | 80.0 (487) | 80.3 (506) | 95.1 (444) |
| PRIVATE_KEY | 37.7 (380) | 64.0 (10) | 49.5 (139) | 31.7 (231) | 32.5 (241) | 49.6 (139) |
| STREET | 93.4 (2282) | 85.0 (57) | 98.4 (1240) | 87.4 (985) | 87.3 (1047) | 98.4 (1235) |
| SURNAME | 89.7 (8207) | 96.1 (170) | 94.1 (3564) | 86.0 (4473) | 86.5 (4670) | 94.0 (3537) |
| TELEPHONENUM | 91.3 (4538) | 92.3 (121) | 92.1 (2497) | 90.3 (1920) | 90.4 (2056) | 92.0 (2482) |
| TIME | 80.0 (1398) | 77.1 (28) | 84.8 (700) | 75.4 (670) | 75.6 (703) | 84.8 (695) |
| URL | 91.9 (1085) | 92.3 (25) | 92.8 (605) | 90.6 (455) | 90.7 (480) | 92.8 (605) |
| ZIPCODE | 88.4 (1773) | 93.2 (42) | 95.2 (887) | 81.3 (844) | 82.0 (892) | 95.2 (881) |

## Run B test split by part (track M)

old / new = same id and text as in v1's test split / v2 only; old_corpus / new_data = by id prefix (merged_relabeled_swept_dated vs targeted + LLM b1-b5). Exact-span percentages.

| Part | Docs | Micro P / R / F1 | Macro F1 | PII-free docs | PII-free FP |
|---|---|---|---|---|---|
| all | 16848 | 89.3 / 80.2 / 84.5 | 85.1 | 1691 | 20.2 |
| new | 353 | 90.1 / 84.2 / 87.0 | 84.6 | 23 | 26.1 |
| old | 7854 | 97.8 / 81.7 / 89.1 | 94.3 | 1017 | 1.6 |
| unlisted | 8641 | 81.9 / 78.5 / 80.1 | 78.3 | 651 | 49.2 |
| new_data | 9029 | 82.2 / 78.8 / 80.5 | 78.6 | 677 | 48.4 |
| old_corpus | 7819 | 97.9 / 81.7 / 89.1 | 94.3 | 1014 | 1.4 |

| Label | all F1 (gold) | new F1 (gold) | old F1 (gold) | unlisted F1 (gold) | new_data F1 (gold) | old_corpus F1 (gold) |
|---|---|---|---|---|---|---|
| ACCESS_TOKEN | 65.8 (911) | 53.8 (19) | 99.2 (383) | 24.5 (509) | 25.6 (531) | 99.6 (380) |
| AGE | 97.2 (1457) | 98.5 (33) | 99.3 (823) | 94.3 (601) | 94.6 (637) | 99.3 (820) |
| API_KEY | 86.1 (1344) | 80.0 (26) | 99.6 (603) | 77.2 (715) | 77.3 (744) | 99.8 (600) |
| AZ_DRIVER_LICENSE_NUMBER | 73.4 (1228) | 73.2 (20) | 99.1 (328) | 64.6 (880) | 65.0 (907) | 99.4 (321) |
| AZ_FIN | 88.3 (1060) | 89.5 (34) | 97.1 (556) | 79.3 (470) | 80.0 (506) | 97.1 (554) |
| AZ_ID_CARD_NUMBER | 77.8 (1543) | 90.0 (36) | 99.8 (409) | 68.7 (1098) | 69.5 (1135) | 99.8 (408) |
| AZ_PASSPORT_NUMBER | 86.9 (648) | 86.5 (16) | 100.0 (287) | 77.9 (345) | 78.3 (362) | 100.0 (286) |
| AZ_VOEN | 89.3 (629) | 82.4 (14) | 99.6 (276) | 82.1 (339) | 82.1 (353) | 99.6 (276) |
| BUILDINGNUM | 94.1 (1431) | 97.1 (35) | 99.4 (690) | 89.2 (706) | 89.6 (744) | 99.3 (687) |
| CARD_SECURITY_CODE | 78.1 (739) | 60.9 (16) | 99.2 (305) | 67.0 (418) | 66.9 (437) | 99.2 (302) |
| CITY | 91.1 (3502) | 92.1 (79) | 98.5 (1821) | 81.9 (1602) | 82.5 (1688) | 98.5 (1814) |
| DATE | 40.5 (8727) | 43.8 (199) | 33.6 (5050) | 47.8 (3478) | 47.5 (3699) | 33.7 (5028) |
| EMAIL | 98.2 (5249) | 100.0 (125) | 99.9 (2974) | 95.8 (2150) | 96.0 (2295) | 99.9 (2954) |
| GIVENNAME | 84.7 (11474) | 94.5 (194) | 86.9 (5245) | 82.4 (6035) | 82.9 (6257) | 86.9 (5217) |
| IBAN | 93.6 (739) | 93.3 (15) | 98.3 (352) | 89.2 (372) | 89.3 (387) | 98.3 (352) |
| ICCID | 98.7 (469) | 100.0 (21) | 99.8 (218) | 97.6 (230) | 97.8 (251) | 99.8 (218) |
| IPV4_ADDRESS | 93.3 (1038) | 90.9 (10) | 99.9 (519) | 87.2 (509) | 87.2 (520) | 100.0 (518) |
| IPV6_ADDRESS | 75.7 (716) | 50.0 (23) | 99.8 (202) | 65.6 (491) | 65.0 (515) | 99.8 (201) |
| MAC_ADDRESS | 82.7 (792) | 81.7 (30) | 99.8 (252) | 75.7 (510) | 76.1 (543) | 99.8 (249) |
| PAYMENT_CARD_NUMBER | 90.1 (950) | 81.1 (18) | 99.2 (445) | 83.0 (487) | 83.0 (506) | 99.2 (444) |
| PRIVATE_KEY | 54.7 (380) | 87.0 (10) | 61.7 (139) | 49.7 (231) | 50.8 (241) | 61.9 (139) |
| STREET | 94.7 (2282) | 88.1 (57) | 99.3 (1240) | 88.9 (985) | 88.9 (1047) | 99.3 (1235) |
| SURNAME | 91.4 (8207) | 96.4 (170) | 94.3 (3564) | 88.9 (4473) | 89.2 (4670) | 94.2 (3537) |
| TELEPHONENUM | 98.3 (4538) | 100.0 (121) | 99.7 (2497) | 96.4 (1920) | 96.7 (2056) | 99.7 (2482) |
| TIME | 79.1 (1398) | 76.1 (28) | 83.9 (700) | 74.5 (670) | 74.7 (703) | 83.9 (695) |
| URL | 98.4 (1085) | 100.0 (25) | 99.2 (605) | 97.2 (455) | 97.3 (480) | 99.2 (605) |
| ZIPCODE | 94.3 (1773) | 96.6 (42) | 99.9 (887) | 88.6 (844) | 89.0 (892) | 99.9 (881) |

### Slices: runb_test (exact recall / overlap recall / split spans)

| Slice | Value | Gold | R | M |
|---|---|---|---|---|
| doc:_adversarials | 0 | 57029 | 79.6 / 82.7 / 1035 | 81.6 / 82.4 / 292 |
| doc:_adversarials | 1 | 4218 | 67.5 / 70.7 / 106 | 68.8 / 70.2 / 48 |
| doc:_adversarials | 2 | 2517 | 64.1 / 67.7 / 63 | 66.2 / 67.2 / 20 |
| doc:_adversarials | 3 | 370 | 73.8 / 82.7 / 20 | 78.4 / 81.9 / 13 |
| doc:_adversarials | 4 | 90 | 87.8 / 92.2 / 3 | 91.1 / 92.2 / 1 |
| doc:_adversarials | 5 | 17 | 58.8 / 64.7 / 1 | 64.7 / 64.7 / 0 |
| doc:_adversarials | 6 | 8 | 87.5 / 100.0 / 1 | 87.5 / 87.5 / 0 |
| doc:_adversarials | 8 | 60 | 90.0 / 90.0 / 0 | 88.3 / 88.3 / 0 |
| doc:_bucket | extreme | 2518 | 72.1 / 75.6 / 48 | 73.9 / 75.5 / 36 |
| doc:_bucket | long | 18599 | 79.4 / 81.9 / 227 | 81.2 / 81.7 / 56 |
| doc:_bucket | medium | 17907 | 79.5 / 82.4 / 311 | 81.4 / 82.2 / 90 |
| doc:_bucket | short | 11649 | 74.3 / 78.5 / 391 | 76.9 / 78.2 / 125 |
| doc:_bucket | very_long | 9432 | 80.2 / 82.8 / 97 | 81.9 / 82.5 / 25 |
| doc:_bucket | very_short | 4201 | 76.9 / 81.8 / 155 | 79.7 / 80.9 / 42 |
| doc:_gen_version | 14e1626c5846 | 1899 | 77.0 / 79.9 / 25 | 79.0 / 80.0 / 13 |
| doc:_gen_version | 1e976944376d | 3766 | 78.7 / 82.9 / 141 | 81.0 / 81.8 / 28 |
| doc:_gen_version | 22f108b78dea | 1935 | 86.6 / 89.0 / 29 | 88.0 / 89.2 / 16 |
| doc:_gen_version | 2ee9cb4f4b66 | 7074 | 77.6 / 81.3 / 237 | 79.6 / 80.4 / 40 |
| doc:_gen_version | 57fcdd4581e2 | 776 | 80.0 / 84.0 / 28 | 82.9 / 83.2 / 2 |
| doc:_gen_version | 5f82f117746a | 2399 | 76.0 / 77.7 / 22 | 77.3 / 78.0 / 11 |
| doc:_gen_version | 75b71ab25e5f | 5881 | 63.0 / 70.7 / 403 | 66.3 / 69.1 / 158 |
| doc:_gen_version | c3e7de3b39f5 | 64 | 76.6 / 76.6 / 0 | 76.6 / 76.6 / 0 |
| doc:_gen_version | c91c89591c16 | 7134 | 82.1 / 85.5 / 147 | 84.5 / 85.8 / 59 |
| doc:_gen_version | d0e7f1dee7c2 | 1760 | 75.7 / 77.9 / 18 | 77.0 / 77.7 / 6 |
| doc:_gen_version | f680dbb6b892 | 363 | 84.0 / 86.5 / 6 | 85.7 / 86.8 / 2 |
| doc:_gen_version | f78568bf074c | 55 | 85.5 / 85.5 / 0 | 87.3 / 87.3 / 0 |
| doc:_hard_negatives | 0 | 50574 | 79.8 / 82.8 / 837 | 81.9 / 82.6 / 244 |
| doc:_hard_negatives | 1 | 6060 | 76.3 / 79.8 / 168 | 78.1 / 79.3 / 59 |
| doc:_hard_negatives | 2 | 4094 | 76.2 / 80.6 / 134 | 78.5 / 79.7 / 40 |
| doc:_hard_negatives | 3 | 2337 | 72.0 / 76.3 / 74 | 73.9 / 75.1 / 24 |
| doc:_hard_negatives | 4 | 597 | 54.4 / 56.6 / 10 | 55.6 / 56.4 / 5 |
| doc:_hard_negatives | 5 | 255 | 36.1 / 38.4 / 5 | 38.4 / 39.2 / 2 |
| doc:_hard_negatives | 6 | 271 | 5.5 / 5.9 / 1 | 4.1 / 4.1 / 0 |
| doc:_hard_negatives | 7 | 61 | 0.0 / 0.0 / 0 | 1.6 / 1.6 / 0 |
| doc:_hard_negatives | 8 | 60 | 90.0 / 90.0 / 0 | 88.3 / 88.3 / 0 |
| doc:_old | True | 31203 | 79.9 / 82.1 / 173 | 81.7 / 82.1 / 39 |
| doc:_pii_free | False | 33058 | 76.6 / 80.7 / 1056 | 78.9 / 80.1 / 335 |
| doc:_pii_free | True | 48 | 0.0 / 0.0 / 0 | 2.1 / 2.1 / 0 |
| doc:_register | anxious and confused | 3622 | 83.7 / 86.6 / 54 | 85.7 / 86.5 / 13 |
| doc:_register | apologetic | 3346 | 83.0 / 85.1 / 36 | 84.4 / 85.0 / 10 |
| doc:_register | bureaucratic | 1472 | 61.7 / 70.2 / 117 | 65.1 / 67.5 / 35 |
| doc:_register | bureaucratic and officious | 4753 | 79.1 / 81.6 / 62 | 81.0 / 81.4 / 11 |
| doc:_register | casual with typos and abbreviations | 3737 | 79.9 / 83.2 / 41 | 82.2 / 83.2 / 21 |
| doc:_register | chat | 1154 | 61.0 / 67.9 / 69 | 63.3 / 65.8 / 29 |
| doc:_register | empathetic customer-service | 3527 | 84.4 / 86.5 / 34 | 85.6 / 86.3 / 8 |
| doc:_register | formal and businesslike | 4738 | 78.5 / 81.4 / 78 | 80.6 / 81.2 / 15 |
| doc:_register | friendly with light humour | 4115 | 77.9 / 80.1 / 41 | 79.5 / 80.0 / 8 |
| doc:_register | frustrated and complaining | 3792 | 83.4 / 85.9 / 37 | 85.5 / 86.0 / 8 |
| doc:_register | matter-of-fact administrative | 4498 | 77.5 / 80.4 / 79 | 79.5 / 80.1 / 21 |
| doc:_register | note | 1180 | 64.7 / 72.0 / 79 | 67.5 / 70.2 / 30 |
| doc:_register | polite | 958 | 63.5 / 71.6 / 65 | 68.3 / 71.8 / 32 |
| doc:_register | polite but firm | 4594 | 79.4 / 82.4 / 82 | 81.7 / 82.2 / 16 |
| doc:_register | technical | 1117 | 64.4 / 72.2 / 73 | 67.9 / 70.9 / 32 |
| doc:_register | technical and precise | 4686 | 77.4 / 80.4 / 99 | 79.2 / 80.0 / 28 |
| doc:_register | terse and clipped | 4272 | 74.8 / 77.5 / 51 | 76.9 / 77.6 / 23 |
| doc:_register | urgent and escalating | 5066 | 79.3 / 82.3 / 96 | 81.3 / 82.0 / 22 |
| doc:_register | warm and conversational | 3682 | 80.7 / 82.8 / 36 | 82.0 / 82.6 / 12 |
| doc:_source | llm | 58428 | 79.7 / 82.4 / 826 | 81.6 / 82.2 / 216 |
| doc:_source | targeted | 5881 | 63.0 / 70.7 / 403 | 66.3 / 69.1 / 158 |
| doc:lang | az | 64309 | 78.2 / 81.3 / 1229 | 80.2 / 81.0 / 374 |
| … | 10 more rows in the JSON | | |

Calibration (score bins vs precision) is in the JSON. It is reported only and is never used to set a threshold (A2.2).
