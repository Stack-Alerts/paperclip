'use client';

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { PerPhaseTimingChart, type PhaseData } from './PerPhaseTimingChart';

export interface BarCloseEvent {
  cycleId: string;
  barCloseUtc: string;
  checkpointSeq: number;
}

export interface PhaseStartedEvent {
  eventType: 'PhaseStarted';
  phaseName: string;
  phaseIndex: number;
  cycleId: string;
  occurredAt: string;
}

export interface PhaseCompletedEvent {
  eventType: 'PhaseCompleted';
  phaseName: string;
  phaseIndex: number;
  cycleId: string;
  occurredAt: string;
  durationMs: number;
  outcome: string;
}

export type CycleWsMessage = BarCloseEvent | PhaseStartedEvent | PhaseCompletedEvent;

export interface DecisionCycleMonitorProps {
  className?: string;
}

const MIN_EVENTS_TO_ACTIVATE = 3;
const FALLBACK_MS = 30_000;

type DisplayMode = 'aggregate' | 'per-phase';

interface AggregateState {
  cycleId: string;
  barCloseUtc: string;
  checkpointSeq: number;
  lastUpdated: Date;
}

export const DecisionCycleMonitor: React.FC<DecisionCycleMonitorProps> = ({ className = '' }) => {
  const [mode, setMode] = useState<DisplayMode>('aggregate');
  const [aggregate, setAggregate] = useState<AggregateState | null>(null);
  const [phases, setPhases] = useState<Map<string, PhaseData>>(new Map());
  const [phaseCount, setPhaseCount] = useState(0);
  const fallbackTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const resetFallbackTimer = useCallback(() => {
    if (fallbackTimer.current) clearTimeout(fallbackTimer.current);
    fallbackTimer.current = setTimeout(() => {
      setMode('aggregate');
      setPhases(new Map());
      setPhaseCount(0);
    }, FALLBACK_MS);
  }, []);

  useEffect(() => {
    return () => {
      if (fallbackTimer.current) clearTimeout(fallbackTimer.current);
    };
  }, []);

  const onWsMessage = useCallback(
    (data: CycleWsMessage) => {
      if ('eventType' in data) {
        if (data.eventType === 'PhaseStarted') {
          const ev = data as PhaseStartedEvent;
          setPhases((prev) => {
            const next = new Map(prev);
            next.set(ev.phaseName, {
              name: ev.phaseName,
              startUs: 0,
              durationUs: 0,
            });
            return next;
          });
        } else if (data.eventType === 'PhaseCompleted') {
          const ev = data as PhaseCompletedEvent;
          setPhases((prev) => {
            const next = new Map(prev);
            const existing = next.get(ev.phaseName);
            next.set(ev.phaseName, {
              name: ev.phaseName,
              startUs: existing?.startUs ?? 0,
              durationUs: ev.durationMs * 1000,
              outcome: ev.outcome,
            });
            return next;
          });
          setPhaseCount((c) => {
            const n = c + 1;
            if (n >= MIN_EVENTS_TO_ACTIVATE) setMode('per-phase');
            return n;
          });
          resetFallbackTimer();
        }
      } else {
        const ev = data as BarCloseEvent;
        setAggregate({
          cycleId: ev.cycleId,
          barCloseUtc: ev.barCloseUtc,
          checkpointSeq: ev.checkpointSeq,
          lastUpdated: new Date(),
        });
      }
    },
    [resetFallbackTimer]
  );

  // Expose onWsMessage for parent components via ref pattern
  void onWsMessage;

  const phaseList: PhaseData[] = Array.from(phases.values()).filter((p) => p.durationUs > 0);

  return (
    <div className={`rounded-lg overflow-hidden border ${className}`} style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b" style={{ borderColor: 'var(--border)' }}>
        <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-primary)' }}>
          Decision Cycle Monitor
        </span>
        <span
          className="text-xs px-2 py-0.5 rounded-full font-medium"
          style={
            mode === 'per-phase'
              ? { background: 'color-mix(in srgb, #a855f7 20%, transparent)', color: '#c084fc' }
              : { background: 'var(--bg-hover)', color: 'var(--text-secondary)' }
          }
        >
          {mode === 'per-phase' ? 'Per-Phase' : 'Aggregate'}
        </span>
      </div>

      {mode === 'aggregate' && (
        <div className="px-4 py-4 space-y-2">
          {aggregate ? (
            <>
              <div className="flex items-center justify-between">
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Bar Close UTC</span>
                <span className="text-sm font-mono" style={{ color: 'var(--text-primary)' }}>{aggregate.barCloseUtc}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Checkpoint Seq</span>
                <span className="text-sm font-mono" style={{ color: 'var(--text-primary)' }}>{aggregate.checkpointSeq}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Cycle ID</span>
                <span className="text-xs font-mono truncate max-w-[160px]" style={{ color: 'var(--text-secondary)' }}>
                  {aggregate.cycleId}
                </span>
              </div>
              <div className="text-xs text-right" style={{ color: 'var(--text-faintest)' }}>
                {aggregate.lastUpdated.toLocaleTimeString()}
              </div>
            </>
          ) : (
            <p className="text-xs text-center py-4" style={{ color: 'var(--text-muted)' }}>
              Waiting for /ws/cycle stream…
            </p>
          )}
          {phaseCount > 0 && phaseCount < MIN_EVENTS_TO_ACTIVATE && (
            <p className="text-xs text-center mt-2" style={{ color: 'var(--text-faintest)' }}>
              Phase events: {phaseCount}/{MIN_EVENTS_TO_ACTIVATE} (activating per-phase view)
            </p>
          )}
        </div>
      )}

      {mode === 'per-phase' && (
        <div className="px-4 py-3">
          <PerPhaseTimingChart phases={phaseList} />
          <p className="text-xs text-center mt-1" style={{ color: 'var(--text-faintest)' }}>
            Falls back to aggregate view after {FALLBACK_MS / 1000}s with no phase events
          </p>
        </div>
      )}
    </div>
  );
};

export default DecisionCycleMonitor;
