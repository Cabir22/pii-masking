"""DSPy is the sole generation backend now: one Signature, one LM.

This replaces three former modules at once, each for a specific reason:

  * `company.py` (raw HTTP client) -- `dspy.LM` already talks to any
    OpenAI-compatible endpoint via litellm, with its own retry/backoff. A
    second, hand-rolled HTTP+retry layer on top of that was redundant, not
    defense in depth.
  * `parse.py` (JSON envelope extraction/repair) -- that existed to parse
    `{"text": ..., "entities": [...]}` out of a raw chat completion, tolerating
    markdown fences, trailing commas, prose wrapping. DSPy's adapter parses
    its own `[[ ## field ## ]]` structure natively, so envelope-format
    failures (F1 in docs/audit_llm_augmentation.md) are structurally
    impossible now, not repaired after the fact.
  * `prompts.py`'s message-building (its *content* -- the actual rules about
    verbatim values, no invented PII, no placeholders -- is preserved below,
    just moved into Signature field descriptions instead of a hand-formatted
    string).

The `entities` field the model used to be asked to report back is gone too:
`_assemble` in pipeline.py never read it (a real, previously-unfixed dead
parameter -- F3 in the audit). We already know the planned entities from
`DocumentSpec`; `resolve_claims` finds them in the returned text regardless
of what the model claims. Removing the ask removes the failure mode.
"""

from __future__ import annotations

import os
import re
import time

from ..anchors import SELF_SIGNALLING
from ..config import DETECTION_TIERS, LANG_NAMES
from .specs import NAME_ROLE_HINTS, STRUCTURED_LAYOUTS, DocumentSpec

ENV_KEY = "COMPANY_API_KEY"
LEGACY_ENV_KEY = "HALX_API_KEY"
ENV_BASE_URL = "COMPANY_API_BASE_URL"
ENV_MODEL = "COMPANY_MODEL"
DEFAULT_BASE_URL = "https://api.hal-x.ai/v1"


class ConfigError(RuntimeError):
    """Missing credentials or an unusable model configuration."""


class ContentError(RuntimeError):
    """The call succeeded but returned no usable text."""


def build_lm(model: str, base_url: str | None = None, *,
             api_key: str | None = None, temperature: float = 0.9,
             max_tokens: int = 16384, no_think: bool = False,
             num_retries: int = 5, timeout: float | None = None):
    """One dspy.LM, routed at the internal endpoint via litellm's generic
    openai/<model> provider. `num_retries` leans on litellm's own retry/
    backoff rather than reimplementing one -- see the module docstring."""
    import dspy

    key = api_key or os.environ.get(ENV_KEY) or os.environ.get(LEGACY_ENV_KEY)
    if not key:
        raise ConfigError(
            f"No API key. Export {ENV_KEY} before running:\n"
            f"    export {ENV_KEY}='...'          # bash/zsh\n"
            f"    $env:{ENV_KEY}='...'            # PowerShell\n"
            f"({LEGACY_ENV_KEY} is also accepted.)")

    url = (base_url or os.environ.get(ENV_BASE_URL) or DEFAULT_BASE_URL).rstrip("/")

    extra: dict = {}
    if no_think:
        # vLLM/SGLang-style "thinking" models (wahoo-1.5-preview is one) burn
        # the whole max_tokens budget in a reasoning channel and return
        # content: None otherwise -- docs/audit_llm_augmentation.md F10/F11.
        extra["extra_body"] = {"chat_template_kwargs": {"enable_thinking": False}}
    if timeout is not None:
        extra["timeout"] = timeout

    return dspy.LM(
        f"openai/{model}", api_key=key, api_base=url,
        temperature=temperature, max_tokens=max_tokens,
        num_retries=num_retries, **extra,
    )


def list_models(base_url: str | None = None, api_key: str | None = None) -> list[str]:
    """GET {base}/models. Deliberately NOT routed through dspy.LM -- this is a
    one-off discovery call, not a generation call, and plain `requests` is
    simpler than standing up an LM object with no model id yet."""
    import requests

    key = api_key or os.environ.get(ENV_KEY) or os.environ.get(LEGACY_ENV_KEY)
    if not key:
        raise ConfigError(f"No API key. Export {ENV_KEY} first.")
    url = (base_url or os.environ.get(ENV_BASE_URL) or DEFAULT_BASE_URL).rstrip("/")
    resp = requests.get(f"{url}/models", headers={"Authorization": f"Bearer {key}"},
                        timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    items = payload.get("data") if isinstance(payload, dict) else payload
    out: list[str] = []
    if isinstance(items, list):
        for item in items:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict):
                for key_name in ("id", "name", "model", "model_id"):
                    if isinstance(item.get(key_name), str):
                        out.append(item[key_name])
                        break
    return sorted(dict.fromkeys(out))


