"""Build the Run B probe families (P3-3): eval/probes/<family>.jsonl.

    python eval/probes/build_probes_runb.py [--seed 34] [--validators scripts]

One family per thing Run B's data adds (D-23..D-27, P2-1/P2-4 contrast pairs,
P2-4c noisy suffixes, P2-4d/P4-2 homograph pairs, D-17 dates, D-23c villages,
D-23d foreign names):

  noisy_suffixes        misspelt suffixes on names and cities (harmony, dropped
                        buffer, doubled consonant, spoken -nAn), common nouns
                        with the same misspellings as controls
  contrast_token_key    ACCESS_TOKEN and API_KEY side by side, same body;
                        commit/UUID/digest/identifier look-alikes
  contrast_ipv6_mac     compressed IPv6 ("::" in the middle, at the end,
                        <prefix>::1, ::ffff:a.b.c.d, fe80::), MAC with ":" "-"
                        "." separators, both side by side; hex hashes,
                        fingerprints, timestamps, C++ scopes, UUIDs as decoys
  contrast_licence_id   licence (2 letters + 6 digits) and ID card (AA/AB + 7)
                        with the same prefix in one document; plates and
                        wrong-length codes as decoys
  homograph_pairs       a name that is also a word, both uses in one document,
                        either side inflected (names outside P4-2's list)
  date_vs_timestamp     standalone dates (DATE) next to date+time timestamps
                        (not DATE, D-17) in the same document
  villages              Azerbaijani villages and settlements (CITY), inflected,
                        with ordinary-word and generic-place controls
  foreign_names         Russian, Turkish, Georgian, Persian/Arabic and
                        English/European names (outside the generator's pool);
                        brand names in the same slots as decoys

Independence (rule A2.5 / RC7) as in build_probes.py: every sentence, name
form and value maker here was written for the probes. Nothing comes from
frames_az.py, homographs_az.py, values.py, negatives.py, suffix.py,
scripts/piigen/targeted/, the locale pools, the training corpus or the
private shadow set. Names, villages and inflected forms are literal strings.
Validators are only used to CHECK the result (--validators).

Records use build_probes.py's format: corpus schema + family, pair, role;
`hard_negatives` for look-alikes, `controls` for ordinary-word uses. Extra
entity fields slice the scoreboard: `noise` (noisy_suffixes), `form`
(IPv6 and date forms), `sep` (MAC separators), `origin` (foreign names).
"""
from __future__ import annotations

import argparse
import base64
import json
import random
import re
import string
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_probes as BP  # noqa: E402  (render/check/Builder: the probes' own code)

DIG, UP, LOW = string.digits, string.ascii_uppercase, string.ascii_lowercase
ALNUM = string.ascii_letters + DIG
HEX = "0123456789abcdef"
FAMILIES = ["noisy_suffixes", "contrast_token_key", "contrast_ipv6_mac", "contrast_licence_id",
            "homograph_pairs", "date_vs_timestamp", "villages", "foreign_names"]
SLOT = re.compile(r"\{(\w+)\}")
# [[value|LABEL|key=val...]] gold · {{value|RESEMBLES|kind}} look-alike · <<value|RESEMBLES|kind>> control
MARK = re.compile(r"\[\[(.+?)\|([A-Z_]+)((?:\|\w+=[^|\]]+)*)\]\]"
                  r"|\{\{(.+?)\|([A-Z_]+)\|(\w+)\}\}"
                  r"|<<(.+?)\|([A-Z_]+)\|(\w+)>>")


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def marked(s: str):
    """Hand-written text with inline marks -> (text, gold, hard negatives, controls)."""
    text, ents, hns, ctl, pos = "", [], [], [], 0
    for m in MARK.finditer(s):
        text += s[pos:m.start()]
        st = len(text)
        if m.group(1) is not None:
            text += m.group(1)
            extra = dict(kv.split("=", 1) for kv in m.group(3).split("|") if kv)
            ents.append({"start": st, "end": len(text), "label": m.group(2), **extra})
        elif m.group(4) is not None:
            text += m.group(4)
            hns.append({"start": st, "end": len(text), "resembles": m.group(5), "kind": m.group(6),
                        "policy": False})
        else:
            text += m.group(7)
            ctl.append({"start": st, "end": len(text), "resembles": m.group(8), "kind": m.group(9)})
        pos = m.end()
    return text + s[pos:], ents, hns, ctl


def fill(template: str, **slots):
    """{name} slots -> (text, gold, hard negatives, controls). A slot is
    ("g", value, label[, extra]) for gold or ("h", value, resembles, kind)."""
    text, ents, hns, pos = "", [], [], 0
    for m in SLOT.finditer(template):
        text += template[pos:m.start()]
        kind, value, lab, *rest = slots[m.group(1)]
        st = len(text)
        text += value
        if kind == "g":
            ents.append({"start": st, "end": len(text), "label": lab, **(rest[0] if rest else {})})
        else:
            hns.append({"start": st, "end": len(text), "resembles": lab, "kind": rest[0], "policy": False})
        pos = m.end()
    return text + template[pos:], ents, hns, []


# ---------------------------------------------------------------------------
# Value makers (own code; shapes from data/schema.md and real-world formats)
# ---------------------------------------------------------------------------

def _rs(r, a, n):
    return "".join(r.choice(a) for _ in range(n))


def _grp(r):
    return f"{r.randint(1, 0xffff):x}"


V6_PREFIX = ["2a02:4780", "2a0b:f300", "2a10:cc4", "2c0f:f7a8", "2400:8902", "2604:a880", "2800:3f0",
             "2a01:4f8", "2a00:1450", "2a05:d014"]
IPV6_FORMS = ["mid", "end", "prefix_one", "mapped", "link_local", "upper", "full"]


