# Shapes in the training data: v4 against v4.1

Sources: targeted builder; LLM batches b1-b6; old corpus (`_old`).

| documents | v4 | v4.1 |
|---|---|---|
| targeted | 19,957 | 22,612 |
| LLM b1 | 3,801 | 3,765 |
| LLM b2 | 4,268 | 4,240 |
| LLM b3 | 4,329 | 4,314 |
| LLM b4 | 4,354 | 4,328 |
| LLM b5 | 15,626 | 15,529 |
| LLM b6 | 17,485 | 17,413 |
| old corpus | 63,069 | 63,069 |

## 1. Labelled values

| | v4 targeted | v4.1 targeted | v4 LLM | v4.1 LLM | v4 old | v4.1 old | v4 all | v4.1 all |
|---|---|---|---|---|---|---|---|---|
| AZ_DRIVER_LICENSE_NUMBER | 2,816 | 3,653 | 3,316 | 3,296 | 2,400 | 2,400 | 8,532 | 9,349 |
| AZ_ID_CARD_NUMBER | 3,425 | 4,517 | 3,921 | 3,895 | 3,235 | 3,235 | 10,581 | 11,647 |
| CARD_SECURITY_CODE | 1,174 | 1,224 | 2,195 | 2,174 | 2,329 | 2,329 | 5,698 | 5,727 |
| DATE | 1,245 | 1,353 | 27,207 | 27,019 | 39,549 | 39,549 | 68,001 | 67,921 |
| EMAIL | 1,102 | 1,202 | 16,336 | 16,138 | 23,517 | 23,517 | 40,955 | 40,857 |
| IPV4_ADDRESS | 749 | 911 | 3,061 | 3,084 | 3,823 | 3,823 | 7,633 | 7,818 |
| IPV6_ADDRESS | 769 | 1,358 | 2,667 | 2,624 | 1,553 | 1,553 | 4,989 | 5,535 |
| MAC_ADDRESS | 901 | 1,249 | 2,821 | 2,788 | 1,960 | 1,960 | 5,682 | 5,997 |
| TIME | 1,332 | 1,520 | 4,220 | 4,284 | 5,584 | 5,584 | 11,136 | 11,388 |
| ZIPCODE | 1,253 | 1,687 | 5,179 | 5,099 | 7,049 | 7,049 | 13,481 | 13,835 |

### By shape

