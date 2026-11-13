# Azerbaijani PII Masking Dataset — Reference

**Dataset:** `data/repaired/combined.jsonl` · **Taxonomy:** v2.0.0 (locked) · **Compiled:** 2026-08-29
**Sources:** `data/schema.md`, `piigen/config.py`, `piigen/checksums.py`, `piigen/llm/edge_cases.py`, `piigen/negatives.py`

Trains a token classifier to **find spans of sensitive information in Azerbaijani text** for masking — and to **leave alone** strings that only look like PII. Every example in this document is copied verbatim from the dataset (synthetic; contains no real PII).

---

## 1. Overview

| | | | |
|---|---:|---|---:|
| Records | **105,419** | Labels | **27** |
| — `positive` docs | 80,632 | Entity mentions | 357,700 |
| — `negative_only` docs | 24,787 | Document types | 42 |
| Language | `az` only | Registers / length bands | 14 / 6 |

Edge-case–tagged records: **13,663** `positive_valid` (§6) + **281** `ambiguous_requires_anchor` (§7). Every other contrastive signal in the data is an unlabeled decoy injected by `negatives.py` — **25** hard-negative kinds (§8) and **19** adversarial near-miss kinds (§9).

---

## 2. Schema

One JSON object per line.

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique id, prefixed by source corpus |
| `text` | string | The document; may contain newlines; NFC-normalized |
| `lang` | string | Always `"az"` |
| `entities` | array | Labeled spans. **Always `[]` for `negative_only` docs** |
| `_doc_type`, `_bucket`, `_register` | string | Genre, length band, writing tone |
| `_noise` | array | Noise kinds applied; `[]` if none |
| `_hard_negatives`, `_adversarials` | integer | Decoy counts; `0` for positives |
| `_source` | string | `"llm"` or `"targeted"` (the targeted builder, §11) |
| `_decoys` | array | (2026-10, C2) `[{start, end, kind, resembles}]`: character spans that are deliberately **not** PII. Every quality gate skips a match that lies entirely inside one. Absent in records from before P2-3 (= none) |
| `_gen_version` | string | (C2) the git commit the generator ran from |
| `_frame_ids` | array | (C2, targeted only) the frames the document was built from |
| `_pii_free` | boolean | (2026-10) the document is deliberately PII-free (`entities == []` allowed; D-1) |
| `_suffixes` | array | (P2-4c, targeted) `[{start, end, stem_end, case, surface}]`: inflected words the generator wrote on purpose; the resolver and the validator trust these forms. `surface` is plain, apostrophe or folded |
| `_spec` | object | Generation plan — planned values, **the actual decoy strings** (`_spec.hard_negatives` holds every decoy; `_spec.adversarials` is the near-miss subset), seed, `edge_case` |
| `_repair` | array | Optional; repairs applied (11,146 records) |

**Entity object:** `start` (inclusive) · `end` (**exclusive**) · `label` · `text`.
Offsets are **character** offsets. `text == document.text[start:end]`, enforced on 100% of records. Entities never overlap.

```json
{"id": "repaired.clean__llm_az_000003",
 "text": "Müştəri Profili:\nAd: Nərmin\nMaliyyə kodu: 5V0PP33",
 "lang": "az",
 "entities": [{"start": 21, "end": 27, "label": "GIVENNAME", "text": "Nərmin"},
              {"start": 42, "end": 49, "label": "AZ_FIN",    "text": "5V0PP33"}],
 "_doc_type": "crm_note", "_bucket": "long", "_register": "bureaucratic and officious",
 "_noise": [], "_hard_negatives": 0, "_adversarials": 0, "_source": "llm",
 "_spec": {"entities": [{"label":"GIVENNAME","value":"Nərmin"}],
           "hard_negatives": [], "adversarials": [], "negative_only": false, "seed": 1544862794}}
```

---

## 3. The 27 Labels

**Tiers** decide how a label is detected and what kind of negative is meaningful for it:
`pattern` (16) — own shape + validator · `hybrid` (2) — mixed · `anchor_required` (5) — needs a nearby Azerbaijani cue word · `ml_context` (4) — no shape at all, pure NER.

