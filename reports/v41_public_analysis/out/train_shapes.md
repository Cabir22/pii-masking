# Shapes in the training data: v3 against v4

Sources: targeted builder; LLM batches b1-b6; old corpus (`_old`).

| documents | v3 | v4 |
|---|---|---|
| targeted | 20,013 | 19,957 |
| LLM b1 | 3,921 | 3,801 |
| LLM b2 | 4,375 | 4,268 |
| LLM b3 | 4,535 | 4,329 |
| LLM b4 | 4,555 | 4,354 |
| LLM b5 | 16,269 | 15,626 |
| LLM b6 | 18,267 | 17,485 |
| old corpus | 72,151 | 63,069 |

## 1. Labelled values

| | v3 targeted | v4 targeted | v3 LLM | v4 LLM | v3 old | v4 old | v3 all | v4 all |
|---|---|---|---|---|---|---|---|---|
| AZ_DRIVER_LICENSE_NUMBER | 2,668 | 2,816 | 3,365 | 3,316 | 2,771 | 2,400 | 8,804 | 8,532 |
| AZ_ID_CARD_NUMBER | 3,037 | 3,425 | 3,981 | 3,921 | 3,758 | 3,235 | 10,776 | 10,581 |
| CARD_SECURITY_CODE | 857 | 1,174 | 2,261 | 2,195 | 2,721 | 2,329 | 5,839 | 5,698 |
| DATE | 1,331 | 1,245 | 28,062 | 27,207 | 45,974 | 39,549 | 75,367 | 68,001 |
| EMAIL | 1,256 | 1,102 | 16,878 | 16,336 | 27,060 | 23,517 | 45,194 | 40,955 |
| IPV4_ADDRESS | 717 | 749 | 3,155 | 3,061 | 4,517 | 3,823 | 8,389 | 7,633 |
| IPV6_ADDRESS | 1,155 | 769 | 2,680 | 2,667 | 1,780 | 1,553 | 5,615 | 4,989 |
| MAC_ADDRESS | 1,152 | 901 | 2,859 | 2,821 | 2,299 | 1,960 | 6,310 | 5,682 |
| TIME | 657 | 1,332 | 4,551 | 4,220 | 6,246 | 5,584 | 11,454 | 11,136 |
| ZIPCODE | 1,434 | 1,253 | 5,274 | 5,179 | 8,159 | 7,049 | 14,867 | 13,481 |

### By shape

