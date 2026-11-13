# Translation re-check pack: D-56c fixes (TR/RU findings)

The same 300 v4.1 train documents as the first check, translated again with the D-56c fixes (branch `p2/translation-d56c`, overnight launcher, concurrency 40). Each item shows the Azerbaijani source, then the translation. Labelled values are `[value]{LABEL}`; an inflected name carries its case inside the brackets (`[Bakü'de]{CITY}`, `[Гатамовой]{SURNAME}`, D-56d).

**What to check (the tags after each id say which findings the item covers):**

- **case:** the name or place has the case the sentence needs, with the right ending;
- **names:** a person's given name and surname agree in gender with each other and with the text;
- **year:** the DATE has the year the text gives elsewhere;
- **patronymic** (RU): `оглы`/`кызы` after the father's name, in the source order;
- **VÖEN** (RU): written `ИНН`;
- **mask:** `****1234` matches the new value's last digits;
- **everywhere:** no `. yıl`/`год` after a full date, no `-dir` after a value, no `bilgi tabanı`/`prosedur`/`tekniki`, `Aliyev` not `Eliyev`.

The full outputs are next to this file: `tr.jsonl`, `ru.jsonl`, `en.jsonl`, and the Azerbaijani source `az_source.jsonl`. `d56c_before_after.md` has your checks counted on the first sample and on this one.

## TR items

### TR 1 · patronymic, names · sprint1_llm_b6.clean__llm_az_017469

**AZ:**

```
Məhkəmə Bildirişi

Şəhər Məhkəməsi tərəfindən açılmış mülki iş üzrə tərəflərin dinlənməsi barədə.

İşin icra edilməsi zamanı aşağıdakı şəxslər çağırılır:
1. [Məhədağalı]{SURNAME} [Zaray]{GIVENNAME} [Samiran]{GIVENNAME} qızı
2. [Atalarov]{SURNAME} [Mətin]{GIVENNAME} [Qaplan]{GIVENNAME} oğlu
3. [Ağaşərifov]{SURNAME} [Ziyapaşa]{GIVENNAME} [İmpixan]{GIVENNAME} oğlu

Məhkəmə tərəfindən tədqiq edilən materiallar arasında ****9821 nömrəli kartın təhlükəsizlik kodu [713]{CARD_SECURITY_CODE} olan əməliyyatları və əlavə melumatlar daxildir. İşin baxılması üçün təyin olunmuş ünvan: bina [10]{BUILDINGNUM}.

Mesela - yox, məsələ ilə bağlı əlavə suallar üçün [(055) 125-12-65]{TELEPHONENUM} və ya [allahman.sahmemmedli@nurtekstil.az]{EMAIL} vasitəsilə əlaqə saxlamaq olar. Mehkeme tərəfindən verilən qərar qəti deyil.

[2015-05-03]{DATE}
```

**TR:**

```
Mahkeme Bildirisi

Şehir Mahkemesi tarafından açılmış hukuki dava uyarınca tarafların dinlenmesi hakkında.

Davanın yürütülmesi sırasında aşağıdaki kişiler çağrılmaktadır:
1. [Adler]{SURNAME} [Tamamnur]{GIVENNAME} [Öcalan]{GIVENNAME} kızı
2. [Aksyonov]{SURNAME} [Bereket]{GIVENNAME} [Andria]{GIVENNAME} oğlu
3. [Ucallı]{SURNAME} [Tolga]{GIVENNAME} [Tasin]{GIVENNAME} oğlu

Mahkeme tarafından incelenen materyaller arasında ****9821 numaralı kartın güvenlik kodu [548]{CARD_SECURITY_CODE} olan işlemler ve ek bilgiler yer almaktadır. Davanın incelenmesi için belirlenen adres: bina [56B]{BUILDINGNUM}.

Örneğin değil, konuyla ilgili ek sorular için [+994996173188]{TELEPHONENUM} veya [miranxan_mubarekov@mail.ru]{EMAIL} vasıtasıyla iletişime geçilebilir. Mahkeme tarafından verilen karar kesin değildir.

[26 Ekim 2015]{DATE}
```

---

### TR 2 · patronymic, names · sprint1_llm_b6.clean__llm_az_002916

**AZ:**

```
TƏCİLİ: Melumat Təhlükəsizliyi ilə Bağlı Kritik Xeberdarliq

Bu sənəd [23.11.2022]{DATE} tarixində tərtib edilib. Sistemimizdə çox ciddi bir nasazlıq aşkar olunmuşdur və vəziyyət sürətlə pisləşir. Melumatların sızması ehtimalı yüksəkdir.

Tərtib olunan siyahıda aşağıdakı şəxslər qeyd olunub:
- [İgidcanova]{SURNAME} [Əlvanbəyim]{GIVENNAME} [Usufəli]{GIVENNAME} qızı
- [Eldarova]{SURNAME} [Ərdənay]{GIVENNAME} [Əlvənd]{GIVENNAME} qızı
- [Xətibov]{SURNAME} [Xıdır]{GIVENNAME} [Möhkəm]{GIVENNAME} oğlu

Müşahidələrə görə, [Ərməki küç.]{STREET} ərazisində yaşayan və [28]{AGE} yaşında olan şəxslərin dataları təhlükə altındadır. Həmçinin hfjyi [at] yttyys [dot] com ünvanından şübhəli girişlər qeydə alınıb. Sistem loglarında aşağıdakı MAC ünvanı görünür: 68:7d:b2:c3:2c:4c:7d:81:2d:45:fd:e9:46:95:8f:91.

"Vəziyyət dərhal həll edilməlidir, əks halda fəsadlar daha da böyüyəcək," - texniki rəhbər bildirdi.

Ətraflı məlumat üçün [https://files.barama.io/confirm/9kuS9IWhxU-fQH90C8F8OGHwN0zI2sy]{URL} ünvanına daxil olun və ya [elruz.xudaquluyev12@azdata.az]{EMAIL} ünvanına müraciət edin.
Əlaqə: [+994557068210]{TELEPHONENUM}
```

**TR:**

