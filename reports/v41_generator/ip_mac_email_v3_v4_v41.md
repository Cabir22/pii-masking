# IPv4, IPv6, MAC and email in the targeted data: v3 against v4

| | v3 | v4 | v4.1 |
|---|---|---|---|
| documents | 25,000 | 25,000 | 28,000 |
| IPv4: real values | 892 | 918 | 1,155 |
| IPv4: documents with a real value | 500 | 592 | 733 |
| IPv4: look-alikes | 132 | 412 | 277 |
| IPv4: documents with a look-alike | 131 | 401 | 275 |
| IPv4: documents with both | 49 | 227 | 159 |
| IPv6: real values | 1,450 | 975 | 1,678 |
| IPv6: documents with a real value | 1,047 | 687 | 1,327 |
| IPv6: look-alikes | 397 | 311 | 330 |
| IPv6: documents with a look-alike | 374 | 292 | 314 |
| IPv6: documents with both | 142 | 72 | 136 |
| MAC: real values | 1,433 | 1,109 | 1,557 |
| MAC: documents with a real value | 999 | 781 | 1,181 |
| MAC: look-alikes | 133 | 206 | 220 |
| MAC: documents with a look-alike | 133 | 201 | 216 |
| MAC: documents with both | 83 | 148 | 158 |
| email: real values | 1,582 | 1,370 | 1,523 |
| email: documents with a real value | 985 | 844 | 955 |
| email: look-alikes | 876 | 740 | 758 |
| email: documents with a look-alike | 797 | 675 | 684 |
| email: documents with both | 236 | 218 | 245 |

## IPv4

### Real values by format

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| public | 464 | 474 | 599 | +135 |
| private | 252 | 234 | 381 | +129 |
| documentation range | 108 | 134 | 108 | +0 |
| carrier-grade NAT | 68 | 76 | 67 | -1 |

### Real values by family

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| structured | 720 | 597 | 627 | -93 |
| net_context | 0 | 0 | 203 | +203 |
| cross_anchor | 0 | 90 | 158 | +158 |
| punct | 128 | 89 | 85 | -43 |
| decoy_pair | 16 | 108 | 64 | +48 |
| prose | 28 | 34 | 18 | -10 |

### Real values by context

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| prose | 160 | 307 | 510 | +350 |
| container:csv_header | 156 | 96 | 73 | -83 |
| container:pipe_table | 155 | 131 | 140 | -15 |
| container:csv_snake | 106 | 139 | 109 | +3 |
| container:log | 90 | 65 | 98 | +8 |
| container:csv_noheader | 54 | 42 | 62 | +8 |
| container:json | 59 | 42 | 55 | -4 |
| container:dialogue | 51 | 39 | 45 | -6 |
| container:key_value | 32 | 31 | 25 | -7 |
| container:config | 17 | 12 | 20 | +3 |
| label: value line | 5 | 10 | 12 | +7 |
| table / csv-like line | 7 | 4 | 6 | -1 |

### Character right after a real value

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| space | 269 | 400 | 652 | +383 |
| line break | 205 | 181 | 166 | -39 |
| , | 147 | 125 | 137 | -10 |
| ] | 129 | 90 | 86 | -43 |
| " | 62 | 47 | 56 | -6 |
| ; | 57 | 56 | 35 | -22 |
| . | 19 | 15 | 20 | +1 |
| » | 3 | 1 | 2 | -1 |
| ) | 1 | 3 | 1 | +0 |

### Look-alikes by kind

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| ipv4_octet_over_255 | 132 | 103 | 110 | -22 |
| ipv4_short_over_255 | 0 | 103 | 56 | +56 |
| ipv4_three_octets | 0 | 103 | 55 | +55 |
| ipv4_placeholder | 0 | 103 | 56 | +56 |

### Look-alikes by family

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| pii_free | 11 | 129 | 57 | +46 |
| decoy_pair | 16 | 108 | 64 | +48 |
| cross_anchor | 0 | 90 | 79 | +79 |
| punct | 59 | 40 | 47 | -12 |
| structured | 46 | 45 | 30 | -16 |

