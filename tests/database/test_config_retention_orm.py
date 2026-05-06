"""
Unit tests for Strategy Configuration Retention (BTCAAAAA-252)

Tests verify:
- save_backtest_config_for_version() serialises config and persists to DB
- backtest_config is now in allowed_fields for update_strategy_version()
- datetime serialisation works correctly
- _saved_at and _save_source tags are added
- False returned for unknown version_id
"""

import pytest
import json
from datetime import datetime
from unittest.mock import MagicMock, patch, call
from uuid import uuid4

from src.optimizer_v3.database.strategy_manager import StrategyDatabaseManager


class TestSaveBacktestConfigForVersion:
    """Tests for StrategyDatabaseManager.save_backtest_config_for_version()"""

    @pytest.fixture
    def manager(self, db_session):
        """Create strategy database manager with real DB session"""
        return StrategyDatabaseManager(db_session)

    @pytest.fixture
    def strategy_id(self, manager):
        """Create a real strategy in the DB for testing"""
        return manager.create_strategy("ConfigRetentionTestStrategy")

    @pytest.fixture
    def version_id(self, manager, strategy_id):
        """Create a real strategy version for testing"""
        version_data = {
            'strategy_id': strategy_id,
            'name': 'ConfigRetentionTestVersion',
            'blocks': [],
            'signals': {},
            'parameters': {},
            'entry_conditions': {'logic': 'AND', 'rules': []},
            'exit_conditions': [],
            'risk_management': {},
            'backtest_config': {'start_date': '2023-01-01'},
        }
        return manager.create_strategy_version(version_data)

    def test_save_backtest_config_returns_true_on_success(self, manager, version_id):
        """save_backtest_config_for_version() returns True when version exists"""
        config = {
            'lookback_days': 90,
            'mode': 1,
            'starting_capital': 10000.0,
        }
        result = manager.save_backtest_config_for_version(version_id, config, source='test_run')
        assert result is True

    def test_save_backtest_config_returns_false_for_unknown_version(self, manager):
        """save_backtest_config_for_version() returns False for non-existent version"""
        fake_id = str(uuid4())
        config = {'lookback_days': 30}
        result = manager.save_backtest_config_for_version(fake_id, config, source='manual')
        assert result is False

    def test_save_backtest_config_stores_source_tag(self, manager, version_id, db_session):
        """Saved config includes _save_source tag"""
        config = {'lookback_days': 60, 'mode': 2}
        manager.save_backtest_config_for_version(version_id, config, source='config_discovery')

        from sqlalchemy import text
        row = db_session.execute(
            text("SELECT backtest_config FROM strategy_versions WHERE version_id = :vid"),
            {'vid': version_id}
        ).fetchone()
        assert row is not None
        stored = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        assert stored['_save_source'] == 'config_discovery'

    def test_save_backtest_config_stores_saved_at_tag(self, manager, version_id, db_session):
        """Saved config includes _saved_at ISO timestamp"""
        config = {'lookback_days': 45}
        manager.save_backtest_config_for_version(version_id, config, source='test_run')

        from sqlalchemy import text
        row = db_session.execute(
            text("SELECT backtest_config FROM strategy_versions WHERE version_id = :vid"),
            {'vid': version_id}
        ).fetchone()
        stored = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        assert '_saved_at' in stored
        # Should be parseable as ISO datetime
        datetime.fromisoformat(stored['_saved_at'])

    def test_save_backtest_config_stores_all_scalar_fields(self, manager, version_id, db_session):
        """All scalar config fields are persisted correctly"""
        config = {
            'lookback_days': 90,
            'mode': 1,
            'starting_capital': 10000.0,
            'risk_per_trade_pct': 1.5,
            'max_leverage': 1.0,
        }
        manager.save_backtest_config_for_version(version_id, config, source='test_run')

        from sqlalchemy import text
        row = db_session.execute(
            text("SELECT backtest_config FROM strategy_versions WHERE version_id = :vid"),
            {'vid': version_id}
        ).fetchone()
        stored = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        assert stored['lookback_days'] == 90
        assert stored['mode'] == 1
        assert stored['starting_capital'] == 10000.0
        assert stored['risk_per_trade_pct'] == 1.5
        assert stored['max_leverage'] == 1.0

    def test_save_backtest_config_serialises_datetime_values(self, manager, version_id, db_session):
        """datetime values in config are serialised to ISO-8601 strings"""
        dt_val = datetime(2024, 3, 15, 12, 30, 0)
        config = {
            'lookback_days': 30,
            'some_date': dt_val,
        }
        manager.save_backtest_config_for_version(version_id, config, source='manual')

        from sqlalchemy import text
        row = db_session.execute(
            text("SELECT backtest_config FROM strategy_versions WHERE version_id = :vid"),
            {'vid': version_id}
        ).fetchone()
        stored = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        assert stored['some_date'] == '2024-03-15T12:30:00'

    def test_save_backtest_config_serialises_nested_dict_datetimes(self, manager, version_id, db_session):
        """datetime values inside nested dicts are also serialised"""
        dt_val = datetime(2024, 6, 1, 8, 0, 0)
        config = {
            'lookback_days': 30,
            'adaptive_sl': {
                'delay_enabled': True,
                'inner_date': dt_val,
            },
        }
        manager.save_backtest_config_for_version(version_id, config, source='manual')

        from sqlalchemy import text
        row = db_session.execute(
            text("SELECT backtest_config FROM strategy_versions WHERE version_id = :vid"),
            {'vid': version_id}
        ).fetchone()
        stored = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        assert stored['adaptive_sl']['inner_date'] == '2024-06-01T08:00:00'
        assert stored['adaptive_sl']['delay_enabled'] is True

    def test_save_backtest_config_overwrites_previous(self, manager, version_id, db_session):
        """Calling save twice overwrites the previous config"""
        config_v1 = {'lookback_days': 30}
        config_v2 = {'lookback_days': 90, 'mode': 2}
        manager.save_backtest_config_for_version(version_id, config_v1, source='test_run')
        manager.save_backtest_config_for_version(version_id, config_v2, source='config_discovery')

        from sqlalchemy import text
        row = db_session.execute(
            text("SELECT backtest_config FROM strategy_versions WHERE version_id = :vid"),
            {'vid': version_id}
        ).fetchone()
        stored = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        assert stored['lookback_days'] == 90
        assert stored['mode'] == 2
        assert stored['_save_source'] == 'config_discovery'

    def test_update_strategy_version_allows_backtest_config_field(self, manager, version_id, db_session):
        """update_strategy_version() now accepts backtest_config as an allowed field"""
        config_payload = {'lookback_days': 50, 'mode': 1}
        result = manager.update_strategy_version(version_id, {'backtest_config': config_payload})
        assert result is True

        from sqlalchemy import text
        row = db_session.execute(
            text("SELECT backtest_config FROM strategy_versions WHERE version_id = :vid"),
            {'vid': version_id}
        ).fetchone()
        stored = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        assert stored['lookback_days'] == 50

    def test_update_strategy_version_allows_validation_status_field(self, manager, version_id):
        """update_strategy_version() now accepts validation_status as an allowed field"""
        result = manager.update_strategy_version(
            version_id, {'validation_status': 'passed'}
        )
        assert result is True


