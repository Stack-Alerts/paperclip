'use client';
import { useState, useRef, useCallback, useEffect } from 'react';
import { GripVertical } from 'lucide-react';

// ── Split layout (AC1) ───────────────────────────────────────────────────

const SPLIT_MIN = 30;
const SPLIT_MAX = 65;
const SPLIT_DEFAULT = 40;
const SPLIT_STORAGE_KEY = 'ai_recs_panel_split';
const LEFT_PANEL_MIN_PX = 360;

export function SplitPanel({
  left,
  right,
}: {
  left: React.ReactNode;
  right: React.ReactNode;
}) {
  const [splitPercent, setSplitPercent] = useState<number>(() => {
    if (typeof window === 'undefined') return SPLIT_DEFAULT;
    try {
      const stored = window.localStorage.getItem(SPLIT_STORAGE_KEY);
      if (stored) {
        const parsed = Number.parseFloat(stored);
        if (Number.isFinite(parsed) && parsed >= SPLIT_MIN && parsed <= SPLIT_MAX) return parsed;
      }
    } catch { /* best effort */ }
    return SPLIT_DEFAULT;
  });
  const containerRef = useRef<HTMLDivElement | null>(null);
  const isDraggingRef = useRef(false);
  const hasMountedRef = useRef(false);

  // Persist split on change (skip the initial mount so we don't echo
  // the value we just read from localStorage back immediately).
  useEffect(() => {
    if (!hasMountedRef.current) {
      hasMountedRef.current = true;
      return;
    }
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(SPLIT_STORAGE_KEY, String(splitPercent));
    } catch {
      // best effort
    }
  }, [splitPercent]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isDraggingRef.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, []);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!isDraggingRef.current) return;
      const container = containerRef.current;
      if (!container) return;
      const rect = container.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const minPx = LEFT_PANEL_MIN_PX;
      const minPctFromPx = (minPx / rect.width) * 100;
      const effectiveMin = Math.max(SPLIT_MIN, minPctFromPx);
      const clamped = Math.min(
        Math.max((x / rect.width) * 100, effectiveMin),
        SPLIT_MAX,
      );
      setSplitPercent(clamped);
    };
    const onUp = () => {
      if (!isDraggingRef.current) return;
      isDraggingRef.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      data-testid="ai-recs-split-panel"
      className="flex w-full"
      style={{ minHeight: 360 }}
    >
      <div
        className="overflow-auto pr-2"
        style={{
          flexBasis: `${splitPercent}%`,
          flexGrow: 0,
          flexShrink: 0,
          minWidth: LEFT_PANEL_MIN_PX,
        }}
      >
        {left}
      </div>
      <div
        role="separator"
        aria-orientation="vertical"
        aria-valuenow={Math.round(splitPercent)}
        aria-valuemin={SPLIT_MIN}
        aria-valuemax={SPLIT_MAX}
        aria-label="Resize AI recommendations split panel"
        onMouseDown={handleMouseDown}
        data-testid="ai-recs-split-handle"
        className="w-2 cursor-col-resize flex-shrink-0 flex items-center justify-center"
        style={{
          background: 'var(--bg-elevated)',
          borderLeft: '1px solid var(--border)',
          borderRight: '1px solid var(--border)',
        }}
        title="Drag to resize"
      >
        <GripVertical size={12} style={{ color: 'var(--text-faint)' }} />
      </div>
      <div
        className="overflow-auto pl-2"
        style={{ flexBasis: `${100 - splitPercent}%`, flexGrow: 1, flexShrink: 1 }}
      >
        {right}
      </div>
    </div>
  );
}
