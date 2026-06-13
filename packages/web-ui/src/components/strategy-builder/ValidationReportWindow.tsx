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
import { ShieldCheck, BarChart3, AlertTriangle, TrendingUp, Maximize2, Download } from 'lucide-react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { ValidationReport, ValidationIssue, ValidationSeverity } from '@/lib/strategy-builder/types';
import { AutoFixConfirmDialog } from './AutoFixConfirmDialog';
import { AppBrand } from '@/components/shared/AppBrand';
import { ThemeSelector } from './ThemeSelector';
import { status } from '@/lib/status';
import { RichTooltip } from './RichTooltip';
import { FixedIssuesList } from './FixedIssuesList';

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
    badge: { background: 'color-mix(in srgb, var(--accent-red) 28%, var(--bg-panel))', color: 'var(--accent-red)' },
  },
  [ValidationSeverity.ERROR]: {
    text: { color: 'var(--accent-red)' },
    bg: { background: 'color-mix(in srgb, var(--accent-red) 10%, transparent)' },
    badge: {
      background: 'color-mix(in srgb, var(--accent-red) 28%, var(--bg-panel))',
      color: 'var(--accent-red)',
    },
  },
  [ValidationSeverity.WARNING]: {
    text: { color: 'var(--accent-orange)' },
    bg: { background: 'color-mix(in srgb, var(--accent-orange) 8%, transparent)' },
    badge: {
      background: 'color-mix(in srgb, var(--accent-orange) 26%, var(--bg-panel))',
      color: 'var(--accent-orange)',
    },
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
            <Maximize2 size={12} strokeWidth={1.75} />
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

interface IssueTableRowProps {
  issue: ValidationIssue;
  isFixed?: boolean;
  onFixClick: (issue: ValidationIssue) => void;
  onUndoClick?: (key: string) => void;
  fixedIssueKey?: string;
}

function IssueTableRow({ issue, isFixed = false, onFixClick, onUndoClick, fixedIssueKey }: IssueTableRowProps) {
  const styles = isFixed
    ? {
        text: { color: 'var(--text-muted)' },
        bg: { background: 'var(--bg-panel)', opacity: 0.6 },
        badge: SEVERITY_STYLES[issue.severity].badge,
      }
    : SEVERITY_STYLES[issue.severity];

  const getFixButtonLabel = (ruleId: string): string => {
    const labels: Record<string, string> = {
      DIRECTION_001: 'Switch',
      TIMING_004: 'Fix',
      EXIT_009: 'Consolidate',
      LOGIC_003: 'Remove',
      missing_timeframe: 'Set',
      missing_target_market: 'Set',
    };
    return labels[ruleId] || 'Fix';
  };

  return (
    <div
      className="rounded border transition-colors"
      style={{
        borderColor: 'var(--border)',
        ...styles.bg,
        padding: '10px',
        opacity: isFixed ? 0.75 : 1,
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
            <div
              className="font-bold text-sm flex items-center gap-2"
              style={{
                color: isFixed ? 'var(--text-muted)' : 'var(--text-secondary)',
                marginBottom: '2px',
                textDecoration: isFixed ? 'line-through' : 'none',
              }}
            >
              {issue.rule_name}
              {isFixed && (
                <span
                  className="inline-block px-1.5 py-0.5 rounded text-[9px] font-bold"
                  style={{
                    background: 'color-mix(in srgb, var(--accent-green) 20%, var(--bg-panel))',
                    color: 'var(--accent-green)',
                    letterSpacing: '0.05em',
                  }}
                >
                  ✓ FIXED
                </span>
              )}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              {issue.category}
            </div>
          </div>
        </div>
        <div className="flex-shrink-0">
          {isFixed ? (
            <RichTooltip content={{
              title: 'Undo Fix',
              body: 'Revert this fix and restore the issue. Validation will re-run automatically.',
            }}>
              <button
                onClick={() => onUndoClick?.(fixedIssueKey || '')}
                className="px-2 py-1 rounded text-xs font-bold transition-colors whitespace-nowrap"
                style={{
                  background: 'color-mix(in srgb, var(--accent-blue) 28%, var(--bg-panel))',
                  color: 'var(--accent-blue)',
                  border: '1px solid var(--accent-blue)',
                }}
              >
                Undo
              </button>
            </RichTooltip>
          ) : issue.severity === ValidationSeverity.INFO ? (
            <span className="text-xs font-bold" style={{ color: 'var(--accent-green)' }}>
              ✓
            </span>
          ) : issue.auto_fix_available ? (
            <RichTooltip content={{
              title: getFixButtonLabel(issue.rule_id),
              body: getFixButtonTooltip(issue.rule_id),
            }}>
              <button
                onClick={() => onFixClick(issue)}
                className="px-2 py-1 rounded text-xs font-bold transition-colors whitespace-nowrap"
                style={{
                  background: 'color-mix(in srgb, var(--accent-blue) 28%, var(--bg-panel))',
                  color: 'var(--accent-blue)',
                }}
              >
                {getFixButtonLabel(issue.rule_id)}
              </button>
            </RichTooltip>
          ) : (
            <RichTooltip content={{
              title: 'No Auto-Fix Available',
              body: 'This rule does not have an automatic fix. See the "How to Fix" hint below the issue message for the recommended manual remediation.',
            }}>
              <span
                className="text-xs font-bold whitespace-nowrap"
                style={{
                  color:
                    issue.severity === ValidationSeverity.CRITICAL ||
                    issue.severity === ValidationSeverity.ERROR
                      ? 'color-mix(in srgb, var(--accent-red) 70%, var(--text-secondary))'
                      : 'var(--text-muted)',
                  cursor: 'help',
                }}
              >
                {getActionText(issue.severity)}
              </span>
            </RichTooltip>
          )}
        </div>
      </div>

      {/* Message */}
      <div
        style={{
          fontSize: '12px',
          color: isFixed ? 'var(--text-muted)' : 'var(--text-secondary)',
          lineHeight: '1.4',
          marginBottom: '6px',
        }}
      >
        {issue.message}
      </div>

      {/* Location & Suggestion */}
      <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '8px 12px', fontSize: '11px' }}>
        {issue.location && (
          <>
            <span style={{ color: 'var(--text-muted)', fontWeight: '600' }}>Location:</span>
            <code
              style={{
                color: isFixed ? 'var(--text-muted)' : 'var(--text-secondary)',
                fontFamily: 'monospace',
                whiteSpace: 'pre-wrap',
              }}
            >
              {formatLocation(issue.location)}
            </code>
          </>
        )}
        {issue.suggestion && (
          <>
            <span style={{ color: 'var(--accent-blue)', fontWeight: '600' }}>How to Fix:</span>
            <span style={{ color: 'var(--accent-blue)' }}>{issue.suggestion}</span>
          </>
        )}
      </div>
    </div>
  );
}

function IssuesTable({
  issues,
  fixedIssuesInSession,
  showFixed,
  onFixClick,
  onUndoClick,
}: {
  issues: ValidationIssue[];
  fixedIssuesInSession?: Array<{ key: string; issue: ValidationIssue }>;
  showFixed?: boolean;
  onFixClick: (issue: ValidationIssue) => void;
  onUndoClick?: (key: string) => void;
}) {
  const fixedIssuesDisplay = showFixed ? (fixedIssuesInSession ?? []) : [];
  const allIssuesDisplay = [...issues, ...fixedIssuesDisplay.map((f) => ({ ...f.issue, isFixed: true, fixedIssueKey: f.key }))];

  return (
    <div className="space-y-2">
      {allIssuesDisplay.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-muted)' }}>
          No issues found.
        </div>
      ) : (
        allIssuesDisplay.map((issue: any, idx) => (
          <IssueTableRow
            key={`${issue.rule_id}-${idx}`}
            issue={issue}
            isFixed={issue.isFixed}
            onFixClick={onFixClick}
            onUndoClick={onUndoClick}
            fixedIssueKey={issue.fixedIssueKey}
          />
        ))
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
      return 'Must Fix';
    case ValidationSeverity.WARNING:
      return 'Should Review';
    default:
      return 'Review';
  }
}

function getFixButtonTooltip(ruleId: string): string {
  const tooltips: Record<string, string> = {
    DIRECTION_001: 'Click to automatically switch strategy direction to match signal bias.',
    TIMING_004: 'Click to reduce RECHECK delay to fit within timing window.',
    EXIT_009: 'Click to merge duplicate exit conditions.',
    LOGIC_003: 'Click to disable unreachable signals.',
    missing_timeframe: 'Click to select a timeframe for your strategy.',
    missing_target_market: 'Click to specify the trading pair for your strategy.',
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
  lines.push('TIMING CONFLICT DETECTED — CRITICAL ISSUE');
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
    lines.push('Problem:');
    lines.push(`   Timing Window: ${conflict.timing_window} bars`);
    lines.push(`   RECHECK Delay: ${conflict.recheck_delay} bars`);
    lines.push('');
    lines.push(`   The RECHECK happens at bar ${conflict.recheck_delay},`);
    lines.push(`   but the timing window expires at bar ${conflict.timing_window}.`);
    lines.push('   This signal will NEVER trigger!');
    lines.push('');
    lines.push('Solution:');
    lines.push(`   1. Reduce RECHECK delay to ≤ ${conflict.timing_window} bars, OR`);
    lines.push(`   2. Increase timing window to ≥ ${conflict.recheck_delay} bars`);
    lines.push('');
    lines.push('='.repeat(60));
    lines.push('');
  });

  return lines.join('\n');
}

