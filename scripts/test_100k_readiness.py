"""Regression tests for the 100k-readiness audit findings.

Every test here reproduces a specific defect the audit found in the
28,560-record corpus or the code that produced it. Each one fails against the
code as audited at commit 3d44592 and passes after the corresponding fix.

Kept separate from test_llm_augment.py deliberately: that suite tests the
pipeline's intended behaviour, this one pins defects so they cannot come back.
Same conventions (plain asserts via `check`, no pytest, no network).

Run:  python scripts/test_100k_readiness.py
"""

from __future__ import annotations

import importlib
import json
import random
import sys
import tempfile
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from piigen.config import ENTITY_SET, ENTITY_TYPES, REMOVED_LABELS  # noqa: E402
from piigen.llm.checkpoint import OutputWriter, load_existing, save_state, RunState  # noqa: E402
from piigen.resolver import complete_occurrences, resolve_claims  # noqa: E402
from piigen.values import ValuePool  # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond: bool, name: str, detail: object = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(f"{name}: {detail}")


def opt(modname: str):
    """Import a module that may not exist yet, so a missing fix records a
    failure instead of crashing the whole suite before later sections run."""
    try:
        return importlib.import_module(modname)
    except ImportError:
        return None


# Azerbaijani letters that exercise NFC/casing/width edge cases.
AZ_LETTERS = "əİıöüçşğƏÖÜÇŞĞ"


# ---------------------------------------------------------------------------
print("1. Resume idempotency (P0-1: spec-index regression)")
# ---------------------------------------------------------------------------
# Audit evidence: output holds ids up to llm_az_048595 while the checkpoint
# says next_spec_index=27585 and only 24,902 accepted. The old line
#     self._spec_counter = max(state.next_spec_index, len(existing))
# would resume at 32,535 and re-issue 16,061 already-used indices, each of
# which is a completed API call discarded as "duplicate id".

pipeline = opt("piigen.llm.pipeline")
next_index_fn = getattr(pipeline, "next_spec_index", None) if pipeline else None
check(callable(next_index_fn),
      "1.1 pipeline exposes next_spec_index() helper",
      "missing -- P0-1 not implemented")

if callable(next_index_fn):
    # The exact audited situation: sparse ids far beyond the accepted count.
    existing = ([{"id": f"llm_az_{i:06d}"} for i in range(100)]
                + [{"id": "llm_az_048595"}])
    idx, diverged = next_index_fn(existing, state_next_index=27585)
    check(idx == 48596,
          "1.2 resumes past the highest USED index, not the row count",
          f"got {idx}, want 48596")
    check(diverged,
          "1.3 checkpoint/output divergence is detected and reported",
          f"diverged={diverged}")

    # A stale-but-higher checkpoint must still win (never move backward).
    idx2, _ = next_index_fn([{"id": "llm_az_000005"}], state_next_index=900)
    check(idx2 == 900, "1.4 never regresses below the checkpoint", idx2)

    # Malformed ids must not crash or silently read as 0.
    idx3, _ = next_index_fn(
        [{"id": "llm_az_000007"}, {"id": "garbage"}, {"id": ""}, {}],
        state_next_index=0)
    check(idx3 == 8, "1.5 tolerates malformed ids without regressing", idx3)

    # Empty output resumes from the checkpoint alone.
    idx4, div4 = next_index_fn([], state_next_index=42)
    check(idx4 == 42 and not div4, "1.6 empty output uses checkpoint value",
          (idx4, div4))

# The monotonic invariant itself.
inv = getattr(pipeline, "assert_index_monotonic", None) if pipeline else None
check(callable(inv), "1.7 monotonic-index invariant helper exists",
      "missing -- P0-1 not implemented")
if callable(inv):
    try:
        inv(previous=100, nxt=99)
        check(False, "1.8 backward spec index raises", "no exception")
    except Exception:
        check(True, "1.8 backward spec index raises")


# ---------------------------------------------------------------------------
print("2. Unicode and span integrity")
# ---------------------------------------------------------------------------
# Decomposed Azerbaijani text: if NFC runs after spans are computed, every
# offset past the normalized character shifts and entity.text stops matching.
decomposed = unicodedata.normalize("NFD", "Şəhər Gəncə, yaşı 34, ünvan Üzeyir 12")
check(decomposed != unicodedata.normalize("NFC", decomposed),
      "2.1 test fixture really is decomposed")

