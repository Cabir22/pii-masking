"""P4-1 acceptance check: contract C1, `frames_az.py`.

No network, no model. Checks the frames themselves; the builder's own test
(`test_builder.py`) checks the documents built from them.

    python scripts/piigen/targeted/test_frames.py
"""

from __future__ import annotations

import collections
import logging
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
logging.disable(logging.WARNING)            # value-pool exhaustion notes
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.anchors import ANCHOR_REQUIRED, DEFAULT_WINDOW            # noqa: E402
from piigen.config import ENTITY_TYPES                                # noqa: E402
from piigen.llm.quality import find_leaked_pii                        # noqa: E402
from piigen.locales import az as AZ                                   # noqa: E402
from piigen.targeted import builder as B                              # noqa: E402
from piigen.targeted import frames_az as F                            # noqa: E402
from piigen.targeted import suffix as SFX                             # noqa: E402
from piigen.text import fold_diacritics                               # noqa: E402
from piigen.validate import validate_example                          # noqa: E402

PASS = 0
FAIL = 0
FAILURES: list[str] = []


def check(cond: bool, msg: str, detail=None) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(msg + (f"  [{detail!r}]"[:600] if detail is not None else ""))


# The C1 case tags (A4).
CASES = {"gen", "dat", "acc", "loc", "abl", "ins", "rel", "pl",
         "pl_gen", "pl_dat", "pl_loc", "pl_abl", "cop"}
# The labels P4-1 step 3 asks 15-30 frames for.
FRAME_LABELS = ("DATE", "IBAN", "PAYMENT_CARD_NUMBER", "ZIPCODE", "AGE", "TIME",
                "CARD_SECURITY_CODE", "BUILDINGNUM", "EMAIL", "AZ_ID_CARD_NUMBER",
                "AZ_DRIVER_LICENSE_NUMBER", "ACCESS_TOKEN", "API_KEY", "IPV6_ADDRESS",
                "MAC_ADDRESS")
# P4-1 step 2: the accusative, locative, dative and first-person forms of each
# label's main anchor noun. They don't fit before a passive verb, so they are
# not in ANCHORS; each must be written into one of the label's own frames.
# CVV's are phrases: `kodunu` alone does not license the label, `CVV kodunu` does.
INFLECTED = {
    "DATE": ("tarixini", "tarixində", "tarixinə", "tarixim"),
    "TIME": ("vaxtını", "vaxtında", "vaxtına", "vaxtım"),
    "AGE": ("yaşını", "yaşında", "yaşına", "yaşım", "yaşımı"),
    "BUILDINGNUM": ("binanı", "binada", "binaya", "evimin"),
    "CARD_SECURITY_CODE": ("cvv kodunu", "cvv kodunda", "cvv koduna", "kartımın cvv kodu"),
    "ZIPCODE": ("indeksini", "indeksində", "indeksinə", "indeksim"),
    "IBAN": ("hesabını", "hesabında", "hesabına", "hesabım"),
    "PAYMENT_CARD_NUMBER": ("kartını", "kartında", "kartına", "kartımın"),
}
# An ANCHORS form is spliced in as a noun phrase before a passive verb
# ("... tarixi göstərilib"), so it must not end in a case: genitive
# (tarixin), accusative (tarixini), dative (tarixinə), locative (tarixində),
# ablative, or first person + accusative (yaşımı).
_CASE_FINAL = re.compile(r"(?:[ıiuü]n|[ıiuü]n[ıiuüaə]|[ıiuü]nd[aə]n?|[ıiuü]m[ıiuü])$")
# A genitive right before {a} ("Müqavilənin {a}") needs a possessive anchor,
# and ANCHORS also holds bare nominatives ("tarix") and phrases that carry
# their own possessor ("müştərinin yaşı"): the possessor goes in the anchor.
_GENITIVE_BEFORE_A = re.compile(r"(\w+)\s+\{a\}")
_NOT_GENITIVE = {"üçün", "bütün", "ucun", "butun"}
_NOT_INFLECTED = {"bina"}                   # ends like a dative, is a nominative
_SLOT_ANY = re.compile(r"\{[^{}]*\}")
# A possessed noun right after {a} ("{a} müddəti") needs the anchor in the
# genitive ("tokeninin müddəti"), and ANCHORS holds nominatives. Listed, not
# guessed from the ending: "sifarişçi", "pasportdakı", "texniki" end the same way.
_POSSESSED = ("müddəti", "sahəsi", "nömrəsi", "formatı", "dəyəri", "statusu", "növü",
              "tarixi", "vaxtı", "surəti", "sahibi", "yeri")
