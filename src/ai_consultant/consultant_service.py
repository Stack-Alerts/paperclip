"""
AI Consultant — ReAct Tool-Calling Agent Loop (P1.4)

Orchestrates LLM calls with DB query tools and signal catalog tools
via a ReAct-pattern loop (up to 10 iterations per turn), with
session management and automatic context summarization.

Usage:
    from ai_consultant.consultant_service import ConsultantService
    from ai_consultant.db.query_engine import QueryEngine
    from ai_consultant.signal_catalog import SignalCatalogService

    svc = ConsultantService(query_engine=QueryEngine())
    reply = asyncio.run(svc.chat("session-uuid", "How is strategy XYZ doing?"))
"""

from __future__ import annotations

import asyncio
import collections.abc
import dataclasses
import inspect
import json
import logging
import types as _types
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Union, get_args, get_origin

from ai_consultant.provider import ChatResponse, LLMProvider, ToolCall, create_provider

log = logging.getLogger(__name__)

_MAX_ITERATIONS = 10
_SUMMARIZE_AT = 0.80  # fraction of model token limit

_MODEL_TOKEN_LIMITS: dict[str, int] = {
    "claude-sonnet-4-6": 200_000,
    "claude-opus-4-7": 200_000,
    "claude-haiku-4-5": 200_000,
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "llama3": 8_192,
}
_DEFAULT_TOKEN_LIMIT = 100_000


# ── Session ───────────────────────────────────────────────────────────────────


@dataclass
class Session:
    session_id: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_cost: float = 0.0
    turn_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Session":
        return cls(**d)


# ── Tool schema helpers ───────────────────────────────────────────────────────


def _type_to_json_schema(annotation: Any) -> dict[str, Any]:
    origin = get_origin(annotation)
    args = get_args(annotation)

    if annotation is str:
        return {"type": "string"}
    if annotation is int:
        return {"type": "integer"}
    if annotation is float:
        return {"type": "number"}
    if annotation is bool:
        return {"type": "boolean"}

    # Optional[X] / Union[X, None]
    if origin is Union:
        non_none = [a for a in args if a is not type(None)]
        return _type_to_json_schema(non_none[0]) if non_none else {"type": "string"}

    # Python 3.10+ X | Y syntax
    if hasattr(_types, "UnionType") and isinstance(annotation, _types.UnionType):
        non_none = [a for a in args if a is not type(None)]
        return _type_to_json_schema(non_none[0]) if non_none else {"type": "string"}

    # list / List / Sequence[X]
    if origin in (list, collections.abc.Sequence):
        item = _type_to_json_schema(args[0]) if args else {"type": "string"}
        return {"type": "array", "items": item}

    return {"type": "string"}


def _build_tool_schema(name: str, fn: Callable, description: str = "") -> dict[str, Any]:
    """Generate a JSON Schema tool definition from a callable's type hints."""
    sig = inspect.signature(fn)
    from typing import get_type_hints
    try:
        hints: dict[str, Any] = get_type_hints(fn)
    except Exception:
        hints = {}

    properties: dict[str, Any] = {}
    required: list[str] = []

    for pname, param in sig.parameters.items():
        if pname in ("self", "cls"):
            continue
        annotation = hints.get(pname, Any)
        properties[pname] = _type_to_json_schema(annotation)
        if param.default is inspect.Parameter.empty:
            required.append(pname)

    doc_first_line = (fn.__doc__ or "").strip().split("\n")[0].strip()
    return {
        "name": name,
        "description": description or doc_first_line,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }


# ── Token estimation ──────────────────────────────────────────────────────────


def _estimate_tokens(messages: list[dict[str, Any]]) -> int:
    return sum(len(json.dumps(m)) for m in messages) // 4


def _result_to_str(result: Any) -> str:
    if dataclasses.is_dataclass(result) and not isinstance(result, type):
        return json.dumps(dataclasses.asdict(result), default=str)
    if isinstance(result, list):
        if result and dataclasses.is_dataclass(result[0]) and not isinstance(result[0], type):
            return json.dumps([dataclasses.asdict(x) for x in result], default=str)
        return json.dumps(result, default=str)
    if result is None:
        return "null"
    return str(result)


# ── ConsultantService ─────────────────────────────────────────────────────────