```
ACİL: Bilgi Güvenliği ile İlgili Kritik Uyarı

Bu belge [17 Mart 2022]{DATE} tarihinde düzenlenmiştir. Sistemimizde çok ciddi bir arıza tespit edilmiştir ve durum hızla kötüleşmektedir. Bilgilerin sızma ihtimali yüksektir.

Düzenlenen listede aşağıdaki kişiler belirtilmiştir:
- [Velibeyli]{SURNAME} [Olga]{GIVENNAME} [Abdıhan]{GIVENNAME} kızı
- [Ağaceferova]{SURNAME} [Tatyana]{GIVENNAME} [Tarik]{GIVENNAME} kızı
- [Muştaglı]{SURNAME} [İsin]{GIVENNAME} [Şirindil]{GIVENNAME} oğlu

Gözlemlere göre, [Camal Aliyev Cad.]{STREET} bölgesinde yaşayan ve [40]{AGE} yaşında olan kişilerin dataları tehlike altındadır. Ayrıca hfjyi [at] yttyys [dot] com adresinden şüpheli girişler kaydedilmiştir. Sistem loglarında aşağıdaki MAC adresi görünmektedir: 68:7d:b2:c3:2c:4c:7d:81:2d:45:fd:e9:46:95:8f:91.

"Durum derhal çözülmelidir, aksi takdirde felaketler daha da büyüyecektir," - teknik müdür bildirdi.

Ayrıntılı bilgi için [https://portal.barama.io/callback/qcxK6akr6TW7e5A3pm0gix]{URL} adresine girin veya [sixeliyev.m@mail.ru]{EMAIL} adresine başvurun.
İletişim: [994247686699]{TELEPHONENUM}
```

---

### TR 3 · VÖEN · runb_targeted__targeted_az_023759

**AZ:**

```
Sağ ol, çox kömək etdin.
Sənədin elektron versiyasında VÖEN [5043978344]{AZ_VOEN} olaraq saxlanılıb. Düzəliş edildikdən sonra qeyd yenilənib. Sənədin elektron versiyasında VÖEN 14QZ394205 olaraq saxlanılıb. Axşam zəng edərəm.
```

**TR:**

```
Sağ ol, çok yardım ettin.
Belgenin elektronik versiyonunda VÖEN [4497037959]{AZ_VOEN} olarak saklanmıştır. Düzeltme yapıldıktan sonra not güncellenmiştir. Belgenin elektronik versiyonunda VÖEN 14QZ394205 olarak saklanmıştır. Akşam ararım.
```

---

### TR 4 · VÖEN · repaired.clean__llm_az_094708

**AZ:**

```
Bağışlayın, amma mən bu hissədə çox qarışıq və narahat vəziyyətdəyəm. Niyə bu məlumatlar birbaşa kodun içindədir? Məsələn, VÖEN: [3373262713]{AZ_VOEN} burada necə yarana bilər? Bu təhlükəsizlik baxımından düzgün deyil?
> Səhv yazılıb deyə düşünürəm, amma dəqiq deyil...
Mən çox həyəcanlıyam, zəhmət olmasa bunu bir daha yoxlayaq.
```

**TR:**

```
Affedersiniz, ama ben bu kısımda çok karışık ve rahatsız bir durumdayım. Neden bu bilgiler doğrudan kodun içindedir? Örneğin, VÖEN: [101563415428165]{AZ_VOEN} burada nasıl oluşabilir? Bu güvenlik açısından doğru değil mi?
> Yanlış yazılmış diye düşünüyorum, ama kesin değil...
Çok heyecanlıyım, lütfen bunu bir daha kontrol edelim.
```

---

### TR 5 · mask · repaired.clean__llm_az_043694

**AZ:**

```
------------------------------------------------------------
| Yönləndirilmiş Səs Mesajı                                |
| Tarix: [14.05.2019]{DATE}                                        |
| Müştəri ID: VM-4492                                     |
------------------------------------------------------------

(Sistem: Səs yazısı avtomatik olaraq mətnə çevrilir)

"Salam, salam! Mən [Qarakişi]{GIVENNAME}, hələ də o köhnə, enerjili [78]{AGE} yaşındayam, amma hələ də dəyişməmişəm! (Qısa gülüş səsi). Sizi narahat etdiyim üçün üzr istəyirəm, amma saat artıq [10:48]{TIME}-dir və mən hələ də sizin zənginizi gözləyirəm.

Mənim nömrəm [+994188118558]{TELEPHONENUM} olacaq. Zəhmət olmasa, məni geri zəng edin. Bu arada, o kartın son rəqəmlərini də tam xatırlamıram, yəqin ki, ****558 idi. Amma eybi yoxdur, zəng edəndə hər şeyi izah edərəm. Hər şey yaxşı olacaq, deyilmi? Hə, hələlik!"
```

**TR:**

```
------------------------------------------------------------
| Yönlendirilmiş Ses Mesajı                                |
| Tarih: [7 Ağustos 2019]{DATE}                                        |
| Müşteri ID: VM-4492                                     |
------------------------------------------------------------

(Sistem: Ses kaydı otomatik olarak metne çevrilir)

"Selam, selam! Ben [Gedeş]{GIVENNAME}, hala o eski, enerjik [54]{AGE} yaşındayım, ama hala değişmedim! (Kısa gülüş sesi). Sizi rahatsız ettiğim için özür dilerim, ama saat artık [18:53]{TIME}'dür ve ben hala sizin aramanızı bekliyorum.

Benim numaram [+994 (10) 874-90-98]{TELEPHONENUM} olacak. Lütfen, beni geri arayın. Bu arada, o kartın son rakamlarını da tam hatırlamıyorum, herhalde ****098 idi. Ama sorun değil, aradığınızda her şeyi açıklarım. Her şey iyi olacak, değil mi? Ha, şimdilik!"
```

---

### TR 6 · mask · repaired.clean__llm_az_036430

**AZ:**

```
Xəstə Hesabatı

Məkan: [Qusar]{CITY}
Tarix: [14.06.2022]{DATE}

Klinik qeydlər:
Vəziyyət: Stabil.
Şikayət: Halsızlıq, baş ağrısı, yüngül titrəmə.
Müayinə: Təzyiq 120/80, temperatur 36.6.
Tövsiyə: Dərman qəbulu və tam istirahət.
Növbəti nəzarət: 1 həftə sonra.

İnzibati məlumatlar:
Telefon: [077 911 45 83]{TELEPHONENUM}
Email: [a.ferecov@azertelekom.az]{EMAIL}
Fin kodu: [ESAN78Q]{AZ_FIN}
Kart nömrəsi: [4885905221530696]{PAYMENT_CARD_NUMBER}
Kart son: ****0696
```

