"""Re-evaluate name recall after adding the unconditional gazetteer_names
tier, against the same 11-sample corpus and the same real model
(your-hf-org/masking-multilingual) used for the 42% baseline.

Ground truth: every GIVENNAME/SURNAME value that appears in each sample's
TEXT (paragraphs/tables/header/footer -- not embedded-image OCR, which is
evaluated separately from text detection in the earlier report too),
taken directly from scripts/pii_guard/gen_test_docs.py's own source
content (read directly, not assumed). For each ground-truth value, every
verbatim occurrence in the extracted text counts as one mention -- same
"every mention" methodology the 42% baseline report used. Patronymics
("Tofiq oğlu", "Vüqar qızı", Russian "-ovna"/"-ovich" middle names) are
deliberately NOT counted as GIVENNAME/SURNAME ground truth: they're a
separate name-part this taxonomy doesn't have a label for.

A mention counts as FOUND if any final (post-overlap-resolution)
detection's span overlaps it, regardless of which tier produced it --
this measures the combined pipeline's recall, matching what the user
actually receives.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # reports/pii_guard_docx/<this file> -> repo root
sys.path.insert(0, str(ROOT / "scripts"))

import pii_guard as pg  # noqa: E402
from pii_guard.config import GuardConfig  # noqa: E402

SAMPLES_DIR = ROOT / "scratch" / "pii_test_samples"
OUT_DIR = Path(__file__).resolve().parent
OUT_DIR.mkdir(parents=True, exist_ok=True)

# language grouping, matching the baseline report's AZ vs non-AZ split
AZ_SAMPLES = {
    "sample_02_insurance_claim_az.docx",
    "sample_07_university_transcript_az.docx",
    "sample_11_employment_reference_az.docx",
}

GROUND_TRUTH = {
    "sample_01_hr_onboarding_en.docx": {
        "GIVENNAME": ["Jonathan", "Elena"], "SURNAME": ["Reyes"]},
    "sample_02_insurance_claim_az.docx": {
        "GIVENNAME": ["Vüqar"], "SURNAME": ["Səmədov"]},
    "sample_03_it_incident_en.docx": {
        "GIVENNAME": ["Mariya"], "SURNAME": ["Ivanova"]},
    "sample_04_rental_agreement_tr.docx": {
        "GIVENNAME": ["Elif", "Kamran"], "SURNAME": ["Yıldız", "Əliyev"]},
    "sample_05_bank_letter_ru.docx": {
        "GIVENNAME": ["Дмитрий"], "SURNAME": ["Соколов"]},
    "sample_06_medical_referral_en.docx": {
        "GIVENNAME": ["Margaret", "Amir"], "SURNAME": ["Foster", "Khalil"]},
    "sample_07_university_transcript_az.docx": {
        "GIVENNAME": ["Elvin", "Aygün"], "SURNAME": ["Məmmədov", "Əliyeva"]},
    "sample_08_utility_bill_tr.docx": {
        "GIVENNAME": ["Kerem"], "SURNAME": ["Yıldız"]},
    "sample_09_loan_application_ru.docx": {
        "GIVENNAME": ["Наталья", "Игорь"], "SURNAME": ["Волкова", "Соколов"]},
    "sample_10_travel_itinerary_en.docx": {
        "GIVENNAME": ["David"], "SURNAME": ["Okonkwo"]},
    "sample_11_employment_reference_az.docx": {
        "GIVENNAME": ["Nərmin", "Rauf"], "SURNAME": ["Hüseynova", "Bayramov"]},
}


def _in_email_token(text: str, start: int, end: int) -> bool:
    """True if [start,end) sits inside a single non-whitespace token that
    contains '@' -- i.e. the match is part of an email address's local or
    domain part ("jonathan.reyes@personal-mail.com" contains BOTH
    "jonathan" and "reyes" as substrings, with no name/surname word
    boundary the email pattern itself respects). Not a real ground-truth
    name mention: the whole email is already masked as one EMAIL span
    (`patterns.py`, checksum/shape-verified, 100% reliable per the
    baseline report), so the name text inside it is never exposed to a
    reader regardless of whether a GIVENNAME/SURNAME detector also fires
    on the substring. Excluded here so recall measures real prose
    mentions, matching the baseline report's own (manual) counting, which
    also did not count email-local-part occurrences.
    """
    i = start
    while i > 0 and not text[i - 1].isspace():
        i -= 1
    j = end
    while j < len(text) and not text[j].isspace():
        j += 1
    return "@" in text[i:j]


def find_mentions(text: str, value: str) -> list[tuple[int, int]]:
    pattern = re.compile(r"(?<!\w)" + re.escape(value) + r"(?!\w)",
                         re.UNICODE | re.IGNORECASE)
    return [(m.start(), m.end()) for m in pattern.finditer(text)
           if not _in_email_token(text, m.start(), m.end())]


def main() -> int:
    cfg = GuardConfig(ner_model="your-hf-org/masking-multilingual")

    per_sample = {}
    totals = {
        "az": {"GIVENNAME": [0, 0], "SURNAME": [0, 0]},
        "non_az": {"GIVENNAME": [0, 0], "SURNAME": [0, 0]},
    }
    missed_detail = []

    for fname, gt in GROUND_TRUTH.items():
        path = SAMPLES_DIR / fname
        assert path.exists(), f"missing sample: {path}"

        result = pg.sanitize_document(str(path), config=cfg)
        detections = result.detections

        # MaskResult.text is POST-mask; ground-truth mention offsets need
        # the original text. sanitize_document's `joined` text (what it
        # actually fed the detector, and what `detections[i].start/end`
        # are offsets into) is `SEGMENT_JOIN.join(s.text for s in
        # included)`; for DOCX, DEFAULT_EXCLUDED_SEGMENT_KINDS only
        # excludes "slide_notes" (a PPTX-only kind), so `included` ==
        # every segment and this equals ExtractedDocument.text exactly.
        from pii_guard.extract import docx as extract_docx
        doc_text = extract_docx.extract(str(path)).text

        bucket = "az" if fname in AZ_SAMPLES else "non_az"
        sample_result = {"GIVENNAME": {"found": 0, "total": 0, "missed": []},
                         "SURNAME": {"found": 0, "total": 0, "missed": []}}

        for label in ("GIVENNAME", "SURNAME"):
            for value in gt[label]:
                mentions = find_mentions(doc_text, value)
                if not mentions:
                    raise AssertionError(
                        f"{fname}: ground-truth value {value!r} not found "
                        f"in extracted text at all -- ground truth is wrong")
                for start, end in mentions:
                    covered = any(
                        d.label in ("GIVENNAME", "SURNAME")
                        and d.start < end and start < d.end
                        for d in detections
                    )
                    sample_result[label]["total"] += 1
                    totals[bucket][label][1] += 1
                    if covered:
                        sample_result[label]["found"] += 1
                        totals[bucket][label][0] += 1
                    else:
                        ctx_start = max(0, start - 20)
                        ctx_end = min(len(doc_text), end + 20)
                        sample_result[label]["missed"].append({
                            "value": value, "start": start, "end": end,
                            "context": doc_text[ctx_start:ctx_end],
                        })
                        missed_detail.append({
                            "sample": fname, "label": label, "value": value,
                            "context": doc_text[ctx_start:ctx_end],
                        })

        per_sample[fname] = sample_result
        print(f"{fname}: GIVENNAME {sample_result['GIVENNAME']['found']}/"
             f"{sample_result['GIVENNAME']['total']}  SURNAME "
             f"{sample_result['SURNAME']['found']}/{sample_result['SURNAME']['total']}")

    def pct(found, total):
        return f"{found}/{total} ({100 * found // total if total else 0}%)"

    az_g = totals["az"]["GIVENNAME"]
    az_s = totals["az"]["SURNAME"]
    na_g = totals["non_az"]["GIVENNAME"]
    na_s = totals["non_az"]["SURNAME"]
    all_found = az_g[0] + az_s[0] + na_g[0] + na_s[0]
    all_total = az_g[1] + az_s[1] + na_g[1] + na_s[1]

    print("\n=== SUMMARY ===")
    print(f"AZ       GIVENNAME {pct(*az_g)}  SURNAME {pct(*az_s)}")
    print(f"non-AZ   GIVENNAME {pct(*na_g)}  SURNAME {pct(*na_s)}")
    print(f"OVERALL  GIVENNAME {pct(az_g[0]+na_g[0], az_g[1]+na_g[1])}  "
         f"SURNAME {pct(az_s[0]+na_s[0], az_s[1]+na_s[1])}")
    print(f"COMBINED {all_found}/{all_total} "
         f"({100 * all_found // all_total}%)")

    print("\n=== MISSED MENTIONS ===")
    for m in missed_detail:
        print(f"  {m['sample']}: {m['label']} {m['value']!r}  context: ...{m['context']}...")

    out = {
        "per_sample": per_sample,
        "totals": {k: {kk: list(vv) for kk, vv in v.items()} for k, v in totals.items()},
        "missed": missed_detail,
        "combined_found": all_found,
        "combined_total": all_total,
    }
    (OUT_DIR / "recall_results.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\nwrote {OUT_DIR / 'recall_results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
