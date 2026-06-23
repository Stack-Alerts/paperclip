// Institutional-grade tooltip content for the Backtest MetricsPanel.
// Follows the same schema and editorial standard as BacktestConfigTooltips.ts.
// Text is derived from industry definitions (Sharpe/Sortino/Calmar) and the
// PyQt5 thick-client results panel to keep both surfaces in sync.
//
// BTCAAAAA-35862: institutional-grade tooltips matching the strategy-builder
// quality bar requested in audit feedback.

import type { TooltipContent } from '@/components/strategy-builder/RichTooltip';

// ── Returns & Capital ─────────────────────────────────────────────────────────

export const TT_TOTAL_RETURN: TooltipContent = {
  title: 'Total Return (%)',
  body: 'Compound percentage gain or loss on the initial capital over the entire backtest period, calculated as (Final Capital − Initial Capital) / Initial Capital × 100.',
  sections: [
    {
      header: 'Formula:',
      items: [
        'Return % = (Final Capital − Initial Capital) / Initial Capital × 100',
        'Uses dollar-based equity curve — not the sum of per-trade percentages',
      ],
    },
    {
      header: 'Benchmarks:',
      items: [
        '< 0%: Strategy lost money — review entry/exit logic',
        '0–15%: Marginal — costs and slippage may erase live edge',
        '15–50%: Acceptable — verify robustness across market regimes',
        '> 50%: Strong — test for overfitting before live deployment',
      ],
    },
    { items: ['⚠️ Always compare against a buy-and-hold BTC benchmark for the same period.'] },
  ],
};

export const TT_NET_PROFIT: TooltipContent = {
  title: 'Net Profit (USD)',
  body: 'Absolute dollar P&L: Final Capital minus Initial Capital. Provides scale context that the percentage return alone cannot — a 50% return on $1,000 is not the same as 50% on $100,000.',
  sections: [
    {
      header: 'Formula:',
      items: ['Net Profit = Final Capital − Initial Capital'],
    },
    {
      header: 'Usage:',
      items: [
        'Compare across strategies with different starting capitals using Return % instead',
        'Use Net Profit to estimate real dollar exposure and slippage impact',
        'Negative net profit means the strategy destroyed capital',
      ],
    },
  ],
};

export const TT_INITIAL_CAPITAL: TooltipContent = {
  title: 'Initial Capital (USD)',
  body: 'Starting portfolio value configured before the backtest run. Acts as the denominator for all percentage-based metrics including Return %, Max Drawdown %, and Expectancy calculations.',
  sections: [
    {
      header: 'Critical for:',
      items: [
        'Position sizing — larger capital = larger absolute position sizes',
        'Drawdown % — same dollar loss is a smaller % on larger capital',
        'Realistic simulation — match your actual live trading capital',
      ],
    },
    {
      header: 'Recommended:',
      items: [
        '$10,000: Standard backtest default',
        'Match your actual trading capital for realistic results',
        'Do not inflate capital to artificially lower drawdown percentages',
      ],
    },
  ],
};

export const TT_FINAL_CAPITAL: TooltipContent = {
  title: 'Final Capital (USD)',
  body: 'Portfolio value at end of the backtest. Equals Initial Capital plus cumulative P&L from all closed trades, without compounding adjustments.',
  sections: [
    {
      header: 'How it works:',
      items: [
        'Tracks equity bar-by-bar as each trade closes',
        'Peak equity determines max drawdown reference point',
        'Final Capital drives Total Return % and Net Profit',
      ],
    },
    {
      header: 'Watch for:',
      items: [
        'Final Capital ≈ Initial Capital: strategy is flat — review edge',
        'Final Capital well above Initial: validate with out-of-sample data',
        'Final Capital below Initial: strategy is net-losing',
      ],
    },
  ],
};

// ── Risk Metrics ──────────────────────────────────────────────────────────────

export const TT_MAX_DRAWDOWN: TooltipContent = {
  title: 'Maximum Drawdown (%)',
  body: 'Largest peak-to-trough decline in portfolio equity expressed as a percentage of the peak value. Defines the worst-case historical loss an investor would have experienced.',
  sections: [
    {
      header: 'Formula:',
      items: ['Max DD% = (Peak Equity − Trough Equity) / Peak Equity × 100'],
    },
    {
      header: 'Benchmarks:',
      items: [
        '< 5%: Very low — conservative, may leave performance on table',
        '5–15%: Acceptable — suitable for most risk profiles',
        '15–25%: Elevated — review position sizing and stop distances',
        '> 25%: High — unsuitable for most live deployments',
      ],
    },
    {
      header: 'Critical for:',
      items: [
        'Position sizing — Kelly Criterion requires accurate drawdown estimates',
        'Investor suitability — drawdown > account equity triggers margin calls',
        'Calmar Ratio numerator — high drawdown kills Calmar',
      ],
    },
    { items: ['⚠️ Backtest drawdown is typically an underestimate of live drawdown.'] },
  ],
};

