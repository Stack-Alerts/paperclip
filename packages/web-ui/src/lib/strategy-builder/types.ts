// Strategy Builder type definitions
// Single source of truth for all StrategyBuilder data structures

export enum BlockType {
  ENTRY_CONDITION = 'entry_condition',
  EXIT_CONDITION = 'exit_condition',
  RISK_MANAGEMENT = 'risk_management',
  TIME_CONSTRAINT = 'time_constraint',
  FILTER = 'filter',
  INDICATOR = 'indicator',
  POSITION_SIZING = 'position_sizing',
}

export enum StrategyStatus {
  DRAFT = 'draft',
  VALID = 'valid',
  INVALID = 'invalid',
  BACKTESTED = 'backtested',
  ACTIVE = 'active',
}

export enum ValidationLevel {
  ERROR = 'error',
  WARNING = 'warning',
  INFO = 'info',
}

// Block data payload - generic, specific structure depends on BlockType
export interface BlockData {
  [key: string]: unknown;
}

// Block configuration entry point
export interface Block {
  id: string;
  type: BlockType;
  index: number;
  data: BlockData;
  metadata?: {
    createdAt?: string;
    updatedAt?: string;
    labels?: string[];
  };
}

// Validation fix event - persisted as part of the strategy
export interface ValidationFixEvent {
  rule_id: string;
  rule_name: string;
  mode?: string; // Fix mode (e.g., 'rename_signal', 'remove_block', etc.)
  targetIndex?: number; // Index of the target block if applicable
  newName?: string; // New name if the fix involves renaming
  timestamp: string; // ISO 8601 timestamp when the fix was applied
  undone?: boolean; // Whether this fix was later undone
}

// Strategy core structure
export interface Strategy {
  id: string;
  name: string;
  description?: string;
  status: StrategyStatus;
  blocks: Block[];
  settings: StrategySettings;
  tags?: string[];
  createdAt: string;
  updatedAt: string;
  backtestResults?: BacktestResult[];
  versionId?: string;
  versionNumber?: number;
  published?: boolean;
  testCount?: number;
  strategyType?: string;
  validationStatus?: 'Pass' | 'Fail' | 'Un-Validated';
  versions?: StrategyVersion[];
  validationHistory?: ValidationFixEvent[];
}

// Strategy version snapshot for history/rollback
export interface StrategyVersion {
  id: string;
  strategyId: string;
  versionNumber: number;
  createdAt: string;
  author?: string;
  description?: string;
  isLatest: boolean;
  changesSummary?: string;
}

// Strategy-level settings and configuration
export interface StrategySettings {
  timeframe: string; // e.g., '1h', '4h', '1d'
  targetMarket?: string;
  assetClass?: string;
  riskParameters?: {
    maxLossPerTrade?: number;
    maxAllocation?: number;
    maxDrawdown?: number;
  };
  timeoutSeconds?: number;
  notes?: string;
}

// Signal definition for block
export interface BlockSignal {
  name: string;
  description?: string;
  ui_visible?: boolean;
  occurrences?: number;
  occurrence_percentage?: number;
  total_candles?: number;
}

// Exit condition configuration
export interface ExitCondition {
  signalName: string;
  bindingLevel: string;
  exitMode: 'percentage' | 'fixed';
  exitPercentage?: number;
  tpThreshold?: number;
  reversal?: boolean;
  recheck?: boolean;
}

// Block definition from library
export interface BlockDefinition {
  id: string;
  type: BlockType;
  name: string;
  description: string;
  category: string;
  signals?: BlockSignal[];
  schema?: Record<string, BlockFieldSchema>; // Field definitions for config
  validators?: BlockValidator[];
  metadata?: {
    version?: string;
    deprecated?: boolean;
  };
}

// Field schema for block configuration
export interface BlockFieldSchema {
  type: 'string' | 'number' | 'boolean' | 'select' | 'multiselect' | 'date-range';
  label: string;
  required?: boolean;
  default?: unknown;
  options?: Array<{ label: string; value: string | number }>;
  validation?: {
    min?: number;
    max?: number;
    pattern?: string;
  };
  description?: string;
}

