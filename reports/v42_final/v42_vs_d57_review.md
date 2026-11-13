# D-57: the v4.2 build against the fixed build

v4.2: `t_base.jsonl`, 30,000 documents; new: `t_rev.jsonl`, 37,000 documents.

## The fix-list items (per 25,000 documents)

| Item | Row | v4.2 | new |
|---|---|---|---|
| M1 PII-free near misses | PII-free: near-miss date look-alikes | 18 | 264 |
| M1 PII-free near misses | PII-free: short IBAN-like codes (AZ99AAAA + digits, < 28) | 42 | 136 |
| M1 PII-free near misses | PII-free: ... of them exactly 18 characters | 5 | 38 |
| M1 PII-free near misses | PII-free: bare AZ | 12 | 57 |
| M1 PII-free near misses | PII-free: three-letter licence shapes AAA999999 | 154 | 232 |
| M1 PII-free near misses | PII-free: near-miss times (hour 24-29, minute 60-69) | 128 | 198 |
| M1 PII-free near misses | PII-free: ... of all the above, in `Label: value` lines or tables | 147 | 470 |
| M2 PII-free documents | PII-free documents (targeted) | 2117 | 2532 |
| M2 PII-free documents | PII-free documents with a table | 167 | 307 |
| M3 FIN | FIN look-alikes dashed after the 2nd or 4th character | 0 | 172 |
| M3 FIN | FIN look-alikes dashed 3-3 | 156 | 151 |
| M3 FIN | FIN look-alikes right before the word FİN | 0 | 145 |
| M3 FIN | real FINs right before the word FİN | 0 | 145 |
| M4 dates before their noun | Feb 30/31 and month 13-19 look-alikes before `tarix…` | 18 | 255 |
| M4 dates before their noun | real dates before `tarix…` | 123 | 303 |
| M5 CVV | 5-digit CVV look-alikes at a line end after `CVV kodu:` | 17 | 191 |
| M5 CVV | 2-digit CVV look-alikes | 29 | 226 |
| M5 CVV | ... in PII-free documents | 8 | 80 |
| M6 IPv6 | IPv6 look-alikes with `::` | 150 | 422 |
| M6 IPv6 | ... in PII-free documents | 79 | 186 |
| M6 IPv6 | real compressed IPv6 (`::`) | 1026 | 1392 |
| M6 IPv6 | ... mid-sentence | 617 | 778 |
| M6 IPv6 | ... after a label | 10 | 211 |
| M7 small A5 groups | 9-digit VÖEN look-alikes | 18 | 272 |
| M7 small A5 groups | ... in PII-free documents | 2 | 91 |
| M7 small A5 groups | letters-only MAC look-alikes (AA:BB:...) | 0 | 100 |
| M7 small A5 groups | 3-part IPv4 look-alikes | 112 | 122 |
| M7 small A5 groups | ... ending in one digit (`99.99.9`) | 9 | 57 |
| S1 ages | real 2-digit ages after a lowercase word | 90 | 604 |
| S1 ages | ... without `yaş` right after | 20 | 549 |
| S1 ages | age-shaped look-alikes (2-digit numbers declared as non-ages) | 0 | 316 |
| S2 ALL-CAPS | ALL-CAPS cities | 0 | 296 |
| S2 ALL-CAPS | ALL-CAPS given names and surnames | 0 | 388 |
| S2 ALL-CAPS | ALL-CAPS heading words declared as controls | 135 | 257 |
| S3 brackets and quotes | cities, names and streets right after an opening bracket or quote | 278 | 610 |
| S3 brackets and quotes | ... of them cities | 45 | 383 |
| S3 brackets and quotes | quoted organisation/brand names built from a town word (unlabelled) | 0 | 336 |
| S4 building numbers | real building numbers after a lowercase word | 1452 | 1203 |
| S4 building numbers | ... after a street-type word | 0 | 416 |
| S4 building numbers | ... after a label (`Bina: 12`) | 58 | 302 |
| S5 thinned labels | ACCESS_TOKEN in prose | 430 | 548 |
| S5 thinned labels | ACCESS_TOKEN in table cells | 248 | 400 |
| S5 thinned labels | CVV after a label | 232 | 514 |
| S5 thinned labels | CVV mid-sentence | 579 | 625 |
| S5 thinned labels | cards after a label | 238 | 344 |
| S5 thinned labels | cards mid-sentence | 335 | 359 |
| S5 thinned labels | VÖEN after a label | 37 | 194 |
| S5 thinned labels | VÖEN mid-sentence | 395 | 357 |
| S5 thinned labels | passports after a label | 18 | 169 |
| S5 thinned labels | passports mid-sentence | 209 | 211 |
| S5 thinned labels | seconds-times closing a range | 134 | 218 |
| S6 recall guards | real 29 February in a leap year | 0 | 113 |
| S6 recall guards | 29 February look-alikes in a non-leap year | 176 | 147 |
| S6 recall guards | real dates on the 31st | 0 | 257 |
| S6 recall guards | day-31 look-alikes | 1331 | 1490 |
| S6 recall guards | real times in `saat X radələrində` | 65 | 130 |
| S6 recall guards | time look-alikes in `saat X radələrində` | 118 | 89 |
| S6 recall guards | real times 23:5x | 13 | 84 |
| S6 recall guards | real times 00:0x | 8 | 86 |
| S6 recall guards | real `24:00` (labelled) | 0 | 67 |
| S6 recall guards | `24:00` as a look-alike (must be 0) | 0 | 0 |
| S7 floors | contrast ipv6_mac documents | 592 | 640 |
| S7 floors | contrast licence_id documents | 592 | 640 |
| S7 floors | postal documents | 417 | 447 |