| | v3 targeted | v4 targeted | v3 LLM | v4 LLM | v3 old | v4 old | v3 all | v4 all |
|---|---|---|---|---|---|---|---|---|
| AZ_DRIVER_LICENSE_NUMBER · `aa999999` | 2,668 | 2,816 | 3,365 | 3,316 | 2,771 | 2,400 | 8,804 | 8,532 |
| AZ_ID_CARD_NUMBER · `aa9999999` | 1,767 | 3,154 | 2,658 | 2,616 | 1,928 | 1,681 | 6,353 | 7,451 |
| AZ_ID_CARD_NUMBER · `aaa9999999` | 1,270 | 271 | 1,323 | 1,305 | 1,830 | 1,554 | 4,423 | 3,130 |
| CARD_SECURITY_CODE · `999` | 623 | 863 | 1,783 | 1,750 | 2,325 | 2,012 | 4,731 | 4,625 |
| CARD_SECURITY_CODE · `9999` | 129 | 178 | 292 | 283 | 395 | 316 | 816 | 777 |
| CARD_SECURITY_CODE · `99-9` | 57 | 86 | 114 | 93 | 0 | 0 | 171 | 179 |
| CARD_SECURITY_CODE · `9-99` | 22 | 27 | 69 | 67 | 0 | 0 | 91 | 94 |
| CARD_SECURITY_CODE · `99-99` | 26 | 20 | 0 | 0 | 0 | 0 | 26 | 20 |
| DATE · `99.99.9999` | 457 | 431 | 13,190 | 12,787 | 23,598 | 20,331 | 37,245 | 33,549 |
| DATE · `9999-99-99` | 430 | 401 | 3,436 | 3,365 | 4,995 | 4,275 | 8,861 | 8,041 |
| DATE · `99 aaaaaa 9999` | 135 | 123 | 2,321 | 2,395 | 3,296 | 3,028 | 5,752 | 5,546 |
| DATE · `99 aaaa 9999` | 77 | 63 | 1,163 | 1,220 | 3,793 | 3,395 | 5,033 | 4,678 |
| DATE · `99 aaa 9999` | 21 | 25 | 1,056 | 991 | 3,029 | 2,604 | 4,106 | 3,620 |
| DATE · `99/99/9999` | 0 | 0 | 1,967 | 1,940 | 1,073 | 914 | 3,040 | 2,854 |
| DATE · `99 aaaaaaa 9999` | 21 | 33 | 612 | 652 | 1,456 | 1,279 | 2,089 | 1,964 |
| DATE · `99 aaaaaaaa 9999` | 27 | 25 | 428 | 418 | 1,059 | 944 | 1,514 | 1,387 |
| DATE · `99.99.99` | 0 | 0 | 516 | 502 | 747 | 648 | 1,263 | 1,150 |
| DATE · `99.9.9999` | 0 | 0 | 410 | 409 | 676 | 595 | 1,086 | 1,004 |
| DATE · `9 aaaaaa 9999` | 54 | 46 | 549 | 584 | 262 | 301 | 865 | 931 |
| DATE · `99 aaaaa 9999` | 36 | 33 | 258 | 246 | 387 | 374 | 681 | 653 |
| DATE · `9 aaaa 9999` | 41 | 25 | 329 | 354 | 167 | 191 | 537 | 570 |
| DATE · `9.9.9999` | 0 | 0 | 144 | 143 | 267 | 218 | 411 | 361 |
| DATE · `9 aaa 9999` | 10 | 8 | 139 | 136 | 45 | 57 | 194 | 201 |
| DATE · `99 aaaaaa 9999-aa aa` | 0 | 0 | 149 | 0 | 235 | 0 | 384 | 0 |
| DATE · `9 aaaaa 9999` | 7 | 11 | 121 | 125 | 51 | 68 | 179 | 204 |
| DATE · `9 aaaaaaa 9999` | 6 | 11 | 106 | 121 | 46 | 58 | 158 | 190 |
| DATE · `9 aaaaaaaa 9999` | 9 | 10 | 102 | 130 | 36 | 57 | 147 | 197 |
| DATE · `9.99.9999` | 0 | 0 | 69 | 60 | 106 | 92 | 175 | 152 |
| DATE · `99 aaaa 9999-aa aa` | 0 | 0 | 107 | 0 | 138 | 0 | 245 | 0 |
| DATE · `9 aaaaaa 9999-aa aa` | 0 | 0 | 55 | 0 | 90 | 0 | 145 | 0 |
| DATE · `9 aaaa 9999-aa aa` | 0 | 0 | 35 | 0 | 45 | 0 | 80 | 0 |
| DATE · `99 aaaaaaaa 9999-aa aa` | 0 | 0 | 21 | 0 | 45 | 0 | 66 | 0 |
| DATE · `99 aaa 9999-aa aa` | 0 | 0 | 23 | 0 | 41 | 0 | 64 | 0 |
| DATE · `99 aaaaaaa 9999-aa aa` | 0 | 0 | 35 | 0 | 28 | 0 | 63 | 0 |
| DATE · `99 aaaaa 9999-aa aa` | 0 | 0 | 27 | 0 | 35 | 0 | 62 | 0 |
| DATE · `9 aaaaaaaa 9999-aa aa` | 0 | 0 | 20 | 0 | 24 | 0 | 44 | 0 |
| DATE · `9 aaaaa 9999-aa aa` | 0 | 0 | 13 | 0 | 26 | 0 | 39 | 0 |
| DATE · `aaaaa, 99 aaaaaa 9999` | 0 | 0 | 17 | 18 | 0 | 0 | 17 | 18 |
| DATE · `99 aaaaaa 9999, aaaaa` | 0 | 0 | 16 | 15 | 0 | 0 | 16 | 15 |
| DATE · `99-99-9999` | 0 | 0 | 8 | 6 | 10 | 6 | 18 | 12 |
| DATE · `aaaa, 99 aaaaaa 9999` | 0 | 0 | 13 | 16 | 0 | 0 | 13 | 16 |
| DATE · `aaaaa, 99 aaaa 9999` | 0 | 0 | 14 | 15 | 0 | 0 | 14 | 15 |
| DATE · `99 aaaaaa 9999, aaaaa aaaaaa` | 0 | 0 | 14 | 14 | 0 | 0 | 14 | 14 |
| DATE · `9 aaaaaaa 9999-aa aa` | 0 | 0 | 11 | 0 | 16 | 0 | 27 | 0 |
| DATE · `99 aaaaaa 9999, aaaaaaaa aaaaaa` | 0 | 0 | 13 | 14 | 0 | 0 | 13 | 14 |
| DATE · `aaaa, 99 aaaa 9999` | 0 | 0 | 15 | 12 | 0 | 0 | 15 | 12 |
| DATE · `aaaaaaaa, 99 aaaaaa 9999` | 0 | 0 | 11 | 16 | 0 | 0 | 11 | 16 |
| DATE · `9 aaa 9999-aa aa` | 0 | 0 | 8 | 0 | 17 | 0 | 25 | 0 |
| DATE · `99 aaaaaa 9999, aaaa` | 0 | 0 | 12 | 13 | 0 | 0 | 12 | 13 |
| DATE · `aaaaa, 9 aaaaaa 9999` | 0 | 0 | 13 | 12 | 0 | 0 | 13 | 12 |
| DATE · `99 aaaa 9999, aaaaa` | 0 | 0 | 13 | 11 | 0 | 0 | 13 | 11 |
| DATE · `aaaaa aaaaaa, 99 aaaaaa 9999` | 0 | 0 | 13 | 10 | 0 | 0 | 13 | 10 |
| DATE · `aaaaaaaa aaaaaa, 99 aaaaaa 9999` | 0 | 0 | 11 | 11 | 0 | 0 | 11 | 11 |
| DATE · `9 aaaaaa 9999, aaaaa` | 0 | 0 | 9 | 10 | 0 | 0 | 9 | 10 |
| DATE · `aaaa aaaaaa, 99 aaaaaa 9999` | 0 | 0 | 9 | 9 | 0 | 0 | 9 | 9 |
| DATE · `9 aaaaaa 9999, aaaa aaaaaa` | 0 | 0 | 8 | 9 | 0 | 0 | 8 | 9 |
| DATE · `99  aaaa 9999` | 0 | 0 | 2 | 2 | 7 | 6 | 9 | 8 |
| DATE · `9 aaaa 9999, aaaaa aaaaaa` | 0 | 0 | 7 | 8 | 0 | 0 | 7 | 8 |
| DATE · `aaaaa, 99 aaaaaaa 9999` | 0 | 0 | 9 | 6 | 0 | 0 | 9 | 6 |
| DATE · `9999/99/99` | 0 | 0 | 1 | 2 | 6 | 5 | 7 | 7 |
| DATE · `aaaa, 99 aaa 9999` | 0 | 0 | 7 | 7 | 0 | 0 | 7 | 7 |
| DATE · `aaaaa aaaaaa, 99 aaaa 9999` | 0 | 0 | 8 | 6 | 0 | 0 | 8 | 6 |
| DATE · `99  aaaaaa 9999` | 0 | 0 | 2 | 0 | 6 | 5 | 8 | 5 |
| DATE · `99 aaaa 9999, aaaaaaaa` | 0 | 0 | 6 | 7 | 0 | 0 | 6 | 7 |
| DATE · `aaaa aaaaaa, 9 aaaaaa 9999` | 0 | 0 | 6 | 7 | 0 | 0 | 6 | 7 |
| DATE · `aaaa aaaaaa, 99 aaaa 9999` | 0 | 0 | 5 | 8 | 0 | 0 | 5 | 8 |
| DATE · `aaaaaaaa aaaaaa, 9 aaaaaa 9999` | 0 | 0 | 5 | 8 | 0 | 0 | 5 | 8 |
| DATE · `9 aaaaaa 9999, aaaaa aaaaaa` | 0 | 0 | 5 | 7 | 0 | 0 | 5 | 7 |
| DATE · `99  aaa 9999` | 0 | 0 | 2 | 2 | 4 | 4 | 6 | 6 |
| DATE · `99 aaaa 9999, aaaa aaaaaa` | 0 | 0 | 7 | 5 | 0 | 0 | 7 | 5 |
| DATE · `aaaaaaaa aaaaaa, 99 aaaa 9999` | 0 | 0 | 7 | 5 | 0 | 0 | 7 | 5 |
| DATE · `99	aaaaaa 9999` | 0 | 0 | 2 | 1 | 4 | 4 | 6 | 5 |
| DATE · `99 aaaa 9999, aaaaaaaa aaaaaa` | 0 | 0 | 7 | 4 | 0 | 0 | 7 | 4 |
| DATE · `99 aaaaa 9999, aaaaa` | 0 | 0 | 5 | 6 | 0 | 0 | 5 | 6 |
| DATE · `99 aaaaaa 9999, aaaa aaaaaa` | 0 | 0 | 5 | 6 | 0 | 0 | 5 | 6 |
| DATE · `99 aaaaaa	9999` | 0 | 0 | 4 | 4 | 1 | 1 | 5 | 5 |
| DATE · `99 aaaaaa  9999` | 0 | 0 | 1 | 1 | 4 | 4 | 5 | 5 |
| DATE · `99 aaaaaa 9999, aaaaaaaa` | 0 | 0 | 5 | 5 | 0 | 0 | 5 | 5 |
| DATE · `99.99.999` | 0 | 0 | 5 | 5 | 0 | 0 | 5 | 5 |
| DATE · `aaaaa, 9 aaaa 9999` | 0 | 0 | 5 | 5 | 0 | 0 | 5 | 5 |
| DATE · `aaaaa, 99 aaaaa 9999` | 0 | 0 | 6 | 4 | 0 | 0 | 6 | 4 |
| DATE · `aaaaaaaa, 9 aaaaaa 9999` | 0 | 0 | 5 | 5 | 0 | 0 | 5 | 5 |
| DATE · `9 aaaa 9999, aaaa aaaaaa` | 0 | 0 | 4 | 5 | 0 | 0 | 4 | 5 |
| DATE · `9 aaaa 9999, aaaaaaaa aaaaaa` | 0 | 0 | 4 | 5 | 0 | 0 | 4 | 5 |
| DATE · `99 aaaa 9999, aaaaa aaaaaa` | 0 | 0 | 5 | 4 | 0 | 0 | 5 | 4 |
| DATE · `99 aaaaaaaa 9999, aaaaa` | 0 | 0 | 5 | 4 | 0 | 0 | 5 | 4 |
| DATE · `9999-99–99` | 0 | 0 | 1 | 3 | 3 | 2 | 4 | 5 |
| DATE · `aaaaa aaaaaa, 9 aaaa 9999` | 0 | 0 | 5 | 4 | 0 | 0 | 5 | 4 |
| DATE · `9 aaaaaaa 9999, aaaaa` | 0 | 0 | 4 | 4 | 0 | 0 | 4 | 4 |
| DATE · `9 aaaaaaaa 9999, aaaaaaaa` | 0 | 0 | 4 | 4 | 0 | 0 | 4 | 4 |
| DATE · `99 aaa  9999` | 0 | 0 | 1 | 1 | 3 | 3 | 4 | 4 |
| DATE · `99 aaaaaa, 9999` | 0 | 0 | 3 | 4 | 1 | 0 | 4 | 4 |
| DATE · `99 aaaaaaa 9999, aaaaa` | 0 | 0 | 3 | 5 | 0 | 0 | 3 | 5 |
| DATE · `99 aaaa 9999` | 0 | 0 | 4 | 4 | 0 | 0 | 4 | 4 |
| DATE · `99 aaa 9999` | 0 | 0 | 1 | 2 | 3 | 2 | 4 | 4 |
| DATE · `99.99.a999` | 0 | 0 | 4 | 2 | 1 | 1 | 5 | 3 |
| DATE · `9999–99-99` | 0 | 0 | 4 | 4 | 0 | 0 | 4 | 4 |
| DATE · `99 aaa 9999` | 0 | 0 | 0 | 0 | 4 | 4 | 4 | 4 |
| DATE · `99 aaaa 9999` | 0 | 0 | 0 | 0 | 4 | 4 | 4 | 4 |
| DATE · `aaaaa aaaaaa, 9 aaaaaa 9999` | 0 | 0 | 4 | 4 | 0 | 0 | 4 | 4 |
| DATE · `aaaaaaaa aaaaaa, 99 aaaaa 9999` | 0 | 0 | 4 | 4 | 0 | 0 | 4 | 4 |
| DATE · `aaaaaaaa, 9 aaaa 9999` | 0 | 0 | 4 | 4 | 0 | 0 | 4 | 4 |
| DATE · `9 aaaa 9999, aaaaa` | 0 | 0 | 4 | 3 | 0 | 0 | 4 | 3 |
| DATE · `9 aaaaaa 9999, aaaaaaaa` | 0 | 0 | 4 | 3 | 0 | 0 | 4 | 3 |
| DATE · `99 aaaaaaa 9999, aaaaaaaa` | 0 | 0 | 3 | 4 | 0 | 0 | 3 | 4 |
| DATE · `99 aaaaaaaa 9999, aaaaaaaa` | 0 | 0 | 3 | 4 | 0 | 0 | 3 | 4 |
| DATE · `aaaaa, 99 aaa 9999` | 0 | 0 | 4 | 3 | 0 | 0 | 4 | 3 |
| DATE · `aaaaaaaa, 99 aaaa 9999` | 0 | 0 | 3 | 4 | 0 | 0 | 3 | 4 |
| DATE · `9 aaaaaa 9999, aaaaaaaa aaaaaa` | 0 | 0 | 3 | 3 | 0 | 0 | 3 | 3 |
| DATE · `9/999/9999` | 0 | 0 | 1 | 1 | 2 | 2 | 3 | 3 |
| DATE · `99   aaaaaa 9999` | 0 | 0 | 0 | 1 | 2 | 3 | 2 | 4 |
| DATE · `99 aaaa	9999` | 0 | 0 | 1 | 1 | 2 | 2 | 3 | 3 |
| DATE · `99 aaaa  9999` | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 3 |
| DATE · `99 aaaa 9999, aaaa` | 0 | 0 | 3 | 3 | 0 | 0 | 3 | 3 |
| DATE · `99 aaaaa 9999, aaaa` | 0 | 0 | 3 | 3 | 0 | 0 | 3 | 3 |
| DATE · `99 aaaaa 9999, aaaaaaaa aaaaaa` | 0 | 0 | 3 | 3 | 0 | 0 | 3 | 3 |
| DATE · `99 aaaaaaa 9999, aaaaa aaaaaa` | 0 | 0 | 4 | 2 | 0 | 0 | 4 | 2 |
| DATE · `99.9a.9999` | 0 | 0 | 3 | 3 | 0 | 0 | 3 | 3 |
| DATE · `99.a9.9999` | 0 | 0 | 2 | 2 | 1 | 1 | 3 | 3 |
| DATE · `99/99/9a99` | 0 | 0 | 3 | 3 | 0 | 0 | 3 | 3 |
| DATE · `aaaaa aaaaaa, 99 aaaaaaa 9999` | 0 | 0 | 4 | 2 | 0 | 0 | 4 | 2 |
| DATE · `aaaaa, 99 aaaaaaaa 9999` | 0 | 0 | 3 | 3 | 0 | 0 | 3 | 3 |
| DATE · `aaaaaaaa aaaaaa, 9 aaaaaaa 9999` | 0 | 0 | 3 | 3 | 0 | 0 | 3 | 3 |
| DATE · `aaaaaaaa, 99 aaaaaaa 9999` | 0 | 0 | 2 | 4 | 0 | 0 | 2 | 4 |
| DATE · `9 aaa 9999, aaaaa` | 0 | 0 | 4 | 1 | 0 | 0 | 4 | 1 |
| DATE · `9 aaaaa 9999, aaaaaaaa` | 0 | 0 | 1 | 4 | 0 | 0 | 1 | 4 |
| DATE · `99	aaaaaaaa 9999` | 0 | 0 | 1 | 2 | 1 | 1 | 2 | 3 |
| DATE · `99 aaa 9999, aaaaa` | 0 | 0 | 3 | 2 | 0 | 0 | 3 | 2 |
| DATE · `99 aaaaaa   9999` | 0 | 0 | 0 | 0 | 2 | 3 | 2 | 3 |
| DATE · `99 aaaaaaaa 9999, aaaa` | 0 | 0 | 3 | 2 | 0 | 0 | 3 | 2 |
| DATE · `99 aaaaaaaa 9999, aaaaaaaa aaaaaa` | 0 | 0 | 2 | 3 | 0 | 0 | 2 | 3 |
| DATE · `99 aaaaaa 9999` | 0 | 0 | 3 | 2 | 0 | 0 | 3 | 2 |
| DATE · `99.9.99999` | 0 | 0 | 1 | 2 | 1 | 1 | 2 | 3 |
| DATE · `99.99.999a` | 0 | 0 | 1 | 0 | 2 | 2 | 3 | 2 |
| DATE · `99.999.999` | 0 | 0 | 1 | 1 | 2 | 1 | 3 | 2 |
| DATE · `999.9.9999` | 0 | 0 | 1 | 0 | 2 | 2 | 3 | 2 |
| DATE · `99 aaaaaa 9999` | 0 | 0 | 0 | 0 | 2 | 3 | 2 | 3 |
| DATE · `a9.99.9999` | 0 | 0 | 0 | 0 | 3 | 2 | 3 | 2 |
| DATE · `aaaa aaaaaa, 9 aaaaaaaa 9999` | 0 | 0 | 3 | 2 | 0 | 0 | 3 | 2 |
| DATE · `aaaa, 9 aaaaaa 9999` | 0 | 0 | 4 | 1 | 0 | 0 | 4 | 1 |
| EMAIL · `domain dots 1` | 1,256 | 1,102 | 16,878 | 16,336 | 27,060 | 23,517 | 45,194 | 40,955 |
| EMAIL · `local: dot` | 586 | 533 | 8,084 | 7,788 | 12,830 | 11,171 | 21,500 | 19,492 |
| EMAIL · `local: letters only` | 103 | 83 | 2,783 | 2,765 | 4,646 | 4,031 | 7,532 | 6,879 |
| EMAIL · `local: digit` | 198 | 190 | 2,170 | 2,111 | 3,453 | 2,993 | 5,821 | 5,294 |
| EMAIL · `local: dot+digit` | 182 | 138 | 1,691 | 1,584 | 2,679 | 2,330 | 4,552 | 4,052 |
| EMAIL · `local: underscore` | 170 | 141 | 1,483 | 1,442 | 2,421 | 2,093 | 4,074 | 3,676 |
| EMAIL · `local: hyphen` | 17 | 17 | 667 | 646 | 1,031 | 899 | 1,715 | 1,562 |
| EMAIL · `domain hyphen` | 224 | 190 | 567 | 503 | 787 | 685 | 1,578 | 1,378 |
| EMAIL · `upper case` | 0 | 0 | 95 | 97 | 0 | 0 | 95 | 97 |
| IPV4_ADDRESS · `4 parts` | 717 | 749 | 3,155 | 3,061 | 4,517 | 3,823 | 8,389 | 7,633 |
| IPV4_ADDRESS · `no one-digit octet` | 582 | 596 | 2,548 | 2,493 | 3,622 | 3,065 | 6,752 | 6,154 |
| IPV4_ADDRESS · `private` | 204 | 189 | 746 | 722 | 1,063 | 894 | 2,013 | 1,805 |
| IPV4_ADDRESS · `documentation` | 90 | 109 | 418 | 410 | 622 | 537 | 1,130 | 1,056 |
| IPV4_ADDRESS · `1 one-digit octets` | 108 | 102 | 424 | 408 | 621 | 516 | 1,153 | 1,026 |
| IPV4_ADDRESS · `2 one-digit octets` | 27 | 50 | 182 | 158 | 262 | 231 | 471 | 439 |
| IPV4_ADDRESS · `3 one-digit octets` | 0 | 1 | 1 | 2 | 12 | 11 | 13 | 14 |
| IPV6_ADDRESS · `lower` | 891 | 600 | 2,062 | 2,073 | 1,780 | 1,553 | 4,733 | 4,226 |
| IPV6_ADDRESS · `full 8 groups` | 404 | 273 | 476 | 472 | 1,780 | 1,553 | 2,660 | 2,298 |
| IPV6_ADDRESS · `:: middle` | 512 | 342 | 1,543 | 1,509 | 0 | 0 | 2,055 | 1,851 |
| IPV6_ADDRESS · `prefix fd/fc` | 312 | 215 | 667 | 657 | 627 | 550 | 1,606 | 1,422 |
| IPV6_ADDRESS · `other prefix` | 240 | 159 | 437 | 433 | 926 | 795 | 1,603 | 1,387 |
| IPV6_ADDRESS · `prefix 2001:db8` | 363 | 244 | 931 | 950 | 227 | 208 | 1,521 | 1,402 |
| IPV6_ADDRESS · `leading zeros` | 155 | 110 | 202 | 194 | 534 | 472 | 891 | 776 |
| IPV6_ADDRESS · `upper` | 178 | 109 | 419 | 417 | 0 | 0 | 597 | 526 |
| IPV6_ADDRESS · `prefix ::` | 156 | 104 | 421 | 435 | 0 | 0 | 577 | 539 |
| IPV6_ADDRESS · `:: end` | 83 | 50 | 240 | 251 | 0 | 0 | 323 | 301 |
| IPV6_ADDRESS · `:: start` | 79 | 55 | 209 | 223 | 0 | 0 | 288 | 278 |
| IPV6_ADDRESS · `::ffff:` | 77 | 49 | 212 | 212 | 0 | 0 | 289 | 261 |
| IPV6_ADDRESS · `prefix fe80` | 84 | 47 | 224 | 192 | 0 | 0 | 308 | 239 |
| IPV6_ADDRESS · `mixed` | 84 | 58 | 192 | 172 | 0 | 0 | 276 | 230 |
| IPV6_ADDRESS · `digit-only groups` | 2 | 2 | 7 | 5 | 0 | 0 | 9 | 7 |
| IPV6_ADDRESS · `no letters` | 2 | 2 | 7 | 5 | 0 | 0 | 9 | 7 |
| MAC_ADDRESS · `colon` | 666 | 475 | 1,574 | 1,560 | 1,707 | 1,461 | 3,947 | 3,496 |
| MAC_ADDRESS · `upper` | 512 | 414 | 1,300 | 1,296 | 1,483 | 1,282 | 3,295 | 2,992 |
| MAC_ADDRESS · `lower` | 506 | 368 | 1,210 | 1,170 | 816 | 678 | 2,532 | 2,216 |
| MAC_ADDRESS · `dash` | 250 | 259 | 698 | 672 | 592 | 499 | 1,540 | 1,430 |
| MAC_ADDRESS · `dotted` | 236 | 167 | 587 | 589 | 0 | 0 | 823 | 756 |
| MAC_ADDRESS · `mixed` | 134 | 119 | 349 | 355 | 0 | 0 | 483 | 474 |
| TIME · `99:99` | 566 | 660 | 3,932 | 3,572 | 5,414 | 4,834 | 9,912 | 9,066 |
| TIME · `9:99 aa` | 69 | 89 | 451 | 466 | 612 | 515 | 1,132 | 1,070 |
| TIME · `99:99 aa` | 22 | 29 | 162 | 155 | 202 | 166 | 386 | 350 |
| TIME · `99:99:99` | 0 | 554 | 0 | 16 | 0 | 52 | 0 | 622 |
| TIME · `9:99` | 0 | 0 | 1 | 5 | 1 | 3 | 2 | 8 |
| TIME · `99:a9` | 0 | 0 | 1 | 2 | 2 | 1 | 3 | 3 |
| TIME · `a9:99` | 0 | 0 | 1 | 1 | 2 | 2 | 3 | 3 |
| ZIPCODE · `aa9999` | 947 | 838 | 4,904 | 4,803 | 8,159 | 7,049 | 14,010 | 12,690 |
| ZIPCODE · `9999` | 487 | 415 | 370 | 376 | 0 | 0 | 857 | 791 |

