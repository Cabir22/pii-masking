# Scoreboard: runb_az_v2_seed42_2ep_runbtest

| | |
|---|---|
| Model | `your-hf-org/masking-az-runb-v2-seed42-2ep` |
| Revision SHA | `937f29d008f9f99d498e7686aa5e5dddf11ace14` |
| Requested revision | `937f29d008f9f99d498e7686aa5e5dddf11ace14` |
| Code git SHA | `7a1fd4c5ada668e8a23420fb70a4840a056420ae` |
| Date (UTC) | 2026-10-10T04:07:24Z |
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
| runb_test | R | 15835 | 96.2 / 96.8 / 96.5 | 96.2 | 99.0 | 1.4 | 25.6 | 291 | 1.7 (1.8) | – | 1.8 | 89.0 |
| runb_test | M | 15835 | 98.7 / 99.3 / 99.0 | 99.0 | 99.2 | 0.9 | 73.1 | 62 | 1.3 (1.4) | – | 1.5 | 96.0 |

## Run B test split by part (track R)

old / new = same id and text as in v1's test split / v2 only; old_corpus / new_data = by id prefix (merged_relabeled_swept_dated vs targeted + LLM b1-b5). Exact-span percentages.

| Part | Docs | Micro P / R / F1 | Macro F1 | PII-free docs | PII-free FP |
|---|---|---|---|---|---|
| all | 15835 | 96.2 / 96.8 / 96.5 | 96.2 | 1787 | 1.8 |
| new | 6425 | 96.1 / 97.0 / 96.6 | 95.9 | 552 | 3.1 |
| old | 9410 | 96.2 / 96.8 / 96.5 | 96.4 | 1235 | 1.3 |
| new_data | 6900 | 96.2 / 97.0 / 96.6 | 95.9 | 583 | 3.4 |
| old_corpus | 8935 | 96.2 / 96.7 / 96.4 | 96.3 | 1204 | 1.1 |

| Label | all F1 (gold) | new F1 (gold) | old F1 (gold) | new_data F1 (gold) | old_corpus F1 (gold) |
|---|---|---|---|---|---|
| ACCESS_TOKEN | 97.5 (894) | 97.0 (420) | 98.0 (474) | 96.2 (451) | 98.9 (443) |
| AGE | 95.1 (1415) | 96.5 (424) | 94.5 (991) | 96.4 (465) | 94.5 (950) |
| API_KEY | 99.4 (1297) | 99.6 (576) | 99.2 (721) | 99.6 (608) | 99.2 (689) |
| AZ_DRIVER_LICENSE_NUMBER | 96.0 (1064) | 97.1 (659) | 94.2 (405) | 97.2 (688) | 93.8 (376) |
| AZ_FIN | 95.8 (1087) | 93.4 (433) | 97.5 (654) | 93.6 (456) | 97.5 (631) |
| AZ_ID_CARD_NUMBER | 95.8 (1214) | 97.5 (713) | 93.5 (501) | 97.4 (741) | 93.3 (473) |
| AZ_PASSPORT_NUMBER | 95.0 (666) | 93.7 (309) | 96.1 (357) | 94.0 (326) | 95.9 (340) |
| AZ_VOEN | 96.8 (611) | 95.9 (279) | 97.4 (332) | 96.1 (290) | 97.4 (321) |
| BUILDINGNUM | 96.9 (1444) | 97.1 (602) | 96.7 (842) | 97.1 (649) | 96.7 (795) |
| CARD_SECURITY_CODE | 94.1 (600) | 93.8 (244) | 94.3 (356) | 94.2 (260) | 94.0 (340) |
| CITY | 99.0 (3409) | 98.3 (1152) | 99.3 (2257) | 98.2 (1241) | 99.4 (2168) |
| DATE | 92.9 (8828) | 93.6 (2509) | 92.6 (6319) | 93.9 (2796) | 92.4 (6032) |
| EMAIL | 98.7 (5111) | 98.9 (1456) | 98.7 (3655) | 98.6 (1679) | 98.8 (3432) |
| GIVENNAME | 97.9 (7481) | 97.7 (2433) | 98.0 (5048) | 97.7 (2651) | 98.0 (4830) |
| IBAN | 95.3 (735) | 95.1 (303) | 95.5 (432) | 95.4 (322) | 95.3 (413) |
| ICCID | 95.3 (502) | 95.6 (238) | 95.1 (264) | 95.3 (243) | 95.4 (259) |
| IPV4_ADDRESS | 94.7 (997) | 94.5 (386) | 94.7 (611) | 94.8 (404) | 94.6 (593) |
| IPV6_ADDRESS | 98.1 (696) | 97.5 (420) | 98.9 (276) | 97.7 (464) | 98.7 (232) |
| MAC_ADDRESS | 95.3 (681) | 94.1 (369) | 96.7 (312) | 94.4 (392) | 96.4 (289) |
| PAYMENT_CARD_NUMBER | 93.4 (906) | 90.3 (349) | 95.4 (557) | 90.4 (381) | 95.6 (525) |
| PRIVATE_KEY | 93.4 (468) | 86.9 (165) | 97.1 (303) | 87.5 (174) | 97.0 (294) |
| STREET | 98.5 (2351) | 98.3 (884) | 98.7 (1467) | 98.3 (939) | 98.7 (1412) |
| SURNAME | 98.3 (6244) | 97.8 (1970) | 98.5 (4274) | 97.9 (2172) | 98.6 (4072) |
| TELEPHONENUM | 95.7 (4308) | 96.8 (1329) | 95.2 (2979) | 97.1 (1443) | 95.1 (2865) |
| TIME | 94.1 (1420) | 97.1 (552) | 92.3 (868) | 96.9 (593) | 92.2 (827) |
| URL | 98.5 (1058) | 98.8 (335) | 98.4 (723) | 98.7 (374) | 98.5 (684) |
| ZIPCODE | 95.4 (1633) | 95.5 (576) | 95.3 (1057) | 95.8 (629) | 95.1 (1004) |