def ipv6(r, form):
    if form in ("mid", "upper"):
        pre = r.choice(V6_PREFIX).split(":") + [_grp(r) for _ in range(r.randint(0, 2))]
        post = [_grp(r) for _ in range(r.randint(1, 6 - len(pre)))]
        v = ":".join(pre) + "::" + ":".join(post)
        return v.upper() if form == "upper" else v
    if form == "end":
        return r.choice(V6_PREFIX) + ":" + _grp(r) + "::"
    if form == "prefix_one":
        return f"fd{_rs(r, HEX, 2)}:{_grp(r)}:{_grp(r)}::1"
    if form == "mapped":
        return f"::ffff:{r.choice([5, 37, 62, 85, 109, 188])}.{r.randint(0, 255)}.{r.randint(0, 255)}.{r.randint(1, 254)}"
    if form == "link_local":
        return f"fe80::{_grp(r)}:{_rs(r, HEX, 2)}ff:fe{_rs(r, HEX, 2)}:{_grp(r)}"
    return ":".join([r.choice(V6_PREFIX).split(":")[0]] + [_grp(r) for _ in range(7)])  # full


MAC_SEPS = ["colon", "hyphen", "dot"]


def mac(r, sep):
    b = [_rs(r, HEX, 2) for _ in range(6)]
    case = r.choice([str.upper, str.lower])
    if sep == "dot":
        return ".".join("".join(b[i:i + 2]) for i in (0, 2, 4)).lower()
    return case((":" if sep == "colon" else "-").join(b))


TOKEN_PREFIX = ["at_", "tok_", "oauth_", "sess_", "pat_", "atk-"]
KEY_PREFIX = ["key_", "api_", "apikey_", "svc_"]


def token_key_same_body(r):
    body = _rs(r, ALNUM, r.randint(24, 40))
    return r.choice(TOKEN_PREFIX) + body, r.choice(KEY_PREFIX) + body


def _b64(obj) -> str:
    return base64.urlsafe_b64encode(json.dumps(obj, separators=(",", ":")).encode()).decode().rstrip("=")


def jwt(r):
    head = _b64({"alg": r.choice(["HS256", "RS256", "ES256"]), "typ": "JWT"})
    body = _b64({"sub": _rs(r, DIG, 8), "iat": r.randint(1_700_000_000, 1_790_000_000),
                 "scope": r.choice(["read", "write", "profile"])})
    return f"{head}.{body}.{_rs(r, ALNUM + '-_', 43)}"


def sk_key(r):
    return r.choice(["sk-live-", "sk-test-"]) + _rs(r, ALNUM, r.randint(24, 32))


def lic_id_same_prefix(r):
    p = r.choice(["AA", "AB"])
    return p + _rs(r, DIG, 6), p + _rs(r, DIG, 7)


def licence_other(r):
    while True:
        p = _rs(r, UP, 2)
        if p not in ("AA", "AB"):
            return p + _rs(r, DIG, 6)


MONTHS_AZ = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avqust", "sentyabr", "oktyabr",
             "noyabr", "dekabr"]
DATE_FORMS = ["dmy_dot", "iso", "dmy_slash", "worded", "dmy_dot_short"]


def date(r, form):
    # 2011-2014: every calendar day of 2015-2026 occurs somewhere in Run B's corpus
    y, m, d = r.randint(2011, 2014), r.randint(1, 12), r.randint(1, 28)
    return {"dmy_dot": f"{d:02d}.{m:02d}.{y}", "iso": f"{y}-{m:02d}-{d:02d}", "dmy_slash": f"{d:02d}/{m:02d}/{y}",
            "worded": f"{d} {MONTHS_AZ[m - 1]} {y}", "dmy_dot_short": f"{d}.{m}.{y}"}[form]


def timestamp(r, i):
    y, m, d = r.randint(2019, 2026), r.randint(1, 12), r.randint(1, 28)
    h, mi, s = r.randint(0, 23), r.randint(0, 59), r.randint(0, 59)
    return [f"{y}-{m:02d}-{d:02d} {h:02d}:{mi:02d}:{s:02d}", f"{y}-{m:02d}-{d:02d}T{h:02d}:{mi:02d}:{s:02d}",
            f"{d:02d}.{m:02d}.{y} {h:02d}:{mi:02d}", f"{h:02d}:{mi:02d}, {d:02d}.{m:02d}.{y}",
            f"{y}/{m:02d}/{d:02d} {h:02d}:{mi:02d}:{s:02d}", f"{y}-{m:02d}-{d:02d} {h:02d}:{mi:02d}"][i % 6]


