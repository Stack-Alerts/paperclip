'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { DataUpdateModal } from '@/components/strategy-builder/DataUpdateModal';
import type { DataGapCheckResult } from '@/components/strategy-builder/DataUpdateModal';
import {
  fetchDataStatus,
  fetchDataGapCheck,
  triggerDataUpdate,
  runDataVerify,
  runDataRepair,
  runBulkBackfill,
  formatLocalShort,
  parseApiTimestamp,
} from '@/lib/data-management/api';
import type { DataStatusResponse, TimeframeVerifyResult, TimeframeFreshness } from '@/lib/data-management/api';
import { WindowBreadcrumb } from '@/components/shared/WindowBreadcrumb';

// The backend uses a fixed 90 000 s (25 h) threshold for the 1d timeframe,
// which flags the last *closed* daily candle as stale once it's past 01:00 UTC
// even though there is no gap (today's in-flight candle hasn't closed yet).
// This function replaces the backend flag with an interval-aware computation:
// a bar is stale only when its open-time predates the expected last closed candle.
function computeActualStale(tf: string, f: TimeframeFreshness): boolean {
  if (!f.lastBarTs || f.ageSeconds === null) return true;
  const intervalSeconds: Record<string, number> = { '15m': 900, '1h': 3600, '1d': 86400 };
  const interval = intervalSeconds[tf];
  if (interval === undefined) return f.stale;
  const nowSec = Date.now() / 1000;
  // Expected open-time of the last fully-closed candle:
  // floor(now / interval) * interval - interval
  const expectedLastClosedOpen = Math.floor(nowSec / interval) * interval - interval;
  const d = parseApiTimestamp(f.lastBarTs);
  if (!d) return true;
  return d.getTime() / 1000 < expectedLastClosedOpen;
}

// Detect the "data source archive lag" pattern: the freshness card is stale AND
// the last bar timestamp is exactly the prior-day 00:00:00Z (i.e. the daily
// archive's last bar, not a real 15m/1h close). This is the tell that the
// `/data/update` updater is sourcing from the LakeAPI daily archive and not
// falling through to Binance REST for the trailing intraday window — the
// underlying data-pipeline bug tracked separately. Surfacing it in the UI
// explains the "Update Data → success → no change" loop to the user.
function isArchiveLagged(tf: string, f: TimeframeFreshness): boolean {
  if (tf === '1d') return false; // 1d bars are legitimately anchored to 00:00Z
  if (!f.lastBarTs) return false;
  const d = parseApiTimestamp(f.lastBarTs);
  if (!d) return false;
  // Must be on a UTC midnight boundary
  if (d.getUTCHours() !== 0 || d.getUTCMinutes() !== 0 || d.getUTCSeconds() !== 0) return false;
  // Must be a prior UTC day (not today's midnight, which is a normal in-flight anchor)
  const todayUtc = new Date();
  const todayMidnightUtc = Date.UTC(
    todayUtc.getUTCFullYear(), todayUtc.getUTCMonth(), todayUtc.getUTCDate(), 0, 0, 0,
  );
  return d.getTime() < todayMidnightUtc;
}

