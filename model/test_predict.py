"""Tests for predict.py. No downloaded model weights required -- same policy
as scripts/test_prepare_splits.py.

`_decode_window_spans` / `_merge_window_spans` are pure functions tested
directly with hand-built fixtures. The end-to-end test uses the REAL
xlm-roberta-large tokenizer (cached locally, no fine-tuned weights needed)
wired to a FAKE model whose "predictions" are the real ground-truth labels
from data/processed/merged/test.docs.jsonl, computed via
prepare_splits.align_labels_for_window -- the same function that produced
the training labels in the first place. This proves the windowing, decoding,
and cross-window merge logic correctly reconstructs real documents' real
entities, independent of whether the actual trained checkpoint is any good.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT / "scripts"))

import predict  # noqa: E402
from predict import (IGNORE_LABEL_ID, _decode_window_spans,  # noqa: E402
                     _enforce_word_consistency, _merge_window_spans,
                     _tokenize_windows, detect_entities, hybrid_detect_entities)

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond, name, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(f"{name}: {detail}" if detail is not None else name)


ID2LABEL = {0: "O", 1: "B-GIVENNAME", 2: "I-GIVENNAME",
            3: "B-CITY", 4: "I-CITY", 5: "B-EMAIL", 6: "I-EMAIL"}


# ---------------------------------------------------------------------------
print("1. _decode_window_spans")
# ---------------------------------------------------------------------------

# "Kamil Aygunov" -- B-GIVENNAME then I-GIVENNAME -> one span covering both.
offs = [(0, 0), (0, 5), (6, 13), (0, 0)]
preds = [IGNORE_LABEL_ID, 1, 2, IGNORE_LABEL_ID]
got = _decode_window_spans(offs, preds, ID2LABEL)
check(got == [{"start": 0, "end": 13, "label": "GIVENNAME"}],
      "B- then I- of the same type merges into one span", got)

# Two adjacent same-type entities, each with its OWN B-: must NOT merge into
# one -- mirrors align_labels_for_window's own test for the forward direction.
offs2 = [(0, 5), (6, 11)]
preds2 = [1, 1]  # B-GIVENNAME, B-GIVENNAME
got2 = _decode_window_spans(offs2, preds2, ID2LABEL)
check(got2 == [{"start": 0, "end": 5, "label": "GIVENNAME"},
              {"start": 6, "end": 11, "label": "GIVENNAME"}],
      "two adjacent B-'s stay two spans, not one", got2)

# Orphan I- (no preceding B- of the same type, e.g. this window only sees the
# tail of an entity that started in a previous window): starts a fresh span
# rather than being dropped.
offs3 = [(0, 0), (5, 13), (0, 0)]
preds3 = [IGNORE_LABEL_ID, 4, IGNORE_LABEL_ID]  # bare I-CITY
got3 = _decode_window_spans(offs3, preds3, ID2LABEL)
check(got3 == [{"start": 5, "end": 13, "label": "CITY"}],
      "an orphan I- with no preceding B- still starts a span, not dropped",
      got3)

# I- immediately following a B- of a DIFFERENT label (a model mistake): must
# close the first span and open a new one, not silently extend across types.
offs4 = [(0, 5), (6, 11)]
preds4 = [1, 4]  # B-GIVENNAME, I-CITY
got4 = _decode_window_spans(offs4, preds4, ID2LABEL)
check(got4 == [{"start": 0, "end": 5, "label": "GIVENNAME"},
              {"start": 6, "end": 11, "label": "CITY"}],
      "I- of a different label than the open span closes it and starts a new one",
      got4)

# A special token mid-sequence closes (flushes) any open span rather than
# silently bridging across it or dropping it -- and the I- token after it is
# correctly treated as an orphan starting its OWN span (per the orphan
# handling above), not dropped either. Two legitimate detections, not one:
# this scenario doesn't occur in real windowing (special tokens only appear
# at a window's edges, never mid-sequence), but the function's behaviour in
# isolation should still be the same either way.
offs5 = [(0, 5), (0, 0), (6, 11)]
preds5 = [1, IGNORE_LABEL_ID, 2]
got5 = _decode_window_spans(offs5, preds5, ID2LABEL)
check(got5 == [{"start": 0, "end": 5, "label": "GIVENNAME"},
              {"start": 6, "end": 11, "label": "GIVENNAME"}],
      "a special token flushes the open span instead of bridging across it",
      got5)

# Pure "O" sequence: nothing.
check(_decode_window_spans([(0, 5), (6, 8)], [0, 0], ID2LABEL) == [],
      "an all-O window decodes to no spans")


# ---------------------------------------------------------------------------
print("2. _merge_window_spans")
# ---------------------------------------------------------------------------

# Exact duplicate from two overlapping windows -> one survives.
dupe = [{"start": 10, "end": 20, "label": "CITY"},
        {"start": 10, "end": 20, "label": "CITY"}]
check(_merge_window_spans(dupe) == [{"start": 10, "end": 20, "label": "CITY"}],
      "exact-duplicate candidates from two windows collapse to one")

# One window saw the entity whole; a neighbour, cut by the window boundary,
# only saw a suffix of it. Longest wins.
partial = [{"start": 100, "end": 120, "label": "STREET"},
          {"start": 110, "end": 120, "label": "STREET"}]
check(_merge_window_spans(partial) == [{"start": 100, "end": 120, "label": "STREET"}],
      "a window-boundary-truncated partial span loses to the whole one",
      _merge_window_spans(partial))

# An entity longer than one window (a full-length PEM key) arrives as
# overlapping pieces from three windows, none of them whole: they are one
# entity and must be joined, not reduced to the longest piece (v3 root
# causes, section 2: 43.7% of each probe key was left unmasked).
pieces = [{"start": 9, "end": 1200, "label": "PRIVATE_KEY"},
          {"start": 700, "end": 2500, "label": "PRIVATE_KEY"},
          {"start": 2000, "end": 3100, "label": "PRIVATE_KEY"}]
check(_merge_window_spans(pieces) == [{"start": 9, "end": 3100, "label": "PRIVATE_KEY"}],
      "overlapping same-label pieces of a long entity are joined into one span",
      _merge_window_spans(pieces))

# Touching but not overlapping same-label spans stay two entities
# ("Əli" and "Vəli" written without a gap is not one name).
touching = [{"start": 0, "end": 3, "label": "GIVENNAME"},
            {"start": 3, "end": 7, "label": "GIVENNAME"}]
check(_merge_window_spans(touching) == touching,
      "touching same-label spans are not joined", _merge_window_spans(touching))

# Two genuinely different, non-overlapping spans both survive, in order.
disjoint = [{"start": 50, "end": 60, "label": "EMAIL"},
           {"start": 10, "end": 20, "label": "CITY"}]
check(_merge_window_spans(disjoint) ==
      [{"start": 10, "end": 20, "label": "CITY"},
       {"start": 50, "end": 60, "label": "EMAIL"}],
      "non-overlapping spans both survive, sorted by position")


# ---------------------------------------------------------------------------
print("2b. _enforce_word_consistency")
# ---------------------------------------------------------------------------
# Real case that motivated this: 'Gədəbəy' (one word) tokenizes into 4
# subwords; the model predicted CITY, CITY, GIVENNAME, CITY across them,
# the third piece ('bə' alone) genuinely ambiguous at 53% confidence.
ID2ID = {v: k for k, v in ID2LABEL.items()}

# G / ədə / bə / y -- all character-adjacent (offsets touch, no gap) ->
# one word. Highest confidence (0.700, the first token) is CITY, so every
# token in the word should end up CITY, B- on the first, I- on the rest.
text_gedebey = "Gədəbəy"
offs_gedebey = [(0, 1), (1, 4), (4, 6), (6, 7)]
preds_gedebey = [3, 4, 2, 4]  # B-CITY, I-CITY, I-GIVENNAME, I-CITY
conf_gedebey = [0.700, 0.638, 0.534, 0.597]
corrected = _enforce_word_consistency(offs_gedebey, preds_gedebey,
                                      conf_gedebey, ID2LABEL, ID2ID,
                                      text_gedebey)
check(corrected == [3, 4, 4, 4],
      "the word's most-confident subword (CITY, 70%) wins for the whole "
      "word, overriding the low-confidence (53%) mid-word flip to "
      "GIVENNAME", corrected)

# Same shape, but the most confident subword says O -- the whole word
# should become O, not just the winning token.
preds_o_wins = [3, 4, 0, 4]  # B-CITY, I-CITY, O, I-CITY
conf_o_wins = [0.55, 0.51, 0.91, 0.52]
corrected_o = _enforce_word_consistency(offs_gedebey, preds_o_wins,
                                        conf_o_wins, ID2LABEL, ID2ID,
                                        text_gedebey)
check(corrected_o == [0, 0, 0, 0],
      "a high-confidence O among the word's subwords wins the same way "
      "an entity label would", corrected_o)

# A lone, non-adjacent token (its own one-token 'word') is never touched,
# regardless of its confidence -- there's no disagreement to resolve.
offs_lone = [(0, 5)]
preds_lone = [1]  # B-GIVENNAME
conf_lone = [0.12]  # very low confidence, but nothing to compare it against
corrected_lone = _enforce_word_consistency(offs_lone, preds_lone, conf_lone,
                                           ID2LABEL, ID2ID, "Kamil")
check(corrected_lone == [1],
      "a single-token word is left exactly as predicted, however low its "
      "own confidence", corrected_lone)

# Multi-word entity continuity: "Fazil Hüseynov" as two SEPARATE words
# (space between them -- offsets are NOT adjacent), each word itself split
# into subwords the model agrees on internally. The second word's first
# token must come out I-GIVENNAME (continuing), not B-GIVENNAME (which
# would wrongly split the entity into two spans downstream).
text_two_words = "Fazil Hüseynov"
offs_two_words = [(0, 2), (2, 5),   # "Fa" "zil"   (word 1)
                  (6, 10), (10, 13)]  # "Hüse" "yno" (word 2, starts at 6:
                                      # gap between 5 and 6 is the space)
preds_two_words = [1, 2, 2, 2]  # B-GIVEN, I-GIVEN, I-GIVEN, I-GIVEN
conf_two_words = [0.9, 0.85, 0.8, 0.88]
corrected_two = _enforce_word_consistency(offs_two_words, preds_two_words,
                                          conf_two_words, ID2LABEL, ID2ID,
                                          text_two_words)
check(corrected_two == [1, 2, 2, 2],
      "a second word the model continues (I- on its first token) stays one "
      "entity with the word before it", corrected_two)

# D-51b: when the model itself starts a new entity on the second word (B-),
# the decoder keeps two spans -- a given name and the father's name are two
# GIVENNAME spans (D-39b), and forcing I- merged them (264 of 542 audited
# disagreements in the v3 label-noise review).
preds_new_entity = [1, 2, 1, 2]  # B-GIVEN, I-GIVEN, B-GIVEN, I-GIVEN
corrected_new = _enforce_word_consistency(offs_two_words, preds_new_entity,
                                          conf_two_words, ID2LABEL, ID2ID,
                                          text_two_words)
check(corrected_new == [1, 2, 1, 2],
      "a second same-label word the model starts with B- stays a separate "
      "entity (given name + father's name)", corrected_new)

# Digit groups keep the old stitching: a grouped number is one value even if
# the model flickers to B- on a later group (D-51b; cards lost 1.1 F1 otherwise).
text_digits = "4169 7385"
offs_digits = [(0, 2), (2, 4), (5, 7), (7, 9)]
preds_digits = [5, 6, 5, 6]  # B-EMAIL stands in for any label: B, I, B, I
corrected_digits = _enforce_word_consistency(offs_digits, preds_digits,
                                             [0.9, 0.9, 0.9, 0.9], ID2LABEL, ID2ID,
                                             text_digits)
check(corrected_digits == [5, 6, 6, 6],
      "a digit group after a same-label digit group continues the value",
      corrected_digits)

# Special tokens (start == end) sit between two real words and must not be
# treated as adjacent to either -- and must not corrupt the continuity
# tracking used for the word that follows them.
offs_special = [(0, 2), (2, 5), (0, 0), (6, 10), (10, 13)]
preds_special = [1, 2, IGNORE_LABEL_ID, 2, 2]  # the model continues the entity (D-51b)
conf_special = [0.9, 0.85, 0.0, 0.8, 0.88]
corrected_special = _enforce_word_consistency(offs_special, preds_special,
                                              conf_special, ID2LABEL, ID2ID,
                                              text_two_words)
check(corrected_special[2] == IGNORE_LABEL_ID,
      "a special token's own id is left completely untouched", corrected_special)
check(corrected_special == [1, 2, IGNORE_LABEL_ID, 2, 2],
      "continuity still carries across a special token to the next real "
      "word, same as if it weren't there", corrected_special)

# Regression test for a real, shipped-then-caught bug: a name immediately
# followed by punctuation with NO space ("Bərgah:") is character-adjacent
# to the colon, but the colon must NEVER join the word -- an earlier
# version grouped them, and the colon's confident O-prediction overwrote a
# fully correct GIVENNAME detection. Confirmed against the real model
# (your-hf-org/masking-multilingual) before this test was written: exact
# token/offset/confidence values below are the real per-token output for
# '[14:22] Bərgah: Sabah...', not invented.
text_colon = "Bərgah: Sabah"
offs_colon = [(0, 2), (2, 3), (3, 6),   # 'Bə' 'r' 'gah'  (the name)
             (6, 7),                    # ':'            (must stay isolated)
             (8, 13)]                   # 'Sabah'
preds_colon = [1, 2, 2, 0, 0]  # B-GIVEN, I-GIVEN, I-GIVEN, O, O
conf_colon = [0.994, 0.994, 0.993, 1.000, 1.000]
corrected_colon = _enforce_word_consistency(offs_colon, preds_colon,
                                            conf_colon, ID2LABEL, ID2ID,
                                            text_colon)
check(corrected_colon == [1, 2, 2, 0, 0],
      "a name immediately followed by punctuation with no space keeps its "
      "own correct label -- the punctuation's confident O never joins "
      "(and never overwrites) the word before it", corrected_colon)

# Regression test for a second real, shipped-then-caught bug: punctuation
# GENUINELY INSIDE an entity (a phone number's own hyphens) must still
# carry continuity through itself, even though it's never corrected -- AND
# that continuity must reach all the way into the NEXT correction decision
# for a multi-token word right after it. '+994-77...': every token,
# including every '-', predicted I-TELEPHONENUM at ~100% confidence in
# the real model (relabelled B-/I-CITY here only because the test fixture
# has no TELEPHONENUM id); '994' itself splits into two real subwords
# ('99' + '4'), so it's a length-2 word that goes through the correction
# branch -- exactly where the bug showed up (it came out with a spurious
# fresh B- because continuity had already been lost at the '+').
text_phone2 = "+994-77"
offs_phone2 = [(0, 1), (1, 3), (3, 4), (4, 5), (5, 7)]  # '+' '99' '4' '-' '77'
preds_phone2 = [3, 4, 4, 4, 4]  # B-CITY, I-CITY, I-CITY, I-CITY, I-CITY
conf_phone2 = [0.999, 1.000, 1.000, 1.000, 1.000]
corrected_phone2 = _enforce_word_consistency(offs_phone2, preds_phone2,
                                             conf_phone2, ID2LABEL, ID2ID,
                                             text_phone2)
check(corrected_phone2 == [3, 4, 4, 4, 4],
      "continuity carried through a punctuation token reaches the next "
      "multi-token word too -- '99'+'4' gets I- (continuing the span "
      "from '+'), not a spurious fresh B- that would split one entity "
      "into two", corrected_phone2)


# ---------------------------------------------------------------------------
print("3. End-to-end: real tokenizer + real ground-truth labels, fake model")
# ---------------------------------------------------------------------------
try:
    import torch
    from transformers import AutoTokenizer
    from prepare_splits import add_punctuation_boundary, align_labels_for_window

    tok = AutoTokenizer.from_pretrained("xlm-roberta-large")
    add_punctuation_boundary(tok)

    labels_data = json.loads(
        (ROOT / "data/processed/merged/labels.json").read_text(encoding="utf-8"))
    label2id = {k: int(v) for k, v in labels_data["label2id"].items()}
    id2label_real = {int(k): v for k, v in labels_data["id2label"].items()}
    num_labels = len(labels_data["labels"])

    class _FakeConfig:
        pass

    class _FakeModel:
        """Mimics the one call shape detect_entities needs:
        model(input_ids=..., attention_mask=...).logits -- returning
        one-hot logits over the REAL ground-truth label at each position,
        computed the exact same way training labels were computed."""

        def __init__(self, entities):
            self.entities = entities

        def parameters(self):
            yield torch.zeros(1)

        def __call__(self, input_ids, attention_mask):
            offs = self._last_offsets
            gold_ids = align_labels_for_window(offs, self.entities, label2id)
            seq_len = input_ids.shape[1]
            logits = torch.zeros(1, seq_len, num_labels)
            for i, lid in enumerate(gold_ids):
                logits[0, i, lid if lid != IGNORE_LABEL_ID else 0] = 10.0

            class _Out:
                pass
            out = _Out()
            out.logits = logits
            return out

        def to(self, device):
            return self

        def eval(self):
            return self

    # Monkeypatch detect_entities' window loop to hand the fake model each
    # window's offsets, since a real model call doesn't need them but this
    # fake one does to look up the gold labels for that exact window.
    def _detect_with_fake(text, entities, max_length=512, stride=256):
        enc = _tokenize_windows(text, tok, max_length, stride)
        fake = _FakeModel(entities)
        candidates = []
        for w in range(len(enc["input_ids"])):
            fake._last_offsets = enc["offset_mapping"][w]
            input_ids = torch.tensor([enc["input_ids"][w]])
            attention_mask = torch.tensor([enc["attention_mask"][w]])
            logits = fake(input_ids=input_ids, attention_mask=attention_mask).logits[0]
            pred_ids = logits.argmax(dim=-1).tolist()
            candidates.extend(_decode_window_spans(
                enc["offset_mapping"][w], pred_ids, id2label_real))
        merged = _merge_window_spans(candidates)
        return [{"start": s["start"], "end": s["end"], "label": s["label"],
                 "text": text[s["start"]:s["end"]]} for s in merged]

    # Pick a handful of real documents, including at least one long enough to
    # span multiple windows (multi-window merge is the part with real risk).
    docs = []
    with (ROOT / "data/processed/merged/test.docs.jsonl").open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("lang") == "az" and r.get("entities"):
                docs.append(r)
            if len(docs) >= 60:
                break

    long_docs = [d for d in docs if len(d["text"]) > 2200]
    sample = docs[:8] + long_docs[:4]
    check(len(sample) > 0, "found real AZ ground-truth documents to test against",
          len(docs))
    check(any(len(d["text"]) > 2200 for d in sample),
          "at least one sampled document is long enough to exercise multi-window merge")

    exact_matches = 0
    total_entities = 0
    for doc in sample:
        gold = sorted(({"start": e["start"], "end": e["end"], "label": e["label"]}
                       for e in doc["entities"]),
                      key=lambda x: x["start"])
        pred = _detect_with_fake(doc["text"], doc["entities"])
        pred_stripped = [{"start": p["start"], "end": p["end"], "label": p["label"]}
                         for p in pred]
        total_entities += len(gold)
        if pred_stripped == gold:
            exact_matches += 1
        else:
            missing = [g for g in gold if g not in pred_stripped]
            extra = [p for p in pred_stripped if p not in gold]
            if missing or extra:
                FAILURES.append(
                    f"doc {doc.get('id', '?')}: missing={missing[:2]} "
                    f"extra={extra[:2]}")

    check(exact_matches == len(sample),
          f"reconstructed entities exactly match ground truth on all "
          f"{len(sample)} sampled real documents ({total_entities} entities "
          f"total)", f"{exact_matches}/{len(sample)} exact")

except ImportError as exc:
    print(f"  SKIPPED (missing dependency: {exc})")
except FileNotFoundError as exc:
    print(f"  SKIPPED (missing data file: {exc})")


# ---------------------------------------------------------------------------
print("4. hybrid_detect_entities: pattern fallback fills in what the model "
      "misses")
# ---------------------------------------------------------------------------
# Real-model testing found the trained checkpoint
# genuinely misses DATE and EMAIL in a lot of ordinary sentence phrasing.
# detect_entities itself must never be patched to paper over that -- it
# exists to prove the decode/merge logic faithfully reflects whatever the
# model actually predicted, nothing more. hybrid_detect_entities is the
# separate, real fix: it's tested here by monkeypatching detect_entities to
# reproduce that exact observed failure mode (model finds CITY, misses
# DATE/EMAIL/TELEPHONENUM entirely) and confirming the pattern-tier
# fallback still recovers them, with no tokenizer or model weights needed.
_real_detect_entities = predict._detect_entities_word_consistent


doc = ("Mənim adım Əli Məmmədovdur və Bakı şəhərində yaşayıram. "
       "Sizə 15.03.2024 tarixində göndərdiyim sifarişlə bağlı narahatlığımı "
       "bildirmək istəyirəm.\nTelefon: 0501234567\n"
       "E-poçt: eli.mammadov@example.com\nVÖEN: 1503613621")
_city_start = doc.index("Bakı")


def _model_missing_pattern_tier(text, model, tokenizer, id2label, **kwargs):
    return [{"start": _city_start, "end": _city_start + 4, "label": "CITY",
             "text": "Bakı"}]

predict._detect_entities_word_consistent = _model_missing_pattern_tier
try:
    hybrid = hybrid_detect_entities(doc, None, None, None)
finally:
    predict._detect_entities_word_consistent = _real_detect_entities

hybrid_labels = sorted(s["label"] for s in hybrid)
check(hybrid_labels == ["AZ_VOEN", "CITY", "DATE", "EMAIL", "TELEPHONENUM"],
      "every pattern-tier entity the fake model missed is recovered by the "
      "fallback, AND the model's own CITY hit is kept alongside them",
      hybrid_labels)
check(all(doc[s["start"]:s["end"]] == s["text"] for s in hybrid),
      "every merged span (model or fallback) has correct offsets into the "
      "original text")


def _model_finds_email_as_garbage_fragments(text, model, tokenizer, id2label,
                                             **kwargs):
    # Reproduces the real observed bug: the model tags disjoint punctuation
    # fragments of an email instead of one span covering the whole address.
    idx = text.index("@")
    return [{"start": idx, "end": idx + 1, "label": "EMAIL", "text": "@"}]


email_doc = "E-poçt: eli.mammadov@example.com filan"
email_start = email_doc.index("eli.mammadov")
email_end = email_start + len("eli.mammadov@example.com")

predict._detect_entities_word_consistent = _model_finds_email_as_garbage_fragments
try:
    hybrid2 = hybrid_detect_entities(email_doc, None, None, None)
finally:
    predict._detect_entities_word_consistent = _real_detect_entities

check(hybrid2 == [{"start": email_start, "end": email_end, "label": "EMAIL",
                   "text": "eli.mammadov@example.com"}],
      "a verified full-address pattern match REPLACES the model's "
      "overlapping garbage fragment rather than the two coexisting",
      hybrid2)


def _model_misses_name_echoed_in_email(text, model, tokenizer, id2label,
                                       **kwargs):
    # Reproduces the real observed bug: a name goes undetected specifically
    # because a name-derived email also appears in the same short document.
    return []


name_echo_doc = ("Mən Nərmin Kərimova, işə qəbul üçün müraciət edirəm.\n"
                 "E-poçt: nermin.kerimova@mail.az\n\nHörmətlə,\nNərmin Kərimova")
predict._detect_entities_word_consistent = _model_misses_name_echoed_in_email
try:
    hybrid3 = hybrid_detect_entities(name_echo_doc, None, None, None)
finally:
    predict._detect_entities_word_consistent = _real_detect_entities

hybrid3_labels = sorted(s["label"] for s in hybrid3)
check(hybrid3_labels == ["EMAIL", "GIVENNAME", "GIVENNAME", "GIVENNAME",
                         "GIVENNAME"],
      "hybrid_detect_entities' third pass recovers both standalone "
      "mentions of a name the fake model missed entirely, purely from "
      "cross-referencing the EMAIL the second pass already verified",
      hybrid3_labels)



# ---------------------------------------------------------------------------
# Validity check (after-A5 plan, 21 Oct): impossible TIME/DATE/CVV values are
# not masked; real values and noisy (OCR/typo) values are always kept.
# ---------------------------------------------------------------------------
from predict import _value_possible, _drop_impossible_values

for label, value, expect in [
    ("TIME", "24:51", False), ("TIME", "27:49", False), ("TIME", "19:63", False),
    ("TIME", "14:05:61", False), ("TIME", "24:00", True), ("TIME", "23:59", True),
    ("TIME", "00:00", True), ("TIME", "14:05:22", True), ("TIME", "7:30 PM", True),
    ("DATE", "30.02.2027", False), ("DATE", "31.04.2026", False), ("DATE", "15.13.2026", False),
    ("DATE", "2026-02-30", False), ("DATE", "29.02.2023", False), ("DATE", "29.02.2024", True),
    ("DATE", "31.05.2026", True), ("DATE", "2026-10-21", True), ("DATE", "02/13/2024", True),
    ("DATE", "30 fevral 2027", False), ("DATE", "30 февраля 2027", False),
    ("DATE", "30 Şubat 2027", False), ("DATE", "February 30, 2027", False),
    ("DATE", "31 mart 2026", True), ("DATE", "21 октября 2026", True),
    ("DATE", "21 Ekim 2026", True), ("DATE", "October 21st, 2026", True),
    ("DATE", "l976-02-19", True), ("DATE", "220.09.2022", True),   # noisy: kept
    ("CARD_SECURITY_CODE", "18275", False), ("CARD_SECURITY_CODE", "12", False),
    ("CARD_SECURITY_CODE", "123", True), ("CARD_SECURITY_CODE", "1234", True),
    ("CARD_SECURITY_CODE", "12-3", True),                          # dashed CVV is real (D-30b)
    ("PAYMENT_CARD_NUMBER", "1234", True),                         # other labels untouched
]:
    check(_value_possible(label, value) is expect,
          f"validity: {label} {value!r} -> {'kept' if expect else 'dropped'}")

_t = "Qatar saat 24:51 radələrində, 14:30-da isə yenidən çatır."
for _v, _lab, _expect in [("A12B34", "AZ_FIN", []), ("4111 1111 1111 1111", "PAYMENT_CARD_NUMBER", []),
                          ("12:34:56", "TIME", []), ("1234", "CARD_SECURITY_CODE", ["1234"]),
                          ("4111111111111112", "PAYMENT_CARD_NUMBER", ["4111111111111112"])]:
    _txt = f"Dəyər: {_v}"
    _got = _drop_impossible_values([{"start": 7, "end": 7 + len(_v), "label": _lab}], _txt)
    check([_txt[g["start"]:g["end"]] for g in _got] == _expect,
          f"D-2 dummies: {_v!r} {'kept masked' if _expect else 'never masked'}", _got)

_a, _b = _t.index("24:51"), _t.index("14:30")
_kept = _drop_impossible_values([{"start": _a, "end": _a + 5, "label": "TIME"},
                                 {"start": _b, "end": _b + 5, "label": "TIME"}], _t)
check([_t[s["start"]:s["end"]] for s in _kept] == ["14:30"],
      "validity: an impossible time is dropped, the real one in the same text is kept",
      _kept)


# ---------------------------------------------------------------------------
print()
print("=" * 62)
print(f"PASSED {PASS}   FAILED {FAIL}")
for f in FAILURES[:25]:
    print("  FAIL:", f)
print("=" * 62)
sys.exit(1 if FAIL else 0)