_POSSESSED_AFTER_A = re.compile(r"\{a\} (" + "|".join(
    {w for p in _POSSESSED for w in (p, fold_diacritics(p))}) + r")\b")
# Native review, round 1: after "{a} {v}" a verb that states or records the
# value takes "kimi"/"olaraq" ("adı Əli kimi əks olunub", not "adı Əli əks
# olunub"). Verbs acting on the thing itself ("bloklanıb", "tapılıb") don't.
RECORDING_VERBS = ("göstərilib", "göstərilir", "təsdiqlənib", "əks olunub", "qeyd olunub",
                   "qeyd edilib", "qeydə alınıb", "qeydiyyata alınıb", "yazılıb", "yazılır",
                   "saxlanılır", "saxlanılıb", "daxil edilib", "dəyişdirilib", "düzəldilib",
                   "yenilənib", "bərpa edilib", "görünür", "bildirilib")
_RECORDED_BARE = re.compile(r"\{a\} \{v\} (" + "|".join(
    sorted({v for verb in RECORDING_VERBS for v in (verb, fold_diacritics(verb))},
           key=len, reverse=True)) + r")\b")


def all_frames() -> list[tuple[str, str, str | None]]:
    """(frame id, text, label or None for a generic frame), as the builder names them."""
    out = [(f"F.{lab}.{i}", t, lab) for lab, ts in F.FRAMES.items() for i, t in enumerate(ts)]
    out += [(f"G.{i}", t, None) for i, t in enumerate(F.GENERIC_FRAMES)]
    return out


def words(s: str) -> list[str]:
    return re.findall(r"[^\W\d_]+", s.lower())


# --------------------------------------------------------------------------- #
def test_shape() -> None:
    for name in ("ANCHORS", "FRAMES", "GENERIC_FRAMES", "NEUTRAL", "FRAME_VERSION"):
        check(hasattr(F, name), f"frames_az exports the C1 name {name}")
    check(F.FRAME_VERSION == "c1-v1", "FRAME_VERSION is c1-v1", F.FRAME_VERSION)
    check(set(F.FRAMES) <= set(ENTITY_TYPES), "FRAMES keys are labels",
          sorted(set(F.FRAMES) - set(ENTITY_TYPES)))
    texts = [t for _, t, _ in all_frames()]
    dup = [t for t, n in collections.Counter(texts).items() if n > 1]
    check(not dup, "no frame is written twice", dup[:5])


def test_slots() -> None:
    for fid, text, label in all_frames():
        try:
            frame = B.parse_frame(fid, text)
        except ValueError as exc:
            check(False, str(exc))
            continue
        check(frame.case is None or frame.case in CASES, f"{fid}: case tag is a C1 tag", text)
        rest = _SLOT_ANY.sub("", text.replace("{a}", "", 1))
        check("{" not in rest and "}" not in rest and text.count("{a}") <= 1,
              f"{fid}: no other slots or braces", text)
        # no digits outside names such as "IPv6" and "CVV2": a digit in a
        # frame would be an unlabeled number in every document it writes
        check(not re.search(r"\d", re.sub(r"IPv6|CVV2|CVC2", "", text)),
              f"{fid}: frames carry no digits", text)
        # the renderer adds the suffix; a letter or apostrophe glued to the
        # slot would end the span mid-word
        check(not re.search(r"\{v(?::[a-z_]+)?\}['’\w]|\w\{v", text),
              f"{fid}: nothing glued to the value slot", text)
        check(text.rstrip()[-1:] in ".?!", f"{fid}: ends as a sentence", text)
        if label is None:
            check("{a}" in text and frame.case is None,
                  f"{fid}: a generic frame has {{a}} and a bare {{v}}", text)


