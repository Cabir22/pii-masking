# MAC addresses on the benchmark (374 gold values in the first 5,000 documents)

Track M. Outcome per gold MAC (exact = correct; boundary = fully masked, right label, other span; wrong_type = fully masked, other label; partly_masked = some characters visible; missed = nothing masked).

| v4.2 vs m1 | Values |
|---|---|
| v4.2 ok / m1 ok | 246 |
| v4.2 ok / m1 wrong | 112 |
| v4.2 wrong / m1 wrong | 9 |
| v4.2 wrong / m1 ok | 7 |

**v42 outcome:** correct: 358; missed: 9; partly_masked: 6; boundary: 1

**m1 outcome:** correct: 253; missed: 89; partly_masked: 32

## by separator

| Value | Gold | v4.2 not exact | m1 not exact | m1 missed | m1 partly | m1 wrong type |
|---|---|---|---|---|---|---|
| : | 374 | 16 | 121 | 89 | 32 | 0 |

## by case

| Value | Gold | v4.2 not exact | m1 not exact | m1 missed | m1 partly | m1 wrong type |
|---|---|---|---|---|---|---|
| upper | 317 | 14 | 116 | 86 | 30 | 0 |
| lower | 53 | 1 | 3 | 2 | 1 | 0 |
| digits only | 4 | 1 | 2 | 1 | 1 | 0 |

## by grouping

| Value | Gold | v4.2 not exact | m1 not exact | m1 missed | m1 partly | m1 wrong type |
|---|---|---|---|---|---|---|
| 2x6 | 374 | 16 | 121 | 89 | 32 | 0 |

## by label_word_near

| Value | Gold | v4.2 not exact | m1 not exact | m1 missed | m1 partly | m1 wrong type |
|---|---|---|---|---|---|---|
| True | 189 | 7 | 55 | 44 | 11 | 0 |
| False | 185 | 9 | 66 | 45 | 21 | 0 |

## by line_start

| Value | Gold | v4.2 not exact | m1 not exact | m1 missed | m1 partly | m1 wrong type |
|---|---|---|---|---|---|---|
| False | 370 | 16 | 121 | 89 | 32 | 0 |
| True | 4 | 0 | 0 | 0 | 0 | 0 |

## by next_char

| Value | Gold | v4.2 not exact | m1 not exact | m1 missed | m1 partly | m1 wrong type |
|---|---|---|---|---|---|---|
| ' ' | 314 | 15 | 117 | 86 | 31 | 0 |
| '-' | 26 | 1 | 4 | 3 | 1 | 0 |
| '"' | 17 | 0 | 0 | 0 | 0 | 0 |
| ';' | 10 | 0 | 0 | 0 | 0 | 0 |
| '\n' | 7 | 0 | 0 | 0 | 0 | 0 |

## by prev_char

| Value | Gold | v4.2 not exact | m1 not exact | m1 missed | m1 partly | m1 wrong type |
|---|---|---|---|---|---|---|
| ' ' | 340 | 16 | 121 | 89 | 32 | 0 |
| '"' | 17 | 0 | 0 | 0 | 0 | 0 |
| '=' | 7 | 0 | 0 | 0 | 0 | 0 |
| ';' | 6 | 0 | 0 | 0 | 0 | 0 |
| '\n' | 4 | 0 | 0 | 0 | 0 | 0 |

m1 wrong-type predictions: 

## v42: MAC predictions on non-MAC text (0)


## m1: MAC predictions on non-MAC text (0)


## m1 failures where v4.2 is exact (first 30)