function formatAge(seconds: number | null): string {
  if (seconds === null) return '—';
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${Math.round(seconds / 3600)}h`;
}

function StatusDot({ stale }: { stale: boolean }) {
  return (
    <span
      className="inline-block w-2 h-2 rounded-full mr-2"
      style={{ background: stale ? 'var(--color-bearish)' : 'var(--accent-green)' }}
    />
  );
}

function NextCandleCountdown({ timeframe, lastCandleTs }: { timeframe: string; lastCandleTs: string | null }) {
  const [now, setNow] = React.useState(() => Date.now());
  React.useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  if (!lastCandleTs) return <>—</>;
  const minutes: Record<string, number> = { '1m': 1, '5m': 5, '15m': 15, '30m': 30, '1h': 60, '4h': 240, '1d': 1440 };
  const m = minutes[timeframe] ?? 15;
  const intervalMs = m * 60_000;
  const lastMs = new Date(lastCandleTs.endsWith('Z') || /[+-]\d{2}:?\d{2}$/.test(lastCandleTs) ? lastCandleTs : lastCandleTs + 'Z').getTime();
  const nominalCloseMs = lastMs + intervalMs;
  // The status row only refreshes every 60s, so lastCandleTs lags the wall clock
  // by up to a full poll interval. Roll the close boundary forward so the display
  // counts down to the *next* close instead of freezing on a bare "closing…".
  const overshootMs = now - nominalCloseMs;
  const rolledIntervals = overshootMs > 0 ? Math.floor(overshootMs / intervalMs) + 1 : 0;
  const closesAt = nominalCloseMs + rolledIntervals * intervalMs;
  const remainingMs = Math.max(0, closesAt - now);
  const totalSec = Math.floor(remainingMs / 1000);
  const hh = Math.floor(totalSec / 3600);
  const mm = Math.floor((totalSec % 3600) / 60);
  const ss = totalSec % 60;
  const pad = (n: number) => n.toString().padStart(2, '0');
  const countdown = hh > 0 ? `${hh}:${pad(mm)}:${pad(ss)}` : `${mm}:${pad(ss)}`;
  // While the shown bar has passed its nominal close (data refresh pending), label
  // it as closing but keep the live countdown to the next close visible.
  return <>{rolledIntervals > 0 ? `closing… next close: ${countdown}` : `next close: ${countdown}`}</>;
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    complete: 'var(--accent-green)',
    gap: 'var(--color-bearish)',
    missing: 'var(--color-bearish)',
    error: 'var(--color-warning)',
  };
  const labels: Record<string, string> = {
    complete: 'up-to-date',
    gap: 'gap',
    missing: 'missing',
    error: 'error',
  };
  return (
    <span
      className="text-xs px-1.5 py-0.5 rounded font-medium uppercase"
      style={{
        background: 'var(--bg-panel-raised)',
        color: colors[status] ?? 'var(--text-muted)',
        border: `1px solid ${colors[status] ?? 'var(--border-subtle)'}`,
      }}
    >
      {labels[status] ?? status}
    </span>
  );
}

export default function MarketDataPage() {
  const [status, setStatus] = useState<DataStatusResponse | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);

  const [showUpdateModal, setShowUpdateModal] = useState(false);
  const [updateRunning, setUpdateRunning] = useState(false);
  const [updateResult, setUpdateResult] = useState<{ success: boolean; message: string } | null>(null);

  const [verifyResults, setVerifyResults] = useState<Record<string, TimeframeVerifyResult> | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [verifyError, setVerifyError] = useState<string | null>(null);

  const [repairing, setRepairing] = useState(false);
  const [repairResult, setRepairResult] = useState<string | null>(null);

  const [bulkBackfilling, setBulkBackfilling] = useState(false);
  const [bulkBackfillResult, setBulkBackfillResult] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    setLoadingStatus(true);
    setStatusError(null);
    try {
      const s = await fetchDataStatus();
      setStatus(s);
    } catch (e) {
      setStatusError(e instanceof Error ? e.message : 'Failed to load data status');
    } finally {
      setLoadingStatus(false);
    }
  }, []);

  const handleVerify = useCallback(async () => {
    setVerifying(true);
    setVerifyError(null);
    setVerifyResults(null);
    try {
      const results = await runDataVerify();
      setVerifyResults(results);
    } catch (e) {
      setVerifyError(e instanceof Error ? e.message : 'Verification failed');
    } finally {
      setVerifying(false);
    }
  }, []);

  useEffect(() => {
    loadStatus();
    handleVerify();
    const interval = setInterval(loadStatus, 60_000);
    return () => clearInterval(interval);
  }, [loadStatus, handleVerify]);

  const handleCheckGaps = useCallback(async (): Promise<DataGapCheckResult> => {
    return fetchDataGapCheck();
  }, []);

  const handleUpdate = useCallback(async (startDate: string, endDate: string) => {
    setUpdateRunning(true);
    setUpdateResult(null);
    try {
      const result = await triggerDataUpdate(startDate, endDate);
      setUpdateResult({ success: result.success, message: result.message });
      if (result.success) {
        await loadStatus();
      }
    } catch (e) {
      setUpdateResult({ success: false, message: e instanceof Error ? e.message : 'Update failed' });
    } finally {
      setUpdateRunning(false);
    }
  }, [loadStatus]);

  const handleRepair = useCallback(async (timeframe?: string) => {
    setRepairing(true);
    setRepairResult(null);
    try {
      const result = await runDataRepair(timeframe);
      setRepairResult(result.message);
      if (result.success) {
        await loadStatus();
        await handleVerify();
      }
    } catch (e) {
      setRepairResult(e instanceof Error ? e.message : 'Repair failed');
    } finally {
      setRepairing(false);
    }
  }, [loadStatus, handleVerify]);

  const handleBulkBackfill = useCallback(async () => {
    setBulkBackfilling(true);
    setBulkBackfillResult(null);
    try {
      const result = await runBulkBackfill('2024-01', '2026-04', true);
      const s = result.summary;
      setBulkBackfillResult(
        result.success
          ? `Downloaded ${s.downloaded} month/TF files (${s.totalBars.toLocaleString()} bars), skipped ${s.skipped} existing.`
          : `Finished with ${s.errors} error(s). ${result.message}`,
      );
      if (result.success) {
        await loadStatus();
        await handleVerify();
      }
    } catch (e) {
      setBulkBackfillResult(e instanceof Error ? e.message : 'Bulk backfill failed');
    } finally {
      setBulkBackfilling(false);
    }
  }, [loadStatus, handleVerify]);

  const timeframes = status?.timeframeFreshness ?? {};
  const allStatuses = status?.allStatus ?? {};
  // Recalculate staleness using interval-aware logic (backend uses a fixed 25 h
  // threshold for 1d which falsely flags the normal last-closed-daily-bar as stale).
  const anyActuallyStale = Object.entries(timeframes).some(([tf, f]) => computeActualStale(tf, f));
  const anyIssue = status?.anyGaps || anyActuallyStale;
  // Detect the LakeAPI daily-archive lag pattern: 15m and/or 1h stuck on a prior
  // day's 00:00Z bar. The presence of this pattern is what makes the "Update
  // Data → success → no change" loop reproducible.
  const archiveLaggedTfs = (['15m', '1h'] as const).filter(
    (tf) => timeframes[tf] && isArchiveLagged(tf, timeframes[tf]),
  );
  const anyArchiveLagged = archiveLaggedTfs.length > 0;

  return (
    <>
      <div
        className="flex items-center border-b px-3 py-1.5 flex-shrink-0"
        style={{ background: 'var(--bg-deep)', borderColor: 'var(--border)' }}
      >
        <WindowBreadcrumb page="Market Data" />
      </div>
      <div className="flex-1 overflow-y-auto p-6" style={{ background: 'var(--app-bg)' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>
          Market Data
        </h1>
        <div className="flex gap-2">
          <button
            onClick={loadStatus}
            disabled={loadingStatus}
            className="px-3 py-1.5 text-sm rounded transition-colors"
            style={{
              background: 'var(--bg-panel-raised)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            {loadingStatus ? 'Refreshing…' : 'Refresh'}
          </button>
          <button
            onClick={() => setShowUpdateModal(true)}
            className="px-3 py-1.5 text-sm rounded font-medium transition-colors"
            style={{
              background: anyIssue ? 'color-mix(in srgb, var(--color-bearish) 20%, #1e2a38)' : '#314255',
              color: anyIssue ? 'var(--color-bearish)' : 'var(--btn-primary-text, white)',
              border: anyIssue ? '1px solid var(--color-bearish)' : '1px solid #3d5470',
            }}
          >
            {anyIssue ? '⚠ Update Data' : 'Update Data'}
          </button>
        </div>
      </div>

      {statusError && (
        <div
          className="mb-4 p-3 rounded text-sm"
          style={{ background: 'var(--bg-panel-raised)', color: 'var(--color-bearish)', border: '1px solid var(--color-bearish)' }}
        >
          {statusError}
        </div>
      )}

      {/* Data Source Lag Notice — explains the "Update Data → success → no change" loop */}
      {anyArchiveLagged && (
        <section
          className="mb-6 p-4 rounded-lg text-sm"
          style={{
            background: 'var(--bg-panel)',
            border: '1px solid var(--color-warning)',
            color: 'var(--text-primary)',
          }}
        >
          <div className="flex items-start gap-2 mb-2">
            <span
              className="font-semibold uppercase text-xs tracking-wide mt-0.5"
              style={{ color: 'var(--color-warning)' }}
            >
              ⚠ Data source archive lag
            </span>
          </div>
          <p className="mb-2" style={{ color: 'var(--text-secondary)' }}>
            The {archiveLaggedTfs.join(' and ')} timeframe{archiveLaggedTfs.length === 1 ? '' : 's'}
            {' '}last bar{archiveLaggedTfs.length === 1 ? ' is' : 's are'} the{' '}
            <span className="font-mono">
              {timeframes[archiveLaggedTfs[0]]?.lastBarTs
                ? formatLocalShort(timeframes[archiveLaggedTfs[0]].lastBarTs)
                : '—'}
            </span>
            {' '}midnight snapshot from the LakeAPI daily archive. That archive is published
            once per UTC day, so <em>Update Data</em> re-fetches the same daily bar
            and cannot advance the trailing intraday window — which is also why{' '}
            <em>Re-run Verification</em> reports <code>totalGaps: 0</code> (no internal
            holes in the stored range) at the same time the freshness card shows{' '}
            <em>STALE</em> (the stored range ends ~1 day behind real-time).
          </p>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Trailing intraday bars exist on Binance; surfacing them requires a
            backend change to fall through from the LakeAPI archive to Binance
            REST for the trailing window. Tracked on{' '}
            <a
              href="/BTCAAAAA/issues/BTCAAAAA-36376"
              style={{ color: 'var(--accent-blue)' }}
            >
              BTCAAAAA-36376
            </a>{' '}
            (cross-scope backend fix pending board authorization).
          </p>
        </section>
      )}

      {/* OHLCV Freshness Section */}
      <section className="mb-6">
        <h2 className="text-sm font-semibold uppercase tracking-wide mb-3" style={{ color: 'var(--text-muted)' }}>
          OHLCV Freshness
        </h2>
        <div className="grid grid-cols-3 gap-3">
          {(['15m', '1h', '1d'] as const).map((tf) => {
            const f = timeframes[tf];
            const stale = f ? computeActualStale(tf, f) : true;
            return (
              <div
                key={tf}
                className="p-4 rounded-lg"
                style={{
                  background: 'var(--bg-panel)',
                  border: `1px solid ${stale ? 'var(--color-bearish)' : 'var(--border-subtle)'}`,
                }}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                    {tf}
                  </span>
                  <div className="flex items-center gap-1.5">
                    {f && isArchiveLagged(tf, f) && (
                      <span
                        className="text-[10px] px-1.5 py-0.5 rounded font-medium uppercase"
                        style={{
                          background: 'var(--bg-panel-raised)',
                          color: 'var(--color-warning)',
                          border: '1px solid var(--color-warning)',
                        }}
                        title="Last bar is the daily archive's midnight snapshot; trailing intraday bars require a backend fix."
                      >
                        archive
                      </span>
                    )}
                    <StatusDot stale={stale} />
                  </div>
                </div>
                {f ? (
                  <>
                    <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                      Last bar:{' '}
                      {f.lastBarTs ? formatLocalShort(f.lastBarTs) : '—'}
                    </p>
                    <p
                      className="text-xs mt-0.5"
                      style={{ color: stale ? 'var(--color-bearish)' : 'var(--text-muted)' }}
                    >
                      Age: {formatAge(f.ageSeconds)} {stale ? '⚠ STALE' : '✓ fresh'}
                    </p>
                  </>
                ) : (
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    {loadingStatus ? 'Loading…' : 'No data'}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* Data Source Coverage */}
      {Object.keys(allStatuses).length > 0 && (
        <section className="mb-6">
          <h2 className="text-sm font-semibold uppercase tracking-wide mb-3" style={{ color: 'var(--text-muted)' }}>
            Data Source Coverage
          </h2>
          <div
            className="rounded-lg overflow-hidden"
            style={{ border: '1px solid var(--border-subtle)', background: 'var(--bg-panel)' }}
          >
            <table className="w-full text-sm">
              <thead>
                <tr
                  style={{
                    borderBottom: '1px solid var(--border-subtle)',
                    background: 'var(--bg-panel-raised)',
                  }}
                >
                  <th className="px-4 py-2 text-left font-medium" style={{ color: 'var(--text-secondary)' }}>
                    Type
                  </th>
                  <th className="px-4 py-2 text-left font-medium" style={{ color: 'var(--text-secondary)' }}>
                    Status
                  </th>
                  <th className="px-4 py-2 text-left font-medium" style={{ color: 'var(--text-secondary)' }}>
                    Range
                  </th>
                  <th className="px-4 py-2 text-left font-medium" style={{ color: 'var(--text-secondary)' }}>
                    Gap
                  </th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(allStatuses).map(([key, val]) => (
                  <tr
                    key={key}
                    style={{ borderBottom: '1px solid var(--border-subtle)' }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLTableRowElement).style.background =
                        'var(--bg-panel-raised)';
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLTableRowElement).style.background = 'transparent';
                    }}
                  >
                    <td
                      className="px-4 py-2 font-mono text-xs"
                      style={{ color: 'var(--text-primary)' }}
                    >
                      {key}
                    </td>
                    <td className="px-4 py-2">
                      <StatusBadge status={val.status} />
                    </td>
                    <td className="px-4 py-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
                      {val.start && val.end
                        ? `${val.start.slice(0, 10)} → ${val.end.slice(0, 10)}`
                        : val.end
                          ? `Recent → ${val.end.slice(0, 10)}`
                          : '—'}
                    </td>
                    <td
                      className="px-4 py-2 text-xs"
                      style={{
                        color: val.gap_days ? 'var(--color-bearish)' : 'var(--text-muted)',
                      }}
                    >
                      {val.gap_days ? `${val.gap_days}d` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Verification */}
      <section className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <h2
            className="text-sm font-semibold uppercase tracking-wide"
            style={{ color: 'var(--text-muted)' }}
          >
            Gap Verification
          </h2>
          <button
            onClick={handleVerify}
            disabled={verifying}
            className="px-3 py-1.5 text-sm rounded font-medium transition-colors"
            style={{ background: '#314255', color: 'var(--btn-primary-text, white)', border: '1px solid #3d5470' }}
          >
            {verifying ? 'Verifying…' : 'Re-run Verification'}
          </button>
        </div>

        {verifyError && (
          <div
            className="p-3 rounded text-sm mb-3"
            style={{
              color: 'var(--color-bearish)',
              background: 'var(--bg-panel-raised)',
              border: '1px solid var(--color-bearish)',
            }}
          >
            {verifyError}
          </div>
        )}

        {repairResult && (
          <div
            className="p-3 rounded text-sm mb-3"
            style={{
              color: 'var(--text-secondary)',
              background: 'var(--bg-panel-raised)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            Repair: {repairResult}
          </div>
        )}

        {bulkBackfillResult && (
          <div
            className="p-3 rounded text-sm mb-3"
            style={{
              color: 'var(--text-secondary)',
              background: 'var(--bg-panel-raised)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            Archive backfill: {bulkBackfillResult}
          </div>
        )}

        {verifyResults ? (
          <div className="space-y-3">
            {Object.entries(verifyResults).map(([tf, r]) => (
              <div
                key={tf}
                className="p-4 rounded-lg"
                style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-subtle)' }}
              >
                <div className="flex items-center justify-between mb-2">
                  <span
                    className="font-mono font-semibold text-sm"
                    style={{ color: 'var(--text-primary)' }}
                  >
                    {tf}
                  </span>
                  <div className="flex items-center gap-3 text-xs">
                    {r.totalGaps === 0 ? (
                      <span style={{ color: 'var(--accent-green)' }}>✓ No gaps</span>
                    ) : r.repairableCount > 0 ? (
                      <>
                        <span style={{ color: 'var(--color-bearish)' }}>
                          {r.totalGaps} gap{r.totalGaps === 1 ? '' : 's'}
                        </span>
                        <button
                          onClick={() => handleRepair(tf)}
                          disabled={repairing}
                          className="px-2 py-0.5 rounded text-xs"
                          style={{ background: 'var(--accent-green)', color: '#000' }}
                        >
                          {repairing ? 'Repairing…' : `Repair ${r.repairableCount}`}
                        </button>
                      </>
                    ) : (
                      <>
                        <span style={{ color: 'var(--color-warning)' }}>
                          ⚠ {r.totalGaps} historical gap{r.totalGaps === 1 ? '' : 's'}
                        </span>
                        <button
                          onClick={handleBulkBackfill}
                          disabled={bulkBackfilling}
                          className="px-2 py-0.5 rounded text-xs"
                          style={{ background: '#3d5470', color: 'var(--text-primary)', border: '1px solid #4d6480' }}
                          title="Download historical OHLCV from Binance public archive (data.binance.vision). No API key required."
                        >
                          {bulkBackfilling ? 'Downloading…' : 'Backfill from Archive'}
                        </button>
                      </>
                    )}
                  </div>
                </div>
                <div
                  className="mb-3 p-2.5 rounded text-xs flex items-center justify-between"
                  style={{
                    background: 'var(--bg-panel-raised)',
                    border: '1px solid var(--accent-green)',
                  }}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className="inline-block w-2 h-2 rounded-full"
                      style={{
                        background: 'var(--accent-green)',
                        boxShadow: '0 0 6px var(--accent-green)',
                      }}
                    />
                    <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                      Current Candle: Open
                    </span>
                  </div>
                  <div style={{ color: 'var(--text-secondary)' }}>
                    {r.lastCandleTs ? (
                      <>
                        opened {formatLocalShort(r.lastCandleTs)} ·{' '}
                        <NextCandleCountdown timeframe={tf} lastCandleTs={r.lastCandleTs} />
                      </>
                    ) : (
                      '—'
                    )}
                  </div>
                </div>
                <div
                  className="grid grid-cols-4 gap-2 text-xs"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  <div>
                    <span className="block" style={{ color: 'var(--text-muted)' }}>
                      Total Gaps
                    </span>
                    <span
                      style={{
                        color:
                          r.totalGaps > 0 ? 'var(--color-bearish)' : 'var(--text-primary)',
                      }}
                    >
                      {r.totalGaps}
                    </span>
                  </div>
                  <div>
                    <span className="block" style={{ color: 'var(--text-muted)' }}>
                      Repairable
                    </span>
                    <span style={{ color: 'var(--accent-green)' }}>{r.repairableCount}</span>
                  </div>
                  <div>
                    <span
                      className="block"
                      style={{ color: 'var(--text-muted)' }}
                      title="Closed candles from before the 90-day Binance horizon that have not been backfilled from LakeAPI. Not the current in-flight candle."
                    >
                      Old Gaps
                    </span>
                    <span style={{ color: 'var(--color-warning)' }}>{r.tooOldCount}</span>
                    {r.tooOldCount > 0 && r.gaps?.find((g) => !g.repairable) && (
                      <span
                        className="block mt-0.5"
                        style={{ color: 'var(--text-muted)', fontSize: '10px' }}
                      >
                        {(() => {
                          const g = r.gaps.find((g) => !g.repairable);
                          if (!g) return null;
                          const s = g.gapStart?.slice(0, 10);
                          const e = g.gapEnd?.slice(0, 10);
                          return s && e ? `${s} → ${e}` : (e ?? s ?? 'historical');
                        })()}
                      </span>
                    )}
                  </div>
                  <div>
                    <span className="block" style={{ color: 'var(--text-muted)' }}>
                      Last Candle
                    </span>
                    <span>
                      {r.lastCandleTs
                        ? formatLocalShort(r.lastCandleTs)
                        : '—'}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          !verifying && (
            <div
              className="p-8 text-center rounded-lg"
              style={{
                background: 'var(--bg-panel)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-secondary)',
              }}
            >
              Click &ldquo;Run Verification&rdquo; to check for data gaps
            </div>
          )
        )}
      </section>

      {/* DataUpdateModal — mirrors the thick-client startup modal */}
      <DataUpdateModal
        open={showUpdateModal}
        onUpdate={handleUpdate}
        onSkip={() => {
          setShowUpdateModal(false);
          setUpdateResult(null);
        }}
        onCheckGaps={handleCheckGaps}
        isRunning={updateRunning}
        result={updateResult}
        autoMode={false}
      />
      </div>
    </>
  );
}
