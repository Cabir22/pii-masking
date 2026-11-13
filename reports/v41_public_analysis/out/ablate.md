# Ablation: which other sentence blocks v4 (track R)

Each other sentence of the document deleted in turn; a blocker is a deletion that brings the exact span back.

## IPV6_ADDRESS: 123 v4 misses, 58 brought back by deleting one other sentence

| blockers per miss | misses |
|---|---|
| 0 | 65 |
| 1 | 28 |
| 2 | 13 |
| 3+ | 17 |

### What the blocking sentences hold (benchmark plants, digits as 9)

| plant | n |
|---|---|
| `nothing planted` | 118 |
| `hard negative: 999` | 3 |
| `distractor: müqavilə bəndi 9.9.9` | 3 |
| `hard negative: 9999` | 2 |
| `distractor: versiya v9.99.99` | 2 |
| `hard negative: 99999` | 2 |
| `hard negative: 999999` | 2 |
| `hard negative: AB-99` | 2 |
| `hard negative: a***.b***@company.com` | 1 |
| `distractor: versiya v9.9.99` | 1 |
| `distractor: faktura INV/9999/99999` | 1 |
| `hard negative: 9999999999` | 1 |
| `distractor: müqavilə bəndi 99.9.9` | 1 |
| `distractor: daxili istinad REF999999` | 1 |
| `hard negative: P99999999` | 1 |
| `hard negative: 99:99:99` | 1 |
| `hard negative: 99:99` | 1 |
| `hard negative: ---` | 1 |
| `hard negative: AZ9999` | 1 |
| `distractor: versiya v9.99.9` | 1 |
| `hard negative: 99 May bayramı` | 1 |
| `hard negative: AA-999` | 1 |
| `hard negative: 99.99.9999` | 1 |

### Blocking sentences by shape

| sentence | n |
|---|---|
| `Eyni qeyddə tracking kodu üçün 9999999999999999 göstərilib;` | 4 |
| `Tracking kodu məlumatında 9999999999999999 kodu qeyd olunub;` | 4 |
| `Tarixçədə müqavilə bəndi 9.9.9 ilə əlaqəli ayrıca qeyd var.` | 3 |
| `Sənədin digər hissəsində müqavilə bəndi olaraq 99.9.9 yazılıb.` | 2 |
| `Sənədin digər hissəsində tracking kodu olaraq 9999999999999999 yazılıb;` | 2 |
| `Sənədin digər hissəsində otaq olaraq 999 yazılıb;` | 2 |
| `Tarixçədə versiya v9.99.99 ilə əlaqəli ayrıca qeyd var;` | 2 |
| `Əlavə hissədə tracking kodu məlumatı 9999999999999999 kimi saxlanılıb;` | 2 |
| `-----END PRIVATE KEY-----;` | 2 |
| `Versiya məlumatında v9.99.99 kodu qeyd olunub.` | 2 |
| `Qeydiyyat tarixçəsində FIN olaraq 999999 saxlanılıb;` | 2 |
| `Müqavilə bəndi məlumatında 99.9.9 kodu qeyd olunub.` | 2 |
| `Müqavilə bəndi məlumatında 9.9.9 kodu qeyd olunub.` | 1 |
| `Eyni qeyddə faktura üçün INV/9999/99999 gosterilib;` | 1 |
| `yazışma nüsxəsi noyabr dövrü üçün keyfiyyət bölməsində tarixçəyə daxil edilib.` | 1 |
| `Email sahəsində a***.b***@company.com yazılıb;` | 1 |
| `surəti sənəd dövriyyəsi bölməsinin iyun arxivində profil çıxarışı ilə iş materiallarına əl` | 1 |
| `Formanı mən doldurmuşam;` | 1 |
| `istifadə etdiyim məlumatları burada təkrar qeyd edirəm;` | 1 |
| `xidmət jurnalı iyul dövrü üçün abonent xidmətləri bölməsində qovluğa əlavə olunub.` | 1 |
| `Tarixçədə versiya v9.9.99 ilə əlaqəli ayrıca qeyd var.` | 1 |
| `CVV sahəsində 9999 yazılıb;` | 1 |
| `Sənədin digər hissəsində arxiv qovluğu olaraq ARX-9999 yazılıb;` | 1 |
| `Tarixçədə faktura INV/9999/99999 ilə əlaqəli ayrıca qeyd var;` | 1 |
| `Ərizədə yaş kimi 999 qeyd olunub;` | 1 |
| `muraciet əlavəsi avqust dövrü üçün keyfiyyət bölməsində iş materiallarına əlavə edilib.` | 1 |
| `Köhnə profildə küçə olaraq 999 görünür;` | 1 |
| `surəti korporativ xidmətlər bölməsinin iyul arxivində profil çıxarışı ilə qovluğa əlavə ol` | 1 |
| `avqust ayında arxiv bölməsində müraciət paketi daxilində də tarixçəyə daxil edilib.` | 1 |
| `Hesab üzrə növbəti əlaqə bu qeyddən sonra planlaşdırılıb;` | 1 |

