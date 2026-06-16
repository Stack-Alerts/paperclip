import { act, renderHook } from '@testing-library/react';
import { useAiRecsHistory, summarize } from '../useAiRecsHistory';

const STORAGE_KEY = 'btc-paperclip:ai-recs:v1';

function makeSample(overrides: Partial<Parameters<ReturnType<typeof useAiRecsHistory>['add']>[0]> = {}) {
  return {
    prompt: 'Analyze this trading strategy backtest.',
    diagnosis: 'The strategy shows decent win rate but poor risk management.',
    recommendations: 'Tighten stop loss. Increase position size only after 50 trades.',
    raw: 'DIAGNOSIS: The strategy shows decent win rate but poor risk management.\n\nRECOMMENDATIONS: Tighten stop loss. Increase position size only after 50 trades.',
    ...overrides,
  };
}

describe('useAiRecsHistory', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('hydrates from localStorage on mount and exposes the hydrated flag', async () => {
    const { result } = renderHook(() => useAiRecsHistory());
    await act(async () => {
      await Promise.resolve();
    });
    expect(result.current.entries).toEqual([]);
    expect(result.current.hydrated).toBe(true);
  });

  it('adds an entry and persists to localStorage', async () => {
    const { result } = renderHook(() => useAiRecsHistory());
    await act(async () => {
      await Promise.resolve();
    });
    let addedId = '';
    act(() => {
      const e = result.current.add(makeSample({ strategyName: 'TestStrat' }));
      addedId = e.id;
    });
    expect(result.current.entries).toHaveLength(1);
    expect(result.current.entries[0].id).toBe(addedId);
    expect(result.current.entries[0].status).toBe('new');
    expect(result.current.entries[0].strategyName).toBe('TestStrat');
    const stored = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || '[]');
    expect(stored).toHaveLength(1);
    expect(stored[0].id).toBe(addedId);
  });

  it('prepends new entries (newest first)', async () => {
    const { result } = renderHook(() => useAiRecsHistory());
    await act(async () => {
      await Promise.resolve();
    });
    act(() => {
      result.current.add(makeSample({ prompt: 'first' }));
      result.current.add(makeSample({ prompt: 'second' }));
      result.current.add(makeSample({ prompt: 'third' }));
    });
    expect(result.current.entries.map((e) => e.prompt)).toEqual(['third', 'second', 'first']);
  });

  it('caps history at 100 entries (FIFO drop)', async () => {
    const { result } = renderHook(() => useAiRecsHistory());
    await act(async () => {
      await Promise.resolve();
    });
    act(() => {
      for (let i = 0; i < 105; i += 1) {
        result.current.add(makeSample({ prompt: `prompt-${i}` }));
      }
    });
    expect(result.current.entries).toHaveLength(100);
    expect(result.current.entries[0].prompt).toBe('prompt-104');
    expect(result.current.entries[99].prompt).toBe('prompt-5');
  });

  it('updates status, notes, and deletes entries', async () => {
    const { result } = renderHook(() => useAiRecsHistory());
    await act(async () => {
      await Promise.resolve();
    });
    let id = '';
    act(() => {
      id = result.current.add(makeSample()).id;
    });
    act(() => {
      result.current.updateStatus(id, 'applied');
      result.current.updateNotes(id, 'follow-up notes');
    });
    const updated = result.current.entries.find((e) => e.id === id);
    expect(updated?.status).toBe('applied');
    expect(updated?.notes).toBe('follow-up notes');

    act(() => {
      result.current.deleteEntry(id);
    });
    expect(result.current.entries).toHaveLength(0);
  });

  it('clear empties the list and storage', async () => {
    const { result } = renderHook(() => useAiRecsHistory());
    await act(async () => {
      await Promise.resolve();
    });
    act(() => {
      result.current.add(makeSample());
      result.current.add(makeSample());
    });
    expect(result.current.entries).toHaveLength(2);
    act(() => {
      result.current.clear();
    });
    expect(result.current.entries).toHaveLength(0);
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe('[]');
  });

  it('hydrates from previously persisted entries', async () => {
    const pre = {
      id: 'pre-1',
      createdAt: '2026-06-15T10:00:00.000Z',
      prompt: 'old',
      summary: 'old',
      diagnosis: 'd',
      recommendations: 'r',
      raw: 'raw',
      status: 'applied',
      notes: 'persisted',
    };
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify([pre]));
    const { result } = renderHook(() => useAiRecsHistory());
    await act(async () => {
      await Promise.resolve();
    });
    expect(result.current.entries).toHaveLength(1);
    expect(result.current.entries[0].id).toBe('pre-1');
    expect(result.current.entries[0].status).toBe('applied');
  });

  it('coerces malformed entries to null (drop on hydrate)', async () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify([{ not: 'valid' }, null, 'string', 42]),
    );
    const { result } = renderHook(() => useAiRecsHistory());
    await act(async () => {
      await Promise.resolve();
    });
    expect(result.current.entries).toEqual([]);
  });

  it('drops entries with invalid status on hydrate', async () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify([
        {
          id: 'a',
          createdAt: '2026-06-15T10:00:00.000Z',
          prompt: 'p',
          summary: 's',
          diagnosis: 'd',
          recommendations: 'r',
          raw: 'raw',
          status: 'bogus',
          notes: '',
        },
      ]),
    );
    const { result } = renderHook(() => useAiRecsHistory());
    await act(async () => {
      await Promise.resolve();
    });
    expect(result.current.entries).toEqual([]);
  });
});

describe('summarize', () => {
  it('returns the input unchanged when short', () => {
    expect(summarize('hello world', 100)).toBe('hello world');
  });
  it('truncates with ellipsis when over the limit', () => {
    const out = summarize('a'.repeat(300), 10);
    expect(out.endsWith('…')).toBe(true);
    expect(out.length).toBeLessThanOrEqual(10);
  });
  it('collapses whitespace before measuring', () => {
    const out = summarize('a\n\n\nb   c', 100);
    expect(out).toBe('a b c');
  });
});