| | v4 targeted | v4.1 targeted | v4 LLM | v4.1 LLM | v4 old | v4.1 old | v4 all | v4.1 all |
|---|---|---|---|---|---|---|---|---|
| AZ_DRIVER_LICENSE_NUMBER · `aa999999` | 2,816 | 3,653 | 3,316 | 3,296 | 2,400 | 2,400 | 8,532 | 9,349 |
| AZ_ID_CARD_NUMBER · `aa9999999` | 3,154 | 4,255 | 2,616 | 2,610 | 1,681 | 1,681 | 7,451 | 8,546 |
| AZ_ID_CARD_NUMBER · `aaa9999999` | 271 | 262 | 1,305 | 1,285 | 1,554 | 1,554 | 3,130 | 3,101 |
| CARD_SECURITY_CODE · `999` | 863 | 917 | 1,750 | 1,709 | 2,012 | 2,012 | 4,625 | 4,638 |
| CARD_SECURITY_CODE · `9999` | 178 | 178 | 283 | 289 | 316 | 316 | 777 | 783 |
| CARD_SECURITY_CODE · `99-9` | 86 | 78 | 93 | 102 | 0 | 0 | 179 | 180 |
| CARD_SECURITY_CODE · `9-99` | 27 | 22 | 67 | 71 | 0 | 0 | 94 | 93 |
| CARD_SECURITY_CODE · `99-99` | 20 | 29 | 0 | 0 | 0 | 0 | 20 | 29 |
| DATE · `99.99.9999` | 431 | 449 | 12,787 | 12,604 | 20,331 | 20,331 | 33,549 | 33,384 |
| DATE · `9999-99-99` | 401 | 446 | 3,365 | 3,400 | 4,275 | 4,275 | 8,041 | 8,121 |
| DATE · `99 aaaaaa 9999` | 123 | 118 | 2,395 | 2,417 | 3,028 | 3,028 | 5,546 | 5,563 |
| DATE · `99 aaaa 9999` | 63 | 96 | 1,220 | 1,229 | 3,395 | 3,395 | 4,678 | 4,720 |
| DATE · `99 aaa 9999` | 25 | 27 | 991 | 993 | 2,604 | 2,604 | 3,620 | 3,624 |
| DATE · `99/99/9999` | 0 | 0 | 1,940 | 1,945 | 914 | 914 | 2,854 | 2,859 |
| DATE · `99 aaaaaaa 9999` | 33 | 24 | 652 | 639 | 1,279 | 1,279 | 1,964 | 1,942 |
| DATE · `99 aaaaaaaa 9999` | 25 | 27 | 418 | 411 | 944 | 944 | 1,387 | 1,382 |
| DATE · `99.99.99` | 0 | 0 | 502 | 464 | 648 | 648 | 1,150 | 1,112 |
| DATE · `99.9.9999` | 0 | 0 | 409 | 407 | 595 | 595 | 1,004 | 1,002 |
| DATE · `9 aaaaaa 9999` | 46 | 52 | 584 | 560 | 301 | 301 | 931 | 913 |
| DATE · `99 aaaaa 9999` | 33 | 21 | 246 | 259 | 374 | 374 | 653 | 654 |
| DATE · `9 aaaa 9999` | 25 | 33 | 354 | 362 | 191 | 191 | 570 | 586 |
| DATE · `9.9.9999` | 0 | 0 | 143 | 138 | 218 | 218 | 361 | 356 |
| DATE · `9 aaa 9999` | 8 | 18 | 136 | 141 | 57 | 57 | 201 | 216 |
| DATE · `9 aaaaa 9999` | 11 | 18 | 125 | 122 | 68 | 68 | 204 | 208 |
| DATE · `9 aaaaaaa 9999` | 11 | 10 | 121 | 129 | 58 | 58 | 190 | 197 |
| DATE · `9 aaaaaaaa 9999` | 10 | 14 | 130 | 112 | 57 | 57 | 197 | 183 |
| DATE · `9.99.9999` | 0 | 0 | 60 | 63 | 92 | 92 | 152 | 155 |
| DATE · `aaaaa, 99 aaaaaa 9999` | 0 | 0 | 18 | 20 | 0 | 0 | 18 | 20 |
| DATE · `aaaaa, 99 aaaa 9999` | 0 | 0 | 15 | 22 | 0 | 0 | 15 | 22 |
| DATE · `99 aaaaaa 9999, aaaaa` | 0 | 0 | 15 | 18 | 0 | 0 | 15 | 18 |
| DATE · `aaaa, 99 aaaaaa 9999` | 0 | 0 | 16 | 17 | 0 | 0 | 16 | 17 |
| DATE · `99 aaaaaa 9999, aaaaaaaa aaaaaa` | 0 | 0 | 14 | 17 | 0 | 0 | 14 | 17 |
| DATE · `99 aaaaaa 9999, aaaaa aaaaaa` | 0 | 0 | 14 | 14 | 0 | 0 | 14 | 14 |
| DATE · `aaaaaaaa, 99 aaaaaa 9999` | 0 | 0 | 16 | 11 | 0 | 0 | 16 | 11 |
| DATE · `aaaa, 99 aaaa 9999` | 0 | 0 | 12 | 14 | 0 | 0 | 12 | 14 |
| DATE · `99 aaaaaa 9999, aaaa` | 0 | 0 | 13 | 12 | 0 | 0 | 13 | 12 |
| DATE · `aaaaa aaaaaa, 99 aaaaaa 9999` | 0 | 0 | 10 | 14 | 0 | 0 | 10 | 14 |
| DATE · `aaaaa, 9 aaaaaa 9999` | 0 | 0 | 12 | 12 | 0 | 0 | 12 | 12 |
| DATE · `99 aaaa 9999, aaaaa` | 0 | 0 | 11 | 12 | 0 | 0 | 11 | 12 |
| DATE · `99-99-9999` | 0 | 0 | 6 | 5 | 6 | 6 | 12 | 11 |
| DATE · `aaaaaaaa aaaaaa, 99 aaaaaa 9999` | 0 | 0 | 11 | 11 | 0 | 0 | 11 | 11 |
| DATE · `9 aaaaaa 9999, aaaaa` | 0 | 0 | 10 | 9 | 0 | 0 | 10 | 9 |
| DATE · `aaaa aaaaaa, 99 aaaaaa 9999` | 0 | 0 | 9 | 8 | 0 | 0 | 9 | 8 |
| DATE · `99  aaaa 9999` | 0 | 0 | 2 | 2 | 6 | 6 | 8 | 8 |
| DATE · `9 aaaaaa 9999, aaaa aaaaaa` | 0 | 0 | 9 | 6 | 0 | 0 | 9 | 6 |
| DATE · `aaaaa, 99 aaaaaaa 9999` | 0 | 0 | 6 | 9 | 0 | 0 | 6 | 9 |
| DATE · `9 aaaa 9999, aaaaa aaaaaa` | 0 | 0 | 8 | 6 | 0 | 0 | 8 | 6 |
| DATE · `9 aaaaaa 9999, aaaaa aaaaaa` | 0 | 0 | 7 | 7 | 0 | 0 | 7 | 7 |
| DATE · `99 aaaa 9999, aaaaaaaa` | 0 | 0 | 7 | 7 | 0 | 0 | 7 | 7 |
| DATE · `9999/99/99` | 0 | 0 | 2 | 2 | 5 | 5 | 7 | 7 |
| DATE · `aaaa aaaaaa, 99 aaaa 9999` | 0 | 0 | 8 | 6 | 0 | 0 | 8 | 6 |
| DATE · `aaaaa aaaaaa, 99 aaaa 9999` | 0 | 0 | 6 | 8 | 0 | 0 | 6 | 8 |
| DATE · `aaaaaaaa aaaaaa, 9 aaaaaa 9999` | 0 | 0 | 8 | 6 | 0 | 0 | 8 | 6 |
| DATE · `99 aaaa 9999, aaaa aaaaaa` | 0 | 0 | 5 | 7 | 0 | 0 | 5 | 7 |
| DATE · `aaaa aaaaaa, 9 aaaaaa 9999` | 0 | 0 | 7 | 5 | 0 | 0 | 7 | 5 |
| DATE · `99  aaa 9999` | 0 | 0 | 2 | 1 | 4 | 4 | 6 | 5 |
| DATE · `99  aaaaaa 9999` | 0 | 0 | 0 | 1 | 5 | 5 | 5 | 6 |
| DATE · `99 aaaaaa 9999, aaaa aaaaaa` | 0 | 0 | 6 | 5 | 0 | 0 | 6 | 5 |
| DATE · `99.99.999` | 0 | 0 | 5 | 6 | 0 | 0 | 5 | 6 |
| DATE · `aaaa, 99 aaa 9999` | 0 | 0 | 7 | 4 | 0 | 0 | 7 | 4 |
| DATE · `9 aaaa 9999, aaaaaaaa aaaaaa` | 0 | 0 | 5 | 5 | 0 | 0 | 5 | 5 |
| DATE · `99	aaaaaa 9999` | 0 | 0 | 1 | 1 | 4 | 4 | 5 | 5 |
| DATE · `99 aaaa 9999, aaaaa aaaaaa` | 0 | 0 | 4 | 6 | 0 | 0 | 4 | 6 |
| DATE · `99 aaaaa 9999, aaaaa` | 0 | 0 | 6 | 4 | 0 | 0 | 6 | 4 |
| DATE · `99 aaaaaa  9999` | 0 | 0 | 1 | 1 | 4 | 4 | 5 | 5 |
| DATE · `99 aaaaaaa 9999, aaaaa` | 0 | 0 | 5 | 5 | 0 | 0 | 5 | 5 |
| DATE · `9999-99–99` | 0 | 0 | 3 | 3 | 2 | 2 | 5 | 5 |
| DATE · `aaaaa, 99 aaaaa 9999` | 0 | 0 | 4 | 6 | 0 | 0 | 4 | 6 |
| DATE · `aaaaaaaa aaaaaa, 99 aaaa 9999` | 0 | 0 | 5 | 5 | 0 | 0 | 5 | 5 |
| DATE · `9 aaaa 9999, aaaa aaaaaa` | 0 | 0 | 5 | 4 | 0 | 0 | 5 | 4 |
| DATE · `99 aaaaaa	9999` | 0 | 0 | 4 | 3 | 1 | 1 | 5 | 4 |
| DATE · `99 aaaaaa 9999, aaaaaaaa` | 0 | 0 | 5 | 4 | 0 | 0 | 5 | 4 |
| DATE · `99 aaaa 9999` | 0 | 0 | 4 | 5 | 0 | 0 | 4 | 5 |
| DATE · `aaaaa aaaaaa, 9 aaaaaa 9999` | 0 | 0 | 4 | 5 | 0 | 0 | 4 | 5 |
| DATE · `aaaaa, 9 aaaa 9999` | 0 | 0 | 5 | 4 | 0 | 0 | 5 | 4 |
| DATE · `aaaaaaaa, 9 aaaaaa 9999` | 0 | 0 | 5 | 4 | 0 | 0 | 5 | 4 |
| DATE · `9 aaaaa 9999, aaaaaaaa` | 0 | 0 | 4 | 4 | 0 | 0 | 4 | 4 |
| DATE · `9 aaaaaaa 9999, aaaaa` | 0 | 0 | 4 | 4 | 0 | 0 | 4 | 4 |
| DATE · `9 aaaaaaaa 9999, aaaaaaaa` | 0 | 0 | 4 | 4 | 0 | 0 | 4 | 4 |
| DATE · `99   aaaaaa 9999` | 0 | 0 | 1 | 1 | 3 | 3 | 4 | 4 |
| DATE · `99 aaaa 9999, aaaaaaaa aaaaaa` | 0 | 0 | 4 | 4 | 0 | 0 | 4 | 4 |
| DATE · `99 aaa 9999` | 0 | 0 | 2 | 2 | 2 | 2 | 4 | 4 |
| DATE · `9999–99-99` | 0 | 0 | 4 | 4 | 0 | 0 | 4 | 4 |
| DATE · `99 aaa 9999` | 0 | 0 | 0 | 0 | 4 | 4 | 4 | 4 |
| DATE · `99 aaaa 9999` | 0 | 0 | 0 | 0 | 4 | 4 | 4 | 4 |
| DATE · `aaaaaaaa, 9 aaaa 9999` | 0 | 0 | 4 | 4 | 0 | 0 | 4 | 4 |
| DATE · `aaaaaaaa, 99 aaaa 9999` | 0 | 0 | 4 | 4 | 0 | 0 | 4 | 4 |
| DATE · `9 aaaaaa 9999, aaaaaaaa` | 0 | 0 | 3 | 4 | 0 | 0 | 3 | 4 |
| DATE · `99 aaa  9999` | 0 | 0 | 1 | 0 | 3 | 3 | 4 | 3 |
| DATE · `99 aaaaaa, 9999` | 0 | 0 | 4 | 3 | 0 | 0 | 4 | 3 |
| DATE · `99 aaaaaaa 9999, aaaaaaaa` | 0 | 0 | 4 | 3 | 0 | 0 | 4 | 3 |
| DATE · `99.99.a999` | 0 | 0 | 2 | 3 | 1 | 1 | 3 | 4 |
| DATE · `aaaaa, 99 aaa 9999` | 0 | 0 | 3 | 4 | 0 | 0 | 3 | 4 |
| DATE · `9 aaaa 9999, aaaaa` | 0 | 0 | 3 | 3 | 0 | 0 | 3 | 3 |
| DATE · `9 aaaaa 9999, aaaa` | 0 | 0 | 3 | 3 | 0 | 0 | 3 | 3 |
| DATE · `9/999/9999` | 0 | 0 | 1 | 1 | 2 | 2 | 3 | 3 |
| DATE · `99	aaaaaaaa 9999` | 0 | 0 | 2 | 2 | 1 | 1 | 3 | 3 |
| DATE · `99 aaaa	9999` | 0 | 0 | 1 | 1 | 2 | 2 | 3 | 3 |
| DATE · `99 aaaa  9999` | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 3 |
| DATE · `99 aaaa 9999, aaaa` | 0 | 0 | 3 | 3 | 0 | 0 | 3 | 3 |
| DATE · `99 aaaaa 9999, aaaaaaaa aaaaaa` | 0 | 0 | 3 | 3 | 0 | 0 | 3 | 3 |
| DATE · `99 aaaaaa   9999` | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 3 |
| DATE · `99 aaaaaaaa 9999, aaaaaaaa aaaaaa` | 0 | 0 | 3 | 3 | 0 | 0 | 3 | 3 |
| DATE · `99.a9.9999` | 0 | 0 | 2 | 2 | 1 | 1 | 3 | 3 |
| DATE · `99 aaaaaa 9999` | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 3 |
| DATE · `aaaa aaaaaa, 9 aaaaaaaa 9999` | 0 | 0 | 2 | 4 | 0 | 0 | 2 | 4 |
| DATE · `aaaaa aaaaaa, 9 aaaa 9999` | 0 | 0 | 4 | 2 | 0 | 0 | 4 | 2 |
| DATE · `aaaaa aaaaaa, 99 aaaaaaa 9999` | 0 | 0 | 2 | 4 | 0 | 0 | 2 | 4 |
| DATE · `aaaaaaaa, 99 aaaaaaa 9999` | 0 | 0 | 4 | 2 | 0 | 0 | 4 | 2 |
| DATE · `9 aaa 9999, aaaaa` | 0 | 0 | 1 | 4 | 0 | 0 | 1 | 4 |
| DATE · `9 aaa 9999, aaaaaaaa` | 0 | 0 | 2 | 3 | 0 | 0 | 2 | 3 |
| DATE · `9 aaaa 9999, aaaaaaaa` | 0 | 0 | 2 | 3 | 0 | 0 | 2 | 3 |
| DATE · `99 aaaaa 9999, aaaa` | 0 | 0 | 3 | 2 | 0 | 0 | 3 | 2 |
| DATE · `99 aaaaaaa 9999, aaaaa aaaaaa` | 0 | 0 | 2 | 3 | 0 | 0 | 2 | 3 |
| DATE · `99 aaaaaaaa 9999, aaaa` | 0 | 0 | 2 | 3 | 0 | 0 | 2 | 3 |
| DATE · `99 aaaaaaaa 9999, aaaaaaaa` | 0 | 0 | 4 | 1 | 0 | 0 | 4 | 1 |
| DATE · `99.99.999a` | 0 | 0 | 0 | 1 | 2 | 2 | 2 | 3 |
| DATE · `99.9a.9999` | 0 | 0 | 3 | 2 | 0 | 0 | 3 | 2 |
| DATE · `99/99/9a99` | 0 | 0 | 3 | 2 | 0 | 0 | 3 | 2 |
| DATE · `999.9.9999` | 0 | 0 | 0 | 1 | 2 | 2 | 2 | 3 |
| DATE · `999.99.9999` | 0 | 0 | 2 | 3 | 0 | 0 | 2 | 3 |
| DATE · `9999—99-99` | 0 | 0 | 2 | 1 | 1 | 1 | 3 | 2 |
| DATE · `aaaa aaaaaa, 99 aaaaaaaa 9999` | 0 | 0 | 2 | 3 | 0 | 0 | 2 | 3 |
| DATE · `aaaaa aaaaaa, 99 aaaaa 9999` | 0 | 0 | 2 | 3 | 0 | 0 | 2 | 3 |
| DATE · `aaaaa, 99 aaaaaaaa 9999` | 0 | 0 | 3 | 2 | 0 | 0 | 3 | 2 |
| EMAIL · `domain dots 1` | 1,102 | 1,202 | 16,336 | 16,138 | 23,517 | 23,517 | 40,955 | 40,857 |
| EMAIL · `local: dot` | 533 | 545 | 7,788 | 7,733 | 11,171 | 11,171 | 19,492 | 19,449 |
| EMAIL · `local: letters only` | 83 | 87 | 2,765 | 2,695 | 4,031 | 4,031 | 6,879 | 6,813 |
| EMAIL · `local: digit` | 190 | 172 | 2,111 | 2,069 | 2,993 | 2,993 | 5,294 | 5,234 |
| EMAIL · `local: dot+digit` | 138 | 245 | 1,584 | 1,572 | 2,330 | 2,330 | 4,052 | 4,147 |
| EMAIL · `local: underscore` | 141 | 139 | 1,442 | 1,419 | 2,093 | 2,093 | 3,676 | 3,651 |
| EMAIL · `local: hyphen` | 17 | 14 | 646 | 650 | 899 | 899 | 1,562 | 1,563 |
| EMAIL · `domain hyphen` | 190 | 259 | 503 | 544 | 685 | 685 | 1,378 | 1,488 |
| EMAIL · `upper case` | 0 | 0 | 97 | 104 | 0 | 0 | 97 | 104 |
| IPV4_ADDRESS · `4 parts` | 749 | 911 | 3,061 | 3,084 | 3,823 | 3,823 | 7,633 | 7,818 |
| IPV4_ADDRESS · `no one-digit octet` | 596 | 491 | 2,493 | 2,506 | 3,065 | 3,065 | 6,154 | 6,062 |
| IPV4_ADDRESS · `private` | 189 | 303 | 722 | 742 | 894 | 894 | 1,805 | 1,939 |
| IPV4_ADDRESS · `documentation` | 109 | 90 | 410 | 410 | 537 | 537 | 1,056 | 1,037 |
| IPV4_ADDRESS · `1 one-digit octets` | 102 | 107 | 408 | 408 | 516 | 516 | 1,026 | 1,031 |
| IPV4_ADDRESS · `2 one-digit octets` | 50 | 118 | 158 | 169 | 231 | 231 | 439 | 518 |
| IPV4_ADDRESS · `3 one-digit octets` | 1 | 117 | 2 | 1 | 11 | 11 | 14 | 129 |
| IPV4_ADDRESS · `4 one-digit octets` | 0 | 78 | 0 | 0 | 0 | 0 | 0 | 78 |
| IPV6_ADDRESS · `lower` | 600 | 1,071 | 2,073 | 2,040 | 1,553 | 1,553 | 4,226 | 4,664 |
| IPV6_ADDRESS · `full 8 groups` | 273 | 414 | 472 | 471 | 1,553 | 1,553 | 2,298 | 2,438 |
| IPV6_ADDRESS · `:: middle` | 342 | 630 | 1,509 | 1,483 | 0 | 0 | 1,851 | 2,113 |
| IPV6_ADDRESS · `prefix fd/fc` | 215 | 377 | 657 | 662 | 550 | 550 | 1,422 | 1,589 |
| IPV6_ADDRESS · `prefix 2001:db8` | 244 | 436 | 950 | 924 | 208 | 208 | 1,402 | 1,568 |
| IPV6_ADDRESS · `other prefix` | 159 | 258 | 433 | 418 | 795 | 795 | 1,387 | 1,471 |
| IPV6_ADDRESS · `leading zeros` | 110 | 166 | 194 | 190 | 472 | 472 | 776 | 828 |
| IPV6_ADDRESS · `prefix ::` | 104 | 196 | 435 | 412 | 0 | 0 | 539 | 608 |
| IPV6_ADDRESS · `upper` | 109 | 211 | 417 | 398 | 0 | 0 | 526 | 609 |
| IPV6_ADDRESS · `:: end` | 50 | 118 | 251 | 258 | 0 | 0 | 301 | 376 |
| IPV6_ADDRESS · `:: start` | 55 | 96 | 223 | 205 | 0 | 0 | 278 | 301 |
| IPV6_ADDRESS · `::ffff:` | 49 | 100 | 212 | 207 | 0 | 0 | 261 | 307 |
| IPV6_ADDRESS · `prefix fe80` | 47 | 91 | 192 | 208 | 0 | 0 | 239 | 299 |
| IPV6_ADDRESS · `mixed` | 58 | 75 | 172 | 180 | 0 | 0 | 230 | 255 |
| IPV6_ADDRESS · `digit-only groups` | 2 | 1 | 5 | 6 | 0 | 0 | 7 | 7 |
| IPV6_ADDRESS · `no letters` | 2 | 1 | 5 | 6 | 0 | 0 | 7 | 7 |
| MAC_ADDRESS · `colon` | 475 | 708 | 1,560 | 1,562 | 1,461 | 1,461 | 3,496 | 3,731 |
| MAC_ADDRESS · `upper` | 414 | 565 | 1,296 | 1,306 | 1,282 | 1,282 | 2,992 | 3,153 |
| MAC_ADDRESS · `lower` | 368 | 506 | 1,170 | 1,144 | 678 | 678 | 2,216 | 2,328 |
| MAC_ADDRESS · `dash` | 259 | 295 | 672 | 666 | 499 | 499 | 1,430 | 1,460 |
| MAC_ADDRESS · `dotted` | 167 | 246 | 589 | 560 | 0 | 0 | 756 | 806 |
| MAC_ADDRESS · `mixed` | 119 | 178 | 355 | 338 | 0 | 0 | 474 | 516 |
| TIME · `99:99` | 660 | 825 | 3,572 | 3,660 | 4,834 | 4,834 | 9,066 | 9,319 |
| TIME · `9:99 aa` | 89 | 96 | 466 | 443 | 515 | 515 | 1,070 | 1,054 |
| TIME · `99:99:99` | 554 | 570 | 16 | 23 | 52 | 52 | 622 | 645 |
| TIME · `99:99 aa` | 29 | 29 | 155 | 146 | 166 | 166 | 350 | 341 |
| TIME · `9:99` | 0 | 0 | 5 | 5 | 3 | 3 | 8 | 8 |
| TIME · `99:a9` | 0 | 0 | 2 | 2 | 1 | 1 | 3 | 3 |
| TIME · `a9:99` | 0 | 0 | 1 | 1 | 2 | 2 | 3 | 3 |
| ZIPCODE · `aa9999` | 838 | 1,052 | 4,803 | 4,727 | 7,049 | 7,049 | 12,690 | 12,828 |
| ZIPCODE · `9999` | 415 | 635 | 376 | 372 | 0 | 0 | 791 | 1,007 |