## Run B test split by part (track M)

old / new = same id and text as in v1's test split / v2 only; old_corpus / new_data = by id prefix (merged_relabeled_swept_dated vs targeted + LLM b1-b5). Exact-span percentages.

| Part | Docs | Micro P / R / F1 | Macro F1 | PII-free docs | PII-free FP |
|---|---|---|---|---|---|
| all | 15835 | 98.7 / 99.3 / 99.0 | 99.0 | 1787 | 1.5 |
| new | 6425 | 98.4 / 99.0 / 98.7 | 98.5 | 552 | 2.5 |
| old | 9410 | 98.9 / 99.5 / 99.2 | 99.4 | 1235 | 1.1 |
| new_data | 6900 | 98.4 / 99.0 / 98.7 | 98.5 | 583 | 2.7 |
| old_corpus | 8935 | 98.9 / 99.5 / 99.2 | 99.4 | 1204 | 0.9 |

| Label | all F1 (gold) | new F1 (gold) | old F1 (gold) | new_data F1 (gold) | old_corpus F1 (gold) |
|---|---|---|---|---|---|
| ACCESS_TOKEN | 98.8 (894) | 98.3 (420) | 99.2 (474) | 98.0 (451) | 99.6 (443) |
| AGE | 99.2 (1415) | 98.9 (424) | 99.2 (991) | 98.9 (465) | 99.3 (950) |
| API_KEY | 99.9 (1297) | 99.9 (576) | 99.9 (721) | 99.9 (608) | 99.9 (689) |
| AZ_DRIVER_LICENSE_NUMBER | 99.8 (1064) | 99.8 (659) | 99.8 (405) | 99.8 (688) | 99.7 (376) |
| AZ_FIN | 98.3 (1087) | 96.1 (433) | 99.7 (654) | 96.2 (456) | 99.8 (631) |
| AZ_ID_CARD_NUMBER | 99.8 (1214) | 99.8 (713) | 99.9 (501) | 99.8 (741) | 99.9 (473) |
| AZ_PASSPORT_NUMBER | 99.9 (666) | 99.7 (309) | 100.0 (357) | 99.7 (326) | 100.0 (340) |
| AZ_VOEN | 99.1 (611) | 98.4 (279) | 99.7 (332) | 98.5 (290) | 99.7 (321) |
| BUILDINGNUM | 99.4 (1444) | 99.3 (602) | 99.5 (842) | 99.3 (649) | 99.5 (795) |
| CARD_SECURITY_CODE | 98.4 (600) | 98.0 (244) | 98.6 (356) | 98.1 (260) | 98.5 (340) |
| CITY | 99.1 (3409) | 98.7 (1152) | 99.3 (2257) | 98.4 (1241) | 99.5 (2168) |
| DATE | 99.3 (8828) | 98.8 (2509) | 99.6 (6319) | 98.9 (2796) | 99.6 (6032) |
| EMAIL | 99.8 (5111) | 99.6 (1456) | 99.8 (3655) | 99.7 (1679) | 99.8 (3432) |
| GIVENNAME | 98.0 (7481) | 97.9 (2433) | 98.1 (5048) | 97.9 (2651) | 98.1 (4830) |
| IBAN | 99.7 (735) | 99.5 (303) | 99.9 (432) | 99.5 (322) | 99.9 (413) |
| ICCID | 100.0 (502) | 100.0 (238) | 100.0 (264) | 100.0 (243) | 100.0 (259) |
| IPV4_ADDRESS | 99.9 (997) | 99.9 (386) | 99.9 (611) | 99.9 (404) | 99.9 (593) |
| IPV6_ADDRESS | 100.0 (696) | 100.0 (420) | 100.0 (276) | 100.0 (464) | 100.0 (232) |
| MAC_ADDRESS | 99.6 (681) | 99.2 (369) | 100.0 (312) | 99.2 (392) | 100.0 (289) |
| PAYMENT_CARD_NUMBER | 98.4 (906) | 97.0 (349) | 99.2 (557) | 96.9 (381) | 99.4 (525) |
| PRIVATE_KEY | 95.4 (468) | 87.6 (165) | 99.8 (303) | 88.2 (174) | 99.8 (294) |
| STREET | 99.2 (2351) | 98.6 (884) | 99.6 (1467) | 98.6 (939) | 99.6 (1412) |
| SURNAME | 98.5 (6244) | 98.0 (1970) | 98.6 (4274) | 98.0 (2172) | 98.7 (4072) |
| TELEPHONENUM | 99.8 (4308) | 99.8 (1329) | 99.8 (2979) | 99.9 (1443) | 99.8 (2865) |
| TIME | 95.9 (1420) | 96.7 (552) | 95.3 (868) | 96.8 (593) | 95.2 (827) |
| URL | 99.7 (1058) | 99.9 (335) | 99.7 (723) | 99.9 (374) | 99.6 (684) |
| ZIPCODE | 99.4 (1633) | 98.7 (576) | 99.8 (1057) | 98.8 (629) | 99.8 (1004) |

