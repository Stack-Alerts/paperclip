"""
AuditWriter — dual-write audit log for AI Consultant activity.

Primary: PostgreSQL ai_consultant_audit table (via asyncpg).
Backup:  ~/.btc_trade_engine/audit/ai_consultant.jsonl (append-only, asyncio.Lock).

Write failures are logged to stderr and never propagate to callers.
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Optional

try:
    import asyncpg
    _HAS_ASYNCPG = True
except ImportError:
    _HAS_ASYNCPG = False


class AuditEventType(str, Enum):
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    TOOL_CALL = "tool_call"
    LLM_CALL = "llm_call"
    PROPOSAL_GENERATED = "proposal_generated"
    PROPOSAL_APPROVED = "proposal_approved"
    PROPOSAL_REJECTED = "proposal_rejected"
    CHANGE_APPLIED = "change_applied"
    ROLLBACK_EXECUTED = "rollback_executed"


_JSONL_PATH = Path.home() / ".btc_trade_engine" / "audit" / "ai_consultant.jsonl"

_INSERT_SQL = """
INSERT INTO ai_consultant_audit
    (id, session_id, event_type, timestamp, user_id, strategy_id, payload, token_cost_usd)
VALUES
    ($1, $2, $3, $4, $5, $6, $7, $8)
"""


def _get_db_url() -> Optional[str]:
    """Build asyncpg DSN from environment, return None if not configured."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "optimizer_v3")
    user = os.getenv("POSTGRES_USER", "optimizer_admin")
    password = os.getenv("POSTGRES_PASSWORD", "")
    if not password:
        return None
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


