"""RT-5 -- what actually happens when a detector tier raises under strict=False.

`strict=False` is documented as "a development convenience" and is itself
gated behind `PII_GUARD_ALLOW_UNSAFE=1` outside production (config.py's
`_enforce_safety`), so this is not a bypass of that gate -- it verifies the
gate is exactly as unsafe as its name says, and measures the blast radius
precisely: `HybridDetector.detect()` wraps each tier in try/except, and
under strict=False a raised exception is silently swallowed with NO log,
NO warning, and the tier's `found.extend(fn())` call simply contributes
nothing. Because `detect/anchored.py`'s single `detect()` function handles
ALL FIVE `anchor_required` labels, one exception in it drops DATE, TIME,
AGE, BUILDINGNUM and CARD_SECURITY_CODE for the entire document in one
shot, and `sanitize()` returns as if nothing happened.
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
    print("=== RT-5: strict=False silently drops an entire detector tier ===\n")

    from pii_guard.detect import anchored as anchored_mod

    def _boom(text, labels=None):
        raise RuntimeError("simulated detector failure (malformed input, a "
                           "missing dependency, a regex blowup -- exactly "
                           "what 'strict' exists to catch)")

    orig = anchored_mod.detect
    anchored_mod.detect = _boom
    try:
        doc = "CVV 482 was charged. Invoice 2026-09-01. Age 34."
        for strict in (True, False):
            cfg = pg.GuardConfig(require_ml_context=False, strict=strict)
            try:
                r = pg.sanitize(doc, cfg)
                print(f"  strict={strict!s:5s} -> returned normally, "
                     f"{len(r.vault)} entries masked. text={r.text!r}")
            except pg.pipeline.SanitizationFailed:
                print(f"  strict={strict!s:5s} -> raised SanitizationFailed "
                     f"(aborted, as designed)")
    finally:
        anchored_mod.detect = orig

    print("\nCVV, invoice date and age -- all five anchor_required labels --")
    print("ship completely unmasked under strict=False, with zero signal that")
    print("anything degraded. A warning log on tier skip would cost little and")
    print("give an operator SOMETHING to notice before the fact.")


if __name__ == "__main__":
    main()
