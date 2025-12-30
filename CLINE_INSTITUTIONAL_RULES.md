# CLINE INSTITUTIONAL RULES - COMPREHENSIVE REFERENCE

## ⚠️ CRITICAL: REAL MONEY AT RISK

This is the complete institutional-grade reference for the BTC_Engine_v3 project.
Use this when you need deep, comprehensive information about rules, standards, and requirements.

---

## TABLE OF CONTENTS

1. Project Metadata & Critical Parameters
2. Three-Part Rule System (.clinerules, CLINE_RESEARCH_RULES, this document)
3. Institutional Code Quality Standards
4. NautilusTrader Core Architecture
5. Type System (Complete Reference)
6. Enum System (Complete Reference)
7. Risk Management (Detailed Enforcement)
8. Strategy Development (Complete Template)
9. Backtesting Workflow (Step-by-Step)
10. Research & Discovery Protocol
11. Pre-Deployment Checklist
12. Common Mistakes (With Solutions)
13. Escalation Procedures

---

## 1. PROJECT METADATA & CRITICAL PARAMETERS

```
Project Name:           BTC_Engine_v3
Type:                   Institutional Algorithmic Trading Platform
Primary Framework:      NautilusTrader (ONLY - no alternatives)
Python Version:         3.11.14
Environment:            conda (py311)
Data Source:            LakeAPI (user-provided historical BTC data)
Status:                 PRODUCTION - REAL MONEY AT RISK
Code Quality Standard:  INSTITUTIONAL GRADE
Decimal Precision:      8 (for BTC/USDT)
Timezone:               UTC (all timestamps must be UTC nanoseconds)
Backup Rules Files:     .clinerules (daily), CLINE_RESEARCH_RULES.md (research)
This File:              Deep reference for comprehensive information
```

### Critical Decision History
- ❌ **Rejected**: PFund 0.0.2 (circular import bugs, broken pre-release)
- ❌ **Rejected**: PFeed 0.0.5 (mlflow/pyarrow conflicts)
- ❌ **Rejected**: Backtesting.py (insufficient features for institutional use)
- ✅ **Chosen**: NautilusTrader (production-grade, zero conflicts, nanosecond precision)

---

## 2. THREE-PART RULE SYSTEM

### Part 1: `.clinerules.md` (Daily Reference)
**Show to Cline at EVERY session start**
- Session start checklist (7 items)
- 12 critical rules
- Forbidden patterns with examples
- Core types
- Critical enums
- Risk management patterns
- Common operations (copy-paste ready)
- Research strategy template
- Data validation template
- Installation commands
- Pre-deployment checklist

### Part 2: `CLINE_RESEARCH_RULES.md` (Research Expert Mode)
**Reference when asking Cline to research/discover**
- Research expert mode requirements
- M pattern discovery example
- 7 critical NautilusTrader expertise areas
- Common research patterns
- Quick reference for research
- Critical research rules
- Documentation links

### Part 3: `CLINE_INSTITUTIONAL_RULES.md` (This File - Deep Reference)
**Reference for comprehensive information**
- Complete architecture explanation
- Type system details
- Enum system details
- Detailed risk management
- Complete strategy template with explanation
- Backtesting workflow with details
- Common mistakes with solutions
- Escalation procedures

---

## 3. INSTITUTIONAL CODE QUALITY STANDARDS

### Accuracy Requirements
✅ **All numeric types must be exact**
   - Quantity: `Quantity(0.1)` NOT `0.1`
   - Price: `Price('45000.50')` NOT `45000.50`
   - Money: `Money('500.75', USD)` NOT `500.75`
   - Reason: Float precision errors accumulate in trading

✅ **All timestamps must be UTC nanoseconds**
   - Nanoseconds: `int(timestamp.timestamp() * 1e9)`
   - NOT: datetime objects or string timestamps
   - Reason: NautilusTrader uses nanosecond precision

✅ **All IDs must be NautilusTrader types**
   - InstrumentId: `InstrumentId(Symbol('BTC'), Venue('CCXT'))`
   - NOT: strings like `'BTC/USDT'`
   - Reason: Type safety and proper identification

✅ **All enums from NautilusTrader**
   - OrderSide: `OrderSide.BUY` NOT `"BUY"`
   - OrderType: `OrderType.MARKET` NOT `"MARKET"`
   - Reason: Type safety and IDE autocomplete

### Error Handling Requirements
✅ **Every external call wrapped in try/except**
✅ **Every numeric conversion validated**
✅ **Every state change logged with context**
✅ **No silent failures - all errors reported**
✅ **Graceful degradation for missing data**

