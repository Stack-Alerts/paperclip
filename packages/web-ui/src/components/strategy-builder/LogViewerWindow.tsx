'use client';

import { useState, useRef, useEffect, useCallback, useMemo } from 'react';

export interface LogEntry {
  message: string;
  level: string;
  timestamp: string;
}

export interface LogViewerWindowProps {
  open: boolean;
  onClose: () => void;
  logs?: LogEntry[];
  onClear?: () => void;
}

type LogLevel = 'INFO' | 'SYSTEM' | 'WARNING' | 'ERROR' | 'TRADE_OPENED' | 'TRADE_CLOSED' | 'DEBUG';

const LEVEL_COLORS: Record<string, string> = {
  ERROR: 'var(--accent-red)',
  WARNING: 'var(--accent-orange)',
  TRADE_OPENED: 'var(--accent-green)',
  TRADE_CLOSED: 'var(--accent-teal)',
  INFO: 'var(--text-primary)',
  SYSTEM: 'var(--accent-blue)',
  DEBUG: 'var(--text-muted)',
};

const ALL_LEVELS: LogLevel[] = [
  'INFO',
  'SYSTEM',
  'WARNING',
  'ERROR',
  'TRADE_OPENED',
  'TRADE_CLOSED',
  'DEBUG',
];

const LEVEL_LABELS: Record<LogLevel, string> = {
  INFO: 'Info',
  SYSTEM: 'System',
  WARNING: 'Warning',
  ERROR: 'Error',
  TRADE_OPENED: 'Trade Opened',
  TRADE_CLOSED: 'Trade Closed',
  DEBUG: 'Debug',
};

const TABS = ['All', 'Trades', 'System', 'Errors'] as const;
type Tab = (typeof TABS)[number];

function levelColor(level: string): string {
  const normalized = level.toUpperCase().replace(/\s+/g, '_');
  return LEVEL_COLORS[normalized] ?? 'var(--text-primary)';
}

function entryMatchesTab(entry: LogEntry, tab: Tab): boolean {
  if (tab === 'All') return true;
  const lvl = entry.level.toUpperCase().replace(/\s+/g, '_');
  if (tab === 'Trades') return lvl === 'TRADE_OPENED' || lvl === 'TRADE_CLOSED';
  if (tab === 'System') return lvl === 'SYSTEM' || lvl === 'INFO' || lvl === 'DEBUG';
  if (tab === 'Errors') return lvl === 'ERROR' || lvl === 'WARNING';
  return true;
}

