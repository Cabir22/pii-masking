# Formats benchmark on v4.2: results

Model `your-hf-org/masking-az-runb-v4.2-seed42@223e54e8799dc60f6f6b19362191cf7c10c774c7`, decoder `validity-2`, max_length 512, stride 256, no truncation (overlapping windows, merged). **M** = product decoding (decides, D-64a); **R** = raw model.

## Overall

| | M (product) | R (raw) |
|---|---|---|
| Exact span+label precision | 90.4% (274/303) | 89.3% (274/307) |
| Exact span+label recall | 87.0% (274/315) | 87.0% (274/315) |
| Exact F1 | 88.7 | 88.1 |
| **Fully masked (any label)** | 90.2% (284/315) | 90.2% (284/315) |
| Missed | 24 | 21 |
| Partly masked (fragment visible) | 7 | 10 |
| Wrong type (masked) | 4 | 4 |
| Boundary only (masked, right label) | 6 | 6 |
| False alarms | 5 | 6 |

Negative-only cases: 8; with a false alarm on M: 2 (2 false alarms).
Cases passing strictly (all exact, no false alarm) on M: 156/200; safely (every value fully masked, no false alarm): 166/200.

## By group (M)

| Group | Values | Fully masked | Missed | Partly | Wrong type | False alarms | Exact F1 |
|---|---|---|---|---|---|---|---|
| G1 structured | 35 | 100% | 0 | 0 | 0 | 0 | 100 |
| G2 logs | 26 | 100% | 0 | 0 | 0 | 1 | 98 |
| G3 spacing | 25 | 100% | 0 | 0 | 0 | 1 | 98 |
| G4 hidden_chars | 30 | 97% | 0 | 1 | 0 | 1 | 76 |
| G5 disguised | 24 | 38% | 11 | 4 | 0 | 0 | 44 |
| G6 long_mixed | 89 | 97% | 3 | 0 | 0 | 0 | 98 |
| G7 documents | 59 | 98% | 1 | 0 | 0 | 0 | 97 |
| G8 encodings | 27 | 59% | 9 | 2 | 4 | 2 | 51 |

## By label (M)

| Label | Values | Correct | Boundary | Wrong type | Partly | Missed |
|---|---|---|---|---|---|---|
| EMAIL | 63 | 42 | 5 | 3 | 4 | 9 |
| TELEPHONENUM | 62 | 54 | 0 | 1 | 2 | 5 |
| GIVENNAME | 49 | 46 | 0 | 0 | 0 | 3 |
| SURNAME | 43 | 42 | 0 | 0 | 0 | 1 |
| AZ_FIN | 36 | 30 | 0 | 0 | 1 | 5 |
| IBAN | 17 | 16 | 1 | 0 | 0 | 0 |
| AZ_PASSPORT_NUMBER | 10 | 10 | 0 | 0 | 0 | 0 |
| AZ_VOEN | 9 | 8 | 0 | 0 | 0 | 1 |
| PAYMENT_CARD_NUMBER | 8 | 8 | 0 | 0 | 0 | 0 |
| AZ_ID_CARD_NUMBER | 6 | 6 | 0 | 0 | 0 | 0 |
| IPV4_ADDRESS | 5 | 5 | 0 | 0 | 0 | 0 |
| IPV6_ADDRESS | 3 | 3 | 0 | 0 | 0 | 0 |
| MAC_ADDRESS | 2 | 2 | 0 | 0 | 0 | 0 |
| CITY | 1 | 1 | 0 | 0 | 0 | 0 |
| URL | 1 | 1 | 0 | 0 | 0 | 0 |

Label confusions (expected → predicted): EMAIL → URL ×3; TELEPHONENUM → URL ×1

## Reference vs transformation (M, safe pass)