### Risk Management Requirements
✅ **Position sizing**: MAX_POSITION_SIZE enforced before every trade
✅ **Max drawdown**: Stop loss percentage applied
✅ **Leverage**: LEVERAGE_RATIO checked before every trade
✅ **Daily loss limit**: DAILY_LOSS_LIMIT tracked in real-time
✅ **Order validation**: size, price, instrument verified before submission

### Testing Requirements
✅ **Unit tests**: Every helper function tested
✅ **Integration tests**: Strategy tested on sample data
✅ **Backtest validation**: Results match manual calculation
✅ **Edge cases**: Zero volume, price gaps, halts handled
✅ **Performance**: Execution speed profiled

### Documentation Requirements
✅ **Every function**: docstring with parameters, returns, raises
✅ **Every class**: purpose, attributes, methods documented
✅ **Complex logic**: inline comments explaining why (not what)
✅ **Configuration**: all parameters documented with valid ranges
✅ **Assumptions**: explicitly stated in docstrings

---

## 4. NAUTILUS TRADER CORE ARCHITECTURE

### Clock (Nanosecond-Resolution Timing)
**Purpose**: Provides precise timing for both backtesting and live trading

**Types**:
- `BacktestClock`: Used in backtesting (stepped through data)
- `LiveClock`: Used in production (real-time)

**Key Methods**:
- `utc_now() -> datetime`: Returns current UTC time
- `advance_to_ns(ns: int)`: For stepping through backtest

**Critical Rule**: All timestamps MUST be UTC nanoseconds (int), never datetime objects

**Documentation**: https://nautilustrader.io/docs/latest/api/core/clock/

### DataEngine (Market Data Management)
**Purpose**: Manages subscription and publication of all market data

**Responsibility**:
- Subscribe to instruments (bars, quotes, trades)
- Unsubscribe from instruments
- Publish data events to strategies

**Key Concept**: Event-driven architecture - data flows through message bus

**Documentation**: https://nautilustrader.io/docs/latest/api/core/engines/

### ExecutionEngine (Order Lifecycle Management)
**Purpose**: Executes orders and manages fills

**Responsibility**:
- Order submission
- Order cancellation
- Order modification
- Fill execution
- Position updates

**Key Methods**:
- `submit_order(order)`: Submits order to market
- `cancel_order(order)`: Cancels pending order
- `modify_order(order)`: Modifies open order

**Documentation**: https://nautilustrader.io/docs/latest/api/core/engines/

### Portfolio (Account & Position State)
**Purpose**: Real-time tracking of portfolio state

**Tracks**:
- Open positions
- Account balance
- Unrealized PnL
- Realized PnL
- Margin/leverage

**Key Methods**:
- `net_position(instrument_id)`: Get current position
- `unrealized_pnl(instrument_id)`: Get unrealized PnL
- `realized_pnl(instrument_id)`: Get realized PnL
- `calculate_pnl()`: Total portfolio PnL

**Documentation**: https://nautilustrader.io/docs/latest/api/core/portfolio/

### MessageBus (Central Event System)
**Purpose**: Central event bus for all trading system events

**Pattern**: Publish/subscribe architecture for system decoupling

**Key Concept**:
- Events published by components
- Subscribers listen to events
- Decoupled system design

**Documentation**: https://nautilustrader.io/docs/latest/api/core/message_bus/

### Strategy (User-Defined Logic)
**Purpose**: User inherits from Strategy base class

**Key Methods**:
- `on_start()`: Called when strategy initializes
- `on_bar(bar)`: Called on each bar event
- `on_quote(quote)`: Called on each quote event
- `on_trade(trade)`: Called on each trade event
- `on_order_filled(event)`: Called when order fills
- `on_order_rejected(event)`: Called when order rejected
- `on_position_closed(event)`: Called when position closes

**Documentation**: https://nautilustrader.io/docs/latest/guide/strategies/

---

## 5. TYPE SYSTEM - COMPLETE REFERENCE

### Quantity (Order Size/Volume)
**Purpose**: Represents discrete order size or volume

**Usage**:
```python
from nautilus_trader.model.types import Quantity

# Correct
qty = Quantity(0.1)  # 0.1 BTC
self.buy(qty)

# Wrong - never do this
qty = 0.1  # Float - will cause precision errors
self.buy(qty)
```

**Properties**:
- Exact precision (no floating-point errors)
- Represents discrete units (1 BTC, 0.5 BTC, 0.001 BTC)
- Cannot be negative

**Precision**: Full decimal precision, not limited to float

**Documentation**: https://nautilustrader.io/docs/latest/api/types/

