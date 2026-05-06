"""
Unit tests for GapDetector and GapBackfiller.

Tests cover:
- BarGap construction and validation
- GapDetector.find_gaps() — empty, single bar, no gaps, one gap, multiple gaps
- GapDetector.find_leading_gap()
- GapBackfillResult construction
- GapBackfiller.fill() with mocked REST client
- GapBackfiller.fill_all()
"""

from __future__ import annotations

import sys
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

_SRC = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from src.itm.data.gap_detector import BarGap, GapBackfillResult, GapDetector, GapBackfiller
from src.itm.data.realtime_bar_builder import BarInterval, OHLCVBar


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ts(h: int, m: int, s: int = 0) -> datetime:
    return datetime(2026, 5, 6, h, m, s, tzinfo=timezone.utc)


def _make_bar(ts: datetime, interval: BarInterval = BarInterval.ONE_MIN) -> OHLCVBar:
    return OHLCVBar(
        symbol="BTCUSDT",
        interval=interval,
        timestamp=ts,
        open=Decimal("95000"),
        high=Decimal("95100"),
        low=Decimal("94900"),
        close=Decimal("95050"),
        volume=Decimal("1.0"),
        volume_quote=Decimal("95000"),
        trade_count=10,
    )


def _bars_no_gaps(start: datetime, count: int, interval: BarInterval = BarInterval.ONE_MIN) -> list:
    step = timedelta(seconds=interval.seconds)
    return [_make_bar(start + step * i, interval) for i in range(count)]


# ---------------------------------------------------------------------------
# BarGap tests
# ---------------------------------------------------------------------------


class TestBarGap:
    def test_valid_gap(self):
        gap = BarGap(
            interval=BarInterval.ONE_MIN,
            gap_start=_ts(10, 5),
            gap_end=_ts(10, 7),
            missing_count=2,
        )
        assert gap.missing_count == 2

    def test_gap_start_after_end_raises(self):
        with pytest.raises(ValueError, match="gap_start"):
            BarGap(
                interval=BarInterval.ONE_MIN,
                gap_start=_ts(10, 7),
                gap_end=_ts(10, 5),
                missing_count=2,
            )

    def test_zero_missing_count_raises(self):
        with pytest.raises(ValueError, match="missing_count"):
            BarGap(
                interval=BarInterval.ONE_MIN,
                gap_start=_ts(10, 5),
                gap_end=_ts(10, 5),
                missing_count=0,
            )

    def test_repr(self):
        gap = BarGap(
            interval=BarInterval.ONE_MIN,
            gap_start=_ts(10, 5),
            gap_end=_ts(10, 7),
            missing_count=2,
        )
        r = repr(gap)
        assert "1m" in r
        assert "missing=2" in r


# ---------------------------------------------------------------------------
# GapDetector.find_gaps() tests
# ---------------------------------------------------------------------------


class TestGapDetectorFindGaps:
    def test_empty_list_returns_no_gaps(self):
        detector = GapDetector(BarInterval.ONE_MIN)
        assert detector.find_gaps([]) == []

    def test_single_bar_returns_no_gaps(self):
        detector = GapDetector(BarInterval.ONE_MIN)
        bars = [_make_bar(_ts(10, 5))]
        assert detector.find_gaps(bars) == []

    def test_consecutive_bars_no_gaps(self):
        detector = GapDetector(BarInterval.ONE_MIN)
        bars = _bars_no_gaps(_ts(10, 0), 10)
        assert detector.find_gaps(bars) == []

    def test_single_gap_detected(self):
        detector = GapDetector(BarInterval.ONE_MIN)
        # bars at 10:00, 10:01, (gap 10:02, 10:03), 10:04
        bars = [
            _make_bar(_ts(10, 0)),
            _make_bar(_ts(10, 1)),
            _make_bar(_ts(10, 4)),  # missing 10:02 and 10:03
        ]
        gaps = detector.find_gaps(bars)
        assert len(gaps) == 1
        assert gaps[0].gap_start == _ts(10, 2)
        assert gaps[0].gap_end == _ts(10, 3)
        assert gaps[0].missing_count == 2

    def test_multiple_gaps_detected(self):
        detector = GapDetector(BarInterval.ONE_MIN)
        # 10:00, 10:01, gap, 10:05, gap, 10:10
        bars = [
            _make_bar(_ts(10, 0)),
            _make_bar(_ts(10, 1)),
            _make_bar(_ts(10, 5)),
            _make_bar(_ts(10, 10)),
        ]
        gaps = detector.find_gaps(bars)
        assert len(gaps) == 2
        assert gaps[0].missing_count == 3  # 10:02, 10:03, 10:04
        assert gaps[1].missing_count == 4  # 10:06, 10:07, 10:08, 10:09

    def test_tolerance_suppresses_small_gaps(self):
        detector = GapDetector(BarInterval.ONE_MIN, tolerance_bars=1)
        bars = [
            _make_bar(_ts(10, 0)),
            _make_bar(_ts(10, 2)),  # 1 bar missing — within tolerance
        ]
        gaps = detector.find_gaps(bars)
        assert gaps == []

    def test_tolerance_does_not_suppress_large_gaps(self):
        detector = GapDetector(BarInterval.ONE_MIN, tolerance_bars=1)
        bars = [
            _make_bar(_ts(10, 0)),
            _make_bar(_ts(10, 5)),  # 4 bars missing — exceeds tolerance
        ]
        gaps = detector.find_gaps(bars)
        assert len(gaps) == 1

    def test_unsorted_input_still_works(self):
        detector = GapDetector(BarInterval.ONE_MIN)
        bars = [
            _make_bar(_ts(10, 4)),
            _make_bar(_ts(10, 0)),
            _make_bar(_ts(10, 1)),
        ]
        gaps = detector.find_gaps(bars)
        # Gap between 10:01 and 10:04 (10:02 and 10:03 missing)
        assert len(gaps) == 1
        assert gaps[0].missing_count == 2

    def test_fifteen_min_gap_detection(self):
        detector = GapDetector(BarInterval.FIFTEEN_MIN)
        bars = [
            _make_bar(_ts(10, 0), BarInterval.FIFTEEN_MIN),
            _make_bar(_ts(10, 15), BarInterval.FIFTEEN_MIN),
            _make_bar(_ts(11, 0), BarInterval.FIFTEEN_MIN),  # gap: 10:30 and 10:45
        ]
        gaps = detector.find_gaps(bars)
        assert len(gaps) == 1
        assert gaps[0].missing_count == 2


