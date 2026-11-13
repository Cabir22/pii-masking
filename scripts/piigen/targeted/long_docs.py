"""Carrier text for the long PEM documents (D-27).

A real RSA-2048 key is about 1,700 characters. The quality gate's PII-density
cap for the longest length band (`extreme`, 4,200-9,000 characters) is 25%, so
a document with such a key must be at least 6,800 characters, and the gate is
not loosened (A2.4). This is the prose around the key: runbooks, deployment
notes and tickets of a technical team. Written without digits, names, places,
addresses, e-mails or dates, so nothing in it can read as unlabelled PII.

`TOPICS` maps a section heading to its sentences. A document takes a random
subset of topics and sentences until it is long enough; no sentence is used
twice in a document.
"""

from __future__ import annotations

TOPICS: dict[str, list[str]] = {
    "Məqsəd": [
        "Bu sənəd xidmətin istifadə etdiyi şəxsi açarın təhlükəsiz şəkildə dəyişdirilməsi qaydasını izah edir.",
        "Sənəd növbətçi mühəndislər üçün hazırlanıb və hər addım ardıcıllıqla yerinə yetirilməlidir.",
        "Məqsəd açarın dəyişdirilməsi zamanı xidmətin dayanmasının qarşısını almaqdır.",
        "Aşağıdakı qaydalar həm planlı yenilənmə, həm də təcili dəyişdirmə hallarına aiddir.",
        "Sənəddə göstərilən addımlar əvvəlcə sınaq mühitində yoxlanılıb və yalnız sonra əsas mühitə tətbiq edilib.",
        "Dəyişiklik başlamazdan əvvəl məsul komanda bu sənədlə tanış olmalı və razılığını bildirməlidir.",
        "Sənəd hər dəyişiklikdən sonra yenilənir ki, növbəti mühəndis köhnəlmiş təlimata əməl etməsin.",
        "Bütün əməliyyatlar jurnala yazılır və sonradan yoxlama üçün saxlanılır.",
    ],
    "Hazırlıq": [
        "Başlamazdan əvvəl cari xidmətin işlək vəziyyətdə olduğunu və gözlənilməz xətaların olmadığını yoxlayın.",
        "Dəyişiklik pəncərəsi barədə bütün əlaqəli komandalara əvvəlcədən məlumat verin.",
        "Lazımi giriş hüquqlarının hazır olduğuna əmin olun, çünki sonradan icazə istəmək vaxt aparır.",
        "Köhnə açarın nüsxəsini ayrıca təhlükəsiz yerdə saxlayın ki, lazım olarsa geri qayıtmaq mümkün olsun.",
        "Yeni açarın yaradılması üçün istifadə olunacaq alətin cari versiyasını yoxlayın.",
        "Dəyişikliyi yalnız yük az olan saatlarda başlamaq tövsiyə olunur.",
        "Növbətçi mühəndis dəyişiklik zamanı əlçatan olmalı və telefonu açıq saxlamalıdır.",
        "Hazırlıq mərhələsində bütün ehtiyat planlar bir daha nəzərdən keçirilir.",
        "Cari konfiqurasiyanın surəti götürülür və yalnız oxumaq üçün qorunur.",
    ],
    "Açarın yerləşdirilməsi": [
        "Yeni şəxsi açar yaradıldıqdan sonra serverdə yalnız xidmət hesabının oxuya bildiyi qovluğa qoyulur.",
        "Açarın faylı üçün icazələr məhdudlaşdırılır və digər istifadəçilərə heç bir giriş verilmir.",
        "Faylın yerləşdirilməsindən sonra xidmət konfiqurasiyasında açarın yolu yenilənir.",
        "Açarı elektron məktubla, söhbət proqramı ilə və ya ictimai yazışma kanalı ilə göndərmək qadağandır.",
        "Köçürmə zamanı yalnız şifrələnmiş əlaqə kanalından istifadə olunmalıdır.",
        "Yerləşdirmədən sonra açarın məzmunu ilə qaynaq arasında fərq olmadığı yoxlanılır.",
        "Əgər açar sətirlərə bölünübsə, sətirlərin uzunluğunun dəyişmədiyinə diqqət edin.",
        "Faylın sonundakı boş sətir bəzi alətlər üçün vacibdir, ona görə onu silməyin.",
        "Açarı yerləşdirən mühəndis bunu növbə jurnalında qeyd etməlidir.",
    ],
    "Sertifikatın yoxlanması": [
        "Yeni açar yerləşdirildikdən sonra uyğun sertifikatın həmin açara aid olduğu yoxlanılır.",
        "Sertifikatın qüvvədə olma müddəti və buraxan qurumun adı diqqətlə oxunmalıdır.",
        "Zəncirdəki aralıq sertifikatlar çatışmırsa, bəzi müştərilər bağlantını rədd edə bilər.",
        "Yoxlama üçün xidmətə kənardan sınaq sorğusu göndərilir və cavabdakı sertifikat müqayisə olunur.",
        "Sertifikat və açar bir-birinə uyğun gəlmirsə, xidməti yenidən başlatmayın.",
        "Müddəti bitməyə yaxın olan sertifikatlar üçün ayrıca xatırlatma qurulub.",
        "Yoxlama nəticəsi tiketə əlavə olunur ki, sonradan baxan şəxs prosesi izləyə bilsin.",
        "Sertifikatın mövzu sahəsində göstərilən xidmət adı real ünvanla üst-üstə düşməlidir.",
    ],
    "Xidmətlərin yenidən başladılması": [
        "Konfiqurasiya yenilənəndən sonra xidmət ehtiyatla və bir-bir yenidən başladılır.",
        "Əvvəlcə ikinci dərəcəli nüsxə yenidən başladılır və onun sağlamlıq yoxlamasından keçməsi gözlənilir.",
        "Yalnız ikinci nüsxə sabit işlədikdən sonra əsas nüsxəyə keçid edilir.",
        "Yenidən başlatma zamanı aktiv bağlantıların bir hissəsi qısa müddətə kəsilə bilər.",
        "Başlatmadan sonra jurnalda açarla bağlı xəta mesajlarının olmadığı yoxlanılır.",
        "Əgər xidmət ayağa qalxmırsa, əvvəlcə açarın icazələrinə və yoluna baxın.",
        "Hər başlatmadan sonra bir neçə dəqiqə gözləyin və cavab müddətlərinin normaya qayıtdığını görün.",
        "Bütün nüsxələr yeni açarla işləməyə başladıqdan sonra dəyişikliyi tamamlanmış hesab edin.",
        "Yük balansçısında bütün nüsxələrin sağlam göründüyünə əmin olun.",
    ],
    "Giriş hüquqları": [
        "Açara yalnız xidmət hesabı və məhdud sayda növbətçi mühəndis daxil ola bilər.",
        "Hüquqların siyahısı hər rübdə yoxlanılır və artıq lazım olmayan icazələr ləğv edilir.",
        "İşdən ayrılmış əməkdaşın bütün giriş hüquqları həmin gün bağlanmalıdır.",
        "Müvəqqəti giriş yalnız yazılı təsdiqdən sonra və dəqiq müddətlə verilir.",
        "Açara daxil olan hər kəsin əməliyyatları ayrıca jurnalda izlənir.",
        "Paylaşılan hesablardan istifadə etmək qadağandır, çünki bu halda məsul şəxsi müəyyən etmək çətinləşir.",
        "Giriş hüququ verilərkən əməkdaşın rolu və iş vəzifəsi nəzərə alınır.",
        "Hüquqlarla bağlı hər dəyişiklik ikinci bir mühəndis tərəfindən təsdiqlənməlidir.",
    ],
    "Ehtiyat nüsxə": [
        "Köhnə açarın ehtiyat nüsxəsi şifrələnmiş şəkildə ayrıca saxlama sistemində qorunur.",
        "Ehtiyat nüsxəyə giriş yalnız iki məsul şəxsin birgə təsdiqi ilə mümkündür.",
        "Nüsxələrin bərpa oluna bildiyi vaxtaşırı sınaqdan keçirilir.",
        "Saxlama müddəti bitən nüsxələr təhlükəsiz qaydada silinir və bu barədə qeyd aparılır.",
        "Ehtiyat nüsxə heç vaxt açarın özü ilə eyni serverdə saxlanılmır.",
        "Bərpa sınağının nəticələri yazılı şəkildə təhlükəsizlik komandasına təqdim olunur.",
        "Nüsxənin yerləşdiyi saxlama sistemində müstəqil giriş jurnalı aparılır.",
        "Yeni açarın nüsxəsi də eyni qayda ilə, təsdiq alındıqdan dərhal sonra çıxarılır.",
    ],
    "Monitorinq": [
        "Dəyişiklikdən sonra ilk saat ərzində xəta nisbəti və cavab müddəti ayrıca izlənir.",
        "Monitorinq panelində şifrələnmiş bağlantılarla bağlı ani artımlar diqqətlə yoxlanılır.",
        "Əgər xəta nisbəti müəyyən həddi keçərsə, növbətçiyə avtomatik bildiriş göndərilir.",
        "Bildirişlər həm komanda kanalına, həm də növbətçinin telefonuna çatdırılır.",
        "Sağlamlıq yoxlamaları hər nüsxə üçün ayrıca qurulub və nəticələr tarixçədə saxlanılır.",
        "Qeyri-adi giriş cəhdləri aşkar olunarsa, təhlükəsizlik komandasına dərhal məlumat verilir.",
        "Jurnal fayllarında açarın məzmununun görünmədiyinə vaxtaşırı baxılır.",
        "Nəticələr həftəlik hesabatda ümumiləşdirilir və komanda iclasında müzakirə olunur.",
    ],
    "Geri qaytarma": [
        "Əgər yeni açarla problem yaranarsa, əvvəlki açara qayıtmaq üçün ehtiyat plan hazırdır.",
        "Geri qaytarmaya qərar verən mühəndis bunu dərhal komanda kanalına yazmalıdır.",
        "Əvvəlcə xidmət konfiqurasiyası köhnə vəziyyətinə qaytarılır, sonra xidmət yenidən başladılır.",
        "Geri qaytarmadan sonra səbəb araşdırılana qədər yeni dəyişiklik edilmir.",
        "Qayıdış addımları da sınaq mühitində vaxtaşırı yoxlanılır ki, real vəziyyətdə sürpriz olmasın.",
        "Əgər köhnə açar artıq ləğv edilibsə, geri qaytarma mümkün deyil və təcili plan işə düşür.",
        "Geri qaytarılan dəyişiklik üçün ayrıca hadisə qeydi açılır.",
        "Hər geri qaytarma sonrakı təkmilləşdirmə üçün dərs kimi sənədləşdirilir.",
    ],
    "Təhlükəsizlik qaydaları": [
        "Şəxsi açar heç vaxt ictimai yazışmalarda, tiketlərdə və ya ümumi qovluqlarda saxlanılmamalıdır.",
        "Əgər açar təsadüfən görünən yerdə qalıbsa, o dərhal etibarsız sayılır və dəyişdirilməlidir.",
        "Açarın kod anbarına düşməsi ciddi hadisə sayılır və təhlükəsizlik komandasına bildirilməlidir.",
        "Hər açar yalnız bir xidmət üçün istifadə olunur və başqa məqsədlə təkrar işlədilmir.",
        "Açarların ömrü məhdud tutulur və müddəti bitməmiş əvvəlcədən dəyişdirilir.",
        "Sənədlərdə nümunə kimi göstərilən açarlar həmişə real açarlardan fərqli olmalıdır.",
        "Şübhəli fəaliyyət aşkar olunarsa, əvvəlcə açarı ləğv edin, sonra səbəbi araşdırın.",
        "Təhlükəsizlik qaydalarına riayət etməyən əməliyyatlar dayandırılır və yenidən nəzərdən keçirilir.",
        "Açarla işləyən bütün kompüterlərdə disk şifrələməsi aktiv olmalıdır.",
    ],
    "Sınaq mühiti": [
        "Hər dəyişiklik əvvəlcə sınaq mühitində, əsas mühitin dəqiq surəti üzərində yoxlanılır.",
        "Sınaq mühitində istifadə olunan açarlar əsas mühitin açarlarından tamamilə fərqlidir.",
        "Sınaq zamanı real istifadəçi məlumatlarından istifadə etmək olmaz.",
        "Sınaqdan keçməyən dəyişiklik əsas mühitə buraxılmır və səbəbi yazılı şəkildə qeyd olunur.",
        "Sınaq mühitinin konfiqurasiyası əsas mühitlə mümkün qədər eyni saxlanılır.",
        "Sınaq nəticələri tiketə əlavə olunur və təsdiq üçün məsul mühəndisə göndərilir.",
        "Yeni alətlər və versiyalar da əvvəlcə burada yoxlanılır.",
        "Sınaq mühitində aşkar olunan xətalar əsas mühitə keçməzdən əvvəl düzəldilir.",
    ],
    "Məsuliyyət və əlaqə": [
        "Dəyişikliyin ümumi məsuliyyəti növbətçi mühəndisin üzərindədir.",
        "Təhlükəsizlik komandası hər addımda məsləhət verə bilər və ona vaxtında müraciət etmək tövsiyə olunur.",
        "Həll olunmayan məsələlər komanda rəhbərinə çatdırılır və iclasda müzakirə edilir.",
        "Dəyişiklik tamamlandıqdan sonra bütün tərəflərə qısa yekun məlumat göndərilir.",
        "Sənəddə rast gəlinən qeyri-dəqiqliklər barədə komanda kanalına yazın.",
        "Hər yeniləmədən sonra növbə təhvil verilərkən bu sənədin cari vəziyyəti də təhvil verilir.",
        "Qeydlər və sorğular yalnız komandanın rəsmi kanalları ilə aparılır.",
        "Təcili hallarda növbətçi mühəndisə birbaşa zəng edilir, digər hallarda yazılı müraciət kifayətdir.",
    ],
}

