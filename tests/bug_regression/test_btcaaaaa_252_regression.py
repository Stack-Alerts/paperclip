"""
Regression tests for BTCAAAAA-252: Strategy Configuration Retention.

Issue: BTCAAAAA-252
Component: src/strategy_builder/ui/backtest_config_panel.py
           src/optimizer_v3/database/strategy_manager.py

Fix: Persist backtest config to DB so it survives app restart.
  - save_backtest_config_for_version() — DB layer helper
  - update_strategy_version() extended with backtest_config + validation_status
  - apply_config_from_dict() — restore panel widgets from persisted dict
  - _mark_config_retained() — UI label helper

This file replicates the mock-based tests that do NOT require a live database.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-252"),
    pytest.mark.regression,
]


FULL_BACKTEST_CONFIG = {
    'lookback_days': 180,
    'mode': 2,
    'tpsl_mode': 'Fibonacci',
    'sl_mode': 'Adaptive v2.0',
    'starting_capital': 10000,
    'risk_per_trade_pct': 1.5,
    'min_risk_reward': 1.5,
    'max_leverage': 1.0,
    'confluence_threshold': 3,
    'max_bars_held': 200,
    'adaptive_sl': {
        'delay_enabled': True,
        'delay_bars': 5,
        'emergency_sl_pct': 1.5,
        'volatility_lookback': 20,
        'volatility_multiplier': 1.2,
        'min_sl_pct': 0.7,
        'max_sl_pct': 2.0,
        'use_structure_sl': False,
    },
}


def _make_mock_panel():
    from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
    panel = MagicMock()
    panel._loading_preset = False
    panel.config_retention_label = MagicMock()
    for attr in [
        'lookback_spin', 'capital_spin', 'risk_spin', 'rr_spin',
        'leverage_spin', 'confluence_spin', 'max_bars_spin',
        'training_spin', 'testing_spin',
        'delay_spin', 'emergency_spin', 'vol_lookback_spin',
        'vol_multi_spin', 'min_sl_spin', 'max_sl_spin',
    ]:
        setattr(panel, attr, MagicMock())
    for attr in ['tpsl_combo', 'sl_combo']:
        setattr(panel, attr, MagicMock())
    for attr in ['delayed_sl_check', 'structure_check']:
        setattr(panel, attr, MagicMock())
    mock_btn = MagicMock()
    panel.mode_group = MagicMock()
    panel.mode_group.button.return_value = mock_btn
    panel.apply_config_from_dict = lambda saved, source='database': (
        BacktestConfigPanel.apply_config_from_dict(panel, saved, source)
    )
    return panel


class TestApplyConfigFromDict:
    """Tests for BacktestConfigPanel.apply_config_from_dict()."""

    def test_returns_false_on_empty_dict(self):
        panel = _make_mock_panel()
        assert panel.apply_config_from_dict({}) is False

    def test_returns_false_on_none(self):
        panel = _make_mock_panel()
        assert panel.apply_config_from_dict(None) is False

    def test_returns_true_when_fields_applied(self):
        panel = _make_mock_panel()
        result = panel.apply_config_from_dict({'lookback_days': 90})
        assert result is True

    def test_lookback_days_restored(self):
        panel = _make_mock_panel()
        panel.apply_config_from_dict({'lookback_days': 180})
        panel.lookback_spin.setValue.assert_called_once_with(180)

    def test_mode_restored(self):
        panel = _make_mock_panel()
        panel.apply_config_from_dict({'mode': 2})
        panel.mode_group.button.assert_called_once_with(2)
        panel.mode_group.button.return_value.setChecked.assert_called_once_with(True)

    def test_tpsl_mode_restored(self):
        panel = _make_mock_panel()
        panel.apply_config_from_dict({'tpsl_mode': 'Hybrid'})
        panel.tpsl_combo.setCurrentText.assert_called_once_with('Hybrid')

    def test_sl_mode_restored(self):
        panel = _make_mock_panel()
        panel.apply_config_from_dict({'sl_mode': 'Static'})
        panel.sl_combo.setCurrentText.assert_called_once_with('Static')

    def test_starting_capital_restored(self):
        panel = _make_mock_panel()
        panel.apply_config_from_dict({'starting_capital': 25000})
        panel.capital_spin.setValue.assert_called_once_with(25000.0)

    def test_risk_per_trade_restored(self):
        panel = _make_mock_panel()
        panel.apply_config_from_dict({'risk_per_trade_pct': 2.0})
        panel.risk_spin.setValue.assert_called_once_with(2.0)

    def test_min_risk_reward_10x_scaled(self):
        panel = _make_mock_panel()
        panel.apply_config_from_dict({'min_risk_reward': 1.5})
        panel.rr_spin.setValue.assert_called_once_with(15.0)

    def test_max_leverage_restored(self):
        panel = _make_mock_panel()
        panel.apply_config_from_dict({'max_leverage': 1.0})
        panel.leverage_spin.setValue.assert_called_once_with(1.0)

    def test_confluence_threshold_restored(self):
        panel = _make_mock_panel()
        panel.apply_config_from_dict({'confluence_threshold': 4})
        panel.confluence_spin.setValue.assert_called_once_with(4.0)

    def test_max_bars_held_restored(self):
        panel = _make_mock_panel()
        panel.apply_config_from_dict({'max_bars_held': 150})
        panel.max_bars_spin.setValue.assert_called_once_with(150)

    def test_training_window_restored(self):
        panel = _make_mock_panel()
        panel.apply_config_from_dict({'training_window': 60})
        panel.training_spin.setValue.assert_called_once_with(60)

    def test_testing_window_restored(self):
        panel = _make_mock_panel()
        panel.apply_config_from_dict({'testing_window': 30})
        panel.testing_spin.setValue.assert_called_once_with(30)

    def test_adaptive_sl_delay_enabled_restored(self):
        panel = _make_mock_panel()
        panel.apply_config_from_dict({'adaptive_sl': {'delay_enabled': True}})
        panel.delayed_sl_check.setChecked.assert_called_once_with(True)

    def test_adaptive_sl_delay_bars_restored(self):
        panel = _make_mock_panel()
        panel.apply_config_from_dict({'adaptive_sl': {'delay_bars': 7}})
        panel.delay_spin.setValue.assert_called_once_with(7)

    def test_adaptive_sl_volatility_multiplier_restored(self):
        panel = _make_mock_panel()
        panel.apply_config_from_dict({'adaptive_sl': {'volatility_multiplier': 1.8}})
        panel.vol_multi_spin.setValue.assert_called_once_with(1.8)

    def test_adaptive_sl_min_max_sl_restored(self):
        panel = _make_mock_panel()
        panel.apply_config_from_dict({
            'adaptive_sl': {'min_sl_pct': 0.5, 'max_sl_pct': 3.0}
        })
        panel.min_sl_spin.setValue.assert_called_once_with(0.5)
        panel.max_sl_spin.setValue.assert_called_once_with(3.0)

    def test_full_config_restores_all_widgets(self):
        panel = _make_mock_panel()
        result = panel.apply_config_from_dict(FULL_BACKTEST_CONFIG)
        assert result is True
        panel.lookback_spin.setValue.assert_called()
        panel.tpsl_combo.setCurrentText.assert_called()
        panel.capital_spin.setValue.assert_called()
        panel.vol_multi_spin.setValue.assert_called()

    def test_metadata_keys_ignored_gracefully(self):
        panel = _make_mock_panel()
        config = {
            'lookback_days': 90,
            '_saved_at': '2026-05-06T10:00:00',
            '_save_source': 'test_run',
        }
        result = panel.apply_config_from_dict(config, source='database')
        assert result is True

    def test_loading_preset_flag_reset_after_apply(self):
        panel = _make_mock_panel()
        panel.tpsl_combo.setCurrentText.side_effect = RuntimeError("widget error")
        try:
            panel.apply_config_from_dict({'tpsl_mode': 'Fibonacci'})
        except Exception:
            pass
        assert panel._loading_preset is False

    def test_mark_config_retained_called_on_apply(self):
        panel = _make_mock_panel()
        panel.apply_config_from_dict({'lookback_days': 60})
        panel._mark_config_retained.assert_called_once_with('database')


class TestMarkConfigRetained:
    """Tests for BacktestConfigPanel._mark_config_retained()."""

    def _make_mock_panel(self):
        panel = MagicMock()
        panel.config_retention_label = MagicMock()
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        panel._mark_config_retained = lambda source='database': (
            BacktestConfigPanel._mark_config_retained(panel, source)
        )
        return panel

    def test_label_made_visible(self):
        panel = self._make_mock_panel()
        panel._mark_config_retained('test run')
        panel.config_retention_label.setVisible.assert_called_once_with(True)

    def test_label_text_set_for_test_run(self):
        panel = self._make_mock_panel()
        panel._mark_config_retained('test run')
        call_args = panel.config_retention_label.setText.call_args[0][0]
        assert 'saved' in call_args.lower()

    def test_label_text_set_for_database(self):
        panel = self._make_mock_panel()
        panel._mark_config_retained('database')
        call_args = panel.config_retention_label.setText.call_args[0][0]
        assert 'restored' in call_args.lower() or 'Config' in call_args

    def test_label_text_set_for_config_discovery(self):
        panel = self._make_mock_panel()
        panel._mark_config_retained('config discovery')
        call_args = panel.config_retention_label.setText.call_args[0][0]
        assert 'discovery' in call_args.lower() or 'saved' in call_args.lower()

    def test_does_not_raise_on_missing_label(self):
        panel = MagicMock(spec=[])
        panel.output_panel = None
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        BacktestConfigPanel._mark_config_retained(panel, 'test run')


class TestSaveBacktestConfigForVersion:
    """Unit tests for StrategyDatabaseManager.save_backtest_config_for_version()
    using mocked DB session (no real database)."""

    def test_returns_true_on_success(self):
        from src.optimizer_v3.database.strategy_manager import StrategyDatabaseManager
        mock_session = MagicMock()
        mock_execute = MagicMock()
        mock_session.execute.return_value = mock_execute
        mock_execute.rowcount = 1
        manager = StrategyDatabaseManager(mock_session)

        result = manager.save_backtest_config_for_version(
            'test-version-id', {'lookback_days': 90}, source='test_run'
        )
        assert result is True

    def test_returns_false_for_unknown_version(self):
        from src.optimizer_v3.database.strategy_manager import StrategyDatabaseManager
        mock_session = MagicMock()
        mock_execute = MagicMock()
        mock_session.execute.return_value = mock_execute
        mock_execute.rowcount = 0
        manager = StrategyDatabaseManager(mock_session)

        result = manager.save_backtest_config_for_version(
            'fake-version-id', {'lookback_days': 30}, source='test_run'
        )
        assert result is False

    def test_update_backtest_config_allowed_field(self):
        from src.optimizer_v3.database.strategy_manager import StrategyDatabaseManager
        mock_session = MagicMock()
        mock_session.execute.return_value.rowcount = 1
        manager = StrategyDatabaseManager(mock_session)

        result = manager.update_strategy_version(
            'test-version-id', {'backtest_config': {'lookback_days': 50}}
        )
        assert result is True

    def test_update_validation_status_allowed_field(self):
        from src.optimizer_v3.database.strategy_manager import StrategyDatabaseManager
        mock_session = MagicMock()
        mock_session.execute.return_value.rowcount = 1
        manager = StrategyDatabaseManager(mock_session)

        result = manager.update_strategy_version(
            'test-version-id', {'validation_status': 'passed'}
        )
        assert result is True
