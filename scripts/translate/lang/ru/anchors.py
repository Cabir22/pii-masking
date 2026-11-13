"""Russian licensing words for the `anchor_required` tier.

`scripts/piigen/anchors.py` is the Azerbaijani original and the contract this
mirrors; `anchors_en.py` is the English port and this file follows its shape
exactly, so the harness needs no Russian-specific branch.

Five labels carry no standalone signal -- a bare "34" is only an AGE because
something nearby says so -- and are valid only if a licensing word sits within
+/-80 characters. The Azerbaijani lists cannot do that job on a Russian
document: Wahoo translates "doğum tarixi" to "дата рождения" and the
Azerbaijani validator does not recognise the result, so every DATE, TIME, AGE,
BUILDINGNUM and CARD_SECURITY_CODE in a translated document would fail
silently.

The word lists themselves live in `piigen.anchors.ru`, which the Russian
calibration harness has been running against since the first batch. This
module is the adapter that presents them through the shared
`has_anchor` / `anchor_failures` interface, so there is one vocabulary rather
than two copies drifting apart.

Three properties carried over deliberately:

  * both pre- and post-position are checked -- Russian puts the licensing word
    on either side ("возраст 34" and "34 года");
  * Russian inflects heavily, so every stem matches as a word-prefix
    ("рожден-" covers "рождения", "рожденный", "рождён");
  * a Latin-transliterated spelling is included for each stem, because the
    noise injector strips diacritics and Wahoo occasionally leaves a
    romanised label ("data rozhdeniya") in an otherwise-Cyrillic document.

One addition the English port does not need: when Wahoo leaves a table header
in Azerbaijani ("ID;SOYAD;AD;YAŞ;..."), the anchor-required values in that row
are orphaned in a Russian document. Falling back to the Azerbaijani words for
that case recovers the row rather than invalidating five labels in it, and
costs nothing -- an Azerbaijani anchor word next to a value is evidence for
the label whatever language the rest of the document is in.
"""
from __future__ import annotations

# Same window and threshold as the Azerbaijani original -- properties of the
# task, not of the language.
from piigen.anchors import DEFAULT_WINDOW, MIN_UNANCHORED_LEN  # noqa: F401
from piigen.anchors import ANCHOR_REQUIRED as _AZ_ANCHOR_REQUIRED
from piigen.anchors import SELF_SIGNALLING as _SHAPE_SELF_SIGNALLING
from piigen.anchors import is_structural_position
from piigen.anchors.ru import ANCHOR_REQUIRED, SELF_SIGNALLING  # noqa: F401

__all__ = ["ANCHOR_REQUIRED", "SELF_SIGNALLING", "DEFAULT_WINDOW",
           "MIN_UNANCHORED_LEN", "has_anchor", "anchor_failures"]


def has_anchor(label: str, text: str, start: int, end: int,
               window: int = DEFAULT_WINDOW) -> bool:
    """True if `label` is licensed by the Russian context around [start:end).

    Identical logic to `piigen.anchors.has_anchor` against the Russian word
    lists, plus the Azerbaijani fallback described in the module docstring.
    `SELF_SIGNALLING` and `is_structural_position` are reused unchanged -- a
    date's *shape* and a heading number's *position* are language-independent.
    """
    pattern = ANCHOR_REQUIRED.get(label)
    if pattern is None:
        return True

    value = text[start:end]
    # Shape-based self-signalling is language-independent: 07.07.1971,
    # 2008-01-28 and HH:MM identify themselves whatever language wraps them.
    # piigen.anchors.ru.SELF_SIGNALLING deliberately does NOT repeat those
    # (its docstring says so) and only carries the Russian *worded* date --
    # so both dicts have to be consulted. Missing this fallback failed 4.5%
    # of RU DATE/TIME entities: every log-bracket time "[2025-05-10 15:26]"
    # and every numeric date with no nearby "дата"/"в" word (2026-09-06).
    for sig_map in (_SHAPE_SELF_SIGNALLING, SELF_SIGNALLING):
        sig = sig_map.get(label)
        if sig is not None and sig.match(value):
            return True

    if is_structural_position(text, start, end):
        return False

    left = text[max(0, start - window):start]
    right = text[end:end + window]
    if pattern.search(left) or pattern.search(right):
        return True

    az_pattern = _AZ_ANCHOR_REQUIRED.get(label)
    return bool(az_pattern
                and (az_pattern.search(left) or az_pattern.search(right)))


def anchor_failures(text: str, entities: list[dict],
                    window: int = DEFAULT_WINDOW) -> list[dict]:
    """Every entity whose label requires an anchor and does not have one."""
    return [e for e in entities
            if e.get("label", "") in ANCHOR_REQUIRED
            and not has_anchor(e["label"], text, e["start"], e["end"], window)]
