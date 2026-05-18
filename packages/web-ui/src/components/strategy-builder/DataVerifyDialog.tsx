'use client';

import React, { useState, useCallback } from 'react';

export interface DataGapEntry {
  gapStart: string;
  gapEnd: string;
  missingBars: number;
  repairable: boolean;
  reason?: string;
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
  /** ISO string of the most recent stored candle for this timeframe, or null */
  lastCandleTs: string | null;
}

export interface DataVerifyDialogProps {
  open: boolean;
  onVerify: () => Promise<Record<string, TimeframeVerifyResult>>;
  onRepair: (timeframe: string) => Promise<void>;
  onClose: () => void;
}

// ─── Summary banner helpers ──────────────────────────────────────────────────

type SummaryVariant = 'clean' | 'fixable' | 'too-old' | 'mixed' | 'idle';

interface SummaryBanner {
  icon: string;
  text: string;
  variant: SummaryVariant;
}

function computeSummary(
  results: TimeframeVerifyResult[]
): SummaryBanner {
  const totalRepairable = results.reduce((s, r) => s + r.repairableCount, 0);
  const totalTooOld = results.reduce((s, r) => s + r.tooOldCount, 0);
  const totalRepairableMissing = results.reduce((s, r) => s + (r.repairableMissingBars ?? 0), 0);
  const totalTooOldMissing = results.reduce((s, r) => s + (r.tooOldMissingBars ?? 0), 0);

  if (totalRepairable === 0 && totalTooOld === 0) {
    return { icon: '✅', text: 'All data is complete — no gaps found', variant: 'clean' };
  }
  if (totalRepairable > 0 && totalTooOld === 0) {
    return {
      icon: '⚠️',
      text: `Fixable gaps found — ${totalRepairable} gap(s), ${totalRepairableMissing} missing bars. Use "Fix Gaps" to repair from Binance.`,
      variant: 'fixable',
    };
  }
  if (totalRepairable === 0 && totalTooOld > 0) {
    return {
      icon: '❌',
      text: `Too-old gaps (unfixable) — ${totalTooOld} gap(s), ${totalTooOldMissing} missing bars older than 90-day Binance horizon. LakeAPI backfill needed.`,
      variant: 'too-old',
    };
  }
  return {
    icon: '⚠️',
    text: `Mixed gaps — ${totalRepairable} fixable (${totalRepairableMissing} bars) + ${totalTooOld} too old (${totalTooOldMissing} bars, need LakeAPI).`,
    variant: 'mixed',
  };
}

const BANNER_STYLES: Record<SummaryVariant, string> = {
  clean: 'bg-green-900/30 border-green-700 text-green-300',
  fixable: 'bg-amber-900/30 border-amber-600 text-amber-300',
  'too-old': 'bg-red-900/30 border-red-700 text-red-300',
  mixed: 'bg-amber-900/30 border-amber-600 text-amber-300',
  idle: 'bg-zinc-800 border-zinc-700 text-zinc-400',
};

// ─── Per-timeframe row rendering ─────────────────────────────────────────────

interface TfRowProps {
  result: TimeframeVerifyResult;
  isRepairing: boolean;
  onRepair: () => void;
}