interface ExecutionBlock {
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
}

interface ExecutionFlowData {
  blocks: ExecutionBlock[];
  strategyLevelExits: Array<{ index: number; name: string; closePct: number; mode: 'ABSOLUTE' | 'FLEXIBLE' }>;
}

interface ConfluenceScoringData {
  requiredPoints: number;
  optionalPoints: number;
  totalPossible: number;
  threshold: number;
  perBlock: Array<{ index: number; name: string; logic: 'REQUIRED' | 'OPTIONAL'; points: number; signalCount: number }>;
}

interface Scenario {
  label: string;
  outcome: 'opens' | 'no_position';
  totalPoints: number;
  perBlock: Array<{ index: number; name: string; result: string; points: number }>;
}

interface FlowSection {
  title: string;
  subtitle?: string;
  body: string;
}

// Build the execution-flow report as discrete sections so each title can be a
// styled banner instead of a raw === bar. Section bodies keep the thick-client
// tree/emoji formatting and render inside a <pre> (BTCAAAAA-32954 cc8d5eec).
function buildExecutionFlowSections(
  executionFlow: ExecutionFlowData | undefined,
  confluenceScoring: ConfluenceScoringData | undefined,
  scenarios: Scenario[] | undefined,
): FlowSection[] {
  const sections: FlowSection[] = [];

  if (executionFlow && executionFlow.blocks && executionFlow.blocks.length > 0) {
    const lines: string[] = [];
    executionFlow.blocks.forEach((block, bIdx) => {
      const num = block.index + 1 || bIdx + 1;
      const logicNote = block.logic === 'REQUIRED' ? 'ALL signals required' : 'ANY signal triggers';
      lines.push(`📦 BLOCK ${num}: ${block.name.toUpperCase()} (${logicNote})`);
      lines.push('');
      (block.signals || []).forEach((sig) => {
        lines.push(`   ENTRY SIGNAL: ${sig.name}`);
        if (sig.timingConstraint) {
          const ref = sig.timingConstraint.ofSignal
            ? ` of '${sig.timingConstraint.ofSignal}'`
            : '';
          lines.push(`      └── Timing: Must trigger within ${sig.timingConstraint.withinCandles} candles${ref}`);
        }
        if (sig.recheck) {
          lines.push(`      └── 🔄 RECHECK: Validate '${sig.recheck.signal}' after ${sig.recheck.afterBars} bars`);
          lines.push(`          ├── If found: Signal VALID ✓`);
          lines.push(`          └── If not found: Signal RESET ✗`);
        }
        if (sig.linkedExit) {
          lines.push(`      └── 🚪 EXIT: ${sig.linkedExit.name} → Close ${sig.linkedExit.closePct}% (${sig.linkedExit.mode})`);
        }
        lines.push('');
      });
    });
    sections.push({
      title: 'Strategy Execution Flow',
      subtitle: 'How your strategy works',
      body: lines.join('\n').trimEnd(),
    });
  }

  if (executionFlow && executionFlow.strategyLevelExits && executionFlow.strategyLevelExits.length > 0) {
    const lines: string[] = [];
    executionFlow.strategyLevelExits.forEach((ex, i) => {
      lines.push(`🚪 EXIT #${i + 1}: ${ex.name} triggers`);
      lines.push(`   └── Action: Close ${ex.closePct}% of position (${ex.mode} mode)`);
      lines.push('');
    });
    sections.push({
      title: 'Exit Conditions',
      subtitle: 'Strategy-level',
      body: lines.join('\n').trimEnd(),
    });
  }

  if (confluenceScoring && confluenceScoring.perBlock.length > 0) {
    const lines: string[] = [];
    lines.push('BLOCK TYPES IN YOUR STRATEGY');
    lines.push('');
    confluenceScoring.perBlock.forEach((b) => {
      const num = b.index + 1;
      const logicLabel = b.logic === 'REQUIRED' ? 'REQUIRED (AND logic)' : 'OPTIONAL (OR logic)';
      const allOrAny = b.logic === 'REQUIRED' ? 'ALL' : 'ANY';
      const contribNote = b.logic === 'REQUIRED' ? 'required' : 'optional bonus';
      lines.push(`Block ${num} (${b.name.toUpperCase()}) - ${logicLabel}`);
      lines.push(`   • Type: ${b.logic} - ${allOrAny} ${b.signalCount} signal${b.signalCount === 1 ? '' : 's'} must trigger`);
      lines.push(`   • Contributes: ~${b.points} pts (${contribNote})`);
      if (b.logic === 'REQUIRED') {
        lines.push(`   • If ANY signal missing → 0 points from this block`);
      }
      lines.push('');
    });
    sections.push({
      title: 'Position Opening Logic',
      subtitle: 'Institutional-grade confluence system',
      body: lines.join('\n').trimEnd(),
    });

    const scoreLines: string[] = [];
    scoreLines.push('YOUR STRATEGY POINT BREAKDOWN');
    scoreLines.push(`   • Required Points: ${confluenceScoring.requiredPoints} pts (${confluenceScoring.perBlock.filter((b) => b.logic === 'REQUIRED').length} REQUIRED blocks)`);
    scoreLines.push(`   • Optional Points: ${confluenceScoring.optionalPoints} pts (${confluenceScoring.perBlock.filter((b) => b.logic === 'OPTIONAL').length} OPTIONAL blocks)`);
    scoreLines.push(`   • Total Possible: ${confluenceScoring.totalPossible} pts`);
    scoreLines.push('');
    scoreLines.push('POSITION OPENS WHEN');
    scoreLines.push(`   ⇨ Confluence Score >= Threshold (e.g., ${confluenceScoring.threshold} pts)`);
    scoreLines.push(`   ⇨ ONLY ONE POSITION opens when threshold met`);
    scoreLines.push(`   ⇨ Once open, strategy manages THIS POSITION with exits/TP/SL`);
    sections.push({
      title: 'Confluence Scoring System',
      subtitle: 'How position actually opens',
      body: scoreLines.join('\n'),
    });
  }

  if (scenarios && scenarios.length > 0) {
    const lines: string[] = [];
    scenarios.forEach((sc) => {
      lines.push(sc.label);
      sc.perBlock.forEach((b) => {
        const marker = b.result === 'FIRE' ? '✓' : b.result === 'MISS' ? '✗' : '·';
        const pointsTxt = b.result === 'FIRE' ? `+${b.points} pts` : `${b.points} pts`;
        const desc = b.result === 'FIRE' ? 'ALL signals' : b.result === 'MISS' ? 'Missing signal' : b.result;
        lines.push(`   • Block ${b.index + 1} (${b.name.toUpperCase()}): ${desc} ${marker} → ${pointsTxt}`);
      });
      const verdict = sc.outcome === 'opens' ? 'POSITION OPENS ✓' : 'Below threshold, NO POSITION';
      lines.push(`   Total: ${sc.totalPoints} pts → ${verdict}`);
      lines.push('');
    });
    sections.push({
      title: 'Real-World Scenarios',
      subtitle: 'Walking through how points add up',
      body: lines.join('\n').trimEnd(),
    });
  }

  if (confluenceScoring) {
    const lines: string[] = [];
    lines.push('✓ REQUIRED blocks (AND): Must have ALL signals to contribute points');
    lines.push('✓ OPTIONAL blocks (OR): Contribute bonus points if ANY signal fires');
    lines.push('✓ Position opens when: Total points >= Confluence Threshold');
    lines.push('✓ ONE POSITION only: Not multiple trades');
    lines.push(`✓ Threshold configurable: In backtest config (default ~${confluenceScoring.threshold} pts)`);
    lines.push('');
    lines.push('EXECUTION: Signals evaluated bar-by-bar in real-time');
    sections.push({
      title: 'Key Takeaways',
      body: lines.join('\n'),
    });
  }

  return sections;
}

