# Shapes in the training data: v4.1 against v4.2

Sources: targeted builder; LLM batches b1-b6; old corpus (`_old`).

| documents | v4.1 | v4.2 |
|---|---|---|
| targeted | 22,612 | 29,851 |
| LLM b1 | 3,765 | 3,742 |
| LLM b2 | 4,240 | 4,146 |
| LLM b3 | 4,314 | 4,300 |
| LLM b4 | 4,328 | 4,375 |
| LLM b5 | 15,529 | 15,600 |
| LLM b6 | 17,413 | 17,385 |
| old corpus | 63,069 | 63,069 |

## 1. Labelled values

| | v4.1 targeted | v4.2 targeted | v4.1 LLM | v4.2 LLM | v4.1 old | v4.2 old | v4.1 all | v4.2 all |
|---|---|---|---|---|---|---|---|---|
| AZ_DRIVER_LICENSE_NUMBER | 3,653 | 5,270 | 3,296 | 3,295 | 2,400 | 2,400 | 9,349 | 10,965 |
| AZ_ID_CARD_NUMBER | 4,517 | 6,310 | 3,895 | 3,811 | 3,235 | 3,235 | 11,647 | 13,356 |
| CARD_SECURITY_CODE | 1,224 | 1,902 | 2,174 | 2,163 | 2,329 | 2,329 | 5,727 | 6,394 |
| DATE | 1,353 | 2,365 | 27,019 | 26,993 | 39,549 | 39,549 | 67,921 | 68,907 |
| EMAIL | 1,202 | 1,533 | 16,138 | 16,219 | 23,517 | 23,517 | 40,857 | 41,269 |
| IPV4_ADDRESS | 911 | 1,571 | 3,084 | 3,039 | 3,823 | 3,823 | 7,818 | 8,433 |
| IPV6_ADDRESS | 1,358 | 2,272 | 2,624 | 2,595 | 1,553 | 1,553 | 5,535 | 6,420 |
| MAC_ADDRESS | 1,249 | 1,664 | 2,788 | 2,819 | 1,960 | 1,960 | 5,997 | 6,443 |
| TIME | 1,520 | 3,173 | 4,284 | 4,215 | 5,584 | 5,587 | 11,388 | 12,975 |
| ZIPCODE | 1,687 | 2,196 | 5,099 | 5,117 | 7,049 | 7,049 | 13,835 | 14,362 |

### By shape

