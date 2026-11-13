"""Structured containers for the targeted builder (P2-4).

CSV with a header, without one, and with snake_case headers; a pipe table;
JSON; a config block; log lines; key-value lines; and a dialogue. Values sit
in BARE cells: no anchor word beside them, which is where checkpoint 1 missed
EMAIL and the ID card entirely (0% in CSV, dialogue, JSON, pipe and log).

Two rules keep every container valid under the same gates as prose:

  * The five anchor_required labels need a licensing word within 80
    characters. In a table the header is too far from later rows, so AGE,
    CARD_SECURITY_CODE and BUILDINGNUM appear only in formats that put an
    Azerbaijani key right beside the value (`yaş: 34`, `"cvv": "123"`).
  * A container is introduced by an Azerbaijani sentence: header words are
    field labels, not prose, and the language gate does not count them.

Log lines carry no timestamp. Whether a log timestamp is a DATE/TIME is an
open policy question, and an unlabeled one would teach a miss.
"""

from __future__ import annotations

import random

# label -> (Azerbaijani display names, snake_case / machine names)
FIELDS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "GIVENNAME": (("Ad", "Adı"), ("ad", "first_name", "musteri_adi")),
    "SURNAME": (("Soyad", "Soyadı"), ("soyad", "last_name", "musteri_soyadi")),
    "EMAIL": (("E-poçt", "Elektron poçt"), ("email", "e_poct", "mail")),
    "TELEPHONENUM": (("Telefon", "Mobil nömrə"), ("telefon", "phone", "mobil")),
    "CITY": (("Şəhər",), ("seher", "city")),
    "STREET": (("Ünvan", "Küçə"), ("unvan", "street", "kuce")),
    "DATE": (("Doğum tarixi", "Tarix"), ("dogum_tarixi", "birth_date", "tarix")),
    "TIME": (("Saat", "Görüş vaxtı"), ("saat", "time", "vaxt")),
    "IBAN": (("IBAN", "Hesab nömrəsi"), ("iban", "hesab_nomresi")),
    "PAYMENT_CARD_NUMBER": (("Kart nömrəsi",), ("kart_nomresi", "card_number")),
    # D-51h: the Azerbaijani snake_case keys with their own letters too
    # (`şəxsiyyət_vəsiqəsi`, `sürücülük_vəsiqəsi`), listed twice so 2 in 5 cells use them
    "AZ_ID_CARD_NUMBER": (("Şəxsiyyət vəsiqəsi", "Vəsiqə nömrəsi"),
                          ("vesiqe_nomresi", "id_card", "sexsiyyet_vesiqesi", "şəxsiyyət_vəsiqəsi",
                           "şəxsiyyət_vəsiqəsi")),
    "AZ_DRIVER_LICENSE_NUMBER": (("Sürücülük vəsiqəsi",),
                                 ("surucu_vesiqesi", "driver_license", "vesiqe_suruculuk",
                                  "sürücülük_vəsiqəsi", "sürücülük_vəsiqəsi")),
    "AZ_FIN": (("FİN",), ("fin", "fin_kod")),
    "AZ_VOEN": (("VÖEN",), ("voen", "tax_id")),
    "AZ_PASSPORT_NUMBER": (("Pasport",), ("pasport", "passport_no")),
    "IPV4_ADDRESS": (("IP ünvanı",), ("ip", "ip_address")),
    "IPV6_ADDRESS": (("IPv6 ünvanı",), ("ipv6", "ipv6_address")),
    "MAC_ADDRESS": (("MAC ünvanı",), ("mac", "mac_address")),
    "URL": (("Keçid",), ("url", "link")),
    "ICCID": (("ICCID",), ("iccid", "sim_iccid")),
    "API_KEY": (("API açarı",), ("api_key",)),
    "ACCESS_TOKEN": (("Giriş tokeni",), ("access_token", "token")),
    "ZIPCODE": (("Poçt indeksi",), ("poct_indeksi", "zip")),
    # keyed only: the key must license the value (anchors/az.py)
    "AGE": (("Yaş",), ("yaş",)),
    "CARD_SECURITY_CODE": (("CVV",), ("cvv",)),
    "BUILDINGNUM": (("Bina",), ("bina",)),
}

