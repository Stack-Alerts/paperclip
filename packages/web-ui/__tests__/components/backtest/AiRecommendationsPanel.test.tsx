import React from 'react';
import { render, screen, fireEvent, waitFor, act, cleanup, within } from '@testing-library/react';
import { AiRecommendationsPanel } from '@/components/backtest/ai-recommendations/AiRecommendationsPanel';
import type { BacktestResult, Strategy, Trade } from '@/lib/strategy-builder/types';

jest.mock('@/hooks/useAiSettings', () => ({
  useAiSettings: jest.fn(),
}));

import { useAiSettings } from '@/hooks/useAiSettings';

const mockUseAiSettings = useAiSettings as jest.MockedFunction<typeof useAiSettings>;

function makeTrade(i: number): Trade {
  return {
    id: `t${i}`,
    entryTime: '2026-01-01T00:00:00Z',
    exitTime: '2026-01-01T01:00:00Z',
    entryPrice: 100,
    exitPrice: 110,
    side: 'long',
    quantity: 1,
    profit: 10,
    profitPercentage: 10,
  } as unknown as Trade;
}

function makeResult(overrides: Partial<BacktestResult> = {}): BacktestResult {
  return {
    id: 'r1',
    strategyId: 's1',
    runId: 'r1',
    status: 'completed',
    startDate: '2026-01-01',
    endDate: '2026-02-01',
    initialCapital: 10000,
    finalCapital: 11000,
    totalTrades: 1,
    winningTrades: 1,
    losingTrades: 0,
    winRate: 1,
    totalReturn: 1000,
    returnPercentage: 10,
    maxDrawdown: 5,
    sharpeRatio: 1.5,
    sortino_ratio: 2,
    profitFactor: 2,
    averageWin: 10,
    averageLoss: 0,
    calmar_ratio: 1,
    trades: [makeTrade(1)],
    createdAt: '2026-01-01T00:00:00Z',
    ...overrides,
  } as BacktestResult;
}

function makeStrategy(): Strategy {
  return {
    id: 's1',
    name: 'Test Strategy',
    description: 'desc',
    status: 'draft',
    strategyType: 'Bullish',
    blocks: [],
    settings: {
      timeframe: '1h',
      targetMarket: 'BTC/USD',
      riskParameters: { maxLossPerTrade: 2, maxDrawdown: 10, maxAllocation: 25 },
    },
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-01T00:00:00Z',
  } as unknown as Strategy;
}

const defaultSettings = {
  settings: {
    provider: 'anthropic' as const,
    model: 'claude-sonnet-4-6',
    apiKeys: { anthropic: 'sk-test' },
    ollamaBaseUrl: '',
  },
  save: jest.fn(),
  hydrated: true,
};

beforeEach(() => {
  jest.clearAllMocks();
  mockUseAiSettings.mockReturnValue(defaultSettings);
  // Reset any sessionStorage / localStorage state that the panel caches
  // across mounts (AC21 cache, AC9 auth token). Without this, tests within
  // the same describe chain inherit each other's state and trigger
  // confusing "first click did not toggle" symptoms.
  window.sessionStorage.clear();
  window.localStorage.clear();
});

