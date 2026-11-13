# IPV4_ADDRESS: spans v4 or v3 does not find exactly

| outcome | v4 | v3 |
|---|---|---|
| exact | 365 | 410 |
| split | 13 | 2 |
| covered_inexact | 0 | 0 |
| wrong_label | 0 | 0 |
| missed | 46 | 12 |

## Exact rate per frame, all spans (frames folded: case, letters, 5-letter stems)

| frame | n | v4 exact | v3 exact |
|---|---|---|---|
| `logda ipv4 x qeyd olunu` | 69 | 25 (36%) | 65 (94%) |
| `menbe ip x kimi goste` | 66 | 61 (92%) | 62 (94%) |
| `sebek tarix x gorun` | 64 | 63 (98%) | 63 (98%) |
| `serve unvan x yazil` | 59 | 54 (92%) | 58 (98%) |
| `unvan kimi x qeyd etmis` | 29 | 28 (97%) | 29 (100%) |
| `ipv4 unvan x-dir` | 26 | 26 (100%) | 26 (100%) |
| `texni murac x ip-si elave` | 23 | 23 (100%) | 20 (87%) |
| `logda x ip unvan` | 16 | 16 (100%) | 16 (100%) |
| `ipv4 | x |` | 16 | 16 (100%) | 16 (100%) |
| `"ipv4 " x",` | 16 | 16 (100%) | 16 (100%) |
| `info ipv4= x` | 13 | 13 (100%) | 13 (100%) |
| `ipv4 melum x olara qeyd` | 8 | 8 (100%) | 8 (100%) |
| `logda x ip unvni` | 2 | 2 (100%) | 2 (100%) |
| `logda ipv4 x qeyd olunb` | 2 | 0 (0%) | 2 (100%) |
| `menbe ip x kimi gostr` | 2 | 2 (100%) | 2 (100%) |
| `x;11.08.2033;at_bench_1604_butfjarx4qc0fgrha6ixef8qliwlyn;25:81;999` | 1 | 1 (100%) | 1 (100%) |
| `serve unvni x yazlb` | 1 | 0 (0%) | 0 (0%) |
| `x;89994332608139790817;otken;https://support.example.com/news/archive/10370;p123` | 1 | 1 (100%) | 1 (100%) |
| `aygul x;81;25:81;999` | 1 | 1 (100%) | 1 (100%) |
| `x;2367843398;zq701467;abc;-----begin publi` | 1 | 1 (100%) | 1 (100%) |
| `priva key-- x;danaci;https://support.example.com/help/article/10820;p123` | 1 | 1 (100%) | 1 (100%) |
| `x;zq702262;+994 60` | 1 | 1 (100%) | 1 (100%) |
| `zx800 x;+994 60` | 1 | 1 (100%) | 1 (100%) |
| `zx800 x;user@;999.12.4.1` | 1 | 1 (100%) | 1 (100%) |
| `x;120;ebulhesen;abc;-----begin publi` | 1 | 1 (100%) | 1 (100%) |

## v4 misses and splits by outcome (n = 59)

| | n |
|---|---|
| `missed` | 46 |
| `split` | 13 |

## v4 misses and splits by cut character (n = 59)

| | n |
|---|---|
| `1` | 19 |
| `2` | 16 |
| `9` | 6 |
| `1 .` | 3 |
| `4` | 3 |
| `3` | 3 |
| `7` | 2 |
| `6` | 1 |
| `2 2 .` | 1 |
| `2 1` | 1 |
| `2 . 8` | 1 |
| `4 4` | 1 |
| `.` | 1 |
| `. . 2` | 1 |

## v4 misses and splits by shape (n = 59)

| | n |
|---|---|
| `4 parts` | 59 |
| `no one-digit octet` | 53 |
| `1 one-digit octets` | 6 |

## v4 misses and splits by context (n = 59)

| | n |
|---|---|
| `prose` | 59 |

## v4 misses and splits by frame (n = 59)

| | n |
|---|---|
| `Logda IPv4 X qeyd olunub` | 44 |
| `Server ünvanı X yazılıb` | 5 |
| `Mənbə IP X kimi göstərilib` | 3 |
| `Mənbə IP X kimi gosterilib` | 2 |
| `Logda IPv4 X qeyd olunb` | 2 |
| `Server unvnı X yazlb` | 1 |
| `Şəbəkə tarixçəsində X görünür` | 1 |
| `ünvanı kimi X qeyd etmişəm` | 1 |

## v4 misses and splits by previous word (n = 59)

| | n |
|---|---|
| `IPv4` | 46 |
| `ünvanı` | 5 |
| `IP` | 5 |
| `unvnı` | 1 |
| `tarixçəsində` | 1 |
| `kimi` | 1 |

## v4 misses and splits by next word (n = 59)

| | n |
|---|---|
| `qeyd` | 47 |
| `yazılıb;` | 5 |
| `kimi` | 5 |
| `yazlb;` | 1 |
| `görünür;` | 1 |