# IPv6/MAC look-alikes: (maker, resembles, kind), each verified invalid by check()
NET_DECOYS = [
    (lambda r: _rs(r, HEX, 32), "MAC_ADDRESS", "md5_hash"),
    (lambda r: _rs(r, HEX, 40), "IPV6_ADDRESS", "sha1_hash"),
    (lambda r: _rs(r, HEX, r.randint(7, 10)), "IPV6_ADDRESS", "commit_hash"),
    (lambda r: ":".join(_rs(r, HEX, 2) for _ in range(16)), "MAC_ADDRESS", "ssh_md5_fingerprint"),
    (lambda r: ":".join(_rs(r, "0123456789ABCDEF", 2) for _ in range(20)), "MAC_ADDRESS", "sha1_fingerprint"),
    (lambda r: f"{r.randint(0, 23):02d}:{r.randint(0, 59):02d}:{r.randint(0, 59):02d}.{r.randint(100, 999)}",
     "IPV6_ADDRESS", "timestamp"),
    (lambda r: f"{r.randint(0, 9):02d}:{r.randint(0, 59):02d}:{r.randint(0, 59):02d}:{r.randint(0, 24):02d}",
     "IPV6_ADDRESS", "timecode"),
    (lambda r: f"{r.randint(2019, 2026)}-{r.randint(1, 12):02d}-{r.randint(1, 28):02d}T{r.randint(0, 23):02d}:"
               f"{r.randint(0, 59):02d}:{r.randint(0, 59):02d}Z", "IPV6_ADDRESS", "timestamp"),
    (lambda r: r.choice(["std::chrono::steady_clock", "boost::asio::ip::tcp", "App::Http::Kernel",
                         "Net::DNS::Resolver", "std::filesystem::path"]), "IPV6_ADDRESS", "scope_operator"),
    (lambda r: f"{_rs(r, HEX, 8)}-{_rs(r, HEX, 4)}-4{_rs(r, HEX, 3)}-a{_rs(r, HEX, 3)}-{_rs(r, HEX, 12)}",
     "IPV6_ADDRESS", "uuid"),
    (lambda r: ":".join([r.choice(V6_PREFIX)] + [_grp(r) for _ in range(7)]), "IPV6_ADDRESS", "nine_groups"),
    (lambda r: ":".join(_rs(r, "0123456789ABCDEF", 2) for _ in range(5)), "MAC_ADDRESS", "five_octets"),
]
NET_DECOY_FRAMES = {
    "md5_hash": "Yüklənmiş faylın MD5 cəmi {x} ilə üst-üstə düşür.",
    "sha1_hash": "Arxivin SHA-1 heşi: {x}",
    "commit_hash": "Düzəliş {x} nömrəli commit-də edilib.",
    "ssh_md5_fingerprint": "Serverin SSH açarının barmaq izi {x} olaraq göstərildi.",
    "sha1_fingerprint": "Sertifikatın barmaq izi: {x}",
    "timestamp": "Proses {x} anında dayandı.",
    "timecode": "Video {x} anından kəsilməlidir.",
    "scope_operator": "Xəta {x} sinfində baş verib.",
    "uuid": "Sorğunun identifikatoru {x}, onu dəstək xidmətinə göndərin.",
    "nine_groups": "Konfiqurasiyada yazılmış {x} sətri qəbul edilmədi.",
    "five_octets": "Cədvəldə natamam qeyd qalıb: {x}",
}

# token/key look-alikes
SECRET_DECOYS = [
    (lambda r: _rs(r, HEX, 7), "ACCESS_TOKEN", "commit_hash", "Commit {x} test mühitinə yükləndi."),
    (lambda r: f"{_rs(r, HEX, 8)}-{_rs(r, HEX, 4)}-4{_rs(r, HEX, 3)}-b{_rs(r, HEX, 3)}-{_rs(r, HEX, 12)}",
     "ACCESS_TOKEN", "uuid", "Sorğu identifikatoru {x} ilə dəstəyə yazın."),
    (lambda r: "sha256:" + _rs(r, HEX, 64), "API_KEY", "image_digest", "Docker obrazının həzmi {x}."),
    (lambda r: r.choice(["access_token_ttl", "refresh_token_expiry", "token_cache_dir"]), "ACCESS_TOKEN",
     "identifier", "Kodda dəyişənin adı {x} kimi yazılıb."),
    (lambda r: r.choice(["api_quota_reset_hours", "apikey_header_name", "key_vault_url"]), "API_KEY",
     "identifier", "Konfiqurasiya parametri {x} dəyişdirilib."),
    (lambda r: "tok_" + _rs(r, ALNUM, r.randint(5, 9)), "ACCESS_TOKEN", "truncated",
     "Jurnalda tokenin yalnız başlanğıcı qalıb: {x}"),
    (lambda r: "key_" + _rs(r, ALNUM, r.randint(4, 8)), "API_KEY", "truncated",
     "Ekranda açarın ilk simvolları görünür: {x}"),
    (lambda r: f"/api/v{r.randint(1, 3)}/tokens", "ACCESS_TOKEN", "url_path", "Endpoint {x} artıq köhnəlib."),
]

PLATE_DECOYS = [
    (lambda r: f"{r.choice([10, 77, 90, 99, 20, 85])}-{r.choice(['AA', 'AB'])}-{r.randint(100, 999)}",
     "AZ_DRIVER_LICENSE_NUMBER", "car_plate", "Avtomobilin dövlət nömrə nişanı {x}."),
    (lambda r: f"{r.choice([10, 77, 90, 99, 20, 85])}-{r.choice(['AA', 'AB'])}-{r.randint(100, 999)}",
     "AZ_DRIVER_LICENSE_NUMBER", "car_plate", "Cərimə {x} nömrəli maşına yazılıb."),
    (lambda r: r.choice(["AA", "AB"]) + _rs(r, DIG, 5), "AZ_ID_CARD_NUMBER", "short_code",
     "Anbar hücrəsi {x} boşaldılıb."),
    (lambda r: r.choice(["AA", "AB"]) + _rs(r, DIG, 8), "AZ_ID_CARD_NUMBER", "long_code",
     "Bağlamanın izləmə kodu {x}."),
    (lambda r: r.choice(["AA", "AB"]) + _rs(r, DIG, 4), "AZ_DRIVER_LICENSE_NUMBER", "short_code",
     "Kassa çekinin nömrəsi {x}."),
]

# ---------------------------------------------------------------------------
# Hand-written texts
# ---------------------------------------------------------------------------

