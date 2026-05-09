"""
Integration tests for AuditWriter (P1.5).

Tests run without a live PostgreSQL instance — the DB pool is not opened.
JSONL writes are redirected to a tmp directory for isolation.
All event types must write successfully and produce valid, parseable JSONL.
"""

import asyncio
import json
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

pytestmark = pytest.mark.anyio

from ai_consultant.audit_writer import AuditWriter, AuditEventType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_writer(tmp_path: Path) -> AuditWriter:
    jsonl = tmp_path / "audit" / "ai_consultant.jsonl"
    return AuditWriter(
        session_id=uuid.UUID("aaaabbbb-0000-0000-0000-000000000001"),
        db_url=None,          # no DB in unit/integration tests without Postgres
        jsonl_path=jsonl,
    )


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_session_start(tmp_path):
    async with make_writer(tmp_path) as w:
        await w.log_session_start(model="claude-3-5-sonnet-20241022")

    records = read_jsonl(tmp_path / "audit" / "ai_consultant.jsonl")
    assert len(records) == 1
    r = records[0]
    assert r["event_type"] == AuditEventType.SESSION_START
    assert r["payload"]["model"] == "claude-3-5-sonnet-20241022"
    assert r["session_id"] == "aaaabbbb-0000-0000-0000-000000000001"


@pytest.mark.anyio
async def test_session_end(tmp_path):
    async with make_writer(tmp_path) as w:
        await w.log_session_end(reason="user_exit")

    records = read_jsonl(tmp_path / "audit" / "ai_consultant.jsonl")
    assert records[0]["event_type"] == AuditEventType.SESSION_END
    assert records[0]["payload"]["reason"] == "user_exit"


@pytest.mark.anyio
async def test_tool_call(tmp_path):
    async with make_writer(tmp_path) as w:
        await w.log_tool_call(
            tool_name="read_strategy",
            args={"strategy_id": "s1"},
            result_summary="Returned 412 bytes",
            latency_ms=34.7,
        )

    r = read_jsonl(tmp_path / "audit" / "ai_consultant.jsonl")[0]
    assert r["event_type"] == AuditEventType.TOOL_CALL
    assert r["payload"]["tool_name"] == "read_strategy"
    assert r["payload"]["latency_ms"] == 34.7
    assert r["payload"]["result_summary"] == "Returned 412 bytes"


@pytest.mark.anyio
async def test_llm_call(tmp_path):
    async with make_writer(tmp_path) as w:
        await w.log_llm_call(
            model="claude-3-5-sonnet-20241022",
            input_tokens=1200,
            output_tokens=350,
            cost_usd=Decimal("0.00234"),
        )

    r = read_jsonl(tmp_path / "audit" / "ai_consultant.jsonl")[0]
    assert r["event_type"] == AuditEventType.LLM_CALL
    assert r["payload"]["input_tokens"] == 1200
    assert r["payload"]["output_tokens"] == 350
    assert r["token_cost_usd"] == "0.00234"


@pytest.mark.anyio
async def test_proposal_generated(tmp_path):
    async with make_writer(tmp_path) as w:
        await w.log_proposal_generated(
            diff_summary="+5 lines: tighten stop-loss to 0.8%",
            strategy_id="strat-42",
        )

    r = read_jsonl(tmp_path / "audit" / "ai_consultant.jsonl")[0]
    assert r["event_type"] == AuditEventType.PROPOSAL_GENERATED
    assert r["strategy_id"] == "strat-42"
    assert "stop-loss" in r["payload"]["diff_summary"]


@pytest.mark.anyio
async def test_proposal_approved(tmp_path):
    async with make_writer(tmp_path) as w:
        await w.log_proposal_approved(user_id="user-99", strategy_id="strat-42")

    r = read_jsonl(tmp_path / "audit" / "ai_consultant.jsonl")[0]
    assert r["event_type"] == AuditEventType.PROPOSAL_APPROVED
    assert r["user_id"] == "user-99"
    assert r["strategy_id"] == "strat-42"


@pytest.mark.anyio
async def test_proposal_rejected(tmp_path):
    async with make_writer(tmp_path) as w:
        await w.log_proposal_rejected(
            user_id="user-99",
            reason="risk too high",
            strategy_id="strat-42",
        )

    r = read_jsonl(tmp_path / "audit" / "ai_consultant.jsonl")[0]
    assert r["event_type"] == AuditEventType.PROPOSAL_REJECTED
    assert r["payload"]["reason"] == "risk too high"


