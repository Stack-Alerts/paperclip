# BTC Trade Engine — Training Manual

**Version:** 1.0  
**Platform:** BTC Trade Engine (Powered by NautilusTrader)  
**Audience:** New Trade Engineers — systematic traders learning to use the platform  
**Last Updated:** 2026-05-08

---

## How to Use This Manual

Work through each module in order. Each module builds on the previous one. By the end of Module 6 you will be able to build, test, optimise, and run live trading strategies on the BTC Trade Engine.

**Time commitment:** Allow approximately 4–6 hours to complete all six modules. You can pause between modules and resume at any point.

**Prerequisites:** You have completed the installation steps in the [User Guide](user-guide.md) and the application launches successfully.

---

## Table of Contents

- [Module 1: Introduction to Algorithmic Trading](#module-1-introduction-to-algorithmic-trading)
- [Module 2: Understanding the BTC Trade Engine](#module-2-understanding-the-btc-trade-engine)
- [Module 3: Your First Strategy](#module-3-your-first-strategy)
- [Module 4: Testing and Validation](#module-4-testing-and-validation)
- [Module 5: Going Live](#module-5-going-live)
- [Module 6: Advanced Topics](#module-6-advanced-topics)
- [Glossary](#glossary)

---

## Module 1: Introduction to Algorithmic Trading

**Estimated time:** 30 minutes  
**Goal:** Understand the core concepts behind systematic, algorithmic trading before touching any software.

---

### 1.1 What Is Algorithmic Trading?

Algorithmic trading (also called systematic trading or automated trading) means using a computer program — rather than human judgement in the moment — to decide when to buy and sell a financial instrument.

The program follows a fixed set of rules. Those rules are your *strategy*. When the rules are met, the computer places an order automatically.

**Why use algorithms?**

| Human Trading | Algorithmic Trading |
|---------------|---------------------|
| Affected by fear and greed | Executes rules exactly, every time |
| Can only monitor one market at a time | Can monitor hundreds simultaneously |
| Tires, makes mistakes under pressure | Runs 24/7 without degradation |
| Hard to test objectively | Testable on historical data before risking capital |

---

### 1.2 Key Concepts

**Signal**  
A signal is a condition that, when true, suggests a trading opportunity. Examples:
- RSI (Relative Strength Index) is above 70 — suggests overbought conditions
- A double-top pattern has formed — suggests price may reverse downward
- Price has broken below a key support level — confirms bearish momentum

**Confluence**  
No single signal is reliable on its own. *Confluence* means multiple independent signals all pointing in the same direction at the same time. A strategy with high confluence requires several conditions to align before placing a trade, which filters out low-quality setups.

**Entry and Exit**  
- *Entry:* The moment the strategy decides to open a position (buy or sell)
- *Stop Loss (SL):* A price level at which the position is automatically closed to limit losses if the market moves against you
- *Take Profit (TP):* A price level at which the position is automatically closed to lock in gains

**Risk:Reward Ratio**  
If your stop loss is 1% from entry and your take profit is 3% from entry, your risk:reward ratio is 1:3. This means you only need to be right one-third of the time to break even over many trades.

**Win Rate**  
The percentage of trades that are profitable. A 60% win rate means 6 out of 10 trades close in profit. Combined with a good risk:reward ratio, even a lower win rate can be highly profitable.

**Drawdown**  
The largest peak-to-trough decline in your account balance during a period. A maximum drawdown of 15% means your account fell 15% from its high point before recovering. Lower drawdown is better — it means the strategy is more consistent.

---

### 1.3 The BTC Perpetual Futures Market

The BTC Trade Engine trades **BTC/USDT Perpetual Futures** on Binance. Key points:

- **Perpetual futures** are contracts with no expiry date. You hold a position until you choose to close it (or your stop loss triggers).
- **Long position:** You profit when BTC price goes up.
- **Short position:** You profit when BTC price goes down.
- **Leverage:** Futures allow you to control a larger position than your account balance. This amplifies both gains and losses. The platform caps leverage at 2× by default — use caution.
- **Funding rate:** Perpetual futures charge a small fee every 8 hours to keep the futures price aligned with the spot price. This is a minor cost to be aware of in live trading.

---

### 1.4 The 15-Minute Timeframe

The platform operates on **15-minute candles** (also called bars). Each candle represents 15 minutes of price action and contains:

- **Open:** Price at the start of the 15-minute period
- **High:** Highest price during the period
- **Low:** Lowest price during the period
- **Close:** Price at the end of the period
- **Volume:** Total BTC traded during the period

A new candle is completed every 15 minutes. The strategy evaluates signals on each completed candle.

---

### Module 1 Summary

- Algorithmic trading removes emotion and applies rules consistently.
- Signals identify potential opportunities; confluence filters out poor-quality setups.
- Every trade has a defined entry, stop loss, and take profit.
- The platform trades BTC/USDT Perpetual Futures on 15-minute candles.

**Next:** Module 2 — Understanding the BTC Trade Engine

---

## Module 2: Understanding the BTC Trade Engine

**Estimated time:** 45 minutes  
**Goal:** Understand how the platform is structured and what each component does.

---

### 2.1 Platform Architecture Overview

The BTC Trade Engine is built on **NautilusTrader**, an open-source, high-performance algorithmic trading framework. NautilusTrader handles the low-level work: processing candle data, submitting orders to the exchange, tracking positions, and calculating portfolio metrics.

On top of NautilusTrader, the BTC Trade Engine adds:

- A **Strategy Builder** — a graphical interface for building strategies without writing code
- A **Building Block Registry** — a library of 80+ pre-built market detectors and indicators
- A **Walk-Forward Testing Engine** — for validating strategies on historical data
- An **Optimiser** — for automatically finding the best parameter combinations
- A **Live Trading Bridge** — for connecting validated strategies to Binance Futures

---

### 2.2 The Two-Window Layout

When you launch the platform, two windows open:

**Window 1 — Strategy Builder**  
This is where you design strategies. You select building blocks, configure their logic, and set stop-loss and take-profit rules. Think of this as your *workshop*.

**Window 2 — Backtest & Optimizer**  
This is where you test and optimise strategies. You set date ranges, run walk-forward tests, review trade records, compare metrics, and optimise parameters. Think of this as your *laboratory*.

> **Screenshot needed (Training-1):** Both windows open side by side, Window 1 on the left and Window 2 on the right, with labels identifying each window.

---

### 2.3 Building Blocks

A **building block** is a self-contained market detector. Each block watches price action and emits named signals when specific conditions are met.

Building blocks are organised into categories:

| Category | Examples |
|----------|---------|
| Patterns | Double Top, Head & Shoulders, M-Pattern, W-Pattern |
| Oscillators | RSI, CCI, CMO, MFI, ROC |
| Price Levels | Support/Resistance, Fibonacci Levels |
| Sessions & Time | London Open, New York Open, Asian Session |
| Trend & Momentum | Moving Average Crossovers, ADX |
| Volatility | ATR, Bollinger Bands |
| Market Structure | Highs/Lows, Break of Structure |
| Elliott Wave | Wave counts, Oscillator |
| Wyckoff | Accumulation/Distribution phases |
| SMC/ICT | Order Blocks, Fair Value Gaps, Liquidity Sweeps |
| Supply & Demand | Supply and Demand zones |

Each block emits one or more named signals. For example, an RSI block might emit `OVERBOUGHT` when RSI crosses above 70, or `OVERSOLD` when it crosses below 30.

---

### 2.4 The Confluence Engine

The heart of the trading logic is the **Confluence Engine**. Here is how it works:

1. Each block is assigned a **weight** (a number, typically 10–40 points).
2. On each new candle, the engine checks whether each block's signal has fired.
3. It adds up the weights of all blocks whose signals are currently active.
4. If the total score reaches the **minimum confluence threshold** (default: 70 out of 100), a trade entry is triggered.
5. The direction of the trade (Long or Short) is determined by whether the blocks are configured for bullish or bearish signals.

**Example:**

| Block | Weight | Signal Active? | Contributes |
|-------|--------|---------------|------------|
| M-Pattern | 30 | Yes | 30 |
| RSI Overbought | 25 | Yes | 25 |
| London Session | 20 | Yes | 20 |
| Volume Spike | 15 | No | 0 |
| **Total** | | | **75 / 100** |

Score is 75. Threshold is 70. **Entry triggered.**

---

### 2.5 AND vs. OR Logic

When adding a block to your strategy, you choose its logic type:

**AND (Required)**  
The block *must* fire for an entry to be considered. If any AND block fails to fire, no entry occurs, regardless of the total score.

**OR (Optional Booster)**  
The block is not required. If it fires, it adds to the confluence score and can increase the position size by up to 10% per OR block. If it doesn't fire, the strategy continues normally.

**Practical rule:** Use AND for your primary pattern and a few key confirming signals. Use OR for secondary confirmations that strengthen the setup but are not critical.

---

### 2.6 Walk-Forward Testing

Walk-forward testing is the gold standard for validating trading strategies. It works as follows:

1. Start at a point in the past (e.g., 1 January 2024).
2. Process each candle in sequence, exactly as the strategy would see them in real time.
3. When a signal fires, record the entry, apply the stop loss and take profit rules, and record the outcome.
4. Continue until the test window ends.

This approach is honest — the strategy never "sees" future data. It is equivalent to paper-trading the strategy on historical data.

---

### 2.7 Data Available

The platform has **45 GB of historical BTC data** covering 2024–2025 on the 15-minute timeframe. This is approximately 110,000 candles — more than enough for rigorous walk-forward testing.

Data is stored locally in the `data/` directory and is loaded automatically when you run a test.

---

### Module 2 Summary

- The platform = NautilusTrader framework + Strategy Builder + Building Block Registry + Testing Engine.
- Window 1 builds strategies; Window 2 tests and optimises them.
- Building blocks detect market conditions and emit named signals.
- The Confluence Engine sums signal weights and triggers entries when the threshold is met.
- AND blocks are required; OR blocks are optional boosters.
- Walk-forward testing validates strategies honestly on historical data.

**Next:** Module 3 — Your First Strategy

---

## Module 3: Your First Strategy

**Estimated time:** 60 minutes  
**Goal:** Build a complete, valid strategy step by step using the Strategy Builder.

This module walks you through building a bearish reversal strategy that combines an M-Pattern (a price reversal pattern) with RSI overbought confirmation and a London Session time filter.

---

### 3.1 Launch the Platform

```bash
cd /home/sirrus/projects/BTC-Trade-Engine-PaperClip
source venv/bin/activate
python scripts/launch_strategy_builder.py
```

Both windows open. You are in Window 1 — Strategy Builder.

> **Screenshot needed (Training-2):** Window 1 immediately after launch, empty state, with the main panels labelled: Block Search (left), Strategy Configuration (centre), Strategy Info (top), Real-time Preview (right).

---

### 3.2 Create a New Strategy

1. Click **New Strategy** in Window 1.
2. A name prompt appears. Enter:
   ```
   m_pattern_rsi_london_bear
   ```
3. Press Enter or click OK.

The Strategy Info panel at the top now shows your strategy name. The centre panel is empty and ready for blocks.

---

### 3.3 Add the M-Pattern Block (AND — Primary Signal)

The M-Pattern is a classic bearish reversal pattern. It will be the primary signal for this strategy.

1. In the **Block Search** panel (left), type `m_pattern` in the search bar.
2. The M-Pattern block appears in the results. Click it to expand the detail card.
3. Review the available signals. You will see signals such as `BEARISH_BREAKDOWN`.
4. Click **Add as AND**.

The M-Pattern block now appears in the centre panel. It is set to AND (required) and a default signal is pre-selected.

**What you've done:** You've told the strategy that the M-Pattern *must* form before any entry is considered.

---

### 3.4 Configure the M-Pattern Signal

1. Click the M-Pattern block in the centre panel to expand its signal configuration.
2. Confirm the selected signal is `BEARISH_BREAKDOWN`.
3. Confirm the signal role is **SIGNAL** (this is the primary entry trigger).

Leave the timing constraints unchecked for now.

---

### 3.5 Add the RSI Block (AND — Confirming Signal)

Next, add RSI overbought confirmation. This ensures we only take the M-Pattern signal when the market is genuinely overbought.

1. In Block Search, type `rsi`.
2. Click the RSI block to expand it.
3. Click **Add as AND**.

The RSI block appears in the centre panel below the M-Pattern block.

4. Click the RSI block to expand its configuration.
5. Select the signal `OVERBOUGHT`.
6. Set the role to **FILTER** — this means RSI must be overbought, but it acts as a filter rather than the primary trigger.

**What you've done:** You've added a second required condition — RSI must be overbought when the M-Pattern fires. This eliminates M-Pattern signals that occur in oversold or neutral RSI conditions.

---

### 3.6 Add the London Session Block (OR — Time Booster)

Trading during the London session (high liquidity, strong momentum) increases the quality of signals. We'll add this as an OR booster — it's not required, but it adds confidence.

1. In Block Search, type `london`.
2. Click the London Open / London Session block.
3. Click **Add as OR**.

4. Click the block to expand it.
5. Select the signal `LONDON_ACTIVE` or `IN_SESSION`.
6. Set the role to **BOOSTER**.

**What you've done:** When the M-Pattern fires and RSI is overbought *and* it's during the London session, the confluence score gets an extra boost and the position size is slightly larger. Outside of London hours, the strategy still trades — just with a standard position size.

---

### 3.7 Configure Stop Loss and Take Profit

Scroll down in the centre panel to find the **Adaptive SL/TP Configuration** panel. Click to expand it.

Set the following:

| Setting | Value |
|---------|-------|
| Stop Loss Mode | Fibonacci |
| SL Fibonacci Level | 0.618 |
| Take Profit Mode | Hybrid |
| TP1 | 1.5% |
| TP2 | 3.0% |
| TP3 | 5.0% |

**What these mean:**
- The stop loss is placed at the 0.618 Fibonacci retracement of the M-Pattern swing. This is a natural support-turned-resistance level.
- TP1 closes a portion of the position at 1.5% profit (fast, secured gains).
- TP2 closes another portion at 3.0%.
- TP3 closes the remainder at 5.0% (let winners run).

> **Screenshot needed (Training-3):** The Adaptive SL/TP panel expanded with the values above filled in.

---

### 3.8 Review the Real-Time Preview

The **Real-time Preview** panel (right side of Window 1) automatically ran a quick backtest on the last 30 days of data as you built the strategy. Review it now:

- **Signals triggered:** How many times the confluence conditions were met in the last 30 days.
- **Estimated win rate:** Percentage of signals that would have been profitable.
- **Estimated P&L:** Rough net profit/loss estimate.

> **Note:** The real-time preview is approximate and uses only 30 days of data. Do not base trading decisions on it — use the full walk-forward test in Module 4.

---

### 3.9 Validate and Save

The Strategy Info panel shows a green checkmark when the strategy is valid. Common errors at this stage:

| Error | Fix |
|-------|-----|
| No SIGNAL role found | Expand the M-Pattern block, confirm signal role is SIGNAL |
| Main signal block not found | The first AND block must be the primary pattern |
| Weight out of range | Click the block and adjust the weight slider |

Once the strategy is valid (green checkmark):

1. Click **Save Strategy**.
2. The strategy is saved to `user_strategies/` as a JSON file.
3. A confirmation message appears.

**Congratulations — you have built your first strategy.**

---

### Module 3 Summary

Strategy built: `m_pattern_rsi_london_bear`
- AND Block 1: M-Pattern → `BEARISH_BREAKDOWN` (SIGNAL role) — required
- AND Block 2: RSI → `OVERBOUGHT` (FILTER role) — required
- OR Block 3: London Session → `IN_SESSION` (BOOSTER role) — optional
- SL: Fibonacci 0.618 | TP: Hybrid 1.5% / 3.0% / 5.0%

**Next:** Module 4 — Testing and Validation

---

## Module 4: Testing and Validation

**Estimated time:** 60 minutes  
**Goal:** Run a walk-forward test on your strategy and correctly interpret the results.

---

### 4.1 Switch to Window 2

Click on **Window 2 — Backtest & Optimizer** (it may be minimised behind Window 1).

Window 2 has five tabs across the top: Configuration, Live Output, Trades, Metrics, Compare.

---

### 4.2 Configure the Test (Tab 1 — Configuration)

In Tab 1, set the following:

**Date Range**

| Field | Value |
|-------|-------|
| Start Date | 2024-01-01 |
| End Date | 2024-12-31 |
| Timeframe | 15m |

This gives a full year of data — sufficient for statistically meaningful results (the strategy should produce at least 30 trades for the metrics to be reliable).

**Capital & Risk**

| Field | Value |
|-------|-------|
| Starting Capital | $10,000 |
| Risk Per Trade | 1% |
| Max Position Size | 0.1 BTC |

**Test Mode**  
Select **Mode 1 — Historical Walk-Forward**.

> **Screenshot needed (Training-4):** Tab 1 (Configuration) filled in with the values above, ready to run.

---

### 4.3 Run the Test

Confirm your strategy (`m_pattern_rsi_london_bear`) is shown as the active strategy at the top of Window 2.

Click **Run Test**.

Switch to **Tab 2 — Live Output** to watch progress. You will see:
- A progress bar showing how far through the historical data the engine has processed
- A running count of signals triggered and trades opened/closed
- Current P&L estimate
- CPU and memory usage

A full-year test on 15-minute data typically completes in 1–3 minutes on a standard machine.

> **Screenshot needed (Training-5):** Tab 2 (Live Output) mid-run, showing progress bar at approximately 50%, trade count updating, and resource monitor.

---

### 4.4 Reading the Trades (Tab 3)

When the test completes, click **Tab 3 — Trades**.

Each row is one completed trade. Key columns:

| Column | What to Look For |
|--------|-----------------|
| Entry Time | Are trades spread throughout the year, or clustered? Clustering can indicate curve-fitting |
| Side | All Short for a bearish strategy — this should be consistent |
| PnL | Look for a mix of wins and losses — too many consecutive wins or losses is a warning sign |
| Duration | Average holding time; very short or very long trades are worth investigating |

**What to look for in a healthy trade log:**
- Trades distributed throughout the year (not all in one month)
- A mix of wins and losses with no catastrophic single loss
- Consistent trade duration (not all extremely long or short)

---

### 4.5 Reading the Metrics (Tab 4)

Click **Tab 4 — Metrics**.

The metrics table shows performance statistics for the test run.

**Key metrics and what they mean:**

| Metric | What It Measures | Minimum Target |
|--------|-----------------|----------------|
| **Win Rate** | % of trades that closed in profit | > 55% |
| **Profit Factor** | Gross profit ÷ gross loss | > 1.5 |
| **Sharpe Ratio** | Risk-adjusted return (reward per unit of risk) | > 1.5 |
| **Max Drawdown** | Largest peak-to-valley decline | < 20% |
| **Trade Count** | Number of completed trades | > 30 |
| **Total PnL** | Net profit in USD | Positive |

**Interpreting your results:**

If all five targets are met — excellent. The strategy has passed an initial validation. Proceed to Module 5.

If one or two targets are missed — investigate before continuing:

| Problem | Possible Cause | Action |
|---------|----------------|--------|
| Win Rate < 50% | Signals not confirming reversals | Try adding a volume or momentum filter |
| Trade Count < 15 | Confluence threshold too high | Lower `min_confluence` from 70 to 60 |
| Max Drawdown > 25% | Stop losses too wide | Change SL Fibonacci level from 0.618 to 0.382 |
| Sharpe < 1.0 | High variance in returns | Strategy may need more filtering |

If no targets are met — the strategy concept may not be sound. Try a different primary pattern or different confirming signals. Do not attempt to force a failing strategy to pass by over-optimising.

---

### 4.6 The Danger of Over-Optimisation (Curve-Fitting)

A critical concept: if you keep adjusting your strategy until it looks great on the test data, you are *curve-fitting* — the strategy has learned the specific quirks of that data, not genuine market patterns. It will likely fail on new data.

**How to avoid it:**
- Test on a fixed period first. Only adjust the strategy concept (which blocks to include), not the parameter values.
- Use the Optimiser (covered in Module 6) with early-stopping to avoid over-fitting.
- Validate on a separate *out-of-sample* period (data the strategy has never seen).

**Out-of-sample validation procedure:**
1. Test on 2024 data (in-sample). Fix the strategy when results look reasonable.
2. Run a second test on 2025 data (out-of-sample) — do NOT adjust the strategy after seeing these results.
3. If 2025 results are broadly similar to 2024, the strategy is likely genuinely robust.
4. If 2025 results collapse, the strategy was curve-fit. Return to step 1 with a different approach.

---

### Module 4 Summary

- Configure date range, capital, and risk in Tab 1 before running.
- Tab 2 shows live progress; Tab 3 shows individual trades; Tab 4 shows aggregate metrics.
- Minimum targets: Win Rate > 55%, Profit Factor > 1.5, Sharpe > 1.5, Drawdown < 20%.
- Always validate on out-of-sample data before going live.
- Avoid over-optimisation — fit the market, not the historical data.

**Next:** Module 5 — Going Live

---

## Module 5: Going Live

**Estimated time:** 45 minutes  
**Goal:** Understand the process of activating a validated strategy for live trading, and how to monitor it safely.

> **Important:** Only proceed to live trading after your strategy has passed walk-forward testing on at least one year of in-sample data **and** one out-of-sample validation period. Live trading involves real financial risk.

---

### 5.1 Pre-Live Checklist

Before activating Autopilot, confirm every item on this checklist:

- [ ] Strategy has been walk-forward validated on at least 6 months of in-sample data
- [ ] Sharpe Ratio > 1.5 on the validation period
- [ ] Max Drawdown < 20% on the validation period
- [ ] Out-of-sample results are broadly consistent with in-sample results
- [ ] Binance API key is entered in `.env` with Futures trading enabled
- [ ] API key does **not** have withdrawal permissions (security best practice)
- [ ] `BINANCE_TESTNET=true` is set in `.env` for a trial run first (see 5.2)
- [ ] Risk per trade is set conservatively (start with 0.5%)

---

### 5.2 Paper Trading First (Testnet)

Before risking real capital, run your strategy on the **Binance testnet** — a simulated exchange that uses fake money but real market data.

1. In your `.env` file, set:
   ```
   BINANCE_TESTNET=true
   ```
2. Obtain testnet API credentials from: https://testnet.binancefuture.com
3. Enter the testnet credentials in `.env` as `BINANCE_API_KEY` and `BINANCE_SECRET`.
4. Launch the platform and run the strategy in Mode 2 (Live Continuation).
5. Monitor for at least 2 weeks before considering real capital.

**What to check during testnet:**
- Orders are placing and closing correctly on Binance testnet
- Stop losses are triggering as expected
- The strategy is behaving consistently with the backtest results
- No unexpected errors in the logs

---

### 5.3 Activating Live Trading

Once testnet validation is complete:

1. In `.env`, change `BINANCE_TESTNET=false` (or remove the line).
2. Replace testnet credentials with your real Binance Futures API credentials.
3. In Window 1, load your validated strategy.
4. In Window 2, Tab 1, confirm risk parameters:
   - Start with **Risk Per Trade = 0.5%** (not 1%) for the first month
   - Confirm Max Position Size is appropriate for your account size
5. Select **Mode 2 — Live Continuation**.
6. Click **Run Test**.

The platform runs the historical phase first (processing all historical data up to today), then switches automatically to live mode.

When you see the message **"Historical complete. Waiting for live candles…"**, the strategy is live.

> **Screenshot needed (Training-6):** The Live Output tab showing "LIVE" status badge, historical phase marked as complete, and the live candle counter incrementing.

---

### 5.4 What Happens on Each Live Candle

Every 15 minutes, when a new candle completes:

1. The platform receives the closed candle data from Binance.
2. All building block signals are evaluated on the new candle.
3. The Confluence Engine calculates the current score.
4. If the score meets the threshold:
   - A market order is placed on Binance Futures (Long or Short, per strategy direction)
   - A stop loss order is placed simultaneously
5. If a position is already open, the platform tracks it against the TP1/TP2/TP3 levels and closes portions as each level is reached.
6. Results are recorded to the database.

---

### 5.5 Monitoring a Live Strategy

**Daily checks (5 minutes):**
- Open Tab 2 (Live Output) — confirm status shows 🟢 LIVE
- Check "New Candles Processed" is incrementing
- Check Live P&L is within expected range

**Weekly checks (15 minutes):**
- Review Tab 3 (Trades) for the week's trades
- Confirm win rate and average PnL per trade are in line with backtest expectations
- Check the application logs (`logs/strategy_builder_YYYY-MM-DD.log`) for any WARNING or ERROR entries

**When to pause the strategy:**
- Live drawdown exceeds 10% (half your max validated drawdown) — pause and review
- Three consecutive days of losses — pause and review
- Unexpected errors appear in logs (API failures, connection issues) — investigate before continuing
- Market regime has visibly changed (e.g., extreme volatility event) — pause and reassess

---

### 5.6 Stopping the Strategy

Click **Stop Test** at any time.

The platform will:
1. Stop processing new candles.
2. Close any open position (if your risk settings include force-close on stop — check your config).
3. Generate a final report covering the full period (historical + live).

> **Note:** If you want to leave a position open after stopping the automated strategy, ensure "Close positions on stop" is set to `false` in your settings. You can then manage the position manually on Binance.

---

### Module 5 Summary

- Always paper-trade on testnet before using real capital.
- Start with 0.5% risk per trade for the first month live.
- Monitor daily (2 min), weekly (15 min).
- Pause if live drawdown exceeds 10% or three consecutive losing days occur.
- The strategy can be stopped at any time with no data loss.

**Next:** Module 6 — Advanced Topics

---

## Module 6: Advanced Topics

**Estimated time:** 60 minutes  
**Goal:** Learn optimisation, concurrent strategies, and performance tuning.

---

### 6.1 Strategy Optimisation

The Optimiser automatically tests many parameter combinations and ranks them by performance. Use it to find the best settings for your strategy — but only after the strategy concept has been validated.

**When to optimise:**
- After your strategy passes initial walk-forward testing
- When you want to fine-tune parameters (confluence threshold, SL/TP levels, block weights)
- Not as a first step — optimise a strategy that already shows promise

**How to run an optimisation:**

1. In Window 2, Tab 1, click **Optimize** (instead of Run Test).
2. A parameter panel appears. Check the boxes next to parameters you want to optimise. Examples:
   - `min_confluence` (range: 60–80, step: 5)
   - `sl_fibonacci_level` (values: 0.382, 0.5, 0.618)
   - `risk_per_trade_pct` (range: 0.5–2.0, step: 0.5)
3. Review the **Estimated Configurations** count. Aim for 20–100 configurations for most optimisations. More than 500 will take hours.
4. Click **Start Optimization**.
5. Monitor progress in Tab 2.
6. Results appear in Tab 4 sorted by Sharpe Ratio. The top row is the best configuration found.

**Optimisation best practices:**

- Optimise 2–3 parameters at a time. Optimising 6+ parameters simultaneously almost always leads to curve-fitting.
- Configure `EARLY_STOP_PATIENCE` in `.env` (e.g. `EARLY_STOP_PATIENCE=10`) — this stops the optimisation when N consecutive configurations show no improvement. This setting is not pre-configured; add it to `.env` if needed.
- After optimisation, re-run a clean walk-forward test with the best parameters on **out-of-sample data** to confirm they generalise.

---

### 6.2 Running Multiple Concurrent Strategies

The platform is designed to run **100s of concurrent strategies** simultaneously. This is one of its core strengths — diversification across many strategy instances reduces overall portfolio risk.

**How concurrent strategies work:**
- Each strategy runs independently.
- The Confluence Engine evaluates each strategy on each new candle.
- Multiple strategies may place trades simultaneously, each with their own position size.
- Portfolio-level risk is managed by the per-strategy risk settings.

**Setting up concurrent strategies:**

1. Build and validate multiple strategies (using the process from Modules 3 and 4).
2. Save each strategy with a descriptive, unique name.
3. In Window 2, Tab 1, there is a **Strategy Selection** section. Select all strategies you want to run concurrently.
4. Set the per-strategy risk low when running many strategies concurrently. Example: if running 10 strategies, use 0.2%–0.5% per strategy (not 1% — the aggregate exposure would be too high).

**Recommended concurrent portfolio structure:**
- 2–3 primary strategies (high confidence, validated, 0.5% risk each)
- 5–10 secondary strategies (validated, lower risk, 0.2% each)
- Start small (3–5 concurrent) and scale up as you build confidence

---

### 6.3 The Compare Tab (Tab 5)

Tab 5 shows the last three parameter configurations side by side. Use it to quickly spot which parameter changes helped and which hurt.

- Green cells: improvement over the baseline
- Red cells: regression from the baseline

This is particularly useful after an optimisation run — you can compare the top 3 configurations and understand the trade-offs between them (e.g., higher win rate but lower trade count, or higher Sharpe but higher drawdown).

---

### 6.4 Performance Tuning

If the platform is slow during optimisation or backtesting:

**Reduce parallel workers:**
```
# In .env:
MAX_WORKERS=4   # Set to number of CPU cores minus 2
```

**Enable caching:**
```
# In .env:
TEST_CACHE_ENABLED=true
TEST_CACHE_TTL=3600
```
Caching stores loaded historical data in memory across test runs, eliminating repeated disk reads.

**Reduce history length:**
```
# In .env:
# Default: 300. Reduce if memory is limited.
PERF_HISTORY_LENGTH=300
```

**Use early stopping for optimisation:**
```
# In .env:
# Add both to .env:
# EARLY_STOP_PATIENCE=10
# EARLY_STOP_MIN_DELTA=0.001
```

---

### 6.5 Adding Building Blocks Over Time

As you gain experience, explore more building block categories. Each category has its own characteristics:

**Good starting blocks for beginners:**
- M-Pattern / W-Pattern (clear visual patterns, well-validated)
- RSI (universal, intuitive, reliable)
- London Session / NY Session (time filters that improve signal quality)

**Intermediate blocks to add once comfortable:**
- Fibonacci Levels (powerful confluence with patterns)
- Volume indicators (confirm momentum behind moves)
- Moving Average Crossovers (trend direction filter)

**Advanced blocks for experienced users:**
- Elliott Wave (complex, requires domain knowledge)
- Wyckoff (requires understanding of accumulation/distribution theory)
- SMC/ICT (institutional order flow concepts — high signal quality when correct)

---

### 6.6 Strategy Lifecycle

A strategy goes through a defined lifecycle on the platform:

```
Design → Validate (in-sample) → Validate (out-of-sample) → Testnet → Live (low risk) → Live (full risk)
```

**Design phase:** Build strategy in Window 1. Use real-time preview for quick feedback.

**Validate (in-sample):** Run walk-forward test on one year of data. Check metrics against targets.

**Validate (out-of-sample):** Run on a different period of data with no changes. Confirm robustness.

**Testnet:** Run live on simulated exchange for 2+ weeks. Confirm operational behaviour.

**Live (low risk):** Deploy with 50% of planned risk. Monitor for 1–2 months.

**Live (full risk):** Increase to full planned risk after consistent live performance confirmed.

**Retirement:** If a strategy's live performance degrades significantly from its validation metrics over 3+ months, retire it and rebuild from the design phase.

---

### Module 6 Summary

- Optimise only after the strategy concept is validated; keep parameter count low (2–3 at a time).
- Always validate optimised parameters on out-of-sample data.
- Concurrent strategies reduce portfolio risk — use low per-strategy risk when running many.
- Use Tab 5 (Compare) to quickly understand trade-offs between parameter configurations.
- Follow the strategy lifecycle: Design → Validate → Testnet → Live.

---

## Glossary

| Term | Definition |
|------|-----------|
| **Algorithm / Algo** | A fixed set of rules that a computer executes automatically |
| **AND Block** | A building block that must fire for a trade entry to be considered |
| **Autopilot** | Platform mode in which strategies run live, placing real orders automatically |
| **Bar / Candle** | A unit of price data representing one time period (Open, High, Low, Close, Volume) |
| **Building Block** | A self-contained market detector that emits named signals |
| **Confluence** | Multiple independent signals pointing in the same direction simultaneously |
| **Confluence Score** | The weighted sum of all active signals; must reach the threshold to trigger an entry |
| **Curve-Fitting** | Over-optimising a strategy to historical data so it performs well on that data but fails on new data |
| **Drawdown** | Decline from a peak account balance to a subsequent trough |
| **Entry** | The moment a position is opened |
| **Fibonacci Retracement** | A technical tool that identifies potential support/resistance levels at 23.6%, 38.2%, 50%, and 61.8% of a prior move |
| **Filter** | A signal role that acts as a prerequisite — the signal must be true for the entry to qualify |
| **Funding Rate** | A periodic fee/rebate on perpetual futures contracts to keep the futures price aligned with spot |
| **Leverage** | Trading a position larger than your account balance; amplifies both gains and losses |
| **Long** | A position that profits when price rises |
| **Max Drawdown** | The largest peak-to-trough decline observed during a test period |
| **OR Block** | A building block that is optional; fires add to the confluence score but are not required |
| **Out-of-Sample** | Historical data not used during strategy development; used only for final validation |
| **Perpetual Futures** | A futures contract with no expiry date |
| **Profit Factor** | Gross profit divided by gross loss; a value above 1.0 means the strategy is profitable |
| **Risk Per Trade** | The percentage of account capital at risk on each individual trade |
| **Sharpe Ratio** | A measure of risk-adjusted return; higher is better (target > 1.5) |
| **Short** | A position that profits when price falls |
| **Signal** | A named condition emitted by a building block when specific market conditions are met |
| **Stop Loss** | An automatic order that closes a losing position at a predefined price |
| **Take Profit** | An automatic order that closes a winning position at a predefined price |
| **Walk-Forward Test** | A sequential historical simulation that processes data candle-by-candle without lookahead |
| **Weight** | A numerical value assigned to each building block; determines its contribution to the confluence score |
| **Win Rate** | The percentage of completed trades that closed at a profit |

---

*For day-to-day operational reference, see the [User Guide](user-guide.md). For architecture and developer documentation, see `docs/architecture/`. For operational procedures (CI/CD, migrations, incident response), see `docs/runbook-*.md`.*
