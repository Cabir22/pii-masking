# Confirmed masking failures

`your-hf-org/masking-multilingual` — manual + automated probing. Every input
below was run against the real checkpoint (raw model and/or the production
hybrid pipeline) and the output shown was directly observed, not inferred.

**Tags:**
- **MISSED** — nothing detected, plaintext leaks
- **PARTIAL** — some entities caught, others in the same input missed
- **MISLABELED** — detected and masked, but under the wrong label

Total: 47 confirmed cases across 12 categories, plus one corpus-level
root-cause finding (below the category list) that plausibly explains part
of categories 6 and 7.

> **Highest-priority finding across every language tested this session:**
> see category 12 (Russian grammatical case declension). It is the most
> cleanly isolated result in this whole catalog — a controlled pair where
> literally the only variable changed is grammatical declension, and that
> alone flips detection from a complete miss to a complete catch — and,
> unlike the other findings here, it affects what is likely the *default*
> case for how names appear in real, correctly-written Russian prose, not
> a narrow edge case.

---

## 1. Given name + surname with a grammatical suffix attached directly (no space)

GIVENNAME/SURNAME have no regex/checksum safety net, so a miss here is a
real leak. Fails across every grammatical person, not just 3rd-person
"-dır." The only reliably-working shape found all session is the specific
template "Soyadım X-dir" ("my surname is X").

| Tag | Input | Result |
|---|---|---|
| MISSED | `Mənim adım Əli Məmmədovdur` | Nothing detected — both GIVENNAME and SURNAME missed. |
| PARTIAL | `Mənim adım Aygün Hüseynovadır` | GIVENNAME "Aygün" caught; SURNAME "Hüseynovadır" missed. |
| PARTIAL | `Adım Vüqar Əliyevdir` | GIVENNAME caught; SURNAME "Əliyevdir" missed. |
| MISSED | `Mən Əliyevəm` | 1st-person copula ("I am Əliyev") — nothing detected. |
| MISSED | `Sən Məmmədovsan` | 2nd-person copula ("you are Məmmədov") — nothing detected. |
| MISSED | `Onlar Quliyevlərdir` | 3rd-person plural copula — nothing detected. |
| MISSED | `Bu sənəd Nəbiyevindir` | Possessive form ("this document is Nəbiyev's") — nothing detected. |
| MISSED | `Ofis Rəhimovdadır` | Locative+copula ("the office is at Rəhimov's") — nothing detected. |
| MISLABELED | `Telefon Kərimovundur` | "Kərimovundur" detected but tagged GIVENNAME — should be SURNAME. |
| MISSED | `Benim adım Ahmet Yılmazdır` | Same pattern in Turkish — nothing detected. |
| MISSED | `Mənim adım Əli-Xan Məmmədov-Zadədir` | Hyphenated compound given+surname — nothing detected. |
| PARTIAL | `Dostlar mənə Sasha deyir, əsl adım Aleksandrdır` | Nickname "Sasha" caught; real name "Aleksandrdır" (with suffix) missed. |
| MISSED | `Mənim adım Əli Əlidir` | "Əli" (extremely common 3-letter given name) fails even where other given names in this exact sentence shape (Ruslan, Aygün, Vüqar, Nərmin, Tural, Vüsalə) do not — nothing detected. |

## 2. Missing or substituted Azerbaijani/Turkish diacritics

The single highest-impact finding: a sentence shape that detects correctly
with the right characters fails completely when a diacritic is dropped or
swapped — something that happens constantly in real text typed on non-AZ
keyboards.

| Tag | Input | Result |
|---|---|---|
| MISSED | `Soyadım Eliyevdir, unutmayın` | "Ə" written as plain "E" — nothing detected. The identical sentence with "Əhmədovdur" (correct Ə) is caught correctly. |
| MISSED | `Imza: Kamran Rzayev` | Dotless ASCII "I" instead of Turkic dotted "İ" — nothing detected. The identical sentence with "İmza:" (correct İ) is caught correctly. |

## 3. ALL-CAPS text

Detection collapses in full caps regardless of which name is used — even
names that are reliably caught in normal case.

| Tag | Input | Result |
|---|---|---|
| MISSED | `MƏNIM ADIM ƏLİ MƏMMƏDOVDUR` | Nothing detected. |
| MISSED | `MƏNIM ADIM RUSLAN MƏMMƏDOVDUR` | Nothing detected — "Ruslan" is reliably caught in mixed/normal case. |

## 4. Surname-first ordering

Common on official AZ forms and documents. A nearby, correctly-formatted
DATE was still caught — the failure is specific to the reordered name pair.

| Tag | Input | Result |
|---|---|---|
| MISSED | `Məmmədov Əli, doğum tarixi 12.05.1990` | Only the DATE was caught; both GIVENNAME and SURNAME were missed. |

## 5. Plural / collective surname forms

A surname referring to a family/group ("the Məmmədovs' house") rather than
one individual.

