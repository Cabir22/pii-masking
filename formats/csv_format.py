"""Phase 3: CSV.

The genuinely new piece for this format (TXT's extract/mask/unmask is
reused as-is per cell, see below): deciding, per COLUMN, whether every cell
in it is a single structured value the checksum validators already know how
to mask directly, or whether it needs full per-cell entity detection because
it's free text with PII embedded in it (a "Notes" column).

Column classification, in order:
  1. Header name matches a known keyword for some label -> that label.
  2. No header match, but a sample of the column's own values pass that
     label's `value_valid` check (reused from piigen.validate, the same
     validator the training corpus itself was checked against -- not
     reimplemented) -> that label.
  3. Neither -> free text. Every cell is run through `formats.txt.mask_text`
     (the exact Phase-2 code, unmodified) with the same `detect_fn`.

Structured columns skip the NER model entirely -- a full transformer forward
pass per cell across a 10,000-row "Phone" column would be wasteful when
`checksums.py` already answers the question in microseconds. This is the
column vs. cell split flagged as the actual design goal back when Presidio's
own architecture was evaluated.
"""

from __future__ import annotations

import csv
import io
import re
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "model"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from piigen.config import STRUCTURED_LABELS          # noqa: E402
from piigen.validate import value_valid               # noqa: E402
from masking import LABEL_ALPHABET, mask_value, unmask_value  # noqa: E402
from txt import mask_text, unmask_text                # noqa: E402

DetectFn = Callable[[str], list]

# Header keywords per label, lowercase, AZ/EN/RU/TR (the corpus's own 4
# languages -- a real customer file could be headed in any of them).
# Consistent with piigen/locales/az.py's own LABELS dict where a clean
# correspondence exists ("Telefon" for phone, "E-poçt" for email, "FİN kod"
# for AZ_FIN), extended with the header variety that dict was never meant to
# cover (it generates ONE canonical prose field-label, not a matcher for
# arbitrary real-world spreadsheet headers).
HEADER_KEYWORDS: dict[str, list[str]] = {
    "TELEPHONENUM": ["telefon", "tel", "mobil", "nömrə", "phone", "mobile",
                     "телефон", "тел"],
    "EMAIL": ["e-poçt", "epoçt", "email", "e-mail", "mail", "почта",
             "электронная"],
    "GIVENNAME": ["ad", "given name", "first name", "imya", "имя"],
    "SURNAME": ["soyad", "surname", "last name", "familiya", "фамилия"],
    "CITY": ["şəhər", "city", "город"],
    "STREET": ["küçə", "ünvan", "street", "address", "улица", "адрес"],
    "BUILDINGNUM": ["bina", "ev nömrəsi", "building", "house no", "дом"],
    "ZIPCODE": ["poçt indeksi", "zip", "postal code", "индекс"],
    "DATE": ["tarix", "date", "дата"],
    "TIME": ["vaxt", "vaxtı", "saat", "saatı", "saati", "time", "время"],
    "AGE": ["yaş", "age", "возраст"],
    "AZ_FIN": ["fin", "fin kod", "fin kodu"],
    "AZ_VOEN": ["vöen", "voen"],
    "AZ_ID_CARD_NUMBER": ["şəxsiyyət vəsiqəsi", "id card", "id nömrəsi"],
    "AZ_PASSPORT_NUMBER": ["pasport", "passport", "паспорт"],
    "AZ_DRIVER_LICENSE_NUMBER": ["sürücülük vəsiqəsi", "driver licen",
                                 "driving licen"],
    "IBAN": ["iban"],
    "PAYMENT_CARD_NUMBER": ["kart nömrəsi", "card number", "card no",
                            "номер карты"],
    "CARD_SECURITY_CODE": ["cvv", "cvc", "kart kodu"],
    "MAC_ADDRESS": ["mac"],
    "ICCID": ["iccid", "sim"],
}

# How many non-empty sample values a value-pattern check needs to agree on
# before trusting it over "this is free text".
_SAMPLE_SIZE = 12
_SAMPLE_AGREEMENT = 0.8


def _normalize_header(h: str) -> str:
    return (h or "").strip().lower()