// Block validator for validation rules
export interface BlockValidator {
  name: string;
  description: string;
  validate: (blockData: BlockData) => boolean;
}

// Block category for UI organization
export interface BlockCategory {
  id: string;
  name: string;
  description?: string;
  icon?: string;
  blockTypes: BlockType[];
}

// Validation message for real-time feedback
export interface ValidationMessage {
  id: string;
  level: ValidationLevel;
  text: string;
  blockIndex?: number;
  code?: string;
  timestamp: string;
}

// Backtest configuration
export interface BacktestConfig {
  strategyId: string;
  startDate: string; // ISO 8601
  endDate: string;
  initialCapital: number;
  commissionPercentage?: number;
  slippagePercentage?: number;
  maxConcurrentPositions?: number;
  timeframe?: string;
}

export interface AdaptiveSLConfig {
  enabled: boolean;
  delayEnabled: boolean;
  delayBars: number;
  emergencySlPct: number;
  volatilityLookback: number;
  volatilityMultiplier: number;
  minSlPct: number;
  maxSlPct: number;
  useStructureSl: boolean;
  structureSources?: string[];
}

export interface BacktestConfigFull extends BacktestConfig {
  mode: 'historical' | 'live_replay';
  tpslMode: string;
  slAdjustmentMode: string;
  adaptiveSLPreset: string;
  adaptiveSL: AdaptiveSLConfig;
  riskPerTradePct: number;
  minRiskRewardRatio: number;
  maxBarsHeld: number;
  lookbackDays?: number;
  trainingDays?: number;
  testingDays?: number;
  maxLeverage?: number;
  confluenceThreshold?: number;
}

export interface BacktestStatusMessage {
  message: string;
  level: 'INFO' | 'SYSTEM' | 'ERROR';
  timestamp: string;
}

export interface TpSlAdjustments {
  TP1: number;
  TP2: number;
  TP3: number;
  SL: number;
}

// Backtest execution result
export interface BacktestResult {
  id: string;
  strategyId: string;
  runId: string;
  status: 'running' | 'completed' | 'failed';
  startDate: string;
  endDate: string;
  initialCapital: number;
  finalCapital: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  winRate: number;
  totalReturn: number;
  returnPercentage: number;
  maxDrawdown: number;
  sharpeRatio: number;
  sortino_ratio: number;
  calmar_ratio?: number;
  profitFactor: number;
  averageWin: number;
  averageLoss: number;
  equityCurve?: Array<{ timestamp: string; value: number }>;
  trades?: Trade[];
  totalBars?: number;
  createdAt: string;
  completedAt?: string;
}

// Individual trade from backtest
export interface Trade {
  id: string;
  entryTime: string;
  exitTime: string;
  entryPrice: number;
  exitPrice: number;
  quantity: number;
  pnl: number;
  pnlPercentage: number;
  bars: number;
  exitType?: string;
  // `side` is emitted by /api/backtest (src/api/app.py); thick-client colors LONG green, SHORT red.
  side?: 'LONG' | 'SHORT' | string;
  // Symbol traded; thick-client defaults to BTC.P/USDT when not present on the record.
  symbol?: string;
  status?: 'open' | 'closed' | 'OPEN' | 'CLOSED' | 'PARTIAL' | string;
  // Exit notes from thick-client _format_notes (e.g. "TP1 Hit", "Stop Loss Hit").
  notes?: string;
  // Entry signal names that fired at trade open (e.g. ["BULLISH_BREAK"]).
  entrySignals?: string[];
  // Partial exit breakdown from thick-client _aggregate_exits (e.g. "TP1: $X | TP2: $Y").
  partialBreakdown?: string;
}

// UI State for panels and modals
export interface StrategyBuilderUIState {
  selectedBlockIndex: number | null;
  activeModalType?: 'block-config' | 'backtest' | 'settings' | null;
  activeModalBlockType?: BlockType;
  backTestInProgress: boolean;
  backTestProgress: number;
  validationPanelOpen: boolean;
  settingsPanelExpanded: boolean;
}

// API response types
export interface ApiResponse<T> {
  data: T;
  error?: {
    code: string;
    message: string;
  };
  timestamp: string;
}