| Label | Meaning | Tier | Valid. | Mentions |
|---|---|---|:--:|---:|
| `GIVENNAME` | First name | ml_context | — | 58,427 |
| `SURNAME` | Family name | ml_context | — | 43,578 |
| `EMAIL` | Email address | pattern | ✓ | 40,393 |
| `TELEPHONENUM` | Phone number | hybrid | ✓ | 32,994 |
| `CITY` | City / rayon (97-place gazetteer) | ml_context | — | 24,693 |
| `STREET` | Street or avenue | ml_context | — | 16,724 |
| `DATE` | PII-relevant date (e.g. DOB) | anchor_required | — | 15,077 |
| `ZIPCODE` | Postal code, `AZ`+4 digits | hybrid | ✓ | 12,353 |
| `BUILDINGNUM` | Building / house number | anchor_required | — | 12,303 |
| `AGE` | A person's age | anchor_required | — | 10,315 |
| `TIME` | PII-relevant time of day | anchor_required | — | 9,287 |
| `API_KEY` | API key / secret | pattern | ✓ | 8,485 |
| `URL` | URL, incl. embedded tokens | pattern | ✓ | 8,251 |
| `AZ_FIN` | Personal ID (FİN), 7 chars, **no I/O** | pattern | ✓ | 7,552 |
| `IPV4_ADDRESS` | IPv4 address | pattern | ✓ | 6,851 |
| `PAYMENT_CARD_NUMBER` | Card number, Luhn + BIN | pattern | ✓ | 6,309 |
| `AZ_ID_CARD_NUMBER` | Citizen ID, `AA/AB/DYI/MYI`+7 | pattern | ✓ | 5,591 |
| `IBAN` | Bank account, mod-97 checksum | pattern | ✓ | 5,011 |
| `ACCESS_TOKEN` | Bearer / JWT token | pattern | ✓ | 4,961 |
| `AZ_PASSPORT_NUMBER` | Passport, 1 letter + 8 digits, **incl. I/O** | pattern | ✓ | 4,625 |
| `AZ_DRIVER_LICENSE_NUMBER` | Licence, 2 letters + 6 digits | pattern | ✓ | 4,129 |
| `AZ_VOEN` | Tax ID, 10 digits, **no checksum exists** | pattern | ✓ | 4,000 |
| `CARD_SECURITY_CODE` | CVV / CVC | anchor_required | — | 3,890 |
| `MAC_ADDRESS` | Hardware address, 6 hex pairs | pattern | ✓ | 3,339 |
| `PRIVATE_KEY` | PEM / OpenSSH key block | pattern | ✓ | 3,321 |
| `ICCID` | SIM serial, `89` + 18 digits | pattern | ✓ | 2,690 |
| `IPV6_ADDRESS` | IPv6 address | pattern | ✓ | 2,551 |

**Removed — never generate or export:** `PASSWORD`, `AZ_BIRTH_CERTIFICATE_NUMBER`, `AZ_PROPERTY_REGISTER_NUMBER`.

---

## 4. Sample Classes

Classes exist at **two levels**. Keeping them apart is the main thing to understand.

**Document classes** — what a whole record is:

| Class | Records | `entities` | Model should |
|---|---:|---|---|
| `positive` | 80,632 | ≥ 1 span | Detect and label the PII |
| `negative_only` | 24,787 | **`[]` always** | Emit `O` for the entire document |

**Value classes** — what an individual string is:

| Class | Where it lives in the data | Model should | Meaning |
|---|---|---|---|
| `positive_valid` | Every span in a `positive` doc; 13,663 target a named edge case via `_spec.edge_case` | **Label it** | A real, format-valid value in natural context |
| `ambiguous_requires_anchor` | 281 docs, all `ZIPCODE` case ZIP-02 | **Depends** on a nearby cue word | Bare 4-digit code, resolved only by a postal anchor |
| `hard_negative` | Decoy strings in `negative_only` docs, `_spec.hard_negatives` minus `_spec.adversarials` (§8) | **Emit `O`** | A different kind of object — order ID, port, build hash |
| `adversarial` / `invalid_near_miss` | Decoy strings in `negative_only` docs, `_spec.adversarials` (§9) | **Emit `O`** | Regex matches, structure fails — bad Luhn, wrong IBAN digits, truncated key, obfuscated address |

> **Note:** `piigen/llm/edge_cases.py` also defines contrastive `hard_negative` / `invalid_near_miss` *cases* per label (APK-03, ATK-02, …). Those are **not present** in the current dataset — no record carries a negative-status `edge_case`. All contrastive negatives in the data come from the decoy injector (§8–§9).

