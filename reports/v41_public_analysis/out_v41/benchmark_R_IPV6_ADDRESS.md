# IPV6_ADDRESS: spans v4.1 or v4 does not find exactly

| outcome | v4.1 | v4 |
|---|---|---|
| exact | 439 | 323 |
| split | 7 | 45 |
| covered_inexact | 0 | 0 |
| wrong_label | 0 | 0 |
| missed | 0 | 78 |

## Exact rate per frame, all spans (frames folded: case, letters, 5-letter stems)

| frame | n | v4.1 exact | v4 exact |
|---|---|---|---|
| `serve ipv6- x yazil` | 72 | 71 (99%) | 34 (47%) |
| `logda ipv6 x qeyd olunu` | 71 | 69 (97%) | 20 (28%) |
| `sebek tarix x gorun` | 59 | 58 (98%) | 55 (93%) |
| `ipv6 unvan x kimi goste` | 59 | 58 (98%) | 40 (68%) |
| `ipv6 unvan x-dir` | 38 | 37 (97%) | 35 (92%) |
| `logda x ipv6 unvan` | 36 | 36 (100%) | 34 (94%) |
| `texni murac x unvan elave` | 36 | 36 (100%) | 36 (100%) |
| `ipv6 melum x olara qeyd` | 17 | 17 (100%) | 17 (100%) |
| `ipv6 | x |` | 15 | 15 (100%) | 15 (100%) |
| `"ipv6 " x",` | 11 | 11 (100%) | 11 (100%) |
| `info ipv6= x` | 6 | 6 (100%) | 6 (100%) |
| `texni murac x unvni elave` | 3 | 3 (100%) | 3 (100%) |
| `logda ipv6 x qeyd olunb` | 3 | 3 (100%) | 0 (0%) |
| `logda x ipv6 unvni` | 3 | 3 (100%) | 3 (100%) |
| `logda ipv6 x qeyd olunn` | 3 | 3 (100%) | 2 (67%) |
| `x;13:31;z4hnwp2;az1994;000` | 1 | 0 (0%) | 1 (100%) |
| `x;kobarova;z90002217;https://support.example.com/news/archive/10730;p123` | 1 | 1 (100%) | 1 (100%) |
| `ipv6 unvan x kimi gostr` | 1 | 1 (100%) | 0 (0%) |
| `ipv6 unvni x kimi goste` | 1 | 1 (100%) | 1 (100%) |
| `x;-----begin priva` | 1 | 1 (100%) | 1 (100%) |
| `d2:be x;be:d2:0a:53:99:74;https://support.example.com/news/archive/10070;p123` | 1 | 1 (100%) | 1 (100%) |
| `i̇man kuces x;25:81;999` | 1 | 1 (100%) | 1 (100%) |
| `x;851;zx8000635;903075;12345` | 1 | 1 (100%) | 1 (100%) |
| `ipv6 unvni x-dir` | 1 | 1 (100%) | 0 (0%) |
| `xelilov kuces x;az1994;000` | 1 | 1 (100%) | 1 (100%) |

## v4.1 misses and splits by outcome (n = 7)

| | n |
|---|---|
| `split` | 7 |

## v4.1 misses and splits by cut character (n = 7)

| | n |
|---|---|
| `:` | 4 |
| `: :` | 1 |
| `: 8` | 1 |
| `2 8 2` | 1 |

## v4.1 misses and splits by shape (n = 7)

| | n |
|---|---|
| `:: middle` | 7 |
| `lower` | 7 |
| `prefix 2001:db8` | 7 |

## v4.1 misses and splits by context (n = 7)

| | n |
|---|---|
| `prose` | 6 |
| `CSV / table` | 1 |

## v4.1 misses and splits by frame (n = 7)

| | n |
|---|---|
| `Logda IPv6 X qeyd olunub` | 2 |
| `Server IPv6-si X yazılıb` | 1 |
| `IPv6 ünvanı X-dir` | 1 |
| `X;13:31;Z4HNWP2;AZ1994;000` | 1 |
| `IPv6 ünvanı X kimi göstərilib` | 1 |
| `Şəbəkə tarixçəsində X görünür` | 1 |

