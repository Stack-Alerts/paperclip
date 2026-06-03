// Institutional-grade tooltip content for the BacktestConfigDialog Config tab.
// Each entry is the institutional definition lifted from the PyQt5 thick-client
// backtest panel (src/strategy_builder/ui/backtest_config_panel.py) and reshaped
// into the RichTooltip {title, body, sections} schema.
//
// BTCAAAAA-34257: board called out that every clickable element and every field
// in this dialog needs an institutional-grade tooltip matching the thick client.
// Keeping the text close to the thick-client source means future thick-client
// edits can be diffed against this file to keep the two surfaces in sync.

import type { TooltipContent } from './RichTooltip';

export const TT_LOOKBACK: TooltipContent = {
  title: 'Historical Data Lookback Period',
  body: 'Total days of historical data to load for backtesting.',
  sections: [
    {
      header: 'Includes:',
      items: [
        'Training period (for strategy calibration)',
        'Testing period (for strategy validation)',
      ],
    },
    { items: ['Example: 180 days allows 90-day training + 90-day testing'] },
    { items: ['Recommendation: At least 2x training period'] },
  ],
};

export const TT_TRAINING: TooltipContent = {
  title: 'Strategy Training Window',
  body: 'Period used to calibrate strategy parameters and learn patterns.',
  sections: [
    {
      header: 'Used for:',
      items: [
        'Pattern recognition training',
        'Parameter optimization',
        'Feature learning',
      ],
    },
    {
      header: 'Best Practice:',
      items: [
        'Minimum 60 days for reliable patterns',
        '90 days recommended for crypto volatility',
      ],
    },
  ],
};

export const TT_TESTING: TooltipContent = {
  title: 'Strategy Testing Window',
  body: 'Out-of-sample period for strategy validation.',
  sections: [
    {
      header: 'Purpose:',
      items: [
        'Test strategy on unseen data',
        'Detect overfitting',
        'Validate performance metrics',
      ],
    },
    {
      header: 'Best Practice:',
      items: [
        'At least 30 days for meaningful results',
        'Should represent diverse market conditions',
      ],
    },
  ],
};

export const TT_MODE_HISTORICAL: TooltipContent = {
  title: 'Mode 1: Historical Backtest',
  body: 'Standard historical data analysis mode.',
  sections: [
    {
      header: 'How it works:',
      items: [
        'Loads all historical data at once',
        'Processes bars sequentially',
        'Fast execution',
      ],
    },
    {
      header: 'Best for:',
      items: [
        'Quick strategy testing',
        'Parameter optimization',
        'Walk-forward analysis',
      ],
    },
    { items: ["Limitation: Can't simulate real-time conditions"] },
  ],
};

// Note: Mode 2 Walk has no verbatim thick-client tooltip; institutional-equivalent
// text written from surrounding code context (per audit comment 2026-06-03).
export const TT_MODE_WALK: TooltipContent = {
  title: 'Mode 2: Walk-Forward Optimization',
  body: 'Re-trains strategy parameters at each step using a rolling window, then evaluates out-of-sample.',
  sections: [
    {
      header: 'How it works:',
      items: [
        'Slide a training window across the lookback range',
        'Refit at each step, evaluate on the next testing slice',
        'Roll the window and repeat',
      ],
    },
    {
      header: 'Best for:',
      items: [
        'Detecting parameter drift over time',
        'Stress-testing robustness to regime changes',
        'Final pre-live validation',
      ],
    },
    { items: ['Slowest of the three modes; most realistic generalisation estimate.'] },
  ],
};

export const TT_MODE_LIVE_REPLAY: TooltipContent = {
  title: 'Mode 2: Live Replay Simulation',
  body: 'Simulates real-time trading conditions.',
  sections: [
    {
      header: 'How it works:',
      items: [
        'Feeds data bar-by-bar as if live',
        'Strategy only sees past data',
        'More realistic execution',
      ],
    },
    {
      header: 'Best for:',
      items: [
        'Final strategy validation',
        'Testing order execution logic',
        'Real-time decision verification',
      ],
    },
    { items: ['Note: Slower than Mode 1, more realistic'] },
  ],
};

