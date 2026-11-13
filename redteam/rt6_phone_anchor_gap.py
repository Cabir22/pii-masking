"""RT-6 -- the TELEPHONENUM anchor vocabulary misses ordinary English phrasing.

Found by accident while building RT-3 (a first draft used "call the
customer at ..." and the phone number came out unmasked with no attacker
intent at all). `ANCHOR_WORDS["TELEPHONENUM"]` requires "call\\s*(?:me|us|
now)" specifically -- not "call THE CUSTOMER", "call HIM", "reach ... at",
or "dial ...". None of these four sentences involve any adversarial
trick; they are just ordinary ways to write about a phone number.
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
    print("=== RT-6: ordinary phone phrasing the anchor vocabulary doesn't know ===\n")
    cfg = pg.GuardConfig(require_ml_context=False)

    sentences = [
        "Please call the customer at +994 50 987 65 43 to confirm.",
        "Reach him at +994 50 987 65 43 before noon.",
        "You can dial +994 50 987 65 43 for support.",
        "His number is +994 50 987 65 43.",
    ]
    for text in sentences:
        r = pg.sanitize(text, cfg)
        print(f"  masked={len(r.vault) > 0!s:5s}  {text!r}")


if __name__ == "__main__":
    main()
