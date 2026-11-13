# IPv4, IPv6, MAC and email in the targeted data: v3 against v4

| | v3 | v4 |
|---|---|---|
| documents | 25,000 | 25,000 |
| IPv4: real values | 892 | 918 |
| IPv4: documents with a real value | 500 | 592 |
| IPv4: look-alikes | 132 | 412 |
| IPv4: documents with a look-alike | 131 | 401 |
| IPv4: documents with both | 49 | 227 |
| IPv6: real values | 1,450 | 975 |
| IPv6: documents with a real value | 1,047 | 687 |
| IPv6: look-alikes | 397 | 311 |
| IPv6: documents with a look-alike | 374 | 292 |
| IPv6: documents with both | 142 | 72 |
| MAC: real values | 1,433 | 1,109 |
| MAC: documents with a real value | 999 | 781 |
| MAC: look-alikes | 133 | 206 |
| MAC: documents with a look-alike | 133 | 201 |
| MAC: documents with both | 83 | 148 |
| email: real values | 1,582 | 1,370 |
| email: documents with a real value | 985 | 844 |
| email: look-alikes | 876 | 740 |
| email: documents with a look-alike | 797 | 675 |
| email: documents with both | 236 | 218 |

## IPv4

### Real values by format

| | v3 | v4 | change |
|---|---|---|---|
| public | 464 | 474 | +10 |
| private | 252 | 234 | -18 |
| documentation range | 108 | 134 | +26 |
| carrier-grade NAT | 68 | 76 | +8 |

### Real values by family

| | v3 | v4 | change |
|---|---|---|---|
| structured | 720 | 597 | -123 |
| punct | 128 | 89 | -39 |
| decoy_pair | 16 | 108 | +92 |
| cross_anchor | 0 | 90 | +90 |
| prose | 28 | 34 | +6 |

### Real values by context

| | v3 | v4 | change |
|---|---|---|---|
| prose | 160 | 307 | +147 |
| container:csv_header | 156 | 96 | -60 |
| container:pipe_table | 155 | 131 | -24 |
| container:csv_snake | 106 | 139 | +33 |
| container:log | 90 | 65 | -25 |
| container:json | 59 | 42 | -17 |
| container:csv_noheader | 54 | 42 | -12 |
| container:dialogue | 51 | 39 | -12 |
| container:key_value | 32 | 31 | -1 |
| container:config | 17 | 12 | -5 |
| label: value line | 5 | 10 | +5 |
| table / csv-like line | 7 | 4 | -3 |

### Character right after a real value

| | v3 | v4 | change |
|---|---|---|---|
| space | 269 | 400 | +131 |
| line break | 205 | 181 | -24 |
| , | 147 | 125 | -22 |
| ] | 129 | 90 | -39 |
| " | 62 | 47 | -15 |
| ; | 57 | 56 | -1 |
| . | 19 | 15 | -4 |
| » | 3 | 1 | -2 |
| ) | 1 | 3 | +2 |

### Look-alikes by kind

| | v3 | v4 | change |
|---|---|---|---|
| ipv4_octet_over_255 | 132 | 103 | -29 |
| ipv4_short_over_255 | 0 | 103 | +103 |
| ipv4_three_octets | 0 | 103 | +103 |
| ipv4_placeholder | 0 | 103 | +103 |

### Look-alikes by family

| | v3 | v4 | change |
|---|---|---|---|
| pii_free | 11 | 129 | +118 |
| decoy_pair | 16 | 108 | +92 |
| cross_anchor | 0 | 90 | +90 |
| punct | 59 | 40 | -19 |
| structured | 46 | 45 | -1 |

### Look-alikes by context

| | v3 | v4 | change |
|---|---|---|---|
| prose | 81 | 331 | +250 |
| label: value line | 3 | 29 | +26 |
| container:csv_snake | 5 | 11 | +6 |
| container:csv_header | 9 | 3 | -6 |
| container:dialogue | 5 | 9 | +4 |
| container:pipe_table | 7 | 4 | -3 |
| table / csv-like line | 2 | 7 | +5 |
| container:csv_noheader | 6 | 3 | -3 |
| container:config | 5 | 3 | -2 |
| container:json | 3 | 4 | +1 |
| container:key_value | 3 | 4 | +1 |
| container:log | 3 | 4 | +1 |


## IPv6

### Real values by format

