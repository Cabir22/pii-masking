"""D-38 acceptance check: --doc-types and the published-text genres.

  * the five genres are document types, with hints that ask for natural prose;
  * a sampler given doc_types draws only those (edge-case and PII-free briefs
    too), every one of them; without it, every type;
  * the genres get no table/JSON/chat layout, no email/log/table noise
    directive and a formal register; other types keep theirs;
  * an unknown type is an error in the sampler and on the command line;
  * a --resume with other --doc-types than the run started with is refused.

    python scripts/piigen/test_doc_types.py
"""
from __future__ import annotations

import collections
import json
import random
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from llm_augment_data import parse_doc_types                           # noqa: E402
from piigen.config import GeneratorConfig                               # noqa: E402
from piigen.llm import specs as S                                       # noqa: E402
from piigen.llm.checkpoint import RunState, save_state                  # noqa: E402
from piigen.llm.pipeline import (AugmentConfig, AugmentationPipeline,   # noqa: E402
                                 ResumeMismatch)
from piigen.values import ValueFactory, ValuePool                       # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []
GENRES = {"news_article", "press_release", "official_notice", "procurement_announcement",
          "court_announcement"}
BATCH6 = sorted(GENRES | {"legal_notice", "government_form", "court_filing"})


def check(cond: bool, msg: str, detail=None) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(msg + (f"  [{detail}]" if detail is not None else ""))


def sampler(doc_types=None, seed=7) -> S.SpecSampler:
    cfg = GeneratorConfig()
    cfg.doc_types = doc_types
    cfg.negative_only_rate = 0.1
    cfg.hard_negative_rate = 0.3
    return S.SpecSampler(cfg, ValueFactory(random.Random(seed), ValuePool(state_path=None)),
                         random.Random(seed))


def test_genres() -> None:
    check(GENRES <= set(S.DOC_TYPES) and S.PROSE_DOC_TYPES == GENRES, "the five genres are document types")
    check(all("natural prose" in S.DOC_TYPES[g] for g in GENRES), "their hints ask for natural prose")
    check(GENRES <= S._LAYOUT_DOC_TYPES_EXCLUDED, "no structured layout for them")


def test_sampling() -> None:
    s = sampler(BATCH6)
    specs = [s.sample(i) for i in range(3000)]
    seen = collections.Counter(x.doc_type for x in specs)
    check(set(seen) == set(BATCH6), "only and every --doc-types type is drawn", dict(seen))
    check(min(seen.values()) >= 0.6 * 3000 / len(BATCH6), "drawn about evenly", dict(seen))
    check(any(x.edge_case for x in specs) and any(x.negative_only for x in specs),
          "edge-case and PII-free briefs keep to the types too")
    prose = [x for x in specs if x.doc_type in GENRES]
    banned = set(S._NOT_IN_PROSE)
    check(prose and not any(x.layout for x in prose), "published-text genres get no layout")
    check(not any(set(x.noise) & banned for x in prose), "no email, log or table noise for them")
    check(all(x.register in S.PROSE_REGISTERS for x in prose), "a formal register for them")
    check(any(e.role == "document_date" for x in prose for e in x.entities), "they still carry a document date")
    other = [x for x in specs if x.doc_type not in GENRES]
    # D-47c: the three legal genres of batch 6 take the formal registers too
    # (was "other types keep every register"; see test_d47c for the rest)
    check(other and all(x.register in S.PROSE_REGISTERS for x in other),
          "the legal genres take the formal registers too (D-47c)")
    all_types = sampler(None)
    everything = collections.Counter(all_types.sample(i).doc_type for i in range(6000))
    check(set(everything) == set(S.DOC_TYPES), "without --doc-types every type is drawn", len(everything))