# Needs its licensing key right beside the value.
KEYED_ONLY = frozenset({"AGE", "CARD_SECURITY_CODE", "BUILDINGNUM"})
# Never in a container (a multi-line PEM block is not a cell).
NOT_IN_CONTAINERS = frozenset({"PRIVATE_KEY"})

TABLE_FORMATS = ("csv_header", "csv_noheader", "csv_snake", "pipe_table", "log")
KEYED_FORMATS = ("json", "config", "key_value", "dialogue")
FORMATS = TABLE_FORMATS + KEYED_FORMATS

# Introductions, as frames: each has an id and counts toward the 3% rule.
INTROS: dict[str, list[str]] = {
    "table": [
        "Aşağıdakı cədvəldə müştəri məlumatları verilib:",
        "Sistemdən ixrac edilmiş siyahı belədir:",
        "Hesabat üçün seçilmiş qeydlər aşağıda göstərilib:",
        "Yoxlama üçün tələb olunan məlumatlar cədvəldə toplanıb:",
        "Şöbənin göndərdiyi siyahıdan çıxarış:",
        "Son həftənin qeydiyyat məlumatları aşağıdadır:",
        "Müraciət edənlərin siyahısı cədvəl şəklində təqdim olunur:",
        "Məlumat bazasından seçilmiş sətirlər:",
    ],
    "log": [
        "Sistem jurnalından çıxarış aşağıda verilib:",
        "Serverin qeydlərindən seçilmiş sətirlər:",
        "Təhlükəsizlik yoxlaması zamanı bu qeydlər tapılıb:",
        "Tətbiqin jurnalında aşağıdakı sətirlər qeydə alınıb:",
        "Monitorinq sistemi bu hadisələri qeyd edib:",
    ],
    "json": [
        "Tətbiqdən gələn cavab belədir:",
        "Sorğunun gövdəsi aşağıdakı kimidir:",
        "İnteqrasiya xidmətinə göndərilən məlumat:",
        "Müştəri profili sistemdə bu formada saxlanılır:",
        "Məlumat bazasından qaytarılan qeyd:",
    ],
    "config": [
        "Konfiqurasiya faylının müvafiq hissəsi:",
        "Xidmətin tənzimləmələri aşağıda göstərilib:",
        "Quraşdırma zamanı istifadə edilən parametrlər:",
        "Profil faylında bu dəyərlər yazılıb:",
    ],
    "key_value": [
        "Müştərinin anket məlumatları:",
        "Qeydiyyat kartındakı məlumatlar belədir:",
        "Ərizəçi haqqında məlumat:",
        "Sifariş üzrə əlaqə məlumatları:",
        "Sənəddən köçürülmüş məlumatlar:",
        "Profil səhifəsində göstərilən məlumatlar:",
    ],
    "dialogue": [
        "Operatorla müştəri arasındakı yazışma:",
        "Dəstək xidmətinə edilən zəngin yazılı qeydi:",
        "Çat pəncərəsindən çıxarış:",
        "Qeydiyyat zamanı aparılan danışıq:",
        "Mesajlaşma tarixçəsindən bir hissə:",
    ],
}
OUTROS: list[str] = [
    "Məlumatlar yoxlanıldıqdan sonra arxivə göndəriləcək.",
    "Siyahı şöbə rəhbərinə təqdim edilib.",
    "Qeydlər sistemdə saxlanılır.",
    "Əlavə sual yaranarsa, dəstək xidmətinə müraciət edin.",
    "Bu məlumatlar yalnız daxili istifadə üçündür.",
    "Dəyişikliklər növbəti yeniləmədə nəzərə alınacaq.",
]

# Log messages (Azerbaijani, digit-free) and level tags.
LOG_MESSAGES = [
    "giriş uğurla tamamlandı", "şifrə dəyişdirildi", "profil yeniləndi",
    "sorğu qəbul edildi", "ödəniş təsdiqləndi", "sessiya bağlandı",
    "hesab bloklandı", "yeni cihaz qeydə alındı", "məlumat ixrac edildi",
    "bildiriş göndərildi",
]
LOG_LEVELS = ("INFO", "WARN", "DEBUG", "AUDIT")

