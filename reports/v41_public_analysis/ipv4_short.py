"""v4.1 analysis, H3: valid IPv4 addresses with one-digit octets
(8.8.8.8, 1.1.1.1, 10.0.0.1) against D-51h's look-alikes built from one-digit
octets (`9.9.9.999`, `1.2.3.x`). Tracks R and M, exact span, the pair in P4_PAIR.

    python reports/v41_public_analysis/ipv4_short.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import read_errors as R  # noqa: E402

GROUPS = {
    "4 one-digit octets": ["8.8.8.8", "1.1.1.1", "9.9.9.9", "4.2.2.2", "1.0.0.1", "8.8.4.4"],
    "3 one-digit octets": ["10.0.0.1", "10.1.1.5", "1.2.3.40", "8.8.8.53", "192.0.0.8", "4.2.2.25"],
    "2 one-digit octets": ["10.0.12.5", "172.16.0.9", "10.20.1.7", "192.168.0.5", "100.64.0.9", "10.8.0.33"],
    "no one-digit octet": ["10.12.44.201", "185.34.112.17", "192.168.10.45", "45.103.192.192", "172.16.20.12", "203.0.113.55"],
}
FRAMES = ["IP ünvanı: {}", "Serverin IP ünvanı {} olaraq qeyd olunub.", "Mənbə IP {} kimi göstərilib.",
          "DNS server kimi {} istifadə olunur.", "Bağlantı {} ünvanından gəlib."]
# the same sentences without the final period (chat lines, log lines): v4.1 splits IPv4 there
NO_STOP = [f[:-1] for f in FRAMES if f.endswith(".")]
TRACKS = ["R", "M"]
out = {}
O, N = R.OLD, R.NEW
for m in (O, N):
    eng = R.SB.Engine(*R.MODELS[m], "cpu", TRACKS)
    groups = list(GROUPS.items()) + [(g + ", no final period", v) for g, v in GROUPS.items()]
    for tr, (g, vals) in [(tr, x) for tr in TRACKS for x in groups]:
        n = hit = 0
        for f in (NO_STOP if g.endswith("period") else FRAMES):
            for v in vals:
                t = f.format(v)
                s = t.index(v)
                n += 1
                hit += any(p["start"] == s and p["end"] == s + len(v) and p["label"] == "IPV4_ADDRESS"
                           for p in eng.run(tr, t))
        out[(m, tr, g)] = (hit, n)
    del eng
L = ["# Valid IPv4 with one-digit octets: exact spans found (tracks R and M)", "",
     f"{len(FRAMES)} frames × 6 values per group; without the final period, {len(NO_STOP)} frames.", "",
     "| group | " + " | ".join(f"{m} {tr}" for tr in TRACKS for m in (O, N)) + " |", "|---|" + "---|" * 2 * len(TRACKS)]
L += [f"| {g} | " + " | ".join(f"{out[(m, tr, g)][0]}/{out[(m, tr, g)][1]}" for tr in TRACKS for m in (O, N)) + " |"
      for g in sorted({k for *_, k in out}, key=lambda k: (k.endswith("period"), list(GROUPS).index(k.split(",")[0])))]
(R.OUT / "ipv4_short.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
print("\n".join(L))
