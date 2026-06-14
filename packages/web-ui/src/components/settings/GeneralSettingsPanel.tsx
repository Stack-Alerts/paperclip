'use client';

import React, { useEffect, useState } from 'react';
import {
  AI_PROVIDERS,
  AiProvider,
  AiSettings,
  DEFAULT_AI_SETTINGS,
  getProviderMeta,
  useAiSettings,
} from '@/hooks/useAiSettings';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';

/**
 * GeneralSettingsPanel — web port of the AI Configuration / API Keys sections
 * of the desktop Settings dialog (src/strategy_builder/ui/settings_dialog.py).
 *
 * Lets the user choose the AI provider used by the recommendation system,
 * pick a model, and supply the API key for providers that require one. The
 * Claude Code (CLI subscription) option needs no key, addressing the request
 * on BTCAAAAA-36340.
 */
export const GeneralSettingsPanel: React.FC = () => {
  const { settings, save, hydrated } = useAiSettings();
  const [draft, setDraft] = useState<AiSettings>(settings);
  const [hasChanges, setHasChanges] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDraft(settings);
    setHasChanges(false);
  }, [settings]);

  const meta = getProviderMeta(draft.provider);

  const update = (patch: Partial<AiSettings>) => {
    setDraft((prev) => ({ ...prev, ...patch }));
    setHasChanges(true);
    setSaved(false);
  };

  const handleProviderChange = (provider: AiProvider) => {
    const nextMeta = getProviderMeta(provider);
    // Default the model to the new provider's default unless the current model
    // is already valid for it.
    const model = nextMeta.models.includes(draft.model)
      ? draft.model
      : nextMeta.defaultModel;
    update({ provider, model });
  };

  const handleApiKeyChange = (value: string) => {
    update({ apiKeys: { ...draft.apiKeys, [draft.provider]: value } });
  };

  const handleSave = () => {
    save(draft);
    setHasChanges(false);
    setSaved(true);
  };

  const handleReset = () => {
    setDraft(settings);
    setHasChanges(false);
    setSaved(false);
  };

  const handleRestoreDefaults = () => {
    setDraft(DEFAULT_AI_SETTINGS);
    setHasChanges(true);
    setSaved(false);
  };

  const currentKey = draft.apiKeys[draft.provider] ?? '';

  return (
    <Card>
      <CardHeader>
        <CardTitle>AI Recommendations</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
          Choose the AI provider that powers the recommendation system. Some
          providers use a paid API key; Claude Code uses your local CLI
          subscription and needs no key.
        </p>

        {/* Provider */}
        <div className="space-y-2">
          <Label htmlFor="ai-provider">AI Provider</Label>
          <Select
            id="ai-provider"
            value={draft.provider}
            onChange={(e) => handleProviderChange(e.target.value as AiProvider)}
            disabled={!hydrated}
          >
            {AI_PROVIDERS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </Select>
          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
            {meta.info}
          </p>
        </div>

        {/* Model */}
        <div className="space-y-2">
          <Label htmlFor="ai-model">Model</Label>
          <Input
            id="ai-model"
            type="text"
            list="ai-model-options"
            value={draft.model}
            onChange={(e) => update({ model: e.target.value })}
            disabled={!hydrated}
            placeholder={meta.defaultModel}
          />
          <datalist id="ai-model-options">
            {meta.models.map((m) => (
              <option key={m} value={m} />
            ))}
          </datalist>
          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
            Pick a suggested model or type a custom one.
          </p>
        </div>

        {/* API key (only for providers that need one) */}
        {meta.requiresApiKey && (
          <div className="space-y-2">
            <Label htmlFor="ai-api-key">API Key</Label>
            <Input
              id="ai-api-key"
              type="password"
              value={currentKey}
              onChange={(e) => handleApiKeyChange(e.target.value)}
              disabled={!hydrated}
              placeholder="••••••••"
              autoComplete="off"
            />
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
              Stored locally in your browser. Do not use a shared computer for
              production keys — secure server-side storage is a planned
              follow-up.
            </p>
          </div>
        )}

        {/* Ollama base URL */}
        {draft.provider === 'ollama' && (
          <div className="space-y-2">
            <Label htmlFor="ollama-url">Ollama Base URL</Label>
            <Input
              id="ollama-url"
              type="text"
              value={draft.ollamaBaseUrl}
              onChange={(e) => update({ ollamaBaseUrl: e.target.value })}
              disabled={!hydrated}
              placeholder="http://localhost:11434"
            />
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2 justify-end pt-4 border-t" style={{ borderTopColor: 'var(--border-subtle)' }}>
          {saved && (
            <span className="text-xs mr-auto" style={{ color: 'var(--text-secondary)' }}>
              Settings saved.
            </span>
          )}
          <Button variant="secondary" onClick={handleRestoreDefaults} disabled={!hydrated}>
            Restore Defaults
          </Button>
          <Button variant="secondary" onClick={handleReset} disabled={!hydrated || !hasChanges}>
            Reset
          </Button>
          <Button onClick={handleSave} disabled={!hydrated || !hasChanges}>
            Save Settings
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default GeneralSettingsPanel;
