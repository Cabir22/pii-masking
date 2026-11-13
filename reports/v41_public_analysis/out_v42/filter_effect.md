# v4.2: what track M's validity-2 filter drops (M0 = track M without it)

## probes: 11 spans dropped, in 1680 documents (filter(M0) = M in every one)

| label | why | what it was | n |
|---|---|---|---|
| AZ_FIN | D-2 dummy | look-alike | 3 |
| CARD_SECURITY_CODE | CVV not 3-4 digits | look-alike | 1 |
| DATE | impossible DATE | look-alike | 4 |
| TIME | impossible TIME | look-alike | 3 |

| family | id | label | value | words before | why | what it was | track R masks it too |
|---|---|---|---|---|---|---|---|
| decoy_cvv | decoy_cvv_014 | CARD_SECURITY_CODE | `18275` | CVV kodu: | CVV not 3-4 digits | look-alike: invalid_shape | yes |
| decoy_date | decoy_date_004 | DATE | `30.02.2027` | Sənəd | impossible DATE | look-alike: invalid_shape | yes |
| decoy_date | decoy_date_016 | DATE | `30.02.2024` | Sənəd | impossible DATE | look-alike: invalid_shape | yes |
| decoy_date | decoy_date_022 | DATE | `30.02.2026` | Sənəd | impossible DATE | look-alike: invalid_shape | yes |
| decoy_fin | decoy_fin_010 | AZ_FIN | `A12B34` | Ərizədə FİN | D-2 dummy | look-alike: d2_dummy (policy) | yes |
| decoy_time | decoy_time_004 | TIME | `24:51` | Qatar saat | impossible TIME | look-alike: invalid_shape | yes |
| decoy_time | decoy_time_010 | TIME | `24:13` | Qatar saat | impossible TIME | look-alike: invalid_shape | yes |
| decoy_time | decoy_time_016 | TIME | `27:49` | Qatar saat | impossible TIME | look-alike: invalid_shape | yes |
| inflected_anchor | inflected_anchor_014 | DATE | `30.02.2026` | düzəldin, düzgünü | impossible DATE | look-alike: invalid_shape | yes |
| punct_touching | punct_touching_022 | AZ_FIN | `A12B34` | FİN: | D-2 dummy | look-alike: policy_d36d (policy) | yes |
| single_entity | single_entity_016 | AZ_FIN | `A12B34` | FİN kodu | D-2 dummy | look-alike: d2_dummy (policy) | yes |

## benchmark: 56 spans dropped, in 5000 documents (filter(M0) = M in every one)

| label | why | what it was | n |
|---|---|---|---|
| CARD_SECURITY_CODE | CVV not 3-4 digits | look-alike | 3 |
| CARD_SECURITY_CODE | CVV not 3-4 digits | other false alarm | 1 |
| DATE | impossible DATE | other false alarm | 15 |
| IPV4_ADDRESS | D-2 dummy | look-alike | 20 |
| IPV4_ADDRESS | D-2 dummy | other false alarm | 16 |
| TIME | D-2 dummy | other false alarm | 1 |

