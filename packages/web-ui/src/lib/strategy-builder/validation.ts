// Client-side strategy validation (local fallback when backend unavailable)
// This provides basic structural validation for the Strategy Builder UI.
// For full institutional validation, a backend endpoint is needed.

import {
  Strategy,
  ValidationReport,
  ValidationIssue,
  ValidationSeverity,
  BlockType,
} from './types';

interface NormalizedSignal {
  id?: string;
  name?: string;
  signalName?: string;
  weight?: number;
  logic?: string;
  exit_conditions?: Array<{
    signal_name?: string;
    signalName?: string;
    exit_mode?: string;
    exitMode?: string;
    percentage?: number;
  }>;
  timing_constraint?: { reference?: string; max_candles?: number };
  recheck_config?: { enabled?: boolean; bar_delay?: number };
  recheckEnabled?: boolean;
  recheckBarDelay?: number;
}

interface BlockDataWithSignals {
  signals?: NormalizedSignal[];
  name?: string;
  blockName?: string;
  category?: string;
  logic?: string;
}

const titleCase = (s: string) =>
  s.split('_').map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ');

// Main strategy blocks are normalized to BlockType.INDICATOR with the raw
// API payload (name, logic, signals, exit_conditions on each signal) preserved
// inside `data` (see StrategyBuilderMainWindow.tsx::normalizeSignal). Synthetic
// per-signal exit pills get type === BlockType.EXIT_CONDITION. So an "entry
// block" here is any block that isn't an exit-pill — filtering by
// === ENTRY_CONDITION misses everything.
const isEntryBlock = (b: Strategy['blocks'][number]) =>
  b.type !== BlockType.EXIT_CONDITION;

interface ExitBlockData {
  name?: string;
  exitName?: string;
  exitMode?: string;
  exitPercentage?: number;
}

interface StrategySettingsExtended {
  confluenceThreshold?: number;
  [key: string]: unknown;
}

function signalName(sig: NormalizedSignal): string {
  return sig.name || sig.signalName || (sig.id ? `Signal_${sig.id}` : 'Signal');
}

function generateExecutionFlow(strategy: Strategy) {
  const blocks = strategy.blocks ?? [];
  const entryBlocks = blocks.filter(isEntryBlock);
  const exitBlocks = blocks.filter((b) => b.type === BlockType.EXIT_CONDITION);

  const blockFlows = entryBlocks.map((block) => {
    const data = block.data as BlockDataWithSignals;
    const rawSignals = Array.isArray(data?.signals) ? data.signals : [];

    const signals = rawSignals.map((sig) => {
      const ec = Array.isArray(sig.exit_conditions) ? sig.exit_conditions[0] : undefined;
      const linkedExit = ec
        ? {
            name: ec.signal_name || ec.signalName || 'Exit',
            closePct: typeof ec.percentage === 'number' ? Math.round(ec.percentage * 100) : 100,
            mode: ((ec.exit_mode || ec.exitMode || 'ABSOLUTE').toString().toUpperCase() === 'ABSOLUTE'
              ? 'ABSOLUTE'
              : 'FLEXIBLE') as 'ABSOLUTE' | 'FLEXIBLE',
          }
        : undefined;

      const tc = sig.timing_constraint;
      const timingConstraint =
        tc && typeof tc.max_candles === 'number'
          ? { withinCandles: tc.max_candles, ofSignal: tc.reference || '' }
          : undefined;

      const recheckBars =
        sig.recheck_config?.enabled && typeof sig.recheck_config.bar_delay === 'number'
          ? sig.recheck_config.bar_delay
          : sig.recheckEnabled && typeof sig.recheckBarDelay === 'number'
            ? sig.recheckBarDelay
            : undefined;
      const recheck =
        typeof recheckBars === 'number'
          ? { signal: signalName(sig), afterBars: recheckBars }
          : undefined;

      return {
        kind: 'entry' as const,
        name: signalName(sig),
        linkedExit,
        timingConstraint,
        recheck,
      };
    });

    const blockName = data?.name || data?.blockName || `Block_${block.id}`;
    const blockLogic = (data?.logic || '').toString().toUpperCase();
    return {
      index: block.index,
      name: blockName,
      logic: (data?.category === 'required' || blockLogic === 'AND' ? 'REQUIRED' : 'OPTIONAL') as 'REQUIRED' | 'OPTIONAL',
      signals,
    };
  });

  const strategyLevelExits = exitBlocks.map((block, idx) => {
    const data = block.data as ExitBlockData & {
      signalName?: string;
      exitMode?: string;
      percentage?: number;
      blockName?: string;
      parentSignalName?: string;
    };
    const rawName = (data?.signalName || data?.name || data?.exitName || `Exit_${idx + 1}`).toString();
    const display = /[a-z]/.test(rawName) ? rawName : titleCase(rawName);
    return {
      index: block.index,
      name: display,
      closePct: typeof data?.percentage === 'number' ? Math.round(data.percentage * 100) : 100,
      mode: ((data?.exitMode || 'ABSOLUTE').toString().toUpperCase() === 'ABSOLUTE'
        ? 'ABSOLUTE'
        : 'FLEXIBLE') as 'ABSOLUTE' | 'FLEXIBLE',
    };
  });

  return {
    blocks: blockFlows,
    strategyLevelExits,
  };
}

