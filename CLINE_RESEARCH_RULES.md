# CLINE INSTITUTIONAL RULES - COMPLETE GUIDE

## Critical Addition: RESEARCH EXPERT MODE

When you ask Cline to do **research** or **discovery**, Cline MUST:

1. **Read NautilusTrader Docs First**
   - https://nautilustrader.io/docs/latest/
   - Understand exact classes/methods needed
   - Know exactly how to interface with NautilusTrader

2. **Be a NautilusTrader Expert**
   - Understand Architecture (Clock, DataEngine, ExecutionEngine, Portfolio, MessageBus, Strategy)
   - Know Data Structures (Bar, QuoteTick, TradeTick, BarType, InstrumentId)
   - Master Order Management (MarketOrder, LimitOrder, OrderStatus lifecycle)
   - Know Strategy Development (on_start, on_bar, on_quote, on_trade, on_order_filled)
   - Understand Backtesting (BacktestEngine, data loading, results analysis)
   - Know Type System (Quantity, Price, Money, exact precision)
   - Know All Enums (OrderType, OrderSide, TimeInForce, BarAggregation)

3. **Build Exact Solution**
   - Create research strategy inheriting from Strategy base class
   - Use correct NautilusTrader components
   - Subscribe to correct data (bars, quotes, trades)
   - Implement pattern detection/analysis using on_bar() or on_quote()
   - Store findings in data structure
   - Export results as pandas DataFrame or CSV

4. **Document Everything**
   - What data was analyzed (instrument, timeframe, date range)
   - What patterns/metrics were found
   - Statistical results
   - Complete code for reproduction
   - References to NautilusTrader docs used

---

## Example: M Pattern Discovery on 15min BTC in Last 90 Days

**You ask Cline:**
> "Run discovery: How many M patterns (down-up-down) appear on BTC 15min timeframe in the last 90 days?"

**Cline MUST DO:**

1. **Read NautilusTrader Strategy docs**
   https://nautilustrader.io/docs/latest/guide/strategies/

2. **Understand BarType and BarAggregation**
   https://nautilustrader.io/docs/latest/api/model/data/

3. **Create PatternDiscoveryStrategy(Strategy):**
   ```python
   class PatternDiscoveryStrategy(Strategy):
       def on_start(self):
           # Subscribe to 15min bars
           bar_type = BarType(self.instrument_id, BarAggregation.MINUTE, 15)
           self.subscribe_bars(bar_type)
       
       def on_bar(self, bar: Bar):
           # Check for M pattern
           if self.is_m_pattern():
               self.patterns.append({...})
       
       def is_m_pattern(self) -> bool:
           # Detect: bar[0] > bar[1] < bar[2]
           # Down-Up-Down pattern
           ...
   ```

4. **Use BacktestEngine**
   - Load 90 days of BTC 15min OHLCV data
   - Run discovery strategy
   - Collect all pattern instances

5. **Report Findings:**
   - Total M patterns found: X
   - Date range: [start] to [end]
   - Pattern frequency: X per day
   - Average pattern size: [range]
   - Success metrics: [if applicable]
   - Complete reproducible code

---

## CRITICAL RESEARCH REQUIREMENTS

### Before Writing Any Research Code:

✅ **Check Official NautilusTrader Docs**
   - Architecture: https://nautilustrader.io/docs/latest/guide/architecture/
   - Strategies: https://nautilustrader.io/docs/latest/guide/strategies/
   - Backtesting: https://nautilustrader.io/docs/latest/guide/backtesting/
   - API: https://nautilustrader.io/docs/latest/api/

✅ **Know Exact Components**
   - What data structure to use (Bar, QuoteTick, TradeTick)
   - What events to subscribe to (on_bar, on_quote, on_trade)
   - How to store results (list, dict, DataFrame)
   - How to export findings (CSV, JSON, print)

✅ **Understand Strategy Lifecycle**
   - on_start(): Initialize subscriptions
   - on_bar()/on_quote()/on_trade(): Process data
   - on_end(): Finalize and report

