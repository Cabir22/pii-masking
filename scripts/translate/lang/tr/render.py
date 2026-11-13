"""Turkish renderer: how a minted Azerbaijani value is spelled in Turkish
carrier text.

Turkish is Azerbaijani's sister language, so this keeps ç ğ ı ö ş ü
(Turkish owns them natively) and only maps ə, plus city exonyms and
street-type conversions.

Registered into `translate.render.RENDERERS` by `translate.lang`.
"""
from __future__ import annotations

import random
import re
import weakref  # noqa: F401

from piigen.text import fold_diacritics  # noqa: F401
from translate.render import Renderer  # noqa: F401


# --- Turkish ----------------------------------------------------------------
# Unlike English, Turkish natively has ç ş ğ ı ö ü -- so unlike `en_translit`,
# this must NOT touch them. THREE Azerbaijani letters are absent from the
# Turkish alphabet (a b c ç d e f g ğ h ı i j k l m n o ö p r s ş t u ü v y z):
#
#   ə -> e    the schwa
#   q -> g    Azerbaijani q is /g/  (Qəbələ -> Gebele, Beyləqan -> Beylegan)
#   x -> h    Azerbaijani x is /x/  (Naxçıvan -> Nahçıvan, Xaçmaz -> Haçmaz)
#
# CRITICAL, and the reason this is a letter map and not a cognate table: Əli
# must render as Eli, never as the Turkish name "Ali", and Məmməd must never
# become "Mehmet". Substituting a Turkish cognate changes who the person is,
# which is exactly what this corpus must not do. q->g and x->h are in the
# same category as ə->e -- a spelling convention that still spells the same
# name (Qumriyeva -> Gumriyeva is one person; Əli -> Ali would be two).
#
# EVIDENCE for q->g / x->h, not a guess: this three-letter map reproduces
# 23 of the 26 hand-written TR_CITY_EXONYMS below, against 19 for a
# schwa-only map. The three it misses are Bakı->Bakü (genuinely irregular,
# which is what the table is for), Sumqayıt (the table deliberately keeps
# the q, matching Turkish press usage), and Qəbələ (whose table entry was an
# English exonym pasted in by mistake -- fixed below). Before this, the same
# letter was folded for the four cities that happened to be in the table and
# left alone for the other ~21 that were not, so a single corpus wrote both
# "Haçmaz" and "Xocalı".
_TR_TRANSLIT = {
    "ə": "e", "Ə": "E",
    "q": "g", "Q": "G",
    "x": "h", "X": "H",
}
_TR_SCHWA = _TR_TRANSLIT          # back-compat alias for existing importers

# Share of names that keep the original ə spelling (a pasted ID/database
# export, say) rather than the natural-Turkish-orthography fold. Small by
# design -- a config value so the choice is visible here, not a magic number
# buried in `_tr_name`. Contrast with EN_FOLD_NAME_RATE=0.6: English news
# prose commonly anglicises names, so anglicised is the majority form there;
# Turkish orthography folding ə->e is the unmarked default, so keeping ə is
# the minority form here instead.
TR_KEEP_SCHWA_RATE = 0.12


def tr_translit(value: str) -> str:
    """Azerbaijani surface form -> its Turkish spelling: ə->e, q->g, x->h.

    Turkish keeps ç ş ğ ı ö ü as-is; only the three letters its alphabet
    lacks are folded. See the map above for why these three and no others.
    """
    return "".join(_TR_TRANSLIT.get(ch, ch) for ch in value)


