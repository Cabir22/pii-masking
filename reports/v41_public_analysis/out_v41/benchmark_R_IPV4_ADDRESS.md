# IPV4_ADDRESS: spans v4.1 or v4 does not find exactly

| outcome | v4.1 | v4 |
|---|---|---|
| exact | 405 | 365 |
| split | 9 | 13 |
| covered_inexact | 0 | 0 |
| wrong_label | 0 | 0 |
| missed | 10 | 46 |

## Exact rate per frame, all spans (frames folded: case, letters, 5-letter stems)

| frame | n | v4.1 exact | v4 exact |
|---|---|---|---|
| `logda ipv4 x qeyd olunu` | 69 | 56 (81%) | 25 (36%) |
| `menbe ip x kimi goste` | 66 | 66 (100%) | 61 (92%) |
| `sebek tarix x gorun` | 64 | 63 (98%) | 63 (98%) |
| `serve unvan x yazil` | 59 | 59 (100%) | 54 (92%) |
| `unvan kimi x qeyd etmis` | 29 | 29 (100%) | 28 (97%) |
| `ipv4 unvan x-dir` | 26 | 26 (100%) | 26 (100%) |
| `texni murac x ip-si elave` | 23 | 23 (100%) | 23 (100%) |
| `logda x ip unvan` | 16 | 16 (100%) | 16 (100%) |
| `ipv4 | x |` | 16 | 16 (100%) | 16 (100%) |
| `"ipv4 " x",` | 16 | 16 (100%) | 16 (100%) |
| `info ipv4= x` | 13 | 13 (100%) | 13 (100%) |
| `ipv4 melum x olara qeyd` | 8 | 8 (100%) | 8 (100%) |
| `logda x ip unvni` | 2 | 2 (100%) | 2 (100%) |
| `logda ipv4 x qeyd olunb` | 2 | 2 (100%) | 0 (0%) |
| `menbe ip x kimi gostr` | 2 | 2 (100%) | 2 (100%) |
| `x;11.08.2033;at_bench_1604_butfjarx4qc0fgrha6ixef8qliwlyn;25:81;999` | 1 | 0 (0%) | 1 (100%) |
| `serve unvni x yazlb` | 1 | 1 (100%) | 0 (0%) |
| `x;89994332608139790817;otken;https://support.example.com/news/archive/10370;p123` | 1 | 1 (100%) | 1 (100%) |
| `aygul x;81;25:81;999` | 1 | 0 (0%) | 1 (100%) |
| `x;2367843398;zq701467;abc;-----begin publi` | 1 | 1 (100%) | 1 (100%) |
| `priva key-- x;danaci;https://support.example.com/help/article/10820;p123` | 1 | 1 (100%) | 1 (100%) |
| `x;zq702262;+994 60` | 1 | 0 (0%) | 1 (100%) |
| `zx800 x;+994 60` | 1 | 1 (100%) | 1 (100%) |
| `zx800 x;user@;999.12.4.1` | 1 | 0 (0%) | 1 (100%) |
| `x;120;ebulhesen;abc;-----begin publi` | 1 | 1 (100%) | 1 (100%) |

## v4.1 misses and splits by outcome (n = 19)

| | n |
|---|---|
| `missed` | 10 |
| `split` | 9 |

## v4.1 misses and splits by cut character (n = 19)

| | n |
|---|---|
| `1` | 5 |
| `2` | 4 |
| `.` | 4 |
| `3` | 2 |
| `9` | 1 |
| `. . 1` | 1 |
| `. .` | 1 |
| `1 5` | 1 |

## v4.1 misses and splits by shape (n = 19)

| | n |
|---|---|
| `4 parts` | 19 |
| `no one-digit octet` | 13 |
| `1 one-digit octets` | 6 |
| `private` | 5 |

## v4.1 misses and splits by context (n = 19)

| | n |
|---|---|
| `prose` | 14 |
| `CSV / table` | 5 |

## v4.1 misses and splits by frame (n = 19)