---

## 5. Span Rules & Collisions

**Azerbaijani suffixes go INSIDE the span.** The most consequential boundary rule:

| Form | Span | Why |
|---|---|---|
| `Bakıda` ("in Baku") | `⟦Bakıda⟧` — whole word | It is a **single SentencePiece token**; a stem-only span would end mid-token and no classifier could emit it |
| `Qax'da` (apostrophe) | `⟦Qax'da⟧` | Same |
| `10:17-də` (hyphen) | `⟦10:17⟧-də` — suffix **outside** | The hyphen already tokenizes separately |

- Multi-token entities (`Qara Qarayev prospekti`, PEM blocks) are **one** span covering the whole value.
- Adjacent punctuation stays outside; `prepare_splits.add_punctuation_boundary()` adds a `Punctuation()` pre-tokenizer step so it isn't welded on.
- If a labeled value repeats in a document, **every occurrence is annotated**.
- `anchor_required` labels are never licensed by the value alone — `anchors.py` holds the cue lists and blocks structural positions (heading numbers, list markers, `Maddə 6`).

**Known shape collisions**, resolved by context only:

| Shape | Competing labels |
|---|---|
| 1–2 bare digits | `AGE` / `BUILDINGNUM` |
| 3 bare digits | `BUILDINGNUM` / `CARD_SECURITY_CODE` |
| 4 bare digits | `ZIPCODE` (domestic) / `BUILDINGNUM` |
| 10 bare digits | `TELEPHONENUM` / `AZ_VOEN` |
| 7 uppercase alnum | `AZ_FIN` / order IDs, git short SHAs |
| `dd.mm.yyyy` | `DATE` (PII) / `DATE_LIKE_ID` decoy (§9) |

**Alphabet rule:** `AZ_FIN` excludes `I` and `O`; `AZ_PASSPORT_NUMBER` includes them. They must never share an alphabet.

---

## 6. `positive_valid` — one dataset example per label

`⟦…⟧` marks the span the model must label. Case ids reference `edge_cases.LABEL_CASES`.

