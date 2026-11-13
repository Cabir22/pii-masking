# ZIPCODE: spans v4 or v3 does not find exactly

| outcome | v4 | v3 |
|---|---|---|
| exact | 356 | 373 |
| split | 6 | 4 |
| covered_inexact | 0 | 0 |
| wrong_label | 0 | 0 |
| missed | 23 | 8 |

## Exact rate per frame, all spans (frames folded: case, letters, 5-letter stems)

| frame | n | v4 exact | v3 exact |
|---|---|---|---|
| `poct indek x kimi goste` | 47 | 47 (100%) | 47 (100%) |
| `catdi indek x qeyd olunu` | 47 | 36 (77%) | 37 (79%) |
| `unvan indek x yazil` | 41 | 41 (100%) | 41 (100%) |
| `uzre zip x gorun` | 36 | 20 (56%) | 35 (97%) |
| `poct indek x gorun` | 27 | 27 (100%) | 27 (100%) |
| `poct indek x-dir` | 26 | 26 (100%) | 26 (100%) |
| `unvan indek x kimi yazmi` | 19 | 19 (100%) | 19 (100%) |
| `catdi ucun x indek qeyd` | 19 | 18 (95%) | 18 (95%) |
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

## v4 misses and splits by outcome (n = 29)

| | n |
|---|---|
| `missed` | 23 |
| `split` | 6 |

## v4 misses and splits by cut character (n = 29)

| | n |
|---|---|
| `A` | 26 |
| `5` | 1 |
| `9` | 1 |
| `A 2` | 1 |

## v4 misses and splits by shape (n = 29)

| | n |
|---|---|
| `aa9999` | 29 |

## v4 misses and splits by context (n = 29)

| | n |
|---|---|
| `prose` | 29 |

## v4 misses and splits by frame (n = 29)

| | n |
|---|---|
| `üzrə ZIP X görünür` | 15 |
| `Çatdırılma indeksi X qeyd olunub` | 11 |
| `üzrə ZIP X görunur` | 1 |
| `Çatdırılma üçün X indeksini qeyd` | 1 |
| `Ünvan indksində X yazılıb` | 1 |

## v4 misses and splits by previous word (n = 29)

| | n |
|---|---|
| `ZIP` | 16 |
| `indeksi` | 11 |
| `üçün` | 1 |
| `indksində` | 1 |

## v4 misses and splits by next word (n = 29)

| | n |
|---|---|
| `görünür.` | 15 |
| `qeyd` | 11 |
| `görunur.` | 1 |
| `indeksini` | 1 |
| `yazılıb.` | 1 |

## v4 misses and splits by MAC in the same document (n = 29)

| | n |
|---|---|
| `False` | 26 |
| `True` | 3 |

## v4 misses and splits by hh:mm(:ss) stamp in the same document (n = 29)

| | n |
|---|---|
| `False` | 22 |
| `True` | 7 |

## v4 misses and splits by v3 outcome on the same span (n = 29)

| | n |
|---|---|
| `exact` | 22 |
| `missed` | 5 |
| `split` | 2 |

## v4 misses and splits by doc type (n = 29)

| | n |
|---|---|
| `technical_note` | 6 |
| `email` | 4 |
| `report` | 4 |
| `bank_message` | 3 |
| `crm` | 3 |
| `insurance` | 3 |
| `support_ticket` | 2 |
| `legal` | 2 |
| `form` | 1 |
| `first_person_email` | 1 |

## v4 misses and splits by benchmark category (n = 29)

| | n |
|---|---|
| `mixed` | 9 |
| `hard_negative` | 8 |
| `natural_variant_hard_negative` | 3 |
| `anchor_variant_hard_negative` | 3 |
| `positive_control` | 3 |
| `corrected_hard_negative` | 1 |
| `anchor_variant_positive` | 1 |
| `natural_variant_positive` | 1 |

## Every span (v4 not exact, or v3 not exact)

