import {
  testAiConnection,
  type ConnectionTestConfig,
  type ConnectionTestResult,
} from '../../app/api/ai/test-connection/tester';

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

const okClaude = async (model: string): Promise<ConnectionTestResult> => ({
  ok: true,
  message: `Claude Code responded using ${model}.`,
});

function deps(fetchImpl: jest.Mock) {
  return {
    fetch: fetchImpl as unknown as typeof fetch,
    runClaudeCli: okClaude,
    timeoutMs: 1000,
  };
}

describe('testAiConnection', () => {
  it('rejects an empty model before any network call', async () => {
    const fetchMock = jest.fn();
    const cfg: ConnectionTestConfig = { provider: 'anthropic', model: '   ', apiKey: 'k' };
    const result = await testAiConnection(cfg, deps(fetchMock));
    expect(result.ok).toBe(false);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('requires an API key for key-based providers', async () => {
    const fetchMock = jest.fn();
    const cfg: ConnectionTestConfig = { provider: 'openai', model: 'gpt-4o' };
    const result = await testAiConnection(cfg, deps(fetchMock));
    expect(result.ok).toBe(false);
    expect(result.message).toMatch(/API key/i);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('reports success for an Anthropic 200', async () => {
    const fetchMock = jest.fn().mockResolvedValue(makeResponse(200, { id: 'msg_1' }));
    const cfg: ConnectionTestConfig = {
      provider: 'anthropic',
      model: 'claude-sonnet-4-6',
      apiKey: 'sk-ant',
    };
    const result = await testAiConnection(cfg, deps(fetchMock));
    expect(result.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.anthropic.com/v1/messages',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('surfaces the provider error message on a 401', async () => {
    const fetchMock = jest
      .fn()
      .mockResolvedValue(makeResponse(401, { error: { message: 'invalid x-api-key' } }));
    const cfg: ConnectionTestConfig = {
      provider: 'anthropic',
      model: 'claude-sonnet-4-6',
      apiKey: 'bad',
    };
    const result = await testAiConnection(cfg, deps(fetchMock));
    expect(result.ok).toBe(false);
    expect(result.detail).toBe('invalid x-api-key');
  });

  it('hits the OpenAI-compatible endpoint for deepseek', async () => {
    const fetchMock = jest.fn().mockResolvedValue(makeResponse(200, {}));
    const cfg: ConnectionTestConfig = {
      provider: 'deepseek',
      model: 'deepseek-chat',
      apiKey: 'dk',
    };
    const result = await testAiConnection(cfg, deps(fetchMock));
    expect(result.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.deepseek.com/chat/completions',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('confirms an installed Ollama model (tag-stripped match)', async () => {
    const fetchMock = jest
      .fn()
      .mockResolvedValue(makeResponse(200, { models: [{ name: 'llama3.1:latest' }] }));
    const cfg: ConnectionTestConfig = {
      provider: 'ollama',
      model: 'llama3.1',
      ollamaBaseUrl: 'http://localhost:11434',
    };
    const result = await testAiConnection(cfg, deps(fetchMock));
    expect(result.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:11434/api/tags',
      expect.objectContaining({ method: 'GET' }),
    );
  });

  it('fails when the Ollama model is not installed', async () => {
    const fetchMock = jest
      .fn()
      .mockResolvedValue(makeResponse(200, { models: [{ name: 'mistral:latest' }] }));
    const cfg: ConnectionTestConfig = {
      provider: 'ollama',
      model: 'llama3.1',
      ollamaBaseUrl: 'http://localhost:11434',
    };
    const result = await testAiConnection(cfg, deps(fetchMock));
    expect(result.ok).toBe(false);
    expect(result.detail).toMatch(/mistral/);
  });

  it('reports an unreachable Ollama server', async () => {
    const fetchMock = jest.fn().mockRejectedValue(new Error('ECONNREFUSED'));
    const cfg: ConnectionTestConfig = {
      provider: 'ollama',
      model: 'llama3.1',
      ollamaBaseUrl: 'http://localhost:11434',
    };
    const result = await testAiConnection(cfg, deps(fetchMock));
    expect(result.ok).toBe(false);
    expect(result.message).toMatch(/could not reach/i);
  });

  it('delegates claude-code to the CLI runner without fetch', async () => {
    const fetchMock = jest.fn();
    const cfg: ConnectionTestConfig = { provider: 'claude-code', model: 'claude-sonnet-4-6' };
    const result = await testAiConnection(cfg, deps(fetchMock));
    expect(result.ok).toBe(true);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('converts a thrown fetch into a failed result', async () => {
    const fetchMock = jest.fn().mockRejectedValue(new Error('boom'));
    const cfg: ConnectionTestConfig = {
      provider: 'openai',
      model: 'gpt-4o',
      apiKey: 'k',
    };
    const result = await testAiConnection(cfg, deps(fetchMock));
    expect(result.ok).toBe(false);
    expect(result.detail).toBe('boom');
  });
});
