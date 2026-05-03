# NAUTILUS STRATEGY STRUCTURE INTEGRATION
**Integration of Strategy Structure and Building Blocks with Optimizer V3**

## 📋 OVERVIEW

This document outlines how strategy structures, building blocks, timing constraints, and dependencies are integrated with Optimizer V3, ensuring proper handling of user configurations.

## 🔧 IMPLEMENTATION

### 1. Strategy Structure Handler

```python
from nautilus_trader.model.objects import Quantity, Price, Money
from nautilus_trader.model.identifiers import InstrumentId
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class NautilusStrategyStructure:
    """Handle strategy structure and building blocks"""
    
    def __init__(self, logger: OptimizerLogger):
        self.logger = logger
        self._strategy = None
        self._dependency_graph = None
        self._timing_map = {}
        self._block_delays = {}
    
    def load_strategy(self, strategy_config: dict) -> dict:
        """Load and validate strategy configuration"""
        try:
            # Convert strategy configuration to NautilusTrader types
            self._strategy = {
                'name': strategy_config['name'],
                'blocks': self._process_blocks(strategy_config['blocks']),
                'dependencies': self._build_dependency_graph(strategy_config['blocks']),
                'timing': self._extract_timing_constraints(strategy_config['blocks']),
                'risk_management': self._process_risk_management(
                    strategy_config.get('risk_management', {})
                )
            }
            
            return self._strategy
            
        except Exception as e:
            self.logger.error(f"Strategy load failed: {str(e)}")
            raise
    
    def _process_blocks(self, blocks: List[dict]) -> List[dict]:
        """Process building blocks with NautilusTrader types"""
        processed_blocks = []
        
        for block in blocks:
            processed_block = {
                'name': block['name'],
                'type': block['type'],
                'signals': self._process_signals(block['signals']),
                'parameters': self._process_parameters(block.get('parameters', {})),
                'recheck': self._process_recheck(block.get('recheck', {})),
                'delay': self._process_delay(block.get('delay', {}))
            }
            
            # Store block delays for dependency resolution
            self._block_delays[block['name']] = processed_block['delay']
            
            processed_blocks.append(processed_block)
        
        return processed_blocks
    
    def _process_signals(self, signals: List[dict]) -> List[dict]:
        """Process signals with timing constraints"""
        processed_signals = []
        
        for signal in signals:
            processed_signal = {
                'name': signal['name'],
                'type': signal['type'],
                'parameters': self._process_parameters(signal.get('parameters', {}))
            }
            
            # Process timing constraints
            if 'timing_constraint' in signal:
                tc = signal['timing_constraint']
                processed_signal['timing_constraint'] = {
                    'reference': tc['reference'],
                    'max_candles': int(tc['max_candles']),
                    'min_candles': int(tc.get('min_candles', 1)),
                    'condition': tc.get('condition', 'AFTER')
                }
                
                # Store in timing map for dependency resolution
                key = f"{signal['name']}::{tc['reference']}"
                self._timing_map[key] = processed_signal['timing_constraint']
            
            processed_signals.append(processed_signal)
        
        return processed_signals
    
    def _process_parameters(self, params: dict) -> dict:
        """Process parameters with NautilusTrader types"""
        processed = {}
        
        for name, value in params.items():
            if isinstance(value, (int, float)):
                processed[name] = Decimal(str(value))
            elif isinstance(value, str):
                if 'price' in name.lower():
                    processed[name] = Price(value)
                elif 'quantity' in name.lower() or 'size' in name.lower():
                    processed[name] = Quantity(value)
                elif 'money' in name.lower() or 'amount' in name.lower():
                    processed[name] = Money(value, 'USD')
                else:
                    processed[name] = value
            else:
                processed[name] = value
        
        return processed
    
    def _process_recheck(self, recheck: dict) -> dict:
        """Process recheck configuration"""
        if not recheck:
            return None
            
        return {
            'max_bars': int(recheck.get('max_bars', 0)),
            'every_n_bars': int(recheck.get('every_n_bars', 1)),
            'condition': recheck.get('condition', 'ANY')
        }
    
    def _process_delay(self, delay: dict) -> dict:
        """Process delay configuration"""
        if not delay:
            return {'bars': 0}
            
        return {
            'bars': int(delay.get('bars', 0)),
            'condition': delay.get('condition', 'ALWAYS')
        }
    
    def _build_dependency_graph(self, blocks: List[dict]) -> dict:
        """Build dependency graph for signals"""
        graph = {}
        
        for block in blocks:
            for signal in block['signals']:
                node_id = f"{block['name']}::{signal['name']}"
                graph[node_id] = {
                    'dependencies': [],
                    'timing_constraints': []
                }
                
                # Add timing dependencies
                if 'timing_constraint' in signal:
                    tc = signal['timing_constraint']
                    graph[node_id]['timing_constraints'].append({
                        'reference': tc['reference'],
                        'max_candles': int(tc['max_candles']),
                        'min_candles': int(tc.get('min_candles', 1)),
                        'condition': tc.get('condition', 'AFTER')
                    })
                    
                    # Add reference signal as dependency
                    ref_parts = tc['reference'].split('::')
                    if len(ref_parts) == 2:
                        ref_block, ref_signal = ref_parts
                        graph[node_id]['dependencies'].append(
                            f"{ref_block}::{ref_signal}"
                        )
        
        self._dependency_graph = graph
        return graph
    
    def _extract_timing_constraints(self, blocks: List[dict]) -> dict:
        """Extract all timing constraints"""
        constraints = {}
        
        for block in blocks:
            for signal in block['signals']:
                if 'timing_constraint' in signal:
                    tc = signal['timing_constraint']
                    key = f"{block['name']}::{signal['name']}"
                    
                    constraints[key] = {
                        'reference': tc['reference'],
                        'max_candles': int(tc['max_candles']),
                        'min_candles': int(tc.get('min_candles', 1)),
                        'condition': tc.get('condition', 'AFTER'),
                        'block_delay': self._block_delays.get(block['name'], {'bars': 0})
                    }
        
        return constraints
    
    def _process_risk_management(self, risk: dict) -> dict:
        """Process risk management settings"""
        if not risk:
            return None
            
        return {
            'position_sizing': {
                'type': risk.get('position_sizing', 'FIXED'),
                'size': Quantity(str(risk['size'])) if 'size' in risk else None,
                'risk_per_trade': Money(str(risk['risk_per_trade']), 'USD') if 'risk_per_trade' in risk else None
            },
            'stop_loss': {
                'type': risk.get('stop_loss_type', 'FIXED'),
                'value': (
                    Price(str(risk['stop_loss'])) 
                    if risk.get('stop_loss_type') == 'FIXED'
                    else Decimal(str(risk['stop_loss']))
                )
            },
            'take_profit': {
                'type': risk.get('take_profit_type', 'FIXED'),
                'value': (
                    Price(str(risk['take_profit']))
                    if risk.get('take_profit_type') == 'FIXED'
                    else Decimal(str(risk['take_profit']))
                )
            },
            'limits': {
                'max_trades_per_day': int(risk.get('max_trades_per_day', 0)),
                'max_concurrent_trades': int(risk.get('max_concurrent_trades', 1)),
                'max_drawdown': Money(str(risk['max_drawdown']), 'USD') if 'max_drawdown' in risk else None
            }
        }
    
    def validate_structure(self) -> bool:
        """Validate strategy structure"""
        try:
            if not self._strategy:
                raise ValueError("No strategy loaded")
            
            # Validate blocks exist
            if not self._strategy['blocks']:
                raise ValueError("Strategy must have at least one block")
            
            # Validate dependencies
            if not self._validate_dependencies():
                return False
            
            # Validate timing constraints
            if not self._validate_timing_constraints():
                return False
            
            # Validate parameters
            if not self._validate_parameters():
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Strategy validation failed: {str(e)}")
            return False
    
    def _validate_dependencies(self) -> bool:
        """Validate dependency graph"""
        if not self._dependency_graph:
            return True
            
        # Check for cycles
        visited = set()
        rec_stack = set()
        
        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)
            
            for dep in self._dependency_graph[node]['dependencies']:
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        # Check each node
        for node in self._dependency_graph:
            if node not in visited:
                if has_cycle(node):
                    self.logger.error(f"Cyclic dependency detected at {node}")
                    return False
        
        return True
    
    def _validate_timing_constraints(self) -> bool:
        """Validate timing constraints"""
        if not self._timing_map:
            return True
            
        for key, constraint in self._timing_map.items():
            # Validate reference exists
            ref = constraint['reference']
            if '::' not in ref:
                self.logger.error(f"Invalid reference format in {key}: {ref}")
                return False
            
            ref_block, ref_signal = ref.split('::')
            ref_exists = False
            
            for block in self._strategy['blocks']:
                if block['name'] == ref_block:
                    for signal in block['signals']:
                        if signal['name'] == ref_signal:
                            ref_exists = True
                            break
                    if ref_exists:
                        break
            
            if not ref_exists:
                self.logger.error(f"Reference not found in {key}: {ref}")
                return False
            
            # Validate candle constraints
            if constraint['max_candles'] < constraint['min_candles']:
                self.logger.error(
                    f"Invalid candle constraints in {key}: "
                    f"max_candles < min_candles"
                )
                return False
        
        return True
    
    def _validate_parameters(self) -> bool:
        """Validate parameters"""
        for block in self._strategy['blocks']:
            # Validate block parameters
            for name, value in block['parameters'].items():
                if isinstance(value, (Quantity, Price, Money)):
                    if value <= 0:
                        self.logger.error(
                            f"Invalid parameter in {block['name']}: "
                            f"{name} must be positive"
                        )
                        return False
            
            # Validate signal parameters
            for signal in block['signals']:
                for name, value in signal['parameters'].items():
                    if isinstance(value, (Quantity, Price, Money)):
                        if value <= 0:
                            self.logger.error(
                                f"Invalid parameter in {block['name']}::"
                                f"{signal['name']}: {name} must be positive"
                            )
                            return False
        
        return True
    
    def generate_baseline_config(self) -> dict:
        """Generate baseline configuration for optimizer"""
        if not self._strategy:
            raise ValueError("No strategy loaded")
            
        try:
            return {
                'strategy': {
                    'name': self._strategy['name'],
                    'blocks': [
                        {
                            'name': block['name'],
                            'type': block['type'],
                            'parameters': block['parameters'],
                            'signals': [
                                {
                                    'name': signal['name'],
                                    'type': signal['type'],
                                    'parameters': signal['parameters'],
                                    'timing_constraint': signal.get('timing_constraint')
                                }
                                for signal in block['signals']
                            ],
                            'recheck': block['recheck'],
                            'delay': block['delay']
                        }
                        for block in self._strategy['blocks']
                    ],
                    'risk_management': self._strategy['risk_management']
                },
                'dependencies': self._dependency_graph,
                'timing': self._strategy['timing']
            }
            
        except Exception as e:
            self.logger.error(f"Baseline config generation failed: {str(e)}")
            raise
    
    def analyze_parameter_changes(self,
                                optimized_params: dict) -> dict:
        """Analyze changes in strategy parameters"""
        if not self._strategy:
            raise ValueError("No strategy loaded")
            
        changes = {
            'blocks': {},
            'signals': {},
            'timing': {},
            'risk': {}
        }
        
        # Compare block parameters
        for block in self._strategy['blocks']:
            block_name = block['name']
            if block_name in optimized_params['blocks']:
                opt_block = optimized_params['blocks'][block_name]
                
                # Parameter changes
                param_changes = {}
                for param, value in block['parameters'].items():
                    if param in opt_block['parameters']:
                        opt_value = opt_block['parameters'][param]
                        if opt_value != value:
                            param_changes[param] = {
                                'from': value,
                                'to': opt_value,
                                'change': opt_value - value
                            }
                
                if param_changes:
                    changes['blocks'][block_name] = param_changes
                
                # Signal changes
                signal_changes = {}
                for signal in block['signals']:
                    signal_name = signal['name']
                    if signal_name in opt_block['signals']:
                        opt_signal = opt_block['signals'][signal_name]
                        
                        # Parameter changes
                        sig_param_changes = {}
                        for param, value in signal['parameters'].items():
                            if param in opt_signal['parameters']:
                                opt_value = opt_signal['parameters'][param]
                                if opt_value != value:
                                    sig_param_changes[param] = {
                                        'from': value,
                                        'to': opt_value,
                                        'change': opt_value - value
                                    }
                        
                        if sig_param_changes:
                            signal_changes[signal_name] = sig_param_changes
                
                if signal_changes:
                    changes['signals'][block_name] = signal_changes
        
        # Compare timing constraints
        timing_changes = {}
        for key, constraint in self._strategy['timing'].items():
            if key in optimized_params['timing']:
                opt_timing = optimized_params['timing'][key]
                
                if opt_timing != constraint:
                    timing_changes[key] = {
                        'from': constraint,
                        'to': opt_timing,
                        'changes': {
                            k: {
                                'from': constraint[k],
                                'to': opt_timing[k]
                            }
                            for k in constraint
                            if k in opt_timing and opt_timing[k] != constraint[k]
                        }
                    }
        
        if timing_changes:
            changes['timing'] = timing_changes
        
        # Compare risk management
        if (self._strategy['risk_management'] and 
            'risk_management' in optimized_params):
            risk_changes = {}
            base_risk = self._strategy['risk_management']
            opt_risk = optimized_params['risk_management']
            
            # Position sizing changes
            if base_risk['position_sizing'] != opt_risk['position_sizing']:
                risk_changes['position_sizing'] = {
                    'from': base_risk['position_sizing'],
                    'to': opt_risk['position_sizing']
                }
            
            # Stop loss changes
            if base_risk['stop_loss'] != opt_risk['stop_loss']:
                risk_changes['stop_loss'] = {
                    'from': base_risk['stop_loss'],
                    'to': opt_risk['stop_loss']
                }
            
            # Take profit changes
            if base_risk['take_profit'] != opt_risk['take_profit']:
                risk_changes['take_profit'] = {
                    'from': base_risk['take_profit'],
                    'to': opt_risk['take_profit']
                }
            
            # Limits changes
            if base_risk['limits'] != opt_risk['limits']:
                risk_changes['limits'] = {
                    'from': base_risk['limits'],
                    'to': opt_risk['limits']
                }
            
            if risk_changes:
                changes['risk'] = risk_changes
        
        return changes
```