**TR:**

```
Hasta Raporu

Yer: [Sehlebad]{CITY}
Tarih: [21 Temmuz 2022]{DATE}

Klinik notlar:
Durum: Stabil.
Şikayet: Halsızlık, baş ağrısı, hafif titreme.
Muayene: Tansiyon 120/80, ateş 36.6.
Öneri: İlaç kullanımı ve tam istirahat.
Sonraki kontrol: 1 hafta sonra.

İdari bilgiler:
Telefon: [+994705972635]{TELEPHONENUM}
E-posta: [mehdiyev.h@box.az]{EMAIL}
Fin kodu: [453LPGD]{AZ_FIN}
Kart numarası: [5202-4014-9838-1123]{PAYMENT_CARD_NUMBER}
Kart son: ****1123
```

---

### TR 7 · case · sprint1_llm_b5.clean__llm_az_006791

**AZ:**

```
// Endpoint: /v1/profile
// Təsvir: İstifadəçi məlumatlarını oxumaq.
// Nümunə: [Büniyamin]{GIVENNAME} [Oruc Ramazanov küçəsində]{STREET} qeydiyyatdan keçib və [izayeddinalisov@gmail.com]{EMAIL} ünvanına sahibdir – 2016-cı il məlumatı.“
```

**TR:**

```
// Endpoint: /v1/profile
// Açıklama: Kullanıcı bilgilerini okumak.
// Örnek: [Tale]{GIVENNAME} [Tekle Bulvarı'nda]{STREET} kayıt olmuştur ve [kafiyesalayev@gmail.com]{EMAIL} adresine sahiptir – 2016 yılı bilgisi.
```

---

### TR 8 · case · repaired.clean__llm_az_097563

**AZ:**

```
## Əməliyyat Təlimatı: Hesab Yaratma və Texniki Dəstək (2023)

Bu sənəd, istifadəçi profillərinin yaradılması və texniki nasazlıqların aradan qaldırılması prosesində tətbiq ediləcək standart prosedurları əhatə edir.

### 1. İstifadəçi Məlumatlarının Yoxlanılması
Yeni müraciət daxil olduqda, məsuliyyətli əməkdaş ilk növbədə sənədlərin doğruluğunu yoxlamalıdır. Məsələn, [Tariyelzadənin]{SURNAME} təqdim etdiyi məlumatlar bazadakı mövcud qeydlərlə üst-üstə düşməlidir. Əgər əlaqə problemi yaşanarsa, [orders.agamirov@company.az]{EMAIL} ünvanına dərhal bildiriş göndərilməlidir.

### 2. Qeydiyyat Problemlərinin Həlli
İstifadəçilər qeydiyyatdan keçə bilmədikdə, onlara aşağıdakı rəsmi link vasitəsilə yenidən qoşulma imkanı təqdim edilməlidir:
[http://account.xezerlog.az/join?t=QCvIoz6AN9RsC6jX5Ny7MCGG]{URL}

Əgər ünvan təyini ilə bağlı xəta baş verərsə, [Mişkireyn prospektində]{STREET} yerləşən ofis məlumatlarının bazada düzgün indekslənib-indekslənmədiyini yoxlayın.

### 3. Sistem Logları
[2023-08-10 09:15:22] [INFO] Database connection established.
[2023-08-10 09:17:45] [ERROR] Invalid user session detected.
```

**TR:**

```
## Operasyon Talimatı: Hesap Oluşturma ve Teknik Destek (2023)

Bu belge, kullanıcı profillerinin oluşturulması ve teknik arızaların giderilmesi sürecinde uygulanacak standart prosedürleri kapsamaktadır.

### 1. Kullanıcı Bilgilerinin Kontrol Edilmesi
Yeni başvuru geldiğinde, sorumlu çalışan ilk olarak belgelerin doğruluğunu kontrol etmelidir. Örneğin, [Memmedhanov'un]{SURNAME} tarafından sunulan bilgiler veritabanındaki mevcut kayıtlarla örtüşmelidir. Eğer iletişim sorunu yaşanırsa, [velinurovt@nurtekstil.az]{EMAIL} adresine derhal bildirim gönderilmelidir.

### 2. Kayıt Sorunlarının Çözümü
Kullanıcılar kayıt olamadıklarında, onlara aşağıdaki resmi bağlantı aracılığıyla yeniden bağlanma imkanı sunulmalıdır:
[https://portal.company.az/activate?verify=iZuC77KdInhLs2pTJbihycFb0lRZA-Uw]{URL}

Eğer adres tanımlama ile ilgili bir hata oluşursa, [1-ci Deymedağlı Blv.]{STREET} adresinde bulunan ofis bilgilerinin veritabanında doğru indekslenip indekslenmediğini kontrol edin.

### 3. Sistem Logları
[2023-08-10 09:15:22] [INFO] Database connection established.
[2023-08-10 09:17:45] [ERROR] Invalid user session detected.
```

---

### TR 9 · case, names · sprint1_llm_b6.clean__llm_az_015101

**AZ:**

```
----- Forwarded message -----
[2024-05-15 09:45]

[Cövri]{GIVENNAME} [Eldarlı]{SURNAME} mür. doldurdu.
Ad: [Ərkixanım]{GIVENNAME}
SOYAD: [ELDARLI]{SURNAME}
Zəhmət olmasa, [Ərkixanımı]{GIVENNAME} qeyd edin və sənədi yoxlayın, xəta olmasın.
```

**TR:**

```
----- İletilen mesaj -----
[2024-05-15 09:45]

[Tapdıghan]{GIVENNAME} [Ceferağalı]{SURNAME} mür. doldurdu.
Ad: [Gülbacı]{GIVENNAME}
SOYAD: [Ceferağalı]{SURNAME}
Lütfen, [Gülbacı'yı]{GIVENNAME} kaydedin ve belgeyi kontrol edin, hata olmasın.
```

---

### TR 10 · case · sprint1_llm_b5.clean__llm_az_009275

