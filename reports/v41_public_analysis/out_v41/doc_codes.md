# IPV6_ADDRESS not found exactly, by the codes in the same document (benchmark, track R)

| in the same document | v4 missed, with | v4 missed, without | v4.1 missed, with | v4.1 missed, without |
|---|---|---|---|---|
| a dotted 3-part number (`9.9.9`, `v9.99.99`) | 48/118 (41%) | 75/328 (23%) | 2/118 (2%) | 5/328 (2%) |
| a 16-digit code | 33/67 (49%) | 90/379 (24%) | 3/67 (4%) | 4/379 (1%) |
| a code with a dash (`ARX-9999`) | 69/231 (30%) | 54/215 (25%) | 3/231 (1%) | 4/215 (2%) |
| an `hh:mm` time | 18/54 (33%) | 105/392 (27%) | 1/54 (2%) | 6/392 (2%) |

Inside each frame (a dotted 3-part number or a 16-digit code in the document, against neither):

| frame | v4 missed, with a code | v4 missed, without | v4.1 missed, with a code | v4.1 missed, without |
|---|---|---|---|---|
| `serve ipv6- x yazil` | 21/30 (70%) | 17/42 (40%) | 1/30 (3%) | 0/42 (0%) |
| `logda ipv6 x qeyd olunu` | 29/32 (91%) | 22/39 (56%) | 1/32 (3%) | 1/39 (3%) |
| `sebek tarix x gorun` | 4/28 (14%) | 0/31 (0%) | 1/28 (4%) | 0/31 (0%) |
| `ipv6 unvan x kimi goste` | 11/22 (50%) | 8/37 (22%) | 1/22 (5%) | 0/37 (0%) |
| `ipv6 unvan x-dir` | 3/17 (18%) | 0/21 (0%) | 1/17 (6%) | 0/21 (0%) |