### Examples

- bench_az_000028 `2001:db8::31de`: `Müqavilə bəndi məlumatında 2.8.9 kodu qeyd olunub.` / `Eyni qeyddə faktura üçün INV/2023/35717 gosterilib;`
- bench_az_000266 `2001:db8::6f56`: `Eyni qeyddə tracking kodu üçün 9920561726723051 göstərilib;` / `Email sahəsində a***.b***@company.com yazılıb;`
- bench_az_000466 `fd00::e8cc:4421`: `surəti sənəd dövriyyəsi bölməsinin iyun arxivində profil çıxarışı ilə iş materiallarına əlavə edilib.` / `Sənədin digər hissəsində müqavilə bəndi olaraq 13.1.6 yazılıb.`
- bench_az_000638 `2001:db8::e6c0`: `Formanı mən doldurmuşam;` / `istifadə etdiyim məlumatları burada təkrar qeyd edirəm;`
- bench_az_000712 `fd00::1cc4:9f7a`: `Sənədin digər hissəsində arxiv qovluğu olaraq ARX-4472 yazılıb;`
- bench_az_000901 `fd00::106e:7a04`: `Tracking kodu məlumatında 9582158565152893 kodu qeyd olunub;` / `Tarixçədə faktura INV/2025/70172 ilə əlaqəli ayrıca qeyd var;`
- bench_az_001072 `fd00::6f2b:2284`: `Sənədin digər hissəsində tracking kodu olaraq 3366105727489810 yazılıb;` / `Sənədin digər hissəsində otaq olaraq 776 yazılıb;`
- bench_az_001094 `2001:db8::fc7`: `Salam, hesabımla bağlı məlumatları bir mesajda göndərirəm;` / `həmin məlumat korporativ xidmətlər komandasının fevral üzrə sistem qeydi sənədində birlikdə saxlanılıb.`
- bench_az_001200 `fd00::1572:d1f7`: `Sənədin digər hissəsində məhsul olaraq AX-61184 yazılıb;` / `Şirkətin VÖEN-i 1573160471 kimi gostrılıb;`
- bench_az_001209 `fd00::7fe0:ef9a`: `Əlavə hissədə tracking kodu məlumatı 0875352578991068 kimi saxlanılıb;` / `Sənədin digər hissəsində müqavilə bəndi olaraq 10.1.4 yazılıb.`
- bench_az_001301 `fd00::d66c:440e`: `Sürücülük vəsiqəsi sahəsində 0501234567 yazılıb;`
- bench_az_001367 `2001:db8::cd4c`: `Arxivdə FIN kodu 59324 kimi görünür;`

## IPV4_ADDRESS: 59 v4 misses, 16 brought back by deleting one other sentence

| blockers per miss | misses |
|---|---|
| 0 | 43 |
| 1 | 4 |
| 2 | 2 |
| 3+ | 10 |

