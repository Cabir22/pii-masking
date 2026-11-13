# EMAIL: spans v4 or v3 does not find exactly

| outcome | v4 | v3 |
|---|---|---|
| exact | 377 | 402 |
| split | 26 | 1 |
| covered_inexact | 0 | 0 |
| wrong_label | 0 | 0 |
| missed | 0 | 0 |

## Exact rate per frame, all spans (frames folded: case, letters, 5-letter stems)

| frame | n | v4 exact | v3 exact |
|---|---|---|---|
| `elaqe ucun x e-poc unvan` | 69 | 69 (100%) | 69 (100%) |
| `email hisse x yazil` | 55 | 55 (100%) | 55 (100%) |
| `hesab x unvan ile` | 54 | 54 (100%) | 54 (100%) |
| `e-poc olara x saxla` | 48 | 48 (100%) | 48 (100%) |
| `email olara x qeyd etmis` | 29 | 29 (100%) | 29 (100%) |
| `mene x unvan yaza` | 26 | 26 (100%) | 26 (100%) |
| `email unvan x-dir` | 20 | 20 (100%) | 20 (100%) |
| `cavab x e-poc unvan` | 19 | 19 (100%) | 19 (100%) |
| `e_poc | x |` | 14 | 6 (43%) | 14 (100%) |
| `e_poc melum x olara qeyd` | 12 | 8 (67%) | 12 (100%) |
| `"e_po " x",` | 10 | 4 (40%) | 10 (100%) |
| `info e_poc x` | 10 | 6 (60%) | 9 (90%) |
| `nomre ve x e-poc goste` | 9 | 9 (100%) | 9 (100%) |
| `email ise x kimi yazil` | 5 | 5 (100%) | 5 (100%) |
| `hesab x unvni ile` | 3 | 3 (100%) | 3 (100%) |
| `ve ya x unvan cata` | 3 | 3 (100%) | 3 (100%) |
| `e-poc olara x qeyd etmis` | 2 | 2 (100%) | 2 (100%) |
| `email hisse x yazlb` | 2 | 2 (100%) | 2 (100%) |
| `x;5294 0753` | 1 | 0 (0%) | 1 (100%) |
| `cavab x e poct` | 1 | 1 (100%) | 1 (100%) |
| `3490 2214; x;laza;az1994;000` | 1 | 0 (0%) | 1 (100%) |
| `27 62; x;vendam;https://support.example.com/news/archive/10910;p123` | 1 | 1 (100%) | 1 (100%) |
| `hesap x unvan ile` | 1 | 1 (100%) | 1 (100%) |
| `zq701 x;https://support.example.com/help/article/10640;p123` | 1 | 1 (100%) | 1 (100%) |
| `email unvni x-dir` | 1 | 1 (100%) | 1 (100%) |

## v4 misses and splits by outcome (n = 26)

| | n |
|---|---|
| `split` | 26 |

## v4 misses and splits by cut character (n = 26)

| | n |
|---|---|
| `b` | 9 |
| `c` | 9 |
| `b u` | 5 |
| `.` | 2 |
| `b .` | 1 |

## v4 misses and splits by shape (n = 26)

| | n |
|---|---|
| `local: dot+digit` | 26 |
| `domain dots 1` | 26 |
| `domain hyphen` | 26 |

## v4 misses and splits by context (n = 26)

| | n |
|---|---|
| `CSV / table` | 12 |
| `JSON` | 6 |
| `prose` | 4 |
| `log line` | 4 |

## v4 misses and splits by frame (n = 26)

| | n |
|---|---|
| `e_poçt | X |` | 8 |
| `"e_poçt": " X",` | 6 |
| `e_poçt məlumatı X olaraq qeyd` | 4 |
| `INFO e_poçt= X` | 4 |
| `X;5294 0753` | 1 |
| `3490 2214; X;Laza;AZ1994;000` | 1 |
| `Laza; X;568/9;M97A90;12345` | 1 |
| `37;38; X;25:81;999` | 1 |

