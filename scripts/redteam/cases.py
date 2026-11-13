"""Adversarial test-case registry for the masking-model probe.

Every case's `expected` entities are computed the same way the real
generation pipeline computes them: a value is minted by `ValueFactory` (so
it is checksum-valid and blocklist-screened, exactly like training data)
and appended to a text buffer via `piigen.text.TextBuilder`, with its
offset recorded AT THE MOMENT OF INSERTION -- never recovered afterwards by
string search (`finalize_expected` below never calls `.find()`/`.index()`
on the assembled text). For the five `anchor_required` labels (AGE,
BUILDINGNUM, CARD_SECURITY_CODE, DATE, TIME), whether a value counts as
"expected" is decided by calling the real `has_anchor()` -- from
`piigen.anchors` for Azerbaijani, `translate.lang.ANCHORS[lang]` for
en/tr/ru -- against the fully assembled text, never a hardcoded assumption.
This is applied uniformly to every category, not just the ones explicitly
probing anchor behaviour, so a case's ground truth can never silently
disagree with the tier rule it is meant to probe.

Entity VALUES for labels whose locale packs are still incomplete (see
scripts/piigen/locales/{en,tr,ru}.py module docstrings: only the calendar
layer is populated there, geography/phone/email are deliberately borrowed
from `az`) are minted with lang="az" even inside EN/TR/RU carrier
documents -- matching how the real translated corpus already behaves (an
Azerbaijani city name like "Astara" stays untranslated inside English
carrier text). DATE/TIME/AGE and every globally-generic pattern-tier label
are minted with the case's actual language, since those builders are fully
populated for all four locales.

Rebuilt 2026-09-16 after the prior campaign's source files (same package,
same general shape: a text-buffer builder, per-label/per-category `_build_*`
functions, `has_anchor()`-driven ground truth) were found deleted from disk
and absent from all git history -- only compiled `.pyc` bytecode survived,
used here strictly as design reference (via `marshal`/`dis`, never
execution), not as an authoritative source for case counts or exact
wording. See docs/findings/redteam_masking_model_findings.md for that investigation.

Run: python scripts/redteam/cases.py
    # builds ALL_CASES, self-validates (dup ids + offset/substring
    # correctness), prints a coverage summary. Does not touch the model.
"""

from __future__ import annotations

import collections
import random
import re
import string
import sys
from dataclasses import dataclass, field
from pathlib import Path

SCRIPTS_DIR = str(Path(__file__).resolve().parents[1])
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from piigen import negatives as NEG                                # noqa: E402
from piigen import checksums as CK                                 # noqa: E402
from piigen.config import ENTITY_TYPES, DETECTION_TIERS, GeneratorConfig  # noqa: E402
from piigen.values import ValueFactory, ValuePool                  # noqa: E402
from piigen.noise import NoiseInjector                             # noqa: E402
from piigen.text import TextBuilder                                # noqa: E402
from piigen import anchors as az_anchors                           # noqa: E402
from translate.lang import ANCHORS as LANG_ANCHORS                 # noqa: E402

SEED = 20260916

ENTITY_TYPES_SET = set(ENTITY_TYPES)

LANGS = ["az", "en", "tr", "ru"]

ANCHOR_REQUIRED_LABELS = {"AGE", "BUILDINGNUM", "CARD_SECURITY_CODE", "DATE", "TIME"}

# Labels whose only populated locale pack is `az` -- see module docstring.
AZ_ONLY_LABELS = {"IBAN", "URL", "EMAIL", "CITY", "STREET", "TELEPHONENUM", "ZIPCODE"}

DEFAULT_WINDOW = az_anchors.DEFAULT_WINDOW

# --- stress categories -------------------------------------------------
CORE = "core"
ANCHOR_DISTANCE = "anchor_distance"
DOC_LENGTH = "doc_length"
COLLISIONS = "collisions"
MULTILINGUAL = "multilingual_names"
FORMATTING = "formatting"
INFORMAL = "informal"
EMBEDDED = "embedded"
BOUNDARY = "boundary"
HARD_NEGATIVE = "hard_negative"
SUPPRESSION = "suppression"

ALL_CATEGORIES = [
    CORE, ANCHOR_DISTANCE, DOC_LENGTH, COLLISIONS, MULTILINGUAL, FORMATTING,
    INFORMAL, EMBEDDED, BOUNDARY, HARD_NEGATIVE, SUPPRESSION,
]


@dataclass
class TestCase:
    id: str
    label: str          # primary label this case is designed to probe
    lang: str
    category: str
    text: str
    expected: list = field(default_factory=list)   # [{start,end,label,text}, ...]
    notes: str = ""
    is_hard_negative: bool = False   # expected is meant to be empty
    is_ambiguous: bool = False       # documented schema collision, log don't hard-fail


# --------------------------------------------------------------------------
# Ground-truth helpers -- the real anchor/offset machinery, nothing hand-typed
# --------------------------------------------------------------------------
def _anchor_mod(lang: str):
    return az_anchors if lang == "az" else LANG_ANCHORS[lang]


