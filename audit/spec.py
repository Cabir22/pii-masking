"""Canonical cross-format content spec.

FIVE records' worth of PII, expressed in three REGISTERS (prose / labeled
fields / table) in four languages, so identical semantic content can be
rendered into TXT, CSV, XLSX, DOCX, PDF and PPTX and scored the same way.

## Why the values are what they are

Everything here is sampled from the project's OWN corpus
(data/testing_samples/test_samples.jsonl and translate_input/*_output.jsonl)
by taking the first N distinct values of each label in corpus order. That is
deliberate and matters for the audit's validity:

* **In-distribution.** Hand-invented names would confound "this format is
  hard" with "this name is out-of-vocabulary", which is a real and separate
  effect in this model.
* **Unbiased.** First-N-in-corpus-order, NOT names picked because the model
  detects them. A first pass of this audit used a single hand-picked record
  ('Rəşad Quliyev') and measured a flat 70% recall everywhere -- which turned
  out to be that one name being a model blind spot, not a property of any
  format. Five records sampled without regard to model behaviour is what
  makes the format comparison mean anything.
* **Correct span convention.** STREET values INCLUDE the street-type word
  ('küçəsi', 'prospekti', 'St.', 'Ave.', 'Cad.'), because that is what the
  corpus's own gold spans do (verified directly: 'Həydər Əliyev küç.',
  'Xəgani prospekti', '28-ji Garachukhur St.'). The same first pass used a
  bare 'Nizami' and scored a 100% STREET miss rate across every format --
  entirely a gold-convention error, since the model was in fact returning
  'Nizami küçəsi'. Getting this wrong would have produced a confident,
  completely false 'the model cannot detect streets in any format'.

Names stay Azerbaijani across all four languages, transliterated into the
target script, because that is what the real translated corpora do (the
Russian rows carry 'Сейидгурбан'/'Аливова', not Russian names).
"""

from __future__ import annotations

# Structured values are shared across languages -- they have no language, so
# holding them fixed isolates the language variable to the prose around them
# and the script the names are written in. All are real corpus values and all
# pass piigen.validate (asserted in audit/run_audit.py before scoring).
_STRUCT = [
    {"EMAIL": "sefadur.sekixanov@yahoo.com", "TELEPHONENUM": "(051) 617-87-13",
     "BUILDINGNUM": "149/6", "ZIPCODE": "AZ1009", "AZ_VOEN": "6317520716",
     "URL": "https://portal.azsoft.az/share/PY6fIE3KcuqeQeD3GLqMRikKS5"},
    {"EMAIL": "s.humehrov@list.az", "TELEPHONENUM": "+994-50-833-47-75",
     "BUILDINGNUM": "14", "ZIPCODE": "AZ1059", "AZ_VOEN": "9678427114",
     "URL": "https://login.company.az/activate?code=UjohztvP4oA-l5h6q16h7NcYGaBjf2Sihi8eK0"},
    {"EMAIL": "abdulhuseynov.f@yandex.ru", "TELEPHONENUM": "+994-77-889-89-31",
     "BUILDINGNUM": "60", "ZIPCODE": "AZ1075", "AZ_VOEN": "3770285196",
     "URL": "https://www.turanholding.az/magic?code=ciz4qlQpf7gv3Y_dW2wTBxJJ"},
    {"EMAIL": "e.sanerli@mail.ru", "TELEPHONENUM": "+994108287625",
     "BUILDINGNUM": "119", "ZIPCODE": "AZ1008", "AZ_VOEN": "5940821545",
     "URL": "https://auth.sirket.az/unsubscribe#GkAvYnmi8gdYknHtkXNDFK4qqvdeT"},
    {"EMAIL": "semaye8164@outlook.com", "TELEPHONENUM": "055 550 59-53",
     "BUILDINGNUM": "25", "ZIPCODE": "AZ1039", "AZ_VOEN": "229604432785106",
     "URL": "https://docs.nurtekstil.az/callback?session_id=saJsqGwodqbTEPcwHgq1oi85Un5CfM6d"},
]