normed = unicodedata.normalize("NFC", decomposed)
ents, _ = resolve_claims(normed, [{"label": "CITY", "text": "Gəncə"}])
check(all(normed[e["start"]:e["end"]] == e["text"] for e in ents),
      "2.2 spans hold after NFC normalization", ents)
check(len(ents) == 1, "2.3 the city resolved exactly once", ents)

# Every active noise kind must repair offsets exactly.
from piigen.noise import NoiseInjector  # noqa: E402
from piigen.config import GeneratorConfig  # noqa: E402

_gc = GeneratorConfig()
_base = ("Müştəri Əliyev Üzeyir, yaşı 41, ünvan Nizami küçəsi 12, "
         "şəhər Şəki, e-poçt uzeyir.aliyev@example.az, telefon +994501234567.")
_bad_noise = []
for _seed in range(300):
    _r = random.Random(_seed)
    _e0, _ = resolve_claims(_base, [
        {"label": "SURNAME", "text": "Əliyev"},
        {"label": "GIVENNAME", "text": "Üzeyir"},
        {"label": "CITY", "text": "Şəki"},
        {"label": "EMAIL", "text": "uzeyir.aliyev@example.az"},
    ])
    _t1, _e1, _kinds = NoiseInjector(_gc, _r).maybe_apply(_base, _e0, "az", rate=1.0)
    for _e in _e1:
        if _t1[_e["start"]:_e["end"]] != _e["text"]:
            _bad_noise.append((_seed, _kinds, _e))
            break
check(not _bad_noise,
      "2.4 every noise kind repairs offsets exactly (300 seeds)",
      _bad_noise[:3])

# Zero-width characters inside a span corrupt the value.
qf = opt("piigen.llm.quality_filter")
zw_fn = getattr(qf, "check_zero_width_in_spans", None) if qf else None
check(callable(zw_fn), "2.5 zero-width-in-span check exists")
if callable(zw_fn):
    _zt = "yaşı 34​ il"
    _ze = [{"start": 5, "end": 8, "label": "AGE", "text": "34​"}]
    check(bool(zw_fn(_zt, _ze)), "2.6 zero-width inside a span is detected")
    check(not zw_fn("yaşı 34​ il",
                    [{"start": 5, "end": 7, "label": "AGE", "text": "34"}]),
          "2.7 zero-width outside a span is allowed (deliberate noise kind)")


# ---------------------------------------------------------------------------
print("3. Anchor enforcement (P0-2)")
# ---------------------------------------------------------------------------
anchors = opt("piigen.anchors")
check(anchors is not None, "3.1 piigen.anchors module exists",
      "missing -- P0-2 not implemented")

if anchors is not None:
    has_anchor = anchors.has_anchor
    ANCHOR_REQUIRED = anchors.ANCHOR_REQUIRED

    check(set(ANCHOR_REQUIRED) == {"AGE", "BUILDINGNUM", "CARD_SECURITY_CODE",
                                   "DATE", "TIME"},
          "3.2 exactly the five anchor_required labels", sorted(ANCHOR_REQUIRED))

    cases = [
        # (label, text, value, anchored?)
        ("AGE", "Müştərinin yaşı 34 olduğu təsdiqləndi.", "34", True),
        ("AGE", "Bölmə 34 üzrə hesabat hazırlanır.", "34", False),
        ("BUILDINGNUM", "Ünvan: Nizami küçəsi, bina 12.", "12", True),
        ("BUILDINGNUM", "Cədvəl 12 aşağıda verilmişdir.", "12", False),
        ("CARD_SECURITY_CODE", "Kartın CVV kodu 417 daxil edildi.", "417", True),
        ("CARD_SECURITY_CODE", "Sifariş 417 tamamlandı.", "417", False),
        ("DATE", "Doğum tarixi 12.03.1990 olaraq qeyd olundu.", "12.03.1990", True),
        ("TIME", "Görüş saat 10:17-də başladı.", "10:17", True),
    ]
    for lab, text, val, want in cases:
        idx = text.find(val)
        got = has_anchor(lab, text, idx, idx + len(val))
        check(got is want, f"3.3 {lab} anchored={want}: {text[:38]!r}", got)

    # Self-signalling structured formats must not be over-rejected even with
    # no lexical anchor -- dd.mm.yyyy and HH:MM carry their own signal.
    check(has_anchor("DATE", "Sənəd 12.03.1990 tarixlidir.", 6, 16),
          "3.4 dd.mm.yyyy is self-signalling")
    check(has_anchor("TIME", "Log: 10:17 INFO başladı", 5, 10),
          "3.5 HH:MM is self-signalling")

    # Window must be configurable and respected.
    far = "yaşı" + " x" * 120 + " 34"
    i = far.rfind("34")
    check(not has_anchor("AGE", far, i, i + 2, window=80),
          "3.6 anchor beyond the window does not count")
    check(has_anchor("AGE", far, i, i + 2, window=400),
          "3.7 window is configurable")

    # Natural Azerbaijani must not be over-rejected.
    natural = [
        ("AGE", "O, 28 yaşındadır və Bakıda yaşayır.", "28"),
        ("AGE", "45 yaşlı müəllim məktəbdə işləyir.", "45"),
        ("BUILDINGNUM", "Mənzil 7, bina 3, Nərimanov rayonu.", "3"),
        ("BUILDINGNUM", "Üzeyir Hacıbəyov küçəsi 84 ünvanında.", "84"),
    ]
    for lab, text, val in natural:
        idx = text.find(val)
        check(has_anchor(lab, text, idx, idx + len(val)),
              f"3.8 natural AZ not over-rejected: {text[:38]!r}")


