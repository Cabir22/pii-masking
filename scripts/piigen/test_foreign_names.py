"""P2-15 (D-23d): foreign given names and surnames for a minority of persons.

    python scripts/piigen/test_foreign_names.py
"""
from __future__ import annotations

import collections
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.config import GeneratorConfig  # noqa: E402
from piigen.llm.quality import find_invented_pii  # noqa: E402
from piigen.llm.specs import NAME_SHAPE_ROLES, SpecSampler  # noqa: E402
from piigen.locales import LOCALES  # noqa: E402
from piigen.locales import az as AZ  # noqa: E402
from piigen.locales.build_foreign_names import AZ_WORDS, SHARES, _template_words  # noqa: E402
from piigen.resolver import _common_words, find_unlabelled_planned, match_key  # noqa: E402
from piigen.targeted import suffix as S  # noqa: E402
from piigen.values import ValueFactory, ValuePool  # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond, msg, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(msg + (f"  [{detail!r}]"[:300] if detail is not None else ""))


FN = AZ.FOREIGN_NAMES
GIVEN = set(FN.given_names())
SURNAMES = set(FN.surname_forms())


def origin_of(name: str, kind: str) -> set:
    table = {"given_m": FN.given_m, "given_f": FN.given_f}
    if kind == "surname":
        return {o for o, (pairs, _w) in FN.surnames.items() if any(name in p for p in pairs)}
    return {o for o, (names, _w) in table[kind].items() if name in names}


def canonical(factory, value: str) -> str:
    """The name a recorded variant spells, when that is a foreign name. An
    Azerbaijani name's spelling can equal a foreign name (`Samad` is Persian
    and the English spelling of `Saməd`); that one stays as written."""
    canon, kind = factory.name_variants.get(value, (value, ""))
    return canon if kind == "cyrillic" or canon in GIVEN or canon in SURNAMES else value


# the file: provenance header, origins, kinds
path = ROOT / "scripts/piigen/locales/data/foreign_names.txt"
header = [l for l in path.read_text(encoding="utf-8").splitlines() if l.startswith("#")]
check(any("Wikidata" in l for l in header) and any("none from the benchmark" in l for l in header),
      "the file header names its public source and says it is not the benchmark")
check(FN.origins == sorted(SHARES), "all eight origins have male, female and family names",
      FN.origins)
for o in FN.origins:
    check(len(FN.given_m[o][0]) >= 30 and len(FN.given_f[o][0]) >= 15 and len(FN.surnames[o][0]) >= 50,
          f"{o}: enough names", (len(FN.given_m[o][0]), len(FN.given_f[o][0]), len(FN.surnames[o][0])))
for name in ("Sergey", "Mehmet", "Giorgi", "John"):
    check(name in GIVEN, f"common foreign given name {name}")
check(("Petrov", "Petrova") in FN.surnames["ru"][0] and ("Yılmaz", "Yılmaz") in FN.surnames["tr"][0],
      "Petrov/Petrova and Yılmaz in the surname pool")
shape = re.compile(r"^[A-ZÇƏĞIİÖŞÜ][a-zçəğıiöşüw]{2,}$")
check(not [n for n in GIVEN | SURNAMES if not shape.match(n.replace("W", "A"))],
      "one word, a capital then Azerbaijani letters or w (no hyphen, apostrophe, é)",
      [n for n in GIVEN | SURNAMES if not shape.match(n.replace("W", "A"))][:5])
common = (_common_words() | {match_key(c) for c in AZ.CITIES + AZ.SETTLEMENTS}
          | {match_key(w) for w in AZ_WORDS} | _template_words())
check(not [n for n in GIVEN | SURNAMES if match_key(n) in common],
      "no foreign name is an Azerbaijani word (stopword, homograph, template word, AZ_WORDS) or city",
      [n for n in GIVEN | SURNAMES if match_key(n) in common][:5])
ru_fem = [f for m, f in FN.surnames["ru"][0] if m.endswith(("ov", "ev", "in"))]
check(ru_fem and all(f.endswith("a") for f in ru_fem), "Russian -ov/-ev/-in surnames have the -a feminine")
check(all(m == f for o in FN.origins if o != "ru" for m, f in FN.surnames[o][0]),
      "other origins' surnames are the same for women")
check(FN.cyrillic.get("Sergey") == "Сергей" and FN.cyrillic.get("Petrova") == "Петрова",
      "Russian names keep their Cyrillic form")

# frozen consumers keep the Azerbaijani pools
loc = LOCALES["az"]
check(loc.first_names_m is AZ.FIRST_M and loc.first_names_f is AZ.FIRST_F
      and loc.surname_stems is AZ.SURNAME_STEMS and len(AZ.FIRST_M) > 5000,
      "first_names/surname_stems are still the Azerbaijani pools (the frozen pii_guard reads them)")

# draws: ~13% foreign, origins by share, Azerbaijani the majority
f = ValueFactory(random.Random(7), ValuePool(state_path=None))
N = 20000
given = [f.givenname("az") for _ in range(N)]
foreign = [g for g in given if g in GIVEN and g not in AZ.FIRST_M and g not in AZ.FIRST_F]
share = len(foreign) / N
check(0.09 <= share <= 0.16, "about 13% of given names are foreign (less the shared ones)", share)
origins = collections.Counter(f.name_origin("az") or "az" for _ in range(N))
check(abs(origins["az"] / N - (1 - ValueFactory.FOREIGN_NAME_RATE)) < 0.01
      and 0.10 <= ValueFactory.FOREIGN_NAME_RATE <= 0.15,
      "name_origin: 87% Azerbaijani, 13% foreign", origins["az"] / N)