### Slices: runb_test (exact recall / overlap recall / split spans)

| Slice | Value | Gold | R | M |
|---|---|---|---|---|
| doc:_adversarials | 0 | 53106 | 96.9 / 99.3 / 259 | 99.3 / 99.6 / 54 |
| doc:_adversarials | 1 | 2471 | 95.7 / 98.6 / 22 | 99.0 / 99.4 / 8 |
| doc:_adversarials | 2 | 1543 | 96.2 / 99.0 / 10 | 99.4 / 99.4 / 0 |
| doc:_adversarials | 3 | 0 | – / – / 0 | – / – / 0 |
| doc:_bucket | extreme | 2879 | 95.6 / 98.7 / 25 | 98.5 / 99.3 / 14 |
| doc:_bucket | long | 17022 | 96.5 / 99.1 / 48 | 99.4 / 99.5 / 11 |
| doc:_bucket | medium | 14930 | 97.3 / 99.5 / 60 | 99.5 / 99.7 / 10 |
| doc:_bucket | short | 9439 | 97.3 / 99.5 / 98 | 99.5 / 99.6 / 14 |
| doc:_bucket | very_long | 9343 | 97.0 / 99.5 / 19 | 99.6 / 99.8 / 4 |
| doc:_bucket | very_short | 3361 | 95.9 / 98.4 / 39 | 98.2 / 98.7 / 8 |
| doc:_gen_version | 01a97fd5f84a | 4798 | 96.3 / 99.0 / 72 | 98.9 / 99.3 / 22 |
| doc:_gen_version | 14e1626c5846 | 2150 | 96.0 / 99.0 / 18 | 99.0 / 99.3 / 5 |
| doc:_gen_version | 22f108b78dea | 2105 | 98.1 / 99.4 / 7 | 99.0 / 99.3 / 3 |
| doc:_gen_version | 5f82f117746a | 2317 | 96.6 / 99.2 / 9 | 99.4 / 99.7 / 5 |
| doc:_gen_version | c3e7de3b39f5 | 46 | 89.1 / 100.0 / 1 | 91.3 / 100.0 / 0 |
| doc:_gen_version | c91c89591c16 | 7833 | 97.8 / 99.2 / 35 | 98.9 / 99.2 / 9 |
| doc:_gen_version | d0e7f1dee7c2 | 2019 | 96.3 / 99.6 / 12 | 99.6 / 99.9 / 4 |
| doc:_gen_version | f680dbb6b892 | 509 | 98.4 / 99.2 / 3 | 98.8 / 98.8 / 0 |
| doc:_gen_version | f78568bf074c | 54 | 98.1 / 100.0 / 1 | 100.0 / 100.0 / 0 |
| doc:_hard_negatives | 0 | 49217 | 96.9 / 99.3 / 241 | 99.4 / 99.6 / 46 |
| doc:_hard_negatives | 1 | 3348 | 97.1 / 99.0 / 27 | 98.9 / 99.4 / 10 |
| doc:_hard_negatives | 2 | 2327 | 97.0 / 98.8 / 16 | 98.9 / 99.1 / 3 |
| doc:_hard_negatives | 3 | 1224 | 96.2 / 98.4 / 5 | 98.1 / 98.7 / 3 |
| doc:_hard_negatives | 4 | 398 | 94.5 / 99.5 / 0 | 99.5 / 99.5 / 0 |
| doc:_hard_negatives | 5 | 251 | 96.0 / 99.6 / 1 | 100.0 / 100.0 / 0 |
| doc:_hard_negatives | 6 | 280 | 93.9 / 98.6 / 1 | 99.3 / 99.3 / 0 |
| doc:_hard_negatives | 7 | 75 | 93.3 / 98.7 / 0 | 100.0 / 100.0 / 0 |
| doc:_old | True | 35289 | 96.7 / 99.3 / 133 | 99.5 / 99.7 / 14 |
| doc:_pii_free | False | 21742 | 97.1 / 99.2 / 158 | 99.0 / 99.4 / 48 |
| doc:_pii_free | True | 89 | 92.1 / 100.0 / 0 | 100.0 / 100.0 / 0 |
| doc:_register | anxious and confused | 3920 | 97.0 / 99.4 / 26 | 99.3 / 99.4 / 4 |
| doc:_register | apologetic | 3460 | 97.1 / 99.2 / 12 | 99.3 / 99.5 / 3 |
| doc:_register | bureaucratic | 1018 | 97.2 / 99.3 / 6 | 99.1 / 99.5 / 4 |
| doc:_register | bureaucratic and officious | 3721 | 96.2 / 99.5 / 9 | 99.5 / 99.7 / 3 |
| doc:_register | casual with typos and abbreviations | 4430 | 97.0 / 99.3 / 7 | 99.4 / 99.5 / 1 |
| doc:_register | chat | 852 | 95.3 / 98.8 / 15 | 98.6 / 99.6 / 9 |
| doc:_register | empathetic customer-service | 3606 | 97.9 / 99.8 / 9 | 99.5 / 99.7 / 4 |
| doc:_register | formal and businesslike | 3470 | 96.6 / 99.5 / 18 | 98.9 / 99.6 / 7 |
| doc:_register | friendly with light humour | 3817 | 97.3 / 99.4 / 17 | 99.3 / 99.5 / 3 |
| doc:_register | frustrated and complaining | 3911 | 97.4 / 99.5 / 15 | 99.7 / 99.7 / 3 |
| doc:_register | matter-of-fact administrative | 3808 | 96.1 / 99.2 / 24 | 99.4 / 99.6 / 1 |
| doc:_register | note | 1030 | 96.7 / 99.1 / 14 | 99.0 / 99.0 / 0 |
| doc:_register | polite | 928 | 96.2 / 99.2 / 20 | 98.6 / 99.2 / 6 |
| doc:_register | polite but firm | 3244 | 96.4 / 99.4 / 11 | 99.6 / 99.7 / 0 |
| doc:_register | technical | 970 | 95.7 / 98.7 / 17 | 98.9 / 99.2 / 3 |
| doc:_register | technical and precise | 3184 | 96.7 / 98.9 / 17 | 99.2 / 99.2 / 2 |
| doc:_register | terse and clipped | 4398 | 96.4 / 98.6 / 22 | 99.4 / 99.6 / 5 |
| doc:_register | urgent and escalating | 3664 | 96.5 / 99.5 / 22 | 99.6 / 99.7 / 3 |
| doc:_register | warm and conversational | 3689 | 97.8 / 99.3 / 10 | 99.3 / 99.5 / 1 |
| doc:_source | llm | 52322 | 96.9 / 99.3 / 219 | 99.4 / 99.6 / 40 |
| doc:_source | targeted | 4798 | 96.3 / 99.0 / 72 | 98.9 / 99.3 / 22 |
| doc:lang | az | 57120 | 96.8 / 99.3 / 291 | 99.3 / 99.6 / 62 |
| doc:runb_origin | new_data | 21831 | 97.0 / 99.2 / 158 | 99.0 / 99.4 / 48 |
| doc:runb_origin | old_corpus | 35289 | 96.7 / 99.3 / 133 | 99.5 / 99.7 / 14 |
| doc:runb_part | new | 20085 | 97.0 / 99.2 / 146 | 99.0 / 99.3 / 45 |
| doc:runb_part | old | 37035 | 96.8 / 99.3 / 145 | 99.5 / 99.7 / 17 |
| doc:density | 0 | 0 | – / – / 0 | – / – / 0 |
| doc:density | 1 | 4112 | 95.5 / 99.0 / 48 | 98.7 / 99.2 / 20 |
| doc:density | 2-3 | 11091 | 96.3 / 99.3 / 76 | 99.2 / 99.4 / 15 |
| doc:density | 4-6 | 13934 | 97.6 / 99.3 / 51 | 99.4 / 99.5 / 12 |
| … | 1 more rows in the JSON | | |

Calibration (score bins vs precision) is in the JSON. It is reported only and is never used to set a threshold (A2.2).
