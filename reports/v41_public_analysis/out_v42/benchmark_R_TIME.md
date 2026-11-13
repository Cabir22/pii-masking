# TIME: spans v4.2 or v4.1 does not find exactly

| outcome | v4.2 | v4.1 |
|---|---|---|
| exact | 403 | 406 |
| split | 5 | 2 |
| covered_inexact | 0 | 0 |
| wrong_label | 0 | 0 |
| missed | 5 | 5 |

## Exact rate per frame, all spans (frames folded: case, letters, 5-letter stems)

| frame | n | v4.2 exact | v4.1 exact |
|---|---|---|---|
| `emeli vaxti x yazil` | 64 | 64 (100%) | 64 (100%) |
| `gorus vaxti x qeyd olunu` | 62 | 62 (100%) | 62 (100%) |
| `teqvi x gorun` | 57 | 48 (84%) | 51 (89%) |
| `saat x kimi goste` | 53 | 53 (100%) | 53 (100%) |
| `vaxt hisse x yazmi` | 46 | 45 (98%) | 46 (100%) |
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
| `x;502/3;elesrefzade;+994966569019;12345` | 1 | 1 (100%) | 0 (0%) |
| `.nurt x;https://login.azertelekom.az/session/resume?jwt=xfa5alzuzssg1jeltpxb47zdy2c8zuu` | 1 | 1 (100%) | 1 (100%) |
| `zx800 x;5952 0111` | 1 | 1 (100%) | 1 (100%) |
| `0836 1191; x;c35s42574;12345` | 1 | 1 (100%) | 1 (100%) |
| `89994 x;4621636046;12345` | 1 | 1 (100%) | 1 (100%) |

## v4.2 misses and splits by outcome (n = 10)

| | n |
|---|---|
| `split` | 5 |
| `missed` | 5 |

## v4.2 misses and splits by cut character (n = 10)

| | n |
|---|---|
| `1` | 5 |
| `0` | 4 |
| `:` | 1 |

## v4.2 misses and splits by shape (n = 10)

| | n |
|---|---|
| `99:99` | 10 |

## v4.2 misses and splits by context (n = 10)

| | n |
|---|---|
| `prose` | 10 |

## v4.2 misses and splits by frame (n = 10)

| | n |
|---|---|
| `Təqvimdə X görünür` | 8 |
| `Təqvimdə X gorunur` | 1 |
| `vaxt hissəsinə X yazmışam` | 1 |

## v4.2 misses and splits by previous word (n = 10)

| | n |
|---|---|
| `Təqvimdə` | 9 |
| `hissəsinə` | 1 |

## v4.2 misses and splits by next word (n = 10)

| | n |
|---|---|
| `görünür;` | 7 |
| `gorunur;` | 1 |
| `yazmışam.` | 1 |
| `görünür.` | 1 |

## v4.2 misses and splits by MAC in the same document (n = 10)

| | n |
|---|---|
| `False` | 9 |
| `True` | 1 |

## v4.2 misses and splits by hh:mm(:ss) stamp in the same document (n = 10)

| | n |
|---|---|
| `True` | 10 |

## v4.2 misses and splits by v4.1 outcome on the same span (n = 10)

| | n |
|---|---|
| `missed` | 4 |
| `exact` | 4 |
| `split` | 2 |

## v4.2 misses and splits by doc type (n = 10)

| | n |
|---|---|
| `legal` | 3 |
| `form` | 2 |
| `report` | 1 |
| `bank_message` | 1 |
| `email` | 1 |
| `first_person_email` | 1 |
| `support_ticket` | 1 |

## v4.2 misses and splits by benchmark category (n = 10)

| | n |
|---|---|
| `natural_variant_positive` | 4 |
| `hard_negative` | 2 |
| `corrected_hard_negative` | 1 |
| `mixed` | 1 |
| `natural_variant_hard_negative` | 1 |
| `positive_control` | 1 |

## Every span (v4.2 not exact, or v4.1 not exact)

| id | v4.2 | v4.1 | v4.2 pieces | v4.1 pieces | other label (v4.2) | context | prev | next | MAC | stamp |
|---|---|---|---|---|---|---|---|---|---|---|
| bench_az_000406 | split | missed | `11:[09]` | `11:09` | - | prose | Təqvimdə | görünür; |  | y |
| bench_az_000716 | missed | missed | `14:24` | `14:24` | - | prose | Təqvimdə | gorunur; |  | y |
| bench_az_001425 | split | exact | `11[:12]` | `[11:12]` | - | prose | Təqvimdə | görünür; |  | y |
| bench_az_001587 | exact | missed | `[09:27]` | `09:27` | - | CSV / table | saat;bina_nömrəsi;soyad;fin_kodu;cvv | ;502/3;Ələşrəfzadə;+994966569019;12345 |  | y |
| bench_az_001615 | split | exact | `[14]:[24]` | `[14:24]` | - | prose | Təqvimdə | görünür; |  | y |
| bench_az_001825 | missed | exact | `08:00` | `[08:00]` | - | prose | hissəsinə | yazmışam. |  | y |
| bench_az_002119 | missed | split | `14:39` | `14[:39]` | - | prose | Təqvimdə | görünür; |  | y |
| bench_az_002530 | split | missed | `12[:20]` | `12:20` | - | prose | Təqvimdə | görünür; | y | y |
| bench_az_003556 | missed | missed | `00:12` | `00:12` | - | prose | Təqvimdə | görünür; |  | y |
| bench_az_004521 | missed | split | `01:15` | `[01:]15` | - | prose | Təqvimdə | görünür; |  | y |
| bench_az_004666 | split | exact | `02[:11]` | `[02:11]` | - | prose | Təqvimdə | görünür. |  | y |

## False alarms of TIME (no gold TIME under them)

### v4.1: 13 (policy items 0)

| shape | n |
|---|---|
| `99:99:99 · gold here - · decoy benchmark_unique` | 6 |
| `99 · gold here - · decoy benchmark_unique` | 5 |
| `99:99 · gold here - · decoy benchmark_unique` | 2 |

### v4.2: 5 (policy items 0)

| shape | n |
|---|---|
| `99 · gold here - · decoy benchmark_unique` | 3 |
| `99:99:99 · gold here - · decoy benchmark_unique` | 1 |
| `99:99 · gold here - · decoy benchmark_unique` | 1 |

