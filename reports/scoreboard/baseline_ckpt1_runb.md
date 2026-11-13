# Scoreboard: ckpt1_runb_test

| | |
|---|---|
| Model | `your-hf-org/masking-multilingual` |
| Revision SHA | `3a0a6e5df228bdc89dd01312a728e10a78b3e3fb` |
| Requested revision | `3a0a6e5df228bdc89dd01312a728e10a78b3e3fb` |
| Code git SHA | `1f098969c38bfc5b960326a024bff1acb7495a01` |
| Date (UTC) | 2026-10-12T13:11:57Z |
| Device | cpu |
| Tracks | R = raw HF pipeline (simple), M = model-only product path |
| Data version | runb_test `c4c85ba5a4d4c2db` |

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
| runb_test | R | 15835 | 89.6 / 81.7 / 85.5 | 85.4 | 88.6 | 10.4 | 65.2 | 778 | 31.6 (36.9) | – | 14.9 | 51.4 |
| runb_test | M | 15835 | 92.9 / 83.7 / 88.1 | 89.4 | 88.8 | 10.4 | 89.9 | 256 | 30.3 (35.2) | – | 14.4 | 54.6 |

## Run B test split by part (track R)

old / new = same id and text as in v1's test split / v2 only; old_corpus / new_data = by id prefix (merged_relabeled_swept_dated vs targeted + LLM b1-b5). Exact-span percentages.

| Part | Docs | Micro P / R / F1 | Macro F1 | PII-free docs | PII-free FP |
|---|---|---|---|---|---|
| all | 15835 | 89.6 / 81.7 / 85.5 | 85.4 | 1787 | 14.9 |
| new | 6425 | 79.3 / 79.5 / 79.4 | 76.9 | 552 | 45.1 |
| old | 9410 | 96.0 / 82.9 / 89.0 | 92.5 | 1235 | 1.5 |
| new_data | 6900 | 79.8 / 79.7 / 79.8 | 77.2 | 583 | 45.1 |
| old_corpus | 8935 | 96.6 / 83.0 / 89.3 | 93.3 | 1204 | 0.3 |

| Label | all F1 (gold) | new F1 (gold) | old F1 (gold) | new_data F1 (gold) | old_corpus F1 (gold) |
|---|---|---|---|---|---|
| ACCESS_TOKEN | 67.3 (894) | 16.5 (420) | 95.8 (474) | 16.9 (451) | 98.8 (443) |
| AGE | 92.5 (1415) | 88.6 (424) | 94.2 (991) | 88.9 (465) | 94.3 (950) |
| API_KEY | 87.2 (1297) | 76.4 (576) | 97.9 (721) | 76.3 (608) | 99.3 (689) |
| AZ_DRIVER_LICENSE_NUMBER | 75.9 (1064) | 65.4 (659) | 92.3 (405) | 66.1 (688) | 93.4 (376) |
| AZ_FIN | 86.6 (1087) | 75.2 (433) | 95.9 (654) | 75.0 (456) | 97.2 (631) |
| AZ_ID_CARD_NUMBER | 84.0 (1214) | 78.8 (713) | 92.5 (501) | 79.0 (741) | 93.2 (473) |
| AZ_PASSPORT_NUMBER | 84.9 (666) | 75.3 (309) | 94.8 (357) | 75.4 (326) | 95.9 (340) |
| AZ_VOEN | 87.0 (611) | 77.0 (279) | 96.6 (332) | 76.9 (290) | 97.5 (321) |
| BUILDINGNUM | 92.6 (1444) | 87.4 (602) | 96.6 (842) | 88.0 (649) | 96.7 (795) |
| CARD_SECURITY_CODE | 78.8 (600) | 64.3 (244) | 93.2 (356) | 64.8 (260) | 94.4 (340) |
| CITY | 93.2 (3409) | 82.8 (1152) | 98.3 (2257) | 82.8 (1241) | 98.9 (2168) |
| DATE | 38.3 (8828) | 45.9 (2509) | 34.7 (6319) | 45.4 (2796) | 34.4 (6032) |
| EMAIL | 99.7 (5111) | 99.0 (1456) | 99.9 (3655) | 99.1 (1679) | 99.9 (3432) |
| GIVENNAME | 94.7 (7481) | 88.2 (2433) | 97.8 (5048) | 88.5 (2651) | 98.1 (4830) |
| IBAN | 88.0 (735) | 81.9 (303) | 92.6 (432) | 82.0 (322) | 93.1 (413) |
| ICCID | 95.3 (502) | 95.8 (238) | 94.9 (264) | 95.5 (243) | 95.2 (259) |
| IPV4_ADDRESS | 91.7 (997) | 86.8 (386) | 95.0 (611) | 86.5 (404) | 95.5 (593) |
| IPV6_ADDRESS | 80.1 (696) | 69.2 (420) | 95.1 (276) | 69.8 (464) | 98.5 (232) |
| MAC_ADDRESS | 83.3 (681) | 75.1 (369) | 94.7 (312) | 74.9 (392) | 97.2 (289) |
| PAYMENT_CARD_NUMBER | 88.6 (906) | 79.4 (349) | 95.1 (557) | 80.3 (381) | 95.3 (525) |
| PRIVATE_KEY | 65.9 (468) | 44.4 (165) | 84.0 (303) | 45.8 (174) | 84.0 (294) |
| STREET | 94.3 (2351) | 87.6 (884) | 98.1 (1467) | 87.7 (939) | 98.5 (1412) |
| SURNAME | 91.0 (6244) | 84.7 (1970) | 93.9 (4274) | 85.6 (2172) | 93.9 (4072) |
| TELEPHONENUM | 92.3 (4308) | 92.0 (1329) | 92.5 (2979) | 92.3 (1443) | 92.3 (2865) |
| TIME | 88.6 (1420) | 80.9 (552) | 94.0 (868) | 81.5 (593) | 94.2 (827) |
| URL | 91.7 (1058) | 89.8 (335) | 92.7 (723) | 89.8 (374) | 92.8 (684) |
| ZIPCODE | 92.7 (1633) | 88.0 (576) | 95.3 (1057) | 88.8 (629) | 95.2 (1004) |