| Family | Reference | Transformations failing while the reference passes | Both fail | Reference fails, transformation passes |
|---|---|---|---|---|
| F01 json_field_count | F-001 pass | – | – | – |
| F02 json_nesting_layout | F-006 pass | – | – | – |
| F03 csv_tsv | F-011 pass | – | – | – |
| F04 config_formats | F-016 pass, F-019 pass | – | – | – |
| F05 html_md_sql | F-021 pass | – | – | – |
| F06 web_server_log | F-026 pass, F-030 pass | F-029 | – | – |
| F07 app_json_log | F-031 pass | – | – | – |
| F08 syslog_audit | F-036 pass | – | – | – |
| F09 stack_trace | F-041 pass | – | – | – |
| F10 ipv6_mac | F-046 pass, F-049 pass | – | – | – |
| F11 digit_grouping | F-051 pass | – | – | – |
| F12 line_breaks | F-056 pass | – | – | – |
| F13 whitespace_types | F-061 pass, F-065 FAIL | – | – | – |
| F14 attached_labels | F-066 pass | – | – | – |
| F15 punct_adjacency | F-071 pass | – | – | – |
| F16 zero_width | F-076 pass, F-078 pass, F-079 pass, F-080 pass | – | – | – |
| F17 format_controls | F-081 pass | – | – | – |
| F18 lookalike_letters | F-086 pass, F-089 pass, F-090 pass | – | – | – |
| F19 digit_scripts | F-091 pass, F-095 FAIL | – | – | – |
| F20 combining_marks | F-096 pass, F-098 pass, F-099 pass, F-100 FAIL | – | – | – |
| F21 email_at_disguise | F-101 pass | F-102, F-103, F-104, F-105 | – | – |
| F22 email_dot_disguise | F-106 pass, F-110 pass | F-107, F-108, F-109 | – | – |
| F23 spoken_digits | F-111 pass | F-112, F-113, F-114 | – | – |
| F24 char_by_char_id | F-116 pass | F-117, F-118, F-119 | – | – |
| F25 mixed_obfuscation | F-121 pass, F-124 FAIL, F-125 FAIL | – | – | – |
| F26 long_position | F-126 pass | – | – | – |
| F27 chunk_boundary | F-131 pass | – | – | – |
| F28 dense_table | F-136 pass, F-139 pass | F-138, F-140 | – | – |
| F29 repeated_formats | F-141 pass, F-143 pass, F-144 pass, F-145 pass | – | – | – |
| F30 mixed_language | F-146 pass | – | – | – |
| F31 letters_signatures | F-151 pass | – | – | – |
| F32 forms | F-156 pass, F-158 pass, F-160 pass | – | – | – |
| F33 invoices_receipts | F-161 pass, F-163 pass, F-164 pass, F-165 pass | – | – | – |
| F34 chat_export | F-166 pass | – | – | – |
| F35 email_headers_urls | F-171 pass, F-174 pass, F-175 pass | F-173 | – | – |
| F36 url_encoding | F-176 FAIL, F-180 pass | – | – | F-177, F-178, F-179 |
| F37 html_entities | F-181 pass | F-182, F-183, F-184, F-185 | – | – |
| F38 json_escapes | F-186 pass, F-188 FAIL, F-189 FAIL, F-190 pass | F-187 | – | – |
| F39 base64_distractors | F-191 pass, F-194 pass | – | – | – |
| F40 representation_layers | F-196 pass | F-197, F-198, F-199, F-200 | – | – |

## Every failing case (M)

**F-029** `F06 web_server_log` — IP with port
- input: `2026-10-23 12:05:11 WARN conn client=185.47.112.36:51432 closed`
- false_alarm: `:` as IPV6_ADDRESS
- masked (M): `2026-10-23 12:05:11 WARN conn client=[IPV4_ADDRESS][IPV6_ADDRESS]51432 closed`

**F-065** `F13 whitespace_types` — negative spaced code
- input: `Sifariş kodu: SIF 2026 0048 1752 3301 7720 (IBAN deyil)`
- false_alarm: `2026 0048 1752 3301 7720` as IBAN
- masked (M): `Sifariş kodu: SIF [IBAN] (IBAN deyil)`

**F-079** `F16 zero_width` — ZWSP in e-mail (regression)
- input: `E-poçt: rauf​.aliyev@kamranservis.az`
- boundary: `rauf​.aliyev@kamranservis.az` (EMAIL) → predicted EMAIL/EMAIL; split
- masked (M): `E-poçt: [EMAIL]​[EMAIL]`

**F-080** `F16 zero_width` — word joiner before IBAN
- input: `IBAN: ⁠AZ29JHZF31948757491186252760`
- boundary: `⁠AZ29JHZF31948757491186252760` (IBAN) → predicted IBAN
- masked (M): `IBAN: ⁠[IBAN]`

