"""DocumentSpec -- the brief handed to the model for one document.

The central design decision, following `docs/generator_redesign_plan.md` §2.6:

    **We inject entity values; we do not ask the model to invent them.**

The audit of the previous LLM dataset found 33% of credit cards were Stripe
test numbers, 82 API keys were the verbatim AWS documentation key, and 152
phone numbers were in the 555 fiction range. That is not a prompting failure
that better wording fixes -- an LLM asked for "an example credit card" will
reach for the example it saw ten thousand times in training. It is doing
exactly what it was asked.

So `ValueFactory` mints the values (checksum-valid, blocklist-screened,
deduplicated across runs) and the model is asked to write a realistic document
*around* them. This converts an unreliable "invent something realistic"
instruction into a much more reliable "use these exact strings" one, and it
means every structured entity is correct by construction rather than by luck.

The cost is a slight loss of naturalness in value *placement*. Worth it.

Each spec also carries: a language, a document type, a target length band, a
register/tone, hard negatives to embed unlabeled, and noise directives -- all
sampled so the augmented set matches the procedural set's distributions rather
than drifting into whatever the model finds easiest.
"""

from __future__ import annotations

import functools
import json
import logging
import random
from dataclasses import dataclass, field

from ..config import ENTITY_TYPES, GeneratorConfig
from ..negatives import (FAMILY_RESEMBLES, random_adversarial, random_anchored,
                         random_hard)
from ..values import ValueFactory
from . import edge_cases as EC

log = logging.getLogger("piigen.llm.specs")

# ---------------------------------------------------------------------------
# Document taxonomy
#
# Wider than the procedural generator's DOC_TYPES on purpose. The LLM's
# comparative advantage is naturalistic prose, so the list leans toward
# free-text genres that templates reproduce badly.
# ---------------------------------------------------------------------------

DOC_TYPES: dict[str, str] = {
    "customer_email": "an email from or to a customer, with greeting and sign-off",
    "email_thread": "a forwarded/replied email thread with quoted history (> markers)",
    "support_ticket": "a support ticket with a description and agent notes",
    "live_chat": "a live chat transcript between an agent and a customer",
    "whatsapp_thread": "an informal instant-messaging conversation",
    "crm_note": "a terse internal CRM note written by a sales rep",
    "meeting_notes": "notes taken during a meeting, with action items",
    "medical_note": "a clinical note or referral letter",
    "lab_report": "a laboratory or diagnostic report with a patient header",
    "insurance_claim": "an insurance claim form or adjuster's narrative",
    "bank_correspondence": "a letter or secure message from a bank",
    "invoice": "an invoice or billing statement",
    "receipt": "a purchase receipt",
    "loan_application": "a credit or loan application record",
    "contract_clause": "an excerpt from a contract naming the parties",
    "legal_notice": "a formal legal notice or demand letter",
    "court_filing": "an excerpt from a court filing or case record",
    "government_form": "a completed government form or official request",
    "police_report": "an incident or police report narrative",
    "shipping_manifest": "a shipping manifest or delivery note",
    "customs_declaration": "a customs or import declaration",
    "hr_record": "an HR record, offer letter, or performance note",
    "cv_resume": "a CV or resume section",
    "onboarding_doc": "an employee or customer onboarding document",
    "technical_log": "application or server log output",
    "incident_postmortem": "an incident postmortem write-up",
    "runbook": "an internal runbook or operations guide",
    "api_documentation": "internal API documentation with examples",
    "config_snippet": "a configuration file excerpt with comments",
    "code_review": "code review comments on a pull request",
    "bug_report": "a bug report with reproduction steps",
    "internal_wiki": "an internal wiki or knowledge-base page",
    "social_media": "a social media post or comment thread",
    "forum_post": "a public forum or community post asking for help",
    "complaint_letter": "an angry or frustrated complaint letter",
    "survey_response": "a free-text survey or feedback response",
    "voicemail_transcript": "an automatically transcribed voicemail",
    "call_center_transcript": "a transcribed phone call with disfluencies",
    "rental_agreement": "a rental or lease agreement excerpt",
    "vehicle_record": "a vehicle registration, service, or fleet record",
    "utility_bill": "a utility or telecom bill",
    "school_record": "a school or university administrative record",
    # D-38: genres of published text, written as natural prose (Run B found
    # 26 of 93 given names in real text). Genres only, never real-text content.
    "news_article": "a news article in natural prose: a headline and a few paragraphs reporting "
                    "a local event, naming and quoting the people involved",
    "press_release": "a press release in natural prose from a company or organisation: a headline, "
                     "the announcement, a quote from a named representative and a contact paragraph",
    "official_notice": "an official notice or public announcement from a state body or municipality, "
                       "in natural prose, naming the responsible officials",
    "procurement_announcement": "a public procurement or tender announcement in natural prose: the "
                                "buying organisation, what is bought, the deadline and the contact person",
    "court_announcement": "a court announcement or public summons in natural prose: the court, the case, "
                          "the parties named in it and the hearing",
}
# D-38: the published-text genres above. Natural prose: no table, JSON or
# chat layout, no email or log noise, a formal register.
PROSE_DOC_TYPES = frozenset({"news_article", "press_release", "official_notice",
                             "procurement_announcement", "court_announcement"})