export function LogViewerWindow({ open, onClose, logs = [], onClear }: LogViewerWindowProps) {
  const [activeTab, setActiveTab] = useState<Tab>('All');
  const [enabledLevels, setEnabledLevels] = useState<Record<LogLevel, boolean>>(
    () => Object.fromEntries(ALL_LEVELS.map((l) => [l, true])) as Record<LogLevel, boolean>,
  );
  const [searchText, setSearchText] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const [copyFeedback, setCopyFeedback] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  const visibleEntries = useMemo(() => {
    const lower = searchText.toLowerCase();
    return logs.filter((entry) => {
      const normalized = entry.level.toUpperCase().replace(/\s+/g, '_') as LogLevel;
      if (!enabledLevels[normalized]) return false;
      if (!entryMatchesTab(entry, activeTab)) return false;
      if (lower && !entry.message.toLowerCase().includes(lower) && !entry.level.toLowerCase().includes(lower))
        return false;
      return true;
    });
  }, [logs, enabledLevels, activeTab, searchText]);

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [visibleEntries, autoScroll]);

  const toggleLevel = useCallback((level: LogLevel) => {
    setEnabledLevels((prev) => ({ ...prev, [level]: !prev[level] }));
  }, []);

  const allEnabled = ALL_LEVELS.every((l) => enabledLevels[l]);

  const toggleAll = useCallback(() => {
    const next = !allEnabled;
    setEnabledLevels(Object.fromEntries(ALL_LEVELS.map((l) => [l, next])) as Record<LogLevel, boolean>);
  }, [allEnabled]);

  const copyLog = useCallback(async () => {
    const text = visibleEntries
      .map((e) => `[${e.timestamp}] [${e.level}] ${e.message}`)
      .join('\n');
    try {
      await navigator.clipboard.writeText(text);
      setCopyFeedback(`Copied ${visibleEntries.length} lines`);
      setTimeout(() => setCopyFeedback(''), 2500);
    } catch {
      setCopyFeedback('Copy failed');
      setTimeout(() => setCopyFeedback(''), 2500);
    }
  }, [visibleEntries]);

  const clearLogs = useCallback(() => {
    setSearchText('');
    onClear?.();
  }, [onClear]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="flex flex-col w-[1100px] max-w-[95vw] h-[720px] max-h-[90vh] rounded-lg shadow-2xl overflow-hidden" style={{ background: 'var(--bg-panel)', border: '1px solid var(--border)' }}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 flex-shrink-0" style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-deep)' }}>
          <h2 className="text-sm font-semibold tracking-wide" style={{ color: 'var(--text-primary)' }}>Log Viewer</h2>
          <button
            onClick={onClose}
            className="transition-colors text-lg leading-none px-1"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-primary)'; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-secondary)'; }}
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Tabs */}
        <div className="flex flex-shrink-0" style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-deep)' }}>
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className="px-5 py-2 text-xs font-medium border-b-2 transition-colors"
              style={
                activeTab === tab
                  ? { borderColor: 'var(--accent-blue)', color: 'var(--accent-blue)', background: 'var(--bg-panel)' }
                  : { borderColor: 'transparent', color: 'var(--text-secondary)' }
              }
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Filter bar */}
        <div className="flex items-center gap-3 px-4 py-2 flex-shrink-0 flex-wrap" style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-panel)' }}>
          <span className="text-xs font-medium whitespace-nowrap" style={{ color: 'var(--text-muted)' }}>Levels:</span>
          {ALL_LEVELS.map((level) => (
            <label
              key={level}
              className="flex items-center gap-1.5 cursor-pointer select-none"
            >
              <input
                type="checkbox"
                checked={enabledLevels[level]}
                onChange={() => toggleLevel(level)}
                className="accent-blue-500"
              />
              <span className="text-xs" style={{ color: levelColor(level) }}>{LEVEL_LABELS[level]}</span>
            </label>
          ))}
          <button
            onClick={toggleAll}
            className="ml-1 px-2 py-0.5 rounded text-xs transition-colors"
            style={{ background: 'var(--bg-hover)', color: 'var(--text-primary)' }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
          >
            {allEnabled ? 'Unselect All' : 'Select All'}
          </button>
        </div>

        {/* Search + auto-scroll */}
        <div className="flex items-center gap-3 px-4 py-2 flex-shrink-0" style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-panel)' }}>
          <input
            type="text"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="Search log content..."
            className="flex-1 px-3 py-1.5 rounded text-xs focus:outline-none"
            style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
          />
          <label className="flex items-center gap-1.5 cursor-pointer select-none whitespace-nowrap">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="accent-blue-500"
            />
            <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>Auto-scroll</span>
          </label>
        </div>

        {/* Log area */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto font-mono text-xs px-4 py-3 space-y-0.5"
          style={{ background: 'var(--bg-deep)' }}
        >
          {visibleEntries.length === 0 ? (
            <p className="italic pt-4" style={{ color: 'var(--text-muted)' }}>No log entries match the current filters.</p>
          ) : (
            visibleEntries.map((entry, idx) => (
              <div key={idx} className="flex gap-2 leading-5">
                <span className="shrink-0 w-[170px] truncate" style={{ color: 'var(--text-faintest)' }}>{entry.timestamp}</span>
                <span
                  className="shrink-0 w-[110px] font-semibold uppercase"
                  style={{ color: levelColor(entry.level) }}
                >
                  {entry.level}
                </span>
                <span className="break-all" style={{ color: levelColor(entry.level) }}>{entry.message}</span>
              </div>
            ))
          )}
        </div>

        {/* Bottom bar */}
        <div className="flex items-center justify-between px-4 py-2 flex-shrink-0" style={{ borderTop: '1px solid var(--border)', background: 'var(--bg-panel)' }}>
          <div className="flex items-center gap-4 text-xs" style={{ color: 'var(--text-secondary)' }}>
            <span>
              Total: <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{logs.length}</span>
            </span>
            <span>
              Displayed: <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{visibleEntries.length}</span>
            </span>
            {copyFeedback && (
              <span className="font-medium" style={{ color: 'var(--accent-green)' }}>{copyFeedback}</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={clearLogs}
              className="px-3 py-1.5 rounded text-xs transition-colors"
              style={{ background: 'var(--bg-hover)', color: 'var(--text-primary)' }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
            >
              Clear Filter
            </button>
            <button
              onClick={copyLog}
              className="px-3 py-1.5 rounded text-xs transition-colors"
              style={{ background: 'var(--bg-hover)', color: 'var(--text-primary)' }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
            >
              Copy Log
            </button>
            <button
              onClick={onClose}
              className="px-3 py-1.5 rounded text-xs transition-colors"
              style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
