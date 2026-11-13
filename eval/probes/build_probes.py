"""Build the P3-3 probe sets: eval/probes/<family>.jsonl (committed).

    python eval/probes/build_probes.py [--seed 33] [--validators <dir containing piigen/>]

Every sentence, name form and value maker here was written for the probes
(rule A2.5 / RC7): nothing from frames_az.py, values.py, negatives.py,
scripts/piigen/targeted/, suffix.py, name_transliterators.py, the training
corpus or the private shadow set. Inflected and transliterated names are
written out by hand as literal strings. Validators are only used to CHECK
the result (--validators), never to make values.

Record: corpus schema + family, pair, role; `hard_negatives` for planted
look-alikes (D-2 dummies and names-as-org tagged policy); `controls` for
ordinary-word / non-PII uses; `control: true` for a whole ordinary-word
record; entity fields `case` (suffixed_entities) and `variant`
(name_transliteration_variants).
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import string
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
UP, DIG = string.ascii_uppercase, string.digits
ALNUM = string.ascii_letters + DIG
PH = re.compile(r"\{(v2|v|d|c)\}")


# ---------------------------------------------------------------------------
# Values (own makers) and look-alikes
# ---------------------------------------------------------------------------

def _rs(r, a, n):
    return "".join(r.choice(a) for _ in range(n))


def _luhn(body: str) -> str:
    s = 0
    for i, ch in enumerate(reversed(body)):
        d = int(ch) * (2 if i % 2 == 0 else 1)
        s += d - 9 if d > 9 else d
    return str((10 - s % 10) % 10)


def card(r, spaced=None):
    pre = r.choice(["4", "4169", "5239", "53", "2202"])
    body = pre + _rs(r, DIG, 15 - len(pre))
    n = body + _luhn(body)
    if spaced is None:
        spaced = r.random() < 0.5
    return " ".join(n[i:i + 4] for i in range(0, 16, 4)) if spaced else n


def bad_card(r):
    while True:
        body = r.choice(["4", "4169", "5239"]) + _rs(r, DIG, 15 - 4)
        body = body[:15]
        v = body + str((int(_luhn(body)) + r.randint(1, 9)) % 10)
        if v[-1] != _luhn(body):
            return v


def iban(r, spaced=None):
    bban = _rs(r, UP, 4) + _rs(r, UP + DIG, 20)
    n = int("".join(str(int(c, 36)) for c in bban + "AZ00"))
    v = f"AZ{98 - n % 97:02d}{bban}"
    if spaced is None:
        spaced = r.random() < 0.4
    return " ".join(v[i:i + 4] for i in range(0, 28, 4)) if spaced else v


def iccid(r):
    b = "89994" + _rs(r, DIG, 13)
    return b + _luhn(b)


def ipv4(r):
    return f"{r.choice([46, 77, 85, 94, 178, 185, 212])}.{r.randint(0, 255)}.{r.randint(0, 255)}.{r.randint(1, 254)}"


def ipv6(r, compressed=True):
    g = [r.choice(["2a03", "2a0d", "2001", "2c0f"])] + [f"{r.randint(0, 0xffff):x}" for _ in range(7)]
    if compressed:
        k = r.randint(2, 5)
        i = r.randint(1, 7 - k)
        return ":".join(g[:i]) + "::" + ":".join(g[i + k:])
    return ":".join(g)


def mac(r):
    sep = r.choice([":", "-"])
    return sep.join(_rs(r, "0123456789ABCDEF", 2) for _ in range(6))


def email(r):
    u = r.choice(["leyla.n", "kamran88", "s.aliyeva", "orxan.q", "nigar_h", "tural.babayev", "aynur.m", "vusal21"])
    return f"{u}@{r.choice(['mektub-xett.az', 'ofisnet.az', 'qovsaq.com', 'northdesk.io'])}"


def access_token(r):
    if r.random() < 0.7:
        return r.choice(["at_", "bearer_", "tok_"]) + _rs(r, ALNUM, r.randint(26, 40))
    return "eyJhbGciOiJSUzI1NiJ9." + _rs(r, ALNUM + "-_", 48) + "." + _rs(r, ALNUM + "-_", 43)


def api_key(r):
    k = r.random()
    if k < 0.5:
        return r.choice(["key_", "api_"]) + _rs(r, ALNUM, r.randint(26, 36))
    if k < 0.75:
        return "sk-live-" + _rs(r, ALNUM, 30)
    return "ghp_" + _rs(r, ALNUM, 36)


def pem(r):
    body = "\n".join(_rs(r, string.ascii_letters + DIG + "+/", 64) for _ in range(r.randint(3, 5)))
    kind = r.choice(["RSA PRIVATE KEY", "PRIVATE KEY", "EC PRIVATE KEY"])
    return f"-----BEGIN {kind}-----\n{body}\n{_rs(r, ALNUM, 20)}==\n-----END {kind}-----"


def phone(r, spaced=True):
    op = r.choice(["50", "51", "55", "70", "77", "99"])
    a, b, c = r.randint(200, 989), r.randint(10, 99), r.randint(10, 99)
    return r.choice([f"+994 {op} {a} {b} {c}", f"0{op} {a} {b} {c}"]) if spaced else f"+994{op}{a}{b}{c}"


def fin(r):
    a = "".join(c for c in UP if c not in "IO") + DIG
    while True:
        v = _rs(r, a, 7)
        if any(c.isdigit() for c in v) and any(c.isalpha() for c in v):
            return v


def id_card(r):
    return r.choice(["AA", "AB"]) + _rs(r, DIG, 7)


def licence(r):
    return r.choice(["AA", "AB"]) + _rs(r, DIG, 6)


def passport(r):
    return r.choice(["C", "P"]) + _rs(r, DIG, 8)


def voen(r):
    return _rs(r, "123456789", 1) + _rs(r, DIG, 9)


def zipc(r):
    return f"AZ{r.randint(1000, 6999)}"


def date(r):
    d, m, y = r.randint(1, 28), r.randint(1, 12), r.randint(1960, 2004)
    return r.choice([f"{d:02d}.{m:02d}.{y}", f"{y}-{m:02d}-{d:02d}"])


def time_(r):
    return f"{r.randint(0, 23):02d}:{r.randint(0, 59):02d}"


def age(r):
    return str(r.randint(19, 79))


def cvv(r):
    return _rs(r, DIG, 3)


VALUE = {"PAYMENT_CARD_NUMBER": card, "IBAN": iban, "ICCID": iccid, "IPV4_ADDRESS": ipv4,
         "IPV6_ADDRESS": ipv6, "MAC_ADDRESS": mac, "EMAIL": email, "ACCESS_TOKEN": access_token,
         "API_KEY": api_key, "PRIVATE_KEY": pem, "TELEPHONENUM": phone, "AZ_FIN": fin,
         "AZ_ID_CARD_NUMBER": id_card, "AZ_DRIVER_LICENSE_NUMBER": licence,
         "AZ_PASSPORT_NUMBER": passport, "AZ_VOEN": voen, "ZIPCODE": zipc, "DATE": date,
         "TIME": time_, "AGE": age, "CARD_SECURITY_CODE": cvv}

# look-alikes that are NOT the label (shape-invalid); D-2 dummies are policy
LOOKALIKE = {
    "CARD_SECURITY_CODE": lambda r: r.choice([_rs(r, "123456789", 1) + _rs(r, DIG, 4), f"{r.randint(10, 99)}-{r.randint(1, 9)}", str(r.randint(10, 99))]),
    "TIME": lambda r: r.choice([f"{r.randint(24, 28)}:{r.randint(10, 59)}", f"{r.randint(10, 22)}:{r.randint(61, 97)}"]),
    "AGE": lambda r: r.choice([str(r.randint(160, 880)), f"-{r.randint(2, 9)}"]),
    "DATE": lambda r: r.choice([f"30.02.{r.randint(2021, 2027)}", f"{r.randint(13, 28)}.{r.randint(13, 18)}.{r.randint(2021, 2027)}"]),
    "ZIPCODE": lambda r: r.choice([f"AZ{r.randint(10000, 99999)}", f"AZ{r.randint(1, 99)}"]),
    "AZ_FIN": lambda r: r.choice([_rs(r, DIG, 5), "O" + _rs(r, "ABCDEFGH123456789", 6), _rs(r, UP, 2) + _rs(r, DIG, 2) + "-" + _rs(r, UP, 2)]),
    "AZ_VOEN": lambda r: _rs(r, "123456789", 1) + _rs(r, DIG, 7),
    "AZ_PASSPORT_NUMBER": lambda r: _rs(r, UP, 2) + _rs(r, DIG, 5),
    "AZ_ID_CARD_NUMBER": lambda r: r.choice(["AA", "AB"]) + _rs(r, DIG, 4),
    "IPV4_ADDRESS": lambda r: r.choice([f"{r.randint(256, 999)}.{r.randint(0, 9)}.{r.randint(0, 9)}.{r.randint(1, 9)}",
                                        f"{r.randint(256, 999)}.{r.randint(10, 99)}.{r.randint(0, 9)}.{r.randint(1, 9)}"]),
    "IPV6_ADDRESS": lambda r: f"{_rs(r, '0123456789abcdef', 4)}:{_rs(r, '0123456789abcdef', 3)}:::{r.randint(1, 9)}",
    "MAC_ADDRESS": lambda r: ":".join(_rs(r, "0123456789ABCDEF", 2) for _ in range(3)),
    "PAYMENT_CARD_NUMBER": bad_card,
    "ICCID": lambda r: "89" + _rs(r, DIG, 5),
    "IBAN": lambda r: f"AZ{r.randint(10, 99)}{_rs(r, UP, 4)}",
    "EMAIL": lambda r: r.choice(["leyla.n.ofisnet.az", "kamran88@@qovsaq.com", "orxan.q@localhost"]),
    "PRIVATE_KEY": lambda r: "-----BEGIN PUBLIC KEY-----\n" + _rs(r, ALNUM, 64) + "\n-----END PUBLIC KEY-----",
    "TELEPHONENUM": lambda r: f"{r.randint(10, 99)}-{r.randint(10, 99)}",
    "ACCESS_TOKEN": lambda r: "tok_" + _rs(r, ALNUM, 6),
    "API_KEY": lambda r: "key-" + str(r.randint(10, 99)),
}
# Dense archive-style register (the benchmark's RC4 failure pattern: values deep
# inside long bureaucratic text full of month words and non-PII codes). Own wording.
MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avqust", "sentyabr",
          "oktyabr", "noyabr", "dekabr"]
ARCHIVE = [
    "Sənədin nüsxəsi logistika şöbəsinin {m} qovluğunda hesabat çapı ilə birlikdə saxlanılır",
    "Daxili qeyd {k} olaraq {m} dövrü üçün maliyyə bölməsinin reyestrinə salınıb",
    "Əlavə vərəqdə istinad nömrəsi {k} göstərilib, {m} ayının yoxlama siyahısına keçirilib",
    "Paketin ikinci hissəsi {m} yığımı ilə birlikdə keyfiyyət nəzarəti bölməsinə ötürülüb",
    "Müqavilə bəndi {k} üzrə {m} ayında aparılan düzəlişlər ayrıca jurnalda yazılıb",
    "Arayışın surəti {m} toplusunda kadrlar şöbəsinin arxiv qutusuna qoyulub",
    "Hesabın icmalı {k} nömrəsi altında {m} rübü üçün mühasibat cədvəlinə köçürülüb",
    "Yoxlama aktının qaralaması {m} sessiyasında komissiyanın gündəliyinə salınıb",
    "Paylama vərəqi {k} işarəsi ilə {m} göndərişləri arasında saxlanılıb",
    "Xidməti yazışmanın tam mətni {m} dövrünün elektron qovluğunda qalıb",
]


def archive_code(r):
    return r.choice([f"SFR-{r.randint(1000, 9999)}", f"QM/2026/{r.randint(10000, 99999)}",
                     f"İST{r.randint(100000, 999999)}", f"KMP-{r.randint(100, 999)}",
                     f"{r.randint(2, 9)}.{r.randint(1, 9)}.{r.randint(1, 9)}", f"PL-{r.randint(10, 99)}/{r.randint(1, 9)}"])


def archive_text(r, n):
    return "; ".join(r.choice(ARCHIVE).format(m=r.choice(MONTHS), k=archive_code(r)) for _ in range(n))


def archive_wrap(r, mid):
    """mid (a clause with {v}/{d}/{c}) placed after 3-5 archive clauses and before 1-2."""
    return archive_text(r, r.randint(3, 5)) + "; " + mid + "; " + archive_text(r, r.randint(1, 2)) + "."


def format_email(r):
    """Format-probe emails in the benchmark's missed shape: digits in the local
    part, a hyphen-and-digit domain, an unusual top-level domain."""
    u = r.choice(["nurlan.qasimov", "aytac.rehimova", "elvin.ceferov", "sevda.mirzeyeva", "kamil.orucov", "lale.hesenova"])
    return f"{u}{r.randint(2, 98)}@{r.choice(['poct-xidmet', 'mesaj-merkez', 'bulud-poct', 'ofis-xett'])}{r.randint(1, 9)}" \
           f".{r.choice(['invalid', 'example', 'invalid', 'example'])}"


def long_pem(r, one_line=False):
    body = [_rs(r, string.ascii_letters + DIG + "+/", 64) for _ in range(r.randint(20, 28))]
    kind = r.choice(["RSA PRIVATE KEY", "PRIVATE KEY"])
    v = f"-----BEGIN {kind}-----\n" + "\n".join(body) + f"\n{_rs(r, ALNUM, 30)}==\n-----END {kind}-----"
    return v.replace("\n", " ") if one_line else v


D2 = {"CARD_SECURITY_CODE": ["1234", "12345", "0000"], "PAYMENT_CARD_NUMBER": ["4242424242424242", "4111111111111111"],
      "AZ_PASSPORT_NUMBER": ["P12345678"], "AZ_FIN": ["A12B34"]}

# ---------------------------------------------------------------------------
# Names, written by hand. Inflected forms are literal (D-9: span = value + suffix).
# ---------------------------------------------------------------------------
GIVEN = ["Rəşad", "Aysel", "Tural", "Nigar", "Kamran", "Səbinə", "Orxan", "Lalə", "Vüqar", "Günay",
         "Elçin", "Nərmin", "Fuad", "Aynur", "Ramil", "Könül", "Səməd", "Türkan", "Ceyhun", "Zəhra"]
SURNAME = ["Hüseynov", "Əliyeva", "Babayev", "Quliyeva", "Səfərov", "Rzayeva", "Orucov", "Kərimli",
           "Abbasova", "Musayev", "Nəsirli", "Cəfərova"]
CITY = ["Gəncə", "Şəki", "Lənkəran", "Quba", "Şamaxı", "Mingəçevir", "Naxçıvan", "Zaqatala", "Qəbələ", "Bakı"]
STREET = ["Nizami küçəsi", "Füzuli küçəsi", "Azadlıq prospekti", "Səməd Vurğun küçəsi", "Xətai prospekti",
          "Natəvan küçəsi", "Bülbül prospekti", "Rəsul Rza küçəsi"]

# (case, label, bare, inflected) -- every form written out by hand
SUFFIXED = [
    ("gen", "GIVENNAME", "Rəşad", "Rəşadın"), ("gen", "GIVENNAME", "Lalə", "Lalənin"), ("gen", "SURNAME", "Hüseynov", "Hüseynovun"),
    ("gen", "CITY", "Gəncə", "Gəncənin"), ("gen", "CITY", "Şəki", "Şəkinin"), ("gen", "STREET", "Nizami küçəsi", "Nizami küçəsinin"),
    ("dat", "GIVENNAME", "Aysel", "Ayselə"), ("dat", "GIVENNAME", "Səməd", "Səmədə"), ("dat", "SURNAME", "Əliyeva", "Əliyevaya"),
    ("dat", "CITY", "Quba", "Qubaya"), ("dat", "CITY", "Lənkəran", "Lənkərana"), ("dat", "STREET", "Azadlıq prospekti", "Azadlıq prospektinə"),
    ("acc_vowel", "CITY", "Bakı", "Bakını"), ("acc_vowel", "CITY", "Gəncə", "Gəncəni"), ("acc_vowel", "GIVENNAME", "Lalə", "Laləni"),
    ("acc_vowel", "SURNAME", "Quliyeva", "Quliyevanı"), ("acc_vowel", "CITY", "Şəki", "Şəkini"), ("acc_vowel", "STREET", "Füzuli küçəsi", "Füzuli küçəsini"),
    ("acc_consonant", "GIVENNAME", "Əsgər", "Əsgəri"), ("acc_consonant", "GIVENNAME", "Kamran", "Kamranı"), ("acc_consonant", "GIVENNAME", "Orxan", "Orxanı"),
    ("acc_consonant", "SURNAME", "Babayev", "Babayevi"), ("acc_consonant", "CITY", "Lənkəran", "Lənkəranı"), ("acc_consonant", "GIVENNAME", "Tural", "Turalı"),
    ("loc", "CITY", "Şamaxı", "Şamaxıda"), ("loc", "CITY", "Zaqatala", "Zaqatalada"), ("loc", "CITY", "Mingəçevir", "Mingəçevirdə"),
    ("loc", "STREET", "Natəvan küçəsi", "Natəvan küçəsində"), ("loc", "STREET", "Xətai prospekti", "Xətai prospektində"), ("loc", "CITY", "Naxçıvan", "Naxçıvanda"),
    ("abl", "GIVENNAME", "Nigar", "Nigardan"), ("abl", "GIVENNAME", "Elçin", "Elçindən"), ("abl", "SURNAME", "Səfərov", "Səfərovdan"),
    ("abl", "CITY", "Qəbələ", "Qəbələdən"), ("abl", "STREET", "Nizami küçəsi", "Nizami küçəsindən"), ("abl", "CITY", "Bakı", "Bakıdan"),
    ("ins", "GIVENNAME", "Əsgər", "Əsgərlə"), ("ins", "GIVENNAME", "Nərmin", "Nərminlə"), ("ins", "CITY", "Bakı", "Bakıyla"),
    ("ins", "GIVENNAME", "Günay", "Günayla"), ("ins", "SURNAME", "Musayev", "Musayevlə"), ("ins", "GIVENNAME", "Səbinə", "Səbinəylə"),
    ("rel", "CITY", "Bakı", "Bakıdakı"), ("rel", "CITY", "Şəki", "Şəkidəki"), ("rel", "CITY", "Quba", "Qubadakı"),
    ("rel", "STREET", "Bülbül prospekti", "Bülbül prospektindəki"), ("rel", "CITY", "Gəncə", "Gəncədəki"), ("rel", "STREET", "Rəsul Rza küçəsi", "Rəsul Rza küçəsindəki"),
    ("pl", "SURNAME", "Məmmədov", "Məmmədovlar"), ("pl", "SURNAME", "Hüseynov", "Hüseynovlar"), ("pl", "SURNAME", "Orucov", "Orucovlar"),
    ("pl", "SURNAME", "Kərimli", "Kərimlilər"), ("pl", "SURNAME", "Babayev", "Babayevlər"), ("pl", "SURNAME", "Nəsirli", "Nəsirlilər"),
    ("pl_case", "SURNAME", "Məmmədov", "Məmmədovların"), ("pl_case", "SURNAME", "Hüseynov", "Hüseynovlara"), ("pl_case", "SURNAME", "Orucov", "Orucovlardan"),
    ("pl_case", "SURNAME", "Kərimli", "Kərimlilərdə"), ("pl_case", "SURNAME", "Babayev", "Babayevləri"), ("pl_case", "SURNAME", "Musayev", "Musayevlərin"),
    ("cop", "GIVENNAME", "Fuad", "Fuaddır"), ("cop", "GIVENNAME", "Aynur", "Aynurdur"), ("cop", "CITY", "Bakı", "Bakıdır"),
    ("cop", "GIVENNAME", "Könül", "Könüldür"), ("cop", "SURNAME", "Rzayeva", "Rzayevadır"), ("cop", "CITY", "Şəki", "Şəkidir"),
    ("apostrophe", "GIVENNAME", "Əsgər", "Əsgər'in"), ("apostrophe", "GIVENNAME", "Ramil", "Ramil'ə"), ("apostrophe", "CITY", "Bakı", "Bakı'da"),
    ("apostrophe", "SURNAME", "Hüseynov", "Hüseynov'un"), ("apostrophe", "CITY", "Gəncə", "Gəncə'dən"), ("apostrophe", "GIVENNAME", "Türkan", "Türkan'ı"),
    ("ascii_folded", "CITY", "Bakı", "Bakida"), ("ascii_folded", "GIVENNAME", "Əsgər", "Esgerden"), ("ascii_folded", "CITY", "Gəncə", "Gencede"),
    ("ascii_folded", "CITY", "Şəki", "Sekiden"), ("ascii_folded", "GIVENNAME", "Səbinə", "Sebineye"), ("ascii_folded", "SURNAME", "Hüseynov", "Huseynovun"),
]
# one carrier per case (+ label family): {v} is the inflected form
SUFFIX_FRAMES = {
    "gen": ["{v} sifarişi bu səhər yola salındı.", "Bu gün {v} növbəsidir.", "{v} adı siyahıda yoxdur."],
    "dat": ["Dünən {v} zəng vurdum.", "Bağlamanı {v} göndərmişik.", "Bu məktubu {v} ünvanlayın."],
    "acc_vowel": ["Keçən həftə {v} gördüm.", "Hamı {v} tərifləyir.", "Biz {v} çox sevirik."],
    "acc_consonant": ["Keçən həftə {v} gördüm.", "Rəhbər {v} yanına çağırdı.", "Müəllim {v} tərifləyib."],
    "loc": ["Hazırda {v} yaşayıram.", "Yeni filial {v} açılıb.", "Bu il yay tətilini {v} keçirdik."],
    "abl": ["Səhər {v} xəbər gəldi.", "Bu sənədi {v} almışıq.", "Avtobus {v} gecikdi."],
    "ins": ["Axşam {v} görüşdük.", "Layihəni {v} birlikdə bitirdik.", "Telefonda {v} danışdım."],
    "rel": ["{v} ofisimiz bağlıdır.", "{v} anbar yenidən açıldı.", "{v} yeni mağaza çox böyükdür."],
    "pl": ["{v} bu bayramı bizimlə keçirəcək.", "Qonşumuz {v} köçüb.", "Toyda {v} də iştirak etdi."],
    "pl_case": ["Bu ev {v} aiddir.", "Dəvətnamə {v} göndərildi.", "Hədiyyə {v} gəldi."],
    "cop": ["Növbəti məruzəçi {v}.", "Bu layihənin rəhbəri {v}.", "Bizim komanda kapitanı {v}."],
    "apostrophe": ["Məktub {v} göndərildi.", "Sənəd {v} çatıb.", "Bu gün {v} görüş var."],
    "ascii_folded": ["Sabah {v} cavab gozleyirik.", "Biz {v} xeber aldiq.", "Mektub {v} gonderildi."],
}

# Names that are also ordinary words (written for the probes), with a name use
# and an ordinary-word use in matching structures. {x} marks the word.
HOMOGRAPHS = [
    ("Dəniz", "Dəniz bu gün işə gec gəldi.", "Dəniz bu gün çox dalğalı idi."),
    ("Bahar", "Bahar xanım sənədləri gətirdi.", "Bahar gəldi, ağaclar çiçək açdı."),
    ("Ümid", "Ümid sabah imtahan verəcək.", "Ümid hələ də ürəyimizdədir."),
    ("Aydın", "Aydın mənə dünən zəng etdi.", "Aydın səma altında gəzdik."),
    ("Fidan", "Fidan iclasda çıxış etdi.", "Fidan bağda tez böyüdü."),
    ("Lalə", "Lalə müəllimə ilə danışdı.", "Lalə çəmənlikdə açılıb."),
    ("Ulduz", "Ulduz bu axşam gələcək.", "Ulduz səmada parlayırdı."),
    ("Günəş", "Günəş xanım məktubu imzaladı.", "Günəş buludların arxasından çıxdı."),
    ("Səma", "Səma qardaşına kömək etdi.", "Səma bu gün tamamilə mavidir."),
    ("Polad", "Polad iş yerində qalıb.", "Polad bu körpünün əsas materialıdır."),
    ("Qaya", "Qaya məktəbə yeni başlayıb.", "Qaya yolun ortasına düşmüşdü."),
    ("Araz", "Araz bu həftə məzuniyyətdədir.", "Araz yazda daşır."),
    ("Zəfər", "Zəfər komandanı təbrik etdi.", "Zəfər hamını sevindirdi."),
    ("Sevinc", "Sevinc yeni işə başladı.", "Sevinc gözlərindən oxunurdu."),
    ("Arzu", "Arzu xanım hesabatı göndərdi.", "Arzu insanı irəli aparır."),
    ("Etibar", "Etibar müqaviləni oxudu.", "Etibar dostluğun əsasıdır."),
    ("Cəsur", "Cəsur yarışda birinci oldu.", "Cəsur addım atmaq lazımdır."),
    ("Nərgiz", "Nərgiz kitabxanaya getdi.", "Nərgiz vazada solmuşdu."),
    ("Şəfəq", "Şəfəq səhər tezdən gəldi.", "Şəfəq üfüqdə qızardı."),
    ("Bulud", "Bulud bizə qonaq gəldi.", "Bulud dağların üstünü örtdü."),
    ("Yağış", "Yağış adlı qız sinifdə ən balacadır.", "Yağış səhərdən dayanmır."),
    ("Çiçək", "Çiçək nənəsinə zəng etdi.", "Çiçək pəncərənin önündə açıb."),
    ("Mələk", "Mələk dərsə hazırlaşır.", "Mələk nağıllarda tez-tez görünür."),
    ("Şahin", "Şahin maşını təmirə verdi.", "Şahin qayanın üstünə qondu."),
    ("Toğrul", "Toğrul layihəyə qoşuldu.", "Toğrul quşu əfsanələrdə yaşayır."),
    ("Ilham", "Ilham hesabatı yoxladı.", "Ilham gecə yarısı gəldi."),
    ("Nur", "Nur bu gün ad gününü qeyd edir.", "Nur pəncərədən otağa doldu."),
    ("Gülüş", "Gülüş müsabiqədə qalib gəldi.", "Gülüş otağı bürüdü."),
    ("Dilək", "Dilək sənədləri təhvil verdi.", "Dilək tutdum və şamı söndürdüm."),
    ("Ürfan", "Ürfan konfransda çıxış etdi.", "Ürfan dərin bilik deməkdir."),
    ("Fəxri", "Fəxri qonaqları qarşıladı.", "Fəxri fərman ona təqdim edildi."),
    ("Mərd", "Mərd adlı oğlan bizim qonşudur.", "Mərd insan sözünün üstündə durur."),
]

# One underlying name, several hand-written spellings (no transliteration code).
TRANSLIT = [
    ("SURNAME", ["Məmmədov", "Mammadov", "Mamedov", "Маммадов", "Мамедов"]),
    ("SURNAME", ["Hüseynova", "Huseynova", "Guseynova", "Гусейнова", "Hüseynowa"]),
    ("SURNAME", ["Əliyev", "Aliyev", "Aliev", "Алиев", "Əliev"]),
    ("GIVENNAME", ["Şəhriyar", "Shahriyar", "Sahriyar", "Шахрияр", "Şehriyar"]),
    ("GIVENNAME", ["Gülnarə", "Gulnara", "Gülnara", "Гюльнара", "Gulnare"]),
    ("GIVENNAME", ["Xəyyam", "Khayyam", "Xayyam", "Хаййам", "Hayyam"]),
    ("CITY", ["Gəncə", "Ganja", "Gence", "Гянджа", "Ganca"]),
    ("CITY", ["Şəki", "Shaki", "Seki", "Шеки", "Şeki"]),
]
VARIANT_NAMES = ["az_latin", "en_latin", "ascii_or_ru_latin", "cyrillic", "tr_or_other"]
TRANSLIT_FRAMES = {"SURNAME": ["İmza: {v}", "{v} sənədi göndərdi."],
                   "GIVENNAME": ["İmza: {v}", "{v} sənədi göndərdi."],
                   "CITY": ["Ünvan: {v}", "{v} filialına zəng edin."]}


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render(template: str, v=None, v2=None, d=None, c=None):
    """-> (text, entities, hard_negatives, controls). v/v2 = (value, label[, extra]);
    d = (value, resembles, kind, policy); c = (text, resembles, kind)."""
    text, ents, hns, ctl, pos = "", [], [], [], 0
    for m in PH.finditer(template):
        text += template[pos:m.start()]
        k = m.group(1)
        s = len(text)
        if k in ("v", "v2"):
            val = v if k == "v" else v2
            text += val[0]
            ents.append({"start": s, "end": len(text), "label": val[1], **(val[2] if len(val) > 2 else {})})
        elif k == "d":
            text += d[0]
            hns.append({"start": s, "end": len(text), "resembles": d[1], "kind": d[2], "policy": d[3]})
        else:
            text += c[0]
            ctl.append({"start": s, "end": len(text), "resembles": c[1], "kind": c[2]})
        pos = m.end()
    text += template[pos:]
    return text, ents, hns, ctl


def assemble(parts):
    """Plain strings and ("g"|"h", value, label) tuples -> (text, gold, hard negatives, [])."""
    text, ents, hns = "", [], []
    for part in parts:
        if isinstance(part, str):
            text += part
            continue
        kind, value, label = part
        s = len(text)
        text += value
        if kind == "g":
            ents.append({"start": s, "end": len(text), "label": label})
        else:
            hns.append({"start": s, "end": len(text), "resembles": label, "kind": "invalid_shape", "policy": False})
    return text, ents, hns, []


class Builder:
    def __init__(self, seed: int, forbidden: set):
        self.r = random.Random(seed)
        self.forbidden = forbidden
        self.out: dict[str, list] = {}

    def val(self, label, **kw):
        for _ in range(50):
            v = VALUE[label](self.r, **kw)
            if v not in self.forbidden:
                return v
        raise RuntimeError(label)

    def look(self, label, policy_share=0.15):
        if label in D2 and self.r.random() < policy_share:
            return self.r.choice(D2[label]), "d2_dummy", True
        for _ in range(50):
            v = LOOKALIKE[label](self.r)
            if v not in self.forbidden:
                return v, "invalid_shape", False
        raise RuntimeError(label)

    def add(self, family, pair, role, rendered, **extra):
        text, ents, hns, ctl = rendered
        rows = self.out.setdefault(family, [])
        rec = {"id": f"{family}_{len(rows) + 1:03d}", "text": text, "lang": "az", "family": family,
               "pair": pair, "role": role, "entities": ents}
        if hns:
            rec["hard_negatives"] = hns
        if ctl:
            rec["controls"] = ctl
        rec.update(extra)
        rows.append(rec)

    def pairs_archive(self, family, items, n=12):
        """items: (clause with {v}, label). A pair shares one archive document;
        only the value differs (gold vs look-alike)."""
        for i in range(n):
            mid, lab = items[i % len(items)]
            doc = archive_wrap(self.r, mid)
            self.add(family, i, "valid", render(doc, v=(self.val(lab), lab)))
            dv, kind, pol = self.look(lab)
            self.add(family, i, "invalid", render(doc.replace("{v}", "{d}"), d=(dv, lab, kind, pol)))

    def pairs(self, family, label, frames, n=12, resembles=None):
        """valid/invalid pairs in the same template: gold value vs look-alike."""
        for i in range(n):
            t = frames[i % len(frames)]
            self.add(family, i, "valid", render(t, v=(self.val(label), label)))
            dv, kind, pol = self.look(resembles or label)
            self.add(family, i, "invalid", render(t.replace("{v}", "{d}"), d=(dv, resembles or label, kind, pol)))


def build(b: Builder):
    r = b.r
    # --- confusion pairs ------------------------------------------------------
    tv = ["Sorğuya bu dəyər əlavə olundu: {v}", "Konfiqurasiyada {v} saxlanılır.", "Qoşulma üçün {v} istifadə edildi.",
          "Mühit faylında belə yazılıb: {v}", "Avtorizasiya başlığında {v} göründü.", "Skript {v} ilə işləyir."]
    for i in range(12):
        t = tv[i % len(tv)]
        b.add("token_vs_key", i, "token", render(t, v=(b.val("ACCESS_TOKEN"), "ACCESS_TOKEN")))
        b.add("token_vs_key", i, "key", render(t, v=(b.val("API_KEY"), "API_KEY")))
    nv = ["Şəbəkə jurnalında {v} qeydə alınıb.", "Cihaz {v} ilə tanındı.", "Bu ünvan ağ siyahıdadır: {v}",
          "Qoşulmanın mənbəyi {v} idi.", "Monitorinq {v} üzrə xəbərdarlıq verdi.", "Konfiqurasiya sətri: {v}"]
    for i in range(12):
        t = nv[i % len(nv)]
        b.add("ipv6_vs_mac", i, "ipv6", render(t, v=(b.val("IPV6_ADDRESS"), "IPV6_ADDRESS")))
        b.add("ipv6_vs_mac", i, "mac", render(t, v=(b.val("MAC_ADDRESS"), "MAC_ADDRESS")))
    lv = ["Təqdim olunan sənədin nömrəsi {v}.", "Yoxlamada {v} nömrəli vəsiqə göstərildi.", "Sürücü vəsiqəsini də gətirdi: {v}.",
          "Şəxsiyyət vəsiqəsi {v} olaraq yazılıb.", "Sənəd: {v}, etibarlıdır.", "Qeydiyyat {v} üzrə aparıldı."]
    for i in range(12):
        t = lv[i % len(lv)]
        b.add("licence_vs_id", i, "licence", render(t, v=(b.val("AZ_DRIVER_LICENSE_NUMBER"), "AZ_DRIVER_LICENSE_NUMBER")))
        b.add("licence_vs_id", i, "id_card", render(t, v=(b.val("AZ_ID_CARD_NUMBER"), "AZ_ID_CARD_NUMBER")))
    # --- one decoy family per target ---------------------------------------------
    b.pairs("decoy_cvv", "CARD_SECURITY_CODE", ["Kartın CVV kodu: {v}", "Ödəniş formasına CVV {v} yazıldı.", "CVC sahəsində {v} görünür."])
    b.pairs("decoy_time", "TIME", ["Görüş vaxtı: {v}", "Qatar saat {v} radələrində çatır.", "Cədvəldə vaxt {v} göstərilib."])
    b.pairs("decoy_age", "AGE", ["Yaşı: {v}", "Anketdə yaş {v} qeyd olunub.", "Pasiyentin yaşı {v} kimi yazılıb."])
    b.pairs("decoy_date", "DATE", ["Doğum tarixi: {v}", "Sənəd {v} tarixində imzalanıb.", "Tarix sahəsində {v} var."])
    b.pairs("decoy_zip", "ZIPCODE", ["Poçt indeksi: {v}", "Göndəriş {v} indeksinə gedir.", "İndeks sahəsində {v} yazılıb."])
    b.pairs("decoy_fin", "AZ_FIN", ["FİN kodu: {v}", "Ərizədə FİN {v} göstərilib.", "Bazada {v} FİN-i axtarıldı."])
    for i in range(12):
        lab = ["AZ_VOEN", "AZ_PASSPORT_NUMBER", "AZ_ID_CARD_NUMBER"][i % 3]
        word = {"AZ_VOEN": "VÖEN", "AZ_PASSPORT_NUMBER": "pasport nömrəsi", "AZ_ID_CARD_NUMBER": "vəsiqə nömrəsi"}[lab]
        t = f"Müraciətdə {word} {{v}} göstərilib."
        b.add("decoy_voen_passport_id", i, "valid", render(t, v=(b.val(lab), lab)))
        dv, k, p = b.look(lab)
        b.add("decoy_voen_passport_id", i, "invalid", render(t.replace("{v}", "{d}"), d=(dv, lab, k, p)))
    b.pairs("decoy_ipv4", "IPV4_ADDRESS", ["Server ünvanı {v} kimi yazılıb.", "Mənbə IP {v} olaraq qeyd edilib.",
                                           "Logda IPv4 {v} görünür.", "Şəbəkə tarixçəsində {v} ünvanı qalıb."])
    for i in range(12):
        lab = ["IPV6_ADDRESS", "MAC_ADDRESS"][i % 2]
        t = ["Şəbəkə ünvanı: {v}", "Cihazın fiziki ünvanı {v}."][i % 2]
        b.add("decoy_ipv6_mac", i, "valid", render(t, v=(b.val(lab), lab)))
        dv, k, p = b.look(lab)
        b.add("decoy_ipv6_mac", i, "invalid", render(t.replace("{v}", "{d}"), d=(dv, lab, k, p)))
    for i in range(12):
        lab = ["PAYMENT_CARD_NUMBER", "ICCID", "IBAN"][i % 3]
        t = {"PAYMENT_CARD_NUMBER": "Kart nömrəsi: {v}", "ICCID": "SIM kartın kodu {v}.", "IBAN": "Hesab: {v}"}[lab]
        b.add("decoy_card_iccid_iban", i, "valid", render(t, v=(b.val(lab), lab)))
        dv, k, p = b.look(lab)
        b.add("decoy_card_iccid_iban", i, "invalid", render(t.replace("{v}", "{d}"), d=(dv, lab, k, p)))
    orgs = [("Rəşad", "GIVENNAME", "MMC"), ("Hüseynov", "SURNAME", "Holdinq"), ("Gəncə", "CITY", "layihəsi"),
            ("Aysel", "GIVENNAME", "Market"), ("Babayev", "SURNAME", "ASC"), ("Quba", "CITY", "festivalı")]
    for i in range(12):
        name, lab, suf = orgs[i % len(orgs)]
        b.add("decoy_names_as_org", i, "valid", render("Müqaviləni {v} imzaladı.", v=(name, lab)))
        b.add("decoy_names_as_org", i, "invalid", render("Müqaviləni {d} imzaladı.", d=(f"{name} {suf}", lab, "name_as_org", True)))
    # --- spurious mentions ------------------------------------------------------
    for i in range(12):
        n = r.randint(100, 499)
        b.add("building_vs_room", i, "building", render("Ofis {v} saylı binada yerləşir.", v=(str(r.randint(2, 99)), "BUILDINGNUM")))
        b.add("building_vs_room", i, "room", render("Toplantı otaq {c} içində keçiriləcək.", c=(str(n), "BUILDINGNUM", "room_number")))
    nouns = ["Ərizənin", "Müqavilənin", "Hesabatın", "Sifarişin", "Kitabçanın", "Cədvəlin", "Qaimənin", "Arayışın",
             "Bildirişin", "Qərarın", "Tapşırığın", "Protokolun"]
    for i in range(12):
        nm = GIVEN[i]
        gen = {"Rəşad": "Rəşadın", "Aysel": "Ayselin", "Tural": "Turalın", "Nigar": "Nigarın", "Kamran": "Kamranın",
               "Səbinə": "Səbinənin", "Orxan": "Orxanın", "Lalə": "Lalənin", "Vüqar": "Vüqarın", "Günay": "Günayın",
               "Elçin": "Elçinin", "Nərmin": "Nərminin"}[nm]
        b.add("sentence_initial_nouns", i, "name", render("{v} surəti dünən arxivə verildi.", v=(gen, "GIVENNAME", {"case": "gen"})))
        b.add("sentence_initial_nouns", i, "noun", render("{c} surəti dünən arxivə verildi.", c=(nouns[i], "GIVENNAME", "sentence_initial_noun")))
    ids = [("Sifariş nömrəsi {c} üzrə çatdırılma gecikir.", lambda: "SF-" + _rs(r, DIG, 6), "AZ_FIN"),
           ("İzləmə kodu {c} ilə bağlamanı tapın.", lambda: _rs(r, DIG, 16), "PAYMENT_CARD_NUMBER"),
           ("Bilet nömrəsi {c} artıq istifadə olunub.", lambda: "TK" + _rs(r, DIG, 7), "AZ_ID_CARD_NUMBER"),
           ("Qaimə {c} ödənilib.", lambda: _rs(r, DIG, 10), "AZ_VOEN"),
           ("Müraciət {c} qeydə alınıb.", lambda: "REF" + _rs(r, DIG, 6), "AZ_PASSPORT_NUMBER"),
           ("Partiya kodu {c} anbara daxil oldu.", lambda: _rs(r, UP, 3) + _rs(r, DIG, 4), "AZ_FIN")]
    pii_for = {"AZ_FIN": "FİN kodu {v} olaraq təsdiqləndi.", "PAYMENT_CARD_NUMBER": "Ödəniş {v} kartından keçdi.",
               "AZ_ID_CARD_NUMBER": "Şəxsiyyət vəsiqəsi {v} təqdim edildi.", "AZ_VOEN": "Şirkətin VÖEN-i {v}.",
               "AZ_PASSPORT_NUMBER": "Pasport nömrəsi {v}."}
    for i in range(12):
        t, mk, lab = ids[i % len(ids)]
        b.add("nonpii_ids", i, "pii", render(pii_for[lab], v=(b.val(lab), lab)))
        b.add("nonpii_ids", i, "id", render(t, c=(mk(), lab, "non_pii_identifier")))
    # --- prose and anchors -------------------------------------------------------
    b.pairs_archive("prose_card", [("ödəniş kartı olaraq {v} yazılıb", "PAYMENT_CARD_NUMBER"),
                                    ("kart məlumatında {v} göstərilib", "PAYMENT_CARD_NUMBER"),
                                    ("ödəniş üçün {v} kartı qeyd olunub", "PAYMENT_CARD_NUMBER")])
    b.pairs_archive("prose_date", [("müraciətdə {v} tarixini yazmışam", "DATE"), ("tarix {v} kimi göstərilib", "DATE"),
                                    ("görüş tarixi olaraq {v} seçilib", "DATE")])
    b.pairs_archive("prose_iban", [("köçürmə üçün hesab olaraq {v} qeyd edilib", "IBAN"),
                                    ("ödəniş {v} hesabına yönləndirilib", "IBAN"), ("fakturada {v} hesabı göstərilib", "IBAN")])
    b.pairs_archive("anchor_distance", [
        ("telefon nömrəsi soruşulmuşdu, bir qədər axtarışdan sonra tapıldı: {v}", "TELEPHONENUM"),
        ("doğum tarixi ilə bağlı əvvəlki qeyd səhv idi, sonradan düzgünü yazıldı: {v}", "DATE"),
        ("e-poçt ünvanı dəyişib, köhnəsi işləmir, yenisi bu kimi qeyd olunub: {v}", "EMAIL"),
        ("hesab nömrəsi barədə ötən həftə danışılmışdı, indi ayrıca əlavə edilib: {v}", "IBAN"),
        ("vəsiqə məlumatı lazım idi; çantadan tapılan sənədin nömrəsi {v}", "AZ_ID_CARD_NUMBER"),
        ("kart barədə sual verilmişdi, axırda tapıldı, üstündə {v} yazılıb", "PAYMENT_CARD_NUMBER")])
    b.pairs_archive("inflected_anchor", [
        ("zəhmət olmasa doğum tarixini düzəldin, düzgünü {v}", "DATE"), ("görüş vaxtını dəyişdik, indi {v}", "TIME"),
        ("ünvan indeksində səhv var idi, düzgünü {v}", "ZIPCODE"), ("telefon nömrəsinə SMS gəlmədi: {v}", "TELEPHONENUM"),
        ("kart nömrəsini yenidən yoxlayın: {v}", "PAYMENT_CARD_NUMBER"), ("FİN kodunu bazaya daxil etdim: {v}", "AZ_FIN")])
    # --- structured formats: EMAIL and ID card inside each -----------------------------
    for i in range(12):
        e, idc, ph = format_email(r), b.val("AZ_ID_CARD_NUMBER"), b.val("TELEPHONENUM")
        de, di = b.look("EMAIL")[0], b.look("AZ_ID_CARD_NUMBER")[0]
        for valid in (True, False):
            E = ("g", e, "EMAIL") if valid else ("h", de, "EMAIL")
            ID = ("g", idc, "AZ_ID_CARD_NUMBER") if valid else ("h", di, "AZ_ID_CARD_NUMBER")
            PH_ = ("g", ph, "TELEPHONENUM")
            fmts = {
                "fmt_csv": ["e_poçt;şəxsiyyət_vəsiqəsi;telefon\n", E, ";", ID, ";", PH_],
                "fmt_csv_noheader": [E, ",", ID, ",", PH_, ",aktiv"],
                "fmt_json": ['{\n  "e_poçt": "', E, '",\n  "şəxsiyyət_vəsiqəsi": "', ID, '",\n  "telefon": "', PH_, '"\n}'],
                "fmt_pipe": ["| e_poçt | şəxsiyyət_vəsiqəsi | telefon |\n|---|---|---|\n| ", E, " | ", ID, " | ", PH_, " |"],
                "fmt_log": ["[INFO] info e_poçt=", E, " şəxsiyyət_vəsiqəsi=", ID, " telefon=", PH_],
                "fmt_kv": ["e_poçt məlumatı: ", E, "\nşəxsiyyət_vəsiqəsi məlumatı: ", ID, "\ntelefon: ", PH_],
                "fmt_dialogue": ["Operator: Poçtunuzu deyin.\nMüştəri: ", E, "\nOperator: Vəsiqə nömrəsi?\nMüştəri: ",
                                 ID, ", telefonum ", PH_],
            }
            for fam, parts in fmts.items():
                b.add(fam, i, "valid" if valid else "invalid", assemble(parts))
    # --- boundary families ------------------------------------------------------
    for i in range(10):
        one = i % 2 == 1
        t = "[WARN] info private_key={v} env=prod" if one else "Səhvən repoya düşən açar:\n{v}\nDərhal ləğv edin."
        b.add("pem", i, "valid", render(t, v=(long_pem(r, one), "PRIVATE_KEY")))
        b.add("pem", i, "invalid", render(t.replace("{v}", "{d}"), d=(b.look("PRIVATE_KEY")[0], "PRIVATE_KEY", "invalid_shape", False)))
    for i in range(12):
        op, x, y, z = r.choice(["50", "55", "70", "77"]), r.randint(200, 989), r.randint(10, 99), r.randint(10, 99)
        # irregular real groupings after a weak anchor (the benchmark's "dönüş üçün" misses)
        v = [f"{op} {x} {y} {z}", f"0{op} {x}{y}{z}", f"+994 {op} {x}{y}{z}", f"8 0{op} {x} {y} {z}"][i % 4]
        doc = archive_wrap(r, ["geri dönüş üçün {v} yazılıb", "zəng üçün {v} qeyd olunub",
                                  "dönüş üçün {v} göstərilib"][i % 3])
        b.add("spaced_phone", i, "valid", render(doc, v=(v, "TELEPHONENUM")))
        b.add("spaced_phone", i, "invalid", render(doc.replace("{v}", "{d}"), d=(b.look("TELEPHONENUM")[0], "TELEPHONENUM", "invalid_shape", False)))
    for i in range(12):
        lab = ["PAYMENT_CARD_NUMBER", "IBAN"][i % 2]
        t = ["Kart: {v}, sahibi təsdiqlənib.", "Köçürmə {v} hesabına edilsin."][i % 2]
        b.add("spaced_card_iban", i, "valid", render(t, v=(b.val(lab, spaced=True), lab)))
        dv, k, p = b.look(lab)
        b.add("spaced_card_iban", i, "invalid", render(t.replace("{v}", "{d}"), d=(dv, lab, k, p)))
    glue = [("Əlaqə:({v})", "TELEPHONENUM"), ("IBAN:{v}.", "IBAN"), ("Poçt — {v}!", "EMAIL"), ("[{v}]", "IPV4_ADDRESS"),
            ("FİN:{v};", "AZ_FIN"), ("\"{v}\"", "AZ_PASSPORT_NUMBER")]
    for i in range(12):
        t, lab = glue[i % len(glue)]
        kw = {"spaced": False} if lab == "TELEPHONENUM" else ({"spaced": False} if lab == "IBAN" else {})
        b.add("punct_touching", i, "valid", render(t, v=(b.val(lab, **kw), lab)))
        dv, k, p = b.look(lab)
        b.add("punct_touching", i, "invalid", render(t.replace("{v}", "{d}"), d=(dv, lab, k, p)))
    noisy = [("Xınalıq", "XINALIQ", "CITY"), ("Qəbələ", "qAbAlA", "CITY"), ("Hüseynova", "HUSEYNOVA", "SURNAME"),
             ("Lahıc", "LaHiC", "CITY"), ("İlisu", "iLiSu", "CITY"), ("Quliyev", "QULIYEV", "SURNAME"),
             ("Nardaran", "nArDaRaN", "CITY"), ("Səfərova", "SEFEROVA", "SURNAME"), ("Qrız", "QRIZ", "CITY"),
             ("Mərdəkan", "MeRdEkAn", "CITY"), ("Rəşad", "RESAD", "GIVENNAME"), ("Şüvəlan", "SUVELAN", "CITY")]
    for i, (clean, noise, lab) in enumerate(noisy):
        t = {"CITY": "Bağlama {v} ünvanına gedir.", "GIVENNAME": "Yazı {v} tərəfindən göndərilib.",
             "SURNAME": "Yazı {v} tərəfindən göndərilib."}[lab]
        b.add("casing_noise", i, "clean", render(t, v=(clean, lab)))
        b.add("casing_noise", i, "noised", render(t, v=(noise, lab, {"entity_noise": "case_or_ascii"})))
    b.pairs_archive("single_entity", [("əlaqə üçün {v} nömrəsi göstərilib", "TELEPHONENUM"),
                                       ("yeni əməkdaşın poçtu {v} kimi qeyd olunub", "EMAIL"),
                                       ("ödəniş hesabı {v} olaraq qalır", "IBAN"), ("FİN kodu {v} yazılıb", "AZ_FIN")])
    for i in range(24):
        labs = r.sample(["CARD_SECURITY_CODE", "TIME", "AGE", "DATE", "ZIPCODE", "AZ_FIN", "IPV4_ADDRESS", "MAC_ADDRESS"], 2)
        cl = {"CARD_SECURITY_CODE": "CVV sahəsində {d} qalıb", "TIME": "cədvəldə saat {d} yazılıb",
              "AGE": "yaş sahəsində {d} görünür", "DATE": "tarix sahəsinə {d} düşüb", "ZIPCODE": "indeks olaraq {d} qeyd edilib",
              "AZ_FIN": "sifariş kodu {d} göstərilib", "IPV4_ADDRESS": "versiya {d} quraşdırılıb",
              "MAC_ADDRESS": "qısa kod {d} yazılıb"}
        parts, hns = archive_text(r, r.randint(2, 3)) + "; ", []
        text = parts
        for lab in labs:
            dv, kind, pol = b.look(lab)
            clause = cl[lab]
            k = clause.index("{d}")
            s0 = len(text) + k
            text += clause.replace("{d}", dv) + "; "
            hns.append({"start": s0, "end": s0 + len(dv), "resembles": lab, "kind": kind, "policy": pol})
        text += archive_text(r, 1) + "."
        b.add("pii_free", i // 2, "free", (text, [], hns, []))
    # --- RC8: suffixed entities --------------------------------------------------------
    by_case: dict[str, list] = {}
    for case, lab, bare, form in SUFFIXED:
        by_case.setdefault(case, []).append((lab, bare, form))
    for case, items in by_case.items():
        frames = SUFFIX_FRAMES[case]
        for j in range(21):
            lab, bare, form = items[j % len(items)]
            b.add("suffixed_entities", j, case, render(frames[j % len(frames)], v=(form, lab, {"case": case})), stem=bare)
    # --- RC9: bare names (D-10: a lone lowercase homograph is not masked) ----------
    exact_failures = [("Fidan.", [("Fidan", "GIVENNAME")]), ("Fidan Məmmədova", [("Fidan", "GIVENNAME"), ("Məmmədova", "SURNAME")]),
                      ("Aydın", [("Aydın", "GIVENNAME")]), ("Bahar", [("Bahar", "GIVENNAME")]), ("Dəniz", [("Dəniz", "GIVENNAME")])]
    bare = list(exact_failures)
    bare += [(g, [(g, "GIVENNAME")]) for g in ["Rəşad", "Nigar", "Kamran", "Səbinə", "Orxan", "Günay", "Elçin"]]
    bare += [(f"{g} {s}", [(g, "GIVENNAME"), (s, "SURNAME")]) for g, s in [("Tural", "Hüseynov"), ("Aysel", "Quliyeva"), ("Vüqar", "Səfərov")]]
    bare += [(f"{s} {g}", [(s, "SURNAME"), (g, "GIVENNAME")]) for g, s in [("Lalə", "Rzayeva"), ("Ramil", "Orucov"), ("Könül", "Abbasova")]]
    bare += [(t, [(n, "GIVENNAME")]) for t, n in [("Fidan!", "Fidan"), ("(Fidan)", "Fidan"), ("\"Nərmin\"", "Nərmin"),
                                                  ("Aysel,", "Aysel"), ("Tural?", "Tural"), ("— Kamran", "Kamran")]]
    bare += [(t, [(n, "GIVENNAME")]) for t, n in [("Salam, Nigar!", "Nigar"), ("Hörmətlə, Orxan", "Orxan"),
                                                  ("Sağ ol, Səbinə!", "Səbinə"), ("Əziz Fuad,", "Fuad"), ("Görüşənədək, Zəhra", "Zəhra")]]
    bare += [("Hörmətlə, Ceyhun Musayev", [("Ceyhun", "GIVENNAME"), ("Musayev", "SURNAME")])]
    bare += [(c, [(c, "CITY")]) for c in ["Gəncə", "Şəki", "Lənkəran", "Quba"]]
    bare += [(s, [(s, "STREET")]) for s in ["Nizami küçəsi", "Azadlıq prospekti", "Füzuli küçəsi"]]
    for i, (text, ents) in enumerate(bare):
        spans, pos = [], 0
        for val, lab in ents:
            s = text.index(val, pos)
            spans.append({"start": s, "end": s + len(val), "label": lab})
            pos = s + len(val)
        b.add("bare_name", i, "exact_failure" if i < len(exact_failures) else "bare", (text, spans, [], []))
    for i, w in enumerate(["dəniz", "bahar", "aydın", "fidan", "ulduz", "lalə"]):          # D-10 controls
        b.add("bare_name", 100 + i, "lowercase_homograph", (w, [], [], []), control=True, resembles="GIVENNAME")
    # --- RC9: homographs ----------------------------------------------------------
    for i, (name, as_name, as_word) in enumerate(HOMOGRAPHS):
        s = as_name.index(name)
        b.add("name_homographs", i, "name", (as_name, [{"start": s, "end": s + len(name), "label": "GIVENNAME"}], [], []))
        w = as_word.index(name)
        b.add("name_homographs", i, "word", (as_word, [], [], [{"start": w, "end": w + len(name), "resembles": "GIVENNAME",
                                                                 "kind": "homograph_word"}]))
    # --- transliteration variants -------------------------------------------------------
    for i, (lab, variants) in enumerate(TRANSLIT):
        for j, v in enumerate(variants):
            for t in TRANSLIT_FRAMES[lab]:
                b.add("name_transliteration_variants", i, VARIANT_NAMES[j],
                      render(t, v=(v, lab, {"variant": VARIANT_NAMES[j]})))
    # --- D-56a (1): IPs and emails ending a line or sentence without a final period --------
    # v4.1 split them (`mənim ip [219].[83.211.173]`, the v4 -> v4.1 note). Written for
    # the probes, last in build() so every earlier family draws the same values; no frame here
    # is in the training generator. Each frame once with an IPv4, an IPv6 and an email.
    line_end = ["Sorğu bu ünvandan gəlib: {v}", "Müştəri yazır: mənim ünvanım {v}",
                "Sistem qeydi, mənbə ünvanı {v};", "Ünvanı bir də yoxlayın {v}",
                "Dünən axşam {v} ünvanından giriş olub", "Hesabatda göstərilən ünvan {v};",
                "Admin: yeni ünvan əlavə edildi {v}", "Bildirişdəki ünvan {v}"]
    for i, t in enumerate(line_end):
        for lab in ("IPV4_ADDRESS", "IPV6_ADDRESS", "EMAIL"):
            b.add("line_end_ip_email", i, lab.split("_")[0].lower(), render(t, v=(b.val(lab), lab)))


# D-34c: look-alikes that contradict the labelling convention (D-30b, D-33 treat dashed CVVs
# like `12-8` and O-initial FINs as real values), so a correct model would be penalised. They
# move to the policy bucket: kind "policy_d34c", scored and reported apart, left out of C4
# (`exclude_kinds` in targets.json). D-34c moved the two dashed CVVs Run B masks; D-39c moves the
# other three too (POLICY_MOVES below): the convention decides, not the model's result.
D34C_POLICY = {"decoy_cvv_010": "CARD_SECURITY_CODE", "decoy_cvv_022": "CARD_SECURITY_CODE",
               "decoy_fin_004": "AZ_FIN", "decoy_fin_012": "AZ_FIN", "decoy_fin_018": "AZ_FIN"}


def apply_d34c(out: dict) -> int:
    n = 0
    for rows in out.values():
        for rec in rows:
            if rec["id"] in D34C_POLICY:
                hns = [h for h in rec.get("hard_negatives", []) if h["resembles"] == D34C_POLICY[rec["id"]]]
                assert len(hns) == 1, rec["id"]
                hns[0]["kind"], hns[0]["policy"] = "policy_d34c", True
                n += 1
    assert n == len(D34C_POLICY), n
    return n


# Look-alikes moved to the policy bucket by a decision: scored and reported apart (D-29 F3).
# id -> (label it resembles, kind). D-36d: after D-34b, masking a 6-character code after FIN is
# the intended behaviour, so the 6-character dummy FIN in punct_touching is a policy item.
# D-39c: all 5 dashed (`99-9`) CVV look-alikes follow the convention (D-30b), so the 3 that
# D-34c left in decoy_cvv join the 2 already moved.
POLICY_MOVES = {"punct_touching_022": ("AZ_FIN", "policy_d36d"),
                "decoy_cvv_006": ("CARD_SECURITY_CODE", "policy_d39c"),
                "decoy_cvv_018": ("CARD_SECURITY_CODE", "policy_d39c"),
                "decoy_cvv_024": ("CARD_SECURITY_CODE", "policy_d39c"),
                # D-41c: the dashed CVVs in pii_free follow D-39c; their documents leave the PII-free count
                "pii_free_005": ("CARD_SECURITY_CODE", "policy_d39c"),
                "pii_free_017": ("CARD_SECURITY_CODE", "policy_d39c"),
                "pii_free_021": ("CARD_SECURITY_CODE", "policy_d39c")}


def apply_policy_moves(out: dict) -> int:
    n = 0
    for rows in out.values():
        for rec in rows:
            if rec["id"] in POLICY_MOVES:
                lab, kind = POLICY_MOVES[rec["id"]]
                hns = [h for h in rec.get("hard_negatives", []) if h["resembles"] == lab]
                assert len(hns) == 1, rec["id"]
                hns[0]["kind"], hns[0]["policy"] = kind, True
                n += 1
    assert n == len(POLICY_MOVES), n
    return n


# D-51d (2026-10-15): cards and IBANs are masked whatever their checksum (privacy first, as
# D-33c for FINs). A card look-alike whose only defect is its Luhn digit (13-19 digits, the
# right check digit makes it a valid card) or an IBAN look-alike whose only defect is its mod-97
# check digits is a real value under that rule, so it moves to the policy bucket: kind
# "policy_d51d", scored and reported apart, left out of C4. Shape-invalid look-alikes (IBAN
# fragments, short ICCIDs) stay. Chosen by rule, not by id or by any model's result.
D51D_LABELS = ("PAYMENT_CARD_NUMBER", "IBAN")
CARD_PREFIXES = ("4", "51", "52", "53", "54", "55", "2", "34", "37", "6", "35", "9")


def _iban_check(v: str) -> str:
    n = int("".join(str(int(c, 36)) for c in v[4:] + v[:2] + "00"))
    return f"{98 - n % 97:02d}"


def checksum_only(label: str, value: str) -> bool:
    v = "".join(value.split())
    if label == "PAYMENT_CARD_NUMBER":
        return (v.isdigit() and 13 <= len(v) <= 19 and v.startswith(CARD_PREFIXES)
                and v[-1] != _luhn(v[:-1]))
    if label == "IBAN":
        return (len(v) == 28 and v[:2] == "AZ" and v[2:4].isdigit() and v[4:].isalnum()
                and v[2:4] != _iban_check(v))
    return False


def apply_d51d(out: dict) -> int:
    n = 0
    for rows in out.values():
        for rec in rows:
            for h in rec.get("hard_negatives", []):
                if h["resembles"] in D51D_LABELS and not h["policy"] \
                        and checksum_only(h["resembles"], rec["text"][h["start"]:h["end"]]):
                    h["kind"], h["policy"] = "policy_d51d", True
                    n += 1
    return n


# The team, 15 Oct (after the v3 release check, #84): FIN look-alikes of 5-7 letters/digits
# (D-34a: 7 characters; D-34b: a foreign resident's PIN has 5-6) may be real identifiers after
# the word FIN, so they move to the policy bucket: kind "policy_fin_len". The dashed ones
# (`AA99-AA`) keep their wrong shape and stay. Chosen by rule, not by any model's result.
def apply_fin_len(out: dict) -> int:
    n = 0
    for rows in out.values():
        for rec in rows:
            for h in rec.get("hard_negatives", []):
                if h["resembles"] == "AZ_FIN" and not h["policy"] \
                        and re.fullmatch(r"[A-Z0-9]{5,7}", rec["text"][h["start"]:h["end"]]):
                    h["kind"], h["policy"] = "policy_fin_len", True
                    n += 1
    return n


def load_forbidden() -> set:
    ex = ROOT / "benchmarks" / "extracted"
    vals = {e["value"] for r in json.loads((ex / "records.json").read_text(encoding="utf-8")) for e in r["entries"]}
    with open(ex / "errors.csv", encoding="utf-8") as fh:
        vals |= {row["value"] for row in csv.DictReader(fh) if row["value"]}
    allow = {v for vs in D2.values() for v in vs}
    names = set(GIVEN + SURNAME + CITY + STREET + [h[0] for h in HOMOGRAPHS])
    return vals - allow - names


def check(out: dict, validators: str | None) -> list[str]:
    problems = []
    vv = None
    if validators:
        sys.path.insert(0, validators)
        from piigen.validate import value_valid as vv  # noqa: E402
    for fam, rows in out.items():
        for rec in rows:
            t = rec["text"]
            spans = [(e["start"], e["end"]) for e in rec["entities"]] + \
                [(h["start"], h["end"]) for h in rec.get("hard_negatives", [])] + \
                [(c["start"], c["end"]) for c in rec.get("controls", [])]
            spans.sort()
            for (s, e), (s2, _) in zip(spans, spans[1:]):
                if s2 < e:
                    problems.append(f"{rec['id']}: overlapping spans")
            for s, e in spans:
                if not (0 <= s < e <= len(t)) or t[s:e] != t[s:e].strip():
                    problems.append(f"{rec['id']}: bad span {s}-{e}")
            if vv:
                for e in rec["entities"]:
                    if fam != "casing_noise" and not vv(e["label"], t[e["start"]:e["end"]])[0]:
                        problems.append(f"{rec['id']}: gold not valid {e['label']}")
                for h in rec.get("hard_negatives", []):
                    if not h["policy"] and vv(h["resembles"], t[h["start"]:h["end"]])[0] \
                            and h["resembles"] not in ("GIVENNAME", "SURNAME", "CITY", "STREET", "BUILDINGNUM"):
                        problems.append(f"{rec['id']}: decoy still valid {h['resembles']}")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=33)
    ap.add_argument("--validators", default=None, help="directory containing piigen/ (checking only)")
    ap.add_argument("--out", type=Path, default=HERE)
    args = ap.parse_args(argv)
    b = Builder(args.seed, load_forbidden())
    build(b)
    apply_policy_moves(b.out)
    apply_d34c(b.out)
    n51 = apply_d51d(b.out)
    assert n51 == 24, n51  # D-51d: 11 13-digit and 13 16-digit Luhn-only card look-alikes
    nfin = apply_fin_len(b.out)
    assert nfin == 10, nfin  # 6 of 5 digits, 4 of 7 characters
    problems = check(b.out, args.validators)
    for fam, rows in sorted(b.out.items()):
        (args.out / f"{fam}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows),
                                               encoding="utf-8")
    print(f"{len(b.out)} families, {sum(len(v) for v in b.out.values())} documents; "
          f"{sum(len(x['entities']) for v in b.out.values() for x in v)} gold, "
          f"{sum(len(x.get('hard_negatives', [])) for v in b.out.values() for x in v)} look-alikes, "
          f"{sum(len(x.get('controls', [])) + bool(x.get('control')) for v in b.out.values() for x in v)} controls")
    print("problems:", len(problems))
    for p in problems[:20]:
        print("  ", p)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
