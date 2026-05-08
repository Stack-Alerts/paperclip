"""
Unit tests: BinanceClient WebSocket reconnection (Fix 2 — BTCAAAAA-573)
========================================================================
Verifies that ``start_user_data_stream`` passes ``reconnect=5`` to
``WebSocketApp.run_forever()``, ensuring the user-data stream reconnects
automatically after a disconnect rather than silently dying.

All network I/O is mocked — no real Binance connection.
The websocket-client package may not be installed in CI; these tests inject
a mock module into sys.modules so they run without the real package.
"""

from __future__ import annotations

import sys
import types
import threading
import time
import logging
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_websocket_module():
    """Build a minimal mock that stands in for the websocket-client package."""
    mock_module = types.ModuleType("websocket")
    mock_ws_app = MagicMock()
    mock_module.WebSocketApp = MagicMock(return_value=mock_ws_app)
    return mock_module, mock_ws_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_ws_module():
    """Inject a fake websocket module and restore state afterwards."""
    mod, ws_app = _make_mock_websocket_module()
    original = sys.modules.get("websocket")
    sys.modules["websocket"] = mod
    yield mod, ws_app
    if original is None:
        sys.modules.pop("websocket", None)
    else:
        sys.modules["websocket"] = original


@pytest.fixture
def client(mock_ws_module):
    """BinanceClient with websocket module mocked out."""
    # Re-import after websocket module is injected
    import importlib
    import src.itm.engine.binance_client as bc_module
    # Ensure the module sees websocket as available
    bc_module._WS_AVAILABLE = True
    bc_module.websocket = sys.modules["websocket"]

    mock_session = MagicMock()
    from src.itm.engine.binance_client import BinanceClient
    c = BinanceClient(
        api_key="test-key-abc123",
        api_secret="test-secret-xyz789",
        use_testnet=True,
        session=mock_session,
    )
    return c


# ---------------------------------------------------------------------------
# WebSocket reconnection tests
# ---------------------------------------------------------------------------


class TestWebSocketReconnect:
    """Verify that run_forever() is invoked with reconnect=5."""

    def test_run_forever_called_with_reconnect_5(self, client, mock_ws_module):
        """start_user_data_stream must pass reconnect=5 to run_forever().

        This ensures the order-update stream auto-reconnects after a
        connection drop instead of silently dying (Fix 2, BTCAAAAA-573).
        """
        _mod, mock_ws_app = mock_ws_module
        client._listen_key = "abcdefgh-12345678-listen-key"
        client._create_listen_key = MagicMock(return_value=client._listen_key)

        client.start_user_data_stream(on_execution_report=MagicMock())

        # Give the daemon thread a moment to call run_forever
        if client._ws_thread and client._ws_thread.is_alive():
            client._ws_thread.join(timeout=1.0)

        # run_forever must have been called exactly once
        mock_ws_app.run_forever.assert_called_once()

        # The call must include reconnect=5
        _args, kwargs = mock_ws_app.run_forever.call_args
        assert kwargs.get("reconnect") == 5, (
            f"Expected reconnect=5, got reconnect={kwargs.get('reconnect')!r}. "
            "run_forever() must include reconnect=5 so the stream auto-reconnects."
        )

    def test_run_forever_ping_params_preserved(self, client, mock_ws_module):
        """ping_interval and ping_timeout are preserved alongside reconnect=5."""
        _mod, mock_ws_app = mock_ws_module
        client._listen_key = "abcdefgh-12345678-listen-key"
        client._create_listen_key = MagicMock(return_value=client._listen_key)

        client.start_user_data_stream(on_execution_report=MagicMock())

        if client._ws_thread and client._ws_thread.is_alive():
            client._ws_thread.join(timeout=1.0)

        _args, kwargs = mock_ws_app.run_forever.call_args
        assert kwargs.get("ping_interval") == 60
        assert kwargs.get("ping_timeout") == 10
        assert kwargs.get("reconnect") == 5

    def test_ws_thread_is_daemon(self, client, mock_ws_module):
        """The WebSocket background thread must be a daemon thread."""
        _mod, mock_ws_app = mock_ws_module

        def slow_run_forever(**kwargs):
            time.sleep(0.05)

        mock_ws_app.run_forever.side_effect = slow_run_forever

        client._listen_key = "abcdefgh-12345678-listen-key"
        client._create_listen_key = MagicMock(return_value=client._listen_key)

        client.start_user_data_stream(on_execution_report=MagicMock())

        assert client._ws_thread is not None
        assert client._ws_thread.daemon is True, (
            "binance-ws thread must be a daemon so it doesn't block process shutdown"
        )

    def test_on_open_logs_truncated_key(self, client, mock_ws_module, caplog):
        """on_open must log only the first 8 chars of the listen key (Fix 1)."""
        _mod, mock_ws_app = mock_ws_module

        full_key = "ABCDEFGH_SHOULD_NOT_APPEAR_IN_LOGS_XYZ"
        client._listen_key = full_key
        client._create_listen_key = MagicMock(return_value=full_key)

        captured_on_open = {}

        def capture_ws_app(url, on_message, on_error, on_close, on_open):
            captured_on_open["fn"] = on_open
            return mock_ws_app

        import src.itm.engine.binance_client as bc_module
        bc_module.websocket.WebSocketApp.side_effect = capture_ws_app

        with caplog.at_level(logging.INFO, logger="src.itm.engine.binance_client"):
            client.start_user_data_stream(on_execution_report=MagicMock())

            # Invoke the on_open callback directly to check log output
            if "fn" in captured_on_open:
                captured_on_open["fn"](ws=None)

        # The full key must not appear in the log
        for record in caplog.records:
            assert full_key not in record.getMessage(), (
                f"Full listen key leaked in log: {record.getMessage()!r}"
            )
        # The first 8 chars should appear
        assert any(
            full_key[:8] in record.getMessage()
            for record in caplog.records
        ), "Expected first 8 chars of listen key in log, but not found"
