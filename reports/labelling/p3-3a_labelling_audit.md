# P3-3a labelling check

Corpus `data/processed/merged_relabeled_swept/train.docs.jsonl` (SHA-256 `b4c737c162f8374a…`), 20000 documents sampled (seed 13), tokenizer `FacebookAI/xlm-roberta-large` + `add_punctuation_boundary`, max_length 512 / stride 256, labels from `prepare_splits.align_labels_for_window` (git `910e5f393f`). Threshold 0.5% for (a) and (b).

| Label | Entities | (a) no token at start % | (a') no B- % | (b) end mid-token % | (c) whitespace multi-token | (c) all B/I same label | Over 0.5%? |
|---|---|---|---|---|---|---|---|
| ACCESS_TOKEN | 924 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| AGE | 1883 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| API_KEY | 1539 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| AZ_DRIVER_LICENSE_NUMBER | 753 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| AZ_FIN | 1379 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| AZ_ID_CARD_NUMBER | 1073 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| AZ_PASSPORT_NUMBER | 888 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| AZ_VOEN | 821 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| BUILDINGNUM | 2286 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| CARD_SECURITY_CODE | 691 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| CITY | 4598 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 26 | 26/26 | no |
| DATE | 2749 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 1227 | 1227/1227 | no |
| EMAIL | 7475 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| GIVENNAME | 10911 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 3 | 3/3 | no |
| IBAN | 936 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 300 | 300/300 | no |
| ICCID | 470 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| IPV4_ADDRESS | 1243 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| IPV6_ADDRESS | 475 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| MAC_ADDRESS | 641 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| PAYMENT_CARD_NUMBER | 1215 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 506 | 506/506 | no |
| PRIVATE_KEY | 580 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 580 | 580/580 | no |
| STREET | 3123 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 3123 | 3123/3123 | no |
| SURNAME | 8998 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 2 | 2/2 | no |
| TELEPHONENUM | 6322 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 3663 | 3663/3663 | no |
| TIME | 1841 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 295 | 295/295 | no |
| URL | 1578 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| ZIPCODE | 2256 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |

## Slices (RC8 suffixed, RC9 punctuation-touching and bare names)

| Label | Slice | Value | Entities | (a) % | (a') % | (b) % |
|---|---|---|---|---|---|---|
| ACCESS_TOKEN | punct_after | yes | 264 | 0.000 | 0.000 | 0.000 |
| AGE | punct_after | yes | 261 | 0.000 | 0.000 | 0.000 |
| AGE | short_doc | yes | 1 | 0.000 | 0.000 | 0.000 |
| API_KEY | punct_after | yes | 688 | 0.000 | 0.000 | 0.000 |
| AZ_DRIVER_LICENSE_NUMBER | punct_after | yes | 263 | 0.000 | 0.000 | 0.000 |
| AZ_FIN | punct_after | yes | 477 | 0.000 | 0.000 | 0.000 |
| AZ_ID_CARD_NUMBER | punct_after | yes | 309 | 0.000 | 0.000 | 0.000 |
| AZ_PASSPORT_NUMBER | punct_after | yes | 278 | 0.000 | 0.000 | 0.000 |
| AZ_VOEN | punct_after | yes | 241 | 0.000 | 0.000 | 0.000 |
| BUILDINGNUM | punct_after | yes | 860 | 0.000 | 0.000 | 0.000 |
| CARD_SECURITY_CODE | punct_after | yes | 232 | 0.000 | 0.000 | 0.000 |
| CARD_SECURITY_CODE | short_doc | yes | 1 | 0.000 | 0.000 | 0.000 |
| CITY | punct_after | yes | 1293 | 0.000 | 0.000 | 0.000 |
| CITY | short_doc | yes | 1 | 0.000 | 0.000 | 0.000 |
| CITY | suffixed | case | 123 | 0.000 | 0.000 | 0.000 |
| CITY | suffixed | no | 4475 | 0.000 | 0.000 | 0.000 |
| DATE | punct_after | yes | 785 | 0.000 | 0.000 | 0.000 |
| EMAIL | punct_after | yes | 2022 | 0.000 | 0.000 | 0.000 |
| EMAIL | short_doc | yes | 1 | 0.000 | 0.000 | 0.000 |
| GIVENNAME | punct_after | yes | 3350 | 0.000 | 0.000 | 0.000 |
| GIVENNAME | suffixed | apostrophe | 2 | 0.000 | 0.000 | 0.000 |
| GIVENNAME | suffixed | case | 302 | 0.000 | 0.000 | 0.000 |
| GIVENNAME | suffixed | no | 10607 | 0.000 | 0.000 | 0.000 |
| IBAN | punct_after | yes | 285 | 0.000 | 0.000 | 0.000 |
| ICCID | punct_after | yes | 149 | 0.000 | 0.000 | 0.000 |
| IPV4_ADDRESS | punct_after | yes | 398 | 0.000 | 0.000 | 0.000 |
| IPV6_ADDRESS | punct_after | yes | 187 | 0.000 | 0.000 | 0.000 |
| MAC_ADDRESS | punct_after | yes | 225 | 0.000 | 0.000 | 0.000 |
| PAYMENT_CARD_NUMBER | punct_after | yes | 446 | 0.000 | 0.000 | 0.000 |
| PRIVATE_KEY | punct_after | yes | 98 | 0.000 | 0.000 | 0.000 |
| STREET | punct_after | yes | 1306 | 0.000 | 0.000 | 0.000 |
| STREET | suffixed | apostrophe | 4 | 0.000 | 0.000 | 0.000 |
| STREET | suffixed | no | 3119 | 0.000 | 0.000 | 0.000 |
| SURNAME | punct_after | yes | 3122 | 0.000 | 0.000 | 0.000 |
| SURNAME | short_doc | yes | 2 | 0.000 | 0.000 | 0.000 |
| SURNAME | suffixed | case | 839 | 0.000 | 0.000 | 0.000 |
| SURNAME | suffixed | no | 8159 | 0.000 | 0.000 | 0.000 |
| TELEPHONENUM | punct_after | yes | 1939 | 0.000 | 0.000 | 0.000 |
| TIME | punct_after | yes | 796 | 0.000 | 0.000 | 0.000 |
| URL | punct_after | yes | 516 | 0.000 | 0.000 | 0.000 |
| ZIPCODE | punct_after | yes | 717 | 0.000 | 0.000 | 0.000 |

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
