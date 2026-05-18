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
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl w-full max-w-2xl mx-4">

        {/* ── Header ── */}
        <div className="flex items-center gap-3 border-b border-zinc-700 px-6 py-4">
          <span className="text-xl">⏱</span>
          <div>
            <h2 className="text-base font-semibold text-zinc-100">Timing Constraint</h2>
            <p className="text-xs text-zinc-400">
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
              className="w-4 h-4 rounded border-zinc-600 bg-zinc-800 text-blue-500 focus:ring-blue-500 cursor-pointer"
            />
            <label
              htmlFor="tc-enabled"
              className="text-sm font-semibold text-zinc-200 cursor-pointer"
            >
              Enable timing constraint
            </label>
          </div>

          {/* Settings group */}
          <div
            className={`border border-zinc-700 rounded-lg px-5 py-4 space-y-4 transition-opacity ${
              enabled ? '' : 'opacity-40 pointer-events-none'
            }`}
          >
            <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
              Timing Constraint Settings
            </p>

            {/* Candle count */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-300">
                Maximum candles from reference
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="number"
                  min={1}
                  max={1000}
                  value={candleCount}
                  onChange={handleCandleChange}
                  className="w-28 bg-zinc-800 border border-zinc-600 rounded px-3 py-2 text-zinc-100 text-sm focus:outline-none focus:border-blue-500"
                />
                <span className="text-sm text-zinc-400">candles</span>
              </div>
            </div>

            {/* Reference signal */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-300">Reference signal</label>
              {hasReferences ? (
                <>
                  <select
                    value={referenceId}
                    onChange={(e) => setReferenceId(e.target.value)}
                    className="w-full bg-zinc-800 border border-zinc-600 rounded px-3 py-2 text-zinc-100 text-sm focus:outline-none focus:border-blue-500"
                  >
                    {availableReferences.map((ref) => (
                      <option key={ref.referenceId} value={ref.referenceId}>
                        {ref.displayName}
                      </option>
                    ))}
                  </select>
                  {referenceStale && (
                    <p className="text-xs text-amber-400 mt-1">
                      ⚠️ The previously selected reference no longer exists in the current blocks.
                      Please choose a new reference.
                    </p>
                  )}
                </>
              ) : (
                <div className="flex items-center gap-2">
                  <select
                    disabled
                    className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-zinc-500 text-sm opacity-60 cursor-not-allowed"
                  >
                    <option>(No previous signals available)</option>
                  </select>
                </div>
              )}
            </div>
          </div>

          {/* Example group box */}
          <div className="border border-zinc-700 rounded-lg px-5 py-4 bg-zinc-800/30">
            <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
              Example
            </p>
            <p className="text-sm text-zinc-400 italic whitespace-pre-line leading-relaxed">
              {exampleText}
            </p>
          </div>
        </div>

        {/* ── Footer ── */}
        <div className="flex justify-end gap-2 px-6 py-4 border-t border-zinc-700">
          <button
            onClick={onCancel}
            className="px-4 py-2 rounded bg-zinc-700 text-zinc-200 text-sm font-medium hover:bg-zinc-600 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 rounded bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            Save Constraint
          </button>
        </div>
      </div>
    </div>
  );
};

export default TimingConstraintDialog;