| | n |
|---|---|
| `Logda IPv4 X qeyd olunub` | 13 |
| `X;11.08.2033;at_bench_1604_buTfJArX4qc0FgRha6Ixef8QlIwlYn;25:81;999` | 1 |
| `Aygül; X;81;25:81;999` | 1 |
| `Şəbəkə tarixçəsində X görünür` | 1 |
| `X;ZQ702262;+994 60` | 1 |
| `ZX8000528;17.02.2039; X;user@;999.12.4.1` | 1 |
| `Bikə; X;at_bench_0153_iS68BGFAdoSiUKf6UyBUNGL4D3v7WF;25:81;999` | 1 |

## v4.1 misses and splits by previous word (n = 19)

| | n |
|---|---|
| `IPv4` | 13 |
| `ipv4;tarix;access_token;saat;yaş` | 1 |
| `Aygül;` | 1 |
| `tarixçəsində` | 1 |
| `ipv4;sürücülük_vəsiqəsi;telefon;e_poçt;ipv4` | 1 |
| `ZX8000528;17.02.2039;` | 1 |
| `Bikə;` | 1 |

## v4.1 misses and splits by next word (n = 19)

| | n |
|---|---|
| `qeyd` | 13 |
| `;11.08.2033;at_bench_1604_buTfJArX4qc0FgRha6Ixef8QlIwlYn;25:` | 1 |
| `;81;25:81;999` | 1 |
| `görünür;` | 1 |
| `;ZQ702262;+994` | 1 |
| `;user@;999.12.4.1` | 1 |
| `;at_bench_0153_iS68BGFAdoSiUKf6UyBUNGL4D3v7WF;25:81;999` | 1 |

## v4.1 misses and splits by MAC in the same document (n = 19)

| | n |
|---|---|
| `False` | 18 |
| `True` | 1 |

## v4.1 misses and splits by hh:mm(:ss) stamp in the same document (n = 19)

| | n |
|---|---|
| `False` | 13 |
| `True` | 6 |

## v4.1 misses and splits by v4 outcome on the same span (n = 19)

| | n |
|---|---|
| `missed` | 14 |
| `exact` | 5 |

## v4.1 misses and splits by doc type (n = 19)

| | n |
|---|---|
| `csv` | 5 |
| `email` | 3 |
| `support_ticket` | 3 |
| `bank_message` | 3 |
| `crm` | 3 |
| `insurance` | 1 |
| `form` | 1 |

## v4.1 misses and splits by benchmark category (n = 19)

| | n |
|---|---|
| `mixed` | 5 |
| `structured_csv` | 5 |
| `hard_negative` | 4 |
| `anchor_variant_positive` | 3 |
| `natural_variant_hard_negative` | 1 |
| `natural_variant_positive` | 1 |

## Every span (v4.1 not exact, or v4 not exact)

