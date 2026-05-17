'use client';

import React, { useState, useCallback } from 'react';

export interface SystemConfig {
  blockOptimization: {
    maxCombinations: number;
    minImpact: number;
    minImprovement: number;
  };
  signalLogic: {
    confidenceThreshold: number;
    signalWindow: number;
  };
  marketConditions: {
    volatilityWindow: number;
    trendStrength: number;
  };
  systemIntegration: {
    apiEndpoint: string;
    wsEndpoint: string;
    retryAttempts: number;
  };
  security: {
    requirePinForAdmin: boolean;
    sessionTimeoutMinutes: number;
  };
  monitoring: {
    decisionCycleWarningMs: number;
    alertOnSlippage: boolean;
  };
}

const DEFAULT_CONFIG: SystemConfig = {
  blockOptimization: { maxCombinations: 100, minImpact: 0.05, minImprovement: 0.1 },
  signalLogic: { confidenceThreshold: 0.7, signalWindow: 5 },
  marketConditions: { volatilityWindow: 20, trendStrength: 0.6 },
  systemIntegration: { apiEndpoint: '', wsEndpoint: '', retryAttempts: 3 },
  security: { requirePinForAdmin: true, sessionTimeoutMinutes: 60 },
  monitoring: { decisionCycleWarningMs: 5000, alertOnSlippage: true },
};

type TabId = keyof SystemConfig;

const TABS: { id: TabId; label: string }[] = [
  { id: 'blockOptimization', label: 'Block Optimization' },
  { id: 'signalLogic', label: 'Signal Logic' },
  { id: 'marketConditions', label: 'Market Conditions' },
  { id: 'systemIntegration', label: 'System Integration' },
  { id: 'security', label: 'Security' },
  { id: 'monitoring', label: 'Monitoring' },
];

export interface SystemConfigWindowProps {
  open: boolean;
  initialConfig?: Partial<SystemConfig>;
  onSave: (config: SystemConfig) => void;
  onClose: () => void;
}