| Label | Case | Example |
|---|---|---|
| `GIVENNAME` | GVN-01 | …klinik qeydlər və yönləndirmə  ⟦Kərim⟧ müəyyən edilmiş klinik göstəricilərə… |
| `SURNAME` | SUR-01 | …məlumatları təqdim edirik: • Soyad: ⟦Rəhimli⟧ • Mövzu: Dəstək tələbi… |
| `EMAIL` | EML-01 | …de görüm, sən ⟦zeyneb.kazimov61@azdata.az⟧ ünvanından gələn maili… |
| `TELEPHONENUM` | TEL-01 | …**Əlaqə nömrəsi:** ⟦(055) 731-88-47⟧ *   **Xidmət növü:** Tam texniki… |
| `CITY` | CTY-01 | …Tarix: 12.05.2019 Məkan: ⟦Xankəndi⟧ Məhkəmə: Xankəndi Şəhər Məhkəməsi… |
| `STREET` | STR-01 | …Sorğu qəbul edildi. ⟦Xudu Məmmədov prospekti⟧ ünvanındakı filialda… |
| `DATE` | DAT-01 | …şəxsi işində doğum tarixi ⟦1949-09-16⟧ olaraq qeyd edilib. HR şöbəsinə… |
| `ZIPCODE` | ZIP-01 | …Nizami küçəsi, bina 12 Poçt indeksi: ⟦AZ6608⟧  Sənin iş prosesindəki… |
| `BUILDINGNUM` | BLD-01 | …Yaşayış Ünvanı: Nizami küçəsi, bina ⟦4⟧ Müraciət Mövzusu: Kommunal… |
| `AGE` | AGE-01 | …hadisə yerində saxlanılan şəxs ⟦49⟧ yaşındadır.  Şübhəli şəxsin ilkin… |
| `TIME` | TIM-01 | …Son əlaqə və ya müraciət ⟦18:35⟧ vaxtında qeydə alınmışdır… |
| `API_KEY` | APK-01 | …üçün vacibdir:  API açarı = "⟦sk_live_Ev8v8wfRY3Yc3Po9Gjf4AMlmr⟧"  Bunu… |
| `URL` | URL-01 | …əsas sübut olaraq qeydə alınmışdır:  ⟦https://my.azertelekom.az/magic?hash=-oU_YYlXAj…⟧ |
| `AZ_FIN` | FIN-01 | Yeni işç1 üçün Fin kodu ⟦LM53LM9⟧ təyin olundu. Maaş;Bonus;Status… |
| `IPV4_ADDRESS` | IP4-01 | …DEBUG: Connection established from ⟦25.15.254.207⟧. [2O19-05-12 09:00:12] INFO… |
| `PAYMENT_CARD_NUMBER` | PCN-01 | …Bank Kartı Kartın nömrəsi: ⟦4920 3606 2164 0207⟧ Ödəniş tarixi: 12 sentyabr 2023… |
| `AZ_ID_CARD_NUMBER` | IDC-01 | …Mənim şəxsiyyət vəsiqəsi nömrəm: ⟦AB2149083⟧. Sanki bu rəqəmləri bilmək… |
| `IBAN` | IBN-01 | …bu IBAN nömrəsini təsdiqləy- in: ⟦AZ89BDEO97290399936832355541⟧. Hər hansı sualınız… |
| `ACCESS_TOKEN` | ATK-01 | …göstərdi: Authorization: Bearer ⟦4Ehs8_qPJ09UF1Rej-nMqtNR3Iq5HZngADAh.TkOUX1kf…⟧ |
| `AZ_PASSPORT_NUMBER` | PAS-01 | …* Profil bölməsinə keçin * Pasport №: ⟦O12920344⟧ yazın * Təsdiqləyin… |
| `AZ_DRIVER_LICENSE_NUMBER` | DRV-01 | …Sürücülük vəsiqəsi \| ⟦PI206354⟧ Status  \| — Stabil… |
| `AZ_VOEN` | VOE-01 | …müşahidə olunur. Məsələn, VÖEN: ⟦4088316229⟧ üçün sistem sorğusu göndərildikdə… |
| `CARD_SECURITY_CODE` | CVV-01 | …Kartın təhlükəsizlik kodu (CVV): ⟦675⟧ kodu sistemə daxil edildikdə… |
| `MAC_ADDRESS` | MAC-01 | …Cihazın MAC ünvanı dəqiq olaraq ⟦00-16-3E-CB-3B-F0⟧ olmalıdır… |
| `PRIVATE_KEY` | PVK-01 | …-----BEGIN RSA PRIVATE KEY----- ⟦ssh-rsa AAAAB3NzaC1yc2Eqs/ZvIknFWNZossAzxty…⟧ -----END RSA PRIVATE KEY----- |
| `ICCID` | ICC-01 | …çəkmiş cihazın ICCID kodu ⟦89994572794389829569⟧ olaraq qeyd olunub… |
| `IPV6_ADDRESS` | IP6-01 | …şəbəkə məlumatları arasında ⟦2001:db8:f639:c76:7033:6567:d2ef:fc01⟧ IP ünvanı… |

---

## 7. `ambiguous_requires_anchor`

The only ambiguous case in the taxonomy. 281 documents.

| Case | Example | Resolves to |
|---|---|---|
| ZIP-02 | …Yenə eyni səhv! Şagirdin poçt indeksi ⟦AZ4760⟧ olmalıdır, amma sistemdə… | `ZIPCODE` — **only** because *poçt indeksi* sits next to it. Identical in shape to a bare `BUILDINGNUM`; with no postal cue nearby it would be `O`. |

---

## 8. Hard-negative decoys — 25 kinds

Strings that resemble PII but are a **different kind of object**. They live in `negative_only` documents; ground truth is `O` for all of them. One verbatim dataset example per kind (`negatives.HARD_NEGATIVES`).