| id | v4.1 | v4 | v4.1 pieces | v4 pieces | other label (v4.1) | context | prev | next | MAC | stamp |
|---|---|---|---|---|---|---|---|---|---|---|
| bench_az_000028 | missed | missed | `23.37.224.90` | `23.37.224.90` | - | prose | IPv4 | qeyd |  |  |
| bench_az_000056 | split | exact | `[172].[28.6.103]` | `[172.28.6.103]` | - | CSV / table | ipv4;tarix;access_token;saat;yaş | ;11.08.2033;at_bench_1604_buTfJArX4qc0FgRha6Ixef8QlIwlYn;25: |  | y |
| bench_az_000084 | missed | missed | `18.30.67.202` | `18.30.67.202` | - | prose | IPv4 | qeyd |  |  |
| bench_az_000085 | missed | missed | `99.63.17.79` | `99.63.17.79` | - | prose | IPv4 | qeyd |  |  |
| bench_az_000289 | exact | missed | `[1.76.78.96]` | `1.76.78.96` | - | prose | ünvanı | yazılıb; |  |  |
| bench_az_000329 | exact | missed | `[216.101.109.156]` | `216.101.109.156` | - | prose | IPv4 | qeyd |  | y |
| bench_az_000470 | exact | missed | `[192.172.139.74]` | `192.172.139.74` | - | prose | IPv4 | qeyd |  |  |
| bench_az_000489 | exact | missed | `[99.105.222.105]` | `99.105.222.105` | - | prose | IPv4 | qeyd |  | y |
| bench_az_000498 | exact | missed | `[60.92.199.62]` | `60.92.199.62` | - | prose | IPv4 | qeyd |  | y |
| bench_az_000510 | exact | split | `[165.79.175.28]` | `165.79.[175].28` | - | prose | IPv4 | qeyd |  |  |
| bench_az_000531 | split | missed | `[46].[81].[18]1.251` | `46.81.181.251` | - | prose | IPv4 | qeyd |  | y |
| bench_az_000586 | exact | missed | `[99.218.164.91]` | `99.218.164.91` | - | prose | IPv4 | qeyd |  |  |
| bench_az_000602 | exact | missed | `[253.6.123.87]` | `253.6.123.87` | - | prose | unvnı | yazlb; |  |  |
| bench_az_000604 | exact | missed | `[229.4.227.247]` | `229.4.227.247` | - | prose | IP | kimi |  |  |
| bench_az_000659 | split | exact | `[172.18].[0].[63]` | `[172.18.0.63]` | - | CSV / table | Aygül; | ;81;25:81;999 |  | y |
| bench_az_000710 | exact | missed | `[192.76.34.5]` | `192.76.34.5` | - | prose | IPv4 | qeyd | y |  |
| bench_az_000989 | exact | missed | `[99.239.104.232]` | `99.239.104.232` | - | prose | IP | kimi |  | y |
| bench_az_000991 | missed | missed | `14.1.25.76` | `14.1.25.76` | - | prose | tarixçəsində | görünür; | y |  |
| bench_az_001104 | exact | missed | `[97.193.47.65]` | `97.193.47.65` | - | prose | IPv4 | qeyd |  |  |
| bench_az_001137 | exact | split | `[216.89.216.218]` | `216.89[.]2[16].218` | - | prose | IPv4 | qeyd |  |  |
| bench_az_001139 | exact | missed | `[135.190.89.232]` | `135.190.89.232` | - | prose | IPv4 | qeyd |  |  |
| bench_az_001268 | exact | missed | `[191.41.253.251]` | `191.41.253.251` | - | prose | IPv4 | qeyd |  |  |
| bench_az_001304 | exact | missed | `[152.25.66.30]` | `152.25.66.30` | - | prose | IPv4 | qeyd |  |  |
| bench_az_001313 | exact | missed | `[160.45.90.23]` | `160.45.90.23` | - | prose | IPv4 | qeyd |  |  |
| bench_az_001391 | exact | missed | `[154.77.123.94]` | `154.77.123.94` | - | prose | IPv4 | qeyd |  |  |
| bench_az_001399 | exact | split | `[141.91.211.68]` | `141.[91.211].[68]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_001520 | exact | missed | `[73.184.186.217]` | `73.184.186.217` | - | prose | IPv4 | qeyd |  | y |
| bench_az_001566 | exact | split | `[111.130.138.126]` | `111.130[.138].126` | - | prose | IPv4 | qeyd |  |  |
| bench_az_001631 | exact | split | `[42.19.87.229]` | `42[.19.87.229]` | - | prose | ünvanı | yazılıb; |  |  |
| bench_az_001734 | split | exact | `[172].[27.9.12]` | `[172.27.9.12]` | - | CSV / table | ipv4;sürücülük_vəsiqəsi;telefon;e_poçt;ipv4 | ;ZQ702262;+994 |  |  |
| bench_az_001949 | exact | missed | `[226.95.66.246]` | `226.95.66.246` | - | prose | IPv4 | qeyd |  |  |
| bench_az_002012 | missed | missed | `34.20.135.233` | `34.20.135.233` | - | prose | IPv4 | qeyd |  |  |
| bench_az_002069 | exact | missed | `[226.49.85.45]` | `226.49.85.45` | - | prose | IPv4 | qeyd |  |  |
| bench_az_002216 | exact | missed | `[221.93.99.75]` | `221.93.99.75` | - | prose | IPv4 | qeyd |  |  |
| bench_az_002226 | exact | missed | `[40.62.237.72]` | `40.62.237.72` | - | prose | IPv4 | qeyd |  |  |
| bench_az_002281 | missed | missed | `131.15.66.23` | `131.15.66.23` | - | prose | IPv4 | qeyd |  |  |
| bench_az_002419 | exact | missed | `[39.73.179.236]` | `39.73.179.236` | - | prose | IPv4 | qeyd |  |  |
| bench_az_002628 | exact | missed | `[9.231.60.220]` | `9.231.60.220` | - | prose | IPv4 | qeyd | y | y |
| bench_az_002720 | exact | missed | `[126.58.115.45]` | `126.58.115.45` | - | prose | IPv4 | qeyd |  |  |
| bench_az_002884 | exact | missed | `[251.15.53.187]` | `251.15.53.187` | - | prose | ünvanı | yazılıb; |  |  |
| bench_az_002925 | exact | missed | `[108.90.234.45]` | `108.90.234.45` | - | prose | IPv4 | qeyd |  |  |
| bench_az_002983 | exact | missed | `[232.232.14.142]` | `232.232.14.142` | - | prose | IP | kimi |  |  |
| bench_az_002991 | exact | split | `[233.187.128.163]` | `233.[187.128.]163` | - | prose | ünvanı | yazılıb; |  |  |
| bench_az_003036 | missed | missed | `239.228.36.81` | `239.228.36.81` | - | prose | IPv4 | qeyd |  |  |
| bench_az_003089 | exact | split | `[230.63.236.198]` | `230.[63.236].[19]8` | - | prose | IPv4 | qeyd |  |  |
| bench_az_003123 | split | exact | `[172].[21.2.31]` | `[172.21.2.31]` | - | CSV / table | ZX8000528;17.02.2039; | ;user@;999.12.4.1 |  |  |
| bench_az_003162 | missed | missed | `33.61.146.13` | `33.61.146.13` | - | prose | IPv4 | qeyd |  |  |
| bench_az_003169 | exact | split | `[46.111.212.245]` | `46.[111.212.2]45` | - | prose | IPv4 | qeyd |  |  |
| bench_az_003422 | missed | missed | `114.104.25.240` | `114.104.25.240` | - | prose | IPv4 | qeyd |  |  |
| bench_az_003501 | exact | missed | `[184.237.49.153]` | `184.237.49.153` | - | prose | IPv4 | qeyd |  |  |
| bench_az_003524 | exact | split | `[245.214.103.62]` | `245[.214.103.62]` | - | prose | ünvanı | yazılıb; |  |  |
| bench_az_003838 | split | exact | `[172.18].[0.153]` | `[172.18.0.153]` | - | CSV / table | Bikə; | ;at_bench_0153_iS68BGFAdoSiUKf6UyBUNGL4D3v7WF;25:81;999 |  | y |
| bench_az_003933 | exact | missed | `[198.186.38.57]` | `198.186.38.57` | - | prose | IPv4 | qeyd |  |  |
| bench_az_003984 | split | missed | `183.[219.248.]57` | `183.219.248.57` | - | prose | IPv4 | qeyd |  | y |
| bench_az_004113 | missed | missed | `232.108.56.45` | `232.108.56.45` | - | prose | IPv4 | qeyd |  |  |
| bench_az_004142 | exact | split | `[235.93.71.225]` | `235.[93.71.225]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_004152 | exact | missed | `[251.129.204.91]` | `251.129.204.91` | - | prose | kimi | qeyd |  |  |
| bench_az_004178 | split | missed | `244[.87.235.104]` | `244.87.235.104` | - | prose | IPv4 | qeyd |  |  |
| bench_az_004190 | exact | split | `[70.215.81.108]` | `70[.215.81.108]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_004486 | exact | split | `[227.54.236.80]` | `[227.54.236].[80]` | - | prose | IP | kimi |  |  |
| bench_az_004862 | exact | missed | `[184.131.128.20]` | `184.131.128.20` | - | prose | IPv4 | qeyd |  |  |
| bench_az_004893 | exact | split | `[153.196.147.242]` | `[153].196[.147].[24]2` | - | prose | IPv4 | qeyd |  | y |
| bench_az_004894 | split | missed | `161.227.52.[161]` | `161.227.52.161` | - | prose | IPv4 | qeyd |  | y |
| bench_az_004906 | exact | missed | `[232.227.193.211]` | `232.227.193.211` | - | prose | IP | kimi |  |  |

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

