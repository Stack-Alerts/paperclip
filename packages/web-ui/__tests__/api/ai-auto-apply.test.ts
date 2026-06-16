import { runAutoApply } from '../../app/api/ai/auto-apply/orchestrator';

type FakeResponse = {
  ok: boolean;
  status: number;
  statusText: string;
  text: () => Promise<string>;
  json: () => Promise<unknown>;
};

function makeResponse(status: number, body: unknown): FakeResponse {
  const text = typeof body === 'string' ? body : JSON.stringify(body);
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: `status ${status}`,
    text: async () => text,
    json: async () => (typeof body === 'string' ? JSON.parse(body) : body),
  };
}

function deps(fetchImpl: jest.Mock) {
  return {
    fetch: fetchImpl as unknown as typeof fetch,
    baseUrl: 'http://localhost:8765',
  };
}

const baseReq = {
  strategyId: 's-1',
  recs: [
    { rec_id: 'r1', type: 'FIX_STRATEGY_TYPE' },
  ],
  optInDestructiveIds: null,
};

describe('runAutoApply (BTCAAAAA-36779)', () => {
  it('POSTs to the strategy builder auto-apply path with snake_case body', async () => {
    const fetchMock = jest.fn().mockResolvedValue(
      makeResponse(200, {
        strategy: { id: 's-1', name: 'Test', strategyType: 'Bullish' },
        dry_run: { entries: [], applicable_count: 0 },
        apply: { applied: [{ rec_id: 'r1' }], applied_count: 1 },
      }),
    );

    const result = await runAutoApply(baseReq, deps(fetchMock));

    expect(result.ok).toBe(true);
    expect(result.strategy?.id).toBe('s-1');
    expect(result.apply?.applied_count).toBe(1);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('http://localhost:8765/strategy-builder/strategies/s-1/auto-apply');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual({
      recs: [{ rec_id: 'r1', type: 'FIX_STRATEGY_TYPE' }],
      opt_in_destructive_ids: null,
    });
  });

  it('strips trailing slashes from the baseUrl before composing the path', async () => {
    const fetchMock = jest.fn().mockResolvedValue(
      makeResponse(200, {
        strategy: { id: 's-1', name: 'T', strategyType: 'Bullish' },
        dry_run: { entries: [], applicable_count: 0 },
        apply: { applied: [], applied_count: 0 },
      }),
    );
    await runAutoApply(baseReq, { ...deps(fetchMock), baseUrl: 'http://localhost:8765///' });
    expect(fetchMock.mock.calls[0][0]).toBe(
      'http://localhost:8765/strategy-builder/strategies/s-1/auto-apply',
    );
  });

  it('URL-encodes the strategyId', async () => {
    const fetchMock = jest.fn().mockResolvedValue(
      makeResponse(200, {
        strategy: { id: 'a b/c', name: 'T', strategyType: 'Bullish' },
        dry_run: { entries: [], applicable_count: 0 },
        apply: { applied: [], applied_count: 0 },
      }),
    );
    await runAutoApply(
      { ...baseReq, strategyId: 'a b/c' },
      deps(fetchMock),
    );
    expect(fetchMock.mock.calls[0][0]).toBe(
      'http://localhost:8765/strategy-builder/strategies/a%20b%2Fc/auto-apply',
    );
  });

  it('converts a 404 to ok=false with the FastAPI detail in `detail`', async () => {
    const fetchMock = jest
      .fn()
      .mockResolvedValue(makeResponse(404, { detail: 'Strategy not found' }));
    const result = await runAutoApply(baseReq, deps(fetchMock));
    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/HTTP 404/);
    expect(result.detail).toBe('Strategy not found');
  });

  it('converts a 401 to ok=false without leaking the upstream body', async () => {
    const fetchMock = jest
      .fn()
      .mockResolvedValue(makeResponse(401, { detail: 'Not authenticated' }));
    const result = await runAutoApply(baseReq, deps(fetchMock));
    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/HTTP 401/);
    expect(result.detail).toBe('Not authenticated');
  });

  it('survives a non-JSON error body (reverse-proxy 502)', async () => {
    const fetchMock = jest.fn().mockResolvedValue(
      makeResponse(502, '<html>Bad Gateway</html>'),
    );
    const result = await runAutoApply(baseReq, deps(fetchMock));
    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/HTTP 502/);
  });

  it('converts a thrown fetch (ECONNREFUSED) into ok=false', async () => {
    const fetchMock = jest.fn().mockRejectedValue(new Error('ECONNREFUSED'));
    const result = await runAutoApply(baseReq, deps(fetchMock));
    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/Could not reach the FastAPI service/);
    expect(result.detail).toBe('ECONNREFUSED');
  });

  it('rejects a malformed success payload', async () => {
    const fetchMock = jest.fn().mockResolvedValue(makeResponse(200, 'plain text'));
    const result = await runAutoApply(baseReq, deps(fetchMock));
    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/empty or malformed/);
  });

  it('passes optInDestructiveIds through when provided', async () => {
    const fetchMock = jest.fn().mockResolvedValue(
      makeResponse(200, {
        strategy: { id: 's-1', name: 'T', strategyType: 'Bullish' },
        dry_run: { entries: [], applicable_count: 0 },
        apply: { applied: [], applied_count: 0 },
      }),
    );
    await runAutoApply(
      { ...baseReq, optInDestructiveIds: ['r1', 'r2'] },
      deps(fetchMock),
    );
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.opt_in_destructive_ids).toEqual(['r1', 'r2']);
  });

  it('forwards the Authorization header unchanged when authHeader is set', async () => {
    const fetchMock = jest.fn().mockResolvedValue(
      makeResponse(200, {
        strategy: { id: 's-1', name: 'T', strategyType: 'Bullish' },
        dry_run: { entries: [], applicable_count: 0 },
        apply: { applied: [], applied_count: 0 },
      }),
    );
    await runAutoApply(baseReq, {
      ...deps(fetchMock),
      authHeader: 'Bearer eyJhbGciOiJIUzI1NiJ9.test',
    });
    const init = fetchMock.mock.calls[0][1];
    expect(init.headers.authorization).toBe('Bearer eyJhbGciOiJIUzI1NiJ9.test');
  });

  it('omits the Authorization header when authHeader is null', async () => {
    const fetchMock = jest.fn().mockResolvedValue(
      makeResponse(200, {
        strategy: { id: 's-1', name: 'T', strategyType: 'Bullish' },
        dry_run: { entries: [], applicable_count: 0 },
        apply: { applied: [], applied_count: 0 },
      }),
    );
    await runAutoApply(baseReq, { ...deps(fetchMock), authHeader: null });
    const init = fetchMock.mock.calls[0][1];
    expect(init.headers.authorization).toBeUndefined();
  });
});
