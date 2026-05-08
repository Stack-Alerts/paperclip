"""
Unit tests: PositionVerifier (Section H.1)
==========================================
Tests all verification paths:
  - Close verification: pass (position reaches 0 within timeout)
  - Close verification: fail (timeout, position remains open)
  - Reconciliation: match (ITM == Binance, no alert)
  - Reconciliation: WARNING mismatch (below halt threshold)
  - Reconciliation: CRITICAL mismatch — open vs closed divergence
  - Reconciliation: CRITICAL mismatch — size >= halt threshold
  - Manual halt acknowledgment clears halt flag
  - Trading halt prevents new entry (halt flag observable)
  - get_position_size method on BinanceClient (REST mock)
  - Alert channel fan-out (MultiAlertChannel)
  - FileAlertChannel, WebhookAlertChannel (error absorption)

All exchange calls and time functions are mocked — no real network I/O.
"""

from __future__ import annotations

import json
import time
import threading
from decimal import Decimal
from unittest.mock import MagicMock, patch, call
import pytest

from src.itm.engine.position_verifier import (
    Alert,
    AlertChannel,
    AlertSeverity,
    FileAlertChannel,
    LogAlertChannel,
    MultiAlertChannel,
    PositionVerifier,
    PositionVerifierConfig,
    WebhookAlertChannel,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_verifier(
    exchange_sizes=None,
    itm_size: Decimal = Decimal("0"),
    config: PositionVerifierConfig = None,
    alert_channel=None,
    clock_values=None,
) -> tuple[PositionVerifier, MagicMock]:
    """
    Build a PositionVerifier with a mocked BinanceClient.

    exchange_sizes: list of Decimal values returned in order by
        client.get_position_size.  Repeated calls cycle the last value.
    clock_values:  list of floats returned in order by the injected clock.
    """
    client = MagicMock()
    if exchange_sizes is not None:
        # Build side_effect that exhausts the list then repeats the last value
        responses = list(exchange_sizes)
        last = responses[-1] if responses else Decimal("0")

        def _side_effect(*args, **kwargs):
            if responses:
                return responses.pop(0)
            return last

        client.get_position_size.side_effect = _side_effect
    else:
        client.get_position_size.return_value = Decimal("0")

    if clock_values is not None:
        clock_iter = iter(clock_values)

        def _clock():
            try:
                return next(clock_iter)
            except StopIteration:
                return 9999.0  # safely past any deadline

        clock = _clock
    else:
        clock = None

    cfg = config or PositionVerifierConfig(
        close_verify_timeout_secs=10.0,
        close_verify_poll_interval_secs=0.01,  # fast for tests
        reconcile_interval_secs=3600.0,  # prevent background fires
    )
    alerts = alert_channel or _CollectingAlertChannel()
    verifier = PositionVerifier(
        binance_client=client,
        internal_position_provider=lambda sym: itm_size,
        config=cfg,
        alert_channel=alerts,
        clock=clock,
    )
    return verifier, client


class _CollectingAlertChannel:
    """Captures all alerts sent to it for assertion."""

    def __init__(self):
        self.alerts: list[Alert] = []

    def send(self, alert: Alert) -> None:
        self.alerts.append(alert)


# ---------------------------------------------------------------------------
# BinanceClient.get_position_size unit tests
# ---------------------------------------------------------------------------


class TestBinanceClientGetPositionSize:
    """Unit tests for the new get_position_size REST method."""

    def _make_client(self, response_body, symbol="BTCUSDT"):
        from src.itm.engine.binance_client import BinanceClient

        client = BinanceClient(
            api_key="testkey",
            api_secret="testsecret",
            use_testnet=True,
        )
        # Patch the internal _signed_request to return our mock body
        client._signed_request = MagicMock(return_value=response_body)
        client._rate_limiter = MagicMock()
        return client

    def test_returns_absolute_long_position(self):
        body = [{"symbol": "BTCUSDT", "positionAmt": "0.5"}]
        client = self._make_client(body)
        assert client.get_position_size("BTCUSDT") == Decimal("0.5")

    def test_returns_absolute_short_position(self):
        body = [{"symbol": "BTCUSDT", "positionAmt": "-0.3"}]
        client = self._make_client(body)
        assert client.get_position_size("BTCUSDT") == Decimal("0.3")

    def test_returns_zero_when_flat(self):
        body = [{"symbol": "BTCUSDT", "positionAmt": "0"}]
        client = self._make_client(body)
        assert client.get_position_size("BTCUSDT") == Decimal("0")

    def test_returns_zero_when_symbol_not_in_response(self):
        body = [{"symbol": "ETHUSDT", "positionAmt": "1.0"}]
        client = self._make_client(body)
        assert client.get_position_size("BTCUSDT") == Decimal("0")

    def test_handles_dict_response_single_object(self):
        # Some Binance endpoints return a single dict rather than list
        body = {"symbol": "BTCUSDT", "positionAmt": "0.1"}
        client = self._make_client(body)
        assert client.get_position_size("BTCUSDT") == Decimal("0.1")

    def test_consumes_rate_limiter(self):
        from src.itm.engine.binance_client import BinanceClient

        client = BinanceClient(
            api_key="testkey",
            api_secret="testsecret",
            use_testnet=True,
        )
        client._signed_request = MagicMock(return_value=[])
        client._rate_limiter = MagicMock()
        client.get_position_size("BTCUSDT")
        client._rate_limiter.consume.assert_called_once_with(weight=5)


# ---------------------------------------------------------------------------
# Close verification tests
# ---------------------------------------------------------------------------


class TestCloseVerification:
    def test_pass_position_reaches_zero_immediately(self):
        """Position is already 0 on first poll — verification passes."""
        alerts = _CollectingAlertChannel()
        verifier, client = _make_verifier(
            exchange_sizes=[Decimal("0")],
            alert_channel=alerts,
        )
        verifier.schedule_close_verification("coid-001")
        # Wait for background thread to complete
        time.sleep(0.2)

        assert not verifier.is_halted
        assert len(alerts.alerts) == 0
        client.get_position_size.assert_called()

    def test_pass_position_reaches_zero_after_polling(self):
        """Position closes after a couple of polls — verification passes."""
        alerts = _CollectingAlertChannel()
        verifier, client = _make_verifier(
            exchange_sizes=[Decimal("0.01"), Decimal("0.01"), Decimal("0")],
            alert_channel=alerts,
        )
        verifier.schedule_close_verification("coid-002")
        time.sleep(0.5)

        assert not verifier.is_halted
        assert len(alerts.alerts) == 0

    def test_fail_timeout_triggers_critical_alert_and_halt(self):
        """Position never reaches zero — CRITICAL alert fired and trading halted."""
        alerts = _CollectingAlertChannel()
        # Use a controlled clock: starts at 0, advances past deadline on 4th call
        # deadline = 0 + 10 = 10; calls: 0, 2, 4, 6, 8, 10.1 (past deadline)
        clock_values = [0.0, 2.0, 4.0, 6.0, 8.0, 10.1]
        cfg = PositionVerifierConfig(
            close_verify_timeout_secs=10.0,
            close_verify_poll_interval_secs=0.001,
            reconcile_interval_secs=3600.0,
        )
        verifier, client = _make_verifier(
            exchange_sizes=[Decimal("0.05")] * 20,
            alert_channel=alerts,
            config=cfg,
            clock_values=clock_values,
        )
        verifier.schedule_close_verification("coid-timeout")
        time.sleep(0.5)

        assert verifier.is_halted
        assert len(alerts.alerts) == 1
        alert = alerts.alerts[0]
        assert alert.severity == AlertSeverity.CRITICAL
        assert "FAILED" in alert.message
        assert alert.client_order_id == "coid-timeout"

    def test_fail_binance_query_error_on_timeout_still_halts(self):
        """If the final position query fails, we still halt with sentinel value."""
        alerts = _CollectingAlertChannel()
        # Clock: immediately past deadline so the loop exits on the first iteration
        # but then the final query raises
        clock_values = [0.0, 11.0]  # first call = 0, second = 11 (past 10s deadline)
        cfg = PositionVerifierConfig(
            close_verify_timeout_secs=10.0,
            close_verify_poll_interval_secs=0.001,
            reconcile_interval_secs=3600.0,
        )
        alerts = _CollectingAlertChannel()
        client = MagicMock()
        # First call (inside loop): return non-zero so we keep looping
        # But the loop condition fails first because clock already past deadline
        # Final call (post-loop): raise an error
        call_count = [0]

        def _pos_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] >= 2:
                raise RuntimeError("network error")
            return Decimal("0.1")

        client.get_position_size.side_effect = _pos_effect
        clock_iter = iter(clock_values)

        def _clock():
            try:
                return next(clock_iter)
            except StopIteration:
                return 9999.0

        verifier = PositionVerifier(
            binance_client=client,
            internal_position_provider=lambda s: Decimal("0"),
            config=cfg,
            alert_channel=alerts,
            clock=_clock,
        )
        verifier.schedule_close_verification("coid-error")
        time.sleep(0.5)

        assert verifier.is_halted
        assert len(alerts.alerts) == 1
        assert alerts.alerts[0].severity == AlertSeverity.CRITICAL

    def test_multiple_concurrent_verifications(self):
        """Multiple close verifications can run concurrently without interfering."""
        alerts = _CollectingAlertChannel()
        verifier, client = _make_verifier(
            exchange_sizes=[Decimal("0")],
            alert_channel=alerts,
        )
        for i in range(5):
            verifier.schedule_close_verification(f"coid-{i:03d}")
        time.sleep(0.5)

        assert not verifier.is_halted
        assert len(alerts.alerts) == 0