describe('AiRecommendationsPanel — progress UI (BTCAAAAA-36777)', () => {
  it('does not show progress UI when idle', () => {
    render(
      <AiRecommendationsPanel
        result={makeResult()}
        strategy={makeStrategy()}
        backtestConfig={{}}
      />,
    );
    expect(screen.queryByTestId('ai-recs-progress')).toBeNull();
  });

  it('shows progress UI with phase label and percent when sending', async () => {
    // Never-resolving fetch so the phase deterministically lands on
    // awaiting-provider (Stage 3/4) without racing past it to done.
    const fetchMock = jest.fn().mockImplementation(
      () => new Promise(() => {}),
    );
    global.fetch = fetchMock as unknown as typeof fetch;

    render(
      <AiRecommendationsPanel
        result={makeResult()}
        strategy={makeStrategy()}
        backtestConfig={{}}
      />,
    );

    const sendButton = screen.getByRole('button', { name: /Approve & Send to AI/i });
    fireEvent.click(sendButton);

    // AC7 (BTCAAAAA-36873): the click now opens the optimization-goal modal
    // first; the actual fetch only fires after the user confirms a goal.
    fireEvent.click(screen.getByTestId('opt-goal-confirm'));

    await waitFor(() => {
      expect(screen.getByTestId('ai-recs-progress-label').textContent).toMatch(
        /Stage 3\/4/,
      );
    });
    expect(screen.getByTestId('ai-recs-progress-percent').textContent).toBe('75%');
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '75');
    expect(screen.getByTestId('ai-recs-cancel')).toBeInTheDocument();
  });

  it('re-enables the button after error', async () => {
    const fetchMock = jest.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ ok: false, error: 'Provider exploded' }),
    });
    global.fetch = fetchMock as unknown as typeof fetch;

    render(
      <AiRecommendationsPanel
        result={makeResult()}
        strategy={makeStrategy()}
        backtestConfig={{}}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: /Approve & Send to AI/i }));

    // AC7 (BTCAAAAA-36873): confirm the optimization goal first.
    fireEvent.click(screen.getByTestId('opt-goal-confirm'));

    await waitFor(() => {
      expect(screen.getByText(/AI analysis failed/)).toBeInTheDocument();
    });
    expect(screen.getByText(/Provider exploded/)).toBeInTheDocument();

    const retryButton = screen.getByRole('button', { name: /Retry/i });
    expect(retryButton).toBeEnabled();
  });

  it('cancel aborts the in-flight fetch', async () => {
    let abortSignal: AbortSignal | null | undefined;
    let rejectFetch: ((reason: unknown) => void) | undefined;
    const fetchMock = jest.fn().mockImplementation((_url: string, init?: RequestInit) => {
      abortSignal = init?.signal ?? null;
      return new Promise((_, reject) => {
        rejectFetch = reject;
        // Also wire the event listener as a belt-and-suspenders fallback for
        // jsdom versions that DO fire the abort event.
        init?.signal?.addEventListener('abort', () => {
          reject(new DOMException('aborted', 'AbortError'));
        });
      });
    });
    global.fetch = fetchMock as unknown as typeof fetch;

    render(
      <AiRecommendationsPanel
        result={makeResult()}
        strategy={makeStrategy()}
        backtestConfig={{}}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: /Approve & Send to AI/i }));

    // AC7 (BTCAAAAA-36873): confirm the optimization goal first.
    fireEvent.click(screen.getByTestId('opt-goal-confirm'));

    await waitFor(() => {
      expect(screen.getByTestId('ai-recs-cancel')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('ai-recs-cancel'));

    await waitFor(() => {
      expect(abortSignal?.aborted).toBe(true);
    });

    // jsdom 30's AbortSignal event dispatch is unreliable in tests, so we
    // explicitly drive the rejection once we've observed the abort. The
    // component's catch path is the unit under test here, not jsdom's event
    // loop.
    rejectFetch?.(new DOMException('aborted', 'AbortError'));

    await waitFor(() => {
      expect(screen.getByText(/Request cancelled\./)).toBeInTheDocument();
    });
  });
});

