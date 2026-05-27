'use client';

import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { ChevronRight, ChevronDown, Search, Filter, Save, Trash2, Blocks, Plus, X, Edit2, Check, Play } from 'lucide-react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { BlockDefinition, BlockType } from '@/lib/strategy-builder/types';
import { ExitConditionDialog, ExitConditionConfig, AvailableBlock } from './ExitConditionDialog';
import { RichTooltip, TooltipContent } from './RichTooltip';
import { QuestionDialog } from './AlertDialog';
import { resolveBlockIcon } from './blockIcons';

const BLOCK_TYPE_LABELS: Record<string, string> = {
  [BlockType.ENTRY_CONDITION]:  'Entry Condition',
  [BlockType.EXIT_CONDITION]:   'Exit Condition',
  [BlockType.RISK_MANAGEMENT]:  'Risk Management',
  [BlockType.TIME_CONSTRAINT]:  'Time Constraint',
  [BlockType.FILTER]:           'Filter',
  [BlockType.INDICATOR]:        'Indicator',
  [BlockType.POSITION_SIZING]:  'Position Sizing',
};

function getBlockIcon(definition: BlockDefinition): React.ReactNode {
  const Icon = resolveBlockIcon(definition.name, definition.category);
  return <Icon size={18} strokeWidth={1.75} />;
}

const EVENT_CATS   = new Set(['PATTERNS', 'MARKET_STRUCTURE', 'PRICE_ACTION']);
const SIGNAL_CATS  = new Set(['OSCILLATORS', 'MOVING_AVERAGES', 'VOLATILITY']);
const CONTEXT_CATS = new Set(['SESSIONS', 'FIBONACCI', 'PRICE_LEVELS']);

function computeSignalType(category: string): 'EVENT' | 'SIGNAL' | 'CONTEXT' | 'HYBRID' {
  const cat = category.toUpperCase();
  if (EVENT_CATS.has(cat))   return 'EVENT';
  if (SIGNAL_CATS.has(cat))  return 'SIGNAL';
  if (CONTEXT_CATS.has(cat)) return 'CONTEXT';
  return 'HYBRID';
}

const SIGNAL_TYPE_TOOLTIPS: Record<string, string> = {
  EVENT:
    'EVENT blocks detect discrete, selective market occurrences — chart patterns, structural breaks, or volume events that fire only when their condition is met. They are ideal as primary triggers because they mark specific actionable moments (e.g. Cup & Handle breakout, Break of Structure).',
  SIGNAL:
    'SIGNAL blocks are oscillator- and indicator-based confirmations that generate directional bias from momentum, trend, or volatility data. They run continuously and produce scored outputs (e.g. MACD crossover, RSI, Bollinger width). Use them to qualify or filter EVENT triggers.',
  CONTEXT:
    'CONTEXT blocks provide persistent market-state awareness that runs in the background at all times. They do not generate individual trade triggers; instead they describe the current environment (e.g. active Fibonacci zones, session type, key price levels) so other blocks can interpret their signals correctly.',
  HYBRID:
    'HYBRID blocks combine event-detection with continuous state tracking. They fire specific signals AND maintain background context simultaneously (e.g. ICT / SMC concepts, Wyckoff phases, Elliott Wave count). Useful when a single analysis framework handles both role.',
};

const TT_SEARCH: TooltipContent = {
  title: 'Search Building Blocks',
  body: 'Full-text search across block names, signal names, and descriptions.',
  sections: [
    { header: 'Comma-stacking:', items: [
      'Separate terms with commas to match ANY of them',
      'Example: "50, asia, hod" returns blocks mentioning 50 OR asia OR hod',
    ]},
    { header: 'Tip:', items: ['Partial terms work — you do not need exact block names'] },
  ],
};
const TT_FILTER: TooltipContent = {
  title: 'Category & Type Filter',
  body: 'Narrows the library by analysis domain (category) and block role (type).',
  sections: [
    { header: 'Category examples:', items: [
      'PATTERNS — classical chart formations (Cup & Handle, Double Top)',
      'OSCILLATORS — momentum-based indicators (RSI, MACD)',
      'SESSIONS — time-of-day context (London, New York killzones)',
    ]},
    { header: 'Type options:', items: [
      'EVENT — fires once on discrete occurrences',
      'SIGNAL — continuous indicator scoring',
      'CONTEXT — always-active background state',
      'HYBRID — combines event + continuous state',
    ]},
  ],
};
const TT_NARROW: TooltipContent = {
  title: 'Narrow Results',
  body: 'Filters within the current search + category + type results. Use to further refine a broad search.',
  sections: [
    { header: 'Tip:', items: ['Combine with a broad comma-search above to drill down precisely'] },
  ],
};
const TT_PRESET: TooltipContent = {
  title: 'Filter Presets',
  body: 'Saved combinations of search text, category, and type filters for one-click restore.',
  sections: [
    { header: 'How to use:', items: [
      'Choose a preset in this dropdown — it is applied instantly',
      'Click 💾 to open the preset browser and save or manage presets',
    ]},
    { header: 'Tip:', items: ['Create presets for views you use often, e.g. "ICT blocks" or "Bullish patterns"'] },
  ],
};
const TT_PRESET_SAVE: TooltipContent = {
  title: 'Manage Filter Presets',
  body: 'Opens the preset browser to save the current filters, rename, or delete existing presets.',
  sections: [
    { header: 'Stored in:', items: ['Browser local storage — persists across sessions on this device'] },
  ],
};
const TT_PRESET_DELETE: TooltipContent = {
  title: 'Delete Filter Preset',
  body: 'Permanently removes the selected preset from local storage.',
  sections: [
    { header: 'Warning:', items: ['This action cannot be undone'] },
  ],
};
const TT_STANDARD: TooltipContent = {
  title: 'Standard Mode',
  body: 'Each block definition can appear only once per logic slot (AND or OR) in your strategy.',
  sections: [
    { header: 'Behaviour:', items: [
      'Signals from the same block are merged into the existing card rather than creating a duplicate',
      'Already-added signals are greyed out and disabled in the library',
    ]},
    { header: 'Recommendation:', items: [
      'Use Standard mode for most strategies — keeps the board clean and prevents redundant evaluations',
    ]},
  ],
};
const TT_ADVANCED: TooltipContent = {
  title: 'Advanced Mode',
  body: 'Removes deduplication — the same block can be added multiple times with different configurations.',
  sections: [
    { header: 'Use when:', items: [
      'Building layered or ensemble strategies',
      'Stacking the same indicator at different periods (e.g. two EMA blocks at different lengths)',
    ]},
    { header: 'Note:', items: ['All signals remain selectable regardless of prior additions'] },
  ],
};
const TT_SHOW_SIGNALS: TooltipContent = {
  title: 'Signals',
  body: 'Specific named outputs this block emits during backtesting and live trading.',
  sections: [
    { header: 'Selecting signals:', items: [
      'Check individual signals to include only specific outputs in your strategy',
      'Unchecked signals are excluded when you click Add AND / Add OR / Add Exit',
      'No selection = all visible signals are included automatically',
    ]},
    { header: 'Occurrence counts:', items: [
      'Shows how often each signal fired over the last 180 days of BTC data',
      'Higher occurrence % = more frequent signal = more trade opportunities per period',
    ]},
  ],
};
const TT_ADD_AND: TooltipContent = {
  title: 'Add as AND (Required)',
  body: "This block's selected signals must ALL be present for the strategy entry to trigger.",
  sections: [
    { header: 'Use when:', items: [
      'This is a must-have confirmation for your trade setup',
      'You will not enter a trade without this block confirming',
    ]},
    { header: 'Behaviour:', items: [
      'In Standard mode, signals from the same block+AND slot are merged into one card',
      'AND enforces strict simultaneous confirmation across all required blocks',
    ]},
  ],
};
const TT_ADD_OR: TooltipContent = {
  title: 'Add as OR (Optional)',
  body: "This block's signals satisfy the entry condition independently — the strategy enters when this OR any other OR-logic block fires.",
  sections: [
    { header: 'Use when:', items: [
      'This is a supporting confluence condition',
      'You want multiple alternative confirmation paths to the same entry',
    ]},
    { header: 'Tip:', items: ['Use OR for secondary indicators that strengthen but do not gate the trade setup'] },
  ],
};
const TT_ADD_EXIT: TooltipContent = {
  title: 'Add as Exit Condition',
  body: 'Opens the Exit Condition dialog to configure how and when this block triggers a position close.',
  sections: [
    { header: 'Exit modes:', items: [
      'ABSOLUTE — closes the position at a fixed profit or loss percentage',
      'FLEXIBLE — uses TP proximity and reversal trigger thresholds for dynamic management',
    ]},
    { header: 'Binding levels:', items: [
      'Strategy — this exit applies to the entire strategy',
      'Block — applies to signals within this specific block only',
      'Signal — applies to one specific signal output',
    ]},
  ],
};