def has_anchor_for(label: str, text: str, start: int, end: int, lang: str,
                    window: int | None = None) -> bool:
    mod = _anchor_mod(lang)
    kw = {} if window is None else {"window": window}
    return mod.has_anchor(label, text, start, end, **kw)


def finalize_expected(text: str, raw_entities: list[dict], lang: str) -> list[dict]:
    """Drop anchor_required entities that the REAL has_anchor() rejects.

    Every other entity passes through unchanged. Never re-finds a span by
    searching `text` -- offsets already came from TextBuilder.
    """
    out = []
    for e in raw_entities:
        if e["label"] in ANCHOR_REQUIRED_LABELS:
            if not has_anchor_for(e["label"], text, e["start"], e["end"], lang):
                continue
        out.append(e)
    return out


def mint_value(vf: ValueFactory, rng: random.Random, label: str, lang: str, **kw) -> str:
    use_lang = "az" if label in AZ_ONLY_LABELS else lang
    if label == "GIVENNAME":
        return vf.givenname(use_lang, female=kw.get("female"))
    if label == "SURNAME":
        return vf.surname(use_lang, female=kw.get("female"))
    if label == "EMAIL":
        return vf.email(use_lang, first=kw.get("first", ""), last=kw.get("last", ""),
                        corporate=kw.get("corporate"))
    if label == "TIME":
        return vf.time_of_day(use_lang)
    method = getattr(vf, label.lower())
    return method(use_lang)


_FILLER_SENTENCE = {
    "az": "Sistem qeydiyyatı uğurla tamamlandı və heç bir əlavə tədbir tələb olunmur. ",
    "en": "The system registration completed successfully and no further action is required. ",
    "tr": "Sistem kaydı başarıyla tamamlandı ve başka bir işlem gerekmiyor. ",
    "ru": "Регистрация в системе успешно завершена, дальнейших действий не требуется. ",
}


def filler(lang: str, n: int) -> str:
    if n <= 0:
        return ""
    s = _FILLER_SENTENCE[lang]
    while len(s) < n:
        s += s
    return s[:n]


