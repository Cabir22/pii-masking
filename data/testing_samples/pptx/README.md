# PPTX test fixtures

Untracked until now; collected here so they live with the other format fixtures
(`txt/`, `excel/`, `pdf/`, `web_style/`, ...).

| dir | files | what |
|---|---|---|
| `ppts/` | 200 | `llm_az_NNNNNN.pptx` -- Azerbaijani presentations, ids from the `llm_az` corpus |
| `multilingual/{az,en,ru,tr}/` | 50 / 50 / 48 / 48 | translated variants of the same source ids, named `llm_az_NNNNNN__<lang>.pptx` (az has no suffix) |

Used to benchmark `your-hf-org/masking-multilingual` on PPTX.
No gold labels are stored here.