**F-083** `F17 format_controls` — LRM U+200E around the e-mail
- input: `E-poçt ünvanı: ‎s.qasimova@inbox.az‎`
- boundary: `‎s.qasimova@inbox.az‎` (EMAIL) → predicted EMAIL
- masked (M): `E-poçt ünvanı: ‎[EMAIL]‎`

**F-084** `F17 format_controls` — RLM U+200F before @
- input: `E-poçt ünvanı: s.qasimova‏@inbox.az`
- boundary: `s.qasimova‏@inbox.az` (EMAIL) → predicted EMAIL/EMAIL; split
- masked (M): `E-poçt ünvanı: [EMAIL]‏[EMAIL]`

**F-085** `F17 format_controls` — BOM U+FEFF before the e-mail
- input: `E-poçt ünvanı: ﻿s.qasimova@inbox.az`
- boundary: `﻿s.qasimova@inbox.az` (EMAIL) → predicted EMAIL
- masked (M): `E-poçt ünvanı: ﻿[EMAIL]`

**F-095** `F19 digit_scripts` — negative full-width order
- input: `Sifariş № ４８２９１７３６５１ qəbul olundu.`
- false_alarm: `４８２９１７３６５１` as AZ_VOEN
- masked (M): `Sifariş № [AZ_VOEN] qəbul olundu.`

**F-100** `F20 combining_marks` — mark after FIN
- input: `FİN kodu: 7KD3M2X́ qeydə alınıb.`
- partly_masked: `7KD3M2X́` (AZ_FIN) → predicted AZ_FIN; visible: `́`
- masked (M): `FİN kodu: [AZ_FIN]́ qeydə alınıb.`

**F-102** `F21 email_at_disguise` — [at]
- input: `Mənə leyla.rzayeva[at]poct.az ünvanına yazın.`
- partly_masked: `leyla.rzayeva[at]poct.az` (EMAIL) → predicted EMAIL/EMAIL; visible: `[at]`; split
- masked (M): `Mənə [EMAIL][at][EMAIL] ünvanına yazın.`

**F-103** `F21 email_at_disguise` — (at)
- input: `Mənə leyla.rzayeva(at)poct.az ünvanına yazın.`
- partly_masked: `leyla.rzayeva(at)poct.az` (EMAIL) → predicted EMAIL/EMAIL; visible: `.rzayeva(at)poct`; split
- masked (M): `Mənə [EMAIL].rzayeva(at)poct[EMAIL] ünvanına yazın.`

**F-104** `F21 email_at_disguise` — spaced at
- input: `Mənə leyla.rzayeva at poct.az ünvanına yazın.`
- missed: `leyla.rzayeva at poct.az` (EMAIL); visible: `leyla.rzayevaatpoct.az`
- masked (M): `Mənə leyla.rzayeva at poct.az ünvanına yazın.`

**F-105** `F21 email_at_disguise` — spaced [at] and [dot]
- input: `Mənə leyla.rzayeva [at] poct [dot] az ünvanına yazın.`
- missed: `leyla.rzayeva [at] poct [dot] az` (EMAIL); visible: `leyla.rzayeva[at]poct[dot]az`
- masked (M): `Mənə leyla.rzayeva [at] poct [dot] az ünvanına yazın.`

**F-107** `F22 email_dot_disguise` — [dot]
- input: `Ünvan: rauf[dot]aliyev@kamranservis[dot]az`
- missed: `rauf[dot]aliyev@kamranservis[dot]az` (EMAIL); visible: `rauf[dot]aliyev@kamranservis[dot]az`
- masked (M): `Ünvan: rauf[dot]aliyev@kamranservis[dot]az`

**F-108** `F22 email_dot_disguise` — (dot)
- input: `Ünvan: rauf(dot)aliyev@kamranservis(dot)az`
- partly_masked: `rauf(dot)aliyev@kamranservis(dot)az` (EMAIL) → predicted EMAIL/EMAIL/EMAIL; visible: `(dot)(dot)`; split
- masked (M): `Ünvan: [EMAIL](dot)[EMAIL](dot)[EMAIL]`

