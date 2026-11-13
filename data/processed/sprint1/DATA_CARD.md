# sprint1-v1 data card

- `data_version`: **sprint1-v1**
- git SHA: `8422088425ae63d5b966ffc3171f4b5c4fd20587`
- built: 2026-10-06, `python scripts/build_sprint_mix.py `
- targeted build: `-n 25000 --seed 20261001`; split and replay seed: 20261001
- replay: `data/processed/merged_relabeled_swept_dated`, 60,000 train (15,000 per language) + 5,000 val
- LLM input (D-19d): sprint1_llm_b1.clean.jsonl, sprint1_llm_b2.clean.jsonl, sprint1_llm_b3.clean.jsonl, sprint1_llm_b4.clean.jsonl

## Gates

All exited 0: `validate_corpus.py` on the targeted file and on each LLM batch, `leakage_guard.py` on all five files with `--bench-docs` `data/benchmark_v3/pii_az_benchmark_v3_structured_9780.jsonl`.

- new documents in: 47,855; after `prepare_splits` (re-validation and exact-text dedup): 47,855 (0 dropped)
- D-19c: 13 documents moved from val/test to train because their normalised text was in another split. After the move, exact and normalised text overlap between splits is 0.

## Documents

| source | train | val | test | total |
|---|---|---|---|---|
| targeted | 20,013 | 2,531 | 2,456 | 25,000 |
| llm | 18,281 | 2,250 | 2,324 | 22,855 |
| replay | 60,000 | 5,000 | 0 | 65,000 |

| language | train | val | test |
|---|---|---|---|
| az | 53,294 | 6,031 | 4,780 |
| en | 15,000 | 1,250 | 0 |
| tr | 15,000 | 1,250 | 0 |
| ru | 15,000 | 1,250 | 0 |

New data in train: 38,294 of 98,294 = **39.0%** (target about 40%, D-20).

## Entities per label

| label | train | val | test |
|---|---|---|---|
| API_KEY | 7,845 | 768 | 363 |
| ACCESS_TOKEN | 5,001 | 532 | 258 |
| PRIVATE_KEY | 2,706 | 272 | 101 |
| PAYMENT_CARD_NUMBER | 5,859 | 586 | 284 |
| IBAN | 4,775 | 471 | 223 |
| CARD_SECURITY_CODE | 3,374 | 325 | 165 |
| IPV4_ADDRESS | 5,848 | 581 | 244 |
| IPV6_ADDRESS | 3,661 | 411 | 269 |
| MAC_ADDRESS | 4,166 | 478 | 301 |
| URL | 6,437 | 584 | 217 |
| ICCID | 3,049 | 302 | 192 |
| GIVENNAME | 46,503 | 4,173 | 1,639 |
| SURNAME | 37,352 | 3,475 | 1,330 |
| EMAIL | 29,614 | 2,726 | 898 |
| TELEPHONENUM | 24,606 | 2,334 | 790 |
| DATE | 55,172 | 4,971 | 1,785 |
| TIME | 8,277 | 865 | 373 |
| AGE | 7,907 | 766 | 263 |
| CITY | 19,717 | 1,870 | 742 |
| STREET | 13,664 | 1,353 | 554 |
| BUILDINGNUM | 9,990 | 929 | 354 |
| ZIPCODE | 9,916 | 927 | 412 |
| AZ_FIN | 6,656 | 699 | 291 |
| AZ_ID_CARD_NUMBER | 7,585 | 811 | 527 |
| AZ_PASSPORT_NUMBER | 4,682 | 490 | 252 |
| AZ_VOEN | 4,136 | 400 | 237 |
| AZ_DRIVER_LICENSE_NUMBER | 6,434 | 717 | 543 |

## New data (targeted + LLM, all splits)

| source | documents | with decoys | PII-free | single-entity |
|---|---|---|---|---|
| targeted | 25,000 | 41.2% | 9.4% | 53.0% |
| llm | 22,855 | 33.1% | 6.5% | 24.7% |
| all new | 47,855 | 37.3% | 8.0% | 39.4% |

### Decoys per `_decoys.kind`

