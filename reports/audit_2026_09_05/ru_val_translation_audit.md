# Russian Translation Audit — `val` split

**Date:** 2026-09-05 · **Records:** 10,339 written of 10,540 attempted · **Source:** `data/processed/az/val.docs.jsonl`
**Method:** every rejection in the repair queue read individually rather than counted, plus an independent sweep of all 10,339 *accepted* documents using the project's own modules (`piigen.sentinel`, `ru_calibration`, `piigen.locales.ru`, `anchors_ru`). Every figure below is measured from the output file (`sha256 e391750221a9497a…`), not estimated.

---

## Verdict

**READY TO PROCEED TO THE `test` SPLIT.**

Every hard gate passes at 100%, with no margin needed: 34,557 spans with **zero offset errors**, **zero** of 2,438 negatives wrongly labelled, zero sentinel leaks, zero duplicate ids, zero non-NFC text, and all 27 labels preserved at exactly 100% of source count. Unresolved loss is **1.91%**, inside the 3% budget.

Two defect classes were found in accepted output during this audit and are now caught. Neither blocks `test`, but **both should be closed before `train`**, because at `train`'s 84,339 documents the same rates mean roughly 615 defective documents rather than 75:

1. **75 documents (0.73%) carrying a single untranslated Azerbaijani word**, most often an `E-poçt:` label on a signature block. These passed because `az_residue` required *two* distinct Azerbaijani words before flagging.
2. **3 documents (0.03%) of Russian written in Latin script** — "Manifest Dostavki i Detali Otpravki" where the corpus wants "Манифест доставки и детали отправки". Correct content, wrong alphabet, and invisible to every check: the length is right, there is no Azerbaijani in it, and SIMURG permits Latin because emails and log tags need it.

Both checks are now in the pipeline and both classes are queued for retranslation, not discarded.

---

## Corpus at a glance

| | |
|---|---|
| Documents written / attempted | 10,339 / 10,540 (**98.09%**) |
| Entities / labels | 34,557 · **27 of 27** |
| Negatives (zero-entity documents) | 2,438 |
| Entities per document | mean 3.34 · median 2 · max 87 |
| Document length (chars) | min 28 · p25 287 · median 655 · p90 2,522 · p99 4,399 · max 7,580 |
| Length bands | medium 3,426 · short 2,641 · long 2,245 · very_short 1,056 · very_long 846 · extreme 125 |
| Registers / document types | 14 · 42 |
| Cyrillic fraction | median 0.932 · p5 0.605 · p1 0.354 |
| AZ→RU length ratio (slotted) | median **1.028** · p1 0.885 · p99 1.192 |

---

## Hard gates

| Gate | Threshold | Measured | |
|---|---|---|---|
| Span integrity | ≥ 99.9% | **100.000%** (0 of 34,557 bad) | PASS |
| Negatives clean | ≥ 90% | **100.000%** (0 of 2,438 labelled) | PASS |
| Unresolved loss | ≤ 3% | **1.91%** (201 of 10,540) | PASS |
| Label coverage | — | **100.00%** on all 27 labels | PASS |

Span integrity being exactly 100% is the design working as intended rather than luck: values are cut out before translation and spliced back at known offsets, so a span can only be wrong if `sentinel.splice_with_offsets` has a bug. It is asserted on every document anyway.

---

## Integrity sweep of accepted output

| Check | Result |
|---|---|
| Sentinel leaked into final text | 0 |
| Non-NFC normalised text | 0 |
| Duplicate document ids | 0 |
| Near-empty documents | 0 |
| Azerbaijani residue (current validator) | 0 |
| Untranslated single AZ word (**old** validator missed) | 75 → now caught |
| Romanised Russian (**no** validator existed) | 3 → now caught |

---

## Unresolved documents, by cause

201 documents, 1.91%. 87 are marked `retry` and are re-attempted by the next `--resume`; 114 are `needs_repair`.

| Cause | n | Recoverable? |
|---|---|---|
| `az_residue` | 133 | Yes — the rewritten prompt targets exactly this |
| slot set changed | 21 | Partly — the extreme/high-slot documents need splitting |
| `simurg` corrupt stream | 17 | Yes, on retry |
| slot duplicated | 9 | Yes, on retry |
| decoy slots mangled (negatives) | 9 | Partly |
| `expanded` | 8 | Yes |
| `truncated` | 4 | Needs document splitting |

The dominant remaining class is Azerbaijani residue, which is what the prompt rewrite (`ab710a3`) addresses and which had not yet been re-attempted at the time of this audit.

---

## Findings that changed the pipeline

### 1. Defects were passing every check