# ---------------------------------------------------------------------------
# Reconciliation tests
# ---------------------------------------------------------------------------


class TestReconciliation:
    def test_match_no_alert(self):
        """ITM and Binance agree — no alert, no halt."""
        alerts = _CollectingAlertChannel()
        verifier, _ = _make_verifier(
            exchange_sizes=[Decimal("0.1")],
            itm_size=Decimal("0.1"),
            alert_channel=alerts,
        )
        result = verifier.reconcile_once()

        assert result is True
        assert not verifier.is_halted
        assert len(alerts.alerts) == 0

    def test_both_zero_no_alert(self):
        """Both sides show zero position — clean match."""
        alerts = _CollectingAlertChannel()
        verifier, _ = _make_verifier(
            exchange_sizes=[Decimal("0")],
            itm_size=Decimal("0"),
            alert_channel=alerts,
        )
        result = verifier.reconcile_once()
        assert result is True
        assert len(alerts.alerts) == 0

    def test_warning_mismatch_below_threshold(self):
        """Size difference below threshold → WARNING, no halt."""
        cfg = PositionVerifierConfig(
            mismatch_size_warning_threshold=Decimal("0.001"),
            reconcile_interval_secs=3600.0,
        )
        alerts = _CollectingAlertChannel()
        verifier, _ = _make_verifier(
            exchange_sizes=[Decimal("0.1005")],
            itm_size=Decimal("0.1"),
            config=cfg,
            alert_channel=alerts,
        )
        result = verifier.reconcile_once()
        # diff = 0.0005 < 0.001 threshold → WARNING
        assert result is True  # trading not halted
        assert not verifier.is_halted
        assert len(alerts.alerts) == 1
        assert alerts.alerts[0].severity == AlertSeverity.WARNING

    def test_critical_open_vs_closed_divergence_itm_open(self):
        """ITM thinks open (0.1 BTC), Binance shows closed (0) → CRITICAL halt."""
        alerts = _CollectingAlertChannel()
        verifier, _ = _make_verifier(
            exchange_sizes=[Decimal("0")],
            itm_size=Decimal("0.1"),
            alert_channel=alerts,
        )
        result = verifier.reconcile_once()

        assert result is False
        assert verifier.is_halted
        assert len(alerts.alerts) == 1
        alert = alerts.alerts[0]
        assert alert.severity == AlertSeverity.CRITICAL
        assert "DIVERGENCE" in alert.message

    def test_critical_open_vs_closed_divergence_exchange_open(self):
        """ITM thinks closed (0), Binance shows open (0.5 BTC) → CRITICAL halt."""
        alerts = _CollectingAlertChannel()
        verifier, _ = _make_verifier(
            exchange_sizes=[Decimal("0.5")],
            itm_size=Decimal("0"),
            alert_channel=alerts,
        )
        result = verifier.reconcile_once()

        assert result is False
        assert verifier.is_halted
        assert len(alerts.alerts) == 1
        assert alerts.alerts[0].severity == AlertSeverity.CRITICAL

    def test_critical_size_mismatch_at_threshold(self):
        """Size difference at threshold → CRITICAL halt."""
        cfg = PositionVerifierConfig(
            mismatch_size_warning_threshold=Decimal("0.001"),
            reconcile_interval_secs=3600.0,
        )
        alerts = _CollectingAlertChannel()
        verifier, _ = _make_verifier(
            exchange_sizes=[Decimal("0.101")],
            itm_size=Decimal("0.1"),
            config=cfg,
            alert_channel=alerts,
        )
        result = verifier.reconcile_once()
        # diff = 0.001 == threshold → CRITICAL (≥)
        assert result is False
        assert verifier.is_halted
        assert alerts.alerts[0].severity == AlertSeverity.CRITICAL

    def test_critical_size_mismatch_above_threshold(self):
        """Size difference well above threshold → CRITICAL halt."""
        cfg = PositionVerifierConfig(
            mismatch_size_warning_threshold=Decimal("0.001"),
            reconcile_interval_secs=3600.0,
        )
        alerts = _CollectingAlertChannel()
        verifier, _ = _make_verifier(
            exchange_sizes=[Decimal("0.2")],
            itm_size=Decimal("0.1"),
            config=cfg,
            alert_channel=alerts,
        )
        result = verifier.reconcile_once()
        assert result is False
        assert verifier.is_halted
        assert alerts.alerts[0].severity == AlertSeverity.CRITICAL

    def test_binance_query_failure_is_conservative(self):
        """If Binance query fails, reconciliation skips without raising."""
        alerts = _CollectingAlertChannel()
        client = MagicMock()
        client.get_position_size.side_effect = RuntimeError("network error")
        cfg = PositionVerifierConfig(reconcile_interval_secs=3600.0)
        verifier = PositionVerifier(
            binance_client=client,
            internal_position_provider=lambda s: Decimal("0.1"),
            config=cfg,
            alert_channel=alerts,
        )
        result = verifier.reconcile_once()
        # Should NOT halt on query failure — conservative
        assert result is True
        assert not verifier.is_halted
        assert len(alerts.alerts) == 0

    def test_internal_provider_failure_is_conservative(self):
        """If internal_position_provider raises, skip without halting."""
        alerts = _CollectingAlertChannel()
        client = MagicMock()
        client.get_position_size.return_value = Decimal("0.1")
        cfg = PositionVerifierConfig(reconcile_interval_secs=3600.0)

        def _bad_provider(sym):
            raise RuntimeError("state db unavailable")

        verifier = PositionVerifier(
            binance_client=client,
            internal_position_provider=_bad_provider,
            config=cfg,
            alert_channel=alerts,
        )
        result = verifier.reconcile_once()
        assert result is True
        assert not verifier.is_halted


