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
    <div className={`bg-zinc-900 rounded-lg border border-zinc-700 overflow-hidden ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-zinc-700">
        <span className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">
          Decision Cycle Monitor
        </span>
        <span
          className={`text-xs px-2 py-0.5 rounded-full font-medium ${
            mode === 'per-phase'
              ? 'bg-purple-900/40 text-purple-300'
              : 'bg-zinc-700 text-zinc-400'
          }`}
        >
          {mode === 'per-phase' ? 'Per-Phase' : 'Aggregate'}
        </span>
      </div>

      {mode === 'aggregate' && (
        <div className="px-4 py-4 space-y-2">
          {aggregate ? (
            <>
              <div className="flex items-center justify-between">
                <span className="text-xs text-zinc-500">Bar Close UTC</span>
                <span className="text-sm font-mono text-zinc-200">{aggregate.barCloseUtc}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-zinc-500">Checkpoint Seq</span>
                <span className="text-sm font-mono text-zinc-200">{aggregate.checkpointSeq}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-zinc-500">Cycle ID</span>
                <span className="text-xs font-mono text-zinc-400 truncate max-w-[160px]">
                  {aggregate.cycleId}
                </span>
              </div>
              <div className="text-xs text-zinc-600 text-right">
                {aggregate.lastUpdated.toLocaleTimeString()}
              </div>
            </>
          ) : (
            <p className="text-zinc-500 text-xs text-center py-4">
              Waiting for /ws/cycle stream…
            </p>
          )}
          {phaseCount > 0 && phaseCount < MIN_EVENTS_TO_ACTIVATE && (
            <p className="text-xs text-zinc-600 text-center mt-2">
              Phase events: {phaseCount}/{MIN_EVENTS_TO_ACTIVATE} (activating per-phase view)
            </p>
          )}
        </div>
      )}

      {mode === 'per-phase' && (
        <div className="px-4 py-3">
          <PerPhaseTimingChart phases={phaseList} />
          <p className="text-xs text-zinc-600 text-center mt-1">
            Falls back to aggregate view after {FALLBACK_MS / 1000}s with no phase events
          </p>
        </div>
      )}
    </div>
  );
};

export default DecisionCycleMonitor;