function formatLastCandle(ts: string | null): string {
  if (!ts) return '—';
  try {
    const d = new Date(ts);
    const yyyy = d.getUTCFullYear();
    const mm = String(d.getUTCMonth() + 1).padStart(2, '0');
    const dd = String(d.getUTCDate()).padStart(2, '0');
    const hh = String(d.getUTCHours()).padStart(2, '0');
    const min = String(d.getUTCMinutes()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd} ${hh}:${min} UTC`;
  } catch {
    return ts;
  }
}

function TimeframeRow({ result, isRepairing, onRepair }: TfRowProps) {
  const {
    timeframe,
    repairableCount,
    tooOldCount,
    repairableMissingBars,
    tooOldMissingBars,
    gaps,
    lastCandleTs,
  } = result;

  const totalGaps = repairableCount + tooOldCount;
  const hasMixed = repairableCount > 0 && tooOldCount > 0;

  // Determine primary row status
  let statusLabel: string;
  let statusClass: string;
  let primaryNotes: string;

  if (totalGaps === 0) {
    statusLabel = '✓ Clean';
    statusClass = 'bg-green-900/40 text-green-400';
    primaryNotes = 'No action required';
  } else if (repairableCount > 0 && tooOldCount === 0) {
    statusLabel = 'Repairable Gaps';
    statusClass = 'bg-red-900/40 text-red-400';
    const earliest = gaps
      .filter((g) => g.repairable)
      .map((g) => g.gapStart)
      .sort()[0];
    primaryNotes = earliest ? `Earliest: ${earliest}` : '';
  } else if (repairableCount === 0 && tooOldCount > 0) {
    statusLabel = 'Too Old (Binance limit - cannot repair)';
    statusClass = 'bg-orange-900/40 text-orange-400';
    const earliest = gaps
      .filter((g) => !g.repairable)
      .map((g) => g.gapStart)
      .sort()[0];
    primaryNotes = earliest ? `From ${earliest} — beyond 90d horizon` : '';
  } else {
    statusLabel = 'Mixed Gaps';
    statusClass = 'bg-amber-900/40 text-amber-400';
    primaryNotes = `${repairableCount} fixable, ${tooOldCount} need LakeAPI`;
  }

  const repairableGaps = gaps.filter((g) => g.repairable);
  const tooOldGaps = gaps.filter((g) => !g.repairable);

  return (
    <div className="bg-zinc-800/50 rounded-lg border border-zinc-700">
      {/* ── Primary row header ── */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b border-zinc-700">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-sm font-bold text-zinc-100 min-w-[3rem]">{timeframe}</span>
          <span className={`px-2 py-0.5 rounded text-xs font-semibold ${statusClass}`}>
            {statusLabel}
          </span>
          {totalGaps > 0 && (
            <>
              <span className="text-xs text-zinc-400">
                Repairable: <span className="text-green-400 font-medium">{repairableCount}</span>
                {repairableCount > 0 && (
                  <span className="text-zinc-500"> ({repairableMissingBars ?? 0} bars)</span>
                )}
              </span>
              {tooOldCount > 0 && (
                <span className="text-xs text-zinc-400">
                  Too Old: <span className="text-orange-400 font-medium">{tooOldCount}</span>
                  <span className="text-zinc-500"> ({tooOldMissingBars ?? 0} bars)</span>
                </span>
              )}
            </>
          )}
          {primaryNotes && (
            <span className="text-xs text-zinc-500 italic">{primaryNotes}</span>
          )}
        </div>

        <div className="flex items-center gap-3 text-xs text-zinc-400">
          <span>
            Most recent data:{' '}
            <span className="text-zinc-300 font-mono">{formatLastCandle(lastCandleTs)}</span>
          </span>
          {repairableCount > 0 && (
            <button
              onClick={onRepair}
              disabled={isRepairing}
              className="px-3 py-1 rounded bg-green-700 text-white text-xs font-medium hover:bg-green-600 disabled:opacity-50 transition-colors"
            >
              {isRepairing ? 'Repairing…' : 'Fix Gaps'}
            </button>
          )}
        </div>
      </div>

      {/* ── Mixed: secondary row for too-old portion ── */}
      {hasMixed && (
        <div className="flex flex-wrap items-center gap-3 px-4 py-2 border-b border-zinc-700/60 bg-zinc-900/30">
          <span className="text-xs font-mono text-zinc-500">{timeframe} (old)</span>
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-orange-900/40 text-orange-400">
            Too Old (Binance limit - cannot repair)
          </span>
          <span className="text-xs text-zinc-400">
            {tooOldCount} gap(s) · {tooOldMissingBars ?? 0} missing bars
          </span>
          {tooOldGaps.length > 0 && (
            <span className="text-xs text-zinc-500 italic">
              From {tooOldGaps.map((g) => g.gapStart).sort()[0]} — beyond 90d horizon
            </span>
          )}
        </div>
      )}

      {/* ── Gap detail table ── */}
      {gaps.length > 0 && (
        <div className="overflow-x-auto max-h-52">
          <table className="w-full text-xs border-collapse">
            <thead className="bg-zinc-800 sticky top-0">
              <tr>
                <th className="px-3 py-2 text-left text-zinc-400 font-semibold">Start</th>
                <th className="px-3 py-2 text-left text-zinc-400 font-semibold">End</th>
                <th className="px-3 py-2 text-right text-zinc-400 font-semibold">Missing Bars</th>
                <th className="px-3 py-2 text-left text-zinc-400 font-semibold">Status</th>
                <th className="px-3 py-2 text-left text-zinc-400 font-semibold">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-700/40">
              {repairableGaps.map((gap, i) => (
                <tr key={`r-${i}`} className="hover:bg-zinc-700/20">
                  <td className="px-3 py-1.5 text-zinc-300 font-mono">{gap.gapStart}</td>
                  <td className="px-3 py-1.5 text-zinc-300 font-mono">{gap.gapEnd}</td>
                  <td className="px-3 py-1.5 text-zinc-300 text-right font-medium">{gap.missingBars}</td>
                  <td className="px-3 py-1.5">
                    <span className="px-1.5 py-0.5 rounded text-xs bg-green-900/40 text-green-400">
                      Repairable
                    </span>
                  </td>
                  <td className="px-3 py-1.5 text-zinc-500">{gap.reason ?? '—'}</td>
                </tr>
              ))}
              {tooOldGaps.map((gap, i) => (
                <tr key={`o-${i}`} className="hover:bg-zinc-700/20">
                  <td className="px-3 py-1.5 text-zinc-300 font-mono">{gap.gapStart}</td>
                  <td className="px-3 py-1.5 text-zinc-300 font-mono">{gap.gapEnd}</td>
                  <td className="px-3 py-1.5 text-zinc-300 text-right font-medium">{gap.missingBars}</td>
                  <td className="px-3 py-1.5">
                    <span className="px-1.5 py-0.5 rounded text-xs bg-orange-900/40 text-orange-400">
                      Too Old
                    </span>
                  </td>
                  <td className="px-3 py-1.5 text-zinc-500">
                    {gap.reason ?? '(Binance limit - cannot repair)'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── Main dialog ─────────────────────────────────────────────────────────────

export const DataVerifyDialog: React.FC<DataVerifyDialogProps> = ({
  open,
  onVerify,
  onRepair,
  onClose,
}) => {
  const [isVerifying, setIsVerifying] = useState(false);
  const [isRepairing, setIsRepairing] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, TimeframeVerifyResult> | null>(null);
  const [error, setError] = useState('');
  const [repairStatus, setRepairStatus] = useState('');

  const handleVerify = useCallback(async () => {
    setIsVerifying(true);
    setError('');
    setRepairStatus('');
    try {
      const res = await onVerify();
      setResults(res);
    } catch (e) {
      setError(String(e));
    } finally {
      setIsVerifying(false);
    }
  }, [onVerify]);

  const handleRepair = useCallback(
    async (tf: string) => {
      setIsRepairing(tf);
      setError('');
      try {
        await onRepair(tf);
        setRepairStatus(`Repair complete for ${tf} — re-verifying…`);
        // Auto-repair + re-verify chain
        const res = await onVerify();
        setResults(res);
        setRepairStatus('');
      } catch (e) {
        setError(String(e));
      } finally {
        setIsRepairing(null);
      }
    },
    [onRepair, onVerify]
  );

  if (!open) return null;

  const tfResults = results ? Object.values(results) : [];
  const summary = tfResults.length > 0 ? computeSummary(tfResults) : null;
  const hasAnyRepairable = tfResults.some((r) => r.repairableCount > 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl w-full max-w-5xl mx-4 max-h-[92vh] flex flex-col">

        {/* ── Header ── */}
        <div className="flex items-center justify-between border-b border-zinc-700 px-6 py-4 flex-shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-xl">🔍</span>
            <div>
              <h2 className="text-base font-semibold text-zinc-100">Data Verification</h2>
              <p className="text-xs text-zinc-400">
                Gap detection and repair for BTCUSDT Perpetual OHLCV data across all timeframes
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-zinc-200 transition-colors text-xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {/* ── Body ── */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">

          {/* Error */}
          {error && (
            <div className="bg-red-900/20 border border-red-700 rounded p-3 text-sm text-red-300">
              {error}
            </div>
          )}

          {/* Repair in-progress status */}
          {repairStatus && (
            <div className="bg-blue-900/20 border border-blue-700 rounded p-3 text-sm text-blue-300">
              {repairStatus}
            </div>
          )}

          {/* Summary banner */}
          {summary && (
            <div
              className={`rounded-lg border px-4 py-3 text-sm font-semibold flex items-center gap-2 ${BANNER_STYLES[summary.variant]}`}
            >
              <span>{summary.icon}</span>
              <span>{summary.text}</span>
            </div>
          )}

          {/* Idle prompt */}
          {!results && !isVerifying && (
            <div className="text-center py-12">
              <p className="text-zinc-400 text-sm mb-4">
                Run verification to detect gaps in your stored OHLCV data.
              </p>
              <button
                onClick={handleVerify}
                className="px-5 py-2.5 rounded bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                Run Verification
              </button>
            </div>
          )}

          {/* Spinner */}
          {isVerifying && (
            <div className="text-center py-12">
              <div className="inline-block w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mb-4" />
              <p className="text-zinc-400 text-sm">Scanning data files…</p>
            </div>
          )}

          {/* Per-timeframe results */}
          {tfResults.map((tfResult) => (
            <TimeframeRow
              key={tfResult.timeframe}
              result={tfResult}
              isRepairing={isRepairing === tfResult.timeframe}
              onRepair={() => handleRepair(tfResult.timeframe)}
            />
          ))}
        </div>

        {/* ── Footer ── */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-zinc-700 flex-shrink-0">
          <div className="flex gap-2">
            {results && (
              <button
                onClick={handleVerify}
                disabled={isVerifying || !!isRepairing}
                className="px-4 py-2 rounded bg-zinc-700 text-zinc-200 text-sm font-medium hover:bg-zinc-600 disabled:opacity-50 transition-colors"
              >
                Re-verify
              </button>
            )}
            {hasAnyRepairable && !isRepairing && (
              <button
                onClick={() => {
                  // Repair all timeframes sequentially by triggering the first repairable one —
                  // each repair auto-re-verifies, so subsequent ones will appear on next Re-verify.
                  const first = tfResults.find((r) => r.repairableCount > 0);
                  if (first) handleRepair(first.timeframe);
                }}
                className="px-4 py-2 rounded bg-green-700 text-white text-sm font-medium hover:bg-green-600 transition-colors"
              >
                Fix Gaps
              </button>
            )}
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded bg-zinc-700 text-zinc-200 text-sm font-medium hover:bg-zinc-600 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default DataVerifyDialog;
