# Ablation: which other sentence blocks v4.2 (track R)

Each other sentence of the document deleted in turn; a blocker is a deletion that brings the exact span back.

## IPV6_ADDRESS: 160 v4.2 misses, 55 brought back by deleting one other sentence

| blockers per miss | misses |
|---|---|
| 0 | 105 |
| 1 | 30 |
| 2 | 9 |
| 3+ | 16 |

### What the blocking sentences hold (benchmark plants, digits as 9)

| plant | n |
|---|---|
| `nothing planted` | 102 |
| `hard negative: ABC999` | 3 |
| `hard negative: 9999` | 3 |
| `hard negative: abc` | 2 |
| `hard negative: ABCD` | 1 |
| `hard negative: H99C99999` | 1 |
| `distractor: versiya v9.9.99` | 1 |
| `hard negative: 99999` | 1 |
| `distractor: müqavilə bəndi 99.9.9` | 1 |
| `hard negative: AA999` | 1 |
| `hard negative: 999` | 1 |
| `distractor: faktura INV/9999/99999` | 1 |
| `hard negative: 99` | 1 |
| `hard negative: mail yoxdur` | 1 |
| `hard negative: 99:999` | 1 |
| `distractor: daxili istinad REF999999` | 1 |
| `hard negative: private_key=test` | 1 |
| `distractor: müqavilə bəndi 9.9.9` | 1 |
| `hard negative: 999999` | 1 |
| `distractor: sifariş ORD-99999` | 1 |
| `distractor: otaq 999` | 1 |
| `hard negative: 9999999999999999` | 1 |

### Blocking sentences by shape

| sentence | n |
|---|---|
| `Eyni qeyddə tracking kodu üçün 9999999999999999 göstərilib;` | 5 |
| `Əlavə hissədə tracking kodu məlumatı 9999999999999999 kimi saxlanılıb;` | 3 |
| `Müqavilə bəndi məlumatında 99.9.9 kodu qeyd olunub.` | 3 |
| `Şirkət profilində 9999999999 görünür;` | 2 |
| `Ərizənin ad bölməsinə ABC999 daxil edilib;` | 2 |
| `Sifariş məlumatında ORD-99999 kodu qeyd olunub;` | 2 |
| `Sənədin digər hissəsində müqavilə bəndi olaraq 99.9.9 yazılıb.` | 2 |
| `Tracking kodu məlumatında 9999999999999999 kodu qeyd olunub;` | 2 |
| `Daxili istinad məlumatında REF999999 kodu qeyd olunub;` | 2 |
| `surəti qeydiyyat bölməsinin noyabr arxivində müraciət əlavəsi ilə sənədlə birlikdə qorunub` | 1 |
| `surəti hesablaşmalar bölməsinin dekabr arxivində xidmət jurnalı ilə arxivə köçürülüb.` | 1 |
| `Kart nömrəsi sahəsində ABCD yazılıb;` | 1 |
| `profil çıxarışı avqust dövrü üçün inteqrasiya bölməsində birlikdə saxlanılıb.` | 1 |
| `Müştəri söhbətin əvvəlində fIN kodunu H99C99999 kimi yazıb;` | 1 |
| `surəti sənəd dövriyyəsi bölməsinin iyun arxivində profil çıxarışı ilə iş materiallarına əl` | 1 |
| `Formanın ad hissəsində ABC999 yazilib;` | 1 |
| `həmin məlumat çatdırılma komandasının avqust üzrə əməliyyat qeydi sənədində arxivə köçürül` | 1 |
| `Formanı mən doldurmuşam;` | 1 |
| `istifadə etdiyim məlumatları burada təkrar qeyd edirəm;` | 1 |
| `xidmət jurnalı iyul dövrü üçün abonent xidmətləri bölməsində qovluğa əlavə olunub.` | 1 |
| `Tarixçədə versiya v9.9.99 ilə əlaqəli ayrıca qeyd var.` | 1 |
| `dekabr ayında çatdırılma bölməsində sənəd paketi daxilində də arxivə köçürülüb.` | 1 |
| `Müqavilə əlavəsində əvvəlki yazışmadan götürülən məlumatlar yeni müraciətə əlavə olunub;` | 1 |
| `həmin məlumat qeydiyyat komandasının mart üzrə profil çıxarışı sənədində eyni paketə daxil` | 1 |
| `may ayında korporativ xidmətlər bölməsində sənəd paketi daxilində də sənədlə birlikdə qoru` | 1 |
| `Köhnə profildə mobil nömrə 99999 görünür;` | 1 |
| `həmin məlumat ödəniş əməliyyatları komandasının iyun üzrə yazışma nüsxəsi sənədində arxivə` | 1 |
| `E-poçt yazışmasında əvvəlki yazışmadan götürülən məlumatlar yeni müraciətə əlavə olunub;` | 1 |
| `gündəlik qeyd noyabr dövrü üçün müştəri xidmətləri bölməsində qovluğa əlavə olunub.` | 1 |
| `həmin məlumat ödəniş əməliyyatları komandasının noyabr üzrə hesab çıxarışı sənədində eyni ` | 1 |

