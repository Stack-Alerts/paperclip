// BTCAAAAA-37772 Sprint B/B4 — hybrid re-projection server endpoint.
//
// Wraps the existing Python backtest pipeline: starts a backtest on the
// currently-stored strategy (which already has applied rec params from
// auto-apply), polls for completion, and returns normalised KPI values so the
// StrategyImpactKpiBar can flip from Preview → Confirmed.
//
// The endpoint is deliberately stateless — it fires the backtest and waits
// inline (max POLL_CEILING_MS). This keeps the calling side simple: one
// fetch, one JSON response.

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8765';
const POLL_INTERVAL_MS = 2_000;
const POLL_CEILING_MS = 120_000;

interface ReProjectBody {
  strategyId?: unknown;
  backtestConfig?: unknown;
}

interface BacktestStartResponse {
  runId?: string;
}

interface BacktestStatusResponse {
  status?: string;
  error?: string;
  winRate?: number;
  profitFactor?: number;
  maxDrawdown?: number;
  totalTrades?: number;
  initialCapital?: number;
  finalCapital?: number;
}

export interface ReProjectKpis {
  winRate: number;
  netLiquidity: number;
  maxDrawdown: number;
  profitFactor: number;
  entries: number;
}

function clampUnit(n: number): number {
  if (!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(1, n));
}

function numberOr(v: unknown, fallback: number): number {
  const n = typeof v === 'number' ? v : Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function toKpis(status: BacktestStatusResponse): ReProjectKpis {
  const initial = numberOr(status.initialCapital, 0);
  const final = numberOr(status.finalCapital, 0);
  return {
    winRate: clampUnit(numberOr(status.winRate, 0)),
    netLiquidity: Number.isFinite(final - initial) ? final - initial : 0,
    maxDrawdown: clampUnit(numberOr(status.maxDrawdown, 0)),
    profitFactor: Math.max(0, numberOr(status.profitFactor, 0)),
    entries: Math.max(0, Math.trunc(numberOr(status.totalTrades, 0))),
  };
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  return res.json() as Promise<T>;
}

export async function POST(request: Request): Promise<Response> {
  let body: ReProjectBody;
  try {
    body = (await request.json()) as ReProjectBody;
  } catch {
    return Response.json({ ok: false, error: 'Invalid JSON body.' }, { status: 400 });
  }

  const strategyId = body.strategyId;
  if (typeof strategyId !== 'string' || strategyId.length === 0) {
    return Response.json({ ok: false, error: 'Missing strategyId.' }, { status: 400 });
  }

  const backtestConfig = body.backtestConfig ?? {};

  const authHeader = request.headers.get('Authorization') ?? '';

  const startUrl = `${BASE_URL}/strategies/${encodeURIComponent(strategyId)}/backtest`;
  let runId: string;
  try {
    const startResp = await fetchJson<BacktestStartResponse>(startUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(authHeader ? { Authorization: authHeader } : {}),
      },
      body: JSON.stringify(backtestConfig),
    });
    if (!startResp.runId) {
      return Response.json({ ok: false, error: 'Backend did not return a runId.' }, { status: 502 });
    }
    runId = startResp.runId;
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Failed to start re-backtest.';
    return Response.json({ ok: false, error: msg }, { status: 502 });
  }

  const deadline = Date.now() + POLL_CEILING_MS;
  const pollUrl = `${BASE_URL}/strategies/${encodeURIComponent(strategyId)}/backtest/${encodeURIComponent(runId)}`;
  for (;;) {
    if (Date.now() > deadline) {
      return Response.json({ ok: false, error: 'Re-backtest timed out.' }, { status: 504 });
    }
    await new Promise<void>((r) => setTimeout(r, POLL_INTERVAL_MS));
    let status: BacktestStatusResponse;
    try {
      status = await fetchJson<BacktestStatusResponse>(pollUrl, {
        headers: authHeader ? { Authorization: authHeader } : {},
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Polling failed.';
      return Response.json({ ok: false, error: msg }, { status: 502 });
    }
    if (status.status === 'error') {
      return Response.json({ ok: false, error: status.error ?? 'Backtest failed.' }, { status: 502 });
    }
    if (status.status === 'done') {
      return Response.json({ ok: true, kpis: toKpis(status) });
    }
  }
}
