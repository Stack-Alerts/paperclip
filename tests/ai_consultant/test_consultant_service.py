"""
Unit tests for ConsultantService (P1.4).

All LLM calls and DB interactions are mocked — no network or DB required.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest
from typing import List, Optional, Sequence

from ai_consultant.consultant_service import (
    ConsultantService,
    Session,
    _build_tool_schema,
    _estimate_tokens,
    _result_to_str,
    _type_to_json_schema,
)
from ai_consultant.provider import ChatResponse, LLMProvider, ProviderConfig, ToolCall


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_response(content: str = "", tool_calls: list[ToolCall] | None = None) -> ChatResponse:
    return ChatResponse(
        content=content,
        tool_calls=tool_calls or [],
        prompt_tokens=100,
        completion_tokens=50,
        model="test-model",
    )


class _MockProvider(LLMProvider):
    """Provider that returns a preset sequence of responses."""

    def __init__(self, responses: list[ChatResponse]) -> None:
        super().__init__(ProviderConfig(provider="anthropic"))
        self._responses = list(responses)
        self._calls: list[tuple] = []

    def chat(self, messages, tools=None) -> ChatResponse:
        self._calls.append((messages, tools))
        if self._responses:
            return self._responses.pop(0)
        return _make_response("(no more responses)")

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return 0.001


def _make_service(responses: list[ChatResponse], **kwargs) -> ConsultantService:
    provider = _MockProvider(responses)
    return ConsultantService(provider=provider, **kwargs)


# ── Type conversion ───────────────────────────────────────────────────────────


class TestTypeToJsonSchema:
    def test_primitives(self):
        assert _type_to_json_schema(str) == {"type": "string"}
        assert _type_to_json_schema(int) == {"type": "integer"}
        assert _type_to_json_schema(float) == {"type": "number"}
        assert _type_to_json_schema(bool) == {"type": "boolean"}

    def test_optional(self):
        assert _type_to_json_schema(Optional[str]) == {"type": "string"}
        assert _type_to_json_schema(Optional[int]) == {"type": "integer"}

    def test_list(self):
        assert _type_to_json_schema(List[str]) == {"type": "array", "items": {"type": "string"}}
        assert _type_to_json_schema(list[int]) == {"type": "array", "items": {"type": "integer"}}

    def test_sequence(self):
        result = _type_to_json_schema(Sequence[str])
        assert result == {"type": "array", "items": {"type": "string"}}


# ── Tool schema generation ────────────────────────────────────────────────────


class TestBuildToolSchema:
    def test_simple_function(self):
        def my_tool(signal_id: str, lookback_days: int) -> dict:
            """Get signal stats."""

        schema = _build_tool_schema("my_tool", my_tool)
        assert schema["name"] == "my_tool"
        assert schema["parameters"]["properties"]["signal_id"] == {"type": "string"}
        assert schema["parameters"]["properties"]["lookback_days"] == {"type": "integer"}
        assert "signal_id" in schema["parameters"]["required"]
        assert "lookback_days" in schema["parameters"]["required"]

    def test_optional_param_not_required(self):
        def my_tool(strategy_id: str, period: str = "latest") -> dict:
            """Get performance."""

        schema = _build_tool_schema("my_tool", my_tool)
        assert "strategy_id" in schema["parameters"]["required"]
        assert "period" not in schema["parameters"]["required"]

    def test_custom_description_overrides_docstring(self):
        def my_tool(x: str) -> str:
            """Original docstring."""

        schema = _build_tool_schema("my_tool", my_tool, description="Custom description")
        assert schema["description"] == "Custom description"

    def test_sequence_param(self):
        def my_tool(block_ids: Sequence[str]) -> list:
            """Correlate blocks."""

        schema = _build_tool_schema("my_tool", my_tool)
        prop = schema["parameters"]["properties"]["block_ids"]
        assert prop["type"] == "array"
        assert prop["items"]["type"] == "string"


# ── Token estimation ──────────────────────────────────────────────────────────


class TestEstimateTokens:
    def test_non_zero_for_nonempty_messages(self):
        msgs = [{"role": "user", "content": "Hello world, how are you today?"}]
        assert _estimate_tokens(msgs) > 0

    def test_longer_content_more_tokens(self):
        short = [{"role": "user", "content": "Hi"}]
        long = [{"role": "user", "content": "Hi " * 200}]
        assert _estimate_tokens(long) > _estimate_tokens(short)


# ── Result serialisation ──────────────────────────────────────────────────────


class TestResultToStr:
    def test_string(self):
        assert _result_to_str("hello") == "hello"

    def test_none(self):
        assert _result_to_str(None) == "null"

    def test_dataclass(self):
        @dataclass
        class Foo:
            x: int
            y: str

        result = _result_to_str(Foo(x=1, y="a"))
        d = json.loads(result)
        assert d["x"] == 1
        assert d["y"] == "a"

    def test_list_of_dataclasses(self):
        @dataclass
        class Bar:
            n: int

        result = _result_to_str([Bar(1), Bar(2)])
        lst = json.loads(result)
        assert lst[0]["n"] == 1
        assert lst[1]["n"] == 2


# ── Session ───────────────────────────────────────────────────────────────────


class TestSession:
    def test_round_trip(self):
        s = Session(session_id="abc-123", total_cost=0.5, turn_count=3)
        s.messages.append({"role": "user", "content": "hi"})
        restored = Session.from_dict(s.to_dict())
        assert restored.session_id == "abc-123"
        assert restored.total_cost == 0.5
        assert restored.turn_count == 3
        assert restored.messages[0]["content"] == "hi"


# ── ConsultantService.chat ────────────────────────────────────────────────────


class TestConsultantServiceChat:
    def test_simple_reply_no_tools(self):
        svc = _make_service([_make_response("The strategy looks good.")])
        reply = asyncio.run(svc.chat("session-1", "How is strategy X?"))
        assert reply == "The strategy looks good."

    def test_session_created_on_first_chat(self):
        svc = _make_service([_make_response("Hi!")])
        asyncio.run(svc.chat("new-session", "Hello"))
        assert "new-session" in svc._sessions
        s = svc._sessions["new-session"]
        assert s.turn_count == 1
        assert len(s.messages) == 2  # user + assistant

    def test_react_loop_single_tool_call(self):
        tc = ToolCall(id="tc-1", name="fake_tool", arguments={"x": "y"})
        responses = [
            _make_response("Checking...", tool_calls=[tc]),
            _make_response("Done! The result is 42."),
        ]
        mock_tool = MagicMock(return_value="42")
        svc = _make_service(responses)
        svc._tool_registry["fake_tool"] = mock_tool
        svc._tools = [_build_tool_schema("fake_tool", lambda x: None)]

        reply = asyncio.run(svc.chat("s1", "What is the answer?"))

        mock_tool.assert_called_once_with(x="y")
        assert reply == "Done! The result is 42."
        session = svc._sessions["s1"]
        # messages: user, assistant(tool_use), user(tool_result), assistant
        assert len(session.messages) == 4

    def test_tool_error_returned_as_result_not_crash(self):
        tc = ToolCall(id="tc-err", name="boom_tool", arguments={})
        responses = [
            _make_response("Calling boom...", tool_calls=[tc]),
            _make_response("I encountered an error but here's what I know."),
        ]
        svc = _make_service(responses)
        svc._tool_registry["boom_tool"] = MagicMock(side_effect=RuntimeError("db down"))
        svc._tools = []

        reply = asyncio.run(svc.chat("s-err", "Explode!"))
        # Must not raise; error surfaced as tool result
        assert "error" not in reply.lower() or "encountered" in reply.lower()
        # Verify the tool result message has the error JSON
        session = svc._sessions["s-err"]
        tool_result_msg = session.messages[2]
        assert tool_result_msg["role"] == "user"
        result_content = tool_result_msg["content"][0]["content"]
        parsed = json.loads(result_content)
        assert parsed["error"] == "db down"

    def test_multi_tool_calls_grouped_in_single_user_message(self):
        tc1 = ToolCall(id="tc-a", name="tool_a", arguments={"k": "v1"})
        tc2 = ToolCall(id="tc-b", name="tool_b", arguments={"k": "v2"})
        responses = [
            _make_response("Calling both...", tool_calls=[tc1, tc2]),
            _make_response("Final answer."),
        ]
        svc = _make_service(responses)
        svc._tool_registry["tool_a"] = MagicMock(return_value="result_a")
        svc._tool_registry["tool_b"] = MagicMock(return_value="result_b")

        asyncio.run(svc.chat("multi", "Call both tools"))

        session = svc._sessions["multi"]
        # messages: user, assistant(2 tool_use), user(2 tool_result), assistant
        tool_result_msg = session.messages[2]
        assert tool_result_msg["role"] == "user"
        assert len(tool_result_msg["content"]) == 2

    def test_max_iterations_causes_final_summary_call(self):
        from ai_consultant.consultant_service import _MAX_ITERATIONS

        tc = ToolCall(id="tc-loop", name="looping_tool", arguments={})
        # Always return tool call → triggers max iterations
        loop_response = _make_response("Still checking...", tool_calls=[tc])
        final_response = _make_response("Here is the summary.")
        responses = [loop_response] * _MAX_ITERATIONS + [final_response]
        svc = _make_service(responses)
        svc._tool_registry["looping_tool"] = MagicMock(return_value="data")

        reply = asyncio.run(svc.chat("loop-session", "Keep calling tools"))
        assert reply == "Here is the summary."

    def test_cost_accumulated_across_turns(self):
        responses = [
            _make_response("Turn 1"),
            _make_response("Turn 2"),
        ]
        svc = _make_service(responses)
        asyncio.run(svc.chat("cost-session", "First"))
        asyncio.run(svc.chat("cost-session", "Second"))
        assert svc._sessions["cost-session"].total_cost > 0

    def test_new_session_creates_unique_ids(self):
        svc = _make_service([])
        id1 = svc.new_session()
        id2 = svc.new_session()
        assert id1 != id2

    def test_get_session_returns_none_for_unknown(self):
        svc = _make_service([])
        assert svc.get_session("does-not-exist") is None


# ── Tool registration ─────────────────────────────────────────────────────────


class TestToolRegistration:
    def test_no_tools_without_engine_or_catalog(self):
        svc = _make_service([])
        assert svc._tools == []
        assert svc._tool_registry == {}

    def test_db_tools_registered_when_engine_present(self):
        mock_engine = MagicMock()

        def _stub_method(x: str, y: int) -> str:
            """Stub method."""

        # Give each attribute a callable with a proper signature
        for name in [
            "get_signal_stats", "get_strategy_performance", "get_recent_trades",
            "get_open_positions", "get_block_correlation", "get_market_regime",
            "get_signal_coactivation", "get_portfolio_stats", "get_config_diff",
        ]:
            setattr(mock_engine, name, _stub_method)

        svc = _make_service([], query_engine=mock_engine)
        tool_names = {t["name"] for t in svc._tools}
        assert "get_signal_stats" in tool_names
        assert "get_portfolio_stats" in tool_names
        assert len(tool_names) == 9

    def test_catalog_tools_registered_when_catalog_present(self):
        mock_catalog = MagicMock()

        def _search(query: str) -> list:
            """Search."""

        def _get_info(signal_name: str) -> dict:
            """Info."""

        def _list_by_type(signal_type: str) -> list:
            """List."""

        mock_catalog.search = _search
        mock_catalog.get_signal_info = _get_info
        mock_catalog.list_signals_by_type = _list_by_type
        mock_catalog.context_string.return_value = ""

        svc = _make_service([], catalog=mock_catalog)
        tool_names = {t["name"] for t in svc._tools}
        assert "search_signals" in tool_names
        assert "get_signal_info" in tool_names
        assert "list_signals_by_type" in tool_names


# ── Session persistence ───────────────────────────────────────────────────────


class TestSessionPersistence:
    def test_save_and_load_roundtrip(self, tmp_path):
        svc = _make_service([_make_response("Hi")])
        asyncio.run(svc.chat("persist-session", "Hello"))

        out = tmp_path / "sessions.json"
        svc.save_sessions(out)

        svc2 = _make_service([])
        svc2.load_sessions(out)
        assert "persist-session" in svc2._sessions
        restored = svc2._sessions["persist-session"]
        assert restored.turn_count == 1
        assert any(m["role"] == "user" and m["content"] == "Hello" for m in restored.messages)


# ── System prompt ─────────────────────────────────────────────────────────────


class TestSystemPrompt:
    def test_system_message_injected_on_each_call(self):
        provider = _MockProvider([_make_response("ok")])
        svc = ConsultantService(provider=provider)
        asyncio.run(svc.chat("s", "Hello"))
        messages, _ = provider._calls[0]
        assert messages[0]["role"] == "system"
        assert len(messages[0]["content"]) > 0

    def test_catalog_context_appended_to_system_prompt(self):
        mock_catalog = MagicMock()
        mock_catalog.context_string.return_value = "=== CATALOG CONTEXT ==="
        provider = _MockProvider([_make_response("ok")])
        svc = ConsultantService(provider=provider, catalog=mock_catalog)
        assert "CATALOG CONTEXT" in svc._system_prompt


# ── Provider message adaptation ───────────────────────────────────────────────


class TestOpenAIProviderAdaptMessages:
    def test_converts_anthropic_tool_use_to_openai(self):
        from ai_consultant.provider import OpenAIProvider

        messages = [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Calling tool"},
                    {"type": "tool_use", "id": "tu-1", "name": "my_tool", "input": {"x": 1}},
                ],
            }
        ]
        adapted = OpenAIProvider._adapt_messages(messages)
        assert len(adapted) == 1
        msg = adapted[0]
        assert msg["role"] == "assistant"
        assert msg["tool_calls"][0]["id"] == "tu-1"
        assert msg["tool_calls"][0]["function"]["name"] == "my_tool"
        assert json.loads(msg["tool_calls"][0]["function"]["arguments"]) == {"x": 1}

    def test_converts_anthropic_tool_result_to_openai(self):
        from ai_consultant.provider import OpenAIProvider

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "tu-1", "content": "42"},
                    {"type": "tool_result", "tool_use_id": "tu-2", "content": "99"},
                ],
            }
        ]
        adapted = OpenAIProvider._adapt_messages(messages)
        assert len(adapted) == 2
        assert adapted[0]["role"] == "tool"
        assert adapted[0]["tool_call_id"] == "tu-1"
        assert adapted[0]["content"] == "42"
        assert adapted[1]["tool_call_id"] == "tu-2"

    def test_passthrough_for_regular_messages(self):
        from ai_consultant.provider import OpenAIProvider

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        adapted = OpenAIProvider._adapt_messages(messages)
        assert adapted == messages
