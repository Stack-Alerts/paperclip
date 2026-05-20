/**
 * Tooltip Registry — BTCAAAAA-27654
 *
 * Central registry of all tooltips used across the BTC Trade Engine UI modules.
 * Ported from the PyQt5 implementations where tooltips were inline in widget creation.
 *
 * Structure: module → component → field → { label, description }
 */

export interface Tooltip {
  id: string;
  label: string;
  description: string;
  category?: string;
}

export interface TooltipModule {
  [fieldId: string]: Tooltip;
}

export interface TooltipRegistry {
  [moduleId: string]: TooltipModule;
}

// ---------------------------------------------------------------------------
// Backtest Module Tooltips
// Sourced from: src/strategy_builder/ui/backtest_config_panel.py
// ---------------------------------------------------------------------------
const backtestTooltips: TooltipModule = {
  'lookback-days': {
    id: 'backtest.lookback-days',
    label: 'Lookback Days',
    description:
      'Number of historical calendar days to include in the backtest. ' +
      '180 days is the recommended minimum for statistical significance.',
    category: 'backtest.config',
  },
  'training-window': {
    id: 'backtest.training-window',
    label: 'Training Window',
    description:
      'Number of days used for in-sample training before the out-of-sample window. ' +
      'Must be at least 14 days.',
    category: 'backtest.config',
  },
  'mode-historical': {
    id: 'backtest.mode-historical',
    label: 'Mode 1: Historical Walkforward',
    description:
      'Runs the backtest from the lookback start date up to the current date. ' +
      'Produces a fixed performance snapshot.',
    category: 'backtest.config',
  },
  'mode-live': {
    id: 'backtest.mode-live',
    label: 'Mode 2: Live Continuation',
    description:
      'Starts from 180 days back, reaches the current date, then continues processing ' +
      'new candles as they arrive. Useful for validating real-time signal generation.',
    category: 'backtest.config',
  },
  'strategy-id': {
    id: 'backtest.strategy-id',
    label: 'Strategy',
    description:
      'Select the strategy configuration to run in this backtest. ' +
      'All blocks and parameters must be valid before running.',
    category: 'backtest.config',
  },
  'instrument-id': {
    id: 'backtest.instrument-id',
    label: 'Instrument',
    description:
      'Trading instrument identifier (e.g. BTCUSDT). ' +
      'Historical data for this instrument must be available in the data store.',
    category: 'backtest.config',
  },
  'run-button': {
    id: 'backtest.run-button',
    label: 'Run Test',
    description:
      'Starts the backtest. Automatic signal calibration is performed before each run. ' +
      'The run cannot be started if data is missing or the strategy configuration is invalid.',
    category: 'backtest.control',
  },
  'stop-button': {
    id: 'backtest.stop-button',
    label: 'Stop',
    description:
      'Gracefully stops the in-progress backtest. ' +
      'Partial results up to the last completed bar will be preserved.',
    category: 'backtest.control',
  },
  'candle-progress': {
    id: 'backtest.candle-progress',
    label: 'Candle Progress',
    description: 'Number of candles processed vs. total candles in the backtest window.',
    category: 'backtest.progress',
  },
  'trade-progress': {
    id: 'backtest.trade-progress',
    label: 'Trade Progress',
    description: 'Number of trades executed so far vs. expected total trades.',
    category: 'backtest.progress',
  },
  'win-rate': {
    id: 'backtest.result.win-rate',
    label: 'Win Rate',
    description:
      'Percentage of closed trades that were profitable. ' +
      'Values above 50% indicate a positive edge.',
    category: 'backtest.results',
  },
  'profit-factor': {
    id: 'backtest.result.profit-factor',
    label: 'Profit Factor',
    description:
      'Ratio of gross profit to gross loss. ' +
      'A value above 1.5 is generally considered acceptable; above 2.0 is strong.',
    category: 'backtest.results',
  },
  'max-drawdown': {
    id: 'backtest.result.max-drawdown',
    label: 'Max Drawdown',
    description:
      'Largest peak-to-trough decline in portfolio value expressed as a percentage. ' +
      'Lower is better; values above -20% warrant caution.',
    category: 'backtest.results',
  },
  'sharpe-ratio': {
    id: 'backtest.result.sharpe-ratio',
    label: 'Sharpe Ratio',
    description:
      'Risk-adjusted return. Sharpe > 1.0 is acceptable; > 2.0 is excellent.',
    category: 'backtest.results',
  },
};