REGISTERS = [
    "formal and businesslike", "warm and conversational", "terse and clipped",
    "frustrated and complaining", "apologetic", "urgent and escalating",
    "bureaucratic and officious", "technical and precise",
    "casual with typos and abbreviations", "polite but firm",
    "friendly with light humour", "anxious and confused",
    "matter-of-fact administrative", "empathetic customer-service",
]
# D-39b (the shapes of the given names Run B missed in real text: 27
# patronymics, 22 list-format given names, 9 after a lowercase title or job
# word, 4 alone on a signature line, 4 sentence-initial, 1 after an
# organisation; the constructions only). A share of the briefs for the
# published-text genres plan one of these constructions, with the names from
# our pools, and say so in the scenario note. Convention: the father's name in
# a patronymic is GIVENNAME, `oğlu`/`qızı` stay outside the span.
# Per genre, the share of briefs that plan one; most in the three genres
# The team named for these lists (official notices, court and procurement
# announcements)
NAME_SHAPE_RATES = {"official_notice": 0.8, "court_announcement": 0.8, "procurement_announcement": 0.8,
                    "news_article": 0.5, "press_release": 0.5, "legal_notice": 0.5,
                    "government_form": 0.5, "court_filing": 0.5}
NAME_SHAPE_DOC_TYPES = frozenset(NAME_SHAPE_RATES)
NAME_SHAPE_ROLES = frozenset({"list_person", "patronymic_father", "named_person"})
_NAME_SHAPES_ROOM = {"patronymic_list": 0.40, "patronymic_sentence": 0.10, "role_word": 0.20,
                     "signature": 0.12, "sentence_initial": 0.12, "after_org": 0.06}
_NAME_SHAPES_TIGHT = {"patronymic_sentence": 0.25, "role_word": 0.35, "signature": 0.15,
                      "sentence_initial": 0.25}           # very short and short documents
_PEOPLE_BY_BAND = {"medium": (2, 3), "long": (3, 5), "very_long": (4, 6), "extreme": (5, 8)}
NAME_ROLE_HINTS = {
    "list_person": "write it exactly as given, with no case ending, in the line the scenario note gives",
    "patronymic_father": "the father's name in a patronymic: write it exactly as given, with no case "
                         "ending, directly before the word oğlu (qızı for a woman)",
    "named_person": "write it exactly as given, with no case ending, as the scenario note says",
}
# D-47f (batch-6 read): no "urgent and escalating" here either;
# emotional registers were 16-18% of the published-text genres
PROSE_REGISTERS = ["formal and businesslike", "bureaucratic and officious", "technical and precise",
                   "matter-of-fact administrative", "polite but firm"]
# D-47c: the legal genres take the formal registers too. They drew all 14
# (4,485 of batch 6's 8,882 emotional or casual documents were of these
# three), so court filings and official forms read like complaints
FORMAL_REGISTER_DOC_TYPES = PROSE_DOC_TYPES | frozenset({"legal_notice", "government_form",
                                                         "court_filing"})

# Noise directives. The procedural generator applies noise programmatically
# after the fact (with exact offset repair); here we additionally ask the model
# to write text that is *natively* messy, which produces kinds of mess a
# character-level transform cannot invent.
NOISE_DIRECTIVES = [
    "include a quoted reply section with '>' markers",
    "include a forwarded-message header block",
    "include an email signature block at the end",
    # P2-5 (batch 4): "in ordinary words". 43 of batch 4's attempts were
    # rejected for a planned name or city written misspelt, and one slipped
    # through as a "self-correction" (`Seyidnovun (Seyidxanovun)`).
    # D-47 (batch-6 read): the model explained its typos
    # (`vəziyyit (typo)`) and corrected itself in brackets in court and official
    # text. Typos are never explained or marked; the self-correction is a
    # directive of its own, for conversational types only (`noise_directives`).
    "include a few realistic typos in ordinary words, never inside a value from "
    "entities_to_embed; never explain or mark them",
    "include a self-correction in ordinary words, as people do when they type fast, "
    "never inside a value from entities_to_embed",
    "use inconsistent spacing and a stray double space",
    # D-47c: never explained (`l0st (0/O qarışığı)`, `# OCR-style artifact`)
    "include an OCR-style artifact (a 0/O or 1/l confusion) in non-sensitive text; "
    "never explain or mark the error",
    "drop some diacritics as if typed on the wrong keyboard layout",
    "include a copy-paste artifact such as smart quotes or an en-dash",
    "include a partially redacted value elsewhere in the text (e.g. ****1234)",
    "mix in one short sentence or log line in English",
    "include a timestamp-prefixed log line or two",
    "include a bulleted list",
    "use a table-like layout with aligned columns",
    "include a line that was clearly pasted from a spreadsheet",
    "leave one sentence unfinished, as people do when interrupted",
]

