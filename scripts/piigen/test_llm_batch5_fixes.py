"""Fixes from the LLM batch-5 audit (P2-5, batch 5).

No network, no model, no API key.

    python scripts/piigen/test_llm_batch5_fixes.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.llm.quality import find_invented_pii  # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond: bool, msg: str, detail=None) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(msg + (f"  [{detail!r}]"[:300] if detail is not None else ""))


def streets(text: str, entities=()) -> list[str]:
    return [f["text"] for f in find_invented_pii(text, list(entities)) if f["label"] == "STREET"]


def test_folded_streets() -> None:
    """An invented street written without Azerbaijani letters or misspelt is
    still an invented street (batch 5: `Nizami küçesi`, `Serhed kucesi`)."""
    for word in ("küçəsi", "küçesi", "kucesi", "kuçesi", "kücesi", "kuçəsi", "küçəsində",
                 "kucesinde", "prospekti", "prospekti̇", "prospektı", "döngəsi", "dongesi",
                 "küç.", "kuc.", "pr."):
        found = streets(f"Ünvan: Nizami {word}, bina yoxdur.")
        check(found and found[0].startswith("Nizami"), f"unlabelled 'Nizami {word}' is caught", found)
    # labelled, the same strings are not findings
    text = "Ünvan: Nizami kucesi, ev."
    s = text.index("Nizami")
    check(not streets(text, [{"start": s, "end": s + len("Nizami kucesi"), "label": "STREET"}]),
          "a labelled folded street is not a finding")
    # words that only look like the suffix are not streets
    for text in ("Kucə itləri haqqında yazı.", "Bu Kəsik yoldur.", "Problem Prosesi başladı."):
        check(not streets(text), f"no street in {text!r}", streets(text))


def test_homograph_full_names() -> None:
    """A homograph given name (`Murad` = wish, `Qurban` = sacrifice, `Ümid` =
    hope) before a surname is a full name: the homograph list (P4-2) must not
    hide it (3 such invented names were back in batch 1's clean file)."""
    for name in ("Murad Məmmədov", "Qurban Adilov", "Murad Hüseynov", "Ümid Əliyev"):
        found = [f["text"] for f in find_invented_pii(f"Hörmətlə, {name}.", [])]
        check(name in found, f"unlabelled {name!r} is caught", found)
    for text in ("Ümid edirəm ki, gələcək.", "Murad hasil oldu."):
        check(not find_invented_pii(text, []), f"no name in {text!r}")


TESTS = [("folded and misspelt invented streets", test_folded_streets),
         ("homograph given names before a surname", test_homograph_full_names)]

if __name__ == "__main__":
    for name, fn in TESTS:
        print(name)
        fn()
    print("=" * 60)
    print(f"PASSED {PASS}   FAILED {FAIL}")
    print("=" * 60)
    for f in FAILURES:
        print("  FAIL:", f)
    sys.exit(1 if FAIL else 0)
