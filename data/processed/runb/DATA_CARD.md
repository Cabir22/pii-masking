# runb-az-v4.2 data card

- `data_version`: **runb-az-v4.2**
- git SHA: `425f301affc443ef05141812ba5ee0e8d38c1f5e`
- built: 2026-10-21, `python scripts/build_sprint_mix.py --az-only --data-version runb-az-v4.2 --v4-clean --llm data/raw/sprint1_llm_b1.clean.jsonl data/raw/sprint1_llm_b2.clean.jsonl data/raw/sprint1_llm_b3.clean.jsonl data/raw/sprint1_llm_b4.clean.jsonl data/raw/sprint1_llm_b5.clean.jsonl data/raw/sprint1_llm_b6.clean.jsonl`
- targeted build: `-n 37000 --seed 20261001`; split and replay seed: 20261001
- Azerbaijani only (D-23b), no replay: the `lang == "az"` documents of `data/processed/merged_relabeled_swept_dated` in their own splits, minus the P2-16 drop list `data/processed/merged_relabeled_swept_dated/az_drop_list.jsonl` (15,346 documents)
- LLM input: sprint1_llm_b1.clean.jsonl, sprint1_llm_b2.clean.jsonl, sprint1_llm_b3.clean.jsonl, sprint1_llm_b4.clean.jsonl, sprint1_llm_b5.clean.jsonl, sprint1_llm_b6.clean.jsonl

## Gates

All exited 0: `validate_corpus.py` on the targeted file and on each LLM batch, `leakage_guard.py` on all 7 files with `--bench-docs` `data/benchmark_v3/pii_az_benchmark_v3_structured_9780.jsonl`.

- new documents in: 99,250; after `prepare_splits` (re-validation and exact-text dedup): 99,250 (0 dropped)
- v4.1 (data audit A2): the new documents are split by template (`prepare_splits --group-split template`): documents that differ only in their values and look-alikes (`_skeleton`) are always in the same split.
- D-19c: 0 documents moved from val/test to train because their normalised text was in another split. After the move, exact and normalised text overlap between splits is 0.

- D-23b: after the old documents are added, no normalised text is in more than one split (new val/test vs old train and the reverse; the build stops otherwise).

## Documents

| source | train | val | test | total |
|---|---|---|---|---|
| targeted | 29,851 | 3,579 | 3,570 | 37,000 |
| llm | 49,548 | 6,344 | 6,358 | 62,250 |
| old | 63,069 | 7,841 | 7,819 | 78,729 |

| language | train | val | test |
|---|---|---|---|
| az | 142,468 | 17,764 | 17,747 |
| en | 0 | 0 | 0 |
| tr | 0 | 0 | 0 |
| ru | 0 | 0 | 0 |

### Old and new per split

| split | old | new | total | new share |
|---|---|---|---|---|
| train | 63,069 | 79,399 | 142,468 | 55.7% |
| val | 7,841 | 9,923 | 17,764 | 55.9% |
| test | 7,819 | 9,928 | 17,747 | 55.9% |

### Old documents left out (P2-16 drop list, first reason)

| reason | train | val | test | total |
|---|---|---|---|---|
| planned_value_unlabelled | 2,268 | 334 | 286 | 2,888 |
| repeat_mention_incomplete | 21 | 1 | 7 | 29 |
| resolver_drift | 156 | 25 | 23 | 204 |
| unlabeled_pii_leak | 2,916 | 351 | 398 | 3,665 |
| unlabelled_standalone_date | 147 | 17 | 11 | 175 |
| unplanned_pii | 4,593 | 594 | 608 | 5,795 |
| validator_failure | 2,079 | 239 | 272 | 2,590 |

## v4 cleaning (D-51f, D-51g)

`piigen.v4_clean.clean_doc` on every source; lexicon `scripts/piigen/v4_clean_lexicon.json` (sha256 `ba8bbdfd7cab4dc2cf87ba36bc8e579f33983811badc485e24265f04a3586e25`). Cleaned copies of the targeted and LLM inputs: `data/processed/runb/v4_clean_inputs`; the originals are untouched. Each cell: values labelled / values unlabelled / spans trimmed / documents dropped.