class ConsultantService:
    """
    ReAct-pattern LLM agent that orchestrates DB queries and signal catalog
    lookups to answer multi-turn trading strategy questions.
    """

    def __init__(
        self,
        provider: LLMProvider | None = None,
        query_engine: Any | None = None,   # QueryEngine (avoid hard import)
        catalog: Any | None = None,        # SignalCatalogService (avoid hard import)
        model_token_limit: int | None = None,
    ) -> None:
        self._provider = provider or create_provider()
        self._engine = query_engine
        self._catalog = catalog
        self._sessions: dict[str, Session] = {}
        self._model_limit = model_token_limit or self._detect_model_limit()
        self._tool_registry: dict[str, Callable] = {}
        self._tools: list[dict[str, Any]] = self._register_tools()
        self._system_prompt: str = self._build_system_prompt()

    # ── Public API ────────────────────────────────────────────────────────

    async def chat(self, session_id: str, message: str) -> str:
        """Run one user turn through the ReAct loop, return assistant reply."""
        session = self._get_or_create_session(session_id)
        session.messages.append({"role": "user", "content": message})

        for iteration in range(_MAX_ITERATIONS):
            messages_with_system = self._inject_system(session.messages)
            response: ChatResponse = await asyncio.to_thread(
                self._provider.chat, messages_with_system, self._tools or None
            )
            session.total_cost += self._provider.estimate_cost(
                response.prompt_tokens, response.completion_tokens
            )

            if not response.tool_calls:
                session.messages.append({"role": "assistant", "content": response.content})
                session.turn_count += 1
                log.info(
                    "session=%s turn=%d iterations=%d cost=$%.4f",
                    session_id[:8], session.turn_count, iteration + 1, session.total_cost,
                )
                return response.content

            # Append assistant message containing tool_use blocks
            session.messages.append(self._assistant_tool_msg(response))

            # Execute each tool call; errors become error results (no crash)
            tool_results: list[tuple[ToolCall, str]] = []
            for tc in response.tool_calls:
                result_str = await asyncio.to_thread(self._dispatch_tool, tc)
                tool_results.append((tc, result_str))
                log.debug("tool=%s result_len=%d", tc.name, len(result_str))

            # Anthropic expects all tool results in a single user message
            session.messages.append(self._tool_results_msg(tool_results))

            await self._maybe_summarize(session)

        # Max iterations hit — ask for a final answer without tools
        log.warning("session=%s hit max iterations (%d)", session_id[:8], _MAX_ITERATIONS)
        session.messages.append({
            "role": "user",
            "content": "Please summarise the information you have gathered and give your final answer.",
        })
        final: ChatResponse = await asyncio.to_thread(
            self._provider.chat, self._inject_system(session.messages)
        )
        session.messages.append({"role": "assistant", "content": final.content})
        session.turn_count += 1
        return final.content

    def new_session(self) -> str:
        """Create a new session and return its ID."""
        sid = str(uuid.uuid4())
        self._sessions[sid] = Session(session_id=sid)
        return sid

    def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def save_sessions(self, path: str | Path) -> None:
        """Persist all sessions to a JSON file."""
        data = {sid: s.to_dict() for sid, s in self._sessions.items()}
        Path(path).write_text(json.dumps(data, indent=2, default=str))
        log.info("Saved %d sessions to %s", len(self._sessions), path)

    def load_sessions(self, path: str | Path) -> None:
        """Load sessions from a JSON file produced by save_sessions()."""
        raw: dict[str, Any] = json.loads(Path(path).read_text())
        self._sessions = {sid: Session.from_dict(d) for sid, d in raw.items()}
        log.info("Loaded %d sessions from %s", len(self._sessions), path)

    # ── Session management ────────────────────────────────────────────────

    def _get_or_create_session(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id=session_id)
        return self._sessions[session_id]

    # ── System prompt ─────────────────────────────────────────────────────

    def _build_system_prompt(self) -> str:
        base = (
            "You are an AI consultant for a BTC algorithmic trading company. "
            "You help traders understand strategy performance, signal behaviour, and market conditions. "
            "Always query the available tools to obtain real data before making claims about specific "
            "strategies, signals, or portfolio metrics. "
            "When analysing strategies, always consider: Sharpe ratio, win rate, max drawdown, and profit factor. "
            "Be concise and quantitative in your answers."
        )
        if self._catalog is not None:
            try:
                catalog_ctx = self._catalog.context_string()
                return f"{base}\n\n{catalog_ctx}"
            except Exception as exc:
                log.warning("Could not get catalog context: %s", exc)
        return base

    def _inject_system(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{"role": "system", "content": self._system_prompt}] + messages

    # ── Tool registration ─────────────────────────────────────────────────

    def _register_tools(self) -> list[dict[str, Any]]:
        schemas: list[dict[str, Any]] = []

        if self._engine is not None:
            db_tools = [
                ("get_signal_stats", self._engine.get_signal_stats),
                ("get_strategy_performance", self._engine.get_strategy_performance),
                ("get_recent_trades", self._engine.get_recent_trades),
                ("get_open_positions", self._engine.get_open_positions),
                ("get_block_correlation", self._engine.get_block_correlation),
                ("get_market_regime", self._engine.get_market_regime),
                ("get_signal_coactivation", self._engine.get_signal_coactivation),
                ("get_portfolio_stats", self._engine.get_portfolio_stats),
                ("get_config_diff", self._engine.get_config_diff),
            ]
            for name, fn in db_tools:
                schemas.append(_build_tool_schema(name, fn))
                self._tool_registry[name] = fn

        if self._catalog is not None:
            catalog_tools = [
                ("search_signals", self._catalog.search,
                 "Search blocks and signals by keyword, category, or direction"),
                ("get_signal_info", self._catalog.get_signal_info,
                 "Return metadata and live stats for a specific signal name"),
                ("list_signals_by_type", self._catalog.list_signals_by_type,
                 "List all signals in a given category or direction (BULLISH/BEARISH/NEUTRAL)"),
            ]
            for name, fn, desc in catalog_tools:
                schemas.append(_build_tool_schema(name, fn, description=desc))
                self._tool_registry[name] = fn

        log.info("Registered %d tools: %s", len(schemas), [s["name"] for s in schemas])
        return schemas

    # ── Tool dispatch ─────────────────────────────────────────────────────

    def _dispatch_tool(self, tc: ToolCall) -> str:
        fn = self._tool_registry.get(tc.name)
        if fn is None:
            return json.dumps({"error": f"Unknown tool: {tc.name!r}"})
        try:
            result = fn(**tc.arguments)
            return _result_to_str(result)
        except Exception as exc:
            log.warning("Tool %s failed: %s", tc.name, exc)
            return json.dumps({"error": str(exc), "tool": tc.name})

    # ── Message builders (Anthropic format used in session history) ───────

    @staticmethod
    def _assistant_tool_msg(response: ChatResponse) -> dict[str, Any]:
        """Build an assistant message containing text + tool_use blocks."""
        content: list[dict[str, Any]] = []
        if response.content:
            content.append({"type": "text", "text": response.content})
        for tc in response.tool_calls:
            content.append({
                "type": "tool_use",
                "id": tc.id,
                "name": tc.name,
                "input": tc.arguments,
            })
        return {"role": "assistant", "content": content}

    @staticmethod
    def _tool_results_msg(results: list[tuple[ToolCall, str]]) -> dict[str, Any]:
        """Build a user message containing all tool_result blocks."""
        return {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": tc.id, "content": result_str}
                for tc, result_str in results
            ],
        }

    # ── Context summarization ─────────────────────────────────────────────

    async def _maybe_summarize(self, session: Session) -> None:
        token_estimate = _estimate_tokens(self._inject_system(session.messages))
        threshold = int(self._model_limit * _SUMMARIZE_AT)
        if token_estimate <= threshold:
            return

        log.info(
            "session=%s context at ~%d tokens (limit=%d), summarising",
            session.session_id[:8], token_estimate, self._model_limit,
        )

        # Keep the 6 most recent messages intact (≈3 turns); summarise the rest
        tail = session.messages[-6:]
        head = session.messages[:-6]

        if not head:
            return  # nothing to summarise

        summary_prompt = [
            {"role": "system", "content": "You are a precise summariser. Summarise the conversation below, preserving all factual data (numbers, strategy IDs, signal names, metrics)."},
            {"role": "user", "content": f"Conversation to summarise:\n\n{json.dumps(head, default=str)}\n\nProvide a concise factual summary."},
        ]
        summary_resp: ChatResponse = await asyncio.to_thread(
            self._provider.chat, summary_prompt
        )
        summary_msg = {"role": "user", "content": f"[Context summary from earlier in this conversation]\n{summary_resp.content}"}
        session.messages = [summary_msg] + tail
        log.info("session=%s context compressed to %d messages", session.session_id[:8], len(session.messages))

    # ── Model limit detection ─────────────────────────────────────────────

    def _detect_model_limit(self) -> int:
        model_name: str = getattr(self._provider, "_model", "") or ""
        for key, limit in _MODEL_TOKEN_LIMITS.items():
            if key in model_name:
                return limit
        return _DEFAULT_TOKEN_LIMIT
