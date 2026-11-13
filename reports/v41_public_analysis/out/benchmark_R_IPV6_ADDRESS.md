# IPV6_ADDRESS: spans v4 or v3 does not find exactly

| outcome | v4 | v3 |
|---|---|---|
| exact | 323 | 428 |
| split | 45 | 13 |
| covered_inexact | 0 | 0 |
| wrong_label | 0 | 0 |
| missed | 78 | 5 |

## Exact rate per frame, all spans (frames folded: case, letters, 5-letter stems)

| frame | n | v4 exact | v3 exact |
|---|---|---|---|
| `serve ipv6- x yazil` | 72 | 34 (47%) | 70 (97%) |
| `logda ipv6 x qeyd olunu` | 71 | 20 (28%) | 56 (79%) |
| `sebek tarix x gorun` | 59 | 55 (93%) | 59 (100%) |
| `ipv6 unvan x kimi goste` | 59 | 40 (68%) | 58 (98%) |
| `ipv6 unvan x-dir` | 38 | 35 (92%) | 38 (100%) |
| `logda x ipv6 unvan` | 36 | 34 (94%) | 36 (100%) |
| `texni murac x unvan elave` | 36 | 36 (100%) | 36 (100%) |
| `ipv6 melum x olara qeyd` | 17 | 17 (100%) | 17 (100%) |
| `ipv6 | x |` | 15 | 15 (100%) | 15 (100%) |
| `"ipv6 " x",` | 11 | 11 (100%) | 11 (100%) |
| `info ipv6= x` | 6 | 6 (100%) | 6 (100%) |
| `texni murac x unvni elave` | 3 | 3 (100%) | 3 (100%) |
| `logda ipv6 x qeyd olunb` | 3 | 0 (0%) | 3 (100%) |
| `logda x ipv6 unvni` | 3 | 3 (100%) | 3 (100%) |
| `logda ipv6 x qeyd olunn` | 3 | 2 (67%) | 3 (100%) |
| `x;13:31;z4hnwp2;az1994;000` | 1 | 1 (100%) | 1 (100%) |
| `x;kobarova;z90002217;https://support.example.com/news/archive/10730;p123` | 1 | 1 (100%) | 1 (100%) |
| `ipv6 unvan x kimi gostr` | 1 | 0 (0%) | 1 (100%) |
| `ipv6 unvni x kimi goste` | 1 | 1 (100%) | 1 (100%) |
| `x;-----begin priva` | 1 | 1 (100%) | 1 (100%) |
| `d2:be x;be:d2:0a:53:99:74;https://support.example.com/news/archive/10070;p123` | 1 | 1 (100%) | 1 (100%) |
| `i̇man kuces x;25:81;999` | 1 | 1 (100%) | 1 (100%) |
| `x;851;zx8000635;903075;12345` | 1 | 1 (100%) | 1 (100%) |
| `ipv6 unvni x-dir` | 1 | 0 (0%) | 1 (100%) |
| `xelilov kuces x;az1994;000` | 1 | 1 (100%) | 1 (100%) |

## v4 misses and splits by outcome (n = 123)

| | n |
|---|---|
| `missed` | 78 |
| `split` | 45 |

## v4 misses and splits by cut character (n = 123)

| | n |
|---|---|
| `2` | 51 |
| `f` | 28 |
| `:` | 14 |
| `d` | 9 |
| `: :` | 4 |
| `: 8 :` | 2 |
| `d e` | 1 |
| `d f` | 1 |
| `d 3` | 1 |
| `d 1 e` | 1 |
| `: 9` | 1 |
| `d :` | 1 |
| `d 8 1` | 1 |
| `c` | 1 |
| `: : e` | 1 |
| `d 4 : b` | 1 |
| `d : 8` | 1 |
| `d 2 c` | 1 |
| `0` | 1 |
| `3` | 1 |
| `d a 9` | 1 |

## v4 misses and splits by shape (n = 123)