# P2-4c noisy suffixes: (noise type, text with one gold); correct form in the comment
NOISY = [
    ("harmony", "Səhər [[Zakirdan|GIVENNAME]] mesaj gəldi."),                    # Zakirdən
    ("harmony", "Bu hədiyyəni [[Mehribandən|GIVENNAME]] almışam."),              # Mehribandan
    ("harmony", "Sənədləri [[Nəsibovdən|SURNAME]] götürün."),                    # Nəsibovdan
    ("harmony", "Qardaşım indi [[Ağdaşdə|CITY]] işləyir."),                      # Ağdaşda
    ("harmony", "Gələn həftə [[Şabranə|CITY]] köçürük."),                        # Şabrana
    ("harmony", "[[Elşənın|GIVENNAME]] maşını həyətdə qalıb."),                  # Elşənin
    ("buffer", "Bu [[Nailəin|GIVENNAME]] kitabıdır."),                           # Nailənin
    ("buffer", "Zəhmət olmasa bunu [[Rənaa|GIVENNAME]] verin."),                 # Rənaya
    ("buffer", "[[Culfaın|CITY]] bazarı bazar günü bağlıdır."),                  # Culfanın
    ("buffer", "Sabah səhər [[Astaraa|CITY]] yola düşürük."),                    # Astaraya
    ("buffer", "Dünən [[Elmiraı|GIVENNAME]] parkda gördüm."),                    # Elmiranı
    ("buffer", "Məktubu [[Səlimovaa|SURNAME]] göndərmişəm."),                    # Səlimovaya
    ("double", "Bu yay [[Xaçmazdda|CITY]] dincəldik."),                          # Xaçmazda
    ("double", "Avtobus [[Tovuzddan|CITY]] gec çıxdı."),                         # Tovuzdan
    ("double", "Bu xəbəri [[Samirdden|GIVENNAME]] eşitdim."),                    # Samirdən
    ("double", "Pulu [[Qasımovddan|SURNAME]] aldıq."),                           # Qasımovdan
    ("double", "Axşam [[Elnurlla|GIVENNAME]] kinoya getdik."),                   # Elnurla
    ("double", "Nənəm [[Zərdabdda|CITY]] yaşayır."),                             # Zərdabda
    ("colloquial", "Dünən [[Ramiznən|GIVENNAME]] telefonda danışdım."),          # Ramizlə
    ("colloquial", "Bazara [[Kamalnan|GIVENNAME]] getmişəm."),                   # Kamalla
    ("colloquial", "Bu layihəni [[Aidaynan|GIVENNAME]] birlikdə bitirdik."),     # Aida ilə
    ("colloquial", "[[Masallıynan|CITY]] əlaqə bir saatlıq kəsilib."),           # Masallı ilə
    ("colloquial", "İclasdan sonra [[Kazımovnan|SURNAME]] görüşəcəm."),          # Kazımovla
    ("colloquial", "Müqaviləni [[Vəliyevnən|SURNAME]] imzalayacağıq."),          # Vəliyevlə
]
# the same misspellings on common nouns: never masked
NOISY_NOUNS = [
    ("harmony", "<<Məktəbdan|GIVENNAME|noisy_suffix_noun>> zəng gəldi."),
    ("harmony", "Uşaqlar <<bağdə|CITY|noisy_suffix_noun>> oynayır."),
    ("harmony", "Bu xəbəri <<qəzetdan|GIVENNAME|noisy_suffix_noun>> oxudum."),
    ("buffer", "Kağızları <<masaa|GIVENNAME|noisy_suffix_noun>> qoyun."),
    ("buffer", "<<Bağçaın|CITY|noisy_suffix_noun>> qapısı bağlıdır."),
    ("buffer", "Dünən <<qapıı|GIVENNAME|noisy_suffix_noun>> rəngladik."),
    ("double", "<<Evdde|CITY|noisy_suffix_noun>> heç kim yoxdur."),
    ("double", "<<Bazardda|CITY|noisy_suffix_noun>> təzə meyvə var."),
    ("double", "Bu kitabı <<dosttan|GIVENNAME|noisy_suffix_noun>> almışam."),
    ("colloquial", "<<Maşınnan|GIVENNAME|noisy_suffix_noun>> gəldik."),
    ("colloquial", "Axşam <<dostlarnan|GIVENNAME|noisy_suffix_noun>> çay içdik."),
    ("colloquial", "Bakıya <<qatarnan|CITY|noisy_suffix_noun>> getdim."),
]

# P2-4d/P4-2 homograph pairs: names outside P4-2's 56-name list
HOMOGRAPH_PAIRS = [
    "<<Gözəl|GIVENNAME|homograph_word>> bir gün idi, [[Gözəllə|GIVENNAME]] parkda gəzdik.",
    "[[Səhərə|GIVENNAME]] dedim ki, <<səhər|GIVENNAME|homograph_word>> tezdən gəlsin.",
    "<<Həyat|GIVENNAME|homograph_word>> bahalaşıb, [[Həyatın|GIVENNAME]] da maaşı artmayıb.",
    "[[Sakit|GIVENNAME]] otağa girəndə hamı <<sakit|GIVENNAME|homograph_word>> oturmuşdu.",
    "<<Nəsim|GIVENNAME|homograph_word>> pəncərədən içəri doldu, [[Nəsim|GIVENNAME]] isə yatmışdı.",
    "[[Yaqutun|GIVENNAME]] üzüyündəki daş <<yaqut|GIVENNAME|homograph_word>> deyil, şüşədir.",
    "<<Firuzə|GIVENNAME|homograph_word>> rəngli parçanı [[Firuzəyə|GIVENNAME]] bağışladım.",
    "[[Zümrüd|GIVENNAME]] dedi ki, boyunbağının daşları <<zümrüddür|GIVENNAME|homograph_word>>.",
    "<<İnamını|GIVENNAME|homograph_word>> itirmə, [[İnam|GIVENNAME]] sənə kömək edəcək.",
    "[[Vüsala|GIVENNAME]] yazdım ki, uzun ayrılıqdan sonra <<vüsal|GIVENNAME|homograph_word>> anı gəlib.",
    "[[Qüdrət|GIVENNAME]] yeni mühərrikin <<qüdrətinə|GIVENNAME|homograph_word>> heyran qaldı.",
    "<<Hünər|GIVENNAME|homograph_word>> göstərmək lazım idi və [[Hünər|GIVENNAME]] bunu bacardı.",
    "[[Səadətin|GIVENNAME]] yeganə arzusu ailəsinin <<səadəti|GIVENNAME|homograph_word>> idi.",
    "<<Sevda|GIVENNAME|homograph_word>> mahnısı oxunanda [[Sevda|GIVENNAME]] gülümsədi.",
    "[[Nemətə|GIVENNAME]] dedim ki, süfrədəki hər <<nemət|GIVENNAME|homograph_word>> halaldır.",
    "<<Mətanət|GIVENNAME|homograph_word>> göstər, — deyə [[Mətanət|GIVENNAME]] qızına pıçıldadı.",
]