**F-109** `F22 email_dot_disguise` — spaced dot
- input: `Ünvan: rauf dot aliyev@kamranservis dot az`
- missed: `rauf dot aliyev@kamranservis dot az` (EMAIL); visible: `raufdotaliyev@kamranservisdotaz`
- masked (M): `Ünvan: rauf dot aliyev@kamranservis dot az`

**F-112** `F23 spoken_digits` — words
- input: `Nömrəm: üstəgəl doqquz yüz doxsan dörd əlli yeddi yüz otuz doqquz iyirmi bir altmış dörd`
- missed: `üstəgəl doqquz yüz doxsan dörd əlli yeddi yüz otuz doqquz iyirmi bir altmış dörd` (TELEPHONENUM); visible: `üstəgəldoqquzyüzdoxsandördəlliyeddiyüzotuzdoqquziyirmibiraltmışdörd`
- masked (M): `Nömrəm: üstəgəl doqquz yüz doxsan dörd əlli yeddi yüz otuz doqquz iyirmi bir altmış dörd`

**F-113** `F23 spoken_digits` — words + commas
- input: `Nömrəm: üstəgəl doqquz yüz doxsan dörd, əlli, yeddi yüz otuz doqquz, iyirmi bir, altmış dörd`
- missed: `üstəgəl doqquz yüz doxsan dörd, əlli, yeddi yüz otuz doqquz, iyirmi bir, altmış dörd` (TELEPHONENUM); visible: `üstəgəldoqquzyüzdoxsandörd,əlli,yeddiyüzotuzdoqquz,iyirmibir,altmışdörd`
- masked (M): `Nömrəm: üstəgəl doqquz yüz doxsan dörd, əlli, yeddi yüz otuz doqquz, iyirmi bir, altmış dörd`

**F-114** `F23 spoken_digits` — words, multiline
- input: `Nömrəm:\nüstəgəl doqquz yüz doxsan dörd\nəlli\nyeddi yüz otuz doqquz\niyirmi bir altmış dörd`
- missed: `üstəgəl doqquz yüz doxsan dörd\nəlli\nyeddi yüz otuz doqquz\niyirmi bir altmış dörd` (TELEPHONENUM); visible: `üstəgəldoqquzyüzdoxsandördəlliyeddiyüzotuzdoqquziyirmibiraltmışdörd`
- masked (M): `Nömrəm:\nüstəgəl doqquz yüz doxsan dörd\nəlli\nyeddi yüz otuz doqquz\niyirmi bir altmış dörd`

**F-117** `F24 char_by_char_id` — spaces between characters
- input: `FİN: 5 R T 8 V Q 2`
- missed: `5 R T 8 V Q 2` (AZ_FIN); visible: `5RT8VQ2`
- masked (M): `FİN: 5 R T 8 V Q 2`

**F-118** `F24 char_by_char_id` — hyphens
- input: `FİN: 5-R-T-8-V-Q-2`
- missed: `5-R-T-8-V-Q-2` (AZ_FIN); visible: `5-R-T-8-V-Q-2`
- masked (M): `FİN: 5-R-T-8-V-Q-2`

**F-119** `F24 char_by_char_id` — dots
- input: `FİN: 5.R.T.8.V.Q.2`
- missed: `5.R.T.8.V.Q.2` (AZ_FIN); visible: `5.R.T.8.V.Q.2`
- masked (M): `FİN: 5.R.T.8.V.Q.2`

**F-124** `F25 mixed_obfuscation` — ZWSP + [at]
- input: `E-poçt: leyla​.rzayeva[at]poct.az`
- partly_masked: `leyla​.rzayeva[at]poct.az` (EMAIL) → predicted EMAIL; visible: `leyla`
- masked (M): `E-poçt: leyla​[EMAIL]`

**F-125** `F25 mixed_obfuscation` — spaces + Cyrillic
- input: `FİN: 5 R Т 8 V Q 2`
- missed: `5 R Т 8 V Q 2` (AZ_FIN); visible: `5RТ8VQ2`
- masked (M): `FİN: 5 R Т 8 V Q 2`

