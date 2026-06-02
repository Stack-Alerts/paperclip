'use client';

import { useState } from 'react';
import type { FixedIssueEntry } from '@/hooks/strategy-builder/useStrategyStore';

// "Fixed in this session" section used by the Validation surface to render
// rehydrated fix events (BTCAAAAA-33700) for the currently-loaded strategy
// version. Each row carries an Undo affordance that calls back with the
// entry's key — the store's `undoAutoFix` reverts the snapshot and marks the
// validation_history row as undone instead of deleting it, so audit trail
// is preserved (BTCAAAAA-33738 Bug 3).

export interface FixedIssuesListProps {
  entries: FixedIssueEntry[];
  onUndo: (key: string) => void;
  // Optional compact mode for the in-tab variant (the dialog header callout
  // uses the default expanded layout).
  compact?: boolean;
  defaultCollapsed?: boolean;
}

function formatAppliedAt(iso: string): string {
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString();
  } catch {
    return iso;
  }
}

export function FixedIssuesList({
  entries,
  onUndo,
  compact = false,
  defaultCollapsed = false,
}: FixedIssuesListProps) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  if (entries.length === 0) return null;

  return (
    <section
      data-testid="fixed-issues-list"
      className="rounded border-l-4"
      style={{
        border: '1px solid var(--border)',
        borderLeftColor: 'var(--accent-green)',
        borderLeftWidth: 4,
        background: 'color-mix(in srgb, var(--accent-green) 5%, var(--bg-card))',
        padding: compact ? '0.5rem 0.75rem' : '0.75rem 1rem',
      }}
    >
      <header className="flex items-center justify-between gap-2">
        <h3
          className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest"
          style={{ color: 'var(--accent-green)', letterSpacing: '0.08em' }}
        >
          <span aria-hidden="true">✓</span>
          Fixed in this session
          <span
            className="px-1.5 py-0.5 rounded text-[10px] font-bold"
            style={{
              background: 'color-mix(in srgb, var(--accent-green) 25%, var(--bg-panel))',
              color: 'var(--accent-green)',
            }}
          >
            {entries.length}
          </span>
        </h3>
        <button
          type="button"
          onClick={() => setCollapsed((v) => !v)}
          aria-expanded={!collapsed}
          aria-controls="fixed-issues-list-body"
          className="text-xs transition-colors"
          style={{ color: 'var(--text-muted)' }}
        >
          {collapsed ? 'Show' : 'Hide'}
        </button>
      </header>
      {!collapsed && (
        <ul id="fixed-issues-list-body" className="mt-2 space-y-1.5" role="list">
          {entries.map((entry) => (
            <li
              key={entry.key}
              className="flex items-start gap-2 rounded px-2 py-1.5"
              style={{ background: 'var(--bg-panel)', border: '1px solid var(--border)' }}
            >
              <span
                aria-hidden="true"
                className="flex-shrink-0 font-bold"
                style={{ color: 'var(--accent-green)' }}
              >
                ✓
              </span>
              <div className="flex-1 min-w-0">
                <div
                  className="text-xs font-semibold truncate"
                  style={{ color: 'var(--text-secondary)' }}
                  title={entry.issue.rule_name}
                >
                  {entry.issue.rule_name || entry.issue.rule_id}
                </div>
                <div
                  className="text-[11px] flex flex-wrap items-baseline gap-x-2"
                  style={{ color: 'var(--text-muted)' }}
                >
                  <span className="font-mono">{entry.issue.rule_id}</span>
                  {entry.issue.location && (
                    <span className="font-mono truncate" title={entry.issue.location}>
                      {entry.issue.location}
                    </span>
                  )}
                  <span>Applied {formatAppliedAt(entry.appliedAt)}</span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => onUndo(entry.key)}
                aria-label={`Undo fix for ${entry.issue.rule_name || entry.issue.rule_id}`}
                className="flex-shrink-0 px-2 py-1 rounded text-xs font-semibold transition-colors"
                style={{
                  background: 'color-mix(in srgb, var(--accent-blue) 28%, var(--bg-panel))',
                  color: 'var(--accent-blue)',
                  border: '1px solid var(--accent-blue)',
                }}
              >
                ↶ Undo
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default FixedIssuesList;
