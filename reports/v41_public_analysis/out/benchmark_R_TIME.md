# TIME: spans v4 or v3 does not find exactly

| outcome | v4 | v3 |
|---|---|---|
| exact | 403 | 401 |
| split | 5 | 3 |
| covered_inexact | 0 | 0 |
| wrong_label | 0 | 0 |
| missed | 5 | 9 |

## Exact rate per frame, all spans (frames folded: case, letters, 5-letter stems)

| frame | n | v4 exact | v3 exact |
|---|---|---|---|
| `emeli vaxti x yazil` | 64 | 64 (100%) | 64 (100%) |
| `gorus vaxti x qeyd olunu` | 62 | 62 (100%) | 61 (98%) |
| `teqvi x gorun` | 57 | 48 (84%) | 46 (81%) |
| `saat x kimi goste` | 53 | 53 (100%) | 53 (100%) |
| `vaxt hisse x yazmi` | 46 | 46 (100%) | 46 (100%) |
| `mene x vaxti zeng` | 28 | 28 (100%) | 28 (100%) |
| `gorus vaxti x kimi qeyd` | 24 | 24 (100%) | 24 (100%) |
| `saat olara x secmi` | 20 | 20 (100%) | 20 (100%) |
| `saat melum x olara qeyd` | 12 | 12 (100%) | 12 (100%) |
| `info saat= x` | 10 | 10 (100%) | 10 (100%) |
| `"saat " x",` | 10 | 10 (100%) | 10 (100%) |
| `saat | x |` | 9 | 9 (100%) | 9 (100%) |
| `saat x kimi gostr` | 3 | 3 (100%) | 3 (100%) |
| `gorus vaxti x qeyd olunb` | 2 | 2 (100%) | 2 (100%) |
| `priva key-- x;user@;999.12.4.1` | 2 | 2 (100%) | 2 (100%) |
| `z79le x;ali musta` | 1 | 1 (100%) | 1 (100%) |
| `mrndn x;user@;999.12.4.1` | 1 | 1 (100%) | 1 (100%) |
| `emeli vaxti x yazlb` | 1 | 1 (100%) | 1 (100%) |
| `2001: x;z4hnwp2;az1994;000` | 1 | 1 (100%) | 1 (100%) |
| `569;q qeseb x;abc;-----begin publi` | 1 | 1 (100%) | 1 (100%) |
| `x;502/3;elesrefzade;+994966569019;12345` | 1 | 0 (0%) | 1 (100%) |
| `.nurt x;https://login.azertelekom.az/session/resume?jwt=xfa5alzuzssg1jeltpxb47zdy2c8zuu` | 1 | 1 (100%) | 1 (100%) |
| `zx800 x;5952 0111` | 1 | 1 (100%) | 1 (100%) |
| `0836 1191; x;c35s42574;12345` | 1 | 1 (100%) | 1 (100%) |
| `89994 x;4621636046;12345` | 1 | 1 (100%) | 1 (100%) |

## v4 misses and splits by outcome (n = 10)

| | n |
|---|---|
| `split` | 5 |
| `missed` | 5 |

## v4 misses and splits by cut character (n = 10)

| | n |
|---|---|
| `1` | 7 |
| `0` | 3 |

## v4 misses and splits by shape (n = 10)

| | n |
|---|---|
| `99:99` | 10 |

## v4 misses and splits by context (n = 10)

| | n |
|---|---|
| `prose` | 9 |
| `CSV / table` | 1 |

## v4 misses and splits by frame (n = 10)

| | n |
|---|---|
| `Təqvimdə X görünür` | 8 |
| `Təqvimdə X gorunur` | 1 |
| `X;502/3;Ələşrəfzadə;+994966569019;12345` | 1 |

## v4 misses and splits by previous word (n = 10)

| | n |
|---|---|
| `Təqvimdə` | 9 |
| `saat;bina_nömrəsi;soyad;fin_kodu;cvv` | 1 |

## v4 misses and splits by next word (n = 10)

| | n |
|---|---|
| `görünür;` | 7 |
| `görünür.` | 1 |
| `gorunur;` | 1 |
| `;502/3;Ələşrəfzadə;+994966569019;12345` | 1 |

