# IPV4_ADDRESS: spans v4.2 or v4.1 does not find exactly

| outcome | v4.2 | v4.1 |
|---|---|---|
| exact | 414 | 405 |
| split | 4 | 9 |
| covered_inexact | 0 | 0 |
| wrong_label | 0 | 0 |
| missed | 6 | 10 |

## Exact rate per frame, all spans (frames folded: case, letters, 5-letter stems)

| frame | n | v4.2 exact | v4.1 exact |
|---|---|---|---|
| `logda ipv4 x qeyd olunu` | 69 | 65 (94%) | 56 (81%) |
| `menbe ip x kimi goste` | 66 | 65 (98%) | 66 (100%) |
| `sebek tarix x gorun` | 64 | 63 (98%) | 63 (98%) |
| `serve unvan x yazil` | 59 | 56 (95%) | 59 (100%) |
| `unvan kimi x qeyd etmis` | 29 | 29 (100%) | 29 (100%) |
| `ipv4 unvan x-dir` | 26 | 26 (100%) | 26 (100%) |
| `texni murac x ip-si elave` | 23 | 23 (100%) | 23 (100%) |
| `logda x ip unvan` | 16 | 16 (100%) | 16 (100%) |
| `ipv4 | x |` | 16 | 16 (100%) | 16 (100%) |
| `"ipv4 " x",` | 16 | 16 (100%) | 16 (100%) |
| `info ipv4= x` | 13 | 13 (100%) | 13 (100%) |
| `ipv4 melum x olara qeyd` | 8 | 8 (100%) | 8 (100%) |
| `logda x ip unvni` | 2 | 2 (100%) | 2 (100%) |
| `logda ipv4 x qeyd olunb` | 2 | 2 (100%) | 2 (100%) |
| `menbe ip x kimi gostr` | 2 | 2 (100%) | 2 (100%) |
| `x;11.08.2033;at_bench_1604_butfjarx4qc0fgrha6ixef8qliwlyn;25:81;999` | 1 | 1 (100%) | 0 (0%) |
| `serve unvni x yazlb` | 1 | 0 (0%) | 1 (100%) |
| `x;89994332608139790817;otken;https://support.example.com/news/archive/10370;p123` | 1 | 1 (100%) | 1 (100%) |
| `aygul x;81;25:81;999` | 1 | 1 (100%) | 0 (0%) |
| `x;2367843398;zq701467;abc;-----begin publi` | 1 | 1 (100%) | 1 (100%) |
| `priva key-- x;danaci;https://support.example.com/help/article/10820;p123` | 1 | 1 (100%) | 1 (100%) |
| `x;zq702262;+994 60` | 1 | 1 (100%) | 0 (0%) |
| `zx800 x;+994 60` | 1 | 1 (100%) | 1 (100%) |
| `zx800 x;user@;999.12.4.1` | 1 | 1 (100%) | 0 (0%) |
| `x;120;ebulhesen;abc;-----begin publi` | 1 | 1 (100%) | 1 (100%) |

## v4.2 misses and splits by outcome (n = 10)

| | n |
|---|---|
| `missed` | 6 |
| `split` | 4 |

## v4.2 misses and splits by cut character (n = 10)

| | n |
|---|---|
| `2` | 5 |
| `2 2` | 1 |
| `. .` | 1 |
| `.` | 1 |
| `1` | 1 |
| `3` | 1 |

## v4.2 misses and splits by shape (n = 10)

| | n |
|---|---|
| `4 parts` | 10 |
| `no one-digit octet` | 7 |
| `1 one-digit octets` | 3 |

## v4.2 misses and splits by context (n = 10)

| | n |
|---|---|
| `prose` | 10 |

## v4.2 misses and splits by frame (n = 10)

| | n |
|---|---|
| `Logda IPv4 X qeyd olunub` | 4 |
| `Server ünvanı X yazılıb` | 3 |
| `Server unvnı X yazlb` | 1 |
| `Şəbəkə tarixçəsində X görünür` | 1 |
| `Mənbə IP X kimi göstərilib` | 1 |

## v4.2 misses and splits by previous word (n = 10)

| | n |
|---|---|
| `IPv4` | 4 |
| `ünvanı` | 3 |
| `unvnı` | 1 |
| `tarixçəsində` | 1 |
| `IP` | 1 |

## v4.2 misses and splits by next word (n = 10)

| | n |
|---|---|
| `qeyd` | 4 |
| `yazılıb;` | 3 |
| `yazlb;` | 1 |
| `görünür;` | 1 |
| `kimi` | 1 |

## v4.2 misses and splits by MAC in the same document (n = 10)

| | n |
|---|---|
| `False` | 9 |
| `True` | 1 |

## v4.2 misses and splits by hh:mm(:ss) stamp in the same document (n = 10)

| | n |
|---|---|
| `False` | 10 |

## v4.2 misses and splits by v4.1 outcome on the same span (n = 10)

| | n |
|---|---|
| `exact` | 5 |
| `missed` | 4 |
| `split` | 1 |

## v4.2 misses and splits by doc type (n = 10)

| | n |
|---|---|
| `email` | 2 |
| `support_ticket` | 2 |
| `insurance` | 2 |
| `crm` | 2 |
| `bank_message` | 1 |
| `legal` | 1 |

## v4.2 misses and splits by benchmark category (n = 10)

| | n |
|---|---|
| `mixed` | 5 |
| `anchor_variant_positive` | 2 |
| `positive_control` | 1 |
| `hard_negative` | 1 |
| `natural_variant_positive` | 1 |

## Every span (v4.2 not exact, or v4.1 not exact)

