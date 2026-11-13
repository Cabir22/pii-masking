"""Splices replacement text into a python-docx Paragraph's runs, in place,
preserving each surviving run's formatting.

The piece `extract/docx.py`'s read side never needed: extraction only reads
`paragraph.text`, which python-docx already flattens across runs. Writing
back is harder, because Word routinely splits one word across multiple
`<w:r>` runs (spell-check markers, a mid-word formatting change, tracked
edits) -- a placeholder's offsets, computed against `paragraph.text`, will
almost never line up with where one run ends and the next begins.

Approach: rebuild the paragraph as a flat list of (text, formatting-source
run) fragments, cut at both the original run boundaries and every edit
boundary, then write those fragments back onto the paragraph's EXISTING
run objects -- reusing one run per fragment and copying that fragment's
source run's `rPr` onto it, so bold/italic/font/color survive without
hand-copying every run property one by one.
"""

from __future__ import annotations

import copy


def _paragraph_text_with_run_spans(paragraph):
    """paragraph.text, plus each run's [start, end) span within it."""
    text = ""
    run_spans = []
    for run in paragraph.runs:
        t = run.text
        start = len(text)
        text += t
        run_spans.append((start, start + len(t), run))
    return text, run_spans


def _copy_formatting(source, target) -> None:
    from docx.oxml.ns import qn

    if source is target:
        return
    src_rpr = source._r.find(qn("w:rPr"))
    tgt_rpr = target._r.find(qn("w:rPr"))
    if tgt_rpr is not None:
        target._r.remove(tgt_rpr)
    if src_rpr is not None:
        target._r.insert(0, copy.deepcopy(src_rpr))


def _run_covering(run_spans, pos: int):
    for s, e, run in run_spans:
        if s <= pos < e:
            return run
    return run_spans[-1][2]


def _untouched_fragments(run_spans, text: str, seg_start: int, seg_end: int):
    fragments = []
    for s, e, run in run_spans:
        a, b = max(s, seg_start), min(e, seg_end)
        if a < b:
            fragments.append((text[a:b], run))
    return fragments


def apply_edits(paragraph, edits: list[tuple[int, int, str]]) -> int:
    """Replace each `[start, end)` span of `paragraph.text` with its
    replacement string, in place, preserving run-level formatting for
    everything NOT replaced. `edits` are local to this paragraph's own
    text (not the wider joined-document text `detect()` actually saw --
    the caller is responsible for that offset translation, same
    responsibility `mask.apply_mask` already has for its own flat-string
    case). Returns the number of edits actually applied.

    A replaced span's formatting is taken from whichever run covers its
    START offset. When a span straddles two differently-formatted runs
    there is no single correct answer for what the replacement should look
    like; taking the start run's formatting is a deliberate, simple,
    predictable choice (the same one this project's earlier docx-masking
    prototype made and documented, not a new judgment call).
    """
    text, run_spans = _paragraph_text_with_run_spans(paragraph)
    if not run_spans or not edits:
        return 0

    edits = sorted(edits, key=lambda e: e[0])
    for i in range(len(edits) - 1):
        if edits[i][1] > edits[i + 1][0]:
            raise ValueError(
                f"overlapping edits in one paragraph: {edits[i]} and "
                f"{edits[i + 1]} -- this is a caller bug (detections should "
                f"already be overlap-resolved before reaching here).")
    for s, e, _ in edits:
        if not (0 <= s < e <= len(text)):
            raise ValueError(f"edit span [{s}:{e}) out of bounds for a "
                            f"{len(text)}-character paragraph")

    out_chunks: list[tuple[str, object]] = []
    cursor = 0
    for start, end, replacement in edits:
        if start > cursor:
            out_chunks.extend(_untouched_fragments(run_spans, text, cursor, start))
        out_chunks.append((replacement, _run_covering(run_spans, start)))
        cursor = end
    if cursor < len(text):
        out_chunks.extend(_untouched_fragments(run_spans, text, cursor, len(text)))

    runs = paragraph.runs
    for i, (chunk_text, source_run) in enumerate(out_chunks):
        if i < len(runs):
            target = runs[i]
            _copy_formatting(source_run, target)
            target.text = chunk_text
        else:
            new_run = paragraph.add_run(chunk_text)
            _copy_formatting(source_run, new_run)

    for j in range(len(out_chunks), len(runs)):
        el = runs[j]._r
        parent = el.getparent()
        if parent is not None:
            parent.remove(el)

    return len(edits)