**AZ:**

```
[2023-03-22 14:05] Çağrı başladı –
Operator: Salam.
Müştəri: ...ə, mən... ünvanı deyeceem. [Zaur Nəsibov küçəsində]{STREET}, [Bəydövüldə]{CITY}.
Operator: Bir də.
Müştəri: [Zaur Nəsibov küçəsində]{STREET}, [Bəydövüldə]{CITY}. Səhv... yox, düzdür.
```

**TR:**

```
[2023-03-22 14:05] Çağrı başladı –
Operatör: Merhaba.
Müşteri: ...e, ben... adresi söyleyeceğim. [Morul Blv.]{STREET}, [Erçivan'da]{CITY}.
Operatör: Bir de.
Müşteri: [Morul Blv.]{STREET}, [Erçivan'da]{CITY}. Yanlış... hayır, doğru.
```

---

### TR 11 · VÖEN, year · sprint1_llm_b2.clean__llm_az_001544

**AZ:**

```
Tarix: [22.05.2016]{DATE}

[2016-05-22 14:02:11] LOG: Məlumat bazasında xəta aşkar edildi.
[2016-05-22 14:05:48] LOG: Sistem xətası: Vergi məlumatı tapılmadı.

Mən çox çaşqınam və nə edəcəyimi bilmirəm. Tələbənin qeydiyyat sənədlərini yenidən nəzərdən keçirirəm, amma hər şey çox qarışıqdır. Sənədlərdə qeyd olunan VÖEN [1052774604]{AZ_VOEN} nömrəsidir, lakin mən bunun kimə aid olduğunu və ya niyə belə göründüyünü tam başa düşmürəm. Bu məlumat çox əhəmiyyətlidir və biz bunu tez bir zamanda həll etməliyik. Bütün məlumatları yenidən yoxladım, amma hələ də bir problem görürəm. Zəhmət olmasa, bu xətanın səbəbini tapmağa kömək edin, çünki bu vəziyyət məni çox narahat edir.
```

**TR:**

```
Tarih: [17 Temmuz 2016]{DATE}

[2016-05-22 14:02:11] LOG: Veritabanında hata tespit edildi.
[2016-05-22 14:05:48] LOG: Sistem hatası: Vergi bilgisi bulunamadı.

Ben çok şaşkınım ve ne yapacağımı bilmiyorum. Öğrencinin kayıt belgelerini yeniden gözden geçiriyorum, ama her şey çok karışık. Belgelerde belirtilen VÖEN [6490626041]{AZ_VOEN} numarasıdır, ancak bunun kime ait olduğunu veya neden böyle göründüğünü tam olarak anlayamıyorum. Bu bilgi çok önemlidir ve bunu hızlı bir şekilde çözmeliyiz. Tüm bilgileri yeniden kontrol ettim, ama hâlâ bir sorun görüyorum. Lütfen bu hatanın sebebini bulmaya yardım edin, çünkü bu durum beni çok endişelendiriyor.
```

---

### TR 12 · year, names · repaired.clean__llm_az_035559

**AZ:**

```
------------------------------------------------------------
| Forwarded message from: Police_Internal_Relay            |
| Date: [14.06.2019]{DATE}                                          |
| Subject: Hadisə protokolu                                 |
------------------------------------------------------------

2019-cu ilin iyun ayının 14-də baş vermiş hadisə ilə bağlı rəsmi məlumatdır.

Müraciət edən şəxs: [Samir]{GIVENNAME} [İbrahimov]{SURNAME}.
Əlaqə nömrəsi: [+994 10 211 90 12]{TELEPHONENUM}.
Hadisənin baş verdiyi ünvan: Bina [81]{BUILDINGNUM}.
Hadisə vaxtı – 14:30.

Hadisənin təsviri: Şikayətçinin bildirdiyinə görə, şəxsi əmlakı və şəxsiyyət vəsiqəsi (son rəqəmləri ****4921) hadisə yerindən itmişdir. Hadisə ətrafında “şübhəli” şəxslərin olduğu barədə ilkin məlumatlar daxil olub. Tədqiqat davam etdirilir.
```

**TR:**

```
------------------------------------------------------------
| İletilen mesaj: Police_Internal_Relay            |
| Tarih: [17.02.19]{DATE}                                          |
| Konu: Olay protokolü                                 |
------------------------------------------------------------

2019 yılının Haziran ayının 14'ünde meydana gelen olayla ilgili resmi bilgidir.

Başvuran kişi: [Efsun]{GIVENNAME} [Zamanov]{SURNAME}.
İletişim numarası: [(051) 649-46-49]{TELEPHONENUM}.
Olayın meydana geldiği adres: Bina [90]{BUILDINGNUM}.
Olay vakti – 14:30.

Olayın tanımı: Şikayetçinin bildirdiğine göre, şahsi malı ve kimlik kartı (son rakamları ****4921) olay yerinden kaybolmuştur. Olay çevresinde “şüpheli” kişilerin olduğuna dair ilk bilgiler gelmiştir. Araştırma devam etmektedir.
```

---

### TR 13 · case, names · sprint1_llm_b6.clean__llm_az_006156

**AZ:**

```
Seher sebekesinde yenileme

[2024-05-22]{DATE} tarihinde yerli texniki infrastrukturun tekmillestirilmesi ile bagli yeni melumatlar paylasildi. [Zaidədəki]{GIVENNAME} texniki otaqda aparilan isler neticesinde sistemin stabilliyi artirildi. [Ceyhunovagildən]{SURNAME} gələn rəsmi rəyə esasen, əsas cihazın MAC ünvanı [0016.3ef1.f347]{MAC_ADDRESS} olaraq qeyd edilir. Etraflı melumat ve sorğular üçün [(099) 815-36-83]{TELEPHONENUM} nomresine elaqe saxlamaq mumkundur.
```

**TR:**

```
Sabah şebekesinde yenileme

[14/06/2024]{DATE} tarihinde yerel teknik altyapının geliştirilmesi ile ilgili yeni bilgiler paylaşıldı. [Türkanhanım'daki]{GIVENNAME} teknik odada yapılan işler sonucunda sistemin stabilitesi artırıldı. [Mehremov]{SURNAME} gelen resmi görüşe göre, ana cihazın MAC adresi [001B.44C4.C376]{MAC_ADDRESS} olarak belirtilir. Detaylı bilgi ve talepler için [+994 77 326 86 43]{TELEPHONENUM} numarasına ulaşmak mümkündür.
```

