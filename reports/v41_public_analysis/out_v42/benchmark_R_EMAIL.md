# EMAIL: spans v4.2 or v4.1 does not find exactly

| outcome | v4.2 | v4.1 |
|---|---|---|
| exact | 403 | 399 |
| split | 0 | 4 |
| covered_inexact | 0 | 0 |
| wrong_label | 0 | 0 |
| missed | 0 | 0 |

## Exact rate per frame, all spans (frames folded: case, letters, 5-letter stems)

| frame | n | v4.2 exact | v4.1 exact |
|---|---|---|---|
| `elaqe ucun x e-poc unvan` | 69 | 69 (100%) | 69 (100%) |
| `email hisse x yazil` | 55 | 55 (100%) | 55 (100%) |
| `hesab x unvan ile` | 54 | 54 (100%) | 54 (100%) |
| `e-poc olara x saxla` | 48 | 48 (100%) | 48 (100%) |
| `email olara x qeyd etmis` | 29 | 29 (100%) | 29 (100%) |
| `mene x unvan yaza` | 26 | 26 (100%) | 26 (100%) |
| `email unvan x-dir` | 20 | 20 (100%) | 20 (100%) |
| `cavab x e-poc unvan` | 19 | 19 (100%) | 19 (100%) |
| `e_poc | x |` | 14 | 14 (100%) | 14 (100%) |
| `e_poc melum x olara qeyd` | 12 | 12 (100%) | 12 (100%) |
| `"e_po " x",` | 10 | 10 (100%) | 10 (100%) |
| `info e_poc x` | 10 | 10 (100%) | 10 (100%) |
| `nomre ve x e-poc goste` | 9 | 9 (100%) | 9 (100%) |
| `email ise x kimi yazil` | 5 | 5 (100%) | 5 (100%) |
| `hesab x unvni ile` | 3 | 3 (100%) | 3 (100%) |
| `ve ya x unvan cata` | 3 | 3 (100%) | 3 (100%) |
| `e-poc olara x qeyd etmis` | 2 | 2 (100%) | 2 (100%) |
| `email hisse x yazlb` | 2 | 2 (100%) | 2 (100%) |
| `x;5294 0753` | 1 | 1 (100%) | 0 (0%) |
| `cavab x e poct` | 1 | 1 (100%) | 1 (100%) |
| `3490 2214; x;laza;az1994;000` | 1 | 1 (100%) | 0 (0%) |
| `27 62; x;vendam;https://support.example.com/news/archive/10910;p123` | 1 | 1 (100%) | 1 (100%) |
| `hesap x unvan ile` | 1 | 1 (100%) | 1 (100%) |
| `zq701 x;https://support.example.com/help/article/10640;p123` | 1 | 1 (100%) | 1 (100%) |
| `email unvni x-dir` | 1 | 1 (100%) | 1 (100%) |

## v4.2 misses and splits by outcome (n = 0)

| | n |
|---|---|

## v4.2 misses and splits by cut character (n = 0)

| | n |
|---|---|

## v4.2 misses and splits by shape (n = 0)

| | n |
|---|---|

## v4.2 misses and splits by context (n = 0)

| | n |
|---|---|

## v4.2 misses and splits by frame (n = 0)

| | n |
|---|---|

## v4.2 misses and splits by previous word (n = 0)

| | n |
|---|---|

## v4.2 misses and splits by next word (n = 0)

| | n |
|---|---|

## v4.2 misses and splits by MAC in the same document (n = 0)

| | n |
|---|---|

## v4.2 misses and splits by hh:mm(:ss) stamp in the same document (n = 0)

| | n |
|---|---|

## v4.2 misses and splits by v4.1 outcome on the same span (n = 0)

| | n |
|---|---|

## v4.2 misses and splits by doc type (n = 0)

| | n |
|---|---|

## v4.2 misses and splits by benchmark category (n = 0)

| | n |
|---|---|

## Every span (v4.2 not exact, or v4.1 not exact)

| id | v4.2 | v4.1 | v4.2 pieces | v4.1 pieces | other label (v4.2) | context | prev | next | MAC | stamp |
|---|---|---|---|---|---|---|---|---|---|---|
| bench_az_000013 | exact | split | `[bench.user2548@synthetic-mail15.invalid]` | `[bench].[user2548@synthetic-mail15.invalid]` | - | CSV / table | e_poçt;kart_nömrəsi;iccid;fin_kodu;cvv | ;5294 |  |  |
| bench_az_000936 | exact | split | `[bench.user2049@synthetic-mail9.invalid]` | `[bench].[user2049@synthetic-mail9.invalid]` | - | CSV / table | 2214; | ;Laza;AZ1994;000 |  |  |
| bench_az_003664 | exact | split | `[bench.user1267@synthetic-mail9.invalid]` | `[bench].[user1267@synthetic-mail9.invalid]` | - | CSV / table | Laza; | ;568/9;M97A90;12345 |  |  |
| bench_az_004629 | exact | split | `[bench.user2430@synthetic-mail16.invalid]` | `[bench].[user2430@synthetic-mail16.invalid]` | - | CSV / table | 37;38; | ;25:81;999 |  | y |

## False alarms of EMAIL (no gold EMAIL under them)