export const TT_SHARPE: TooltipContent = {
  title: 'Sharpe Ratio',
  body: 'Risk-adjusted return: mean per-trade return divided by the standard deviation of returns, scaled by √n. Measures reward earned per unit of total volatility (both upside and downside).',
  sections: [
    {
      header: 'Formula:',
      items: [
        'Sharpe = (Mean Return / Std Dev of Returns) × √n',
        'Computed on per-trade returns (% of capital per trade)',
        'Higher is better — measures edge quality, not just raw profit',
      ],
    },
    {
      header: 'Benchmarks:',
      items: [
        '< 0.5: Poor — returns don\'t justify the volatility',
        '0.5–1.0: Acceptable — marginal edge',
        '1.0–2.0: Good — solid risk-adjusted return',
        '> 2.0: Excellent — validate; may indicate overfitting',
      ],
    },
    {
      header: 'Limitations:',
      items: [
        'Penalises upside volatility equally with downside — use Sortino for skewed returns',
        'Sensitive to the number of trades — more trades = more stable estimate',
        'Does not account for fat-tail risk in crypto',
      ],
    },
  ],
};

export const TT_SORTINO: TooltipContent = {
  title: 'Sortino Ratio',
  body: 'Like Sharpe but penalises only downside volatility — the standard deviation of losing-trade returns. Preferred for strategies with positively skewed return distributions (more small losses, fewer large wins).',
  sections: [
    {
      header: 'Formula:',
      items: [
        'Sortino = (Mean Return / Downside Deviation) × √n',
        'Downside Deviation = √(mean of squared negative returns)',
        'Upside swings do not inflate the denominator',
      ],
    },
    {
      header: 'Benchmarks:',
      items: [
        '< 1.0: Needs improvement',
        '1.0–2.0: Good',
        '> 2.0: Excellent',
        'Sortino > Sharpe is expected for profitable strategies — confirms upside skew',
      ],
    },
    {
      header: 'Interpretation:',
      items: [
        'Sortino much higher than Sharpe: upside volatility is high — winning trades run far',
        'Sortino ≈ Sharpe: symmetric return distribution — review win/loss profile',
        'Sortino < Sharpe: unusual — suggests downside outliers larger than upside',
      ],
    },
  ],
};

export const TT_CALMAR: TooltipContent = {
  title: 'Calmar Ratio',
  body: 'Total annualised return divided by Maximum Drawdown. Directly balances the reward you earned against the worst historical pain you would have endured. Widely used in hedge fund and CTA evaluation.',
  sections: [
    {
      header: 'Formula:',
      items: [
        'Calmar = Total Return % / Max Drawdown %',
        'Higher is better — maximise return per unit of peak-to-trough risk',
      ],
    },
    {
      header: 'Benchmarks:',
      items: [
        '< 0.5: Poor — risk far exceeds return',
        '0.5–1.0: Acceptable — marginal return-to-risk',
        '1.0–3.0: Good — institutional quality range',
        '> 3.0: Excellent — validate before live deployment',
      ],
    },
    {
      header: 'Tuning:',
      items: [
        'Low Calmar + good Sharpe: drawdown is the bottleneck — tighten stops',
        'Good Calmar + low Sharpe: return is consistent but small — increase position size',
        'Both high: strategy is strong — run more out-of-sample tests',
      ],
    },
  ],
};

// ── Trade Statistics ──────────────────────────────────────────────────────────

export const TT_TOTAL_TRADES: TooltipContent = {
  title: 'Total Trades',
  body: 'Number of completed (closed) trades in the backtest. Statistical significance of all other metrics increases with trade count — low counts produce unreliable estimates.',
  sections: [
    {
      header: 'Guidelines:',
      items: [
        '< 30 trades: Insufficient — metrics are noise, not signal',
        '30–100: Minimum viable for preliminary analysis',
        '100–500: Statistically meaningful for most metrics',
        '> 500: High confidence — safe to draw conclusions',
      ],
    },
    {
      header: 'Tuning:',
      items: [
        'Too few trades? Lower confluence threshold or extend the lookback period',
        'Too many trades? Raise confluence or add a trend filter',
        'Target 200+ closed trades before committing to live deployment',
      ],
    },
  ],
};