// ---------------------------------------------------------------------------
// Data Management Module Tooltips
// Sourced from: src/strategy_builder/ui/data_verify_dialog.py, data_update_modal.py
// ---------------------------------------------------------------------------
const dataManagementTooltips: TooltipModule = {
  'source-status-active': {
    id: 'data.source-status.active',
    label: 'Active',
    description:
      'This data source is healthy and up to date. No action required.',
    category: 'data.sources',
  },
  'source-status-inactive': {
    id: 'data.source-status.inactive',
    label: 'Inactive',
    description:
      'This data source is configured but not currently receiving updates. ' +
      'Check your connection and API keys.',
    category: 'data.sources',
  },
  'source-status-error': {
    id: 'data.source-status.error',
    label: 'Error',
    description:
      'This data source has encountered an error. ' +
      'Check logs for details and verify the data source configuration.',
    category: 'data.sources',
  },
  'verify-button': {
    id: 'data.verify-button',
    label: 'Verify Data Integrity',
    description:
      'Scans all configured data sources for gaps in OHLCV data. ' +
      'Gaps are classified as repairable (within 90-day Binance API horizon) ' +
      'or too old (require LakeAPI backfill).',
    category: 'data.actions',
  },
  'update-button': {
    id: 'data.update-button',
    label: 'Update',
    description:
      'Downloads the latest OHLCV bars from the Binance API for this data source. ' +
      'Only gaps within the 90-day API window can be filled this way.',
    category: 'data.actions',
  },
  'repair-button': {
    id: 'data.repair-button',
    label: 'Repair Gaps',
    description:
      'Fetches missing OHLCV bars from the Binance API to fill repairable gaps. ' +
      'Gaps older than 90 days cannot be repaired from Binance and need a LakeAPI backfill.',
    category: 'data.actions',
  },
  'gap-repairable': {
    id: 'data.gap.repairable',
    label: 'Repairable Gap',
    description:
      'This gap falls within the 90-day Binance API window and can be filled automatically. ' +
      'Click "Repair Gaps" to fetch the missing bars.',
    category: 'data.gaps',
  },
  'gap-too-old': {
    id: 'data.gap.too-old',
    label: 'Too Old',
    description:
      'This gap predates the 90-day Binance API horizon. ' +
      'A LakeAPI historical backfill is required to fill this gap.',
    category: 'data.gaps',
  },
};

// ---------------------------------------------------------------------------
// Log Viewer Module Tooltips
// Sourced from: src/strategy_builder/ui/log_viewer_window.py
// ---------------------------------------------------------------------------
const logViewerTooltips: TooltipModule = {
  'log-search': {
    id: 'logs.search',
    label: 'Search Logs',
    description:
      'Filter log entries by message text or source module name. ' +
      'The search is case-insensitive and matches partial strings.',
    category: 'logs.filters',
  },
  'log-level-debug': {
    id: 'logs.level.debug',
    label: 'DEBUG',
    description:
      'Highly detailed diagnostic messages. ' +
      'Generally only useful when tracing a specific code path.',
    category: 'logs.levels',
  },
  'log-level-info': {
    id: 'logs.level.info',
    label: 'INFO',
    description:
      'Normal operational messages. ' +
      'Shows startup, shutdown, and key lifecycle events.',
    category: 'logs.levels',
  },
  'log-level-warning': {
    id: 'logs.level.warning',
    label: 'WARNING',
    description:
      'Something unexpected happened but the system can continue. ' +
      'Warnings should be reviewed but do not stop execution.',
    category: 'logs.levels',
  },
  'log-level-error': {
    id: 'logs.level.error',
    label: 'ERROR',
    description:
      'A significant error occurred. ' +
      'The system will attempt to recover but manual review is recommended.',
    category: 'logs.levels',
  },
  'log-level-critical': {
    id: 'logs.level.critical',
    label: 'CRITICAL',
    description:
      'A fatal error occurred that may have stopped execution. ' +
      'Immediate investigation is required.',
    category: 'logs.levels',
  },
  'auto-scroll': {
    id: 'logs.auto-scroll',
    label: 'Auto-scroll to Latest',
    description:
      'When enabled, the log viewer will automatically scroll to the newest entry ' +
      'as logs are received. Disable to inspect older entries without losing your place.',
    category: 'logs.controls',
  },
  'clear-logs': {
    id: 'logs.clear',
    label: 'Clear',
    description: 'Clears all displayed log entries. Does not delete log files on disk.',
    category: 'logs.controls',
  },
  'export-logs': {
    id: 'logs.export',
    label: 'Export',
    description:
      'Exports the currently visible log entries to a text file. ' +
      'Filtered logs (by level or search term) are exported as-is.',
    category: 'logs.controls',
  },
};

