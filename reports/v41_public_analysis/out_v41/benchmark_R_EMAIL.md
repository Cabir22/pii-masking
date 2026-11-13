# EMAIL: spans v4.1 or v4 does not find exactly

| outcome | v4.1 | v4 |
|---|---|---|
| exact | 399 | 377 |
| split | 4 | 26 |
| covered_inexact | 0 | 0 |
| wrong_label | 0 | 0 |
| missed | 0 | 0 |

## Exact rate per frame, all spans (frames folded: case, letters, 5-letter stems)

| frame | n | v4.1 exact | v4 exact |
|---|---|---|---|
| `elaqe ucun x e-poc unvan` | 69 | 69 (100%) | 69 (100%) |
| `email hisse x yazil` | 55 | 55 (100%) | 55 (100%) |
| `hesab x unvan ile` | 54 | 54 (100%) | 54 (100%) |
| `e-poc olara x saxla` | 48 | 48 (100%) | 48 (100%) |
| `email olara x qeyd etmis` | 29 | 29 (100%) | 29 (100%) |
| `mene x unvan yaza` | 26 | 26 (100%) | 26 (100%) |
| `email unvan x-dir` | 20 | 20 (100%) | 20 (100%) |
| `cavab x e-poc unvan` | 19 | 19 (100%) | 19 (100%) |
| `e_poc | x |` | 14 | 14 (100%) | 6 (43%) |
| `e_poc melum x olara qeyd` | 12 | 12 (100%) | 8 (67%) |
| `"e_po " x",` | 10 | 10 (100%) | 4 (40%) |
| `info e_poc x` | 10 | 10 (100%) | 6 (60%) |
| `nomre ve x e-poc goste` | 9 | 9 (100%) | 9 (100%) |
| `email ise x kimi yazil` | 5 | 5 (100%) | 5 (100%) |
| `hesab x unvni ile` | 3 | 3 (100%) | 3 (100%) |
| `ve ya x unvan cata` | 3 | 3 (100%) | 3 (100%) |
| `e-poc olara x qeyd etmis` | 2 | 2 (100%) | 2 (100%) |
| `email hisse x yazlb` | 2 | 2 (100%) | 2 (100%) |
| `x;5294 0753` | 1 | 0 (0%) | 0 (0%) |
| `cavab x e poct` | 1 | 1 (100%) | 1 (100%) |
| `3490 2214; x;laza;az1994;000` | 1 | 0 (0%) | 0 (0%) |
| `27 62; x;vendam;https://support.example.com/news/archive/10910;p123` | 1 | 1 (100%) | 1 (100%) |
| `hesap x unvan ile` | 1 | 1 (100%) | 1 (100%) |
| `zq701 x;https://support.example.com/help/article/10640;p123` | 1 | 1 (100%) | 1 (100%) |
| `email unvni x-dir` | 1 | 1 (100%) | 1 (100%) |

## v4.1 misses and splits by outcome (n = 4)

| | n |
|---|---|
| `split` | 4 |

## v4.1 misses and splits by cut character (n = 4)

| | n |
|---|---|
| `.` | 4 |

## v4.1 misses and splits by shape (n = 4)

| | n |
|---|---|
| `local: dot+digit` | 4 |
| `domain dots 1` | 4 |
| `domain hyphen` | 4 |

## v4.1 misses and splits by context (n = 4)

| | n |
|---|---|
| `CSV / table` | 4 |

## v4.1 misses and splits by frame (n = 4)

| | n |
|---|---|
| `X;5294 0753` | 1 |
| `3490 2214; X;Laza;AZ1994;000` | 1 |
| `Laza; X;568/9;M97A90;12345` | 1 |
| `37;38; X;25:81;999` | 1 |

## v4.1 misses and splits by previous word (n = 4)

| | n |
|---|---|
| `e_poçt;kart_nömrəsi;iccid;fin_kodu;cvv` | 1 |
| `2214;` | 1 |
| `Laza;` | 1 |
| `37;38;` | 1 |

## v4.1 misses and splits by next word (n = 4)

| | n |
|---|---|
| `;5294` | 1 |
| `;Laza;AZ1994;000` | 1 |
| `;568/9;M97A90;12345` | 1 |
| `;25:81;999` | 1 |

## v4.1 misses and splits by MAC in the same document (n = 4)

| | n |
|---|---|
| `False` | 4 |

## v4.1 misses and splits by hh:mm(:ss) stamp in the same document (n = 4)

| | n |
|---|---|
| `False` | 3 |
| `True` | 1 |

## v4.1 misses and splits by v4 outcome on the same span (n = 4)

| | n |
|---|---|
| `split` | 4 |

## v4.1 misses and splits by doc type (n = 4)

| | n |
|---|---|
| `csv` | 4 |

## v4.1 misses and splits by benchmark category (n = 4)

| | n |
|---|---|
| `structured_csv` | 4 |

## Every span (v4.1 not exact, or v4 not exact)

