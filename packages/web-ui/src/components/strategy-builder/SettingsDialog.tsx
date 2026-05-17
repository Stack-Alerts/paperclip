'use client';

import React, { useState, useCallback } from 'react';
import { X, Eye, EyeOff, Shield, ShieldAlert } from 'lucide-react';
import { AdminPinDialog } from './AdminPinDialog';

export interface SettingsDialogProps {
  open: boolean;
  onClose: () => void;
}

type Tab = 'api' | 'trading' | 'display' | 'admin';

const TABS: { id: Tab; label: string }[] = [
  { id: 'api', label: 'API Keys' },
  { id: 'trading', label: 'Trading' },
  { id: 'display', label: 'Display' },
  { id: 'admin', label: 'Admin' },
];

const PROVIDER_OPTIONS = ['anthropic', 'openai', 'openrouter', 'deepseek', 'ollama'];
const PROVIDER_MODELS: Record<string, string[]> = {
  anthropic: ['claude-sonnet-4-6', 'claude-opus-4-1', 'claude-haiku-3-5'],
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4.1'],
  openrouter: ['anthropic/claude-4.5-sonnet', 'openai/gpt-4o', 'deepseek/deepseek-chat-v4'],
  deepseek: ['deepseek-chat', 'deepseek-reasoner'],
  ollama: ['llama3', 'mistral', 'codellama'],
};

function maskStored(storageKey: string): string {
  if (typeof window === 'undefined') return '';
  const stored = localStorage.getItem(storageKey);
  return stored ? `${'•'.repeat(Math.min(stored.length, 20))}` : '';
}

function SecretField({ label, storageKey }: { label: string; storageKey: string }) {
  const [value, setValue] = useState(() => maskStored(storageKey));
  const [prevStorageKey, setPrevStorageKey] = useState(storageKey);
  const [showing, setShowing] = useState(false);
  const [editing, setEditing] = useState(false);

  if (prevStorageKey !== storageKey) {
    setPrevStorageKey(storageKey);
    setValue(maskStored(storageKey));
  }

  const handleSave = useCallback(() => {
    if (value && !value.startsWith('•')) {
      localStorage.setItem(storageKey, value);
    }
    setEditing(false);
    setShowing(false);
  }, [value, storageKey]);

  const handleShow = useCallback(() => {
    const stored = localStorage.getItem(storageKey) ?? '';
    setValue(stored);
    setShowing(true);
    setTimeout(() => {
      setShowing(false);
      setValue(stored ? `${'•'.repeat(Math.min(stored.length, 20))}` : '');
    }, 10000);
  }, [storageKey]);

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 space-y-1">
        <label className="text-xs font-medium text-zinc-400">{label}</label>
        <input
          type={showing || editing ? 'text' : 'password'}
          value={value}
          readOnly={!editing}
          onChange={(e) => setValue(e.target.value)}
          placeholder={editing ? 'Enter new value…' : 'Not set'}
          className="w-full rounded bg-zinc-800 border border-zinc-700 px-3 py-1.5 text-sm text-zinc-100 focus:outline-none focus:border-blue-500 font-mono"
        />
      </div>
      {!editing ? (
        <>
          <button
            onClick={handleShow}
            title="Reveal for 10s"
            className="mt-5 p-1.5 rounded bg-zinc-700 hover:bg-zinc-600 text-zinc-400 hover:text-zinc-100 transition-colors"
          >
            {showing ? <EyeOff size={13} /> : <Eye size={13} />}
          </button>
          <button
            onClick={() => { setEditing(true); setValue(''); }}
            className="mt-5 px-2 py-1.5 rounded bg-zinc-700 hover:bg-zinc-600 text-xs text-zinc-300 transition-colors"
          >
            Edit
          </button>
        </>
      ) : (
        <>
          <button
            onClick={handleSave}
            className="mt-5 px-2 py-1.5 rounded bg-blue-600 hover:bg-blue-700 text-xs text-white transition-colors"
          >
            Save
          </button>
          <button
            onClick={() => { setEditing(false); setValue(''); }}
            className="mt-5 px-2 py-1.5 rounded bg-zinc-700 hover:bg-zinc-600 text-xs text-zinc-300 transition-colors"
          >
            Cancel
          </button>
        </>
      )}
    </div>
  );
}