| Kind | Example | What it actually is |
|---|---|---|
| `ORDER_ID` | `#8304373` | An order / line-item reference |
| `INVOICE_ID` | `BILL-QER-4510` | An invoice number |
| `TRACKING` | `PH899418249AZ` | A parcel tracking code |
| `POSTAL` | `AZ1618` | A region/lot code — no *poçt* anchor, so not `ZIPCODE` |
| `VERSION` | `iOS 18.0` | A software version string |
| `UUID` | `5ebe6b7a-ff37-9fff-556e-1f6aa586fdf9` | A random system UUID |
| `SHA256` | `3f4883d2b1fe69b5cca1861aac914d8d2f76233092d8fe89157f5445ec04c155` | A 64-hex content hash |
| `MD5` | `86ad340c251bec1d1bfadde07682d7d4` | A 32-hex digest |
| `HEX_BLOB` | `0xCBD2C7D5DF4C` | A hex constant / dump value |
| `BUILD_HASH` | `build-878d1fa01413` | A CI build identifier |
| `MEM_ADDR` | `0xf0773cf65a3b` | A memory address |
| `GIT_SHA` | `5e6661e3` | A git short hash — shape collides with `AZ_FIN` |
| `CONTAINER_ID` | `dc2bb6aafbd2` | A Docker container id |
| `TIMESTAMP` | `01.06.2025 07:32` | A log timestamp — not a PII `DATE`/`TIME` |
| `REF_CODE` | `CASE-3578955` | A ticket / case reference |
| `EMPLOYEE_ID` | `E-673775` | An internal staff number |
| `PORT` | `27017` | A network port |
| `AMOUNT` | `$1770.98` | A monetary amount |
| `SKU` | `SKU-AJL-09475` | A product / stock code |
| `COORDINATES` | `-51.383626, 123.204489` | Map coordinates |
| `ERROR_CODE` | `E0296` | A diagnostic / error code |
| `PERCENT` | `79.6%` | A percentage figure |
| `DURATION` | `45s` | An elapsed-time measurement |
| `LICENSE_KEY_PRODUCT` | `VUZIT-XRP73-HJ6WP-XFWNT-M7JBF` | A product licence key (not an API secret) |
| `SESSION_COUNT` | `318991` | A bare count / tally |

---

## 9. Adversarial near-miss decoys — 19 kinds

The harder class: a **regex would match**, but the value is structurally invalid or is deliberately obfuscated/partial PII. These are what separate a model that learned *structure* from one that learned *shape*. Ground truth is `O`. One verbatim dataset example per kind (`negatives.ADVERSARIAL`).

| Kind | Example | Why it is still `O` |
|---|---|---|
| `LOYALTY_CARD_LUHN_BAD` | `6229013433886893` | 16 digits, card-shaped — **fails Luhn** |
| `IBAN_BAD_CHECKSUM` | `DE33032543495959629430` | IBAN-shaped — **fails mod-97** |
| `VIN_BAD_CHECKDIGIT` | `WVW2JK2N0VL923454` | 17-char VIN — check digit wrong |
| `IMEI_BAD_LUHN` | `620510174941098` | 15 digits, IMEI-shaped — fails Luhn |
| `IP_INVALID_OCTET` | `338.17.40.607` | dotted quad — octets **> 255** |
| `IP_LIKE_VERSION` | `4.31.95.495` | four dotted numbers, out of IPv4 range |
| `MAC_LIKE_HASH` | `66:c6:67:b8:e7:33:0d:19` | **8** hex pairs — a MAC has 6 |
| `DATE_LIKE_ID` | `27.06.2010` | `dd.mm.yyyy` shape, but a record id — no DOB anchor |
| `SSN_LIKE_CODE` | `498-413-173` | `NNN-NN-NNNN`-style code; no such AZ identifier |
| `ISBN` | `978-1-982-36211-6` | book number — digit-group shape near ICCID/EAN |
| `PLATE_LIKE_CODE` | `RACK-PT10` | letters+digits like a plate / licence |
| `TRUNCATED_API_KEY` | `AKIASW37OM****` | real provider prefix, body replaced by `*` |
| `MASKED_CARD` | `•••• 3509` | only the last 4 digits shown |
| `MASKED_EMAIL` | `dob***@***.az` | local part and domain starred out |
| `PARTIAL_PHONE` | `...742` | trailing fragment of a number |
| `REDACTED` | `[[email protected]]` | a redaction placeholder, not a value |
| `EMAIL_LIKE_HANDLE` | `npm@latest` | `user@host`-shaped, not an address |
| `OBFUSCATED_EMAIL` | `swape AT hymbqc DOT org` | address spelled out to dodge a matcher |
| `URL_NO_TOKEN` | `https://docs.internal.dev/getting-started` | URL with **no** credential-bearing parameter |