export interface BlockLibraryResponse {
  blocks: BlockDefinition[];
  categories: BlockCategory[];
}

// UI Component Props types (exported for component reuse)
export interface BlockRowProps {
  block: Block;
  index: number;
  isSelected: boolean;
  onSelect: (index: number) => void;
  onDelete: (index: number) => void;
  onConfigure: (index: number) => void;
  onReorder: (fromIdx: number, toIdx: number) => void;
}

export interface BlockConfigModalProps {
  blockType: BlockType;
  blockData: BlockData;
  blockDefinition?: BlockDefinition;
  onSave: (data: BlockData) => void;
  onCancel: () => void;
}

export interface ValidationPanelProps {
  messages: ValidationMessage[];
  onMessageClick?: (message: ValidationMessage) => void;
  onClear?: () => void;
  filterLevel?: ValidationLevel;
}

export interface BacktestConfigModalProps {
  strategyId: string;
  onClose: () => void;
  onBacktestStart?: (config: BacktestConfig) => void;
}

// Service layer type contracts (Phase 2 wiring targets)
export interface PhaseTimingDataModel {
  phaseId: string;
  phaseName: string;
  startTimestamp: number;
  endTimestamp: number | null;
  durationMs: number | null;
  candleCount: number;
  signalCount: number;
  metadata: Record<string, unknown>;
}

export interface PhaseEventBuffer {
  phaseId: string;
  events: Array<{
    timestamp: number;
    eventType: string;
    payload: Record<string, unknown>;
  }>;
  maxBufferSize: number;
  overflowPolicy: 'drop_oldest' | 'drop_newest' | 'error';
}

// Validation Report types (P1 Parity - ValidationReportWindow)
export enum ValidationSeverity {
  CRITICAL = 'CRITICAL',
  ERROR = 'ERROR',
  WARNING = 'WARNING',
  NOTICE = 'NOTICE',
  INFO = 'INFO',
}

export interface ValidationIssue {
  rule_id: string;
  rule_name: string;
  severity: ValidationSeverity;
  category: string;
  message: string;
  location: string; // e.g., "Block::hod::Signal::BELOW_HOD"
  suggestion?: string;
  auto_fix_available?: boolean;
  auto_fix_data?: Record<string, unknown>;
}

export interface ValidationReport {
  is_valid: boolean;
  timestamp: string; // ISO 8601
  strategy_summary: {
    name: string;
    version?: string;
  };
  critical_issues: ValidationIssue[];
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
  notices: ValidationIssue[];
  info: ValidationIssue[];
  complexity_metrics: {
    complexity_score: number;
  };
  timing_conflicts?: Array<{
    signal: string;
    timing_window: number;
    recheck_delay: number;
  }>;
  executionFlow?: {
    blocks: Array<{
      index: number;
      name: string;
      logic: 'REQUIRED' | 'OPTIONAL';
      signals: Array<{
        kind: 'entry';
        name: string;
        linkedExit?: { name: string; closePct: number; mode: 'ABSOLUTE' | 'FLEXIBLE' };
        timingConstraint?: { withinCandles: number; ofSignal: string };
        recheck?: { signal: string; afterBars: number };
      }>;
    }>;
    strategyLevelExits: Array<{ index: number; name: string; closePct: number; mode: 'ABSOLUTE' | 'FLEXIBLE' }>;
  };
  confluenceScoring?: {
    requiredPoints: number;
    optionalPoints: number;
    totalPossible: number;
    threshold: number;
    perBlock: Array<{ index: number; name: string; logic: 'REQUIRED' | 'OPTIONAL'; points: number; signalCount: number }>;
  };
  scenarios?: Array<{
    label: string;
    outcome: 'opens' | 'no_position';
    totalPoints: number;
    perBlock: Array<{ index: number; name: string; result: string; points: number }>;
  }>;
}

export interface WalkforwardResult {
  tp1_adjustments: number;
  tp2_adjustments: number;
  tp3_adjustments: number;
  sl_adjustments: number;
  adjustments_per_position: number;
  total_positions: number;
}