# ---------------------------------------------------------------------------
# GapBackfillResult tests
# ---------------------------------------------------------------------------


class TestGapBackfillResult:
    def test_bars_fetched_property(self):
        gap = BarGap(
            interval=BarInterval.ONE_MIN,
            gap_start=_ts(10, 5),
            gap_end=_ts(10, 6),
            missing_count=1,
        )
        bars = [_make_bar(_ts(10, 5))]
        result = GapBackfillResult(gap=gap, filled_bars=bars, success=True, source="binance_rest")
        assert result.bars_fetched == 1

    def test_default_success_is_false(self):
        gap = BarGap(
            interval=BarInterval.ONE_MIN,
            gap_start=_ts(10, 5),
            gap_end=_ts(10, 5),
            missing_count=1,
        )
        result = GapBackfillResult(gap=gap)
        assert result.success is False
        assert result.bars_fetched == 0


# ---------------------------------------------------------------------------
# GapBackfiller tests (with mocked REST client)
# ---------------------------------------------------------------------------


class TestGapBackfiller:
    def _make_gap(self, start: datetime, end: datetime, count: int) -> BarGap:
        return BarGap(
            interval=BarInterval.ONE_MIN,
            gap_start=start,
            gap_end=end,
            missing_count=count,
        )

    def _make_fake_kline_response(self, start: datetime, count: int) -> list:
        """Simulate Binance REST klines response format."""
        step = timedelta(minutes=1)
        result = []
        for i in range(count):
            ts = start + step * i
            ts_ms = int(ts.timestamp() * 1000)
            result.append([
                ts_ms,       # open_time
                "95000.0",   # open
                "95100.0",   # high
                "94900.0",   # low
                "95050.0",   # close
                "1.0",       # volume
                ts_ms + 59999, # close_time
                "95025.0",   # quote_volume
                10,          # trades
                "0.5",       # taker_buy_base
                "47500.0",   # taker_buy_quote
                "0",         # ignore
            ])
        return result

    def test_fill_success_via_binance_rest(self):
        gap = self._make_gap(_ts(10, 5), _ts(10, 6), 2)
        filler = GapBackfiller()

        fake_response = self._make_fake_kline_response(_ts(10, 5), 2)

        with patch.object(filler, "_fetch_binance_rest", return_value=[
            _make_bar(_ts(10, 5)),
            _make_bar(_ts(10, 6)),
        ]) as mock_fetch:
            result = filler.fill(gap)

        assert result.success is True
        assert result.bars_fetched == 2
        assert result.source == "binance_rest"

    def test_fill_falls_back_to_lakeapi_on_rest_failure(self):
        gap = self._make_gap(_ts(10, 5), _ts(10, 5), 1)
        mock_lakeapi = MagicMock()
        mock_lakeapi.get_bars.return_value = [{
            "timestamp": _ts(10, 5),
            "open": "95000",
            "high": "95100",
            "low": "94900",
            "close": "95050",
            "volume": "1.0",
            "volume_quote": "95025",
            "trade_count": 10,
        }]

        filler = GapBackfiller(lakeapi_client=mock_lakeapi)
        with patch.object(filler, "_fetch_binance_rest", side_effect=ConnectionError("oops")):
            result = filler.fill(gap)

        assert result.success is True
        assert result.source == "lakeapi"
        assert result.bars_fetched == 1

    def test_fill_returns_failure_when_both_sources_fail(self):
        gap = self._make_gap(_ts(10, 5), _ts(10, 5), 1)
        filler = GapBackfiller()
        with patch.object(filler, "_fetch_binance_rest", side_effect=ConnectionError("rest fail")):
            result = filler.fill(gap)

        assert result.success is False
        assert result.error is not None

    def test_fill_all_processes_multiple_gaps(self):
        filler = GapBackfiller()
        gaps = [
            self._make_gap(_ts(10, 5), _ts(10, 5), 1),
            self._make_gap(_ts(10, 10), _ts(10, 11), 2),
        ]
        with patch.object(filler, "_fetch_binance_rest", return_value=[]):
            results = filler.fill_all(gaps)

        assert len(results) == 2

    def test_lakeapi_not_called_when_rest_succeeds(self):
        gap = self._make_gap(_ts(10, 5), _ts(10, 5), 1)
        mock_lakeapi = MagicMock()
        filler = GapBackfiller(lakeapi_client=mock_lakeapi)

        with patch.object(filler, "_fetch_binance_rest", return_value=[_make_bar(_ts(10, 5))]):
            filler.fill(gap)

        mock_lakeapi.get_bars.assert_not_called()