| id | v4.1 | v4 | v4.1 pieces | v4 pieces | other label (v4.1) | context | prev | next | MAC | stamp |
|---|---|---|---|---|---|---|---|---|---|---|
| bench_az_000013 | split | split | `[bench].[user2548@synthetic-mail15.invalid]` | `[bench].[user2548@synthetic-mail15.invalid]` | - | CSV / table | e_poçt;kart_nömrəsi;iccid;fin_kodu;cvv | ;5294 |  |  |
| bench_az_000379 | exact | split | `[bench.user304@synthetic-mail15.invalid]` | `bench.user[304@synthetic-mail15.invalid]` | - | CSV / table | | | | |  | y |
| bench_az_000392 | exact | split | `[bench.user1239@synthetic-mail15.invalid]` | `[ben]ch[.user1239@synthetic-mail15.invalid]` | - | CSV / table | | | | |  |  |
| bench_az_000569 | exact | split | `[bench.user1545@synthetic-mail15.invalid]` | `[ben]ch[.user1545@synthetic-mail15.invalid]` | - | CSV / table | | | | |  |  |
| bench_az_000830 | exact | split | `[bench.user565@synthetic-mail4.invalid]` | `bench[.user565@synthetic-mail4.invalid]` | - | JSON | " | ", |  |  |
| bench_az_000936 | split | split | `[bench].[user2049@synthetic-mail9.invalid]` | `bench.[user2049@synthetic-mail9.invalid]` | - | CSV / table | 2214; | ;Laza;AZ1994;000 |  |  |
| bench_az_000974 | exact | split | `[bench.user110@synthetic-mail8.invalid]` | `ben[ch.user110@synthetic-mail8.invalid]` | - | CSV / table | | | | |  |  |
| bench_az_001017 | exact | split | `[bench.user1090@synthetic-mail2.invalid]` | `bench[.]user[1090@synthetic-mail2.invalid]` | - | CSV / table | | | | |  |  |
| bench_az_001040 | exact | split | `[bench.user2023@synthetic-mail0.invalid]` | `[ben]ch[.user2023@synthetic-mail0.invalid]` | - | JSON | " | ", |  |  |
| bench_az_001047 | exact | split | `[bench.user1998@synthetic-mail9.invalid]` | `[ben]ch[.user1998@synthetic-mail9.invalid]` | - | prose | məlumatı | olaraq |  |  |
| bench_az_001058 | exact | split | `[bench.user598@synthetic-mail3.invalid]` | `bench[.]user[598@synthetic-mail3.invalid]` | - | log line | e_poçt= | [2031-04-12 |  | y |
| bench_az_001250 | exact | split | `[bench.user2211@synthetic-mail1.invalid]` | `bench[.user2211@synthetic-mail1.invalid]` | - | log line | e_poçt= | [2031-04-12 |  | y |
| bench_az_001607 | exact | split | `[bench.user1228@synthetic-mail4.invalid]` | `[ben]ch[.user1228@synthetic-mail4.invalid]` | - | JSON | " | ", |  |  |
| bench_az_001667 | exact | split | `[bench.user220@synthetic-mail16.invalid]` | `bench[.]user[220@synthetic-mail16.invalid]` | - | log line | e_poçt= | [2031-04-12 |  | y |
| bench_az_002175 | exact | split | `[bench.user1528@synthetic-mail15.invalid]` | `[ben]ch[.user1528@synthetic-mail15.invalid]` | - | CSV / table | | | | | y | y |
| bench_az_002235 | exact | split | `[bench.user1352@synthetic-mail9.invalid]` | `bench.user1352[@synthetic-mail9.invalid]` | - | log line | e_poçt= | [2031-04-12 |  | y |
| bench_az_002505 | exact | split | `[bench.user1153@synthetic-mail14.invalid]` | `[ben]ch[.user1153@synthetic-mail14.invalid]` | - | JSON | " | ", |  |  |
| bench_az_002748 | exact | split | `[bench.user2948@synthetic-mail7.invalid]` | `[ben]ch[.user2948@synthetic-mail7.invalid]` | - | CSV / table | | | | |  |  |
| bench_az_003057 | exact | split | `[bench.user1729@synthetic-mail12.invalid]` | `bench[.user1729@synthetic-mail12.invalid]` | - | CSV / table | | | | |  |  |
| bench_az_003503 | exact | split | `[bench.user753@synthetic-mail5.invalid]` | `[ben]ch[.user753@synthetic-mail5.invalid]` | - | prose | məlumatı | olaraq |  |  |
| bench_az_003664 | split | split | `[bench].[user1267@synthetic-mail9.invalid]` | `[bench].[user1267@synthetic-mail9.invalid]` | - | CSV / table | Laza; | ;568/9;M97A90;12345 |  |  |
| bench_az_003892 | exact | split | `[bench.user1784@synthetic-mail16.invalid]` | `bench[.user1784@synthetic-mail16.invalid]` | - | prose | məlumatı | olaraq |  |  |
| bench_az_004096 | exact | split | `[bench.user174@synthetic-mail4.invalid]` | `bench[.]user[174@synthetic-mail4.invalid]` | - | JSON | " | ", |  |  |
| bench_az_004214 | exact | split | `[bench.user1779@synthetic-mail11.invalid]` | `bench[.]user[1779@synthetic-mail11.invalid]` | - | JSON | " | ", | y |  |
| bench_az_004376 | exact | split | `[bench.user2882@synthetic-mail9.invalid]` | `bench.user[2882@synthetic-mail9.invalid]` | - | prose | məlumatı | olaraq |  |  |
| bench_az_004629 | split | split | `[bench].[user2430@synthetic-mail16.invalid]` | `bench[.user2430@synthetic-mail16].[invalid]` | - | CSV / table | 37;38; | ;25:81;999 |  | y |

## False alarms of EMAIL (no gold EMAIL under them)

