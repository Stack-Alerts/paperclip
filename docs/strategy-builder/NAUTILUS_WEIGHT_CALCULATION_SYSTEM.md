# NAUTILUS WEIGHT CALCULATION SYSTEM
**Weight Calculation Integration for Building Blocks and Optimizer V3**

## 📋 OVERVIEW

This document outlines the weight calculation system that integrates building block signal weights with Optimizer V3, ensuring proper handling of visible signals in the Strategy Builder UI.

## 🔧 IMPLEMENTATION

### 1. Weight Calculation System

```python
from nautilus_trader.model.objects import Quantity, Price, Money
from decimal import Decimal
from typing import Dict, List, Optional

class NautilusWeightCalculator:
    """Weight calculation system for NautilusTrader signals"""
    
    def __init__(self):
        self.logger = OptimizerLogger('weight_calculator')
        self._visible_signals = set()  # Only visible signals in UI
        self._block_weights = {}  # Building block assigned weights
        self._optimizer_weights = {}  # Optimizer V3 calculated weights
    
    def register_visible_signal(self, signal_name: str, block_name: str):
        """Register a signal as visible in Strategy Builder UI"""
        self._visible_signals.add((signal_name, block_name))
        
        if block_name not in self._block_weights:
            self._block_weights[block_name] = {}
    
    def set_block_weight(self, 
                        block_name: str,
                        signal_name: str,
                        weight: Decimal):
        """Set weight assigned by building block"""
        if (signal_name, block_name) not in self._visible_signals:
            self.logger.warning(
                f"Attempting to set weight for non-visible signal: "
                f"{signal_name} in block {block_name}"
            )
            return
            
        if block_name not in self._block_weights:
            self._block_weights[block_name] = {}
            
        self._block_weights[block_name][signal_name] = weight
    
    def set_optimizer_weight(self,
                           block_name: str,
                           signal_name: str,
                           weight: Decimal):
        """Set weight calculated by Optimizer V3"""
        if (signal_name, block_name) not in self._visible_signals:
            self.logger.warning(
                f"Attempting to set optimizer weight for non-visible signal: "
                f"{signal_name} in block {block_name}"
            )
            return
            
        if block_name not in self._optimizer_weights:
            self._optimizer_weights[block_name] = {}
            
        self._optimizer_weights[block_name][signal_name] = weight
    
    def calculate_final_weight(self,
                             block_name: str,
                             signal_name: str) -> Optional[Decimal]:
        """Calculate final weight combining block and optimizer weights"""
        if (signal_name, block_name) not in self._visible_signals:
            return None
            
        block_weight = self._block_weights.get(block_name, {}).get(
            signal_name, Decimal('0')
        )
        optimizer_weight = self._optimizer_weights.get(block_name, {}).get(
            signal_name, Decimal('0')
        )
        
        # Combine weights with optimizer having higher influence
        if optimizer_weight > Decimal('0'):
            # Optimizer weight is primary, block weight is modifier
            final_weight = optimizer_weight * (
                Decimal('1') + (block_weight / Decimal('100'))
            )
        else:
            # Use block weight if no optimizer weight
            final_weight = block_weight
        
        # Clamp to valid range
        return max(Decimal('0'), min(Decimal('100'), final_weight))
    
    def get_visible_signals(self) -> List[Dict[str, str]]:
        """Get list of visible signals"""
        return [
            {'signal': signal, 'block': block}
            for signal, block in self._visible_signals
        ]
    
    def get_weight_report(self) -> Dict[str, Dict[str, Dict[str, Decimal]]]:
        """Generate weight report for all visible signals"""
        report = {}
        
        for signal, block in self._visible_signals:
            if block not in report:
                report[block] = {}
                
            report[block][signal] = {
                'block_weight': self._block_weights.get(block, {}).get(
                    signal, Decimal('0')
                ),
                'optimizer_weight': self._optimizer_weights.get(block, {}).get(
                    signal, Decimal('0')
                ),
                'final_weight': self.calculate_final_weight(block, signal)
            }
        
        return report
```

### 2. Integration with Strategy Builder UI

