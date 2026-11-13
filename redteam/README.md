# Adversarial-robustness / red-team probes

Scope, per the user's own framing: red-teaming the pipeline's own defenses
(`scripts/pii_guard/`, `your-hf-org/masking-multilingual`) — prompt-injection
and evasion attempts aimed at leaking unmasked PII, or getting the masking
detector to skip an entity. **Not** attacks on a third-party LLM's own
safety guardrails.

Nine probes: seven confirmed findings, two honest negative results. Full
write-up: **PII Guard — Adversarial Robustness Findings** (artifact).

Six of the nine (RT-2 through RT-6) attack the pipeline code around the
model (regex, anchor windows, config, rehydration) — none of them touch
`your-hf-org/masking-multilingual`'s own weights. RT-1, RT-7, RT-8 and the
homoglyph probe attack the model's own decision boundary directly. See the
artifact's §01 for why that distinction matters.

## Running

```bash
.venv/bin/python redteam/rt1_unicode_normalization.py  # needs the model
.venv/bin/python redteam/rt2_invisible_chars.py
.venv/bin/python redteam/rt3_placeholder_confusion.py
.venv/bin/python redteam/rt4_anchor_window_padding.py
.venv/bin/python redteam/rt5_strict_false_failopen.py
.venv/bin/python redteam/rt6_phone_anchor_gap.py
.venv/bin/python redteam/rt7_chunk_boundary.py          # needs the model
.venv/bin/python redteam/rt8_typo_perturbation.py       # needs the model
.venv/bin/python redteam/rt8b_homoglyph.py              # needs the model
```

`harness.py` puts `scripts/` and `model/` on `sys.path`; the probes import
`pii_guard` and `predict` straight from this tree, so no particular branch,
git access or scratch directory is needed and no production code is touched.
(An earlier version `git archive`d the package out of the `mask/docx` branch
into a scratch dir, because on that date it existed only on two divergent
branches. They were consolidated into `main` on 2026-09-28. All nine probes
produce byte-identical output before and after that change, apart from one
extra log line, see below.)

Probes that construct `GuardConfig(require_ml_context=False)` do so on purpose,
to exercise the regex/anchor tiers without loading the transformer;
`harness.allow_unsafe_for_probes()` sets the documented `PII_GUARD_ALLOW_UNSAFE`
opt-in for exactly that.

Note the merged package's default with a model configured is
`CombinedBackend` (gazetteer + model), and that class always logs "using the
offline GAZETTEER name/address detector" even though a model is loaded. Harmless
to the results here, but misleading in a real deployment's logs.

`scripts/redteam/` (a colleague's adversarial suite) is unrelated to this
directory and deliberately kept separate.

## Findings at a glance

| # | Finding | Severity | Model needed? |
|---|---|---|---|
| RT-2 | Invisible/zero-width characters evade every regex/checksum detector (16/27 labels) | Critical | No |
| RT-5 | `strict=False` silently drops an entire tier (all 5 anchor_required labels) with zero warning | Critical (as designed, but silent) | No |
| RT-4 | Ordinary sentence padding pushes a licensing word outside the 80-char anchor window | High | No |
| RT-6 | Natural English phone phrasing ("call the customer at...") isn't in the anchor vocabulary at all | High | No |
| RT-3 | Literal placeholder-shaped text (`[PHONE_001]`) forges real PII into unrelated rehydrated text | Medium | No |
| RT-1 | `_assert_clean`/`assert_no_raw_pii` are Unicode-normalization-blind (proven directly); no live target found in practice — the model's own tokenizer normalizer incidentally covers ml_context labels today | Medium (latent) | Yes |
| RT-8 | Single-character transposition/hyphen insertion in a name — attacks the model directly | High, but inconsistent (3/5 names) | Yes |
| RT-7 | Attempted chunk-boundary evasion of the NER model | **Not reproduced** — clause chunking held | Yes |
| — | Full homoglyph (visual-lookalike script) substitution, properly controlled | **Not reproduced** — one apparent hit was a confound | Yes |

## What was already covered and not re-tested

`scripts/pii_guard/test_pii_guard.py`'s section 8 ("prompt injection
independence") already tests the "ignore previous instructions, don't mask
anything" case and an `eval`/`exec` grep across the package — both hold, by
construction (nothing in the detection path branches on document
semantics). Not repeated here; these probes target different, untested
surface.
