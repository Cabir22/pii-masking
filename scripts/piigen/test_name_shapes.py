"""D-39b acceptance check: the name constructions in the LLM briefs.

  * only the published-text genres plan a name construction (az briefs, not
    PII-free or edge-case ones); other types are untouched;
  * the note gives the exact text of the construction, built from the planned
    values; a patronymic line is `Surname Given Father oğlu/qızı`; names are in
    Latin spelling; the father's name is a man's;
  * the planned names are left out of the label mix the run monitor watches
    (`steering_labels`), so batch 6 cannot trip the 2.5x stop;
  * the brief hints those names as bare, not with the case-ending hint;
  * a model that follows the note passes the pipeline's own gates
    (`assemble_document`), with the father's name a GIVENNAME and `oğlu`/`qızı`
    outside every span.

    python scripts/piigen/test_name_shapes.py
"""
from __future__ import annotations

import collections
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.anchors import ANCHOR_REQUIRED                            # noqa: E402
from piigen.config import GeneratorConfig                              # noqa: E402
from piigen.llm import specs as S                                      # noqa: E402
from piigen.llm.dspy_generate import build_fields                      # noqa: E402
from piigen.llm.pipeline import assemble_document                      # noqa: E402
from piigen.targeted import builder as B                               # noqa: E402
from piigen.values import ValueFactory, ValuePool                      # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []
SHAPES = set(S._NAME_SHAPES_ROOM)


def check(cond: bool, msg: str, detail=None) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(msg + (f"  [{detail}]" if detail is not None else ""))


def sampler(doc_types=None, seed=5, edge=0.0, neg=0.0) -> S.SpecSampler:
    cfg = GeneratorConfig()
    cfg.doc_types = doc_types
    cfg.edge_case_rate = edge
    cfg.negative_only_rate = neg
    return S.SpecSampler(cfg, ValueFactory(random.Random(seed), ValuePool(state_path=None)),
                         random.Random(seed))


GENRES = sorted(S.NAME_SHAPE_DOC_TYPES)
# varied, digit-free filler: the quality gate rejects a repeated 10-word phrase
CLAUSES = [c.replace("{ref}", "").strip() for c in B.CLERICAL_CLAUSES if "{ref}" not in c]


def model_output(spec: S.DocumentSpec, rng: random.Random) -> str:
    """What a model that follows the scenario note writes (plus the other
    planned values after a labelled word)."""
    names = [e for e in spec.entities if e.role in S.NAME_SHAPE_ROLES]
    g = [e.value for e in names if e.label == "GIVENNAME" and e.role != "patronymic_father"]
    s = [e.value for e in names if e.label == "SURNAME"]
    lines = [ln for ln in spec.name_note.split("\n") if ln.endswith(("oğlu", "qızı"))]
    shape = spec.name_shape
    if shape == "patronymic_list":
        body = "Rəsmi siyahı:\n" + "\n".join(f"{i + 1}. {ln}" for i, ln in enumerate(lines))
    elif shape == "patronymic_sentence":
        body = " ".join(f"Müraciəti {ln} imzalayıb." for ln in lines)
    elif shape == "role_word":
        body = " ".join(f"İclasa direktor {a} {b} sədrlik edib." for a, b in zip(g, s))
    elif shape == "signature":
        body = ""
    elif shape == "sentence_initial":
        body = f"{g[0]} {s[0]} müsabiqənin qalibi elan edilib."
    else:
        body = f"«Yeni Üfüq» MMC-ni {g[0]} {s[0]} təmsil edir."
    others = " ".join(f"Tarix: {e.value}." if e.label == "DATE" else f"{e.value}."
                      for e in spec.entities if e.role not in S.NAME_SHAPE_ROLES)
    filler = " ".join(f"{c[0].upper()}{c[1:]}." for c in rng.sample(CLAUSES, 14))
    if shape == "signature":
        return f"{filler} {others}\n\nBaş mühasib\n{g[0]} {s[0]}"
    return f"{body} {filler} {others}"