### Look-alikes by context

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| prose | 81 | 331 | 219 | +138 |
| label: value line | 3 | 29 | 23 | +20 |
| container:csv_snake | 5 | 11 | 2 | -3 |
| container:csv_header | 9 | 3 | 5 | -4 |
| container:dialogue | 5 | 9 | 9 | +4 |
| container:pipe_table | 7 | 4 | 4 | -3 |
| table / csv-like line | 2 | 7 | 5 | +3 |
| container:csv_noheader | 6 | 3 | 1 | -5 |
| container:config | 5 | 3 | 3 | -2 |
| container:json | 3 | 4 | 3 | +0 |
| container:key_value | 3 | 4 | 2 | -1 |
| container:log | 3 | 4 | 1 | -2 |


## IPv6

### Real values by format

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| :: in the middle / lower | 433 | 299 | 535 | +102 |
| full 8 groups (leading zeros) / lower | 235 | 175 | 252 | +17 |
| full 8 groups / lower | 151 | 100 | 160 | +9 |
| :: at end / lower | 85 | 57 | 111 | +26 |
| :: in the middle / upper | 102 | 55 | 105 | +3 |
| IPv4-embedded ::ffff: / lower | 77 | 45 | 103 | +26 |
| :: at start / lower | 79 | 52 | 89 | +10 |
| <prefix>::1 / lower | 48 | 38 | 71 | +23 |
| full 8 groups (leading zeros) / upper | 40 | 20 | 45 | +5 |
| full 8 groups / upper | 39 | 18 | 32 | -7 |
| :: in the middle / mixed | 39 | 29 | 37 | -2 |
| <prefix>::1 / upper | 18 | 13 | 24 | +6 |
| full 8 groups (leading zeros) / mixed | 22 | 17 | 23 | +1 |
| :: at end / upper | 13 | 13 | 22 | +9 |
| :: at start / upper | 13 | 9 | 20 | +7 |
| full 8 groups / mixed | 17 | 6 | 10 | -7 |
| IPv4-embedded ::ffff: / upper | 12 | 11 | 11 | -1 |
| IPv4-embedded ::ffff: / mixed | 6 | 6 | 10 | +4 |
| <prefix>::1 / mixed | 9 | 1 | 5 | -4 |
| :: at end / mixed | 8 | 2 | 8 | +0 |
| :: at start / mixed | 2 | 7 | 4 | +2 |
| <prefix>::1 / no letters | 1 | 1 | 1 | +0 |
| :: at start / no letters | 1 | 1 | 0 | -1 |

### Real values by family

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| structured | 732 | 543 | 651 | -81 |
| contrast | 585 | 358 | 663 | +78 |
| net_context | 0 | 0 | 227 | +227 |
| decoy_pair | 109 | 49 | 117 | +8 |
| prose | 24 | 25 | 20 | -4 |

### Real values by context

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| prose | 677 | 410 | 990 | +313 |
| container:pipe_table | 168 | 90 | 142 | -26 |
| container:csv_snake | 141 | 111 | 103 | -38 |
| container:csv_header | 138 | 102 | 99 | -39 |
| container:csv_noheader | 65 | 42 | 83 | +18 |
| container:json | 56 | 47 | 70 | +14 |
| container:log | 67 | 64 | 58 | -9 |
| container:dialogue | 44 | 41 | 53 | +9 |
| container:key_value | 35 | 31 | 26 | -9 |
| label: value line | 26 | 13 | 26 | +0 |
| container:config | 18 | 15 | 17 | -1 |
| table / csv-like line | 15 | 9 | 11 | -4 |

### Character right after a real value

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| space | 766 | 458 | 1,003 | +237 |
| , | 239 | 158 | 225 | -14 |
| line break | 197 | 146 | 171 | -26 |
| . | 111 | 79 | 127 | +16 |
| ; | 79 | 79 | 73 | -6 |
| " | 56 | 49 | 72 | +16 |
| ) | 1 | 3 | 1 | +0 |
| ] | 1 | 2 | 3 | +2 |
| » | 0 | 1 | 3 | +3 |