## v4 misses and splits by previous word (n = 26)

| | n |
|---|---|
| `|` | 8 |
| `"` | 6 |
| `məlumatı` | 4 |
| `e_poçt=` | 4 |
| `e_poçt;kart_nömrəsi;iccid;fin_kodu;cvv` | 1 |
| `2214;` | 1 |
| `Laza;` | 1 |
| `37;38;` | 1 |

## v4 misses and splits by next word (n = 26)

| | n |
|---|---|
| `|` | 8 |
| `",` | 6 |
| `olaraq` | 4 |
| `[2031-04-12` | 4 |
| `;5294` | 1 |
| `;Laza;AZ1994;000` | 1 |
| `;568/9;M97A90;12345` | 1 |
| `;25:81;999` | 1 |

## v4 misses and splits by MAC in the same document (n = 26)

| | n |
|---|---|
| `False` | 24 |
| `True` | 2 |

## v4 misses and splits by hh:mm(:ss) stamp in the same document (n = 26)

| | n |
|---|---|
| `False` | 19 |
| `True` | 7 |

## v4 misses and splits by v3 outcome on the same span (n = 26)

| | n |
|---|---|
| `exact` | 25 |
| `split` | 1 |

## v4 misses and splits by doc type (n = 26)

| | n |
|---|---|
| `pipe_table` | 8 |
| `json_config` | 6 |
| `csv` | 4 |
| `dialogue` | 4 |
| `technical_log` | 4 |

## v4 misses and splits by benchmark category (n = 26)

| | n |
|---|---|
| `structured_pipe_table` | 8 |
| `structured_json_config` | 6 |
| `structured_csv` | 4 |
| `structured_dialogue` | 4 |
| `structured_technical_log` | 4 |

## Every span (v4 not exact, or v3 not exact)

