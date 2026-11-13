# Left-context words of v4's failing benchmark frames, in training

| frame word | next digit token | v4 targeted | v4 LLM | v4 old | v4.1 targeted | v4.1 LLM | v4.1 old |
|---|---|---|---|---|---|---|---|
| Logda … (IPv4/IPv6 X qeyd olunub) | labelled ACCESS_TOKEN | 0 | 1 | 0 | 0 | 1 | 0 |
| Logda … (IPv4/IPv6 X qeyd olunub) | labelled IPV4_ADDRESS | 0 | 6 | 3 | 0 | 8 | 3 |
| Logda … (IPv4/IPv6 X qeyd olunub) | labelled IPV6_ADDRESS | 0 | 0 | 1 | 0 | 0 | 1 |
| Logda … (IPv4/IPv6 X qeyd olunub) | labelled TIME | 0 | 0 | 1 | 0 | 0 | 1 |
| Logda … (IPv4/IPv6 X qeyd olunub) | look-alike AMOUNT | 0 | 1 | 0 | 0 | 0 | 0 |
| Logda … (IPv4/IPv6 X qeyd olunub) | look-alike SSN_LIKE_CODE | 0 | 1 | 0 | 0 | 0 | 0 |
| Logda … (IPv4/IPv6 X qeyd olunub) | look-alike TIMESTAMP | 0 | 1 | 0 | 0 | 1 | 0 |
| Logda … (IPv4/IPv6 X qeyd olunub) | unlabelled | 0 | 1 | 14 | 0 | 0 | 14 |
| Server … (IPv6-si / ünvanı X yazılıb) | labelled ACCESS_TOKEN | 1 | 0 | 0 | 0 | 0 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | labelled DATE | 0 | 2 | 6 | 0 | 1 | 6 |
| Server … (IPv6-si / ünvanı X yazılıb) | labelled IPV4_ADDRESS | 0 | 17 | 16 | 56 | 15 | 16 |
| Server … (IPv6-si / ünvanı X yazılıb) | labelled IPV6_ADDRESS | 0 | 7 | 4 | 0 | 7 | 4 |
| Server … (IPv6-si / ünvanı X yazılıb) | labelled TELEPHONENUM | 0 | 1 | 1 | 0 | 1 | 1 |
| Server … (IPv6-si / ünvanı X yazılıb) | labelled TIME | 0 | 0 | 1 | 0 | 0 | 1 |
| Server … (IPv6-si / ünvanı X yazılıb) | labelled ZIPCODE | 0 | 1 | 0 | 0 | 1 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike COORDINATES | 0 | 1 | 0 | 0 | 1 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike ERROR_CODE | 0 | 2 | 0 | 0 | 3 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike IP_INVALID_OCTET | 0 | 3 | 0 | 0 | 5 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike IP_LIKE_VERSION | 0 | 2 | 0 | 0 | 1 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike MAC_LIKE_HASH | 0 | 0 | 0 | 0 | 1 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike PLATE_LIKE_CODE | 0 | 3 | 0 | 0 | 4 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike PORT | 0 | 1 | 0 | 0 | 0 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike REF_CODE | 0 | 2 | 0 | 0 | 2 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike SHA256 | 0 | 1 | 0 | 0 | 1 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike door_code | 6 | 0 | 0 | 5 | 0 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike floor_number | 0 | 1 | 0 | 0 | 1 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike ipv4_octet_over_255 | 0 | 14 | 0 | 0 | 14 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike public_key_ssh | 0 | 0 | 1 | 0 | 0 | 1 |
| Server … (IPv6-si / ünvanı X yazılıb) | unlabelled | 0 | 83 | 397 | 0 | 87 | 397 |
| Təqvimdə X görünür | labelled TIME | 2 | 0 | 0 | 2 | 0 | 0 |
| Təqvimdə X görünür | look-alike time_bad_hour | 1 | 0 | 0 | 1 | 0 | 0 |
| Təqvimdə X görünür | look-alike time_bad_minute | 1 | 0 | 0 | 1 | 0 | 0 |
| … üzrə ZIP X görünür | labelled DATE | 0 | 0 | 1 | 0 | 0 | 1 |
| … üzrə ZIP X görünür | labelled ZIPCODE | 12 | 6 | 5 | 121 | 4 | 5 |
| … üzrə ZIP X görünür | look-alike zip_wrong_length | 0 | 135 | 0 | 15 | 118 | 0 |
| … üzrə ZIP X görünür | unlabelled | 0 | 2 | 0 | 0 | 1 | 0 |
| IPv6 ünvanı X | labelled API_KEY | 1 | 0 | 0 | 0 | 0 | 0 |
| IPv6 ünvanı X | labelled AZ_DRIVER_LICENSE_NUMBER | 4 | 0 | 0 | 2 | 0 | 0 |
| IPv6 ünvanı X | labelled AZ_FIN | 1 | 0 | 0 | 0 | 0 | 0 |
| IPv6 ünvanı X | labelled AZ_ID_CARD_NUMBER | 3 | 0 | 0 | 0 | 0 | 0 |
| IPv6 ünvanı X | labelled AZ_PASSPORT_NUMBER | 1 | 0 | 0 | 0 | 0 | 0 |
| IPv6 ünvanı X | labelled AZ_VOEN | 1 | 0 | 0 | 0 | 0 | 0 |
| IPv6 ünvanı X | labelled DATE | 0 | 0 | 0 | 1 | 0 | 0 |
| IPv6 ünvanı X | labelled GIVENNAME | 0 | 0 | 0 | 1 | 0 | 0 |
| IPv6 ünvanı X | labelled IBAN | 0 | 0 | 0 | 3 | 0 | 0 |
| IPv6 ünvanı X | labelled IPV6_ADDRESS | 303 | 606 | 55 | 599 | 595 | 55 |
| IPv6 ünvanı X | labelled MAC_ADDRESS | 0 | 8 | 0 | 0 | 8 | 0 |
| IPv6 ünvanı X | labelled STREET | 1 | 0 | 0 | 1 | 0 | 0 |
| IPv6 ünvanı X | labelled SURNAME | 1 | 0 | 0 | 0 | 0 | 0 |
| IPv6 ünvanı X | labelled TIME | 0 | 0 | 0 | 1 | 0 | 0 |
| IPv6 ünvanı X | labelled ZIPCODE | 0 | 0 | 1 | 0 | 0 | 1 |
| IPv6 ünvanı X | look-alike ipv6_non_hex | 38 | 45 | 0 | 40 | 41 | 0 |
| IPv6 ünvanı X | look-alike ipv6_triple_colon | 36 | 158 | 0 | 33 | 156 | 0 |
| IPv6 ünvanı X | look-alike ipv6_two_compressions | 35 | 30 | 0 | 40 | 32 | 0 |
| IPv6 ünvanı X | unlabelled | 0 | 4 | 2 | 0 | 4 | 2 |
| Mənbə IP X (v4 finds 92%) | labelled IPV4_ADDRESS | 0 | 3 | 5 | 0 | 7 | 5 |
| Mənbə IP X (v4 finds 92%) | look-alike ipv4_octet_over_255 | 0 | 12 | 0 | 0 | 13 | 0 |
| Mənbə IP X (v4 finds 92%) | unlabelled | 0 | 2 | 2 | 0 | 1 | 2 |
