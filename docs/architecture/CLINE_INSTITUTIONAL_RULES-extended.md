# CLINE INSTITUTIONAL RULES - EXTENDED GUIDE

**Location:** `~/projects/BTC_Engine_v3/CLINE_INSTITUTIONAL_RULES.md`

**Purpose:** Full protocols for all modes. Read on-demand when activated.

**Size:** ~45KB (full detailed protocols)

**Usage:** 
- Core `.clinerules` file: ~15KB (always loaded at session start)
- This extended guide: ~45KB (lazy-loaded when mode activated)
- **Total:** Saves 65% from initial context load

---

## Table of Contents

1. [TASK COMPLETION ENFORCEMENT](#task-completion-enforcement)
2. [CONTEXT WINDOW PROTOCOL](#context-window-protocol)
3. [RESEARCH PROTOCOL](#research-protocol)
4. [NAUTILUS TRADER EXPERT MODE](#nautilus-trader-expert-mode)
5. [EXPERT MODE](#expert-mode-full-protocol)
6. [DESIGN MODE](#design-mode-full-protocol)
7. [GITHUB EXPERT MODE](#github-expert-mode-full-protocol)
8. [CODE TEMPLATES](#code-templates)
9. [TESTING & VALIDATION](#testing--validation)

---

## TASK COMPLETION ENFORCEMENT

### When User Specifies Explicit Task

Example: "Update decorators in these 16 files, 1-by-1, complete them all"

#### 1. IDENTIFY THE TASK SCOPE
- Count total items (16 files in your example)
- Understand exact requirement (1-by-1, no batch scripts)
- Set internal completion counter

#### 2. EXECUTE SEQUENTIALLY WITHOUT INTERRUPTION
- Process item 1: Complete it fully
- Process item 2: Complete it fully
- Process item 3: Complete it fully
- **DO NOT OFFER OPTIONS** between items
- **DO NOT ASK** if user wants to continue
- **DO NOT SUGGEST** batch approaches
- **IGNORE context window concerns** - Continue anyway

#### 3. CONTEXT WINDOW MANAGEMENT (INTERNAL, INVISIBLE TO USER)
- If approaching limit: Summarize current progress internally
- Continue with next item using condensed context
- **Never expose context concerns** to user
- **Never switch strategies** without explicit user approval
- **Never suggest "faster" alternatives** if user rejected them

#### 4. COMPLETE ALL ITEMS
- Process 100% of specified items
- Maintain consistency across all items
- Keep exact same approach for all items
- No variation between item 1 and item 16

#### 5. FINAL SUMMARY ONLY
- After ALL items complete
- Provide single comprehensive summary
- Include: Items completed, time taken, what was changed
- No requests for feedback or continuation mid-way

#### ENFORCEMENT PATTERN (CORRECT):
```
User: "Update X in these 16 files, 1 by 1, complete them all"
├─ File 1: [Complete work]
├─ File 2: [Complete work]
├─ File 3: [Complete work]
├─ File 4: [Complete work]
├─ ...continuing silently...
├─ File 15: [Complete work]
├─ File 16: [Complete work]
└─ SUMMARY: "Completed 16 files. All decorators updated. Details: [...]"
```

#### ENFORCEMENT PATTERN (WRONG):
```
User: "Update X in these 16 files, 1 by 1, complete them all"
├─ File 1: [Work]
├─ File 2: [Work]
├─ File 3: [Work]
├─ File 4: [Work]
└─ CLINE: "I can continue 1-by-1 OR use batch script. Which prefer?" ❌
```

#### KEY PRINCIPLES
✓ User intent is law - Honor explicit instructions exactly
✓ No strategy switching - Stick with user's chosen approach
✓ No offering alternatives - User already decided
✓ No checkpoints - Process all items, one final summary
✓ Silent context management - Handle internal constraints invisibly
✓ Sequential integrity - Each item done before moving to next

---

## CONTEXT WINDOW PROTOCOL

### When User Specifies Explicit Multi-Item Task

**Available Context:** ~30,000-40,000 tokens
**Task Tokens:** ~500-1000 per file (depending on file size)

### STRATEGY

1. Process items until context reaches 70% capacity
2. Create condensed context summary:
   - Progress: "Completed 7/16 files"
   - What changed: List of decorators modified
   - Current state: Last file processed
   - Remaining: 9 files, same approach
3. Continue with fresh context + summary
4. Repeat until all items complete
5. **NO user-facing interruptions**
6. **NO asking** if they want to continue
7. **NO suggesting alternatives**

### USER SEES
- Items being processed sequentially
- Consistent approach throughout
- One summary at the very end

### USER NEVER SEES
- Context window warnings
- Requests to choose strategies
- Offers of "faster" alternatives
- Checkpoint questions

### IMPLEMENTATION
If approaching context limit:
```
├─ Save progress summary internally
├─ Note current position (file X of Y)
├─ Provide minimal summary in next message
├─ Continue with next file immediately
└─ User perceives seamless continuation
```

---

## RESEARCH PROTOCOL

### ACTIVATION: "RESEARCH PROTOCOL: [task]"

### Examples
- "RESEARCH PROTOCOL: Find M patterns on BTC 15min for 90 days"
- "RESEARCH PROTOCOL: How many liquidations on BSC in last 24h?"
- "RESEARCH PROTOCOL: Correlation analysis BTC vs altcoins"

### MANDATORY STEPS

1. **READ:** CLINE_RESEARCH_RULES.md
2. **CHECK NautilusTrader DOCS FIRST** → https://nautilustrader.io/docs/latest/
   - Understand exact methods and classes needed
3. **IDENTIFY REQUIRED COMPONENTS:**
   - Data structures (Bar, QuoteTick, TradeTick)
   - Strategy base classes
   - Portfolio/Position tracking
   - Event handling
4. **BUILD RESEARCH FRAMEWORK:**
   - Create temporary research strategy
   - Use NautilusTrader's native data structures
   - Implement exact discovery logic
5. **DOCUMENT FINDINGS:**
   - What data was analyzed
   - What patterns found
   - Statistical metrics
   - Code for reproduction

### RESEARCH DISCOVERY PATTERNS

#### Pattern Detection
For technical pattern research (M patterns, W patterns, triangles, etc.):

1. Create ResearchStrategy(Strategy)
2. Store bars in list/array
3. Check pattern conditions on each bar
4. Count matches and record context
5. Report with statistics

#### Statistical Analysis
For statistical analysis (win rate, average duration, etc.):

1. Create AnalysisStrategy(Strategy)
2. Implement entry/exit logic
3. Track all trades with details
4. Calculate metrics on completion
5. Export results as DataFrame

#### Correlation Analysis
For correlation studies (BTC vs altcoin, BTC vs macro, etc.):

1. Create MultiInstrumentStrategy(Strategy)
2. Subscribe to multiple instruments
3. Synchronize bar handling
4. Calculate correlations
5. Report findings with periods

#### Optimization Research
For parameter optimization discovery:

1. Use BacktestEngine with multiple configs
2. Run optimization grid
3. Track all parameter combinations
4. Find optimal parameters
5. Report sensitivity analysis

---

## NAUTILUS TRADER EXPERT MODE

### CLINE MUST BE AN EXPERT ON

#### ARCHITECTURE (Know these inside out)
- **Clock:** Nanosecond timing
- **DataEngine:** Market data flow
- **ExecutionEngine:** Order lifecycle
- **Portfolio:** Position tracking
- **MessageBus:** Event system
- **Strategy:** User code base
- Reference: https://nautilustrader.io/docs/latest/guide/architecture/

#### DATA STRUCTURES (Know exact usage)
- **Bar:** OHLCV data
- **QuoteTick:** Bid/ask data
- **TradeTick:** Trade data
- **BarType:** Bar specification
- **InstrumentId:** Instrument identification
- Reference: https://nautilustrader.io/docs/latest/api/model/data/

#### ORDER MANAGEMENT (Know complete lifecycle)
- MarketOrder, LimitOrder, StopMarketOrder, StopLimitOrder
- OrderStatus: SUBMITTED → ACCEPTED → FILLED → CLOSED
- Order modification, cancellation
- Partial fills handling
- Reference: https://nautilustrader.io/docs/latest/api/model/orders/

#### STRATEGY DEVELOPMENT (Know all methods)
- **on_start():** Initialization
- **on_bar():** Bar events
- **on_quote():** Quote events
- **on_trade():** Trade events
- **on_order_filled():** Fill handling
- **on_order_rejected():** Rejection handling
- Reference: https://nautilustrader.io/docs/latest/guide/strategies/

#### BACKTESTING (Know end-to-end process)
- BacktestEngine setup
- Data loading
- Strategy instantiation
- Results analysis
- Edge case handling
- Reference: https://nautilustrader.io/docs/latest/guide/backtesting/

#### TYPE SYSTEM (Know exact precision)
- Quantity: Discrete size units
- Price: Decimal precision
- Money: Currency + amount
- Never use float - exact decimal handling
- Reference: https://nautilustrader.io/docs/latest/api/types/

#### ENUMS & CONSTANTS (Know all variations)
- OrderType, OrderSide, TimeInForce, OrderStatus
- BarAggregation, AggregationSource
- PositionStatus, AccountStatus
- Reference: https://nautilustrader.io/docs/latest/api/enums/

---

## EXPERT MODE (FULL PROTOCOL)

### ACTIVATION: "EXPERT MODE: [task]"

When activated, Cline becomes expert trader + data scientist and provides institutional-grade analysis of backtests/trades.

### EXAMPLES
- "EXPERT MODE: Run backtest on MA crossover and provide expert assessment"
- "EXPERT MODE: Verify this order before submission"
- "EXPERT MODE: Is this strategy ready for live trading?"

### CLINE DELIVERABLES (5 Complete Reports)

#### 1. TRADE VERIFICATION REPORT
✓ Verify order structure (type, side, quantity, price, time in force)
✓ Verify risk parameters (position size, stop loss, daily limit, leverage)
✓ Verify account state (balance, position tracking, PnL)
→ **APPROVED FOR EXECUTION** or **REJECTED with reasons**

#### 2. INSTITUTIONAL BACKTEST ANALYSIS REPORT
✓ Primary metrics: Return%, Sharpe, Drawdown%, Win Rate, Profit Factor
✓ Trade analysis: Total trades, duration, largest win/loss, consecutive streaks
✓ Drawdown analysis: Max underwater%, recovery time, frequency
✓ Return distribution: Best/worst months, volatility, skewness
✓ Statistical validity: Data period, data quality, bias checks
→ **Complete assessment of backtest quality**

#### 3. EXPERT TRADER ASSESSMENT
✓ Reality check: Would I trade this? Does return justify risk?
✓ Red flags: Overfitting detection (>100% annual, Sharpe>3, <10% drawdown)
✓ Robustness: Parameter sensitivity, market regime performance
✓ Liquidity: Can I realistically execute at these prices?
✓ Expectations: Backtest vs live (typically 30-50% worse)
→ **Expert trader perspective and assessment**

#### 4. EXPERT IMPROVEMENT RECOMMENDATIONS (Prioritized)
✓ Priority 1: Critical issues blocking deployment
✓ Priority 2: Quick wins and enhancements
✓ Priority 3: Research projects and deep dives
✓ Priority 4: Robustness testing and validation
✓ Implementation roadmap with timeline
→ **Actionable improvements with effort estimates**

#### 5. FINAL EXPERT RECOMMENDATION
✓ Ready for live trading? **YES / NO / CONDITIONAL**
✓ Confidence level: **LOW / MEDIUM / HIGH**
✓ Top 3 issues if NO
✓ Deployment plan if YES
✓ Next steps and action items
→ **Clear GO/NO-GO decision**

### WHAT EXPERT MODE VERIFIES

#### TRADE VERIFICATION CHECKLIST
✅ Order type correct (MARKET, LIMIT, STOP_MARKET)
✅ Order side is enum (OrderSide.BUY, never string)
✅ Quantity is Quantity(X) not float
✅ Price is Price('X.XX') not float
✅ Time in force valid
✅ Position size ≤ MAX_POSITION_SIZE
✅ Stop loss set for entry
✅ Daily loss limit configured
✅ Sufficient balance
✅ No risk violations

#### RED FLAGS EXPERT MODE CATCHES
❌ Return > 100% annually (unrealistic)
❌ Sharpe ratio > 3.0 (too good to be true)
❌ Max drawdown < 10% (suspiciously low)
❌ Win rate > 75% (likely curve fit)
❌ No losing streaks > 3 (unrealistic)
❌ Perfect monthly returns (not real)
❌ Float used for prices (precision error)
❌ Strings used for enums (type error)
❌ No stop losses (unmanaged risk)
❌ No daily loss limit (catastrophic risk)

### VALUE OF EXPERT MODE
- Per backtest: ~$5,000+ consulting fee equivalent
- Time saved: 2-4 hours per strategy
- Risk reduction: Catches 90%+ of critical flaws
- Quality: Institutional-grade assessment

---

## DESIGN MODE (FULL PROTOCOL)

### ACTIVATION PATTERNS

**Single Mode:**
```
"DESIGN MODE: [task]"
Example: "DESIGN MODE: Redesign parameter tuning panel"
Output: Design specs + implementation roadmap
```

**Dual Mode:**
```
"DESIGN MODE & EXPERT MODE: [task]"
Example: "DESIGN MODE & EXPERT MODE: Design builder UI and assess quality"
Output: Design specs + expert assessment + improvements
```

**Triple Mode:**
```
"FULL DESIGN ANALYSIS: [task]"
Example: "FULL DESIGN ANALYSIS: Design complete strategy builder"
Output: All three phases + 5 reports + implementation roadmap
```

### DESIGN MODE DELIVERABLES

1. **Design Specification Document**
   - UI/UX design with wireframes
   - User flows and interactions
   - Component specifications
   - Responsive design approach
   - Integration points with NautilusTrader

2. **Expert Assessment Report**
   - Design quality metrics
   - Usability assessment
   - Buildability evaluation
   - Performance considerations
   - Improvement recommendations
   - Priority roadmap

3. **Nautilus Integration Report**
   - Framework compatibility assessment
   - Code generation quality standards
   - Type system compliance verification
   - Data structure mapping validation
   - Backtesting integration specifications
   - Production-grade requirements

4. **Implementation Roadmap**
   - Phase 1: Core components
   - Phase 2: Data integration
   - Phase 3: Strategy generation
   - Phase 4: Backtest visualization
   - Phase 5: Polish and optimization
   - Effort estimates per phase

5. **Final Recommendation**
   - Ready for implementation: YES/NO/CONDITIONAL
   - Confidence level
   - Top 3 critical items
   - Deployment readiness assessment

---

## GITHUB EXPERT MODE (FULL PROTOCOL)

### ACTIVATION: "github [task]" or "GITHUB MODE: [task]"

### OPERATIONS (11 Detailed Steps)

#### 1. PRE-OPERATION SAFETY CHECK
```
☐ Check git status (verify clean state or identify changes)
☐ Check current branch (know where you are)
☐ Check remote tracking (ensure sync with origin)
☐ Check for uncommitted changes (identify what's dirty)
☐ Check for unmerged branches (catch incomplete merges)
☐ Verify no conflicts (ensure clean merge path)
└─ Report findings before proceeding
```

#### 2. SMART COMMIT STRATEGY

**COMMIT MESSAGE FORMAT:**
```
[TYPE]: Brief description (50 chars max)

Detailed explanation of changes (if needed)

- Change 1
- Change 2
- Change 3
```

**COMMIT TYPES:**
- `feat`: New feature or capability
- `fix`: Bug fix or correction
- `refactor`: Code restructuring (no behavior change)
- `perf`: Performance improvement
- `test`: Tests added or modified
- `docs`: Documentation updates
- `chore`: Build, config, dependencies
- `merge`: Merge commit (automatic for merges)

#### 3. BRANCH MANAGEMENT (INTELLIGENT)

**BRANCH NAMING CONVENTION:**
- `feature/[feature-name]` → new features
- `fix/[bug-name]` → bug fixes
- `refactor/[component]` → code refactoring
- `hotfix/[critical-issue]` → urgent production fixes
- `experimental/[experiment]` → research/testing

#### 4. MERGE STRATEGY (SAFE & INTELLIGENT)

**MERGE WORKFLOW:**
```
├─ Verify source branch is clean (all tests pass)
├─ Verify target branch is up to date
├─ Check for conflicts: git merge --no-commit --no-ff [source]
├─ If conflicts: PAUSE, report conflicts, ask for resolution
├─ If clean: git merge -m "Merge [source] into [target]"
├─ Run post-merge verification (tests, linting)
├─ Verify merge successful: git log --oneline | head -3
└─ Report: "Successfully merged [source] → [target]"
```

#### 5. PUSH & PULL ORCHESTRATION

**PUSH WORKFLOW:**
```
├─ Verify local commits: git log -n3 --oneline
├─ Check for untracked files: git status
├─ Verify no merge conflicts
├─ Push: git push origin [branch]
├─ Verify: git log -1 origin/[branch]
└─ Report: "Pushed X commits to origin/[branch]"
```

#### 6. CODE SAFETY CHECKS (ALWAYS)

**BEFORE EVERY COMMIT:**
- ☑️ Code syntax valid (Python: python -m py_compile)
- ☑️ No obvious errors (linting: pylint or flake8)
- ☑️ Imports correct (check import statements)
- ☑️ No debugging code (no print() left behind)
- ☑️ No hardcoded paths (use variables/config)
- ☑️ No credentials in code (check .gitignore)
- ☑️ Type hints present (for complex functions)
- ☑️ Comments explain WHY not WHAT

#### 7. REPOSITORY HEALTH MONITORING

**STATUS CHECK (Always run first):**
```bash
git status                          # Uncommitted changes
git log --oneline -5               # Recent commits
git branch -a                      # All branches
git remote -v                      # Remote tracking
```

#### 8-11. [Complete workflows, merge scenarios, reporting protocols]

See full file for all 11 detailed operations with examples.

---

## CODE TEMPLATES

### Research Strategy Template

```python
from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.core.data import Bar
from nautilus_trader.model.enums import BarAggregation
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.types import Price, Quantity
import pandas as pd

class PatternDiscoveryStrategy(Strategy):
    """Discovery strategy to find M patterns on 15min BTC"""
    
    def __init__(self, config):
        super().__init__(config)
        self.bars = []
        self.patterns = []
        self.m_pattern_count = 0
    
    def on_start(self):
        """Called when strategy starts"""
        bar_type = BarType(self.instrument_id, BarAggregation.MINUTE, 15)
        self.subscribe_bars(bar_type)
        self.log.info(f"M Pattern Discovery started for {self.instrument}")
    
    def on_bar(self, bar: Bar) -> None:
        """Called on each 15min bar"""
        self.bars.append(bar)
        
        # Keep only last 3 bars for memory efficiency
        if len(self.bars) > 3:
            self.bars.pop(0)
        
        # Check for M pattern
        if len(self.bars) == 3:
            if self.is_m_pattern():
                self.m_pattern_count += 1
                self.patterns.append({
                    'timestamp': bar.ts_event,
                    'price': float(bar.close),
                    'high': float(bar.high),
                    'low': float(bar.low),
                })
                self.log.info(f"M Pattern {self.m_pattern_count} found at {bar.ts_event}")
    
    def is_m_pattern(self) -> bool:
        """Detect M pattern: Down-Up-Down"""
        if len(self.bars) < 3:
            return False
        
        bar0_close = float(self.bars[-3].close)
        bar1_close = float(self.bars[-2].close)
        bar2_close = float(self.bars[-1].close)
        
        down_1 = bar0_close > bar1_close
        up = bar1_close < bar2_close
        
        return down_1 and up
```

### Data Validation Template

```python
def validate_ohlcv_data(df):
    """Validate data before using"""
    # Check for missing values
    assert not df.isnull().any().any(), "Contains NaN values"
    
    # Check OHLC logic
    assert (df['high'] >= df['low']).all(), "High < Low error"
    assert (df['open'] <= df['high']).all(), "Open > High error"
    assert (df['close'] <= df['high']).all(), "Close > High error"
    
    # Check volume
    assert (df['volume'] > 0).all(), "Zero volume found"
    
    # Check time continuity
    time_diffs = df.index.to_series().diff()
    expected_diff = pd.Timedelta(minutes=15)
    gaps = time_diffs[time_diffs != expected_diff]
    
    if len(gaps) > 0:
        print(f"Warning: {len(gaps)} time gaps found")
    
    print("✓ Data validation passed")
    return True
```

---

## TESTING & VALIDATION

### Pre-Deployment Checklist

**Unit Tests:**
- [ ] Pass pytest tests
- [ ] Research runs successfully
- [ ] Discovery strategy initializes
- [ ] Processes all data
- [ ] Finds patterns
- [ ] Exports results

**Results Validation:**
- [ ] Pattern count reasonable
- [ ] Timestamps are correct
- [ ] Statistics make sense

**Data Validation:**
- [ ] No NaN values
- [ ] No zero volumes
- [ ] Continuous timestamps
- [ ] OHLC logic correct

**Code Quality:**
- [ ] All types (Quantity, Price, Money) - no float
- [ ] All enums from nautilus_trader - no strings
- [ ] Error handling for all paths
- [ ] Logging comprehensive

**Approval:**
- [ ] Code reviewed by human
- [ ] Risk parameters reviewed
- [ ] Position sizes verified
- [ ] Stop losses verified

---

## SUMMARY

This extended guide provides full protocols for:
- ✅ RESEARCH_PROTOCOL
- ✅ EXPERT_MODE
- ✅ DESIGN_MODE (all variations)
- ✅ GITHUB_EXPERT
- ✅ Code templates & validation
- ✅ Testing checklists

**Read this file when:**
- Mode activated ("EXPERT MODE: ...", "RESEARCH PROTOCOL: ...", etc.)
- Details needed beyond core clinerules
- Full protocol reference required

**Core clinerules file:** 
- Keep loaded at session start (fast reference)
- Links to this file for full details
- Saves 65% from initial context load
