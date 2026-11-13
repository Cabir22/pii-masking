"""EXPERIMENT 1 -- the central cross-format experiment.

Identical semantic content (audit/spec.py) rendered into six formats x four
languages x three registers, then for each one:

  1. EXTRACTION  -- what did the format's own extractor hand back? Compared
     against what the renderer put in, so extraction loss is separated from
     detection loss before any model runs.
  2. SURVIVAL    -- which expected entity VALUES still appear verbatim in the
     extracted text? An entity destroyed by extraction cannot be detected by
     any model, so it must not be charged to the model.
  3. DETECTION   -- raw model on the extracted text, value-level scored.

Detection here is deliberately RAW MODEL ONLY, on each format's real
extracted text. That isolates the model from the product. What the shipped
per-format pipelines actually do with that text is exp2_pipeline_vs_model.py.
"""

from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness  # noqa: E402

harness.setup_paths()

import spec          # noqa: E402
import render        # noqa: E402
import extract_all   # noqa: E402


def norm(s: str) -> str:
    """Whitespace- and NFC-normalised, for fidelity comparison only.

    Every format legitimately reflows whitespace (PDF wraps lines, DOCX
    tables join cells, PPTX joins text boxes). Charging that as an
    extraction failure would be wrong -- what matters is whether the
    CHARACTERS and entity values survived, not the line breaks. Anything
    that differs after this normalisation is a real extraction difference
    and is reported as one.
    """
    return " ".join(unicodedata.normalize("NFC", s).split())


def survives(value: str, text: str) -> bool:
    return unicodedata.normalize("NFC", value) in unicodedata.normalize("NFC", text)


def main() -> None:
    harness.FIXTURES.mkdir(parents=True, exist_ok=True)
    harness.RESULTS.mkdir(parents=True, exist_ok=True)
    detect = harness.detect_fn_factory()

    results = []
    for lang in spec.LANGS:
        expected = spec.expected_entities(lang)
        for register in spec.REGISTERS:
            for fmt in ["txt", "csv", "xlsx", "docx", "pptx", "pdf"]:
                path = harness.FIXTURES / f"x_{lang}_{register}_{fmt}{render.EXT[fmt]}"
                intended = render.RENDERERS[fmt](path, lang, register)

                # ---- extraction ----
                segments = None
                if fmt == "txt":
                    got = extract_all.extract_txt(path)
                elif fmt == "csv":
                    got = extract_all.extract_csv_text(path)
                elif fmt == "xlsx":
                    got = extract_all.extract_xlsx_text(path)
                elif fmt == "docx":
                    got, segments = extract_all.extract_docx(path)
                elif fmt == "pptx":
                    got, segments = extract_all.extract_pptx(path)
                else:
                    got = extract_all.extract_pdf(path)

                fidelity = None
                if intended:
                    fidelity = norm(intended) == norm(got)

                survived = [(lab, v) for lab, v in expected if survives(v, got)]
                destroyed = [(lab, v) for lab, v in expected if not survives(v, got)]

                # ---- raw model detection on the extracted text ----
                spans = detect(got)
                found = harness.spans_to_values(got, spans)

                # Scored against what SURVIVED extraction, so the model is
                # not charged for entities extraction already destroyed;
                # `destroyed` is reported separately and charged to
                # extraction instead.
                sc = harness.score_values(found, survived)

                results.append({
                    "lang": lang, "register": register, "format": fmt,
                    "extracted_chars": len(got),
                    "n_segments": len(segments) if segments is not None else None,
                    "extraction_faithful": fidelity,
                    "destroyed_by_extraction": [list(x) for x in destroyed],
                    "survived": len(survived), "expected": len(expected),
                    **{k: v for k, v in sc.items()
                       if k in ("tp", "fp", "fn", "precision", "recall", "f1")},
                    "missed": [list(x) for x in sc["missed"]],
                    "spurious": [list(x) for x in sc["spurious"]],
                    "extracted_sample": got[:400],
                })
                print(f"{lang} {register:8s} {fmt:5s} "
                      f"fidelity={str(fidelity):5s} "
                      f"survived={len(survived)}/{len(expected)} "
                      f"P={sc['precision']:.0%} R={sc['recall']:.0%} "
                      f"F1={sc['f1']:.0%}")

    out = harness.RESULTS / "exp1_cross_format.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
