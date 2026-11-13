# API_KEY: spans v4.2 or v4.1 does not find exactly

| outcome | v4.2 | v4.1 |
|---|---|---|
| exact | 371 | 371 |
| split | 0 | 0 |
| covered_inexact | 0 | 0 |
| wrong_label | 0 | 0 |
| missed | 0 | 0 |

## Exact rate per frame, all spans (frames folded: case, letters, 5-letter stems)

| frame | n | v4.2 exact | v4.1 exact |
|---|---|---|---|
| `api acari x kimi goste` | 60 | 60 (100%) | 60 (100%) |
| `i̇nte qeydi x istif olunu` | 60 | 60 (100%) | 60 (100%) |
| `api key x gorun` | 54 | 54 (100%) | 54 (100%) |
| `konfi api_k x yazil` | 46 | 46 (100%) | 46 (100%) |
| `acari kimi x istif edire` | 36 | 36 (100%) | 36 (100%) |
| `konfi x api key-n` | 28 | 28 (100%) | 28 (100%) |
| `servi ucun x acari qeyd` | 25 | 25 (100%) | 25 (100%) |
| `info api_k x` | 16 | 16 (100%) | 16 (100%) |
| `"api_ " x",` | 13 | 13 (100%) | 13 (100%) |
| `api_k | x |` | 9 | 9 (100%) | 9 (100%) |
| `api_k melum x olara qeyd` | 6 | 6 (100%) | 6 (100%) |
| `api ky x gorun` | 2 | 2 (100%) | 2 (100%) |
| `https x;07:13;user@;999.12.4.1` | 1 | 1 (100%) | 1 (100%) |
| `x;genclik kuces` | 1 | 1 (100%) | 1 (100%) |
| `acari kimi x istif eddir` | 1 | 1 (100%) | 1 (100%) |
| `x;89994275288689564661;zq700907;xsygfxv;12345` | 1 | 1 (100%) | 1 (100%) |
| `x;sk_bench_2976_fdunryh5vhtki1sk63lsm4oji57w;89994245907638857507;25:81;999` | 1 | 1 (100%) | 1 (100%) |
| `sk_be x;89994245907638857507;25:81;999` | 1 | 1 (100%) | 1 (100%) |
| `priva key-- x;at_bench_2248_tsub1hfire2rjkg00ctiijbuxnglag;25:81;999` | 1 | 1 (100%) | 1 (100%) |
| `89994 x;a2:38:c7:ce:66:62;az1994;000` | 1 | 1 (100%) | 1 (100%) |
| `x;lahic;nasihe;az1994;000` | 1 | 1 (100%) | 1 (100%) |
| `348;p x;az1994;000` | 1 | 1 (100%) | 1 (100%) |
| `api acri x kimi goste` | 1 | 1 (100%) | 1 (100%) |
| `01 67; x;user@;999.12.4.1` | 1 | 1 (100%) | 1 (100%) |
| `x;zx8001956;qadir;az1994;000` | 1 | 1 (100%) | 1 (100%) |

## v4.2 misses and splits by outcome (n = 0)

| | n |
|---|---|

## v4.2 misses and splits by cut character (n = 0)

| | n |
|---|---|

## v4.2 misses and splits by shape (n = 0)

| | n |
|---|---|

## v4.2 misses and splits by context (n = 0)

| | n |
|---|---|

## v4.2 misses and splits by frame (n = 0)

| | n |
|---|---|

## v4.2 misses and splits by previous word (n = 0)

| | n |
|---|---|

## v4.2 misses and splits by next word (n = 0)

| | n |
|---|---|

## v4.2 misses and splits by MAC in the same document (n = 0)

| | n |
|---|---|

## v4.2 misses and splits by hh:mm(:ss) stamp in the same document (n = 0)

| | n |
|---|---|

## v4.2 misses and splits by v4.1 outcome on the same span (n = 0)

| | n |
|---|---|

## v4.2 misses and splits by doc type (n = 0)

| | n |
|---|---|

## v4.2 misses and splits by benchmark category (n = 0)

| | n |
|---|---|

## Every span (v4.2 not exact, or v4.1 not exact)

| id | v4.2 | v4.1 | v4.2 pieces | v4.1 pieces | other label (v4.2) | context | prev | next | MAC | stamp |
|---|---|---|---|---|---|---|---|---|---|---|

## False alarms of API_KEY (no gold API_KEY under them)

### v4.2: 2 (policy items 0)

| shape | n |
|---|---|
| `aa99aaaa9a9aaa9aa9a9aaa9a9a9 · gold here IBAN · decoy -` | 1 |
| `aa99aaaaaaaaaaa9aaaaaaa9aaaa · gold here IBAN · decoy -` | 1 |

