"""Streaming Wahoo client for the translation harness.

Deliberately NOT DSPy. DSPy earns its place in generation -- structured
output, BootstrapFewShot, the compiled program -- but translation is one
string in, one string out with a fixed instruction, and SIMURG needs raw
token deltas that DSPy's abstraction does not expose. This is a thin wrapper
over the OpenAI-compatible endpoint, with the retry/backoff shape the
generation pipeline arrived at the hard way.

Backoff is full jitter, not fixed and not decorrelated: at concurrency > 1,
synchronised retries after a 429 re-trigger the rate limit, and randomising
the whole interval is what breaks the thundering herd (the same reasoning as
`piigen/llm/dspy_generate.py`).
"""
from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass
from typing import Iterator

ENV_KEY = "COMPANY_API_KEY"
LEGACY_ENV_KEY = "HALX_API_KEY"
ENV_BASE_URL = "COMPANY_API_BASE_URL"
ENV_MODEL = "COMPANY_MODEL"
DEFAULT_BASE_URL = "https://api.hal-x.ai/v1"
DEFAULT_MODEL = "wahoo-1.5-preview"

# Retried; anything else is raised immediately. Matches the generation
# pipeline's list -- a 400 means the request is wrong and retrying it just
# burns the attempt budget.
RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


class ConfigError(RuntimeError):
    """Missing credentials or unusable configuration."""


class CallFailed(RuntimeError):
    """The call failed after exhausting retries."""


@dataclass
class ClientConfig:
    model: str = DEFAULT_MODEL
    base_url: str | None = None
    temperature: float = 0.2      # translation wants the best rendering, not variety
    think: bool = False           # see _extra_body
    max_retries: int = 5
    backoff_base: float = 1.5
    backoff_cap: float = 60.0
    timeout: float = 300.0


def _extra_body(think: bool) -> dict:
    """`wahoo-1.5-preview` is a reasoning model. Left on, it spends the whole
    max_tokens budget in a reasoning channel and returns content=None
    (audit F10/F11) -- and translation is a mechanical task where reasoning
    invites restructuring rather than translating. Off by default."""
    return {} if think else {"chat_template_kwargs": {"enable_thinking": False}}


def _status_of(exc: Exception) -> int | None:
    for attr in ("status_code", "http_status", "code"):
        v = getattr(exc, attr, None)
        if isinstance(v, int):
            return v
    resp = getattr(exc, "response", None)
    return getattr(resp, "status_code", None) if resp is not None else None


def _retryable(exc: Exception) -> bool:
    status = _status_of(exc)
    if status is not None:
        return status in RETRY_STATUS
    # Transport-level failures (reset connection, read timeout) carry no
    # status and are exactly the kind worth retrying.
    return isinstance(exc, (TimeoutError, ConnectionError))


class WahooClient:
    """One OpenAI-compatible endpoint, with streaming."""

    def __init__(self, cfg: ClientConfig | None = None, *,
                 api_key: str | None = None) -> None:
        from openai import OpenAI

        self.cfg = cfg or ClientConfig()
        key = (api_key or os.environ.get(ENV_KEY)
               or os.environ.get(LEGACY_ENV_KEY))
        if not key:
            raise ConfigError(
                f"No API key. Export {ENV_KEY} before running:\n"
                f"    export {ENV_KEY}='...'\n"
                f"({LEGACY_ENV_KEY} is also accepted.)")
        self.base_url = (self.cfg.base_url or os.environ.get(ENV_BASE_URL)
                         or DEFAULT_BASE_URL).rstrip("/")
        self.model = os.environ.get(ENV_MODEL) or self.cfg.model
        self._client = OpenAI(api_key=key, base_url=self.base_url,
                              timeout=self.cfg.timeout)
        self.calls = 0
        self.retries = 0

    # -- streaming ------------------------------------------------------
    def stream_chat(self, messages: list[dict], *,
                    max_tokens: int) -> Iterator[str]:
        """Yield text deltas as they arrive.

        Retries are per-attempt and restart the stream from scratch: a
        partially consumed stream cannot be resumed, and the caller's guard
        is stateful over the whole stream anyway, so it must see a clean one.
        """
        last: Exception | None = None
        for attempt in range(self.cfg.max_retries + 1):
            try:
                stream = self._client.chat.completions.create(
                    model=self.model, messages=messages,
                    temperature=self.cfg.temperature, max_tokens=max_tokens,
                    stream=True, extra_body=_extra_body(self.cfg.think),
                )
                self.calls += 1
                for event in stream:
                    if not event.choices:
                        continue
                    delta = event.choices[0].delta.content
                    if delta:
                        yield delta
                return
            except Exception as exc:  # noqa: BLE001
                last = exc
                if attempt >= self.cfg.max_retries or not _retryable(exc):
                    break
                self.retries += 1
                # Full jitter: sleep uniformly in [0, cap], never a fixed
                # interval -- see the module docstring.
                ceiling = min(self.cfg.backoff_cap,
                              self.cfg.backoff_base * (2 ** attempt))
                time.sleep(random.uniform(0, ceiling))
        raise CallFailed(
            f"{type(last).__name__}: {last}"
            f" (after {self.cfg.max_retries} retries)") from last

    def complete(self, messages: list[dict], *, max_tokens: int) -> str:
        """Non-streaming convenience -- used by tools, not the main loop."""
        return "".join(self.stream_chat(messages, max_tokens=max_tokens))