| | v4.1 targeted | v4.2 targeted | v4.1 LLM | v4.2 LLM | v4.1 old | v4.2 old | v4.1 all | v4.2 all |
|---|---|---|---|---|---|---|---|---|
| AZ_DRIVER_LICENSE_NUMBER · `aa999999` | 3,653 | 5,270 | 3,296 | 3,295 | 2,400 | 2,400 | 9,349 | 10,965 |
| AZ_ID_CARD_NUMBER · `aa9999999` | 4,255 | 5,939 | 2,610 | 2,552 | 1,681 | 1,681 | 8,546 | 10,172 |
| AZ_ID_CARD_NUMBER · `aaa9999999` | 262 | 371 | 1,285 | 1,259 | 1,554 | 1,554 | 3,101 | 3,184 |
| CARD_SECURITY_CODE · `999` | 917 | 1,460 | 1,709 | 1,711 | 2,012 | 2,012 | 4,638 | 5,183 |
| CARD_SECURITY_CODE · `9999` | 178 | 266 | 289 | 275 | 316 | 316 | 783 | 857 |
| CARD_SECURITY_CODE · `99-9` | 78 | 108 | 102 | 98 | 0 | 0 | 180 | 206 |
| CARD_SECURITY_CODE · `9-99` | 22 | 29 | 71 | 76 | 0 | 0 | 93 | 105 |
| CARD_SECURITY_CODE · `99-99` | 29 | 39 | 0 | 0 | 0 | 0 | 29 | 39 |
| DATE · `99.99.9999` | 449 | 791 | 12,604 | 12,549 | 20,331 | 20,331 | 33,384 | 33,671 |
| DATE · `9999-99-99` | 446 | 790 | 3,400 | 3,426 | 4,275 | 4,275 | 8,121 | 8,491 |
| DATE · `99 aaaaaa 9999` | 118 | 296 | 2,417 | 2,425 | 3,028 | 3,028 | 5,563 | 5,749 |
| DATE · `99 aaaa 9999` | 96 | 128 | 1,229 | 1,256 | 3,395 | 3,395 | 4,720 | 4,779 |
| DATE · `99 aaa 9999` | 27 | 46 | 993 | 976 | 2,604 | 2,604 | 3,624 | 3,626 |
| DATE · `99/99/9999` | 0 | 0 | 1,945 | 1,948 | 914 | 914 | 2,859 | 2,862 |
| DATE · `99 aaaaaaa 9999` | 24 | 52 | 639 | 638 | 1,279 | 1,279 | 1,942 | 1,969 |
| DATE · `99 aaaaaaaa 9999` | 27 | 45 | 411 | 418 | 944 | 944 | 1,382 | 1,407 |
| DATE · `99.99.99` | 0 | 0 | 464 | 475 | 648 | 648 | 1,112 | 1,123 |
| DATE · `99.9.9999` | 0 | 0 | 407 | 393 | 595 | 595 | 1,002 | 988 |
| DATE · `9 aaaaaa 9999` | 52 | 76 | 560 | 570 | 301 | 301 | 913 | 947 |
| DATE · `99 aaaaa 9999` | 21 | 38 | 259 | 255 | 374 | 374 | 654 | 667 |
| DATE · `9 aaaa 9999` | 33 | 40 | 362 | 348 | 191 | 191 | 586 | 579 |
| DATE · `9.9.9999` | 0 | 0 | 138 | 138 | 218 | 218 | 356 | 356 |
| DATE · `9 aaaaa 9999` | 18 | 15 | 122 | 123 | 68 | 68 | 208 | 206 |
| DATE · `9 aaa 9999` | 18 | 10 | 141 | 130 | 57 | 57 | 216 | 197 |
| DATE · `9 aaaaaaa 9999` | 10 | 20 | 129 | 120 | 58 | 58 | 197 | 198 |
| DATE · `9 aaaaaaaa 9999` | 14 | 18 | 112 | 121 | 57 | 57 | 183 | 196 |
| DATE · `9.99.9999` | 0 | 0 | 63 | 67 | 92 | 92 | 155 | 159 |
| DATE · `aaaaa, 99 aaaa 9999` | 0 | 0 | 22 | 23 | 0 | 0 | 22 | 23 |
| DATE · `99 aaaaaa 9999, aaaaa` | 0 | 0 | 18 | 18 | 0 | 0 | 18 | 18 |
| DATE · `aaaaa, 99 aaaaaa 9999` | 0 | 0 | 20 | 15 | 0 | 0 | 20 | 15 |
| DATE · `99 aaaaaa 9999, aaaaa aaaaaa` | 0 | 0 | 14 | 17 | 0 | 0 | 14 | 17 |
| DATE · `99 aaaaaa 9999, aaaaaaaa aaaaaa` | 0 | 0 | 17 | 13 | 0 | 0 | 17 | 13 |
| DATE · `aaaa, 99 aaaaaa 9999` | 0 | 0 | 17 | 13 | 0 | 0 | 17 | 13 |
| DATE · `aaaa, 99 aaaa 9999` | 0 | 0 | 14 | 15 | 0 | 0 | 14 | 15 |
| DATE · `99 aaaa 9999, aaaaa` | 0 | 0 | 12 | 13 | 0 | 0 | 12 | 13 |
| DATE · `99 aaaaaa 9999, aaaa` | 0 | 0 | 12 | 12 | 0 | 0 | 12 | 12 |
| DATE · `99-99-9999` | 0 | 0 | 5 | 7 | 6 | 6 | 11 | 13 |
| DATE · `aaaaa aaaaaa, 99 aaaaaa 9999` | 0 | 0 | 14 | 9 | 0 | 0 | 14 | 9 |
| DATE · `aaaaa, 9 aaaaaa 9999` | 0 | 0 | 12 | 11 | 0 | 0 | 12 | 11 |
| DATE · `aaaaaaaa, 99 aaaaaa 9999` | 0 | 0 | 11 | 12 | 0 | 0 | 11 | 12 |
| DATE · `aaaaaaaa aaaaaa, 99 aaaaaa 9999` | 0 | 0 | 11 | 11 | 0 | 0 | 11 | 11 |
| DATE · `aaaa aaaaaa, 99 aaaaaa 9999` | 0 | 0 | 8 | 9 | 0 | 0 | 8 | 9 |
| DATE · `aaaaa, 99 aaaaaaa 9999` | 0 | 0 | 9 | 8 | 0 | 0 | 9 | 8 |
| DATE · `99  aaaa 9999` | 0 | 0 | 2 | 2 | 6 | 6 | 8 | 8 |
| DATE · `9 aaaaaa 9999, aaaaa` | 0 | 0 | 9 | 6 | 0 | 0 | 9 | 6 |
| DATE · `9 aaaaaa 9999, aaaa aaaaaa` | 0 | 0 | 6 | 8 | 0 | 0 | 6 | 8 |
| DATE · `9999/99/99` | 0 | 0 | 2 | 2 | 5 | 5 | 7 | 7 |
| DATE · `aaaaa aaaaaa, 99 aaaa 9999` | 0 | 0 | 8 | 6 | 0 | 0 | 8 | 6 |
| DATE · `9 aaaa 9999, aaaaa aaaaaa` | 0 | 0 | 6 | 7 | 0 | 0 | 6 | 7 |
| DATE · `9 aaaaaa 9999, aaaaa aaaaaa` | 0 | 0 | 7 | 6 | 0 | 0 | 7 | 6 |
| DATE · `99 aaaa 9999, aaaa aaaaaa` | 0 | 0 | 7 | 6 | 0 | 0 | 7 | 6 |
| DATE · `aaaaaaaa aaaaaa, 9 aaaaaa 9999` | 0 | 0 | 6 | 7 | 0 | 0 | 6 | 7 |
| DATE · `99  aaaaaa 9999` | 0 | 0 | 1 | 1 | 5 | 5 | 6 | 6 |
| DATE · `99 aaaa 9999, aaaaaaaa` | 0 | 0 | 7 | 5 | 0 | 0 | 7 | 5 |
| DATE · `99.99.999` | 0 | 0 | 6 | 6 | 0 | 0 | 6 | 6 |
| DATE · `aaaa aaaaaa, 99 aaaa 9999` | 0 | 0 | 6 | 6 | 0 | 0 | 6 | 6 |
| DATE · `aaaaa, 99 aaaaa 9999` | 0 | 0 | 6 | 6 | 0 | 0 | 6 | 6 |
| DATE · `9 aaaa 9999, aaaaaaaa aaaaaa` | 0 | 0 | 5 | 6 | 0 | 0 | 5 | 6 |
| DATE · `99 aaaa 9999, aaaaaaaa aaaaaa` | 0 | 0 | 4 | 7 | 0 | 0 | 4 | 7 |
| DATE · `99	aaaaaa 9999` | 0 | 0 | 1 | 1 | 4 | 4 | 5 | 5 |
| DATE · `99  aaa 9999` | 0 | 0 | 1 | 1 | 4 | 4 | 5 | 5 |
| DATE · `99 aaaaaa  9999` | 0 | 0 | 1 | 1 | 4 | 4 | 5 | 5 |
| DATE · `99 aaaaaa 9999, aaaa aaaaaa` | 0 | 0 | 5 | 5 | 0 | 0 | 5 | 5 |
| DATE · `aaaa aaaaaa, 9 aaaaaa 9999` | 0 | 0 | 5 | 5 | 0 | 0 | 5 | 5 |
| DATE · `aaaa, 99 aaa 9999` | 0 | 0 | 4 | 6 | 0 | 0 | 4 | 6 |
| DATE · `9 aaaa 9999, aaaa aaaaaa` | 0 | 0 | 4 | 5 | 0 | 0 | 4 | 5 |
| DATE · `99 aaaa 9999, aaaaa aaaaaa` | 0 | 0 | 6 | 3 | 0 | 0 | 6 | 3 |
| DATE · `9999-99–99` | 0 | 0 | 3 | 2 | 2 | 2 | 5 | 4 |
| DATE · `aaaaaaaa aaaaaa, 99 aaaa 9999` | 0 | 0 | 5 | 4 | 0 | 0 | 5 | 4 |
| DATE · `aaaaaaaa, 9 aaaa 9999` | 0 | 0 | 4 | 5 | 0 | 0 | 4 | 5 |
| DATE · `aaaaaaaa, 9 aaaaaa 9999` | 0 | 0 | 4 | 5 | 0 | 0 | 4 | 5 |
| DATE · `9 aaaa 9999, aaaaa` | 0 | 0 | 3 | 5 | 0 | 0 | 3 | 5 |
| DATE · `9 aaaaaa 9999, aaaaaaaa` | 0 | 0 | 4 | 4 | 0 | 0 | 4 | 4 |
| DATE · `9 aaaaaaa 9999, aaaaa` | 0 | 0 | 4 | 4 | 0 | 0 | 4 | 4 |
| DATE · `9 aaaaaaaa 9999, aaaaaaaa` | 0 | 0 | 4 | 4 | 0 | 0 | 4 | 4 |
| DATE · `99   aaaaaa 9999` | 0 | 0 | 1 | 1 | 3 | 3 | 4 | 4 |
| DATE · `99 aaaaaa	9999` | 0 | 0 | 3 | 3 | 1 | 1 | 4 | 4 |
| DATE · `99 aaaaaa 9999, aaaaaaaa` | 0 | 0 | 4 | 4 | 0 | 0 | 4 | 4 |
| DATE · `99 aaaaaaa 9999, aaaaa` | 0 | 0 | 5 | 3 | 0 | 0 | 5 | 3 |
| DATE · `99 aaaa 9999` | 0 | 0 | 5 | 3 | 0 | 0 | 5 | 3 |
| DATE · `99 aaa 9999` | 0 | 0 | 2 | 2 | 2 | 2 | 4 | 4 |
| DATE · `99.99.a999` | 0 | 0 | 3 | 3 | 1 | 1 | 4 | 4 |
| DATE · `99 aaa 9999` | 0 | 0 | 0 | 0 | 4 | 4 | 4 | 4 |
| DATE · `99 aaaa 9999` | 0 | 0 | 0 | 0 | 4 | 4 | 4 | 4 |
| DATE · `aaaa aaaaaa, 9 aaaaaaaa 9999` | 0 | 0 | 4 | 4 | 0 | 0 | 4 | 4 |
| DATE · `aaaaa aaaaaa, 9 aaaaaa 9999` | 0 | 0 | 5 | 3 | 0 | 0 | 5 | 3 |
| DATE · `aaaaa aaaaaa, 99 aaaaaaa 9999` | 0 | 0 | 4 | 4 | 0 | 0 | 4 | 4 |
| DATE · `aaaaa, 99 aaa 9999` | 0 | 0 | 4 | 4 | 0 | 0 | 4 | 4 |
| DATE · `aaaaaaaa, 99 aaaa 9999` | 0 | 0 | 4 | 4 | 0 | 0 | 4 | 4 |
| DATE · `99 aaa  9999` | 0 | 0 | 0 | 1 | 3 | 3 | 3 | 4 |
| DATE · `99 aaaaa 9999, aaaaa` | 0 | 0 | 4 | 3 | 0 | 0 | 4 | 3 |
| DATE · `99 aaaaa 9999, aaaaaaaa aaaaaa` | 0 | 0 | 3 | 4 | 0 | 0 | 3 | 4 |
| DATE · `99 aaaaaa, 9999` | 0 | 0 | 3 | 4 | 0 | 0 | 3 | 4 |
| DATE · `99 aaaaaaa 9999, aaaaa aaaaaa` | 0 | 0 | 3 | 4 | 0 | 0 | 3 | 4 |
| DATE · `99.99.999a` | 0 | 0 | 1 | 2 | 2 | 2 | 3 | 4 |
| DATE · `9999–99-99` | 0 | 0 | 4 | 3 | 0 | 0 | 4 | 3 |
| DATE · `aaaaa, 9 aaaa 9999` | 0 | 0 | 4 | 3 | 0 | 0 | 4 | 3 |
| DATE · `9 aaa 9999, aaaaaaaa` | 0 | 0 | 3 | 3 | 0 | 0 | 3 | 3 |
| DATE · `9 aaaaa 9999, aaaa` | 0 | 0 | 3 | 3 | 0 | 0 | 3 | 3 |
| DATE · `9 aaaaa 9999, aaaaaaaa` | 0 | 0 | 4 | 2 | 0 | 0 | 4 | 2 |
| DATE · `9/999/9999` | 0 | 0 | 1 | 1 | 2 | 2 | 3 | 3 |
| DATE · `99	aaaaaaaa 9999` | 0 | 0 | 2 | 2 | 1 | 1 | 3 | 3 |
| DATE · `99 aaaa	9999` | 0 | 0 | 1 | 1 | 2 | 2 | 3 | 3 |
| DATE · `99 aaaa  9999` | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 3 |
| DATE · `99 aaaaaa   9999` | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 3 |
| DATE · `99 aaaaaaa 9999, aaaaaaaa` | 0 | 0 | 3 | 3 | 0 | 0 | 3 | 3 |
| DATE · `99 aaaaaaaa 9999, aaaaaaaa aaaaaa` | 0 | 0 | 3 | 3 | 0 | 0 | 3 | 3 |
| DATE · `99.a9.9999` | 0 | 0 | 2 | 2 | 1 | 1 | 3 | 3 |
| DATE · `999.9.9999` | 0 | 0 | 1 | 1 | 2 | 2 | 3 | 3 |
| DATE · `999.99.9999` | 0 | 0 | 3 | 3 | 0 | 0 | 3 | 3 |
| DATE · `99 aaaaaa 9999` | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 3 |
| DATE · `aaaaa aaaaaa, 9 aaaa 9999` | 0 | 0 | 2 | 4 | 0 | 0 | 2 | 4 |
| DATE · `9 aaaa 9999, aaaaaaaa` | 0 | 0 | 3 | 2 | 0 | 0 | 3 | 2 |
| DATE · `99 aaa 9999, aaaaa` | 0 | 0 | 2 | 3 | 0 | 0 | 2 | 3 |
| DATE · `99 aaaa 9999, aaaa` | 0 | 0 | 3 | 2 | 0 | 0 | 3 | 2 |
| DATE · `99 aaaaa 9999, aaaa aaaaaa` | 0 | 0 | 2 | 3 | 0 | 0 | 2 | 3 |
| DATE · `99 aaaaaaaa 9999, aaaa` | 0 | 0 | 3 | 2 | 0 | 0 | 3 | 2 |
| DATE · `99 aaaaaaaa 9999, aaaaaaaa` | 0 | 0 | 1 | 4 | 0 | 0 | 1 | 4 |
| DATE · `99.9a.9999` | 0 | 0 | 2 | 3 | 0 | 0 | 2 | 3 |
| DATE · `aaaa aaaaaa, 99 aaaaaaaa 9999` | 0 | 0 | 3 | 2 | 0 | 0 | 3 | 2 |
| DATE · `aaaaa aaaaaa, 99 aaaaa 9999` | 0 | 0 | 3 | 2 | 0 | 0 | 3 | 2 |
| DATE · `aaaaaaaa, 99 aaaaaaa 9999` | 0 | 0 | 2 | 3 | 0 | 0 | 2 | 3 |
| DATE · `99 aaaaaaaa 9999, aaaaa` | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 5 |
| EMAIL · `domain dots 1` | 1,202 | 1,533 | 16,138 | 16,219 | 23,517 | 23,517 | 40,857 | 41,269 |
| EMAIL · `local: dot` | 545 | 714 | 7,733 | 7,702 | 11,171 | 11,171 | 19,449 | 19,587 |
| EMAIL · `local: letters only` | 87 | 116 | 2,695 | 2,670 | 4,031 | 4,031 | 6,813 | 6,817 |
| EMAIL · `local: digit` | 172 | 194 | 2,069 | 2,140 | 2,993 | 2,993 | 5,234 | 5,327 |
| EMAIL · `local: dot+digit` | 245 | 297 | 1,572 | 1,605 | 2,330 | 2,330 | 4,147 | 4,232 |
| EMAIL · `local: underscore` | 139 | 190 | 1,419 | 1,462 | 2,093 | 2,093 | 3,651 | 3,745 |
| EMAIL · `local: hyphen` | 14 | 22 | 650 | 640 | 899 | 899 | 1,563 | 1,561 |
| EMAIL · `domain hyphen` | 259 | 332 | 544 | 519 | 685 | 685 | 1,488 | 1,536 |
| EMAIL · `upper case` | 0 | 0 | 104 | 89 | 0 | 0 | 104 | 89 |
| IPV4_ADDRESS · `4 parts` | 911 | 1,571 | 3,084 | 3,039 | 3,823 | 3,823 | 7,818 | 8,433 |
| IPV4_ADDRESS · `no one-digit octet` | 491 | 858 | 2,506 | 2,468 | 3,065 | 3,065 | 6,062 | 6,391 |
| IPV4_ADDRESS · `private` | 303 | 496 | 742 | 724 | 894 | 894 | 1,939 | 2,114 |
| IPV4_ADDRESS · `documentation` | 90 | 146 | 410 | 404 | 537 | 537 | 1,037 | 1,087 |
| IPV4_ADDRESS · `1 one-digit octets` | 107 | 154 | 408 | 392 | 516 | 516 | 1,031 | 1,062 |
| IPV4_ADDRESS · `2 one-digit octets` | 118 | 243 | 169 | 177 | 231 | 231 | 518 | 651 |
| IPV4_ADDRESS · `3 one-digit octets` | 117 | 183 | 1 | 2 | 11 | 11 | 129 | 196 |
| IPV4_ADDRESS · `4 one-digit octets` | 78 | 133 | 0 | 0 | 0 | 0 | 78 | 133 |
| IPV6_ADDRESS · `lower` | 1,071 | 1,747 | 2,040 | 1,974 | 1,553 | 1,553 | 4,664 | 5,274 |
| IPV6_ADDRESS · `full 8 groups` | 414 | 595 | 471 | 463 | 1,553 | 1,553 | 2,438 | 2,611 |
| IPV6_ADDRESS · `:: middle` | 630 | 1,170 | 1,483 | 1,460 | 0 | 0 | 2,113 | 2,630 |
| IPV6_ADDRESS · `prefix 2001:db8` | 436 | 763 | 924 | 938 | 208 | 208 | 1,568 | 1,909 |
| IPV6_ADDRESS · `prefix fd/fc` | 377 | 600 | 662 | 642 | 550 | 550 | 1,589 | 1,792 |
| IPV6_ADDRESS · `other prefix` | 258 | 437 | 418 | 403 | 795 | 795 | 1,471 | 1,635 |
| IPV6_ADDRESS · `leading zeros` | 166 | 236 | 190 | 191 | 472 | 472 | 828 | 899 |
| IPV6_ADDRESS · `upper` | 211 | 372 | 398 | 432 | 0 | 0 | 609 | 804 |
| IPV6_ADDRESS · `prefix ::` | 196 | 306 | 412 | 431 | 0 | 0 | 608 | 737 |
| IPV6_ADDRESS · `:: end` | 118 | 201 | 258 | 241 | 0 | 0 | 376 | 442 |
| IPV6_ADDRESS · `::ffff:` | 100 | 150 | 207 | 220 | 0 | 0 | 307 | 370 |
| IPV6_ADDRESS · `:: start` | 96 | 156 | 205 | 211 | 0 | 0 | 301 | 367 |
| IPV6_ADDRESS · `prefix fe80` | 91 | 166 | 208 | 181 | 0 | 0 | 299 | 347 |
| IPV6_ADDRESS · `mixed` | 75 | 149 | 180 | 184 | 0 | 0 | 255 | 333 |
| IPV6_ADDRESS · `digit-only groups` | 1 | 4 | 6 | 5 | 0 | 0 | 7 | 9 |
| IPV6_ADDRESS · `no letters` | 1 | 4 | 6 | 5 | 0 | 0 | 7 | 9 |
| MAC_ADDRESS · `colon` | 708 | 921 | 1,562 | 1,558 | 1,461 | 1,461 | 3,731 | 3,940 |
| MAC_ADDRESS · `upper` | 565 | 776 | 1,306 | 1,279 | 1,282 | 1,282 | 3,153 | 3,337 |
| MAC_ADDRESS · `lower` | 506 | 699 | 1,144 | 1,186 | 678 | 678 | 2,328 | 2,563 |
| MAC_ADDRESS · `dash` | 295 | 383 | 666 | 681 | 499 | 499 | 1,460 | 1,563 |
| MAC_ADDRESS · `dotted` | 246 | 360 | 560 | 580 | 0 | 0 | 806 | 940 |
| MAC_ADDRESS · `mixed` | 178 | 189 | 338 | 354 | 0 | 0 | 516 | 543 |
| TIME · `99:99` | 825 | 2,085 | 3,660 | 3,586 | 4,834 | 4,837 | 9,319 | 10,508 |
| TIME · `9:99 aa` | 96 | 154 | 443 | 455 | 515 | 515 | 1,054 | 1,124 |
| TIME · `99:99:99` | 570 | 882 | 23 | 24 | 52 | 52 | 645 | 958 |
| TIME · `99:99 aa` | 29 | 52 | 146 | 139 | 166 | 166 | 341 | 357 |
| TIME · `9:99` | 0 | 0 | 5 | 4 | 3 | 3 | 8 | 7 |
| TIME · `99:a9` | 0 | 0 | 2 | 2 | 1 | 1 | 3 | 3 |
| TIME · `a9:99` | 0 | 0 | 1 | 1 | 2 | 2 | 3 | 3 |
| ZIPCODE · `aa9999` | 1,052 | 1,425 | 4,727 | 4,742 | 7,049 | 7,049 | 12,828 | 13,216 |
| ZIPCODE · `9999` | 635 | 771 | 372 | 375 | 0 | 0 | 1,007 | 1,146 |

