"""NoiseInjector -- corruption with exact offset repair.

The previous dataset contained no typo, no OCR error, no encoding glitch and no
copy/paste artifact anywhere: every character was pristine. Real inputs are not,
and Azerbaijani/Turkish are especially exposed because users routinely type
`s/ş`, `i/ı`, `g/ğ`, `o/ö`, `u/ü`, `c/ç`, `e/ə` when a keyboard layout is
unavailable -- a substitution that changes tokenization completely.

The hard part is not producing noise, it is keeping annotations exact while
doing it. Every transform here goes through the `text.transform` edit stream,
so a span moves by exactly the number of characters inserted or deleted before
it. Nothing is ever re-found by string search.

Two safety rules:
  * spans of NOISE_PROTECTED_LABELS are never corrupted internally, because
    breaking a Luhn or mod-97 checksum would make the value invalid and the
    Day 8 regex layer would then legitimately disagree with the label
  * a noised document is re-validated by the normal gate before it is written
"""

from __future__ import annotations

import random
import unicodedata

from .config import GeneratorConfig, NOISE_PROTECTED_LABELS
from .text import DIACRITIC_MAP, fold_diacritics, transform

# --- character-level confusion tables --------------------------------------

# Latin keyboard neighbours (QWERTY) -- typo model
_NEIGHBOURS = {
    "a": "qwsz", "b": "vghn", "c": "xdfv", "d": "serfcx", "e": "wsdr",
    "f": "drtgvc", "g": "ftyhbv", "h": "gyujnb", "i": "ujko", "j": "huikmn",
    "k": "jiolm", "l": "kop", "m": "njk", "n": "bhjm", "o": "iklp",
    "p": "ol", "q": "wa", "r": "edft", "s": "awedxz", "t": "rfgy",
    "u": "yhji", "v": "cfgb", "w": "qase", "x": "zsdc", "y": "tghu",
    "z": "asx",
}
# Cyrillic ЙЦУКЕН neighbours
_NEIGHBOURS_CYR = {
    "а": "вфыпр", "б": "ью待", "в": "ыаfц", "г": "нршо", "д": "лож",
    "е": "укн", "и": "мтчс", "к": "уец", "л": "джо", "м": "сич",
    "н": "тгш", "о": "лрщ", "п": "аври", "р": "поа", "с": "чмыи",
    "т": "ьбюи", "у": "цкв", "ф": "яыа", "ц": "уйк", "ч": "смя",
    "ш": "гщл", "щ": "шзд", "ы": "фчв", "э": "жх", "я": "фч",
}

# Diacritic stripping -- the highest-value noise type for az/tr.
#
# 2026-08-27: moved to text.py so resolver.py's suffix matchers can derive the
# folded surface forms THIS kind produces from the same table, instead of
# hand-listing them and drifting out of sync (they had).
_DIACRITIC_MAP = DIACRITIC_MAP

# OCR confusions (scanned forms, PDF extraction)
_OCR_MAP = {
    "0": "O", "O": "0", "1": "l", "l": "1", "I": "1", "5": "S", "S": "5",
    "8": "B", "B": "8", "2": "Z", "Z": "2", "6": "G", "G": "6",
    "rn": "m", "m": "rn", "cl": "d", "vv": "w", "ii": "n",
}

# Unicode lookalikes that survive copy/paste from web pages and Word
_SMART = {
    '"': "“", "'": "’", "-": "–", "...": "…",
}
_INVISIBLE = ["​", "‌", "­", "﻿"]

# Label carried by a protected non-entity span (a declared decoy) while it
# rides through the transforms; never a taxonomy label.
_PROTECT_TAG = "\x00protect:"


# --- entity casing noise (P2-4b, RC6) -----------------------------------------
#
# The benchmark missed lower-case, ASCII-folded and mixed-case values written
# inside otherwise normal text: 57 of its 116 missed GIVENNAME / SURNAME /
# CITY / STREET values look like `gebele`, `novxani`, `BUZoVNA`, `xInalIq`.
# The document-level kinds above touch whole documents or scattered letters;
# these rewrite one entity's whole value, which is how such values are typed.
# Every map is one character to one character, so offsets never move; the
# edit still goes through `transform`, so the entity's text is recomputed.