## v4.1 misses and splits by previous word (n = 7)

| | n |
|---|---|
| `ünvanı` | 2 |
| `IPv6` | 2 |
| `IPv6-si` | 1 |
| `ipv6;saat;fin_kodu;iban;telefon` | 1 |
| `tarixçəsində` | 1 |

## v4.1 misses and splits by next word (n = 7)

| | n |
|---|---|
| `qeyd` | 2 |
| `yazılıb.` | 1 |
| `-dir.` | 1 |
| `;13:31;Z4HNWP2;AZ1994;000` | 1 |
| `kimi` | 1 |
| `görünür.` | 1 |

## v4.1 misses and splits by MAC in the same document (n = 7)

| | n |
|---|---|
| `False` | 7 |

## v4.1 misses and splits by hh:mm(:ss) stamp in the same document (n = 7)

| | n |
|---|---|
| `False` | 6 |
| `True` | 1 |

## v4.1 misses and splits by v4 outcome on the same span (n = 7)

| | n |
|---|---|
| `missed` | 4 |
| `exact` | 2 |
| `split` | 1 |

## v4.1 misses and splits by doc type (n = 7)

| | n |
|---|---|
| `form` | 2 |
| `crm` | 2 |
| `first_person_chat` | 1 |
| `csv` | 1 |
| `insurance` | 1 |

## v4.1 misses and splits by benchmark category (n = 7)

| | n |
|---|---|
| `hard_negative` | 2 |
| `anchor_variant_positive` | 1 |
| `structured_csv` | 1 |
| `natural_variant_hard_negative` | 1 |
| `anchor_variant_hard_negative` | 1 |
| `mixed` | 1 |

## Every span (v4.1 not exact, or v4 not exact)

