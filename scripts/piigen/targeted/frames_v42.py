"""Sentences of the v4.2 final fix list (D-57, 20 Oct).

Data only; the families that write them are in `builder.py`. The pools follow
the v4.2 fix list (Must M1-M7, Should S1-S7) and the v4.1 shadow-shape analysis. Shadow and real
text were described there only by counts and abstract formats; every sentence
here is our own, written for the general rule, never a probe, benchmark or
shadow sentence. All are for the native check (`native_check_list()`).

Rules the sentences keep (as frames_v4.py does):
  * no digits in a fixed sentence: a digit would be an unlabelled number in
    every document that uses it (the numbers of the business documents are
    drawn, never written into a frame);
  * `{v}` is the value (a real one or a look-alike);
  * no judgement words (`səhv`, `yanlış`, ...): the quality gate rejects a
    sentence that calls a look-alike wrong (llm/quality.LEAK_WORDS).
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# S1. A bare 2-digit age after an ordinary lowercase word, mostly with no
#     `yaş` right after it; the age word sits elsewhere in the sentence (AGE
#     needs it within 80 characters, anchors/az.py). Each pair: the real
#     sentence, and the same sentence where the number is something else (a
#     score, a queue number, months of work, a pulse, a weight).
# --------------------------------------------------------------------------- #
# (real sentence, look-alike sentence, the age's range, the look-alike's range):
# each number fits its sentence (`o hələ {v}` is young, a pulse is 55-99)
AGE_PAIRS = [
    ("Yaşını soruşduqda müştəri {v} dedi, sonra sənədlərini təqdim etdi.",
     "Növbəsini soruşduqda müştəri {v} nömrəli talonu göstərdi, sonra sənədlərini təqdim etdi.", (18, 80), (10, 99)),
    ("Anketin yaş sütununda iştirakçı {v} yazıb, digər sahələr boş qalıb.",
     "Anketin bal sütununda iştirakçı {v} yazıb, digər sahələr boş qalıb.", (16, 75), (10, 99)),
    ("Sığorta haqqı yaşa görə hesablanır: sığortalı {v}, buna görə məbləğ dəyişməyib.",
     "Sığorta haqqı staja görə hesablanır: sığortalı {v} ay işləyib, buna görə məbləğ dəyişməyib.", (18, 70), (10, 60)),
    ("Qeydiyyatda yaşını soruşdular, qızım {v} deyib cavab verdi.",
     "Qeydiyyatda çəkisini soruşdular, qızım {v} kiloqram deyib cavab verdi.", (10, 35), (25, 70)),
    ("Həkim pasiyentin yaşını tibbi kartına yazıb: kişi, {v}, şikayəti yoxdur.",
     "Həkim pasiyentin nəbzini tibbi kartına yazıb: dəqiqədə {v}, şikayəti yoxdur.", (18, 89), (55, 99)),
    ("Namizədin yaşı şərtə uyğundur, o hələ {v}, amma təcrübəsi böyükdür.",
     "Namizədin stajı şərtə uyğundur, o artıq {v} aydır işləyir, təcrübəsi böyükdür.", (19, 29), (12, 48)),
    ("Yaş həddinə görə idmançı {v} olduğu üçün böyüklər yarışına buraxılıb.",
     "Reytinqə görə idmançı {v} xal topladığı üçün böyüklər yarışına buraxılıb.", (18, 25), (10, 99)),
    ("Sorğuda yaş da qeyd olunub: respondent {v}, ali təhsillidir.",
     "Sorğuda sıra nömrəsi də qeyd olunub: respondent {v}, ali təhsillidir.", (21, 80), (10, 99)),
]
# a second real age in the same document, no look-alike beside it: (sentence, range)
AGE_REAL_MORE = [
    ("Ailədə yaş fərqi böyükdür: qardaşım {v}, bacım isə hələ məktəblidir.", (25, 45)),
    ("Pasportda doğulduğu il göstərilib, yəni o indi {v}.", (16, 89)),       # the team, F: no comma
    ("Təqaüdə çıxanda atam {v} idi, yaşına görə güzəşt alırdı.", (55, 70)),
    ("Klubun ən yaşlı üzvü {v}, amma hər səhər qaçışa çıxır.", (60, 89)),
    ("Yaşını soruşanda nənəm gülərək {v} dedi.", (60, 95)),
    ("Yaş məhdudiyyəti olsa da, iştirakçı cəmi {v}, buna görə valideyni ilə gəlib.", (12, 17)),
]

# --------------------------------------------------------------------------- #
# M3. FIN look-alikes BEFORE the word (`... {v} FİN-i ...`), the value before
#     its noun like the other `noun` pairs: once a real FIN, once a look-alike
# --------------------------------------------------------------------------- #
NOUN_FIN = [
    "{v} FİN-i ilə qeydiyyatdan keçən şəxs ərizə təqdim edib.",
    "Sistem {v} FİN kodu üzrə məlumatı tapıb.",
    "Ərizəçi portala {v} FİN kodu ilə daxil olub.",
    "Arayış {v} FİN-li vətəndaşa verilib.",
    "Sorğu {v} FİN kodu üzrə yenidən göndərilib.",
]
# M4. Dates before `tarixli` (the `noun` pairs already hold `tarixində`,
#     `tarixindən`, `tarixinə qədər`)
NOUN_DATE_TARIXLI = [
    "Bank {v} tarixli çıxarışı təqdim edib.",
    "Şirkət {v} tarixli məktubla cavab verib.",
    "Ərizəyə {v} tarixli arayış əlavə olunub.",
    "Komissiya {v} tarixli protokolu təsdiqləyib.",
]

# --------------------------------------------------------------------------- #
# S3. A real city right after an opening bracket or quote, and an
#     organisation or brand built from a town word in quotes, unlabelled (D-2,
#     D-57). The same index: the decoy sentence and its valid twin.
# --------------------------------------------------------------------------- #
CITY_BRAND_DECOY = [
    "Müqavilə «{v}» MMC ilə bağlanıb.",
    "Sifariş \"{v}\" mağazasından gəlib.",
    "Tenderdə «{v}» ASC qalib gəlib.",
    "Məhsullar «{v}» şirkətinin anbarından göndərilib.",
    "Reklam «{v}» brendi üçün hazırlanıb.",
]
CITY_BRAND_VALID = [
    "Müqavilə şirkətin regional ofisi ({v}) ilə bağlanıb.",
    "Bağlamanın etiketində şəhər kimi \"{v}\" yazılıb.",
    "Tenderin qalibi bu dəfə bölgədən ({v}) olan şirkət olub.",
    # The review, B: not after `anbarından` (it reads as the warehouse's
    # name, an organisation, D-2), and no quotes inside brackets
    "Qaimədə yükün göndərildiyi şəhər «{v}» kimi yazılıb.",
    "Reklam ilk olaraq bir şəhərdə ({v}) sınaqdan keçiriləcək.",
]

# --------------------------------------------------------------------------- #
# S4. Building numbers: `ev {v}`, a street name then the number, and
#     `Bina: {v}` lines beside a room / floor / office line (unlabelled)
# --------------------------------------------------------------------------- #
BUILDING_LINES_INTROS = [
    "Görüşün keçiriləcəyi yer:",
    "Çatdırılma ünvanı:",
    "Ofisin yeni ünvanı:",
    "Kuryer üçün qeyd:",
]
# the room / floor / office line's field, by look-alike kind
BUILDING_LINE_FIELDS = {"room_number": "Otaq", "floor_number": "Mərtəbə", "office_number": "Kabinet"}

# --------------------------------------------------------------------------- #
# S2. ALL-CAPS headers, form fields and stamps. Field names are written in
#     capitals by `az_upper`; a heading word alone on its line is a control
#     (unlabelled), checked against every name and place pool
# --------------------------------------------------------------------------- #
CAPS_HEADINGS = ["ƏRİZƏ", "ARAYIŞ", "MÜQAVİLƏ", "BİLDİRİŞ", "QƏBZ", "AKT", "PROTOKOL", "HESABAT",
                 "SƏRƏNCAM", "TƏQDİMAT", "XASİYYƏTNAMƏ", "ETİBARNAMƏ", "QAİMƏ", "ANKET"]
CAPS_FIELDS = {
    "SURNAME": ["Soyadı", "Soyad"],
    "GIVENNAME": ["Adı", "Ad"],
    "FATHER": ["Atasının adı"],
    "CITY": ["Doğulduğu şəhər", "Yaşadığı şəhər", "Şəhər", "Qeydiyyat yeri"],
    "AZ_ID_CARD_NUMBER": ["Şəxsiyyət vəsiqəsinin nömrəsi"],
    "AZ_DRIVER_LICENSE_NUMBER": ["Sürücülük vəsiqəsinin nömrəsi"],
}
# The review, H: the `… ŞƏHƏRİ` header only with a town that is a city
# (not `Binəqədi`, `Lökbatan`, `Mərdəkan`, `Qırmızı Bazar`: settlements). The
# cities with city status and the district centres; the rest of the town list
# still fills the form's town fields
CAPS_HEADER_CITIES = [
    "Bakı", "Gəncə", "Sumqayıt", "Mingəçevir", "Şirvan", "Naxçıvan", "Lənkəran", "Şəki", "Yevlax",
    "Naftalan", "Xankəndi", "Xırdalan", "Quba", "Qusar", "Xaçmaz", "Şamaxı", "Şəmkir", "Tovuz", "Qazax",
    "Ağstafa", "Zaqatala", "Balakən", "Qax", "Qəbələ", "İsmayıllı", "Göyçay", "Ağdaş", "Bərdə", "Tərtər",
    "Ağcabədi", "Salyan", "Sabirabad", "Saatlı", "İmişli", "Beyləqan", "Füzuli", "Cəlilabad", "Masallı",
    "Astara", "Lerik", "Yardımlı", "Biləsuvar", "Neftçala", "Kürdəmir", "Ucar", "Zərdab", "Hacıqabul",
    "Siyəzən", "Şabran", "Gədəbəy", "Daşkəsən", "Goranboy", "Göygöl", "Oğuz", "Ordubad", "Culfa", "Şərur",
    "Şuşa", "Laçın", "Kəlbəcər", "Ağdam", "Cəbrayıl", "Zəngilan", "Qubadlı", "Xocalı",
]
# a sentence after the form, in ordinary case
CAPS_AFTER = [
    "Sənəd iki nüsxədə tərtib olunub.",
    "Ərizəyə baxılması üçün sənədlərin əsli təqdim edilməlidir.",
    "Məlumatların düzgünlüyünə ərizəçi cavabdehdir.",
    "Forma çap hərfləri ilə doldurulub.",
    "Blank möhürlə təsdiqlənib.",
]
CAPS_INTROS = [
    "Formanın surəti aşağıdadır:",
    "Arxivdən çıxarılmış blankın mətni:",
    "Skan edilmiş sənəddən köçürülmüş məlumat:",
    "Ərizə blankı belə doldurulub:",
]

# --------------------------------------------------------------------------- #
# M6 / M7. Beside a real IPv6 and MAC (contrast ipv6_mac): an IPv6 look-alike
#     with `::`, another real compressed IPv6 (mid-sentence or after a label),
#     a letter-pair MAC look-alike
# --------------------------------------------------------------------------- #
IPV6_LOOKALIKE = [
    "Köhnə konfiqurasiya faylında ünvan kimi {v} qalıb.",
    "Təlimatdakı nümunədə ünvan {v} şəklində verilib.",
    "Monitorinq paneli {v} sətrini ünvan kimi tanımayıb.",
    "Sənədin qaralamasında şəbəkə ünvanı {v} kimi yazılıb.",
]
IPV6_REAL_PROSE = [
    "Qovşağın ehtiyat IPv6 ünvanı {v} olaraq təyin edilib.",
    "Server yeni {v} ünvanından cavab verir.",
    "Marşrutlaşdırma cədvəlinə {v} ünvanı əlavə olunub.",
    "Monitorinq sistemi {v} ünvanlı qovşağı izləyir.",
]
IPV6_REAL_FIELDS = ["IPv6 ünvanı", "IPv6", "Ehtiyat IPv6 ünvanı"]
MAC_LETTERS = [
    "Şablonda MAC ünvanının yerinə {v} yazılıb.",
    "Təlimatda MAC ünvanı nümunə kimi {v} şəklində göstərilib.",
    "Formanın MAC sahəsində doldurulmamış {v} işarəsi qalıb.",
]

# --------------------------------------------------------------------------- #
# M5 / M7 / S5. Extra `Field: value` lines in a `form` document: a real value
#     after its field, and beside it a look-alike of the same label
# --------------------------------------------------------------------------- #
FORM_EXTRA_FIELDS = {
    "AZ_VOEN": ["VÖEN", "VÖEN nömrəsi", "Vergi ödəyicisinin VÖEN-i"],
    "AZ_PASSPORT_NUMBER": ["Pasport", "Pasportun nömrəsi", "Xarici pasportun nömrəsi"],
}

# --------------------------------------------------------------------------- #
# M1. Near misses in PII-free documents: the field of a `Field: value` line
# --------------------------------------------------------------------------- #
PF_NEAR_FIELDS = {
    "date": ["Sənədin tarixi", "Növbəti yoxlama", "Etibarlılıq müddəti", "Plan tarixi", "Tarix"],
    "iban_short": ["Hesab kodu", "Daxili hesab", "Hesab nömrəsi"],
    "iban_bare": ["Ölkə kodu", "Ölkə"],
    "licence3": ["Sənədin kodu", "Qeydiyyat kodu", "Sürücülük vəsiqəsi"],
    "time_near": ["Başlama vaxtı", "Saat", "Bitmə vaxtı"],
    "cvv2": ["CVV", "CVC"],
    "ipv6_bad": ["IPv6", "Server ünvanı"],
    "voen9": ["VÖEN", "Vergi nömrəsi"],
}

# --------------------------------------------------------------------------- #
# S5 / S6. Real values the new look-alikes must not teach the model to miss
# --------------------------------------------------------------------------- #
RECALL = {
    # S5: an access token in prose
    "token_prose": [
        "Mobil tətbiq serverə {v} tokeni ilə qoşulub.",
        "Sorğuda istifadəçinin access token dəyəri {v} olaraq göndərilib.",
        "Sessiya üçün yeni token {v} yaradılıb və tətbiqə ötürülüb.",
        "Avtorizasiya {v} tokeni ilə uğurla tamamlanıb.",
    ],
    # S5: a CVV and a card mid-sentence
    "cvv_mid": [
        "Müştəri onlayn ödənişdə CVV kodu kimi {v} daxil edib.",
        "Kartın CVC kodu {v} sistemdə maskalanmadan saxlanılıb.",
        "Sifariş zamanı təhlükəsizlik kodu {v} ikinci dəfə tələb olunub.",
        "Ödəniş səhifəsində CVV2 kodu {v} avtomatik doldurulub.",
    ],
    "card_mid": [
        "Ödəniş {v} nömrəli kartdan uğurla tutulub.",
        "Müştəri abunə haqqını {v} kartı ilə ödəyib.",
        "Geri qaytarma {v} kartına həyata keçiriləcək.",
        "Bank {v} kartını müvəqqəti bloklayıb.",
    ],
    # S6: a real time in `saat X radələrində`
    "time_radelerinde": [
        "Kuryer saat {v} radələrində ünvana çatıb.",
        "Zəng saat {v} radələrində daxil olub.",
        "Sistem saat {v} radələrində yenidən işə düşüb.",
        "Görüş saat {v} radələrində başlayıb.",
    ],
    # S6: real 23:5x and 00:0x times
    "time_edge": [
        "Sonuncu ödəniş saat {v} olaraq qeydə alınıb.",
        "Mağaza gecə saat {v} bağlanıb.",
        "Sistem gecə saat {v} yenilənib.",
        "Sifariş saat {v} olaraq qəbul edilib.",
    ],
    # S6, D-57: `24:00` is a real time (the end of a day), labelled
    "time_2400": [
        "Xidmət hər gün saat {v}-dək işləyir.",
        "Ərizələr saat {v}-dək qəbul olunur.",
        "Endirim gecə saat {v}-dək davam edəcək.",
        "Növbətçi aptek saat {v}-dək açıqdır.",
    ],
    # S6: a real 29 February in a leap year
    "feb29": [
        "Müqavilə {v} tarixində imzalanıb.",
        "Ödəniş {v} tarixində həyata keçirilib.",
        "Ərizə {v} tarixində qəbul edilib.",
        "Arayış {v} tarixində verilib.",
    ],
    # D-57's last rule (no real-value count goes down against v4.2): values
    # that open a line, and a key after a colon on its line
    "card_line": [
        "{v} kartı müştərinin profilinə əlavə olunub.",
        "{v} nömrəli kartla ödəniş təsdiqlənib.",
        "{v} kartı üzrə limit artırılıb.",
    ],
    "iban_line": [
        "{v} nömrəli hesab aktivdir.",
        "{v} hesabı üzrə çıxarış hazırlanıb.",
        "{v} hesabına vəsait daxil olub.",
    ],
    "key_inline": [
        "Konfiqurasiya faylında şəxsi açar: {v}",
        "Jurnala düşən şəxsi açar: {v}",
    ],
    "id_line": [
        "{v} nömrəli şəxsiyyət vəsiqəsi təqdim olunub.",
        "{v} saylı vəsiqə ilə qeydiyyat aparılıb.",
    ],
    "surname_line": [
        "{v} ailəsi yeni ünvana köçüb.",
        "{v} soyadlı müştərinin müraciəti qeydə alınıb.",
    ],
    # S4 too: a building number after an ordinary word. The review, C:
    # an address is never only a house number, and an office is not in a house
    "building_word": [
        "Ünvanda küçənin adı və ev {v} göstərilib.",
        "Yeni filial üçün həmin küçədə bina {v} icarəyə götürülüb.",
        "Ərizəçi qeydiyyat vərəqəsində mənzil {v} göstərib.",
        "Toplantı bina {v}, üçüncü mərtəbədəki ofisdə keçiriləcək.",
    ],
}
# the field of a `Field: value` line in a recall document
RECALL_FIELDS = {"IPV4_ADDRESS": ["IP ünvanı", "Serverin IP ünvanı", "Mənbə IP"],
                 "MAC_ADDRESS": ["MAC ünvanı", "Cihazın MAC ünvanı"],
                 "CITY": ["Şəhər", "Yaşadığı şəhər"],
                 "SURNAME": ["Soyad", "Soyadı"],
                 "GIVENNAME": ["Ad", "Adı"],
                 "API_KEY": ["API açarı", "İnteqrasiya açarı"],
                 "AZ_FIN": ["FİN", "FİN kodu"]}

# --------------------------------------------------------------------------- #
# M2 + item 5. Business-like PII-free documents: price lists, stock tables,
#     version histories, meeting notes without people, technical specs, and
#     geography / route / region texts dense with place-like words (none in a
#     city, settlement or name pool; the builder screens them)
# --------------------------------------------------------------------------- #
BIZ_TITLES = {
    "price_list": ["Qiymət siyahısı", "Məhsulların qiymət cədvəli", "Topdan satış qiymətləri"],
    "stock": ["Anbar qalığı", "Anbar hesabatı", "Mal qalıqlarının siyahısı"],
    "versions": ["Versiya tarixçəsi", "Buraxılış qeydləri", "Proqram təminatının dəyişiklikləri"],
    "meeting": ["İclas protokolu", "Şöbələrarası görüşün qeydləri", "İşçi qrupunun yekun qeydləri"],
    "spec": ["Texniki göstəricilər", "Məhsulun texniki xüsusiyyətləri", "Avadanlığın pasport məlumatları"],
    "geography": ["Coğrafiya dərsi üçün qeydlər", "Nəqliyyat dəhlizləri haqqında arayış", "Regional icmal"],
}
BIZ_INTROS = {
    "price_list": ["Anbarda olan məhsulların cari qiymətləri aşağıdakı cədvəldə verilib:",
                   "Qiymətlərə əlavə dəyər vergisi daxildir:",
                   "Sifariş verərkən məhsulun kodunu göstərmək xahiş olunur:"],
    "stock": ["Ay sonuna olan qalıqlar aşağıdakı cədvəldə göstərilib:",
              "Minimum həddən aşağı düşən mallar ayrıca qeyd olunub:",
              "Anbarlar üzrə qalıqlar yoxlanılıb və cədvələ köçürülüb:"],
    "versions": ["Sistemin son buraxılışlarında edilən dəyişikliklər:",
                 "Hər buraxılışda əlavə olunan funksiyalar aşağıda sadalanıb:",
                 "Komanda tərəfindən hazırlanan yeniliklərin siyahısı:"],
    "meeting": ["İclasda şöbələrin nümayəndələri iştirak edib.",
                "Görüşdə cari layihələrin vəziyyəti müzakirə olunub.",
                "İşçi qrupu aşağıdakı məsələlərə baxıb."],
    "spec": ["Məhsulun əsas texniki göstəriciləri aşağıda verilib:",
             "Avadanlığın istismarı üçün vacib parametrlər:",
             "Satış üçün təqdim olunan modelin xüsusiyyətləri:"],
}
BIZ_OUTROS = {
    "price_list": ["Qiymətlər növbəti siyahı dərc olunana qədər qüvvədədir.",
                   "Böyük sifarişlər üçün əlavə endirim mümkündür.",
                   "Çatdırılma xərci qiymətə daxil deyil."],
    "stock": ["Qalıqlar növbəti inventarizasiyada yenidən yoxlanılacaq.",
              "Minimum həddən aşağı olan mallar üçün sifariş hazırlanır.",
              "Hesabat maliyyə şöbəsinə göndərilib."],
    "versions": ["Növbəti buraxılışda hesabat modulunun yenilənməsi planlaşdırılır.",
                 "Köhnə versiyalar üçün dəstək mərhələli şəkildə dayandırılacaq.",
                 "Dəyişikliklər test mühitində yoxlanılıb."],
    "meeting": ["Növbəti iclasda qərarların icrası yoxlanılacaq.",
                "Protokol bütün şöbələrə göndərilib.",
                "Təkliflər iki həftə ərzində yazılı şəkildə təqdim olunmalıdır."],
    "spec": ["Zəmanət yalnız rəsmi servis mərkəzində qüvvədədir.",
             "Texniki göstəricilər istehsalçı tərəfindən xəbərdarlıqsız dəyişdirilə bilər.",
             "Avadanlıq quru və havalandırılan yerdə saxlanılmalıdır."],
    "geography": ["Məlumatlar dərslik və açıq mənbələr əsasında hazırlanıb.",
                  "Mövzu növbəti dərsdə xəritə üzərində təkrarlanacaq.",
                  "Arayış tələbələrin sərbəst işi üçün nəzərdə tutulub."],
}
BIZ_PRODUCTS = ["A4 kağız", "Printer kartrici", "Ofis stulu", "Yazı masası", "Qovluq", "Çay dəsti",
                "Su qızdırıcısı", "Elektrik çaydanı", "Monitor", "Klaviatura", "Kabel", "Lampa",
                "Boya", "Sement", "Kərpic", "Plitə", "Şüşə qab", "Dəftər", "Qələm", "Zımba"]
BIZ_UNITS = ["ədəd", "qutu", "kq", "litr", "paket", "metr"]
BIZ_STORES = ["Mərkəzi anbar", "Şimal anbarı", "Cənub anbarı", "Ehtiyat anbarı", "Satış zalı"]
BIZ_DEPARTMENTS = ["maliyyə şöbəsi", "hüquq şöbəsi", "texniki xidmət", "satış şöbəsi",
                   "insan resursları şöbəsi", "təchizat bölməsi", "marketinq şöbəsi"]
# meeting notes: agenda items and decisions; {n} a drawn number
BIZ_AGENDA = ["Büdcənin icrası", "Yeni layihənin mərhələləri", "Təchizat müqavilələri",
              "Ofisin təmiri", "Rüblük hesabat", "Satış planı", "Təlim proqramı"]
BIZ_DECISIONS = ["Layihənin ikinci mərhələsi üçün {n} manat ayrılsın.",
                 "Satış planı {n} faiz artırılsın.",
                 "Təlim proqramına {n} saatlıq yeni kurs əlavə edilsin.",
                 "Təmir işləri üçün {n} manatlıq smeta hazırlansın.",
                 "Rüblük hesabat {n} iş günü ərzində təqdim olunsun."]
# spec lines: field and a value pattern ({n} a drawn number, {d} a decimal)
BIZ_SPEC = [("Ekranın ölçüsü", "{d} düym"), ("Operativ yaddaş", "{n} GB"), ("Çəki", "{d} kq"),
            ("Gərginlik", "{n} V"), ("Güc", "{n} Vt"), ("Zəmanət müddəti", "{n} ay"),
            ("Prosessorun nüvələri", "{n}"), ("Batareyanın tutumu", "{n} mAh"), ("Rəng", "boz"),
            ("Material", "alüminium"), ("Hündürlük", "{n} sm"), ("Eni", "{n} sm")]
# version-history lines (after the version number)
BIZ_CHANGES = ["hesabat modulu yeniləndi", "axtarış funksiyası sürətləndirildi",
               "istifadəçi interfeysi sadələşdirildi", "ixrac funksiyası əlavə olundu",
               "bildiriş sistemi yenidən quruldu", "kiçik nasazlıqlar aradan qaldırıldı",
               "təhlükəsizlik yeniləməsi tətbiq olundu", "yeni dil seçimi əlavə olundu"]

# item 5: place-like words as topics. {r} river, {p} peak, {m} mountain
# range, {s} sea or lake, {c} country, {o} route or corridor, {g} wider
# region, {l} lowland or peninsula; {km}, {h}, {pct}, {n} drawn numbers. The
# decoy span is the place word itself. A word whose part is in a city,
# settlement or given-name pool is dropped by the builder (`geo_pools`).
GEO = {
    "r": ["Kür", "Volqa", "Dunay", "Nil", "Dəclə", "Fərat", "Terek", "Reyn", "Amazon", "Missisipi"],
    "p": ["Bazardüzü", "Şahdağ", "Tufandağ", "Babadağ", "Murovdağ", "Elbrus", "Ararat"],
    "m": ["Böyük Qafqaz", "Kiçik Qafqaz", "Talış dağları", "Alp dağları", "Ural dağları"],
    "s": ["Qara dəniz", "Aralıq dənizi", "Baltik dənizi", "Aral gölü", "Sevan gölü", "Baykal gölü"],
    "c": ["Gürcüstan", "Türkiyə", "İran", "Rusiya", "Qazaxıstan", "Türkmənistan", "Özbəkistan",
          "Çin", "Almaniya", "İtaliya", "Ukrayna", "Bolqarıstan", "Rumıniya"],
    "o": ["Orta Dəhliz", "Şimal–Cənub dəhlizi", "Şərq–Qərb dəhlizi", "Böyük İpək Yolu",
          "Lapis-Lazuli dəhlizi"],
    "g": ["Cənubi Qafqaz", "Mərkəzi Asiya", "Şərqi Avropa", "Yaxın Şərq"],
    "l": ["Abşeron yarımadası", "Kür-Araz ovalığı", "Muğan düzü", "Mil düzü"],
}
# The review, G: a sentence with a country and a region never draws a
# country that lies inside that region (`Gürcüstan` + `Cənubi Qafqaz`)
GEO_REGION_MEMBERS = {"Cənubi Qafqaz": {"Gürcüstan"},
                      "Mərkəzi Asiya": {"Qazaxıstan", "Türkmənistan", "Özbəkistan"},
                      "Şərqi Avropa": {"Ukrayna", "Bolqarıstan", "Rumıniya", "Rusiya"},
                      "Yaxın Şərq": {"İran", "Türkiyə"}}
GEO_SENTENCES = [
    "{r} çayının uzunluğu təxminən {km} kilometrdir.",
    "Bu il {r} çayında suyun səviyyəsi {pct} faiz aşağı düşüb.",
    "{p} zirvəsinin hündürlüyü {h} metrdir.",
    "{c} ilə ticarət dövriyyəsi ötən il {pct} faiz artıb.",
    "{o} üzrə daşınan yüklərin həcmi {n} min ton olub.",
    "{o} {g} ölkələrini {c} ilə birləşdirir.",               # the team, G (no country in its own region)
    "{g} regionunda yağıntının miqdarı son illərdə azalıb.",
    "{l} ərazisində əkin sahələri {pct} faiz genişlənib.",
    # The team, A: no possessive noun after a name that already ends in one (`dağları`)
    "Ekspedisiya {m} istiqamətində yola düşüb və {r} vadisi boyunca davam edib.",
    "Dərslikdə {m} və {s} hövzəsinin iqlimi müqayisə olunur.",
    "{s} sahillərində turizm mövsümü may ayında başlayır.",
    "Hesabatda {g} və {c} üzrə yük axınları ayrıca göstərilib.",
    "Yeni dəmir yolu xətti {o} çərçivəsində tikilir.",
]


def native_check_list() -> list[tuple[str, str]]:
    """(pool, sentence) for every sentence and word list in this module, for
    The native check."""
    out: list[tuple[str, str]] = []

    def add(pool: str, items) -> None:
        out.extend((pool, s) for s in items)

    add("AGE_PAIRS (real)", [f"{a}   [{lo}-{hi}]" for a, _b, (lo, hi), _f in AGE_PAIRS])
    add("AGE_PAIRS (look-alike)", [f"{b}   [{lo}-{hi}]" for _a, b, _r, (lo, hi) in AGE_PAIRS])
    add("AGE_REAL_MORE", [f"{t}   [{lo}-{hi}]" for t, (lo, hi) in AGE_REAL_MORE])
    for name in ("NOUN_FIN", "NOUN_DATE_TARIXLI", "CITY_BRAND_DECOY", "CITY_BRAND_VALID",
                 "BUILDING_LINES_INTROS", "CAPS_HEADINGS", "CAPS_AFTER", "CAPS_INTROS", "IPV6_LOOKALIKE",
                 "IPV6_REAL_PROSE", "IPV6_REAL_FIELDS", "MAC_LETTERS", "BIZ_PRODUCTS", "BIZ_UNITS",
                 "BIZ_STORES", "BIZ_DEPARTMENTS", "BIZ_AGENDA", "BIZ_DECISIONS", "BIZ_CHANGES",
                 "GEO_SENTENCES"):
        add(name, globals()[name])
    add("BUILDING_LINE_FIELDS", list(BUILDING_LINE_FIELDS.values()))
    add("CAPS_HEADER_CITIES (the team: please confirm each is a city)", CAPS_HEADER_CITIES)
    add("CAPS_FIELDS", [f for fs in CAPS_FIELDS.values() for f in fs])
    add("FORM_EXTRA_FIELDS", [f for fs in FORM_EXTRA_FIELDS.values() for f in fs])
    add("PF_NEAR_FIELDS", [f for fs in PF_NEAR_FIELDS.values() for f in fs])
    for key, items in RECALL.items():
        add(f"RECALL[{key}]", items)
    add("RECALL_FIELDS", [f for fs in RECALL_FIELDS.values() for f in fs])
    for name in ("BIZ_TITLES", "BIZ_INTROS", "BIZ_OUTROS"):
        for key, items in globals()[name].items():
            add(f"{name}[{key}]", items)
    add("BIZ_SPEC", [f"{f}: {v}" for f, v in BIZ_SPEC])
    for key, items in GEO.items():
        add(f"GEO[{key}]", items)
    return out
