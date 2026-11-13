"""Per-language packs for the translation harness.

One directory per carrier language, each holding everything that is specific
to spelling Azerbaijani PII inside that language's prose:

    lang/<code>/anchors.py   licensing words for the anchor_required tier
    lang/<code>/render.py    how a minted value is spelled in this language

Adding a language is adding one directory and one line in `PACKS` below --
nothing in the harness, the validators or the auditor needs to change.

Importing this package registers every renderer into
`translate.render.RENDERERS` and every anchor adapter into `ANCHORS`, so the
harness only ever asks for a language by code. Before this, three separate
modules kept their own hand-written `ANCHOR_MODULES = {...}` dicts and each
one listed a different subset -- merging the language branches in 2026-09
found Turkish missing from two of them, which is not an error at runtime, it
just silently skips anchor validation. A single registry cannot drift.
"""
from __future__ import annotations

from types import ModuleType

from translate.render import RENDERERS

from .en import anchors as en_anchors, render as en_render
from .ru import anchors as ru_anchors, render as ru_render
from .tr import anchors as tr_anchors, render as tr_render

#: carrier code -> (anchor adapter, renderer instance)
PACKS: dict[str, tuple[ModuleType, object]] = {
    "en": (en_anchors, en_render.RENDERER),
    "tr": (tr_anchors, tr_render.RENDERER),
    "ru": (ru_anchors, ru_render.RENDERER),
}

#: carrier code -> the module exposing has_anchor / anchor_failures
ANCHORS: dict[str, ModuleType] = {c: a for c, (a, _) in PACKS.items()}

#: carrier code -> ASCII-folding function, for packs that have one.
#: Cyrillic targets have none: an ASCII domain skeleton needs no folding.
TRANSLITS = {
    "en": en_render.TRANSLIT,
    "tr": tr_render.TRANSLIT,
}

for _code, (_anchors, _renderer) in PACKS.items():
    RENDERERS[_code] = _renderer

LANGS = sorted(PACKS)

__all__ = ["PACKS", "ANCHORS", "TRANSLITS", "LANGS"]
