'use client';

import { useCallback, useEffect, useState } from 'react';

export type AiProvider =
  | 'claude-code'
  | 'anthropic'
  | 'openai'
  | 'openrouter'
  | 'deepseek'
  | 'ollama';

export interface AiProviderMeta {
  id: AiProvider;
  label: string;
  /** Whether this provider authenticates with an API key the user must supply. */
  requiresApiKey: boolean;
  /** Short cost/usage note shown under the provider selector. */
  info: string;
  /** Curated model list (editable — users may type their own). */
  models: string[];
  defaultModel: string;
}

// Full Claude model lineup, shared by the local Claude Code CLI and the
// Anthropic API providers so every available model is selectable.
export const CLAUDE_MODELS = [
  'claude-opus-4-7',
  'claude-opus-4-1',
  'claude-sonnet-4-6',
  'claude-haiku-4-5',
  'claude-haiku-3-5',
];

// Mirrors the desktop (PyQt) Settings dialog provider catalog in
// src/strategy_builder/ui/settings_dialog.py, plus the local Claude Code CLI
// option requested on BTCAAAAA-36340.
export const AI_PROVIDERS: AiProviderMeta[] = [
  {
    id: 'claude-code',
    label: 'Claude Code (local CLI subscription)',
    requiresApiKey: false,
    info: 'Runs locally through your Claude Code CLI session — no API key required. Uses your existing Claude Code / Claude subscription.',
    models: CLAUDE_MODELS,
    defaultModel: 'claude-sonnet-4-6',
  },
  {
    id: 'anthropic',
    label: 'Anthropic API',
    requiresApiKey: true,
    info: 'Default pricing: $3.00/M input · $15.00/M output',
    models: CLAUDE_MODELS,
    defaultModel: 'claude-sonnet-4-6',
  },
  {
    id: 'openrouter',
    label: 'OpenRouter',
    requiresApiKey: true,
    info: 'Aggregates multiple providers via the OpenRouter API.',
    models: [
      'anthropic/claude-4.5-sonnet',
      'anthropic/claude-opus-4-1',
      'openai/gpt-4o',
      'deepseek/deepseek-chat-v4',
      'deepseek/deepseek-r1',
    ],
    defaultModel: 'anthropic/claude-4.5-sonnet',
  },
  {
    id: 'openai',
    label: 'OpenAI',
    requiresApiKey: true,
    info: 'Default pricing: $5.00/M input · $15.00/M output',
    models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4.1'],
    defaultModel: 'gpt-4o',
  },
  {
    id: 'deepseek',
    label: 'DeepSeek',
    requiresApiKey: true,
    info: 'Cost varies — see the DeepSeek pricing page.',
    models: ['deepseek-chat', 'deepseek-reasoner'],
    defaultModel: 'deepseek-chat',
  },
  {
    id: 'ollama',
    label: 'Ollama (local)',
    requiresApiKey: false,
    info: 'Free local inference. Set the base URL of your Ollama server.',
    models: ['llama3.1', 'qwen2.5', 'mistral'],
    defaultModel: 'llama3.1',
  },
];

export function getProviderMeta(provider: AiProvider): AiProviderMeta {
  return AI_PROVIDERS.find((p) => p.id === provider) ?? AI_PROVIDERS[0];
}

export interface AiSettings {
  provider: AiProvider;
  model: string;
  /** API keys kept per-provider so switching providers does not lose them. */
  apiKeys: Partial<Record<AiProvider, string>>;
  /** Base URL for the Ollama local server. */
  ollamaBaseUrl: string;
}

export const DEFAULT_AI_SETTINGS: AiSettings = {
  provider: 'claude-code',
  model: 'claude-sonnet-4-6',
  apiKeys: {},
  ollamaBaseUrl: 'http://localhost:11434',
};

const STORAGE_KEY = 'ai-recommendation-settings';

function loadStored(): AiSettings {
  if (typeof window === 'undefined') return DEFAULT_AI_SETTINGS;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_AI_SETTINGS;
    const parsed = JSON.parse(raw) as Partial<AiSettings>;
    return {
      ...DEFAULT_AI_SETTINGS,
      ...parsed,
      apiKeys: { ...DEFAULT_AI_SETTINGS.apiKeys, ...(parsed.apiKeys ?? {}) },
    };
  } catch {
    return DEFAULT_AI_SETTINGS;
  }
}

/**
 * localStorage-backed AI recommendation settings (provider / model / key).
 *
 * NOTE: localStorage is not a secure secret store. The desktop client keeps
 * provider API keys in the OS keyring; moving web key persistence server-side
 * is tracked as backend follow-up (see BTCAAAAA-36340 closure comment).
 */
export function useAiSettings() {
  const [settings, setSettings] = useState<AiSettings>(DEFAULT_AI_SETTINGS);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSettings(loadStored());
    setHydrated(true);
  }, []);

  const save = useCallback((next: AiSettings) => {
    setSettings(next);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    }
  }, []);

  return { settings, save, hydrated };
}
