'use client';

import { forwardRef, useCallback, useImperativeHandle, useRef, useState } from 'react';
import * as api from '@/lib/strategy-builder/api';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import {
  ValidationLevel,
  ValidationMessage,
  ValidationReport,
  ValidationSeverity,
  ValidationIssue,
  BacktestConfig,
} from '@/lib/strategy-builder/types';
import { InfoTooltip } from './InfoTooltip';

// ---------------------------------------------------------------------------
// Legacy flat-message helpers (existing store uses ValidationMessage[])
// ---------------------------------------------------------------------------

const LEVEL_STYLES: Record<
  ValidationLevel,
  { icon: string; classes: string; rowClasses: string }
> = {
  [ValidationLevel.ERROR]: {
    icon: '✗',
    classes: 'text-red-400',
    rowClasses: 'border-l-2 border-l-red-600 bg-red-950/30',
  },
  [ValidationLevel.WARNING]: {
    icon: '⚠',
    classes: 'text-amber-400',
    rowClasses: 'border-l-2 border-l-amber-600 bg-amber-950/30',
  },
  [ValidationLevel.INFO]: {
    icon: 'ℹ',
    classes: 'text-blue-400',
    rowClasses: 'border-l-2 border-l-blue-600 bg-blue-950/20',
  },
};

interface MessageRowProps {
  message: ValidationMessage;
  onClick?: (msg: ValidationMessage) => void;
}

function MessageRow({ message, onClick }: MessageRowProps) {
  const style = LEVEL_STYLES[message.level];
  return (
    <button
      className={`w-full text-left px-3 py-1.5 flex items-start gap-2 text-xs hover:bg-zinc-800 transition-colors ${style.rowClasses}`}
      onClick={() => onClick?.(message)}
    >
      <span
        className={`flex-shrink-0 font-bold mt-0.5 ${style.classes}`}
        aria-label={message.level}
      >
        {style.icon}
      </span>
      <span className="flex-1 text-zinc-200 leading-relaxed">{message.text}</span>
      {message.blockIndex != null && (
        <span className="flex-shrink-0 text-zinc-500 font-mono">#{message.blockIndex + 1}</span>
      )}
    </button>
  );
}

function summarize(messages: ValidationMessage[]) {
  const errors = messages.filter((m) => m.level === ValidationLevel.ERROR).length;
  const warnings = messages.filter((m) => m.level === ValidationLevel.WARNING).length;
  const infos = messages.filter((m) => m.level === ValidationLevel.INFO).length;
  return { errors, warnings, infos };
}

// ---------------------------------------------------------------------------
// ValidationReport section types (full-parity with PyQt5 panel)
// ---------------------------------------------------------------------------

type SectionStatus = 'pass' | 'warn' | 'error' | 'empty';

interface SectionConfig {
  id: string;
  title: string;
  passTitle: string;
  failTitle: string;
  borderColor: string;
  passColor: string;
  failColor: string;
  warnColor: string;
}

const SECTIONS: SectionConfig[] = [
  {
    id: 'basic',
    title: 'Basic Validation',
    passTitle: '✅ Basic Validation',
    failTitle: '❌ Basic Validation',
    borderColor: 'border-l-green-500',
    passColor: 'text-green-400',
    failColor: 'text-red-400',
    warnColor: 'text-amber-400',
  },
  {
    id: 'standard',
    title: 'Standard Validation',
    passTitle: '✅ Standard Validation',
    failTitle: '❌ Standard Validation',
    borderColor: 'border-l-blue-500',
    passColor: 'text-blue-400',
    failColor: 'text-red-400',
    warnColor: 'text-amber-400',
  },
  {
    id: 'strict',
    title: 'Strict Validation',
    passTitle: '✅ Strict Validation',
    failTitle: '❌ Strict Validation',
    borderColor: 'border-l-purple-500',
    passColor: 'text-purple-400',
    failColor: 'text-red-400',
    warnColor: 'text-amber-400',
  },
  {
    id: 'exit',
    title: 'Exit Condition Validation',
    passTitle: '✅ Exit Condition Validation',
    failTitle: '❌ Exit Condition Validation',
    borderColor: 'border-l-red-500',
    passColor: 'text-green-400',
    failColor: 'text-red-400',
    warnColor: 'text-amber-400',
  },
];

