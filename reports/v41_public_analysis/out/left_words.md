# Left-context words of v4's failing benchmark frames, in training

| frame word | next digit token | v3 targeted | v3 LLM | v3 old | v4 targeted | v4 LLM | v4 old |
|---|---|---|---|---|---|---|---|
| Logda … (IPv4/IPv6 X qeyd olunub) | labelled ACCESS_TOKEN | 0 | 2 | 0 | 0 | 1 | 0 |
| Logda … (IPv4/IPv6 X qeyd olunub) | labelled IPV4_ADDRESS | 0 | 7 | 3 | 0 | 6 | 3 |
| Logda … (IPv4/IPv6 X qeyd olunub) | labelled IPV6_ADDRESS | 0 | 0 | 1 | 0 | 0 | 1 |
| Logda … (IPv4/IPv6 X qeyd olunub) | labelled TIME | 0 | 0 | 1 | 0 | 0 | 1 |
| Logda … (IPv4/IPv6 X qeyd olunub) | look-alike AMOUNT | 0 | 0 | 0 | 0 | 1 | 0 |
| Logda … (IPv4/IPv6 X qeyd olunub) | look-alike SSN_LIKE_CODE | 0 | 0 | 0 | 0 | 1 | 0 |
| Logda … (IPv4/IPv6 X qeyd olunub) | look-alike TIMESTAMP | 0 | 1 | 0 | 0 | 1 | 0 |
| Logda … (IPv4/IPv6 X qeyd olunub) | unlabelled | 0 | 1 | 16 | 0 | 1 | 14 |
| Server … (IPv6-si / ünvanı X yazılıb) | labelled ACCESS_TOKEN | 1 | 0 | 0 | 1 | 0 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | labelled BUILDINGNUM | 0 | 0 | 1 | 0 | 0 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | labelled DATE | 0 | 2 | 6 | 0 | 2 | 6 |
| Server … (IPv6-si / ünvanı X yazılıb) | labelled IPV4_ADDRESS | 0 | 18 | 22 | 0 | 17 | 16 |
| Server … (IPv6-si / ünvanı X yazılıb) | labelled IPV6_ADDRESS | 0 | 7 | 5 | 0 | 7 | 4 |
| Server … (IPv6-si / ünvanı X yazılıb) | labelled TELEPHONENUM | 0 | 0 | 1 | 0 | 1 | 1 |
| Server … (IPv6-si / ünvanı X yazılıb) | labelled TIME | 0 | 0 | 2 | 0 | 0 | 1 |
| Server … (IPv6-si / ünvanı X yazılıb) | labelled ZIPCODE | 0 | 1 | 0 | 0 | 1 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike COORDINATES | 0 | 1 | 0 | 0 | 1 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike ERROR_CODE | 0 | 2 | 0 | 0 | 2 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike IP_INVALID_OCTET | 0 | 8 | 0 | 0 | 3 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike IP_LIKE_VERSION | 0 | 0 | 0 | 0 | 2 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike LOYALTY_CARD_LUHN_BAD | 0 | 1 | 0 | 0 | 0 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike MAC_LIKE_HASH | 0 | 1 | 0 | 0 | 0 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike PLATE_LIKE_CODE | 0 | 4 | 0 | 0 | 3 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike PORT | 0 | 2 | 0 | 0 | 1 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike REF_CODE | 0 | 2 | 0 | 0 | 2 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike SHA256 | 0 | 1 | 0 | 0 | 1 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike TIMESTAMP | 0 | 1 | 0 | 0 | 0 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike door_code | 0 | 0 | 0 | 6 | 0 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike floor_number | 0 | 1 | 0 | 0 | 1 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike ipv4_octet_over_255 | 0 | 13 | 0 | 0 | 14 | 0 |
| Server … (IPv6-si / ünvanı X yazılıb) | look-alike public_key_ssh | 0 | 0 | 1 | 0 | 0 | 1 |
| Server … (IPv6-si / ünvanı X yazılıb) | unlabelled | 0 | 85 | 467 | 0 | 83 | 397 |
| Təqvimdə X görünür | labelled TIME | 0 | 0 | 0 | 2 | 0 | 0 |
| Təqvimdə X görünür | look-alike time_bad_hour | 0 | 0 | 0 | 1 | 0 | 0 |
| Təqvimdə X görünür | look-alike time_bad_minute | 0 | 0 | 0 | 1 | 0 | 0 |
| … üzrə ZIP X görünür | labelled DATE | 0 | 0 | 1 | 0 | 0 | 1 |
| … üzrə ZIP X görünür | labelled ZIPCODE | 38 | 3 | 8 | 12 | 6 | 5 |
| … üzrə ZIP X görünür | look-alike zip_wrong_length | 0 | 150 | 0 | 0 | 135 | 0 |
| … üzrə ZIP X görünür | unlabelled | 0 | 2 | 1 | 0 | 2 | 0 |
| IPv6 ünvanı X | labelled API_KEY | 2 | 0 | 0 | 1 | 0 | 0 |
| IPv6 ünvanı X | labelled AZ_DRIVER_LICENSE_NUMBER | 3 | 0 | 0 | 4 | 0 | 0 |
| IPv6 ünvanı X | labelled AZ_FIN | 0 | 0 | 0 | 1 | 0 | 0 |
| IPv6 ünvanı X | labelled AZ_ID_CARD_NUMBER | 3 | 0 | 0 | 3 | 0 | 0 |
| IPv6 ünvanı X | labelled AZ_PASSPORT_NUMBER | 0 | 0 | 0 | 1 | 0 | 0 |
| IPv6 ünvanı X | labelled AZ_VOEN | 0 | 0 | 0 | 1 | 0 | 0 |
| IPv6 ünvanı X | labelled GIVENNAME | 1 | 0 | 0 | 0 | 0 | 0 |
| IPv6 ünvanı X | labelled IPV4_ADDRESS | 1 | 0 | 0 | 0 | 0 | 0 |
| IPv6 ünvanı X | labelled IPV6_ADDRESS | 503 | 626 | 61 | 303 | 606 | 55 |
| IPv6 ünvanı X | labelled MAC_ADDRESS | 0 | 10 | 0 | 0 | 8 | 0 |
| IPv6 ünvanı X | labelled PAYMENT_CARD_NUMBER | 2 | 0 | 0 | 0 | 0 | 0 |
| IPv6 ünvanı X | labelled STREET | 1 | 0 | 0 | 1 | 0 | 0 |
| IPv6 ünvanı X | labelled SURNAME | 0 | 0 | 0 | 1 | 0 | 0 |
| IPv6 ünvanı X | labelled TELEPHONENUM | 2 | 0 | 0 | 0 | 0 | 0 |
| IPv6 ünvanı X | labelled ZIPCODE | 0 | 0 | 1 | 0 | 0 | 1 |
| IPv6 ünvanı X | look-alike ipv6_non_hex | 38 | 53 | 0 | 38 | 45 | 0 |
| IPv6 ünvanı X | look-alike ipv6_triple_colon | 53 | 168 | 0 | 36 | 158 | 0 |
| IPv6 ünvanı X | look-alike ipv6_two_compressions | 42 | 39 | 0 | 35 | 30 | 0 |
| IPv6 ünvanı X | unlabelled | 0 | 4 | 2 | 0 | 4 | 2 |
| Mənbə IP X (v4 finds 92%) | labelled IPV4_ADDRESS | 0 | 6 | 5 | 0 | 3 | 5 |
| Mənbə IP X (v4 finds 92%) | labelled IPV6_ADDRESS | 0 | 0 | 1 | 0 | 0 | 0 |
| Mənbə IP X (v4 finds 92%) | look-alike ipv4_octet_over_255 | 0 | 11 | 0 | 0 | 12 | 0 |
| Mənbə IP X (v4 finds 92%) | unlabelled | 0 | 2 | 5 | 0 | 2 | 2 |