# Name/place values per language: first-N-distinct in corpus order.
_NAMES = {
    "az": [("Gülsəba", "Həqiqətov", "Salyan", "Səfa İmanov döngəsi"),
           ("Amalə", "Əlağayeva", "Bakı", "Həydər Əliyev küç."),
           ("Müzalim", "Ulusoyov", "Yevlax", "Xəgani prospekti"),
           ("Hacıverdi", "Baharov", "Füzuli", "Zığ prospekti"),
           ("Xuddam", "Gülbalayev", "Qırmızı Bazar", "İkram Umarov küçəsi")],
    "en": [("Khani", "Abadov", "Astara", "28-ji Garachukhur St."),
           ("Gulanzar", "Shahsoltanova", "Aghsu", "Olimpiya Ave."),
           ("Ədilbəy", "Xanbutayeva", "Govlar", "Neapol Ave."),
           ("Nənə", "Sarvarli", "Khojavand", "Aladdin Aliyev St."),
           ("Khirdakhanim", "Imamguluzada", "Alat", "Abbas Aliyev St.")],
    "ru": [("Сайтакин", "Агамаликов", "Нахичевань", "проспект Аггёл"),
           ("Фарад", "Агамогланов", "Ходжавенд", "проспект Низами"),
           ("Насиг", "Нюджабаев", "Хырдалан", "улица Ази Асланова"),
           ("Сейидгурбан", "Аливова", "Гёйгёль", "проспект Гейдара Алиева"),
           ("Бабакиши", "Халсаев", "Физули", "улица Хагани")],
    "tr": [("Nikbur", "Qaracayev", "Nahçıvan", "Gündüz Süleymanov Cad."),
           ("Seyyab", "Garalov", "Elet", "Etceler Bulvarı"),
           ("Şahhanım", "Zamanhanov", "Siyezen", "Ezimov Bulvarı"),
           ("Halige", "Hagnezerov", "Kürdemir", "Nizami Cad."),
           ("Vulkan", "Fuladlı", "Gence", "Hagani Bulvarı")],
}

FIELD_ORDER = ["GIVENNAME", "SURNAME", "EMAIL", "TELEPHONENUM",
               "CITY", "STREET", "BUILDINGNUM", "ZIPCODE", "AZ_VOEN", "URL"]

N_RECORDS = 5
LANGS = ["az", "en", "ru", "tr"]
REGISTERS = ["prose", "labeled", "table"]


def records(lang: str) -> list[dict]:
    out = []
    for i in range(N_RECORDS):
        gn, sn, city, street = _NAMES[lang][i]
        out.append({"GIVENNAME": gn, "SURNAME": sn, "CITY": city,
                    "STREET": street, **_STRUCT[i]})
    return out


# Field labels per language -- the HEADERS in the table register and the
# 'Label:' prefixes in the labeled register. Chosen to match the vocabulary
# formats/csv_format.py's HEADER_KEYWORDS actually knows, because that is
# what a real file would use; exp3 runs an unknown-header variant to measure
# what happens when they do not match.
FIELD_LABELS = {
    "az": {"GIVENNAME": "Ad", "SURNAME": "Soyad", "EMAIL": "E-poçt",
           "TELEPHONENUM": "Telefon", "CITY": "Şəhər", "STREET": "Küçə",
           "BUILDINGNUM": "Bina", "ZIPCODE": "Poçt indeksi",
           "AZ_VOEN": "VÖEN", "URL": "Veb sayt"},
    "en": {"GIVENNAME": "First name", "SURNAME": "Surname", "EMAIL": "Email",
           "TELEPHONENUM": "Phone", "CITY": "City", "STREET": "Street",
           "BUILDINGNUM": "Building", "ZIPCODE": "Postal code",
           "AZ_VOEN": "VOEN", "URL": "Website"},
    "ru": {"GIVENNAME": "Имя", "SURNAME": "Фамилия", "EMAIL": "Почта",
           "TELEPHONENUM": "Телефон", "CITY": "Город", "STREET": "Улица",
           "BUILDINGNUM": "Дом", "ZIPCODE": "Индекс",
           "AZ_VOEN": "ВОЕН", "URL": "Сайт"},
    "tr": {"GIVENNAME": "Ad", "SURNAME": "Soyad", "EMAIL": "E-posta",
           "TELEPHONENUM": "Telefon", "CITY": "Şehir", "STREET": "Sokak",
           "BUILDINGNUM": "Bina", "ZIPCODE": "Posta kodu",
           "AZ_VOEN": "VOEN", "URL": "Web sitesi"},
}