// ---------------------------------------------------------------------------
// Classify issues from a ValidationReport into the four section buckets
// ---------------------------------------------------------------------------

interface SectionIssues {
  basic: ValidationIssue[];
  standard: ValidationIssue[];
  strict: ValidationIssue[];
  exit: ValidationIssue[];
  warnings: ValidationIssue[];
}

function classifyIssues(report: ValidationReport): SectionIssues {
  const allIssues: ValidationIssue[] = [
    ...report.critical_issues,
    ...report.errors,
    ...report.warnings,
    ...report.notices,
    ...report.info,
  ];

  const basic: ValidationIssue[] = [];
  const standard: ValidationIssue[] = [];
  const strict: ValidationIssue[] = [];
  const exit: ValidationIssue[] = [];
  const warnings: ValidationIssue[] = [];

  for (const issue of allIssues) {
    const cat = issue.category?.toLowerCase() ?? '';
    const msg = issue.message?.toLowerCase() ?? '';
    const loc = issue.location?.toLowerCase() ?? '';

    if (
      issue.severity === ValidationSeverity.WARNING ||
      issue.severity === ValidationSeverity.NOTICE ||
      issue.severity === ValidationSeverity.INFO
    ) {
      warnings.push(issue);
    } else if (loc.includes('exit') || cat.includes('exit') || msg.includes('exit')) {
      exit.push(issue);
    } else if (
      cat.includes('circular') ||
      cat.includes('dependency') ||
      msg.includes('circular') ||
      msg.includes('dependency')
    ) {
      strict.push(issue);
    } else if (
      cat.includes('logic') ||
      cat.includes('timing') ||
      cat.includes('duplicate') ||
      msg.includes('logic') ||
      msg.includes('timing') ||
      msg.includes('duplicate')
    ) {
      standard.push(issue);
    } else {
      basic.push(issue);
    }
  }

  return { basic, standard, strict, exit, warnings };
}

// ---------------------------------------------------------------------------
// Section severity helpers
// ---------------------------------------------------------------------------

function severityIcon(sev: ValidationSeverity): string {
  switch (sev) {
    case ValidationSeverity.CRITICAL:
      return '🔴';
    case ValidationSeverity.ERROR:
      return '✗';
    case ValidationSeverity.WARNING:
      return '⚠';
    case ValidationSeverity.NOTICE:
      return '•';
    case ValidationSeverity.INFO:
      return 'ℹ';
    default:
      return '•';
  }
}

function severityTextClass(sev: ValidationSeverity): string {
  switch (sev) {
    case ValidationSeverity.CRITICAL:
    case ValidationSeverity.ERROR:
      return 'text-red-400';
    case ValidationSeverity.WARNING:
      return 'text-amber-400';
    case ValidationSeverity.NOTICE:
      return 'text-blue-300';
    case ValidationSeverity.INFO:
      return 'text-zinc-400';
    default:
      return 'text-zinc-400';
  }
}

// ---------------------------------------------------------------------------
// ReportSection — a styled section card matching PyQt5 _create_validation_section
// ---------------------------------------------------------------------------

interface ReportSectionProps {
  config: SectionConfig;
  issues: ValidationIssue[];
  passItems?: string[];
  hidden?: boolean;
}