# ---------------------------------------------------------------------------
print("4. Short-value resolver guard (P0-3)")
# ---------------------------------------------------------------------------
# Audit: 32 documents where a planned AGE=3 also tagged the '3' in
# "### 3. Kritik Ssenari". resolve_claims had no minimum-length rule while
# complete_occurrences already had one -- that asymmetry is the bug.
structural = (
    "### 3. Bölmə\n"
    "1. Maddə qeyd olunur\n"
    "Qrup 2 üzrə nəticələr\n"
    "Müştərinin yaşı 3 ildir, mənzil 2 nömrəli binadadır.\n"
)
ents, _ = resolve_claims(structural, [
    {"label": "AGE", "text": "3"},
    {"label": "BUILDINGNUM", "text": "2"},
])
ages = [e for e in ents if e["label"] == "AGE"]
builds = [e for e in ents if e["label"] == "BUILDINGNUM"]

check(len(ages) == 1, "4.1 AGE='3' labeled exactly once, not on the heading",
      [(e["start"], structural[max(0, e["start"] - 22):e["end"] + 6]) for e in ages])
if len(ages) == 1:
    check("yaşı" in structural[max(0, ages[0]["start"] - 24):ages[0]["start"]],
          "4.2 the surviving AGE span is the anchored one",
          structural[max(0, ages[0]["start"] - 24):ages[0]["end"]])

check(len(builds) == 1,
      "4.3 BUILDINGNUM='2' not labeled on 'Qrup 2'",
      [(e["start"], structural[max(0, e["start"] - 22):e["end"] + 6]) for e in builds])

# A properly anchored short value must still survive.
ok_short, _ = resolve_claims("Müştərinin yaşı 9 ildir.", [{"label": "AGE", "text": "9"}])
check(len(ok_short) == 1, "4.4 anchored one-digit AGE is preserved", ok_short)

# Long values are unaffected by the guard.
long_ok, _ = resolve_claims("E-poçt: nurlan@example.az və nurlan@example.az",
                            [{"label": "EMAIL", "text": "nurlan@example.az"}])
check(len(long_ok) == 2, "4.5 repeat-mention of a long value still labels both",
      long_ok)

# The same policy must apply in complete_occurrences.
_t = "Qrup 2 üzrə. Mənzil 2 nömrəlidir."
_e = [{"start": _t.find("2", 13), "end": _t.find("2", 13) + 1,
       "label": "BUILDINGNUM", "text": "2"}]
_done, _added = complete_occurrences(_t, _e)
check(_added == 0, "4.6 complete_occurrences does not add the 'Qrup 2' digit",
      _added)


# ---------------------------------------------------------------------------
print("5. Taxonomy allowlist")
# ---------------------------------------------------------------------------
check(len(ENTITY_TYPES) == 27, "5.1 taxonomy is 27 labels", len(ENTITY_TYPES))
check(not (ENTITY_SET & REMOVED_LABELS),
      "5.2 no removed label is in ENTITY_SET", ENTITY_SET & REMOVED_LABELS)

