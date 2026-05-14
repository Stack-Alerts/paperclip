"""Unit tests for ai_consultant.provider — all providers mocked, no network."""

from __future__ import annotations

import json
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from ai_consultant.provider import (
    AnthropicProvider,
    ChatResponse,
    DeepSeekProvider,
    OllamaProvider,
    OpenAIProvider,
    OpenRouterProvider,
    ProviderConfig,
    RetryConfig,
    ToolCall,
    create_provider,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_config(provider: str = "anthropic", **kwargs: Any) -> ProviderConfig:
    return ProviderConfig(provider=provider, api_key="test-key", **kwargs)


# ── Anthropic ─────────────────────────────────────────────────────────────────


class TestAnthropicProvider:
    def _mock_text_response(self, text: str = "Hello") -> MagicMock:
        block = MagicMock()
        block.type = "text"
        block.text = text

        resp = MagicMock()
        resp.content = [block]
        resp.usage.input_tokens = 10
        resp.usage.output_tokens = 5
        resp.model = "claude-sonnet-4-6"
        return resp

    def _mock_tool_response(
        self, tool_id: str, name: str, arguments: dict[str, Any]
    ) -> MagicMock:
        block = MagicMock()
        block.type = "tool_use"
        block.id = tool_id
        block.name = name
        block.input = arguments

        resp = MagicMock()
        resp.content = [block]
        resp.usage.input_tokens = 20
        resp.usage.output_tokens = 8
        resp.model = "claude-sonnet-4-6"
        return resp

    def test_chat_plain_text(self) -> None:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = self._mock_text_response("Hi there")

        with patch("anthropic.Anthropic", return_value=mock_client):
            p = AnthropicProvider(_make_config())
            result = p.chat([{"role": "user", "content": "Hello"}])

        assert isinstance(result, ChatResponse)
        assert result.content == "Hi there"
        assert result.tool_calls == []
        assert result.prompt_tokens == 10
        assert result.completion_tokens == 5
        assert result.model == "claude-sonnet-4-6"

    def test_chat_system_message_becomes_system_param(self) -> None:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = self._mock_text_response()

        with patch("anthropic.Anthropic", return_value=mock_client):
            p = AnthropicProvider(_make_config())
            p.chat(
                [
                    {"role": "system", "content": "You are a trading assistant."},
                    {"role": "user", "content": "Help me."},
                ]
            )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert "system" in call_kwargs
        system = call_kwargs["system"]
        assert len(system) == 1
        assert system[0]["type"] == "text"
        assert system[0]["text"] == "You are a trading assistant."
        # cache_control should be set on the last (only) system block
        assert system[0]["cache_control"] == {"type": "ephemeral"}
        # system message should not appear in messages list
        assert all(m["role"] != "system" for m in call_kwargs["messages"])

    def test_chat_prompt_caching_on_last_system_block(self) -> None:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = self._mock_text_response()

        with patch("anthropic.Anthropic", return_value=mock_client):
            p = AnthropicProvider(_make_config())
            p.chat(
                [
                    {"role": "system", "content": "Block A"},
                    {"role": "system", "content": "Block B"},
                    {"role": "user", "content": "Question"},
                ]
            )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        system = call_kwargs["system"]
        assert len(system) == 2
        assert "cache_control" not in system[0]
        assert system[1]["cache_control"] == {"type": "ephemeral"}

    def test_chat_tool_call(self) -> None:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = self._mock_tool_response(
            "toolu_01", "get_price", {"symbol": "BTC"}
        )

        tools = [
            {
                "name": "get_price",
                "description": "Get current price",
                "parameters": {
                    "type": "object",
                    "properties": {"symbol": {"type": "string"}},
                    "required": ["symbol"],
                },
            }
        ]

        with patch("anthropic.Anthropic", return_value=mock_client):
            p = AnthropicProvider(_make_config())
            result = p.chat([{"role": "user", "content": "Price?"}], tools=tools)

        assert len(result.tool_calls) == 1
        tc = result.tool_calls[0]
        assert tc.id == "toolu_01"
        assert tc.name == "get_price"
        assert tc.arguments == {"symbol": "BTC"}

        # Verify tool format passed to SDK uses input_schema
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["tools"][0]["input_schema"] == tools[0]["parameters"]

    def test_estimate_cost(self) -> None:
        with patch("anthropic.Anthropic", return_value=MagicMock()):
            p = AnthropicProvider(_make_config())
        cost = p.estimate_cost(1_000_000, 1_000_000)
        assert cost == pytest.approx(18.0)  # $3 input + $15 output

    def test_estimate_cost_zero_tokens(self) -> None:
        with patch("anthropic.Anthropic", return_value=MagicMock()):
            p = AnthropicProvider(_make_config())
        assert p.estimate_cost(0, 0) == 0.0


# ── OpenAI ────────────────────────────────────────────────────────────────────


class TestOpenAIProvider:
    def _mock_text_response(self, text: str = "Hello") -> MagicMock:
        msg = MagicMock()
        msg.content = text
        msg.tool_calls = None

        choice = MagicMock()
        choice.message = msg

        resp = MagicMock()
        resp.choices = [choice]
        resp.usage.prompt_tokens = 10
        resp.usage.completion_tokens = 5
        resp.model = "gpt-4o"
        return resp

    def _mock_tool_response(
        self, call_id: str, name: str, arguments: dict[str, Any]
    ) -> MagicMock:
        fn = MagicMock()
        fn.name = name
        fn.arguments = json.dumps(arguments)

        tc = MagicMock()
        tc.id = call_id
        tc.function = fn

        msg = MagicMock()
        msg.content = None
        msg.tool_calls = [tc]

        choice = MagicMock()
        choice.message = msg

        resp = MagicMock()
        resp.choices = [choice]
        resp.usage.prompt_tokens = 20
        resp.usage.completion_tokens = 10
        resp.model = "gpt-4o"
        return resp

    def test_chat_plain_text(self) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._mock_text_response(
            "Hi"
        )

        with patch("openai.OpenAI", return_value=mock_client):
            p = OpenAIProvider(_make_config("openai"))
            result = p.chat([{"role": "user", "content": "Hello"}])

        assert result.content == "Hi"
        assert result.tool_calls == []
        assert result.prompt_tokens == 10
        assert result.completion_tokens == 5
        assert result.model == "gpt-4o"

    def test_chat_tool_call(self) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._mock_tool_response(
            "call_abc", "get_price", {"symbol": "ETH"}
        )

        tools = [
            {
                "name": "get_price",
                "description": "Returns price",
                "parameters": {
                    "type": "object",
                    "properties": {"symbol": {"type": "string"}},
                },
            }
        ]

        with patch("openai.OpenAI", return_value=mock_client):
            p = OpenAIProvider(_make_config("openai"))
            result = p.chat([{"role": "user", "content": "ETH price?"}], tools=tools)

        assert len(result.tool_calls) == 1
        tc = result.tool_calls[0]
        assert tc.id == "call_abc"
        assert tc.name == "get_price"
        assert tc.arguments == {"symbol": "ETH"}

        # Verify SDK receives OpenAI function-calling format
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["tools"][0]["type"] == "function"
        assert call_kwargs["tools"][0]["function"]["name"] == "get_price"

    def test_system_message_passed_through(self) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._mock_text_response()

        with patch("openai.OpenAI", return_value=mock_client):
            p = OpenAIProvider(_make_config("openai"))
            messages = [
                {"role": "system", "content": "You are an assistant."},
                {"role": "user", "content": "Hi"},
            ]
            p.chat(messages)

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        # OpenAI accepts system as a regular message role
        assert call_kwargs["messages"][0]["role"] == "system"

    def test_estimate_cost(self) -> None:
        with patch("openai.OpenAI", return_value=MagicMock()):
            p = OpenAIProvider(_make_config("openai"))
        cost = p.estimate_cost(1_000_000, 1_000_000)
        assert cost == pytest.approx(20.0)  # $5 input + $15 output


# ── Ollama ────────────────────────────────────────────────────────────────────


class TestOllamaProvider:
    def _mock_http_client(
        self,
        content: str = "Hello",
        tool_calls: list[dict[str, Any]] | None = None,
        prompt_eval_count: int = 10,
        eval_count: int = 5,
    ) -> MagicMock:
        response_data: dict[str, Any] = {
            "message": {
                "role": "assistant",
                "content": content,
                "tool_calls": tool_calls or [],
            },
            "prompt_eval_count": prompt_eval_count,
            "eval_count": eval_count,
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = response_data
        mock_resp.raise_for_status.return_value = None

        mock_http = MagicMock()
        mock_http.post.return_value = mock_resp
        return mock_http

    def test_chat_plain_text(self) -> None:
        mock_http = self._mock_http_client("Ollama says hi")

        with patch("httpx.Client", return_value=mock_http):
            p = OllamaProvider(_make_config("ollama"))
            result = p.chat([{"role": "user", "content": "Hello"}])

        assert result.content == "Ollama says hi"
        assert result.tool_calls == []
        assert result.prompt_tokens == 10
        assert result.completion_tokens == 5

    def test_chat_posts_to_correct_endpoint(self) -> None:
        mock_http = self._mock_http_client()

        with patch("httpx.Client", return_value=mock_http):
            p = OllamaProvider(_make_config("ollama"))
            p.chat([{"role": "user", "content": "Hi"}])

        call = mock_http.post.call_args
        assert call.args[0] == "http://localhost:11434/api/chat"
        assert call.kwargs["json"]["stream"] is False

    def test_chat_custom_base_url(self) -> None:
        mock_http = self._mock_http_client()
        config = ProviderConfig(
            provider="ollama", base_url="http://myhost:11434", api_key=None
        )

        with patch("httpx.Client", return_value=mock_http):
            p = OllamaProvider(config)
            p.chat([{"role": "user", "content": "Hi"}])

        call = mock_http.post.call_args
        assert call.args[0].startswith("http://myhost:11434")

    def test_chat_tool_call(self) -> None:
        tool_calls = [
            {
                "id": "tc_1",
                "function": {"name": "query_db", "arguments": {"table": "trades"}},
            }
        ]
        mock_http = self._mock_http_client(tool_calls=tool_calls)

        tools = [
            {
                "name": "query_db",
                "description": "Query the database",
                "parameters": {
                    "type": "object",
                    "properties": {"table": {"type": "string"}},
                },
            }
        ]

        with patch("httpx.Client", return_value=mock_http):
            p = OllamaProvider(_make_config("ollama"))
            result = p.chat([{"role": "user", "content": "Query?"}], tools=tools)

        assert len(result.tool_calls) == 1
        tc = result.tool_calls[0]
        assert tc.id == "tc_1"
        assert tc.name == "query_db"
        assert tc.arguments == {"table": "trades"}

    def test_estimate_cost_always_zero(self) -> None:
        with patch("httpx.Client", return_value=MagicMock()):
            p = OllamaProvider(_make_config("ollama"))
        assert p.estimate_cost(999_999, 999_999) == 0.0


# ── Retry logic ───────────────────────────────────────────────────────────────


class TestRetryLogic:
    def test_succeeds_on_first_try(self) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = (
            _make_openai_text_response("ok")
        )

        with patch("openai.OpenAI", return_value=mock_client):
            p = OpenAIProvider(_make_config("openai"))
            result = p.chat([{"role": "user", "content": "Hi"}])

        assert result.content == "ok"
        assert mock_client.chat.completions.create.call_count == 1

    def test_retries_on_transient_failure(self) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            RuntimeError("timeout"),
            _make_openai_text_response("recovered"),
        ]

        config = ProviderConfig(
            provider="openai",
            api_key="test",
            retry=RetryConfig(max_retries=3, base_delay=0.001, jitter=False),
        )
        with patch("openai.OpenAI", return_value=mock_client):
            p = OpenAIProvider(config)
            result = p.chat([{"role": "user", "content": "Hi"}])

        assert result.content == "recovered"
        assert mock_client.chat.completions.create.call_count == 2

    def test_raises_after_max_retries(self) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("always fails")

        config = ProviderConfig(
            provider="openai",
            api_key="test",
            retry=RetryConfig(max_retries=2, base_delay=0.001, jitter=False),
        )
        with patch("openai.OpenAI", return_value=mock_client):
            p = OpenAIProvider(config)
            with pytest.raises(RuntimeError, match="always fails"):
                p.chat([{"role": "user", "content": "Hi"}])

        assert mock_client.chat.completions.create.call_count == 3  # 1 + 2 retries


# ── Factory ───────────────────────────────────────────────────────────────────


class TestCreateProvider:
    def test_default_is_anthropic(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        monkeypatch.delenv("LLM_CONFIG_PATH", raising=False)

        with patch("anthropic.Anthropic", return_value=MagicMock()):
            p = create_provider()
        assert isinstance(p, AnthropicProvider)

    def test_env_var_selects_openai(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.delenv("LLM_CONFIG_PATH", raising=False)

        with patch("openai.OpenAI", return_value=MagicMock()):
            p = create_provider()
        assert isinstance(p, OpenAIProvider)

    def test_env_var_selects_ollama(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        monkeypatch.delenv("LLM_CONFIG_PATH", raising=False)

        with patch("httpx.Client", return_value=MagicMock()):
            p = create_provider()
        assert isinstance(p, OllamaProvider)

    def test_explicit_config_overrides_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "openai")

        with patch("anthropic.Anthropic", return_value=MagicMock()):
            p = create_provider(ProviderConfig(provider="anthropic", api_key="k"))
        assert isinstance(p, AnthropicProvider)

    def test_yaml_config(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
    ) -> None:
        cfg_file = tmp_path / "llm.yaml"
        cfg_file.write_text("provider: ollama\nbase_url: http://local:11434\n")

        monkeypatch.setenv("LLM_CONFIG_PATH", str(cfg_file))
        monkeypatch.delenv("LLM_PROVIDER", raising=False)

        with patch("httpx.Client", return_value=MagicMock()):
            p = create_provider()
        assert isinstance(p, OllamaProvider)
        assert p._base_url == "http://local:11434"

    def test_unknown_provider_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            create_provider(ProviderConfig(provider="groq"))


# ── Shared helpers ────────────────────────────────────────────────────────────


def _make_openai_text_response(text: str) -> MagicMock:
    msg = MagicMock()
    msg.content = text
    msg.tool_calls = None

    choice = MagicMock()
    choice.message = msg

    resp = MagicMock()
    resp.choices = [choice]
    resp.usage.prompt_tokens = 5
    resp.usage.completion_tokens = 3
    resp.model = "gpt-4o"
    return resp


# ── DeepSeek ──────────────────────────────────────────────────────────────────


class TestDeepSeekProvider:
    def _mock_text_response(self, text: str = "Hello") -> MagicMock:
        msg = MagicMock()
        msg.content = text
        msg.tool_calls = None
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]
        resp.usage.prompt_tokens = 10
        resp.usage.completion_tokens = 5
        resp.model = "deepseek-v4-pro"
        return resp

    def test_chat_plain_text(self) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._mock_text_response("Hi")
        with patch("openai.OpenAI", return_value=mock_client):
            p = DeepSeekProvider(_make_config("deepseek"))
            result = p.chat([{"role": "user", "content": "Hello"}])
        assert result.content == "Hi"
        assert result.model == "deepseek-v4-pro"

    def test_estimate_cost_flash(self) -> None:
        with patch("openai.OpenAI", return_value=MagicMock()):
            p = DeepSeekProvider(
                ProviderConfig(provider="deepseek", model="deepseek-v4-flash", api_key="k")
            )
        cost = p.estimate_cost(1_000_000, 1_000_000)
        assert cost == pytest.approx(1.30)  # $0.20 input + $1.10 output

    def test_estimate_cost_pro(self) -> None:
        with patch("openai.OpenAI", return_value=MagicMock()):
            p = DeepSeekProvider(
                ProviderConfig(provider="deepseek", model="deepseek-v4-pro", api_key="k")
            )
        cost = p.estimate_cost(1_000_000, 1_000_000)
        assert cost == pytest.approx(2.74)  # $0.55 input + $2.19 output

    def test_estimate_cost_default_is_pro(self) -> None:
        with patch("openai.OpenAI", return_value=MagicMock()):
            p = DeepSeekProvider(_make_config("deepseek"))
        cost = p.estimate_cost(1_000_000, 0)
        assert cost == pytest.approx(0.55)

    def test_default_base_url(self) -> None:
        with patch("openai.OpenAI", return_value=MagicMock()):
            p = DeepSeekProvider(_make_config("deepseek"))
        assert p._DEFAULT_BASE_URL == "https://api.deepseek.com/v1"


# ── OpenRouter ────────────────────────────────────────────────────────────────


class TestOpenRouterProvider:
    def _mock_text_response(self, text: str = "Hello") -> MagicMock:
        msg = MagicMock()
        msg.content = text
        msg.tool_calls = None
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]
        resp.usage.prompt_tokens = 10
        resp.usage.completion_tokens = 5
        resp.model = "deepseek/deepseek-v4-pro"
        return resp

    def test_chat_plain_text(self) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._mock_text_response("Hi")
        with patch("openai.OpenAI", return_value=mock_client):
            p = OpenRouterProvider(_make_config("openrouter"))
            result = p.chat([{"role": "user", "content": "Hello"}])
        assert result.content == "Hi"

    def test_estimate_cost(self) -> None:
        with patch("openai.OpenAI", return_value=MagicMock()):
            p = OpenRouterProvider(_make_config("openrouter"))
        cost = p.estimate_cost(1_000_000, 1_000_000)
        assert cost == pytest.approx(2.74)  # $0.55 input + $2.19 output

    def test_default_base_url(self) -> None:
        with patch("openai.OpenAI", return_value=MagicMock()):
            p = OpenRouterProvider(_make_config("openrouter"))
        assert p._DEFAULT_BASE_URL == "https://openrouter.ai/api/v1"


# ── Factory (updated) ─────────────────────────────────────────────────────────


class TestCreateProviderExtended:
    def test_env_var_selects_deepseek(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "deepseek")
        monkeypatch.delenv("LLM_CONFIG_PATH", raising=False)
        with patch("openai.OpenAI", return_value=MagicMock()):
            p = create_provider()
        assert isinstance(p, DeepSeekProvider)

    def test_env_var_selects_openrouter(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "openrouter")
        monkeypatch.delenv("LLM_CONFIG_PATH", raising=False)
        with patch("openai.OpenAI", return_value=MagicMock()):
            p = create_provider()
        assert isinstance(p, OpenRouterProvider)


# ── Cost tracker helpers ──────────────────────────────────────────────────────


class TestCostTrackerHelpers:
    def test_classify_anthropic(self) -> None:
        from ai_consultant.cost_tracker import _classify_provider
        assert _classify_provider("claude-sonnet-4-6") == "Anthropic"
        assert _classify_provider("claude-opus-4") == "Anthropic"

    def test_classify_openai(self) -> None:
        from ai_consultant.cost_tracker import _classify_provider
        assert _classify_provider("gpt-4o") == "OpenAI"
        assert _classify_provider("gpt-4-turbo") == "OpenAI"

    def test_classify_deepseek(self) -> None:
        from ai_consultant.cost_tracker import _classify_provider
        assert _classify_provider("deepseek-v4-flash") == "DeepSeek"
        assert _classify_provider("deepseek-v4-pro") == "DeepSeek"
        assert _classify_provider("deepseek/deepseek-v4-pro") == "DeepSeek"

    def test_classify_openrouter_fallback(self) -> None:
        from ai_consultant.cost_tracker import _classify_provider
        assert _classify_provider("some-future-model") == "OpenRouter"

    def test_estimate_cost_anthropic(self) -> None:
        from ai_consultant.cost_tracker import _estimate_cost
        cost = _estimate_cost("Anthropic", "claude-sonnet-4-6", 1_000_000, 1_000_000)
        assert cost == pytest.approx(18.0)  # $3 input + $15 output

    def test_estimate_cost_deepseek_flash(self) -> None:
        from ai_consultant.cost_tracker import _estimate_cost
        cost = _estimate_cost("DeepSeek", "deepseek-v4-flash", 1_000_000, 1_000_000)
        assert cost == pytest.approx(1.30)  # $0.20 input + $1.10 output

    def test_estimate_cost_deepseek_pro(self) -> None:
        from ai_consultant.cost_tracker import _estimate_cost
        cost = _estimate_cost("DeepSeek", "deepseek-v4-pro", 1_000_000, 1_000_000)
        assert cost == pytest.approx(2.74)  # $0.55 input + $2.19 output