# Which topic hosts the key: it is placed after the second or third sentence.
KEY_TOPIC = "Açarın yerləşdirilməsi"

# kind -> (titles, closing lines). The first line of the document.
KINDS: dict[str, dict] = {
    "runbook": {
        "titles": ["# Runbook: şəxsi açarın dəyişdirilməsi",
                   "# Runbook: sertifikat açarının yenilənməsi",
                   "# Runbook: xidmətlərarası açarın rotasiyası",
                   "# Runbook: şlüz açarının təcili dəyişdirilməsi"],
        "heading": "## {h}",
        "closing": ["Bu runbook hər dəyişiklikdən sonra yenilənməlidir.",
                    "Addımlar tamamlandıqdan sonra növbə jurnalına qeyd yazılır."],
    },
    "deployment": {
        "titles": ["Yerləşdirmə qeydləri: ödəniş xidməti",
                   "Yerləşdirmə qeydləri: bildiriş xidməti",
                   "Yerləşdirmə qeydləri: autentifikasiya şlüzü",
                   "Yerləşdirmə qeydləri: hesabat xidməti"],
        "heading": "{h}:",
        "closing": ["Qeydlər növbəti yerləşdirmədən əvvəl bir daha nəzərdən keçirilir.",
                    "Yerləşdirmənin nəticəsi komanda kanalında paylaşılır."],
    },
    "ticket": {
        "titles": ["Tiket: açarın təcili dəyişdirilməsi\nStatus: açıq\nPrioritet: yüksək\nKomponent: autentifikasiya xidməti",
                   "Tiket: sertifikat açarının yenilənməsi\nStatus: işdə\nPrioritet: orta\nKomponent: şlüz xidməti",
                   "Tiket: xidmət açarının rotasiyası\nStatus: açıq\nPrioritet: yüksək\nKomponent: ödəniş xidməti",
                   "Tiket: açarın planlı dəyişdirilməsi\nStatus: gözləmədə\nPrioritet: aşağı\nKomponent: bildiriş xidməti"],
        "heading": "{h}",
        "closing": ["Tiket dəyişiklik təsdiqləndikdən sonra bağlanır.",
                    "Əlavə sualları bu tiketin şərhlərində yazın."],
    },
}