Three documents with `simurg = corrupt` had been written into the corpus. The guard aborts the stream on a repetition loop; nothing downstream rejected the fragment it left behind. The worst was a 13,226-character log truncated to 2,045 characters, cut mid-token — with all seven spans intact and byte-exact, fluent Russian, and no Azerbaijani, so span integrity, the slot check and the residue check all passed on it while 85% of the document was missing.

Two more had been padded with invented text: a 288-character complaint about a card charge came back as 1,360 characters of advice, including a `«Следующий шаг:»` section that exists nowhere in the source.

`completeness()` (a length-ratio band on the *slotted* forms, so re-minted values cannot move it) and treating `simurg = corrupt` as a failed attempt now catch both. During the completing run these fired **25** and **11** times respectively.

### 2. The prompt and the validator contradicted each other

The corpus deliberately injects OCR damage and the prompt orders it preserved byte-for-byte; `az_residue` then rejected the document for containing it. 8 of 76 residue rejects were only ever this. The exemption is now narrow: a damaged token is excused **only when it appears verbatim in the source**, so damage the model invented (`Şirkəti` → `Шirkəti`) still counts.

### 3. Character-mutilation noise drives failure; layout noise does not

Rejection lift per source `_noise` feature against a 2.15% baseline:

| Feature | Lift | Rejects / attempts |
|---|---|---|
| `invisible` | 2.27× | 6 / 123 |
| `case_glitch` | 2.25× | 6 / 124 |
| drop some diacritics | 1.87× | 16 / 397 |
| `ocr` | 1.51× | 4 / 123 |
| `typos` | 1.45× | 4 / 128 |
| table-like layout | 0.58× | 6 / 478 |
| email signature block | 0.00× | 0 / 198 |

### 4. Slot failure is U-shaped

Residue scales with length as expected; slot failure does not. It is worst at `extreme` (2.83%) but rises again at `very_short` (0.74%) against a `medium` trough of 0.15%. Four documents of roughly 110 characters carrying a single marker failed — text with nothing difficult in it. Two different mechanisms share one label.

### 5. The model was answering the documents

16 documents came back as the model explaining itself, in Azerbaijani: *"mən bir tərcümə modeliyəm … zəhmət olmasa tərcümə olunmalı olan mətni göndərin"* — "I am a translation model … please send the text to be translated". The document **was** the text. Corpus documents frequently read like requests, and the `⟦N⟧` markers push a short one further toward looking like a meta-conversation. The prompt now opens with the rule that the input is always the document.

---

## Comparison with `origin/translate/en`

Read side by side with `scripts/translate/prompt.py` and `validate.py` on the English branch.

**Adopted from theirs:** the anti-invention paragraph (much stronger than our "invent nothing" — it names invented headers, signature blocks and "a plausible-looking address or person"); transliterating Azerbaijani letters *inside* an otherwise-literal token (`merkezi_dispetcer@…`), for which **we had no rule at all**; "a word that merely looks technical is translated normally"; concrete register examples; "text already in the target stays as it is". Our prompt went from 5,572 characters of prose sections to 4,018 characters in 14 flat rules, with more coverage.

**Kept, which theirs lacks:** input-is-the-document, translate-to-the-last-line, diacritic-stripped Azerbaijani, and the damaged-token exception — each an audited failure class here.

**Rejected:** their `azletter` rule resolves to *"your output must not contain any Latin letters"* for Russian, which would forbid the emails, URLs, log tags and code paths their own copy-unchanged rule protects.

**Still to take from theirs:** `find_leaked_pii()`, an independent sweep for PII the model *invented* — an untagged invented name teaches a false negative and nothing of ours looks for it. We independently arrived at the same length-ratio band and the same `simurg = corrupt` rule, which is useful corroboration for both tracks.

**Not to take:** their rejection of zero-width characters. The corpus injects them deliberately (118 val source documents), so a faithful translation carries them through — the same prompt/validator conflict described in finding 2.

---

## Before `train`

1. Requeue and re-run the 74 documents this audit quarantined, plus the 87 already marked `retry`, against the rewritten prompt.
2. Implement document splitting for extreme/high-slot documents. `012886` (143 slots, 10,947 characters) has failed every run; it and its three siblings are the dominant hard-failure class and no prompt rule reaches them.
3. Port `find_leaked_pii()` from `origin/translate/en`.
4. Deliver `anchors_ru.py` to the shared harness — `ANCHOR_MODULES` in their `validate.py` still has `"ru": anchors_ru` commented out.

## Known upstream, not fixable here

`Hacımürsələvan` is a surname the Azerbaijani corpus never labelled, so it is never slotted, never protected, and surfaces as residue in translation. The blind spot is far larger than the rejects show — roughly 6,500 documents once names, cities and streets are swept. It belongs upstream, in the Azerbaijani corpus, not in any translation track.
