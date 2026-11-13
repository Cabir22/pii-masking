"""D-47: noise the model explained or corrected in the text itself.

D-47a  explained_typos(text): the model writes a typo or an OCR artifact and
       then says so: `vəziyyit (typo)`, `l0st (0/O qarışığı)`, `(xata -> xəta)`,
       `# OCR-style artifact`. No real document does that, in any genre.
D-47b  self_corrections(text): a bracketed self-correction,
       `aparılmalıddır (yox, aparılmalıdır)`, `(xəta... yox, problem)`,
       `(daha doğrusu, …)`. Plausible in a chat, an email or a complaint,
       never in official, legal or record text (`FORMAL` doc types).
D-47e  placeholders(text): an unfilled template slot, `[Məhkəmənin adı]`,
       `[Şirkət Adı]`; real form blanks (`[İmza]`, `[Möhür yeri]`) stay.

Each returns the matched snippets (empty: nothing found). The patterns are
kept narrow on purpose: a bare `(xəta)`, `(yəni …)` or `(sic)` is an ordinary
gloss and is not caught; `OCR` alone (a tender for OCR scanners) is not caught.
"""
from __future__ import annotations

import re
import unicodedata

# Document types where a bracketed self-correction is plausible (D-47b keeps them).
CONVERSATIONAL = frozenset({
    "live_chat", "whatsapp_thread", "social_media", "forum_post",          # chat
    "customer_email", "email_thread",                                      # email
    "complaint_letter",                                                    # complaints
    "call_center_transcript", "voicemail_transcript",                      # spoken
    "survey_response", "support_ticket",                                   # a person's own words
})


def is_formal(doc_type: str | None) -> bool:
    return doc_type not in CONVERSATIONAL


_I = re.IGNORECASE
_BR = r"[^()\n]"
# D-47a ---------------------------------------------------------------------
_META = re.compile(r"\(" + _BR + r"{0,40}?\b(?:typos?|ocr[- ]?(?:style|artifact|artefakt|error|xətası|xetasi|səhvi)"
                   r"|noise|artifact|artefakt)\b" + _BR + r"{0,60}\)", _I)
_NOISE_METADATA = re.compile(r"noise\s*:\s*(?:very\s+)?(?:low|high|moderate|medium)\b", _I)
_BARE_OCR = re.compile(r"\(\s*ocr\s*\)", _I)              # `l0g (OCR)`; not `tanıma (OCR)`
_OCR_GLOSS = re.compile(r"(?:tanıma|tanınma|tanima|recognition|oxuma)\s*$", _I)
_SQUARE = re.compile(r"\[\s*ocr[- ]?(?:style\s+)?artifact\s*\]|#\s*ocr[- ]style|ocr[- ]style\s+artifact", _I)
# a lone confusion pair `0/O`, `'1'/'l'`; never part of a date or a number (`25/10/1954`)
_PAIR = r"(?<![\w/.])(?:['\"]?[0O1lI]['\"]?\s*/\s*['\"]?[0O1lI]['\"]?)(?![\w/.])"
_CONFUSION_WORD = r"(?:qarış|qariş|qaris|confusion|əvəz|evez|ocr|nasazl)"
# the pair with a confusion word in the same bracket or within 60 characters before it;
# `I/O` (input/output) is a real term and never counts
_CONFUSION = re.compile(r"(?:" + _CONFUSION_WORD + r"[^\n]{0,60}?|\(" + _BR + r"{0,40}?)" + _PAIR
                        + r"|" + _PAIR + r"\s*\)?\s*" + _CONFUSION_WORD
                        + r"|\b[0O1lI]\s+instead\s+of\s+[0O1lI]\b", _I)
_IO = re.compile(r"(?<![\w/])I\s*/\s*O(?![\w/])", _I)
_ARROW = re.compile(r"\(\s*([^\s()]{2,30})\s*(?:->|→|=>)\s*([^\s()]{2,30})\s*\)")


def _fold(s: str) -> str:
    s = s.casefold().translate(str.maketrans("əışçğöü0", "eiscgouo"))
    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))


def _near(a: str, b: str) -> bool:
    """Same word up to a typo: equal after folding, at most 2 edits, or at most
    4 edits with the same first two letters (`malamt -> məlumat`)."""
    a, b = _fold(a), _fold(b)
    if a == b:
        return True
    limit = 4 if a[:2] == b[:2] else 2
    if abs(len(a) - len(b)) > limit:
        return False
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1] <= limit