def _no_turkish() -> str:
    """P2-6 fix 6: 53 of batch 1's rejections were Turkish words in an
    Azerbaijani document (`lütfen` 43, `teşekkür` 10). Built from the
    validator's own table, so the brief and the check cannot drift apart."""
    from ..validate import TURKISH_ONLY_FORMS
    pairs = ", ".join(f"{az} (not {tr})" for tr, az in TURKISH_ONLY_FORMS.items())
    return f"Write the Azerbaijani words, never their Turkish forms: {pairs}."


def _language_clause(lang: str) -> str:
    name = LANG_NAMES.get(lang, lang)
    extra = {
        "az": (" Use Azerbaijani Latin script including ə, ğ, ı, ö, ş, ü. "
               "Use natural agglutinative morphology, not word-by-word English. "
               + _no_turkish()),
        "tr": (" Use Turkish orthography including ı, İ, ğ, ş, ö, ü, ç."),
        "ru": (" Use Cyrillic. Use the appropriate case endings; in formal "
               "registers a patronymic is common."),
        "en": " Mix US, UK and Irish conventions across documents.",
    }.get(lang, "")
    return f"{name} ({lang}).{extra}"


# Azerbaijani context phrases the model should place beside each
# anchor_required value. Kept in the model's own language: the document is
# Azerbaijani, so an English hint ("next to the word 'age'") invites an
# English word into the text, which the language gate then rejects.
_ANCHOR_HINTS = {
    "AGE": "\"yaşı\", \"yaşında\", \"yaşlı\"",
    "BUILDINGNUM": "\"bina\", \"mənzil\", \"ünvan\", or a street name",
    "CARD_SECURITY_CODE": "\"CVV\", \"CVC\", \"təhlükəsizlik kodu\"",
    # P2-6 batch 2: these two said "(or write it as dd.mm.yyyy)" and "(or
    # write it as HH:MM)". The model read that as leave to re-spell the value
    # it was given: 36 times in 31 batch-2 documents a planned date appears
    # in another format (1991-09-14 written 14.09.1991), in 29 of them as its
    # only form, and none was labelled. A value in a self-signalling shape
    # needs no context word at all (anchors.SELF_SIGNALLING), so it is now
    # asked only to keep its format (`_KEEP_FORMAT`), and the rest keep their
    # anchor words.
    "DATE": "\"tarix\", \"tarixli\", \"doğum tarixi\"",
    "TIME": "\"saat\", \"vaxt\"",
}
_KEEP_FORMAT = ("write it in exactly this format every time it appears; never "
                "re-spell it in another date or time format")
# D-17: the document's own date is planned and labelled (specs.document_date).
# Where the document's own date goes. P2-5 (batch 4): with one example
# ("Tarix: <date>"), 1,654 of the 1,679 document dates came right after
# "Tarix:", usually as the first line. The brief now names one of four
# placements, by the brief's seed.
_DOCUMENT_DATE_PLACEMENTS = (
    'in a header line such as "Tarix: <date>"',
    'in a line such as "Sənəd tarixi: <date>" or "Tərtib tarixi: <date>"',
    'in the first sentence, e.g. "Bu sənəd <date> tarixində tərtib edilib"',
    "on a line of its own at the end of the document",
)


def _document_date_hint(seed: int) -> str:
    where = _DOCUMENT_DATE_PLACEMENTS[seed % len(_DOCUMENT_DATE_PLACEMENTS)]
    return f"the document's own date: put it {where}; " + _KEEP_FORMAT


# What a label's code means, where the model misreads it. P2-6 (batch 2):
# only 99 of the clean batch's 416 AZ_FIN values (24%) stood near any FIN or
# ID-card word, against 82-85% for VÖEN, passport, ID card and licence. The
# model read "FIN" as financial: "Maliyyə kodu: 4DW9Z35", "tranzaksiya kodu",
# an account number. Labelled there, it teaches the model that any 7-character
# code is a FIN, and too few real FIN contexts.
_MEANING_HINTS = {
    "AZ_FIN": ("a person's FİN: the 7-character personal identification code on "
               "an Azerbaijani ID card, not a financial, account or transaction "
               "code -- write it as one, e.g. after \"FİN\", \"FİN kodu\" or "
               "\"şəxsiyyət vəsiqəsinin FİN kodu\""),
}

