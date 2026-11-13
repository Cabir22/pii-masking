"""Generate the 200-document .docx test-fixture batch for DOCX format
testing (data/testing_samples/docx/), mirroring the existing txt/, excel/
and pdf/ batches under data/testing_samples/ on `excel-txt`.

Two halves, 100 documents each:

  corpus_<lang>_NNN.docx  -- one real record from the 200-doc Wahoo AZ batch
                             (`test_samples.jsonl`) or its EN/TR/RU
                             translations (`translate_input/<lang>_output.jsonl`),
                             inserted VERBATIM into a single Word paragraph
                             (line breaks preserved via `run.add_break()`, not
                             separate paragraphs, so the extracted text is
                             byte-identical to the source `text` field and the
                             source start/end offsets apply unchanged).

  new_<lang>_NNN.docx     -- freshly authored (5 document templates x 5
                             value-variations x 4 languages), no corpus text
                             reused. Every PII value is minted through
                             `piigen.values.ValueFactory` (checksum-valid
                             where applicable, blocklist-screened) -- never
                             invented inline. Gold spans are recorded via
                             `piigen.text.TextBuilder` at write time, never
                             recovered by re-searching the assembled text.

Source corpus is read from a checked-out `excel-txt` worktree (see
--source-dir); it is not copied into this branch. The manifest records
enough (source id, lang, entities, text) to make the docx batch itself
self-contained for downstream use.

Run: python scripts/gen_docx_test_samples.py --source-dir <path-to-excel-txt-worktree>
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import docx  # noqa: E402

from piigen.text import TextBuilder  # noqa: E402
from piigen.values import ValueFactory, ValuePool  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "testing_samples" / "docx"

LANGS = ["az", "en", "tr", "ru"]

# Labels whose only populated locale pack is `az` (see
# scripts/piigen/locales/{en,tr,ru}.py module docstrings: "the PII stays
# Azerbaijani and is spliced from the shared az pools" under the translation
# approach). Calling ValueFactory with the document's own lang for these
# raises (empty geography/phone/domain pools), so they're always minted with
# lang="az" regardless of the carrier document's language -- matching how
# the real corpus translations behave (see e.g. `Astara` staying a literal
# AZ city name inside translated EN carrier text).
AZ_ONLY_LABELS = {"IBAN", "URL", "EMAIL", "CITY", "STREET", "TELEPHONENUM", "ZIPCODE"}


def mint(vf: ValueFactory, label: str, lang: str, **kw) -> str:
    use_lang = "az" if label in AZ_ONLY_LABELS else lang
    return vf.make(label, use_lang, **kw)


# ---------------------------------------------------------------------------
# Offset-exact paragraph writer: preserves "\n" inside a single Word
# paragraph via soft line breaks, so `paragraph.text` round-trips exactly
# (verified empirically: python-docx >=1.1 reconstructs w:br as "\n" and
# w:tab as "\t" in `.text`).
# ---------------------------------------------------------------------------
def write_paragraph_text(paragraph, text: str) -> None:
    parts = text.split("\n")
    run = paragraph.add_run(parts[0])
    for part in parts[1:]:
        run.add_break()
        run = paragraph.add_run(part)


def new_doc(header: str, footer: str) -> docx.Document:
    d = docx.Document()
    d.sections[0].header.paragraphs[0].text = header
    d.sections[0].footer.paragraphs[0].text = footer
    return d


class DocBuilder:
    """Multiple TextBuilder-tracked Word paragraphs; the document's full
    text is defined as "\\n".join(paragraph texts), matching the join
    convention the verification script uses when re-extracting text."""

    def __init__(self, doc: docx.Document) -> None:
        self.doc = doc
        self._tbs: list[TextBuilder] = []

    def paragraph(self) -> TextBuilder:
        tb = TextBuilder()
        self._tbs.append(tb)
        return tb

    def finish(self) -> tuple[str, list[dict]]:
        full_parts = []
        spans: list[dict] = []
        offset = 0
        for tb in self._tbs:
            text, ents = tb.result()
            p = self.doc.add_paragraph()
            write_paragraph_text(p, text)
            full_parts.append(text)
            for e in ents:
                spans.append({"start": e["start"] + offset, "end": e["end"] + offset,
                              "label": e["label"], "text": e["text"]})
            offset += len(text) + 1  # "\n" join separator
        return "\n".join(full_parts), spans


# ---------------------------------------------------------------------------
# Deliverable 1: corpus-derived documents
# ---------------------------------------------------------------------------
def load_jsonl(path: Path) -> tuple[list[dict], int]:
    records, bad = [], 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                bad += 1
    return records, bad


def select_corpus_records(source_dir: Path, per_lang: int, seed: int) -> list[dict]:
    """Pull `per_lang` records per language from test_samples.jsonl (az) and
    translate_input/{en,tr,ru}_output.jsonl, tagging each with its source
    file and language. Skips zero-entity / malformed records (none found in
    this corpus as of 2026-09-16, but handled defensively)."""
    rng = random.Random(seed)
    pools: dict[str, tuple[list[dict], str]] = {}

    az_path = source_dir / "test_samples.jsonl"
    az_recs, az_bad = load_jsonl(az_path)
    if az_bad:
        print(f"  WARNING: {az_bad} malformed line(s) skipped in {az_path.name}")
    pools["az"] = (az_recs, "test_samples.jsonl")

    for lang in ("en", "tr", "ru"):
        p = source_dir / "translate_input" / f"{lang}_output.jsonl"
        recs, bad = load_jsonl(p)
        if bad:
            print(f"  WARNING: {bad} malformed line(s) skipped in {p.name}")
        pools[lang] = (recs, f"translate_input/{lang}_output.jsonl")

    selected: list[dict] = []
    for lang in LANGS:
        recs, source_name = pools[lang]
        usable = [r for r in recs if r.get("entities")]
        skipped_zero_ent = len(recs) - len(usable)
        if skipped_zero_ent:
            print(f"  {lang}: skipped {skipped_zero_ent} zero-entity record(s)")
        if len(usable) < per_lang:
            print(f"  WARNING: only {len(usable)} usable {lang} records "
                  f"(wanted {per_lang}); taking all of them")
        k = min(per_lang, len(usable))
        picks = rng.sample(usable, k)
        for rec in picks:
            selected.append({
                "id": rec["id"],
                "lang": lang,
                "text": rec["text"],
                "entities": [{"start": e["start"], "end": e["end"], "label": e["label"]}
                             for e in rec["entities"]],
                "source_file": source_name,
            })
    return selected


def build_corpus_docx(rec: dict, out_path: Path) -> None:
    d = new_doc(
        header="DOCX format-testing fixture -- corpus-derived (verbatim)",
        footer="Confidential -- internal use only. Do not forward externally.",
    )
    p = d.add_paragraph()
    write_paragraph_text(p, rec["text"])
    d.save(str(out_path))


# ---------------------------------------------------------------------------
# Deliverable 2: freshly generated documents
# ---------------------------------------------------------------------------
# Per-language carrier phrases. Every template function below is
# language-branched inline; phrases live next to their entity() calls so the
# offset bookkeeping is visibly correct at the call site.

def template_hr(vf: ValueFactory, lang: str, rng: random.Random):
    """HR onboarding memo. GIVENNAME, SURNAME, DATE, AGE, EMAIL,
    TELEPHONENUM, CITY, STREET, BUILDINGNUM, ZIPCODE, IBAN, AZ_FIN,
    AZ_ID_CARD_NUMBER."""
    female = rng.random() < 0.5
    given = mint(vf, "GIVENNAME", lang, female=female)
    surname = mint(vf, "SURNAME", lang, female=female)
    dob = vf.make("DATE", lang, min_year=1968, max_year=2004)
    age = mint(vf, "AGE", lang)
    email = mint(vf, "EMAIL", lang, first=given, last=surname, corporate=False)
    phone = mint(vf, "TELEPHONENUM", lang)
    city = mint(vf, "CITY", lang)
    street = mint(vf, "STREET", lang)
    buildingnum = mint(vf, "BUILDINGNUM", lang)
    zipcode = mint(vf, "ZIPCODE", lang)
    iban = mint(vf, "IBAN", lang)
    fin = mint(vf, "AZ_FIN", lang)
    idcard = mint(vf, "AZ_ID_CARD_NUMBER", lang)

    headers = {
        "az": ("Zirvə Logistika MMC -- İnsan Resursları", "HR-001"),
        "en": ("Acme Logistics LLC -- Human Resources", "HR-001"),
        "tr": ("Zirve Lojistik A.S. -- Insan Kaynaklari", "HR-001"),
        "ru": ('ООО «Зирве Логистика» -- Отдел кадров', "HR-001"),
    }[lang]
    d = new_doc(headers[0], "Confidential -- internal use only.")
    db = DocBuilder(d)

    tb = db.paragraph()
    if lang == "az":
        tb.write("Xoş gəlmisiniz! Bu memo ").entity("GIVENNAME", given).write(" ") \
          .entity("SURNAME", surname).write(f" -in işə qəbulu ilə bağlı təfərrüatları təsdiq edir. Doğum tarixi ") \
          .entity("DATE", dob).write(", hazırda ").entity("AGE", age).write(" yaşındadır. ") \
          .write("Şəxsi elektron poçt ünvanı ").entity("EMAIL", email).write(" və mobil nömrəsi ") \
          .entity("TELEPHONENUM", phone).write(" -dir.")
    elif lang == "en":
        tb.write("Welcome to the team! This memo confirms onboarding details for ") \
          .entity("GIVENNAME", given).write(" ").entity("SURNAME", surname) \
          .write(", whose date of birth is ").entity("DATE", dob) \
          .write(" and who is currently ").entity("AGE", age).write(" years old. ") \
          .write("Personal email is ").entity("EMAIL", email).write(" and mobile is ") \
          .entity("TELEPHONENUM", phone).write(".")
    elif lang == "tr":
        tb.write("Ekibe hos geldiniz! Bu yazi ").entity("GIVENNAME", given).write(" ") \
          .entity("SURNAME", surname).write(" adli calisanin ise alim bilgilerini onaylar. Dogum tarihi ") \
          .entity("DATE", dob).write(" olup, halen ").entity("AGE", age).write(" yasindadir. ") \
          .write("Kisisel e-posta adresi ").entity("EMAIL", email).write(", cep telefonu ") \
          .entity("TELEPHONENUM", phone).write(" seklindedir.")
    else:  # ru
        tb.write("Добро пожаловать в команду! Настоящая записка подтверждает данные о приёме на работу ") \
          .entity("GIVENNAME", given).write(" ").entity("SURNAME", surname) \
          .write(", дата рождения ").entity("DATE", dob).write(", возраст ") \
          .entity("AGE", age).write(" лет. Личная электронная почта ").entity("EMAIL", email) \
          .write(", мобильный телефон ").entity("TELEPHONENUM", phone).write(".")

    tb2 = db.paragraph()
    if lang == "az":
        tb2.write("Yaşayış ünvanı: ").entity("STREET", street).write(" ").entity("BUILDINGNUM", buildingnum) \
           .write(", ").entity("CITY", city).write(", ").entity("ZIPCODE", zipcode) \
           .write(". Əmək haqqı bu bank hesabına köçürüləcək: ").entity("IBAN", iban) \
           .write(". FİN kodu: ").entity("AZ_FIN", fin).write(", şəxsiyyət vəsiqəsi nömrəsi: ") \
           .entity("AZ_ID_CARD_NUMBER", idcard).write(".")
    elif lang == "en":
        tb2.write("Residential address: ").entity("STREET", street).write(" ").entity("BUILDINGNUM", buildingnum) \
           .write(", ").entity("CITY", city).write(", ").entity("ZIPCODE", zipcode) \
           .write(". Payroll will be set up against IBAN ").entity("IBAN", iban) \
           .write(". AZ FIN code: ").entity("AZ_FIN", fin).write(", national ID card number: ") \
           .entity("AZ_ID_CARD_NUMBER", idcard).write(".")
    elif lang == "tr":
        tb2.write("Ikamet adresi: ").entity("STREET", street).write(" ").entity("BUILDINGNUM", buildingnum) \
           .write(", ").entity("CITY", city).write(", ").entity("ZIPCODE", zipcode) \
           .write(". Maas odemesi su IBAN hesabina yapilacaktir: ").entity("IBAN", iban) \
           .write(". FIN kodu: ").entity("AZ_FIN", fin).write(", kimlik karti numarasi: ") \
           .entity("AZ_ID_CARD_NUMBER", idcard).write(".")
    else:  # ru
        tb2.write("Адрес проживания: ").entity("STREET", street).write(" ").entity("BUILDINGNUM", buildingnum) \
           .write(", ").entity("CITY", city).write(", ").entity("ZIPCODE", zipcode) \
           .write(". Зарплата будет начисляться на счёт IBAN ").entity("IBAN", iban) \
           .write(". Код ФИН: ").entity("AZ_FIN", fin).write(", номер удостоверения личности: ") \
           .entity("AZ_ID_CARD_NUMBER", idcard).write(".")

    full_text, spans = db.finish()
    return d, full_text, spans  # type: ignore[return-value]


def template_id_verify(vf: ValueFactory, lang: str, rng: random.Random):
    """Travel / ID verification form. GIVENNAME, SURNAME, DATE, TIME,
    AZ_PASSPORT_NUMBER, AZ_DRIVER_LICENSE_NUMBER, TELEPHONENUM, EMAIL,
    CITY, AZ_VOEN, AGE."""
    female = rng.random() < 0.5
    given = mint(vf, "GIVENNAME", lang, female=female)
    surname = mint(vf, "SURNAME", lang, female=female)
    dob = vf.make("DATE", lang, min_year=1965, max_year=2005)
    arrival_time = mint(vf, "TIME", lang)
    passport = mint(vf, "AZ_PASSPORT_NUMBER", lang)
    license_ = mint(vf, "AZ_DRIVER_LICENSE_NUMBER", lang)
    phone = mint(vf, "TELEPHONENUM", lang)
    email = mint(vf, "EMAIL", lang, first=given, last=surname, corporate=False)
    city = mint(vf, "CITY", lang)
    voen = mint(vf, "AZ_VOEN", lang)
    age = mint(vf, "AGE", lang)

    headers = {
        "az": "Sərhəd Nəzarəti -- Şəxsiyyət Təsdiqi Formu",
        "en": "Border Control -- Identity Verification Form",
        "tr": "Sinir Kontrolu -- Kimlik Dogrulama Formu",
        "ru": "Пограничный контроль -- Форма проверки личности",
    }[lang]
    d = new_doc(headers, "Confidential -- internal use only.")
    db = DocBuilder(d)

    tb = db.paragraph()
    if lang == "az":
        tb.write("Müraciətçi: ").entity("GIVENNAME", given).write(" ").entity("SURNAME", surname) \
          .write(", doğum tarixi ").entity("DATE", dob).write(", ").entity("AGE", age).write(" yaşında. ") \
          .write("Beynəlxalq pasport nömrəsi ").entity("AZ_PASSPORT_NUMBER", passport) \
          .write(", sürücülük vəsiqəsi ").entity("AZ_DRIVER_LICENSE_NUMBER", license_).write(".")
    elif lang == "en":
        tb.write("Applicant: ").entity("GIVENNAME", given).write(" ").entity("SURNAME", surname) \
          .write(", date of birth ").entity("DATE", dob).write(", age ").entity("AGE", age).write(". ") \
          .write("International passport number ").entity("AZ_PASSPORT_NUMBER", passport) \
          .write(", driver's licence ").entity("AZ_DRIVER_LICENSE_NUMBER", license_).write(".")
    elif lang == "tr":
        tb.write("Basvuru sahibi: ").entity("GIVENNAME", given).write(" ").entity("SURNAME", surname) \
          .write(", dogum tarihi ").entity("DATE", dob).write(", yas ").entity("AGE", age).write(". ") \
          .write("Pasaport numarasi ").entity("AZ_PASSPORT_NUMBER", passport) \
          .write(", surucu belgesi ").entity("AZ_DRIVER_LICENSE_NUMBER", license_).write(".")
    else:  # ru
        tb.write("Заявитель: ").entity("GIVENNAME", given).write(" ").entity("SURNAME", surname) \
          .write(", дата рождения ").entity("DATE", dob).write(", возраст ").entity("AGE", age).write(". ") \
          .write("Номер загранпаспорта ").entity("AZ_PASSPORT_NUMBER", passport) \
          .write(", водительское удостоверение ").entity("AZ_DRIVER_LICENSE_NUMBER", license_).write(".")

    tb2 = db.paragraph()
    if lang == "az":
        tb2.write("Gəliş vaxtı: ").entity("TIME", arrival_time).write(", giriş şəhəri: ").entity("CITY", city) \
           .write(". Əlaqə telefonu ").entity("TELEPHONENUM", phone).write(", e-poçt ").entity("EMAIL", email) \
           .write(". İşəgötürənin VÖEN-i (təsdiq üçün): ").entity("AZ_VOEN", voen).write(".")
    elif lang == "en":
        tb2.write("Arrival time: ").entity("TIME", arrival_time).write(", entry city: ").entity("CITY", city) \
           .write(". Contact phone ").entity("TELEPHONENUM", phone).write(", email ").entity("EMAIL", email) \
           .write(". Employer VOEN (for verification): ").entity("AZ_VOEN", voen).write(".")
    elif lang == "tr":
        tb2.write("Varis saati: ").entity("TIME", arrival_time).write(", giris sehri: ").entity("CITY", city) \
           .write(". Iletisim telefonu ").entity("TELEPHONENUM", phone).write(", e-posta ").entity("EMAIL", email) \
           .write(". Isveren VOEN numarasi (dogrulama icin): ").entity("AZ_VOEN", voen).write(".")
    else:  # ru
        tb2.write("Время прибытия: ").entity("TIME", arrival_time).write(", город въезда: ").entity("CITY", city) \
           .write(". Контактный телефон ").entity("TELEPHONENUM", phone).write(", эл. почта ").entity("EMAIL", email) \
           .write(". VOEN работодателя (для проверки): ").entity("AZ_VOEN", voen).write(".")

    full_text, spans = db.finish()
    return d, full_text, spans


def template_banking(vf: ValueFactory, lang: str, rng: random.Random):
    """Loan application letter. GIVENNAME, SURNAME, PAYMENT_CARD_NUMBER,
    CARD_SECURITY_CODE, IBAN, AZ_VOEN, EMAIL, TELEPHONENUM, CITY, STREET,
    BUILDINGNUM, DATE."""
    female = rng.random() < 0.5
    given = mint(vf, "GIVENNAME", lang, female=female)
    surname = mint(vf, "SURNAME", lang, female=female)
    card = mint(vf, "PAYMENT_CARD_NUMBER", lang)
    cvv = mint(vf, "CARD_SECURITY_CODE", lang)
    iban = mint(vf, "IBAN", lang)
    voen = mint(vf, "AZ_VOEN", lang)
    email = mint(vf, "EMAIL", lang, first=given, last=surname, corporate=False)
    phone = mint(vf, "TELEPHONENUM", lang)
    city = mint(vf, "CITY", lang)
    street = mint(vf, "STREET", lang)
    buildingnum = mint(vf, "BUILDINGNUM", lang)
    app_date = vf.make("DATE", lang, min_year=2025, max_year=2026)

    headers = {
        "az": "BakuBank ASC -- Kredit Ərizəsi",
        "en": "BakuBank JSC -- Loan Application",
        "tr": "BakuBank A.S. -- Kredi Basvurusu",
        "ru": "АО «БакуБанк» -- Заявка на кредит",
    }[lang]
    d = new_doc(headers, "Confidential -- internal use only.")
    db = DocBuilder(d)

    tb = db.paragraph()
    if lang == "az":
        tb.write("Ərizəçi ").entity("GIVENNAME", given).write(" ").entity("SURNAME", surname) \
          .write(", müraciət tarixi: ").entity("DATE", app_date) \
          .write(". Mövcud kart: ").entity("PAYMENT_CARD_NUMBER", card).write(", təhlükəsizlik kodu ") \
          .entity("CARD_SECURITY_CODE", cvv).write(". Kredit ödənişi üçün bank hesabı: ") \
          .entity("IBAN", iban).write(".")
    elif lang == "en":
        tb.write("Applicant ").entity("GIVENNAME", given).write(" ").entity("SURNAME", surname) \
          .write(", application date: ").entity("DATE", app_date) \
          .write(". Existing card on file: ").entity("PAYMENT_CARD_NUMBER", card) \
          .write(", security code ").entity("CARD_SECURITY_CODE", cvv) \
          .write(". Disbursement account (IBAN): ").entity("IBAN", iban).write(".")
    elif lang == "tr":
        tb.write("Basvuru sahibi ").entity("GIVENNAME", given).write(" ").entity("SURNAME", surname) \
          .write(", basvuru tarihi: ").entity("DATE", app_date) \
          .write(". Kayitli kart: ").entity("PAYMENT_CARD_NUMBER", card) \
          .write(", guvenlik kodu ").entity("CARD_SECURITY_CODE", cvv) \
          .write(". Odeme hesabi (IBAN): ").entity("IBAN", iban).write(".")
    else:  # ru
        tb.write("Заявитель ").entity("GIVENNAME", given).write(" ").entity("SURNAME", surname) \
          .write(", дата подачи заявки: ").entity("DATE", app_date) \
          .write(". Карта в деле: ").entity("PAYMENT_CARD_NUMBER", card) \
          .write(", код безопасности ").entity("CARD_SECURITY_CODE", cvv) \
          .write(". Счёт для выплаты (IBAN): ").entity("IBAN", iban).write(".")

    tb2 = db.paragraph()
    if lang == "az":
        tb2.write("VÖEN: ").entity("AZ_VOEN", voen).write(". Əlaqə: ").entity("EMAIL", email) \
           .write(", ").entity("TELEPHONENUM", phone).write(". Ünvan: ").entity("STREET", street) \
           .write(" ").entity("BUILDINGNUM", buildingnum).write(", ").entity("CITY", city).write(".")
    elif lang == "en":
        tb2.write("VOEN: ").entity("AZ_VOEN", voen).write(". Contact: ").entity("EMAIL", email) \
           .write(", ").entity("TELEPHONENUM", phone).write(". Address: ").entity("STREET", street) \
           .write(" ").entity("BUILDINGNUM", buildingnum).write(", ").entity("CITY", city).write(".")
    elif lang == "tr":
        tb2.write("VOEN: ").entity("AZ_VOEN", voen).write(". Iletisim: ").entity("EMAIL", email) \
           .write(", ").entity("TELEPHONENUM", phone).write(". Adres: ").entity("STREET", street) \
           .write(" ").entity("BUILDINGNUM", buildingnum).write(", ").entity("CITY", city).write(".")
    else:  # ru
        tb2.write("ИНН/VOEN: ").entity("AZ_VOEN", voen).write(". Контакты: ").entity("EMAIL", email) \
           .write(", ").entity("TELEPHONENUM", phone).write(". Адрес: ").entity("STREET", street) \
           .write(" ").entity("BUILDINGNUM", buildingnum).write(", ").entity("CITY", city).write(".")

    full_text, spans = db.finish()
    return d, full_text, spans


def template_it_incident(vf: ValueFactory, lang: str, rng: random.Random):
    """IT/security incident report. EMAIL, TELEPHONENUM, IPV4_ADDRESS,
    IPV6_ADDRESS, MAC_ADDRESS, API_KEY, ACCESS_TOKEN, PRIVATE_KEY, ICCID,
    URL, GIVENNAME, SURNAME, TIME, DATE."""
    female = rng.random() < 0.5
    given = mint(vf, "GIVENNAME", lang, female=female)
    surname = mint(vf, "SURNAME", lang, female=female)
    email = mint(vf, "EMAIL", lang, first=given, last=surname, corporate=True)
    phone = mint(vf, "TELEPHONENUM", lang)
    ipv4 = mint(vf, "IPV4_ADDRESS", lang)
    ipv6 = mint(vf, "IPV6_ADDRESS", lang)
    mac = mint(vf, "MAC_ADDRESS", lang)
    api_key = mint(vf, "API_KEY", lang)
    access_token = mint(vf, "ACCESS_TOKEN", lang)
    private_key = mint(vf, "PRIVATE_KEY", lang)
    iccid = mint(vf, "ICCID", lang)
    url = mint(vf, "URL", lang)
    inc_time = mint(vf, "TIME", lang)
    inc_date = vf.make("DATE", lang, min_year=2025, max_year=2026)

    headers = {
        "az": "Daxili İT Təhlükəsizlik -- Hadisə Hesabatı",
        "en": "Internal IT Security -- Incident Report",
        "tr": "Ic BT Guvenligi -- Olay Raporu",
        "ru": "Внутренняя ИТ-безопасность -- Отчёт об инциденте",
    }[lang]
    d = new_doc(headers, "Confidential -- internal use only.")
    db = DocBuilder(d)

    tb = db.paragraph()
    if lang == "az":
        tb.write("Hadisə ").entity("DATE", inc_date).write(" tarixində, saat ").entity("TIME", inc_time) \
          .write(" aşkarlandı. Bildirən: ").entity("GIVENNAME", given).write(" ").entity("SURNAME", surname) \
          .write(" (").entity("EMAIL", email).write(", ").entity("TELEPHONENUM", phone).write("). ") \
          .write("Şübhəli giriş IP ünvanından ").entity("IPV4_ADDRESS", ipv4).write(" və ") \
          .entity("IPV6_ADDRESS", ipv6).write(" ünvanından baş verib, MAC ünvanı ").entity("MAC_ADDRESS", mac).write(".")
    elif lang == "en":
        tb.write("The incident was detected on ").entity("DATE", inc_date).write(" at ").entity("TIME", inc_time) \
          .write(". Reported by: ").entity("GIVENNAME", given).write(" ").entity("SURNAME", surname) \
          .write(" (").entity("EMAIL", email).write(", ").entity("TELEPHONENUM", phone).write("). ") \
          .write("The suspicious session originated from ").entity("IPV4_ADDRESS", ipv4).write(" and later from ") \
          .entity("IPV6_ADDRESS", ipv6).write(", MAC address ").entity("MAC_ADDRESS", mac).write(".")
    elif lang == "tr":
        tb.write("Olay ").entity("DATE", inc_date).write(" tarihinde, saat ").entity("TIME", inc_time) \
          .write(" tespit edildi. Bildiren: ").entity("GIVENNAME", given).write(" ").entity("SURNAME", surname) \
          .write(" (").entity("EMAIL", email).write(", ").entity("TELEPHONENUM", phone).write("). ") \
          .write("Supheli oturum ").entity("IPV4_ADDRESS", ipv4).write(" adresinden, daha sonra ") \
          .entity("IPV6_ADDRESS", ipv6).write(" adresinden basladi, MAC adresi ").entity("MAC_ADDRESS", mac).write(".")
    else:  # ru
        tb.write("Инцидент обнаружен ").entity("DATE", inc_date).write(" в ").entity("TIME", inc_time) \
          .write(". Сообщил: ").entity("GIVENNAME", given).write(" ").entity("SURNAME", surname) \
          .write(" (").entity("EMAIL", email).write(", ").entity("TELEPHONENUM", phone).write("). ") \
          .write("Подозрительная сессия началась с адреса ").entity("IPV4_ADDRESS", ipv4).write(", затем с ") \
          .entity("IPV6_ADDRESS", ipv6).write(", MAC-адрес ").entity("MAC_ADDRESS", mac).write(".")

    tb2 = db.paragraph()
    if lang == "az":
        tb2.write("Sızmış API açarı: ").entity("API_KEY", api_key).write(". Əlaqəli giriş tokeni: ") \
           .entity("ACCESS_TOKEN", access_token).write(". Log faylında aşkarlanan açar fraqmenti:\n") \
           .entity("PRIVATE_KEY", private_key).write("\nNəzarətdə olan SIM ICCID: ").entity("ICCID", iccid) \
           .write(". Sıfırlama linki: ").entity("URL", url).write(".")
    elif lang == "en":
        tb2.write("The exposed API key was ").entity("API_KEY", api_key).write(". The associated access token: ") \
           .entity("ACCESS_TOKEN", access_token).write(". A private key fragment found in the log file:\n") \
           .entity("PRIVATE_KEY", private_key).write("\nMonitored SIM ICCID: ").entity("ICCID", iccid) \
           .write(". Password reset link: ").entity("URL", url).write(".")
    elif lang == "tr":
        tb2.write("Ifsa edilen API anahtari: ").entity("API_KEY", api_key).write(". Iliskili erisim jetonu: ") \
           .entity("ACCESS_TOKEN", access_token).write(". Log dosyasinda bulunan anahtar parcasi:\n") \
           .entity("PRIVATE_KEY", private_key).write("\nIzlenen SIM ICCID: ").entity("ICCID", iccid) \
           .write(". Sifirlama baglantisi: ").entity("URL", url).write(".")
    else:  # ru
        tb2.write("Скомпрометированный API-ключ: ").entity("API_KEY", api_key).write(". Связанный токен доступа: ") \
           .entity("ACCESS_TOKEN", access_token).write(". Фрагмент приватного ключа, найденный в логе:\n") \
           .entity("PRIVATE_KEY", private_key).write("\nОтслеживаемый ICCID SIM-карты: ").entity("ICCID", iccid) \
           .write(". Ссылка для сброса пароля: ").entity("URL", url).write(".")

    full_text, spans = db.finish()
    return d, full_text, spans


def template_delivery(vf: ValueFactory, lang: str, rng: random.Random):
    """Delivery / shipping note. GIVENNAME, SURNAME, STREET, BUILDINGNUM,
    CITY, ZIPCODE, TELEPHONENUM, DATE, TIME, AGE, URL."""
    female = rng.random() < 0.5
    given = mint(vf, "GIVENNAME", lang, female=female)
    surname = mint(vf, "SURNAME", lang, female=female)
    street = mint(vf, "STREET", lang)
    buildingnum = mint(vf, "BUILDINGNUM", lang)
    city = mint(vf, "CITY", lang)
    zipcode = mint(vf, "ZIPCODE", lang)
    phone = mint(vf, "TELEPHONENUM", lang)
    ship_date = vf.make("DATE", lang, min_year=2025, max_year=2026)
    ship_time = mint(vf, "TIME", lang)
    age = mint(vf, "AGE", lang)
    track_url = mint(vf, "URL", lang)

    headers = {
        "az": "SkyBridge Kuryer -- Çatdırılma Qeydi",
        "en": "SkyBridge Courier -- Delivery Note",
        "tr": "SkyBridge Kurye -- Teslimat Fisi",
        "ru": "SkyBridge Курьер -- Накладная",
    }[lang]
    d = new_doc(headers, "Confidential -- internal use only.")
    db = DocBuilder(d)

    tb = db.paragraph()
    if lang == "az":
        tb.write("Qəbul edən: ").entity("GIVENNAME", given).write(" ").entity("SURNAME", surname) \
          .write(" (").entity("AGE", age).write(" yaş). Çatdırılma ünvanı: ").entity("STREET", street) \
          .write(" ").entity("BUILDINGNUM", buildingnum).write(", ").entity("CITY", city) \
          .write(", ").entity("ZIPCODE", zipcode).write(".")
    elif lang == "en":
        tb.write("Recipient: ").entity("GIVENNAME", given).write(" ").entity("SURNAME", surname) \
          .write(" (age ").entity("AGE", age).write("). Delivery address: ").entity("STREET", street) \
          .write(" ").entity("BUILDINGNUM", buildingnum).write(", ").entity("CITY", city) \
          .write(", ").entity("ZIPCODE", zipcode).write(".")
    elif lang == "tr":
        tb.write("Alici: ").entity("GIVENNAME", given).write(" ").entity("SURNAME", surname) \
          .write(" (yas ").entity("AGE", age).write("). Teslimat adresi: ").entity("STREET", street) \
          .write(" ").entity("BUILDINGNUM", buildingnum).write(", ").entity("CITY", city) \
          .write(", ").entity("ZIPCODE", zipcode).write(".")
    else:  # ru
        tb.write("Получатель: ").entity("GIVENNAME", given).write(" ").entity("SURNAME", surname) \
          .write(" (возраст ").entity("AGE", age).write("). Адрес доставки: ").entity("STREET", street) \
          .write(" ").entity("BUILDINGNUM", buildingnum).write(", ").entity("CITY", city) \
          .write(", ").entity("ZIPCODE", zipcode).write(".")

    tb2 = db.paragraph()
    if lang == "az":
        tb2.write("Planlaşdırılan çatdırılma: ").entity("DATE", ship_date).write(", saat ") \
           .entity("TIME", ship_time).write(". Əlaqə nömrəsi: ").entity("TELEPHONENUM", phone) \
           .write(". İzləmə linki: ").entity("URL", track_url).write(".")
    elif lang == "en":
        tb2.write("Scheduled delivery: ").entity("DATE", ship_date).write(" at ") \
           .entity("TIME", ship_time).write(". Contact number: ").entity("TELEPHONENUM", phone) \
           .write(". Tracking link: ").entity("URL", track_url).write(".")
    elif lang == "tr":
        tb2.write("Planlanan teslimat: ").entity("DATE", ship_date).write(" saat ") \
           .entity("TIME", ship_time).write(". Iletisim numarasi: ").entity("TELEPHONENUM", phone) \
           .write(". Takip baglantisi: ").entity("URL", track_url).write(".")
    else:  # ru
        tb2.write("Плановая доставка: ").entity("DATE", ship_date).write(" в ") \
           .entity("TIME", ship_time).write(". Контактный номер: ").entity("TELEPHONENUM", phone) \
           .write(". Ссылка для отслеживания: ").entity("URL", track_url).write(".")

    full_text, spans = db.finish()
    return d, full_text, spans


TEMPLATES = [
    ("hr_onboarding", template_hr),
    ("id_verification", template_id_verify),
    ("loan_application", template_banking),
    ("it_incident", template_it_incident),
    ("delivery_note", template_delivery),
]


def build_generated_batch(per_lang: int, seed: int) -> list[dict]:
    """5 templates x (per_lang // 5) variations x 4 languages."""
    assert per_lang % len(TEMPLATES) == 0, "per_lang must divide evenly by template count"
    variations = per_lang // len(TEMPLATES)
    rng = random.Random(seed)
    pool = ValuePool()
    vf = ValueFactory(rng, pool)

    out = []
    for lang in LANGS:
        n = 0
        for doc_type, fn in TEMPLATES:
            for variation in range(variations):
                n += 1
                doc, full_text, spans = fn(vf, lang, rng)
                out.append({
                    "lang": lang,
                    "doc_type": doc_type,
                    "variation": variation,
                    "index": n,
                    "doc": doc,
                    "text": full_text,
                    "entities": spans,
                })
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dir", type=Path, required=True,
                     help="Path to a checked-out excel-txt worktree's data/testing_samples/")
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--per-lang-corpus", type=int, default=25)
    ap.add_argument("--per-lang-generated", type=int, default=25)
    ap.add_argument("--seed", type=int, default=1337)
    args = ap.parse_args()

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = []

    print("== Deliverable 1: corpus-derived ==")
    corpus_recs = select_corpus_records(args.source_dir, args.per_lang_corpus, args.seed)
    by_lang_count: dict[str, int] = {}
    for rec in corpus_recs:
        lang = rec["lang"]
        by_lang_count[lang] = by_lang_count.get(lang, 0) + 1
        idx = by_lang_count[lang]
        fname = f"corpus_{lang}_{idx:03d}.docx"
        out_path = out_dir / fname
        build_corpus_docx(rec, out_path)
        manifest.append({
            "filename": fname,
            "bucket": "corpus_derived",
            "source_id": rec["id"],
            "lang": rec["lang"],
            "source": rec["source_file"],
            "text": rec["text"],
            "entities": rec["entities"],
        })
    print(f"  wrote {len(corpus_recs)} files: {by_lang_count}")

    print("== Deliverable 2: freshly generated ==")
    gen_recs = build_generated_batch(args.per_lang_generated, args.seed + 1)
    by_lang_count2: dict[str, int] = {}
    for rec in gen_recs:
        lang = rec["lang"]
        by_lang_count2[lang] = by_lang_count2.get(lang, 0) + 1
        idx = by_lang_count2[lang]
        fname = f"new_{lang}_{idx:03d}.docx"
        out_path = out_dir / fname
        rec["doc"].save(str(out_path))
        manifest.append({
            "filename": fname,
            "bucket": "generated",
            "source_id": None,
            "lang": rec["lang"],
            "source": "generated",
            "doc_type": rec["doc_type"],
            "text": rec["text"],
            "entities": rec["entities"],
        })
    print(f"  wrote {len(gen_recs)} files: {by_lang_count2}")

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nmanifest: {manifest_path} ({len(manifest)} entries)")

    lang_totals: dict[str, int] = {}
    for m in manifest:
        lang_totals[m["lang"]] = lang_totals.get(m["lang"], 0) + 1
    print(f"total files: {len(manifest)}  per-language totals: {lang_totals}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