class TestApplyConfigFromDictUnit:
    """Unit tests for BacktestConfigPanel.apply_config_from_dict() (no Qt required)"""

    def _make_mock_panel(self):
        """
        Build a minimal mock of BacktestConfigPanel with the widget attributes
        that apply_config_from_dict() touches.
        """
        panel = MagicMock()

        # Spinboxes / combo boxes
        panel.lookback_spin = MagicMock()
        panel.mode_group = MagicMock()
        panel.tpsl_combo = MagicMock()
        panel.sl_combo = MagicMock()
        panel.capital_spin = MagicMock()
        panel.risk_spin = MagicMock()
        panel.rr_spin = MagicMock()
        panel.leverage_spin = MagicMock()
        panel.confluence_spin = MagicMock()
        panel.max_bars_spin = MagicMock()
        panel.training_spin = MagicMock()
        panel.testing_spin = MagicMock()

        # ASL widgets
        panel.delayed_sl_check = MagicMock()
        panel.delay_spin = MagicMock()
        panel.emergency_spin = MagicMock()
        panel.vol_lookback_spin = MagicMock()
        panel.vol_multi_spin = MagicMock()
        panel.min_sl_spin = MagicMock()
        panel.max_sl_spin = MagicMock()
        panel.structure_check = MagicMock()

        # Status label
        panel.config_retention_label = MagicMock()
        panel._loading_preset = False

        return panel

    def test_apply_config_from_dict_returns_false_on_empty_dict(self):
        """apply_config_from_dict() returns False when called with empty dict"""
        # Import directly to test the logic without Qt
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        panel = self._make_mock_panel()
        # Bind the method directly
        result = BacktestConfigPanel.apply_config_from_dict(panel, {}, source='database')
        assert result is False

    def test_apply_config_from_dict_sets_lookback_days(self):
        """apply_config_from_dict() calls lookback_spin.setValue with correct int"""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        panel = self._make_mock_panel()
        # mode_group.button returns a truthy mock by default
        result = BacktestConfigPanel.apply_config_from_dict(
            panel, {'lookback_days': 90}, source='database'
        )
        assert result is True
        panel.lookback_spin.setValue.assert_called_once_with(90)

    def test_apply_config_from_dict_sets_mode(self):
        """apply_config_from_dict() calls mode_group.button and setChecked"""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        panel = self._make_mock_panel()
        mock_btn = MagicMock()
        panel.mode_group.button.return_value = mock_btn

        BacktestConfigPanel.apply_config_from_dict(panel, {'mode': 2}, source='database')
        panel.mode_group.button.assert_called_once_with(2)
        mock_btn.setChecked.assert_called_once_with(True)

    def test_apply_config_from_dict_rr_spin_scaled(self):
        """apply_config_from_dict() multiplies min_risk_reward by 10 for the spin"""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        panel = self._make_mock_panel()
        BacktestConfigPanel.apply_config_from_dict(
            panel, {'min_risk_reward': 1.5}, source='database'
        )
        panel.rr_spin.setValue.assert_called_once_with(15.0)

    def test_apply_config_from_dict_applies_asl_subdict(self):
        """apply_config_from_dict() applies adaptive_sl sub-dict fields"""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        panel = self._make_mock_panel()
        config = {
            'adaptive_sl': {
                'delay_enabled': True,
                'delay_bars': 3,
                'emergency_sl_pct': 2.5,
            }
        }
        result = BacktestConfigPanel.apply_config_from_dict(panel, config, source='database')
        assert result is True
        panel.delayed_sl_check.setChecked.assert_called_once_with(True)
        panel.delay_spin.setValue.assert_called_once_with(3)
        panel.emergency_spin.setValue.assert_called_once_with(2.5)

    def test_apply_config_from_dict_skips_metadata_keys(self):
        """apply_config_from_dict() ignores _saved_at and _save_source without error"""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        panel = self._make_mock_panel()
        config = {
            'lookback_days': 30,
            '_saved_at': '2024-01-01T00:00:00',
            '_save_source': 'test_run',
        }
        # Should not raise and should still apply lookback_days
        result = BacktestConfigPanel.apply_config_from_dict(panel, config, source='database')
        assert result is True
        panel.lookback_spin.setValue.assert_called_once_with(30)

    def test_apply_config_from_dict_calls_mark_config_retained(self):
        """apply_config_from_dict() calls _mark_config_retained when widgets updated"""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        panel = self._make_mock_panel()
        BacktestConfigPanel.apply_config_from_dict(
            panel, {'lookback_days': 60}, source='database'
        )
        panel._mark_config_retained.assert_called_once_with('database')

    def test_apply_config_from_dict_no_mark_if_nothing_applied(self):
        """apply_config_from_dict() does NOT call _mark_config_retained on empty dict"""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        panel = self._make_mock_panel()
        BacktestConfigPanel.apply_config_from_dict(panel, {}, source='database')
        panel._mark_config_retained.assert_not_called()


