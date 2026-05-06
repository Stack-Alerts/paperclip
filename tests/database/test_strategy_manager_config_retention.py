"""
Unit tests for Strategy Configuration Retention  (BTCAAAAA-252 / BTCAAAAA-253)

Covers:
  - save_backtest_config_for_version()   — DB layer helper
  - update_strategy_version() extension  — backtest_config + validation_status
  - apply_config_from_dict()             — BacktestConfigPanel restore logic
  - _mark_config_retained()              — UI label helper

Tests run against a real PostgreSQL session fixture (via conftest.py) and rely on
the standard transaction-rollback isolation pattern so no permanent rows are written.

Note: Tests that call get_strategy_version() are deliberately avoided here because
that method does session.rollback() internally which breaks the fixture's nested
transaction.  We instead verify persistence by querying directly with SQLAlchemy.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_VERSION_DATA = {
    'name': 'Config Retention Test Version',
    'description': 'QA test version for BTCAAAAA-253',
    'blocks': [{'name': 'test_block', 'signals': [], 'parameters': {}}],
    'signals': {},
    'parameters': {'param1': 10},
    'entry_conditions': {},
    'exit_conditions': [],
    'risk_management': {'max_position': 1.0, 'stop_loss': 0.02},
    'backtest_config': {'lookback_days': 90, 'mode': 2},
}

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
        'enabled': True,
        'delay_enabled': True,
        'delay_bars': 5,
        'emergency_sl_pct': 1.5,
        'volatility_lookback': 20,
        'volatility_multiplier': 1.2,
        'min_sl_pct': 0.7,
        'max_sl_pct': 2.0,
        'use_structure_sl': False,
        'structure_sources': ['swing_points', 'supply_demand', 'fibonacci'],
    },
}


# ---------------------------------------------------------------------------
# DB-layer tests: save_backtest_config_for_version
# ---------------------------------------------------------------------------

class TestSaveBacktestConfigForVersion:
    """Tests for StrategyDatabaseManager.save_backtest_config_for_version()"""

    @pytest.fixture
    def manager(self, db_session):
        from src.optimizer_v3.database.strategy_manager import StrategyDatabaseManager
        return StrategyDatabaseManager(db_session)

    @pytest.fixture
    def strategy_id(self, manager):
        return manager.create_strategy("QA Config Retention Strategy")

    @pytest.fixture
    def version_id(self, manager, strategy_id):
        data = {**MINIMAL_VERSION_DATA, 'strategy_id': strategy_id}
        return manager.create_strategy_version(data)

    # ── Basic save ─────────────────────────────────────────────────────────

    def test_save_returns_true_on_success(self, manager, version_id):
        """save_backtest_config_for_version returns True when version exists."""
        result = manager.save_backtest_config_for_version(
            version_id, FULL_BACKTEST_CONFIG, source='test_run'
        )
        assert result is True

    def test_save_returns_false_for_unknown_version(self, manager):
        """save_backtest_config_for_version returns False for non-existent version_id."""
        fake_id = str(uuid4())
        result = manager.save_backtest_config_for_version(
            fake_id, FULL_BACKTEST_CONFIG, source='test_run'
        )
        assert result is False

    # ── Metadata tags ──────────────────────────────────────────────────────

    def test_saved_config_has_save_source_tag(self, manager, db_session, version_id):
        """_save_source tag is added to the stored snapshot."""
        from sqlalchemy import text as _text
        manager.save_backtest_config_for_version(
            version_id, {'lookback_days': 90}, source='test_run'
        )
        row = db_session.execute(
            _text("SELECT backtest_config FROM strategy_versions WHERE version_id = :vid"),
            {'vid': version_id}
        ).fetchone()
        stored = row[0]
        assert stored['_save_source'] == 'test_run'

    def test_saved_config_has_saved_at_tag(self, manager, db_session, version_id):
        """_saved_at ISO timestamp is added to the stored snapshot."""
        from sqlalchemy import text as _text
        manager.save_backtest_config_for_version(
            version_id, {'lookback_days': 90}, source='config_discovery'
        )
        row = db_session.execute(
            _text("SELECT backtest_config FROM strategy_versions WHERE version_id = :vid"),
            {'vid': version_id}
        ).fetchone()
        stored = row[0]
        assert '_saved_at' in stored
        # Should parse as ISO datetime without error
        datetime.fromisoformat(stored['_saved_at'])

    def test_save_source_config_discovery(self, manager, db_session, version_id):
        """source='config_discovery' is stored correctly."""
        from sqlalchemy import text as _text
        manager.save_backtest_config_for_version(
            version_id, {'lookback_days': 60}, source='config_discovery'
        )
        row = db_session.execute(
            _text("SELECT backtest_config FROM strategy_versions WHERE version_id = :vid"),
            {'vid': version_id}
        ).fetchone()
        assert row[0]['_save_source'] == 'config_discovery'

    # ── Datetime serialisation ─────────────────────────────────────────────

    def test_datetime_values_are_serialised_to_iso(self, manager, db_session, version_id):
        """datetime values in the config are stored as ISO-8601 strings."""
        from sqlalchemy import text as _text
        dt = datetime(2026, 3, 15, 12, 0, 0)
        config_with_dt = {'lookback_days': 90, 'start_date': dt}
        manager.save_backtest_config_for_version(
            version_id, config_with_dt, source='test_run'
        )
        row = db_session.execute(
            _text("SELECT backtest_config FROM strategy_versions WHERE version_id = :vid"),
            {'vid': version_id}
        ).fetchone()
        stored = row[0]
        # start_date must be a string (ISO format), not a datetime object
        assert isinstance(stored['start_date'], str)
        assert stored['start_date'] == dt.isoformat()

    def test_nested_datetime_values_serialised(self, manager, db_session, version_id):
        """datetime values inside nested dicts are also serialised."""
        from sqlalchemy import text as _text
        dt = datetime(2026, 4, 1, 8, 30, 0)
        config_with_nested = {
            'lookback_days': 90,
            'dates': {'start': dt, 'label': 'test'},
        }
        manager.save_backtest_config_for_version(
            version_id, config_with_nested, source='test_run'
        )
        row = db_session.execute(
            _text("SELECT backtest_config FROM strategy_versions WHERE version_id = :vid"),
            {'vid': version_id}
        ).fetchone()
        stored = row[0]
        assert isinstance(stored['dates']['start'], str)
        assert stored['dates']['start'] == dt.isoformat()

    # ── Config payload survives round-trip ─────────────────────────────────

    def test_full_config_payload_survives_round_trip(self, manager, db_session, version_id):
        """All non-datetime scalar fields survive the JSON round-trip."""
        from sqlalchemy import text as _text
        manager.save_backtest_config_for_version(
            version_id, FULL_BACKTEST_CONFIG, source='test_run'
        )
        row = db_session.execute(
            _text("SELECT backtest_config FROM strategy_versions WHERE version_id = :vid"),
            {'vid': version_id}
        ).fetchone()
        stored = row[0]
        assert stored['lookback_days'] == 180
        assert stored['tpsl_mode'] == 'Fibonacci'
        assert stored['starting_capital'] == 10000
        assert stored['adaptive_sl']['delay_bars'] == 5
        assert stored['adaptive_sl']['volatility_multiplier'] == 1.2

    def test_overwrite_replaces_previous_config(self, manager, db_session, version_id):
        """Calling save twice overwrites — newest config wins."""
        from sqlalchemy import text as _text
        manager.save_backtest_config_for_version(
            version_id, {'lookback_days': 90}, source='test_run'
        )
        manager.save_backtest_config_for_version(
            version_id, {'lookback_days': 365}, source='test_run'
        )
        row = db_session.execute(
            _text("SELECT backtest_config FROM strategy_versions WHERE version_id = :vid"),
            {'vid': version_id}
        ).fetchone()
        assert row[0]['lookback_days'] == 365


# ---------------------------------------------------------------------------
# DB-layer tests: update_strategy_version backtest_config / validation_status
# ---------------------------------------------------------------------------

class TestUpdateStrategyVersionExtension:
    """
    Tests that update_strategy_version() now accepts backtest_config and
    validation_status — the two new allowed_fields added in BTCAAAAA-252.
    """

    @pytest.fixture
    def manager(self, db_session):
        from src.optimizer_v3.database.strategy_manager import StrategyDatabaseManager
        return StrategyDatabaseManager(db_session)

    @pytest.fixture
    def version_id(self, manager):
        strat_id = manager.create_strategy("QA Update Extension Strategy")
        data = {**MINIMAL_VERSION_DATA, 'strategy_id': strat_id}
        return manager.create_strategy_version(data)

    def test_update_backtest_config_accepted(self, manager, db_session, version_id):
        """update_strategy_version() accepts backtest_config update."""
        from sqlalchemy import text as _text
        new_config = {'lookback_days': 270, 'mode': 1}
        result = manager.update_strategy_version(version_id, {'backtest_config': new_config})
        assert result is True
        row = db_session.execute(
            _text("SELECT backtest_config FROM strategy_versions WHERE version_id = :vid"),
            {'vid': version_id}
        ).fetchone()
        stored = row[0]
        assert stored['lookback_days'] == 270

    def test_update_validation_status_accepted(self, manager, db_session, version_id):
        """update_strategy_version() accepts validation_status update."""
        from sqlalchemy import text as _text
        result = manager.update_strategy_version(
            version_id, {'validation_status': 'passed'}
        )
        assert result is True
        row = db_session.execute(
            _text("SELECT validation_status FROM strategy_versions WHERE version_id = :vid"),
            {'vid': version_id}
        ).fetchone()
        assert row[0] == 'passed'

    def test_update_unknown_field_ignored(self, manager, version_id):
        """Fields outside allowed_fields are silently ignored — returns False."""
        result = manager.update_strategy_version(
            version_id, {'core_blocks': []}  # Not an allowed field
        )
        assert result is False


# ---------------------------------------------------------------------------
# UI-layer tests: apply_config_from_dict (no Qt display — mock widgets)
# ---------------------------------------------------------------------------

class TestApplyConfigFromDict:
    """
    Tests for BacktestConfigPanel.apply_config_from_dict().

    We do NOT create a real QApplication — we unit-test the method logic by
    constructing a panel with all its widget references replaced by mocks.
    """

    def _make_mock_panel(self):
        """
        Build a minimal mock of BacktestConfigPanel with mocked Qt widgets
        so apply_config_from_dict() can be called without a running Qt loop.
        """
        from unittest.mock import MagicMock, PropertyMock

        panel = MagicMock()
        panel._loading_preset = False

        # Spinboxes / DoubleSpinboxes
        for attr in [
            'lookback_spin', 'capital_spin', 'risk_spin', 'rr_spin',
            'leverage_spin', 'confluence_spin', 'max_bars_spin',
            'training_spin', 'testing_spin',
            'delay_spin', 'emergency_spin', 'vol_lookback_spin',
            'vol_multi_spin', 'min_sl_spin', 'max_sl_spin',
        ]:
            setattr(panel, attr, MagicMock())

        # ComboBoxes
        for attr in ['tpsl_combo', 'sl_combo']:
            setattr(panel, attr, MagicMock())

        # CheckBoxes
        for attr in ['delayed_sl_check', 'structure_check']:
            setattr(panel, attr, MagicMock())

        # Button group for mode
        mock_btn = MagicMock()
        panel.mode_group = MagicMock()
        panel.mode_group.button.return_value = mock_btn

        # config_retention_label
        panel.config_retention_label = MagicMock()

        # Bind the REAL method under test
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        panel.apply_config_from_dict = lambda saved, source='database': (
            BacktestConfigPanel.apply_config_from_dict(panel, saved, source)
        )
        panel._mark_config_retained = lambda source='database': (
            BacktestConfigPanel._mark_config_retained(panel, source)
        )

        return panel

    # ── Return value ───────────────────────────────────────────────────────

    def test_returns_false_on_empty_dict(self):
        panel = self._make_mock_panel()
        assert panel.apply_config_from_dict({}) is False

    def test_returns_false_on_none(self):
        panel = self._make_mock_panel()
        assert panel.apply_config_from_dict(None) is False

    def test_returns_true_when_fields_applied(self):
        panel = self._make_mock_panel()
        result = panel.apply_config_from_dict({'lookback_days': 90})
        assert result is True

    # ── Basic field restoration ────────────────────────────────────────────

    def test_lookback_days_restored(self):
        panel = self._make_mock_panel()
        panel.apply_config_from_dict({'lookback_days': 180})
        panel.lookback_spin.setValue.assert_called_once_with(180)

    def test_mode_restored(self):
        panel = self._make_mock_panel()
        panel.apply_config_from_dict({'mode': 2})
        panel.mode_group.button.assert_called_once_with(2)
        panel.mode_group.button.return_value.setChecked.assert_called_once_with(True)

    def test_tpsl_mode_restored(self):
        panel = self._make_mock_panel()
        panel.apply_config_from_dict({'tpsl_mode': 'Hybrid'})
        panel.tpsl_combo.setCurrentText.assert_called_once_with('Hybrid')

    def test_sl_mode_restored(self):
        panel = self._make_mock_panel()
        panel.apply_config_from_dict({'sl_mode': 'Static'})
        panel.sl_combo.setCurrentText.assert_called_once_with('Static')

    def test_starting_capital_restored(self):
        panel = self._make_mock_panel()
        panel.apply_config_from_dict({'starting_capital': 25000})
        panel.capital_spin.setValue.assert_called_once_with(25000.0)

    def test_risk_per_trade_restored(self):
        panel = self._make_mock_panel()
        panel.apply_config_from_dict({'risk_per_trade_pct': 2.0})
        panel.risk_spin.setValue.assert_called_once_with(2.0)

    def test_min_risk_reward_10x_inverse(self):
        """min_risk_reward is stored as actual ratio; UI stores 10x."""
        panel = self._make_mock_panel()
        panel.apply_config_from_dict({'min_risk_reward': 1.5})
        panel.rr_spin.setValue.assert_called_once_with(15.0)

    def test_max_leverage_restored(self):
        panel = self._make_mock_panel()
        panel.apply_config_from_dict({'max_leverage': 1.0})
        panel.leverage_spin.setValue.assert_called_once_with(1.0)

    def test_confluence_threshold_restored(self):
        panel = self._make_mock_panel()
        panel.apply_config_from_dict({'confluence_threshold': 4})
        panel.confluence_spin.setValue.assert_called_once_with(4.0)

    def test_max_bars_held_restored(self):
        panel = self._make_mock_panel()
        panel.apply_config_from_dict({'max_bars_held': 150})
        panel.max_bars_spin.setValue.assert_called_once_with(150)

    # ── Mode-1 specific fields ─────────────────────────────────────────────

    def test_training_window_restored(self):
        panel = self._make_mock_panel()
        panel.apply_config_from_dict({'training_window': 60})
        panel.training_spin.setValue.assert_called_once_with(60)

    def test_testing_window_restored(self):
        panel = self._make_mock_panel()
        panel.apply_config_from_dict({'testing_window': 30})
        panel.testing_spin.setValue.assert_called_once_with(30)

    # ── Adaptive SL sub-dict ───────────────────────────────────────────────

    def test_adaptive_sl_delay_enabled_restored(self):
        panel = self._make_mock_panel()
        panel.apply_config_from_dict({'adaptive_sl': {'delay_enabled': True}})
        panel.delayed_sl_check.setChecked.assert_called_once_with(True)

    def test_adaptive_sl_delay_bars_restored(self):
        panel = self._make_mock_panel()
        panel.apply_config_from_dict({'adaptive_sl': {'delay_bars': 7}})
        panel.delay_spin.setValue.assert_called_once_with(7)

    def test_adaptive_sl_volatility_multiplier_restored(self):
        panel = self._make_mock_panel()
        panel.apply_config_from_dict({'adaptive_sl': {'volatility_multiplier': 1.8}})
        panel.vol_multi_spin.setValue.assert_called_once_with(1.8)

    def test_adaptive_sl_min_max_sl_pct_restored(self):
        panel = self._make_mock_panel()
        panel.apply_config_from_dict({
            'adaptive_sl': {'min_sl_pct': 0.5, 'max_sl_pct': 3.0}
        })
        panel.min_sl_spin.setValue.assert_called_once_with(0.5)
        panel.max_sl_spin.setValue.assert_called_once_with(3.0)

    def test_full_config_restores_all_widgets(self):
        """Complete config snapshot restores every mapped widget."""
        panel = self._make_mock_panel()
        result = panel.apply_config_from_dict(FULL_BACKTEST_CONFIG)
        assert result is True
        panel.lookback_spin.setValue.assert_called()
        panel.tpsl_combo.setCurrentText.assert_called()
        panel.capital_spin.setValue.assert_called()
        panel.vol_multi_spin.setValue.assert_called()

    # ── Extra metadata keys ignored ────────────────────────────────────────

    def test_metadata_keys_ignored_gracefully(self):
        """_saved_at / _save_source present in DB snapshot do not crash restore."""
        panel = self._make_mock_panel()
        config = {
            'lookback_days': 90,
            '_saved_at': '2026-05-06T10:00:00',
            '_save_source': 'test_run',
            'start_date': '2026-03-01T00:00:00',
            'end_date': '2026-05-01T00:00:00',
        }
        result = panel.apply_config_from_dict(config, source='database')
        assert result is True  # lookback_days matched — returned True

    # ── _loading_preset suppression ────────────────────────────────────────

    def test_loading_preset_flag_restored_after_apply(self):
        """_loading_preset is reset to False even if an exception occurs."""
        panel = self._make_mock_panel()
        # Simulate a widget raise
        panel.tpsl_combo.setCurrentText.side_effect = RuntimeError("widget error")
        try:
            panel.apply_config_from_dict({'tpsl_mode': 'Fibonacci'})
        except Exception:
            pass
        assert panel._loading_preset is False


# ---------------------------------------------------------------------------
# UI-layer tests: _mark_config_retained
# ---------------------------------------------------------------------------

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

    def test_mark_retained_does_not_raise_on_missing_label(self):
        """If config_retention_label is absent, method falls back silently."""
        panel = MagicMock(spec=[])  # no attributes
        panel.output_panel = None
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        # Should not raise
        BacktestConfigPanel._mark_config_retained(panel, 'test run')