# 2026-08-26: measured directly against the repaired corpus -- of 55,935
# GIVENNAME/SURNAME/CITY/STREET mentions, the genuine rate of a real
# Azerbaijani case suffix fused onto one of these values ("Bakıda",
# "Məmmədovun") was 0% (the 2 candidates that superficially looked like it
# turned out to be noise-injection typo artifacts on inspection, not real
# grammar). Cross-checked against the reject log too: leaked-unlabeled-PII
# rejections, the failure mode an inflected-but-then-unrecognized value
# would produce, are 95% EMAIL -- essentially none implicate these four
# labels. So this was not the model trying and getting rejected; it is the
# model barely attempting natural inflection at all, despite
# `_language_clause`'s existing general "natural agglutinative morphology"
# instruction -- rule 1's "must appear EXACTLY as given ... do not
# reformat" is the more specific, more forceful instruction where the
# entities_to_embed values themselves are concerned, and it wins.
#
# `piigen/resolver.py` was fixed the same day to actually recognize a fused
# suffix on these four labels when the model does write one (it already
# could recognize the DIFFERENT hyphen-joined case, "10:17-də", but not
# this far more common no-hyphen one) -- this hint is what gives that fix
# something to accept. Doing only one half of this pair is close to
# useless: the resolver fix alone has nothing to recognize if the model
# still never inflects, and prompting for inflection alone would just
# convert the gap into leaked-unlabeled-PII rejections instead of closing
# it, since nothing would recognize the result.
_INFLECTION_HINT = (
    "a real Azerbaijani case ending may be fused directly onto this word "
    "with no space when your sentence's grammar calls for it, e.g. "
    "\"Bakı\" -> \"Bakıda\"/\"Bakının\"/\"Bakıdan\"/\"Bakıya\" -- do not "
    "force it into the bare form where a native speaker would inflect it"
)
# Same set piigen/resolver.py derives from the same source, for the same
# reason: these two must never silently drift apart, or this hint would be
# telling the model to write forms the resolver can't yet recognize (or
# vice versa).
_INFLECTABLE_LABELS = {label for label, tier in DETECTION_TIERS.items()
                       if tier == "ml_context"}


