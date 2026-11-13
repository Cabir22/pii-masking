# IP addresses and emails in a line with and without a final period: exact spans found

| label | frame | v4.1 R | v4.2 R | v4.1 M | v4.2 M |
|---|---|---|---|---|---|
| IPV4_ADDRESS | `Server ünvanı {} yazılıb.` | 9/10 | 9/10 | 9/10 | 9/10 |
| IPV4_ADDRESS | `Server ünvanı {} yazılıb;` | 2/10 | 9/10 | 2/10 | 9/10 |
| IPV4_ADDRESS | `Server ünvanı {} yazılıb` | 1/10 | 9/10 | 1/10 | 9/10 |
| IPV4_ADDRESS | `mənim ip {}` | 0/10 | 10/10 | 0/10 | 10/10 |
| IPV4_ADDRESS | `Bağlantı {} ünvanından gəlib` | 0/10 | 10/10 | 0/10 | 10/10 |
| IPV4_ADDRESS | `Server: {} ⏎ Port: 443` | 10/10 | 9/10 | 10/10 | 9/10 |
| IPV6_ADDRESS | `Server IPv6-si {} yazılıb.` | 5/5 | 4/5 | 5/5 | 4/5 |
| IPV6_ADDRESS | `Server IPv6-si {} yazılıb` | 1/5 | 4/5 | 1/5 | 4/5 |
| IPV6_ADDRESS | `Logda IPv6 {} qeyd olunub;` | 1/5 | 4/5 | 1/5 | 4/5 |
| IPV6_ADDRESS | `mənim ipv6 {}` | 3/5 | 4/5 | 3/5 | 4/5 |
| EMAIL | `E-poçt ünvanı {} yazılıb.` | 4/5 | 5/5 | 4/5 | 5/5 |
| EMAIL | `E-poçt ünvanı {} yazılıb` | 4/5 | 5/5 | 4/5 | 5/5 |
| EMAIL | `mənim email {}` | 4/5 | 5/5 | 4/5 | 5/5 |
| EMAIL | `Yazın: {};` | 3/5 | 5/5 | 3/5 | 5/5 |