// ──────────────────────────────────────────────────────────────────────────
// AC8: countdown ETA shown next to the progress percent during awaiting-provider
// ──────────────────────────────────────────────────────────────────────────
describe('AiRecommendationsPanel — AC8 countdown (BTCAAAAA-36873)', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });
  afterEach(() => {
    jest.useRealTimers();
  });

  it('shows ~Ns ETA next to the percent while waiting for provider', async () => {
    const fetchMock = jest.fn().mockImplementation(
      () => new Promise(() => {}),
    );
    global.fetch = fetchMock as unknown as typeof fetch;

    render(
      <AiRecommendationsPanel
        result={makeResult()}
        strategy={makeStrategy()}
        backtestConfig={{}}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: /Approve & Send to AI/i }));
    fireEvent.click(screen.getByTestId('opt-goal-confirm'));

    await waitFor(() => {
      expect(screen.getByTestId('ai-recs-progress-label').textContent).toMatch(/Stage 3\/4/);
    });

    expect(screen.getByTestId('ai-recs-progress-eta').textContent).toBe('~30s');

    act(() => {
      jest.advanceTimersByTime(5000);
    });
    expect(screen.getByTestId('ai-recs-progress-eta').textContent).toBe('~25s');
  });

  it('does not show an ETA outside the awaiting-provider phase', () => {
    render(
      <AiRecommendationsPanel
        result={makeResult()}
        strategy={makeStrategy()}
        backtestConfig={{}}
      />,
    );
    expect(screen.queryByTestId('ai-recs-progress-eta')).toBeNull();
  });
});