# 2026-08-25 (audit P1): the top two bounds are measured, not aspirational.
#
# As originally specified, `extreme` asked for 5,500-10,000 characters and the
# model delivered a median of 4,349 -- only 10.2% of extreme-band documents
# ever reached their own floor, and the band under-delivered its share by
# almost half (3.0% target vs 1.6% actual). That is an impossible
# specification, not a quality problem: asking harder does not make the model
# write 6,000 characters.
#
# Measured over 32,535 documents, what the model actually produces when asked
# for each of the two long bands:
#
#     very_long   n=2,710   p10 2,649   p50 3,292   p90 4,067   p99 4,795
#     extreme     n=  512   p10 3,523   p50 4,349   p90 5,583   p99 7,983
#
# Candidate bounds scored by in-band rate (both bands, non-overlapping):
#
#     very_long(2600,5500) extreme(5500,10000)  ->  91.7% / 10.2%   <- was
#     very_long(2600,4500) extreme(4500, 9000)  ->  89.2% / 41.2%
#     very_long(2600,4200) extreme(4200, 9000)  ->  85.2% / 55.9%   <- now
#
# The last row is chosen: it costs very_long 6.5 points to gain extreme 45.7,
# and the band that was broken is the one worth fixing. The ceiling drops to
# 9,000 because only 1% of documents ever exceeded 8,000, and 4 of the 512
# blew past the old 10,000 ceiling entirely (max 18,856) -- a ceiling nothing
# ever enforced.
LENGTH_BANDS = [
    ("very_short", 0.12,   40,   150, "one or two lines"),
    ("short",      0.23,  150,   400, "a short paragraph"),
    ("medium",     0.30,  400,  1100, "several paragraphs or sections"),
    ("long",       0.22, 1100,  2600, "a full-page document"),
    ("very_long",  0.10, 2600,  4200, "a long multi-section document"),
    ("extreme",    0.03, 4200,  9000, "a very long document or log dump"),
]

# Range for DocumentSpec.reference_year -- the anchor year for AMBIENT
# document dates (log timestamps, forwarded-message headers, meeting dates),
# not the wider 1945-2027 range ValueFactory.date() uses for actual DATE
# entities like birthdates. A business document's incidental timestamps are
# plausible anywhere in the last decade or so, not the full birthdate range.
_REFERENCE_YEAR_RANGE = (2015, 2026)

# D-17: every standalone date is DATE, a document's own date (`Tarix: ...`)
# included. The brief used to ask for such dates as unlabelled "ambient"
# context; 41% of batch 2's documents carried one, and 56% of them fell on
# the 12th or 14th. Now a document that would naturally carry its own date is
# given one, planned and labelled like any other value, spread evenly over
# its reference year; the brief allows no other standalone date. Chats, posts,
# logs, code and transcripts are left undated: their dates are timestamps
# (a date with a clock time), which D-17 does not label.
DOCUMENT_DATE_SHARE = 0.6

# P2-6 (RC8, suffixes in LLM prose). Only 8-12% of these labels' mentions in
# the corpus carry a suffix; the brief asks for one in this share of planned
# names, surnames, cities and streets, spread over the cases by the targeted
# builder's own case weights, and gives the renderer's form.
TARGET_CASE_SHARE = 0.4
# P2-6 (structured formats). The benchmark fails in tables, logs and JSON
# (A7); this share of positive briefs of medium length or longer asks for one.
STRUCTURED_SHARE = 0.15
STRUCTURED_LAYOUTS: dict[str, str] = {
    "csv": "with a short CSV excerpt (a header row and two or three data rows) "
           "holding some of the values",
    "json": "with a small JSON object or record holding some of the values",
    "pipe_table": "with a small table drawn with | separators holding some of the values",
    "key_value": "with a block of 'Field: value' lines holding some of the values",
    "dialogue": "as a dialogue, each turn on its own line after the speaker's name or role",
}
_LAYOUT_BANDS = frozenset({"medium", "long", "very_long"})
_LAYOUT_DOC_TYPES_EXCLUDED = frozenset({"live_chat", "whatsapp_thread", "voicemail_transcript",
                                       "call_center_transcript"}) | PROSE_DOC_TYPES
# P2-6: share of edge-case briefs that are a contrast lesson (CONTRAST_CASES)
CONTRAST_SHARE = 0.3


def _case_weights() -> dict[str, float]:
    from ..targeted import quotas as Q              # lazy: stdlib-only module
    return {k: float(v) for k, v in Q.load()["suffix"]["case_weights"].items()}


def target_case(rng: random.Random, label: str, value: str) -> tuple[str, str]:
    """(case, inflected form) for a planned name, surname, city or street,
    or ("", "") when the value takes none of the weighted cases."""
    from ..targeted import suffix as SFX            # lazy; it imports only ..text
    weights = {c: w for c, w in _case_weights().items() if c in SFX.APPLIES.get(label, ())}
    while weights:
        case = rng.choices(sorted(weights), weights=[weights[c] for c in sorted(weights)])[0]
        try:
            return case, SFX.inflect(value, case, label)
        except SFX.NotInflectable:
            weights.pop(case)
    return "", ""
_UNDATED_DOC_TYPES = frozenset({
    "live_chat", "whatsapp_thread", "social_media", "forum_post", "survey_response",
    "voicemail_transcript", "call_center_transcript", "technical_log", "config_snippet",
    "code_review",
})
_AZ_MONTHS = ("yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avqust",
              "sentyabr", "oktyabr", "noyabr", "dekabr")


_DROP_DIACRITICS = next(d for d in NOISE_DIRECTIVES if d.startswith("drop some diacritics"))
# D-38: what a published article, notice or announcement does not contain
_NOT_IN_PROSE = tuple(d for d in NOISE_DIRECTIVES if d.startswith((
    "include a quoted reply", "include a forwarded-message", "include an email signature",
    "mix in one short sentence or log line", "include a timestamp-prefixed",
    "use a table-like layout", "include a line that was clearly pasted",
    "leave one sentence unfinished")))
# D-47c: a self-correction belongs to chat, email and complaints, never to
# official, legal or record text (D-47b drops those)
_SELF_CORRECTION = next(d for d in NOISE_DIRECTIVES if d.startswith("include a self-correction"))


