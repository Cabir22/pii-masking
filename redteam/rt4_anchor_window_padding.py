"""RT-4 -- anchor-window evasion via ordinary sentence padding.

The five `anchor_required` labels (DATE/TIME/AGE/BUILDINGNUM/
CARD_SECURITY_CODE) are only masked if a licensing word sits within 80
characters (`ANCHOR_WINDOW` / `WINDOW`), measured via `cue_window`, which
clips at a sentence boundary or segment break -- but NOT at any smaller
unit. A single ordinary sentence with enough clauses between the cue word
and the value pushes the value outside that 80-character budget while
staying completely unremarkable as writing: no adversarial trick, no
unusual punctuation, nothing an editor would flag.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness  # noqa: E402

harness.setup_paths()
harness.allow_unsafe_for_probes()
import pii_guard as pg  # noqa: E402


def main() -> None:
    print("=== RT-4: pushing a licensing word out of the 80-char anchor window ===\n")
    cfg = pg.GuardConfig(require_ml_context=False)

    base = "Security code: 482. Charge approved."
    padded = ("Security code: this transaction was manually reviewed and "
             "verified by our fraud team before being finally approved as "
             "482. Charge approved.")
    for label, text in [("unpadded (39 chars to value)", base),
                        ("padded, same sentence, ordinary prose", padded)]:
        r = pg.sanitize(text, cfg)
        print(f"  {label}")
        print(f"    masked={len(r.vault) > 0}   {text!r}\n")


if __name__ == "__main__":
    main()
