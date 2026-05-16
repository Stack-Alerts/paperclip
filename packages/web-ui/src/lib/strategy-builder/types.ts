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

// Block definition from library
export interface BlockDefinition {
  id: string;
  type: BlockType;
  name: string;
  description: string;
  category: string;
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
  profitFactor: number;
  averageWin: number;
  averageLoss: number;
  equityCurve?: Array<{ timestamp: string; value: number }>;
  trades?: Trade[];
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