def build_fields(spec: DocumentSpec) -> dict[str, str]:
    """DocumentSpec -> the Signature's InputField values."""
    # anchor_required labels carry no standalone signal: a bare "417" is only
    # a CARD_SECURITY_CODE because something nearby says so, and the validator
    # now enforces that (piigen/anchors.py). Measured on 8,001 real documents,
    # 20.2% of CARD_SECURITY_CODE mentions and 5.9% of AGE mentions had no
    # licensing word within +/-80 characters -- so without this hint the
    # anchor gate would reject documents the model had no way to know it
    # needed to write differently. Naming the expected context word per label
    # is cheaper than rejecting and resampling.
    entity_lines = []
    for e in spec.entities:
        hint = _ANCHOR_HINTS.get(e.label)
        shape = SELF_SIGNALLING.get(e.label)
        if getattr(e, "role", "") == "document_date":
            entity_lines.append(f"{e.label}: {e.value}   ({_document_date_hint(spec.seed)})")
        elif e.label == "ZIPCODE" and e.value.isdigit():
            # D-42c: a bare 4-digit postal code needs its context
            entity_lines.append(f"{e.label}: {e.value}   (a postal code written without \"AZ\": put it "
                                f"right after a postal-code word such as \"poçt indeksi\" or \"indeks\", "
                                f"or after the place name; write it exactly as given)")
        elif getattr(e, "role", "") in NAME_ROLE_HINTS:
            # D-39b: a name the scenario note places (a list line, a patronymic)
            entity_lines.append(f"{e.label}: {e.value}   ({NAME_ROLE_HINTS[e.role]})")
        elif shape is not None and shape.match(e.value):
            # P2-6 (batch 3): with only "keep this format", the model labelled
            # the value with the code itself -- `TIME: 14:10` -- and the
            # taxonomy check rejected it: 61 of batch 3's attempts, 6 of batch
            # 2's when the line still named "saat"/"vaxt". The context word is
            # back, as a suggestion: the value needs no anchor.
            say = f"; introduce it with an Azerbaijani word such as {hint}" if hint else ""
            entity_lines.append(f"{e.label}: {e.value}   ({_KEEP_FORMAT}{say})")
        elif hint:
            keep = f"; {_KEEP_FORMAT}" if shape is not None else ""
            entity_lines.append(f"{e.label}: {e.value}   (must appear next to "
                                f"a phrase such as {hint}{keep})")
        elif e.label in _INFLECTABLE_LABELS and getattr(e, "form", ""):
            # P2-6 (RC8): a case asked for, with the renderer's form
            entity_lines.append(f"{e.label}: {e.value}   (write it once in this form, with "
                                f"its case ending, in a sentence whose grammar needs it: "
                                f"\"{e.form}\"; elsewhere as the sentence requires)")
        elif e.label in _INFLECTABLE_LABELS:
            entity_lines.append(f"{e.label}: {e.value}   ({_INFLECTION_HINT})")
        elif e.label in _MEANING_HINTS:
            entity_lines.append(f"{e.label}: {e.value}   ({_MEANING_HINTS[e.label]})")
        else:
            entity_lines.append(f"{e.label}: {e.value}")
    if entity_lines:
        entities_to_embed = "\n".join(entity_lines)
    elif spec.negative_only:
        # P2-6 fix 3: these documents are mostly codes, log lines and numbers,
        # and 33 of batch 1's were too short on real words to pass the
        # language gate. Asked for plainly instead of rejected afterwards.
        entities_to_embed = ("none -- this document must contain NO personal data at all. "
                             "Write it in real sentences of the requested language: even a "
                             "log, receipt or config excerpt has at least two full sentences "
                             "around its codes and numbers")
    else:
        entities_to_embed = "none"

    scenario_note = "none"
    if getattr(spec, "name_note", ""):
        scenario_note = spec.name_note            # D-39b; an edge-case brief has none
    if spec.edge_case is not None:
        scenario_note = (f"[{spec.edge_case.status}] {spec.edge_case.prompt_text} "
                          "Do not comment on whether this value/decoy's format "
                          "or validity looks correct -- use it as ordinary "
                          "content with no remark about correctness.")

    length_hint = f"roughly {spec.min_chars}-{spec.max_chars} characters ({spec.length_hint})"
    if spec.band in ("very_short", "short") and spec.entities:
        # P2-6 (batch 2): 201 of batch 2's 229 language rejections were short
        # documents WITH PII written as bare 'field: value' lines, too few
        # Azerbaijani words for the gate. PII-free ones already get this
        # request (fix 3).
        length_hint += ("; even this short, write the values inside at least one full "
                        "sentence of ordinary Azerbaijani words, not as bare "
                        "'field: value' lines")

    return {
        "language": _language_clause(spec.lang),
        "doc_type": f"{spec.doc_type.replace('_', ' ')} -- {spec.doc_type_hint}"
                    + (f", {STRUCTURED_LAYOUTS[spec.layout]}, with ordinary Azerbaijani "
                       f"sentences around it" if getattr(spec, "layout", "") else ""),
        "tone_register": spec.register,
        "length_hint": length_hint,
        "entities_to_embed": entities_to_embed,
        "decoys": "\n".join(spec.hard_negatives) if spec.hard_negatives else "none",
        "noise_directives": "\n".join(spec.noise) if spec.noise else "none",
        "scenario_note": scenario_note,
        "document_year": str(spec.reference_year),
    }