function ReportSection({ config, issues, passItems, hidden }: ReportSectionProps) {
  if (hidden) return null;

  const hasErrors = issues.length > 0;
  const titleText = hasErrors ? config.failTitle : config.passTitle;
  const titleColor = hasErrors ? config.failColor : config.passColor;
  const borderColor = hasErrors ? 'border-l-red-500' : config.borderColor;

  return (
    <div
      className={`border border-zinc-700 border-l-4 ${borderColor} rounded bg-zinc-800/60 px-4 py-3 space-y-1.5`}
    >
      <span className={`text-xs font-bold ${titleColor}`}>{titleText}</span>
      {!hasErrors && passItems && passItems.length > 0 && (
        <ul className="space-y-0.5 pl-2">
          {passItems.map((item, i) => (
            <li key={i} className="text-xs text-zinc-400 flex items-start gap-1.5">
              <span className="text-green-500 flex-shrink-0">├─</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      )}
      {hasErrors && (
        <ul className="space-y-1 pl-2">
          {issues.map((issue, i) => (
            <li key={i} className="text-xs flex items-start gap-1.5">
              <span className={`flex-shrink-0 font-bold ${severityTextClass(issue.severity)}`}>
                {severityIcon(issue.severity)}
              </span>
              <div className="flex-1">
                <span className="text-zinc-200">{issue.message}</span>
                {issue.location && (
                  <span className="ml-1.5 text-zinc-500 font-mono text-[10px]">
                    [{issue.location}]
                  </span>
                )}
                {issue.suggestion && (
                  <p className="mt-0.5 text-zinc-500 italic">{issue.suggestion}</p>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// WarningsSection — amber section for warnings / notices / info
// ---------------------------------------------------------------------------

interface WarningsSectionProps {
  issues: ValidationIssue[];
}

function WarningsSection({ issues }: WarningsSectionProps) {
  if (issues.length === 0) return null;
  return (
    <div className="border border-zinc-700 border-l-4 border-l-amber-500 rounded bg-zinc-800/60 px-4 py-3 space-y-1.5">
      <span className="text-xs font-bold text-amber-400">
        ⚠️ Warnings ({issues.length})
      </span>
      <ul className="space-y-1 pl-2">
        {issues.map((issue, i) => (
          <li key={i} className="text-xs flex items-start gap-1.5">
            <span className={`flex-shrink-0 font-bold ${severityTextClass(issue.severity)}`}>
              {severityIcon(issue.severity)}
            </span>
            <span className="flex-1 text-zinc-300">{issue.message}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ---------------------------------------------------------------------------
// External imperative handle (mirrors PyQt5 refresh_from_orchestrator / auto_validate)
// ---------------------------------------------------------------------------

export interface ValidationPanelHandle {
  refresh_from_orchestrator: () => void;
  auto_validate: (enabled: boolean) => void;
}

// ---------------------------------------------------------------------------
// Main ValidationPanel export
// ---------------------------------------------------------------------------

interface ValidationPanelProps {
  currentVersionId?: string;
}

export const ValidationPanel = forwardRef<ValidationPanelHandle, ValidationPanelProps>(
function ValidationPanel({ currentVersionId }, ref) {
  const {
    validationMessages,
    isValidating,
    validateStrategy,
    clearValidation,
    selectBlock,
    saveStrategy,
    runBacktest,
    currentStrategy,
  } = useStrategyStore();

  // ValidationReport is produced by the full report endpoint; this panel
  // also accepts the simpler ValidationMessage[] from the store for
  // backward compatibility. When a full report arrives, it takes priority.
  const [report, setReport] = useState<ValidationReport | null>(null);
  const [lastValidatedAt, setLastValidatedAt] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isBacktesting, setIsBacktesting] = useState(false);
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const autoValidateEnabledRef = useRef(false);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3000);
  };

  const handleValidate = useCallback(async () => {
    try {
      await validateStrategy();
      const now = new Date();
      setLastValidatedAt(now.toLocaleTimeString());
      setReport(null);

      // Persist validation status to strategy_versions (mirrors PyQt5 _save_validation_status)
      if (currentVersionId && currentStrategy) {
        const hasErrors = validationMessages.some((m) => m.level === ValidationLevel.ERROR);
        try {
          await api.patch(`/strategies/${currentStrategy.id}/versions/${currentVersionId}/validation`, {
            validation_status: hasErrors ? 'Fail' : 'Pass',
            validation_timestamp: now.toISOString(),
          });
        } catch {
          // Non-fatal: DB persistence best-effort, don't surface to user
        }
      }
    } catch (err) {
      console.error(err);
    }
  }, [validateStrategy, currentVersionId, currentStrategy, validationMessages]);

  useImperativeHandle(ref, () => ({
    refresh_from_orchestrator: () => {
      handleValidate();
    },
    auto_validate: (enabled: boolean) => {
      autoValidateEnabledRef.current = enabled;
      if (enabled) handleValidate();
    },
  }), [handleValidate]);

  const handleMessageClick = useCallback(
    (msg: ValidationMessage) => {
      if (msg.blockIndex != null) selectBlock(msg.blockIndex);
    },
    [selectBlock],
  );

  const handleSave = useCallback(async () => {
    setIsSaving(true);
    try {
      await saveStrategy();
      showToast('Strategy saved successfully');
    } catch (err) {
      showToast(`Save failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsSaving(false);
    }
  }, [saveStrategy]);

  const handleRunBacktest = useCallback(async () => {
    if (!currentStrategy) {
      showToast('No strategy loaded');
      return;
    }
    setIsBacktesting(true);
    try {
      const config: BacktestConfig = {
        strategyId: currentStrategy.id,
        startDate: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
        endDate: new Date().toISOString().slice(0, 10),
        initialCapital: 10000,
        commissionPercentage: 0.1,
      };
      await runBacktest(config);
      showToast('Backtest started');
    } catch (err) {
      showToast(`Backtest failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsBacktesting(false);
    }
  }, [currentStrategy, runBacktest]);

  const handleGenerateCode = useCallback(() => {
    showToast('Generate Code is a P2 feature — coming soon');
  }, []);

  // Derived state
  const { errors, warnings, infos } = summarize(validationMessages);
  const hasMessages = validationMessages.length > 0;

  // Full report derived
  const classified = report ? classifyIssues(report) : null;
  const hasCriticalOrError =
    report &&
    (report.critical_issues.length > 0 || report.errors.length > 0);
  const nautilusCompatible = report ? !hasCriticalOrError : errors === 0;

  // Action button enablement: enabled after validation if no blocking errors
  const canActOnStrategy = currentStrategy != null && !isValidating;
  const isSafeToSave = canActOnStrategy && errors === 0;
  const isSafeToBacktest = canActOnStrategy;

  return (
    <div className="border-t border-zinc-800 bg-zinc-900 flex flex-col" style={{ maxHeight: '22rem' }}>
      {/* Toast notification */}
      {toastMsg && (
        <div className="absolute bottom-16 right-4 z-50 bg-zinc-700 text-zinc-100 text-xs px-3 py-2 rounded shadow-lg animate-fade-in">
          {toastMsg}
        </div>
      )}

      {/* Toolbar */}
      <div className="flex items-center gap-2 px-4 py-1.5 border-b border-zinc-800 flex-shrink-0">
        <span className="text-xs font-semibold text-zinc-400 flex-1">Validation</span>

        {/* Last validated timestamp */}
        {lastValidatedAt && (
          <span className="text-[10px] text-zinc-600 font-mono">Last: {lastValidatedAt}</span>
        )}

        {/* NautilusTrader compatibility badge */}
        {hasMessages || report ? (
          <span
            className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
              nautilusCompatible
                ? 'bg-green-900/40 text-green-400 border border-green-700'
                : 'bg-red-900/40 text-red-400 border border-red-700'
            }`}
          >
            {nautilusCompatible ? '✅ NT Compatible' : '❌ NT Incompatible'}
          </span>
        ) : null}

        {/* Summary counters */}
        {hasMessages && (
          <div className="flex items-center gap-2 text-xs">
            {errors > 0 && (
              <span className="text-red-400 font-medium">
                {errors} error{errors !== 1 ? 's' : ''}
              </span>
            )}
            {warnings > 0 && (
              <span className="text-amber-400 font-medium">
                {warnings} warning{warnings !== 1 ? 's' : ''}
              </span>
            )}
            {infos > 0 && <span className="text-blue-400">{infos} info</span>}
          </div>
        )}

        <InfoTooltip id="validate-now-btn">
          <button
            onClick={handleValidate}
            disabled={isValidating}
            className="px-2 py-0.5 rounded bg-green-700 hover:bg-green-600 text-white text-xs font-medium disabled:opacity-50 transition-colors"
          >
            {isValidating ? 'Validating…' : 'Validate'}
          </button>
        </InfoTooltip>

        {hasMessages && (
          <InfoTooltip id="clear-validation-btn">
            <button
              onClick={() => {
                clearValidation();
                setReport(null);
                setLastValidatedAt(null);
              }}
              className="px-2 py-0.5 rounded bg-zinc-700 hover:bg-zinc-600 text-zinc-300 text-xs transition-colors"
            >
              Clear
            </button>
          </InfoTooltip>
        )}
      </div>

      {/* Scrollable results area */}
      <div className="overflow-y-auto flex-1 min-h-0">
        {/* No results placeholder */}
        {!hasMessages && !report && !isValidating && (
          <p className="px-4 py-2 text-xs text-zinc-600">
            No validation results — click Validate to run checks.
          </p>
        )}

        {isValidating && (
          <p className="px-4 py-2 text-xs text-zinc-400 animate-pulse">Running validation…</p>
        )}

        {/* Full ValidationReport view — three sections + exit + warnings */}
        {report && classified && (
          <div className="px-4 py-3 space-y-3">
            <ReportSection
              config={SECTIONS[0]}
              issues={classified.basic}
              passItems={['Strategy has name', 'At least one block present', 'All blocks have signals']}
            />
            <ReportSection
              config={SECTIONS[1]}
              issues={classified.standard}
              passItems={['All logic values valid (AND/OR)', 'Timing constraints configured correctly', 'No duplicate names']}
            />
            <ReportSection
              config={SECTIONS[2]}
              issues={classified.strict}
              passItems={['No circular dependencies']}
            />
            <ReportSection
              config={SECTIONS[3]}
              issues={classified.exit}
              hidden={classified.exit.length === 0}
            />
            <WarningsSection issues={classified.warnings} />
          </div>
        )}

        {/* Flat ValidationMessage[] view — legacy / server messages */}
        {!report && hasMessages && (
          <div>
            {validationMessages.map((msg) => (
              <MessageRow key={msg.id} message={msg} onClick={handleMessageClick} />
            ))}
          </div>
        )}
      </div>

      {/* Action buttons row */}
      <div className="flex items-center gap-2 px-4 py-2 border-t border-zinc-800 flex-shrink-0 bg-zinc-900">
        <InfoTooltip id="save-strategy-btn">
          <button
            onClick={handleSave}
            disabled={!isSafeToSave || isSaving}
            className="px-3 py-1 rounded bg-emerald-700 hover:bg-emerald-600 text-white text-xs font-medium disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            title="Save the validated strategy to the database"
          >
            {isSaving ? 'Saving…' : '💾 Save Strategy'}
          </button>
        </InfoTooltip>

        <InfoTooltip id="run-backtest-btn">
          <button
            onClick={handleRunBacktest}
            disabled={!isSafeToBacktest || isBacktesting}
            className="px-3 py-1 rounded bg-blue-700 hover:bg-blue-600 text-white text-xs font-medium disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            title="Run a quick backtest on this strategy"
          >
            {isBacktesting ? 'Starting…' : '▶ Run Backtest'}
          </button>
        </InfoTooltip>

        <InfoTooltip id="generate-code-btn">
          <button
            onClick={handleGenerateCode}
            className="px-3 py-1 rounded bg-zinc-700 hover:bg-zinc-600 text-zinc-300 text-xs font-medium transition-colors"
            title="Generate NautilusTrader Python strategy code (P2 feature)"
          >
            📝 Generate Code
          </button>
        </InfoTooltip>
      </div>
    </div>
  );
});
