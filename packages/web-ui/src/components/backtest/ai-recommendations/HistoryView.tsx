'use client';
import { useState } from 'react';
import { Trash2 } from 'lucide-react';
import { AiRecsHistoryEntry, AiRecsHistoryStatus } from '@/hooks/useAiRecsHistory';
import { PreviewText } from './CollapsibleSection';

const STATUS_LABELS: Record<AiRecsHistoryStatus, string> = {
  new: 'NEW',
  applied: 'APPLIED',
  dismissed: 'DISMISSED',
};

const STATUS_COLORS: Record<AiRecsHistoryStatus, { bg: string; fg: string; border: string }> = {
  new: { bg: 'var(--bg-elevated)', fg: 'var(--text-muted)', border: 'var(--border)' },
  applied: { bg: 'var(--accent-green-soft)', fg: 'var(--accent-green-on)', border: 'var(--accent-green-on)' },
  dismissed: { bg: 'var(--accent-red-soft)', fg: 'var(--accent-red-on)', border: 'var(--accent-red-on)' },
};

export function StatusBadge({ status }: { status: AiRecsHistoryStatus }) {
  const c = STATUS_COLORS[status];
  return (
    <span
      className="text-[10px] font-semibold uppercase tracking-wide rounded px-1.5 py-0.5"
      style={{ background: c.bg, color: c.fg, border: `1px solid ${c.border}` }}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}

function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    const pad = (n: number) => n.toString().padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  } catch {
    return iso;
  }
}

