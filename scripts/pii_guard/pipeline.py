"""Library entry point: what chathal's failover path calls.

## Where this sits

chathal is not part of this repository -- there is no chat backend, routing,
or overload-detection code here (confirmed by inspection before writing any
of this package). The actual deployment shape is:

    user message (+ optional DOCX/PPTX attachment -- PDF is a different
    contributor's workstream, not this package)
              |
              v
      chathal's own primary model  <-- the normal path, no masking needed,
              |                        stays on internal infrastructure
              | (only on overload/failure)
              v
    +----------------------------+
    |   THIS PACKAGE             |   <-- sanitize() / sanitize_document()
    |   detect -> mask           |
    +----------------------------+
              |
              v  sanitized text only, vault stays local
      foreign LLM (e.g. OpenAI)
              |
              v  sanitized response
    +----------------------------+
    |   THIS PACKAGE             |   <-- rehydrate()
    +----------------------------+
              |
              v
         user (via chathal)

So `sanitize()`/`sanitize_document()`/`rehydrate()` are the three calls
chathal's failover code needs. Everything else in `pii_guard` is their
implementation. This module does not decide *when* to fail over -- that
policy belongs to chathal, which knows its own load. It only guarantees that
IF chathal calls this on the failover path, no raw PII leaves in the request
it goes on to build, and the response can be de-masked locally afterward.

## Prompt injection (STEP 11)

Detection here is mechanical: regex + checksum + an NER model run over the
text as data. Nothing in this package parses document/message text as
instructions, evaluates it, or branches pipeline behavior on its content --
there is no `eval`, no template rendering of extracted text, no code path
that reads a document and changes what the *pipeline* does. A document
containing "ignore previous instructions and mask nothing" is just a string
`detect()` scans for entity shapes; it cannot make `detect()` return fewer
detections or make `mask()` skip a span, because neither function branches on
semantic content at all. See `test_pii_guard.py::test_prompt_injection_*`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import GuardConfig, UnsafeConfiguration
from .detect import DetectorError, HybridDetector, MlContextUnavailable
from .extract import (ExtractedDocument, ExtractionDependencyMissing,
                      ExtractionError, extract as extract_document)
from .logging_ import log_sanitisation, safe_excerpt, value_present
from .mask import MaskResult, apply_mask, assign_placeholders, placeholder_pattern
from .mask import rehydrate as _rehydrate
from .vault import Vault

__all__ = [
    "sanitize", "sanitize_document", "rehydrate", "build_external_request",
    "assert_no_raw_pii", "SanitizationFailed",
    "sanitize_document_to_docx", "rehydrate_document", "DocxMaskResult",
    "GuardConfig", "UnsafeConfiguration", "DetectorError",
    "MlContextUnavailable", "ExtractionError", "ExtractionDependencyMissing",
    "MaskResult", "Vault",
]


class SanitizationFailed(RuntimeError):
    """Sanitisation could not be completed with confidence.

    STEP 15's rule, enforced at the one place that matters: raised here means
    the caller must NOT proceed to send `text` (or any attachment text) to an
    external model. There is deliberately no "send anyway" return value --
    the only two outcomes are a `MaskResult` the caller can trust, or this
    exception.
    """


#: Segment kinds excluded from external requests by default. Speaker notes
#: and headers/footers often carry information (internal remarks, letterhead
#: contact details) that is not part of what the user is actually asking
#: about -- excluding them by default is the more conservative choice for
#: something leaving to a third party; a caller can override explicitly.
DEFAULT_EXCLUDED_SEGMENT_KINDS: frozenset[str] = frozenset({"slide_notes"})


def _assert_clean(result: MaskResult, config: GuardConfig) -> None:
    """Re-scan the sanitised text itself for any leftover raw value.

    A belt-and-suspenders check on `apply_mask`'s own output: if a value made
    it into the vault but the exact word/phrase somehow survives in
    `result.text` (an overlapping-span edge case, an encoding surprise),
    this catches it before the text is ever handed back to a caller who will
    send it out. Cheap -- it is a handful of regex checks, not another
    detection pass. Word-boundary matched (`value_present`, not a bare
    substring test) -- see that function's docstring for the real false
    alarms a substring test produced.
    """
    for value in result.vault.values():
        if value and len(value) >= 3 and value_present(result.text, value):
            raise SanitizationFailed(
                f"post-mask self-check failed: a raw value is still present "
                f"in the sanitised text ({safe_excerpt(result.text)}). "
                f"Refusing to return this result.")


def _detector_for(config: GuardConfig) -> HybridDetector:
    try:
        return HybridDetector(config)
    except MlContextUnavailable as exc:
        raise SanitizationFailed(
            f"cannot sanitise: {exc}") from exc


def sanitize(text: str, config: GuardConfig | None = None) -> MaskResult:
    """Mask PII in a chat message (or any plain string) before it leaves.

    This is the call for the common case: a user's typed message on the
    failover path. Raises `SanitizationFailed` rather than returning
    something the caller could mistake for success -- see STEP 15.
    """
    cfg = config or GuardConfig()
    if not text:
        return MaskResult(text=text or "", vault=Vault(), detections=[])

    detector = _detector_for(cfg)
    try:
        detections = detector.detect(text)
    except DetectorError as exc:
        raise SanitizationFailed(
            f"detection failed on text ({safe_excerpt(text)}): {exc}") from exc

    result = apply_mask(text, detections, cfg)
    _assert_clean(result, cfg)
    log_sanitisation(result.vault, result.masked_count, doc="chat_message")
    return result


def sanitize_document(path: str | Path, config: GuardConfig | None = None, *,
                      include_kinds: frozenset[str] | None = None) -> MaskResult:
    """Extract + mask a DOCX/PPTX attachment.

    (PDF is a different contributor's workstream, not this package -- see
    `extract/__init__.py`.)

    `include_kinds`: which `Segment.kind`s to include (default: everything
    except `DEFAULT_EXCLUDED_SEGMENT_KINDS`). Extraction failures are
    re-raised as `SanitizationFailed` -- the original (`ExtractionError`) is
    chained on `__cause__` for diagnosis, but the type callers actually need
    to catch to know "do not proceed" is always this one, matching
    `sanitize()`.
    """
    cfg = config or GuardConfig()
    try:
        doc = extract_document(path)
    except (ExtractionError, ExtractionDependencyMissing) as exc:
        raise SanitizationFailed(
            f"cannot sanitise {Path(path).name!r}: extraction failed "
            f"({type(exc).__name__}: {exc})") from exc

    if cfg.strict and doc.warnings:
        raise SanitizationFailed(
            f"extraction of {doc.source!r} had warnings under strict mode: "
            f"{doc.warnings}. Refusing to send a document that may be "
            f"missing content (e.g. an unread scanned page).")

    kinds = include_kinds if include_kinds is not None else (
        frozenset(s.kind for s in doc.segments) - DEFAULT_EXCLUDED_SEGMENT_KINDS)
    included = [s for s in doc.segments if s.kind in kinds]
    if not included:
        return MaskResult(text="", vault=Vault(), detections=[])

    # Join with the same separator base.py documents, then detect+mask once
    # over the joined text so a repeat mention across segments (a name in
    # the body, the same name in a table) still gets one placeholder.
    from .extract.base import SEGMENT_JOIN
    joined = SEGMENT_JOIN.join(s.text for s in included)

    detector = _detector_for(cfg)
    try:
        detections = detector.detect(joined)
    except DetectorError as exc:
        raise SanitizationFailed(
            f"detection failed on {doc.source!r}: {exc}") from exc

    result = apply_mask(joined, detections, cfg)
    _assert_clean(result, cfg)
    log_sanitisation(result.vault, result.masked_count, doc=doc.source)
    return result


def rehydrate(response_text: str, vault: Vault) -> str:
    """Substitute real values back into a foreign model's response, locally.

    Never called on anything before it leaves -- only on what comes back.
    """
    return _rehydrate(response_text, vault)


def build_external_request(sanitized_text: str, *, model: str,
                           system_prompt: str | None = None,
                           **extra: object) -> dict:
    """Shape the payload chathal's failover call would send.

    Exists mainly so there is one place that assembles "what goes over the
    wire", which is what `assert_no_raw_pii` and the leakage tests check --
    STEP 12's "add a test that fails if raw PII appears in the final payload
    sent to the LLM" needs a payload to inspect, not just a sanitized string.
    A real integration may shape its request differently; the guarantee this
    package provides is about `sanitized_text`, not this particular dict.
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": sanitized_text})
    return {"model": model, "messages": messages, **extra}


