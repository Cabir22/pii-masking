# m1 audit: public results verified and explained (24 Oct 2026)

**Candidate:** `your-hf-org/masking-multi-m1-seed42@d7493a16` (AZ v4.2 + EN/TR/RU translation, D-67), compared with v4.2 (`@223e54e8`) and checkpoint 1 (`your-hf-org/masking-multilingual@2519392a` = `your-hf-org/masking-multilingual@3a0a6e5`, D-52a).
**Method:**
- the saved scoreboard reports, re-read with `eval/release_check.py`'s own rule functions;
- per-document predictions re-run with the scoreboard's own engine (`diag_run.py`) on the English set, the 461 benchmark documents with a MAC or MAC-like string, and C13's family;
- minimal and ablation tests for MAC;
- a spread sample of the Turkish and Russian sets.

Nothing was trained, no gold or threshold was changed, and the original reports are untouched. Markers: **[confirmed]** = measured here; **[hypothesis]**; **[open]**.

**Provisional verdict: public checks failed; the candidate needs fixes.**
- **B3 (MAC addresses) is a genuine regression.**
- **A7-English fails as the rule is written**, but almost entirely because the English gold predates the current labelling policy. That is an evaluation-set problem with a documented fix.
- Private A1–A6, A10 and E3 are pending.

## 1. Verified scorecard (track M decides, D-64a)

Every number below **reproduces** from the saved reports. The English, name-list and MAC figures also reproduce exactly from re-run per-document predictions (`analysis.md` §1). Exact-span micro scores: start, end and label must all match.

| Rule | Metric, population | Reported | Reproduced | Baseline | Status |
|---|---|---|---|---|---|
| B1 | exact micro F1, benchmark (AZ, first 5,000 docs), policy items out | 96.4 vs 72.1 | 96.4 (TP 10,169 / FP 412 / FN 349) | ckpt1 72.1 (+2 needed) | **pass** |
| B2 | per-label recall, benchmark, vs ckpt1 (−1 pt) | pass | no label drops | ckpt1 | **pass** |
| B3 | per-label exact F1, benchmark, vs v4.2 (−5 pt, ≥30 gold) | MAC 95.6 → 74.1 | MAC 95.6 → 74.1 (R: 95.2 → 73.3) | v4.2 | **fail** [confirmed genuine, §3] |
| C1–C3 | contrast probes | pass | pass (5 / 5 / 4 conditions) | ckpt1 | **pass** |
| C4 | look-alike trigger, 11 families | 0% | 0 of 11 families, 0.0% overall, **on R and on M** | <15% each, <10% | **pass** |
| C13 | family >10 pt **and** >3 docs worse than ckpt1 | "fail" | names_list_lines **2 docs** worse (same 2 as v4.2) | ckpt1 | **watched, not blocking** (the earlier "fail" was my quick check, which lacked per-document data) |
| A7 | exact micro F1 per language, translated set, vs ckpt1 (−1 pt) | EN 98.6→85.7, TR 89.4→93.8, RU 89.2→95.1 | same | ckpt1 | **fail (EN)** as written; see §2 |
| A1–A6, A10, E3 | private sets | – | **not scored** | | pending |

