"""D-40b: apply the gender marks for the names in both given-name pools.

`scripts/piigen/locales/data/shared_name_genders.tsv` (name, decision,
draft_guess) marks each of the 233 names in both az_first_names_m.txt and
az_first_names_f.txt:

  F     a woman's name only -> removed from the men's pool
  M     a man's name only   -> removed from the women's pool
  both  really used for both -> kept in both
  open  not decided yet      -> kept in both (draft_guess is NOT applied)

Plus MOVES: a name in the wrong pool only (`Hürrü`, a woman's name only in
the men's pool) goes to the other one.

Deterministic and idempotent: lines are removed in place (file order
kept), a moved name is inserted in sorted position, and a name already
where it belongs is left alone. When the team decides the open names,
only the TSV changes; rerun this script.

    python scripts/piigen/locales/apply_shared_name_genders.py [--check]

The frozen pii_guard gazetteer reads the UNION of the two pools
(pii_guard/detect/names.py), which this never changes: every removed name
stays in the other pool.
"""
from __future__ import annotations

import argparse
import csv
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = Path(__file__).resolve().parent / "data"
POOLS = {"m": DATA / "az_first_names_m.txt", "f": DATA / "az_first_names_f.txt"}
TSV = DATA / "shared_name_genders.tsv"
MOVES = {"Hürrü": ("m", "f")}       # name: (from pool, to pool)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s.strip())


def read(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tsv", type=Path, default=TSV)
    ap.add_argument("--check", action="store_true", help="report only, write nothing")
    args = ap.parse_args(argv)

    rows = list(csv.DictReader(args.tsv.open(encoding="utf-8-sig"), delimiter="\t"))
    lines = {k: read(p) for k, p in POOLS.items()}
    names = {k: {nfc(x) for x in v} for k, v in lines.items()}
    drop = {"m": set(), "f": set()}
    problems = []
    for r in rows:
        name, decision = nfc(r["name"]), r["decision"].strip()
        if decision not in ("F", "M", "both", "open"):
            problems.append(f"{name}: unknown decision {decision!r}")
            continue
        in_m, in_f = name in names["m"], name in names["f"]
        if decision == "F":
            if not in_f:
                problems.append(f"{name}: marked F but not in the women's pool")
            if in_m:
                drop["m"].add(name)
        elif decision == "M":
            if not in_m:
                problems.append(f"{name}: marked M but not in the men's pool")
            if in_f:
                drop["f"].add(name)
    add = {"m": [], "f": []}
    for name, (src, dst) in MOVES.items():
        if name in names[src]:
            drop[src].add(name)
        if name not in names[dst]:
            add[dst].append(name)
    if problems:
        print("\n".join("problem: " + p for p in problems))
        return 1

    for k in ("m", "f"):
        kept = [x for x in lines[k] if nfc(x) not in drop[k]]
        for name in add[k]:
            at = next((i for i, x in enumerate(kept) if nfc(x) > name), len(kept))
            kept.insert(at, name)
        removed = len(lines[k]) - len(kept) + len(add[k])
        print(f"{POOLS[k].name}: {len(lines[k]):,} -> {len(kept):,} lines "
              f"({removed} removed, {len(add[k])} added: {', '.join(add[k]) or '-'})")
        if not args.check and kept != lines[k]:
            POOLS[k].write_text("\n".join(kept) + "\n", encoding="utf-8", newline="")
    decided = {d: sum(r["decision"].strip() == d for r in rows) for d in ("F", "M", "both", "open")}
    print(f"marks: {decided}" + ("  (check only, nothing written)" if args.check else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
