# Translation test run: 300 documents of runb-az-v4.1 train → EN / TR / RU

The request (19 Oct 2026): run the translation pipeline on ~300 documents
of v4.1's train split, report survival per language, the top rejection reasons,
time and API cost per 1,000 documents, an estimate for the full set, and check
that `golden_en`, `lang_tr` and `lang_ru` are ready for A7.

**Short answer.**
- Survival is 94.7% (EN), 94.3% (TR) and 93.3% (RU).
- One defect explains most rejections, and its fix (below) should lift survival to about 98 / 98 / 95%.
- Two defects in the Russian runner were found and fixed here. One of them was making every Russian call reason first, which took 13× longer and used about 3,900 hidden reasoning tokens per document.
- The full train split is about 724M prompt + 104M completion tokens, or about 11 h if the three languages run side by side at 8 requests each.
- A7's gold sets are usable. They still carry a few old-convention labels, listed at the end.

## Sample

`make_sample.py`, seed 20261019, drew the documents in the split's own source proportions. The split has 135,270 documents.

| Source | Sampled | PII-free |
|---|---|---|
| LLM | 110 | 8 |
| Old corpus | 140 | 15 |
| Targeted | 50 | 8 |

How the run was done:
- The harness ran unchanged: `scripts/translate/run.py --lang en|tr` and `scripts/translate/run_ru.py`.
- The model was `wahoo-1.5-preview` on `api.hal-x.ai`, with thinking off, at concurrency 8.
- `run_test.py` wraps the calls, asks the endpoint for its token usage, and writes `<out>.usage.json`.
- `analyse.py` builds the tables below.

Commands:

```
python reports/translation_test/make_sample.py <v4.1 train.docs.jsonl> sample300.jsonl
python reports/translation_test/run_test.py --lang en --input sample300.jsonl --out real_en.jsonl   # and tr, ru
python reports/translation_test/analyse.py sample300.jsonl <dir>
```

## Results

| | EN | TR | RU |
|---|---|---|---|
| **Survival (written / sent)** | **284/300 = 94.7%** | **283/300 = 94.3%** | **280/300 = 93.3%** |
| LLM | 99/110 | 99/110 | 100/110 |
| Old corpus | 136/140 | 134/140 | 132/140 |
| Targeted | 49/50 | 50/50 | 48/50 |
| Targeted look-alikes back verbatim | 38/45 | 40/47 | 33/41 |
| Look-alike values that became labelled | 0 | 0 | 0 |
| API calls (including retries) | 336 | 337 | 344 |
| Prompt / completion tokens | 319,483 / 64,146 | 392,410 / 78,844 | 893,136 / 87,372 |
| Reasoning tokens | 0 | 0 | 0 |
| Wall time | 72 s | 89 s | 83 s |
| **Per 1,000 docs: tokens in / out** | **1.06M / 214k** | **1.31M / 263k** | **2.98M / 291k** |
| **Per 1,000 docs: minutes at concurrency 8** | **4.0** | **5.0** | **4.6** |

Russian sends about 2.8× the prompt tokens per call of English: about 2,600 against 950. Its system prompt is much longer. If the endpoint caches prompts, most of that is a repeated prefix. Completion tokens are similar across the three languages.

## Top rejection reasons

| Reason | EN | TR | RU |
|---|---|---|---|
| Azerbaijani words left in the output | 12 | 14 | 17 |
| … of which from a hard-negative phrase (problem B) | 10 | 10 | 6 (+2 other reasons) |
| `length_ratio` outside the band | 2 | 3 | – |
| Invented PII (`URL:https://docs.internal.dev/…`, the same document in all three) | 1 | – | 1 |
| Invented or mangled slots | 1 | – | 1 (`mixed_script`) |
| Stale Azerbaijani value | – | – | 1 |
| Rejects marked "retry" (another `--resume` pass may save them) | – | – | 8 of 20 |

### Problem B: hard-negative phrases are put back in Azerbaijani

The harness protects each `_spec.hard_negatives` string. It hides the string behind a placeholder and puts the string back verbatim after translation. In the LLM batches these strings are whole phrases, not bare values, so the restored text still contains Azerbaijani words and the leftover-Azerbaijani check rejects the document. For example:
- `vəsiqə nömrəsi AB-5115`
- `kart nömrəsi 5555 …`

This one cause accounts for 10 of 16 English rejects, 10 of 17 Turkish and 6–8 of 20 Russian. Every one is an LLM document.

The reverse also happens. Targeted documents declare their look-alikes in `_decoys` (exact spans) rather than in `_spec`, so those look-alikes are not protected. They come back verbatim only 81–85% of the time; the model sometimes reformats or translates them.

**Proposed fix (separate PR):**
- When a document has `_decoys`, protect exactly those spans.
- Otherwise, cut each hard-negative phrase down to its value-shaped part before protecting it.

Expected survival after the fix: about 98.0% (EN), 97.7% (TR), 95.3% (RU).

**Measured after the fix (D-54b, `p2/translation-problem-b`, same 300 documents):** 98.0% (EN), 97.0% (TR), 96.3% (RU). Every protected look-alike came back verbatim (223/223, 218/218, 214/214).