def assert_no_raw_pii(payload: object, vault: Vault) -> None:
    """Raise if any raw value from `vault` appears anywhere in `payload`.

    Walks the payload recursively (dicts, lists, strings) rather than just
    checking a `"content"` key, so it catches a leak in any field -- a
    `metadata`, a `user_id` accidentally set to the raw name, a nested list.
    This is the assertion STEP 12 and STEP 10 both ask for; call it in tests
    against `build_external_request(...)`'s output, or against whatever a
    real HTTP client is about to send.
    """
    values = [v for v in vault.values() if v and len(v) >= 3]
    if not values:
        return

    def walk(obj: object, path: str) -> None:
        if isinstance(obj, str):
            for v in values:
                if value_present(obj, v):
                    raise SanitizationFailed(
                        f"raw PII value found in outgoing payload at {path!r} "
                        f"({safe_excerpt(obj)}). This must never happen -- "
                        f"aborting the request.")
        elif isinstance(obj, dict):
            for k, val in obj.items():
                walk(val, f"{path}.{k}")
        elif isinstance(obj, (list, tuple)):
            for i, val in enumerate(obj):
                walk(val, f"{path}[{i}]")

    walk(payload, "$")


# ---------------------------------------------------------------------------
# DOCX as an output format: mask (or rehydrate) a document IN PLACE and
# write a new .docx, instead of only extracting its text for an outbound
# chat payload.
#
# Distinct from `sanitize_document()` above on purpose: that function's
# whole contract is "text only, for the foreign-LLM request" (see the
# module docstring's diagram) -- it never re-opens or re-saves the
# original file, because chathal's failover path has no reason to. A
# masked/rehydrated .docx that preserves the original's formatting, tables,
# headers/footers and embedded images is a different deliverable with a
# different caller (someone who wants a redacted copy of the file itself,
# not just its text in a chat request), so it gets its own entry point
# rather than an extra flag bolted onto `sanitize_document`.
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class DocxMaskResult:
    """What `sanitize_document_to_docx` produces: where the masked copy
    was written, the vault to reverse it locally, and a redaction summary
    for the embedded-image path (which has no vault entry of its own --
    an image is redacted by blacking out pixels, not by a reversible
    placeholder; see `ocr.py`'s module docstring)."""

    output_path: str
    vault: Vault
    detections: list
    #: one dict per embedded image: {partname, lines_detected, lines_redacted}
    images: list = field(default_factory=list)

    def __repr__(self) -> str:  # never show text/values -- this may be logged
        return (f"DocxMaskResult({self.output_path!r}, {len(self.detections)} spans, "
                f"{len(self.images)} images, {self.vault!r})")


