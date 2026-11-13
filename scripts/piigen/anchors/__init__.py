"""Context-anchor vocabularies, one module per language.

Five labels carry no standalone signal -- a bare "34" is only an AGE because
something nearby says so -- and are valid only when a licensing word sits
within `DEFAULT_WINDOW` characters on either side.

`az` is the original and the contract every other module mirrors; `ru` is the
Russian vocabulary, needed because Wahoo translates "doğum tarixi" to "дата
рождения" and the Azerbaijani lists do not recognise the result.

The Azerbaijani names are re-exported here unprefixed, so the generator and
the corpus validators keep reading `from piigen.anchors import has_anchor`
with no change: Azerbaijani IS the source language, and everything that
imports this package bare is working on Azerbaijani text.

Was two modules named `anchors.py` and `anchors_ru.py`, with a THIRD file
also called `anchors_ru.py` living under `scripts/translate/` (the adapter
that presents these lists through the shared `has_anchor` interface). Two
different files with the same name, one importing the other, is a trap; the
adapters now live in `translate/lang/<code>/anchors.py`.
"""
from __future__ import annotations

from . import az, ru                                            # noqa: F401
from .az import (  # noqa: F401
    ANCHOR_REQUIRED, DEFAULT_WINDOW, MAX_STRUCTURAL_DIGITS,
    MIN_UNANCHORED_LEN, SELF_SIGNALLING, anchor_failures, has_anchor,
    is_structural_position, resolvable_unanchored, structural_kind,
)

# Derived from `az`, not hand-listed: a hand-written subset is exactly the
# drift this package exists to stop. Asserted at import so a name added to
# `az.py` and forgotten here fails loudly instead of at some caller's import.
__all__ = ["az", "ru"] + [n for n in dir(az)
                          if not n.startswith("_") and n not in
                          ("annotations", "re")]
_missing = [n for n in __all__ if n not in ("az", "ru") and n not in globals()]
if _missing:  # pragma: no cover - a source edit, not a runtime path
    raise ImportError(
        f"piigen.anchors re-exports are out of date: {_missing} exist in "
        f"anchors/az.py but are not imported in anchors/__init__.py")
