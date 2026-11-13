"""Tests for eval/labelling_audit.py: the audit must flag spans that start
or end mid-token and must pass clean ones. Uses the real xlm-roberta-large
tokenizer (cached locally, no model weights) and the real
prepare_splits.align_labels_for_window.

Run:  python eval/test_labelling_audit.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "scripts"))

from labelling_audit import TOKENIZER, audit_entity, minimal_cases, run, suffix_kind  # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond, name, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(f"{name}: {detail}" if detail is not None else name)


from transformers import AutoTokenizer  # noqa: E402
from prepare_splits import add_punctuation_boundary, align_labels_for_window, build_label_list  # noqa: E402

tok = AutoTokenizer.from_pretrained(TOKENIZER)
assert add_punctuation_boundary(tok)
label2id = {l: i for i, l in enumerate(build_label_list())}
id2label = {i: l for l, i in label2id.items()}


def flags(text, value, label, start=None):
    s = text.index(value) if start is None else start
    e = {"start": s, "end": s + len(value), "label": label}
    enc = tok(text, return_offsets_mapping=True, truncation=True, max_length=512)
    labels = align_labels_for_window(enc["offset_mapping"], [e], label2id)
    return audit_entity(text, e, [(enc["offset_mapping"], labels)], id2label)


# Clean spans: a token starts at the start, none straddles the end, B- first.
f = flags("Mən Bakıda yaşayıram.", "Bakıda", "CITY")
check(not f["no_token_at_start"] and not f["no_B"] and not f["end_mid_token"]
      and f["all_tokens_consistent"], "clean: suffixed city is aligned (D-9)", f)
f = flags("Fidan.", "Fidan", "GIVENNAME")
check(not f["end_mid_token"] and not f["no_B"], "clean: 'Fidan.' ends at a token boundary", f)

# Broken on purpose: a stem-only span inside one token ends mid-token.
f = flags("Mən Bakıda yaşayıram.", "Bakı", "CITY")
check(f["end_mid_token"], "flag: stem-only 'Bakı' of 'Bakıda' ends mid-token", f)

# Broken on purpose: a span starting inside a word has no token at its
# start, so align gives its first token I- (no B-).
f = flags("Mən Bakıda yaşayıram.", "akıda", "CITY")
check(f["no_token_at_start"] and f["no_B"], "flag: mid-word start = no token at start, no B-", f)

# Multi-token entity across whitespace: every token B/I of its own label.
f = flags("Tel: +994 50 123 45 67.", "+994 50 123 45 67", "TELEPHONENUM")
check(f["whitespace_inside"] and f["n_tokens"] > 1 and f["all_tokens_consistent"],
      "whitespace multi-token phone is consistent", f)

# suffix_kind: a suffix only counts when the stem is another gold value.
bare = {"CITY": {"Bakı"}, "GIVENNAME": {"Əsgər"}, "SURNAME": set(), "STREET": set()}
check(suffix_kind("Bakıda", "CITY", bare) == "case", "suffix: Bakıda = Bakı + da")
check(suffix_kind("Leyla", "GIVENNAME", bare) is None, "suffix: Leyla is not suffixed")
check(suffix_kind("Əsgər'in", "GIVENNAME", bare) == "apostrophe", "suffix: apostrophe form")

# run(): counts per label, and the flag counts reach the table.
recs = [{"id": "a", "text": "Mən Bakıda yaşayıram.",
         "entities": [{"start": 4, "end": 8, "label": "CITY"}]},       # stem-only, broken
        {"id": "b", "text": "Bakıda və Bakı.",
         "entities": [{"start": 0, "end": 6, "label": "CITY"},
                      {"start": 10, "end": 14, "label": "CITY"}]}]
res = run(recs, tok, label2id)
c = res["per_label"]["CITY"]
check(c["entities"] == 3 and c["end_mid_token"] == 1 and c["no_token_at_start"] == 0,
      "run: per-label counts", c)
check(res["slices"]["CITY|suffixed|case"]["entities"] == 1, "run: suffixed slice", res["slices"])

# Declared suffixes (P2-12): an entity the record declares in `_suffixes` is
# sliced by its surface, including a misspelt (noisy) suffix the guessing
# `suffixed` slice cannot see.
recs = [{"id": "n", "text": "Dünən Bakıdə idim, Bakıda yox.",
         "entities": [{"start": 6, "end": 12, "label": "CITY"},
                      {"start": 19, "end": 25, "label": "CITY"}],
         "_suffixes": [{"start": 6, "end": 12, "stem_end": 10, "case": "loc", "surface": "noisy"},
                       {"start": 19, "end": 25, "stem_end": 23, "case": "loc", "surface": "plain"}]}]
res = run(recs, tok, label2id)
s = res["slices"]
check(s.get("CITY|declared_suffix|noisy", {}).get("entities") == 1
      and s.get("CITY|declared_suffix|plain", {}).get("entities") == 1,
      "run: declared_suffix slice by surface", s)
check(s["CITY|declared_suffix|noisy"]["no_B"] == 0 and s["CITY|declared_suffix|noisy"]["end_mid_token"] == 0,
      "a noisy suffix (Bakıdə) still gets a clean B- and ends on a token boundary", s["CITY|declared_suffix|noisy"])

# Minimal hand-written cases all run and report a verdict.
mc = minimal_cases(tok, label2id)
check(len(mc) >= 20 and all("ok" in m for m in mc), "minimal cases run")


if __name__ == "__main__":
    print(f"{PASS} passed, {FAIL} failed")
    for f in FAILURES:
        print("  FAIL", f)
    sys.exit(1 if FAIL else 0)