**F-138** `F28 dense_table` — 8 rows
- input: `Ad | Soyad | FİN | Telefon\nRauf | Əliyev | 7KD3M2X | +994553186420\nSəbinə | Qasımova | 5RT8VQ2 | +994553186427\nOrxan | Mustafayev | 2HN6WK9 | +994553186434\nLeyla | Rzayeva | 9PL4ZT3 | +994553186441\nKamran | Həsənov | 4XC7RB8 | +994553186448\nGünel | Abbasova | 6MV2QJ5 | +994553186455\nElnur | Quliyev | 3WZ9KD4 | +994553186462\nAytən | Məmmədova | 8TB5NH7 | +994553186469`
- missed: `Leyla` (GIVENNAME); visible: `Leyla`
- masked (M): `Ad | Soyad | FİN | Telefon\n[GIVENNAME] | [SURNAME] | [AZ_FIN] | [TELEPHONENUM]\n[GIVENNAME] | [SURNAME] | [AZ_FIN] | [TELEPHONENUM]\n[GIVENNAME] | [SURNAME] | [AZ_FIN] | [TELEPHONENUM]\nLeyla | [SURNAME] | [AZ_FIN] | [TELEPHONENUM]\n[GIVENNAME] | [SURNAME] | [AZ_FIN] | [TELEPHONENUM]\n[GIVENNAME] | [SURNAME] | [AZ_FIN] | [TELEPHONENUM]\n[GIVENNAME] | [SURNAME] | [AZ_FIN] | [TELEPHONENUM]\n[GIVENNAME] | [SURNAME] | [AZ_FIN] | [TELEPHONENUM]`

**F-140** `F28 dense_table` — glued values
- input: `Rauf Əliyev+994553186427 7KD3M2X1702938461`
- missed: `7KD3M2X` (AZ_FIN); visible: `7KD3M2X`
- missed: `1702938461` (AZ_VOEN); visible: `1702938461`
- masked (M): `[GIVENNAME] [SURNAME][TELEPHONENUM] 7KD3M2X1702938461`

**F-173** `F35 email_headers_urls` — quoted display name
- input: `From: \"Əliyev, Rauf\" <rauf.aliyev@kamranservis.az>`
- missed: `Rauf` (GIVENNAME); visible: `Rauf`
- masked (M): `From: \"[SURNAME], Rauf\" <[EMAIL]>`

**F-174** `F35 email_headers_urls` — query e-mail
- input: `Keçid: https://portal.kamran-servis.az/qeydiyyat?ref=mail&email=rauf.aliyev@kamranservis.az`
- boundary: `rauf.aliyev@kamranservis.az` (EMAIL) → predicted URL/EMAIL; overreach, split
- masked (M): `Keçid: [URL][EMAIL]`

**F-176** `F36 url_encoding` — literal
- input: `Keçid: https://portal.kamran-servis.az/profil?email=rauf.aliyev@kamranservis.az&lang=az`
- false_alarm: `https://portal.kamran-servis.az/profil?email=` as URL
- false_alarm: `&lang=az` as URL
- masked (M): `Keçid: [URL][EMAIL][URL]`

**F-177** `F36 url_encoding` — @ as %40
- input: `Keçid: https://portal.kamran-servis.az/profil?email=rauf.aliyev%40kamranservis.az&lang=az`
- wrong_type: `rauf.aliyev%40kamranservis.az` (EMAIL) → predicted URL; overreach
- masked (M): `Keçid: [URL]`

**F-178** `F36 url_encoding` — @ and the TLD dot encoded
- input: `Keçid: https://portal.kamran-servis.az/profil?email=rauf.aliyev%40kamranservis%2Eaz&lang=az`
- wrong_type: `rauf.aliyev%40kamranservis%2Eaz` (EMAIL) → predicted URL; overreach
- masked (M): `Keçid: [URL]`

**F-179** `F36 url_encoding` — every delimiter encoded
- input: `Keçid: https://portal.kamran-servis.az/profil?email=rauf%2Ealiyev%40kamranservis%2Eaz&lang=az`
- wrong_type: `rauf%2Ealiyev%40kamranservis%2Eaz` (EMAIL) → predicted URL; overreach
- masked (M): `Keçid: [URL]`

**F-180** `F36 url_encoding` — phone %2B
- input: `Keçid: https://portal.kamran-servis.az/zeng?tel=%2B994553186427&lang=az`
- wrong_type: `%2B994553186427` (TELEPHONENUM) → predicted URL; overreach
- masked (M): `Keçid: [URL]`