class AuditWriter:
    """
    Async audit log writer for AI Consultant events.

    Usage:
        writer = AuditWriter(session_id=uuid.uuid4())
        await writer.open()
        await writer.log(AuditEventType.SESSION_START, {"model": "claude-3-5-sonnet"})
        await writer.close()

    Or as an async context manager:
        async with AuditWriter(session_id=...) as writer:
            await writer.log(...)
    """

    def __init__(
        self,
        session_id: Optional[uuid.UUID] = None,
        db_url: Optional[str] = None,
        jsonl_path: Optional[Path] = None,
    ) -> None:
        self.session_id: uuid.UUID = session_id or uuid.uuid4()
        self._db_url: Optional[str] = db_url or _get_db_url()
        self._jsonl_path: Path = jsonl_path or _JSONL_PATH
        self._pool: Optional[Any] = None  # asyncpg.Pool
        self._jsonl_lock = asyncio.Lock()

    async def open(self) -> None:
        """Initialise DB pool and ensure JSONL directory exists."""
        if _HAS_ASYNCPG and self._db_url:
            try:
                self._pool = await asyncpg.create_pool(self._db_url, min_size=1, max_size=3)
            except Exception as exc:
                print(f"[AuditWriter] DB pool creation failed: {exc}", file=sys.stderr)  # noqa: T201
                self._pool = None
        self._jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    async def close(self) -> None:
        if self._pool is not None:
            try:
                await self._pool.close()
            except Exception as exc:
                print(f"[AuditWriter] DB pool close error: {exc}", file=sys.stderr)  # noqa: T201
            self._pool = None

    async def __aenter__(self) -> "AuditWriter":
        await self.open()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def log(
        self,
        event_type: AuditEventType | str,
        payload: dict[str, Any],
        *,
        user_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        token_cost_usd: Optional[Decimal] = None,
    ) -> None:
        """
        Write an audit event.  Never raises; errors go to stderr.
        """
        event_id = uuid.uuid4()
        ts = datetime.now(timezone.utc)
        event_type_str = event_type.value if isinstance(event_type, AuditEventType) else str(event_type)

        record = {
            "id": str(event_id),
            "session_id": str(self.session_id),
            "event_type": event_type_str,
            "timestamp": ts.isoformat(),
            "user_id": user_id,
            "strategy_id": strategy_id,
            "payload": payload,
            "token_cost_usd": str(token_cost_usd) if token_cost_usd is not None else None,
        }

        await asyncio.gather(
            self._write_db(event_id, ts, event_type_str, payload, user_id, strategy_id, token_cost_usd),
            self._write_jsonl(record),
            return_exceptions=True,
        )

    async def _write_db(
        self,
        event_id: uuid.UUID,
        ts: datetime,
        event_type: str,
        payload: dict[str, Any],
        user_id: Optional[str],
        strategy_id: Optional[str],
        token_cost_usd: Optional[Decimal],
    ) -> None:
        if self._pool is None:
            return
        try:
            payload_json = json.dumps(payload)
            async with self._pool.acquire() as conn:
                await conn.execute(
                    _INSERT_SQL,
                    event_id,
                    self.session_id,
                    event_type,
                    ts,
                    user_id,
                    strategy_id,
                    payload_json,
                    token_cost_usd,
                )
        except Exception as exc:
            print(f"[AuditWriter] DB write failed ({event_type}): {exc}", file=sys.stderr)  # noqa: T201

    async def _write_jsonl(self, record: dict[str, Any]) -> None:
        try:
            line = json.dumps(record, ensure_ascii=False) + "\n"
            async with self._jsonl_lock:
                await asyncio.get_event_loop().run_in_executor(
                    None, self._append_line, line
                )
        except Exception as exc:
            print(f"[AuditWriter] JSONL write failed: {exc}", file=sys.stderr)  # noqa: T201

    def _append_line(self, line: str) -> None:
        with open(self._jsonl_path, "a", encoding="utf-8") as fh:
            fh.write(line)

    # ------------------------------------------------------------------
    # Convenience helpers for typed events
    # ------------------------------------------------------------------

    async def log_session_start(self, model: str, **extra: Any) -> None:
        await self.log(AuditEventType.SESSION_START, {"model": model, **extra})

    async def log_session_end(self, reason: str = "normal", **extra: Any) -> None:
        await self.log(AuditEventType.SESSION_END, {"reason": reason, **extra})

    async def log_tool_call(
        self,
        tool_name: str,
        args: dict[str, Any],
        result_summary: str,
        latency_ms: float,
        **extra: Any,
    ) -> None:
        await self.log(
            AuditEventType.TOOL_CALL,
            {
                "tool_name": tool_name,
                "args": args,
                "result_summary": result_summary,
                "latency_ms": latency_ms,
                **extra,
            },
        )

    async def log_llm_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: Decimal,
        **extra: Any,
    ) -> None:
        await self.log(
            AuditEventType.LLM_CALL,
            {
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                **extra,
            },
            token_cost_usd=cost_usd,
        )

    async def log_proposal_generated(
        self, diff_summary: str, strategy_id: str, **extra: Any
    ) -> None:
        await self.log(
            AuditEventType.PROPOSAL_GENERATED,
            {"diff_summary": diff_summary, **extra},
            strategy_id=strategy_id,
        )

    async def log_proposal_approved(
        self, user_id: str, strategy_id: str, **extra: Any
    ) -> None:
        await self.log(
            AuditEventType.PROPOSAL_APPROVED,
            extra,
            user_id=user_id,
            strategy_id=strategy_id,
        )

    async def log_proposal_rejected(
        self, user_id: str, reason: str, strategy_id: str, **extra: Any
    ) -> None:
        await self.log(
            AuditEventType.PROPOSAL_REJECTED,
            {"reason": reason, **extra},
            user_id=user_id,
            strategy_id=strategy_id,
        )

    async def log_change_applied(
        self, diff: str, strategy_id: str, snapshot_path: str, **extra: Any
    ) -> None:
        await self.log(
            AuditEventType.CHANGE_APPLIED,
            {"diff": diff, "snapshot_path": snapshot_path, **extra},
            strategy_id=strategy_id,
        )

    async def log_rollback_executed(
        self, snapshot_path: str, strategy_id: str, **extra: Any
    ) -> None:
        await self.log(
            AuditEventType.ROLLBACK_EXECUTED,
            {"snapshot_path": snapshot_path, **extra},
            strategy_id=strategy_id,
        )