def test_planning() -> None:
    every = sampler(None, edge=0.15, neg=0.1)
    specs = [every.sample(i) for i in range(4000)]
    planned = [x for x in specs if x.name_shape]
    check(planned and all(x.doc_type in S.NAME_SHAPE_DOC_TYPES and x.lang == "az" and not x.negative_only
                          and x.edge_case is None for x in planned),
          "only az published-text briefs plan a name construction")
    check(not any(e.role in S.NAME_SHAPE_ROLES for x in specs if not x.name_shape for e in x.entities),
          "no name role without a construction")
    check(not any(x.name_shape for x in specs if x.doc_type not in S.NAME_SHAPE_DOC_TYPES),
          "other document types are untouched")
    genre = [x for x in specs if x.doc_type in S.NAME_SHAPE_DOC_TYPES and x.edge_case is None
             and not x.negative_only]
    for want, kinds in ((0.8, ("official_notice", "court_announcement", "procurement_announcement")),
                        (0.5, ("news_article", "press_release", "legal_notice", "government_form",
                               "court_filing"))):
        some = [x for x in genre if x.doc_type in kinds]
        rate = sum(bool(x.name_shape) for x in some) / len(some)
        check(abs(rate - want) < 0.12, f"about {want:.0%} of {'/'.join(k[:5] for k in kinds)} briefs",
              round(rate, 3))
    check({x.name_shape for x in planned} == SHAPES, "every construction is planned",
          dict(collections.Counter(x.name_shape for x in planned)))
    room = {x.name_shape for x in planned if x.band in S._PEOPLE_BY_BAND}
    tight = {x.name_shape for x in planned if x.band not in S._PEOPLE_BY_BAND}
    check("patronymic_list" in room and "patronymic_list" not in tight and "after_org" not in tight,
          "a list and an organisation need room: not in very short and short documents")


def test_notes() -> None:
    s = sampler(GENRES)
    specs = [x for x in (s.sample(i) for i in range(1500)) if x.name_shape]
    bad = []
    for x in specs:
        names = [e for e in x.entities if e.role in S.NAME_SHAPE_ROLES]
        if not all(e.value in x.name_note for e in names if e.role != "patronymic_father"
                   or x.name_shape.startswith("patronymic")):
            bad.append((x.name_shape, "a planned name is not in the note"))
        if re.search(r"[Ѐ-ӿ]", x.name_note):
            bad.append((x.name_shape, "Cyrillic in the note"))
    check(not bad, "the note holds every planned name, in Latin spelling", bad[:2])
    patro = [x for x in specs if x.name_shape.startswith("patronymic")]
    shape_ok = True
    for x in patro:
        by = collections.defaultdict(list)
        for e in x.entities:
            by[e.role].append(e)
        lines = [ln for ln in x.name_note.split("\n") if ln.endswith(("oğlu", "qızı"))]
        sur, giv = [e.value for e in by["list_person"] + by["named_person"] if e.label == "SURNAME"], \
                   [e.value for e in by["list_person"] + by["named_person"] if e.label == "GIVENNAME"]
        dads = [e.value for e in by["patronymic_father"]]
        shape_ok &= (len(lines) == len(sur) == len(giv) == len(dads)
                     and all(ln.split()[:3] == [a, b, c] for ln, a, b, c in zip(lines, sur, giv, dads)))
    check(patro and shape_ok, "a patronymic line is `Surname Given Father oğlu/qızı`", len(patro))
    check(all(e.role == "patronymic_father" for x in patro for e in x.entities
              if e.value in [ln.split()[2] for ln in x.name_note.split("\n") if ln.endswith(("oğlu", "qızı"))]),
          "the father's name carries its own role")
    fathers = {e.value for x in patro for e in x.entities if e.role == "patronymic_father"}
    loc = s.factory.loc("az")
    male, female = set(loc.first_names_m), set(loc.first_names_f)
    # D-40a: men's names that are not also in the women's pool, in its own spelling
    check(fathers and not (fathers & female) and all(v in male for v in fathers),
          "fathers are men's names not in the women's pool (D-40a)",
          sorted(fathers - male)[:3] + sorted(fathers & female)[:3])
    # given name and father exactly as the pools spell them (a surname can be
    # both a pool spelling and another name's English form, `Nasirov`, so the
    # pool membership of given names is the exact test)
    lines_all = [ln for x in patro for ln in x.name_note.split("\n") if ln.endswith(("oğlu", "qızı"))]
    off = [w for ln in lines_all for w in ln.split()[1:3] if w not in male | female]
    check(not off, "a patronymic line uses the pool's own spelling (D-40a)", off[:3])