def test_anchors() -> None:
    for label in ENTITY_TYPES:
        check(bool(F.ANCHORS.get(label)), f"ANCHORS[{label}] exists (generic frames serve every label)")
    for fid, text, label in all_frames():
        if "{a}" not in text:
            continue
        check(text.index("{a}") < text.index("{v"), f"{fid}: {{a}} comes before the value", text)
        m = _GENITIVE_BEFORE_A.search(text)
        check(not m or m.group(1).lower() in _NOT_GENITIVE
              or not re.search(r"[ıiuü]n$", m.group(1).lower()),
              f"{fid}: no genitive right before {{a}} (the possessor goes in the anchor)", text)
        check(not _POSSESSED_AFTER_A.search(text),
              f"{fid}: no possessed noun right after {{a}} ('{{a}} müddəti')", text)
    for label, forms in F.ANCHORS.items():
        bad = [a for a in forms if not a.split()[-1].isupper()
               and a.split()[-1].lower() not in _NOT_INFLECTED
               and _CASE_FINAL.search(a.split()[-1].lower())]
        check(not bad, f"ANCHORS[{label}]: no case-inflected forms (they fit no passive frame)", bad)
        check(len(set(forms)) == len(forms), f"ANCHORS[{label}]: no duplicates")
        pattern = ANCHOR_REQUIRED.get(label)
        if pattern is not None:
            bad = [a for a in forms if not pattern.search(a)]
            check(not bad, f"every {label} anchor form licenses the label", bad)


def test_inflected_anchors() -> None:
    for label, forms in INFLECTED.items():
        texts = [t.lower() for t in F.FRAMES.get(label, [])]
        missing = [f for f in forms
                   if not any(re.search(rf"(?<!\w){f}(?!\w)", t) for t in texts)]
        check(not missing, f"{label}: inflected anchors written into its own frames", missing)
        pattern = ANCHOR_REQUIRED.get(label)
        if pattern is not None:
            bad = [f for f in forms if not pattern.search(f)]
            check(not bad, f"has_anchor accepts the inflected {label} anchors", bad)


def test_counts() -> None:
    for label in FRAME_LABELS:
        frames = [B.parse_frame(f"F.{label}.{i}", t) for i, t in enumerate(F.FRAMES.get(label, []))]
        check(15 <= len(frames) <= 30, f"{label}: 15-30 frames", len(frames))
        far = sum(1 for f in frames if f.gap is not None and 2 <= f.gap <= 6)
        check(far >= math.ceil(len(frames) / 3),
              f"{label}: >= 1/3 of frames put the anchor 2-6 words away", (far, len(frames)))
    sections = {" ".join(words(t.split("{a}")[0])) for t in F.GENERIC_FRAMES}
    verbs = {" ".join(words(t.split("}")[-1])) for t in F.GENERIC_FRAMES}
    check(len(sections) >= 20, "GENERIC_FRAMES: >= 20 section nouns", len(sections))
    check(len(verbs) >= 20, "GENERIC_FRAMES: >= 20 verbs", len(verbs))
    parsed = [B.parse_frame(fid, t) for fid, t, _ in all_frames()]
    folded = sum(f.folded for f in parsed)
    check(0.08 <= folded / len(parsed) <= 0.15, "about 10% of frames are ASCII-folded",
          f"{folded}/{len(parsed)}")


def test_native_review() -> None:
    """Rules from the native-speaker read of 100 filled frames (round 1)."""
    for fid, text, label in all_frames():
        check(not _RECORDED_BARE.search(text),
              f"{fid}: '{{a}} {{v}}' + a recording verb needs kimi/olaraq", text)
        # "..., indi isə Şəki." / "..., yenisi AB1234567." have no predicate;
        # a colon may introduce the value ("Qeyd: {a} {v}.")
        check(not re.search(r"\{v\}\.$", text) or re.search(r":\s(\{a\}\s)?\{v\}\.$", text),
              f"{fid}: a value at the end of a sentence needs a predicate or a colon", text)
        # street values end in "küç."/"pr.", which would swallow the full stop
        if label == "STREET":
            check(not re.search(r"\{v\}[.!?]$", text),
                  f"{fid}: a street value never ends the sentence", text)
    for label in ("AZ_DRIVER_LICENSE_NUMBER",):
        check("sürücü vəsiqəsi" not in F.ANCHORS[label], f"{label}: 'sürücülük vəsiqəsi', not 'sürücü'")
    bad = [s for s in F.NEUTRAL if "ılmaq üçün" in s or "ilmək üçün" in s]
    check(not bad, "NEUTRAL: 'baxılması üçün', not 'baxılmaq üçün'", bad)