def build_signature():
    import dspy

    class GenerateTrainingDocument(dspy.Signature):
        """You generate realistic training documents for a PII-detection model.

        1. Every value in entities_to_embed must appear in the output EXACTLY
        as given -- same characters, spacing, punctuation, grouping. Do not
        reformat, translate, abbreviate, correct, mask or truncate. Do not
        change a phone number's spacing or an IBAN's grouping, do not add or
        remove a leading '+'. The one exception: a GIVENNAME, SURNAME, CITY
        or STREET value may take a natural Azerbaijani grammatical case
        ending fused directly onto it with no space, when the sentence
        actually calls for it (see the per-value note next to that entity
        below) -- that is real Azerbaijani grammar, not a reformat, and a
        native writer would never leave it in the bare form just because
        that is how it was given to you.

        2. entities_to_embed is formatted 'LABEL: value' for YOUR reference
        only -- the LABEL half (e.g. GIVENNAME, AZ_PASSPORT_NUMBER,
        BUILDINGNUM, TELEPHONENUM) is an internal taxonomy code, not a real
        field name. NEVER write that label token into the document itself,
        whether as a heading, a form field name, a JSON/log key, or next to
        the value ("Ad: GIVENNAME: Fatimə" and "AZ_PASSPORT_NUMBER: O69367632"
        are both wrong). That includes a key in a log line, config or JSON:
        no `DATE:`, `TIME=` or `AZ_FIN` in capitals. Always express the field
        with a natural label in the target language and register instead
        ("Ad:", "Pasport №:", "Doğum tarixi:"), the way a real document
        actually would.

        3. Do NOT invent any additional PII beyond entities_to_embed. No extra
        names (not even in a From:/Göndərən: line, a greeting or a
        signature), initials, emails -- including a company's support, info,
        admin or destek mailbox, and any address on the domain of the service
        you are running on --, phone numbers, city, district or village
        names, street names, building or flat numbers, card numbers, IDs, IP
        addresses, keys or passwords. If the document needs another person,
        a contact point or a place, refer to it by role or description ("the
        supervisor", "our support team", "the regional office"), never by
        inventing one.

        4. NEVER use placeholder or well-known example values. Specifically
        forbidden: John/Jane Doe, example.com, test@test.com, 555-01xx
        numbers, 4242424242424242 or any Stripe/Visa test card,
        AKIAIOSFODNN7EXAMPLE, password123, P@ssw0rd, hunter2, 192.168.1.1,
        8.8.8.8, 127.0.0.1, lorem ipsum, Springfield, 742 Evergreen Terrace,
        or any address/name from film or television.

        5. decoys, if given, must appear in the text VERBATIM as ordinary
        content, but must NOT be labeled or treated as PII -- and never
        comment on whether a decoy (or any entity value) looks correct,
        valid, or well-formatted. Just use it plainly, the way a real
        document would. When decoys is not 'none', do not use any of these
        words anywhere in the document, even about something unrelated:
        yanlış, səhv, düzgün deyil, etibarsız, keçərsiz, invalid, wrong,
        incorrect. Say "problem", "xəta" or "nasazlıq" instead.

        6. Write genuinely in the requested language: native sentence
        structure, honorifics and punctuation a native writer would actually
        use, not a translated English template.

        7. Vary structure between documents. Do not fall into a house style;
        match the requested document type and register. In particular, vary
        how a document opens -- not every document needs to start with a
        horizontal divider line or section rule. A spoken/conversational
        format (voicemail, live chat, call transcript) should almost never
        open that way; it is a written-document convention.

        8. Follow noise_directives (if not 'none') and scenario_note (if not
        'none') exactly -- always write a real sentence around any value or
        decoy, never output it bare with no surrounding words, even for a
        terse register like a log line or code comment.

        9. Output plain text only. No markdown fences, no JSON, no
        commentary before or after the document.

        10. Dates. The only full dates (a day, a month and a year) the
        document may contain are the DATE values in entities_to_embed; the
        document's own date, if it has one, is given there. Do not add any
        other date -- not in a header, a signature, a reference number's
        description or the running text. A timestamp, a date immediately
        followed by a clock time ("2021-08-22 19:45", "[12.05.2021 10:15]"
        in a log line or message header), is allowed, and so is a year or a
        month and year alone ("2018-ci il", "may 2016"); anchor those to
        document_year (not the current year, not always the same year)."""

        language: str = dspy.InputField()
        doc_type: str = dspy.InputField()
        tone_register: str = dspy.InputField(desc="the tone/register to write in")
        length_hint: str = dspy.InputField()
        entities_to_embed: str = dspy.InputField(
            desc="one per line, 'LABEL: verbatim value' -- LABEL is an "
                 "internal code for your reference, never write it into "
                 "the document itself (see rule 2)")
        decoys: str = dspy.InputField(
            desc="strings to include as ordinary content but never label")
        noise_directives: str = dspy.InputField()
        document_year: str = dspy.InputField(
            desc="anchor year for timestamps and for a year or month mentioned "
                 "alone; never a reason to add a full date (rule 10)")
        scenario_note: str = dspy.InputField()
        text: str = dspy.OutputField(desc="the generated document, plain text")

    return GenerateTrainingDocument


