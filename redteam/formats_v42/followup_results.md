# Formats follow-up probes (v4.2, product decoding M)

Separate from the frozen 200. Each group varies one factor of a confirmed failure.


## A at-disguise

| Probe | Result | Masked (M) |
|---|---|---|
| [at], nigar.huseynova@inbox.az | ok | `E-poçt: [EMAIL]` |
| (at), nigar.huseynova@inbox.az | ok | `E-poçt: [EMAIL]` |
| spaced at, nigar.huseynova@inbox.az | partly_masked | `E-poçt: [EMAIL].huseynova at inbox.[EMAIL]` |
| [at], kamal77@poct.az | partly_masked | `E-poçt: [EMAIL][at][EMAIL]` |
| (at), kamal77@poct.az | partly_masked | `E-poçt: [EMAIL]([EMAIL])[EMAIL]` |
| spaced at, kamal77@poct.az | missed | `E-poçt: kamal77 at poct.az` |
| [at], info.sabina@kamranservis.az | ok | `E-poçt: [EMAIL]` |
| (at), info.sabina@kamranservis.az | partly_masked | `E-poçt: [EMAIL](at)[EMAIL]` |
| spaced at, info.sabina@kamranservis.az | partly_masked | `E-poçt: [EMAIL].sabina at kamranservis.az` |
| [at] without a label word | ok | `Mənə [EMAIL] ünvanına yazın.` |
| [at] after 'Əlaqə üçün' | ok | `Əlaqə üçün: [EMAIL]` |

## B spoken

| Probe | Result | Masked (M) |
|---|---|---|
| short local, words | missed | `Nömrəm: sıfır əlli yeddi yüz otuz doqquz iyirmi bir altmış dörd` |
| 'telefonum' as the label | missed | `Telefonum: sıfır əlli yeddi yüz otuz doqquz iyirmi bir altmış dörd` |
| digit by digit | missed | `Nömrəm: sıfır beş sıfır yeddi üç doqquz iki bir altı dörd` |
| control: same number in digits | ok | `Nömrəm: [TELEPHONENUM]` |

## C spaced id

| Probe | Result | Masked (M) |
|---|---|---|
| AZ_VOEN spaced by character | missed | `VÖEN: 1 7 0 2 9 3 8 4 6 1` |
| AZ_VOEN control | ok | `VÖEN: [AZ_VOEN]` |
| AZ_PASSPORT_NUMBER spaced by character | missed | `Pasport: C 4 7 1 9 5 3 6 2` |
| AZ_PASSPORT_NUMBER control | ok | `Pasport: [AZ_PASSPORT_NUMBER]` |
| AZ_ID_CARD_NUMBER spaced by character | missed | `Vəsiqə: A A 7 3 6 4 5 1 9` |
| AZ_ID_CARD_NUMBER control | ok | `Vəsiqə: [AZ_ID_CARD_NUMBER]` |
| AZ_FIN spaced by character | missed | `FİN: 2 H N 6 W K 9` |
| AZ_FIN control | ok | `FİN: [AZ_FIN]` |
| FIN grouped 3-4 | ok | `FİN: [AZ_FIN]` |
| FIN grouped 2-2-3 | missed | `FİN: 5R T8 VQ2` |

## D entity

| Probe | Result | Masked (M) |
|---|---|---|
| &#64; without HTML tags | missed | `E-poçt: s.qasimova&#64;inbox.az` |
| &#64;, another address | missed | `<p>E-poçt: kamal77&#64;poct.az</p>` |
| &#64; in a mailto link | missed | `<a href=\"mailto:kamal77&#64;poct.az\">yaz</a>` |
| control: literal @ in a link | boundary | `<a href=\"[EMAIL]\">yaz</a>` |

## E table name

| Probe | Result | Masked (M) |
|---|---|---|
| Leyla row alone | missed | `Ad | Soyad | FİN\nLeyla | [SURNAME] | [AZ_FIN]` |
| Leyla in a sentence | ok | `Ərizəçi [GIVENNAME] [SURNAME] müraciət edib.` |
| Leyla as given name with another surname | missed | `Ad | Soyad\nLeyla | [SURNAME]` |
| Lalə in the same row instead | ok | `Ad | Soyad | FİN\n[GIVENNAME] | [SURNAME] | [AZ_FIN]` |
| Leyla at the start of a line, no table | ok | `[GIVENNAME] bu gün gəlməyəcək.` |

## F json plus

| Probe | Result | Masked (M) |
|---|---|---|
| original shape (name, surname, phone, fin) | partly_masked | `{\"name\": \"[GIVENNAME]\", \"surname\": \"[SURNAME]\", \"phone\": \"[TELEPHONENUM]994501234567\", \"fin\": \"[AZ_FIN]\"}` |
| without fin | ok | `{\"name\": \"[GIVENNAME]\", \"surname\": \"[SURNAME]\", \"phone\": \"[TELEPHONENUM]\"}` |
| without the names | ok | `{\"phone\": \"[TELEPHONENUM]\", \"fin\": \"[AZ_FIN]\"}` |
| another phone, same shape | ok | `{\"name\": \"[GIVENNAME]\", \"surname\": \"[SURNAME]\", \"phone\": \"[TELEPHONENUM]\", \"fin\": \"[AZ_FIN]\"}` |
| Azerbaijani keys | ok | `{\"ad\": \"[GIVENNAME]\", \"soyad\": \"[SURNAME]\", \"telefon\": \"[TELEPHONENUM]\", \"fin\": \"[AZ_FIN]\"}` |

## G display

| Probe | Result | Masked (M) |
|---|---|---|
| quoted 'Əliyev, Rauf' (another) | missed | `From: \"[SURNAME], Elnur\" <[EMAIL]>` |
| unquoted 'Əliyev Rauf' | missed | `From: [SURNAME] Rauf <[EMAIL]>` |
| 'Əliyev, Rauf' in a sentence | ok | `Sənədi [SURNAME], [GIVENNAME] imzalayıb.` |

## H codes

| Probe | Result | Masked (M) |
|---|---|---|
| spaced 5-group code | false_alarm | `Sifariş kodu: [IBAN]` |
| dashed code | false_alarm | `Sifariş kodu: [IBAN]` |
| ASCII 10-digit after 'Sifariş №' | false_alarm | `Sifariş № [AZ_VOEN] qəbul olundu.` |
| full-width 8-digit order | ok | `Sifariş № ４８２９１７３６ qəbul olundu.` |
| IP:port again, another IP | partly_masked | `client=[IPV4_ADDRESS].14:443 closed` |