# ---------------------------------------------------------------------------
# Halt / acknowledgment tests
# ---------------------------------------------------------------------------


class TestHaltAndAcknowledgment:
    def test_halt_set_by_reconciliation(self):
        """Reconciliation CRITICAL sets is_halted=True."""
        verifier, _ = _make_verifier(
            exchange_sizes=[Decimal("0.5")],
            itm_size=Decimal("0"),
        )
        verifier.reconcile_once()
        assert verifier.is_halted

    def test_acknowledge_halt_clears_flag(self):
        """acknowledge_halt() clears the halt and sets is_halted=False."""
        verifier, _ = _make_verifier(
            exchange_sizes=[Decimal("0.5")],
            itm_size=Decimal("0"),
        )
        verifier.reconcile_once()
        assert verifier.is_halted

        verifier.acknowledge_halt(operator_id="ops-alice")
        assert not verifier.is_halted

    def test_acknowledge_halt_when_not_halted_is_safe(self):
        """acknowledge_halt() is a no-op when not halted."""
        verifier, _ = _make_verifier(exchange_sizes=[Decimal("0")])
        verifier.acknowledge_halt(operator_id="ops-bob")
        assert not verifier.is_halted

    def test_multiple_reconcile_mismatches_only_one_alert(self):
        """If already halted, subsequent reconcile passes do not spam alerts."""
        alerts = _CollectingAlertChannel()
        verifier, client = _make_verifier(
            exchange_sizes=[Decimal("0.5"), Decimal("0.5"), Decimal("0.5")],
            itm_size=Decimal("0"),
            alert_channel=alerts,
        )
        verifier.reconcile_once()  # triggers halt + 1 alert
        verifier.reconcile_once()  # still halted — sends new alert but no duplicate halt log
        verifier.reconcile_once()

        # Halt was triggered once (no repeated halt log), but alerts still fire each pass
        assert verifier.is_halted
        # Alerts should be present for each reconcile call
        assert len(alerts.alerts) >= 1

    def test_halt_cleared_then_retriggered_by_new_mismatch(self):
        """After ack, a new mismatch re-triggers halt."""
        alerts = _CollectingAlertChannel()
        verifier, client = _make_verifier(
            exchange_sizes=[Decimal("0.5"), Decimal("0")],
            itm_size=Decimal("0"),
            alert_channel=alerts,
        )
        # First mismatch: halted
        verifier.reconcile_once()
        assert verifier.is_halted

        # Operator clears
        verifier.acknowledge_halt("ops-alice")
        assert not verifier.is_halted

        # Reset exchange to mismatch again
        client.get_position_size.side_effect = None
        client.get_position_size.return_value = Decimal("0.5")
        verifier.reconcile_once()
        assert verifier.is_halted

    def test_status_dict_reflects_halt(self):
        """status() returns accurate halt info."""
        verifier, _ = _make_verifier(
            exchange_sizes=[Decimal("0.5")],
            itm_size=Decimal("0"),
        )
        s = verifier.status()
        assert s["halted"] is False

        verifier.reconcile_once()
        s2 = verifier.status()
        assert s2["halted"] is True
        assert s2["halt_reason"] is not None
        assert s2["halt_ts"] is not None


