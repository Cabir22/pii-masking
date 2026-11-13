"""Build the FORMATS red-team benchmark for v4.2: 200 core cases (8 groups x 5 families x 5).

The red-team area. Every value is invented; labels
follow the labelling decisions, in particular D-17/D-51f (stamps), D-66e (phone vs VOEN) and D-72 (format
conventions: URLs, disguised and spelled-out values, separators, encodings, invisible chars,
IP:port, chat exports). Writes, next to this file:

  formats_az_v42_200.jsonl   the cases: {"id","kind","text","expected","probe"} only
  manifest.jsonl             per case: group, family, reference, factor, values, code points,
                             input representation, policy dependencies, polarity, chunk placement
  spans.jsonl                exact character spans of every expected occurrence
  validation.md              the 12 checks of the brief and their results

  python redteam/formats_v42/build_cases.py
Deterministic: same code, same files. Exits 1 if any validation check fails.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "model"))

LABELS = {"GIVENNAME", "SURNAME", "CITY", "STREET", "BUILDINGNUM", "ZIPCODE", "TELEPHONENUM",
          "EMAIL", "DATE", "TIME", "AGE", "AZ_FIN", "AZ_VOEN", "AZ_ID_CARD_NUMBER",
          "AZ_PASSPORT_NUMBER", "AZ_DRIVER_LICENSE_NUMBER", "PAYMENT_CARD_NUMBER",
          "CARD_SECURITY_CODE", "IBAN", "ICCID", "IPV4_ADDRESS", "IPV6_ADDRESS", "MAC_ADDRESS",
          "URL", "API_KEY", "ACCESS_TOKEN", "PRIVATE_KEY"}
DUMMIES = {"A12B34", "P12345678", "4111111111111111", "4242424242424242", "5555555555554444",
           "12:34:56", "1.2.3.4"}

# --- the invented values (checked against piigen.validate below where a clean form exists) ---
PH1 = "+994553186427"          # compact international mobile
PH1G = "+994 55 318 64 27"     # the same, grouped
PH2 = "+994 70 528 31 46"
PH3 = "+994513946208"
PH4 = "+994 50 739 21 64"
PH5 = "+994 77 604 18 52"
EM1 = "rauf.aliyev@kamranservis.az"
EM2 = "s.qasimova@inbox.az"
EM3 = "orxan.mustafayev@poct.az"
EM4 = "leyla.rzayeva@poct.az"
FIN1 = "7KD3M2X"
FIN2 = "5RT8VQ2"
VOEN = "1702938461"
IDC = "AA7364519"
PASS = "C47195362"
CARD = "4518190937865794"
CARDG = "4518 1909 3786 5794"
IBAN = "AZ29JHZF31948757491186252760"
IBANG = "AZ29 JHZF 3194 8757 4911 8625 2760"
IP4 = "185.47.112.36"
IP6 = "2001:db8:4f2a::17c"
MAC = "3C:52:A1:7F:0E:94"
TOKEN_URL = "https://portal.kamran-servis.az/reset?token=Qk7vX2mN9pLr4TzA8sWy3HcB"

CLEAN = [("TELEPHONENUM", PH1), ("TELEPHONENUM", PH1G), ("TELEPHONENUM", PH2), ("TELEPHONENUM", PH3),
         ("TELEPHONENUM", PH4), ("TELEPHONENUM", PH5), ("EMAIL", EM1), ("EMAIL", EM2), ("EMAIL", EM3),
         ("EMAIL", EM4), ("AZ_FIN", FIN1), ("AZ_FIN", FIN2), ("AZ_VOEN", VOEN),
         ("AZ_ID_CARD_NUMBER", IDC), ("AZ_PASSPORT_NUMBER", PASS), ("PAYMENT_CARD_NUMBER", CARD),
         ("PAYMENT_CARD_NUMBER", CARDG), ("IBAN", IBAN), ("IPV4_ADDRESS", IP4),
         ("IPV6_ADDRESS", IP6), ("MAC_ADDRESS", MAC), ("URL", TOKEN_URL)]

FILLER = [
    "Hesabat dövründə şöbənin əsas fəaliyyəti daxili prosedurların sadələşdirilməsinə yönəldilib.",
    "İş qrupu mövcud təlimatları nəzərdən keçirib və bir neçə dəyişiklik təklif edib.",
    "Təkliflər rəhbərliyə təqdim olunub və növbəti iclasda müzakirə ediləcək.",
    "Bundan əlavə, sənəd dövriyyəsinin elektron formaya keçirilməsi davam etdirilir.",
    "Əməkdaşlar üçün təşkil edilən təlimlərdə yeni sistemin imkanları izah olunub.",
    "Texniki dəstək xidməti sorğuların cavablandırılma müddətini xeyli qısaldıb.",
    "Anbar qalıqlarının yoxlanılması planlaşdırılmış qaydada başa çatdırılıb.",
    "Gələn rübdə xərclərin optimallaşdırılması üzrə əlavə tədbirlər nəzərdə tutulur.",
]


def filler(n: int, start: int = 0) -> str:
    return " ".join(FILLER[(start + i) % len(FILLER)] for i in range(n))


CASES: list[dict] = []
META: list[dict] = []
GROUPS = {1: "structured", 2: "logs", 3: "spacing", 4: "hidden_chars", 5: "disguised",
          6: "long_mixed", 7: "documents", 8: "encodings"}


def add(group: int, family: int, kind: str, text: str, expected: list[tuple[str, str]], probe: str,
        factor: str, ref: str | None = None, policy: tuple = (), representation: str = "raw text",
        values: tuple = (), chunk: str = "") -> str:
    cid = f"F-{len(CASES) + 1:03d}"
    CASES.append({"id": cid, "kind": kind, "text": text,
                  "expected": [{"value": v, "label": l} for v, l in expected], "probe": probe})
    cps = sorted({f"U+{ord(c):04X} {unicodedata.name(c, '?')}" for c in text
                  if ord(c) > 0x7E and not c.isalpha() or unicodedata.category(c) in ("Cf", "Mn", "Zs")
                  and c != " "})
    pol = "negative-only" if not expected else "positive"
    META.append({"id": cid, "group": f"G{group} {GROUPS[group]}", "family": f"F{family:02d} {kind}",
                 "reference": ref or cid, "is_reference": ref is None, "factor": factor,
                 "values": list(values) or sorted({v for v, _ in expected}),
                 "code_points": cps, "input": representation, "policy": list(policy),
                 "polarity": pol, "chunk": chunk})
    return cid


# ============================== G1 structured data ==============================
r = add(1, 1, "json_field_count", f"Müştərinin telefon nömrəsi: {PH1}.", [(PH1, "TELEPHONENUM")],
        "reference: the phone in a plain sentence", "plain sentence")
add(1, 1, "json_field_count", f'{{"telefon": "{PH1}"}}', [(PH1, "TELEPHONENUM")],
    f"JSON with one field (vs {r})", "1 field", r)
add(1, 1, "json_field_count", f'{{"sifaris": "SIF-48217", "mebleg": "149.90", "telefon": "{PH1}"}}',
    [(PH1, "TELEPHONENUM")], f"3 fields, phone last (vs {r}); order code and price are harmless", "3 fields, last", r)
many = ['"sifaris": "SIF-48217"', '"mebleg": "149.90"', '"valyuta": "AZN"', '"status": "tesdiqlendi"',
        '"kanal": "mobil"', '"versiya": "4.2.1"', '"qeyd": "zeng edin"']
add(1, 1, "json_field_count", "{" + ", ".join(many[:4] + [f'"telefon": "{PH1}"'] + many[4:]) + "}",
    [(PH1, "TELEPHONENUM")], f"8 fields, phone in the middle (vs {r})", "8 fields, middle", r)
add(1, 1, "json_field_count", "{" + ", ".join([f'"telefon": "{PH1}"'] + many) + "}",
    [(PH1, "TELEPHONENUM")], f"8 fields, phone first (vs the middle case): position only", "8 fields, first", r)

r = add(1, 2, "json_nesting_layout", f'{{"email":"{EM1}","status":"aktiv"}}', [(EM1, "EMAIL")],
        "reference: flat minified JSON", "flat minified")
add(1, 2, "json_nesting_layout", f'{{"musteri":{{"elaqe":{{"email":"{EM1}"}}}},"status":"aktiv"}}',
    [(EM1, "EMAIL")], f"nested 3 levels, minified (vs {r})", "nested, minified", r)
add(1, 2, "json_nesting_layout",
    f'{{\n  "musteri": {{\n    "elaqe": {{\n      "email": "{EM1}"\n    }}\n  }},\n  "status": "aktiv"\n}}',
    [(EM1, "EMAIL")], "the same nesting pretty-printed: layout only", "nested, pretty", r)
add(1, 2, "json_nesting_layout",
    f'{{"musteriler":[{{"id":1,"email":"{EM1}"}},{{"id":2,"email":"{EM2}"}}]}}',
    [(EM1, "EMAIL"), (EM2, "EMAIL")], f"array of objects, two e-mails (vs {r})", "array of objects", r)
add(1, 2, "json_nesting_layout", f'["aktiv",42,"{EM1}",null,"v2",true]', [(EM1, "EMAIL")],
    f"mixed-type array (vs {r})", "mixed array", r)

row = f"Səbinə,Qasımova,{FIN2}"
exp_row = [("Səbinə", "GIVENNAME"), ("Qasımova", "SURNAME"), (FIN2, "AZ_FIN")]
r = add(1, 3, "csv_tsv", f"ad,soyad,fin\n{row}", exp_row, "reference: CSV with a header", "comma, header")
add(1, 3, "csv_tsv", row, exp_row, f"the same row without a header (vs {r})", "no header", r)
add(1, 3, "csv_tsv", f"ad;soyad;fin\n{row.replace(',', ';')}", exp_row,
    f"semicolon delimiter (vs {r})", "semicolon", r)
add(1, 3, "csv_tsv", f"ad\tsoyad\tfin\n{row.replace(',', chr(9))}", exp_row, f"tab delimiter (vs {r})", "tab", r)
add(1, 3, "csv_tsv", f'"ad","soyad","fin","qeyd"\n"Səbinə","Qasımova","{FIN2}","zəng, sonra\nyenidən yoxla"',
    exp_row, f"quoted fields, a delimiter and a line break inside the last field (vs {r})", "quoted", r)

r = add(1, 4, "config_formats", f"Bildirişlər {EM2} ünvanına göndərilir.", [(EM2, "EMAIL")],
        "reference: the e-mail in a sentence", "plain sentence")
add(1, 4, "config_formats", f"# bildiriş ayarları\nnotify_email = {EM2}\nretry = 3", [(EM2, "EMAIL")],
    f"key = value with a comment line (vs {r})", "key=value", r)
add(1, 4, "config_formats", f"bildiris:\n  email: {EM2}\n  versiya: 4.2.1", [(EM2, "EMAIL")],
    f"YAML scalar (vs {r})", "YAML scalar", r)
add(1, 4, "config_formats", "retry = 3\ntimeout_ms = 4500\nsifaris_prefiksi = SIF-2026\nversiya = 4.2.1\nport = 8443", [],
    "negative-only config: numbers, a version, a code prefix, a port (replaces the YAML list case)",
    "negative config", None)
add(1, 4, "config_formats", f'<elaqe email="{EM2}" versiya="4.2.1"/>', [(EM2, "EMAIL")],
    f"XML attribute (vs {r})", "XML attribute", r)

r = add(1, 5, "html_md_sql", f"Ödəniş {IBAN} hesabına köçürülsün.", [(IBAN, "IBAN")],
        "reference: the IBAN in a sentence", "plain sentence")
add(1, 5, "html_md_sql", f"<tr><td>{IBAN}</td><td>149,90 AZN</td></tr>", [(IBAN, "IBAN")],
    f"HTML text node beside a price (vs {r})", "HTML text node", r)
add(1, 5, "html_md_sql", f'<input type="text" name="iban" value="{IBAN}" maxlength="34">', [(IBAN, "IBAN")],
    f"HTML attribute value (vs {r})", "HTML attribute", r)
add(1, 5, "html_md_sql", f"| Hesab | Məbləğ | Versiya |\n|---|---|---|\n| {IBAN} | 149,90 AZN | 4.2.1 |",
    [(IBAN, "IBAN")], f"Markdown table cell (vs {r})", "Markdown cell", r)
add(1, 5, "html_md_sql", f"INSERT INTO odenisler (iban, mebleg, versiya) VALUES ('{IBAN}', 149.90, '4.2.1');",
    [(IBAN, "IBAN")], f"SQL INSERT value (vs {r})", "SQL INSERT", r)

# ============================== G2 logs ==============================
r = add(2, 6, "web_server_log", f"Sorğu {IP4} ünvanından daxil olub.", [(IP4, "IPV4_ADDRESS")],
        "reference: the IPv4 in a sentence", "plain sentence")
add(2, 6, "web_server_log",
    f'{IP4} - - [23/Oct/2026:12:05:11 +0400] "GET /hesab HTTP/1.1" 200 5123 "-" "Mozilla/5.0"',
    [(IP4, "IPV4_ADDRESS")], f"combined access log, IP first; the stamp is not labelled (D-17) (vs {r})",
    "access log, first field", r, policy=("D-17",))
add(2, 6, "web_server_log",
    f'91.198.36.14 - - [23/Oct/2026:12:05:11 +0400] "GET /hesab HTTP/1.1" 200 5123 "-" "Mozilla/5.0" xff={IP4}',
    [("91.198.36.14", "IPV4_ADDRESS"), (IP4, "IPV4_ADDRESS")], "the client IP at the end as xff=, a proxy IP first",
    "access log, last field", r, policy=("D-17",))
add(2, 6, "web_server_log", f"2026-10-23 12:05:11 WARN conn client={IP4}:51432 closed",
    [(IP4, "IPV4_ADDRESS")], "IP:port, the address only (D-72g)", "IP with port", r, policy=("D-17", "D-72g"))
add(2, 6, "web_server_log", "2026-10-23 12:05:11 INFO worker=3 queue=17 latency_ms=482 build=4.2.1 port=8443", [],
    "negative-only log line: worker, queue, latency, build and port numbers", "negative log", None, policy=("D-17",))

r = add(2, 7, "app_json_log", f"İstifadəçi {EM3} sistemə daxil oldu.", [(EM3, "EMAIL")],
        "reference: the e-mail in a sentence", "plain sentence")
add(2, 7, "app_json_log", f"2026-10-23 12:05:11 INFO event=login user={EM3} result=ok", [(EM3, "EMAIL")],
    f"key=value log line (vs {r})", "key=value log", r, policy=("D-17",))
add(2, 7, "app_json_log",
    f'{{"ts":"2026-10-23T12:05:11Z","level":"INFO","user":"{EM3}","event":"login"}}', [(EM3, "EMAIL")],
    f"JSON log line (vs {r})", "JSON log", r, policy=("D-17",))
add(2, 7, "app_json_log",
    f'{{"level":"INFO","payload":{{"actor":{{"email":"{EM3}"}},"action":"login"}}}}', [(EM3, "EMAIL")],
    "JSON log with a nested payload", "nested payload", r)
add(2, 7, "app_json_log", f'{{"level":"INFO","payload":"{{\\"email\\":\\"{EM3}\\"}}"}}', [(EM3, "EMAIL")],
    "the payload as an escaped JSON string: the model sees backslash-quote", "escaped payload", r,
    representation="literal backslash-quote characters in the text")

r = add(2, 8, "syslog_audit", f"Şəxsiyyət vəsiqəsi {IDC} yoxlanıldı.", [(IDC, "AZ_ID_CARD_NUMBER")],
        "reference: the ID card in a sentence", "plain sentence")
add(2, 8, "syslog_audit", f"Oct 23 12:05:11 srv-02 kyc[2817]: vesiqe={IDC} yoxlama=ugurlu",
    [(IDC, "AZ_ID_CARD_NUMBER")], f"syslog line with a process prefix (vs {r})", "syslog", r, policy=("D-17",))
add(2, 8, "syslog_audit", f"[kyc][srv-02][pid:2817] vəsiqə {IDC} yoxlandı", [(IDC, "AZ_ID_CARD_NUMBER")],
    f"bracketed metadata prefix (vs {r})", "bracketed metadata", r)
add(2, 8, "syslog_audit", f"AUDIT actor=operator17 action=view target.id_card={IDC} status=OK",
    [(IDC, "AZ_ID_CARD_NUMBER")], "audit line: user name operator17 is not labelled (D-72i)", "audit fields", r,
    policy=("D-72i",))
add(2, 8, "syslog_audit",
    f"AUDIT|operator17|view|{IDC}|OK\nAUDIT|operator17|print|{IDC}|OK",
    [(IDC, "AZ_ID_CARD_NUMBER"), (IDC, "AZ_ID_CARD_NUMBER")], "pipe-delimited, the same ID in two events",
    "repeated, pipes", r, policy=("D-72i",))

r = add(2, 9, "stack_trace", f"Pasport nömrəsi {PASS} qəbul edilmədi.", [(PASS, "AZ_PASSPORT_NUMBER")],
        "reference: the passport in a sentence", "plain sentence")
add(2, 9, "stack_trace", f"ValueError: invalid passport {PASS} for applicant", [(PASS, "AZ_PASSPORT_NUMBER")],
    f"exception message in English (vs {r})", "exception message", r)
add(2, 9, "stack_trace",
    f'Traceback (most recent call last):\n  File "kyc.py", line 88, in check\n    verify(passport="{PASS}", retries=3)',
    [(PASS, "AZ_PASSPORT_NUMBER")], "parameter in a code line of a traceback", "parameter dump", r)
add(2, 9, "stack_trace", f"KycError: args=('{PASS}', 'v4.2.1')", [(PASS, "AZ_PASSPORT_NUMBER")],
    "quoted tuple argument beside a version string", "quoted argument", r)
add(2, 9, "stack_trace", f"ERROR yoxlama uğursuz:\n    sənəd növü: pasport\n    nömrə:\n        {PASS}",
    [(PASS, "AZ_PASSPORT_NUMBER")], "the value alone on an indented continuation line", "indented continuation", r)

r = add(2, 10, "ipv6_mac", f"Serverin IPv6 ünvanı {IP6} olaraq təyin edilib.", [(IP6, "IPV6_ADDRESS")],
        "reference: compressed IPv6 in a sentence", "plain sentence")
add(2, 10, "ipv6_mac", f"2026-10-23 12:05:11 INFO bind addr=[{IP6}] ok", [(IP6, "IPV6_ADDRESS")],
    "IPv6 in brackets in a log line; brackets outside (D-72g)", "brackets", r, policy=("D-17", "D-72g"))
add(2, 10, "ipv6_mac", f"2026-10-23 12:05:11 INFO listen [{IP6}]:8443 ok", [(IP6, "IPV6_ADDRESS")],
    "bracketed IPv6 with a port: the address only (D-72g)", "brackets + port", r, policy=("D-17", "D-72g"))
r2 = add(2, 10, "ipv6_mac", f"Cihazın MAC ünvanı {MAC} kimi qeydə alınıb.", [(MAC, "MAC_ADDRESS")],
         "reference: MAC with colons in a sentence", "MAC plain sentence")
add(2, 10, "ipv6_mac", f"dev=eth0 mac={MAC.replace(':', '-')} state=up mtu=1500",
    [(MAC.replace(":", "-"), "MAC_ADDRESS")], f"MAC with dashes in a key=value line (vs {r2})",
    "MAC dashes, key=value", r2)

# ============================== G3 spacing and line breaks ==============================
r = add(3, 11, "digit_grouping", f"Əlaqə nömrəsi: {PH2}", [(PH2, "TELEPHONENUM")],
        "reference: spaces between groups", "spaces")
for sep, name in ((".", "dots"), ("-", "hyphens")):
    v = PH2.replace(" ", sep)
    add(3, 11, "digit_grouping", f"Əlaqə nömrəsi: {v}", [(v, "TELEPHONENUM")], f"groups joined by {name} (vs {r})",
        name, r, policy=("D-72d",))
v = PH2.replace(" ", "  ")
add(3, 11, "digit_grouping", f"Əlaqə nömrəsi: {v}", [(v, "TELEPHONENUM")], f"double spaces (vs {r})",
    "double spaces", r, policy=("D-72d",))
v = "+994 (70) 528-31-46"
add(3, 11, "digit_grouping", f"Əlaqə nömrəsi: {v}", [(v, "TELEPHONENUM")], f"brackets and hyphens (vs {r})",
    "brackets + hyphens", r, policy=("D-72d",))

r = add(3, 12, "line_breaks", f"Kart nömrəsi: {CARDG}", [(CARDG, "PAYMENT_CARD_NUMBER")],
        "reference: grouped card on one line", "one line")
for v, f in ((CARDG.replace("1909 ", "1909\n"), "LF after the 2nd group"),
             (CARDG.replace("4518 ", "4518\n"), "LF after the 1st group"),
             (CARDG.replace("1909 ", "1909\r\n"), "CRLF after the 2nd group"),
             ("4518 19\n09 3786 5794", "LF inside a group")):
    add(3, 12, "line_breaks", f"Kart nömrəsi: {v}", [(v, "PAYMENT_CARD_NUMBER")], f"{f} (vs {r})", f, r,
        policy=("D-72d",))

r = add(3, 13, "whitespace_types", f"IBAN: {IBANG}", [(IBANG, "IBAN")], "reference: ordinary spaces", "spaces")
for ch, f in (("\t", "tabs"), ("\u00a0", "non-breaking spaces U+00A0"), ("\u202f", "narrow NBSP U+202F"),
              ):
    v = IBANG.replace(" ", ch)
    add(3, 13, "whitespace_types", f"IBAN: {v}", [(v, "IBAN")], f"{f} between groups (vs {r})", f, r,
        policy=("D-72d",))

add(3, 13, "whitespace_types", "Sifariş kodu: SIF 2026 0048 1752 3301 7720 (IBAN deyil)", [],
    "negative-only: a long spaced order code shaped like a grouped IBAN or card", "negative spaced code", None)
r = add(3, 14, "attached_labels", f"Telefon: {PH3}", [(PH3, "TELEPHONENUM")],
        "reference: label, colon, space", "label: value")
for t, f in ((f"Telefon:{PH3}", "no space after the colon"), (f"Telefon{PH3}", "label glued, no colon"),
             (f"тел.{PH3}", "Russian label glued"), (f"TEL:{PH3}", "ASCII upper-case label, no space")):
    add(3, 14, "attached_labels", t, [(PH3, "TELEPHONENUM")], f"{f} (vs {r})", f, r, policy=("D-66e",))

r = add(3, 15, "punct_adjacency", f"FİN kodu {FIN1} olaraq göstərilib.", [(FIN1, "AZ_FIN")],
        "reference: FIN in a sentence", "plain sentence")
for t, f in ((f"Ərizəçi (FİN: {FIN1}) müraciət edib.", "inside parentheses"),
             (f"FİN kodu «{FIN1}» kimi yazılıb.", "inside guillemets"),
             (f"FİN kodu [{FIN1}] kimi yazılıb.", "inside square brackets")):
    add(3, 15, "punct_adjacency", t, [(FIN1, "AZ_FIN")], f"{f} (vs {r})", f, r)
add(3, 15, "punct_adjacency", f"FİN:{FIN1};VÖEN:{VOEN};status:OK", [(FIN1, "AZ_FIN"), (VOEN, "AZ_VOEN")],
    "two IDs in adjacent compact fields: merging check", "adjacent fields", r)

# ============================== G4 hidden and look-alike characters ==============================
r = add(4, 16, "zero_width", f"Əlaqə: {PH4}", [(PH4, "TELEPHONENUM")], "reference: plain phone", "plain")
v = PH4.replace("50 ", "50\u200b")
add(4, 16, "zero_width", f"Əlaqə: {v}", [(v, "TELEPHONENUM")], f"U+200B replacing a space in the phone (vs {r})",
    "ZWSP in phone", r, policy=("D-72f",))
v = FIN1[:3] + "\u200b" + FIN1[3:]
add(4, 16, "zero_width", f"FİN kodu: {v}", [(v, "AZ_FIN")], "U+200B inside a FIN", "ZWSP in FIN", None,
    policy=("D-72f",))
v = EM1.replace(".", "\u200b.", 1)
add(4, 16, "zero_width", f"E-poçt: {v}", [(v, "EMAIL")], "regression: U+200B in an e-mail (handled before)",
    "ZWSP in e-mail (regression)", None, policy=("D-72f",))
v = "\u2060" + IBAN
add(4, 16, "zero_width", f"IBAN: {v}", [(v, "IBAN")], "U+2060 word joiner right before an IBAN",
    "word joiner before IBAN", None, policy=("D-72f",))

r = add(4, 17, "format_controls", f"E-poçt ünvanı: {EM2}", [(EM2, "EMAIL")], "reference: plain e-mail", "plain")
for v, f in ((EM2.replace("qasi", "qa\u00adsi"), "soft hyphen U+00AD inside the local part"),
             ("\u200e" + EM2 + "\u200e", "LRM U+200E around the e-mail"),
             (EM2.replace("@", "\u200f@"), "RLM U+200F before @"),
             ("\ufeff" + EM2, "BOM U+FEFF before the e-mail")):
    add(4, 17, "format_controls", f"E-poçt ünvanı: {v}", [(v, "EMAIL")], f"{f} (vs {r})", f, r, policy=("D-72f",))

r = add(4, 18, "lookalike_letters", "Müraciət edən: Rauf Əliyev.", [("Rauf", "GIVENNAME"), ("Əliyev", "SURNAME")],
        "reference: name in Latin letters", "Latin")
add(4, 18, "lookalike_letters", "Müraciət edən: Rauf Əliуev.", [("Rauf", "GIVENNAME"), ("Əliуev", "SURNAME")],
    "Cyrillic у U+0443 inside the surname", "Cyrillic in surname", r, policy=("D-72f",))
add(4, 18, "lookalike_letters", "Müraciət edən: Rаuf Əliyev.", [("Rаuf", "GIVENNAME"), ("Əliyev", "SURNAME")],
    "Cyrillic а U+0430 inside the given name", "Cyrillic in given name", r, policy=("D-72f",))
add(4, 18, "lookalike_letters", "Müraciət edən: Οrxan Mustafayev.", [("Οrxan", "GIVENNAME"), ("Mustafayev", "SURNAME")],
    "Greek Ο U+039F as the first letter of the given name", "Greek first letter", None, policy=("D-72f",))
v = EM3.replace("poct", "pоct")
add(4, 18, "lookalike_letters", f"E-poçt: {v}", [(v, "EMAIL")], "Cyrillic о U+043E in the e-mail domain",
    "Cyrillic in e-mail domain", None, policy=("D-72f",))

FW = str.maketrans("0123456789+", "０１２３４５６７８９＋")
AI = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
r = add(4, 19, "digit_scripts", f"Mobil nömrə: {PH1G}", [(PH1G, "TELEPHONENUM")], "reference: ASCII digits", "ASCII")
for v, f in ((PH1G.translate(FW), "full-width digits and plus"), (PH1G.translate(AI), "Arabic-Indic digits"),
             (PH1G[:-2] + "２７", "last group full-width")):
    add(4, 19, "digit_scripts", f"Mobil nömrə: {v}", [(v, "TELEPHONENUM")], f"{f} (vs {r})", f, r, policy=("D-72f",))
add(4, 19, "digit_scripts", "Sifariş № " + "4829173651".translate(FW) + " qəbul olundu.", [],
    "negative-only: a 10-digit order number in full-width digits (VÖEN-shaped)", "negative full-width order", None)

r = add(4, 20, "combining_marks", "Sənəd Nigar Hüseynovaya təqdim olunub.",
        [("Nigar", "GIVENNAME"), ("Hüseynovaya", "SURNAME")], "reference: precomposed ü (NFC)", "NFC")
nfd = unicodedata.normalize("NFD", "Hüseynovaya")
add(4, 20, "combining_marks", f"Sənəd Nigar {nfd} təqdim olunub.", [("Nigar", "GIVENNAME"), (nfd, "SURNAME")],
    "the same surname decomposed (u + U+0308): canonically equal", "NFD surname", r, policy=("D-72f",))
city = unicodedata.normalize("NFD", "Şəkidə")
add(4, 20, "combining_marks", f"Ərizəçi {city} yaşayır.", [(city, "CITY")],
    "city with Ş decomposed (S + U+0327): canonically equal", "NFD city", None, policy=("D-72f",))
v = PH1G.replace("318", "31\u03018")
add(4, 20, "combining_marks", f"Mobil nömrə: {v}", [(v, "TELEPHONENUM")],
    "a stray combining acute U+0301 inside the phone (corrupted)", "mark inside phone", None, policy=("D-72f",))
v = FIN1 + "\u0301"
add(4, 20, "combining_marks", f"FİN kodu: {FIN1}\u0301 qeydə alınıb.", [(FIN1 + "\u0301", "AZ_FIN")],
    "a combining mark right after the last FIN character", "mark after FIN", None, policy=("D-72f",))

# ============================== G5 disguised and spelled-out ==============================
r = add(5, 21, "email_at_disguise", f"Mənə {EM4} ünvanına yazın.", [(EM4, "EMAIL")],
        "reference: plain e-mail", "plain")
for v, f in ((EM4.replace("@", "[at]"), "[at]"), (EM4.replace("@", "(at)"), "(at)"),
             (EM4.replace("@", " at "), "spaced at"), (EM4.replace("@", " [at] ").replace(".az", " [dot] az"),
                                                       "spaced [at] and [dot]")):
    add(5, 21, "email_at_disguise", f"Mənə {v} ünvanına yazın.", [(v, "EMAIL")], f"{f} for @ (vs {r})", f, r,
        policy=("D-72b",))

r = add(5, 22, "email_dot_disguise", f"Ünvan: {EM1}", [(EM1, "EMAIL")], "reference: plain e-mail", "plain")
for v, f in ((EM1.replace(".", "[dot]"), "[dot]"), (EM1.replace(".", "(dot)"), "(dot)"),
             (EM1.replace(".", " dot "), "spaced dot")):
    add(5, 22, "email_dot_disguise", f"Ünvan: {v}", [(v, "EMAIL")], f"{f} for dots (vs {r})", f, r,
        policy=("D-72b",))

add(5, 22, "email_dot_disguise", "Ətraflı məlumat kamranservis[dot]az saytındadır.", [],
    "negative-only: a disguised website domain, no e-mail", "negative disguised domain", None, policy=("D-72a", "D-72b"))
r = add(5, 23, "spoken_digits", f"Nömrəm: {PH4}", [(PH4, "TELEPHONENUM")], "reference: digits", "digits")
spoken = "üstəgəl doqquz yüz doxsan dörd əlli yeddi yüz otuz doqquz iyirmi bir altmış dörd"
add(5, 23, "spoken_digits", f"Nömrəm: {spoken}", [(spoken, "TELEPHONENUM")], f"all digits as words (vs {r})",
    "words", r, policy=("D-72c",))
sp2 = "üstəgəl doqquz yüz doxsan dörd, əlli, yeddi yüz otuz doqquz, iyirmi bir, altmış dörd"
add(5, 23, "spoken_digits", f"Nömrəm: {sp2}", [(sp2, "TELEPHONENUM")], "words separated by commas",
    "words + commas", r, policy=("D-72c",))
sp3 = "üstəgəl doqquz yüz doxsan dörd\nəlli\nyeddi yüz otuz doqquz\niyirmi bir altmış dörd"
add(5, 23, "spoken_digits", f"Nömrəm:\n{sp3}", [(sp3, "TELEPHONENUM")], "words over several lines",
    "words, multiline", r, policy=("D-72c", "D-72d"))
sp4 = "+994 əlli 739 iyirmi bir 64"
add(5, 23, "spoken_digits", f"Nömrəm: {sp4}", [(sp4, "TELEPHONENUM")], "digits and words mixed",
    "mixed words + digits", r, policy=("D-72c",))

r = add(5, 24, "char_by_char_id", f"FİN: {FIN2}", [(FIN2, "AZ_FIN")], "reference: FIN as one token", "plain")
for v, f in ((" ".join(FIN2), "spaces between characters"), ("-".join(FIN2), "hyphens"), (".".join(FIN2), "dots"),
             (FIN2[:3] + "\n" + FIN2[3:], "a line break after 3 characters")):
    add(5, 24, "char_by_char_id", f"FİN: {v}", [(v, "AZ_FIN")], f"{f} (vs {r})", f, r, policy=("D-72d",))

r = add(5, 25, "mixed_obfuscation", f"Telefon: {PH5}", [(PH5, "TELEPHONENUM")], "reference: plain phone", "plain")
v = PH5.replace(" ", "\u00a0")
add(5, 25, "mixed_obfuscation", f"Telefon: {v}", [(v, "TELEPHONENUM")], "control: NBSP grouping alone",
    "NBSP alone", r, policy=("D-72d",))
v = PH5.replace(" ", ".", 2).replace(" 18", "\n18")
add(5, 25, "mixed_obfuscation", f"Telefon: {v}", [(v, "TELEPHONENUM")], "dots plus a line break (two factors)",
    "dots + LF", r, policy=("D-72d",))
v = EM4.replace(".", "\u200b.", 1).replace("@", "[at]")
add(5, 25, "mixed_obfuscation", f"E-poçt: {v}", [(v, "EMAIL")], "zero-width plus [at] (two factors; see F-016-type and F-0xx controls)",
    "ZWSP + [at]", None, policy=("D-72b", "D-72f"))
v = " ".join(FIN2).replace("T", "Т")
add(5, 25, "mixed_obfuscation", f"FİN: {v}", [(v, "AZ_FIN")], "spaced characters plus Cyrillic Т U+0422",
    "spaces + Cyrillic", None, policy=("D-72d", "D-72f"))

# ============================== G6 long and mixed documents ==============================
VLINE = f"Şirkətin VÖEN-i: {VOEN}."
r = add(6, 26, "long_position", VLINE, [(VOEN, "AZ_VOEN")], "reference: short document", "short")
add(6, 26, "long_position", VLINE + " " + filler(40), [(VOEN, "AZ_VOEN")], "long document, value at the start",
    "long, start", r)
add(6, 26, "long_position", filler(20) + " " + VLINE + " " + filler(20, 3), [(VOEN, "AZ_VOEN")],
    "long document, value in the middle", "long, middle", r)
add(6, 26, "long_position", filler(40) + " " + VLINE, [(VOEN, "AZ_VOEN")], "long document, value at the end",
    "long, end", r)
add(6, 26, "long_position", filler(20) + " Şirkətin VÖEN-i aşağıda verilib. " + filler(3, 5) + f" {VOEN}. " + filler(15),
    [(VOEN, "AZ_VOEN")], "long document, the label 3 sentences before the bare value", "long, label far", r)

# F27 chunk boundaries: measured with the product's own windowing (predict._tokenize_windows)
CHUNK_NOTES: dict[str, str] = {}


def chunk_cases() -> None:
    from transformers import AutoTokenizer
    from prepare_splits import add_punctuation_boundary
    import predict
    tok = AutoTokenizer.from_pretrained("FacebookAI/xlm-roberta-large")
    add_punctuation_boundary(tok)
    long_text = filler(120)

    def windows_of(text: str):
        enc = predict._tokenize_windows(text, tok)
        spans = []
        for offs in enc["offset_mapping"]:
            real = [o for o in offs if o[1] > o[0]]
            spans.append((real[0][0], real[-1][1]))
        return spans

    line = f"Ödəniş hesabı: {IBAN}."
    ref = add(6, 27, "chunk_boundary", filler(4) + " " + line, [(IBAN, "IBAN")],
              "reference: short document, one window", "one window", chunk="single window")
    # each placement is searched: insert the line at successive word boundaries until the IBAN
    # really sits where intended in the windows the product computes for that very text
    def place(want) -> tuple[str, str]:
        for cut in [m.end() for m in re.finditer(r" ", long_text)]:
            text = long_text[:cut] + line + " " + long_text[cut:]
            s0 = text.index(IBAN)
            e0 = s0 + len(IBAN)
            ww = windows_of(text)
            if want(ww, s0, e0):
                inside = [i for i, (x, y) in enumerate(ww) if x <= s0 and e0 <= y]
                cutby = [i for i, (x, y) in enumerate(ww) if x < e0 and s0 < y and not (x <= s0 and e0 <= y)]
                return text, f"IBAN chars {s0}-{e0}; fully inside windows {inside}; cut by windows {cutby}; windows {ww}"
        raise SystemExit("no placement found")

    for name, want in (
            ("cut by the end of window 0 (whole only in window 1)",
             lambda ww, s0, e0: ww[0][0] <= s0 < ww[0][1] < e0),
            ("in the overlap, near the start of window 1 (whole in windows 0 and 1)",
             lambda ww, s0, e0: ww[1][0] <= s0 and s0 - ww[1][0] < 60 and e0 <= ww[0][1]),
            ("cut by the end of window 1 (whole only in window 2)",
             lambda ww, s0, e0: len(ww) > 2 and ww[1][0] <= s0 < ww[1][1] < e0)):
        text, note = place(want)
        cid = add(6, 27, "chunk_boundary", text, [(IBAN, "IBAN")], f"{name} (vs {ref})", name, ref, chunk=note)
        CHUNK_NOTES[cid] = note
    text = long_text + " " + line
    ww = windows_of(text)
    cid = add(6, 27, "chunk_boundary", text, [(IBAN, "IBAN")], f"at the very end of a long document (vs {ref})",
              "end of last window", ref, chunk=f"windows {ww}")


chunk_cases()

names = [("Rauf", "Əliyev"), ("Səbinə", "Qasımova"), ("Orxan", "Mustafayev"), ("Leyla", "Rzayeva"),
         ("Kamran", "Həsənov"), ("Günel", "Abbasova"), ("Elnur", "Quliyev"), ("Aytən", "Məmmədova")]
fins = ["7KD3M2X", "5RT8VQ2", "2HN6WK9", "9PL4ZT3", "4XC7RB8", "6MV2QJ5", "3WZ9KD4", "8TB5NH7"]


def rows(n: int, phone: bool = True) -> tuple[str, list]:
    out, exp = ["Ad | Soyad | FİN | Telefon" if phone else "Ad | Soyad | FİN"], []
    for i in range(n):
        g, s = names[i]
        ph = f"+99455{3186420 + i * 7:07d}"
        cells = [g, s, fins[i]] + ([ph] if phone else [])
        out.append(" | ".join(cells))
        exp += [(g, "GIVENNAME"), (s, "SURNAME"), (fins[i], "AZ_FIN")] + ([(ph, "TELEPHONENUM")] if phone else [])
    return "\n".join(out), exp


t, e = rows(1)
r = add(6, 28, "dense_table", t, e, "reference: a table with one row", "1 row")
for n in (3, 8):
    t, e = rows(n)
    add(6, 28, "dense_table", t, e, f"{n} rows (vs {r})", f"{n} rows", r)
add(6, 28, "dense_table", "Məhsul | Kod | Say | Qiymət\nÇay | MHS-88412 | 3 | 4,50 AZN\nQəhvə | MHS-88413 | 1 | 12,90 AZN\n"
    "Şəkər | MHS-88414 | 2 | 1,80 AZN\nSu | MHS-88415 | 12 | 0,60 AZN", [],
    "negative-only product table: codes, counts, prices", "negative product table", None)
add(6, 28, "dense_table", f"Rauf Əliyev{PH1} {FIN1}{VOEN}",
    [("Rauf", "GIVENNAME"), ("Əliyev", "SURNAME"), (PH1, "TELEPHONENUM"), (FIN1, "AZ_FIN"), (VOEN, "AZ_VOEN")],
    "values glued with no separators: surname+phone, FIN+VÖEN", "glued values", r, policy=("D-66e",))

r = add(6, 29, "repeated_formats", f"Bizimlə {EM1} ünvanı ilə əlaqə saxlayın.", [(EM1, "EMAIL")],
        "reference: one occurrence", "one occurrence")
add(6, 29, "repeated_formats",
    f'Bizimlə {EM1} ünvanı ilə əlaqə saxlayın.\n{{"email": "{EM1}"}}\n| E-poçt |\n|---|\n| {EM1} |',
    [(EM1, "EMAIL")] * 3, "the same e-mail in prose, JSON and a table", "3 formats", r)
add(6, 29, "repeated_formats", f"Mobil: {PH1G}. Sistemdə: {PH1}. Köhnə qeyd: (055) 318-64-27.",
    [(PH1G, "TELEPHONENUM"), (PH1, "TELEPHONENUM"), ("(055) 318-64-27", "TELEPHONENUM")],
    "one phone written three ways", "phone 3 ways", None, policy=("D-66e",))
add(6, 29, "repeated_formats", f"Kart: {CARDG}. Təsdiq: {CARD}.",
    [(CARDG, "PAYMENT_CARD_NUMBER"), (CARD, "PAYMENT_CARD_NUMBER")], "the card grouped and ungrouped",
    "card 2 ways", None)
add(6, 29, "repeated_formats", f"IBAN: {IBANG}\nIBAN (sistem): {IBAN}", [(IBANG, "IBAN"), (IBAN, "IBAN")],
    "the IBAN grouped and ungrouped", "IBAN 2 ways", None)

r = add(6, 30, "mixed_language", f"Ərizəçinin FİN kodu {FIN1}, adı Rauf Əliyevdir.",
        [(FIN1, "AZ_FIN"), ("Rauf", "GIVENNAME"), ("Əliyevdir", "SURNAME")], "reference: Azerbaijani", "AZ")
add(6, 30, "mixed_language", f"The applicant's FIN is {FIN1} and his name is Rauf Əliyev.",
    [(FIN1, "AZ_FIN"), ("Rauf", "GIVENNAME"), ("Əliyev", "SURNAME")], "English sentence", "EN", r)
add(6, 30, "mixed_language", f"ФИН заявителя {FIN1}, его зовут Рауф Алиев.",
    [(FIN1, "AZ_FIN"), ("Рауф", "GIVENNAME"), ("Алиев", "SURNAME")], "Russian sentence, name in Cyrillic", "RU", r)
add(6, 30, "mixed_language", f"Erizecinin FIN kodu {FIN1}, adi Rauf Eliyevdir.",
    [(FIN1, "AZ_FIN"), ("Rauf", "GIVENNAME"), ("Eliyevdir", "SURNAME")], "Azerbaijani typed without its letters",
    "AZ ASCII", r)
add(6, 30, "mixed_language", f"Salam, FIN kodum {FIN1}-dir, please check it asap. Rauf Əliyev",
    [(FIN1, "AZ_FIN"), ("Rauf", "GIVENNAME"), ("Əliyev", "SURNAME")], "chat code-switch AZ + EN", "AZ+EN", r)

# ============================== G7 document types ==============================
r = add(7, 31, "letters_signatures", f"Rauf Əliyev ilə {PH1G} nömrəsi ilə əlaqə saxlaya bilərsiniz.",
        [("Rauf", "GIVENNAME"), ("Əliyev", "SURNAME"), (PH1G, "TELEPHONENUM")], "reference: one sentence", "sentence")
add(7, 31, "letters_signatures",
    f"Hörmətli həmkarlar,\n\nSorğunuz qəbul olunub, növbəti həftə cavab veriləcək.\n\nHörmətlə,\nRauf Əliyev\nBaş mütəxəssis\nTel.: {PH1G}\nE-poçt: {EM1}",
    [("Rauf", "GIVENNAME"), ("Əliyev", "SURNAME"), (PH1G, "TELEPHONENUM"), (EM1, "EMAIL")],
    "formal letter with a signature block", "formal letter", r)
add(7, 31, "letters_signatures",
    f"Sənədlər əlavə olunub.\n\n        Rauf Əliyev\n        {PH1G}\n        {EM1}",
    [("Rauf", "GIVENNAME"), ("Əliyev", "SURNAME"), (PH1G, "TELEPHONENUM"), (EM1, "EMAIL")],
    "indented signature without labels", "indented signature", r)
add(7, 31, "letters_signatures", f"Rauf Əliyev | {PH1G} | {EM1}",
    [("Rauf", "GIVENNAME"), ("Əliyev", "SURNAME"), (PH1G, "TELEPHONENUM"), (EM1, "EMAIL")],
    "compact one-line signature with pipes", "compact signature", r)
add(7, 31, "letters_signatures", f"— Rauf Əliyev —\ntel.: +994-55-318-64-27; e-poçt: <{EM1}>",
    [("Rauf", "GIVENNAME"), ("Əliyev", "SURNAME"), ("+994-55-318-64-27", "TELEPHONENUM"), (EM1, "EMAIL")],
    "punctuation-heavy contact block", "punctuation-heavy", r, policy=("D-72d",))

r = add(7, 32, "forms", f"Ad: Səbinə\nSoyad: Qasımova\nPasport: {PASS}",
        [("Səbinə", "GIVENNAME"), ("Qasımova", "SURNAME"), (PASS, "AZ_PASSPORT_NUMBER")],
        "reference: label: value lines", "label lines")
add(7, 32, "forms", f"Ad.............. Səbinə\nSoyad........... Qasımova\nPasport......... {PASS}",
    [("Səbinə", "GIVENNAME"), ("Qasımova", "SURNAME"), (PASS, "AZ_PASSPORT_NUMBER")], "dotted leaders", "dotted leaders", r)
add(7, 32, "forms", f"[x] Pasport  [ ] Şəxsiyyət vəsiqəsi\nSənədin nömrəsi: {PASS}\n[x] Razıyam",
    [(PASS, "AZ_PASSPORT_NUMBER")], "checkbox form", "checkboxes", None)
add(7, 32, "forms", f"Ad         Soyad       Pasport\nSəbinə     Qasımova    {PASS}",
    [("Səbinə", "GIVENNAME"), ("Qasımova", "SURNAME"), (PASS, "AZ_PASSPORT_NUMBER")],
    "space-aligned columns", "aligned columns", r)
add(7, 32, "forms", f"Müraciətin səbəbi:\nPasportumu itirmişəm, nömrəsi\n{PASS} idi, yenisini istəyirəm.",
    [(PASS, "AZ_PASSPORT_NUMBER")], "multiline free answer", "multiline answer", None)

r = add(7, 33, "invoices_receipts", f"Satıcının VÖEN-i: {VOEN}", [(VOEN, "AZ_VOEN")],
        "reference: VÖEN after a label", "label line")
add(7, 33, "invoices_receipts",
    f"QAİMƏ № 00381752\nSatıcı VÖEN: {VOEN}\nMəhsul: MHS-88412 x 3 ədəd — 149,90 AZN\nCəmi: 449,70 AZN",
    [(VOEN, "AZ_VOEN")], "invoice: VÖEN beside an 8-digit invoice number, a product code, counts, prices",
    "invoice", r, policy=("D-66e",))
add(7, 33, "invoices_receipts",
    f"Sifariş nömrəsi: 4829173651\nKuryer: {PH3}\nÇatdırılma haqqı: 5 AZN",
    [(PH3, "TELEPHONENUM")], "ticket: a 10-digit order number (not VÖEN) beside a phone", "order number + phone",
    None, policy=("D-66e",))
add(7, 33, "invoices_receipts",
    "ÇEK № 000417\nKassir: 03\nÇörək 2 x 0,80 AZN\nSüd 1 x 2,15 AZN\nCəmi: 3,75 AZN\nƏDV 18%: 0,57 AZN\nMəhsul kodu: 4760012345671",
    [], "negative-only receipt: prices, counts, a 13-digit product barcode", "negative receipt", None)
add(7, 33, "invoices_receipts", f"Ödəniş təsdiqləndi: 24,90 AZN\nKart: {CARDG}\nTerminal: T-0042, əməliyyat 771045",
    [(CARDG, "PAYMENT_CARD_NUMBER")], "payment slip: card beside amounts and terminal ids", "payment slip", None)

r = add(7, 34, "chat_export", f"Leyla: nömrəm {PH5}, yaz", [("Leyla", "GIVENNAME"), (PH5, "TELEPHONENUM")],
        "reference: one chat line", "one line", policy=("D-72h",))
add(7, 34, "chat_export", f"[12:05] Leyla: nömrəm {PH5}, yaz\n[12:06] Kamran: oldu",
    [("Leyla", "GIVENNAME"), (PH5, "TELEPHONENUM"), ("Kamran", "GIVENNAME")], "time stamps not TIME (D-51f)",
    "stamps", r, policy=("D-51f", "D-72h"))
add(7, 34, "chat_export", f"23.10.2026, 12:05 - Leyla Rzayeva: e-poçtum {EM4}",
    [("Leyla", "GIVENNAME"), ("Rzayeva", "SURNAME"), (EM4, "EMAIL")], "WhatsApp-style date+time stamp (not labelled)",
    "WhatsApp stamp", r, policy=("D-17", "D-72h"))
add(7, 34, "chat_export", f"Kamran: > nömrəm {PH5}, yaz\nKamran: bu nömrəni yazdım",
    [("Kamran", "GIVENNAME"), (PH5, "TELEPHONENUM"), ("Kamran", "GIVENNAME")], "quoted message with >", "quote", r,
    policy=("D-72h",))
add(7, 34, "chat_export", f"Yönləndirilmiş mesaj\nKimdən: Leyla Rzayeva\nnömrəm\n{PH5}\nyaz",
    [("Leyla", "GIVENNAME"), ("Rzayeva", "SURNAME"), (PH5, "TELEPHONENUM")], "forwarded, multiline message",
    "forwarded multiline", r, policy=("D-72h",))

r = add(7, 35, "email_headers_urls", f"From: Rauf Əliyev <{EM1}>",
        [("Rauf", "GIVENNAME"), ("Əliyev", "SURNAME"), (EM1, "EMAIL")], "reference: From header", "From")
add(7, 35, "email_headers_urls", f"To: {EM2}\nCc: {EM3}, {EM4}",
    [(EM2, "EMAIL"), (EM3, "EMAIL"), (EM4, "EMAIL")], "To and Cc with a list", "To + Cc", r)
add(7, 35, "email_headers_urls", f'From: "Əliyev, Rauf" <{EM1}>',
    [("Əliyev", "SURNAME"), ("Rauf", "GIVENNAME"), (EM1, "EMAIL")], "quoted display name, surname first",
    "quoted display name", r)
q = f"https://portal.kamran-servis.az/qeydiyyat?ref=mail&email={EM1}"
add(7, 35, "email_headers_urls", f"Keçid: {q}", [(EM1, "EMAIL")],
    "a URL without a token: the e-mail inside is labelled, the URL is not (D-72a)", "query e-mail", None,
    policy=("D-72a",))
add(7, 35, "email_headers_urls", f"Şifrəni bərpa etmək üçün: {TOKEN_URL}", [(TOKEN_URL, "URL")],
    "a URL with a token: one URL span (D-72a)", "token URL", None, policy=("D-72a",))

# ============================== G8 encodings ==============================
base = "https://portal.kamran-servis.az/profil?email="
r = add(8, 36, "url_encoding", f"Keçid: {base}{EM1}&lang=az", [(EM1, "EMAIL")],
        "reference: literal e-mail in a query (no token)", "literal", policy=("D-72a",))
for v, f in ((EM1.replace("@", "%40"), "@ as %40"), (EM1.replace("@", "%40").replace(".az", "%2Eaz"), "@ and the TLD dot encoded"),
             ("".join(f"%{ord(c):02X}" if not c.isalnum() else c for c in EM1), "every delimiter encoded")):
    add(8, 36, "url_encoding", f"Keçid: {base}{v}&lang=az", [(v, "EMAIL")], f"{f} (vs {r})", f, r,
        policy=("D-72a", "D-72e"), representation="raw percent-encoded text")
v = "%2B994553186427"
add(8, 36, "url_encoding", f"Keçid: https://portal.kamran-servis.az/zeng?tel={v}&lang=az", [(v, "TELEPHONENUM")],
    "a phone with %2B for +", "phone %2B", None, policy=("D-72a", "D-72e"), representation="raw percent-encoded text")

r = add(8, 37, "html_entities", f"<p>E-poçt: {EM2}</p>", [(EM2, "EMAIL")], "reference: literal @ in HTML", "literal")
for v, f in ((EM2.replace("@", "&#64;"), "decimal &#64;"), (EM2.replace("@", "&#x40;"), "hex &#x40;"),
             (EM2.replace("@", "&commat;"), "named &commat;"), ("&#115;." + EM2[2:].replace("@", "&#64;"), "mixed literal/entity")):
    add(8, 37, "html_entities", f"<p>E-poçt: {v}</p>", [(v, "EMAIL")], f"{f} (vs {r})", f, r, policy=("D-72e",),
        representation="raw HTML entities in the text")

r = add(8, 38, "json_escapes", '{"ad":"Rauf","soyad":"Əliyev"}', [("Rauf", "GIVENNAME"), ("Əliyev", "SURNAME")],
        "reference: literal Ə", "literal")
add(8, 38, "json_escapes", '{"ad":"Rauf","soyad":"\\u018fliyev"}', [("Rauf", "GIVENNAME"), ("\\u018fliyev", "SURNAME")],
    "the text holds a literal backslash-u escape for Ə", "\\u escape in name", r, policy=("D-72e",),
    representation="literal backslash-u sequence in the text (not decoded)")
v = EM1.replace("@", "\\u0040")
add(8, 38, "json_escapes", f'{{"email":"{v}"}}', [(v, "EMAIL")], "literal \\u0040 for @", "\\u0040", None,
    policy=("D-72e",), representation="literal backslash-u sequence in the text")
add(8, 38, "json_escapes", f'{{"msg":"{{\\"email\\":\\"{EM1}\\",\\"ad\\":\\"Rauf\\"}}"}}',
    [(EM1, "EMAIL"), ("Rauf", "GIVENNAME")], "JSON embedded in a JSON string", "JSON in string", None,
    representation="literal backslash-quote characters")
v = EM1.replace("/", "")
add(8, 38, "json_escapes", f'{{"profil":"https:\\/\\/portal.kamran-servis.az\\/u","email":"{EM1}"}}', [(EM1, "EMAIL")],
    "escaped slashes in a sibling field", "escaped slashes nearby", None)

r = add(8, 39, "base64_distractors", f"E-poçt: {EM3}", [(EM3, "EMAIL")], "reference: e-mail alone", "alone")
add(8, 39, "base64_distractors", f"sorğu=req-7f3a9c1e e-poçt={EM3} imza=dGVzdA==", [(EM3, "EMAIL")],
    "beside a short request id and padded base64 (not PII, D-72k)", "short ids", r, policy=("D-72k",))
add(8, 39, "base64_distractors", f"fayl=c2FtcGxlLWZpbGU=.pdf istifadəçi={EM3} ölçü=48213", [(EM3, "EMAIL")],
    "beside a base64 file name and a size", "base64 file name", r, policy=("D-72k",))
add(8, 39, "base64_distractors", "sorğu=req-7f3a9c1e imza=dGVzdA== fayl=c2FtcGxlLWZpbGU=.pdf versiya=4.2.1", [],
    "negative-only: opaque short strings, nothing personal", "negative opaque", None, policy=("D-72k",))
add(8, 39, "base64_distractors", f"Sifariş SİF-2026-004817, izləmə kodu AZP7731905KR, alıcı {EM3}", [(EM3, "EMAIL")],
    "beside an order code and a tracking code", "order + tracking", r)

r = add(8, 40, "representation_layers", f"Telefon: {PH1G}", [(PH1G, "TELEPHONENUM")], "reference: raw text", "raw")
for v, f, rep in (("\\u002B994 55 318 64 27", "literal \\u002B for +", "literal backslash-u sequence"),
                  ("%2B994%2055%20318%2064%2027", "URL-encoded", "percent-encoded"),
                  ("%252B994%252055%2520318%252064%252027", "double URL-encoded", "double percent-encoded"),
                  ("&#43;994 55 318 64 27", "HTML entity for +", "HTML entity")):
    add(8, 40, "representation_layers", f"Telefon: {v}", [(v, "TELEPHONENUM")], f"{f} (vs {r})", f, r,
        policy=("D-72e",), representation=rep)


# ============================== validation ==============================
def occurrences(text: str, value: str) -> list[int]:
    out, i = [], text.find(value)
    while i >= 0:
        out.append(i)
        i = text.find(value, i + 1)
    return out


def validate() -> tuple[list[str], list[dict]]:
    from piigen.validate import value_valid
    problems, spans = [], []
    lines = [json.dumps(c, ensure_ascii=False) for c in CASES]
    # 1 every line parses; 2 exactly 200 unique ids; 3 keys and labels
    parsed = [json.loads(l) for l in lines]
    if len(parsed) != 200:
        problems.append(f"2: {len(parsed)} cases, not 200")
    ids = [c["id"] for c in parsed]
    if len(set(ids)) != len(ids) or ids != [f"F-{i:03d}" for i in range(1, len(ids) + 1)]:
        problems.append("2: ids not unique/sequential")
    for c in parsed:
        if set(c) != {"id", "kind", "text", "expected", "probe"}:
            problems.append(f"3: {c['id']} keys {sorted(c)}")
        for e in c["expected"]:
            if set(e) != {"value", "label"} or e["label"] not in LABELS:
                problems.append(f"3: {c['id']} bad expected item {e}")
    for c in parsed:
        text = c["text"]
        # 4 substrings; 5 occurrence counts and order; span assignment in reading order
        pos, sp = 0, []
        need = Counter(e["value"] for e in c["expected"])
        for v, n in need.items():
            if len(occurrences(text, v)) < n:
                problems.append(f"4/5: {c['id']} {v!r} expected {n}x, found {len(occurrences(text, v))}x")
        taken: list[tuple[int, int]] = []
        for e in c["expected"]:
            starts = [s for s in occurrences(text, e["value"]) if s >= pos
                      and not any(a < s + len(e["value"]) and s < b for a, b in taken)]
            if not starts:
                problems.append(f"4/5: {c['id']} cannot place {e['value']!r} in reading order")
                continue
            s = starts[0]
            # a value that is also a substring of a longer expected value must not land inside it
            taken.append((s, s + len(e["value"])))
            sp.append({"start": s, "end": s + len(e["value"]), "label": e["label"], "value": e["value"]})
            pos = s + 1
        spans.append({"id": c["id"], "spans": sp})
        # 6 dummies never positive
        for e in c["expected"]:
            if e["value"] in DUMMIES:
                problems.append(f"6: {c['id']} dummy {e['value']} expected positive")
        # 7 log date-time stamps never expected
        for e in c["expected"]:
            if e["label"] in ("DATE", "TIME"):
                problems.append(f"7: {c['id']} DATE/TIME expected; check D-17")
        # 8 field labels outside spans
        for e in c["expected"]:
            if re.match(r"(?i)(telefon|e-poçt|fin|vöen|iban|kart|pasport|email)\s*[:=]", e["value"]):
                problems.append(f"8: {c['id']} label inside span {e['value']!r}")
        # 10 invisible characters survive JSON round trip
        if json.loads(json.dumps(text, ensure_ascii=False)) != text:
            problems.append(f"10: {c['id']} text does not round-trip")
    # 9 (partial, automatic): every clean e-mail/IBAN/card/phone-shaped string is expected
    shapes = {"EMAIL": r"[\w.]+@[\w-]+\.[a-z]{2,}", "IBAN": r"\bAZ\d{2}[A-Z]{4}\w{20}\b",
              "TELEPHONENUM": r"\+994\d{9}\b"}
    for c in parsed:
        exp = [e["value"] for e in c["expected"]]
        for lab, rx in shapes.items():
            for m in re.finditer(rx, c["text"]):
                if not any(m.group(0) in v for v in exp):
                    problems.append(f"9: {c['id']} unannotated {lab}-shaped {m.group(0)!r}")
    # 11 references exist and are earlier in the same family
    fam = {m["id"]: m["family"] for m in META}
    for m in META:
        if m["reference"] not in fam or fam[m["reference"]] != m["family"]:
            problems.append(f"11: {m['id']} reference {m['reference']} not in its family")
    # 12 no duplicate texts
    dup = [t for t, n in Counter(c["text"] for c in parsed).items() if n > 1]
    if dup:
        problems.append(f"12: {len(dup)} duplicate texts")
    # family sizes: 40 families x 5
    sizes = Counter(m["family"] for m in META)
    bad = {f: n for f, n in sizes.items() if n != 5}
    if len(sizes) != 40 or bad:
        problems.append(f"design: {len(sizes)} families; not 5 cases: {bad}")
    # clean values pass the project's validators
    for lab, v in CLEAN:
        ok, why = value_valid(lab, v)
        if not ok:
            problems.append(f"validator: {lab} {v!r}: {why}")
    return problems, spans


def main() -> int:
    problems, spans = validate()
    (HERE / "formats_az_v42_200.jsonl").write_text(
        "".join(json.dumps(c, ensure_ascii=True) + "\n" for c in CASES), encoding="utf-8")
    (HERE / "manifest.jsonl").write_text("".join(json.dumps(m, ensure_ascii=False) + "\n" for m in META),
                                         encoding="utf-8")
    (HERE / "spans.jsonl").write_text("".join(json.dumps(s, ensure_ascii=False) + "\n" for s in spans),
                                      encoding="utf-8")
    pos = sum(1 for c in CASES if c["expected"])
    labels = Counter(e["label"] for c in CASES for e in c["expected"])
    L = ["# Formats benchmark: validation", "",
         f"Cases: {len(CASES)} ({pos} with expected entities, {len(CASES) - pos} negative-only); "
         f"expected occurrences: {sum(labels.values())}.", "",
         "| Label | Expected occurrences |", "|---|---|", *[f"| {k} | {v} |" for k, v in labels.most_common()], "",
         "## Checks", "",
         "1–5, 8, 10–12 are automatic; 9 is automatic for e-mail/IBAN/+994 shapes and by reading for the rest;"
         " 6–7 are automatic.", "",
         "**Result:** " + ("all checks pass." if not problems else f"{len(problems)} problem(s):"), *problems]
    (HERE / "validation.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
