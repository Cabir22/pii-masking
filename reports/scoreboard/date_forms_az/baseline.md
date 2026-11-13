# date_forms_az (D-82): baseline

75 Azerbaijani documents (`eval/probes/date_forms_az.jsonl`, seed 82), one DATE each, 15 per cell. 25 also hold a weekday on its own (controls). Track M, scored on our server with the pinned tokenizer (transformers 4.57.6, tokenizers 0.22.2), 28 Oct.

Why: D-82 changes two things about Azerbaijani dates in m2, and no Azerbaijani set in the release check measures either. The benchmark has no weekday next to a date and no year-first date, and A7 covers EN/TR/RU only.

**Date found exactly / masked at all (any overlap), out of 15 per cell:**

| model | plain | weekday before | weekday after | year-first `2023-cü il oktyabrın 15` | year-first `2025-ci ilin 12 may` | exact, all (of 75) |
|---|---|---|---|---|---|---|
| checkpoint 1 | 14 / 14 | 5 / 15 | 3 / 15 | 0 / 8 | 6 / 14 | 28 (37.3%) |
| v4.2 | 15 / 15 | 1 / 15 | 1 / 15 | 0 / 0 | 0 / 0 | 17 (22.7%) |
| m1 | 15 / 15 | 0 / 15 | 3 / 15 | 0 / 6 | 1 / 5 | 19 (25.3%) |

- **Weekdays:** every model masks the date but takes the weekday with it (exact misses, D-54d). This is what the D-82 relabel fixes. It is a span-policy error, not a leak.
- **Year-first dates:** a real leak. v4.2 leaves all 30 unmasked, and m1 masks 11 of 30, only in part. X-DFRAG and the year_before relabel teach these, but only if both are ready on Thu 29; otherwise they wait for m3 (D-82).
- Plain dates are fine: 14-15 of 15 for every model, so the misses come from the weekday or the year-first form.
- A weekday on its own: masked 0/25 (m1, v4.2) and 1/25 (checkpoint 1).

**Targets** (numbers, as weekday_outside_date_tr): DATE exact recall >= 85%, every cell >= 12/15, weekdays on their own masked < 10%. All three models fail the first two.

**Release check:** C16, reported, and left out of C13. Otherwise checkpoint 1's 28 vs m1's 19 would already trip C13 (more than 10 points and 3 documents), a rule m1's data could not prepare for. For m2, expect the weekday cells to rise if the relabel is applied, and the year-first cells to rise only if `forms.y` is on.

Matches the X-DFRAG counts (weekday inside for 93-100% of dates; year-first found 7.7% by m1, 0% by v4.2). The family shares no 6-gram (or 5-gram) with the training frames, X-DFRAG's included.