| id | v4.1 | v4 | v4.1 pieces | v4 pieces | other label (v4.1) | context | prev | next | MAC | stamp |
|---|---|---|---|---|---|---|---|---|---|---|
| bench_az_000021 | exact | missed | `[fd00::b03c:a2f8]` | `fd00::b03c:a2f8` | - | prose | IPv6 | qeyd |  |  |
| bench_az_000022 | exact | missed | `[2001:db8::13b2]` | `2001:db8::13b2` | - | prose | IPv6 | qeyd |  |  |
| bench_az_000028 | exact | split | `[2001:db8::31de]` | `[2001]:db8::31de` | - | prose | tarixçəsində | görünür. |  |  |
| bench_az_000266 | exact | split | `[2001:db8::6f56]` | `[2001]:db8::6f56` | - | prose | ünvanı | kimi |  |  |
| bench_az_000388 | exact | missed | `[fd00::d4ca:62c0]` | `fd00::d4ca:62c0` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_000444 | exact | missed | `[fd00::ce5b:1f0b]` | `fd00::ce5b:1f0b` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_000466 | exact | split | `[fd00::e8cc:4421]` | `[f]d00[::]e8cc:4421` | - | prose | ünvanı | kimi |  |  |
| bench_az_000497 | exact | missed | `[2001:db8::b02f]` | `2001:db8::b02f` | - | prose | IPv6 | qeyd |  |  |
| bench_az_000549 | split | missed | `[2001]:db8::8489` | `2001:db8::8489` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_000587 | exact | missed | `[2001:db8::cc63]` | `2001:db8::cc63` | - | prose | IPv6 | qeyd |  |  |
| bench_az_000638 | split | split | `[2001]:[db8]::[e6c0]` | `[2001]:[db8:]:e6c0` | - | prose | ünvanı | -dir. |  |  |
| bench_az_000666 | exact | missed | `[2001:db8::ee7c]` | `2001:db8::ee7c` | - | prose | IPv6 | qeyd |  |  |
| bench_az_000712 | exact | split | `[fd00::1cc4:9f7a]` | `[f]d00::1cc4:9f7a` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_000757 | exact | missed | `[2001:db8::1f2a]` | `2001:db8::1f2a` | - | prose | IPv6 | qeyd |  |  |
| bench_az_000802 | exact | missed | `[fd00::37b0:d5]` | `fd00::37b0:d5` | - | prose | IPv6 | qeyd |  | y |
| bench_az_000901 | exact | split | `[fd00::106e:7a04]` | `[f]d[00::106e:7a04]` | - | prose | ünvanı | kimi |  |  |
| bench_az_001027 | exact | missed | `[fd00::39b4:a9c]` | `fd00::39b4:a9c` | - | prose | IPv6 | qeyd |  |  |
| bench_az_001069 | exact | split | `[2001:db8::4257]` | `[2001]:db8::4257` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_001072 | exact | missed | `[fd00::6f2b:2284]` | `fd00::6f2b:2284` | - | prose | IPv6 | qeyd | y |  |
| bench_az_001094 | exact | split | `[2001:db8::fc7]` | `[2001:]db8[::]fc7` | - | prose | Logdan | IPv6 |  | y |
| bench_az_001164 | exact | missed | `[2001:db8::bed8]` | `2001:db8::bed8` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_001175 | exact | missed | `[2001:db8::980b]` | `2001:db8::980b` | - | prose | IPv6 | qeyd |  |  |
| bench_az_001200 | exact | split | `[fd00::1572:d1f7]` | `[f]d00::1572:d1f7` | - | prose | IPv6 | qeyd |  |  |
| bench_az_001209 | exact | missed | `[fd00::7fe0:ef9a]` | `fd00::7fe0:ef9a` | - | prose | ünvanı | kimi |  |  |
| bench_az_001277 | exact | missed | `[2001:db8::8c26]` | `2001:db8::8c26` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_001301 | exact | split | `[fd00::d66c:440e]` | `[f]d00::d66c:440e` | - | prose | ünvanı | kimi |  |  |
| bench_az_001312 | split | exact | `[2001:db8:96c:96d]:[:96c]` | `[2001:db8:96c:96d::96c]` | - | CSV / table | ipv6;saat;fin_kodu;iban;telefon | ;13:31;Z4HNWP2;AZ1994;000 |  | y |
| bench_az_001317 | exact | missed | `[2001:db8::bfd]` | `2001:db8::bfd` | - | prose | IPv6 | qeyd |  |  |
| bench_az_001352 | exact | missed | `[2001:db8::11d]` | `2001:db8::11d` | - | prose | IPv6 | qeyd |  |  |
| bench_az_001367 | exact | split | `[2001:db8::cd4c]` | `[2001]:db8::cd4c` | - | prose | ünvanı | kimi |  |  |
| bench_az_001375 | exact | split | `[fd00::39c6:70b5]` | `[f]d00[::]39c6:70b5` | - | prose | IPv6-si | yazılıb. |  | y |
| bench_az_001423 | exact | split | `[2001:db8::fc51]` | `[2001]:db[8:]:fc51` | - | prose | ünvanı | kimi |  |  |
| bench_az_001453 | exact | missed | `[2001:db8::3509]` | `2001:db8::3509` | - | prose | IPv6 | qeyd |  | y |
| bench_az_001454 | exact | split | `[2001:db8::6d64]` | `[2001]:[db]8[:]:6d64` | - | prose | IPv6 | qeyd |  |  |
| bench_az_001600 | exact | missed | `[fd00::70c:e557]` | `fd00::70c:e557` | - | prose | IPv6 | qeyd |  | y |
| bench_az_001601 | exact | missed | `[2001:db8::926d]` | `2001:db8::926d` | - | prose | IPv6 | qeyd |  |  |
| bench_az_001602 | exact | split | `[2001:db8::a679]` | `[2001]:db8::a679` | - | prose | tarixçəsində | görünür. |  |  |
| bench_az_001639 | exact | split | `[fd00::602f:6b39]` | `f[d00::602f:6b39]` | - | prose | IPv6 | qeyd | y |  |
| bench_az_001720 | split | missed | `[2001:db8:]:7887` | `2001:db8::7887` | - | prose | IPv6 | qeyd |  |  |
| bench_az_001784 | exact | missed | `[fd00::c1fe:18a3]` | `fd00::c1fe:18a3` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_001814 | split | missed | `[2001]:[db]8::1071` | `2001:db8::1071` | - | prose | ünvanı | kimi |  |  |
| bench_az_001844 | exact | missed | `[2001:db8::ed23]` | `2001:db8::ed23` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_001874 | exact | missed | `[fd00::316b:d410]` | `fd00::316b:d410` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_002009 | exact | missed | `[fd00::b100:98aa]` | `fd00::b100:98aa` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002024 | exact | missed | `[fd00::94dd:1d5]` | `fd00::94dd:1d5` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_002043 | exact | missed | `[2001:db8::eb2]` | `2001:db8::eb2` | - | prose | Ipv6 | qeyd |  |  |
| bench_az_002056 | exact | missed | `[2001:db8::fde7]` | `2001:db8::fde7` | - | prose | ünvanı | kimi |  |  |
| bench_az_002086 | exact | missed | `[2001:db8::48b0]` | `2001:db8::48b0` | - | prose | IPv6 | qeyd | y |  |
| bench_az_002124 | exact | split | `[fd00::194f:12ea]` | `[f]d[00::]194[f:12]ea` | - | prose | IPv6-si | yazılıb. |  | y |
| bench_az_002209 | exact | split | `[2001:db8::9823]` | `[2001]:db8[::]9823` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_002245 | exact | missed | `[2001:db8::fc10]` | `2001:db8::fc10` | - | prose | IPv6-si | yazılıb. |  | y |
| bench_az_002260 | exact | missed | `[2001:db8::4344]` | `2001:db8::4344` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002263 | exact | missed | `[2001:db8::cf4]` | `2001:db8::cf4` | - | prose | ünvanı | kimi |  |  |
| bench_az_002303 | exact | missed | `[2001:db8::5eb7]` | `2001:db8::5eb7` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_002424 | exact | split | `[fd00::b970:edd]` | `[f]d00[:]:b970:edd` | - | prose | IPV6 | qeyd |  |  |
| bench_az_002488 | exact | missed | `[2001:db8::c297]` | `2001:db8::c297` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_002525 | exact | missed | `[2001:db8::5d7b]` | `2001:db8::5d7b` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002592 | exact | split | `[fd00::838f:c181]` | `[f]d00[::]838f[:c]181` | - | prose | IPv6-si | yazılıb. |  | y |
| bench_az_002670 | exact | split | `[2001:db8::49cf]` | `[2001:db8::49]cf` | - | prose | ünvanı | kimi |  |  |
| bench_az_002683 | exact | split | `[2001:db8::97e]` | `[2001]:db8[:]:[97]e` | - | prose | Logdan | IPv6 |  | y |
| bench_az_002713 | exact | missed | `[fd00::37cf:4509]` | `fd00::37cf:4509` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002762 | exact | split | `[fd00::2558:cf05]` | `[f]d00::2558:cf05` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_002830 | exact | split | `[fd00::4576:dc3b]` | `[f]d[00::]45[76]:dc[3]b` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_002852 | exact | missed | `[2001:db8::64b5]` | `2001:db8::64b5` | - | prose | IPv6 | qeyd |  | y |
| bench_az_002858 | exact | split | `[fd00::f178:ab1f]` | `[f]d00::f178:ab1f` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002874 | exact | missed | `[2001:db8::86b1]` | `2001:db8::86b1` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002914 | exact | missed | `[2001:db8::cb47]` | `2001:db8::cb47` | - | prose | ünvanı | kimi |  |  |
| bench_az_002920 | exact | missed | `[2001:db8::4e55]` | `2001:db8::4e55` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002953 | exact | split | `[fd00::721a:a8e3]` | `[f]d00[:]:721a:[a]8e3` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_002954 | exact | missed | `[fd00::a5df:2865]` | `fd00::a5df:2865` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002980 | exact | missed | `[2001:db8::e0b5]` | `2001:db8::e0b5` | - | prose | IPv6 | qeyd | y |  |
| bench_az_002981 | exact | missed | `[fd00::c82f:9ffc]` | `fd00::c82f:9ffc` | - | prose | IPv6 | qeyd |  |  |
| bench_az_003035 | exact | split | `[fd00::eac:7d21]` | `[f]d00::eac:7d21` | - | prose | IPv6-si | yazilib. |  |  |
| bench_az_003064 | exact | missed | `[2001:db8::944b]` | `2001:db8::944b` | - | prose | IPv6 | qeyd |  | y |
| bench_az_003068 | exact | missed | `[fd00::4787:fa9]` | `fd00::4787:fa9` | - | prose | ünvanı | kimi |  |  |
| bench_az_003135 | exact | missed | `[fd00::6e77:8e68]` | `fd00::6e77:8e68` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_003165 | exact | missed | `[2001:db8::6f30]` | `2001:db8::6f30` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_003272 | exact | split | `[2001:db8::3a8d]` | `[2001]:db8::3a8d` | - | prose | unvnı | -dir. |  |  |
| bench_az_003285 | exact | split | `[2001:db8::3517]` | `[2001]:db8::3517` | - | prose | IPv6 | qeyd |  |  |
| bench_az_003293 | exact | missed | `[2001:db8::be07]` | `2001:db8::be07` | - | prose | ünvanı | kimi |  | y |
| bench_az_003310 | exact | missed | `[fd00::c057:c750]` | `fd00::c057:c750` | - | prose | IPv6-si | yazılıb. |  | y |
| bench_az_003363 | exact | split | `[2001:db8::1e97]` | `[2001]:[db]8[:]:1e97` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_003378 | exact | missed | `[2001:db8::5f72]` | `2001:db8::5f72` | - | prose | IPv6 | qeyd |  |  |
| bench_az_003383 | exact | missed | `[2001:db8::a085]` | `2001:db8::a085` | - | prose | tarixçəsində | görünür. |  |  |
| bench_az_003445 | exact | split | `[2001:db8::b2ab]` | `[2001]:db8::b2ab` | - | prose | ünvanı | -dir. |  | y |
| bench_az_003455 | exact | split | `[fd00::a947:7cdc]` | `[f]d00::a947:7cdc` | - | prose | ünvanı | kimi |  |  |
| bench_az_003498 | exact | split | `[2001:db8::6b78]` | `[2001]:db8::6b[78]` | - | prose | ünvanı | kimi |  |  |
| bench_az_003582 | exact | split | `[fd00::1cf4:4953]` | `[f]d00::1cf4:4953` | - | prose | IPv6 | qeyd |  |  |
| bench_az_003583 | exact | missed | `[2001:db8::e462]` | `2001:db8::e462` | - | prose | IPv6 | qeyd |  |  |
| bench_az_003631 | exact | missed | `[fd00::f2e2:f061]` | `fd00::f2e2:f061` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_003702 | exact | missed | `[2001:db8::8b0d]` | `2001:db8::8b0d` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_003853 | exact | missed | `[fd00::6c92:6b9d]` | `fd00::6c92:6b9d` | - | prose | IPv6-si | yazilb. |  |  |
| bench_az_003896 | exact | missed | `[fd00::f810:dc8a]` | `fd00::f810:dc8a` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_003963 | exact | split | `[2001:db8::eff5]` | `[2001]:db8::eff5` | - | prose | ünvanı | kimi |  |  |
| bench_az_003965 | exact | split | `[2001:db8::b60a]` | `[2001]:db8::b60a` | - | prose | tarixçəsində | gorunr. |  |  |
| bench_az_003970 | exact | missed | `[2001:db8::5ac9]` | `2001:db8::5ac9` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004028 | exact | split | `[2001:db8::70de]` | `[2001]:db8[:]:70de` | - | prose | ünvanı | kimi |  |  |
| bench_az_004046 | exact | split | `[2001:db8::611b]` | `[2001]:[db8:]:611b` | - | prose | ünvanı | -dir. |  |  |
| bench_az_004051 | exact | split | `[fd00::2131:46c4]` | `[f]d00[::]2131:[46]c4` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004081 | exact | split | `[2001:db8:bf56:447e::e010]` | `[2001:db8:bf56:447e::e]010` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004085 | exact | split | `[2001:db8::eed4]` | `[2001]:db8::eed4` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_004136 | exact | missed | `[2001:db8::f142]` | `2001:db8::f142` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_004188 | exact | missed | `[fd00::71be:2e65]` | `fd00::71be:2e65` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_004287 | exact | missed | `[fd00::ec97:140f]` | `fd00::ec97:140f` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004310 | exact | missed | `[fd00::e953:ff53]` | `fd00::e953:ff53` | - | prose | IPv6 | qeyd |  | y |
| bench_az_004319 | exact | missed | `[2001:db8::d28b]` | `2001:db8::d28b` | - | prose | IPv6-si | yazılıb. |  | y |
| bench_az_004321 | exact | split | `[2001:db8::1eb3]` | `[2001:db8::1eb]3` | - | prose | ünvanı | kimi |  |  |
| bench_az_004332 | exact | missed | `[2001:db8::feb3]` | `2001:db8::feb3` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004339 | exact | missed | `[2001:db8::f9ac]` | `2001:db8::f9ac` | - | prose | IPv6-si | yazılıb. |  | y |
| bench_az_004353 | exact | split | `[2001:db8::17dd]` | `[2001]:db8::17dd` | - | prose | IPv6-si | yazilib. |  |  |
| bench_az_004452 | exact | split | `[fd00::a3ec:f962]` | `[f]d00[::]a3[ec:f]962` | - | prose | IPv6 | qeyd |  | y |
| bench_az_004454 | exact | missed | `[2001:db8::f6d2]` | `2001:db8::f6d2` | - | prose | IPv6 | qeyd | y |  |
| bench_az_004539 | exact | split | `[2001:db8::fd4d]` | `[2001]:db8::fd4d` | - | prose | ünvanı | kimi |  |  |
| bench_az_004556 | split | exact | `[2001]:db8::d4b` | `[2001:db8::d4b]` | - | prose | tarixçəsində | görünür. |  |  |
| bench_az_004675 | exact | missed | `[fd00::54cd:6eaa]` | `fd00::54cd:6eaa` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_004680 | exact | missed | `[2001:db8::6f92]` | `2001:db8::6f92` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004707 | exact | missed | `[2001:db8::3b2a]` | `2001:db8::3b2a` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004735 | exact | missed | `[fd00::7e7c:3556]` | `fd00::7e7c:3556` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004771 | exact | missed | `[2001:db8::6428]` | `2001:db8::6428` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004802 | exact | missed | `[2001:db8::c0aa]` | `2001:db8::c0aa` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004810 | exact | missed | `[fd00::8a6d:99ac]` | `fd00::8a6d:99ac` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004855 | exact | missed | `[2001:db8::a488]` | `2001:db8::a488` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_004950 | exact | missed | `[2001:db8::36e]` | `2001:db8::36e` | - | prose | IPv6 | qeyd |  | y |
| bench_az_004966 | split | missed | `2001[:db]8[::d]28d` | `2001:db8::d28d` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004969 | exact | missed | `[2001:db8::e79f]` | `2001:db8::e79f` | - | prose | IPv6 | qeyd |  |  |

## False alarms of IPV6_ADDRESS (no gold IPV6_ADDRESS under them)

### v4.1: 1 (policy items 0)

| shape | n |
|---|---|
| `:aa:aa:aa · gold here - · decoy benchmark_unique` | 1 |

