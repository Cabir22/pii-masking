# Training Reference — Base Model Choice & Training Plan

Scope of this doc: (1) why the base model is `FacebookAI/xlm-roberta-large`
and how it compares to the alternatives, at the architecture/layer level, and
(2) concretely how we fine-tune it. This is the Stage 4 reference — see
[`plan.md`](plan.md) Stage 4/5 for where it sits.

Status: base model already decided (2026-08-25 research + 2026-08-26
tokenizer audit). This doc records the reasoning and turns it into a training
plan; it does **not** reopen the decision.

---

## 1. What the task actually is

We are training a **token-classification (NER) head** on top of a pretrained
encoder:

- Input: a document (Azerbaijani, for now), tokenized to subwords.
- Output: one label per subword token, `B-<TYPE>` / `I-<TYPE>` / `O`, over
  the 27-label taxonomy (`data/schema.md`). Character spans are reconstructed
  from token predictions.
- Success metric: entity-level F1 (`seqeval`), with **recall weighted
  heavily** — a missed span is leaked PII, which is worse than a false
  positive.

Two architectural facts follow from this framing and they drive the whole
model choice:

1. **The task is per-token labelling, not generation.** The natural head is a
   linear layer over each token's contextual vector. No decoding, no beam
   search, no JSON to parse, exact offsets for free.
2. **Every token needs left *and* right context.** "Bakı" is a `CITY` in one
   sentence and a surname in another; `34` is an `AGE` or a `BUILDINGNUM`
   only by its neighbours. The model must attend in both directions at every
   layer.

That second point is why we use an **encoder-only (bidirectional)**
transformer and not the alternatives:

| Family | Example | Why not for this task |
|---|---|---|
| Decoder-only (causal) | Llama, GPT, Qwen | Each token only sees tokens to its **left**. You can bolt NER on, but you pay for a 7B+ model to approximate context an encoder gets natively at 0.5B, and you still fight nondeterminism, prompt drift, JSON/offset alignment, and per-label precision across 27 classes. Inference cost is 10–50× higher. |
| Encoder-decoder (seq2seq) | T5, mT5, BART | Full bidirectional encoder, but you're forced to *generate* the answer (e.g. "tag: value" pairs). Reintroduces decoding, offset reconstruction, and hallucinated spans. Pure overhead for a labelling task. |
| **Encoder-only (MLM)** | **XLM-R**, BERT, DeBERTa | Bidirectional self-attention at every layer; a cheap linear head does the labelling; deterministic; exact offsets; trivially evaluated with `seqeval`. **This is the right family.** |

So the real question is *which encoder-only model*, and that is a question
about pretraining data and capacity, not architecture novelty.

---

## 2. XLM-RoBERTa-large: the architecture and its layers

`xlm-roberta-large` is architecturally a **RoBERTa-large encoder** (which is
itself BERT-large with a cleaner training recipe), retrained on 100
languages. There is nothing exotic in the layer stack — its strength is the
pretraining, not a new attention mechanism.

### 2.1 Layer-by-layer

```
Input text
  │
  ▼
SentencePiece tokenizer  (unigram LM, 250k shared multilingual vocab)
  │  subword ids
  ▼
Embedding layer
  ├─ token embedding      (250 002 × 1024)
  ├─ position embedding   (learned, absolute, positions 0..511)
  └─ [no segment/NSP embedding used, no language embedding]
  │  → LayerNorm → dropout
  ▼
24 × Transformer encoder block:
     ├─ Multi-head self-attention   (16 heads × 64 dim = 1024)
     │     → residual add → LayerNorm            (post-LN)
     └─ Feed-forward:  1024 → 4096 → 1024, GELU
           → residual add → LayerNorm
  │  → per-token contextual vector, 1024-dim
  ▼
Task head (ours):  dropout → Linear(1024 → 27·2+1 BIO labels)
  │
  ▼
Per-token logits → softmax → BIO tags → char spans
```

### 2.2 The numbers

| Property | `xlm-roberta-base` | `xlm-roberta-large` (**ours**) |
|---|---|---|
| Encoder layers | 12 | **24** |
| Hidden size (d_model) | 768 | **1024** |
| Attention heads | 12 | **16** |
| Feed-forward size | 3072 | **4096** |
| Total parameters | ~270 M | **~550 M** |
| Max sequence length | 512 | 512 |
| Vocabulary | 250 002 (shared) | 250 002 (shared) |
| Pretraining data | CC-100, 2.5 TB, 100 languages | CC-100, 2.5 TB, 100 languages |
| Pretraining objective | Masked LM only (no NSP) | Masked LM only (no NSP) |