# --------------------------------------------------------------------------
# Per-label carrier phrases: (lead-in ending right before the value, trailer)
# For the 5 anchor_required labels the lead-in MUST contain a real anchor
# word for that label/language (verified against the live regex tables
# above, not assumed) -- see anchor_distance/suppression tests for direct
# has_anchor() checks against these exact phrases.
# --------------------------------------------------------------------------
CORE_PHRASES: dict[str, dict[str, tuple[str, str]]] = {
    "GIVENNAME": {
        "az": ("Müştərinin adı: ", "."), "en": ("Customer's first name: ", "."),
        "tr": ("Müşterinin adı: ", "."), "ru": ("Имя клиента: ", "."),
    },
    "SURNAME": {
        "az": ("Soyadı: ", "."), "en": ("Last name: ", "."),
        "tr": ("Soyadı: ", "."), "ru": ("Фамилия: ", "."),
    },
    "EMAIL": {
        "az": ("Elektron poçt: ", "."), "en": ("Email address: ", "."),
        "tr": ("E-posta adresi: ", "."), "ru": ("Электронная почта: ", "."),
    },
    "TELEPHONENUM": {
        "az": ("Telefon nömrəsi: ", "."), "en": ("Phone number: ", "."),
        "tr": ("Telefon numarası: ", "."), "ru": ("Номер телефона: ", "."),
    },
    "CITY": {
        "az": ("Şəhər: ", "."), "en": ("City: ", "."),
        "tr": ("Şehir: ", "."), "ru": ("Город: ", "."),
    },
    "STREET": {
        "az": ("Küçə: ", "."), "en": ("Street: ", "."),
        "tr": ("Sokak: ", "."), "ru": ("Улица: ", "."),
    },
    "ZIPCODE": {
        "az": ("Poçt indeksi: ", "."), "en": ("Postal code: ", "."),
        "tr": ("Posta kodu: ", "."), "ru": ("Почтовый индекс: ", "."),
    },
    "IBAN": {
        "az": ("Bank hesabı (IBAN): ", "."), "en": ("Bank account (IBAN): ", "."),
        "tr": ("Banka hesabı (IBAN): ", "."), "ru": ("Банковский счёт (IBAN): ", "."),
    },
    "PAYMENT_CARD_NUMBER": {
        "az": ("Ödəniş kartı nömrəsi: ", "."), "en": ("Payment card number: ", "."),
        "tr": ("Ödeme kartı numarası: ", "."), "ru": ("Номер платёжной карты: ", "."),
    },
    "CARD_SECURITY_CODE": {
        "az": ("Kartın CVV kodu: ", "."), "en": ("Card CVV: ", "."),
        "tr": ("Kartın CVV kodu: ", "."), "ru": ("CVV код карты: ", "."),
    },
    "AZ_FIN": {
        "az": ("FİN kodu: ", "."), "en": ("AZ FIN code: ", "."),
        "tr": ("FIN kodu: ", "."), "ru": ("Код ФИН: ", "."),
    },
    "AZ_ID_CARD_NUMBER": {
        "az": ("Şəxsiyyət vəsiqəsi nömrəsi: ", "."), "en": ("National ID card number: ", "."),
        "tr": ("Kimlik kartı numarası: ", "."), "ru": ("Номер удостоверения личности: ", "."),
    },
    "AZ_PASSPORT_NUMBER": {
        "az": ("Pasport nömrəsi: ", "."), "en": ("Passport number: ", "."),
        "tr": ("Pasaport numarası: ", "."), "ru": ("Номер загранпаспорта: ", "."),
    },
    "AZ_VOEN": {
        "az": ("VÖEN: ", "."), "en": ("VOEN: ", "."),
        "tr": ("VOEN: ", "."), "ru": ("VOEN: ", "."),
    },
    "AZ_DRIVER_LICENSE_NUMBER": {
        "az": ("Sürücülük vəsiqəsi: ", "."), "en": ("Driver's licence number: ", "."),
        "tr": ("Sürücü belgesi numarası: ", "."), "ru": ("Водительское удостоверение: ", "."),
    },
    "API_KEY": {
        "az": ("API açarı: ", "."), "en": ("API key: ", "."),
        "tr": ("API anahtarı: ", "."), "ru": ("API-ключ: ", "."),
    },
    "ACCESS_TOKEN": {
        "az": ("Giriş tokeni: ", "."), "en": ("Access token: ", "."),
        "tr": ("Erişim jetonu: ", "."), "ru": ("Токен доступа: ", "."),
    },
    "PRIVATE_KEY": {
        "az": ("Şəxsi açar:\n", ""), "en": ("Private key:\n", ""),
        "tr": ("Özel anahtar:\n", ""), "ru": ("Приватный ключ:\n", ""),
    },
    "ICCID": {
        "az": ("SIM kart ICCID: ", "."), "en": ("SIM card ICCID: ", "."),
        "tr": ("SIM kart ICCID: ", "."), "ru": ("ICCID SIM-карты: ", "."),
    },
    "IPV4_ADDRESS": {
        "az": ("IP ünvanı: ", "."), "en": ("IP address: ", "."),
        "tr": ("IP adresi: ", "."), "ru": ("IP-адрес: ", "."),
    },
    "IPV6_ADDRESS": {
        "az": ("IPv6 ünvanı: ", "."), "en": ("IPv6 address: ", "."),
        "tr": ("IPv6 adresi: ", "."), "ru": ("IPv6-адрес: ", "."),
    },
    "MAC_ADDRESS": {
        "az": ("MAC ünvanı: ", "."), "en": ("MAC address: ", "."),
        "tr": ("MAC adresi: ", "."), "ru": ("MAC-адрес: ", "."),
    },
    "URL": {
        "az": ("Sıfırlama linki: ", "."), "en": ("Reset link: ", "."),
        "tr": ("Sıfırlama bağlantısı: ", "."), "ru": ("Ссылка для сброса: ", "."),
    },
    "BUILDINGNUM": {
        "az": ("Ünvanı: bina ", "."), "en": ("Address: building ", "."),
        "tr": ("Adresi: bina no ", "."), "ru": ("Адрес: дом ", "."),
    },
    "AGE": {
        "az": ("Onun yaşı: ", "."), "en": ("Her age is: ", "."),
        "tr": ("Onun yaşı: ", "."), "ru": ("Её возраст: ", "."),
    },
    "DATE": {
        "az": ("Doğum tarixi: ", "."), "en": ("Date of birth: ", "."),
        "tr": ("Doğum tarihi: ", "."), "ru": ("Дата рождения: ", "."),
    },
    "TIME": {
        "az": ("Görüş saatı: ", "."), "en": ("Meeting time: ", "."),
        "tr": ("Görüşme saati: ", "."), "ru": ("Время встречи: ", "."),
    },
}

_missing = sorted(ENTITY_TYPES_SET - set(CORE_PHRASES))
if _missing:  # pragma: no cover - a source edit, not a runtime path
    raise ImportError(f"CORE_PHRASES is missing entries for: {_missing}")


# --------------------------------------------------------------------------
# Category builders
# --------------------------------------------------------------------------
def _build_core(vf: ValueFactory, rng: random.Random) -> list[TestCase]:
    cases = []
    for label in sorted(ENTITY_TYPES):
        for lang in LANGS:
            female = rng.random() < 0.5
            lead, trail = CORE_PHRASES[label][lang]
            tb = TextBuilder()
            tb.write(lead)
            value = mint_value(vf, rng, label, lang, female=female)
            tb.entity(label, value)
            tb.write(trail)
            text, raw = tb.result()
            cases.append(TestCase(
                id=f"core_{label.lower()}_{lang}", label=label, lang=lang,
                category=CORE, text=text, expected=finalize_expected(text, raw, lang),
                notes=f"Baseline single-entity {label} probe in {lang}.",
            ))
    return cases