class TestMarkConfigRetainedUnit:
    """Unit tests for BacktestConfigPanel._mark_config_retained()"""

    def _make_panel_with_label(self):
        panel = MagicMock()
        panel.config_retention_label = MagicMock()
        panel.output_panel = None
        return panel

    def test_mark_config_retained_test_run_message(self):
        """_mark_config_retained sets correct label text for 'test run' source"""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        panel = self._make_panel_with_label()
        BacktestConfigPanel._mark_config_retained(panel, 'test run')
        panel.config_retention_label.setVisible.assert_called_with(True)
        # Verify text contains key phrase
        args = panel.config_retention_label.setText.call_args[0][0]
        assert 'test run' in args.lower() or 'Config saved' in args

    def test_mark_config_retained_database_message(self):
        """_mark_config_retained sets correct label text for 'database' source"""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        panel = self._make_panel_with_label()
        BacktestConfigPanel._mark_config_retained(panel, 'database')
        args = panel.config_retention_label.setText.call_args[0][0]
        assert 'restored' in args.lower() or 'Config' in args

    def test_mark_config_retained_is_exception_safe(self):
        """_mark_config_retained never raises — exceptions are silently caught"""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        panel = MagicMock()
        panel.config_retention_label = MagicMock(side_effect=Exception("boom"))
        # Should not propagate
        try:
            BacktestConfigPanel._mark_config_retained(panel, 'test run')
        except Exception:
            pytest.fail("_mark_config_retained raised an exception")
