# AZ_ID_CARD_NUMBER: spans v4.1 or v4 does not find exactly

| outcome | v4.1 | v4 |
|---|---|---|
| exact | 368 | 381 |
| split | 4 | 1 |
| covered_inexact | 0 | 0 |
| wrong_label | 1 | 0 |
| missed | 11 | 2 |

## Exact rate per frame, all spans (frames folded: case, letters, 5-letter stems)

| frame | n | v4.1 exact | v4 exact |
|---|---|---|---|
| `sexsi vesiq x kimi goste` | 66 | 66 (100%) | 66 (100%) |
| `sexsi sened x gorun` | 58 | 57 (98%) | 58 (100%) |
| `nomre olara x yazil` | 54 | 43 (80%) | 51 (94%) |
| `vesiq sahes x qeyd olunu` | 40 | 40 (100%) | 40 (100%) |
| `vesiq hisse x daxil etmis` | 27 | 27 (100%) | 27 (100%) |
| `sened kimi x teqdi etmis` | 25 | 25 (100%) | 25 (100%) |
| `id nomre x kimi yazmi` | 24 | 21 (88%) | 24 (100%) |
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

## v4.1 misses and splits by outcome (n = 16)

| | n |
|---|---|
| `missed` | 11 |
| `split` | 4 |
| `wrong_label` | 1 |

## v4.1 misses and splits by cut character (n = 16)

| | n |
|---|---|
| `A` | 13 |
| `3` | 1 |
| `2` | 1 |
| `Z` | 1 |

## v4.1 misses and splits by shape (n = 16)

| | n |
|---|---|
| `aa9999999` | 16 |

## v4.1 misses and splits by context (n = 16)

| | n |
|---|---|
| `prose` | 15 |
| `CSV / table` | 1 |

## v4.1 misses and splits by frame (n = 16)

| | n |
|---|---|
| `nömrəsi olaraq X yazılıb` | 8 |
| `ID nömrəmi X kimi yazmışam` | 3 |
| `nömrəsi olaraq X yazilib` | 2 |
| `nomresi olaraq X yazılıb` | 1 |
| `X;-----BEGIN PRIVATE` | 1 |
| `şəxsiyyət sənədi X görünür` | 1 |

## v4.1 misses and splits by previous word (n = 16)

| | n |
|---|---|
| `olaraq` | 11 |
| `nömrəmi` | 3 |
| `vəsiqəsi;private_key;sürücülük_vəsiqəsi;api_key;private_key` | 1 |
| `sənədi` | 1 |

## v4.1 misses and splits by next word (n = 16)

| | n |
|---|---|
| `yazılıb;` | 7 |
| `kimi` | 3 |
| `yazılıb.` | 2 |
| `yazilib;` | 1 |
| `;-----BEGIN` | 1 |
| `yazilib.` | 1 |
| `görünür.` | 1 |

## v4.1 misses and splits by MAC in the same document (n = 16)

| | n |
|---|---|
| `False` | 14 |
| `True` | 2 |

## v4.1 misses and splits by hh:mm(:ss) stamp in the same document (n = 16)

| | n |
|---|---|
| `False` | 12 |
| `True` | 4 |

## v4.1 misses and splits by v4 outcome on the same span (n = 16)

| | n |
|---|---|
| `exact` | 14 |
| `missed` | 2 |

## v4.1 misses and splits by doc type (n = 16)

| | n |
|---|---|
| `report` | 3 |
| `crm` | 3 |
| `form` | 2 |
| `first_person_chat` | 2 |
| `email` | 1 |
| `first_person_email` | 1 |
| `technical_note` | 1 |
| `csv` | 1 |
| `support_ticket` | 1 |
| `bank_message` | 1 |

## v4.1 misses and splits by benchmark category (n = 16)

| | n |
|---|---|
| `hard_negative` | 5 |
| `natural_variant_positive` | 3 |
| `mixed` | 3 |
| `anchor_variant_hard_negative` | 2 |
| `anchor_variant_positive` | 1 |
| `structured_csv` | 1 |
| `positive_control` | 1 |

## Every span (v4.1 not exact, or v4 not exact)

| id | v4.1 | v4 | v4.1 pieces | v4 pieces | other label (v4.1) | context | prev | next | MAC | stamp |
|---|---|---|---|---|---|---|---|---|---|---|
| bench_az_000112 | missed | exact | `AA5019620` | `[AA5019620]` | - | prose | olaraq | yazılıb. |  | y |
| bench_az_000149 | missed | missed | `AA5846934` | `AA5846934` | - | prose | olaraq | yazılıb; |  | y |
| bench_az_000263 | exact | split | `[AA0422464]` | `[AA]0422464` | - | prose | olaraq | yazılıb; |  |  |
| bench_az_000846 | missed | missed | `AA9575382` | `AA9575382` | - | prose | olaraq | yazılıb; |  |  |
| bench_az_001164 | split | exact | `[AA03]368[51]` | `[AA0336851]` | - | prose | olaraq | yazılıb; |  |  |
| bench_az_001565 | split | exact | `[AA]2919968` | `[AA2919968]` | - | prose | nömrəmi | kimi |  |  |
| bench_az_001815 | missed | exact | `AA2744643` | `[AA2744643]` | - | prose | olaraq | yazılıb. |  |  |
| bench_az_001965 | split | exact | `AA[0717645]` | `[AA0717645]` | - | prose | nömrəmi | kimi | y |  |
| bench_az_003602 | missed | exact | `AA9069389` | `[AA9069389]` | - | prose | olaraq | yazilib; |  |  |
| bench_az_003633 | wrong_label | exact | `ZX8000467` | `[ZX8000467]` | AZ_DRIVER_LICENSE_NUMBER | CSV / table | vəsiqəsi;private_key;sürücülük_vəsiqəsi;api_key;private_key | ;-----BEGIN |  |  |
| bench_az_003684 | missed | exact | `AA9775540` | `[AA9775540]` | - | prose | olaraq | yazilib. |  |  |
| bench_az_003936 | missed | exact | `AA1122304` | `[AA1122304]` | - | prose | olaraq | yazılıb; |  |  |
| bench_az_003977 | missed | exact | `AA3720340` | `[AA3720340]` | - | prose | olaraq | yazılıb; | y |  |
| bench_az_004178 | missed | exact | `AA8826743` | `[AA8826743]` | - | prose | olaraq | yazılıb; |  |  |
| bench_az_004377 | missed | exact | `AA3410434` | `[AA3410434]` | - | prose | olaraq | yazılıb; |  |  |
| bench_az_004632 | split | exact | `AA[5953250]` | `[AA5953250]` | - | prose | sənədi | görünür. |  | y |
| bench_az_004945 | missed | exact | `AA7434142` | `[AA7434142]` | - | prose | nömrəmi | kimi |  | y |

## False alarms of AZ_ID_CARD_NUMBER (no gold AZ_ID_CARD_NUMBER under them)

### v4: 5 (policy items 0)

| shape | n |
|---|---|
| `aa999999 · gold here AZ_DRIVER_LICENSE_NUMBER · decoy -` | 3 |
| `99 · gold here AZ_DRIVER_LICENSE_NUMBER · decoy -` | 1 |
| `999 · gold here AZ_DRIVER_LICENSE_NUMBER · decoy -` | 1 |