## v4 misses and splits by MAC in the same document (n = 10)

| | n |
|---|---|
| `False` | 9 |
| `True` | 1 |

## v4 misses and splits by hh:mm(:ss) stamp in the same document (n = 10)

| | n |
|---|---|
| `True` | 10 |

## v4 misses and splits by v3 outcome on the same span (n = 10)

| | n |
|---|---|
| `exact` | 5 |
| `missed` | 3 |
| `split` | 2 |

## v4 misses and splits by doc type (n = 10)

| | n |
|---|---|
| `legal` | 3 |
| `email` | 2 |
| `bank_message` | 2 |
| `report` | 1 |
| `csv` | 1 |
| `insurance` | 1 |

## v4 misses and splits by benchmark category (n = 10)

| | n |
|---|---|
| `natural_variant_positive` | 3 |
| `anchor_variant_positive` | 2 |
| `hard_negative` | 1 |
| `corrected_hard_negative` | 1 |
| `structured_csv` | 1 |
| `mixed` | 1 |
| `natural_variant_hard_negative` | 1 |

## Every span (v4 not exact, or v3 not exact)

| id | v4 | v3 | v4 pieces | v3 pieces | other label (v4) | context | prev | next | MAC | stamp |
|---|---|---|---|---|---|---|---|---|---|---|
| bench_az_000406 | split | exact | `11[:09]` | `[11:09]` | - | prose | Təqvimdə | görünür; |  | y |
| bench_az_000562 | missed | split | `05:26` | `05[:26]` | - | prose | Təqvimdə | görünür. |  | y |
| bench_az_000716 | missed | missed | `14:24` | `14:24` | - | prose | Təqvimdə | gorunur; |  | y |
| bench_az_001208 | exact | missed | `[08:38]` | `08:38` | - | prose | Təqvimdə | görünür; |  | y |
| bench_az_001287 | exact | missed | `[01:54]` | `01:54` | - | prose | Təqvimdə | görünür. |  | y |
| bench_az_001363 | split | exact | `16[:32]` | `[16:32]` | - | prose | Təqvimdə | görünür; |  | y |
| bench_az_001425 | split | split | `11[:12]` | `11[:]12` | - | prose | Təqvimdə | görünür; |  | y |
| bench_az_001587 | missed | exact | `09:27` | `[09:27]` | - | CSV / table | saat;bina_nömrəsi;soyad;fin_kodu;cvv | ;502/3;Ələşrəfzadə;+994966569019;12345 |  | y |
| bench_az_001615 | missed | missed | `14:24` | `14:24` | - | prose | Təqvimdə | görünür; |  | y |
| bench_az_001694 | exact | missed | `[01:22]` | `01:22` | - | prose | Təqvimdə | görünür; |  | y |
| bench_az_002119 | missed | missed | `14:39` | `14:39` | - | prose | Təqvimdə | görünür; |  | y |
| bench_az_002530 | split | exact | `12:[20]` | `[12:20]` | - | prose | Təqvimdə | görünür; | y | y |
| bench_az_002728 | exact | missed | `[18:44]` | `18:44` | - | prose | Təqvimdə | görünür; |  | y |
| bench_az_003180 | exact | split | `[16:45]` | `[16:]45` | - | prose | vaxtı | qeyd |  | y |
| bench_az_003556 | exact | missed | `[00:12]` | `00:12` | - | prose | Təqvimdə | görünür; |  | y |
| bench_az_003845 | exact | missed | `[01:27]` | `01:27` | - | prose | Təqvimdə | görünür; |  | y |
| bench_az_004978 | split | exact | `01[:08]` | `[01:08]` | - | prose | Təqvimdə | görünür; |  | y |

## False alarms of TIME (no gold TIME under them)

### v3: 1 (policy items 0)

| shape | n |
|---|---|
| `99 · gold here - · decoy benchmark_unique` | 1 |

### v4: 14 (policy items 0)

| shape | n |
|---|---|
| `99 · gold here - · decoy benchmark_unique` | 6 |
| `99:99:99 · gold here - · decoy benchmark_unique` | 4 |
| `99:99 · gold here - · decoy benchmark_unique` | 3 |
| `: · gold here - · decoy benchmark_unique` | 1 |