| rule | targeted | llm_b1 | llm_b2 | llm_b3 | llm_b4 | llm_b5 | llm_b6 | old_train | old_val | old_test |
|---|---|---|---|---|---|---|---|---|---|---|
| R1 |  |  |  |  |  |  |  | 0 / 0 / 0 / 7,713 | 0 / 0 / 0 / 950 | 0 / 0 / 0 / 953 |
| R2 |  | 0 / 57 / 0 / 0 | 0 / 57 / 0 / 0 | 0 / 147 / 0 / 0 | 0 / 68 / 0 / 0 | 0 / 311 / 0 / 0 | 0 / 110 / 0 / 0 | 0 / 749 / 0 / 0 | 0 / 92 / 0 / 0 | 0 / 93 / 0 / 0 |
| R3 |  | 0 / 0 / 54 / 0 | 0 / 0 / 58 / 0 | 0 / 0 / 53 / 0 | 0 / 0 / 59 / 0 | 0 / 0 / 198 / 0 | 0 / 0 / 192 / 0 | 0 / 0 / 647 / 0 | 0 / 0 / 84 / 0 | 0 / 0 / 80 / 0 |
| R4 |  | 512 / 0 / 0 / 1 | 87 / 0 / 0 / 0 | 146 / 0 / 0 / 0 | 224 / 0 / 0 / 0 | 507 / 0 / 0 / 1 | 13 / 0 / 0 / 1 | 7,366 / 0 / 0 / 14 | 1,002 / 0 / 0 / 0 | 916 / 0 / 0 / 0 |
| R5 |  |  | 2 / 0 / 0 / 0 | 2 / 0 / 0 / 0 |  | 2 / 0 / 0 / 0 |  | 1,647 / 0 / 0 / 1 | 192 / 0 / 0 / 0 | 218 / 0 / 0 / 1 |
| R6 |  | 0 / 9 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 5 / 0 / 0 | 0 / 7 / 0 / 0 | 0 / 11 / 0 / 0 | 0 / 362 / 0 / 0 | 0 / 198 / 0 / 0 | 0 / 16 / 0 / 0 | 0 / 22 / 0 / 0 |
| R7 |  |  |  |  |  |  |  | 0 / 85 / 0 / 0 | 0 / 13 / 0 / 0 | 0 / 10 / 0 / 0 |
| R8 |  | 0 / 0 / 0 / 161 | 0 / 0 / 0 / 221 | 0 / 0 / 0 / 255 | 0 / 0 / 0 / 228 | 0 / 0 / 0 / 812 | 0 / 0 / 0 / 949 | 0 / 0 / 0 / 1,310 | 0 / 0 / 0 / 180 | 0 / 0 / 0 / 154 |
| R9 |  | 6 / 0 / 0 / 0 | 7 / 0 / 0 / 0 | 7 / 0 / 0 / 0 | 2 / 0 / 0 / 1 | 8 / 0 / 0 / 2 |  | 72 / 0 / 0 / 16 | 3 / 0 / 0 / 3 | 4 / 0 / 0 / 2 |
| R10 |  | 88 / 0 / 0 / 0 | 88 / 0 / 0 / 0 | 83 / 0 / 0 / 0 | 125 / 0 / 0 / 0 | 130 / 0 / 0 / 0 | 42 / 0 / 0 / 0 | 995 / 0 / 0 / 0 | 128 / 0 / 0 / 0 | 107 / 0 / 0 / 0 |
| GATE |  | 0 / 0 / 0 / 1 | 0 / 0 / 0 / 2 | 0 / 0 / 0 / 3 |  | 0 / 0 / 0 / 3 |  | 0 / 0 / 0 / 28 | 0 / 0 / 0 / 5 | 0 / 0 / 0 / 6 |
| documents in | 37,000 | 4,874 | 5,480 | 5,667 | 5,687 | 20,351 | 22,832 | 72,151 | 8,979 | 8,935 |
| documents out | 37,000 | 4,711 | 5,257 | 5,409 | 5,458 | 19,533 | 21,882 | 63,069 | 7,841 | 7,819 |

Rules: R1 D-47/D-45b drop (old only), R2 TIME/DATE in stamps, R3 `-ci il` out of DATE, R4 persona names, R5 half-labelled names, R6 city heading an institution/project, R7 false SURNAME, R8 checksum-only look-alikes, R9 unlabelled ages, R10 clock times after `saat`/`vaxtı`, GATE a record that would fail a check it passed before.

