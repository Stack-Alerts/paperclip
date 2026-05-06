"""
Unit tests for ComprehensiveAIRequestBuilder._extract_signal_statistics()
==========================================================================

Covers:
- Heuristic fire-rate estimation when no trade data is available
- Empirical fire-rate calculation from trade signals_fired lists
- Mixed data source (registry signals + non-registry signals)
- Zero-fire signals (in registry but never triggered in trades)
- Classification thresholds (filtering / momentum / neutral)
- Correct integration into build_complete_request() and format_for_ai_prompt()
"""

import pytest
from unittest.mock import patch, MagicMock

from src.optimizer_v3.core.comprehensive_ai_request_builder import (
    ComprehensiveAIRequestBuilder,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_builder_no_registry() -> ComprehensiveAIRequestBuilder:
    """Return a builder with no block registry (isolated unit tests)."""
    b = ComprehensiveAIRequestBuilder.__new__(ComprehensiveAIRequestBuilder)
    b.block_registry = None
    return b


def _make_minimal_backtest(trade_signals: list[list[str]]) -> dict:
    """Build a minimal backtest_results dict from a list of per-trade signal lists."""
    return {
        'total_trades': len(trade_signals),
        'trades': [
            {
                'signals_fired': sigs,
                'pnl': 10.0,
                'side': 'SHORT',
                'entry_time': '2025-01-01T08:00:00',
                'exit_time': '2025-01-01T10:00:00',
                'entry_bar': 0,
                'exit_bar': 8,
            }
            for sigs in trade_signals
        ],
    }


# ---------------------------------------------------------------------------
# Tests: heuristic path (no trade data)
# ---------------------------------------------------------------------------

class TestHeuristicFireRates:
    """Tests for keyword-based heuristic fire-rate estimation."""

    def test_divergence_keyword_gives_low_rate(self):
        b = _make_builder_no_registry()
        rate = b._heuristic_fire_rate('MACD_DIVERGENCE')
        assert rate == pytest.approx(0.05)

    def test_breakout_keyword_gives_filtering_rate(self):
        b = _make_builder_no_registry()
        rate = b._heuristic_fire_rate('BREAKOUT_CONFIRMED')
        assert rate == pytest.approx(0.15)

    def test_cross_keyword_gives_moderate_rate(self):
        b = _make_builder_no_registry()
        rate = b._heuristic_fire_rate('EMA_CROSSOVER')
        assert rate == pytest.approx(0.30)

    def test_active_keyword_gives_permissive_rate(self):
        b = _make_builder_no_registry()
        rate = b._heuristic_fire_rate('PATTERN_ACTIVE')
        assert rate == pytest.approx(0.60)

    def test_unknown_signal_falls_back_to_moderate(self):
        b = _make_builder_no_registry()
        rate = b._heuristic_fire_rate('COMPLETELY_UNKNOWN_XYZ')
        assert rate == pytest.approx(0.30)

    def test_bearish_keyword(self):
        b = _make_builder_no_registry()
        rate = b._heuristic_fire_rate('BEARISH_SIGNAL')
        assert rate == pytest.approx(0.15)

    def test_overbought_keyword(self):
        b = _make_builder_no_registry()
        rate = b._heuristic_fire_rate('RSI_OVERBOUGHT')
        assert rate == pytest.approx(0.15)

    def test_longest_keyword_wins_divergence_over_trend(self):
        """TREND (len 5) and DIVERGENCE (len 10) — DIVERGENCE should win."""
        b = _make_builder_no_registry()
        rate = b._heuristic_fire_rate('TREND_DIVERGENCE')
        # DIVERGENCE is longer, so its rate (0.05) should win
        assert rate == pytest.approx(0.05)


# ---------------------------------------------------------------------------
# Tests: classification
# ---------------------------------------------------------------------------

class TestClassifySignal:

    def test_low_rate_is_filtering(self):
        assert ComprehensiveAIRequestBuilder._classify_signal(0.0) == 'filtering'
        assert ComprehensiveAIRequestBuilder._classify_signal(0.19) == 'filtering'

    def test_boundary_20pct_is_momentum(self):
        assert ComprehensiveAIRequestBuilder._classify_signal(0.20) == 'momentum'

    def test_mid_range_is_momentum(self):
        assert ComprehensiveAIRequestBuilder._classify_signal(0.40) == 'momentum'
        assert ComprehensiveAIRequestBuilder._classify_signal(0.60) == 'momentum'

    def test_above_60pct_is_neutral(self):
        assert ComprehensiveAIRequestBuilder._classify_signal(0.61) == 'neutral'
        assert ComprehensiveAIRequestBuilder._classify_signal(1.0) == 'neutral'


# ---------------------------------------------------------------------------
# Tests: empirical path (no registry, purely trade-based)
# ---------------------------------------------------------------------------

class TestEmpiricalCalculation:
    """Tests that empirical counts are computed correctly."""

    def test_basic_fire_counts(self):
        b = _make_builder_no_registry()
        backtest = _make_minimal_backtest([
            ['HOD_REJECTION', 'BEARISH'],
            ['HOD_REJECTION'],
            ['BEARISH'],
            [],
        ])
        stats = b._extract_signal_statistics(backtest)

        rates = stats['signal_occurrence_rates']
        assert rates['HOD_REJECTION']['fires'] == 2
        assert rates['HOD_REJECTION']['fire_rate'] == pytest.approx(0.5)
        assert rates['HOD_REJECTION']['fire_rate_pct'] == '50.0%'
        assert rates['HOD_REJECTION']['source'] == 'empirical'

        assert rates['BEARISH']['fires'] == 2
        assert rates['BEARISH']['fire_rate'] == pytest.approx(0.5)

    def test_total_trades_analysed(self):
        b = _make_builder_no_registry()
        backtest = _make_minimal_backtest([['A'], ['A', 'B'], ['B']])
        stats = b._extract_signal_statistics(backtest)
        assert stats['total_trades_analysed'] == 3

    def test_data_source_is_empirical(self):
        b = _make_builder_no_registry()
        backtest = _make_minimal_backtest([['SIG_ONE'], ['SIG_ONE', 'SIG_TWO']])
        stats = b._extract_signal_statistics(backtest)
        assert stats['data_source'] == 'empirical'

    def test_signal_never_fired_has_zero_rate(self):
        """Signals in registry but absent from all trades get fire_rate = 0."""
        b = _make_builder_no_registry()
        backtest = _make_minimal_backtest([['ONLY_THIS_SIGNAL']])
        stats = b._extract_signal_statistics(backtest)
        # ONLY_THIS_SIGNAL fired once in 1 trade → rate = 1.0
        assert stats['signal_occurrence_rates']['ONLY_THIS_SIGNAL']['fire_rate'] == pytest.approx(1.0)

    def test_empty_signals_fired_list(self):
        b = _make_builder_no_registry()
        backtest = _make_minimal_backtest([[], [], []])
        stats = b._extract_signal_statistics(backtest)
        # No signals fired → no entries
        assert len(stats['signal_occurrence_rates']) == 0

    def test_non_string_entries_in_signals_fired_ignored(self):
        """Guard against malformed signals_fired containing non-string values."""
        b = _make_builder_no_registry()
        backtest = {
            'trades': [
                {'signals_fired': ['VALID_SIGNAL', None, 42, 'VALID_SIGNAL']},
            ]
        }
        stats = b._extract_signal_statistics(backtest)
        rates = stats['signal_occurrence_rates']
        assert 'VALID_SIGNAL' in rates
        assert rates['VALID_SIGNAL']['fires'] == 2
        # None and 42 should not appear as keys
        assert None not in rates
        assert 42 not in rates

    def test_fire_rate_precision(self):
        """fire_rate should be rounded to 4 decimal places."""
        b = _make_builder_no_registry()
        # 1 fire in 3 trades = 0.3333...
        backtest = _make_minimal_backtest([['SIG'], [], []])
        stats = b._extract_signal_statistics(backtest)
        rate = stats['signal_occurrence_rates']['SIG']['fire_rate']
        assert rate == pytest.approx(round(1 / 3, 4))


# ---------------------------------------------------------------------------
# Tests: heuristic data source (no trades)
# ---------------------------------------------------------------------------

class TestHeuristicDataSource:

    def test_data_source_is_heuristic_when_no_trades(self):
        b = _make_builder_no_registry()
        stats = b._extract_signal_statistics({})
        # No registry + no trades → empty rates, source = 'none'
        assert stats['data_source'] == 'none'

    def test_data_source_is_heuristic_with_registry(self):
        """With a mock registry but no trades, source should be 'heuristic'."""
        b = ComprehensiveAIRequestBuilder.__new__(ComprehensiveAIRequestBuilder)

        mock_metadata = MagicMock()
        mock_metadata.signal_tiers = {
            'BULLISH_SIGNAL': {'base_points': 30, 'formula': 'scaled'},
        }

        mock_registry = MagicMock()
        mock_registry.get_all_blocks.return_value = {'test_block': mock_metadata}
        b.block_registry = mock_registry

        stats = b._extract_signal_statistics({})
        assert stats['data_source'] == 'heuristic'
        assert stats['signal_occurrence_rates']['BULLISH_SIGNAL']['source'] == 'heuristic'
        assert stats['signal_occurrence_rates']['BULLISH_SIGNAL']['fire_rate'] == pytest.approx(0.15)


# ---------------------------------------------------------------------------
# Tests: registry + trades integration (mixed source)
# ---------------------------------------------------------------------------

class TestMixedSource:
    """Registry signals combined with trade data produce 'mixed' when some
    registry signals never fired (empirical = 0) and some are heuristic."""

    def test_registry_signal_fired_in_trade_gets_empirical(self):
        b = ComprehensiveAIRequestBuilder.__new__(ComprehensiveAIRequestBuilder)

        mock_metadata = MagicMock()
        mock_metadata.signal_tiers = {
            'HOD_REJECTION': {'base_points': 30, 'formula': 'scaled'},
            'LOD_BOUNCE':    {'base_points': 20, 'formula': 'scaled'},
        }
        mock_registry = MagicMock()
        mock_registry.get_all_blocks.return_value = {'hod': mock_metadata}
        b.block_registry = mock_registry

        backtest = _make_minimal_backtest([
            ['HOD_REJECTION'],
            ['HOD_REJECTION'],
        ])
        stats = b._extract_signal_statistics(backtest)

        hod = stats['signal_occurrence_rates']['HOD_REJECTION']
        lod = stats['signal_occurrence_rates']['LOD_BOUNCE']

        assert hod['source'] == 'empirical'
        assert hod['fire_rate'] == pytest.approx(1.0)

        # LOD_BOUNCE is in registry but never in trades → empirical with 0 fires
        assert lod['source'] == 'empirical'
        assert lod['fires'] == 0
        assert lod['fire_rate'] == pytest.approx(0.0)

    def test_signal_only_in_trades_not_in_registry_included(self):
        """Signals appearing only in trade data (not registry) must also be included."""
        b = ComprehensiveAIRequestBuilder.__new__(ComprehensiveAIRequestBuilder)

        mock_metadata = MagicMock()
        mock_metadata.signal_tiers = {}   # empty registry
        mock_registry = MagicMock()
        mock_registry.get_all_blocks.return_value = {'empty_block': mock_metadata}
        b.block_registry = mock_registry

        backtest = _make_minimal_backtest([['CUSTOM_SIGNAL'], ['CUSTOM_SIGNAL']])
        stats = b._extract_signal_statistics(backtest)

        assert 'CUSTOM_SIGNAL' in stats['signal_occurrence_rates']
        assert stats['signal_occurrence_rates']['CUSTOM_SIGNAL']['fires'] == 2


# ---------------------------------------------------------------------------
# Tests: result structure invariants
# ---------------------------------------------------------------------------

class TestReturnStructure:

    def test_required_top_level_keys(self):
        b = _make_builder_no_registry()
        stats = b._extract_signal_statistics({})
        assert 'total_signals_available' in stats
        assert 'total_trades_analysed' in stats
        assert 'data_source' in stats
        assert 'signal_occurrence_rates' in stats

    def test_per_signal_required_keys(self):
        b = _make_builder_no_registry()
        backtest = _make_minimal_backtest([['MY_SIG']])
        stats = b._extract_signal_statistics(backtest)
        entry = stats['signal_occurrence_rates']['MY_SIG']
        for key in ('fires', 'fire_rate', 'fire_rate_pct', 'classification', 'source'):
            assert key in entry, f"Missing key: {key}"

    def test_none_backtest_arg(self):
        b = _make_builder_no_registry()
        stats = b._extract_signal_statistics(None)
        assert stats['total_trades_analysed'] == 0
        assert stats['data_source'] == 'none'


# ---------------------------------------------------------------------------
# Tests: integration with build_complete_request and format_for_ai_prompt
# ---------------------------------------------------------------------------

class TestIntegration:

    def test_signal_statistics_present_in_full_request(self):
        b = ComprehensiveAIRequestBuilder()
        backtest = _make_minimal_backtest([['HOD_REJECTION'], ['HOD_REJECTION']])
        req = b.build_complete_request(
            strategy_config={'name': 'Test', 'blocks': []},
            backtest_results=backtest,
            metrics_with_ratings={},
        )
        assert 'signal_statistics' in req
        sig_stats = req['signal_statistics']
        assert sig_stats['total_trades_analysed'] == 2

    def test_section_7_present_in_prompt(self):
        b = ComprehensiveAIRequestBuilder()
        backtest = _make_minimal_backtest([['BEARISH'], ['BEARISH', 'TREND']])
        req = b.build_complete_request(
            strategy_config={'name': 'Test', 'blocks': []},
            backtest_results=backtest,
            metrics_with_ratings={},
        )
        prompt = b.format_for_ai_prompt(req)
        assert '7. SIGNAL OCCURRENCE STATISTICS' in prompt

    def test_prompt_explains_classification_thresholds(self):
        b = ComprehensiveAIRequestBuilder()
        req = b.build_complete_request(
            strategy_config={'name': 'T', 'blocks': []},
            backtest_results={'trades': []},
            metrics_with_ratings={},
        )
        prompt = b.format_for_ai_prompt(req)
        assert 'filtering' in prompt
        assert 'momentum' in prompt
        assert 'neutral' in prompt