def noise_directives(band: str, doc_type: str | None = None) -> list[str]:
    """The directives a brief of this length band may draw. A very short or
    short document written without Azerbaijani letters keeps too few
    Azerbaijani words for the language gate (P2-5, batch 4: 53% of the very
    short and 22% of the short accepted documents fail once folded; 173 of
    the 197 language rejections were such documents), so those bands do not
    get the diacritics directive. A published-text genre (D-38) gets no
    email, log or table directive. Only a conversational type (chat, email,
    complaint: `meta_noise.CONVERSATIONAL`) gets the self-correction (D-47c)."""
    from ..meta_noise import CONVERSATIONAL         # lazy, as the other helpers
    out = list(NOISE_DIRECTIVES)
    if band in ("very_short", "short"):
        out = [d for d in out if d != _DROP_DIACRITICS]
    if doc_type in PROSE_DOC_TYPES:
        out = [d for d in out if d not in _NOT_IN_PROSE]
    if doc_type not in CONVERSATIONAL:
        out = [d for d in out if d != _SELF_CORRECTION]
    return out


def register_choices(doc_type: str) -> list[str]:
    """The registers a brief of this document type may draw (D-38: formal
    ones for the published-text genres; D-47c: and the three legal genres)."""
    return PROSE_REGISTERS if doc_type in FORMAL_REGISTER_DOC_TYPES else REGISTERS


def steering_labels(entities: list[dict], spec) -> list[str]:
    """The labels a document adds to the label mix: every entity except the
    planned document date's mentions (D-17).

    `SpecSampler` steers label choice toward `entity_weights`, and the run
    monitor stops a run at 2.5x a label's target. The document date is a
    fixed addition outside that mix, about one per dated brief: counted, it
    put DATE at 2.95x its target in a simulated 6,000-brief batch 4 (0.99x
    without it), so batch 4 would have stopped and planned DATEs would have
    been steered away. `spec` is a DocumentSpec or a record's `_spec` dict."""
    planned = getattr(spec, "entities", None)
    if planned is None:
        planned = (spec or {}).get("entities") or []
    own = {_field(e, "value") for e in planned if _field(e, "role") == "document_date"}
    # A contrast lesson (P2-6) plants two look-alike labels on purpose, outside
    # the mix like the document date: counted, IPv6 and MAC reached 3.4x and
    # 2.6x their targets and stopped batch 5 after 1,146 documents (D-23e).
    edge = _field(spec, "edge_case") if spec is not None else None
    edge_id = edge.get("id") if isinstance(edge, dict) else getattr(edge, "id", None)
    lesson = ({(_field(e, "label"), _field(e, "value")) for e in planned}
              if edge_id in _contrast_ids() else set())
    # D-39b: the names a name-construction brief plans are a fixed addition
    # too -- a notice listing five people would otherwise put GIVENNAME and
    # SURNAME past the monitor's 2.5x stop in batch 6's first batches
    lesson |= {(_field(e, "label"), _field(e, "value")) for e in planned
               if _field(e, "role") in NAME_SHAPE_ROLES}
    # A value repeated through one document counts once: the repeats are the
    # writer's choice, not the label mix. Counted, one batch-6 court filing
    # (a log quoting one IPv6 address 51 times) put IPV6_ADDRESS at 3.3x its
    # target and stopped the run after 1,777 documents; counted once, every
    # label sat between 0.89x and 1.19x
    seen: set = set()
    out = []
    for e in entities:
        key = (e["label"], e.get("text"))
        if key in seen or key in lesson or (e["label"] == "DATE" and own and e.get("text") in own):
            continue
        seen.add(key)
        out.append(e["label"])
    return out


def _contrast_ids() -> frozenset:
    from . import edge_cases as EC
    return frozenset(c.case.id for c in EC.CONTRAST_CASES)


def _field(entity, name: str):
    return entity.get(name) if isinstance(entity, dict) else getattr(entity, name, None)


# D-51i (v3 label-noise report, pattern 5): a planned name that is also a
# common word (`Şəkil`, `Döyüş`) was used by the LLM as the word (`rəsmi
# [şəkildə]`) about 1 time in 5, and the resolver labelled it. LLM plans now
# redraw such a value: the homograph list, the names his cleaning
# lexicon excludes or finds written in lower case, and the stopwords. (The
# targeted builder keeps them: its homograph family teaches them on purpose.)
_COMMON_PLAN_LABELS = frozenset({"GIVENNAME", "SURNAME", "CITY"})


@functools.lru_cache(maxsize=None)
def common_word_keys() -> frozenset:
    from ..locales import LOCALES
    from ..resolver import match_key
    from ..v4_clean import LEXICON_PATH
    try:
        from ..targeted import homographs_az as H
    except ImportError:
        from ..targeted import homographs_az_stub as H
    lex = json.loads(LEXICON_PATH.read_text(encoding="utf-8"))
    return frozenset({match_key(w) for w in H.LONE_WORDS} | set(lex["given_excluded"])
                     | set(lex["given_lowercase_uses"]) | set(lex["surname_stoplist"])
                     | {match_key(w) for w in LOCALES["az"].stopwords})


def plan_value(factory, label: str, lang: str, tries: int = 12, **kw) -> str:
    """`factory.make`, redrawn while the value is a common word (D-51i)."""
    from ..resolver import match_key
    value = factory.make(label, lang, **kw)
    if label not in _COMMON_PLAN_LABELS:
        return value
    common = common_word_keys()
    for _ in range(tries):
        if not value or not any(match_key(w) in common for w in value.split()):
            return value
        value = factory.make(label, lang, **kw)
    return value


