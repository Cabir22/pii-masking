# English (golden_en): original score and a current-policy reassessment

The original gold is unchanged; this is a separate, documented view. Track M, exact spans.

| View | TP | FP | FN | P | R | F1 |
|---|---|---|---|---|---|---|
| original gold (A7's number) | 1016 | 329 | 11 | 75.5 | 98.9 | **85.7** |
| current policy, ambiguous against m1 | 1325 | 20 | 10 | 98.5 | 99.3 | **98.9** |
| current policy, ambiguous for m1 | 1332 | 13 | 10 | 99.0 | 99.3 | **99.1** |

Of m1's 329 non-exact predictions: **309 gold missing**, 13 model errors, 7 ambiguous. Of its 6 misses: 1 gold error(s), the rest model misses.

Checkpoint 1 (98.6 on the original gold) was trained on the same old corpus as this gold, with the same sparse labelling; under the current policy it would also lose the values it leaves unlabelled. **Not re-scored here:** checkpoint 1's own current-policy score would need the same review of its predictions.

| Verdict | Label | Spans | Reason |
|---|---|---|---|
| gold_missing | DATE | 192 | standalone date (D-17: every standalone date is DATE) |
| gold_missing | GIVENNAME | 81 | a real value of a person (names incl. chat speakers D-72h, address parts, ages, times, tokens) |
| gold_missing | SURNAME | 20 | a real value of a person (names incl. chat speakers D-72h, address parts, ages, times, tokens) |
| model_error | DATE | 8 | a piece of a date or a bare year (partial or wrong DATE) |
| gold_missing | CITY | 4 | a real value of a person (names incl. chat speakers D-72h, address parts, ages, times, tokens) |
| gold_missing | AGE | 3 | a real value of a person (names incl. chat speakers D-72h, address parts, ages, times, tokens) |
| gold_missing | BUILDINGNUM | 3 | a real value of a person (names incl. chat speakers D-72h, address parts, ages, times, tokens) |
| model_error | DATE | 2 | weekday inside DATE (D-54d: outside) |
| gold_missing | STREET | 2 | a real value of a person (names incl. chat speakers D-72h, address parts, ages, times, tokens) |
| gold_missing | ACCESS_TOKEN | 2 | a real value of a person (names incl. chat speakers D-72h, address parts, ages, times, tokens) |
| ambiguous | GIVENNAME | 2 | gold SURNAME vs predicted GIVENNAME: either reading is possible |
| ambiguous | CITY | 2 | a city in a company's address (organisation, D-2) — not settled |
| gold_missing | TIME | 2 | a real value of a person (names incl. chat speakers D-72h, address parts, ages, times, tokens) |
| ambiguous | EMAIL | 2 | organisation mailbox, no person — not settled |
| ambiguous | CITY | 2 | a settlement name inside a police department's name (D-2/D-66f-like) — not settled |
| model_error | STREET | 1 | street split; 'Link to' is not part of it |
| model_error | STREET | 1 | street split from its prefix |
| ambiguous | IPV4_ADDRESS | 1 | leading-zero octet in an obfuscated log — not settled |
| model_error | ACCESS_TOKEN | 1 | an asterisk from a masked card number |
| model_error | GIVENNAME | 1 | gold value not masked at all |
| model_error | BUILDINGNUM | 1 | gold value not masked at all |
| gold_error | AGE | 1 | gold AGE placed on '54' inside a time stamp (10:54), not on 'Age: 54' |
| model_error | AGE | 1 | gold value not masked at all |
