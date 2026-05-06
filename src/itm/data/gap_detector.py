"""
ITM Section B — Gap Detector & LakeAPI Backfill
================================================
Detects missing bars in the live OHLCV series and backfills gaps using the
Binance Futures REST API (via the existing ``BinanceRestClient``) or a
LakeAPI client when deep historical data is required.

Design
------
* ``GapDetector`` compares the expected bar sequence against the bars actually
  received and returns a list of :class:`BarGap` objects.
* ``GapBackfiller`` resolves each gap by fetching historical klines from the
  Binance REST API; it falls back to LakeAPI for gaps beyond Binance's
  ~1000-bar REST window.
* The combined ``GapDetector`` / ``GapBackfiller`` pipeline is synchronous and
  designed to run at startup (warm-up) and during brief reconnections.  For
  steady-state operation the WebSocket stream should be gap-free.

Gap definition
--------------
A gap exists when the difference between consecutive bar timestamps is greater
than one bar interval (accounting for 1-bar tolerance for race conditions).

LakeAPI note
------------
LakeAPI is the deep-history provider (referenced in the codebase via
``data_manager.download``).  When LakeAPI credentials are not available the
backfiller falls back to the Binance REST client's full klines endpoint, which
covers ~3 months of 1 m data.

Usage
-----
::

    detector = GapDetector(interval=BarInterval.ONE_MIN)
    gaps = detector.find_gaps(bars)   # bars: List[OHLCVBar]

    backfiller = GapBackfiller()
    result = backfiller.fill(gap)     # GapBackfillResult with filled bars

"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional

from .realtime_bar_builder import BarInterval, OHLCVBar

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BarGap:
    """Represents a contiguous block of missing bars.

    Attributes
    ----------
    interval:       Bar interval with the gap.
    gap_start:      Timestamp of the first missing bar (inclusive).
    gap_end:        Timestamp of the last missing bar (inclusive).
    missing_count:  Number of bars missing.
    """

    interval: BarInterval
    gap_start: datetime
    gap_end: datetime
    missing_count: int

    def __post_init__(self) -> None:
        if self.gap_start > self.gap_end:
            raise ValueError(
                f"BarGap: gap_start ({self.gap_start}) > gap_end ({self.gap_end})"
            )
        if self.missing_count < 1:
            raise ValueError("BarGap: missing_count must be at least 1")

    def __repr__(self) -> str:
        return (
            f"BarGap({self.interval.label}: "
            f"{self.gap_start:%Y-%m-%d %H:%M} → "
            f"{self.gap_end:%Y-%m-%d %H:%M}, "
            f"missing={self.missing_count})"
        )


@dataclass
class GapBackfillResult:
    """Result of a gap backfill attempt.

    Attributes
    ----------
    gap:            The :class:`BarGap` that was processed.
    filled_bars:    List of :class:`OHLCVBar` objects fetched to fill the gap.
    success:        True if the gap was fully resolved.
    source:         'binance_rest' or 'lakeapi' — where the data came from.
    error:          Error message if ``success`` is False.
    """

    gap: BarGap
    filled_bars: List[OHLCVBar] = field(default_factory=list)
    success: bool = False
    source: str = ""
    error: Optional[str] = None

    @property
    def bars_fetched(self) -> int:
        return len(self.filled_bars)


# ---------------------------------------------------------------------------
# GapDetector
# ---------------------------------------------------------------------------


class GapDetector:
    """Detects missing OHLCV bars in a sorted bar sequence.

    Parameters
    ----------
    interval:
        The :class:`BarInterval` to check.
    tolerance_bars:
        Number of consecutive missing bars below which a gap is ignored
        (default: 0 — report every gap).
    """

    def __init__(
        self,
        interval: BarInterval,
        tolerance_bars: int = 0,
    ) -> None:
        self.interval = interval
        self.tolerance_bars = tolerance_bars

    def find_gaps(self, bars: List[OHLCVBar]) -> List[BarGap]:
        """Return all gaps in *bars*.

        Parameters
        ----------
        bars:
            List of :class:`OHLCVBar` sorted by timestamp ascending.  The list
            need not be complete — the method only checks consecutive pairs.

        Returns
        -------
        List of :class:`BarGap`, ordered by ``gap_start``.
        """
        if len(bars) < 2:
            return []

        # Ensure bars are sorted
        sorted_bars = sorted(bars, key=lambda b: b.timestamp)
        step = timedelta(seconds=self.interval.seconds)
        gaps: List[BarGap] = []

        for i in range(1, len(sorted_bars)):
            prev_ts = sorted_bars[i - 1].timestamp
            curr_ts = sorted_bars[i].timestamp
            expected_next = prev_ts + step

            if curr_ts <= expected_next:
                continue  # no gap (or duplicate — skip)

            # Number of missing bars between prev and curr
            missing = int((curr_ts - expected_next) / step)
            if missing <= self.tolerance_bars:
                continue

            gap = BarGap(
                interval=self.interval,
                gap_start=expected_next,
                gap_end=curr_ts - step,
                missing_count=missing,
            )
            gaps.append(gap)
            logger.warning("Gap detected: %s", gap)

        if gaps:
            total_missing = sum(g.missing_count for g in gaps)
            logger.warning(
                "GapDetector found %d gap(s), %d total missing %s bars",
                len(gaps),
                total_missing,
                self.interval.label,
            )
        else:
            logger.debug(
                "GapDetector: no gaps in %d %s bars",
                len(sorted_bars),
                self.interval.label,
            )
        return gaps

    def find_leading_gap(
        self,
        bars: List[OHLCVBar],
        lookback_bars: int,
    ) -> Optional[BarGap]:
        """Check whether the bar series is missing bars at the front.

        Compares the timestamp of *bars[0]* against the expected start given a
        *lookback_bars* window.  Returns a :class:`BarGap` if leading bars are
        missing, else ``None``.

        Parameters
        ----------
        bars:
            List of OHLCVBar objects (sorted ascending).
        lookback_bars:
            How many bars back from the current time to expect.
        """
        if not bars:
            return None
        now_utc = datetime.now(timezone.utc)
        # Expected first bar timestamp
        from .realtime_bar_builder import _align_bar_open

        current_bar_open = _align_bar_open(now_utc, self.interval)
        step = timedelta(seconds=self.interval.seconds)
        expected_start = current_bar_open - step * lookback_bars

        actual_start = sorted(bars, key=lambda b: b.timestamp)[0].timestamp
        if actual_start <= expected_start:
            return None

        missing = int((actual_start - expected_start) / step)
        if missing <= self.tolerance_bars:
            return None

        return BarGap(
            interval=self.interval,
            gap_start=expected_start,
            gap_end=actual_start - step,
            missing_count=missing,
        )


# ---------------------------------------------------------------------------
# GapBackfiller
# ---------------------------------------------------------------------------


class GapBackfiller:
    """Fills :class:`BarGap` objects using Binance REST or LakeAPI.

    Strategy
    --------
    1. Attempt fill with the ``BinanceRestClient`` (free, no auth, fast).
       This covers gaps up to ~1000 bars per request.
    2. If the gap is too old for Binance REST (> 1000 1m bars ≈ ~16.7 h),
       fall back to LakeAPI.  If LakeAPI is unavailable, log a warning and
       return a partial result.

    Parameters
    ----------
    symbol:         Binance symbol (default: ``"BTCUSDT"``).
    use_futures:    Use Binance Futures klines (default: ``True`` for ITM).
    lakeapi_client: Optional LakeAPI client instance.  If ``None``, LakeAPI
                    backfill is skipped and Binance REST is the only source.
    max_bars_per_request:
                    Maximum bars to fetch in a single REST call (default: 1000).
    """

    # Binance REST max klines per request
    _BINANCE_MAX_KLINES = 1000

    def __init__(
        self,
        symbol: str = "BTCUSDT",
        use_futures: bool = True,
        lakeapi_client: Optional[object] = None,
        max_bars_per_request: int = 1000,
    ) -> None:
        self.symbol = symbol
        self.use_futures = use_futures
        self.lakeapi_client = lakeapi_client
        self.max_bars_per_request = max_bars_per_request

    def fill(self, gap: BarGap) -> GapBackfillResult:
        """Fetch bars to fill *gap*.

        Returns
        -------
        :class:`GapBackfillResult` with ``filled_bars`` and ``success`` flag.
        """
        logger.info("Backfilling gap: %s", gap)

        # Try Binance REST first
        try:
            bars = self._fetch_binance_rest(gap)
            if bars:
                logger.info(
                    "Backfill via Binance REST: fetched %d bars for %s",
                    len(bars),
                    gap,
                )
                return GapBackfillResult(
                    gap=gap,
                    filled_bars=bars,
                    success=len(bars) >= gap.missing_count,
                    source="binance_rest",
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Binance REST backfill failed: %s", exc)

        # Fall back to LakeAPI
        if self.lakeapi_client is not None:
            try:
                bars = self._fetch_lakeapi(gap)
                if bars:
                    logger.info(
                        "Backfill via LakeAPI: fetched %d bars for %s",
                        len(bars),
                        gap,
                    )
                    return GapBackfillResult(
                        gap=gap,
                        filled_bars=bars,
                        success=len(bars) >= gap.missing_count,
                        source="lakeapi",
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning("LakeAPI backfill failed: %s", exc)

        logger.error(
            "Unable to backfill gap %s (Binance REST and LakeAPI both failed)", gap
        )
        return GapBackfillResult(
            gap=gap,
            filled_bars=[],
            success=False,
            source="",
            error="All backfill sources exhausted",
        )

    def fill_all(self, gaps: List[BarGap]) -> List[GapBackfillResult]:
        """Fill multiple gaps in sequence.

        Returns a list of :class:`GapBackfillResult` in the same order as
        *gaps*.
        """
        results = []
        for gap in gaps:
            result = self.fill(gap)
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_binance_rest(self, gap: BarGap) -> List[OHLCVBar]:
        """Fetch klines from Binance REST to cover *gap*."""
        from ...data_manager.binance.rest_client import BinanceRestClient  # lazy import

        client = BinanceRestClient(use_testnet=False)

        interval_label = gap.interval.label  # e.g. "1m", "15m"
        start_ms = int(gap.gap_start.timestamp() * 1000)
        end_ms = int(
            (gap.gap_end + timedelta(seconds=gap.interval.seconds)).timestamp() * 1000
        )

        import pandas as pd  # noqa: PLC0415
        params: dict = {
            "symbol": self.symbol,
            "interval": interval_label,
            "limit": min(gap.missing_count + 1, self._BINANCE_MAX_KLINES),
        }
        params["startTime"] = start_ms
        params["endTime"] = end_ms

        # Use the internal _request method directly
        endpoint = "/fapi/v1/klines" if self.use_futures else "/api/v3/klines"
        raw = client._request(endpoint, params, futures=self.use_futures)

        bars: List[OHLCVBar] = []
        for candle in raw:
            ts = datetime.fromtimestamp(int(candle[0]) / 1000.0, tz=timezone.utc)
            bar = OHLCVBar(
                symbol=self.symbol,
                interval=gap.interval,
                timestamp=ts,
                open=Decimal(str(candle[1])),
                high=Decimal(str(candle[2])),
                low=Decimal(str(candle[3])),
                close=Decimal(str(candle[4])),
                volume=Decimal(str(candle[5])),
                volume_quote=Decimal(str(candle[7])),
                trade_count=int(candle[8]),
            )
            bars.append(bar)
        return bars

    def _fetch_lakeapi(self, gap: BarGap) -> List[OHLCVBar]:
        """Fetch klines from LakeAPI.

        The LakeAPI client interface is duck-typed; it must expose a method::

            client.get_bars(symbol, interval_label, start, end) -> List[dict]

        where each dict has keys: timestamp (datetime), open, high, low,
        close, volume (all Decimal-compatible).
        """
        if self.lakeapi_client is None:
            return []

        raw_bars = self.lakeapi_client.get_bars(
            symbol=self.symbol,
            interval=gap.interval.label,
            start=gap.gap_start,
            end=gap.gap_end,
        )
        bars: List[OHLCVBar] = []
        for rb in raw_bars:
            bar = OHLCVBar(
                symbol=self.symbol,
                interval=gap.interval,
                timestamp=rb["timestamp"],
                open=Decimal(str(rb["open"])),
                high=Decimal(str(rb["high"])),
                low=Decimal(str(rb["low"])),
                close=Decimal(str(rb["close"])),
                volume=Decimal(str(rb.get("volume", "0"))),
                volume_quote=Decimal(str(rb.get("volume_quote", "0"))),
                trade_count=int(rb.get("trade_count", 0)),
            )
            bars.append(bar)
        return bars