| | n |
|---|---|
| `:: middle` | 123 |
| `lower` | 123 |
| `prefix 2001:db8` | 77 |
| `prefix fd/fc` | 46 |

## v4 misses and splits by context (n = 123)

| | n |
|---|---|
| `prose` | 123 |

## v4 misses and splits by frame (n = 123)

| | n |
|---|---|
| `Logda IPv6 X qeyd olunub` | 49 |
| `Server IPv6-si X yazılıb` | 35 |
| `IPv6 ünvanı X kimi göstərilib` | 17 |
| `Şəbəkə tarixçəsində X görünür` | 3 |
| `Logda IPv6 X qeyd olunb` | 3 |
| `IPv6 ünvanı X-dir` | 3 |
| `Logdan X IPv6 ünvanını` | 2 |
| `IPv6 ünvanı X kimi gosterilib` | 2 |
| `Server IPv6-si X yazilib` | 2 |
| `Logda IPv6 X qeyd olunnub` | 1 |
| `Logda Ipv6 X qeyd olunub` | 1 |
| `IPv6 ünvanı X kimi gostrılıb` | 1 |
| `Logda IPV6 X qeyd olunub` | 1 |
| `IPv6 unvnı X-dir` | 1 |
| `Server IPv6-si X yazilb` | 1 |
| `Şəbəkə tarixçəsində X gorunr` | 1 |

## v4 misses and splits by previous word (n = 123)

| | n |
|---|---|
| `IPv6` | 53 |
| `IPv6-si` | 38 |
| `ünvanı` | 23 |
| `tarixçəsində` | 4 |
| `Logdan` | 2 |
| `Ipv6` | 1 |
| `IPV6` | 1 |
| `unvnı` | 1 |

## v4 misses and splits by next word (n = 123)

| | n |
|---|---|
| `qeyd` | 55 |
| `yazılıb.` | 35 |
| `kimi` | 20 |
| `-dir.` | 4 |
| `görünür.` | 3 |
| `IPv6` | 2 |
| `yazilib.` | 2 |
| `yazilb.` | 1 |
| `gorunr.` | 1 |

## v4 misses and splits by MAC in the same document (n = 123)

| | n |
|---|---|
| `False` | 118 |
| `True` | 5 |

## v4 misses and splits by hh:mm(:ss) stamp in the same document (n = 123)

| | n |
|---|---|
| `False` | 104 |
| `True` | 19 |

## v4 misses and splits by v3 outcome on the same span (n = 123)

| | n |
|---|---|
| `exact` | 106 |
| `split` | 12 |
| `missed` | 5 |

## v4 misses and splits by doc type (n = 123)

| | n |
|---|---|
| `form` | 18 |
| `technical_note` | 17 |
| `legal` | 14 |
| `support_ticket` | 13 |
| `report` | 13 |
| `crm` | 13 |
| `insurance` | 11 |
| `email` | 9 |
| `bank_message` | 9 |
| `first_person_chat` | 3 |
| `first_person_email` | 2 |
| `first_person_form` | 1 |

## v4 misses and splits by benchmark category (n = 123)

| | n |
|---|---|
| `mixed` | 37 |
| `natural_variant_positive` | 24 |
| `hard_negative` | 20 |
| `natural_variant_hard_negative` | 17 |
| `anchor_variant_positive` | 12 |
| `anchor_variant_hard_negative` | 7 |
| `positive_control` | 5 |
| `corrected_hard_negative` | 1 |

## Every span (v4 not exact, or v3 not exact)

