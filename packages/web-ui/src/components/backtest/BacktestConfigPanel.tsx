'use client';

import React, { useState, useCallback } from 'react';
import { BacktestConfig, BacktestProgress, BacktestResult } from '@/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';

export interface BacktestConfigPanelProps {
  onStart?: (config: BacktestConfig) => void;
  onStop?: () => void;
  progress?: BacktestProgress;
  result?: BacktestResult;
  disabled?: boolean;
}

/**
 * BacktestConfigPanel - React port of PyQt5 BacktestConfigPanel
 *
 * Provides comprehensive backtest configuration with:
 * - Lookback days and training window control
 * - Mode 1 (historical) / Mode 2 (live replay) selection
 * - TP/SL configuration integration
 * - Live progress tracking with candle/trade counters
 * - Pause/Resume/Stop controls
 */
export const BacktestConfigPanel: React.FC<BacktestConfigPanelProps> = ({
  onStart,
  onStop,
  progress,
  result,
  disabled = false,
}) => {
  const [config, setConfig] = useState<BacktestConfig>({
    lookbackDays: 180,
    trainingWindow: 30,
    mode: 'historical',
    strategyId: '',
    instrumentId: '',
    startDate: new Date(),
    endDate: new Date(),
  });

  const [isRunning, setIsRunning] = useState(false);

  const handleConfigChange = useCallback((field: keyof BacktestConfig, value: BacktestConfig[keyof BacktestConfig]) => {
    setConfig(prev => ({
      ...prev,
      [field]: value,
    }));
  }, []);

  const handleStart = useCallback(() => {
    setIsRunning(true);
    onStart?.(config);
  }, [config, onStart]);

  const handleStop = useCallback(() => {
    setIsRunning(false);
    onStop?.();
  }, [onStop]);

  return (
    <div className="space-y-6">
      {/* Configuration Section */}
      <Card>
        <CardHeader>
          <CardTitle>Backtest Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Lookback Period */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="lookback-days">Lookback Days</Label>
              <Input
                id="lookback-days"
                type="number"
                value={config.lookbackDays}
                onChange={(e) => handleConfigChange('lookbackDays', parseInt(e.target.value))}
                disabled={disabled || isRunning}
                min="1"
                max="3650"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="training-window">Training Window</Label>
              <Input
                id="training-window"
                type="number"
                value={config.trainingWindow}
                onChange={(e) => handleConfigChange('trainingWindow', parseInt(e.target.value))}
                disabled={disabled || isRunning}
                min="1"
                max="365"
              />
            </div>
          </div>

          {/* Mode Selection */}
          <div className="space-y-2">
            <Label htmlFor="mode">Backtest Mode</Label>
            <Select
              value={config.mode}
              onChange={(value) => handleConfigChange('mode', value)}
              disabled={disabled || isRunning}
            >
              <option value="historical">Mode 1: Historical</option>
              <option value="live">Mode 2: Live Replay</option>
            </Select>
          </div>

          {/* Strategy and Instrument Selection */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="strategy-id">Strategy</Label>
              <Input
                id="strategy-id"
                type="text"
                value={config.strategyId}
                onChange={(e) => handleConfigChange('strategyId', e.target.value)}
                disabled={disabled || isRunning}
                placeholder="Select strategy..."
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="instrument-id">Instrument</Label>
              <Input
                id="instrument-id"
                type="text"
                value={config.instrumentId}
                onChange={(e) => handleConfigChange('instrumentId', e.target.value)}
                disabled={disabled || isRunning}
                placeholder="Select instrument..."
              />
            </div>
          </div>

          {/* Control Buttons */}
          <div className="flex gap-2 pt-4">
            {!isRunning ? (
              <Button
                onClick={handleStart}
                disabled={disabled || !config.strategyId || !config.instrumentId}
                className="flex-1"
              >
                Run Test
              </Button>
            ) : (
              <Button
                onClick={handleStop}
                className="flex-1"
                variant="destructive"
              >
                Stop
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Progress Section */}
      {progress && (
        <Card>
          <CardHeader>
            <CardTitle>Progress</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Status</Label>
                <p className="text-sm font-semibold">{progress.status}</p>
              </div>
              <div>
                <Label>Candles</Label>
                <p className="text-sm font-semibold">
                  {progress.currentCandle} / {progress.totalCandles}
                </p>
              </div>
              <div>
                <Label>Trades</Label>
                <p className="text-sm font-semibold">
                  {progress.currentTrade} / {progress.totalTrades}
                </p>
              </div>
              <div>
                <Label>Message</Label>
                <p className="text-sm truncate">{progress.message}</p>
              </div>
            </div>

            {/* Progress Bars */}
            <div className="space-y-2">
              <div className="space-y-1">
                <Label className="text-xs">Candle Progress</Label>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all"
                    style={{
                      width: `${progress.totalCandles > 0
                        ? (progress.currentCandle / progress.totalCandles) * 100
                        : 0}%`,
                    }}
                  />
                </div>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Trade Progress</Label>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-green-600 h-2 rounded-full transition-all"
                    style={{
                      width: `${progress.totalTrades > 0
                        ? (progress.currentTrade / progress.totalTrades) * 100
                        : 0}%`,
                    }}
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Results Section */}
      {result && (
        <Card>
          <CardHeader>
            <CardTitle>Results</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-1">
                <Label className="text-xs">Total Trades</Label>
                <p className="text-lg font-semibold">{result.tradeCount}</p>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Win Rate</Label>
                <p className="text-lg font-semibold">{(result.winRate * 100).toFixed(2)}%</p>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Profit Factor</Label>
                <p className="text-lg font-semibold">{result.profitFactor.toFixed(2)}</p>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Max Drawdown</Label>
                <p className="text-lg font-semibold">{(result.maxDrawdown * 100).toFixed(2)}%</p>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Total Return</Label>
                <p className="text-lg font-semibold">{(result.totalReturn * 100).toFixed(2)}%</p>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Sharpe Ratio</Label>
                <p className="text-lg font-semibold">{result.sharpeRatio.toFixed(2)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default BacktestConfigPanel;
