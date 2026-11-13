"""EXPERIMENT 7 -- does the proposed fix actually reduce plaintext leakage?

exp2 showed that prefixing a cell with its own column header lifts raw-model
recall on that cell from 74% to 95%. That is a model measurement. This
checks whether it survives contact with the real product: the same Excel
pipeline, the same files, the same leak accounting as exp3, with ONE change
-- per-cell detection sees "<header>: <value>" instead of "<value>".

The production module is NOT modified (brief section 25). A copy is patched
in the scratch dir and imported under a different name, so both versions can
be run against the same fixtures in the same process.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness  # noqa: E402

harness.setup_paths()

import spec     # noqa: E402
import render   # noqa: E402
from exp3_pipeline_vs_model import _leaked_cells  # noqa: E402

KEY = b"0" * 32


#: The ONE behavioural change under test. Kept as data so the patch is visible
#: in the diff of this file and re-derivable, not a hand-edited copy that only
#: ever existed on one machine (an earlier version of this script loaded a
#: patched file from a scratch dir that nothing in the repo created).
_OLD_CALL = '''            value = str(cell.value)
            spans = detect_fn(value)
            cache[(row, col_idx)] = spans'''
_NEW_CALL = '''            value = str(cell.value)
            spans = _detect_with_header(detect_fn, name, value)
            cache[(row, col_idx)] = spans'''

_HELPER = '''

def _detect_with_header(detect_fn, header: str, value: str) -> list[dict]:
    """PROTOTYPE (audit): run detection on "<header>: <value>" rather than the
    bare value, then translate offsets back onto the bare value.

    Spans that fall entirely inside the injected prefix are dropped, and a
    span that straddles the prefix boundary is clipped to the value. The
    header text is already in hand here -- this adds no new information, it
    only presents what is already known in the form the model responds to.
    """
    if not header or header.startswith("Column "):
        return detect_fn(value)
    prefix = f"{header}: "
    off = len(prefix)
    out = []
    for s in detect_fn(prefix + value):
        start, end = s["start"] - off, s["end"] - off
        if end <= 0:
            continue                      # entirely inside the header
        start = max(start, 0)
        if start >= end or end > len(value):
            continue
        out.append({**s, "start": start, "end": end})
    return out
'''


def build_prototype() -> Path:
    """Write a patched COPY of formats/excel_format.py into the work dir.

    The production module is never modified (audit brief section 25). If the
    call site being patched ever changes upstream this raises instead of
    silently measuring an unpatched module -- which would report "the fix
    changes nothing" for the wrong reason.
    """
    src = (harness.REPO / "formats" / "excel_format.py").read_text(encoding="utf-8")
    if _OLD_CALL not in src:
        raise RuntimeError(
            "formats/excel_format.py no longer contains the per-cell "
            "detect_fn(value) call this prototype patches; update _OLD_CALL "
            "rather than trusting a run against an unpatched copy.")
    patched = src.replace(_OLD_CALL, _NEW_CALL)
    marker = "\ndef _load_workbook("
    if marker not in patched:
        raise RuntimeError("could not find where to insert the helper")
    patched = patched.replace(marker, _HELPER + marker, 1)
    proto_dir = harness.SCRATCH / "prototype"
    proto_dir.mkdir(parents=True, exist_ok=True)
    out = proto_dir / "excel_format.py"
    out.write_text(patched, encoding="utf-8")
    return out


def load_prototype():
    path = build_prototype()
    spec_ = importlib.util.spec_from_file_location("excel_format_proto", path)
    mod = importlib.util.module_from_spec(spec_)
    sys.modules["excel_format_proto"] = mod
    spec_.loader.exec_module(mod)
    return mod


def run(mod, lang: str, condition: str, detect) -> dict:
    import openpyxl
    labels = (spec.FIELD_LABELS[lang] if condition == "known_headers"
              else spec.FIELD_LABELS_UNKNOWN[lang])
    path = harness.FIXTURES / f"p7_{lang}_{condition}.xlsx"
    render.render_xlsx(path, lang, "table", labels)
    if condition == "no_header":
        wb = openpyxl.load_workbook(path)
        wb.active.delete_rows(1)
        wb.save(path)

    expected = spec.expected_entities(lang)
    wb, manifest = mod.mask_workbook(path, detect, KEY)
    out = harness.FIXTURES / f"p7_{lang}_{condition}.{mod.__name__}.xlsx"
    wb.save(out)

    def cells(p_):
        wbx = openpyxl.load_workbook(p_)
        return [(f"{ws.title}!{c.row}:{c.column}",
                 "" if c.value is None else str(c.value))
                for ws in wbx.worksheets for row in ws.iter_rows() for c in row]

    leaked = _leaked_cells(cells(path), cells(out), expected)
    return {"leaked": len(leaked), "expected": len(expected),
            "mask_rate": 1 - len(leaked) / len(expected),
            "leaked_labels": sorted({l for l, _ in leaked})}


def main() -> None:
    import excel_format as baseline
    proto = load_prototype()
    detect = harness.detect_fn_factory()
    results = []

    print(f"{'lang':5s} {'condition':16s} {'baseline':>9s} {'prototype':>10s} "
          f"{'delta':>7s}   leaked labels (prototype)")
    print("-" * 82)
    tot_b = tot_p = tot_e = 0
    for condition in ["known_headers", "unknown_headers", "no_header"]:
        for lang in spec.LANGS:
            b = run(baseline, lang, condition, detect)
            p = run(proto, lang, condition, detect)
            tot_b += b["leaked"]; tot_p += p["leaked"]; tot_e += b["expected"]
            results.append({"lang": lang, "condition": condition,
                            "baseline": b, "prototype": p})
            print(f"{lang:5s} {condition:16s} {b['mask_rate']:>8.0%} "
                  f"{p['mask_rate']:>9.0%} "
                  f"{p['mask_rate']-b['mask_rate']:>+7.0%}   "
                  f"{p['leaked_labels']}")

    print("-" * 82)
    print(f"TOTAL leaked values: baseline={tot_b}/{tot_e} "
          f"({1-tot_b/tot_e:.1%} masked)  ->  prototype={tot_p}/{tot_e} "
          f"({1-tot_p/tot_e:.1%} masked)")

    out = harness.RESULTS / "exp7_fix_prototype.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
