/**
 * Shared TypeScript types for BTC Trade Engine UI modules
 * Ported from PyQt5 implementations
 */

// Backtest Configuration Types
export interface BacktestConfig {
  lookbackDays: number;
  trainingWindow: number;
  mode: 'historical' | 'live';
  strategyId: string;
  instrumentId: string;
  startDate: Date;
  endDate: Date;
}

export interface BacktestResult {
  tradeCount: number;
  winRate: number;
  profitFactor: number;
  maxDrawdown: number;
  totalReturn: number;
  sharpeRatio: number;
  sortinoRatio: number;
}

export interface BacktestProgress {
  currentCandle: number;
  totalCandles: number;
  currentTrade: number;
  totalTrades: number;
  status: 'idle' | 'running' | 'paused' | 'completed' | 'failed';
  message: string;
}

// Data Management Types
export interface DataSource {
  id: string;
  name: string;
  type: 'binance' | 'other';
  status: 'active' | 'inactive' | 'error';
  lastUpdated: Date;
}

export interface DataGap {
  startTime: Date;
  endTime: Date;
  missingBars: number;
  repairable: boolean;
  reason?: string;
}

export interface DataVerificationResult {
  symbol: string;
  timeframe: string;
  totalGaps: number;
  repairableGaps: number;
  tooOldGaps: number;
  gaps: DataGap[];
}

// Log Entry Types
export enum LogLevel {
  DEBUG = 'DEBUG',
  INFO = 'INFO',
  WARNING = 'WARNING',
  ERROR = 'ERROR',
  CRITICAL = 'CRITICAL',
}

export enum LogEventType {
  TRADE_OPENED = 'TRADE_OPENED',
  TRADE_CLOSED = 'TRADE_CLOSED',
  TRADE_UPDATED = 'TRADE_UPDATED',
  POSITIONS_SNAPSHOT = 'POSITIONS_SNAPSHOT',
  TRADE_NOT_FOUND = 'TRADE_NOT_FOUND',
  CONFIG_INITIALIZED = 'CONFIG_INITIALIZED',
  CONFIG_READ = 'CONFIG_READ',
  CONFIG_VALIDATED = 'CONFIG_VALIDATED',
  ERROR = 'ERROR',
  WARNING = 'WARNING',
  SUCCESS = 'SUCCESS',
}

export interface LogEntry {
  timestamp: Date;
  level: LogLevel;
  message: string;
  eventType?: LogEventType;
  source?: string;
  stackTrace?: string;
}

// Settings Types
export interface SettingsCategory {
  id: string;
  name: string;
  icon?: string;
  description?: string;
}

export interface Setting<T = string> {
  key: string;
  label: string;
  value: T;
  type: 'text' | 'number' | 'select' | 'toggle' | 'password';
  description?: string;
  options?: { label: string; value: string | number | boolean }[];
  required?: boolean;
  masked?: boolean;
}

export interface AppSettings {
  [category: string]: {
    [key: string]: Setting;
  };
}

// UI Module State
export interface UIModuleState {
  activeModule: 'backtest' | 'data-management' | 'log-viewer' | 'settings' | null;
  loading: boolean;
  error?: string;
}

// Tooltip Registry
export interface Tooltip {
  id: string;
  label: string;
  description: string;
  category?: string;
}

export interface TooltipRegistry {
  [moduleId: string]: Tooltip[];
}
