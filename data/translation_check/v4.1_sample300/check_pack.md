# Translation check pack: v4.1 train sample, EN / TR / RU

Made from `main` at f13051f (problem B #104, weekdays #105, repeat mentions #106), with the overnight launcher at concurrency 40.

Each item shows the Azerbaijani source, then the translation. Labelled values are shown as `[value]{LABEL}`. In the translation they are freshly minted, so they differ from the source on purpose.

**What to check:**

- the translation reads naturally;
- no Azerbaijani words are left;
- every `[value]{LABEL}` has the right label and covers exactly the value;
- the same person or place keeps one name throughout;
- look-alikes (unlabelled values) come through unchanged;
- dates have no weekday inside the brackets.

The full outputs are next to this file: `en.jsonl`, `tr.jsonl`, `ru.jsonl`, plus the Azerbaijani source `az_source.jsonl`.

## EN

### EN 1 · llm · sprint1_llm_b6.clean__llm_az_015101

**AZ:**

```
----- Forwarded message -----
[2024-05-15 09:45]

[Cövri]{GIVENNAME} [Eldarlı]{SURNAME} mür. doldurdu.
Ad: [Ərkixanım]{GIVENNAME}
SOYAD: [ELDARLI]{SURNAME}
Zəhmət olmasa, [Ərkixanımı]{GIVENNAME} qeyd edin və sənədi yoxlayın, xəta olmasın.
```

**EN:**

```
----- Forwarded message -----
[2024-05-15 09:45]

[Taftanisa]{GIVENNAME} [Fərəczadə]{SURNAME} filled out the application.
Name: [Afig]{GIVENNAME}
SURNAME: [Fərəczadə]{SURNAME}
Please, note [Afig]{GIVENNAME} and check the document, so there are no errors.
```

---

### EN 2 · llm · sprint1_llm_b1.clean__llm_az_005173

**AZ:**

```
# 2025-ci il üçün təsdiq edilmiş rəsmi konfiqurasiya sənədi
# L0g_Sistemi nizamlamaları:

# Aşağıdakı parametrlər rəsmi sənədləşməyə əsasən müəyyən edilmişdir:

Parametr_Növü      | Müvafiq_Dəyər
-------------------|-----------------------------------------------------------------------
Əsas_E-poçt        | [cemil3729@xezerlog.az]{EMAIL}
Giriş_Tokeni       | [1277e4a8df1af4fcd4eddde5627a3d9ff786faa22e3baa83e4f89aad0de40c]{ACCESS_TOKEN}
Sənəd_Tarixi       | 32.03.1997
Sistem_Kodu        | 5YJTD7862X6048343

# Məlumatlar rəsmi nizamlamalara uyğun olaraq tətbiq olunmalıdır.
```

**EN:**

```
# Approved official configuration document for 2025
# L0g_System regulations:

# The following parameters have been determined based on official documentation:

Parameter_Type      | Corresponding_Value
-------------------|-----------------------------------------------------------------------
Main_Email        | [u.uluxanov@list.az]{EMAIL}
Input_Token       | [pat_ce84d166c6f422bd9569bc95a3caf45075669206b8a067f83183f7b52]{ACCESS_TOKEN}
Document_Date       | 32.03.1997
System_Code        | 5YJTD7862X6048343

# Data must be applied in accordance with official regulations.
```

---

### EN 3 · llm · sprint1_llm_b6.clean__llm_az_005510

**AZ:**

```
Sened tarixi: [18.08.2021]{DATE}. [Zahidxanova]{SURNAME} [Tirmexatin]{GIVENNAME} [Tunar]{GIVENNAME} qizi ve [Xandemirli]{SURNAME} [Dogmasad]{GIVENNAME} [Mohtesib]{GIVENNAME} oglu [Yeni Yasamal dongesine]{STREET} muraciät, muraciet edirler. [099 986 78-38]{TELEPHONENUM}. Log: active.
```

**EN:**

```
Document date: [05.12.1960]{DATE}. [Howard]{SURNAME} [Астон]{GIVENNAME} [Xudayat]{GIVENNAME} daughter and [Sirəddinova]{SURNAME} [Ganiyya]{GIVENNAME} [Nuri]{GIVENNAME} son [Takhta Korpu Lane]{STREET} application, they are applying. [077 276 55-44]{TELEPHONENUM}. Log: active.
```

---

### EN 4 · old · repaired.clean__llm_az_100343

**AZ:**

```
----------------------------------------
Yönləndirilmiş mesaj: [15.05.2020]{DATE}
Mövzu: Texniki xəta haqqında
----------------------------------------
Müştəri ilə əlaqə saxlanıldı. Sistem loglarında aşağıdakı token xətası aşkar olunub:
Authorization: Bearer [Kp0omy65UJ8tnWYr8-8aw-ey0vwOUckCmBoL.WsUHBEFQzY3tvWa66fSbLglBEr-R_NJHc2XfUWOnHzEVBQmA5dbaawNHlk94DIsiFwBCzBrkDerRj6Di4-rBHkoaQ.HvgcrMICKWjwl1hOsbUsFf6j1ywNyYaRky5M3uLHaFZ]{ACCESS_TOKEN}
Məsələnin dərhal həll edilməsi vacibdir, əks halda müqavilə şərtləri tətbiq olunacaq.
```

**EN:**

```
----------------------------------------
Forwarded message: [18.02.1968]{DATE}
Subject: Regarding technical error
----------------------------------------
Contact was made with the customer. The following token error was discovered in the system logs:
Authorization: Bearer [at_Lk-w3mnwtfdRhQRrserraqZr1s65bvJVQT8]{ACCESS_TOKEN}
Immediate resolution of the issue is vital, otherwise contract terms will be applied.
```

---

### EN 5 · old · repaired.clean__llm_az_062014

**AZ:**

```
Xidmətlərinizdən çox razı qaldıq, hər şey əla idi! Babamın doğum tarixi: [1946-12-11]{DATE} kimi sistemdə qeyd olunub və biz bu məlumatı tamamilə doğru hesab edirik. Sizinlə işləmək bizim üçün çox xoş idi, göstərdiyiniz diqqətə görə çox sağ olun!
```

**EN:**

```
We were very satisfied with your services, everything was excellent! My grandfather's date of birth: [05/08/2025]{DATE} is recorded in the system and we consider this information to be completely correct. It was a great pleasure working with you, thank you very much for the attention you showed!
```

---

### EN 6 · old · repaired.clean__llm_az_079642

**AZ:**

```
Yönləndirilmiş mesaj:
Töndərən: Sistem
[[2025-01-10]{DATE}] XƏTA: [hekkakovs@mail.az]{EMAIL}. ID: ****9901.
---
Həkim
[hekkakovs@mail.az]{EMAIL}
```

**EN:**

```
Forwarded message:
Sender: System
[[August 25, 2019]{DATE}] ERROR: [sirbabayevk@azdata.az]{EMAIL}. ID: ****9901.
---
Doctor
[sirbabayevk@azdata.az]{EMAIL}
```

---

### EN 7 · targeted · runb_targeted__targeted_az_023441

**AZ:**

```
[Ömerin]{GIVENNAME} müraciətinə hələ baxılmayıb. Mən artıq [Vagif küçəsindəyəm]{STREET}, harada görüşək? Canım [fermayisim]{GIVENNAME}, sənə uğurlar!
Hesabat tələb olunan formada tərtib edilib.
```

**EN:**

```
[Ellarə]{GIVENNAME} application has not been reviewed yet. I am already [Fatullah Mammadov St.]{STREET}, where shall we meet? My dear [Bircəbəyim]{GIVENNAME}, good luck to you!
The report has been prepared in the required form.
```

---

### EN 8 · targeted · runb_targeted__targeted_az_012055

**AZ:**

```
Elektron kabinetdə VÖEN: [6262650624]{AZ_VOEN} kimi saxlanılır.
Elektron kabinetdə VÖEN 687 kimi saxlanılır.
```

**EN:**

```
In the electronic cabinet, TIN: [7814705015]{AZ_VOEN} is stored.
In the electronic cabinet, TIN 687 is stored.
```

---

## TR

### TR 1 · llm · sprint1_llm_b5.clean__llm_az_013034

**AZ:**

```
[14:20] Salam, sistemdə ciddi bir nasazliq aşkar olunub.
[14:21] Zehmət olmasa, baxın. Sistmde xəta var, yəni sistemdə xəta var. Session log entry: [pat_0dI7yZmskzXwtUNrxWop]{ACCESS_TOKEN}. Zəhmət olmasa, bu məlumatı dərhal araşdırın.
```

**TR:**

```
[14:20] Selam, sistemde ciddi bir arıza tespit edildi.
[14:21] Lütfen bakın. Sistemde hata var, yani sistemde hata var. Session log entry: [at_y-IgF-wqhsmLTpTsNgjqMo5JqHkJPVVlSr9CIjVwRwwkMWA9]{ACCESS_TOKEN}. Lütfen bu bilgiyi derhal araştırın.
```

---

### TR 2 · llm · sprint1_llm_b5.clean__llm_az_010006

**AZ:**

```
[78]{BUILDINGNUM} nömrəli binada yerləşən ünvan üzrə sənədləri tez göndərin, yoxsa hüquqi prosedurlar gələcək ki, heç də gülməli olmayacaq.
```

**TR:**

```
[112]{BUILDINGNUM} numaralı binada yer alan adres üzerine belgeleri hızlı gönderin, aksi takdirde hukuki prosedurlar gelecek ki hiç de gülünç olmayacak.
```

---

### TR 3 · llm · sprint1_llm_b6.clean__llm_az_023921

**AZ:**

```
Məhkəmə tərəfindən təqdim olunan sənədlərdə qeyd olunduğu kimi, mübahisə predmeti olan ərazinin poçt indeksi [AZ1063]{ZIPCODE} şəklində müəyyən edilmişdir. Bu məlumatın təsdiqlənməsi mütləqdir.
```

**TR:**

```
Mahkeme tarafından sunulan belgelerde belirtildiği gibi, uyuşmazlık konusu olan alanın posta kodu [AZ2010]{ZIPCODE} şeklinde belirlenmiştir. Bu bilginin teyit edilmesi zorunludur.
```

---

### TR 4 · old · repaired.clean__llm_az_036430

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
Tarih: [21. Temmuz 1969]{DATE}

Klinik notlar:
Durum: Stabil.
Şikayet: Halsızlık, baş ağrısı, hafif titreme.
Muayene: Tansiyon 120/80, sıcaklık 36.6.
Öneri: İlaç kullanımı ve tam istirahat.
Sonraki kontrol: 1 hafta sonra.

İdari bilgiler:
Telefon: [+994705972635]{TELEPHONENUM}
E-posta: [mehdiyev.h@box.az]{EMAIL}
Fin kodu: [453LPGD]{AZ_FIN}
Kart numarası: [5202-4014-9838-1123]{PAYMENT_CARD_NUMBER}
Kart son: ****0696
```

---

### TR 5 · old · repaired.clean__llm_az_055705

**AZ:**

```
[2020-03-15 14:20] Log: System error.
[2020-03-15 14:22] Log: Timeout.
Yenə eyni problem! Müştəri deyir ki, [https://link.company.az/invite?session_id=U_ybgm8if0YPY8Qd2O-4zk9QjAFS2]{URL} linki  açılmır. Üstəlik, [pk_live_YOcDtTCULErToWWtGyVESs2vQ]{API_KEY} açarı da xəta verir. Kartın son rəqəmləri ****4004 olan müştəri  çox narazıdır. Bu ləngiMələr dəhşətdir.
```

**TR:**

```
[2020-03-15 14:20] Log: Sistem hatası.
[2020-03-15 14:22] Log: Zaman aşımı.
Yine aynı problem! Müşteri [http://my.xezerlog.az/v2/auth?t=zngVV0kxgAKTA-IKZBHtppyzzc_BCU-Gj4H9gxKRd1H3p]{URL} linkinin açılmadığını söylüyor. Üstelik, [api_jAM4gdFYtyRamkttAkEjRdCJKIIXivwC]{API_KEY} anahtarı da hata veriyor. Kartın son rakamları ****4004 olan müşteri çok memnuniyetsiz. Bu gecikmeler korkunç.
```

---

### TR 6 · old · repaired.clean__llm_az_004532

**AZ:**

```
[Emin]{GIVENNAME}, borcunuz dərhal ödənilməlidir! Kart: [5360 4063 9288 0524]{PAYMENT_CARD_NUMBER}. Məbləğ;Tarix;Status: 150;2023;Gecikmiş. ID: O892
```

**TR:**

```
[Tinati]{GIVENNAME}, borcunuz derhal odenmelidir! Kart: [4905-3460-6862-4894]{PAYMENT_CARD_NUMBER}. Tutar;Tarih;Durum: 150;2023;Gecikmiş. ID: O892
```

---

### TR 7 · targeted · runb_targeted__targeted_az_025817

**AZ:**

```
Tərəflər öhdəliklərini vaxtında yerinə yetirməlidir.
CVC: 34432
Bank kartı: [4547 6349 6396 6880]{PAYMENT_CARD_NUMBER}
E-poçt: sixahmad.konalzada.portal.org
Müqavilənin tarixi: 23.17.2001
```

**TR:**

```
Taraflar yükümlülüklerini zamanında yerine getirmelidir.
CVC: 34432
Banka kartı: [9792068086605771]{PAYMENT_CARD_NUMBER}
E-posta: sixahmad.konalzada.portal.org
Sözleşmenin tarihi: 23.17.2001
```

---

### TR 8 · targeted · runb_targeted__targeted_az_006689

**AZ:**

```
Toy [Ahmadilərdə]{SURNAME} keçiriləcək. [Mayisovadakı]{SURNAME} nüsxə imzalanmayıb. Əlavə məlumat yoxdur.
```

**TR:**

```
Düğün [Hurşidov]{SURNAME} yapılacak. [Chaladze]{SURNAME} nüsha imzalanmadı. Ek bilgi yok.
```

---

## RU

### RU 1 · llm · sprint1_llm_b1.clean__llm_az_009308

**AZ:**

```
Tarix: [12.08.2018]{DATE}

SALAM.

Sim kart aktivləşmir. ICCID: [89994194082409040518]{ICCID}. Zəhmət olmasa, problemi dərhal həll edin. Məlumat gözləyirəm.

Təşəkkürlər,
Müştəri
```

**RU:**

```
Дата: [8 октября 1949]{DATE}

ЗДРАВСТВУЙТЕ.

Сим-карта не активируется. ICCID: [89994974973441120696]{ICCID}. Пожалуйста, немедленно решите проблему. Жду информацию.

Спасибо,
Клиент
```

---

### RU 2 · llm · sprint1_llm_b6.clean__llm_az_005205

**AZ:**

```
Məhkəmə 0rganı tərəfindən ****9821 nömrəli iş üzrə [Zirəddin]{GIVENNAME} [Ziyadzadə]{SURNAME}  və FİN kodu [RHJ8RAT]{AZ_FIN} olan tərəf arasında [10.14.26.179]{IPV4_ADDRESS} IP ünvanı ilə bağlı müzakirə aparılacaqdır.

Məhkəmə Katibi
[Zirəddin]{GIVENNAME} [Ziyadzadə]{SURNAME}
[08/05/2025]{DATE}
```

**RU:**

```
Судебным 0рганом будет проведено обсуждение по делу № ****9821 между [Нариман]{GIVENNAME} [Зайигов]{SURNAME} и стороной с ФИН-кодом [KMC4QZ0]{AZ_FIN}, связанное с IP-адресом [213.77.49.69]{IPV4_ADDRESS}.

Секретарь суда
[Нариман]{GIVENNAME} [Зайигов]{SURNAME}
[17 апреля 1996]{DATE}
```

---

### RU 3 · llm · sprint1_llm_b5.clean__llm_az_018244

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
Приносим глубокие извинения за доставленные неудобства. В декабре 2023 года при доставке заказа, зарегистрированного в этот период, произошла техническая ошибка, связанная с адресом. Из-за этой неисправности, возникшей в сервисном регионе [проспект Нураддин Пашаев]{STREET}, произошла задержка. Благодарим вас за терпение.

Заметки агента:
С клиентом была установлена связь и предоставлена информация о новом времени доставки [И̇сиф]{GIVENNAME}.
System log: Error in routing.
```

---

### RU 4 · old · repaired.clean__llm_az_021952

**AZ:**

```
Tarix: [15.05.2017]{DATE}

Hörmətli [Nəsirov]{SURNAME} bəy, yenə biz! Narahat olmayın, bu ayın hesabı keçən aydan qorxulu deyil, əksinə, bir az daha yüngüldür! :)

Sizin internet və telefon xidmətləriniz üçün aylıq hesabat:
Hesabın hazırlandığı vaxt: [14:01]{TIME}.
Əgər hər hansı bir sualınız olarsa, bizə [022-737-36-70]{TELEPHONENUM} nömrəsi ilə zəng edə bilərsiniz. Biz hər zaman buradayıq və sizə gülərüzlə cavab verməyə hazırıq.

Xidmət_Növü;Müştəri_Soyadı;Məbləğ;Status;2017_Hesab;[Nəsirov]{SURNAME};25.50;Ödənilib

Gününüz aydın, internetiniz sürətli olsun!
```

**RU:**

```
Дата: [21.11.1993]{DATE}

Уважаемый господин [Абайли]{SURNAME}, снова мы! Не беспокойтесь, счет за этот месяц не страшнее, чем в прошлом, наоборот, он даже немного легче! :)

Ваш ежемесячный отчет по интернет- и телефонным услугам:
Время подготовки счета: [12:23]{TIME}.
Если у вас возникнут какие-либо вопросы, вы можете позвонить нам по номеру [018 718 89-62]{TELEPHONENUM}. Мы всегда здесь и готовы ответить вам с улыбкой.

Вид_Услуги;Фамилия_Клиента;Сумма;Статус;2017_Счет;[Абайли]{SURNAME};25.50;Оплачено

Пусть ваш день будет светлым, а интернет — быстрым!
```

---

### RU 5 · old · repaired.clean__llm_az_108580

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

**RU:**

```
Отчёт о производительности сотрудника

Дата: [29.03.1980]{DATE}
Тема: Оценка ежегодных показателей работы

Показатели производительности сотрудника финансового департамента госпожи [Дуралбаова]{SURNAME} за 2019 год оформлены следующим образом.

Данные профиля сотрудника:
Фамилия: [Дуралбаова]{SURNAME}
Номер сотрудника: ****5582
Должность: Главный бухгалтер

Госпожа [Дуралбаова]{SURNAME} выполняет свои должностные обязанности в полном объёме и добросовестно. Её строгое соблюдение графика работы и правил внутреннего документооборота высоко оценивается внутри департамента.
```

---

### RU 6 · old · repaired.clean__llm_az_024805

**AZ:**

```
[2024-05-10 14:15:22] [CRITICAL] Müştəri əlaqə saxlamır.

---------- Forwarded message ----------
From: Satış Departamenti
Date: [10 May 2024]{DATE}

Müştəri ilə əlaqə qurmaq mümkün deyil. [(012) 320-29-76]{TELEPHONENUM} nömrəsinə zəng edirik, amma cavab yoxdur. Satış itir, dərhal müdaxilə lazımdır!

---
Satış Meneceri
```

**RU:**

```
[2024-05-10 14:15:22] [CRITICAL] Клиент не выходит на связь.

---------- Forwarded message ----------
From: Отдел продаж
Date: [17 августа 1972]{DATE}

С клиентом невозможно установить связь. Звоним на номер [050 152 45-99]{TELEPHONENUM}, но ответа нет. Продажа теряется, требуется немедленное вмешательство!

---
Менеджер по продажам
```

---

### RU 7 · targeted · runb_targeted__targeted_az_022837

**AZ:**

```
Arayış sorğu əsasında hazırlanaraq verilib. Ərizə [Hadiyev]{SURNAME} [Şadalı]{GIVENNAME} [Möhkəm]{GIVENNAME} oğlu adına qəbul edilib.
[Şahbəndiyarov]{SURNAME} [Öcal]{GIVENNAME} [Davıd]{GIVENNAME} oğlu haqqında qərar qəbul olunub.
```

**RU:**

```
Подготовлено и выдано на основании запроса. Заявление принято на имя сына [Юмидханов]{SURNAME} [Туда]{GIVENNAME} [Овхан]{GIVENNAME}.
Принято решение в отношении сына [Маисурадзе]{SURNAME} [Юммат]{GIVENNAME} [Анадил]{GIVENNAME}.
```

---

### RU 8 · targeted · runb_targeted__targeted_az_012055

**AZ:**

```
Elektron kabinetdə VÖEN: [6262650624]{AZ_VOEN} kimi saxlanılır.
Elektron kabinetdə VÖEN 687 kimi saxlanılır.
```

**RU:**

```
В электронном кабинете VÖEN: [0776890563]{AZ_VOEN} хранится.
В электронном кабинете VÖEN 687 хранится.
```

---
