# Bug check: `your-hf-org/masking-multilingual` @ `3a0a6e5df228`

`scripts/release_check.sh --bug-check`, 2026-10-13 11:40 UTC, code `1e97694`. Probes and the benchmark only, against Run B. **Not a release verdict** (D-44b): shadow-dev and real text are not looked at.

**8 possible bug(s):**

- benchmark: ACCESS_TOKEN near 0 (recall 0.0, F1 0.0, 385 gold values)
- benchmark micro F1 68.7, more than 10 points below Run B's 88.9
- benchmark: ACCESS_TOKEN F1 0.0, more than 30 points below Run B's 98.7
- benchmark: AGE F1 66.3, more than 30 points below Run B's 97.3
- benchmark: API_KEY F1 49.7, more than 30 points below Run B's 98.0
- benchmark: AZ_DRIVER_LICENSE_NUMBER F1 40.4, more than 30 points below Run B's 92.9
- benchmark: DATE F1 57.5, more than 30 points below Run B's 88.1
- benchmark: IPV6_ADDRESS F1 18.0, more than 30 points below Run B's 95.3

| Check | Result |
|---|---|
| Benchmark micro F1 (R / M) | 68.7 / 71.4 (Run B 88.9) |
| Label map | 55 tags, 27 labels, same as Run B |
| Tokenizer | vocabulary 250002, same ids as Run B on the test strings |
| Predictions checked | 28286 |
| Values after the first 512-token window (400 runb_test documents, R) | found 83.9% of 93 vs 83.1% before |
