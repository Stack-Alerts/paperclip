'use client';

import { forwardRef, useCallback, useImperativeHandle, useRef, useState } from 'react';
import * as api from '@/lib/strategy-builder/api';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { status } from '@/lib/status';
import {
  ValidationLevel,
  ValidationMessage,
  ValidationReport,
  ValidationSeverity,
  ValidationIssue,
  BacktestConfig,
} from '@/lib/strategy-builder/types';
import { InfoTooltip } from './InfoTooltip';
import { FixedIssuesList } from './FixedIssuesList';

// ---------------------------------------------------------------------------
// Legacy flat-message helpers (existing store uses ValidationMessage[])
// ---------------------------------------------------------------------------

const LEVEL_STYLES: Record<
  ValidationLevel,
  { icon: string; color: string; borderColor: string; bgColor: string }
> = {
  [ValidationLevel.ERROR]: {
    icon: '✗',
    color: 'var(--accent-red)',
    borderColor: 'var(--accent-red-dark)',
    bgColor: 'var(--accent-red-deeper)',
  },
  [ValidationLevel.WARNING]: {
    icon: '⚠',
    color: 'var(--accent-orange)',
    borderColor: 'var(--accent-orange)',
    bgColor: 'color-mix(in srgb, var(--accent-orange) 8%, transparent)',
  },
  [ValidationLevel.INFO]: {
    icon: 'ℹ',
    color: 'var(--accent-blue)',
    borderColor: 'var(--accent-blue-dark)',
    bgColor: 'var(--accent-blue-dark)',
  },
};

interface MessageRowProps {
  message: ValidationMessage;
  onClick?: (msg: ValidationMessage) => void;
}

