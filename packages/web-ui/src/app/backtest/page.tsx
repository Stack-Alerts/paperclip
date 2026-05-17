'use client';

import { useState, useCallback } from 'react';
import { AppLayout } from '@/components/shared/AppLayout';
import { BacktestConfigPanel } from '@/components/backtest/BacktestConfigPanel';
import type { BacktestProgress, BacktestResult } from '@/types';

export default function BacktestPage() {
  const [progress, setProgress] = useState<BacktestProgress | undefined>();
  const [result, setResult] = useState<BacktestResult | undefined>();

  const handleStart = useCallback(() => {
    setResult(undefined);
    setProgress({
      currentCandle: 0,
      totalCandles: 1000,
      currentTrade: 0,
      totalTrades: 50,
      status: 'running',
      message: 'Initializing backtest...',
    });

    const interval = setInterval(() => {
      setProgress((prev) => {
        if (!prev) return undefined;
        const next = Math.min(prev.currentCandle + 15, prev.totalCandles);
        const nextTrade = Math.min(
          prev.currentTrade + (Math.random() > 0.8 ? 1 : 0),
          prev.totalTrades
        );

        if (next === prev.totalCandles && nextTrade === prev.totalTrades) {
          clearInterval(interval);
          setResult({
            tradeCount: 47,
            winRate: 0.64,
            profitFactor: 2.1,
            maxDrawdown: -0.15,
            totalReturn: 0.25,
            sharpeRatio: 1.8,
            sortinoRatio: 2.4,
          });
          return { ...prev, currentCandle: next, currentTrade: nextTrade, status: 'completed', message: 'Backtest completed' };
        }

        return { ...prev, currentCandle: next, currentTrade: nextTrade, message: `Processing candle ${next}/${prev.totalCandles}...` };
      });
    }, 400);
  }, []);

  const handleStop = useCallback(() => {
    setProgress((prev) => (prev ? { ...prev, status: 'idle' } : undefined));
  }, []);

  return (
    <AppLayout>
      <div className="p-8">
        <div className="mb-6">
          <h2 className="text-3xl font-bold text-gray-900">Backtest</h2>
          <p className="text-gray-600 mt-1">Configure and run strategy backtests</p>
        </div>
        <BacktestConfigPanel onStart={handleStart} onStop={handleStop} progress={progress} result={result} />
      </div>
    </AppLayout>
  );
}
