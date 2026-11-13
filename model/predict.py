"""Stage 4b: turn a trained checkpoint into `detect_entities(text) -> spans`.

Phase 1 of the Excel/CSV/TXT masking track. This is
the one piece that did not exist anywhere in the repo before: train.py
produces a scored model, but nothing converted its token-level predictions
back into character-offset spans on arbitrary input text.

Data contract this must match EXACTLY, or every prediction is silently
wrong (see train.py's own docstring for why):
  - tokenizer: the xlm-roberta-large FAST tokenizer, with the same
    `add_punctuation_boundary` pre-tokenizer patch prepare_splits.py applies
    before producing training data. A model trained on punctuation-patched
    windows sees a systematically different token stream at inference time
    if this patch is skipped -- not a crash, a silent accuracy loss.
  - windowing: max_length=512, stride=256, matching prepare_splits.py's
    defaults (see its own docstring for why: stride must be >= the longest
    entity in tokens, measured at 199 tokens for ACCESS_TOKEN).
  - labels: BIO tags from labels.json (55 labels: O + B-/I- per the 27
    entity types), id2label keyed by string int (JSON has no int keys).

Two-part design, deliberately: `_decode_window_spans` (per-window BIO ->
character spans) and `_merge_window_spans` (many windows' overlapping
candidates -> one final non-overlapping list) are pure functions with no
model or tokenizer dependency, so they are fully testable without ever
downloading model weights -- see test_predict.py, same "no downloaded
model in tests" policy scripts/test_prepare_splits.py already established.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

IGNORE_LABEL_ID = -100


# ---------------------------------------------------------------------------
# Pure decode/merge logic -- no model, no tokenizer, fully unit-testable.
# ---------------------------------------------------------------------------

def _decode_window_spans(offset_mapping: list[tuple[int, int]],
                         pred_label_ids: list[int],
                         id2label: dict[int, str]) -> list[dict]:
    """One window's per-token predicted label ids -> character-offset spans.

    Mirrors `prepare_splits.align_labels_for_window` in reverse: that
    function set B-<TYPE> only where `tok_start == entity_start` and I-<TYPE>
    on any other overlapping token, so decoding walks the same rule
    backwards -- a span starts exactly where a B- token starts, and extends
    through immediately-following I- tokens of the SAME type.

    An I-<TYPE> with no preceding B-<TYPE> open (the model's own mistake, or
    a window seeing only the tail of an entity that started before this
    window) is treated as starting a fresh span there rather than being
    dropped -- seqeval's own BIO decoding tolerates this same case, and
    dropping it would silently lose a real detection at every window
    boundary, the exact class of bug the punctuation/morphology span-policy
    work spent real effort fixing.
    """
    spans: list[dict] = []
    open_span: dict | None = None

    for (tok_start, tok_end), pid in zip(offset_mapping, pred_label_ids):
        if tok_start == tok_end or pid == IGNORE_LABEL_ID:
            # Special token (<s>, </s>, <pad>): never part of a span, and
            # never extends one across it either -- but flush whatever was
            # open first. The original version of this cleared open_span
            # without appending it, silently dropping the last entity of
            # every window right at its closing </s> token: caught by the
            # end-to-end test, which showed ~2 missing entities per real
            # document regardless of length, in every sampled document.
            if open_span is not None:
                spans.append(open_span)
            open_span = None
            continue

        tag = id2label[pid]
        if tag == "O":
            if open_span is not None:
                spans.append(open_span)
            open_span = None
            continue

        prefix, label = tag.split("-", 1)
        if prefix == "B" or open_span is None or open_span["label"] != label:
            if open_span is not None:
                spans.append(open_span)
            open_span = {"start": tok_start, "end": tok_end, "label": label}
        else:  # "I-" continuing the currently open span of the same label
            open_span["end"] = tok_end

    if open_span is not None:
        spans.append(open_span)
    return spans


def _enforce_word_consistency(offset_mapping: list[tuple[int, int]],
                              pred_label_ids: list[int],
                              confidences: list[float],
                              id2label: dict[int, str],
                              id2id: dict[str, int],
                              text: str) -> list[int]:
    """Independent per-subword classification lets one weak subword flip
    the label mid-word: found via a real case, 'Gədəbəy' (one Azerbaijani
    word) tokenizes into 4 subword pieces, and the model predicted
    CITY, CITY, GIVENNAME, CITY across them -- the third piece, 'bə' taken
    alone, is genuinely ambiguous (53% confidence, barely above chance),
    so the argmax landed on the wrong side of a near-coin-flip and nothing
    stopped it from disagreeing with its own neighbours. There is no
    per-token mechanism that enforces "the same word stays one entity."

    Fix applied here, not in the model: group consecutive CHARACTER-
    ADJACENT ALPHANUMERIC tokens into words, and within each word let the
    MOST CONFIDENT subword's tag win for the whole word -- B- on the
    word's first token, I- on the rest (or O throughout if the winning
    tag is O). This is a decode-time correction, not a retrain: it only
    ever resolves a disagreement the model already expressed between its
    own subwords, never introduces a label unsupported by any of them.

    The "alphanumeric" qualifier is load-bearing, found the hard way: an
    earlier version of this function grouped by adjacency ALONE, on the
    assumption that punctuation "tokenizes separately, so adjacency
    reliably means still inside one word." That's true of tokenizing
    separately, but false of adjacency -- punctuation with no preceding
    space ("Bərgah:") is still character-adjacent to the word before it.
    Tested against the full adversarial suite: that version grouped
    'gah' + ':' into one word, the colon's O-prediction (confidence
    1.000, punctuation is easy) beat the name's own correct GIVENNAME
    prediction (0.993) on raw confidence, and overwrote a fully correct
    detection with nothing -- 105 cases regressed, zero improved. Never
    shipped past that test. A token only joins a word if its own text is
    alphanumeric; punctuation always stands alone and is never corrected.

    A second bug, caught the same way, one fix later: a punctuation token
    is never CORRECTED, but its own original prediction still has to feed
    CONTINUITY tracking, or a hyphen genuinely inside an entity ("+994-77-
    871-68-38", every token including every '-' predicted I-TELEPHONENUM
    at ~100% confidence) forces the next digit group to restart with a
    fresh B-, splitting one correct span into two. The first version of
    this fix built a `words` list that only ever contained alphanumeric
    runs -- punctuation tokens were skipped entirely, never touched
    `open_label`, so continuity silently reset to None every time a
    punctuation token appeared. Tested and confirmed against the full
    adversarial suite: 17 regressions, all phone numbers/PRIVATE_KEY
    armour/URLs with in-entity punctuation, zero improvements. Fixed by
    processing every non-special token in one strict left-to-right pass:
    punctuation still updates `open_label` from its own original
    prediction, it just never has its OWN label rewritten.

    Special tokens (start == end, e.g. <s>/</s>/<pad>) are the only
    tokens skipped entirely -- never corrected, never read for
    continuity, never treated as adjacent to their neighbours.
    """
    corrected = list(pred_label_ids)

    def tag_label(idx: int) -> str | None:
        tag = id2label[pred_label_ids[idx]]
        return tag.split("-", 1)[1] if "-" in tag else None

    # One left-to-right pass, split into runs: each run is either a
    # maximal group of adjacent alphanumeric tokens (len >= 1, a "word")
    # or a single non-alphanumeric token (punctuation, len == 1, never
    # corrected). Special tokens are dropped entirely, not even a run of
    # their own -- they must never break continuity across them either.
    runs: list[list[int]] = []
    current: list[int] = []
    prev_end: int | None = None
    for i, (s, e) in enumerate(offset_mapping):
        if s == e:  # special token -- invisible to both correction and
            continue  # continuity, exactly as if it weren't there
        if not text[s:e].isalnum():
            if current:
                runs.append(current)
                current = []
            runs.append([i])
            prev_end = None
            continue
        if prev_end is not None and s == prev_end and current:
            current.append(i)
        else:
            if current:
                runs.append(current)
            current = [i]
        prev_end = e

    if current:
        runs.append(current)

    # Walk the runs in order, tracking the entity label (if any) the
    # PREVIOUS run resolved to -- a multi-word entity ("Fazil Hüseynov
    # Blv.") must still stitch together across word boundaries, and an
    # in-entity punctuation run must still carry continuity through
    # itself even though its own label is never rewritten.
    open_label: str | None = None
    for run in runs:
        # A run of length 1 is either a punctuation token (always a
        # singleton by construction above) or a single-token word --
        # either way there's no internal disagreement to resolve, so it's
        # read-only: its own prediction just feeds continuity forward.
        if len(run) < 2:
            open_label = tag_label(run[0])
            continue

        winner = max(run, key=lambda i: confidences[i])
        base_label = tag_label(winner)

        if base_label is None:
            for i in run:
                corrected[i] = id2id["O"]
        else:
            # 2026-10-14 (v3 root causes, section 7): continue the previous
            # word's entity only if the model itself continued it on this
            # word's first token. Forcing I- whenever the labels matched
            # merged a given name and the father's name (two GIVENNAME
            # spans by D-39b) into one span in 264 of 542 audited
            # disagreements; the raw model split them correctly (105 of 105).
            # A multi-word entity ("Fazil Hüseynov Blv.") still stitches:
            # there the model predicts I- on the next word.
            # Digit groups (`1234 5678 …`) keep the old stitching: a card or
            # phone written in groups is one value even where the model
            # flickers to B- on a later group (cards lost 1.1 F1 otherwise).
            run_text = "".join(text[offset_mapping[i][0]:offset_mapping[i][1]] for i in run)
            continues = (id2label[pred_label_ids[run[0]]] == f"I-{base_label}"
                         or run_text.isdigit())
            first_prefix = "I" if (open_label == base_label and continues) else "B"
            for pos, i in enumerate(run):
                prefix = first_prefix if pos == 0 else "I"
                corrected[i] = id2id[f"{prefix}-{base_label}"]
        open_label = base_label

    return corrected


def _merge_window_spans(candidates: list[dict]) -> list[dict]:
    """Many (possibly overlapping, possibly duplicate) window-level span
    candidates -> one final non-overlapping list.

    Overlap is expected and by design: with stride < window size, an entity
    near a window boundary is seen fully in one window and only partially in
    its neighbour (this is exactly the invariant
    test_prepare_splits.py's "stride >= entity length captures it whole in
    >=1 window" check exists to guarantee). Longest-first, first-claimed-wins
    is the same overlap policy resolver.py's `resolve_claims` already uses
    for the identical reason: a containing/complete span should win over a
    partial one, independent of which window happened to produce it first.
    """
    # 2026-10-14 (v3 root causes, section 2): an entity LONGER than one
    # window (a full-length PEM key, D-27: ~1,300 tokens) is seen as several
    # overlapping pieces, one per window, none of them whole. Longest-first
    # alone kept one piece and dropped the rest (43.7% of each probe key left
    # unmasked). Same-label spans that overlap are pieces of one entity, so
    # they are joined first; the containment and duplicate cases above give
    # the same result as before, and touching-but-not-overlapping spans stay
    # separate entities.
    joined: list[dict] = []
    for span in sorted(candidates, key=lambda s: (s["label"], s["start"], -s["end"])):
        last = joined[-1] if joined else None
        if last is not None and last["label"] == span["label"] and span["start"] < last["end"]:
            if span["end"] > last["end"]:
                joined[-1] = {**last, "end": span["end"]}
            continue
        joined.append(dict(span))
    candidates = joined
    ordered = sorted(candidates, key=lambda s: s["end"] - s["start"], reverse=True)
    claimed: list[tuple[int, int]] = []
    final: list[dict] = []
    for span in ordered:
        s, e = span["start"], span["end"]
        if any(s < ce and cs < e for cs, ce in claimed):
            continue
        claimed.append((s, e))
        final.append(span)
    final.sort(key=lambda s: s["start"])
    return final


# ---------------------------------------------------------------------------
# Tokenizer / windowing -- must match prepare_splits.py exactly.
# ---------------------------------------------------------------------------

def _tokenize_windows(text: str, tokenizer, max_length: int = 512,
                      stride: int = 256):
    """Same call shape as prepare_splits.tokenize_split, for ONE string
    instead of a whole split -- offsets come back in original-text
    coordinates in every window (verified there, relied on here)."""
    return tokenizer(
        text,
        return_offsets_mapping=True,
        return_overflowing_tokens=True,
        truncation=True,
        max_length=max_length,
        stride=stride,
    )


# ---------------------------------------------------------------------------
# Model loading and the real end-to-end call.
# ---------------------------------------------------------------------------

def load_model(checkpoint_dir: str | Path, device: str | None = None,
               revision: str | None = None):
    """Loads a fine-tuned checkpoint the way train.py produced it.

    Returns (model, tokenizer, id2label). Applies add_punctuation_boundary
    to the tokenizer -- required, see module docstring -- and fails loudly
    (matching prepare_splits.py's own behaviour) rather than silently
    running unpatched if the checkpoint's tokenizer turns out to be a
    slow/Python one with no backend_tokenizer.

    `revision` pins a Hub branch, tag or commit SHA (eval/scoreboard.py
    scores one exact commit); None keeps from_pretrained's default.
    """
    import torch
    from transformers import AutoModelForTokenClassification, AutoTokenizer
    from prepare_splits import add_punctuation_boundary  # noqa: E402

    # Deliberately NOT wrapped in Path(): `checkpoint_dir` may be a local
    # directory OR a Hugging Face Hub repo ID ("your-hf-org/masking-multilingual"),
    # and `from_pretrained` already accepts either as a plain string. Path()
    # used to run here regardless -- harmless on POSIX, but on Windows
    # Path(str(...)) silently turns "/" into "\", corrupting a real repo ID
    # into "your-hf-org\masking-multilingual", which huggingface_hub then
    # rejects outright. Found by actually loading a real Hub model, not by
    # any local-file-only test (none of which would have hit this path).
    tokenizer = AutoTokenizer.from_pretrained(checkpoint_dir, revision=revision)
    if not add_punctuation_boundary(tokenizer):
        raise RuntimeError(
            f"{checkpoint_dir} has no fast tokenizer -- cannot apply the "
            "punctuation-boundary patch training data was built with. "
            "Predictions from this checkpoint would not match training.")

    model = AutoModelForTokenClassification.from_pretrained(checkpoint_dir,
                                                            revision=revision)
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device).eval()

    id2label = {int(k): v for k, v in model.config.id2label.items()}
    return model, tokenizer, id2label


def _model_window_predictions(text: str, model, tokenizer,
                              max_length: int = 512, stride: int = 256,
                              device: str | None = None
                              ) -> list[tuple[list[tuple[int, int]], list[int], list[float]]]:
    """Runs the model once over every sliding window of `text`, returning
    per window (offset_mapping, pred_label_ids, confidences) -- confidence
    being the winning label's own softmax probability. The one place the
    model actually runs; both detect_entities (pure decode, unmodified)
    and the word-consistency-corrected path build on this instead of each
    running their own forward pass.
    """
    import torch

    device = device or next(model.parameters()).device
    enc = _tokenize_windows(text, tokenizer, max_length, stride)

    windows = []
    with torch.no_grad():
        for w in range(len(enc["input_ids"])):
            input_ids = torch.tensor([enc["input_ids"][w]], device=device)
            attention_mask = torch.tensor([enc["attention_mask"][w]], device=device)
            logits = model(input_ids=input_ids,
                           attention_mask=attention_mask).logits[0]
            probs = torch.softmax(logits, dim=-1)
            pred_ids = logits.argmax(dim=-1).tolist()
            confidences = probs.max(dim=-1).values.tolist()
            windows.append((enc["offset_mapping"][w], pred_ids, confidences))
    return windows


def detect_entities(text: str, model, tokenizer, id2label: dict[int, str],
                    max_length: int = 512, stride: int = 256,
                    device: str | None = None) -> list[dict]:
    """The Phase-1 deliverable: text in, entity spans out.

    Format-agnostic on purpose -- this is called identically whether `text`
    came from a TXT file, a free-text spreadsheet cell, or a document
    paragraph. The format only ever affects extraction (Phase 2+), never
    this function.
    """
    windows = _model_window_predictions(text, model, tokenizer,
                                        max_length, stride, device)
    candidates: list[dict] = []
    for offsets, pred_ids, _confidences in windows:
        candidates.extend(_decode_window_spans(offsets, pred_ids, id2label))

    merged = _merge_window_spans(candidates)
    return [{"start": s["start"], "end": s["end"], "label": s["label"],
             "text": text[s["start"]:s["end"]]} for s in merged]


# ---------------------------------------------------------------------------
# Validity check (after-A5 plan, 21 Oct): a TIME, DATE or CVV whose value
# cannot exist is not masked. The model reads the context ("saat …
# radələrində", "… tarixində imzalanıb", "CVV kodu:") and sometimes trusts it
# over the value (v4.2 probes: 24:51, 30.02.2027, a 5-digit CVV). A real value
# always passes, so this can't lower recall; anything it can't parse is kept.
# ---------------------------------------------------------------------------

DECODER_VERSION = "validity-2"  # part of the scoreboard's track-M cache key

_MONTHS = {  # stem -> month number; az, tr, ru (nominative + genitive stems), en
    **{s: i + 1 for i, s in enumerate(["yanvar", "fevral", "mart", "aprel", "may", "iyun",
                                       "iyul", "avqust", "sentyabr", "oktyabr", "noyabr", "dekabr"])},
    **{s: i + 1 for i, s in enumerate(["ocak", "şubat", "mart", "nisan", "mayıs", "haziran",
                                       "temmuz", "ağustos", "eylül", "ekim", "kasım", "aralık"])},
    **{s: i + 1 for i, s in enumerate(["январ", "феврал", "март", "апрел", "ма", "июн",
                                       "июл", "август", "сентябр", "октябр", "ноябр", "декабр"])},
    **{s: i + 1 for i, s in enumerate(["jan", "feb", "mar", "apr", "may", "jun",
                                       "jul", "aug", "sep", "oct", "nov", "dec"])},
}
_TIME_RE = re.compile(r"(?<!\d)(\d{1,2})\s*[:.]\s*(\d{2})(?:\s*[:.]\s*(\d{2}))?(?!\d)")
_NUM_DATE_RE = re.compile(r"(?<!\d)(\d{1,4})\s*([./\-])\s*(\d{1,2})\s*\2\s*(\d{2,4})(?!\d)")
_WORD_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})(?:-?(?:ci|cı|cu|cü|st|nd|rd|th|го|е))?\.?\s+([^\W\d_]+)(?:\s+(\d{4}))?",
                           re.UNICODE)
_WORD_FIRST_DATE_RE = re.compile(r"([^\W\d_]{3,})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})", re.UNICODE)


def _days_in_month(month: int, year: int | None) -> int:
    if month == 2:
        if year is None:
            return 29
        return 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28
    return 30 if month in (4, 6, 9, 11) else 31


def _date_ok(day: int, month: int, year: int | None) -> bool:
    return 1 <= month <= 12 and 1 <= day <= _days_in_month(month, year)


def _month_of(word: str) -> int | None:
    w = word.lower().replace("i̇", "i")
    for stem in sorted(_MONTHS, key=len, reverse=True):
        if w.startswith(stem) and (len(stem) >= 3 or w in ("май", "мая", "мае", "ма")):
            return _MONTHS[stem]
    return None


def _value_possible(label: str, value: str) -> bool:
    """False only when `value` provably can't be a real `label` value."""
    v = value.strip()
    if label == "TIME":
        # judge only a cleanly written time; a noisy one (OCR, typos) is kept
        m = _TIME_RE.fullmatch(re.sub(r"\s*[AaPp]\.?[Mm]\.?$", "", v))
        if not m:
            return True
        h, mi, s = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
        if h == 24:
            return mi == 0 and s == 0          # 24:00 is end of day (D-57)
        return h <= 23 and mi <= 59 and s <= 59
    if label == "DATE":
        # judge only a cleanly written date: dd.mm.yyyy / dd/mm/yy / yyyy-mm-dd, whole value
        m = _NUM_DATE_RE.fullmatch(v)
        if m and len(m.group(1)) in (1, 2, 4) and len(m.group(4)) in (2, 4) \
                and not (len(m.group(1)) == 4 and len(m.group(4)) != 2):
            a, sep, b, c = int(m.group(1)), m.group(2), int(m.group(3)), m.group(4)
            if len(m.group(1)) == 4:                       # yyyy-mm-dd
                return _date_ok(int(c), b, a)
            year = int(c) if len(c) == 4 else None
            # day-month first; month-day too for slashes (English documents)
            return _date_ok(a, b, year) or (sep == "/" and _date_ok(b, a, year))
        if m:
            return True                                    # unusual numeric shape: keep
        m = _WORD_DATE_RE.match(v)
        if m and (month := _month_of(m.group(2))):
            return _date_ok(int(m.group(1)), month, int(m.group(3)) if m.group(3) else None)
        m = _WORD_FIRST_DATE_RE.match(v)
        if m and (month := _month_of(m.group(1))):
            return _date_ok(int(m.group(2)), month, int(m.group(3)))
        return True
    if label == "CARD_SECURITY_CODE":
        if "-" in v:                                       # dashed CVVs are real (D-30b)
            return True
        digits = re.sub(r"\D", "", v)
        return not (digits and digits == re.sub(r"\s", "", v) and not 3 <= len(digits) <= 4)
    return True


# D-2 dummies that can't be anyone's real value: never masked. Only the distinctive
# ones; the short sequences (1234, 12345, 123456, 0000) stay masked, because a real
# PIN, CVV or ZIP code can be exactly that and masking is the privacy-safe side.
D2_DUMMIES = frozenset({"4242424242424242", "4111111111111111", "5555555555554444",
                        "P12345678", "A12B34", "12:34:56", "1.2.3.4"})


def _drop_impossible_values(spans: list[dict], text: str) -> list[dict]:
    out = []
    for s in spans:
        v = text[s["start"]:s["end"]]
        if not _value_possible(s["label"], v):
            continue
        if re.sub(r"[\s-]", "", v) in D2_DUMMIES or v.strip() in D2_DUMMIES:
            continue
        out.append(s)
    return out


def _detect_entities_word_consistent(text: str, model, tokenizer,
                                     id2label: dict[int, str],
                                     max_length: int = 512, stride: int = 256,
                                     device: str | None = None) -> list[dict]:
    """detect_entities, with _enforce_word_consistency applied per window
    before decoding -- the actual fix for the intra-word label-flip
    failure mode (see that function's docstring). NOT used by
    detect_entities itself (which must stay a faithful, uncorrected
    reflection of the model -- see test_predict.py); this is what
    hybrid_detect_entities calls instead, so production masking gets the
    correction automatically.
    """
    id2id = {label: idx for idx, label in id2label.items()}
    windows = _model_window_predictions(text, model, tokenizer,
                                        max_length, stride, device)
    candidates: list[dict] = []
    for offsets, pred_ids, confidences in windows:
        corrected = _enforce_word_consistency(offsets, pred_ids, confidences,
                                              id2label, id2id, text)
        candidates.extend(_decode_window_spans(offsets, corrected, id2label))

    merged = _drop_impossible_values(_merge_window_spans(candidates), text)
    return [{"start": s["start"], "end": s["end"], "label": s["label"],
             "text": text[s["start"]:s["end"]]} for s in merged]


# ---------------------------------------------------------------------------
# Hybrid detection -- model + deterministic pattern-tier safety net.
# ---------------------------------------------------------------------------

def hybrid_detect_entities(text: str, model, tokenizer, id2label: dict[int, str],
                           **kwargs) -> list[dict]:
    """detect_entities, with pattern_fallback.find_pattern_spans layered on
    top for the labels that have a deterministic shape.

    Why this is a second function rather than folding the fallback into
    detect_entities itself: detect_entities's contract is "the model's
    answer, decoded correctly" -- test_predict.py holds it to that
    specifically so a decode bug is never masked by a regex quietly
    papering over it. This wrapper is the actual detect_fn a caller should
    hand to mask_text/mask_workbook in production, matching real-model
    findings that DATE and EMAIL in particular need it:
    DATE's dd.mm.yyyy shape is missed in most ordinary sentence phrasing
    despite being a third of all training examples of that shape, and EMAIL
    comes back from the model as disjoint unusable fragments rather than
    one span.

    A pattern-verified span REPLACES any model span it overlaps, rather
    than the two being merged by length like predict.py's own
    _merge_window_spans does internally. That asymmetry is deliberate: a
    checksum/format-verified TELEPHONENUM or a structurally-plausible DATE
    is trusted over the model's guess in that same region even when the
    model's span is longer, because these specific labels don't need
    semantic judgment to confirm -- unlike GIVENNAME/CITY/etc., which never
    go through pattern_fallback at all and are left exactly as the model
    predicted them.

    The model spans themselves come from _detect_entities_word_consistent,
    not detect_entities directly -- it corrects one specific decode-level
    failure (a low-confidence subword mid-word flipping the label away
    from its neighbours' agreement, e.g. one Azerbaijani word fragmenting
    into CITY/GIVENNAME/CITY across its own subword pieces) before any of
    the passes below ever run. See that function's docstring for the real
    case that motivated it.

    A third pass, find_email_echoed_name_spans, runs after the merge above
    and only ever ADDS to it -- it recovers a name the model missed by
    cross-referencing an EMAIL address already confirmed in this same
    text (see its own docstring for the exact, reproducible failure this
    closes and why it's safe). It never overrides anything the first two
    passes already found.
    """
    from pattern_fallback import find_email_echoed_name_spans, find_pattern_spans

    model_spans = _detect_entities_word_consistent(text, model, tokenizer,
                                                    id2label, **kwargs)
    pattern_spans = find_pattern_spans(text)

    pattern_ranges = [(s["start"], s["end"]) for s in pattern_spans]
    kept_model_spans = [
        s for s in model_spans
        if not any(s["start"] < pe and ps < s["end"] for ps, pe in pattern_ranges)
    ]

    merged = kept_model_spans + pattern_spans
    echoed_name_spans = find_email_echoed_name_spans(text, merged)
    merged = merged + echoed_name_spans
    merged.sort(key=lambda s: s["start"])
    return merged


# ---------------------------------------------------------------------------
# CLI smoke test -- run wherever the real checkpoint actually lives.
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("checkpoint", help="path to a trained checkpoint dir "
                    "(e.g. model/checkpoints/xlmr-large-4lang)")
    ap.add_argument("text", nargs="?",
                    help="text to run detection on; reads stdin if omitted")
    args = ap.parse_args(argv)

    text = args.text if args.text is not None else sys.stdin.read()
    print(f"Loading {args.checkpoint!r}...", file=sys.stderr)
    model, tokenizer, id2label = load_model(args.checkpoint)
    print(f"  {len(id2label)} labels, device={next(model.parameters()).device}",
          file=sys.stderr)

    spans = detect_entities(text, model, tokenizer, id2label)
    print(json.dumps(spans, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