def name_shape_plan(rng: random.Random, factory, lang: str, band: str, taken: set | None = None):
    """D-39b: (shape, planned name entities, scenario note) for one brief, or
    None when a name cannot be minted. The note gives the exact text of the
    construction, built from the planned values, so the model reproduces
    them verbatim."""
    shapes = _NAME_SHAPES_ROOM if band in _PEOPLE_BY_BAND else _NAME_SHAPES_TIGHT
    names = sorted(shapes)
    shape = rng.choices(names, weights=[shapes[k] for k in names])[0]
    n = (rng.randint(*_PEOPLE_BY_BAND[band]) if shape == "patronymic_list"
         else rng.randint(1, 2) if shape in ("patronymic_sentence", "role_word") else 1)
    patronymic = shape.startswith("patronymic")
    people, planned = [], []
    try:
        for _ in range(n):
            female = rng.random() < 0.4
            # a patronymic is an Azerbaijani construction: the person's names
            # and the father's are Azerbaijani; elsewhere a foreign name may stand
            origin = "" if patronymic else factory.name_origin(lang)
            kw = {"female": female, "origin": origin}
            # Latin spelling throughout: a document does not write one
            # person's names in two scripts
            mint = lambda label, **k: factory.latin_spelling(plan_value(factory, label, lang, **k))   # noqa: E731
            if patronymic:
                # D-40a: a patronymic line in one spelling, the pool's own
                # (The team: English-style parts beside Azerbaijani ones)
                kw["variant"] = False
            p = {"female": female, "g": mint("GIVENNAME", **kw), "s": mint("SURNAME", **kw)}
            role = "list_person" if shape == "patronymic_list" else "named_person"
            planned += [PlannedEntity("SURNAME", p["s"], role=role),
                        PlannedEntity("GIVENNAME", p["g"], role=role)]
            if patronymic:
                # D-40a: men's names only; and no name already planned in the
                # brief (D-42c's draws surfaced a father equal to another given name)
                seen = set(taken or ()) | {x.value for x in planned}
                for _ in range(30):
                    p["f"] = factory.father_name(lang)
                    if p["f"] not in seen:
                        break
                p["p"] = "qızı" if female else "oğlu"
                planned.append(PlannedEntity("GIVENNAME", p["f"], role="patronymic_father"))
            people.append(p)
    except Exception as exc:                                   # noqa: BLE001
        log.warning("name shape %s skipped: %s: %s", shape, type(exc).__name__, exc)
        return None
    p0 = people[0]
    full0 = f"{p0['g']} {p0['s']}"
    if patronymic:
        lines = "\n".join(f"{p['s']} {p['g']} {p['f']} {p['p']}" for p in people)
    if shape == "patronymic_list":
        note = ("Include an official list of people, one per line, each line in exactly this form "
                "(surname, given name, father's name, then oğlu for a man or qızı for a woman) and "
                "with no other words in it (a number or a dash before the line is fine):\n" + lines
                + "\nThe surnames and given names of these lines are the SURNAME and GIVENNAME values above.")
    elif shape == "patronymic_sentence":
        note = ("Name " + ("each of these people" if n > 1 else "this person") + " in a sentence of an "
                "official text, in exactly this form (surname, given name, father's name, oğlu/qızı):\n"
                + lines)
    elif shape == "role_word":
        note = ("Introduce " + " and ".join(f"{p['g']} {p['s']}" for p in people) + " with a lowercase "
                "job or title word right before the name, as a news report or an official notice does "
                "(for example direktor, hakim, vəkil, müdir, mühasib, sədr, prokuror, həkim).")
    elif shape == "signature":
        note = (f"End the document with the name {full0} alone on its own last line, as a signature, "
                "with nothing else on that line (a title may stand on the line above it).")
    elif shape == "sentence_initial":
        note = (f"Begin one sentence of the document with the person's name {full0} "
                f"(or just {p0['g']}), as the subject of the sentence.")
    else:                                                      # after_org
        note = ("Name an organisation in quotation marks (invent one, with no person's name and no "
                f"place name in it) and put the name {full0} directly after the organisation's name, "
                "for example as the person who represents or runs it.")
    return shape, planned, note


def document_date(rng: random.Random, year: int) -> str:
    """A day of `year`, uniform, in a format a document header uses."""
    import datetime
    day = datetime.date(year, 1, 1) + datetime.timedelta(days=rng.randrange(365))
    style = rng.choices(("dmy", "worded", "iso", "slash"), weights=(50, 25, 15, 10))[0]
    if style == "worded":
        return f"{day.day} {_AZ_MONTHS[day.month - 1]} {day.year}"
    if style == "iso":
        return day.isoformat()
    sep = "." if style == "dmy" else "/"
    return f"{day.day:02d}{sep}{day.month:02d}{sep}{day.year}"

# How many PII values to inject, by band. Kept deliberately low relative to
# document length: the procedural set sits at ~11% of characters being PII and
# production is lower still. Asking for many entities in a short document is
# how the previous dataset reached 29.6%.
_ENTITY_BUDGET = {
    "very_short": (1, 2), "short": (1, 3), "medium": (2, 5),
    "long": (3, 7), "very_long": (4, 9), "extreme": (5, 12),
}

# Share of an az document's hard negatives drawn from the anchored decoy
# families (P2-2) rather than the older unanchored ones. The anchored kinds
# are what checkpoint 1 failed on; the unanchored ones stay for coverage.
ANCHORED_DECOY_SHARE = 0.6