# D-23c villages and settlements (none in the old 97-city pool, none a benchmark value)
VILLAGES = [
    "Nənəm [[Kürdəxanı|CITY]] qəsəbəsində yaşayır.",
    "Bu bal [[Cekdən|CITY]] gətirilib.",
    "Yay tətilini [[Əlikdə|CITY]] keçirdik.",
    "[[Vəndam|CITY]] kəndinin məktəbi təmir olunub.",
    "Atam hər gün [[İvanovkaya|CITY]] işə gedir.",
    "[[Kişdəki|CITY]] alban məbədinə ekskursiya təşkil olunub.",
    "Qardaşım [[Oxuddan|CITY]] zəng etdi.",
    "Ailəmiz [[Bumda|CITY]] bağ evi alıb.",
    "Bu il [[Qumda|CITY]] fındıq məhsulu yaxşı olub.",
    "Toy [[Carda|CITY]] olacaq.",
    "[[Zərnava|CITY]] sakinləri yeni yol istəyir.",
    "Müəllim [[Qalaaltıya|CITY]] təyinat alıb.",
    "Bağ evimiz [[Bilgəhdədir|CITY]].",
    "Avtobus [[Pirşağıdan|CITY]] səhər tezdən çıxır.",
    "[[Söhübdə|CITY]] yeni körpü tikiləcək.",
    "Biz [[Fatmayıda|CITY]] kirayədə qalırıq.",
    "Sifariş [[Hövsana|CITY]] çatdırılmalıdır.",
    "[[Zirənin|CITY]] bazarında təzə balıq satılır.",
    "Xalam [[Şağanda|CITY]] yaşayır.",
    "[[Xaltan|CITY]] kəndində yeni məktəb açılıb.",
    "Bu ünvan [[Masazırdadır|CITY]].",
    "Toyuqlar [[Digahdan|CITY]] gətirilir.",
    "Qonşumuz keçən ay [[Qobuya|CITY]] köçdü.",
    "[[Qonaqkənd|CITY]] kəndi dağların ətəyindədir.",
    "Babam [[Qəmərvanda|CITY]] doğulub.",
    "Bu xalçalar [[Talışnurudan|CITY]] gəlib.",
]
VILLAGE_CONTROLS = [
    "<<Qum|CITY|common_word>> ayaqqabıma dolub.",
    "Uşaqlar sahildə <<qumdan|CITY|common_word>> <<qala|CITY|common_word>> tikdilər.",
    "<<Car|CITY|common_word>> çəkdilər ki, bazar sabah açılacaq.",
    "<<Dağ|CITY|generic_place>> kəndlərində qış tez gəlir.",
    "<<Ucqar|CITY|generic_place>> kəndə nəhayət yol çəkilir.",
    "<<Qonşu|CITY|generic_place>> kənddən gələn qonaqlar gecikdi.",
    "<<Bağ|CITY|generic_place>> evində iki gün qaldıq.",
    "<<Yaylaq|CITY|generic_place>> mövsümü bu həftə başlayıb.",
]

# D-23d foreign names (none in the generator's foreign_names.txt); brands in the same slots
FOREIGN = [
    ("ru", "İclasa [[Yaropolk|GIVENNAME]] [[Belozyorov|SURNAME]] də qatıldı."),
    ("ru", "Müqaviləni [[Snezhana|GIVENNAME]] [[Kudryashova|SURNAME]] imzalayıb."),
    ("ru", "Tərcüməni [[Feofan|GIVENNAME]] [[Zvyagintsev|SURNAME]] edib."),
    ("ru", "Qonaqlar arasında [[Lukerya|GIVENNAME]] [[Lapshina|SURNAME]] da var idi."),
    ("tr", "Layihənin rəhbəri [[Gökberk|GIVENNAME]] [[Tekinalp|SURNAME]] təyin olunub."),
    ("tr", "Bu məktubu [[Ecrin|GIVENNAME]] [[Akgündüz|SURNAME]] göndərib."),
    ("tr", "Seminarda [[Ilgaz|GIVENNAME]] [[Kocabıyık|SURNAME]] çıxış etdi."),
    ("ka", "Yeni mühasib [[Iase|GIVENNAME]] [[Sulaberidze|SURNAME]] oldu."),
    ("ka", "Ekspert rəyini [[Bachana|GIVENNAME]] [[Jgenti|SURNAME]] yazıb."),
    ("ka", "Sərgini [[Eter|GIVENNAME]] [[Pataraia|SURNAME]] təşkil edib."),
    ("fa_ar", "Sifarişi [[Shahrzad|GIVENNAME]] [[Daneshvar|SURNAME]] qəbul etdi."),
    ("fa_ar", "Həkim [[Ghassan|GIVENNAME]] [[Qabbani|SURNAME]] xəstəni müayinə etdi."),
    ("fa_ar", "Konfransa [[Lubna|GIVENNAME]] [[Nasrallah|SURNAME]] dəvət olunub."),
    ("en_eu", "Hesabatı [[Thaddeus|GIVENNAME]] [[Fairweather|SURNAME]] hazırlayıb."),
    ("en_eu", "Müsahibəni [[Margaux|GIVENNAME]] [[Achterberg|SURNAME]] aparıb."),
    ("en_eu", "Təqdimatdan sonra [[Lorcan|GIVENNAME]] [[Hargreaves|SURNAME]] suallara cavab verdi."),
    ("en_eu", "Sənədləri [[Benedetta|GIVENNAME]] [[Lindqvistə|SURNAME]] təhvil verdik."),
    ("en_eu", "Bu barədə [[Siobhan|GIVENNAME]] [[Kowalczykdan|SURNAME]] soruşun."),
    ("ru", "Dünən [[Zinoviy|GIVENNAME]] [[Pustovoitovla|SURNAME]] görüşdük."),
    ("fa_ar", "[[Nizar|GIVENNAME]] [[Hamadaninin|SURNAME]] təklifi qəbul olundu."),
]
BRANDS = [
    "İclasa {{Lukoil|SURNAME|brand_not_person}} nümayəndəsi də qatıldı.",
    "Müqaviləni {{Gazprom|SURNAME|brand_not_person}} ilə imzalamışıq.",
    "Tərcüməni {{Rostelekom|SURNAME|brand_not_person}} sifariş edib.",
    "Qonaqlar {{Aeroflot|SURNAME|brand_not_person}} reysi ilə gəldilər.",
    "Layihəyə {{Turkcell|SURNAME|brand_not_person}} sponsorluq edir.",
    "Bu məktubu {{Vodafone|SURNAME|brand_not_person}} göndərib.",
    "Seminarda {{Skoda|SURNAME|brand_not_person}} avtomobilləri təqdim olundu.",
    "Sifarişi {{Carrefour|SURNAME|brand_not_person}} qəbul etdi.",
    "Konfransa {{Lufthansa|SURNAME|brand_not_person}} nümayəndələri dəvət olunub.",
    "Hesabatı {{Sberbank|SURNAME|brand_not_person}} dərc edib.",
]

