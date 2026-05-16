'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { BacktestConfigPanel } from '@/components/backtest/BacktestConfigPanel';
import { DataManagementPanel } from '@/components/data-management/DataManagementPanel';
import { LogViewerPanel } from '@/components/log-viewer/LogViewerPanel';
import { SettingsPanel } from '@/components/settings/SettingsPanel';
import {
  LogLevel,
} from '@/types';
import type {
  BacktestConfig,
  BacktestProgress,
  BacktestResult,
  DataSource,
  DataVerificationResult,
  LogEntry,
  AppSettings,
} from '@/types';

// Import icons from lucide-react
import { BarChart3, Database, TerminalSquare, Settings, Menu, X } from 'lucide-react';

type ActiveModule = 'backtest' | 'data-management' | 'log-viewer' | 'settings';

export default function Dashboard() {
  const [activeModule, setActiveModule] = useState<ActiveModule>('backtest');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // Backtest state
  const [backtestProgress, setBacktestProgress] = useState<BacktestProgress | undefined>();
  const [backtestResult, setBacktestResult] = useState<BacktestResult | undefined>();

  // Data Management state
  const [dataSources, setDataSources] = useState<DataSource[]>([
    {
      id: '1',
      name: 'Binance 15m',
      type: 'binance',
      status: 'active',
      lastUpdated: new Date(),
    },
  ]);
  const [verificationResults, setVerificationResults] = useState<DataVerificationResult[]>([]);

  // Log Viewer state
  const [logs, setLogs] = useState<LogEntry[]>([
    {
      timestamp: new Date(),
      level: LogLevel.INFO,
      message: 'Application started successfully',
      source: 'System',
    },
  ]);

  // Settings state
  const [appSettings, setAppSettings] = useState<AppSettings>({
    general: {
      theme: {
        key: 'theme',
        label: 'Theme',
        value: 'dark',
        type: 'select',
        options: [
          { label: 'Light', value: 'light' },
          { label: 'Dark', value: 'dark' },
        ],
      },
      autoSave: {
        key: 'autoSave',
        label: 'Auto Save',
        value: 'true',
        type: 'toggle',
        description: 'Automatically save settings and configurations',
      },
    },
    api: {
      nautilusApiUrl: {
        key: 'nautilusApiUrl',
        label: 'NautilusTrader API URL',
        value: 'http://localhost:8000',
        type: 'text',
        required: true,
      },
      timeout: {
        key: 'timeout',
        label: 'API Timeout (seconds)',
        value: '30',
        type: 'number',
      },
    },
  });

  // Handlers
  const handleBacktestStart = useCallback((config: BacktestConfig) => {
    setBacktestProgress({
      currentCandle: 0,
      totalCandles: 1000,
      currentTrade: 0,
      totalTrades: 50,
      status: 'running',
      message: 'Initializing backtest...',
    });

    // Simulate backtest progress
    const interval = setInterval(() => {
      setBacktestProgress((prev) => {
        if (!prev) return undefined;
        const nextCandle = Math.min(prev.currentCandle + 10, prev.totalCandles);
        const nextTrade = Math.min(prev.currentTrade + (Math.random() > 0.8 ? 1 : 0), prev.totalTrades);

        if (nextCandle === prev.totalCandles && nextTrade === prev.totalTrades) {
          clearInterval(interval);
          setBacktestResult({
            tradeCount: 47,
            winRate: 0.64,
            profitFactor: 2.1,
            maxDrawdown: -0.15,
            totalReturn: 0.25,
            sharpeRatio: 1.8,
            sortinoRatio: 2.4,
          });
          return {
            ...prev,
            status: 'completed',
            message: 'Backtest completed',
          };
        }

        return {
          ...prev,
          currentCandle: nextCandle,
          currentTrade: nextTrade,
          message: `Processing candle ${nextCandle}/${prev.totalCandles}...`,
        };
      });
    }, 500);
  }, []);

  const handleBacktestStop = useCallback(() => {
    setBacktestProgress((prev) => (prev ? { ...prev, status: 'idle' } : undefined));
  }, []);

  const handleDataVerify = useCallback(async () => {
    // Simulate verification
    setVerificationResults([
      {
        symbol: 'BTCUSDT',
        timeframe: '15m',
        totalGaps: 3,
        repairableGaps: 2,
        tooOldGaps: 1,
        gaps: [
          {
            startTime: new Date('2024-05-01'),
            endTime: new Date('2024-05-02'),
            missingBars: 96,
            repairable: true,
          },
          {
            startTime: new Date('2024-04-15'),
            endTime: new Date('2024-04-16'),
            missingBars: 96,
            repairable: true,
          },
          {
            startTime: new Date('2023-05-01'),
            endTime: new Date('2023-05-02'),
            missingBars: 96,
            repairable: false,
            reason: 'Gap predates Binance API 90-day horizon',
          },
        ],
      },
    ]);
  }, []);

  const handleSettingsSave = useCallback((settings: AppSettings) => {
    setAppSettings(settings);
    // Add log entry
    setLogs((prev) => [
      ...prev,
      {
        timestamp: new Date(),
        level: LogLevel.INFO,
        message: 'Settings saved successfully',
        source: 'Settings Panel',
      },
    ]);
  }, []);

  const navigationItems = [
    {
      id: 'backtest' as ActiveModule,
      label: 'Backtest',
      icon: BarChart3,
    },
    {
      id: 'data-management' as ActiveModule,
      label: 'Data Management',
      icon: Database,
    },
    {
      id: 'log-viewer' as ActiveModule,
      label: 'Log Viewer',
      icon: TerminalSquare,
    },
    {
      id: 'settings' as ActiveModule,
      label: 'Settings',
      icon: Settings,
    },
  ];

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside
        className={`bg-gray-900 text-white transition-all duration-300 ${
          isSidebarOpen ? 'w-64' : 'w-20'
        } border-r border-gray-800`}
      >
        <div className="p-4 flex items-center justify-between">
          {isSidebarOpen && (
            <h1 className="text-lg font-bold truncate">BTC Trade Engine</h1>
          )}
          <button
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="p-1 hover:bg-gray-800 rounded transition-colors"
          >
            {isSidebarOpen ? (
              <X className="w-5 h-5" />
            ) : (
              <Menu className="w-5 h-5" />
            )}
          </button>
        </div>

        <nav className="mt-8 space-y-2 px-2">
          {navigationItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                onClick={() => setActiveModule(item.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                  activeModule === item.id
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                }`}
                title={item.label}
              >
                <Icon className="w-5 h-5" />
                {isSidebarOpen && <span>{item.label}</span>}
              </button>
            );
          })}
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <div className="p-8">
          <div className="mb-6">
            <h2 className="text-3xl font-bold text-gray-900">
              {navigationItems.find((item) => item.id === activeModule)?.label}
            </h2>
            <p className="text-gray-600 mt-1">
              React port of PyQt5 UI modules for NautilusTrader
            </p>
          </div>

          {/* Active Module Content */}
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
            <LogViewerPanel
              logs={logs}
              onClear={() => setLogs([])}
            />
          )}

          {activeModule === 'settings' && (
            <SettingsPanel
              settings={appSettings}
              onSave={handleSettingsSave}
            />
          )}
        </div>
      </main>
    </div>
  );
}
