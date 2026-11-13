# code_density: checkpoint 1, v4.2 and m1 (26 Oct 2026)

Exact recall per label at 0 / 2 / 6 unlabelled codes, 10 values per cell. Probes set scored with eval/scoreboard.py (tok022 env).

```
track M: exact recall, 0 / 2 / 6 codes (10 values each)
                checkpoint 1          v4.2            m1
IPV4_ADDRESS          10/3/0      10/10/10      10/10/10
IPV6_ADDRESS           7/3/1      10/10/10       10/10/2
MAC_ADDRESS           10/1/0      10/10/10        10/9/3
URL                   10/7/5      10/10/10      10/10/10
ACCESS_TOKEN           5/5/4      10/10/10         9/6/9
API_KEY                9/3/2      10/10/10      10/10/10
EMAIL                10/10/7      10/10/10      10/10/10
all, %              87/46/27   100/100/100      99/93/77
target                  FAIL          PASS          FAIL
codes masked        0 of 560      0 of 560      0 of 560
```

Track R gives the same for v4.2 and m1.

**D-77 (26 Oct): C14 blocks from m2** (every label >= 9/10 at each density, family >= 95%, track M). Re-scored with that target:
m1 fails (89.5% overall, worst cell IPV6_ADDRESS|6 at 2/10); v4.2 passes; checkpoint 1 fails.