## 2. Declared look-alikes (`_decoys`)

| | v4.1 targeted | v4.2 targeted | v4.1 LLM | v4.2 LLM | v4.1 old | v4.2 old | v4.1 all | v4.2 all |
|---|---|---|---|---|---|---|---|---|
| AZ_DRIVER_LICENSE_NUMBER · archive_folder | 208 | 272 | 327 | 319 | 0 | 0 | 535 | 591 |
| AZ_DRIVER_LICENSE_NUMBER · campaign_code | 203 | 283 | 320 | 339 | 0 | 0 | 523 | 622 |
| AZ_DRIVER_LICENSE_NUMBER · internal_reference | 334 | 306 | 342 | 339 | 0 | 0 | 676 | 645 |
| AZ_DRIVER_LICENSE_NUMBER · licence_hyphen | 85 | 96 | 341 | 318 | 0 | 0 | 426 | 414 |
| AZ_DRIVER_LICENSE_NUMBER · licence_three_letters | 0 | 306 | 0 | 0 | 0 | 0 | 0 | 306 |
| AZ_DRIVER_LICENSE_NUMBER · licence_too_short | 87 | 97 | 324 | 329 | 0 | 0 | 411 | 426 |
| AZ_ID_CARD_NUMBER · ORDER_ID | 0 | 0 | 580 | 569 | 0 | 0 | 580 | 569 |
| AZ_ID_CARD_NUMBER · id_card_hyphen | 93 | 99 | 297 | 307 | 0 | 0 | 390 | 406 |
| AZ_ID_CARD_NUMBER · id_card_short_number | 84 | 90 | 0 | 0 | 0 | 0 | 84 | 90 |
| AZ_ID_CARD_NUMBER · id_card_too_long | 86 | 91 | 337 | 347 | 0 | 0 | 423 | 438 |
| AZ_ID_CARD_NUMBER · id_card_too_short | 91 | 91 | 328 | 301 | 0 | 0 | 419 | 392 |
| CARD_SECURITY_CODE · cvv_1_2_digits | 81 | 288 | 293 | 310 | 0 | 0 | 374 | 598 |
| CARD_SECURITY_CODE · cvv_5_digits | 305 | 391 | 354 | 356 | 0 | 0 | 659 | 747 |
| CARD_SECURITY_CODE · cvv_letters | 85 | 97 | 296 | 294 | 0 | 0 | 381 | 391 |
| CARD_SECURITY_CODE · cvv_separator | 91 | 92 | 180 | 168 | 0 | 0 | 271 | 260 |
| CARD_SECURITY_CODE · cvv_sequential_5 | 225 | 256 | 79 | 77 | 0 | 0 | 304 | 333 |
| CARD_SECURITY_CODE · door_code | 90 | 97 | 0 | 0 | 0 | 0 | 90 | 97 |
| CARD_SECURITY_CODE · policy_sequential | 84 | 91 | 298 | 290 | 0 | 0 | 382 | 381 |
| CARD_SECURITY_CODE · room_code | 93 | 98 | 0 | 0 | 0 | 0 | 93 | 98 |
| DATE · DATE_LIKE_ID | 0 | 0 | 669 | 629 | 0 | 0 | 669 | 629 |
| DATE · TIMESTAMP | 0 | 0 | 1,132 | 1,088 | 738 | 738 | 1,870 | 1,826 |
| DATE · date_bad_month | 1,250 | 1,863 | 349 | 346 | 0 | 0 | 1,599 | 2,209 |
| DATE · date_clause_number | 198 | 290 | 357 | 341 | 0 | 0 | 555 | 631 |
| DATE · date_feb_invalid | 0 | 873 | 0 | 0 | 0 | 0 | 0 | 873 |
| DATE · date_impossible_day | 1,295 | 1,837 | 327 | 341 | 0 | 0 | 1,622 | 2,178 |
| DATE · date_iso_out_of_range | 1,117 | 600 | 318 | 323 | 0 | 0 | 1,435 | 923 |
| DATE · date_month_near | 0 | 852 | 0 | 0 | 0 | 0 | 0 | 852 |
| DATE · date_version_string | 192 | 361 | 328 | 310 | 0 | 0 | 520 | 671 |
| EMAIL · EMAIL_LIKE_HANDLE | 0 | 0 | 686 | 710 | 0 | 0 | 686 | 710 |
| EMAIL · MASKED_EMAIL | 0 | 0 | 771 | 784 | 0 | 0 | 771 | 784 |
| EMAIL · OBFUSCATED_EMAIL | 0 | 0 | 728 | 720 | 0 | 0 | 728 | 720 |
| EMAIL · email_dotless_domain | 155 | 172 | 90 | 91 | 0 | 0 | 245 | 263 |
| EMAIL · email_double_at | 139 | 184 | 104 | 112 | 0 | 0 | 243 | 296 |
| EMAIL · email_localhost | 151 | 184 | 102 | 95 | 0 | 0 | 253 | 279 |
| EMAIL · email_no_at | 156 | 170 | 95 | 92 | 0 | 0 | 251 | 262 |
| IPV4_ADDRESS · IP_INVALID_OCTET | 0 | 0 | 671 | 650 | 0 | 0 | 671 | 650 |
| IPV4_ADDRESS · IP_LIKE_VERSION | 0 | 0 | 752 | 750 | 0 | 0 | 752 | 750 |
| IPV4_ADDRESS · ipv4_octet_over_255 | 92 | 69 | 307 | 315 | 0 | 0 | 399 | 384 |
| IPV4_ADDRESS · ipv4_over_255_mixed | 0 | 74 | 0 | 0 | 0 | 0 | 0 | 74 |
| IPV4_ADDRESS · ipv4_placeholder | 36 | 36 | 0 | 0 | 0 | 0 | 36 | 36 |
| IPV4_ADDRESS · ipv4_short_over_255 | 42 | 98 | 0 | 0 | 0 | 0 | 42 | 98 |
| IPV4_ADDRESS · ipv4_three_octets | 43 | 150 | 0 | 0 | 0 | 0 | 43 | 150 |
| IPV4_ADDRESS · policy_sequential_ipv4 | 0 | 42 | 0 | 0 | 0 | 0 | 0 | 42 |
| IPV6_ADDRESS · ipv6_compressed_bad | 0 | 339 | 0 | 0 | 0 | 0 | 0 | 339 |
| IPV6_ADDRESS · ipv6_non_hex | 86 | 77 | 81 | 93 | 0 | 0 | 167 | 170 |
| IPV6_ADDRESS · ipv6_triple_colon | 85 | 72 | 319 | 320 | 0 | 0 | 404 | 392 |
| IPV6_ADDRESS · ipv6_two_compressions | 79 | 67 | 91 | 99 | 0 | 0 | 170 | 166 |
| MAC_ADDRESS · MAC_LIKE_HASH | 0 | 0 | 790 | 820 | 0 | 0 | 790 | 820 |
| MAC_ADDRESS · mac_3_to_5_groups | 85 | 73 | 302 | 302 | 0 | 0 | 387 | 375 |
| MAC_ADDRESS · mac_fragment_dashed | 82 | 70 | 0 | 0 | 0 | 0 | 82 | 70 |
| MAC_ADDRESS · mac_letters_only | 0 | 110 | 0 | 0 | 0 | 0 | 0 | 110 |
| TIME · TIMESTAMP | 0 | 0 | 130 | 102 | 56 | 56 | 186 | 158 |
| TIME · policy_sequential_time | 53 | 41 | 0 | 0 | 0 | 0 | 53 | 41 |
| TIME · policy_version_time | 82 | 71 | 299 | 307 | 0 | 0 | 381 | 378 |
| TIME · time_3_digit_minutes | 87 | 82 | 350 | 333 | 0 | 0 | 437 | 415 |
| TIME · time_bad_hour | 226 | 264 | 294 | 306 | 0 | 0 | 520 | 570 |
| TIME · time_bad_minute | 224 | 256 | 305 | 307 | 0 | 0 | 529 | 563 |
| TIME · time_hour_near | 0 | 245 | 0 | 0 | 0 | 0 | 0 | 245 |
| TIME · time_line_stamp | 1,012 | 1,343 | 0 | 0 | 0 | 0 | 1,012 | 1,343 |
| TIME · time_minute_near | 0 | 248 | 0 | 0 | 0 | 0 | 0 | 248 |
| ZIPCODE · zip_shape_as_code | 92 | 67 | 79 | 77 | 0 | 0 | 171 | 144 |
| ZIPCODE · zip_shape_in_iban_field | 81 | 71 | 339 | 355 | 0 | 0 | 420 | 426 |
| ZIPCODE · zip_two_digits | 94 | 157 | 0 | 0 | 0 | 0 | 94 | 157 |
| ZIPCODE · zip_wrong_length | 541 | 727 | 322 | 346 | 0 | 0 | 863 | 1,073 |