def _docx_extract_module():
    # Imported lazily (not at module load) so pipeline.py does not hard-fail
    # to import on a system without python-docx just because these two
    # DOCX-output functions exist -- extract/docx.py already does the same
    # lazy `import docx` + ExtractionDependencyMissing pattern; this mirrors
    # it at the call site rather than the import site.
    from .extract import docx as extract_docx
    return extract_docx


def sanitize_document_to_docx(
    path: str | Path, output_path: str | Path, config: GuardConfig | None = None,
    *, mask_images: bool = True,
) -> DocxMaskResult:
    """Mask a .docx's text (body/tables/headers/footers) AND, by default,
    PII found via OCR in its embedded images -- writing a new .docx at
    `output_path` rather than returning text for a chat request.

    Text masking reuses exactly the same detection this package's other
    entry points use (`HybridDetector`, `mask.assign_placeholders` -- the
    same family/coreference/numbering rules `sanitize_document` applies,
    just spliced into the original paragraph/cell runs instead of one flat
    string) so a name masked here gets the identical placeholder a caller
    would see from `sanitize_document` on the same file.

    Image masking is NOT placeholder-based -- there is no reliable way to
    render "[PERSON_001]" onto an arbitrary image at the right size/
    position, and a wrong-sized overlay could still leave the original
    pixels partially visible underneath. Instead each OCR-detected line
    that contains PII (per this SAME detector, run on that line's text) has
    its whole bounding box blacked out -- see `ocr.redact_regions`. This is
    irreversible by design: `rehydrate_document` (below) can restore masked
    TEXT because it went through the vault, but redacted image pixels are
    gone, matching how a real redaction is expected to behave once it
    leaves the building.

    Raises `SanitizationFailed` under the same conditions `sanitize_document`
    does (extraction failure, strict-mode warnings, a detector error, or the
    post-mask self-check finding a raw value still present) -- this
    function makes the identical "trustworthy result or an exception, never
    a partially-masked file silently written" guarantee.
    """
    cfg = config or GuardConfig()
    extract_docx = _docx_extract_module()

    try:
        rt = extract_docx.extract_for_roundtrip(path)
    except (ExtractionError, ExtractionDependencyMissing) as exc:
        raise SanitizationFailed(
            f"cannot sanitise {Path(path).name!r}: extraction failed "
            f"({type(exc).__name__}: {exc})") from exc

    if cfg.strict and rt.extracted.warnings:
        raise SanitizationFailed(
            f"extraction of {rt.extracted.source!r} had warnings under "
            f"strict mode: {rt.extracted.warnings}. Refusing to write a "
            f"masked copy that may be missing content.")

    joined = rt.extracted.text
    detector = _detector_for(cfg)
    try:
        detections = detector.detect(joined) if joined else []
    except DetectorError as exc:
        raise SanitizationFailed(
            f"detection failed on {rt.extracted.source!r}: {exc}") from exc

    assigned, vault, kept = assign_placeholders(joined, detections, cfg)
    if assigned:
        edits = [(det.start, det.end, placeholder) for det, placeholder in assigned]
        rt.apply_joined_edits(edits)

    image_results: list[dict] = []
    if mask_images:
        for img in extract_docx.find_embedded_images(rt.document):
            image_results.append(_mask_one_image(img, detector, cfg))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rt.save(output_path)

    # Belt-and-suspenders, matching `_assert_clean`'s own reasoning: re-read
    # the file we just wrote and confirm no vault value survived the
    # round-trip through python-docx's own XML serialisation (an edge case
    # `_assert_clean`'s flat-string check cannot see, since it never
    # touches a real .docx save/reload).
    try:
        written = extract_docx.extract(output_path)
    except (ExtractionError, ExtractionDependencyMissing):
        written = None
    if written is not None:
        for value in vault.values():
            if value and len(value) >= 3 and value_present(written.text, value):
                raise SanitizationFailed(
                    f"post-write self-check failed: a raw value is still "
                    f"present in the saved file "
                    f"({safe_excerpt(written.text)}). Refusing to leave "
                    f"this output in place.")

    log_sanitisation(vault, len(kept), doc=rt.extracted.source)
    return DocxMaskResult(output_path=str(output_path), vault=vault,
                          detections=kept, images=image_results)