IPV6_FRAMES = ["Firewall jurnalında bloklanan ünvan: {v}", "Gecə {v} ünvanından çoxlu uğursuz giriş cəhdi qeydə alındı.",
               "Müştərinin routerinə yeni IPv6 verildi: {v}", "Zəhmət olmasa {v} ünvanını ağ siyahıya əlavə edin.",
               "VPN sessiyası {v} üzərindən açılıb.", "Monitorinq sistemi {v} ilə bağlantının kəsildiyini bildirdi.",
               "DNS qeydində AAAA dəyəri {v} olaraq yazılıb.", "Qeyd: {v} bu gün iki dəfə bloklandı."]
MAC_FRAMES = ["Printerin fiziki ünvanı {v} kimi qeydiyyatdadır.", "Ofis Wi-Fi şəbəkəsinə {v} cihazı qoşuldu.",
              "Kamera {v} ünvanı ilə DHCP-dən IP ala bilmir.", "Anbardakı skanerin MAC-ı: {v}",
              "Şəbəkə kartı dəyişdirildi, yeni ünvan {v}.", "Bu noutbuku {v} üzrə bloklayın."]
PAIR_FRAMES = ["Noutbukun MAC ünvanı {m}, ona təyin olunan IPv6 isə {i}.", "Cihaz {m} şəbəkəyə {i} ünvanı ilə daxil olub.",
               "Qeyd: {i} — {m} (ofis-2, ikinci mərtəbə)", "DHCPv6 icarəsi: müştəri {m}, ünvan {i}, müddət bir gün.",
               "Şübhəli trafik {i} ünvanından gəlirdi; cihazın fiziki ünvanı {m} çıxdı.", "Router cədvəlində {m} üçün {i} yazılıb.",
               "{i} ünvanlı serverin şəbəkə kartı {m} idi.", "İnventar sətri: {m} / {i}"]
TK_FRAMES = ["Mobil tətbiqin access token-i {t}, inteqrasiya üçün API açarı isə {k}.",
             "Authorization: Bearer {t}\nX-Api-Key: {k}",
             ".env faylında iki sətir var: API_KEY={k} və ACCESS_TOKEN={t}",
             "Sessiya tokeni {t} bitib; xidmət açarı {k} hələ etibarlıdır.",
             "Diqqət: {k} API açarıdır, {t} isə istifadəçi tokenidir, qarışdırmayın.",
             "Loqda iki dəyər görünür: token={t}, apikey={k}",
             "Ödəniş şlüzü üçün açar {k}; OAuth girişindən sonra alınan token {t}.",
             "Qeyd: {t} (token, bir saatlıq) və {k} (açar, daimi)."]
LI_FRAMES = ["Sürücülük vəsiqəsi: {l}; şəxsiyyət vəsiqəsi: {n}.",
             "Ərizəçi şəxsiyyət vəsiqəsini ({n}) və sürücülük vəsiqəsini ({l}) təqdim etdi.",
             "Yol polisi {l} nömrəli sürücülük vəsiqəsini yoxladı, sahibin şəxsiyyət vəsiqəsi isə {n} idi.",
             "Sənədlər: ŞV {n}, SV {l}",
             "Vəsiqə nömrələri: {n} (şəxsiyyət), {l} (sürücülük).",
             "Kirayə müqaviləsində sürücünün vəsiqəsi {l}, şəxsiyyət sənədi {n} göstərilib.",
             "{n} — şəxsiyyət vəsiqəsi; {l} — sürücülük vəsiqəsi.",
             "Avtomobil icarəsi üçün {l} və {n} nömrəli sənədlər skan edildi."]
