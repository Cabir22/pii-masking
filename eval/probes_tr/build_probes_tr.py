"""Turkish probe families (D-58): hand-written Turkish carrier sentences, our own
value and look-alike makers (eval/probes/build_probes.py; never the training generator).

Families mirror the Azerbaijani ones that carry a C rule, plus the Turkish specifics:
apostrophe endings on names (D-56d: the span covers the whole inflected form), endings after a
time or number (outside the span), weekdays outside DATE (D-54d), İ/ı casing, values at a line end.

    python eval/probes_tr/build_probes_tr.py            # writes eval/probes_tr/*.jsonl
    python eval/probes_tr/build_probes_tr.py --check    # rebuild in memory, fail if a file differs
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "probes"))

import build_probes as B  # noqa: E402

SEED = 20261020
TR_MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim",
             "Kasım", "Aralık"]
TR_WEEKDAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


def tr_date(r):
    d, m, y = r.randint(1, 28), r.randint(1, 12), r.randint(1960, 2004)
    return r.choice([f"{d:02d}.{m:02d}.{y}", f"{d} {TR_MONTHS[m - 1]} {y}", f"{y}-{m:02d}-{d:02d}"])


def tr_bad_date(r):
    # the same year range as the valid dates, so only the day or month gives it away (note)
    y = r.randint(1960, 2004)
    return r.choice([f"30 Şubat {y}", f"31.04.{y}", f"{y}-02-30", f"{r.randint(13, 28)}.{r.randint(13, 18)}.{y}"])


# Turkish reads a time aloud; the ending after it follows the last spoken word (vowel harmony,
# t after a voiceless consonant, y after a vowel): 14:02'de (iki), 23:03'te (üç), 10:30'da (otuz).
_UNITS = ["sıfır", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
_TENS = {1: "on", 2: "yirmi", 3: "otuz", 4: "kırk", 5: "elli"}


def _last_word(hhmm: str) -> str:
    h, m = (int(x) for x in hhmm.split(":"))
    n = m if m else h
    return _UNITS[n % 10] if n % 10 or n == 0 else _TENS[n // 10]


def tr_ending(hhmm: str, case: str) -> str:
    w = _last_word(hhmm)
    back = [c for c in w if c in "aıoueiöü"][-1] in "aıou"
    vowel_end, hard = w[-1] in "aıoueiöü", w[-1] in "çfhkpsşt"
    if case == "LOC":
        return "'" + ("t" if hard else "d") + ("a" if back else "e")
    if case == "ABL":
        return "'" + ("t" if hard else "d") + ("an" if back else "en")
    if case == "DAT":
        return "'" + ("y" if vowel_end else "") + ("a" if back else "e")
    raise ValueError(case)


class TRBuilder(B.Builder):
    def __init__(self, seed, forbidden):
        super().__init__(seed, forbidden)
        self.extra_value = {"DATE": tr_date}
        self.extra_look = {"DATE": tr_bad_date}

    def val(self, label, **kw):
        if label in self.extra_value:
            return self.extra_value[label](self.r)
        return super().val(label, **kw)

    def look(self, label, policy_share=0.15):
        if label in self.extra_look:
            return self.extra_look[label](self.r), "invalid_shape", False
        return super().look(label, policy_share)

    def add(self, family, pair, role, rendered, **extra):
        super().add(family, pair, role, rendered, **extra)
        self.out[family][-1]["lang"] = "tr"


# (case, label, bare, inflected): Turkish writes an apostrophe before the ending of a proper
# noun; vowel harmony and consonant softening are written out by hand.
INFLECTED = [
    ("gen", "CITY", "Gence", "Gence'nin"), ("gen", "GIVENNAME", "Ayşe", "Ayşe'nin"), ("gen", "SURNAME", "Hüseynov", "Hüseynov'un"),
    ("gen", "GIVENNAME", "Elvin", "Elvin'in"), ("gen", "SURNAME", "Aliyeva", "Aliyeva'nın"), ("gen", "STREET", "Nizami Caddesi", "Nizami Caddesi'nin"),
    ("dat", "CITY", "Bakü", "Bakü'ye"), ("dat", "GIVENNAME", "Mehmet", "Mehmet'e"), ("dat", "SURNAME", "Babayev", "Babayev'e"),
    ("dat", "CITY", "Şeki", "Şeki'ye"), ("dat", "GIVENNAME", "Nigar", "Nigar'a"), ("dat", "CITY", "İzmir", "İzmir'e"),
    ("loc", "CITY", "Lenkeran", "Lenkeran'da"), ("loc", "CITY", "Ankara", "Ankara'da"), ("loc", "STREET", "Füzuli Sokağı", "Füzuli Sokağı'nda"),
    ("loc", "CITY", "Gence", "Gence'de"), ("loc", "CITY", "Bakü", "Bakü'de"), ("loc", "CITY", "Kuba", "Kuba'da"),
    ("abl", "GIVENNAME", "Tural", "Tural'dan"), ("abl", "SURNAME", "Kerimli", "Kerimli'den"), ("abl", "CITY", "Şamahı", "Şamahı'dan"),
    ("abl", "GIVENNAME", "Zeynep", "Zeynep'ten"), ("abl", "CITY", "Bakü", "Bakü'den"), ("abl", "STREET", "Azadlık Caddesi", "Azadlık Caddesi'nden"),
    ("acc", "GIVENNAME", "Kamran", "Kamran'ı"), ("acc", "CITY", "Gence", "Gence'yi"), ("acc", "SURNAME", "Rzayeva", "Rzayeva'yı"),
    ("acc", "GIVENNAME", "Emre", "Emre'yi"), ("acc", "CITY", "İstanbul", "İstanbul'u"), ("acc", "GIVENNAME", "Günay", "Günay'ı"),
    ("ins", "GIVENNAME", "Orhan", "Orhan'la"), ("ins", "GIVENNAME", "Leyla", "Leyla'yla"), ("ins", "SURNAME", "Musayev", "Musayev'le"),
    ("ins", "GIVENNAME", "Selin", "Selin'le"), ("ins", "CITY", "Gence", "Gence'yle"), ("ins", "SURNAME", "Abbasova", "Abbasova'yla"),
]
FRAMES_BY_CASE = {
    "gen": ["{v} başvurusu dün işleme alındı.", "Raporda {v} adı geçiyor.", "Ekte {v} fotoğrafları var."],
    "dat": ["Dosya {v} gönderildi.", "Toplantı daveti {v} iletildi.", "Kargo yarın {v} ulaşacak."],
    "loc": ["Şube {v} açıldı.", "Etkinlik {v} yapılacak.", "Kayıt {v} tutuluyor."],
    "abl": ["Bu mesaj {v} geldi.", "Ödeme {v} alındı.", "Talep {v} iletildi."],
    "acc": ["Lütfen {v} arayın.", "Müdür geçen ay {v} ziyaret etti.", "Formda {v} işaretleyin."],
    "ins": ["Proje {v} birlikte yürütülüyor.", "Yeni rapor {v} ilgili.", "Sözleşme {v} imzalandı."],
}


def build(b: TRBuilder):
    r = b.r
    # --- confusion pairs (C1-C3) -----------------------------------------------------------
    tv = ["İsteğe şu değer eklendi: {v}", "Yapılandırmada {v} saklanıyor.", "Bağlantı için {v} kullanıldı.",
          "Ortam dosyasında şöyle yazıyor: {v}", "Yetkilendirme başlığında {v} görüldü.", "Betik {v} ile çalışıyor."]
    for i in range(12):
        t = tv[i % len(tv)]
        b.add("token_vs_key_tr", i, "token", B.render(t, v=(b.val("ACCESS_TOKEN"), "ACCESS_TOKEN")))
        b.add("token_vs_key_tr", i, "key", B.render(t, v=(b.val("API_KEY"), "API_KEY")))
    nv = ["Ağ günlüğünde {v} kaydedildi.", "Cihaz {v} ile tanımlandı.", "Bu adres beyaz listede: {v}",
          "Bağlantının kaynağı {v} idi.", "İzleme {v} için uyarı verdi.", "Yapılandırma satırı: {v}"]
    for i in range(12):
        t = nv[i % len(nv)]
        b.add("ipv6_vs_mac_tr", i, "ipv6", B.render(t, v=(b.val("IPV6_ADDRESS"), "IPV6_ADDRESS")))
        b.add("ipv6_vs_mac_tr", i, "mac", B.render(t, v=(b.val("MAC_ADDRESS"), "MAC_ADDRESS")))
    lv = ["Sunulan belgenin numarası {v}.", "Kontrolde {v} numaralı belge gösterildi.", "Ehliyetini de getirdi: {v}.",
          "Kimlik numarası {v} olarak yazılmış.", "Belge: {v}, geçerli.", "Kayıt {v} üzerinden yapıldı."]
    for i in range(12):
        t = lv[i % len(lv)]
        b.add("licence_vs_id_tr", i, "licence", B.render(t, v=(b.val("AZ_DRIVER_LICENSE_NUMBER"), "AZ_DRIVER_LICENSE_NUMBER")))
        b.add("licence_vs_id_tr", i, "id_card", B.render(t, v=(b.val("AZ_ID_CARD_NUMBER"), "AZ_ID_CARD_NUMBER")))
    # --- one look-alike family per type (C4) ---------------------------------------------------
    b.pairs("decoy_cvv_tr", "CARD_SECURITY_CODE", ["Kartın CVV kodu: {v}", "Ödeme formuna CVV {v} yazıldı.", "CVC alanında {v} görünüyor."])
    b.pairs("decoy_time_tr", "TIME", ["Görüşme saati: {v}", "Tren saat {v} civarında varıyor.", "Programda saat {v} olarak gösterilmiş."])
    b.pairs("decoy_date_tr", "DATE", ["Doğum tarihi: {v}", "Belge {v} tarihinde imzalandı.", "Tarih alanında {v} yazıyor."])
    b.pairs("decoy_zip_tr", "ZIPCODE", ["Posta kodu: {v}", "Gönderi {v} posta kodlu adrese gidiyor.", "Posta kodu alanında {v} yazılı."])
    b.pairs("decoy_fin_tr", "AZ_FIN", ["FİN kodu: {v}", "Başvuruda FİN {v} belirtilmiş.", "Veritabanında {v} FİN'i arandı."])
    b.pairs("decoy_ipv4_tr", "IPV4_ADDRESS", ["Sunucu adresi {v} olarak yazılmış.", "Kaynak IP {v} olarak kaydedildi.",
                                              "Günlükte IPv4 {v} görünüyor.", "Ağ geçmişinde {v} adresi kalmış."])
    for i in range(12):
        lab = ["PAYMENT_CARD_NUMBER", "ICCID", "IBAN"][i % 3]
        t = {"PAYMENT_CARD_NUMBER": "Kart numarası: {v}", "ICCID": "SIM kartın seri numarası {v}.", "IBAN": "Hesap: {v}"}[lab]
        b.add("decoy_card_iccid_iban_tr", i, "valid", B.render(t, v=(b.val(lab), lab)))
        dv, k, p = b.look(lab)
        b.add("decoy_card_iccid_iban_tr", i, "invalid", B.render(t.replace("{v}", "{d}"), d=(dv, lab, k, p)))
    for i in range(12):
        lab = ["AZ_VOEN", "AZ_PASSPORT_NUMBER", "AZ_ID_CARD_NUMBER"][i % 3]
        word = {"AZ_VOEN": "VÖEN", "AZ_PASSPORT_NUMBER": "pasaport numarası", "AZ_ID_CARD_NUMBER": "kimlik kartı numarası"}[lab]
        t = f"Başvuruda {word} {{v}} belirtilmiş."
        b.add("decoy_voen_passport_id_tr", i, "valid", B.render(t, v=(b.val(lab), lab)))
        dv, k, p = b.look(lab)
        b.add("decoy_voen_passport_id_tr", i, "invalid", B.render(t.replace("{v}", "{d}"), d=(dv, lab, k, p)))
    # --- Turkish specifics ------------------------------------------------------------------------
    for i, (case, lab, bare, form) in enumerate(INFLECTED):
        t = FRAMES_BY_CASE[case][i % 3]
        b.add("inflected_names_tr", i, case, B.render(t, v=(form, lab, {"case": case})), stem=bare)
    tf = [("Toplantı saat {v}{e} başlıyor.", "LOC"), ("Kargo {v}{e} teslim edilecek.", "LOC"),
          ("Uçak {v}{e} önce kalkmaz.", "ABL"), ("Nöbet {v}{e} kadar sürüyor.", "DAT"),
          ("Sistem {v}{e} yeniden başlatıldı.", "LOC"), ("Randevunuz saat {v}{e}.", "LOC")]
    for i in range(12):
        t, case = tf[i % len(tf)]
        v = B.time_(r)
        b.add("time_ending_outside_tr", i, case.lower(), B.render(t.replace("{e}", tr_ending(v, case)), v=(v, "TIME")))
    wf = ["Toplantı {w}, {v} tarihinde yapıldı.", "Son başvuru günü: {w}, {v}", "Belge {v} {w} günü teslim edildi."]
    for i in range(12):
        d, m, y = r.randint(1, 28), r.randint(1, 12), r.randint(2020, 2026)
        t = wf[i % len(wf)].replace("{w}", TR_WEEKDAYS[datetime.date(y, m, d).weekday()])  # the date's real weekday
        b.add("weekday_outside_date_tr", i, "date", B.render(t, v=(f"{d} {TR_MONTHS[m - 1]} {y}", "DATE")))
    caps = [("İLKNUR", "GIVENNAME"), ("IŞIL", "GIVENNAME"), ("İSMAİL", "GIVENNAME"), ("ÇİĞDEM", "GIVENNAME"),
            ("İnci", "GIVENNAME"), ("Işık", "SURNAME"), ("YILDIRIM", "SURNAME"), ("ŞİMŞEK", "SURNAME"),
            ("İZMİR", "CITY"), ("IĞDIR", "CITY"), ("ŞIRNAK", "CITY"), ("İsmayıllı", "CITY")]
    cf = {"GIVENNAME": "ADI: {v}", "SURNAME": "SOYADI: {v}", "CITY": "DOĞUM YERİ: {v}"}
    for i, (v, lab) in enumerate(caps):
        b.add("dotted_i_caps_tr", i, lab.lower(), B.render(cf[lab], v=(v, lab)))
    le = ["İstek bu adresten geldi: {v}", "Müşteri yazıyor: benim adresim {v}", "Sistem kaydı, kaynak adres {v};",
          "Adresi bir daha kontrol edin {v}"]
    for i in range(12):
        lab = ["IPV4_ADDRESS", "IPV6_ADDRESS", "EMAIL"][i % 3]
        b.add("line_end_ip_email_tr", i // 3, lab.lower(), B.render(le[(i // 3) % len(le)], v=(b.val(lab), lab)))
    pf = ["Karadeniz kıyısındaki dağ köyleri, kışın kar yüzünden ova kasabalarıyla bağlantısını kaybediyor; "
          "yeni yol projesi vadiyi iki ilçeye bağlayacak.",
          "Bölgenin batısındaki göller göçmen kuşlar için önemli bir durak; ilkbaharda kuzeyden gelen sürüler "
          "burada birkaç hafta kalıyor.",
          "Rota sahil boyunca ilerliyor, sonra iç kesimlerdeki plato üzerinden eski İpek Yolu duraklarına uzanıyor.",
          "Toplantıda Kafkasya, Orta Asya ve Balkan ülkeleri arasındaki demiryolu bağlantıları konuşuldu.",
          "Rapor, nehir havzasındaki tarım alanlarının son on yılda nasıl değiştiğini anlatıyor.",
          "Turizm broşürü dağ evleri, şelaleler ve yayla yolları hakkında genel bilgi veriyor."]
    for i, t in enumerate(pf):
        b.add("pii_free_places_tr", i, "pii_free", (t, [], [], []))


TARGETS = {
    "token_vs_key_tr": "token_vs_key", "ipv6_vs_mac_tr": "ipv6_vs_mac", "licence_vs_id_tr": "licence_vs_id",
    "decoy_cvv_tr": "decoy_time", "decoy_time_tr": "decoy_time", "decoy_date_tr": "decoy_time", "decoy_zip_tr": "decoy_time",
    "decoy_fin_tr": "decoy_time", "decoy_ipv4_tr": "decoy_time", "decoy_card_iccid_iban_tr": "decoy_time",
    "decoy_voen_passport_id_tr": "decoy_time", "inflected_names_tr": "suffixed_entities",
    "line_end_ip_email_tr": "line_end_ip_email",
}
OWN_TARGETS = {
    "time_ending_outside_tr": {"source": "D-58 TR: a time followed by an apostrophe ending; the span is the time only; exact recall >= 85%",
                               "conditions": [{"metric": "exact_recall", "op": ">=", "value": 0.85}]},
    "weekday_outside_date_tr": {"source": "D-54d TR: a weekday next to a date stays outside DATE; exact recall >= 85%",
                                "conditions": [{"metric": "exact_recall", "op": ">=", "value": 0.85}]},
    "dotted_i_caps_tr": {"source": "D-58 TR: names and cities in capitals with İ/ı; exact recall >= 85%",
                         "conditions": [{"metric": "exact_recall", "op": ">=", "value": 0.85}]},
    "pii_free_places_tr": {"source": "D-57/D-58 TR: PII-free text dense with place-like words; PII-free FP rate < 15%",
                           "conditions": [{"metric": "pii_free_fp_rate", "op": "<", "value": 0.15}]},
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    b = TRBuilder(SEED, B.load_forbidden())
    build(b)
    az = json.loads((HERE.parent / "probes" / "targets.json").read_text(encoding="utf-8"))
    targets = {f: {**az[src], "source": f"as {src}: " + az[src]["source"]} for f, src in TARGETS.items()}
    targets.update(OWN_TARGETS)
    files = {f"{fam}.jsonl": "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows) for fam, rows in b.out.items()}
    files["targets.json"] = json.dumps(targets, ensure_ascii=False, indent=1) + "\n"
    bad = []
    for name, content in files.items():
        p = HERE / name
        if a.check:
            if not p.exists() or p.read_text(encoding="utf-8") != content:
                bad.append(name)
        else:
            p.write_text(content, encoding="utf-8")
    if a.check:
        print("check:", "OK" if not bad else f"differs: {bad}")
        return 1 if bad else 0
    print(f"wrote {len(files) - 1} families, {sum(len(v) for v in b.out.values())} documents, targets.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
