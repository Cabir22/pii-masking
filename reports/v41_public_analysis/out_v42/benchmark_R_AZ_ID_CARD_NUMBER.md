# AZ_ID_CARD_NUMBER: spans v4.2 or v4.1 does not find exactly

| outcome | v4.2 | v4.1 |
|---|---|---|
| exact | 379 | 368 |
| split | 2 | 4 |
| covered_inexact | 0 | 0 |
| wrong_label | 0 | 1 |
| missed | 3 | 11 |

## Exact rate per frame, all spans (frames folded: case, letters, 5-letter stems)

| frame | n | v4.2 exact | v4.1 exact |
|---|---|---|---|
| `sexsi vesiq x kimi goste` | 66 | 66 (100%) | 66 (100%) |
| `sexsi sened x gorun` | 58 | 58 (100%) | 57 (98%) |
| `nomre olara x yazil` | 54 | 49 (91%) | 43 (80%) |
| `vesiq sahes x qeyd olunu` | 40 | 40 (100%) | 40 (100%) |
| `vesiq hisse x daxil etmis` | 27 | 27 (100%) | 27 (100%) |
| `sened kimi x teqdi etmis` | 25 | 25 (100%) | 25 (100%) |
| `id nomre x kimi yazmi` | 24 | 24 (100%) | 21 (88%) |
| `vesiq nomre x-dir` | 22 | 22 (100%) | 22 (100%) |
| `sexsi melum x olara qeyd` | 15 | 15 (100%) | 15 (100%) |
| `sexsi | x |` | 12 | 12 (100%) | 12 (100%) |
| `info sexsi x` | 9 | 9 (100%) | 9 (100%) |
| `"sexs " x",` | 6 | 6 (100%) | 6 (100%) |
| `vesiq sahes x qeyd olunn` | 5 | 5 (100%) | 5 (100%) |
| `nomre olara x yazlb` | 2 | 2 (100%) | 2 (100%) |
| `sexsi vesqe x kimi goste` | 2 | 2 (100%) | 2 (100%) |
| `vesiq hisse x daxil etmse` | 1 | 1 (100%) | 1 (100%) |
| `57; x;z90002596;az1994;000` | 1 | 1 (100%) | 1 (100%) |
| `zq701 x;bench.user1942@synthetic-mail4.invalid;https://support.example.com/help/article` | 1 | 1 (100%) | 1 (100%) |
| `vesiq sahes x qeyd olunb` | 1 | 1 (100%) | 1 (100%) |
| `at_be x;user@;999.12.4.1` | 1 | 1 (100%) | 1 (100%) |
| `x;https://secure.bakusteel.az/verify?secret=ctrlt1njmkkwzyyneck3oabyjwzv7yufhbbk` | 1 | 1 (100%) | 1 (100%) |
| `9657 4607; x;az1994;000` | 1 | 1 (100%) | 1 (100%) |
| `89994 x;az1994;000` | 1 | 1 (100%) | 1 (100%) |
| `x;20:08;5952 0111` | 1 | 1 (100%) | 1 (100%) |
| `x;172.18.0.33;+994 60` | 1 | 1 (100%) | 1 (100%) |

## v4.2 misses and splits by outcome (n = 5)

| | n |
|---|---|
| `missed` | 3 |
| `split` | 2 |

## v4.2 misses and splits by cut character (n = 5)

| | n |
|---|---|
| `A` | 4 |
| `A 2` | 1 |

## v4.2 misses and splits by shape (n = 5)

| | n |
|---|---|
| `aa9999999` | 5 |

## v4.2 misses and splits by context (n = 5)

| | n |
|---|---|
| `prose` | 5 |

## v4.2 misses and splits by frame (n = 5)

| | n |
|---|---|
| `nömrəsi olaraq X yazılıb` | 3 |
| `nomresi olaraq X yazılıb` | 2 |

## v4.2 misses and splits by previous word (n = 5)

| | n |
|---|---|
| `olaraq` | 5 |

