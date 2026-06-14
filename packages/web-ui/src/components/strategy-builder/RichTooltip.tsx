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
// `anchorRect`, when supplied, pins the balloon to one consistent place (just
// outside the right edge of the anchor element, vertically centred on it) and
// draws an arrow whose vertical position tracks the hovered trigger row. Without
// it, the popup follows the trigger directly (original behaviour). BTCAAAAA-36309.
const ARROW = 7; // half-height of the balloon arrow, px

function TooltipPopup({
  content,
  triggerRect,
  anchorRect,
}: {
  content: TooltipContent;
  triggerRect: DOMRect;
  anchorRect?: DOMRect | null;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{
    left: number;
    top: number;
    opacity: number;
    arrow: { top: number; side: 'left' | 'right' } | null;
  }>({ left: 0, top: 0, opacity: 0, arrow: null });

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const { width: tw, height: th } = el.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    if (anchorRect) {
      // Pinned balloon: prefer the right of the anchor, fall back to its left.
      const fitsRight = anchorRect.right + tw + 16 <= vw;
      const side: 'left' | 'right' = fitsRight ? 'left' : 'right';
      const left = fitsRight
        ? anchorRect.right + 12
        : Math.max(8, anchorRect.left - tw - 12);
      const center = anchorRect.top + anchorRect.height / 2;
      const top = Math.max(8, Math.min(center - th / 2, vh - th - 8));
      const triggerCenter = triggerRect.top + triggerRect.height / 2;
      const arrowTop = Math.max(ARROW + 4, Math.min(triggerCenter - top, th - ARROW - 4));
      setPos({ left, top, opacity: 1, arrow: { top: arrowTop, side } });
      return;
    }

    const cx = triggerRect.left + triggerRect.width / 2;
    const left = Math.max(8, Math.min(cx - tw / 2, vw - tw - 8));
    const showBelow = triggerRect.bottom + th + 12 <= vh || triggerRect.top < th + 12;
    const top = showBelow ? triggerRect.bottom + 8 : triggerRect.top - th - 8;
    setPos({ left, top, opacity: 1, arrow: null });
  }, [triggerRect, anchorRect]);

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
      {/* Balloon arrow — a rotated square that pokes out of the edge nearest the
          hovered row, with the two outward faces carrying the tooltip border. */}
      {pos.arrow && (
        <div
          style={{
            position: 'absolute',
            top: pos.arrow.top - 6,
            width: 12,
            height: 12,
            background: 'var(--tooltip-bg)',
            transform: 'rotate(45deg)',
            ...(pos.arrow.side === 'left'
              ? { left: -6, borderLeft: '1px solid var(--tooltip-border)', borderBottom: '1px solid var(--tooltip-border)' }
              : { right: -6, borderRight: '1px solid var(--tooltip-border)', borderTop: '1px solid var(--tooltip-border)' }),
          }}
        />
      )}

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
  // BTCAAAAA-36309: when provided, the balloon is pinned to a consistent spot
  // beside this element and an arrow tracks the hovered trigger row.
  anchorTo?: React.RefObject<HTMLElement | null>;
}

export function RichTooltip({ content, children, anchorTo }: RichTooltipProps) {
  const { settings } = useTooltipSettings();
  const [triggerRect, setTriggerRect] = useState<DOMRect | null>(null);
  const [anchorRect, setAnchorRect] = useState<DOMRect | null>(null);
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
    const anchor = anchorTo?.current?.getBoundingClientRect() ?? null;
    timerRef.current = setTimeout(() => {
      setTriggerRect(rect);
      setAnchorRect(anchor);
    }, settings.delayMs);
  }, [settings.enabled, settings.delayMs, anchorTo]);

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
        <TooltipPopup content={content} triggerRect={triggerRect} anchorRect={anchorRect} />,
        document.body,
      )}
    </>
  );
}
