# FORMATS red-team of v4.2: findings (23 Oct 2026)

**Question:** if the same personal data appears in an unusual format, does v4.2 still mask the whole value with the right label?
**Model:** `your-hf-org/masking-az-runb-v4.2-seed42@223e54e8`, product decoding **M** (`validity-2`, decides, D-64a), raw **R** for comparison. Windows of 512 tokens, stride 256, no truncation; run on the Mac CPU.
**Data:** 200 frozen, validated cases (8 groups × 5 families × 5) in `formats_az_v42_200.jsonl`, plus 42 follow-up probes kept separate. All values are invented. Labels follow the labelling decisions, with **D-72** (format conventions) written **before** the run.
**This set is deliberately hard:** its scores are not comparable with the benchmark's ~97.

## Results in one table (M)

| | Result |
|---|---|
| Values fully masked (any label) | **284 of 315 (90.2%)** |
| Exact span and label (F1) | 88.7 (P 90.4%, R 87.0%) |
| Missed / partly masked / wrong type | 24 / 7 / 4 |
| False alarms | 5 (2 of 8 negative-only cases) |
| Cases fully safe (all values masked, no false alarm) | 166 of 200 |

R gives the same coverage, with 3 more partial masks (M's word-consistency repairs those).

**By group:**

| Group | Fully masked | Note |
|---|---|---|
| G1 structured (JSON, CSV, YAML, XML, HTML, Markdown, SQL) | 100% | every variation passes |
| G2 logs (access, JSON, syslog, audit, traces, IPv6/MAC) | 100% | one false alarm (IP:port) |
| G3 spacing (grouping, line breaks, NBSP, glued labels) | 100% | one false alarm (spaced code → IBAN) |
| G4 hidden characters (zero-width, bidi marks, look-alikes, digit scripts, NFD) | 97% | masks hide the values; only the edges differ |
| **G5 disguised and spelled-out** | **38%** | the main weakness |
| G6 long and mixed documents (positions, chunk edges, tables, languages) | 97% | chunk edges all pass |
| G7 document types (letters, forms, receipts, chats, headers) | 98% | |
| **G8 encodings** (URL, HTML entities, JSON escapes) | **59%** | the second weakness |

## What holds (no action needed)

- **Structure doesn't break it.** JSON of any size, nesting or layout; CSV, TSV and quoted fields; YAML; XML; HTML attributes; Markdown tables; SQL; logs; stack traces.
- **Spacing doesn't break it.** Dots, hyphens and brackets in phones; a line break inside a card number (LF, CRLF, mid-group); tabs and non-breaking spaces in an IBAN; a label glued to the value (`Telefon+994…`, `тел.+994…`).
- **Hidden characters don't break it.** Zero-width spaces and bidi marks inside values (the mask splits around them, but nothing readable stays visible); Cyrillic and Greek look-alike letters; **full-width and Arabic-Indic digits**; decomposed letters (NFD).
- **Long documents and chunk edges are fine.** A value cut by a window's edge is still masked whole (it sits whole in the overlapping window), and so is one at the start, middle or end of a long document.
- **Other languages around the value are fine:** English, Russian (Cyrillic names), Azerbaijani without its letters.

## Findings, by severity

**Visible leaks: the value stays readable.**

1. **Spoken digits are never masked.** A phone in words (`üstəgəl doqquz yüz doxsan dörd …`, `sıfır beş sıfır …`) is missed in all 5 forms. The same number in digits is found. (RT-0075, -0012)
2. **IDs spaced or dotted character by character are missed, for every ID type:** FIN, VÖEN, passport and ID card (`5 R T 8 V Q 2`, `1 7 0 2 …`). Grouping matters: `5RT 8VQ2` (3-4) is found, but `5R T8 VQ2` (2-2-3) is missed. The unspaced controls pass. (-0013 to -0016)
3. **Disguised e-mails leak, and the result depends on the address.**
   - `' at '` and `[dot]`/`' dot '` leave the whole address visible.
   - `[at]` and `(at)` are sometimes masked whole and sometimes split, which can leave `.rzayeva(at)poct` visible.
   - (-0007 to -0010)
4. **HTML entities hide e-mails from the model:** `&#64;`, `&#x40;`, `&commat;`, and a mix. All are missed, in HTML, in plain text, and in a `mailto:` link. The literal `@` is found. (-0017, -0018)
5. **Literal escapes and URL-encoding:** `@` in JSON text and `%2B994%2055…` (single or double encoded) are missed. (-0019, -0020)
6. **IP with a port can leak its last octet:** `91.198.36.14:443` is masked as `[IPV4].14`. A second IP:port produced a stray `:` IPv6 mask instead. (-0031)
7. **`Leyla` in table cells is missed.** That happens in a one-row table and in an 8-row table, and with another surname too. `Leyla` in a sentence, and `Lalə` in the same cell, are found. The name probably reads as a common word without context (compare the earlier `Leyla` → CITY finding). (-0023, -0024)
8. **A surname-first display name** (`From: "Əliyev, Rauf"`, `From: Əliyev Rauf`): the given name is missed in headers, but found in a sentence. (-0025, -0026)
9. **A name inside escaped JSON within a JSON string** is missed (the e-mail beside it is found). (-0027)
10. **FIN and VÖEN glued together** (`7KD3M2X1702938461`) are both missed. (-0032)

**Wrong type: the value is hidden, but labelled wrong.**

11. **E-mails and phones inside a URL query are masked as part of a URL.** D-72a says EMAIL or TELEPHONENUM, and a URL without a token is not labelled. Privacy holds, but the type is wrong, and the plain URL parts become false alarms. (-0021, -0022)

**False alarms**

12. **Order codes look like IBANs:** spaced (`SIF 2026 0048 1752 3301 7720`) and dashed (`SIF-2026-0048-…`). (-0028, -0029)
13. **A 10-digit order number after `Sifariş №` is masked as VÖEN** (ASCII and full-width). After `Sifariş nömrəsi:`, it isn't. (-0030)

**Earlier finding re-checked:** the "phone cut to `+` in JSON" (RT-0065) reproduces only with that exact value (`+994501234567`) in that four-field shape. Another phone in the same shape, fewer fields, or Azerbaijani keys all pass. It depends on the value, not on JSON.

## Recommendations for m2

**Training data** (added to the m2 extra batch as **X-FMT**):
- spoken digit sequences for phones and IDs;
- IDs spaced, dotted and hyphenated per character, plus 2-2-3 and 3-4 grouping;
- every e-mail disguise form, with both delimiters;
- HTML-entity, `\u`- and percent-encoded e-mails and phones;
- IP:port in logs (address only);
- `Leyla`-type names in table cells;
- surname-first display names in headers;
- e-mails and phones in token-free query strings (EMAIL/TELEPHONENUM, not URL);
- order codes shaped like IBANs or VÖENs after `Sifariş №`, unlabelled, beside real values.

**Preprocessing**, worth testing (not data): decode HTML entities and percent-encoding into a parallel text **with an offset map back to the raw text**, run the model on both, and mask the union in the raw text. That would fix items 4 and 5 without teaching the model encodings. It needs a design note and tests before it goes in.

**Inference:** item 6 (an IP:port partly masked) is a boundary issue at `:` followed by digits. Check it again after the X-FMT data before adding any rule (model-first strategy).

**Splits:** each family's 5 cases are near-duplicates. If any case is ever used for training, keep a whole family on one side of a split.

## Coverage notes

- **Labels not exercised here:**
  - DATE, TIME, AGE, ZIPCODE, STREET, BUILDINGNUM (other people's areas, and the date/time conventions are covered there);
  - ICCID, driver licence, CVV, API_KEY, ACCESS_TOKEN, PRIVATE_KEY (no format question that differs from the labels tested). The secrets would need care with the opaque-string policy (D-72k).
- **Not tested:** file paths and user names containing names (D-72i leaves them unscored until a native review); scanned or OCR noise; very long single lines over many windows.
- **Files:**
  - `formats_az_v42_200.jsonl` (cases), `manifest.jsonl`, `spans.jsonl`, `validation.md`;
  - `predictions.jsonl` (R and M per case), `results.jsonl` and `results.md` (per-case scoring and every failure);
  - `followup.py`, `followup_results.md`, `followup_predictions.jsonl`.
- **Reproduce:** `build_cases.py` → `run_cases.py` → `evaluate.py` → `followup.py`.
