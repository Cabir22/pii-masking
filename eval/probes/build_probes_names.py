"""Build the given-name shape probes (D-38 step 1): eval/probes/<family>.jsonl.

    python eval/probes/build_probes_names.py [--seed 35] [--validators scripts]

The four constructions in which Run B missed real given names (counted on the real-text
set; constructions only, no real text, values or document details):

  names_list_lines      one-name-per-line lists in "Surname Given Father oğlu/qızı" order
                        (award, roster and order lists); the father's name is GIVENNAME with
                        entity field role=patronymic, so it is reported apart
  names_after_role      a name right after a lowercase title, job or role word
  names_signature       a name alone on its own line at the end of a letter or notice
  names_sentence_start  a name at the start of a sentence

Synthetic only (A2.5 / RC7): every sentence, name and role below was written for these probes.
Nothing comes from the real-text set, the generator's pools, frames or value makers, the
training corpus or the shadow set. Controls are capitalised non-person words in the same
position (department or product lines in a list, an organisation after a role word, a
department on the signature line, a capitalised common noun at the start of a sentence).
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
from build_probes_runb import marked  # noqa: E402

FAMILIES = ["names_list_lines", "names_after_role", "names_signature", "names_sentence_start"]

MALE = ["Anar", "Bəhruz", "Cavanşir", "Eldəniz", "Həbib", "Kənan", "Lətif", "Mübariz", "Nurlan", "Oqtay",
        "Pərviz", "Rüstəm", "Sənan", "Ülvi", "Vaqif", "Yaşar", "Zaur", "Elmar", "Fikrət", "Qabil", "Rauf", "Şahlar"]
FEMALE = ["Afət", "Billurə", "Dilarə", "Elnarə", "Fərqanə", "Gülşən", "Həcər", "İlahə", "Kəmalə", "Mehparə",
          "Nüşabə", "Pərvanə", "Sevil", "Şəbnəm", "Təranə", "Ülviyyə", "Xumar", "Zemfira"]
# surname stems: male form, female form
SURNAMES = [("Ağayev", "Ağayeva"), ("Bədəlov", "Bədəlova"), ("Cəlilov", "Cəlilova"), ("Dadaşov", "Dadaşova"),
            ("Eyvazov", "Eyvazova"), ("Fərzəliyev", "Fərzəliyeva"), ("Həsənzadə", "Həsənzadə"),
            ("İsmixanov", "İsmixanova"), ("Kərimzadə", "Kərimzadə"), ("Mehdiyev", "Mehdiyeva"),
            ("Novruzov", "Novruzova"), ("Orucəliyev", "Orucəliyeva"), ("Paşayev", "Paşayeva"), ("Qasımlı", "Qasımlı"),
            ("Rüstəmov", "Rüstəmova"), ("Sadıqov", "Sadıqova"), ("Şirinov", "Şirinova"), ("Tağıyev", "Tağıyeva"),
            ("Xəlilov", "Xəlilova"), ("Yusifzadə", "Yusifzadə"), ("Zeynalov", "Zeynalova")]
ROLES = ["baş mühasib", "şöbə müdiri", "həkim", "müəllimə", "sürücü", "kassir", "katibə", "operator", "mühəndis",
         "direktor müavini", "layihə rəhbəri", "tibb bacısı", "dispetçer", "hüquqşünas", "satış meneceri", "laborant"]
POSITIONS = ["Direktor", "Şöbə müdiri", "Baş mühasib", "İcraçı direktor", "Layihə koordinatoru", "Sədr"]

LIST_HEADS = [
    "Bu il keçirilmiş peşəkar ustalıq müsabiqəsinin qalibləri:",
    "Növbəti tədris ilində bu müəllimlərə əlavə dərs saatı verilsin:",
    "Komandanın əsas heyətinə daxil edilən idmançılar:",
    "Mükafat fondundan pul mükafatı alacaq əməkdaşlar:",
    "Sınaq müddətini uğurla başa vuran yeni işçilər:",
    "Könüllü yardım aksiyasında fərqlənən tələbələr:",
]
LIST_TAILS = ["Siyahı kadrlar xidmətində saxlanılır.", "Mükafatlar ay sonunda veriləcək.", "",
              "Əlavə məlumat üçün idarəyə müraciət edin."]
LIST_CONTROLS = ["Maliyyə Nəzarəti Şöbəsi", "Təhsil Proqramları Mərkəzi", "Kəhrəba Çay Dəsti", "Gümüş Qələm Mükafatı"]

AFTER_ROLE = [
    "Dünənki görüşdə {r} {n} yeni qrafiki təqdim etdi.",
    "Hesabatı {r} {n} hazırlayıb.",
    "Səhər növbəsini {r} {n} qəbul edəcək.",
    "Müraciətinizə {r} {n} baxacaq.",
    "Bu barədə {r} {n} əlavə izahat verdi.",
    "Təlimi {r} {n} aparıb.",
    "Sənədləri {r} {n} imzalamalıdır.",
    "Yoxlama zamanı {r} {n} də iştirak edirdi.",
]
AFTER_ROLE_CONTROLS = [
    "Dünənki görüşdə {r} <<Yaşıl Vadi|GIVENNAME|org_after_role>> layihəsini təqdim etdi.",
    "Hesabatı {r} <<Mavi Liman|GIVENNAME|org_after_role>> şirkəti üçün hazırlayıb.",
    "Səhər növbəsini {r} <<Şimal Terminalı|GIVENNAME|org_after_role>> üzrə qəbul edəcək.",
    "Müraciətinizə {r} <<Qızıl Açar|GIVENNAME|org_after_role>> xidmətində baxacaq.",
]

LETTERS = [
    "Sizi növbəti həftə keçiriləcək illik iclasa dəvət edirik. Gündəlik ayrıca göndəriləcək.",
    "Təqdim etdiyiniz təklif nəzərdən keçirildi və qəbul olundu. Müqavilənin layihəsi əlavə olunur.",
    "Anbarda inventarizasiya aparılacağı üçün cümə günü qəbul olmayacaq. Narahatlığa görə üzr istəyirik.",
    "Ödənişin gecikməsi ilə bağlı məktubunuzu aldıq. Məsələ beş iş günü ərzində həll ediləcək.",
    "Yeni iş qrafiki gələn aydan qüvvəyə minir. Suallarınızı şöbəyə yazılı göndərə bilərsiniz.",
]
SIG_CONTROLS = ["Kadrlar şöbəsi", "İnzibati heyət", "Mühasibatlıq xidməti", "Təchizat bölməsi"]

SENT_START = [
    "{n} dünən yeni vəzifəyə başladı.",
    "{n} bu səhər arxivə müraciət etdi.",
    "Toplantı uzun çəkdi. {n} axırda qısa çıxış etdi.",
    "{n} sənədləri vaxtında təhvil verib.",
    "Hamı gözləyirdi. {n} isə gecikdi.",
    "{n} layihənin ikinci mərhələsinə rəhbərlik edəcək.",
    "Qeydiyyat bitdi. {n} siyahının sonunda idi.",
    "{n} məzuniyyətdən qayıdıb.",
]
SENT_CONTROLS = ["<<Hesabat|GIVENNAME|common_noun>> dünən təsdiqləndi.", "<<Anbar|GIVENNAME|common_noun>> bu səhər açıldı.",
                 "Toplantı uzun çəkdi. <<Qərar|GIVENNAME|common_noun>> axırda qəbul olundu.",
                 "<<Sənədlər|GIVENNAME|common_noun>> vaxtında təhvil verilib.", "Hamı gözləyirdi. <<Avtobus|GIVENNAME|common_noun>> isə gecikdi.",
                 "<<Layihə|GIVENNAME|common_noun>> ikinci mərhələyə keçib."]


def person(r: random.Random):
    male = r.random() < 0.55
    given = r.choice(MALE if male else FEMALE)
    father = r.choice([m for m in MALE if m != given])
    return given, r.choice(SURNAMES)[0 if male else 1], father, "oğlu" if male else "qızı"


def name_mark(given, surname, order="gs", full=True):
    g, s = f"[[{given}|GIVENNAME]]", f"[[{surname}|SURNAME]]"
    if not full:
        return g
    return f"{g} {s}" if order == "gs" else f"{s} {g}"


def build(r: random.Random, out: dict):
    def add(fam, pair, role, rendered, **extra):
        text, ents, hns, ctl = rendered
        rows = out.setdefault(fam, [])
        rec = {"id": f"{fam}_{len(rows) + 1:03d}", "text": text, "lang": "az", "family": fam, "pair": pair,
               "role": role, "entities": ents}
        if hns:
            rec["hard_negatives"] = hns
        if ctl:
            rec["controls"] = ctl
        rec.update(extra)
        rows.append(rec)

    # 1. one-name-per-line lists: Surname Given Father oğlu/qızı
    for i in range(14):
        lines = []
        for _ in range(r.randint(3, 5)):
            g, s, f, w = person(r)
            lines.append(f"[[{s}|SURNAME]] [[{g}|GIVENNAME|role=given]] [[{f}|GIVENNAME|role=patronymic]] {w}")
        if i % 3 == 2:   # a non-person line in the same list
            lines.insert(r.randint(1, len(lines)), f"<<{LIST_CONTROLS[(i // 3) % len(LIST_CONTROLS)]}|SURNAME|non_person_line>>")
        tail = LIST_TAILS[i % len(LIST_TAILS)]
        doc = LIST_HEADS[i % len(LIST_HEADS)] + "\n" + "\n".join(lines) + ("\n" + tail if tail else "")
        add("names_list_lines", i, "list", marked(doc))

    # 2. a name right after a lowercase title, job or role word
    for i in range(20):
        g, s, _, _ = person(r)
        full = i % 3 != 0
        doc = AFTER_ROLE[i % len(AFTER_ROLE)].format(r=ROLES[i % len(ROLES)], n=name_mark(g, s, full=full))
        add("names_after_role", i, "full_name" if full else "given_only", marked(doc))
    for i, t in enumerate(AFTER_ROLE_CONTROLS):
        add("names_after_role", 100 + i, "control", marked(t.format(r=ROLES[(i * 5) % len(ROLES)])))

    # 3. a name alone on its own line (signature)
    for i in range(20):
        g, s, _, _ = person(r)
        order = "sg" if i % 4 == 3 else "gs"
        sig = name_mark(g, s, order=order)
        extra_line = "\n" + POSITIONS[i % len(POSITIONS)] if i % 2 == 0 else ""
        doc = LETTERS[i % len(LETTERS)] + "\n" + sig + extra_line
        add("names_signature", i, "surname_first" if order == "sg" else "given_first", marked(doc))
    for i, c in enumerate(SIG_CONTROLS):
        add("names_signature", 100 + i, "control", marked(LETTERS[(i + 2) % len(LETTERS)] + f"\n<<{c}|GIVENNAME|department_signature>>"))

    # 4. a name at the start of a sentence
    for i in range(20):
        g, s, _, _ = person(r)
        full = i % 2 == 0
        doc = SENT_START[i % len(SENT_START)].format(n=name_mark(g, s, full=full))
        add("names_sentence_start", i, "full_name" if full else "given_only", marked(doc))
    for i, c in enumerate(SENT_CONTROLS):
        add("names_sentence_start", 100 + i, "control", marked(c))


def run(seed: int, validators: str | None = None):
    out: dict = {}
    build(random.Random(seed), out)
    problems = BP.check(out, validators)
    for fam, rows in out.items():
        for rec in rows:
            if "[[" in rec["text"] or "<<" in rec["text"]:
                problems.append(f"{rec['id']}: mark left in text")
    return out, problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=35)
    ap.add_argument("--validators", default=None, help="directory containing piigen/ (checking only)")
    ap.add_argument("--out", type=Path, default=HERE)
    args = ap.parse_args(argv)
    out, problems = run(args.seed, args.validators)
    for fam in FAMILIES:
        (args.out / f"{fam}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out[fam]),
                                               encoding="utf-8")
        rows = out[fam]
        print(f"{fam:22s} {len(rows):3d} docs  {sum(len(x['entities']) for x in rows):3d} gold  "
              f"{sum(len(x.get('controls', [])) for x in rows):3d} controls")
    print("problems:", len(problems))
    for p in problems[:20]:
        print("  ", p)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