---

### TR 14 · names · runb_targeted__targeted_az_023441

**AZ:**

```
[Ömerin]{GIVENNAME} müraciətinə hələ baxılmayıb. Mən artıq [Vagif küçəsindəyəm]{STREET}, harada görüşək? Canım [fermayisim]{GIVENNAME}, sənə uğurlar!
Hesabat tələb olunan formada tərtib edilib.
```

**TR:**

```
[Sincab]{GIVENNAME} başvurusuna henüz bakılmadı. Ben çoktan [Süleyman Rüstemzade Bulvarı]{STREET}, nerede görüşelim? Canım [Mövlud]{GIVENNAME}, sana başarılar!
Rapor istenen biçimde düzenlendi.
```

---

### TR 15 · names · repaired.clean__llm_az_123267

**AZ:**

```
Mövzu: Maliyyə əməliyyatlarının təsdiqlənməsi barədə rəsmi bildiriş

Hörmətli [Niyyətxanım]{GIVENNAME} [Fəzlova]{SURNAME},

Bu məktub, 2018-ci ilin cari dövründə sistemimizdə qeydə alınmış maliyyə əməliyyatlarının rəsmiləşdirilməsi və təhlükəsizlik protokollarının icrası məqsədilə sizə göndərilir. Şirkətimizin daxili audit qaydalarına əsasən, aşağıdakı kart vasitəsilə həyata keçirilən əməliyyat üzrə əlavə təsdiq tələb olunur:

Əməliyyat Təsviri   | Kart Nömrəsi
-------------------|-----------------------
Debet Əməliyyatı   | [4784-3848-4828-3059]{PAYMENT_CARD_NUMBER}

Sözügedən əməliyyatın qaydasında olduğunu və hesabın təhlükəsizliyini təmin etmək üçün aşağıdakı sənədlərin təqdim edilməsi zəruridir:

* Şəxsiyyət vəsiqəsinin rəsmi surəti;
* Müvafiq bank çıxarışının kopyası;
* Əməliyyatın mahiyyətini izah edən bəyanat.

Məlumatların təqdim edilməsi gecikdikdə, müvafiq hesabın müvəqqəti dondurulması ehtimalı mövcuddur.

Hörmət və ehtiramla,

Maliyyə Monitorinqi və Təhlükəsizlik Şöbəsi
```

**TR:**

```
Konu: Finansal işlemlerin onaylanması hakkında resmi bildirim

Sayın [Mary]{GIVENNAME} [Elvinova]{SURNAME},

Bu mektup, 2018 yılının cari döneminde sistemimizde kaydedilen finansal işlemlerin resmileştirilmesi ve güvenlik protokollarının uygulanması amacıyla size gönderilir. Şirketimizin iç denetim kurallarına göre, aşağıdaki kart vasıtasıyla gerçekleştirilen işlem için ek onay gerekmektedir:

İşlem Açıklaması   | Kart Numarası
-------------------|-----------------------
Debit İşlemi      | [4824 6886 1096 4452]{PAYMENT_CARD_NUMBER}

Söz konusu işlemin kurallara uygun olduğunu ve hesabın güvenliğini sağlamak için aşağıdaki belgelerin sunulması zorunludur:

* Kimlik belgesinin resmi sureti;
* İlgili banka ekstresinin kopyası;
* İşlemin mahiyetini açıklayan beyan.

Bilgilerin sunulması geciktiğinde, ilgili hesabın geçici olarak dondurulması ihtimali mevcuttur.

Saygılarımla,

Finansal İzleme ve Güvenlik Departmanı
```

---

### TR 16 · year, names · repaired.clean__llm_az_108580

**AZ:**

```
İşçi Performans Hesabatı

Tarix: [15.10.2019]{DATE}
Mövzu: İllik iş göstəricilərinin qiymətləndirilməsi

Maliyyə departamentinin əməkdaşı [Kəmandarova]{SURNAME} xanımın 2019-cu il ərzində göstərdiyi performans göstəriciləri aşağıdakı kimi rəsmiləşdirilmişdir.

İşçi profil məlumatları:
Soyad: [Kəmandarova]{SURNAME}
İşçi nömrəsi: ****5582
Vəzifə: Baş mühasib

[Kəmandarova]{SURNAME} xanım öz vəzifə öhdəliklərini tam və dürüst şəkildə yerinə yetirir. Onun iş qrafikinə və daxili sənədləşmə qaydalarına ciddi riayət etməsi departament daxilində yüksək səviyyədə qiymətləndirilir.
```

**TR:**

```
Çalışan Performans Raporu

Tarih: [22 Ocak 2019]{DATE}
Konu: Yıllık iş göstergelerinin değerlendirilmesi

Finans departmanı çalışanı [Garasultanova]{SURNAME} hanımın 2019 yılında göstermiş olduğu performans göstergeleri aşağıdaki gibi resmileştirilmiştir.

Çalışan profil bilgileri:
Soyadı: [Garasultanova]{SURNAME}
Çalışan numarası: ****5582
Görev: Baş muhasebeci

[Garasultanova]{SURNAME} hanım kendi görev yükümlülüklerini tam ve dürüst bir şekilde yerine getirir. Onun iş programına ve iç dokümantasyon kurallarına ciddi şekilde riayet etmesi departman içerisinde yüksek seviyede değerlendirilmektedir.
```

---

## RU items

### RU 1 · patronymic, names · runb_targeted__targeted_az_022837

**AZ:**

```
Arayış sorğu əsasında hazırlanaraq verilib. Ərizə [Hadiyev]{SURNAME} [Şadalı]{GIVENNAME} [Möhkəm]{GIVENNAME} oğlu adına qəbul edilib.
[Şahbəndiyarov]{SURNAME} [Öcal]{GIVENNAME} [Davıd]{GIVENNAME} oğlu haqqında qərar qəbul olunub.
```

**RU:**

