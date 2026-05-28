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

const BANNER_INLINE_STYLES: Record<SummaryVariant, React.CSSProperties> = {
  clean: { background: 'color-mix(in srgb, var(--accent-green) 15%, transparent)', borderColor: 'var(--accent-green-dark)', color: 'var(--accent-green)' },
  fixable: { background: 'color-mix(in srgb, var(--accent-orange) 15%, transparent)', borderColor: 'var(--accent-orange)', color: 'var(--accent-orange)' },
  'too-old': { background: 'color-mix(in srgb, var(--accent-red) 15%, transparent)', borderColor: 'var(--accent-red-dark)', color: 'var(--accent-red)' },
  mixed: { background: 'color-mix(in srgb, var(--accent-orange) 15%, transparent)', borderColor: 'var(--accent-orange)', color: 'var(--accent-orange)' },
  idle: { background: 'var(--bg-card)', borderColor: 'var(--border)', color: 'var(--text-secondary)' },
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
  let statusStyle: React.CSSProperties;
  let primaryNotes: string;

  if (totalGaps === 0) {
    statusLabel = '✓ Clean';
    statusStyle = { background: 'color-mix(in srgb, var(--accent-green) 20%, transparent)', color: 'var(--accent-green)' };
    primaryNotes = 'No action required';
  } else if (repairableCount > 0 && tooOldCount === 0) {
    statusLabel = 'Repairable Gaps';
    statusStyle = { background: 'color-mix(in srgb, var(--accent-red) 20%, transparent)', color: 'var(--accent-red)' };
    const earliest = gaps
      .filter((g) => g.repairable)
      .map((g) => g.gapStart)
      .sort()[0];
    primaryNotes = earliest ? `Earliest: ${earliest}` : '';
  } else if (repairableCount === 0 && tooOldCount > 0) {
    statusLabel = 'Too Old (Binance limit - cannot repair)';
    statusStyle = { background: 'color-mix(in srgb, var(--accent-orange) 20%, transparent)', color: 'var(--accent-orange)' };
    const earliest = gaps
      .filter((g) => !g.repairable)
      .map((g) => g.gapStart)
      .sort()[0];
    primaryNotes = earliest ? `From ${earliest} — beyond 90d horizon` : '';
  } else {
    statusLabel = 'Mixed Gaps';
    statusStyle = { background: 'color-mix(in srgb, var(--accent-orange) 15%, transparent)', color: 'var(--accent-orange)' };
    primaryNotes = `${repairableCount} fixable, ${tooOldCount} need LakeAPI`;
  }

  const repairableGaps = gaps.filter((g) => g.repairable);
  const tooOldGaps = gaps.filter((g) => !g.repairable);

  return (
    <div className="rounded-lg border" style={{ background: 'color-mix(in srgb, var(--bg-card) 50%, transparent)', borderColor: 'var(--border)' }}>
      {/* ── Primary row header ── */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b" style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-sm font-bold min-w-[3rem]" style={{ color: 'var(--text-primary)' }}>{timeframe}</span>
          <span className="px-2 py-0.5 rounded text-xs font-semibold" style={statusStyle}>
            {statusLabel}
          </span>
          {totalGaps > 0 && (
            <>
              <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                Repairable: <span style={{ color: 'var(--accent-green)', fontWeight: 500 }}>{repairableCount}</span>
                {repairableCount > 0 && (
                  <span style={{ color: 'var(--text-muted)' }}> ({repairableMissingBars ?? 0} bars)</span>
                )}
              </span>
              {tooOldCount > 0 && (
                <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  Too Old: <span style={{ color: 'var(--accent-orange)', fontWeight: 500 }}>{tooOldCount}</span>
                  <span style={{ color: 'var(--text-muted)' }}> ({tooOldMissingBars ?? 0} bars)</span>
                </span>
              )}
            </>
          )}
          {primaryNotes && (
            <span className="text-xs italic" style={{ color: 'var(--text-muted)' }}>{primaryNotes}</span>
          )}
        </div>

        <div className="flex items-center gap-3 text-xs" style={{ color: 'var(--text-secondary)' }}>
          <span>
            Most recent data:{' '}
            <span className="font-mono" style={{ color: 'var(--text-primary)' }}>{formatLastCandle(lastCandleTs)}</span>
          </span>
          {repairableCount > 0 && (
            <button
              onClick={onRepair}
              disabled={isRepairing}
              className="px-3 py-1 rounded text-xs font-medium disabled:opacity-50 transition-colors"
              style={{ background: 'var(--btn-confirm-bg)', color: 'var(--btn-primary-text)' }}
            >
              {isRepairing ? 'Repairing…' : 'Fix Gaps'}
            </button>
          )}
        </div>
      </div>

      {/* ── Mixed: secondary row for too-old portion ── */}
      {hasMixed && (
        <div className="flex flex-wrap items-center gap-3 px-4 py-2 border-b" style={{ borderColor: 'color-mix(in srgb, var(--border) 60%, transparent)', background: 'color-mix(in srgb, var(--bg-panel) 30%, transparent)' }}>
          <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>{timeframe} (old)</span>
          <span className="px-2 py-0.5 rounded text-xs font-semibold" style={{ background: 'color-mix(in srgb, var(--accent-orange) 20%, transparent)', color: 'var(--accent-orange)' }}>
            Too Old (Binance limit - cannot repair)
          </span>
          <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
            {tooOldCount} gap(s) · {tooOldMissingBars ?? 0} missing bars
          </span>
          {tooOldGaps.length > 0 && (
            <span className="text-xs italic" style={{ color: 'var(--text-muted)' }}>
              From {tooOldGaps.map((g) => g.gapStart).sort()[0]} — beyond 90d horizon
            </span>
          )}
        </div>
      )}

      {/* ── Gap detail table ── */}
      {gaps.length > 0 && (
        <div className="overflow-x-auto max-h-52">
          <table className="w-full text-xs border-collapse">
            <thead className="sticky top-0" style={{ background: 'var(--bg-card)' }}>
              <tr>
                <th className="px-3 py-2 text-left font-semibold" style={{ color: 'var(--text-secondary)' }}>Start</th>
                <th className="px-3 py-2 text-left font-semibold" style={{ color: 'var(--text-secondary)' }}>End</th>
                <th className="px-3 py-2 text-right font-semibold" style={{ color: 'var(--text-secondary)' }}>Missing Bars</th>
                <th className="px-3 py-2 text-left font-semibold" style={{ color: 'var(--text-secondary)' }}>Status</th>
                <th className="px-3 py-2 text-left font-semibold" style={{ color: 'var(--text-secondary)' }}>Notes</th>
              </tr>
            </thead>
            <tbody style={{ borderColor: 'var(--border)' }}>
              {repairableGaps.map((gap, i) => (
                <tr
                  key={`r-${i}`}
                  onMouseEnter={e => ((e.currentTarget as HTMLTableRowElement).style.background = 'color-mix(in srgb, var(--bg-hover) 20%, transparent)')}
                  onMouseLeave={e => ((e.currentTarget as HTMLTableRowElement).style.background = '')}
                >
                  <td className="px-3 py-1.5 font-mono" style={{ color: 'var(--text-primary)' }}>{gap.gapStart}</td>
                  <td className="px-3 py-1.5 font-mono" style={{ color: 'var(--text-primary)' }}>{gap.gapEnd}</td>
                  <td className="px-3 py-1.5 text-right font-medium" style={{ color: 'var(--text-primary)' }}>{gap.missingBars}</td>
                  <td className="px-3 py-1.5">
                    <span className="px-1.5 py-0.5 rounded text-xs" style={{ background: 'color-mix(in srgb, var(--accent-green) 20%, transparent)', color: 'var(--accent-green)' }}>
                      Repairable
                    </span>
                  </td>
                  <td className="px-3 py-1.5" style={{ color: 'var(--text-muted)' }}>{gap.reason ?? '—'}</td>
                </tr>
              ))}
              {tooOldGaps.map((gap, i) => (
                <tr
                  key={`o-${i}`}
                  onMouseEnter={e => ((e.currentTarget as HTMLTableRowElement).style.background = 'color-mix(in srgb, var(--bg-hover) 20%, transparent)')}
                  onMouseLeave={e => ((e.currentTarget as HTMLTableRowElement).style.background = '')}
                >
                  <td className="px-3 py-1.5 font-mono" style={{ color: 'var(--text-primary)' }}>{gap.gapStart}</td>
                  <td className="px-3 py-1.5 font-mono" style={{ color: 'var(--text-primary)' }}>{gap.gapEnd}</td>
                  <td className="px-3 py-1.5 text-right font-medium" style={{ color: 'var(--text-primary)' }}>{gap.missingBars}</td>
                  <td className="px-3 py-1.5">
                    <span className="px-1.5 py-0.5 rounded text-xs" style={{ background: 'color-mix(in srgb, var(--accent-orange) 20%, transparent)', color: 'var(--accent-orange)' }}>
                      Too Old
                    </span>
                  </td>
                  <td className="px-3 py-1.5" style={{ color: 'var(--text-muted)' }}>
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
      <div className="rounded-lg shadow-2xl w-full max-w-5xl mx-4 max-h-[92vh] flex flex-col border" style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}>

        {/* ── Header ── */}
        <div className="flex items-center justify-between border-b px-6 py-4 flex-shrink-0" style={{ borderColor: 'var(--border)' }}>
          <div className="flex items-center gap-3">
            <span className="text-xl">🔍</span>
            <div>
              <h2 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>Data Verification</h2>
              <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                Gap detection and repair for BTCUSDT Perpetual OHLCV data across all timeframes
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="transition-colors text-xl leading-none"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-primary)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {/* ── Body ── */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">

          {/* Error */}
          {error && (
            <div className="rounded p-3 text-sm border" style={{ background: 'color-mix(in srgb, var(--accent-red) 12%, transparent)', borderColor: 'var(--accent-red-dark)', color: 'var(--accent-red)' }}>
              {error}
            </div>
          )}

          {/* Repair in-progress status */}
          {repairStatus && (
            <div className="rounded p-3 text-sm border" style={{ background: 'color-mix(in srgb, var(--accent-blue) 12%, transparent)', borderColor: 'var(--accent-blue-dark)', color: 'var(--accent-blue)' }}>
              {repairStatus}
            </div>
          )}

          {/* Summary banner */}
          {summary && (
            <div
              className="rounded-lg border px-4 py-3 text-sm font-semibold flex items-center gap-2"
              style={BANNER_INLINE_STYLES[summary.variant]}
            >
              <span>{summary.icon}</span>
              <span>{summary.text}</span>
            </div>
          )}

          {/* Idle prompt */}
          {!results && !isVerifying && (
            <div className="text-center py-12">
              <p className="text-sm mb-4" style={{ color: 'var(--text-secondary)' }}>
                Run verification to detect gaps in your stored OHLCV data.
              </p>
              <button
                onClick={handleVerify}
                className="px-5 py-2.5 rounded text-sm font-medium transition-colors"
                style={{ background: 'var(--accent-blue)', color: 'var(--btn-primary-text)' }}
              >
                Run Verification
              </button>
            </div>
          )}

          {/* Spinner */}
          {isVerifying && (
            <div className="text-center py-12">
              <div className="inline-block w-8 h-8 border-2 border-t-transparent rounded-full animate-spin mb-4" style={{ borderColor: 'var(--accent-blue)', borderTopColor: 'transparent' }} />
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Scanning data files…</p>
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
        <div className="flex items-center justify-between px-6 py-4 border-t flex-shrink-0" style={{ borderColor: 'var(--border)' }}>
          <div className="flex gap-2">
            {results && (
              <button
                onClick={handleVerify}
                disabled={isVerifying || !!isRepairing}
                className="px-4 py-2 rounded text-sm font-medium disabled:opacity-50 transition-colors"
                style={{ background: 'var(--bg-hover)', color: 'var(--text-primary)' }}
                onMouseEnter={e => (e.currentTarget.style.background = 'var(--border)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
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
                className="px-4 py-2 rounded text-sm font-medium transition-colors"
                style={{ background: 'var(--btn-confirm-bg)', color: 'var(--btn-primary-text)' }}
              >
                Fix Gaps
              </button>
            )}
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded text-sm font-medium transition-colors"
            style={{ background: 'var(--bg-hover)', color: 'var(--text-primary)' }}
            onMouseEnter={e => (e.currentTarget.style.background = 'var(--border)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default DataVerifyDialog;
