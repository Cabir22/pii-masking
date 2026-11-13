# Probability of the gold label on the value's tokens (mean over tokens)

| label | spans | n | v4 doc | v4.1 doc | v4 sentence | v4.1 sentence | v4.1 doc in 0.2-0.5 |
|---|---|---|---|---|---|---|---|
| IPV6_ADDRESS | v4.1 misses | 7 | 0.03 | 0.52 | 1.00 | 1.00 | 3 |
| IPV6_ADDRESS | v4.1 finds | 60 | 0.99 | 1.00 | 1.00 | 1.00 | 0 |
| IPV4_ADDRESS | v4.1 misses | 19 | 0.01 | 0.29 | 0.96 | 0.86 | 3 |
| IPV4_ADDRESS | v4.1 finds | 60 | 1.00 | 1.00 | 1.00 | 0.88 | 0 |
| EMAIL | v4.1 misses | 4 | 0.87 | 0.94 | 0.81 | 0.95 | 0 |
| EMAIL | v4.1 finds | 60 | 1.00 | 1.00 | 1.00 | 0.99 | 0 |

Medians. `v4.1 finds` is a random sample of the spans v4.1 finds exactly.
