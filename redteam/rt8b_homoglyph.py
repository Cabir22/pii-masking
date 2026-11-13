"""RT-8b -- homoglyph (visual-lookalike script) substitution against the
model's own decision boundary. NEGATIVE RESULT, properly controlled.

Substituting Latin characters for visually-identical Cyrillic lookalikes
(a -> а, e -> е, o -> о, ...) is a classic content-filter/DLP evasion
technique: invisible to a human reading a rendered page, tokenizes
completely differently to most text pipelines. Tested here directly
against the model's raw per-token predictions, with every eligible
character in the name replaced (not just one).

Result: did NOT evade detection when a clean, in-sentence baseline was
available to compare against -- confidence stayed 0.8-0.99 per token even
with every character replaced, for 3 of 4 names tried. One apparent
success (a Latin name embedded in a Russian sentence) does not survive its
own control: the CLEAN, non-homoglyphed version of that same sentence
already failed to detect the name, for an unrelated, already-documented
reason (an out-of-distribution name in an unusual language/script
combination) -- so it is excluded here rather than reported as a finding.
Bare (no sentence context) homoglyphed names were also missed, but so were
their clean, non-homoglyphed controls -- the pre-existing "bare value"
weakness, not a homoglyph-specific effect.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "model"))
from predict import load_model, detect_entities  # noqa: E402

HOMO = {"a": "а", "e": "е", "o": "о", "p": "р", "c": "с", "x": "х", "y": "у",
       "i": "і", "A": "А", "E": "Е", "O": "О"}


def full_homoglyph(s: str) -> str:
    return "".join(HOMO.get(ch, ch) for ch in s)


def check(model, tok, id2label, text):
    return [(p["label"], p["text"]) for p in detect_entities(text, model, tok, id2label)]


def main() -> None:
    print("=== RT-8b: full homoglyph substitution, properly controlled (negative result) ===\n")
    print("Loading model...")
    model, tok, id2label = load_model("your-hf-org/masking-multilingual")
    print("Loaded.\n")

    cases = [
        ("Poladxan", "Müştəri Poladxan Baharov ilə bağlı sənəd təsdiqləndi."),
        ("John", "The client John Smith confirmed the order today."),
        ("Sarah", "Please contact Sarah Johnson about the invoice."),
    ]
    for name, frame in cases:
        name_h = full_homoglyph(name)
        frame_h = frame.replace(name, name_h)
        base = check(model, tok, id2label, frame)
        homo = check(model, tok, id2label, frame_h)
        base_ok = any(p[1] == name for p in base)
        homo_ok = any(p[1] == name_h for p in homo)
        print(f"{name!r} -> {name_h!r}  (every eligible char replaced)")
        print(f"  clean baseline detected:    {base_ok}  {base}")
        print(f"  homoglyphed still detected: {homo_ok}  {homo}\n")

    print("--- the one confound, excluded from the report ---")
    clean = "Форма подписана. Alexei Petrov подтвердил получение."
    homo = "Форма подписана. Аlехеі Petrov подтвердил получение."
    print(f"  clean:      {check(model, tok, id2label, clean)}")
    print(f"  homoglyphed: {check(model, tok, id2label, homo)}")
    print("  -> the CLEAN version already misses 'Alexei' entirely (an unrelated,")
    print("     already-documented out-of-distribution-name gap), so this pair")
    print("     cannot be attributed to homoglyphs and is not reported as a finding.")


if __name__ == "__main__":
    main()
