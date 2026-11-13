# PRIVATE_KEY: spans v4.2 or v4.1 does not find exactly

| outcome | v4.2 | v4.1 |
|---|---|---|
| exact | 425 | 426 |
| split | 3 | 2 |
| covered_inexact | 0 | 0 |
| wrong_label | 0 | 0 |
| missed | 0 | 0 |

## Exact rate per frame, all spans (frames folded: case, letters, 5-letter stems)

| frame | n | v4.2 exact | v4.1 exact |
|---|---|---|---|
| `x` | 286 | 286 (100%) | 285 (100%) |
| `priva | x |` | 17 | 17 (100%) | 17 (100%) |
| `priva melum x olara qeyd` | 13 | 13 (100%) | 13 (100%) |
| `key saxla x` | 11 | 11 (100%) | 11 (100%) |
| `info priva x` | 10 | 10 (100%) | 10 (100%) |
| `key gorun x` | 7 | 7 (100%) | 7 (100%) |
| `"priv " x",` | 6 | 5 (83%) | 5 (83%) |
| `qeyd olunu x` | 6 | 6 (100%) | 6 (100%) |
| `gorun - x` | 5 | 5 (100%) | 5 (100%) |
| `x eyni qeydd` | 5 | 5 (100%) | 5 (100%) |
| `saxla - x` | 5 | 5 (100%) | 5 (100%) |
| `x elave hisse` | 4 | 4 (100%) | 4 (100%) |
| `etmis - x` | 3 | 3 (100%) | 3 (100%) |
| `key-i gormu x` | 3 | 3 (100%) | 3 (100%) |
| `olunu - x` | 2 | 2 (100%) | 2 (100%) |
| `x lazim olsa,` | 1 | 1 (100%) | 1 (100%) |
| `x elaqe melum` | 1 | 1 (100%) | 1 (100%) |
| `x murac telef` | 1 | 1 (100%) | 1 (100%) |
| `x kart melum` | 1 | 1 (100%) | 1 (100%) |
| `x yazis soyad` | 1 | 1 (100%) | 1 (100%) |
| `x sessi acces` | 1 | 1 (100%) | 1 (100%) |
| `az962 x;10:22;user@;999.12.4.1` | 1 | 1 (100%) | 1 (100%) |
| `x;172.30.9.240;danaci;https://support.example.com/help/article/10820;p123` | 1 | 1 (100%) | 1 (100%) |
| `x melum forma` | 1 | 1 (100%) | 1 (100%) |
| `02.08 x;-----begin priva` | 1 | 1 (100%) | 1 (100%) |

## v4.2 misses and splits by outcome (n = 3)

| | n |
|---|---|
| `split` | 3 |

## v4.2 misses and splits by cut character (n = 3)

| | n |
|---|---|
| ` ` | 3 |

## v4.2 misses and splits by shape (n = 3)

| | n |
|---|---|
| `-----aaaaa aaaaaaa aaa----- aaaaaaa9aaaaaaaaaaaaaaaaaaa9aaaaaaaaaaaa9 -----aaa aaaaaaa aaa-----` | 1 |
| `-----aaaaa aaaaaaa aaa----- aaaaaa9aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa9a9 -----aaa aaaaaaa aaa-----` | 1 |
| `-----aaaaa aaaaaaa aaa----- aaaaaa9aaaaaaa9aa9a9aaaaaaaaaa999aa9aaa9a -----aaa aaaaaaa aaa-----` | 1 |

## v4.2 misses and splits by context (n = 3)

| | n |
|---|---|
| `CSV / table` | 2 |
| `JSON` | 1 |

## v4.2 misses and splits by frame (n = 3)

| | n |
|---|---|
| `"private_key": " X",` | 1 |
| `X;sk_bench_2247_UVBfrjxWuBrdf6WIo0hOwKrEykvb;at_bench_2248_TSUB1hFiRe2RjKg00cTIij` | 1 |
| `2001:db8:6eb:6ec::6eb; X;5671 0439` | 1 |

## v4.2 misses and splits by previous word (n = 3)

| | n |
|---|---|
| `"` | 1 |
| `private_key;api_key;access_token;saat;yaş` | 1 |
| `2001:db8:6eb:6ec::6eb;` | 1 |