export const TT_WIN_RATE: TooltipContent = {
  title: 'Win Rate (%)',
  body: 'Percentage of closed trades that ended in profit. Must be interpreted alongside Risk/Reward — a 40% win rate with a 3:1 R:R is more profitable than a 60% win rate with a 1:1 R:R.',
  sections: [
    {
      header: 'Formula:',
      items: ['Win Rate = Winning Trades / Total Trades × 100'],
    },
    {
      header: 'Context:',
      items: [
        'Compare against Breakeven Win Rate for margin of safety',
        'High win rate + poor R:R often worse than low win rate + strong R:R',
        'Win Rate > 50% is NOT required to be profitable',
      ],
    },
    {
      header: 'Directional bias check:',
      items: [
        'If Long Win Rate >> Short Win Rate: strategy is trend-direction dependent',
        'Stable Win Rate across bull and bear regimes: true robustness',
      ],
    },
  ],
};

export const TT_WINNING_TRADES: TooltipContent = {
  title: 'Winning Trades',
  body: 'Count of trades that closed with positive P&L (pnl > 0). Used with Total Trades to compute Win Rate and to verify the wins/losses split.',
};

export const TT_LOSING_TRADES: TooltipContent = {
  title: 'Losing Trades',
  body: 'Count of trades that closed at zero or negative P&L. Used with Winning Trades to assess balance and with Avg Loss to calculate Expectancy.',
  sections: [
    {
      items: [
        'High losing count + good Profit Factor: small individual losses, fine',
        'High losing count + poor Profit Factor: losses are too large — review stop placement',
      ],
    },
  ],
};

export const TT_PROFIT_FACTOR: TooltipContent = {
  title: 'Profit Factor',
  body: 'Gross profit across all winning trades divided by gross loss across all losing trades. A single ratio that captures both win rate and the average reward-to-risk in one number.',
  sections: [
    {
      header: 'Formula:',
      items: ['Profit Factor = Sum of Winning Trade P&L / |Sum of Losing Trade P&L|'],
    },
    {
      header: 'Benchmarks:',
      items: [
        '< 1.0: Losing strategy — gross losses exceed gross wins',
        '1.0–1.5: Marginal — thin edge, costs will hurt in live trading',
        '1.5–2.0: Good — sustainable edge with real transaction costs',
        '> 2.0: Excellent — verify for overfitting with out-of-sample test',
      ],
    },
    {
      header: 'Tuning:',
      items: [
        'PF < 1.5 with good Win Rate: Avg Loss is too large — tighten stops',
        'PF < 1.5 with poor Win Rate: too many losers — review signal quality',
        'PF > 3.0: Usually overfitted on small sample — validate on unseen data',
      ],
    },
  ],
};

export const TT_EXPECTANCY: TooltipContent = {
  title: 'Expectancy (USD per Trade)',
  body: 'Average dollar profit expected per trade across the full distribution. The mathematical edge of the strategy: (Win Rate × Avg Win) + (Loss Rate × Avg Loss). Positive = profitable on average.',
  sections: [
    {
      header: 'Formula:',
      items: [
        'Expectancy = (Win Rate × Avg Win) + ((1 − Win Rate) × Avg Loss)',
        'Avg Loss is negative — so this is a sum of positive and negative terms',
      ],
    },
    {
      header: 'Interpretation:',
      items: [
        'Negative expectancy: strategy destroys value on every trade on average',
        'Near-zero expectancy: thin edge — transaction costs will flip it negative in live trading',
        'Large positive expectancy: strong edge — validate with out-of-sample data',
      ],
    },
    {
      header: 'Critical for:',
      items: [
        'Position sizing — Kelly fraction = Expectancy / Avg Win',
        'Break-even transaction cost = Expectancy / (entry + exit cost)',
        'Risk-of-ruin calculations — requires positive expectancy',
      ],
    },
  ],
};

export const TT_AVG_WIN: TooltipContent = {
  title: 'Average Win (USD)',
  body: 'Mean dollar profit across all winning trades. Compare against Average Loss to evaluate the reward-to-risk profile. A strategy is not required to have Avg Win > Avg Loss to be profitable — Win Rate compensates.',
  sections: [
    {
      header: 'Usage:',
      items: [
        'Risk/Reward = Avg Win / |Avg Loss| — target ≥ 1.5 for robust strategies',
        'Avg Win dropping over time may indicate regime change — monitor live',
        'Very large Avg Win vs Avg Win suggests the strategy relies on outlier trades',
      ],
    },
  ],
};