### 2. Integration Tests

```python
def test_strategy_structure_handler():
    """Test strategy structure handling"""
    handler = NautilusStrategyStructure(OptimizerLogger('test'))
    
    # Test strategy
    strategy = {
        'name': 'HOD Rejection with RSI Filter',
        'blocks': [
            {
                'name': 'hod',
                'type': 'price_action',
                'signals': [
                    {
                        'name': 'HOD_REJECTION',
                        'type': 'reversal',
                        'parameters': {
                            'lookback': 20,
                            'threshold': 0.001
                        }
                    }
                ],
                'parameters': {
                    'min_range': 100
                },
                'recheck': {
                    'max_bars': 10,
                    'every_n_bars': 1
                },
                'delay': {
                    'bars': 1
                }
            },
            {
                'name': 'rsi',
                'type': 'indicator',
                'signals': [
                    {
                        'name': 'OVERBOUGHT',
                        'type': 'filter',
                        'parameters': {
                            'period': 14,
                            'level': 70
                        },
                        'timing_constraint': {
                            'reference': 'hod::HOD_REJECTION',
                            'max_candles': 5,
                            'min_candles': 1,
                            'condition': 'BEFORE'
                        }
                    }
                ],
                'parameters': {},
                'delay': {
                    'bars': 0
                }
            }
        ],
        'risk_management': {
            'position_sizing': {
                'type': 'FIXED',
                'size': '1.0'
            },
            'stop_loss': {
                'type': 'FIXED',
                'value': '49000'
            },
            'take_profit': {
                'type': 'FIXED',
                'value': '51000'
            },
            'limits': {
                'max_trades_per_day': 5,
                'max_concurrent_trades': 1,
                'max_drawdown': '1000'
            }
        }
    }
    
    # Load strategy
    config = handler.load_strategy(strategy)
    
    # Verify NautilusTrader types
    assert isinstance(
        config['risk_management']['position_sizing']['size'],
        Quantity
    )
    assert isinstance(
        config['risk_management']['stop_loss']['value'],
        Price
    )
    assert isinstance(
        config['risk_management']['limits']['max_drawdown'],
        Money
    )
    
    # Validate structure
    assert handler.validate_structure()
    
    # Generate baseline config
    baseline = handler.generate_baseline_config()
    assert 'strategy' in baseline
    assert 'dependencies' in baseline
    assert 'timing' in baseline
    
    # Test parameter changes
    optimized = {
        'blocks': {
            'hod': {
                'parameters': {
                    'min_range': 120
                },
                'signals': {
                    'HOD_REJECTION': {
                        'parameters': {
                            'lookback': 25,
                            'threshold': 0.0012
                        }
                    }
                }
            },
            'rsi': {
                'signals': {
                    'OVERBOUGHT': {
                        'parameters': {
                            'period': 16,
                            'level': 75
                        }
                    }
                }
            }
        },
        'timing': {
            'rsi::OVERBOUGHT': {
                'reference': 'hod::HOD_REJECTION',
                'max_candles': 4,
                'min_candles': 1,
                'condition': 'BEFORE'
            }
        },
        'risk_management': {
            'position_sizing': {
                'type': 'FIXED',
                'size': '1.2'
            },
            'stop_loss': {
                'type': 'FIXED',
                'value': '49200'
            },
            'take_profit': {
                'type': 'FIXED',
                'value': '51200'
            },
            'limits': {
                'max_trades_per_day': 4,
                'max_concurrent_trades': 1,
                'max_drawdown': '1200'
            }
        }
    }
    
    changes = handler.analyze_parameter_changes(optimized)
    
    # Verify changes structure
    assert 'blocks' in changes
    assert 'signals' in changes
    assert 'timing' in changes
    assert 'risk' in changes
    
    # Verify specific changes
    assert changes['blocks']['hod']['min_range']['change'] == 20
    assert changes['signals']['hod']['HOD_REJECTION']['lookback']['change'] == 5
    assert changes['timing']['rsi::OVERBOUGHT']['changes']['max_candles']['from'] == 5
    assert changes['risk']['position_sizing']['to']['size'] == Quantity('1.2')
```