Kept, for the team: documents with an `IMEI_BAD_LUHN` look-alike that has a card's shape (checksum-only, not in D-51d's list): {'llm_b1': 2, 'llm_b2': 3, 'llm_b4': 3, 'llm_b5': 5, 'llm_b6': 9}.

New data in train: 79,399 of 142,468 = **55.7%** (D-23b: about 31% before the drop list).

## Entities per label

| label | train | val | test |
|---|---|---|---|
| API_KEY | 11,027 | 1,354 | 1,325 |
| ACCESS_TOKEN | 7,468 | 961 | 976 |
| PRIVATE_KEY | 3,313 | 383 | 398 |
| PAYMENT_CARD_NUMBER | 8,062 | 1,005 | 997 |
| IBAN | 6,523 | 804 | 786 |
| CARD_SECURITY_CODE | 6,394 | 791 | 834 |
| IPV4_ADDRESS | 8,433 | 1,054 | 1,153 |
| IPV6_ADDRESS | 6,420 | 754 | 852 |
| MAC_ADDRESS | 6,443 | 816 | 813 |
| URL | 8,738 | 1,112 | 1,080 |
| ICCID | 3,914 | 486 | 528 |
| GIVENNAME | 91,752 | 11,522 | 11,832 |
| SURNAME | 64,145 | 8,108 | 8,192 |
| EMAIL | 41,269 | 5,176 | 5,230 |
| TELEPHONENUM | 35,242 | 4,526 | 4,494 |
| DATE | 68,907 | 8,639 | 8,698 |
| TIME | 12,975 | 1,711 | 1,590 |
| AGE | 11,605 | 1,462 | 1,538 |
| CITY | 28,784 | 3,669 | 3,676 |
| STREET | 18,851 | 2,356 | 2,384 |
| BUILDINGNUM | 12,273 | 1,567 | 1,518 |
| ZIPCODE | 14,362 | 1,841 | 1,798 |
| AZ_FIN | 8,911 | 1,121 | 1,108 |
| AZ_ID_CARD_NUMBER | 13,356 | 1,677 | 1,655 |
| AZ_PASSPORT_NUMBER | 6,099 | 758 | 678 |
| AZ_VOEN | 5,537 | 680 | 661 |
| AZ_DRIVER_LICENSE_NUMBER | 10,965 | 1,388 | 1,378 |

## New data (targeted + LLM, all splits)

| source | documents | with decoys | PII-free | single-entity |
|---|---|---|---|---|
| targeted | 37,000 | 64.5% | 10.1% | 43.3% |
| llm | 62,250 | 32.5% | 7.0% | 22.7% |
| all new | 99,250 | 44.4% | 8.2% | 30.4% |

### Decoys per `_decoys.kind`

