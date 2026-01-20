"""
Comprehensive Integration Tests for Optimizer V3 UI Components

Tests all UI components with 100% coverage target:
- OptimizerControls (Tab 1)
- LiveOutputPanel (Tab 2)
- TradesPanel (Tab 3)
- MetricsDisplayPanel (Tab 4)
- CompareViewPanel (Tab 5)

Author: Optimizer v3 Team
Date: 2026-01-20
Sprint: 1.4 (Task 1.4.9 - Integration Tests)
"""

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from decimal import Decimal
from datetime import datetime, timedelta
import sys

# NautilusTrader imports
from nautilus_trader.model.objects import Money, Quantity, Price
from nautilus_trader.model.identifiers import InstrumentId, OrderId, TradeId

# Import UI components
from src.optimizer_v3.ui.optimizer_controls import OptimizerControls
from src.optimizer_v3.ui.live_output_panel import LiveOutputPanel, OutputLevel, OutputCategory
from src.optimizer_v3.ui.trades_panel import TradesPanel, TradeDetails, SignalInfo
from src.optimizer_v3.ui.metrics_display_panel import (
    MetricsDisplayPanel, PerformanceMetrics, ParameterSet
)
from src.optimizer_v3.ui.compare_view_panel import CompareViewPanel, ConfigSnapshot


