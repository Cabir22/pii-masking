# P2-12 labelling re-run (P3-3a method)

Corpus `data/raw/sprint1_llm_b4.clean.jsonl` (SHA-256 `3ae14a178d0cf932…`), 5973 documents sampled (seed 13), tokenizer `FacebookAI/xlm-roberta-large` + `add_punctuation_boundary`, max_length 512 / stride 256, labels from `prepare_splits.align_labels_for_window` (git `a03da9f401`). Threshold 0.5% for (a) and (b).

| Label | Entities | (a) no token at start % | (a') no B- % | (b) end mid-token % | (c) whitespace multi-token | (c) all B/I same label | Over 0.5%? |
|---|---|---|---|---|---|---|---|
| ACCESS_TOKEN | 283 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| AGE | 555 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| API_KEY | 461 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| AZ_DRIVER_LICENSE_NUMBER | 240 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| AZ_FIN | 431 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| AZ_ID_CARD_NUMBER | 299 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| AZ_PASSPORT_NUMBER | 279 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| AZ_VOEN | 220 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| BUILDINGNUM | 669 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| CARD_SECURITY_CODE | 243 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| CITY | 1314 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 7 | 7/7 | no |
| DATE | 2761 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 763 | 763/763 | no |
| EMAIL | 2102 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| GIVENNAME | 2896 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 4 | 4/4 | no |
| IBAN | 315 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 96 | 96/96 | no |
| ICCID | 214 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| IPV4_ADDRESS | 390 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| IPV6_ADDRESS | 183 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| MAC_ADDRESS | 209 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| PAYMENT_CARD_NUMBER | 364 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 139 | 139/139 | no |
| PRIVATE_KEY | 192 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 192 | 192/192 | no |
| STREET | 946 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 946 | 946/946 | no |
| SURNAME | 2285 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 4 | 4/4 | no |
| TELEPHONENUM | 1768 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 976 | 976/976 | no |
| TIME | 739 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 118 | 118/118 | no |
| URL | 468 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| ZIPCODE | 690 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |

## Slices (RC8 suffixed, RC9 punctuation-touching and bare names)

| Label | Slice | Value | Entities | (a) % | (a') % | (b) % |
|---|---|---|---|---|---|---|
| ACCESS_TOKEN | punct_after | yes | 71 | 0.000 | 0.000 | 0.000 |
| AGE | punct_after | yes | 22 | 0.000 | 0.000 | 0.000 |
| API_KEY | punct_after | yes | 170 | 0.000 | 0.000 | 0.000 |
| AZ_DRIVER_LICENSE_NUMBER | punct_after | yes | 43 | 0.000 | 0.000 | 0.000 |
| AZ_FIN | punct_after | yes | 39 | 0.000 | 0.000 | 0.000 |
| AZ_ID_CARD_NUMBER | punct_after | yes | 45 | 0.000 | 0.000 | 0.000 |
| AZ_PASSPORT_NUMBER | punct_after | yes | 49 | 0.000 | 0.000 | 0.000 |
| AZ_VOEN | punct_after | yes | 34 | 0.000 | 0.000 | 0.000 |
| BUILDINGNUM | punct_after | yes | 111 | 0.000 | 0.000 | 0.000 |
| CARD_SECURITY_CODE | punct_after | yes | 28 | 0.000 | 0.000 | 0.000 |
| CITY | punct_after | yes | 127 | 0.000 | 0.000 | 0.000 |
| CITY | suffixed | case | 627 | 0.000 | 0.000 | 0.000 |
| CITY | suffixed | no | 687 | 0.000 | 0.000 | 0.000 |
| DATE | punct_after | yes | 164 | 0.000 | 0.000 | 0.000 |
| EMAIL | punct_after | yes | 223 | 0.000 | 0.000 | 0.000 |
| GIVENNAME | punct_after | yes | 465 | 0.000 | 0.000 | 0.000 |
| GIVENNAME | suffixed | case | 215 | 0.000 | 0.000 | 0.000 |
| GIVENNAME | suffixed | no | 2681 | 0.000 | 0.000 | 0.000 |
| IBAN | punct_after | yes | 66 | 0.000 | 0.000 | 0.000 |
| ICCID | punct_after | yes | 40 | 0.000 | 0.000 | 0.000 |
| IPV4_ADDRESS | punct_after | yes | 58 | 0.000 | 0.000 | 0.000 |
| IPV6_ADDRESS | punct_after | yes | 26 | 0.000 | 0.000 | 0.000 |
| MAC_ADDRESS | punct_after | yes | 32 | 0.000 | 0.000 | 0.000 |
| PAYMENT_CARD_NUMBER | punct_after | yes | 81 | 0.000 | 0.000 | 0.000 |
| PRIVATE_KEY | punct_after | yes | 20 | 0.000 | 0.000 | 0.000 |
| STREET | punct_after | yes | 161 | 0.000 | 0.000 | 0.000 |
| STREET | suffixed | apostrophe | 3 | 0.000 | 0.000 | 0.000 |
| STREET | suffixed | case | 11 | 0.000 | 0.000 | 0.000 |
| STREET | suffixed | no | 932 | 0.000 | 0.000 | 0.000 |
| SURNAME | punct_after | yes | 374 | 0.000 | 0.000 | 0.000 |
| SURNAME | short_doc | yes | 1 | 0.000 | 0.000 | 0.000 |
| SURNAME | suffixed | case | 308 | 0.000 | 0.000 | 0.000 |
| SURNAME | suffixed | no | 1977 | 0.000 | 0.000 | 0.000 |
| TELEPHONENUM | punct_after | yes | 270 | 0.000 | 0.000 | 0.000 |
| TIME | punct_after | yes | 263 | 0.000 | 0.000 | 0.000 |
| URL | punct_after | yes | 117 | 0.000 | 0.000 | 0.000 |
| ZIPCODE | punct_after | yes | 109 | 0.000 | 0.000 | 0.000 |

## Hand-written minimal cases

| Text | Tokens (label) | OK |
|---|---|---|
| `Fidan.` | `Fi`:B-GIVENNAME `dan`:I-GIVENNAME `.`:O | yes |
| `Fidan!` | `Fi`:B-GIVENNAME `dan`:I-GIVENNAME `!`:O | yes |
| `(Fidan)` | `(`:O `(`:O `Fi`:B-GIVENNAME `dan`:I-GIVENNAME `)`:O | yes |
| `"Fidan"` | `"`:O `"`:O `Fi`:B-GIVENNAME `dan`:I-GIVENNAME `"`:O | yes |
| `Fidan Məmmədova` | `Fi`:B-GIVENNAME `dan`:I-GIVENNAME `Məmmədov`:B-SURNAME `a`:I-SURNAME | yes |
| `Salam, Fidan!` | `Salam`:O `,`:O `Fi`:B-GIVENNAME `dan`:I-GIVENNAME `!`:O | yes |
| `Hörmətlə, Fidan Məmmədova` | `Hör`:O `m`:O `ətlə`:O `,`:O `Fi`:B-GIVENNAME `dan`:I-GIVENNAME `Məmmədov`:B-SURNAME `a`:I-SURNAME | yes |
| `— Fidan` | `—`:O `—`:O `Fi`:B-GIVENNAME `dan`:I-GIVENNAME | yes |
| `Bakıda yaşayıram.` | `Bakıda`:B-CITY `yaşayır`:O `am`:O `.`:O | yes |
| `Bakını gördüm.` | `Bakı`:B-CITY `nı`:I-CITY `gördüm`:O `.`:O | yes |
| `Bakıdakı ofis bağlıdır.` | `Bakı`:B-CITY `dakı`:I-CITY `of`:O `is`:O `bağlıdır`:O `.`:O | yes |
| `Gəncədən gəldim.` | `Gəncədə`:B-CITY `n`:I-CITY `gəldi`:O `m`:O `.`:O | yes |
| `Əsgərin kitabı buradadır.` | `Ə`:B-GIVENNAME `s`:I-GIVENNAME `gə`:I-GIVENNAME `rin`:I-GIVENNAME `kitabı`:O `burada`:O `dır`:O `.`:O | yes |
| `Əsgəri çağırdım.` | `Ə`:B-GIVENNAME `s`:I-GIVENNAME `g`:I-GIVENNAME `əri`:I-GIVENNAME `çağır`:O `dım`:O `.`:O | yes |
| `Əsgərlə danışdım.` | `Ə`:B-GIVENNAME `s`:I-GIVENNAME `g`:I-GIVENNAME `ər`:I-GIVENNAME `lə`:I-GIVENNAME `danışdı`:O `m`:O `.`:O | yes |
| `Əsgərdən məktub gəldi.` | `Ə`:B-GIVENNAME `s`:I-GIVENNAME `g`:I-GIVENNAME `ər`:I-GIVENNAME `dən`:I-GIVENNAME `məktub`:O `gəldi`:O `.`:O | yes |
| `Əsgər'in sənədi hazırdır.` | `Ə`:B-GIVENNAME `s`:I-GIVENNAME `g`:I-GIVENNAME `ər`:I-GIVENNAME `'`:I-GIVENNAME `in`:I-GIVENNAME `sənəd`:O `i`:O `hazır`:O `dır`:O `.`:O | yes |
| `Məmmədovlar gəldi.` | `Məmmədov`:B-SURNAME `lar`:I-SURNAME `gəldi`:O `.`:O | yes |
| `Məmmədovların evi` | `Məmmədov`:B-SURNAME `ların`:I-SURNAME `e`:O `vi`:O | yes |
| `Nizami küçəsində görüşək.` | `Nizami`:B-STREET `küçəsi`:I-STREET `ndə`:I-STREET `görüş`:O `ək`:O `.`:O | yes |
| `Nizami küçəsindən keçdik.` | `Nizami`:B-STREET `küçəsi`:I-STREET `ndən`:I-STREET `keçdi`:O `k`:O `.`:O | yes |
| `Bakida yasayiram.` | `Bak`:B-CITY `ida`:I-CITY `yasa`:O `yi`:O `ram`:O `.`:O | yes |
| `Esgerden mektub geldi.` | `Es`:B-GIVENNAME `ger`:I-GIVENNAME `den`:I-GIVENNAME `m`:O `mek`:O `tub`:O `geldi`:O `.`:O | yes |
| `Tel: +994 50 123 45 67.` | `Tel`:O `:`:O `+`:B-TELEPHONENUM `+`:I-TELEPHONENUM `99`:I-TELEPHONENUM `4`:I-TELEPHONENUM `50`:I-TELEPHONENUM `123`:I-TELEPHONENUM `45`:I-TELEPHONENUM `67`:I-TELEPHONENUM `.`:O | yes |
| `Kart 4169 7388 1234 5678, müddət 12/27` | `Kart`:O `4`:B-PAYMENT_CARD_NUMBER `169`:I-PAYMENT_CARD_NUMBER `7`:I-PAYMENT_CARD_NUMBER `388`:I-PAYMENT_CARD_NUMBER `1`:I-PAYMENT_CARD_NUMBER `1234`:I-PAYMENT_CARD_NUMBER `5`:I-PAYMENT_CARD_NUMBER `678`:I-PAYMENT_CARD_NUMBER `,`:O `müddət`:O `12`:O `/`:O `27`:O | yes |
| `IBAN: AZ21 NABZ 0000 0000 1370 1000 1944` | `I`:O `BAN`:O `:`:O `AZ`:B-IBAN `21`:I-IBAN `NAB`:I-IBAN `Z`:I-IBAN `0`:I-IBAN `0000`:I-IBAN `0`:I-IBAN `0000`:I-IBAN `13`:I-IBAN `70`:I-IBAN `1000`:I-IBAN `1944`:I-IBAN | yes |
