"""RT-1 -- Unicode normalization blind spot in the fail-closed self-check.

`_assert_clean` (pipeline.py) and `assert_no_raw_pii` both call
`logging_.value_present(text, value)`, a bare regex substring search with NO
Unicode normalization. `mask.py`'s own coreference key (`_norm_key`) DOES
call `unicodedata.normalize("NFKC", ...)` -- the project already knows
normalization drift is real for this text (Azerbaijani/Turkish/Russian all
use combining diacritics) and defends against it in exactly one of the
three places it matters.

Two code points sequences can render IDENTICALLY (NFC precomposed vs. NFD
decomposed) while being byte-different strings. This probe shows:
  1. the safety-net functions themselves are provably blind to this (pure
     code, no model needed) -- CONFIRMED.
  2. whether that gap has a live target in practice, i.e. whether the real
     detector + `_propagate_strong_mentions` ever leave a decomposed
     duplicate undetected in the first place -- tested end to end for
     GIVENNAME/SURNAME/CITY/STREET; NOT reproduced, because the model's
     SentencePiece tokenizer has its own Precompiled normalizer that folds
     NFD back to NFC-equivalent internally (confirmed separately: see the
     README). That protection is incidental to a tokenizer choice, not a
     deliberate design decision -- it is not guaranteed to survive a future
     checkpoint or tokenizer swap.
"""
from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness  # noqa: E402

harness.setup_paths()
import pii_guard as pg  # noqa: E402
from pii_guard.logging_ import value_present  # noqa: E402
from pii_guard.vault import Vault  # noqa: E402
from pii_guard.pipeline import assert_no_raw_pii, SanitizationFailed  # noqa: E402


def main() -> None:
    print("=== RT-1: Unicode normalization bypass of the fail-closed self-check ===\n")

    name = "Rəşad Əliyev"
    nfc, nfd = unicodedata.normalize("NFC", name), unicodedata.normalize("NFD", name)
    assert nfc.encode("utf-8") != nfd.encode("utf-8")
    print(f"NFC bytes: {nfc.encode('utf-8')}")
    print(f"NFD bytes: {nfd.encode('utf-8')}  (renders identically, different bytes)\n")

    print("--- 1. direct proof against the real safety-net functions ---")
    v = Vault()
    v.put("[PERSON_001]", nfc)
    forged_text = f"[PERSON_001] confirmed the order. Follow-up handled by {nfd}."
    caught = value_present(forged_text, nfc)
    print(f"value_present(text, vault_value) [what _assert_clean checks]: {caught}")
    payload = {"model": "x", "messages": [{"role": "user", "content": forged_text}]}
    try:
        assert_no_raw_pii(payload, v)
        print("assert_no_raw_pii: PASSED (did not raise) -- treated as clean")
    except SanitizationFailed as e:
        print(f"assert_no_raw_pii: raised ({e})")

    print("\n--- 2. does a live document ever hand this gap a real target? ---")
    cfg = pg.GuardConfig(ner_model=harness.MODEL_ID)
    print("loading model...")
    for base in ["Rəşad Əliyev", "Elvin Məmmədov", "Poladxan Quliyev"]:
        nfc_b, nfd_b = unicodedata.normalize("NFC", base), unicodedata.normalize("NFD", base)
        doc = (f"Müştəri: {nfc_b}. Sənəd təsdiqləndi.\n\n"
              f"Arxiv qeydi. Kod: 88213. {nfd_b}. Bitti.")
        r = pg.sanitize(doc, cfg)
        leaked = nfd_b in r.text
        print(f"  {base!r}: NFD duplicate leaked end-to-end = {leaked}")

    print("\n=== verdict ===")
    print("Safety-net functions: CONFIRMED blind to Unicode normalization (part 1).")
    print("Live exploitation via ml_context labels: NOT reproduced -- the model's")
    print("tokenizer normalizer incidentally closes it today. The underlying gap")
    print("in the LAST line of defense is real regardless of what currently")
    print("happens to sit in front of it.")


if __name__ == "__main__":
    main()