### Price (Bid/Ask/Last Quote)
**Purpose**: Represents price with exact decimal precision

**Usage**:
```python
from nautilus_trader.model.types import Price

# Correct
price = Price('45000.50')  # String for exactness
order = MarketOrder(..., price=price)

# Wrong - never do this
price = 45000.50  # Float - precision errors
price = Decimal('45000.50')  # Not the right type
```

**Properties**:
- Exact decimal precision
- Built-in validation
- Comparable, sortable
- String-based for exactness

**Why String Input?**: Avoids floating-point conversion errors during initialization

**Documentation**: https://nautilustrader.io/docs/latest/api/types/

### Money (Monetary Amounts)
**Purpose**: Represents monetary amounts with currency

**Usage**:
```python
from nautilus_trader.model.types import Money
from nautilus_trader.model.enums import Currency

# Correct
amount = Money('500.75', Currency.USD)
pnl = Money('123.45', Currency.USD)

# Wrong - never do this
amount = 500.75  # No currency
amount = Money('500.75')  # Missing currency
```

**Properties**:
- ALWAYS includes currency
- Exact decimal precision
- Prevents currency mixing

**Why Currency Required?**: Prevents adding USD and EUR, mixed currency errors

**Documentation**: https://nautilustrader.io/docs/latest/api/types/

### InstrumentId (Unique Instrument Identifier)
**Purpose**: Unique identifier for tradeable instruments

**Usage**:
```python
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue

# Correct
instrument_id = InstrumentId(
    symbol=Symbol("BTC"),
    venue=Venue("CCXT")
)

# Wrong - never do this
instrument_id = "BTC/USDT"  # String not safe
instrument_id = "BTC"  # Missing venue
```

**Structure**: `InstrumentId = Symbol + Venue`

**Why Two Parts?**:
- Symbol: Asset being traded (BTC, ETH, AAPL)
- Venue: Exchange/broker (CCXT, IB, Binance, NASDAQ)
- Together: Uniquely identifies BTC on CCXT vs BTC on Binance

**Documentation**: https://nautilustrader.io/docs/latest/api/model/identifiers/

### BarType (Bar Specification)
**Purpose**: Specifies bar configuration (what instrument, what period)

**Usage**:
```python
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import BarAggregation

# Correct - 15 minute bars
bar_type = BarType(
    instrument_id=instrument_id,
    aggregation=BarAggregation.MINUTE,
    period=15,  # 15 minutes
)

# For hourly
bar_type = BarType(
    instrument_id=instrument_id,
    aggregation=BarAggregation.HOUR,
    period=1,  # 1 hour
)

# For daily
bar_type = BarType(
    instrument_id=instrument_id,
    aggregation=BarAggregation.DAY,
    period=1,  # 1 day
)
```

**Components**:
- `instrument_id`: Which instrument (BTC, ETH, etc.)
- `aggregation`: Time unit (MINUTE, HOUR, DAY)
- `period`: Number of units (15 for 15 minutes, 1 for 1 hour)

**Documentation**: https://nautilustrader.io/docs/latest/api/model/data/

---

## 6. ENUM SYSTEM - COMPLETE REFERENCE

### OrderSide (Buy or Sell)
```python
from nautilus_trader.model.enums import OrderSide

OrderSide.BUY   # Buying (long)
OrderSide.SELL  # Selling (short/closing)

# Always use:
order = MarketOrder(..., order_side=OrderSide.BUY)

# Never use:
order = MarketOrder(..., order_side="BUY")
```

### OrderType (How to Execute)
```python
from nautilus_trader.model.enums import OrderType

OrderType.MARKET        # Execute immediately at market price
OrderType.LIMIT         # Execute only at or better than limit price
OrderType.STOP_MARKET   # Trigger market order when price hits stop
OrderType.STOP_LIMIT    # Trigger limit order when price hits stop

# Usage:
order = MarketOrder(...)      # Type is implicit
order = LimitOrder(..., price=Price('45000'))  # Limit price specified
```

### TimeInForce (How Long to Keep Order)
```python
from nautilus_trader.model.enums import TimeInForce

TimeInForce.GTC  # Good Till Canceled (keep until filled or canceled)
TimeInForce.IOC  # Immediate Or Cancel (fill what you can, cancel rest)
TimeInForce.FOK  # Fill Or Kill (all or nothing, cancel if can't fill all)
TimeInForce.DAY  # Good For Day (cancel at end of trading day)

# Usage:
order = MarketOrder(
    ...,
    time_in_force=TimeInForce.IOC,
)
```

