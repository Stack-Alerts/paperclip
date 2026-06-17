import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
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
// AC10: success banner auto-dismisses after 3s with opacity fade
// ──────────────────────────────────────────────────────────────────────────
describe('AiRecommendationsPanel — AC10 auto-dismiss (BTCAAAAA-36873)', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });
  afterEach(() => {
    jest.useRealTimers();
  });

  it('hides the applySuccess banner after ~3s and starts faded first', async () => {
    const fetchMock = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ok: true, apply: { applied: [], applied_count: 1 } }),
    });
    global.fetch = fetchMock as unknown as typeof fetch;

    render(
      <AiRecommendationsPanel
        result={makeResult()}
        strategy={makeStrategy()}
        backtestConfig={{}}
      />,
    );

    fireEvent.click(screen.getByTestId('ai-recs-apply-all'));
    // Confirm the apply-all confirmation modal.
    fireEvent.click(screen.getByRole('button', { name: /^Apply all$/i }));

    await waitFor(() => {
      expect(screen.getByTestId('ai-recs-apply-success')).toBeInTheDocument();
    });

    // After 2.7s the banner should still be visible (fade hasn't started yet).
    act(() => {
      jest.advanceTimersByTime(2700);
    });
    expect(screen.getByTestId('ai-recs-apply-success')).toBeInTheDocument();
    expect(screen.getByTestId('ai-recs-apply-success').style.opacity).toBe('1');

    // After 3s total the banner should be fully dismissed.
    act(() => {
      jest.advanceTimersByTime(400);
    });
    expect(screen.queryByTestId('ai-recs-apply-success')).toBeNull();
  });
});

// ──────────────────────────────────────────────────────────────────────────
// AC11: Apply-all moved to the bottom of the right pane
// ──────────────────────────────────────────────────────────────────────────
describe('AiRecommendationsPanel — AC11 apply-all footer (BTCAAAAA-36873)', () => {
  it('renders a single Apply-all button in the right pane', () => {
    render(
      <AiRecommendationsPanel
        result={makeResult()}
        strategy={makeStrategy()}
        backtestConfig={{}}
      />,
    );
    const applyAllButtons = screen.getAllByTestId('ai-recs-apply-all');
    expect(applyAllButtons).toHaveLength(1);
  });

  it('still gates the button on having a strategy loaded', () => {
    render(
      <AiRecommendationsPanel
        result={makeResult()}
        strategy={null}
        backtestConfig={{}}
      />,
    );
    const applyAll = screen.getByTestId('ai-recs-apply-all');
    expect(applyAll).toBeDisabled();
    expect(applyAll.getAttribute('title')).toMatch(/Load a strategy/);
  });
});

// ──────────────────────────────────────────────────────────────────────────
// AC12: Strategy diagnosis renders as compare-style cards
// ──────────────────────────────────────────────────────────────────────────
describe('AiRecommendationsPanel — AC12 diagnosis cards (BTCAAAAA-36873)', () => {
  function strategyWithBlocks(): Strategy {
    return {
      ...makeStrategy(),
      blocks: [
        { id: 'b1', type: 'RSI', index: 0, data: {} },
        { id: 'b2', type: 'EMA_CROSS', index: 1, data: {} },
      ] as unknown as Strategy['blocks'],
    };
  }

  it('renders one block card per strategy block', () => {
    render(
      <AiRecommendationsPanel
        result={makeResult()}
        strategy={strategyWithBlocks()}
        backtestConfig={{}}
      />,
    );
    const blockCards = screen.getAllByTestId('ai-recs-block-card');
    expect(blockCards).toHaveLength(2);
    expect(blockCards[0]).toHaveTextContent('RSI');
    expect(blockCards[1]).toHaveTextContent('EMA_CROSS');
  });

  it('shows the empty-state copy when the strategy has no blocks', () => {
    render(
      <AiRecommendationsPanel
        result={makeResult()}
        strategy={makeStrategy()}
        backtestConfig={{}}
      />,
    );
    expect(screen.queryByTestId('ai-recs-block-card')).toBeNull();
    expect(screen.getByText(/No building blocks on the current strategy/i)).toBeInTheDocument();
  });
});
