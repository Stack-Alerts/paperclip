'use client';

import { useCallback } from 'react';
import type { AfterChangesItem, AfterChangesStatus } from './strategyAfterChangesMerge';

export interface StrategyAfterChangesRailProps {
  items: AfterChangesItem[];
  toggleOn: ReadonlySet<string>;
  onToggleCurrent: (recId: string) => void;
  onJumpToOriginEntry?: (historyEntryId: string) => void;
}

const STATUS_PILL: Record<
  AfterChangesStatus,
  { label: string; bg: string; fg: string; border: string }
> = {
  recommended: {
    label: 'recommended',
    bg: 'var(--accent-blue-soft)',
    fg: 'var(--accent-blue)',
    border: 'var(--accent-blue)',
  },
  applied: {
    label: 'applied',
    bg: 'var(--accent-green-soft)',
    fg: 'var(--accent-green-on)',
    border: 'var(--accent-green-on)',
  },
  'staged-from-prior': {
    label: 'staged-from-prior',
    bg: 'var(--accent-amber-soft, var(--bg-elevated))',
    fg: 'var(--accent-amber-on, var(--text-secondary))',
    border: 'var(--accent-amber-on, var(--border))',
  },
};

function scrollRecCardIntoView(recId: string): void {
  if (typeof document === 'undefined') return;
  const sel = `[data-testid="ai-recs-toggle-card"][data-rec-id="${CSS.escape(recId)}"]`;
  const node = document.querySelector<HTMLElement>(sel);
  if (!node) return;
  node.scrollIntoView({ behavior: 'smooth', block: 'center' });
  node.setAttribute('data-rail-flash', 'true');
  window.setTimeout(() => node.removeAttribute('data-rail-flash'), 1200);
}

function StatusPill({ status }: { status: AfterChangesStatus }) {
  const p = STATUS_PILL[status];
  return (
    <span
      className="text-[9px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded"
      style={{ background: p.bg, color: p.fg, border: `1px solid ${p.border}` }}
      data-testid="after-changes-status-pill"
      data-status={status}
    >
      {p.label}
    </span>
  );
}

export function StrategyAfterChangesRail({
  items,
  toggleOn,
  onToggleCurrent,
  onJumpToOriginEntry,
}: StrategyAfterChangesRailProps) {
  const handleRowClick = useCallback((item: AfterChangesItem) => {
    if (item.carriedOver) return;
    scrollRecCardIntoView(item.recId);
  }, []);

  return (
    <aside
      data-testid="strategy-after-changes-rail"
      aria-label="Strategy after changes"
      className="rounded flex flex-col gap-2 p-3"
      style={{
        width: 300,
        flex: '0 0 300px',
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        alignSelf: 'flex-start',
      }}
    >
      <p
        className="text-xs font-semibold uppercase tracking-wide"
        style={{ color: 'var(--text-muted)' }}
      >
        Strategy after changes
      </p>

      {items.length === 0 ? (
        <p
          className="text-[11px]"
          style={{ color: 'var(--text-faint)' }}
          data-testid="after-changes-empty"
        >
          No recommendations or staged items yet for this strategy.
        </p>
      ) : (
        <ul className="flex flex-col gap-1.5">
          {items.map((item) => {
            const isOn = !item.carriedOver && toggleOn.has(item.recId);
            return (
              <li
                key={item.key}
                data-testid="after-changes-row"
                data-status={item.status}
                data-rec-id={item.recId}
                className="rounded p-2 flex flex-col gap-1"
                style={{
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                }}
              >
                <div className="flex items-center justify-between gap-2">
                  <button
                    type="button"
                    onClick={() => handleRowClick(item)}
                    disabled={item.carriedOver}
                    title={
                      item.carriedOver
                        ? 'Staged from a prior session — no matching card today.'
                        : 'Scroll the matching recommendation card into view.'
                    }
                    className="text-[11px] font-semibold text-left truncate flex-1"
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-secondary)',
                      cursor: item.carriedOver ? 'default' : 'pointer',
                      padding: 0,
                    }}
                    data-testid="after-changes-title"
                  >
                    {item.title}
                  </button>
                  <StatusPill status={item.status} />
                </div>

                <div className="flex items-center justify-between gap-2">
                  {item.carriedOver ? (
                    <button
                      type="button"
                      onClick={() => {
                        if (item.originHistoryEntryId && onJumpToOriginEntry) {
                          onJumpToOriginEntry(item.originHistoryEntryId);
                        }
                      }}
                      disabled={!item.originHistoryEntryId || !onJumpToOriginEntry}
                      className="text-[10px] underline"
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--accent-blue)',
                        cursor: onJumpToOriginEntry ? 'pointer' : 'default',
                        padding: 0,
                      }}
                      data-testid="after-changes-carried-over-link"
                      title="Open the originating analysis in History."
                    >
                      carried over · view analysis
                    </button>
                  ) : (
                    <span />
                  )}

                  {!item.carriedOver && (
                    <label
                      className="flex items-center gap-1 text-[10px] cursor-pointer"
                      style={{ color: 'var(--text-muted)' }}
                      title={isOn ? 'Toggle off — local rollback.' : 'Toggle on — apply this recommendation.'}
                    >
                      <input
                        type="checkbox"
                        checked={isOn}
                        onChange={() => onToggleCurrent(item.recId)}
                        data-testid="after-changes-toggle"
                        data-rec-id={item.recId}
                        style={{ accentColor: 'var(--accent-blue)' }}
                      />
                      {isOn ? 'ON' : 'OFF'}
                    </label>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </aside>
  );
}