FIELD_LABELS_UNKNOWN = {
    lang: {k: f"Col{i+1}" for i, k in enumerate(FIELD_ORDER)}
    for lang in LANGS
}

# Prose frames. STREET already carries its own type word, so the frame does
# NOT add one -- matching the corpus gold convention.
_PROSE = {
    "az": ("Müştəri {GIVENNAME} {SURNAME} ilə bağlı məlumatları təsdiqləyirik. "
           "Onunla {EMAIL} ünvanından və ya {TELEPHONENUM} nömrəsindən əlaqə "
           "saxlamaq olar. Hazırda {CITY} şəhərində, {STREET} {BUILDINGNUM} "
           "ünvanında yaşayır, poçt indeksi {ZIPCODE}. Şirkətin VÖEN-i "
           "{AZ_VOEN}, hesab səhifəsi isə {URL} ünvanındadır."),
    "en": ("We confirm the details for customer {GIVENNAME} {SURNAME}. "
           "They can be reached at {EMAIL} or on {TELEPHONENUM}. They "
           "currently live in {CITY}, at {STREET} {BUILDINGNUM}, postal code "
           "{ZIPCODE}. The company VOEN is {AZ_VOEN} and the account page is "
           "at {URL}."),
    "ru": ("Подтверждаем данные клиента {GIVENNAME} {SURNAME}. Связаться "
           "можно по адресу {EMAIL} или по номеру {TELEPHONENUM}. В "
           "настоящее время проживает в городе {CITY}, {STREET}, дом "
           "{BUILDINGNUM}, индекс {ZIPCODE}. ВОЕН компании {AZ_VOEN}, "
           "страница счёта находится по адресу {URL}."),
    "tr": ("Müşteri {GIVENNAME} {SURNAME} ile ilgili bilgileri onaylıyoruz. "
           "Kendisine {EMAIL} adresinden veya {TELEPHONENUM} numarasından "
           "ulaşılabilir. Şu anda {CITY} şehrinde, {STREET} {BUILDINGNUM} "
           "adresinde yaşıyor, posta kodu {ZIPCODE}. Şirketin VOEN numarası "
           "{AZ_VOEN}, hesap sayfası ise {URL} adresindedir."),
}


def prose_text(lang: str) -> str:
    """All five records as five consecutive sentences of flowing prose."""
    return "\n\n".join(_PROSE[lang].format(**r) for r in records(lang))


def labeled_lines(lang: str, labels: dict | None = None) -> list[str]:
    """Register 2: 'Label: value' lines, one block per record."""
    labels = labels or FIELD_LABELS[lang]
    out: list[str] = []
    for i, r in enumerate(records(lang)):
        if i:
            out.append("")
        for k in FIELD_ORDER:
            out.append(f"{labels[k]}: {r[k]}")
    return out


def table_rows(lang: str, labels: dict | None = None
              ) -> tuple[list[str], list[list[str]]]:
    """Register 3: header row plus one row per record."""
    labels = labels or FIELD_LABELS[lang]
    header = [labels[k] for k in FIELD_ORDER]
    rows = [[r[k] for k in FIELD_ORDER] for r in records(lang)]
    return header, rows


def expected_entities(lang: str) -> list[tuple[str, str]]:
    """Every (label, value) the content contains, once per occurrence.

    Scoring is value-level, not offset-level: identical content necessarily
    lands at different offsets in different formats, so an offset-exact
    cross-format comparison would measure the renderer rather than the
    pipeline. Offset/mapping correctness is measured separately, per format,
    against that format's own extracted text (exp4).
    """
    return [(k, r[k]) for r in records(lang) for k in FIELD_ORDER]