function generateConfluenceScoring(strategy: Strategy) {
  const blocks = strategy.blocks ?? [];
  const entryBlocks = blocks.filter(isEntryBlock);

  const perBlock = entryBlocks.map((block) => {
    const data = block.data as BlockDataWithSignals;
    const signalCount = data?.signals?.length ?? 1;
    const blockLogic = (data?.logic || '').toString().toUpperCase();
    const isRequired = data?.category === 'required' || blockLogic === 'AND';
    const points = isRequired ? signalCount * 10 : signalCount * 5;

    return {
      index: block.index,
      name: data?.name || data?.blockName || `Block_${block.id}`,
      logic: (isRequired ? 'REQUIRED' : 'OPTIONAL') as 'REQUIRED' | 'OPTIONAL',
      points,
      signalCount,
    };
  });

  const requiredPoints = perBlock.filter((b) => b.logic === 'REQUIRED').reduce((sum, b) => sum + b.points, 0);
  const optionalPoints = perBlock.filter((b) => b.logic === 'OPTIONAL').reduce((sum, b) => sum + b.points, 0);
  const totalPossible = requiredPoints + optionalPoints;
  const settings = strategy.settings as unknown as StrategySettingsExtended;
  const threshold = settings?.confluenceThreshold ?? 40;

  return {
    requiredPoints,
    optionalPoints,
    totalPossible,
    threshold,
    perBlock,
  };
}

function generateScenarios(strategy: Strategy) {
  const blocks = strategy.blocks ?? [];
  const entryBlocks = blocks.filter(isEntryBlock);
  const scoring = generateConfluenceScoring(strategy);

  const scenarios = [];

  if (entryBlocks.length > 0) {
    const requiredBlocks = scoring.perBlock.filter((b) => b.logic === 'REQUIRED');
    const optionalBlocks = scoring.perBlock.filter((b) => b.logic === 'OPTIONAL');

    const allRequiredFirePerBlock = requiredBlocks.map((b) => ({
      index: b.index,
      name: b.name,
      result: 'FIRE',
      points: b.points,
    }));
    const allRequiredPoints = allRequiredFirePerBlock.reduce((sum, b) => sum + b.points, 0);
    const allOptionalPoints = optionalBlocks.reduce((sum, b) => sum + b.points, 0);

    scenarios.push({
      label: 'Scenario A: All REQUIRED blocks fire',
      outcome: allRequiredPoints >= scoring.threshold ? ('opens' as const) : ('no_position' as const),
      totalPoints: allRequiredPoints + allOptionalPoints,
      perBlock: [
        ...allRequiredFirePerBlock,
        ...optionalBlocks.map((b) => ({ index: b.index, name: b.name, result: 'FIRE', points: b.points })),
      ],
    });

    if (requiredBlocks.length > 0) {
      const oneRequiredShortPerBlock = requiredBlocks.map((b, idx) =>
        idx === 0
          ? { index: b.index, name: b.name, result: 'MISS', points: 0 }
          : { index: b.index, name: b.name, result: 'FIRE', points: b.points }
      );
      const oneRequiredShortPoints = oneRequiredShortPerBlock.reduce((sum, b) => sum + b.points, 0);

      scenarios.push({
        label: `Scenario C: One REQUIRED block misses`,
        outcome: oneRequiredShortPoints >= scoring.threshold ? ('opens' as const) : ('no_position' as const),
        totalPoints: oneRequiredShortPoints,
        perBlock: oneRequiredShortPerBlock,
      });
    }
  }

  return scenarios;
}

