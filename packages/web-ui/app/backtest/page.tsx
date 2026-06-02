'use client';

import { BacktestWindow } from '@/components/backtest/BacktestWindow';
import { useState } from 'react';
import { BacktestConfig, BacktestProgress } from '@/types';
import { BacktestResult } from '@/lib/strategy-builder/types';

export default function BacktestPage() {
  const [progress, setProgress] = useState<BacktestProgress | undefined>();
  const [result, setResult] = useState<BacktestResult | undefined>();
  const [isRunning, setIsRunning] = useState(false);

  const handleStart = (config: BacktestConfig) => {
    console.log('Starting backtest with config:', config);
    setIsRunning(true);
  };

  const handleStop = () => {
    console.log('Stopping backtest');
    setIsRunning(false);
  };

  return (
    <div className="flex-1 overflow-y-auto p-6" style={{ background: 'var(--app-bg)' }}>
      <BacktestWindow
        progress={progress}
        result={result}
        isRunning={isRunning}
        onStart={handleStart}
        onStop={handleStop}
      />
    </div>
  );
}