### 2.3 What in the pretraining recipe actually helps us

- **CC-100: 2.5 TB of filtered CommonCrawl across 100 languages**, including
  Azerbaijani (~1–2 GB of AZ text). This is the single most important point:
  the model has genuinely seen Azerbaijani morphology, address grammar, and
  name patterns during pretraining. Most alternatives have not, or have seen
  far less.
- **Shared 250k SentencePiece vocabulary, no language embeddings.** Azerbaijani
  words fragment into fewer, more meaningful subwords than they would under an
  English-only tokenizer, so entity boundaries land on cleaner token
  boundaries. The 2026-08-26 tokenizer audit checked this at the label level
  and is why the split pipeline sizes its sliding window to XLM-R's real cap
  (`max_length=512, stride=256`) and patches punctuation boundaries
  (`add_punctuation_boundary()`, span-recoverability 98.386% → 99.982%).
- **RoBERTa recipe:** dynamic masking, no next-sentence-prediction objective,
  large batches, long training. Consistently ~2–4 F1 over the older BERT
  recipe on downstream NER.
- **Encoder depth (24 layers, 1024-dim).** Fine-grained entity typing (27
  labels, many of them near-collisions — `ZIPCODE` vs `BUILDINGNUM`,
  `TELEPHONENUM` vs `AZ_VOEN`, `AZ_FIN` vs an order code) needs the extra
  representational capacity to separate classes that look identical at the
  character level and differ only by context. This is exactly where `-large`
  pulls ahead of `-base` on rare labels and hard negatives.

### 2.4 How it compares to the concrete alternatives

| Candidate | What it is | Why not (for AZ PII NER, now) |
|---|---|---|
| **`xlm-roberta-base`** | Same model, 12 layers / 270 M | Viable fallback. But `-large` typically adds **+2–5 entity-level F1** on NER, and the gain concentrates in *rare labels* and *recall* — precisely the metrics that matter when a miss = leaked secret. The original reason to prefer `-base` (multilingual capacity budget spread over 4 languages) went away when scope narrowed to AZ-only. |
| **mBERT** (`bert-base-multilingual-cased`) | 110 languages, Wikipedia-only, 110k vocab, old BERT recipe | Pretrained on ~an order of magnitude less data, smaller vocab (worse AZ subword splits), no RoBERTa improvements. Consistently below XLM-R on multilingual NER (CoNLL, WikiAnn, MasakhaNER). No upside here. |
| **mDeBERTa-v3-base** | DeBERTa-v3 (disentangled attention + ELECTRA-style replaced-token-detection pretraining), multilingual, CC-100 | Genuinely strong — often matches or beats `xlm-roberta-large` on multilingual NER **despite being base-size**, thanks to the RTD objective. The blockers: (a) there is **no large multilingual DeBERTa-v3** published, so we can't get the capacity headroom we want; (b) smaller ecosystem of ready PII/NER checkpoints and tokenizer/fine-tuning quirks historically. Keep it as the **first thing to A/B** against our XLM-R-large baseline in Stage 5. |
| **DeBERTa-v3-large** | Same, but **English-only** | Best-in-class on English NLU, but it never saw Azerbaijani and its tokenizer shreds AZ text. Wrong tool while scope is AZ-only. Revisit if/when an English phase starts. |
| Monolingual AZ / Turkish BERTs (BERTurk, LocalDoc-style AZ models) | Small encoders trained on AZ or TR corpora | AZ models are small, trained on far less data, thinly documented, weak tooling. Turkish models rely on Turkic proximity — related but not identical morphology, a silent accuracy tax. XLM-R already contains real AZ pretraining data *and* is battle-tested. |
| `distilbert`, `MiniLM`, `xtremedistil` | Distilled small encoders | Speed/size play for later (serving), not accuracy. Premature — we distil *from* a good teacher once we have one, per `plan.md` Stage 6. |
| Decoder LLM (few-shot or fine-tuned) | Llama/Qwen/GPT-class | Covered in §1: 10–50× inference cost, nondeterministic, offset/JSON fragility, hard to hit 27-label precision, expensive on-prem. Not competitive for a high-volume deterministic masking service. |

