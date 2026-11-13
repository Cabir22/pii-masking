"""Tests for prepare_splits.py (Stage 3). No network required except for the
one section explicitly marked -- everything else uses a hand-crafted offset
list or an in-process tiny BPE tokenizer, never a downloaded model."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from prepare_splits import (       # noqa: E402
    IGNORE_LABEL_ID, add_punctuation_boundary, align_labels_for_window,
    build_label_list, dedup, main, revalidate, stratified_split,
    tokenize_split,
)
from piigen.config import ENTITY_TYPES  # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond, name, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        msg = f"{name}: {detail}" if detail is not None else name
        FAILURES.append(msg)


def make_record(rid, text, entities, lang="az"):
    return {"id": rid, "text": text, "lang": lang, "entities": entities}


def ent(label, start, end, text):
    return {"label": label, "start": start, "end": end, "text": text}


# ---------------------------------------------------------------------------
print("1. Label list")
# ---------------------------------------------------------------------------
labels = build_label_list()
check(labels[0] == "O", "first label is O")
check(len(labels) == 1 + 2 * len(ENTITY_TYPES),
      "one O plus B-/I- per entity type", len(labels))
check(len(labels) == len(set(labels)), "no duplicate labels")
check("B-GIVENNAME" in labels and "I-GIVENNAME" in labels,
      "spot check: GIVENNAME has both B and I")


# ---------------------------------------------------------------------------
print("2. align_labels_for_window")
# ---------------------------------------------------------------------------
label2id = {l: i for i, l in enumerate(build_label_list())}
id2label = {i: l for l, i in label2id.items()}

# "Ad: Kamil, Soyad: Rustemov" -- offsets by hand.
text = "Ad: Kamil, Soyad: Rustemov"
entities = [ent("GIVENNAME", 4, 9, "Kamil"), ent("SURNAME", 18, 27, "Rustemov")]
# One token per character range for simplicity (word-level, not subword).
offsets = [(0, 0), (0, 2), (4, 9), (18, 27), (0, 0)]
got = align_labels_for_window(offsets, entities, label2id)
want = [IGNORE_LABEL_ID, label2id["O"], label2id["B-GIVENNAME"],
        label2id["B-SURNAME"], IGNORE_LABEL_ID]
check(got == want, "basic B-/O/special-token alignment", got)

# Adjacent same-type entities: two different GIVENNAME mentions back to back
# with no separator ("KamilAygun" as two names glued in the raw string is
# unrealistic, but two tokens with touching spans is a real subword case --
# what matters is each entity's OWN start still gets its OWN B-).
text2 = "Kamil Aygun"
entities2 = [ent("GIVENNAME", 0, 5, "Kamil"), ent("GIVENNAME", 6, 11, "Aygun")]
offsets2 = [(0, 5), (6, 11)]
got2 = align_labels_for_window(offsets2, entities2, label2id)
check(got2 == [label2id["B-GIVENNAME"], label2id["B-GIVENNAME"]],
      "two adjacent same-type entities each get their own B-, not B-then-I-",
      got2)

# A single entity split across two subword tokens: second token must be I-,
# not a second B-, because tok_start != entity_start for it.
entities3 = [ent("SURNAME", 0, 9, "Mammadova")]
offsets3 = [(0, 4), (4, 9)]   # "Mamm" + "adova", one entity, two tokens
got3 = align_labels_for_window(offsets3, entities3, label2id)
check(got3 == [label2id["B-SURNAME"], label2id["I-SURNAME"]],
      "one entity split across two tokens: B- then I-, not B- then B-", got3)

# Sliding-window continuation: window 2's offsets are in ORIGINAL document
# coordinates (as real tokenizer output is, verified empirically before
# writing this), so an entity that started in window 1 and continues into
# window 2 must be seen as I- again in window 2, not a fresh B-.
entities4 = [ent("EMAIL", 10, 30, "someone@example.com")]
window1_offsets = [(0, 0), (10, 15), (15, 20)]           # entity starts here
window2_offsets = [(0, 0), (20, 25), (25, 30)]           # continues here
w1 = align_labels_for_window(window1_offsets, entities4, label2id)
w2 = align_labels_for_window(window2_offsets, entities4, label2id)
check(w1 == [IGNORE_LABEL_ID, label2id["B-EMAIL"], label2id["I-EMAIL"]],
      "window 1: entity start gets B-", w1)
check(w2 == [IGNORE_LABEL_ID, label2id["I-EMAIL"], label2id["I-EMAIL"]],
      "window 2: same entity continuing gets I-, not a new B-", w2)

# 2026-08-30: xlm-roberta-large's real fast tokenizer, on real corpus text
# ("...CVV: 483..."), produced a standalone metaspace token whose offset
# OVERLAPS the following real token's first character instead of ending
# where it starts -- '▁' at (10, 11) immediately followed by '483' at
# (10, 13), both starting at 10. Naive `tok_start == e["start"]` makes both
# true -> double B-, an invalid BIO sequence. Confirmed on the real
# corpus: 21.4% of tokenized windows (150,825 total), 41,828 occurrences --
# not a rare edge case. This exact offset pair, unmodified from what the
# real tokenizer produced.
entities5 = [ent("CARD_SECURITY_CODE", 10, 13, "483")]
offsets5 = [(0, 0), (0, 4), (5, 6), (6, 8), (8, 9), (10, 11), (10, 13),
           (14, 18), (0, 0)]
got5 = align_labels_for_window(offsets5, entities5, label2id)
want5 = [IGNORE_LABEL_ID, label2id["O"], label2id["O"], label2id["O"],
        label2id["O"], label2id["B-CARD_SECURITY_CODE"],
        label2id["I-CARD_SECURITY_CODE"], label2id["O"], IGNORE_LABEL_ID]
check(got5 == want5,
      "overlapping tokenizer offsets for one entity: B- then I-, not B- then B-",
      got5)


# ---------------------------------------------------------------------------
print("3. dedup")
# ---------------------------------------------------------------------------
r1 = make_record("a", "text one", [])
# Same id as r1, DIFFERENT text -- exactly what two independent generation
# runs produce (both number their output from 0). Must survive: an id
# collision across files is not evidence of duplication.
r2 = make_record("a", "a completely different document", [])
r3 = make_record("b", "text one", [])           # different id, SAME text
r4 = make_record("c", "genuinely unique text", [])
out, dupes = dedup([r1, r2, r3, r4])
check(dupes == 1, "only the genuine text duplicate is dropped, "
     "not the id collision", dupes)
check([r["id"] for r in out] == ["a", "a", "c"],
      "id collision with different text survives dedup", [r["id"] for r in out])


# ---------------------------------------------------------------------------
print("4. revalidate")
# ---------------------------------------------------------------------------
_good_text = "Salam, mənim adım Kamildir və bura yaza bilərsiniz."
_good_val = "Kamil"
_good_start = _good_text.index(_good_val)
good = make_record("g1", _good_text,
                   [ent("GIVENNAME", _good_start, _good_start + len(_good_val),
                        _good_val)])
# offset text mismatch -> should fail validate_example
bad = make_record("b1", "Salam, mənim adım Kamildir.",
                  [ent("GIVENNAME", 0, 5, "WRONG")])
clean, rejected = revalidate([good, bad])
check(len(rejected) == 1 and rejected[0][0] == "b1",
      "revalidate rejects a broken offset/text mismatch", rejected)
check(len(clean) <= 1, "revalidate does not blindly pass everything")


# ---------------------------------------------------------------------------
print("5. stratified_split")
# ---------------------------------------------------------------------------
_value_rng = None


def _fake_doc(i, label):
    global _value_rng
    if _value_rng is None:
        import random as _r
        from piigen.values import ValueFactory, ValuePool
        _value_rng = ValueFactory(_r.Random(0), ValuePool())
    value = _value_rng.make(label, "az")
    text = f"Sənəddə {value} göstərilib və burada bəzi əlavə mətn də var."
    start = text.index(value)
    return make_record(f"d{i}", text,
                       [ent(label, start, start + len(value), value)])

# One common label (20 docs) and one rare label (2 docs) -- the rare one is
# too small to fractionally split and must land entirely in train.
records = ([_fake_doc(i, "GIVENNAME") for i in range(20)]
          + [_fake_doc(100 + i, "AZ_VOEN") for i in range(2)])
train, val, test = stratified_split(records, val_frac=0.1, test_frac=0.1, seed=1)
all_ids = [r["id"] for r in train] + [r["id"] for r in val] + [r["id"] for r in test]
check(len(all_ids) == len(records), "every record lands in exactly one split",
      (len(all_ids), len(records)))
check(len(set(all_ids)) == len(all_ids), "no record duplicated across splits")
check(len(val) > 0 and len(test) > 0,
      "the larger group actually gets split, not all dumped into train")
rare_ids = {f"d10{i}" for i in range(2)}
train_ids = {r["id"] for r in train}
check(rare_ids <= train_ids,
      "a 2-doc rare-label group is too small to fractionally split, stays in train",
      rare_ids - train_ids)

# Determinism: same seed -> same split.
train2, val2, test2 = stratified_split(records, 0.1, 0.1, seed=1)
check([r["id"] for r in train] == [r["id"] for r in train2],
      "same seed produces the same split")


# ---------------------------------------------------------------------------
print("5b. group split by template (v4.1, data audit A2)")
# ---------------------------------------------------------------------------
from prepare_splits import _skeleton  # noqa: E402

# 30 templates x 4 documents that differ only in their values, plus 60 one-off
# documents: one template must never sit in two splits
tmpl = []
for t in range(30):
    for k in range(4):
        text = f"Şablon {chr(97 + t % 26)}{chr(97 + t // 26)}: müştərinin adı Leyla{k} kimi yazılıb, qeyd {k}."
        s = text.index(f"Leyla{k}")
        # the value differs per document, the template does not
        tmpl.append(make_record(f"t{t}_{k}", text.replace(f"Leyla{k}", ["Leyla", "Aynur", "Səbinə", "Nərgiz"][k]),
                                [ent("GIVENNAME", s, s + len(["Leyla", "Aynur", "Səbinə", "Nərgiz"][k]),
                                     ["Leyla", "Aynur", "Səbinə", "Nərgiz"][k])]))
one_off = [make_record(f"o{i}", f"Ayrıca sənəd nömrə {'abcdefghij'[i % 10]}{i}: ad Kamran.",
                       [ent("GIVENNAME", len(f"Ayrıca sənəd nömrə {'abcdefghij'[i % 10]}{i}: ad "),
                            len(f"Ayrıca sənəd nömrə {'abcdefghij'[i % 10]}{i}: ad ") + 6, "Kamran")])
           for i in range(60)]
check(len({_skeleton(r) for r in tmpl}) == 30, "documents that differ only in values share a skeleton",
      len({_skeleton(r) for r in tmpl}))
g_train, g_val, g_test = stratified_split(tmpl + one_off, 0.1, 0.1, seed=3, group_key=_skeleton)
where_ = {}
for name, rows in (("train", g_train), ("val", g_val), ("test", g_test)):
    for r in rows:
        where_.setdefault(_skeleton(r), set()).add(name)
check(all(len(s) == 1 for s in where_.values()), "no template is in two splits",
      [k for k, s in where_.items() if len(s) > 1][:2])
check(len(g_train) + len(g_val) + len(g_test) == 180, "every document lands in exactly one split")
check(14 <= len(g_test) <= 22 and 14 <= len(g_val) <= 22, "val and test stay near 10% each",
      (len(g_val), len(g_test)))
g2 = stratified_split(tmpl + one_off, 0.1, 0.1, seed=3, group_key=_skeleton)
check([r["id"] for r in g_test] == [r["id"] for r in g2[2]], "the group split is deterministic")
# the largest template groups go to train first (their lesson is learnt there)
big = [make_record(f"b{i}", "Leyla", [ent("GIVENNAME", 0, 5, "Leyla")]) for i in range(40)]
gb = stratified_split(big + one_off, 0.1, 0.1, seed=3, group_key=_skeleton)
check(all(r["id"].startswith("b") for r in gb[0][:0]) and {r["id"] for r in big} <= {r["id"] for r in gb[0]},
      "a large template group goes to train")
# without group_key the split is the documents-one-by-one split of before
plain = stratified_split(tmpl + one_off, 0.1, 0.1, seed=3)
check(any(len({n for n, rows in zip(("train", "val", "test"), plain) for r in rows if _skeleton(r) == k}) > 1
          for k in {_skeleton(r) for r in tmpl}),
      "(control) one by one, templates do cross splits")
# a look-alike's value is masked too: two documents that differ only there share a skeleton
d1 = {**make_record("x1", "Kod 412 qeyd olunub.", []), "_decoys": [{"start": 4, "end": 7, "resembles": "CARD_SECURITY_CODE"}]}
d2 = {**make_record("x2", "Kod 9X1 qeyd olunub.", []), "_decoys": [{"start": 4, "end": 7, "resembles": "CARD_SECURITY_CODE"}]}
check(_skeleton(d1) == _skeleton(d2), "look-alike values are masked in the skeleton", (_skeleton(d1), _skeleton(d2)))


# ---------------------------------------------------------------------------
print("6. tokenize_split (real in-process tokenizer, no network)")
# ---------------------------------------------------------------------------
from tokenizers import Tokenizer, models, pre_tokenizers, trainers  # noqa: E402
from transformers import PreTrainedTokenizerFast                    # noqa: E402

_raw_tok = Tokenizer(models.BPE(unk_token="[UNK]"))
_raw_tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
_trainer = trainers.BpeTrainer(
    vocab_size=400, special_tokens=["[UNK]", "<s>", "</s>", "<pad>"])
_raw_tok.train_from_iterator(
    ["Salam dunya bu bir metndir", "Ad Soyad Email Telefon nomresi",
     "kamil aygun rustemov mammadova bakida yasayir"] * 5, trainer=_trainer)

tiny_tokenizer = PreTrainedTokenizerFast(
    tokenizer_object=_raw_tok, unk_token="[UNK]", bos_token="<s>",
    eos_token="</s>", pad_token="<pad>")

long_text = ("Kamil aygun bakida yasayir. " * 10) + "email test metni sondadir."
doc = make_record("t1", long_text, [ent("GIVENNAME", 0, 5, "Kamil")])
windows = tokenize_split([doc], tiny_tokenizer, label2id,
                         max_length=16, stride=4)
check(len(windows) > 1, "a long document produces more than one window",
      len(windows))
check(all(len(w["input_ids"]) == len(w["labels"]) for w in windows),
      "every window has one label per token")
check(all(w["id"].startswith("t1__w") for w in windows),
      "window ids are derived from the document id")
check(windows[0]["labels"][:3].count(label2id["B-GIVENNAME"]) <= 1,
      "at most one B-GIVENNAME token in the first window "
      "(the entity is short, should not be split across many tokens here)")

# 2026-08-26: regression for the truncation bug found while researching the
# base model -- a long entity (e.g. ACCESS_TOKEN, measured up to 197 tokens
# on the real corpus) straddling a window boundary was silently never
# captured whole by ANY window when stride < entity length, at every
# max_length/stride combination the CLI defaulted to before that fix. The
# invariant this guards -- stride >= longest entity in tokens -- is a
# property of (text, entity, max_length, stride), not of any one tokenizer,
# so it is verified here with the same offline tiny_tokenizer as the rest of
# this section rather than downloading xlm-roberta-base into the test suite.
_secret = "kamilaygunbakidayasayirrustemovmammadova" * 3
_secret_len = len(tiny_tokenizer(_secret, add_special_tokens=False)["input_ids"])
check(_secret_len >= 20, "fixture entity is long enough to actually test "
      "boundary-straddling with this tokenizer's granularity", _secret_len)

for _pad_words in range(1, 12):
    _text = (("Kamil aygun bakida yasayir. " * _pad_words) + _secret
             + (" metni sondadir." * 3))
    _s = _text.index(_secret)
    _doc = make_record(f"secret{_pad_words}", _text,
                       [ent("ACCESS_TOKEN", _s, _s + len(_secret), _secret)])

    # Unsafe: a window smaller than the entity, with a short stride -- this
    # is what shipped before the fix (max_length=256/stride=32 against a
    # measured 197-token entity), reproduced here as a negative control, not
    # asserted on (a given boundary position may or may not trigger it; the
    # swept measurement during the actual fix, not a single position, is
    # what proved the old default unsafe).
    _small_window = max(_secret_len - 4, 8)
    _unsafe = tokenize_split([_doc], tiny_tokenizer, label2id,
                             max_length=_small_window, stride=2)
    _unsafe_best = max(
        (sum(1 for x in w["labels"] if x != -100 and id2label[x] != "O")
         for w in _unsafe), default=0)

    # Safe: stride >= entity length, with max_length comfortably larger than
    # the stride (same 2x ratio as the real 512/256 default). This is the
    # actual invariant prepare_splits.py's new default relies on.
    _safe = tokenize_split([_doc], tiny_tokenizer, label2id,
                           max_length=_secret_len * 2, stride=_secret_len)
    _safe_best = max(
        (sum(1 for x in w["labels"] if x != -100 and id2label[x] != "O")
         for w in _safe), default=0)
    check(_safe_best >= _secret_len,
          f"stride >= entity length captures it whole in >=1 window "
          f"(pad={_pad_words})", _safe_best)


# ---------------------------------------------------------------------------
print("6b. add_punctuation_boundary (2026-08-26 tokenizer-audit punctuation-weld fix)")
# ---------------------------------------------------------------------------
# Reproduces the real xlm-roberta-large pre-tokenizer shape (confirmed by
# direct inspection of the real tokenizer.json, not assumed): a
# Sequence([WhitespaceSplit(), Metaspace()]). WhitespaceSplit only splits on
# whitespace, so punctuation directly touching a word ("hello!", no space)
# has NO pre-tokenizer boundary before this fix -- which is exactly why the
# real model's BPE vocab was free to learn a merged token spanning across
# it ('92)' in the audit's finding). This is what the fix actually
# guarantees structurally, independent of any specific trained vocab: a
# HARD boundary at every punctuation edge that BPE can never merge across
# afterward. Tested at the pre-tokenizer level (`pre_tokenize_str`), which
# is vocab-independent and needs no trained/downloaded model -- same policy
# as the rest of this file.
from types import SimpleNamespace                                    # noqa: E402

_weld_pretok = pre_tokenizers.Sequence([
    pre_tokenizers.WhitespaceSplit(),
    pre_tokenizers.Metaspace(replacement="▁", prepend_scheme="always",
                             split=True),
])
_weld_backend = Tokenizer(models.BPE())
_weld_backend.pre_tokenizer = _weld_pretok
_weld_tokenizer = SimpleNamespace(backend_tokenizer=_weld_backend)

_weld_text = "say hello! today"
_before = _weld_pretok.pre_tokenize_str(_weld_text)
check(any(piece.endswith("hello!") for piece, _ in _before),
      "fixture reproduces the real weld before patching: 'hello!' has no "
      "pre-tokenizer boundary before the '!'", _before)

_patched = add_punctuation_boundary(_weld_tokenizer)
check(_patched is True, "add_punctuation_boundary reports it patched a "
     "tokenizer with a backend_tokenizer")

_after = _weld_backend.pre_tokenizer.pre_tokenize_str(_weld_text)
check(not any(piece.endswith("hello!") for piece, _ in _after),
      "after patching, 'hello!' is no longer one welded piece", _after)
check(any(piece.endswith("hello") for piece, _ in _after)
      and any(piece == "!" for piece, _ in _after),
      "after patching, 'hello' and '!' are separate pieces with a real "
      "boundary between them -- a token can never span it afterward",
      _after)

# Existing pre-tokenizer steps must survive, not be replaced -- ordinary
# whitespace splitting still works exactly as before.
check(any(piece.endswith("today") for piece, _ in _after),
      "ordinary whitespace-delimited words are still pre-tokenized "
      "normally after patching (existing steps preserved, not dropped)",
      _after)

# A tokenizer with no backend_tokenizer (a slow/Python tokenizer) must be a
# no-op the caller can detect and warn about, not a crash.
check(add_punctuation_boundary(SimpleNamespace()) is False,
      "add_punctuation_boundary returns False (no-op) for a tokenizer "
      "with no backend_tokenizer, rather than raising")

# A tokenizer whose pre-tokenizer is a single step (not already a Sequence)
# must be wrapped, not overwritten -- the existing step must survive.
_single_backend = Tokenizer(models.BPE())
_single_backend.pre_tokenizer = pre_tokenizers.WhitespaceSplit()
_single_tokenizer = SimpleNamespace(backend_tokenizer=_single_backend)
check(add_punctuation_boundary(_single_tokenizer) is True,
      "add_punctuation_boundary patches a tokenizer whose pre-tokenizer "
      "is a single (non-Sequence) step")
_single_after = _single_backend.pre_tokenizer.pre_tokenize_str("hello!")
check(any(piece == "hello" for piece, _ in _single_after)
      and any(piece == "!" for piece, _ in _single_after),
      "the pre-existing single WhitespaceSplit step still runs, plus the "
      "new Punctuation() boundary", _single_after)


# ---------------------------------------------------------------------------
print("7. End-to-end CLI (--no-tokenize, no network needed)")
# ---------------------------------------------------------------------------
tmp = Path(tempfile.mkdtemp())
try:
    raw1 = tmp / "run1.jsonl"
    raw2 = tmp / "run2.jsonl"
    docs_a = [_fake_doc(i, "GIVENNAME") for i in range(15)]
    # Reuses ids 0..14 -- exactly what two independent generation runs do,
    # each numbering from 0. Must NOT be treated as duplicates: different
    # content under a coincidentally-reused id.
    docs_b = [_fake_doc(i, "EMAIL") for i in range(14)]
    # A genuine cross-run duplicate: identical text, appended as one more
    # record in the second file. This one SHOULD be dropped.
    exact_dup = dict(docs_a[0])
    with raw1.open("w", encoding="utf-8") as f:
        for d in docs_a:
            f.write(json.dumps(d) + "\n")
    with raw2.open("w", encoding="utf-8") as f:
        for d in docs_b:
            f.write(json.dumps(d) + "\n")
        f.write(json.dumps(exact_dup) + "\n")

    out_dir = tmp / "processed"
    rc = main([str(raw1), str(raw2), "--output-dir", str(out_dir),
              "--no-tokenize", "--seed", "3"])
    check(rc == 0, "CLI exits 0 on a clean merge")
    check((out_dir / "train.docs.jsonl").exists(), "train.docs.jsonl written")
    check((out_dir / "val.docs.jsonl").exists(), "val.docs.jsonl written")
    check((out_dir / "test.docs.jsonl").exists(), "test.docs.jsonl written")
    check((out_dir / "labels.json").exists(), "labels.json written")

    label_data = json.loads((out_dir / "labels.json").read_text())
    check(label_data["labels"] == build_label_list(),
          "labels.json matches build_label_list()")

    all_out_ids = []
    for split in ("train", "val", "test"):
        for line in (out_dir / f"{split}.docs.jsonl").read_text().splitlines():
            all_out_ids.append(json.loads(line)["id"])
    check(len(all_out_ids) == 29,
          "29 unique docs survive (15 + 14 distinct, 1 genuine text dup "
          "dropped, the 0..13 id overlap between the two files is NOT "
          "treated as duplication)", len(all_out_ids))
    check(len(set(all_out_ids)) == len(all_out_ids),
          "no duplicate ids in the merged output")
    check(any(i.startswith("run1__") for i in all_out_ids)
          and any(i.startswith("run2__") for i in all_out_ids),
          "ids are prefixed by source file, not left ambiguous across runs")

    rc_missing = main([str(tmp / "does_not_exist.jsonl"),
                       "--output-dir", str(out_dir), "--no-tokenize"])
    check(rc_missing == 1, "CLI exits 1 on a missing input file")
finally:
    shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
print()
print("=" * 62)
print(f"PASSED {PASS}   FAILED {FAIL}")
for failure in FAILURES[:25]:
    print("  FAIL:", failure)
print("=" * 62)
sys.exit(1 if FAIL else 0)