### OrderStatus (Order Lifecycle)
```python
from nautilus_trader.model.enums import OrderStatus

OrderStatus.SUBMITTED   # Order submitted to exchange (waiting acceptance)
OrderStatus.ACCEPTED    # Order accepted by exchange (active)
OrderStatus.FILLED      # Order fully executed
OrderStatus.PARTIALLY_FILLED  # Order partially executed
OrderStatus.CANCELED    # Order canceled
OrderStatus.REJECTED    # Order rejected by exchange
OrderStatus.EXPIRED     # Order expired

# Typical lifecycle:
# SUBMITTED → ACCEPTED → FILLED
# SUBMITTED → ACCEPTED → CANCELED
# SUBMITTED → REJECTED
```

### BarAggregation (Bar Time Period)
```python
from nautilus_trader.model.enums import BarAggregation

BarAggregation.MINUTE   # 1 minute (use with period=1)
BarAggregation.HOUR     # 1 hour (use with period=1)
BarAggregation.DAY      # 1 day (use with period=1)

# For 15-minute bars:
bar_type = BarType(
    instrument_id,
    BarAggregation.MINUTE,  # Unit
    15,                      # Period (15 minutes)
)
```

### Currency (Monetary Unit)
```python
from nautilus_trader.model.enums import Currency

Currency.USD  # US Dollar
Currency.EUR  # Euro
Currency.GBP  # British Pound
# ... many more

# Usage:
amount = Money('500.75', Currency.USD)
```

---

## 7. RISK MANAGEMENT - DETAILED ENFORCEMENT

### Position Sizing (Absolute Rule)
```python
# Parameters
MAX_POSITION_SIZE = 1.0      # Maximum 1 BTC per trade
MIN_POSITION_SIZE = 0.001    # Minimum 0.001 BTC

# Enforcement - BEFORE every trade
def on_bar(self, bar: Bar) -> None:
    # ... logic to determine quantity ...
    
    # CHECK POSITION SIZE
    if quantity > Quantity(self.MAX_POSITION_SIZE):
        self.log.error(
            f"Position size {quantity} exceeds max {self.MAX_POSITION_SIZE}"
        )
        return  # DON'T SUBMIT ORDER
    
    if quantity < Quantity(self.MIN_POSITION_SIZE):
        self.log.warning(
            f"Position size {quantity} below minimum {self.MIN_POSITION_SIZE}"
        )
        return  # DON'T SUBMIT ORDER
    
    # Only after validation, submit
    self.submit_order(order)
```

### Stop Loss (Absolute Rule)
```python
# Every open position MUST have stop loss

def on_order_filled(self, event):
    # When order fills, immediately set stop loss
    fill_price = event.last_px
    stop_price = fill_price * (1 - self.STOP_LOSS_PERCENT / 100)
    
    # Create stop loss order
    stop_order = StopMarketOrder(
        instrument_id=self.instrument_id,
        client_order_id=self.order_factory.client_order_id(),
        order_side=OrderSide.SELL,
        quantity=event.quantity,
        trigger_price=Price(str(stop_price)),
    )
    
    self.submit_order(stop_order)
    self.log.info(
        f"Set stop loss at {stop_price} for {event.quantity}"
    )
```

### Daily Loss Limit (Absolute Rule)
```python
# Parameters
DAILY_LOSS_LIMIT = 500.0  # Stop trading if down $500 in a day

# Enforcement - CHECK EVERY BAR
def on_bar(self, bar: Bar) -> None:
    daily_pnl = self.calculate_daily_pnl()
    
    if daily_pnl < -self.DAILY_LOSS_LIMIT:
        # Close all positions
        self.close_all_positions()
        
        self.log.warning(
            f"Daily loss limit hit: ${daily_pnl:.2f}"
        )
        return

def calculate_daily_pnl(self) -> float:
    """Calculate today's PnL"""
    total_pnl = 0.0
    
    for instrument in self.instruments:
        realized = self.portfolio.realized_pnl(instrument)
        unrealized = self.portfolio.unrealized_pnl(instrument)
        total_pnl += float(realized) + float(unrealized)
    
    return total_pnl
```

### Leverage Control (Absolute Rule)
```python
# Parameter
MAX_LEVERAGE = 1.0  # No leverage (1:1 ratio only)

# Enforcement - Check account setup
# Never use margin account
# Always use cash account
# Prevent leveraged orders
```

