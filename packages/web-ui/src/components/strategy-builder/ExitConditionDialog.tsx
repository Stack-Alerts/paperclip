'use client';

import React, { useState } from 'react';

export interface ExitConditionConfig {
  signalName: string;
  percentage: number;            // stored 0.01–1.0 (e.g. 50% → 0.5)
  exitMode: 'ABSOLUTE' | 'FLEXIBLE';
  bindingLevel: 'STRATEGY' | 'BLOCK' | 'SIGNAL';
  tpProximityThreshold: number;  // 0.25–10.0 (%)
  reversalTrigger: number;       // stored 0.1–1.0 (e.g. 5% → 0.5)
  recheckEnabled: boolean;
  recheckBarDelay: number;
  blockName?: string;
  parentSignalName?: string;
}

export interface AvailableBlock {
  id: string;
  name: string;
  signals: string[];
}

export interface ExitConditionDialogProps {
  open: boolean;
  signalName?: string;
  availableBlocks?: AvailableBlock[];
  existing?: ExitConditionConfig;
  onSave: (config: ExitConditionConfig) => void;
  onCancel: () => void;
}

function PresetChip({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="text-xs px-2 py-0.5 rounded transition-colors hover:opacity-80 flex-shrink-0"
      style={{ background: 'var(--accent-teal-dark)', color: 'var(--text-secondary)', border: '1px solid var(--accent-teal-mid)' }}
    >
      {label}
    </button>
  );
}

const BINDING_OPTIONS = [
  {
    value: 'STRATEGY' as const,
    label: 'STRATEGY - Apply to all positions',
    desc: '└─ Global exit for entire strategy',
    color: 'var(--accent-red)',
  },
  {
    value: 'BLOCK' as const,
    label: 'BLOCK - Apply to specific block positions',
    desc: '└─ Exit only for positions from specific block',
    color: 'var(--accent-orange)',
  },
  {
    value: 'SIGNAL' as const,
    label: 'SIGNAL - Apply to specific signal positions',
    desc: '└─ Granular exit for specific signal only',
    color: 'var(--accent-blue)',
  },
];

const MODE_OPTIONS = [
  {
    value: 'ABSOLUTE' as const,
    label: 'ABSOLUTE - Exit Immediately',
    desc: '└─ Executes partial exit as soon as signal fires',
    color: 'var(--text-secondary)',
  },
  {
    value: 'FLEXIBLE' as const,
    label: 'FLEXIBLE - TP-Aware Exit',
    desc: '└─ Defers exit if price moving toward TP; fires on reversal',
    color: 'var(--accent-blue)',
  },
];