| kind | count |
|---|---|
| AMOUNT | 621 |
| BUILD_HASH | 720 |
| CONTAINER_ID | 628 |
| COORDINATES | 698 |
| DATE_LIKE_ID | 819 |
| DURATION | 672 |
| EMAIL_LIKE_HANDLE | 888 |
| EMPLOYEE_ID | 647 |
| ERROR_CODE | 685 |
| GIT_SHA | 637 |
| HEX_BLOB | 655 |
| IMEI_BAD_LUHN | 919 |
| INVOICE_ID | 701 |
| IP_INVALID_OCTET | 844 |
| IP_LIKE_VERSION | 942 |
| ISBN | 859 |
| LICENSE_KEY_PRODUCT | 637 |
| MAC_LIKE_HASH | 986 |
| MASKED_CARD | 867 |
| MASKED_EMAIL | 969 |
| MD5 | 635 |
| MEM_ADDR | 635 |
| OBFUSCATED_EMAIL | 901 |
| ORDER_ID | 715 |
| PARTIAL_PHONE | 858 |
| PERCENT | 672 |
| PLATE_LIKE_CODE | 1,049 |
| PORT | 727 |
| REDACTED | 960 |
| REF_CODE | 729 |
| SESSION_COUNT | 677 |
| SHA256 | 626 |
| SKU | 700 |
| SSN_LIKE_CODE | 956 |
| TIMESTAMP | 1,519 |
| TRACKING | 705 |
| TRUNCATED_API_KEY | 873 |
| URL_NO_TOKEN | 816 |
| UUID | 621 |
| VERSION | 713 |
| VIN_BAD_CHECKDIGIT | 946 |
| age_currency_amount | 590 |
| age_implausible | 556 |
| age_negative | 565 |
| age_shaped_number | 468 |
| api_key_short | 221 |
| api_key_short_number | 90 |
| archive_folder | 752 |
| campaign_code | 753 |
| caps_heading_control | 198 |
| card_wrong_length | 820 |
| code_in_name_slot | 183 |
| cvv_1_2_digits | 738 |
| cvv_5_digits | 929 |
| cvv_letters | 477 |
| cvv_separator | 345 |
| cvv_sequential_5 | 420 |
| date_bad_month | 2,751 |
| date_clause_number | 802 |
| date_feb_invalid | 1,077 |
| date_impossible_day | 2,729 |
| date_iso_out_of_range | 1,140 |
| date_month_near | 1,078 |
| date_version_string | 872 |
| door_code | 118 |
| email_dotless_domain | 334 |
| email_double_at | 360 |
| email_localhost | 345 |
| email_no_at | 334 |
| fin_8_9_chars | 631 |
| fin_dummy_pattern | 120 |
| fin_short_number | 239 |
| fin_with_hyphen | 920 |
| floor_number | 1,037 |
| homograph_noun | 1,458 |
| iban_country_code | 139 |
| iban_fragment_short | 231 |
| iban_short_account | 460 |
| iban_truncated | 661 |
| iccid_short_prefix | 645 |
| iccid_wrong_prefix | 208 |
| id_card_hyphen | 515 |
| id_card_short_number | 118 |
| id_card_too_long | 558 |
| id_card_too_short | 513 |
| image_digest | 237 |
| internal_reference | 810 |
| ipv4_octet_over_255 | 477 |
| ipv4_over_255_mixed | 90 |
| ipv4_placeholder | 45 |
| ipv4_short_over_255 | 135 |
| ipv4_three_octets | 180 |
| ipv6_compressed_bad | 444 |
| ipv6_non_hex | 203 |
| ipv6_triple_colon | 498 |
| ipv6_two_compressions | 207 |
| jwt_two_segments | 202 |
| kinship_possessive | 178 |
| licence_hyphen | 535 |
| licence_three_letters | 393 |
| licence_too_short | 545 |
| line_start_control | 1,246 |
| mac_3_to_5_groups | 458 |
| mac_fragment_dashed | 90 |
| mac_letters_only | 148 |
| namelist_control | 393 |
| office_number | 1,015 |
| order_number | 529 |
| passport_letter_in_digits | 507 |
| passport_wrong_length | 533 |
| place_word_topic | 934 |
| policy_city_as_project | 741 |
| policy_city_in_brand | 497 |
| policy_city_in_institution | 387 |
| policy_foreign_brand | 471 |
| policy_givenname_in_company | 456 |
| policy_passport_dummy | 519 |
| policy_sequential | 479 |
| policy_sequential_ipv4 | 54 |
| policy_sequential_time | 54 |
| policy_street_as_topic | 717 |
| policy_surname_in_company | 791 |
| policy_test_card | 511 |
| policy_version_time | 461 |
| private_key_placeholder | 359 |
| public_key_block | 513 |
| public_key_ssh | 678 |
| reference_19_digits | 208 |
| role_word_control | 68 |
| room_code | 117 |
| room_number | 1,024 |
| sentence_initial_genitive | 1,327 |
| sentence_initial_locative | 1,335 |
| signature_title_only | 20 |
| time_3_digit_minutes | 519 |
| time_bad_hour | 702 |
| time_bad_minute | 717 |
| time_hour_near | 305 |
| time_line_stamp | 1,665 |
| time_minute_near | 305 |
| token_prefix_only | 214 |
| token_short_number | 90 |
| village_descriptor | 280 |
| voen_letters_in_digits | 529 |
| voen_nine_digits | 371 |
| voen_short_number | 117 |
| voen_wrong_length | 517 |
| zip_shape_as_code | 193 |
| zip_shape_in_iban_field | 517 |
| zip_two_digits | 199 |
| zip_wrong_length | 1,319 |

