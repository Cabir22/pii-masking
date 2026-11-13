# ZIPCODE: spans v4.2 or v4.1 does not find exactly

| outcome | v4.2 | v4.1 |
|---|---|---|
| exact | 384 | 381 |
| split | 1 | 3 |
| covered_inexact | 0 | 0 |
| wrong_label | 0 | 0 |
| missed | 0 | 1 |

## Exact rate per frame, all spans (frames folded: case, letters, 5-letter stems)

| frame | n | v4.2 exact | v4.1 exact |
|---|---|---|---|
| `poct indek x kimi goste` | 47 | 47 (100%) | 47 (100%) |
| `catdi indek x qeyd olunu` | 47 | 46 (98%) | 46 (98%) |
| `unvan indek x yazil` | 41 | 41 (100%) | 41 (100%) |
| `uzre zip x gorun` | 36 | 36 (100%) | 33 (92%) |
| `poct indek x gorun` | 27 | 27 (100%) | 27 (100%) |
| `poct indek x-dir` | 26 | 26 (100%) | 26 (100%) |
| `unvan indek x kimi yazmi` | 19 | 19 (100%) | 19 (100%) |
| `catdi ucun x indek qeyd` | 19 | 19 (100%) | 19 (100%) |
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

## v4.2 misses and splits by outcome (n = 1)

| | n |
|---|---|
| `split` | 1 |

## v4.2 misses and splits by cut character (n = 1)

| | n |
|---|---|
| `9` | 1 |

## v4.2 misses and splits by shape (n = 1)

| | n |
|---|---|
| `aa9999` | 1 |

## v4.2 misses and splits by context (n = 1)

| | n |
|---|---|
| `prose` | 1 |

## v4.2 misses and splits by frame (n = 1)

| | n |
|---|---|
| `Çatdırılma indeksi X qeyd olunub` | 1 |

## v4.2 misses and splits by previous word (n = 1)

| | n |
|---|---|
| `indeksi` | 1 |

## v4.2 misses and splits by next word (n = 1)

| | n |
|---|---|
| `qeyd` | 1 |

## v4.2 misses and splits by MAC in the same document (n = 1)

| | n |
|---|---|
| `False` | 1 |

## v4.2 misses and splits by hh:mm(:ss) stamp in the same document (n = 1)

| | n |
|---|---|
| `False` | 1 |

## v4.2 misses and splits by v4.1 outcome on the same span (n = 1)

| | n |
|---|---|
| `missed` | 1 |

## v4.2 misses and splits by doc type (n = 1)

| | n |
|---|---|
| `technical_note` | 1 |

## v4.2 misses and splits by benchmark category (n = 1)

| | n |
|---|---|
| `mixed` | 1 |

## Every span (v4.2 not exact, or v4.1 not exact)

| id | v4.2 | v4.1 | v4.2 pieces | v4.1 pieces | other label (v4.2) | context | prev | next | MAC | stamp |
|---|---|---|---|---|---|---|---|---|---|---|
| bench_az_000079 | exact | split | `[AZ3193]` | `[AZ31]93` | - | prose | ZIP | görünür. |  | y |
| bench_az_002018 | exact | split | `[AZ8202]` | `AZ[82]02` | - | prose | ZIP | görünür. |  | y |
| bench_az_002746 | exact | split | `[AZ3774]` | `AZ[3]774` | - | prose | ZIP | görünür. | y |  |
| bench_az_004228 | split | missed | `[AZ]9094` | `AZ9094` | - | prose | indeksi | qeyd |  |  |

## False alarms of ZIPCODE (no gold ZIPCODE under them)

### v4.1: 36 (policy items 0)

| shape | n |
|---|---|
| `aa9999 · gold here - · decoy benchmark_unique` | 29 |
| `aa · gold here - · decoy benchmark_unique` | 6 |
| `9999 · gold here - · decoy benchmark_unique` | 1 |

### v4.2: 54 (policy items 0)

| shape | n |
|---|---|
| `aa9999 · gold here - · decoy benchmark_unique` | 47 |
| `aa · gold here - · decoy benchmark_unique` | 7 |