### 2.5 The costs we are accepting

- **~550 M params.** Fine-tuning needs ~24–32 GB VRAM at seq-len 512 with
  bf16 + gradient checkpointing (see §3.5). Fits one A100 40 GB / 48 GB card
  comfortably; a 24 GB card needs small per-device batch + accumulation or
  frozen embeddings.
- **Latency:** ~2–4× `-base` at inference. Acceptable for batch masking;
  addressed later with ONNX/quantisation/distillation (Stage 6) if the online
  path needs it.
- **Fine-tuning instability.** `xlm-roberta-large` occasionally has a
  degenerate run that collapses to all-`O` predictions. Mitigations are
  standard and in the recipe below (low LR, long warmup, multiple seeds, kill
  early if val-F1 ≈ 0 after epoch 1).

---

## 3. How we train it

### 3.1 Inputs

- `data/processed/{train,val,test}.jsonl` from `prepare_splits.py` —
  stratified 80/10/10 by `(lang, rarest label present)`, with the
  cross-split leakage report attached. **Not generated yet** (`plan.md`
  Stage 3 open items: decide 81,818 vs wait-for-100k, repair the 25k
  negative-class file, merge).
- Negative-class docs (target ~25k) mixed into all three splits so the model
  and the eval both see "text that looks like it has PII but doesn't".
- Format per line: `{"text", "lang", "entities":[{start,end,label}]}`,
  end-exclusive char offsets, no overlaps (`data/schema.md`).

### 3.2 Label alignment (already built)

Handled by `prepare_splits.py::align_labels_for_window` — do not reimplement:

- Sliding window, `max_length=512`, `stride=256`, over the fast tokenizer's
  offset mapping.
- **First subword of an entity → `B-<TYPE>`; continuation subwords →
  `I-<TYPE>`; all non-first subwords of any word → label id `-100`** so they
  are ignored by the loss and by `seqeval`.
- Special tokens (`<s>`, `</s>`, `<pad>`) → `-100`.
- Punctuation-boundary patch applied so spans that abut punctuation stay
  recoverable.
- BIO now; escalate to BIOES only if error analysis shows adjacent same-type
  entities merging (`data/schema.md`).

### 3.3 Model + head

```python
from transformers import AutoModelForTokenClassification, AutoTokenizer

MODEL = "FacebookAI/xlm-roberta-large"
tok   = AutoTokenizer.from_pretrained(MODEL)          # fast tokenizer required
model = AutoModelForTokenClassification.from_pretrained(
    MODEL,
    num_labels=len(label2id),          # 27 types → 55 BIO labels incl. O
    id2label=id2label, label2id=label2id,
)
```

The head is a single `dropout → Linear(1024 → num_labels)`. No CRF for v1
(same rationale as BIOES: add only if boundary errors in the confusion matrix
justify it).

### 3.4 Hyperparameters — starting point

| Knob | Value | Note |
|---|---|---|
| Optimizer | AdamW, β=(0.9, 0.999), eps=1e-8 | no weight decay on bias / LayerNorm |
| Weight decay | 0.01 | |
| Learning rate | **1e-5** (try 2e-5) | `-large` is LR-sensitive; 3e-5+ is a common cause of the all-`O` collapse |
| LR schedule | linear warmup **10%** of steps → linear decay to 0 | long warmup aids stability |
| Effective batch size | 32 (per-device 8 × grad-accum 4) | drop to 16 if VRAM-bound |
| Epochs | 3–5 | ~80k docs; early stop below |
| Early stopping | on val micro-F1, patience 3, eval every ~0.25 epoch | |
| Max grad norm | 1.0 | |
| Precision | bf16 (Ampere+) else fp16 | |
| Gradient checkpointing | on | ~40% memory cut, ~20% slower |
| Dropout | 0.1 (hidden + classifier) | default |
| Seeds | **run 3** (e.g. 13, 42, 123) | keep best on val; a seed that sits at F1≈0 after epoch 1 is dead — kill it |
| Optional stabiliser | freeze token embeddings (256 M params) | saves memory, adds stability, negligible F1 cost for NER |
| Class weighting / focal loss | **off initially** | revisit only if per-label recall analysis shows a starved label |
| Label smoothing | off | standard for NER |

