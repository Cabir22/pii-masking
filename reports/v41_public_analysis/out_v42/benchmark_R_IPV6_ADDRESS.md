# IPV6_ADDRESS: spans v4.2 or v4.1 does not find exactly

| outcome | v4.2 | v4.1 |
|---|---|---|
| exact | 286 | 439 |
| split | 31 | 7 |
| covered_inexact | 0 | 0 |
| wrong_label | 0 | 0 |
| missed | 129 | 0 |

## Exact rate per frame, all spans (frames folded: case, letters, 5-letter stems)

| frame | n | v4.2 exact | v4.1 exact |
|---|---|---|---|
| `serve ipv6- x yazil` | 72 | 16 (22%) | 71 (99%) |
| `logda ipv6 x qeyd olunu` | 71 | 8 (11%) | 69 (97%) |
| `sebek tarix x gorun` | 59 | 40 (68%) | 58 (98%) |
| `ipv6 unvan x kimi goste` | 59 | 49 (83%) | 58 (98%) |
| `ipv6 unvan x-dir` | 38 | 35 (92%) | 37 (97%) |
| `logda x ipv6 unvan` | 36 | 35 (97%) | 36 (100%) |
| `texni murac x unvan elave` | 36 | 35 (97%) | 36 (100%) |
| `ipv6 melum x olara qeyd` | 17 | 17 (100%) | 17 (100%) |
| `ipv6 | x |` | 15 | 15 (100%) | 15 (100%) |
| `"ipv6 " x",` | 11 | 11 (100%) | 11 (100%) |
| `info ipv6= x` | 6 | 6 (100%) | 6 (100%) |
| `texni murac x unvni elave` | 3 | 3 (100%) | 3 (100%) |
| `logda ipv6 x qeyd olunb` | 3 | 0 (0%) | 3 (100%) |
| `logda x ipv6 unvni` | 3 | 3 (100%) | 3 (100%) |
| `logda ipv6 x qeyd olunn` | 3 | 1 (33%) | 3 (100%) |
| `x;13:31;z4hnwp2;az1994;000` | 1 | 1 (100%) | 0 (0%) |
| `x;kobarova;z90002217;https://support.example.com/news/archive/10730;p123` | 1 | 1 (100%) | 1 (100%) |
| `ipv6 unvan x kimi gostr` | 1 | 0 (0%) | 1 (100%) |
| `ipv6 unvni x kimi goste` | 1 | 1 (100%) | 1 (100%) |
| `x;-----begin priva` | 1 | 1 (100%) | 1 (100%) |
| `d2:be x;be:d2:0a:53:99:74;https://support.example.com/news/archive/10070;p123` | 1 | 1 (100%) | 1 (100%) |
| `i̇man kuces x;25:81;999` | 1 | 1 (100%) | 1 (100%) |
| `x;851;zx8000635;903075;12345` | 1 | 1 (100%) | 1 (100%) |
| `ipv6 unvni x-dir` | 1 | 0 (0%) | 1 (100%) |
| `xelilov kuces x;az1994;000` | 1 | 1 (100%) | 1 (100%) |

## v4.2 misses and splits by outcome (n = 160)

| | n |
|---|---|
| `missed` | 129 |
| `split` | 31 |

## v4.2 misses and splits by cut character (n = 160)

| | n |
|---|---|
| `2` | 88 |
| `f` | 42 |
| `d` | 11 |
| `:` | 5 |
| `1` | 2 |
| `4` | 1 |
| `8 6` | 1 |
| `3` | 1 |
| `2 d` | 1 |
| `d :` | 1 |
| `: a` | 1 |
| `: d` | 1 |
| `8` | 1 |
| `d : a 1` | 1 |
| `: :` | 1 |
| `8 2` | 1 |
| `d : a` | 1 |

## v4.2 misses and splits by shape (n = 160)

| | n |
|---|---|
| `:: middle` | 160 |
| `lower` | 160 |
| `prefix 2001:db8` | 102 |
| `prefix fd/fc` | 58 |

## v4.2 misses and splits by context (n = 160)

| | n |
|---|---|
| `prose` | 160 |

## v4.2 misses and splits by frame (n = 160)

