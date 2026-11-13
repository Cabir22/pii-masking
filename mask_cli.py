# -*- coding: utf-8 -*-
"""Quick manual test of the masking model on one sentence at a time.

Usage:
    python mask_cli.py "Mənim adım Əli Məmmədovdur"
    python mask_cli.py --raw "Mənim adım Əli Məmmədovdur"   # raw model only, no regex/checksum fallback

Prints what entities were found (label, text, position) and a
placeholder-style masked preview ("[GIVENNAME] [SURNAME]") -- not the
real reversible masking (that needs an encryption key and file-format
context), just enough to see what the model/pipeline caught or missed.
"""
import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "model"))

from predict import load_model, hybrid_detect_entities, detect_entities  # noqa: E402

MODEL_NAME = "your-hf-org/masking-multilingual"


def build_masked_display(text: str, spans: list[dict]) -> str:
    spans_sorted = sorted(spans, key=lambda s: s["start"])
    out = []
    pos = 0
    for s in spans_sorted:
        out.append(text[pos:s["start"]])
        out.append(f"[{s['label']}]")
        pos = s["end"]
    out.append(text[pos:])
    return "".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Quick manual test of the masking model on one sentence.")
    parser.add_argument("text", help="The sentence to test, in quotes.")
    parser.add_argument("--raw", action="store_true",
                        help="Raw model only, no regex/checksum fallback layer.")
    args = parser.parse_args()

    print(f"Loading {MODEL_NAME} ...", file=sys.stderr)
    model, tokenizer, id2label = load_model(MODEL_NAME)

    detect = detect_entities if args.raw else hybrid_detect_entities
    spans = detect(args.text, model, tokenizer, id2label)

    print()
    print("MODE:", "RAW MODEL ONLY" if args.raw else "HYBRID (model + regex/checksum fallback)")
    print()
    print("INPUT:")
    print(args.text)
    print()
    print("MASKED PREVIEW (placeholders, not real reversible masking):")
    print(build_masked_display(args.text, spans))
    print()
    print(f"ENTITIES ({len(spans)}):")
    print(json.dumps(spans, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
