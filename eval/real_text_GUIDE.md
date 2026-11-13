# Real-text labelling guide (P3-7)

This guide covers labelling real, public documents (news, official notices, procurement notices, decrees, press releases) so that every labeller marks the same things: Azerbaijani first, and the independent English, Turkish and Russian sets of D-46b with the [language notes](#language-notes-english-turkish-russian) at the end. It follows `data/schema.md` and decisions D-2, D-9, D-10 and D-17. The documents themselves stay outside git, in `~/pii-eval-private/real_text/` and `real_text_en/`, `real_text_tr/`, `real_text_ru/` (A2 rule 5), each with a private manifest of URLs and dates.

## What to label: the 27 labels

- **People:** `GIVENNAME`, `SURNAME`.
- **Places:** `CITY`, `STREET`, `BUILDINGNUM`, `ZIPCODE`.
- **Contact:** `TELEPHONENUM`, `EMAIL`, `URL`.
- **Time:** `DATE`, `TIME`, `AGE`.
- **Azerbaijani IDs:** `AZ_FIN`, `AZ_ID_CARD_NUMBER`, `AZ_PASSPORT_NUMBER`, `AZ_VOEN`, `AZ_DRIVER_LICENSE_NUMBER`.
- **Money and network:** `PAYMENT_CARD_NUMBER`, `IBAN`, `CARD_SECURITY_CODE`, `ICCID`, `IPV4_ADDRESS`, `IPV6_ADDRESS`, `MAC_ADDRESS`.
- **Secrets:** `API_KEY`, `ACCESS_TOKEN`, `PRIVATE_KEY`.

There is no label for organisations, countries, job titles or money amounts. Leave those unlabelled.

## Span rules

1. **The whole value, nothing around it.** No quotes, brackets, commas or full stops at the edges. A phone written with brackets inside it is labelled whole: `(012) 361-14-07`.
2. **A case suffix is inside the span (D-9):** `Bakıda`, `Adamyanla`, `Nəriman Nərimanov küçəsində`.
3. **Each name part is its own span.** `Kamran Əliyev` gives `Kamran` (GIVENNAME) and `Əliyev` (SURNAME), in either order.
4. **Spans never overlap.** When one thing sits inside another, label the bigger thing: a street named after a person is one STREET span.

## People

- **Label every person's name:** private people, officials, public figures, athletes and foreign names (`Qoki Tayimaya`).
- **Patronymic:** in `Hacıbaba Adil oğlu Babayev`, the father's name `Adil` is labelled GIVENNAME. `oğlu`/`qızı` stays outside.
- **Initials are not labelled; the surname next to them is.** In `Z.Kotsoyev`, only `Kotsoyev` is labelled.
- **A personal name used as the name of something else is not labelled (D-2).** That covers organisations, awards, events, metro stations and buildings, for example the station `Həzi Aslanov` or the award `“Şöhrət” ordeni`. The one exception is a street named after a person, which is a STREET.
- **A name that is also an ordinary word** is a name only when it refers to a person (D-10). A lone capitalised word counts as a name; a lone lowercase word does not.

## Places

- **CITY** covers cities, towns, villages and settlements (`Xaçmaz`, `Dağmaşanlı kəndi` → `Dağmaşanlı`, `Günəşli qəsəbəsi` → `Günəşli`). It also covers a district named after its town (`Cəbrayıl rayonu` → `Cəbrayıl`) and foreign cities.
- **A town's name inside an organisation's or an event's name is still CITY.** Examples: `Füzuli` in `Füzuli Rayon Mərkəzi Xəstəxanası`, `ŞƏKİ` in `ŞƏKİ REGİONAL TURİZM İDARƏSİ`.
- **Not CITY:**
  - Baku's districts, except names that are also settlements. Pure district names (`Səbail`, `Yasamal`, `Nəsimi`, `Nərimanov`, `Xətai`) are not CITY. Names that are also settlements (`Suraxanı`, `Balaxanı`, `Hövsan`, `Buzovna`, `Mərdəkan`) are CITY, as in the benchmark, even in `Suraxanı rayonu`;
  - countries (`Azərbaycan`, `Türkiyə`);
  - metro stations;
  - hills, rivers and other natural places.
- **STREET** is the street name with its word (`küçəsi`, `prospekti`), or without the word when an address leaves it out (`K.Kazimzadə 118` → STREET `K.Kazimzadə`, BUILDINGNUM `118`).
- **BUILDINGNUM** is a house or building number in an address. **ZIPCODE** is `AZ` + 4 digits.

## Time

- **DATE** is a full date with day, month and a 4-digit year (D-17), in any format. `28 sentyabr 2026-cı il` → `28 sentyabr 2026`: the `-cı il` stays outside.
- **Not DATE:**
  - a year alone (`1966-cı il təvəllüdlü`);
  - a day and month without a year (`oktyabrın 16-da`);
  - a month and year;
  - a **complete timestamp**: a full date (day, month and a 4-digit year) followed or preceded by a clock time. Neither part is labelled (`09.10.2026 14:00`, `Ekim 14, 2026 10:59`).
- **TIME** is a clock time on its own (`saat 10:00-da` → `10:00`), and also a clock time next to an **incomplete** date: with no year, the date is not DATE and the time is TIME (`25 Eylül’de saat 14.00` → `14.00`; the decision, 2026-10-14). **AGE** is an age number (`45 yaşında` → `45`).

## Contact, IDs and numbers

- **TELEPHONENUM** is any phone number of a person or an office. A short service number (`196 Əlaqə Mərkəzi`) is not labelled.
- **EMAIL** is every e-mail address, including office addresses.
- **AZ_VOEN** is every tax number, a company's too.
- **URL** is labelled only when it carries a token or a personal identifier. A plain web address (`birbank.az`, `https://portal.dim.gov.az/HR/`) is not labelled.
- **Not PII:** document, case and tender numbers (`2026/AT/05079/V1`), product codes, money amounts, weights (`100 kq`) and counts.
- **D-2 dummy values** (`1234`, `4242424242424242`, `P12345678`, …) are not labelled, if a real text ever has them.

## When unsure

Label your best choice and add a line to the unsure list (`unsure.tsv`, next to the documents; not `.jsonl`, because the scoreboard reads every `.jsonl` file in that folder as documents): document id, the text, and why you are unsure. The native-speaker check goes through that list.

## Language notes: English, Turkish, Russian

Everything above applies; these notes cover what differs. They follow how the translated training data (`merged_relabeled_swept_dated`) already labels these cases, so the independent sets measure the same thing as A7's translated sets (D-46b).

### English

- **Middle names are GIVENNAME:** `John Michael Smith` gives `John`, `Michael` (GIVENNAME) and `Smith` (SURNAME).
- **Initials are not labelled**, as in Azerbaijani: in `J. Smith` or `John F. Kennedy` only the full names are labelled.
- **Titles and suffixes stay outside:** `Mr`, `Dr`, `Sir`, `Jr`, `III` (training data: 626 of 626 titles outside).
- **Possessive `'s` stays outside:** `Smith's` → `Smith` (112 of 112).
- **CITY** covers towns, cities and villages; counties, states and regions are not CITY. A postcode is not ZIPCODE (ZIPCODE is the Azerbaijani `AZ` + 4 digits); leave it unlabelled and note it in the unsure list.
- **Dates:** `14 October 2026`, `October 14, 2026` and `14/10/2026` are DATE. `October 14` without a year is not.

### Turkish

- **The apostrophe suffix stays outside the span:** `Ankara'da` → `Ankara`, `Mahiroğlu'nun` → `Mahiroğlu` (with `'` or `’`). This differs from Azerbaijani, which has no apostrophe and keeps the suffix inside (D-9); the training data does the same (98 of 99 cases).
- **A suffix without an apostrophe is a different word:** `Ankaralı`, `Kalecikliler` (people from a place) are not labelled.
- **Provinces (il) and districts (ilçe) are CITY**, including provinces not named after their main city (`Kocaeli`, `Sakarya`) and districts of metropolitan cities (`Esenyurt`, `Başakşehir`, `Büyükçekmece`, `Sarıçam`, `Pursaklar`). **Neighbourhoods (`mahalle`) and city areas are not labelled**: `Cebeci Mahallesi`, `İkitelli`, `Ulus`. In an address, `Gonca Sokak` and `Fatih Caddesi` are STREET.
- **Names inside organisation and building names** follow the general rules: a city name is CITY (`İstanbul` in `İstanbul Aydın Üniversitesi` and in `İstanbul Eczanesi`); a person's name is not labelled (D-2): `Aydın` (the founder) in that university's name, `Atatürk’ün Eczanesi`, `Çandarlı İbrahim Paşa Hamamı`. A place-like brand (`Bilkent CYBERPARK`) is not labelled.
- **Initials are not labelled** (`M.Y.`, `Nur Banu S.` → `Nur`, `Banu`, two GIVENNAMEs); an age in brackets after them is AGE (`M.Y. (53)` → `53`).
- **Foreign names with a father's name** follow the patronymic rule: `Tedros Adhanom Ghebreyesus` → `Tedros`, `Adhanom` (father's name) GIVENNAME, `Ghebreyesus` SURNAME.
- **A name is labelled as written**, even when the article misspells it (`Caferoğlu` for `Mahiroğlu`: SURNAME).
- **Dates:** `09.10.2026` and `14 Ekim 2026` are DATE; `25 Eylül` without a year is not. A complete timestamp (`Ekim 14, 2026 10:59`) is not labelled; `25 Eylül’de saat 14.00` gives TIME `14.00` (see Time).
- These Turkish rules were checked by the team (native check, 2026-10-14) on the 14 open questions of the Turkish set.

### Russian

- **Case endings are inside the span**, as in Azerbaijani (D-9): `в Москве` → `Москве`, `Иванова` (genitive) → `Иванова`. The training data labels whole words (12,813 of 12,813).
- **Patronymics** (`Иван Петрович Сидоров`): the patronymic `Петрович` is GIVENNAME, by analogy with Azerbaijani (the father's name is GIVENNAME). The training data has almost no patronymics, so the Russian reader confirms this (D-46c) before the set is scored.
- **Initials are not labelled** (`И.П. Сидоров` → `Сидоров`).
- **A Latin spelling of a Russian name** is labelled the same way as the Cyrillic one.
- **Dates:** `14 октября 2026 года` → `14 октября 2026` (`года` stays outside, like `-cı il`); `14.10.2026` is DATE.