# Dialogue: the question names the field; the answer carries the value.
DIALOGUE_Q = [                      # every one takes an accusative field
    "{field} deyə bilərsiniz?",
    "Zəhmət olmasa, {field} yazın.",
    "{field} bir daha təkrarlaya bilərsiniz?",
    "{field} qeyd edə bilərsiniz?",
    "{field} dəqiqləşdirək, zəhmət olmasa.",
]
DIALOGUE_A = [
    "Bəli, {v}.",
    "Yazın: {v}",
    "{v}, yoxlaya bilərsiniz.",
    "Mənimki {v} olmalıdır.",
    "Buyurun, {v}.",
]
# how a question refers to a field, lower-case, for the dialogue
DIALOGUE_FIELD = {
    "GIVENNAME": "adınızı", "SURNAME": "soyadınızı", "EMAIL": "e-poçt ünvanınızı",
    "TELEPHONENUM": "telefon nömrənizi", "CITY": "yaşadığınız şəhəri",
    "STREET": "ünvanınızı", "DATE": "doğum tarixinizi", "TIME": "görüş vaxtını",
    "IBAN": "hesab nömrənizi", "PAYMENT_CARD_NUMBER": "kart nömrənizi",
    "AZ_ID_CARD_NUMBER": "şəxsiyyət vəsiqənizin nömrəsini",
    "AZ_DRIVER_LICENSE_NUMBER": "sürücülük vəsiqənizin nömrəsini",
    "AZ_FIN": "FİN kodunuzu", "AZ_VOEN": "VÖEN nömrənizi",
    "AZ_PASSPORT_NUMBER": "pasport nömrənizi", "IPV4_ADDRESS": "IP ünvanını",
    "IPV6_ADDRESS": "IPv6 ünvanını", "MAC_ADDRESS": "cihazın MAC ünvanını",
    "URL": "keçidi", "ICCID": "SIM kartın ICCID nömrəsini",
    "API_KEY": "API açarını", "ACCESS_TOKEN": "giriş tokenini",
    "ZIPCODE": "poçt indeksini", "AGE": "yaşınızı",
    "CARD_SECURITY_CODE": "kartın CVV kodunu", "BUILDINGNUM": "bina nömrəsini",
}

JSON_NUMBERS = frozenset({"AGE", "BUILDINGNUM"})     # written without quotes


def allowed(fmt: str, label: str) -> bool:
    if label in NOT_IN_CONTAINERS:
        return False
    if label in KEYED_ONLY:
        return fmt in ("json", "config", "key_value")
    return True


def field_name(label: str, fmt: str, rng: random.Random) -> str:
    az, snake = FIELDS[label]
    if fmt in ("csv_snake", "json", "config", "log"):
        # the licensing key of an anchor label must be the Azerbaijani word
        return az[0].lower() if label in KEYED_ONLY else rng.choice(snake)
    return rng.choice(az)


# D-34 (D-33f `fmt_csv_noheader`): a record's status word, a plain cell
STATUS_WORDS = ("aktiv", "gözləmədə", "bağlı", "təsdiqlənib", "ləğv edilib", "yoxlanılır")


# A cell is ("entity", label, value), ("decoy", label, value, kind) or
# ("text", None, word): a cell with no value in it.
def _put(draft, cell) -> None:
    if cell[0] == "entity":
        draft.entity(cell[1], cell[2])
    elif cell[0] == "text":
        draft.add(cell[2])
    else:
        draft.decoy(cell[2], cell[3], cell[1])