## 2. Declared look-alikes (`_decoys`)

| | v4 targeted | v4.1 targeted | v4 LLM | v4.1 LLM | v4 old | v4.1 old | v4 all | v4.1 all |
|---|---|---|---|---|---|---|---|---|
| AZ_DRIVER_LICENSE_NUMBER · archive_folder | 83 | 208 | 322 | 327 | 0 | 0 | 405 | 535 |
| AZ_DRIVER_LICENSE_NUMBER · campaign_code | 86 | 203 | 325 | 320 | 0 | 0 | 411 | 523 |
| AZ_DRIVER_LICENSE_NUMBER · internal_reference | 331 | 334 | 338 | 342 | 0 | 0 | 669 | 676 |
| AZ_DRIVER_LICENSE_NUMBER · licence_hyphen | 79 | 85 | 323 | 341 | 0 | 0 | 402 | 426 |
| AZ_DRIVER_LICENSE_NUMBER · licence_too_short | 84 | 87 | 336 | 324 | 0 | 0 | 420 | 411 |
| AZ_ID_CARD_NUMBER · ORDER_ID | 0 | 0 | 572 | 580 | 0 | 0 | 572 | 580 |
| AZ_ID_CARD_NUMBER · id_card_hyphen | 87 | 93 | 317 | 297 | 0 | 0 | 404 | 390 |
| AZ_ID_CARD_NUMBER · id_card_short_number | 78 | 84 | 0 | 0 | 0 | 0 | 78 | 84 |
| AZ_ID_CARD_NUMBER · id_card_too_long | 85 | 86 | 345 | 337 | 0 | 0 | 430 | 423 |
| AZ_ID_CARD_NUMBER · id_card_too_short | 85 | 91 | 320 | 328 | 0 | 0 | 405 | 419 |
| CARD_SECURITY_CODE · cvv_1_2_digits | 81 | 81 | 301 | 293 | 0 | 0 | 382 | 374 |
| CARD_SECURITY_CODE · cvv_5_digits | 231 | 305 | 342 | 354 | 0 | 0 | 573 | 659 |
| CARD_SECURITY_CODE · cvv_letters | 90 | 85 | 281 | 296 | 0 | 0 | 371 | 381 |
| CARD_SECURITY_CODE · cvv_separator | 87 | 91 | 183 | 180 | 0 | 0 | 270 | 271 |
| CARD_SECURITY_CODE · cvv_sequential_5 | 213 | 225 | 70 | 79 | 0 | 0 | 283 | 304 |
| CARD_SECURITY_CODE · door_code | 78 | 90 | 0 | 0 | 0 | 0 | 78 | 90 |
| CARD_SECURITY_CODE · policy_sequential | 81 | 84 | 296 | 298 | 0 | 0 | 377 | 382 |
| CARD_SECURITY_CODE · room_code | 86 | 93 | 0 | 0 | 0 | 0 | 86 | 93 |
| DATE · DATE_LIKE_ID | 0 | 0 | 643 | 669 | 0 | 0 | 643 | 669 |
| DATE · TIMESTAMP | 0 | 0 | 1,010 | 1,132 | 738 | 738 | 1,748 | 1,870 |
| DATE · date_bad_month | 1,035 | 1,250 | 351 | 349 | 0 | 0 | 1,386 | 1,599 |
| DATE · date_clause_number | 122 | 198 | 355 | 357 | 0 | 0 | 477 | 555 |
| DATE · date_impossible_day | 1,032 | 1,295 | 333 | 327 | 0 | 0 | 1,365 | 1,622 |
| DATE · date_iso_out_of_range | 1,035 | 1,117 | 318 | 318 | 0 | 0 | 1,353 | 1,435 |
| DATE · date_version_string | 117 | 192 | 333 | 328 | 0 | 0 | 450 | 520 |
| EMAIL · EMAIL_LIKE_HANDLE | 0 | 0 | 736 | 686 | 0 | 0 | 736 | 686 |
| EMAIL · MASKED_EMAIL | 0 | 0 | 771 | 771 | 0 | 0 | 771 | 771 |
| EMAIL · OBFUSCATED_EMAIL | 0 | 0 | 724 | 728 | 0 | 0 | 724 | 728 |
| EMAIL · email_dotless_domain | 145 | 155 | 84 | 90 | 0 | 0 | 229 | 245 |
| EMAIL · email_double_at | 153 | 139 | 104 | 104 | 0 | 0 | 257 | 243 |
| EMAIL · email_localhost | 151 | 151 | 93 | 102 | 0 | 0 | 244 | 253 |
| EMAIL · email_no_at | 146 | 156 | 94 | 95 | 0 | 0 | 240 | 251 |
| IPV4_ADDRESS · IP_INVALID_OCTET | 0 | 0 | 670 | 671 | 0 | 0 | 670 | 671 |
| IPV4_ADDRESS · IP_LIKE_VERSION | 0 | 0 | 758 | 752 | 0 | 0 | 758 | 752 |
| IPV4_ADDRESS · ipv4_octet_over_255 | 84 | 92 | 320 | 307 | 0 | 0 | 404 | 399 |
| IPV4_ADDRESS · ipv4_placeholder | 82 | 36 | 0 | 0 | 0 | 0 | 82 | 36 |
| IPV4_ADDRESS · ipv4_short_over_255 | 85 | 42 | 0 | 0 | 0 | 0 | 85 | 42 |
| IPV4_ADDRESS · ipv4_three_octets | 81 | 43 | 0 | 0 | 0 | 0 | 81 | 43 |
| IPV6_ADDRESS · ipv6_non_hex | 79 | 86 | 91 | 81 | 0 | 0 | 170 | 167 |
| IPV6_ADDRESS · ipv6_triple_colon | 77 | 85 | 328 | 319 | 0 | 0 | 405 | 404 |
| IPV6_ADDRESS · ipv6_two_compressions | 83 | 79 | 96 | 91 | 0 | 0 | 179 | 170 |
| MAC_ADDRESS · MAC_LIKE_HASH | 0 | 0 | 774 | 790 | 0 | 0 | 774 | 790 |
| MAC_ADDRESS · mac_3_to_5_groups | 78 | 85 | 291 | 302 | 0 | 0 | 369 | 387 |
| MAC_ADDRESS · mac_fragment_dashed | 85 | 82 | 0 | 0 | 0 | 0 | 85 | 82 |
| TIME · TIMESTAMP | 0 | 0 | 105 | 130 | 56 | 56 | 161 | 186 |
| TIME · policy_sequential_time | 0 | 53 | 0 | 0 | 0 | 0 | 0 | 53 |
| TIME · policy_version_time | 134 | 82 | 305 | 299 | 0 | 0 | 439 | 381 |
| TIME · time_3_digit_minutes | 127 | 87 | 335 | 350 | 0 | 0 | 462 | 437 |
| TIME · time_bad_hour | 131 | 226 | 302 | 294 | 0 | 0 | 433 | 520 |
| TIME · time_bad_minute | 125 | 224 | 324 | 305 | 0 | 0 | 449 | 529 |
| TIME · time_line_stamp | 992 | 1,012 | 0 | 0 | 0 | 0 | 992 | 1,012 |
| ZIPCODE · zip_shape_as_code | 84 | 92 | 84 | 79 | 0 | 0 | 168 | 171 |
| ZIPCODE · zip_shape_in_iban_field | 84 | 81 | 339 | 339 | 0 | 0 | 423 | 420 |
| ZIPCODE · zip_two_digits | 212 | 94 | 0 | 0 | 0 | 0 | 212 | 94 |
| ZIPCODE · zip_wrong_length | 201 | 541 | 345 | 322 | 0 | 0 | 546 | 863 |