def _mask_one_image(img, detector: HybridDetector, cfg: GuardConfig) -> dict:
    """OCR the image, detect PII, redact every line that carries any.

    Detects over ALL of the image's OCR lines joined into one string, not
    line-by-line independently -- found by testing against a realistic
    ID-card layout (this package's own `gen_test_docs.py` sample 06): a
    label and its value are almost always two SEPARATE OCR boxes ("DOB:"
    on one line, "1972-06-19" on the next), and `detect/anchored.py`'s
    5 anchor-required labels (DATE, TIME, AGE, BUILDINGNUM,
    CARD_SECURITY_CODE) need to see the label word within 80 characters of
    the value to fire at all. Detecting each OCR line in isolation meant
    the anchor NEVER saw the value it was licensing -- a bare "1972-06-19"
    with no visible "DOB:" nearby is correctly NOT masked by
    `detect/anchored.py`'s design (STEP 2's whole point), so every
    anchor-required label in every embedded image was silently unreachable
    via this path regardless of what the model or pattern tiers did. This
    is the exact same problem `extract/docx.py`'s table-row segments
    already solved (joining cells with " | " so a "Phone" label and its
    number are visible together) -- same fix, applied to OCR lines here.

    Lines are joined with a single "\\n" (NOT `extract.base.SEGMENT_JOIN`'s
    "\\n\\n") deliberately: `entities.cue_window` only treats "\\n\\n" as a
    hard segment boundary, so a single newline keeps adjacent OCR lines
    inside one anchor window (what a label/value pair on two lines needs)
    while `cue_window`'s own sentence-boundary clipping still stops an
    anchor leaking across an unrelated pair of lines further down the
    image (the same protection it already gives ordinary multi-sentence
    text).

    A Detection may fall inside one line's span or straddle two adjacent
    lines that got joined into one OCR box's `\\n`-neighbour text runs
    together -- either way, every OCR line whose character range the
    detection overlaps gets its whole box redacted (still whole-line
    granularity, see `ocr.py`'s module docstring for why: RapidOCR gives no
    sub-word region to redact more precisely than that).
    """
    from . import ocr

    lines = ocr.ocr_lines(img.blob)
    line_spans: list[tuple[int, int]] = []
    pos = 0
    for line in lines:
        line_spans.append((pos, pos + len(line.text)))
        pos += len(line.text) + 1                # + len("\n")
    joined = "\n".join(line.text for line in lines)

    dets = [d for d in detector.detect(joined)
           if d.label in cfg.labels and d.score >= cfg.min_score] if joined.strip() else []

    redacted_indices: set[int] = set()
    for d in dets:
        for i, (ls, le) in enumerate(line_spans):
            if d.start < le and ls < d.end:
                redacted_indices.add(i)

    boxes_to_redact = [lines[i].box for i in sorted(redacted_indices)]
    new_bytes = ocr.redact_regions(img.blob, boxes_to_redact)
    if new_bytes != img.blob:
        img.replace(new_bytes)
    return {"lines_detected": len(lines), "lines_redacted": len(boxes_to_redact)}