export function ExitConditionDialog({
  open,
  signalName,
  availableBlocks,
  existing,
  onSave,
  onCancel,
}: ExitConditionDialogProps) {
  const isEditMode = !!existing;

  // Lazy initializers run once on mount — component is unmounted/remounted each time
  // the dialog is opened, so this always captures the correct initial config.
  // Using useState(fn) instead of useEffect+setState prevents the reset-on-re-render
  // bug caused by `existing` being a new object reference on every parent render.
  const [bindingLevel, setBindingLevel] = useState<'STRATEGY' | 'BLOCK' | 'SIGNAL'>(
    () => existing?.bindingLevel ?? 'STRATEGY'
  );
  const [selectedBlockName, setSelectedBlockName] = useState(
    () => existing?.blockName ?? ''
  );
  const [selectedSignalKey, setSelectedSignalKey] = useState(
    () => existing?.blockName && existing?.parentSignalName
      ? `${existing.blockName}::${existing.parentSignalName}` : ''
  );
  const [percentage, setPercentage] = useState(
    () => existing ? Math.round(existing.percentage * 100) : 50
  );
  const [exitMode, setExitMode] = useState<'ABSOLUTE' | 'FLEXIBLE'>(
    () => existing?.exitMode ?? 'ABSOLUTE'
  );
  const [tpProximity, setTpProximity] = useState(
    () => existing?.tpProximityThreshold ?? 2.0
  );
  const [reversal, setReversal] = useState(
    () => existing ? Math.round(existing.reversalTrigger * 10) : 5
  );
  const [recheckEnabled, setRecheckEnabled] = useState(
    () => existing?.recheckEnabled ?? false
  );
  const [recheckDelay, setRecheckDelay] = useState(
    () => existing?.recheckBarDelay ?? 3
  );

  if (!open) return null;

  // Flat list of block→signal pairs for SIGNAL binding selector
  const allSignalOptions: { key: string; label: string }[] = [];
  for (const b of (availableBlocks ?? [])) {
    for (const sig of b.signals) {
      allSignalOptions.push({ key: `${b.name}::${sig}`, label: `${b.name} → ${sig}` });
    }
  }

  const handleSave = () => {
    const config: ExitConditionConfig = {
      signalName: signalName ?? '',
      percentage: percentage / 100,
      exitMode,
      bindingLevel,
      tpProximityThreshold: tpProximity,
      reversalTrigger: reversal / 10,
      recheckEnabled,
      recheckBarDelay: recheckDelay,
    };
    if (bindingLevel === 'BLOCK' && selectedBlockName) {
      config.blockName = selectedBlockName;
    }
    if (bindingLevel === 'SIGNAL' && selectedSignalKey.includes('::')) {
      const idx = selectedSignalKey.indexOf('::');
      config.blockName = selectedSignalKey.slice(0, idx);
      config.parentSignalName = selectedSignalKey.slice(idx + 2);
    }
    onSave(config);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div
        className="rounded border shadow-2xl flex flex-col"
        style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)', width: 680, maxHeight: '90vh' }}
      >
        {/* Title bar */}
        <div
          className="flex items-center justify-between px-4 py-2 border-b rounded-t flex-shrink-0"
          style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}
        >
          <span className="text-sm font-semibold" style={{ color: 'var(--text-secondary)' }}>Configure Exit Condition</span>
          <div className="flex items-center gap-1">
            <span className="w-5 h-5 rounded text-xs flex items-center justify-center" style={{ background: 'var(--border)', color: 'var(--text-secondary)' }}>─</span>
            <span className="w-5 h-5 rounded text-xs flex items-center justify-center" style={{ background: 'var(--border)', color: 'var(--text-secondary)' }}>□</span>
            <button
              onClick={onCancel}
              className="w-5 h-5 rounded text-xs flex items-center justify-center hover:opacity-80"
              style={{ background: 'var(--accent-red-dark)', color: 'var(--text-secondary)' }}
            >✕</button>
          </div>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto" style={{ scrollbarWidth: 'thin', scrollbarColor: 'var(--border) transparent' }}>
          <div className="px-4 py-4 space-y-4">
            {/* Dialog header */}
            <div className="text-sm font-bold" style={{ color: 'var(--accent-teal)' }}>
              ⚙ Configure EXIT: {signalName}
            </div>

            {/* Exit Binding Level — hidden in edit mode */}
            {!isEditMode && (
              <section className="border rounded p-3 space-y-2" style={{ borderColor: 'var(--border)' }}>
                <div className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>Exit Binding Level</div>
                {BINDING_OPTIONS.map(opt => (
                  <div key={opt.value}>
                    <div
                      className="flex items-center gap-2 cursor-pointer"
                      onClick={() => setBindingLevel(opt.value)}
                    >
                      <div
                        className="w-4 h-4 rounded-full border-2 flex items-center justify-center flex-shrink-0"
                        style={{ borderColor: bindingLevel === opt.value ? opt.color : 'var(--text-muted)' }}
                      >
                        {bindingLevel === opt.value && (
                          <div className="w-2 h-2 rounded-full" style={{ background: opt.color }} />
                        )}
                      </div>
                      <span
                        className="text-sm font-semibold"
                        style={{ color: bindingLevel === opt.value ? opt.color : 'var(--text-secondary)' }}
                      >
                        {opt.label}
                      </span>
                    </div>
                    <div className="ml-6 text-xs" style={{ color: 'var(--text-muted)' }}>{opt.desc}</div>

                    {opt.value === 'BLOCK' && bindingLevel === 'BLOCK' && (availableBlocks ?? []).length > 0 && (
                      <div className="ml-6 mt-1.5">
                        <select
                          value={selectedBlockName}
                          onChange={e => setSelectedBlockName(e.target.value)}
                          className="w-full px-2 py-1.5 rounded border text-xs focus:outline-none"
                          style={{ background: 'var(--input-bg)', borderColor: 'var(--input-border)', color: 'var(--input-text)' }}
                        >
                          <option value="">Select block…</option>
                          {(availableBlocks ?? []).map(b => (
                            <option key={b.id} value={b.name}>{b.name}</option>
                          ))}
                        </select>
                      </div>
                    )}

                    {opt.value === 'SIGNAL' && bindingLevel === 'SIGNAL' && allSignalOptions.length > 0 && (
                      <div className="ml-6 mt-1.5">
                        <select
                          value={selectedSignalKey}
                          onChange={e => setSelectedSignalKey(e.target.value)}
                          className="w-full px-2 py-1.5 rounded border text-xs focus:outline-none"
                          style={{ background: 'var(--input-bg)', borderColor: 'var(--input-border)', color: 'var(--input-text)' }}
                        >
                          <option value="">Select signal…</option>
                          {allSignalOptions.map(o => (
                            <option key={o.key} value={o.key}>{o.label}</option>
                          ))}
                        </select>
                      </div>
                    )}
                  </div>
                ))}
              </section>
            )}

            {/* Exit Percentage */}
            <section className="border rounded p-3" style={{ borderColor: 'var(--border)' }}>
              <div className="text-xs font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>Exit Percentage</div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs flex-shrink-0" style={{ color: 'var(--text-secondary)' }}>Close % of Position:</span>
                <input
                  type="number"
                  min={1}
                  max={100}
                  value={percentage}
                  onChange={e =>
                    setPercentage(Math.min(100, Math.max(1, parseInt(e.target.value) || 1)))
                  }
                  className="w-16 px-2 py-1 rounded border text-sm text-center focus:outline-none"
                  style={{ background: 'var(--input-bg)', borderColor: 'var(--input-border)', color: 'var(--input-text)' }}
                />
                {[10, 15, 20, 25, 50, 75, 100].map(p => (
                  <PresetChip key={p} label={`${p}%`} onClick={() => setPercentage(p)} />
                ))}
              </div>
            </section>

            {/* Exit Mode */}
            <section className="border rounded p-3 space-y-2" style={{ borderColor: 'var(--border)' }}>
              <div className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>Exit Mode</div>
              {MODE_OPTIONS.map(opt => (
                <div key={opt.value}>
                  <div className="flex items-center gap-2 cursor-pointer" onClick={() => setExitMode(opt.value)}>
                    <div
                      className="w-4 h-4 rounded-full border-2 flex items-center justify-center flex-shrink-0"
                      style={{ borderColor: exitMode === opt.value ? opt.color : 'var(--text-muted)' }}
                    >
                      {exitMode === opt.value && (
                        <div className="w-2 h-2 rounded-full" style={{ background: opt.color }} />
                      )}
                    </div>
                    <span
                      className="text-sm font-semibold"
                      style={{ color: exitMode === opt.value ? opt.color : 'var(--text-secondary)' }}
                    >
                      {opt.label}
                    </span>
                  </div>
                  <div className="ml-6 text-xs" style={{ color: 'var(--text-muted)' }}>{opt.desc}</div>
                </div>
              ))}
            </section>

            {/* FLEXIBLE Mode Parameters */}
            {exitMode === 'FLEXIBLE' && (
              <section
                className="border rounded p-3 space-y-3"
                style={{ borderColor: 'var(--accent-blue)', background: 'color-mix(in srgb, var(--accent-blue) 5%, transparent)' }}
              >
                <div className="text-xs font-semibold" style={{ color: 'var(--accent-blue)' }}>
                  FLEXIBLE Mode Parameters
                </div>

                {/* TP Proximity */}
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs w-40 flex-shrink-0" style={{ color: 'var(--text-secondary)' }}>
                    TP Proximity Threshold:
                  </span>
                  <input
                    type="number"
                    min={0.25}
                    max={10}
                    step={0.25}
                    value={tpProximity}
                    onChange={e =>
                      setTpProximity(
                        Math.min(10, Math.max(0.25, parseFloat(e.target.value) || 0.25))
                      )
                    }
                    className="w-20 px-2 py-1 rounded border text-sm text-center focus:outline-none"
                    style={{ background: 'var(--input-bg)', borderColor: 'var(--input-border)', color: 'var(--input-text)' }}
                  />
                  <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>%</span>
                  {[0.25, 0.5, 1.0, 1.5, 2.0].map(v => (
                    <PresetChip key={v} label={`${v}%`} onClick={() => setTpProximity(v)} />
                  ))}
                </div>

                {/* Reversal Trigger */}
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs w-40 flex-shrink-0" style={{ color: 'var(--text-secondary)' }}>
                    Reversal Trigger:
                  </span>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={reversal}
                    onChange={e => setReversal(Math.min(10, Math.max(1, parseInt(e.target.value) || 1)))}
                    className="w-20 px-2 py-1 rounded border text-sm text-center focus:outline-none"
                    style={{ background: 'var(--input-bg)', borderColor: 'var(--input-border)', color: 'var(--input-text)' }}
                  />
                  <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>%</span>
                  {[1, 2, 3, 4, 5, 6, 7, 8].map(v => (
                    <PresetChip key={v} label={`${v}%`} onClick={() => setReversal(v)} />
                  ))}
                </div>
              </section>
            )}

            {/* RECHECK Validation */}
            <section className="border rounded p-3" style={{ borderColor: 'var(--border)' }}>
              <div className="text-xs font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>RECHECK Validation</div>
              <div
                className="flex items-center gap-2 cursor-pointer"
                onClick={() => setRecheckEnabled(v => !v)}
              >
                <div
                  className="w-4 h-4 rounded border-2 flex items-center justify-center flex-shrink-0"
                  style={{
                    borderColor: recheckEnabled ? 'var(--accent-green)' : 'var(--text-muted)',
                    background: recheckEnabled ? 'var(--accent-green)' : 'transparent',
                  }}
                >
                  {recheckEnabled && (
                    <span className="leading-none" style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-secondary)' }}>✓</span>
                  )}
                </div>
                <span className="text-sm" style={{ color: recheckEnabled ? 'var(--text-secondary)' : 'var(--text-secondary)' }}>
                  Enable RECHECK for this exit condition
                </span>
              </div>

              {recheckEnabled && (
                <div className="flex items-center gap-2 flex-wrap mt-2 ml-6">
                  <span className="text-xs flex-shrink-0" style={{ color: 'var(--text-secondary)' }}>Bar Delay:</span>
                  <input
                    type="number"
                    min={1}
                    max={500}
                    value={recheckDelay}
                    onChange={e => setRecheckDelay(Math.max(1, parseInt(e.target.value) || 1))}
                    className="w-16 px-2 py-1 rounded border text-sm text-center focus:outline-none"
                    style={{ background: 'var(--input-bg)', borderColor: 'var(--input-border)', color: 'var(--input-text)' }}
                  />
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(v => (
                    <PresetChip key={v} label={String(v)} onClick={() => setRecheckDelay(v)} />
                  ))}
                </div>
              )}
            </section>
          </div>
        </div>

        {/* Footer */}
        <div className="flex border-t rounded-b overflow-hidden flex-shrink-0" style={{ borderColor: 'var(--border)' }}>
          <button
            onClick={onCancel}
            className="flex-1 py-3 text-sm font-semibold transition-colors hover:brightness-110"
            style={{ background: 'var(--btn-cancel-bg)', color: 'var(--btn-primary-text)' }}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="flex-1 py-3 text-sm font-semibold transition-colors hover:brightness-110"
            style={{ background: 'var(--btn-confirm-bg)', color: 'var(--btn-primary-text)' }}
          >
            {isEditMode ? 'Update Exit Condition' : 'Add Exit Condition'}
          </button>
        </div>
      </div>
    </div>
  );
}