@dataclass
class PlannedEntity:
    """One pre-generated, validated value the model must reproduce verbatim."""

    label: str
    value: str
    # "document_date" for the document's own date (D-17); "" otherwise.
    role: str = ""
    # P2-6 (RC8): a case the brief asks this name, surname, city or street to
    # be written in, and the form the renderer gives (`Bakıda`); "" otherwise.
    case: str = ""
    form: str = ""


@dataclass
class DocumentSpec:
    index: int
    lang: str
    doc_type: str
    doc_type_hint: str
    register: str
    band: str
    min_chars: int
    max_chars: int
    length_hint: str
    entities: list[PlannedEntity] = field(default_factory=list)
    hard_negatives: list[str] = field(default_factory=list)
    # Adversarial near-misses are a SUBSET of hard_negatives (they are sent to
    # the model in the same decoy list) but are tracked separately so the
    # analyzer can report adversarial coverage, which previously read 0 always.
    adversarials: list[str] = field(default_factory=list)
    # Anchored decoys (negatives.ANCHORED_DECOYS, P2-2). Each one's `phrase`
    # (`CVV kodu 12345`) is also in hard_negatives, so the brief carries the
    # anchor word right next to the decoy; this keeps kind/resembles/value so
    # the record can declare the exact decoy span (P2-3).
    anchored_decoys: list[dict] = field(default_factory=list)
    # The older, unanchored families' decoys with their kind, so the record
    # can declare kind/resembles for them too (C2 `_decoys`, P2-3).
    plain_decoys: list[dict] = field(default_factory=list)
    noise: list[str] = field(default_factory=list)
    # P2-6: a structured layout the brief asks for (STRUCTURED_LAYOUTS), "" if none
    layout: str = ""
    # D-39b: the name construction this brief plans (NAME_SHAPE_*), and the
    # scenario note that asks for it; "" when none
    name_shape: str = ""
    name_note: str = ""
    negative_only: bool = False
    seed: int = 0
    # Set only when this spec deliberately targets one case from the
    # edge-case catalog instead of broad sampling -- lets the DSPy signature
    # add a scenario note, and lets pipeline._assemble enforce the stricter
    # "decoy must actually appear" / "no judgment-word leak" checks that only
    # matter for a deliberately-constructed collision, not organic sampling.
    edge_case: EC.EdgeCase | None = None
    # Anchor year for AMBIENT dates/timestamps the model writes as flavor text
    # (log lines, forwarded-message headers, meeting dates) -- anything that
    # is not itself a supplied DATE entity. Without this the model has no
    # signal to vary these and defaults to clustering on one recent year
    # (observed: real runs came back almost entirely dated 2024). Same
    # "inject it, don't ask the model to invent it" principle already applied
    # to entity values, applied here to incidental document dates too.
    reference_year: int = 2024

    @property
    def labels(self) -> list[str]:
        return [e.label for e in self.entities]


