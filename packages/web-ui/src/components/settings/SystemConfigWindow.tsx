'use client';

import React, { useState } from 'react';
import { X, Save, RotateCcw } from 'lucide-react';

export interface SystemConfigWindowProps {
  open?: boolean;
  onClose?: () => void;
}

type ConfigTab = 'block' | 'signal' | 'market' | 'system' | 'security' | 'monitoring';

const CONFIG_TABS: { id: ConfigTab; label: string }[] = [
  { id: 'block', label: 'Block Optimization' },
  { id: 'signal', label: 'Signal Logic' },
  { id: 'market', label: 'Market Conditions' },
  { id: 'system', label: 'System Integration' },
  { id: 'security', label: 'Security' },
  { id: 'monitoring', label: 'Monitoring' },
];

function FormRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-4">
      <label className="w-48 text-sm text-zinc-400 flex-shrink-0">{label}</label>
      <div className="flex-1">{children}</div>
    </div>
  );
}

function NumberInput({ value, onChange, min, max }: { value: number; onChange: (v: number) => void; min?: number; max?: number }) {
  return (
    <input
      type="number"
      value={value}
      min={min}
      max={max}
      onChange={(e) => onChange(Number(e.target.value))}
      className="w-32 bg-zinc-800 border border-zinc-700 rounded px-3 py-1.5 text-sm text-zinc-100 focus:outline-none focus:border-blue-500"
    />
  );
}

