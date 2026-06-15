"""
Unified LLM Client
==================

Sprint: BTCAAAAA-36469 (AI Recs P1)

A single, configurable HTTP client for LLM providers (OpenRouter today,
extensible to other OpenAI-compatible endpoints). Replaces the scattered
``requests.post`` call inside ``ai_recommendation_enhancer._query_openrouter``
with:

- **Single configuration** (``LlmClientConfig``) — env-driven defaults, but every
  field is overridable per-instance for tests.
- **Exponential backoff with jitter** on transient failures (timeouts, 5xx,
  connection errors).
- **No retry on 4xx** — those are caller errors, retrying doesn't help.
- **Per-attempt timeout** — bounded worst case per request.
- **Total time budget** — aborts retries once the cumulative elapsed time
  crosses the budget, even if attempts remain.
- **Structured error** (``LlmError``) — callers can pattern-match on cause.

The contract is exercised by ``tests/optimizer_v3/test_ai_recommendation_enhancer_p1.py``.
"""

from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests


class LlmError(Exception):
    """Raised when the LLM client cannot complete a request.

    The string form always includes the failure category and (when relevant)
    the time-budget message.
    """


@dataclass
class LlmClientConfig:
    """Configuration for the unified LLM client.

    Defaults are env-driven (``OPENROUTER_API_KEY``, ``AI_MODEL``) but every
    field is overridable for tests. All time values are seconds.
    """

    api_key: str
    model: str
    base_url: str
    max_attempts: int = 4
    initial_backoff_seconds: float = 0.5
    max_backoff_seconds: float = 8.0
    per_attempt_timeout_seconds: float = 30.0
    total_time_budget_seconds: float = 60.0
    jitter_seconds: float = 0.25
    extra_headers: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "LlmClientConfig":
        """Build a config from environment variables (OpenRouter defaults)."""
        return cls(
            api_key=os.getenv("OPENROUTER_API_KEY", ""),
            model=os.getenv("AI_MODEL", "anthropic/claude-3.5-sonnet"),
            base_url=os.getenv(
                "AI_BASE_URL", "https://openrouter.ai/api/v1/chat/completions"
            ),
            max_attempts=int(os.getenv("AI_MAX_ATTEMPTS", "4")),
            initial_backoff_seconds=float(
                os.getenv("AI_INITIAL_BACKOFF_SECONDS", "0.5")
            ),
            max_backoff_seconds=float(
                os.getenv("AI_MAX_BACKOFF_SECONDS", "8.0")
            ),
            per_attempt_timeout_seconds=float(
                os.getenv("AI_PER_ATTEMPT_TIMEOUT_SECONDS", "30.0")
            ),
            total_time_budget_seconds=float(
                os.getenv("AI_TOTAL_TIME_BUDGET_SECONDS", "60.0")
            ),
            jitter_seconds=float(os.getenv("AI_JITTER_SECONDS", "0.25")),
        )


class LlmClient:
    """Thin, retry-aware HTTP client for OpenAI-compatible chat-completion APIs.

    The client does NOT own the system prompt, the message construction, or the
    response parsing — those are responsibilities of the caller. This client
    focuses on transport: send ``messages`` + options, return the parsed JSON
    response body, retry on transient failures, fail fast on caller errors.
    """

    def __init__(self, config: Optional[LlmClientConfig] = None):
        if config is None:
            config = LlmClientConfig.from_env()
        self._config = config

    @property
    def config(self) -> LlmClientConfig:
        return self._config

    def chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float = 0.3,
        max_tokens: int = 3000,
        response_format: Optional[Dict[str, Any]] = None,
        extra_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a chat-completion request and return the parsed JSON response.

        Retries on timeouts, connection errors, and 5xx responses with
        exponential backoff + jitter. Aborts once ``max_attempts`` is reached
        OR the ``total_time_budget_seconds`` budget is exhausted, whichever
        comes first. 4xx responses raise ``LlmError`` immediately (no retry).
        """
        if not self._config.api_key:
            raise LlmError("api_key is empty — set OPENROUTER_API_KEY in .env")

        payload: Dict[str, Any] = {
            "model": self._config.model,
            "messages": list(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format is not None:
            payload["response_format"] = response_format
        if extra_payload:
            payload.update(extra_payload)

        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }
        headers.update(self._config.extra_headers)

        return self._post_with_retries(
            url=self._config.base_url,
            headers=headers,
            json_payload=payload,
        )

    def _post_with_retries(
        self,
        *,
        url: str,
        headers: Dict[str, str],
        json_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """POST with retry/backoff/jitter + total-time-budget enforcement."""
        cfg = self._config
        deadline = time.monotonic() + cfg.total_time_budget_seconds
        last_error: Optional[BaseException] = None
        backoff = cfg.initial_backoff_seconds

        for attempt in range(1, cfg.max_attempts + 1):
            if time.monotonic() >= deadline:
                raise LlmError(
                    f"LLM time budget exhausted before attempt {attempt} "
                    f"(budget={cfg.total_time_budget_seconds}s, "
                    f"cause={last_error!r})"
                )

            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=json_payload,
                    timeout=cfg.per_attempt_timeout_seconds,
                )
            except requests.exceptions.Timeout as exc:
                last_error = exc
                self._sleep_backoff_or_bail(backoff, deadline, attempt, cfg)
                backoff = min(backoff * 2.0, cfg.max_backoff_seconds)
                continue
            except requests.exceptions.RequestException as exc:
                last_error = exc
                self._sleep_backoff_or_bail(backoff, deadline, attempt, cfg)
                backoff = min(backoff * 2.0, cfg.max_backoff_seconds)
                continue

            status = getattr(response, "status_code", 0)
            if 400 <= status < 500:
                body_preview = (response.text or "")[:200]
                raise LlmError(
                    f"LLM call rejected (HTTP {status}, no retry): {body_preview}"
                )

            if 500 <= status < 600:
                last_error = RuntimeError(f"HTTP {status}")
                self._sleep_backoff_or_bail(backoff, deadline, attempt, cfg)
                backoff = min(backoff * 2.0, cfg.max_backoff_seconds)
                continue

            try:
                return response.json()
            except ValueError as exc:
                last_error = exc
                self._sleep_backoff_or_bail(backoff, deadline, attempt, cfg)
                backoff = min(backoff * 2.0, cfg.max_backoff_seconds)
                continue

        raise LlmError(
            f"LLM call failed after {cfg.max_attempts} attempts "
            f"(cause={last_error!r})"
        )

    def _sleep_backoff_or_bail(
        self,
        backoff: float,
        deadline: float,
        attempt: int,
        cfg: LlmClientConfig,
    ) -> None:
        """Sleep for ``backoff + jitter`` — or raise ``LlmError`` if no time left."""
        if cfg.jitter_seconds > 0:
            jitter = random.random() * cfg.jitter_seconds
        else:
            jitter = 0.0
        sleep_seconds = max(0.0, backoff + jitter)

        now = time.monotonic()
        if now >= deadline:
            raise LlmError(
                f"LLM time budget exhausted before attempt {attempt + 1} "
                f"sleep (budget={cfg.total_time_budget_seconds}s, "
                f"cause=retries exhausted)"
            )

        remaining = deadline - now
        if sleep_seconds > remaining:
            sleep_seconds = remaining
            if sleep_seconds <= 0:
                raise LlmError(
                    f"LLM time budget exhausted (budget="
                    f"{cfg.total_time_budget_seconds}s, "
                    f"cause=no time left for backoff)"
                )

        time.sleep(sleep_seconds)