export const TT_AVG_LOSS: TooltipContent = {
  title: 'Average Loss (USD)',
  body: 'Mean dollar loss across all losing trades (negative value). Ideally significantly smaller in magnitude than Average Win to produce a favourable Risk/Reward profile.',
  sections: [
    {
      header: 'Guidelines:',
      items: [
        'Avg Loss > Avg Win: requires high win rate (> 60%) to be profitable',
        'Avg Loss well below Avg Win: low win rate (35–50%) can still generate positive Expectancy',
        'Avg Loss much larger than expected from stop distance: review stop slippage and gap risk',
      ],
    },
    { items: ['⚠️ In live crypto trading, gap opens can cause losses well beyond stop placement.'] },
  ],
};

export const TT_RISK_REWARD: TooltipContent = {
  title: 'Risk / Reward Ratio',
  body: 'Average Win divided by absolute Average Loss. Represents dollars earned for each dollar risked per trade. Determines the minimum win rate needed to break even.',
  sections: [
    {
      header: 'Formula:',
      items: ['R:R = |Avg Win| / |Avg Loss|'],
    },
    {
      header: 'Benchmarks:',
      items: [
        '< 1.0: Unfavourable — requires win rate > 50% just to break even',
        '1.0–1.5: Acceptable with > 50% win rate',
        '1.5–2.5: Good — standard institutional target range',
        '> 2.5: Excellent — lower win rate acceptable',
      ],
    },
    {
      header: 'Breakeven win rate at common R:R levels:',
      items: [
        'R:R 1.0 → need 50% win rate',
        'R:R 1.5 → need 40% win rate',
        'R:R 2.0 → need 33% win rate',
        'R:R 3.0 → need 25% win rate',
      ],
    },
  ],
};

export const TT_BREAKEVEN_WIN: TooltipContent = {
  title: 'Breakeven Win Rate (%)',
  body: 'Minimum win rate required to break even at the current Risk/Reward ratio. Your actual Win Rate must exceed this value for the strategy to be net profitable.',
  sections: [
    {
      header: 'Formula:',
      items: ['Breakeven Win% = |Avg Loss| / (|Avg Win| + |Avg Loss|) × 100'],
    },
    {
      header: 'Usage:',
      items: [
        'Margin of Safety = Actual Win Rate − Breakeven Win Rate',
        'Larger margin = more robust to regime changes and performance decay',
        'Margin < 5%: fragile — small signal degradation kills profitability',
        'Margin > 15%: robust — has room to absorb real-world slippage and costs',
      ],
    },
    {
      header: 'Tuning:',
      items: [
        'Breakeven Win% too high: improve R:R by widening TP or tightening SL',
        'Breakeven Win% too low with poor Win Rate: check stop placement quality',
      ],
    },
  ],
};

// ── Trade Insights ────────────────────────────────────────────────────────────

export const TT_BEST_TRADE: TooltipContent = {
  title: 'Best Trade (USD)',
  body: 'Largest single-trade profit in the entire backtest. A large outlier relative to Average Win may indicate the strategy\'s total return depends on rare events that may not repeat.',
  sections: [
    {
      header: 'Watch for:',
      items: [
        'Best Trade > 5× Avg Win: outlier dependency — remove and re-check total return',
        'Best Trade during a specific market event (e.g., flash pump): not repeatable',
        'Best Trade consistent with Avg Win × 2–3: healthy distribution',
      ],
    },
  ],
};

export const TT_WORST_TRADE: TooltipContent = {
  title: 'Worst Trade (USD)',
  body: 'Largest single-trade loss in the entire backtest. Compare to Average Loss to assess stop-loss consistency and whether gap risk or slippage is creating outlier losses.',
  sections: [
    {
      header: 'Watch for:',
      items: [
        'Worst Trade > 3× Avg Loss: stop-loss was breached by gap or slippage',
        'Worst Trade ≈ Emergency SL × position size: expected maximum loss functioning correctly',
        'Multiple outlier losses: review max bars held and emergency stop settings',
      ],
    },
    { items: ['⚠️ In live trading, crypto gap risk can produce losses 2–5× larger than backtest worst.'] },
  ],
};

