'use client';

import { Strategy } from '@/lib/strategy-builder/types';
import type {
  RecommendationCardData,
  RecommendationChange,
  RecommendationFooterMetrics,
} from './RecommendationCard';
import type { RecommendationCategoryId } from './recommendationCategoryPalette';
import type { RecommendationDiffParam } from './RecommendationDiff';
import { ProjectedDelta } from './strategyImpactKpi';

// ── Recommendation parsing & rendering ───────────────────────────────────

export interface ParsedRec {
  /** Stable id derived from the rec text (index + hash). */
  id: string;
  title: string;
  summary: string;
  raw: string;
  /** Structured type extracted from "Type:" line (e.g. ADJUST_PARAM, ADD_SIGNAL). */
  type: string;
  /** Optional fields extracted from "Confidence: …" / "Rationale: …" lines. */
  confidence?: string;
  rationale?: string;
  /** Key:value parameter suggestions extracted from the block. */
  suggestedParams: Array<{ key: string; value: string }>;
  // Structured fields forwarded to the auto-apply orchestrator.
  block?: string;
  signal?: string;
  parameter?: string;
  suggestedValue?: string;
  // Presentational overrides (mockup-verbatim demo path). When present these
  // take precedence over the derived defaults in toCardData so the card face
  // matches the approved Current Analysis mockup exactly.
  categoryIdOverride?: RecommendationCategoryId;
  categoryLabel?: string;
  deltaLabelOverride?: string;
  deltaNegativeOverride?: boolean;
  change?: RecommendationChange;
  affectsLine?: string;
  footerMetrics?: RecommendationFooterMetrics;
  insight?: boolean;
  insightBox?: string;
}

/**
 * Extract the value side of a "Label: value" or "**Label**: value" line from
 * a recommendation block. The match is line-bounded so we don't accidentally
 * pull a body paragraph in.
 */
export function tryExtractField(block: string, label: string): string | undefined {
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const re = new RegExp(
    `(?:^|\\n)\\s*(?:\\*\\*)?${escaped}(?:\\*\\*)?\\s*[:\\-]\\s*([^\\n]+)`,
    'i',
  );
  const m = block.match(re);
  if (!m) return undefined;
  const value = m[1].trim();
  return value.length === 0 ? undefined : value;
}

export function parseSuggestedParams(block: string): Array<{ key: string; value: string }> {
  const params: Array<{ key: string; value: string }> = [];
  const seen = new Set<string>();
  const lines = block.split(/\r?\n/);
  for (const line of lines) {
    const m = line.match(/^\s*-\s*\*\*([^*]+)\*\*\s*[:=]\s*(.+?)\s*$/);
    if (!m) continue;
    const key = m[1].trim();
    const value = m[2].trim();
    if (!key || !value) continue;
    const dedupe = key.toLowerCase();
    if (seen.has(dedupe)) continue;
    seen.add(dedupe);
    params.push({ key, value });
  }
  return params;
}

export function findParamInStrategy(strategy: Strategy, paramKey: string): string | undefined {
  for (const block of (strategy.blocks ?? [])) {
    const data = block.data;
    if (!data || typeof data !== 'object') continue;
    for (const [key, value] of Object.entries(data)) {
      if (key === paramKey && (typeof value === 'number' || typeof value === 'string')) {
        return String(value);
      }
    }
  }
  const settings = strategy.settings;
  if (settings && typeof settings === 'object') {
    for (const [key, value] of Object.entries(settings as unknown as Record<string, unknown>)) {
      if (key === paramKey && (typeof value === 'number' || typeof value === 'string')) {
        return String(value);
      }
    }
  }
  return undefined;
}

