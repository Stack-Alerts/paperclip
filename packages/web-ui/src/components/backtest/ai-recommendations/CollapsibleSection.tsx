'use client';
import { useState, useCallback, useId } from 'react';
import { ChevronDown, ChevronRight, Copy, Check } from 'lucide-react';

export function CollapsibleSection({
  title,
  description,
  children,
  defaultOpen = true,
  copyText,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  copyText?: string;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const [copied, setCopied] = useState(false);
  const contentId = useId();

  const handleCopy = useCallback(
    async (e: React.MouseEvent) => {
      e.stopPropagation();
      if (!copyText) return;
      try {
        if (
          typeof navigator !== 'undefined' &&
          navigator.clipboard &&
          typeof navigator.clipboard.writeText === 'function'
        ) {
          await navigator.clipboard.writeText(copyText);
        } else if (typeof document !== 'undefined') {
          const ta = document.createElement('textarea');
          ta.value = copyText;
          ta.style.position = 'fixed';
          ta.style.opacity = '0';
          document.body.appendChild(ta);
          ta.select();
          document.execCommand('copy');
          document.body.removeChild(ta);
        }
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1500);
      } catch {
        // best-effort copy
      }
    },
    [copyText],
  );

  return (
    <div
      className="rounded mb-2"
      style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
    >
      <div className="w-full flex items-center gap-2 px-3 py-2">
        <button
          className="flex items-center gap-2 text-left flex-1"
          onClick={() => setOpen((v) => !v)}
          type="button"
          aria-expanded={open}
          aria-controls={contentId}
        >
          {open ? (
            <ChevronDown size={14} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
          ) : (
            <ChevronRight size={14} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
          )}
          <span className="text-xs font-semibold uppercase tracking-wide flex-1" style={{ color: 'var(--text-secondary)' }}>
            {title}
          </span>
          <span className="text-xs" style={{ color: 'var(--text-faint)' }}>
            {description}
          </span>
        </button>
        {copyText !== undefined && (
          <button
            type="button"
            aria-label={copied ? `Copied ${title}` : `Copy ${title}`}
            data-testid={`collapsible-copy-${title.replace(/\s+/g, '-').toLowerCase()}`}
            onClick={handleCopy}
            className="ml-2 px-1.5 py-0.5 rounded flex items-center gap-1 text-[10px] font-medium shrink-0"
            style={{
              background: copied ? 'var(--accent-green-soft)' : 'var(--bg-elevated)',
              color: copied ? 'var(--accent-green-on)' : 'var(--text-muted)',
              border: `1px solid ${copied ? 'var(--accent-green-on)' : 'var(--border)'}`,
              cursor: 'pointer',
            }}
          >
            {copied ? (
              <Check size={10} aria-hidden="true" />
            ) : (
              <Copy size={10} aria-hidden="true" />
            )}
            {copied ? 'Copied' : 'Copy'}
          </button>
        )}
      </div>
      {open && (
        <div id={contentId} className="px-3 pb-3">
          {children}
        </div>
      )}
    </div>
  );
}

export function PreviewText({ text }: { text: string }) {
  return (
    <pre
      className="text-xs rounded p-2 overflow-auto max-h-48 whitespace-pre-wrap break-words"
      style={{
        background: 'var(--bg-elevated)',
        color: 'var(--text-muted)',
        border: '1px solid var(--border)',
        fontFamily: 'var(--font-mono, monospace)',
      }}
    >
      {text}
    </pre>
  );
}
