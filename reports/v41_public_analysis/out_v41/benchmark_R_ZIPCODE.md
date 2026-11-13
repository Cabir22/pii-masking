# ZIPCODE: spans v4.1 or v4 does not find exactly

| outcome | v4.1 | v4 |
|---|---|---|
| exact | 381 | 356 |
| split | 3 | 6 |
| covered_inexact | 0 | 0 |
| wrong_label | 0 | 0 |
| missed | 1 | 23 |

## Exact rate per frame, all spans (frames folded: case, letters, 5-letter stems)

| frame | n | v4.1 exact | v4 exact |
|---|---|---|---|
| `poct indek x kimi goste` | 47 | 47 (100%) | 47 (100%) |
| `catdi indek x qeyd olunu` | 47 | 46 (98%) | 36 (77%) |
| `unvan indek x yazil` | 41 | 41 (100%) | 41 (100%) |
| `uzre zip x gorun` | 36 | 33 (92%) | 20 (56%) |
| `poct indek x gorun` | 27 | 27 (100%) | 27 (100%) |
| `poct indek x-dir` | 26 | 26 (100%) | 26 (100%) |
| `unvan indek x kimi yazmi` | 19 | 19 (100%) | 19 (100%) |
| `catdi ucun x indek qeyd` | 19 | 19 (100%) | 18 (95%) |
| `info poct_ x` | 18 | 18 (100%) | 18 (100%) |
| `"poct " x",` | 15 | 15 (100%) | 15 (100%) |
| `poct_ | x |` | 10 | 10 (100%) | 10 (100%) |
| `poct_ melum x olara qeyd` | 9 | 9 (100%) | 9 (100%) |
| `kuces indek x yazil` | 5 | 5 (100%) | 5 (100%) |
| `poct indek x kimi gostr` | 5 | 5 (100%) | 5 (100%) |
| `kuces indek x yazmi` | 3 | 3 (100%) | 3 (100%) |
| `kuces indek x qeyd olunu` | 3 | 3 (100%) | 3 (100%) |
| `unvan indek x yazlb` | 2 | 2 (100%) | 2 (100%) |
| `unvan index x yazil` | 2 | 2 (100%) | 2 (100%) |
| `xinaliq, indek x goste` | 1 | 1 (100%) | 1 (100%) |
| `4, indek x kimi qeyd` | 1 | 1 (100%) | 1 (100%) |
| `narda indek x yazil` | 1 | 1 (100%) | 1 (100%) |
| `unvn indek x yazil` | 1 | 1 (100%) | 1 (100%) |
| `kuces indek x goste` | 1 | 1 (100%) | 1 (100%) |
| `balax indek x yazmi` | 1 | 1 (100%) | 1 (100%) |
| `kuces indks x melum goste` | 1 | 1 (100%) | 1 (100%) |

## v4.1 misses and splits by outcome (n = 4)

| | n |
|---|---|
| `split` | 3 |
| `missed` | 1 |

## v4.1 misses and splits by cut character (n = 4)

| | n |
|---|---|
| `9` | 1 |
| `A 0` | 1 |
| `A 7` | 1 |
| `A` | 1 |

## v4.1 misses and splits by shape (n = 4)

| | n |
|---|---|
| `aa9999` | 4 |

## v4.1 misses and splits by context (n = 4)

| | n |
|---|---|
| `prose` | 4 |

## v4.1 misses and splits by frame (n = 4)

| | n |
|---|---|
| `üzrə ZIP X görünür` | 3 |
| `Çatdırılma indeksi X qeyd olunub` | 1 |

## v4.1 misses and splits by previous word (n = 4)

| | n |
|---|---|
| `ZIP` | 3 |
| `indeksi` | 1 |

## v4.1 misses and splits by next word (n = 4)

| | n |
|---|---|
| `görünür.` | 3 |
| `qeyd` | 1 |

## v4.1 misses and splits by MAC in the same document (n = 4)

| | n |
|---|---|
| `False` | 3 |
| `True` | 1 |

## v4.1 misses and splits by hh:mm(:ss) stamp in the same document (n = 4)

| | n |
|---|---|
| `True` | 2 |
| `False` | 2 |

## v4.1 misses and splits by v4 outcome on the same span (n = 4)

| | n |
|---|---|
| `missed` | 3 |
| `exact` | 1 |

## v4.1 misses and splits by doc type (n = 4)

| | n |
|---|---|
| `technical_note` | 2 |
| `report` | 1 |
| `form` | 1 |

## v4.1 misses and splits by benchmark category (n = 4)

| | n |
|---|---|
| `mixed` | 3 |
| `hard_negative` | 1 |

## Every span (v4.1 not exact, or v4 not exact)