## v4.2 misses and splits by next word (n = 5)

| | n |
|---|---|
| `yazılıb;` | 4 |
| `yazılıb.` | 1 |

## v4.2 misses and splits by MAC in the same document (n = 5)

| | n |
|---|---|
| `False` | 5 |

## v4.2 misses and splits by hh:mm(:ss) stamp in the same document (n = 5)

| | n |
|---|---|
| `False` | 4 |
| `True` | 1 |

## v4.2 misses and splits by v4.1 outcome on the same span (n = 5)

| | n |
|---|---|
| `missed` | 4 |
| `exact` | 1 |

## v4.2 misses and splits by doc type (n = 5)

| | n |
|---|---|
| `support_ticket` | 2 |
| `report` | 1 |
| `technical_note` | 1 |
| `crm` | 1 |

## v4.2 misses and splits by benchmark category (n = 5)

| | n |
|---|---|
| `hard_negative` | 2 |
| `mixed` | 1 |
| `natural_variant_positive` | 1 |
| `anchor_variant_hard_negative` | 1 |

## Every span (v4.2 not exact, or v4.1 not exact)

| id | v4.2 | v4.1 | v4.2 pieces | v4.1 pieces | other label (v4.2) | context | prev | next | MAC | stamp |
|---|---|---|---|---|---|---|---|---|---|---|
| bench_az_000112 | exact | missed | `[AA5019620]` | `AA5019620` | - | prose | olaraq | yazılıb. |  | y |
| bench_az_000149 | missed | missed | `AA5846934` | `AA5846934` | - | prose | olaraq | yazılıb; |  | y |
| bench_az_000846 | exact | missed | `[AA9575382]` | `AA9575382` | - | prose | olaraq | yazılıb; |  |  |
| bench_az_001164 | exact | split | `[AA0336851]` | `[AA03]368[51]` | - | prose | olaraq | yazılıb; |  |  |
| bench_az_001296 | split | exact | `AA[85]28571` | `[AA8528571]` | - | prose | olaraq | yazılıb; |  |  |
| bench_az_001565 | exact | split | `[AA2919968]` | `[AA]2919968` | - | prose | nömrəmi | kimi |  |  |
| bench_az_001815 | missed | missed | `AA2744643` | `AA2744643` | - | prose | olaraq | yazılıb. |  |  |
| bench_az_001965 | exact | split | `[AA0717645]` | `AA[0717645]` | - | prose | nömrəmi | kimi | y |  |
| bench_az_003602 | exact | missed | `[AA9069389]` | `AA9069389` | - | prose | olaraq | yazilib; |  |  |
| bench_az_003633 | exact | wrong_label | `[ZX8000467]` | `ZX8000467` | - | CSV / table | vəsiqəsi;private_key;sürücülük_vəsiqəsi;api_key;private_key | ;-----BEGIN |  |  |
| bench_az_003684 | exact | missed | `[AA9775540]` | `AA9775540` | - | prose | olaraq | yazilib. |  |  |
| bench_az_003936 | exact | missed | `[AA1122304]` | `AA1122304` | - | prose | olaraq | yazılıb; |  |  |
| bench_az_003977 | exact | missed | `[AA3720340]` | `AA3720340` | - | prose | olaraq | yazılıb; | y |  |
| bench_az_004178 | split | missed | `AA[8826743]` | `AA8826743` | - | prose | olaraq | yazılıb; |  |  |
| bench_az_004377 | missed | missed | `AA3410434` | `AA3410434` | - | prose | olaraq | yazılıb; |  |  |
| bench_az_004632 | exact | split | `[AA5953250]` | `AA[5953250]` | - | prose | sənədi | görünür. |  | y |
| bench_az_004945 | exact | missed | `[AA7434142]` | `AA7434142` | - | prose | nömrəmi | kimi |  | y |

## False alarms of AZ_ID_CARD_NUMBER (no gold AZ_ID_CARD_NUMBER under them)

