# PRIVATE_KEY: spans v4.1 or v4 does not find exactly

| outcome | v4.1 | v4 |
|---|---|---|
| exact | 426 | 427 |
| split | 2 | 0 |
| covered_inexact | 0 | 1 |
| wrong_label | 0 | 0 |
| missed | 0 | 0 |

## Exact rate per frame, all spans (frames folded: case, letters, 5-letter stems)

| frame | n | v4.1 exact | v4 exact |
|---|---|---|---|
| `x` | 286 | 285 (100%) | 286 (100%) |
| `priva | x |` | 17 | 17 (100%) | 17 (100%) |
| `priva melum x olara qeyd` | 13 | 13 (100%) | 13 (100%) |
| `key saxla x` | 11 | 11 (100%) | 11 (100%) |
| `info priva x` | 10 | 10 (100%) | 10 (100%) |
| `key gorun x` | 7 | 7 (100%) | 7 (100%) |
| `"priv " x",` | 6 | 5 (83%) | 6 (100%) |
| `qeyd olunu x` | 6 | 6 (100%) | 6 (100%) |
| `gorun - x` | 5 | 5 (100%) | 5 (100%) |
| `x eyni qeydd` | 5 | 5 (100%) | 5 (100%) |
| `saxla - x` | 5 | 5 (100%) | 4 (80%) |
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

## v4.1 misses and splits by outcome (n = 2)

| | n |
|---|---|
| `split` | 2 |

## v4.1 misses and splits by cut character (n = 2)

| | n |
|---|---|
| ` ` | 2 |

## v4.1 misses and splits by shape (n = 2)

| | n |
|---|---|
| `-----aaaaa aaaaaaa aaa----- aaaaaa9aaaaaaaaaaaaa99aaaaa9aaaa9aaa9aaaa -----aaa aaaaaaa aaa-----` | 1 |
| `-----aaaaa aaaaaaa aaa-----
aa9aaaaaaaaaa9aaaaaaaaa9aaaaaaaa9aaa9aaa9a9aa9aaa9aaa9aa9aaaa9aa
-----aaa aaaaaaa aaa-----` | 1 |

## v4.1 misses and splits by context (n = 2)

| | n |
|---|---|
| `JSON` | 1 |
| `prose` | 1 |

## v4.1 misses and splits by frame (n = 2)

| | n |
|---|---|
| `"private_key": " X",` | 1 |
| `X` | 1 |

## v4.1 misses and splits by previous word (n = 2)

| | n |
|---|---|
| `"` | 1 |
| `görünür:` | 1 |

## v4.1 misses and splits by next word (n = 2)

| | n |
|---|---|
| `",` | 1 |
| `;` | 1 |

## v4.1 misses and splits by MAC in the same document (n = 2)

| | n |
|---|---|
| `False` | 2 |

## v4.1 misses and splits by hh:mm(:ss) stamp in the same document (n = 2)

| | n |
|---|---|
| `False` | 1 |
| `True` | 1 |

## v4.1 misses and splits by v4 outcome on the same span (n = 2)

| | n |
|---|---|
| `exact` | 2 |

## v4.1 misses and splits by doc type (n = 2)

| | n |
|---|---|
| `json_config` | 1 |
| `first_person_form` | 1 |

## v4.1 misses and splits by benchmark category (n = 2)

| | n |
|---|---|
| `structured_json_config` | 1 |
| `positive_control` | 1 |

## Every span (v4.1 not exact, or v4 not exact)

| id | v4.1 | v4 | v4.1 pieces | v4 pieces | other label (v4.1) | context | prev | next | MAC | stamp |
|---|---|---|---|---|---|---|---|---|---|---|
| bench_az_000166 | split | exact | `[-----BEGIN PRIVATE KEY----- BENCHs1hsAdaFOdVgEcg94mptLQ0lnMQ8nqH6mwHv] [-----END PRIVATE KEY-----]` | `[-----BEGIN PRIVATE KEY----- BENCHs1hsAdaFOdVgEcg94mptLQ0lnMQ8nqH6mwHv -----END PRIVATE KEY-----]` | - | JSON | " | ", |  |  |
| bench_az_000726 | split | exact | `[-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEILG7ekEqiXZX8xMD8iBm9i7LM5xWL3fPP3bh8AZfw8Tp
-----END PRIVATE] [KEY-----]` | `[-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEILG7ekEqiXZX8xMD8iBm9i7LM5xWL3fPP3bh8AZfw8Tp
-----END PRIVATE KEY-----]` | - | prose | görünür: | ; |  | y |
| bench_az_002080 | exact | covered_inexact | `[-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEIHBALOhph/YhTSI8LsB07Rrh1WIKh3ZLPmO5ouKQs///
-----END PRIVATE KEY-----]` | `[-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEIHBALOhph/YhTSI8LsB07Rrh1WIKh3ZLPmO5ouKQs///
-----END PRIVATE KEY-----]` | - | prose | - | ; |  |  |

## False alarms of PRIVATE_KEY (no gold PRIVATE_KEY under them)

### v4: 18 (policy items 0)

| shape | n |
|---|---|
| `- · gold here - · decoy -` | 5 |
| `a · gold here - · decoy -` | 5 |
| `: · gold here - · decoy -` | 4 |
| `- · gold here - · decoy benchmark_unique` | 1 |
| `9 · gold here - · decoy benchmark_unique` | 1 |
| `a · gold here - · decoy benchmark_unique` | 1 |
| `9 · gold here CARD_SECURITY_CODE · decoy -` | 1 |

### v4.1: 13 (policy items 0)

| shape | n |
|---|---|
| `- · gold here - · decoy -` | 8 |
| `a · gold here - · decoy -` | 3 |
| `: · gold here - · decoy -` | 2 |