| | v3 | v4 | change |
|---|---|---|---|
| :: in the middle / lower | 433 | 299 | -134 |
| full 8 groups (leading zeros) / lower | 235 | 175 | -60 |
| full 8 groups / lower | 151 | 100 | -51 |
| :: in the middle / upper | 102 | 55 | -47 |
| :: at end / lower | 85 | 57 | -28 |
| :: at start / lower | 79 | 52 | -27 |
| IPv4-embedded ::ffff: / lower | 77 | 45 | -32 |
| <prefix>::1 / lower | 48 | 38 | -10 |
| full 8 groups (leading zeros) / upper | 40 | 20 | -20 |
| full 8 groups / upper | 39 | 18 | -21 |
| :: in the middle / mixed | 39 | 29 | -10 |
| full 8 groups (leading zeros) / mixed | 22 | 17 | -5 |
| <prefix>::1 / upper | 18 | 13 | -5 |
| full 8 groups / mixed | 17 | 6 | -11 |
| :: at start / upper | 13 | 9 | -4 |
| :: at end / upper | 13 | 13 | +0 |
| IPv4-embedded ::ffff: / upper | 12 | 11 | -1 |
| <prefix>::1 / mixed | 9 | 1 | -8 |
| :: at end / mixed | 8 | 2 | -6 |
| :: at start / mixed | 2 | 7 | +5 |
| IPv4-embedded ::ffff: / mixed | 6 | 6 | +0 |
| <prefix>::1 / no letters | 1 | 1 | +0 |
| :: at start / no letters | 1 | 1 | +0 |

### Real values by family

| | v3 | v4 | change |
|---|---|---|---|
| structured | 732 | 543 | -189 |
| contrast | 585 | 358 | -227 |
| decoy_pair | 109 | 49 | -60 |
| prose | 24 | 25 | +1 |

### Real values by context

| | v3 | v4 | change |
|---|---|---|---|
| prose | 677 | 410 | -267 |
| container:pipe_table | 168 | 90 | -78 |
| container:csv_snake | 141 | 111 | -30 |
| container:csv_header | 138 | 102 | -36 |
| container:log | 67 | 64 | -3 |
| container:csv_noheader | 65 | 42 | -23 |
| container:json | 56 | 47 | -9 |
| container:dialogue | 44 | 41 | -3 |
| container:key_value | 35 | 31 | -4 |
| label: value line | 26 | 13 | -13 |
| container:config | 18 | 15 | -3 |
| table / csv-like line | 15 | 9 | -6 |

### Character right after a real value

| | v3 | v4 | change |
|---|---|---|---|
| space | 766 | 458 | -308 |
| , | 239 | 158 | -81 |
| line break | 197 | 146 | -51 |
| . | 111 | 79 | -32 |
| ; | 79 | 79 | +0 |
| " | 56 | 49 | -7 |
| ) | 1 | 3 | +2 |
| ] | 1 | 2 | +1 |
| » | 0 | 1 | +1 |

### Look-alikes by kind

| | v3 | v4 | change |
|---|---|---|---|
| ipv6_triple_colon | 133 | 104 | -29 |
| ipv6_non_hex | 132 | 103 | -29 |
| ipv6_two_compressions | 132 | 104 | -28 |

### Look-alikes by family

| | v3 | v4 | change |
|---|---|---|---|
| pii_free | 238 | 235 | -3 |
| decoy_pair | 109 | 49 | -60 |
| structured | 50 | 27 | -23 |

### Look-alikes by context

| | v3 | v4 | change |
|---|---|---|---|
| prose | 281 | 226 | -55 |
| label: value line | 58 | 49 | -9 |
| container:pipe_table | 12 | 6 | -6 |
| container:csv_snake | 9 | 3 | -6 |
| container:dialogue | 9 | 2 | -7 |
| table / csv-like line | 8 | 9 | +1 |
| container:csv_header | 3 | 6 | +3 |
| container:log | 5 | 2 | -3 |
| container:config | 4 | 0 | -4 |
| container:key_value | 4 | 2 | -2 |
| container:csv_noheader | 4 | 3 | -1 |
| container:json | 0 | 3 | +3 |


## MAC

### Real values by format

| | v3 | v4 | change |
|---|---|---|---|
| colon / upper | 376 | 276 | -100 |
| colon / lower | 352 | 234 | -118 |
| dash / lower | 153 | 124 | -29 |
| dash / upper | 141 | 147 | +6 |
| dotted aabb.ccdd.eeff / upper | 127 | 90 | -37 |
| dotted aabb.ccdd.eeff / lower | 123 | 96 | -27 |
| colon / mixed | 97 | 74 | -23 |
| dash / mixed | 29 | 44 | +15 |
| dotted aabb.ccdd.eeff / mixed | 35 | 24 | -11 |

### Real values by family

| | v3 | v4 | change |
|---|---|---|---|
| structured | 764 | 606 | -158 |
| contrast | 585 | 358 | -227 |
| cross_anchor | 0 | 80 | +80 |
| decoy_pair | 54 | 42 | -12 |
| prose | 30 | 23 | -7 |

### Real values by context

| | v3 | v4 | change |
|---|---|---|---|
| prose | 645 | 488 | -157 |
| container:csv_header | 175 | 97 | -78 |
| container:csv_snake | 158 | 94 | -64 |
| container:pipe_table | 157 | 142 | -15 |
| container:log | 79 | 89 | +10 |
| container:csv_noheader | 68 | 52 | -16 |
| container:dialogue | 47 | 43 | -4 |
| container:json | 38 | 42 | +4 |
| container:key_value | 28 | 40 | +12 |
| container:config | 14 | 7 | -7 |
| table / csv-like line | 13 | 9 | -4 |
| label: value line | 11 | 6 | -5 |