class SpecSampler:
    """Samples briefs that keep the augmented set on-distribution.

    Language and entity-type selection are *deficit-weighted* against the same
    targets the procedural generator uses, so augmentation fills gaps instead of
    piling more NAME/EMAIL/PHONE onto an already head-heavy distribution --
    which is what the previous LLM run did.
    """

    def __init__(self, cfg: GeneratorConfig, factory: ValueFactory,
                 rng: random.Random) -> None:
        self.cfg = cfg
        self.factory = factory
        self.rng = rng
        self.label_counts: dict[str, int] = {lab: 0 for lab in ENTITY_TYPES}
        self.lang_counts: dict[str, int] = {lg: 0 for lg in cfg.lang_weights}
        self.doc_type_counts: dict[str, int] = {}
        self.total_mentions = 0
        # Minting failures, by label. Previously swallowed silently -- see
        # the `except` in sample(). Surfaced in the run report so a broken
        # value source is visible as a broken value source, not as a
        # mysteriously under-represented label.
        self.mint_failures: dict[str, int] = {}
        self.mint_empty: dict[str, int] = {}
        # D-38: a run may sample only some document types (--doc-types)
        wanted = list(getattr(cfg, "doc_types", None) or [])
        unknown = sorted(set(wanted) - set(DOC_TYPES))
        if unknown:
            raise ValueError(f"unknown document types {unknown}; known: {sorted(DOC_TYPES)}")
        self._doc_names = sorted(set(wanted)) if wanted else sorted(DOC_TYPES)
        self._rate_warned: set[str] = set()

    # -- deficit-weighted choice -----------------------------------------
    def _pick_lang(self) -> str:
        langs = sorted(self.cfg.lang_weights)
        written = sum(self.lang_counts.values())
        if written and self.rng.random() < self.cfg.balance_strength:
            deficits = {
                lg: self.cfg.lang_weights[lg] - self.lang_counts[lg] / written
                for lg in langs
            }
            return max(deficits, key=deficits.get)
        return self.rng.choices(
            langs, weights=[self.cfg.lang_weights[lg] for lg in langs])[0]

    def _label_weights(self) -> dict[str, float]:
        """Positive weight per label, larger where we are behind target."""
        weights = {}
        for lab in ENTITY_TYPES:
            target = self.cfg.entity_weights[lab]
            actual = (self.label_counts[lab] / self.total_mentions
                      if self.total_mentions else 0.0)
            # Squared boost for starved labels so rare types (VEHICLE,
            # DEVICE_ID, IBAN) actually get sampled instead of asymptotically
            # approaching their target from below.
            weights[lab] = max(0.0005, target + max(0.0, target - actual) * 3.0)
        return weights

    def _pick_labels(self, k: int) -> list[str]:
        weights = self._label_weights()
        labels = sorted(weights)
        chosen: list[str] = []
        for _ in range(k):
            pick = self.rng.choices(labels, weights=[weights[x] for x in labels])[0]
            chosen.append(pick)
            # soft penalty so one document does not become six IBANs
            weights[pick] *= 0.35
        return chosen

    def _pick_band(self) -> tuple:
        return self.rng.choices(
            LENGTH_BANDS, weights=[b[1] for b in LENGTH_BANDS])[0]

    # -- edge-case-targeted sampling ---------------------------------------
    def _sample_edge_case(self, index: int) -> DocumentSpec:
        """Deliberately realize one POSITIVE case from the edge-case catalog.

        A single entity in a short-to-medium document -- this is a
        collision/format test, not an organic multi-entity document, so the
        usual entity budget does not apply.

        Restricted to positive-family cases only (positive_valid/
        positive_format_variant/ambiguous_requires_anchor) as of 2026-08-21:
        training data is true-positive only by explicit instruction, so the
        hard_negative/invalid_near_miss half of the catalog is never sampled
        here. Their case definitions and near_miss_value() stay in
        edge_cases.py, unused for now -- a config change away, not a rewrite,
        if that's revisited.
        """
        rng = self.rng
        lang = self._pick_lang()
        band, _w, lo, hi, length_hint = self._pick_band()
        doc_type = rng.choice(self._doc_names)

        entities: list[PlannedEntity] = []
        if rng.random() < CONTRAST_SHARE:
            contrast = rng.choice(EC.CONTRAST_CASES)
            case = contrast.case
            values = getattr(self.factory, contrast.maker)()
            entities += [PlannedEntity(lab, v) for lab, v in zip(contrast.labels, values) if v]
        else:
            label = rng.choice(ENTITY_TYPES)
            positive_cases = [c for c in EC.LABEL_CASES[label] if not EC.is_negative(c)]
            case = rng.choice(positive_cases)
            try:
                value = EC.positive_value(case, label, self.factory, lang)
            except Exception:                              # noqa: BLE001
                value = None
            if value:
                entities.append(PlannedEntity(label, value))

        noise = rng.sample(noise_directives(band, doc_type), rng.randint(0, 2))

        return DocumentSpec(
            index=index, lang=lang, doc_type=doc_type,
            doc_type_hint=DOC_TYPES[doc_type], register=rng.choice(register_choices(doc_type)),
            band=band, min_chars=lo, max_chars=hi, length_hint=length_hint,
            entities=entities, noise=noise, negative_only=False,
            seed=rng.randrange(2 ** 31), edge_case=case,
            reference_year=rng.randint(*_REFERENCE_YEAR_RANGE),
        )

    # -- rates -------------------------------------------------------------
    def branch_rates(self) -> tuple[float, float, float]:
        """(P(negative-only), P(hard negatives), P(adversarial)) to draw with
        once a document is NOT an edge case, such that every configured rate
        holds as a share of ALL documents (P2-6 fix 4).

        An edge-case brief is drawn first and carries none of the three, so
        drawing the configured rates directly among the rest under-delivered
        each by the edge-case share: batch 1 (edge 0.3) asked for 10% PII-free
        and 30% hard-negative documents and got 7.1% and 26.3% of 12,000
        offline briefs. A negative-only document always carries both kinds of
        decoy, so it counts towards the hard-negative and adversarial shares
        too; the positive documents make up the rest.
        """
        cfg = self.cfg
        rest = 1.0 - min(max(cfg.edge_case_rate, 0.0), 1.0)
        if rest <= 0.0:
            return 0.0, 0.0, 0.0
        neg = min(max(cfg.negative_only_rate, 0.0), rest)
        positives = rest - neg

        def among_positives(rate: float, name: str) -> float:
            if positives <= 0.0:
                return 0.0
            want = (rate - neg) / positives
            if not 0.0 <= want <= 1.0 and rate > 0.0 and name not in self._rate_warned:
                self._rate_warned.add(name)
                log.warning("%s %.2f cannot hold as a share of all documents with "
                            "negative_only_rate %.2f and edge_case_rate %.2f; using %.2f",
                            name, rate, cfg.negative_only_rate, cfg.edge_case_rate,
                            neg + positives * min(max(want, 0.0), 1.0))
            return min(max(want, 0.0), 1.0)

        return (neg / rest, among_positives(cfg.hard_negative_rate, "hard_negative_rate"),
                among_positives(cfg.adversarial_rate, "adversarial_rate"))

    # -- public -----------------------------------------------------------
    def sample(self, index: int) -> DocumentSpec:
        if self.rng.random() < self.cfg.edge_case_rate:
            return self._sample_edge_case(index)

        rng = self.rng
        lang = self._pick_lang()
        band, _w, lo, hi, length_hint = self._pick_band()
        doc_type = rng.choice(self._doc_names)
        p_negative_only, p_hard, p_adversarial = self.branch_rates()

        negative_only = rng.random() < p_negative_only

        entities: list[PlannedEntity] = []
        if not negative_only:
            lo_n, hi_n = _ENTITY_BUDGET[band]
            # GIVENNAME and SURNAME are drawn independently by ValueFactory
            # (each coin-flips its own gender when not told one), so a
            # document planning both can otherwise pair a male given name
            # with a feminine-suffixed surname or vice versa -- fixed by
            # settling one gender per document and passing it to both.
            # Documents about more than one person are not modeled at this
            # level (specs.py has no concept of "person"), so this is a
            # deliberate simplification: it fixes the observed single-person
            # mismatch at the cost of not varying gender within a doc that
            # happens to plan multiple GIVENNAME/SURNAME entities.
            female = rng.random() < 0.5
            # P2-15: the same holds for a foreign name's origin; `Sergey`
            # comes with `Petrov`, not with `Məmmədova`
            origin = self.factory.name_origin(lang)
            for label in self._pick_labels(rng.randint(lo_n, hi_n)):
                kw = ({"female": female, "origin": origin}
                      if label in ("GIVENNAME", "SURNAME") else {})
                try:
                    value = plan_value(self.factory, label, lang, **kw)   # D-51i
                except Exception as exc:               # noqa: BLE001
                    # Was a bare `continue`, which dropped the entity from
                    # the spec leaving no trace anywhere -- so a
                    # systematically failing minter (a bad locale file, a
                    # missing data file) would quietly shrink every
                    # document's entity list and surface only as unexplained
                    # label under-representation in the final distribution.
                    self.mint_failures[label] =                         self.mint_failures.get(label, 0) + 1
                    log.warning("value minting failed for %s/%s: %s: %s",
                                label, lang, type(exc).__name__, exc)
                    continue
                if value:
                    entities.append(PlannedEntity(label, value))
                else:
                    # "" is what ValuePool.fresh() returns when it cannot
                    # find any unblocked value at all. Distinct from an
                    # exception, and equally invisible before now.
                    self.mint_empty[label] = self.mint_empty.get(label, 0) + 1

        # Hard negatives: strings that look like PII but are not. Target
        # coverage matches the procedural generator's ~40% of documents.
        hard: list[str] = []
        adversarial: list[str] = []
        anchored: list[dict] = []
        plain: list[dict] = []
        if rng.random() < p_hard or negative_only:
            for _ in range(rng.randint(1, 3 if not negative_only else 5)):
                # Anchor phrases are Azerbaijani, so anchored decoys go into
                # az briefs only (sprint-1 new data is az-only, D-4).
                if lang == "az" and rng.random() < ANCHORED_DECOY_SHARE:
                    decoy = random_anchored(rng)
                    hard.append(decoy.phrase)
                    anchored.append(decoy.as_dict())
                    continue
                kind, value = random_hard(lang, rng)
                hard.append(value)
                plain.append({"kind": kind, "value": value,
                              "resembles": FAMILY_RESEMBLES.get(kind)})
        if rng.random() < p_adversarial or negative_only:
            for _ in range(rng.randint(1, 2)):
                kind, value = random_adversarial(lang, rng)
                adversarial.append(value)
                hard.append(value)
                plain.append({"kind": kind, "value": value,
                              "resembles": FAMILY_RESEMBLES.get(kind)})

        noise = rng.sample(noise_directives(band, doc_type), rng.randint(1, 3))

        # P2-6 (RC8): a target case for some names, surnames, cities, streets
        if lang == "az":
            for i, e in enumerate(entities):
                if e.label in ("GIVENNAME", "SURNAME", "CITY", "STREET") \
                        and rng.random() < TARGET_CASE_SHARE:
                    case, form = target_case(rng, e.label, e.value)
                    if case:
                        entities[i] = PlannedEntity(e.label, e.value, e.role, case, form)
        layout = ""
        if (entities and band in _LAYOUT_BANDS and doc_type not in _LAYOUT_DOC_TYPES_EXCLUDED
                and rng.random() < STRUCTURED_SHARE):
            layout = rng.choice(sorted(STRUCTURED_LAYOUTS))

        # D-39b: a name construction for some published-text briefs, after the
        # target-case loop above so these names stay bare
        name_shape = name_note = ""
        if (lang == "az" and not negative_only and doc_type in NAME_SHAPE_DOC_TYPES
                and rng.random() < NAME_SHAPE_RATES[doc_type]):
            plan = name_shape_plan(rng, self.factory, lang, band, taken={e.value for e in entities})
            if plan:
                name_shape, planned_names, name_note = plan
                entities += planned_names

        reference_year = rng.randint(*_REFERENCE_YEAR_RANGE)
        if (entities and doc_type not in _UNDATED_DOC_TYPES
                and rng.random() < DOCUMENT_DATE_SHARE):
            entities.append(PlannedEntity("DATE", document_date(rng, reference_year),
                                          role="document_date"))

        spec = DocumentSpec(
            index=index, lang=lang, doc_type=doc_type,
            doc_type_hint=DOC_TYPES[doc_type], register=rng.choice(register_choices(doc_type)),
            band=band, min_chars=lo, max_chars=hi, length_hint=length_hint,
            entities=entities, hard_negatives=hard, adversarials=adversarial,
            anchored_decoys=anchored, plain_decoys=plain, noise=noise,
            layout=layout, name_shape=name_shape, name_note=name_note,
            negative_only=negative_only,
            seed=rng.randrange(2 ** 31),
            reference_year=reference_year,
        )
        return spec

    def record(self, labels_emitted: list[str], lang: str, doc_type: str) -> None:
        """Feed accepted output back so steering reflects reality, not intent."""
        for lab in labels_emitted:
            if lab in self.label_counts:
                self.label_counts[lab] += 1
                self.total_mentions += 1
        if lang in self.lang_counts:
            self.lang_counts[lang] += 1
        self.doc_type_counts[doc_type] = self.doc_type_counts.get(doc_type, 0) + 1