- missed: `0F:41:18:73:39:C1` sep :, upper, 2x6 … da v9.4.52 kodu qeyd olunub. MAC ünvanı 0F:41:18:73:39:C1 kimi göstərilib; hesab ç
- missed: `17:B5:DB:31:47:36` sep :, upper, 2x6 … sənədlə birlikdə qorunub. Cihazın MAC-ı 17:B5:DB:31:47:36 yazılıb; iş qovluğu sent
- missed: `0F:E8:2C:4F:4E:0F` sep :, upper, 2x6 … dlə birlikdə qorunub. Texniki müraciətə 0F:E8:2C:4F:4E:0F MAC ünvanını əlavə etmiş
- missed: `FA:1B:0C:DC:28:6B` sep :, upper, 2x6 … eyd ilə birlikdə saxlanılıb. MAC ünvanı FA:1B:0C:DC:28:6B kimi göstərilib; həmin m
- missed: `F3:B1:D1:E5:5C:B1` sep :, upper, 2x6 …  birlikdə saxlanılıb. Şəbəkə profilində F3:B1:D1:E5:5C:B1 görünür; həmin məlumat h
- partly_masked: `0A:BC:4F:DC:FA:3E` sep :, upper, 2x6 … 8764866 hesabını qeyd etmişəm. Routerdə 0A:BC:4F:DC:FA:3E MAC ünvanını görürəm; su
- missed: `4D:9D:F6:17:07:D3` sep :, upper, 2x6 … ün 17.1.9 göstərilib. Şəbəkə profilində 4D:9D:F6:17:07:D3 görünür; dekabr ayında a
- partly_masked: `0A:CD:1B:82:9C:3A` sep :, upper, 2x6 … dində ayrıca qeyd edilib. Cihazın MAC-ı 0A:CD:1B:82:9C:3A yazılıb; həmin məlumat ə
- missed: `51:4E:73:9D:88:FD` sep :, upper, 2x6 … nədlə birlikdə qorunub. Router qeydində 51:4E:73:9D:88:FD qeyd olunub; surəti arxi
- missed: `16:85:DB:32:0C:52` sep :, upper, 2x6 …  birlikdə saxlanılıb. Şəbəkə profilində 16:85:DB:32:0C:52 görünür; surəti keyfiyyə
- partly_masked: `7D:1F:AB:6B:58:F1` sep :, upper, 2x6 … sənədində birlikdə saxlanılıb. Routerdə 7D:1F:AB:6B:58:F1 MAC ünvanını görürəm; he
- missed: `4E:54:E7:FD:55:63` sep :, upper, 2x6 … də də ayrıca qeyd edilib. Cihazın MAC-ı 4E:54:E7:FD:55:63 yazılıb; surəti keyfiyyə
- missed: `67:F5:CA:85:94:DE` sep :, upper, 2x6 … materiallarına əlavə edilib. MAC ünvanı 67:F5:CA:85:94:DE kimi gosterlib; arxiv qe
- missed: `3D:F1:D4:AB:CC:03` sep :, upper, 2x6 … laraq 18.6.2 yazılıb. Texniki müraciətə 3D:F1:D4:AB:CC:03 MAC ünvanını əlavə etmiş
- partly_masked: `54:54:0C:6C:A5:D0` sep :, upper, 2x6 … laraq 15.7.4 yazılıb. Şəbəkə profilində 54:54:0C:6C:A5:D0 görünür; həmin məlumat i
- missed: `16:DB:EB:CE:33:A6` sep :, upper, 2x6 …  paketə daxil edilib. Şəbəkə profilində 16:DB:EB:CE:33:A6 görünür; surəti sənəd dö
- missed: `95:99:FD:5F:BC:9B` sep :, upper, 2x6 … də də arxivə köçürülüb. Router qeydində 95:99:FD:5F:BC:9B qeyd olunub; hesap çıxar
- partly_masked: `DB:29:29:6C:F4:E0` sep :, upper, 2x6 … daxilində də arxivə köçürülüb. Routerdə DB:29:29:6C:F4:E0 MAC ünvanını görürəm. Kö
- missed: `3B:5B:C3:8D:52:82` sep :, upper, 2x6 … qovluğa əlavə olunub. Şəbəkə profilində 3B:5B:C3:8D:52:82 görünür; fevral ayında k
- missed: `33:10:D2:05:2B:DA` sep :, upper, 2x6 … üçün 18.8.3 göstərilib. Router qeydində 33:10:D2:05:2B:DA qeyd olunub; arxiv qeydi
- missed: `96:5C:36:D1:3A:01` sep :, upper, 2x6 … 14.8.9 kimi saxlanılıb. Router qeydində 96:5C:36:D1:3A:01 qeyd olunb; surəti sənəd
- partly_masked: `EA:CB:1C:ED:CA:13` sep :, upper, 2x6 … ə qovluğa əlavə olunub. Router qeydində EA:CB:1C:ED:CA:13 qeyd olunub; həmin məlum
- partly_masked: `39:09:C1:F9:9E:FE` sep :, upper, 2x6 … iallarına əlavə edilib. Router qeydində 39:09:C1:F9:9E:FE qeyd olunub; həmin məlum
- missed: `25:2B:0C:07:B1:AD` sep :, upper, 2x6 … lində də ayrıca qeyd edilib. MAC ünvanı 25:2B:0C:07:B1:AD kimi göstərilib; yanvar 
- partly_masked: `7D:48:64:26:89:EE` sep :, upper, 2x6 … bəndi üçün 2.7.2 göstərilib. MAC ünvanı 7D:48:64:26:89:EE kimi göstərilib; həmin m
- missed: `89:E8:4B:4E:56:4A` sep :, upper, 2x6 … matı 12.1.3 kimi saxlanılıb. MAC ünvanı 89:E8:4B:4E:56:4A kimi göstərilib; gündəli
- missed: `4B:F6:8D:CF:91:31` sep :, upper, 2x6 … llarına əlavə edilib. Şəbəkə profilində 4B:F6:8D:CF:91:31 görünür; həmin məlumat s
- partly_masked: `16:D1:68:9B:4D:8B` sep :, upper, 2x6 … materiallarına əlavə edilib. MAC ünvanı 16:D1:68:9B:4D:8B kimi göstərilib; həmin m
- missed: `67:53:C4:E8:5C:69` sep :, upper, 2x6 … ə qovluğa əlavə olunub. Router qeydində 67:53:C4:E8:5C:69 qeyd olunub; gündəlik qe
- missed: `98:9B:EA:59:E5:AB` sep :, upper, 2x6 … xilində də arxivə köçürülüb. MAC ünvanı 98:9B:EA:59:E5:AB kimi göstərilib; aprel a