### What the blocking sentences hold (benchmark plants, digits as 9)

| plant | n |
|---|---|
| `nothing planted` | 58 |
| `hard negative: 99.99.9999` | 1 |
| `distractor: arxiv qovluğu ARX-9999` | 1 |
| `distractor: məhsul TR-99999` | 1 |
| `hard negative: AA:BB:CC:DD` | 1 |
| `hard negative: 999999999999999` | 1 |
| `distractor: sifariş ORD-99999` | 1 |
| `hard negative: 999` | 1 |
| `distractor: faktura INV/9999/99999` | 1 |
| `hard negative: AA99` | 1 |
| `hard negative: 9999:::9999` | 1 |
| `hard negative: IBAN yoxdur` | 1 |
| `hard negative: soyad yoxdur` | 1 |
| `hard negative: 9999` | 1 |
| `hard negative: 99:99 versiyası` | 1 |
| `hard negative: 99:99:99` | 1 |

### Blocking sentences by shape

| sentence | n |
|---|---|
| `surəti risk nəzarəti bölməsinin noyabr arxivində müraciət paketi ilə ayrıca qeyd edilib.` | 1 |
| `Əlavə hissədə daxili istinad məlumatı REF999999 kimi saxlanılıb;` | 1 |
| `dekabr ayında hesablaşmalar bölməsində arxiv qeydi daxilində də ayrıca qeyd edilib.` | 1 |
| `hesab çıxarışı may dövrü üçün texniki dəstək bölməsində arxivə köçürülüb.` | 1 |
| `hesab çıxarışı oktyabr dövrü üçün müştəri xidmətləri bölməsində eyni paketə daxil edilib.` | 1 |
| `Sənədin digər hissəsində versiya olaraq v9.99.99 yazılıb.` | 1 |
| `Sığorta dosyesində profil, ünvan və texniki məlumatlar eyni qeyddə göstərilib;` | 1 |
| `Tarix sahəsində 99.99.9999 yazılıb.` | 1 |
| `Tarixçədə arxiv qovluğu ARX-9999 ilə əlaqəli ayrıca qeyd var;` | 1 |
| `Sığorta dosyesində əlaqə və sənəd məlumatları eyni blokda toplanıb;` | 1 |
| `surəti texniki dəstək bölməsinin iyul arxivində hesab çıxarışı ilə birlikdə saxlanılıb.` | 1 |
| `Küçə olaraq Nüsrət Kəsəmənli küçəsi göstərilib;` | 1 |
| `may ayında risk nəzarəti bölməsində muracət paketi daxilində də tarixçəyə daxil edilib.` | 1 |
| `Tarixçədə məhsul TR-99999 ilə əlaqəli ayrıca qeyd var;` | 1 |
| `surəti təhlükəsizlik bölməsinin fevral arxivində iş qovluğu ilə eyni paketə daxil edilib.` | 1 |
| `Ödəniş kartı olaraq 9999 9999 9999 9999 yazılıb;` | 1 |
| `həmin məlumat təhlükəsizlik komandasının oktyabr üzrə gündəlik qeyd sənədində arxivə köçür` | 1 |
| `Profil üzrə ad Hənəfi qeyd olunub;` | 1 |
| `mart ayında hesablaşmalar bölməsində muracət paketi daxilində də iş materiallarına əlavə e` | 1 |
| `arxiv qeydi yanvar dövrü üçün əməliyyat dəstəyi bölməsində birlikdə saxlanılıb.` | 1 |
| `gündəlik qeyd iyun dövrü üçün hesablaşmalar bölməsində qovluğa əlavə olunub.` | 1 |
| `sistem qeydi aprel dövrü üçün qeydiyyat bölməsində qovluğa əlavə olunub.` | 1 |
| `Əlavə hissədə məhsul məlumatı AX-99999 kimi saxlanılıb;` | 1 |
| `Köhnə şəbəkə profilində AA:BB:CC:DD görünür;` | 1 |
| `Bankın daxili yazışmasında formadan və sistem tarixçəsindən gələn sahələr bir yerdə görünü` | 1 |
| `xidmət jurnalı iyun dövrü üçün müqavilələr bölməsində birlikdə saxlanılıb.` | 1 |
| `Köhnə odenis tarixçəsində kart 999999999999999 görünür;` | 1 |
| `profil çıxarışı dekabr dövrü üçün qeydiyyat bölməsində iş materiallarına əlavə edilib.` | 1 |
| `Kampaniya məlumatında CMP-9999 kodu qeyd olunub;` | 1 |
| `həmin məlumat risk nəzarəti komandasının iyul üzrə sənəd paketi sənədində qovluğa əlavə ol` | 1 |