| kind | count |
|---|---|
| AMOUNT | 242 |
| BUILD_HASH | 309 |
| CONTAINER_ID | 241 |
| COORDINATES | 271 |
| DATE_LIKE_ID | 320 |
| DURATION | 290 |
| EMAIL_LIKE_HANDLE | 347 |
| EMPLOYEE_ID | 241 |
| ERROR_CODE | 271 |
| GIT_SHA | 264 |
| HEX_BLOB | 233 |
| IBAN_BAD_CHECKSUM | 350 |
| IMEI_BAD_LUHN | 386 |
| INVOICE_ID | 278 |
| IP_INVALID_OCTET | 349 |
| IP_LIKE_VERSION | 372 |
| ISBN | 378 |
| LICENSE_KEY_PRODUCT | 256 |
| LOYALTY_CARD_LUHN_BAD | 366 |
| MAC_LIKE_HASH | 393 |
| MASKED_CARD | 341 |
| MASKED_EMAIL | 403 |
| MD5 | 234 |
| MEM_ADDR | 254 |
| OBFUSCATED_EMAIL | 355 |
| ORDER_ID | 237 |
| PARTIAL_PHONE | 372 |
| PERCENT | 252 |
| PLATE_LIKE_CODE | 413 |
| PORT | 310 |
| REDACTED | 380 |
| REF_CODE | 268 |
| SESSION_COUNT | 294 |
| SHA256 | 241 |
| SKU | 312 |
| SSN_LIKE_CODE | 393 |
| TIMESTAMP | 286 |
| TRACKING | 270 |
| TRUNCATED_API_KEY | 358 |
| URL_NO_TOKEN | 325 |
| UUID | 234 |
| VERSION | 312 |
| VIN_BAD_CHECKDIGIT | 405 |
| age_currency_amount | 322 |
| age_implausible | 291 |
| age_negative | 304 |
| archive_folder | 325 |
| campaign_code | 310 |
| card_luhn_invalid | 299 |
| cvv_1_2_digits | 297 |
| cvv_5_digits | 336 |
| cvv_letters | 280 |
| cvv_separator | 333 |
| date_bad_month | 303 |
| date_clause_number | 328 |
| date_impossible_day | 323 |
| date_iso_out_of_range | 301 |
| date_version_string | 326 |
| fin_6_chars | 317 |
| fin_8_9_chars | 295 |
| fin_with_hyphen | 347 |
| fin_with_i_or_o | 305 |
| floor_number | 591 |
| homograph_noun | 1,352 |
| iban_truncated | 322 |
| iccid_short_prefix | 315 |
| id_card_hyphen | 316 |
| id_card_too_long | 335 |
| id_card_too_short | 321 |
| internal_reference | 325 |
| ipv4_octet_over_255 | 297 |
| ipv6_triple_colon | 307 |
| licence_hyphen | 311 |
| licence_too_short | 309 |
| mac_3_to_5_groups | 290 |
| office_number | 606 |
| order_number | 301 |
| passport_letter_in_digits | 288 |
| passport_wrong_length | 310 |
| policy_city_as_project | 614 |
| policy_passport_dummy | 323 |
| policy_sequential | 289 |
| policy_street_as_topic | 612 |
| policy_surname_in_company | 617 |
| policy_test_card | 314 |
| policy_version_time | 289 |
| room_number | 613 |
| sentence_initial_genitive | 853 |
| sentence_initial_locative | 826 |
| time_3_digit_minutes | 321 |
| time_bad_hour | 307 |
| time_bad_minute | 309 |
| tracking_code_15_16 | 323 |
| voen_letters_in_digits | 318 |
| voen_wrong_length | 313 |
| zip_shape_in_iban_field | 322 |
| zip_wrong_length | 321 |

### Format mix (`_doc_type`)

| `_doc_type` | targeted | llm |
|---|---|---|
| api_documentation | 0 | 560 |
| bank_correspondence | 0 | 543 |
| bug_report | 0 | 564 |
| call_center_transcript | 0 | 501 |
| code_review | 0 | 564 |
| complaint_letter | 0 | 603 |
| config_snippet | 0 | 495 |
| contract_clause | 0 | 585 |
| contrast_ipv6_mac | 908 | 0 |
| contrast_licence_id | 907 | 0 |
| contrast_token_key | 935 | 0 |
| court_filing | 0 | 543 |
| crm_note | 0 | 587 |
| customer_email | 0 | 549 |
| customs_declaration | 0 | 531 |
| cv_resume | 0 | 553 |
| decoy_pair | 6,500 | 0 |
| email_thread | 0 | 495 |
| forum_post | 0 | 541 |
| government_form | 0 | 583 |
| homograph_pair | 1,250 | 0 |
| hr_record | 0 | 574 |
| incident_postmortem | 0 | 530 |
| inflected | 3,000 | 0 |
| insurance_claim | 0 | 514 |
| internal_wiki | 0 | 555 |
| invoice | 0 | 511 |
| lab_report | 0 | 534 |
| legal_notice | 0 | 590 |
| live_chat | 0 | 557 |
| loan_application | 0 | 531 |
| medical_note | 0 | 541 |
| meeting_notes | 0 | 569 |
| minimal_context | 1,250 | 0 |
| onboarding_doc | 0 | 599 |
| pii_free | 2,250 | 0 |
| police_report | 0 | 523 |
| prose | 3,750 | 0 |
| receipt | 0 | 451 |
| rental_agreement | 0 | 578 |
| runbook | 0 | 530 |
| school_record | 0 | 547 |
| shipping_manifest | 0 | 479 |
| social_media | 0 | 569 |
| structured_config | 334 | 0 |
| structured_csv_header | 478 | 0 |
| structured_csv_noheader | 478 | 0 |
| structured_csv_snake | 478 | 0 |
| structured_dialogue | 478 | 0 |
| structured_json | 477 | 0 |
| structured_key_value | 573 | 0 |
| structured_log | 477 | 0 |
| structured_pipe_table | 477 | 0 |
| support_ticket | 0 | 514 |
| survey_response | 0 | 599 |
| technical_log | 0 | 516 |
| utility_bill | 0 | 504 |
| vehicle_record | 0 | 537 |
| voicemail_transcript | 0 | 541 |
| whatsapp_thread | 0 | 565 |