### Order Validation (Absolute Rule)
```python
# Before EVERY submit_order()
def validate_order(self, order) -> bool:
    """Validate order before submission"""
    
    # Check quantity positive
    if order.quantity <= 0:
        self.log.error("Order quantity must be positive")
        return False
    
    # Check price positive
    if order.price is not None and order.price <= 0:
        self.log.error("Order price must be positive")
        return False
    
    # Check instrument exists
    if order.instrument_id not in self.instruments:
        self.log.error(f"Unknown instrument {order.instrument_id}")
        return False
    
    # Check sufficient balance
    balance = self.portfolio.cash()
    required = float(order.price) * float(order.quantity)
    if balance < required:
        self.log.error(
            f"Insufficient balance: {balance} < {required}"
        )
        return False
    
    return True

# Usage
if not self.validate_order(order):
    return  # Don't submit

self.submit_order(order)
```

---

## 8. STRATEGY DEVELOPMENT - COMPLETE TEMPLATE

```python
from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.core.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import (
    OrderSide, TimeInForce, BarAggregation
)
from nautilus_trader.model.types import Price, Quantity
from nautilus_trader.model.identifiers import InstrumentId
import pandas as pd

class YourStrategy(Strategy):
    """
    Your strategy description.
    
    This strategy implements [specific logic].
    
    Parameters:
    - fast_period: Fast moving average period
    - slow_period: Slow moving average period
    """
    
    def __init__(self, config):
        """Initialize strategy with configuration"""
        super().__init__(config)
        
        # Configuration parameters
        self.fast_period = 10
        self.slow_period = 20
        
        # Risk management parameters
        self.MAX_POSITION_SIZE = Quantity(1.0)
        self.STOP_LOSS_PERCENT = 2.0
        self.DAILY_LOSS_LIMIT = 500.0
        
        # Data storage
        self.bars = []  # Store recent bars for analysis
        self.trades = []  # Store all trades
        self.patterns = []  # Store discovered patterns
    
    def on_start(self):
        """
        Called when strategy starts.
        
        Use this to:
        - Subscribe to data
        - Load models
        - Initialize state
        """
        # Subscribe to 15-minute bars
        bar_type = BarType(
            self.instrument_id,
            BarAggregation.MINUTE,
            15,
        )
        self.subscribe_bars(bar_type)
        
        self.log.info(f"Strategy started for {self.instrument}")
        self.log.info(f"Configuration: fast={self.fast_period}, slow={self.slow_period}")
    
    def on_bar(self, bar: Bar) -> None:
        """
        Called on each new bar event.
        
        Args:
            bar: The new bar data
        """
        
        # STEP 1: VALIDATE INPUT
        if bar is None:
            self.log.warning("Received None bar")
            return
        
        # STEP 2: CHECK RISK LIMITS
        position = self.portfolio.net_position(self.instrument)
        current_size = position.quantity if position else Quantity(0)
        
        if current_size >= self.MAX_POSITION_SIZE:
            self.log.warning(f"Already at max position: {current_size}")
            return
        
        # Check daily loss limit
        daily_pnl = self.calculate_daily_pnl()
        if daily_pnl < -self.DAILY_LOSS_LIMIT:
            self.log.warning(f"Daily loss limit hit: {daily_pnl}")
            self.close_all_positions()
            return
        
        # STEP 3: STORE AND UPDATE DATA
        self.bars.append(bar)
        if len(self.bars) > self.slow_period + 10:
            self.bars.pop(0)  # Keep only recent bars
        
        # STEP 4: CHECK IF WE HAVE ENOUGH DATA
        if len(self.bars) < self.slow_period:
            self.log.debug(f"Need {self.slow_period} bars, have {len(self.bars)}")
            return
        
        # STEP 5: CALCULATE INDICATORS
        closes = [float(b.close) for b in self.bars]
        fast_ma = sum(closes[-self.fast_period:]) / self.fast_period
        slow_ma = sum(closes[-self.slow_period:]) / self.slow_period
        
        # STEP 6: TRADING LOGIC
        if current_size == 0:
            # No position - look for buy signal
            if fast_ma > slow_ma:
                self.execute_buy()
        else:
            # Have position - look for sell signal
            if fast_ma < slow_ma:
                self.execute_sell()
    
    def execute_buy(self):
        """Execute buy order with risk management"""
        from nautilus_trader.model.orders import MarketOrder
        
        # Determine quantity
        quantity = Quantity(0.1)  # Fixed size
        
        # VALIDATE
        if quantity > self.MAX_POSITION_SIZE:
            self.log.error(f"Quantity {quantity} exceeds max")
            return
        
        # CREATE ORDER
        order = MarketOrder(
            instrument_id=self.instrument_id,
            client_order_id=self.order_factory.client_order_id(),
            order_side=OrderSide.BUY,
            quantity=quantity,
            time_in_force=TimeInForce.IOC,
        )
        
        # LOG AND SUBMIT
        self.log.info(f"BUY signal: submitting {quantity} at ${float(self.last_quote.ask)}")
        self.submit_order(order)
    
    def execute_sell(self):
        """Execute sell order"""
        from nautilus_trader.model.orders import MarketOrder
        
        position = self.portfolio.net_position(self.instrument)
        if position is None or position.quantity == 0:
            return
        
        order = MarketOrder(
            instrument_id=self.instrument_id,
            client_order_id=self.order_factory.client_order_id(),
            order_side=OrderSide.SELL,
            quantity=position.quantity,
            time_in_force=TimeInForce.IOC,
        )
        
        self.log.info(f"SELL signal: closing {position.quantity}")
        self.submit_order(order)
    
    def on_order_filled(self, event):
        """Called when order fills"""
        self.log.info(
            f"Order filled: {event.order.order_side} "
            f"{event.quantity} @ {event.last_px}"
        )
        
        # Set stop loss if buying
        if event.order.order_side == OrderSide.BUY:
            self.set_stop_loss(event)
        
        # Record trade
        self.trades.append({
            'timestamp': event.ts_event,
            'side': event.order.order_side,
            'quantity': event.quantity,
            'price': event.last_px,
        })
    
    def set_stop_loss(self, fill_event):
        """Set stop loss for filled buy order"""
        from nautilus_trader.model.orders import StopMarketOrder
        
        fill_price = float(fill_event.last_px)
        stop_price = fill_price * (1 - self.STOP_LOSS_PERCENT / 100)
        
        stop_order = StopMarketOrder(
            instrument_id=self.instrument_id,
            client_order_id=self.order_factory.client_order_id(),
            order_side=OrderSide.SELL,
            quantity=fill_event.quantity,
            trigger_price=Price(str(stop_price)),
        )
        
        self.submit_order(stop_order)
        self.log.info(f"Set stop loss at {stop_price}")
    
    def calculate_daily_pnl(self) -> float:
        """Calculate today's PnL"""
        realized = self.portfolio.realized_pnl(self.instrument)
        unrealized = self.portfolio.unrealized_pnl(self.instrument)
        
        if realized is None:
            realized_float = 0.0
        else:
            realized_float = float(realized)
        
        if unrealized is None:
            unrealized_float = 0.0
        else:
            unrealized_float = float(unrealized)
        
        return realized_float + unrealized_float
    
    def close_all_positions(self):
        """Close all open positions"""
        from nautilus_trader.model.orders import MarketOrder
        
        position = self.portfolio.net_position(self.instrument)
        if position is None or position.quantity == 0:
            return
        
        order = MarketOrder(
            instrument_id=self.instrument_id,
            client_order_id=self.order_factory.client_order_id(),
            order_side=OrderSide.SELL,
            quantity=position.quantity,
            time_in_force=TimeInForce.IOC,
        )
        
        self.submit_order(order)
        self.log.warning(f"Closed all positions: {position.quantity}")
    
    def on_end(self):
        """Called when strategy ends (backtest complete)"""
        # Calculate final statistics
        print("\n" + "="*60)
        print("STRATEGY RESULTS")
        print("="*60)
        print(f"Total Trades: {len(self.trades)}")
        if len(self.trades) > 0:
            print(f"First Trade: {self.trades[0]}")
            print(f"Last Trade: {self.trades[-1]}")
        print(f"Final PnL: ${self.calculate_daily_pnl():.2f}")
        print("="*60)
```

