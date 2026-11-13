"""RT-2 -- invisible/zero-width character evasion of every regex/checksum
detector (16 of the 27 taxonomy labels).

A single zero-width space (U+200B), zero-width joiner (U+200D), or soft
hyphen (U+00AD) inserted inside a structured value breaks every
`SELF_SIGNALLING`/`ANCHORED` regex in `detect/patterns.py` and
`detect/anchored.py`, because none of the character classes used
(`[A-Za-z0-9._%+-]`, `\\d`, `\\w`, etc.) admit those code points, and the
value is never normalized/stripped before matching.

The character is invisible to a human reading the rendered document and is
typically ignored or silently merged by an LLM tokenizer, so the value
still reads as (and functions as) the same email/card/IBAN/phone/FIN to
anyone or anything downstream -- while being completely invisible to this
pipeline's detectors.

Confirmed end to end via the real `sanitize()` call, not just the
individual regexes.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness  # noqa: E402

harness.setup_paths()
harness.allow_unsafe_for_probes()
import pii_guard as pg  # noqa: E402
from pii_guard.detect import patterns, anchored  # noqa: E402

ZWSP = "​"
ZWJ = "‍"
SHY = "­"


def main() -> None:
    print("=== RT-2: invisible-character evasion of regex/checksum detectors ===\n")

    cases = [
        ("EMAIL", f"Contact us at john.smith{ZWSP}@example.com for help.",
         "Contact us at john.smith@example.com for help."),
        ("PAYMENT_CARD_NUMBER", f"Card on file: 4532{ZWSP}0151{ZWSP}1283{ZWSP}0366.",
         "Card on file: 4532 0151 1283 0366."),
        ("IBAN", f"IBAN: AZ21NABZ{ZWJ}00000000137010001944.",
         "IBAN: AZ21NABZ00000000137010001944."),
        ("TELEPHONENUM", f"Telefon: +994{SHY}50{SHY}987{SHY}65{SHY}43",
         "Telefon: +994 50 987 65 43"),
        ("AZ_FIN", f"FİN kod: 7YAX{ZWSP}L2Z", "FİN kod: 7YAXL2Z"),
    ]

    print("--- per-regex proof (patterns.py + anchored.py directly) ---")
    for label, poisoned, clean in cases:
        got_poisoned = patterns.detect(poisoned, frozenset({label})) + \
                      anchored.detect(poisoned, frozenset({label}))
        got_clean = patterns.detect(clean, frozenset({label})) + \
                   anchored.detect(clean, frozenset({label}))
        evades = not got_poisoned and got_clean
        print(f"  {label:20s} clean={bool(got_clean)!s:5s} "
             f"invisible-char copy={bool(got_poisoned)!s:5s}  "
             f"{'EVADES' if evades else ''}")

    print("\n--- end to end through the real sanitize() call ---")
    cfg = pg.GuardConfig(require_ml_context=False)  # this attack targets the
                                                     # regex tier; skip loading
                                                     # the transformer for speed
    doc = (f"Please charge card 4532{ZWSP}0151{ZWSP}1283{ZWSP}0366 and confirm "
          f"by emailing john.smith{ZWSP}@example.com for the refund.")
    r = pg.sanitize(doc, cfg)
    print(f"Sanitized text: {r.text!r}")
    print(f"Vault entries: {len(r.vault)}")
    print(f"Card number still present verbatim in output: "
         f"{'4532' + ZWSP + '0151' + ZWSP + '1283' + ZWSP + '0366' in r.text}")
    print("sanitize() returned normally -- no SanitizationFailed raised.")


if __name__ == "__main__":
    main()