## 3. Regex shapes anywhere in the text

| | v4 targeted | v4.1 targeted | v4 LLM | v4.1 LLM | v4 old | v4.1 old | v4 all | v4.1 all |
|---|---|---|---|---|---|---|---|---|
| hh:mm · unlabelled | 0 | 0 | 13,003 | 12,484 | 18,503 | 18,503 | 31,506 | 30,987 |
| hh:mm · labelled TIME | 778 | 950 | 4,184 | 4,239 | 5,444 | 5,444 | 10,406 | 10,633 |
| hh:mm · declared look-alike | 565 | 742 | 1,464 | 1,552 | 177 | 177 | 2,206 | 2,471 |
| hh:mm · labelled BUILDINGNUM | 0 | 0 | 0 | 0 | 14 | 14 | 14 | 14 |
| hh:mm · labelled AGE | 0 | 0 | 2 | 1 | 4 | 4 | 6 | 5 |
| hh:mm after `saat` · labelled TIME | 203 | 278 | 3,163 | 3,208 | 3,342 | 3,342 | 6,708 | 6,828 |
| hh:mm after `saat` · declared look-alike | 85 | 186 | 285 | 269 | 1 | 1 | 371 | 456 |
| hh:mm after `saat` · unlabelled | 0 | 0 | 42 | 43 | 131 | 131 | 173 | 174 |
| hh:mm after `vaxt` · labelled TIME | 180 | 279 | 748 | 768 | 1,450 | 1,450 | 2,378 | 2,497 |
| hh:mm after `vaxt` · declared look-alike | 104 | 189 | 362 | 345 | 0 | 0 | 466 | 534 |
| hh:mm after `vaxt` · unlabelled | 0 | 0 | 160 | 150 | 299 | 299 | 459 | 449 |
| hh:mm:ss · unlabelled | 0 | 0 | 27,427 | 26,739 | 35,842 | 35,842 | 63,269 | 62,581 |
| hh:mm:ss · declared look-alike | 817 | 855 | 326 | 331 | 608 | 608 | 1,751 | 1,794 |
| hh:mm:ss · labelled TIME | 554 | 570 | 19 | 27 | 71 | 71 | 644 | 668 |
| hh:mm:ss · labelled AGE | 0 | 0 | 2 | 1 | 9 | 9 | 11 | 10 |
| hh:mm:ss · labelled BUILDINGNUM | 0 | 0 | 3 | 3 | 0 | 0 | 3 | 3 |
| [hh:mm(:ss)] line stamp · unlabelled | 0 | 0 | 7,952 | 7,576 | 13,585 | 13,585 | 21,537 | 21,161 |
| [hh:mm(:ss)] line stamp · declared look-alike | 498 | 527 | 90 | 109 | 45 | 45 | 633 | 681 |
| [hh:mm(:ss)] line stamp · labelled BUILDINGNUM | 0 | 0 | 1 | 0 | 14 | 14 | 15 | 14 |
| [hh:mm(:ss)] line stamp · labelled AGE | 0 | 0 | 3 | 1 | 2 | 2 | 5 | 3 |
| IPv6-like (:: or 3+ colons) · labelled IPV6_ADDRESS | 769 | 1,358 | 2,664 | 2,619 | 1,550 | 1,550 | 4,983 | 5,527 |
| IPv6-like (:: or 3+ colons) · labelled MAC_ADDRESS | 475 | 708 | 1,558 | 1,560 | 1,459 | 1,459 | 3,492 | 3,727 |
| IPv6-like (:: or 3+ colons) · declared look-alike | 189 | 190 | 516 | 496 | 0 | 0 | 705 | 686 |
| IPv6-like (:: or 3+ colons) · unlabelled | 0 | 0 | 26 | 20 | 146 | 146 | 172 | 166 |
| IPv6-like, digit-only groups · unlabelled | 0 | 0 | 24 | 17 | 145 | 145 | 169 | 162 |
| IPv6-like, digit-only groups · labelled IPV6_ADDRESS | 2 | 1 | 5 | 6 | 0 | 0 | 7 | 7 |
| IPv6-like, digit-only groups · declared look-alike | 3 | 0 | 2 | 3 | 0 | 0 | 5 | 3 |
| ::ffff: + IPv4 · labelled IPV6_ADDRESS | 43 | 94 | 203 | 197 | 0 | 0 | 246 | 291 |
| MAC colon 6 pairs · labelled MAC_ADDRESS | 475 | 708 | 1,557 | 1,559 | 1,459 | 1,459 | 3,491 | 3,726 |
| MAC dash 6 pairs · labelled MAC_ADDRESS | 259 | 295 | 664 | 660 | 496 | 496 | 1,419 | 1,451 |
| MAC dash 6 pairs · unlabelled | 0 | 0 | 0 | 0 | 7 | 7 | 7 | 7 |
| dash pairs 3-4 (99-99-99) · declared look-alike | 112 | 109 | 107 | 118 | 0 | 0 | 219 | 227 |
| dash pairs 3-4 (99-99-99) · unlabelled | 0 | 0 | 6 | 7 | 8 | 8 | 14 | 15 |
| dotted 4 parts, all <=255 · labelled IPV4_ADDRESS | 736 | 897 | 2,839 | 2,873 | 3,385 | 3,385 | 6,960 | 7,155 |
| dotted 4 parts, all <=255 · labelled IPV6_ADDRESS | 43 | 94 | 203 | 197 | 0 | 0 | 246 | 291 |
| dotted 4 parts, all <=255 · unlabelled | 0 | 0 | 7 | 4 | 6 | 6 | 13 | 10 |
| dotted 4 parts, one-digit octets >=2 · unlabelled | 0 | 0 | 5 | 3 | 93 | 93 | 98 | 96 |
| dotted 4 parts, one-digit octets >=2 · labelled IPV4_ADDRESS | 2 | 85 | 5 | 5 | 3 | 3 | 10 | 93 |
| dotted 4 parts, one-digit octets >=2 · declared look-alike | 38 | 19 | 9 | 8 | 0 | 0 | 47 | 27 |
| dotted 3 parts (99.99.99) · labelled DATE | 0 | 0 | 484 | 456 | 610 | 610 | 1,094 | 1,066 |
| dotted 3 parts (99.99.99) · unlabelled | 0 | 0 | 187 | 189 | 865 | 865 | 1,052 | 1,054 |
| dotted 3 parts (99.99.99) · declared look-alike | 200 | 239 | 559 | 551 | 1 | 1 | 760 | 791 |
| dotted 5 parts · declared look-alike | 38 | 28 | 0 | 0 | 0 | 0 | 38 | 28 |
| email-like a@b.c · labelled EMAIL | 1,102 | 1,202 | 16,336 | 16,138 | 23,517 | 23,517 | 40,955 | 40,857 |
| email-like a@b.c · declared look-alike | 80 | 69 | 49 | 47 | 0 | 0 | 129 | 116 |
| email-like a@b.c · unlabelled | 0 | 0 | 0 | 0 | 4 | 4 | 4 | 4 |
| email-like, local part with dot · labelled EMAIL | 671 | 790 | 9,372 | 9,305 | 13,501 | 13,501 | 23,544 | 23,596 |
| email-like, local part with hyphen · labelled EMAIL | 17 | 14 | 646 | 650 | 899 | 899 | 1,562 | 1,563 |
| 2 letters + 6 digits · labelled AZ_DRIVER_LICENSE_NUMBER | 2,816 | 3,653 | 3,316 | 3,296 | 2,400 | 2,400 | 8,532 | 9,349 |
| 2 letters + 6 digits · declared look-alike | 0 | 0 | 55 | 49 | 0 | 0 | 55 | 49 |
| 2 letters + 6 digits · unlabelled | 0 | 0 | 0 | 1 | 12 | 12 | 12 | 13 |
| 2 letters + 6 digits after `sürücü` · labelled AZ_DRIVER_LICENSE_NUMBER | 720 | 988 | 2,128 | 2,095 | 1,306 | 1,306 | 4,154 | 4,389 |
| 2 letters + 6 digits after `vəsiqə` · labelled AZ_DRIVER_LICENSE_NUMBER | 166 | 321 | 342 | 339 | 311 | 311 | 819 | 971 |
| 2 letters + 6 digits after `vəsi̇qə` · labelled AZ_DRIVER_LICENSE_NUMBER | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 3 |
| 2 letters + 6 digits after `şəxsiyyət` · labelled AZ_DRIVER_LICENSE_NUMBER | 12 | 155 | 37 | 32 | 15 | 15 | 64 | 202 |
| 2 letters + 7 digits · labelled AZ_ID_CARD_NUMBER | 3,154 | 4,255 | 2,616 | 2,610 | 1,681 | 1,681 | 7,451 | 8,546 |
| 2 letters + 7 digits · unlabelled | 0 | 0 | 3 | 3 | 328 | 328 | 331 | 331 |
| 2 letters + 7 digits · declared look-alike | 0 | 0 | 165 | 156 | 0 | 0 | 165 | 156 |
| 2 letters + 7 digits after `sürücü` · labelled AZ_ID_CARD_NUMBER | 22 | 169 | 25 | 22 | 4 | 4 | 51 | 195 |
| 2 letters + 7 digits after `vəsiqə` · labelled AZ_ID_CARD_NUMBER | 262 | 471 | 293 | 299 | 250 | 250 | 805 | 1,020 |
| 2 letters + 7 digits after `şəxsiyyət` · labelled AZ_ID_CARD_NUMBER | 657 | 957 | 1,654 | 1,662 | 810 | 810 | 3,121 | 3,429 |
| 3 digits · labelled TELEPHONENUM | 1,890 | 2,130 | 13,885 | 13,592 | 19,690 | 19,690 | 35,465 | 35,412 |
| 3 digits · unlabelled | 0 | 0 | 5,258 | 5,086 | 12,229 | 12,229 | 17,487 | 17,315 |
| 3 digits · labelled CARD_SECURITY_CODE | 730 | 751 | 1,642 | 1,601 | 1,794 | 1,794 | 4,166 | 4,146 |
| 3 digits · labelled BUILDINGNUM | 89 | 92 | 1,771 | 1,731 | 1,867 | 1,867 | 3,727 | 3,690 |
| 3 digits · declared look-alike | 1,323 | 1,541 | 1,367 | 1,367 | 0 | 0 | 2,690 | 2,908 |
| 3 digits · labelled IBAN | 16 | 18 | 84 | 81 | 121 | 121 | 221 | 220 |
| 3 digits · labelled STREET | 1 | 2 | 5 | 4 | 3 | 3 | 9 | 9 |
| 3 digits · labelled URL | 7 | 6 | 0 | 0 | 0 | 0 | 7 | 6 |
| 3 digits · labelled PRIVATE_KEY | 1 | 0 | 2 | 2 | 1 | 1 | 4 | 3 |
| 3 digits after `cvc` · labelled CARD_SECURITY_CODE | 105 | 123 | 32 | 28 | 56 | 56 | 193 | 207 |
| 3 digits after `cvc` · declared look-alike | 1 | 2 | 3 | 3 | 0 | 0 | 4 | 5 |
| 3 digits after `cvv` · labelled CARD_SECURITY_CODE | 466 | 456 | 413 | 395 | 365 | 365 | 1,244 | 1,216 |
| 3 digits after `cvv` · labelled TELEPHONENUM | 13 | 6 | 3 | 3 | 5 | 5 | 21 | 14 |
| 3 digits after `cvv` · unlabelled | 0 | 0 | 0 | 2 | 9 | 9 | 9 | 11 |
| 3 digits after `cvv` · declared look-alike | 3 | 8 | 2 | 2 | 0 | 0 | 5 | 10 |
| 3 digits after `təhlükəsizlik kodu` · labelled CARD_SECURITY_CODE | 109 | 116 | 1,108 | 1,096 | 1,171 | 1,171 | 2,388 | 2,383 |
| 3 digits after `təhlükəsizlik kodu` · unlabelled | 0 | 0 | 1 | 1 | 2 | 2 | 3 | 3 |
| 3 digits after `təhlükəsizlik kodu` · declared look-alike | 2 | 1 | 1 | 1 | 0 | 0 | 3 | 2 |
| 3 digits after `təhlükəsizlik kodu` · labelled TELEPHONENUM | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 2 |
| 4 digits · unlabelled | 0 | 0 | 13,257 | 13,211 | 26,579 | 26,579 | 39,836 | 39,790 |
| 4 digits · labelled DATE | 371 | 394 | 5,880 | 5,863 | 6,687 | 6,687 | 12,938 | 12,944 |
| 4 digits · labelled PAYMENT_CARD_NUMBER | 2,888 | 2,953 | 3,989 | 3,987 | 5,442 | 5,442 | 12,319 | 12,382 |
| 4 digits · labelled IBAN | 1,160 | 1,165 | 3,209 | 3,209 | 4,506 | 4,506 | 8,875 | 8,880 |
| 4 digits · declared look-alike | 725 | 867 | 1,552 | 1,589 | 1 | 1 | 2,278 | 2,457 |
| 4 digits · labelled ZIPCODE | 383 | 553 | 333 | 334 | 0 | 0 | 716 | 887 |
| 4 digits · labelled CARD_SECURITY_CODE | 154 | 152 | 263 | 262 | 286 | 286 | 703 | 700 |
| 4 digits · labelled TELEPHONENUM | 25 | 30 | 0 | 0 | 0 | 0 | 25 | 30 |
| 4 digits · labelled URL | 9 | 6 | 0 | 0 | 0 | 0 | 9 | 6 |
| 4 digits · labelled STREET | 0 | 1 | 1 | 1 | 0 | 0 | 1 | 2 |
| 4 digits after `cvc` · declared look-alike | 18 | 23 | 44 | 48 | 0 | 0 | 62 | 71 |
| 4 digits after `cvc` · labelled CARD_SECURITY_CODE | 28 | 24 | 11 | 11 | 18 | 18 | 57 | 53 |
| 4 digits after `cvc` · labelled PAYMENT_CARD_NUMBER | 4 | 10 | 0 | 0 | 0 | 0 | 4 | 10 |
| 4 digits after `cvc` · unlabelled | 0 | 0 | 4 | 4 | 0 | 0 | 4 | 4 |
| 4 digits after `cvc` · labelled IBAN | 2 | 1 | 0 | 0 | 0 | 0 | 2 | 1 |
| 4 digits after `cvv` · declared look-alike | 67 | 58 | 198 | 193 | 0 | 0 | 265 | 251 |
| 4 digits after `cvv` · labelled CARD_SECURITY_CODE | 83 | 93 | 63 | 59 | 54 | 54 | 200 | 206 |
| 4 digits after `cvv` · labelled PAYMENT_CARD_NUMBER | 33 | 15 | 0 | 4 | 0 | 0 | 33 | 19 |
| 4 digits after `cvv` · unlabelled | 0 | 0 | 9 | 7 | 1 | 1 | 10 | 8 |
| 4 digits after `cvv` · labelled DATE | 1 | 1 | 1 | 1 | 0 | 0 | 2 | 2 |
| 4 digits after `indeks` · labelled ZIPCODE | 101 | 62 | 11 | 13 | 0 | 0 | 112 | 75 |
| 4 digits after `indeks` · unlabelled | 0 | 0 | 6 | 7 | 13 | 13 | 19 | 20 |
| 4 digits after `indeks` · labelled PAYMENT_CARD_NUMBER | 6 | 11 | 1 | 1 | 1 | 1 | 8 | 13 |
| 4 digits after `indeks` · declared look-alike | 1 | 0 | 2 | 3 | 0 | 0 | 3 | 3 |
| 4 digits after `indeks` · labelled IBAN | 1 | 0 | 0 | 0 | 1 | 1 | 2 | 1 |
| 4 digits after `i̇ndeks` · labelled ZIPCODE | 6 | 17 | 1 | 0 | 0 | 0 | 7 | 17 |
| 4 digits after `i̇ndeks` · declared look-alike | 4 | 3 | 0 | 0 | 0 | 0 | 4 | 3 |
| 4 digits after `i̇ndeks` · unlabelled | 0 | 0 | 1 | 0 | 2 | 2 | 3 | 2 |
| 4 digits after `i̇ndeks` · labelled PAYMENT_CARD_NUMBER | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 4 |
| 4 digits after `poçt` · labelled ZIPCODE | 111 | 94 | 283 | 281 | 0 | 0 | 394 | 375 |
| 4 digits after `poçt` · unlabelled | 0 | 0 | 34 | 20 | 13 | 13 | 47 | 33 |
| 4 digits after `poçt` · labelled DATE | 0 | 1 | 4 | 8 | 0 | 0 | 4 | 9 |
| 4 digits after `poçt` · labelled PAYMENT_CARD_NUMBER | 4 | 3 | 3 | 3 | 0 | 0 | 7 | 6 |
| AZ + 4 digits · labelled ZIPCODE | 838 | 1,052 | 4,803 | 4,727 | 7,049 | 7,049 | 12,690 | 12,828 |
| AZ + 4 digits · unlabelled | 0 | 0 | 19 | 16 | 1,915 | 1,915 | 1,934 | 1,931 |
| AZ + 4 digits · declared look-alike | 168 | 173 | 424 | 418 | 0 | 0 | 592 | 591 |
| AZ + 4 digits after `indeks` · labelled ZIPCODE | 165 | 171 | 208 | 207 | 266 | 266 | 639 | 644 |
| AZ + 4 digits after `indeks` · declared look-alike | 44 | 43 | 1 | 1 | 0 | 0 | 45 | 44 |
| AZ + 4 digits after `indeks` · unlabelled | 0 | 0 | 0 | 0 | 17 | 17 | 17 | 17 |
| AZ + 4 digits after `i̇ndeks` · labelled ZIPCODE | 52 | 92 | 11 | 10 | 69 | 69 | 132 | 171 |
| AZ + 4 digits after `i̇ndeks` · unlabelled | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 2 |
| AZ + 4 digits after `poçt` · labelled ZIPCODE | 149 | 223 | 2,053 | 2,033 | 3,896 | 3,896 | 6,098 | 6,152 |
| AZ + 4 digits after `poçt` · declared look-alike | 12 | 12 | 0 | 0 | 0 | 0 | 12 | 12 |
| dd.mm.yyyy · labelled DATE | 429 | 446 | 12,549 | 12,369 | 19,576 | 19,576 | 32,554 | 32,391 |
| dd.mm.yyyy · unlabelled | 0 | 0 | 2,330 | 2,360 | 1,718 | 1,718 | 4,048 | 4,078 |
| dd.mm.yyyy · declared look-alike | 1,304 | 1,578 | 1,217 | 1,328 | 33 | 33 | 2,554 | 2,939 |
| dd.mm.yyyy after `tarix` · labelled DATE | 243 | 255 | 7,772 | 7,696 | 10,569 | 10,569 | 18,584 | 18,520 |
| dd.mm.yyyy after `tarix` · declared look-alike | 1,074 | 1,326 | 429 | 429 | 8 | 8 | 1,511 | 1,763 |
| dd.mm.yyyy after `tarix` · unlabelled | 0 | 0 | 429 | 429 | 179 | 179 | 608 | 608 |
| dd.mm.yyyy after `tari̇x` · labelled DATE | 0 | 0 | 25 | 21 | 96 | 96 | 121 | 117 |
| dd.mm.yyyy after `tari̇x` · unlabelled | 0 | 0 | 9 | 6 | 4 | 4 | 13 | 10 |
| 5 digits · unlabelled | 0 | 0 | 1,145 | 975 | 2,218 | 2,218 | 3,363 | 3,193 |
| 5 digits · declared look-alike | 478 | 571 | 819 | 838 | 0 | 0 | 1,297 | 1,409 |
| 5 digits · labelled PAYMENT_CARD_NUMBER | 17 | 11 | 81 | 87 | 119 | 119 | 217 | 217 |
| 5 digits · labelled URL | 15 | 14 | 41 | 38 | 43 | 43 | 99 | 95 |
| 5 digits after `cvc` · declared look-alike | 97 | 109 | 66 | 67 | 0 | 0 | 163 | 176 |
| 5 digits after `cvv` · declared look-alike | 270 | 315 | 256 | 273 | 0 | 0 | 526 | 588 |
| 5 digits after `cvv` · unlabelled | 0 | 0 | 1 | 1 | 1 | 1 | 2 | 2 |
| 5 digits after `indeks` · unlabelled | 0 | 0 | 0 | 0 | 6 | 6 | 6 | 6 |
| 5 digits after `i̇ndeks` · unlabelled | 0 | 0 | 1 | 1 | 2 | 2 | 3 | 3 |
| 5 digits after `i̇ndeks` · declared look-alike | 1 | 2 | 0 | 0 | 0 | 0 | 1 | 2 |
| 5 digits after `poçt` · unlabelled | 0 | 0 | 6 | 6 | 2 | 2 | 8 | 8 |
| AZ + 1-3 digits · labelled IBAN | 288 | 279 | 413 | 411 | 587 | 587 | 1,288 | 1,277 |
| AZ + 1-3 digits · declared look-alike | 148 | 396 | 174 | 170 | 0 | 0 | 322 | 566 |
| AZ + 1-3 digits · unlabelled | 0 | 0 | 5 | 5 | 8 | 8 | 13 | 13 |
| AZ + 1-3 digits after `indeks` · declared look-alike | 2 | 34 | 60 | 60 | 0 | 0 | 62 | 94 |
| AZ + 1-3 digits after `i̇ndeks` · declared look-alike | 8 | 56 | 0 | 1 | 0 | 0 | 8 | 57 |
| AZ + 1-3 digits after `poçt` · declared look-alike | 21 | 76 | 52 | 54 | 0 | 0 | 73 | 130 |
| AZ + 1-3 digits after `poçt` · unlabelled | 0 | 0 | 1 | 1 | 1 | 1 | 2 | 2 |
| AZ + 5 digits · declared look-alike | 53 | 145 | 63 | 61 | 0 | 0 | 116 | 206 |
| AZ + 5 digits · unlabelled | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 2 |
| AZ + 5 digits after `indeks` · declared look-alike | 4 | 11 | 22 | 20 | 0 | 0 | 26 | 31 |
| AZ + 5 digits after `i̇ndeks` · declared look-alike | 4 | 23 | 0 | 0 | 0 | 0 | 4 | 23 |
| AZ + 5 digits after `poçt` · declared look-alike | 7 | 31 | 19 | 19 | 0 | 0 | 26 | 50 |
| hh:mm, hour > 23 or minute > 59 · declared look-alike | 256 | 450 | 626 | 599 | 0 | 0 | 882 | 1,049 |
| hh:mm, hour > 23 or minute > 59 · unlabelled | 0 | 0 | 13 | 16 | 1 | 1 | 14 | 17 |
| hh:mm, hour > 23 or minute > 59 · labelled TIME | 0 | 0 | 2 | 2 | 1 | 1 | 3 | 3 |
| hh:mm, hour > 23 or minute > 59 after `saat` · declared look-alike | 84 | 186 | 282 | 267 | 0 | 0 | 366 | 453 |
| hh:mm, hour > 23 or minute > 59 after `saat` · unlabelled | 0 | 0 | 2 | 3 | 0 | 0 | 2 | 3 |
| hh:mm, hour > 23 or minute > 59 after `vaxt` · declared look-alike | 104 | 188 | 339 | 326 | 0 | 0 | 443 | 514 |
| dd.mm.yyyy, month > 12 · declared look-alike | 524 | 644 | 159 | 162 | 0 | 0 | 683 | 806 |
| dd.mm.yyyy, month > 12 · unlabelled | 0 | 0 | 4 | 4 | 2 | 2 | 6 | 6 |
| dd.mm.yyyy, month > 12 after `tarix` · declared look-alike | 424 | 551 | 115 | 116 | 0 | 0 | 539 | 667 |
| dd.mm.yyyy, month > 12 after `tarix` · unlabelled | 0 | 0 | 2 | 2 | 1 | 1 | 3 | 3 |
| 30/31.02.yyyy · declared look-alike | 131 | 147 | 40 | 48 | 0 | 0 | 171 | 195 |
| 30/31.02.yyyy after `tarix` · declared look-alike | 102 | 122 | 27 | 35 | 0 | 0 | 129 | 157 |
