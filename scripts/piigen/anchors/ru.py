"""Russian context-anchor rules for the ``anchor_required`` detection tier.

Parallel to ``anchors.py``, which is entirely Azerbaijani-keyed. Five labels
carry no standalone signal and need a licensing word within
``anchors.DEFAULT_WINDOW`` (80) characters, on either side::

    AGE  BUILDINGNUM  CARD_SECURITY_CODE  DATE  TIME

Wahoo will happily translate ``doğum tarixi`` to ``дата рождения`` but the
Azerbaijani-keyed validator would not recognise the result, silently
invalidating every one of those entities across the whole Russian run. This
module supplies the Russian equivalents.

Integration (a shared-harness change, owned by whoever owns ``anchors.py`` --
do NOT fork the module): ``anchors.has_anchor`` / ``anchor_failures`` should
take the carrier language and dispatch to the matching tables. Everything here
mirrors the names and shapes in ``anchors.py`` so that dispatch is a lookup,
not a rewrite:

    ANCHOR_REQUIRED         dict[label, re.Pattern]   -- licensing words
    SELF_SIGNALLING         dict[label, re.Pattern]   -- shapes needing none
    STRUCTURAL_GROUP_WORDS  re.Pattern                -- "Группа 2", "Пункт 3"

Design notes carried over from ``anchors.py``:

* Lists are deliberately generous, not minimal -- tightening here rejects
  natural Russian, and the tier's job is recall.
* Both pre- and post-position are checked by the caller; Russian, like
  Azerbaijani, licenses from either side ("в возрасте 34 лет" / "34 года").
* Latin transliterations are listed next to the Cyrillic because mixed-script
  business text and the ``strip_diacritics``-style noise both produce them,
  and a noised document must not fail a gate the clean one passes.
* Russian is fused-inflectional: a stem is matched as a word-prefix
  (``регистрац`` covers регистрация / регистрации / зарегистрирован? no --
  prefix only, so зарегистр… is listed separately where it matters).
"""

from __future__ import annotations

import re

from .az import DEFAULT_WINDOW, MIN_UNANCHORED_LEN  # re-exported for callers

__all__ = [
    "ANCHOR_REQUIRED", "SELF_SIGNALLING", "STRUCTURAL_GROUP_WORDS",
    "DEFAULT_WINDOW", "MIN_UNANCHORED_LEN",
]

_CYR = "а-яёА-ЯЁ"


def _words(*variants: str) -> str:
    """Alternation matching each variant as a whole word or word-prefix, not
    inside a longer word. Mirrors ``anchors._words`` but with a Cyrillic-aware
    left boundary (``\\w`` alone would treat а Cyrillic letter as a word char
    on Py3, which is what we want, but an explicit class keeps intent clear).
    """
    return r"(?<![" + _CYR + r"\w])(?:" + "|".join(variants) + r")"