### Look-alikes by kind

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| ipv6_triple_colon | 133 | 104 | 110 | -23 |
| ipv6_non_hex | 132 | 103 | 110 | -22 |
| ipv6_two_compressions | 132 | 104 | 110 | -22 |

### Look-alikes by family

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| pii_free | 238 | 235 | 183 | -55 |
| decoy_pair | 109 | 49 | 117 | +8 |
| structured | 50 | 27 | 30 | -20 |

### Look-alikes by context

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| prose | 281 | 226 | 233 | -48 |
| label: value line | 58 | 49 | 60 | +2 |
| container:pipe_table | 12 | 6 | 5 | -7 |
| container:csv_snake | 9 | 3 | 2 | -7 |
| container:dialogue | 9 | 2 | 5 | -4 |
| table / csv-like line | 8 | 9 | 7 | -1 |
| container:csv_header | 3 | 6 | 3 | +0 |
| container:json | 0 | 3 | 6 | +6 |
| container:log | 5 | 2 | 2 | -3 |
| container:config | 4 | 0 | 3 | -1 |
| container:key_value | 4 | 2 | 3 | -1 |
| container:csv_noheader | 4 | 3 | 1 | -3 |


## MAC

### Real values by format

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| colon / upper | 376 | 276 | 393 | +17 |
| colon / lower | 352 | 234 | 362 | +10 |
| dash / upper | 141 | 147 | 172 | +31 |
| dash / lower | 153 | 124 | 141 | -12 |
| dotted aabb.ccdd.eeff / lower | 123 | 96 | 140 | +17 |
| dotted aabb.ccdd.eeff / upper | 127 | 90 | 124 | -3 |
| colon / mixed | 97 | 74 | 126 | +29 |
| dash / mixed | 29 | 44 | 57 | +28 |
| dotted aabb.ccdd.eeff / mixed | 35 | 24 | 42 | +7 |

### Real values by family

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| structured | 764 | 606 | 667 | -97 |
| contrast | 585 | 358 | 663 | +78 |
| cross_anchor | 0 | 80 | 70 | +70 |
| net_context | 0 | 0 | 75 | +75 |
| decoy_pair | 54 | 42 | 60 | +6 |
| prose | 30 | 23 | 22 | -8 |

### Real values by context

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| prose | 645 | 488 | 870 | +225 |
| container:csv_header | 175 | 97 | 108 | -67 |
| container:csv_snake | 158 | 94 | 147 | -11 |
| container:pipe_table | 157 | 142 | 132 | -25 |
| container:log | 79 | 89 | 67 | -12 |
| container:csv_noheader | 68 | 52 | 85 | +17 |
| container:json | 38 | 42 | 54 | +16 |
| container:dialogue | 47 | 43 | 38 | -9 |
| container:key_value | 28 | 40 | 26 | -2 |
| container:config | 14 | 7 | 10 | -4 |
| table / csv-like line | 13 | 9 | 12 | -1 |
| label: value line | 11 | 6 | 8 | -3 |

### Character right after a real value

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| space | 674 | 588 | 825 | +151 |
| , | 400 | 241 | 391 | -9 |
| line break | 208 | 154 | 142 | -66 |
| ; | 77 | 54 | 113 | +36 |
| " | 38 | 43 | 57 | +19 |
| . | 32 | 26 | 24 | -8 |
| ) | 3 | 1 | 1 | -2 |
| » | 0 | 1 | 3 | +3 |
| ] | 1 | 1 | 1 | +0 |

### Look-alikes by kind

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| mac_3_to_5_groups | 133 | 103 | 110 | -23 |
| mac_fragment_dashed | 0 | 103 | 110 | +110 |

### Look-alikes by family

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| cross_anchor | 0 | 80 | 70 | +70 |
| decoy_pair | 54 | 42 | 60 | +6 |
| pii_free | 35 | 54 | 55 | +20 |
| structured | 44 | 30 | 35 | -9 |