### Format mix (`_doc_type`)

| `_doc_type` | targeted | llm |
|---|---|---|
| api_documentation | 0 | 952 |
| bank_correspondence | 0 | 990 |
| bug_report | 0 | 936 |
| call_center_transcript | 0 | 943 |
| clerical | 586 | 0 |
| code_review | 0 | 966 |
| complaint_letter | 0 | 1,043 |
| config_snippet | 0 | 865 |
| contract_clause | 0 | 1,026 |
| contrast_ipv6_mac | 947 | 0 |
| contrast_key_pair | 398 | 0 |
| contrast_licence_id | 947 | 0 |
| contrast_token_key | 557 | 0 |
| court_announcement | 0 | 2,488 |
| court_filing | 0 | 3,626 |
| crm_note | 0 | 1,061 |
| cross_anchor | 875 | 0 |
| customer_email | 0 | 1,065 |
| customs_declaration | 0 | 928 |
| cv_resume | 0 | 956 |
| decoy_pair | 8,510 | 0 |
| edges | 438 | 0 |
| email_thread | 0 | 881 |
| form | 2,516 | 0 |
| forum_post | 0 | 997 |
| government_form | 0 | 3,759 |
| homograph_pair | 1,339 | 0 |
| hr_record | 0 | 962 |
| incident_postmortem | 0 | 959 |
| inflected | 3,145 | 0 |
| insurance_claim | 0 | 924 |
| internal_wiki | 0 | 1,006 |
| invoice | 0 | 901 |
| key_placeholder | 200 | 0 |
| lab_report | 0 | 911 |
| legal_notice | 0 | 3,769 |
| live_chat | 0 | 977 |
| loan_application | 0 | 973 |
| locative | 413 | 0 |
| medical_note | 0 | 970 |
| meeting_notes | 0 | 973 |
| minimal_context | 1,339 | 0 |
| namelist | 875 | 0 |
| net_context | 336 | 0 |
| news_article | 0 | 2,850 |
| official_notice | 0 | 2,606 |
| onboarding_doc | 0 | 1,078 |
| pem_long | 447 | 0 |
| pii_free | 2,157 | 0 |
| pii_free_business | 740 | 0 |
| place_verbs | 250 | 0 |
| police_report | 0 | 951 |
| postal | 661 | 0 |
| press_release | 0 | 2,915 |
| procurement_announcement | 0 | 2,802 |
| prose | 526 | 0 |
| punct | 375 | 0 |
| recall | 466 | 0 |
| receipt | 0 | 793 |
| rental_agreement | 0 | 994 |
| runbook | 0 | 951 |
| school_record | 0 | 968 |
| shipping_manifest | 0 | 870 |
| short_keys | 250 | 0 |
| slot_invalid | 1,110 | 0 |
| social_media | 0 | 1,003 |
| structured_caps_form | 225 | 0 |
| structured_config | 425 | 0 |
| structured_csv_header | 607 | 0 |
| structured_csv_noheader | 607 | 0 |
| structured_csv_snake | 607 | 0 |
| structured_dialogue | 607 | 0 |
| structured_json | 606 | 0 |
| structured_key_value | 728 | 0 |
| structured_log | 606 | 0 |
| structured_pipe_table | 606 | 0 |
| support_ticket | 0 | 904 |
| survey_response | 0 | 1,005 |
| technical_log | 0 | 954 |
| time_seconds | 660 | 0 |
| utility_bill | 0 | 863 |
| vehicle_record | 0 | 948 |
| village | 313 | 0 |
| voicemail_transcript | 0 | 1,006 |
| whatsapp_thread | 0 | 982 |

### Suffixed name/city/street mentions per case (targeted)

From `_suffixes`; LLM records carry no case tags, so they are left out.