def test_neutral() -> None:
    n = F.NEUTRAL
    check(len(n) >= 100, "NEUTRAL has 100+ sentences", len(n))
    check(len(set(n)) == len(n), "NEUTRAL has no duplicates",
          [s for s, c in collections.Counter(n).items() if c > 1][:5])
    check(not any(re.search(r"\d|[{}]", s) for s in n), "NEUTRAL has no digits and no slots")
    leaks = [s for s in n if find_leaked_pii(s, [], decoy_spans=[])]
    check(not leaks, "NEUTRAL carries no PII", leaks[:5])
    # The leak gate knows pattern PII only (phones, cards, ...), not places.
    # Person names can't be listed this way: the name lists hold ordinary
    # words (Sabah, Diqqət, Həkim), so they are left to the native read.
    cities = {fold for c in AZ.CITIES for fold in (c, fold_diacritics(c))}
    city = re.compile(r"(?<!\w)(" + "|".join(sorted(map(re.escape, cities), key=len, reverse=True)) + ")")
    texts = [t for _, t, _ in all_frames()] + list(n) + [a for fs in F.ANCHORS.values() for a in fs]
    named = [t for t in texts if city.search(t)]
    check(not named, "no city name in a frame, anchor or NEUTRAL sentence", named[:5])


def test_case_frames() -> None:
    """RC8, D-9: inflected name/city/street slots, counted over the
    name/city/street frames together (the plural family forms belong to
    surnames, the -dakı/-dəki form mostly to cities and streets).
    The 5% rule is per row of the P4-1 step 4 table, where plural + case
    (`pl_*`) is one row; each of the 13 C1 tags still appears twice."""
    frames = [B.parse_frame(f"F.{lab}.{i}", t) for lab in B.NAME_LABELS
              for i, t in enumerate(F.FRAMES.get(lab, []))]
    tags = collections.Counter(f.case for f in frames if f.case)
    rows = collections.Counter("pl_*" if c.startswith("pl_") else c for c in tags.elements())
    total = len(frames)
    check(total > 0 and sum(tags.values()) / total >= 0.40,
          "name/city/street: >= 40% of frames carry {v:CASE}", f"{sum(tags.values())}/{total}")
    table = sorted({"pl_*" if c.startswith("pl_") else c for c in CASES})
    low = {r: rows[r] for r in table if rows[r] < 0.05 * total}
    check(not low, "name/city/street: every row of the case table is >= 5% of the frames",
          (low, f"5% of {total} = {0.05 * total:.1f}"))
    rare = {c: tags[c] for c in sorted(CASES) if tags[c] < 2}
    check(not rare, "name/city/street: every C1 case tag is used at least twice", rare)
    # the builder drops a {v:CASE} frame whose case its label never takes
    dead = [f"F.{lab}.{i}" for lab in B.NAME_LABELS for i, t in enumerate(F.FRAMES.get(lab, []))
            if (c := B.parse_frame("x", t).case) and c not in SFX.APPLIES[lab]]
    check(not dead, "every {v:CASE} is a case its label takes (suffix.APPLIES)", dead)
    honorific = [t for t in F.FRAMES.get("GIVENNAME", [])
                 if re.search(r"\{v:[a-z_]+\}\s+(?:xanım|bəy|xanim|bey)", t)]
    check(not honorific, "an honorific carries the case, not the name", honorific)