```
Справка подготовлена и выдана на основании запроса. Заявление было принято на имя [Шагбагатов]{SURNAME} [Сабил]{GIVENNAME} [Матвей]{GIVENNAME} оглы.
Принято решение в отношении [Овчуханов]{SURNAME} [Константине]{GIVENNAME} [Юммат]{GIVENNAME} оглы.
```

---

### RU 2 · patronymic, names · sprint1_llm_b6.clean__llm_az_005510

**AZ:**

```
Sened tarixi: [18.08.2021]{DATE}. [Zahidxanova]{SURNAME} [Tirmexatin]{GIVENNAME} [Tunar]{GIVENNAME} qizi ve [Xandemirli]{SURNAME} [Dogmasad]{GIVENNAME} [Mohtesib]{GIVENNAME} oglu [Yeni Yasamal dongesine]{STREET} muraciät, muraciet edirler. [099 986 78-38]{TELEPHONENUM}. Log: active.
```

**RU:**

```
Дата документа: [2021-05-21]{DATE}. [Мооре]{SURNAME} [Париназ]{GIVENNAME} [Арислан]{GIVENNAME} кызы и [Фирдостова]{SURNAME} [Тайфун]{GIVENNAME} [Тафи]{GIVENNAME} оглы [улица Гараллар]{STREET} обрашения (обращения), обращения делают. [+994 50 370 60 25]{TELEPHONENUM}. Log: active.
```

---

### RU 3 · VÖEN, names · repaired.clean__llm_az_118068

**AZ:**

```
Subject: Köməyə ehtiyacım var

Salam,

Mən çox narahatyam və nəsə  tam başa düşmürəm. Hesabıma giriş edə bilmirəm və hər şey çox qarışıqdır. Mənim [61]{AGE} yaşımdır və bu texniki məsələlərlə məşğul olmaq mənim üçün çox çətindir.

Mən [Səyyad]{GIVENNAME}, sizə müraciət edirəm. VÖEN nömrəm [796174979823190]{AZ_VOEN} olmalıdır, amma sistem hər dəfə xəta verir. Həmçinin, e-poçt ünvanım [sifeyre.sahmemmedov@yandex.ru]{EMAIL} olaraq qeyd olunub, lakin heç bir bildiriş gəlmir,  hər şey boş qalır.

Sistemdən belə bir sətir gördüm:
[Səyyad]{GIVENNAME};Gözləmədə;150 AZN;[12.05.2020]{DATE};[796174979823190]{AZ_VOEN}

Başa düşmürəm ki, niyə hər şey bu qədər...

Zəhmət olmasa, kömək edin.

Hörmətlə,
[Səyyad]{GIVENNAME}
```

**RU:**

```
Тема: Мне нужна помощь

Здравствуйте,

Я очень обеспокоен и чего-то не совсем понимаю. Я не могу войти в свой аккаунт, и всё очень запутанно. Мне [62]{AGE} лет, и заниматься этими техническими вопросами для меня очень сложно.

Я [Бегроуз]{GIVENNAME}, обращаюсь к вам. Мой ИНН должен быть [1980356793]{AZ_VOEN}, но система каждый раз выдает ошибку. Кроме того, мой адрес эл. почты указан как [selvi_israfilov@zirve.az]{EMAIL}, но никаких уведомлений не приходит, всё остается пустым.

Я увидел в системе такую строку:
[Бегроуз]{GIVENNAME};В ожидании;150 AZN;[20/04/2020]{DATE};[1980356793]{AZ_VOEN}

Не понимаю, почему всё так...

Пожалуйста, помогите.

С уважением,
[Бегроуз]{GIVENNAME}
```

---

### RU 4 · VÖEN · repaired.clean__llm_az_094708

**AZ:**

```
Bağışlayın, amma mən bu hissədə çox qarışıq və narahat vəziyyətdəyəm. Niyə bu məlumatlar birbaşa kodun içindədir? Məsələn, VÖEN: [3373262713]{AZ_VOEN} burada necə yarana bilər? Bu təhlükəsizlik baxımından düzgün deyil?
> Səhv yazılıb deyə düşünürəm, amma dəqiq deyil...
Mən çox həyəcanlıyam, zəhmət olmasa bunu bir daha yoxlayaq.
```

**RU:**

```
Извините, но я нахожусь в очень замешательстве и в тревожном состоянии в этой части. Почему эти данные находятся прямо внутри кода? Например, как здесь может возникнуть ИНН: [0517957611]{AZ_VOEN}? Разве это не небезопасно?
> Думаю, что написано с ошибкой, но не уверен точно...
Я очень взволнован, пожалуйста, давайте проверим это еще раз.
```

---

### RU 5 · mask · repaired.clean__llm_az_043694

**AZ:**

```
------------------------------------------------------------
| Yönləndirilmiş Səs Mesajı                                |
| Tarix: [14.05.2019]{DATE}                                        |
| Müştəri ID: VM-4492                                     |
------------------------------------------------------------

(Sistem: Səs yazısı avtomatik olaraq mətnə çevrilir)

"Salam, salam! Mən [Qarakişi]{GIVENNAME}, hələ də o köhnə, enerjili [78]{AGE} yaşındayam, amma hələ də dəyişməmişəm! (Qısa gülüş səsi). Sizi narahat etdiyim üçün üzr istəyirəm, amma saat artıq [10:48]{TIME}-dir və mən hələ də sizin zənginizi gözləyirəm.

Mənim nömrəm [+994188118558]{TELEPHONENUM} olacaq. Zəhmət olmasa, məni geri zəng edin. Bu arada, o kartın son rəqəmlərini də tam xatırlamıram, yəqin ki, ****558 idi. Amma eybi yoxdur, zəng edəndə hər şeyi izah edərəm. Hər şey yaxşı olacaq, deyilmi? Hə, hələlik!"
```

**RU:**

```
------------------------------------------------------------
| Перенаправленное голосовое сообщение                      |
| Дата: [26.10.2019]{DATE}                                        |
| ID клиента: VM-4492                                     |
------------------------------------------------------------

(Система: Голосовая запись автоматически преобразуется в текст)

"Привет, привет! Я [Расиг]{GIVENNAME}, мне всё ещё те же старые, энергичные [30]{AGE} лет, но я всё ещё не изменился! (Короткий смешок). Извините, что беспокою вас, но сейчас уже [13:24]{TIME}, а я всё ещё жду вашего звонка.

Мой номер будет [994505145689]{TELEPHONENUM}. Пожалуйста, перезвоните мне. Кстати, я также не совсем помню последние цифры той карты, наверное, это было ****689. Но ничего страшного, когда позвоните, я всё объясню. Всё будет хорошо, правда? Ну, пока!"
```

