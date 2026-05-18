'use client';

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { LogEntry, LogLevel, LogEventType } from '@/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';

const LOG_LEVEL_COLORS: Record<LogLevel, Record<string, string>> = {
  [LogLevel.DEBUG]: { color: 'var(--text-muted)' },
  [LogLevel.INFO]: { color: 'var(--accent-blue)' },
  [LogLevel.WARNING]: { color: 'var(--color-warning)' },
  [LogLevel.ERROR]: { color: 'var(--color-bearish)' },
  [LogLevel.CRITICAL]: { color: 'var(--color-bearish)', fontWeight: 'bold' },
};

const LOG_EVENT_COLORS: Record<LogEventType, Record<string, string>> = {
  [LogEventType.TRADE_OPENED]: { color: 'var(--color-bullish)' },
  [LogEventType.TRADE_CLOSED]: { color: 'var(--accent-blue)' },
  [LogEventType.TRADE_UPDATED]: { color: 'var(--color-warning)' },
  [LogEventType.POSITIONS_SNAPSHOT]: { color: 'var(--accent-cyan)' },
  [LogEventType.TRADE_NOT_FOUND]: { color: 'var(--color-bearish)' },
  [LogEventType.CONFIG_INITIALIZED]: { color: 'var(--color-bullish)' },
  [LogEventType.CONFIG_READ]: { color: 'var(--accent-blue)' },
  [LogEventType.CONFIG_VALIDATED]: { color: 'var(--color-bullish)' },
  [LogEventType.ERROR]: { color: 'var(--color-bearish)' },
  [LogEventType.WARNING]: { color: 'var(--color-warning)' },
  [LogEventType.SUCCESS]: { color: 'var(--color-bullish)' },
};

export interface LogViewerPanelProps {
  logs?: LogEntry[];
  onClear?: () => void;
  onExport?: () => void;
  disabled?: boolean;
}

/**
 * LogViewerPanel - React port of PyQt5 LogViewerWindow
 *
 * Provides real-time log streaming with:
 * - Event-based filtering and color coding
 * - Search functionality
 * - Log level filtering
 * - Auto-scroll to latest logs
 * - Performance optimization for large log volumes
 */
export const LogViewerPanel: React.FC<LogViewerPanelProps> = ({
  logs = [],
  onClear,
  onExport,
  disabled = false,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedLevels, setSelectedLevels] = useState<Set<LogLevel>>(
    new Set(Object.values(LogLevel))
  );
  const [selectedEvents] = useState<Set<LogEventType>>(
    new Set(Object.values(LogEventType))
  );
  const [autoScroll, setAutoScroll] = useState(true);
  const logEndRef = useRef<HTMLDivElement>(null);

  const filteredLogs = useMemo(() => {
    let filtered = logs.filter((log) => selectedLevels.has(log.level));
    filtered = filtered.filter((log) => !log.eventType || selectedEvents.has(log.eventType));
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter((log) =>
        log.message.toLowerCase().includes(term) ||
        log.source?.toLowerCase().includes(term)
      );
    }
    return filtered;
  }, [logs, searchTerm, selectedLevels, selectedEvents]);

  // Auto-scroll to latest logs
  useEffect(() => {
    if (autoScroll && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [filteredLogs, autoScroll]);

  const toggleLogLevel = useCallback((level: LogLevel) => {
    setSelectedLevels((prev) => {
      const next = new Set(prev);
      if (next.has(level)) {
        next.delete(level);
      } else {
        next.add(level);
      }
      return next;
    });
  }, []);

  return (
    <div className="space-y-4">
      {/* Search and Filters */}
      <Card>
        <CardContent className="space-y-4 pt-6">
          <div className="space-y-2">
            <Label htmlFor="log-search">Search Logs</Label>
            <Input
              id="log-search"
              type="text"
              placeholder="Search by message or source..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              disabled={disabled}
            />
          </div>

          <div className="space-y-2">
            <Label>Log Levels</Label>
            <div className="flex flex-wrap gap-2">
              {Object.values(LogLevel).map((level) => (
                <button
                  key={level}
                  onClick={() => toggleLogLevel(level)}
                  className="px-3 py-1 rounded text-sm transition-colors"
                  style={
                    selectedLevels.has(level)
                      ? {
                          backgroundColor: 'var(--accent-blue)',
                          color: 'white',
                        }
                      : {
                          backgroundColor: 'var(--bg-panel)',
                          color: 'var(--text-secondary)',
                          border: '1px solid var(--border-default)',
                        }
                  }
                  onMouseEnter={
                    !selectedLevels.has(level)
                      ? (e) => {
                          (e.currentTarget as HTMLButtonElement).style.backgroundColor =
                            'var(--bg-panel-raised)';
                        }
                      : undefined
                  }
                  onMouseLeave={
                    !selectedLevels.has(level)
                      ? (e) => {
                          (e.currentTarget as HTMLButtonElement).style.backgroundColor =
                            'var(--bg-panel)';
                        }
                      : undefined
                  }
                  disabled={disabled}
                >
                  {level}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="auto-scroll"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              disabled={disabled}
              className="rounded"
            />
            <Label htmlFor="auto-scroll" className="mb-0">
              Auto-scroll to latest
            </Label>
          </div>

          <div className="flex gap-2 pt-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={onClear}
              disabled={disabled || logs.length === 0}
            >
              Clear
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={onExport}
              disabled={disabled || logs.length === 0}
            >
              Export
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Log Display */}
      <Card>
        <CardHeader>
          <CardTitle>
            Logs ({filteredLogs.length} / {logs.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div
            className="rounded-lg font-mono text-sm h-96 overflow-y-auto p-3 space-y-1"
            style={{ backgroundColor: 'var(--bg-panel)' }}
          >
            {filteredLogs.length > 0 ? (
              <>
                {filteredLogs.map((log, idx) => (
                  <div
                    key={idx}
                    className="whitespace-pre-wrap break-words"
                    style={{
                      color: 'var(--text-primary)',
                      ...(LOG_LEVEL_COLORS[log.level] || LOG_EVENT_COLORS[log.eventType!] || {}),
                    }}
                  >
                    <span style={{ color: 'var(--text-muted)' }}>
                      {log.timestamp.toLocaleTimeString()}
                    </span>{' '}
                    <span className="font-semibold">[{log.level}]</span>{' '}
                    {log.source && (
                      <span style={{ color: 'var(--text-secondary)' }}>
                        ({log.source})
                      </span>
                    )}{' '}
                    {log.message}
                  </div>
                ))}
                <div ref={logEndRef} />
              </>
            ) : (
              <div className="text-center py-8" style={{ color: 'var(--text-secondary)' }}>
                No logs to display
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default LogViewerPanel;