export function validateStrategyLocal(strategy: Strategy): ValidationReport {
  const issues: {
    critical: ValidationIssue[];
    errors: ValidationIssue[];
    warnings: ValidationIssue[];
    notices: ValidationIssue[];
    info: ValidationIssue[];
  } = {
    critical: [],
    errors: [],
    warnings: [],
    notices: [],
    info: [],
  };

  const blocks = strategy.blocks ?? [];
  const settings = strategy.settings ?? ({} as Partial<Strategy['settings']>);

  // Check for required blocks. Main strategy blocks are normalized to
  // BlockType.INDICATOR with their entry signals embedded in data.signals;
  // strategy-level exit pills get BlockType.EXIT_CONDITION. So "has entry"
  // means "has any non-exit block with at least one signal."
  const hasEntry = blocks.some(
    (b) =>
      b.type !== BlockType.EXIT_CONDITION &&
      Array.isArray((b.data as BlockDataWithSignals | undefined)?.signals) &&
      ((b.data as BlockDataWithSignals).signals?.length ?? 0) > 0,
  );
  const hasExit = blocks.some((b) => b.type === BlockType.EXIT_CONDITION);

  if (!hasEntry) {
    issues.critical.push({
      rule_id: 'missing_entry_condition',
      rule_name: 'Missing Entry Condition',
      severity: ValidationSeverity.CRITICAL,
      category: 'structure',
      message: 'Strategy must have at least one entry condition block',
      location: 'Strategy::blocks',
    });
  }

  if (!hasExit) {
    issues.critical.push({
      rule_id: 'missing_exit_condition',
      rule_name: 'Missing Exit Condition',
      severity: ValidationSeverity.CRITICAL,
      category: 'structure',
      message: 'Strategy must have at least one exit condition block',
      location: 'Strategy::blocks',
    });
  }

  // Check for empty strategy
  if (blocks.length === 0) {
    issues.errors.push({
      rule_id: 'empty_strategy',
      rule_name: 'Empty Strategy',
      severity: ValidationSeverity.ERROR,
      category: 'structure',
      message: 'Strategy has no blocks. Add entry and exit conditions.',
      location: 'Strategy::blocks',
    });
  }

  // Check for missing strategy name
  if (!strategy.name || strategy.name.trim() === '') {
    issues.warnings.push({
      rule_id: 'missing_strategy_name',
      rule_name: 'Unnamed Strategy',
      severity: ValidationSeverity.WARNING,
      category: 'metadata',
      message: 'Strategy should have a descriptive name for easy identification',
      location: 'Strategy::name',
    });
  }

  // Check settings
  if (!settings.timeframe) {
    issues.warnings.push({
      rule_id: 'missing_timeframe',
      rule_name: 'Missing Timeframe',
      severity: ValidationSeverity.WARNING,
      category: 'settings',
      message: 'Timeframe is required (e.g., 1h, 4h, 1d)',
      location: 'Strategy::settings::timeframe',
    });
  }

  if (!settings.targetMarket) {
    issues.warnings.push({
      rule_id: 'missing_target_market',
      rule_name: 'Missing Target Market',
      severity: ValidationSeverity.WARNING,
      category: 'settings',
      message: 'Target market should be specified (e.g., BTC/USDT)',
      location: 'Strategy::settings::targetMarket',
    });
  }

  // Backend validation unavailable notice
  issues.info.push({
    rule_id: 'backend_validation_unavailable',
    rule_name: 'Limited Validation',
    severity: ValidationSeverity.INFO,
    category: 'system',
    message:
      'Backend validation service is temporarily unavailable. Showing local structural checks only. ' +
      'Full institutional validation including logic flow, timing conflicts, and exit strategy analysis requires backend support.',
    location: 'System::validation',
  });

  const is_valid =
    issues.critical.length === 0 &&
    issues.errors.length === 0;

  try {
    const executionFlow = generateExecutionFlow(strategy);
    const confluenceScoring = generateConfluenceScoring(strategy);
    const scenarios = generateScenarios(strategy);

    return {
      is_valid,
      timestamp: new Date().toISOString(),
      strategy_summary: {
        name: strategy.name || '(unnamed)',
        version: (strategy as { versionNumber?: number }).versionNumber?.toString(),
      },
      critical_issues: issues.critical,
      errors: issues.errors,
      warnings: issues.warnings,
      notices: issues.notices,
      info: issues.info,
      complexity_metrics: {
        complexity_score: Math.min(100, blocks.length * 10),
      },
      executionFlow: executionFlow.blocks.length > 0 ? executionFlow : undefined,
      confluenceScoring: confluenceScoring.perBlock.length > 0 ? confluenceScoring : undefined,
      scenarios: scenarios.length > 0 ? scenarios : undefined,
    };
  } catch {
    return {
      is_valid,
      timestamp: new Date().toISOString(),
      strategy_summary: {
        name: strategy.name || '(unnamed)',
        version: (strategy as { versionNumber?: number }).versionNumber?.toString(),
      },
      critical_issues: issues.critical,
      errors: issues.errors,
      warnings: issues.warnings,
      notices: issues.notices,
      info: issues.info,
      complexity_metrics: {
        complexity_score: Math.min(100, blocks.length * 10),
      },
    };
  }
}
