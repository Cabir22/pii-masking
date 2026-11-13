"""Build the card_expiry probe family (D-78, 27 Oct): eval/probes/card_expiry.jsonl.

    python eval/probes/build_probes_expiry.py [--seed 78]

Red-team probes found that no model masks a card's expiry date: m1 0 of 140, v4.2 29, v4.1 10, and the
short MM/YY form once in 210 tries. v4.2's data had 13 expiries, all unlabelled. D-78 labels them DATE
(one span, `08/27`) and adds this family to the release check: reported for m2, blocking from m3.

Design: every document holds one real card (Luhn-valid) and its expiry; about half also hold a CVV.
Two forms of the expiry (`MM/YY`, `MM/YYYY`) x three layouts:
  field   a form, one field per line (`Son istifadə: 08/27`);
  prose   a sentence in running text;
  record  one line with separators (`|`, `;`, `/`), sometimes after a header line.
15 documents per cell, 90 in all. The expiry spans carry `form`, `layout` and `cell` ("<form>|<layout>")
for the scoreboard's entity slices; card and CVV spans carry none, so the slices are about the expiry only.
About a third of the documents also hold a reference number shaped NN/NN whose first part cannot be a
month (13-98): `controls` (kind `number_slash`), so a model that masks every NN/NN shows up there.

Every sentence here was written for this probe (rule A2.5) and none copies a training frame
(X-CARD in scripts/piigen/targeted/frames_v43.py: 0 shared 6-grams when built). Card and CVV makers
come from build_probes.py.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_probes as BP  # noqa: E402

FAMILY = "card_expiry"
FORMS = ("MM/YY", "MM/YYYY")
LAYOUTS = ("field", "prose", "record")
PER_CELL = 15


def expiry(r, form):
    m, yy = r.randint(1, 12), r.randint(26, 33)
    return f"{m:02d}/{yy}" if form == "MM/YY" else f"{m:02d}/20{yy}"


def ref_number(r):  # NN/NN that cannot be a month/year: not a date
    return f"{r.randint(13, 98)}/{r.randint(10, 99)}"


FIELD_HEAD = ["Ödəniş forması", "Kart məlumatları", "Abunəlik üçün ödəniş", "Onlayn sifariş: ödəniş hissəsi",
              "Bank kartının əlavə edilməsi"]
FIELD_CARD = ["Kart nömrəsi", "Kartın nömrəsi", "Ödəniş kartı", "Kart"]
FIELD_EXP = ["Son istifadə", "Etibarlılıq müddəti", "Bitmə tarixi", "Kartın müddəti", "MM/YY", "Ay/il"]
FIELD_CVV = ["CVV", "CVC", "Təhlükəsizlik kodu"]
FIELD_END = ["Məlumatlar yalnız bu ödəniş üçün istifadə olunur.", "Təsdiq kodu telefonunuza göndəriləcək.",
             "Ödəniş bir iş günü ərzində hesabınızda görünəcək.", "Formanı yoxlayıb təsdiq düyməsini basın."]

PROSE = [  # {c} card, {e} expiry
    "Müştərinin {c} kartı {e} tarixinədək etibarlıdır, ona görə yeni kart sifariş edilməyib.",
    "Ödəniş alınmadı: {c} kartının son istifadə tarixi ({e}) artıq keçib.",
    "Kart sahibi zəng zamanı {c} nömrəsini və {e} bitmə tarixini diktə etdi.",
    "Sifarişdə {c} nömrəli kart qeyd olunub, son istifadə {e}.",
    "Hesabda saxlanılan {c} kartının müddəti {e} olaraq yadda saxlanılıb, abunəlik ondan çıxılır.",
]
PROSE_INTRO = ["Müraciət üzrə qısa qeyd.", "Dəstək xidmətinin cavabı.", "Ödəniş şöbəsinin qeydi.",
               "Zəng barədə məlumat."]
PROSE_END = ["Müştəriyə SMS ilə məlumat verilib.", "Məsələ bağlanıb.", "Növbəti ödəniş ayın sonunda olacaq.",
             "Əlavə yoxlama tələb olunmur."]

RECORD = [  # (header or None, line); {k} CVV, always present in records
    ("Kart | MM/YY | CVV", "{c} | {e} | {k}"),
    (None, "kart={c}; bitir={e}; cvv={k}"),
    (None, "{c} / son istifadə {e} / CVC {k}"),
    ("Kart nömrəsi; Ay/il; Kod", "{c}; {e}; {k}"),
    (None, "Ödəniş: kart {c}, müddət {e}, kod {k}"),
]
RECORD_INTRO = ["Ödəniş jurnalından sətir:", "İxrac edilmiş qeyd:", "Uğursuz əməliyyat:", "Sistemdən çıxarış:"]

CONTROL = ["Müraciət № {x} ilə qeydə alınıb.", "Qərar № {x} əsasında.", "Arxiv qovluğu {x}."]


def _put(text, piece, spans, ent=None):
    """Append `piece` (with {c}/{e}/{k} slots filled from ent) to text, recording spans."""
    out = text
    for part in re.split(r"(\{[cek]\})", piece):
        if part in ("{c}", "{e}", "{k}"):
            v, span = ent[part]
            span = dict(span, start=len(out), end=len(out) + len(v))
            spans.append(span)
            out += v
        else:
            out += part
    return out


def build(seed: int) -> list[dict]:
    r = random.Random(seed)
    forbidden = BP.load_forbidden()
    rows: list[dict] = []
    for form in FORMS:
        for layout in LAYOUTS:
            for i in range(PER_CELL):
                c = next(x for x in (BP.card(r) for _ in range(50)) if x not in forbidden)
                e = next(x for x in (expiry(r, form) for _ in range(50)) if x not in forbidden)
                k = BP.cvv(r)
                slots = {"{c}": (c, {"label": "PAYMENT_CARD_NUMBER"}),
                         "{e}": (e, {"label": "DATE", "form": form, "layout": layout, "cell": f"{form}|{layout}"}),
                         "{k}": (k, {"label": "CARD_SECURITY_CODE"})}
                ents: list[dict] = []
                if layout == "field":
                    with_cvv = i % 2 == 0
                    lines = [r.choice(FIELD_HEAD), f"{r.choice(FIELD_CARD)}: {{c}}", f"{r.choice(FIELD_EXP)}: {{e}}"]
                    if with_cvv:
                        lines.append(f"{r.choice(FIELD_CVV)}: {{k}}")
                    lines.append(r.choice(FIELD_END))
                    text = _put("", "\n".join(lines), ents, slots)
                elif layout == "prose":
                    text = _put("", f"{r.choice(PROSE_INTRO)} {PROSE[i % len(PROSE)]} {r.choice(PROSE_END)}", ents, slots)
                else:
                    head, line = RECORD[i % len(RECORD)]
                    text = _put("", r.choice(RECORD_INTRO) + "\n" + (head + "\n" if head else "") + line, ents, slots)
                ctl = []
                if i % 3 == 0:
                    x = ref_number(r)
                    pre, post = r.choice(CONTROL).split("{x}")
                    text += ("\n" if layout != "prose" else " ") + pre
                    ctl.append({"start": len(text), "end": len(text) + len(x), "resembles": "DATE", "kind": "number_slash"})
                    text += x + post
                rec = {"id": f"{FAMILY}_{len(rows) + 1:03d}", "text": text, "lang": "az", "family": FAMILY,
                       "role": f"{form}|{layout}", "entities": sorted(ents, key=lambda s: s["start"])}
                if ctl:
                    rec["controls"] = ctl
                rows.append(rec)
    return rows


EXP_RE = re.compile(r"(0[1-9]|1[0-2])/(\d{2}|20\d{2})")


def check(rows: list[dict]) -> list[str]:
    bad = []
    for x in rows:
        t = x["text"]
        for s in x["entities"] + x.get("controls", []):
            if not (0 <= s["start"] < s["end"] <= len(t)) or t[s["start"]:s["end"]] != t[s["start"]:s["end"]].strip():
                bad.append(f"{x['id']}: bad span")
        exp = [s for s in x["entities"] if s["label"] == "DATE"]
        cards = [s for s in x["entities"] if s["label"] == "PAYMENT_CARD_NUMBER"]
        if len(exp) != 1 or len(cards) != 1:
            bad.append(f"{x['id']}: needs one card and one expiry")
            continue
        if not EXP_RE.fullmatch(t[exp[0]["start"]:exp[0]["end"]]):
            bad.append(f"{x['id']}: expiry shape")
        digits = t[cards[0]["start"]:cards[0]["end"]].replace(" ", "")
        if BP._luhn(digits[:-1]) != digits[-1]:
            bad.append(f"{x['id']}: card checksum")
        for s in x.get("controls", []):
            if EXP_RE.fullmatch(t[s["start"]:s["end"]]):
                bad.append(f"{x['id']}: control reads as an expiry")
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=78)
    ap.add_argument("--out", type=Path, default=HERE)
    a = ap.parse_args(argv)
    rows = build(a.seed)
    problems = check(rows)
    (a.out / f"{FAMILY}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows), encoding="utf-8")
    print(f"{FAMILY}: {len(rows)} documents ({len(FORMS)} forms x {len(LAYOUTS)} layouts x {PER_CELL}), "
          f"{sum(1 for x in rows for s in x['entities'] if s['label'] == 'CARD_SECURITY_CODE')} CVVs, "
          f"{sum(len(x.get('controls', [])) for x in rows)} NN/NN controls; problems: {len(problems)}")
    for p in problems[:20]:
        print("  ", p)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