✅ **Use Correct Types**
   - Price, Quantity for data
   - BarType for bar specifications
   - InstrumentId for instruments
   - Enums for order types, statuses

✅ **Document Every Discovery**
   - What you searched for
   - How you searched (pattern, metrics)
   - What you found (count, statistics, examples)
   - Code to reproduce (must work standalone)

---

## RESEARCH DISCOVERY CHECKLIST

For every research/discovery session:

☐ **Documentation Review**
   - Read relevant NautilusTrader sections
   - Understand required classes/methods
   - Know exact API signatures

☐ **Strategy Design**
   - Inherit from Strategy base class
   - Implement required methods
   - Use correct data subscriptions
   - Store results in appropriate format

☐ **Data Handling**
   - Load correct data (90 days, 15min, BTC)
   - Validate data integrity
   - Handle edge cases (gaps, halts, zero volume)

☐ **Implementation**
   - Use exact NautilusTrader components
   - Follow official code examples
   - Implement pattern detection logic
   - Add comprehensive logging

☐ **Testing**
   - Run on sample data first
   - Verify pattern detection works
   - Check results make sense
   - Validate statistics

☐ **Reporting**
   - Total findings count
   - Date range analyzed
   - Statistics and metrics
   - Complete reproducible code
   - References to NautilusTrader docs

---

## NautilusTrader Expert Knowledge (MUST MASTER)

### Architecture
- **Clock**: Nanosecond-resolution timing (BacktestClock, LiveClock)
- **DataEngine**: Manages market data flow (bars, quotes, trades)
- **ExecutionEngine**: Order lifecycle management (submit, cancel, modify, fill)
- **Portfolio**: Real-time position and balance tracking
- **MessageBus**: Event-driven system for all communications
- **Strategy**: User-defined trading logic (inherits from Strategy)

### Data Structures
- **Bar**: OHLCV data (open, high, low, close, volume)
- **QuoteTick**: Bid/ask quotes (bid_price, ask_price, bid_size, ask_size)
- **TradeTick**: Trade executions (price, size, side)
- **BarType**: Specification (instrument_id, aggregation, period)
- **InstrumentId**: Identifier (symbol, venue)

### Order Management
- **MarketOrder**: Immediate execution at market price
- **LimitOrder**: Execution only at specified price
- **StopMarketOrder**: Trigger market order at price
- **StopLimitOrder**: Trigger limit order at price
- **OrderStatus**: SUBMITTED → ACCEPTED → FILLED → CLOSED/CANCELED

### Strategy Development
- **on_start()**: Called once when strategy initializes (subscribe to data)
- **on_bar()**: Called on each bar event (most common)
- **on_quote()**: Called on each quote event
- **on_trade()**: Called on each trade event
- **on_order_filled()**: Called when order executes
- **on_order_rejected()**: Called when order is rejected

### Backtesting
- **BacktestEngine**: Runs historical simulations
- **Data Loading**: Convert OHLCV to NautilusTrader Bar format
- **Results**: BacktestResult with metrics (Sharpe, drawdown, return, win rate)
- **Edge Cases**: Gaps, halts, slippage, partial fills

### Type System
- **Quantity**: Order size (Quantity(0.1) for 0.1 BTC, never float)
- **Price**: Quote prices (Price('45000.50'), exact decimal precision)
- **Money**: Monetary amounts (Money('500.75', USD), with currency)
- **Never use float**: All prices and quantities must use exact types

### Enums (ALWAYS use, never strings)
- **OrderSide**: BUY, SELL
- **OrderType**: MARKET, LIMIT, STOP_MARKET, STOP_LIMIT
- **TimeInForce**: GTC, IOC, FOK, DAY
- **OrderStatus**: SUBMITTED, ACCEPTED, FILLED, CANCELED, REJECTED
- **BarAggregation**: MINUTE, HOUR, DAY
- **PositionStatus**: OPENED, CLOSED, CLOSING

