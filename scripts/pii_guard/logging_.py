"""Keep raw PII out of logs, tracebacks and error messages.

Two mechanisms, because the leak paths are different:

* **`RedactingFilter`** -- a `logging.Filter` that rewrites records before a
  handler formats them. Attach it once and any log line containing a value
  from the active vault comes out as `[EMAIL_001]` instead. This catches the
  realistic accident: someone logs `f"processing {text}"` where `text` is the
  raw extraction.

* **`safe_excerpt`** -- for messages this package builds itself. Exceptions
  are the sneakiest leak path, because the natural way to write a useful
  error is to quote the offending text. Every error message in this package
  goes through `safe_excerpt`, which reports shape (length, character
  classes) rather than content.

The filter is scoped to values registered on it, not a global PII regex --
scanning every log line with the full detector would be slow and would still
miss anything the detector missed. Registering the vault's values is exact.
"""

from __future__ import annotations

import logging
import re
import threading
import unicodedata

from .vault import Vault

_LOG = logging.getLogger("pii_guard")


def value_present(text: str, value: str) -> bool:
    """True if `value` appears in `text` as a whole token/phrase, not as a
    substring inside a longer, unrelated word.

    Every leak check in this package used to be a bare `value in text`
    substring test. That is too blunt for the languages this service
    actually handles: Azerbaijani, Turkish and Russian are all heavily
    suffixing/compounding, so a masked value is very often the PREFIX of a
    completely unrelated, non-PII word elsewhere in the same document --
    found by testing against realistic documents, not synthetic single-
    mention smoke tests. Two confirmed false alarms from that: a masked
    Turkish word "Kira" ("rent", itself a real bug -- see detect/names.py)
    triggering on "Kiracı" ("tenant"), and a correctly-masked city "Баку"
    ("Baku") triggering on "БакуБанк" (the bank's own brand name, "BakuBank"
    -- a real, correctly-unmasked proper noun that merely starts with the
    same four letters). Neither is a leak: the raw value never actually
    appears as its own word anywhere in the output.
    """
    if not value:
        return False
    return re.search(r"(?<!\w)" + re.escape(value) + r"(?!\w)", text,
                     re.UNICODE) is not None


class RedactingFilter(logging.Filter):
    """Replaces known PII values with their placeholders in log records.

    Thread-safe: documents are processed concurrently in any real service, so
    the registry is guarded and keyed per vault.
    """

    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.Lock()
        self._values: dict[str, str] = {}      # value -> placeholder

    def register(self, vault: Vault) -> None:
        with self._lock:
            for placeholder, value in vault.items():
                if value and len(value) >= 3:   # 1-2 char values would over-match
                    self._values[value] = placeholder

    def forget(self, vault: Vault) -> None:
        with self._lock:
            for _placeholder, value in vault.items():
                self._values.pop(value, None)

    def _scrub(self, s: str) -> str:
        with self._lock:
            items = sorted(self._values.items(), key=lambda kv: len(kv[0]), reverse=True)
        for value, placeholder in items:
            pattern = re.compile(r"(?<!\w)" + re.escape(value) + r"(?!\w)", re.UNICODE)
            s = pattern.sub(placeholder, s)
        return s

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = self._scrub(record.msg)
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {k: self._scrub(v) if isinstance(v, str) else v
                                   for k, v in record.args.items()}
                else:
                    record.args = tuple(self._scrub(a) if isinstance(a, str) else a
                                        for a in record.args)
            if record.exc_text:
                record.exc_text = self._scrub(record.exc_text)
        except Exception:                       # a logging filter must never raise
            return True
        return True


#: Process-wide filter. `install()` attaches it to the root logger.
REDACTOR = RedactingFilter()
_installed = False


def install(logger: logging.Logger | None = None) -> RedactingFilter:
    """Attach the redactor. Idempotent."""
    global _installed
    target = logger or logging.getLogger()
    if not any(isinstance(f, RedactingFilter) for f in target.filters):
        target.addFilter(REDACTOR)
    for handler in target.handlers:
        if not any(isinstance(f, RedactingFilter) for f in handler.filters):
            handler.addFilter(REDACTOR)
    _installed = True
    return REDACTOR


def safe_excerpt(text: str, limit: int = 60) -> str:
    """Describe text without quoting it.

    Used in this package's own error messages and debug lines. Returns
    something like `<214 chars, 3 lines, alpha+digit+punct>` -- enough to
    debug an extraction or offset bug, never enough to reconstruct a value.
    """
    if text is None:
        return "<none>"
    if not text:
        return "<empty>"
    classes = set()
    for ch in text[:2000]:
        cat = unicodedata.category(ch)
        if cat.startswith("L"):
            classes.add("alpha")
        elif cat.startswith("N"):
            classes.add("digit")
        elif ch.isspace():
            classes.add("space")
        else:
            classes.add("punct")
    lines = text.count("\n") + 1
    return (f"<{len(text)} chars, {lines} line{'s' if lines != 1 else ''}, "
            f"{'+'.join(sorted(classes))}>")


def log_sanitisation(vault: Vault, n_detections: int, *, doc: str = "") -> None:
    """The one summary line this package logs. Counts only, never values."""
    families: dict[str, int] = {}
    for placeholder in vault.placeholders():
        fam = placeholder.strip("[]").rsplit("_", 1)[0]
        families[fam] = families.get(fam, 0) + 1
    summary = ", ".join(f"{k}={v}" for k, v in sorted(families.items())) or "none"
    _LOG.info("sanitised %s: %d spans masked (%s)",
              doc or "document", n_detections, summary)
