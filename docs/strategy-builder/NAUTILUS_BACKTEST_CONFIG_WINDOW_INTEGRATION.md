# NAUTILUS BACKTEST CONFIG WINDOW INTEGRATION
**Integration of Backtest Configuration Window Tab 1 with Optimizer V3**

## 📋 OVERVIEW

This document outlines how settings from Backtest Configuration Window Tab 1 are integrated with Optimizer V3, ensuring proper handling of user inputs and baseline comparison.

## 🔧 IMPLEMENTATION

### 1. Window Tab 1 Configuration Handler

```python
from nautilus_trader.model.objects import Quantity, Price, Money
from nautilus_trader.model.identifiers import InstrumentId
from decimal import Decimal
from typing import Dict, Optional
from datetime import datetime, timezone

class NautilusBacktestWindowConfig:
    """Handle Backtest Configuration Window Tab 1 settings"""
    
    def __init__(self, logger: OptimizerLogger):
        self.logger = logger
        self._config = None
        self._baseline_results = None
    
    def load_window_settings(self, settings: dict) -> dict:
        """Load and validate window settings"""
        try:
            # Convert all settings to NautilusTrader types
            self._config = {
                # Trading Parameters
                'instrument_id': InstrumentId(settings['instrument']),
                'position_size': Quantity(str(settings['position_size'])),
                'max_position_size': Quantity(str(settings['max_position_size'])),
                'risk_per_trade': Money(str(settings['risk_per_trade']), 'USD'),
                'daily_loss_limit': Money(str(settings['daily_loss_limit']), 'USD'),
                
                # Stop Loss Settings
                'stop_loss_type': settings['stop_loss_type'],
                'fixed_stop_loss': Price(str(settings['fixed_stop_loss'])) if settings['stop_loss_type'] == 'fixed' else None,
                'atr_stop_loss': Decimal(str(settings['atr_stop_loss'])) if settings['stop_loss_type'] == 'atr' else None,
                'trailing_stop': Decimal(str(settings['trailing_stop'])),
                
                # Take Profit Settings
                'take_profit_type': settings['take_profit_type'],
                'fixed_take_profit': Price(str(settings['fixed_take_profit'])) if settings['take_profit_type'] == 'fixed' else None,
                'atr_take_profit': Decimal(str(settings['atr_take_profit'])) if settings['take_profit_type'] == 'atr' else None,
                'partial_tp_enabled': settings['partial_tp_enabled'],
                'partial_tp_size': Decimal(str(settings['partial_tp_size'])) if settings['partial_tp_enabled'] else None,
                
                # Time Settings
                'start_date': datetime.strptime(settings['start_date'], '%Y-%m-%d').replace(tzinfo=timezone.utc),
                'end_date': datetime.strptime(settings['end_date'], '%Y-%m-%d').replace(tzinfo=timezone.utc),
                'session_times': {
                    'asia': (settings['asia_start'], settings['asia_end']),
                    'london': (settings['london_start'], settings['london_end']),
                    'ny': (settings['ny_start'], settings['ny_end'])
                },
                'excluded_times': settings.get('excluded_times', []),
                
                # Market Conditions
                'min_volatility': Decimal(str(settings['min_volatility'])),
                'max_volatility': Decimal(str(settings['max_volatility'])),
                'min_volume': Quantity(str(settings['min_volume'])),
                'trend_strength': Decimal(str(settings['trend_strength'])),
                
                # Risk Management
                'max_trades_per_day': int(settings['max_trades_per_day']),
                'max_concurrent_trades': int(settings['max_concurrent_trades']),
                'max_drawdown': Money(str(settings['max_drawdown']), 'USD'),
                'required_win_rate': Decimal(str(settings['required_win_rate'])),
                'min_profit_factor': Decimal(str(settings['min_profit_factor'])),
                
                # Advanced Settings
                'recheck_interval': int(settings['recheck_interval']),
                'warmup_period': int(settings['warmup_period']),
                'commission_rate': Decimal(str(settings['commission_rate'])),
                'slippage': Decimal(str(settings['slippage']))
            }
            
            return self._config
            
        except Exception as e:
            self.logger.error(f"Window settings load failed: {str(e)}")
            raise
    
    def validate_window_settings(self) -> bool:
        """Validate loaded window settings"""
        try:
            if not self._config:
                raise ValueError("No settings loaded")
            
            # Validate position sizing
            if self._config['position_size'] > self._config['max_position_size']:
                raise ValueError("Position size exceeds maximum")
            
            # Validate stop loss
            if self._config['stop_loss_type'] == 'fixed':
                if not self._config['fixed_stop_loss']:
                    raise ValueError("Fixed stop loss required")
            elif self._config['stop_loss_type'] == 'atr':
                if not self._config['atr_stop_loss']:
                    raise ValueError("ATR stop loss required")
            
            # Validate take profit
            if self._config['take_profit_type'] == 'fixed':
                if not self._config['fixed_take_profit']:
                    raise ValueError("Fixed take profit required")
            elif self._config['take_profit_type'] == 'atr':
                if not self._config['atr_take_profit']:
                    raise ValueError("ATR take profit required")
            
            # Validate dates
            if self._config['start_date'] >= self._config['end_date']:
                raise ValueError("Start date must be before end date")
            
            # Validate risk parameters
            if self._config['risk_per_trade'] > self._config['daily_loss_limit']:
                raise ValueError("Risk per trade exceeds daily loss limit")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Window settings validation failed: {str(e)}")
            return False
    
    def generate_baseline_config(self) -> dict:
        """Generate baseline configuration for optimizer"""
        if not self._config:
            raise ValueError("No settings loaded")
            
        try:
            return {
                'trading': {
                    'instrument_id': self._config['instrument_id'],
                    'position_size': self._config['position_size'],
                    'risk_per_trade': self._config['risk_per_trade'],
                    'stop_loss': {
                        'type': self._config['stop_loss_type'],
                        'fixed_price': self._config['fixed_stop_loss'],
                        'atr_multiple': self._config['atr_stop_loss'],
                        'trailing': self._config['trailing_stop']
                    },
                    'take_profit': {
                        'type': self._config['take_profit_type'],
                        'fixed_price': self._config['fixed_take_profit'],
                        'atr_multiple': self._config['atr_take_profit'],
                        'partial': {
                            'enabled': self._config['partial_tp_enabled'],
                            'size': self._config['partial_tp_size']
                        }
                    }
                },
                'time': {
                    'start_date': self._config['start_date'],
                    'end_date': self._config['end_date'],
                    'sessions': self._config['session_times'],
                    'excluded': self._config['excluded_times']
                },
                'conditions': {
                    'volatility': {
                        'min': self._config['min_volatility'],
                        'max': self._config['max_volatility']
                    },
                    'volume': {
                        'min': self._config['min_volume']
                    },
                    'trend': {
                        'strength': self._config['trend_strength']
                    }
                },
                'risk': {
                    'daily_loss_limit': self._config['daily_loss_limit'],
                    'max_drawdown': self._config['max_drawdown'],
                    'max_trades_per_day': self._config['max_trades_per_day'],
                    'max_concurrent_trades': self._config['max_concurrent_trades'],
                    'required_metrics': {
                        'win_rate': self._config['required_win_rate'],
                        'profit_factor': self._config['min_profit_factor']
                    }
                },
                'execution': {
                    'recheck_interval': self._config['recheck_interval'],
                    'warmup_period': self._config['warmup_period'],
                    'commission_rate': self._config['commission_rate'],
                    'slippage': self._config['slippage']
                }
            }
            
        except Exception as e:
            self.logger.error(f"Baseline config generation failed: {str(e)}")
            raise
    
    def store_baseline_results(self, results: dict):
        """Store baseline backtest results"""
        self._baseline_results = results
    
    def generate_comparison_report(self, optimized_results: dict) -> dict:
        """Generate comparison report between baseline and optimized results"""
        if not self._baseline_results:
            raise ValueError("No baseline results available")
            
        try:
            # Calculate improvements
            improvements = {
                'absolute': {
                    'net_pnl': optimized_results['net_pnl'] - self._baseline_results['net_pnl'],
                    'drawdown': (
                        self._baseline_results['max_drawdown'] - 
                        optimized_results['max_drawdown']
                    ),
                    'win_rate': (
                        optimized_results['win_rate'] - 
                        self._baseline_results['win_rate']
                    ),
                    'profit_factor': (
                        optimized_results['profit_factor'] - 
                        self._baseline_results['profit_factor']
                    ),
                    'avg_trade': (
                        optimized_results['avg_trade_pnl'] - 
                        self._baseline_results['avg_trade_pnl']
                    )
                },
                'percentage': {
                    'net_pnl': self._calculate_percentage_change(
                        self._baseline_results['net_pnl'],
                        optimized_results['net_pnl']
                    ),
                    'drawdown': self._calculate_percentage_change(
                        self._baseline_results['max_drawdown'],
                        optimized_results['max_drawdown']
                    ),
                    'win_rate': self._calculate_percentage_change(
                        self._baseline_results['win_rate'],
                        optimized_results['win_rate']
                    ),
                    'profit_factor': self._calculate_percentage_change(
                        self._baseline_results['profit_factor'],
                        optimized_results['profit_factor']
                    )
                }
            }
            
            # Generate summary
            summary = {
                'performance_rating': self._calculate_performance_rating(
                    improvements['percentage']
                ),
                'risk_rating': self._calculate_risk_rating(
                    self._baseline_results,
                    optimized_results
                ),
                'recommendation': self._generate_recommendation(
                    improvements,
                    self._baseline_results,
                    optimized_results
                )
            }
            
            # Add parameter changes
            parameter_changes = self._analyze_parameter_changes(
                self._config,
                optimized_results['parameters']
            )
            
            return {
                'improvements': improvements,
                'summary': summary,
                'parameter_changes': parameter_changes,
                'details': {
                    'baseline': self._baseline_results,
                    'optimized': optimized_results
                }
            }
            
        except Exception as e:
            self.logger.error(f"Comparison report generation failed: {str(e)}")
            raise
    
    def _calculate_percentage_change(self,
                                   baseline: Decimal,
                                   optimized: Decimal) -> Decimal:
        """Calculate percentage change"""
        if baseline == Decimal('0'):
            return Decimal('0')
        return ((optimized - baseline) / baseline) * Decimal('100')
    
    def _calculate_performance_rating(self, improvements: dict) -> str:
        """Calculate overall performance rating"""
        # Weight the improvements
        weights = {
            'net_pnl': Decimal('0.4'),
            'drawdown': Decimal('0.3'),
            'win_rate': Decimal('0.2'),
            'profit_factor': Decimal('0.1')
        }
        
        score = sum(
            improvements[metric] * weights[metric]
            for metric in weights
        )
        
        if score > Decimal('20'):
            return 'EXCELLENT'
        elif score > Decimal('10'):
            return 'GOOD'
        elif score > Decimal('0'):
            return 'FAIR'
        else:
            return 'POOR'
    
    def _calculate_risk_rating(self,
                             baseline: dict,
                             optimized: dict) -> str:
        """Calculate risk rating"""
        risk_factors = {
            'drawdown_ratio': (
                optimized['max_drawdown'] / baseline['max_drawdown']
            ),
            'trade_frequency': (
                optimized['trades_per_day'] / baseline['trades_per_day']
            ),
            'avg_risk': (
                optimized['avg_risk_per_trade'] / baseline['avg_risk_per_trade']
            )
        }
        
        # Weight the risk factors
        weights = {
            'drawdown_ratio': Decimal('0.4'),
            'trade_frequency': Decimal('0.3'),
            'avg_risk': Decimal('0.3')
        }
        
        score = sum(
            Decimal(str(risk_factors[factor])) * weights[factor]
            for factor in weights
        )
        
        if score < Decimal('0.8'):
            return 'LOW_RISK'
        elif score < Decimal('1.2'):
            return 'MODERATE_RISK'
        else:
            return 'HIGH_RISK'
    
    def _generate_recommendation(self,
                               improvements: dict,
                               baseline: dict,
                               optimized: dict) -> str:
        """Generate recommendation based on comparison"""
        performance_rating = self._calculate_performance_rating(
            improvements['percentage']
        )
        risk_rating = self._calculate_risk_rating(baseline, optimized)
        
        if performance_rating == 'EXCELLENT' and risk_rating == 'LOW_RISK':
            return 'STRONGLY_RECOMMEND'
        elif performance_rating in ['EXCELLENT', 'GOOD'] and risk_rating != 'HIGH_RISK':
            return 'RECOMMEND'
        elif performance_rating == 'POOR' or risk_rating == 'HIGH_RISK':
            return 'NOT_RECOMMENDED'
        else:
            return 'NEUTRAL'
    
    def _analyze_parameter_changes(self,
                                 baseline_config: dict,
                                 optimized_params: dict) -> dict:
        """Analyze changes in parameters"""
        changes = {}
        
        # Compare stop loss settings
        if baseline_config['stop_loss_type'] == optimized_params['stop_loss_type']:
            if baseline_config['stop_loss_type'] == 'fixed':
                changes['stop_loss'] = {
                    'type': 'fixed',
                    'change': (
                        optimized_params['fixed_stop_loss'] -
                        baseline_config['fixed_stop_loss']
                    )
                }
            else:  # ATR
                changes['stop_loss'] = {
                    'type': 'atr',
                    'change': (
                        optimized_params['atr_stop_loss'] -
                        baseline_config['atr_stop_loss']
                    )
                }
        else:
            changes['stop_loss'] = {
                'type': 'changed',
                'from': baseline_config['stop_loss_type'],
                'to': optimized_params['stop_loss_type']
            }
        
        # Compare take profit settings
        if baseline_config['take_profit_type'] == optimized_params['take_profit_type']:
            if baseline_config['take_profit_type'] == 'fixed':
                changes['take_profit'] = {
                    'type': 'fixed',
                    'change': (
                        optimized_params['fixed_take_profit'] -
                        baseline_config['fixed_take_profit']
                    )
                }
            else:  # ATR
                changes['take_profit'] = {
                    'type': 'atr',
                    'change': (
                        optimized_params['atr_take_profit'] -
                        baseline_config['atr_take_profit']
                    )
                }
        else:
            changes['take_profit'] = {
                'type': 'changed',
                'from': baseline_config['take_profit_type'],
                'to': optimized_params['take_profit_type']
            }
        
        # Compare position size
        changes['position_size'] = {
            'change': (
                optimized_params['position_size'] -
                baseline_config['position_size']
            )
        }
        
        # Compare risk settings
        changes['risk_settings'] = {
            'risk_per_trade': (
                optimized_params['risk_per_trade'] -
                baseline_config['risk_per_trade']
            ),
            'max_trades_per_day': (
                optimized_params['max_trades_per_day'] -
                baseline_config['max_trades_per_day']
            )
        }
        
        return changes
```