```python
class StrategyBuilderWeightManager:
    """Manage weights in Strategy Builder UI"""
    
    def __init__(self):
        self.weight_calculator = NautilusWeightCalculator()
    
    def on_signal_visibility_changed(self, 
                                   signal_name: str,
                                   block_name: str,
                                   visible: bool):
        """Handle signal visibility changes in UI"""
        if visible:
            self.weight_calculator.register_visible_signal(signal_name, block_name)
        else:
            # Weight calculation will automatically ignore non-visible signals
            pass
    
    def update_block_weight(self,
                          block_name: str,
                          signal_name: str,
                          weight: Decimal):
        """Update weight from building block"""
        self.weight_calculator.set_block_weight(block_name, signal_name, weight)
        self._refresh_ui_weights()
    
    def update_optimizer_weight(self,
                              block_name: str,
                              signal_name: str,
                              weight: Decimal):
        """Update weight from Optimizer V3"""
        self.weight_calculator.set_optimizer_weight(block_name, signal_name, weight)
        self._refresh_ui_weights()
    
    def _refresh_ui_weights(self):
        """Refresh weights displayed in UI"""
        report = self.weight_calculator.get_weight_report()
        
        for block_name, signals in report.items():
            for signal_name, weights in signals.items():
                self._update_ui_weight_display(
                    block_name,
                    signal_name,
                    weights['final_weight']
                )
```

### 3. Integration with Optimizer V3

```python
class OptimizerWeightManager:
    """Manage weights in Optimizer V3"""
    
    def __init__(self, weight_calculator: NautilusWeightCalculator):
        self.weight_calculator = weight_calculator
        self.logger = OptimizerLogger('optimizer_weights')
    
    def optimize_weights(self, backtest_results: dict):
        """Optimize weights based on backtest results"""
        visible_signals = self.weight_calculator.get_visible_signals()
        
        for signal_info in visible_signals:
            signal_name = signal_info['signal']
            block_name = signal_info['block']
            
            # Calculate optimizer weight
            weight = self._calculate_optimizer_weight(
                signal_name,
                block_name,
                backtest_results
            )
            
            # Update weight
            self.weight_calculator.set_optimizer_weight(
                block_name,
                signal_name,
                weight
            )
    
    def _calculate_optimizer_weight(self,
                                  signal_name: str,
                                  block_name: str,
                                  results: dict) -> Decimal:
        """Calculate optimizer weight for signal"""
        try:
            # Extract signal metrics
            metrics = results.get('signal_metrics', {}).get(
                f"{block_name}.{signal_name}", {}
            )
            
            if not metrics:
                return Decimal('0')
            
            # Calculate weight components
            win_rate = Decimal(str(metrics.get('win_rate', 0)))
            profit_factor = Decimal(str(metrics.get('profit_factor', 1)))
            risk_reward = Decimal(str(metrics.get('risk_reward_ratio', 1)))
            
            # Calculate weight (example formula)
            weight = (
                win_rate * Decimal('40') +  # 40% influence
                min(profit_factor, Decimal('3')) * Decimal('20') +  # 20% influence
                min(risk_reward, Decimal('3')) * Decimal('20') +  # 20% influence
                Decimal(str(metrics.get('market_alignment', 0))) * Decimal('20')  # 20% influence
            )
            
            return max(Decimal('0'), min(Decimal('100'), weight))
            
        except Exception as e:
            self.logger.error(f"Weight calculation failed: {str(e)}")
            return Decimal('0')
```

## 🔍 KEY CONSIDERATIONS

1. **Visibility Control**
   - Only visible signals in Strategy Builder UI are:
     * Tracked for optimization
     * Included in weight calculations
     * Displayed in UI

2. **Weight Sources**
   - Building Block Weights:
     * Assigned by building block logic
     * Based on signal-specific criteria
     * Acts as baseline/modifier
   
   - Optimizer V3 Weights:
     * Calculated from backtest results
     * Based on comprehensive metrics
     * Takes precedence when available

3. **Weight Calculation**
   - Final weight combines both sources
   - Optimizer weight has higher influence
   - Weights clamped to 0-100 range
   - Only calculated for visible signals

4. **UI Integration**
   - Automatic UI updates
   - Clear weight display
   - Visibility toggles
   - Weight history tracking

## 📈 IMPLEMENTATION STEPS

1. **Setup**
   - [ ] Implement NautilusWeightCalculator
   - [ ] Integrate with Strategy Builder UI
   - [ ] Connect to Optimizer V3

2. **Testing**
   - [ ] Unit tests for weight calculations
   - [ ] Integration tests with UI
   - [ ] Validation of weight combinations

3. **Validation**
   - [ ] Verify visibility tracking
   - [ ] Confirm weight calculations
   - [ ] Test UI updates

4. **Documentation**
   - [ ] Update user guide
   - [ ] Document weight formulas
   - [ ] Add usage examples

## 🎯 EXPECTED OUTCOMES

1. **Accurate Weights**
   - Proper combination of sources
   - Consistent calculations
   - Valid weight ranges

2. **Clear UI**
   - Visible signal tracking
   - Weight display
   - Update notifications

3. **Optimization**
   - Focused on visible signals
   - Performance-based weights
   - Efficient calculations

## 📝 MONITORING

Monitor these aspects:
- Weight calculation accuracy
- UI update performance
- Optimization effectiveness
- Signal visibility tracking
- Weight history patterns
