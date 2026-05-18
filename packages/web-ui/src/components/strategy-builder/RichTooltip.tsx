'use client';

import React, {
  cloneElement, isValidElement, ReactElement,
  useCallback, useEffect, useRef, useState,
} from 'react';
import { createPortal } from 'react-dom';

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
        maxWidth: 380,
        minWidth: 220,
        left: pos.left,
        top: pos.top,
        opacity: pos.opacity,
        transition: 'opacity 0.08s ease',
        background: '#0D1117',
        border: '1px solid #2D3748',
        color: '#E2E8F0',
        borderRadius: 6,
        padding: '10px 13px',
        fontSize: 11.5,
        lineHeight: 1.55,
        boxShadow: '0 8px 32px rgba(0,0,0,0.65), 0 2px 8px rgba(0,0,0,0.4)',
        fontFamily: 'inherit',
      }}
    >
      {/* Title */}
      <div style={{
        color: '#F0F4F8',
        fontWeight: 700,
        fontSize: 12.5,
        marginBottom: content.body || hasSections ? 5 : 0,
        letterSpacing: 0.1,
      }}>
        {content.title}
      </div>

      {/* Body */}
      {content.body && (
        <div style={{ color: '#CBD5E0', marginBottom: hasSections ? 7 : 0 }}>
          {content.body}
        </div>
      )}

      {/* Sections */}
      {content.sections?.map((sec, i) => (
        <div key={i} style={{ marginTop: i === 0 ? 0 : 7 }}>
          {sec.header && (
            <div style={{ color: '#A0AEC0', fontWeight: 600, marginBottom: 3 }}>
              {sec.header}
            </div>
          )}
          {sec.items.map((item, j) => (
            <div
              key={j}
              style={{ color: '#CBD5E0', display: 'flex', gap: 5, alignItems: 'flex-start', marginBottom: 2 }}
            >
              <span style={{ color: '#718096', flexShrink: 0, marginTop: 1 }}>•</span>
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

export function RichTooltip({ content, children, delay = 350 }: RichTooltipProps) {
  const [triggerRect, setTriggerRect] = useState<DOMRect | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => { setMounted(true); }, []);
  useEffect(() => () => { if (timerRef.current) clearTimeout(timerRef.current); }, []);

  const show = useCallback((e: React.MouseEvent<HTMLElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    timerRef.current = setTimeout(() => setTriggerRect(rect), delay);
  }, [delay]);

  const hide = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setTriggerRect(null);
  }, []);

  if (!isValidElement(children)) return <>{children}</>;

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
