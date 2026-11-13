# Probability of the gold label on the value's tokens (mean over tokens)

| label | spans | n | v4.1 doc | v4.2 doc | v4.1 sentence | v4.2 sentence | v4.2 doc in 0.2-0.5 |
|---|---|---|---|---|---|---|---|
| IPV6_ADDRESS | v4.2 misses | 160 | 0.99 | 0.06 | 1.00 | 0.99 | 39 |
| IPV6_ADDRESS | v4.2 finds | 60 | 1.00 | 0.99 | 1.00 | 1.00 | 0 |
| IPV4_ADDRESS | v4.2 misses | 10 | 0.70 | 0.26 | 0.87 | 0.98 | 5 |
| IPV4_ADDRESS | v4.2 finds | 60 | 1.00 | 1.00 | 0.88 | 1.00 | 0 |
| EMAIL | v4.2 finds | 60 | 1.00 | 1.00 | 0.99 | 1.00 | 0 |

Medians. `v4.2 finds` is a random sample of the spans v4.2 finds exactly.
