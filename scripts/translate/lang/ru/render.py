"""Russian renderer: how a minted Azerbaijani value is spelled in Russian
carrier text.

Full Cyrillic transliteration in the Soviet-standard forms people carry
on their Russian-language documents (Hüseyn -> Гусейн), not a naive
character map, with exonyms from `piigen.locales.ru`.

Registered into `translate.render.RENDERERS` by `translate.lang`.
"""
from __future__ import annotations

import random
import weakref  # noqa: F401

from piigen.text import fold_diacritics  # noqa: F401
from translate.render import Renderer  # noqa: F401
from piigen.locales import ru as _ru_locale


# --- Russian -------------------------------------------------------------
# Russian text about Azerbaijan uses the Soviet-standard spellings people
# carry on their own Russian-language documents -- Гусейн, not a naive
# character map's "Хюсейн". The full rule set, the exonym table and the
# digraph handling live in `piigen.locales.ru`, which the Russian calibration
# harness has run against since the first batch; importing it here keeps one
# implementation rather than a second copy that drifts.
#
# Unlike English, Russian never keeps the original spelling: a Cyrillic
# document with "Əli Məmmədov" in it is a defect, not a variant, so name_fn
# ignores its rng and always transliterates.

RU_PLACE_MAP = dict(_ru_locale.EXONYMS)


def _ru_place(value: str) -> str:
    return _ru_locale.transliterate(value)


def _ru_name(value: str, rng: random.Random) -> str:
    return _ru_locale.transliterate(value)


RENDERER = Renderer(lang="ru", place_map=RU_PLACE_MAP,
                    place_fn=_ru_place, name_fn=_ru_name)
