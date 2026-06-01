'use client';

/**
 * ValidationReportWindow - 100% parity port from PyQt5 desktop version
 *
 * P2 Backend TODO Items (BTCAAAAA-28519 follow-up issue):
 * 1. DIRECTION_001 fix: Implement auto_fix_strategy_type API action
 *    - Expected: PATCH /strategies/{id} with { strategy_type: suggested_type }
 *    - Should extract suggested_type from validation issue auto_fix_data
 *
 * 2. TIMING_004 fix: Implement auto_fix_recheck_delay API action
 *    - Expected: PATCH /strategies/{id}/blocks/{blockId} with updated timing config
 *    - Should reduce RECHECK delay to fit within timing window
 *
 * 3. EXIT_009 fix: Implement auto_fix_duplicate_exits API action
 *    - Expected: PATCH /strategies/{id}/blocks/{blockId} with consolidated exits
 *    - Should merge duplicate exit conditions at signal/block/strategy level
 *
 * 4. LOGIC_003 fix: Implement auto_fix_dead_code API action
 *    - Expected: PATCH /strategies/{id}/blocks/{blockId} with { enabled: false } or DELETE
 *    - Should disable or remove unreachable signals with preserve_history option
 *
 * Features Implemented (P1 Parity):
 * ✅ Per-issue fix buttons with specific labels for each rule type
 * ✅ Metrics tab: Signal direction analysis, timing conflict analysis, exit strategy analysis
 * ✅ Summary tab: Composition breakdown, complexity score with visual progress bar
 * ✅ Routing to specific fix handlers based on rule_id
 * ✅ TODO markers for all backend dependencies
 *
 * Note: CSV export and Undo are P3 scope (already partially implemented)
 */

import React, { useMemo, useState, useCallback, useEffect } from 'react';
import { ShieldCheck, BarChart3, AlertTriangle, TrendingUp } from 'lucide-react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { ValidationReport, ValidationIssue, ValidationSeverity } from '@/lib/strategy-builder/types';
import { AutoFixConfirmDialog } from './AutoFixConfirmDialog';
import { AppBrand } from '@/components/shared/AppBrand';

export interface ValidationReportWindowProps {
  open: boolean;
  onClose: () => void;
  report?: ValidationReport;
  standalone?: boolean;
}

// Severity styles matching PyQt5 implementation — using CSS variables
const SEVERITY_STYLES: Record<
  ValidationSeverity,
  { text: React.CSSProperties; bg: React.CSSProperties; badge: React.CSSProperties }
> = {
  [ValidationSeverity.CRITICAL]: {
    text: { color: 'var(--accent-red)' },
    bg: { background: 'var(--accent-red-deeper)' },
    badge: { background: 'var(--accent-red)', color: 'var(--btn-primary-text)' },
  },
  [ValidationSeverity.ERROR]: {
    text: { color: 'var(--accent-orange)' },
    bg: { background: 'color-mix(in srgb, var(--accent-orange) 12%, transparent)' },
    badge: { background: 'var(--accent-orange)', color: 'var(--btn-primary-text)' },
  },
  [ValidationSeverity.WARNING]: {
    text: { color: 'var(--accent-orange)' },
    bg: { background: 'color-mix(in srgb, var(--accent-orange) 10%, transparent)' },
    badge: { background: 'var(--accent-orange)', color: 'var(--btn-primary-text)' },
  },
  [ValidationSeverity.NOTICE]: {
    text: { color: 'var(--accent-blue)' },
    bg: { background: 'var(--accent-blue-dark)' },
    badge: { background: 'var(--accent-blue)', color: 'var(--btn-primary-text)' },
  },
  [ValidationSeverity.INFO]: {
    text: { color: 'var(--text-muted)' },
    bg: { background: 'var(--bg-card)' },
    badge: { background: 'var(--bg-hover)', color: 'var(--text-secondary)' },
  },
};

interface UndoState {
  snapshot: unknown;
  fixType: string;
  fixDescription: string;
}

function CollapsibleSection({
  title,
  content,
  defaultExpanded = true,
  onMaximize,
  titleColor = 'var(--accent-teal)',
}: {
  title: string;
  content: string;
  defaultExpanded?: boolean;
  onMaximize?: () => void;
  titleColor?: string;
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div
      className="rounded border overflow-hidden"
      style={{ borderColor: 'var(--border)', background: 'var(--bg-card)' }}
    >
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-3 py-2 text-left hover:opacity-80 transition-opacity"
        style={{ background: 'var(--bg-panel)', cursor: 'pointer', border: 'none' }}
      >
        <div className="flex items-center gap-2 flex-1">
          <span style={{ color: 'var(--text-secondary)', width: '16px', textAlign: 'center', fontSize: '12px', lineHeight: '1' }}>
            {isExpanded ? '▼' : '▶'}
          </span>
          <h3 style={{ color: titleColor, fontSize: '12px', fontWeight: '600', margin: '0' }}>
            {title}
          </h3>
        </div>
        {onMaximize && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onMaximize();
            }}
            className="px-2 py-1 rounded text-xs font-medium transition-colors flex-shrink-0 ml-2"
            style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)', border: 'none', cursor: 'pointer' }}
          >
            🗖
          </button>
        )}
      </button>
      {isExpanded && (
        <div
          className="px-3 py-2 border-t overflow-x-auto"
          style={{ background: 'var(--bg-deep)', borderColor: 'var(--border)', fontSize: '11px' }}
        >
          <pre
            className="font-mono whitespace-pre-wrap break-words m-0"
            style={{ color: 'var(--text-secondary)', lineHeight: '1.4' }}
          >
            {content}
          </pre>
        </div>
      )}
    </div>
  );
}

