"""v4.2 analysis: v4.1 split IPv4 and IPv6 when the sentence or line
has no final period (v41_to_v42_note). The short frames of that note, now as
a script: each frame with a final `.`, with `;`, with nothing, and the chat /
log shapes, for IPv4, IPv6 and email. Tracks R and M, exact span, the pair in P4_PAIR.

    python reports/v41_public_analysis/linestop_frames.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import read_errors as R  # noqa: E402

VALUES = {
    "IPV4_ADDRESS": ["10.12.44.201", "185.34.112.17", "192.168.10.45", "45.103.192.192", "203.0.113.55",
                     "8.8.8.8", "10.0.0.1", "192.168.0.5", "172.16.20.12", "100.64.0.9"],
    "IPV6_ADDRESS": ["2001:db8::13b2", "fe80::1ff:fe23:4567:890a", "2a02:2c8:4:1::25", "::ffff:10.0.0.1",
                     "2001:0db8:85a3:0000:0000:8a2e:0370:7334"],
    "EMAIL": ["leyla.mammadova@gmail.com", "orxan88@mail.ru", "info@sirket.az", "n.aliyev@bank.az",
              "test.user1@example.com"],
}
FRAMES = {
    "IPV4_ADDRESS": ["Server ünvanı {} yazılıb.", "Server ünvanı {} yazılıb;", "Server ünvanı {} yazılıb",
                     "mənim ip {}", "Bağlantı {} ünvanından gəlib", "Server: {}\nPort: 443"],
    "IPV6_ADDRESS": ["Server IPv6-si {} yazılıb.", "Server IPv6-si {} yazılıb", "Logda IPv6 {} qeyd olunub;",
                     "mənim ipv6 {}"],
    "EMAIL": ["E-poçt ünvanı {} yazılıb.", "E-poçt ünvanı {} yazılıb", "mənim email {}", "Yazın: {};"],
}
TRACKS = ["R", "M"]


def found(preds: list[dict], s: int, e: int, label: str) -> bool:
    return any(p["start"] == s and p["end"] == e and p["label"] == label for p in preds)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    O, N = R.OLD, R.NEW
    out = {}
    for m in (O, N):
        eng = R.SB.Engine(*R.MODELS[m], "cpu", TRACKS)
        for lab, frames in FRAMES.items():
            for f in frames:
                for tr in TRACKS:
                    hit = 0
                    for v in VALUES[lab]:
                        t = f.format(v)
                        s = t.index(v)
                        hit += found(eng.run(tr, t), s, s + len(v), lab)
                    out[(m, tr, lab, f)] = hit
        del eng
    L = ["# IP addresses and emails in a line with and without a final period: exact spans found", "",
         "| label | frame | " + " | ".join(f"{m} {tr}" for tr in TRACKS for m in (O, N)) + " |",
         "|---|---|" + "---|" * 2 * len(TRACKS)]
    for lab, frames in FRAMES.items():
        n = len(VALUES[lab])
        for f in frames:
            L.append(f"| {lab} | `{f.replace(chr(10), ' ⏎ ')}` | "
                     + " | ".join(f"{out[(m, tr, lab, f)]}/{n}" for tr in TRACKS for m in (O, N)) + " |")
    (R.OUT / "linestop_frames.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(L))