fshare = {o: origins[o] / (N - origins["az"]) for o in SHARES}
check(all(abs(fshare[o] - SHARES[o]) < 0.03 for o in SHARES), "origins drawn by their shares", fshare)

# one person: the given name and surname share an origin and a gender
bad = []
for _ in range(3000):
    o = f.name_origin("az")
    if not o:
        continue
    female = random.random() < 0.5
    g = f.givenname("az", female=female, origin=o)
    s = f.surname("az", female=female, origin=o)
    g, s = canonical(f, g), canonical(f, s)
    if o not in origin_of(g, "given_f" if female else "given_m") or o not in origin_of(s, "surname"):
        bad.append((o, g, s))
    elif o == "ru" and female and not any(s == fem for _m, fem in FN.surnames["ru"][0]):
        bad.append((o, g, s))
check(not bad, "given name and surname of one person come from the same origin and gender", bad[:3])

# spellings: a Russian name's variant is its Russian form; no invented transliteration
check(f.name_spellings("Sergey") == {"cyrillic": "Сергей"}, "Sergey's variant is Сергей",
      f.name_spellings("Sergey"))
check(f.name_spellings("John") == {}, "John has no variant (never Жохн)", f.name_spellings("John"))
check(f.name_spellings("Yılmaz") == {"english": "Yilmaz"},
      "a Turkish name's variant is its English-keyboard spelling", f.name_spellings("Yılmaz"))
f.name_variants["Сергей"] = ("Sergey", "cyrillic")
check(f.latin_spelling("Сергей") == "Sergey", "an inflected Cyrillic variant is written in Latin")

# the LLM path: briefs plan foreign persons, one origin per document
cfg = GeneratorConfig()
cfg.edge_case_rate = 0.0
sampler = SpecSampler(cfg, ValueFactory(random.Random(7), ValuePool(state_path=None)),
                      random.Random(11))
mixed = n_foreign = n_names = 0
for i in range(3000):
    spec = sampler.sample(i)
    # the brief's own person; a D-39b name construction plans separate people,
    # each paired on its own (test_name_shapes.py)
    names = [(e.label, e.value) for e in spec.entities if e.label in ("GIVENNAME", "SURNAME")
             and e.role not in NAME_SHAPE_ROLES]
    canon = [(lab, canonical(sampler.factory, v)) for lab, v in names]
    n_names += len(canon)
    fl = [v in (GIVEN if lab == "GIVENNAME" else SURNAMES)
          and v not in AZ.FIRST_M and v not in AZ.FIRST_F for lab, v in canon]
    n_foreign += sum(fl)
    gs = [v for lab, v in canon if lab == "GIVENNAME" and v in GIVEN
          and v not in AZ.FIRST_M and v not in AZ.FIRST_F]
    ss = [v for lab, v in canon if lab == "SURNAME"]
    # an Azerbaijani name's spelling can equal a foreign name (`Khatuna` is
    # Xatunə's English spelling and a Georgian name): such a brief says
    # nothing about pairing
    spelled = any(sampler.factory.name_variants.get(v, ("", ""))[1] not in ("", "cyrillic")
                  for _lab, v in names)
    if gs and ss and not spelled:
        og = origin_of(gs[0], "given_m") | origin_of(gs[0], "given_f")
        if not any(origin_of(s, "surname") & og for s in ss):
            mixed += 1
check(n_names and 0.09 <= n_foreign / n_names <= 0.16,
      "LLM briefs: about 10-15% of planned names are foreign", n_foreign / max(n_names, 1))
check(mixed == 0, "LLM briefs: a foreign given name comes with a surname of its origin", mixed)

# every foreign name takes every case of its label
bad = []
for label, names in (("GIVENNAME", GIVEN), ("SURNAME", SURNAMES)):
    for n in sorted(names):
        for case in sorted(S.APPLIES[label]):
            try:
                S.inflect(n, case, label)
            except S.NotInflectable:
                bad.append((n, case))
check(not bad, "the renderer inflects every foreign name in every case", bad[:5])
check(S.inflect("Johnson", "dat", "SURNAME") == "Johnsona" and
      S.inflect("Beridze", "gen", "SURNAME") == "Beridzenin",
      "suffixes follow the written letters", (S.inflect("Johnson", "dat", "SURNAME"),
                                              S.inflect("Beridze", "gen", "SURNAME")))

# the checks know them: a planned foreign name left unlabelled, an invented one
text = "Sergeyə zəng edin."
check(find_unlabelled_planned(text, [], [("GIVENNAME", "Sergey")]),
      "an unlabelled inflected planned foreign name is found")
inv = find_invented_pii("Dünən Anna Petrova da gəldi.", [])
check(any(x["label"] == "GIVENNAME" and x["text"] == "Anna Petrova" for x in inv),
      "the invented-name sweep finds an unlabelled foreign person", inv)

print(f"PASSED {PASS}   FAILED {FAIL}")
for x in FAILURES:
    print("  FAIL:", x)
sys.exit(1 if FAIL else 0)