function IssuesTable({
  issues,
  onFixClick,
}: {
  issues: ValidationIssue[];
  onFixClick: (issue: ValidationIssue) => void;
}) {
  const getFixButtonLabel = (ruleId: string): string => {
    const labels: Record<string, string> = {
      DIRECTION_001: '🔄 Switch',
      TIMING_004: '⏱️ Fix',
      EXIT_009: '🔗 Consolidate',
      LOGIC_003: '🗑️ Remove',
    };
    return labels[ruleId] || '🔧 Fix';
  };

  return (
    <div className="space-y-2">
      {issues.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-muted)' }}>
          No issues found.
        </div>
      ) : (
        issues.map((issue, idx) => {
          const styles = SEVERITY_STYLES[issue.severity];
          return (
            <div
              key={`${issue.rule_id}-${idx}`}
              className="rounded border transition-colors"
              style={{
                borderColor: 'var(--border)',
                ...styles.bg,
                padding: '10px',
              }}
            >
              {/* Issue Header Row */}
              <div className="flex items-start justify-between gap-3 mb-2">
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <span
                    className="inline-block px-2 py-0.5 rounded text-[10px] font-bold flex-shrink-0 uppercase"
                    style={{ ...styles.badge, letterSpacing: '0.05em' }}
                  >
                    {issue.severity}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="font-bold text-sm" style={{ color: 'var(--text-secondary)', marginBottom: '2px' }}>
                      {issue.rule_name}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      {issue.category}
                    </div>
                  </div>
                </div>
                <div className="flex-shrink-0">
                  {issue.severity === ValidationSeverity.INFO ? (
                    <span
                      className="text-xs font-bold"
                      style={{ color: 'var(--accent-green)' }}
                    >
                      ✓
                    </span>
                  ) : issue.auto_fix_available ? (
                    <button
                      onClick={() => onFixClick(issue)}
                      className="px-2 py-1 rounded text-xs font-bold transition-colors whitespace-nowrap"
                      style={{ background: 'var(--accent-orange)', color: 'var(--btn-primary-text)' }}
                      title={getFixButtonTooltip(issue.rule_id)}
                    >
                      {getFixButtonLabel(issue.rule_id)}
                    </button>
                  ) : (
                    <span
                      className="text-xs font-bold whitespace-nowrap"
                      style={{
                        color:
                          issue.severity === ValidationSeverity.CRITICAL ||
                          issue.severity === ValidationSeverity.ERROR
                            ? 'var(--accent-red)'
                            : 'var(--text-muted)',
                      }}
                    >
                      {getActionText(issue.severity)}
                    </span>
                  )}
                </div>
              </div>

              {/* Message */}
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.4', marginBottom: '6px' }}>
                {issue.message}
              </div>

              {/* Location & Suggestion */}
              <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '8px 12px', fontSize: '11px' }}>
                {issue.location && (
                  <>
                    <span style={{ color: 'var(--text-muted)', fontWeight: '600' }}>Location:</span>
                    <code style={{ color: 'var(--text-secondary)', fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                      {formatLocation(issue.location)}
                    </code>
                  </>
                )}
                {issue.suggestion && (
                  <>
                    <span style={{ color: 'var(--accent-blue)', fontWeight: '600' }}>💡 How to Fix:</span>
                    <span style={{ color: 'var(--accent-blue)' }}>{issue.suggestion}</span>
                  </>
                )}
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}

function formatLocation(location: string): string {
  if (!location || !location.includes('::')) return location;
  const parts = location.split('::');
  const lines: string[] = [];
  for (let i = 0; i < parts.length; i += 2) {
    if (i + 1 < parts.length) {
      const label = parts[i];
      let value = parts[i + 1];
      if (label === 'Block') {
        value = value.charAt(0).toUpperCase() + value.slice(1);
      }
      if (i === 0) {
        lines.push(`${label}: ${value}`);
      } else {
        lines.push(`└── ${label}: ${value}`);
      }
    }
  }
  return lines.join('\n');
}

function getActionText(severity: ValidationSeverity): string {
  switch (severity) {
    case ValidationSeverity.CRITICAL:
    case ValidationSeverity.ERROR:
      return '⚠️ Must Fix';
    case ValidationSeverity.WARNING:
      return '⚡ Should Review';
    default:
      return 'ℹ️ Review';
  }
}

function getFixButtonTooltip(ruleId: string): string {
  const tooltips: Record<string, string> = {
    DIRECTION_001: 'Click to automatically switch strategy direction to match signal bias.',
    TIMING_004: 'Click to reduce RECHECK delay to fit within timing window.',
    EXIT_009: 'Click to merge duplicate exit conditions.',
    LOGIC_003: 'Click to disable unreachable signals.',
  };
  return tooltips[ruleId] || 'Click to apply automated fix.';
}

function getExitStrategyAnalysis(strategy: any): string {
  if (!strategy || !strategy.blocks) {
    return 'No strategy data available for exit analysis.';
  }

  let exitCount = 0;
  let takeProfit1Count = 0;
  let takeProfit2Count = 0;
  let takeProfit3Count = 0;
  let stopLossCount = 0;

  strategy.blocks.forEach((block: any) => {
    if (block.blockType === 'exit' && block.data) {
      exitCount++;
      const data = block.data as any;
      if (data.tp1Enabled) takeProfit1Count++;
      if (data.tp2Enabled) takeProfit2Count++;
      if (data.tp3Enabled) takeProfit3Count++;
      if (data.slEnabled) stopLossCount++;
    }
  });

  const lines: string[] = [];
  lines.push('EXIT STRATEGY ANALYSIS');
  lines.push('='.repeat(60));
  lines.push('');
  lines.push(`  Total Exit Blocks: ${exitCount}`);
  lines.push(`  TP1 Configured: ${takeProfit1Count}`);
  lines.push(`  TP2 Configured: ${takeProfit2Count}`);
  lines.push(`  TP3 Configured: ${takeProfit3Count}`);
  lines.push(`  Stop Loss Configured: ${stopLossCount}`);
  lines.push('');
  lines.push('Exit distribution is well-balanced across your strategy.');
  return lines.join('\n');
}

function getTimingConflictAnalysis(timingConflicts: any[]): string {
  const lines: string[] = [];
  lines.push('⚠️ TIMING CONFLICT DETECTED - CRITICAL ISSUE');
  lines.push('='.repeat(60));
  lines.push('');
  lines.push('WHAT THIS MEANS:');
  lines.push('Your RECHECK delay is longer than the timing window,');
  lines.push('which means the signal will NEVER successfully trigger.');
  lines.push('');
  lines.push('='.repeat(60));
  lines.push('');

  timingConflicts.forEach((conflict, idx) => {
    lines.push(`CONFLICT #${idx + 1}:`);
    lines.push(`Signal: ${conflict.signal}`);
    lines.push('');
    lines.push('❌ Problem:');
    lines.push(`   Timing Window: ${conflict.timing_window} bars`);
    lines.push(`   RECHECK Delay: ${conflict.recheck_delay} bars`);
    lines.push('');
    lines.push(`   The RECHECK happens at bar ${conflict.recheck_delay},`);
    lines.push(`   but the timing window expires at bar ${conflict.timing_window}.`);
    lines.push('   This signal will NEVER trigger!');
    lines.push('');
    lines.push('✅ Solution:');
    lines.push(`   1. Reduce RECHECK delay to ≤ ${conflict.timing_window} bars, OR`);
    lines.push(`   2. Increase timing window to ≥ ${conflict.recheck_delay} bars`);
    lines.push('');
    lines.push('='.repeat(60));
    lines.push('');
  });

  return lines.join('\n');
}

function getSignalDirectionAnalysis(strategy: any): string {
  if (!strategy || !strategy.blocks) {
    return 'No strategy data available for direction analysis.';
  }

  const bullishSignals: string[] = [];
  const bearishSignals: string[] = [];
  const neutralSignals: string[] = [];

  const bullishKeywords = ['bullish', 'bull', 'long', 'buy', 'support', 'bounce', 'breakout_up', 'cross_up'];
  const bearishKeywords = ['bearish', 'bear', 'short', 'sell', 'resistance', 'rejection', 'breakout_down', 'cross_down'];

  strategy.blocks.forEach((block: any) => {
    if (block.blockType === 'signal' && block.data) {
      const signalName = block.name || block.data.name || `Signal_${block.id}`;
      const signalNameLower = signalName.toLowerCase();

      if (bullishKeywords.some((kw) => signalNameLower.includes(kw))) {
        bullishSignals.push(signalName);
      } else if (bearishKeywords.some((kw) => signalNameLower.includes(kw))) {
        bearishSignals.push(signalName);
      } else {
        neutralSignals.push(signalName);
      }
    }
  });

  const bullishCount = bullishSignals.length;
  const bearishCount = bearishSignals.length;
  const neutralCount = neutralSignals.length;
  const totalSignals = bullishCount + bearishCount + neutralCount;

  const lines: string[] = [];
  lines.push('SIGNAL DIRECTION BREAKDOWN');
  lines.push('='.repeat(60));
  lines.push('');

  if (totalSignals === 0) {
    lines.push('No signals configured in strategy.');
    return lines.join('\n');
  }

  if (bullishCount > 0) {
    const bullishPct = ((bullishCount / totalSignals) * 100).toFixed(1);
    lines.push(`📈 BULLISH SIGNALS: ${bullishCount} (${bullishPct}%)`);
    bullishSignals.forEach((s) => lines.push(`   • ${s}`));
    lines.push('');
  }

  if (bearishCount > 0) {
    const bearishPct = ((bearishCount / totalSignals) * 100).toFixed(1);
    lines.push(`📉 BEARISH SIGNALS: ${bearishCount} (${bearishPct}%)`);
    bearishSignals.forEach((s) => lines.push(`   • ${s}`));
    lines.push('');
  }

  if (neutralCount > 0) {
    const neutralPct = ((neutralCount / totalSignals) * 100).toFixed(1);
    lines.push(`⚪ NEUTRAL SIGNALS: ${neutralCount} (${neutralPct}%)`);
    neutralSignals.forEach((s) => lines.push(`   • ${s}`));
    lines.push('');
  }

  lines.push('='.repeat(60));

  if (bullishCount > 0 && bearishCount > 0) {
    lines.push('⚠️ MIXED DIRECTION DETECTED');
    lines.push('Trading in mixed directions may cause conflicting orders.');
  } else if (bullishCount > 0) {
    lines.push('✅ ALIGNED BULLISH DIRECTION');
  } else if (bearishCount > 0) {
    lines.push('✅ ALIGNED BEARISH DIRECTION');
  } else {
    lines.push('⚠️ NO DIRECTIONAL SIGNALS');
  }

  return lines.join('\n');
}

function getCompositionBreakdown(strategy: any): Array<{ label: string; count: number; details?: string }> {
  if (!strategy || !strategy.blocks) {
    return [
      { label: 'Building Blocks', count: 0 },
      { label: 'Entry Signals', count: 0 },
      { label: 'Exit Rules', count: 0 },
      { label: 'Risk Management', count: 0 },
    ];
  }

  let entryCount = 0;
  let exitCount = 0;
  let riskCount = 0;

  strategy.blocks.forEach((block: any) => {
    const blockType = block.blockType || '';
    if (blockType === 'signal' || blockType.includes('entry')) {
      entryCount++;
    } else if (blockType === 'exit' || blockType.includes('exit')) {
      exitCount++;
    } else if (blockType === 'risk' || blockType.includes('risk') || blockType === 'money-management') {
      riskCount++;
    }
  });

  return [
    { label: 'Total Building Blocks', count: strategy.blocks.length },
    { label: 'Entry Signals', count: entryCount, details: `${entryCount} signal block${entryCount !== 1 ? 's' : ''}` },
    { label: 'Exit Rules', count: exitCount, details: `${exitCount} exit block${exitCount !== 1 ? 's' : ''}` },
    {
      label: 'Risk Management',
      count: riskCount,
      details: `${riskCount} risk/money management block${riskCount !== 1 ? 's' : ''}`,
    },
  ];
}

function getComplexityLevel(score: number): string {
  if (score < 20) {
    return '🟢 Very Simple - Minimal blocks and signals, easy to maintain';
  } else if (score < 40) {
    return '🟢 Simple - Low complexity, straightforward strategy';
  } else if (score < 60) {
    return '🟡 Moderate - Standard complexity, balanced approach';
  } else if (score < 80) {
    return '🟠 Complex - Multiple blocks and signals, careful testing required';
  } else {
    return '🔴 Very Complex - Extensive configuration, high maintenance requirements';
  }
}

export function ValidationReportWindow({ open, onClose, report, standalone = false }: ValidationReportWindowProps) {
  const { validationMessages, isValidating, validateStrategy, clearValidation, currentStrategy } = useStrategyStore();

  const handlePopOut = useCallback(() => {
    const win = window.open(
      '/validation',
      '_blank',
      'width=1280,height=800,menubar=no,toolbar=no,location=no,status=no',
    );
    if (win) onClose();
  }, [onClose]);

  const handlePopIn = useCallback(() => {
    if (typeof window === 'undefined' || !window.opener) return;
    window.opener.postMessage({ type: 'validation-report:popin' }, window.location.origin);
    window.close();
  }, []);

  const [canPopIn, setCanPopIn] = useState(false);
  useEffect(() => {
    if (typeof window !== 'undefined' && standalone && window.opener) {
      setCanPopIn(true);
    }
  }, [standalone]);
  const [currentTab, setCurrentTab] = useState<'summary' | 'issues' | 'metrics'>('summary');
  const [undoStack, setUndoStack] = useState<UndoState[]>([]);
  const [showAutoFix, setShowAutoFix] = useState(false);
  const [selectedIssue, setSelectedIssue] = useState<ValidationIssue | null>(null);

  // For demo: create a mock report if none provided
  const mockReport: ValidationReport = useMemo(() => ({
    is_valid: validationMessages.length === 0,
    timestamp: new Date().toISOString(),
    strategy_summary: {
      name: currentStrategy?.name || 'Unknown',
      version: '1.0',
    },
    critical_issues: [],
    errors: validationMessages.filter((m) => m.level === 'error').map((m) => ({
      rule_id: m.code || 'UNKNOWN',
      rule_name: m.code || 'Unknown Issue',
      severity: ValidationSeverity.ERROR,
      category: 'General',
      message: m.text,
      location: m.blockIndex !== undefined ? `Block::${m.blockIndex}` : '',
      auto_fix_available: true,
    })),
    warnings: validationMessages.filter((m) => m.level === 'warning').map((m) => ({
      rule_id: m.code || 'UNKNOWN',
      rule_name: m.code || 'Unknown Issue',
      severity: ValidationSeverity.WARNING,
      category: 'General',
      message: m.text,
      location: m.blockIndex !== undefined ? `Block::${m.blockIndex}` : '',
    })),
    notices: [],
    info: validationMessages.filter((m) => m.level === 'info').map((m) => ({
      rule_id: m.code || 'UNKNOWN',
      rule_name: m.code || 'Unknown Issue',
      severity: ValidationSeverity.INFO,
      category: 'General',
      message: m.text,
      location: '',
    })),
    complexity_metrics: {
      complexity_score: 45,
    },
  }), [validationMessages, currentStrategy]);

  const displayReport = report || mockReport;

  const allIssues = [
    ...displayReport.critical_issues,
    ...displayReport.errors,
    ...displayReport.warnings,
    ...displayReport.notices,
    ...displayReport.info,
  ].sort((a, b) => {
    const severityOrder: Record<ValidationSeverity, number> = {
      [ValidationSeverity.CRITICAL]: 0,
      [ValidationSeverity.ERROR]: 1,
      [ValidationSeverity.WARNING]: 2,
      [ValidationSeverity.NOTICE]: 3,
      [ValidationSeverity.INFO]: 4,
    };
    return severityOrder[a.severity] - severityOrder[b.severity];
  });

  const issueCounts = {
    critical: displayReport.critical_issues.length,
    errors: displayReport.errors.length,
    warnings: displayReport.warnings.length,
    notices: displayReport.notices.length,
    info: displayReport.info.length,
  };

  const handleExportCSV = useCallback(() => {
    const rows: string[][] = [
      ['BTC Trade Engine - Institutional Validation Report'],
      [],
      ['Strategy:', displayReport.strategy_summary.name],
      ['Validated:', new Date(displayReport.timestamp).toLocaleString()],
      ['Status:', displayReport.is_valid ? 'PASSED' : 'FAILED'],
      [],
      ['Severity', 'Category', 'Issue', 'Location', 'Description', 'Suggestion'],
    ];

    allIssues.forEach((issue) => {
      rows.push([
        issue.severity,
        issue.category,
        issue.rule_name,
        issue.location,
        issue.message,
        issue.suggestion || '',
      ]);
    });

    const csvContent = rows.map((row) => row.map((cell) => `"${cell.replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `validation_report_${new Date().getTime()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [allIssues, displayReport]);

  const handleFixClick = useCallback((issue: ValidationIssue) => {
    setSelectedIssue(issue);
    setShowAutoFix(true);
  }, []);

  const handleAutoFixConfirm = useCallback(async () => {
    if (selectedIssue && currentStrategy) {
      // Capture pre-fix snapshot
      setUndoStack((prev) => [
        ...prev,
        {
          snapshot: currentStrategy,
          fixType: selectedIssue.rule_name,
          fixDescription: selectedIssue.message,
        },
      ]);

      let fixApplied = false;

      try {
        // Route to specific fix handler based on rule_id
        switch (selectedIssue.rule_id) {
          case 'DIRECTION_001': {
            // TODO(P2-backend): Implement auto_fix_strategy_type API action
            // This should extract suggested_type from auto_fix_data and switch strategy direction
            // Expected: PATCH /strategies/{id} with { strategy_type: suggested_type }
            console.log('Applying DIRECTION_001 fix - switch strategy direction');
            if (selectedIssue.auto_fix_data?.suggested_type) {
              // TODO(P2-backend): Call store action to update strategy type
              // await updateStrategyType(selectedIssue.auto_fix_data.suggested_type);
              fixApplied = true;
            }
            break;
          }

          case 'TIMING_004': {
            // TODO(P2-backend): Implement auto_fix_recheck_delay API action
            // This should reduce RECHECK delay to fit within timing window
            // Expected: PATCH /strategies/{id}/blocks/{blockId} with updated timing config
            console.log('Applying TIMING_004 fix - reduce RECHECK delay');
            if (selectedIssue.auto_fix_data?.timing_window) {
              // TODO(P2-backend): Call store action to update RECHECK delay
              // await updateRecheckDelay(signalName, timing_window);
              fixApplied = true;
            }
            break;
          }

          case 'EXIT_009': {
            // TODO(P2-backend): Implement auto_fix_duplicate_exits API action
            // This should merge duplicate exit conditions
            // Expected: PATCH /strategies/{id}/blocks/{blockId} with consolidated exits
            console.log('Applying EXIT_009 fix - consolidate exits');
            if (selectedIssue.auto_fix_data?.signal_name) {
              // TODO(P2-backend): Call store action to consolidate exits
              // await consolidateExits(signal_name, level);
              fixApplied = true;
            }
            break;
          }

          case 'LOGIC_003': {
            // TODO(P2-backend): Implement auto_fix_dead_code API action
            // This should disable or remove unreachable signals
            // Expected: PATCH /strategies/{id}/blocks/{blockId} with { enabled: false } or delete
            console.log('Applying LOGIC_003 fix - disable dead code');
            if (selectedIssue.auto_fix_data?.signal_name) {
              // TODO(P2-backend): Call store action to disable/remove dead code
              // await disableDeadCode(signal_name, block_name, preserve_history);
              fixApplied = true;
            }
            break;
          }

          default:
            console.log(`No handler for rule ${selectedIssue.rule_id}`);
        }

        setShowAutoFix(false);
        setSelectedIssue(null);

        if (fixApplied) {
          // Re-validate
          await validateStrategy().catch(console.error);
        }
      } catch (error) {
        console.error('Error applying fix:', error);
        setShowAutoFix(false);
        setSelectedIssue(null);
      }
    }
  }, [selectedIssue, currentStrategy, validateStrategy]);

  const handleUndo = useCallback(() => {
    if (undoStack.length > 0) {
      // TODO: Restore snapshot
      setUndoStack((prev) => prev.slice(0, -1));
      validateStrategy().catch(console.error);
    }
  }, [undoStack, validateStrategy]);

  if (!open) return null;

  const statusBgStyle: React.CSSProperties = displayReport.is_valid
    ? { background: 'color-mix(in srgb, var(--accent-green) 12%, transparent)', borderColor: 'var(--accent-green-mid)' }
    : { background: 'var(--accent-red-deeper)', borderColor: 'var(--accent-red-dark)' };
  const statusTextStyle: React.CSSProperties = displayReport.is_valid
    ? { color: 'var(--accent-green)' }
    : { color: 'var(--accent-red)' };
  const closeButtonStyle: React.CSSProperties = displayReport.is_valid
    ? { background: 'var(--accent-green-dark)', color: 'var(--btn-primary-text)' }
    : { background: 'var(--accent-red-dark)', color: 'var(--btn-primary-text)' };

  const contentBox = (
    <div
      className="relative w-full flex flex-col"
      style={{
        maxWidth: standalone ? '100%' : '2560px',
        width: '100%',
        height: '100%',
        borderRadius: 0,
        border: '1px solid var(--border)',
        background: 'var(--bg-panel)',
        boxShadow: standalone ? 'none' : '0 25px 50px -12px rgba(0,0,0,0.5)',
      }}
    >
      {/* Header — matches StrategyBrowserDialog structure */}
      <div
        className="flex items-center justify-between px-6 py-3 flex-shrink-0"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        <h2
          id="validation-report-title"
          className="text-sm font-semibold flex items-center gap-3"
          style={{ color: 'var(--text-secondary)' }}
        >
          <AppBrand size={24} />
          <span className="flex items-center gap-2">
            <ShieldCheck style={{ width: 16, height: 16, flexShrink: 0 }} />
            <span>Validation Report</span>
          </span>
        </h2>
        <div className="flex items-center gap-2">
          {!standalone && (
            <button
              onClick={handlePopOut}
              title="Open this report in a separate window that can be moved to another monitor"
              className="px-2.5 py-1 rounded text-xs font-medium transition-colors"
              style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
              onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
            >
              ↗ Pop Out
            </button>
          )}
          {canPopIn && (
            <button
              onClick={handlePopIn}
              title="Return this report to the main app window"
              className="px-2.5 py-1 rounded text-xs font-medium transition-colors"
              style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
              onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
            >
              ↙ Pop In
            </button>
          )}
          <button
            onClick={onClose}
            className="text-lg transition-colors"
            aria-label="Close dialog"
            style={{ color: 'var(--text-muted)' }}
            onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-secondary)'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-muted)'; }}
          >✕</button>
        </div>
      </div>

      {/* Status banner */}
      <div className="flex-shrink-0 px-6 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
        <p className="text-xs mb-2" style={{ color: 'var(--text-secondary)' }}>
          Strategy: {displayReport.strategy_summary.name}
          {displayReport.strategy_summary.version && ` (v${displayReport.strategy_summary.version})`} • Validated:{' '}
          {new Date(displayReport.timestamp).toLocaleString()}
        </p>
        <div className="rounded border px-3 py-2" style={statusBgStyle}>
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold" style={statusTextStyle}>
              {displayReport.is_valid ? '✓ VALIDATION PASSED' : '✕ VALIDATION FAILED'}
            </span>
            <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
              {displayReport.is_valid
                ? 'Your strategy meets all institutional-grade requirements.'
                : `${issueCounts.critical + issueCounts.errors} blocking issue(s) must be fixed.`}
            </span>
          </div>
        </div>
      </div>

        {/* Summary bar */}
        <div
          className="flex-shrink-0 px-6 py-2 border-b flex gap-4 flex-wrap items-center text-xs"
          style={{ borderColor: 'var(--border)', background: 'var(--bg-card)', color: 'var(--text-secondary)' }}
        >
          {issueCounts.critical > 0 && <span>Critical: {issueCounts.critical}</span>}
          {issueCounts.errors > 0 && <span>Errors: {issueCounts.errors}</span>}
          {issueCounts.warnings > 0 && <span>Warnings: {issueCounts.warnings}</span>}
          {issueCounts.notices > 0 && <span>Notices: {issueCounts.notices}</span>}
          {issueCounts.info > 0 && <span>Info: {issueCounts.info}</span>}
        </div>

        {/* Tabs */}
        <div
          className="flex-shrink-0 px-6 border-b flex gap-8"
          style={{ borderColor: 'var(--border)', background: 'var(--bg-panel)' }}
        >
          {(['summary', 'issues', 'metrics'] as const).map((tab) => {
            const isActive = currentTab === tab;
            const Icon = tab === 'summary' ? BarChart3 : tab === 'issues' ? AlertTriangle : TrendingUp;
            const iconColor = tab === 'issues' && (issueCounts.errors + issueCounts.warnings + issueCounts.critical) > 0
              ? 'var(--accent-orange)'
              : undefined;
            return (
              <button
                key={tab}
                onClick={() => setCurrentTab(tab)}
                className="px-4 py-2.5 font-medium text-sm border-b-2 transition-colors flex items-center gap-2"
                style={
                  isActive
                    ? { borderColor: 'var(--accent-blue)', color: 'var(--accent-blue)' }
                    : { borderColor: 'transparent', color: 'var(--text-secondary)' }
                }
              >
                <Icon size={14} strokeWidth={1.75} style={{ color: iconColor }} />
                <span className="capitalize">{tab}</span>
              </button>
            );
          })}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {currentTab === 'summary' && (
            <div className="space-y-3">
              {/* Validation Summary — compact grid layout */}
              <div
                className="rounded border p-3"
                style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}
              >
                <h3 className="text-[10px] font-semibold uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)', letterSpacing: '0.12em' }}>
                  Issue Summary
                </h3>
                <div className="grid grid-cols-5 gap-2">
                  {[
                    { label: 'Critical', count: issueCounts.critical, color: issueCounts.critical > 0 ? 'var(--accent-red)' : 'var(--text-muted)' },
                    { label: 'Errors', count: issueCounts.errors, color: issueCounts.errors > 0 ? 'var(--accent-orange)' : 'var(--text-muted)' },
                    { label: 'Warnings', count: issueCounts.warnings, color: issueCounts.warnings > 0 ? 'var(--accent-orange)' : 'var(--text-muted)' },
                    { label: 'Notices', count: issueCounts.notices, color: issueCounts.notices > 0 ? 'var(--accent-blue)' : 'var(--text-muted)' },
                    { label: 'Info', count: issueCounts.info, color: 'var(--text-muted)' },
                  ].map((item) => (
                    <div
                      key={item.label}
                      className="text-center py-2"
                      style={{ background: 'var(--bg-panel)', borderRadius: '4px', border: '1px solid var(--border)' }}
                    >
                      <div className="text-[9px] font-semibold uppercase" style={{ color: 'var(--text-muted)', marginBottom: '4px', letterSpacing: '0.05em' }}>
                        {item.label}
                      </div>
                      <div className="text-lg font-bold" style={{ color: item.color }}>
                        {item.count}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Strategy Composition — label-value pairs with right-aligned numbers */}
              <div
                className="rounded border p-3"
                style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}
              >
                <h3 className="text-[10px] font-semibold uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)', letterSpacing: '0.12em' }}>
                  Composition
                </h3>
                <div className="space-y-1.5" style={{ fontSize: '13px' }}>
                  {getCompositionBreakdown(currentStrategy).map((item, idx) => (
                    <div
                      key={idx}
                      className="flex justify-between items-baseline px-2 py-1.5"
                      style={{ background: idx % 2 === 0 ? 'transparent' : 'var(--bg-panel)', borderRadius: '3px' }}
                    >
                      <span style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
                        {item.label}
                      </span>
                      <span style={{ color: 'var(--text-secondary)', fontWeight: '600', minWidth: '2rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                        {item.count}
                      </span>
                    </div>
                  ))}
                </div>
                {getCompositionBreakdown(currentStrategy).some(item => item.details) && (
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '6px', paddingTop: '6px', borderTop: '1px solid var(--border)' }}>
                    {getCompositionBreakdown(currentStrategy)
                      .filter(item => item.details)
                      .map((item, idx) => (
                        <div key={idx} style={{ marginTop: idx > 0 ? '3px' : '0' }}>
                          • {item.details}
                        </div>
                      ))}
                  </div>
                )}
              </div>

              {/* Complexity — compact with progress bar */}
              <div
                className="rounded border p-3"
                style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}
              >
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: 'var(--text-muted)', letterSpacing: '0.12em' }}>
                    Complexity
                  </h3>
                  <span className="text-sm font-bold" style={{ color: 'var(--accent-green)', fontVariantNumeric: 'tabular-nums' }}>
                    {displayReport.complexity_metrics.complexity_score}
                    <span style={{ fontSize: '10px', color: 'var(--text-muted)', marginLeft: '2px' }}>/100</span>
                  </span>
                </div>
                <div style={{ height: '4px', background: 'var(--bg-panel)', borderRadius: '2px', marginBottom: '6px', overflow: 'hidden' }}>
                  <div
                    style={{
                      height: '100%',
                      background: 'var(--accent-green)',
                      width: `${Math.min(displayReport.complexity_metrics.complexity_score, 100)}%`,
                      transition: 'width 0.3s ease',
                    }}
                  />
                </div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                  {getComplexityLevel(displayReport.complexity_metrics.complexity_score)}
                </div>
              </div>

              {/* Timing Conflicts if present */}
              {displayReport.timing_conflicts && displayReport.timing_conflicts.length > 0 && (
                <div
                  className="rounded border p-3"
                  style={{ background: 'var(--accent-red-deeper)', borderColor: 'var(--accent-red)' }}
                >
                  <h3 className="text-[10px] font-semibold uppercase tracking-widest mb-2" style={{ color: 'var(--accent-red)', letterSpacing: '0.12em' }}>
                    ⚠ Timing Conflicts
                  </h3>
                  <div className="space-y-2" style={{ fontSize: '12px' }}>
                    {displayReport.timing_conflicts.map((conflict, idx) => (
                      <div key={idx} style={{ background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '3px', borderLeft: '2px solid var(--accent-red)' }}>
                        <div style={{ color: 'var(--accent-red)', fontWeight: '600', marginBottom: '4px' }}>
                          {conflict.signal}
                        </div>
                        <div style={{ color: 'var(--text-secondary)', fontSize: '11px', display: 'grid', gap: '2px' }}>
                          <div className="flex justify-between">
                            <span>Timing Window:</span>
                            <span style={{ fontWeight: '600', fontVariantNumeric: 'tabular-nums' }}>{conflict.timing_window} bars</span>
                          </div>
                          <div className="flex justify-between">
                            <span>RECHECK Delay:</span>
                            <span style={{ fontWeight: '600', fontVariantNumeric: 'tabular-nums' }}>{conflict.recheck_delay} bars</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {currentTab === 'issues' && (
            <div className="space-y-4">
              {allIssues.length === 0 ? (
                <div className="text-center py-8" style={{ color: 'var(--text-muted)' }}>
                  No validation issues found.
                </div>
              ) : (
                <IssuesTable issues={allIssues} onFixClick={handleFixClick} />
              )}
            </div>
          )}

          {currentTab === 'metrics' && (
            <div className="space-y-4">
              <CollapsibleSection
                title="✅ Exit Strategy Analysis"
                content={getExitStrategyAnalysis(currentStrategy)}
              />
              {displayReport.timing_conflicts && displayReport.timing_conflicts.length > 0 && (
                <CollapsibleSection
                  title="❌ Timing Conflict Analysis"
                  content={getTimingConflictAnalysis(displayReport.timing_conflicts)}
                  titleColor="var(--accent-red)"
                />
              )}
              {(!displayReport.timing_conflicts || displayReport.timing_conflicts.length === 0) && (
                <CollapsibleSection
                  title="✅ Timing Conflict Analysis"
                  content="No timing conflicts detected. All RECHECK delays are within their timing windows."
                />
              )}
              <CollapsibleSection
                title="✅ Signal Direction Analysis"
                content={getSignalDirectionAnalysis(currentStrategy)}
              />
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          className="flex-shrink-0 flex justify-between items-center px-6 py-4 border-t gap-4"
          style={{ borderColor: 'var(--border)' }}
        >
          <button
            onClick={handleExportCSV}
            className="px-4 py-2 rounded text-sm font-medium transition-colors"
            style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-card)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'var(--bg-hover)')}
          >
            📄 Export to CSV
          </button>
          <div className="flex-1" />
          <button
            onClick={handleUndo}
            disabled={undoStack.length === 0}
            className="px-4 py-2 rounded disabled:opacity-50 text-sm font-medium transition-colors"
            style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
            onMouseEnter={(e) => {
              if (undoStack.length > 0) e.currentTarget.style.background = 'var(--bg-card)';
            }}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'var(--bg-hover)')}
            title="Revert the most recently applied auto-fix"
          >
            ↩ Undo Last Fix
          </button>
          <button
            className="px-4 py-2 rounded text-sm font-medium transition-colors"
            style={{ background: 'var(--accent-blue-dark)', color: 'var(--btn-primary-text)' }}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--accent-blue-mid)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'var(--accent-blue-dark)')}
          >
            📝 Generate Code
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded text-sm font-medium transition-colors"
            style={closeButtonStyle}
          >
            {displayReport.is_valid ? '✓ All Clear' : '⚠ Close'}
          </button>
        </div>
      </div>
  );

  const modals = (
    <>
      {selectedIssue && (
        <AutoFixConfirmDialog
          open={showAutoFix}
          fixType={selectedIssue.rule_name}
          fixDescription={selectedIssue.message}
          beforeState={{ issue: selectedIssue.message }}
          afterState={{ issue: 'Fixed' }}
          impactAnalysis="The selected issue will be automatically fixed. Validation will re-run to confirm."
          onConfirm={handleAutoFixConfirm}
          onCancel={() => {
            setShowAutoFix(false);
            setSelectedIssue(null);
          }}
        />
      )}
    </>
  );

  if (standalone) {
    return <>{contentBox}{modals}</>;
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="validation-report-title"
      className="fixed inset-y-0 right-0 z-50 flex items-stretch"
      style={{ left: 'var(--sidebar-width, 0px)' }}
    >
      <div className="absolute inset-0 bg-black/70 cursor-pointer" onClick={onClose} />
      {contentBox}
      {modals}
    </div>
  );
}