### Suffixed name/city/street mentions per case (targeted)

From `_suffixes`; LLM records carry no case tags, so they are left out.

| case | GIVENNAME (5,875 mentions) | SURNAME (4,694 mentions) | CITY (2,788 mentions) | STREET (2,155 mentions) |
|---|---|---|---|---|
| abl | 168 (2.9%) | 89 (1.9%) | 65 (2.3%) | 39 (1.8%) |
| acc | 107 (1.8%) | 106 (2.3%) | 95 (3.4%) | 53 (2.5%) |
| any case | 1,715 (29.2%) | 2,724 (58.0%) | 1,105 (39.6%) | 427 (19.8%) |
| cond | 26 (0.4%) | 22 (0.5%) | 0 (0.0%) | 0 (0.0%) |
| cop | 111 (1.9%) | 120 (2.6%) | 83 (3.0%) | 47 (2.2%) |
| dat | 351 (6.0%) | 7 (0.1%) | 25 (0.9%) | 8 (0.4%) |
| gen | 190 (3.2%) | 95 (2.0%) | 69 (2.5%) | 38 (1.8%) |
| gen_ki | 49 (0.8%) | 42 (0.9%) | 0 (0.0%) | 0 (0.0%) |
| gil | 57 (1.0%) | 16 (0.3%) | 0 (0.0%) | 0 (0.0%) |
| gil_abl | 19 (0.3%) | 17 (0.4%) | 0 (0.0%) | 0 (0.0%) |
| gil_dat | 29 (0.5%) | 19 (0.4%) | 0 (0.0%) | 0 (0.0%) |
| gil_gen | 12 (0.2%) | 24 (0.5%) | 0 (0.0%) | 0 (0.0%) |
| gil_loc | 22 (0.4%) | 26 (0.6%) | 0 (0.0%) | 0 (0.0%) |
| ins | 200 (3.4%) | 74 (1.6%) | 59 (2.1%) | 29 (1.3%) |
| loc | 118 (2.0%) | 114 (2.4%) | 108 (3.9%) | 51 (2.4%) |
| loc_cond | 0 (0.0%) | 0 (0.0%) | 48 (1.7%) | 0 (0.0%) |
| loc_cop | 0 (0.0%) | 0 (0.0%) | 67 (2.4%) | 42 (1.9%) |
| loc_past | 0 (0.0%) | 0 (0.0%) | 42 (1.5%) | 0 (0.0%) |
| loc_past1 | 0 (0.0%) | 0 (0.0%) | 36 (1.3%) | 0 (0.0%) |
| loc_pred1 | 0 (0.0%) | 0 (0.0%) | 37 (1.3%) | 23 (1.1%) |
| loc_pred1pl | 0 (0.0%) | 0 (0.0%) | 30 (1.1%) | 0 (0.0%) |
| loc_pred2 | 0 (0.0%) | 0 (0.0%) | 30 (1.1%) | 0 (0.0%) |
| loc_q | 0 (0.0%) | 0 (0.0%) | 45 (1.6%) | 21 (1.0%) |
| past | 23 (0.4%) | 19 (0.4%) | 0 (0.0%) | 0 (0.0%) |
| pl | 0 (0.0%) | 349 (7.4%) | 0 (0.0%) | 0 (0.0%) |
| pl_abl | 0 (0.0%) | 349 (7.4%) | 0 (0.0%) | 0 (0.0%) |
| pl_dat | 0 (0.0%) | 349 (7.4%) | 0 (0.0%) | 0 (0.0%) |
| pl_gen | 0 (0.0%) | 349 (7.4%) | 0 (0.0%) | 0 (0.0%) |
| pl_loc | 0 (0.0%) | 349 (7.4%) | 0 (0.0%) | 0 (0.0%) |
| poss1 | 60 (1.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| poss1pl | 0 (0.0%) | 0 (0.0%) | 60 (2.2%) | 0 (0.0%) |
| pred1 | 37 (0.6%) | 48 (1.0%) | 0 (0.0%) | 0 (0.0%) |
| pred_formal | 15 (0.3%) | 21 (0.4%) | 0 (0.0%) | 0 (0.0%) |
| q | 23 (0.4%) | 16 (0.3%) | 15 (0.5%) | 0 (0.0%) |
| rel | 98 (1.7%) | 104 (2.2%) | 92 (3.3%) | 55 (2.6%) |
| term_can | 0 (0.0%) | 0 (0.0%) | 60 (2.2%) | 0 (0.0%) |
| term_dek | 0 (0.0%) | 0 (0.0%) | 39 (1.4%) | 21 (1.0%) |

## Checks

- PASS: all 27 labels in train
- PASS: decoys in ≥ 25% of new documents: 37.3%
- PASS: PII-free ≈ 10% of new documents: 8.0%