export function deriveTitle(block: string, index: number): string {
  // Try the first markdown heading inside the block.
  const heading = block.match(/^\s*#{1,6}\s+(.+?)\s*$/m);
  if (heading) {
    const t = heading[1].replace(/\*+/g, '').trim();
    if (t.length > 0 && t.length <= 120) return t;
  }
  // Try the first **Bold** prefix.
  const bold = block.match(/^\s*\*\*([^*]+)\*\*/);
  if (bold) {
    const t = bold[1].trim();
    if (t.length > 0 && t.length <= 120) return t;
  }
  // Try "1. Title" / "1) Title" prefix.
  const numbered = block.match(/^\s*\d+[.)]\s+([^\n]{1,120})/);
  if (numbered) {
    const t = numbered[1].replace(/[*_`]/g, '').trim();
    if (t.length > 0) return t;
  }
  // Fallback: first non-empty line, trimmed and capped.
  const firstLine =
    block
      .split(/\r?\n/)
      .map((l) => l.trim())
      .find((l) => l.length > 0) ?? '';
  return firstLine.length === 0
    ? `Recommendation #${index + 1}`
    : firstLine.replace(/[*_`#]/g, '').slice(0, 80) || `Recommendation #${index + 1}`;
}

export function deriveSummary(block: string, maxLen = 220): string {
  // Strip headings, list markers, and inline markdown noise to get a one-liner.
  const stripped = block
    .replace(/^\s*#{1,6}\s+.+$/gm, '')
    .replace(/^\s*[-*+]\s+/gm, '')
    .replace(/^\s*\d+[.)]\s+/gm, '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\s+/g, ' ')
    .trim();
  if (stripped.length === 0) return '';
  if (stripped.length <= maxLen) return stripped;
  return `${stripped.slice(0, maxLen - 1).trimEnd()}…`;
}

// BTCAAAAA-37774 Sprint A2 — optional projected-impact fields per rec block.
export function projectedImpactFromRecRaw(raw: string): ProjectedDelta {
  const pick = (label: string): number | undefined => {
    const v = tryExtractField(raw, label);
    if (v === undefined) return undefined;
    const m = v.match(/-?\d+(?:\.\d+)?/);
    if (!m) return undefined;
    const n = Number(m[0]);
    if (!Number.isFinite(n)) return undefined;
    if (/%|pp/i.test(v)) return n / 100;
    return n;
  };
  const out: ProjectedDelta = {};
  const wr = pick('Projected Win Rate') ?? pick('Projected WR');
  if (wr !== undefined) out.winRate = wr;
  const nl = pick('Projected Net Liquidity') ?? pick('Projected PnL');
  if (nl !== undefined) out.netLiquidity = nl;
  const dd = pick('Projected Drawdown') ?? pick('Projected DD');
  if (dd !== undefined) out.maxDrawdown = dd;
  const pf = pick('Projected Profit Factor') ?? pick('Projected PF');
  if (pf !== undefined) out.profitFactor = pf;
  const en = pick('Projected Entries');
  if (en !== undefined) out.entries = en;
  return out;
}

// BTCAAAAA-38438: hoisted from the inline .map() so the mapper below can
// classify recs without recreating the Set on every render.
export const STRUCTURAL_TYPES = new Set(['ADD_SIGNAL', 'REMOVE_SIGNAL', 'ADD_BLOCK', 'REMOVE_BLOCK']);

// BTCAAAAA-38438: map a ParsedRec.type string to a RecommendationCategoryId
export function categoryIdFromRecType(type: string | undefined): RecommendationCategoryId {
  const t = (type ?? '').toUpperCase();
  if (t.includes('ADJUST_PARAM') || t.includes('ADJUST')) return 'risk';
  if (t.includes('ADD_SIGNAL') || t.includes('REMOVE_SIGNAL') || t.includes('SIGNAL')) return 'signal';
  if (t.includes('ADD_BLOCK') || t.includes('REMOVE_BLOCK') || t.includes('REGIME')) return 'regime';
  if (t.includes('EXIT')) return 'exit';
  if (t.includes('ENTRY')) return 'entry';
  return 'signal';
}

// BTCAAAAA-38438: format a projected-impact delta as a short label
export function formatDeltaLabel(delta: ProjectedDelta): { label: string; negative: boolean } {
  if (delta.winRate !== undefined) {
    const v = delta.winRate;
    const pct = Math.abs(v) < 1 ? `${(v * 100).toFixed(1)}pp` : `${v.toFixed(1)}pp`;
    return { label: `${v >= 0 ? '+' : ''}${pct} WR`, negative: v < 0 };
  }
  if (delta.netLiquidity !== undefined) {
    const v = delta.netLiquidity;
    return { label: `${v >= 0 ? '+' : ''}${v.toFixed(1)} PnL`, negative: v < 0 };
  }
  if (delta.maxDrawdown !== undefined) {
    const v = delta.maxDrawdown;
    return { label: `${v >= 0 ? '+' : ''}${v.toFixed(1)} DD`, negative: v < 0 };
  }
  if (delta.profitFactor !== undefined) {
    const v = delta.profitFactor;
    return { label: `${v >= 0 ? '+' : ''}${v.toFixed(2)} PF`, negative: v < 0 };
  }
  if (delta.entries !== undefined) {
    const v = delta.entries;
    return { label: `${v >= 0 ? '+' : ''}${Math.round(v)} entries`, negative: v < 0 };
  }
  return { label: '—', negative: false };
}

export function toCardData(rec: ParsedRec, ctx: {
  applied: boolean;
  isApplyingThis: boolean;
  isAutoApplicable: boolean;
  onToggleApplied: () => void;
  preApplySnapshots: ReadonlyArray<[string, Strategy]>;
  analysisId: string;
}): RecommendationCardData {
  const delta = projectedImpactFromRecRaw(rec.raw);
  const { label: deltaLabel, negative: deltaNegative } = formatDeltaLabel(delta);
  const codeLines = rec.suggestedParams.length > 0
    ? rec.suggestedParams.map((p) => `${p.key} = ${p.value}`)
    : rec.parameter && rec.suggestedValue
      ? [`${rec.parameter} = ${rec.suggestedValue}`]
      : [`type: ${rec.type ?? 'recommendation'}`];

  // B3 (BTCAAAAA-38467): when the rec is applied, compute the per-param
  // before/after diff from the pre-apply snapshot so RecommendationCard can
  // render its inline <RecommendationDiff />.
  let appliedDiff: ReadonlyArray<RecommendationDiffParam> | undefined;
  if (ctx.applied) {
    const snapshotEntry = ctx.preApplySnapshots.find(([id]) => id === rec.id);
    if (snapshotEntry) {
      const [, preStrategy] = snapshotEntry;
      const paramSource: Array<{ key: string; value: string }> =
        rec.suggestedParams.length > 0
          ? rec.suggestedParams
          : rec.parameter && rec.suggestedValue
            ? [{ key: rec.parameter, value: rec.suggestedValue }]
            : [];
      appliedDiff = paramSource
        .map((p) => ({
          key: p.key,
          before: findParamInStrategy(preStrategy, p.key),
          after: p.value,
        }))
        .filter(
          (d): d is RecommendationDiffParam =>
            d.before !== undefined && d.before !== d.after,
        );
      if (appliedDiff.length === 0) appliedDiff = undefined;
    }
  }

  return {
    id: rec.id,
    categoryId: rec.categoryIdOverride ?? categoryIdFromRecType(rec.type),
    categoryLabel: rec.categoryLabel,
    deltaLabel: rec.deltaLabelOverride ?? deltaLabel,
    deltaNegative: rec.deltaNegativeOverride ?? deltaNegative,
    title: rec.title,
    description: rec.rationale ?? rec.summary,
    codeLines,
    change: rec.change,
    affectsLine: rec.affectsLine,
    footerMetrics: rec.footerMetrics,
    insight: rec.insight,
    insightBox: rec.insightBox,
    applied: ctx.applied,
    onToggleApplied: ctx.onToggleApplied,
    disabled: ctx.isApplyingThis || !ctx.isAutoApplicable,
    appliedDiff,
    dataAttributes: {
      'data-testid': 'ai-recs-toggle-card',
      'data-rec-id': rec.id,
      'data-applied': ctx.applied ? 'true' : 'false',
      'data-auto-applicable': ctx.isAutoApplicable ? 'true' : 'false',
    },
    analysisId: ctx.analysisId,
  };
}

export function simpleHash(input: string): string {
  let h = 5381;
  for (let i = 0; i < input.length; i++) {
    h = ((h << 5) + h + input.charCodeAt(i)) | 0;
  }
  // Convert to unsigned hex so it's always a stable id substring.
  return (h >>> 0).toString(16);
}

export function parseSingleRec(block: string, index: number): ParsedRec {
  const rawSignal = tryExtractField(block, 'Signal');
  return {
    id: `rec-${index}-${simpleHash(block)}`,
    title: deriveTitle(block, index),
    summary: deriveSummary(block),
    raw: block.trim(),
    type: tryExtractField(block, 'Type') ?? 'recommendation',
    confidence: tryExtractField(block, 'Confidence'),
    rationale: tryExtractField(block, 'Rationale'),
    suggestedParams: parseSuggestedParams(block),
    block: tryExtractField(block, 'Block'),
    signal: rawSignal && !/^n\/a$/i.test(rawSignal) ? rawSignal : undefined,
    parameter: tryExtractField(block, 'Parameter'),
    suggestedValue: tryExtractField(block, 'Suggested Value'),
  };
}

/**
 * Split a free-form recommendations block into individual recs.
 */
export function parseRecommendations(text: string): ParsedRec[] {
  const trimmed = text.trim();
  if (!trimmed) return [];

  const trySplit = (re: RegExp): string[] | null => {
    const parts = trimmed.split(re);
    if (parts.length < 2) return null;
    const nonEmpty = parts.map((p) => p.trim()).filter((p) => p.length > 0);
    return nonEmpty.length >= 2 ? nonEmpty : null;
  };

  // 1) Numbered list: "1." / "1)" at the start of a line.
  const numbered = trySplit(/(?=^\s*\d+[.)]\s+)/gm);
  if (numbered) return numbered.map((b, i) => parseSingleRec(b, i));

  // 2) Markdown headings (##/###) at the start of a line.
  const headed = trySplit(/(?=^\s*#{2,6}\s+)/gm);
  if (headed) return headed.map((b, i) => parseSingleRec(b, i));

  // 3) Horizontal rule separators: --- or *** on their own line.
  const ruleSplit = trySplit(/^\s*(?:---|\*\*\*|___)\s*$/gm);
  if (ruleSplit) return ruleSplit.map((b, i) => parseSingleRec(b, i));

  // 4) Blank-line paragraph split: only treat as multiple recs when the
  //    paragraphs look like a list (each starts with - or *).
  const paragraphs = trimmed
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter((p) => p.length > 0);
  if (paragraphs.length >= 2 && paragraphs.every((p) => /^\s*[-*+]/.test(p))) {
    return paragraphs.map((b, i) => parseSingleRec(b, i));
  }

  // 5) Fallback: whole block as a single rec.
  return [parseSingleRec(trimmed, 0)];
}