CASE_NOISE_KINDS = ("lower", "fold", "lower_fold", "mixed", "mixed_fold")

_AZ_LOWER = {"İ": "i", "I": "ı"}
_AZ_UPPER = {"i": "İ", "ı": "I"}


def _lower(ch: str) -> str:
    low = _AZ_LOWER.get(ch) or ch.lower()
    return low if len(low) == 1 else ch


def _upper(ch: str) -> str:
    up = _AZ_UPPER.get(ch) or ch.upper()
    return up if len(up) == 1 else ch


def case_noised(value: str, kind: str, rng: random.Random) -> str:
    """`value` written the way `kind` mistypes it; same length, always."""
    if kind.startswith("lower"):
        out = "".join(_lower(c) for c in value)
    elif kind.startswith("mixed"):
        letters = [i for i, c in enumerate(value) if c.isalpha()]
        out = list(value)
        for i in letters:
            out[i] = _upper(value[i]) if rng.random() < 0.5 else _lower(value[i])
        # both cases present after the first letter, as in `noVxanI`
        rest = letters[1:]
        if rest and not any(out[i].isupper() for i in rest):
            j = rng.choice(rest)
            out[j] = _upper(value[j])
        if rest and not any(out[i].islower() for i in rest):
            j = rng.choice(rest)
            out[j] = _lower(value[j])
        out = "".join(out)
    else:
        out = value
    if kind.endswith("fold"):
        out = fold_diacritics(out)
    return out if len(out) == len(value) else value


def apply_entity_casing(text: str, entities: list[dict],
                        choices: dict[int, str], rng: random.Random,
                        ) -> tuple[str, list[dict], dict[int, str]]:
    """Rewrite the entities at `choices` ({index: kind}); returns the new
    text, the remapped entities (same order) and the choices that actually
    changed a value. A kind that would leave a value unchanged (folding a
    name with no Azerbaijani letters) is dropped, not counted."""
    new_values, applied = {}, {}
    for i, kind in choices.items():
        e = entities[i]
        value = text[e["start"]:e["end"]]
        noised = case_noised(value, kind, rng)
        if noised != value:
            new_values[i] = noised
            applied[i] = kind
    if not new_values:
        return text, entities, {}
    by_start = {entities[i]["start"]: (entities[i]["end"], v) for i, v in new_values.items()}
    edits, pos = [], 0
    for start in sorted(by_start):
        end, value = by_start[start]
        for ch in text[pos:start]:
            edits.append(("keep", ch, ch))
        for old, new in zip(text[start:end], value):
            edits.append(("keep", old, old) if old == new else ("replace", old, new))
        pos = end
    for ch in text[pos:]:
        edits.append(("keep", ch, ch))
    new_text, remapped = transform(text, entities, edits)
    return new_text, remapped, applied


def _still_resolvable(text: str, merged: list[dict], n_entities: int, n_protect: int) -> bool:
    """After noise: every entity and protected span survived, and every entity
    is placed again by `resolve_claims` from its own text, as the corpus gate's
    resolver_drift check will place it (P2-6, batch 2)."""
    from .resolver import resolve_claims                 # lazy: resolver is heavier
    ents = [e for e in merged if not e["label"].startswith(_PROTECT_TAG)]
    prot = [(e["start"], e["end"]) for e in merged if e["label"].startswith(_PROTECT_TAG)]
    if len(ents) != n_entities or len(prot) != n_protect:
        return False
    if any(not 0 <= e["start"] < e["end"] <= len(text) for e in ents):
        return False
    placed, _ = resolve_claims(text, [{"label": e["label"], "text": text[e["start"]:e["end"]]}
                                      for e in ents], blocked=prot)
    return ({(e["start"], e["end"], e["label"]) for e in ents}
            <= {(p["start"], p["end"], p["label"]) for p in placed})