# Removed labels must not appear as string literals in generator/validator
# paths. analyze.py's ghost labels (PASSWORD_SECRET_PRIVATE_KEY, IP_ADDRESS)
# are not in the taxonomy at all, so their metrics silently read 0.0 forever.
GHOSTS = ("PASSWORD_SECRET_PRIVATE_KEY", "IP_ADDRESS")
_src_root = Path(__file__).resolve().parent / "piigen"
_ghost_hits = []
for _p in sorted(_src_root.rglob("*.py")):
    _txt = _p.read_text(encoding="utf-8")
    for _g in GHOSTS:
        for _lineno, _line in enumerate(_txt.splitlines(), 1):
            if _g in _line and not _line.lstrip().startswith("#"):
                _ghost_hits.append(f"{_p.name}:{_lineno} {_g}")
check(not _ghost_hits, "5.3 no ghost label queried in library code", _ghost_hits)

_removed_hits = []
for _p in sorted(_src_root.rglob("*.py")):
    if _p.name == "config.py":       # the traceability declaration lives here
        continue
    _txt = _p.read_text(encoding="utf-8")
    for _lineno, _line in enumerate(_txt.splitlines(), 1):
        if _line.lstrip().startswith("#"):
            continue
        for _rl in REMOVED_LABELS:
            if f'"{_rl}"' in _line or f"'{_rl}'" in _line:
                _removed_hits.append(f"{_p.name}:{_lineno} {_rl}")
check(not _removed_hits, "5.4 no removed label as a literal in library code",
      _removed_hits)

# An allowlist gate callable the pipeline can use.
_allow = getattr(opt("piigen.validate"), "labels_allowed", None)
check(callable(_allow), "5.5 validate.labels_allowed() exists")
if callable(_allow):
    check(_allow([{"label": "GIVENNAME"}]) == [], "5.6 valid label passes")
    check(_allow([{"label": "PASSWORD"}]), "5.7 removed label is rejected")
    check(_allow([{"label": "NOT_A_LABEL"}]), "5.8 unknown label is rejected")


# ---------------------------------------------------------------------------
print("6. Pool exhaustion becomes a stop condition (P0-4)")
# ---------------------------------------------------------------------------
_pool = ValuePool(max_share=0.004, state_path=None)
check(hasattr(_pool, "draws"), "6.1 pool tracks per-label draw counts",
      "missing -- P0-4 not implemented")
check(hasattr(_pool, "over_cap"), "6.2 pool tracks per-label over-cap draws",
      "missing -- P0-4 not implemented")
check(hasattr(_pool, "health"), "6.3 pool exposes health()",
      "missing -- P0-4 not implemented")

if hasattr(_pool, "health"):
    # A three-value pool cannot cover 400 draws under any sane cap.
    tiny = ["Bakı", "Gəncə", "Sumqayıt"]
    r = random.Random(1)
    for _ in range(400):
        _pool.fresh("CITY", lambda: r.choice(tiny))
    h = _pool.health("CITY")
    check(h["draws"] == 400, "6.4 draw count is exact", h)
    check(h["over_cap"] > 0, "6.5 over-cap draws are counted", h)
    check(h["over_cap_share"] > 0.10,
          "6.6 tiny pool blows past the 10% stop threshold", h)
    check(h["status"] == "stop", "6.7 health() reports stop status", h)

    # A healthy pool must stay clean -- no false alarm.
    big = ValuePool(max_share=0.004, state_path=None)
    n = [0]

    def _uniq() -> str:
        n[0] += 1
        return f"value-{n[0]:07d}"

    for _ in range(400):
        big.fresh("EMAIL", _uniq)
    hb = big.health("EMAIL")
    check(hb["over_cap"] == 0 and hb["status"] == "ok",
          "6.8 healthy pool reports ok", hb)

    # Run-level rollup used by the batch stop condition.
    check(callable(getattr(_pool, "health_report", None)),
          "6.9 pool exposes health_report()")
    if callable(getattr(_pool, "health_report", None)):
        rep = _pool.health_report()
        check(rep["status"] == "stop" and "CITY" in rep["stop_labels"],
              "6.10 run-level rollup names the offending label", rep)


