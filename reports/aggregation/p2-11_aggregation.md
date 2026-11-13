# P2-11 aggregation audit (was P3-6)

Checkpoint `your-hf-org/masking-multilingual` (revision `3a0a6e5df228`), CPU, git `a03da9f401`. 456 probe documents (pem, spaced_phone, spaced_card_iban, punct_touching, bare_name, suffixed_entities, prose_card, prose_iban) and 220 `golden_az` documents. One network pass per document and tokenizer; every strategy decodes the same output. Public sets only (A2.5). Measurement only (D-3).

## RC5 probes, all families together

| Decode | Exact P | Exact R | Exact F1 | Overlap F1 | Leaked PII chars % | Boundary errors (narrower / wider / shifted) | Split values (pieces) |
|---|---|---|---|---|---|---|---|
| `raw/simple` | 34.1 | 43.8 | **38.3** | 71.7 | 25.5 | 265 (262 / 3 / 0) | 17 of 388 (216) |
| `raw/first` | 61.1 | 44.8 | **51.7** | 64.9 | 43.4 | 57 (33 / 22 / 2) | 10 of 388 (31) |
| `raw/max` | 65.6 | 40.7 | **50.2** | 59.9 | 37.7 | 42 (37 / 4 / 1) | 9 of 388 (27) |
| `raw/average` | 57.4 | 36.9 | **44.9** | 59.5 | 36.4 | 58 (27 / 26 / 5) | 11 of 388 (29) |
| `patched/first` | 58.9 | 45.1 | **51.1** | 65.4 | 43.5 | 67 (45 / 22 / 0) | 9 of 388 (39) |
| `patched/max` | 63.7 | 40.7 | **49.7** | 59.6 | 42.8 | 45 (42 / 3 / 0) | 8 of 388 (29) |
| `patched/average` | 55.2 | 37.1 | **44.4** | 60.1 | 37.7 | 68 (32 / 26 / 10) | 10 of 388 (37) |
| `word_consistent` | 57.0 | 48.5 | **52.4** | 64.6 | 32.7 | 76 (76 / 0 / 0) | 14 of 388 (68) |

## Per family: exact F1 / split values

| Family | Gold | `raw/simple` | `raw/first` | `raw/max` | `raw/average` | `patched/first` | `patched/max` | `patched/average` | `word_consistent` |
|---|---|---|---|---|---|---|---|---|---|
| bare_name | 45 | 46.9 / 0 | 36.7 / 0 | 35.7 / 0 | 32.1 / 0 | 36.7 / 0 | 35.7 / 0 | 32.1 / 0 | 49.2 / 0 |
| golden_az | 1061 | 95.0 / 1 | 43.3 / 0 | 53.4 / 0 | 45.8 / 0 | 43.5 / 0 | 53.4 / 0 | 46.1 / 0 | 98.7 / 0 |
| pem | 10 | 0.0 / 10 | 0.0 / 8 | 0.0 / 8 | 0.0 / 10 | 0.0 / 7 | 0.0 / 7 | 0.0 / 9 | 0.0 / 10 |
| prose_card | 12 | 25.0 / 0 | 25.0 / 0 | 25.0 / 0 | 25.0 / 0 | 35.3 / 0 | 35.3 / 0 | 35.3 / 0 | 35.3 / 0 |
| prose_iban | 12 | 0.0 / 1 | 11.8 / 0 | 11.8 / 0 | 0.0 / 0 | 11.1 / 0 | 0.0 / 0 | 0.0 / 0 | 0.0 / 0 |
| punct_touching | 12 | 51.6 / 0 | 0.0 / 0 | 0.0 / 0 | 0.0 / 0 | 0.0 / 0 | 0.0 / 0 | 0.0 / 0 | 75.0 / 0 |
| spaced_card_iban | 12 | 34.1 / 3 | 5.3 / 2 | 13.3 / 1 | 11.1 / 1 | 5.3 / 2 | 13.3 / 1 | 11.1 / 1 | 44.4 / 1 |
| spaced_phone | 12 | 55.6 / 0 | 55.6 / 0 | 55.6 / 0 | 55.6 / 0 | 55.6 / 0 | 55.6 / 0 | 55.6 / 0 | 55.6 / 0 |
| suffixed_entities | 273 | 56.6 / 3 | 68.3 / 0 | 64.9 / 0 | 60.7 / 0 | 68.3 / 0 | 64.9 / 0 | 60.7 / 0 | 65.0 / 3 |

## Leaked PII characters per family (%)

| Family | `raw/simple` | `raw/first` | `raw/max` | `raw/average` | `patched/first` | `patched/max` | `patched/average` | `word_consistent` |
|---|---|---|---|---|---|---|---|---|
| bare_name | 63.7 | 67.3 | 72.7 | 72.3 | 67.3 | 72.7 | 72.3 | 63.3 |
| golden_az | 0.3 | 18.5 | 58.2 | 10.2 | 18.7 | 58.5 | 11.5 | 0.2 |
| pem | 20.5 | 42.2 | 33.6 | 32.3 | 42.4 | 39.8 | 34.0 | 29.5 |
| prose_card | 81.9 | 81.9 | 81.9 | 81.9 | 74.3 | 74.3 | 74.3 | 74.3 |
| prose_iban | 95.7 | 92.0 | 92.0 | 100.0 | 92.0 | 100.0 | 100.0 | 100.0 |
| punct_touching | 0.6 | 77.9 | 92.3 | 0.0 | 77.9 | 100.0 | 0.0 | 0.0 |
| spaced_card_iban | 35.8 | 38.4 | 44.0 | 34.6 | 38.4 | 44.0 | 34.6 | 34.6 |
| spaced_phone | 57.9 | 57.9 | 57.9 | 57.9 | 57.2 | 57.2 | 57.2 | 57.2 |
| suffixed_entities | 38.5 | 36.2 | 43.7 | 48.7 | 36.2 | 43.7 | 48.7 | 39.0 |
