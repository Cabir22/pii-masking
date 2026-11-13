# -*- coding: utf-8 -*-
"""Load name pools for all four languages: AZ, EN, RU, TR.

Each language provides three lists of NameEntry(name, count, gender):
  - given_names_m   male given names
  - given_names_f   female given names
  - surnames        surnames (gender mixed; RU and AZ carry gendered forms)

All names are native orthography (AZ/EN/TR Latin, RU Cyrillic) and Title Case.
Counts are frequency weights; equal weight 1.0 where the source has no counts.

Data sources (data/name_sources/, fetched once):
  en_given_names.txt      32k US given names, lowercase, no gender
  us_surnames.csv         US Census 2010 surnames, ALL CAPS, with count
  russian_male_names.csv  sorokinpf, Cyrillic lowercase, with count
  russian_female_names.csv
  russian_surnames.csv    ~99k, both -ov and -ova forms, with count
AZ names come from piigen.locales.az (FIRST_M/FIRST_F lists, SURNAME_STEMS +
the az.surname() builder). TR names come from scripts/tr_names_out/*.pool.csv.
"""

from __future__ import annotations
import csv
import random
import re
import sys
from pathlib import Path
from typing import NamedTuple


class NameEntry(NamedTuple):
    name: str
    count: float
    gender: str | None = None  # "M", "F", or None


_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "data" / "name_sources"
_TR_OUT = Path(__file__).resolve().parent / "tr_names_out"

# How many AZ surname forms to pre-generate from the stem list. Verified stems
# are weighted up so common real surnames dominate the frequency-weighted draw.
_AZ_SURNAME_VERIFIED_WEIGHT = 8.0
_AZ_SURNAME_PLAIN_WEIGHT = 1.0


def _title_ru(s: str) -> str:
    """Title-case a Cyrillic token (str.title mishandles some scripts less,
    but .capitalize on a single word is what we want here)."""
    s = s.strip()
    return s[:1].upper() + s[1:].lower() if s else s


def _title_latin(s: str) -> str:
    s = s.strip()
    if not s:
        return s
    # keep internal apostrophes/hyphens, capitalise each alpha run start
    out = []
    cap = True
    for ch in s:
        if cap and ch.isalpha():
            out.append(ch.upper())
            cap = False
        elif ch in " -'":
            out.append(ch)
            cap = True
        else:
            out.append(ch.lower())
    return "".join(out)


# ============================================================================
# AZ  --  piigen locale
# ============================================================================

def load_az_names() -> dict[str, list[NameEntry]]:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from piigen.locales import az

    given_m = [NameEntry(n, 1.0, "M") for n in az.FIRST_M]
    given_f = [NameEntry(n, 1.0, "F") for n in az.FIRST_F]

    # Pre-generate surnames from stems, both gender forms.
    rng = random.Random(20260909)
    verified = set(getattr(az, "SURNAME_STEMS_VERIFIED", []))
    surnames: list[NameEntry] = []
    seen: set[str] = set()
    for stem in az.SURNAME_STEMS:
        w = _AZ_SURNAME_VERIFIED_WEIGHT if stem in verified else _AZ_SURNAME_PLAIN_WEIGHT
        for female in (False, True):
            form = az.surname(stem, female, rng)
            if form and form not in seen:
                seen.add(form)
                surnames.append(NameEntry(form, w, "F" if female else "M"))

    return {"given_names_m": given_m, "given_names_f": given_f, "surnames": surnames}


# ============================================================================
# EN  --  US given names + Census surnames
# ============================================================================