## Run B test split by part (track M)

old / new = same id and text as in v1's test split / v2 only; old_corpus / new_data = by id prefix (merged_relabeled_swept_dated vs targeted + LLM b1-b5). Exact-span percentages.

| Part | Docs | Micro P / R / F1 | Macro F1 | PII-free docs | PII-free FP |
|---|---|---|---|---|---|
| all | 15835 | 92.9 / 83.7 / 88.1 | 89.4 | 1787 | 14.4 |
| new | 6425 | 84.2 / 81.9 / 83.0 | 81.7 | 552 | 43.7 |
| old | 9410 | 98.3 / 84.7 / 91.0 | 95.7 | 1235 | 1.4 |
| new_data | 6900 | 84.4 / 82.0 / 83.2 | 81.8 | 583 | 43.7 |
| old_corpus | 8935 | 98.9 / 84.8 / 91.3 | 96.5 | 1204 | 0.2 |

| Label | all F1 (gold) | new F1 (gold) | old F1 (gold) | new_data F1 (gold) | old_corpus F1 (gold) |
|---|---|---|---|---|---|
| ACCESS_TOKEN | 69.9 (894) | 19.8 (420) | 96.2 (474) | 19.5 (451) | 99.7 (443) |
| AGE | 97.9 (1415) | 94.8 (424) | 99.2 (991) | 95.0 (465) | 99.3 (950) |
| API_KEY | 88.4 (1297) | 78.3 (576) | 98.2 (721) | 77.9 (608) | 99.7 (689) |
| AZ_DRIVER_LICENSE_NUMBER | 83.2 (1064) | 73.6 (659) | 97.7 (405) | 74.0 (688) | 99.1 (376) |
| AZ_FIN | 88.3 (1087) | 78.3 (433) | 96.1 (654) | 77.9 (456) | 97.3 (631) |
| AZ_ID_CARD_NUMBER | 90.2 (1214) | 84.8 (713) | 98.9 (501) | 84.9 (741) | 99.8 (473) |
| AZ_PASSPORT_NUMBER | 90.2 (666) | 81.8 (309) | 98.8 (357) | 81.6 (326) | 100.0 (340) |
| AZ_VOEN | 91.1 (611) | 82.8 (279) | 98.5 (332) | 82.3 (290) | 99.7 (321) |
| BUILDINGNUM | 94.8 (1444) | 89.3 (602) | 99.2 (842) | 89.8 (649) | 99.3 (795) |
| CARD_SECURITY_CODE | 83.2 (600) | 68.2 (244) | 97.9 (356) | 68.6 (260) | 99.3 (340) |
| CITY | 93.9 (3409) | 84.7 (1152) | 98.3 (2257) | 84.5 (1241) | 98.9 (2168) |
| DATE | 40.2 (8828) | 49.0 (2509) | 36.1 (6319) | 49.2 (2796) | 35.2 (6032) |
| EMAIL | 99.8 (5111) | 99.3 (1456) | 100.0 (3655) | 99.4 (1679) | 100.0 (3432) |
| GIVENNAME | 95.0 (7481) | 89.0 (2433) | 97.8 (5048) | 89.4 (2651) | 98.1 (4830) |
| IBAN | 93.2 (735) | 87.1 (303) | 97.7 (432) | 86.9 (322) | 98.4 (413) |
| ICCID | 99.5 (502) | 99.2 (238) | 99.8 (264) | 99.2 (243) | 99.8 (259) |
| IPV4_ADDRESS | 95.4 (997) | 89.8 (386) | 99.2 (611) | 89.2 (404) | 100.0 (593) |
| IPV6_ADDRESS | 82.7 (696) | 73.5 (420) | 94.9 (276) | 73.1 (464) | 99.8 (232) |
| MAC_ADDRESS | 85.6 (681) | 77.6 (369) | 96.6 (312) | 77.0 (392) | 99.8 (289) |
| PAYMENT_CARD_NUMBER | 92.7 (906) | 84.1 (349) | 98.7 (557) | 84.5 (381) | 99.3 (525) |
| PRIVATE_KEY | 87.6 (468) | 75.8 (165) | 94.8 (303) | 76.9 (174) | 94.7 (294) |
| STREET | 95.6 (2351) | 89.6 (884) | 99.0 (1467) | 89.7 (939) | 99.3 (1412) |
| SURNAME | 92.0 (6244) | 87.7 (1970) | 94.0 (4274) | 88.4 (2172) | 93.9 (4072) |
| TELEPHONENUM | 99.5 (4308) | 99.1 (1329) | 99.7 (2979) | 99.1 (1443) | 99.7 (2865) |
| TIME | 90.1 (1420) | 81.4 (552) | 96.3 (868) | 81.7 (593) | 96.8 (827) |
| URL | 97.8 (1058) | 95.1 (335) | 99.1 (723) | 95.3 (374) | 99.3 (684) |
| ZIPCODE | 96.9 (1633) | 91.7 (576) | 99.8 (1057) | 92.4 (629) | 99.8 (1004) |

