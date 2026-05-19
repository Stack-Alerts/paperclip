import { BacktestConfigPanel } from '@/components/backtest/BacktestConfigPanel';

export default function BacktestPage() {
  return (
    <div className="flex-1 overflow-y-auto p-6" style={{ background: 'var(--app-bg)' }}>
      <h1 className="text-xl font-semibold mb-6" style={{ color: 'var(--text-primary)' }}>Backtest</h1>
      <BacktestConfigPanel />
    </div>
  );
}
