"""
E2E tests for the Trades panel — empty state, trade entry, widget state.

Regression coverage for BTCAAAAA-645 (Trades Broken): the widget must
correctly reflect state when trades are present and when they are absent.

Happy-path: add a valid trade, verify table row count and get_trades().
Error-path: add a trade with missing optional fields — panel must not raise.

Run:
    QT_QPA_PLATFORM=offscreen pytest tests/ui_qt/test_trades.py -v
"""

import pytest
from PyQt5.QtWidgets import QTableWidget

from src.optimizer_v3.ui.trades_panel import TradesPanel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _trade(trade_id="T001", status="OPEN", **overrides):
    """Return a minimal valid trade dict with all required keys."""
    base = {
        "id": trade_id,
        "timestamp": "2026-01-01T09:00:00",
        "symbol": "BTC/USDT",
        "side": "BUY",
        "size": "0.01",
        "entry_price": "50000.00",
        "status": status,
    }
    base.update(overrides)
    return base


def _closed_trade(trade_id="T002"):
    """Return a closed trade with exit fields populated."""
    return _trade(
        trade_id=trade_id,
        status="CLOSED",
        exit_price="51000.00",
        exit_timestamp="2026-01-01T10:00:00",
        pnl="10.00",
        exit_condition_name="TP",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.qt_real
def test_trades_panel_renders_trade_table(qtbot):
    """TradesPanel initialises and exposes a QTableWidget at self.table."""
    panel = TradesPanel()
    qtbot.addWidget(panel)

    assert hasattr(panel, "table"), "TradesPanel must have a .table attribute"
    assert isinstance(panel.table, QTableWidget)


@pytest.mark.qt_real
def test_trades_panel_empty_on_init(qtbot):
    """Panel starts with zero rows and empty get_trades()."""
    panel = TradesPanel()
    qtbot.addWidget(panel)

    assert panel.table.rowCount() == 0
    assert panel.get_trades() == []


@pytest.mark.qt_real
def test_trades_panel_add_open_trade_updates_row_count(qtbot):
    """
    Happy path: adding an OPEN trade increments the table row count.

    Regression for BTCAAAAA-645 — widget state must update when a trade
    is present, verifying the display pipeline is wired correctly.
    """
    panel = TradesPanel()
    qtbot.addWidget(panel)

    panel.add_trade(_trade("T001"))

    assert panel.table.rowCount() == 1, (
        "REGRESSION BTCAAAAA-645: table row count must be 1 after add_trade()"
    )
    assert len(panel.get_trades()) == 1


@pytest.mark.qt_real
def test_trades_panel_add_multiple_distinct_trades(qtbot):
    """Adding three distinct trades produces three rows."""
    panel = TradesPanel()
    qtbot.addWidget(panel)

    for i in range(3):
        panel.add_trade(_trade(f"T{i:03d}"))

    assert panel.table.rowCount() == 3


@pytest.mark.qt_real
def test_trades_panel_add_closed_trade(qtbot):
    """Adding a closed trade with exit fields does not crash the panel."""
    panel = TradesPanel()
    qtbot.addWidget(panel)

    panel.add_trade(_closed_trade("T_CLOSE"))

    assert panel.table.rowCount() == 1


@pytest.mark.qt_real
def test_trades_panel_update_open_to_closed(qtbot):
    """
    Happy path: adding the same trade ID again with status=CLOSED updates
    the existing row rather than appending a new one (non-partial exit path).
    """
    panel = TradesPanel()
    qtbot.addWidget(panel)

    panel.add_trade(_trade("T001", status="OPEN"))
    panel.add_trade(_closed_trade("T001"))  # same ID, now closed

    assert panel.table.rowCount() == 1, (
        "Updating an existing trade (same ID, non-partial) must not add a new row"
    )


@pytest.mark.qt_real
def test_trades_panel_missing_optional_fields_does_not_raise(qtbot):
    """
    Error path: add_trade() with only the required 'id' key must not raise.

    The panel must handle incomplete trade dicts gracefully.
    """
    panel = TradesPanel()
    qtbot.addWidget(panel)

    try:
        panel.add_trade({"id": "T_INCOMPLETE"})
    except Exception as exc:
        pytest.fail(
            f"add_trade with minimal dict raised {type(exc).__name__}: {exc}"
        )


@pytest.mark.qt_real
def test_trades_panel_clear_resets_to_empty(qtbot):
    """clear_trades() removes all rows from the table."""
    panel = TradesPanel()
    qtbot.addWidget(panel)

    panel.add_trade(_trade("T001"))
    panel.add_trade(_trade("T002"))
    assert panel.table.rowCount() == 2

    panel.clear_trades()

    assert panel.table.rowCount() == 0
    assert panel.get_trades() == []