### Slices: runb_test (exact recall / overlap recall / split spans)

| Slice | Value | Gold | R | M |
|---|---|---|---|---|
| doc:_adversarials | 0 | 53106 | 83.4 / 86.0 / 701 | 85.4 / 86.0 / 217 |
| doc:_adversarials | 1 | 2471 | 63.1 / 66.0 / 58 | 65.1 / 66.2 / 22 |
| doc:_adversarials | 2 | 1543 | 54.1 / 55.8 / 19 | 54.4 / 55.5 / 17 |
| doc:_adversarials | 3 | 0 | – / – / 0 | – / – / 0 |
| doc:_bucket | extreme | 2879 | 69.7 / 72.4 / 34 | 71.7 / 72.8 / 22 |
| doc:_bucket | long | 17022 | 83.4 / 85.4 / 115 | 85.1 / 85.4 / 39 |
| doc:_bucket | medium | 14930 | 82.4 / 84.6 / 183 | 84.1 / 84.6 / 55 |
| doc:_bucket | short | 9439 | 79.7 / 83.6 / 269 | 82.6 / 83.6 / 93 |
| doc:_bucket | very_long | 9343 | 84.2 / 86.1 / 43 | 85.9 / 86.2 / 16 |
| doc:_bucket | very_short | 3361 | 80.2 / 85.0 / 122 | 83.1 / 84.1 / 27 |
| doc:_gen_version | 01a97fd5f84a | 4798 | 73.0 / 80.5 / 295 | 77.4 / 79.7 / 108 |
| doc:_gen_version | 14e1626c5846 | 2150 | 77.5 / 80.0 / 31 | 79.1 / 79.7 / 9 |
| doc:_gen_version | 22f108b78dea | 2105 | 87.2 / 89.6 / 33 | 89.3 / 90.1 / 15 |
| doc:_gen_version | 5f82f117746a | 2317 | 79.2 / 80.7 / 23 | 80.2 / 80.8 / 14 |
| doc:_gen_version | c3e7de3b39f5 | 46 | 76.1 / 78.3 / 1 | 69.6 / 78.3 / 0 |
| doc:_gen_version | c91c89591c16 | 7833 | 84.1 / 87.0 / 167 | 85.9 / 87.0 / 71 |
| doc:_gen_version | d0e7f1dee7c2 | 2019 | 71.9 / 74.5 / 28 | 74.0 / 74.3 / 4 |
| doc:_gen_version | f680dbb6b892 | 509 | 86.1 / 87.6 / 7 | 88.8 / 88.8 / 0 |
| doc:_gen_version | f78568bf074c | 54 | 85.2 / 87.0 / 1 | 85.2 / 85.2 / 0 |
| doc:_hard_negatives | 0 | 49217 | 83.4 / 86.0 / 629 | 85.5 / 86.0 / 189 |
| doc:_hard_negatives | 1 | 3348 | 82.3 / 85.2 / 77 | 84.4 / 85.3 / 24 |
| doc:_hard_negatives | 2 | 2327 | 78.9 / 81.8 / 53 | 80.7 / 81.9 / 28 |
| doc:_hard_negatives | 3 | 1224 | 66.1 / 67.8 / 14 | 67.3 / 68.5 / 13 |
| doc:_hard_negatives | 4 | 398 | 42.0 / 43.5 / 4 | 41.2 / 42.5 / 2 |
| doc:_hard_negatives | 5 | 251 | 24.3 / 25.1 / 1 | 25.1 / 25.1 / 0 |
| doc:_hard_negatives | 6 | 280 | 1.4 / 1.4 / 0 | 0.0 / 0.0 / 0 |
| doc:_hard_negatives | 7 | 75 | 0.0 / 0.0 / 0 | 0.0 / 0.0 / 0 |
| doc:_old | True | 35289 | 83.0 / 84.9 / 192 | 84.8 / 85.0 / 35 |
| doc:_pii_free | False | 21742 | 80.0 / 83.6 / 586 | 82.4 / 83.5 / 221 |
| doc:_pii_free | True | 89 | 0.0 / 0.0 / 0 | 0.0 / 0.0 / 0 |
| doc:_register | anxious and confused | 3920 | 86.6 / 89.1 / 48 | 88.6 / 88.9 / 10 |
| doc:_register | apologetic | 3460 | 83.1 / 85.1 / 42 | 84.6 / 85.1 / 12 |
| doc:_register | bureaucratic | 1018 | 73.7 / 81.4 / 65 | 78.1 / 80.8 / 28 |
| doc:_register | bureaucratic and officious | 3721 | 79.9 / 81.9 / 27 | 81.8 / 82.1 / 7 |
| doc:_register | casual with typos and abbreviations | 4430 | 83.4 / 86.2 / 39 | 86.2 / 86.5 / 5 |
| doc:_register | chat | 852 | 70.2 / 78.5 / 55 | 76.5 / 78.2 / 13 |
| doc:_register | empathetic customer-service | 3606 | 86.2 / 88.0 / 29 | 87.7 / 88.1 / 11 |
| doc:_register | formal and businesslike | 3470 | 80.3 / 82.4 / 35 | 81.7 / 82.4 / 11 |
| doc:_register | friendly with light humour | 3817 | 82.7 / 84.8 / 34 | 84.7 / 85.0 / 8 |
| doc:_register | frustrated and complaining | 3911 | 86.3 / 88.2 / 28 | 88.0 / 88.1 / 6 |
| doc:_register | matter-of-fact administrative | 3808 | 79.4 / 81.4 / 30 | 81.2 / 81.6 / 10 |
| doc:_register | note | 1030 | 74.2 / 81.0 / 57 | 78.2 / 80.2 / 20 |
| doc:_register | polite | 928 | 73.9 / 81.7 / 66 | 77.9 / 80.7 / 26 |
| doc:_register | polite but firm | 3244 | 80.4 / 82.4 / 26 | 81.8 / 82.1 / 8 |
| doc:_register | technical | 970 | 72.7 / 79.5 / 52 | 76.2 / 78.5 / 21 |
| doc:_register | technical and precise | 3184 | 81.6 / 83.7 / 33 | 83.3 / 83.6 / 10 |
| doc:_register | terse and clipped | 4398 | 76.3 / 78.4 / 37 | 78.1 / 78.6 / 19 |
| doc:_register | urgent and escalating | 3664 | 82.3 / 84.6 / 27 | 84.2 / 84.6 / 11 |
| doc:_register | warm and conversational | 3689 | 86.9 / 89.0 / 48 | 88.2 / 88.9 / 20 |
| doc:_source | llm | 52322 | 82.5 / 84.6 / 483 | 84.3 / 84.7 / 148 |
| doc:_source | targeted | 4798 | 73.0 / 80.5 / 295 | 77.4 / 79.7 / 108 |
| doc:lang | az | 57120 | 81.7 / 84.3 / 778 | 83.7 / 84.3 / 256 |
| doc:runb_origin | new_data | 21831 | 79.7 / 83.3 / 586 | 82.0 / 83.2 / 221 |
| doc:runb_origin | old_corpus | 35289 | 83.0 / 84.9 / 192 | 84.8 / 85.0 / 35 |
| doc:runb_part | new | 20085 | 79.5 / 83.2 / 555 | 81.9 / 83.1 / 209 |
| doc:runb_part | old | 37035 | 82.9 / 84.9 / 223 | 84.7 / 84.9 / 47 |
| doc:density | 0 | 0 | – / – / 0 | – / – / 0 |
| doc:density | 1 | 4112 | 75.5 / 79.3 / 103 | 77.8 / 78.9 / 43 |
| doc:density | 2-3 | 11091 | 76.3 / 79.6 / 234 | 78.7 / 79.3 / 58 |
| doc:density | 4-6 | 13934 | 84.0 / 86.0 / 184 | 85.6 / 86.1 / 57 |
| … | 1 more rows in the JSON | | |

Calibration (score bins vs precision) is in the JSON. It is reported only and is never used to set a threshold (A2.2).
