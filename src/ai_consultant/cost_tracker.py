"""
Multi-provider cost aggregation against the ai_consultant_audit table.

Queries LLM_CALL events from Postgres, classifies them by provider/model,
and returns aggregated token counts with estimated USD costs.

Usage:
    from ai_consultant.cost_tracker import CostTracker

    tracker = CostTracker()
    rows = tracker.query_costs(days=30)
    totals = tracker.compute_totals(rows)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool


@dataclass
class ProviderCost:
    provider: str
    model: str
    calls: int
    input_tokens: int
    output_tokens: int
    estimated_cost: float


# Per-model pricing ($/M tokens)
_PRICING: Dict[str, Dict[str, float]] = {
    "Anthropic": {"input": 3.0, "output": 15.0},
    "OpenAI": {"input": 5.0, "output": 15.0},
    "DeepSeek": {"flash_input": 0.20, "flash_output": 1.10, "pro_input": 0.55, "pro_output": 2.19},
    "OpenRouter": {"input": 0.55, "output": 2.19},
    "Ollama": {"input": 0.0, "output": 0.0},
}


def _classify_provider(model: str) -> str:
    """Classify the provider from the model name string."""
    ml = model.lower()
    if "claude" in ml:
        return "Anthropic"
    if "gpt" in ml or "openai" in ml:
        return "OpenAI"
    if "deepseek" in ml:
        return "DeepSeek"
    if "llama" in ml or "mistral" in ml or "gemma" in ml or "phi" in ml:
        return "Ollama"
    return "OpenRouter"


def _estimate_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate USD cost for a provider/model/token-tuple."""
    pricing = _PRICING.get(provider, _PRICING["OpenRouter"])
    ml = model.lower()
    if provider == "DeepSeek":
        if "flash" in ml:
            in_rate, out_rate = pricing["flash_input"], pricing["flash_output"]
        else:
            in_rate, out_rate = pricing["pro_input"], pricing["pro_output"]
    else:
        in_rate = pricing.get("input", 0.55)
        out_rate = pricing.get("output", 2.19)
    return input_tokens * in_rate / 1_000_000 + output_tokens * out_rate / 1_000_000


def _build_db_url() -> str:
    """Construct DB URL via pydantic-settings (.env auto-loaded — BTCAAAAA-30576)."""
    from src.optimizer_v3.database.settings import get_database_settings

    return get_database_settings().database_url()


class CostTracker:
    """Query ai_consultant_audit for LLM_CALL events and aggregate costs."""

    def __init__(self, db_url: Optional[str] = None) -> None:
        url = db_url or _build_db_url()
        self._engine = create_engine(
            url,
            poolclass=QueuePool,
            pool_size=2,
            max_overflow=3,
            pool_timeout=15,
            pool_recycle=1800,
            pool_pre_ping=True,
        )
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

    def _session(self) -> Session:
        return self._session_factory()

    def query_costs(
        self,
        since: Optional[datetime] = None,
        days: Optional[int] = None,
    ) -> List[ProviderCost]:
        """Query LLM_CALL audit events, aggregate by provider/model.

        Args:
            since: Start of time range (inclusive).
            days: Look back N days from now (overridden by `since`).
        """
        if since is None:
            if days is not None:
                since = datetime.now(timezone.utc) - timedelta(days=days)
            else:
                since = datetime.now(timezone.utc) - timedelta(days=30)

        sql = text("""
            SELECT
                payload->>'model'    AS model,
                COUNT(*)             AS calls,
                COALESCE(SUM((payload->>'input_tokens')::bigint), 0)  AS input_tokens,
                COALESCE(SUM((payload->>'output_tokens')::bigint), 0) AS output_tokens
            FROM ai_consultant_audit
            WHERE event_type = 'llm_call'
              AND timestamp    >= :since
            GROUP BY payload->>'model'
            ORDER BY input_tokens + output_tokens DESC
        """)

        results: List[ProviderCost] = []
        with self._session() as sess:
            rows = sess.execute(sql, {"since": since}).mappings().all()

        for row in rows:
            model = row["model"] or "unknown"
            provider = _classify_provider(model)
            input_tok = row["input_tokens"]
            output_tok = row["output_tokens"]
            cost = _estimate_cost(provider, model, input_tok, output_tok)
            results.append(
                ProviderCost(
                    provider=provider,
                    model=model,
                    calls=row["calls"],
                    input_tokens=input_tok,
                    output_tokens=output_tok,
                    estimated_cost=cost,
                )
            )

        return results

    def compute_totals(self, rows: List[ProviderCost]) -> ProviderCost:
        """Compute a totals row from a list of ProviderCost rows."""
        total_input = sum(r.input_tokens for r in rows)
        total_output = sum(r.output_tokens for r in rows)
        total_cost = sum(r.estimated_cost for r in rows)
        return ProviderCost(
            provider="",
            model="TOTAL",
            calls=sum(r.calls for r in rows),
            input_tokens=total_input,
            output_tokens=total_output,
            estimated_cost=total_cost,
        )

    def close(self) -> None:
        self._engine.dispose()
