'use client';

import React, { useState, useCallback } from 'react';

export interface TimingConstraint {
  enabled: boolean;
  candleCount: number;
  referenceId: string;
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

  if (prevOpen !== open && open) {
    setPrevOpen(open);
    if (currentConstraint) {
      setEnabled(currentConstraint.enabled);
      setCandleCount(currentConstraint.candleCount);
      setReferenceId(currentConstraint.referenceId);
    } else {
      setEnabled(false);
      setCandleCount(3);
      setReferenceId(availableReferences[0]?.referenceId ?? '');
    }
  } else if (prevOpen !== open) {
    setPrevOpen(open);
  }

  const handleSave = useCallback(() => {
    onSave({ enabled, candleCount, referenceId });
  }, [enabled, candleCount, referenceId, onSave]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl w-full max-w-md mx-4">
        <div className="flex items-center gap-3 border-b border-zinc-700 px-6 py-4">
          <span className="text-xl">⏱</span>
          <div>
            <h2 className="text-base font-semibold text-zinc-100">Timing Constraint</h2>
            <p className="text-xs text-zinc-400">
              {blockName} › {signalName}
            </p>
          </div>
        </div>

        <div className="px-6 py-5 space-y-5">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="tc-enabled"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
              className="w-4 h-4 rounded border-zinc-600 bg-zinc-800 text-blue-500 focus:ring-blue-500"
            />
            <label htmlFor="tc-enabled" className="text-sm font-medium text-zinc-200">
              Enable timing constraint
            </label>
          </div>

          <div className={`space-y-4 transition-opacity ${enabled ? '' : 'opacity-40 pointer-events-none'}`}>
            <div className="space-y-2">
              <label className="text-xs font-medium text-zinc-300">
                Within candles from reference
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="number"
                  min={1}
                  max={999}
                  value={candleCount}
                  onChange={(e) => setCandleCount(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-24 bg-zinc-800 border border-zinc-600 rounded px-3 py-2 text-zinc-100 text-sm focus:outline-none focus:border-blue-500"
                />
                <span className="text-sm text-zinc-400">candles</span>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-medium text-zinc-300">Reference Signal</label>
              {availableReferences.length > 0 ? (
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
              ) : (
                <p className="text-xs text-zinc-500">No reference signals available</p>
              )}
            </div>
          </div>
        </div>

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
