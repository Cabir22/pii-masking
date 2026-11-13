# Scoreboard: new_runb_test

| | |
|---|---|
| Model | `your-hf-org/masking-az-runb-v4.1-seed42` |
| Revision SHA | `502598c1d5850958e98b1922ce65d504f700b528` |
| Requested revision | `502598c1d5850958e98b1922ce65d504f700b528` |
| Code git SHA | `c5c1614b85b8e2f8922673509b1c87b505e98f8c` |
| Date (UTC) | 2026-10-19T11:26:27Z |
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
| runb_test | R | 16848 | 98.5 / 99.5 / 99.0 | 99.2 | 99.2 | 0.1 | 93.5 | 84 | 0.9 (1.2) | – | 1.1 | 96.1 |
| runb_test | M | 16848 | 98.8 / 99.5 / 99.1 | 99.3 | 99.2 | 0.1 | 84.7 | 32 | 0.8 (1.0) | – | 0.9 | 96.3 |

## Run B test split by part (track R)

old / new = same id and text as in v1's test split / v2 only; old_corpus / new_data = by id prefix (merged_relabeled_swept_dated vs targeted + LLM b1-b5). Exact-span percentages.

| Part | Docs | Micro P / R / F1 | Macro F1 | PII-free docs | PII-free FP |
|---|---|---|---|---|---|
| all | 16848 | 98.5 / 99.5 / 99.0 | 99.2 | 1691 | 1.1 |
| new | 353 | 98.5 / 99.5 / 99.0 | 99.5 | 23 | 0.0 |
| old | 7854 | 98.7 / 99.6 / 99.2 | 99.4 | 1017 | 1.3 |
| unlisted | 8641 | 98.4 / 99.3 / 98.8 | 99.0 | 651 | 0.9 |
| new_data | 9029 | 98.4 / 99.3 / 98.8 | 99.0 | 677 | 0.9 |
| old_corpus | 7819 | 98.7 / 99.6 / 99.2 | 99.4 | 1014 | 1.3 |

