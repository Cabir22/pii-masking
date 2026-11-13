# -*- coding: utf-8 -*-
"""Fetch the external name pools used by substitute_names.py and (via
scripts/name_pools.py) the pii_guard GazetteerBackend name fallback.

Downloads into data/name_sources/ (git-ignored, ~16 MB):

  RU  sorokinpf/russian_names       -- male/female given names + surnames, with counts
  EN  US Census 2010 surnames       -- via fivethirtyeight mirror, with counts
  EN  ~22k given names              -- Moby Word List (public domain, Project
                                        Gutenberg #3201) via dominictarr/random-name

EN given names originally shipped as a local Kaggle "names" dump with no
canonical URL, so this script used to only warn that the file was missing.
dominictarr/random-name ships two candidate files for this and they are NOT
interchangeable: `first-names.txt` (~4,945 entries) turned out, on
inspection, to be female names only -- "John", "David", "Michael",
"Jonathan" are all absent, which silently halved English given-name
gazetteer coverage. `names.txt` (~22k entries, the actual Moby Word List
proper-names corpus the repo's own README points to, public domain) has
both genders and both given names and surnames mixed together -- some
entries are surnames, but that costs nothing here: scripts/name_pools.py
loads it purely as a membership set for the gazetteer fallback, which
already checks both the given-name and surname pools per candidate word,
so an entry present in both is harmless. Swap in a different/larger source
here if one becomes available; nothing downstream depends on this specific
file beyond its one-name-per-line shape.

Usage:
    python scripts/fetch_name_sources.py
"""

from __future__ import annotations
import sys
import urllib.request
from pathlib import Path

DEST = Path(__file__).resolve().parent.parent / "data" / "name_sources"

SOROKIN = "https://raw.githubusercontent.com/sorokinpf/russian_names/master"
RANDOM_NAME = "https://raw.githubusercontent.com/dominictarr/random-name/master"
FILES = {
    "russian_male_names.csv":   f"{SOROKIN}/russian_male_names.csv",
    "russian_female_names.csv": f"{SOROKIN}/russian_female_names.csv",
    "russian_surnames.csv":     f"{SOROKIN}/russian_surnames.csv",
    "us_surnames.csv": (
        "https://raw.githubusercontent.com/fivethirtyeight/data/master/"
        "most-common-name/surnames.csv"
    ),
    "en_given_names.txt": f"{RANDOM_NAME}/names.txt",
}


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        target = DEST / name
        if target.exists() and target.stat().st_size > 0:
            print(f"  have  {name} ({target.stat().st_size:,} B)")
            continue
        print(f"  fetch {name} <- {url}")
        try:
            urllib.request.urlretrieve(url, target)
            print(f"        {target.stat().st_size:,} B")
        except Exception as e:
            print(f"        FAILED: {e}", file=sys.stderr)
            return 1

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
