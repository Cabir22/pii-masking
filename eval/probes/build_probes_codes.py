"""Build the code_density probe family (ask, 26 Oct): eval/probes/code_density.jsonl.

    python eval/probes/build_probes_codes.py [--seed 35]

The red-team X-MAC and X-IP6 trials found that m1 misses MAC and IPv6 addresses when the document also
holds several unlabelled codes (versions, contract clauses, order codes): IPv6 92% in plain prose,
17.5% with several codes. This family checks every technical label for the same pattern.

Design: for each label (IPV4_ADDRESS, IPV6_ADDRESS, MAC_ADDRESS, URL, ACCESS_TOKEN, API_KEY, and
EMAIL as the comparison that m1 kept at 30/30), 10 triples. A triple is one document skeleton and one
value; its three documents differ only in how many unlabelled code sentences surround the value
sentence: 0, 2 or 6 (half before, half after). So any drop is the codes' doing.
Gold spans carry `codes` ("0"/"2"/"6") and `cell` ("<label>|<codes>") for the scoreboard's entity
slices; the codes are `controls` (kind `code`), so over-masking them is reported too.
URLs carry a credential (D-72a: a plain page link is not URL). Versions never read as a date (their middle part is 13-49). Every sentence here was written for
this probe (rule A2.5); value makers come from build_probes.py.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_probes as BP  # noqa: E402

FAMILY = "code_density"
DENSITIES = (0, 2, 6)
PER_LABEL = 10


def url(r):
    """A URL with a credential in it: only then is it URL (D-72a); a plain page link is not PII."""
    host = r.choice(["portal.qovsaq.com", "docs.northdesk.io", "kabinet.ofisnet.az", "app.mektub-xett.az"])
    path = r.choice(["hesabat", "sened", "muraciet", "fayl", "qeyd"])
    key = r.choice(["?token=", "?sig=", "?auth=", "#t="])
    return f"https://{host}/{path}{key}{BP._rs(r, BP.ALNUM + '-_', r.randint(28, 40))}"


VALUE = {"IPV4_ADDRESS": BP.ipv4, "IPV6_ADDRESS": BP.ipv6, "MAC_ADDRESS": BP.mac, "URL": url,
         "ACCESS_TOKEN": BP.access_token, "API_KEY": BP.api_key, "EMAIL": BP.email}

FRAMES = {
    "IPV4_ADDRESS": ["Sorğu {v} ünvanından gəlib və qəbul edilib.",
                     "Uğursuz giriş cəhdi {v} IP ünvanından qeydə alınıb.",
                     "Trafik müvəqqəti olaraq {v} ünvanına yönləndirildi."],
    "IPV6_ADDRESS": ["Cihaz şəbəkəyə {v} ünvanı ilə qoşulub.",
                     "Bağlantı {v} ünvanından quruldu, sonra kəsildi.",
                     "Yeni qovşaq üçün {v} ünvanı ayrılıb."],
    "MAC_ADDRESS": ["Şəbəkə kartının fiziki ünvanı {v} olaraq görünür.",
                    "Router {v} cihazını tanımadı və bağlantını rədd etdi.",
                    "Siyahıya {v} fiziki ünvanlı printer əlavə olundu."],
    "URL": ["Ətraflı məlumat {v} səhifəsində yerləşdirilib.",
            "Faylı {v} linkindən yükləmək olar.",
            "Müraciətin vəziyyətini {v} ünvanında izləyin."],
    "ACCESS_TOKEN": ["Sessiya {v} tokeni ilə açıldı.",
                     "Müvəqqəti giriş üçün {v} tokeni verildi.",
                     "Sorğuda {v} tokeni göndərilib, müddəti bitib."],
    "API_KEY": ["İnteqrasiya {v} açarı ilə işləyir.",
                "Xidmətə qoşulmaq üçün {v} açarından istifadə olunur.",
                "Köhnə {v} açarı ləğv edildi və yenisi yaradıldı."],
    "EMAIL": ["Cavabı {v} ünvanına göndərin.",
              "Hesabat {v} ünvanından gəlib.",
              "Əlaqə üçün {v} ünvanı göstərilib."],
}
INTRO = ["Texniki dəstək xidmətinin həftəlik qeydi.", "Aşağıda yoxlamanın qısa nəticəsi verilir.",
         "Hadisə barədə daxili məlumat.", "Növbətçi mühəndisin qeydləri.", "Sistem jurnalından çıxarış."]
OUTRO = ["Əlavə sual olarsa, dəstək komandasına yazın.", "Yoxlama növbəti həftə təkrarlanacaq.",
         "Məsələ hələlik açıq qalır.", "Qeyd arxivə köçürülüb.", "Növbəti addım rəhbərliklə razılaşdırılacaq."]


def version(r):
    return f"{r.randint(1, 12)}.{r.randint(13, 49)}.{r.randint(0, 20)}"


CODES = [  # (sentence with {c}, code maker): unlabelled, not PII, not a look-alike of any label above
    ("Proqram təminatı {c} versiyasına yenilənib.", version),
    ("Quraşdırma {c} buraxılışı ilə aparılıb.", lambda r: "v" + version(r)),
    ("Sənəd müqavilənin {c} bəndinə əsasən hazırlanıb.", lambda r: f"{r.randint(2, 19)}.{r.randint(1, 9)}"),
    ("Sifariş {c} nömrəsi ilə qeydiyyata alınıb.", lambda r: f"SF-{r.randint(2019, 2026)}-{r.randint(1000, 99999)}"),
    ("Müraciət {c} kodu ilə açılıb.", lambda r: f"TKT-{r.randint(10000, 99999)}"),
    ("Hesab-faktura {c} üzrə ödəniş gözlənilir.", lambda r: f"QF-{r.randint(100, 999)}/{r.randint(19, 26)}"),
    ("Avadanlıq {c} modelinə aiddir.", lambda r: f"{BP._rs(r, 'ABCDEFGHKMNPRSTX', 2)}-{r.randint(100, 990)}"),
    ("Dəyişiklik {c} paketində saxlanılıb.", lambda r: f"build-{r.randint(1000, 9999)}"),
]


def build(seed: int) -> list[dict]:
    r = random.Random(seed)
    forbidden = BP.load_forbidden()
    rows: list[dict] = []
    pair = 0
    for label in VALUE:
        for i in range(PER_LABEL):
            v = next(x for x in (VALUE[label](r) for _ in range(50)) if x not in forbidden)
            frame = FRAMES[label][i % len(FRAMES[label])]
            intro, outro = r.choice(INTRO), r.choice(OUTRO)
            codes = [(s, mk(r)) for s, mk in r.sample(CODES, 6)]   # one draw per triple, so 2 is a subset of 6
            for n in DENSITIES:
                use = codes[:n]
                before, after = use[:(n + 1) // 2], use[(n + 1) // 2:]
                parts, ctl = [intro], []
                text = intro
                for s, c in before:
                    pre, post = s.split("{c}")
                    text += " " + pre
                    ctl.append({"start": len(text), "end": len(text) + len(c), "resembles": "none", "kind": "code"})
                    text += c + post
                pre, post = frame.split("{v}")
                text += " " + pre
                ent = {"start": len(text), "end": len(text) + len(v), "label": label, "codes": str(n), "cell": f"{label}|{n}"}
                text += v + post
                for s, c in after:
                    pre, post = s.split("{c}")
                    text += " " + pre
                    ctl.append({"start": len(text), "end": len(text) + len(c), "resembles": "none", "kind": "code"})
                    text += c + post
                text += " " + outro
                rec = {"id": f"{FAMILY}_{len(rows) + 1:03d}", "text": text, "lang": "az", "family": FAMILY,
                       "pair": pair, "role": f"codes_{n}", "entities": [ent]}
                if ctl:
                    rec["controls"] = ctl
                rows.append(rec)
            pair += 1
    return rows


def check(rows: list[dict]) -> list[str]:
    bad = []
    for x in rows:
        for e in x["entities"] + x.get("controls", []):
            if not (0 <= e["start"] < e["end"] <= len(x["text"])) or x["text"][e["start"]:e["end"]] != x["text"][e["start"]:e["end"]].strip():
                bad.append(f"{x['id']}: bad span")
        if len(x.get("controls", [])) != int(x["role"].split("_")[1]):
            bad.append(f"{x['id']}: code count")
    by = {}
    for x in rows:
        by.setdefault(x["pair"], []).append(x)
    for p, xs in by.items():
        vals = {x["text"][x["entities"][0]["start"]:x["entities"][0]["end"]] for x in xs}
        if len(xs) != 3 or len(vals) != 1:
            bad.append(f"pair {p}: not one value in three documents")
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=35)
    ap.add_argument("--out", type=Path, default=HERE)
    a = ap.parse_args(argv)
    rows = build(a.seed)
    problems = check(rows)
    (a.out / f"{FAMILY}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows), encoding="utf-8")
    print(f"{FAMILY}: {len(rows)} documents ({len(VALUE)} labels x {PER_LABEL} triples x {len(DENSITIES)} densities), "
          f"{sum(len(x.get('controls', [])) for x in rows)} code controls; problems: {len(problems)}")
    for p in problems[:20]:
        print("  ", p)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