def test_errors() -> None:
    try:
        sampler(["news_article", "newz_article"])
        check(False, "an unknown type is refused by the sampler")
    except ValueError:
        check(True, "")
    check(parse_doc_types(" news_article,press_release,news_article ") == ["news_article", "press_release"],
          "--doc-types parses, trims and de-duplicates")
    check(parse_doc_types(None) is None and parse_doc_types("") is None, "no --doc-types: every type")
    try:
        parse_doc_types("news_article,court_anouncement")
        check(False, "an unknown type on the command line is an error")
    except ValueError as exc:
        check("court_anouncement" in str(exc), "the error names the unknown type")


def test_resume() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "batch.jsonl"
        out.write_text(json.dumps({"id": "llm_az_000000", "text": "x", "entities": [], "lang": "az",
                                   "_doc_type": "news_article"}) + "\n", encoding="utf-8")
        save_state(out, RunState(model="m", seed=1, doc_types=["news_article"]))
        gen = types.SimpleNamespace(model="m")
        for asked, ok in ((["news_article"], True), (["press_release"], False), (None, False)):
            cfg = GeneratorConfig()
            cfg.doc_types = asked
            pipe = AugmentationPipeline(gen, AugmentConfig(output=out, resume=True, pool_state=None), cfg)
            try:
                pipe._prepare_resume()
                check(ok, f"a resume with --doc-types {asked} is refused")
            except ResumeMismatch:
                check(not ok, f"a resume with the same --doc-types {asked} goes on")


def test_d47c() -> None:
    """D-47c/f (batch-6 read): the legal genres take the formal
    registers, no "urgent and escalating" in them; typos and OCR artifacts
    are never explained; the self-correction only in conversational types."""
    from piigen.meta_noise import CONVERSATIONAL
    legal = {"legal_notice", "government_form", "court_filing"}
    check("urgent and escalating" not in S.PROSE_REGISTERS, "no `urgent and escalating` in the formal registers (D-47f)")
    check(legal | GENRES == set(S.FORMAL_REGISTER_DOC_TYPES), "the five genres and the three legal ones are formal")
    s = sampler(BATCH6)
    specs = [s.sample(i) for i in range(3000)]
    regs = collections.Counter((x.doc_type in legal, x.register) for x in specs)
    check(all(x.register in S.PROSE_REGISTERS for x in specs),
          "every batch-6 type draws a formal register", sorted({r for (_l, r) in regs if r not in S.PROSE_REGISTERS}))
    check({r for (l, r) in regs if l} == set(S.PROSE_REGISTERS), "the legal genres use every formal register")
    other = sampler(None)
    loose = [other.sample(i) for i in range(4000)]
    check(any(x.register == "frustrated and complaining" for x in loose if x.doc_type == "complaint_letter"),
          "a complaint still takes the emotional registers")
    ocr = next(d for d in S.NOISE_DIRECTIVES if "OCR" in d)
    typo = next(d for d in S.NOISE_DIRECTIVES if "typos" in d)
    check("never explain or mark the error" in ocr, "the OCR directive says never explain or mark the error", ocr)
    check("never explain or mark them" in typo and "self-correction" not in typo,
          "typos are never explained, and no longer come with a self-correction", typo)
    for dt in sorted(S.DOC_TYPES):
        has = S._SELF_CORRECTION in S.noise_directives("medium", dt)
        check(has == (dt in CONVERSATIONAL), f"self-correction directive only for conversational types: {dt}", has)
    drawn = [x for x in specs + loose if S._SELF_CORRECTION in x.noise]
    check(drawn and all(x.doc_type in CONVERSATIONAL for x in drawn),
          "sampled briefs carry the self-correction only in conversational types", len(drawn))


if __name__ == "__main__":
    for name, fn in (("genres", test_genres), ("sampling", test_sampling),
                     ("errors", test_errors), ("resume", test_resume),
                     ("D-47c/f registers and noise", test_d47c)):
        print(name)
        fn()
    print("\n" + "=" * 60)
    print(f"PASSED {PASS}   FAILED {FAIL}")
    print("=" * 60)
    for f in FAILURES:
        print("  FAIL:", f)
    sys.exit(1 if FAIL else 0)
