"""RT-3 -- vault/placeholder confusion via literal placeholder-shaped text.

Placeholders are `[{family}_{n:03d}]` by default and are assigned
deterministically, in order of first appearance (mask.py's own docstring).
A document containing LITERAL text of that exact shape -- entirely
plausible in real business writing (a ticket/reference/case number: "see
ticket [REF_001]") -- is not itself PII, so nothing detects or masks it. It
survives into the "sanitised" text verbatim, byte-identical to a real
placeholder, because `mask.py::rehydrate` does not distinguish "a
placeholder this pipeline emitted" from "text that merely looks like one":
it does a blind `out.replace(placeholder, value)` for every placeholder
string found anywhere in the response.

Impact is bounded (this is local-only substitution, not a network leak --
the caller already possesses the true value), but it is a real integrity
bug: a real person's real PII can be forged into a sentence the source
document never actually associated them with, driven entirely by
attacker-chosen literal text that happens to share the placeholder's shape.
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
    print("=== RT-3: placeholder-shaped literal text forges real PII into unrelated text ===\n")
    cfg = pg.GuardConfig(require_ml_context=False)

    doc = ("Telefon: +994 50 987 65 43.\n\n"
          "Internal note: this case was already escalated once, see prior "
          "ticket [PHONE_001] for the original complaint history.")
    r = pg.sanitize(doc, cfg)
    print(f"Sanitized text sent externally:\n  {r.text!r}\n")
    print(f"Vault: {[(p, r.vault.reveal(p)) for p in r.vault.placeholders()]}\n")

    # A plausible foreign-LLM response: it saw "[PHONE_001]" twice (once as
    # the real masked value, once as the attacker's literal reference text)
    # and echoes the token back for both, as models routinely do.
    foreign_llm_response = (
        "The customer's contact [PHONE_001] was confirmed. Regarding the "
        "earlier ticket [PHONE_001] you referenced, no additional complaint "
        "is on file for it.")
    rehydrated = pg.rehydrate(foreign_llm_response, r.vault)
    print(f"Rehydrated response returned to the user:\n  {rehydrated!r}\n")
    print("Every occurrence of the placeholder string was replaced blindly --")
    print("including the one that was never about the real phone number. The")
    print("real number now appears attached to a 'prior ticket' sentence the")
    print("source document never associated with it.")


if __name__ == "__main__":
    main()
