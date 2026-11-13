# Probability of the gold label on the value's tokens (mean over tokens)

| label | spans | n | v3 doc | v4 doc | v3 sentence | v4 sentence | v4 doc in 0.2-0.5 |
|---|---|---|---|---|---|---|---|
| IPV6_ADDRESS | v4 misses | 123 | 0.99 | 0.11 | 1.00 | 1.00 | 36 |
| IPV6_ADDRESS | v4 finds | 60 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| IPV4_ADDRESS | v4 misses | 59 | 1.00 | 0.07 | 1.00 | 0.99 | 13 |
| IPV4_ADDRESS | v4 finds | 60 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| EMAIL | v4 misses | 26 | 1.00 | 0.88 | 1.00 | 0.99 | 0 |
| EMAIL | v4 finds | 60 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |

Medians. `v4 finds` is a random sample of the spans v4 finds exactly.
