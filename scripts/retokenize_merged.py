# -*- coding: utf-8 -*-
"""Re-tokenize merged_rebalanced/ splits after name substitution.

Thin wrapper around `scripts/prepare_splits.py --tokenize-only`, which is the
ONE canonical tokenizer path in this repo. Do not re-implement tokenization
here.

History: the first version of this script hard-coded
`TOKENIZER_NAME = "bert-base-multilingual-uncased"` (comment claimed it was
copied from prepare_splits.py -- it was not; prepare_splits uses
`xlm-roberta-base`), a flat 35-entry label list that never existed in this
project (`AZ_CITY`, `EN_EMAIL`, ... instead of the 55-label BIO taxonomy),
no B-/I- distinction, no -100 masking on special tokens, no punctuation-
boundary pre-tokenizer patch, and stride 128 instead of 256. Every
`merged_rebalanced/*.jsonl` it produced was unusable with
`model/train.py --model FacebookAI/xlm-roberta-large` -- wrong vocab, wrong
labels. Replaced 2026-09-10 after a verification pass.

Usage:
    python scripts/retokenize_merged.py [--splits train val test]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REBALANCED = REPO / "data" / "processed" / "merged_rebalanced"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--splits", nargs="+", default=["train", "val", "test"],
                    choices=["train", "val", "test"])
    args = ap.parse_args()

    docs = [REBALANCED / f"{s}.docs.jsonl" for s in args.splits]
    missing = [p for p in docs if not p.exists()]
    if missing:
        print(f"error: not found: {missing}\n"
              f"run scripts/substitute_names.py first.", file=sys.stderr)
        return 1

    sys.path.insert(0, str(Path(__file__).parent))
    from prepare_splits import main as prepare_main

    argv = ["--tokenize-only", *map(str, docs)]
    print(f"delegating to: prepare_splits.py {' '.join(argv)}", file=sys.stderr)
    return prepare_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