function formatSignalName(name: string): string {
  return name
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

interface FilterPreset {
  name: string;
  search: string;
  category: string;
  type: string;
}

const PRESETS_KEY = 'sb_filter_presets';

function loadPresets(): FilterPreset[] {
  try {
    return JSON.parse(localStorage.getItem(PRESETS_KEY) ?? '[]') as FilterPreset[];
  } catch {
    return [];
  }
}

function savePresets(presets: FilterPreset[]) {
  localStorage.setItem(PRESETS_KEY, JSON.stringify(presets));
}

// ─────────────────────────────────────────────
// CombinedFilterMenu — single button that opens a popover with Category + Type sections
// ─────────────────────────────────────────────
interface CombinedFilterMenuProps {
  selectedCategory: string;
  selectedType: string;
  onCategoryChange: (v: string) => void;
  onTypeChange: (v: string) => void;
  allCategories: { id: string; name: string }[];
  allTypes: { value: string; label: string }[];
}

function CombinedFilterMenu({ selectedCategory, selectedType, onCategoryChange, onTypeChange, allCategories, allTypes }: CombinedFilterMenuProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const activeCount = (selectedCategory !== 'all' ? 1 : 0) + (selectedType !== 'all' ? 1 : 0);
  const catLabel = selectedCategory !== 'all'
    ? (allCategories.find(c => c.id === selectedCategory)?.name ?? selectedCategory)
    : null;
  const typeLabel = selectedType !== 'all' ? selectedType : null;

  const parts = [catLabel, typeLabel].filter(Boolean);
  const buttonLabel = parts.length > 0 ? parts.join(' · ') : 'All';

  const clearAll = (e: React.MouseEvent) => {
    e.stopPropagation();
    onCategoryChange('all');
    onTypeChange('all');
  };

  return (
    <div ref={ref} className="relative flex-shrink-0">
      <RichTooltip content={TT_FILTER}>
        <button
          onClick={() => setOpen(v => !v)}
          className="flex items-center gap-1 px-2 py-1 rounded border text-xs transition-colors max-w-[160px]"
          style={{
            background: activeCount > 0 ? 'color-mix(in srgb, var(--accent-blue) 15%, var(--input-bg))' : 'var(--input-bg)',
            borderColor: activeCount > 0 ? 'var(--accent-blue)' : 'var(--input-border)',
            color: activeCount > 0 ? 'var(--accent-blue)' : 'var(--input-text)',
          }}
        >
          <span className="truncate max-w-[110px]">{buttonLabel}</span>
          {activeCount > 0 && (
            <span
              onClick={clearAll}
              className="flex-shrink-0 ml-0.5 hover:opacity-70 transition-opacity"
              style={{ color: 'var(--accent-blue)' }}
              title="Clear filters"
            >
              <X size={11} />
            </span>
          )}
          {activeCount === 0 && <ChevronDown size={11} className="flex-shrink-0 ml-0.5" />}
        </button>
      </RichTooltip>

      {open && (
        <div
          className="absolute left-0 top-full mt-1 z-50 rounded-lg shadow-2xl border overflow-hidden"
          style={{ background: 'var(--surface-panel)', borderColor: 'var(--border)', minWidth: 220, maxHeight: 340, overflowY: 'auto' }}
        >
          {/* Category section */}
          <div className="px-3 pt-2.5 pb-1">
            <p className="text-xs font-semibold uppercase tracking-wider mb-1.5" style={{ color: 'var(--text-muted)' }}>Category</p>
            <div className="space-y-0.5">
              {[{ id: 'all', name: 'All Categories' }, ...allCategories].map(cat => (
                <button
                  key={cat.id}
                  onClick={() => { onCategoryChange(cat.id); }}
                  className="w-full text-left text-xs px-2 py-1 rounded transition-colors"
                  style={{
                    background: selectedCategory === cat.id ? 'color-mix(in srgb, var(--accent-blue) 15%, transparent)' : 'transparent',
                    color: selectedCategory === cat.id ? 'var(--accent-blue)' : 'var(--text-secondary)',
                    fontWeight: selectedCategory === cat.id ? 600 : 400,
                  }}
                >
                  {cat.name}
                </button>
              ))}
            </div>
          </div>

          <div className="mx-3 my-2" style={{ borderTop: '1px solid var(--border)' }} />

          {/* Type section */}
          <div className="px-3 pb-2.5">
            <p className="text-xs font-semibold uppercase tracking-wider mb-1.5" style={{ color: 'var(--text-muted)' }}>Type</p>
            <div className="space-y-0.5">
              {[{ value: 'all', label: 'All Types' }, ...allTypes].map(t => (
                <button
                  key={t.value}
                  onClick={() => { onTypeChange(t.value); }}
                  className="w-full text-left text-xs px-2 py-1 rounded transition-colors"
                  style={{
                    background: selectedType === t.value ? 'color-mix(in srgb, var(--accent-blue) 15%, transparent)' : 'transparent',
                    color: selectedType === t.value ? 'var(--accent-blue)' : 'var(--text-secondary)',
                    fontWeight: selectedType === t.value ? 600 : 400,
                  }}
                >
                  {t.label}
                  {t.value !== 'all' && SIGNAL_TYPE_TOOLTIPS[t.value] && (
                    <span className="ml-1 text-xs" style={{ color: 'var(--text-muted)', fontWeight: 400 }}>
                      — {SIGNAL_TYPE_TOOLTIPS[t.value].split('—')[0].trim().substring(0, 40)}…
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
// PresetBrowserModal — full preset management UI
// ─────────────────────────────────────────────
interface PresetBrowserModalProps {
  open: boolean;
  presets: FilterPreset[];
  currentFilters: { search: string; category: string; type: string };
  onClose: () => void;
  onApply: (preset: FilterPreset) => void;
  onSave: (name: string) => void;
  onRename: (oldName: string, newName: string) => void;
  onDelete: (name: string) => void;
}

function PresetBrowserModal({ open, presets, currentFilters, onClose, onApply, onSave, onRename, onDelete }: PresetBrowserModalProps) {
  const [newName, setNewName] = useState('');
  const [editingName, setEditingName] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [presetSearch, setPresetSearch] = useState('');

  const filteredPresets = useMemo(() => {
    const q = presetSearch.trim().toLowerCase();
    if (!q) return presets;
    return presets.filter(p =>
      p.name.toLowerCase().includes(q) ||
      p.search.toLowerCase().includes(q) ||
      p.category.toLowerCase().includes(q) ||
      p.type.toLowerCase().includes(q)
    );
  }, [presets, presetSearch]);

  if (!open) return null;

  const hasActiveFilters = currentFilters.search || currentFilters.category !== 'all' || currentFilters.type !== 'all';

  const startEdit = (name: string) => {
    setEditingName(name);
    setEditValue(name);
    setConfirmDelete(null);
  };

  const commitRename = (oldName: string) => {
    if (editValue.trim() && editValue.trim() !== oldName) {
      onRename(oldName, editValue.trim());
    }
    setEditingName(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="rounded-xl shadow-2xl border flex flex-col" style={{ background: 'var(--surface-panel)', borderColor: 'var(--border)', width: 'min(820px, 95vw)', height: 'min(820px, 90vh)' }}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 flex-shrink-0" style={{ borderBottom: '1px solid var(--border)' }}>
          <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Filter Presets</h3>
          <button onClick={onClose} className="p-1 rounded hover:opacity-70 transition-opacity" style={{ color: 'var(--text-muted)' }}>
            <X size={15} />
          </button>
        </div>

        {/* Save current as new */}
        <div className="px-5 py-3.5 flex-shrink-0" style={{ borderBottom: '1px solid var(--border)' }}>
          <p className="text-xs mb-2" style={{ color: 'var(--text-muted)' }}>
            {hasActiveFilters
              ? `Save current filters as a preset:`
              : 'No active filters — set a search, category, or type first to save.'}
          </p>
          {hasActiveFilters && (
            <div className="text-xs mb-2 px-2 py-1.5 rounded" style={{ background: 'color-mix(in srgb, var(--accent-blue) 8%, transparent)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>
              {[
                currentFilters.search && `Search: "${currentFilters.search}"`,
                currentFilters.category !== 'all' && `Category: ${currentFilters.category}`,
                currentFilters.type !== 'all' && `Type: ${currentFilters.type}`,
              ].filter(Boolean).join(' · ')}
            </div>
          )}
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Preset name…"
              value={newName}
              onChange={e => setNewName(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && newName.trim() && hasActiveFilters) { onSave(newName.trim()); setNewName(''); }
                if (e.key === 'Escape') setNewName('');
              }}
              disabled={!hasActiveFilters}
              className="flex-1 px-2.5 py-1.5 rounded border text-xs focus:outline-none disabled:opacity-40"
              style={{ background: 'var(--input-bg)', borderColor: 'var(--input-border)', color: 'var(--input-text)' }}
            />
            <button
              onClick={() => { if (newName.trim() && hasActiveFilters) { onSave(newName.trim()); setNewName(''); } }}
              disabled={!newName.trim() || !hasActiveFilters}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded border text-xs font-medium transition-colors disabled:opacity-40"
              style={{ background: 'var(--accent-blue-dark)', borderColor: 'var(--accent-blue)', color: 'var(--accent-blue)' }}
            >
              <Save size={12} />
              Save
            </button>
          </div>
        </div>

        {/* Search row — matches Block Library search affordance */}
        <div className="px-5 py-3 flex-shrink-0" style={{ borderBottom: '1px solid var(--border)' }}>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 text-xs flex-shrink-0" style={{ color: 'var(--text-muted)', width: 68, justifyContent: 'flex-end' }}>
              <Search size={13} style={{ flexShrink: 0 }} />
              <span>Search:</span>
            </div>
            <input
              type="text"
              placeholder="Search presets by name, search text, category, or type…"
              value={presetSearch}
              onChange={e => setPresetSearch(e.target.value)}
              className="flex-1 px-2.5 py-1.5 rounded border text-xs focus:outline-none"
              style={{ background: 'var(--input-bg)', borderColor: 'var(--input-border)', color: 'var(--input-text)' }}
            />
          </div>
        </div>

        {/* Preset list */}
        <div className="flex-1 overflow-y-auto px-5 py-3">
          {presets.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No presets saved yet.</p>
              <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Set filters above and save them for one-click access.</p>
            </div>
          ) : filteredPresets.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No presets match &ldquo;{presetSearch}&rdquo;.</p>
              <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Try a different search term or clear the search to see all presets.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {filteredPresets.map(preset => (
                <div
                  key={preset.name}
                  className="rounded-lg border p-3"
                  style={{ background: 'var(--surface-card)', borderColor: 'var(--border)' }}
                >
                  {/* Name row */}
                  <div className="flex items-center gap-2 mb-1.5">
                    {editingName === preset.name ? (
                      <input
                        autoFocus
                        type="text"
                        value={editValue}
                        onChange={e => setEditValue(e.target.value)}
                        onKeyDown={e => {
                          if (e.key === 'Enter') commitRename(preset.name);
                          if (e.key === 'Escape') setEditingName(null);
                        }}
                        onBlur={() => commitRename(preset.name)}
                        className="flex-1 px-1.5 py-0.5 rounded border text-xs focus:outline-none"
                        style={{ background: 'var(--input-bg)', borderColor: 'var(--accent-blue)', color: 'var(--input-text)' }}
                      />
                    ) : (
                      <span className="flex-1 text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>{preset.name}</span>
                    )}
                    <button
                      onClick={() => editingName === preset.name ? commitRename(preset.name) : startEdit(preset.name)}
                      className="p-1 rounded hover:opacity-70 transition-opacity"
                      style={{ color: 'var(--text-muted)' }}
                      title={editingName === preset.name ? 'Confirm rename' : 'Rename'}
                    >
                      {editingName === preset.name ? <Check size={12} /> : <Edit2 size={12} />}
                    </button>
                  </div>

                  {/* Detail chips */}
                  <div className="flex flex-wrap gap-1 mb-2">
                    {preset.search && (
                      <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: 'color-mix(in srgb, var(--text-muted) 10%, transparent)', color: 'var(--text-secondary)' }}>
                        🔍 {preset.search}
                      </span>
                    )}
                    {preset.category !== 'all' && (
                      <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: 'color-mix(in srgb, var(--accent-blue) 10%, transparent)', color: 'var(--accent-blue)' }}>
                        {preset.category}
                      </span>
                    )}
                    {preset.type !== 'all' && (
                      <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: 'color-mix(in srgb, var(--accent-teal) 10%, transparent)', color: 'var(--accent-teal)' }}>
                        {preset.type}
                      </span>
                    )}
                    {!preset.search && preset.category === 'all' && preset.type === 'all' && (
                      <span className="text-xs" style={{ color: 'var(--text-muted)' }}>No filters (shows all)</span>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => { onApply(preset); onClose(); }}
                      className="text-xs px-2.5 py-1 rounded border font-medium transition-colors"
                      style={{ background: 'var(--accent-blue-dark)', borderColor: 'var(--accent-blue)', color: 'var(--accent-blue)' }}
                    >
                      Apply
                    </button>
                    {confirmDelete === preset.name ? (
                      <>
                        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Delete permanently?</span>
                        <button
                          onClick={() => { onDelete(preset.name); setConfirmDelete(null); }}
                          className="text-xs px-2 py-1 rounded border transition-colors"
                          style={{ borderColor: 'var(--core-danger)', color: 'var(--core-danger)', background: 'color-mix(in srgb, var(--core-danger) 10%, transparent)' }}
                        >
                          Confirm
                        </button>
                        <button
                          onClick={() => setConfirmDelete(null)}
                          className="text-xs px-2 py-1 rounded border transition-colors"
                          style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)', background: 'transparent' }}
                        >
                          Cancel
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => setConfirmDelete(preset.name)}
                        className="p-1 rounded hover:opacity-70 transition-opacity ml-auto"
                        style={{ color: 'var(--text-muted)' }}
                        title="Delete preset"
                      >
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// SignalRow — hoverable row in the expanded "Select signals to add" panel.
// Implements the BTCAAAAA-30005 hover palette (see globals.css --hover-row-*).
// ─────────────────────────────────────────────
interface SignalRowProps {
  sig: { name: string; description?: string; occurrences?: number | null; occurrence_percentage?: number | null };
  isAdded: boolean;
  isChecked: boolean;
  onToggle: () => void;
}

function SignalRow({ sig, isAdded, isChecked, onToggle }: SignalRowProps) {
  const [hovered, setHovered] = useState(false);
  const active = hovered && !isAdded;

  const rowStyle: React.CSSProperties = {
    transition: 'background 150ms ease, box-shadow 150ms ease, border-color 150ms ease',
    borderRadius: 6,
    borderStyle: 'solid',
    borderWidth: 1,
    borderColor: 'transparent',
    padding: '4px 6px',
    ...(active ? {
      background: 'linear-gradient(to bottom, var(--hover-row-bg-top), var(--hover-row-bg))',
      borderColor: 'var(--hover-row-border)',
      // BTCAAAAA-30030: dropped the 10px outer glow — it extended past the
      // 8px space-y-2 row gap and visually bled onto neighbors, reading as a
      // "frame on adjacent rows". Inset ring softened 35% -> 15% to dim the
      // bright "white frame" perceived on the hovered row.
      // BTCAAAAA-30028 finetune 3: outer-ring opacity 18% -> 12% so the glow
      // sits closer to the surrounding teal-blue panel theme instead of
      // popping as a saturated accent.
      boxShadow:
        'inset 0 0 0 1px color-mix(in srgb, var(--hover-row-border-soft) 15%, transparent), ' +
        '0 0 0 1px color-mix(in srgb, var(--hover-row-glow) 12%, transparent)',
    } : {}),
  };

  const checkboxStyle: React.CSSProperties = isChecked
    ? {
        // BTCAAAAA-30028 board fix 2026-05-27: the unhovered checked state was using
        // --accent-sky-bright (#2BE8F2 bright cyan) which doesn't appear anywhere
        // else in the dark theme. Match the hovered fill so hover only adds glow.
        backgroundColor: 'var(--hover-row-selected-fill)',
        borderColor: 'var(--hover-row-selected-fill)',
        boxShadow: active ? '0 0 6px 0 color-mix(in srgb, var(--hover-row-selected-glow) 60%, transparent)' : undefined,
        backgroundImage:
          "url(\"data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16' fill='white'%3e%3cpath d='M12.207 4.793a1 1 0 010 1.414l-5 5a1 1 0 01-1.414 0l-2-2a1 1 0 011.414-1.414L6.5 9.086l4.293-4.293a1 1 0 011.414 0z'/%3e%3c/svg%3e\")",
        backgroundSize: '100% 100%',
        transition: 'background-color 150ms ease, box-shadow 150ms ease, border-color 150ms ease',
      }
    : {
        background: active ? 'var(--hover-row-checkbox)' : 'transparent',
        borderColor: active ? 'var(--hover-row-checkbox-border)' : 'var(--text-faintest)',
        transition: 'background 150ms ease, border-color 150ms ease',
      };

  const titleColor = isAdded
    ? 'var(--text-muted)'
    : active
      ? 'var(--hover-row-text-primary)'
      : 'var(--text-secondary)';
  const countColor = active ? 'var(--hover-row-text-secondary)' : 'var(--text-muted)';
  const descColor = active ? 'var(--hover-row-text-description)' : 'var(--text-secondary)';

  return (
    <div
      className={`pl-1 ${isAdded ? 'opacity-50' : ''}`}
      style={rowStyle}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <label className={`flex items-start gap-2 ${isAdded ? 'cursor-default' : 'cursor-pointer'}`}>
        <input
          type="checkbox"
          checked={isChecked}
          disabled={isAdded}
          onChange={() => !isAdded && onToggle()}
          className="mt-0.5 flex-shrink-0 appearance-none w-3.5 h-3.5 rounded-sm border cursor-pointer disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--hover-row-glow)]"
          style={checkboxStyle}
        />
        <div className="min-w-0">
          <span
            className={`text-xs font-semibold ${isAdded ? 'line-through' : ''}`}
            style={{ color: titleColor, transition: 'color 150ms ease' }}
          >
            {formatSignalName(sig.name)}
          </span>
          {sig.occurrences != null && (
            <span className="font-normal text-xs ml-1.5" style={{ color: countColor, transition: 'color 150ms ease' }}>
              ({sig.occurrences.toLocaleString()} found, {sig.occurrence_percentage != null ? sig.occurrence_percentage.toFixed(1) : '?'}%)
            </span>
          )}
          {sig.description ? (
            <div className="text-xs mt-0.5 italic leading-relaxed" style={{ color: descColor, transition: 'color 150ms ease' }}>{sig.description}</div>
          ) : null}
        </div>
      </label>
    </div>
  );
}

// ─────────────────────────────────────────────
// BlockItem
// ─────────────────────────────────────────────
interface BlockItemProps {
  definition: BlockDefinition;
  onAdd: (def: BlockDefinition, logic: 'AND' | 'OR', selectedSignals: string[]) => void;
  onAddExit: (def: BlockDefinition, selectedSignals: string[]) => void;
  advancedMode: boolean;
  isHighlighted?: boolean;
  onHighlightCleared?: () => void;
  addedSignals?: Set<string>;
  isBlockUsed?: boolean;
}

function BlockItem({ definition, onAdd, onAddExit, advancedMode, isHighlighted, onHighlightCleared, addedSignals, isBlockUsed }: BlockItemProps) {
  const itemRef = useRef<HTMLDivElement>(null);
  const [signalsOpen, setSignalsOpen] = useState(false);
  const [checkedSignals, setCheckedSignals] = useState<Set<string>>(new Set());

  const signals = definition.signals ?? [];
  const visibleSignals = signals.filter(s => s.ui_visible !== false);

  useEffect(() => {
    if (!isHighlighted) return;
    setSignalsOpen(true);
    setTimeout(() => {
      itemRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 50);
    const t = setTimeout(() => onHighlightCleared?.(), 3500);
    return () => clearTimeout(t);
  }, [isHighlighted]); // eslint-disable-line react-hooks/exhaustive-deps

  const ext = definition as unknown as Record<string, unknown>;
  const weight = ext.weight as number | undefined;
  const typeLabel = BLOCK_TYPE_LABELS[definition.type] ?? (definition.type as string).replace('_', ' ').toUpperCase();

  const toggleSignal = (name: string) => {
    setCheckedSignals(prev => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const handleAdd = (logic: 'AND' | 'OR') => {
    const selected = checkedSignals.size > 0 ? [...checkedSignals] : visibleSignals.map(s => s.name);
    setCheckedSignals(new Set());
    onAdd(definition, logic, selected);
  };

  const handleAddExit = () => {
    const selected = checkedSignals.size > 0 ? [...checkedSignals] : visibleSignals.map(s => s.name);
    setCheckedSignals(new Set());
    onAddExit(definition, selected);
  };

  return (
    <div
      ref={itemRef}
      className="rounded-md border mb-1.5 transition-all duration-300"
      style={{
        background: isHighlighted ? 'color-mix(in srgb, var(--accent-sky-bright) 7%, transparent)' : 'var(--bg-card)',
        borderColor: isHighlighted ? 'var(--accent-sky-bright)' : 'var(--border)',
        boxShadow: isHighlighted ? '0 0 0 2px rgba(14,165,233,0.25)' : undefined,
        opacity: isBlockUsed ? 0.45 : undefined,
      }}
    >
      <div className="px-3 pt-2.5 pb-1.5">
        <div className="flex items-center gap-2">
          <span
            style={{
              color: 'var(--accent-blue)',
              flexShrink: 0,
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 26,
              height: 26,
              borderRadius: 6,
              background: 'rgba(46, 140, 255, 0.10)',
              border: '1px solid rgba(46, 140, 255, 0.35)',
              boxShadow: '0 0 6px rgba(46, 140, 255, 0.18)',
            }}
          >
            {getBlockIcon(definition)}
          </span>
          <span className={`text-sm font-medium leading-tight${isBlockUsed ? ' line-through' : ''}`} style={{ color: isBlockUsed ? 'var(--text-muted)' : 'var(--text-primary)', cursor: isBlockUsed ? 'not-allowed' : undefined }}>{definition.name}</span>
        </div>
        <div className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
          Category: {definition.category}
          {typeLabel && ` | Type: ${typeLabel}`}
          {weight != null && ` | Weight: ${weight} points`}
        </div>
      </div>

      {visibleSignals.length > 0 && (
        <RichTooltip content={TT_SHOW_SIGNALS}>
          <button
            onClick={() => setSignalsOpen(v => !v)}
            className="w-full px-3 pt-1.5 pb-2.5 text-left text-xs flex items-center gap-1.5 hover:opacity-80 transition-opacity"
            style={{
              color: 'var(--accent-blue)',
              borderTop: '1px solid rgba(46, 140, 255, 0.35)',
              marginTop: 2,
            }}
          >
            {signalsOpen ? (
              <ChevronDown size={12} style={{ flexShrink: 0, color: 'var(--accent-blue)' }} />
            ) : (
              <Play size={10} fill="currentColor" style={{ flexShrink: 0, color: 'var(--accent-blue)' }} />
            )}
            <span style={{ color: '#126f77' }}>{signalsOpen ? `Hide Signals (${visibleSignals.length})` : `Show Signals (${visibleSignals.length})`}</span>
          </button>
        </RichTooltip>
      )}

      {signalsOpen && visibleSignals.length > 0 && (
        <div className="px-3 pb-2 bg-[var(--bg-deep)]">
          <p className="text-xs font-semibold pt-2 pb-1" style={{ color: 'var(--text-secondary)' }}>Select signals to add:</p>
          <div className="space-y-2">
            {visibleSignals.map((sig, i) => {
              const isAdded = !advancedMode && (addedSignals?.has(sig.name) ?? false);
              const isChecked = checkedSignals.has(sig.name);
              return (
                <SignalRow
                  key={i}
                  sig={sig}
                  isAdded={isAdded}
                  isChecked={isChecked}
                  onToggle={() => toggleSignal(sig.name)}
                />
              );
            })}
          </div>

          <div className="flex gap-1.5 mt-3">
            <RichTooltip content={TT_ADD_AND}>
              <button
                onClick={() => handleAdd('AND')}
                className="flex-1 flex items-center justify-center gap-1 text-xs py-1.5 rounded border font-medium transition-colors"
                style={{ borderColor: 'var(--accent-green-mid)', background: 'var(--accent-green-dark)', color: 'var(--accent-green)' }}
                onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--accent-green-mid)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--accent-green-dark)'; }}
              >
                <Plus size={13} style={{ flexShrink: 0 }} />
                Add as AND (Required)
              </button>
            </RichTooltip>
            <RichTooltip content={TT_ADD_OR}>
              <button
                onClick={() => handleAdd('OR')}
                className="flex-1 flex items-center justify-center gap-1 text-xs py-1.5 rounded border font-medium transition-colors"
                style={{ borderColor: 'var(--accent-blue-mid)', background: 'var(--accent-blue-dark)', color: 'var(--accent-blue)' }}
                onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--accent-blue-mid)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--accent-blue-dark)'; }}
              >
                <Plus size={13} style={{ flexShrink: 0 }} />
                Add as OR (Optional)
              </button>
            </RichTooltip>
            <RichTooltip content={TT_ADD_EXIT}>
              <button
                onClick={handleAddExit}
                className="flex-1 flex items-center justify-center gap-1 text-xs py-1.5 rounded border font-medium transition-colors"
                style={{ borderColor: 'var(--accent-red-dark)', background: 'var(--accent-red-deeper)', color: 'var(--accent-red)' }}
                onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--accent-red-dark)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--accent-red-deeper)'; }}
              >
                <Plus size={13} style={{ flexShrink: 0 }} />
                Add as Exit
              </button>
            </RichTooltip>
          </div>

          <p className="text-xs italic mt-2" style={{ color: 'var(--text-muted)' }}>
            Note: Signal counts based on last 180 days of BTC data
          </p>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
// BlockSearchPanel (main export)
// ─────────────────────────────────────────────
export function BlockSearchPanel() {
  const {
    blockLibrary,
    blockCategories,
    isLoadingLibrary,
    addBlock,
    updateBlock,
    currentStrategy,
    highlightedLibraryBlockId,
    highlightLibraryBlock,
  } = useStrategyStore();

  const [searchText, setSearchText]     = useState('');
  const [narrowText, setNarrowText]     = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedType, setSelectedType] = useState<'EVENT' | 'SIGNAL' | 'CONTEXT' | 'HYBRID' | 'all'>('all');
  const [advancedMode, setAdvancedMode] = useState(false);

  const [exitPending, setExitPending] = useState<{
    definition: BlockDefinition;
    selectedSignals: string[];
  } | null>(null);

  useEffect(() => {
    if (!highlightedLibraryBlockId) return;
    setSearchText('');
    setNarrowText('');
    setSelectedCategory('all');
    setSelectedType('all');
  }, [highlightedLibraryBlockId]);

  // Presets
  const [presets, setPresets]           = useState<FilterPreset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState('');
  const [presetBrowserOpen, setPresetBrowserOpen] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  useEffect(() => { setPresets(loadPresets()); }, []);

  const handleSavePreset = useCallback((name: string) => {
    const preset: FilterPreset = { name, search: searchText, category: selectedCategory, type: selectedType };
    const updated = [...presets.filter(p => p.name !== preset.name), preset];
    savePresets(updated);
    setPresets(updated);
    setSelectedPreset(name);
  }, [searchText, selectedCategory, selectedType, presets]);

  const handleRenamePreset = useCallback((oldName: string, newName: string) => {
    const updated = presets.map(p => p.name === oldName ? { ...p, name: newName } : p);
    savePresets(updated);
    setPresets(updated);
    if (selectedPreset === oldName) setSelectedPreset(newName);
  }, [presets, selectedPreset]);

  const handleDeletePreset = useCallback((name: string) => {
    const updated = presets.filter(p => p.name !== name);
    savePresets(updated);
    setPresets(updated);
    if (selectedPreset === name) setSelectedPreset('');
  }, [presets, selectedPreset]);

  const handleApplyPreset = useCallback((preset: FilterPreset) => {
    setSearchText(preset.search);
    setSelectedCategory(preset.category);
    setSelectedType(preset.type as 'EVENT' | 'SIGNAL' | 'CONTEXT' | 'HYBRID' | 'all');
    setNarrowText('');
    setSelectedPreset(preset.name);
  }, []);

  const handlePresetSelectChange = useCallback((name: string) => {
    if (!name) {
      setSelectedPreset('');
      return;
    }
    const preset = presets.find(p => p.name === name);
    if (!preset) {
      setSelectedPreset(name);
      return;
    }
    handleApplyPreset(preset);
  }, [presets, handleApplyPreset]);

  // Primary filtered blocks (search + category + type)
  const filteredBlocks = useMemo(() => {
    const terms = searchText
      .split(',')
      .map(t => t.trim().toLowerCase())
      .filter(Boolean);
    return blockLibrary
      .filter(b => {
        const matchSearch = terms.length === 0 || terms.some(q =>
          b.name.toLowerCase().includes(q) ||
          b.description.toLowerCase().includes(q) ||
          (b.signals ?? []).some(s =>
            s.name.toLowerCase().includes(q) ||
            (s.description ?? '').toLowerCase().includes(q)
          )
        );
        const matchCat = selectedCategory === 'all' || b.category === selectedCategory;
        const matchType = selectedType === 'all' || computeSignalType(b.category) === selectedType;
        return matchSearch && matchCat && matchType;
      })
      .sort((a, b) => {
        if (a.category < b.category) return -1;
        if (a.category > b.category) return 1;
        return a.name.localeCompare(b.name);
      });
  }, [blockLibrary, searchText, selectedCategory, selectedType]);

  // Map definitionId → Set of signal names already in the strategy (standard mode only).
  const addedSignalsByDefId = useMemo(() => {
    if (advancedMode || !currentStrategy?.blocks) return new Map<string, Set<string>>();
    const map = new Map<string, Set<string>>();
    for (const block of currentStrategy.blocks) {
      const defId = (block.data as Record<string, unknown>).definitionId as string;
      if (!defId) continue;
      const signals = ((block.data as Record<string, unknown>).signals as Array<{ name: string }>) ?? [];
      if (!map.has(defId)) map.set(defId, new Set());
      for (const s of signals) map.get(defId)!.add(s.name);
    }
    return map;
  }, [advancedMode, currentStrategy?.blocks]);

  // Secondary narrow — filters within filteredBlocks
  const displayBlocks = useMemo(() => {
    const q = narrowText.trim().toLowerCase();
    if (!q) return filteredBlocks;
    return filteredBlocks.filter(b =>
      b.name.toLowerCase().includes(q) ||
      b.description.toLowerCase().includes(q)
    );
  }, [filteredBlocks, narrowText]);

  const allCategories = useMemo(() => {
    if (blockCategories.length > 0) return blockCategories.map(c => ({ id: c.id, name: c.name }));
    const cats = new Set(blockLibrary.map(b => b.category));
    return [...cats].sort().map(c => ({
      id: c,
      name: c.replace(/_/g, ' ').replace(/\b\w/g, (ch: string) => ch.toUpperCase()),
    }));
  }, [blockCategories, blockLibrary]);

  const allTypes = useMemo(() => {
    const seen = new Set(blockLibrary.map(b => computeSignalType(b.category)));
    return (['CONTEXT', 'EVENT', 'HYBRID', 'SIGNAL'] as const).filter(t => seen.has(t)).map(t => ({
      value: t,
      label: t.charAt(0) + t.slice(1).toLowerCase(),
    }));
  }, [blockLibrary]);

  const handleAdd = useCallback(
    (definition: BlockDefinition, logic: 'AND' | 'OR', selectedSignals: string[]) => {
      const state = useStrategyStore.getState();
      const allSignals = definition.signals ?? [];
      const signalsToAdd = selectedSignals.length > 0
        ? allSignals.filter(s => selectedSignals.includes(s.name))
        : allSignals;
      const newSignalData = signalsToAdd.map(s => ({
        name: s.name,
        description: s.description ?? '',
        recheckEnabled: false,
      }));

      if (!advancedMode) {
        const currentBlocks = state.currentStrategy?.blocks ?? [];
        const existingIdx = currentBlocks.findIndex(
          b =>
            (b.data as Record<string, unknown>).definitionId === definition.id &&
            (b.data as Record<string, unknown>).logic === logic
        );
        if (existingIdx >= 0) {
          const existingSignals =
            ((currentBlocks[existingIdx].data as Record<string, unknown>).signals as Array<Record<string, unknown>>) ?? [];
          updateBlock(existingIdx, { signals: [...existingSignals, ...newSignalData] });
          return;
        }
      }

      const position = state.currentStrategy?.blocks.length ?? 0;
      addBlock(definition.type, position);
      updateBlock(position, {
        name: definition.name,
        definitionId: definition.id,
        category: definition.category,
        logic,
        signals: newSignalData,
      });
    },
    [addBlock, updateBlock, advancedMode]
  );

  const handleAddExit = useCallback(
    (definition: BlockDefinition, selectedSignals: string[]) => {
      setExitPending({ definition, selectedSignals });
    },
    []
  );

  const handleExitSave = useCallback(
    (config: ExitConditionConfig) => {
      if (!exitPending) return;
      const { definition, selectedSignals } = exitPending;
      const state = useStrategyStore.getState();
      const allSignals = definition.signals ?? [];
      const signalsToAdd = selectedSignals.length > 0
        ? allSignals.filter(s => selectedSignals.includes(s.name))
        : allSignals;
      const newSignalData = signalsToAdd.map(s => ({
        name: s.name,
        description: s.description ?? '',
        recheckEnabled: false,
      }));

      const position = state.currentStrategy?.blocks.length ?? 0;
      addBlock(BlockType.EXIT_CONDITION, position);
      updateBlock(position, {
        name: definition.name,
        definitionId: definition.id,
        category: definition.category,
        logic: 'EXIT',
        signals: newSignalData,
        exitConfig: config,
      });
      setExitPending(null);
    },
    [exitPending, addBlock, updateBlock]
  );

  return (
    <div className="flex flex-col h-full border-l border-[var(--border)]" style={{ background: 'var(--bg-deep)' }}>
      {/* Panel header with Standard / Advanced toggle */}
      <div className="px-4 py-2 border-b border-[var(--border)] flex-shrink-0 flex items-center justify-between" style={{ background: 'var(--bg-panel)' }}>
        <div className="flex items-center gap-2">
          <Blocks size={14} style={{ color: 'var(--text-dim)', flexShrink: 0 }} />
          <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-dim)' }}>
            Available Building Blocks
          </h2>
        </div>
        <div className="flex items-center" style={{ border: '1px solid var(--border)', borderRadius: 4, overflow: 'hidden' }}>
          <RichTooltip content={TT_STANDARD}>
            <button
              onClick={() => setAdvancedMode(false)}
              className="text-xs px-2.5 py-1 transition-colors"
              style={!advancedMode
                ? { background: 'var(--accent-blue-dark)', color: 'var(--accent-blue)', fontWeight: 600 }
                : { background: 'var(--bg-card)', color: 'var(--text-muted)' }}
            >
              Standard
            </button>
          </RichTooltip>
          <RichTooltip content={TT_ADVANCED}>
            <button
              onClick={() => setAdvancedMode(true)}
              className="text-xs px-2.5 py-1 transition-colors border-l border-[var(--border)]"
              style={advancedMode
                ? { background: 'var(--accent-blue-dark)', color: 'var(--accent-blue)', fontWeight: 600 }
                : { background: 'var(--bg-card)', color: 'var(--text-muted)' }}
            >
              Advanced
            </button>
          </RichTooltip>
        </div>
      </div>

      {/* Search + Filter rows */}
      <div className="px-3 pt-3 pb-2 space-y-1.5 flex-shrink-0 border-b border-[var(--border)]" style={{ background: 'var(--bg-panel)' }}>
        {/* Row 1: Main search */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 text-xs flex-shrink-0" style={{ color: 'var(--text-muted)', width: 68, justifyContent: 'flex-end' }}>
            <Search size={13} style={{ flexShrink: 0 }} />
            <span>Search:</span>
          </div>
          <RichTooltip content={TT_SEARCH}>
            <input
              type="text"
              placeholder="Search name, signal, description… or stack with commas: 50, asia, hod"
              value={searchText}
              onChange={e => setSearchText(e.target.value)}
              className="flex-1 px-2.5 py-1.5 rounded border text-xs focus:outline-none"
              style={{ background: 'var(--input-bg)', borderColor: 'var(--input-border)', color: 'var(--input-text)' }}
            />
          </RichTooltip>
        </div>

        {/* Row 2: Combined filter + narrow within results */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 text-xs flex-shrink-0" style={{ color: 'var(--text-muted)', width: 68, justifyContent: 'flex-end' }}>
            <Filter size={13} style={{ flexShrink: 0 }} />
            <span>Filter:</span>
          </div>
          <CombinedFilterMenu
            selectedCategory={selectedCategory}
            selectedType={selectedType}
            onCategoryChange={setSelectedCategory}
            onTypeChange={v => setSelectedType(v as 'EVENT' | 'SIGNAL' | 'CONTEXT' | 'HYBRID' | 'all')}
            allCategories={allCategories}
            allTypes={allTypes}
          />
          <RichTooltip content={TT_NARROW}>
            <input
              type="text"
              placeholder="Narrow within results…"
              value={narrowText}
              onChange={e => setNarrowText(e.target.value)}
              className="flex-1 min-w-0 px-2.5 py-1.5 rounded border text-xs focus:outline-none"
              style={{ background: 'var(--input-bg)', borderColor: 'var(--input-border)', color: 'var(--input-text)' }}
            />
          </RichTooltip>
        </div>

        {/* Row 3: Presets */}
        <div className="flex items-center gap-1.5">
          <div className="flex items-center gap-1.5 text-xs flex-shrink-0" style={{ color: 'var(--text-muted)', width: 68, justifyContent: 'flex-end' }}>
            <Save size={13} style={{ flexShrink: 0 }} />
            <span>Preset:</span>
          </div>
          <RichTooltip content={TT_PRESET}>
            <select
              value={selectedPreset}
              onChange={e => handlePresetSelectChange(e.target.value)}
              className="flex-1 min-w-0 px-1.5 py-1 rounded border text-xs focus:outline-none"
              style={{ background: 'var(--bg-card)', borderColor: 'var(--border)', color: 'var(--text-dim)' }}
            >
              <option value="">— Select preset —</option>
              {presets.map(p => <option key={p.name} value={p.name}>{p.name}</option>)}
            </select>
          </RichTooltip>
          <RichTooltip content={TT_PRESET_SAVE}>
            <button
              onClick={() => setPresetBrowserOpen(true)}
              className="flex items-center gap-1 px-2 py-1 rounded border flex-shrink-0 hover:opacity-80 transition-opacity text-xs"
              style={{ background: 'var(--bg-card)', borderColor: 'var(--border)', color: 'var(--text-dim)' }}
              title="Manage presets"
            >
              <Save size={12} />
              Manage
            </button>
          </RichTooltip>
        </div>
      </div>

      {/* Block list */}
      <div className="flex-1 overflow-y-auto px-3 py-3" style={{ background: 'var(--bg-deep)', scrollbarWidth: 'thin', scrollbarColor: 'var(--border) transparent' }}>
        {isLoadingLibrary ? (
          <div className="flex flex-col items-center justify-center py-10 gap-2">
            <div className="w-6 h-6 border-2 rounded-full animate-spin" style={{ borderColor: 'var(--border)', borderTopColor: 'var(--accent-blue)' }} />
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Loading block library…</p>
          </div>
        ) : displayBlocks.length === 0 ? (
          <p className="text-xs text-center py-8" style={{ color: 'var(--text-secondary)' }}>No blocks match the current filters</p>
        ) : (
          displayBlocks.map(block => (
            <BlockItem
              key={block.id}
              definition={block}
              onAdd={handleAdd}
              onAddExit={handleAddExit}
              advancedMode={advancedMode}
              isHighlighted={highlightedLibraryBlockId === block.id}
              onHighlightCleared={() => highlightLibraryBlock(null)}
              addedSignals={addedSignalsByDefId.get(block.id)}
            />
          ))
        )}
      </div>

      {/* Footer count */}
      <div className="px-3 py-2 border-t border-[var(--border)] flex-shrink-0 flex items-center justify-between" style={{ background: 'var(--bg-panel)' }}>
        <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
          {displayBlocks.length} / {blockLibrary.length} blocks
          {narrowText && filteredBlocks.length !== displayBlocks.length && (
            <span style={{ color: 'var(--text-muted)' }}> ({filteredBlocks.length} before narrow)</span>
          )}
        </p>
        {currentStrategy && (
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            {currentStrategy.blocks.length} in strategy
          </p>
        )}
      </div>

      <PresetBrowserModal
        open={presetBrowserOpen}
        presets={presets}
        currentFilters={{ search: searchText, category: selectedCategory, type: selectedType }}
        onClose={() => setPresetBrowserOpen(false)}
        onApply={handleApplyPreset}
        onSave={handleSavePreset}
        onRename={handleRenamePreset}
        onDelete={handleDeletePreset}
      />

      <QuestionDialog
        open={deleteConfirmOpen}
        icon="⚠️"
        title="Delete Filter Preset"
        heading={`Delete "${selectedPreset}"?`}
        message="This preset will be permanently removed from local storage and cannot be recovered."
        onResult={(result) => {
          setDeleteConfirmOpen(false);
          if (result === 'yes') handleDeletePreset(selectedPreset);
        }}
      />

      {exitPending && (() => {
        const stratBlocks = currentStrategy?.blocks ?? [];
        const availableBlocks: AvailableBlock[] = stratBlocks
          .filter(b => b.type !== BlockType.EXIT_CONDITION && (b.data as Record<string, unknown>).logic !== 'EXIT')
          .map(b => ({
            id: b.id,
            name: (b.data as Record<string, unknown>).name as string ?? b.id,
            signals: ((b.data as Record<string, unknown>).signals as Array<{ name: string }> | undefined ?? []).map(s => s.name),
          }));
        const signalName = exitPending.selectedSignals.length === 1
          ? exitPending.selectedSignals[0]
          : exitPending.definition.name;
        return (
          <ExitConditionDialog
            open={true}
            signalName={signalName}
            availableBlocks={availableBlocks}
            onSave={handleExitSave}
            onCancel={() => setExitPending(null)}
          />
        );
      })()}
    </div>
  );
}