@pytest.mark.anyio
async def test_change_applied(tmp_path):
    async with make_writer(tmp_path) as w:
        await w.log_change_applied(
            diff="--- a/strategy.py\n+++ b/strategy.py\n@@ -1 +1 @@\n-sl=1\n+sl=0.8",
            strategy_id="strat-42",
            snapshot_path="/snapshots/strat-42-20260509.json",
        )

    r = read_jsonl(tmp_path / "audit" / "ai_consultant.jsonl")[0]
    assert r["event_type"] == AuditEventType.CHANGE_APPLIED
    assert r["payload"]["snapshot_path"] == "/snapshots/strat-42-20260509.json"


@pytest.mark.anyio
async def test_rollback_executed(tmp_path):
    async with make_writer(tmp_path) as w:
        await w.log_rollback_executed(
            snapshot_path="/snapshots/strat-42-20260509.json",
            strategy_id="strat-42",
        )

    r = read_jsonl(tmp_path / "audit" / "ai_consultant.jsonl")[0]
    assert r["event_type"] == AuditEventType.ROLLBACK_EXECUTED
    assert r["strategy_id"] == "strat-42"


@pytest.mark.anyio
async def test_all_event_types_in_sequence(tmp_path):
    """All event types write and produce valid parseable JSONL."""
    async with make_writer(tmp_path) as w:
        await w.log_session_start(model="claude-sonnet")
        await w.log_tool_call("read_file", {"path": "/x"}, "ok", 10.0)
        await w.log_llm_call("claude-sonnet", 100, 50, Decimal("0.001"))
        await w.log_proposal_generated("diff", "strat-1")
        await w.log_proposal_approved("u1", "strat-1")
        await w.log_proposal_rejected("u1", "too risky", "strat-1")
        await w.log_change_applied("diff", "strat-1", "/snap/1.json")
        await w.log_rollback_executed("/snap/1.json", "strat-1")
        await w.log_session_end("normal")

    records = read_jsonl(tmp_path / "audit" / "ai_consultant.jsonl")
    assert len(records) == 9
    seen_types = {r["event_type"] for r in records}
    assert seen_types == {e.value for e in AuditEventType}


@pytest.mark.anyio
async def test_jsonl_is_human_readable(tmp_path):
    """Each line must be valid JSON with readable fields (not binary)."""
    async with make_writer(tmp_path) as w:
        await w.log_session_start(model="claude-sonnet")

    raw = (tmp_path / "audit" / "ai_consultant.jsonl").read_text()
    assert raw.strip() != ""
    parsed = json.loads(raw.strip())
    assert isinstance(parsed["timestamp"], str)
    assert isinstance(parsed["event_type"], str)
    assert isinstance(parsed["payload"], dict)


@pytest.mark.anyio
async def test_write_failure_does_not_crash(tmp_path, monkeypatch):
    """A broken JSONL path must not raise — only stderr output."""
    async with make_writer(tmp_path) as w:
        # Corrupt the path so _append_line raises
        monkeypatch.setattr(w, "_jsonl_path", Path("/proc/non_existent_dir/fail.jsonl"))
        # Must not raise
        await w.log_session_start(model="claude-sonnet")


@pytest.mark.anyio
async def test_concurrent_writes_are_safe(tmp_path):
    """Concurrent log calls must not corrupt JSONL (lock test)."""
    async with make_writer(tmp_path) as w:
        await asyncio.gather(*[
            w.log_tool_call(f"tool_{i}", {}, "ok", float(i))
            for i in range(20)
        ])

    records = read_jsonl(tmp_path / "audit" / "ai_consultant.jsonl")
    assert len(records) == 20
    tool_names = {r["payload"]["tool_name"] for r in records}
    assert tool_names == {f"tool_{i}" for i in range(20)}


@pytest.mark.anyio
async def test_optional_fields_nullable(tmp_path):
    """user_id, strategy_id, token_cost_usd may be None."""
    async with make_writer(tmp_path) as w:
        await w.log(AuditEventType.SESSION_START, {"model": "x"})

    r = read_jsonl(tmp_path / "audit" / "ai_consultant.jsonl")[0]
    assert r["user_id"] is None
    assert r["strategy_id"] is None
    assert r["token_cost_usd"] is None