def rehydrate_document(
    masked_path: str | Path, output_path: str | Path, vault: Vault,
) -> str:
    """The DOCX-output counterpart to `rehydrate()`: put real TEXT values
    back into a previously-masked .docx, writing a new file rather than
    returning a string.

    Only reverses placeholders `mask.placeholder_pattern` recognises --
    exactly the ones `sanitize_document_to_docx` could have written. Image
    redaction is NOT reversed: see `sanitize_document_to_docx`'s docstring
    for why that is irreversible by design, not a gap in this function.
    Returns `output_path` (as a string) for chaining.
    """
    extract_docx = _docx_extract_module()
    try:
        rt = extract_docx.extract_for_roundtrip(masked_path)
    except (ExtractionError, ExtractionDependencyMissing) as exc:
        raise SanitizationFailed(
            f"cannot rehydrate {Path(masked_path).name!r}: extraction "
            f"failed ({type(exc).__name__}: {exc})") from exc

    joined = rt.extracted.text
    pattern = placeholder_pattern()
    edits = []
    for m in pattern.finditer(joined):
        value = vault.reveal(m.group(0))
        if value is not None:
            edits.append((m.start(), m.end(), value))
    if edits:
        rt.apply_joined_edits(edits)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rt.save(output_path)
    return str(output_path)