// ──────────────────────────────────────────────────────────────────────────
// AC9: Export to JSON is gated on admin role
// ──────────────────────────────────────────────────────────────────────────
describe('AiRecommendationsPanel — AC9 admin gate (BTCAAAAA-36873)', () => {
  function setAuthToken(token: string | null) {
    if (token === null) {
      window.localStorage.removeItem('auth_token');
    } else {
      window.localStorage.setItem('auth_token', token);
    }
  }

  // Build a JWT-like "header.payload.sig" string with a base64url JSON payload.
  function makeJwt(claims: Record<string, unknown>): string {
    const header = btoa(JSON.stringify({ alg: 'none', typ: 'JWT' }));
    const payload = btoa(JSON.stringify(claims))
      .replace(/=/g, '')
      .replace(/\+/g, '-')
      .replace(/\//g, '_');
    return `${header}.${payload}.sig`;
  }

  it('disables Export to JSON when no auth_token is present', () => {
    setAuthToken(null);
    render(
      <AiRecommendationsPanel
        result={makeResult()}
        strategy={makeStrategy()}
        backtestConfig={{}}
      />,
    );
    const exportBtn = screen.getByRole('button', { name: /Export to JSON/i });
    expect(exportBtn).toBeDisabled();
    expect(exportBtn.getAttribute('title')).toMatch(/admin/i);
  });

  it('disables Export to JSON when auth_token has no admin claim', () => {
    setAuthToken(makeJwt({ sub: 'u1', role: 'viewer' }));
    render(
      <AiRecommendationsPanel
        result={makeResult()}
        strategy={makeStrategy()}
        backtestConfig={{}}
      />,
    );
    const exportBtn = screen.getByRole('button', { name: /Export to JSON/i });
    expect(exportBtn).toBeDisabled();
  });

  it('enables Export to JSON when auth_token has admin=true', () => {
    setAuthToken(makeJwt({ sub: 'u1', admin: true }));
    render(
      <AiRecommendationsPanel
        result={makeResult()}
        strategy={makeStrategy()}
        backtestConfig={{}}
      />,
    );
    const exportBtn = screen.getByRole('button', { name: /Export to JSON/i });
    expect(exportBtn).toBeEnabled();
  });

  it('enables Export to JSON when auth_token has role=admin', () => {
    setAuthToken(makeJwt({ sub: 'u1', role: 'admin' }));
    render(
      <AiRecommendationsPanel
        result={makeResult()}
        strategy={makeStrategy()}
        backtestConfig={{}}
      />,
    );
    const exportBtn = screen.getByRole('button', { name: /Export to JSON/i });
    expect(exportBtn).toBeEnabled();
  });
});

// ──────────────────────────────────────────────────────────────────────────
// AC15: per-tile toggle cards render in a grid (one card per AI rec)
// AC18: click toggles apply/rollback; rollback is local
//
// The toggle grid only renders AFTER the AI analysis arrives (the panel
// derives its parsedRecs from local `aiAnalysis` state, which is populated
// when /api/ai/analyze returns). Each test below mocks the analyze fetch
// response and clicks through the send + goal-confirm flow to land in that
// post-analysis state before exercising the grid.
// ──────────────────────────────────────────────────────────────────────────
describe('AiRecommendationsPanel — AC15 per-tile toggle grid (BTCAAAAA-36873 v3)', () => {
  const SAMPLE_RECOMMENDATIONS =
    '1. Reduce position size\n   Type: signal\n   Rationale: cap exposure\n   Key: maxAllocation\n   Value: 15\n\n2. Tighten stop-loss\n   Type: risk\n   Rationale: cut losers early\n   Key: stopLossPct\n   Value: 1.5';

  const SAMPLE_DIAGNOSIS =
    'The strategy overshoots on high-volatility regimes.';

  // The /api/ai/analyze response is { ok, text } where text is the raw
  // model reply. parseAnalysisResponse then splits it on the
  // "DIAGNOSIS:" / "RECOMMENDATIONS:" headers before populating the
  // local `aiAnalysis` state.
  const SAMPLE_TEXT =
    `DIAGNOSIS: ${SAMPLE_DIAGNOSIS}\n\n` +
    `RECOMMENDATIONS: ${SAMPLE_RECOMMENDATIONS}`;

  /**
   * Render the panel with a mocked fetch that resolves /api/ai/analyze
   * with two recommendations, then drive the send + goal-confirm clicks
   * so the panel lands in the post-analysis state. Returns the fetch mock
   * so individual tests can attach additional expectations.
   */
  async function renderWithAnalysis() {
    const fetchMock = jest.fn().mockImplementation((url: string) => {
      const u = String(url);
      if (u.includes('/api/ai/analyze')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ ok: true, text: SAMPLE_TEXT }),
        });
      }
      // Any other fetch (auto-apply during the toggle tests) returns success.
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          strategy: makeStrategy(),
          apply: { applied: [{ rec_id: 'rec-0-ignored' }], applied_count: 1 },
        }),
      });
    });
    global.fetch = fetchMock as unknown as typeof fetch;

    render(
      <AiRecommendationsPanel
        result={makeResult()}
        strategy={makeStrategy()}
        backtestConfig={{}}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: /Approve & Send to AI/i }));
    fireEvent.click(screen.getByTestId('opt-goal-confirm'));

    await waitFor(() => {
      expect(screen.getAllByTestId('ai-recs-toggle-card')).toHaveLength(2);
    });
    return fetchMock;
  }

  it('renders one toggle card per parsed recommendation', async () => {
    await renderWithAnalysis();
    const cards = screen.getAllByTestId('ai-recs-toggle-card');
    expect(cards).toHaveLength(2);
  });

  it('renders OFF state for every card on initial analysis', async () => {
    await renderWithAnalysis();
    const badges = screen.getAllByTestId('ai-recs-toggle-badge');
    expect(badges).toHaveLength(2);
    expect(badges.every((b) => b.textContent === 'OFF')).toBe(true);
  });

  it('flips a card to ON state when clicked and POSTs the single rec to /api/ai/auto-apply', async () => {
    const fetchMock = await renderWithAnalysis();

    const cards = screen.getAllByTestId('ai-recs-toggle-card');
    fireEvent.click(cards[0]);

    await waitFor(() => {
      const badges = screen.getAllByTestId('ai-recs-toggle-badge');
      expect(badges[0].textContent).toBe('ON');
    });

    const autoApplyCall = fetchMock.mock.calls.find(([url]) =>
      String(url).includes('/api/ai/auto-apply'),
    );
    expect(autoApplyCall).toBeDefined();
    const body = JSON.parse(autoApplyCall![1].body as string);
    expect(body.strategyId).toBe('s1');
    expect(Array.isArray(body.recs)).toBe(true);
    expect(body.recs).toHaveLength(1);
  });

  it('flips a card back to OFF on second click without calling the API again', async () => {
    const fetchMock = await renderWithAnalysis();

    const cards = screen.getAllByTestId('ai-recs-toggle-card');
    fireEvent.click(cards[0]);
    await waitFor(() => {
      expect(screen.getAllByTestId('ai-recs-toggle-badge')[0].textContent).toBe('ON');
    });
    const callsBefore = fetchMock.mock.calls.length;

    fireEvent.click(cards[0]);
    await waitFor(() => {
      expect(screen.getAllByTestId('ai-recs-toggle-badge')[0].textContent).toBe('OFF');
    });
    // No new auto-apply POST — rollback is local (AC18).
    expect(fetchMock.mock.calls.length).toBe(callsBefore);
  });
});