## PII-free documents

| | v4.2 | new |
|---|---|---|
| documents | 2540.0 | 3748.0 |
| median characters | 240.0 | 284.5 |
| numbers per document | 5.4 | 6.2 |

## Real values per label and context (absolute counts)

| Label | Context | v4.2 | new | change |
|---|---|---|---|---|
| ACCESS_TOKEN | prose | 516 | 811 | +57.2% |
| ACCESS_TOKEN | table | 297 | 592 | +99.3% |
| AGE | after a label | 293 | 376 | +28.3% |
| AGE | prose | 207 | 1056 | +410.1% |
| AGE | table | 88 | 116 | +31.8% |
| API_KEY | after a label | 1 | 6 | +500.0% |
| API_KEY | prose | 489 | 631 | +29.0% |
| API_KEY | table | 716 | 830 | +15.9% |
| AZ_DRIVER_LICENSE_NUMBER | after a label | 662 | 880 | +32.9% |
| AZ_DRIVER_LICENSE_NUMBER | prose | 1078 | 1370 | +27.1% |
| AZ_DRIVER_LICENSE_NUMBER | table | 3630 | 4273 | +17.7% |
| AZ_FIN | after a label | 321 | 401 | +24.9% |
| AZ_FIN | line start | 16 | 33 | +106.2% |
| AZ_FIN | prose | 180 | 364 | +102.2% |
| AZ_FIN | table | 593 | 732 | +23.4% |
| AZ_ID_CARD_NUMBER | after a label | 615 | 818 | +33.0% |
| AZ_ID_CARD_NUMBER | line start | 16 | 42 | +162.5% |
| AZ_ID_CARD_NUMBER | prose | 1144 | 1485 | +29.8% |
| AZ_ID_CARD_NUMBER | table | 4529 | 5444 | +20.2% |
| AZ_PASSPORT_NUMBER | after a label | 22 | 250 | +1036.4% |
| AZ_PASSPORT_NUMBER | prose | 251 | 312 | +24.3% |
| AZ_PASSPORT_NUMBER | table | 725 | 937 | +29.2% |
| AZ_VOEN | after a label | 44 | 287 | +552.3% |
| AZ_VOEN | line start | 18 | 20 | +11.1% |
| AZ_VOEN | prose | 474 | 528 | +11.4% |
| AZ_VOEN | table | 725 | 906 | +25.0% |
| BUILDINGNUM | after a label | 0 | 353 | new |
| BUILDINGNUM | prose | 1762 | 1877 | +6.5% |
| BUILDINGNUM | table | 110 | 138 | +25.5% |
| CARD_SECURITY_CODE | after a label | 278 | 761 | +173.7% |
| CARD_SECURITY_CODE | prose | 695 | 925 | +33.1% |
| CARD_SECURITY_CODE | table | 585 | 702 | +20.0% |
| CITY | after a label | 47 | 94 | +100.0% |
| CITY | line start | 328 | 380 | +15.9% |
| CITY | prose | 2613 | 3546 | +35.7% |
| CITY | table | 771 | 1313 | +70.3% |
| DATE | after a label | 600 | 772 | +28.7% |
| DATE | prose | 262 | 621 | +137.0% |
| DATE | table | 1271 | 1508 | +18.6% |
| EMAIL | after a label | 253 | 299 | +18.2% |
| EMAIL | prose | 113 | 158 | +39.8% |
| EMAIL | table | 1199 | 1441 | +20.2% |
| GIVENNAME | after a label | 1 | 4 | +300.0% |
| GIVENNAME | line start | 1908 | 2265 | +18.7% |
| GIVENNAME | prose | 6065 | 6683 | +10.2% |
| GIVENNAME | table | 837 | 1438 | +71.8% |
| IBAN | after a label | 287 | 382 | +33.1% |
| IBAN | line start | 32 | 63 | +96.9% |
| IBAN | prose | 309 | 356 | +15.2% |
| IBAN | table | 600 | 726 | +21.0% |
| ICCID | after a label | 291 | 328 | +12.7% |
| ICCID | prose | 49 | 70 | +42.9% |
| ICCID | table | 589 | 770 | +30.7% |
| IPV4_ADDRESS | after a label | 46 | 64 | +39.1% |
| IPV4_ADDRESS | prose | 886 | 1041 | +17.5% |
| IPV4_ADDRESS | table | 693 | 879 | +26.8% |
| IPV6_ADDRESS | after a label | 20 | 315 | +1475.0% |
| IPV6_ADDRESS | prose | 1020 | 1541 | +51.1% |
| IPV6_ADDRESS | table | 708 | 941 | +32.9% |
| MAC_ADDRESS | after a label | 8 | 19 | +137.5% |
| MAC_ADDRESS | prose | 901 | 1134 | +25.9% |
| MAC_ADDRESS | table | 694 | 930 | +34.0% |
| PAYMENT_CARD_NUMBER | after a label | 285 | 509 | +78.6% |
| PAYMENT_CARD_NUMBER | line start | 23 | 55 | +139.1% |
| PAYMENT_CARD_NUMBER | prose | 402 | 532 | +32.3% |
| PAYMENT_CARD_NUMBER | table | 715 | 812 | +13.6% |
| PRIVATE_KEY | after a label | 44 | 53 | +20.5% |
| PRIVATE_KEY | line start | 627 | 698 | +11.3% |
| PRIVATE_KEY | prose | 452 | 498 | +10.2% |
| STREET | after a label | 5 | 326 | +6420.0% |
| STREET | line start | 112 | 163 | +45.5% |
| STREET | prose | 859 | 1337 | +55.6% |
| STREET | table | 770 | 815 | +5.8% |
| SURNAME | after a label | 32 | 43 | +34.4% |
| SURNAME | line start | 1064 | 1107 | +4.0% |
| SURNAME | prose | 5104 | 5943 | +16.4% |
| SURNAME | table | 951 | 1253 | +31.8% |
| TELEPHONENUM | prose | 150 | 182 | +21.3% |
| TELEPHONENUM | table | 2482 | 2976 | +19.9% |
| TIME | after a label | 691 | 789 | +14.2% |
| TIME | line start | 231 | 339 | +46.8% |
| TIME | prose | 1215 | 1963 | +61.6% |
| TIME | table | 569 | 837 | +47.1% |
| URL | prose | 21 | 31 | +47.6% |
| URL | table | 327 | 388 | +18.7% |
| ZIPCODE | after a label | 421 | 561 | +33.3% |
| ZIPCODE | prose | 1198 | 1435 | +19.8% |
| ZIPCODE | table | 630 | 737 | +17.0% |