def load_en_names() -> dict[str, list[NameEntry]]:
    given_path = _SRC / "en_given_names.txt"
    surnames_path = _SRC / "us_surnames.csv"

    given: list[NameEntry] = []
    if given_path.exists():
        with open(given_path, encoding="utf-8") as f:
            for line in f:
                nm = _title_latin(line)
                if nm and nm.replace("'", "").replace("-", "").isalpha():
                    given.append(nm)
    # names.txt has no gender: expose the same list to both slots
    given_m = [NameEntry(n, 1.0, "M") for n in given]
    given_f = [NameEntry(n, 1.0, "F") for n in given]

    surnames: list[NameEntry] = []
    if surnames_path.exists():
        with open(surnames_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw = (row.get("name") or "").strip()
                if not raw or raw.upper() == "ALL OTHER NAMES":
                    continue
                try:
                    cnt = float(row.get("count") or 1.0)
                except ValueError:
                    cnt = 1.0
                surnames.append(NameEntry(_title_latin(raw), cnt))
    if not surnames:
        surnames = [NameEntry(n, 1.0) for n in
                    ("Smith", "Johnson", "Williams", "Brown", "Jones")]

    return {"given_names_m": given_m, "given_names_f": given_f, "surnames": surnames}


# ============================================================================
# RU  --  sorokinpf/russian_names
# ============================================================================

_RU_NAME_RE = re.compile(r"^[а-яёА-ЯЁ]+(?:-[а-яёА-ЯЁ]+)?$")


def _load_ru_csv(path: Path, gender: str | None) -> list[NameEntry]:
    """Load a sorokinpf name/count CSV, rejecting the handful of dirty rows
    (stray Latin letters, digits, multi-word org strings) it carries."""
    out: list[NameEntry] = []
    if not path.exists():
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split(",")
            if not parts or not parts[0].strip():
                continue
            raw = parts[0].strip()
            if not _RU_NAME_RE.match(raw) or len(raw) > 24:
                continue  # dirty row: Latin char, digit, space, or too long
            name = _title_ru(raw)
            try:
                cnt = float(parts[1]) if len(parts) > 1 and parts[1].strip() else 1.0
            except ValueError:
                cnt = 1.0
            out.append(NameEntry(name, cnt, gender))
    return out


def load_ru_names() -> dict[str, list[NameEntry]]:
    given_m = _load_ru_csv(_SRC / "russian_male_names.csv", "M")
    given_f = _load_ru_csv(_SRC / "russian_female_names.csv", "F")
    surnames = _load_ru_csv(_SRC / "russian_surnames.csv", None)

    if not given_m:
        given_m = [NameEntry(n, 1.0, "M") for n in
                   ("Иван", "Сергей", "Николай", "Алексей", "Дмитрий")]
    if not given_f:
        given_f = [NameEntry(n, 1.0, "F") for n in
                   ("Мария", "Анна", "Ольга", "Наталья", "Татьяна")]
    if not surnames:
        surnames = [NameEntry(n, 1.0) for n in
                    ("Иванов", "Петров", "Смирнов", "Кузнецов", "Попов")]

    return {"given_names_m": given_m, "given_names_f": given_f, "surnames": surnames}


# ============================================================================
# TR  --  built pools (scripts/tr_names_out/)
# ============================================================================

def _load_tr_csv(path: Path, want_gender: bool) -> list[NameEntry]:
    out: list[NameEntry] = []
    if not path.exists():
        return out
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("name") or "").strip()
            if not name:
                continue
            try:
                cnt = float(row.get("count") or 1.0)
            except ValueError:
                cnt = 1.0
            g = (row.get("gender") or "").strip() or None if want_gender else None
            out.append(NameEntry(name, cnt, g))
    return out


def load_tr_names() -> dict[str, list[NameEntry]]:
    given = _load_tr_csv(_TR_OUT / "tr_given_names.pool.csv", True) \
        or _load_tr_csv(_TR_OUT / "tr_given_names.csv", True)
    surnames = _load_tr_csv(_TR_OUT / "tr_surnames.pool.csv", False) \
        or _load_tr_csv(_TR_OUT / "tr_surnames.csv", False)

    given_m = [e for e in given if e.gender == "M"]
    given_f = [e for e in given if e.gender == "F"]

    if not given_m:
        given_m = [NameEntry(n, 1.0, "M") for n in
                   ("Ahmet", "Mehmet", "Mustafa", "Ali", "Hüseyin")]
    if not given_f:
        given_f = [NameEntry(n, 1.0, "F") for n in
                   ("Ayşe", "Fatma", "Emine", "Hatice", "Zeynep")]
    if not surnames:
        surnames = [NameEntry(n, 1.0) for n in
                    ("Yılmaz", "Kaya", "Demir", "Şahin", "Çelik")]

    return {"given_names_m": given_m, "given_names_f": given_f, "surnames": surnames}


# ============================================================================
# Public API
# ============================================================================

_POOLS: dict[str, dict[str, list[NameEntry]]] | None = None


def load_all_pools() -> dict[str, dict[str, list[NameEntry]]]:
    global _POOLS
    if _POOLS is None:
        _POOLS = {
            "az": load_az_names(),
            "en": load_en_names(),
            "ru": load_ru_names(),
            "tr": load_tr_names(),
        }
    return _POOLS


def get_pool(lang: str) -> dict[str, list[NameEntry]]:
    return load_all_pools().get(lang, {})


if __name__ == "__main__":
    import io
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    pools = load_all_pools()
    for lang, pool in pools.items():
        out.write(f"\n{lang.upper()}:\n")
        for slot in ("given_names_m", "given_names_f", "surnames"):
            entries = pool[slot]
            sample = ", ".join(e.name for e in entries[:5])
            out.write(f"  {slot:14} {len(entries):>7,}   e.g. {sample}\n")
    out.flush()
