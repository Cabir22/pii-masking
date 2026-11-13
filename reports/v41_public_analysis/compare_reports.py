"""v4.1 analysis: the numbers of the v4 -> v4.1 note from two
models' scoreboard reports (track R, or --track M): benchmark F1 overall and per label,
C3 and C4 as release_check computes them (C4 per family, policy kinds left
out), and the key labels on the benchmark and in the key probe families.

    python reports/v41_public_analysis/compare_reports.py \
        v4=<bench.json>,<probes.json> v4.1=<bench.json>,<probes.json> [...] [--track M] [--out .../compare_reports.md]

Reports from eval/scoreboard.py (older model first). Benchmark and probe
values are public (task sheet, rule 3).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval"))
import release_check as RC  # noqa: E402

LABELS = ["IPV4_ADDRESS", "IPV6_ADDRESS", "EMAIL", "TIME", "ZIPCODE", "AZ_ID_CARD_NUMBER",
          "AZ_DRIVER_LICENSE_NUMBER", "PRIVATE_KEY", "API_KEY", "ACCESS_TOKEN"]
KEY_FAMILIES = ["pem", "token_vs_key", "contrast_token_key"]
KEY_LABELS = ["PRIVATE_KEY", "API_KEY", "ACCESS_TOKEN"]


def merged(paths: str) -> dict:
    rep = {"sets": {}}
    for p in paths.split(","):
        rep["sets"].update(RC.load(p)["sets"])
    return rep


def c4(rep: dict, fam: str, track: str = "R") -> tuple[int, int]:
    """(triggered, look-alikes) of one decoy family, policy kinds left out (as RC.probe_rules)."""
    dec = RC.tr(rep, "probes", track)["per_family"][fam]["decoys"]
    excl = set(next((c.get("exclude_kinds", []) for c, *_ in RC.family_rows(rep, rep, fam, track)), []))
    n = dec["overall"]["decoys"] - sum(v["decoys"] for k, v in dec["per_kind"].items() if k in excl)
    hit = dec["overall"]["triggered_same_label"] - sum(v["triggered_same_label"] for k, v in dec["per_kind"].items() if k in excl)
    return hit, n


def f1(block: dict, lab: str | None = None) -> str:
    m = block["exact"]["micro"] if lab is None else block["exact"]["per_label"].get(lab)
    return "–" if not m else f"{100 * m['f1']:.1f} (P {100 * m['precision']:.1f}, R {100 * m['recall']:.1f})"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("reports", nargs="+", help="name=bench.json,probes.json, older first")
    ap.add_argument("--track", default="R")
    ap.add_argument("--out", default=str(Path(__file__).parent / "out_v41" / "compare_reports.md"))
    a = ap.parse_args()
    reps = {n: merged(p) for n, p in (r.split("=", 1) for r in a.reports)}
    names = list(reps)
    head = "| | " + " | ".join(names) + " |"
    rule = "|---|" + "---|" * len(names)
    t = a.track
    L = [f"# {' -> '.join(names)} from the scoreboard reports (track {t}, exact spans)", "", "## Benchmark", "", head, rule]
    L.append("| all labels, policy items left out | " + " | ".join(f1(RC.tr(r, "benchmark", t)["excl_policy"]) for r in reps.values()) + " |")
    L.append("| all labels, with the policy items | " + " | ".join(f1(RC.tr(r, "benchmark", t)["all"]) for r in reps.values()) + " |")
    for lab in LABELS:
        L.append(f"| {lab} | " + " | ".join(f1(RC.tr(r, "benchmark", t)["all"], lab) for r in reps.values()) + " |")

    L += ["", "## C3 (licence_vs_id + contrast_licence_id)", "", "| condition | " + " | ".join(names) + " |", rule]
    for fam in ("licence_vs_id", "contrast_licence_id"):
        rows = {n: RC.family_rows(r, r, fam, t) for n, r in reps.items()}
        for i, (c, *_) in enumerate(rows[names[0]]):
            L.append(f"| {fam} {RC.cond_name(c)} {c['op']} {c.get('value', '')} | "
                     + " | ".join(RC.pct(rows[n][i][1]) for n in names) + " |")

    L += ["", "## C4 (look-alikes masked with the label they resemble, policy kinds left out)", "",
          "| family | " + " | ".join(names) + " |", rule]
    tot = {n: [0, 0] for n in names}
    for fam in RC.DECOY_FAMILIES:
        cells = []
        for n, r in reps.items():
            hit, k = c4(r, fam, t)
            tot[n][0] += hit
            tot[n][1] += k
            cells.append(f"{RC.pct(hit / k if k else None)}% ({hit}/{k})")
        L.append(f"| {fam} | " + " | ".join(cells) + " |")
    L.append("| **overall** | " + " | ".join(f"**{RC.pct(h / k)}%** ({h}/{k})" for h, k in tot.values()) + " |")

    L += ["", "## Key probe families (exact F1 per label)", "", "| family | label | " + " | ".join(names) + " |",
          "|---|---|" + "---|" * len(names)]
    for fam in KEY_FAMILIES:
        for lab in KEY_LABELS:
            blocks = [RC.tr(r, "probes", t)["per_family"][fam] for r in reps.values()]
            if all(lab not in b["exact"]["per_label"] for b in blocks):
                continue
            L.append(f"| {fam} | {lab} | " + " | ".join(f1(b, lab) for b in blocks) + " |")
        L.append(f"| {fam} | split spans | " + " | ".join(
            str(RC.tr(r, "probes", t)["per_family"][fam]["recall"]["split"]) for r in reps.values()) + " |")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
