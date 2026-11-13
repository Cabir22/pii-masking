"""How a freshly minted Azerbaijani value is spelled in carrier-language text.

The PII stays Azerbaijani -- +994 numbers, AZ_FIN codes, Baku addresses,
Azerbaijani people. Only its *orthography* adapts to the language around it:
an English document writes "Baku", a Russian one writes "Баку", and neither
writes "Bakı".

Three rules, and which one applies is decided by the label's detection tier:

  * `pattern` / `hybrid` / `anchor_required` values -- phone numbers, emails,
    IBANs, every AZ_* identifier, IPs, MACs, URLs, cards, tokens, zipcodes --
    are NEVER touched. Every character is load-bearing, and none of them
    carry diacritics anyway.
  * `ml_context` values -- GIVENNAME, SURNAME, CITY, STREET -- get the
    language's orthography treatment.
  * DATE and TIME never reach here at all: they are minted through the
    *carrier* locale's `date_builder`, which emits correct script directly.

Registering a language means adding one `Renderer` -- no changes here or in
the harness.
"""
from __future__ import annotations

import random
import weakref
from dataclasses import dataclass, field
from typing import Callable

from piigen.config import DETECTION_TIERS
from piigen.text import fold_diacritics

# Values whose orthography may be rewritten. Everything else is verbatim.
ORTHOGRAPHY_LABELS = {label for label, tier in DETECTION_TIERS.items()
                      if tier == "ml_context"}
# Minted through the carrier locale's own builder, already in the right
# script -- must not be transformed a second time.
CARRIER_MINTED_LABELS = {"DATE", "TIME"}


class RendererError(RuntimeError):
    """A language pack is missing or incomplete."""


@dataclass
class Renderer:
    """One language's orthography rules.

    `place_map` and `name_fn` are the two halves of the job: established
    exonyms for the handful of places that have one ("Gəncə" -> "Гянджа" is
    not something a character map produces), and a mechanical fallback for
    the long tail.
    """

    lang: str
    # Established exonyms, keyed by the exact Azerbaijani surface form.
    place_map: dict = field(default_factory=dict)
    # Mechanical fallback for places with no exonym.
    place_fn: Callable[[str], str] = lambda s: s
    # How a person's name is written. Takes (value, rng) because some
    # languages deliberately mix forms (English keeps ~40% original).
    name_fn: Callable[[str, random.Random], str] = lambda s, rng: s

    def __call__(self, label: str, value: str, rng: random.Random) -> str:
        if label in CARRIER_MINTED_LABELS or label not in ORTHOGRAPHY_LABELS:
            return value
        if label in ("CITY", "STREET"):
            return self.place(value)
        return self.name_fn(value, rng)

    def place(self, value: str) -> str:
        if value in self.place_map:
            return self.place_map[value]
        # A street is "<stem> küçəsi"; the stem may itself have an exonym.
        parts = value.split(" ", 1)
        if len(parts) == 2 and parts[0] in self.place_map:
            return self.place_fn(f"{self.place_map[parts[0]]} {parts[1]}")
        return self.place_fn(value)



RENDERERS: dict[str, Renderer] = {}
"""code -> Renderer. Populated by `translate.lang` at import time; importing
`translate.lang` (which `get_renderer` does lazily) registers every pack."""


def _load_packs() -> None:
    """Import the language packs so they can register themselves.

    Deferred rather than done at module import: each pack imports `Renderer`
    from this module, so a top-level import here would be circular.
    """
    if not RENDERERS:
        import translate.lang  # noqa: F401  (its __init__ does the registering)


def get_renderer(lang: str) -> Renderer:
    _load_packs()
    try:
        return RENDERERS[lang]
    except KeyError:
        raise RendererError(
            f"no renderer for {lang!r}. Language packs present: "
            f"{sorted(RENDERERS)}. Add one under "
            f"scripts/translate/lang/<code>/render.py and register it in "
            f"scripts/translate/lang/__init__.py.") from None


def render_value(label: str, value: str, lang: str,
                 rng: random.Random) -> str:
    """Spell `value` (a freshly minted Azerbaijani value) for `lang` text."""
    return get_renderer(lang)(label, value, rng)
