# Perturbation test: exact spans found, v3 / v4 (track R)

Variants change one thing at a time (see the script's docstring).

| label | spans | n | doc | sentence | frame | value | frame+value |
|---|---|---|---|---|---|---|---|
| IPV6_ADDRESS | v4 misses | 123 | 106 / 0 | 123 / 123 | 123 / 123 | 72 / 86 | 71 / 123 |
| IPV6_ADDRESS | v4 finds (control) | 40 | 40 / 40 | 40 / 40 | 40 / 40 | 24 / 36 | 22 / 40 |
| IPV4_ADDRESS | v4 misses | 59 | 50 / 0 | 54 / 49 | 58 / 59 | 59 / 42 | 59 / 36 |
| IPV4_ADDRESS | v4 finds (control) | 40 | 40 / 40 | 40 / 40 | 40 / 40 | 37 / 34 | 40 / 27 |
| EMAIL | v4 misses | 26 | 25 / 0 | 23 / 19 | 22 / 26 | 26 / 26 | 26 / 26 |
| EMAIL | v4 finds (control) | 40 | 40 / 40 | 40 / 40 | 39 / 40 | 40 / 40 | 40 / 40 |
