"""
AI Consultant CLI — multi-turn conversation harness.

Usage:
    PYTHONPATH=src python -m consultant_cli

Environment:
    LLM_PROVIDER    anthropic | openai | ollama  (default: anthropic)
    ANTHROPIC_API_KEY / OPENAI_API_KEY / OLLAMA_BASE_URL as required
    AI_READONLY_PASSWORD  required when DB tools are enabled
    DB_DISABLE=1    set to skip DB tool registration (catalog-only mode)
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import uuid

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s %(name)s: %(message)s",
)


def _build_service():
    from ai_consultant.consultant_service import ConsultantService

    query_engine = None
    catalog = None

    if not os.environ.get("DB_DISABLE"):
        try:
            from ai_consultant.db.query_engine import QueryEngine
            query_engine = QueryEngine()
        except Exception as exc:
            print(f"[warn] DB tools unavailable: {exc}", file=sys.stderr)  # noqa: T201

    try:
        from ai_consultant.signal_catalog import SignalCatalogService
        db_url = None
        if query_engine is not None:
            from ai_consultant.db.query_engine import _build_readonly_url
            db_url = _build_readonly_url()
        catalog = SignalCatalogService(db_url=db_url)
        catalog.load(with_live_stats=(db_url is not None))
    except Exception as exc:
        print(f"[warn] Signal catalog unavailable: {exc}", file=sys.stderr)  # noqa: T201

    return ConsultantService(query_engine=query_engine, catalog=catalog)


async def _repl(service, session_id: str) -> None:
    print("AI Consultant — type 'exit' or press Ctrl-D to quit.\n")  # noqa: T201
    while True:
        try:
            line = await asyncio.get_event_loop().run_in_executor(None, lambda: input("You: "))
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")  # noqa: T201
            break
        line = line.strip()
        if not line:
            continue
        if line.lower() in {"exit", "quit", "bye"}:
            print("Goodbye.")  # noqa: T201
            break
        try:
            reply = await service.chat(session_id, line)
            print(f"\nConsultant: {reply}\n")  # noqa: T201
        except Exception as exc:
            print(f"[error] {exc}", file=sys.stderr)  # noqa: T201


async def main() -> None:
    service = _build_service()
    session_id = str(uuid.uuid4())
    tool_count = len(service._tools)
    print(f"Session: {session_id[:8]}…  Tools registered: {tool_count}")  # noqa: T201
    await _repl(service, session_id)


if __name__ == "__main__":
    asyncio.run(main())
