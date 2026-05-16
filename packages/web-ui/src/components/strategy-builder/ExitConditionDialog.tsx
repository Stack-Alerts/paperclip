'use client';

import { useState, useCallback, useEffect } from 'react';
import { InfoTooltip } from './InfoTooltip';

export interface ExitConditionConfig {
  percentage: number;
  exitMode: 'ABSOLUTE' | 'FLEXIBLE';
  tpProximity?: number;
  reversalTrigger?: number;
  recheckEnabled?: boolean;
  recheckBarDelay?: number;
}

export interface ExitConditionDialogProps {
  open: boolean;
  signalName?: string;
  existingConfig?: ExitConditionConfig;
  onSave: (config: ExitConditionConfig) => void;
  onClose: () => void;
}

export function ExitConditionDialog({
  open,
  signalName,
  existingConfig,
  onSave,
  onClose,
}: ExitConditionDialogProps) {
  const [percentage, setPercentage] = useState(50);
  const [exitMode, setExitMode] = useState<'ABSOLUTE' | 'FLEXIBLE'>('ABSOLUTE');
  const [tpProximity, setTpProximity] = useState(2.0);
  const [reversalTrigger, setReversalTrigger] = useState(0.5);
  const [recheckEnabled, setRecheckEnabled] = useState(false);
  const [recheckBarDelay, setRecheckBarDelay] = useState(3);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open && existingConfig) {
      setPercentage(existingConfig.percentage);
      setExitMode(existingConfig.exitMode);
      setTpProximity(existingConfig.tpProximity ?? 2.0);
      setReversalTrigger(existingConfig.reversalTrigger ?? 0.5);
      setRecheckEnabled(existingConfig.recheckEnabled ?? false);
      setRecheckBarDelay(existingConfig.recheckBarDelay ?? 3);
      setError(null);
    }
  }, [open, existingConfig]);

  const handleSave = useCallback(() => {
    if (percentage < 1 || percentage > 100) {
      setError('Percentage must be between 1 and 100.');
      return;
    }
    setError(null);
    onSave({
      percentage,
      exitMode,
      tpProximity,
      reversalTrigger,
      recheckEnabled,
      recheckBarDelay,
    });
    onClose();
  }, [percentage, exitMode, tpProximity, reversalTrigger, recheckEnabled, recheckBarDelay, onSave, onClose]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    },
    [onClose],
  );

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="exit-condition-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
      onKeyDown={handleKeyDown}
    >
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      <div className="relative w-full max-w-lg rounded-lg border border-zinc-700 bg-zinc-900 shadow-2xl mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800">
          <h2 id="exit-condition-title" className="text-base font-semibold text-zinc-50">
            🚪 Exit Condition
            {signalName && <span className="text-zinc-400 ml-2 font-normal">({signalName})</span>}
          </h2>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300 text-lg" aria-label="Close dialog">
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-5">
          {/* Percentage */}
          <div className="space-y-1.5">
            <label htmlFor="exit-percentage" className="text-xs font-medium text-zinc-400 uppercase tracking-wide">
              Exit Percentage (%) <span className="text-red-400">*</span>
            </label>
            <InfoTooltip id="exit-percentage-input">
              <input
                id="exit-percentage"
                type="number"
                min={1}
                max={100}
                value={percentage}
                onChange={(e) => { setPercentage(parseFloat(e.target.value)); setError(null); }}
                className={`w-full px-3 py-2 rounded bg-zinc-800 border text-sm text-zinc-100 focus:outline-none ${
                  error ? 'border-red-600 focus:border-red-500' : 'border-zinc-700 focus:border-zinc-500'
                }`}
              />
            </InfoTooltip>
            <p className="text-xs text-zinc-500">Percentage of position to exit (1–100%)</p>
            {error && <p className="text-xs text-red-400">{error}</p>}
          </div>

          {/* Exit Mode */}
          <div className="space-y-2">
            <p className="text-xs font-medium text-zinc-400 uppercase tracking-wide">Exit Mode</p>
            <div className="space-y-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="exit-mode"
                  checked={exitMode === 'ABSOLUTE'}
                  onChange={() => setExitMode('ABSOLUTE')}
                  className="w-4 h-4"
                />
                <span className="text-sm text-zinc-100">ABSOLUTE</span>
              </label>
              <p className="text-xs text-zinc-500 ml-6">Exit immediately at fixed price</p>

              <label className="flex items-center gap-2 cursor-pointer mt-3">
                <input
                  type="radio"
                  name="exit-mode"
                  checked={exitMode === 'FLEXIBLE'}
                  onChange={() => setExitMode('FLEXIBLE')}
                  className="w-4 h-4"
                />
                <span className="text-sm text-zinc-100">FLEXIBLE</span>
              </label>
              <p className="text-xs text-zinc-500 ml-6">Dynamic exit based on market conditions</p>
            </div>
          </div>

          {/* Flexible Mode Parameters */}
          {exitMode === 'FLEXIBLE' && (
            <div className="rounded border border-zinc-700 bg-zinc-800/50 p-3 space-y-3">
              <div className="space-y-1.5">
                <label htmlFor="tp-proximity" className="text-xs text-zinc-400 font-medium">
                  TP Proximity (%)
                </label>
                <InfoTooltip id="exit-tp-proximity">
                  <input
                    id="tp-proximity"
                    type="number"
                    step={0.1}
                    value={tpProximity}
                    onChange={(e) => setTpProximity(parseFloat(e.target.value))}
                    className="w-full px-3 py-2 rounded bg-zinc-700 border border-zinc-600 text-sm text-zinc-100 focus:outline-none focus:border-zinc-500"
                  />
                </InfoTooltip>
              </div>
              <div className="space-y-1.5">
                <label htmlFor="reversal-trigger" className="text-xs text-zinc-400 font-medium">
                  Reversal Trigger (%)
                </label>
                <InfoTooltip id="exit-reversal-trigger">
                  <input
                    id="reversal-trigger"
                    type="number"
                    step={0.01}
                    value={reversalTrigger}
                    onChange={(e) => setReversalTrigger(parseFloat(e.target.value))}
                    className="w-full px-3 py-2 rounded bg-zinc-700 border border-zinc-600 text-sm text-zinc-100 focus:outline-none focus:border-zinc-500"
                  />
                </InfoTooltip>
              </div>
            </div>
          )}

          {/* Recheck */}
          <div className="space-y-2 rounded border border-zinc-700 bg-zinc-800/50 p-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={recheckEnabled}
                onChange={(e) => setRecheckEnabled(e.target.checked)}
                className="w-4 h-4"
              />
              <span className="text-sm text-zinc-100">Enable RECHECK validation</span>
            </label>
            {recheckEnabled && (
              <div className="space-y-1.5 ml-6">
                <label htmlFor="recheck-delay" className="text-xs text-zinc-400 font-medium">
                  Bar Delay
                </label>
                <InfoTooltip id="exit-recheck-delay">
                  <input
                    id="recheck-delay"
                    type="number"
                    min={1}
                    value={recheckBarDelay}
                    onChange={(e) => setRecheckBarDelay(parseInt(e.target.value))}
                    className="w-full px-3 py-2 rounded bg-zinc-700 border border-zinc-600 text-sm text-zinc-100 focus:outline-none focus:border-zinc-500"
                  />
                </InfoTooltip>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 px-6 py-4 border-t border-zinc-800">
          <InfoTooltip id="exit-condition-cancel-btn">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded bg-zinc-700 hover:bg-zinc-600 text-zinc-200 text-sm font-medium transition-colors"
            >
              Cancel
            </button>
          </InfoTooltip>
          <InfoTooltip id="exit-condition-save-btn">
            <button
              onClick={handleSave}
              className="px-4 py-2 rounded bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors"
            >
              Save Exit Condition
            </button>
          </InfoTooltip>
        </div>
      </div>
    </div>
  );
}