def _noise_breaks_language(before: str, after: str, lang: str) -> bool:
    """Does the noised text fail the language gate the clean text passes?"""
    from .validate import LANGUAGES, language_ok          # lazy: validate is heavier
    if lang not in LANGUAGES:
        return False
    return language_ok(before, lang)[0] and not language_ok(after, lang)[0]


class NoiseInjector:
    def __init__(self, cfg: GeneratorConfig, rng: random.Random) -> None:
        self.cfg = cfg
        self.rng = rng
        self.applied = 0
        self.kinds = {}

    # -- public -----------------------------------------------------------
    def maybe_apply(self, text: str, entities: list[dict], lang: str,
                    rate: float | None = None,
                    ) -> tuple[str, list[dict], list[str]]:
        """Apply 1-3 noise transforms with probability `rate`.

        `rate` defaults to `cfg.noise_rate`. A caller that wants to own the
        gate itself MUST pass `rate=1.0` rather than gating *and* calling in --
        two independent gates multiply, which is how the LLM pipeline ended up
        noising 1.8% of documents while both config values read ~0.2.

        This object holds a single RNG, so a caller running concurrently must
        construct one injector per document (they are cheap) rather than
        sharing one across threads.
        """
        threshold = self.cfg.noise_rate if rate is None else rate
        if self.rng.random() >= threshold or not text:
            return text, entities, []

        protected = self._protected_ranges(entities)
        transforms = self._choose(lang)
        applied = []
        for name in transforms:
            fn = getattr(self, f"_{name}")
            try:
                new_text, new_ents = fn(text, entities, protected, lang)
            except Exception:                       # noqa: BLE001 -- never fail a doc
                continue
            if new_text and new_ents is not None:
                text, entities = new_text, new_ents
                protected = self._protected_ranges(entities)
                applied.append(name)
                self.kinds[name] = self.kinds.get(name, 0) + 1
        if applied:
            self.applied += 1
        return text, entities, applied

    def apply_protected(self, text: str, entities: list[dict], protect: list[dict],
                        lang: str, rate: float | None = None,
                        ) -> tuple[str, list[dict], list[dict], list[str]]:
        """`maybe_apply`, plus extra spans (declared decoys, P2-3) that noise
        must neither edit nor lose.

        A decoy is proven NOT to be PII (rule R4); a typo inside it could make
        it valid (`saat 22:94` -> `saat 22:34`), turning it into unlabeled PII.
        So its characters are protected, and its offsets ride through the same
        remapping as the entities'. Returns (text, entities, protect, applied);
        each protect dict keeps its other keys with new start/end.
        """
        tagged = [{"start": p["start"], "end": p["end"], "label": f"{_PROTECT_TAG}{i}",
                   "text": text[p["start"]:p["end"]]} for i, p in enumerate(protect)]
        noised, merged, applied = self.maybe_apply(text, entities + tagged, lang, rate=rate)
        if applied and not _still_resolvable(noised, merged, len(entities), len(protect)):
            # P2-6 (batch 2): noise must never make a record the corpus gate
            # rejects. 2 of batch 2's 6,000 slipped through: a typo deleted the
            # only entity (`bina 95` -> `bina  5ünvanı`, accepted with no
            # labels) or landed right after a span (`...61-dirr`, `...c7.B u`),
            # which validate_corpus's resolver_drift re-check then could not
            # place. The document ships un-noised instead, as pipeline.py does
            # for a span left mid-word.
            noised, merged, applied = text, entities + tagged, []
        if applied and _noise_breaks_language(text, noised, lang):
            # P2-5 (batch 4): nor one the language gate rejects because of the
            # noise alone. strip_diacritics leaves a short document too few
            # Azerbaijani words (53% of batch 4's very short documents fail
            # once folded), and the document was rejected after generation.
            noised, merged, applied = text, entities + tagged, []
        text = noised
        entities, kept = [], []
        for e in merged:
            if e["label"].startswith(_PROTECT_TAG):
                original = protect[int(e["label"][len(_PROTECT_TAG):])]
                kept.append({**original, "start": e["start"], "end": e["end"]})
            else:
                entities.append(e)
        return text, entities, kept, applied

    def _choose(self, lang: str) -> list[str]:
        pool = ["typos", "whitespace", "copy_paste", "ocr", "line_wrap",
                "case_glitch", "invisible", "all_caps"]
        if lang in ("az", "tr"):
            pool += ["strip_diacritics", "strip_diacritics"]
        if lang == "ru":
            pool += ["mojibake"]
        k = self.rng.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
        return self.rng.sample(pool, min(k, len(pool)))

    def _protected_ranges(self, entities: list[dict]) -> list[tuple[int, int]]:
        return [(e["start"], e["end"]) for e in entities
                if e["label"] in NOISE_PROTECTED_LABELS
                or e["label"].startswith(_PROTECT_TAG)]

    @staticmethod
    def _is_protected(i: int, ranges: list[tuple[int, int]]) -> bool:
        return any(s <= i < e for s, e in ranges)

    # -- transforms -------------------------------------------------------
    def _typos(self, text, entities, protected, lang):
        rng = self.rng
        rate = self.cfg.noise_intensity
        table = _NEIGHBOURS_CYR if lang == "ru" else _NEIGHBOURS
        edits = []
        i = 0
        while i < len(text):
            ch = text[i]
            if self._is_protected(i, protected) or rng.random() >= rate:
                edits.append(("keep", ch, ch))
                i += 1
                continue
            low = ch.lower()
            op = rng.random()
            if op < 0.40 and low in table:                       # substitute
                sub = rng.choice(table[low])
                edits.append(("replace", ch, sub.upper() if ch.isupper() else sub))
            elif op < 0.62 and i + 1 < len(text) and not self._is_protected(i + 1, protected):
                edits.append(("replace", text[i:i + 2], text[i + 1] + ch))  # transpose
                i += 2
                continue
            elif op < 0.80:                                       # double
                edits.append(("replace", ch, ch + ch))
            elif ch not in " \n":                                 # drop
                edits.append(("delete", ch, ""))
            else:
                edits.append(("keep", ch, ch))
            i += 1
        return transform(text, entities, edits)

    def _strip_diacritics(self, text, entities, protected, lang):
        """Users without a localized keyboard write `Meherremov` for `Məhərrəmov`.

        Applied to whole words including inside NAME/ADDRESS spans -- that is
        the realistic case and the span stays exact because the replacement is
        recorded in the edit stream.
        """
        rng = self.rng
        partial = rng.random() < 0.6          # some words only
        edits = []
        for i, ch in enumerate(text):
            if ch in _DIACRITIC_MAP and not self._is_protected(i, protected):
                if not partial or rng.random() < 0.7:
                    edits.append(("replace", ch, _DIACRITIC_MAP[ch]))
                    continue
            edits.append(("keep", ch, ch))
        return transform(text, entities, edits)

    def _ocr(self, text, entities, protected, lang):
        rng = self.rng
        rate = self.cfg.noise_intensity * 1.4
        edits = []
        for i, ch in enumerate(text):
            if (not self._is_protected(i, protected) and ch in _OCR_MAP
                    and rng.random() < rate):
                edits.append(("replace", ch, _OCR_MAP[ch]))
            else:
                edits.append(("keep", ch, ch))
        return transform(text, entities, edits)

    def _whitespace(self, text, entities, protected, lang):
        rng = self.rng
        edits = []
        for i, ch in enumerate(text):
            if ch == " " and rng.random() < 0.05:
                edits.append(("replace", ch, rng.choice(["  ", "   ", "\t"])))
            elif ch == "\n" and rng.random() < 0.05:
                edits.append(("replace", ch, rng.choice(["\n\n", " \n", "\r\n"])))
            else:
                edits.append(("keep", ch, ch))
        return transform(text, entities, edits)

    def _copy_paste(self, text, entities, protected, lang):
        """Smart quotes, en-dashes and NBSP that survive a paste from Word."""
        rng = self.rng
        edits = []
        for i, ch in enumerate(text):
            if self._is_protected(i, protected):
                edits.append(("keep", ch, ch))
                continue
            if ch == '"' and rng.random() < 0.5:
                edits.append(("replace", ch, rng.choice(["“", "”"])))
            elif ch == "'" and rng.random() < 0.5:
                edits.append(("replace", ch, "’"))
            elif ch == "-" and rng.random() < 0.12:
                edits.append(("replace", ch, rng.choice(["–", "—"])))
            elif ch == " " and rng.random() < 0.03:
                edits.append(("replace", ch, " "))
            else:
                edits.append(("keep", ch, ch))
        return transform(text, entities, edits)

    def _invisible(self, text, entities, protected, lang):
        rng = self.rng
        edits = []
        for i, ch in enumerate(text):
            edits.append(("keep", ch, ch))
            if (ch == " " and rng.random() < 0.01
                    and not self._is_protected(i, protected)):
                edits.append(("insert", "", rng.choice(_INVISIBLE)))
        return transform(text, entities, edits)

    def _line_wrap(self, text, entities, protected, lang):
        """PDF extraction wraps mid-word with a hyphen and hard newline."""
        rng = self.rng
        edits = []
        col = 0
        width = rng.choice([64, 72, 78, 80])
        for i, ch in enumerate(text):
            if ch == "\n":
                col = 0
                edits.append(("keep", ch, ch))
                continue
            col += 1
            # mid-word only, as the docstring says: a wrap after a word's LAST
            # letter left `-\n` at the end of a span (`...2021-CI IL-\n`),
            # which validation then rejects (P2-6). Checked after the draw so
            # the random stream is unchanged.
            if (col >= width and ch.isalpha()
                    and not self._is_protected(i, protected)
                    and rng.random() < 0.5
                    and text[i + 1:i + 2].isalpha()):
                edits.append(("replace", ch, ch + "-\n"))
                col = 0
            else:
                edits.append(("keep", ch, ch))
        return transform(text, entities, edits)

    def _all_caps(self, text, entities, protected, lang):
        """A whole line, or the whole document, shouted in capitals.

        Distinct from `_case_glitch`, which flips scattered individual
        characters: this is the uniform upper-casing real scanned forms,
        headers and pasted-from-caps-lock text arrive in, and detection was
        measured to collapse on it even for names caught reliably in mixed
        case. Only single-character upper-casings are emitted, so the edit
        stream stays length-preserving and every span offset is unchanged.
        """
        rng = self.rng
        lines = text.split("\n")
        if len(lines) > 1 and rng.random() < 0.5:        # one line only
            target = rng.randrange(len(lines))
            begin = sum(len(l) + 1 for l in lines[:target])
            finish = begin + len(lines[target])
        else:
            begin, finish = 0, len(text)

        edits = []
        for i, ch in enumerate(text):
            upper = ch.upper()
            if (begin <= i < finish and len(upper) == 1 and upper != ch
                    and not self._is_protected(i, protected)):
                edits.append(("replace", ch, upper))
            else:
                edits.append(("keep", ch, ch))
        return transform(text, entities, edits)

    def _case_glitch(self, text, entities, protected, lang):
        rng = self.rng
        edits = []
        for i, ch in enumerate(text):
            if (ch.isalpha() and not self._is_protected(i, protected)
                    and rng.random() < self.cfg.noise_intensity * 0.6):
                edits.append(("replace", ch, ch.upper() if ch.islower() else ch.lower()))
            else:
                edits.append(("keep", ch, ch))
        return transform(text, entities, edits)

    def _mojibake(self, text, entities, protected, lang):
        """UTF-8 bytes decoded as cp1252 -- classic legacy-export corruption."""
        rng = self.rng
        edits = []
        for i, ch in enumerate(text):
            if (ord(ch) > 127 and not self._is_protected(i, protected)
                    and rng.random() < 0.10):
                try:
                    broken = ch.encode("utf-8").decode("cp1252", errors="replace")
                except Exception:                    # noqa: BLE001
                    broken = ch
                edits.append(("replace", ch, broken))
            else:
                edits.append(("keep", ch, ch))
        return transform(text, entities, edits)
