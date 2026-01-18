# NautilusTrader Code Generation
**Document**: 31_NAUTILUS_CODE_GENERATION.md
**Status**: 🟢 Complete
**Priority**: P0 - Critical

## Code Generation Templates

### Strategy Class Template
```python
from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.types import Quantity, Price
from nautilus_trader.model.orders import MarketOrder
from src.detectors.building_blocks.registry import BlockRegistry

class {{STRATEGY_NAME}}(Strategy):
    def __init__(self, config):
        super().__init__(config)
        self.registry = BlockRegistry
        self.blocks = {}
        self.signal_state = SignalState()
        
    def on_start(self):
        {{INITIALIZATION_CODE}}
        
    def on_bar(self, bar):
        {{SIGNAL_DETECTION_CODE}}
        {{ENTRY_LOGIC_CODE}}
        {{EXIT_LOGIC_CODE}}
```

### Signal Detection Code
```python
# For each building block
block_result = self.blocks['{{BLOCK_NAME}}'].analyze(self.df)
if block_result['signal'] == '{{SIGNAL_NAME}}':
    self.signal_state.add_signal('{{BLOCK_NAME}}', '{{SIGNAL_NAME}}')
```

### Entry Logic Code (AND/OR)
```python
and_count = 0
or_boost = 1.0

# AND blocks (required)
{% for block in and_blocks %}
if self.signal_state.has_signal('{{block.name}}', '{{block.signal}}'):
    and_count += 1
{% endfor %}

# OR blocks (boosters)
{% for block in or_blocks %}
if self.signal_state.has_signal('{{block.name}}', '{{block.signal}}'):
    or_boost += 0.1
{% endfor %}

if and_count >= {{REQUIRED_SIGNALS}}:
    self.enter_position(quantity * or_boost)
```

### Order Submission
```python
order = MarketOrder(
    instrument_id=self.instrument_id,
    client_order_id=self.order_factory.client_order_id(),
    order_side=OrderSide.{{SIDE}},
    quantity=Quantity({{QUANTITY}}),
    time_in_force=TimeInForce.GTC
)
self.submit_order(order)
```

**Version**: 1.0