_DISTANCE_SPECS = [("near", 4), ("boundary_in", 74), ("beyond", 109)]


def _build_anchor_distance(vf: ValueFactory, rng: random.Random) -> list[TestCase]:
    cases = []
    for label in sorted(ANCHOR_REQUIRED_LABELS):
        for lang in ("az", "en"):
            anchor_phrase, _ = CORE_PHRASES[label][lang]
            anchor_word = anchor_phrase.strip().rstrip(":")
            for distance_name, gap in _DISTANCE_SPECS:
                tb = TextBuilder()
                tb.write(filler(lang, 20))
                tb.write(anchor_word)
                tb.write(" ")
                tb.write(filler(lang, gap))
                value = mint_value(vf, rng, label, lang)
                tb.entity(label, value)
                tb.write(".")
                text, raw = tb.result()
                cases.append(TestCase(
                    id=f"anchordist_{label.lower()}_{lang}_{distance_name}",
                    label=label, lang=lang, category=ANCHOR_DISTANCE,
                    text=text, expected=finalize_expected(text, raw, lang),
                    notes=(f"{label} value placed ~{gap + 1} chars after its anchor "
                           f"word ('{anchor_word}') -- distance={distance_name}, "
                           f"DEFAULT_WINDOW={DEFAULT_WINDOW}. This was the prior "
                           "campaign's #1 systemic failure mode."),
                ))
    return cases


_DOC_LENGTH_SPECS = [("short", 120), ("long", 1800)]


