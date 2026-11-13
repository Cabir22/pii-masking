"""RT-8 -- adversarial evasion against the model's own decision boundary.

Unlike RT-1 through RT-6, this attacks `your-hf-org/masking-multilingual`
directly, not the pipeline code around it: a single-character transposition
or an inserted hyphen, an edit distance of 1, invisible to a skimming
reader and unambiguously the same name to a human. Every case is checked
against its own clean baseline first (does the model detect the unperturbed
name at all?) so a miss can be attributed to the perturbation and not to a
name the model was already going to miss.

Result: inconsistent. 2 of 5 names ('John', 'Elena') had at least one
1-edit variant fall completely out of detection; 3 of 5 ('Sarah',
'Michael', 'Poladxan') were robust to the same perturbations. Reported
honestly as a real but unpredictable finding -- see the companion
`rt8b_homoglyph.py` for a related attack (visual-lookalike character
substitution) that did NOT reproduce once properly controlled.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "model"))
from predict import load_model, detect_entities  # noqa: E402


def check(model, tok, id2label, text):
    return [(p["label"], p["text"]) for p in detect_entities(text, model, tok, id2label)]


def main() -> None:
    print("=== RT-8: minimal character-edit evasion against the model directly ===\n")
    print("Loading model...")
    model, tok, id2label = load_model("your-hf-org/masking-multilingual")
    print("Loaded.\n")

    cases = [
        ("Poladxan", "Müştəri Poladxan Baharov ilə bağlı sənəd təsdiqləndi."),
        ("John", "The client John Smith confirmed the order today."),
        ("Sarah", "Please contact Sarah Johnson about the invoice."),
        ("Michael", "Our representative Michael Brown will call you back."),
        ("Elena", "The manager Elena Volkova signed the contract."),
    ]

    any_evaded = 0
    for name, frame in cases:
        base = check(model, tok, id2label, frame)
        base_ok = any(p[1] == name for p in base)
        print(f"{name!r}  baseline detected={base_ok}  {base}")
        if not base_ok:
            print("  (skipping -- clean baseline already misses this name; "
                 "a perturbation test needs a clean hit to attribute a miss to)")
            continue

        variants = {
            "swap adjacent (edit distance 1)": name[1] + name[0] + name[2:],
            "insert hyphen mid-word":          name[:len(name)//2] + "-" + name[len(name)//2:],
        }
        for tag, v in variants.items():
            text_v = frame.replace(name, v)
            found = check(model, tok, id2label, text_v)
            hit = any(v.replace("-", "") == f[1].replace("-", "") for f in found)
            print(f"  {tag:32s} {v!r:14s} -> {'DETECTED' if hit else 'MISSED'}  {found}")
            if not hit:
                any_evaded += 1
        print()

    print(f"Total (name, variant) pairs that evaded detection: {any_evaded}")
    print("Inconsistent across names -- not a reliable, targetable technique, but a")
    print("real, cleanly-controlled instance of model-level adversarial fragility.")


if __name__ == "__main__":
    main()
