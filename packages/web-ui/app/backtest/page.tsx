import { BacktestConfigPanel } from '@/components/backtest/BacktestConfigPanel';

export default function BacktestPage() {
  return (
    <div className="flex-1 overflow-y-auto p-6 bg-zinc-950">
      <h1 className="text-xl font-semibold text-zinc-100 mb-6">Backtest</h1>
      <BacktestConfigPanel />
    </div>
  );
}