export const TT_AVG_BARS: TooltipContent = {
  title: 'Average Bars Held',
  body: 'Mean number of price bars a position was held open before closing. Combined with the timeframe, gives average trade duration in calendar time.',
  sections: [
    {
      header: 'Examples (15-minute bars):',
      items: [
        '10 bars: ~2.5 hours average hold',
        '50 bars: ~12.5 hours average hold',
        '200 bars: ~2 days average hold',
      ],
    },
    {
      header: 'Implications:',
      items: [
        'Short hold times: high transaction cost impact — verify net PnL after fees',
        'Long hold times: overnight/weekend gap risk exposure',
        'Very short holds with high win rate: potential look-ahead bias — audit entry logic',
      ],
    },
    {
      header: 'Guidelines:',
      items: [
        'Compare to Max Bars Held setting — large gap may indicate timeout-exits dominating',
        'Compare to Min Bars Held setting — near-equal means strategy is exiting at floor',
      ],
    },
  ],
};

export const TT_MAX_CONSEC_WINS: TooltipContent = {
  title: 'Max Consecutive Wins',
  body: 'Longest unbroken sequence of profitable trades. Useful for understanding momentum characteristics and for evaluating anti-martingale position sizing during hot streaks.',
  sections: [
    {
      header: 'Usage:',
      items: [
        'High streak (> 10): strategy has autocorrelation — consider scaling up during runs',
        'Low streak (≤ 3): returns are nearly random walk — avoid streak-based sizing',
        'Kelly Criterion does not require consecutive wins — use Expectancy instead',
      ],
    },
  ],
};

export const TT_MAX_CONSEC_LOSSES: TooltipContent = {
  title: 'Max Consecutive Losses',
  body: 'Longest unbroken sequence of losing trades. Defines the worst-case losing run the strategy produced historically. Live traders must be psychologically and financially prepared to endure this sequence without deviating from the strategy.',
  sections: [
    {
      header: 'Critical for:',
      items: [
        'Risk-of-ruin calculations — longer streaks require smaller position sizing',
        'Kelly Criterion — fraction must survive max losing streak without margin call',
        'Drawdown estimation — max losing streak × Avg Loss ≈ worst sequential drawdown',
      ],
    },
    {
      header: 'Guidelines:',
      items: [
        '≤ 5 losses: manageable for most traders',
        '5–10 losses: require strong discipline and adequate capital buffer',
        '> 10 losses: reduce position size or review strategy robustness',
      ],
    },
    { items: ['⚠️ Live performance typically produces longer losing streaks than backtest.'] },
  ],
};

export const TT_LONG_TRADES: TooltipContent = {
  title: 'Long Trades',
  body: 'Number of trades entered in the long (buy) direction. Compare to Short Trades to identify directional bias.',
  sections: [
    {
      header: 'Directional bias check:',
      items: [
        'Long >> Short: strategy is bullish-biased — will underperform in bear markets',
        'Balanced Long/Short: strategy is regime-agnostic — more robust',
        'Check Long Win Rate vs Short Win Rate separately for deeper analysis',
      ],
    },
  ],
};

export const TT_SHORT_TRADES: TooltipContent = {
  title: 'Short Trades',
  body: 'Number of trades entered in the short (sell) direction. Heavy skew toward one direction may mean the strategy only works in a specific market regime.',
  sections: [
    {
      header: 'Directional bias check:',
      items: [
        'Short >> Long: strategy is bearish-biased — will underperform in bull markets',
        'If strategy is long-only by design: compare to neutral baseline',
        'Crypto markets have historically been long-biased — short edge is harder to maintain',
      ],
    },
  ],
};

// ── Backtest Period ───────────────────────────────────────────────────────────

export const TT_START_DATE: TooltipContent = {
  title: 'Backtest Start Date',
  body: 'First date from which historical price data was included in this backtest run. Determined by the lookback period setting minus training window offset.',
};

export const TT_END_DATE: TooltipContent = {
  title: 'Backtest End Date',
  body: 'Last date up to which price data was processed. Corresponds to the most recent bar in the historical dataset for this instrument.',
};

export const TT_DURATION: TooltipContent = {
  title: 'Backtest Duration (Days)',
  body: 'Total calendar days covered by the backtest. Longer periods expose the strategy to more market regimes — bull, bear, ranging — and improve the statistical robustness of all metrics.',
  sections: [
    {
      header: 'Guidelines:',
      items: [
        '< 90 days: Insufficient — metrics highly regime-dependent',
        '90–365 days: Acceptable minimum for preliminary validation',
        '365–730 days: Recommended — covers at least one full market cycle',
        '> 730 days: Strong — includes multiple regimes including at least one bear market',
      ],
    },
    { items: ['⚠️ BTC had distinct regimes in 2020 (COVID crash), 2021 (bull), 2022 (bear), 2023–2024 (recovery/bull). Include all four.'] },
  ],
};