# ---------------------------------------------------------------------------
print("7. Global duplicate detection (P1)")
# ---------------------------------------------------------------------------
q = opt("piigen.llm.quality")
GlobalIndex = getattr(q, "GlobalSimilarityIndex", None) if q else None
check(GlobalIndex is not None, "7.1 GlobalSimilarityIndex exists",
      "missing -- P1 global dedup not implemented")

if GlobalIndex is not None:
    gi = GlobalIndex(threshold=0.82)
    skeleton = ("Hörmətli müştəri, hesabınız üzrə əməliyyat təsdiqləndi. "
                "Ətraflı məlumat üçün filiala müraciət edin. Təşəkkür edirik. "
                "Bu mesaj avtomatik göndərilmişdir və cavab tələb etmir. ")
    gi.add(skeleton + "ilk sənəd", doc_id="doc_000000")
    for i in range(1, 6000):
        gi.add(f"tamamilə fərqli sənəd nömrə {i} " * 6, doc_id=f"doc_{i:06d}")
    is_dupe, score, match = gi.check(skeleton + "ilk sənəd")
    check(is_dupe, "7.2 duplicate 6,000 records back is caught", (score, match))
    check(match == "doc_000000", "7.3 the matching id is reported", match)

    ok, score2, _ = gi.check("bu tamamilə yeni və orijinal bir mətndir " * 5)
    check(not ok, "7.4 a genuinely new document is not flagged", score2)

    # Shingle hashing must be deterministic across processes -- Python's
    # builtin hash() is salted per interpreter.
    shingles = getattr(q, "shingles", None)
    if callable(shingles):
        sub = ("import sys; sys.path.insert(0, r'%s'); "
               "from piigen.llm.quality import shingles; "
               "print(sorted(shingles('sabit mətn nümunəsi'))[:3])"
               % str(Path(__file__).resolve().parent))
        import subprocess
        outs = set()
        for _ in range(2):
            res = subprocess.run([sys.executable, "-c", sub],
                                 capture_output=True, text=True)
            outs.add(res.stdout.strip())
        check(len(outs) == 1 and outs != {""},
              "7.5 shingle hashes are stable across processes", outs)

# --- 7.6-7.8: the PRODUCTION pipeline must use the global index.
# Regression for a real defect: GlobalSimilarityIndex existed, was tested
# here in isolation, and passed -- while AugmentationPipeline went on
# constructing the 600-document windowed SimilarityIndex. Testing the class
# without testing the wiring is what let that survive, so this asserts the
# object the pipeline actually holds.
_pipe_mod = opt("piigen.llm.pipeline")
if _pipe_mod is not None and GlobalIndex is not None:
    class _StubGen:
        model = "stub"

        def stats(self):
            return {}

    _d = Path(tempfile.mkdtemp(prefix="pii-dedup-wiring-"))
    try:
        _cfg = _pipe_mod.AugmentConfig(
            num_examples=1, batch_size=1, concurrency=1, seed=1,
            output=_d / "o.jsonl", pool_state=None)
        _pipe = _pipe_mod.AugmentationPipeline(_StubGen(), _cfg)
        _idx = _pipe.similarity

        _is_global = isinstance(_idx, GlobalIndex)
        check(_is_global,
              "7.6 pipeline wires the GLOBAL index, not the windowed one",
              type(_idx).__name__)

        # Behavioural: a duplicate further back than the old 600-document
        # window must still be caught by the index the pipeline holds.
        # Guarded on 7.6 so that a regression fails 7.6 cleanly instead of
        # raising TypeError on the windowed index's 2-argument add() and
        # aborting the rest of the suite.
        if _is_global:
            _dup = ("Hörmətli müştəri, sifarişiniz qeydə alındı və emal "
                    "edilir. Ətraflı məlumat üçün dəstəyə yazın. ")
            _idx.add(_dup + "orijinal", "llm_az_000000")
            for _i in range(1, 1500):
                _idx.add(f"başqa bir sənəd mətni {_i} " * 6,
                         f"llm_az_{_i:06d}")
            _hit = _idx.check(_dup + "orijinal")
            check(_hit[0],
                  "7.7 pipeline index catches a duplicate 1,500 records back",
                  _hit)
            check(_hit[2] == "llm_az_000000",
                  "7.8 pipeline index reports the matching document id", _hit)
    finally:
        import shutil as _sh
        _sh.rmtree(_d, ignore_errors=True)