def render(fmt: str, draft, columns: list[str], rows: list[list[tuple]],
           rng: random.Random, pick=None) -> list[str]:
    """Write one container into `draft`; return the ids of the fixed text used.

    `pick(items)` chooses one (id, text) pair; the builder passes its
    cap-aware picker, so no introduction or dialogue line breaks the 3% rule.
    """
    pick = pick or (lambda items: rng.choice(items))
    used: list[str] = []
    kind = ("table" if fmt in ("csv_header", "csv_noheader", "csv_snake", "pipe_table")
            else fmt)
    fid, intro = pick([(f"FMT.intro.{kind}.{i}", t) for i, t in enumerate(INTROS[kind])])
    draft.add(intro + "\n")
    used.append(fid)
    names = [field_name(label, fmt, rng) if label in FIELDS else "status" for label in columns]

    if fmt in ("csv_header", "csv_noheader", "csv_snake"):
        sep = rng.choice([",", ",", ";"])
        if fmt != "csv_noheader":
            draft.add(sep.join(names) + "\n")
        for r, row in enumerate(rows):
            for c, cell in enumerate(row):
                if c:
                    draft.add(sep)
                quote = sep in cell[2] or '"' in cell[2]
                if quote:
                    draft.add('"')
                _put(draft, cell)
                if quote:
                    draft.add('"')
            draft.add("\n")
    elif fmt == "pipe_table":
        draft.add("| " + " | ".join(names) + " |\n")
        draft.add("|" + "|".join("---" for _ in names) + "|\n")
        for row in rows:
            draft.add("| ")
            for c, cell in enumerate(row):
                if c:
                    draft.add(" | ")
                _put(draft, cell)
            draft.add(" |\n")
    elif fmt == "log":
        for row in rows:
            draft.add(f"{rng.choice(LOG_LEVELS)} {rng.choice(LOG_MESSAGES)}:")
            for label, cell in zip(columns, row):
                draft.add(f" {field_name(label, fmt, rng)}=")
                _put(draft, cell)
            draft.add("\n")
    elif fmt == "json":
        objs = rows
        many = len(objs) > 1
        draft.add("[\n" if many else "")
        for o, row in enumerate(objs):
            pad = "  " if many else ""
            draft.add(pad + "{\n")
            for c, (label, cell, name) in enumerate(zip(columns, row, names)):
                draft.add(f'{pad}  "{name}": ')
                bare = label in JSON_NUMBERS and cell[2].isdigit()
                draft.add("" if bare else '"')
                _put(draft, cell)
                draft.add("" if bare else '"')
                draft.add(",\n" if c < len(columns) - 1 else "\n")
            draft.add(pad + "}" + ("," if many and o < len(objs) - 1 else "") + "\n")
        draft.add("]\n" if many else "")
    elif fmt == "config":
        draft.add(rng.choice(["[profil]", "[istifadeci]", "[xidmet]", "[musteri]"]) + "\n")
        for row in rows[:1]:
            for label, cell, name in zip(columns, row, names):
                draft.add(f"{name} = ")
                _put(draft, cell)
                draft.add("\n")
    elif fmt == "key_value":
        for row in rows[:1]:
            for label, cell, name in zip(columns, row, names):
                draft.add(f"{name}: ")
                _put(draft, cell)
                draft.add("\n")
    elif fmt == "dialogue":
        for row in rows[:1]:
            for label, cell in zip(columns, row):
                qid, q = pick([(f"FMT.dialogue.q.{i}", t) for i, t in enumerate(DIALOGUE_Q)])
                aid, a = pick([(f"FMT.dialogue.a.{i}", t) for i, t in enumerate(DIALOGUE_A)])
                question = q.replace("{field}", DIALOGUE_FIELD[label])
                draft.add("A: " + question[:1].upper() + question[1:] + "\n")
                before, after = a.split("{v}")
                draft.add("B: " + before)
                _put(draft, cell)
                draft.add(after + "\n")
                used += [qid, aid]
    else:
        raise ValueError(f"unknown format {fmt!r}")

    if rng.random() < 0.5:
        oid, outro = pick([(f"FMT.outro.{i}", t) for i, t in enumerate(OUTROS)])
        draft.add(outro)
        used.append(oid)
    return used


def rows_for(fmt: str) -> int:
    """How many records a container holds: tables are multi-row."""
    return {"csv_header": 3, "csv_noheader": 3, "csv_snake": 3, "pipe_table": 3,
            "log": 3, "json": 2}.get(fmt, 1)


__all__ = ["FIELDS", "FORMATS", "TABLE_FORMATS", "KEYED_FORMATS", "KEYED_ONLY",
           "NOT_IN_CONTAINERS", "allowed", "field_name", "render", "rows_for"]