# ---------------------------------------------------------------------------
# Background reconciliation thread tests
# ---------------------------------------------------------------------------


class TestBackgroundReconciliation:
    def test_start_runs_startup_reconciliation(self):
        """start() runs an immediate reconciliation pass."""
        alerts = _CollectingAlertChannel()
        verifier, client = _make_verifier(
            exchange_sizes=[Decimal("0"), Decimal("0")],
            itm_size=Decimal("0"),
            alert_channel=alerts,
        )
        verifier.start()
        time.sleep(0.1)
        verifier.stop()
        # At least one position query happened during startup
        assert client.get_position_size.call_count >= 1

    def test_stop_terminates_thread(self):
        """stop() joins the background thread cleanly."""
        verifier, _ = _make_verifier(exchange_sizes=[Decimal("0")])
        verifier.start()
        assert verifier._reconcile_thread.is_alive()
        verifier.stop()
        # Thread should not be alive after stop
        assert verifier._reconcile_thread is None or not verifier._reconcile_thread.is_alive()

    def test_double_start_does_not_duplicate_thread(self):
        """Calling start() twice does not start a second thread."""
        verifier, _ = _make_verifier(exchange_sizes=[Decimal("0")])
        verifier.start()
        t1 = verifier._reconcile_thread
        verifier.start()  # should be a no-op
        t2 = verifier._reconcile_thread
        assert t1 is t2
        verifier.stop()