## v4 misses and splits by MAC in the same document (n = 59)

| | n |
|---|---|
| `False` | 56 |
| `True` | 3 |

## v4 misses and splits by hh:mm(:ss) stamp in the same document (n = 59)

| | n |
|---|---|
| `False` | 49 |
| `True` | 10 |

## v4 misses and splits by v3 outcome on the same span (n = 59)

| | n |
|---|---|
| `exact` | 50 |
| `missed` | 7 |
| `split` | 2 |

## v4 misses and splits by doc type (n = 59)

| | n |
|---|---|
| `email` | 14 |
| `bank_message` | 8 |
| `support_ticket` | 7 |
| `crm` | 7 |
| `form` | 6 |
| `technical_note` | 5 |
| `legal` | 4 |
| `insurance` | 4 |
| `report` | 3 |
| `first_person_form` | 1 |

## v4 misses and splits by benchmark category (n = 59)

| | n |
|---|---|
| `mixed` | 18 |
| `hard_negative` | 12 |
| `anchor_variant_hard_negative` | 7 |
| `positive_control` | 7 |
| `anchor_variant_positive` | 6 |
| `natural_variant_hard_negative` | 5 |
| `natural_variant_positive` | 4 |

## Every span (v4 not exact, or v3 not exact)

| id | v4 | v3 | v4 pieces | v3 pieces | other label (v4) | context | prev | next | MAC | stamp |
|---|---|---|---|---|---|---|---|---|---|---|
| bench_az_000028 | missed | exact | `23.37.224.90` | `[23.37.224.90]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_000084 | missed | exact | `18.30.67.202` | `[18.30.67.202]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_000085 | missed | exact | `99.63.17.79` | `[99.63.17.79]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_000219 | exact | missed | `[8.48.73.245]` | `8.48.73.245` | - | prose | IP | kimi |  |  |
| bench_az_000289 | missed | exact | `1.76.78.96` | `[1.76.78.96]` | - | prose | ünvanı | yazılıb; |  |  |
| bench_az_000329 | missed | exact | `216.101.109.156` | `[216.101.109.156]` | - | prose | IPv4 | qeyd |  | y |
| bench_az_000470 | missed | exact | `192.172.139.74` | `[192.172.139.74]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_000489 | missed | exact | `99.105.222.105` | `[99.105.222.105]` | - | prose | IPv4 | qeyd |  | y |
| bench_az_000498 | missed | exact | `60.92.199.62` | `[60.92.199.62]` | - | prose | IPv4 | qeyd |  | y |
| bench_az_000510 | split | exact | `165.79.[175].28` | `[165.79.175.28]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_000531 | missed | exact | `46.81.181.251` | `[46.81.181.251]` | - | prose | IPv4 | qeyd |  | y |
| bench_az_000586 | missed | exact | `99.218.164.91` | `[99.218.164.91]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_000602 | missed | missed | `253.6.123.87` | `253.6.123.87` | - | prose | unvnı | yazlb; |  |  |
| bench_az_000604 | missed | exact | `229.4.227.247` | `[229.4.227.247]` | - | prose | IP | kimi |  |  |
| bench_az_000710 | missed | exact | `192.76.34.5` | `[192.76.34.5]` | - | prose | IPv4 | qeyd | y |  |
| bench_az_000989 | missed | exact | `99.239.104.232` | `[99.239.104.232]` | - | prose | IP | kimi |  | y |
| bench_az_000991 | missed | missed | `14.1.25.76` | `14.1.25.76` | - | prose | tarixçəsində | görünür; | y |  |
| bench_az_001104 | missed | exact | `97.193.47.65` | `[97.193.47.65]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_001137 | split | exact | `216.89[.]2[16].218` | `[216.89.216.218]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_001139 | missed | exact | `135.190.89.232` | `[135.190.89.232]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_001264 | exact | missed | `[238.165.89.32]` | `238.165.89.32` | - | prose | müraciətə | IP-sini |  |  |
| bench_az_001268 | missed | exact | `191.41.253.251` | `[191.41.253.251]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_001304 | missed | exact | `152.25.66.30` | `[152.25.66.30]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_001313 | missed | exact | `160.45.90.23` | `[160.45.90.23]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_001391 | missed | exact | `154.77.123.94` | `[154.77.123.94]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_001399 | split | exact | `141.[91.211].[68]` | `[141.91.211.68]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_001520 | missed | exact | `73.184.186.217` | `[73.184.186.217]` | - | prose | IPv4 | qeyd |  | y |
| bench_az_001566 | split | exact | `111.130[.138].126` | `[111.130.138.126]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_001631 | split | exact | `42[.19.87.229]` | `[42.19.87.229]` | - | prose | ünvanı | yazılıb; |  |  |
| bench_az_001949 | missed | exact | `226.95.66.246` | `[226.95.66.246]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_002012 | missed | exact | `34.20.135.233` | `[34.20.135.233]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_002069 | missed | exact | `226.49.85.45` | `[226.49.85.45]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_002216 | missed | exact | `221.93.99.75` | `[221.93.99.75]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_002226 | missed | exact | `40.62.237.72` | `[40.62.237.72]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_002281 | missed | exact | `131.15.66.23` | `[131.15.66.23]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_002419 | missed | exact | `39.73.179.236` | `[39.73.179.236]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_002628 | missed | exact | `9.231.60.220` | `[9.231.60.220]` | - | prose | IPv4 | qeyd | y | y |
| bench_az_002720 | missed | exact | `126.58.115.45` | `[126.58.115.45]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_002884 | missed | missed | `251.15.53.187` | `251.15.53.187` | - | prose | ünvanı | yazılıb; |  |  |
| bench_az_002925 | missed | exact | `108.90.234.45` | `[108.90.234.45]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_002983 | missed | missed | `232.232.14.142` | `232.232.14.142` | - | prose | IP | kimi |  |  |
| bench_az_002991 | split | exact | `233.[187.128.]163` | `[233.187.128.163]` | - | prose | ünvanı | yazılıb; |  |  |
| bench_az_003036 | missed | missed | `239.228.36.81` | `239.228.36.81` | - | prose | IPv4 | qeyd |  |  |
| bench_az_003089 | split | exact | `230.[63.236].[19]8` | `[230.63.236.198]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_003099 | exact | missed | `[238.5.151.246]` | `238.5.151.246` | - | prose | müraciətə | IP-sini |  |  |
| bench_az_003162 | missed | split | `33.61.146.13` | `33.[61.146].13` | - | prose | IPv4 | qeyd |  |  |
| bench_az_003169 | split | exact | `46.[111.212.2]45` | `[46.111.212.245]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_003422 | missed | exact | `114.104.25.240` | `[114.104.25.240]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_003501 | missed | exact | `184.237.49.153` | `[184.237.49.153]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_003511 | exact | missed | `[241.218.100.238]` | `241.218.100.238` | - | prose | müraciətə | IP-sini |  |  |
| bench_az_003524 | split | exact | `245[.214.103.62]` | `[245.214.103.62]` | - | prose | ünvanı | yazılıb; |  |  |
| bench_az_003754 | exact | missed | `[237.142.86.154]` | `237.142.86.154` | - | prose | IP | kimi |  |  |
| bench_az_003933 | missed | exact | `198.186.38.57` | `[198.186.38.57]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_003984 | missed | exact | `183.219.248.57` | `[183.219.248.57]` | - | prose | IPv4 | qeyd |  | y |
| bench_az_004113 | missed | missed | `232.108.56.45` | `232.108.56.45` | - | prose | IPv4 | qeyd |  |  |
| bench_az_004142 | split | exact | `235.[93.71.225]` | `[235.93.71.225]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_004152 | missed | exact | `251.129.204.91` | `[251.129.204.91]` | - | prose | kimi | qeyd |  |  |
| bench_az_004178 | missed | split | `244.87.235.104` | `244[.87.235.104]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_004190 | split | exact | `70[.215.81.108]` | `[70.215.81.108]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_004486 | split | exact | `[227.54.236].[80]` | `[227.54.236.80]` | - | prose | IP | kimi |  |  |
| bench_az_004862 | missed | exact | `184.131.128.20` | `[184.131.128.20]` | - | prose | IPv4 | qeyd |  |  |
| bench_az_004893 | split | exact | `[153].196[.147].[24]2` | `[153.196.147.242]` | - | prose | IPv4 | qeyd |  | y |
| bench_az_004894 | missed | exact | `161.227.52.161` | `[161.227.52.161]` | - | prose | IPv4 | qeyd |  | y |
| bench_az_004906 | missed | missed | `232.227.193.211` | `232.227.193.211` | - | prose | IP | kimi |  |  |

## False alarms of IPV4_ADDRESS (no gold IPV4_ADDRESS under them)

### v3: 48 (policy items 0)

| shape | n |
|---|---|
| `999.9.9.9 · gold here - · decoy benchmark_unique` | 17 |
| `9.9.9.9 · gold here - · decoy benchmark_unique` | 12 |
| `.9.9.9 · gold here - · decoy benchmark_unique` | 8 |
| `. · gold here - · decoy benchmark_unique` | 3 |
| `99.9.9 · gold here - · decoy benchmark_unique` | 2 |
| `9.9. · gold here - · decoy benchmark_unique` | 1 |
| `.9.9 · gold here - · decoy benchmark_unique` | 1 |
| `999 · gold here - · decoy benchmark_unique` | 1 |
| `9 · gold here - · decoy benchmark_unique` | 1 |
| `.9. · gold here - · decoy benchmark_unique` | 1 |
| `99.9.9 · gold here - · decoy benchmark_ambiguous` | 1 |