// ──────────────────────────────────────────────────────────────────────────
// AC21 + AC22: recommendations are retained across unmount/remount via
// sessionStorage cache; cache is keyed by (strategyId, backtestRunId) so it
// does not bleed across strategies; explicit "Re-run AI" is the only reload
// trigger.
// ──────────────────────────────────────────────────────────────────────────
describe('AiRecommendationsPanel — AC21/AC22 retention (BTCAAAAA-36873 v3)', () => {
  // Same response shape used by the AC15 tests above.
  const SAMPLE_TEXT =
    'DIAGNOSIS: The strategy overshoots on high-volatility regimes.\n\n' +
    'RECOMMENDATIONS:\n' +
    '1. Reduce position size\n' +
    '   Type: signal\n' +
    '   Rationale: cap exposure\n' +
    '   - **maxAllocation**: 15\n\n' +
    '2. Tighten stop-loss\n' +
    '   Type: risk\n' +
    '   Rationale: cut losers early\n' +
    '   - **stopLossPct**: 1.5';

  function makeAnalyzeFetchMock() {
    return jest.fn().mockImplementation((url: string) => {
      const u = String(url);
      if (u.includes('/api/ai/analyze')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ ok: true, text: SAMPLE_TEXT }),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          strategy: makeStrategy(),
          apply: { applied: [{ rec_id: 'rec-0-ignored' }], applied_count: 1 },
        }),
      });
    });
  }

  async function driveAnalysis(
    fetchMock: jest.Mock,
    strategyId = 's1',
    runId = 'r1',
  ) {
    global.fetch = fetchMock as unknown as typeof fetch;

    render(
      <AiRecommendationsPanel
        result={makeResult({ id: runId, strategyId })}
        strategy={{ ...makeStrategy(), id: strategyId } as unknown as Strategy}
        backtestConfig={{}}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: /Approve & Send to AI/i }));
    fireEvent.click(screen.getByTestId('opt-goal-confirm'));

    await waitFor(() => {
      expect(screen.getAllByTestId('ai-recs-toggle-card')).toHaveLength(2);
    });
  }

  beforeEach(() => {
    // Clear cache between tests so they don't bleed via sessionStorage.
    window.sessionStorage.clear();
  });

  it('AC21: re-mounting the panel reads the cached recommendations from sessionStorage instead of calling /api/ai/analyze again', async () => {
    const fetchMock = makeAnalyzeFetchMock();
    await driveAnalysis(fetchMock);

    const analyzeCallsAfterFirstMount =
      fetchMock.mock.calls.filter(([url]) =>
        String(url).includes('/api/ai/analyze'),
      ).length;
    expect(analyzeCallsAfterFirstMount).toBe(1);

    // Unmount, then re-render the panel. AC21 requires the second mount to
    // read the cached recommendations instead of re-fetching.
    cleanup();

    await driveAnalysis(fetchMock);

    const analyzeCallsAfterSecondMount =
      fetchMock.mock.calls.filter(([url]) =>
        String(url).includes('/api/ai/analyze'),
      ).length;
    expect(analyzeCallsAfterSecondMount).toBe(1);

    // Toggle state survives the remount as part of the cached payload.
    const cards = screen.getAllByTestId('ai-recs-toggle-card');
    expect(cards).toHaveLength(2);
    expect(screen.getAllByTestId('ai-recs-toggle-badge').every((b) => b.textContent === 'OFF')).toBe(
      true,
    );
  });

  it('AC21: cache is scoped by strategyId — mounting a different strategy does not hydrate stale recs', async () => {
    const fetchMock = makeAnalyzeFetchMock();
    // First mount: strategy s1 produces recommendations + writes cache.
    await driveAnalysis(fetchMock, 's1', 'r1');

    cleanup();

    // Second mount: strategy s2 (different id) must NOT hydrate the s1
    // cache; it should treat the panel as fresh (no toggle cards visible
    // until the user clicks "Re-run AI" or sends a new analysis).
    render(
      <AiRecommendationsPanel
        result={makeResult({ id: 'r2', strategyId: 's2' })}
        strategy={{ ...makeStrategy(), id: 's2' } as unknown as Strategy}
        backtestConfig={{}}
      />,
    );

    // The send button must still be visible (no cached recs for s2), and no
    // toggle cards from a foreign strategy.
    expect(screen.getByRole('button', { name: /Approve & Send to AI/i })).toBeInTheDocument();
    expect(screen.queryByTestId('ai-recs-toggle-card')).toBeNull();

    // Sanity: cache exists for s1 but not s2.
    const raw = window.sessionStorage.getItem('ai_recs_v3_cache_v1');
    if (raw) {
      const parsed = JSON.parse(raw) as {
        entries?: Record<string, unknown>;
      };
      // Cache exists only for s1, never for s2.
      const hasS1 = Object.keys(parsed.entries ?? {}).some((k) => k.includes('s1'));
      const hasS2 = Object.keys(parsed.entries ?? {}).some((k) => k.includes('s2'));
      expect(hasS1).toBe(true);
      expect(hasS2).toBe(false);
    }
  });

  it('AC22: explicit "Send Again" button is the only reload trigger after a successful analysis', async () => {
    const fetchMock = makeAnalyzeFetchMock();
    await driveAnalysis(fetchMock);

    // After the initial analysis completes, no automatic follow-up call to
    // /api/ai/analyze should occur (no polling, no implicit refresh).
    const analyzeCalls =
      fetchMock.mock.calls.filter(([url]) =>
        String(url).includes('/api/ai/analyze'),
      ).length;
    expect(analyzeCalls).toBe(1);

    // v3 implements AC22 with a single button that re-labels per phase:
    // "Approve & Send to AI" (idle) → "Send Again" (post-analysis, the
    // explicit reload trigger) → "Retry" (error). The "Send Again" affordance
    // is the only path that produces a fresh /api/ai/analyze call after the
    // first analysis completes.
    const rerunBtn = screen.getByRole('button', { name: /Send Again/i });
    expect(rerunBtn).toBeInTheDocument();

    fireEvent.click(rerunBtn);

    // Same AC7 modal pattern as the initial send: the button click opens
    // the optimization-goal modal, and the actual /api/ai/analyze fetch
    // fires only after the user confirms a goal.
    fireEvent.click(screen.getByTestId('opt-goal-confirm'));

    await waitFor(() => {
      const analyzeCallsAfter =
        fetchMock.mock.calls.filter(([url]) =>
          String(url).includes('/api/ai/analyze'),
        ).length;
      expect(analyzeCallsAfter).toBeGreaterThan(analyzeCalls);
    });
  });
});