# Word-boundary matched, not plain substring containment. A real bug found
# by running an actual generated Excel file (not a synthetic unit test) and
# reading its output rather than only checking the parts a test happened to
# assert on: "ad" (GIVENNAME) is a substring of "soyad" (SURNAME), so
# "Soyad" was silently classified as GIVENNAME -- caught only because this
# demo run PRINTED the classification and it was visibly wrong, whereas
# earlier tests included "Ad"/"Soyad" columns in fixtures but never actually
# asserted on their classification. `(?<!\w)...(?!\w)` (Unicode-aware by
# default for str patterns) rejects a keyword match with a word character
# immediately before or after it, so "ad" only matches a header that IS
# "ad" (or has it as a separate word), never one that merely ends in it.
# This generalizes past the one bug found: "fin" inside a header like
# "Final", "age" inside "Package", "mac" inside a name are the same class
# of risk and are fixed by the same change, not patched individually.
def _keyword_matches(keyword: str, normalized_header: str) -> bool:
    pattern = re.compile(r"(?<!\w)" + re.escape(keyword) + r"(?!\w)")
    return pattern.search(normalized_header) is not None


def classify_column(header: str, sample_values: list[str]) -> str | None:
    """Returns a label if every cell in this column should be treated as
    ONE structured value of that label, else None (free text)."""
    norm = _normalize_header(header)
    for label, keywords in HEADER_KEYWORDS.items():
        if any(_keyword_matches(kw, norm) for kw in keywords):
            return label

    non_empty = [v for v in sample_values if v and v.strip()][:_SAMPLE_SIZE]
    if len(non_empty) < 3:
        return None  # too little data to trust a value-pattern guess
    best_label, best_score = None, 0.0
    # Sorted, not the raw set: data/schema.md documents a real, ACKNOWLEDGED
    # taxonomy collision -- a bare 10-digit string ("0501234567") is
    # simultaneously a valid TELEPHONENUM and a valid AZ_VOEN shape ("a
    # documented, unresolved-by-ordering collision", the schema's own
    # words). Iterating a Python set gave whichever label happened to win
    # UNDEFINED iteration order -- the same file could classify differently
    # across runs/Python versions. Sorting doesn't resolve the genuine
    # ambiguity (nothing can, by the schema's own admission), it just makes
    # the tie-break DETERMINISTIC. The practical impact of which one wins is
    # cosmetic, not a protection gap: TELEPHONENUM and AZ_VOEN share the
    # exact same digit alphabet in model.masking, so the actual mask/unmask
    # operation is byte-identical either way -- only the manifest's
    # recorded label differs.
    for label in sorted(STRUCTURED_LABELS):
        ok = sum(1 for v in non_empty if value_valid(label, v)[0])
        score = ok / len(non_empty)
        if score > best_score:
            best_label, best_score = label, score
    if best_score >= _SAMPLE_AGREEMENT:
        return best_label
    return None


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def _dedupe_fieldnames(fieldnames: list[str]) -> list[str]:
    """Phase 6 fix for a real, verified gap: stdlib csv.DictReader silently
    keeps only the LAST column's data when two columns share a header name
    (confirmed directly: fieldnames lists both, but the row dict ends up
    with one value -- the earlier column's data is gone with no error,
    because DictReader builds the row dict by assigning
    `row[fieldname] = value` per column position, so a later position with
    the same name simply overwrites the earlier one before the row object
    ever exists).

    The fix has to happen BEFORE DictReader ever runs, not after -- once a
    row dict has been built from a duplicate-header line, the earlier
    value is unrecoverable, there is nothing left to fix. So this renames
    duplicate headers to unique names ("Telefon", "Telefon (2)", ...)
    up front, and `extract` builds rows itself with `csv.reader` instead of
    `DictReader`, keyed on these already-unique names -- every column's data
    survives, and the rest of the pipeline (classify_column, mask_csv, ...)
    needs no changes since it only ever sees already-unique fieldnames.
    """
    seen: dict[str, int] = {}
    out = []
    for name in fieldnames:
        count = seen.get(name, 0) + 1
        seen[name] = count
        out.append(name if count == 1 else f"{name} ({count})")
    return out