### 3.5 Training loop & infra

- HF `Trainer` + `DataCollatorForTokenClassification` (dynamic padding). No
  need for a hand-rolled loop for the baseline.
- `compute_metrics` = `seqeval` (see §3.6).
- `load_best_model_at_end=True`, `metric_for_best_model="eval_f1"`,
  `greater_is_better=True`.
- Checkpoint every eval; keep last 2 + best. Confirm resume works before the
  full run (see memory note on the stale-process hazard — a long run that
  can't resume cleanly is a real risk).
- Log: train/val loss, micro-F1, macro-F1, and per-label F1 to
  TensorBoard/W&B every eval step.
- Expected footprint: one 40 GB GPU, seq-len 512, per-device batch 8, bf16 +
  checkpointing ≈ 24–32 GB used. ~80k docs × 4 epochs ≈ a few hours on an
  A100.

### 3.6 Evaluation

Primary (`seqeval`, entity-level, `mode="strict"`, `scheme=IOB2`):

- **Micro-F1** — headline number.
- **Macro-F1** — catches rare-label collapse that micro hides.
- **Full per-label precision / recall / F1 table** — this is what drives
  Stage 5 targeted data generation.

PII-specific, on top of `seqeval`:

- **Character-level leakage rate** — fraction of gold PII *characters* left
  unmasked. This is the number the product is actually judged on; track it
  separately from F1.
- **Recall-first reporting.** For high-harm labels (`API_KEY`, `PRIVATE_KEY`,
  `ACCESS_TOKEN`, `IBAN`, `PAYMENT_CARD_NUMBER`, `AZ_PASSPORT_NUMBER`, …)
  report recall prominently and consider a recall-biased decode threshold at
  serving time.
- **Hard-negative / collision tracking** — explicit metrics for the pairs
  called out in `data/schema.md`: `ZIPCODE` vs `BUILDINGNUM`,
  `TELEPHONENUM` vs `AZ_VOEN`, `AZ_FIN` vs order codes / short SHAs.
- **False-positive rate on the negative-class split**, per label.
- **Golden set** (`data/golden/golden_az.jsonl`): has **8 known defects**
  (`plan.md` risk #6). Decide fix-or-accept *before* using it as a gate;
  don't silently score against a known-broken reference.

### 3.7 Risks specific to this training run

- **Splits not built yet.** `prepare_splits.py` has never run end-to-end on
  final data — first real run may surface something the 52 fixture tests
  didn't (`plan.md` risk #3).
- **Negative corpus not repaired.** Don't merge the 25k negative-class file
  into training until it's been through `migrate_dataset.py` + the filter
  scripts (`plan.md` risk #7).
- **Stale-generation hazard** (memory): only train on records produced
  *after* the last `piigen` fix; records carry no version stamp, so this is a
  process check, not a query.
- **Planned-value blind spot** (memory): ~8% of documents. Val/test recall on
  `ml_context` labels (`GIVENNAME`, `SURNAME`, `CITY`, `STREET`) may look
  better than it generalises — hold out a **human-checked** slice for those
  labels before trusting the number.
- **`xlm-roberta-large` instability**: see the multi-seed / kill-early note in
  §3.4.

### 3.8 First run = de-risk, not tune

Before the full multi-seed sweep:

1. Take ~5k train / ~1k val, 1 epoch, LR 1e-5.
2. Confirm train loss decreases and val F1 climbs off zero.
3. Decode ~20 val predictions back to **character spans** and eyeball them
   against `text` — this is the real test that §3.2 alignment survived the
   round trip on non-fixture data.
4. Confirm `seqeval` metrics wire up and per-label numbers render.
5. Confirm checkpoint save + resume.

Only then run the full 3-seed training. Goal of the first real run, per
`plan.md` Stage 4, is an **end-to-end baseline F1**, untuned — de-risk the
pipeline, then iterate in Stage 5.

---

## 4. Open decisions (carry into Stage 4 kickoff)

- 81,818 true-positive docs now, or wait for the paused run to reach 100k?
- Fix the 8 golden-set defects, or record explicit acceptance?
- bf16 vs fp16 — depends on the actual training GPU.
- Whether to A/B `mdeberta-v3-base` against the XLM-R-large baseline in
  Stage 5 (recommended — it's the only alternative with a real chance of
  winning, and it's cheaper to serve).
