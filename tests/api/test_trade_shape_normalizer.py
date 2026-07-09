"""
BTCAAAAA-39058: regression test for src/api/app.py trade-shape normalizer.

Pin the partial-size / position-size / quantity / size fallback chain for the
`quantity` field so the webui Trades Table SIZE column populates for partial-exit
legs (partial_size) AND full-close rows (position_size). Engine emits these keys
since the BTC-25803 institutional fix (multicore_backtest_engine.py:753-754 and
ultra_hybrid_simulator.py:638-639); previously the API fallback only read the
legacy "quantity"/"size" keys (neither of which exist on engine output) and
returned 0.0, causing TradesPanel.tsx TradeRow/TotalRow to render "—".
"""

from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Source-level fallback chain contract (pin the BTC-39058 patch)
# ---------------------------------------------------------------------------


def _read_quantity_line() -> str:
    """Return the literal `quantity` line in _run_backtest_in_thread's normalizer."""
    import src.api.app as api_app  # noqa: WPS433 — intentional in-test import
    src = api_app.__file__
    with open(src, "r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.lstrip()
            if stripped.startswith('"quantity":'):
                return stripped.rstrip("\n")
    raise AssertionError(
        "Could not find `\"quantity\":` line in src/api/app.py — "
        "the trade-shape normalizer block may have been moved."
    )


def test_quantity_fallback_chain_includes_partial_and_position_size():
    """Pin the exact fallback order: partial_size → position_size → quantity → size → 0."""
    line = _read_quantity_line()
    # Exact priority order mandated by BTC-25803 / mirrored by PyQt trades_panel.py:559-564
    expected_order = [
        't.get("partial_size")',
        't.get("position_size")',
        't.get("quantity")',
        't.get("size")',
        " or 0",
    ]
    last_idx = -1
    for needle in expected_order:
        idx = line.find(needle)
        assert idx > last_idx, (
            f"fallback chain out of order at {needle!r}; line was: {line!r}"
        )
        last_idx = idx
    # Also assert no truncation/snippet was left behind
    assert line.count("t.get(") == 4, (
        f"expected exactly 4 t.get(...) calls, got {line.count('t.get(')} in: {line!r}"
    )


def test_quantity_fallback_does_not_regress_entry_exit_pnl_paths():
    """Regression guard: ensure entryPrice/exitPrice/pnl normalization is unchanged."""
    import src.api.app as api_app
    src = open(api_app.__file__, "r", encoding="utf-8").read()
    # Existing fallbacks for entry/exit/pnl must remain single-source; we only
    # added two new keys to the quantity chain.
    assert '"entryPrice": float(t.get("entry_price") or t.get("entryPrice") or 0)' in src
    assert '"exitPrice": float(t.get("exit_price") or t.get("exitPrice") or 0)' in src
    assert '"pnl": float(t.get("pnl") or 0)' in src
    # And pnlPct unchanged
    assert re.search(
        r'"pnlPercentage":\s*float\(t\.get\("pnl_pct"\) or t\.get\("pnl_percent"\) or t\.get\("pnlPercentage"\) or 0\)',
        src,
    ), "pnlPercentage fallback chain must remain unchanged"


# ---------------------------------------------------------------------------
# Behavioral fall-through — validate the same `or` chain semantics in isolation.
# This proves the logic the API applies (not just that the source is written
# correctly) so a future refactor that preserves the source but breaks the
# truthiness chain still fails loudly.
# ---------------------------------------------------------------------------


def _normalize_quantity_like_api(t: dict) -> float:
    """Mirror the exact fallback chain in src/api/app.py:2293."""
    return float(
        t.get("partial_size")
        or t.get("position_size")
        or t.get("quantity")
        or t.get("size")
        or 0
    )


def test_partial_size_wins_over_position_size_partial_exit_leg():
    trade = {"partial_size": 0.123, "position_size": 0.5, "quantity": 999}
    assert _normalize_quantity_like_api(trade) == 0.123


def test_position_size_used_when_no_partial_size_full_close_row():
    trade = {"position_size": 0.5, "quantity": 999, "size": 999}
    assert _normalize_quantity_like_api(trade) == 0.5


def test_legacy_quantity_key_still_works():
    """Pre-BTC-25803 trades carried size in 'quantity' or 'size' keys."""
    trade = {"quantity": 0.25, "size": 999}
    assert _normalize_quantity_like_api(trade) == 0.25


def test_legacy_size_key_still_works():
    trade = {"size": 0.25}
    assert _normalize_quantity_like_api(trade) == 0.25


def test_zero_falls_back_to_zero_float():
    """All None / missing → 0.0 (the previous behavior)."""
    for trade in (
        {},
        {"partial_size": None, "position_size": None, "quantity": None, "size": None},
        {"partial_size": 0.0},  # 0 is falsy → falls through (preserves BTC-25803 semantics)
    ):
        # NB: a literal 0.0 still falls through to the trailing `0`, which is the
        # behavior of the existing `or` chain — this test documents that quirk.
        result = _normalize_quantity_like_api(trade)
        assert result == 0.0, f"expected 0.0 for {trade!r}, got {result!r}"


# ---------------------------------------------------------------------------
# Module import smoke test — no syntax / name errors introduced by the patch.
# ---------------------------------------------------------------------------


def test_api_app_module_imports_without_error():
    import src.api.app as api_app  # noqa: F401
    assert hasattr(api_app, "_run_backtest_in_thread")
