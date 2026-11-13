"""The translation prompt.

This is a tuned artifact, not boilerplate. Its current form was validated in
the Phase-0.5 smoke test: 12/12 sentinels survived across all six length
buckets, length ratios 0.94-1.11, register preserved, zero preambles. Change
it only with a smoke-test run to back the change up
(`python scripts/translate/smoke_test.py`).

Four things it has to buy, in order of how expensive the failure is:
  1. sentinel survival -- a dropped or renumbered token sends the whole
     document to the repair queue;
  2. faithfulness -- paraphrase quietly changes what the model learns from;
  3. register -- the corpus spans 20 registers on purpose and an LLM's
     default is to normalise all of them toward neutral prose;
  4. no preamble -- "Here is the translation:" is cheap to detect but
     cheaper to prevent.
"""
from __future__ import annotations

from translate.sentinel import CLOSE, OPEN

LANG_NAME = {"en": "English", "tr": "Turkish", "ru": "Russian"}

# Per-language nudges. Kept minimal -- the more said, the more the model
# treats translation as a creative brief.
_LANG_NOTES = {
    "en": "",
    # The concrete examples are not decoration. Azerbaijani and Turkish are
    # sister languages, so a word that is ALREADY almost Turkish does not
    # trigger the model's "translate this" reflex the way an obviously
    # foreign word does -- and an untagged Azerbaijani NAME reads as a proper
    # noun to preserve verbatim. Measured on the first 17.6k Turkish records
    # (2026-09-06): 96% of leftover-Azerbaijani rejections were a single
    # unconverted word, led by exactly these two classes -- surnames
    # (məmmədov 28, məmməd 17, rəşad 14, həsənov 10) and near-Turkish common
    # words (müştəri 27, məbləğ 19, təhlükəsizlik 14). Abstract guidance
    # ("write it in its Turkish form") was already present and was not
    # enough; worked pairs are.
    "tr": (" Use natural Turkish orthography (ı, İ, ğ, ş, ö, ü, ç) and "
           "agglutinative morphology, not word-by-word English."
           " Azerbaijani and Turkish look alike, so words that are ALMOST "
           "Turkish still have to be converted:"
           " ordinary words are TRANSLATED (müştəri->müşteri, məbləğ->tutar,"
           " təhlükəsizlik->güvenlik, müraciət->başvuru, miqdar->miktar,"
           " qiymət->fiyat, sənəd->belge, məlumat->bilgi, tarix->tarih,"
           " məlumat bazası->veritabanı, prosedur->prosedür, texniki->teknik,"
           # M6 (re-check): never `uyarınca` ("in accordance with")
           " üzrə->ile ilgili / kapsamında / için, or -de in an address;"
           " never uyarınca, which means \"in accordance with\");"
           " personal and place names are only RE-SPELLED, never swapped for"
           " a Turkish cognate (Bakı->Bakü, Azərbaycan->Azerbaycan,"
           " Məmmədov->Memmedov, Rəşad->Reşad, Əliyev->Aliyev,"
           " Xətai->Hatai -- never Mehmet, never Ali)."
           " This applies to names in signatures, headers and quoted text"
           " even though they carry no placeholder token."
           # D-56c (2), (7): case tags after placeholders; no hyphen endings
           " A placeholder may be followed by a case tag in curly braces, such"
           " as {GEN} or {LOC}: the name or place it stands for had that case"
           " in the Azerbaijani text (GEN of, DAT to, ACC object, LOC in/at,"
           " ABL from, INS with, REL the one in, COP is). In your Turkish,"
           " write the placeholder followed by the tag the Turkish sentence"
           " needs, with no space and no ending of your own: the Turkish"
           " ending is added for you. Use only GEN, DAT, ACC, LOC, ABL, INS,"
           " REL, COP, and no tag when the name needs no ending; a name right"
           # M6: no genitive before `tarafından` (`Memmedhanov tarafından`)
           " before tarafından takes no tag and no ending (⟦0⟧ tarafından,"
           " never ⟦0⟧{GEN} tarafından). After a"
           " number, time or code, a Turkish ending takes an apostrophe"
           " (18:53'te), never a hyphen."),
    "ru": (" Use Cyrillic with correct case endings throughout."),
}


# Letters that must NOT appear in the output, per target language. This is
# the set the source alphabet has and the TARGET alphabet does not -- getting
# it wrong is expensive in both directions.
#
# Turkish is the trap: ç ğ ı ö ş ü are all core Turkish letters (the alphabet
# is a b c ç d e f g ğ h ı i j k l m n o ö p r s ş t u ü v y z). Banning them
# told the model to avoid the very letters Turkish requires, and directly
# contradicted this prompt's own "Use natural Turkish orthography (ı, İ, ğ,
# ş, ö, ü, ç)" note -- pushing output toward ASCII-folded Turkish. Only the
# three Azerbaijani letters Turkish genuinely lacks belong here (2026-09-06).
_FORBIDDEN_LETTERS = {
    "en": "ə, ğ, ı, ö, ş, ç, ü",     # English has none of them
    "tr": "ə, q, x",                 # Turkish has ç ğ ı ö ş ü natively
    "ru": "any Latin letters",
}