| case | GIVENNAME (10,390 mentions) | SURNAME (8,346 mentions) | CITY (5,333 mentions) | STREET (2,641 mentions) |
|---|---|---|---|---|
| abl | 148 (1.4%) | 213 (2.6%) | 199 (3.7%) | 30 (1.1%) |
| acc | 156 (1.5%) | 157 (1.9%) | 197 (3.7%) | 80 (3.0%) |
| any case | 2,323 (22.4%) | 4,491 (53.8%) | 2,265 (42.5%) | 672 (25.4%) |
| cond | 41 (0.4%) | 38 (0.5%) | 0 (0.0%) | 0 (0.0%) |
| cop | 145 (1.4%) | 141 (1.7%) | 222 (4.2%) | 82 (3.1%) |
| dat | 430 (4.1%) | 68 (0.8%) | 110 (2.1%) | 31 (1.2%) |
| gen | 266 (2.6%) | 134 (1.6%) | 167 (3.1%) | 72 (2.7%) |
| gen_ki | 76 (0.7%) | 71 (0.9%) | 0 (0.0%) | 0 (0.0%) |
| gil | 71 (0.7%) | 47 (0.6%) | 0 (0.0%) | 0 (0.0%) |
| gil_abl | 30 (0.3%) | 29 (0.3%) | 0 (0.0%) | 0 (0.0%) |
| gil_dat | 43 (0.4%) | 36 (0.4%) | 0 (0.0%) | 0 (0.0%) |
| gil_gen | 33 (0.3%) | 26 (0.3%) | 0 (0.0%) | 0 (0.0%) |
| gil_loc | 35 (0.3%) | 44 (0.5%) | 0 (0.0%) | 0 (0.0%) |
| ins | 252 (2.4%) | 121 (1.4%) | 159 (3.0%) | 58 (2.2%) |
| loc | 163 (1.6%) | 173 (2.1%) | 217 (4.1%) | 86 (3.3%) |
| loc_cond | 0 (0.0%) | 0 (0.0%) | 79 (1.5%) | 0 (0.0%) |
| loc_cop | 0 (0.0%) | 0 (0.0%) | 110 (2.1%) | 67 (2.5%) |
| loc_past | 0 (0.0%) | 0 (0.0%) | 69 (1.3%) | 0 (0.0%) |
| loc_past1 | 0 (0.0%) | 0 (0.0%) | 59 (1.1%) | 0 (0.0%) |
| loc_pred1 | 0 (0.0%) | 0 (0.0%) | 64 (1.2%) | 34 (1.3%) |
| loc_pred1pl | 0 (0.0%) | 0 (0.0%) | 49 (0.9%) | 0 (0.0%) |
| loc_pred2 | 0 (0.0%) | 0 (0.0%) | 49 (0.9%) | 0 (0.0%) |
| loc_q | 0 (0.0%) | 0 (0.0%) | 69 (1.3%) | 39 (1.5%) |
| past | 31 (0.3%) | 38 (0.5%) | 0 (0.0%) | 0 (0.0%) |
| pl | 0 (0.0%) | 570 (6.8%) | 0 (0.0%) | 0 (0.0%) |
| pl_abl | 0 (0.0%) | 570 (6.8%) | 0 (0.0%) | 0 (0.0%) |
| pl_dat | 0 (0.0%) | 570 (6.8%) | 0 (0.0%) | 0 (0.0%) |
| pl_gen | 0 (0.0%) | 570 (6.8%) | 0 (0.0%) | 0 (0.0%) |
| pl_loc | 0 (0.0%) | 570 (6.8%) | 0 (0.0%) | 0 (0.0%) |
| poss1 | 98 (0.9%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| poss1pl | 0 (0.0%) | 0 (0.0%) | 98 (1.8%) | 0 (0.0%) |
| pred1 | 76 (0.7%) | 62 (0.7%) | 0 (0.0%) | 0 (0.0%) |
| pred_formal | 31 (0.3%) | 28 (0.3%) | 0 (0.0%) | 0 (0.0%) |
| q | 28 (0.3%) | 35 (0.4%) | 25 (0.5%) | 0 (0.0%) |
| rel | 170 (1.6%) | 180 (2.2%) | 155 (2.9%) | 65 (2.5%) |
| term_can | 0 (0.0%) | 0 (0.0%) | 98 (1.8%) | 0 (0.0%) |
| term_dek | 0 (0.0%) | 0 (0.0%) | 70 (1.3%) | 28 (1.1%) |

## Checks

- PASS: all 27 labels in train
- PASS: decoys in ≥ 25% of new documents: 44.4%
- PASS: PII-free ≈ 10% of new documents: 8.2%