---

### RU 6 · mask · repaired.clean__llm_az_036430

**AZ:**

```
Xəstə Hesabatı

Məkan: [Qusar]{CITY}
Tarix: [14.06.2022]{DATE}

Klinik qeydlər:
Vəziyyət: Stabil.
Şikayət: Halsızlıq, baş ağrısı, yüngül titrəmə.
Müayinə: Təzyiq 120/80, temperatur 36.6.
Tövsiyə: Dərman qəbulu və tam istirahət.
Növbəti nəzarət: 1 həftə sonra.

İnzibati məlumatlar:
Telefon: [077 911 45 83]{TELEPHONENUM}
Email: [a.ferecov@azertelekom.az]{EMAIL}
Fin kodu: [ESAN78Q]{AZ_FIN}
Kart nömrəsi: [4885905221530696]{PAYMENT_CARD_NUMBER}
Kart son: ****0696
```

**RU:**

```
Отчёт пациента

Место: [Баку]{CITY}
Дата: [1 апреля 2022]{DATE}

Клинические заметки:
Состояние: Стабильное.
Жалоба: Слабость, головная боль, легкий тремор.
Осмотр: Давление 120/80, температура 36.6.
Рекомендация: Приём лекарств и полный отдых.
Следующий контроль: через 1 неделю.

Административная информация:
Телефон: [+994121276865]{TELEPHONENUM}
Email: [fuladcelestunov@zirve.az]{EMAIL}
ФИН код: [FYLAWEL]{AZ_FIN}
Номер карты: [9792715170568964]{PAYMENT_CARD_NUMBER}
Конец карты: ****8964
```

---

### RU 7 · case, names · sprint1_llm_b6.clean__llm_az_007622

**AZ:**

```
2017-ci ildə keçiriləcək “ofis ləvazimatları” tenderi haqqında elan edilir. Tender nömrəsi ****8821 olan bu layihə üçün təkliflər [K 4 prospektində]{STREET} yerləşən mərkəzə təqdim edilməlidir. Əlaqə üçün müdir [Minyashar]{GIVENNAME} [Nurullayev]{SURNAME} ilə əlaqə saxlaya bilərsiniz. Kod: l023.
```

**RU:**

```
Объявляется тендер на «офисные принадлежности», который будет проведен в 2017 году. Предложения по данному проекту под номером тендера ****8821 должны быть представлены в центр, расположенный в [улице 15 Ийун]{STREET}. Для связи вы можете связаться с директором [Шаммад]{GIVENNAME} [Мореау]{SURNAME}. Код: l023.
```

---

### RU 8 · case · runb_targeted__targeted_az_006936

**AZ:**

```
Bələdiyyə [Gölyeri küçəsini]{STREET} genişləndirir. Göndərişin son məntəqəsi [Naxçıvandır]{CITY}. Bu məsələni [Raminəylə]{GIVENNAME} ətraflı müzakirə etdik. Sifariş hazırdır.
```

**RU:**

```
Муниципалитет [переулок 108-джи Зира]{STREET} расширяет. Последний пункт отправления [Маликджанлы]{CITY}. Мы обсудили этот вопрос [Гюлсаной]{GIVENNAME} подробно. Заказ готов.
```

---

### RU 9 · case · sprint1_llm_b5.clean__llm_az_018244

**AZ:**

```
Müştəri şikayəti:
Yaşadığınız narahatlığa görə çox üzr istəyirik. 2023-cü ilin dekabr ayında qeydə alınan sifarişin çatdırılması zamanı ünvanla bağlı texniki bir xəta baş verdi. [Elçin İsrafilzadə küç.indəki]{STREET} xidmət bölgəsində yaranan bu nasazlıq səbəbindən gecikmə yarandı. Səbirli olduğunuz üçün təşəkkür edirik.

Agent qeydləri:
Müştəri ilə əlaqə saxlanıldı və [Üstünə]{GIVENNAME} yeni çatdırılma vaxtı barədə məlumat verildi.
System log: Error in routing.
```

**RU:**

```
Жалоба клиента:
Приносим глубокие извинения за доставленные неудобства. В декабре 2023 года при доставке заказа, зарегистрированного в этот период, произошла техническая ошибка, связанная с адресом. Из-за этой неисправности, возникшей в сервисном регионе [проспект Нураддин Пашаев]{STREET}, возникла задержка. Благодарим вас за терпение.

Заметки агента:
С клиентом была установлена связь и [Елтаку]{GIVENNAME} предоставлена информация о новом времени доставки.
System log: Error in routing.
```

---

### RU 10 · case · runb_targeted__targeted_az_005697

**AZ:**

```
Sənədlər natamamdır.
Hamı qələbəyə əmin idi. [Əminin]{GIVENNAME} maşını həyətdədir.
```

**RU:**

```
Документы неполные.
Все были уверены в победе. Машина [Танрыверди]{GIVENNAME} находится во дворе.
```

---

### RU 11 · year, names · repaired.clean__llm_az_031685

**AZ:**

```
[2026-05-20 14:15:02] [ERROR] Transaction ID #9982: Receipt mismatch.
[2026-05-20 14:15:10] [INFO] System retrying automated print...

QƏBZ DETALLARI:
Müştəri: [Zeynəb]{GIVENNAME}
Ünvan: [Qara Qarayev prospekti]{STREET}
Əlaqə: [+994 55 570 39 93]{TELEPHONENUM}
Email: [zeynalabbasov@xezerlog.az]{EMAIL}
Məbləğ: 145.50 AZN
Tarix: [20.05.2026]{DATE}

Bu nə mənasız işdir? Göndərdiyiniz qəbz tamamilə xətalıdır! Mən bu məbləği ödəmişəm, amma sistemdə hələ də borcum var görünür. Həm də məlumatlarımın bu cür səliqəsiz olması qəbul edilməzdir. Sizin bu laqeydliyinizdən artıq bezmişəm!

> Müştəri Xidmətləri: Hörmətli [Zeynəb]{GIVENNAME} xanım, xahiş edirik, məlumatlarınızı yeniləyin.
> Mən: Yenilədim, amma yenə də eyni səhv! Artıq sizinlə işləmək imkansızdır!
```

