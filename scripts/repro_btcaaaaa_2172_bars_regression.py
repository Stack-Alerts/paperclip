"""
Repro: BTCAAAAA-2172 — bars-loaded pipeline (30/30/30 → 1,500 bars regression)

Demonstrates that _get_bars_binance() always returns at most 1,500 bars
regardless of how large a date window is requested, because it calls
Binance with limit=1500 and NO startTime parameter.

Run with:
    python scripts/repro_btcaaaaa_2172_bars_regression.py

Expected output (the regression):
    [ROUTING]  start_date=2026-02-11 threshold=2026-04-12 → route=binance
    [RESULT]   bars loaded: 1500 (expected ~2880 for 30 days of 15m)

Expected output (the correct hybrid path that produces ~8632 bars):
    [ROUTING]  start_date=2026-02-11 threshold=2026-04-12 → route=auto
    [RESULT]   bars loaded: 8632 (covers full 90-day window via local files)
"""

import sys
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("repro_2172")


def demonstrate_routing_decision():
    """Show how _determine_source() routes for lookback_days=30."""
    from datetime import datetime, timedelta, timezone

    # Simulate get_config() — called BEFORE the worker thread starts
    T0 = datetime.now()
    lookback_days = 30
    end_date_config = T0
    start_date_config = end_date_config - timedelta(days=lookback_days)
    logger.info(f"[CONFIG]   T0={T0}, start_date={start_date_config.date()}, end_date={end_date_config.date()}")

    # Simulate _get_bars_by_range() → _determine_source() — called inside worker thread
    # (potentially milliseconds to seconds later)
    import time as _time
    _time.sleep(0.001)  # Simulated scheduling delay

    T1 = datetime.now(timezone.utc)
    binance_threshold_days = 30
    threshold = T1 - timedelta(days=binance_threshold_days)

    # Normalize start_date to UTC-aware (done in _get_bars_by_range line 432-433)
    start_date_norm = start_date_config.replace(tzinfo=timezone.utc)
    end_date_norm = end_date_config.replace(tzinfo=timezone.utc)

    # _determine_source() logic (unified_manager.py:284-310)
    if end_date_norm < threshold:
        route = "lakeapi"
    elif start_date_norm >= threshold:
        route = "binance"
    else:
        route = "auto (hybrid)"

    logger.info(f"[ROUTING]  T1={T1}, threshold={threshold.date()}")
    logger.info(f"[ROUTING]  start_date={start_date_norm.date()} >= threshold={threshold.date()} ? {start_date_norm >= threshold}")
    logger.info(f"[ROUTING]  → route={route}")

    if route == "binance":
        logger.warning(
            "[BUG]     _get_bars_binance() will be called. It always uses limit=1500 "
            "with NO startTime. Binance returns only the most recent 1,500 bars "
            "(~15.6 days at 15m). A 30-day window needs ~2,880 bars. Result: TRUNCATED."
        )
    return route, start_date_config, end_date_config


def demonstrate_binance_truncation(start_date, end_date):
    """Show the Binance API returns only 1,500 bars regardless of window size."""
    from src.data_manager.unified_manager import UnifiedDataManager, DataSource

    manager = UnifiedDataManager(mode='backtest')
    logger.info(f"[BINANCE]  Requesting bars {start_date.date()} → {end_date.date()}")

    expected_bars = 30 * 24 * 4  # 30 days × 96 bars/day at 15m = 2880
    logger.info(f"[BINANCE]  Expected: ~{expected_bars} bars for 30 days at 15m")

    try:
        # Force the Binance path directly (bypassing routing)
        bars = manager._get_bars_binance('15m', start_date, end_date)
        actual = len(bars)
        logger.info(f"[BINANCE]  Actual:   {actual} bars")

        if actual <= 1500:
            logger.error(
                f"[REGRESSION CONFIRMED] Got {actual} bars (≤ 1500 API limit). "
                f"Missing {expected_bars - actual} bars ({(expected_bars - actual) / expected_bars * 100:.0f}%)."
            )
        else:
            logger.info(f"[OK]  Got {actual} bars — above 1,500 cap. Binance may have paginated.")
    except Exception as e:
        logger.warning(f"[BINANCE]  Skipped (no network/API key): {e}")


def demonstrate_hybrid_path(start_date_90, end_date):
    """Show the hybrid/local-files path returns full data when available."""
    from src.data_manager.unified_manager import UnifiedDataManager, DataSource

    manager = UnifiedDataManager(mode='backtest')
    logger.info(f"[HYBRID]   Requesting bars {start_date_90.date()} → {end_date.date()} (90-day window)")

    try:
        bars = manager._get_bars_by_range(
            '15m', start_date_90, end_date.replace(tzinfo=timezone.utc), DataSource.AUTO
        )
        actual = len(bars)
        logger.info(f"[HYBRID]   Actual:   {actual} bars")
        if actual >= 8000:
            logger.info(f"[HYBRID]   → Hybrid path successfully loaded ~{actual/96:.0f} days of data.")
        else:
            logger.warning(f"[HYBRID]   → Only {actual} bars; local parquet files may not cover full 90 days.")
    except Exception as e:
        logger.warning(f"[HYBRID]   Could not load: {e}")


def demonstrate_cache_poisoning(start_date, end_date):
    """Show the day-boundary cache hash causes subsequent runs to reuse 1,500 bars."""
    from src.optimizer_v3.core.data_cache_manager import DataCacheManager

    cm = DataCacheManager()
    config = {
        'lookback_days': 30,
        'timeframe': '15m',
        'start_date': start_date,
        'end_date': end_date,
    }

    # Simulate first run: cache 1,500 (truncated) bars
    truncated_bars = [object()] * 1500  # Placeholder objects
    cm.cache_bars(truncated_bars, config)
    hash1 = cm.get_config_hash(config)
    logger.info(f"[CACHE]    Run 1 hash: {hash1} → cached 1,500 bars")

    # Simulate second run on same day (slightly different timestamp)
    import time as _time; _time.sleep(0.001)
    config2 = dict(config)
    config2['start_date'] = datetime.now() - timedelta(days=30)
    config2['end_date'] = datetime.now()
    hash2 = cm.get_config_hash(config2)
    hit = cm.get_cached_bars(config2)

    logger.info(f"[CACHE]    Run 2 hash: {hash2} → cache {'HIT' if hit else 'MISS'}")
    if hit:
        logger.error(
            f"[CACHE POISON CONFIRMED] Run 2 reuses {len(hit):,} bars from Run 1's truncated load. "
            "Date rounding to day boundaries causes same-day runs to always cache-hit."
        )


if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("REPRO: BTCAAAAA-2172 bars-loaded pipeline regression (30/30/30 → 1,500)")
    logger.info("=" * 70)

    # Step 1: Demonstrate routing
    route, start_date, end_date = demonstrate_routing_decision()

    # Step 2: Demonstrate Binance truncation (requires network + API key; skips gracefully)
    logger.info("-" * 70)
    demonstrate_binance_truncation(start_date, end_date)

    # Step 3: Demonstrate hybrid path (requires local parquet files)
    logger.info("-" * 70)
    start_date_90 = end_date - timedelta(days=90)
    demonstrate_hybrid_path(start_date_90, end_date)

    # Step 4: Demonstrate cache poisoning
    logger.info("-" * 70)
    demonstrate_cache_poisoning(start_date, end_date)

    logger.info("=" * 70)
    logger.info("Root cause: unified_manager.py:529 — limit=1500 with no startTime")
    logger.info("Cache amplifier: data_cache_manager.py:99-103 — day-boundary rounding")
    logger.info("=" * 70)