| | n |
|---|---|
| `Logda IPv6 X qeyd olunub` | 60 |
| `Server IPv6-si X yazılıb` | 49 |
| `Şəbəkə tarixçəsində X görünür` | 17 |
| `IPv6 ünvanı X kimi göstərilib` | 8 |
| `Server IPv6-si X yazilib` | 5 |
| `Logda IPv6 X qeyd olunb` | 3 |
| `IPv6 ünvanı X-dir` | 3 |
| `Logda IPv6 X qeyd olunnub` | 2 |
| `Logda IPV6 X qeyd olunub` | 2 |
| `IPv6 ünvanı X kimi gosterilib` | 2 |
| `Şəbəkə tarixçəsində X gorunr` | 2 |
| `Logda Ipv6 X qeyd olunub` | 1 |
| `IPv6 ünvanı X kimi gostrılıb` | 1 |
| `Server IPV6-si X yazılıb` | 1 |
| `Texniki muracietə X ünvanını əlavə` | 1 |
| `IPv6 unvnı X-dir` | 1 |
| `Server IPv6-si X yazilb` | 1 |
| `Logdan X IPv6 ünvanını` | 1 |

## v4.2 misses and splits by previous word (n = 160)

| | n |
|---|---|
| `IPv6` | 65 |
| `IPv6-si` | 55 |
| `tarixçəsində` | 19 |
| `ünvanı` | 14 |
| `IPV6` | 2 |
| `Ipv6` | 1 |
| `IPV6-si` | 1 |
| `muracietə` | 1 |
| `unvnı` | 1 |
| `Logdan` | 1 |

## v4.2 misses and splits by next word (n = 160)

| | n |
|---|---|
| `qeyd` | 68 |
| `yazılıb.` | 50 |
| `görünür.` | 17 |
| `kimi` | 11 |
| `yazilib.` | 5 |
| `-dir.` | 4 |
| `gorunr.` | 2 |
| `ünvanını` | 1 |
| `yazilb.` | 1 |
| `IPv6` | 1 |

## v4.2 misses and splits by MAC in the same document (n = 160)

| | n |
|---|---|
| `False` | 155 |
| `True` | 5 |

## v4.2 misses and splits by hh:mm(:ss) stamp in the same document (n = 160)

| | n |
|---|---|
| `False` | 136 |
| `True` | 24 |

## v4.2 misses and splits by v4.1 outcome on the same span (n = 160)

| | n |
|---|---|
| `exact` | 154 |
| `split` | 6 |

## v4.2 misses and splits by doc type (n = 160)

| | n |
|---|---|
| `form` | 25 |
| `legal` | 21 |
| `technical_note` | 21 |
| `crm` | 17 |
| `report` | 16 |
| `support_ticket` | 15 |
| `bank_message` | 15 |
| `insurance` | 13 |
| `email` | 11 |
| `first_person_chat` | 2 |
| `first_person_form` | 2 |
| `first_person_email` | 2 |

## v4.2 misses and splits by benchmark category (n = 160)

| | n |
|---|---|
| `mixed` | 42 |
| `natural_variant_positive` | 30 |
| `hard_negative` | 26 |
| `natural_variant_hard_negative` | 21 |
| `anchor_variant_positive` | 17 |
| `positive_control` | 11 |
| `anchor_variant_hard_negative` | 10 |
| `corrected_hard_negative` | 3 |

## Every span (v4.2 not exact, or v4.1 not exact)