### Examples

- bench_az_000470 `192.172.139.74`: `surəti risk nəzarəti bölməsinin noyabr arxivində müraciət paketi ilə ayrıca qeyd edilib.` / `Əlavə hissədə daxili istinad məlumatı REF287877 kimi saxlanılıb;`
- bench_az_000510 `165.79.175.28`: `Sığorta dosyesində profil, ünvan və texniki məlumatlar eyni qeyddə göstərilib;` / `Tarix sahəsində 99.99.9999 yazılıb.`
- bench_az_001137 `216.89.216.218`: `Sığorta dosyesində əlaqə və sənəd məlumatları eyni blokda toplanıb;` / `surəti texniki dəstək bölməsinin iyul arxivində hesab çıxarışı ilə birlikdə saxlanılıb.`
- bench_az_001391 `154.77.123.94`: `arxiv qeydi yanvar dövrü üçün əməliyyat dəstəyi bölməsində birlikdə saxlanılıb.` / `gündəlik qeyd iyun dövrü üçün hesablaşmalar bölməsində qovluğa əlavə olunub.`
- bench_az_001399 `141.91.211.68`: `sistem qeydi aprel dövrü üçün qeydiyyat bölməsində qovluğa əlavə olunub.` / `Əlavə hissədə məhsul məlumatı AX-18808 kimi saxlanılıb;`
- bench_az_001566 `111.130.138.126`: `Bankın daxili yazışmasında formadan və sistem tarixçəsindən gələn sahələr bir yerdə görünür;` / `xidmət jurnalı iyun dövrü üçün müqavilələr bölməsində birlikdə saxlanılıb.`
- bench_az_001631 `42.19.87.229`: `cRM qeydində formadan və sistem tarixçəsindən gələn sahələr bir yerdə görünür;` / `Tarixçədə sifariş ORD-12107 ilə əlaqəli ayrıca qeyd var;`
- bench_az_003169 `46.111.212.245`: `Hesabatın müvafiq hissəsində əvvəlki yazışmadan götürülən məlumatlar yeni müraciətə əlavə olunub;`
- bench_az_003422 `114.104.25.240`: `Tarixçədə faktura INV/2026/12655 ilə əlaqəli ayrıca qeyd var;`
- bench_az_003524 `245.214.103.62`: `Bankın daxili yazışmasında bir neçə mənbədən gələn məlumatlar birlikdə saxlanılıb;` / `həmin məlumat əməliyyat dəstəyi komandasının aprel üzrə əməliyyat qeydi sənədində sənədlə birlikdə qorunub.`
- bench_az_003933 `198.186.38.57`: `Texniki insident qeydində formadan və sistem tarixçəsindən gələn sahələr bir yerdə görünür;` / `noyabr ayında keyfiyyət bölməsində sənəd paketi daxilində də eyni paketə daxil edilib.`
- bench_az_004190 `70.215.81.108`: `Texniki insident qeydində müştərinin göndərdiyi məlumatlarla sistem referansları birləşdirilib;` / `Köhnə şəbəkə qeydində 2001:::1234 görunur;`

## EMAIL: 26 v4 misses, 18 brought back by deleting one other sentence