### 2. Window Integration Tests

```python
def test_window_config_handler():
    """Test window configuration handling"""
    handler = NautilusBacktestWindowConfig(OptimizerLogger('test'))
    
    # Test settings
    settings = {
        'instrument': 'BTC-USD',
        'position_size': '1.0',
        'max_position_size': '5.0',
        'risk_per_trade': '100',
        'daily_loss_limit': '500',
        'stop_loss_type': 'fixed',
        'fixed_stop_loss': '49000',
        'take_profit_type': 'fixed',
        'fixed_take_profit': '51000',
        'partial_tp_enabled': True,
        'partial_tp_size': '0.5',
        'start_date': '2025-01-01',
        'end_date': '2025-12-31',
        'asia_start': '00:00',
        'asia_end': '08:00',
        'london_start': '08:00',
        'london_end': '16:00',
        'ny_start': '16:00',
        'ny_end': '24:00',
        'min_volatility': '0.01',
        'max_volatility': '0.05',
        'min_volume': '100',
        'trend_strength': '25',
        'max_trades_per_day': '5',
        'max_concurrent_trades': '2',
        'max_drawdown': '1000',
        'required_win_rate': '0.6',
        'min_profit_factor': '2.0',
        'recheck_interval': '5',
        'warmup_period': '20',
        'commission_rate': '0.001',
        'slippage': '0.0005'
    }
    
    # Load settings
    config = handler.load_window_settings(settings)
    
    # Verify NautilusTrader types
    assert isinstance(config['instrument_id'], InstrumentId)
    assert isinstance(config['position_size'], Quantity)
    assert isinstance(config['risk_per_trade'], Money)
    assert isinstance(config['fixed_stop_loss'], Price)
    assert isinstance(config['min_volatility'], Decimal)
    
    # Validate settings
    assert handler.validate_window_settings()
    
    # Generate baseline config
    baseline = handler.generate_baseline_config()
    assert 'trading' in baseline
    assert 'time' in baseline
    assert 'conditions' in baseline
    assert 'risk' in baseline
    
    # Test comparison report
    optimized_results = {
        'net_pnl': Money('2000', 'USD'),
        'max_drawdown': Money('400', 'USD'),
        'win_rate': Decimal('0.65'),
        'profit_factor': Decimal('2.5'),
        'avg_trade_pnl': Money('100', 'USD'),
        'trades_per_day': Decimal('4'),
        'avg_risk_per_trade': Money('80', 'USD'),
        'parameters': {
            'stop_loss_type': 'fixed',
            'fixed_stop_loss': Price('49200'),
            'take_profit_type': 'fixed',
            'fixed_take_profit': Price('51200'),
            'position_size': Quantity('1.2'),
            'risk_per_trade': Money('120', 'USD'),
            'max_trades_per_day': 4
        }
    }
    
    handler.store_baseline_results({
        'net_pnl': Money('1500', 'USD'),
        'max_drawdown': Money('500', 'USD'),
        'win_rate': Decimal('0.60'),
        'profit_factor': Decimal('2.0'),
        'avg_trade_pnl': Money('75', 'USD'),
        'trades_per_day': Decimal('5'),
        'avg_risk_per_trade': Money('100', 'USD')
    })
    
    report = handler.generate_comparison_report(optimized_results)
    
    # Verify report structure
    assert 'improvements' in report
    assert 'summary' in report
    assert 'parameter_changes' in report
    assert 'details' in report
    
    # Verify improvements
    assert isinstance(report['improvements']['absolute']['net_pnl'], Money)
    assert isinstance(report['improvements']['percentage']['win_rate'], Decimal)
    
    # Verify parameter changes
    changes = report['parameter_changes']
    assert isinstance(changes['position_size']['change'], Quantity)
    assert isinstance(changes['risk_settings']['risk_per_trade'], Money)
```

