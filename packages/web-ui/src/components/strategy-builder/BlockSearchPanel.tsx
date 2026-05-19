'use client';

import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { ChevronRight, Search, Filter, Save, Folder, Trash2, Blocks, Plus } from 'lucide-react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { BlockDefinition, BlockType } from '@/lib/strategy-builder/types';
import { ExitConditionDialog, ExitConditionConfig, AvailableBlock } from './ExitConditionDialog';
import { RichTooltip, TooltipContent } from './RichTooltip';
import { QuestionDialog } from './AlertDialog';

const BLOCK_TYPE_LABELS: Record<string, string> = {
  [BlockType.ENTRY_CONDITION]:  'Entry Condition',
  [BlockType.EXIT_CONDITION]:   'Exit Condition',
  [BlockType.RISK_MANAGEMENT]:  'Risk Management',
  [BlockType.TIME_CONSTRAINT]:  'Time Constraint',
  [BlockType.FILTER]:           'Filter',
  [BlockType.INDICATOR]:        'Indicator',
  [BlockType.POSITION_SIZING]:  'Position Sizing',
};

// Signal-type classification mirrors the desktop block_registry_adapter logic.
// EVENT  — pattern/event-driven triggers (e.g. double-top completion, BOS break)
// SIGNAL — indicator crossovers and oscillator-based signals (e.g. MACD, EMA cross)
// CONTEXT — continuous state providers always active in background (e.g. sessions, Fibonacci levels)
// HYBRID — blocks that combine event detection with continuous state (e.g. ICT, Wyckoff)
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

// ─── Structured tooltip content (replaces native title attributes) ────────────
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
const TT_CATEGORY: TooltipContent = {
  title: 'Category Filter',
  body: 'Narrows the library to blocks sharing the same market analysis domain.',
  sections: [
    { header: 'Examples:', items: [
      'PATTERNS — classical chart formations (Cup & Handle, Double Top)',
      'OSCILLATORS — momentum-based indicators (RSI, MACD, Stochastic)',
      'SESSIONS — time-of-day context (London, New York, Asia killzones)',
    ]},
    { header: 'Tip:', items: ['Combine with the Type filter to target a specific block role'] },
  ],
};
const TT_TYPE: TooltipContent = {
  title: 'Block Type Filter',
  body: 'Controls how a block participates in your strategy execution.',
  sections: [
    { header: 'Types:', items: [
      'EVENT — fires once on discrete occurrences (pattern completions, structure breaks)',
      'SIGNAL — continuous indicator scoring directional bias (MACD, RSI, EMA cross)',
      'CONTEXT — always-active background state (sessions, Fibonacci zones, price levels)',
      'HYBRID — combines event detection with continuous state (ICT/SMC, Wyckoff, Elliott Wave)',
    ]},
    { header: 'Tip:', items: [
      'Use EVENT as primary triggers, SIGNAL as confirmation, CONTEXT to qualify the market environment',
    ]},
  ],
};
const TT_PRESET: TooltipContent = {
  title: 'Filter Presets',
  body: 'Saved combinations of search text, category, and type filters for one-click restore.',
  sections: [
    { header: 'How to use:', items: [
      'Select a preset in this dropdown, then click 📂 to apply it',
      'Click 💾 to save the current filter state under a new name',
    ]},
    { header: 'Tip:', items: ['Create presets for views you use often, e.g. "ICT blocks" or "Bullish patterns"'] },
  ],
};
const TT_PRESET_SAVE: TooltipContent = {
  title: 'Save Filter Preset',
  body: 'Captures the current search text, category, and type filter as a named preset.',
  sections: [
    { header: 'Stored in:', items: ['Browser local storage — persists across sessions on this device'] },
    { header: 'Tip:', items: ['Name presets descriptively, e.g. "ICT + HYBRID" or "Pattern EVENT blocks"'] },
  ],
};
const TT_PRESET_LOAD: TooltipContent = {
  title: 'Load Filter Preset',
  body: 'Applies the saved search text, category, and type filter from the selected preset.',
  sections: [
    { header: 'How to use:', items: ['Select a preset in the dropdown first, then click here to activate it'] },
    { header: 'Note:', items: ['Overwrites the current filter state — unsaved filters will be lost'] },
  ],
};
const TT_PRESET_DELETE: TooltipContent = {
  title: 'Delete Filter Preset',
  body: 'Permanently removes the selected preset from local storage.',
  sections: [
    { header: 'How to use:', items: ['Select a preset in the dropdown first, then click here to delete it'] },
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

// ui_visible=false signals are hidden in Standard mode (matches desktop app behaviour).
// Advanced mode shows all signals including ui_visible=false for debugging/exploration.

// Convert WAVE_1_BULLISH → Wave 1 Bullish
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
// SavePresetModal
// ─────────────────────────────────────────────
interface SavePresetModalProps {
  open: boolean;
  onSave: (name: string) => void;
  onCancel: () => void;
}

function SavePresetModal({ open, onSave, onCancel }: SavePresetModalProps) {
  const [value, setValue] = useState('');
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="rounded-lg shadow-2xl border p-5 w-80" style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}>
        <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-dim)' }}>Save Filter Preset</h3>
        <input
          autoFocus
          type="text"
          placeholder="Preset name…"
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && value.trim()) onSave(value.trim()); if (e.key === 'Escape') onCancel(); }}
          className="w-full px-2.5 py-1.5 rounded border text-sm focus:outline-none mb-4"
          style={{ background: 'var(--input-bg)', borderColor: 'var(--input-border)', color: 'var(--input-text)' }}
        />
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="text-xs px-3 py-1.5 rounded border transition-colors"
            style={{ background: 'var(--bg-card)', borderColor: 'var(--border)', color: 'var(--text-secondary)' }}
          >
            Cancel
          </button>
          <button
            onClick={() => { if (value.trim()) onSave(value.trim()); }}
            disabled={!value.trim()}
            className="text-xs px-3 py-1.5 rounded border transition-colors disabled:opacity-40"
            style={{ background: 'var(--accent-blue-dark)', borderColor: 'var(--accent-sky-bright)', color: 'var(--accent-sky)' }}
          >
            Save
          </button>
        </div>
      </div>
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
}