| id | v4 | v3 | v4 pieces | v3 pieces | other label (v4) | context | prev | next | MAC | stamp |
|---|---|---|---|---|---|---|---|---|---|---|
| bench_az_000021 | missed | exact | `fd00::b03c:a2f8` | `[fd00::b03c:a2f8]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_000022 | missed | missed | `2001:db8::13b2` | `2001:db8::13b2` | - | prose | IPv6 | qeyd |  |  |
| bench_az_000028 | split | exact | `[2001]:db8::31de` | `[2001:db8::31de]` | - | prose | tarixçəsində | görünür. |  |  |
| bench_az_000266 | split | exact | `[2001]:db8::6f56` | `[2001:db8::6f56]` | - | prose | ünvanı | kimi |  |  |
| bench_az_000388 | missed | exact | `fd00::d4ca:62c0` | `[fd00::d4ca:62c0]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_000444 | missed | exact | `fd00::ce5b:1f0b` | `[fd00::ce5b:1f0b]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_000466 | split | exact | `[f]d00[::]e8cc:4421` | `[fd00::e8cc:4421]` | - | prose | ünvanı | kimi |  |  |
| bench_az_000497 | missed | exact | `2001:db8::b02f` | `[2001:db8::b02f]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_000549 | missed | exact | `2001:db8::8489` | `[2001:db8::8489]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_000587 | missed | split | `2001:db8::cc63` | `[2001:db]8::[cc63]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_000638 | split | exact | `[2001]:[db8:]:e6c0` | `[2001:db8::e6c0]` | - | prose | ünvanı | -dir. |  |  |
| bench_az_000666 | missed | exact | `2001:db8::ee7c` | `[2001:db8::ee7c]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_000712 | split | exact | `[f]d00::1cc4:9f7a` | `[fd00::1cc4:9f7a]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_000757 | missed | exact | `2001:db8::1f2a` | `[2001:db8::1f2a]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_000802 | missed | exact | `fd00::37b0:d5` | `[fd00::37b0:d5]` | - | prose | IPv6 | qeyd |  | y |
| bench_az_000901 | split | exact | `[f]d[00::106e:7a04]` | `[fd00::106e:7a04]` | - | prose | ünvanı | kimi |  |  |
| bench_az_001027 | missed | exact | `fd00::39b4:a9c` | `[fd00::39b4:a9c]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_001069 | split | exact | `[2001]:db8::4257` | `[2001:db8::4257]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_001072 | missed | exact | `fd00::6f2b:2284` | `[fd00::6f2b:2284]` | - | prose | IPv6 | qeyd | y |  |
| bench_az_001094 | split | exact | `[2001:]db8[::]fc7` | `[2001:db8::fc7]` | - | prose | Logdan | IPv6 |  | y |
| bench_az_001164 | missed | exact | `2001:db8::bed8` | `[2001:db8::bed8]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_001175 | missed | split | `2001:db8::980b` | `[2001:db]8::[980b]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_001200 | split | exact | `[f]d00::1572:d1f7` | `[fd00::1572:d1f7]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_001209 | missed | exact | `fd00::7fe0:ef9a` | `[fd00::7fe0:ef9a]` | - | prose | ünvanı | kimi |  |  |
| bench_az_001277 | missed | exact | `2001:db8::8c26` | `[2001:db8::8c26]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_001301 | split | exact | `[f]d00::d66c:440e` | `[fd00::d66c:440e]` | - | prose | ünvanı | kimi |  |  |
| bench_az_001317 | missed | split | `2001:db8::bfd` | `[2001]:[db]8::[bfd]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_001352 | missed | missed | `2001:db8::11d` | `2001:db8::11d` | - | prose | IPv6 | qeyd |  |  |
| bench_az_001367 | split | exact | `[2001]:db8::cd4c` | `[2001:db8::cd4c]` | - | prose | ünvanı | kimi |  |  |
| bench_az_001375 | split | exact | `[f]d00[::]39c6:70b5` | `[fd00::39c6:70b5]` | - | prose | IPv6-si | yazılıb. |  | y |
| bench_az_001423 | split | exact | `[2001]:db[8:]:fc51` | `[2001:db8::fc51]` | - | prose | ünvanı | kimi |  |  |
| bench_az_001453 | missed | exact | `2001:db8::3509` | `[2001:db8::3509]` | - | prose | IPv6 | qeyd |  | y |
| bench_az_001454 | split | exact | `[2001]:[db]8[:]:6d64` | `[2001:db8::6d64]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_001600 | missed | exact | `fd00::70c:e557` | `[fd00::70c:e557]` | - | prose | IPv6 | qeyd |  | y |
| bench_az_001601 | missed | missed | `2001:db8::926d` | `2001:db8::926d` | - | prose | IPv6 | qeyd |  |  |
| bench_az_001602 | split | exact | `[2001]:db8::a679` | `[2001:db8::a679]` | - | prose | tarixçəsində | görünür. |  |  |
| bench_az_001639 | split | exact | `f[d00::602f:6b39]` | `[fd00::602f:6b39]` | - | prose | IPv6 | qeyd | y |  |
| bench_az_001720 | missed | missed | `2001:db8::7887` | `2001:db8::7887` | - | prose | IPv6 | qeyd |  |  |
| bench_az_001784 | missed | exact | `fd00::c1fe:18a3` | `[fd00::c1fe:18a3]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_001814 | missed | split | `2001:db8::1071` | `[2001]:[db]8::[10]71` | - | prose | ünvanı | kimi |  |  |
| bench_az_001844 | missed | exact | `2001:db8::ed23` | `[2001:db8::ed23]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_001874 | missed | exact | `fd00::316b:d410` | `[fd00::316b:d410]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_002009 | missed | exact | `fd00::b100:98aa` | `[fd00::b100:98aa]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002024 | missed | exact | `fd00::94dd:1d5` | `[fd00::94dd:1d5]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_002043 | missed | exact | `2001:db8::eb2` | `[2001:db8::eb2]` | - | prose | Ipv6 | qeyd |  |  |
| bench_az_002056 | missed | exact | `2001:db8::fde7` | `[2001:db8::fde7]` | - | prose | ünvanı | kimi |  |  |
| bench_az_002086 | missed | exact | `2001:db8::48b0` | `[2001:db8::48b0]` | - | prose | IPv6 | qeyd | y |  |
| bench_az_002124 | split | exact | `[f]d[00::]194[f:12]ea` | `[fd00::194f:12ea]` | - | prose | IPv6-si | yazılıb. |  | y |
| bench_az_002209 | split | exact | `[2001]:db8[::]9823` | `[2001:db8::9823]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_002245 | missed | exact | `2001:db8::fc10` | `[2001:db8::fc10]` | - | prose | IPv6-si | yazılıb. |  | y |
| bench_az_002260 | missed | exact | `2001:db8::4344` | `[2001:db8::4344]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002263 | missed | exact | `2001:db8::cf4` | `[2001:db8::cf4]` | - | prose | ünvanı | kimi |  |  |
| bench_az_002303 | missed | exact | `2001:db8::5eb7` | `[2001:db8::5eb7]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_002424 | split | exact | `[f]d00[:]:b970:edd` | `[fd00::b970:edd]` | - | prose | IPV6 | qeyd |  |  |
| bench_az_002488 | missed | exact | `2001:db8::c297` | `[2001:db8::c297]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_002525 | missed | split | `2001:db8::5d7b` | `[2001]:[db]8::5[d]7b` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002592 | split | exact | `[f]d00[::]838f[:c]181` | `[fd00::838f:c181]` | - | prose | IPv6-si | yazılıb. |  | y |
| bench_az_002670 | split | exact | `[2001:db8::49]cf` | `[2001:db8::49cf]` | - | prose | ünvanı | kimi |  |  |
| bench_az_002683 | split | exact | `[2001]:db8[:]:[97]e` | `[2001:db8::97e]` | - | prose | Logdan | IPv6 |  | y |
| bench_az_002713 | missed | exact | `fd00::37cf:4509` | `[fd00::37cf:4509]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002762 | split | exact | `[f]d00::2558:cf05` | `[fd00::2558:cf05]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_002830 | split | exact | `[f]d[00::]45[76]:dc[3]b` | `[fd00::4576:dc3b]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_002852 | missed | exact | `2001:db8::64b5` | `[2001:db8::64b5]` | - | prose | IPv6 | qeyd |  | y |
| bench_az_002858 | split | exact | `[f]d00::f178:ab1f` | `[fd00::f178:ab1f]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002874 | missed | split | `2001:db8::86b1` | `[2001]:[db]8::[86b]1` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002914 | missed | exact | `2001:db8::cb47` | `[2001:db8::cb47]` | - | prose | ünvanı | kimi |  |  |
| bench_az_002920 | missed | exact | `2001:db8::4e55` | `[2001:db8::4e55]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002953 | split | exact | `[f]d00[:]:721a:[a]8e3` | `[fd00::721a:a8e3]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_002954 | missed | exact | `fd00::a5df:2865` | `[fd00::a5df:2865]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002980 | missed | exact | `2001:db8::e0b5` | `[2001:db8::e0b5]` | - | prose | IPv6 | qeyd | y |  |
| bench_az_002981 | missed | exact | `fd00::c82f:9ffc` | `[fd00::c82f:9ffc]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_003035 | split | exact | `[f]d00::eac:7d21` | `[fd00::eac:7d21]` | - | prose | IPv6-si | yazilib. |  |  |
| bench_az_003064 | missed | exact | `2001:db8::944b` | `[2001:db8::944b]` | - | prose | IPv6 | qeyd |  | y |
| bench_az_003068 | missed | exact | `fd00::4787:fa9` | `[fd00::4787:fa9]` | - | prose | ünvanı | kimi |  |  |
| bench_az_003135 | missed | exact | `fd00::6e77:8e68` | `[fd00::6e77:8e68]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_003165 | missed | exact | `2001:db8::6f30` | `[2001:db8::6f30]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_003272 | split | exact | `[2001]:db8::3a8d` | `[2001:db8::3a8d]` | - | prose | unvnı | -dir. |  |  |
| bench_az_003285 | split | exact | `[2001]:db8::3517` | `[2001:db8::3517]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_003293 | missed | exact | `2001:db8::be07` | `[2001:db8::be07]` | - | prose | ünvanı | kimi |  | y |
| bench_az_003310 | missed | exact | `fd00::c057:c750` | `[fd00::c057:c750]` | - | prose | IPv6-si | yazılıb. |  | y |
| bench_az_003363 | split | exact | `[2001]:[db]8[:]:1e97` | `[2001:db8::1e97]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_003378 | missed | exact | `2001:db8::5f72` | `[2001:db8::5f72]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_003383 | missed | exact | `2001:db8::a085` | `[2001:db8::a085]` | - | prose | tarixçəsində | görünür. |  |  |
| bench_az_003445 | split | exact | `[2001]:db8::b2ab` | `[2001:db8::b2ab]` | - | prose | ünvanı | -dir. |  | y |
| bench_az_003455 | split | exact | `[f]d00::a947:7cdc` | `[fd00::a947:7cdc]` | - | prose | ünvanı | kimi |  |  |
| bench_az_003498 | split | exact | `[2001]:db8::6b[78]` | `[2001:db8::6b78]` | - | prose | ünvanı | kimi |  |  |
| bench_az_003582 | split | exact | `[f]d00::1cf4:4953` | `[fd00::1cf4:4953]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_003583 | missed | exact | `2001:db8::e462` | `[2001:db8::e462]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_003631 | missed | exact | `fd00::f2e2:f061` | `[fd00::f2e2:f061]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_003702 | missed | split | `2001:db8::8b0d` | `[2001:db8]::[8b0d]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_003853 | missed | exact | `fd00::6c92:6b9d` | `[fd00::6c92:6b9d]` | - | prose | IPv6-si | yazilb. |  |  |
| bench_az_003896 | missed | exact | `fd00::f810:dc8a` | `[fd00::f810:dc8a]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_003963 | split | exact | `[2001]:db8::eff5` | `[2001:db8::eff5]` | - | prose | ünvanı | kimi |  |  |
| bench_az_003965 | split | exact | `[2001]:db8::b60a` | `[2001:db8::b60a]` | - | prose | tarixçəsində | gorunr. |  |  |
| bench_az_003970 | missed | missed | `2001:db8::5ac9` | `2001:db8::5ac9` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004028 | split | exact | `[2001]:db8[:]:70de` | `[2001:db8::70de]` | - | prose | ünvanı | kimi |  |  |
| bench_az_004046 | split | exact | `[2001]:[db8:]:611b` | `[2001:db8::611b]` | - | prose | ünvanı | -dir. |  |  |
| bench_az_004051 | split | exact | `[f]d00[::]2131:[46]c4` | `[fd00::2131:46c4]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004081 | split | exact | `[2001:db8:bf56:447e::e]010` | `[2001:db8:bf56:447e::e010]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004085 | split | exact | `[2001]:db8::eed4` | `[2001:db8::eed4]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_004136 | missed | exact | `2001:db8::f142` | `[2001:db8::f142]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_004188 | missed | exact | `fd00::71be:2e65` | `[fd00::71be:2e65]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_004287 | missed | exact | `fd00::ec97:140f` | `[fd00::ec97:140f]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004310 | missed | exact | `fd00::e953:ff53` | `[fd00::e953:ff53]` | - | prose | IPv6 | qeyd |  | y |
| bench_az_004319 | missed | split | `2001:db8::d28b` | `[2001]:[db]8[:]:[d28b]` | - | prose | IPv6-si | yazılıb. |  | y |
| bench_az_004321 | split | exact | `[2001:db8::1eb]3` | `[2001:db8::1eb3]` | - | prose | ünvanı | kimi |  |  |
| bench_az_004332 | missed | split | `2001:db8::feb3` | `[2001]:[db]8::feb3` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004339 | missed | exact | `2001:db8::f9ac` | `[2001:db8::f9ac]` | - | prose | IPv6-si | yazılıb. |  | y |
| bench_az_004353 | split | exact | `[2001]:db8::17dd` | `[2001:db8::17dd]` | - | prose | IPv6-si | yazilib. |  |  |
| bench_az_004452 | split | exact | `[f]d00[::]a3[ec:f]962` | `[fd00::a3ec:f962]` | - | prose | IPv6 | qeyd |  | y |
| bench_az_004454 | missed | exact | `2001:db8::f6d2` | `[2001:db8::f6d2]` | - | prose | IPv6 | qeyd | y |  |
| bench_az_004539 | split | exact | `[2001]:db8::fd4d` | `[2001:db8::fd4d]` | - | prose | ünvanı | kimi |  |  |
| bench_az_004675 | missed | exact | `fd00::54cd:6eaa` | `[fd00::54cd:6eaa]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_004680 | missed | exact | `2001:db8::6f92` | `[2001:db8::6f92]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004707 | missed | exact | `2001:db8::3b2a` | `[2001:db8::3b2a]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004735 | missed | exact | `fd00::7e7c:3556` | `[fd00::7e7c:3556]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004771 | missed | split | `2001:db8::6428` | `[2001]:[db8]::[6428]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004802 | missed | split | `2001:db8::c0aa` | `2001:[db]8::c0aa` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004810 | missed | exact | `fd00::8a6d:99ac` | `[fd00::8a6d:99ac]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004835 | exact | split | `[2001:db8::5712]` | `2001:[db]8::5712` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004855 | missed | exact | `2001:db8::a488` | `[2001:db8::a488]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_004950 | missed | exact | `2001:db8::36e` | `[2001:db8::36e]` | - | prose | IPv6 | qeyd |  | y |
| bench_az_004966 | missed | split | `2001:db8::d28d` | `[2001]:[db]8[::d28d]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004969 | missed | exact | `2001:db8::e79f` | `[2001:db8::e79f]` | - | prose | IPv6 | qeyd |  |  |

## False alarms of IPV6_ADDRESS (no gold IPV6_ADDRESS under them)