| Label | all F1 (gold) | new F1 (gold) | old F1 (gold) | unlisted F1 (gold) | new_data F1 (gold) | old_corpus F1 (gold) |
|---|---|---|---|---|---|---|
| ACCESS_TOKEN | 99.1 (911) | 100.0 (19) | 99.6 (383) | 98.7 (509) | 98.8 (531) | 99.6 (380) |
| AGE | 99.1 (1457) | 100.0 (33) | 99.4 (823) | 98.7 (601) | 98.8 (637) | 99.4 (820) |
| API_KEY | 99.7 (1344) | 100.0 (26) | 99.7 (603) | 99.7 (715) | 99.7 (744) | 99.7 (600) |
| AZ_DRIVER_LICENSE_NUMBER | 99.8 (1228) | 100.0 (20) | 99.8 (328) | 99.7 (880) | 99.7 (907) | 99.8 (321) |
| AZ_FIN | 98.9 (1060) | 100.0 (34) | 99.6 (556) | 98.1 (470) | 98.2 (506) | 99.6 (554) |
| AZ_ID_CARD_NUMBER | 99.7 (1543) | 100.0 (36) | 99.8 (409) | 99.7 (1098) | 99.7 (1135) | 99.8 (408) |
| AZ_PASSPORT_NUMBER | 99.9 (648) | 100.0 (16) | 100.0 (287) | 99.9 (345) | 99.9 (362) | 100.0 (286) |
| AZ_VOEN | 98.0 (629) | 100.0 (14) | 99.5 (276) | 96.8 (339) | 96.9 (353) | 99.5 (276) |
| BUILDINGNUM | 99.1 (1431) | 98.6 (35) | 99.0 (690) | 99.3 (706) | 99.3 (744) | 99.0 (687) |
| CARD_SECURITY_CODE | 97.9 (739) | 97.0 (16) | 98.5 (305) | 97.5 (418) | 97.5 (437) | 98.5 (302) |
| CITY | 98.1 (3502) | 97.5 (79) | 99.2 (1821) | 96.9 (1602) | 97.0 (1688) | 99.2 (1814) |
| DATE | 99.7 (8727) | 100.0 (199) | 99.7 (5050) | 99.7 (3478) | 99.7 (3699) | 99.7 (5028) |
| EMAIL | 100.0 (5249) | 100.0 (125) | 99.9 (2974) | 100.0 (2150) | 100.0 (2295) | 99.9 (2954) |
| GIVENNAME | 97.7 (11474) | 95.9 (194) | 97.6 (5245) | 97.8 (6035) | 97.8 (6257) | 97.6 (5217) |
| IBAN | 99.9 (739) | 100.0 (15) | 100.0 (352) | 99.7 (372) | 99.7 (387) | 100.0 (352) |
| ICCID | 99.8 (469) | 100.0 (21) | 100.0 (218) | 99.6 (230) | 99.6 (251) | 100.0 (218) |
| IPV4_ADDRESS | 99.6 (1038) | 100.0 (10) | 99.6 (519) | 99.5 (509) | 99.5 (520) | 99.6 (518) |
| IPV6_ADDRESS | 99.5 (716) | 100.0 (23) | 99.5 (202) | 99.5 (491) | 99.5 (515) | 99.5 (201) |
| MAC_ADDRESS | 99.6 (792) | 100.0 (30) | 99.4 (252) | 99.7 (510) | 99.7 (543) | 99.4 (249) |
| PAYMENT_CARD_NUMBER | 98.6 (950) | 100.0 (18) | 99.0 (445) | 98.2 (487) | 98.2 (506) | 99.0 (444) |
| PRIVATE_KEY | 98.7 (380) | 100.0 (10) | 99.3 (139) | 98.3 (231) | 98.3 (241) | 99.3 (139) |
| STREET | 99.5 (2282) | 99.1 (57) | 99.7 (1240) | 99.2 (985) | 99.2 (1047) | 99.7 (1235) |
| SURNAME | 98.7 (8207) | 98.5 (170) | 99.0 (3564) | 98.4 (4473) | 98.4 (4670) | 99.0 (3537) |
| TELEPHONENUM | 99.6 (4538) | 100.0 (121) | 99.6 (2497) | 99.6 (1920) | 99.7 (2056) | 99.6 (2482) |
| TIME | 98.2 (1398) | 100.0 (28) | 97.8 (700) | 98.6 (670) | 98.6 (703) | 97.8 (695) |
| URL | 100.0 (1085) | 100.0 (25) | 99.9 (605) | 100.0 (455) | 100.0 (480) | 99.9 (605) |
| ZIPCODE | 99.7 (1773) | 100.0 (42) | 99.7 (887) | 99.7 (844) | 99.7 (892) | 99.7 (881) |

## Run B test split by part (track M)

old / new = same id and text as in v1's test split / v2 only; old_corpus / new_data = by id prefix (merged_relabeled_swept_dated vs targeted + LLM b1-b5). Exact-span percentages.

| Part | Docs | Micro P / R / F1 | Macro F1 | PII-free docs | PII-free FP |
|---|---|---|---|---|---|
| all | 16848 | 98.8 / 99.5 / 99.1 | 99.3 | 1691 | 0.9 |
| new | 353 | 98.5 / 99.5 / 99.0 | 99.5 | 23 | 0.0 |
| old | 7854 | 98.8 / 99.7 / 99.2 | 99.5 | 1017 | 1.0 |
| unlisted | 8641 | 98.7 / 99.4 / 99.0 | 99.2 | 651 | 0.8 |
| new_data | 9029 | 98.7 / 99.4 / 99.1 | 99.2 | 677 | 0.7 |
| old_corpus | 7819 | 98.8 / 99.7 / 99.2 | 99.5 | 1014 | 1.0 |

