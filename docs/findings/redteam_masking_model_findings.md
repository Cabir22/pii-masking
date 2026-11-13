# Adversarial red-team findings -- `your-hf-org/masking-multilingual`

Model: `your-hf-org/masking-multilingual` (revision `3a0a6e5df228bdc89dd01312a728e10a78b3e3fb`). Generated from `scripts/redteam/findings.jsonl` and `scripts/redteam/run_ledger.jsonl` by `scripts/redteam/masking_model_probe.py --report` -- do not hand-edit.

**Scope note:** this document lists FAILURES in detail, and totals computed from `run_ledger.jsonl` (every case run, pass or fail). Every number below is derived directly from those two files, not asserted in prose.

## Overall results

- **Cases in harness:** 209
- **Cases run:** 209
- **Passed:** 171
- **Failed:** 38

## Per-label snapshot (primary-label cases only)

| Label | Risk | Cases (primary) | Expected entities | Failure rows |
|---|---|---|---|---|
| ACCESS_TOKEN | high | 4 | 4 | 0 |
| AGE | low | 16 | 12 | 6 |
| API_KEY | high | 5 | 6 | 0 |
| AZ_DRIVER_LICENSE_NUMBER | high | 4 | 4 | 2 |
| AZ_FIN | high | 7 | 7 | 1 |
| AZ_ID_CARD_NUMBER | high | 4 | 4 | 1 |
| AZ_PASSPORT_NUMBER | high | 5 | 5 | 2 |
| AZ_VOEN | high | 5 | 5 | 0 |
| BUILDINGNUM | low | 13 | 11 | 4 |
| CARD_SECURITY_CODE | high | 10 | 7 | 4 |
| CITY | low | 5 | 5 | 0 |
| DATE | low | 16 | 16 | 5 |
| EMAIL | medium | 8 | 8 | 0 |
| GIVENNAME | medium | 10 | 13 | 3 |
| IBAN | high | 7 | 7 | 1 |
| ICCID | medium | 4 | 4 | 1 |
| IPV4_ADDRESS | medium | 5 | 5 | 0 |
| IPV6_ADDRESS | medium | 5 | 5 | 1 |
| MAC_ADDRESS | medium | 5 | 5 | 0 |
| PAYMENT_CARD_NUMBER | high | 8 | 10 | 0 |
| PRIVATE_KEY | high | 4 | 4 | 0 |
| STREET | low | 4 | 4 | 0 |
| SURNAME | medium | 7 | 7 | 0 |
| TELEPHONENUM | medium | 8 | 9 | 3 |
| TIME | low | 12 | 12 | 2 |
| URL | low | 5 | 5 | 2 |
| ZIPCODE | low | 7 | 7 | 2 |

## Dominant cross-cutting root cause: trailing-character over-capture

**24 of 29 `partial_span` failure rows** (across 24 cases, 13 distinct labels) share one exact pattern: the predicted span is the correct span plus exactly one trailing character -- the sentence-final punctuation immediately after the value. This is the single largest failure cluster in this run, larger than any per-category grouping below, and it hits every risk tier (AZ_DRIVER_LICENSE_NUMBER, AZ_ID_CARD_NUMBER, AZ_PASSPORT_NUMBER, IBAN, CARD_SECURITY_CODE, ICCID -- all `high` risk -- alongside AGE/BUILDINGNUM).

- **Labels affected:** AGE, AZ_DRIVER_LICENSE_NUMBER, AZ_ID_CARD_NUMBER, AZ_PASSPORT_NUMBER, BUILDINGNUM, CARD_SECURITY_CODE, DATE, IBAN, ICCID, IPV6_ADDRESS, TELEPHONENUM, URL, ZIPCODE
- **Example case IDs:** `anchordist_age_az_boundary_in`, `anchordist_date_en_beyond`, `anchordist_date_en_boundary_in`, `anchordist_date_en_near`, `collision_passport_real_az`, `core_age_en`, `core_age_ru`, `core_az_driver_license_number_ru`

## Systemic failure clusters (root-cause grouped, by category)