# ChatAdapter closes a reply with `[[ ## completed ## ]]`. The model sometimes
# writes it a little wrong -- `[[ ## completed ]]` -- and the adapter, not
# recognising it, leaves it at the end of the `text` field. That was 477 of
# batch 1's 11,015 calls (4.3%), every one at the very end of an otherwise
# finished document, all rejected by quality_filter's adapter-artifact check
# (P2-6 fix 6). It is protocol framing, not document content, so a marker at
# the END is removed here, when the reply is parsed; one anywhere else still
# rejects the document.
_TRAILING_COMPLETION = re.compile(r"\[\[\s*##\s*completed\s*(?:##\s*)?\]\]\s*$")


def strip_completion_marker(text: str) -> str:
    """`text` without a trailing ChatAdapter completion marker."""
    return _TRAILING_COMPLETION.sub("", text).rstrip()


class DSPyGenerator:
    """Everything pipeline.py needs from a generation backend."""

    def __init__(self, lm, module=None) -> None:
        self.lm = lm
        self.model = getattr(lm, "model", "")
        self.module = module or self._default_module()
        self.call_count = 0
        self.latencies: list[float] = []

    def _default_module(self):
        import dspy
        return dspy.Predict(build_signature())

    def generate(self, spec: DocumentSpec) -> str:
        import dspy

        started = time.monotonic()
        # Force ChatAdapter, not DSPy's default (JSONAdapter): our Signature
        # has a single plain-text output field, so there is nothing to gain
        # from JSON-constrained decoding, and requesting it via
        # `response_format` 500s outright on this endpoint (it does not
        # implement structured outputs) instead of cleanly declining.
        # ChatAdapter's `[[ ## text ## ]]` framing needs no response_format
        # at all and works against any chat-completion endpoint.
        with dspy.context(lm=self.lm, adapter=dspy.ChatAdapter()):
            pred = self.module(**build_fields(spec))
        self.call_count += 1
        self.latencies.append(time.monotonic() - started)
        text = strip_completion_marker((pred.text or "").strip())
        if not text:
            raise ContentError("model returned empty text")

        # dspy.Predict doesn't surface finish_reason on its return value, but
        # the raw completion response (which has it) is preserved in the LM's
        # own history. A truncated response is not a complete document -- a
        # real one was caught by hand here (thinking mode, --max-tokens too
        # low: cut off mid-timestamp, "...[2025-11-04") and it passed every
        # other check, because whatever entity value was needed had already
        # been written before the cutoff. Reject explicitly instead of
        # relying on that coincidence.
        if self.lm.history:
            response = self.lm.history[-1].get("response")
            choices = getattr(response, "choices", None)
            if choices and any(getattr(c, "finish_reason", None) == "length"
                               for c in choices):
                raise ContentError(
                    "response was truncated before the document finished "
                    "(finish_reason=length) -- raise --max-tokens")
        return text

    def load_compiled(self, path: str) -> None:
        self.module.load(path)

    def stats(self) -> dict:
        """Call statistics, with token usage read from the LM's own history.

        Two of these fields used to be structurally dishonest. `retries` was
        hardcoded to 0 while litellm retried internally, so the run report's
        "API retries: 0" line meant "not measured" but read as "none
        happened" -- the audit flagged it as a permanently-dead metric. Token
        counts were hardcoded to 0 next to a comment noting the history has
        them, which it does; they are now actually read.

        `retries` stays unavailable because litellm does not expose its
        internal per-call attempt count, so it is reported as None and the
        run report prints "not observable" rather than a number that cannot
        be anything but zero.
        """
        lat = sorted(self.latencies)
        prompt_tokens = completion_tokens = 0
        for entry in (getattr(self.lm, "history", None) or []):
            usage = entry.get("usage") if isinstance(entry, dict) else None
            if isinstance(usage, dict):
                prompt_tokens += usage.get("prompt_tokens") or 0
                completion_tokens += usage.get("completion_tokens") or 0
        return {
            "calls": self.call_count,
            "retries": None,         # see docstring -- not observable, not zero
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "latency_mean": (sum(lat) / len(lat)) if lat else 0.0,
            "latency_p50": lat[len(lat) // 2] if lat else 0.0,
            "latency_p95": lat[int(len(lat) * 0.95)] if lat else 0.0,
        }


def preflight(generator: DSPyGenerator, spec: DocumentSpec) -> None:
    """One cheap call that proves the model returns usable content before a
    long run starts -- same rationale as company.py's preflight, adapted."""
    text = generator.generate(spec)
    if not text.strip():
        raise ContentError(
            f"preflight: model {generator.model!r} returned no usable text")