// ---------------------------------------------------------------------------
// Settings Module Tooltips
// Sourced from: src/strategy_builder/ui/settings_dialog.py
// ---------------------------------------------------------------------------
const settingsTooltips: TooltipModule = {
  'theme': {
    id: 'settings.general.theme',
    label: 'Theme',
    description: 'Select the application colour theme. Dark is recommended for extended sessions.',
    category: 'settings.general',
  },
  'auto-save': {
    id: 'settings.general.auto-save',
    label: 'Auto Save',
    description:
      'Automatically save changes to settings, strategy configurations, and backtest runs ' +
      'without requiring a manual save action.',
    category: 'settings.general',
  },
  'nautilus-api-url': {
    id: 'settings.api.nautilus-url',
    label: 'NautilusTrader API URL',
    description:
      'Base URL of the NautilusTrader REST API server. ' +
      'Example: http://localhost:8000. ' +
      'The trailing slash must be omitted.',
    category: 'settings.api',
  },
  'api-timeout': {
    id: 'settings.api.timeout',
    label: 'API Timeout (seconds)',
    description:
      'Maximum time in seconds to wait for a NautilusTrader API response ' +
      'before the request is considered failed. Default is 30 seconds.',
    category: 'settings.api',
  },
  'save-button': {
    id: 'settings.save',
    label: 'Save Settings',
    description:
      'Persists all modified settings to disk. ' +
      'Changes take effect immediately without requiring an application restart.',
    category: 'settings.actions',
  },
  'reset-button': {
    id: 'settings.reset',
    label: 'Reset',
    description: 'Reverts all unsaved changes to the last saved values.',
    category: 'settings.actions',
  },
};

// ---------------------------------------------------------------------------
// Strategy Browser Module Tooltips
// Sourced from: src/strategy_builder/ui/strategy_browser_dialog.py
// ---------------------------------------------------------------------------
const strategyBrowserTooltips: TooltipModule = {
  'search': {
    id: 'strategy-browser.search',
    label: 'Search Strategies',
    description: 'Filter strategies by name — updates results as you type',
    category: 'strategy-browser.filters',
  },
  'type-filter': {
    id: 'strategy-browser.type-filter',
    label: 'Strategy Type Filter',
    description: 'Filter strategies by market direction — Bullish (long) or Bearish (short)',
    category: 'strategy-browser.filters',
  },
  'delete': {
    id: 'strategy-browser.delete',
    label: 'Delete Strategy',
    description: 'Permanently delete the selected strategy and all its versions from the database',
    category: 'strategy-browser.actions',
  },
  'duplicate': {
    id: 'strategy-browser.duplicate',
    label: 'Duplicate Strategy',
    description: 'Create a copy of the selected strategy as a new entry',
    category: 'strategy-browser.actions',
  },
  'export-json': {
    id: 'strategy-browser.export-json',
    label: 'Export to JSON',
    description: "Export the selected strategy's configuration to a JSON file",
    category: 'strategy-browser.actions',
  },
  'import-json': {
    id: 'strategy-browser.import-json',
    label: 'Import from JSON',
    description: 'Import a strategy configuration from a previously exported JSON file',
    category: 'strategy-browser.actions',
  },
  'cancel': {
    id: 'strategy-browser.cancel',
    label: 'Cancel',
    description: 'Close the browser without opening or saving a strategy',
    category: 'strategy-browser.actions',
  },
  'open': {
    id: 'strategy-browser.open',
    label: 'Open',
    description: 'Open the selected strategy in the Strategy Builder',
    category: 'strategy-browser.actions',
  },
  'pop-out': {
    id: 'strategy-browser.pop-out',
    label: 'Pop Out',
    description: 'Open this browser in a separate window that can be moved to another monitor',
    category: 'strategy-browser.controls',
  },
};

// ---------------------------------------------------------------------------
// Assembled Registry
// ---------------------------------------------------------------------------
export const TOOLTIP_REGISTRY: TooltipRegistry = {
  backtest: backtestTooltips,
  'data-management': dataManagementTooltips,
  'log-viewer': logViewerTooltips,
  settings: settingsTooltips,
  'strategy-browser': strategyBrowserTooltips,
};

/**
 * Look up a tooltip by module and field ID.
 * Returns undefined if no tooltip is registered for this key.
 */
export function getTooltip(moduleId: string, fieldId: string): Tooltip | undefined {
  return TOOLTIP_REGISTRY[moduleId]?.[fieldId];
}

/**
 * Returns all tooltips for a given module (flat array).
 */
export function getModuleTooltips(moduleId: string): Tooltip[] {
  const reg = TOOLTIP_REGISTRY[moduleId];
  return reg ? Object.values(reg) : [];
}

/**
 * Returns all registered modules with their tooltip counts.
 */
export function getRegistrySummary(): Record<string, number> {
  return Object.fromEntries(
    Object.entries(TOOLTIP_REGISTRY).map(([mod, tips]) => [mod, Object.keys(tips).length])
  );
}

/**
 * Total number of registered tooltips across all modules.
 */
export function getTotalTooltipCount(): number {
  return Object.values(TOOLTIP_REGISTRY).reduce(
    (sum, mod) => sum + Object.keys(mod).length,
    0
  );
}