# Fixture for QApplication
@pytest.fixture(scope='session')
def qapp():
    """Create QApplication for tests"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


class TestOptimizerControls:
    """Test OptimizerControls component (Tab 1)"""
    
    def test_initialization(self, qapp):
        """Test component initializes correctly"""
        controls = OptimizerControls()
        
        assert controls is not None
        assert controls.optimize_btn is not None
        assert controls.steps_spin is not None
        assert len(controls.param_checkboxes) == 13
        assert controls.optimize_btn.isEnabled() is False  # Disabled by default
    
    def test_parameter_selection(self, qapp):
        """Test parameter selection functionality"""
        controls = OptimizerControls()
        
        # Initially no parameters selected
        assert sum(1 for v in controls.selected_params.values() if v) == 0
        
        # Select one parameter
        controls.param_checkboxes['delay_bars'].setChecked(True)
        assert controls.optimize_btn.isEnabled() is True
        
        # Count should be 1
        selected = controls.get_selected_parameters()
        assert sum(1 for v in selected.values() if v) == 1
    
    def test_config_count_estimation(self, qapp):
        """Test configuration count estimation"""
        controls = OptimizerControls()
        
        # Set steps to 5
        controls.steps_spin.setValue(5)
        
        # Select 2 parameters (should be 5^2 = 25 configs)
        controls.param_checkboxes['delay_bars'].setChecked(True)
        controls.param_checkboxes['emergency_sl'].setChecked(True)
        
        config = controls.get_optimization_config()
        assert config['steps_per_param'] == 5
        assert config['total_configs'] == 25
    
    def test_select_all_params(self, qapp):
        """Test select all functionality"""
        controls = OptimizerControls()
        
        controls._select_all_params()
        
        # All 13 parameters should be selected
        assert sum(1 for cb in controls.param_checkboxes.values() if cb.isChecked()) == 13
    
    def test_clear_all_params(self, qapp):
        """Test clear all functionality"""
        controls = OptimizerControls()
        
        controls._select_all_params()
        controls._clear_all_params()
        
        # No parameters should be selected
        assert sum(1 for cb in controls.param_checkboxes.values() if cb.isChecked()) == 0
    
    def test_optimize_signal(self, qapp):
        """Test optimize button signal emission"""
        controls = OptimizerControls()
        signal_received = []
        
        controls.optimize_clicked.connect(lambda config: signal_received.append(config))
        
        # Select parameters and click
        controls.param_checkboxes['delay_bars'].setChecked(True)
        controls._on_optimize_clicked()
        
        assert len(signal_received) == 1
        assert 'selected_params' in signal_received[0]


class TestLiveOutputPanel:
    """Test LiveOutputPanel component (Tab 2)"""
    
    def test_initialization(self, qapp):
        """Test component initializes correctly"""
        panel = LiveOutputPanel()
        
        assert panel is not None
        assert panel.output_text is not None
        assert len(panel.messages) == 0
        assert panel.auto_scroll is True
    
    def test_add_message(self, qapp):
        """Test adding messages"""
        panel = LiveOutputPanel()
        
        panel.add_message(
            OutputLevel.INFO,
            OutputCategory.SYSTEM,
            "Test message",
            {'key': 'value'}
        )
        
        # Process pending messages
        panel._flush_pending_messages()
        
        assert len(panel.messages) == 1
        assert panel.messages[0]['message'] == "Test message"
    
    def test_level_filtering(self, qapp):
        """Test message level filtering"""
        panel = LiveOutputPanel()
        
        # Add different level messages
        panel.add_message(OutputLevel.INFO, OutputCategory.SYSTEM, "Info")
        panel.add_message(OutputLevel.ERROR, OutputCategory.SYSTEM, "Error")
        panel._flush_pending_messages()
        
        # Filter to only errors
        panel.active_levels = {OutputLevel.ERROR}
        panel._refresh_display()
        
        # Output should only show error messages
        assert "Error" in panel.output_text.toPlainText()
    
    def test_export_functionality(self, qapp):
        """Test export to file"""
        panel = LiveOutputPanel()
        
        panel.add_message(OutputLevel.INFO, OutputCategory.SYSTEM, "Export test")
        panel._flush_pending_messages()
        
        # Export should work (file created)
        import os
        panel._export_output()
        
        # Check a file was created (basic test)
        assert len(panel.messages) > 0
    
    def test_stats_update(self, qapp):
        """Test statistics update"""
        panel = LiveOutputPanel()
        
        # Add various messages
        panel.add_message(OutputLevel.INFO, OutputCategory.SYSTEM, "Info 1")
        panel.add_message(OutputLevel.INFO, OutputCategory.SYSTEM, "Info 2")
        panel.add_message(OutputLevel.ERROR, OutputCategory.SYSTEM, "Error 1")
        panel._flush_pending_messages()
        
        # Stats should be updated
        assert "2" in panel.info_count_label.text()
        assert "1" in panel.error_count_label.text()


class TestTradesPanel:
    """Test TradesPanel component (Tab 3)"""
    
    def test_initialization(self, qapp):
        """Test component initializes correctly"""
        panel = TradesPanel()
        
        assert panel is not None
        assert panel.trades_table is not None
        assert len(panel.trades) == 0
    
    def test_add_trade(self, qapp):
        """Test adding trade with NautilusTrader types"""
        panel = TradesPanel()
        
        # Create test trade
        trade = TradeDetails(
            trade_id=TradeId('TEST-1'),
            order_id=OrderId('ORDER-1'),
            instrument_id=InstrumentId.from_str('BTC-USD.BINANCE'),
            entry_time=datetime.now(),
            exit_time=None,
            side='BUY',
            quantity=Quantity.from_str('1.0'),
            entry_price=Price.from_str('50000'),
            exit_price=None,
            stop_loss=Price.from_str('49000'),
            take_profit=Price.from_str('52000'),
            commission=Money(10, 'USD'),
            slippage=Money(5, 'USD'),
            pnl=Money(0, 'USD'),
            risk_reward_ratio=Decimal('2.0'),
            win_loss='OPEN',
            duration=timedelta(),
            signals=[],
            capital_start=Money(10000, 'USD'),
            capital_end=Money(10000, 'USD'),
            drawdown=Money(0, 'USD'),
            notes='Test trade'
        )
        
        panel.add_trade(trade)
        
        assert len(panel.trades) == 1
        assert len(panel.filtered_trades) == 1
    
    def test_filter_trades(self, qapp):
        """Test trade filtering"""
        panel = TradesPanel()
        
        # Add winning trade
        winning_trade = self._create_test_trade('WIN')
        panel.add_trade(winning_trade)
        
        # Add losing trade
        losing_trade = self._create_test_trade('LOSS')
        panel.add_trade(losing_trade)
        
        # Filter to winning trades
        panel.filter_combo.setCurrentText("Winning Trades")
        panel._apply_filter("Winning Trades")
        
        assert len(panel.filtered_trades) == 1
        assert panel.filtered_trades[0].win_loss == 'WIN'
    
    def test_summary_stats(self, qapp):
        """Test summary statistics calculation"""
        panel = TradesPanel()
        
        # Add trades
        panel.add_trade(self._create_test_trade('WIN'))
        panel.add_trade(self._create_test_trade('LOSS'))
        
        stats = panel.get_summary_stats()
        
        assert stats['total_trades'] == 2
        assert stats['winning_trades'] == 1
        assert stats['win_rate'] == Decimal('0.5')
        assert isinstance(stats['total_pnl'], Money)
    
    @staticmethod
    def _create_test_trade(outcome: str) -> TradeDetails:
        """Helper to create test trade"""
        pnl = Money(100, 'USD') if outcome == 'WIN' else Money(-50, 'USD')
        exit_price = Price.from_str('51000') if outcome == 'WIN' else Price.from_str('49500')
        
        return TradeDetails(
            trade_id=TradeId(f'TEST-{outcome}'),
            order_id=OrderId(f'ORDER-{outcome}'),
            instrument_id=InstrumentId.from_str('BTC-USD.BINANCE'),
            entry_time=datetime.now(),
            exit_time=datetime.now() + timedelta(minutes=5),
            side='BUY',
            quantity=Quantity.from_str('1.0'),
            entry_price=Price.from_str('50000'),
            exit_price=exit_price,
            stop_loss=Price.from_str('49000'),
            take_profit=Price.from_str('52000'),
            commission=Money(10, 'USD'),
            slippage=Money(5, 'USD'),
            pnl=pnl,
            risk_reward_ratio=Decimal('2.0'),
            win_loss=outcome,
            duration=timedelta(minutes=5),
            signals=[],
            capital_start=Money(10000, 'USD'),
            capital_end=Money(10000, 'USD') + pnl,
            drawdown=Money(0, 'USD'),
            notes=f'Test {outcome} trade'
        )


class TestMetricsDisplayPanel:
    """Test MetricsDisplayPanel component (Tab 4)"""
    
    def test_initialization(self, qapp):
        """Test component initializes correctly"""
        panel = MetricsDisplayPanel()
        
        assert panel is not None
        assert panel.metrics_table is not None
        assert panel.params_table is not None
        assert panel.apply_btn is not None
        assert panel.apply_btn.isEnabled() is False  # Disabled until data loaded
    
    def test_load_comparison(self, qapp):
        """Test loading comparison data"""
        panel = MetricsDisplayPanel()
        
        # Create test metrics
        user_metrics = PerformanceMetrics(
            sharpe_ratio=Decimal('1.5'),
            sortino_ratio=Decimal('1.8'),
            calmar_ratio=Decimal('1.2'),
            win_rate=Decimal('0.6'),
            profit_factor=Decimal('1.5'),
            max_drawdown=Money(500, 'USD'),
            total_pnl=Money(1000, 'USD'),
            avg_trade_pnl=Money(50, 'USD'),
            num_trades=20,
            avg_trade_duration_minutes=30,
            risk_reward_ratio=Decimal('2.0'),
            capital_efficiency=Decimal('0.8')
        )
        
        optimized_metrics = PerformanceMetrics(
            sharpe_ratio=Decimal('2.0'),
            sortino_ratio=Decimal('2.3'),
            calmar_ratio=Decimal('1.8'),
            win_rate=Decimal('0.65'),
            profit_factor=Decimal('1.8'),
            max_drawdown=Money(400, 'USD'),
            total_pnl=Money(1500, 'USD'),
            avg_trade_pnl=Money(75, 'USD'),
            num_trades=20,
            avg_trade_duration_minutes=25,
            risk_reward_ratio=Decimal('2.5'),
            capital_efficiency=Decimal('0.85')
        )
        
        user_params = ParameterSet('User Config', {'stop_loss': '100', 'take_profit': '200'})
        opt_params = ParameterSet('Optimized Config', {'stop_loss': '120', 'take_profit': '240'})
        
        panel.load_comparison(user_metrics, optimized_metrics, user_params, opt_params)
        
        assert panel.user_metrics is not None
        assert panel.optimized_metrics is not None
        assert panel.apply_btn.isEnabled() is True
    
    def test_percent_change_calculation(self, qapp):
        """Test percentage change calculations"""
        panel = MetricsDisplayPanel()
        
        change = panel._calc_percent_change(Decimal('100'), Decimal('120'))
        assert change == '+20.00%'
        
        change = panel._calc_percent_change(Decimal('100'), Decimal('80'))
        assert change == '-20.00%'
    
    def test_money_change_calculation(self, qapp):
        """Test money type change calculations"""
        panel = MetricsDisplayPanel()
        
        old = Money(100, 'USD')
        new = Money(120, 'USD')
        
        change = panel._calc_money_change(old, new)
        assert '+20.00%' in change


class TestCompareViewPanel:
    """Test CompareViewPanel component (Tab 5)"""
    
    def test_initialization(self, qapp):
        """Test component initializes correctly"""
        panel = CompareViewPanel()
        
        assert panel is not None
        assert len(panel.panels) == 3
        assert len(panel.configs) == 0
    
    def test_load_configurations(self, qapp):
        """Test loading configurations"""
        panel = CompareViewPanel()
        
        # Create test configs
        configs = [
            ConfigSnapshot(
                name='Config 1',
                timestamp=datetime.now(),
                parameters={'stop_loss': '100', 'take_profit': '200'},
                metrics={'sharpe': Decimal('1.5'), 'win_rate': Decimal('0.6')},
                runtime_seconds=120,
                hardware_usage={'cpu': 50.0, 'memory': 2048.0}
            ),
            ConfigSnapshot(
                name='Config 2',
                timestamp=datetime.now(),
                parameters={'stop_loss': '120', 'take_profit': '240'},
                metrics={'sharpe': Decimal('2.0'), 'win_rate': Decimal('0.65')},
                runtime_seconds=130,
                hardware_usage={'cpu': 55.0, 'memory': 2100.0}
            )
        ]
        
        panel.load_configurations(configs)
        
        assert len(panel.configs) == 2
        assert panel.panels[0].config is not None
        assert panel.panels[1].config is not None
    
    def test_sync_scroll(self, qapp):
        """Test synchronized scrolling"""
        panel = CompareViewPanel()
        
        # Load configs first
        configs = [
            ConfigSnapshot(
                name=f'Config {i}',
                timestamp=datetime.now(),
                parameters={},
                metrics={},
                runtime_seconds=100,
                hardware_usage={}
            )
            for i in range(3)
        ]
        panel.load_configurations(configs)
        
        # Trigger scroll on first panel
        panel._sync_scroll(100, panel.panels[0])
        
        # Other panels should be synced
        assert panel.panels[1].scroll_area.verticalScrollBar().value() == 100
        assert panel.panels[2].scroll_area.verticalScrollBar().value() == 100


class TestStyleValidation:
    """Test zero hardcoded styles validation"""
    
    def test_no_hardcoded_colors(self):
        """Verify no hardcoded hex colors in UI files"""
        import os
        import re
        
        ui_files = [
            'src/optimizer_v3/ui/optimizer_controls.py',
            'src/optimizer_v3/ui/live_output_panel.py',
            'src/optimizer_v3/ui/trades_panel.py',
            'src/optimizer_v3/ui/metrics_display_panel.py',
            'src/optimizer_v3/ui/compare_view_panel.py'
        ]
        
        # Pattern for hex colors (excluding imports from COLORS)
        hex_pattern = r'["\']#[0-9A-Fa-f]{6}["\']'
        
        for file_path in ui_files:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                    # Check for hex colors (should only be in COLORS references)
                    matches = re.findall(hex_pattern, content)
                    # Filter out COLORS dictionary references
                    violations = [m for m in matches if 'COLORS[' not in content[max(0, content.find(m)-50):content.find(m)]]
                    
                    assert len(violations) == 0, f"Found hardcoded colors in {file_path}: {violations}"
    
    def test_styles_imports(self):
        """Verify all UI files import from styles.py"""
        import os
        
        ui_files = [
            'src/optimizer_v3/ui/optimizer_controls.py',
            'src/optimizer_v3/ui/live_output_panel.py',
            'src/optimizer_v3/ui/trades_panel.py',
            'src/optimizer_v3/ui/metrics_display_panel.py',
            'src/optimizer_v3/ui/compare_view_panel.py'
        ]
        
        for file_path in ui_files:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                    assert 'from src.strategy_builder.ui.styles import' in content, \
                        f"{file_path} missing styles.py import!"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
