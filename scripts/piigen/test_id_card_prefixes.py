"""D-51h: an ID card is any two capital letters + 7 digits (or DYI/MYI + 7),
in every place that recognises one -- the validators, the product's regex
fallback, pii_guard and the LLM leak detector. A driver licence stays two
letters + 6, so the length tells them apart.

    python scripts/piigen/test_id_card_prefixes.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "model"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen import checksums as CK  # noqa: E402
from piigen.llm.quality import find_leaked_pii  # noqa: E402
from piigen.validate import value_valid  # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond: bool, msg: str, detail=None) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(msg + (f"  [{detail!r}]"[:300] if detail is not None else ""))


IDS = ["AA1234567", "AB7654321", "KT3071958", "ZX0000001", "DYI1234567", "MYI7654321"]
NOT_IDS = ["AB123456",            # a licence: 2 + 6
           "AB12345678",          # 2 + 8
           "A12345678",           # a passport: 1 + 8
           "ABC1234567",          # 3 letters (an order number, D-51h)
           "AB-1234567", "1234567"]


def test_validators() -> None:
    for v in IDS:
        check(CK.az_id_card_valid(v), "checksums: an ID card", v)
        check(value_valid("AZ_ID_CARD_NUMBER", v)[0], "validate: an ID card", v)
    for v in NOT_IDS:
        check(not CK.az_id_card_valid(v), "checksums: not an ID card", v)
        check(not value_valid("AZ_ID_CARD_NUMBER", v)[0], "validate: not an ID card", v)
    check(CK.az_driver_license_valid("BA154675") and not CK.az_driver_license_valid("BA1546751"),
          "a licence is 2 + 6, never 2 + 7")


def test_fallback() -> None:
    from pattern_fallback import find_pattern_spans
    text = "Sənəd KT3071958, vəsiqə AA1234567, sürücülük vəsiqəsi BA154675, sifariş ABC1234567."
    found = {(s["label"], s["text"]) for s in find_pattern_spans(text)}
    check(("AZ_ID_CARD_NUMBER", "KT3071958") in found and ("AZ_ID_CARD_NUMBER", "AA1234567") in found,
          "the fallback finds ID cards with any two-letter prefix", found)
    check(("AZ_DRIVER_LICENSE_NUMBER", "BA154675") in found, "the licence is still a licence", found)
    check(not any(t.startswith("ABC") or t.endswith("BC1234567") for _l, t in found),
          "three letters + 7 digits is no ID card", found)


def test_pii_guard() -> None:
    from pii_guard.detect.patterns import detect

    def ids(t: str) -> list[str]:
        return [t[d.start:d.end] for d in detect(t) if d.label == "AZ_ID_CARD_NUMBER"]
    check(ids("Şəxsiyyət vəsiqəsinin nömrəsi KT3071958 göstərilib.") == ["KT3071958"],
          "pii_guard: another prefix next to an ID-card word")
    check(ids("Sifariş kodu KT3071958 qeydə alındı.") == [],
          "pii_guard: another prefix with no ID-card word is left alone")
    check(ids("Sənəd AA1234567 qəbul edildi.") == ["AA1234567"],
          "pii_guard: AA/AB/DYI/MYI still on sight")
    # next to an ID-card word both tiers match AA1234567: reported once
    check(ids("Vəsiqə AA1234567") == ["AA1234567"], "pii_guard: a known prefix next to an "
          "ID-card word is reported once, not by both tiers", ids("Vəsiqə AA1234567"))
    d = [x for x in detect("Vəsiqə AA1234567") if x.label == "AZ_ID_CARD_NUMBER"]
    check(len(d) == 1 and d[0].source == "pattern", "the unanchored tier keeps it", d)


def test_leak_detector() -> None:
    def leaks(t: str) -> list[str]:
        return [x for x in find_leaked_pii(t, []) if x.startswith("AZ_ID_CARD_NUMBER")]
    check(leaks("Şəxsiyyət vəsiqəsinin nömrəsi KT3071958 göstərilib."),
          "leak detector: an unlabelled ID card with another prefix next to an ID-card word")
    check(not leaks("Sifariş kodu KT3071958 qeydə alındı."),
          "leak detector: another prefix with no ID-card word is no leak")
    check(leaks("Sifariş AA1234567 qeydə alındı."),
          "leak detector: AA/AB/DYI/MYI still flagged on sight, with no anchor word")
    # the anchor check applies to the anchored tier only: before, adding an
    # anchor word for a kind made its unanchored tier need one too
    check(leaks("Müraciət DYI1234567 qeydə alındı."), "leak detector: DYI on sight")


TESTS = [("validators", test_validators), ("regex fallback", test_fallback),
         ("pii_guard", test_pii_guard), ("LLM leak detector", test_leak_detector)]

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
