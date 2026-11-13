"""English renderer: how a minted Azerbaijani value is spelled in English
carrier text.

Registered into `translate.render.RENDERERS` by `translate.lang`.
"""
from __future__ import annotations

import random
import weakref  # noqa: F401

from piigen.text import fold_diacritics  # noqa: F401
from translate.render import Renderer  # noqa: F401


# --- English --------------------------------------------------------------
# English text about Azerbaijan anglicises places ("Baku", not "Bakı") but is
# genuinely mixed on people: a news article writes "Ali Mammadov", a pasted
# form or database export keeps "Əli Məmmədov". Generating both teaches the
# model to recognise a name either way; the split is a knob, not a constant.
EN_FOLD_NAME_RATE = 0.6

# Cities whose English form is not just the diacritic-folded spelling.
# The long tail falls through to fold_diacritics().
EN_PLACE_MAP = {
    "Bakı": "Baku", "Gəncə": "Ganja", "Sumqayıt": "Sumgait",
    "Naxçıvan": "Nakhchivan", "Şuşa": "Shusha", "Şəki": "Sheki",
    "Şirvan": "Shirvan", "Mingəçevir": "Mingachevir", "Xankəndi": "Khankendi",
    "Lənkəran": "Lankaran", "Şəmkir": "Shamkir", "Yevlax": "Yevlakh",
    "Xaçmaz": "Khachmaz", "Şamaxı": "Shamakhi", "Quba": "Guba",
    "Zaqatala": "Zagatala", "Ağdam": "Aghdam", "Füzuli": "Fuzuli",
    "Cəbrayıl": "Jabrayil", "Qəbələ": "Gabala", "Xudat": "Khudat",
    "Göyçay": "Goychay", "Salyan": "Salyan", "Bərdə": "Barda",
    "Xırdalan": "Khirdalan", "Sabirabad": "Sabirabad", "Astara": "Astara",
    "Xocalı": "Khojaly", "Laçın": "Lachin", "Kəlbəcər": "Kalbajar",
}

_EN_STREET_TYPES = {
    "küçəsi": "Street", "küç.": "St.", "prospekti": "Avenue",
    "pr.": "Ave.", "döngəsi": "Lane",
}

# Azerbaijani -> English transliteration.
#
# NOT `piigen.text.fold_diacritics`, which is the *noise* map: it models
# OCR/keyboard-degraded Azerbaijani (ə->e, ş->s, ç->c) and produces "Eli
# Memmedov", a spelling no English text uses. English renders the sounds:
# ş->sh, ç->ch, ğ->gh, x->kh, and the Azerbaijani letters c (/dʒ/) and
# q (/g/) become j and g.
#
# The exonym table above is the evidence for every rule here -- Xaçmaz ->
# Khachmaz (x->kh, ç->ch), Cəbrayıl -> Jabrayil (c->j, ə->a), Qəbələ ->
# Gabala (q->g), Ağdam -> Aghdam (ğ->gh).
#
# ə is the one genuinely irregular letter: Əli -> Ali but Şəki -> Sheki.
# ->a is the commoner choice in personal names (Əliyev -> Aliyev, Məmməd ->
# Mammad), and the places where it goes to e are exactly the ones the exonym
# table already covers by hand.
_EN_TRANSLIT = {
    "ə": "a", "Ə": "A",
    "ç": "ch", "Ç": "Ch",
    "ş": "sh", "Ş": "Sh",
    "ğ": "gh", "Ğ": "Gh",
    "x": "kh", "X": "Kh",
    "c": "j", "C": "J",
    "q": "g", "Q": "G",
    "ı": "i", "İ": "I",
    "ö": "o", "Ö": "O",
    "ü": "u", "Ü": "U",
}


def en_translit(value: str) -> str:
    """Azerbaijani surface form -> its usual English spelling."""
    return "".join(_EN_TRANSLIT.get(ch, ch) for ch in value)


def _en_place(value: str) -> str:
    """Transliterate, and translate a trailing Azerbaijani street-type word."""
    for az_type, en_type in _EN_STREET_TYPES.items():
        if value.endswith(" " + az_type):
            stem = value[: -(len(az_type) + 1)]
            return f"{en_translit(stem)} {en_type}"
    return en_translit(value)


def _en_name(value: str, rng: random.Random) -> str:
    """Mixed on purpose: a news article writes "Ali Mammadov", a pasted form
    or database export keeps "Əli Məmmədov". Both occur in real English text
    about Azerbaijan, so the model should see both."""
    return en_translit(value) if rng.random() < EN_FOLD_NAME_RATE else value


RENDERER = Renderer(lang="en", place_map=EN_PLACE_MAP,
                    place_fn=_en_place, name_fn=_en_name)

#: ASCII-folding used by validate._domain_skeleton
TRANSLIT = en_translit
