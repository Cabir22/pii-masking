"""v4.1 analysis: what makes v4 miss a benchmark value that v3
finds? Each benchmark span from read_errors.py is re-run in variants that
change one thing at a time:

  doc            the whole benchmark document (as scored)
  sentence       only the sentence (or line) holding the value
  frame          the value in a frame the training data has (`IPv6 ünvanı X kimi göstərilib.`)
  value          the same sentence with another valid value of the same label
  frame+value    both

    python reports/v41_public_analysis/perturb.py --label IPV6_ADDRESS --label IPV4_ADDRESS --label EMAIL \
        [--controls 40] [--out reports/v41_public_analysis/out/perturb.md]

A variant counts as found when track R predicts the value's exact span with
its label. --controls adds that many spans both models find, as a check
that the variants themselves are fair. Needs the HF cache (HF_HUB_OFFLINE=1).
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import read_errors as R  # noqa: E402

SB = R.SB
FRAMES = {
    "IPV6_ADDRESS": "IPv6 ünvanı {} kimi göstərilib.",
    "IPV4_ADDRESS": "IP ünvanı: {}",
    "EMAIL": "E-poçt: {}",
}
SWAPS = {
    "IPV6_ADDRESS": ["fe80::1ff:fe23:4567:890a", "2a02:2c8:4:1::25", "2001:0db8:85a3:0000:0000:8a2e:0370:7334"],
    "IPV4_ADDRESS": ["10.12.4.201", "185.34.112.7", "192.168.1.45"],
    "EMAIL": ["leyla.aliyeva@gmail.com", "orxan_m@mail.ru", "info@azercell.az"],
}


def sentence(text: str, s: int, e: int) -> tuple[str, int]:
    """The sentence or line holding [s, e) -> (sentence, offset of s in it)."""
    a = max(text.rfind("\n", 0, s), max((m.end() for m in re.finditer(r"[.;!?]\s", text[:s])), default=0) - 1)
    a = a + 1
    m = re.search(r"[.;!?](\s|$)|\n", text[e:])
    b = e + (m.start() + 1 if m else len(text) - e)
    sent = text[a:b].strip()
    lead = len(text[a:b]) - len(text[a:b].lstrip())
    return sent, s - a - lead


def found(preds: list[dict], s: int, e: int, label: str) -> bool:
    return any(p["start"] == s and p["end"] == e and p["label"] == label for p in preds)


def variants(label: str, text: str, s: int, e: int, swap: str) -> dict[str, tuple[str, int, int]]:
    v = text[s:e]
    sent, off = sentence(text, s, e)
    fr = FRAMES[label]
    k = fr.index("{}")
    return {
        "doc": (text, s, e),
        "sentence": (sent, off, off + len(v)),
        "frame": (fr.format(v), k, k + len(v)),
        "value": (sent[:off] + swap + sent[off + len(v):], off, off + len(swap)),
        "frame+value": (fr.format(swap), k, k + len(swap)),
    }


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--label", action="append", required=True)
    ap.add_argument("--controls", type=int, default=40)
    ap.add_argument("--errors-dir", default=str(R.OUT))
    ap.add_argument("--out", default=str(R.OUT / "perturb.md"))
    a = ap.parse_args()
    O, N = R.OLD, R.NEW
    docs = {d["id"]: d for d in R.load_docs("benchmark")}
    rng = random.Random(20261017)
    cases = []  # (label, group, doc id, start, end, swap)
    for lab in a.label:
        res = json.loads((Path(a.errors_dir) / f"benchmark_R_{lab}.json").read_text(encoding="utf-8"))
        # chosen by the newer model's outcome only: the script runs the older one on every variant itself
        bad = {(i["id"], i["value"]) for i in res["items"] if i["outcomes"][N] != "exact"}
        good = []
        for d in docs.values():
            for g in d["gold"]:
                if g["label"] != lab:
                    continue
                key = (d["id"], d["text"][g["start"]:g["end"]])
                grp = f"{N} misses" if key in bad else None
                if grp:
                    cases.append((lab, grp, d["id"], g["start"], g["end"]))
                else:
                    good.append((lab, f"{N} finds (control)", d["id"], g["start"], g["end"]))
        cases += rng.sample(good, min(a.controls, len(good)))
    cases = [(*c, rng.choice(SWAPS[c[0]])) for c in cases]

    hits = collections.Counter()
    n = collections.Counter()
    for m, (model, sha) in R.MODELS.items():
        eng = SB.Engine(model, sha, "cpu", ["R"])
        for lab, grp, did, s, e, swap in cases:
            for vname, (text, vs, ve) in variants(lab, docs[did]["text"], s, e, swap).items():
                n[(m, lab, grp, vname)] += 1
                hits[(m, lab, grp, vname)] += found(eng.run("R", text), vs, ve, lab)
        del eng
    vnames = ["doc", "sentence", "frame", "value", "frame+value"]
    L = [f"# Perturbation test: exact spans found, {O} / {N} (track R)", "",
         "Variants change one thing at a time (see the script's docstring).", "",
         "| label | spans | n | " + " | ".join(vnames) + " |", "|---|---|---|" + "---|" * len(vnames)]
    for lab in a.label:
        for grp in (f"{N} misses", f"{N} finds (control)"):
            k0 = (N, lab, grp, "doc")
            if not n[k0]:
                continue
            cells = [f"{hits[(O, lab, grp, v)]} / {hits[(N, lab, grp, v)]}" for v in vnames]
            L.append(f"| {lab} | {grp} | {n[k0]} | " + " | ".join(cells) + " |")
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