---

## 9. BACKTESTING WORKFLOW - STEP-BY-STEP

### Step 1: Load Data
```python
import pandas as pd
from data.lakeapi_loader import load_btc_from_lakeapi

# Load BTC data from LakeAPI
df = load_btc_from_lakeapi()

# Validate data
assert not df.isnull().any().any(), "Contains NaN"
assert (df['high'] >= df['low']).all(), "High < Low"
```

### Step 2: Convert to NautilusTrader Format
```python
from nautilus_trader.model.data import Bar
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.enums import BarAggregation
from nautilus_trader.model.types import Price, Quantity

def convert_to_bars(df):
    """Convert pandas DataFrame to NautilusTrader Bar objects"""
    
    instrument_id = InstrumentId(
        Symbol("BTC"),
        Venue("CCXT")
    )
    
    bar_type = BarType(
        instrument_id,
        BarAggregation.MINUTE,
        15,
    )
    
    bars = []
    for timestamp, row in df.iterrows():
        ts_nanoseconds = int(timestamp.timestamp() * 1e9)
        
        bar = Bar(
            instrument_id=instrument_id,
            bar_type=bar_type,
            open=Price(str(row['open'])),
            high=Price(str(row['high'])),
            low=Price(str(row['low'])),
            close=Price(str(row['close'])),
            volume=Quantity(row['volume']),
            ts_event=ts_nanoseconds,
            ts_init=ts_nanoseconds,
        )
        bars.append(bar)
    
    return bars

bars = convert_to_bars(df)
```