**Why the four `ml_context` labels (`GIVENNAME` `SURNAME` `CITY` `STREET`) have no negative kinds:** a name is a name because of *where it sits*, not what it looks like. There is no "invalid name" a regex could match, so `invalid_near_miss` is logically undefined; the catalog gives them a second `positive_valid` case instead (GVN-02 initial form, SUR-02 feminine form, CTY-02 running-prose form, STR-02 `prospekti` suffix).

---

## 10. Terms

**Span** — character range, `start` inclusive to `end` exclusive · **Tier** — how a label is detected · **Anchor** — an Azerbaijani cue word licensing a shapeless value (*yaş* → `AGE`) · **Decoy** — a PII-shaped string deliberately left unlabeled (§8–§9) · **Resolver** — `resolver.py`, locates planned values in text and emits spans · **BIO** — `B-`/`I-`/`O` tagging used at training time.

---

## 11. Generator changes since checkpoint 1 (sprint of 2026-10-01 to 2026-10-08)

Written for task P2-10. The benchmark of checkpoint 1 (68.4 F1) found that the training data, not the model, was missing the shapes it failed on. Every change below is **training data**; `scripts/pii_guard/` is untouched (A2 rule 1).

### 11.1 Value forms (`piigen/values.py`, P2-1)

| Label | Before | Now |
|---|---|---|
| `ACCESS_TOKEN` | JWTs only | JWT at most 30% (measured 26%); prefixed opaque tokens (`at_`, `bearer_`, `tok_`, `oauth_`, `sess_`, `atk-`, `pat_` + 20–64 base64url or hex); bare 32–64 character base64url or hex. Validator and `data/schema.md` widened: the benchmark's real tokens are prefixed |
| `API_KEY` | vendor prefixes | adds `key_`, `api_`, `apikey_`, `svc_`, `sk-live-`, `sk-test-`. The ACCESS_TOKEN and API_KEY prefix lists are disjoint (tested) |
| `IPV6_ADDRESS` | no `::` in 8,033 training values | at least 60% compressed (measured 64%): `::` at start, middle and end, `::1`, `::ffff:a.b.c.d`, dropped zeros, mixed case |
| `MAC_ADDRESS` | colon form | colon, dash and dotted (`aabb.ccdd.eeff`), mixed case |
| `AZ_DRIVER_LICENSE_NUMBER` | `AA`/`AB` almost never | all letter pairs with `AA`/`AB` at least 35% (measured 41%), 2 letters + 6 digits. `AZ_ID_CARD_NUMBER` is unchanged (7 digits), so digit count and anchor word separate them |
| names | one spelling | about 10% rendered in another script or spelling (`Məmmədov` → `Mammadov`, `Маммадов`) |

### 11.2 Decoys and the negative policy (`piigen/negatives.py`, P2-2, P2-3; D-1, D-2)

- **D-1 reversed the negative policy.** Checkpoint 1 was trained with `negative_only_rate`, `hard_negative_rate` and `adversarial_rate` all 0.0 ("true positives only"), so it never saw a look-alike and the benchmark's 1,784 decoy triggers followed. Deliberate PII-free documents and decoys are back. Target shares in the LLM batches: hard-negative 30%, adversarial 20%, PII-free 10%, edge cases 30%.
- **Anchored decoys:** `ANCHORED_DECOYS` has **53 kinds** (7 are policy decoys, D-2) for 21 look-alike labels, placed next to the correct anchor word (`CVV kodu 12345`, `saat 25:81`, `yaş 999`, `otaq 247` beside a labelled `bina`, sentence-initial `Ərizənin`, `<SURNAME> MMC`). Every non-policy decoy must fail `validate.value_valid` for the label it resembles; every policy decoy must pass it (tested, 1,000 draws per kind). The older unanchored near-misses stay.
- **`_decoys` field and the gate exemption (P2-3):** the leak gate, the planned-value check and the invented-PII check skip a match entirely inside a declared decoy span; the same string undeclared still fails.

### 11.3 The targeted corpus builder (`scripts/build_targeted_corpus.py`, `piigen/targeted/`, P2-4)