| id | v4 | v3 | v4 pieces | v3 pieces | other label (v4) | context | prev | next | MAC | stamp |
|---|---|---|---|---|---|---|---|---|---|---|
| bench_az_000023 | missed | exact | `AZ7724` | `[AZ7724]` | - | prose | ZIP | görünür. |  |  |
| bench_az_000079 | missed | split | `AZ3193` | `[AZ31]93` | - | prose | ZIP | görünür. |  | y |
| bench_az_000120 | missed | exact | `AZ6513` | `[AZ6513]` | - | prose | ZIP | görünür. |  |  |
| bench_az_000169 | missed | missed | `AZ6236` | `AZ6236` | - | prose | indeksi | qeyd |  |  |
| bench_az_000228 | missed | exact | `AZ6953` | `[AZ6953]` | - | prose | ZIP | görünür. |  |  |
| bench_az_000333 | exact | split | `[AZ5737]` | `AZ[5737]` | - | prose | indeksi | qeyd |  |  |
| bench_az_000413 | missed | exact | `AZ9279` | `[AZ9279]` | - | prose | ZIP | görunur. |  | y |
| bench_az_000455 | exact | split | `[AZ3104]` | `AZ[3104]` | - | prose | indeksi | qeyd |  | y |
| bench_az_000610 | missed | exact | `AZ7111` | `[AZ7111]` | - | prose | ZIP | görünür. |  |  |
| bench_az_000666 | missed | exact | `AZ4727` | `[AZ4727]` | - | prose | indeksi | qeyd |  |  |
| bench_az_000860 | missed | exact | `AZ8231` | `[AZ8231]` | - | prose | indeksi | qeyd |  |  |
| bench_az_001432 | missed | exact | `AZ9553` | `[AZ9553]` | - | prose | ZIP | görünür. |  |  |
| bench_az_001455 | split | exact | `AZ33[24]` | `[AZ3324]` | - | prose | indeksi | qeyd |  |  |
| bench_az_001466 | split | exact | `AZ[7203]` | `[AZ7203]` | - | prose | indeksi | qeyd |  |  |
| bench_az_001471 | split | missed | `[AZ]555[8]` | `AZ5558` | - | prose | üçün | indeksini |  |  |
| bench_az_001477 | split | exact | `[AZ]96[95]` | `[AZ9695]` | - | prose | indksində | yazılıb. |  |  |
| bench_az_001534 | missed | exact | `AZ9570` | `[AZ9570]` | - | prose | ZIP | görünür. |  | y |
| bench_az_001967 | missed | exact | `AZ5831` | `[AZ5831]` | - | prose | ZIP | görünür. |  |  |
| bench_az_002018 | missed | exact | `AZ8202` | `[AZ8202]` | - | prose | ZIP | görünür. |  | y |
| bench_az_002597 | missed | exact | `AZ3508` | `[AZ3508]` | - | prose | ZIP | görünür. |  |  |
| bench_az_002687 | missed | exact | `AZ8437` | `[AZ8437]` | - | prose | indeksi | qeyd | y |  |
| bench_az_002770 | missed | exact | `AZ6252` | `[AZ6252]` | - | prose | ZIP | görünür. |  |  |
| bench_az_002816 | missed | split | `AZ6878` | `[AZ]6878` | - | prose | indeksi | qeyd |  |  |
| bench_az_003010 | missed | exact | `AZ6833` | `[AZ6833]` | - | prose | ZIP | görünür. |  |  |
| bench_az_003314 | missed | missed | `AZ6206` | `AZ6206` | - | prose | indeksi | qeyd |  |  |
| bench_az_003542 | exact | missed | `[AZ4985]` | `AZ4985` | - | prose | indeksi | qeyd |  |  |
| bench_az_003741 | exact | missed | `[AZ8998]` | `AZ8998` | - | prose | indeksi | qeyd |  | y |
| bench_az_003885 | split | exact | `AZ[754]2` | `[AZ7542]` | - | prose | ZIP | görünür. | y |  |
| bench_az_004149 | missed | exact | `AZ3753` | `[AZ3753]` | - | prose | ZIP | görünür. |  |  |
| bench_az_004196 | split | exact | `AZ[8213]` | `[AZ8213]` | - | prose | indeksi | qeyd | y | y |
| bench_az_004228 | missed | missed | `AZ9094` | `AZ9094` | - | prose | indeksi | qeyd |  |  |
| bench_az_004607 | missed | exact | `AZ8489` | `[AZ8489]` | - | prose | ZIP | görünür. |  | y |
| bench_az_004899 | missed | missed | `AZ4667` | `AZ4667` | - | prose | indeksi | qeyd |  | y |
| bench_az_004994 | exact | missed | `[AZ4985]` | `AZ4985` | - | prose | indeksi | qeyd |  |  |

## False alarms of ZIPCODE (no gold ZIPCODE under them)

### v3: 68 (policy items 0)

| shape | n |
|---|---|
| `aa9999 · gold here - · decoy benchmark_unique` | 68 |

### v4: 54 (policy items 0)

| shape | n |
|---|---|
| `aa9999 · gold here - · decoy benchmark_unique` | 22 |
| `aa · gold here - · decoy benchmark_unique` | 16 |
| `aa999999 · gold here - · decoy benchmark_unique` | 10 |
| `9999 · gold here - · decoy benchmark_unique` | 6 |

