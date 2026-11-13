"""Round-trip validator: is this translated record safe to train on?

Every check here is deterministic and cheap. Together they are what lets an
unattended multi-day run be trusted -- SIMURG guards *delivery* quality
(script drift, loops, leakage) but knows nothing about sentinels, spans or
anchors, and cannot tell a fluent mistranslation from a good one.

The first check is the important one and should never fire: because values
are spliced in by us at a known position, a span that is not byte-exact is a
bug in `sentinel.splice`, not a translation problem. It is asserted anyway --
a silent off-by-one here would poison the training labels invisibly, which
is precisely the failure mode this whole design exists to make impossible.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from piigen.config import DETECTION_TIERS
from piigen.llm.quality import find_leaked_pii
from piigen.text import fold_diacritics
from translate.lang import ANCHORS as ANCHOR_MODULES, TRANSLITS as _TRANSLIT
from translate.sentinel import CLOSE, OPEN, SENTINEL_RE

# Email-shaped, Azerbaijani letters allowed -- find_leaked_pii's own regex is
# ASCII-only, which is exactly why the AZ corpus's header/signature emails
# (Göndərən: müştəri@email.com) are invisible to its audit.
_EMAIL_ANY = re.compile(r"[\wəğıöşçüİ.+-]+@[\wəğıöşçüİ.-]+\.[a-z]{2,}", re.I | re.U)
_LEAK_VALUE_RE = re.compile(r"[A-Z_]+:(.+)")

def _domain_skeleton(email: str, lang: str = "en") -> str:
    """A transliteration-agnostic fingerprint of an email's domain.

    The same Azerbaijani address is spelled differently in each carrier
    language -- `şirkət.az` becomes `shirkat.az` in English (en_translit
    spells the sounds) and `sirket.az` in Turkish (tr_translit only drops
    the letters Turkish lacks). To recognise them as one address the
    skeleton must not depend on which scheme ran:

      1. fold_diacritics -> bare ASCII (ə->e, ş->s, ç->c, ğ->g, ü->u);
      2. drop `h`, which is the only letter the two schemes disagree on
         (`ş`->`sh` vs `s`, `x`->`kh` vs `h`);
      3. collapse k/g/q, which Azerbaijani `q` maps to differently per
         language;
      4. strip vowels, which absorb the ə->a / ə->e split.

    `lang` is accepted for symmetry with the callers and to keep the door
    open for a language that needs its own pre-fold (Russian's Cyrillic);
    the ASCII path above is language-independent by construction.
    """
    dom = email.rsplit("@", 1)[-1].lower()
    if lang == "ru":                      # Cyrillic needs its own pre-fold
        dom = _TRANSLIT.get(lang, lambda s: s)(dom)
    dom = fold_diacritics(dom)
    dom = dom.replace("h", "")
    return re.sub(r"[aeiou]", "", re.sub(r"[kgq]", "k", dom))


# Kept for a future Cyrillic pre-fold; the ASCII path needs no per-language
# transliterator (see _domain_skeleton). Email domains stay Latin in every
# carrier language -- Wahoo transliterates only the AZ letters *inside* an
# address, never the domain to Cyrillic -- so the fold_diacritics ASCII path
# in _domain_skeleton covers ru as well without a Cyrillic branch.


def inherited_leak_exemptions(source_text: str, source_entities: list,
                              lang: str = "en") -> set:
    """Domain skeletons of every email in the Azerbaijani source that is not
    already a tagged entity. A translated leak matching one of these is not
    a translation defect -- it is an untagged email the AZ corpus carried in
    a header or signature, faithfully translated. (Known pre-existing gap:
    the AZ corpus should tag these, and then it propagates to every
    language. Tracked since 2026-09-05.)"""
    tagged = {source_text[e["start"]:e["end"]]
              for e in source_entities if e.get("label") == "EMAIL"}
    return {_domain_skeleton(m, lang) for m in _EMAIL_ANY.findall(source_text)
            if m not in tagged}

# Azerbaijani-only letters. Any of these outside an entity span means a
# segment came back untranslated (Wahoo silently skipping a chunk is the
# failure this catches, and it is invisible to every other check).
AZ_ONLY_CHARS = set("əƏ")

# Words that are distinctively Azerbaijani and common enough to be reliable
# without ə. Latin-script targets (en/tr) would not otherwise notice leftover
# Azerbaijani, since a Latin-script check passes on it.
# >= 4 chars and distinctively Azerbaijani. Short function words (və -> "ve",
# ilə -> "ile") are deliberately excluded: folded to ASCII they collide with
# English -- "ve" is the tail of every "I've"/"we've" contraction, "ile" sits
# inside "while"/"mile". The ə-letter check already catches un-folded prose.
AZ_MARKER_WORDS = frozenset({
    "üçün", "ucun", "olaraq", "haqqında", "haqqinda", "barədə", "barede",
    "zəhmət", "zehmet", "xahiş", "xahis", "olunur", "edilir", "edilməlidir",
    "edilmelidir", "edilmişdir", "edilmisdir", "müştəri", "musteri", "sənəd",
    "sened", "məlumat", "melumat", "melumatlari", "tarixində", "tarixinde",
    "nömrəli", "nomreli", "hörmətli", "hormetli", "təşəkkür", "tesekkur",
    "soyadi", "vəziyyət", "veziyyet", "miqdar", "qiymət", "qiymet",
})

# Turkish is Azerbaijani's sister language, and the marker list above was
# built against an ENGLISH target, where folded Azerbaijani is distinctive.
# Six of those folded forms are ordinary Turkish -- a Turkish document that
# says "kabul edilir" ("is accepted") or "rica olunur" ("is kindly
# requested") is correct Turkish, not leftover Azerbaijani. Measured on the
# 2026-09-06 calibration set: these six accounted for 25 of 28 repair-queue
# entries, every one of them a fluent, correct translation.
#
#   edilir / edilmelidir  -- core Turkish passives ("kontrol edilmelidir")
#   olunur                -- "rica olunur"
#   musteri               -- Turkish "müşteri" folds to exactly this
#   soyadi                -- Turkish "soyadı" folds to exactly this
#   tesekkur              -- Turkish "teşekkür" folds to exactly this
#
# The last three are the same trap as `musteri`: a real Turkish word whose
# diacritic-stripped form is byte-identical to the Azerbaijani marker, so no
# amount of context can separate them. The ə-carrying spellings
# (`edilməlidir`, `müştəri`, `təşəkkür`) stay in the set -- ə is not a
# Turkish letter, so they can never fire on real Turkish.
#
# Verified on the calibration corpus: dropping these six costs ZERO
# detection power (150/150 Azerbaijani source documents are still flagged,
# including the one ASCII-folded document with no ə to give it away).
TR_UNUSABLE_MARKERS = frozenset({
    "edilir", "edilmelidir", "musteri", "olunur", "soyadi", "tesekkur",
})

# Target language -> the markers that actually mean "this is untranslated
# Azerbaijani" in THAT language's output.
TR_CALQUE_WORDS = frozenset({"prosedur", "prosedurlar", "prosedurları", "prosedura",
                             "proseduru", "tekniki"})
# `bilgi tabanı` for veritabanı (two words, so a phrase, not a marker word)
TR_CALQUE_PHRASE = re.compile(r"\bbilgi taban", re.IGNORECASE)

MARKER_WORDS_BY_LANG = {
    "en": AZ_MARKER_WORDS,
    # D-56c (9), the TR check: Azerbaijani-only spellings left in
    # Turkish (`prosedur` for prosedür, `tekniki` for teknik)
    "tr": (AZ_MARKER_WORDS - TR_UNUSABLE_MARKERS) | TR_CALQUE_WORDS,
    # Cyrillic target: no Azerbaijani marker can collide with real Russian, so
    # the full set applies with none of Turkish's exclusions. (This entry was
    # reserved with a "add ru when anchors_ru lands" note; anchors_ru landed.)
    "ru": AZ_MARKER_WORDS,
}
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

# --- Azerbaijani letters, per target language ----------------------------- #
# For a LATIN target, ə/Ə are the only safe signals: Turkish owns ö ü ş ç ğ ı
# natively and English text borrows them, so a wider set would fire on correct
# output. A CYRILLIC target has no such conflict -- Russian prose contains no
# Latin letters at all -- which makes the full Azerbaijani diacritic set
# diagnostic there and catches an entire class the ə-only rule cannot see:
#
#   * whole untranslated words with no ə  -- hüquq, sığorta, doğum, poçt,
#     bakı, yaşında, küçəsi, vəsiqəsi, and org names (TEKSTİL, HOLDİNG,
#     ENERJİ, ŞİRKETİ), which the prompt requires be transliterated;
#   * HALF-TRANSLATED words, the more damaging case -- the model renders the
#     front of a word in Russian and leaves the Latin tail, giving fragments
#     like "şteri" (müştəri), "mrük" (gömrük), "lumatları" (məlumatları),
#     "peratör" (operatör). These are invisible to every other check: the
#     document reads as fluent Russian with a broken word inside it.
#
# Measured on train (2026-09-07): the ə-only rule flags 471 records; the full
# set flags 1,150 -- 679 genuinely defective records were shipping as clean.
AZ_LATIN_LETTERS = set("əƏıİğĞşŞçÇöÖüÜ")
AZ_ONLY_CHARS_BY_LANG = {"ru": AZ_LATIN_LETTERS}

# The one Latin word that is CORRECT inside Russian text here. VÖEN is the
# proper name of the Azerbaijani tax number (Vergi Ödəyicisinin Eyniləşdirmə
# Nömrəsi) and is used untranslated in Russian-language Azerbaijani business
# prose exactly as IBAN and SWIFT are -- the corpus even glosses it,
# "номер VÖEN (ИНН)". 980 of the 2,130 letter-carrying train records carry
# nothing else, and flagging them would have sent correct translations back
# for repair. Matched case-insensitively but only in pure Latin script, so
# the mixed-script corruption "ВÖEN" (Cyrillic В + Latin ÖEN, 5 occurrences)
# is still caught rather than excused by this exemption.
RU_BORROWED_LATIN = frozenset({"vöen"})
_LATIN_RE = re.compile(r"[A-Za-zƏəİıĞğŞşÇçÖöÜü]")
_CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")

# (translate/tr's parallel work reached the same conclusion independently
# with a MARKER_WORD_EXCLUSIONS dict -- {edilir, edilməlidir, olunur, ...}.
# TR_UNUSABLE_MARKERS above supersedes it: it also carries musteri / soyadi /
# tesekkur, the three real Turkish words whose diacritic-stripped form is
# byte-identical to an Azerbaijani marker, which that list missed.)

# Email- and URL-shaped tokens are masked before the marker-word scan: a
# transliterated address like musteri_sikayet@mail.az is correct output, but
# its local part word-splits into tokens ("musteri") that collide with the
# folded Azerbaijani marker list. The ə-letter check still runs on them --
# an untransliterated mərkəzi@... is still caught.
_EMAILISH_RE = re.compile(
    r"\b[\w.\-+]+@[\w.\-]+\.\w+|https?://\S+|\b[\w.\-]+\.(?:az|com|net|org|ru|io)\b/\S*",
    re.UNICODE)

ZERO_WIDTH = set("​‌‍⁠﻿")

_PREAMBLE_RE = re.compile(
    r"^\s*(?:here\s+is|here's|sure[,!]|certainly|of\s+course|"
    r"the\s+translation|translation\s*:|translated\s+text\s*:)",
    re.IGNORECASE)

# Outside this band the output is not a translation of the input -- either
# truncated/summarised, or padded with commentary. Measured against the
# ORIGINAL source text, not the templated text: sentinels are far shorter
# than the values they replace (a 180-char API key becomes 3 chars), so a
# templated-text baseline flags every identifier-heavy document as "too
# long". Against the source, the smoke test's real range was 0.85-1.25.
LEN_RATIO_MIN, LEN_RATIO_MAX = 0.55, 1.9


@dataclass
class Report:
    ok: bool = True
    failures: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def fail(self, code: str, detail: str = "") -> None:
        self.ok = False
        self.failures.append(f"{code}: {detail}" if detail else code)

    def warn(self, code: str, detail: str = "") -> None:
        self.warnings.append(f"{code}: {detail}" if detail else code)


def _spans_ok(text: str, entities: list[dict], minted: dict, rep: Report) -> None:
    prev_end = -1
    for i, e in enumerate(entities):
        s, t = e["start"], e["end"]
        if not (0 <= s < t <= len(text)):
            rep.fail("span_out_of_range", f"entity {i}: [{s},{t}) len={len(text)}")
            continue
        got = text[s:t]
        want = minted.get(i)
        if want is not None and got != want:
            rep.fail("span_not_exact", f"entity {i}: {got!r} != {want!r}")
        if s < prev_end:
            rep.fail("spans_overlap", f"entity {i} starts at {s}, previous ended {prev_end}")
        prev_end = t


def _leftover_azerbaijani(text: str, entities: list[dict],
                          lang: str = "en") -> list[str]:
    """Azerbaijani markers in carrier text, ignoring entity spans.

    Values are Azerbaijani by design -- a name legitimately carries ə -- so
    the spans are masked out before looking. The marker set is per-target-
    language: see MARKER_WORDS_BY_LANG for why Turkish drops six of them.
    """
    masked = list(text)
    for e in entities:
        for i in range(e["start"], min(e["end"], len(masked))):
            masked[i] = " "
    carrier = "".join(masked)

    # ə/Ə anywhere is a hard signal -- it survives even inside an email.
    hits = sorted({c for c in carrier if c in AZ_ONLY_CHARS})

    # Marker words only count in prose, not inside an email/URL token.
    markers = MARKER_WORDS_BY_LANG.get(lang, AZ_MARKER_WORDS)
    prose = _EMAILISH_RE.sub(" ", carrier)
    words = {w.lower() for w in _WORD_RE.findall(prose)}
    if lang == "tr":                     # Turkish lower case: İ -> i, I -> ı
        words |= {w.replace("İ", "i").replace("I", "ı").lower() for w in _WORD_RE.findall(prose)}
    hits += sorted(words & markers)
    if lang == "tr" and TR_CALQUE_PHRASE.search(prose):
        hits.append("bilgi tabanı")

    # Cyrillic targets additionally reject the wider Azerbaijani letter set
    # (see AZ_ONLY_CHARS_BY_LANG). Reported as the carrying WORD, not the bare
    # letter: "hüquq" tells a reviewer what went wrong, "ü" does not. Restricted
    # to prose for the same reason the markers are -- a URL or an email is not
    # translated, so a diacritic inside one is not evidence of anything.
    wide = AZ_ONLY_CHARS_BY_LANG.get(lang)
    if wide:
        extra = set()
        for w in _WORD_RE.findall(prose):
            if not (set(w) & wide):
                continue
            if (w.lower() in RU_BORROWED_LATIN
                    and not _CYRILLIC_RE.search(w)):
                continue                      # VÖEN, but never Cyrillic "ВÖEN"
            extra.add(w)
        hits += sorted(extra)
    return hits


# Targets written in Cyrillic. For these, and only these, a single word may
# not mix scripts (see _mixed_script_words).
CYRILLIC_TARGETS = frozenset({"ru"})


def _mixed_script_words(text: str, entities: list[dict],
                        lang: str = "en") -> list[str]:
    """Words mixing Latin and Cyrillic letters -- Cyrillic targets only.

    The most damaging defect a Cyrillic target can have, and the only one no
    other check can see. Two ways it is produced, both observed:

      * HOMOGLYPH substitution inside otherwise-correct Russian -- "договорa"
        with a Latin a, "систEме" with a Latin E, "ускорениe", "проблеmы".
        These render identically to the correct word. A human proofreader
        cannot see them and every content check passes, but the tokenizer
        splits them into different subwords than the real word, so the model
        is trained on a token sequence that will never occur at inference.
      * HALF-TRANSLITERATION -- "сirket", "месuliyyet", "Лейla", "техниqi":
        the model began converting an Azerbaijani word to Cyrillic and
        stopped part-way, leaving a word that is in neither language.

    Only meaningful where the two scripts do not legitimately coexist, hence
    the language gate: an English or Turkish document is Latin throughout and
    this would be either vacuous or wrong there.

    False positives are structurally near-impossible because `_WORD_RE` breaks
    on every non-letter: "IT-специалист", "Wi-Fi", "SIM-карта" and "VÖEN"
    each split into single-script words before they get here. Measured on the
    2026-09-07 corpus: 907 occurrences over 767 records, 681 distinct forms,
    601 of them occurring exactly once -- the signature of random corruption,
    not of a convention. The most frequent were "Лейla", "ошибкa", "клиентa",
    "удостоверениe", "счетe": all unambiguously broken.
    """
    if lang not in CYRILLIC_TARGETS:
        return []
    masked = list(text)
    for e in entities:
        for i in range(e["start"], min(e["end"], len(masked))):
            masked[i] = " "
    return sorted({w for w in _WORD_RE.findall("".join(masked))
                   if _LATIN_RE.search(w) and _CYRILLIC_RE.search(w)})


STALE_MIN_LEN = 6


def _stale_source_values(text: str, entities: list, source_values: list,
                         decoys: list) -> list[str]:
    """Original Azerbaijani entity values still sitting in the translation.

    An occurrence that carries no span of its own means the document states
    the same fact twice -- once as the freshly minted value, once as the
    Azerbaijani original -- so a reader (and the model) sees two different
    people. Two exemptions, both measured on real data:

      * a match INSIDE a tagged span is a minting collision, not a leak.
        CITY and ZIPCODE have small value spaces, so mint_values
        legitimately redraws the source value now and then; it is still
        correctly tagged and internally consistent.
      * a match inside a decoy is the decoy, spliced back verbatim by
        design (the "Astara (yox, ...)" self-correction traps).

    Word-boundary, not substring: a plain `in` false-positives whenever the
    old value is a prefix of an unrelated fresh one (stale "192.0.2.5"
    flagged because a correct, different entity minted "192.0.2.56").
    """
    spans = [(e["start"], e["end"]) for e in entities
             if isinstance(e.get("start"), int) and isinstance(e.get("end"), int)]
    decoy_hits = [(m.start(), m.end()) for d in (decoys or []) if d
                  for m in re.finditer(re.escape(d), text)]
    out = []
    for sv in set(source_values or []):
        if len(sv) < STALE_MIN_LEN:
            continue
        for m in re.finditer(rf"(?<!\w){re.escape(sv)}(?!\w)", text):
            if any(a <= m.start() and m.end() <= b for a, b in spans):
                continue
            if any(a <= m.start() < b or a < m.end() <= b for a, b in decoy_hits):
                continue
            out.append(sv)
            break
    return out


def validate_record(rec: dict, *, source_text: str, templated: str,
                    minted: dict | None = None,
                    decoys: list | None = None,
                    source_values: list | None = None,
                    expected_entities: int | None = None,
                    inherited_leak_domains: set | None = None,
                    guard_state: str = "clean") -> Report:
    """Full round-trip check on one translated record.

    `minted` maps slot index -> the exact value spliced in, when the caller
    has it (the harness always does). `templated` is what was sent to the
    model, used for the length-ratio check -- comparing against the *source*
    would be wrong, since sentinels are much shorter than the values they
    replaced.

    `expected_entities` is the number of ENTITY slots. Once
    `sentinelize_protected` also sentinelizes decoys and shadows, the
    sentinel count in `templated` is no longer the entity count, and
    counting all of them fails ~every negative and repeat-mention record.
    Falls back to the all-sentinel count for callers that predate it.

    `decoys` are PII-shaped on purpose and must not count as leaks.
    `inherited_leak_domains` exempts an EMAIL leak whose domain is an
    untagged email already present in the Azerbaijani source -- see
    `inherited_leak_exemptions`.
    """
    rep = Report()
    text = rec["text"]
    entities = rec["entities"]
    lang = rec["lang"]

    # 1. spans byte-exact, ordered, in range  (should never fail -> bug)
    _spans_ok(text, entities, minted or {}, rep)

    # 2. no sentinel survived into the output.
    #
    # ANY ⟦ or ⟧ is a failure, not just a well-formed ⟦digits⟧. Those two
    # characters were chosen precisely because they are absent from natural
    # az/en/tr/ru text, so a bare one is never legitimate -- and the strict
    # form misses the two ways this actually happens: a mangled token
    # (⟦ 0 ⟧, a dropped bracket), and the model echoing the literal "⟦N⟧"
    # out of the prompt's own description of the token format. The latter
    # shipped one record into the Turkish train split before this check was
    # widened (2026-09-06).
    stray = sorted({c for c in text if c in (OPEN, CLOSE)})
    if stray:
        shown = [m.group(0) for m in SENTINEL_RE.finditer(text)] or [
            text[max(0, i - 2):i + 3] for i, c in enumerate(text)
            if c in (OPEN, CLOSE)][:3]
        rep.fail("sentinel_survived", ", ".join(map(repr, sorted(set(shown)))))

    # 3. entity count preserved
    n_expected = (expected_entities if expected_entities is not None
                  else len(SENTINEL_RE.findall(templated)))
    if len(entities) != n_expected:
        rep.fail("entity_count",
                 f"{len(entities)} spans vs {n_expected} entity slots sent")

    # 4. no untranslated Azerbaijani left in the carrier text
    az = _leftover_azerbaijani(text, entities, lang)
    if az:
        rep.fail("leftover_azerbaijani", ", ".join(map(repr, az[:6])))

    # 5. anchor_required labels still licensed in the target language
    mod = ANCHOR_MODULES.get(lang)
    if mod is None:
        rep.fail("no_anchor_module",
                 f"{lang!r} -- add scripts/translate/anchors_{lang}.py")
    else:
        missing = mod.anchor_failures(text, entities)
        if missing:
            rep.fail("anchor_missing", ", ".join(
                f"{e['label']}@{e['start']}" for e in missing[:6]))

    # 6. unicode hygiene -- matches what validate_corpus.py enforces on AZ
    if unicodedata.normalize("NFC", text) != text:
        rep.fail("not_nfc")
    if any(c in ZERO_WIDTH for c in text):
        rep.fail("zero_width")
    # Characters that are never legitimate in training text and that the
    # SOURCE corpus provably does not contain (measured 2026-09-06: zero
    # across all 84,339 Azerbaijani train records). So any of these is
    # corruption introduced by the model or the transport, not something
    # translated faithfully -- two Turkish records picked up a U+FFFD
    # replacement character this way before the check existed.
    corrupt = sorted({c for c in text
                      if c == "�"
                      or unicodedata.category(c) in ("Co", "Cs", "Cn")})
    if corrupt:
        rep.fail("corrupt_char",
                 ", ".join(f"U+{ord(c):04X}" for c in corrupt[:4]))

    # 7. the model answered rather than translated
    if _PREAMBLE_RE.match(text):
        rep.fail("preamble", repr(text[:48]))
    if source_text:
        # X-TOK: the spliced values are freshly minted and may differ in length from the source's (a 47-char
        # token can come back as a 400-char JWT), which alone pushed 6-7% of token documents outside the band.
        # Count each value at its source length, so the ratio measures the translation, not the new values.
        length = len(text)
        if minted and source_values and len(minted) == len(source_values):
            length += sum(len(v) for v in source_values) - sum(len(v) for v in minted.values())
        ratio = length / max(1, len(source_text))
        if not (LEN_RATIO_MIN <= ratio <= LEN_RATIO_MAX):
            rep.fail("length_ratio", f"{ratio:.2f} vs source outside "
                                     f"[{LEN_RATIO_MIN}, {LEN_RATIO_MAX}]")

    # 8. PII the model invented and left untagged. Wahoo completes document
    # furniture it was never given -- a "Gönderen:"/"From:" header, a
    # signature block -- and fills it with a plausible email or phone. The
    # span machinery cannot see this: the invented value occupies no slot, so
    # every offset stays correct while the document quietly contains PII the
    # labels do not mark. On the English track this shipped in 0.84% of
    # records before the check was ported from validate_corpus.py.
    leaks = find_leaked_pii(text, entities, list(decoys or []))
    exempt = inherited_leak_domains or set()
    real = []
    for lk in leaks:
        m = _LEAK_VALUE_RE.match(lk)
        val = m.group(1) if m else lk
        if lk.startswith("EMAIL:") and _domain_skeleton(val, lang) in exempt:
            continue
        real.append(lk)
    if real:
        rep.fail("unlabeled_pii_leak", "; ".join(map(repr, real[:4])))

    # 8b. an ORIGINAL Azerbaijani entity value still present in the output.
    # This was audit-only until 2026-09-06, so run.py accepted such records
    # and the audit only caught them afterwards -- 29 reached the Turkish
    # corpus that way, concentrated in the hard tail where the adversarial
    # "Astar (yox, <tagged>)" typo-correction trap lives: the model
    # normalises the deliberately-misspelled decoy back into the real value.
    # Checking it here means those records go to the repair queue instead of
    # into the corpus.
    stale = _stale_source_values(text, entities, source_values or [],
                                 list(decoys or []))
    if stale:
        rep.fail("stale_az_value", ", ".join(map(repr, stale[:4])))

    # 9. SIMURG's verdict, carried through
    if guard_state == "corrupt":
        rep.fail("simurg_corrupt")
    elif guard_state == "suspect":
        # Not a failure: SIMURG's "maybe" loses to the deterministic checks
        # above, which have already had their say.
        rep.warn("simurg_suspect")

    if not source_text:
        rep.warn("no_source_text")
    return rep
