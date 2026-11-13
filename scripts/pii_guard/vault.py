"""The placeholder -> original-value mapping. Local only, always.

This object is the one thing in the pipeline that still contains raw PII after
masking. Everything about it is built to make it hard to leak by accident:

* `__repr__` / `__str__` show counts, never values. A stray `print(vault)`,
  an f-string in a log line, or a `%r` in an exception message all render as
  `Vault(3 entries, 2 families)`.
* It is not JSON-serialisable. `json.dumps(vault)` raises rather than quietly
  writing the mapping to a request body or a log file.
* `__getstate__` raises, so `pickle`/`copy.deepcopy`/`multiprocessing` cannot
  ship it to another process or a cache.
* Reading a value is deliberately a method call (`reveal`), not attribute or
  index access, so every read site greps as `\\.reveal\\(` in a security review.

None of this makes leaking impossible -- a determined caller can iterate
`_by_placeholder`. It makes leaking *require intent*, which is the realistic
goal: the failure mode this defends against is a debug print, not an attacker
with local code execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class VaultSerializationError(TypeError):
    """Raised on any attempt to serialise the mapping out of the process."""


@dataclass(slots=True)
class Vault:
    """placeholder <-> original value, one per sanitised document."""

    _by_placeholder: dict[str, str] = field(default_factory=dict, repr=False)
    _by_key: dict[tuple[str, str], str] = field(default_factory=dict, repr=False)

    # -- writing ---------------------------------------------------------
    def put(self, placeholder: str, value: str, *, key: tuple[str, str] | None = None) -> None:
        existing = self._by_placeholder.get(placeholder)
        if existing is not None and existing != value:
            raise ValueError(
                f"placeholder collision: {placeholder} already maps to a "
                f"different value. This would make rehydration ambiguous.")
        self._by_placeholder[placeholder] = value
        if key is not None:
            self._by_key[key] = placeholder

    # -- reading ---------------------------------------------------------
    def reveal(self, placeholder: str) -> str | None:
        """The original value behind a placeholder. Named to be greppable."""
        return self._by_placeholder.get(placeholder)

    def placeholder_for(self, key: tuple[str, str]) -> str | None:
        """Existing placeholder for a `(family, value)` key, if any."""
        return self._by_key.get(key)

    def placeholders(self) -> list[str]:
        """Placeholder strings only -- safe to log."""
        return list(self._by_placeholder)

    def values(self) -> list[str]:
        """Raw values. Only for the local rehydration step and leak tests."""
        return list(self._by_placeholder.values())

    def items(self):
        """Raw mapping. Local rehydration and tests only -- never a prompt."""
        return self._by_placeholder.items()

    # -- containment -----------------------------------------------------
    def __len__(self) -> int:
        return len(self._by_placeholder)

    def __bool__(self) -> bool:
        return bool(self._by_placeholder)

    def __contains__(self, placeholder: object) -> bool:
        return placeholder in self._by_placeholder

    # -- leak resistance -------------------------------------------------
    def __repr__(self) -> str:
        fams = {p.strip("[]").rsplit("_", 1)[0] for p in self._by_placeholder}
        return f"Vault({len(self._by_placeholder)} entries, {len(fams)} families)"

    __str__ = __repr__

    def __getstate__(self):
        raise VaultSerializationError(
            "the PII vault must not be pickled, copied between processes, or "
            "cached. It exists only for local rehydration.")

    def __reduce__(self):
        raise VaultSerializationError(
            "the PII vault must not be pickled, copied between processes, or "
            "cached. It exists only for local rehydration.")

    def for_json(self):  # pragma: no cover - defensive
        raise VaultSerializationError(
            "the PII vault must never be serialised into a prompt, a request "
            "body, a log record, or a database row.")
