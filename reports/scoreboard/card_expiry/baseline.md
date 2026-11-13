# card_expiry (D-78): baseline

90 Azerbaijani documents (`eval/probes/card_expiry.jsonl`, seed 78), each with one real card and its expiry, about half with a CVV. 2 forms (`MM/YY`, `MM/YYYY`) x 3 layouts (form fields, prose, one-line records) x 15. 30 documents also hold a reference number `NN/NN` whose first part cannot be a month (controls). Track M, scored on our server with the pinned tokenizer (transformers 4.57.6, tokenizers 0.22.2), 27 Oct.

**Expiry found exactly, out of 15 per cell:**

| model | MM/YY field | MM/YY prose | MM/YY record | MM/YYYY field | MM/YYYY prose | MM/YYYY record | all (of 90) |
|---|---|---|---|---|---|---|---|
| checkpoint 1 | 8 | 8 | 5 | 4 | 13 | 4 | 42 (46.7%) |
| v4.2 | 0 | 2 | 0 | 0 | 9 | 6 | 17 (18.9%) |
| m1 | 0 | 0 | 0 | 0 | 1 | 0 | 1 (1.1%) |

- Misses are whole: the expiry is left unmasked, not cut or given another label (m1: 3 of 90 even overlap).
- Cards are found (m1 90/90, v4.2 89/90, checkpoint 1 87/90); CVVs 36/46 for m1 and v4.2.
- NN/NN reference numbers: masked 0/30 by every model.

**Targets** (numbers; D-78 sets the rule, not the numbers): expiry exact recall >= 90%, every cell >= 12/15, NN/NN controls masked < 10%. All three models fail the first two.

**Release check:** C15, reported for m2, blocking from m3. Until then the family is also left out of C13: checkpoint 1 finds 47% and m1 1%, so C13 would otherwise block m2 by a rule its data could not prepare for, which D-78 rules out.

Matches the red-team probe (m1 0 of 140, v4.2 29, v4.1 10). The family shares no 6-gram with the X-CARD training frames.