| id | v4.1 | v4 | v4.1 pieces | v4 pieces | other label (v4.1) | context | prev | next | MAC | stamp |
|---|---|---|---|---|---|---|---|---|---|---|
| bench_az_000023 | exact | missed | `[AZ7724]` | `AZ7724` | - | prose | ZIP | görünür. |  |  |
| bench_az_000079 | split | missed | `[AZ31]93` | `AZ3193` | - | prose | ZIP | görünür. |  | y |
| bench_az_000120 | exact | missed | `[AZ6513]` | `AZ6513` | - | prose | ZIP | görünür. |  |  |
| bench_az_000169 | exact | missed | `[AZ6236]` | `AZ6236` | - | prose | indeksi | qeyd |  |  |
| bench_az_000228 | exact | missed | `[AZ6953]` | `AZ6953` | - | prose | ZIP | görünür. |  |  |
| bench_az_000413 | exact | missed | `[AZ9279]` | `AZ9279` | - | prose | ZIP | görunur. |  | y |
| bench_az_000610 | exact | missed | `[AZ7111]` | `AZ7111` | - | prose | ZIP | görünür. |  |  |
| bench_az_000666 | exact | missed | `[AZ4727]` | `AZ4727` | - | prose | indeksi | qeyd |  |  |
| bench_az_000860 | exact | missed | `[AZ8231]` | `AZ8231` | - | prose | indeksi | qeyd |  |  |
| bench_az_001432 | exact | missed | `[AZ9553]` | `AZ9553` | - | prose | ZIP | görünür. |  |  |
| bench_az_001455 | exact | split | `[AZ3324]` | `AZ33[24]` | - | prose | indeksi | qeyd |  |  |
| bench_az_001466 | exact | split | `[AZ7203]` | `AZ[7203]` | - | prose | indeksi | qeyd |  |  |
| bench_az_001471 | exact | split | `[AZ5558]` | `[AZ]555[8]` | - | prose | üçün | indeksini |  |  |
| bench_az_001477 | exact | split | `[AZ9695]` | `[AZ]96[95]` | - | prose | indksində | yazılıb. |  |  |
| bench_az_001534 | exact | missed | `[AZ9570]` | `AZ9570` | - | prose | ZIP | görünür. |  | y |
| bench_az_001967 | exact | missed | `[AZ5831]` | `AZ5831` | - | prose | ZIP | görünür. |  |  |
| bench_az_002018 | split | missed | `AZ[82]02` | `AZ8202` | - | prose | ZIP | görünür. |  | y |
| bench_az_002597 | exact | missed | `[AZ3508]` | `AZ3508` | - | prose | ZIP | görünür. |  |  |
| bench_az_002687 | exact | missed | `[AZ8437]` | `AZ8437` | - | prose | indeksi | qeyd | y |  |
| bench_az_002746 | split | exact | `AZ[3]774` | `[AZ3774]` | - | prose | ZIP | görünür. | y |  |
| bench_az_002770 | exact | missed | `[AZ6252]` | `AZ6252` | - | prose | ZIP | görünür. |  |  |
| bench_az_002816 | exact | missed | `[AZ6878]` | `AZ6878` | - | prose | indeksi | qeyd |  |  |
| bench_az_003010 | exact | missed | `[AZ6833]` | `AZ6833` | - | prose | ZIP | görünür. |  |  |
| bench_az_003314 | exact | missed | `[AZ6206]` | `AZ6206` | - | prose | indeksi | qeyd |  |  |
| bench_az_003885 | exact | split | `[AZ7542]` | `AZ[754]2` | - | prose | ZIP | görünür. | y |  |
| bench_az_004149 | exact | missed | `[AZ3753]` | `AZ3753` | - | prose | ZIP | görünür. |  |  |
| bench_az_004196 | exact | split | `[AZ8213]` | `AZ[8213]` | - | prose | indeksi | qeyd | y | y |
| bench_az_004228 | missed | missed | `AZ9094` | `AZ9094` | - | prose | indeksi | qeyd |  |  |
| bench_az_004607 | exact | missed | `[AZ8489]` | `AZ8489` | - | prose | ZIP | görünür. |  | y |
| bench_az_004899 | exact | missed | `[AZ4667]` | `AZ4667` | - | prose | indeksi | qeyd |  | y |

## False alarms of ZIPCODE (no gold ZIPCODE under them)

### v4: 54 (policy items 0)

| shape | n |
|---|---|
| `aa9999 · gold here - · decoy benchmark_unique` | 22 |
| `aa · gold here - · decoy benchmark_unique` | 16 |
| `aa999999 · gold here - · decoy benchmark_unique` | 10 |
| `9999 · gold here - · decoy benchmark_unique` | 6 |

### v4.1: 36 (policy items 0)

| shape | n |
|---|---|
| `aa9999 · gold here - · decoy benchmark_unique` | 29 |
| `aa · gold here - · decoy benchmark_unique` | 6 |
| `9999 · gold here - · decoy benchmark_unique` | 1 |