| blockers per miss | misses |
|---|---|
| 0 | 8 |
| 1 | 7 |
| 2 | 7 |
| 3+ | 4 |

### What the blocking sentences hold (benchmark plants, digits as 9)

| plant | n |
|---|---|
| `nothing planted` | 25 |
| `hard negative: user@` | 5 |
| `hard negative: 99999` | 1 |
| `hard negative: 99:99` | 1 |
| `hard negative: AZ9999` | 1 |
| `hard negative: 999` | 1 |
| `hard negative: abc` | 1 |

### Blocking sentences by shape

| sentence | n |
|---|---|
| `| Sahə | Dəyər |` | 7 |
| `|---|---|` | 5 |
| `| e_poçt | user@ |` | 2 |
| `"e_poçt": "user@",` | 2 |
| `| ipv9 | 9999:db9:9f:99::9f |` | 1 |
| `| cvv | 99999 |` | 1 |
| `| bina_nömrəsi | 999/99 |` | 1 |
| `Müştəri: fin_kodu məlumatı Z9999JR olaraq qeyd edildi.` | 1 |
| `[9999-99-99 99:99:99] INFO saat=99:99` | 1 |
| `"pasport": "Z99999999",` | 1 |
| `{` | 1 |
| `"tarix": "99.99.9999",` | 1 |
| `}` | 1 |
| `Operator: poçt_indeksi məlumatı AZ9999 olaraq qeyd edildi.` | 1 |
| `Sistem: yaş məlumatı 99 olaraq qeyd edildi.` | 1 |
| `Operator: iban məlumatı AZ9999 olaraq qeyd edildi.` | 1 |
| `Müştəri: telefon məlumatı 999 olaraq qeyd edildi.` | 1 |
| `Operator: private_key məlumatı -----BEGIN PRIVATE KEY----- BENCHFLHP9t9e9vLgoTZ9m9eb99xXAy` | 1 |
| `Operator: e_poçt məlumatı user@ olaraq qeyd edildi.` | 1 |
| `"ad": "Bəhmənyar",` | 1 |
| `"cvv": "999",` | 1 |
| `"api_key": "abc",` | 1 |
| `Operator: şəhər məlumatı Car olaraq qeyd edildi.` | 1 |

### Examples

- bench_az_000392 `bench.user1239@synthetic-mail15.invalid`: `| Sahə | Dəyər |` / `|---|---|`
- bench_az_000569 `bench.user1545@synthetic-mail15.invalid`: `| Sahə | Dəyər |` / `| e_poçt | user@ |`
- bench_az_000830 `bench.user565@synthetic-mail4.invalid`: `"e_poçt": "user@",`
- bench_az_000974 `bench.user110@synthetic-mail8.invalid`: `| Sahə | Dəyər |` / `|---|---|`
- bench_az_001017 `bench.user1090@synthetic-mail2.invalid`: `| Sahə | Dəyər |` / `| bina_nömrəsi | 389/10 |`
- bench_az_001040 `bench.user2023@synthetic-mail0.invalid`: `"e_poçt": "user@",`
- bench_az_001047 `bench.user1998@synthetic-mail9.invalid`: `Müştəri: fin_kodu məlumatı Z9406JR olaraq qeyd edildi.`
- bench_az_001250 `bench.user2211@synthetic-mail1.invalid`: `[2031-04-12 10:03:00] INFO saat=25:81`
- bench_az_001607 `bench.user1228@synthetic-mail4.invalid`: `"pasport": "Z90001227",`
- bench_az_002175 `bench.user1528@synthetic-mail15.invalid`: `| Sahə | Dəyər |` / `|---|---|`
- bench_az_002505 `bench.user1153@synthetic-mail14.invalid`: `{` / `"tarix": "19.01.2042",`
- bench_az_002748 `bench.user2948@synthetic-mail7.invalid`: `| Sahə | Dəyər |` / `|---|---|`