export const TT_TPSL_CONFIG: TooltipContent = {
  title: 'TP/SL Initial Calculation Method',
  body: 'Controls HOW initial TP/SL levels are calculated at entry.',
  sections: [
    {
      header: 'Fibonacci:',
      items: [
        'TP levels at Fibonacci retracements (0.382, 0.618, 1.0)',
        'SL at key Fibonacci support/resistance',
        'Dynamic based on recent price structure',
        'Best for: Trend-following strategies',
      ],
    },
    {
      header: 'Hybrid (Recommended):',
      items: [
        'Combines Fibonacci levels with volatility (ATR)',
        'Adapts to market conditions',
        'Best for: All-weather strategies',
      ],
    },
    {
      header: 'Fixed:',
      items: [
        'Static percentage-based TP/SL from entry',
        'Simple, predictable risk/reward',
        'Best for: Scalping, high-frequency strategies',
      ],
    },
    { items: ['NOTE: This is separate from SL Adjustment below.'] },
  ],
};

export const TT_SL_ADJUSTMENT: TooltipContent = {
  title: 'Stop Loss Adjustment Behavior',
  body: 'Controls WHETHER the SL adjusts AFTER entry.',
  sections: [
    {
      header: 'Adaptive v2.0 (Recommended):',
      items: [
        'SL dynamically adjusts during trade lifetime',
        'Widens in volatile conditions (protects from noise)',
        'Tightens in calm markets (locks in profits)',
        'Uses market structure (swing highs/lows)',
        'Delayed activation to avoid stop-hunting',
        'Emergency SL for immediate catastrophic protection',
      ],
    },
    {
      header: 'Benefits:',
      items: [
        'Adapts to changing conditions',
        'Reduces false stop-outs by 15-25%',
        'Improves win rate by 10-15%',
        'Institutional-grade protection',
      ],
    },
    {
      header: 'Static:',
      items: [
        'SL stays fixed after entry (no adjustment)',
        'Simple, predictable behavior',
        'Uses initial calculation only',
      ],
    },
    {
      header: 'Difference from TP/SL Config:',
      items: [
        'TP/SL Config = How to CALCULATE initial levels',
        'SL Adjustment = Whether SL CHANGES during trade',
      ],
    },
  ],
};

export const TT_PRESET_CONSERVATIVE: TooltipContent = {
  title: '🐢 Conservative Preset',
  body: 'Wider stop losses for maximum protection.',
  sections: [
    {
      header: 'Configuration:',
      items: [
        'Delay: 3 bars (maximum protection window)',
        'Emergency SL: 3% (wider safety net)',
        'Vol Multi: 1.5x (50% beyond volatility)',
        'Min SL: 1.0% | Max SL: 2.5%',
        'Market Structure: Enabled',
      ],
    },
    {
      header: 'Trading Profile:',
      items: [
        'Win Rate: 60-70% (higher)',
        'Trade Frequency: Lower (quality over quantity)',
        'Risk per Trade: Lower',
        'Ideal for: Risk-averse traders, volatile markets',
      ],
    },
  ],
};

export const TT_PRESET_BALANCED: TooltipContent = {
  title: '⚖️ Balanced Preset (Recommended)',
  body: 'Optimal balance of protection and opportunity.',
  sections: [
    {
      header: 'Configuration:',
      items: [
        'Delay: 2 bars (standard protection)',
        'Emergency SL: 2% (standard safety)',
        'Vol Multi: 1.2x (20% beyond volatility)',
        'Min SL: 0.7% | Max SL: 2.0%',
        'Market Structure: Enabled',
      ],
    },
    {
      header: 'Trading Profile:',
      items: [
        'Win Rate: 50-60% (balanced)',
        'Trade Frequency: Moderate',
        'Risk per Trade: Moderate',
        'Ideal for: Most traders, general market conditions',
      ],
    },
  ],
};

export const TT_PRESET_AGGRESSIVE: TooltipContent = {
  title: '🚀 Aggressive Preset',
  body: 'Tighter stops for maximum trade frequency.',
  sections: [
    {
      header: 'Configuration:',
      items: [
        'Delay: 1 bar (minimal protection window)',
        'Emergency SL: 2% (standard safety)',
        'Vol Multi: 1.0x (at volatility level)',
        'Min SL: 0.6% | Max SL: 1.5%',
        'Market Structure: Enabled',
      ],
    },
    {
      header: 'Trading Profile:',
      items: [
        'Win Rate: 40-50% (lower)',
        'Trade Frequency: Higher (more opportunities)',
        'Risk per Trade: Higher',
        'Ideal for: Active traders, momentum strategies',
      ],
    },
  ],
};

