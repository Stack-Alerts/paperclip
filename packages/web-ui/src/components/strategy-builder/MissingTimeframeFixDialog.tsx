'use client';

import React, { useState, useCallback } from 'react';

const CANONICAL_TIMEFRAMES = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w'];

export interface MissingTimeframeFixDialogProps {
  onConfirm: (value: string) => void;
  onCancel: () => void;
}

export const MissingTimeframeFixDialog: React.FC<MissingTimeframeFixDialogProps> = ({
  onConfirm,
  onCancel,
}) => {
  const [selectedTimeframe, setSelectedTimeframe] = useState<string>('1h');

  const handleConfirm = useCallback(() => {
    onConfirm(selectedTimeframe);
  }, [selectedTimeframe, onConfirm]);

  return (
    <div className="space-y-4">
      {/* Description */}
      <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
        Select the timeframe for your strategy. This determines the candle interval used for signal evaluation.
      </p>

      {/* Timeframe selector */}
      <div className="rounded-lg px-5 py-4 space-y-3 border" style={{ borderColor: 'var(--border)', background: 'color-mix(in srgb, var(--bg-card) 30%, transparent)' }}>
        <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
          ⏱️ Select Timeframe
        </p>
        <div className="grid grid-cols-4 gap-2">
          {CANONICAL_TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              onClick={() => setSelectedTimeframe(tf)}
              className="px-3 py-2 rounded text-sm font-medium transition-colors text-center"
              style={{
                background: selectedTimeframe === tf ? 'var(--accent-blue)' : 'var(--bg-hover)',
                color: selectedTimeframe === tf ? 'var(--btn-primary-text)' : 'var(--text-secondary)',
                border: `1px solid ${selectedTimeframe === tf ? 'var(--accent-blue)' : 'var(--border)'}`,
                cursor: 'pointer',
              }}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* Impact note */}
      <div className="rounded-r px-4 py-3" style={{ borderLeft: '4px solid var(--accent-blue)', background: 'color-mix(in srgb, var(--bg-deep) 60%, transparent)' }}>
        <p className="text-xs font-semibold uppercase tracking-wider mb-1.5" style={{ color: 'var(--accent-blue)' }}>
          💡 Impact
        </p>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          Setting timeframe to {selectedTimeframe} will allow timing-based blocks and signal evaluations to work correctly with {selectedTimeframe} candles.
        </p>
      </div>

      {/* Buttons */}
      <div className="flex justify-end gap-2 pt-2">
        <button
          onClick={onCancel}
          className="px-4 py-2 rounded text-sm font-medium transition-colors"
          style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
          onMouseEnter={e => (e.currentTarget.style.background = 'var(--border)')}
          onMouseLeave={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
        >
          Cancel
        </button>
        <button
          onClick={handleConfirm}
          className="px-4 py-2 rounded text-sm font-medium transition-colors"
          style={{ background: 'var(--accent-blue)', color: 'var(--btn-primary-text)' }}
        >
          ✅ Set Timeframe
        </button>
      </div>
    </div>
  );
};

export default MissingTimeframeFixDialog;