Template-built documents, seconds for 25,000 (D-20). Families: decoy pairs (at least 30% of documents carry a decoy), cross-label contrast (token versus key, IPv6 versus MAC, licence versus ID with the same prefix), prose placements from the frames (`frames_az.py`), structured containers (CSV, pipe table, JSON, log, key-value, dialogue; at least 15%), single-entity documents (at least 25%), PII-free documents (about 10%), minimal-context documents of one to five words (`Fidan.`; about 5%) and homograph pairs (`Dəniz zəng etdi` against `Dəniz sakit idi`; about 5%, `homograph_noun` decoys). No frame is used in more than 3% of documents; the build fails otherwise. Boundary data: PEM keys of varied width, values touching punctuation and line breaks, query-string tokens, space-grouped phones, cards and IBANs. Entity casing and ASCII-folding noise is capped at 8% of entities.

### 11.4 Case suffixes (`targeted/suffix.py`, `resolver.py`, P2-4c, D-9)

The benchmark team reported that names, cities and streets almost never carried a case suffix (7–12% of mentions). The renderer inflects with Azerbaijani vowel harmony and buffer consonants in 13 cases (`gen dat acc loc abl ins rel pl pl_gen pl_dat pl_loc pl_abl cop`) plus tier-2 forms; **the label covers value plus suffix**. 35–40% of name, city and street mentions in the targeted corpus are suffixed, every case at least 5% of those. About 10% of suffixed mentions use the apostrophe form or an ASCII-folded suffix, and about 5% a noisy one (wrong harmony, dropped buffer, doubled consonant); the resolver trusts a form only when the record declares it in `_suffixes`. Suffixes follow the written letters, so English-spelled and foreign names are never k/q-softened.

### 11.5 Value pools (D-23c, D-23d; P2-14, P2-15)

- **CITY:** 4,414 names (`locales/data/az_settlements.txt`): 1 capital (5% of draws), 96 cities (45%), 3,998 villages and settlements (42%, by √population), 319 foreign cities (8%). Wikidata (CC0), queried 2026-10-07, queries and raw results in `data/sources/`. The 97-city `az_cities.txt` stays as it was: the frozen `pii_guard` reads it.
- **Foreign names:** 2,165 given names and 2,737 surnames of 8 origins (ru, tr, ka, fa, ar, en, de, fr), same source and method. One origin per person, so `Sergey Petrov`, never `Sergey Məmmədova`. Foreign persons are 13% of LLM briefs and 15% of the targeted builder's draws, about 12–13% of all name mentions. The Azerbaijani name pools are unchanged.

### 11.6 The LLM path (`piigen/llm/`, P2-5, P2-6, D-15c, D-17)

- **Briefs:** contrast lessons (`CON-01..03`), decoy-next-to-anchor cases, a target case for about 40% of planned names, cities and streets (the prompt allows an inflected surface form for these four labels only), structured layouts, planned document dates, short and homograph briefs.
- **Dates (D-17):** a standalone date is DATE; a date followed by a time is a timestamp and is not labelled. Generation plans the document date and rejects others. The label-mix steering leaves the planned document date and a contrast lesson's two values out, so neither stops a run.
- **Gates added over the batches:** invented PII (a gazetteer city, a street, `bina N`, a full name; D-15c: such documents are dropped, never edited), including streets spelt without Azerbaijani letters and a homograph given name before a surname; invented emails with non-ASCII letters; corrupt text; planned names misspelt inside the word; the noise language net.
- **Cleaning:** `scripts/clean_llm_batch.py <raw> --drop-unplanned-pii`, then `scripts/relabel_standalone_dates.py`. A kept line is never edited. Clean files: b1 5,115, b2 5,775, b3 5,965, b4 5,970, b5 21,265 (44,090 documents). The old Azerbaijani corpus has its own drop list (`az_drop_list.jsonl`, P2-16): 15,347 of 105,413 documents dropped for any blocking `validate_corpus` check, invented PII, an unlabelled date or Turkish text; the remaining 90,066 pass `validate_corpus`.

### 11.7 Known gaps (for the fix round)

- RC5 coverage (full-length PEM keys, space-grouped phones and cards, bare names, cards and IBANs in prose) is counted but not raised (P2-17, after Run B).
- A consonant-final place name with an apostrophe and the bare accusative (`Ağdam'ı`) is not labelled whole by the resolver (P2-14 note); the fix waits for a relabel of 7 old documents.
- Some Turkish surnames ending in `-k` (`Bayrak`) take the written-letter suffix (`Bayrakın`); the team is asked whether a native speaker would write `Bayrağın`.

*For dataset quality findings see `reports/audit_2026_08_29/`.*