| Tag | Input | Result |
|---|---|---|
| MISSED | `Məmmədovların evi böyükdür` | Nothing detected. |
| MISSED | `Əliyevlərə salam söylə` | Nothing detected. |
| MISSED | `Hüseynovlarla görüşdük` | Nothing detected. |

## 6. Low-context / signature-line placement

A name with no attached suffix at all, but sitting right after a closing
salutation or role label on its own line — minimal surrounding sentence
context.

| Tag | Input | Result |
|---|---|---|
| MISSED | `Hörmətlə,`<br>`Elnur Bağırov` | Nothing detected. |
| MISSED | `Sayğılarımla,`<br>`Rəşad Əliyev` | Nothing detected. |
| MISSED | `Best regards,`<br>`Orxan Nəbiyev` | English salutation before an AZ name — nothing detected. |
| MISSED | (blank line)`Leyla Həsənova` | Bare name alone on its own line, no salutation at all — nothing detected. |
| MISSED | `Kimdən: HR üzrə mütəxəssis Фирдуст Hadiyev` | Name after a role title in a memo header — nothing detected. |

## 7. A street name that is also a personal surname, with a compound suffix

Many Baku streets/avenues are named after historical figures, so this
overlaps directly with the surname-suffix failure above.

| Tag | Input | Result |
|---|---|---|
| MISSED | `Nərimanov prospektindəyəm` | Nothing detected (compare to "Füzuli küçəsində" and "Azadlıq prospektinə," which both mask correctly — the difference is the surname-derived street name plus a compound locative+copula suffix). |

## 8. No-separator / squished text

Fields run together with no delimiting space or punctuation.

| Tag | Input | Result |
|---|---|---|
| PARTIAL | `Telefon:0501234567Email:eli@mail.az` | EMAIL caught (unambiguous @ + domain shape); TELEPHONENUM silently dropped. |
| MISSED | `ƏliyevRəşad1990Bakı` | Surname, given name, year, and city all run together — nothing detected. |
| MISSED | `Ad:VüqarSoyad:Məmmədov` | Nothing detected. |

## 9. Numbers and dates in non-digit or incomplete form

| Tag | Input | Result |
|---|---|---|
| MISSED | `Doğum tarixim 1990-dır` | Year-only date — nothing detected. |
| MISSED | `Yaşım iyirmi beşdir` | Age spelled out in words ("twenty-five") — nothing detected. |
| MISSED | `Bina nömrəsi on yeddidir` | Building number spelled out in words ("seventeen") — nothing detected. |
| MISSED | `14 mart 2016` | Named-month date, mid-sentence in Cyrillic-language context — entirely undetected. |
| PARTIAL | `0 7 0   9 2 2   8 1 - 5 8` | Phone number with every digit spaced out one-by-one — only the leading "0" caught, the rest leaks in full. |

## 10. Numeric shape collisions (masked, but under the wrong label)

Not a leak — the value is still masked — but resolves to the wrong entity
type, and would report wrong on any per-label benchmark.

