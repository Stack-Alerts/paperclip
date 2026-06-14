import { redirect } from 'next/navigation';

export default function BacktestPage() {
  redirect('/strategy-builder/backtest-config');
}
