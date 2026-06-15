'use client';

import React, { useState, useEffect } from 'react';
import { useAutoDataUpdate } from '@/hooks/useAutoDataUpdate';
import { parseApiTimestamp } from '@/lib/data-management/api';

function pad(n: number): string {
  return n.toString().padStart(2, '0');
}

/** Live countdown to a target Date. Returns null when target is in the past. */
function useCountdown(target: Date | null): string | null {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  if (!target) return null;
  const ms = target.getTime() - now;
  if (ms <= 0) return null;
  const totalSec = Math.floor(ms / 1000);
  const mm = Math.floor(totalSec / 60);
  const ss = totalSec % 60;
  return `${mm}:${pad(ss)}`;
}

/** Format a Date as HH:MM:SS in local time */
function fmtTime(d: Date | null): string {
  if (!d) return '—';
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

const STATUS_COLOR: Record<string, string> = {
  idle: 'var(--text-muted)',
  updating: 'var(--color-warning)',
  ok: 'var(--status-connected)',
  error: 'var(--color-bearish)',
};

const STATUS_LABEL: Record<string, string> = {
  idle: 'STARTING',
  updating: 'UPDATING',
  ok: 'LIVE',
  error: 'STALE',
};

/** Sidebar widget shown below the CONNECTED indicator.
 *
 *  Displays:
 *  - Live / Updating / Stale dot + label
 *  - Last 15m candle received time (local)
 *  - Countdown to next candle check (MM:SS)
 *  Collapses to a single dot when the sidebar is collapsed.
 */
export function SidebarDataStatus({ collapsed }: { collapsed: boolean }) {
  const { lastCandleTs, nextCheckTime, status, isUpdating } = useAutoDataUpdate();
  const countdown = useCountdown(nextCheckTime);

  const color = STATUS_COLOR[status] ?? 'var(--text-muted)';
  const label = isUpdating ? 'UPDATING' : (STATUS_LABEL[status] ?? 'STARTING');
  // When data is stale the auto-updater keeps probing for fresh candles; surface
  // that with a blinking "( probing )" suffix next to the STALE label.
  const isStale = status === 'error';

  const lastCandleDate = parseApiTimestamp(lastCandleTs);

  if (collapsed) {
    return (
      <div className="flex justify-center py-2">
        <span
          title={`Data: ${label} — Last candle ${lastCandleDate ? fmtTime(lastCandleDate) : '—'}`}
          style={{
            width: 7,
            height: 7,
            borderRadius: '50%',
            background: color,
            display: 'inline-block',
          }}
        />
      </div>
    );
  }

  return (
    <div className="px-3 py-2" style={{ borderTop: '1px solid var(--border)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
        <span
          style={{
            width: 7,
            height: 7,
            borderRadius: '50%',
            background: color,
            display: 'inline-block',
            flexShrink: 0,
          }}
        />
        <span
          style={{
            fontSize: 10,
            color,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            fontWeight: 600,
          }}
        >
          DATA {label}
          {isStale && (
            <span
              className="data-probing-blink"
              style={{ marginLeft: 4, fontWeight: 500, textTransform: 'none' }}
            >
              ( probing )
            </span>
          )}
        </span>
      </div>

      {lastCandleDate && (
        <div style={{ fontSize: 10, color: 'var(--text-muted)', paddingLeft: 13, marginBottom: 2 }}>
          last 15m: {fmtTime(lastCandleDate)}
        </div>
      )}

      {countdown !== null ? (
        <div style={{ fontSize: 10, color: 'var(--text-muted)', paddingLeft: 13 }}>
          heartbeat in:{' '}
          <span style={{ fontVariantNumeric: 'tabular-nums' }}>{countdown}</span>
        </div>
      ) : isUpdating ? (
        <div style={{ fontSize: 10, color: 'var(--color-warning)', paddingLeft: 13 }}>
          fetching…
        </div>
      ) : null}
    </div>
  );
}