def test_toy_fill() -> None:
    """Every frame, filled as the builder fills it, passes validate_example and
    the leak gate. The five anchor labels must find their licensing word in
    the frame itself: TIME and most DATE values are self-signalling, so the
    validator alone would never notice a frame without an anchor.
    The language gate is a document-level gate (it scales with length, and
    a lone eight-word sentence fails it however Azerbaijani it is): the
    builder's documents carry NEUTRAL sentences, and validate_corpus.py runs
    it on the build. A {v:CASE} slot gets the P2-4c renderer's form, in every
    surface the builder writes (plain, apostrophe, ASCII-folded)."""
    builder = B.TargetedBuilder(seed=7, n_docs=10)
    problems: dict[str, list] = collections.defaultdict(list)
    tick = 0
    for fid, text, label in all_frames():
        frame = B.parse_frame(fid, text)
        bare = re.sub(r"\{v:[a-z_]+\}", "{v}", text)
        labels = [label] if label else list(ENTITY_TYPES)
        for lab in labels:
            forms = F.ANCHORS.get(lab) or [""]
            # every anchor form in a label's own frames; across the generic
            # frames each form in turn, so every form still meets every label
            chosen = forms if label else [forms[tick % len(forms)]]
            tick += 1
            for anchor in chosen if "{a}" in text else [None]:
                if anchor and frame.folded:
                    anchor = fold_diacritics(anchor)
                female = builder._gender(text) if lab == "GIVENNAME" else None
                if frame.case:
                    value, inflected = builder._mint_inflectable(lab, frame.case, female=female)
                    kinds = ["plain", "folded"] + (["apostrophe"] if frame.case in SFX.APOSTROPHE_CASES
                                                   and lab != "STREET" else [])
                    fills = [(lambda dd, w=SFX.surface(value, inflected, k), k=k:
                              dd.suffixed(lab, w, SFX.split(inflected, value), frame.case, k))
                             for k in kinds]
                else:
                    value = builder._mint(lab, "prose", female)
                    fills = [lambda dd: dd.entity(lab, value)]
                for fill in fills:
                    d = B.Draft()
                    B.write(d, bare, {
                        "a": lambda dd: dd.add(B.az_capitalize(anchor)
                                               if bare.startswith("{a}") else anchor),
                        "v": fill})
                    record = {"id": fid, "text": d.text, "lang": "az", "entities": d.entities,
                              "_decoys": [], "_suffixes": d.suffixes}
                    bad = validate_example(record, strict_language=False)
                    if find_leaked_pii(d.text, d.entities, decoy_spans=[]):
                        bad.append("leak gate")
                    pattern = ANCHOR_REQUIRED.get(lab)
                    if pattern is not None:
                        e = d.entities[0]
                        t = d.text
                        if not (pattern.search(t[max(0, e["start"] - DEFAULT_WINDOW):e["start"]])
                                or pattern.search(t[e["end"]:e["end"] + DEFAULT_WINDOW])):
                            bad.append("no anchor word in the frame")
                    if bad:
                        problems[f"{fid}/{lab}"].append((bad[0][:90], d.text[:120]))
    reasons = collections.Counter(re.sub(r"\(.*", "", v[0][0]).strip()
                                  for v in problems.values())
    first = {k: v[0] for k, v in list(problems.items())[:12]}
    if problems:
        print("   failing reasons:", dict(reasons.most_common()))
    check(not problems, f"every frame, filled, passes validate_example ({len(problems)} failing)",
          first)


TESTS = [
    ("C1 shape", test_shape),
    ("value slots", test_slots),
    ("anchors and the passive-verb rule", test_anchors),
    ("inflected anchors in active frames", test_inflected_anchors),
    ("counts per label, generic sections and verbs, folding", test_counts),
    ("native-speaker review, round 1", test_native_review),
    ("NEUTRAL", test_neutral),
    ("case-tagged name/city/street frames", test_case_frames),
    ("toy fill through validate_example", test_toy_fill),
]

if __name__ == "__main__":
    for name, fn in TESTS:
        print(name)
        fn()
    print()
    print("=" * 60)
    print(f"PASSED {PASS}   FAILED {FAIL}")
    print("=" * 60)
    for f in FAILURES:
        print("  FAIL:", f)
    sys.exit(1 if FAIL else 0)
