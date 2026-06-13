'use client';

import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  Download,
  BarChart3,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Loader2,
  RefreshCw,
  Check,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TimeframeProgress {
  timeframe: '15m' | '1h' | '1d';
  current: number;
  total: number;
  message: string;
  /** ISO timestamp of the last received candle, if known */
  lastCandleTs?: string;
  /** Whether this timeframe completed successfully */
  done?: boolean;
}

export interface DataUpdateProgress {
  current: number;
  total: number;
  message: string;
  /** Per-timeframe breakdown */
  timeframes?: TimeframeProgress[];
  /** Retry info: current attempt number (1-based) */
  retryAttempt?: number;
  /** Max retries allowed */
  maxRetries?: number;
  /** Seconds until next retry attempt */
  retryInSeconds?: number;
  /** When set, download was skipped because data was already current */
  alreadyCurrent?: boolean;
  /** Connectivity check phase */
  networkCheckStatus?: 'checking' | 'ok' | 'failed';
}

export interface DataTypeStatus {
  status: 'complete' | 'gap' | 'missing' | 'error';
  start?: string;
  end?: string;
  gap_days?: number;
  gap_minutes?: number;
  error?: string;
}

export interface DataGapCheckResult {
  any_gaps: boolean;
  max_gap: number;
  all_status: Record<string, DataTypeStatus>;
  current_time: string;
  lakeapi_end?: string;
}

export interface DataUpdateModalProps {
  open: boolean;
  /** ISO date string for start of gap */
  gapStartDate?: string;
  /** ISO date string for cutoff */
  cutoffDate?: string;
  onUpdate: (startDate: string, endDate: string) => Promise<void>;
  onSkip: () => void;
  onCheckGaps?: () => Promise<DataGapCheckResult>;
  onGapCheckComplete?: (result: DataGapCheckResult) => void;
  progress?: DataUpdateProgress;
  isRunning?: boolean;
  result?: { success: boolean; message: string } | null;
  /** Pre-computed gap check result (if parent provides it) */
  gapCheckResult?: DataGapCheckResult | null;
  /** When true: auto-close on success (startup mode). Default false. */
  autoMode?: boolean;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** Single-timeframe progress row */
function TimeframeRow({ tf }: { tf: TimeframeProgress }) {
  const pct =
    tf.total > 0 ? Math.round((tf.current / tf.total) * 100) : tf.done ? 100 : 0;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="font-mono w-8" style={{ color: 'var(--text-secondary)' }}>{tf.timeframe}</span>
        <span className="flex-1 mx-3 truncate" style={{ color: 'var(--text-secondary)' }}>{tf.message}</span>
        {tf.lastCandleTs && (
          <span className="font-mono text-[10px] whitespace-nowrap" style={{ color: 'var(--text-muted)' }}>
            last: {new Date(tf.lastCandleTs).toUTCString().slice(5, 22)}
          </span>
        )}
        <span
          className="ml-2 flex items-center"
          style={{ color: tf.done ? 'var(--accent-green)' : 'var(--text-secondary)' }}
        >
          {tf.done
            ? <CheckCircle size={12} strokeWidth={1.5} />
            : <span className="text-[10px] font-medium">{pct}%</span>}
        </span>
      </div>
      <div className="w-full rounded-full h-1" style={{ background: 'var(--bg-hover)' }}>
        <div
          className="h-1 rounded-full transition-all duration-300"
          style={{ width: `${tf.done ? 100 : pct}%`, background: tf.done ? 'var(--accent-green)' : 'var(--accent-blue)' }}
        />
      </div>
    </div>
  );
}

/** Network connectivity indicator banner */
function NetworkCheckBanner({
  status,
}: {
  status: 'checking' | 'ok' | 'failed';
}) {
  if (status === 'ok') return null;
  return (
    <div
      className="flex items-center gap-2 text-xs px-3 py-2 rounded border"
      style={
        status === 'checking'
          ? { background: 'var(--bg-card)', borderColor: 'var(--border)', color: 'var(--text-secondary)' }
          : { background: 'color-mix(in srgb, var(--accent-red) 15%, transparent)', borderColor: 'var(--accent-red-dark)', color: 'var(--accent-red)' }
      }
    >
      {status === 'checking' ? (
        <>
          <Loader2 size={14} strokeWidth={1.5} className="animate-spin" style={{ flexShrink: 0 }} />
          <span>Checking Binance connectivity…</span>
        </>
      ) : (
        <>
          <XCircle size={14} strokeWidth={1.5} style={{ flexShrink: 0 }} />
          <span>Binance API unreachable — check your internet connection.</span>
        </>
      )}
    </div>
  );
}