### Step 3: Create Backtest Engine
```python
from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig

config = BacktestEngineConfig(
    trader_name="BTC_Bot_v3",
    log_level="INFO",
)

engine = BacktestEngine(config)
```

### Step 4: Add Data
```python
engine.add_data(bars)
```

### Step 5: Add Strategy
```python
from strategies.ma_crossover import BTCMACrossover

strategy_config = {
    'instrument_id': instrument_id,
    'account_id': AccountId('BACKTEST-001'),
}

strategy = BTCMACrossover(strategy_config)
engine.add_strategy(strategy)
```

### Step 6: Run Backtest
```python
results = engine.run()
```

### Step 7: Analyze Results
```python
print("="*60)
print("BACKTEST RESULTS")
print("="*60)
print(f"Total Return: {results.total_return:.2%}")
print(f"Sharpe Ratio: {results.sharpe_ratio:.2f}")
print(f"Max Drawdown: {results.max_drawdown:.2%}")
print(f"Win Rate: {results.win_rate:.2%}")
print(f"Profit Factor: {results.profit_factor:.2f}")
print("="*60)
```

---

## 10. RESEARCH & DISCOVERY PROTOCOL

### Research Pattern: Detecting M Patterns

When you ask Cline: "Discover how many M patterns on BTC 15min in last 90 days"

Cline MUST:

1. **Read Official NautilusTrader Docs**
   - https://nautilustrader.io/docs/latest/guide/strategies/
   - https://nautilustrader.io/docs/latest/api/model/data/

2. **Understand Components**
   - Strategy base class
   - on_bar() method
   - BarType and BarAggregation
   - Bar data structure

3. **Create Research Strategy**
   ```python
   class PatternDiscoveryStrategy(Strategy):
       def on_start(self):
           # Subscribe to 15min bars
           bar_type = BarType(
               self.instrument_id,
               BarAggregation.MINUTE,
               15,
           )
           self.subscribe_bars(bar_type)
       
       def on_bar(self, bar: Bar) -> None:
           # Check for M pattern
           if self.is_m_pattern():
               self.patterns.append({
                   'timestamp': bar.ts_event,
                   'price': float(bar.close),
               })
       
       def is_m_pattern(self) -> bool:
           """Check if last 3 bars form M pattern (down-up-down)"""
           if len(self.bars) < 3:
               return False
           
           # bar[0] > bar[1] (down)
           # bar[1] < bar[2] (up)
           down_1 = self.bars[-3].close > self.bars[-2].close
           up = self.bars[-2].close < self.bars[-1].close
           
           return down_1 and up
   ```

4. **Run on 90 Days of Data**
   - Load 90 days of BTC 15min bars
   - Run strategy on entire period
   - Collect all M patterns found

5. **Report Findings**
   - Total M patterns found: X
   - Date range: [start] to [end]
   - Pattern frequency: X per day
   - Average pattern size: [range]
   - Complete reproducible code with all imports

---

## 11. PRE-DEPLOYMENT CHECKLIST

### Code Review Phase
- ☐ All types correct: `Quantity`, `Price`, `Money` (no float)
- ☐ All enums correct: `OrderSide.BUY` (no strings)
- ☐ Risk checks present: position size, stop loss, daily limit
- ☐ Position limits enforced: MAX_POSITION_SIZE checked
- ☐ Stop losses configured: set on every fill
- ☐ Error handling complete: all paths have error handling
- ☐ Logging comprehensive: important events logged

### Testing Phase
- ☐ Unit tests pass: `pytest tests/`
- ☐ Backtest runs: no errors during execution
- ☐ Results validated: manual verification of metrics
- ☐ Edge cases tested: zero volume, gaps, halts handled
- ☐ Data validation passes: no NaN, no gaps
- ☐ Risk limits enforced: verified in simulation

### Documentation Phase
- ☐ All functions documented: docstrings present
- ☐ Parameters documented: types and ranges
- ☐ Return values documented: what each method returns
- ☐ Complex logic explained: inline comments for why
- ☐ Docs referenced: NautilusTrader docs cited in comments

### Approval Phase
- ☐ Code reviewed by human: peer review complete
- ☐ Risk parameters reviewed: position size, stops reviewed
- ☐ Position sizes verified: MAX_POSITION_SIZE appropriate
- ☐ Stop losses verified: STOP_LOSS_PERCENT reasonable
- ☐ Market hours verified: trading outside market hours considered
- ☐ Logging configured: appropriate log levels
- ☐ **EXPLICIT HUMAN APPROVAL FOR LIVE TRADING**

