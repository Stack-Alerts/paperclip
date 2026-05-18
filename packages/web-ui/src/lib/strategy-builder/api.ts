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

export interface CreateStrategyRequest {
  name: string;
  description?: string;
}

export async function createStrategy(data: CreateStrategyRequest) {
  return post('/strategies', data);
}

export async function listStrategies() {
  return get('/strategies');
}

export async function getStrategy(id: string) {
  return get(`/strategies/${id}`);
}

export async function updateStrategy(id: string, data: unknown) {
  return put(`/strategies/${id}`, data);
}

export async function deleteStrategy(id: string) {
  return del(`/strategies/${id}`);
}

export async function deleteStrategyScoped(
  id: string,
  scope: 'entire' | 'version',
  versionIds?: string[],
) {
  if (scope === 'version' && versionIds?.length) {
    return post(`/strategies/${id}/versions/delete`, { version_ids: versionIds });
  }
  return del(`/strategies/${id}`);
}

export async function duplicateStrategyScoped(
  id: string,
  scope: 'version' | 'strategy',
  newName?: string,
) {
  return post(`/strategies/${id}/duplicate`, { scope, name: newName });
}

export async function getBlockLibrary() {
  return get('/blocks');
}

export async function getBlockSchema(blockType: string) {
  return get(`/blocks/${blockType}`);
}

export async function validateStrategy(id: string, strategyData: unknown) {
  return post(`/strategies/${id}/validate`, strategyData);
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

// Strategy version management (P2-backend)
// TODO(P2-backend): Implement GET /strategies/{id}/versions endpoint
export async function getStrategyVersions(strategyId: string) {
  try {
    // Placeholder: Returns empty array until backend endpoint is implemented
    // When backend is ready, uncomment:
    // return get(`/strategies/${strategyId}/versions`);
    return [];
  } catch {
    return [];
  }
}

// TODO(P2-backend): Implement GET /strategies/{id}/versions/{versionId} endpoint
export async function loadStrategyVersion(strategyId: string, versionId: string) {
  try {
    // Placeholder: Until backend endpoint is implemented
    // When backend is ready, uncomment:
    // return get(`/strategies/${strategyId}/versions/${versionId}`);
    throw new Error('Version history API not yet implemented');
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to load strategy version';
    throw new Error(message);
  }
}

// TODO(P2-backend): Implement POST /strategies/{id}/versions/{versionId}/restore endpoint
export async function restoreStrategyVersion(strategyId: string, versionId: string) {
  try {
    // Placeholder: Until backend endpoint is implemented
    // When backend is ready, uncomment:
    // return post(`/strategies/${strategyId}/versions/${versionId}/restore`, {});
    throw new Error('Version restore API not yet implemented');
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to restore strategy version';
    throw new Error(message);
  }
}