DT_FRAMES = ["Müqavilə {D} tarixində imzalanıb. Sistem qeydi: {T}, fayl yükləndi.",
             "Doğum tarixi: {D}\nSon giriş: {T}",
             "Ərizə {D} tarixində qəbul olunub; elektron reyestrdə vaxt möhürü {T}.",
             "Hesab-faktura tarixi {D}. Ödəniş {T} vaxtında keçib.",
             "[{T}] INFO: istifadəçinin profilində doğum tarixi {D} kimi yeniləndi",
             "Arayış {D} tarixində verilib, sistemə {T} radələrində daxil edilib.",
             "Görüş {D} tarixinə keçirildi. (Redaktə: {T})",
             "Sığorta {D} tarixindən qüvvədədir; sorğu {T} vaxtında göndərilib.",
             "Tarix: {D}\nQeydiyyat vaxtı: {T}",
             "{T} | sifariş yaradıldı | çatdırılma tarixi {D}",
             "Məzuniyyət əmri {D} tarixlidir; e-poçt {T} vaxtında göndərildi.",
             "Diplom {D} tarixində verilib. Skan surəti {T} yüklənib."]
DATE_ONLY = ["Sənədin tarixi: {D}.", "İclas {D} tarixində keçiriləcək.", "Doğum tarixi {D} olaraq qeyd edilib.",
             "Bu protokol {D} tarixində tərtib olunub."]
TS_ONLY = ["[{T}] WARN disk dolmaq üzrədir", "{T} giriş uğursuz oldu (istifadəçi: admin)", "Son sinxronizasiya: {T}",
           "Kamera yazısı {T} anından başlayır.", "Ehtiyat nüsxə {T} vaxtında tamamlandı.",
           "Bilet {T} reysinə bron edilib."]


# Generated values that the leakage check found in Run B's corpus (runb-az-v1,
# D-26 SHA-256s): re-drawn, so no probe value occurs in Run B's training text.
# Hand-written strings found there were rewritten instead (worklog
# p3-probes-runb.md). Add to this set when a later corpus finds more.
SEEN_IN_RUNB = {"22 avqust 2013"}

# ---------------------------------------------------------------------------
# Families
# ---------------------------------------------------------------------------

class RunBBuilder(BP.Builder):
    def fresh(self, maker, *a):
        """A value not in the forbidden set; for a timestamp, neither its date nor its time."""
        for _ in range(50):
            v = maker(self.r, *a)
            if v not in self.forbidden and not any(p in self.forbidden for p in re.split(r"[ T,\[\]]+", v) if p):
                return v
        raise RuntimeError(getattr(maker, "__name__", "maker"))

    def fresh_pair(self, maker):
        for _ in range(50):
            a, c = maker(self.r)
            if a not in self.forbidden and c not in self.forbidden:
                return a, c
        raise RuntimeError(maker.__name__)


