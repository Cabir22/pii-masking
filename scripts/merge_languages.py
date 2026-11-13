"""Stage 3.5: merge the per-language splits into `data/processed/merged/`.

`prepare_splits.py` writes the Azerbaijani source split to
`data/processed/az/` and each carrier translation to
`data/processed/{en,tr,ru}/` (re-tokenized in place by
`prepare_splits.py --tokenize-only`). This step produces the shuffled union
that `model/train.py` reads by default:

    data/processed/merged/{train,val,test}.docs.jsonl   char-span records
    data/processed/merged/{train,val,test}.jsonl        tokenized windows
    data/processed/merged/labels.json                   copied verbatim

Per language, `train` joins `train`, `val` joins `val`, `test` joins `test`
-- a record and its translation are always in the same split (translation is
done post-split precisely so a doc and its twin can never straddle
train/test), so this is a plain concatenation followed by a seeded shuffle.
The shuffle matters: `model/train.py --smoke-test` and `--max-train-samples`
slice with `.select(range(N))`, which must land a language-mixed sample.

`merged/` is a build artifact (git-ignored): it is byte-for-byte
reproducible from the committed per-language splits and this script's fixed
seed, and re-running it is the right move whenever any language's split
changes. Rebuild with:

    python scripts/merge_languages.py                # all languages present
    python scripts/merge_languages.py --langs az en  # only these
    python scripts/merge_languages.py --root data/processed/m1 --langs az en tr ru

Streams by byte offset (a multilingual build's windows don't fit in a laptop's
memory); the shuffle permutes the same list positions as before, so earlier
builds come out byte for byte the same.
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
from pathlib import Path

PROC = Path(__file__).resolve().parents[1] / "data" / "processed"
SPLITS = ("train", "val", "test")


def _offsets(path: Path) -> list[int]:
    """Byte offsets of the non-blank lines, so a split is never held in memory
    (a multilingual build's windows are several GB). Same lines, same order
    as reading the file with splitlines()."""
    if not path.exists():
        return []
    out, pos = [], 0
    with path.open("rb") as f:
        for line in f:
            if line.strip():
                out.append(pos)
            pos += len(line)
    return out


def _write(path: Path, rows: list[tuple[Path, int]]) -> None:
    """Writes the rows in the given order, LF line endings on every OS."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handles: dict[Path, object] = {}
    try:
        with path.open("wb") as out:
            for src, off in rows:
                fh = handles.get(src) or handles.setdefault(src, src.open("rb"))
                fh.seek(off)
                out.write(fh.readline().rstrip(b"\r\n") + b"\n")
    finally:
        for fh in handles.values():
            fh.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--langs", nargs="+", default=None,
                    help="languages to merge (default: every "
                         "data/processed/<lang>/ that has train.docs.jsonl)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--root", type=Path, default=PROC,
                    help="the folder holding <lang>/ (default data/processed)")
    ap.add_argument("--out", type=Path, default=None,
                    help="default: <root>/merged")
    args = ap.parse_args(argv)
    proc = args.root
    args.out = args.out or proc / "merged"

    if args.langs:
        langs = args.langs
    else:
        langs = sorted(d.name for d in proc.iterdir()
                       if d.is_dir() and (d / "train.docs.jsonl").exists()
                       and d.name != "merged")
    missing = [l for l in langs if not (proc / l / "train.docs.jsonl").exists()]
    if missing:
        print(f"error: no split for language(s): {missing}", file=sys.stderr)
        return 1
    print(f"merging: {', '.join(langs)}")

    for kind in ("docs.jsonl", "jsonl"):
        for split in SPLITS:
            rng = random.Random(f"{args.seed}|{split}|{kind}")
            rows: list[tuple[Path, int]] = []
            per_lang = {}
            for lang in langs:
                src = proc / lang / f"{split}.{kind}"
                got = _offsets(src)
                per_lang[lang] = len(got)
                rows.extend((src, off) for off in got)
            if not rows:
                print(f"  {split}.{kind}: nothing to merge (skipped)")
                continue
            rng.shuffle(rows)
            _write(args.out / f"{split}.{kind}", rows)
            counts = "  ".join(f"{l}={n:,}" for l, n in per_lang.items())
            print(f"  {split}.{kind}: {len(rows):,} rows   ({counts})")

    src_labels = None
    for lang in langs:
        cand = proc / lang / "labels.json"
        if cand.exists():
            src_labels = cand
            break
    src_labels = src_labels or (proc / "labels.json")
    if src_labels.exists():
        shutil.copy2(src_labels, args.out / "labels.json")
        print(f"  labels.json: copied from {src_labels}")
    else:
        print("  warning: no labels.json found to copy", file=sys.stderr)

    print(f"\nwrote {args.out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
