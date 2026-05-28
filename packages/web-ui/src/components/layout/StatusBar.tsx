'use client';

import React, { useMemo, useState, useEffect } from 'react';
import { useStatus } from '@/contexts/StatusContext';
import { useStatusSettings } from '@/contexts/StatusContext';
import { statusBus } from '@/lib/status/StatusBus';

export function StatusBar() {
  const entries = useStatus();
  const { settings } = useStatusSettings();
  const [countdowns, setCountdowns] = useState<Record<string, number>>({});

  useEffect(() => {
    if (!settings.tickerMode) return;

    const interval = setInterval(() => {
      setCountdowns(prev => {
        const updated = { ...prev };
        let hasChanges = false;
        const now = Date.now();

        entries.forEach(entry => {
          if (entry.pinned && entry.expiresAt) {
            const remaining = Math.max(0, entry.expiresAt - now);
            if (updated[entry.id] !== remaining) {
              updated[entry.id] = remaining;
              hasChanges = true;
            }
          }
        });

        return hasChanges ? updated : prev;
      });
    }, 100);

    return () => clearInterval(interval);
  }, [settings.tickerMode, entries]);

  const visibleEntries = useMemo(() => {
    if (!settings.tickerMode) {
      if (entries.length === 0) return [];
      return [entries[entries.length - 1]];
    }

    const active = entries.filter(e => !e.dismissed);
    const sorted = [...active].sort((a, b) => {
      if (a.pinned && !b.pinned) return -1;
      if (!a.pinned && b.pinned) return 1;
      return b.createdAt - a.createdAt;
    });

    return sorted.slice(0, settings.maxVisible);
  }, [entries, settings]);

  const overflowCount = useMemo(() => {
    if (!settings.tickerMode) return 0;
    const active = entries.filter(e => !e.dismissed);
    return Math.max(0, active.length - settings.maxVisible);
  }, [entries, settings]);

  const handleDismiss = (id: string) => {
    statusBus.emit('dismiss', { id });
  };

  const formatCountdown = (ms: number) => {
    const seconds = Math.ceil(ms / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.ceil(ms / 60000);
    return `${minutes}m`;
  };

  if (!settings.tickerMode && visibleEntries.length === 0) {
    return (
      <div className="h-6 border-t px-3 flex items-center flex-shrink-0 min-h-6" style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}>
        <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>Ready</span>
      </div>
    );
  }

  if (!settings.tickerMode) {
    const entry = visibleEntries[0];
    return (
      <div className="h-6 border-t px-3 flex items-center flex-shrink-0 min-h-6" style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}>
        <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{entry?.text ?? 'Ready'}</span>
      </div>
    );
  }

  return (
    <div className="border-t px-3 flex items-stretch flex-shrink-0 flex-col gap-1 py-1" style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)', minHeight: '24px' }}>
      {visibleEntries.map((entry, idx) => (
        <div
          key={entry.id}
          className="flex items-center justify-between gap-2 h-5 animate-fade-in"
          style={{
            animation: 'fadeIn 0.2s ease-in-out',
            animationDelay: `${idx * 50}ms`,
            opacity: 0,
            animationFillMode: 'forwards',
          }}
        >
          <div className="flex items-center gap-2 flex-1 min-w-0">
            {entry.pinned && entry.expiresAt && (
              <span
                className="text-xs flex-shrink-0"
                style={{ color: 'var(--text-tertiary)', whiteSpace: 'nowrap' }}
              >
                {formatCountdown(countdowns[entry.id] ?? (entry.expiresAt - Date.now()))}
              </span>
            )}
            <span className="text-xs truncate" style={{ color: 'var(--text-secondary)' }}>
              {entry.text}
            </span>
          </div>
          {!entry.pinned && (
            <button
              onClick={() => handleDismiss(entry.id)}
              className="flex-shrink-0 w-4 h-4 flex items-center justify-center hover:opacity-70 transition-opacity"
              style={{ color: 'var(--text-tertiary)' }}
              aria-label="Dismiss"
            >
              ✕
            </button>
          )}
        </div>
      ))}
      {overflowCount > 0 && (
        <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
          +{overflowCount} more
        </div>
      )}
      <style>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(-2px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
}
