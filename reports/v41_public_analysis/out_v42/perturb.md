# Perturbation test: exact spans found, v4.1 / v4.2 (track R)

Variants change one thing at a time (see the script's docstring).

| label | spans | n | doc | sentence | frame | value | frame+value |
|---|---|---|---|---|---|---|---|
| IPV6_ADDRESS | v4.2 misses | 160 | 154 / 0 | 160 / 160 | 160 / 160 | 160 / 91 | 160 / 91 |
| IPV6_ADDRESS | v4.2 finds (control) | 40 | 40 / 40 | 39 / 40 | 40 / 40 | 38 / 22 | 40 / 21 |
| IPV4_ADDRESS | v4.2 misses | 10 | 5 / 0 | 1 / 8 | 10 / 10 | 3 / 7 | 10 / 10 |
| IPV4_ADDRESS | v4.2 finds (control) | 40 | 37 / 40 | 16 / 40 | 40 / 40 | 18 / 33 | 40 / 40 |
| EMAIL | v4.2 finds (control) | 40 | 39 / 40 | 23 / 40 | 33 / 40 | 40 / 40 | 40 / 40 |
