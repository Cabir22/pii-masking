"""Generate sample DOCX/PPTX files loaded with PII, for manually testing
detection (this package's own, or the real checkpoint via
model/predict.py) against realistic documents.

Not part of the shipped service -- a dev/testing tool. Output goes to
`scratch/pii_test_samples/` (gitignored, regenerable, never a source
artifact -- same convention the rest of the repo uses for scratch output).

Every value here is synthetic (fake names/numbers built for this script,
not real people), matching this whole project's synthetic-data philosophy.
Card numbers pass Luhn and IBANs pass the real mod-97 check (via
`piigen.checksums.iban_check_digits`, the same function the corpus
generator uses to mint values) so pattern-tier detectors that verify
structure, not just shape, actually fire on them. AZ_FIN/AZ_ID_CARD/
AZ_PASSPORT/AZ_DRIVER_LICENSE follow their real format (piigen.checksums'
own regexes) for the same reason.

Deliberately multilingual (AZ/EN/RU/TR) across the 16 documents, and
deliberately includes non-PII content that LOOKS PII-shaped (an invoice
date, a section number, an ordinary meeting time) so a tester can check the
"don't over-mask ordinary information" behavior, not just recall.

Documents 06-11 (added when `sanitize_document_to_docx`'s embedded-image
OCR path was built) extend the original 5 with more document types/
densities and, deliberately, embedded images carrying PII -- none of the
original 5 contain an image at all, which meant the OCR/redaction path had
no fixture in this generator to exercise it against.

Every PERSON name across the 5 PPTX documents is a real, pool-backed Azerbaijani
name (`piigen.locales.az.FIRST_M`/`FIRST_F`/`SURNAME_STEMS`), regardless of
which language the surrounding slide prose is in -- for the RU document,
transliterated into Cyrillic via `piigen.locales.ru.transliterate`, the
same function the actual training corpus uses. This is not a stylistic
choice: per `piigen.locales.tr`'s own module docstring, this project's
translation approach keeps PII Azerbaijani and only translates the
carrier language, so the currently-trained checkpoint
(`your-hf-org/masking-multilingual`) was trained on Azerbaijani names only,
across those 4 carrier languages. An earlier version of this file used
non-Azerbaijani names (Samantha Cole, Jennifer Park, David Okafor, Emre
Şahin, Anna Kuznetsova) -- realistic-sounding, but not representative of
what that checkpoint was actually trained to recognise, which understated
its real recall when tested against these samples.

Run: python scripts/pii_guard/gen_test_docs.py [output_dir]
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import docx
import pptx
from docx.shared import Pt
from piigen.checksums import iban_check_digits
from pptx.util import Inches

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else (
    Path(__file__).resolve().parents[2] / "scratch" / "pii_test_samples")


# --------------------------------------------------------------------------
# synthetic-but-valid value builders
# --------------------------------------------------------------------------
def luhn_card(prefix: str, fill: str) -> str:
    digits = [int(c) for c in (prefix + fill)]
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    check = (10 - total % 10) % 10
    number = digits + [check]
    s = "".join(map(str, number))
    return " ".join(s[i:i + 4] for i in range(0, len(s), 4))


def az_iban(bban: str) -> str:
    check = iban_check_digits("AZ", bban)
    return f"AZ{check}{bban}"


# Prefix+fill length must equal (real brand length - 1 check digit), and
# the prefix must be a real issuer range (piigen.checksums.CARD_SPECS) --
# the first version of this got the arithmetic wrong (prefix+fill summed to
# 16 digits, +1 check = 17, which is not a real card length for ANY brand),
# so `credit_card_valid` correctly rejected every generated card number and
# PAYMENT_CARD_NUMBER never fired at all; the 4-digit space-separated
# groups fell through to the CARD_SECURITY_CODE (CVV) anchor detector
# instead, which is what a shape-only detector is SUPPOSED to do with an
# unverifiable digit run. Found by testing detection against these exact
# generated documents, not by inspection -- the whole reason "test with
# real documents" surfaces bugs a single-sentence example does not.
CARD_1 = luhn_card("4", "53201511283036")         # Visa, 16 digits total
CARD_2 = luhn_card("55", "1673490218477")         # Mastercard, 16 digits
CARD_3 = luhn_card("6011", "67349021847")         # Discover, 16 digits
ICCID = luhn_card("89", "94023456789012345")      # 20 digits, Luhn-checked

IBAN_1 = az_iban("NABZ00000000137010001944")     # 4-letter bank code + 20 alnum
IBAN_2 = az_iban("ABBZ36040000000004472944")
IBAN_3 = az_iban("PAHA01000000000001234567")
IBAN_4 = az_iban("NABZ00000000137410001944")

CARD_3 = luhn_card("4", "16988012234776")         # Visa, 16 digits -- for the image sample


# --------------------------------------------------------------------------
# DOCX generator
# --------------------------------------------------------------------------
def _docx_doc(title_footer: str) -> docx.Document:
    d = docx.Document()
    d.sections[0].header.paragraphs[0].text = title_footer
    d.sections[0].footer.paragraphs[0].text = (
        "Confidential -- internal use only. Do not forward externally.")
    return d


def _table(d, headers: list[str], rows: list[list[str]]):
    t = d.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1" if "Light Grid Accent 1" in [
        s.name for s in d.styles] else None
    for c, h in enumerate(headers):
        t.rows[0].cells[c].text = h
    for row in rows:
        cells = t.add_row().cells
        for c, val in enumerate(row):
            cells[c].text = val


def _card_image(title: str, fields: list[tuple[str, str]]) -> bytes:
    """A simple ID-card/badge-style raster image with printed text fields
    -- stands in for a scanned ID, staff badge or screenshot embedded in a
    real-world document, exercising `ocr.py` + `sanitize_document_to_docx`'s
    embedded-image redaction path."""
    from PIL import Image, ImageDraw, ImageFont

    size = (640, 80 + 56 * len(fields))
    img = Image.new("RGB", size, (250, 250, 248))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, size[0] - 1, size[1] - 1], outline=(40, 40, 40), width=3)
    d.rectangle([0, 0, size[0] - 1, 56], fill=(30, 60, 110))

    def _font(px):
        for path in ("/System/Library/Fonts/Supplemental/Arial.ttf",
                    "/System/Library/Fonts/Helvetica.ttc"):
            try:
                return ImageFont.truetype(path, px)
            except Exception:
                continue
        return ImageFont.load_default()

    d.text((16, 14), title, fill="white", font=_font(24))
    y = 80
    for label, value in fields:
        d.text((24, y), f"{label}:", fill=(90, 90, 90), font=_font(16))
        d.text((24, y + 20), value, fill=(15, 15, 15), font=_font(20))
        y += 56

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _add_image(d, png_bytes: bytes, width_inches: float = 4.5) -> None:
    from docx.shared import Inches

    d.add_picture(io.BytesIO(png_bytes), width=Inches(width_inches))


def make_docx_01_hr_onboarding() -> docx.Document:
    """English -- HR onboarding memo. Body prose + a table + header/footer."""
    d = _docx_doc("Acme Logistics MMC -- Human Resources")
    d.add_paragraph(
        "Welcome to the team! This memo confirms the onboarding details for "
        "Jonathan Reyes, who joins the Baku office as Senior Logistics "
        "Analyst effective this month. Jonathan's date of birth is "
        "1994-03-12 and he is 32 years old. His personal email is "
        "jonathan.reyes@personal-mail.com and his mobile is "
        "+994 55 213 47 89.")
    d.add_paragraph(
        "Jonathan currently resides at 47 Nizami Street, Apartment 12, "
        "Baku, postal code AZ1000. Payroll has been set up against IBAN "
        f"{IBAN_1} at Bank of Baku. His national ID card number is "
        "AA3456789 and his AZ FIN code is 7A9K3M1.")
    d.add_paragraph(
        "In case of emergency, please contact his spouse, Elena Reyes, at "
        "+994 70 998 12 34. Note: the invoice date on his relocation "
        "expense claim (Invoice date: 2026-03-01) has already been "
        "processed by Accounts Payable -- no action needed on that item.")
    d.add_paragraph(
        "Section 4 of the employee handbook covers benefits enrollment; "
        "he must complete this within 30 days.")
    _table(d, ["Field", "Value"], [
        ["Employee phone", "+994 55 213 47 89"],
        ["Company VOEN (Acme Logistics MMC)", "1234567890"],
        ["Emergency contact", "Elena Reyes, +994 70 998 12 34"],
        ["Driver's license (for company vehicle use)", "AZ482913"],
    ])
    return d


def make_docx_02_insurance_claim_az() -> docx.Document:
    """Azerbaijani -- insurance claim form."""
    d = _docx_doc("AzSığorta ASC -- Zərər üzrə ərizə")
    d.add_paragraph(
        "Ərizəçi: Vüqar Səmədov. Doğum tarixi 1988-07-22, hazırda 38 "
        "yaşındadır. Əlaqə nömrəsi +994 50 667 21 09, elektron poçt "
        "vuqar.samedov@mail.az. Yaşayış ünvanı: Neftçilər prospekti 145, "
        "mənzil 8, Bakı, AZ1010.")
    d.add_paragraph(
        f"Şəxsiyyət vəsiqəsi nömrəsi AB1928374, FIN kodu 9C2X7B4. "
        f"Sığorta ödənişi üçün bank hesabı: {IBAN_2}. Hadisə tarixi: "
        "2026-02-14 saat 17:40-da baş vermişdir.")
    d.add_paragraph(
        "Qeyd: müraciət 3-cü bölmədə göstərilən standart prosedura uyğun "
        "qeydə alınmışdır. Cavab müddəti 2026-09-01 tarixinədək davam edir "
        "(bu, sadəcə inzibati son tarixdir, şəxsi məlumat deyil).")
    _table(d, ["Sahə", "Dəyər"], [
        ["Telefon", "+994 50 667 21 09"],
        ["VÖEN (sığorta şirkəti)", "9876543210"],
        ["Bank hesabı", IBAN_2],
        ["Pasport nömrəsi", "C87654321"],
    ])
    return d


def make_docx_03_it_incident() -> docx.Document:
    """English/mixed -- IT security incident report. Heavy on credential/
    network labels, plus deliberate non-PII (ticket #, log timestamp)."""
    d = _docx_doc("Internal IT Security -- Incident Report #4471")
    d.add_paragraph(
        "Ticket #4471 was opened after unusual login activity was detected "
        "for the account of customer Mariya Ivanova "
        "(mariya.ivanova@clientcorp.ru, +994 12 555 90 21). The affected "
        "session originated from IP 203.0.113.44 and later from "
        "2001:0db8:85a3:0000:0000:8a2e:0370:7334.")
    d.add_paragraph(
        "The exposed API key was sk-live-aBcDeFgH1234567890XyZQrTuVwZ and "
        "the associated access token was "
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U. "
        "A private key fragment was also found exposed in a log file:\n"
        "-----BEGIN PRIVATE KEY-----\n"
        "MIIBVQIBADANBgkqhkiG9w0BAQEFAASCAT8wggE7AgEAAkEAy1eG\n"
        "-----END PRIVATE KEY-----")
    d.add_paragraph(
        "The affected server's MAC address is 3C:5A:B4:1E:88:0F. SIM "
        "provisioning for the on-call phone uses ICCID "
        f"{ICCID}.")
    d.add_paragraph(
        "The incident was logged at 2026-06-04 03:12:07 (log timestamp, "
        "not a personal appointment). Section 7.2 of the runbook was "
        "followed. Mariya's card ending in the number below was flagged "
        "for monitoring out of caution: " + CARD_1 + ", CVV 482.")
    return d


def make_docx_04_rental_agreement_tr() -> docx.Document:
    """Turkish -- rental agreement. Landlord/tenant, dates split personal
    vs administrative on purpose."""
    d = _docx_doc("Kira Sözleşmesi -- Bakü Emlak A.Ş.")
    d.add_paragraph(
        "Kiracı: Elif Yıldız, doğum tarihi 1996-11-05, e-posta "
        "elif.yildiz@example.com, telefon +994 51 442 08 76. Kiracının "
        "kimlik numarası AZ7412963.")
    d.add_paragraph(
        "Mülkiyet adresi: Fəzli Nəcməddin küçəsi 22, Bakı, AZ1078. Kira "
        "bedeli aylık olarak IBAN " + IBAN_3 + " hesabına yatırılacaktır. "
        "Ev sahibi: Kamran Əliyev, telefon +994 77 310 55 42.")
    d.add_paragraph(
        "Sözleşme yürürlük tarihi 2026-01-01 olup, bu idari bir tarihtir "
        "ve kişisel veri değildir. Madde 3 fesih koşullarını "
        "düzenlemektedir.")
    _table(d, ["Alan", "Değer"], [
        ["Kiracı VÖEN (iş yeri kaydı)", "5544332211"],
        ["Ev sahibi telefonu", "+994 77 310 55 42"],
        ["Banka IBAN", IBAN_3],
    ])
    return d


def make_docx_05_bank_letter_ru() -> docx.Document:
    """Russian -- bank customer letter."""
    d = _docx_doc("АО «БакуБанк» -- Клиентское уведомление")
    d.add_paragraph(
        "Уважаемый(ая) Дмитрий Соколов, сообщаем, что ваша карта "
        f"{CARD_2}, код безопасности 917, была перевыпущена. Дата "
        "рождения держателя карты: 1979-09-30, возраст 46 лет.")
    d.add_paragraph(
        "Адрес доставки новой карты: улица Низами 88, кв. 15, Баку, "
        "AZ1001. Контактный телефон +994 12 480 33 27, эл. почта "
        "dmitriy.sokolov@bakubank-client.az.")
    d.add_paragraph(
        f"Расчётный счёт клиента: {IBAN_1}. Номер паспорта: D19283746. "
        "Настоящее уведомление подготовлено 2026-05-10 (дата документа, "
        "не персональные данные).")
    return d


def make_docx_06_medical_referral_en() -> docx.Document:
    """English -- medical referral. Dense PII, embedded patient-ID-card
    image (this generator's first image-bearing sample -- none of 01-05
    carry an embedded image at all)."""
    d = _docx_doc("Riverside Medical Group -- Specialist Referral")
    d.add_paragraph("Date: 2026-02-11")
    d.add_paragraph(
        "Patient: Margaret L. Foster, DOB 1972-06-19, MRN 88213-A, "
        "residing at 44 Larkspur Lane, Portland, OR 97205.")
    d.add_paragraph("Contact: margaret.foster@example.com, +1 (503) 555-0148.")
    d.add_paragraph(
        "Referring physician: Dr. Amir Khalil, NPI 1043827561, "
        "Riverside Medical Group, 12 Cedar Street, Portland, OR 97204.")
    d.add_paragraph(
        "Reason for referral: recurring migraines, referred to neurology "
        "for further evaluation. Insurance policy number PPO-4471-2296, "
        "group ID GRP-90031.")
    _add_image(d, _card_image("PATIENT ID CARD", [
        ("Name", "Margaret L. Foster"),
        ("DOB", "1972-06-19"),
        ("MRN", "88213-A"),
        ("Insurance", "PPO-4471-2296"),
    ]))
    return d


def make_docx_07_university_transcript_az() -> docx.Document:
    """Azerbaijani -- transcript request, embedded student-ID image."""
    d = _docx_doc("Bakı Dövlət Universiteti -- Tələbə İşləri Şöbəsi")
    d.add_paragraph("Tarix: 14.02.2026")
    d.add_paragraph(
        "Tələbə: Elvin Tofiq oğlu Məmmədov, doğum tarixi 03.11.2001, "
        "FİN AZE1234567, ünvan: Nizami küç. 28, Bakı, Azərbaycan.")
    d.add_paragraph("Əlaqə: elvin.mammadov@example.az, telefon +994 50 123 45 67.")
    d.add_paragraph("Fakültə: İnformasiya Texnologiyaları, tələbə bileti №220145.")
    d.add_paragraph(
        "Sorğunu təsdiq edən: dekan müavini Aygün Rəşid qızı Əliyeva, "
        "aygun.aliyeva@example.az.")
    _add_image(d, _card_image("TƏLƏBƏ VƏSİQƏSİ", [
        ("Ad Soyad", "Elvin Məmmədov"),
        ("Doğum tarixi", "03.11.2001"),
        ("FİN", "AZE1234567"),
        ("Tələbə bileti", "220145"),
    ]))
    return d


def make_docx_08_utility_bill_tr() -> docx.Document:
    """Turkish -- utility bill. Sparse PII, table-only, no image."""
    d = _docx_doc("Baku Elektrik Dağıtım A.Ş. -- Fatura")
    d.add_paragraph("Fatura Dönemi: Ocak 2026")
    _table(d, ["Alan", "Değer"], [
        ["Müşteri No", "TR-772104"],
        ["Ad Soyad", "Kerem Yıldız"],
        ["Adres", "Atatürk Cad. No:15, Nişantaşı, İstanbul"],
        ["Tüketim (kWh)", "312"],
        ["Tutar", "486,50 TL"],
        ["Son Ödeme Tarihi", "28.02.2026"],
    ])
    d.add_paragraph("Sorularınız için 444 0 555 numaralı hattı arayabilirsiniz.")
    return d


def make_docx_09_loan_application_ru() -> docx.Document:
    """Russian -- loan application. Dense PII, table + embedded bank-card
    image."""
    d = _docx_doc("АО «БакуБанк» -- Заявка на кредит")
    d.add_paragraph("Дата подачи: 05.02.2026")
    _table(d, ["Поле", "Значение"], [
        ["ФИО заявителя", "Наталья Сергеевна Волкова"],
        ["Дата рождения", "22.09.1988"],
        ["Паспорт", "AZE 04781293"],
        ["Адрес", "ул. Низами 17, кв. 9, Баку"],
        ["Телефон", "+994 55 987 65 43"],
        ["Email", "natalia.volkova@example.ru"],
        ["Запрашиваемая сумма", "15 000 AZN"],
        ["Номер счёта", IBAN_4],
    ])
    d.add_paragraph(
        "Поручитель: Игорь Петрович Соколов, паспорт AZE 05512207, "
        "тел. +994 50 111 22 33.")
    _add_image(d, _card_image("БАНКОВСКАЯ КАРТА", [
        ("Держатель", "N. VOLKOVA"),
        ("Номер карты", CARD_3),
        ("Действительна до", "09/29"),
    ]))
    return d


def make_docx_10_travel_itinerary_en() -> docx.Document:
    """English -- travel itinerary. Sparse body text, embedded boarding-
    pass image."""
    d = _docx_doc("SkyBridge Travel -- Itinerary")
    d.add_paragraph("Traveler: David Okonkwo. Booking reference: 7QXKJM.")
    d.add_paragraph("Departure: Baku (GYD) -> Istanbul (IST), 2026-03-02, 06:40 local.")
    d.add_paragraph("Return: Istanbul (IST) -> Baku (GYD), 2026-03-09, 21:15 local.")
    d.add_paragraph("For assistance contact support@example-travel.com.")
    _add_image(d, _card_image("BOARDING PASS", [
        ("Passenger", "OKONKWO/DAVID"),
        ("Flight", "TK 378"),
        ("Seat", "14C"),
        ("Passport No", "P0044821"),
    ]))
    return d


def make_docx_11_employment_reference_az() -> docx.Document:
    """Azerbaijani + English code-switch -- employment reference letter.
    Dense PII, embedded staff-badge image."""
    d = _docx_doc("Zirvə Consulting MMC -- İnsan Resursları")
    d.add_paragraph("Əmək Fəaliyyəti Haqqında Arayış / Reference Letter")
    d.add_paragraph(
        "Bu sənəd Nərmin Vüqar qızı Hüseynova-nın (doğum tarixi "
        "17.05.1993, FİN AZE7788341) 2021-2026-cı illər arasında "
        "şirkətimizdə Senior Analyst vəzifəsində çalışdığını təsdiq edir.")
    d.add_paragraph(
        "Contact for verification: HR Manager Rauf Bayramov, "
        "rauf.bayramov@example.az, +994 12 404 55 21.")
    d.add_paragraph("Employee ID: ZC-3391. Salary band confirmed separately upon request.")
    d.add_paragraph("Ünvan: Xətai rayonu, Zərifə Əliyeva küç. 9, Bakı AZ1078.")
    _add_image(d, _card_image("İŞÇİ VƏSİQƏSİ / STAFF BADGE", [
        ("Ad Soyad", "Nərmin Hüseynova"),
        ("Vəzifə", "Senior Analyst"),
        ("ID", "ZC-3391"),
        ("FİN", "AZE7788341"),
    ]))
    return d


# --------------------------------------------------------------------------
# PPTX generator
# --------------------------------------------------------------------------
def _slide(prs: pptx.Presentation, title: str, body_lines: list[str],
          notes: str | None = None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3),
                                         Inches(9), Inches(0.8))
    title_box.text_frame.text = title
    body_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.3),
                                        Inches(9), Inches(5))
    tf = body_box.text_frame
    tf.word_wrap = True
    for i, line in enumerate(body_lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.font.size = Pt(16)
    if notes:
        slide.notes_slide.notes_text_frame.text = notes
    return slide


def make_pptx_01_allhands_en() -> pptx.Presentation:
    prs = pptx.Presentation()
    _slide(prs, "Welcome to Acme -- New Hire Spotlight",
          ["Presented by Nigar Abbasova, HR Business Partner",
           "nigar.abbasova@acmecorp.com  |  +994 12 700 45 18"],
          notes="Reminder before this slide: confirm Nigar's badge "
                "access request (employee ID AZ5567123) was approved "
                "yesterday.")
    _slide(prs, "This Quarter's New Team Members",
          ["Farid Huseynov -- Backend Engineer, Baku office",
           "Reached at farid.huseynov@acmecorp.com",
           "Emergency contact: +994 55 981 04 27",
           "Note: quarterly review is scheduled, standard cycle date "
           "2026-07-01 (administrative, not personal)."])
    _slide(prs, "Payroll Setup Confirmation",
          [f"IBAN on file: {IBAN_1}",
           "National ID: AA9081726",
           "Section 2 of the handbook covers direct deposit timing."],
          notes="Farid's date of birth is 1991-02-18, he is 35 years old "
                "-- do not read this slide's notes aloud during the "
                "all-hands.")
    return prs


def make_pptx_02_crm_az() -> pptx.Presentation:
    prs = pptx.Presentation()
    _slide(prs, "Satış Boru Kəməri -- Həftəlik Baxış",
          ["Müştəri: Turan Əkbərov, ATİM MMC",
           "Telefon: +994 50 118 62 90, e-poçt: turan.akbarov@atim.az",
           "Şirkət VÖEN: 3321098765"],
          notes="Turan ilə zəng 2026-04-22 saat 15:00-da planlaşdırılıb. "
                "Ünvan: Xətai rayonu, Cəfər Cabbarlı küçəsi 30.")
    _slide(prs, "Yeni Potensial Müştərilər",
          ["Rəna Quliyeva -- Gəncə filialı, telefon +994 70 442 19 55",
           f"Bank hesabı (ödəniş üçün): {IBAN_2}",
           "Qeyd: müqavilə 4-cü maddəyə uyğun hazırlanıb."],
          notes="Rənanın şəxsiyyət vəsiqəsi AB2837465, FIN 8K4M2X9.")
    return prs


def make_pptx_03_security_en() -> pptx.Presentation:
    prs = pptx.Presentation()
    _slide(prs, "Security Review -- Q2 Incident Summary",
          ["Affected accounts included user aysel.mammadova@corpmail.com",
           "Source IP: 198.51.100.23",
           "Exposed token: ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789"])
    _slide(prs, "Remediation Actions",
          ["Device MAC address rotated: 3C:5A:B4:1E:88:0F",
           f"On-call phone ICCID reissued: {ICCID}",
           "Ticket closed 2026-06-05 (log date, not personal data)."],
          notes="Aysel Məmmədova can be reached directly at "
                "+994 12 333 87 60 if follow-up is needed. Her manager, "
                "Elvin Qasımov, approved the remediation plan.")
    return prs


def make_pptx_04_customer_onboarding_tr() -> pptx.Presentation:
    prs = pptx.Presentation()
    _slide(prs, "Müşteri Katılım Süreci -- Örnek Profil",
          ["Müşteri: Tural Rzayev",
           "E-posta: tural.rzayev@example.com.tr",
           "Telefon: +994 77 205 33 48",
           "Kimlik No: AZ6603381"],
          notes="Doğum tarihi: 1985-12-01, 40 yaşındadır. Adres: "
                "Qara Qarayev prospekti 61, Bakı.")
    _slide(prs, "Ödeme Bilgileri",
          [f"IBAN: {IBAN_3}", "Kart son işlem: " + CARD_3,
           "Not: sözleşme başlangıç tarihi 2026-01-15 idari bir tarihtir."])
    return prs


def make_pptx_05_benefits_ru() -> pptx.Presentation:
    prs = pptx.Presentation()
    _slide(prs, "Обзор льгот для сотрудников",
          ["Сотрудник: Айгюн Гюсейнова, отдел маркетинга",
           "Дата рождения: 1990-08-14, возраст 35 лет",
           "Эл. почта: aygun.huseynova@company.ru"],
          notes="Номер социального страхования: 7С4М2Х9. "
                "Экстренный контакт: +994 55 670 92 18. Адрес: улица "
                "Физули 19, кв. 4, Баку.")
    _slide(prs, "Страховой план",
          [f"Банковский счёт для возмещений: {IBAN_2}",
           "Раздел 5 описывает стандартные условия плана."])
    return prs


# --------------------------------------------------------------------------
def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    docx_makers = [
        ("01_hr_onboarding_en", make_docx_01_hr_onboarding),
        ("02_insurance_claim_az", make_docx_02_insurance_claim_az),
        ("03_it_incident_en", make_docx_03_it_incident),
        ("04_rental_agreement_tr", make_docx_04_rental_agreement_tr),
        ("05_bank_letter_ru", make_docx_05_bank_letter_ru),
        ("06_medical_referral_en", make_docx_06_medical_referral_en),
        ("07_university_transcript_az", make_docx_07_university_transcript_az),
        ("08_utility_bill_tr", make_docx_08_utility_bill_tr),
        ("09_loan_application_ru", make_docx_09_loan_application_ru),
        ("10_travel_itinerary_en", make_docx_10_travel_itinerary_en),
        ("11_employment_reference_az", make_docx_11_employment_reference_az),
    ]
    pptx_makers = [
        ("01_allhands_en", make_pptx_01_allhands_en),
        ("02_crm_az", make_pptx_02_crm_az),
        ("03_security_en", make_pptx_03_security_en),
        ("04_customer_onboarding_tr", make_pptx_04_customer_onboarding_tr),
        ("05_benefits_ru", make_pptx_05_benefits_ru),
    ]

    print(f"writing to {OUT}")
    for name, fn in docx_makers:
        path = OUT / f"sample_{name}.docx"
        fn().save(str(path))
        print(f"  {path.name}")
    for name, fn in pptx_makers:
        path = OUT / f"sample_{name}.pptx"
        fn().save(str(path))
        print(f"  {path.name}")

    print(f"\n{len(docx_makers) + len(pptx_makers)} files written to {OUT}")
    print("Run against this package:")
    print("  python -c \"import sys; sys.path.insert(0,'scripts'); "
         "import pii_guard as pg; "
         "r = pg.sanitize_document('<path>'); print(r.text)\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
