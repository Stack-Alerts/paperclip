import type { AiRecsHistoryEntry } from '@/hooks/useAiRecsHistory';

export type AfterChangesStatus = 'recommended' | 'applied' | 'staged-from-prior';

export interface AfterChangesItem {
  /** Stable key for React lists. */
  key: string;
  /** Rec id matching the current card (when present) or the prior entry. */
  recId: string;
  title: string;
  status: AfterChangesStatus;
  /**
   * When true, this item came from a prior history entry and there is no
   * matching card in today's analysis — UI should render a "carried over"
   * tag + link back to the originating entry id.
   */
  carriedOver: boolean;
  /** ID of the originating history entry (only set for staged-from-prior). */
  originHistoryEntryId?: string;
}

export interface CurrentRecRef {
  id: string;
  title: string;
}

function previewTitle(block: string, fallback: string): string {
  const heading = block.match(/^\s*#{1,6}\s+(.+?)\s*$/m);
  if (heading) {
    const t = heading[1].replace(/\*+/g, '').trim();
    if (t.length > 0 && t.length <= 120) return t;
  }
  const bold = block.match(/^\s*\*\*([^*]+)\*\*/);
  if (bold) {
    const t = bold[1].trim();
    if (t.length > 0 && t.length <= 120) return t;
  }
  const numbered = block.match(/^\s*\d+[.)]\s+([^\n]{1,120})/);
  if (numbered) {
    const t = numbered[1].replace(/[*_`]/g, '').trim();
    if (t.length > 0) return t;
  }
  const firstLine =
    block
      .split(/\r?\n/)
      .map((l) => l.trim())
      .find((l) => l.length > 0) ?? '';
  return firstLine.length === 0
    ? fallback
    : firstLine.replace(/[*_`#]/g, '').slice(0, 80) || fallback;
}

function normalizeTitle(title: string): string {
  return title.toLowerCase().replace(/\s+/g, ' ').trim();
}

function extractPriorRecs(entry: AiRecsHistoryEntry): Array<{ id: string; title: string }> {
  const text = entry.recommendations.trim();
  if (!text) return [];
  const parts = text
    .split(/(?=^\s*\d+[.)]\s+)/gm)
    .map((p) => p.trim())
    .filter((p) => p.length > 0);
  if (parts.length >= 2) {
    return parts.map((block, i) => ({
      id: `${entry.id}:rec-${i}`,
      title: previewTitle(block, `Recommendation #${i + 1}`),
    }));
  }
  return [{
    id: `${entry.id}:rec-0`,
    title: previewTitle(text, entry.summary || 'Prior recommendation'),
  }];
}

/**
 * Merge today's parsed recommendation cards with staged items carried over
 * from prior history entries for the same strategy. A current rec whose
 * normalized title matches a prior applied rec is surfaced ONCE (as the
 * current card); prior recs with no match in today's set carry forward as
 * `staged-from-prior` with a link to their originating entry.
 *
 * `historyEntries` should already be sorted most-recent first. Only
 * entries with status === 'applied' are eligible to carry forward.
 */
export function mergeStrategyAfterChanges(input: {
  currentRecs: CurrentRecRef[];
  appliedRecIds: ReadonlyArray<string>;
  historyEntries: ReadonlyArray<AiRecsHistoryEntry>;
  currentStrategyName?: string | null;
}): AfterChangesItem[] {
  const { currentRecs, appliedRecIds, historyEntries, currentStrategyName } = input;
  const appliedSet = new Set(appliedRecIds);
  const currentTitleSet = new Set(currentRecs.map((r) => normalizeTitle(r.title)));

  const items: AfterChangesItem[] = currentRecs.map((rec) => ({
    key: `current:${rec.id}`,
    recId: rec.id,
    title: rec.title,
    status: appliedSet.has(rec.id) ? 'applied' : 'recommended',
    carriedOver: false,
  }));

  const priorSeen = new Set<string>();
  for (const entry of historyEntries) {
    if (entry.status !== 'applied') continue;
    if (
      currentStrategyName &&
      entry.strategyName &&
      entry.strategyName !== currentStrategyName
    ) {
      continue;
    }
    for (const prior of extractPriorRecs(entry)) {
      const norm = normalizeTitle(prior.title);
      if (!norm) continue;
      if (currentTitleSet.has(norm)) continue;
      if (priorSeen.has(norm)) continue;
      priorSeen.add(norm);
      items.push({
        key: `prior:${prior.id}`,
        recId: prior.id,
        title: prior.title,
        status: 'staged-from-prior',
        carriedOver: true,
        originHistoryEntryId: entry.id,
      });
    }
  }

  return items;
}