## 🔍 KEY CONSIDERATIONS

1. **Strategy Structure**
   - Building blocks
   - Signal definitions
   - Parameters
   - Dependencies

2. **Timing Constraints**
   - Reference signals
   - Candle constraints
   - Block delays
   - Validation

3. **Parameter Handling**
   - Type conversion
   - Validation
   - Optimization ranges
   - Changes tracking

4. **Integration Points**
   - Strategy Builder UI
   - Optimizer V3
   - Results comparison
   - Parameter updates

## 📈 IMPLEMENTATION STEPS

1. **Setup**
   - [ ] Implement NautilusStrategyStructure
   - [ ] Add validation system
   - [ ] Create dependency resolver
   - [ ] Add parameter tracking

2. **Testing**
   - [ ] Strategy structure tests
   - [ ] Dependency validation
   - [ ] Parameter handling tests
   - [ ] Integration tests

3. **Validation**
   - [ ] Test all structure components
   - [ ] Verify type safety
   - [ ] Check error handling
   - [ ] Validate dependencies

4. **Documentation**
   - [ ] Update user guide
   - [ ] Document structure format
   - [ ] Add usage examples

## 🎯 EXPECTED OUTCOMES

1. **Type Safety**
   - All strategy components properly typed
   - Safe parameter handling
   - Validated dependencies

2. **Accurate Analysis**
   - Detailed parameter changes
   - Dependency validation
   - Timing constraint verification

3. **Error Handling**
   - Structure validation
   - Clear error messages
   - Recovery procedures

## 📝 MONITORING

Monitor these aspects:
- Strategy structure integrity
- Dependency resolution
- Parameter handling
- Type safety maintenance
