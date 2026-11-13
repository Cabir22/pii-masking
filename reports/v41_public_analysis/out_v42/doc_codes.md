# IPV6_ADDRESS not found exactly, by the codes in the same document (benchmark, track R)

| in the same document | v4.1 missed, with | v4.1 missed, without | v4.2 missed, with | v4.2 missed, without |
|---|---|---|---|---|
| a dotted 3-part number (`9.9.9`, `v9.99.99`) | 2/118 (2%) | 5/328 (2%) | 52/118 (44%) | 108/328 (33%) |
| a 16-digit code | 3/67 (4%) | 4/379 (1%) | 37/67 (55%) | 123/379 (32%) |
| a code with a dash (`ARX-9999`) | 3/231 (1%) | 4/215 (2%) | 95/231 (41%) | 65/215 (30%) |
| an `hh:mm` time | 1/54 (2%) | 6/392 (2%) | 21/54 (39%) | 139/392 (35%) |

Inside each frame (a dotted 3-part number or a 16-digit code in the document, against neither):

| frame | v4.1 missed, with a code | v4.1 missed, without | v4.2 missed, with a code | v4.2 missed, without |
|---|---|---|---|---|
| `serve ipv6- x yazil` | 1/30 (3%) | 0/42 (0%) | 26/30 (87%) | 30/42 (71%) |
| `logda ipv6 x qeyd olunu` | 1/32 (3%) | 1/39 (3%) | 29/32 (91%) | 34/39 (87%) |
| `sebek tarix x gorun` | 1/28 (4%) | 0/31 (0%) | 12/28 (43%) | 7/31 (23%) |
| `ipv6 unvan x kimi goste` | 1/22 (5%) | 0/37 (0%) | 5/22 (23%) | 5/37 (14%) |
| `ipv6 unvan x-dir` | 1/17 (6%) | 0/21 (0%) | 3/17 (18%) | 0/21 (0%) |
