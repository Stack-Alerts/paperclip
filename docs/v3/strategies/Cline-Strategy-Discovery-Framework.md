# Cline Strategy Framework Implementation Guide
## Autonomous Strategy Discovery & Optimization for NautilusTrader

**Purpose:** Enable Cline (Claude 4.5 Sonnet) to discover, implement, and optimize new trading strategies within your existing NautilusTrader infrastructure

**Your Current State:**
- ✅ NautilusTrader framework fully integrated
- ✅ Building blocks implemented and validated
- ✅ Backtesting infrastructure operational
- ✅ Walk-forward analysis working
- ✅ 2 optimized, production strategies (M Pattern & W Pattern)

**Cline's Role:** Autonomous discovery and optimization of new trading strategies following your proven methodology

**Status:** Production-Ready Implementation Framework  
**Date:** December 31, 2025

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Your Current M & W Pattern Strategies](#your-current-m--w-pattern-strategies)
3. [Strategy Discovery Framework](#strategy-discovery-framework)
4. [Cline Implementation Workflow](#cline-implementation-workflow)
5. [Pattern Recognition Engine](#pattern-recognition-engine)
6. [Backtesting & Validation Protocol](#backtesting--validation-protocol)
7. [Parameter Optimization Methodology](#parameter-optimization-methodology)
8. [Production Readiness Criteria](#production-readiness-criteria)
9. [Cline Prompting Guide](#cline-prompting-guide)

---

## Executive Summary

### Your Competitive Advantage

You have **two proven strategies** (M Pattern & W Pattern) that produce excellent results. Now you can use Cline to systematically discover new high-probability patterns without manual analysis.

**The Opportunity:**
- Your building blocks are validated and working
- Your backtesting/walkforward is proven
- Your risk management is operational
- **Gap:** Limited human time to manually discover and test new patterns

**The Solution:**
Enable Cline to autonomously:
1. Identify new price action patterns (visual and statistical)
2. Implement them as NautilusTrader strategies
3. Backtest with your proven methodology
4. Optimize parameters via walk-forward
5. Validate statistical significance
6. Report only production-ready strategies

### Expected Outcomes

**Conservative Estimate (6 months):**
- 5-10 new validated strategies
- 30%+ improvement in overall portfolio correlation
- Additional 2-3% annual return from strategy diversification
- Reduced drawdown from better strategy mix

---

## Your Current M & W Pattern Strategies

### M Pattern Strategy (Double Top Reversal)

**Pattern Definition:**
```
PRICE ACTION:
  1. Strong uptrend with initial peak (Peak 1)
  2. Price retraces to support level (Neckline)
  3. Price rallies but fails to exceed Peak 1 (Peak 2, lower than Peak 1)
  4. Price breaks below Neckline = BEARISH CONFIRMATION
  
VISUAL SHAPE: "M" with two peaks of decreasing height

ENTRY SIGNAL: Confirmed break below neckline + volume spike
EXIT SIGNAL: Previous peak or measured move projection
STOP LOSS: Above the second peak + margin
```

**Your Implementation Details:**
```python
# Key parameters from your working code:
peak_detection_lookback = 20  # bars
neckline_tolerance = 0.02     # 2% variance allowed
volume_confirmation = 1.5     # Volume must be >1.5× average
breakout_bars = 1-2           # Confirmation within 1-2 bars

# Risk Management:
max_risk_per_trade = 0.02     # 2% of account
atr_multiplier = 1.5          # Stop = Peak + 1.5×ATR
take_profit_ratio = 2.0       # TP = 2× risk distance
```

**Performance (Your Data):**
- Win Rate: [Your actual % from backtesting]
- Profit Factor: [Your actual from backtesting]
- Sharpe Ratio: [Your actual from backtesting]
- Max Drawdown: [Your actual from backtesting]

### W Pattern Strategy (Double Bottom Reversal)

**Pattern Definition:**
```
PRICE ACTION:
  1. Downtrend with initial low (Low 1)
  2. Price rebounds to resistance (Neckline/middle high)
  3. Price declines again but doesn't break Low 1 (Low 2, higher than Low 1)
  4. Price breaks above Neckline = BULLISH CONFIRMATION
  
VISUAL SHAPE: "W" with two lows of increasing height

ENTRY SIGNAL: Confirmed break above neckline + volume spike
EXIT SIGNAL: Previous high or measured move projection
STOP LOSS: Below the second low + margin
```

**Your Implementation Details:**
```python
# Key parameters from your working code:
low_detection_lookback = 20   # bars
neckline_tolerance = 0.02     # 2% variance allowed
volume_confirmation = 1.5     # Volume must be >1.5× average
breakout_bars = 1-2           # Confirmation within 1-2 bars

# Risk Management:
max_risk_per_trade = 0.02     # 2% of account
atr_multiplier = 1.5          # Stop = Low - 1.5×ATR
take_profit_ratio = 2.0       # TP = 2× risk distance
```

**Performance (Your Data):**
- Win Rate: [Your actual % from backtesting]
- Profit Factor: [Your actual from backtesting]
- Sharpe Ratio: [Your actual from backtesting]
- Max Drawdown: [Your actual from backtesting]

### Why These Patterns Work for Bitcoin

1. **Clear Visual Definition:** Easy to identify programmatically
2. **Institutional Footprints:** Reflect buyer/seller exhaustion
3. **Measurable:** Neckline, peaks/lows, volume all quantifiable
4. **Multi-Timeframe:** Work on 1h, 4h, daily for BTC
5. **Reversals:** High probability when combined with confluence

---

## Strategy Discovery Framework

### Pattern Categories Cline Should Focus On

**Tier 1: High-Probability (Similar to M & W)**
- Triple Tops/Bottoms (3 peaks/lows)
- Ascending/Descending Triangles (breakout patterns)
- Head & Shoulders (volume-weighted reversal)
- Wedges (momentum acceleration)
- Cup & Handle (continuation pattern)

**Tier 2: Statistical Patterns**
- Engulfing Candlesticks (with confluence)
- Pin Bars (rejection wicks)
- Morning Star / Evening Star (3-bar reversals)
- Harami (inside reversal bars)

**Tier 3: Confluence-Based**
- Moving Average Crossovers + Divergence
- Order Block + FVG (Smart Money)
- Support/Resistance Breakouts + Volume
- Fibonacci Retracement + Oscillator

**NOT Worth Pursuing:**
- Harmonic patterns (too complex, similar results to simpler patterns)
- Elliott Wave (subjective, hard to program reliably)
- Pure indicator-based (you need structure + confluence)

### Discovery Methodology

Cline should follow this systematic approach:

```
1. PATTERN HYPOTHESIS
   - Select specific pattern type
   - Define entry conditions mathematically
   - Define exit conditions
   - Define stop-loss mechanics
   
2. DEFINITION VALIDATION
   - Can pattern be identified programmatically?
   - Can entry/exit be non-ambiguous?
   - Can stop-loss be placed precisely?
   - Does pattern occur frequently enough? (>5 per month on 4h BTC)
   
3. SKELETON IMPLEMENTATION
   - Write pattern detection code
   - Implement entry/exit logic
   - Test on 1-2 weeks of live data (manual inspection)
   
4. BACKTEST PHASE 1 (Initial Validation)
   - Run 1 year backtest (2024)
   - Calculate basic metrics
   - Check win rate > 45%, profit factor > 1.2
   - If passes, continue to Phase 2
   
5. BACKTEST PHASE 2 (Extended Validation)
   - Run 3 year backtest (2022-2025)
   - Multiple market regimes (bull 2024, bear 2022, consolidation 2023)
   - Win rate > 50%, profit factor > 1.5
   - Sharpe ratio > 0.8
   
6. WALK-FORWARD OPTIMIZATION
   - Use your proven walkforward protocol
   - Parameters must remain consistent across windows
   - Out-of-sample performance must be >80% of in-sample
   
7. PRODUCTION READINESS
   - Passes all validation criteria (see section)
   - Correlation < 0.7 with M & W patterns
   - Risk-adjusted return comparable to M & W
   - Full documentation with evidence
   
8. DEPLOYMENT
   - Paper trading 2-4 weeks
   - Live deployment with position sizing
   - Continuous monitoring
```

---

## Cline Implementation Workflow

### Workflow 1: Pattern Discovery Brainstorm

**Prompt to Cline:**

```
You are implementing new trading strategy discovery for a Bitcoin trading system 
running NautilusTrader with proven M Pattern and W Pattern strategies.

TASK: Identify 5 promising chart patterns for Bitcoin 4h/daily timeframes.

CRITERIA FOR PATTERNS:
- Easy to identify programmatically (non-subjective)
- Occur frequently on BTC (5+ per month on 4h)
- Have clear entry/exit conditions
- Work with ATR-based stops
- NOT already implemented (M & W patterns exist)
- Historical evidence of >50% win rate

PATTERNS TO EVALUATE:
1. Triple Top/Bottom (like M pattern but 3 peaks instead of 2)
2. Ascending/Descending Triangle (consolidation + breakout)
3. Head & Shoulders (large reversal with volume)
4. Cup & Handle (rounding reversal continuation)
5. Wedge Pattern (momentum decline before breakout)

FOR EACH PATTERN:
1. Explain structure and identification rules
2. Define entry conditions (specific, measurable)
3. Define exit conditions
4. Explain why it should work for Bitcoin
5. List potential false signal filters
6. Recommend best timeframe(s)
7. Rate feasibility (1-10) for implementation

PRIORITIZE: Patterns that are similar in mechanics to M & W 
(clear structure, volume confirmation, ATR-based stops).

OUTPUT: Ranked list with implementation difficulty and estimated edge.
```

### Workflow 2: Pattern Implementation

**Prompt to Cline:**

```
Implement the [PATTERN NAME] pattern strategy for NautilusTrader.

PATTERN SPECIFICATION:
[Paste detailed pattern definition from discovery phase]

REQUIREMENTS:
1. Inherit from your BaseStrategy class
2. Implement pattern detection algorithm
3. Generate entry signals with confidence score
4. Implement ATR-based stop-loss
5. Use position sizing formula: (account_size × 0.02) / stop_distance
6. Log all pattern detections for debugging
7. Include configuration parameters (externalizable to YAML)

CODE STRUCTURE:
- Class: [PatternName]Strategy(BaseStrategy)
- Config: [PatternName]StrategyConfig(BaseStrategyConfig)
- Methods:
  - on_start(): Initialize indicators
  - on_bar(): Process each bar
  - _detect_pattern(): Return (is_forming, confidence)
  - _validate_entry(): Check all entry conditions
  - _handle_entry(): Submit order with stop

TESTING:
1. Write unit test for pattern detection
2. Test on 50 bars with known patterns (visual inspection)
3. Verify false signal rate < 30%

PARAMETERS TO EXTERNALIZE:
- lookback_period (bars for pattern formation)
- volume_confirmation_multiplier (volume threshold)
- tolerance_percent (allowed variance)
- atr_period (for stop-loss calculation)
- atr_multiplier (stop distance multiplier)

OUTPUT:
- strategies/[pattern_name]_strategy.py (complete implementation)
- config/[pattern_name]_config.yaml (example configuration)
- Unit tests
- Implementation notes (how pattern works, any assumptions)
```

### Workflow 3: Initial Validation (1-Year Backtest)

**Prompt to Cline:**

```
Run initial backtest validation of [PATTERN NAME] strategy.

BACKTEST PARAMETERS:
- Instrument: BTC/USDT (4h bars)
- Period: 2024 (1 year, single year)
- Data: Use your existing Parquet data
- Account: $100,000
- Risk per trade: 2%
- Commission: 0.1% (Binance spot)
- Slippage: 0.02% (conservative)

EXECUTION:
1. Load 2024 data
2. Run backtest with default parameters
3. Extract statistics:
   - Total return %
   - Annual return %
   - Win rate %
   - Profit factor
   - Sharpe ratio
   - Max drawdown %
   - Number of trades
   - Avg bars in trade
   - Best and worst periods

DECISION GATES (must pass ALL):
□ Win rate >= 45%
□ Profit factor >= 1.2
□ Number of trades >= 10 in year (avg 1 per month minimum)
□ Max drawdown <= 15%

PASS RESULT:
- Continue to Extended Validation (Phase 2)
- Print: "PASS - Proceed to 3-year backtest"

FAIL RESULT:
- Recommend parameter adjustment
- Print: "FAIL - Recommend [specific parameter changes]"

OUTPUT:
```
[PATTERN NAME] - Initial Validation Results
Start Date: 2024-01-01
End Date: 2024-12-31

Performance Metrics:
  Total Return: [X]%
  Annual Return: [X]%
  Win Rate: [X]%
  Profit Factor: [X]
  Sharpe Ratio: [X]
  Max Drawdown: [X]%
  
Trade Summary:
  Total Trades: [X]
  Winning Trades: [X]
  Losing Trades: [X]
  Avg Trade Duration: [X] hours
  
Decision: [PASS/FAIL]
Recommendation: [Next steps]
```
```

### Workflow 4: Extended Validation (3-Year Backtest)

**Prompt to Cline:**

```
Run extended validation backtest of [PATTERN NAME] strategy.

BACKTEST PARAMETERS:
- Instrument: BTC/USDT (4h bars)
- Period: 2022-2025 (3 years, multiple market regimes)
- Account: $100,000
- Risk per trade: 2%
- Commission: 0.1%
- Slippage: 0.02%

TESTING ACROSS REGIMES:
1. Full period 2022-2025 (overall)
2. Bear market: 2022 (May-Dec) - prices declining
3. Recovery: 2023 (Jan-Dec) - consolidation/buildup
4. Bull market: 2024 (Jan-Dec) - strong uptrend

EXECUTION:
1. Load 2022-2025 data
2. Run full backtest
3. Analyze by regime (three separate analyses)
4. Extract metrics for each period

DECISION GATES (must pass ALL for full period):
□ Win rate >= 50%
□ Profit factor >= 1.5
□ Sharpe ratio >= 0.8
□ Max drawdown <= 20%
□ Consistent performance across regimes (no regime >50% worse than average)

REGIME-SPECIFIC ANALYSIS:
For each regime, calculate:
- Win rate
- Profit factor
- Return (%)
- Max drawdown (%)
- Note volatility and trend characteristics

OUTPUT:
```
[PATTERN NAME] - Extended Validation Results
Period: 2022-2025 (3 Years)

Overall Performance:
  Total Return: [X]%
  Annual Return: [X]%
  Win Rate: [X]%
  Profit Factor: [X]
  Sharpe Ratio: [X]
  Max Drawdown: [X]%
  Total Trades: [X]

Regime Analysis:
  
  2022 (Bear Market - BTCUSDT $19k-$42k)
    Return: [X]%, Win Rate: [X]%, Profit Factor: [X]
    
  2023 (Consolidation - BTCUSDT $16k-$42k)
    Return: [X]%, Win Rate: [X]%, Profit Factor: [X]
    
  2024 (Bull Market - BTCUSDT $42k-$108k)
    Return: [X]%, Win Rate: [X]%, Profit Factor: [X]

Consistency Assessment:
  Best Regime Return: [X]%
  Worst Regime Return: [X]%
  Ratio: [X]x (>2x = concerning)

Decision: [PASS/FAIL]
Next Step: [Proceed to walk-forward or adjust parameters]
```
```

### Workflow 5: Walk-Forward Optimization

**Prompt to Cline:**

```
Run walk-forward optimization of [PATTERN NAME] strategy.

PARAMETERS TO OPTIMIZE:
[List parameters from strategy config, e.g.]
- lookback_period: [range, e.g., 15-30]
- volume_multiplier: [range, e.g., 1.0-2.0]
- tolerance_percent: [range, e.g., 0.01-0.05]
- atr_multiplier: [range, e.g., 1.0-2.5]

WALK-FORWARD SETUP:
- Training period: 252 days (1 year)
- Test period: 21 days (1 month rolling forward)
- Data: Full 2022-2025 period
- Rolling windows: ~12 windows (one per quarter across 3 years)

OPTIMIZATION METHOD:
For each window:
  1. Optimize parameters on training period
  2. Test optimized params on test period (unseen data)
  3. Record results
  
SELECTION CRITERIA:
- Optimize for: Sharpe ratio (not just return)
- Constraint: Win rate >= 50%
- Constraint: Profit factor >= 1.5

VALIDATION:
- In-sample Sharpe: [Average of training periods]
- Out-of-sample Sharpe: [Average of test periods]
- Degradation: Must be <20% (OOS/IS ratio > 0.8)
- If >20% degradation = overfitting concern

OUTPUT:
```
[PATTERN NAME] - Walk-Forward Optimization Results

Optimization Period: 2022-2025
Rolling Windows: 12 quarters

Window Results:
  Q1 2022: In-Sample Sharpe [X], Out-of-Sample Sharpe [X]
  Q2 2022: In-Sample Sharpe [X], Out-of-Sample Sharpe [X]
  ... (10 more windows)

Recommended Parameters (average across all windows):
  lookback_period: [X]
  volume_multiplier: [X]
  tolerance_percent: [X]
  atr_multiplier: [X]

Overall Statistics:
  Avg In-Sample Sharpe: [X]
  Avg Out-of-Sample Sharpe: [X]
  Degradation: [X]% (Overfitting: YES/NO)
  Consistency: [X] (std dev of OOS Sharpe)

Robustness Assessment:
  - Parameters stable across periods? [YES/NO]
  - Performance consistent across regimes? [YES/NO]
  - Degradation within acceptable range? [YES/NO]

Decision: [READY FOR DEPLOYMENT / NEEDS REVISION / REJECT]
```
```

### Workflow 6: Correlation & Ensemble Check

**Prompt to Cline:**

```
Check correlation and ensemble fit of [PATTERN NAME] with M & W patterns.

OBJECTIVE:
Verify that new strategy is NOT just duplicating M & W patterns,
and that it adds diversification to the trading system.

METHODOLOGY:
1. Extract monthly returns from:
   - M Pattern strategy (your baseline)
   - W Pattern strategy (your baseline)
   - [NEW PATTERN] strategy (candidate)

2. Calculate Pearson correlation between:
   - M vs W (expect: 0.4-0.7)
   - M vs New (expect: <0.7)
   - W vs New (expect: <0.7)

3. Portfolio simulation:
   - Test equal weighting: (M + W + New) / 3
   - Calculate portfolio Sharpe ratio
   - Calculate portfolio max drawdown
   - Compare to best single strategy

ACCEPTANCE CRITERIA:
□ Correlation with M < 0.7
□ Correlation with W < 0.7
□ Portfolio Sharpe > max(M_Sharpe, W_Sharpe, New_Sharpe)
□ Portfolio max DD < (M_DD + W_DD + New_DD) / 3

PORTFOLIO BENEFIT:
If ensemble Sharpe = 1.2 and max individual = 1.0:
  Benefit = (1.2 - 1.0) / 1.0 = 20% improvement

OUTPUT:
```
[PATTERN NAME] - Correlation & Ensemble Analysis

Correlation Matrix:
            M-Pattern  W-Pattern  New-Pattern
M-Pattern      1.00       0.52       0.41
W-Pattern      0.52       1.00       0.38
New-Pattern    0.41       0.38       1.00

Portfolio Analysis (Equal Weight 1/3 each):
  Individual Sharpe Ratios:
    M Pattern:    [X]
    W Pattern:    [X]
    New Pattern:  [X]
  
  Portfolio Sharpe: [X]
  Improvement: [+X]% vs best single strategy
  
  Individual Max Drawdowns:
    M Pattern:    [X]%
    W Pattern:    [X]%
    New Pattern:  [X]%
  
  Portfolio Max DD: [X]%
  Improvement: [-X]% vs avg individual

Diversification Score: [X]/10
  (Higher = better diversification benefit)

Decision: [ACCEPT - Good ensemble fit / REJECT - Redundant]
```
```

### Workflow 7: Production Readiness Report

**Prompt to Cline:**

```
Generate production readiness report for [PATTERN NAME].

CHECKLIST:

STRATEGY LOGIC:
□ Entry conditions unambiguous (yes/no, not maybe)
□ Exit conditions clearly defined
□ Stop-loss mechanism implemented
□ Position sizing correct (2% risk formula)
□ No look-ahead bias in code
□ All parameters externalized to config

BACKTESTING:
□ 1-year initial validation: PASS
□ 3-year extended validation: PASS (all regimes)
□ Walk-forward optimization: PASS (OOS Sharpe > 80% of IS)
□ Overfit assessment: PASS (degradation < 20%)
□ Robust parameters identified

STATISTICAL VALIDATION:
□ Win rate >= 50%
□ Profit factor >= 1.5
□ Sharpe ratio >= 0.8
□ Max drawdown <= 20%
□ Trades per month >= 5 (liquid enough to trade)

ENSEMBLE FIT:
□ Correlation with M Pattern < 0.7
□ Correlation with W Pattern < 0.7
□ Portfolio Sharpe improves > 10%
□ Diversification benefit confirmed

IMPLEMENTATION:
□ Code follows BaseStrategy pattern
□ Type hints on all methods
□ Docstrings complete
□ Unit tests written and passing
□ Configuration YAML example provided
□ No bugs or error handling gaps

DOCUMENTATION:
□ Pattern explanation with visuals
□ Entry/exit logic documented
□ Risk management rules stated
□ Backtest results summarized
□ Parameters with ranges explained
□ References to research (if any)

DEPLOYMENT READINESS:
□ 2-4 weeks paper trading scheduled
□ Monitoring setup planned
□ Emergency stop mechanism exists
□ Position limits defined
□ Correlation with live portfolio calculated

OUTPUT:
```
[PATTERN NAME] STRATEGY - PRODUCTION READINESS REPORT
Generated: [DATE]

OVERALL DECISION: ✅ APPROVED FOR DEPLOYMENT

Checklist Summary: [X/30 items passed]

Key Metrics:
  Win Rate: [X]% ✅
  Profit Factor: [X] ✅
  Sharpe Ratio: [X] ✅
  Correlation (M): [X] ✅
  Correlation (W): [X] ✅

Critical Pass/Fail Items:
  - Backtest validation: PASS
  - Walk-forward robustness: PASS
  - Ensemble fit: PASS
  - Code quality: PASS
  
Failed Items (if any):
  [List any items not meeting criteria]

Deployment Plan:
  1. Paper trading: [DATE] for 2-4 weeks
  2. Live deployment: [DATE]
  3. Position limit: $[X] per trade
  4. Daily monitoring: [TIME]
  5. Monthly review: Performance check

Risk Assessment:
  - New strategy drawdown: [X]%
  - Portfolio max DD (3 strategies): [X]%
  - Correlation risk: [LOW/MEDIUM/HIGH]

Expected Impact:
  - Additional annual return: +[X]%
  - Sharpe ratio improvement: +[X]%
  - Portfolio drawdown reduction: -[X]%

Recommendation: PROCEED WITH DEPLOYMENT ✅
```
```

---

## Pattern Recognition Engine

### How Cline Should Think About New Patterns

**Checklist for Valid Patterns:**

1. **Visual Clarity**
   - Can be drawn on a chart clearly?
   - Can be described in 1-2 sentences?
   - Would multiple traders identify it the same way?

2. **Mathematical Precision**
   - Can entry condition be coded as `if/else`?
   - Are thresholds measurable (not subjective)?
   - Can false signals be filtered?

3. **Frequency**
   - Does pattern occur at least 5-10 times per year on 4h BTC?
   - Too rare = insufficient sample size
   - Too common = might be noise

4. **Signal Quality**
   - Can historical patterns be located/counted?
   - Do identified patterns produce >50% winning trades?
   - Is edge sustainable across market regimes?

5. **Risk Management**
   - Can stop-loss be placed precisely?
   - Does stop distance allow ATR-based scaling?
   - Can position be sized using 2% risk formula?

### Patterns Cline Should Explore

**High Priority (likely to work):**
```
1. Triangle Patterns (Ascending/Descending/Symmetrical)
   - Clear support/resistance lines
   - Volume dries up during formation
   - Breakout direction is the trade
   
2. Head & Shoulders
   - Left shoulder, head, right shoulder with neckline
   - Volume decreases going into right shoulder
   - Neckline break = entry
   
3. Cup & Handle
   - U-shaped consolidation followed by pullback
   - Volume U-shape (high at lows, low at handle)
   - Break above handle = entry
   
4. Triple Top/Bottom
   - Extension of M pattern to 3 peaks/lows
   - Each peak/low should be roughly equal
   - Pattern completion at neckline break
```

**Medium Priority (worth testing):**
```
1. Wedges (Rising/Falling)
   - Two converging trendlines
   - Volume declining
   - Breakout in either direction
   
2. Flag & Pennant
   - Sharp move followed by tight consolidation
   - Flag = parallelogram shape
   - Pennant = triangle shape
   - Volume spike on breakout
   
3. Diamond Pattern
   - Widening then narrowing price action
   - Usually reversal pattern
   - Breakout direction is the trade
```

**Lower Priority (likely duplicate your existing patterns):**
```
- Harmonic patterns (too complex)
- Fibonacci sequences (arbitrary levels)
- Pure indicator crossovers (no structure)
- Moving average systems (too many false signals)
```

---

## Backtesting & Validation Protocol

### Your Proven Methodology

You have working backtest and walk-forward infrastructure. Cline should:

1. **Use your existing BacktestEngine class**
   - Don't rewrite, just instantiate with new strategy
   - All commission, slippage, data handling already correct

2. **Follow your proven data format**
   - Parquet files with proper time indexing
   - BTCUSDT 4h bars (or other timeframes as specified)
   - UTC timezone consistency

3. **Use your risk management constants**
   ```python
   MAX_RISK_PER_TRADE = 0.02        # 2%
   MAX_POSITION_SIZE = 0.10         # 10% account
   MAX_DAILY_LOSS = 0.05            # 5%
   ATR_PERIOD = 14
   ```

4. **Extract metrics in your standard format**
   - Win rate, profit factor, Sharpe, max DD
   - Monthly returns for correlation analysis
   - Trade log for debugging

### Validation Thresholds

**Minimum Acceptable Performance:**
```
Initial (1-year) Backtest:
  ✓ Win rate >= 45%
  ✓ Profit factor >= 1.2
  ✓ Trades >= 10/year
  ✓ No catastrophic loss month
  
Extended (3-year) Backtest:
  ✓ Win rate >= 50%
  ✓ Profit factor >= 1.5
  ✓ Sharpe ratio >= 0.8
  ✓ Max drawdown <= 20%
  ✓ Consistent across regimes
  
Walk-Forward Analysis:
  ✓ Out-of-sample Sharpe >= 80% of in-sample
  ✓ Parameters stable across windows
  ✓ No optimization cliff (performance doesn't collapse in certain periods)
  
Ensemble Fit:
  ✓ Correlation with M < 0.7
  ✓ Correlation with W < 0.7
  ✓ Portfolio benefit >= 10%
```

**When to Reject a Pattern:**
```
Automatic Rejection:
- Win rate < 45% on 1-year test
- Profit factor < 1.2
- > 30% max drawdown
- Fails to work in one market regime (e.g., 20% return in bull, -5% in bear)
- Same entry signals as M or W patterns (correlation > 0.8)
- Cannot be traded (too few signals or ambiguous)
- Walk-forward shows >30% degradation (overfitted)
```

---

## Parameter Optimization Methodology

### Your Approach: Walk-Forward Analysis

Your existing walkforward implementation should be leveraged:

```python
def run_walk_forward(strategy_class, parameters, data):
    """
    Proven walkforward protocol:
    1. Divide data into rolling training + test windows
    2. Optimize parameters on training
    3. Test on unseen test period
    4. Report out-of-sample performance
    5. Repeat with rolling window
    """
    
    results = []
    
    for training_period, test_period in rolling_windows(data):
        # Optimize on training
        best_params = optimize(strategy_class, parameters, training_period)
        
        # Test on unseen data
        oos_performance = backtest(strategy_class, best_params, test_period)
        
        results.append({
            'params': best_params,
            'oos_sharpe': oos_performance.sharpe,
            'oos_win_rate': oos_performance.win_rate,
        })
    
    return results
```

### Parameter Ranges for New Patterns

When implementing a new pattern, Cline should test reasonable ranges:

```python
# Peak/Low Detection
lookback_period = [15, 20, 25, 30]  # bars to look back for extremes

# Volume Confirmation
volume_multiplier = [1.0, 1.25, 1.5, 1.75, 2.0]  # × 20-period avg

# Pattern Tolerance
tolerance_percent = [0.01, 0.015, 0.02, 0.025, 0.03]  # ±% of price

# Stop-Loss
atr_multiplier = [1.0, 1.25, 1.5, 1.75, 2.0]  # × ATR for stop

# Other
min_pattern_bars = [1, 2, 3]  # bars to confirm pattern completion
```

### How to Avoid Overfitting

1. **Use walk-forward, not grid-search on full data**
   - Never optimize on entire dataset
   - Always test on unseen walk-forward period
   
2. **Require out-of-sample performance >= 80% of in-sample**
   - If IS Sharpe = 1.5, OOS must be >= 1.2
   - If OOS << 0.8×IS, pattern is overfit
   
3. **Monitor parameter stability**
   - Do optimal parameters change significantly across windows?
   - If yes, pattern may be capturing noise
   - Use average/median parameters across all windows
   
4. **Test across multiple regimes**
   - Pattern must work in bull, bear, and consolidation
   - If only works in one regime, it's regime-dependent (risky)

---

## Production Readiness Criteria

### Code Quality Checklist

```python
# All new strategies must have:

1. Proper inheritance
   class [Pattern]Strategy(BaseStrategy): ✓
   
2. Type hints
   def on_bar(self, bar: Bar) -> None: ✓
   
3. Docstrings
   """Strategy for [Pattern Name]"""
   
4. Configuration separation
   class [Pattern]Config(BaseStrategyConfig): ✓
   
5. Proper error handling
   try/except for edge cases: ✓
   
6. Logging
   self.logger.info() for all key events: ✓
   
7. Unit tests
   def test_pattern_detection(): ✓
   def test_entry_conditions(): ✓
   def test_position_sizing(): ✓
```

### Backtest Result Documentation

Every new strategy must include:

```
Strategy: [Name]
Period: [2022-2025] (3 years)
Instrument: BTC/USDT, 4h bars
Account: $100,000, 2% risk per trade

OVERALL RESULTS:
  Total Return: [X]%
  Annual Return: [X]%
  Win Rate: [X]%
  Profit Factor: [X]
  Sharpe Ratio: [X]
  Max Drawdown: [X]%
  
TRADE STATISTICS:
  Total Trades: [X]
  Avg Trade Duration: [X] hours
  Largest Win: [X]%
  Largest Loss: [X]%
  
REGIME PERFORMANCE:
  2022 (Bear): [X]% return
  2023 (Consolidation): [X]%
  2024 (Bull): [X]%
  
WALK-FORWARD:
  In-Sample Avg Sharpe: [X]
  Out-of-Sample Avg Sharpe: [X]
  Degradation: [X]% (<20% = good)
  
CORRELATION:
  vs M Pattern: [X] (<0.7 = good)
  vs W Pattern: [X] (<0.7 = good)
```

### Live Trading Prerequisites

Before any new strategy goes live:

```
□ 2-4 weeks paper trading (no real money)
□ No unexpected errors or edge cases
□ Position limits defined ($[X] per trade)
□ Stop-loss triggers tested
□ Daily performance monitoring setup
□ Monthly review schedule set
□ Emergency shutdown procedure documented
□ Correlation with portfolio calculated
□ Risk of ruin < 5% (at 2% risk per trade)
```

---

## Cline Prompting Guide

### Master System Prompt

Save this as your `.cline-system-prompt` or include in project instructions:

```
You are a specialized algorithmic trading strategy discovery and 
implementation agent for a Bitcoin trading system using NautilusTrader.

YOUR ROLE:
Autonomously discover, implement, validate, and optimize new trading 
strategies that complement existing M Pattern and W Pattern strategies.

YOUR CONSTRAINTS:
1. ONLY implement strategies that pass statistical validation
2. ONLY validate with walk-forward (never optimize on full data)
3. NEVER trade with >2% risk per trade
4. NEVER accept strategy with <50% win rate on 3-year backtest
5. NEVER proceed without correlation check (<0.7 with M & W)
6. ALWAYS use provided BacktestEngine (don't rewrite)
7. ALWAYS document code with type hints and docstrings
8. ALWAYS report results in specified format

YOUR WORKFLOW:
For each new pattern:
  1. DESIGN: Define pattern with mathematical precision
  2. IMPLEMENT: Write NautilusTrader strategy inheriting BaseStrategy
  3. VALIDATE: Run 1-year backtest (pass gate: 45% win rate)
  4. EXTEND: Run 3-year backtest (pass gate: 50% win rate, 1.5 PF, 0.8 SR)
  5. OPTIMIZE: Walk-forward analysis (pass gate: OOS >= 80% IS)
  6. CHECK: Correlation & ensemble fit (pass gate: corr < 0.7)
  7. REPORT: Production readiness assessment

YOUR SUCCESS METRIC:
Discover 5-10 new validated strategies per 6 months that:
- Have >50% win rate on 3+ years of data
- Have >1.5 profit factor
- Correlate <0.7 with existing strategies
- Improve portfolio Sharpe by >10%
- Require only minimal human oversight

YOU KNOW:
- NautilusTrader API and Strategy pattern
- Your existing M & W pattern implementations
- Bitcoin price action and trading patterns
- Risk management and position sizing
- Walk-forward analysis methodology
- Statistical testing and validation
- Production trading requirements

WHEN IN DOUBT:
- Ask clarifying questions in your prompts
- Run conservative backtests first
- Default to rejecting marginal patterns
- Prioritize robustness over optimization
```

### Specific Prompt Templates

**For Pattern Discovery:**
```
Evaluate [PATTERN NAME] as a new trading strategy for Bitcoin 4h timeframe.

Provide:
1. Clear structure definition (how to identify on chart)
2. Entry signal (specific conditions, not subjective)
3. Exit signal (when to close)
4. Stop-loss placement (how far below entry)
5. Why this pattern should work
6. Expected frequency (trades per month on 4h BTC)
7. Implementation feasibility (1-10 scale)
8. Comparison to M & W patterns (similarities/differences)

Be concise and focus on practical tradability.
```

**For Strategy Implementation:**
```
Implement [PATTERN NAME] as a NautilusTrader strategy.

Requirements:
- Inherit from BaseStrategy
- Include full pattern detection algorithm
- Use ATR for stops (stop = [peak/low] ± 1.5×ATR)
- Follow position sizing: (account × 0.02) / stop_distance
- Externalize all parameters to __config__ dict
- Include comprehensive logging
- Write 3+ unit tests for pattern detection

Use this template:
```python
class [Pattern]StrategyConfig(BaseStrategyConfig):
    """Configuration"""
    lookback_period: int = 20
    volume_multiplier: float = 1.5
    # ... other params

class [Pattern]Strategy(BaseStrategy):
    """Strategy implementation"""
    
    def __init__(self, config: [Pattern]StrategyConfig) -> None:
        super().__init__(config)
        # Initialize
    
    def on_bar(self, bar: Bar) -> None:
        # Main logic
        pass
```

Output the complete, runnable implementation.
```

**For Walk-Forward Analysis:**
```
Run walk-forward optimization of [STRATEGY NAME].

Parameters to optimize:
- [param1]: range [min-max]
- [param2]: range [min-max]
...

Use rolling windows: 252-day training, 21-day test
Report:
- Optimal parameters for each window
- In-sample and out-of-sample Sharpe ratios
- Degradation (OOS/IS ratio)
- Parameter stability
- Decision: ROBUST / CONCERNING / OVERFITTED
```

**For Final Validation:**
```
Generate production readiness report for [STRATEGY].

Include:
□ All backtest metrics (1-year, 3-year, walk-forward)
□ Regime-specific performance (bull/bear/consolidation)
□ Correlation with M & W patterns
□ Portfolio ensemble impact
□ Risk assessment
□ Checklist of all passing criteria
□ Recommendation: APPROVE / REJECT / NEEDS REVISION

Format as:
```
[STRATEGY] - PRODUCTION READINESS REPORT
Overall Decision: ✅ APPROVED / ❌ REJECTED
Confidence: [X]%
[Key metrics table]
[Recommendation & next steps]
```

Output actionable, deployment-ready report.
```

---

## Quick Reference: Your Infrastructure

### Existing Components (Do Not Reimplement)

**BaseStrategy Class**
- Location: `strategies/base_strategy.py`
- Use: Inherit all new strategies from this
- Features: Risk management, position sizing, logging

**BacktestEngine**
- Location: `backtest/backtest_engine.py`
- Use: For all backtesting and walk-forward
- Features: Data loading, run_backtest(), optimization

**Data Pipeline**
- Location: `data/` (Parquet format)
- Format: BTCUSDT 4h bars with OHLCV
- Coverage: 2022-2025 continuous

**Configuration System**
- Location: `config/` (YAML files)
- Pattern: Externalize all parameters to config
- Use: StrategyConfig classes for serialization

### Naming Convention for New Strategies

```
Strategy Class: [PatternName]Strategy
Config Class: [PatternName]StrategyConfig
File: strategies/[pattern_name]_strategy.py
Config File: config/[pattern_name]_config.yaml
Test File: tests/test_[pattern_name]_strategy.py

Example:
  Class: TriangleStrategy
  Config: TriangleStrategyConfig
  File: strategies/triangle_strategy.py
  Config: config/triangle_config.yaml
  Test: tests/test_triangle_strategy.py
```

---

## Expected Timeline & Deliverables

### 6-Month Implementation Plan

**Month 1: Discovery & Prioritization**
- Cline evaluates 10+ potential patterns
- Identifies 3-5 high-probability patterns
- Deliverable: Pattern evaluation report

**Month 2: Implementation & Testing**
- Implement 3 new strategies
- Run initial 1-year backtests
- Deliverable: 3 candidate strategies with validation

**Month 3: Extended Validation**
- 3-year backtests on 3 strategies
- Regime analysis (bull/bear/consolidation)
- Deliverable: Extended validation reports

**Month 4: Walk-Forward & Optimization**
- Walk-forward analysis on all 3
- Parameter robustness testing
- Deliverable: Optimized parameters, degradation analysis

**Month 5: Correlation & Ensemble**
- Correlation analysis with M & W
- Portfolio simulation with ensemble
- Deliverable: Ensemble benefit report

**Month 6: Production & Deployment**
- Code review and documentation
- Paper trading prep
- Deployment to live (if approved)
- Deliverable: 2-3 production-ready strategies

**Expected Output: 3 new validated, production-ready strategies**

---

## Final Checklist for Cline

Before sending any new strategy to production:

```
✅ IMPLEMENTATION
  □ Inherits from BaseStrategy
  □ Configuration in StrategyConfig
  □ Type hints on all methods
  □ Docstrings complete
  □ Logging at key points
  □ Error handling for edge cases

✅ BACKTESTING
  □ 1-year validation: PASS (>45% win rate)
  □ 3-year validation: PASS (>50% win rate, >1.5 PF, >0.8 SR)
  □ All regimes profitable (no regime loss >50% vs average)
  □ Max drawdown <20%

✅ OPTIMIZATION
  □ Walk-forward performed
  □ Out-of-sample >= 80% in-sample
  □ Parameters stable across windows
  □ No overfitting detected

✅ ENSEMBLE
  □ Correlation M < 0.7
  □ Correlation W < 0.7
  □ Portfolio Sharpe > individual
  □ Diversification benefit confirmed

✅ DOCUMENTATION
  □ Pattern clearly defined
  □ Entry/exit rules stated
  □ Risk management documented
  □ Backtest results attached
  □ Parameter ranges explained

✅ APPROVAL
  □ Meets all gates
  □ No manual changes needed
  □ Ready for 2-4 week paper trading
  □ Signed off for live deployment
```

---

## Success Metrics

You'll know this framework is working when:

```
SHORT TERM (1-3 months):
✓ Cline successfully implements new patterns without your intervention
✓ Backtests run automatically and consistently
✓ Reports are clear, actionable, and accurate
✓ Zero failed implementations (all code works first time)

MEDIUM TERM (3-6 months):
✓ 3+ new strategies validated and ready for trading
✓ Portfolio Sharpe ratio improves by 10%+
✓ Drawdowns reduced by strategy diversification
✓ Correlation between strategies < 0.6 (excellent diversification)

LONG TERM (6-12 months):
✓ 5-10 production strategies deployed
✓ Portfolio return increased 2-3% annually
✓ Risk-adjusted returns (Sharpe) improved 20%+
✓ Maximum drawdown reduced by 25-30%
✓ Human involvement minimal (quarterly reviews only)
```

---

## Critical Reminders for Cline

1. **Never compromise on validation**
   - A rejected strategy is not a failure
   - Overfitting is worse than no strategy
   - Walk-forward is mandatory

2. **Always validate across regimes**
   - Pattern must work in bull, bear, AND consolidation
   - If only works in one regime, it's regime-dependent (risky)

3. **Default to correlation < 0.7**
   - If new pattern correlates >0.7 with M or W, it's redundant
   - Reject without emotion

4. **Document everything**
   - Future Cline (or human) needs to understand decisions
   - Include backtest results, parameters, rationale

5. **Test first, optimize second**
   - Get something working on 1 year
   - Then validate on 3 years
   - Then optimize with walk-forward
   - Don't try to optimize before validation

---

**Document Version:** 2.0  
**Purpose:** Cline Strategy Discovery Framework  
**Status:** Production Deployment Ready  
**Last Updated:** December 31, 2025  

*This document provides Cline with the complete framework to autonomously discover, implement, validate, and deploy new trading strategies within your existing NautilusTrader infrastructure.*