---

## 12. COMMON MISTAKES - WITH SOLUTIONS

### Mistake 1: Using Float for Prices
**Problem**: Floating-point precision errors accumulate
```python
# ❌ WRONG
price = 45000.50
order.price = price

# ✅ RIGHT
price = Price('45000.50')
order.price = price
```

### Mistake 2: Using Strings for Enums
**Problem**: No type safety, IDE can't autocomplete, easy to typo
```python
# ❌ WRONG
order = MarketOrder(..., order_side="BUY")

# ✅ RIGHT
order = MarketOrder(..., order_side=OrderSide.BUY)
```

### Mistake 3: Not Validating Orders
**Problem**: Invalid orders fail silently or cause crashes
```python
# ❌ WRONG
self.submit_order(order)  # No validation

# ✅ RIGHT
if self.validate_order(order):
    self.submit_order(order)
else:
    self.log.error("Order validation failed")
```

### Mistake 4: Skipping Risk Checks
**Problem**: Can exceed position limits, blow account
```python
# ❌ WRONG
if signal:
    self.buy(100)

# ✅ RIGHT
if signal:
    if quantity <= self.MAX_POSITION_SIZE:
        self.buy(quantity)
    else:
        self.log.warning("Position too large")
```

### Mistake 5: Not Setting Stop Losses
**Problem**: Unlimited downside risk
```python
# ❌ WRONG
self.buy(quantity)  # No stop loss

# ✅ RIGHT
self.buy(quantity)
self.set_stop_loss(fill_price)
```

### Mistake 6: Ignoring Data Gaps
**Problem**: Invalid backtest results due to incomplete data
```python
# ❌ WRONG
df = load_data()
# No validation

# ✅ RIGHT
df = load_data()
validate_ohlcv_data(df)
assert no_gaps(df), "Data has gaps"
```

### Mistake 7: Not Testing Edge Cases
**Problem**: Strategy fails on zero volume, price gaps, halts
```python
# ❌ WRONG
# Test on normal data only

# ✅ RIGHT
# Test on normal, gaps, halts, zero volume
```

### Mistake 8: Deploying Without Approval
**Problem**: Real money lost without review
```python
# ❌ WRONG
# Go live immediately after backtest

# ✅ RIGHT
# Get human code review
# Get risk parameter review
# Get explicit approval before live
```

---

## 13. ESCALATION PROCEDURES

### When Uncertain About Implementation
1. Check `.clinerules.md` (quick reference)
2. Check `CLINE_RESEARCH_RULES.md` (research reference)
3. Check this document (deep reference)
4. Check NautilusTrader official docs
5. Ask for clarification - don't guess

### When Data Validation Fails
1. Stop immediately
2. Log error with full details
3. Investigate root cause
4. Don't use invalid data
5. Report findings before proceeding

### When Backtest Results Seem Anomalous
1. Manually verify calculations
2. Compare with other backtesters
3. Check for data errors
4. Verify strategy logic
5. Get human review before proceeding

### When Live Trading is Requested
1. Complete full code review (peer)
2. Complete risk parameter review (risk officer)
3. Complete backtest validation (test engineer)
4. Get explicit human approval (manager)
5. Start with minimum position size
6. Monitor closely for first 24 hours

### When Suspected Bug in Strategy
1. Isolate in simple backtest
2. Add debug logging
3. Compare expected vs actual behavior
4. Fix and re-test
5. Document root cause
6. Update code comments to prevent recurrence

---

## FINAL SUMMARY

This document provides comprehensive, institutional-grade guidance for:
- **Code Quality**: Exact types, exact enums, validation required
- **Risk Management**: Position sizing, stop losses, daily limits (ABSOLUTE)
- **Architecture**: Complete understanding of NautilusTrader components
- **Development**: Complete strategy templates with full explanations
- **Backtesting**: Step-by-step workflows with validation
- **Research**: Complete discovery protocol with examples
- **Deployment**: Pre-deployment checklists with human approval gates
- **Mistakes**: Common pitfalls with solutions

Use this alongside `.clinerules.md` (daily reference) and `CLINE_RESEARCH_RULES.md` (research reference).

**Real money is at risk. Follow these rules exactly. No shortcuts. No approximations. No exceptions.**

---

*Created: 2025-12-30 12:19 CET*
*Framework: NautilusTrader*
*Status: COMPLETE & COMPREHENSIVE*