export const TT_BARS_ANALYZED: TooltipContent = {
  title: 'Bars Analyzed',
  body: 'Total number of price candles processed during the backtest. Confirms data density and the effective resolution of the historical dataset.',
  sections: [
    {
      header: 'Expected counts (15m bars):',
      items: [
        '90 days: ~8,640 bars',
        '180 days: ~17,280 bars',
        '365 days: ~35,040 bars',
      ],
    },
    {
      header: 'Watch for:',
      items: [
        'Count much lower than expected: gaps in data — may bias results toward liquid periods',
        'Count matches expectation: clean continuous data feed',
      ],
    },
  ],
};

// ── Exit Type (dynamic) ───────────────────────────────────────────────────────

export function TT_EXIT_TYPE(label: string, count: number, total: number): TooltipContent {
  const pct = ((count / total) * 100).toFixed(0);
  return {
    title: `Exit Type: ${label}`,
    body: `${count} of ${total} trades (${pct}%) exited via "${label}".`,
    sections: [
      {
        header: 'Exit type meanings:',
        items: [
          'TP / TP1 / TP2 / TP3: Take-profit target reached — expected winning exit',
          'SL: Stop-loss triggered — expected losing exit',
          'Time / Max Bars: Position auto-closed at max hold limit',
          'Signal: Opposing entry signal closed the position early',
        ],
      },
      {
        header: 'Interpretation:',
        items: [
          'High SL% relative to TP%: stops may be too tight — or entries are poor quality',
          'High Time% / Max Bars%: strategy struggles to reach TP — review TP distance',
          'Balanced TP/SL split: healthy exit distribution — validate with Win Rate',
        ],
      },
    ],
  };
}

// ── New tooltips (BTCAAAAA-37920 — Matrix blocks update) ──────────────────────

export const TT_ADDITIONAL_METRICS: TooltipContent = {
  title: 'Building-Block Signal Diagnostics',
  body: 'Per-trade telemetry for the underlying signal pipeline that produced each entry, recheck, and exit. These counts expose how decisive the strategy was on average — a clean signal cluster drives entries without lots of re-confirmations; a noisy cluster spends the trade waiting for clarity.',
  sections: [
    {
      header: 'Includes:',
      items: [
        'Signals Required — building-block signals fired before the entry committed',
        'Rechecks — additional signals fired while the position was open to re-confirm the thesis',
        'Exit Signals — explicit building-block exit events (distinct from SL/TP/time exits)',
        'Stop-Loss Adjustments — number of SL moves during the life of the trade',
      ],
    },
    {
      header: 'Interpretation:',
      items: [
        'Low Signals Required + low Rechecks: high-conviction entries — fast in, fast out',
        'High Rechecks: thesis needs reinforcement — expect chop on the way to TP',
        'Many Exit Signals: the building-block framework is the dominant exit reason (vs SL/TP)',
        'Many SL Adjustments: trailing/ratcheting stops are active — review SL configuration',
      ],
    },
  ],
};

export const TT_SIGNALS_REQUIRED: TooltipContent = {
  title: 'Signals Required (per trade)',
  body: 'Number of building-block signals that fired between entry decision and the actual entry fill. A value of 1 means the first qualifying signal opened the trade; higher values mean the strategy waited for additional confirmation before committing capital.',
  sections: [
    {
      header: 'How it is measured:',
      items: [
        'Count of fired signal events during the entry-confirmation window for each trade',
        'Window length is strategy-defined (typically a few bars before entry)',
        'Reported as the mean across all trades in the backtest',
      ],
    },
    {
      header: 'Interpretation:',
      items: [
        'Mean ≈ 1: strategy enters on first signal — high fill rate, more whipsaw risk',
        'Mean 2–3: balanced — filters weak setups without much slippage',
        'Mean > 3: heavy confirmation — fewer trades, better quality, possible missed moves',
      ],
    },
  ],
};

export const TT_RECHECKS: TooltipContent = {
  title: 'Rechecks (per trade)',
  body: 'Number of additional building-block signals that fired while the position was still open. Rechecks re-validate the original thesis (or its inverse); a high count means the market kept producing signal events during the trade.',
  sections: [
    {
      header: 'How it is measured:',
      items: [
        'Count of signal events firing between entry fill and exit fill, excluding the entry signal itself',
        'Signals may agree with the position (re-confirm) or oppose it (early warning)',
        'Reported as the mean across all closed trades',
      ],
    },
    {
      header: 'Interpretation:',
      items: [
        'Low rechecks (≈ 0): clean move — entry thesis carried the trade',
        'Moderate rechecks (2–5): normal for trend-following on multi-bar trades',
        'High rechecks (> 10): noisy regime — position spent time under question; consider tighter exits',
      ],
    },
  ],
};

