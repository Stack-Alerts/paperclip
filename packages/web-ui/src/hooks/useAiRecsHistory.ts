'use client';

import { useCallback, useEffect, useState } from 'react';
import { FeedbackValue, setFeedback as persistFeedback } from '@/components/backtest/ai-recommendations/feedbackCapture';

export type AiRecsHistoryStatus = 'new' | 'applied' | 'dismissed';

export interface AiRecsHistoryEntry {
  id: string;
  createdAt: string;
  prompt: string;
  summary: string;
  diagnosis: string;
  recommendations: string;
  raw: string;
  strategyName?: string;
  status: AiRecsHistoryStatus;
  notes: string;
}

const STORAGE_KEY = 'btc-paperclip:ai-recs:v1';
const MAX_ENTRIES = 100;

const VALID_STATUSES: AiRecsHistoryStatus[] = ['new', 'applied', 'dismissed'];

function isStatus(value: unknown): value is AiRecsHistoryStatus {
  return typeof value === 'string' && (VALID_STATUSES as string[]).includes(value);
}

function coerceEntry(raw: unknown): AiRecsHistoryEntry | null {
  if (!raw || typeof raw !== 'object') return null;
  const e = raw as Record<string, unknown>;
  if (typeof e.id !== 'string' || typeof e.createdAt !== 'string') return null;
  if (typeof e.prompt !== 'string') return null;
  if (typeof e.summary !== 'string') return null;
  if (typeof e.diagnosis !== 'string') return null;
  if (typeof e.recommendations !== 'string') return null;
  if (typeof e.raw !== 'string') return null;
  if (typeof e.notes !== 'string') return null;
  if (!isStatus(e.status)) return null;
  return {
    id: e.id,
    createdAt: e.createdAt,
    prompt: e.prompt,
    summary: e.summary,
    diagnosis: e.diagnosis,
    recommendations: e.recommendations,
    raw: e.raw,
    status: e.status,
    notes: e.notes,
    ...(typeof e.strategyName === 'string' ? { strategyName: e.strategyName } : {}),
  };
}

function loadStored(): AiRecsHistoryEntry[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map(coerceEntry)
      .filter((e): e is AiRecsHistoryEntry => e !== null)
      .slice(0, MAX_ENTRIES);
  } catch {
    return [];
  }
}

function persist(entries: AiRecsHistoryEntry[]): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  } catch {
    // Quota exceeded or storage disabled — best effort. In-memory state
    // remains authoritative for the current session.
  }
}

function makeId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `ai-recs-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export function summarize(text: string, maxLen = 280): string {
  const normalized = text.replace(/\s+/g, ' ').trim();
  if (normalized.length <= maxLen) return normalized;
  return `${normalized.slice(0, maxLen - 1).trimEnd()}…`;
}

export interface UseAiRecsHistoryResult {
  entries: AiRecsHistoryEntry[];
  hydrated: boolean;
  add: (input: {
    prompt: string;
    diagnosis: string;
    recommendations: string;
    raw: string;
    strategyName?: string;
  }) => AiRecsHistoryEntry;
  updateStatus: (id: string, status: AiRecsHistoryStatus) => void;
  updateNotes: (id: string, notes: string) => void;
  deleteEntry: (id: string) => void;
  clear: () => void;
  /**
   * Stream 7 (BTCAAAAA-38468) write path. Persists per-card thumbs-up/down
   * feedback for the given analysis+rec IDs to sessionStorage. Frontend-only
   * by design — no network call. The hook is the canonical write path so
   * the panel does not import feedbackCapture directly.
   */
  setFeedback: (analysisId: string, recId: string, value: FeedbackValue) => void;
}

export function useAiRecsHistory(): UseAiRecsHistoryResult {
  const [entries, setEntries] = useState<AiRecsHistoryEntry[]>([]);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setEntries(loadStored());
    setHydrated(true);
  }, []);

  const add = useCallback<UseAiRecsHistoryResult['add']>(
    (input) => {
      const entry: AiRecsHistoryEntry = {
        id: makeId(),
        createdAt: new Date().toISOString(),
        prompt: input.prompt,
        summary: summarize(
          input.diagnosis || input.recommendations || input.raw || input.prompt,
        ),
        diagnosis: input.diagnosis,
        recommendations: input.recommendations,
        raw: input.raw,
        status: 'new',
        notes: '',
        ...(input.strategyName ? { strategyName: input.strategyName } : {}),
      };
      setEntries((prev) => {
        const next = [entry, ...prev].slice(0, MAX_ENTRIES);
        persist(next);
        return next;
      });
      return entry;
    },
    [],
  );

  const updateStatus = useCallback<UseAiRecsHistoryResult['updateStatus']>(
    (id, status) => {
      setEntries((prev) => {
        const next = prev.map((e) => (e.id === id ? { ...e, status } : e));
        persist(next);
        return next;
      });
    },
    [],
  );

  const updateNotes = useCallback<UseAiRecsHistoryResult['updateNotes']>(
    (id, notes) => {
      setEntries((prev) => {
        const next = prev.map((e) => (e.id === id ? { ...e, notes } : e));
        persist(next);
        return next;
      });
    },
    [],
  );

  const deleteEntry = useCallback<UseAiRecsHistoryResult['deleteEntry']>(
    (id) => {
      setEntries((prev) => {
        const next = prev.filter((e) => e.id !== id);
        persist(next);
        return next;
      });
    },
    [],
  );

  const clear = useCallback(() => {
    setEntries([]);
    persist([]);
  }, []);

  const setFeedback = useCallback<UseAiRecsHistoryResult['setFeedback']>(
    (analysisId, recId, value) => {
      persistFeedback(analysisId, recId, value);
    },
    [],
  );

  return {
    entries,
    hydrated,
    add,
    updateStatus,
    updateNotes,
    deleteEntry,
    clear,
    setFeedback,
  };
}