// ──────────────────────────────────────────────────────────────────────────
// BTCAAAAA-36917 v4 UX: empty state should let the user preview the v3
// redesign and load a demo payload *without* polluting the
// `ai_recs_v3_cache_v1` sessionStorage cache. The cache is reserved for
// genuine /api/ai/analyze results and must never carry preview/demo data —
// otherwise a future remount could hydrate the demo payload instead of a
// real re-run, and AC21's strategy-scoping invariant would be silently
// undermined.
// ──────────────────────────────────────────────────────────────────────────
describe('AiRecommendationsPanel — empty-state preview + demo (BTCAAAAA-36917 v4)', () => {
  // Same response shape used by the AC21/22 retention tests above. Defined
  // locally because the AC21/22 helpers are scoped to their own describe
  // arrow body and not visible here. The shape produces 2 numbered recs so
  // the positive-control test can wait on `getAllByTestId(...).length === 2`.
  const SAMPLE_TEXT =
    'DIAGNOSIS: The strategy overshoots on high-volatility regimes.\n\n' +
    'RECOMMENDATIONS:\n' +
    '1. Reduce position size\n' +
    '   Type: signal\n' +
    '   Rationale: cap exposure\n' +
    '   - **maxAllocation**: 15\n\n' +
    '2. Tighten stop-loss\n' +
    '   Type: risk\n' +
    '   Rationale: cut losers early\n' +
    '   - **stopLossPct**: 1.5';

  function makeAnalyzeFetchMock() {
    return jest.fn().mockImplementation((url: string) => {
      const u = String(url);
      if (u.includes('/api/ai/analyze')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ ok: true, text: SAMPLE_TEXT }),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({
          ok: true,
          strategy: makeStrategy(),
          apply: { applied: [{ rec_id: 'rec-0-ignored' }], applied_count: 1 },
        }),
      });
    });
  }

  // Never-resolving fetch so the empty state cannot accidentally auto-run
  // an analysis during these tests. The only /api/ai/analyze calls that
  // happen must come from explicit "Send Again" clicks in the test body.
  function makeNeverResolvingFetchMock(): jest.Mock {
    return jest.fn().mockImplementation(
      () => new Promise(() => {}),
    );
  }

  function renderEmptyPanel() {
    global.fetch = makeNeverResolvingFetchMock() as unknown as typeof fetch;
    return render(
      <AiRecommendationsPanel
        result={makeResult()}
        strategy={makeStrategy()}
        backtestConfig={{}}
      />,
    );
  }

  beforeEach(() => {
    // Defensive: clear any state the previous describe block left behind.
    window.sessionStorage.clear();
    window.localStorage.clear();
  });

  it('v4: empty state surfaces both preview and demo affordances', () => {
    renderEmptyPanel();

    // The two affordances are rendered together so the user can choose how
    // to explore the redesign.
    const actions = screen.getByTestId('ai-recs-empty-actions');
    expect(actions).toBeInTheDocument();
    expect(within(actions).getByTestId('ai-recs-preview-btn')).toBeInTheDocument();
    expect(within(actions).getByTestId('ai-recs-demo-btn')).toBeInTheDocument();
  });

  it('v4: "Preview the new layout" renders a static card without writing to the cache', async () => {
    renderEmptyPanel();

    fireEvent.click(screen.getByTestId('ai-recs-preview-btn'));

    // The static preview card appears; the v3 toggle grid does NOT (no
    // aiAnalysis state change, so no recs to toggle).
    await waitFor(() => {
      expect(screen.getByTestId('ai-recs-preview-card')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('ai-recs-toggle-card')).toBeNull();
    // The empty-state button group is hidden once preview is open.
    expect(screen.queryByTestId('ai-recs-empty-actions')).toBeNull();

    // The preview card carries the same v3 visual contract (badge + params)
    // so the user sees the actual compare-style layout.
    expect(screen.getAllByTestId('ai-recs-toggle-badge')).toHaveLength(1);
    expect(screen.getByTestId('ai-recs-toggle-params')).toBeInTheDocument();

    // Hard contract: preview must NEVER land in sessionStorage, even though
    // the persistence effect could re-run after a re-render.
    expect(window.sessionStorage.getItem('ai_recs_v3_cache_v1')).toBeNull();
  });

  it('v4: "Load demo data" seeds 3 sample recommendations without writing to the cache', async () => {
    renderEmptyPanel();

    fireEvent.click(screen.getByTestId('ai-recs-demo-btn'));

    // The v3 toggle grid hydrates with 3 hardcoded sample recs. We assert
    // count only (not identity) so the sample payload can evolve without
    // breaking this contract test.
    await waitFor(() => {
      expect(screen.getAllByTestId('ai-recs-toggle-card').length).toBeGreaterThanOrEqual(2);
    });
    const cards = screen.getAllByTestId('ai-recs-toggle-card');
    expect(cards.length).toBe(3);

    // Exit-demo affordance is the only way back to the empty state; it must
    // be visible whenever demoMode is true.
    expect(screen.getByTestId('ai-recs-exit-demo-btn')).toBeInTheDocument();

    // Hard contract: demo data must NEVER land in sessionStorage. The
    // persistence effect fires (aiAnalysis changed) but the demoMode guard
    // inside it must short-circuit before the setItem call.
    expect(window.sessionStorage.getItem('ai_recs_v3_cache_v1')).toBeNull();
  });

  it('v4: "Exit demo" returns the panel to the empty state and never writes the cache', async () => {
    renderEmptyPanel();

    fireEvent.click(screen.getByTestId('ai-recs-demo-btn'));
    await waitFor(() => {
      expect(screen.getAllByTestId('ai-recs-toggle-card')).toHaveLength(3);
    });

    fireEvent.click(screen.getByTestId('ai-recs-exit-demo-btn'));

    // Empty state is restored: toggle cards gone, exit button gone, both
    // empty-state affordances back. The preview/demo reset inside the
    // click handler also nulls aiAnalysis so the persistence effect
    // cannot accidentally persist the now-cleared demo payload.
    await waitFor(() => {
      expect(screen.getByTestId('ai-recs-empty-actions')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('ai-recs-toggle-card')).toBeNull();
    expect(screen.queryByTestId('ai-recs-exit-demo-btn')).toBeNull();
    expect(screen.getByTestId('ai-recs-preview-btn')).toBeInTheDocument();
    expect(screen.getByTestId('ai-recs-demo-btn')).toBeInTheDocument();

    // Still no cache pollution after exit.
    expect(window.sessionStorage.getItem('ai_recs_v3_cache_v1')).toBeNull();
  });

  it('v4: a subsequent real /api/ai/analyze call clears preview/demo state and DOES write the cache (positive control)', async () => {
    renderEmptyPanel();

    // Open preview, then trigger a real analysis. The preview flag must be
    // cleared by the runApproveAndSend success path so the user does not
    // see a stale preview card on top of their real results.
    fireEvent.click(screen.getByTestId('ai-recs-preview-btn'));
    expect(screen.getByTestId('ai-recs-preview-card')).toBeInTheDocument();

    // Swap in a working analyze mock and drive a real analysis.
    const fetchMock = makeAnalyzeFetchMock();
    global.fetch = fetchMock as unknown as typeof fetch;
    fireEvent.click(screen.getByRole('button', { name: /Approve & Send to AI/i }));
    fireEvent.click(screen.getByTestId('opt-goal-confirm'));

    await waitFor(() => {
      expect(screen.getAllByTestId('ai-recs-toggle-card')).toHaveLength(2);
    });

    // Preview card is gone; preview/demo flags reset before the real
    // setAiAnalysis call.
    expect(screen.queryByTestId('ai-recs-preview-card')).toBeNull();
    expect(screen.queryByTestId('ai-recs-empty-actions')).toBeNull();

    // Positive control: the cache mechanism itself works for a real
    // analysis — the demoMode guard is what kept preview/demo out, not a
    // broken persistence path.
    await waitFor(() => {
      const raw = window.sessionStorage.getItem('ai_recs_v3_cache_v1');
      expect(raw).not.toBeNull();
    });
  });

  it('v5: preview card has "Request preview" header + "Request outcome" pill on the right', async () => {
    renderEmptyPanel();
    fireEvent.click(screen.getByTestId('ai-recs-preview-btn'));

    const previewCard = await screen.findByTestId('ai-recs-preview-card');
    const header = within(previewCard).getByTestId('ai-recs-preview-header');
    expect(header).toBeInTheDocument();
    expect(within(header).getByText(/Request preview/i)).toBeInTheDocument();

    const pill = within(header).getByTestId('ai-recs-preview-outcome-pill');
    expect(pill).toBeInTheDocument();
    expect(pill).toHaveTextContent(/Request outcome/i);
    expect(pill).toHaveTextContent(/Ready/i);
  });
});