## Real values per label (absolute counts)

| Label | v4.2 | new | change |
|---|---|---|---|
| ACCESS_TOKEN | 813 | 1403 | +72.6% |
| AGE | 588 | 1548 | +163.3% |
| API_KEY | 1206 | 1467 | +21.6% |
| AZ_DRIVER_LICENSE_NUMBER | 5370 | 6523 | +21.5% |
| AZ_FIN | 1110 | 1530 | +37.8% |
| AZ_ID_CARD_NUMBER | 6304 | 7789 | +23.6% |
| AZ_PASSPORT_NUMBER | 998 | 1499 | +50.2% |
| AZ_VOEN | 1261 | 1741 | +38.1% |
| BUILDINGNUM | 1872 | 2368 | +26.5% |
| CARD_SECURITY_CODE | 1558 | 2388 | +53.3% |
| CITY | 3759 | 5333 | +41.9% |
| DATE | 2133 | 2901 | +36.0% |
| EMAIL | 1565 | 1898 | +21.3% |
| GIVENNAME | 8811 | 10390 | +17.9% |
| IBAN | 1228 | 1527 | +24.3% |
| ICCID | 929 | 1168 | +25.7% |
| IPV4_ADDRESS | 1625 | 1984 | +22.1% |
| IPV6_ADDRESS | 1748 | 2797 | +60.0% |
| MAC_ADDRESS | 1603 | 2083 | +29.9% |
| PAYMENT_CARD_NUMBER | 1425 | 1908 | +33.9% |
| PRIVATE_KEY | 1123 | 1249 | +11.2% |
| STREET | 1746 | 2641 | +51.3% |
| SURNAME | 7151 | 8346 | +16.7% |
| TELEPHONENUM | 2632 | 3158 | +20.0% |
| TIME | 2706 | 3928 | +45.2% |
| URL | 348 | 419 | +20.4% |
| ZIPCODE | 2249 | 2733 | +21.5% |

**Label x context cells that went down: 0**