| Label | all F1 (gold) | new F1 (gold) | old F1 (gold) | unlisted F1 (gold) | new_data F1 (gold) | old_corpus F1 (gold) |
|---|---|---|---|---|---|---|
| ACCESS_TOKEN | 99.5 (911) | 100.0 (19) | 99.6 (383) | 99.3 (509) | 99.3 (531) | 99.6 (380) |
| AGE | 99.1 (1457) | 100.0 (33) | 99.4 (823) | 98.8 (601) | 98.8 (637) | 99.4 (820) |
| API_KEY | 99.8 (1344) | 100.0 (26) | 99.7 (603) | 99.9 (715) | 99.9 (744) | 99.7 (600) |
| AZ_DRIVER_LICENSE_NUMBER | 99.9 (1228) | 100.0 (20) | 99.8 (328) | 99.9 (880) | 99.9 (907) | 99.8 (321) |
| AZ_FIN | 99.1 (1060) | 100.0 (34) | 99.6 (556) | 98.5 (470) | 98.6 (506) | 99.6 (554) |
| AZ_ID_CARD_NUMBER | 99.8 (1543) | 100.0 (36) | 99.9 (409) | 99.8 (1098) | 99.8 (1135) | 99.9 (408) |
| AZ_PASSPORT_NUMBER | 99.9 (648) | 100.0 (16) | 100.0 (287) | 99.9 (345) | 99.9 (362) | 100.0 (286) |
| AZ_VOEN | 98.6 (629) | 100.0 (14) | 99.5 (276) | 97.8 (339) | 97.9 (353) | 99.5 (276) |
| BUILDINGNUM | 99.3 (1431) | 98.6 (35) | 99.2 (690) | 99.4 (706) | 99.4 (744) | 99.2 (687) |
| CARD_SECURITY_CODE | 98.0 (739) | 97.0 (16) | 98.5 (305) | 97.7 (418) | 97.6 (437) | 98.5 (302) |
| CITY | 98.4 (3502) | 97.5 (79) | 99.2 (1821) | 97.6 (1602) | 97.6 (1688) | 99.2 (1814) |
| DATE | 99.7 (8727) | 100.0 (199) | 99.7 (5050) | 99.7 (3478) | 99.7 (3699) | 99.7 (5028) |
| EMAIL | 100.0 (5249) | 100.0 (125) | 99.9 (2974) | 100.0 (2150) | 100.0 (2295) | 99.9 (2954) |
| GIVENNAME | 98.0 (11474) | 95.9 (194) | 97.8 (5245) | 98.2 (6035) | 98.2 (6257) | 97.7 (5217) |
| IBAN | 99.9 (739) | 100.0 (15) | 100.0 (352) | 99.7 (372) | 99.7 (387) | 100.0 (352) |
| ICCID | 100.0 (469) | 100.0 (21) | 100.0 (218) | 100.0 (230) | 100.0 (251) | 100.0 (218) |
| IPV4_ADDRESS | 99.6 (1038) | 100.0 (10) | 99.6 (519) | 99.5 (509) | 99.5 (520) | 99.6 (518) |
| IPV6_ADDRESS | 99.7 (716) | 100.0 (23) | 100.0 (202) | 99.5 (491) | 99.5 (515) | 100.0 (201) |
| MAC_ADDRESS | 99.6 (792) | 100.0 (30) | 99.4 (252) | 99.7 (510) | 99.7 (543) | 99.4 (249) |
| PAYMENT_CARD_NUMBER | 98.9 (950) | 100.0 (18) | 99.1 (445) | 98.6 (487) | 98.6 (506) | 99.1 (444) |
| PRIVATE_KEY | 98.7 (380) | 100.0 (10) | 99.3 (139) | 98.3 (231) | 98.3 (241) | 99.3 (139) |
| STREET | 99.5 (2282) | 99.1 (57) | 99.7 (1240) | 99.3 (985) | 99.3 (1047) | 99.7 (1235) |
| SURNAME | 98.9 (8207) | 98.5 (170) | 99.2 (3564) | 98.7 (4473) | 98.7 (4670) | 99.2 (3537) |
| TELEPHONENUM | 99.6 (4538) | 100.0 (121) | 99.6 (2497) | 99.6 (1920) | 99.6 (2056) | 99.6 (2482) |
| TIME | 98.2 (1398) | 100.0 (28) | 97.8 (700) | 98.6 (670) | 98.6 (703) | 97.8 (695) |
| URL | 100.0 (1085) | 100.0 (25) | 99.9 (605) | 100.0 (455) | 100.0 (480) | 99.9 (605) |
| ZIPCODE | 99.8 (1773) | 100.0 (42) | 99.8 (887) | 99.7 (844) | 99.7 (892) | 99.8 (881) |

