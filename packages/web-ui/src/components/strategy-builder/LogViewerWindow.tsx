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
  ERROR: 'text-red-400',
  WARNING: 'text-amber-400',
  TRADE_OPENED: 'text-emerald-400',
  TRADE_CLOSED: 'text-cyan-400',
  INFO: 'text-zinc-300',
  SYSTEM: 'text-blue-400',
  DEBUG: 'text-zinc-500',
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
  return LEVEL_COLORS[normalized] ?? 'text-zinc-300';
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
      <div className="flex flex-col w-[1100px] max-w-[95vw] h-[720px] max-h-[90vh] bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-700 bg-zinc-950 flex-shrink-0">
          <h2 className="text-sm font-semibold text-zinc-100 tracking-wide">Log Viewer</h2>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-zinc-100 transition-colors text-lg leading-none px-1"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-zinc-700 bg-zinc-950 flex-shrink-0">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-5 py-2 text-xs font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? 'border-blue-500 text-blue-400 bg-zinc-900'
                  : 'border-transparent text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Filter bar */}
        <div className="flex items-center gap-3 px-4 py-2 border-b border-zinc-700 bg-zinc-900 flex-shrink-0 flex-wrap">
          <span className="text-xs text-zinc-500 font-medium whitespace-nowrap">Levels:</span>
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
              <span className={`text-xs ${levelColor(level)}`}>{LEVEL_LABELS[level]}</span>
            </label>
          ))}
          <button
            onClick={toggleAll}
            className="ml-1 px-2 py-0.5 rounded bg-zinc-700 hover:bg-zinc-600 text-xs text-zinc-200 transition-colors"
          >
            {allEnabled ? 'Unselect All' : 'Select All'}
          </button>
        </div>

        {/* Search + auto-scroll */}
        <div className="flex items-center gap-3 px-4 py-2 border-b border-zinc-700 bg-zinc-900 flex-shrink-0">
          <input
            type="text"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="Search log content..."
            className="flex-1 px-3 py-1.5 rounded bg-zinc-800 border border-zinc-700 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-zinc-500"
          />
          <label className="flex items-center gap-1.5 cursor-pointer select-none whitespace-nowrap">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="accent-blue-500"
            />
            <span className="text-xs text-zinc-400">Auto-scroll</span>
          </label>
        </div>

        {/* Log area */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto font-mono text-xs bg-zinc-950 px-4 py-3 space-y-0.5"
        >
          {visibleEntries.length === 0 ? (
            <p className="text-zinc-500 italic pt-4">No log entries match the current filters.</p>
          ) : (
            visibleEntries.map((entry, idx) => (
              <div key={idx} className="flex gap-2 leading-5">
                <span className="text-zinc-600 shrink-0 w-[170px] truncate">{entry.timestamp}</span>
                <span
                  className={`shrink-0 w-[110px] font-semibold uppercase ${levelColor(entry.level)}`}
                >
                  {entry.level}
                </span>
                <span className={`break-all ${levelColor(entry.level)}`}>{entry.message}</span>
              </div>
            ))
          )}
        </div>

        {/* Bottom bar */}
        <div className="flex items-center justify-between px-4 py-2 border-t border-zinc-700 bg-zinc-900 flex-shrink-0">
          <div className="flex items-center gap-4 text-xs text-zinc-400">
            <span>
              Total: <span className="text-zinc-200 font-semibold">{logs.length}</span>
            </span>
            <span>
              Displayed: <span className="text-zinc-200 font-semibold">{visibleEntries.length}</span>
            </span>
            {copyFeedback && (
              <span className="text-emerald-400 font-medium">{copyFeedback}</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={clearLogs}
              className="px-3 py-1.5 rounded bg-zinc-700 hover:bg-zinc-600 text-xs text-zinc-200 transition-colors"
            >
              Clear Filter
            </button>
            <button
              onClick={copyLog}
              className="px-3 py-1.5 rounded bg-zinc-700 hover:bg-zinc-600 text-xs text-zinc-200 transition-colors"
            >
              Copy Log
            </button>
            <button
              onClick={onClose}
              className="px-3 py-1.5 rounded bg-zinc-800 hover:bg-zinc-700 border border-zinc-600 text-xs text-zinc-300 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