**F-182** `F37 html_entities` — decimal &#64;
- input: `<p>E-poçt: s.qasimova&#64;inbox.az</p>`
- missed: `s.qasimova&#64;inbox.az` (EMAIL); visible: `s.qasimova&#64;inbox.az`
- masked (M): `<p>E-poçt: s.qasimova&#64;inbox.az</p>`

**F-183** `F37 html_entities` — hex &#x40;
- input: `<p>E-poçt: s.qasimova&#x40;inbox.az</p>`
- missed: `s.qasimova&#x40;inbox.az` (EMAIL); visible: `s.qasimova&#x40;inbox.az`
- masked (M): `<p>E-poçt: s.qasimova&#x40;inbox.az</p>`

**F-184** `F37 html_entities` — named &commat;
- input: `<p>E-poçt: s.qasimova&commat;inbox.az</p>`
- missed: `s.qasimova&commat;inbox.az` (EMAIL); visible: `s.qasimova&commat;inbox.az`
- masked (M): `<p>E-poçt: s.qasimova&commat;inbox.az</p>`

**F-185** `F37 html_entities` — mixed literal/entity
- input: `<p>E-poçt: &#115;.qasimova&#64;inbox.az</p>`
- missed: `&#115;.qasimova&#64;inbox.az` (EMAIL); visible: `&#115;.qasimova&#64;inbox.az`
- masked (M): `<p>E-poçt: &#115;.qasimova&#64;inbox.az</p>`

**F-187** `F38 json_escapes` — \u escape in name
- input: `{\"ad\":\"Rauf\",\"soyad\":\"\\u018fliyev\"}`
- missed: `\\u018fliyev` (SURNAME); visible: `\\u018fliyev`
- masked (M): `{\"ad\":\"[GIVENNAME]\",\"soyad\":\"\\u018fliyev\"}`

**F-188** `F38 json_escapes` — \u0040
- input: `{\"email\":\"rauf.aliyev\\u0040kamranservis.az\"}`
- missed: `rauf.aliyev\\u0040kamranservis.az` (EMAIL); visible: `rauf.aliyev\\u0040kamranservis.az`
- masked (M): `{\"email\":\"rauf.aliyev\\u0040kamranservis.az\"}`

**F-189** `F38 json_escapes` — JSON in string
- input: `{\"msg\":\"{\\\"email\\\":\\\"rauf.aliyev@kamranservis.az\\\",\\\"ad\\\":\\\"Rauf\\\"}\"}`
- missed: `Rauf` (GIVENNAME); visible: `Rauf`
- masked (M): `{\"msg\":\"{\\\"email\\\":\\\"[EMAIL]\\\",\\\"ad\\\":\\\"Rauf\\\"}\"}`

**F-197** `F40 representation_layers` — literal \u002B for +
- input: `Telefon: \\u002B994 55 318 64 27`
- partly_masked: `\\u002B994 55 318 64 27` (TELEPHONENUM) → predicted TELEPHONENUM; visible: `\\u002B994`
- masked (M): `Telefon: \\u002B994 [TELEPHONENUM]`

**F-198** `F40 representation_layers` — URL-encoded
- input: `Telefon: %2B994%2055%20318%2064%2027`
- missed: `%2B994%2055%20318%2064%2027` (TELEPHONENUM); visible: `%2B994%2055%20318%2064%2027`
- masked (M): `Telefon: %2B994%2055%20318%2064%2027`

**F-199** `F40 representation_layers` — double URL-encoded
- input: `Telefon: %252B994%252055%2520318%252064%252027`
- missed: `%252B994%252055%2520318%252064%252027` (TELEPHONENUM); visible: `%252B994%252055%2520318%252064%252027`
- masked (M): `Telefon: %252B994%252055%2520318%252064%252027`

**F-200** `F40 representation_layers` — HTML entity for +
- input: `Telefon: &#43;994 55 318 64 27`
- partly_masked: `&#43;994 55 318 64 27` (TELEPHONENUM) → predicted TELEPHONENUM; visible: `&#43;`
- masked (M): `Telefon: &#43;[TELEPHONENUM]`

