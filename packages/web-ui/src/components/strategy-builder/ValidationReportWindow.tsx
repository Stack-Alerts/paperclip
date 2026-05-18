'use client';

import { useMemo, useState, useCallback, useRef, useEffect } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { ValidationReport, ValidationIssue, ValidationSeverity } from '@/lib/strategy-builder/types';
import { AutoFixConfirmDialog } from './AutoFixConfirmDialog';

export interface ValidationReportWindowProps {
  open: boolean;
  onClose: () => void;
  report?: ValidationReport;
}

// Severity colors matching PyQt5 implementation
const SEVERITY_COLORS: Record<ValidationSeverity, { text: string; bg: string; badge: string }> = {
  [ValidationSeverity.CRITICAL]: {
    text: 'text-red-500',
    bg: 'bg-red-950/30',
    badge: 'bg-red-500 text-white',
  },
  [ValidationSeverity.ERROR]: {
    text: 'text-orange-500',
    bg: 'bg-orange-950/30',
    badge: 'bg-orange-500 text-white',
  },
  [ValidationSeverity.WARNING]: {
    text: 'text-amber-500',
    bg: 'bg-amber-950/30',
    badge: 'bg-amber-500 text-white',
  },
  [ValidationSeverity.NOTICE]: {
    text: 'text-blue-500',
    bg: 'bg-blue-950/30',
    badge: 'bg-blue-500 text-white',
  },
  [ValidationSeverity.INFO]: {
    text: 'text-zinc-500',
    bg: 'bg-zinc-800/30',
    badge: 'bg-zinc-600 text-white',
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
  titleColor = '#095983',
}: {
  title: string;
  content: string;
  defaultExpanded?: boolean;
  onMaximize?: () => void;
  titleColor?: string;
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className="border border-zinc-700 rounded-lg bg-zinc-800/50 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 bg-zinc-900/50">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 flex-1 text-left hover:opacity-80 transition-opacity"
        >
          <span className="text-lg">{isExpanded ? '▼' : '▶'}</span>
          <h3 className="font-bold text-sm" style={{ color: titleColor }}>
            {title}
          </h3>
        </button>
        {onMaximize && (
          <button
            onClick={onMaximize}
            className="px-3 py-1 rounded bg-zinc-700 hover:bg-zinc-600 text-white text-xs font-medium transition-colors"
          >
            🗖 Maximize
          </button>
        )}
      </div>
      {isExpanded && (
        <div className="px-4 py-3 bg-zinc-950/50 border-t border-zinc-700">
          <pre className="text-xs text-zinc-300 font-mono overflow-x-auto whitespace-pre-wrap break-words">
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
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b border-zinc-700 bg-zinc-900/50">
            <th className="px-4 py-3 text-left font-bold text-zinc-300">Severity</th>
            <th className="px-4 py-3 text-left font-bold text-zinc-300">Category</th>
            <th className="px-4 py-3 text-left font-bold text-zinc-300">Issue</th>
            <th className="px-4 py-3 text-left font-bold text-zinc-300">Location</th>
            <th className="px-4 py-3 text-left font-bold text-zinc-300">Description & Guidance</th>
            <th className="px-4 py-3 text-left font-bold text-zinc-300">Action</th>
          </tr>
        </thead>
        <tbody>
          {issues.map((issue, idx) => {
            const colors = SEVERITY_COLORS[issue.severity];
            return (
              <tr key={`${issue.rule_id}-${idx}`} className={`border-b border-zinc-700/50 ${colors.bg} hover:bg-zinc-700/20`}>
                <td className="px-4 py-3 font-bold">
                  <span className={`inline-block px-2 py-1 rounded text-xs font-bold ${colors.badge}`}>
                    {issue.severity}
                  </span>
                </td>
                <td className="px-4 py-3 text-zinc-300">{issue.category}</td>
                <td className="px-4 py-3 font-bold text-zinc-200">{issue.rule_name}</td>
                <td className="px-4 py-3 text-zinc-400 text-xs font-mono whitespace-pre-wrap">
                  {formatLocation(issue.location)}
                </td>
                <td className="px-4 py-3 text-zinc-300 max-w-md">
                  <div className="whitespace-normal break-words">
                    {issue.message}
                    {issue.suggestion && (
                      <div className="mt-2 pt-2 border-t border-zinc-600 text-xs text-blue-400">
                        💡 How to Fix: {issue.suggestion}
                      </div>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  {issue.severity === ValidationSeverity.INFO ? (
                    <span className="text-green-500 font-bold text-xs">✓ Passed</span>
                  ) : issue.auto_fix_available ? (
                    <button
                      onClick={() => onFixClick(issue)}
                      className="px-3 py-1 rounded bg-amber-700 hover:bg-amber-600 text-white text-xs font-bold transition-colors"
                      title={getFixButtonTooltip(issue.rule_id)}
                    >
                      🔧 Fix Now
                    </button>
                  ) : (
                    <span className={`text-xs font-bold ${issue.severity === ValidationSeverity.CRITICAL || issue.severity === ValidationSeverity.ERROR ? 'text-red-500' : 'text-zinc-500'}`}>
                      {getActionText(issue.severity)}
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
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

export function ValidationReportWindow({ open, onClose, report }: ValidationReportWindowProps) {
  const { validationMessages, isValidating, validateStrategy, clearValidation, currentStrategy } = useStrategyStore();
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
    if (selectedIssue) {
      // Capture pre-fix snapshot
      setUndoStack((prev) => [
        ...prev,
        {
          snapshot: currentStrategy,
          fixType: selectedIssue.rule_name,
          fixDescription: selectedIssue.message,
        },
      ]);

      // TODO: Apply fix based on rule_id
      // This will be wired to actual fix functions

      setShowAutoFix(false);
      setSelectedIssue(null);

      // Re-validate
      await validateStrategy().catch(console.error);
    }
  }, [selectedIssue, currentStrategy, validateStrategy]);

  const handleUndo = useCallback(() => {
    if (undoStack.length > 0) {
      const lastUndo = undoStack[undoStack.length - 1];
      // TODO: Restore snapshot
      setUndoStack((prev) => prev.slice(0, -1));
      validateStrategy().catch(console.error);
    }
  }, [undoStack, validateStrategy]);

  if (!open) return null;

  const statusColor = displayReport.is_valid
    ? 'bg-emerald-950/30 border-emerald-700'
    : 'bg-red-950/30 border-red-700';
  const statusText = displayReport.is_valid
    ? 'text-emerald-500'
    : 'text-red-500';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="relative w-full max-w-6xl h-[90vh] rounded-lg border border-zinc-700 bg-zinc-900 shadow-2xl mx-4 flex flex-col">
        {/* Header */}
        <div className="flex-shrink-0 px-6 py-4 border-b border-zinc-700">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xl font-bold text-blue-400">💼 Validation Report</h2>
            <button
              onClick={onClose}
              className="text-zinc-400 hover:text-zinc-200 transition-colors text-2xl"
              aria-label="Close"
            >
              ✕
            </button>
          </div>
          <p className="text-xs text-zinc-500 mb-3">
            Strategy: {displayReport.strategy_summary.name}
            {displayReport.strategy_summary.version && ` (v${displayReport.strategy_summary.version})`} • Validated:{' '}
            {new Date(displayReport.timestamp).toLocaleString()}
          </p>
          <div className={`rounded border ${statusColor} p-3`}>
            <div className="flex items-center gap-3">
              <span className={`text-lg font-bold ${statusText}`}>
                {displayReport.is_valid ? '✅ VALIDATION PASSED' : '❌ VALIDATION FAILED'}
              </span>
              <span className="text-sm text-zinc-400">
                {displayReport.is_valid
                  ? 'Your strategy meets all institutional-grade requirements.'
                  : `${issueCounts.critical + issueCounts.errors} blocking issue(s) must be fixed.`}
              </span>
            </div>
          </div>
        </div>

        {/* Summary bar */}
        <div className="flex-shrink-0 px-6 py-2 border-b border-zinc-700 flex gap-4 bg-zinc-800/20 flex-wrap items-center text-xs text-zinc-300">
          {issueCounts.critical > 0 && <span>Critical: {issueCounts.critical}</span>}
          {issueCounts.errors > 0 && <span>Errors: {issueCounts.errors}</span>}
          {issueCounts.warnings > 0 && <span>Warnings: {issueCounts.warnings}</span>}
          {issueCounts.notices > 0 && <span>Notices: {issueCounts.notices}</span>}
          {issueCounts.info > 0 && <span>Info: {issueCounts.info}</span>}
        </div>

        {/* Tabs */}
        <div className="flex-shrink-0 px-6 border-b border-zinc-700 flex gap-8 bg-zinc-900/50">
          {(['summary', 'issues', 'metrics'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setCurrentTab(tab)}
              className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors ${
                currentTab === tab
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {tab === 'summary' && '📊 Summary'}
              {tab === 'issues' && '⚠️ Issues'}
              {tab === 'metrics' && '📈 Metrics'}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {currentTab === 'summary' && (
            <div className="space-y-6">
              {/* Validation Summary */}
              <div className="bg-zinc-800/30 rounded border border-zinc-700 p-4">
                <h3 className="font-bold text-blue-400 mb-3 text-sm">Validation Summary</h3>
                <div className="grid grid-cols-5 gap-3 text-xs">
                  <div className="bg-zinc-900/50 rounded p-2">
                    <div className="text-red-500 font-bold">Critical</div>
                    <div className="text-xl font-bold text-zinc-300 mt-1">{issueCounts.critical}</div>
                  </div>
                  <div className="bg-zinc-900/50 rounded p-2">
                    <div className="text-orange-500 font-bold">Errors</div>
                    <div className="text-xl font-bold text-zinc-300 mt-1">{issueCounts.errors}</div>
                  </div>
                  <div className="bg-zinc-900/50 rounded p-2">
                    <div className="text-amber-500 font-bold">Warnings</div>
                    <div className="text-xl font-bold text-zinc-300 mt-1">{issueCounts.warnings}</div>
                  </div>
                  <div className="bg-zinc-900/50 rounded p-2">
                    <div className="text-blue-500 font-bold">Notices</div>
                    <div className="text-xl font-bold text-zinc-300 mt-1">{issueCounts.notices}</div>
                  </div>
                  <div className="bg-zinc-900/50 rounded p-2">
                    <div className="text-zinc-500 font-bold">Info</div>
                    <div className="text-xl font-bold text-zinc-300 mt-1">{issueCounts.info}</div>
                  </div>
                </div>
              </div>

              {/* Strategy Composition */}
              <div className="bg-zinc-800/30 rounded border border-zinc-700 p-4">
                <h3 className="font-bold text-blue-400 mb-3 text-sm">Strategy Composition</h3>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="bg-zinc-900/50 rounded p-2">
                    <span className="text-zinc-400">Building Blocks:</span>
                    <div className="text-lg font-bold text-zinc-300 mt-1">{currentStrategy?.blocks.length || 0}</div>
                  </div>
                  <div className="bg-zinc-900/50 rounded p-2">
                    <span className="text-zinc-400">Total Signals:</span>
                    <div className="text-lg font-bold text-zinc-300 mt-1">0</div>
                  </div>
                </div>
              </div>

              {/* Complexity */}
              <div className="bg-zinc-800/30 rounded border border-zinc-700 p-4">
                <h3 className="font-bold text-blue-400 mb-3 text-sm">Strategy Complexity</h3>
                <div className="text-sm text-zinc-300">
                  <span className="font-bold text-emerald-500">{displayReport.complexity_metrics.complexity_score}/100</span>{' '}
                  - Simple to Moderate complexity
                </div>
              </div>
            </div>
          )}

          {currentTab === 'issues' && (
            <div className="space-y-4">
              {allIssues.length === 0 ? (
                <div className="text-center py-8 text-zinc-500">No validation issues found.</div>
              ) : (
                <IssuesTable issues={allIssues} onFixClick={handleFixClick} />
              )}
            </div>
          )}

          {currentTab === 'metrics' && (
            <div className="space-y-4">
              <CollapsibleSection
                title="✅ Exit Strategy Analysis"
                content="Exit strategy analysis data would go here. Showing exit distribution and timing."
              />
              {displayReport.timing_conflicts && displayReport.timing_conflicts.length > 0 && (
                <CollapsibleSection
                  title="❌ Timing Conflict Analysis"
                  content={`Timing conflicts detected:\n${displayReport.timing_conflicts
                    .map((c) => `Signal: ${c.signal}\nTiming Window: ${c.timing_window}\nRECHECK Delay: ${c.recheck_delay}`)
                    .join('\n\n')}`}
                  titleColor="#ef4444"
                />
              )}
              <CollapsibleSection
                title="✅ Signal Direction Analysis"
                content="Signal direction breakdown data would go here."
              />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex-shrink-0 flex justify-between items-center px-6 py-4 border-t border-zinc-700 gap-4">
          <button
            onClick={handleExportCSV}
            className="px-4 py-2 rounded bg-zinc-700 hover:bg-zinc-600 text-white text-sm font-medium transition-colors"
          >
            📄 Export to CSV
          </button>
          <div className="flex-1" />
          <button
            onClick={handleUndo}
            disabled={undoStack.length === 0}
            className="px-4 py-2 rounded bg-zinc-700 hover:bg-zinc-600 disabled:opacity-50 text-white text-sm font-medium transition-colors"
            title="Revert the most recently applied auto-fix"
          >
            ↩ Undo Last Fix
          </button>
          <button
            className="px-4 py-2 rounded bg-blue-700 hover:bg-blue-600 text-white text-sm font-medium transition-colors"
          >
            📝 Generate Code
          </button>
          <button
            onClick={onClose}
            className={`px-4 py-2 rounded text-white text-sm font-medium transition-colors ${
              displayReport.is_valid
                ? 'bg-emerald-700 hover:bg-emerald-600'
                : 'bg-red-700 hover:bg-red-600'
            }`}
          >
            {displayReport.is_valid ? '✓ All Clear' : '⚠ Close'}
          </button>
        </div>
      </div>

      {/* Auto-fix confirmation dialog */}
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
    </div>
  );
}