**RU:**

```
[2026-05-20 14:15:02] [ERROR] Transaction ID #9982: Receipt mismatch.
[2026-05-20 14:15:10] [INFO] System retrying automated print...

ДЕТАЛИ КВИТАНЦИИ:
Клиент: [Жоан]{GIVENNAME}
Адрес: [переулок Зараган Айдынгышлаг]{STREET}
Связь: [994125308336]{TELEPHONENUM}
Email: [kemandar.sehriyarov2@yahoo.com]{EMAIL}
Сумма: 145.50 AZN
Дата: [2 мая 2026]{DATE}

Что это за бессмысленная работа? Отправленная вами квитанция совершенно ошибочна! Я оплатил эту сумму, но в системе всё ещё числится мой долг. К тому же, то, как небрежно хранятся мои данные, неприемлемо. Я уже сыт по горло вашей беспечностью!

> Служба поддержки: Уважаемая госпожа [Жоан]{GIVENNAME}, пожалуйста, обновите ваши данные.
> Я: Обновил, но всё равно та же ошибка! С вами уже невозможно работать!
```

---

### RU 12 · year, names · repaired.clean__llm_az_035559

**AZ:**

```
------------------------------------------------------------
| Forwarded message from: Police_Internal_Relay            |
| Date: [14.06.2019]{DATE}                                          |
| Subject: Hadisə protokolu                                 |
------------------------------------------------------------

2019-cu ilin iyun ayının 14-də baş vermiş hadisə ilə bağlı rəsmi məlumatdır.

Müraciət edən şəxs: [Samir]{GIVENNAME} [İbrahimov]{SURNAME}.
Əlaqə nömrəsi: [+994 10 211 90 12]{TELEPHONENUM}.
Hadisənin baş verdiyi ünvan: Bina [81]{BUILDINGNUM}.
Hadisə vaxtı – 14:30.

Hadisənin təsviri: Şikayətçinin bildirdiyinə görə, şəxsi əmlakı və şəxsiyyət vəsiqəsi (son rəqəmləri ****4921) hadisə yerindən itmişdir. Hadisə ətrafında “şübhəli” şəxslərin olduğu barədə ilkin məlumatlar daxil olub. Tədqiqat davam etdirilir.
```

**RU:**

```
------------------------------------------------------------
| Пересланное сообщение от: Police_Internal_Relay      |
| Дата: [16/06/2019]{DATE}                                          |
| Тема: Протокол происшествия                         |
------------------------------------------------------------

Это официальная информация относительно происшествия, имевшего место 14 июня 2019 года.

Обратившееся лицо: [Нёвджаван]{GIVENNAME} [Багадыров]{SURNAME}.
Контактный номер: [+994502582562]{TELEPHONENUM}.
Адрес места происшествия: Здание [10]{BUILDINGNUM}.
Время происшествия – 14:30.

Описание происшествия: Согласно заявлению жалобщика, его личное имущество и удостоверение личности (последние цифры ****4921) пропали с места происшествия. Поступила предварительная информация о том, что вокруг происшествия находились «подозрительные» лица. Расследование продолжается.
```

---

### RU 13 · case, names · runb_targeted__targeted_az_019818

**AZ:**

```
Xahiş edirik, məlumatları diqqətlə nəzərdən keçirin. Kuryer artıq [eleddin quliyev dongesinden]{STREET} çıxıb.
Rəhbərlik [Elzaminovanı]{SURNAME} təbrik edib. Bu gün növbətçi əməkdaş [Abiyevdır]{SURNAME}.
```

**RU:**

```
Пожалуйста, внимательно ознакомьтесь с информацией. Курьер уже выехал [ул. Карвансарай]{STREET}.
Руководство поздравило [Сабагбаову]{SURNAME}. Сегодня дежурный сотрудник [Гаманбаов]{SURNAME}.
```

---

### RU 14 · case, names · repaired.clean__llm_az_120845

**AZ:**

```
[Seyidalıya]{GIVENNAME} de ki, [40]{AGE} yaşı var artıq.
[Seyidalı]{GIVENNAME};[40]{AGE};Aktiv
> [Seyidalı]{GIVENNAME}, necəsen?
```

**RU:**

```
[Максиму]{GIVENNAME} скажи, что [70]{AGE} уже есть лет.
[Максим]{GIVENNAME};[70]{AGE};Активен
> [Максим]{GIVENNAME}, как ты?
```

---

### RU 15 · case, names · runb_targeted__targeted_az_006689

**AZ:**

```
Toy [Ahmadilərdə]{SURNAME} keçiriləcək. [Mayisovadakı]{SURNAME} nüsxə imzalanmayıb. Əlavə məlumat yoxdur.
```

**RU:**

```
Свадьба [Еркинаров]{SURNAME} состоится. [Исифова]{SURNAME} копия не подписана. Дополнительной информации нет.
```

---

### RU 16 · names · sprint1_llm_b6.clean__llm_az_005205

**AZ:**

```
Məhkəmə 0rganı tərəfindən ****9821 nömrəli iş üzrə [Zirəddin]{GIVENNAME} [Ziyadzadə]{SURNAME}  və FİN kodu [RHJ8RAT]{AZ_FIN} olan tərəf arasında [10.14.26.179]{IPV4_ADDRESS} IP ünvanı ilə bağlı müzakirə aparılacaqdır.

Məhkəmə Katibi
[Zirəddin]{GIVENNAME} [Ziyadzadə]{SURNAME}
[08/05/2025]{DATE}
```

**RU:**

```
Судебным 0рганом будет проведено обсуждение по делу № ****9821 между [Бабашаг]{GIVENNAME} [Гёкюмов]{SURNAME} и стороной с ФИН кодом [Q3KMC4Q]{AZ_FIN}, связанное с IP-адресом [100.57.157.8]{IPV4_ADDRESS}.

Секретарь суда
[Бабашаг]{GIVENNAME} [Гёкюмов]{SURNAME}
[2025-01-27]{DATE}
```

---