## 🔍 KEY CONSIDERATIONS

1. **Window Settings**
   - All fields from Tab 1
   - Proper type conversion
   - Validation rules
   - Default values

2. **Baseline Configuration**
   - User settings as baseline
   - Type safety
   - Complete parameter set
   - Validation

3. **Results Comparison**
   - Absolute improvements
   - Percentage changes
   - Parameter modifications
   - Risk assessment

4. **Integration Points**
   - Window UI
   - Optimizer V3
   - Results display
   - Parameter updates

## 📈 IMPLEMENTATION STEPS

1. **Setup**
   - [ ] Implement NautilusBacktestWindowConfig
   - [ ] Add validation system
   - [ ] Create comparison system
   - [ ] Add parameter tracking

2. **Testing**
   - [ ] Window settings tests
   - [ ] Validation tests
   - [ ] Comparison tests
   - [ ] Integration tests

3. **Validation**
   - [ ] Test all window fields
   - [ ] Verify type safety
   - [ ] Check error handling
   - [ ] Validate comparisons

4. **Documentation**
   - [ ] Update user guide
   - [ ] Document window fields
   - [ ] Add usage examples

## 🎯 EXPECTED OUTCOMES

1. **Type Safety**
   - All window settings properly typed
   - Safe conversions
   - Validated inputs

2. **Accurate Comparison**
   - Detailed improvements
   - Parameter changes
   - Risk assessment

3. **Error Handling**
   - Input validation
   - Clear error messages
   - Recovery procedures

## 📝 MONITORING

Monitor these aspects:
- Window settings accuracy
- Validation effectiveness
- Comparison accuracy
- Type safety maintenance
