"""P2-4d checks: minimal-context documents and homograph pairs (RC9, D-10).

No network, no model.

    python scripts/piigen/targeted/test_short_homograph.py
"""

from __future__ import annotations

import re
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from piigen.llm.quality_filter import screen_record                   # noqa: E402
from piigen.negatives import ALL_DECOY_KINDS, active_decoy_kinds      # noqa: E402
from piigen.targeted import builder as B                              # noqa: E402
from piigen.targeted import homographs_az_stub as HSTUB               # noqa: E402
from piigen.validate import _WORD_RE, minimal_context, validate_example  # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond: bool, msg: str, detail=None) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(msg + (f"  [{detail!r}]"[:300] if detail is not None else ""))


def test_markers() -> None:
    check(B.parse_marked("Bu gün [[Dənizə]] yazdım.") == ("Bu gün ", "Dənizə", " yazdım.", "name"),
          "a name marker splits the sentence")
    check(B.parse_marked("<<Dəniz>> sakit idi.") == ("", "Dəniz", " sakit idi.", "word"), "a word marker")
    for bad in ("Heç bir marker yoxdur.", "[[Dəniz]] və <<dəniz>> birlikdə."):
        try:
            B.parse_marked(bad)
            check(False, f"refuses {bad!r}")
        except ValueError:
            check(True, f"refuses {bad!r}")
    bad = types.ModuleType("bad")
    bad.HOMOGRAPHS = {"Dəniz": {"name": ["<<Dəniz>> zəng etdi."], "word": ["<<Dəniz>> sakit idi."]}}
    bad.LONE_NAMES, bad.LONE_WORDS, bad.HOMOGRAPHS_VERSION = ["Dəniz"], ["dəniz"], "x"
    try:
        B.HomographLibrary(bad)
        check(False, "a name sentence marked as a word fails loudly")
    except ValueError:
        check(True, "a name sentence marked as a word fails loudly")


def test_stub_contract() -> None:
    """The rules the file must meet too (P4-2 check)."""
    lib = B.HomographLibrary(HSTUB)
    check(lib.source == "homographs_az_stub" and len(lib.entries) >= 12, "the stub loads")
    for name, sides in lib.entries.items():
        for side in ("name", "word"):
            items = sides[side]
            check(len(items) >= 3, f"{name}: >= 3 {side} sentences")
            check(any(before == "" for _f, before, _w, _a in items), f"{name}: a sentence-initial {side} use")
            check(any(word.lower() != name.lower() for _f, _b, word, _a in items), f"{name}: an inflected {side} use")
            check(all(not re.search(r"\d", b + w + a) for _f, b, w, a in items), f"{name}: no digits ({side})")
    check(all(n[:1].isupper() for n in lib.lone_names), "LONE_NAMES are capitalised")
    check(all(w == w.lower() for w in lib.lone_words), "LONE_WORDS are lowercase")
    check(all(g in ("f", "m") for g in lib.gender.values()), "the stub gives every name a gender")


def test_gate_exemption() -> None:
    def rec(text, ents, **kw):
        es = []
        for lab, v in ents:
            i = text.index(v)
            es.append({"start": i, "end": i + len(v), "label": lab, "text": v})
        return {"text": text, "lang": "az", "entities": es, "_decoys": [], **kw}
    declared = rec("Fidan.", [("GIVENNAME", "Fidan")], _doc_type="minimal_context", _source="targeted")
    check(minimal_context(declared) and validate_example(declared) == [], "a declared minimal document validates")
    check(screen_record(declared, run_base_gates=False, planned=[("GIVENNAME", "Fidan")]) == [],
          "a declared minimal document passes the quality screen")
    for name, r in (("undeclared", rec("Fidan.", [("GIVENNAME", "Fidan")])),
                    ("from the LLM path", rec("Fidan.", [("GIVENNAME", "Fidan")],
                                              _doc_type="minimal_context", _source="llm"))):
        check(not minimal_context(r) and validate_example(r), f"{name}: no exemption")
    long = rec("Salam, Fidan, sabah saat beşdə ofisdə görüşərik.", [("GIVENNAME", "Fidan")],
               _doc_type="minimal_context", _source="targeted")
    check(not minimal_context(long), "more than 5 words: no exemption")
    # everything else still applies to a minimal document
    broken = rec("Fidan.", [("GIVENNAME", "Fidan")], _doc_type="minimal_context", _source="targeted")
    broken["entities"][0]["end"] = 3
    check(validate_example(broken) != [], "a minimal document with a broken span still fails")


def test_decoy_kind() -> None:
    check("homograph_noun" in ALL_DECOY_KINDS and ALL_DECOY_KINDS["homograph_noun"].contextual,
          "homograph_noun is a contextual decoy kind")
    check("homograph_noun" not in {k.kind for k in active_decoy_kinds()},
          "homograph_noun is never planted at random")