function ApiTab() {
  const [provider, setProvider] = useState('anthropic');
  const [model, setModel] = useState(PROVIDER_MODELS.anthropic[0]);

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <div className="space-y-1">
          <label className="text-xs font-medium text-zinc-400">LLM Provider</label>
          <select
            value={provider}
            onChange={(e) => { setProvider(e.target.value); setModel(PROVIDER_MODELS[e.target.value]?.[0] ?? ''); }}
            className="w-full rounded bg-zinc-800 border border-zinc-700 px-3 py-1.5 text-sm text-zinc-100 focus:outline-none focus:border-blue-500"
          >
            {PROVIDER_OPTIONS.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium text-zinc-400">Model</label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="w-full rounded bg-zinc-800 border border-zinc-700 px-3 py-1.5 text-sm text-zinc-100 focus:outline-none focus:border-blue-500"
          >
            {(PROVIDER_MODELS[provider] ?? []).map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
      </div>
      <div className="border-t border-zinc-800 pt-4 space-y-4">
        <h3 className="text-xs font-semibold text-zinc-300 uppercase tracking-wide">API Keys</h3>
        <SecretField label="Anthropic API Key" storageKey="settings.anthropic_api_key" />
        <SecretField label="OpenAI API Key" storageKey="settings.openai_api_key" />
        <SecretField label="OpenRouter API Key" storageKey="settings.openrouter_api_key" />
        <SecretField label="Binance API Key" storageKey="settings.binance_api_key" />
        <SecretField label="Binance API Secret" storageKey="settings.binance_api_secret" />
      </div>
    </div>
  );
}

function TradingTab() {
  const [riskPct, setRiskPct] = useState('1.0');
  const [maxDrawdown, setMaxDrawdown] = useState('10.0');
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [exchange, setExchange] = useState('binance');

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        {[
          { label: 'Symbol', value: symbol, set: setSymbol },
          { label: 'Exchange', value: exchange, set: setExchange },
          { label: 'Risk % per Trade', value: riskPct, set: setRiskPct },
          { label: 'Max Drawdown %', value: maxDrawdown, set: setMaxDrawdown },
        ].map(({ label, value, set }) => (
          <div key={label} className="space-y-1">
            <label className="text-xs font-medium text-zinc-400">{label}</label>
            <input
              value={value}
              onChange={(e) => set(e.target.value)}
              className="w-full rounded bg-zinc-800 border border-zinc-700 px-3 py-1.5 text-sm text-zinc-100 focus:outline-none focus:border-blue-500"
            />
          </div>
        ))}
      </div>
    </div>
  );
}

function DisplayTab() {
  const [theme, setTheme] = useState('dark');
  const [logLevel, setLogLevel] = useState('INFO');

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <label className="text-xs font-medium text-zinc-400">Theme</label>
        <select
          value={theme}
          onChange={(e) => setTheme(e.target.value)}
          className="w-full rounded bg-zinc-800 border border-zinc-700 px-3 py-1.5 text-sm text-zinc-100 focus:outline-none focus:border-blue-500"
        >
          <option value="dark">Dark (default)</option>
          <option value="light">Light</option>
        </select>
      </div>
      <div className="space-y-1">
        <label className="text-xs font-medium text-zinc-400">Log Level</label>
        <select
          value={logLevel}
          onChange={(e) => setLogLevel(e.target.value)}
          className="w-full rounded bg-zinc-800 border border-zinc-700 px-3 py-1.5 text-sm text-zinc-100 focus:outline-none focus:border-blue-500"
        >
          {['DEBUG', 'INFO', 'WARNING', 'ERROR'].map((l) => <option key={l} value={l}>{l}</option>)}
        </select>
      </div>
    </div>
  );
}

function AdminTab({ unlocked }: { unlocked: boolean }) {
  if (!unlocked) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-3 text-zinc-500">
        <ShieldAlert size={32} />
        <p className="text-sm">Admin section locked. Verify PIN to access.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-emerald-400 text-xs font-medium mb-2">
        <Shield size={13} /> Admin access granted
      </div>
      <SecretField label="Database URL" storageKey="admin.db_url" />
      <SecretField label="Redis URL" storageKey="admin.redis_url" />
      <SecretField label="Nautilus API Key" storageKey="admin.nautilus_api_key" />
    </div>
  );
}

export const SettingsDialog: React.FC<SettingsDialogProps> = ({ open, onClose }) => {
  const [activeTab, setActiveTab] = useState<Tab>('api');
  const [adminUnlocked, setAdminUnlocked] = useState(false);
  const [pinDialogOpen, setPinDialogOpen] = useState(false);

  const handleTabClick = useCallback((tab: Tab) => {
    if (tab === 'admin' && !adminUnlocked) {
      setPinDialogOpen(true);
      return;
    }
    setActiveTab(tab);
  }, [adminUnlocked]);

  const handlePinSuccess = useCallback(() => {
    setPinDialogOpen(false);
    setAdminUnlocked(true);
    setActiveTab('admin');
  }, []);

  if (!open) return null;

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
        <div className="bg-zinc-900 border border-zinc-700 rounded-xl shadow-2xl w-full max-w-2xl mx-4 flex flex-col max-h-[85vh]">
          <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 flex-shrink-0">
            <h2 className="text-base font-semibold text-zinc-100">Settings</h2>
            <button onClick={onClose} className="text-zinc-500 hover:text-zinc-200 transition-colors">
              <X size={16} />
            </button>
          </div>

          <div className="flex border-b border-zinc-800 flex-shrink-0">
            {TABS.map(({ id, label }) => (
              <button
                key={id}
                onClick={() => handleTabClick(id)}
                className={[
                  'px-5 py-2.5 text-xs font-medium transition-colors',
                  activeTab === id
                    ? 'text-blue-400 border-b-2 border-blue-500 -mb-px'
                    : 'text-zinc-400 hover:text-zinc-200',
                ].join(' ')}
              >
                {id === 'admin' && !adminUnlocked ? `🔒 ${label}` : label}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-auto p-6">
            {activeTab === 'api' && <ApiTab />}
            {activeTab === 'trading' && <TradingTab />}
            {activeTab === 'display' && <DisplayTab />}
            {activeTab === 'admin' && <AdminTab unlocked={adminUnlocked} />}
          </div>

          <div className="flex justify-end gap-2 px-6 py-4 border-t border-zinc-800 flex-shrink-0">
            <button
              onClick={onClose}
              className="px-5 py-2 rounded-lg bg-zinc-700 hover:bg-zinc-600 text-zinc-200 text-sm font-medium transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>

      <AdminPinDialog
        open={pinDialogOpen}
        onSuccess={handlePinSuccess}
        onCancel={() => setPinDialogOpen(false)}
      />
    </>
  );
};

export default SettingsDialog;