function HistoryCard({
  entry,
  onUpdateStatus,
  onUpdateNotes,
  onRequestDelete,
  onLoadIntoCurrent,
}: {
  entry: AiRecsHistoryEntry;
  onUpdateStatus: (id: string, status: AiRecsHistoryStatus) => void;
  onUpdateNotes: (id: string, notes: string) => void;
  onRequestDelete: (id: string) => void;
  onLoadIntoCurrent: (entry: AiRecsHistoryEntry) => void;
}) {
  const [notesDraft, setNotesDraft] = useState(entry.notes);
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className="rounded p-3 flex flex-col gap-2"
      style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <StatusBadge status={entry.status} />
          {entry.strategyName && (
            <span className="text-[10px]" style={{ color: 'var(--text-faint)' }}>
              {entry.strategyName}
            </span>
          )}
        </div>
        <span
          className="text-[10px]"
          style={{ color: 'var(--text-faint)', fontFamily: 'var(--font-mono, monospace)' }}
        >
          {formatTimestamp(entry.createdAt)}
        </span>
      </div>

      <p
        className="text-xs"
        style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono, monospace)' }}
      >
        Prompt: <span style={{ color: 'var(--text-muted)' }}>{entry.prompt}</span>
      </p>

      {entry.summary && (
        <p className="text-xs whitespace-pre-wrap" style={{ color: 'var(--text-muted)' }}>
          {entry.summary}
        </p>
      )}

      <details
        open={expanded}
        onToggle={(e) => setExpanded((e.target as HTMLDetailsElement).open)}
      >
        <summary
          className="text-[10px] cursor-pointer select-none"
          style={{ color: 'var(--text-faint)' }}
        >
          {expanded ? '− Hide details' : '+ Show details'}
        </summary>
        <div className="mt-2 flex flex-col gap-2">
          {entry.diagnosis && (
            <div>
              <p
                className="text-[10px] font-semibold uppercase tracking-wide mb-1"
                style={{ color: 'var(--text-muted)' }}
              >
                Diagnosis
              </p>
              <p className="text-xs whitespace-pre-wrap" style={{ color: 'var(--text-secondary)' }}>
                {entry.diagnosis}
              </p>
            </div>
          )}
          {entry.recommendations && (
            <div>
              <p
                className="text-[10px] font-semibold uppercase tracking-wide mb-1"
                style={{ color: 'var(--text-muted)' }}
              >
                Recommendations
              </p>
              <p className="text-xs whitespace-pre-wrap" style={{ color: 'var(--text-secondary)' }}>
                {entry.recommendations}
              </p>
            </div>
          )}
          {entry.raw && (
            <div>
              <p
                className="text-[10px] font-semibold uppercase tracking-wide mb-1"
                style={{ color: 'var(--text-muted)' }}
              >
                {entry.diagnosis || entry.recommendations ? 'Full response' : 'Model output'}
              </p>
              <PreviewText text={entry.raw} />
            </div>
          )}
        </div>
      </details>

      <div>
        <label
          className="text-[10px] font-semibold uppercase tracking-wide"
          style={{ color: 'var(--text-muted)' }}
          htmlFor={`notes-${entry.id}`}
        >
          Notes
        </label>
        <textarea
          id={`notes-${entry.id}`}
          value={notesDraft}
          onChange={(e) => setNotesDraft(e.target.value)}
          onBlur={() => {
            if (notesDraft !== entry.notes) onUpdateNotes(entry.id, notesDraft);
          }}
          placeholder="Add notes about this analysis…"
          rows={2}
          className="w-full mt-1 rounded p-2 text-xs"
          style={{
            background: 'var(--bg-elevated)',
            color: 'var(--text-secondary)',
            border: '1px solid var(--border)',
            fontFamily: 'var(--font-mono, monospace)',
            resize: 'vertical',
          }}
        />
      </div>

      <div className="flex items-center gap-2 justify-end flex-wrap">
        <button
          type="button"
          onClick={() => onLoadIntoCurrent(entry)}
          data-testid={`history-load-${entry.id}`}
          title="Load this analysis into the current view — diagnoses, recommendations, and the first rec become the active rec."
          className="px-2 py-1 rounded text-[10px] font-medium"
          style={{
            background: 'var(--accent-blue)',
            color: 'var(--text-on-accent)',
            border: '1px solid var(--accent-blue)',
            cursor: 'pointer',
          }}
        >
          Load into current analysis
        </button>
        <button
          type="button"
          onClick={() => onUpdateStatus(entry.id, 'applied')}
          disabled={entry.status === 'applied'}
          className="px-2 py-1 rounded text-[10px] font-medium"
          style={{
            background:
              entry.status === 'applied' ? 'var(--accent-green-soft)' : 'var(--bg-elevated)',
            color: entry.status === 'applied' ? 'var(--accent-green-on)' : 'var(--text-secondary)',
            border: '1px solid var(--accent-green-on)',
            cursor: entry.status === 'applied' ? 'default' : 'pointer',
            opacity: entry.status === 'applied' ? 0.7 : 1,
          }}
        >
          Mark applied
        </button>
        <button
          type="button"
          onClick={() => onUpdateStatus(entry.id, 'dismissed')}
          disabled={entry.status === 'dismissed'}
          className="px-2 py-1 rounded text-[10px] font-medium"
          style={{
            background:
              entry.status === 'dismissed' ? 'var(--accent-red-soft)' : 'var(--bg-elevated)',
            color: entry.status === 'dismissed' ? 'var(--accent-red-on)' : 'var(--text-secondary)',
            border: '1px solid var(--accent-red-on)',
            cursor: entry.status === 'dismissed' ? 'default' : 'pointer',
            opacity: entry.status === 'dismissed' ? 0.7 : 1,
          }}
        >
          Mark dismissed
        </button>
        <button
          type="button"
          onClick={() => onRequestDelete(entry.id)}
          className="px-2 py-1 rounded text-[10px] font-medium flex items-center gap-1"
          style={{
            background: 'var(--bg-elevated)',
            color: 'var(--text-muted)',
            border: '1px solid var(--border)',
            cursor: 'pointer',
          }}
          title="Delete this entry"
        >
          <Trash2 size={12} />
          Delete
        </button>
      </div>
    </div>
  );
}

// BTCAAAAA-38300 — helpers for the compact history row.
// History entries don't store a provider today (see useAiRecsHistory.ts).
// Render the strategy name when present, fall back to a stable "ai" label
// so the row never collapses to an empty second line.
function providerLabel(entry: AiRecsHistoryEntry): string {
  if (entry.strategyName && entry.strategyName.trim().length > 0) {
    return entry.strategyName;
  }
  return 'ai';
}

// BTCAAAAA-38300 — count numbered recommendations in a recommendations
// block. Matches "1." / "1)" / "  2. " patterns the AI tends to emit.
function countRecommendations(text: string): number {
  if (!text) return 0;
  const matches = text.match(/(?:^|\n)\s*\d+[.)]\s+\S/g);
  return matches ? matches.length : 0;
}

