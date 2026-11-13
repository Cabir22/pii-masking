"""P4-2 check: the homograph list (homographs_az.py) meets the task's rules.

No network, no model.

    python scripts/piigen/targeted/test_homographs.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from piigen.targeted import builder as B                 # noqa: E402
from piigen.targeted import homographs_az as H            # noqa: E402
from piigen.targeted import suffix as SFX                 # noqa: E402
from piigen.validate import _WORD_RE, language_evidence   # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond: bool, msg: str, detail=None) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(msg + (f"  [{detail!r}]"[:300] if detail is not None else ""))


def az_lower(s: str) -> str:
    return s.replace("İ", "i").replace("I", "ı").lower()


def stray_capitals(before: str, after: str) -> list[str]:
    """Capitalised words that do not start a sentence: another name or place
    (other PII). `before` starts the sentence; `after` follows the marker."""
    out = []
    for seg, starts in ((before, True), (after, False)):
        for m in re.finditer(r"\w+", seg):
            prefix = seg[:m.start()]
            if m.group()[0].isupper() and not (starts and not prefix.strip()) \
                    and not re.search(r"[.!?]\s+$", prefix):
                out.append(m.group())
    return out


def test_list() -> None:
    lib = B.HomographLibrary(H)       # markers parse, each side is marked as itself
    check(lib.source == "homographs_az", "the builder loads the file, not the stub")
    # test_short_homograph's 2000-document build has 100 homograph documents
    # and needs every name in one of them
    check(50 <= len(lib.entries) <= 100, f"50-100 names ({len(lib.entries)})")
    check(lib.lone_names == sorted(H.HOMOGRAPHS) and all(n[:1].isupper() for n in lib.lone_names),
          "D-10: LONE_NAMES are the names, capitalised")
    check(lib.lone_words == sorted(az_lower(n) for n in H.HOMOGRAPHS)
          and not any("̇" in w for w in lib.lone_words), "D-10: LONE_WORDS are the words, lowercase (İ -> i)")
    seen: dict[str, str] = {}
    for name, e in H.HOMOGRAPHS.items():
        check(e.get("gender") in ("f", "m"), f"{name}: gender f or m")
        check(all(isinstance(e.get(k), str) and e[k].strip() for k in ("az", "en")), f"{name}: az and en meanings")
        for side in ("name", "word"):
            items = lib.entries[name][side]
            check(len(items) >= 3, f"{name}: >= 3 {side} sentences")
            check(any(before == "" for _f, before, _w, _a in items), f"{name}: a sentence-initial {side} use")
            check(any(az_lower(word) != az_lower(name) for _f, _b, word, _a in items),
                  f"{name}: an inflected {side} use")
            for (_f, before, word, after), raw in zip(items, e[side]):
                rest = before + after
                check(raw not in seen, f"{name}: the sentence is not used twice", (raw, seen.get(raw)))
                seen[raw] = name
                check(raw == raw.strip() and "  " not in raw and raw[-1] in ".!?", f"{name}: a clean sentence", raw)
                check(len(_WORD_RE.findall(raw)) >= 3, f"{name}: >= 3 words", raw)
                # the language gate counts only ə-words and stopwords: a document
                # of two sentences with none is rejected as "not Azerbaijani"
                check(language_evidence(before + word + after, "az")["native_words"] >= 1,
                      f"{name}: a word the language gate counts as Azerbaijani", raw)
                check(not re.search(r"[\d@]", raw), f"{name}: no digits or e-mail", raw)
                check(not stray_capitals(before, after), f"{name}: no other name or place",
                      (raw, stray_capitals(before, after)))
                # the repeat gate rejects a document where the labelled name occurs again unlabelled
                check(az_lower(name) not in az_lower(rest), f"{name}: the word occurs once", raw)
                check(az_lower(word)[:3] == az_lower(name)[:3], f"{name}: the marked word is this name", raw)
                if side == "name":
                    cases = [c for c in sorted(SFX.APPLIES["GIVENNAME"])
                             if SFX.inflect(name, c, "GIVENNAME") == word]
                    check(word == name or cases, f"{name}: an inflected name is a renderer form, "
                          "so the builder declares its suffix", raw)
        words = [w for _f, _b, w, _a in lib.entries[name]["word"]]
        check(any(w[:1].islower() for w in words) and any(w[:1].isupper() for w in words),
              f"{name}: lowercase and capitalised ordinary-word uses mixed")


TESTS = [("homograph list (P4-2)", test_list)]

if __name__ == "__main__":
    for title, fn in TESTS:
        print(title)
        fn()
    print("=" * 60)
    print(f"PASSED {PASS}   FAILED {FAIL}")
    print("=" * 60)
    for f in FAILURES:
        print("  FAIL:", f)
    sys.exit(1 if FAIL else 0)
