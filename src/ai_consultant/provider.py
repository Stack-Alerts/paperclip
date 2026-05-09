"""
LLM Provider Abstraction — AI Consultant (P1.3)

Config-driven factory for OpenAI, Anthropic, and Ollama backends with retry
logic, cost estimation, and tool/function-calling support.

Usage:
    from ai_consultant.provider import create_provider

    provider = create_provider()                # reads LLM_PROVIDER env var
    response = provider.chat(messages, tools)
    cost = provider.estimate_cost(
        response.prompt_tokens, response.completion_tokens
    )
"""

from __future__ import annotations

import abc
import json
import logging
import os
import random
import time
from dataclasses import dataclass, field
from typing import Any

import yaml

log = logging.getLogger(__name__)


# ── Data models ───────────────────────────────────────────────────────────────


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ChatResponse:
    content: str
    tool_calls: list[ToolCall]
    prompt_tokens: int
    completion_tokens: int
    model: str


@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter: bool = True


@dataclass
class ProviderConfig:
    provider: str = "anthropic"
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    retry: RetryConfig = field(default_factory=RetryConfig)


# ── Abstract base ─────────────────────────────────────────────────────────────


class LLMProvider(abc.ABC):
    """Vendor-agnostic LLM interface consumed by consultant_service (P1.4)."""

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config

    @abc.abstractmethod
    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ChatResponse:
        """Send messages and optional tools, return a structured response."""

    @abc.abstractmethod
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Return estimated USD cost for a call of the given token counts."""

    def _retry(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        cfg = self._config.retry
        last_exc: Exception | None = None
        for attempt in range(cfg.max_retries + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                if attempt == cfg.max_retries:
                    break
                delay = min(cfg.base_delay * (2**attempt), cfg.max_delay)
                if cfg.jitter:
                    delay *= 0.5 + random.random() * 0.5
                log.warning(
                    "LLM call failed (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1,
                    cfg.max_retries + 1,
                    delay,
                    exc,
                )
                time.sleep(delay)
        raise last_exc  # type: ignore[misc]


# ── Anthropic ─────────────────────────────────────────────────────────────────


class AnthropicProvider(LLMProvider):
    """Claude backend via the official Anthropic SDK with prompt caching."""

    _DEFAULT_MODEL = "claude-sonnet-4-6"
    _INPUT_COST_PER_M = 3.0
    _OUTPUT_COST_PER_M = 15.0

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        import anthropic as _anthropic  # lazy import — keeps module importable

        api_key = config.api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = _anthropic.Anthropic(api_key=api_key)
        self._model = config.model or self._DEFAULT_MODEL

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ChatResponse:
        def _call() -> Any:
            system_blocks, user_messages = self._split_messages(messages)
            kwargs: dict[str, Any] = {
                "model": self._model,
                "max_tokens": 4096,
                "messages": user_messages,
            }
            if system_blocks:
                kwargs["system"] = system_blocks
            if tools:
                kwargs["tools"] = self._format_tools(tools)
            return self._client.messages.create(**kwargs)

        resp = self._retry(_call)

        content_text = ""
        tool_calls: list[ToolCall] = []
        for block in resp.content:
            if block.type == "text":
                content_text = block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, arguments=block.input)
                )

        return ChatResponse(
            content=content_text,
            tool_calls=tool_calls,
            prompt_tokens=resp.usage.input_tokens,
            completion_tokens=resp.usage.output_tokens,
            model=resp.model,
        )

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return (
            prompt_tokens * self._INPUT_COST_PER_M / 1_000_000
            + completion_tokens * self._OUTPUT_COST_PER_M / 1_000_000
        )

    def _split_messages(
        self, messages: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Separate system messages; attach cache_control to the last system block."""
        system_texts: list[str] = []
        user_messages: list[dict[str, Any]] = []
        for m in messages:
            if m.get("role") == "system":
                system_texts.append(m["content"])
            else:
                user_messages.append(m)

        system_blocks: list[dict[str, Any]] = []
        for i, text in enumerate(system_texts):
            block: dict[str, Any] = {"type": "text", "text": text}
            if i == len(system_texts) - 1:
                # Mark the final (largest/most-stable) block for ephemeral caching
                block["cache_control"] = {"type": "ephemeral"}
            system_blocks.append(block)

        return system_blocks, user_messages

    @staticmethod
    def _format_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "name": t["name"],
                "description": t.get("description", ""),
                "input_schema": t.get(
                    "parameters", {"type": "object", "properties": {}}
                ),
            }
            for t in tools
        ]


# ── OpenAI ────────────────────────────────────────────────────────────────────


