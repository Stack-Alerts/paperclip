'use client';
import { useState, useCallback } from 'react';
import { B1DecisionCycleMonitor } from './B1DecisionCycleMonitor';
import { B2PositionPanel } from './B2PositionPanel';
import { B3CapitalPanel } from './B3CapitalPanel';
import { B4SignalPanel } from './B4SignalPanel';
import { B5AlertBanner } from './B5AlertBanner';
import { B6DecisionLog } from './B6DecisionLog';
import { emergencyHalt } from '@/lib/strategy-builder/api';

const WS_BASE = process.env.NEXT_PUBLIC_BRIDGE_WS_URL ?? 'ws://localhost:8765';

export function ITMDashboard() {
  const [halting, setHalting] = useState(false);
  const [haltResult, setHaltResult] = useState<string | null>(null);

  const handleEmergencyHalt = useCallback(async () => {
    if (!confirm('EMERGENCY HALT: Pause ALL active strategies immediately. Continue?')) return;
    setHalting(true);
    setHaltResult(null);
    try {
      const result = await emergencyHalt();
      setHaltResult(`Halted ${result.halted} strategy${result.halted !== 1 ? 'ies' : 'y'}`);
    } catch {
      setHaltResult('Halt failed — check backend');
    } finally {
      setHalting(false);
    }
  }, []);

  return (
    <div className="min-h-screen font-sans" style={{ background: 'var(--app-bg)', color: 'var(--text-primary)' }}>
      <header className="px-6 py-4 flex items-center justify-between" style={{ borderBottom: '1px solid var(--border)' }}>
        <div>
          <h1 className="text-lg font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
            BTC Trade Engine — ITM Live Dashboard
          </h1>
          <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
            Real-time institutional monitoring · panels B1–B6
          </p>
        </div>
        <div className="flex items-center gap-4">
          {haltResult && (
            <span className="text-xs text-amber-400 font-mono">{haltResult}</span>
          )}
          <button
            onClick={handleEmergencyHalt}
            disabled={halting}
            className="px-4 py-2 rounded bg-red-700 hover:bg-red-600 text-white text-xs font-bold uppercase tracking-wider disabled:opacity-50 transition-colors border border-red-500"
          >
            {halting ? 'Halting…' : '⛔ Emergency Halt'}
          </button>
          <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>{WS_BASE}</span>
        </div>
      </header>

      {/* B5 Alert Banner — spans full width at top */}
      <div className="px-6 pt-4">
        <B5AlertBanner wsBaseUrl={WS_BASE} />
      </div>

      {/* Main grid: B1–B4 */}
      <div className="grid grid-cols-1 gap-4 px-6 pt-4 lg:grid-cols-2 xl:grid-cols-4">
        <B1DecisionCycleMonitor wsBaseUrl={WS_BASE} />
        <B3CapitalPanel wsBaseUrl={WS_BASE} />
        <B4SignalPanel wsBaseUrl={WS_BASE} />
        <B6DecisionLog wsBaseUrl={WS_BASE} />
      </div>

      {/* B2 Position Panel — wider row */}
      <div className="px-6 pt-4 pb-8">
        <B2PositionPanel wsBaseUrl={WS_BASE} />
      </div>
    </div>
  );
}
