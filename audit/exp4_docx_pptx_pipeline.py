"""EXPERIMENT 4 -- the pii_guard pipeline (DOCX/PPTX) end to end.

Different product from formats/*: pii_guard does NOT classify columns. It
joins every extracted segment and runs HybridDetector (regex/checksum
validators for structured labels + the NER model for the four
'ml_context' labels GIVENNAME/SURNAME/CITY/STREET) over the whole thing.

Two things are measured here that exp1-3 could not:

  1. SEGMENTATION -- scripts/pii_guard/detect/_chunk.py re-cuts text into
     <=100-char clauses before inference. Since exp2 showed representation
     dominates everything, the size of the chunking effect on real documents
     is the question that matters, and it is measured here on the same files
     with chunking on and off (`raw` vs `chunked`). (This experiment was
     first run when chunking existed only on the mask/docx branch; the
     package is now one, so the wrapper below applies the same chunker
     explicitly to the raw detector.)

  2. PPTX TEXT-BOX FRAGMENTATION -- identical field content laid out as ONE
     text box vs. TEN separate text boxes, which is the PPTX-specific
     structural variable. Extraction emits one segment per box and joins
     them with '\\n\\n', so this is exp2's `blankline` condition arising
     naturally from a real file rather than being synthesised.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness  # noqa: E402

harness.setup_paths()

import spec     # noqa: E402
import render   # noqa: E402
import extract_all  # noqa: E402

ML_LABELS = {"GIVENNAME", "SURNAME", "CITY", "STREET"}


def chunked_detect(text: str, detect) -> list[dict]:
    """pii_guard's chunking applied to an arbitrary detect_fn: cut into
    clause-sized spans, infer per chunk, shift offsets back."""
    from pii_guard.detect._chunk import chunk_spans
    out = []
    for cs, ce in chunk_spans(text):
        piece = text[cs:ce]
        for s in detect(piece):
            out.append({"start": s["start"] + cs, "end": s["end"] + cs,
                        "label": s["label"]})
    return out


def main() -> None:
    detect = harness.detect_fn_factory()
    harness.FIXTURES.mkdir(parents=True, exist_ok=True)
    harness.RESULTS.mkdir(parents=True, exist_ok=True)
    results = []

    for lang in spec.LANGS:
        expected_all = spec.expected_entities(lang)
        for register in spec.REGISTERS:
            for fmt in ["docx", "pptx"]:
                path = (harness.FIXTURES /
                        f"x_{lang}_{register}_{fmt}{render.EXT[fmt]}")
                if not path.exists():
                    render.RENDERERS[fmt](path, lang, register)
                text, segs = (extract_all.extract_docx(path) if fmt == "docx"
                              else extract_all.extract_pptx(path))
                for mode, fn in [("raw", lambda t: detect(t)),
                                 ("chunked", lambda t: chunked_detect(t, detect))]:
                    spans = fn(text)
                    found = [(s["label"], text[s["start"]:s["end"]])
                             for s in spans]
                    sc = harness.score_values(found, expected_all)
                    # ml-labels only, which is all chunking can affect
                    found_ml = [x for x in found if x[0] in ML_LABELS]
                    exp_ml = [x for x in expected_all if x[0] in ML_LABELS]
                    sc_ml = harness.score_values(found_ml, exp_ml)
                    results.append({
                        "lang": lang, "register": register, "format": fmt,
                        "mode": mode, "n_segments": len(segs),
                        "recall_all": sc["recall"], "precision_all": sc["precision"],
                        "recall_ml": sc_ml["recall"], "precision_ml": sc_ml["precision"],
                    })

    # PPTX one-box vs many-boxes, same content
    for lang in spec.LANGS:
        exp_ml = [x for x in spec.expected_entities(lang) if x[0] in ML_LABELS]
        one = harness.FIXTURES / f"frag_{lang}_onebox.pptx"
        render.render_pptx(one, lang, "labeled")
        many = harness.FIXTURES / f"frag_{lang}_manybox.pptx"
        render.render_pptx_scattered(many, lang)
        for tag, p in [("one_textbox", one), ("many_textboxes", many)]:
            text, segs = extract_all.extract_pptx(p)
            found = [(s["label"], text[s["start"]:s["end"]])
                     for s in detect(text) if s["label"] in ML_LABELS]
            sc = harness.score_values(found, exp_ml)
            results.append({"lang": lang, "register": "labeled",
                            "format": "pptx", "mode": tag,
                            "n_segments": len(segs),
                            "recall_ml": sc["recall"],
                            "precision_ml": sc["precision"]})

    out = harness.RESULTS / "exp4_docx_pptx.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2),
                   encoding="utf-8")

    print("=== chunking effect (ml_context labels: GIVENNAME/SURNAME/CITY/STREET) ===")
    print(f"{'fmt':5s} {'register':9s} {'lang':5s} {'raw R':>7s} {'chunked R':>10s} {'delta':>7s}")
    by = {(r["format"], r["register"], r["lang"], r["mode"]): r
          for r in results if r["mode"] in ("raw", "chunked")}
    tot_raw = tot_ch = n = 0
    for fmt in ["docx", "pptx"]:
        for register in spec.REGISTERS:
            for lang in spec.LANGS:
                a = by.get((fmt, register, lang, "raw"))
                b = by.get((fmt, register, lang, "chunked"))
                if not a:
                    continue
                d = b["recall_ml"] - a["recall_ml"]
                tot_raw += a["recall_ml"]; tot_ch += b["recall_ml"]; n += 1
                print(f"{fmt:5s} {register:9s} {lang:5s} {a['recall_ml']:>6.0%} "
                      f"{b['recall_ml']:>9.0%} {d:>+7.0%}")
    print(f"\nmean raw={tot_raw/n:.0%}  mean chunked={tot_ch/n:.0%}  "
          f"delta={(tot_ch-tot_raw)/n:+.0%}")

    print("\n=== PPTX text-box fragmentation (same fields, same slide content) ===")
    for lang in spec.LANGS:
        o = next(r for r in results if r["mode"] == "one_textbox" and r["lang"] == lang)
        m = next(r for r in results if r["mode"] == "many_textboxes" and r["lang"] == lang)
        print(f"  {lang}: 1 box ({o['n_segments']} seg) R={o['recall_ml']:.0%}   "
              f"-> {m['n_segments']} boxes R={m['recall_ml']:.0%}   "
              f"{m['recall_ml']-o['recall_ml']:+.0%}")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
