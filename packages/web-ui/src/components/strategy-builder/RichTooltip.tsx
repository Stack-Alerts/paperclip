'use client';

import React, {
  cloneElement, isValidElement, ReactElement,
  useCallback, useEffect, useRef, useState,
} from 'react';
import { createPortal } from 'react-dom';
import { useTooltipSettings } from './TooltipSettingsContext';

export interface TooltipSection {
  header?: string;
  items: string[];
}

export interface TooltipContent {
  title: string;
  body?: string;
  sections?: TooltipSection[];
}

// ─── Popup ────────────────────────────────────────────────────────────────────
function TooltipPopup({ content, triggerRect }: { content: TooltipContent; triggerRect: DOMRect }) {
  const ref = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ left: number; top: number; opacity: number }>({ left: 0, top: 0, opacity: 0 });

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const { width: tw, height: th } = el.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const cx = triggerRect.left + triggerRect.width / 2;
    const left = Math.max(8, Math.min(cx - tw / 2, vw - tw - 8));
    const showBelow = triggerRect.bottom + th + 12 <= vh || triggerRect.top < th + 12;
    const top = showBelow ? triggerRect.bottom + 8 : triggerRect.top - th - 8;
    setPos({ left, top, opacity: 1 });
  }, [triggerRect]);

  const hasSections = content.sections && content.sections.length > 0;

  return (
    <div
      ref={ref}
      style={{
        position: 'fixed',
        zIndex: 9999,
        pointerEvents: 'none',
        maxWidth: 420,
        minWidth: 240,
        left: pos.left,
        top: pos.top,
        opacity: pos.opacity,
        transition: 'opacity 0.08s ease',
        background: 'var(--tooltip-bg)',
        border: '1px solid var(--tooltip-border)',
        color: 'var(--tooltip-text)',
        borderRadius: 6,
        padding: '10px 14px',
        fontSize: 13,
        lineHeight: 1.6,
        boxShadow: '0 8px 32px rgba(0,0,0,0.65), 0 2px 8px rgba(0,0,0,0.4)',
        fontFamily: 'inherit',
      }}
    >
      {/* Title */}
      <div style={{
        color: 'var(--tooltip-title)',
        fontWeight: 700,
        fontSize: 14,
        marginBottom: content.body || hasSections ? 5 : 0,
        letterSpacing: 0.1,
      }}>
        {content.title}
      </div>

      {/* Body */}
      {content.body && (
        <div style={{ color: 'var(--tooltip-body)', marginBottom: hasSections ? 7 : 0 }}>
          {content.body}
        </div>
      )}

      {/* Sections */}
      {content.sections?.map((sec, i) => (
        <div key={i} style={{ marginTop: i === 0 ? 0 : 7 }}>
          {sec.header && (
            <div style={{ color: 'var(--tooltip-header)', fontWeight: 600, marginBottom: 3 }}>
              {sec.header}
            </div>
          )}
          {sec.items.map((item, j) => (
            <div
              key={j}
              style={{ color: 'var(--tooltip-body)', display: 'flex', gap: 5, alignItems: 'flex-start', marginBottom: 2 }}
            >
              <span style={{ color: 'var(--tooltip-bullet)', flexShrink: 0, marginTop: 1 }}>•</span>
              <span>{item}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

// ─── RichTooltip ──────────────────────────────────────────────────────────────
interface RichTooltipProps {
  content: TooltipContent;
  children: ReactElement;
  delay?: number;
}

export function RichTooltip({ content, children }: RichTooltipProps) {
  const { settings } = useTooltipSettings();
  const [triggerRect, setTriggerRect] = useState<DOMRect | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [mounted, setMounted] = useState(false);

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { setMounted(true); }, []);
  useEffect(() => () => { if (timerRef.current) clearTimeout(timerRef.current); }, []);

  // Dismiss any active or pending tooltip immediately when user disables tooltips.
  useEffect(() => {
    if (!settings.enabled) {
      if (timerRef.current) clearTimeout(timerRef.current);
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setTriggerRect(null);
    }
  }, [settings.enabled]);

  const show = useCallback((e: React.MouseEvent<HTMLElement>) => {
    if (!settings.enabled) return;
    const rect = e.currentTarget.getBoundingClientRect();
    timerRef.current = setTimeout(() => setTriggerRect(rect), settings.delayMs);
  }, [settings.enabled, settings.delayMs]);

  const hide = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setTriggerRect(null);
  }, []);

  if (!isValidElement(children)) return <>{children}</>;

  // eslint-disable-next-line react-hooks/refs
  const child = cloneElement(children as ReactElement<React.HTMLAttributes<HTMLElement>>, {
    onMouseEnter: (e: React.MouseEvent<HTMLElement>) => {
      (children.props as React.HTMLAttributes<HTMLElement>).onMouseEnter?.(e);
      show(e);
    },
    onMouseLeave: (e: React.MouseEvent<HTMLElement>) => {
      (children.props as React.HTMLAttributes<HTMLElement>).onMouseLeave?.(e);
      hide();
    },
  });

  return (
    <>
      {child}
      {mounted && triggerRect && createPortal(
        <TooltipPopup content={content} triggerRect={triggerRect} />,
        document.body,
      )}
    </>
  );
}