## 2. Declared look-alikes (`_decoys`)

| | v3 targeted | v4 targeted | v3 LLM | v4 LLM | v3 old | v4 old | v3 all | v4 all |
|---|---|---|---|---|---|---|---|---|
| AZ_DRIVER_LICENSE_NUMBER · archive_folder | 113 | 83 | 387 | 322 | 0 | 0 | 500 | 405 |
| AZ_DRIVER_LICENSE_NUMBER · campaign_code | 102 | 86 | 364 | 325 | 0 | 0 | 466 | 411 |
| AZ_DRIVER_LICENSE_NUMBER · internal_reference | 406 | 331 | 373 | 338 | 0 | 0 | 779 | 669 |
| AZ_DRIVER_LICENSE_NUMBER · licence_hyphen | 102 | 79 | 389 | 323 | 0 | 0 | 491 | 402 |
| AZ_DRIVER_LICENSE_NUMBER · licence_too_short | 104 | 84 | 380 | 336 | 0 | 0 | 484 | 420 |
| AZ_ID_CARD_NUMBER · ORDER_ID | 0 | 0 | 646 | 572 | 0 | 0 | 646 | 572 |
| AZ_ID_CARD_NUMBER · id_card_hyphen | 107 | 87 | 353 | 317 | 0 | 0 | 460 | 404 |
| AZ_ID_CARD_NUMBER · id_card_short_number | 0 | 78 | 0 | 0 | 0 | 0 | 0 | 78 |
| AZ_ID_CARD_NUMBER · id_card_too_long | 106 | 85 | 382 | 345 | 0 | 0 | 488 | 430 |
| AZ_ID_CARD_NUMBER · id_card_too_short | 105 | 85 | 384 | 320 | 0 | 0 | 489 | 405 |
| CARD_SECURITY_CODE · cvv_1_2_digits | 103 | 81 | 333 | 301 | 0 | 0 | 436 | 382 |
| CARD_SECURITY_CODE · cvv_5_digits | 215 | 231 | 434 | 342 | 0 | 0 | 649 | 573 |
| CARD_SECURITY_CODE · cvv_letters | 109 | 90 | 344 | 281 | 0 | 0 | 453 | 371 |
| CARD_SECURITY_CODE · cvv_separator | 111 | 87 | 189 | 183 | 0 | 0 | 300 | 270 |
| CARD_SECURITY_CODE · cvv_sequential_5 | 239 | 213 | 95 | 70 | 0 | 0 | 334 | 283 |
| CARD_SECURITY_CODE · door_code | 0 | 78 | 0 | 0 | 0 | 0 | 0 | 78 |
| CARD_SECURITY_CODE · policy_sequential | 109 | 81 | 341 | 296 | 0 | 0 | 450 | 377 |
| CARD_SECURITY_CODE · room_code | 0 | 86 | 0 | 0 | 0 | 0 | 0 | 86 |
| DATE · DATE_LIKE_ID | 0 | 0 | 744 | 643 | 0 | 0 | 744 | 643 |
| DATE · TIMESTAMP | 0 | 0 | 619 | 1,010 | 0 | 738 | 619 | 1,748 |
| DATE · date_bad_month | 1,137 | 1,035 | 381 | 351 | 0 | 0 | 1,518 | 1,386 |
| DATE · date_clause_number | 124 | 122 | 382 | 355 | 0 | 0 | 506 | 477 |
| DATE · date_impossible_day | 1,139 | 1,032 | 363 | 333 | 0 | 0 | 1,502 | 1,365 |
| DATE · date_iso_out_of_range | 1,129 | 1,035 | 356 | 318 | 0 | 0 | 1,485 | 1,353 |
| DATE · date_version_string | 127 | 117 | 366 | 333 | 0 | 0 | 493 | 450 |
| EMAIL · EMAIL_LIKE_HANDLE | 0 | 0 | 795 | 736 | 0 | 0 | 795 | 736 |
| EMAIL · MASKED_EMAIL | 0 | 0 | 885 | 771 | 0 | 0 | 885 | 771 |
| EMAIL · OBFUSCATED_EMAIL | 0 | 0 | 813 | 724 | 0 | 0 | 813 | 724 |
| EMAIL · email_dotless_domain | 170 | 145 | 102 | 84 | 0 | 0 | 272 | 229 |
| EMAIL · email_double_at | 186 | 153 | 131 | 104 | 0 | 0 | 317 | 257 |
| EMAIL · email_localhost | 178 | 151 | 106 | 93 | 0 | 0 | 284 | 244 |
| EMAIL · email_no_at | 186 | 146 | 106 | 94 | 0 | 0 | 292 | 240 |
| IPV4_ADDRESS · IP_INVALID_OCTET | 0 | 0 | 754 | 670 | 0 | 0 | 754 | 670 |
| IPV4_ADDRESS · IP_LIKE_VERSION | 0 | 0 | 814 | 758 | 0 | 0 | 814 | 758 |
| IPV4_ADDRESS · ipv4_octet_over_255 | 106 | 84 | 325 | 320 | 0 | 0 | 431 | 404 |
| IPV4_ADDRESS · ipv4_placeholder | 0 | 82 | 0 | 0 | 0 | 0 | 0 | 82 |
| IPV4_ADDRESS · ipv4_short_over_255 | 0 | 85 | 0 | 0 | 0 | 0 | 0 | 85 |
| IPV4_ADDRESS · ipv4_three_octets | 0 | 81 | 0 | 0 | 0 | 0 | 0 | 81 |
| IPV6_ADDRESS · ipv6_non_hex | 98 | 79 | 107 | 91 | 0 | 0 | 205 | 170 |
| IPV6_ADDRESS · ipv6_triple_colon | 107 | 77 | 359 | 328 | 0 | 0 | 466 | 405 |
| IPV6_ADDRESS · ipv6_two_compressions | 98 | 83 | 111 | 96 | 0 | 0 | 209 | 179 |
| MAC_ADDRESS · MAC_LIKE_HASH | 0 | 0 | 877 | 774 | 0 | 0 | 877 | 774 |
| MAC_ADDRESS · mac_3_to_5_groups | 101 | 78 | 336 | 291 | 0 | 0 | 437 | 369 |
| MAC_ADDRESS · mac_fragment_dashed | 0 | 85 | 0 | 0 | 0 | 0 | 0 | 85 |
| TIME · TIMESTAMP | 0 | 0 | 0 | 105 | 0 | 56 | 0 | 161 |
| TIME · policy_version_time | 114 | 134 | 355 | 305 | 0 | 0 | 469 | 439 |
| TIME · time_3_digit_minutes | 133 | 127 | 384 | 335 | 0 | 0 | 517 | 462 |
| TIME · time_bad_hour | 133 | 131 | 342 | 302 | 0 | 0 | 475 | 433 |
| TIME · time_bad_minute | 125 | 125 | 363 | 324 | 0 | 0 | 488 | 449 |
| TIME · time_line_stamp | 0 | 992 | 0 | 0 | 0 | 0 | 0 | 992 |
| ZIPCODE · zip_shape_as_code | 105 | 84 | 100 | 84 | 0 | 0 | 205 | 168 |
| ZIPCODE · zip_shape_in_iban_field | 97 | 84 | 400 | 339 | 0 | 0 | 497 | 423 |
| ZIPCODE · zip_two_digits | 0 | 212 | 0 | 0 | 0 | 0 | 0 | 212 |
| ZIPCODE · zip_wrong_length | 456 | 201 | 390 | 345 | 0 | 0 | 846 | 546 |