function Toggle({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!value)}
      className={`relative w-10 h-5 rounded-full transition-colors ${value ? 'bg-blue-600' : 'bg-zinc-700'}`}
    >
      <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${value ? 'translate-x-5' : 'translate-x-0.5'}`} />
    </button>
  );
}

interface Config {
  block: { maxBlocks: number; minConfidence: number; enableAutoFix: boolean };
  signal: { requireConfirmation: boolean; confirmationBars: number; minSignalStrength: number };
  market: { enableRegimeDetection: boolean; trendThreshold: number; volatilityWindow: number };
  system: { apiUrl: string; timeout: number; maxRetries: number };
  security: { adminPin: string; sessionTimeout: number; enforcePin: boolean };
  monitoring: { enableAlerts: boolean; alertThreshold: number; logRetentionDays: number };
}

const DEFAULT_CONFIG: Config = {
  block: { maxBlocks: 10, minConfidence: 0.6, enableAutoFix: true },
  signal: { requireConfirmation: false, confirmationBars: 1, minSignalStrength: 0.5 },
  market: { enableRegimeDetection: true, trendThreshold: 0.3, volatilityWindow: 20 },
  system: { apiUrl: 'http://localhost:8000', timeout: 30, maxRetries: 3 },
  security: { adminPin: '', sessionTimeout: 3600, enforcePin: false },
  monitoring: { enableAlerts: true, alertThreshold: 0.05, logRetentionDays: 30 },
};

function TabContent({ tab, config, setConfig }: { tab: ConfigTab; config: Config; setConfig: React.Dispatch<React.SetStateAction<Config>> }) {
  switch (tab) {
    case 'block':
      return (
        <div className="space-y-4">
          <FormRow label="Max Blocks">
            <NumberInput value={config.block.maxBlocks} min={1} max={50} onChange={(v) => setConfig((c) => ({ ...c, block: { ...c.block, maxBlocks: v } }))} />
          </FormRow>
          <FormRow label="Min Confidence">
            <NumberInput value={config.block.minConfidence} min={0} max={1} onChange={(v) => setConfig((c) => ({ ...c, block: { ...c.block, minConfidence: v } }))} />
          </FormRow>
          <FormRow label="Enable Auto-Fix">
            <Toggle value={config.block.enableAutoFix} onChange={(v) => setConfig((c) => ({ ...c, block: { ...c.block, enableAutoFix: v } }))} />
          </FormRow>
        </div>
      );
    case 'signal':
      return (
        <div className="space-y-4">
          <FormRow label="Require Confirmation">
            <Toggle value={config.signal.requireConfirmation} onChange={(v) => setConfig((c) => ({ ...c, signal: { ...c.signal, requireConfirmation: v } }))} />
          </FormRow>
          <FormRow label="Confirmation Bars">
            <NumberInput value={config.signal.confirmationBars} min={1} max={10} onChange={(v) => setConfig((c) => ({ ...c, signal: { ...c.signal, confirmationBars: v } }))} />
          </FormRow>
          <FormRow label="Min Signal Strength">
            <NumberInput value={config.signal.minSignalStrength} min={0} max={1} onChange={(v) => setConfig((c) => ({ ...c, signal: { ...c.signal, minSignalStrength: v } }))} />
          </FormRow>
        </div>
      );
    case 'market':
      return (
        <div className="space-y-4">
          <FormRow label="Enable Regime Detection">
            <Toggle value={config.market.enableRegimeDetection} onChange={(v) => setConfig((c) => ({ ...c, market: { ...c.market, enableRegimeDetection: v } }))} />
          </FormRow>
          <FormRow label="Trend Threshold">
            <NumberInput value={config.market.trendThreshold} min={0} max={1} onChange={(v) => setConfig((c) => ({ ...c, market: { ...c.market, trendThreshold: v } }))} />
          </FormRow>
          <FormRow label="Volatility Window">
            <NumberInput value={config.market.volatilityWindow} min={5} max={200} onChange={(v) => setConfig((c) => ({ ...c, market: { ...c.market, volatilityWindow: v } }))} />
          </FormRow>
        </div>
      );
    case 'system':
      return (
        <div className="space-y-4">
          <FormRow label="API URL">
            <input
              type="text"
              value={config.system.apiUrl}
              onChange={(e) => setConfig((c) => ({ ...c, system: { ...c.system, apiUrl: e.target.value } }))}
              className="w-64 bg-zinc-800 border border-zinc-700 rounded px-3 py-1.5 text-sm text-zinc-100 focus:outline-none focus:border-blue-500"
            />
          </FormRow>
          <FormRow label="Timeout (s)">
            <NumberInput value={config.system.timeout} min={5} max={300} onChange={(v) => setConfig((c) => ({ ...c, system: { ...c.system, timeout: v } }))} />
          </FormRow>
          <FormRow label="Max Retries">
            <NumberInput value={config.system.maxRetries} min={0} max={10} onChange={(v) => setConfig((c) => ({ ...c, system: { ...c.system, maxRetries: v } }))} />
          </FormRow>
        </div>
      );
    case 'security':
      return (
        <div className="space-y-4">
          <FormRow label="Enforce Admin PIN">
            <Toggle value={config.security.enforcePin} onChange={(v) => setConfig((c) => ({ ...c, security: { ...c.security, enforcePin: v } }))} />
          </FormRow>
          <FormRow label="Session Timeout (s)">
            <NumberInput value={config.security.sessionTimeout} min={300} max={86400} onChange={(v) => setConfig((c) => ({ ...c, security: { ...c.security, sessionTimeout: v } }))} />
          </FormRow>
        </div>
      );
    case 'monitoring':
      return (
        <div className="space-y-4">
          <FormRow label="Enable Alerts">
            <Toggle value={config.monitoring.enableAlerts} onChange={(v) => setConfig((c) => ({ ...c, monitoring: { ...c.monitoring, enableAlerts: v } }))} />
          </FormRow>
          <FormRow label="Alert Threshold">
            <NumberInput value={config.monitoring.alertThreshold} min={0} max={1} onChange={(v) => setConfig((c) => ({ ...c, monitoring: { ...c.monitoring, alertThreshold: v } }))} />
          </FormRow>
          <FormRow label="Log Retention (days)">
            <NumberInput value={config.monitoring.logRetentionDays} min={1} max={365} onChange={(v) => setConfig((c) => ({ ...c, monitoring: { ...c.monitoring, logRetentionDays: v } }))} />
          </FormRow>
        </div>
      );
  }
}

export function SystemConfigWindow({ open, onClose }: SystemConfigWindowProps) {
  const [activeTab, setActiveTab] = useState<ConfigTab>('block');
  const [config, setConfig] = useState<Config>(DEFAULT_CONFIG);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
    onClose?.();
  };

  const handleReset = () => setConfig(DEFAULT_CONFIG);

  if (open === false) return null;

  const content = (
    <div className="flex flex-col h-full bg-zinc-900 text-zinc-100">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 flex-shrink-0">
        <h1 className="text-base font-semibold text-zinc-100">System Configuration</h1>
        {onClose && (
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-200 transition-colors" aria-label="Close">
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar tabs */}
        <div className="w-44 border-r border-zinc-800 flex flex-col py-2 flex-shrink-0">
          {CONFIG_TABS.map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`text-left px-4 py-2.5 text-sm transition-colors ${
                activeTab === id
                  ? 'bg-blue-600/20 text-blue-400 border-r-2 border-blue-500'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto p-6">
          <TabContent tab={activeTab} config={config} setConfig={setConfig} />
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-zinc-800 flex-shrink-0">
        <button
          onClick={handleReset}
          className="flex items-center gap-2 px-4 py-2 rounded bg-zinc-700 text-zinc-200 text-sm hover:bg-zinc-600 transition-colors"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Reset to Defaults
        </button>
        <button
          onClick={handleSave}
          className="flex items-center gap-2 px-4 py-2 rounded bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          <Save className="w-3.5 h-3.5" />
          {saved ? 'Saved!' : 'Save Configuration'}
        </button>
      </div>
    </div>
  );

  if (onClose) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        <div className="absolute inset-0 bg-black/60" onClick={onClose} />
        <div className="relative w-full max-w-3xl h-[80vh] bg-zinc-900 border border-zinc-700 rounded-xl shadow-2xl mx-4 overflow-hidden">
          {content}
        </div>
      </div>
    );
  }

  return <div className="h-full">{content}</div>;
}