def build(b: RunBBuilder):
    r = b.r
    # noisy suffixes: 24 names/cities, 12 nouns
    for i, (noise, s) in enumerate(NOISY):
        text, ents, hns, ctl = marked(s)
        for e in ents:
            e["noise"] = noise
        b.add("noisy_suffixes", i, "name", (text, ents, hns, ctl))
    for i, (noise, s) in enumerate(NOISY_NOUNS):
        text, ents, hns, ctl = marked(s)
        for c in ctl:
            c["noise"] = noise
        b.add("noisy_suffixes", 100 + i, "noun", (text, ents, hns, ctl))

    # token/key: 8 same-body pairs, 4 JWT + sk- pairs, 4 tokens alone, 8 look-alikes
    for i, t in enumerate(TK_FRAMES):
        tok, key = b.fresh_pair(token_key_same_body)
        b.add("contrast_token_key", i, "same_body",
              fill(t, t=("g", tok, "ACCESS_TOKEN"), k=("g", key, "API_KEY")), same_body=True)
    for i in range(4):
        t = TK_FRAMES[(i * 3 + 1) % len(TK_FRAMES)]
        b.add("contrast_token_key", 10 + i, "jwt_sk",
              fill(t, t=("g", b.fresh(jwt), "ACCESS_TOKEN"), k=("g", b.fresh(sk_key), "API_KEY")), same_body=False)
    for i, t in enumerate(["Authorization: Bearer {t}", "Yeni sessiya tokeni: {t}",
                           "Girişdən sonra alınan token {t} bir saat etibarlıdır.", "access_token={t}"]):
        v = b.fresh(lambda rr: rr.choice(TOKEN_PREFIX) + _rs(rr, ALNUM, rr.randint(28, 44))) if i % 2 \
            else b.fresh(lambda rr: _rs(rr, HEX, 40))
        b.add("contrast_token_key", 20 + i, "token", fill(t, t=("g", v, "ACCESS_TOKEN")))
    for i, (mk, lab, kind, t) in enumerate(SECRET_DECOYS):
        b.add("contrast_token_key", 30 + i, "decoy", fill(t, x=("h", b.fresh(mk), lab, kind)))

    # IPv6/MAC: 16 IPv6, 12 MAC, 10 side by side, 22 look-alikes (70 items)
    for i in range(16):
        form = IPV6_FORMS[i % len(IPV6_FORMS)] if i < 14 else "mid"
        b.add("contrast_ipv6_mac", i, "ipv6",
              fill(IPV6_FRAMES[i % len(IPV6_FRAMES)], v=("g", b.fresh(ipv6, form), "IPV6_ADDRESS", {"form": form})))
    for i in range(12):
        sep = MAC_SEPS[i % 3]
        b.add("contrast_ipv6_mac", 20 + i, "mac",
              fill(MAC_FRAMES[i % len(MAC_FRAMES)], v=("g", b.fresh(mac, sep), "MAC_ADDRESS", {"sep": sep})))
    for i in range(10):
        form, sep = ["mid", "end", "prefix_one", "link_local", "mapped"][i % 5], MAC_SEPS[i % 3]
        b.add("contrast_ipv6_mac", 40 + i, "side_by_side",
              fill(PAIR_FRAMES[i % len(PAIR_FRAMES)], i=("g", b.fresh(ipv6, form), "IPV6_ADDRESS", {"form": form}),
                   m=("g", b.fresh(mac, sep), "MAC_ADDRESS", {"sep": sep})))
    for i in range(22):
        mk, lab, kind = NET_DECOYS[i % len(NET_DECOYS)]
        b.add("contrast_ipv6_mac", 60 + i, "decoy", fill(NET_DECOY_FRAMES[kind], x=("h", b.fresh(mk), lab, kind)))

    # licence/ID: 8 same-prefix pairs, 4 other-prefix licences, 4 ID cards alone, 10 look-alikes
    for i, t in enumerate(LI_FRAMES):
        lic, idc = b.fresh_pair(lic_id_same_prefix)
        b.add("contrast_licence_id", i, "same_prefix",
              fill(t, l=("g", lic, "AZ_DRIVER_LICENSE_NUMBER"), n=("g", idc, "AZ_ID_CARD_NUMBER")))
    for i, t in enumerate(["Sürücülük vəsiqəsinin nömrəsi {l}.", "SV: {l}", "Vəsiqə {l} 2031-ci ilədək etibarlıdır.",
                           "Sürücü {l} nömrəli vəsiqə ilə qeydiyyatdan keçib."]):
        b.add("contrast_licence_id", 10 + i, "licence_other_prefix",
              fill(t, l=("g", b.fresh(licence_other), "AZ_DRIVER_LICENSE_NUMBER")))
    for i, t in enumerate(["Vəsiqə: {n}", "Şəxsiyyət vəsiqəsinin seriya və nömrəsi {n}.", "Sənəd nömrəsi {n} yoxlanıldı.",
                           "ŞV {n} təqdim edildi."]):
        b.add("contrast_licence_id", 20 + i, "id_card",
              fill(t, n=("g", b.fresh(lambda rr: rr.choice(["AA", "AB"]) + _rs(rr, DIG, 7)), "AZ_ID_CARD_NUMBER")))
    for i in range(10):
        mk, lab, kind, t = PLATE_DECOYS[i % len(PLATE_DECOYS)]
        b.add("contrast_licence_id", 30 + i, "decoy", fill(t, x=("h", b.fresh(mk), lab, kind)))

    # homograph pairs: 16 documents, one name use and one word use each
    for i, s in enumerate(HOMOGRAPH_PAIRS):
        b.add("homograph_pairs", i, "pair", marked(s))

    # dates vs timestamps: 12 both, 4 dates alone, 6 timestamps alone
    for i, t in enumerate(DT_FRAMES):
        form = DATE_FORMS[i % len(DATE_FORMS)]
        b.add("date_vs_timestamp", i, "both",
              fill(t, D=("g", b.fresh(date, form), "DATE", {"form": form}),
                   T=("h", b.fresh(timestamp, i), "DATE", "timestamp")))
    for i, t in enumerate(DATE_ONLY):
        form = DATE_FORMS[(i + 2) % len(DATE_FORMS)]
        b.add("date_vs_timestamp", 20 + i, "date", fill(t, D=("g", b.fresh(date, form), "DATE", {"form": form})))
    for i, t in enumerate(TS_ONLY):
        b.add("date_vs_timestamp", 30 + i, "timestamp", fill(t, T=("h", b.fresh(timestamp, i + 1), "DATE", "timestamp")))

    # villages: 26 gold, 8 controls (9 spans)
    for i, s in enumerate(VILLAGES):
        b.add("villages", i, "village", marked(s))
    for i, s in enumerate(VILLAGE_CONTROLS):
        b.add("villages", 100 + i, "control", marked(s))

    # foreign names: 20 persons (40 gold), 10 brands
    for i, (origin, s) in enumerate(FOREIGN):
        text, ents, hns, ctl = marked(s)
        for e in ents:
            e["origin"] = origin
        b.add("foreign_names", i, "person", (text, ents, hns, ctl))
    for i, s in enumerate(BRANDS):
        b.add("foreign_names", i, "brand", marked(s))


def stems(rec):
    """Bare forms of hand-written names, for the benchmark-value check."""
    return [rec["text"][e["start"]:e["end"]] for e in rec["entities"]]


def check_runb(out: dict, forbidden: set, validators: str | None) -> list[str]:
    problems = BP.check(out, validators)
    for fam, rows in out.items():
        for rec in rows:
            for v in stems(rec) + [rec["text"][h["start"]:h["end"]] for h in rec.get("hard_negatives", [])]:
                if v in forbidden:
                    problems.append(f"{rec['id']}: benchmark value {v!r}")
                if v in SEEN_IN_RUNB:
                    problems.append(f"{rec['id']}: value seen in Run B's corpus {v!r}")
    return problems


def run(seed: int, validators: str | None = None) -> tuple[dict, list[str]]:
    forbidden = BP.load_forbidden()
    b = RunBBuilder(seed, forbidden | SEEN_IN_RUNB)
    build(b)
    return b.out, check_runb(b.out, forbidden, validators)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=34)
    ap.add_argument("--validators", default=None, help="directory containing piigen/ (checking only)")
    ap.add_argument("--out", type=Path, default=HERE)
    args = ap.parse_args(argv)
    out, problems = run(args.seed, args.validators)
    for fam in FAMILIES:
        (args.out / f"{fam}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out[fam]),
                                               encoding="utf-8")
    for fam in FAMILIES:
        rows = out[fam]
        print(f"{fam:22s} {len(rows):3d} docs  {sum(len(x['entities']) for x in rows):3d} gold  "
              f"{sum(len(x.get('hard_negatives', [])) for x in rows):3d} look-alikes  "
              f"{sum(len(x.get('controls', [])) for x in rows):3d} controls")
    print("problems:", len(problems))
    for p in problems[:20]:
        print("  ", p)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