| Category | Dominant failure type | # cases | Example case IDs |
|---|---|---|---|
| core | partial_span | 16 | `core_age_en`, `core_age_ru`, `core_az_driver_license_number_tr` |
| anchor_distance | partial_span | 7 | `anchordist_age_az_boundary_in`, `anchordist_buildingnum_az_near`, `anchordist_card_security_code_az_near` |
| anchor_distance | false_positive | 3 | `anchordist_age_az_near`, `anchordist_card_security_code_az_boundary_in`, `anchordist_time_az_near` |
| anchor_distance | missed | 3 | `anchordist_buildingnum_en_boundary_in`, `anchordist_buildingnum_en_beyond`, `anchordist_card_security_code_en_boundary_in` |
| doc_length | partial_span | 2 | `doclen_age_en_short`, `doclen_age_en_long` |
| collisions | partial_span | 1 | `collision_passport_real_az` |
| collisions | false_positive | 1 | `collision_fin_order_hardneg_az` |
| multilingual_names | missed | 1 | `mlname_givenname_ru` |
| formatting | partial_span | 1 | `formatting_zipcode_az` |
| informal | partial_span | 1 | `informal_time_en` |
| embedded | missed | 1 | `embedded_hr_az` |
| embedded | partial_span | 1 | `embedded_adjacent_phones_ru` |

## Top findings (risk-ranked: government-ID / financial / credential labels first)

### `core_az_driver_license_number_tr`  (AZ_DRIVER_LICENSE_NUMBER, risk=high, lang=tr, category=core)

- Notes: Baseline single-entity AZ_DRIVER_LICENSE_NUMBER probe in tr.
- PARTIAL_SPAN expected AZ_DRIVER_LICENSE_NUMBER 25:33 'DZ002242', got AZ_DRIVER_LICENSE_NUMBER 25:34 'DZ002242.'

### `core_az_driver_license_number_ru`  (AZ_DRIVER_LICENSE_NUMBER, risk=high, lang=ru, category=core)

- Notes: Baseline single-entity AZ_DRIVER_LICENSE_NUMBER probe in ru.
- PARTIAL_SPAN expected AZ_DRIVER_LICENSE_NUMBER 28:36 'GI004908', got AZ_DRIVER_LICENSE_NUMBER 28:37 'GI004908.'

### `core_az_id_card_number_tr`  (AZ_ID_CARD_NUMBER, risk=high, lang=tr, category=core)

- Notes: Baseline single-entity AZ_ID_CARD_NUMBER probe in tr.
- PARTIAL_SPAN expected AZ_ID_CARD_NUMBER 23:33 'MYI8912307', got AZ_ID_CARD_NUMBER 23:34 'MYI8912307.'

### `core_az_passport_number_ru`  (AZ_PASSPORT_NUMBER, risk=high, lang=ru, category=core)

- Notes: Baseline single-entity AZ_PASSPORT_NUMBER probe in ru.
- PARTIAL_SPAN expected AZ_PASSPORT_NUMBER 22:31 'Z58484752', got AZ_PASSPORT_NUMBER 22:32 'Z58484752.'

### `core_card_security_code_tr`  (CARD_SECURITY_CODE, risk=high, lang=tr, category=core)

- Notes: Baseline single-entity CARD_SECURITY_CODE probe in tr.
- PARTIAL_SPAN expected CARD_SECURITY_CODE 17:20 '482', got CARD_SECURITY_CODE 17:21 '482.'

### `core_iban_tr`  (IBAN, risk=high, lang=tr, category=core)

- Notes: Baseline single-entity IBAN probe in tr.
- PARTIAL_SPAN expected IBAN 21:43 'GE17IK5011206985617002', got IBAN 21:44 'GE17IK5011206985617002.'

### `anchordist_card_security_code_az_near`  (CARD_SECURITY_CODE, risk=high, lang=az, category=anchor_distance)

- Notes: CARD_SECURITY_CODE value placed ~5 chars after its anchor word ('Kartın CVV kodu') -- distance=near, DEFAULT_WINDOW=80. This was the prior campaign's #1 systemic failure mode.
- PARTIAL_SPAN expected CARD_SECURITY_CODE 40:43 '071', got CARD_SECURITY_CODE 36:43 'Sist071'

### `anchordist_card_security_code_az_boundary_in`  (CARD_SECURITY_CODE, risk=high, lang=az, category=anchor_distance)

- Notes: CARD_SECURITY_CODE value placed ~75 chars after its anchor word ('Kartın CVV kodu') -- distance=boundary_in, DEFAULT_WINDOW=80. This was the prior campaign's #1 systemic failure mode.
- FALSE POSITIVE CARD_SECURITY_CODE 110:113 '987' (score=0.554)

### `anchordist_card_security_code_en_boundary_in`  (CARD_SECURITY_CODE, risk=high, lang=en, category=anchor_distance)

- Notes: CARD_SECURITY_CODE value placed ~75 chars after its anchor word ('Card CVV') -- distance=boundary_in, DEFAULT_WINDOW=80. This was the prior campaign's #1 systemic failure mode.
- MISSED CARD_SECURITY_CODE 103:106 '717'

