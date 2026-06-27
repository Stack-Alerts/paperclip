/**
 * Storybook entries for CollapsibleSection (BTCAAAAA-38568 / Sprint B7).
 * Covers: default open, default closed, copyText prop, no copyText.
 */
'use client';

import { CollapsibleSection, PreviewText } from './CollapsibleSection';

const meta = {
  title: 'AI Recommendations / CollapsibleSection',
  component: CollapsibleSection,
};
export default meta;

export function DefaultOpen() {
  return (
    <div style={{ maxWidth: 640, padding: 16, background: 'var(--bg-base)' }}>
      <CollapsibleSection
        title="Strategy Parameters"
        description="3 items"
        defaultOpen
        copyText={'stopLoss: 0.030\nrsiPeriod: 14\ncooldown: 4'}
      >
        <PreviewText text={'stopLoss: 0.030\nrsiPeriod: 14\ncooldown: 4'} />
      </CollapsibleSection>
    </div>
  );
}

export function DefaultClosed() {
  return (
    <div style={{ maxWidth: 640, padding: 16, background: 'var(--bg-base)' }}>
      <CollapsibleSection
        title="Backtest Results"
        description="summary"
        defaultOpen={false}
        copyText={'winRate: 0.62\nprofitFactor: 1.42'}
      >
        <PreviewText text={'winRate: 0.62\nprofitFactor: 1.42'} />
      </CollapsibleSection>
    </div>
  );
}

export function NoCopyButton() {
  return (
    <div style={{ maxWidth: 640, padding: 16, background: 'var(--bg-base)' }}>
      <CollapsibleSection
        title="Building Blocks"
        description="read-only"
        defaultOpen
      >
        <PreviewText text={'RSI\nMACD\nBollingerBands'} />
      </CollapsibleSection>
    </div>
  );
}

export function AllFiveSections() {
  const sections = [
    { title: '1. Strategy Parameters', desc: '5 params', text: 'stopLoss: 0.030\nrsiPeriod: 14\ncooldown: 4\ntakeProfit: 0.063\ntrailAtr: 1.5' },
    { title: '2. Backtest Results', desc: 'summary', text: 'winRate: 0.62\nprofitFactor: 1.42\nmaxDrawdown: 0.18' },
    { title: '3. Recent Trades', desc: '5 trades', text: 'BTC/USDT +2.1%\nBTC/USDT -0.8%\nBTC/USDT +3.4%\nBTC/USDT +1.2%\nBTC/USDT -1.1%' },
    { title: '4. Performance Metrics', desc: '4 metrics', text: 'entries: 84\nnetLiquidity: 3450\nsharpe: 1.8\ncalmar: 2.1' },
    { title: '5. Available Building Blocks', desc: '8 blocks', text: 'RSI\nMACD\nBollingerBands\nATR\nEMA\nSMA\nVWAP\nOBV' },
  ];
  return (
    <div style={{ maxWidth: 640, padding: 16, background: 'var(--bg-base)' }}>
      {sections.map((s) => (
        <CollapsibleSection key={s.title} title={s.title} description={s.desc} defaultOpen copyText={s.text}>
          <PreviewText text={s.text} />
        </CollapsibleSection>
      ))}
    </div>
  );
}
