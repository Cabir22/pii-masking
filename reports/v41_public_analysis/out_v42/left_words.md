# Left-context words of v4's failing benchmark frames, in training

| frame word | next digit token | v4.1 targeted | v4.1 LLM | v4.1 old | v4.2 targeted | v4.2 LLM | v4.2 old |
|---|---|---|---|---|---|---|---|
| Logda … (IPv4/IPv6 X qeyd olunub) | labelled ACCESS_TOKEN | 0 | 1 | 0 | 0 | 2 | 0 |
| Logda … (IPv4/IPv6 X qeyd olunub) | labelled IPV4_ADDRESS | 0 | 8 | 3 | 0 | 5 | 3 |
| Logda … (IPv4/IPv6 X qeyd olunub) | labelled IPV6_ADDRESS | 0 | 0 | 1 | 0 | 0 | 1 |
| Logda … (IPv4/IPv6 X qeyd olunub) | labelled TIME | 0 | 0 | 1 | 0 | 0 | 1 |
| Logda … (IPv4/IPv6 X qeyd olunub) | look-alike AMOUNT | 0 | 0 | 0 | 0 | 1 | 0 |
| Logda … (IPv4/IPv6 X qeyd olunub) | look-alike SSN_LIKE_CODE | 0 | 0 | 0 | 0 | 1 | 0 |
| Logda … (IPv4/IPv6 X qeyd olunub) | look-alike TIMESTAMP | 0 | 1 | 0 | 0 | 1 | 0 |
| Logda … (IPv4/IPv6 X qeyd olunub) | unlabelled | 0 | 0 | 14 | 0 | 1 | 14 |
| Server … (IPv6-si / ünvanı X yazılıb) | labelled DATE | 0 | 1 | 6 | 0 | 0 | 6 |
| Server … (IPv6-si / ünvanı X yazılıb) | labelled IPV4_ADDRESS | 56 | 15 | 16 | 72 | 16 | 16 |
| Server … (IPv6-si / ünvanı X yazılıb) | labelled IPV6_ADDRESS | 0 | 7 | 4 | 68 | 7 | 4 |
| Server … (IPv6-si / ünvanı X yazılıb) | labelled TELEPHONENUM | 0 | 1 | 1 | 0 | 1 | 1 |
| Server … (IPv6-si / ünvanı X yazılıb) | labelled TIME | 0 | 0 | 1 | 0 | 0 | 1 |
| Server … (IPv6-si / ünvanı X yazılıb) | labelled ZIPCODE | 0 | 1 | 0 | 0 | 1 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike COORDINATES | 0 | 1 | 0 | 0 | 1 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike ERROR_CODE | 0 | 3 | 0 | 0 | 2 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike IP_INVALID_OCTET | 0 | 5 | 0 | 0 | 5 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike IP_LIKE_VERSION | 0 | 1 | 0 | 0 | 2 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike MAC_LIKE_HASH | 0 | 1 | 0 | 0 | 1 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike PLATE_LIKE_CODE | 0 | 4 | 0 | 0 | 2 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike PORT | 0 | 0 | 0 | 0 | 1 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike REF_CODE | 0 | 2 | 0 | 0 | 2 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike SHA256 | 0 | 1 | 0 | 0 | 1 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike door_code | 5 | 0 | 0 | 6 | 0 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike floor_number | 0 | 1 | 0 | 0 | 1 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike ipv4_octet_over_255 | 0 | 14 | 0 | 0 | 15 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike ipv6_compressed_bad | 0 | 0 | 0 | 36 | 0 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike public_key_ssh | 0 | 0 | 1 | 0 | 0 | 1 |
| Server … (IPv6-si / ünvanı X yazılıb) | unlabelled | 0 | 87 | 397 | 0 | 87 | 397 |
| Təqvimdə X görünür | labelled TIME | 2 | 0 | 0 | 9 | 0 | 0 |
| Təqvimdə X görünür | look-alike time_bad_hour | 1 | 0 | 0 | 4 | 0 | 0 |
| Təqvimdə X görünür | look-alike time_bad_minute | 1 | 0 | 0 | 2 | 0 | 0 |
| Təqvimdə X görünür | look-alike time_hour_near | 0 | 0 | 0 | 2 | 0 | 0 |
| Təqvimdə X görünür | look-alike time_minute_near | 0 | 0 | 0 | 1 | 0 | 0 |
| … üzrə ZIP X görünür | labelled DATE | 0 | 0 | 1 | 0 | 0 | 1 |
| … üzrə ZIP X görünür | labelled ZIPCODE | 121 | 4 | 5 | 163 | 6 | 5 |
| … üzrə ZIP X görünür | look-alike zip_wrong_length | 15 | 118 | 0 | 8 | 125 | 0 |
| … üzrə ZIP X görünür | unlabelled | 0 | 1 | 0 | 0 | 2 | 0 |
| IPv6 ünvanı X | labelled AZ_DRIVER_LICENSE_NUMBER | 2 | 0 | 0 | 2 | 0 | 0 |
| IPv6 ünvanı X | labelled AZ_FIN | 0 | 0 | 0 | 1 | 0 | 0 |
| IPv6 ünvanı X | labelled AZ_ID_CARD_NUMBER | 0 | 0 | 0 | 3 | 0 | 0 |
| IPv6 ünvanı X | labelled DATE | 1 | 0 | 0 | 1 | 0 | 0 |
| IPv6 ünvanı X | labelled EMAIL | 0 | 0 | 0 | 1 | 0 | 0 |
| IPv6 ünvanı X | labelled GIVENNAME | 1 | 0 | 0 | 0 | 0 | 0 |
| IPv6 ünvanı X | labelled IBAN | 3 | 0 | 0 | 0 | 0 | 0 |
| IPv6 ünvanı X | labelled IPV4_ADDRESS | 0 | 0 | 0 | 1 | 0 | 0 |
| IPv6 ünvanı X | labelled IPV6_ADDRESS | 599 | 595 | 55 | 846 | 613 | 55 |
| IPv6 ünvanı X | labelled MAC_ADDRESS | 0 | 8 | 0 | 1 | 9 | 0 |
| IPv6 ünvanı X | labelled STREET | 1 | 0 | 0 | 1 | 0 | 0 |
| IPv6 ünvanı X | labelled SURNAME | 0 | 0 | 0 | 1 | 0 | 0 |
| IPv6 ünvanı X | labelled TIME | 1 | 0 | 0 | 2 | 0 | 0 |
| IPv6 ünvanı X | labelled ZIPCODE | 0 | 0 | 1 | 0 | 0 | 1 |
| IPv6 ünvanı X | look-alike ipv6_compressed_bad | 0 | 0 | 0 | 19 | 0 | 0 |
| IPv6 ünvanı X | look-alike ipv6_non_hex | 40 | 41 | 0 | 33 | 47 | 0 |
| IPv6 ünvanı X | look-alike ipv6_triple_colon | 33 | 156 | 0 | 31 | 148 | 0 |
| IPv6 ünvanı X | look-alike ipv6_two_compressions | 40 | 32 | 0 | 22 | 40 | 0 |
| IPv6 ünvanı X | unlabelled | 0 | 4 | 2 | 0 | 3 | 2 |
| Mənbə IP X (v4 finds 92%) | labelled IPV4_ADDRESS | 0 | 7 | 5 | 0 | 6 | 5 |
| Mənbə IP X (v4 finds 92%) | look-alike ipv4_octet_over_255 | 0 | 13 | 0 | 0 | 12 | 0 |
| Mənbə IP X (v4 finds 92%) | unlabelled | 0 | 1 | 2 | 0 | 1 | 2 |