/** Retry status banner */
function RetryBanner({
  attempt,
  maxRetries,
  retryInSeconds,
}: {
  attempt: number;
  maxRetries: number;
  retryInSeconds: number;
}) {
  return (
    <div className="flex items-center gap-2 text-xs px-3 py-2 rounded border" style={{ background: 'color-mix(in srgb, var(--accent-orange) 12%, transparent)', borderColor: 'var(--accent-orange)', color: 'var(--accent-orange)' }}>
      <RefreshCw size={14} strokeWidth={1.5} className="animate-pulse" style={{ flexShrink: 0 }} />
      <span>
        Attempt {attempt}/{maxRetries}… retrying in {retryInSeconds}s
      </span>
    </div>
  );
}

/** Fast-path "data already current" banner */
function AlreadyCurrentBanner() {
  return (
    <div className="flex items-center gap-2 text-xs px-3 py-2 rounded border" style={{ background: 'color-mix(in srgb, var(--accent-green) 12%, transparent)', borderColor: 'var(--accent-green-dark)', color: 'var(--accent-green)' }}>
      <CheckCircle size={14} strokeWidth={1.5} style={{ flexShrink: 0 }} />
      <span>Data already current — skipping download.</span>
    </div>
  );
}

/** Scrollable log area */
function DownloadLog({ lines }: { lines: string[] }) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [lines]);

  if (lines.length === 0) return null;

  return (
    <div className="rounded p-2 max-h-36 overflow-y-auto font-mono text-[10px] space-y-0.5 border" style={{ background: 'var(--bg-deep)', borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
      {lines.map((line, i) => (
        <div key={i}>{line}</div>
      ))}
      <div ref={endRef} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export const DataUpdateModal: React.FC<DataUpdateModalProps> = ({
  open,
  gapStartDate,
  cutoffDate,
  onUpdate,
  onSkip,
  onCheckGaps,
  onGapCheckComplete,
  progress,
  isRunning = false,
  result,
  gapCheckResult: propGapCheckResult,
  autoMode = false,
}) => {
  const [startDate, setStartDate] = useState(
    () =>
      gapStartDate ??
      new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
  );
  const [endDate, setEndDate] = useState(
    () => cutoffDate ?? new Date().toISOString().slice(0, 10),
  );

  // Accumulate log lines from progress messages
  const [logLines, setLogLines] = useState<string[]>([]);

  // Auto-close countdown for autoMode
  const [autoCloseSeconds, setAutoCloseSeconds] = useState<number | null>(null);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Gap check state - use prop if provided, otherwise use internal state
  const [internalGapCheckResult, setInternalGapCheckResult] = useState<DataGapCheckResult | null>(null);
  const gapCheckResult = propGapCheckResult ?? internalGapCheckResult;
  const [gapCheckLoading, setGapCheckLoading] = useState(false);
  const [buttonEnabled, setButtonEnabled] = useState(false);

  // Retry state
  const [retryCount, setRetryCount] = useState(0);
  const [retryTimer, setRetryTimer] = useState<number | null>(null);
  const retryTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const maxRetries = 3;

  // Define handleUpdate early so it can be used in useEffect
  const handleUpdate = useCallback(async () => {
    setLogLines([]);
    setRetryCount(0);
    await onUpdate(startDate, endDate);
  }, [startDate, endDate, onUpdate]);

  // Check for data gaps when modal opens or when propGapCheckResult changes
  useEffect(() => {
    if (!open) return;

    // If gap check result is provided as prop, use it directly
    if (propGapCheckResult) {
      setInternalGapCheckResult(propGapCheckResult);
      setButtonEnabled(true);
      onGapCheckComplete?.(propGapCheckResult);

      // If in auto mode and gaps exist, auto-start after 1 second
      if (autoMode && propGapCheckResult.any_gaps && !isRunning) {
        setTimeout(() => {
          handleUpdate();
        }, 1000);
      }
      // If in auto mode and no gaps, auto-close after 3 seconds
      if (autoMode && !propGapCheckResult.any_gaps) {
        setAutoCloseSeconds(3);
      }
      return;
    }

    // Otherwise, if onCheckGaps callback is provided, call it
    if (!onCheckGaps) {
      // No gap check provided - enable button and show default message
      setButtonEnabled(true);
      return;
    }

    setGapCheckLoading(true);
    setButtonEnabled(false);

    const checkGaps = async () => {
      try {
        const result = await onCheckGaps();
        setInternalGapCheckResult(result);
        onGapCheckComplete?.(result);

        // Enable button after gap check completes
        setButtonEnabled(true);

        // If in auto mode and gaps exist, auto-start after 1 second
        if (autoMode && result.any_gaps && !isRunning) {
          setTimeout(() => {
            handleUpdate();
          }, 1000);
        }
        // If in auto mode and no gaps, auto-close after 3 seconds
        if (autoMode && !result.any_gaps) {
          setAutoCloseSeconds(3);
        }
      } catch (error) {
        console.error('Failed to check data gaps:', error);
        setButtonEnabled(true);
      } finally {
        setGapCheckLoading(false);
      }
    };

    checkGaps();
  }, [open, propGapCheckResult, autoMode, isRunning, onCheckGaps, onGapCheckComplete, handleUpdate]);

  // Re-sync when gapStartDate or cutoffDate props change
  useEffect(() => {
    if (gapStartDate) setStartDate(gapStartDate);
  }, [gapStartDate]);

  useEffect(() => {
    if (cutoffDate) setEndDate(cutoffDate);
  }, [cutoffDate]);

  // Collect log lines from progress updates
  useEffect(() => {
    if (progress?.message) {
      const ts = new Date().toISOString().slice(11, 19);
      setLogLines((prev) => [...prev, `[${ts}] ${progress.message}`]);
    }
    if (progress?.timeframes) {
      for (const tf of progress.timeframes) {
        if (tf.message) {
          const ts = new Date().toISOString().slice(11, 19);
          setLogLines((prev) => [...prev, `[${ts}] (${tf.timeframe}) ${tf.message}`]);
        }
      }
    }
  }, [progress]);

  // Reset log when modal opens or a new run starts
  useEffect(() => {
    if (open && isRunning) {
      setLogLines([]);
    }
  }, [open, isRunning]);

  // Auto-close countdown when result is success and autoMode is on
  useEffect(() => {
    if (autoMode && result?.success) {
      setAutoCloseSeconds(3);
    }
  }, [autoMode, result]);

  // Handle auto-close countdown
  useEffect(() => {
    if (autoCloseSeconds === null) return;
    if (autoCloseSeconds <= 0) {
      if (countdownRef.current) clearInterval(countdownRef.current);
      onSkip(); // close
      return;
    }
    countdownRef.current = setInterval(() => {
      setAutoCloseSeconds((s) => (s !== null ? s - 1 : null));
    }, 1000);
    return () => {
      if (countdownRef.current) clearInterval(countdownRef.current);
    };
  }, [autoCloseSeconds, onSkip]);

  // Handle auto-close when no gaps in autoMode
  useEffect(() => {
    if (autoMode && gapCheckResult && !gapCheckResult.any_gaps && !autoCloseSeconds) {
      setAutoCloseSeconds(3);
    }
  }, [autoMode, gapCheckResult]);

  // Handle retry countdown
  useEffect(() => {
    if (retryTimer === null) return;
    if (retryTimer <= 0) {
      if (retryTimerRef.current) clearInterval(retryTimerRef.current);
      handleUpdate();
      return;
    }
    retryTimerRef.current = setInterval(() => {
      setRetryTimer((t) => (t !== null && t > 0 ? t - 1 : null));
    }, 1000);
    return () => {
      if (retryTimerRef.current) clearInterval(retryTimerRef.current);
    };
  }, [retryTimer, handleUpdate]);

  // Handle completion with retry logic
  useEffect(() => {
    if (!result) return;

    if (result.success) {
      setRetryCount(0);
      if (autoMode) {
        setAutoCloseSeconds(3);
      }
    } else if (autoMode && retryCount < maxRetries) {
      // Auto-retry after delay
      setRetryCount((c) => c + 1);
      setRetryTimer(5); // 5 second delay before retry
    }
  }, [result, autoMode, retryCount]);

  if (!open) return null;

  const overallPct =
    progress && progress.total > 0
      ? Math.round((progress.current / progress.total) * 100)
      : 0;

  const hasTimeframeBreakdown =
    isRunning && progress?.timeframes && progress.timeframes.length > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="rounded-lg shadow-2xl w-full max-w-2xl mx-4 border" style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}>
        {/* Header */}
        <div className="flex items-center gap-3 border-b px-6 py-4" style={{ borderColor: 'var(--border)' }}>
          <Download size={20} strokeWidth={1.5} style={{ flexShrink: 0, color: 'var(--text-secondary)' }} />
          <div>
            <h2 className="text-base font-semibold" style={{ color: 'var(--text-secondary)' }}>Data Update</h2>
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Strategy Builder Startup Check</p>
          </div>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-4">
          {/* ── Gap check loading state ────────────────────────── */}
          {gapCheckLoading && !isRunning && !result && (
            <div className="text-center py-6">
              <p className="text-sm mb-2" style={{ color: 'var(--text-secondary)' }}>Checking data availability…</p>
              <Loader2 size={20} strokeWidth={1.5} className="animate-spin inline-block" style={{ color: 'var(--text-secondary)' }} />
            </div>
          )}

          {/* ── Gap check result state ────────────────────────── */}
          {(gapCheckResult || (!gapCheckLoading && !isRunning && !result)) && (
            <>
              {gapCheckResult ? (
                <>
                  {/* Data Status Group - shows per-type gaps */}
                  <div className="rounded-lg p-4 space-y-3 border" style={{ borderColor: 'var(--border)' }}>
                    <h3 className="flex items-center gap-1.5 text-sm font-semibold" style={{ color: 'var(--text-secondary)' }}>
                      <BarChart3 size={14} strokeWidth={1.5} style={{ flexShrink: 0 }} />
                      Data Status
                    </h3>

                    <div className="space-y-2 text-sm">
                      {Object.entries(gapCheckResult.all_status).map(([dataType, info]) => (
                        <div key={dataType} className="flex items-start gap-3">
                          <span className="mt-0.5" style={{
                            color: info.status === 'complete'
                              ? 'var(--accent-green)'
                              : info.status === 'error'
                                ? 'var(--accent-orange)'
                                : 'var(--accent-red)',
                          }}>
                            {info.status === 'complete'
                              ? <CheckCircle size={14} strokeWidth={1.5} style={{ flexShrink: 0 }} />
                              : info.status === 'gap' || info.status === 'missing'
                                ? <XCircle size={14} strokeWidth={1.5} style={{ flexShrink: 0 }} />
                                : <AlertTriangle size={14} strokeWidth={1.5} style={{ flexShrink: 0 }} />}
                          </span>
                          <div className="flex-1">
                            <p className="font-mono" style={{ color: 'var(--text-secondary)' }}>
                              {dataType.toUpperCase()}:{' '}
                              {info.status === 'complete'
                                ? 'Complete'
                                : info.status === 'gap'
                                  ? `GAP DETECTED (${info.gap_days ?? 0} days)`
                                  : info.status === 'missing'
                                    ? 'MISSING'
                                    : 'ERROR'}
                            </p>
                            {info.start && info.end && (
                              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                                {info.start} → {info.end}
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>

                    {gapCheckResult.any_gaps && (
                      <div className="mt-3 p-3 rounded text-xs border" style={{ background: 'color-mix(in srgb, var(--accent-red) 12%, transparent)', borderColor: 'color-mix(in srgb, var(--accent-red-dark) 50%, transparent)', color: 'var(--accent-red)' }}>
                        <p className="flex items-center gap-1.5">
                          <AlertTriangle size={12} strokeWidth={1.5} style={{ flexShrink: 0 }} />
                          {gapCheckResult.max_gap > 0
                            ? `DATA GAPS DETECTED: Up to ${gapCheckResult.max_gap} days MISSING`
                            : 'Some data types are missing or incomplete'}
                        </p>
                      </div>
                    )}

                    {!gapCheckResult.any_gaps && (
                      <div className="mt-3 p-3 rounded text-xs border" style={{ background: 'color-mix(in srgb, var(--accent-green) 12%, transparent)', borderColor: 'color-mix(in srgb, var(--accent-green-dark) 50%, transparent)', color: 'var(--accent-green)' }}>
                        <p className="flex items-center gap-1.5">
                          <CheckCircle size={12} strokeWidth={1.5} style={{ flexShrink: 0 }} />
                          ALL DATA COMPLETE - 100% ACCURATE
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Date range inputs (only show if gaps exist) */}
                  {gapCheckResult.any_gaps && (
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1">
                        <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Start Date</label>
                        <input
                          type="date"
                          value={startDate}
                          onChange={(e) => setStartDate(e.target.value)}
                          className="w-full rounded px-3 py-2 text-sm focus:outline-none border"
                          style={{ background: 'var(--input-bg)', borderColor: 'var(--input-border)', color: 'var(--input-text)' }}
                        />
                      </div>
                      <div className="space-y-1">
                        <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>End Date</label>
                        <input
                          type="date"
                          value={endDate}
                          onChange={(e) => setEndDate(e.target.value)}
                          className="w-full rounded px-3 py-2 text-sm focus:outline-none border"
                          style={{ background: 'var(--input-bg)', borderColor: 'var(--input-border)', color: 'var(--input-text)' }}
                        />
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <>
                  {/* Fallback: no gap check result provided - show old UI */}
                  <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                    Missing market data detected. Download candle data from Binance to
                    ensure accurate backtesting.
                  </p>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Start Date</label>
                      <input
                        type="date"
                        value={startDate}
                        onChange={(e) => setStartDate(e.target.value)}
                        className="w-full rounded px-3 py-2 text-sm focus:outline-none border"
                        style={{ background: 'var(--input-bg)', borderColor: 'var(--input-border)', color: 'var(--input-text)' }}
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>End Date</label>
                      <input
                        type="date"
                        value={endDate}
                        onChange={(e) => setEndDate(e.target.value)}
                        className="w-full rounded px-3 py-2 text-sm focus:outline-none border"
                        style={{ background: 'var(--input-bg)', borderColor: 'var(--input-border)', color: 'var(--input-text)' }}
                      />
                    </div>
                  </div>
                </>
              )}
            </>
          )}

          {/* ── Running state ──────────────────────────────────── */}
          {isRunning && progress && (
            <div className="space-y-4">
              {/* Network check indicator */}
              {progress.networkCheckStatus &&
                progress.networkCheckStatus !== 'ok' && (
                  <NetworkCheckBanner status={progress.networkCheckStatus} />
                )}

              {/* Fast-path: already current */}
              {progress.alreadyCurrent && <AlreadyCurrentBanner />}

              {/* Retry banner */}
              {!progress.alreadyCurrent &&
                progress.retryAttempt !== undefined &&
                progress.retryAttempt > 1 &&
                progress.retryInSeconds !== undefined &&
                progress.retryInSeconds > 0 && (
                  <RetryBanner
                    attempt={progress.retryAttempt}
                    maxRetries={progress.maxRetries ?? 3}
                    retryInSeconds={progress.retryInSeconds}
                  />
                )}

              {/* Overall progress bar */}
              {!progress.alreadyCurrent && (
                <>
                  <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Downloading data from Binance…</p>
                  <div className="w-full rounded-full h-2" style={{ background: 'var(--bg-card)' }}>
                    <div
                      className="h-2 rounded-full transition-all duration-300"
                      style={{ width: `${overallPct}%`, background: 'var(--accent-blue)' }}
                    />
                  </div>
                  <div className="flex justify-between text-xs" style={{ color: 'var(--text-secondary)' }}>
                    <span>{progress.message ?? 'Initializing…'}</span>
                    <span>{overallPct}%</span>
                  </div>
                </>
              )}

              {/* Per-timeframe breakdown */}
              {hasTimeframeBreakdown && !progress.alreadyCurrent && (
                <div className="space-y-3 pt-1 border-t" style={{ borderColor: 'var(--bg-card)' }}>
                  <p className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>Per-timeframe progress</p>
                  {progress.timeframes!.map((tf) => (
                    <TimeframeRow key={tf.timeframe} tf={tf} />
                  ))}
                </div>
              )}

              {/* Scrollable download log */}
              <DownloadLog lines={logLines} />
            </div>
          )}

          {/* ── Result state ───────────────────────────────────── */}
          {result && (
            <div className="space-y-3">
              <div
                className="flex items-start gap-3 p-4 rounded border"
                style={
                  result.success
                    ? { background: 'color-mix(in srgb, var(--accent-green) 12%, transparent)', borderColor: 'var(--accent-green-dark)', color: 'var(--accent-green)' }
                    : { background: 'color-mix(in srgb, var(--accent-red) 12%, transparent)', borderColor: 'var(--accent-red-dark)', color: 'var(--accent-red)' }
                }
              >
                {result.success
                  ? <CheckCircle size={18} strokeWidth={1.5} style={{ flexShrink: 0, marginTop: 1 }} />
                  : <XCircle size={18} strokeWidth={1.5} style={{ flexShrink: 0, marginTop: 1 }} />}
                <p className="text-sm whitespace-pre-wrap">{result.message}</p>
              </div>

              {/* Auto-close countdown */}
              {autoMode && result.success && autoCloseSeconds !== null && (
                <p className="text-xs text-center" style={{ color: 'var(--text-muted)' }}>
                  Closing automatically in {autoCloseSeconds}s…
                </p>
              )}

              {/* Log output after completion */}
              <DownloadLog lines={logLines} />
            </div>
          )}
        </div>

        {/* Footer buttons */}
        <div className="flex justify-end gap-2 px-6 py-4 border-t" style={{ borderColor: 'var(--border)' }}>
          {gapCheckLoading && !isRunning && !result && (
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Checking data…</p>
          )}

          {gapCheckResult && !isRunning && !result && (
            <>
              {gapCheckResult.any_gaps && (
                <>
                  <button
                    onClick={onSkip}
                    className="px-4 py-2 rounded text-sm font-medium transition-colors"
                    style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
                    onMouseEnter={e => (e.currentTarget.style.background = 'var(--border)')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
                  >
                    Skip for Now
                  </button>
                  <button
                    onClick={handleUpdate}
                    disabled={!buttonEnabled}
                    className="flex items-center gap-1.5 px-4 py-2 rounded text-sm font-medium transition-colors"
                    style={
                      buttonEnabled
                        ? { background: 'var(--accent-blue)', color: 'var(--btn-primary-text)' }
                        : { background: 'var(--bg-hover)', color: 'var(--text-muted)', cursor: 'not-allowed', opacity: 0.5 }
                    }
                  >
                    <Download size={13} strokeWidth={1.5} aria-hidden="true" />
                    Update Data
                  </button>
                </>
              )}

              {!gapCheckResult.any_gaps && (
                <button
                  onClick={onSkip}
                  className="flex items-center gap-1.5 px-4 py-2 rounded text-sm font-medium transition-colors"
                  style={{ background: 'var(--btn-confirm-bg)', color: 'var(--btn-primary-text)' }}
                >
                  <Check size={13} strokeWidth={2} aria-hidden="true" />
                  Continue
                  {autoCloseSeconds !== null && autoCloseSeconds > 0
                    ? ` (${autoCloseSeconds}s)`
                    : ''}
                </button>
              )}
            </>
          )}

          {!gapCheckResult && !isRunning && !result && (
            <>
              <button
                onClick={onSkip}
                className="px-4 py-2 rounded text-sm font-medium transition-colors"
                style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
                onMouseEnter={e => (e.currentTarget.style.background = 'var(--border)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
              >
                Skip
              </button>
              <button
                onClick={handleUpdate}
                disabled={!buttonEnabled}
                className="flex items-center gap-1.5 px-4 py-2 rounded text-sm font-medium transition-colors"
                style={
                  buttonEnabled
                    ? { background: 'var(--accent-blue)', color: 'var(--btn-primary-text)' }
                    : { background: 'var(--bg-hover)', color: 'var(--text-muted)', cursor: 'not-allowed', opacity: 0.5 }
                }
              >
                <Download size={13} strokeWidth={1.5} aria-hidden="true" />
                Download Data
              </button>
            </>
          )}

          {isRunning && (
            <button
              onClick={onSkip}
              className="px-4 py-2 rounded text-sm font-medium transition-colors"
              style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--border)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
            >
              Skip
            </button>
          )}

          {result && (
            <>
              {result.success ? (
                <button
                  onClick={onSkip}
                  className="flex items-center gap-1.5 px-4 py-2 rounded text-sm font-medium transition-colors"
                  style={{ background: 'var(--btn-confirm-bg)', color: 'var(--btn-primary-text)' }}
                >
                  <Check size={13} strokeWidth={2} aria-hidden="true" />
                  Continue
                  {autoMode && autoCloseSeconds !== null && autoCloseSeconds > 0
                    ? ` (${autoCloseSeconds}s)`
                    : ''}
                </button>
              ) : (
                <>
                  {autoMode && retryCount < maxRetries && retryTimer !== null && retryTimer > 0 && (
                    <span className="flex items-center gap-1.5 text-xs mr-2" style={{ color: 'var(--accent-orange)' }}>
                      <RefreshCw size={12} strokeWidth={1.5} />
                      Retrying in {retryTimer}s…
                    </span>
                  )}
                  <button
                    onClick={onSkip}
                    className="px-4 py-2 rounded text-sm font-medium transition-colors"
                    style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
                    onMouseEnter={e => (e.currentTarget.style.background = 'var(--border)')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
                  >
                    Close
                  </button>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default DataUpdateModal;
