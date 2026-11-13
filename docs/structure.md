# Repository structure

Four languages, one pipeline. Azerbaijani is generated; English, Turkish and
Russian are **translations of the Azerbaijani splits** with the PII spliced
back in, so a document and its three translations always carry the same facts
and always land in the same split.

## The pipeline, end to end

```
  piigen/            1. generate Azerbaijani documents with tagged PII
       |
  prepare_splits.py  2. dedup, stratified split, tokenize -> data/processed/az/
       |
  translate/         3. translate each split into en / tr / ru,
       |                splicing freshly minted values back into the output
       |
  prepare_splits.py  4. --tokenize-only, per language (translation changes
       |                lengths, so AZ's token windows do not transfer)
       |
  merge_languages.py 5. shuffled union -> data/processed/merged/
       |
  model/train.py     6. train
```

Step 3 happens **after** the split, not before. That is the whole reason a
document can never straddle train and test: its translations inherit its
split by construction. Verified, not assumed — 105,419 source documents, none
appearing in more than one split in any language.

## `scripts/piigen/` — the Azerbaijani generator

The source of truth. Everything else consumes what this produces.

| path | what it is |
|---|---|
| `locales/{az,en,tr,ru}.py` | per-language months, weekdays, date and number formats |
| `anchors/az.py` | Azerbaijani licensing words for the `anchor_required` tier |
| `anchors/ru.py` | the Russian vocabulary for the same tier |
| `anchors/__init__.py` | re-exports `az` unprefixed — bare `from piigen.anchors import …` means Azerbaijani, which is what every generator-side caller wants |
| `validate.py`, `resolver.py`, `values.py`, `noise.py` | label rules, repeat resolution, value pools, noise injection |

Five labels (`AGE`, `BUILDINGNUM`, `CARD_SECURITY_CODE`, `DATE`, `TIME`) carry
no standalone signal — a bare `34` is only an age because something nearby
says so — and are valid only when a licensing word sits within 80 characters.

## `scripts/translate/` — the translation harness

| path | what it is |
|---|---|
| `run.py` | the runner for **en / tr** |
| `run_ru.py` | the runner for **ru** (see below) |
| `lang/<code>/anchors.py` | that language's anchor adapter |
| `lang/<code>/render.py` | how a minted Azerbaijani value is spelled in that language |
| `lang/__init__.py` | the **one** registry: `ANCHORS`, `TRANSLITS`, `RENDERERS` |
| `validate.py` | round-trip validators shared by every language |
| `audit_corpus.py` | corpus-wide auditor; `--prune` removes MUST-BE-ZERO failures |
| `sentinel.py` | entity spans ⇄ `⟦N⟧` placeholders |
| `client.py`, `guard.py` | Wahoo transport, SIMURG streaming guard |
| `outputlock.py` | one run per output file (see below) |
| `repair_*.py`, `restore_*.py`, `recover_*.py` | targeted repair passes |
| `test_*.py` | harness tests, no API needed |

### Adding a language

Create `lang/<code>/anchors.py` and `lang/<code>/render.py`, add one line to
`PACKS` in `lang/__init__.py`. Nothing in the harness, the validators or the
auditor changes.

The single registry is deliberate. Three modules used to keep their own
hand-written `ANCHOR_MODULES = {...}` dicts, and each listed a different
subset. Merging the language branches in September 2026 found Turkish missing
from two of them — which is not a runtime error, it just silently skips
anchor validation for that language.

### Why Russian has its own runner

`run_ru.py` is not a copy of `run.py`. It carries validators that only mean
something for a Cyrillic target — `mixed_script` (a word half Latin and half
Cyrillic, like `договорa`, which renders identically to the real word but
tokenizes as garbage), `romanised_russian`, and an `az_residue` tuned for
Cyrillic — plus a retry loop that feeds the model a correction note and a
soft/hard failure distinction. `run.py` rejects `--lang ru` and says so
rather than quietly producing weaker output.

`outputlock.py` is shared by both. `--resume` reads the output once to decide
what is already done and then appends, so two runs against one output both
translate the whole remainder: three concurrent runs put 16,697 duplicate
records into the Russian train split before the lock existed.

## `data/`

```
data/
  processed/
    az/  en/  tr/  ru/     {train,val,test}.docs.jsonl   char-span records
                           {train,val,test}.jsonl        tokenized windows
    merged/                the four-language union model/train.py reads
    labels.json
  calibration/tr/          one-off audit artifacts, kept on purpose
  golden/                  hand-checked reference corpora
```

`data/processed/<lang>/` holds **only** the corpus splits. `merged/` is
gitignored: it is a deterministic function of the committed per-language
splits plus a fixed seed, so `merge_languages.py --langs az en tr ru`
rebuilds it byte-for-byte rather than costing ~1.4 GB of LFS history.

## Running the tests

No API key needed for any of these.

```
for t in scripts/translate/test_*.py scripts/test_*.py; do python "$t"; done
```

Each prints `PASSED n FAILED n` and exits non-zero on failure.