# ---------------------------------------------------------------------------
print("8. Partial write and crash recovery")
# ---------------------------------------------------------------------------
_tmp = Path(tempfile.mkdtemp(prefix="pii-crash-"))
_out = _tmp / "corpus.jsonl"
rows = [{"id": f"llm_az_{i:06d}", "text": f"sənəd {i} " + AZ_LETTERS,
         "lang": "az", "entities": []} for i in range(20)]
w = OutputWriter(_out, append=False)
w.write_many(rows)
w.close()

raw = _out.read_text(encoding="utf-8")
_out.write_text(raw[:-25], encoding="utf-8")        # truncate mid-record
recovered = load_existing(_out)
check(len(recovered) == 19,
      "8.1 truncated final record is dropped, the rest survive", len(recovered))
check(all(r["id"] == f"llm_az_{i:06d}" for i, r in enumerate(recovered)),
      "8.2 no reordering or duplication after truncation")

if callable(next_index_fn):
    idx, diverged = next_index_fn(recovered, state_next_index=20)
    check(idx == 20, "8.3 resume index survives a truncated tail", idx)
    check(diverged, "8.4 divergence between state and output is reported",
          diverged)


# ---------------------------------------------------------------------------
print("9. Malformed model output is rejected")
# ---------------------------------------------------------------------------
from piigen.llm.pipeline import assemble_document  # noqa: E402
from piigen.llm.specs import SpecSampler  # noqa: E402
from piigen.values import ValueFactory  # noqa: E402

_rng = random.Random(99)
_vp = ValuePool(max_share=0.004, state_path=None)
_vf = ValueFactory(_rng, _vp, GeneratorConfig().password_keyword_share)
_spec = SpecSampler(GeneratorConfig(), _vf, _rng).sample(0)

_bad_outputs = {
    "empty": "",
    "whitespace": "   \n\n  ",
    "truncated": "Hörmətli müş",
    "placeholder": "Ad: [GIVENNAME] Soyad: [SURNAME] Ünvan: [ADDRESS]",
    "label_echo": "GIVENNAME: Nurlan\nSURNAME: Məmmədov\nEMAIL: a@b.az",
    "english_only": ("Dear customer, your account has been updated "
                     "successfully. Please contact support for details."),
    "schema_json": json.dumps({"text": "salam", "entities": []}),
}
for _name, _text in _bad_outputs.items():
    _o = assemble_document(_spec, _text, GeneratorConfig(), 0.0)
    check(not _o.ok, f"9.1 rejects {_name} output", _o.reason[:70])


# ---------------------------------------------------------------------------
print("10. Golden regression corpus")
# ---------------------------------------------------------------------------
_golden = Path(__file__).resolve().parent.parent / "data" / "golden" / "golden_az.jsonl"
check(_golden.exists(), "10.1 golden corpus file exists", str(_golden))

if _golden.exists():
    from piigen.validate import validate_example  # noqa: E402
    _g_rows = [json.loads(l) for l in
               _golden.read_text(encoding="utf-8").splitlines() if l.strip()]
    check(len(_g_rows) >= 100, "10.2 golden corpus is a usable size",
          len(_g_rows))

    _span_bad = [r["id"] for r in _g_rows
                 for e in r["entities"]
                 if r["text"][e["start"]:e["end"]] != e["text"]]
    check(not _span_bad, "10.3 every golden span is exact", _span_bad[:5])

    _lab_bad = sorted({e["label"] for r in _g_rows for e in r["entities"]}
                      - ENTITY_SET)
    check(not _lab_bad, "10.4 every golden label is in the taxonomy", _lab_bad)

    _pos = [r for r in _g_rows if r.get("_golden_kind") != "defect"]
    _val_bad = [(r["id"], validate_example(r)[0])
                for r in _pos if validate_example(r)]
    check(not _val_bad,
          "10.5 every golden positive passes the current validator",
          _val_bad[:3])

    _defects = [r for r in _g_rows if r.get("_golden_kind") == "defect"]
    check(len(_defects) >= 10,
          "10.6 golden corpus carries the audit's historical defects",
          len(_defects))


# ---------------------------------------------------------------------------
print()
print("=" * 68)
print(f"PASSED {PASS}   FAILED {FAIL}")
if FAILURES:
    print("-" * 68)
    for f in FAILURES:
        print("  FAIL", f)
print("=" * 68)
sys.exit(1 if FAIL else 0)