| id | v4.2 | v4.1 | v4.2 pieces | v4.1 pieces | other label (v4.2) | context | prev | next | MAC | stamp |
|---|---|---|---|---|---|---|---|---|---|---|
| bench_az_000028 | split | missed | `23.37.[2]24.90` | `23.37.224.90` | - | prose | IPv4 | qeyd |  |  |
| bench_az_000056 | exact | split | `[172.28.6.103]` | `[172].[28.6.103]` | - | CSV / table | ipv4;tarix;access_token;saat;yaş | ;11.08.2033;at_bench_1604_buTfJArX4qc0FgRha6Ixef8QlIwlYn;25: |  | y |
| bench_az_000084 | split | missed | `[18].30.[67].[202]` | `18.30.67.202` | - | prose | IPv4 | qeyd |  |  |
| bench_az_000085 | exact | missed | `[99.63.17.79]` | `99.63.17.79` | - | prose | IPv4 | qeyd |  |  |
| bench_az_000289 | split | exact | `[1].[76.78.96]` | `[1.76.78.96]` | - | prose | ünvanı | yazılıb; |  |  |
| bench_az_000531 | exact | split | `[46.81.181.251]` | `[46].[81].[18]1.251` | - | prose | IPv4 | qeyd |  | y |
| bench_az_000602 | missed | exact | `253.6.123.87` | `[253.6.123.87]` | - | prose | unvnı | yazlb; |  |  |
| bench_az_000659 | exact | split | `[172.18.0.63]` | `[172.18].[0].[63]` | - | CSV / table | Aygül; | ;81;25:81;999 |  | y |
| bench_az_000991 | missed | missed | `14.1.25.76` | `14.1.25.76` | - | prose | tarixçəsində | görünür; | y |  |
| bench_az_001734 | exact | split | `[172.27.9.12]` | `[172].[27.9.12]` | - | CSV / table | ipv4;sürücülük_vəsiqəsi;telefon;e_poçt;ipv4 | ;ZQ702262;+994 |  |  |
| bench_az_002012 | exact | missed | `[34.20.135.233]` | `34.20.135.233` | - | prose | IPv4 | qeyd |  |  |
| bench_az_002281 | exact | missed | `[131.15.66.23]` | `131.15.66.23` | - | prose | IPv4 | qeyd |  |  |
| bench_az_002884 | missed | exact | `251.15.53.187` | `[251.15.53.187]` | - | prose | ünvanı | yazılıb; |  |  |
| bench_az_003036 | missed | missed | `239.228.36.81` | `239.228.36.81` | - | prose | IPv4 | qeyd |  |  |
| bench_az_003123 | exact | split | `[172.21.2.31]` | `[172].[21.2.31]` | - | CSV / table | ZX8000528;17.02.2039; | ;user@;999.12.4.1 |  |  |
| bench_az_003162 | exact | missed | `[33.61.146.13]` | `33.61.146.13` | - | prose | IPv4 | qeyd |  |  |
| bench_az_003245 | missed | exact | `38.14.72.49` | `[38.14.72.49]` | - | prose | ünvanı | yazılıb; |  |  |
| bench_az_003422 | exact | missed | `[114.104.25.240]` | `114.104.25.240` | - | prose | IPv4 | qeyd |  |  |
| bench_az_003754 | missed | exact | `237.142.86.154` | `[237.142.86.154]` | - | prose | IP | kimi |  |  |
| bench_az_003838 | exact | split | `[172.18.0.153]` | `[172.18].[0.153]` | - | CSV / table | Bikə; | ;at_bench_0153_iS68BGFAdoSiUKf6UyBUNGL4D3v7WF;25:81;999 |  | y |
| bench_az_003984 | exact | split | `[183.219.248.57]` | `183.[219.248.]57` | - | prose | IPv4 | qeyd |  | y |
| bench_az_004113 | exact | missed | `[232.108.56.45]` | `232.108.56.45` | - | prose | IPv4 | qeyd |  |  |
| bench_az_004178 | split | split | `244.[87.235.104]` | `244[.87.235.104]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_004894 | exact | split | `[161.227.52.161]` | `161.227.52.[161]` | - | prose | IPv4 | qeyd |  | y |

## False alarms of IPV4_ADDRESS (no gold IPV4_ADDRESS under them)

### v4.1: 109 (policy items 0)

| shape | n |
|---|---|
| `9.9.9.9 · gold here - · decoy benchmark_unique` | 49 |
| `999.9.9.9 · gold here - · decoy benchmark_unique` | 30 |
| `9 · gold here - · decoy benchmark_unique` | 6 |
| `9.9 · gold here - · decoy benchmark_unique` | 5 |
| `999 · gold here - · decoy benchmark_unique` | 4 |
| `99.9.9 · gold here - · decoy benchmark_unique` | 2 |
| `.9.9.9 · gold here - · decoy benchmark_unique` | 2 |
| `99 · gold here - · decoy benchmark_unique` | 2 |
| `.9 · gold here - · decoy benchmark_unique` | 2 |
| `9 · gold here - · decoy -` | 2 |
| `9.9.9 · gold here - · decoy benchmark_unique` | 1 |
| `9.9.9.9 · gold here - · decoy benchmark_ambiguous` | 1 |
| `9.9.9.9 · gold here - · decoy -` | 1 |
| `.9.9 · gold here - · decoy benchmark_ambiguous` | 1 |
| `99 · gold here - · decoy -` | 1 |

### v4.2: 46 (policy items 0)

| shape | n |
|---|---|
| `9.9.9.9 · gold here - · decoy benchmark_unique` | 36 |
| `9 · gold here - · decoy benchmark_unique` | 5 |
| `999.9.9.9 · gold here - · decoy benchmark_unique` | 4 |
| `99 · gold here MAC_ADDRESS · decoy -` | 1 |