function MessageRow({ message, onClick }: MessageRowProps) {
  const lvlStyle = LEVEL_STYLES[message.level];
  return (
    <button
      className="w-full text-left px-3 py-1.5 flex items-start gap-2 text-xs transition-colors border-l-2"
      style={{ borderColor: lvlStyle.borderColor, background: lvlStyle.bgColor }}
      onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
      onMouseLeave={e => (e.currentTarget.style.background = lvlStyle.bgColor)}
      onClick={() => onClick?.(message)}
    >
      <span
        className="flex-shrink-0 font-bold mt-0.5"
        style={{ color: lvlStyle.color }}
        aria-label={message.level}
      >
        {lvlStyle.icon}
      </span>
      <span className="flex-1 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{message.text}</span>
      {message.blockIndex != null && (
        <span className="flex-shrink-0 font-mono" style={{ color: 'var(--text-muted)' }}>#{message.blockIndex + 1}</span>
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

// eslint-disable-next-line @typescript-eslint/no-unused-vars
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
    borderColor: 'var(--accent-green)',
    passColor: 'var(--accent-green)',
    failColor: 'var(--accent-red)',
    warnColor: 'var(--accent-orange)',
  },
  {
    id: 'standard',
    title: 'Standard Validation',
    passTitle: '✅ Standard Validation',
    failTitle: '❌ Standard Validation',
    borderColor: 'var(--accent-blue)',
    passColor: 'var(--accent-blue)',
    failColor: 'var(--accent-red)',
    warnColor: 'var(--accent-orange)',
  },
  {
    id: 'strict',
    title: 'Strict Validation',
    passTitle: '✅ Strict Validation',
    failTitle: '❌ Strict Validation',
    borderColor: 'var(--accent-teal)',
    passColor: 'var(--accent-teal)',
    failColor: 'var(--accent-red)',
    warnColor: 'var(--accent-orange)',
  },
  {
    id: 'exit',
    title: 'Exit Condition Validation',
    passTitle: '✅ Exit Condition Validation',
    failTitle: '❌ Exit Condition Validation',
    borderColor: 'var(--accent-red)',
    passColor: 'var(--accent-green)',
    failColor: 'var(--accent-red)',
    warnColor: 'var(--accent-orange)',
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

function severityColor(sev: ValidationSeverity): string {
  switch (sev) {
    case ValidationSeverity.CRITICAL:
    case ValidationSeverity.ERROR:
      return 'var(--accent-red)';
    case ValidationSeverity.WARNING:
      return 'var(--accent-orange)';
    case ValidationSeverity.NOTICE:
      return 'var(--accent-blue-mid)';
    case ValidationSeverity.INFO:
      return 'var(--text-secondary)';
    default:
      return 'var(--text-secondary)';
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
  const leftBorderColor = hasErrors ? 'var(--accent-red)' : config.borderColor;

  return (
    <div
      className="rounded border-l-4 px-4 py-3 space-y-1.5"
      style={{ border: '1px solid var(--border)', borderLeftColor: leftBorderColor, borderLeftWidth: 4, background: 'var(--bg-card)' }}
    >
      <span className="text-xs font-bold" style={{ color: titleColor }}>{titleText}</span>
      {!hasErrors && passItems && passItems.length > 0 && (
        <ul className="space-y-0.5 pl-2">
          {passItems.map((item, i) => (
            <li key={i} className="text-xs flex items-start gap-1.5" style={{ color: 'var(--text-secondary)' }}>
              <span className="flex-shrink-0" style={{ color: 'var(--accent-green)' }}>├─</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      )}
      {hasErrors && (
        <ul className="space-y-1 pl-2">
          {issues.map((issue, i) => (
            <li key={i} className="text-xs flex items-start gap-1.5">
              <span className="flex-shrink-0 font-bold" style={{ color: severityColor(issue.severity) }}>
                {severityIcon(issue.severity)}
              </span>
              <div className="flex-1">
                <span style={{ color: 'var(--text-secondary)' }}>{issue.message}</span>
                {issue.location && (
                  <span className="ml-1.5 font-mono text-[10px]" style={{ color: 'var(--text-muted)' }}>
                    [{issue.location}]
                  </span>
                )}
                {issue.suggestion && (
                  <p className="mt-0.5 italic" style={{ color: 'var(--text-muted)' }}>{issue.suggestion}</p>
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
    <div className="rounded border-l-4 px-4 py-3 space-y-1.5" style={{ border: '1px solid var(--border)', borderLeftColor: 'var(--accent-orange)', borderLeftWidth: 4, background: 'var(--bg-card)' }}>
      <span className="text-xs font-bold" style={{ color: 'var(--accent-orange)' }}>
        ⚠️ Warnings ({issues.length})
      </span>
      <ul className="space-y-1 pl-2">
        {issues.map((issue, i) => (
          <li key={i} className="text-xs flex items-start gap-1.5">
            <span className="flex-shrink-0 font-bold" style={{ color: severityColor(issue.severity) }}>
              {severityIcon(issue.severity)}
            </span>
            <span className="flex-1" style={{ color: 'var(--text-secondary)' }}>{issue.message}</span>
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
    fixedIssuesInSession,
    undoAutoFix,
  } = useStrategyStore();

  // ValidationReport is produced by the full report endpoint; this panel
  // also accepts the simpler ValidationMessage[] from the store for
  // backward compatibility. When a full report arrives, it takes priority.
  const [report, setReport] = useState<ValidationReport | null>(null);
  const [lastValidatedAt, setLastValidatedAt] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isBacktesting, setIsBacktesting] = useState(false);
  const autoValidateEnabledRef = useRef(false);

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
      status.emit('Strategy saved', { variant: 'success' });
    } catch (err) {
      status.emit(`Save failed: ${err instanceof Error ? err.message : String(err)}`, { variant: 'error' });
    } finally {
      setIsSaving(false);
    }
  }, [saveStrategy]);

  const handleRunBacktest = useCallback(async () => {
    if (!currentStrategy) {
      status.emit('No strategy loaded', { variant: 'warning' });
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
      status.emit('Backtest started', { variant: 'info' });
    } catch (err) {
      status.emit(`Backtest failed: ${err instanceof Error ? err.message : String(err)}`, { variant: 'error' });
    } finally {
      setIsBacktesting(false);
    }
  }, [currentStrategy, runBacktest]);

  const handleGenerateCode = useCallback(() => {
    status.emit('Generate Code — coming in P2', { variant: 'info' });
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
    <div className="flex flex-col border-t" style={{ maxHeight: '22rem', background: 'var(--bg-panel)', borderColor: 'var(--border)' }}>
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-4 py-1.5 border-b flex-shrink-0" style={{ borderColor: 'var(--border)' }}>
        <span className="text-xs font-semibold flex-1" style={{ color: 'var(--text-secondary)' }}>Validation</span>

        {/* Last validated timestamp */}
        {lastValidatedAt && (
          <span className="text-[10px] font-mono" style={{ color: 'var(--text-faintest)' }}>Last: {lastValidatedAt}</span>
        )}

        {/* NautilusTrader compatibility badge */}
        {hasMessages || report ? (
          <span
            className="text-[10px] font-medium px-2 py-0.5 rounded-full border"
            style={nautilusCompatible
              ? { background: 'var(--accent-green-dark)', color: 'var(--accent-green)', borderColor: 'var(--accent-green-mid)' }
              : { background: 'var(--accent-red-deeper)', color: 'var(--accent-red)', borderColor: 'var(--accent-red-dark)' }}
          >
            {nautilusCompatible ? '✅ NT Compatible' : '❌ NT Incompatible'}
          </span>
        ) : null}

        {/* Summary counters */}
        {hasMessages && (
          <div className="flex items-center gap-2 text-xs">
            {errors > 0 && (
              <span className="font-medium" style={{ color: 'var(--accent-red)' }}>
                {errors} error{errors !== 1 ? 's' : ''}
              </span>
            )}
            {warnings > 0 && (
              <span className="font-medium" style={{ color: 'var(--accent-orange)' }}>
                {warnings} warning{warnings !== 1 ? 's' : ''}
              </span>
            )}
            {infos > 0 && <span style={{ color: 'var(--accent-blue)' }}>{infos} info</span>}
          </div>
        )}

        <InfoTooltip id="validate-now-btn">
          <button
            onClick={handleValidate}
            disabled={isValidating}
            className="px-2 py-0.5 rounded text-xs font-medium disabled:opacity-50 transition-colors"
            style={{ background: 'var(--btn-confirm-bg)', color: 'var(--btn-primary-text)' }}
            onMouseEnter={e => (e.currentTarget.style.background = 'var(--btn-confirm-bg-hover)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'var(--btn-confirm-bg)')}
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
              className="px-2 py-0.5 rounded text-xs transition-colors"
              style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-card)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
            >
              Clear
            </button>
          </InfoTooltip>
        )}
      </div>

      {/* Scrollable results area */}
      <div className="overflow-y-auto flex-1 min-h-0">
        {/* "Fixed in this session" section — rehydrated from
            validationHistory by setCurrentStrategy (BTCAAAAA-33700) and made
            visible per-row with Undo (BTCAAAAA-33738 Bug 3). Rendered before
            the live results so users see their applied fixes alongside any
            still-outstanding issues. */}
        {fixedIssuesInSession.length > 0 && (
          <div className="px-4 pt-3">
            <FixedIssuesList
              entries={fixedIssuesInSession}
              onUndo={(key) => { undoAutoFix(key).catch(console.error); }}
              compact
            />
          </div>
        )}

        {/* No results placeholder */}
        {!hasMessages && !report && !isValidating && fixedIssuesInSession.length === 0 && (
          <p className="px-4 py-2 text-xs" style={{ color: 'var(--text-faintest)' }}>
            No validation results — click Validate to run checks.
          </p>
        )}

        {isValidating && (
          <p className="px-4 py-2 text-xs animate-pulse" style={{ color: 'var(--text-secondary)' }}>Running validation…</p>
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
      <div className="flex items-center gap-2 px-4 py-2 border-t flex-shrink-0" style={{ borderColor: 'var(--border)', background: 'var(--bg-panel)' }}>
        <InfoTooltip id="save-strategy-btn">
          <button
            onClick={handleSave}
            disabled={!isSafeToSave || isSaving}
            className="px-3 py-1 rounded text-xs font-medium disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            style={{ background: 'var(--btn-confirm-bg)', color: 'var(--btn-primary-text)' }}
            onMouseEnter={e => { if (!e.currentTarget.disabled) e.currentTarget.style.background = 'var(--btn-confirm-bg-hover)'; }}
            onMouseLeave={e => (e.currentTarget.style.background = 'var(--btn-confirm-bg)')}
            title="Save the validated strategy to the database"
          >
            {isSaving ? 'Saving…' : '💾 Save Strategy'}
          </button>
        </InfoTooltip>

        <InfoTooltip id="run-backtest-btn">
          <button
            onClick={handleRunBacktest}
            disabled={!isSafeToBacktest || isBacktesting}
            className="px-3 py-1 rounded text-xs font-medium disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            style={{ background: 'var(--accent-blue)', color: 'var(--btn-primary-text)' }}
            onMouseEnter={e => { if (!e.currentTarget.disabled) e.currentTarget.style.background = 'var(--accent-blue-mid)'; }}
            onMouseLeave={e => (e.currentTarget.style.background = 'var(--accent-blue)')}
            title="Run a quick backtest on this strategy"
          >
            {isBacktesting ? 'Starting…' : '▶ Run Backtest'}
          </button>
        </InfoTooltip>

        <InfoTooltip id="generate-code-btn">
          <button
            onClick={handleGenerateCode}
            className="px-3 py-1 rounded text-xs font-medium transition-colors"
            style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
            onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-card)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
            title="Generate NautilusTrader Python strategy code (P2 feature)"
          >
            📝 Generate Code
          </button>
        </InfoTooltip>
      </div>
    </div>
  );
});