### `collision_passport_real_az`  (AZ_PASSPORT_NUMBER, risk=high, lang=az, category=collisions)

- Notes: Companion to collision_fin_real_az -- disjoint alphabet, same slot shape.
- PARTIAL_SPAN expected AZ_PASSPORT_NUMBER 27:36 'F93859209', got AZ_PASSPORT_NUMBER 27:37 'F93859209.'

### `collision_fin_order_hardneg_az`  (AZ_FIN, risk=high, lang=az, category=collisions)

- Notes: data/schema.md: 'a 7-character uppercase alphanumeric string from the same alphabet as AZ_FIN is a deliberate hard-negative target (order IDs, Git short SHAs)'. This is an order-confirmation code, not a FIN -- expected is empty on purpose.
- FALSE POSITIVE AZ_FIN 21:28 'UMSSZ1C' (score=1.000)

### `embedded_hr_az`  (GIVENNAME, risk=medium, lang=az, category=embedded)

- Notes: 4 entities (GIVENNAME, SURNAME, EMAIL, TELEPHONENUM) packed into one comma-dense sentence.
- MISSED GIVENNAME 8:18 'Zillixanım'
- MISSED SURNAME 19:30 'Mirsahibova'

### `embedded_adjacent_phones_ru`  (TELEPHONENUM, risk=medium, lang=ru, category=embedded)

- Notes: Two different TELEPHONENUM values separated by only a comma, zero whitespace -- probes whether adjacent same-type entities merge into one span (the concrete risk plain BIO tagging carries).
- PARTIAL_SPAN expected TELEPHONENUM 9:26 '+994 18 297 77 40', got TELEPHONENUM 9:40 '+994 18 297 77 40,022 966 75 85'
- MISSED TELEPHONENUM 27:40 '022 966 75 85'

### `core_iccid_ru`  (ICCID, risk=medium, lang=ru, category=core)

- Notes: Baseline single-entity ICCID probe in ru.
- PARTIAL_SPAN expected ICCID 17:37 '89994946091218884124', got ICCID 17:38 '89994946091218884124.'

### `core_ipv6_address_az`  (IPV6_ADDRESS, risk=medium, lang=az, category=core)

- Notes: Baseline single-entity IPV6_ADDRESS probe in az.
- PARTIAL_SPAN expected IPV6_ADDRESS 13:52 'fd0c:8df7:a832:6457:7ac3:8cdb:d071:1ec2', got IPV6_ADDRESS 13:53 'fd0c:8df7:a832:6457:7ac3:8cdb:d071:1ec2.'

### `core_telephonenum_tr`  (TELEPHONENUM, risk=medium, lang=tr, category=core)

- Notes: Baseline single-entity TELEPHONENUM probe in tr.
- PARTIAL_SPAN expected TELEPHONENUM 18:35 '+994 10 605 54 16', got TELEPHONENUM 18:36 '+994 10 605 54 16.'

### `mlname_givenname_ru`  (GIVENNAME, risk=medium, lang=ru, category=multilingual_names)

- Notes: Azerbaijani-sourced GIVENNAME embedded mid-sentence in ru prose, no explicit label cue -- known training gap (model documented as trained on Azerbaijani names only).
- MISSED GIVENNAME 26:33 'Ciyadət'

### `core_age_en`  (AGE, risk=low, lang=en, category=core)

- Notes: Baseline single-entity AGE probe in en.
- PARTIAL_SPAN expected AGE 12:14 '29', got AGE 12:15 '29.'

### `core_age_ru`  (AGE, risk=low, lang=ru, category=core)

- Notes: Baseline single-entity AGE probe in ru.
- PARTIAL_SPAN expected AGE 12:14 '16', got AGE 12:15 '16.'

### `core_buildingnum_az`  (BUILDINGNUM, risk=low, lang=az, category=core)

- Notes: Baseline single-entity BUILDINGNUM probe in az.
- PARTIAL_SPAN expected BUILDINGNUM 13:15 '22', got BUILDINGNUM 13:16 '22.'

*18 additional failing case(s) not shown above -- see `findings.jsonl` for the complete set.*

## Known harness limitations

- Per-label recall above is computed only from each case's *primary* label attribution; multi-entity cases (the `embedded` category) test several labels per case but are only tallied under one. Exact per-entity outcomes for every label in every case are in `findings.jsonl`'s `failure_rows`, not summarized here.
- `translate.lang.ANCHORS["en"]` (and tr/ru) has no structural-position guard equivalent to `piigen.anchors.az.is_structural_position` -- confirmed during harness construction, not from a probe result. The `suppression` category is therefore AZ-only in this harness.