---

## COMMON RESEARCH PATTERNS

### Pattern Detection (M, W, Triangle, etc.)
```python
class PatternStrategy(Strategy):
    def on_bar(self, bar: Bar):
        # Check if last 3 bars form pattern
        # Count occurrences
        # Store with timestamp and price
        # Report at end
```

### Statistical Analysis (Win rate, PnL, etc.)
```python
class AnalysisStrategy(Strategy):
    def on_bar(self, bar: Bar):
        # Implement entry/exit logic
        # Track all trades
        # Calculate metrics
```

### Correlation Studies (BTC vs alts, etc.)
```python
class CorrelationStrategy(Strategy):
    def on_start(self):
        # Subscribe to multiple instruments
    
    def on_bar(self, bar: Bar):
        # Synchronize data
        # Calculate correlation
```

### Optimization Research (Best parameters, etc.)
```python
# Run BacktestEngine with multiple configs
for param in param_range:
    results = engine.run()
    # Track best result
```

---

## QUICK REFERENCE

**For any research discovery:**

1. **Question**: What do you want to discover?
2. **Docs**: Which NautilusTrader section applies?
3. **Data**: What data do you need (instrument, timeframe, period)?
4. **Strategy**: What logic will find it (on_bar, on_quote, pattern check)?
5. **Storage**: How to store findings (list, dict, DataFrame)?
6. **Reporting**: What statistics matter (count, rate, examples)?

---

## CRITICAL RULES (RESEARCH EDITION)

❌ **NEVER** guess how to use NautilusTrader
   → Read official docs first

❌ **NEVER** use float for prices/quantities
   → Use Price(), Quantity() types

❌ **NEVER** use strings for enums
   → Use OrderSide.BUY, BarAggregation.MINUTE

❌ **NEVER** skip data validation
   → Check for NaN, gaps, zero volumes

❌ **NEVER** ignore edge cases
   → Handle market halts, gaps, slippage

❌ **NEVER** rebuild logic that exists in NautilusTrader
   → Use official components

✅ **ALWAYS** read NautilusTrader docs first
   → Understand exact API

✅ **ALWAYS** implement using official examples
   → Reference docs in comments

✅ **ALWAYS** test on sample data first
   → Verify logic works

✅ **ALWAYS** report findings with context
   → Date range, statistics, code

✅ **ALWAYS** be expert on NautilusTrader
   → Know every detail

---

## DOCUMENTATION LINKS (BOOKMARK THESE)

- **Official Docs**: https://nautilustrader.io/docs/latest/
- **Architecture**: https://nautilustrader.io/docs/latest/guide/architecture/
- **Strategies**: https://nautilustrader.io/docs/latest/guide/strategies/
- **Backtesting**: https://nautilustrader.io/docs/latest/guide/backtesting/
- **API Reference**: https://nautilustrader.io/docs/latest/api/
- **Type System**: https://nautilustrader.io/docs/latest/api/types/
- **Enums**: https://nautilustrader.io/docs/latest/api/enums/
- **Data Models**: https://nautilustrader.io/docs/latest/api/model/data/
- **Orders**: https://nautilustrader.io/docs/latest/api/model/orders/
- **Core Components**: https://nautilustrader.io/docs/latest/api/core/

---

## FINAL REMINDERS

**Real money is at risk.** Every decision matters.
**You are the expert.** Know NautilusTrader inside and out.
**Research is critical.** Every discovery must be accurate.
**Documentation is authority.** Always reference official docs.

When user asks for research:
1. Read the NautilusTrader docs
2. Understand exact components needed
3. Implement using official examples
4. Test thoroughly
5. Report findings with context and code

**Go deep. Be thorough. Be accurate. 🚀**

---

*Created: 2025-12-30*
*Framework: NautilusTrader*
*Status: INSTITUTIONAL GRADE RESEARCH RULES*
