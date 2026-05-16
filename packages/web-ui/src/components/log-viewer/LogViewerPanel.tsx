'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { LogEntry, LogLevel, LogEventType } from '@/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';

const LOG_LEVEL_COLORS: Record<LogLevel, string> = {
  [LogLevel.DEBUG]: 'text-gray-500',
  [LogLevel.INFO]: 'text-blue-600',
  [LogLevel.WARNING]: 'text-yellow-600',
  [LogLevel.ERROR]: 'text-red-600',
  [LogLevel.CRITICAL]: 'text-red-900 font-bold',
};

const LOG_EVENT_COLORS: Record<LogEventType, string> = {
  [LogEventType.TRADE_OPENED]: 'text-green-600',
  [LogEventType.TRADE_CLOSED]: 'text-blue-600',
  [LogEventType.TRADE_UPDATED]: 'text-yellow-600',
  [LogEventType.POSITIONS_SNAPSHOT]: 'text-purple-600',
  [LogEventType.TRADE_NOT_FOUND]: 'text-red-600',
  [LogEventType.CONFIG_INITIALIZED]: 'text-green-600',
  [LogEventType.CONFIG_READ]: 'text-blue-600',
  [LogEventType.CONFIG_VALIDATED]: 'text-green-600',
  [LogEventType.ERROR]: 'text-red-600',
  [LogEventType.WARNING]: 'text-yellow-600',
  [LogEventType.SUCCESS]: 'text-green-600',
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
  const [filteredLogs, setFilteredLogs] = useState<LogEntry[]>(logs);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedLevels, setSelectedLevels] = useState<Set<LogLevel>>(
    new Set(Object.values(LogLevel))
  );
  const [selectedEvents, setSelectedEvents] = useState<Set<LogEventType>>(
    new Set(Object.values(LogEventType))
  );
  const [autoScroll, setAutoScroll] = useState(true);
  const logEndRef = useRef<HTMLDivElement>(null);

  // Filter logs based on search term and selected levels/events
  useEffect(() => {
    let filtered = logs;

    // Filter by log level
    filtered = filtered.filter((log) => selectedLevels.has(log.level));

    // Filter by event type
    filtered = filtered.filter((log) =>
      !log.eventType || selectedEvents.has(log.eventType)
    );

    // Filter by search term
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter((log) =>
        log.message.toLowerCase().includes(term) ||
        log.source?.toLowerCase().includes(term)
      );
    }

    setFilteredLogs(filtered);
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

  const toggleEventType = useCallback((event: LogEventType) => {
    setSelectedEvents((prev) => {
      const next = new Set(prev);
      if (next.has(event)) {
        next.delete(event);
      } else {
        next.add(event);
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
                  className={`px-3 py-1 rounded text-sm transition-colors ${
                    selectedLevels.has(level)
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
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
          <div className="bg-gray-900 rounded-lg font-mono text-sm h-96 overflow-y-auto p-3 space-y-1">
            {filteredLogs.length > 0 ? (
              <>
                {filteredLogs.map((log, idx) => (
                  <div
                    key={idx}
                    className={`whitespace-pre-wrap break-words text-gray-100 ${
                      LOG_LEVEL_COLORS[log.level] || LOG_EVENT_COLORS[log.eventType!] || ''
                    }`}
                  >
                    <span className="text-gray-500">
                      {log.timestamp.toLocaleTimeString()}
                    </span>{' '}
                    <span className="font-semibold">[{log.level}]</span>{' '}
                    {log.source && <span className="text-gray-400">({log.source})</span>}{' '}
                    {log.message}
                  </div>
                ))}
                <div ref={logEndRef} />
              </>
            ) : (
              <div className="text-gray-500 text-center py-8">No logs to display</div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default LogViewerPanel;
