"""Every date style each language's date builder emits is licensed by that
language's anchor check on its own, with no context word (19 Oct 2026).

A style the check does not self-license fails `missing_anchor` whenever no
`tarih`/`date`/`дата` word happens to sit within 80 characters, and the
translation harness then drops the document. The Russian run lost 4.5% of
its documents to this (2026-09-07); Turkish `21. Şubat 1956`
was the same gap (321 of 5,000 dates).

    python scripts/translate/test_date_anchors.py
"""
from __future__ import annotations

import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen import anchors as AZ_ANCHORS  # noqa: E402
from piigen.locales import LOCALES  # noqa: E402
from translate.lang import ANCHORS  # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond: bool, msg: str, detail=None) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(msg + (f"  [{detail!r}]"[:300] if detail is not None else ""))


def main() -> int:
    for lang in ("az", "en", "tr", "ru"):
        anchors = AZ_ANCHORS if lang == "az" else ANCHORS[lang]
        r = random.Random(9)
        bad = []
        for _ in range(5000):
            v = LOCALES[lang].date_builder(r.randint(1, 28), r.randint(1, 12), r.randint(1950, 2035), r)
            if not anchors.has_anchor("DATE", v, 0, len(v)):
                bad.append(v)
        check(not bad, f"{lang}: every date style is licensed on its own", bad[:3])
    tr = ANCHORS["tr"]
    for v in ("21. Şubat 1956", "3. Ağu 2024", "21. Subat 1956", "Pazartesi, 21. Şubat 1956"):
        check(tr.has_anchor("DATE", v, 0, len(v)), f"tr: {v!r} is licensed")
    for v in ("3. sınıf 2019", "5. kat 2024", "12. madde 1990"):
        check(not tr.has_anchor("DATE", v, 0, len(v)), f"tr: {v!r} is not a date shape")
    print(f"PASSED {PASS}   FAILED {FAIL}")
    for f in FAILURES:
        print("  FAIL:", f)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
