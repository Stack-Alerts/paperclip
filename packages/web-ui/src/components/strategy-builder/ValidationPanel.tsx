'use client';

import { useCallback } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { ValidationLevel, ValidationMessage } from '@/lib/strategy-builder/types';
import { InfoTooltip } from './InfoTooltip';

const LEVEL_STYLES: Record<ValidationLevel, { icon: string; classes: string; rowClasses: string }> = {
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
      <span className={`flex-shrink-0 font-bold mt-0.5 ${style.classes}`} aria-label={message.level}>
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
  const errors   = messages.filter((m) => m.level === ValidationLevel.ERROR).length;
  const warnings = messages.filter((m) => m.level === ValidationLevel.WARNING).length;
  const infos    = messages.filter((m) => m.level === ValidationLevel.INFO).length;
  return { errors, warnings, infos };
}

export function ValidationPanel() {
  const { validationMessages, isValidating, validateStrategy, clearValidation, selectBlock } =
    useStrategyStore();

  const handleMessageClick = useCallback(
    (msg: ValidationMessage) => {
      if (msg.blockIndex != null) selectBlock(msg.blockIndex);
    },
    [selectBlock],
  );

  const { errors, warnings, infos } = summarize(validationMessages);
  const hasMessages = validationMessages.length > 0;

  return (
    <div className="border-t border-zinc-800 bg-zinc-900 flex-shrink-0" style={{ maxHeight: '9rem' }}>
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-4 py-1.5 border-b border-zinc-800">
        <span className="text-xs font-semibold text-zinc-400 flex-1">Validation</span>

        {hasMessages && (
          <div className="flex items-center gap-2 text-xs">
            {errors > 0 && (
              <span className="text-red-400 font-medium">{errors} error{errors !== 1 ? 's' : ''}</span>
            )}
            {warnings > 0 && (
              <span className="text-amber-400 font-medium">{warnings} warning{warnings !== 1 ? 's' : ''}</span>
            )}
            {infos > 0 && (
              <span className="text-blue-400">{infos} info</span>
            )}
          </div>
        )}

        <InfoTooltip id="validate-now-btn">
          <button
            onClick={() => validateStrategy().catch(console.error)}
            disabled={isValidating}
            className="px-2 py-0.5 rounded bg-green-700 hover:bg-green-600 text-white text-xs font-medium disabled:opacity-50 transition-colors"
          >
            {isValidating ? 'Validating…' : 'Validate'}
          </button>
        </InfoTooltip>

        {hasMessages && (
          <InfoTooltip id="clear-validation-btn">
            <button
              onClick={clearValidation}
              className="px-2 py-0.5 rounded bg-zinc-700 hover:bg-zinc-600 text-zinc-300 text-xs transition-colors"
            >
              Clear
            </button>
          </InfoTooltip>
        )}
      </div>

      {/* Message list */}
      <div className="overflow-y-auto" style={{ maxHeight: '6rem' }}>
        {!hasMessages && !isValidating && (
          <p className="px-4 py-2 text-xs text-zinc-600">No validation results — click Validate to run checks.</p>
        )}
        {isValidating && (
          <p className="px-4 py-2 text-xs text-zinc-400 animate-pulse">Running validation…</p>
        )}
        {validationMessages.map((msg) => (
          <MessageRow key={msg.id} message={msg} onClick={handleMessageClick} />
        ))}
      </div>
    </div>
  );
}
