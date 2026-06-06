// Thick-client parity: EVENT_PATTERNS + colors are mirrored verbatim from
// src/strategy_builder/ui/log_viewer_window.py (EVENT_PATTERNS, lines 49-95)
// and src/strategy_builder/ui/styles.py (COLORS). Audit reference:
// BTCAAAAA-34925 — Step 1 audit comment. Do not change hex values without
// updating the audit and the corresponding PyQt5 source.

export type EventKey =
  | 'TRADE_OPENED'
  | 'TRADE_CLOSED'
  | 'TRADE_UPDATED'
  | 'POSITIONS_SNAPSHOT'
  | 'TRADE_NOT_FOUND'
  | 'MULTIPLE_POSITIONS'
  | 'CONFIG_INITIALIZED'
  | 'CONFIG_READ'
  | 'CONFIG_VALIDATED'
  | 'CONFIG_MISMATCH'
  | 'CONFIG_MISSING'
  | 'STARTED'
  | 'STOPPED'
  | 'PROGRESS'
  | 'COMPLETED'
  | 'CRITICAL'
  | 'ERROR'
  | 'WARNING'
  | 'BLOCK_LOADED'
  | 'BLOCK_ADDED'
  | 'SEARCH_RESULTS'
  | 'DECISION'
  | 'CONDITION_MET'
  | 'SIGNAL_DETECTED';

export interface EventDef {
  key: EventKey;
  label: string;
  color: string;
  pattern: RegExp;
}

const make = (key: EventKey, label: string, color: string, source: string): EventDef => ({
  key,
  label,
  color,
  pattern: new RegExp(source, 'i'),
});

export const EVENT_DEFS: readonly EventDef[] = [
  make('TRADE_OPENED', '🟢 Trade Opened', '#10B981', 'TRADE OPENED|trade.*opened|Opening trade|🟢.*TRADE'),
  make('TRADE_CLOSED', '📘 Trade Closed', '#2070FF', 'TRADE CLOSED|trade.*closed|Position closed|Closing trade|😘.*TRADE'),
  make('TRADE_UPDATED', '🔄 Trade Updated', '#FFD700', 'TRADE UPDATED|trade.*updated|Update.*trade|🔄.*TRADE'),
  make('POSITIONS_SNAPSHOT', '📊 Positions', '#8B5CF6', 'POSITIONS SNAPSHOT|OPEN POSITIONS|Position.*snapshot|📊'),
  make('TRADE_NOT_FOUND', '❌ Not Found', '#C35252', 'TRADE.*NOT FOUND|Trade.*not found|❌.*TRADE'),
  make('MULTIPLE_POSITIONS', '🔀 Multi Pos', '#FF8C00', 'multiple.*position|Multiple.*open|Several.*position|🔀'),
  make('CONFIG_INITIALIZED', '✓ Config Init', '#10B981', 'Logger initialized|BlockRegistryAdapter initialized|Institutional Logger initialized'),
  make('CONFIG_READ', '📖 Config Read', '#2070FF', 'Reading|Loading|load blocks|Calling.*search'),
  make('CONFIG_VALIDATED', '✓ Validated', '#10B981', 'validated|validation.*pass|Config.*valid|Validation complete'),
  make('CONFIG_MISMATCH', '❌ Mismatch', '#C35252', 'MISMATCH|mismatch|Config.*error|Invalid.*config'),
  make('CONFIG_MISSING', '⚠ Missing', '#FF8C00', 'not found|missing|Config.*missing|Cannot find'),
  make('STARTED', '▶ Started', '#10B981', 'Starting to load|Starting'),
  make('STOPPED', '⏹ Stopped', '#9AA0A6', 'Stopped|Stopping|Shutdown|Terminated|Ending'),
  make('PROGRESS', '⏳ Progress', '#2070FF', 'Processing|Working|Running|progress'),
  make('COMPLETED', '✅ Completed', '#10B981', 'Successfully loaded|Successfully|Success|Finished'),
  make('CRITICAL', '🔴 Critical', '#C35252', 'CRITICAL|FATAL'),
  make('ERROR', '❌ Error', '#FF8C00', 'ERROR'),
  make('WARNING', '⚠ Warning', '#FFD700', 'WARNING'),
  make('BLOCK_LOADED', '📦 Block Loaded', '#8B5CF6', 'Successfully loaded \\d+ blocks|loaded.*blocks|Processing first block'),
  make('BLOCK_ADDED', '➕ Block Added', '#10B981', 'Added.*block|Block.*added|Block.*config'),
  make('SEARCH_RESULTS', '🔍 Search', '#2070FF', 'Retrieved \\d+ search results|Retrieved.*search'),
  make('DECISION', '🎯 Decision', '#FFD700', 'decision|deciding|evaluate|Decision:'),
  make('CONDITION_MET', '✓ Condition', '#10B981', 'Condition.*met|Threshold.*met|Criteria.*met'),
  make('SIGNAL_DETECTED', '📡 Signal', '#10B981', 'Signal.*detect|Pattern.*found|Signal.*found|Detected:'),
] as const;

export const EVENT_BY_KEY: Readonly<Record<EventKey, EventDef>> = Object.fromEntries(
  EVENT_DEFS.map((d) => [d.key, d]),
) as Record<EventKey, EventDef>;

// Visible-on-Backtest subset — mirrors `_update_filter_visibility` for the
// `backtest` tab (log_viewer_window.py:847-850). Web Live Output is a
// single-stream backtest surface, so this is the default visibility set.
export const BACKTEST_VISIBLE_KEYS: readonly EventKey[] = [
  'TRADE_OPENED',
  'TRADE_CLOSED',
  'TRADE_UPDATED',
  'STARTED',
  'STOPPED',
  'PROGRESS',
  'COMPLETED',
  'CRITICAL',
  'ERROR',
  'WARNING',
];

export interface EventGroup {
  title: string;
  borderColor: string;
  keys: readonly EventKey[];
}

// Visual chrome groups borrow the dominant event color from each family so
// the "structure (grouping)" callout from the board lands visually.
export const EVENT_GROUPS: readonly EventGroup[] = [
  {
    title: 'Trade Events',
    borderColor: '#10B981',
    keys: ['TRADE_OPENED', 'TRADE_CLOSED', 'TRADE_UPDATED'],
  },
  {
    title: 'Lifecycle',
    borderColor: '#2070FF',
    keys: ['STARTED', 'PROGRESS', 'COMPLETED', 'STOPPED'],
  },
  {
    title: 'Severity',
    borderColor: '#C35252',
    keys: ['CRITICAL', 'ERROR', 'WARNING'],
  },
];

// Context-line prefixes mirror _CONTEXT_PREFIXES (log_viewer_window.py:105).
const CONTEXT_PREFIXES = [
  '  ',
  '\t',
  'Location:',
  'Timestamp:',
  'Trade ID:',
  'Side:',
  'Size:',
  'Entry Price:',
  'Status:',
];

export function isContextLine(text: string): boolean {
  for (const p of CONTEXT_PREFIXES) {
    if (text.startsWith(p)) return true;
  }
  return false;
}

export function matchEvents(line: string): Set<EventKey> {
  const hits = new Set<EventKey>();
  for (const def of EVENT_DEFS) {
    if (def.pattern.test(line)) hits.add(def.key);
  }
  return hits;
}

// First-match wins so display is deterministic across renders. Iteration
// order follows EVENT_DEFS, which mirrors the PyQt5 EVENT_PATTERNS dict
// order.
export function colorForLine(line: string): string | null {
  for (const def of EVENT_DEFS) {
    if (def.pattern.test(line)) return def.color;
  }
  return null;
}