| family | id | label | value | words before | why | what it was | track R masks it too |
|---|---|---|---|---|---|---|---|
|  | bench_az_000008 | DATE | `00-11-22` | MAC sahəsində | impossible DATE | other false alarm | yes |
|  | bench_az_000040 | DATE | `00-11-22` | şəbəkə profilində | impossible DATE | other false alarm | yes |
|  | bench_az_000157 | IPV4_ADDRESS | `1.2.3.4` | IP sahəsində | D-2 dummy | look-alike: benchmark_unique | yes |
|  | bench_az_000177 | IPV4_ADDRESS | `1.2.3.4` | ünvanı kimi | D-2 dummy | other false alarm | yes |
|  | bench_az_000433 | IPV4_ADDRESS | `1.2.3.4` | IP sahəsində | D-2 dummy | look-alike: benchmark_unique | yes |
|  | bench_az_000491 | IPV4_ADDRESS | `1.2.3.4` | ünvanı kimi | D-2 dummy | other false alarm | yes |
|  | bench_az_000566 | IPV4_ADDRESS | `1.2.3.4` | ünvanı kimi | D-2 dummy | look-alike: benchmark_unique | yes |
|  | bench_az_000630 | DATE | `00-11-22` | şəbəkə profilində | impossible DATE | other false alarm | yes |
|  | bench_az_000682 | IPV4_ADDRESS | `1.2.3.4` | IP sahəsində | D-2 dummy | look-alike: benchmark_unique | yes |
|  | bench_az_000731 | DATE | `00-11-22` | ünvanı kimi | impossible DATE | other false alarm | yes |
|  | bench_az_000752 | DATE | `00-11-22` | ünvanı kimi | impossible DATE | other false alarm | yes |
|  | bench_az_000996 | IPV4_ADDRESS | `1.2.3.4` | ünvanı kimi | D-2 dummy | other false alarm | yes |
|  | bench_az_001057 | DATE | `00-11-22` | ünvanı kimi | impossible DATE | other false alarm | yes |
|  | bench_az_001069 | IPV4_ADDRESS | `1.2.3.4` | ünvanı kimi | D-2 dummy | other false alarm | yes |
|  | bench_az_001127 | IPV4_ADDRESS | `1.2.3.4` | IP sahəsində | D-2 dummy | look-alike: benchmark_unique | yes |
|  | bench_az_001462 | TIME | `12:34:56` | ünvanı kimi | D-2 dummy | other false alarm | yes |
|  | bench_az_001504 | IPV4_ADDRESS | `1.2.3.4` | ünvanı kimi | D-2 dummy | look-alike: benchmark_unique | yes |
|  | bench_az_001509 | IPV4_ADDRESS | `1.2.3.4` | ünvanı kimi | D-2 dummy | other false alarm | yes |
|  | bench_az_001513 | IPV4_ADDRESS | `1.2.3.4` | IP sahəsində | D-2 dummy | look-alike: benchmark_unique | yes |
|  | bench_az_001777 | IPV4_ADDRESS | `1.2.3.4` | ünvanı kimi | D-2 dummy | other false alarm | yes |
|  | bench_az_001781 | IPV4_ADDRESS | `1.2.3.4` | IP sahəsində | D-2 dummy | look-alike: benchmark_unique | yes |
|  | bench_az_001823 | DATE | `00-11-22` | MAC sahəsində | impossible DATE | other false alarm | yes |
|  | bench_az_001873 | CARD_SECURITY_CODE | `42` | kodu bölməsində | CVV not 3-4 digits | look-alike: benchmark_unique | yes |
|  | bench_az_002147 | DATE | `00-11-22` | unvanı kimi | impossible DATE | other false alarm | yes |
|  | bench_az_002199 | IPV4_ADDRESS | `1.2.3.4` | ünvanı kimi | D-2 dummy | look-alike: benchmark_unique | yes |
|  | bench_az_002282 | IPV4_ADDRESS | `1.2.3.4` | ünvanı kimi | D-2 dummy | other false alarm | yes |
|  | bench_az_002531 | DATE | `00-11-22` | MAC sahəsində | impossible DATE | other false alarm | yes |
|  | bench_az_002625 | IPV4_ADDRESS | `1.2.3.4` | ünvanı kimi | D-2 dummy | look-alike: benchmark_unique | yes |
|  | bench_az_002871 | CARD_SECURITY_CODE | `6` | FIN kodunu | CVV not 3-4 digits | other false alarm | yes |
|  | bench_az_002980 | IPV4_ADDRESS | `1.2.3.4` | IP sahəsində | D-2 dummy | look-alike: benchmark_unique | yes |
|  | bench_az_003051 | DATE | `00-11-22` | şəbəkə profilində | impossible DATE | other false alarm | yes |
|  | bench_az_003129 | IPV4_ADDRESS | `1.2.3.4` | ünvanı kimi | D-2 dummy | look-alike: benchmark_unique | yes |
|  | bench_az_003133 | DATE | `00-11-22` | ünvanı kimi | impossible DATE | other false alarm | yes |
|  | bench_az_003329 | IPV4_ADDRESS | `1.2.3.4` | ünvanı kimi | D-2 dummy | other false alarm | yes |
|  | bench_az_003347 | IPV4_ADDRESS | `1.2.3.4` | ünvanı kimi | D-2 dummy | other false alarm | yes |
|  | bench_az_003419 | DATE | `00-11-22` | şəbəkə profilində | impossible DATE | other false alarm | yes |
|  | bench_az_003453 | CARD_SECURITY_CODE | `42` | kodu bölməsində | CVV not 3-4 digits | look-alike: benchmark_unique | yes |
|  | bench_az_003623 | IPV4_ADDRESS | `1.2.3.4` | IP sahəsində | D-2 dummy | look-alike: benchmark_unique | yes |
|  | bench_az_003693 | IPV4_ADDRESS | `1.2.3.4` | IP sahəsində | D-2 dummy | look-alike: benchmark_unique | yes |
|  | bench_az_003881 | CARD_SECURITY_CODE | `42` | kodu bölməsində | CVV not 3-4 digits | look-alike: benchmark_unique | yes |
|  | bench_az_003888 | IPV4_ADDRESS | `1.2.3.4` | ünvanı kimi | D-2 dummy | look-alike: benchmark_unique | yes |
|  | bench_az_003930 | IPV4_ADDRESS | `1.2.3.4` | ünvanı kimi | D-2 dummy | other false alarm | yes |
|  | bench_az_004014 | IPV4_ADDRESS | `1.2.3.4` | ünvanı kimi | D-2 dummy | other false alarm | yes |
|  | bench_az_004041 | DATE | `00-11-22` | MAC sahəsində | impossible DATE | other false alarm | yes |
|  | bench_az_004082 | DATE | `00-11-22` | unvnı kimi | impossible DATE | other false alarm | yes |
|  | bench_az_004157 | IPV4_ADDRESS | `1.2.3.4` | ünvanı kimi | D-2 dummy | other false alarm | yes |
|  | bench_az_004173 | DATE | `00-11-22` | şəbəkə profilində | impossible DATE | other false alarm | yes |
|  | bench_az_004179 | IPV4_ADDRESS | `1.2.3.4` | ünvanı kimi | D-2 dummy | other false alarm | yes |
|  | bench_az_004276 | IPV4_ADDRESS | `1.2.3.4` | IP sahəsində | D-2 dummy | look-alike: benchmark_unique | yes |
|  | bench_az_004451 | IPV4_ADDRESS | `1.2.3.4` | ünvanı kimi | D-2 dummy | other false alarm | yes |
|  | bench_az_004506 | IPV4_ADDRESS | `1.2.3.4` | ünvanı kimi | D-2 dummy | look-alike: benchmark_unique | yes |
|  | bench_az_004550 | IPV4_ADDRESS | `1.2.3.4` | ünvanı kimi | D-2 dummy | look-alike: benchmark_unique | yes |
|  | bench_az_004721 | IPV4_ADDRESS | `1.2.3.4` | ünvanı kimi | D-2 dummy | look-alike: benchmark_unique | yes |
|  | bench_az_004730 | IPV4_ADDRESS | `1.2.3.4` | ünvanı kimi | D-2 dummy | other false alarm | yes |
|  | bench_az_004771 | IPV4_ADDRESS | `1.2.3.4` | ünvanı kimi | D-2 dummy | look-alike: benchmark_unique | yes |
|  | bench_az_004929 | IPV4_ADDRESS | `1.2.3.4` | ünvanı kimi | D-2 dummy | other false alarm | yes |
