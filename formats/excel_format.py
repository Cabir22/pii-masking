"""Phase 4: Excel (XLSX).

Same column-classification logic as CSV (reused directly, not
reimplemented) plus the format's own real gotchas, each verified directly
against openpyxl rather than assumed:

  * Multiple sheets -- every sheet is walked independently; a column named
    "Telefon" on one sheet has no bearing on a column named "Telefon" on
    another.
  * Merged cells -- openpyxl reports the value ONLY on a merge range's
    top-left anchor cell; every other cell in the range is a `MergedCell`
    whose `.value` is None AND whose `.value` is read-only (writing to one
    raises `AttributeError`, confirmed directly). Cells with no value are
    already skipped by the same "nothing to mask" check every format module
    uses, which is what keeps this safe without a separate special case.
  * Numeric-typed cells -- a phone number typed into Excel without marking
    the column as text becomes a Python `int`, not `str` (confirmed
    directly: 501234567, not "0501234567" -- the leading zero is ALREADY
    gone before this code ever sees it, an Excel behaviour, not a bug this
    module introduces). Masked values are always written back as TEXT,
    deliberately, so a masked phone number can't lose a leading zero a
    second time the same way. This does mean a round-tripped cell that was
    originally numeric comes back as text, not the original number type --
    a real, deliberate trade-off, not silently swept under the rug.

Structure is preserved by modifying the loaded workbook's cells IN PLACE and
saving that same workbook, rather than extracting to a flat row-list and
rebuilding a fresh file the way csv_format does -- CSV has no real structure
beyond rows/columns to lose, Excel has merges, formatting, and other
untouched sheets that a rebuild-from-scratch approach would discard.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "model"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import openpyxl                                        # noqa: E402
from openpyxl.cell.cell import MergedCell               # noqa: E402

from csv_format import classify_column                  # noqa: E402
from masking import LABEL_ALPHABET, mask_value, unmask_value  # noqa: E402
from piigen.validate import value_valid                  # noqa: E402
from piigen.config import STRUCTURED_LABELS              # noqa: E402
from txt import mask_text, unmask_text                   # noqa: E402

DetectFn = Callable[[str], list]

_HEADER_SCAN_ROWS = 5  # how far down to look for a real header row


def _looks_like_data_row(row_cells: list) -> bool:
    """True if ANY cell in this row is itself a valid structured PII value
    (a real phone number, email, VOEN, IBAN, ...) rather than a short label
    word. A genuine header cell essentially never accidentally satisfies a
    checksum/format-verified pattern -- "Telefon" doesn't pass TELEPHONENUM's
    own validator, "VÖEN" doesn't pass az_voen_valid -- so even ONE hit here
    is strong evidence this row is DATA, not a header, independent of
    whatever the other cells in the same row look like (a name column has
    no pattern to check and will never trigger this either way).
    """
    for cell in row_cells:
        text = str(cell.value)
        if any(value_valid(label, text)[0] for label in STRUCTURED_LABELS):
            return True
    return False


def _detect_header_row(ws, max_scan: int = _HEADER_SCAN_ROWS) -> int:
    """Finds the header row within the first `max_scan` rows: the first row
    with at least one real cell that is NOT itself swallowed by a
    multi-column merge (a title banner) AND does not itself look like real
    data. Returns 0 -- a sentinel meaning "no header row exists; every row,
    including row 1, is data" -- but only on POSITIVE evidence: at least
    one scanned row must itself contain a verified structured value (a
    real phone/email/VOEN/...). An empty sheet, or one whose header simply
    sits below the scan window, has no such evidence and keeps the
    original row-1 fallback unchanged.

    Phase 6 fix for a real gap: a title banner merged across the sheet's
    width ("Müştəri Siyahısı", A1:D1) sitting on row 1 with the real header
    on row 2 is a common real-file shape this module could not handle
    before -- the earlier version just assumed row 1 always IS the header,
    and test_excel_format.py's own first fixture attempt had to be
    abandoned and rebuilt without a banner row specifically because of this.

    Reuses the exact same structural signal `_banner_rows` uses below (a
    merge spanning more than one column means "banner", not "data") rather
    than inventing a second, different heuristic for what is really the
    same question asked one row earlier.

    A later, separate real gap: a genuinely headerless file (row 1 is
    already the first customer record) used to fall through to the
    original hardcoded "row 1 is the header" default -- confirmed directly
    by building one and running it through mask_workbook: the entire first
    row of real PII (name, phone, email) got read as column HEADER TEXT,
    which this module never masks, and was silently written back to the
    "masked" file completely in plaintext. `_looks_like_data_row` closes
    that: a candidate row containing a real phone number or email is
    disqualified from being treated as the header, the same way a banner
    row already was.
    """
    saw_real_data = False
    for row in range(1, max_scan + 1):
        if row > ws.max_row:
            break
        row_cells = [c for c in ws[row]
                    if not isinstance(c, MergedCell) and c.value not in (None, "")]
        if not row_cells:
            continue
        banner_cols: set[int] = set()
        for rng in ws.merged_cells.ranges:
            min_col, min_row, max_col, max_row = rng.bounds
            if min_row <= row <= max_row and (max_col - min_col + 1) > 1:
                banner_cols.update(range(min_col, max_col + 1))
        if banner_cols and all(c.column in banner_cols for c in row_cells):
            continue  # every real cell in this row is inside a wide merge
        if _looks_like_data_row(row_cells):
            saw_real_data = True
            continue  # this row is itself a real record, not column labels
        return row
    # Only conclude "headerless" on POSITIVE evidence (a row that is itself
    # a verified structured value) -- an empty sheet, or one whose header
    # sits below the scan window, has no such evidence and keeps the
    # original row-1 fallback, exactly as before this fix existed.
    return 0 if saw_real_data else 1


def _sheet_columns(ws, header_row: int) -> dict[str, int]:
    """header text -> column index, from `header_row`. Empty header cells
    are skipped (no name to classify or report against).

    header_row == 0 means _detect_header_row found no real header at all
    -- every column gets a synthetic, positional name ("Column A", "Column
    B", ...) instead of real header text, since there is none. These names
    can never header-keyword-match anything in HEADER_KEYWORDS (by
    construction), so every column falls through to classify_column's
    value-pattern path: a phone/email/VOEN/etc. column still gets
    classified correctly from its DATA alone, while a GIVENNAME/SURNAME/
    CITY/STREET column -- which has no checkable pattern, only header
    keywords -- has no way to be identified at the column level without a
    real header and falls back to per-cell free-text detection instead
    (weaker on an isolated single-word cell than the same model sees a
    name embedded in a full sentence -- a real, separate detection-quality
    limitation, not something this function can fix structurally).
    """
    if header_row == 0:
        return {f"Column {openpyxl.utils.get_column_letter(c)}": c
               for c in range(1, ws.max_column + 1)}
    cols = {}
    for cell in ws[header_row]:
        if cell.value:
            cols[str(cell.value)] = cell.column
    return cols


def _banner_rows(ws, columns: dict[str, int]) -> set[int]:
    """Rows that are NOT real per-column data, despite sitting below the
    header -- detected via a real structural signal rather than a fragile
    heuristic like "stop at the first blank row" (which would wrongly
    truncate real data after a legitimate blank separator).

    Found by a real bug: a merged footer note ("Qeyd: bütün məlumatlar test
    üçündür.") spanning A5:D5 has its value on the anchor cell A5, which is
    an ordinary Cell (not a MergedCell), so the existing "skip MergedCell /
    empty" check never caught it -- it was classified as an ordinary column-A
    (GIVENNAME) value and format-preserving-encrypted as if it were a name,
    silently corrupting a cell nothing should have touched.

    The actual signal: a merge spanning MORE THAN ONE of the columns this
    sheet is tracking means "this row is a banner/note across the table
    width", not "row-per-record data" -- a genuine data row has each
    tracked column as its own independent cell, never merged with its
    neighbours.
    """
    tracked_cols = set(columns.values())
    banner_rows: set[int] = set()
    for rng in ws.merged_cells.ranges:
        min_col, min_row, max_col, max_row = rng.bounds
        spanned = {c for c in range(min_col, max_col + 1)} & tracked_cols
        if len(spanned) > 1:
            banner_rows.update(range(min_row, max_row + 1))
    return banner_rows


def _column_samples(ws, col_idx: int, header_row: int, max_rows: int = 50) -> list[str]:
    out = []
    for row in range(header_row + 1, min(ws.max_row, header_row + max_rows) + 1):
        cell = ws.cell(row=row, column=col_idx)
        if isinstance(cell, MergedCell) or cell.value in (None, ""):
            continue
        out.append(str(cell.value))
    return out


_COLUMN_CONSENSUS_MIN_SUPPORT = 2    # never promote off a single lucky match
_COLUMN_CONSENSUS_MIN_FRACTION = 0.4  # of all non-empty cells in the column


def _promote_unclassified_columns(ws, columns: dict[str, int],
                                  column_labels: dict[str, str | None],
                                  skip_rows: set[int], header_row: int,
                                  detect_fn: DetectFn
                                  ) -> dict[tuple[int, int], list[dict]]:
    """For every column classify_column left as None (free text), checks
    whether its OTHER cells -- the ones per-cell detection DID confidently
    tag -- agree strongly enough to promote the WHOLE column to that label
    anyway, in place, the same way a real header would.

    Why this closes a real, separate gap header-keyword matching and
    value-pattern matching both miss: GIVENNAME/SURNAME/CITY/STREET have
    no checkable format (pattern_fallback never touches them, by design --
    see its own module docstring), so a headerless name column has no way
    to be classified from a header (there isn't one) or a value pattern
    (there isn't one either). What it usually DOES have is other cells the
    model already found with high confidence, purely because that
    specific word's own shape happens to clear the model's confidence
    threshold alone -- confirmed directly by probing raw model output:
    "Poladxan" alone scores 93% confidence as GIVENNAME, "Ruslan" alone
    scores 33% and loses to "not an entity", even though both are real,
    well-represented training values and the model correctly tags
    "Ruslan" the moment ANY context is added. If most of a column's cells
    already agree on one label, that is strong in-document evidence the
    column IS that type, and the rare holdout cell should be masked too
    rather than left exposed just because its own isolated wording
    happened to land under threshold.

    Promotion requires a real MAJORITY (not unanimity) among cells that DID
    produce a single span covering their ENTIRE value (a cell that's mostly
    free text with an entity embedded partway through doesn't count -- that
    is genuinely free text, not a column of one type) plus a real double
    threshold: at least `_COLUMN_CONSENSUS_MIN_SUPPORT` agreeing cells AND
    at least `_COLUMN_CONSENSUS_MIN_FRACTION` of the column, not the 0.8
    agreement csv_format.classify_column's own value-pattern fallback
    uses for checksum-verified matches -- a checksum passing is near-
    certain, but this project's own measured isolated-name detection rate
    (53-97% depending on label/language) means even a genuinely
    homogeneous name column will legitimately have some cells the model
    misses alone; requiring 0.8 agreement here would mean this almost
    never fires on exactly the real columns it exists to help.

    Majority, not unanimity, is deliberate: confirmed directly on a real
    generated table, a "Владелец" (owner/name) column with 10 real given
    names scored 5 GIVENNAME / 1 CITY / 4 no-detection on isolated per-cell
    lookup -- the same GIVENNAME/CITY confusion documented elsewhere in this
    project's own weakness report (e.g. "Binagadi" tagged GIVENNAME instead
    of CITY). Under a unanimity rule, that ONE minority mislabel made
    `matched_labels` disagree and blocked promotion entirely, leaving all 4
    no-detection cells -- real names -- completely unmasked in the output
    file. A single dissenting cell is weak evidence against an otherwise
    5-1 majority and should not veto masking the rest of the column; a
    genuine tie (no majority at all) still correctly blocks promotion, same
    as before.

    Returns a cache of every (row, col_idx) this function already ran
    detect_fn on, so the main masking loop below never re-runs detection
    on a cell this pass already evaluated.
    """
    cache: dict[tuple[int, int], list[dict]] = {}
    for name, col_idx in columns.items():
        if column_labels[name] is not None:
            continue
        matched_labels: dict[str, int] = {}
        total = 0
        for row in range(header_row + 1, ws.max_row + 1):
            if row in skip_rows:
                continue
            cell = ws.cell(row=row, column=col_idx)
            if isinstance(cell, MergedCell) or cell.value in (None, ""):
                continue
            value = str(cell.value)
            spans = detect_fn(value)
            cache[(row, col_idx)] = spans
            total += 1
            if len(spans) == 1 and spans[0]["start"] == 0 and spans[0]["end"] == len(value):
                matched_labels[spans[0]["label"]] = matched_labels.get(spans[0]["label"], 0) + 1
        if total == 0 or not matched_labels:
            continue  # nothing matched at all -- no promotion
        total_matched = sum(matched_labels.values())
        best_label, best_count = max(matched_labels.items(), key=lambda kv: kv[1])
        if best_count * 2 <= total_matched:
            continue  # no true majority (e.g. an even split/tie) -- genuinely ambiguous
        if (best_count >= _COLUMN_CONSENSUS_MIN_SUPPORT
                and best_count / total >= _COLUMN_CONSENSUS_MIN_FRACTION
                and best_label in LABEL_ALPHABET):
            column_labels[name] = best_label
    return cache


def _load_workbook(path: str | Path):
    """openpyxl's own error for a non-XLSX file (`BadZipFile: File is not
    a zip file`) is accurate but assumes the reader already knows XLSX is a
    ZIP archive internally -- not obvious to whoever is just trying to mask
    a file. Re-raised with a message that says what actually went wrong in
    terms of the FILE, matching the clarity standard every other format
    module's error messages already hold (formats.txt's chardet failure,
    the span-boundary ValueError in mask_text, ...).
    """
    try:
        return openpyxl.load_workbook(path)
    except Exception as exc:
        raise ValueError(
            f"{path} could not be read as an Excel (.xlsx) file: {exc}. "
            f"Confirm it's actually XLSX and not renamed from another "
            f"format (.xls, .csv, ...) or corrupted.") from exc


def mask_workbook(path: str | Path, detect_fn: DetectFn, key: bytes
                  ) -> tuple["openpyxl.Workbook", dict]:
    """Loads `path`, masks every classifiable cell IN PLACE across every
    sheet, and returns (workbook, manifest). Caller saves the workbook
    wherever it wants: `wb.save(out_path)`.
    """
    wb = _load_workbook(path)
    manifest = {"sheets": {}}

    for ws in wb.worksheets:
        header_row = _detect_header_row(ws)
        columns = _sheet_columns(ws, header_row)
        column_labels = {name: classify_column(name, _column_samples(ws, idx, header_row))
                         for name, idx in columns.items()}
        skip_rows = _banner_rows(ws, columns)
        detection_cache = _promote_unclassified_columns(
            ws, columns, column_labels, skip_rows, header_row, detect_fn)

        free_text_spans: dict[str, list[dict]] = {}
        unsupported: list[dict] = []

        for row in range(header_row + 1, ws.max_row + 1):
            if row in skip_rows:
                continue
            for name, col_idx in columns.items():
                cell = ws.cell(row=row, column=col_idx)
                if isinstance(cell, MergedCell) or cell.value in (None, ""):
                    continue
                value = str(cell.value)
                label = column_labels[name]

                if label is not None and label in LABEL_ALPHABET:
                    cell.value = mask_value(label, value, key)
                elif label is not None:
                    unsupported.append({"row": row, "column": name, "label": label})
                else:
                    # A column NOT promoted above had every one of its
                    # cells already run through detect_fn during that
                    # pass -- reuse those spans rather than paying for a
                    # second real detection call on the same value.
                    cached = detection_cache.get((row, col_idx))
                    cell_detect_fn = (lambda t, s=cached: s) if cached is not None else detect_fn
                    cell_masked, cell_spans, cell_unsupported = mask_text(
                        value, cell_detect_fn, key)
                    cell.value = cell_masked
                    if cell_spans:
                        free_text_spans[f"{row}\x1f{name}"] = cell_spans
                    for u in cell_unsupported:
                        unsupported.append({"row": row, "column": name, **u})

        manifest["sheets"][ws.title] = {
            "header_row": header_row,
            "column_labels": column_labels,
            "free_text_spans": free_text_spans,
            "unsupported": unsupported,
        }

    return wb, manifest


def unmask_workbook(path: str | Path, manifest: dict, key: bytes
                    ) -> "openpyxl.Workbook":
    """Loads the MASKED file at `path` and reverses masking in place across
    every sheet, using the manifest mask_workbook produced. Returns the
    restored workbook; caller saves it wherever it wants.
    """
    wb = _load_workbook(path)

    for ws in wb.worksheets:
        sheet_manifest = manifest["sheets"].get(ws.title)
        if sheet_manifest is None:
            continue
        # The manifest's OWN recorded header_row is used rather than
        # re-detecting it here -- both would agree in practice (masking
        # never touches the header or banner rows' text), but reading it
        # from the manifest removes any dependency on that holding true
        # rather than just assuming it.
        header_row = sheet_manifest["header_row"]
        columns = _sheet_columns(ws, header_row)
        column_labels = sheet_manifest["column_labels"]
        free_text_spans = {tuple(k.split("\x1f", 1)): v
                           for k, v in sheet_manifest["free_text_spans"].items()}
        skip_rows = _banner_rows(ws, columns)

        for row in range(header_row + 1, ws.max_row + 1):
            if row in skip_rows:
                continue
            for name, col_idx in columns.items():
                cell = ws.cell(row=row, column=col_idx)
                if isinstance(cell, MergedCell) or cell.value in (None, ""):
                    continue
                value = str(cell.value)
                label = column_labels.get(name)
                key_lookup = (str(row), name)

                if label is not None and label in LABEL_ALPHABET:
                    cell.value = unmask_value(label, value, key)
                elif key_lookup in free_text_spans:
                    cell.value = unmask_text(value, free_text_spans[key_lookup], key)

    return wb