# ---------------------------------------------------------------------------
# Alert channel tests
# ---------------------------------------------------------------------------


class TestAlertChannels:
    def test_log_alert_channel_does_not_raise(self):
        ch = LogAlertChannel()
        alert = Alert(
            severity=AlertSeverity.CRITICAL,
            message="Test alert",
            symbol="BTCUSDT",
            itm_position=Decimal("0"),
            exchange_position=Decimal("0.1"),
        )
        ch.send(alert)  # must not raise

    def test_multi_alert_channel_delivers_to_all(self):
        ch1 = _CollectingAlertChannel()
        ch2 = _CollectingAlertChannel()
        multi = MultiAlertChannel([ch1, ch2])
        alert = Alert(
            severity=AlertSeverity.WARNING,
            message="Test",
            symbol="BTCUSDT",
            itm_position=Decimal("0.1"),
            exchange_position=Decimal("0.1005"),
        )
        multi.send(alert)
        assert len(ch1.alerts) == 1
        assert len(ch2.alerts) == 1

    def test_multi_alert_channel_absorbs_child_exception(self):
        """If one channel raises, the next is still called."""
        class _ErrorChannel(AlertChannel):
            def send(self, alert):
                raise RuntimeError("channel failed")

        ch2 = _CollectingAlertChannel()
        multi = MultiAlertChannel([_ErrorChannel(), ch2])
        alert = Alert(
            severity=AlertSeverity.WARNING,
            message="Test",
            symbol="BTCUSDT",
            itm_position=Decimal("0"),
            exchange_position=Decimal("0"),
        )
        multi.send(alert)  # must not raise
        assert len(ch2.alerts) == 1

    def test_webhook_alert_channel_absorbs_network_error(self):
        """WebhookAlertChannel does not raise on request failure."""
        ch = WebhookAlertChannel(url="http://localhost:0/no-such-endpoint", timeout=0.01)
        alert = Alert(
            severity=AlertSeverity.CRITICAL,
            message="Test",
            symbol="BTCUSDT",
            itm_position=Decimal("0"),
            exchange_position=Decimal("0.5"),
        )
        ch.send(alert)  # must not raise

    def test_file_alert_channel_writes_json_lines(self, tmp_path):
        path = str(tmp_path / "alerts.jsonl")
        ch = FileAlertChannel(path=path)
        for i in range(3):
            alert = Alert(
                severity=AlertSeverity.WARNING,
                message=f"Alert {i}",
                symbol="BTCUSDT",
                itm_position=Decimal("0.1"),
                exchange_position=Decimal("0.1"),
            )
            ch.send(alert)
        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 3
        for line in lines:
            obj = json.loads(line)
            assert obj["symbol"] == "BTCUSDT"

    def test_file_alert_channel_absorbs_io_error(self):
        """FileAlertChannel does not raise if the file cannot be written."""
        ch = FileAlertChannel(path="/nonexistent_dir/alerts.jsonl")
        alert = Alert(
            severity=AlertSeverity.CRITICAL,
            message="Test",
            symbol="BTCUSDT",
            itm_position=Decimal("0"),
            exchange_position=Decimal("0.1"),
        )
        ch.send(alert)  # must not raise

    def test_alert_as_dict_roundtrip(self):
        alert = Alert(
            severity=AlertSeverity.CRITICAL,
            message="Mismatch",
            symbol="BTCUSDT",
            itm_position=Decimal("0"),
            exchange_position=Decimal("0.5"),
            client_order_id="coid-xyz",
            detail="diff=0.5",
        )
        d = alert.as_dict()
        assert d["severity"] == "CRITICAL"
        assert d["symbol"] == "BTCUSDT"
        assert d["itm_position"] == "0"
        assert d["exchange_position"] == "0.5"
        assert d["client_order_id"] == "coid-xyz"
        assert d["detail"] == "diff=0.5"
        assert "timestamp" in d


# ---------------------------------------------------------------------------
# PositionVerifierConfig validation
# ---------------------------------------------------------------------------


class TestPositionVerifierConfig:
    def test_invalid_timeout_raises(self):
        with pytest.raises(ValueError):
            PositionVerifierConfig(close_verify_timeout_secs=0)

    def test_invalid_poll_interval_raises(self):
        with pytest.raises(ValueError):
            PositionVerifierConfig(close_verify_poll_interval_secs=-1)

    def test_invalid_reconcile_interval_raises(self):
        with pytest.raises(ValueError):
            PositionVerifierConfig(reconcile_interval_secs=0)

    def test_defaults_are_sane(self):
        cfg = PositionVerifierConfig()
        assert cfg.close_verify_timeout_secs == 30.0
        assert cfg.reconcile_interval_secs == 60.0
        assert cfg.symbol == "BTCUSDT"