| id | v4.2 | v4.1 | v4.2 pieces | v4.1 pieces | other label (v4.2) | context | prev | next | MAC | stamp |
|---|---|---|---|---|---|---|---|---|---|---|
| bench_az_000021 | missed | exact | `fd00::b03c:a2f8` | `[fd00::b03c:a2f8]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_000022 | missed | exact | `2001:db8::13b2` | `[2001:db8::13b2]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_000028 | missed | exact | `2001:db8::31de` | `[2001:db8::31de]` | - | prose | tarixçəsində | görünür. |  |  |
| bench_az_000069 | missed | exact | `fd00::5a22:13e0` | `[fd00::5a22:13e0]` | - | prose | IPv6-si | yazılıb. |  | y |
| bench_az_000085 | missed | exact | `2001:db8::ebb9` | `[2001:db8::ebb9]` | - | prose | tarixçəsində | görünür. |  |  |
| bench_az_000146 | missed | exact | `fd00::f1e3:d002` | `[fd00::f1e3:d002]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_000229 | split | exact | `[2001]:db8::a392` | `[2001:db8::a392]` | - | prose | tarixçəsində | görünür. |  |  |
| bench_az_000247 | split | exact | `[f]d00::5793:d50c` | `[fd00::5793:d50c]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_000278 | split | exact | `[f]d00::c669:ad0f` | `[fd00::c669:ad0f]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_000388 | missed | exact | `fd00::d4ca:62c0` | `[fd00::d4ca:62c0]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_000444 | missed | exact | `fd00::ce5b:1f0b` | `[fd00::ce5b:1f0b]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_000466 | split | exact | `[fd00::e8cc:44]21` | `[fd00::e8cc:4421]` | - | prose | ünvanı | kimi |  |  |
| bench_az_000497 | missed | exact | `2001:db8::b02f` | `[2001:db8::b02f]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_000549 | missed | split | `2001:db8::8489` | `[2001]:db8::8489` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_000587 | missed | exact | `2001:db8::cc63` | `[2001:db8::cc63]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_000611 | split | exact | `[2001:db8:1932:f4a4::9]45d` | `[2001:db8:1932:f4a4::945d]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_000638 | missed | split | `2001:db8::e6c0` | `[2001]:[db8]::[e6c0]` | - | prose | ünvanı | -dir. |  |  |
| bench_az_000666 | missed | exact | `2001:db8::ee7c` | `[2001:db8::ee7c]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_000669 | split | exact | `[2001:db]8::[85]65` | `[2001:db8::8565]` | - | prose | tarixçəsində | görünür. |  |  |
| bench_az_000686 | split | exact | `[f]d00::7311:3e8` | `[fd00::7311:3e8]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_000700 | missed | exact | `2001:db8:4282:1b3d::9a9` | `[2001:db8:4282:1b3d::9a9]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_000712 | missed | exact | `fd00::1cc4:9f7a` | `[fd00::1cc4:9f7a]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_000757 | missed | exact | `2001:db8::1f2a` | `[2001:db8::1f2a]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_000802 | missed | exact | `fd00::37b0:d5` | `[fd00::37b0:d5]` | - | prose | IPv6 | qeyd |  | y |
| bench_az_000969 | missed | exact | `fd00::8f59:9459` | `[fd00::8f59:9459]` | - | prose | IPv6-si | yazılıb. |  | y |
| bench_az_000983 | split | exact | `[f]d00::6f35:ab8d` | `[fd00::6f35:ab8d]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_001027 | missed | exact | `fd00::39b4:a9c` | `[fd00::39b4:a9c]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_001069 | missed | exact | `2001:db8::4257` | `[2001:db8::4257]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_001072 | missed | exact | `fd00::6f2b:2284` | `[fd00::6f2b:2284]` | - | prose | IPv6 | qeyd | y |  |
| bench_az_001098 | missed | exact | `2001:db8:6122:c2a4::f2e` | `[2001:db8:6122:c2a4::f2e]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_001164 | missed | exact | `2001:db8::bed8` | `[2001:db8::bed8]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_001175 | missed | exact | `2001:db8::980b` | `[2001:db8::980b]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_001200 | missed | exact | `fd00::1572:d1f7` | `[fd00::1572:d1f7]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_001277 | missed | exact | `2001:db8::8c26` | `[2001:db8::8c26]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_001312 | exact | split | `[2001:db8:96c:96d::96c]` | `[2001:db8:96c:96d]:[:96c]` | - | CSV / table | ipv6;saat;fin_kodu;iban;telefon | ;13:31;Z4HNWP2;AZ1994;000 |  | y |
| bench_az_001317 | missed | exact | `2001:db8::bfd` | `[2001:db8::bfd]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_001319 | missed | exact | `fd00::e498:a687` | `[fd00::e498:a687]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_001352 | missed | exact | `2001:db8::11d` | `[2001:db8::11d]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_001375 | missed | exact | `fd00::39c6:70b5` | `[fd00::39c6:70b5]` | - | prose | IPv6-si | yazılıb. |  | y |
| bench_az_001423 | missed | exact | `2001:db8::fc51` | `[2001:db8::fc51]` | - | prose | ünvanı | kimi |  |  |
| bench_az_001453 | missed | exact | `2001:db8::3509` | `[2001:db8::3509]` | - | prose | IPv6 | qeyd |  | y |
| bench_az_001454 | missed | exact | `2001:db8::6d64` | `[2001:db8::6d64]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_001561 | missed | exact | `2001:db8::5649` | `[2001:db8::5649]` | - | prose | tarixçəsində | görünür. |  | y |
| bench_az_001600 | missed | exact | `fd00::70c:e557` | `[fd00::70c:e557]` | - | prose | IPv6 | qeyd |  | y |
| bench_az_001601 | missed | exact | `2001:db8::926d` | `[2001:db8::926d]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_001602 | missed | exact | `2001:db8::a679` | `[2001:db8::a679]` | - | prose | tarixçəsində | görünür. |  |  |
| bench_az_001720 | missed | split | `2001:db8::7887` | `[2001:db8:]:7887` | - | prose | IPv6 | qeyd |  |  |
| bench_az_001784 | split | exact | `[fd00::c1fe:18a]3` | `[fd00::c1fe:18a3]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_001814 | split | split | `2001[:]db8::1071` | `[2001]:[db]8::1071` | - | prose | ünvanı | kimi |  |  |
| bench_az_001828 | split | exact | `[2001]:db8::416b` | `[2001:db8::416b]` | - | prose | ünvanı | -dir. |  |  |
| bench_az_001844 | missed | exact | `2001:db8::ed23` | `[2001:db8::ed23]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_001874 | missed | exact | `fd00::316b:d410` | `[fd00::316b:d410]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_001960 | split | exact | `[f]d[00:]:[de87:3e37]` | `[fd00::de87:3e37]` | - | prose | IPv6 | qeyd |  | y |
| bench_az_002009 | missed | exact | `fd00::b100:98aa` | `[fd00::b100:98aa]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002024 | missed | exact | `fd00::94dd:1d5` | `[fd00::94dd:1d5]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_002043 | missed | exact | `2001:db8::eb2` | `[2001:db8::eb2]` | - | prose | Ipv6 | qeyd |  |  |
| bench_az_002056 | missed | exact | `2001:db8::fde7` | `[2001:db8::fde7]` | - | prose | ünvanı | kimi |  |  |
| bench_az_002086 | missed | exact | `2001:db8::48b0` | `[2001:db8::48b0]` | - | prose | IPv6 | qeyd | y |  |
| bench_az_002124 | split | exact | `[fd00:]:194f[:12e]a` | `[fd00::194f:12ea]` | - | prose | IPv6-si | yazılıb. |  | y |
| bench_az_002172 | split | exact | `[2001:db8:3]151[:c56b::444e]` | `[2001:db8:3151:c56b::444e]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002209 | missed | exact | `2001:db8::9823` | `[2001:db8::9823]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_002218 | missed | exact | `fd00::bbb8:314e` | `[fd00::bbb8:314e]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002245 | missed | exact | `2001:db8::fc10` | `[2001:db8::fc10]` | - | prose | IPv6-si | yazılıb. |  | y |
| bench_az_002260 | missed | exact | `2001:db8::4344` | `[2001:db8::4344]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002263 | missed | exact | `2001:db8::cf4` | `[2001:db8::cf4]` | - | prose | ünvanı | kimi |  |  |
| bench_az_002303 | missed | exact | `2001:db8::5eb7` | `[2001:db8::5eb7]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_002359 | missed | exact | `fd00::60ec:677b` | `[fd00::60ec:677b]` | - | prose | IPV6-si | yazılıb. |  |  |
| bench_az_002374 | missed | exact | `2001:db8::3a1` | `[2001:db8::3a1]` | - | prose | tarixçəsində | görünür. |  |  |
| bench_az_002380 | missed | exact | `2001:db8:73b2:2836::f51b` | `[2001:db8:73b2:2836::f51b]` | - | prose | IPv6 | qeyd |  | y |
| bench_az_002399 | missed | exact | `2001:db8::61b8` | `[2001:db8::61b8]` | - | prose | muracietə | ünvanını |  |  |
| bench_az_002419 | missed | exact | `2001:db8::c323` | `[2001:db8::c323]` | - | prose | tarixçəsində | görünür. |  |  |
| bench_az_002424 | missed | exact | `fd00::b970:edd` | `[fd00::b970:edd]` | - | prose | IPV6 | qeyd |  |  |
| bench_az_002462 | missed | exact | `2001:db8::6fbb` | `[2001:db8::6fbb]` | - | prose | tarixçəsində | görünür. |  |  |
| bench_az_002476 | missed | exact | `2001:db8::384e` | `[2001:db8::384e]` | - | prose | tarixçəsində | görünür. |  | y |
| bench_az_002488 | missed | exact | `2001:db8::c297` | `[2001:db8::c297]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_002516 | missed | exact | `fd00::3598:4ffc` | `[fd00::3598:4ffc]` | - | prose | IPv6-si | yazilib. |  |  |
| bench_az_002525 | missed | exact | `2001:db8::5d7b` | `[2001:db8::5d7b]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002588 | split | exact | `[2001]:db8::8741` | `[2001:db8::8741]` | - | prose | tarixçəsində | görünür. |  |  |
| bench_az_002670 | missed | exact | `2001:db8::49cf` | `[2001:db8::49cf]` | - | prose | ünvanı | kimi |  |  |
| bench_az_002713 | missed | exact | `fd00::37cf:4509` | `[fd00::37cf:4509]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002716 | split | exact | `[f]d00::8959:2b62` | `[fd00::8959:2b62]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_002717 | missed | exact | `fd00::7a02:6492` | `[fd00::7a02:6492]` | - | prose | IPv6-si | yazilib. |  |  |
| bench_az_002762 | missed | exact | `fd00::2558:cf05` | `[fd00::2558:cf05]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_002780 | missed | exact | `2001:db8:cdfd:66f7::7c71` | `[2001:db8:cdfd:66f7::7c71]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002783 | missed | exact | `fd00::9088:271f` | `[fd00::9088:271f]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_002799 | missed | exact | `2001:db8::2289` | `[2001:db8::2289]` | - | prose | tarixçəsində | görünür. |  |  |
| bench_az_002830 | split | exact | `[f]d00::4576:dc3b` | `[fd00::4576:dc3b]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_002852 | missed | exact | `2001:db8::64b5` | `[2001:db8::64b5]` | - | prose | IPv6 | qeyd |  | y |
| bench_az_002858 | missed | exact | `fd00::f178:ab1f` | `[fd00::f178:ab1f]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002874 | missed | exact | `2001:db8::86b1` | `[2001:db8::86b1]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002914 | missed | exact | `2001:db8::cb47` | `[2001:db8::cb47]` | - | prose | ünvanı | kimi |  |  |
| bench_az_002920 | missed | exact | `2001:db8::4e55` | `[2001:db8::4e55]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002953 | split | exact | `[f]d00::721a:a8e3` | `[fd00::721a:a8e3]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_002954 | missed | exact | `fd00::a5df:2865` | `[fd00::a5df:2865]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_002980 | missed | exact | `2001:db8::e0b5` | `[2001:db8::e0b5]` | - | prose | IPv6 | qeyd | y |  |
| bench_az_003035 | missed | exact | `fd00::eac:7d21` | `[fd00::eac:7d21]` | - | prose | IPv6-si | yazilib. |  |  |
| bench_az_003064 | missed | exact | `2001:db8::944b` | `[2001:db8::944b]` | - | prose | IPv6 | qeyd |  | y |
| bench_az_003135 | missed | exact | `fd00::6e77:8e68` | `[fd00::6e77:8e68]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_003148 | split | exact | `[2001:db8:8c5:79]12[::7eea]` | `[2001:db8:8c5:7912::7eea]` | - | prose | IPv6-si | yazilib. |  |  |
| bench_az_003165 | missed | exact | `2001:db8::6f30` | `[2001:db8::6f30]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_003272 | split | exact | `[2001:db8:]:[3a8]d` | `[2001:db8::3a8d]` | - | prose | unvnı | -dir. |  |  |
| bench_az_003285 | missed | exact | `2001:db8::3517` | `[2001:db8::3517]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_003293 | split | exact | `[2001:db]8::be[07]` | `[2001:db8::be07]` | - | prose | ünvanı | kimi |  | y |
| bench_az_003310 | missed | exact | `fd00::c057:c750` | `[fd00::c057:c750]` | - | prose | IPv6-si | yazılıb. |  | y |
| bench_az_003363 | missed | exact | `2001:db8::1e97` | `[2001:db8::1e97]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_003378 | missed | exact | `2001:db8::5f72` | `[2001:db8::5f72]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_003383 | missed | exact | `2001:db8::a085` | `[2001:db8::a085]` | - | prose | tarixçəsində | görünür. |  |  |
| bench_az_003445 | split | exact | `[2001]:db8::b2ab` | `[2001:db8::b2ab]` | - | prose | ünvanı | -dir. |  | y |
| bench_az_003455 | split | exact | `[f]d00::a947:7cdc` | `[fd00::a947:7cdc]` | - | prose | ünvanı | kimi |  |  |
| bench_az_003541 | missed | exact | `2001:db8::875a` | `[2001:db8::875a]` | - | prose | tarixçəsində | görünür. |  |  |
| bench_az_003556 | split | exact | `[f]d[00:]:[505]a[:2]174` | `[fd00::505a:2174]` | - | prose | IPv6-si | yazılıb. |  | y |
| bench_az_003582 | missed | exact | `fd00::1cf4:4953` | `[fd00::1cf4:4953]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_003583 | missed | exact | `2001:db8::e462` | `[2001:db8::e462]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_003623 | missed | exact | `2001:db8:112b:f4af::427f` | `[2001:db8:112b:f4af::427f]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_003631 | missed | exact | `fd00::f2e2:f061` | `[fd00::f2e2:f061]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_003702 | missed | exact | `2001:db8::8b0d` | `[2001:db8::8b0d]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_003846 | split | exact | `[f]d00::8110:4c52` | `[fd00::8110:4c52]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_003847 | missed | exact | `2001:db8::3098` | `[2001:db8::3098]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_003853 | missed | exact | `fd00::6c92:6b9d` | `[fd00::6c92:6b9d]` | - | prose | IPv6-si | yazilb. |  |  |
| bench_az_003875 | missed | exact | `fd00::b5d3:1e69` | `[fd00::b5d3:1e69]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_003885 | missed | exact | `2001:db8::5038` | `[2001:db8::5038]` | - | prose | IPv6-si | yazılıb. | y |  |
| bench_az_003896 | missed | exact | `fd00::f810:dc8a` | `[fd00::f810:dc8a]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_003965 | missed | exact | `2001:db8::b60a` | `[2001:db8::b60a]` | - | prose | tarixçəsində | gorunr. |  |  |
| bench_az_003970 | missed | exact | `2001:db8::5ac9` | `[2001:db8::5ac9]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_003990 | missed | exact | `2001:db8::50db` | `[2001:db8::50db]` | - | prose | Logdan | IPv6 |  |  |
| bench_az_004028 | missed | exact | `2001:db8::70de` | `[2001:db8::70de]` | - | prose | ünvanı | kimi |  |  |
| bench_az_004051 | missed | exact | `fd00::2131:46c4` | `[fd00::2131:46c4]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004081 | missed | exact | `2001:db8:bf56:447e::e010` | `[2001:db8:bf56:447e::e010]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004085 | missed | exact | `2001:db8::eed4` | `[2001:db8::eed4]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_004136 | missed | exact | `2001:db8::f142` | `[2001:db8::f142]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_004188 | missed | exact | `fd00::71be:2e65` | `[fd00::71be:2e65]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_004285 | split | exact | `[2001]:db8[:]:e486` | `[2001:db8::e486]` | - | prose | tarixçəsində | görünür. |  |  |
| bench_az_004287 | missed | exact | `fd00::ec97:140f` | `[fd00::ec97:140f]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004309 | split | exact | `[2001:db]8[::]284c` | `[2001:db8::284c]` | - | prose | tarixçəsində | gorunr. |  |  |
| bench_az_004310 | missed | exact | `fd00::e953:ff53` | `[fd00::e953:ff53]` | - | prose | IPv6 | qeyd |  | y |
| bench_az_004311 | missed | exact | `2001:db8::4d9a` | `[2001:db8::4d9a]` | - | prose | tarixçəsində | görünür. |  | y |
| bench_az_004319 | missed | exact | `2001:db8::d28b` | `[2001:db8::d28b]` | - | prose | IPv6-si | yazılıb. |  | y |
| bench_az_004332 | missed | exact | `2001:db8::feb3` | `[2001:db8::feb3]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004339 | missed | exact | `2001:db8::f9ac` | `[2001:db8::f9ac]` | - | prose | IPv6-si | yazılıb. |  | y |
| bench_az_004341 | missed | exact | `2001:db8:5001:c090::ae9` | `[2001:db8:5001:c090::ae9]` | - | prose | IPv6 | qeyd |  | y |
| bench_az_004353 | missed | exact | `2001:db8::17dd` | `[2001:db8::17dd]` | - | prose | IPv6-si | yazilib. |  |  |
| bench_az_004454 | missed | exact | `2001:db8::f6d2` | `[2001:db8::f6d2]` | - | prose | IPv6 | qeyd | y |  |
| bench_az_004492 | split | exact | `[2001]:db8:6de4:a8a6::789d` | `[2001:db8:6de4:a8a6::789d]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_004504 | split | exact | `[f]d00::3fe2:d3c6` | `[fd00::3fe2:d3c6]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_004556 | missed | split | `2001:db8::d4b` | `[2001]:db8::d4b` | - | prose | tarixçəsində | görünür. |  |  |
| bench_az_004570 | missed | exact | `fd00::14ea:1496` | `[fd00::14ea:1496]` | - | prose | IPV6 | qeyd |  |  |
| bench_az_004675 | missed | exact | `fd00::54cd:6eaa` | `[fd00::54cd:6eaa]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_004680 | missed | exact | `2001:db8::6f92` | `[2001:db8::6f92]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004707 | missed | exact | `2001:db8::3b2a` | `[2001:db8::3b2a]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004735 | missed | exact | `fd00::7e7c:3556` | `[fd00::7e7c:3556]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004746 | missed | exact | `2001:db8:2a16:b79b::9841` | `[2001:db8:2a16:b79b::9841]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004770 | split | exact | `[2001:]db8[:]:[ce6]a` | `[2001:db8::ce6a]` | - | prose | ünvanı | kimi |  |  |
| bench_az_004771 | missed | exact | `2001:db8::6428` | `[2001:db8::6428]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004802 | missed | exact | `2001:db8::c0aa` | `[2001:db8::c0aa]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004810 | split | exact | `[f]d00::8a6d:[99ac]` | `[fd00::8a6d:99ac]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004835 | missed | exact | `2001:db8::5712` | `[2001:db8::5712]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004855 | missed | exact | `2001:db8::a488` | `[2001:db8::a488]` | - | prose | IPv6-si | yazılıb. |  |  |
| bench_az_004872 | missed | exact | `2001:db8:9c51:360c::b793` | `[2001:db8:9c51:360c::b793]` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004950 | missed | exact | `2001:db8::36e` | `[2001:db8::36e]` | - | prose | IPv6 | qeyd |  | y |
| bench_az_004966 | missed | split | `2001:db8::d28d` | `2001[:db]8[::d]28d` | - | prose | IPv6 | qeyd |  |  |
| bench_az_004969 | missed | exact | `2001:db8::e79f` | `[2001:db8::e79f]` | - | prose | IPv6 | qeyd |  |  |

## False alarms of IPV6_ADDRESS (no gold IPV6_ADDRESS under them)

### v4.1: 1 (policy items 0)

| shape | n |
|---|---|
| `:aa:aa:aa · gold here - · decoy benchmark_unique` | 1 |

### v4.2: 13 (policy items 0)

| shape | n |
|---|---|
| `: · gold here - · decoy benchmark_unique` | 8 |
| `aa:aa:aa:aa · gold here - · decoy benchmark_unique` | 4 |
| `:aa:aa:aa · gold here - · decoy benchmark_unique` | 1 |

