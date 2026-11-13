# ACCESS_TOKEN: spans v4.1 or v4 does not find exactly

| outcome | v4.1 | v4 |
|---|---|---|
| exact | 384 | 382 |
| split | 1 | 2 |
| covered_inexact | 0 | 0 |
| wrong_label | 0 | 1 |
| missed | 0 | 0 |

## Exact rate per frame, all spans (frames folded: case, letters, 5-letter stems)

| frame | n | v4.1 exact | v4 exact |
|---|---|---|---|
| `tarix acces x gorun` | 68 | 68 (100%) | 68 (100%) |
| `ucun token x qeyd olunu` | 55 | 55 (100%) | 55 (100%) |
| `acces token x kimi goste` | 49 | 49 (100%) | 49 (100%) |
| `servi x token gonde` | 46 | 46 (100%) | 46 (100%) |
| `sessi qeydi x yazil` | 46 | 46 (100%) | 46 (100%) |
| `acces olara x qeyd etmis` | 39 | 38 (97%) | 38 (97%) |
| `token kimi x istif edire` | 26 | 26 (100%) | 26 (100%) |
| `acces melum x olara qeyd` | 13 | 13 (100%) | 13 (100%) |
| `acces | x |` | 11 | 11 (100%) | 11 (100%) |
| `"acce " x",` | 8 | 8 (100%) | 8 (100%) |
| `info acces x` | 8 | 8 (100%) | 8 (100%) |
| `acess token x kimi goste` | 2 | 2 (100%) | 2 (100%) |
| `aces token x kimi goste` | 2 | 2 (100%) | 2 (100%) |
| `172.2 x;25:81;999` | 1 | 1 (100%) | 1 (100%) |
| `sessi qeydi x yazlb` | 1 | 1 (100%) | 1 (100%) |
| `minas x;az1994;000` | 1 | 1 (100%) | 1 (100%) |
| `priva key-- x;25:81;999` | 1 | 1 (100%) | 1 (100%) |
| `x;z90002171;zx8002172;user@;999.12.4.1` | 1 | 1 (100%) | 1 (100%) |
| `ucun token x qeyd olunb` | 1 | 1 (100%) | 1 (100%) |
| `bike; x;25:81;999` | 1 | 1 (100%) | 1 (100%) |
| `x;at_bench_0453_tggaeylpuhfybznfyvlmphmk0dkpua;z90000454;503;12345` | 1 | 1 (100%) | 1 (100%) |
| `at_be x;z90000454;503;12345` | 1 | 1 (100%) | 1 (100%) |
| `x;parlament prosp` | 1 | 1 (100%) | 0 (0%) |
| `at_be prosp x;abc;-----begin publi` | 1 | 1 (100%) | 0 (0%) |
| `506/7 x;https://support.example.com/help/article/10400;p123` | 1 | 1 (100%) | 1 (100%) |

## v4.1 misses and splits by outcome (n = 1)

| | n |
|---|---|
| `split` | 1 |

## v4.1 misses and splits by cut character (n = 1)

| | n |
|---|---|
| `i` | 1 |

## v4.1 misses and splits by shape (n = 1)

| | n |
|---|---|
| `aaa_aa9-aa9aaaaaaaa-aaaaaaaaa9aaaaa9aaaa-a` | 1 |

## v4.1 misses and splits by context (n = 1)

| | n |
|---|---|
| `prose` | 1 |

## v4.1 misses and splits by frame (n = 1)

| | n |
|---|---|
| `access_token olaraq X qeyd etmişəm` | 1 |

## v4.1 misses and splits by previous word (n = 1)

| | n |
|---|---|
| `olaraq` | 1 |

## v4.1 misses and splits by next word (n = 1)

| | n |
|---|---|
| `qeyd` | 1 |

## v4.1 misses and splits by MAC in the same document (n = 1)

| | n |
|---|---|
| `False` | 1 |

## v4.1 misses and splits by hh:mm(:ss) stamp in the same document (n = 1)

| | n |
|---|---|
| `False` | 1 |

## v4.1 misses and splits by v4 outcome on the same span (n = 1)

| | n |
|---|---|
| `split` | 1 |

## v4.1 misses and splits by doc type (n = 1)

| | n |
|---|---|
| `first_person_form` | 1 |

## v4.1 misses and splits by benchmark category (n = 1)

| | n |
|---|---|
| `natural_variant_hard_negative` | 1 |

## Every span (v4.1 not exact, or v4 not exact)

| id | v4.1 | v4 | v4.1 pieces | v4 pieces | other label (v4.1) | context | prev | next | MAC | stamp |
|---|---|---|---|---|---|---|---|---|---|---|
| bench_az_001725 | split | split | `[tok_ua6-bg8sFgNpGRj-uBUtXkCLw2FRwtg4fDKb-]i` | `[tok_ua6-bg8sFgNpGRj-uBUtXkCLw2FRwtg4fDKb]-i` | - | prose | olaraq | qeyd |  |  |
| bench_az_004411 | exact | split | `[at_bench_2016_LaJtnw55cVJyHyIXQ837RKypFlOYfq]` | `at_bench_2016_[LaJtnw]55[cVJyHy]IX[Q]837RKypFlOYfq` | - | CSV / table | access_token;küçə;access_token;api_key;private_key | ;Parlament |  |  |
| bench_az_004411 | exact | wrong_label | `[at_bench_2018_8otCFUO93OOkwQTmy1L7GEpPBXkt77]` | `at_bench_2018_8otCFUO93OOkwQTmy1L7GEpPBXkt77` | - | CSV / table | prospekti; | ;abc;-----BEGIN |  |  |

## False alarms of ACCESS_TOKEN (no gold ACCESS_TOKEN under them)