### Character right after a real value

| | v3 | v4 | change |
|---|---|---|---|
| space | 674 | 588 | -86 |
| , | 400 | 241 | -159 |
| line break | 208 | 154 | -54 |
| ; | 77 | 54 | -23 |
| " | 38 | 43 | +5 |
| . | 32 | 26 | -6 |
| ) | 3 | 1 | -2 |
| ] | 1 | 1 | +0 |
| » | 0 | 1 | +1 |

### Look-alikes by kind

| | v3 | v4 | change |
|---|---|---|---|
| mac_3_to_5_groups | 133 | 103 | -30 |
| mac_fragment_dashed | 0 | 103 | +103 |

### Look-alikes by family

| | v3 | v4 | change |
|---|---|---|---|
| cross_anchor | 0 | 80 | +80 |
| decoy_pair | 54 | 42 | -12 |
| pii_free | 35 | 54 | +19 |
| structured | 44 | 30 | -14 |

### Look-alikes by context

| | v3 | v4 | change |
|---|---|---|---|
| prose | 81 | 162 | +81 |
| container:csv_snake | 10 | 2 | -8 |
| label: value line | 7 | 9 | +2 |
| container:pipe_table | 8 | 8 | +0 |
| container:key_value | 7 | 1 | -6 |
| container:dialogue | 6 | 3 | -3 |
| container:csv_header | 5 | 5 | +0 |
| container:csv_noheader | 4 | 5 | +1 |
| table / csv-like line | 1 | 5 | +4 |
| container:log | 2 | 4 | +2 |
| container:config | 2 | 0 | -2 |
| container:json | 0 | 2 | +2 |


## email

### Real values by format

| | v3 | v4 | change |
|---|---|---|---|
| local part: dot | 737 | 669 | -68 |
| local part: digit | 251 | 223 | -28 |
| local part: dot+digit | 225 | 173 | -52 |
| local part: underscore | 219 | 178 | -41 |
| local part: letters only | 126 | 107 | -19 |
| local part: hyphen | 24 | 20 | -4 |

### Real values by family

| | v3 | v4 | change |
|---|---|---|---|
| structured | 1,129 | 999 | -130 |
| form | 250 | 198 | -52 |
| punct | 115 | 95 | -20 |
| clerical | 59 | 56 | -3 |
| prose | 29 | 22 | -7 |

### Real values by context

| | v3 | v4 | change |
|---|---|---|---|
| container:csv_noheader | 600 | 583 | -17 |
| label: value line | 250 | 198 | -52 |
| container:csv_header | 134 | 74 | -60 |
| prose | 134 | 110 | -24 |
| container:pipe_table | 100 | 128 | +28 |
| container:csv_snake | 127 | 71 | -56 |
| table / csv-like line | 69 | 63 | -6 |
| container:json | 47 | 30 | -17 |
| container:log | 45 | 43 | -2 |
| container:dialogue | 28 | 34 | +6 |
| container:key_value | 26 | 22 | -4 |
| container:config | 22 | 14 | -8 |

### Character right after a real value

| | v3 | v4 | change |
|---|---|---|---|
| , | 537 | 429 | -108 |
| line break | 393 | 298 | -95 |
| ; | 232 | 247 | +15 |
| space | 216 | 230 | +14 |
| ! | 115 | 95 | -20 |
| " | 48 | 33 | -15 |
| end of text | 22 | 16 | -6 |
| . | 13 | 17 | +4 |
| ) | 1 | 4 | +3 |
| » | 3 | 1 | -2 |
| ] | 2 | 0 | -2 |

### Look-alikes by kind

| | v3 | v4 | change |
|---|---|---|---|
| email_double_at | 219 | 185 | -34 |
| email_no_at | 219 | 185 | -34 |
| email_dotless_domain | 219 | 185 | -34 |
| email_localhost | 219 | 185 | -34 |

### Look-alikes by family

| | v3 | v4 | change |
|---|---|---|---|
| structured | 338 | 302 | -36 |
| form | 219 | 192 | -27 |
| pii_free | 211 | 164 | -47 |
| punct | 69 | 57 | -12 |
| clerical | 39 | 25 | -14 |

### Look-alikes by context

| | v3 | v4 | change |
|---|---|---|---|
| label: value line | 268 | 234 | -34 |
| prose | 222 | 173 | -49 |
| container:csv_noheader | 186 | 182 | -4 |
| table / csv-like line | 48 | 31 | -17 |
| container:csv_header | 40 | 16 | -24 |
| container:pipe_table | 26 | 37 | +11 |
| container:csv_snake | 29 | 19 | -10 |
| container:log | 12 | 20 | +8 |
| container:json | 13 | 8 | -5 |
| container:dialogue | 13 | 13 | +0 |
| container:key_value | 10 | 4 | -6 |
| container:config | 9 | 3 | -6 |