## v4.2 misses and splits by next word (n = 3)

| | n |
|---|---|
| `",` | 1 |
| `;sk_bench_2247_UVBfrjxWuBrdf6WIo0hOwKrEykvb;at_bench_2248_TS` | 1 |
| `;5671` | 1 |

## v4.2 misses and splits by MAC in the same document (n = 3)

| | n |
|---|---|
| `False` | 3 |

## v4.2 misses and splits by hh:mm(:ss) stamp in the same document (n = 3)

| | n |
|---|---|
| `False` | 2 |
| `True` | 1 |

## v4.2 misses and splits by v4.1 outcome on the same span (n = 3)

| | n |
|---|---|
| `exact` | 3 |

## v4.2 misses and splits by doc type (n = 3)

| | n |
|---|---|
| `csv` | 2 |
| `json_config` | 1 |

## v4.2 misses and splits by benchmark category (n = 3)

| | n |
|---|---|
| `structured_csv` | 2 |
| `structured_json_config` | 1 |

## Every span (v4.2 not exact, or v4.1 not exact)

| id | v4.2 | v4.1 | v4.2 pieces | v4.1 pieces | other label (v4.2) | context | prev | next | MAC | stamp |
|---|---|---|---|---|---|---|---|---|---|---|
| bench_az_000166 | split | exact | `[-----BEGIN PRIVATE KEY----- BENCHkm3gDbDyPOztvFsuhLJTaK9QlMzmUkVEBvk4] [-----END PRIVATE KEY-----]` | `[-----BEGIN PRIVATE KEY----- BENCHkm3gDbDyPOztvFsuhLJTaK9QlMzmUkVEBvk4 -----END PRIVATE KEY-----]` | - | JSON | " | ", |  |  |
| bench_az_000166 | exact | split | `[-----BEGIN PRIVATE KEY----- BENCHs1hsAdaFOdVgEcg94mptLQ0lnMQ8nqH6mwHv -----END PRIVATE KEY-----]` | `[-----BEGIN PRIVATE KEY----- BENCHs1hsAdaFOdVgEcg94mptLQ0lnMQ8nqH6mwHv] [-----END PRIVATE KEY-----]` | - | JSON | " | ", |  |  |
| bench_az_000726 | exact | split | `[-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEILG7ekEqiXZX8xMD8iBm9i7LM5xWL3fPP3bh8AZfw8Tp
-----END PRIVATE KEY-----]` | `[-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEILG7ekEqiXZX8xMD8iBm9i7LM5xWL3fPP3bh8AZfw8Tp
-----END PRIVATE] [KEY-----]` | - | prose | görünür: | ; |  | y |
| bench_az_001807 | split | exact | `[-----BEGIN PRIVATE KEY----- BENCHt0ipkXqrrjKsZZgrFycBegoWAMmOSOdym1e4] [-----END PRIVATE KEY-----]` | `[-----BEGIN PRIVATE KEY----- BENCHt0ipkXqrrjKsZZgrFycBegoWAMmOSOdym1e4 -----END PRIVATE KEY-----]` | - | CSV / table | private_key;api_key;access_token;saat;yaş | ;sk_bench_2247_UVBfrjxWuBrdf6WIo0hOwKrEykvb;at_bench_2248_TS |  | y |
| bench_az_002673 | split | exact | `[-----BEGIN PRIVATE KEY----- BENCHH1hfqXWaz0hb8h0rqgteDthHP483bT1ZfW9U] [-----END PRIVATE KEY-----]` | `[-----BEGIN PRIVATE KEY----- BENCHH1hfqXWaz0hb8h0rqgteDthHP483bT1ZfW9U -----END PRIVATE KEY-----]` | - | CSV / table | 2001:db8:6eb:6ec::6eb; | ;5671 |  |  |

## False alarms of PRIVATE_KEY (no gold PRIVATE_KEY under them)

### v4.1: 13 (policy items 0)

| shape | n |
|---|---|
| `- · gold here - · decoy -` | 8 |
| `a · gold here - · decoy -` | 3 |
| `: · gold here - · decoy -` | 2 |