def extract(path: str | Path) -> tuple[list[str], list[dict]]:
    """Returns (fieldnames, rows). Delimiter is sniffed rather than assumed
    to be a comma; encoding falls back through chardet exactly like
    formats.txt.extract does, for the same reason (not every file is UTF-8).
    Duplicate column headers are disambiguated rather than silently losing
    data -- see `_dedupe_fieldnames`.
    """
    raw = Path(path).read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        import chardet
        detected = chardet.detect(raw)
        encoding = detected.get("encoding")
        if not encoding:
            raise ValueError(f"{path}: not UTF-8 and chardet could not "
                             f"identify the encoding either")
        text = raw.decode(encoding)

    if not text.strip():
        return [], []

    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel  # comma default, matches stdlib's own default

    raw_reader = csv.reader(io.StringIO(text), dialect=dialect)
    try:
        raw_header = next(raw_reader)
    except StopIteration:
        return [], []  # header row present but nothing after it (or blank)
    fieldnames = _dedupe_fieldnames([h.strip() for h in raw_header])

    rows = []
    for raw_row in raw_reader:
        if not raw_row:
            continue  # csv.reader yields [] for a genuinely blank line
        # Short/long rows vs. the header are real, survivable messiness
        # (a trailing blank field omitted, a stray extra delimiter) --
        # pad/truncate rather than raise, matching DictReader's own
        # tolerant behaviour for this case rather than being stricter than
        # the tool it replaces.
        padded = raw_row + [""] * (len(fieldnames) - len(raw_row))
        rows.append(dict(zip(fieldnames, padded)))
    return fieldnames, rows


def write_csv(path: str | Path, fieldnames: list[str], rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Mask / unmask
# ---------------------------------------------------------------------------

def mask_csv(fieldnames: list[str], rows: list[dict], detect_fn: DetectFn,
            key: bytes) -> tuple[list[dict], dict]:
    """Returns (masked_rows, manifest). `manifest` records exactly what was
    done to each column/cell so unmask_csv can reverse it -- structured
    columns need only the label (every cell used the same one); free-text
    columns need the per-cell spans formats.txt.mask_text already returns.
    """
    column_labels: dict[str, str | None] = {}
    for col in fieldnames:
        samples = [r.get(col, "") for r in rows[:50]]
        column_labels[col] = classify_column(col, samples)

    masked_rows: list[dict] = []
    free_text_spans: dict[tuple[int, str], list[dict]] = {}
    unsupported: list[dict] = []

    for row_idx, row in enumerate(rows):
        masked_row = dict(row)
        for col in fieldnames:
            value = row.get(col, "")
            if not value:
                continue
            label = column_labels[col]
            if label is not None and label in LABEL_ALPHABET:
                masked_row[col] = mask_value(label, value, key)
            elif label is not None:
                # A structured label with no reversible mask. All 27
                # taxonomy labels have one now, so this is unreachable in
                # practice -- it stays because the alternative, if a label
                # ever loses or lacks a mask, is silently shipping it in
                # plaintext under a "masked" label. Reported, never faked.
                unsupported.append({"row": row_idx, "column": col, "label": label})
            else:
                cell_masked, cell_spans, cell_unsupported = mask_text(
                    value, detect_fn, key)
                masked_row[col] = cell_masked
                if cell_spans:
                    free_text_spans[(row_idx, col)] = cell_spans
                for u in cell_unsupported:
                    unsupported.append({"row": row_idx, "column": col, **u})
        masked_rows.append(masked_row)

    manifest = {
        "column_labels": column_labels,
        "free_text_spans": {f"{r}\x1f{c}": s for (r, c), s in free_text_spans.items()},
        "unsupported": unsupported,
    }
    return masked_rows, manifest


def unmask_csv(fieldnames: list[str], masked_rows: list[dict], manifest: dict,
              key: bytes) -> list[dict]:
    column_labels = manifest["column_labels"]
    free_text_spans = {tuple(k.split("\x1f", 1)): v
                       for k, v in manifest["free_text_spans"].items()}
    # keys were serialized as strings; row index must be int again
    free_text_spans = {(int(r), c): v for (r, c), v in free_text_spans.items()}

    rows: list[dict] = []
    for row_idx, row in enumerate(masked_rows):
        out_row = dict(row)
        for col in fieldnames:
            value = row.get(col, "")
            if not value:
                continue
            label = column_labels.get(col)
            if label is not None and label in LABEL_ALPHABET:
                out_row[col] = unmask_value(label, value, key)
            elif (row_idx, col) in free_text_spans:
                out_row[col] = unmask_text(
                    value, free_text_spans[(row_idx, col)], key)
        rows.append(out_row)
    return rows