def _build_doc_length(vf: ValueFactory, rng: random.Random) -> list[TestCase]:
    cases = []
    for label in ("AGE", "DATE"):
        for lang in ("az", "en"):
            anchor_phrase, _ = CORE_PHRASES[label][lang]
            for length_name, total_len in _DOC_LENGTH_SPECS:
                lead_len = max(0, (total_len - len(anchor_phrase) - 30) // 2)
                tb = TextBuilder()
                tb.write(filler(lang, lead_len))
                tb.write(anchor_phrase)
                value = mint_value(vf, rng, label, lang)
                tb.entity(label, value)
                tb.write(". ")
                trail_len = max(0, total_len - len(tb.text))
                tb.write(filler(lang, trail_len))
                text, raw = tb.result()
                cases.append(TestCase(
                    id=f"doclen_{label.lower()}_{lang}_{length_name}",
                    label=label, lang=lang, category=DOC_LENGTH,
                    text=text, expected=finalize_expected(text, raw, lang),
                    notes=(f"Same anchored {label} value+context embedded in a "
                           f"{length_name} document (~{len(text)} chars)."),
                ))
    return cases


def _bare_phone_digits(vf: ValueFactory, rng: random.Random) -> str:
    digits = ""
    for _ in range(30):
        raw = vf.telephonenum("az")
        digits = re.sub(r"\D", "", raw)
        if len(digits) == 10 and digits.startswith("0"):
            return digits
    return digits


def _bare_voen_digits(vf: ValueFactory, rng: random.Random) -> str:
    value = ""
    for _ in range(30):
        value = vf.az_voen("az")
        if len(value) == 10:
            return value
    return value


def _build_collisions(vf: ValueFactory, rng: random.Random) -> list[TestCase]:
    cases = []

    # 1) ZIPCODE vs BUILDINGNUM -- bare 4-digit shape collision (data/schema.md)
    digits4 = f"{rng.randint(1000, 9999)}"
    for lang, label, ctx in [
        ("az", "ZIPCODE", "poçt indeksi"), ("az", "BUILDINGNUM", "bina"),
        ("en", "ZIPCODE", "postal code"), ("en", "BUILDINGNUM", "building"),
    ]:
        tb = TextBuilder()
        tb.write(f"Ünvan məlumatı: {ctx} " if lang == "az" else f"Address info: {ctx} ")
        tb.entity(label, digits4)
        tb.write(".")
        text, raw = tb.result()
        cases.append(TestCase(
            id=f"collision_zip_bldg_{label.lower()}_{lang}", label=label, lang=lang,
            category=COLLISIONS, text=text, expected=finalize_expected(text, raw, lang),
            notes=("data/schema.md documented collision: a bare 4-digit number is "
                   f"shape-identical between ZIPCODE and BUILDINGNUM; here it sits "
                   f"next to explicit '{ctx}' context, so {label} is the "
                   "schema-correct read."),
            is_ambiguous=True,
        ))

    # 2) TELEPHONENUM vs AZ_VOEN -- bare 10-digit shape collision
    phone_digits = _bare_phone_digits(vf, rng)
    tb = TextBuilder()
    tb.write("Zəng edin: ")
    tb.entity("TELEPHONENUM", phone_digits)
    tb.write(" nömrəsinə.")
    text, raw = tb.result()
    cases.append(TestCase(
        id="collision_phone_voen_phone_az", label="TELEPHONENUM", lang="az",
        category=COLLISIONS, text=text, expected=finalize_expected(text, raw, "az"),
        notes=("data/schema.md documented collision: a bare 10-digit string is "
               "shape-identical between TELEPHONENUM's national form and "
               "AZ_VOEN. Here it sits in explicit phone-call context, so "
               "TELEPHONENUM is the schema-correct read."),
        is_ambiguous=True,
    ))
    voen_digits = _bare_voen_digits(vf, rng)
    tb = TextBuilder()
    tb.write("VÖEN: ")
    tb.entity("AZ_VOEN", voen_digits)
    tb.write(".")
    text, raw = tb.result()
    cases.append(TestCase(
        id="collision_phone_voen_voen_az", label="AZ_VOEN", lang="az",
        category=COLLISIONS, text=text, expected=finalize_expected(text, raw, "az"),
        notes=("Companion to collision_phone_voen_phone_az -- same bare "
               "10-digit shape, disambiguated only by explicit VÖEN context."),
        is_ambiguous=True,
    ))

    # 3) AZ_FIN vs AZ_PASSPORT_NUMBER vs order-code hard negative (shared alphabet)
    fin = vf.az_fin("az")
    tb = TextBuilder()
    tb.write("Şəxsi kabinetdə FİN kodu ")
    tb.entity("AZ_FIN", fin)
    tb.write(" olaraq görünür.")
    text, raw = tb.result()
    cases.append(TestCase(
        id="collision_fin_real_az", label="AZ_FIN", lang="az", category=COLLISIONS,
        text=text, expected=finalize_expected(text, raw, "az"),
        notes="data/schema.md: 'AZ_FIN and AZ_PASSPORT_NUMBER must never share an "
              "alphabet. FIN excludes I/O.'",
    ))
    passport = vf.az_passport_number("az")
    tb = TextBuilder()
    tb.write("Beynəlxalq pasport nömrəsi ")
    tb.entity("AZ_PASSPORT_NUMBER", passport)
    tb.write(".")
    text, raw = tb.result()
    cases.append(TestCase(
        id="collision_passport_real_az", label="AZ_PASSPORT_NUMBER", lang="az",
        category=COLLISIONS, text=text, expected=finalize_expected(text, raw, "az"),
        notes="Companion to collision_fin_real_az -- disjoint alphabet, same slot shape.",
    ))
    order_code = "".join(rng.choice(ValueFactory.AZ_FIN_ALPHABET) for _ in range(7))
    tb = TextBuilder()
    tb.write("Sifariş təsdiq kodu: ")
    tb.write(order_code)
    tb.write(". Zəhmət olmasa bu kodu qeyd edin.")
    text, _raw = tb.result()
    cases.append(TestCase(
        id="collision_fin_order_hardneg_az", label="AZ_FIN", lang="az",
        category=COLLISIONS, text=text, expected=[],
        notes=("data/schema.md: 'a 7-character uppercase alphanumeric string "
               "from the same alphabet as AZ_FIN is a deliberate hard-negative "
               "target (order IDs, Git short SHAs)'. This is an "
               "order-confirmation code, not a FIN -- expected is empty on "
               "purpose."),
        is_hard_negative=True,
    ))
    return cases


_NAME_STRESS_SENTENCES = {
    "en": "Please forward this to {name} as soon as possible, the deadline is tomorrow.",
    "tr": "Bu belgeyi lütfen {name} kişisine en kısa sürede iletin, son tarih yarın.",
    "ru": "Пожалуйста, передайте это {name} как можно скорее, срок истекает завтра.",
}


def _build_multilingual_names(vf: ValueFactory, rng: random.Random) -> list[TestCase]:
    """GIVENNAME/SURNAME embedded mid-sentence in EN/TR/RU prose with no
    explicit 'name:' label cue -- both labels are ml_context tier (no anchor
    requirement at all), so this stresses raw NER recall on Azerbaijani names
    in non-Azerbaijani carrier text, the model's documented training gap."""
    cases = []
    for lang in ("en", "tr", "ru"):
        for label, is_given in [("GIVENNAME", True), ("SURNAME", False)]:
            female = rng.random() < 0.5
            value = vf.givenname("az", female=female) if is_given else vf.surname("az", female=female)
            pre, post = _NAME_STRESS_SENTENCES[lang].split("{name}")
            tb = TextBuilder()
            tb.write(pre)
            tb.entity(label, value)
            tb.write(post)
            text, raw = tb.result()
            cases.append(TestCase(
                id=f"mlname_{label.lower()}_{lang}", label=label, lang=lang,
                category=MULTILINGUAL, text=text, expected=finalize_expected(text, raw, lang),
                notes=(f"Azerbaijani-sourced {label} embedded mid-sentence in "
                       f"{lang} prose, no explicit label cue -- known training "
                       "gap (model documented as trained on Azerbaijani names "
                       "only)."),
            ))
    return cases


_FORMATTING_LABELS = ["PAYMENT_CARD_NUMBER", "IBAN", "TELEPHONENUM", "EMAIL",
                      "MAC_ADDRESS", "IPV4_ADDRESS", "IPV6_ADDRESS", "DATE",
                      "TIME", "ZIPCODE"]


def _build_formatting(vf: ValueFactory, rng: random.Random) -> list[TestCase]:
    cases = []
    cfg = GeneratorConfig()
    for label in _FORMATTING_LABELS:
        lang = "az"
        lead, trail = CORE_PHRASES[label][lang]
        tb = TextBuilder()
        tb.write(lead)
        value = mint_value(vf, rng, label, lang)
        tb.entity(label, value)
        tb.write(trail)
        text, raw = tb.result()
        injector = NoiseInjector(cfg, rng)
        noised_text, noised_ents, applied = injector.maybe_apply(text, raw, lang, rate=1.0)
        cases.append(TestCase(
            id=f"formatting_{label.lower()}_{lang}", label=label, lang=lang,
            category=FORMATTING, text=noised_text,
            expected=finalize_expected(noised_text, noised_ents, lang),
            notes=(f"piigen.noise.NoiseInjector-corrupted carrier text "
                   f"(applied={applied or 'none'}) around a real {label} "
                   "value; the value's own span is noise-protected so its "
                   "checksum/pattern stays valid."),
        ))
    return cases


_INFORMAL_SPECS = [
    ("EMAIL", "az", "mail: "), ("TELEPHONENUM", "az", "tel: "),
    ("CITY", "az", "loc: "), ("DATE", "az", "dogum: "),
    ("AGE", "en", "age: "), ("TIME", "en", "@"),
]


def _build_informal(vf: ValueFactory, rng: random.Random) -> list[TestCase]:
    cases = []
    for label, lang, shorthand in _INFORMAL_SPECS:
        tb = TextBuilder()
        tb.write(shorthand)
        value = mint_value(vf, rng, label, lang)
        tb.entity(label, value)
        text, raw = tb.result()
        cases.append(TestCase(
            id=f"informal_{label.lower()}_{lang}", label=label, lang=lang,
            category=INFORMAL, text=text, expected=finalize_expected(text, raw, lang),
            notes=f"Chat-shorthand label ('{shorthand.strip()}') instead of a full sentence.",
        ))
    return cases


def _build_embedded(vf: ValueFactory, rng: random.Random) -> list[TestCase]:
    cases = []

    given = vf.givenname("az")
    surname = vf.surname("az")
    email = mint_value(vf, rng, "EMAIL", "az", first=given, last=surname)
    phone = mint_value(vf, rng, "TELEPHONENUM", "az")
    tb = TextBuilder()
    tb.write("Əməkdaş ")
    tb.entity("GIVENNAME", given)
    tb.write(" ")
    tb.entity("SURNAME", surname)
    tb.write(", əlaqə: ")
    tb.entity("EMAIL", email)
    tb.write(", ")
    tb.entity("TELEPHONENUM", phone)
    tb.write(".")
    text, raw = tb.result()
    cases.append(TestCase(
        id="embedded_hr_az", label="GIVENNAME", lang="az", category=EMBEDDED,
        text=text, expected=finalize_expected(text, raw, "az"),
        notes="4 entities (GIVENNAME, SURNAME, EMAIL, TELEPHONENUM) packed "
              "into one comma-dense sentence.",
    ))

    card = vf.payment_card_number("en")
    iban = mint_value(vf, rng, "IBAN", "en")
    cvv = vf.card_security_code("en")
    tb = TextBuilder()
    tb.write("Card ")
    tb.entity("PAYMENT_CARD_NUMBER", card)
    tb.write(", CVV ")
    tb.entity("CARD_SECURITY_CODE", cvv)
    tb.write(", account IBAN ")
    tb.entity("IBAN", iban)
    tb.write(" -- all on file.")
    text, raw = tb.result()
    cases.append(TestCase(
        id="embedded_financial_en", label="PAYMENT_CARD_NUMBER", lang="en",
        category=EMBEDDED, text=text, expected=finalize_expected(text, raw, "en"),
        notes="3 financial entities packed into one sentence.",
    ))

    p1 = mint_value(vf, rng, "TELEPHONENUM", "ru")
    p2 = mint_value(vf, rng, "TELEPHONENUM", "ru")
    tb = TextBuilder()
    tb.write("Телефоны:")
    tb.entity("TELEPHONENUM", p1)
    tb.write(",")
    tb.entity("TELEPHONENUM", p2)
    tb.write(".")
    text, raw = tb.result()
    cases.append(TestCase(
        id="embedded_adjacent_phones_ru", label="TELEPHONENUM", lang="ru",
        category=EMBEDDED, text=text, expected=finalize_expected(text, raw, "ru"),
        notes="Two different TELEPHONENUM values separated by only a comma, "
              "zero whitespace -- probes whether adjacent same-type entities "
              "merge into one span (the concrete risk plain BIO tagging carries).",
    ))

    url = mint_value(vf, rng, "URL", "tr")
    tb = TextBuilder()
    tb.write("Bağlantı: ")
    tb.entity("URL", url)
    tb.write(" adresine tıklayın.")
    text, raw = tb.result()
    cases.append(TestCase(
        id="embedded_url_tr", label="URL", lang="tr", category=EMBEDDED,
        text=text, expected=finalize_expected(text, raw, "tr"),
        notes="URL containing an embedded token-bearing query parameter.",
    ))

    fin = vf.az_fin("az")
    idcard = vf.az_id_card_number("az")
    tb = TextBuilder()
    tb.write("FİN ")
    tb.entity("AZ_FIN", fin)
    tb.write(", vəsiqə ")
    tb.entity("AZ_ID_CARD_NUMBER", idcard)
    tb.write(".")
    text, raw = tb.result()
    cases.append(TestCase(
        id="embedded_ids_az", label="AZ_FIN", lang="az", category=EMBEDDED,
        text=text, expected=finalize_expected(text, raw, "az"),
        notes="Two AZ-local ID labels adjacent in the same short clause.",
    ))

    api_key = vf.api_key("en")
    token = vf.access_token("en")
    tb = TextBuilder()
    tb.write("Leaked credentials: key=")
    tb.entity("API_KEY", api_key)
    tb.write(" token=")
    tb.entity("ACCESS_TOKEN", token)
    tb.write(" (rotate both immediately).")
    text, raw = tb.result()
    cases.append(TestCase(
        id="embedded_creds_en", label="API_KEY", lang="en", category=EMBEDDED,
        text=text, expected=finalize_expected(text, raw, "en"),
        notes="API_KEY and ACCESS_TOKEN back-to-back, separated only by '= ' "
              "and a space from surrounding text.",
    ))
    return cases


_BOUNDARY_SPECS = [("EMAIL", "az"), ("PAYMENT_CARD_NUMBER", "en"),
                   ("GIVENNAME", "tr"), ("IBAN", "ru")]


def _build_boundary(vf: ValueFactory, rng: random.Random) -> list[TestCase]:
    cases = []
    for label, lang in _BOUNDARY_SPECS:
        tb = TextBuilder()
        value = mint_value(vf, rng, label, lang)
        tb.entity(label, value)
        tb.write(" is the value on file for this record; no other notes.")
        text, raw = tb.result()
        cases.append(TestCase(
            id=f"boundary_start_{label.lower()}_{lang}", label=label, lang=lang,
            category=BOUNDARY, text=text, expected=finalize_expected(text, raw, lang),
            notes=f"{label} sits at character offset 0 -- no leading context at all.",
        ))

        tb = TextBuilder()
        tb.write("On file, no other notes: ")
        value2 = mint_value(vf, rng, label, lang)
        tb.entity(label, value2)
        text, raw = tb.result()
        cases.append(TestCase(
            id=f"boundary_end_{label.lower()}_{lang}", label=label, lang=lang,
            category=BOUNDARY, text=text, expected=finalize_expected(text, raw, lang),
            notes=f"{label} is the final token of the document -- no trailing punctuation.",
        ))
    return cases


_HARDNEG_CONTEXT = {
    "az": "Sənəd nömrəsi: ", "en": "Reference: ", "tr": "Referans: ", "ru": "Ссылка: ",
}


def _build_hard_negatives(rng: random.Random) -> list[TestCase]:
    cases = []
    hard_sample = sorted(rng.sample(NEG.HARD_KEYS, min(8, len(NEG.HARD_KEYS))))
    adv_sample = sorted(rng.sample(NEG.ADV_KEYS, min(8, len(NEG.ADV_KEYS))))
    for i, kind in enumerate(hard_sample):
        lang = LANGS[i % len(LANGS)]
        value = NEG.make_negative(kind, lang, rng)
        tb = TextBuilder()
        tb.write(_HARDNEG_CONTEXT[lang])
        tb.write(value)
        tb.write(".")
        text, _raw = tb.result()
        cases.append(TestCase(
            id=f"hardneg_{kind.lower()}_{lang}", label=f"_HARD_NEGATIVE:{kind}", lang=lang,
            category=HARD_NEGATIVE, text=text, expected=[],
            notes=f"piigen.negatives hard-negative kind={kind}: resembles PII "
                  "but is deliberately not labeled in the real pipeline either.",
            is_hard_negative=True,
        ))
    for i, kind in enumerate(adv_sample):
        lang = LANGS[i % len(LANGS)]
        value = NEG.make_negative(kind, lang, rng)
        tb = TextBuilder()
        tb.write(_HARDNEG_CONTEXT[lang])
        tb.write(value)
        tb.write(".")
        text, _raw = tb.result()
        cases.append(TestCase(
            id=f"advneg_{kind.lower()}_{lang}", label=f"_HARD_NEGATIVE:{kind}", lang=lang,
            category=HARD_NEGATIVE, text=text, expected=[],
            notes=f"piigen.negatives adversarial near-miss kind={kind}: "
                  "structurally invalid / checksum-broken -- one edit away "
                  "from real PII.",
            is_hard_negative=True,
        ))
    return cases


def _build_suppression(vf: ValueFactory, rng: random.Random) -> list[TestCase]:
    """Structural-position suppression (piigen.anchors.az.structural_kind):
    a bare small number right after a heading/section word ('Bölmə N') must
    never be anchor-licensed even with a same-label anchor word elsewhere in
    the sentence. Verified directly against the real function before being
    written here (see the investigation notes in the findings report) --
    `translate.lang.ANCHORS["en"]` has NO equivalent structural guard, which
    is itself a finding, not assumed to work the same as `az`.
    """
    cases = []
    n = str(rng.randint(1, 9))
    tb = TextBuilder()
    tb.write("Bölmə ")
    tb.entity("AGE", n)
    tb.write("-də yaş qrupları üzrə statistika göstərilir.")
    text, raw = tb.result()
    cases.append(TestCase(
        id="suppression_structural_age_az", label="AGE", lang="az",
        category=SUPPRESSION, text=text, expected=finalize_expected(text, raw, "az"),
        notes="Bare small number directly after a heading word ('Bölmə') in "
              "structural position, with the AGE anchor word ('yaş') "
              "elsewhere in the sentence -- ground truth from the real "
              "has_anchor()/is_structural_position() path.",
        is_hard_negative=True,
    ))

    n2 = str(rng.randint(1, 9))
    tb = TextBuilder()
    tb.write("Maddə ")
    tb.entity("BUILDINGNUM", n2)
    tb.write("-də bina və ünvan qaydaları izah olunur.")
    text, raw = tb.result()
    cases.append(TestCase(
        id="suppression_structural_buildingnum_az", label="BUILDINGNUM", lang="az",
        category=SUPPRESSION, text=text, expected=finalize_expected(text, raw, "az"),
        notes="Same structural-position guard, tested against BUILDINGNUM's "
              "own anchor words ('bina', 'ünvan') elsewhere in the sentence.",
        is_hard_negative=True,
    ))
    return cases


# --------------------------------------------------------------------------
def _new_factory(seed: int) -> tuple[ValueFactory, random.Random]:
    rng = random.Random(seed)
    pool = ValuePool()
    return ValueFactory(rng, pool), rng


def build_all_cases() -> list[TestCase]:
    vf, rng = _new_factory(SEED)
    cases: list[TestCase] = []
    cases += _build_core(vf, rng)
    cases += _build_anchor_distance(vf, rng)
    cases += _build_doc_length(vf, rng)
    cases += _build_collisions(vf, rng)
    cases += _build_multilingual_names(vf, rng)
    cases += _build_formatting(vf, rng)
    cases += _build_informal(vf, rng)
    cases += _build_embedded(vf, rng)
    cases += _build_boundary(vf, rng)
    cases += _build_hard_negatives(rng)
    cases += _build_suppression(vf, rng)

    ids = [c.id for c in cases]
    dupes = {i for i in ids if ids.count(i) > 1}
    assert not dupes, f"duplicate case ids: {dupes}"

    for c in cases:
        for e in c.expected:
            actual = c.text[e["start"]:e["end"]]
            assert actual == e["text"], (
                f"{c.id}: span [{e['start']}:{e['end']}] reads {actual!r}, "
                f"expected {e['text']!r}")

    return cases


ALL_CASES = build_all_cases()


def coverage_report() -> dict:
    by_label = collections.Counter()
    by_category = collections.Counter()
    by_lang = collections.Counter()
    labels_exercised = set()
    for c in ALL_CASES:
        by_category[c.category] += 1
        by_lang[c.lang] += 1
        if c.label in ENTITY_TYPES_SET:
            by_label[c.label] += 1
            labels_exercised.add(c.label)
        for e in c.expected:
            labels_exercised.add(e["label"])
    missing_labels = sorted(ENTITY_TYPES_SET - labels_exercised)
    missing_categories = sorted(set(ALL_CATEGORIES) - set(by_category))
    return {
        "total_cases": len(ALL_CASES),
        "by_label": dict(sorted(by_label.items())),
        "by_category": dict(sorted(by_category.items())),
        "by_lang": dict(sorted(by_lang.items())),
        "labels_exercised": sorted(labels_exercised),
        "missing_labels": missing_labels,
        "missing_categories": missing_categories,
    }


if __name__ == "__main__":
    rep = coverage_report()
    print(f"ALL_CASES: {rep['total_cases']}")
    print("by_category:", rep["by_category"])
    print("by_lang:", rep["by_lang"])
    print(f"labels exercised: {len(rep['labels_exercised'])}/{len(ENTITY_TYPES)}")
    if rep["missing_labels"]:
        print("MISSING LABELS:", rep["missing_labels"])
    else:
        print("all 27 labels exercised -- OK")
    if rep["missing_categories"]:
        print("MISSING CATEGORIES:", rep["missing_categories"])
    print("self-validation (dup ids + offset/substring correctness): PASSED")