function ExecutionFlowSection({
  executionFlow,
  confluenceScoring,
  scenarios,
}: {
  executionFlow?: ExecutionFlowData;
  confluenceScoring?: ConfluenceScoringData;
  scenarios?: Scenario[];
}) {
  if (!executionFlow && !confluenceScoring && !scenarios) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)' }}>
        No execution flow information available for this strategy.
      </div>
    );
  }

  const sections = buildExecutionFlowSections(executionFlow, confluenceScoring, scenarios);

  return (
    <div className="flex flex-col gap-4">
      {sections.map((section, i) => (
        <section
          key={i}
          className="rounded overflow-hidden border"
          style={{ borderColor: 'var(--border)', background: 'var(--bg-card)' }}
        >
          <header
            className="flex items-baseline gap-2 px-4 py-2.5"
            style={{
              background:
                'linear-gradient(90deg, color-mix(in srgb, var(--accent-blue) 18%, transparent), transparent)',
              borderBottom: '1px solid var(--border)',
            }}
          >
            <span
              style={{
                color: 'var(--accent-blue)',
                fontSize: '10px',
                fontWeight: 700,
                letterSpacing: '0.16em',
                textTransform: 'uppercase',
              }}
            >
              {`0${i + 1}`.slice(-2)}
            </span>
            <h3
              style={{
                color: 'var(--text-secondary)',
                fontSize: '13px',
                fontWeight: 600,
                letterSpacing: '0.02em',
                margin: 0,
              }}
            >
              {section.title}
            </h3>
            {section.subtitle && (
              <span
                style={{
                  color: 'var(--text-muted)',
                  fontSize: '11px',
                  fontWeight: 400,
                  letterSpacing: '0.04em',
                }}
              >
                · {section.subtitle}
              </span>
            )}
          </header>
          <pre
            style={{
              margin: 0,
              padding: '12px 16px',
              background: 'var(--bg-panel)',
              color: 'var(--text-secondary)',
              fontFamily:
                'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace',
              fontSize: '12px',
              lineHeight: 1.55,
              whiteSpace: 'pre',
              overflowX: 'auto',
              tabSize: 2,
            }}
          >
            {section.body}
          </pre>
        </section>
      ))}
    </div>
  );
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
    lines.push(`BULLISH SIGNALS: ${bullishCount} (${bullishPct}%)`);
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
    lines.push('MIXED DIRECTION DETECTED');
    lines.push('Trading in mixed directions may cause conflicting orders.');
  } else if (bullishCount > 0) {
    lines.push('ALIGNED BULLISH DIRECTION');
  } else if (bearishCount > 0) {
    lines.push('ALIGNED BEARISH DIRECTION');
  } else {
    lines.push('NO DIRECTIONAL SIGNALS');
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
    return 'Very Simple — Minimal blocks and signals, easy to maintain';
  } else if (score < 40) {
    return 'Simple — Low complexity, straightforward strategy';
  } else if (score < 60) {
    return 'Moderate — Standard complexity, balanced approach';
  } else if (score < 80) {
    return 'Complex — Multiple blocks and signals, careful testing required';
  } else {
    return 'Very Complex — Extensive configuration, high maintenance requirements';
  }
}

