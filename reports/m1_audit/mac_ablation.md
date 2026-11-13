# MAC ablation on documents where m1 fails and v4.2 is exact (track M, m1)

40 documents. One change per column.

| Change | exact | partly | missed |
|---|---|---|---|
| as_is | 0 | 12 | 28 |
| no_hard_negatives | 5 | 10 | 25 |
| no_versions | 10 | 9 | 21 |
| sentence_only | 40 | 0 | 0 |

| doc | MAC | hard negatives replaced | as is | no HN | no versions | sentence only |
|---|---|---|---|---|---|---|
| bench_az_000006 | `0F:41:18:73:39:C1` | `123` | missed | missed | exact | exact |
| bench_az_000096 | `17:B5:DB:31:47:36` | `1234` | missed | missed | missed | exact |
| bench_az_000110 | `0F:E8:2C:4F:4E:0F` | `0501234567`, `AZ100000` | missed | missed | missed | exact |
| bench_az_000123 | `FA:1B:0C:DC:28:6B` | `1234` | missed | missed | missed | exact |
| bench_az_000132 | `F3:B1:D1:E5:5C:B1` | `123456` | missed | missed | missed | exact |
| bench_az_000188 | `0A:BC:4F:DC:FA:3E` | `12AB345678`, `7636051` | partly | partly | exact | exact |
| bench_az_000201 | `4D:9D:F6:17:07:D3` | `ABC` | missed | missed | missed | exact |
| bench_az_000206 | `0A:CD:1B:82:9C:3A` | – | partly | partly | exact | exact |
| bench_az_000207 | `51:4E:73:9D:88:FD` | `küçə yoxdur` | missed | partly | partly | exact |
| bench_az_000270 | `16:85:DB:32:0C:52` | `indeks yoxdur`, `product_token=ABC123` | missed | partly | missed | exact |
| bench_az_000296 | `7D:1F:AB:6B:58:F1` | `12AB345678`, `Atatürk haqqında kitab`, `example` | partly | missed | partly | exact |
| bench_az_000321 | `4E:54:E7:FD:55:63` | `csrf_token=380922` | missed | missed | partly | exact |
| bench_az_000365 | `67:F5:CA:85:94:DE` | `1234567890` | missed | missed | exact | exact |
| bench_az_000424 | `3D:F1:D4:AB:CC:03` | `---`, `example`, `mail yoxdur` | missed | missed | exact | exact |
| bench_az_000427 | `54:54:0C:6C:A5:D0` | – | partly | partly | exact | exact |
| bench_az_000446 | `16:DB:EB:CE:33:A6` | `1234`, `AA123`, `example` | missed | exact | missed | exact |
| bench_az_000505 | `95:99:FD:5F:BC:9B` | `a***.b***@company.com` | missed | exact | missed | exact |
| bench_az_000545 | `DB:29:29:6C:F4:E0` | `4242424242424242`, `ABC`, `API açarı yoxdur` | partly | exact | partly | exact |
| bench_az_000708 | `3B:5B:C3:8D:52:82` | `---` | missed | missed | missed | exact |
| bench_az_000793 | `33:10:D2:05:2B:DA` | `234` | missed | missed | exact | exact |
| bench_az_000905 | `96:5C:36:D1:3A:01` | `14:30 versiyası` | missed | missed | missed | exact |
| bench_az_000910 | `EA:CB:1C:ED:CA:13` | – | partly | partly | exact | exact |
| bench_az_000941 | `39:09:C1:F9:9E:FE` | – | partly | partly | partly | exact |
| bench_az_001072 | `25:2B:0C:07:B1:AD` | `123456` | missed | missed | missed | exact |
| bench_az_001088 | `7D:48:64:26:89:EE` | `999999` | partly | exact | exact | exact |
| bench_az_001112 | `89:E8:4B:4E:56:4A` | `küçə yoxdur` | missed | missed | missed | exact |
| bench_az_001171 | `4B:F6:8D:CF:91:31` | – | missed | missed | missed | exact |
| bench_az_001177 | `16:D1:68:9B:4D:8B` | `csrf_token=013055` | partly | partly | partly | exact |
| bench_az_001181 | `67:53:C4:E8:5C:69` | `68i` | missed | missed | missed | exact |
| bench_az_001191 | `98:9B:EA:59:E5:AB` | `4242424242424242`, `F45J75`, `example` | missed | partly | missed | exact |
| bench_az_001237 | `19:C0:AA:EF:31:54` | `tarix yoxdur` | partly | partly | partly | exact |
| bench_az_001245 | `7D:9E:0E:07:1E:2A` | – | missed | missed | exact | exact |
| bench_az_001303 | `F8:A5:B0:9F:EE:AE` | `8999`, `ABC`, `AZ1000 məhsul kodu` | missed | missed | missed | exact |
| bench_az_001327 | `8A:4C:42:B8:68:68` | – | missed | missed | missed | exact |
| bench_az_001362 | `76:29:9A:20:C9:FE` | `12:34:56`, `abc`, `mail yoxdur` | missed | missed | missed | exact |
| bench_az_001368 | `92:D2:CC:01:F7:69` | `XYZ` | partly | exact | missed | exact |
| bench_az_001381 | `97:EB:BC:D4:20:86` | `AA:BB:CC:DD` | partly | missed | partly | exact |
| bench_az_001400 | `64:F5:3E:A8:1D:89` | `0501234567`, `123`, `secret yoxdur` | missed | missed | partly | exact |
| bench_az_001421 | `6A:E2:DA:77:57:70` | `123456` | missed | missed | missed | exact |
| bench_az_001529 | `A0:2E:0B:82:EB:4F` | – | missed | missed | missed | exact |

## How much context (40 documents, m1)

| Kept | exact | partly | missed |
|---|---|---|---|
| before 100 | 33 | 2 | 5 |
| before 300 | 13 | 5 | 22 |
| before 600 | 15 | 3 | 22 |
| all before, nothing after | 16 | 6 | 18 |
| nothing before, all after | 35 | 3 | 2 |
