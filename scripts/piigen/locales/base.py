"""Locale protocol shared by every language pack."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable

# Phrase registers. Sections request a register, not a specific string, so
# adding phrases to a bank immediately increases diversity everywhere that
# register is used.
REGISTERS = [
    "greeting", "closing", "request", "note", "log_msg", "code_comment",
    "ticket_subject", "complaint", "confirmation", "medical", "legal",
    "banking", "hr", "shipping", "meeting", "policy", "escalation",
    "sysadmin", "release_note", "review_comment",
]


@dataclass
class PhraseBank:
    """Register -> list of natural-language strings in this locale."""

    data: dict = field(default_factory=dict)

    def get(self, register: str, rng: random.Random) -> str:
        pool = self.data.get(register)
        if not pool:
            pool = self.data.get("note") or [""]
        return rng.choice(pool)

    def sentences(self, register: str, rng: random.Random, k: int) -> str:
        """k distinct sentences from a register, joined into a paragraph.

        Paragraph-level composition is what multiplies phrase diversity: with
        20 phrases in a register there are 20*19*18 = 6840 distinct 3-sentence
        paragraphs, so a bank of modest size still yields combinatorially many
        surface forms.
        """
        pool = self.data.get(register) or self.data.get("note") or [""]
        k = max(1, min(k, len(pool)))
        picked = rng.sample(pool, k)
        return " ".join(picked)

    def all_strings(self) -> list[str]:
        return [s for v in self.data.values() for s in v]


@dataclass
class ForeignNames:
    """Foreign given names and surnames a locale's text also meets (P2-15,
    D-23d): per origin (`ru`, `tr`, ...), the names and their draw weights.
    A surname is a (masculine, feminine) pair. `cyrillic` maps a Russian
    name's Latin form to its Russian one."""

    given_m: dict = field(default_factory=dict)      # origin -> (names, weights)
    given_f: dict = field(default_factory=dict)
    surnames: dict = field(default_factory=dict)     # origin -> ([(m, f)], weights)
    cyrillic: dict = field(default_factory=dict)

    @property
    def origins(self) -> list:
        return sorted(o for o in self.given_m if o in self.given_f and o in self.surnames)

    def origin_weights(self) -> list:
        """Each origin's share: the sum of its given-name weights."""
        # D-49: math.fsum, the same total on every Python version (sum() of
        # floats changed in 3.12)
        return [math.fsum(self.given_m[o][1]) + math.fsum(self.given_f[o][1]) for o in self.origins]

    def given_names(self) -> list:
        return sorted({n for d in (self.given_m, self.given_f) for names, _w in d.values()
                       for n in names})

    def surname_forms(self) -> list:
        return sorted({f for pairs, _w in self.surnames.values() for p in pairs for f in p})


@dataclass
class Locale:
    code: str
    name: str

    # --- identity --------------------------------------------------------
    first_names_m: list
    first_names_f: list
    surname_stems: list
    surname_builder: Callable          # (stem, is_female, rng) -> surname
    patronymic_builder: Callable | None = None
    # Foreign names drawn for a minority of persons (P2-15, D-23d); None
    # means only the names above.
    foreign_names: ForeignNames | None = None

    # --- geography -------------------------------------------------------
    cities: list = field(default_factory=list)
    # Parallel to `cities` -- relative sampling weight per city. Empty means
    # uniform. A real population is never uniform (a capital dominates real
    # mention frequency by a wide margin), and forcing uniformity to chase
    # "more distinct values" produces a corpus that under-represents the
    # capital and over-represents places a real document would rarely name.
    # These are deliberately coarse tiers, not census figures -- see the
    # locale file's own comment for exactly what precision is and isn't
    # being claimed.
    city_weights: list = field(default_factory=list)
    # The pool CITY values are drawn from when it is set (P2-14, D-23c: the
    # Azerbaijani settlements and common foreign cities), with its draw
    # weights. `cities` stays the major-city list that other code reads
    # (the frozen pii_guard gazetteer, decoys, the invented-PII sweep).
    settlements: list = field(default_factory=list)
    settlement_weights: list = field(default_factory=list)
    districts: list = field(default_factory=list)
    street_stems: list = field(default_factory=list)
    street_builder: Callable | None = None
    address_builder: Callable | None = None
    postal_builder: Callable | None = None

    # --- contact ---------------------------------------------------------
    phone_builder: Callable | None = None
    email_domains: list = field(default_factory=list)
    corporate_domains: list = field(default_factory=list)

    # --- institutions ----------------------------------------------------
    companies: list = field(default_factory=list)
    banks: list = field(default_factory=list)
    hospitals: list = field(default_factory=list)
    universities: list = field(default_factory=list)

    # --- identifiers -----------------------------------------------------
    gov_id_builder: Callable | None = None
    plate_builder: Callable | None = None
    iban_countries: list = field(default_factory=list)

    # --- calendar --------------------------------------------------------
    months: list = field(default_factory=list)
    weekdays: list = field(default_factory=list)
    date_builder: Callable | None = None

    # --- language --------------------------------------------------------
    phrases: PhraseBank = field(default_factory=PhraseBank)
    labels: dict = field(default_factory=dict)      # field labels for forms
    # Function words used by the language-authenticity gate.
    stopwords: set = field(default_factory=set)
    # Characters that only this language (among the four) uses.
    distinctive_chars: str = ""

    # How often a formal register writes SURNAME first ("Məmmədov Elvin").
    # Normal in az/ru/tr official documents; essentially never in English, so
    # this must not be a shared constant.
    surname_first_rate: float = 0.0
    # How often a full name carries a patronymic (Russian formal register).
    patronymic_rate: float = 0.0

    # ------------------------------------------------------------------
    def full_name(self, rng: random.Random, female: bool | None = None) -> str:
        if female is None:
            female = rng.random() < 0.5
        first = rng.choice(self.first_names_f if female else self.first_names_m)
        last = self.surname_builder(rng.choice(self.surname_stems), female, rng)

        if self.patronymic_builder and rng.random() < self.patronymic_rate:
            patr = self.patronymic_builder(rng, female)
            if rng.random() < self.surname_first_rate:
                return f"{last} {first} {patr}"
            return f"{first} {patr} {last}"

        if rng.random() < self.surname_first_rate:
            return f"{last} {first}"

        style = rng.random()
        if style < 0.74:
            return f"{first} {last}"
        if style < 0.84:
            return first
        if style < 0.93:
            return f"{first} {last[0]}."
        return last

    def person_parts(self, rng: random.Random,
                     female: bool | None = None) -> tuple[str, str, bool]:
        """(first, last, female) -- for sections that need the parts separately
        (email local parts, usernames, signature blocks, `Dear Ms X`)."""
        if female is None:
            female = rng.random() < 0.5
        first = rng.choice(self.first_names_f if female else self.first_names_m)
        last = self.surname_builder(rng.choice(self.surname_stems), female, rng)
        return first, last, female

    def label(self, key: str) -> str:
        return self.labels.get(key, key)
