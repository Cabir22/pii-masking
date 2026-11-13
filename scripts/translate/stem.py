"""Is this mention the same entity as that one? (`Sumqayıt` / `Sumqayıtda`).

Used by both translation runners to mint ONE fresh value per entity, however
the Azerbaijani source inflected or cased each mention. run_ru.py has done
this since the 27% repeat-mention defect; run.py (EN/TR) grouped by the exact
string until 19 Oct 2026, so `Ərkixanım` / `Ərkixanımı` became `Afig` /
`Nikolay` in one English document -- 5,797 of v4.1's 121,900 labelled train
documents had such a pair.
"""
from __future__ import annotations


def az_lower(word: str) -> str:
    """Lower-case the Azerbaijani way: `I` -> `ı`, `İ` -> `i`. Plain
    `.lower()` makes `ELDARLI` `eldarli`, a different stem from `Eldarlı`."""
    return word.replace("I", "ı").replace("İ", "i").lower()


# Azerbaijani nominal case endings and the copula, longest first. A closed
# set: a suffix outside it means a different word, not an inflection of the
# same one. Used only to decide whether two entity mentions are the same
# entity ("Göygöl" / "Göygöldə", "Səidrzayev" / "Səidrzayevin") so they can be
# minted to one value.
_AZ_CASE_SUFFIXES = sorted(
    ["nın", "nin", "nun", "nün", "ın", "in", "un", "ün", "n",
     "nda", "ndə", "da", "də", "ndan", "ndən", "dan", "dən",
     "nı", "ni", "nu", "nü", "na", "nə", "ya", "yə", "a", "ə", "ı", "i",
     "u", "ü", "yla", "ylə", "la", "lə", "sı", "si", "su", "sü",
     "ları", "ləri", "dır", "dir", "dur", "dür", "dırlar", "dirlər"],
    key=len, reverse=True)


def az_stem(word: str, rounds: int = 2) -> str:
    """Strip up to two stacked case endings, keeping at least four letters.

    Only good enough to tell two mentions of one entity apart from two
    different entities -- not a real morphological analyser.
    """
    w = az_lower(word)
    for _ in range(rounds):
        for suf in _AZ_CASE_SUFFIXES:
            if len(w) - len(suf) >= 4 and w.endswith(suf):
                w = w[:-len(suf)]
                break
        else:
            break
    return w
