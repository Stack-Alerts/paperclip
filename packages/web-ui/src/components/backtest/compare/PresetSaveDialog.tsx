'use client';

import { useState, useRef, useEffect } from 'react';
import { X, Bookmark, Tag, FolderOpen, Plus } from 'lucide-react';
import type { BacktestRunRecord } from '@/lib/strategy-builder/types';
import { savePreset, listGroups, listTags, loadPresets } from '@/lib/config-presets';

interface PresetSaveDialogProps {
  record: BacktestRunRecord;
  onSaved: () => void;
  onClose: () => void;
}

export function PresetSaveDialog({ record, onSaved, onClose }: PresetSaveDialogProps) {
  const existingPresets = loadPresets();
  const existingGroups = listGroups(existingPresets);
  const existingTags = listTags(existingPresets);

  const defaultName = record.strategyName
    ? `${record.strategyName} preset`
    : 'My preset';

  const [name, setName] = useState(defaultName);
  const [group, setGroup] = useState('');
  const [tagInput, setTagInput] = useState('');
  const [tags, setTags] = useState<string[]>([]);

  const nameRef = useRef<HTMLInputElement>(null);
  useEffect(() => { nameRef.current?.select(); }, []);

  function addTag(raw: string) {
    const t = raw.trim();
    if (t && !tags.includes(t)) setTags(prev => [...prev, t]);
    setTagInput('');
  }

  function handleTagKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      addTag(tagInput);
    } else if (e.key === 'Backspace' && !tagInput && tags.length > 0) {
      setTags(prev => prev.slice(0, -1));
    }
  }

  function handleSave() {
    if (!record.fullConfig) return;
    savePreset(name, group, tags, record.fullConfig, record.result, record.strategyName);
    onSaved();
    onClose();
  }

  const fmtPct = (n: number) => `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`;
  const r = record.result;

  return (
    // Backdrop
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'rgba(0,0,0,0.5)' }}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="rounded-lg shadow-2xl w-[420px] flex flex-col"
        style={{ background: 'var(--bg-card)', border: '1px solid var(--border-strong)' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
          <div className="flex items-center gap-2">
            <Bookmark size={15} style={{ color: 'var(--accent-blue)' }} />
            <span className="text-sm font-semibold" style={{ color: 'var(--text-secondary)' }}>Save as preset</span>
          </div>
          <button onClick={onClose} style={{ color: 'var(--text-faint)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-faint)')}
          >
            <X size={14} />
          </button>
        </div>

        {/* Headline metrics */}
        <div className="px-4 py-2.5 flex items-center gap-4" style={{ background: 'var(--bg-deep)', borderBottom: '1px solid var(--border)' }}>
          <span className="text-sm font-bold tabular-nums" style={{ color: r.returnPercentage >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
            {fmtPct(r.returnPercentage)}
          </span>
          <span className="text-xs tabular-nums" style={{ color: 'var(--text-muted)' }}>
            WR {(r.winRate * 100).toFixed(1)}%
          </span>
          <span className="text-xs tabular-nums" style={{ color: 'var(--text-muted)' }}>
            {r.totalTrades} trades
          </span>
          <span className="text-xs tabular-nums" style={{ color: 'var(--accent-orange, #f97316)' }}>
            DD {(r.maxDrawdown * 100).toFixed(1)}%
          </span>
        </div>

        {/* Form */}
        <div className="px-4 py-3 space-y-3">
          {/* Name */}
          <div>
            <label className="text-xs font-medium block mb-1" style={{ color: 'var(--text-muted)' }}>
              Preset name
            </label>
            <input
              ref={nameRef}
              value={name}
              onChange={e => setName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSave()}
              className="w-full rounded px-2.5 py-1.5 text-sm focus:outline-none"
              style={{ background: 'var(--bg-deep)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
              placeholder="Give this preset a name…"
              maxLength={80}
            />
          </div>

          {/* Group */}
          <div>
            <label className="text-xs font-medium flex items-center gap-1 mb-1" style={{ color: 'var(--text-muted)' }}>
              <FolderOpen size={11} /> Group <span style={{ color: 'var(--text-faint)' }}>(optional)</span>
            </label>
            <input
              value={group}
              onChange={e => setGroup(e.target.value)}
              className="w-full rounded px-2.5 py-1.5 text-sm focus:outline-none"
              style={{ background: 'var(--bg-deep)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
              placeholder="e.g. High win-rate, BTC scalp…"
              list="preset-groups"
              maxLength={60}
            />
            {existingGroups.length > 0 && (
              <datalist id="preset-groups">
                {existingGroups.map(g => <option key={g} value={g} />)}
              </datalist>
            )}
          </div>

          {/* Tags */}
          <div>
            <label className="text-xs font-medium flex items-center gap-1 mb-1" style={{ color: 'var(--text-muted)' }}>
              <Tag size={11} /> Tags <span style={{ color: 'var(--text-faint)' }}>(optional — press Enter or comma to add)</span>
            </label>
            <div
              className="flex flex-wrap gap-1 rounded px-2 py-1.5 min-h-[34px]"
              style={{ background: 'var(--bg-deep)', border: '1px solid var(--border)', cursor: 'text' }}
              onClick={() => document.getElementById('tag-input')?.focus()}
            >
              {tags.map(t => (
                <span
                  key={t}
                  className="flex items-center gap-0.5 text-[11px] px-1.5 py-0.5 rounded-full"
                  style={{ background: 'rgba(46,140,255,0.12)', color: 'var(--accent-blue)', border: '1px solid rgba(46,140,255,0.3)' }}
                >
                  {t}
                  <button
                    onClick={e => { e.stopPropagation(); setTags(prev => prev.filter(x => x !== t)); }}
                    className="ml-0.5 leading-none"
                    style={{ color: 'var(--accent-blue)', opacity: 0.7 }}
                  >
                    <X size={9} />
                  </button>
                </span>
              ))}
              <input
                id="tag-input"
                value={tagInput}
                onChange={e => setTagInput(e.target.value)}
                onKeyDown={handleTagKey}
                onBlur={() => { if (tagInput.trim()) addTag(tagInput); }}
                className="flex-1 min-w-[80px] bg-transparent text-xs focus:outline-none"
                style={{ color: 'var(--text-secondary)' }}
                placeholder={tags.length === 0 ? 'conservative, 4h, bull…' : ''}
                list="preset-tags"
              />
              {existingTags.length > 0 && (
                <datalist id="preset-tags">
                  {existingTags.filter(t => !tags.includes(t)).map(t => <option key={t} value={t} />)}
                </datalist>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-4 py-3" style={{ borderTop: '1px solid var(--border)' }}>
          <button
            onClick={onClose}
            className="text-xs px-3 py-1.5 rounded"
            style={{ color: 'var(--text-muted)', border: '1px solid var(--border)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!name.trim()}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded font-medium"
            style={{
              background: name.trim() ? 'var(--accent-blue)' : 'var(--bg-elevated)',
              color: name.trim() ? '#fff' : 'var(--text-faint)',
              border: 'none',
              cursor: name.trim() ? 'pointer' : 'not-allowed',
            }}
          >
            <Plus size={11} />Save preset
          </button>
        </div>
      </div>
    </div>
  );
}
