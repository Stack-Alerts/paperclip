import { act, renderHook, waitFor } from '@testing-library/react';
import { useBackendHealth } from '../useBackendHealth';

const mockGet = jest.fn();

jest.mock('@/lib/strategy-builder/api', () => ({
  get: (...args: unknown[]) => mockGet(...args),
}));

function makeOkHealth() {
  return {
    status: 'ok',
    redis: true,
    uptime_seconds: 120,
    version: '1.0.0',
    commit_sha: 'abc',
    branch: 'main',
  };
}

describe('useBackendHealth', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    mockGet.mockReset();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('exposes a recheck function', () => {
    mockGet.mockResolvedValue(makeOkHealth());
    const { result } = renderHook(() => useBackendHealth());
    expect(typeof result.current.recheck).toBe('function');
  });

  it('recheck() triggers an immediate /health call and resolves to connected', async () => {
    mockGet.mockResolvedValue(makeOkHealth());
    const { result } = renderHook(() => useBackendHealth());
    mockGet.mockClear();

    await act(async () => {
      result.current.recheck();
      await Promise.resolve();
    });

    expect(mockGet).toHaveBeenCalledWith('/health');
    await waitFor(() => expect(result.current.connectionState).toBe('connected'));
    expect(result.current.error).toBeNull();
  });

  it('recheck() captures the error when backend is unreachable', async () => {
    mockGet.mockRejectedValueOnce(new Error('NetworkError: fetch failed'));
    const { result } = renderHook(() => useBackendHealth());

    await waitFor(() => expect(result.current.connectionState).toBe('disconnected'));
    expect(result.current.error).toContain('NetworkError');

    mockGet.mockClear();
    mockGet.mockRejectedValueOnce(new Error('NetworkError: fetch failed'));

    await act(async () => {
      result.current.recheck();
      await Promise.resolve();
    });

    await waitFor(() => expect(mockGet).toHaveBeenCalledWith('/health'));
    await waitFor(() => expect(result.current.connectionState).toBe('disconnected'));
    expect(result.current.error).toContain('NetworkError');
  });

  it('recheck() reports checking state during the request', async () => {
    let resolveHealth: (v: unknown) => void = () => {};
    mockGet.mockImplementation(() => new Promise((res) => { resolveHealth = res; }));
    const { result } = renderHook(() => useBackendHealth());

    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(1));
    expect(result.current.connectionState).toBe('checking');

    await act(async () => {
      resolveHealth(makeOkHealth());
      await Promise.resolve();
    });
    await waitFor(() => expect(result.current.connectionState).toBe('connected'));

    mockGet.mockClear();
    let resolveRecheck: (v: unknown) => void = () => {};
    mockGet.mockImplementation(() => new Promise((res) => { resolveRecheck = res; }));

    await act(async () => {
      result.current.recheck();
      await Promise.resolve();
    });
    expect(result.current.connectionState).toBe('checking');

    await act(async () => {
      resolveRecheck(makeOkHealth());
      await Promise.resolve();
    });
    await waitFor(() => expect(result.current.connectionState).toBe('connected'));
  });
});