| Tag | Input | Result |
|---|---|---|
| MISLABELED | `VÖEN-im 123` | Too-short VOEN test value tagged CARD_SECURITY_CODE instead of AZ_VOEN. |
| MISLABELED | `FİN kodum 45` | Too-short FIN test value tagged CARD_SECURITY_CODE instead of AZ_FIN. |
| MISLABELED | `102-182-56-12` (typo'd phone number) | Tagged IPV4_ADDRESS instead of TELEPHONENUM. |

## 11. Span-boundary / mid-word breaks

The value is found, but the masked span is drawn in the wrong place —
either swallowing too little (a leak) or splitting one value into pieces.

| Tag | Input | Result |
|---|---|---|
| PARTIAL | `Mingəçevir'de` | Only "Mingəçevir" is masked — the possessive suffix "'de" leaks outside the CITY span. |
| PARTIAL | `A stara` (city name with an internal space) | Only "A" is masked — " stara" leaks. |
| PARTIAL | `Ağstafa` (city name with an internal newline) | Only the leading "A" is masked — the rest leaks. |
| PARTIAL | A PAYMENT_CARD_NUMBER split across a line break | Captured as two separate spans instead of one — still fully masked, but as two mismatched fragments. |
| PARTIAL | An IBAN split across a line break | Same fragmentation as the card-number case above. |
| PARTIAL | An EMAIL embedded inside a URL query string | Fragments into URL / EMAIL / URL pieces instead of one clean span (3 confirmed instances). |

---

## Root-cause finding: real, unlabeled names inside the training corpus itself

Not a live-model test — a full scan of the training corpus (416,279
documents, all four languages, all splits) for known GIVENNAME/SURNAME
pool values appearing in a document's text but **not covered by any
labeled entity span**. Checks whether the model's own training data
contains inconsistent signal — real names sometimes labeled, sometimes
not, in the same sentence positions the live model fails on. This is a
different mechanism from `scripts/piigen/negatives.py`'s hard negatives
(confirmed to contain zero name-related categories at all) — it's the
LLM generation process writing realistic extra names beyond what was
pre-planned for labeling, which then never get swept into gold labels.

**Headline result: 2,178 documents (0.52%) contain at least one unlabeled
real SURNAME — 2,876 raw occurrences total.** SURNAME is the reliable
signal here, since surnames essentially never double as ordinary
vocabulary the way given names do (see the GIVENNAME caveat below).

| Language | Docs w/ unlabeled surname | Rate |
|---|---|---|
| AZ (source language) | 1,355 / 105,419 | 1.29% |
| TR | 404 / 103,782 | 0.39% |
| EN | 348 / 104,777 | 0.33% |
| RU | 71 / 102,301 | 0.07% |

*Caveat on the RU figure:* this method does exact string matching against
known pool spellings, and RU renders names via Cyrillic transliteration
that doesn't always match the pool's stored spelling exactly — so RU is
very likely undercounted here, not genuinely cleaner. This has no bearing
on the separate, already-confirmed RU case-declension finding (category
12) either way.

**The contamination concentrates in exactly the sentence positions
category 6 and 7 already identified as live failures — not a coincidence:**

```
Respectfully,
Nermin Muradov          <- unlabeled in the training data itself
mukimlie@azdata.az
```
```
Hörmətlə,
Vəkil Muradov            <- unlabeled
Zirvə Hüquq Mərkəzi
```
```
İkamet Adresi | Vaqif Abdullayev caddesinde   <- a surname-derived street
                                                  reference, unlabeled as
                                                  either SURNAME or STREET
                                                  -- the likely origin of
                                                  category 7's finding
```
```
Ad: Elnur
Soyad: Məmmədov     <- the field is literally labeled "Surname:" and the
                        value right after it still isn't tagged
```

**GIVENNAME hits (21,184 raw) need manual judgment, not a bare count** —
most are legitimate common-word homonyms, correctly left unlabeled:
`Ümid` (4,073 — means "hope"), `Tamam` (3,576 — "okay"), `Mayıs`/`Nisan`
(1,156/732 — May/April), `Görüş` (971 — "meeting"), `İnkişaf` (317 —
"development"). But `Elnur` alone accounts for **5,401** unlabeled hits,
and unlike the words above, "Elnur" has no common-word meaning — it's
suspiciously concentrated compared to every other name-only value
(`Sabir` 386, `Sona` 165, `Zaur` 267, `Fidan` 146, `Günay` 104, `Elmira`
86, `Sevinc` 68), and is plausibly a systematic generation artifact (an
unplanned filler name recurring far more than any other) rather than
background noise.

**Practical implication:** this is a real, confirmed, non-hypothetical
contributing cause for at least part of categories 6 and 7 — the model
wasn't just under-exposed to those sentence positions, it was actively
shown *inconsistent* labeling for real names sitting in them. It's also
comparatively cheap to fix: a mechanical re-sweep of the existing corpus
(the same known-pool-value scan used here) to retroactively label or flag
affected documents, rather than full regeneration.

## 12. Russian grammatical case declension defeats name detection — HIGHEST PRIORITY

Russian requires a name to be grammatically inflected ("declined") almost
any time it isn't the sentence's subject — after a preposition, as a direct
or indirect object, or showing possession. This is not a rare construction;
it's how most real Russian sentences mention a name at all. The controlled
pair below changes exactly one variable — whether the name is correctly
declined — with everything else (sentence, names, position) held constant:

| Tag | Input | Result |
|---|---|---|
| MISSED | `Я познакомился с Акбаром Айдыновым` (instrumental case, grammatically correct Russian) | Nothing detected — both GIVENNAME and SURNAME missed. |
| — (control) | `Я познакомился с Акбар Айдынов` (identical sentence, names left undeclined — technically incorrect Russian) | Both GIVENNAME and SURNAME caught correctly. |

That one variable — declension on/off — is the entire difference between a
complete miss and a complete catch. It rules out the explanations that fit
other findings in this catalog (low context, name unfamiliarity, sentence
brevity): none of those changed between the two rows above.

A secondary, smaller effect layers on top of this: SURNAME tolerates full
isolation (no sentence at all) better than GIVENNAME does, but only in the
nominative form.

| Tag | Input | Result |
|---|---|---|
| MISLABELED | `Акбар Айдынов` (bare nominative pair, no sentence) | Only SURNAME "Айдынов" caught; GIVENNAME "Акбар" missed. |
| MISSED | `Айдынов` (surname alone, nominative) | Caught correctly. |
| MISSED | `Акбар` (given name alone, nominative) | Nothing detected. |
| — (control) | `Я познакомился с Акбар` (given name alone, undeclined, with sentence context) | Caught correctly. |

Practical implication: this pattern, if it holds generally across the RU
corpus, means the model may only reliably mask Russian names when they
happen to land in nominative subject position — a minority of real name
mentions in natural, correctly-written Russian prose. This is the same
underlying failure family as category 1 (Azerbaijani suffix attachment)
and the Turkish case in that same category — a morphologically rich
language inflecting a PII value in a way the training data under-
represents — so a retraining effort should very likely treat AZ
agglutination and RU case declension as one unified data-coverage gap,
not two separate fixes.
