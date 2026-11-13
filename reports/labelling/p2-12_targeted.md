# P2-12 labelling re-run (P3-3a method)

Corpus `sprint1_targeted.jsonl` (rebuilt locally, see the P2-12 log) (SHA-256 `923433e87234aa2a…`), 25000 documents sampled (seed 13), tokenizer `FacebookAI/xlm-roberta-large` + `add_punctuation_boundary`, max_length 512 / stride 256, labels from `prepare_splits.align_labels_for_window` (git `a03da9f401`). Threshold 0.5% for (a) and (b).

| Label | Entities | (a) no token at start % | (a') no B- % | (b) end mid-token % | (c) whitespace multi-token | (c) all B/I same label | Over 0.5%? |
|---|---|---|---|---|---|---|---|
| ACCESS_TOKEN | 1585 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| AGE | 535 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| API_KEY | 2006 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| AZ_DRIVER_LICENSE_NUMBER | 4322 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| AZ_FIN | 1321 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| AZ_ID_CARD_NUMBER | 4268 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| AZ_PASSPORT_NUMBER | 1300 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| AZ_VOEN | 1324 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| BUILDINGNUM | 1605 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| CARD_SECURITY_CODE | 673 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| CITY | 2806 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 31 | 31/31 | no |
| DATE | 1644 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 561 | 561/561 | no |
| EMAIL | 1131 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| GIVENNAME | 5788 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| IBAN | 1316 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 466 | 466/466 | no |
| ICCID | 1133 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| IPV4_ADDRESS | 1192 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| IPV6_ADDRESS | 2084 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| MAC_ADDRESS | 2144 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| PAYMENT_CARD_NUMBER | 1373 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 702 | 702/702 | no |
| PRIVATE_KEY | 272 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 272 | 272/272 | no |
| STREET | 2131 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 2131 | 2131/2131 | no |
| SURNAME | 4618 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| TELEPHONENUM | 1287 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 775 | 775/775 | no |
| TIME | 1335 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 210 | 210/210 | no |
| URL | 558 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |
| ZIPCODE | 1210 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0 | 0/0 | no |

## Slices (RC8 suffixed, RC9 punctuation-touching and bare names)

| Label | Slice | Value | Entities | (a) % | (a') % | (b) % |
|---|---|---|---|---|---|---|
| ACCESS_TOKEN | punct_after | yes | 399 | 0.000 | 0.000 | 0.000 |
| AGE | punct_after | yes | 83 | 0.000 | 0.000 | 0.000 |
| API_KEY | punct_after | yes | 595 | 0.000 | 0.000 | 0.000 |
| AZ_DRIVER_LICENSE_NUMBER | punct_after | yes | 1591 | 0.000 | 0.000 | 0.000 |
| AZ_FIN | punct_after | yes | 454 | 0.000 | 0.000 | 0.000 |
| AZ_ID_CARD_NUMBER | punct_after | yes | 1856 | 0.000 | 0.000 | 0.000 |
| AZ_PASSPORT_NUMBER | punct_after | yes | 432 | 0.000 | 0.000 | 0.000 |
| AZ_VOEN | punct_after | yes | 516 | 0.000 | 0.000 | 0.000 |
| BUILDINGNUM | punct_after | yes | 1395 | 0.000 | 0.000 | 0.000 |
| CARD_SECURITY_CODE | punct_after | yes | 167 | 0.000 | 0.000 | 0.000 |
| CITY | declared_suffix | apostrophe | 12 | 0.000 | 0.000 | 0.000 |
| CITY | declared_suffix | folded | 81 | 0.000 | 0.000 | 0.000 |
| CITY | declared_suffix | noisy | 55 | 0.000 | 0.000 | 0.000 |
| CITY | declared_suffix | plain | 941 | 0.000 | 0.000 | 0.000 |
| CITY | punct_after | yes | 964 | 0.000 | 0.000 | 0.000 |
| CITY | short_doc | yes | 105 | 0.000 | 0.000 | 0.000 |
| CITY | suffixed | apostrophe | 12 | 0.000 | 0.000 | 0.000 |
| CITY | suffixed | case | 426 | 0.000 | 0.000 | 0.000 |
| CITY | suffixed | no | 2368 | 0.000 | 0.000 | 0.000 |
| DATE | punct_after | yes | 524 | 0.000 | 0.000 | 0.000 |
| EMAIL | punct_after | yes | 488 | 0.000 | 0.000 | 0.000 |
| GIVENNAME | declared_suffix | apostrophe | 21 | 0.000 | 0.000 | 0.000 |
| GIVENNAME | declared_suffix | folded | 83 | 0.000 | 0.000 | 0.000 |
| GIVENNAME | declared_suffix | noisy | 57 | 0.000 | 0.000 | 0.000 |
| GIVENNAME | declared_suffix | plain | 1557 | 0.000 | 0.000 | 0.000 |
| GIVENNAME | punct_after | yes | 1357 | 0.000 | 0.000 | 0.000 |
| GIVENNAME | short_doc | yes | 1038 | 0.000 | 0.000 | 0.000 |
| GIVENNAME | suffixed | apostrophe | 21 | 0.000 | 0.000 | 0.000 |
| GIVENNAME | suffixed | case | 744 | 0.000 | 0.000 | 0.000 |
| GIVENNAME | suffixed | no | 5023 | 0.000 | 0.000 | 0.000 |
| IBAN | punct_after | yes | 583 | 0.000 | 0.000 | 0.000 |
| ICCID | punct_after | yes | 435 | 0.000 | 0.000 | 0.000 |
| IPV4_ADDRESS | punct_after | yes | 481 | 0.000 | 0.000 | 0.000 |
| IPV6_ADDRESS | punct_after | yes | 803 | 0.000 | 0.000 | 0.000 |
| MAC_ADDRESS | punct_after | yes | 831 | 0.000 | 0.000 | 0.000 |
| PAYMENT_CARD_NUMBER | punct_after | yes | 505 | 0.000 | 0.000 | 0.000 |
| PRIVATE_KEY | punct_after | yes | 138 | 0.000 | 0.000 | 0.000 |
| STREET | declared_suffix | folded | 43 | 0.000 | 0.000 | 0.000 |
| STREET | declared_suffix | noisy | 20 | 0.000 | 0.000 | 0.000 |
| STREET | declared_suffix | plain | 389 | 0.000 | 0.000 | 0.000 |
| STREET | punct_after | yes | 689 | 0.000 | 0.000 | 0.000 |
| STREET | short_doc | yes | 85 | 0.000 | 0.000 | 0.000 |
| STREET | suffixed | apostrophe | 3 | 0.000 | 0.000 | 0.000 |
| STREET | suffixed | case | 1 | 0.000 | 0.000 | 0.000 |
| STREET | suffixed | no | 2127 | 0.000 | 0.000 | 0.000 |
| SURNAME | declared_suffix | apostrophe | 112 | 0.000 | 0.000 | 0.000 |
| SURNAME | declared_suffix | folded | 168 | 0.000 | 0.000 | 0.000 |
| SURNAME | declared_suffix | noisy | 153 | 0.000 | 0.000 | 0.000 |
| SURNAME | declared_suffix | plain | 2218 | 0.000 | 0.000 | 0.000 |
| SURNAME | punct_after | yes | 877 | 0.000 | 0.000 | 0.000 |
| SURNAME | short_doc | yes | 473 | 0.000 | 0.000 | 0.000 |
| SURNAME | suffixed | apostrophe | 112 | 0.000 | 0.000 | 0.000 |
| SURNAME | suffixed | case | 261 | 0.000 | 0.000 | 0.000 |
| SURNAME | suffixed | no | 4245 | 0.000 | 0.000 | 0.000 |
| TELEPHONENUM | punct_after | yes | 515 | 0.000 | 0.000 | 0.000 |
| TIME | punct_after | yes | 483 | 0.000 | 0.000 | 0.000 |
| URL | punct_after | yes | 162 | 0.000 | 0.000 | 0.000 |
| ZIPCODE | punct_after | yes | 484 | 0.000 | 0.000 | 0.000 |

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
