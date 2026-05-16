// Typed fetch wrapper for REST endpoints
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

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
