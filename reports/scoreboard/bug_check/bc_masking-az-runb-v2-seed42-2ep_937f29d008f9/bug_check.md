# Bug check: `your-hf-org/masking-az-runb-v2-seed42-2ep` @ `937f29d008f9`

`scripts/release_check.sh --bug-check`, 2026-10-13 11:08 UTC, code `1e97694`. Probes and the benchmark only, against Run B. **Not a release verdict** (D-44b): shadow-dev and real text are not looked at.

**No clear bug found.**

| Check | Result |
|---|---|
| Benchmark micro F1 (R / M) | 88.9 / 92.0 (Run B 88.9) |
| Label map | 55 tags, 27 labels, same as Run B |
| Tokenizer | vocabulary 250002, same ids as Run B on the test strings |
| Predictions checked | 25440 |
| Values after the first 512-token window (400 runb_test documents, R) | found 91.4% of 93 vs 98.0% before |
