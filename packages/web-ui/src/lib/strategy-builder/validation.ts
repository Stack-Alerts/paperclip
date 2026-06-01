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

  // Check for required blocks
  const hasEntry = strategy.blocks.some((b) => b.type === BlockType.ENTRY_CONDITION);
  const hasExit = strategy.blocks.some((b) => b.type === BlockType.EXIT_CONDITION);

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
  if (strategy.blocks.length === 0) {
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
  if (!strategy.settings.timeframe) {
    issues.warnings.push({
      rule_id: 'missing_timeframe',
      rule_name: 'Missing Timeframe',
      severity: ValidationSeverity.WARNING,
      category: 'settings',
      message: 'Timeframe is required (e.g., 1h, 4h, 1d)',
      location: 'Strategy::settings::timeframe',
    });
  }

  if (!strategy.settings.targetMarket) {
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
      complexity_score: Math.min(100, strategy.blocks.length * 10),
    },
  };
}