class OpenAIProvider(LLMProvider):
    """GPT-4o backend via the official OpenAI SDK."""

    _DEFAULT_MODEL = "gpt-4o"
    _INPUT_COST_PER_M = 5.0
    _OUTPUT_COST_PER_M = 15.0

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        import openai as _openai  # lazy import

        api_key = config.api_key or os.environ.get("OPENAI_API_KEY")
        self._client = _openai.OpenAI(api_key=api_key)
        self._model = config.model or self._DEFAULT_MODEL

    @staticmethod
    def _adapt_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert Anthropic-format tool history to OpenAI message format."""
        result: list[dict[str, Any]] = []
        for m in messages:
            role = m.get("role")
            content = m.get("content")
            if role == "assistant" and isinstance(content, list):
                # Anthropic: [{"type":"text","text":"..."}, {"type":"tool_use","id":...}]
                texts = [b["text"] for b in content if b.get("type") == "text"]
                tool_uses = [b for b in content if b.get("type") == "tool_use"]
                msg: dict[str, Any] = {
                    "role": "assistant",
                    "content": " ".join(texts) or None,
                }
                if tool_uses:
                    msg["tool_calls"] = [
                        {
                            "id": b["id"],
                            "type": "function",
                            "function": {
                                "name": b["name"],
                                "arguments": json.dumps(b["input"]),
                            },
                        }
                        for b in tool_uses
                    ]
                result.append(msg)
            elif (
                role == "user"
                and isinstance(content, list)
                and content
                and content[0].get("type") == "tool_result"
            ):
                # Anthropic tool_result blocks → individual OpenAI tool messages
                for block in content:
                    if block.get("type") == "tool_result":
                        result.append({
                            "role": "tool",
                            "tool_call_id": block["tool_use_id"],
                            "content": block["content"],
                        })
            else:
                result.append(m)
        return result

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ChatResponse:
        adapted = self._adapt_messages(messages)

        def _call() -> Any:
            kwargs: dict[str, Any] = {
                "model": self._model,
                "messages": adapted,
            }
            if tools:
                kwargs["tools"] = self._format_tools(tools)
            return self._client.chat.completions.create(**kwargs)

        resp = self._retry(_call)
        msg = resp.choices[0].message

        tool_calls: list[ToolCall] = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments),
                    )
                )

        return ChatResponse(
            content=msg.content or "",
            tool_calls=tool_calls,
            prompt_tokens=resp.usage.prompt_tokens,
            completion_tokens=resp.usage.completion_tokens,
            model=resp.model,
        )

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return (
            prompt_tokens * self._INPUT_COST_PER_M / 1_000_000
            + completion_tokens * self._OUTPUT_COST_PER_M / 1_000_000
        )

    @staticmethod
    def _format_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get(
                        "parameters", {"type": "object", "properties": {}}
                    ),
                },
            }
            for t in tools
        ]


# ── Ollama ────────────────────────────────────────────────────────────────────


class OllamaProvider(LLMProvider):
    """Local Ollama backend via plain httpx — zero cost, zero latency variance."""

    _DEFAULT_BASE_URL = "http://localhost:11434"
    _DEFAULT_MODEL = "llama3"

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        import httpx  # lazy import

        self._base_url = (
            config.base_url
            or os.environ.get("OLLAMA_BASE_URL", self._DEFAULT_BASE_URL)
        )
        self._model = (
            config.model or os.environ.get("OLLAMA_MODEL", self._DEFAULT_MODEL)
        )
        self._http = httpx.Client(timeout=120.0)

    @staticmethod
    def _adapt_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert Anthropic-format tool history to Ollama/OpenAI message format."""
        return OpenAIProvider._adapt_messages(messages)

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ChatResponse:
        adapted = self._adapt_messages(messages)

        def _call() -> dict[str, Any]:
            payload: dict[str, Any] = {
                "model": self._model,
                "messages": adapted,
                "stream": False,
            }
            if tools:
                payload["tools"] = self._format_tools(tools)
            resp = self._http.post(f"{self._base_url}/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json()  # type: ignore[return-value]

        data = self._retry(_call)
        msg = data.get("message", {})

        tool_calls: list[ToolCall] = []
        for tc in msg.get("tool_calls", []):
            fn = tc.get("function", {})
            tool_calls.append(
                ToolCall(
                    id=tc.get("id", fn.get("name", "")),
                    name=fn.get("name", ""),
                    arguments=fn.get("arguments", {}),
                )
            )

        return ChatResponse(
            content=msg.get("content", ""),
            tool_calls=tool_calls,
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            model=self._model,
        )

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return 0.0  # local inference

    @staticmethod
    def _format_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get(
                        "parameters", {"type": "object", "properties": {}}
                    ),
                },
            }
            for t in tools
        ]


# ── Factory ───────────────────────────────────────────────────────────────────

_PROVIDERS: dict[str, type[LLMProvider]] = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "ollama": OllamaProvider,
}


def _config_from_yaml(path: str) -> ProviderConfig:
    with open(path) as f:
        d: dict[str, Any] = yaml.safe_load(f) or {}
    retry_d = d.get("retry", {})
    return ProviderConfig(
        provider=d.get("provider", "anthropic"),
        model=d.get("model"),
        api_key=d.get("api_key"),
        base_url=d.get("base_url"),
        retry=RetryConfig(
            max_retries=retry_d.get("max_retries", 3),
            base_delay=retry_d.get("base_delay", 1.0),
            max_delay=retry_d.get("max_delay", 60.0),
            jitter=retry_d.get("jitter", True),
        ),
    )


def create_provider(config: ProviderConfig | None = None) -> LLMProvider:
    """Instantiate an LLMProvider from config or environment.

    Resolution order:
      1. Explicit ProviderConfig argument
      2. LLM_CONFIG_PATH env var → YAML file
      3. LLM_PROVIDER env var (defaults to ``anthropic``)
    """
    if config is None:
        yaml_path = os.environ.get("LLM_CONFIG_PATH")
        if yaml_path:
            config = _config_from_yaml(yaml_path)
        else:
            config = ProviderConfig(
                provider=os.environ.get("LLM_PROVIDER", "anthropic")
            )

    name = config.provider.lower()
    cls = _PROVIDERS.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown LLM provider: {name!r}. "
            f"Valid options: {sorted(_PROVIDERS)}"
        )
    return cls(config)