# Cities with an established Turkish form -- not derivable from a character
# map (Naxçıvan -> Nahçıvan is x->h, a real historical convention shared with
# other Azerbaijani/Turkish place-name pairs, not something `tr_translit`
# produces). Best-effort research, not a native speaker's confirmation --
# flag for review if a Turkish speaker sees one that's wrong. The long tail
# (the other ~30 cities in az.py's pool) falls through to the mechanical
# ə->e fold below, which is correct for names with no other irregular
# letter; a handful of AZ city names also carry x/q, letters absent from the
# Turkish alphabet entirely, and the mechanical fallback does NOT fold those
# (only ə->e, matching what was asked) -- a known, narrower gap than the
# exonym table's coverage, left for the same future review.
TR_CITY_EXONYMS = {
    # D-56c (9): Turkish writes Sumgayıt; the old entry kept a q the prompt forbids
    "Bakı": "Bakü", "Gəncə": "Gence", "Sumqayıt": "Sumgayıt",
    "Naxçıvan": "Nahçıvan", "Şəki": "Şeki", "Lənkəran": "Lenkeran",
    # Qəbələ was "Gabala" here -- the ENGLISH exonym, pasted in from
    # EN_PLACE_MAP by mistake (2026-09-06 audit). Turkish folds it exactly
    # like the mechanical map does: q->g, ə->e.
    "Mingəçevir": "Mingeçevir", "Şirvan": "Şirvan", "Qəbələ": "Gebele",
    "Şamaxı": "Şamahı", "Xaçmaz": "Haçmaz", "Ağcabədi": "Ağcabedi",
    "Cəlilabad": "Celilabad", "Zərdab": "Zerdab", "Şəmkir": "Şemkir",
    "Kəlbəcər": "Kelbecer", "Şuşa": "Şuşa", "Xankəndi": "Hankendi",
    "Cəbrayıl": "Cebrayıl", "Zəngilan": "Zengilan", "Kürdəmir": "Kürdemir",
    "Bərdə": "Berde", "Gədəbəy": "Gedebey", "Biləsuvar": "Bilesuvar",
    "Beyləqan": "Beylegan", "Balakən": "Balaken",
}

_TR_STREET_TYPES = {
    "küçəsi": "Caddesi", "küç.": "Cad.", "prospekti": "Bulvarı",
    "pr.": "Blv.", "döngəsi": "Sokağı",
}


_ALIYEV = re.compile(r"Əliyev|ƏLİYEV")


def _tr_aliyev(value: str) -> str:
    """D-56c (9), the team: Turkish writes the surname Aliyev, not Eliyev (the
    given name Əli still folds to Eli -- never Ali)."""
    return _ALIYEV.sub(lambda m: "Aliyev" if m.group(0)[1] != "L" else "ALİYEV", value)


def _tr_place(value: str) -> str:
    """Fold, and translate a trailing Azerbaijani street-type word."""
    value = _tr_aliyev(value)
    for az_type, tr_type in _TR_STREET_TYPES.items():
        if value.endswith(" " + az_type):
            stem = value[: -(len(az_type) + 1)]
            return f"{tr_translit(stem)} {tr_type}"
    return tr_translit(value)


# Keep/fold decision, cached per DOCUMENT rather than per name -- see
# _tr_name's docstring. Keyed on the rng object itself (mint_values()
# creates exactly one random.Random per document and threads it through
# every entity in it), so the cache entry needs no manual cleanup: once a
# document's minting pass ends, nothing else references that rng object,
# it becomes collectible, and the weak-keyed entry disappears with it. No
# behavior change is needed in mint_values()/Renderer to make this work --
# the calling convention (name_fn(value, rng)) is untouched.
_TR_SCHWA_DOC_DECISION: "weakref.WeakKeyDictionary[random.Random, bool]" = \
    weakref.WeakKeyDictionary()


def _tr_name(value: str, rng: random.Random) -> str:
    """Fold ə->e except for a small, configured share kept as-given.

    The decision is made ONCE PER DOCUMENT, not once per name. A document
    is either "pasted from an ID/database export" (every name keeps its ə
    spelling) or ordinary Turkish prose (every name folds) -- one document
    mixing both conventions across different names would read like two
    transcription sources spliced together, which no real document does.
    Concretely, this fixes GIVENNAME/SURNAME fold *disagreement* for the
    same person (confirmed empirically at a 20.8% rate under the old
    per-call roll -- two independent Bernoulli(0.12) draws disagreeing
    2*0.12*0.88 of the time) by making it structurally impossible: every
    name-labeled value in one document shares the same roll, so any two
    of them -- whether or not they belong to the same person -- agree.
    """
    if rng not in _TR_SCHWA_DOC_DECISION:
        _TR_SCHWA_DOC_DECISION[rng] = rng.random() < TR_KEEP_SCHWA_RATE
    if _TR_SCHWA_DOC_DECISION[rng]:
        return value
    return tr_translit(_tr_aliyev(value))


RENDERER = Renderer(lang="tr", place_map=TR_CITY_EXONYMS,
                    place_fn=_tr_place, name_fn=_tr_name)

#: ASCII-folding used by validate._domain_skeleton
TRANSLIT = tr_translit