export const TT_EXIT_SIGNALS: TooltipContent = {
  title: 'Exit Signals (per trade)',
  body: 'Count of building-block exit signals that fired during the life of the trade. An exit signal is a deliberate "close now" event from the signal framework — distinct from stop-loss, take-profit, time-based, or end-of-backtest exits.',
  sections: [
    {
      header: 'How it is measured:',
      items: [
        'Counts only signals explicitly tagged as exit-type by the building-block framework',
        'A trade can have more than one exit signal before it closes (the framework re-emits on each new bar)',
        'Reported as the mean across all closed trades',
      ],
    },
    {
      header: 'Interpretation:',
      items: [
        '≈ 0 exit signals + high win rate: exits are dominated by TP — review whether SL is too wide',
        '≥ 1 exit signal: the framework is actively closing positions — pair with Exit Type breakdown',
        'Many exit signals + losing trades: exit signals are firing too late — review the exit detector',
      ],
    },
  ],
};

export const TT_STOP_LOSS_ADJUSTMENTS: TooltipContent = {
  title: 'Stop-Loss Adjustments (per trade)',
  body: 'Number of times the stop-loss was moved (tightened or ratcheted) while the trade was open. A value of 0 means the SL stayed at its initial level for the entire trade; higher values mean trailing/ratcheting logic was active.',
  sections: [
    {
      header: 'How it is measured:',
      items: [
        'Count of SL update events between entry fill and exit fill',
        'Includes both tightening (toward price) and loosening (away from price) moves',
        'Reported as the mean across all closed trades',
      ],
    },
    {
      header: 'Interpretation:',
      items: [
        '0 adjustments: fixed SL — exit distance was set once at entry',
        '1–3 adjustments: light trailing — common for breakout strategies',
        'Many adjustments: aggressive trailing/ratcheting — locks in profit but can be stopped out prematurely',
      ],
    },
  ],
};

export const TT_VOLATILITY: TooltipContent = {
  title: 'Return Volatility (σ per trade)',
  body: 'Standard deviation of per-trade percentage returns across all trades in the backtest. Higher values indicate more dispersed outcomes — both larger wins and larger losses relative to the mean trade return.',
  sections: [
    {
      header: 'Formula:',
      items: [
        'σ = √( Σ (rᵢ − r̄)² / (N − 1) )',
        'rᵢ = per-trade return (%) for trade i, r̄ = mean per-trade return',
        'Sample stddev (N−1) — matches the convention used by Sharpe/Sortino denominators',
      ],
    },
    {
      header: 'Interpretation:',
      items: [
        'Low σ (< avg return): consistent per-trade performance',
        'High σ (> 2× avg return): "lottery ticket" profile — review Largest Win / Largest Loss distribution',
        'Compare with Avg Win / Avg Loss — high σ with positive expectancy is preferable to high σ with negative expectancy',
      ],
    },
  ],
};

export const TT_VAR_95: TooltipContent = {
  title: 'Value at Risk (95%)',
  body: 'Worst expected per-trade loss at 95% confidence — the return level below which only 5% of historical trades fall. Quantifies downside tail risk on a per-trade basis.',
  sections: [
    {
      header: 'Formula:',
      items: [
        'VaR₉₅ = 5th percentile of {r₁, r₂, …, r_N} (per-trade returns)',
        'Returns a negative number for the typical long-volatility profile',
        'Reported in % so it can be compared directly with avg loss',
      ],
    },
    {
      header: 'Interpretation:',
      items: [
        'VaR₉₅ = −2.5%: in 1 of 20 trades you should expect to lose at least 2.5% of notional',
        'VaR₉₅ < 2× |Avg Loss|: tail risk is well-explained by the average — strategy behaves predictably',
        'VaR₉₅ >> |Avg Loss|: rare but severe losses dominate — review Largest Loss trades and SL placement',
      ],
    },
    { items: ['⚠️ Requires N ≥ 20 trades for a statistically meaningful percentile.'] },
  ],
};

