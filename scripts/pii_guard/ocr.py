"""OCR for PII embedded in images -- format-agnostic, like `extract/base.py`.

Lives at the package top level, not under `extract/docx.py`, because an
embedded image is not a DOCX-specific concept: `mask/pptx` (a slide image)
and any future format adapter have the exact same "read pixels, find PII
text, redact the region" problem, and nothing about detecting/redacting
text in an image cares which container format the image came from. Only
*finding* the image bytes in the first place is format-specific, which is
why `extract/docx.py` (or its `mask/pptx` counterpart) owns locating images
and this module owns everything after that.

Uses `rapidocr-onnxruntime`: it ships its own small detection/recognition
ONNX models on PyPI, so no system `tesseract` binary or package-manager
install is required -- `pip install -r requirements.txt` is enough on a
machine with nothing else set up (verified: this was built on a machine
with no Homebrew and only a stock Python 3.9 from Xcode Command Line
Tools -- rapidocr-onnxruntime was the only OCR route that needed neither).

CONFIRMED LIMITATION, not a suspicion -- see
docs/pii_guard_model_notes.md "OCR: Cyrillic and diacritics" for the
cropped-image evidence: RapidOCR's bundled recognition model does not
support Cyrillic script at all (it substitutes visually-similar Latin
letters wholesale, not an approximation -- "Действительна до:" comes back
as "e NCTBNTenb Ha O:") and strips Azerbaijani diacritics during
recognition (`ə`->`a`, `ş`->`s`, ...). Both are real gaps in this OCR
engine, not something this module works around -- a document whose
embedded images carry Cyrillic PII text will not have that PII detected
via the image path at all. Flagged loudly here and in the docs rather than
silently shipped as if image PII detection were complete.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OcrLine:
    text: str
    box: tuple[int, int, int, int]   # (x0, y0, x1, y1) pixel rect
    score: float


#: RapidOCR groups an entire printed line into one box with no explicit
#: space between recognized words ("Name: John A. Carpenter" comes back as
#: "Name:JohnA.Carpenter"). These are a best-effort heuristic respacing --
#: not a real tokenizer, and they cannot recover spacing the OCR engine
#: discarded outright.
_LABEL_COLON = re.compile(r":(?=\S)")
_CAMEL_BOUNDARY = re.compile(r"(?<=[a-zà-яäöüğşı])(?=[A-ZÀ-ЯÄÖÜĞŞİ])")
_LETTER_DIGIT_BOUNDARY = re.compile(r"(?<=[A-Za-zÀ-я])(?=\d)|(?<=\d)(?=[A-Za-zÀ-я])")


def _respace(raw: str) -> str:
    s = _LABEL_COLON.sub(": ", raw)
    s = _CAMEL_BOUNDARY.sub(" ", s)
    s = _LETTER_DIGIT_BOUNDARY.sub(" ", s)
    return s


_ocr_singleton = None


def _get_ocr():
    global _ocr_singleton
    if _ocr_singleton is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr_singleton = RapidOCR()
    return _ocr_singleton


def ocr_lines(image_bytes: bytes) -> list[OcrLine]:
    """Every text line RapidOCR finds in one image, respaced best-effort."""
    import numpy as np
    from PIL import Image
    import io

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    arr = np.array(img)
    result, _ = _get_ocr()(arr)
    if not result:
        return []

    lines: list[OcrLine] = []
    for box, text, score in result:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        rect = (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)))
        lines.append(OcrLine(text=_respace(text), box=rect, score=float(score)))
    return lines


def redact_regions(image_bytes: bytes, boxes: list[tuple[int, int, int, int]],
                   pad: int = 3, fill: tuple[int, int, int] = (0, 0, 0)) -> bytes:
    """Opaque rectangle (padded by `pad` px) over each box.

    Whole-line granularity, not word-level: RapidOCR returns one box per
    LINE, not per word, so there is no sub-word region to redact even if a
    detector only flagged part of a line's (respaced) text -- the entire
    line's box is blacked out if the detector found anything in it at all.
    Conservative on purpose: a slightly larger black box is a much smaller
    problem than a partially-redacted name. Returns the original bytes
    unchanged if there is nothing to redact, so a clean image is never
    re-encoded for no reason.
    """
    if not boxes:
        return image_bytes

    import io
    from PIL import Image, ImageDraw

    img = Image.open(io.BytesIO(image_bytes))
    fmt = img.format or "PNG"
    img = img.convert("RGB") if fmt in ("JPEG", "JPG") else img.convert("RGBA")
    draw = ImageDraw.Draw(img)
    w, h = img.size
    for x0, y0, x1, y1 in boxes:
        rect = (max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad), min(h, y1 + pad))
        draw.rectangle(rect, fill=fill)

    out = io.BytesIO()
    save_kwargs = {"quality": 95} if fmt in ("JPEG", "JPG") else {}
    img.save(out, format=fmt, **save_kwargs)
    return out.getvalue()
