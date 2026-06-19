'use client';

import type { BacktestConfigFull, BacktestResult } from '@/lib/strategy-builder/types';

const PRESETS_KEY = 'btcte:config_presets';

export interface ConfigPreset {
  id: string;
  name: string;
  group: string;
  tags: string[];
  fullConfig: BacktestConfigFull;
  metrics: {
    returnPercentage: number;
    winRate: number;
    maxDrawdown: number;
    sharpeRatio: number;
    profitFactor: number;
    totalTrades: number;
    finalCapital: number;
    initialCapital: number;
  };
  savedAt: string;
  strategyName?: string;
}

function metricsFromResult(result: BacktestResult): ConfigPreset['metrics'] {
  return {
    returnPercentage: result.returnPercentage,
    winRate: result.winRate,
    maxDrawdown: result.maxDrawdown,
    sharpeRatio: result.sharpeRatio,
    profitFactor: result.profitFactor,
    totalTrades: result.totalTrades,
    finalCapital: result.finalCapital,
    initialCapital: result.initialCapital,
  };
}

function load(): ConfigPreset[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(PRESETS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? (parsed as ConfigPreset[]) : [];
  } catch {
    return [];
  }
}

function persist(presets: ConfigPreset[]): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(PRESETS_KEY, JSON.stringify(presets));
  } catch {
    // localStorage full or disabled — silently skip persistence
  }
}

export function savePreset(
  name: string,
  group: string,
  tags: string[],
  fullConfig: BacktestConfigFull,
  result: BacktestResult,
  strategyName?: string,
): ConfigPreset {
  const preset: ConfigPreset = {
    id: `preset-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    name: name.trim() || 'Untitled preset',
    group: group.trim(),
    tags: tags.map(t => t.trim()).filter(Boolean),
    fullConfig,
    metrics: metricsFromResult(result),
    savedAt: new Date().toISOString(),
    strategyName,
  };
  persist([preset, ...load()]);
  return preset;
}

export function loadPresets(): ConfigPreset[] {
  return load().sort((a, b) => new Date(b.savedAt).getTime() - new Date(a.savedAt).getTime());
}

export function updatePreset(id: string, patch: { name?: string; group?: string; tags?: string[] }): void {
  persist(load().map(p =>
    p.id === id
      ? {
          ...p,
          name: patch.name !== undefined ? (patch.name.trim() || 'Untitled preset') : p.name,
          group: patch.group !== undefined ? patch.group.trim() : p.group,
          tags: patch.tags !== undefined ? patch.tags.map(t => t.trim()).filter(Boolean) : p.tags,
        }
      : p
  ));
}

export function deletePreset(id: string): void {
  persist(load().filter(p => p.id !== id));
}

export function listGroups(presets: ConfigPreset[]): string[] {
  const seen = new Set<string>();
  const groups: string[] = [];
  for (const p of presets) {
    if (p.group && !seen.has(p.group)) {
      seen.add(p.group);
      groups.push(p.group);
    }
  }
  return groups.sort();
}

export function listTags(presets: ConfigPreset[]): string[] {
  const seen = new Set<string>();
  const tags: string[] = [];
  for (const p of presets) {
    for (const t of p.tags) {
      if (!seen.has(t)) {
        seen.add(t);
        tags.push(t);
      }
    }
  }
  return tags.sort();
}