export const TT_PRESET_CUSTOM: TooltipContent = {
  title: '💠 Custom Preset',
  body: 'Your manually configured settings.',
  sections: [
    {
      header: 'How it works:',
      items: [
        'Select a preset (Conservative/Balanced/Aggressive)',
        'Manually adjust any value',
        'Custom preset automatically activates',
        'Your manual settings are preserved',
      ],
    },
    {
      header: 'Benefits:',
      items: [
        'Experiment with preset starting points',
        'Fine-tune to your exact needs',
        'Always return to your custom configuration',
      ],
    },
  ],
};

export const TT_PRESETS_LABEL: TooltipContent = {
  title: 'Adaptive SL Presets',
  body: 'Frozen snapshots of the 8 Adaptive SL knobs. Clicking a preset applies all 8 at once; diverging any knob auto-flips to Custom.',
  sections: [
    {
      header: 'Available presets:',
      items: [
        '🐢 Conservative — wider stops, higher win rate',
        '⚖️ Balanced — recommended default',
        '🚀 Aggressive — tighter stops, higher frequency',
        '💠 Custom — your manual configuration',
      ],
    },
  ],
};

export const TT_DELAY_STOP_LOSS: TooltipContent = {
  title: 'Delayed Stop Loss Activation',
  body: 'Delays stop loss activation after entry to avoid immediate stop-outs.',
  sections: [
    {
      header: 'How it works:',
      items: [
        'Entry at bar N',
        'SL activates at bar N + Delay Period',
        'Emergency SL protects immediately',
      ],
    },
    {
      header: 'Benefits:',
      items: [
        'Reduces false stop-outs from entry volatility',
        'Improves win rate by 10-15%',
        'Emergency SL provides immediate protection',
      ],
    },
    { items: ['Recommendation: 2 bars for 15m timeframe'] },
  ],
};

export const TT_MARKET_STRUCTURE_STOP: TooltipContent = {
  title: 'Market Structure Stop Loss Placement',
  body: 'When enabled, places stop loss at key market structure levels.',
  sections: [
    {
      header: 'Levels considered:',
      items: [
        'Swing highs/lows (recent price pivots)',
        'Supply/Demand zones',
        'Fibonacci retracement levels',
      ],
    },
    {
      header: 'Benefits:',
      items: [
        'Stop loss placed beyond key levels',
        'Reduces false stop-outs',
        'Increases win rate by 5-10%',
      ],
    },
    { items: ['When disabled: uses percentage-based SL only (volatility multiplier).'] },
  ],
};

export const TT_STOP_LOSS_DELAY: TooltipContent = {
  title: 'Stop Loss Delay Period',
  body: 'Number of bars to wait before activating normal stop loss.',
  sections: [
    {
      header: 'During delay:',
      items: [
        'Emergency SL protects position',
        'Normal SL is not yet active',
        'Prevents immediate stop-outs',
      ],
    },
    {
      header: 'Guidelines:',
      items: [
        '0 bars: Traditional SL (no delay)',
        '1-2 bars: Balanced (recommended)',
        '3+ bars: Conservative (wider protection)',
      ],
    },
  ],
};

export const TT_EMERGENCY: TooltipContent = {
  title: 'Emergency Stop Loss',
  body: 'Wide catastrophic-loss protection during delay period.',
  sections: [
    {
      header: 'Purpose:',
      items: [
        'Protects against flash crashes',
        'Prevents total capital loss',
        'Active immediately after entry',
      ],
    },
    {
      header: 'Setting Guidelines:',
      items: [
        '2%: Standard (recommended)',
        '3%: Conservative (more room)',
        '1.5%: Aggressive (tighter)',
      ],
    },
    { items: ['Should be 2-3x wider than normal SL'] },
  ],
};

export const TT_VOL_LOOKBACK: TooltipContent = {
  title: 'Volatility Lookback Period',
  body: 'Number of bars used to calculate recent volatility (ATR).',
  sections: [
    {
      header: 'Purpose:',
      items: [
        'Measures market volatility',
        'Adapts SL to current conditions',
        'Wider SL in volatile markets',
      ],
    },
    {
      header: 'Guidelines:',
      items: [
        '14-20 bars: Standard ATR period',
        '10 bars: More responsive',
        '30+ bars: Smoother, less reactive',
      ],
    },
    { items: ['Recommendation: 20 bars (default ATR)'] },
  ],
};