### Examples

- bench_az_000085 `2001:db8::ebb9`: `Şirkət profilində 1417069842 görünür;`
- bench_az_000146 `fd00::f1e3:d002`: `Əlavə hissədə tracking kodu məlumatı 4795044608071331 kimi saxlanılıb;`
- bench_az_000229 `2001:db8::a392`: `Ərizənin ad bölməsinə ABC123 daxil edilib;`
- bench_az_000247 `fd00::5793:d50c`: `Sifariş məlumatında ORD-75279 kodu qeyd olunub;`
- bench_az_000466 `fd00::e8cc:4421`: `surəti qeydiyyat bölməsinin noyabr arxivində müraciət əlavəsi ilə sənədlə birlikdə qorunub.` / `surəti hesablaşmalar bölməsinin dekabr arxivində xidmət jurnalı ilə arxivə köçürülüb.`
- bench_az_000611 `2001:db8:1932:f4a4::945d`: `Formanın ad hissəsində ABC123 yazilib;` / `həmin məlumat çatdırılma komandasının avqust üzrə əməliyyat qeydi sənədində arxivə köçürülüb.`
- bench_az_000638 `2001:db8::e6c0`: `Formanı mən doldurmuşam;` / `istifadə etdiyim məlumatları burada təkrar qeyd edirəm;`
- bench_az_000669 `2001:db8::8565`: `Əlavə hissədə tracking kodu məlumatı 3874118559983810 kimi saxlanılıb;` / `dekabr ayında çatdırılma bölməsində sənəd paketi daxilində də arxivə köçürülüb.`
- bench_az_000686 `fd00::7311:3e8`: `Müqavilə əlavəsində əvvəlki yazışmadan götürülən məlumatlar yeni müraciətə əlavə olunub;` / `həmin məlumat qeydiyyat komandasının mart üzrə profil çıxarışı sənədində eyni paketə daxil edilib.`
- bench_az_000969 `fd00::8f59:9459`: `Köhnə profildə mobil nömrə 05012 görünür;`
- bench_az_000983 `fd00::6f35:ab8d`: `həmin məlumat ödəniş əməliyyatları komandasının iyun üzrə yazışma nüsxəsi sənədində arxivə köçürülüb.` / `Eyni qeyddə tracking kodu üçün 4298465498777142 göstərilib;`
- bench_az_001098 `2001:db8:6122:c2a4::f2e`: `E-poçt yazışmasında əvvəlki yazışmadan götürülən məlumatlar yeni müraciətə əlavə olunub;` / `gündəlik qeyd noyabr dövrü üçün müştəri xidmətləri bölməsində qovluğa əlavə olunub.`