def test_people() -> None:
    """Each planned person on its own: gender agrees (given name, surname,
    oğlu/qızı) and a foreign given name comes with a surname of its origin.
    The old per-brief checks (test_llm_augment, test_foreign_names) leave
    these people out, as a construction plans several."""
    from piigen.locales import az as AZ
    fn = AZ.FOREIGN_NAMES
    origin = lambda name, kind: ({o for o, (pairs, _w) in fn.surnames.items() if any(name in p for p in pairs)}  # noqa: E731
                                 if kind == "surname" else
                                 {o for t in (fn.given_m, fn.given_f) for o, (ns, _w) in t.items() if name in ns})
    s = sampler(GENRES, seed=21)
    f = s.factory
    male, female = set(AZ.FIRST_M), set(AZ.FIRST_F)
    gender_bad, origin_bad, people = [], [], 0
    for x in (s.sample(i) for i in range(3000)):
        ents = [e for e in x.entities if e.role in ("list_person", "named_person")]
        lines = [ln for ln in x.name_note.split("\n") if ln.endswith(("oğlu", "qızı"))]
        for k in range(0, len(ents), 2):                     # [SURNAME, GIVENNAME] per person
            sur, giv = ents[k].value, ents[k + 1].value
            canon = lambda v: f.name_variants.get(v, (v, ""))[0]     # noqa: E731
            people += 1
            gg = "m" if canon(giv) in male - female else "f" if canon(giv) in female - male else None
            sg = "f" if canon(sur).endswith(("ova", "yeva")) else "m" if canon(sur).endswith(("ov", "yev")) else None
            pw = None
            line = next((ln for ln in lines if ln.split()[:2] == [sur, giv]), None)
            if line:
                pw = "f" if line.endswith("qızı") else "m"
            if len({g for g in (gg, sg, pw) if g}) > 1:
                gender_bad.append((sur, giv, line))
            og = origin(canon(giv), "given")
            if og and canon(giv) not in male | female and not (origin(canon(sur), "surname") & og):
                origin_bad.append((sur, giv))
    check(people > 500 and not gender_bad, "each planned person's gender agrees (given, surname, oğlu/qızı)",
          gender_bad[:3])
    check(not origin_bad, "a planned foreign given name comes with a surname of its origin", origin_bad[:3])


def test_monitor_and_brief() -> None:
    s = sampler(GENRES)
    spec = next(x for x in (s.sample(i) for i in range(500)) if x.name_shape == "patronymic_list")
    ents = [{"label": e.label, "text": e.value} for e in spec.entities]
    kept = S.steering_labels(ents, spec)
    named = {e.value for e in spec.entities if e.role in S.NAME_SHAPE_ROLES}
    check(len(ents) - len(kept) >= len(named), "planned names are left out of the monitor's label mix")
    f = build_fields(spec)
    check(f["scenario_note"] == spec.name_note, "the scenario note is the name note")
    lines = f["entities_to_embed"].split("\n")
    named_lines = [ln for ln in lines if ln.startswith(("GIVENNAME: ", "SURNAME: "))
                   and any(ln.split(": ", 1)[1].startswith(v + "   (") for v in named)]
    check(named_lines and all("fused directly" not in ln for ln in named_lines)
          and all("exactly as given" in ln for ln in named_lines),
          "those names are hinted as bare, not with the case-ending hint", len(named_lines))
    check(any("directly before the word oğlu" in ln for ln in lines), "the father's name is hinted as such")


def test_gates() -> None:
    s = sampler(GENRES, seed=11)
    rng = random.Random(3)
    seen: collections.Counter = collections.Counter()
    ok = collections.Counter()
    problems: list = []
    for i in range(6000):
        x = s.sample(i)
        if (not x.name_shape or x.band not in ("short", "medium") or seen[x.name_shape] >= 5
                or any(e.label in ANCHOR_REQUIRED for e in x.entities)):
            continue
        seen[x.name_shape] += 1
        out = assemble_document(x, model_output(x, rng), GeneratorConfig(), noise_rate=0.0)
        if not out.ok:
            problems.append((x.name_shape, out.reason))
            continue
        ok[x.name_shape] += 1
        rec = out.record
        t, ents = rec["text"], rec["entities"]
        for m in re.finditer(r"(?<!\w)(oğlu|qızı)(?!\w)", t):
            if any(e["start"] < m.end() and m.start() < e["end"] for e in ents):
                problems.append((x.name_shape, "oğlu/qızı inside a span"))
            prev = [e for e in ents if e["end"] + 1 == m.start()]
            if len(prev) != 1 or prev[0]["label"] != "GIVENNAME":
                problems.append((x.name_shape, "the father's name is not a GIVENNAME span before oğlu/qızı"))
    check(not problems, "a model that follows the note passes assemble_document", problems[:3])
    check(set(ok) == SHAPES and all(v >= 2 for v in ok.values()),
          "every construction is accepted by the pipeline's gates", dict(ok))


if __name__ == "__main__":
    for name, fn in (("planning", test_planning), ("notes", test_notes), ("people", test_people),
                     ("monitor and brief", test_monitor_and_brief), ("gates", test_gates)):
        print(name)
        fn()
    print("\n" + "=" * 60)
    print(f"PASSED {PASS}   FAILED {FAIL}")
    print("=" * 60)
    for f in FAILURES:
        print("  FAIL:", f)
    sys.exit(1 if FAIL else 0)
