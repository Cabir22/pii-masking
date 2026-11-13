# Benchmark case catalogue (shared, before generation)

**Who adds cases:** anyone on the team.

**What a case is:** a **type** of situation the benchmark must cover, described abstractly. For example, "a Russian surname in the dative case after a preposition", or "an IBAN split across a line break". It is **not** a test document. Knowing case types is like knowing the rules, so everyone may contribute (plan Part B).

**Rules:**
- **Describe the case; don't paste a finished test document.** One short illustrative example is fine, marked `illustrative`, with **made-up** values. Never real personal data, and never a document from the benchmark, shadow sets or real-text sets.
- **One row per case** in `cases.csv`. Keep `id` unique: `<initials>-<number>`, e.g. `CB-014`.
- **Similar cases can both stay;** duplicates are merged when the matrix is built (task U3).

## Columns of `cases.csv`

| Column | Meaning | Example |
|---|---|---|
| `id` | unique id | `AH-003` |
| `added_by` | who | `team` |
| `languages` | `az`, `ru`, `en`, `tr`, or a pair such as `az+ru` | `ru` |
| `label` | one of our 27 labels, or `NONE` for a no-PII/look-alike case | `SURNAME` |
| `case_family` | short name of the situation | `dative surname after preposition` |
| `description` | what makes it hard, in one or two sentences | `Surname inflected (-ой/-у) after "к", the span must cover the whole inflected word` |
| `expected_label` | what the gold should say (convention reference if any) | `SURNAME, whole word (D-56d analogue for RU)` |
| `illustrative_example` | optional, made-up, marked illustrative | `illustrative: Письмо передано к Ивановой.` |
| `kind` | `positive` (real PII), `negative` (look-alike / no PII), `pair` (both) | `positive` |
| `domain_format` | where it appears | `email; prose` |
| `risk` | `high` (IDs, financial, secrets, names) / `medium` / `low` | `high` |
| `source` | how it was found: `manual`, `model error` (which model, which set: public sets only), `real-world observation`, `regulation/format spec` | `manual` |
| `track_hint` | `release`, `challenge`, `regression`, or `dev` | `release` |
| `notes` | anything else | |

**After the catalogue:** the cases are merged into the coverage matrix (Part F), with minimum counts. The design review approves them, and only then does generation start.