**Population notes:**
- **96.4 vs 95.4** are the **same 5,000 Azerbaijani benchmark documents** on track M: 96.4 with the policy items out (B1's definition), 95.4 with them in.
- Against v4.2 on the same basis, m1 is **0.4 lower** (96.4 vs 96.8 out; 95.4 vs 95.8 in; on R 95.8 vs 96.4).
- `lang_tr` and `lang_ru` are a 1,000-document sample (seed 13) of the old corpus's translated test split. `golden_en` has 217 documents.
- [confirmed] **Not equivalent:** v4.2's public reports were made on 21 Oct, *before* the `validity-2` decoder. So v4.2's M ≠ m1's M for TIME, DATE, CVV and the D-2 dummies. MAC and track R are unaffected, and B3 fails on R too. Re-scoring v4.2 with `validity-2` would make the M comparison exact.

## 2. English (A7): mostly a gold/policy mismatch, plus a contamination caveat

- [confirmed] m1 on `golden_en`: **recall 98.9%** (1,016 of 1,027 gold values), precision 75.5% (329 extra predictions). The counts are **predicted spans (occurrences)**, not unique values.
- [confirmed] Every one of the 329 extra predictions and the 6 misses was reviewed (`english_review.jsonl`, `english_adjudication.jsonl`):
  - **309 are real PII the gold leaves unlabelled**:
    - **192 standalone dates.** The gold labels 44 dates and leaves 218 standalone ones unlabelled, such as `Application Date: 12 March 2025` and dates in tables. D-17 says every standalone date is DATE.
    - **81 given names and 20 surnames:** chat and transcript speakers (D-72h), signatures, `Driver: Hans Müller`.
    - Cities, streets, ages, times and tokens in addresses and records.
  - **13 are m1 errors:** 8 dates split into pieces or a bare year (part of the date stays visible); 2 weekdays inside DATE (D-54d says outside); 2 split streets; an `*` from a masked card.
  - **7 are ambiguous:** a city in a company's address, organisation mailboxes, `Sahil` in a police department's name, `Gulli` as given name or surname, a leading-zero IP.
- [confirmed] **1 gold error:** an AGE label placed on `54` inside the time stamp `10:54` instead of on `Age: 54`. That's a wrong-occurrence placement.
- **Two views:**
  - **original gold 85.7** (unchanged, A7's number);
  - **current-policy reassessment 98.9–99.1** (ambiguous counted against or for m1).
  - The reassessment can only add labels where m1 predicted something, so its recall is an upper bound. Checkpoint 1's 98.6 was earned on the same old labelling it was trained on, and it wasn't re-assessed here.
- [confirmed] **Contamination:** 79 of the 217 `golden_en` documents are translations of source documents whose English translation is in m1's training data (50–85% shared 8-grams; `golden_en_overlap.json`). This **flatters** m1, so it doesn't explain the drop. But `golden_en` isn't an independent test for m1.
- **Conclusion:**
  - The drop is **~94% annotation-policy mismatch** (309 of 329 extra spans), **~4% genuine m1 errors** (13 spans, mostly date fragments) and **~2% ambiguous**.
  - It isn't a technical bug: the scores reproduce exactly.

## 3. MAC addresses (B3): a genuine, context-dependent regression

- [confirmed] Benchmark, 374 gold MACs (same population for both models):

  | | Values |
  |---|---|
  | v4.2 correct, m1 correct | 246 |
  | **v4.2 correct, m1 wrong** | **112** |
  | v4.2 wrong, m1 correct | 7 |
  | both wrong | 9 |

  - m1: **89 missed completely, 32 partly masked** (fragments like `0A:BC:4F:` stay visible), **0 under another label**.
  - The report's 56 "MAC false positives" are the fragments of those partial masks. m1 masks **no** non-MAC text as MAC in this subset.
  - The report's 121 misses vs 16 for v4.2 are the same definition and population as these counts (v4.2: 9 missed, 6 partial, 1 boundary).
- [confirmed] **Where it fails** (`mac.md`):
  - All failures are colon-separated, mostly upper-case, inside prose with spaces around them.
  - Structured documents (CSV, JSON, pipe tables, logs): **0 of 56 fail.**
  - Prose categories: 25–56% fail; the benchmark's `hard_negative` category 22 of 39.
  - MACs that start with a digit fail 44%, those that start with a letter 14%.
  - With a version string (`17.1.9`) before the MAC: 52% fail, vs 27% without.
- [confirmed] **The value isn't the cause:** every failing value is masked exactly in its sentence alone, in 4 frames, upper- and lower-case, colons and dashes (`mac_repro.md`, 36 of 36).
- [confirmed] **The preceding text is the cause** (`mac_ablation.md`, 40 documents where v4.2 is exact and m1 fails):

  | Text kept around the MAC | Exact |
  |---|---|
  | its own sentence only | **40 of 40** |
  | with 100 characters before | 33 |
  | with 300 characters before | **13** |
  | all text after, nothing before | 35 |
  | whole document, version strings removed | 10 |
  | whole document, located look-alikes removed | 5 |

- **Hypotheses for why m1 learned this and v4.2 didn't:**

  | Hypothesis | For | Against | Smallest check | Confidence |
  |---|---|---|---|---|
  | Label noise in the translations (unlabelled MACs) | – | EN training labels MACs as consistently as AZ (0 unlabelled real-looking MACs; `analysis` run) | – | **rejected** |
  | m1 learned stronger suppression of code-like strings after code-like context (version numbers, look-alikes); the same shift that gives C4 0% on R | C4 R 0% (v4.2 failed C4 on R); failures concentrate in hard-negative prose and after version strings; removing those helps | removing them fixes only 10–15 of 40 | count, in m1's train vs v4.2's, MACs that follow a version string or look-alike within 300 characters, by language | moderate |
  | The translated data adds many prose contexts with MACs *after* long non-PII text in other languages, shifting the AZ decision boundary | the same AZ data trained alone (v4.2) passes | not measured | the same count as above | low–moderate |
  | Run-to-run variance (one seed) | v4.1 → v4.2 also moved a single label (IPv6) sharply | the pattern is systematic, not random | a second seed of m1 | low |

## 4. C13 (name-list controls): an old weakness, not new in m1

- [confirmed] 0% → 50% is **2 of 4 control spans**, and both are masked by **v4.2 too**: `Kəhrəba Çay Dəsti` and `Gümüş Qələm Mükafatı`, a product and an award on their own line inside a "Surname Given Patronymic" list, read as a name triple. `c13.md` has the details.
- Checkpoint 1's 0% comes with recall of only 25–29% on these lists (m1 and v4.2: 100%). That's 2 documents worse, at most 3 allowed, so **watched, not blocking**.
- **Distinct from the English and TR/RU name "false positives"**, which are real names (§2, §5). C13 is a genuine positional false positive on capitalised word triples in lists.

## 5. Cross-language and label audit (`label_table.md`)

- [confirmed] **Azerbaijani (benchmark, vs v4.2):** stable. The only large change is **MAC −21.5 F1**. Gains: CVV +3.0, TIME +2.4, DATE +1.8, SURNAME +1.4. Small drops: URL −2.0, AGE −1.2, EMAIL −1.0, ID card −0.7.
  - m1 misses 82 more values in total, and MAC alone accounts for 105, so **all other labels together improved**.
  - **IPv6 stays weak in both (F1 ~75)**, the known D-65a issue.
- [confirmed] **Turkish and Russian vs checkpoint 1:**
  - The gains are **almost entirely DATE** (TR 29 → 91, RU 22 → 89 F1): checkpoint 1 barely labels dates the way the current gold does. PRIVATE_KEY also gains (+30 / +15, but with few values).
  - **GIVENNAME drops** (TR −18, RU −7 F1). In a spread third of each set, 90 of 91 (TR) and 40 of 41 (RU) of m1's non-exact name predictions are **real people the gold leaves unlabelled** (chat speakers, signatures, `Заявитель: Фазиль Мирзеев`). Only 2 are type errors.
  - DATE recall is the weakest real spot: 104 TR and 126 RU dates missed.
  - Small label drops worth watching: TR MAC (22 gold, 9 FP), TR CVV −4.6, RU CITY −4.8, RU TIME −6.2.
- **Data provenance:** the TR/RU test documents are clean by ID. None of their Azerbaijani sources is in v4.2's train or validation split; about 75% are in v4.2's test split, the rest aren't in v4.2.
- **Thin support (under 30 gold values; no reliable conclusion):** most EN labels except names, dates, e-mails, phones, cities, streets, building numbers, API keys, ID cards and ZIP codes; TR MAC, ICCID, VÖEN, IPv6, private keys; RU MAC and private keys.
- **Not available:** v4.2 on the translated sets (it was never scored there; an AZ-only model, as a reference only).

## 6. Prioritised actions (smallest justified first)

1. **MAC (blocks B3).**
   - Add to the m2 extra batch real MACs **in long Azerbaijani prose, after version strings and look-alikes**, digit-first and letter-first, upper-case, with matched look-alikes kept at most 1 : 2. That's a new row next to X-IP6 and X-FMT.
   - **Validate** on `bench_mac` (B3), `mac_repro.md` and the ablation set. Check that C4 still holds on R.
   - **Before that**, run the count in §3's hypothesis table to choose between the two context hypotheses.
2. **A7 evaluation sets (an evaluation fix, not a model fix).** These need a **written decision** (rules and thresholds unchanged):
   - Relabel `golden_en`, `lang_tr` and `lang_ru` to the current policy, as D-54c did for timestamps: standalone dates (D-17), chat speakers and other names (D-72h). Do it deterministically, with a human review of every changed span, keeping the old gold beside it. Then re-score **both** checkpoint 1 and m1.
   - Replace `golden_en` with an independent English set (D-58), because 79 of its 217 documents share sources with m1's training.
3. **m1's genuine English errors** (13 spans): date fragments and weekday inside DATE. Add EN/TR/RU date frames with weekdays and long month-name dates to the batch (D-54d).
4. **C13 (watched):** add award, product and department names on their own lines inside name lists as unlabelled look-alikes (beside D-66f's X-PLACE).
5. **Comparability:** re-score v4.2's public sets with `validity-2` (about 30 minutes on a GPU), so every M comparison uses one decoder.
6. **No decoding change is recommended:** none of the confirmed issues is a decoding effect. R and M agree on MAC, A7 and C13.

**Diagnostic examples** (`mac_repro.py`, `mac_ablation.py`, `names_trru.py`, English review) are **outside** the frozen sets and must not be added to them. Every re-run on the public sets after a fix counts as tuning against public checks; passing them alone doesn't show generalisation.

## 7. Private evaluation: what it must still establish

It must still check:
- **A1–A5 and A6 on shadow-dev**, especially MAC, IPv6 and card recall (v4.2 failed A6 on M, D-68);
- **E3 on real text**, especially GIVENNAME precision;
- **A10 vs v3**;
- **A7 on any independent EN/TR/RU set.**

**No readiness claim** until those and B3 pass (D-71).

## 8. Update 25 Oct: the private check is in (`reports/scoreboard/release_check/m1_seed42/`)

`release_check.sh` on track M, run 24 Oct 00:50 UTC. **13 of 17 blocking rules pass; fails A6, A7, A10, B3.** Under `m1_plan.md`, A7, A10 and B3 are report-only for m1 and blocking from m2, so on the Azerbaijani rules **13 of 14, failing A6 only**.

| Rule | m1 | Note |
|---|---|---|
| A1 | 93.8 (= v4.2 93.8) | pass |
| A5 | 6.9% (v4.2 9.3%) | pass, better |
| **A6** | **AZ_ID_CARD_NUMBER recall 98.7 → 95.8** vs ckpt1 | **fail** (v4.2's IPv6 and card failures are gone; this one is new) |
| E3 | 90.4% found, precision 92.0% | pass |
| **A10** (vs v3) | shadow-dev: MAC 97.0 → 91.5, STREET 94.6 → 89.8, GIVENNAME 96.9 → 94.0, BUILDINGNUM 92.5 → 90.2, ID card 98.1 → 95.8, ACCESS_TOKEN 96.7 → 95.4; benchmark: MAC, BUILDINGNUM, ID card, ZIP | fail (report for m1, **blocking for m2**). **[open]** whether v4.2 already had these drops against v3 (inherited) or m1 caused them: needs v4.2's A10 numbers |
| A7 independent sets | EN real text 32.7 → **78.3**, TR real text 19.7 → **60.9** vs ckpt1 | m1 far ahead on independent text, supporting §2: the translated-set failure is the old gold |

**Small discrepancy:** the summary gives B1 "v4.2 97.0 → m1 96.4 (−0.6)". 97.0 is v4.2 on track R; on track M both models give 96.8 vs 96.4 (−0.4). Both are within the 1-point limit.

**Updated verdict: public and private checks failed; the candidate needs fixes.** For m2: A6 (ID cards), A10 (the six labels), B3 (MAC); A7 after the D-74 relabel.

## Files

| File | What |
|---|---|
| `scorecard.md`, `label_table.md` | verified scores; language × label |
| `analysis.md` | reproduction from per-document predictions |
| `english.md`, `english_review.jsonl`, `english_adjudication.md/.jsonl` | every English mismatch and its verdict |
| `golden_en_overlap.json` | English contamination check |
| `mac.md`, `mac_cases.jsonl`, `mac_repro.md`, `mac_ablation.md` | MAC case table, minimal tests, ablation |
| `c13.md` | C13 control spans |
| `names_trru.jsonl` | Turkish/Russian name review sample |
| `preds/` | per-document predictions (R and M) |
| `diag_run.py`, `analyze.py`, `scorecard.py`, `english_adjudication.py`, `mac_repro.py`, `mac_ablation.py`, `mac_context.py`, `names_trru.py` | scripts that reproduce all of this |