def test_build() -> None:
    builder = B.TargetedBuilder(seed=31, n_docs=2000)
    recs = builder.build()
    mini = [r for r in recs if r["_spec"]["family"] == "minimal"]
    homo = [r for r in recs if r["_spec"]["family"] == "homograph"]
    check(0.035 <= len(mini) / len(recs) <= 0.065, f"minimal ~5% ({len(mini)})")
    check(0.035 <= len(homo) / len(recs) <= 0.065, f"homograph ~5% ({len(homo)})")
    check(all(1 <= len(_WORD_RE.findall(r["text"])) <= 5 for r in mini), "minimal documents are 1-5 words")
    check(all(r["_doc_type"] == "minimal_context" and validate_example(r) == [] for r in mini),
          "minimal documents are declared and validate")
    lone = [r for r in mini if r["_spec"]["minimal"] == "lone_word"]
    check(lone and all(not r["entities"] and r["_decoys"][0]["kind"] == "homograph_noun" for r in lone),
          "D-10: a lone lowercase word is unlabelled, declared as homograph_noun")
    names = [r for r in mini if r["_spec"]["minimal"] in ("name_alone", "name_punct")]
    check(names and all(r["entities"] and r["entities"][0]["text"][:1].isupper() for r in names),
          "D-10: a lone capitalised name is labelled")
    both = all(any(e["label"] == "GIVENNAME" for e in r["entities"])
               and any(x["kind"] == "homograph_noun" for x in r["_decoys"]) for r in homo)
    check(both, "every homograph document has both sides")
    overlap = sum(1 for r in recs for x in r["_decoys"] if x["kind"] == "homograph_noun"
                  for e in r["entities"] if e["start"] < x["end"] and x["start"] < e["end"])
    check(overlap == 0, "a homograph_noun is never labelled")
    inflected = [x for r in homo for x in r["_suffixes"]]
    check(inflected and all(x["surface"] == "plain" for x in inflected),
          "inflected names in homograph pairs are declared")
    check(not any(r["_spec"].get("case_noise") for r in mini + homo), "no casing noise on these families")
    # names from the list are counted, so the variant share can leave them out
    check(all(r["_spec"]["listed_names"] == sum(e["label"] == "GIVENNAME" for e in r["entities"]) >= 1
              for r in homo), "homograph documents count their listed names")
    listed = [r for r in mini if r["_spec"].get("listed_names")]
    check(listed and all(e["text"] in builder.homographs.lone_names for r in listed
                         for e in r["entities"] if e["label"] == "GIVENNAME"),
          "minimal documents count a name only when it comes from the list")
    check(not any(lab == "GIVENNAME" and v in builder.homographs.entries
                  for r in homo for lab, v, _k in r["_spec"].get("name_variants", ())),
          "a listed name is never recorded as a spelling variant")
    covered = {r["_spec"]["homograph"] for r in homo}
    check(covered == set(builder.homographs.entries), "every homograph name is used", sorted(covered))
    # a homograph name in a full name takes a surname of its gender (`Səma Əliyeva`, not `Səma Əliyev`)
    wrong_ending = {"f": ("ov", "ev"), "m": ("ova", "eva")}
    pairs = []
    for r in mini:
        if r["_spec"]["minimal"] != "full_name":
            continue
        given = next(e["text"] for e in r["entities"] if e["label"] == "GIVENNAME")
        sur = next(e["text"] for e in r["entities"] if e["label"] == "SURNAME")
        if given in builder.homographs.gender:
            pairs.append((given, sur))
    bad = [(g, s) for g, s in pairs if s.endswith(wrong_ending[builder.homographs.gender[g]])]
    check(pairs and not bad, f"full names agree in gender ({len(pairs)} checked)", bad[:5])


def test_picks_up_review_file() -> None:
    mod = types.ModuleType("homographs_az_test")
    mod.HOMOGRAPHS = {"Qaya": {"gender": "m", "az": "qaya", "en": "rock",
                               "name": ["[[Qaya]] zəng etdi.", "Sabah [[Qayaya]] yazacağam.", "Sənədi [[Qaya]] gətirib."],
                               "word": ["<<Qaya>> yolu bağlayıb.", "Uşaqlar <<qayaya>> çıxdı.", "Burada böyük <<qaya>> var."]}}
    mod.LONE_NAMES, mod.LONE_WORDS, mod.HOMOGRAPHS_VERSION = ["Qaya"], ["qaya"], "test"
    recs = B.TargetedBuilder(seed=2, n_docs=400, homographs_module=mod).build()
    homo = [r for r in recs if r["_spec"]["family"] == "homograph"]
    check(homo and all(r["_spec"]["homograph"] == "Qaya" for r in homo), "a given homograph module is used")


TESTS = [("markers", test_markers), ("stub contract (P4-2 rules)", test_stub_contract),
         ("declared minimal-context exemption", test_gate_exemption),
         ("homograph_noun decoy kind", test_decoy_kind), ("build", test_build),
         ("The file is picked up", test_picks_up_review_file)]

if __name__ == "__main__":
    for name, fn in TESTS:
        print(name)
        fn()
    print("=" * 60)
    print(f"PASSED {PASS}   FAILED {FAIL}")
    print("=" * 60)
    for f in FAILURES:
        print("  FAIL:", f)
    sys.exit(1 if FAIL else 0)