def explained_typos(text: str) -> list[str]:
    hits = []
    for m in _META.finditer(text):
        if not _NOISE_METADATA.search(m.group(0)):
            hits.append(m.group(0))
    for m in _BARE_OCR.finditer(text):
        if not _OCR_GLOSS.search(text[max(0, m.start() - 25):m.start()]):
            hits.append(text[max(0, m.start() - 12):m.end()])
    hits += [m.group(0) for m in _SQUARE.finditer(text)]
    for m in _CONFUSION.finditer(text):
        pair = re.search(_PAIR, m.group(0))
        if pair is None or not _IO.fullmatch(pair.group(0).strip("'\" ")):
            hits.append(m.group(0))
    hits += [m.group(0) for m in _ARROW.finditer(text) if _near(m.group(1), m.group(2))]
    return hits


# D-47b ---------------------------------------------------------------------
_NO = r"(?:yox|xeyr)"
_LEAD_NO = re.compile(r"\(\s*" + _NO + r"\s*[,.!:;\-–—]\s*" + _BR + r"{1,80}\)", _I)
# `(xəta... yox, problem)`, `(melumat - yox, məlumat)`: at most 3 words before `yox`
_INNER_NO = re.compile(r"\(\s*[^\s()]+(?:\s+[^\s()]+){0,2}?\s*(?:\.\.\.|…|[-–—,])?\s+" + _NO
                       + r"\s*[,!]\s*" + _BR + r"{1,60}\)", _I)
_RATHER = re.compile(r"\(\s*daha\s+do[gğ]rusu\s*,?\s*" + _BR + r"{1,60}\)", _I)
_FIX = re.compile(r"\(\s*d[uü]z[eə]li[sş]\s*:\s*([^\s()]+(?:\s+[^\s()]+){0,2})\s*\)", _I)
# `texnikı (yəni, texniki)`: `yəni` + the word before, respelt. `xəta (yəni, nasazlıq)` is a gloss.
_RESPELT = re.compile(r"([^\s()]+)\s*\(\s*y[əe]ni\s*,?\s+([^\s()]+?)[.…]*\s*\)", _I)


# D-47e ---------------------------------------------------------------------
_SQUARE_BR = re.compile(r"\[([^\[\]\n]{2,60})\](?!\()")
_SLOT_POSSESSIVE = {"adi", "unvani", "nomresi", "tarixi",          # folded: adı, ünvanı, nömrəsi, tarixi
                    "adiniz", "soyadiniz", "sirketi"}
_SLOT_BARE = {"rayon", "seher", "sirket", "tarix", "vezife", "kod", "unvan", "e-poct", "email",
              "soyad", "mebleg"}
_FORM_BLANK = re.compile(r"imza|möhür|mohur|mühür|muhur", re.I)     # `[İmza]`, `[Möhür yeri]`: kept
_ANNOTATION = {"sehv", "duzgun", "kohne", "yanlis", "xetali", "gorunmeyen"}  # `[Səhv nömrə]`: a note


def placeholders(text: str) -> list[str]:
    """Unfilled template slots: `[Məhkəmənin adı]`, `[Şirkət Adı]`, `[Rayon]`,
    `[E-poçt ünvanı]`. Not form blanks (`[İmza]`, `[Möhür yeri]`), not tags
    with a colon or a digit (`[Status: OK]`, `[role: FİN]`), not speaker or
    transcript tags (`[Müştəri]`, `[Səs kəsintisi]`)."""
    hits = []
    for m in _SQUARE_BR.finditer(text):
        inner = m.group(1).strip()
        words = [_fold(w) for w in re.split(r"[\s/]+", inner) if w]
        if not words or len(words) > 6 or _FORM_BLANK.search(inner) or re.search(r"[:\d=]", inner) \
                or _ANNOTATION & set(words):
            continue
        start, end = text.rfind("\n", 0, m.start()) + 1, text.find("\n", m.end())
        line = text[start:end if end >= 0 else len(text)]
        if line.count("[") > 2 and re.search(r"[¦|]", line):
            continue                     # a table header row: `[Sıra] ¦ [Ad / Soyad] ¦ [Məkan]`
        if words[-1] in _SLOT_POSSESSIVE:
            hits.append(m.group(0))
        elif words[-1] in _SLOT_BARE and not (len(words) == 1 and line.count("[") > 1):
            # one bare word beside another bracket on its line is a column header or
            # a log tag (`[Tarix]   [Səviyyə]`, `[INFO] [Email]`), not a slot
            hits.append(m.group(0))
    return hits


def self_corrections(text: str) -> list[str]:
    hits = []
    for rx in (_LEAD_NO, _INNER_NO, _RATHER, _FIX):
        hits += [m.group(0) for m in rx.finditer(text)]
    hits += [m.group(0) for m in _RESPELT.finditer(text)
             if m.group(1) != m.group(2) and _near(m.group(1).strip(".,;:!?\"'"), m.group(2))]
    return list(dict.fromkeys(hits))