export const TT_VOL_MULTIPLIER: TooltipContent = {
  title: 'Volatility Multiplier',
  body: 'How many times ATR to use for stop loss distance.',
  sections: [
    { items: ['Formula: SL = Entry ± (ATR × Multiplier)'] },
    {
      header: 'Examples (ATR = $100):',
      items: [
        '1.0x: SL at $100 from entry',
        '1.2x: SL at $120 from entry (recommended)',
        '1.5x: SL at $150 from entry (conservative)',
      ],
    },
    {
      header: 'Guidelines:',
      items: [
        'Lower = Tighter SL, higher risk',
        'Higher = Wider SL, more breathing room',
      ],
    },
  ],
};

export const TT_MIN_STOP_LOSS: TooltipContent = {
  title: 'Minimum Stop Loss Distance',
  body: 'Minimum allowed SL distance as % from entry.',
  sections: [
    {
      header: 'Purpose:',
      items: [
        'Prevents stops too tight to entry',
        'Ensures minimum breathing room',
        'Floor for volatility-based SL',
      ],
    },
    {
      header: 'Guidelines:',
      items: [
        '0.5-0.7%: Aggressive, scalping',
        '0.8-1.0%: Balanced (recommended)',
        '1.5%+: Conservative, swing trading',
      ],
    },
  ],
};

export const TT_MAX_STOP_LOSS: TooltipContent = {
  title: 'Maximum Stop Loss Distance',
  body: 'Maximum allowed SL distance as % from entry.',
  sections: [
    {
      header: 'Purpose:',
      items: [
        'Caps risk per trade',
        'Prevents excessive stop distances',
        'Ceiling for volatility-based SL',
      ],
    },
    {
      header: 'Guidelines:',
      items: [
        '1.5%: Tight risk control',
        '2.0%: Standard (recommended)',
        '2.5%+: Larger swing-trading stops',
      ],
    },
  ],
};

export const TT_STARTING_CAPITAL: TooltipContent = {
  title: 'Starting Capital (USD)',
  body: 'NautilusTrader-typed Money value used as the simulated account balance.',
  sections: [
    {
      header: 'Critical for:',
      items: [
        'Position sizing calculations',
        'Risk management (% of capital per trade)',
        'Metric calculations (return %, drawdown %)',
        'ML training features',
      ],
    },
    {
      header: 'Validation (Futures with Leverage):',
      items: [
        'Minimum: $500 (small accounts with leverage)',
        'Maximum: $1,000,000 (institutional size)',
      ],
    },
    {
      header: 'Examples:',
      items: [
        '$500: Micro account (high leverage required)',
        '$1,000: Small account (10-20x leverage typical)',
        '$10,000: Standard account (balanced leverage)',
        '$100,000: Large account (lower leverage needed)',
      ],
    },
    {
      header: 'Recommended:',
      items: [
        'Backtesting: $10,000 default',
        'Match your actual trading capital for realistic results',
      ],
    },
  ],
};

export const TT_MIN_RR: TooltipContent = {
  title: 'Minimum Risk:Reward Ratio',
  body: 'Required profit potential vs risk for trade entry.',
  sections: [
    { items: ['Formula: Reward / Risk'] },
    {
      header: 'Examples:',
      items: [
        '1.2 → $120 reward for $100 risk',
        '1.5 → $150 reward for $100 risk',
        '2.0 → $200 reward for $100 risk',
      ],
    },
    {
      header: 'Guidelines:',
      items: [
        '1.0-1.2: Aggressive (high win rate needed)',
        '1.5-2.0: Balanced (recommended)',
        '2.5+: Conservative (lower win rate acceptable)',
      ],
    },
  ],
};

export const TT_RISK_PCT: TooltipContent = {
  title: 'Risk Per Trade (% of Capital)',
  body: 'Percentage of capital risked on each trade.',
  sections: [
    {
      header: 'Examples ($10,000 account):',
      items: [
        '5%: Risk $500 per trade',
        '10%: Risk $1,000 per trade (backtest only!)',
        '2%: Risk $200 per trade (conservative)',
      ],
    },
    {
      header: 'Guidelines:',
      items: [
        'Backtesting: 5-10% acceptable for testing',
        'Live Trading: 1-2% maximum (institutional standard)',
        'Never risk more than you can afford to lose',
      ],
    },
    { items: ['⚠️ High values for testing only — use 1-2% for live.'] },
  ],
};

export const TT_LEVERAGE: TooltipContent = {
  title: 'Maximum Leverage Multiplier',
  body: 'Maximum position size relative to capital.',
  sections: [
    {
      header: 'Examples ($10,000 capital):',
      items: [
        '1x: $10,000 max position (no leverage)',
        '10x: $100,000 max position',
        '20x: $200,000 max position',
      ],
    },
    {
      header: 'Risk Levels:',
      items: [
        '1x: No leverage (safest)',
        '2-5x: Conservative leveraged',
        '10-20x: Moderate (crypto standard)',
        '50x+: High risk (volatile liquidation risk)',
      ],
    },
    { items: ['⚠️ Higher leverage = Higher liquidation risk.'] },
  ],
};

