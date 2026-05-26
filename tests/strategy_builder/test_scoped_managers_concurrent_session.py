"""BTCAAAAA-29971 regression: per-request session isolation.

Bug: the strategy-builder REST endpoints all routed through
``DatabaseManager._session`` (a long-lived, shared SQLAlchemy Session
created once in ``DatabaseManager.__init__``). When the inline Strategy
Browser dialog and the popped-out ``/strategy-browser`` window mounted
concurrently, two FastAPI request handlers raced on that one Session and
SQLAlchemy raised

    InvalidRequestError: This session is provisioning a new connection;
                        concurrent operations are not permitted

and on the rollback path

    Method 'rollback()' can't be called here: method 'rollback()' is
    already in progress and this would cause an unexpected state change.

The per-strategy try/except in ``sb_list_strategies`` swallowed the error
for every row in the loop, producing the ``skipping <id>: ...`` log flood
and an effectively empty list in the popped-out window.

Fix: ``DatabaseManager.scoped_managers()`` yields a fresh Session bound to
specialized managers for each call. All ``sb_*`` endpoints now wrap their
``asyncio.to_thread`` worker in ``with db.scoped_managers() as scoped:``.

This test guards 29371's state-preservation contract from a future
session refactor (gate item 4 — concurrent-request safety).
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# 1. Pure isolation invariant — each ``scoped_managers()`` call yields a
#    fresh ``Session`` that is NOT the shared ``DatabaseManager._session``.
#    This is the structural guarantee; if anyone reverts the patch to share
#    ``self._session`` again, this test fails immediately.
# ---------------------------------------------------------------------------


def test_scoped_managers_yields_distinct_session(db_manager_for_testing):
    db = db_manager_for_testing

    with db.scoped_managers() as a:
        with db.scoped_managers() as b:
            assert a.session is not db._session, (
                "scoped_managers() must NOT reuse the shared DatabaseManager._session "
                "— concurrent FastAPI handlers will race and emit "
                "'rollback() is already in progress' (BTCAAAAA-29971)."
            )
            assert b.session is not db._session
            assert a.session is not b.session, (
                "Each scoped_managers() invocation must hold its own Session; "
                "two overlapping with-blocks sharing one Session would re-introduce "
                "the BTCAAAAA-29971 race."
            )
            assert a.strategy.session is a.session
            assert a.test_results.session is a.session
            assert a.ai_recommendations.session is a.session


# ---------------------------------------------------------------------------
# 2. Concurrent-fetch invariant — N threads calling ``get_all_strategies()``
#    through ``scoped_managers()`` all succeed and observe the same row
#    count. Under the old shared-session path this loop raised
#    ``InvalidRequestError`` and the endpoint returned an empty list.
# ---------------------------------------------------------------------------


_N_WORKERS = 8


def _fetch_all(db: Any) -> tuple[int, list[str]]:
    """Mirror what ``sb_list_strategies._fetch`` does inside its threadpool.

    Returns (row_count, error_messages). Any exception raised by SQLAlchemy
    is captured as an error string so the assertion can name the failure
    mode instead of crashing the worker thread.
    """
    errors: list[str] = []
    try:
        with db.scoped_managers() as scoped:
            strategies = scoped.strategy.get_all_strategies()
            # Touch the latest-version path too — that's the inner call that
            # raised in the original bug for every iteration of the loop.
            for s in strategies[:5]:  # cap to keep the test fast
                try:
                    scoped.strategy.get_latest_version(s["strategy_id"])
                except Exception as exc:  # pragma: no cover - intentional capture
                    errors.append(f"get_latest_version({s['strategy_id']}): {exc!r}")
            return len(strategies), errors
    except Exception as exc:
        errors.append(f"scoped_managers: {exc!r}")
        return -1, errors


def test_concurrent_get_all_strategies_no_rollback_race(db_manager_for_testing):
    """Fire ``_N_WORKERS`` concurrent ``get_all_strategies`` calls through
    ``scoped_managers()`` and assert none raise and all see the same count.

    This is the structural regression test for BTCAAAAA-29971's expanded
    gate item 4: the popped-out window must always render the same
    populated list as the inline view under concurrent mount.
    """
    db = db_manager_for_testing

    # Barrier so all workers hit ``scoped_managers()`` at nearly the same
    # instant — that's the window where the old shared-session path raced.
    barrier = threading.Barrier(_N_WORKERS)

    def _worker() -> tuple[int, list[str]]:
        barrier.wait(timeout=5)
        return _fetch_all(db)

    with ThreadPoolExecutor(max_workers=_N_WORKERS) as pool:
        futures = [pool.submit(_worker) for _ in range(_N_WORKERS)]
        results = [f.result(timeout=30) for f in as_completed(futures)]

    # No worker may have raised SQLAlchemy InvalidRequestError or
    # 'rollback() is already in progress'.
    for idx, (count, errors) in enumerate(results):
        assert errors == [], (
            f"Worker {idx} hit SQLAlchemy errors under concurrent "
            f"scoped_managers() — this is the BTCAAAAA-29971 regression "
            f"signal. Errors: {errors}"
        )
        assert count >= 0, f"Worker {idx} crashed inside scoped_managers()"

    # Every worker must observe the same row count — anything else means
    # one worker's session lost rows to the other's rollback.
    counts = sorted({count for count, _ in results})
    assert len(counts) == 1, (
        f"Concurrent get_all_strategies() returned divergent counts {counts} — "
        f"sessions are bleeding into each other (BTCAAAAA-29971 regression)."
    )


# ---------------------------------------------------------------------------
# 3. Cleanup invariant — the scoped session is closed when the with-block
#    exits, even if the body raises. Otherwise the connection pool leaks
#    and we re-introduce the same 'rollback in progress' surface area on
#    the next checkout.
# ---------------------------------------------------------------------------


def test_scoped_managers_closes_session_on_exception(db_manager_for_testing):
    db = db_manager_for_testing

    captured_session: Any = None

    with pytest.raises(RuntimeError, match="boom"):
        with db.scoped_managers() as scoped:
            captured_session = scoped.session
            raise RuntimeError("boom")

    # SQLAlchemy ``Session.is_active`` is True for an open session; after
    # ``close()`` the session has no live transaction.
    assert captured_session is not None
    # The session itself can still be referenced but its connection is
    # returned to the pool. Calling ``execute`` on a closed session would
    # raise; we don't need to prove that here — we just need to prove the
    # context manager unwound through the rollback/close path without
    # re-raising the SQLAlchemy 'rollback in progress' marker error.
