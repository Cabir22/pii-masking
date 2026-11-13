"""Sentences of the v4 targeted families (D-51h, D-51i).

Data only; the families that write them are in `builder.py`
(`_family_cross_anchor`, `_family_locative`, `_family_slot_invalid`,
`_family_place_verbs`, `_family_short_keys`, the `namelist` controls and the
structured `cvv` rows). The pools follow the v3 coverage report (section 5) and
the v3 root-cause analysis (sections 3, 5a, 8). Benchmark contexts were described
there only by their anchor words and value shapes; every sentence here is our
own. All are for the native check (`native_check_list()` prints them).

Rules the sentences keep (as the earlier rounds' frames do):
  * no digits: a digit in a fixed sentence would be an unlabelled number in
    every document that uses it;
  * R1 (P4-1 round 1): after "anchor + value" a verb that records the value
    takes `kimi`/`olaraq`; a value after a locative noun, with no anchor
    right before it, is the subject and takes the bare verb;
  * `{v}` is the value (a real one or a look-alike), `{tail}` a right-context
    phrase that a look-alike takes and a real value does not.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# 1a. Short numbers after VÖEN / Vergi nömrəsi / FİN / vəsiqə / token / API key
# --------------------------------------------------------------------------- #
# Sentences for BOTH halves of a pair: once with a real value of the label,
# once with a 2-3-digit look-alike, the same left context (v3 tagged these
# numbers CVV: 132 benchmark errors; training had 2-4 of them in the slot).
SHORT_BOTH = {
    "AZ_VOEN": [
        "Formanın VÖEN sahəsində {v} göstərilib.",
        "Hesab-fakturada VÖEN kimi {v} yazılıb.",
        "Sorğuda vergi nömrəsi olaraq {v} daxil edilib.",
        "Ərizədə şirkətin VÖEN-i {v} kimi qeyd olunub.",
        "Müqavilənin rekvizitlərində VÖEN {v} olaraq əks olunub.",
    ],
    "AZ_FIN": [
        "Ərizədə FİN kodu {v} kimi göstərilib.",
        "Formanın FİN sahəsində {v} yazılıb.",
        "Sistemdə FİN olaraq {v} daxil edilib.",
        "Arayışda şəxsin FİN kodu {v} olaraq qeyd olunub.",
    ],
    "AZ_ID_CARD_NUMBER": [
        "Ərizədə şəxsiyyət vəsiqəsinin nömrəsi {v} kimi göstərilib.",
        "Formanın vəsiqə nömrəsi sahəsində {v} yazılıb.",
        "Qeydiyyatda vəsiqə nömrəsi olaraq {v} daxil edilib.",
        "Müqavilədə tərəfin şəxsiyyət vəsiqəsinin nömrəsi {v} kimi qeyd olunub.",
    ],
    "ACCESS_TOKEN": [
        "Sorğunun başlığında token {v} kimi göstərilib.",
        "Jurnalda sessiya tokeni olaraq {v} yazılıb.",
        "Konfiqurasiyada giriş tokeni {v} kimi saxlanılır.",
    ],
    "API_KEY": [
        "Konfiqurasiyada API açarı {v} kimi yazılıb.",
        "İnteqrasiya sorğusunda API açarı olaraq {v} göndərilib.",
        "Tərəfdaşın panelində API açarı {v} kimi göstərilib.",
    ],
}
# ... and sentences for the look-alike alone, where the words after the number
# make it a count or a reference number (`... 214 dəfə`, `... 214 saylı`)
SHORT_ONLY = {
    "AZ_VOEN": [
        "Bu rüb həmin VÖEN {v} dəfə yoxlanılıb.",
        "Vergi nömrəsi {v} saylı sorğu ilə yoxlanılıb.",
        "Reyestrdə VÖEN {v} nömrəli sətirdə göstərilib.",
    ],
    "AZ_FIN": [
        "FİN kodu {v} saylı müraciətdə tələb olunub.",
        "Bu həftə FİN kodu {v} dəfə səhv daxil edilib.",
    ],
    "AZ_ID_CARD_NUMBER": [
        "Şəxsiyyət vəsiqəsi {v} saylı arayışla birlikdə təqdim olunub.",
        "Vəsiqə nömrəsi {v} saylı qovluqda saxlanılır.",
    ],
    "ACCESS_TOKEN": [
        "Sessiya tokeni {v} simvoldan ibarətdir.",
        "Bu gün token {v} dəfə yenilənib.",
        "Hər istifadəçi üçün token {v} dəqiqə ərzində etibarlıdır.",
    ],
    "API_KEY": [
        "Xidmətin API açarı {v} sorğudan sonra müvəqqəti bloklanır.",
        "API açarı {v} gündən bir yenilənir.",
    ],
}
# `label: value` lines and CSV cells: the key names (Azerbaijani display,
# snake_case) of the three ID labels
SHORT_KEYS = {
    "AZ_VOEN": (("VÖEN", "Vergi nömrəsi", "VÖEN nömrəsi"), ("voen", "vergi_nomresi", "vöen")),
    "AZ_FIN": (("FİN", "FİN kodu"), ("fin", "fin_kod", "fin_kodu")),
    "AZ_ID_CARD_NUMBER": (("Şəxsiyyət vəsiqəsi", "Vəsiqə nömrəsi"),
                          ("şəxsiyyət_vəsiqəsi", "vesiqe_nomresi", "sexsiyyet_vesiqesi")),
}
# two records written one after the other, each `Field: value` + a status line
RECORD_INTROS = [
    "Yoxlama üçün sistemdən iki qeyd seçilib:",
    "Müraciətlər bazasından çıxarış:",
    "Operatorun yoxladığı qeydlər:",
    "Arxivdən bərpa olunmuş qeydlər:",
    "Düzəliş tələb olunan qeydlərin siyahısı:",
]
RECORD_HEADS = [("Birinci qeyd:", "İkinci qeyd:"), ("Birinci müraciət:", "İkinci müraciət:"),
                ("Əvvəlki versiya:", "Yenilənmiş versiya:"), ("Köhnə qeyd:", "Yeni qeyd:")]
RECORD_STATUS = ("təsdiqlənib", "yoxlanılır", "natamam", "gözləmədə", "düzəliş tələb olunur")

# --------------------------------------------------------------------------- #
# 1b. Company, project and brand names and codes in a name slot (D-2)
# --------------------------------------------------------------------------- #
# The same sentence with a real surname / city / street (labelled) and with
# `<Surname> MMC`, a code `AAA999`, `<City> layihəsi`, `<name> haqqında kitab`
# (unlabelled). v3 masked 143 such benchmark values; after a surname word 544
# of 561 training values were surnames and none was a look-alike.
NAME_SLOT = {
    "SURNAME": [
        "Anketdə soyad kimi {v} göstərilib.",
        "Qeydiyyat formasında soyad olaraq {v} yazılıb.",
        "Sistemin soyad sahəsində {v} qeyd olunub.",
        "Müraciətdə soyad kimi {v} daxil edilib.",
        "Siyahıda soyad olaraq {v} əks olunub.",
    ],
    "CITY": [
        "Anketdə şəhər kimi {v} göstərilib.",
        "Qeydiyyat formasında şəhər olaraq {v} seçilib.",
        "Ünvan blokunun şəhər sahəsində {v} yazılıb.",
        "Sifarişdə şəhər kimi {v} qeyd olunub.",
    ],
    "STREET": [
        "Anketdə küçə kimi {v} göstərilib.",
        "Çatdırılma formasında küçə olaraq {v} yazılıb.",
        "Ünvanın küçə sahəsində {v} qeyd olunub.",
    ],
}
# the same slot as a `Field: value` line, two records
NAME_SLOT_KEYS = {"SURNAME": ("Soyad", "Soyadı"), "CITY": ("Şəhər",), "STREET": ("Küçə",)}

# --------------------------------------------------------------------------- #
# 1c / 2. Room, office and door numbers named a `kod` (contextual, ~CVV)
# --------------------------------------------------------------------------- #
# A locative document noun, the number, then `kodu` (v3: CVV, 47 benchmark
# distractors). Paired in the document with a real CVV sentence (CVV_FRAMES).
ROOM_CODE = [
    "Otaq kartında {v} kodu ilə göstərilən zal təmirdədir.",
    "Mərtəbə planında {v} kodu iclas otağına aiddir.",
    "Rezervasiya məlumatında {v} kodu ilə qeyd olunan otaq artıq tutulub.",
    "Ofis sxemində {v} kodu altında arxiv otağı göstərilib.",
    "Mehmanxana sistemində {v} kodu ilə yazılan otaq yenidən açılıb.",
    "Təmir siyahısında {v} kodu ilə qeyd olunan otaqda kondisioner dəyişdirilib.",
]
# the words AFTER the number make it a door code (`... 482 qapı kodu`)
DOOR_CODE = [
    "Anbarın girişində {v} qapı kodu istifadə olunur.",
    "Server otağı üçün {v} qapı kodu təyin edilib.",
    "Arxa giriş {v} qapı kodu ilə açılır.",
    "Yeni əməkdaşlara {v} qapı kodu bildirilib.",
]

# --------------------------------------------------------------------------- #
# 1d. MAC fragments with dashes (`12-34-56`)
# --------------------------------------------------------------------------- #
MAC_FRAGMENT = [
    "Şəbəkə jurnalında MAC ünvanı {v} ilə bitən cihaz qeydə alınıb.",
    "MAC filtrində {v} prefiksi olan cihazlar bloklanıb.",
    "Şəbəkə kartının MAC ünvanı {v} ilə başlayır.",
    "Routerin siyahısında MAC ünvanının son hissəsi {v} kimi göstərilib.",
    "Şəbəkə hesabatında istehsalçı prefiksi {v} olan qurğular ayrıca sayılıb.",
]
MAC_REAL = [
    "Cihazın MAC ünvanı {v} olaraq qeyd olunub.",
    "Şəbəkə jurnalında MAC ünvanı {v} olan cihaz qeydə alınıb.",
    "Routerin siyahısında MAC ünvanı {v} kimi göstərilib.",
    "Şəbəkə kartının tam MAC ünvanı {v} kimi yazılıb.",
]

# --------------------------------------------------------------------------- #
# 1e. IBAN fragments (`AZ1234`, `AZ37NAB`) after IBAN / hesab words
# --------------------------------------------------------------------------- #
IBAN_FRAGMENT = [
    "Hesabın IBAN kodu {v} ilə başlayır.",
    "Formanın IBAN sahəsinə yalnız {v} yazılıb, qalan hissə boş qalıb.",
    "Müştəri hesab nömrəsinin əvvəlini {v} kimi bildirib.",
    "Çıxarışda IBAN qısaldılmış formada {v} kimi göstərilib.",
]
IBAN_REAL = [
    "Formanın IBAN sahəsinə {v} yazılıb.",
    "Ödəniş {v} hesabına köçürülüb.",
    "Müştərinin IBAN-ı {v} kimi qeyd olunub.",
    "Çıxarışda hesab nömrəsi {v} olaraq göstərilib.",
]
IBAN_COLUMNS = ("iban", "hesab_nomresi", "IBAN")

# --------------------------------------------------------------------------- #
# 1f. IPv4 look-alikes (`412.3.7.1`, `10.4.7`, `1.2.3.x`) after IP words
# --------------------------------------------------------------------------- #
IPV4_BOTH = [
    "Sorğu qeydində IP ünvanı {v} kimi yazılıb.",
    "Formanın IP sahəsində {v} göstərilib.",
    "Jurnalda mənbə IP ünvanı olaraq {v} qeyd olunub.",
    "Hesabatda serverin IP ünvanı {v} kimi əks olunub.",
]
# v4.1 (#91 item 3): a look-alike gets a sentence of its own, never
# the real value's sentence (`_cross_ipv4` wrote the same IPV4_BOTH sentence
# with a real IPv4 and with a look-alike; v4 then found 36% in such a frame)
IPV4_LOOKALIKE = [
    "Müştərinin göndərdiyi ekran görüntüsündə {v} görünür.",
    "Köhnə qeydlərin şəbəkə sahəsində {v} qalıb.",
    "Texniki müraciətə əlavə olunan faylda {v} yazılıb.",
    "Sənədin layihəsində şəbəkə ünvanı {v} kimi göstərilib.",
]
IPV4_PLACEHOLDER = [
    "Təlimatda IP ünvanı kimi {v} şablonu verilib.",
    "Nümunə konfiqurasiyada IP ünvanı yerinə {v} yazılıb.",
]

# --------------------------------------------------------------------------- #
# 2. Right context: a ZIP-shaped code followed by `məhsul kodu`
# --------------------------------------------------------------------------- #
# The same left context with a real ZIP (no {tail}) and with a ZIP-shaped
# product code ({tail} = ` məhsul kodu`, ...): only the words after decide.
ZIP_RIGHT = [
    "Qaimədə indeks kimi {v}{tail} göstərilib.",
    "Bağlamanın etiketində indeks olaraq {v}{tail} yazılıb.",
    "Sənəddə poçt indeksi kimi {v}{tail} qeyd olunub.",
    "Sifariş formasının indeks sahəsində {v}{tail} göstərilib.",
]
ZIP_TAILS = (" məhsul kodu", " anbar kodu", " partiya kodu")

# --------------------------------------------------------------------------- #
# 3. The locative + verb frame: a document noun in the locative, the value,
#    then the verb -- no anchor word right before the value
# --------------------------------------------------------------------------- #
LOCATIVE = {
    "PAYMENT_CARD_NUMBER": [
        "Ödəniş səhifəsində {v} görünür.",
        "Müştərinin ödəniş profilində {v} saxlanılır.",
        "Kart məlumatları bölməsində {v} əks olunub.",
        "Hesab çıxarışında {v} göstərilib.",
        "Mobil tətbiqin pul kisəsində {v} görünür.",
        "Abunə parametrlərində {v} seçilib.",
        "Sifariş formasında {v} qeyd olunub.",
        "Ödəniş formasına {v} daxil edilib.",
    ],
    "AZ_VOEN": [
        "Şirkət profilində {v} göstərilib.",
        "Rekvizitlər cədvəlində {v} yazılıb.",
        "Vergi bəyannaməsində {v} əks olunub.",
        "Hesab-fakturanın başlığında {v} qeyd edilib.",
        "Tender ərizəsində {v} göstərilib.",
        "Dövlət reyestrindən çıxarışda {v} görünür.",
        "Vergi uçotu kartında {v} qeyd olunub.",
    ],
    "AZ_ID_CARD_NUMBER": [
        "Müraciət kartında {v} qeyd olunub.",
        "Qonaqların qeydiyyat jurnalında {v} yazılıb.",
        "Kredit ərizəsində {v} göstərilib.",
        "Notariat aktında {v} əks olunub.",
        "Bank anketində {v} daxil edilib.",
    ],
    "AZ_PASSPORT_NUMBER": [
        "Bilet sifarişində {v} göstərilib.",
        "Viza ərizəsində {v} yazılıb.",
        "Sərnişin siyahısında {v} görünür.",
        "Mehmanxananın qeydiyyat kartında {v} qeyd olunub.",
    ],
    "IBAN": [
        "Ödəniş tapşırığında {v} göstərilib.",
        "Müqavilənin bank rekvizitlərində {v} yazılıb.",
        "Əmək haqqı cədvəlində {v} qeyd olunub.",
        "Hesab-fakturanın sonunda {v} əks olunub.",
        "Geri ödəniş ərizəsində {v} göstərilib.",
    ],
}
# the look-alike a locative slot may also hold, in the same sentence: the
# length or the format shows it (never a checksum-only difference, D-51d)
LOCATIVE_KINDS = {
    "PAYMENT_CARD_NUMBER": ("card_wrong_length",),
    "AZ_VOEN": ("voen_wrong_length",),
    "AZ_ID_CARD_NUMBER": ("id_card_too_short", "id_card_too_long"),
    "AZ_PASSPORT_NUMBER": ("passport_wrong_length",),
    "IBAN": ("iban_truncated",),
}

# --------------------------------------------------------------------------- #
# 9. Invalid values in the label slot (C4), the same frame with a valid value
# --------------------------------------------------------------------------- #
SLOT_PROSE = {
    "TIME": [
        "Qəbul saatı {v} olaraq göstərilib.",
        "Cədvəldə görüş vaxtı {v} kimi yazılıb.",
        "Sistemdə növbənin başlama vaxtı {v} olaraq qeyd olunub.",
        "Bildirişdə iclasın vaxtı {v} kimi göstərilib.",
        # coverage report section 5, item 10: a clock time right after a
        # calendar word (`təqvimdə`); v3 missed 11, training had none
        "Təqvimdə {v} üçün görüş qeyd olunub.",
        "Paylaşılan təqvimdə {v} üçün zəng planlaşdırılıb.",
        "İş təqvimində {v} üçün iclas təyin edilib.",
        "Təqvimə görə qəbul {v} olaraq göstərilib.",
    ],
    "AGE": [
        "Anketdə müştərinin yaşı {v} kimi göstərilib.",
        "Sistemdə pasiyentin yaşı {v} olaraq qeyd olunub.",
        "Formada iştirakçının yaşı {v} kimi yazılıb.",
    ],
    "DATE": [
        "Ərizədə doğum tarixi {v} kimi göstərilib.",
        "Sistemdə müqavilənin tarixi {v} olaraq qeyd olunub.",
        "Arayışda verilmə tarixi {v} kimi yazılıb.",
    ],
    "AZ_FIN": [
        "Ərizəçinin FİN kodu {v} kimi göstərilib.",
        "Sistemdə FİN {v} olaraq qeyd olunub.",
        "Müraciətdə FİN kodu {v} kimi yazılıb.",
    ],
    "PAYMENT_CARD_NUMBER": [
        "Ödəniş formasında kart nömrəsi {v} kimi daxil edilib.",
        "Sifarişdə bank kartının nömrəsi {v} olaraq göstərilib.",
        "Müştərinin kart nömrəsi {v} kimi qeyd olunub.",
    ],
    # coverage report section 5, item 7: a 2-digit number after a ZIP word
    # (v3 tagged 17 BUILDINGNUM), beside a real ZIP in the same frame
    "ZIPCODE": [
        "Bağlamanın üzərində poçt indeksi {v} kimi yazılıb.",
        "Formada poçt indeksi olaraq {v} göstərilib.",
        "Sifarişin ünvan hissəsində indeks {v} kimi qeyd olunub.",
        "Qaimədə poçt indeksi {v} olaraq daxil edilib.",
    ],
    # v4.2 fix list: IBAN, licence and ICCID slots (native check)
    "IBAN": [
        "Ödəniş tapşırığında alıcının hesab nömrəsi (IBAN) {v} kimi göstərilib.",
        "Müqavilədə şirkətin IBAN nömrəsi {v} olaraq qeyd olunub.",
        "Hesab-fakturada IBAN {v} kimi yazılıb.",
    ],
    "AZ_DRIVER_LICENSE_NUMBER": [
        "Ərizədə sürücülük vəsiqəsinin nömrəsi {v} kimi göstərilib.",
        "Sığorta formasında sürücülük vəsiqəsinin nömrəsi {v} olaraq qeyd olunub.",
        "İcarə müqaviləsində sürücünün vəsiqə nömrəsi {v} kimi yazılıb.",
    ],
    "ICCID": [
        "Müqavilədə SIM kartın ICCID nömrəsi {v} kimi göstərilib.",
        "Sistemdə SIM kartın ICCID kodu {v} olaraq qeyd olunub.",
        "Ərizədə köhnə SIM kartın ICCID nömrəsi {v} kimi yazılıb.",
    ],
}
SLOT_KINDS = {
    # v4.2 fix list (C4): the near misses (`24:51`, `20:61`, `30.02.2027`,
    # `19.15.2022`) beside the far ones, in the label's own slot
    "TIME": ("time_bad_hour", "time_bad_minute", "time_hour_near", "time_minute_near"),
    "AGE": ("age_negative", "age_implausible"),
    "DATE": ("date_impossible_day", "date_bad_month", "date_iso_out_of_range",
             "date_feb_invalid", "date_month_near"),
    "AZ_FIN": ("fin_with_hyphen", "fin_dummy_pattern"),
    "PAYMENT_CARD_NUMBER": ("card_wrong_length",),
    # v4.1 (D-52d, the #91 item 4): the protected `zip_wrong_length` (AZ + 1-3 or 5
    # digits) in the label slot too, beside a real ZIP
    "ZIPCODE": ("zip_two_digits", "zip_wrong_length"),
    # v4.2 fix list (A5): the biggest groups of PII-free shadow documents
    # v4.1 masked. No IPv4 slot (v4.2 native review B): an IPv4 look-alike
    # gets a sentence of its own (#91 item 3, D-52b), as `_cross_ipv4` writes it
    "IBAN": ("iban_short_account",),
    "AZ_DRIVER_LICENSE_NUMBER": ("licence_three_letters",),
    "ICCID": ("iccid_wrong_prefix",),
}

# --------------------------------------------------------------------------- #
# 7. Suffixed cities in verb frames that also take people, and surnames with
#    the ablative. A second clause says the referent is the place
#    (`şəhərin`, `oradakı`, `oranın`), or a person (`o`). D-51h native review
#    (A): not `rayonun`, as the town may be Bakı, Gəncə or Sumqayıt.
# --------------------------------------------------------------------------- #
PLACE_VERBS = {
    # copula: Şəkidir, Gəncədir
    "cop": [
        "Turnirin ev sahibi {v}, oyunlar şəhərin yeni stadionunda keçiriləcək.",
        "Bu layihənin əsas tərəfdaşı {v}, şəhərin bələdiyyəsi maliyyəni öz üzərinə götürüb.",
        "Ən çox darıxdığım şəhər {v}, oranın küçələri yadımdan çıxmır.",
        "Komandamızın əsas rəqibi {v}, oranın klubu bu il çox güclüdür.",
    ],
    # instrumental: Gəncəylə, Lənkəranla (or `<city> ilə`, the `{v} ilə` form)
    "ins": [
        "Bu gün {v} danışdım, oradakı filial sənədləri sabah göndərəcək.",
        "Mərkəzi ofis {v} əlaqə saxlayıb, şəhərin bələdiyyəsi cavab verib.",
        "Biz {v} uzun müddətdir əməkdaşlıq edirik, oradakı zavod əsas təchizatçımızdır.",
        "Səhər iclasında {v} videobağlantı quruldu, oranın nümayəndələri də qoşuldu.",
    ],
    # accusative after a consonant: Lənkəranı, Şirvanı
    "acc": [
        "Uşaqlıqdan {v} çox sevirəm, oranın havası başqadır.",
        "Keçən il {v} ilk dəfə gördüm və şəhərin küçələri xoşuma gəldi.",
        "Biz {v} yaxşı tanıyırıq, orada uzun illər yaşamışıq.",
        "Tələbələr {v} yaxından tanımaq üçün şəhərin muzeylərini gəziblər.",
    ],
    # ablative: Gəncədən, Şirvandan
    "abl": [
        "{v} zəng etdilər, oradakı ofis sifarişi təsdiqləyib.",
        "Səhər {v} xəbər gəldi ki, şəhərdə yollar təmir olunur.",
        "{v} rəsmi məktub aldıq, oranın icra hakimiyyəti görüşə razılıq verib.",
        "Bu həftə {v} çoxlu sifariş gəlib, oranın mağazaları yenidən açılıb.",
    ],
}
# a surname in the ablative (Məmmədovdan): SURNAME, the suffix inside the span
SURNAME_ABLATIVE = [
    "{v} zəng gəldi, sənədləri sabah gətirəcəyini bildirdi.",
    "Dünən {v} məktub aldım, o, iclasa gələ bilməyəcəyini yazıb.",
    "Müdir {v} hesabatı tələb edib, o isə sabaha qədər vaxt istəyib.",
    "{v} cavab gözləyirik, o, sənədləri hələ imzalamayıb.",
]

# --------------------------------------------------------------------------- #
# 6. Non-names in the D-39b name frames (unlabelled controls)
# --------------------------------------------------------------------------- #
CONTROL_DEPARTMENTS = ["Maliyyə şöbəsi", "Hüquqi təminat şöbəsi", "Kadrlar şöbəsi",
                       "Təchizat bölməsi", "Mətbuat xidməti", "Ümumi şöbə",
                       "Texniki xidmət bölməsi", "Mühasibatlıq", "Arxiv bölməsi",
                       "Kargüzarlıq şöbəsi"]
CONTROL_POSITIONS = ["Baş mühasib", "Şöbə müdiri", "Aparıcı mütəxəssis", "Baş məsləhətçi",
                     "Kargüzar", "Hüquqşünas", "Sistem inzibatçısı", "Layihə rəhbəri"]
CONTROL_DOCUMENTS = ["Ərizə forması", "Kollektiv müqavilə", "Daxili nizamnamə",
                     "İllik hesabat", "Vəzifə təlimatı", "Hesabat forması", "Ezamiyyə vərəqəsi"]
CONTROL_ORGS = ["«Mərkəzi Anbar» MMC", "«Mərkəzi Tikinti» ASC", "«Birlik Servis» MMC",
                "«Təmiz Su» MMC", "«Etibarlı Yol» ASC", "«Cənub Logistika» MMC"]
# a separate list in the same document as the name list: intro -> items
CONTROL_LISTS = {
    "Komissiyanın işinə cəlb olunan qurumlar:": "orgs_departments",
    "Müsabiqəyə təqdim olunmalı sənədlər:": "documents",
    "Ştat cədvəlinə əlavə edilən vəzifələr:": "positions",
    "İclasda hesabat verəcək struktur bölmələr:": "departments",
}
# one line inside a name list: a vacant seat (`Baş mühasib (vakant)`)
CONTROL_VACANT = "(vakant)"
# a lowercase role word, then a capitalised department or organisation (the
# marked words, unlabelled)
ROLE_CONTROL_SENTENCES = [
    "İclasda müdir <<Maliyyə Şöbəsinin>> illik hesabatını təqdim edib.",
    "Layihəyə rəis <<Texniki Xidmət Bölməsi>> ilə birlikdə nəzarət edir.",
    "Sənədləri katib <<Ümumi Şöbədən>> alıb.",
    "Toplantıda nümayəndə <<İctimai Şuranın>> mövqeyini açıqlayıb.",
    "Məlumatı mühasib <<Mərkəzi Anbarın>> qaimələrinə əsasən hazırlayıb.",
    "Təklifi direktor <<Müşahidə Şurasına>> təqdim edib.",
    "Müqaviləni vəkil <<Hüquqi Təminat Departamentinin>> adından imzalayıb.",
    "Qərarı sədr <<Direktorlar Şurasının>> iclasında elan edib.",
]
# a signature with only a title (and the letter's addressee, a real name)
SIGNATURE_ONLY_TITLES = ["Direktor", "Baş mühasib", "Komissiya katibliyi", "Şöbə müdiri",
                         "Kadrlar şöbəsi", "Mətbuat xidməti", "Müştəri xidmətləri"]
ADDRESSEE = ["Hörmətli {g} {s},", "Hörmətli {g} {h},"]   # {h}: xanım / bəy

# --------------------------------------------------------------------------- #
# 5. Short Ed25519 private keys (several in one document)
# --------------------------------------------------------------------------- #
KEY_SET_INTROS = [
    "Repozitoriyanın yoxlanışı zamanı bir neçə şəxsi açar tapılıb.",
    "Test serverinin konfiqurasiya qovluğunda aşağıdakı açarlar saxlanılır.",
    "Tərtibatçılar açarları iş yazışmasında paylaşıb.",
    "Köhnə deploy skriptlərində aşağıdakı açarlar aşkarlanıb.",
    "Təhlükəsizlik auditində tapılan açarlar aşağıda verilib.",
]

# --------------------------------------------------------------------------- #
# D-51i: the ordinal suffix after a spelled date's year goes outside the span
# (`12 mart 2016-cı il tarixində`), harmonised by `locales.az.year_suffix`
# --------------------------------------------------------------------------- #
YEAR_SUFFIX_RATE_NOTE = "quotas.json: fix_round.date_year_suffix_rate"


# --------------------------------------------------------------------------- #
# 10. TIME with seconds (v3_shadow_shapes.md lead 1; the team, 15 Oct):
#     `saat 14:05:22` in prose, `Saat: 14:05:22` fields, ranges
#     (`14:00:00-15:30:00`, `14:00:00 – 15:30`; both ends TIME, as R10), and in
#     the same document chat and log line stamps (`[14:05:22] Operator:`),
#     which stay unlabelled (D-51f)
# --------------------------------------------------------------------------- #
TIME_SECONDS_PROSE = [
    "Ödənişin təsdiqi sistemdə saat {v} olaraq qeyd olunub.",
    "Müraciət saat {v} olaraq sistemə daxil edilib.",
    "Jurnalda sonuncu girişin vaxtı saat {v} kimi göstərilib.",
    "Bağlamanın təhvil verildiyi an saat {v} kimi qeydə alınıb.",
    "Hesabatda əməliyyatın başlama vaxtı saat {v} olaraq yazılıb.",
    "Kameranın qeydində qapının açılma vaxtı saat {v} kimi əks olunub.",
    "Zəngin başlama vaxtı saat {v} olaraq qeyd edilib.",
    "Serverin yenidən işə düşmə vaxtı saat {v} kimi göstərilib.",
]
TIME_SECONDS_INTROS = [
    "Sistemin jurnalından çıxarış:",
    "Əməliyyatın təfərrüatları:",
    "Yoxlanılan qeydlər:",
    "Hadisənin qeydiyyat məlumatları:",
]
# `Saat` is the field the shadow shapes name; the builder takes it half the time
TIME_SECONDS_FIELDS = ["Saat", "Giriş saatı", "Qeydiyyat vaxtı", "Başlama vaxtı", "Bitmə vaxtı",
                       "Təsdiq saatı"]
TIME_RANGE_PROSE = [
    "Texniki işlər saat {r} aralığında aparılacaq.",
    "Sistem saat {r} arasında əlçatan olmayıb.",
    # v4.2 native review D: a shift is never written with seconds
    "Məlumatların köçürülməsi saat {r} aralığında aparılıb.",
    "Yükləmə prosesi {r} intervalında icra olunub.",
    "Xidmət saat {r} arasında dayandırılıb.",
]
# v4.2 native review D: work hours, shifts and office hours are never written
# with seconds; ranges with seconds are technical events (native check)
TIME_RANGE_FIELDS = ["Yeniləmə pəncərəsi", "Texniki fasilə", "Ehtiyat nüsxənin çıxarılması",
                     "Serverin dayanma müddəti", "Planlı dayanma"]
# v4.2 fix list (v41_shadow_shapes.md: 24 of v4.1's 51 TIME misses are
# followed by a dash): a range with the case endings outside the spans,
# `{r}` = `14:00:00-dan 15:30:00-dək` (native check)
TIME_RANGE_SUFFIX_PROSE = [
    "Texniki işlər saat {r} aparılacaq.",
    "Sistem saat {r} əlçatan olmayıb.",
    "Bazanın ehtiyat nüsxəsi saat {r} çıxarılıb.",
    "Xidmət {r} müvəqqəti dayandırılıb.",
    "Ödəniş sistemi saat {r} işləməyib.",
]
# an agenda: each line opens with a range, then the item. v4.2 native review C:
# a programme runs forward in time (each range starts where the last ended),
# opens with registration or the opening speech, closes with `Yekun söz`, and
# shows hh:mm, never seconds
TIME_AGENDA_INTROS = ["Tədbirin proqramı:", "İclasın gündəliyi:", "Seminarın proqramı:", "İş gününün cədvəli:"]
TIME_AGENDA_FIRST = ["Qeydiyyat", "Açılış nitqi"]
TIME_AGENDA_MIDDLE = ["Təqdimat", "Panel müzakirəsi", "Kofe fasiləsi", "Praktiki məşğələ", "Nahar fasiləsi",
                      "Komanda görüşü", "Sual-cavab"]          # in programme order
TIME_AGENDA_LAST = "Yekun söz"
TIME_AGENDA_ITEMS = TIME_AGENDA_FIRST + TIME_AGENDA_MIDDLE + [TIME_AGENDA_LAST]
# a real time inside a chat line, after a line stamp that is no TIME
TIME_SECONDS_CHAT = [
    "Ödənişiniz saat {v} olaraq qeydə alınıb.",
    "Sifarişiniz saat {v} olaraq sistemə daxil edilib.",
    "Müraciətiniz saat {v} kimi qeyd olunub.",
    "Sonuncu uğurlu girişiniz saat {v} kimi göstərilir.",
]
# the speakers are roles (v4_clean.CHAT_ROLES), never names, so R4 has nothing
# to label; no line says `saat`/`vaxt`, so R10 has nothing to label either
STAMP_ROLES = [("Operator", "Müştəri"), ("Agent", "Müştəri"), ("Dəstək", "İstifadəçi"),
               ("Operator", "İstifadəçi")]
# the first role of STAMP_ROLES speaks the agent lines, the second the customer's
STAMP_AGENT_LINES = [
    "Salam, sizə necə kömək edə bilərəm?",
    "Bir dəqiqə, məlumatı yoxlayıram.",
    "Problem həll olundu, başqa sualınız var?",
    "Sorğunuz texniki şöbəyə yönləndirildi.",
    "Gözlədiyiniz üçün təşəkkür edirik.",
]
STAMP_CUSTOMER_LINES = [
    "Sifarişimin statusunu öyrənmək istəyirəm.",
    "Təşəkkür edirəm, gözləyirəm.",
    "Xeyr, hər şey aydındır.",
    "Ödəniş keçmədi, səbəbini bilmək istəyirəm.",
    "Tətbiqə daxil ola bilmirəm.",
]
STAMP_LOG_LINES = [
    ("INFO", "istifadəçi sessiyası başladı"),
    ("INFO", "sorğu uğurla emal olundu"),
    ("INFO", "konfiqurasiya yeniləndi"),
    ("DEBUG", "keş təmizləndi"),
    ("WARN", "cavab gecikdi, təkrar cəhd edilir"),
    ("WARN", "bağlantı yenidən quruldu"),
    ("ERROR", "verilənlər bazasına qoşulmaq alınmadı"),
]


# --------------------------------------------------------------------------- #
# 11. Private-key blocks with a placeholder or redacted body (v4.1, A5; v3
#     shapes lead 5): no key, so unlabelled; often beside a real key
# --------------------------------------------------------------------------- #
# The native review of #90 (A, B): the intro, the body and the closing
# sentence tell one story -- the key was REMOVED from the document, or this is
# a TEMPLATE with an empty place for it. "any" fits both.
KEY_PLACEHOLDER_INTRO_STORY = {
    "Konfiqurasiya nümunəsində açarın yeri boş qoyulub:": "template",
    "Təhlükəsizlik səbəbindən açarın məzmunu sənəddən silinib:": "removed",
    "Şablonda gizli açarın yeri belə göstərilib:": "template",
    "Hesabata əlavə edilən açarın məzmunu gizlədilib:": "removed",
    "Təlimatda açarın formatı nümunə kimi verilib:": "template",
    "Müraciətə əlavə olunan faylda açarın məzmunu göstərilməyib:": "any",
}
KEY_PLACEHOLDER_INTROS = list(KEY_PLACEHOLDER_INTRO_STORY)
# said only when no real key is written in the same document
KEY_PLACEHOLDER_AFTER_STORY = {
    "Açarın özü yalnız serverdə saxlanılır.": "any",
    "Açarı bu sahəyə özünüz daxil etməlisiniz.": "template",
    "Məzmun məxfi olduğu üçün göstərilmir.": "removed",
}
KEY_PLACEHOLDER_AFTER = list(KEY_PLACEHOLDER_AFTER_STORY)
KEY_PLACEHOLDER_HEADERS = ("PRIVATE KEY", "RSA PRIVATE KEY", "EC PRIVATE KEY", "OPENSSH PRIVATE KEY",
                           "ENCRYPTED PRIVATE KEY")
KEY_PLACEHOLDER_BODY_STORY = {
    "removed": ("[REDACTED]", "[GİZLƏDİLİB]", "***", "(məzmun silinib)", "...gizlədilib..."),
    "template": ("<gizli açar>", "<private key>", "<açarı bura daxil edin>"),
    "both": ("...", "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"),
}
KEY_PLACEHOLDER_BODIES = tuple(b for bodies in KEY_PLACEHOLDER_BODY_STORY.values() for b in bodies)


# --------------------------------------------------------------------------- #
# 12. Lines opened by a capitalised word (v4.1, A5; v3 shapes lead 5, part 3):
#     a role or heading word (unlabelled) or a real given name (labelled),
#     then a colon. The utterances are STAMP_AGENT_LINES / STAMP_CUSTOMER_LINES.
#     No word here is in a name or place pool (`Katib`, `Diqqət`, `Rəhbər` and
#     `Həkim` are, so they are left out; test_builder checks it)
# --------------------------------------------------------------------------- #
LINE_START_INTROS = [
    "Söhbətin qeydi:",
    "Dəstək xidməti ilə yazışmadan çıxarış:",
    "Müraciət üzrə yazışma:",
    "Zəngin qısa qeydi:",
]
LINE_START_ROLES = ["Operator", "Müştəri", "Dəstək", "Menecer", "Kuryer", "Mühasib", "Kassir",
                    "Direktor", "Satıcı", "Texnik"]
# The native review of #90 (C): every speaker gets a line that fits.
# `Müştəri` speaks the customer's lines, the support roles the agent's
# (STAMP_AGENT_LINES), these four their own
LINE_START_AGENT_ROLES = ("Operator", "Dəstək", "Menecer", "Satıcı", "Texnik")
LINE_START_CUSTOMER_ROLES = ("Müştəri",)
LINE_START_OWN_LINES = {
    "Kuryer": ["Sifarişi sabah günortaya qədər çatdıracağam.", "Ünvana çatmışam, qapını açan yoxdur."],
    "Mühasib": ["Ödəniş hələ hesabımıza daxil olmayıb.", "Hesab-fakturanı bu gün göndərəcəyik."],
    "Direktor": ["Bu məsələni sabahkı iclasda müzakirə edək.", "Təklifi təsdiq edirəm."],
    "Kassir": ["Çekinizi yoxlayıram, bir dəqiqə.", "Ödəniş qəbul olundu."],
}
LINE_START_HEADINGS = {
    "Qeyd": "sənəd yenidən yoxlanılmalıdır.",
    "Nəticə": "müraciət təmin olunub.",
    "Səbəb": "ödəniş sistemində texniki nasazlıq.",
    "Təklif": "sifarişi növbəti həftəyə keçirmək.",
    "Cavab": "məsələ araşdırılır.",
    "Mövzu": "çatdırılmanın gecikməsi.",
    "Qərar": "son tarix dəyişdirilib.",
    "Status": "gözləmədə.",
}


# --------------------------------------------------------------------------- #
# 13. Bare ZIPs after a town, no index word (v4.1 A5; v3 shapes lead 3). Moved
#     from builder.py so the native check lists them (review)
# --------------------------------------------------------------------------- #
POSTAL_BARE_SENTENCES = [
    "Bağlama {t}, {z} ünvanına göndərilib.",
    "Göndərilmə ünvanı: {t} şəhəri, {z}.",
    # The native review of #90 (G): not `Sifariş {t}; {z}; Azərbaycan ünvanına ...`
    "Çatdırılma ünvanı: {t}; {z}; Azərbaycan.",
    "Məktub {t} — {z} ünvanına yollanıb.",
    "Filialımız {t}, {z} ünvanında yerləşir.",
    "Qaimədə alıcının ünvanı {t}, {z} kimi yazılıb.",
    "Kuryer sabah {t}, {z} ünvanına gedəcək.",
    "Hesab-faktura {t} - {z} ünvanına yönləndirilib.",
]


# --------------------------------------------------------------------------- #
# 14. v4.1 fix list (#91, D-52b)
# --------------------------------------------------------------------------- #
# item 5 (C3): beside a licence/ID-card pair, a line whose context word says
# nothing (1 : 1 for each label), and a line whose context word disagrees with
# the shape -- the length decides (D-34d: licence 2 letters + 6 digits, ID card
# 2 letters + 7), about 300 each way per 25,000 documents
LICENCE_ID_GENERIC = [
    "Sənədin nömrəsi: {v}",
    "Təqdim olunan sənədin nömrəsi {v} kimi qeyd olunub.",
    "Yoxlanılan sənəd: {v}",
]
# D-56a (3): ID cards (AA + 7 digits) after short ID words, beside licences
# after the same words, 1 : 1, so the length decides (D-34d). Our own
# wording, not the benchmark frames (native check)
SHORT_ID_LINES = [
    "ID nömrəsi: {v}",
    "ID: {v}",
    "Müştərinin ID nömrəsi {v} kimi göstərilib.",
    "Mənim ID nömrəm {v}, yoxlaya bilərsiniz.",
    "Formada ID nömrəsi {v} olaraq doldurulub.",
]
LICENCE_ID_DISAGREE_FIELDS = {
    # the field names the OTHER document; the value's shape decides the label
    "AZ_ID_CARD_NUMBER": ["Sürücülük vəsiqəsi", "Sürücülük vəsiqəsinin nömrəsi"],
    "AZ_DRIVER_LICENSE_NUMBER": ["Şəxsiyyət vəsiqəsi", "Şəxsiyyət vəsiqəsinin nömrəsi"],
}
# item 1(b, c): a real IPv6, IPv4 or MAC in log/record prose, in a document
# that also holds unlabelled dotted codes (versions, clause numbers). Our own
# frames, not the benchmark's
NET_PROSE = {
    "IPV6_ADDRESS": [
        "Monitorinq sistemində qovşağın ünvanı {v} kimi yazılıb.",
        "Sorğunun mənbə ünvanı jurnalda {v} olaraq qeyd olunub.",
        "Xəta baş verən serverin ünvanı {v} kimi göstərilib.",
        "Qoşulma {v} ünvanından həyata keçirilib.",
    ],
    "IPV4_ADDRESS": [
        "Firewall jurnalında bloklanan IP ünvanı {v} kimi qeyd olunub.",
        "Hesabatda giriş edilən IP {v} olaraq yazılıb.",
        "Server {v} ünvanından gələn sorğunu rədd edib.",
    ],
    "MAC_ADDRESS": [
        "Şəbəkəyə qoşulan cihazın fiziki ünvanı {v} kimi qeyd olunub.",
        "Avadanlığın MAC ünvanı inventar siyahısında {v} olaraq yazılıb.",
    ],
}
NET_CODE_KINDS = ("date_version_string", "date_clause_number", "campaign_code", "archive_folder")
# D-56a (1): v4.1 split IPs whose sentence or line has no final period (every
# IP the targeted data added ended with `.`). Chat lines and log lines that end
# on the value; our own wording, not the probes' (native check)
NET_CHAT_LINES = {
    "IPV4_ADDRESS": ["Müştəri: kompüterimin IP ünvanı {v}", "Operator: sizin cari IP ünvanınız {v}",
                     "Texnik: routerin xarici ünvanı {v}", "Müştəri: sistem məni bu ünvanla göstərir {v}"],
    "IPV6_ADDRESS": ["Texnik: cihazın yeni ünvanı {v}", "Operator: bağlantınızın ünvanı {v}",
                     "Müştəri: modemdə yazılan ünvan {v}"],
    "MAC_ADDRESS": ["Texnik: kartın MAC ünvanı {v}", "Müştəri: modemin arxasında yazılan MAC {v}"],
}
NET_LOG_LINES = {
    "IPV4_ADDRESS": ["INFO  sessiya açıldı, mənbə {v}", "WARN  çoxsaylı uğursuz giriş cəhdi, IP {v}",
                     "ERROR bağlantı rədd edildi: {v}"],
    "IPV6_ADDRESS": ["INFO  yeni qoşulma, ünvan {v}", "WARN  cavab gecikir, qovşaq {v}"],
    "MAC_ADDRESS": ["INFO  cihaz qeydiyyatdan keçdi, MAC {v}", "WARN  naməlum cihaz, MAC {v}"],
}
NET_CHAT_INTROS = ["Dəstək çatından çıxarış:", "Söhbətin qeydi:"]
NET_LOG_INTROS = ["Server jurnalından çıxarış:", "Jurnal qeydləri:"]
# item 6: real ZIPs right after the word ZIP / poçt kodu
POSTAL_ZIP_WORD_SENTENCES = [
    "Formada ZIP {z} kimi göstərilib.",
    "Bağlamanın ZIP kodu {z} olaraq yazılıb.",
    "Sistemdə poçt kodu {z} kimi qeyd olunub.",
    "Alıcının ünvan sətrində ZIP {z} kimi qeyd edilib.",
]


def native_check_list() -> list[tuple[str, str]]:
    """(pool, sentence) for every sentence and word list in this module, for
    The native check."""
    out: list[tuple[str, str]] = []

    def add(pool: str, items) -> None:
        out.extend((pool, s) for s in items)

    for name in ("SHORT_BOTH", "SHORT_ONLY", "NAME_SLOT", "LOCATIVE", "SLOT_PROSE", "PLACE_VERBS"):
        for key, items in globals()[name].items():
            add(f"{name}[{key}]", items)
    for name in ("IPV4_LOOKALIKE", "RECORD_INTROS", "ROOM_CODE", "DOOR_CODE", "MAC_FRAGMENT", "MAC_REAL",
                 "IBAN_FRAGMENT", "IBAN_REAL", "IPV4_BOTH", "IPV4_PLACEHOLDER", "ZIP_RIGHT",
                 "SURNAME_ABLATIVE", "CONTROL_DEPARTMENTS", "CONTROL_POSITIONS",
                 "CONTROL_DOCUMENTS", "CONTROL_ORGS", "ROLE_CONTROL_SENTENCES",
                 "SIGNATURE_ONLY_TITLES", "ADDRESSEE", "KEY_SET_INTROS",
                 "TIME_SECONDS_PROSE", "TIME_SECONDS_INTROS", "TIME_SECONDS_FIELDS",
                 "TIME_RANGE_PROSE", "TIME_RANGE_FIELDS", "TIME_SECONDS_CHAT",
                 "STAMP_AGENT_LINES", "STAMP_CUSTOMER_LINES", "KEY_PLACEHOLDER_INTROS",
                 "KEY_PLACEHOLDER_AFTER", "KEY_PLACEHOLDER_BODIES", "LINE_START_INTROS",
                 "LINE_START_ROLES", "POSTAL_BARE_SENTENCES", "LICENCE_ID_GENERIC",
                 "POSTAL_ZIP_WORD_SENTENCES", "TIME_RANGE_SUFFIX_PROSE", "TIME_AGENDA_INTROS",
                 "NET_CHAT_INTROS", "NET_LOG_INTROS", "SHORT_ID_LINES",
                 "TIME_AGENDA_ITEMS"):
        add(name, globals()[name])
    add("RECORD_HEADS", [f"{a} / {b}" for a, b in RECORD_HEADS])
    add("RECORD_STATUS", RECORD_STATUS)
    add("ZIP_TAILS", [t.strip() for t in ZIP_TAILS])
    add("STAMP_LOG_LINES", [f"{lvl} {msg}" for lvl, msg in STAMP_LOG_LINES])
    add("LINE_START_HEADINGS", [f"{k}: {v}" for k, v in LINE_START_HEADINGS.items()])
    add("LICENCE_ID_DISAGREE_FIELDS", [f for fs in LICENCE_ID_DISAGREE_FIELDS.values() for f in fs])
    for key, items in NET_PROSE.items():
        add(f"NET_PROSE[{key}]", items)
    for key, items in NET_CHAT_LINES.items():
        add(f"NET_CHAT_LINES[{key}]", items)
    for key, items in NET_LOG_LINES.items():
        add(f"NET_LOG_LINES[{key}]", items)
    add("LINE_START_OWN_LINES", [f"{k}: {v}" for k, vs in LINE_START_OWN_LINES.items() for v in vs])
    add("CONTROL_LISTS", list(CONTROL_LISTS))
    return out