## Two Russian-runner defects, fixed in this branch

1. **LiteLLM 1.106 drops `extra_body`, so Russian ran with thinking on.**
   - What happened: `dspy` pulled in LiteLLM 1.106.0. LiteLLM silently drops `extra_body` for this provider, so `chat_template_kwargs: {enable_thinking: False}` never reached the model.
   - Effect per document: about 3,900 hidden reasoning tokens, and the first text arrived after 27 s instead of 2 s. LiteLLM's own usage report does not show the reasoning tokens.
   - Effect on the run: about 2 documents per minute, against about 200 for English.
   - Fix: `run_ru.translate()` now calls the OpenAI SDK, as `translate/client.py` (EN/TR) already does, with the same messages and parameters and `max_retries=2`.
   - Result: 0 reasoning tokens and 3.4 s for a 2,200-character document.
   - Anyone running Russian translation with LiteLLM ≥ 1.106 installed was paying for reasoning.
2. **The Russian postcode check rejected correct values.**
   - What happened: since D-42c, piigen mints 25% of Azerbaijani postcodes without `AZ` (`1061`). The Russian runner's bug detector (`_SHAPE_RULES`) accepted only `AZ####`.
   - Effect: 5 of 300 Russian documents were rejected for a correct postcode.
   - Fix: the rule now accepts `AZ####` or `####`, the same as piigen's own validator.
   - English and Turkish have no such rule.

Tests: `test_run_ru.py` 206/0 (3 new label-shape cases), `test_ru_pack.py` 36/0, `test_repair_repeat_mentions_ru.py` 40/0.

## Full train split (135,270 documents)

| | EN | TR | RU | All |
|---|---|---|---|---|
| Documents written at today's survival | ~128,100 | ~127,600 | ~126,300 | ~382,000 |
| … with problem B fixed | ~132,600 | ~132,100 | ~128,900 | ~393,600 |
| Prompt tokens | 144M | 177M | 403M | **724M** |
| Completion tokens | 28.9M | 35.6M | 39.4M | **104M** |
| Hours at concurrency 8 | 9.0 | 11.3 | 10.4 | 30.7 one after another; **~11 h side by side** |

**Cost.** The endpoint reports tokens but no price. At $P_in and $P_out per 1M tokens, the full run costs 724 × P_in + 104 × P_out. The team has the rate.

**Time.** Concurrency above 8 was not tried. If the endpoint's rate limit allows 16 per language, the time should roughly halve; a 1,000-document test at 16 would confirm that within a few minutes.

## A7 readiness: `golden_en`, `lang_tr`, `lang_ru`

The sets and their baseline are in place:
- `golden_en` has 217 documents.
- `lang_tr` and `lang_ru` each have 1,000 documents, drawn with seed 13 from `merged_relabeled_swept_dated/test`.
- The checkpoint-1 baseline is `reports/scoreboard/baseline_ckpt1_langs.json`.
- The base model is `your-hf-org/masking-multilingual@2519392a`. `release_check.sh` defaults to `your-hf-org/masking-multilingual`, which no longer resolves, so pass `BASE_MODEL` explicitly.
- The v4 release check marks A7 "not applied (Azerbaijani-only model, D-23a)", so the multilingual build is the first model to be scored on it.

The gold still has labels that the current conventions changed (`a7_readiness.py`):

| Set | Labels | DATE with a weekday inside | Other DATE shapes | Timestamp TIMEs the R2 rule unlabels |
|---|---|---|---|---|
| `golden_en` | 1,036 | 2 | 11 ordinal (`21st`), 7 starting with `the` | 9 |
| `lang_tr` | 4,028 | 15 | – | 11 (+1 DATE) |
| `lang_ru` | 3,997 | 17 | **10 with `года`/`г.` inside** | 3 (+1 DATE) |

Effects on A7:
- **`lang_ru`.** The new training data puts the year word outside the DATE. The model will therefore lose about 10 boundary matches on the gold: about 1.3 points of DATE recall, or about 0.25 points overall. That is small, but it counts against the 1-point budget for reasons that are not regressions.
- **`golden_en`.** The 9 timestamp TIMEs are the largest item. If the model learns R2 and stops labelling them, 9 of 1,036 labels go, about 0.9 points overall, close to the whole budget. Relabel the 9 before scoring A7, or exclude them as the policy rules do for Azerbaijani.
- **Weekday inside DATE** (all three sets). This waits on the open decision. Whichever way it goes, gold and training data should agree.

**Recommendation:**
- Before the multilingual build is scored on A7, apply R2 and the year-word rule to the three gold sets, or score A7 with the 15 Oct policy rules.
- Fix `BASE_MODEL`'s default.

## Files

| File | What it does |
|---|---|
| `make_sample.py` | Draws the sample |
| `run_test.py` | Runs the harness and records usage |
| `analyse.py` | Builds the tables |
| `a7_readiness.py` | Runs the gold-set checks and writes `a7_readiness.json` |

The outputs live outside the repository, in `D:/pii_rebuild/tt/`: the translated files, the repair queues and the usage files.