### Look-alikes by context

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| prose | 81 | 162 | 168 | +87 |
| label: value line | 7 | 9 | 16 | +9 |
| container:csv_snake | 10 | 2 | 3 | -7 |
| container:pipe_table | 8 | 8 | 6 | -2 |
| container:key_value | 7 | 1 | 2 | -5 |
| container:dialogue | 6 | 3 | 3 | -3 |
| container:csv_header | 5 | 5 | 6 | +1 |
| container:json | 0 | 2 | 6 | +6 |
| container:csv_noheader | 4 | 5 | 5 | +1 |
| table / csv-like line | 1 | 5 | 1 | +0 |
| container:log | 2 | 4 | 2 | +0 |
| container:config | 2 | 0 | 2 | +0 |


## email

### Real values by format

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| local part: dot | 737 | 669 | 705 | -32 |
| local part: dot+digit | 225 | 173 | 305 | +80 |
| local part: digit | 251 | 223 | 210 | -41 |
| local part: underscore | 219 | 178 | 176 | -43 |
| local part: letters only | 126 | 107 | 110 | -16 |
| local part: hyphen | 24 | 20 | 17 | -7 |

### Real values by family

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| structured | 1,129 | 999 | 1,078 | -51 |
| form | 250 | 198 | 297 | +47 |
| punct | 115 | 95 | 73 | -42 |
| clerical | 59 | 56 | 46 | -13 |
| prose | 29 | 22 | 29 | +0 |

### Real values by context

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| container:csv_noheader | 600 | 583 | 611 | +11 |
| label: value line | 250 | 198 | 297 | +47 |
| container:csv_header | 134 | 74 | 103 | -31 |
| prose | 134 | 110 | 98 | -36 |
| container:pipe_table | 100 | 128 | 102 | +2 |
| container:csv_snake | 127 | 71 | 103 | -24 |
| table / csv-like line | 69 | 63 | 50 | -19 |
| container:log | 45 | 43 | 61 | +16 |
| container:json | 47 | 30 | 31 | -16 |
| container:dialogue | 28 | 34 | 32 | +4 |
| container:key_value | 26 | 22 | 24 | -2 |
| container:config | 22 | 14 | 11 | -11 |

### Character right after a real value

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| , | 537 | 429 | 498 | -39 |
| line break | 393 | 298 | 415 | +22 |
| ; | 232 | 247 | 243 | +11 |
| space | 216 | 230 | 222 | +6 |
| ! | 115 | 95 | 73 | -42 |
| " | 48 | 33 | 32 | -16 |
| end of text | 22 | 16 | 21 | -1 |
| . | 13 | 17 | 14 | +1 |
| ) | 1 | 4 | 3 | +2 |
| » | 3 | 1 | 0 | -3 |
| ] | 2 | 0 | 2 | +0 |

### Look-alikes by kind

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| email_double_at | 219 | 185 | 190 | -29 |
| email_no_at | 219 | 185 | 190 | -29 |
| email_dotless_domain | 219 | 185 | 189 | -30 |
| email_localhost | 219 | 185 | 189 | -30 |

### Look-alikes by family

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| structured | 338 | 302 | 363 | +25 |
| form | 219 | 192 | 263 | +44 |
| pii_free | 211 | 164 | 51 | -160 |
| punct | 69 | 57 | 47 | -22 |
| clerical | 39 | 25 | 34 | -5 |

### Look-alikes by context

| | v3 | v4 | v4.1 | change |
|---|---|---|---|---|
| label: value line | 268 | 234 | 269 | +1 |
| prose | 222 | 173 | 86 | -136 |
| container:csv_noheader | 186 | 182 | 217 | +31 |
| table / csv-like line | 48 | 31 | 40 | -8 |
| container:csv_header | 40 | 16 | 23 | -17 |
| container:pipe_table | 26 | 37 | 30 | +4 |
| container:csv_snake | 29 | 19 | 29 | +0 |
| container:dialogue | 13 | 13 | 22 | +9 |
| container:log | 12 | 20 | 20 | +8 |
| container:json | 13 | 8 | 9 | -4 |
| container:key_value | 10 | 4 | 11 | +1 |
| container:config | 9 | 3 | 2 | -7 |

