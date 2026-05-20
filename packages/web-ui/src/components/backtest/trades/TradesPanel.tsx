'use client';

export interface TradesPanelProps {
  disabled?: boolean;
}

export function TradesPanel(_props: TradesPanelProps = {}) {
  return (
    <div className="p-4" style={{ color: 'var(--text-secondary)' }}>
      Trades panel — scaffold. Owned by WebUI: Test/Optimize — Trades.
    </div>
  );
}
