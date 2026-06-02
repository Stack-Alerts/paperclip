'use client';

import React, { useState, useCallback, useMemo } from 'react';

const SUGGESTED_MARKETS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'];

export interface MissingTargetMarketFixDialogProps {
  onConfirm: (value: string) => void;
  onCancel: () => void;
}

export const MissingTargetMarketFixDialog: React.FC<MissingTargetMarketFixDialogProps> = ({
  onConfirm,
  onCancel,
}) => {
  const [customMarket, setCustomMarket] = useState<string>('');
  const [selectedSuggestion, setSelectedSuggestion] = useState<string | null>(null);

  const isValid = useMemo(() => {
    const market = selectedSuggestion || customMarket.trim();
    if (!market) return false;
    // Validate BASE/QUOTE format: uppercase letters/digits separated by /
    return /^[A-Z0-9]+\/[A-Z0-9]+$/.test(market);
  }, [selectedSuggestion, customMarket]);

  const currentValue = selectedSuggestion || customMarket;

  const handleConfirm = useCallback(() => {
    if (isValid) {
      onConfirm(currentValue);
    }
  }, [currentValue, isValid, onConfirm]);

  const handleSuggestionClick = useCallback((market: string) => {
    setSelectedSuggestion(market);
    setCustomMarket('');
  }, []);

  const handleCustomChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setCustomMarket(e.target.value.toUpperCase());
    setSelectedSuggestion(null);
  }, []);

  return (
    <div className="space-y-4">
      {/* Description */}
      <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
        Specify the trading pair for your strategy. Use the format BASE/QUOTE (e.g., BTC/USDT).
      </p>

      {/* Suggested markets */}
      <div className="rounded-lg px-5 py-4 space-y-3 border" style={{ borderColor: 'var(--border)', background: 'color-mix(in srgb, var(--bg-card) 30%, transparent)' }}>
        <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
          📊 Popular Markets
        </p>
        <div className="flex gap-2 flex-wrap">
          {SUGGESTED_MARKETS.map((market) => (
            <button
              key={market}
              onClick={() => handleSuggestionClick(market)}
              className="px-3 py-1.5 rounded text-sm font-medium transition-colors"
              style={{
                background: selectedSuggestion === market ? 'var(--accent-blue)' : 'var(--bg-hover)',
                color: selectedSuggestion === market ? 'var(--btn-primary-text)' : 'var(--text-secondary)',
                border: `1px solid ${selectedSuggestion === market ? 'var(--accent-blue)' : 'var(--border)'}`,
                cursor: 'pointer',
              }}
            >
              {market}
            </button>
          ))}
        </div>
      </div>

      {/* Custom input */}
      <div className="space-y-2">
        <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)' }}>
          Or enter a custom pair:
        </label>
        <input
          type="text"
          placeholder="e.g., BTC/USDT"
          value={customMarket}
          onChange={handleCustomChange}
          className="w-full px-3 py-2 rounded border text-sm font-mono"
          style={{
            borderColor: customMarket && !isValid ? 'var(--accent-red)' : 'var(--border)',
            background: 'var(--bg-card)',
            color: 'var(--text-secondary)',
            outline: 'none',
          }}
          onFocus={e => {
            e.currentTarget.style.borderColor = customMarket && !isValid ? 'var(--accent-red)' : 'var(--accent-blue)';
          }}
          onBlur={e => {
            e.currentTarget.style.borderColor = customMarket && !isValid ? 'var(--accent-red)' : 'var(--border)';
          }}
        />
        {customMarket && !isValid && (
          <p style={{ fontSize: '11px', color: 'var(--accent-red)' }}>
            Please use the format BASE/QUOTE with uppercase letters (e.g., BTC/USDT)
          </p>
        )}
      </div>

      {/* Impact note */}
      <div className="rounded-r px-4 py-3" style={{ borderLeft: '4px solid var(--accent-blue)', background: 'color-mix(in srgb, var(--bg-deep) 60%, transparent)' }}>
        <p className="text-xs font-semibold uppercase tracking-wider mb-1.5" style={{ color: 'var(--accent-blue)' }}>
          💡 Impact
        </p>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          Setting target market to {currentValue || 'your chosen pair'} allows the strategy to validate and backtest against the correct asset pair.
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
          disabled={!isValid}
          className="px-4 py-2 rounded text-sm font-medium transition-colors"
          style={{
            background: isValid ? 'var(--accent-blue)' : 'var(--bg-hover)',
            color: isValid ? 'var(--btn-primary-text)' : 'var(--text-muted)',
            cursor: isValid ? 'pointer' : 'not-allowed',
            opacity: isValid ? 1 : 0.6,
          }}
        >
          ✅ Set Market
        </button>
      </div>
    </div>
  );
};

export default MissingTargetMarketFixDialog;