export function HistoryView({
  entries,
  hydrated,
  onUpdateStatus,
  onUpdateNotes,
  onRequestDelete,
  onRequestClearAll,
  onLoadIntoCurrent,
}: {
  entries: AiRecsHistoryEntry[];
  hydrated: boolean;
  onUpdateStatus: (id: string, status: AiRecsHistoryStatus) => void;
  onUpdateNotes: (id: string, notes: string) => void;
  onRequestDelete: (id: string) => void;
  onRequestClearAll: () => void;
  onLoadIntoCurrent: (entry: AiRecsHistoryEntry) => void;
}) {
  // BTCAAAAA-38300 — local state tracks which row is currently expanded
  // so the View/Hide button stays in sync with the HistoryCard below.
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (!hydrated) {
    return (
      <p className="text-xs" style={{ color: 'var(--text-faint)' }}>
        Loading history…
      </p>
    );
  }
  if (entries.length === 0) {
    return (
      <div
        className="rounded p-4 text-xs text-center"
        style={{
          background: 'var(--bg-card)',
          color: 'var(--text-faint)',
          border: '1px solid var(--border)',
        }}
      >
        No history yet. Run &ldquo;Approve &amp; Send to AI&rdquo; to record your first analysis.
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <p
          className="text-[10px] font-semibold uppercase tracking-wide"
          style={{ color: 'var(--text-muted)' }}
        >
          {/* BTCAAAAA-38300 — header matches BTC-37748 mockup (mockup
              05.png): "PAST ANALYSES (?N)". Count moved into the label so
              the header reads exactly like the mockup. */}
          PAST ANALYSES ({entries.length})
        </p>
        <button
          type="button"
          onClick={onRequestClearAll}
          className="px-2 py-1 rounded text-[10px] font-medium"
          style={{
            background: 'var(--bg-elevated)',
            color: 'var(--text-muted)',
            border: '1px solid var(--border)',
            cursor: 'pointer',
          }}
        >
          Clear all
        </button>
      </div>
      {entries.map((entry) => {
        const isOpen = expandedId === entry.id;
        const recCount = countRecommendations(entry.recommendations);
        const appliedCount = entry.status === 'applied' ? recCount : 0;
        return (
          <div
            key={entry.id}
            data-testid={`history-row-${entry.id}`}
            className="flex flex-col gap-1"
          >
            {/* Q7 (BTCAAAAA-38564) — compact history row matching mockup 6:
                status badge · date/time + provider · prompt (truncated) ·
                "N recs · K applied" · View (→ Current Analysis) · ⋯ Details. */}
            <div
              className="flex items-center gap-2 rounded px-2 py-1.5"
              style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border)',
              }}
            >
              <StatusBadge status={entry.status} />
              <div className="flex flex-col" style={{ minWidth: 130 }}>
                <span
                  className="text-[11px]"
                  style={{
                    color: 'var(--text-secondary)',
                    fontFamily: 'var(--font-mono, monospace)',
                  }}
                >
                  {formatTimestamp(entry.createdAt)}
                </span>
                <span className="text-[10px]" style={{ color: 'var(--text-faint)' }}>
                  {providerLabel(entry)}
                </span>
              </div>
              <span
                className="text-xs flex-1 truncate"
                style={{ color: 'var(--text-muted)' }}
                title={entry.prompt}
              >
                {entry.prompt}
              </span>
              <span
                data-testid={`history-counts-${entry.id}`}
                className="text-[11px] shrink-0"
                style={{
                  color: entry.status === 'applied' ? 'var(--accent-green-on)' : 'var(--text-faint)',
                  fontFamily: 'var(--font-mono, monospace)',
                }}
              >
                {recCount} rec{recCount === 1 ? '' : 's'} · {appliedCount} applied
              </span>
              {/* Q7: View navigates to Current Analysis with the snapshot KPIs. */}
              <button
                type="button"
                onClick={() => onLoadIntoCurrent(entry)}
                data-testid={`history-view-${entry.id}`}
                className="px-2 py-1 rounded text-[10px] font-medium shrink-0"
                style={{
                  background: 'var(--accent-blue)',
                  color: 'var(--text-on-accent)',
                  border: '1px solid var(--accent-blue)',
                  cursor: 'pointer',
                }}
                title="Load this snapshot into Current Analysis tab"
              >
                View
              </button>
              {/* Details (⋯) toggle for notes / status controls / delete. */}
              <button
                type="button"
                onClick={() => setExpandedId(isOpen ? null : entry.id)}
                data-testid={`history-details-${entry.id}`}
                className="px-2 py-1 rounded text-[10px] font-medium shrink-0"
                style={{
                  background: isOpen ? 'var(--bg-elevated)' : 'transparent',
                  color: 'var(--text-faint)',
                  border: `1px solid ${isOpen ? 'var(--border)' : 'transparent'}`,
                  cursor: 'pointer',
                }}
                title="Show notes, status controls, and delete"
              >
                {isOpen ? '−' : '⋯'}
              </button>
            </div>
            {isOpen && (
              <HistoryCard
                entry={entry}
                onUpdateStatus={onUpdateStatus}
                onUpdateNotes={onUpdateNotes}
                onRequestDelete={onRequestDelete}
                onLoadIntoCurrent={onLoadIntoCurrent}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