### Slices: runb_test (exact recall / overlap recall / split spans)

| Slice | Value | Gold | R | M |
|---|---|---|---|---|
| doc:_adversarials | 0 | 57029 | 99.5 / 99.6 / 60 | 99.5 / 99.6 / 23 |
| doc:_adversarials | 1 | 4218 | 99.2 / 99.6 / 15 | 99.3 / 99.5 / 7 |
| doc:_adversarials | 2 | 2517 | 99.2 / 99.5 / 7 | 99.4 / 99.4 / 0 |
| doc:_adversarials | 3 | 370 | 99.7 / 100.0 / 1 | 99.7 / 100.0 / 1 |
| doc:_adversarials | 4 | 90 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_adversarials | 5 | 17 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_adversarials | 6 | 8 | 87.5 / 100.0 / 1 | 87.5 / 100.0 / 1 |
| doc:_adversarials | 8 | 60 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_bucket | extreme | 2518 | 99.0 / 99.2 / 4 | 99.2 / 99.2 / 0 |
| doc:_bucket | long | 18599 | 99.7 / 99.7 / 12 | 99.7 / 99.7 / 7 |
| doc:_bucket | medium | 17907 | 99.6 / 99.7 / 17 | 99.6 / 99.6 / 4 |
| doc:_bucket | short | 11649 | 99.4 / 99.7 / 25 | 99.5 / 99.6 / 15 |
| doc:_bucket | very_long | 9432 | 99.4 / 99.5 / 10 | 99.4 / 99.5 / 2 |
| doc:_bucket | very_short | 4201 | 98.5 / 99.0 / 16 | 98.7 / 98.8 / 4 |
| doc:_gen_version | 14e1626c5846 | 1899 | 99.6 / 99.6 / 1 | 99.6 / 99.6 / 1 |
| doc:_gen_version | 1e976944376d | 3766 | 99.5 / 99.6 / 5 | 99.5 / 99.5 / 1 |
| doc:_gen_version | 22f108b78dea | 1935 | 99.2 / 99.4 / 3 | 99.2 / 99.3 / 2 |
| doc:_gen_version | 2ee9cb4f4b66 | 7074 | 99.4 / 99.5 / 6 | 99.4 / 99.5 / 1 |
| doc:_gen_version | 57fcdd4581e2 | 776 | 99.2 / 99.7 / 4 | 99.4 / 99.7 / 3 |
| doc:_gen_version | 5f82f117746a | 2399 | 99.6 / 99.8 / 3 | 99.7 / 99.8 / 0 |
| doc:_gen_version | 75b71ab25e5f | 5881 | 99.2 / 99.5 / 16 | 99.3 / 99.4 / 6 |
| doc:_gen_version | c3e7de3b39f5 | 64 | 96.9 / 96.9 / 0 | 96.9 / 96.9 / 0 |
| doc:_gen_version | c91c89591c16 | 7134 | 99.0 / 99.3 / 20 | 99.2 / 99.3 / 6 |
| doc:_gen_version | d0e7f1dee7c2 | 1760 | 99.6 / 99.7 / 2 | 99.6 / 99.7 / 1 |
| doc:_gen_version | f680dbb6b892 | 363 | 99.7 / 99.7 / 0 | 99.2 / 99.7 / 0 |
| doc:_gen_version | f78568bf074c | 55 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_hard_negatives | 0 | 50574 | 99.5 / 99.6 / 50 | 99.5 / 99.6 / 19 |
| doc:_hard_negatives | 1 | 6060 | 99.2 / 99.5 / 16 | 99.3 / 99.4 / 5 |
| doc:_hard_negatives | 2 | 4094 | 99.2 / 99.5 / 11 | 99.4 / 99.4 / 3 |
| doc:_hard_negatives | 3 | 2337 | 99.4 / 99.7 / 6 | 99.5 / 99.7 / 4 |
| doc:_hard_negatives | 4 | 597 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_hard_negatives | 5 | 255 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_hard_negatives | 6 | 271 | 99.6 / 100.0 / 1 | 99.6 / 100.0 / 1 |
| doc:_hard_negatives | 7 | 61 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_hard_negatives | 8 | 60 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_old | True | 31203 | 99.6 / 99.7 / 24 | 99.7 / 99.7 / 11 |
| doc:_pii_free | False | 33058 | 99.3 / 99.5 / 60 | 99.4 / 99.5 / 21 |
| doc:_pii_free | True | 48 | 100.0 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_register | anxious and confused | 3622 | 99.5 / 99.6 / 5 | 99.6 / 99.6 / 1 |
| doc:_register | apologetic | 3346 | 99.6 / 99.8 / 4 | 99.7 / 99.7 / 1 |
| doc:_register | bureaucratic | 1472 | 99.1 / 99.3 / 3 | 99.1 / 99.2 / 1 |
| doc:_register | bureaucratic and officious | 4753 | 99.6 / 99.7 / 3 | 99.6 / 99.7 / 1 |
| doc:_register | casual with typos and abbreviations | 3737 | 99.3 / 99.4 / 2 | 99.4 / 99.4 / 0 |
| doc:_register | chat | 1154 | 99.1 / 99.3 / 2 | 99.3 / 99.3 / 0 |
| doc:_register | empathetic customer-service | 3527 | 99.7 / 99.8 / 2 | 99.7 / 99.8 / 2 |
| doc:_register | formal and businesslike | 4738 | 99.5 / 99.6 / 6 | 99.6 / 99.6 / 1 |
| doc:_register | friendly with light humour | 4115 | 99.3 / 99.6 / 9 | 99.4 / 99.5 / 3 |
| doc:_register | frustrated and complaining | 3792 | 99.6 / 99.7 / 4 | 99.6 / 99.7 / 3 |
| doc:_register | matter-of-fact administrative | 4498 | 99.3 / 99.5 / 8 | 99.4 / 99.5 / 3 |
| doc:_register | note | 1180 | 98.8 / 99.3 / 6 | 98.9 / 99.2 / 3 |
| doc:_register | polite | 958 | 99.8 / 99.9 / 1 | 99.9 / 99.9 / 0 |
| doc:_register | polite but firm | 4594 | 99.5 / 99.6 / 4 | 99.6 / 99.6 / 1 |
| doc:_register | technical | 1117 | 99.3 / 99.6 / 4 | 99.4 / 99.6 / 2 |
| doc:_register | technical and precise | 4686 | 99.5 / 99.6 / 6 | 99.6 / 99.6 / 2 |
| doc:_register | terse and clipped | 4272 | 99.6 / 99.8 / 7 | 99.7 / 99.8 / 2 |
| doc:_register | urgent and escalating | 5066 | 99.3 / 99.4 / 5 | 99.3 / 99.4 / 3 |
| doc:_register | warm and conversational | 3682 | 99.4 / 99.5 / 3 | 99.4 / 99.5 / 3 |
| doc:_source | llm | 58428 | 99.5 / 99.6 / 68 | 99.5 / 99.6 / 26 |
| doc:_source | targeted | 5881 | 99.2 / 99.5 / 16 | 99.3 / 99.4 / 6 |
| doc:lang | az | 64309 | 99.5 / 99.6 / 84 | 99.5 / 99.6 / 32 |
| … | 10 more rows in the JSON | | |

Calibration (score bins vs precision) is in the JSON. It is reported only and is never used to set a threshold (A2.2).