## 3. Regex shapes anywhere in the text

| | v3 targeted | v4 targeted | v3 LLM | v4 LLM | v3 old | v4 old | v3 all | v4 all |
|---|---|---|---|---|---|---|---|---|
| hh:mm · unlabelled | 0 | 0 | 13,984 | 13,003 | 23,203 | 18,503 | 37,187 | 31,506 |
| hh:mm · labelled TIME | 657 | 778 | 4,386 | 4,184 | 5,544 | 5,444 | 10,587 | 10,406 |
| hh:mm · declared look-alike | 372 | 565 | 1,200 | 1,464 | 0 | 177 | 1,572 | 2,206 |
| hh:mm · labelled BUILDINGNUM | 0 | 0 | 0 | 0 | 14 | 14 | 14 | 14 |
| hh:mm · labelled AGE | 0 | 0 | 2 | 2 | 5 | 4 | 7 | 6 |
| hh:mm after `saat` · labelled TIME | 148 | 203 | 2,949 | 3,163 | 2,954 | 3,342 | 6,051 | 6,708 |
| hh:mm after `saat` · unlabelled | 0 | 0 | 404 | 42 | 1,100 | 131 | 1,504 | 173 |
| hh:mm after `saat` · declared look-alike | 93 | 85 | 313 | 285 | 0 | 1 | 406 | 371 |
| hh:mm after `vaxt` · labelled TIME | 152 | 180 | 762 | 748 | 1,656 | 1,450 | 2,570 | 2,378 |
| hh:mm after `vaxt` · unlabelled | 0 | 0 | 205 | 160 | 448 | 299 | 653 | 459 |
| hh:mm after `vaxt` · declared look-alike | 83 | 104 | 403 | 362 | 0 | 0 | 486 | 466 |
| hh:mm:ss · unlabelled | 0 | 0 | 26,398 | 27,427 | 42,484 | 35,842 | 68,882 | 63,269 |
| hh:mm:ss · declared look-alike | 1 | 817 | 160 | 326 | 0 | 608 | 161 | 1,751 |
| hh:mm:ss · labelled TIME | 0 | 554 | 150 | 19 | 655 | 71 | 805 | 644 |
| hh:mm:ss · labelled AGE | 0 | 0 | 3 | 2 | 12 | 9 | 15 | 11 |
| hh:mm:ss · labelled BUILDINGNUM | 0 | 0 | 3 | 3 | 2 | 0 | 5 | 3 |
| [hh:mm(:ss)] line stamp · unlabelled | 0 | 0 | 8,389 | 7,952 | 16,403 | 13,585 | 24,792 | 21,537 |
| [hh:mm(:ss)] line stamp · declared look-alike | 0 | 498 | 0 | 90 | 0 | 45 | 0 | 633 |
| [hh:mm(:ss)] line stamp · labelled TIME | 0 | 0 | 100 | 0 | 56 | 0 | 156 | 0 |
| [hh:mm(:ss)] line stamp · labelled BUILDINGNUM | 0 | 0 | 1 | 1 | 14 | 14 | 15 | 15 |
| [hh:mm(:ss)] line stamp · labelled AGE | 0 | 0 | 3 | 3 | 3 | 2 | 6 | 5 |
| IPv6-like (:: or 3+ colons) · labelled IPV6_ADDRESS | 1,155 | 769 | 2,675 | 2,664 | 1,777 | 1,550 | 5,607 | 4,983 |
| IPv6-like (:: or 3+ colons) · labelled MAC_ADDRESS | 666 | 475 | 1,572 | 1,558 | 1,705 | 1,459 | 3,943 | 3,492 |
| IPv6-like (:: or 3+ colons) · declared look-alike | 237 | 189 | 568 | 516 | 0 | 0 | 805 | 705 |
| IPv6-like (:: or 3+ colons) · unlabelled | 0 | 0 | 21 | 26 | 149 | 146 | 170 | 172 |
| IPv6-like, digit-only groups · unlabelled | 0 | 0 | 19 | 24 | 148 | 145 | 167 | 169 |
| IPv6-like, digit-only groups · labelled IPV6_ADDRESS | 2 | 2 | 7 | 5 | 0 | 0 | 9 | 7 |
| IPv6-like, digit-only groups · declared look-alike | 5 | 3 | 4 | 2 | 0 | 0 | 9 | 5 |
| ::ffff: + IPv4 · labelled IPV6_ADDRESS | 72 | 43 | 202 | 203 | 0 | 0 | 274 | 246 |
| MAC colon 6 pairs · labelled MAC_ADDRESS | 666 | 475 | 1,571 | 1,557 | 1,705 | 1,459 | 3,942 | 3,491 |
| MAC dash 6 pairs · labelled MAC_ADDRESS | 250 | 259 | 691 | 664 | 589 | 496 | 1,530 | 1,419 |
| MAC dash 6 pairs · unlabelled | 0 | 0 | 0 | 0 | 7 | 7 | 7 | 7 |
| dash pairs 3-4 (99-99-99) · declared look-alike | 30 | 112 | 127 | 107 | 0 | 0 | 157 | 219 |
| dash pairs 3-4 (99-99-99) · unlabelled | 0 | 0 | 6 | 6 | 10 | 8 | 16 | 14 |
| dotted 4 parts, all <=255 · labelled IPV4_ADDRESS | 706 | 736 | 2,918 | 2,839 | 3,983 | 3,385 | 7,607 | 6,960 |
| dotted 4 parts, all <=255 · labelled IPV6_ADDRESS | 72 | 43 | 202 | 203 | 0 | 0 | 274 | 246 |
| dotted 4 parts, all <=255 · unlabelled | 0 | 0 | 5 | 7 | 7 | 6 | 12 | 13 |
| dotted 4 parts, one-digit octets >=2 · unlabelled | 0 | 0 | 4 | 5 | 108 | 93 | 112 | 98 |
| dotted 4 parts, one-digit octets >=2 · declared look-alike | 0 | 38 | 9 | 9 | 0 | 0 | 9 | 47 |
| dotted 4 parts, one-digit octets >=2 · labelled IPV4_ADDRESS | 2 | 2 | 5 | 5 | 3 | 3 | 10 | 10 |
| dotted 3 parts (99.99.99) · unlabelled | 0 | 0 | 200 | 187 | 1,066 | 865 | 1,266 | 1,052 |
| dotted 3 parts (99.99.99) · labelled DATE | 0 | 0 | 503 | 484 | 704 | 610 | 1,207 | 1,094 |
| dotted 3 parts (99.99.99) · declared look-alike | 121 | 200 | 600 | 559 | 0 | 1 | 721 | 760 |
| dotted 5 parts · declared look-alike | 0 | 38 | 0 | 0 | 0 | 0 | 0 | 38 |
| email-like a@b.c · labelled EMAIL | 1,256 | 1,102 | 16,878 | 16,336 | 27,060 | 23,517 | 45,194 | 40,955 |
| email-like a@b.c · declared look-alike | 93 | 80 | 67 | 49 | 0 | 0 | 160 | 129 |
| email-like a@b.c · unlabelled | 0 | 0 | 0 | 0 | 4 | 4 | 4 | 4 |
| email-like, local part with dot · labelled EMAIL | 768 | 671 | 9,775 | 9,372 | 15,509 | 13,501 | 26,052 | 23,544 |
| email-like, local part with hyphen · labelled EMAIL | 17 | 17 | 667 | 646 | 1,031 | 899 | 1,715 | 1,562 |
| 2 letters + 6 digits · labelled AZ_DRIVER_LICENSE_NUMBER | 2,668 | 2,816 | 3,365 | 3,316 | 2,771 | 2,400 | 8,804 | 8,532 |
| 2 letters + 6 digits · declared look-alike | 85 | 0 | 64 | 55 | 0 | 0 | 149 | 55 |
| 2 letters + 6 digits · unlabelled | 0 | 0 | 1 | 0 | 13 | 12 | 14 | 12 |
| 2 letters + 6 digits after `sürücü` · labelled AZ_DRIVER_LICENSE_NUMBER | 622 | 720 | 2,183 | 2,128 | 1,522 | 1,306 | 4,327 | 4,154 |
| 2 letters + 6 digits after `vəsiqə` · labelled AZ_DRIVER_LICENSE_NUMBER | 157 | 166 | 340 | 342 | 344 | 311 | 841 | 819 |
| 2 letters + 6 digits after `vəsi̇qə` · labelled AZ_DRIVER_LICENSE_NUMBER | 0 | 0 | 0 | 0 | 4 | 3 | 4 | 3 |
| 2 letters + 6 digits after `şəxsiyyət` · labelled AZ_DRIVER_LICENSE_NUMBER | 3 | 12 | 34 | 37 | 19 | 15 | 56 | 64 |
| 2 letters + 7 digits · labelled AZ_ID_CARD_NUMBER | 1,767 | 3,154 | 2,658 | 2,616 | 1,928 | 1,681 | 6,353 | 7,451 |
| 2 letters + 7 digits · unlabelled | 0 | 0 | 3 | 3 | 406 | 328 | 409 | 331 |
| 2 letters + 7 digits · declared look-alike | 82 | 0 | 179 | 165 | 0 | 0 | 261 | 165 |
| 2 letters + 7 digits after `sürücü` · labelled AZ_ID_CARD_NUMBER | 2 | 22 | 22 | 25 | 5 | 4 | 29 | 51 |
| 2 letters + 7 digits after `vəsiqə` · labelled AZ_ID_CARD_NUMBER | 145 | 262 | 286 | 293 | 289 | 250 | 720 | 805 |
| 2 letters + 7 digits after `şəxsiyyət` · labelled AZ_ID_CARD_NUMBER | 472 | 657 | 1,692 | 1,654 | 932 | 810 | 3,096 | 3,121 |
| 3 digits · labelled TELEPHONENUM | 2,076 | 1,890 | 14,280 | 13,885 | 22,813 | 19,690 | 39,169 | 35,465 |
| 3 digits · unlabelled | 0 | 0 | 5,313 | 5,258 | 14,719 | 12,229 | 20,032 | 17,487 |
| 3 digits · labelled CARD_SECURITY_CODE | 621 | 730 | 1,673 | 1,642 | 2,068 | 1,794 | 4,362 | 4,166 |
| 3 digits · labelled BUILDINGNUM | 91 | 89 | 1,800 | 1,771 | 2,166 | 1,867 | 4,057 | 3,727 |
| 3 digits · declared look-alike | 853 | 1,323 | 1,610 | 1,367 | 0 | 0 | 2,463 | 2,690 |
| 3 digits · labelled IBAN | 16 | 16 | 92 | 84 | 138 | 121 | 246 | 221 |
| 3 digits · labelled URL | 14 | 7 | 0 | 0 | 0 | 0 | 14 | 7 |
| 3 digits · labelled STREET | 1 | 1 | 4 | 5 | 3 | 3 | 8 | 9 |
| 3 digits · labelled PRIVATE_KEY | 1 | 1 | 2 | 2 | 1 | 1 | 4 | 4 |
| 3 digits after `cvc` · labelled CARD_SECURITY_CODE | 105 | 105 | 36 | 32 | 66 | 56 | 207 | 193 |
| 3 digits after `cvc` · declared look-alike | 2 | 1 | 3 | 3 | 0 | 0 | 5 | 4 |
| 3 digits after `cvv` · labelled CARD_SECURITY_CODE | 401 | 466 | 390 | 413 | 414 | 365 | 1,205 | 1,244 |
| 3 digits after `cvv` · labelled TELEPHONENUM | 0 | 13 | 3 | 3 | 5 | 5 | 8 | 21 |
| 3 digits after `cvv` · unlabelled | 0 | 0 | 3 | 0 | 9 | 9 | 12 | 9 |
| 3 digits after `cvv` · declared look-alike | 1 | 3 | 2 | 2 | 0 | 0 | 3 | 5 |
| 3 digits after `təhlükəsizlik kodu` · labelled CARD_SECURITY_CODE | 106 | 109 | 1,152 | 1,108 | 1,356 | 1,171 | 2,614 | 2,388 |
| 3 digits after `təhlükəsizlik kodu` · unlabelled | 0 | 0 | 1 | 1 | 3 | 2 | 4 | 3 |
| 3 digits after `təhlükəsizlik kodu` · declared look-alike | 0 | 2 | 1 | 1 | 0 | 0 | 1 | 3 |
| 3 digits after `təhlükəsizlik kodu` · labelled TELEPHONENUM | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 2 |
| 4 digits · unlabelled | 0 | 0 | 14,104 | 13,257 | 31,245 | 26,579 | 45,349 | 39,836 |
| 4 digits · labelled DATE | 403 | 371 | 6,102 | 5,880 | 7,775 | 6,687 | 14,280 | 12,938 |
| 4 digits · labelled PAYMENT_CARD_NUMBER | 2,646 | 2,888 | 4,055 | 3,989 | 6,258 | 5,442 | 12,959 | 12,319 |
| 4 digits · labelled IBAN | 951 | 1,160 | 3,267 | 3,209 | 5,135 | 4,506 | 9,353 | 8,875 |
| 4 digits · declared look-alike | 595 | 725 | 4,068 | 1,552 | 0 | 1 | 4,663 | 2,278 |
| 4 digits · labelled ZIPCODE | 439 | 383 | 331 | 333 | 0 | 0 | 770 | 716 |
| 4 digits · labelled CARD_SECURITY_CODE | 129 | 154 | 265 | 263 | 357 | 286 | 751 | 703 |
| 4 digits · labelled TELEPHONENUM | 29 | 25 | 0 | 0 | 0 | 0 | 29 | 25 |
| 4 digits · labelled URL | 11 | 9 | 0 | 0 | 0 | 0 | 11 | 9 |
| 4 digits after `cvc` · declared look-alike | 19 | 18 | 68 | 44 | 0 | 0 | 87 | 62 |
| 4 digits after `cvc` · labelled CARD_SECURITY_CODE | 25 | 28 | 12 | 11 | 29 | 18 | 66 | 57 |
| 4 digits after `cvc` · unlabelled | 0 | 0 | 5 | 4 | 0 | 0 | 5 | 4 |
| 4 digits after `cvc` · labelled PAYMENT_CARD_NUMBER | 4 | 4 | 0 | 0 | 0 | 0 | 4 | 4 |
| 4 digits after `cvc` · labelled IBAN | 1 | 2 | 0 | 0 | 0 | 0 | 1 | 2 |
| 4 digits after `cvv` · declared look-alike | 80 | 67 | 228 | 198 | 0 | 0 | 308 | 265 |
| 4 digits after `cvv` · labelled CARD_SECURITY_CODE | 78 | 83 | 65 | 63 | 74 | 54 | 217 | 200 |
| 4 digits after `cvv` · labelled PAYMENT_CARD_NUMBER | 11 | 33 | 4 | 0 | 0 | 0 | 15 | 33 |
| 4 digits after `cvv` · unlabelled | 0 | 0 | 7 | 9 | 1 | 1 | 8 | 10 |
| 4 digits after `cvv` · labelled DATE | 1 | 1 | 0 | 1 | 0 | 0 | 1 | 2 |
| 4 digits after `indeks` · labelled ZIPCODE | 123 | 101 | 13 | 11 | 0 | 0 | 136 | 112 |
| 4 digits after `indeks` · unlabelled | 0 | 0 | 7 | 6 | 15 | 13 | 22 | 19 |
| 4 digits after `indeks` · labelled PAYMENT_CARD_NUMBER | 7 | 6 | 1 | 1 | 1 | 1 | 9 | 8 |
| 4 digits after `indeks` · declared look-alike | 1 | 1 | 5 | 2 | 0 | 0 | 6 | 3 |
| 4 digits after `indeks` · labelled IBAN | 1 | 1 | 0 | 0 | 1 | 1 | 2 | 2 |
| 4 digits after `i̇ndeks` · labelled ZIPCODE | 11 | 6 | 1 | 1 | 0 | 0 | 12 | 7 |
| 4 digits after `i̇ndeks` · unlabelled | 0 | 0 | 0 | 1 | 3 | 2 | 3 | 3 |
| 4 digits after `i̇ndeks` · declared look-alike | 1 | 4 | 0 | 0 | 0 | 0 | 1 | 4 |
| 4 digits after `poçt` · labelled ZIPCODE | 128 | 111 | 279 | 283 | 0 | 0 | 407 | 394 |
| 4 digits after `poçt` · unlabelled | 0 | 0 | 32 | 34 | 16 | 13 | 48 | 47 |
| 4 digits after `poçt` · labelled PAYMENT_CARD_NUMBER | 0 | 4 | 6 | 3 | 0 | 0 | 6 | 7 |
| 4 digits after `poçt` · labelled DATE | 0 | 0 | 6 | 4 | 0 | 0 | 6 | 4 |
| 4 digits after `poçt` · declared look-alike | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 2 |
| 4 digits after `poçt` · labelled CARD_SECURITY_CODE | 1 | 1 | 0 | 0 | 1 | 0 | 2 | 1 |
| AZ + 4 digits · labelled ZIPCODE | 947 | 838 | 4,904 | 4,803 | 8,159 | 7,049 | 14,010 | 12,690 |
| AZ + 4 digits · unlabelled | 0 | 0 | 19 | 19 | 2,309 | 1,915 | 2,328 | 1,934 |
| AZ + 4 digits · declared look-alike | 202 | 168 | 501 | 424 | 0 | 0 | 703 | 592 |
| AZ + 4 digits after `indeks` · labelled ZIPCODE | 135 | 165 | 225 | 208 | 305 | 266 | 665 | 639 |
| AZ + 4 digits after `indeks` · declared look-alike | 0 | 44 | 1 | 1 | 0 | 0 | 1 | 45 |
| AZ + 4 digits after `indeks` · unlabelled | 0 | 0 | 0 | 0 | 20 | 17 | 20 | 17 |
| AZ + 4 digits after `i̇ndeks` · labelled ZIPCODE | 73 | 52 | 11 | 11 | 73 | 69 | 157 | 132 |
| AZ + 4 digits after `i̇ndeks` · unlabelled | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 2 |
| AZ + 4 digits after `poçt` · labelled ZIPCODE | 158 | 149 | 2,135 | 2,053 | 4,508 | 3,896 | 6,801 | 6,098 |
| AZ + 4 digits after `poçt` · declared look-alike | 2 | 12 | 0 | 0 | 0 | 0 | 2 | 12 |
| dd.mm.yyyy · labelled DATE | 449 | 429 | 12,965 | 12,549 | 22,697 | 19,576 | 36,111 | 32,554 |
| dd.mm.yyyy · unlabelled | 0 | 0 | 2,610 | 2,330 | 2,003 | 1,718 | 4,613 | 4,048 |
| dd.mm.yyyy · declared look-alike | 1,407 | 1,304 | 1,295 | 1,217 | 0 | 33 | 2,702 | 2,554 |
| dd.mm.yyyy after `tarix` · labelled DATE | 255 | 243 | 8,053 | 7,772 | 12,168 | 10,569 | 20,476 | 18,584 |
| dd.mm.yyyy after `tarix` · declared look-alike | 1,157 | 1,074 | 466 | 429 | 0 | 8 | 1,623 | 1,511 |
| dd.mm.yyyy after `tarix` · unlabelled | 0 | 0 | 436 | 429 | 219 | 179 | 655 | 608 |
| dd.mm.yyyy after `tari̇x` · labelled DATE | 0 | 0 | 25 | 25 | 119 | 96 | 144 | 121 |
| dd.mm.yyyy after `tari̇x` · unlabelled | 0 | 0 | 8 | 9 | 4 | 4 | 12 | 13 |
| 5 digits · unlabelled | 0 | 0 | 1,049 | 1,145 | 2,630 | 2,218 | 3,679 | 3,363 |
| 5 digits · declared look-alike | 524 | 478 | 963 | 819 | 0 | 0 | 1,487 | 1,297 |
| 5 digits · labelled PAYMENT_CARD_NUMBER | 15 | 17 | 92 | 81 | 136 | 119 | 243 | 217 |
| 5 digits · labelled URL | 14 | 15 | 41 | 41 | 51 | 43 | 106 | 99 |
| 5 digits after `cvc` · declared look-alike | 72 | 97 | 90 | 66 | 0 | 0 | 162 | 163 |
| 5 digits after `cvv` · declared look-alike | 301 | 270 | 322 | 256 | 0 | 0 | 623 | 526 |
| 5 digits after `cvv` · unlabelled | 0 | 0 | 1 | 1 | 1 | 1 | 2 | 2 |
| 5 digits after `indeks` · unlabelled | 0 | 0 | 0 | 0 | 6 | 6 | 6 | 6 |
| 5 digits after `i̇ndeks` · unlabelled | 0 | 0 | 1 | 1 | 2 | 2 | 3 | 3 |
| 5 digits after `poçt` · unlabelled | 0 | 0 | 7 | 6 | 3 | 2 | 10 | 8 |
| AZ + 1-3 digits · labelled IBAN | 251 | 288 | 417 | 413 | 677 | 587 | 1,345 | 1,288 |
| AZ + 1-3 digits · declared look-alike | 206 | 148 | 202 | 174 | 0 | 0 | 408 | 322 |
| AZ + 1-3 digits · unlabelled | 0 | 0 | 7 | 5 | 12 | 8 | 19 | 13 |
| AZ + 1-3 digits after `indeks` · declared look-alike | 9 | 2 | 74 | 60 | 0 | 0 | 83 | 62 |
| AZ + 1-3 digits after `i̇ndeks` · declared look-alike | 25 | 8 | 2 | 0 | 0 | 0 | 27 | 8 |
| AZ + 1-3 digits after `poçt` · declared look-alike | 39 | 21 | 58 | 52 | 0 | 0 | 97 | 73 |
| AZ + 1-3 digits after `poçt` · labelled IBAN | 4 | 1 | 0 | 0 | 0 | 0 | 4 | 1 |
| AZ + 1-3 digits after `poçt` · unlabelled | 0 | 0 | 2 | 1 | 1 | 1 | 3 | 2 |
| AZ + 5 digits · declared look-alike | 84 | 53 | 69 | 63 | 0 | 0 | 153 | 116 |
| AZ + 5 digits · unlabelled | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 2 |
| AZ + 5 digits after `indeks` · declared look-alike | 3 | 4 | 21 | 22 | 0 | 0 | 24 | 26 |
| AZ + 5 digits after `i̇ndeks` · declared look-alike | 3 | 4 | 0 | 0 | 0 | 0 | 3 | 4 |
| AZ + 5 digits after `poçt` · declared look-alike | 19 | 7 | 27 | 19 | 0 | 0 | 46 | 26 |
| hh:mm, hour > 23 or minute > 59 · declared look-alike | 258 | 256 | 704 | 626 | 0 | 0 | 962 | 882 |
| hh:mm, hour > 23 or minute > 59 · unlabelled | 0 | 0 | 12 | 13 | 1 | 1 | 13 | 14 |
| hh:mm, hour > 23 or minute > 59 · labelled TIME | 0 | 0 | 3 | 2 | 1 | 1 | 4 | 3 |
| hh:mm, hour > 23 or minute > 59 after `saat` · declared look-alike | 93 | 84 | 311 | 282 | 0 | 0 | 404 | 366 |
| hh:mm, hour > 23 or minute > 59 after `saat` · unlabelled | 0 | 0 | 2 | 2 | 0 | 0 | 2 | 2 |
| hh:mm, hour > 23 or minute > 59 after `saat` · labelled TIME | 0 | 0 | 2 | 1 | 0 | 0 | 2 | 1 |
| hh:mm, hour > 23 or minute > 59 after `vaxt` · declared look-alike | 83 | 104 | 388 | 339 | 0 | 0 | 471 | 443 |
| dd.mm.yyyy, month > 12 · declared look-alike | 567 | 524 | 170 | 159 | 0 | 0 | 737 | 683 |
| dd.mm.yyyy, month > 12 · unlabelled | 0 | 0 | 4 | 4 | 3 | 2 | 7 | 6 |
| dd.mm.yyyy, month > 12 after `tarix` · declared look-alike | 467 | 424 | 121 | 115 | 0 | 0 | 588 | 539 |
| dd.mm.yyyy, month > 12 after `tarix` · unlabelled | 0 | 0 | 2 | 2 | 1 | 1 | 3 | 3 |
| 30/31.02.yyyy · declared look-alike | 140 | 131 | 57 | 40 | 0 | 0 | 197 | 171 |
| 30/31.02.yyyy after `tarix` · declared look-alike | 108 | 102 | 40 | 27 | 0 | 0 | 148 | 129 |