ANCHOR_REQUIRED: dict[str, re.Pattern] = {
    # возраст / в возрасте / N лет / N года / родился / рождения / исполнилось
    # + N-летний (adjective) and elderly/minor descriptors that co-occur with
    # a bare age in this corpus's complaint prose ("тот пожилой человек 57").
    "AGE": re.compile(
        _words("возраст", "лет\\b", "летн", "года\\b", "годик", "годов\\b",
               "родил", "рождени", "рожд\\.", "исполн", "испол-",
               "пожил", "престарел", "несовершеннолетн", "малолетн",
               "vozrast", "let\\b", "letn", "rodil")
        + r"\w*", re.IGNORECASE),

    # дом / кв. / корпус / строение / подъезд / улица / проспект / переулок /
    # бульвар / шоссе / микрорайон / посёлок / адрес / квартал
    "BUILDINGNUM": re.compile(
        _words("дом\\b", "д\\.", "кв\\b", "кв\\.", "квартир", "корпус", "корп\\.",
               "строени", "стр\\.", "здани", "подъезд", "улиц", "ул\\.",
               "проспект", "просп", "пр\\.", "пр-?кт", "пр-?т", "переул", "пер\\.",
               "бульвар", "б-р", "шоссе", "микрорайон", "мкр", "мкрн",
               "посёлок", "поселок", "пос\\.", "адрес", "квартал", "объект",
               "dom\\b", "kv\\b", "korpus", "ulic", "prospekt", "adres")
        + r"\w*"
        # underscore-joined CSV/YAML headers ("№_Здания;70B", "Nomer_Zdaniya")
        # -- the word-boundary form above cannot see a stem after a "_".
        + r"|№[_\s]*(?:здани|дом|корпус)\w*|nomer[_\s]*zdani\w*",
        re.IGNORECASE),

    # CVV/CVC, plus the spelled-out Russian phrasings. Kept fairly narrow: a
    # bare 3-digit number next to a generic "код" is not reliably a card
    # security code, but "код ... безопасности" with a word or two between
    # (seen in real output: "код kzrt для подтверждения безопасности: 633") is.
    "CARD_SECURITY_CODE": re.compile(
        _words("cvv", "cvc", "cvv2", "cvc2")
        + r"\w*"
        + r"|код\w*(?:\s+\w+){0,3}\s+безопасност\w*"
        + r"|безопасн\w*\s+код\w*"
        + r"|защитн\w*\s+код\w*"
        + r"|секретн\w*\s+код\w*"          # "секретный код карты был 715"
        + r"|код\w*\s+карт\w*"             # "код карты: 660"
        # A bare "код" next to the value. Deliberately permissive, and only
        # because the AZERBAIJANI list already is: piigen.anchors licenses a
        # bare "kod"/"kodu", so a document whose CVV is licensed in the source
        # by nothing more than "974 kodu ilə" loses its licence the moment it
        # is faithfully translated to "код 974". Holding Russian to a stricter
        # standard than the corpus it is derived from rejected 66 source
        # documents (435 queue rows) that were correct translations of
        # correctly-labelled AZ spans (2026-09-07). Whether a bare "код"
        # SHOULD license a CVV is a question for the Azerbaijani taxonomy,
        # not something to answer differently per carrier language.
        + r"|(?<![\w])код\w*"
        + r"|проверочн\w*\s+код\w*\s+карт\w*"
        + r"|код\w*\s+проверки\s+подлинности\s+карт\w*"
        + r"|(?:трёх|трех)значн\w*\s+код\w*",
        re.IGNORECASE),

    # дата / дата рождения / подписан / заключён / регистрация / выдан /
    # действителен до / срок действия / оформлен
    "DATE": re.compile(
        _words("дата", "дате\\b", "даты\\b", "датой", "датир",
               "родил", "рождени", "подписа", "заключ", "регистрац",
               "зарегистр", "выдан", "выдач", "оформл", "действ",
               "срок\\b", "число\\b", "числа\\b",
               "data\\b", "rodil", "podpisa", "vydan")
        + r"\w*"
        + r"|срок\w*\s+действ\w*"
        + r"|действ\w*\s+до\b",
        re.IGNORECASE),

    # время / часов / начало / окончание / приём / встреча / назначено / сеанс
    "TIME": re.compile(
        _words("время", "времени", "час\\b", "часов", "часа\\b",
               "начал", "начин", "начало", "законч", "оконч",
               "приём", "прием", "встреч", "назнач", "сеанс",
               "vremya", "chas", "nachal")
        + r"\w*", re.IGNORECASE),
}


# --- shapes that identify themselves ------------------------------------- #
# Numeric forms (12.03.1990, 1990-03-12, HH:MM) are already covered by
# anchors.SELF_SIGNALLING and are language-independent -- not repeated here.
# This adds the Russian worded date, mirroring what locales/ru.py date()
# emits: "21 февраля 1956" / "«21» февраля 1956" / weekday-wrapped. The year
# word (` г.`, ` года`) stays optional here: since 17 Oct it is written outside
# the DATE span, but older data and other writers still carry it inside.
_WD_RU = r"[" + _CYR + r"]+"
SELF_SIGNALLING: dict[str, re.Pattern] = {
    "DATE": re.compile(
        r"^(?:" + _WD_RU + r",\s+)?"                       # optional leading weekday
        r"«?\d{1,2}»?\s+"                                  # day, maybe «guillemeted»
        r"[" + _CYR + r"]+\.?\s+"                          # month (genitive) or abbr
        r"\d{4}"                                           # year
        r"(?:\s+(?:г\.|года))?"                            # optional  г. / года
        r"(?:,\s+" + _WD_RU + r")?"                        # optional trailing weekday
        r"$",
        re.IGNORECASE),
}


# --- structural-number detection --------------------------------------- #
# Russian equivalents of anchors.py's `group_word` pattern: a digit right
# after one of these is document furniture ("Раздел 3", "Пункт 2"), not PII.
# Feed this into anchors._STRUCTURAL_BEFORE alongside the Azerbaijani list.
STRUCTURAL_GROUP_WORDS: re.Pattern = re.compile(
    r"(?:Группа|Пункт|Раздел|Статья|Глава|Таблица|Рисунок|Схема|Пример|"
    r"Вопрос|Вариант|Этап|Класс|Курс|Уровень|Абзац|Часть|Параграф|Строка|"
    r"Столбец|Версия|Приложение|Задача|Шаг|Позиция|Пп|п\.)[ \t]+$",
    re.IGNORECASE)
