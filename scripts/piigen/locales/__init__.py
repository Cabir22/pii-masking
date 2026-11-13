"""Per-language locale packs.

Each language is a self-contained module exposing a single `LOCALE` object.
Adding a language means adding one file and one import -- no changes to the
generator or validator.

Design principle: a locale is *not* a translation of English. Each one carries
its own name morphology, address grammar, phone numbering plan, national ID
format (with real check digits where the algorithm is public), plate pattern,
bank/institution names, and register-specific phrase banks.

Azerbaijani is the full locale. As of 2026-09-03 the multilingual expansion
adds en/tr/ru back as thin *carrier packs*: the PII
stays Azerbaijani and is spliced from `az`'s pools, so a carrier pack only
overrides the language-facing pieces (months, weekdays, date formats, and
later phrases / render_value / anchors). The pre-scope-down full en/ru/tr
locales are in git history (`git show a7202b3^:scripts/piigen/locales/en.py`)
but describe the *old* design -- they generate English PII, which the
translation approach explicitly does not want.
"""

from __future__ import annotations

from .base import Locale, PhraseBank
from . import az
from . import en
from . import ru
from . import tr

LOCALES: dict[str, Locale] = {
    "az": az.LOCALE,
    "en": en.LOCALE,
    "tr": tr.LOCALE,
    "ru": ru.LOCALE,
}

__all__ = ["Locale", "PhraseBank", "LOCALES"]
