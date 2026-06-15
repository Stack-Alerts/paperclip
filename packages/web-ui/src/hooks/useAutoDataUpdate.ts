'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { fetchDataStatus, triggerDataUpdate } from '@/lib/data-management/api';
import type { DataStatusResponse } from '@/lib/data-management/api';

export type AutoUpdateStatus = 'idle' | 'updating' | 'ok' | 'error';

export interface AutoDataUpdateState {
  lastCandleTs: string | null;
  lastUpdateTime: Date | null;
  nextCheckTime: Date | null;
  status: AutoUpdateStatus;
  statusMessage: string;
  isUpdating: boolean;
}

/** Mirrors the thick-client _start_auto_update_system / _schedule_next_check logic.
 *
 * Fires 2 s after each 15-minute candle close, triggers a data update for the
 * rolling 3-day window, then reschedules for the next close.  Also exposes the
 * last-candle timestamp and countdown for the sidebar widget.
 */
export function useAutoDataUpdate(): AutoDataUpdateState {
  const [lastCandleTs, setLastCandleTs] = useState<string | null>(null);
  const [lastUpdateTime, setLastUpdateTime] = useState<Date | null>(null);
  const [nextCheckTime, setNextCheckTime] = useState<Date | null>(null);
  const [status, setStatus] = useState<AutoUpdateStatus>('idle');
  const [statusMessage, setStatusMessage] = useState<string>('Initialising…');
  const [isUpdating, setIsUpdating] = useState(false);

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inQuickRetryRef = useRef(false);

  /** Refresh /data/status and update lastCandleTs */
  const refreshStatus = useCallback(async () => {
    try {
      const s: DataStatusResponse = await fetchDataStatus();
      const ts15m = s.timeframeFreshness['15m']?.lastBarTs ?? null;
      setLastCandleTs(ts15m);
      return s;
    } catch {
      return null;
    }
  }, []);

  /** Compute ms until 2 s after the next 15-minute candle close */
  function msUntilNextCheck(): number {
    const now = new Date();
    const utcMinutes = now.getUTCMinutes();
    const utcSeconds = now.getUTCSeconds();
    const minutesToNext = 15 - (utcMinutes % 15);
    const secondsToNext = minutesToNext * 60 - utcSeconds;
    // clamp: at exact boundary formula yields 900 which is correct; guard > 900
    const clamped = secondsToNext > 900 ? 1 : secondsToNext;
    return (clamped * 1000) + 2000; // +2 s Binance finalisation buffer
  }

  const scheduleNextCheck = useCallback((checkFn: () => void) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    const ms = Math.min(msUntilNextCheck(), 5 * 60 * 1000); // 5-min hard cap
    const next = new Date(Date.now() + ms);
    setNextCheckTime(next);
    timerRef.current = setTimeout(checkFn, ms);
  }, []);

  const runUpdate = useCallback(async (reschedule: (fn: () => void) => void) => {
    setIsUpdating(true);
    setStatus('updating');
    setStatusMessage('Checking for new candles…');
    try {
      // 3-day rolling window — safe overfetch, matches thick client approach
      const now = new Date();
      const start = new Date(now);
      start.setUTCDate(start.getUTCDate() - 2);
      const end = new Date(now);
      end.setUTCDate(end.getUTCDate() + 1);
      const fmt = (d: Date) => d.toISOString().slice(0, 10);
      await triggerDataUpdate(fmt(start), fmt(end));
      const s = await refreshStatus();
      const ts15m = s?.timeframeFreshness['15m']?.lastBarTs ?? null;
      if (ts15m) setLastCandleTs(ts15m);
      setLastUpdateTime(new Date());
      setStatus('ok');
      setStatusMessage('Data up-to-date');
      inQuickRetryRef.current = false;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setStatus('error');
      setStatusMessage(`Update error: ${msg.slice(0, 60)}`);
      // Quick-retry once on failure (matches thick client _in_quick_retry guard)
      if (!inQuickRetryRef.current) {
        inQuickRetryRef.current = true;
        // eslint-disable-next-line react-hooks/immutability -- intentional self-reference for the quick-retry recursion
        timerRef.current = setTimeout(() => runUpdate(reschedule), 12_000);
        setStatusMessage('Retrying in 12 s…');
        setIsUpdating(false);
        return;
      }
      inQuickRetryRef.current = false;
    } finally {
      setIsUpdating(false);
    }
    reschedule(() => runUpdate(reschedule));
  }, [refreshStatus]);

  // Bootstrap: load current status immediately, then arm the first timer
  useEffect(() => {
    let cancelled = false;

    const start = async () => {
      const s = await refreshStatus();
      if (cancelled) return;
      if (s) {
        const ts15m = s.timeframeFreshness['15m']?.lastBarTs ?? null;
        setLastCandleTs(ts15m);
        setStatus(s.anyStale ? 'error' : 'ok');
        setStatusMessage(s.anyStale ? 'Data may be stale' : 'Data up-to-date');
      }
      // Arm first timer
      const check = () => runUpdate(scheduleNextCheck);
      scheduleNextCheck(check);
    };

    start();

    return () => {
      cancelled = true;
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [refreshStatus, runUpdate, scheduleNextCheck]);

  return { lastCandleTs, lastUpdateTime, nextCheckTime, status, statusMessage, isUpdating };
}
