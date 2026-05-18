'use client';

import React, { useState, useCallback } from 'react';
import { BacktestConfigPanel } from '@/components/backtest/BacktestConfigPanel';
import { DataManagementPanel } from '@/components/data-management/DataManagementPanel';
import { LogViewerPanel } from '@/components/log-viewer/LogViewerPanel';
import { SettingsPanel } from '@/components/settings/SettingsPanel';
import {
  LogLevel,
} from '@/types';
import type {
  BacktestProgress,
  BacktestResult,
  DataSource,
  DataVerificationResult,
  LogEntry,
  AppSettings,
} from '@/types';

import { BarChart3, Database, TerminalSquare, Settings } from 'lucide-react';

type ActiveModule = 'backtest' | 'data-management' | 'log-viewer' | 'settings';

const MODULES = [
  { id: 'backtest' as ActiveModule,        label: 'Backtest',        icon: BarChart3 },
  { id: 'data-management' as ActiveModule, label: 'Data Management', icon: Database },
  { id: 'log-viewer' as ActiveModule,      label: 'Log Viewer',      icon: TerminalSquare },
  { id: 'settings' as ActiveModule,        label: 'Settings',        icon: Settings },
];

export default function Dashboard() {
  const [activeModule, setActiveModule] = useState<ActiveModule>('backtest');

  const [backtestProgress, setBacktestProgress] = useState<BacktestProgress | undefined>();
  const [backtestResult, setBacktestResult] = useState<BacktestResult | undefined>();

  const [dataSources] = useState<DataSource[]>([
    { id: '1', name: 'Binance 15m', type: 'binance', status: 'active', lastUpdated: new Date() },
  ]);
  const [verificationResults, setVerificationResults] = useState<DataVerificationResult[]>([]);

  const [logs, setLogs] = useState<LogEntry[]>([
    { timestamp: new Date(), level: LogLevel.INFO, message: 'Application started successfully', source: 'System' },
  ]);

  const [appSettings, setAppSettings] = useState<AppSettings>({
    general: {
      theme: {
        key: 'theme', label: 'Theme', value: 'dark', type: 'select',
        options: [{ label: 'Light', value: 'light' }, { label: 'Dark', value: 'dark' }],
      },
      autoSave: {
        key: 'autoSave', label: 'Auto Save', value: 'true', type: 'toggle',
        description: 'Automatically save settings and configurations',
      },
    },
    api: {
      nautilusApiUrl: {
        key: 'nautilusApiUrl', label: 'NautilusTrader API URL', value: 'http://localhost:8000',
        type: 'text', required: true,
      },
      timeout: { key: 'timeout', label: 'API Timeout (seconds)', value: '30', type: 'number' },
    },
  });

  const handleBacktestStart = useCallback(() => {
    setBacktestProgress({
      currentCandle: 0, totalCandles: 1000, currentTrade: 0, totalTrades: 50,
      status: 'running', message: 'Initializing backtest...',
    });
    const interval = setInterval(() => {
      setBacktestProgress((prev) => {
        if (!prev) return undefined;
        const nextCandle = Math.min(prev.currentCandle + 10, prev.totalCandles);
        const nextTrade = Math.min(prev.currentTrade + (Math.random() > 0.8 ? 1 : 0), prev.totalTrades);
        if (nextCandle === prev.totalCandles && nextTrade === prev.totalTrades) {
          clearInterval(interval);
          setBacktestResult({
            tradeCount: 47, winRate: 0.64, profitFactor: 2.1,
            maxDrawdown: -0.15, totalReturn: 0.25, sharpeRatio: 1.8, sortinoRatio: 2.4,
          });
          return { ...prev, status: 'completed', message: 'Backtest completed' };
        }
        return { ...prev, currentCandle: nextCandle, currentTrade: nextTrade, message: `Processing candle ${nextCandle}/${prev.totalCandles}...` };
      });
    }, 500);
  }, []);

  const handleBacktestStop = useCallback(() => {
    setBacktestProgress((prev) => (prev ? { ...prev, status: 'idle' } : undefined));
  }, []);

  const handleDataVerify = useCallback(async () => {
    setVerificationResults([
      {
        symbol: 'BTCUSDT', timeframe: '15m', totalGaps: 3, repairableGaps: 2, tooOldGaps: 1,
        gaps: [
          { startTime: new Date('2024-05-01'), endTime: new Date('2024-05-02'), missingBars: 96, repairable: true },
          { startTime: new Date('2024-04-15'), endTime: new Date('2024-04-16'), missingBars: 96, repairable: true },
          { startTime: new Date('2023-05-01'), endTime: new Date('2023-05-02'), missingBars: 96, repairable: false, reason: 'Gap predates Binance API 90-day horizon' },
        ],
      },
    ]);
  }, []);

  const handleSettingsSave = useCallback((settings: AppSettings) => {
    setAppSettings(settings);
    setLogs((prev) => [
      ...prev,
      { timestamp: new Date(), level: LogLevel.INFO, message: 'Settings saved successfully', source: 'Settings Panel' },
    ]);
  }, []);

  const activeLabel = MODULES.find((m) => m.id === activeModule)?.label ?? '';

  return (
    <div className="flex flex-col h-full">
      {/* Horizontal module tabs */}
      <div
        className="flex items-center gap-1 px-4 pt-3 pb-0 flex-shrink-0"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        {MODULES.map(({ id, label, icon: Icon }) => {
          const active = id === activeModule;
          return (
            <button
              key={id}
              onClick={() => setActiveModule(id)}
              className="flex items-center gap-2 px-4 py-2.5 text-sm rounded-t-lg transition-colors"
              style={active
                ? { background: 'var(--surface-panel)', color: 'var(--text-primary)', borderBottom: '2px solid var(--core-accent-blue)' }
                : { color: 'var(--text-secondary)' }}
              onMouseEnter={e => { if (!active) (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-primary)'; }}
              onMouseLeave={e => { if (!active) (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-secondary)'; }}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          );
        })}
      </div>

      {/* Module content */}
      <div className="flex-1 overflow-auto p-8">
        <div className="mb-6">
          <h2 className="text-3xl font-bold" style={{ color: 'var(--text-primary)' }}>
            {activeLabel}
          </h2>
          <p className="mt-1" style={{ color: 'var(--text-secondary)' }}>
            React port of PyQt5 UI modules for NautilusTrader
          </p>
        </div>

        {activeModule === 'backtest' && (
          <BacktestConfigPanel
            onStart={handleBacktestStart}
            onStop={handleBacktestStop}
            progress={backtestProgress}
            result={backtestResult}
          />
        )}
        {activeModule === 'data-management' && (
          <DataManagementPanel
            dataSources={dataSources}
            onVerify={handleDataVerify}
            verificationResults={verificationResults}
          />
        )}
        {activeModule === 'log-viewer' && (
          <LogViewerPanel logs={logs} onClear={() => setLogs([])} />
        )}
        {activeModule === 'settings' && (
          <SettingsPanel settings={appSettings} onSave={handleSettingsSave} />
        )}
      </div>
    </div>
  );
}
