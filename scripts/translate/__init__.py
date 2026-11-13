"""Translation harness: turns the Azerbaijani split into EN/TR/RU carrier
text while keeping every entity span byte-exact (placeholder slotting).

 (2026-09-03 entry) for the design. This package is
language-agnostic -- `--lang en|tr|ru` picks a config, never a code path.
"""
