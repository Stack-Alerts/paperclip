import { get, post } from '@/lib/strategy-builder/api';
export type { DataGapCheckResult, DataTypeStatus } from '@/components/strategy-builder/DataUpdateModal';
import type { DataGapCheckResult } from '@/components/strategy-builder/DataUpdateModal';

export interface TimeframeFreshness {
  lastBarTs: string | null;
  ageSeconds: number | null;
  stale: boolean;
  error?: string;
}

export interface DataStatusResponse {
  currentTime: string;
  anyGaps: boolean;
  anyStale: boolean;
  allStatus: Record<string, { status: string; start?: string; end?: string; gap_days?: number; gap_minutes?: number; error?: string }>;
  timeframeFreshness: Record<string, TimeframeFreshness>;
}

export interface DataUpdateResult {
  success: boolean;
  message: string;
  results: Record<string, { success: boolean; bars_downloaded?: number; error?: string }>;
}

export interface DataGapEntry {
  gapStart: string | null;
  gapEnd: string | null;
  missingBars: number;
  repairable: boolean;
  reason?: string | null;
}

export interface TimeframeVerifyResult {
  timeframe: string;
  totalGaps: number;
  repairableCount: number;
  tooOldCount: number;
  totalMissingBars: number;
  repairableMissingBars: number;
  tooOldMissingBars: number;
  gaps: DataGapEntry[];
  lastCandleTs: string | null;
}

export interface DataRepairResult {
  success: boolean;
  message: string;
  summary: Record<string, {
    gapsFound: number;
    gapsRepaired: number;
    gapsTooOld: number;
    barsFetched: number;
    errors: string[];
  }>;
}

export async function fetchDataStatus(): Promise<DataStatusResponse> {
  return get<DataStatusResponse>('/data/status');
}

export async function fetchDataGapCheck(): Promise<DataGapCheckResult> {
  return get('/data/gap-check') as Promise<DataGapCheckResult>;
}

export async function triggerDataUpdate(startDate: string, endDate: string): Promise<DataUpdateResult> {
  return post<DataUpdateResult>('/data/update', { startDate, endDate });
}

export async function runDataVerify(): Promise<Record<string, TimeframeVerifyResult>> {
  return post<Record<string, TimeframeVerifyResult>>('/data/verify', {});
}

export async function runDataRepair(timeframe?: string): Promise<DataRepairResult> {
  return post<DataRepairResult>('/data/repair', { timeframe: timeframe ?? null });
}

export interface BulkBackfillResult {
  success: boolean;
  message: string;
  summary: {
    downloaded: number;
    skipped: number;
    errors: number;
    totalBars: number;
    errorKeys: string[];
  };
}

export async function runBulkBackfill(
  fromMonth: string,
  toMonth: string,
  skipExisting = true,
): Promise<BulkBackfillResult> {
  return post<BulkBackfillResult>('/data/bulk-backfill', { fromMonth, toMonth, skipExisting });
}

// ---------------------------------------------------------------------------
// Timestamp formatting helpers (BTCAAAAA-35962 follow-up)
//
// The backend's ``_iso_dt()`` now tags naive datetimes with 'Z' so a string
// like ``"2026-06-12T07:00:00"`` from a legacy call or a manual test is
// still treated as UTC.  ``parseApiTimestamp`` normalizes both forms before
// handing a ``Date`` to the formatters below.  ``formatLocalShort`` shows
// the time in the user's local timezone (matches what the thick client
// shows) so a user in UTC+2 reading 07:00Z sees 09:00, not 05:00.
// ---------------------------------------------------------------------------

export function parseApiTimestamp(ts: string | null | undefined): Date | null {
  if (!ts) return null;
  try {
    const hasTz = /Z$|[+-]\d{2}:?\d{2}$/.test(ts);
    return new Date(hasTz ? ts : ts + 'Z');
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Interval-aware staleness (BTCAAAAA-38869)
//
// The backend uses fixed age thresholds (e.g. 25 h for 1d) which flag the
// last *closed* candle as stale even when no bar is actually missing. The
// Market Data page already corrected for this locally; the sidebar widget
// consumed the raw backend ``anyStale`` flag, so the two disagreed. Both now
// share this computation: a timeframe is stale only when its last bar's
// open-time predates the expected open of the last fully-closed candle.
// ---------------------------------------------------------------------------

export function computeActualStale(tf: string, f: TimeframeFreshness): boolean {
  if (!f.lastBarTs || f.ageSeconds === null) return true;
  const intervalSeconds: Record<string, number> = { '15m': 900, '1h': 3600, '1d': 86400 };
  const interval = intervalSeconds[tf];
  if (interval === undefined) return f.stale;
  const nowSec = Date.now() / 1000;
  const expectedLastClosedOpen = Math.floor(nowSec / interval) * interval - interval;
  const d = parseApiTimestamp(f.lastBarTs);
  if (!d) return true;
  return d.getTime() / 1000 < expectedLastClosedOpen;
}

export function anyTimeframeActuallyStale(
  freshness: Record<string, TimeframeFreshness> | null | undefined,
): boolean {
  if (!freshness) return false;
  return Object.entries(freshness).some(([tf, f]) => computeActualStale(tf, f));
}

export function formatLocalShort(ts: string | null | undefined): string {
  const d = parseApiTimestamp(ts);
  if (!d) return '—';
  // "2026-06-12 09:00" in the user's local timezone
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  const hh = String(d.getHours()).padStart(2, '0');
  const min = String(d.getMinutes()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd} ${hh}:${min}`;
}