function BlockItem({ definition, onAdd, onAddExit, advancedMode, isHighlighted, onHighlightCleared }: BlockItemProps) {
  const itemRef = useRef<HTMLDivElement>(null);
  const [signalsOpen, setSignalsOpen] = useState(false);
  const [checkedSignals, setCheckedSignals] = useState<Set<string>>(new Set());
  const [addedSignals, setAddedSignals] = useState<Set<string>>(new Set());

  const signals = definition.signals ?? [];
  const visibleSignals = signals.filter(s => s.ui_visible !== false);

  // Auto-expand and scroll into view when highlighted from the strategy panel
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
    if (!advancedMode) {
      setAddedSignals(prev => {
        const next = new Set(prev);
        selected.forEach(s => next.add(s));
        return next;
      });
    }
    setCheckedSignals(new Set());
    onAdd(definition, logic, selected);
  };

  const handleAddExit = () => {
    const selected = checkedSignals.size > 0 ? [...checkedSignals] : visibleSignals.map(s => s.name);
    if (!advancedMode) {
      setAddedSignals(prev => {
        const next = new Set(prev);
        selected.forEach(s => next.add(s));
        return next;
      });
    }
    setCheckedSignals(new Set());
    onAddExit(definition, selected);
  };

  return (
    <div
      ref={itemRef}
      className="rounded-md border mb-1.5 transition-all duration-300"
      style={{
        background: isHighlighted ? 'color-mix(in srgb, var(--accent-sky-bright) 7%, transparent)' : '#1A2335',
        borderColor: isHighlighted ? 'var(--accent-sky-bright)' : '#1A2535',
        boxShadow: isHighlighted ? '0 0 0 2px rgba(14,165,233,0.25)' : undefined,
      }}
    >
      {/* Block name + meta */}
      <div className="px-3 pt-2.5 pb-1.5">
        <div className="flex items-center gap-1.5">
          <span className="text-sm font-medium leading-tight" style={{ color: '#E8F2FF' }}>{definition.name}</span>
        </div>
        <div className="text-xs mt-0.5" style={{ color: '#8A9FBF' }}>
          Category: {definition.category}
          {typeLabel && ` | Type: ${typeLabel}`}
          {weight != null && ` | Weight: ${weight} pts`}
        </div>
      </div>

      {/* Show/hide signals link row */}
      {visibleSignals.length > 0 && (
        <RichTooltip content={TT_SHOW_SIGNALS}>
          <button
            onClick={() => setSignalsOpen(v => !v)}
            className="w-full px-3 pb-2.5 text-left text-xs flex items-center justify-between hover:opacity-80 transition-opacity"
            style={{ color: '#2E8CFF' }}
          >
            <span>{signalsOpen ? `Hide Signals (${visibleSignals.length})` : `Show Signals (${visibleSignals.length})`}</span>
            <ChevronRight
              style={{
                width: 13,
                height: 13,
                flexShrink: 0,
                color: '#2E8CFF',
                transform: signalsOpen ? 'rotate(90deg)' : 'none',
                transition: 'transform 0.2s',
              }}
            />
          </button>
        </RichTooltip>
      )}

      {/* Expanded: signals list + add buttons */}
      {signalsOpen && visibleSignals.length > 0 && (
        <div className="px-3 pb-2 bg-[var(--bg-deep)]">
          {/* Header */}
          <p className="text-xs font-semibold text-sky-400 pt-2 pb-1">Select signals to add:</p>

          {/* Signal list with checkboxes */}
          <div className="space-y-2">
            {visibleSignals.map((sig, i) => {
              const isAdded = !advancedMode && addedSignals.has(sig.name);
              const isChecked = checkedSignals.has(sig.name);
              return (
                <div key={i} className={`pl-1 ${isAdded ? 'opacity-50' : ''}`}>
                  <label className={`flex items-start gap-2 ${isAdded ? 'cursor-default' : 'cursor-pointer'}`}>
                    <input
                      type="checkbox"
                      checked={isChecked}
                      disabled={isAdded}
                      onChange={() => !isAdded && toggleSignal(sig.name)}
                      className="mt-0.5 flex-shrink-0 appearance-none w-3.5 h-3.5 rounded-sm border border-[var(--text-faintest)] cursor-pointer disabled:opacity-50"
                      style={isChecked ? {
                        background: 'var(--accent-sky-bright)',
                        borderColor: 'var(--accent-sky-bright)',
                        backgroundImage: "url(\"data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16' fill='white'%3e%3cpath d='M12.207 4.793a1 1 0 010 1.414l-5 5a1 1 0 01-1.414 0l-2-2a1 1 0 011.414-1.414L6.5 9.086l4.293-4.293a1 1 0 011.414 0z'/%3e%3c/svg%3e\")",
                        backgroundSize: '100% 100%',
                      } : { background: 'transparent' }}
                    />
                    <div className="min-w-0">
                      <span
                        className={`text-xs font-semibold ${isAdded ? 'line-through' : ''}`}
                        style={{ color: isAdded ? 'var(--text-muted)' : 'var(--text-secondary)' }}
                      >
                        {formatSignalName(sig.name)}
                      </span>
                      {sig.occurrences != null && (
                        <span className="font-normal text-xs ml-1.5" style={{ color: 'var(--text-muted)' }}>
                          ({sig.occurrences.toLocaleString()} found, {sig.occurrence_percentage != null ? sig.occurrence_percentage.toFixed(1) : '?'}%)
                        </span>
                      )}
                      {sig.description ? (
                        <div className="text-xs mt-0.5 italic leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{sig.description}</div>
                      ) : null}
                    </div>
                  </label>
                </div>
              );
            })}
          </div>

          {/* Add buttons */}
          <div className="flex gap-1.5 mt-3">
            <RichTooltip content={TT_ADD_AND}>
              <button
                onClick={() => handleAdd('AND')}
                className="flex-1 flex items-center justify-center gap-1 text-xs py-1.5 rounded border border-emerald-800 bg-emerald-900/40 hover:bg-emerald-900/70 text-emerald-300 font-medium transition-colors"
              >
                <Plus size={13} style={{ flexShrink: 0 }} />
                Add as AND (Required)
              </button>
            </RichTooltip>
            <RichTooltip content={TT_ADD_OR}>
              <button
                onClick={() => handleAdd('OR')}
                className="flex-1 flex items-center justify-center gap-1 text-xs py-1.5 rounded border border-blue-800 bg-blue-900/30 hover:bg-blue-900/60 text-blue-300 font-medium transition-colors"
              >
                <Plus size={13} style={{ flexShrink: 0 }} />
                Add as OR (Optional)
              </button>
            </RichTooltip>
            <RichTooltip content={TT_ADD_EXIT}>
              <button
                onClick={handleAddExit}
                className="flex-1 flex items-center justify-center gap-1 text-xs py-1.5 rounded border border-red-800 bg-red-900/30 hover:bg-red-900/60 text-red-300 font-medium transition-colors"
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

  const [searchText, setSearchText] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedType, setSelectedType] = useState<'EVENT' | 'SIGNAL' | 'CONTEXT' | 'HYBRID' | 'all'>('all');
  const [advancedMode, setAdvancedMode] = useState(false);

  // Exit condition dialog
  const [exitPending, setExitPending] = useState<{
    definition: BlockDefinition;
    selectedSignals: string[];
  } | null>(null);

  // When a block is highlighted from the strategy panel, clear filters so it's visible
  useEffect(() => {
    if (!highlightedLibraryBlockId) return;
    setSearchText('');
    setSelectedCategory('all');
    setSelectedType('all');
  }, [highlightedLibraryBlockId]);

  // Presets
  const [presets, setPresets] = useState<FilterPreset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState('');
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  useEffect(() => { setPresets(loadPresets()); }, []);

  const handleSavePreset = useCallback(() => {
    setSaveModalOpen(true);
  }, []);

  const handleConfirmSavePreset = useCallback((name: string) => {
    const preset: FilterPreset = { name, search: searchText, category: selectedCategory, type: selectedType };
    const updated = [...presets.filter(p => p.name !== preset.name), preset];
    savePresets(updated);
    setPresets(updated);
    setSelectedPreset(name);
    setSaveModalOpen(false);
  }, [searchText, selectedCategory, selectedType, presets]);

  const handleLoadPreset = useCallback(() => {
    const preset = presets.find(p => p.name === selectedPreset);
    if (!preset) return;
    setSearchText(preset.search);
    setSelectedCategory(preset.category);
    setSelectedType(preset.type as 'EVENT' | 'SIGNAL' | 'CONTEXT' | 'HYBRID' | 'all');
  }, [presets, selectedPreset]);

  const handleDeletePreset = useCallback(() => {
    if (!selectedPreset) return;
    setDeleteConfirmOpen(true);
  }, [selectedPreset]);

  const handleConfirmDeletePreset = useCallback((result: 'yes' | 'no' | 'cancel') => {
    setDeleteConfirmOpen(false);
    if (result !== 'yes') return;
    const updated = presets.filter(p => p.name !== selectedPreset);
    savePresets(updated);
    setPresets(updated);
    setSelectedPreset('');
  }, [presets, selectedPreset]);

  // Filtered blocks — flat, sorted by category then name.
  // Search supports comma-separated terms: "50, asia, hod" matches blocks containing ANY term.
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

  // All categories for dropdown — format SNAKE_CASE to Title Case for display
  const allCategories = useMemo(() => {
    if (blockCategories.length > 0) return blockCategories.map(c => ({ id: c.id, name: c.name }));
    const cats = new Set(blockLibrary.map(b => b.category));
    return [...cats].sort().map(c => ({
      id: c,
      name: c.replace(/_/g, ' ').replace(/\b\w/g, (ch: string) => ch.toUpperCase()),
    }));
  }, [blockCategories, blockLibrary]);

  // Signal types are computed from category — same logic as the desktop block_registry_adapter.
  // Only show types that have at least one block in the current library.
  const allTypes = useMemo(() => {
    const seen = new Set(blockLibrary.map(b => computeSignalType(b.category)));
    return (['CONTEXT', 'EVENT', 'HYBRID', 'SIGNAL'] as const).filter(t => seen.has(t)).map(t => ({
      value: t,
      label: t.charAt(0) + t.slice(1).toLowerCase(),
    }));
  }, [blockLibrary]);

  // Add block to strategy.
  // Standard mode: signals from the same block definition + logic are merged
  //   into the existing block card rather than creating a duplicate card.
  // Advanced mode: always creates a new separate block card (allows duplicates).
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
                ? { background: 'var(--accent-blue-dark)', color: 'var(--accent-sky)', fontWeight: 600 }
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
                ? { background: 'var(--accent-blue-dark)', color: 'var(--accent-sky)', fontWeight: 600 }
                : { background: 'var(--bg-card)', color: 'var(--text-muted)' }}
            >
              Advanced
            </button>
          </RichTooltip>
        </div>
      </div>

      {/* Search + Filters — 2 rows, labels fixed-width so inputs align */}
      <div className="px-3 pt-3 pb-2 space-y-1.5 flex-shrink-0 border-b border-[var(--border)]" style={{ background: 'var(--bg-panel)' }}>
        {/* Row 1: Search */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 text-xs flex-shrink-0" style={{ color: '#9AA0A6', width: 68, justifyContent: 'flex-end' }}>
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
              style={{ background: '#111720', borderColor: '#253040', color: 'var(--input-text)' }}
            />
          </RichTooltip>
        </div>

        {/* Row 2: Category + Type dropdowns — same label width so controls align with search input */}
        <div className="flex items-center gap-1.5">
          <div className="flex items-center gap-1.5 text-xs flex-shrink-0" style={{ color: '#9AA0A6', width: 68, justifyContent: 'flex-end' }}>
            <Filter size={13} style={{ flexShrink: 0 }} />
            <span>Filter:</span>
          </div>
          <RichTooltip content={TT_CATEGORY}>
            <select
              value={selectedCategory}
              onChange={e => setSelectedCategory(e.target.value)}
              className="flex-[1.5] min-w-0 px-1.5 py-1 rounded border text-xs focus:outline-none"
              style={{ background: '#111720', borderColor: '#253040', color: 'var(--input-text)' }}
            >
              <option value="all">All Categories</option>
              {allCategories.map(c => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </RichTooltip>
          <RichTooltip content={TT_TYPE}>
            <select
              value={selectedType}
              onChange={e => setSelectedType(e.target.value as 'EVENT' | 'SIGNAL' | 'CONTEXT' | 'HYBRID' | 'all')}
              className="flex-[0.75] min-w-0 px-1.5 py-1 rounded border text-xs focus:outline-none"
              style={{ background: '#111720', borderColor: '#253040', color: 'var(--input-text)' }}
            >
              <option value="all">All Types</option>
              {allTypes.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </RichTooltip>
          <RichTooltip content={TT_PRESET}>
            <select
              value={selectedPreset}
              onChange={e => setSelectedPreset(e.target.value)}
              className="flex-[3] min-w-0 px-1.5 py-1 rounded border text-xs focus:outline-none"
              style={{ background: 'var(--bg-card)', borderColor: 'var(--border)', color: 'var(--text-dim)' }}
            >
              <option value="">— Preset —</option>
              {presets.map(p => <option key={p.name} value={p.name}>{p.name}</option>)}
            </select>
          </RichTooltip>
          <RichTooltip content={TT_PRESET_SAVE}>
            <button onClick={handleSavePreset}
              className="flex items-center justify-center px-1.5 py-1 rounded border flex-shrink-0 hover:opacity-80"
              style={{ background: 'var(--bg-card)', borderColor: 'var(--border)', color: 'var(--text-dim)' }}>
              <Save size={13} />
            </button>
          </RichTooltip>
          <RichTooltip content={TT_PRESET_LOAD}>
            <button onClick={handleLoadPreset} disabled={!selectedPreset}
              className="flex items-center justify-center px-1.5 py-1 rounded border flex-shrink-0 disabled:opacity-40 hover:opacity-80"
              style={{ background: 'var(--bg-card)', borderColor: 'var(--border)', color: 'var(--text-dim)' }}>
              <Folder size={13} />
            </button>
          </RichTooltip>
          <RichTooltip content={TT_PRESET_DELETE}>
            <button onClick={handleDeletePreset} disabled={!selectedPreset}
              className="flex items-center justify-center px-1.5 py-1 rounded border flex-shrink-0 disabled:opacity-40 hover:opacity-80"
              style={{ background: 'var(--bg-card)', borderColor: 'var(--border)', color: 'var(--text-dim)' }}>
              <Trash2 size={13} />
            </button>
          </RichTooltip>
        </div>
      </div>

      {/* Block list — flat, sorted */}
      <div className="flex-1 overflow-y-auto px-3 py-3" style={{ background: 'var(--bg-deep)', scrollbarWidth: 'thin', scrollbarColor: 'var(--border) transparent' }}>
        {isLoadingLibrary ? (
          <div className="flex flex-col items-center justify-center py-10 gap-2">
            <div className="w-6 h-6 border-2 border-zinc-600 border-t-sky-400 rounded-full animate-spin" />
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Loading block library…</p>
          </div>
        ) : filteredBlocks.length === 0 ? (
          <p className="text-xs text-center py-8" style={{ color: 'var(--text-secondary)' }}>No blocks match the current filters</p>
        ) : (
          filteredBlocks.map(block => (
            <BlockItem
              key={block.id}
              definition={block}
              onAdd={handleAdd}
              onAddExit={handleAddExit}
              advancedMode={advancedMode}
              isHighlighted={highlightedLibraryBlockId === block.id}
              onHighlightCleared={() => highlightLibraryBlock(null)}
            />
          ))
        )}
      </div>

      {/* Footer count */}
      <div className="px-3 py-2 border-t border-[var(--border)] flex-shrink-0 flex items-center justify-between" style={{ background: 'var(--bg-panel)' }}>
        <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
          {filteredBlocks.length} / {blockLibrary.length} blocks
        </p>
        {currentStrategy && (
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            {currentStrategy.blocks.length} in strategy
          </p>
        )}
      </div>

      <SavePresetModal
        open={saveModalOpen}
        onSave={handleConfirmSavePreset}
        onCancel={() => setSaveModalOpen(false)}
      />

      <QuestionDialog
        open={deleteConfirmOpen}
        icon="⚠️"
        title="Delete Filter Preset"
        heading={`Delete "${selectedPreset}"?`}
        message="This preset will be permanently removed from local storage and cannot be recovered."
        onResult={handleConfirmDeletePreset}
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
