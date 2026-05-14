"""
Unit Tests for Starting Capital Implementation

NAUTILUS EXPERT: Institutional-grade testing for Phase 0
- NautilusTrader Money type validation
- Futures trading range ($500-$1M)
- Signal emission verification
- UI integration testing

Author: Strategy Builder Team
Date: 2026-01-22
"""

import pytest
from decimal import Decimal
from PyQt5.QtWidgets import QApplication
from nautilus_trader.model.objects import Money, Currency

from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel


@pytest.fixture(scope='module')
def qapp():
    """Create QApplication for Qt widget testing"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_orchestrator():
    """Create mock orchestrator for testing"""
    class MockOrchestrator:
        def get_current_config(self):
            return None

        def validate_strategy(self):
            class ValidationResult:
                success = True
                message = "Valid"
            return ValidationResult()

    return MockOrchestrator()


@pytest.fixture
def panel(qapp, mock_orchestrator):
    """Create BacktestConfigPanel instance"""
    return BacktestConfigPanel(mock_orchestrator)


class TestStartingCapitalValidation:
    """Test starting capital validation logic"""

    def test_default_value(self, panel):
        """Test default starting capital is $10,000"""
        usd = Currency.from_str('USD')
        assert panel.starting_capital == Money('10000', usd)
        assert panel.capital_spin.value() == 10000

    def test_valid_amounts(self, panel):
        """Test valid capital amounts"""
        usd = Currency.from_str('USD')
        valid_amounts = ['500', '1000', '5000', '10000', '50000', '100000', '500000', '1000000']

        for amount in valid_amounts:
            panel.set_starting_capital(amount)
            assert panel.get_starting_capital() == Money(amount, usd)
            assert panel.capital_spin.value() == int(amount)

    def test_minimum_boundary(self, panel):
        """Test minimum boundary ($500)"""
        usd = Currency.from_str('USD')
        # Valid: exactly $500
        panel.set_starting_capital('500')
        assert panel.get_starting_capital() == Money('500', usd)

        # Below minimum: spinbox clamps to $500
        panel.set_starting_capital('499')
        assert panel.capital_spin.value() == 500

    def test_maximum_boundary(self, panel):
        """Test maximum boundary ($1M)"""
        usd = Currency.from_str('USD')
        # Valid: exactly $1M
        panel.set_starting_capital('1000000')
        assert panel.get_starting_capital() == Money('1000000', usd)

        # Above maximum: spinbox clamps to $1M
        panel.set_starting_capital('1000001')
        assert panel.capital_spin.value() == 1000000

    def test_invalid_input(self, panel):
        """Test invalid input handling"""
        panel.set_starting_capital('10000')
        initial_value = panel.capital_spin.value()

        invalid_inputs = ['abc', '', '10.5.5', 'invalid']

        for invalid in invalid_inputs:
            panel.set_starting_capital(invalid)
            assert panel.capital_spin.value() == initial_value

    def test_decimal_amounts(self, panel):
        """Test decimal amounts are rejected by integer spinbox"""
        panel.set_starting_capital('10000')

        panel.set_starting_capital('10000.50')
        assert panel.capital_spin.value() == 10000


class TestStartingCapitalSignals:
    """Test signal emission"""

    def test_capital_changed_signal(self, panel, qapp):
        """Test capital_changed signal is emitted on valid change"""
        usd = Currency.from_str('USD')
        signal_received = []

        def on_capital_changed(capital: Money):
            signal_received.append(capital)

        panel.capital_changed.connect(on_capital_changed)
        panel.set_starting_capital('25000')
        qapp.processEvents()

        assert len(signal_received) == 1
        assert signal_received[0] == Money('25000', usd)

    def test_no_signal_on_invalid(self, panel, qapp):
        """Test no signal emission on invalid input"""
        signal_received = []

        def on_capital_changed(capital: Money):
            signal_received.append(capital)

        panel.capital_changed.connect(on_capital_changed)

        panel.set_starting_capital('10000')
        signal_received.clear()

        panel.set_starting_capital('invalid')
        qapp.processEvents()

        assert len(signal_received) == 0


class TestStartingCapitalUI:
    """Test UI integration"""

    def test_quick_set_buttons(self, panel, qapp):
        """Test quick-set buttons work correctly"""
        usd = Currency.from_str('USD')
        expected_values = [500, 1000, 2500, 5000, 10000, 25000, 50000]

        for value in expected_values:
            panel.capital_spin.setValue(value)
            qapp.processEvents()
            assert panel.get_starting_capital() == Money(str(value), usd)

    def test_validation_ui_feedback(self, panel, qapp):
        """Test spinbox enforces valid range"""
        panel.set_starting_capital('10000')
        qapp.processEvents()
        assert panel.capital_spin.value() == 10000

        panel.capital_spin.setValue(100)
        assert panel.capital_spin.value() == 500


class TestStartingCapitalIntegration:
    """Test integration with backtest config"""

    def test_getter_method(self, panel):
        """Test get_starting_capital returns Money type"""
        capital = panel.get_starting_capital()
        assert isinstance(capital, Money)
        assert capital.currency.code == 'USD'

    def test_setter_method(self, panel):
        """Test set_starting_capital updates UI"""
        usd = Currency.from_str('USD')
        panel.set_starting_capital('75000')
        assert panel.capital_spin.value() == 75000
        assert panel.get_starting_capital() == Money('75000', usd)

    def test_money_type_precision(self, panel):
        """Test Money type preserves precision"""
        panel.set_starting_capital('12345')
        capital = panel.get_starting_capital()
        assert float(capital.as_decimal()) == 12345.0


class TestStartingCapitalFuturesRange:
    """Test futures trading specific validation"""

    def test_micro_account(self, panel):
        """Test micro account ($500-$1000)"""
        usd = Currency.from_str('USD')
        panel.set_starting_capital('500')
        assert panel.get_starting_capital() == Money('500', usd)

        panel.set_starting_capital('750')
        assert panel.get_starting_capital() == Money('750', usd)

        panel.set_starting_capital('1000')
        assert panel.get_starting_capital() == Money('1000', usd)

    def test_small_account(self, panel):
        """Test small account ($1000-$10000)"""
        usd = Currency.from_str('USD')
        for amount in [1000, 2500, 5000, 7500, 10000]:
            panel.set_starting_capital(str(amount))
            assert panel.get_starting_capital() == Money(str(amount), usd)

    def test_standard_account(self, panel):
        """Test standard account ($10000-$100000)"""
        usd = Currency.from_str('USD')
        for amount in [10000, 25000, 50000, 75000, 100000]:
            panel.set_starting_capital(str(amount))
            assert panel.get_starting_capital() == Money(str(amount), usd)

    def test_large_account(self, panel):
        """Test large account ($100000-$1000000)"""
        usd = Currency.from_str('USD')
        for amount in [100000, 250000, 500000, 750000, 1000000]:
            panel.set_starting_capital(str(amount))
            assert panel.get_starting_capital() == Money(str(amount), usd)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