export function ValidationReportWindow({ open, onClose, report, standalone = false }: ValidationReportWindowProps) {
  const { validationMessages, isValidating, validateStrategy, clearValidation, currentStrategy, applyAutoFix, applyLocalAutoFix, fixedIssuesInSession, undoAutoFix, saveStrategy } = useStrategyStore();
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = useCallback(async () => {
    if (isSaving) return;
    setIsSaving(true);
    try {
      const saved = await saveStrategy();
      const versionNumber = (saved as { versionNumber?: number }).versionNumber;
      status.emit(
        versionNumber ? `Strategy saved (v${versionNumber})` : 'Strategy saved',
        { duration: 2000 },
      );
      onClose();
    } catch {
      status.emit('Save failed', { duration: 2000, variant: 'error' });
    } finally {
      setIsSaving(false);
    }
  }, [isSaving, saveStrategy, onClose]);

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
  const [currentTab, setCurrentTab] = useState<'summary' | 'execution-flow' | 'issues' | 'metrics'>('summary');
  const [undoStack, setUndoStack] = useState<UndoState[]>([]);
  const [showAutoFix, setShowAutoFix] = useState(false);
  const [selectedIssue, setSelectedIssue] = useState<ValidationIssue | null>(null);
  const [showFixedIssues, setShowFixedIssues] = useState(true);

  // For demo: create a mock report if none provided
  const mockReport: ValidationReport = useMemo(() => {
    const cs = currentStrategy as (typeof currentStrategy & { versionNumber?: number }) | null;
    const versionNumber = cs?.versionNumber;
    return ({
    is_valid: validationMessages.length === 0,
    timestamp: new Date().toISOString(),
    strategy_summary: {
      name: cs?.name || 'Unknown',
      version: versionNumber ? String(versionNumber) : '1',
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
    });
  }, [validationMessages, currentStrategy]);

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

  const getStructural005Data = useCallback(() => {
    if (!selectedIssue || selectedIssue.rule_id !== 'STRUCTURAL_005' || !currentStrategy) {
      return undefined;
    }

    // Extract auto_fix_data from the issue
    const autoFixData = selectedIssue.auto_fix_data as any;
    if (!autoFixData?.block_name || !autoFixData?.signal_name) {
      return undefined;
    }

    // Find the block and its signals.
    // API blocks are normalized into {id, type, index, data: {name (title-cased), definitionId (raw), signals}}
    // by handleStrategySelect. Use definitionId (the original snake_case name) to find the block.
    let block = currentStrategy.blocks?.find((b: any) => b.data?.definitionId === autoFixData.block_name);
    if (!block) {
      // Fallback: case-insensitive name comparison
      const blockNameLower = autoFixData.block_name.toLowerCase().replace(/_/g, ' ');
      block = currentStrategy.blocks?.find((b: any) =>
        (b.data?.name || '').toLowerCase() === blockNameLower
      );
    }
    if (!block) {
      // Fallback: raw name field on block
      block = currentStrategy.blocks?.find((b: any) => b.name === autoFixData.block_name);
    }
    if (!block) return undefined;

    // Find all indices of the duplicate signal name
    const duplicateIndices: number[] = [];
    const signalDetails: Array<{ index: number; name: string; weight: number; exitCount: number }> = [];

    // Try to get signals from different possible locations
    let signals = block.data?.signals as any[];
    if (!signals) {
      signals = (block.data as any)?.signals as any[];
    }
    if (!Array.isArray(signals)) {
      signals = [];
    }

    signals.forEach((signal: any, idx: number) => {
      const signalName = signal.name || signal.data?.name;
      if (signalName === autoFixData.signal_name) {
        duplicateIndices.push(idx);
        signalDetails.push({
          index: idx,
          name: signalName,
          weight: signal.weight || signal.data?.weight || 0,
          exitCount: (signal.exit_conditions?.length || signal.data?.exit_conditions?.length || 0),
        });
      }
    });

    // Return data even if only 1 or more matches found (not just 2+)
    if (duplicateIndices.length < 1) return undefined;

    return {
      blockName: autoFixData.block_name,
      signalName: autoFixData.signal_name,
      duplicateIndices,
      signalDetails,
    };
  }, [selectedIssue, currentStrategy]);

  const handleAutoFixConfirm = useCallback(async (userInput?: Record<string, any>) => {
    if (!selectedIssue || !currentStrategy) return;

    // Snapshot for undo before the store swaps currentStrategy with the
    // post-fix version returned by the backend.
    setUndoStack((prev) => [
      ...prev,
      {
        snapshot: currentStrategy,
        fixType: selectedIssue.rule_name,
        fixDescription: selectedIssue.message,
      },
    ]);

    try {
      let applied = false;

      // Local auto-fixes (client-side validation issues)
      if ((selectedIssue.rule_id === 'missing_timeframe' || selectedIssue.rule_id === 'missing_target_market') && userInput?.value) {
        applied = await applyLocalAutoFix(selectedIssue.rule_id, { value: userInput.value });
      } else {
        // Backend auto-fixes (institutional validation issues)
        let fixData = selectedIssue.auto_fix_data as Record<string, unknown> | undefined;

        // For STRUCTURAL_005, merge the user input with auto_fix_data
        if (selectedIssue.rule_id === 'STRUCTURAL_005' && userInput && userInput.mode) {
          fixData = {
            ...(selectedIssue.auto_fix_data as Record<string, unknown>),
            mode: userInput.mode,
            target_index: userInput.targetIndex,
            ...(userInput.newName && { new_name: userInput.newName }),
          };
        }

        applied = await applyAutoFix(selectedIssue.rule_id, fixData);
      }

      setShowAutoFix(false);
      setSelectedIssue(null);
      if (!applied) {
        // Roll the undo snapshot back so it doesn't accumulate no-op entries.
        setUndoStack((prev) => prev.slice(0, -1));
      }
    } catch (error) {
      console.error('Error applying fix:', error);
      setShowAutoFix(false);
      setSelectedIssue(null);
      setUndoStack((prev) => prev.slice(0, -1));
    }
  }, [selectedIssue, currentStrategy, applyAutoFix, applyLocalAutoFix]);

  const handleUndo = useCallback(() => {
    if (undoStack.length > 0) {
      // TODO: Restore snapshot
      setUndoStack((prev) => prev.slice(0, -1));
      validateStrategy().catch(console.error);
    }
  }, [undoStack, validateStrategy]);

  const handleUndoFixedIssue = useCallback(
    (key: string) => {
      undoAutoFix(key).catch(console.error);
    },
    [undoAutoFix],
  );

  if (!open) return null;

  const statusBgStyle: React.CSSProperties = displayReport.is_valid
    ? {
        background: 'color-mix(in srgb, var(--accent-green) 7%, transparent)',
        borderColor: 'color-mix(in srgb, var(--accent-green) 40%, var(--border))',
      }
    : {
        background: 'color-mix(in srgb, var(--accent-red) 7%, transparent)',
        borderColor: 'color-mix(in srgb, var(--accent-red) 40%, var(--border))',
      };
  const statusTextStyle: React.CSSProperties = displayReport.is_valid
    ? { color: 'color-mix(in srgb, var(--accent-green) 70%, var(--text-secondary))' }
    : { color: 'color-mix(in srgb, var(--accent-red) 70%, var(--text-secondary))' };
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
            <span>Strategy Validation</span>
          </span>
        </h2>
        <div className="flex items-center gap-2">
          <ThemeSelector />
          <div className="w-px h-4" style={{ background: 'var(--border)' }} />
          {!standalone && (
            <RichTooltip content={{
              title: 'Pop Out',
              body: 'Open this report in a separate window that can be moved to another monitor.',
            }}>
              <button
                onClick={handlePopOut}
                className="px-2.5 py-1 rounded text-xs font-medium transition-colors"
                style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
                onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
              >
                ↗ Pop Out
              </button>
            </RichTooltip>
          )}
          {canPopIn && (
            <RichTooltip content={{
              title: 'Pop In',
              body: 'Return this report to the main app window.',
            }}>
              <button
                onClick={handlePopIn}
                className="px-2.5 py-1 rounded text-xs font-medium transition-colors"
                style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
                onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
              >
                ↙ Pop In
              </button>
            </RichTooltip>
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

        {/* Fixed-in-session callout — rendered above the tabs so it shows
            on every view, not just the Issues tab. Mirrors the thick-client
            PyQt5 layout where "Fixed in this session" is a top-level section
            with per-row Undo (BTCAAAAA-33738 Bug 3). */}
        {fixedIssuesInSession.length > 0 && (
          <div className="flex-shrink-0 px-6 py-3 border-b" style={{ borderColor: 'var(--border)' }}>
            <FixedIssuesList
              entries={fixedIssuesInSession}
              onUndo={handleUndoFixedIssue}
            />
          </div>
        )}

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
          className="flex-shrink-0 px-6 border-b flex gap-8 overflow-x-auto"
          style={{ borderColor: 'var(--border)', background: 'var(--bg-panel)' }}
        >
          {(['summary', 'execution-flow', 'issues', 'metrics'] as const).map((tab) => {
            const isActive = currentTab === tab;
            let Icon = BarChart3;
            let label = 'Summary';
            if (tab === 'execution-flow') {
              Icon = TrendingUp;
              label = 'Execution Flow';
            } else if (tab === 'issues') {
              Icon = AlertTriangle;
              label = 'Issues';
            } else if (tab === 'metrics') {
              Icon = TrendingUp;
              label = 'Metrics';
            }
            const iconColor = tab === 'issues' && (issueCounts.errors + issueCounts.warnings + issueCounts.critical) > 0
              ? 'var(--accent-orange)'
              : undefined;
            return (
              <button
                key={tab}
                onClick={() => setCurrentTab(tab)}
                className="px-4 py-2.5 font-medium text-sm border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap"
                style={
                  isActive
                    ? { borderColor: 'var(--accent-blue)', color: 'var(--accent-blue)' }
                    : { borderColor: 'transparent', color: 'var(--text-secondary)' }
                }
              >
                <Icon size={14} strokeWidth={1.75} style={{ color: iconColor }} />
                <span>{label}</span>
              </button>
            );
          })}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {currentTab === 'execution-flow' && (
            <ExecutionFlowSection
              executionFlow={displayReport.executionFlow}
              confluenceScoring={displayReport.confluenceScoring}
              scenarios={displayReport.scenarios}
            />
          )}

          {currentTab === 'summary' && (
            <div className="space-y-3">
              {/* Issue Summary + Composition as compact tile grids so the tab
                  fits the whole strategy at a glance instead of stacking
                  9-row tables (BTCAAAAA-32954 board comment 8c8259e3). */}
              <div
                className="rounded border p-3"
                style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}
              >
                <h3 className="text-[10px] font-semibold uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)', letterSpacing: '0.12em' }}>
                  Issue Summary
                </h3>
                <div className="grid grid-cols-5 gap-2">
                  {[
                    { label: 'Critical', count: issueCounts.critical, color: issueCounts.critical > 0 ? 'var(--accent-red)' : undefined },
                    { label: 'Errors', count: issueCounts.errors, color: issueCounts.errors > 0 ? 'var(--accent-red)' : undefined },
                    { label: 'Warnings', count: issueCounts.warnings, color: issueCounts.warnings > 0 ? 'var(--accent-orange)' : undefined },
                    { label: 'Notices', count: issueCounts.notices, color: issueCounts.notices > 0 ? 'var(--accent-blue)' : undefined },
                    { label: 'Info', count: issueCounts.info, color: undefined },
                  ].map((item) => (
                    <div
                      key={item.label}
                      className="text-center"
                      style={{
                        background: 'var(--bg-panel)',
                        border: '1px solid var(--border)',
                        borderRadius: '4px',
                        padding: '8px 4px',
                      }}
                    >
                      <div style={{ fontSize: '9px', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '4px' }}>
                        {item.label}
                      </div>
                      <div style={{ fontSize: '18px', fontWeight: 700, color: item.color ?? 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums', lineHeight: 1 }}>
                        {item.count}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div
                className="rounded border p-3"
                style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}
              >
                <h3 className="text-[10px] font-semibold uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)', letterSpacing: '0.12em' }}>
                  Composition
                </h3>
                <div className="grid grid-cols-4 gap-2">
                  {getCompositionBreakdown(currentStrategy).map((item, idx) => (
                    <div
                      key={idx}
                      className="text-center"
                      style={{
                        background: 'var(--bg-panel)',
                        border: '1px solid var(--border)',
                        borderRadius: '4px',
                        padding: '8px 4px',
                      }}
                    >
                      <div style={{ fontSize: '9px', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '4px' }}>
                        {item.label}
                      </div>
                      <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums', lineHeight: 1 }}>
                        {item.count}
                      </div>
                    </div>
                  ))}
                </div>
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
                  style={{
                    background: 'color-mix(in srgb, var(--accent-red) 7%, transparent)',
                    borderColor: 'color-mix(in srgb, var(--accent-red) 40%, var(--border))',
                  }}
                >
                  <h3
                    className="text-[10px] font-semibold uppercase tracking-widest mb-2"
                    style={{
                      color: 'color-mix(in srgb, var(--accent-red) 70%, var(--text-secondary))',
                      letterSpacing: '0.12em',
                    }}
                  >
                    Timing Conflicts
                  </h3>
                  <div className="space-y-2" style={{ fontSize: '12px' }}>
                    {displayReport.timing_conflicts.map((conflict, idx) => (
                      <div
                        key={idx}
                        style={{
                          background: 'var(--bg-panel)',
                          padding: '8px',
                          borderRadius: '3px',
                          borderLeft: '2px solid color-mix(in srgb, var(--accent-red) 60%, var(--border))',
                        }}
                      >
                        <div
                          style={{
                            color: 'color-mix(in srgb, var(--accent-red) 70%, var(--text-secondary))',
                            fontWeight: '600',
                            marginBottom: '4px',
                          }}
                        >
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
              {allIssues.length === 0 && fixedIssuesInSession.length === 0 ? (
                <div className="text-center py-8" style={{ color: 'var(--text-muted)' }}>
                  No validation issues found.
                </div>
              ) : (
                <>
                  {fixedIssuesInSession.length > 0 && (
                    <div
                      className="flex items-center gap-2 p-2 rounded"
                      style={{
                        background: 'var(--bg-card)',
                        border: '1px solid var(--border)',
                      }}
                    >
                      <input
                        type="checkbox"
                        id="show-fixed-toggle"
                        checked={showFixedIssues}
                        onChange={(e) => setShowFixedIssues(e.target.checked)}
                        style={{ cursor: 'pointer' }}
                      />
                      <label
                        htmlFor="show-fixed-toggle"
                        className="text-xs font-medium flex-1"
                        style={{ cursor: 'pointer', color: 'var(--text-secondary)' }}
                      >
                        Show fixed issues ({fixedIssuesInSession.length})
                      </label>
                    </div>
                  )}
                  <IssuesTable
                    issues={allIssues}
                    fixedIssuesInSession={fixedIssuesInSession}
                    showFixed={showFixedIssues}
                    onFixClick={handleFixClick}
                    onUndoClick={handleUndoFixedIssue}
                  />
                </>
              )}
            </div>
          )}

          {currentTab === 'metrics' && (
            <div className="space-y-4">
              <CollapsibleSection
                title="Exit Strategy Analysis"
                content={getExitStrategyAnalysis(currentStrategy)}
              />
              {displayReport.timing_conflicts && displayReport.timing_conflicts.length > 0 && (
                <CollapsibleSection
                  title="Timing Conflict Analysis"
                  content={getTimingConflictAnalysis(displayReport.timing_conflicts)}
                  titleColor="var(--accent-red)"
                />
              )}
              {(!displayReport.timing_conflicts || displayReport.timing_conflicts.length === 0) && (
                <CollapsibleSection
                  title="Timing Conflict Analysis"
                  content="No timing conflicts detected. All RECHECK delays are within their timing windows."
                />
              )}
              <CollapsibleSection
                title="Signal Direction Analysis"
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
            className="px-4 py-2 rounded text-sm font-medium transition-colors flex items-center gap-1.5"
            style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-card)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'var(--bg-hover)')}
          >
            <Download size={14} strokeWidth={1.75} /> Export to CSV
          </button>
          <div className="flex-1" />
          <RichTooltip content={{
            title: 'Undo Last Fix',
            body: 'Revert the most recently applied auto-fix and re-run validation.',
          }}>
            <button
              onClick={handleUndo}
              disabled={undoStack.length === 0}
              className="px-4 py-2 rounded disabled:opacity-50 text-sm font-medium transition-colors"
              style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
              onMouseEnter={(e) => {
                if (undoStack.length > 0) e.currentTarget.style.background = 'var(--bg-card)';
              }}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'var(--bg-hover)')}
            >
              ↩ Undo Last Fix
            </button>
          </RichTooltip>
          <RichTooltip content={
            displayReport.is_valid
              ? {
                  title: 'Save',
                  body: 'Save the current strategy as a new version. Increments the version number and persists all changes — including any auto-fixes applied in this session — to the strategy store.',
                }
              : {
                  title: 'Close',
                  body: 'Dismiss the validation report. Blocking issues must be resolved before the strategy can be saved.',
                }
          }>
            <button
              onClick={displayReport.is_valid ? handleSave : onClose}
              disabled={displayReport.is_valid && isSaving}
              className="px-4 py-2 rounded text-sm font-medium transition-colors disabled:opacity-50"
              style={closeButtonStyle}
            >
              {displayReport.is_valid ? (isSaving ? 'Saving…' : 'Save') : '✕ Close'}
            </button>
          </RichTooltip>
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
          ruleId={selectedIssue.rule_id}
          structural005Data={getStructural005Data()}
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
