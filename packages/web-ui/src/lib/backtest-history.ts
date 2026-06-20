'use client';

import type { BacktestRunRecord } from '@/lib/strategy-builder/types';

const HISTORY_KEY = 'btcte:backtest_run_history';
// Raised from 20 to 50 to accommodate config-discovery runs (25+ per strategy)
const MAX_RUNS_PER_STRATEGY = 50;

function load(): BacktestRunRecord[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? (parsed as BacktestRunRecord[]) : [];
  } catch {
    return [];
  }
}

function save(records: BacktestRunRecord[]): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(records));
  } catch {
    // localStorage full or disabled — silently skip persistence
  }
}

export function addRunRecord(record: BacktestRunRecord): void {
  const all = load();
  const without = all.filter(r => r.runId !== record.runId);
  const forStrategy = without.filter(r => r.strategyId === record.strategyId);
  const others = without.filter(r => r.strategyId !== record.strategyId);
  const capped = [record, ...forStrategy].slice(0, MAX_RUNS_PER_STRATEGY);
  save([...capped, ...others]);
}

export function loadAllRunRecords(opts?: { includeArchived?: boolean }): BacktestRunRecord[] {
  const all = load().sort((a, b) => new Date(b.savedAt).getTime() - new Date(a.savedAt).getTime());
  if (opts?.includeArchived) return all;
  return all.filter(r => !r.archived);
}

export function loadRunRecordsForStrategy(strategyId: string): BacktestRunRecord[] {
  return load()
    .filter(r => r.strategyId === strategyId && !r.archived)
    .sort((a, b) => new Date(b.savedAt).getTime() - new Date(a.savedAt).getTime());
}

export function deleteRunRecord(runId: string): void {
  save(load().filter(r => r.runId !== runId));
}

export function deleteRunRecords(runIds: string[]): void {
  const drop = new Set(runIds);
  save(load().filter(r => !drop.has(r.runId)));
}

export function clearAllRunRecords(): void {
  save([]);
}

export function archiveRunRecord(runId: string): void {
  save(load().map(r => r.runId === runId ? { ...r, archived: true } : r));
}

export function unarchiveRunRecord(runId: string): void {
  save(load().map(r => r.runId === runId ? { ...r, archived: false } : r));
}

export function archiveRunRecords(runIds: string[]): void {
  const ids = new Set(runIds);
  save(load().map(r => ids.has(r.runId) ? { ...r, archived: true } : r));
}