def system_prompt(lang: str) -> str:
    target = LANG_NAME[lang]
    azletter = _FORBIDDEN_LETTERS[lang]
    return (
        f"You are a professional translator. Translate the user's text from "
        f"Azerbaijani into {target}.{_LANG_NOTES.get(lang, '')}\n"
        f"Rules:\n"
        f"- Translate faithfully, sentence for sentence. Do not paraphrase, "
        f"summarise, explain, add, or omit anything.\n"
        f"- NEVER invent content that is not in the source. In particular do "
        f"not add email addresses, names, phone numbers, ID numbers, "
        f"signature blocks, or header fields such as 'Sender:', 'From:' or "
        f"'To:'. If the source has an incomplete header, a bare label with no "
        f"value, or a signature with no name, translate it exactly that way "
        f"and leave it incomplete. Inventing a plausible-looking address or "
        f"person is the single worst thing you can do here.\n"
        # Deliberately NOT written as "tokens of the form ⟦N⟧": the model
        # echoed that literal string into one Turkish document (2026-09-06),
        # because "reproduce every one EXACTLY as written" applies just as
        # well to the example as to a real token. Only concrete, numbered
        # instances are shown now, so there is no token-shaped string in the
        # prompt that is not also a real token.
        f"- The text contains placeholder tokens: a number wrapped in "
        f"{OPEN} {CLOSE} (for example {OPEN}0{CLOSE}, {OPEN}1{CLOSE}, "
        f"{OPEN}2{CLOSE}). Reproduce every one "
        f"EXACTLY as written: same count, same numbers, same {OPEN} {CLOSE} "
        f"characters, no spaces inside. Do not translate, renumber, reorder "
        f"the digits of, or drop them. They stand in for names and numbers "
        f"that must not change.\n"
        f"- Translate EVERYTHING else that is Azerbaijani: ordinary words, "
        f"headings, ALL-CAPS labels, table cells, log-message text, and "
        f"proper nouns. Write place names and any personal names in their "
        f"usual {target} spelling (for example Bakı as its {target} form, "
        f"Azərbaycan as its {target} form). An Azerbaijani word left as-is "
        f"is an error. Apply this to EVERY part of a name, not just the "
        f"first: a half-converted name is an error too.\n"
        f"- The ONLY things you copy across unchanged are: the numbered "
        f"placeholder tokens, and email addresses, web URLs and literal code or file "
        f"paths THAT CONTAIN NO Azerbaijani letters. If such a token does "
        f"contain Azerbaijani letters, transliterate just those letters "
        f"(merkezi_dispetcer@..., not mərkəzi_dispetçer@...). A word that "
        f"merely looks technical (like Merkezi_Sistem) is translated "
        f"normally.\n"
        f"- Preserve the layout: line breaks, blank lines, table pipes, "
        f"bullet markers, headings, and code blocks stay as they are -- but "
        f"translate the Azerbaijani text INSIDE them, including CSV/"
        f"semicolon-delimited header rows, YAML or config keys "
        f"(musteri_melumatlari:, soyadi:), log-line labels, and data-dump "
        f"field names. Only the numbered placeholder tokens and literal "
        f"identifiers stay unchanged.\n"
        f"- Keep the register and tone of the source. A terse log line stays "
        f"terse; an angry complaint stays angry; a formal notice stays "
        f"formal. Do not smooth informal text into business prose.\n"
        f"- Text already in {target} stays as it is.\n"
        f"- Your output must not contain {azletter}. If you are about to "
        f"write an Azerbaijani word, translate or transliterate it instead.\n"
        f"- Output ONLY the translation. No preamble, no notes, no "
        f"explanation, no surrounding quotes."
    )


def build_messages(templated: str, lang: str) -> list[dict]:
    return [{"role": "system", "content": system_prompt(lang)},
            {"role": "user", "content": templated}]


def token_budget(templated: str, *, floor: int = 512, ceiling: int = 16384,
                 slack: float = 1.8) -> int:
    """max_tokens for a document of this size.

    Sized off the source rather than fixed: too small truncates the tail, and
    a truncated tail takes its sentinels with it -- which surfaces as a
    "dropped slot" failure that looks like a model problem but is a budget
    problem. `slack` covers the target language being wordier than the source
    plus tokenizer differences (Cyrillic in particular costs more tokens per
    character than Latin).
    """
    approx_tokens = len(templated) / 2.5
    return int(max(floor, min(ceiling, approx_tokens * slack + 256)))