export const TT_CVAR_95: TooltipContent = {
  title: 'Conditional VaR (95%) — Expected Shortfall',
  body: 'Average loss in the worst 5% of trades. Where VaR tells you the threshold, CVaR tells you the expected damage once you cross it. Always ≤ VaR₉₅ (more negative).',
  sections: [
    {
      header: 'Formula:',
      items: [
        'CVaR₉₅ = mean( rᵢ : rᵢ ≤ VaR₉₅ )',
        'Computed over the bottom 5% of trade returns',
        'Coherent risk measure — sub-additive, unlike VaR',
      ],
    },
    {
      header: 'Interpretation:',
      items: [
        'Use CVaR for stress-test sizing — size positions to absorb the average tail loss',
        'CVaR₉₅ / |Avg Loss| ratio: > 1.5× indicates a fat-tailed loss distribution',
        '|CVaR₉₅ − VaR₉₅| ≈ 0: thin tails (Gaussian-like); large gap: heavy tails',
      ],
    },
  ],
};

export const TT_EXPOSURE_TIME: TooltipContent = {
  title: 'Market Exposure Time',
  body: 'Fraction of the backtest period the strategy held an open position. Strategies that sit in cash most of the time have lower exposure and therefore lower return volatility per unit of time.',
  sections: [
    {
      header: 'Formula:',
      items: [
        'Exposure % = Σ(bars held in trades) / total bars analyzed × 100',
        'Each closed trade contributes its `bars` field; partial bars round toward full-bar resolution',
        'Open positions at backtest end are excluded',
      ],
    },
    {
      header: 'Interpretation:',
      items: [
        'Exposure < 30%: low-frequency / patient — long flat periods between setups',
        'Exposure 30–70%: typical intraday-to-swing profile',
        'Exposure > 80%: near-continuous — return volatility compounds with exposure; size positions accordingly',
      ],
    },
  ],
};

export const TT_PAYOFF_RATIO: TooltipContent = {
  title: 'Payoff Ratio (Σ wins / Σ losses)',
  body: 'Total gross profit divided by total gross loss across the backtest. Distinct from Risk/Reward Ratio (avg win / avg loss) — Payoff captures aggregate profitability rather than the average trade.',
  sections: [
    {
      header: 'Formula:',
      items: [
        'Payoff = Σ(pnl of winning trades) / Σ(|pnl| of losing trades)',
        'Returns the gross-ratio — does not adjust for trade count or time',
      ],
    },
    {
      header: 'Interpretation:',
      items: [
        'Payoff > 1: gross profits exceed gross losses — required for net-positive P&L at any win rate',
        'Payoff = 2 with 40% win rate ≈ breakeven after costs; Payoff = 3 → net profitable from 26% win rate',
        'Payoff < 1: losers dominate — improve exits (TP distance) before adding entries',
      ],
    },
    { items: ['⚠️ Combine with Win Rate and Profit Factor for a complete picture.'] },
  ],
};

export const TT_LARGEST_WIN: TooltipContent = {
  title: 'Largest Winning Trade',
  body: 'Single highest-grossing trade in the backtest. The peak contribution to total profit — useful for assessing concentration: does one trade drive the strategy, or is profit distributed?',
  sections: [
    {
      header: 'Watch for:',
      items: [
        'Largest Win ≈ 3× Avg Win: outlier suggests a fat right tail — desirable',
        'Largest Win / Net Profit > 50%: profit is concentrated in one trade — robustness risk',
        'Compare with Avg Win — large divergence indicates the strategy occasionally captures a regime-specific move',
      ],
    },
  ],
};

export const TT_LARGEST_LOSS: TooltipContent = {
  title: 'Largest Losing Trade',
  body: 'Single biggest loss in the backtest. The worst-case drawdown event. Bounds the per-trade risk that position sizing and stop placement must absorb.',
  sections: [
    {
      header: 'Watch for:',
      items: [
        'Largest Loss ≈ 2× |Avg Loss|: within expected distribution — SL is doing its job',
        'Largest Loss >> 3× |Avg Loss|: stop was either too wide or skipped — review that trade in the trade log',
        'Largest Loss < |Avg Loss|: outliers are wins, not losses — unusually controlled downside',
      ],
    },
  ],
};

export const TT_CURRENCY: TooltipContent = {
  title: 'Quote Currency',
  body: 'Currency in which all dollar-denominated metrics (Net Profit, Final Capital, Avg Win / Loss, etc.) are reported. Defaults to USDT for crypto pairs — the quote currency of the canonical BTC.P/USDT backtest.',
  sections: [
    {
      header: 'Notes:',
      items: [
        'USDT-pegged values are treated as USD-equivalent for reporting',
        'If you trade a non-USDT pair (e.g. BTC/EUR), dollar figures are still reported in USDT after engine conversion',
        'Pair-level notionals and P&L are denominated in this currency throughout',
      ],
    },
  ],
};