## 3. Regex shapes anywhere in the text

| | v4.1 targeted | v4.2 targeted | v4.1 LLM | v4.2 LLM | v4.1 old | v4.2 old | v4.1 all | v4.2 all |
|---|---|---|---|---|---|---|---|---|
| hh:mm · unlabelled | 0 | 0 | 12,484 | 12,800 | 18,503 | 18,500 | 30,987 | 31,300 |
| hh:mm · labelled TIME | 950 | 2,216 | 4,239 | 4,170 | 5,444 | 5,447 | 10,633 | 11,833 |
| hh:mm · declared look-alike | 742 | 1,332 | 1,552 | 1,515 | 177 | 177 | 2,471 | 3,024 |
| hh:mm · labelled BUILDINGNUM | 0 | 0 | 0 | 0 | 14 | 14 | 14 | 14 |
| hh:mm · labelled AGE | 0 | 0 | 1 | 1 | 4 | 4 | 5 | 5 |
| hh:mm after `saat` · labelled TIME | 278 | 773 | 3,208 | 3,183 | 3,342 | 3,345 | 6,828 | 7,301 |
| hh:mm after `saat` · declared look-alike | 186 | 404 | 269 | 276 | 1 | 1 | 456 | 681 |
| hh:mm after `saat` · unlabelled | 0 | 0 | 43 | 30 | 131 | 128 | 174 | 158 |
| hh:mm after `vaxt` · labelled TIME | 279 | 352 | 768 | 731 | 1,450 | 1,450 | 2,497 | 2,533 |
| hh:mm after `vaxt` · declared look-alike | 189 | 432 | 345 | 359 | 0 | 0 | 534 | 791 |
| hh:mm after `vaxt` · unlabelled | 0 | 0 | 150 | 151 | 299 | 299 | 449 | 450 |
| hh:mm:ss · unlabelled | 0 | 0 | 26,739 | 26,600 | 35,842 | 35,842 | 62,581 | 62,442 |
| hh:mm:ss · declared look-alike | 855 | 1,136 | 331 | 327 | 608 | 608 | 1,794 | 2,071 |
| hh:mm:ss · labelled TIME | 570 | 882 | 27 | 27 | 71 | 71 | 668 | 980 |
| hh:mm:ss · labelled AGE | 0 | 0 | 1 | 3 | 9 | 9 | 10 | 12 |
| hh:mm:ss · labelled BUILDINGNUM | 0 | 0 | 3 | 3 | 0 | 0 | 3 | 3 |
| [hh:mm(:ss)] line stamp · unlabelled | 0 | 0 | 7,576 | 7,900 | 13,585 | 13,585 | 21,161 | 21,485 |
| [hh:mm(:ss)] line stamp · declared look-alike | 527 | 673 | 109 | 81 | 45 | 45 | 681 | 799 |
| [hh:mm(:ss)] line stamp · labelled BUILDINGNUM | 0 | 0 | 0 | 1 | 14 | 14 | 14 | 15 |
| [hh:mm(:ss)] line stamp · labelled AGE | 0 | 0 | 1 | 2 | 2 | 2 | 3 | 4 |
| IPv6-like (:: or 3+ colons) · labelled IPV6_ADDRESS | 1,358 | 2,272 | 2,619 | 2,592 | 1,550 | 1,550 | 5,527 | 6,414 |
| IPv6-like (:: or 3+ colons) · labelled MAC_ADDRESS | 708 | 921 | 1,560 | 1,555 | 1,459 | 1,459 | 3,727 | 3,935 |
| IPv6-like (:: or 3+ colons) · declared look-alike | 190 | 246 | 496 | 509 | 0 | 0 | 686 | 755 |
| IPv6-like (:: or 3+ colons) · unlabelled | 0 | 0 | 20 | 21 | 146 | 146 | 166 | 167 |
| IPv6-like, digit-only groups · unlabelled | 0 | 0 | 17 | 20 | 145 | 145 | 162 | 165 |
| IPv6-like, digit-only groups · labelled IPV6_ADDRESS | 1 | 4 | 6 | 5 | 0 | 0 | 7 | 9 |
| IPv6-like, digit-only groups · declared look-alike | 0 | 3 | 3 | 4 | 0 | 0 | 3 | 7 |
| ::ffff: + IPv4 · labelled IPV6_ADDRESS | 94 | 141 | 197 | 208 | 0 | 0 | 291 | 349 |
| MAC colon 6 pairs · labelled MAC_ADDRESS | 708 | 921 | 1,559 | 1,555 | 1,459 | 1,459 | 3,726 | 3,935 |
| MAC dash 6 pairs · labelled MAC_ADDRESS | 295 | 383 | 660 | 673 | 496 | 496 | 1,451 | 1,552 |
| MAC dash 6 pairs · unlabelled | 0 | 0 | 0 | 0 | 7 | 7 | 7 | 7 |
| dash pairs 3-4 (99-99-99) · declared look-alike | 109 | 90 | 118 | 114 | 0 | 0 | 227 | 204 |
| dash pairs 3-4 (99-99-99) · unlabelled | 0 | 0 | 7 | 7 | 8 | 8 | 15 | 15 |
| dotted 4 parts, all <=255 · labelled IPV4_ADDRESS | 897 | 1,557 | 2,873 | 2,811 | 3,385 | 3,385 | 7,155 | 7,753 |
| dotted 4 parts, all <=255 · labelled IPV6_ADDRESS | 94 | 141 | 197 | 208 | 0 | 0 | 291 | 349 |
| dotted 4 parts, all <=255 · declared look-alike | 0 | 42 | 0 | 0 | 0 | 0 | 0 | 42 |
| dotted 4 parts, all <=255 · unlabelled | 0 | 0 | 4 | 4 | 6 | 6 | 10 | 10 |
| dotted 4 parts, one-digit octets >=2 · labelled IPV4_ADDRESS | 85 | 154 | 5 | 4 | 3 | 3 | 93 | 161 |
| dotted 4 parts, one-digit octets >=2 · unlabelled | 0 | 0 | 3 | 3 | 93 | 93 | 96 | 96 |
| dotted 4 parts, one-digit octets >=2 · declared look-alike | 19 | 78 | 8 | 9 | 0 | 0 | 27 | 87 |
| dotted 3 parts (99.99.99) · labelled DATE | 0 | 0 | 456 | 464 | 610 | 610 | 1,066 | 1,074 |
| dotted 3 parts (99.99.99) · unlabelled | 0 | 0 | 189 | 183 | 865 | 865 | 1,054 | 1,048 |
| dotted 3 parts (99.99.99) · declared look-alike | 239 | 433 | 551 | 540 | 1 | 1 | 791 | 974 |
| dotted 5 parts · declared look-alike | 28 | 19 | 0 | 0 | 0 | 0 | 28 | 19 |
| email-like a@b.c · labelled EMAIL | 1,202 | 1,533 | 16,138 | 16,219 | 23,517 | 23,517 | 40,857 | 41,269 |
| email-like a@b.c · declared look-alike | 69 | 99 | 47 | 51 | 0 | 0 | 116 | 150 |
| email-like a@b.c · unlabelled | 0 | 0 | 0 | 0 | 4 | 4 | 4 | 4 |
| email-like, local part with dot · labelled EMAIL | 790 | 1,011 | 9,305 | 9,307 | 13,501 | 13,501 | 23,596 | 23,819 |
| email-like, local part with hyphen · labelled EMAIL | 14 | 22 | 650 | 640 | 899 | 899 | 1,563 | 1,561 |
| 2 letters + 6 digits · labelled AZ_DRIVER_LICENSE_NUMBER | 3,653 | 5,270 | 3,296 | 3,295 | 2,400 | 2,400 | 9,349 | 10,965 |
| 2 letters + 6 digits · declared look-alike | 0 | 0 | 49 | 55 | 0 | 0 | 49 | 55 |
| 2 letters + 6 digits · unlabelled | 0 | 0 | 1 | 1 | 12 | 12 | 13 | 13 |
| 2 letters + 6 digits after `sürücü` · labelled AZ_DRIVER_LICENSE_NUMBER | 988 | 1,433 | 2,095 | 2,136 | 1,306 | 1,306 | 4,389 | 4,875 |
| 2 letters + 6 digits after `vəsiqə` · labelled AZ_DRIVER_LICENSE_NUMBER | 321 | 475 | 339 | 315 | 311 | 311 | 971 | 1,101 |
| 2 letters + 6 digits after `vəsi̇qə` · labelled AZ_DRIVER_LICENSE_NUMBER | 0 | 64 | 0 | 0 | 3 | 3 | 3 | 67 |
| 2 letters + 6 digits after `şəxsiyyət` · labelled AZ_DRIVER_LICENSE_NUMBER | 155 | 208 | 32 | 33 | 15 | 15 | 202 | 256 |
| 2 letters + 7 digits · labelled AZ_ID_CARD_NUMBER | 4,255 | 5,939 | 2,610 | 2,552 | 1,681 | 1,681 | 8,546 | 10,172 |
| 2 letters + 7 digits · unlabelled | 0 | 0 | 3 | 3 | 328 | 328 | 331 | 331 |
| 2 letters + 7 digits · declared look-alike | 0 | 0 | 156 | 162 | 0 | 0 | 156 | 162 |
| 2 letters + 7 digits after `sürücü` · labelled AZ_ID_CARD_NUMBER | 169 | 216 | 22 | 21 | 4 | 4 | 195 | 241 |
| 2 letters + 7 digits after `vəsiqə` · labelled AZ_ID_CARD_NUMBER | 471 | 659 | 299 | 275 | 250 | 250 | 1,020 | 1,184 |
| 2 letters + 7 digits after `vəsi̇qə` · labelled AZ_ID_CARD_NUMBER | 0 | 79 | 0 | 0 | 0 | 0 | 0 | 79 |
| 2 letters + 7 digits after `şəxsiyyət` · labelled AZ_ID_CARD_NUMBER | 957 | 1,229 | 1,662 | 1,643 | 810 | 810 | 3,429 | 3,682 |
| 3 digits · labelled TELEPHONENUM | 2,130 | 2,574 | 13,592 | 13,675 | 19,690 | 19,690 | 35,412 | 35,939 |
| 3 digits · unlabelled | 0 | 644 | 5,086 | 5,201 | 12,229 | 12,229 | 17,315 | 18,074 |
| 3 digits · labelled CARD_SECURITY_CODE | 751 | 1,208 | 1,601 | 1,601 | 1,794 | 1,794 | 4,146 | 4,603 |
| 3 digits · labelled BUILDINGNUM | 92 | 286 | 1,731 | 1,693 | 1,867 | 1,867 | 3,690 | 3,846 |
| 3 digits · declared look-alike | 1,541 | 1,636 | 1,367 | 1,386 | 0 | 0 | 2,908 | 3,022 |
| 3 digits · labelled IBAN | 18 | 21 | 81 | 81 | 121 | 121 | 220 | 223 |
| 3 digits · labelled STREET | 2 | 0 | 4 | 5 | 3 | 3 | 9 | 8 |
| 3 digits · labelled URL | 6 | 10 | 0 | 0 | 0 | 0 | 6 | 10 |
| 3 digits · labelled PRIVATE_KEY | 0 | 2 | 2 | 2 | 1 | 1 | 3 | 5 |
| 3 digits after `cvc` · labelled CARD_SECURITY_CODE | 123 | 210 | 28 | 32 | 56 | 56 | 207 | 298 |
| 3 digits after `cvc` · declared look-alike | 2 | 2 | 3 | 1 | 0 | 0 | 5 | 3 |
| 3 digits after `cvc` · unlabelled | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 2 |
| 3 digits after `cvv` · labelled CARD_SECURITY_CODE | 456 | 664 | 395 | 403 | 365 | 365 | 1,216 | 1,432 |
| 3 digits after `cvv` · labelled TELEPHONENUM | 6 | 16 | 3 | 4 | 5 | 5 | 14 | 25 |
| 3 digits after `cvv` · unlabelled | 0 | 0 | 2 | 2 | 9 | 9 | 11 | 11 |
| 3 digits after `cvv` · declared look-alike | 8 | 9 | 2 | 2 | 0 | 0 | 10 | 11 |
| 3 digits after `təhlükəsizlik kodu` · labelled CARD_SECURITY_CODE | 116 | 259 | 1,096 | 1,086 | 1,171 | 1,171 | 2,383 | 2,516 |
| 3 digits after `təhlükəsizlik kodu` · unlabelled | 0 | 0 | 1 | 1 | 2 | 2 | 3 | 3 |
| 3 digits after `təhlükəsizlik kodu` · labelled TELEPHONENUM | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 2 |
| 3 digits after `təhlükəsizlik kodu` · declared look-alike | 1 | 0 | 1 | 1 | 0 | 0 | 2 | 1 |
| 4 digits · unlabelled | 0 | 118 | 13,211 | 13,353 | 26,579 | 26,579 | 39,790 | 40,050 |
| 4 digits · labelled DATE | 394 | 675 | 5,863 | 5,907 | 6,687 | 6,687 | 12,944 | 13,269 |
| 4 digits · labelled PAYMENT_CARD_NUMBER | 2,953 | 3,967 | 3,987 | 4,006 | 5,442 | 5,442 | 12,382 | 13,415 |
| 4 digits · labelled IBAN | 1,165 | 1,674 | 3,209 | 3,227 | 4,506 | 4,506 | 8,880 | 9,407 |
| 4 digits · declared look-alike | 867 | 936 | 1,589 | 1,548 | 1 | 1 | 2,457 | 2,485 |
| 4 digits · labelled ZIPCODE | 553 | 688 | 334 | 331 | 0 | 0 | 887 | 1,019 |
| 4 digits · labelled CARD_SECURITY_CODE | 152 | 224 | 262 | 251 | 286 | 286 | 700 | 761 |
| 4 digits · labelled TELEPHONENUM | 30 | 25 | 0 | 0 | 0 | 0 | 30 | 25 |
| 4 digits · labelled URL | 6 | 6 | 0 | 0 | 0 | 0 | 6 | 6 |
| 4 digits · labelled STREET | 1 | 0 | 1 | 1 | 0 | 0 | 2 | 1 |
| 4 digits after `cvc` · declared look-alike | 23 | 16 | 48 | 44 | 0 | 0 | 71 | 60 |
| 4 digits after `cvc` · labelled CARD_SECURITY_CODE | 24 | 34 | 11 | 11 | 18 | 18 | 53 | 63 |
| 4 digits after `cvc` · labelled PAYMENT_CARD_NUMBER | 10 | 4 | 0 | 0 | 0 | 0 | 10 | 4 |
| 4 digits after `cvc` · unlabelled | 0 | 0 | 4 | 3 | 0 | 0 | 4 | 3 |
| 4 digits after `cvc` · labelled IBAN | 1 | 5 | 0 | 0 | 0 | 0 | 1 | 5 |
| 4 digits after `cvv` · declared look-alike | 58 | 58 | 193 | 195 | 0 | 0 | 251 | 253 |
| 4 digits after `cvv` · labelled CARD_SECURITY_CODE | 93 | 133 | 59 | 68 | 54 | 54 | 206 | 255 |
| 4 digits after `cvv` · labelled PAYMENT_CARD_NUMBER | 15 | 35 | 4 | 4 | 0 | 0 | 19 | 39 |
| 4 digits after `cvv` · unlabelled | 0 | 0 | 7 | 6 | 1 | 1 | 8 | 7 |
| 4 digits after `cvv` · labelled DATE | 1 | 0 | 1 | 1 | 0 | 0 | 2 | 1 |
| 4 digits after `indeks` · labelled ZIPCODE | 62 | 70 | 13 | 17 | 0 | 0 | 75 | 87 |
| 4 digits after `indeks` · unlabelled | 0 | 0 | 7 | 5 | 13 | 13 | 20 | 18 |
| 4 digits after `indeks` · labelled PAYMENT_CARD_NUMBER | 11 | 9 | 1 | 1 | 1 | 1 | 13 | 11 |
| 4 digits after `indeks` · declared look-alike | 0 | 0 | 3 | 3 | 0 | 0 | 3 | 3 |
| 4 digits after `indeks` · labelled IBAN | 0 | 4 | 0 | 0 | 1 | 1 | 1 | 5 |
| 4 digits after `indeks` · labelled DATE | 0 | 1 | 1 | 1 | 0 | 0 | 1 | 2 |
| 4 digits after `i̇ndeks` · labelled ZIPCODE | 17 | 10 | 0 | 2 | 0 | 0 | 17 | 12 |
| 4 digits after `i̇ndeks` · labelled PAYMENT_CARD_NUMBER | 4 | 7 | 0 | 0 | 0 | 0 | 4 | 7 |
| 4 digits after `i̇ndeks` · declared look-alike | 3 | 5 | 0 | 0 | 0 | 0 | 3 | 5 |
| 4 digits after `i̇ndeks` · unlabelled | 0 | 0 | 0 | 1 | 2 | 2 | 2 | 3 |
| 4 digits after `poçt` · labelled ZIPCODE | 94 | 140 | 281 | 274 | 0 | 0 | 375 | 414 |
| 4 digits after `poçt` · unlabelled | 0 | 0 | 20 | 34 | 13 | 13 | 33 | 47 |
| 4 digits after `poçt` · labelled DATE | 1 | 1 | 8 | 7 | 0 | 0 | 9 | 8 |
| 4 digits after `poçt` · labelled PAYMENT_CARD_NUMBER | 3 | 3 | 3 | 6 | 0 | 0 | 6 | 9 |
| AZ + 4 digits · labelled ZIPCODE | 1,052 | 1,425 | 4,727 | 4,742 | 7,049 | 7,049 | 12,828 | 13,216 |
| AZ + 4 digits · unlabelled | 0 | 0 | 16 | 17 | 1,915 | 1,915 | 1,931 | 1,932 |
| AZ + 4 digits · declared look-alike | 173 | 138 | 418 | 432 | 0 | 0 | 591 | 570 |
| AZ + 4 digits after `indeks` · labelled ZIPCODE | 171 | 210 | 207 | 218 | 266 | 266 | 644 | 694 |
| AZ + 4 digits after `indeks` · declared look-alike | 43 | 34 | 1 | 1 | 0 | 0 | 44 | 35 |
| AZ + 4 digits after `indeks` · unlabelled | 0 | 0 | 0 | 0 | 17 | 17 | 17 | 17 |
| AZ + 4 digits after `i̇ndeks` · labelled ZIPCODE | 92 | 119 | 10 | 9 | 69 | 69 | 171 | 197 |
| AZ + 4 digits after `i̇ndeks` · unlabelled | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 2 |
| AZ + 4 digits after `poçt` · labelled ZIPCODE | 223 | 363 | 2,033 | 2,059 | 3,896 | 3,896 | 6,152 | 6,318 |
| AZ + 4 digits after `poçt` · declared look-alike | 12 | 13 | 0 | 0 | 0 | 0 | 12 | 13 |
| dd.mm.yyyy · labelled DATE | 446 | 787 | 12,369 | 12,325 | 19,576 | 19,576 | 32,391 | 32,688 |
| dd.mm.yyyy · unlabelled | 0 | 0 | 2,360 | 2,387 | 1,718 | 1,718 | 4,078 | 4,105 |
| dd.mm.yyyy · declared look-alike | 1,578 | 3,266 | 1,328 | 1,280 | 33 | 33 | 2,939 | 4,579 |
| dd.mm.yyyy after `tarix` · labelled DATE | 255 | 432 | 7,696 | 7,712 | 10,569 | 10,569 | 18,520 | 18,713 |
| dd.mm.yyyy after `tarix` · declared look-alike | 1,326 | 2,704 | 429 | 438 | 8 | 8 | 1,763 | 3,150 |
| dd.mm.yyyy after `tarix` · unlabelled | 0 | 0 | 429 | 419 | 179 | 179 | 608 | 598 |
| dd.mm.yyyy after `tari̇x` · labelled DATE | 0 | 0 | 21 | 23 | 96 | 96 | 117 | 119 |
| dd.mm.yyyy after `tari̇x` · unlabelled | 0 | 0 | 6 | 7 | 4 | 4 | 10 | 11 |
| 5 digits · unlabelled | 0 | 0 | 975 | 1,062 | 2,218 | 2,218 | 3,193 | 3,280 |
| 5 digits · declared look-alike | 571 | 672 | 838 | 824 | 0 | 0 | 1,409 | 1,496 |
| 5 digits · labelled PAYMENT_CARD_NUMBER | 11 | 22 | 87 | 86 | 119 | 119 | 217 | 227 |
| 5 digits · labelled URL | 14 | 12 | 38 | 38 | 43 | 43 | 95 | 93 |
| 5 digits after `cvc` · declared look-alike | 109 | 101 | 67 | 66 | 0 | 0 | 176 | 167 |
| 5 digits after `cvv` · declared look-alike | 315 | 447 | 273 | 270 | 0 | 0 | 588 | 717 |
| 5 digits after `cvv` · unlabelled | 0 | 0 | 1 | 1 | 1 | 1 | 2 | 2 |
| 5 digits after `indeks` · unlabelled | 0 | 0 | 0 | 0 | 6 | 6 | 6 | 6 |
| 5 digits after `indeks` · declared look-alike | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 3 |
| 5 digits after `i̇ndeks` · declared look-alike | 2 | 6 | 0 | 0 | 0 | 0 | 2 | 6 |
| 5 digits after `i̇ndeks` · unlabelled | 0 | 0 | 1 | 0 | 2 | 2 | 3 | 2 |
| 5 digits after `poçt` · unlabelled | 0 | 0 | 6 | 4 | 2 | 2 | 8 | 6 |
| 5 digits after `poçt` · declared look-alike | 2 | 1 | 0 | 0 | 0 | 0 | 2 | 1 |
| AZ + 1-3 digits · labelled IBAN | 279 | 458 | 411 | 420 | 587 | 587 | 1,277 | 1,465 |
| AZ + 1-3 digits · declared look-alike | 396 | 533 | 170 | 177 | 0 | 0 | 566 | 710 |
| AZ + 1-3 digits · unlabelled | 0 | 0 | 5 | 6 | 8 | 8 | 13 | 14 |
| AZ + 1-3 digits after `indeks` · declared look-alike | 34 | 55 | 60 | 70 | 0 | 0 | 94 | 125 |
| AZ + 1-3 digits after `i̇ndeks` · declared look-alike | 56 | 82 | 1 | 1 | 0 | 0 | 57 | 83 |
| AZ + 1-3 digits after `poçt` · declared look-alike | 76 | 148 | 54 | 52 | 0 | 0 | 130 | 200 |
| AZ + 1-3 digits after `poçt` · labelled IBAN | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 6 |
| AZ + 1-3 digits after `poçt` · unlabelled | 0 | 0 | 1 | 1 | 1 | 1 | 2 | 2 |
| AZ + 5 digits · declared look-alike | 145 | 194 | 61 | 67 | 0 | 0 | 206 | 261 |
| AZ + 5 digits · unlabelled | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 2 |
| AZ + 5 digits after `indeks` · declared look-alike | 11 | 20 | 20 | 24 | 0 | 0 | 31 | 44 |
| AZ + 5 digits after `i̇ndeks` · declared look-alike | 23 | 35 | 0 | 0 | 0 | 0 | 23 | 35 |
| AZ + 5 digits after `poçt` · declared look-alike | 31 | 43 | 19 | 22 | 0 | 0 | 50 | 65 |
| hh:mm, hour > 23 or minute > 59 · declared look-alike | 450 | 1,013 | 599 | 613 | 0 | 0 | 1,049 | 1,626 |
| hh:mm, hour > 23 or minute > 59 · labelled TIME | 0 | 79 | 2 | 2 | 1 | 1 | 3 | 82 |
| hh:mm, hour > 23 or minute > 59 · unlabelled | 0 | 0 | 16 | 7 | 1 | 1 | 17 | 8 |
| hh:mm, hour > 23 or minute > 59 after `saat` · declared look-alike | 186 | 404 | 267 | 273 | 0 | 0 | 453 | 677 |
| hh:mm, hour > 23 or minute > 59 after `saat` · labelled TIME | 0 | 79 | 1 | 1 | 0 | 0 | 1 | 80 |
| hh:mm, hour > 23 or minute > 59 after `saat` · unlabelled | 0 | 0 | 3 | 2 | 0 | 0 | 3 | 2 |
| hh:mm, hour > 23 or minute > 59 after `vaxt` · declared look-alike | 188 | 432 | 326 | 338 | 0 | 0 | 514 | 770 |
| dd.mm.yyyy, month > 12 · declared look-alike | 644 | 1,394 | 162 | 153 | 0 | 0 | 806 | 1,547 |
| dd.mm.yyyy, month > 12 · unlabelled | 0 | 0 | 4 | 3 | 2 | 2 | 6 | 5 |
| dd.mm.yyyy, month > 12 after `tarix` · declared look-alike | 551 | 1,165 | 116 | 115 | 0 | 0 | 667 | 1,280 |
| dd.mm.yyyy, month > 12 after `tarix` · unlabelled | 0 | 0 | 2 | 2 | 1 | 1 | 3 | 3 |
| 30/31.02.yyyy · declared look-alike | 147 | 617 | 48 | 47 | 0 | 0 | 195 | 664 |
| 30/31.02.yyyy after `tarix` · declared look-alike | 122 | 465 | 35 | 37 | 0 | 0 | 157 | 502 |