export const SystemConfigWindow: React.FC<SystemConfigWindowProps> = ({
  open,
  initialConfig,
  onSave,
  onClose,
}) => {
  const [config, setConfig] = useState<SystemConfig>({ ...DEFAULT_CONFIG, ...initialConfig });
  const [activeTab, setActiveTab] = useState<TabId>('blockOptimization');
  const [hasChanges, setHasChanges] = useState(false);

  const setField = useCallback(
    <T extends TabId>(tab: T, field: keyof SystemConfig[T], value: unknown) => {
      setConfig((prev) => ({
        ...prev,
        [tab]: { ...prev[tab], [field]: value },
      }));
      setHasChanges(true);
    },
    []
  );

  const handleSave = useCallback(() => {
    onSave(config);
    setHasChanges(false);
  }, [config, onSave]);

  const handleReset = useCallback(() => {
    setConfig({ ...DEFAULT_CONFIG, ...initialConfig });
    setHasChanges(false);
  }, [initialConfig]);

  if (!open) return null;

  const renderField = (
    label: string,
    type: 'number' | 'text' | 'checkbox',
    value: number | string | boolean,
    onChange: (v: number | string | boolean) => void,
    step?: number
  ) => (
    <div className="flex items-center justify-between py-2 border-b border-zinc-800 last:border-0">
      <label className="text-sm text-zinc-300">{label}</label>
      {type === 'checkbox' ? (
        <input
          type="checkbox"
          checked={value as boolean}
          onChange={(e) => onChange(e.target.checked)}
          className="w-4 h-4 rounded border-zinc-600 bg-zinc-800 text-blue-500"
        />
      ) : (
        <input
          type={type}
          value={value as string | number}
          step={step}
          onChange={(e) =>
            onChange(type === 'number' ? parseFloat(e.target.value) : e.target.value)
          }
          className="w-40 bg-zinc-800 border border-zinc-600 rounded px-2 py-1 text-zinc-100 text-sm focus:outline-none focus:border-blue-500"
        />
      )}
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl w-full max-w-3xl mx-4 max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between border-b border-zinc-700 px-6 py-4 flex-shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-xl">⚙️</span>
            <h2 className="text-base font-semibold text-zinc-100">System Configuration</h2>
          </div>
          <button onClick={onClose} className="text-zinc-400 hover:text-zinc-200 text-xl leading-none">
            ×
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-zinc-700 overflow-x-auto flex-shrink-0">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2.5 text-sm font-medium whitespace-nowrap transition-colors border-b-2 ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {activeTab === 'blockOptimization' && (
            <div className="space-y-1">
              {renderField('Max Combinations', 'number', config.blockOptimization.maxCombinations, (v) =>
                setField('blockOptimization', 'maxCombinations', v)
              )}
              {renderField('Min Impact', 'number', config.blockOptimization.minImpact, (v) =>
                setField('blockOptimization', 'minImpact', v), 0.01
              )}
              {renderField('Min Improvement', 'number', config.blockOptimization.minImprovement, (v) =>
                setField('blockOptimization', 'minImprovement', v), 0.01
              )}
            </div>
          )}
          {activeTab === 'signalLogic' && (
            <div className="space-y-1">
              {renderField('Confidence Threshold', 'number', config.signalLogic.confidenceThreshold, (v) =>
                setField('signalLogic', 'confidenceThreshold', v), 0.01
              )}
              {renderField('Signal Window (bars)', 'number', config.signalLogic.signalWindow, (v) =>
                setField('signalLogic', 'signalWindow', v)
              )}
            </div>
          )}
          {activeTab === 'marketConditions' && (
            <div className="space-y-1">
              {renderField('Volatility Window', 'number', config.marketConditions.volatilityWindow, (v) =>
                setField('marketConditions', 'volatilityWindow', v)
              )}
              {renderField('Trend Strength', 'number', config.marketConditions.trendStrength, (v) =>
                setField('marketConditions', 'trendStrength', v), 0.01
              )}
            </div>
          )}
          {activeTab === 'systemIntegration' && (
            <div className="space-y-1">
              {renderField('API Endpoint', 'text', config.systemIntegration.apiEndpoint, (v) =>
                setField('systemIntegration', 'apiEndpoint', v)
              )}
              {renderField('WebSocket Endpoint', 'text', config.systemIntegration.wsEndpoint, (v) =>
                setField('systemIntegration', 'wsEndpoint', v)
              )}
              {renderField('Retry Attempts', 'number', config.systemIntegration.retryAttempts, (v) =>
                setField('systemIntegration', 'retryAttempts', v)
              )}
            </div>
          )}
          {activeTab === 'security' && (
            <div className="space-y-1">
              {renderField('Require PIN for Admin', 'checkbox', config.security.requirePinForAdmin, (v) =>
                setField('security', 'requirePinForAdmin', v)
              )}
              {renderField('Session Timeout (min)', 'number', config.security.sessionTimeoutMinutes, (v) =>
                setField('security', 'sessionTimeoutMinutes', v)
              )}
            </div>
          )}
          {activeTab === 'monitoring' && (
            <div className="space-y-1">
              {renderField('Cycle Warning Threshold (ms)', 'number', config.monitoring.decisionCycleWarningMs, (v) =>
                setField('monitoring', 'decisionCycleWarningMs', v)
              )}
              {renderField('Alert on Slippage', 'checkbox', config.monitoring.alertOnSlippage, (v) =>
                setField('monitoring', 'alertOnSlippage', v)
              )}
            </div>
          )}
        </div>

        <div className="flex justify-between px-6 py-4 border-t border-zinc-700 flex-shrink-0">
          <button
            onClick={handleReset}
            disabled={!hasChanges}
            className="px-4 py-2 rounded bg-zinc-700 text-zinc-200 text-sm font-medium hover:bg-zinc-600 disabled:opacity-40 transition-colors"
          >
            Reset to Defaults
          </button>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded bg-zinc-700 text-zinc-200 text-sm font-medium hover:bg-zinc-600 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!hasChanges}
              className="px-4 py-2 rounded bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-40 transition-colors"
            >
              Save Configuration
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemConfigWindow;
