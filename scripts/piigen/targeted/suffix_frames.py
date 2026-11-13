"""Sentences for the inflected forms (P2-4c), one slot `{v}` each.

`{v}` is filled with the value already inflected for the case the sentence
is listed under (suffix.inflect), so every sentence was written for exactly
that form: `Sabah {v} görüşəcəyik.` takes the instrumental (`Əsgərlə`).
Contract C1 frames with `{v:CASE}` slots are used as well when
they exist; this bank makes sure every case, including the tier-2 forms C1
does not have codes for, is written in natural sentences.

Kinds: person (GIVENNAME, SURNAME), place (CITY), street (STREET). No other
PII and no digits in any sentence. For the native-speaker check (P4-2).

A question form with `-mI` and no person ending (`loc_q`, `q`) is the 3rd person
(`Kuryer indi Gəncədəmi?`); `Sən indi Gəncədəmi?` would need `-sənmi` (P4-2 round 2).
"""

SUFFIX_FRAMES: dict[str, dict[str, list[str]]] = {
    "person": {
        "gen": ["{v} ərizəsi dünən qeydə alınıb.", "Bu sənəd {v} adına tərtib edilib.",
                "Müqavilədə {v} imzası yoxdur.", "{v} müraciətinə hələ baxılmayıb."],
        "dat": ["Sənədləri dünən {v} göndərdik.", "Bu barədə {v} məlumat verilib.",
                "Sabah {v} yenidən zəng ediləcək.", "Cavab məktubu {v} ünvanlanıb."],
        "acc": ["Komissiya {v} məsul şəxs təyin edib.", "Dünən {v} ofisdə gördüm.",
                "Zəhmət olmasa, {v} iclasa dəvət edin.", "Rəhbərlik {v} təbrik edib."],
        "loc": ["Arxivin açarları hazırda {v} qalır.", "Sənədin əsli hələ {v} saxlanılır.",
                "Kitab bir həftədir {v} qalıb."],
        "abl": ["Bu məlumatı {v} öyrəndik.", "{v} hələ cavab gəlməyib.",
                "Ərizə {v} qəbul edilib.", "Hesabatı dünən {v} almışıq."],
        "ins": ["Sabah {v} görüşəcəyik.", "Bu məsələni {v} ətraflı müzakirə etdik.",
                "Layihə üzərində {v} birlikdə işləyirik.", "Dünən {v} telefonla danışdım."],
        "rel": ["{v} sənədlər bu gün geri qaytarılmalıdır.",
                "{v} açarları istəyin, arxiv bağlıdır.", "{v} nüsxə imzalanmayıb."],
        "cop": ["Layihənin rəhbəri {v}.", "Bu gün növbətçi əməkdaş {v}.",
                "Müqavilənin tərəflərindən biri {v}."],
        # the family plural: only surnames take these (suffix.APPLIES)
        # no particle `da/də` after the slot: it would have to harmonise with
        # the value (Məmmədovlar da / Əlizadələr də)
        "pl": ["{v} bu ünvanda qeydiyyatdadır.", "Qonşuluqda {v} yaşayır.",
               "{v} bu il kəndə köçüb."],
        "pl_gen": ["{v} evi satışa çıxarılıb.", "{v} müraciəti baxılması üçün göndərilib."],
        "pl_dat": ["Dəvətnamə {v} göndərilib.", "Kompensasiya {v} ödənilib."],
        "pl_loc": ["Toy {v} keçiriləcək.", "Bayram axşamı {v} qonaq idik."],
        "pl_abl": ["Bu xəbəri {v} eşitdim.", "Şikayət {v} daxil olub."],
        # tier 2
        "gil": ["Axşam {v} bizə gələcək.", "{v} bu yay dənizə gedir.", "Sabah {v} köçür."],
        "gil_gen": ["{v} evi təmir olunur.", "{v} maşını həyətdə qalıb."],
        "gil_dat": ["Bayramda {v} qonaq getdik.", "Bu gün {v} baş çəkəcəyəm."],
        "gil_loc": ["Dünən axşam {v} idik.", "Uşaqlar indi {v} qalır."],
        "gil_abl": ["Uşaqlar indicə {v} qayıtdı.", "Bu sovqatı {v} gətirmişik."],
        "pred1": ["Salam, mən {v}, sizə dünən yazmışdım.", "Mən {v}, sifarişlə bağlı zəng edirəm.",
                  "Bağışlayın, mən {v}, növbəm çatıb?"],
        "pred_formal": ["Bağışlayın, siz {v}?", "Siz {v}? Sizi gözləyirdik."],
        "q": ["Bu sifarişi verən {v}?", "Növbəti çıxış edən {v}?"],
        "past": ["Zəng edən {v}, sonra yenə yazacaq.", "Dünən növbətçi {v}."],
        "gen_ki": ["Bu çanta mənim deyil, {v}.", "Masanın üstündəki telefon {v}."],
        "poss1": ["Əziz {v}, ad günün mübarək!", "Canım {v}, sənə uğurlar!"],
        "cond": ["Zəng edən {v}, dərhal mənə xəbər verin.",
                 "Növbəti müraciətçi {v}, onu içəri dəvət edin."],
    },
    "place": {
        "gen": ["{v} mərkəzində yeni filial açılıb.", "{v} hava proqnozu dəyişib.",
                "{v} küçələrində təmir işləri gedir."],
        "dat": ["Sabah {v} yola düşürəm.", "Yük artıq {v} göndərilib.", "Gələn ay {v} köçürük."],
        "acc": ["Turistlər {v} çox bəyənib.", "Nümayəndə heyəti {v} ziyarət edəcək."],
        "loc": ["Filialımız {v} yerləşir.", "Konfrans {v} keçiriləcək.", "Anam {v} yaşayır."],
        "abl": ["{v} gələn qatar gecikir.", "Müştəri {v} zəng edib.", "Sifariş {v} göndərilib."],
        "ins": ["{v} əlaqə hələ bərpa olunmayıb.", "Mərkəz {v} birbaşa əlaqə saxlayır."],
        "rel": ["{v} ofisimiz müvəqqəti bağlanıb.", "{v} anbarda yer qalmayıb.",
                "{v} əməkdaşlar da iclasa qoşulacaq."],
        "cop": ["Doğulduğum şəhər {v}.", "Göndərişin son məntəqəsi {v}."],
        "loc_cop": ["Ofisimiz {v}.", "Kuryer hazırda {v}."],
        "loc_pred1": ["Mən hazırda {v}, sabah qayıdacağam.", "İndi {v}, axşam zəng edərəm."],
        "loc_pred2": ["Sən də {v}?", "Hələ {v}? Axşam görüşək."],
        "loc_pred1pl": ["Biz bu həftə {v}.", "Hamımız indi {v}, siz də gəlin."],
        "q": ["Seçilən şəhər {v}?", "Görüş yeri {v}?"],
        "loc_q": ["Kuryer indi {v}?", "Ofis hələ də {v}?"],
        "loc_past": ["Toy keçən ay {v}.", "Seminar ötən həftə {v}."],
        "loc_past1": ["Keçən həftə {v}, ona görə yaza bilmədim.", "Dünən bütün günü {v}."],
        "term_dek": ["Yolu {v} təmir edirlər.", "Avtobus yalnız {v} gedir."],
        "term_can": ["Buradan {v} üç saat yoldur.", "Mən də {v} sizinlə gedərəm."],
        "poss1pl": ["Doğma {v} gündən-günə gözəlləşir.", "Gözəl {v} qonaqları salamlayır."],
        "loc_cond": ["Görüş {v}, mən də gələrəm.", "Sifariş hələ {v}, sabah çatdırılar."],
    },
    "street": {
        "gen": ["{v} təmiri başa çatıb.", "{v} işıqlandırılması yenilənib."],
        "dat": ["Kuryer {v} çatıb.", "Ofisi keçən ay {v} köçürdük."],
        "acc": ["Bələdiyyə {v} genişləndirir.", "Sürücü {v} tapa bilmədi."],
        "loc": ["Ofisimiz {v} yerləşir.", "Yeni mağaza {v} açılıb."],
        "abl": ["{v} keçəndə zəng edin.", "Kuryer artıq {v} çıxıb."],
        "ins": ["Avtobus {v} hərəkət edir.", "Yeni marşrut {v} keçir."],
        "rel": ["{v} mağaza bağlanıb.", "{v} binada təmir gedir."],
        "cop": ["Yeni ünvanımız {v}.", "Çatdırılma ünvanı {v}."],
        "loc_cop": ["Anbar indi {v}.", "Qeydiyyat ünvanı {v}."],
        "loc_pred1": ["Mən artıq {v}, harada görüşək?", "İndi {v}, tezliklə çatıram."],
        "loc_q": ["Kuryer hələ {v}?", "Mağaza hələ də {v}?"],
        "term_dek": ["Tıxac {v} uzanır.", "Yol {v} bağlıdır."],
    },
}

KIND = {"GIVENNAME": "person", "SURNAME": "person", "CITY": "place", "STREET": "street"}
