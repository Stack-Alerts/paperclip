'use client';

import React, { useState, useCallback } from 'react';

export interface TimingConstraint {
  enabled: boolean;
  candleCount: number;
  referenceId: string;
  referenceName: string;
}

export interface TimingConstraintDialogProps {
  open: boolean;
  blockName: string;
  signalName: string;
  availableReferences: { displayName: string; referenceId: string }[];
  currentConstraint?: TimingConstraint | null;
  onSave: (constraint: TimingConstraint) => void;
  onCancel: () => void;
}

// ─── Example text generator ───────────────────────────────────────────────────

function buildExampleText(
  enabled: boolean,
  candleCount: number,
  referenceName: string,
  hasReferences: boolean
): string {
  if (!enabled) {
    return 'No timing constraint. This signal can trigger at any time regardless of other signals.';
  }
  if (!hasReferences) {
    return 'Cannot configure timing constraint without a reference signal.';
  }
  return (
    `This signal must trigger within ${candleCount} candle(s) of "${referenceName}".\n\n` +
    `If more than ${candleCount} candle(s) pass after "${referenceName}" fires without this ` +
    `signal also firing, the entire strategy resets and starts counting from scratch.\n\n` +
    `Example: if "${referenceName}" fires on candle #100, this signal must fire by candle ` +
    `#${100 + candleCount} at the latest.`
  );
}

// ─── Dialog ──────────────────────────────────────────────────────────────────

export const TimingConstraintDialog: React.FC<TimingConstraintDialogProps> = ({
  open,
  blockName,
  signalName,
  availableReferences,
  currentConstraint,
  onSave,
  onCancel,
}) => {
  const [enabled, setEnabled] = useState(false);
  const [candleCount, setCandleCount] = useState(3);
  const [referenceId, setReferenceId] = useState('');
  const [prevOpen, setPrevOpen] = useState(open);

  // Sync state when dialog opens
  if (prevOpen !== open && open) {
    setPrevOpen(open);
    if (currentConstraint) {
      setEnabled(currentConstraint.enabled);
      setCandleCount(currentConstraint.candleCount);
      setReferenceId(currentConstraint.referenceId);
    } else {
      setEnabled(false);
      setCandleCount(5);
      setReferenceId(availableReferences[0]?.referenceId ?? '');
    }
  } else if (prevOpen !== open) {
    setPrevOpen(open);
  }

  const hasReferences = availableReferences.length > 0;

  const selectedRef =
    availableReferences.find((r) => r.referenceId === referenceId) ?? availableReferences[0];

  // Warn if selected referenceId no longer exists in blocks
  const referenceStale =
    enabled && hasReferences && referenceId !== '' &&
    !availableReferences.some((r) => r.referenceId === referenceId);

  const handleSave = useCallback(() => {
    onSave({ enabled, candleCount, referenceId, referenceName: selectedRef?.displayName ?? '' });
  }, [enabled, candleCount, referenceId, selectedRef, onSave]);

  const handleCandleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseInt(e.target.value, 10);
    setCandleCount(Math.min(1000, Math.max(1, isNaN(val) ? 1 : val)));
  }, []);

  if (!open) return null;

  const exampleText = buildExampleText(
    enabled,
    candleCount,
    selectedRef?.displayName ?? '',
    hasReferences
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="rounded-lg shadow-2xl w-full max-w-2xl mx-4 border" style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}>

        {/* ── Header ── */}
        <div className="flex items-center gap-3 border-b px-6 py-4" style={{ borderColor: 'var(--border)' }}>
          <span className="text-xl">⏱</span>
          <div>
            <h2 className="text-base font-semibold" style={{ color: 'var(--text-secondary)' }}>Timing Constraint</h2>
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
              {blockName} › {signalName}
            </p>
          </div>
        </div>

        {/* ── Body ── */}
        <div className="px-6 py-5 space-y-5">

          {/* Enable toggle */}
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="tc-enabled"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
              className="w-4 h-4 rounded cursor-pointer"
              style={{ accentColor: 'var(--accent-blue)' }}
            />
            <label
              htmlFor="tc-enabled"
              className="text-sm font-semibold cursor-pointer"
              style={{ color: 'var(--text-primary)' }}
            >
              Enable timing constraint
            </label>
          </div>

          {/* Settings group */}
          <div
            className={`rounded-lg px-5 py-4 space-y-4 transition-opacity border ${
              enabled ? '' : 'opacity-40 pointer-events-none'
            }`}
            style={{ borderColor: 'var(--border)' }}
          >
            <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
              Timing Constraint Settings
            </p>

            {/* Candle count */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                Maximum candles from reference
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="number"
                  min={1}
                  max={1000}
                  value={candleCount}
                  onChange={handleCandleChange}
                  className="w-28 rounded px-3 py-2 text-sm focus:outline-none"
                  style={{ background: 'var(--input-bg)', border: '1px solid var(--input-border)', color: 'var(--input-text)' }}
                />
                <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>candles</span>
              </div>
            </div>

            {/* Reference signal */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Reference signal</label>
              {hasReferences ? (
                <>
                  <select
                    value={referenceId}
                    onChange={(e) => setReferenceId(e.target.value)}
                    className="w-full rounded px-3 py-2 text-sm focus:outline-none"
                    style={{ background: 'var(--input-bg)', border: '1px solid var(--input-border)', color: 'var(--input-text)' }}
                  >
                    {availableReferences.map((ref) => (
                      <option key={ref.referenceId} value={ref.referenceId}>
                        {ref.displayName}
                      </option>
                    ))}
                  </select>
                  {referenceStale && (
                    <p className="text-xs mt-1" style={{ color: 'var(--accent-orange)' }}>
                      ⚠️ The previously selected reference no longer exists in the current blocks.
                      Please choose a new reference.
                    </p>
                  )}
                </>
              ) : (
                <div className="flex items-center gap-2">
                  <select
                    disabled
                    className="w-full rounded px-3 py-2 text-sm opacity-60 cursor-not-allowed"
                    style={{ background: 'var(--input-bg)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}
                  >
                    <option>(No previous signals available)</option>
                  </select>
                </div>
              )}
            </div>
          </div>

          {/* Example group box */}
          <div className="rounded-lg px-5 py-4 border" style={{ borderColor: 'var(--border)', background: 'var(--bg-card)' }}>
            <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--text-secondary)' }}>
              Example
            </p>
            <p className="text-sm italic whitespace-pre-line leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
              {exampleText}
            </p>
          </div>
        </div>

        {/* ── Footer ── */}
        <div className="flex justify-end gap-2 px-6 py-4 border-t" style={{ borderColor: 'var(--border)' }}>
          <button
            onClick={onCancel}
            className="px-4 py-2 rounded text-sm font-medium transition-colors"
            style={{ background: 'var(--bg-hover)', color: 'var(--text-primary)' }}
            onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-card)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 rounded text-sm font-medium transition-colors"
            style={{ background: 'var(--accent-blue)', color: 'var(--btn-primary-text)' }}
            onMouseEnter={e => (e.currentTarget.style.background = 'var(--accent-blue-mid)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'var(--accent-blue)')}
          >
            Save Constraint
          </button>
        </div>
      </div>
    </div>
  );
};

export default TimingConstraintDialog;