| id | v4 | v3 | v4 pieces | v3 pieces | other label (v4) | context | prev | next | MAC | stamp |
|---|---|---|---|---|---|---|---|---|---|---|
| bench_az_000013 | split | exact | `[bench].[user2548@synthetic-mail15.invalid]` | `[bench.user2548@synthetic-mail15.invalid]` | - | CSV / table | e_poçt;kart_nömrəsi;iccid;fin_kodu;cvv | ;5294 |  |  |
| bench_az_000379 | split | exact | `bench.user[304@synthetic-mail15.invalid]` | `[bench.user304@synthetic-mail15.invalid]` | - | CSV / table | | | | |  | y |
| bench_az_000392 | split | exact | `[ben]ch[.user1239@synthetic-mail15.invalid]` | `[bench.user1239@synthetic-mail15.invalid]` | - | CSV / table | | | | |  |  |
| bench_az_000569 | split | exact | `[ben]ch[.user1545@synthetic-mail15.invalid]` | `[bench.user1545@synthetic-mail15.invalid]` | - | CSV / table | | | | |  |  |
| bench_az_000830 | split | exact | `bench[.user565@synthetic-mail4.invalid]` | `[bench.user565@synthetic-mail4.invalid]` | - | JSON | " | ", |  |  |
| bench_az_000936 | split | exact | `bench.[user2049@synthetic-mail9.invalid]` | `[bench.user2049@synthetic-mail9.invalid]` | - | CSV / table | 2214; | ;Laza;AZ1994;000 |  |  |
| bench_az_000974 | split | exact | `ben[ch.user110@synthetic-mail8.invalid]` | `[bench.user110@synthetic-mail8.invalid]` | - | CSV / table | | | | |  |  |
| bench_az_001017 | split | exact | `bench[.]user[1090@synthetic-mail2.invalid]` | `[bench.user1090@synthetic-mail2.invalid]` | - | CSV / table | | | | |  |  |
| bench_az_001040 | split | exact | `[ben]ch[.user2023@synthetic-mail0.invalid]` | `[bench.user2023@synthetic-mail0.invalid]` | - | JSON | " | ", |  |  |
| bench_az_001047 | split | exact | `[ben]ch[.user1998@synthetic-mail9.invalid]` | `[bench.user1998@synthetic-mail9.invalid]` | - | prose | məlumatı | olaraq |  |  |
| bench_az_001058 | split | exact | `bench[.]user[598@synthetic-mail3.invalid]` | `[bench.user598@synthetic-mail3.invalid]` | - | log line | e_poçt= | [2031-04-12 |  | y |
| bench_az_001250 | split | exact | `bench[.user2211@synthetic-mail1.invalid]` | `[bench.user2211@synthetic-mail1.invalid]` | - | log line | e_poçt= | [2031-04-12 |  | y |
| bench_az_001607 | split | exact | `[ben]ch[.user1228@synthetic-mail4.invalid]` | `[bench.user1228@synthetic-mail4.invalid]` | - | JSON | " | ", |  |  |
| bench_az_001667 | split | exact | `bench[.]user[220@synthetic-mail16.invalid]` | `[bench.user220@synthetic-mail16.invalid]` | - | log line | e_poçt= | [2031-04-12 |  | y |
| bench_az_002175 | split | exact | `[ben]ch[.user1528@synthetic-mail15.invalid]` | `[bench.user1528@synthetic-mail15.invalid]` | - | CSV / table | | | | | y | y |
| bench_az_002235 | split | split | `bench.user1352[@synthetic-mail9.invalid]` | `bench[.]user135[2@synthetic-mail9.invalid]` | - | log line | e_poçt= | [2031-04-12 |  | y |
| bench_az_002505 | split | exact | `[ben]ch[.user1153@synthetic-mail14.invalid]` | `[bench.user1153@synthetic-mail14.invalid]` | - | JSON | " | ", |  |  |
| bench_az_002748 | split | exact | `[ben]ch[.user2948@synthetic-mail7.invalid]` | `[bench.user2948@synthetic-mail7.invalid]` | - | CSV / table | | | | |  |  |
| bench_az_003057 | split | exact | `bench[.user1729@synthetic-mail12.invalid]` | `[bench.user1729@synthetic-mail12.invalid]` | - | CSV / table | | | | |  |  |
| bench_az_003503 | split | exact | `[ben]ch[.user753@synthetic-mail5.invalid]` | `[bench.user753@synthetic-mail5.invalid]` | - | prose | məlumatı | olaraq |  |  |
| bench_az_003664 | split | exact | `[bench].[user1267@synthetic-mail9.invalid]` | `[bench.user1267@synthetic-mail9.invalid]` | - | CSV / table | Laza; | ;568/9;M97A90;12345 |  |  |
| bench_az_003892 | split | exact | `bench[.user1784@synthetic-mail16.invalid]` | `[bench.user1784@synthetic-mail16.invalid]` | - | prose | məlumatı | olaraq |  |  |
| bench_az_004096 | split | exact | `bench[.]user[174@synthetic-mail4.invalid]` | `[bench.user174@synthetic-mail4.invalid]` | - | JSON | " | ", |  |  |
| bench_az_004214 | split | exact | `bench[.]user[1779@synthetic-mail11.invalid]` | `[bench.user1779@synthetic-mail11.invalid]` | - | JSON | " | ", | y |  |
| bench_az_004376 | split | exact | `bench.user[2882@synthetic-mail9.invalid]` | `[bench.user2882@synthetic-mail9.invalid]` | - | prose | məlumatı | olaraq |  |  |
| bench_az_004629 | split | exact | `bench[.user2430@synthetic-mail16].[invalid]` | `[bench.user2430@synthetic-mail16.invalid]` | - | CSV / table | 37;38; | ;25:81;999 |  | y |

## False alarms of EMAIL (no gold EMAIL under them)

### v3: 1 (policy items 0)

| shape | n |
|---|---|
| `. · gold here - · decoy benchmark_unique` | 1 |

