// Typed fetch wrapper for REST endpoints
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8765';

export interface RequestOptions extends RequestInit {
  query?: Record<string, string | number>;
}

async function fetchWithAuth(
  endpoint: string,
  options: RequestOptions = {}
): Promise<Response> {
  const url = new URL(endpoint.startsWith('http') ? endpoint : `${BASE_URL}${endpoint}`);

  if (options.query) {
    Object.entries(options.query).forEach(([key, value]) => {
      url.searchParams.append(key, String(value));
    });
  }

  const token = getAuthToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url.toString(), {
    ...options,
    headers,
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }

  return response;
}

export async function get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
  const response = await fetchWithAuth(endpoint, { ...options, method: 'GET' });
  return response.json();
}

export async function post<T>(
  endpoint: string,
  data?: unknown,
  options?: RequestOptions
): Promise<T> {
  const response = await fetchWithAuth(endpoint, {
    ...options,
    method: 'POST',
    body: data ? JSON.stringify(data) : undefined,
  });
  return response.json();
}

export async function put<T>(
  endpoint: string,
  data?: unknown,
  options?: RequestOptions
): Promise<T> {
  const response = await fetchWithAuth(endpoint, {
    ...options,
    method: 'PUT',
    body: data ? JSON.stringify(data) : undefined,
  });
  return response.json();
}

export async function patch<T>(
  endpoint: string,
  data?: unknown,
  options?: RequestOptions
): Promise<T> {
  const response = await fetchWithAuth(endpoint, {
    ...options,
    method: 'PATCH',
    body: data ? JSON.stringify(data) : undefined,
  });
  return response.json();
}

export async function del<T>(endpoint: string, options?: RequestOptions): Promise<T> {
  const response = await fetchWithAuth(endpoint, { ...options, method: 'DELETE' });
  return response.json();
}

// Auth token helper
function getAuthToken(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }
  return localStorage.getItem('auth_token');
}

export function setAuthToken(token: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem('auth_token', token);
  }
}

export function clearAuthToken(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('auth_token');
  }
}

// Strategy Builder API endpoints
// All strategy-builder endpoints read from the strategy builder ORM DB, not the ITM runtime.

const SB = '/strategy-builder/strategies';

export interface CreateStrategyRequest {
  name: string;
  description?: string;
}

export async function createStrategy(data: CreateStrategyRequest) {
  return post(SB, data);
}

export async function listStrategies() {
  return get(SB);
}

export async function getStrategy(id: string) {
  return get(`${SB}/${id}`);
}

export async function updateStrategy(id: string, data: unknown) {
  return put(`${SB}/${id}`, data);
}

export async function deleteStrategy(id: string) {
  return del(`${SB}/${id}`);
}

export async function deleteStrategyScoped(
  id: string,
  scope: 'entire' | 'version',
  versionIds?: string[],
) {
  if (scope === 'version' && versionIds?.length) {
    return post(`${SB}/${id}/versions/delete`, { version_ids: versionIds });
  }
  return del(`${SB}/${id}`);
}

export async function duplicateStrategyScoped(
  id: string,
  scope: 'version' | 'strategy',
  newName?: string,
) {
  return post(`${SB}/${id}/duplicate`, { scope, name: newName });
}

export async function getBlockLibrary() {
  return get('/blocks');
}

export async function getBlockSchema(blockType: string) {
  return get(`/blocks/${blockType}`);
}

export async function validateStrategy(id: string) {
  // Runs the backend InstitutionalValidator against the strategy's latest
  // stored version. The body is empty by design — validation always reads
  // from the DB, not from in-flight UI edits (BTCAAAAA-32954).
  return post(`/strategy-builder/strategies/${id}/validate`, {});
}

export async function autoFixStrategy(
  id: string,
  ruleId: string,
  autoFixData: Record<string, unknown> | undefined,
) {
  // Apply the named validator auto-fix to the latest stored version. Returns
  // the updated strategy (new version) so the caller can swap currentStrategy
  // directly. BTCAAAAA-32954 board comment 9b5949ca.
  return post(`/strategy-builder/strategies/${id}/auto-fix`, {
    rule_id: ruleId,
    auto_fix_data: autoFixData ?? null,
  });
}

export async function revertStrategy(id: string, versionId: string) {
  // Revert to a previous DB version's blocks by creating a new version.
  // Uses versionId so the backend reads raw DB blocks, avoiding the UI-format
  // mismatch that occurs when the frontend sends normalized blocks (BTCAAAAA-33599).
  return post(`/strategy-builder/strategies/${id}/revert`, {
    versionId,
  });
}

export async function runBacktest(id: string, config: unknown) {
  return post(`/strategies/${id}/backtest`, config);
}

export async function getBacktestResults(id: string, runId: string) {
  return get(`/strategies/${id}/backtest/${runId}`);
}

export async function deployStrategy(id: string) {
  return post(`/strategies/${id}/deploy`, {});
}

// P2: Strategy control endpoints
export async function enableStrategy(id: string) {
  return post(`/strategies/${id}/enable`, {});
}

export async function disableStrategy(id: string) {
  return post(`/strategies/${id}/disable`, {});
}

export async function emergencyHalt(): Promise<{ halted: number; strategy_ids: string[] }> {
  return post('/halt', {}) as Promise<{ halted: number; strategy_ids: string[] }>;
}

// Signal statistics endpoints
export interface SignalStatistics {
  [signalName: string]: {
    count: number;
    percentage: number;
    total_candles: number;
  };
}

export async function getSignalStatistics(blockName: string, signalNames: string[]) {
  return post<SignalStatistics>(`/blocks/${blockName}/signal-statistics`, {
    signal_names: signalNames,
  });
}

// Filter presets - using localStorage
export interface FilterPreset {
  name: string;
  searchText: string;
  category: string;
  blockType: string;
}

export function saveFilterPreset(preset: FilterPreset): void {
  if (typeof window === 'undefined') return;
  const presets = loadAllFilterPresets();
  const index = presets.findIndex((p) => p.name === preset.name);
  if (index >= 0) {
    presets[index] = preset;
  } else {
    presets.push(preset);
  }
  localStorage.setItem('block_search_presets', JSON.stringify(presets));
}

export function loadAllFilterPresets(): FilterPreset[] {
  if (typeof window === 'undefined') return [];
  const stored = localStorage.getItem('block_search_presets');
  return stored ? JSON.parse(stored) : [];
}

export function deleteFilterPreset(name: string): void {
  if (typeof window === 'undefined') return;
  const presets = loadAllFilterPresets();
  localStorage.setItem(
    'block_search_presets',
    JSON.stringify(presets.filter((p) => p.name !== name))
  );
}

// Strategy version management
export async function getStrategyVersions(strategyId: string) {
  return get(`${SB}/${strategyId}/versions`);
}

export async function loadStrategyVersion(strategyId: string, versionId: string) {
  return get(`${SB}/${strategyId}/versions/${versionId}`);
}

export async function restoreStrategyVersion(strategyId: string, _versionId: string) {
  throw new Error('Version restore not yet implemented');
}