export const TT_CONFLUENCE: TooltipContent = {
  title: 'Minimum Confluence Points',
  body: 'Required signal strength for trade entry. Points vary based on selected strategy.',
  sections: [
    {
      header: 'How Confluence Works:',
      items: [
        'Each building block contributes points',
        'Required signals always add points',
        'Optional signals contribute bonus points',
        'Timing requirements must align',
      ],
    },
    {
      header: 'Setting Guidelines:',
      items: [
        '20-30 pts: Aggressive (required signals only)',
        '40-60 pts: Balanced (required + some optional)',
        '70+ pts: Conservative (require most optionals)',
      ],
    },
    {
      header: 'Tuning loop:',
      items: [
        'Too many trades? Raise confluence.',
        'Too few trades? Lower confluence.',
        "Check the strategy's signal distribution.",
      ],
    },
  ],
};

export const TT_HOLD_DURATION: TooltipContent = {
  title: 'Hold Duration',
  body: 'Min/Max bars a position must stay open before exit logic can fire or auto-close kicks in.',
  sections: [
    {
      header: 'Use cases:',
      items: [
        'Filter same-bar noise exits (min)',
        'Recycle stuck positions (max)',
        'Enforce minimum holding window for ML labels',
      ],
    },
  ],
};

export const TT_MIN_BARS_HELD: TooltipContent = {
  title: 'Minimum Position Hold Time',
  body: 'Minimum number of bars a position must remain open before any exit signal can fire.',
  sections: [
    {
      header: 'Purpose:',
      items: [
        'Filters out same-bar noise exits',
        'Lets the entry thesis develop',
        'Forces minimum trade duration for ML labels',
      ],
    },
    {
      header: 'Guidelines (15m timeframe):',
      items: [
        '0-5 bars: Scalping — no enforced floor',
        '5-15 bars: Day trading',
        '20+ bars: Swing-style holds',
      ],
    },
  ],
};

export const TT_MAX_BARS_HELD: TooltipContent = {
  title: 'Maximum Position Hold Time',
  body: 'Auto-close trades that exceed this duration.',
  sections: [
    {
      header: 'Purpose:',
      items: [
        'Prevents stuck positions',
        'Forces capital recycling',
        'Limits opportunity cost',
      ],
    },
    {
      header: 'Examples (15m timeframe):',
      items: [
        '50 bars: 12.5 hours max hold',
        '200 bars: 50 hours (~2 days)',
        '500 bars: 125 hours (~5 days)',
      ],
    },
    {
      header: 'Guidelines:',
      items: [
        'Scalping: 20-100 bars',
        'Day trading: 100-300 bars',
        'Swing: 300+ bars',
      ],
    },
  ],
};

export const TT_RUN_TEST: TooltipContent = {
  title: 'Run Test',
  body: 'Run the walk-forward backtest with the current configuration.',
};

export const TT_PAUSE: TooltipContent = {
  title: 'Pause',
  body: 'Pause the currently running backtest.',
};

export const TT_STOP: TooltipContent = {
  title: 'Stop',
  body: 'Stop and cancel the currently running backtest.',
};

export const TT_CONFIG_DISCOVERY: TooltipContent = {
  title: 'Config Discovery',
  body: 'Runs N permutations of strategy parameters and shows ranked results.',
  sections: [
    {
      header: 'Metrics per run:',
      items: [
        'Total PnL, Win Rate, Sharpe Ratio',
        'Exit Type Distribution (TP1/TP2/TP3/SL/Time)',
        'Avg PnL per Trade, Avg Bars Held',
      ],
    },
    {
      header: 'Badges:',
      items: [
        'Most Profitable',
        'Best Sharpe',
        'Most Frequent',
      ],
    },
    { items: ['Uses cached bars for speed (no repeated data loading).'] },
  ],
};

export const TT_VIEW_LIVE_RESULTS: TooltipContent = {
  title: 'View Live Results',
  body: 'View the detailed results from the most recently completed backtest.',
};

export const TT_CANCEL: TooltipContent = {
  title: 'Close',
  body: 'Close this dialog without running a backtest. Your configuration is preserved for the next open.',
};
