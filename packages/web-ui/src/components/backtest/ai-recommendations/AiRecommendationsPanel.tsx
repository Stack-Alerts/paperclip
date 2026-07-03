'use client';

import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { X, ExternalLink } from 'lucide-react';
import { BacktestResult, Strategy } from '@/lib/strategy-builder/types';
import { useAiSettings } from '@/hooks/useAiSettings';
import { useAiProviderAvailability } from '@/hooks/useAiProviderAvailability';
import { useAiRecsHistory, AiRecsHistoryEntry, HistorySnapshotKpis } from '@/hooks/useAiRecsHistory';
import {
  AI_RECS_CACHE_VERSION,
  CachedAnalysis,
  readRecsCache,
  writeRecsCache,
  readIsAdminFromAuthToken,
} from './cacheUtils';
import { CollapsibleSection, PreviewText } from './CollapsibleSection';
import { detectConflicts } from './conflictDetector';
import {
  formatStrategyConfig,
  formatBacktestConfig,
  formatTrades,
  formatMetrics,
  buildRequestPayload,
  parseAnalysisResponse,
  confidenceToUplift,
} from './analysisUtils';
import { HistoryView } from './HistoryView';
import { ConfirmationModal } from './ConfirmationModal';
import {
  executeApply,
  type ApplyOrchestratorDeps,
} from './applyOrchestrator';
import {
  classifyPreflight,
  scrollToBacktestButton,
  DEFAULT_SETTINGS_HREF,
  type PreflightError,
} from './preflightValidation';
import { ReverseViewBanner } from './ReverseViewBanner';
import {
  DEFAULT_CONFIDENCE_FLOOR,
  meetsConfidenceFloor,
} from './confidenceFloor';
import {
  buildDiagnoseRows,
  buildStagedRecsSentence,
  type StagedRecSummary,
} from './diagnoseMetrics';
import {
  extractReverseViewPattern,
  ReverseViewInput,
} from './reverseViewPattern';
import { StrategyImpactKpiBar, type ReProjectFn } from './StrategyImpactKpiBar';
import {
  AppliedRecImpact,
  deriveBaselineKpis,
  reProjectFromServer,
  type KpiSet,
} from './strategyImpactKpi';
import { computeReanalyzeHash } from './dirtyHash';
import { buildAiRecsSystemPrompt } from './prompts/systemPrompt';
import { StrategyAfterChangesRail } from './StrategyAfterChangesRail';
import type { DemoLeg } from './StrategyAfterChangesRail';
import { mergeStrategyAfterChanges } from './strategyAfterChangesMerge';
import { RecommendationsRow } from './RecommendationsRow';
import { OptimizationGoalModal } from './OptimizationGoalModal';
import { DiagnosePane } from './DiagnosisCard';
import {
  type ParsedRec,
  parseRecommendations,
  toCardData,
  projectedImpactFromRecRaw,
  STRUCTURAL_TYPES,
} from './RecommendationList';

type SendPhase =
  | 'idle'
  | 'building-request'
  | 'sending'
  | 'awaiting-provider'
  | 'done'
  | 'error';

interface PhaseInfo {
  percent: number;
  label: string;
}

const PHASE_INFO: Record<Exclude<SendPhase, 'idle' | 'error'>, PhaseInfo> = {
  'building-request': { percent: 15, label: 'Stage 1/4: Packaging request…' },
  sending: { percent: 35, label: 'Stage 2/4: Sending to AI provider…' },
  'awaiting-provider': { percent: 75, label: 'Stage 3/4: Awaiting provider response…' },
  done: { percent: 100, label: 'Stage 4/4: Complete' },
};

// AC8: rough ETA shown next to the percent while we are waiting for the
// provider to respond. Starts at 60s and counts down; once it passes zero
// it continues into negative numbers (e.g. -5s) — the request is never
// aborted by the countdown; the negative value signals the response is
// taking longer than estimated without killing the in-flight call.
const AWAITING_PROVIDER_ETA_SECONDS = 60;

// AC10: how long the green "Applied" banner stays visible before fading out.
const APPLY_SUCCESS_DISMISS_MS = 3000;

// BTCAAAAA-36917 v4 UX: hardcoded sample payload for the empty-state
// "Preview the new layout" + "Load demo data" affordances. The preview card
// renders a single rec without touching aiAnalysis so the v3 cache stays
// clean; the demo path populates aiAnalysis but is guarded inside the cache
// persistence effect so the demo data never leaks into sessionStorage.
const SAMPLE_DIAGNOSIS =
  "Strategy shows modest profitability with a healthy win rate, but a long "
  + "drawdown between Apr-Jun suggests the trend filter is too tight in "
  + "ranging markets. Consider relaxing the EMA window or adding a "
  + "volatility regime detector.";

const SAMPLE_RECOMMENDATIONS =
  "1. Widen the EMA trend filter window\n"
  + "   Type: signal\n"
  + "   Rationale: 50-period EMA is too restrictive in the current chop; "
  + "wider window lets more setups through.\n"
  + "   Confidence: high\n"
  + "   - **ema_window**: 100\n"
  + "   - **min_atr**: 250\n"
  + "\n"
  + "2. Add volatility regime block\n"
  + "   Type: building-block\n"
  + "   Rationale: regime detector reduces whipsaw losses during low-vol "
  + "consolidation.\n"
  + "   Confidence: medium\n"
  + "   - **atr_period**: 14\n"
  + "   - **regime_threshold**: 0.6\n"
  + "\n"
  + "3. Tighten the stop loss to 1.5x ATR\n"
  + "   Type: risk\n"
  + "   Rationale: fixed-percent stop gives back too much during the recent "
  + "high-volatility leg.\n"
  + "   Confidence: high\n"
  + "   - **stop_atr_multiple**: 1.5\n";

// BTCAAAAA-38721 — verbatim Current Analysis mockup demo data. These are the
// five recommendations + the reverse-view insight card from the approved
// BTCAAAAA-37748 mockup, injected when demoMode is true so the live panel
// renders the exact mockup face the board is screenshot-gating against.
const DEMO_PARSED_RECS: ParsedRec[] = [
  {
    id: 'demo-rec-1',
    title: 'Widen the stop past the −0.70% cluster',
    summary: '',
    raw: 'demo-rec-1',
    type: 'risk',
    confidence: 'high',
    suggestedParams: [],
    categoryIdOverride: 'risk',
    categoryLabel: 'STOP LOSS',
    deltaLabelOverride: '+8% WR',
    change: {
      contextLine: 'At 1hod exit · ABSOLUTE',
      oldLine: 'stop = 0.70%',
      newLine: 'stop = 1.05%',
    },
    affectsLine: 'Asia 50% → At 1hod',
    footerMetrics: { wr: '+8 WR', dd: '+34 DD', pl: '+$1,640 P/L' },
  },
  {
    id: 'demo-rec-2',
    title: 'Gate entries against the EMA-55 vector',
    summary: '',
    raw: 'demo-rec-2',
    type: 'entry',
    confidence: 'high',
    suggestedParams: [],
    categoryIdOverride: 'entry',
    categoryLabel: 'ENTRY FILTER',
    deltaLabelOverride: '+5% WR',
    change: {
      contextLine: 'Ema 55 vector · entry gate',
      oldLine: 'gate = off',
      newLine: 'gate = require alignment',
    },
    affectsLine: 'Ema 55 vector → gate',
    footerMetrics: { wr: '+5 WR', dd: '-46 DD', pl: '-$320 P/L' },
  },
  {
    id: 'demo-rec-3',
    title: 'Tighten the Below Asia 50 window to 8 candles',
    summary: '',
    raw: 'demo-rec-3',
    type: 'regime',
    confidence: 'high',
    suggestedParams: [],
    categoryIdOverride: 'regime',
    categoryLabel: 'TIMING',
    deltaLabelOverride: '+2.5% WR',
    change: {
      contextLine: 'Time constraint · Below Asia 50',
      oldLine: 'within 12 candles',
      newLine: 'within 8 candles',
    },
    affectsLine: 'Asia 50% → Below Asia 50',
    footerMetrics: { wr: '+2.5 WR', dd: '-12 DD', pl: '-$110 P/L' },
  },
  {
    id: 'demo-rec-4',
    title: 'Deepen recheck on the 100% TP-aware exit',
    summary: '',
    raw: 'demo-rec-4',
    type: 'exit',
    confidence: 'high',
    suggestedParams: [],
    categoryIdOverride: 'exit',
    categoryLabel: 'EXIT',
    deltaLabelOverride: '+1.5% WR',
    change: {
      contextLine: 'Above Asia 50 exit · RCHECK',
      oldLine: 'recheck = 2 bars',
      newLine: 'recheck = 4 bars',
    },
    affectsLine: 'Asia 50% → Above Asia 50',
    footerMetrics: { wr: '+1.5 WR', dd: '-8 DD', pl: '+$240 P/L' },
  },
  {
    id: 'demo-rec-5',
    title: 'Shorten Bearish Climax recheck to 3 bars',
    summary: '',
    raw: 'demo-rec-5',
    type: 'signal',
    confidence: 'high',
    suggestedParams: [],
    categoryIdOverride: 'signal',
    categoryLabel: 'SIGNAL',
    deltaLabelOverride: '+1% WR',
    change: {
      contextLine: 'Bearish Climax · RCHECK',
      oldLine: 'within 5 bars',
      newLine: 'within 3 bars',
    },
    affectsLine: 'Ema 55 vector → Bearish Climax',
    footerMetrics: { wr: '+1 WR', dd: '-5 DD', pl: '+$90 P/L' },
  },
  {
    id: 'demo-rec-6',
    title: 'Reverse view — what the winners share',
    summary: '',
    raw: 'demo-rec-6',
    type: 'pattern',
    confidence: 'high',
    suggestedParams: [],
    categoryIdOverride: 'signal',
    categoryLabel: 'PATTERN',
    deltaLabelOverride: 'Insight',
    insight: true,
    insightBox:
      'No parameter to toggle — use as a manual confluence check when placing trades.',
    affectsLine: '—',
    footerMetrics: { wr: '— WR', dd: '— DD', pl: '— P/L' },
  },
];

// BTCAAAAA-38721 — verbatim STRATEGY IMPACT baseline from the mockup. With no
// recommendations applied ("0 on"), PROJECTED equals BASELINE, so this single
// KpiSet drives both columns of the bar.
const DEMO_BASELINE_KPIS: KpiSet = {
  winRate: 0.524,
  netLiquidity: 8824,
  maxDrawdown: 2.088,
  profitFactor: 0,
  entries: 21,
};

const DEMO_RAIL_LEGS: ReadonlyArray<DemoLeg> = [
  {
    title: 'Asia session 50 percent',
    pillLabel: 'REQUIRED',
    pillBg: 'var(--accent-green-soft)',
    pillFg: 'var(--accent-green-on)',
    pillBorder: 'var(--accent-green-on)',
  },
  {
    title: 'Above Asia 50 exit',
    pillLabel: '100% EXIT',
    pillBg: 'var(--accent-blue-soft)',
    pillFg: 'var(--accent-blue)',
    pillBorder: 'var(--accent-blue)',
  },
  {
    title: 'Ema 55 vector',
    pillLabel: 'REQUIRED',
    pillBg: 'var(--accent-green-soft)',
    pillFg: 'var(--accent-green-on)',
    pillBorder: 'var(--accent-green-on)',
  },
  {
    title: 'Bearish Climax',
    pillLabel: 'SIGNAL',
    pillBg: 'rgba(192, 139, 255, 0.16)',
    pillFg: '#c08bff',
    pillBorder: '#c08bff',
  },
  {
    title: 'Supply Demand Zones',
    pillLabel: 'EXIT',
    pillBg: 'rgba(255, 154, 82, 0.16)',
    pillFg: '#ff9a52',
    pillBorder: '#ff9a52',
  },
];

const ACTIVE_PHASES: ReadonlySet<SendPhase> = new Set([
  'building-request',
  'sending',
  'awaiting-provider',
]);

export interface AiRecommendationsPanelProps {
  result?: BacktestResult | null;
  strategy?: Strategy | null;
  backtestConfig?: Record<string, unknown> | null;
  disabled?: boolean;
  /**
   * Called with the updated strategy after a successful auto-apply. The
   * parent decides how to refresh the strategy view (e.g. re-fetch from
   * FastAPI, swap local state). Optional so the panel remains usable in
   * read-only / preview contexts.
   */
  onStrategyUpdated?: (strategy: Strategy) => void;
}

interface ActiveRec {
  id: string;
  title: string;
  raw: string;
  confidence?: string;
  rationale?: string;
  suggestedParams: Array<{ key: string; value: string }>;
}



type View = 'current' | 'request' | 'response' | 'history';

const VIEW_LABELS: Record<View, string> = {
  current: 'Current Analysis',
  request: 'AI Request',
  response: 'AI Response',
  history: 'History',
};

const VIEW_ORDER: View[] = ['current', 'request', 'response', 'history'];

// BTCAAAAA-37773 / Sprint A1: persist the active sub-tab in sessionStorage so
// it survives panel unmounts (parent tab switches, route navigations) within
// the same browser session.
const VIEW_STORAGE_KEY = 'ai_recs_view_v1';

function isView(v: unknown): v is View {
  return v === 'current' || v === 'request' || v === 'response' || v === 'history';
}

function readStoredView(): View | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.sessionStorage.getItem(VIEW_STORAGE_KEY);
    return isView(raw) ? raw : null;
  } catch {
    return null;
  }
}

function writeStoredView(v: View): void {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.setItem(VIEW_STORAGE_KEY, v);
  } catch {
    // best effort
  }
}

function formatPF(pf: number | undefined | null): string {
  if (pf === undefined || pf === null || !Number.isFinite(pf)) return '—';
  return pf.toFixed(2);
}

function formatWR(wr: number | undefined | null): string {
  if (wr === undefined || wr === null || !Number.isFinite(wr)) return '—';
  // BacktestResult.winRate may arrive as fraction (0-1) or percent (0-100);
  // collapse both forms to a single `XX%` chip so the header chip is stable.
  const pct = wr <= 1 ? wr * 100 : wr;
  return `${pct.toFixed(1)}%`;
}


export function AiRecommendationsPanel({
  result,
  strategy,
  backtestConfig,
  onStrategyUpdated,
}: AiRecommendationsPanelProps = {}) {
  const hasTrades = (result?.trades?.length ?? 0) > 0;
  const { settings, hydrated: aiSettingsHydrated } = useAiSettings();
  const { hasProvider, providerLabel } = useAiProviderAvailability();
  const history = useAiRecsHistory();
  const router = useRouter();

  // BTCAAAAA-38466 (Stream 5, B2) — preflight validation state. The classifier
  // (preflightValidation.ts) is pure; we feed it the hydrated flags plus the
  // most-recent request error + duration + raw response + parse result. Each
  // failure mode (no-trades / no-provider / timeout / unparseable) renders
  // its own banner with a one-click affordance.
  const [lastPreflightError, setLastPreflightError] = useState<PreflightError | null>(null);
  const [lastPreflightDurationMs, setLastPreflightDurationMs] = useState<number | null>(null);
  const [lastRawResponse, setLastRawResponse] = useState<string | null>(null);
  const [lastParseResult, setLastParseResult] = useState<{ diagnosis: string; recommendations: string } | null>(null);
  const timedOutRef = useRef(false);

const [blockCatalog, setBlockCatalog] = useState<unknown[] | null>(null);
  useEffect(() => {
    fetch('/api/strategy-builder/block-library')
      .then((r) => (r.ok ? r.json() : null))
      .then((data: unknown) => {
        if (data && typeof data === 'object' && Array.isArray((data as { blocks?: unknown }).blocks)) {
          setBlockCatalog((data as { blocks: unknown[] }).blocks);
        }
      })
      .catch(() => { /* best effort */ });
  }, []);

  const [view, setViewState] = useState<View>(() => readStoredView() ?? 'current');
  const setView = useCallback((v: View) => {
    setViewState(v);
    writeStoredView(v);
  }, []);
  // BTCAAAAA-37780 / Sprint A6: right-rail sub-tab. "recs" keeps the
  // existing diagnosis-summary + recommendations grid; "diagnose" renders
  // the orchestrator's diagnosis markdown plus the reported-vs-per-entry
  // metrics table and a pinned-impact sentence.
  const [rightTab, setRightTab] = useState<'recs' | 'diagnose'>('recs');

  // AC21: hydrate from the sessionStorage cache on mount so the recs
  // survive a tab switch or a remount of the panel. The cache is also
  // keyed by strategyId so a different strategy does not bleed recs.
  // AC22: we do NOT clear on prop-driven re-renders — the only clear
  // paths are explicit user actions (rerun / load-different-history).
  //
  // Hydration is performed by the useState lazy initializers below
  // (lastAnalysisHash / aiAnalysis / appliedRecIds / preApplySnapshots),
  // each of which calls `readInitialCache()` to read sessionStorage
  // exactly once at mount. This avoids the cascading render the
  // react-hooks/set-state-in-effect rule would flag if we ran a
  // useEffect that called setState at mount.
  //
  // `readInitialCache` is a closure over `strategy` (the current prop)
  // so the strategyId filter is identical to the old useEffect's
  // filter — different strategy → cache is ignored.
  function readInitialCache(): CachedAnalysis | null {
    if (typeof window === 'undefined') return null;
    const cached = readRecsCache();
    if (!cached) return null;
    if (
      cached.strategyId !== null &&
      strategy?.id &&
      cached.strategyId !== strategy.id
    ) {
      return null;
    }
    return cached;
  }

  // BTCAAAAA-37773: hash captured at the time of the last successful analysis.
  // Compared against the live strategy+backtestConfig hash to gate the
  // persistent Re-analyze button (equal → disabled, different → enabled).
  //
  // AC21: this is hydrated from the sessionStorage cache via the useState
  // lazy initializer above instead of a useEffect, to avoid the cascading
  // render the react-hooks/set-state-in-effect rule flags. The initializer
  // runs exactly once at mount.
  const [lastAnalysisHash, setLastAnalysisHash] = useState<string | null>(
    () => readInitialCache()?.analysisHash ?? null,
  );
  const [phase, setPhase] = useState<SendPhase>('idle');
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisDetail, setAnalysisDetail] = useState<string | null>(null);
  const [aiAnalysis, setAiAnalysis] = useState<{
    diagnosis: string;
    recommendations: string;
    raw: string;
  } | null>(() => {
    const cached = readInitialCache();
    return cached
      ? {
          diagnosis: cached.diagnosis,
          recommendations: cached.recommendations,
          raw: cached.raw,
        }
      : null;
  });
  const [applySuccess, setApplySuccess] = useState<string | null>(null);
  const [applySuccessVisible, setApplySuccessVisible] = useState(true);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    ok: boolean;
    message: string;
    detail?: string;
  } | null>(null);
  const [confirmation, setConfirmation] = useState<{
    type: 'clear-all' | 'delete';
    entryId?: string;
  } | null>(null);
  const [goalModalOpen, setGoalModalOpen] = useState(false);
  const [activeRec, setActiveRec] = useState<ActiveRec | null>(null);
  const [optimizationGoal, setOptimizationGoal] = useState<string | null>(null);
  // Q7 (BTCAAAAA-38564): when the user clicks "View" on a history row the entry is
  // stored here so the Current Analysis tab can show the snapshot KPIs + banner.
  // Cleared when a new analysis starts or the user clicks Re-analyze.
  const [viewingHistoryEntry, setViewingHistoryEntry] = useState<AiRecsHistoryEntry | null>(null);

  // BTCAAAAA-38300 — AI Response tab metadata (provider / tokens / duration).
  // Populated after each successful analyze; the response tab header reads
  // this to render "claude, 184 tokens · 4.1s" matching mockup 04.png.
  const [responseMeta, setResponseMeta] = useState<{
    provider: string;
    tokens: number;
    durationMs: number;
  } | null>(null);
  const [responseCopied, setResponseCopied] = useState(false);

  // BTCAAAAA-36917 v4 UX: empty-state preview/demo affordances.
  // previewMode renders a single static card inline (no aiAnalysis touch —
  // the v3 sessionStorage cache stays empty).
  // demoMode populates aiAnalysis with hardcoded sample data; the cache
  // persistence effect below early-returns while demoMode is true, so the
  // demo payload never leaks into sessionStorage.
  const [previewMode, setPreviewMode] = useState(false);
  const [demoMode, setDemoMode] = useState(false);
  // BTCAAAAA-38464 (Stream 3, L2): confidence-floor toggle. When false
  // (default), recs whose `confidence` falls below the floor are hidden behind
  // the "Advanced" disclosure. When true, every parsed rec is shown regardless
  // of confidence so the user can audit what the AI declined to flag.
  const [showLowConfidenceRecs, setShowLowConfidenceRecs] = useState(false);

  // AC9: admin gate for Export to JSON. Computed once on mount from the
  // auth_token claim; a fresh login would remount the panel through key
  // changes elsewhere so we do not need to live-observe it. Lazy init
  // (instead of useState(false) + useEffect) avoids the cascading render
  // that the react-hooks/set-state-in-effect rule flags and is sufficient
  // here because the value never changes during a single mount.
  const [isAdmin] = useState(() => readIsAdminFromAuthToken());

  // AC15-AC22: per-tile toggle state. Each card knows whether its rec has
  // been applied (and thus should render in the "on" / enabled state), what
  // the strategy looked like right before that apply (so AC18 rollback can
  // restore it locally), and whether an apply is currently in flight for
  // that specific rec so we can show per-tile spinners. Per-tile errors
  // surface under the failing card rather than collapsing into a single
  // global banner.
  const [appliedRecIds, setAppliedRecIds] = useState<string[]>(
    () => readInitialCache()?.appliedRecIds ?? [],
  );
  const [preApplySnapshots, setPreApplySnapshots] = useState<
    Array<[string, Strategy]>
  >(() => readInitialCache()?.preApplySnapshots ?? []);
  const [perTileApplying, setPerTileApplying] = useState<string[]>([]);
  const [perTileError, setPerTileError] = useState<Record<string, string>>({});

  // Tracks the most recent AI-recommendations history entry so the
  // orchestrator can flip its Applied/Dismissed badge via AC3. Updated
  // each time the user runs an analysis; the orchestrator fires
  // onHistoryStatusChange(recId, status) on every successful apply or
  // rollback, and the panel translates that into a history.updateStatus
  // call against this id.
  const lastHistoryEntryIdRef = useRef<string | undefined>(undefined);

  // AC21: persist recs + applied state to sessionStorage on change. Done in
  // a single effect so we only touch storage when something actually
  // changed. Errors are silent (readRecsCache handles the read side).
  // BTCAAAAA-36917 v4 UX: while demoMode is true we deliberately skip the
  // cache write so the demo payload never lands in sessionStorage. The
  // effect re-fires when demoMode flips back to false and resumes normal
  // persistence.
  //
  // Hydration now happens in the useState lazy initializers above, so
  // there is no cacheHydratedRef guard — by the time this effect first
  // runs, the initial cache (if any) has already been applied.
  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (demoMode) return;
    if (!aiAnalysis) {
      writeRecsCache(null);
      return;
    }
    writeRecsCache({
      version: AI_RECS_CACHE_VERSION,
      strategyId: strategy?.id ?? null,
      diagnosis: aiAnalysis.diagnosis,
      recommendations: aiAnalysis.recommendations,
      raw: aiAnalysis.raw,
      appliedRecIds,
      preApplySnapshots,
      analysisTimestamp: new Date().toISOString(),
      ...(lastAnalysisHash ? { analysisHash: lastAnalysisHash } : {}),
    });
  }, [aiAnalysis, appliedRecIds, preApplySnapshots, strategy?.id, demoMode, lastAnalysisHash]);

  // AC8: countdown for the awaiting-provider phase. Resets to the full
  // ETA whenever we enter the phase, ticks once per second while we are
  // inside it, and clears when we leave. The two setAwaitingEta calls in
  // the effect body go through the functional-updater form with a prev
  // equality bail-out so React skips the render when the new value
  // equals the old. The setInterval callback runs outside the effect
  // body so the rule does not flag it.
  //
  // The phase is the canonical external trigger for this timer — this is
  // a legitimate "sync React state with an external signal" use of
  // useEffect (https://react.dev/learn/synchronizing-with-effects), so
  // we suppress the set-state-in-effect lint for these two calls.
  const [awaitingEta, setAwaitingEta] = useState<number | null>(null);
  /* eslint-disable react-hooks/set-state-in-effect -- the phase is the
     canonical external trigger for this countdown (see
     https://react.dev/learn/synchronizing-with-effects); the two
     setAwaitingEta calls reset and clear the countdown as we
     enter/exit the awaiting-provider phase. */
  useEffect(() => {
    if (phase !== 'awaiting-provider') {
      setAwaitingEta((prev) => (prev === null ? prev : null));
      return;
    }
    setAwaitingEta((prev) =>
      prev === AWAITING_PROVIDER_ETA_SECONDS ? prev : AWAITING_PROVIDER_ETA_SECONDS,
    );
    const interval = setInterval(() => {
      setAwaitingEta((prev) => (prev === null ? null : prev - 1));
    }, 1000);
    return () => clearInterval(interval);
  }, [phase]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const abortRef = useRef<AbortController | null>(null);
  const dismissTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const applySuccessTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const applySuccessFadeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (abortRef.current) {
        abortRef.current.abort();
        abortRef.current = null;
      }
      if (dismissTimerRef.current) {
        clearTimeout(dismissTimerRef.current);
        dismissTimerRef.current = null;
      }
      if (applySuccessTimerRef.current) {
        clearTimeout(applySuccessTimerRef.current);
        applySuccessTimerRef.current = null;
      }
      if (applySuccessFadeTimerRef.current) {
        clearTimeout(applySuccessFadeTimerRef.current);
        applySuccessFadeTimerRef.current = null;
      }
    };
  }, []);

  // AC10: auto-dismiss the apply success banner after 3 seconds. We flip
  // the "visible" flag first to drive the opacity fade, then clear the
  // message on a second timer. The two setApplySuccessVisible calls in
  // the effect body go through the functional-updater form with a prev
  // equality bail-out so the react-hooks/set-state-in-effect rule does
  // not flag the entry / exit transitions. The setTimeout callbacks
  // below are not flagged because they fire outside the effect body.
  useEffect(() => {
    const showBanner = () =>
      setApplySuccessVisible((prev) => (prev === true ? prev : true));
    if (!applySuccess) {
      showBanner();
      if (applySuccessTimerRef.current) {
        clearTimeout(applySuccessTimerRef.current);
        applySuccessTimerRef.current = null;
      }
      if (applySuccessFadeTimerRef.current) {
        clearTimeout(applySuccessFadeTimerRef.current);
        applySuccessFadeTimerRef.current = null;
      }
      return;
    }
    showBanner();
    if (applySuccessFadeTimerRef.current) {
      clearTimeout(applySuccessFadeTimerRef.current);
    }
    if (applySuccessTimerRef.current) {
      clearTimeout(applySuccessTimerRef.current);
    }
    // AC10: keep the banner fully opaque for the full 3s window, then flip
    // visibility to drive the 300ms CSS opacity fade, then clear the message
    // 300ms after that so the element is removed once the fade has had time
    // to play out.
    applySuccessFadeTimerRef.current = setTimeout(() => {
      setApplySuccessVisible(false);
    }, APPLY_SUCCESS_DISMISS_MS);
    applySuccessTimerRef.current = setTimeout(() => {
      setApplySuccess(null);
      setApplySuccessVisible(true);
    }, APPLY_SUCCESS_DISMISS_MS);
    return () => {
      if (applySuccessFadeTimerRef.current) {
        clearTimeout(applySuccessFadeTimerRef.current);
        applySuccessFadeTimerRef.current = null;
      }
      if (applySuccessTimerRef.current) {
        clearTimeout(applySuccessTimerRef.current);
        applySuccessTimerRef.current = null;
      }
    };
  }, [applySuccess]);

  const analyzing = ACTIVE_PHASES.has(phase);

  // Hoist the optional chain out of the useMemo deps array. The
  // react-hooks/preserve-manual-memoization rule infers the actual
  // runtime dependency as `aiAnalysis.recommendations` (the field
  // accessed inside the body) and would refuse to compile if the source
  // dep `aiAnalysis?.recommendations` differs — moving it to a const
  // makes both the source and inferred deps equal.
  const analysisRecommendations = aiAnalysis?.recommendations;
  const parsedRecs = useMemo(() => {
    if (demoMode) return DEMO_PARSED_RECS;
    if (!analysisRecommendations) return [];
    return parseRecommendations(analysisRecommendations);
  }, [analysisRecommendations, demoMode]);

  // BTCAAAAA-37780 / Sprint A6 — Diagnose tab data.
  const diagnoseRows = useMemo(
    () => buildDiagnoseRows(result ?? null, result?.trades ?? null),
    [result],
  );
  const stagedSummaries: StagedRecSummary[] = useMemo(
    () =>
      parsedRecs
        .filter((r) => appliedRecIds.includes(r.id))
        .map((r) => ({ id: r.id, title: r.title, suggestedParams: r.suggestedParams })),
    [parsedRecs, appliedRecIds],
  );
  const stagedSentence = useMemo(
    () => buildStagedRecsSentence(stagedSummaries, strategy ?? null),
    [stagedSummaries, strategy],
  );
  // BTCAAAAA-38464 (Stream 3, L2): confidence-floor filter applied to the
  // recs that actually render. When `showLowConfidenceRecs` is true the floor
  // is bypassed so the user can audit what was hidden; otherwise recs with
  // `confidence` below the floor (default 0.4) are excluded. Hidden count is
  // surfaced separately in the RECOMMENDATIONS header.
  const visibleRecs = useMemo(
    () =>
      showLowConfidenceRecs
        ? parsedRecs
        : parsedRecs.filter((rec) =>
            meetsConfidenceFloor(rec.confidence, DEFAULT_CONFIDENCE_FLOOR),
          ),
    [parsedRecs, showLowConfidenceRecs],
  );
  const hiddenRecCount = parsedRecs.length - visibleRecs.length;
  // A4 (BTCAAAAA-37777): map the same parsed recs into the minimal shape the
  // reverse-view extractor needs. Confidence drives the synthetic uplift so
  // the top-quartile ranking matches the model's own confidence ordering.
  const reverseViewInputs = useMemo<ReverseViewInput[]>(
    () =>
      parsedRecs.map((r) => ({
        id: r.id,
        uplift: confidenceToUplift(r.confidence),
        category: r.type,
        paramKeys: r.suggestedParams.map((p) => p.key),
      })),
    [parsedRecs],
  );

  // BTCAAAAA-37774 Sprint A2 — baseline + applied impacts feed the KPI bar.
  const baselineKpis = useMemo(
    () => (demoMode ? DEMO_BASELINE_KPIS : deriveBaselineKpis(result ?? null)),
    [result, demoMode],
  );

  // BTCAAAAA-37772 Sprint B/B4 — real re-projection function passed to the
  // KPI bar. When a strategy ID is available, fires /api/backtest/re-project
  // after the bar's 250ms debounce so the indicator flips Preview → Confirmed.
  const _reProjectFn = useCallback(
    (signal: AbortSignal) =>
      reProjectFromServer(strategy?.id ?? '', backtestConfig ?? {}, signal),
    [strategy?.id, backtestConfig],
  );
  const reProjectFn: ReProjectFn | undefined = strategy?.id ? _reProjectFn : undefined;

  const appliedImpacts = useMemo<AppliedRecImpact[]>(() => {
    if (parsedRecs.length === 0 || appliedRecIds.length === 0) return [];
    const byId = new Map(parsedRecs.map((r) => [r.id, r] as const));
    return appliedRecIds
      .map((id) => {
        const rec = byId.get(id);
        if (!rec) return null;
        return { recId: id, delta: projectedImpactFromRecRaw(rec.raw) };
      })
      .filter((x): x is AppliedRecImpact => x !== null);
  }, [parsedRecs, appliedRecIds]);

  const handleExport = useCallback(() => {
    const payload = buildRequestPayload(
      result,
      strategy,
      backtestConfig,
      activeRec,
      optimizationGoal,
    );
    const blob = new Blob([payload], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ai_request_${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [result, strategy, backtestConfig, activeRec, optimizationGoal]);

  const handleTestConnection = useCallback(async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await fetch('/api/ai/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: settings.provider,
          model: settings.model,
          apiKey: settings.apiKeys?.[settings.provider] ?? '',
          ollamaBaseUrl: settings.ollamaBaseUrl,
        }),
      });
      const data = await res.json().catch(() => ({}));
      setTestResult({
        ok: !!res.ok && data?.ok !== false,
        message: data?.message ?? (res.ok ? 'Connection succeeded.' : `Request failed (${res.status}).`),
        detail: data?.detail,
      });
    } catch (err) {
      setTestResult({
        ok: false,
        message: err instanceof Error ? err.message : 'Network error contacting /api/ai/test-connection.',
      });
    } finally {
      setTesting(false);
    }
  }, [settings]);

  const handleCancel = useCallback(() => {
    if (!analyzing) return;
    abortRef.current?.abort();
  }, [analyzing]);

  // Refactored to take the goal explicitly so AC7 can pipe the modal value
  // through, and so tests can drive a deterministic code path.
  const runApproveAndSend = useCallback(
    async (goal: string | null) => {
      if (!hasTrades || analyzing) return;
      setAnalysisError(null);
      setAnalysisDetail(null);
      setOptimizationGoal(goal);
      if (dismissTimerRef.current) {
        clearTimeout(dismissTimerRef.current);
        dismissTimerRef.current = null;
      }
      const controller = new AbortController();
      abortRef.current = controller;
      timedOutRef.current = false;

      setPhase('building-request');
      await new Promise((r) => setTimeout(r, 0));

      let payload: unknown;
      try {
        const payloadJson = buildRequestPayload(
          result,
          strategy,
          backtestConfig,
          activeRec,
          goal,
          blockCatalog,
        );
        payload = JSON.parse(payloadJson) as unknown;
      } catch (err) {
        setAnalysisError(
          err instanceof Error
            ? `Failed to package request: ${err.message}`
            : 'Failed to package request.',
        );
        setPhase('error');
        abortRef.current = null;
        return;
      }

      if (controller.signal.aborted) {
        setAnalysisError('Request cancelled.');
        setPhase('error');
        abortRef.current = null;
        return;
      }

      setPhase('sending');
      await new Promise((r) => setTimeout(r, 0));

      setPhase('awaiting-provider');

      // BTCAAAAA-38300 — record provider / tokens / duration so the AI
      // Response tab can show "claude, 184 tokens · 4.1s" matching the
      // BTC-37748 mockup (mockup 04.png). Tokens are estimated from the
      // response length at 4 chars/token; the analyzer endpoint does not
      // return a usage field today.
      const sentAt = Date.now();

      // BTCAAAAA-38465 (Stream 4) — build the system prompt from the live
      // strategy + block catalog so it includes BTC/crypto context, the
      // supported building-block vocabulary, the strategy's actual block
      // types, and the parameter key list the auto-apply path keys off of.
      const systemPrompt = buildAiRecsSystemPrompt({
        strategy: strategy ?? null,
        blockCatalog,
      });

      try {
        const res = await fetch('/api/ai/analyze', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({
            provider: settings.provider,
            model: settings.model,
            apiKey: settings.apiKeys[settings.provider],
            ollamaBaseUrl: settings.ollamaBaseUrl,
            prompt: systemPrompt,
            payload,
            optimizationGoal: goal,
          }),
          signal: controller.signal,
        });
        const data = (await res.json()) as {
          ok: boolean;
          text?: string;
          error?: string;
          detail?: string;
        };
        if (!res.ok || !data.ok) {
          // BTCAAAAA-38466 — feed the HTTP failure into the preflight
          // classifier so generic HTTP errors fall through to the existing
          // analysisError banner, but anything that *would* be a timeout
          // is classified correctly.
          setLastPreflightError({
            kind: res.status === 408 || res.status === 504 ? 'timeout' : 'http',
            message: data.error ?? `The analyze endpoint returned HTTP ${res.status}.`,
          });
          setLastPreflightDurationMs(Date.now() - sentAt);
          setAnalysisError(
            data.error ?? `The analyze endpoint returned HTTP ${res.status}.`,
          );
          setAnalysisDetail(data.detail ?? null);
          setPhase('error');
          abortRef.current = null;
          return;
        }
        const parsed = parseAnalysisResponse(data.text ?? '');
        // BTCAAAAA-38466 — detect an unparseable model reply before
        // clearing preflight state. parseAnalysisResponse falls back to
        // "use the full text as diagnosis" so we need to compare parsed
        // sections to the raw length to know whether the model actually
        // produced a structured reply.
        setLastRawResponse(parsed.raw);
        setLastParseResult({
          diagnosis: parsed.diagnosis,
          recommendations: parsed.recommendations,
        });
        // BTCAAAAA-36917 v4 UX: real AI response — clear any preview/demo
        // affordances so the user lands on the genuine analysis.
        setPreviewMode(false);
        setDemoMode(false);
        setAiAnalysis(parsed);
        // BTCAAAAA-38300 — record provider / tokens / duration for the AI
        // Response tab header. Tokens are estimated at ~4 chars/token from
        // the raw response text; the analyzer endpoint does not return a
        // usage field today.
        setResponseMeta({
          provider: settings.provider,
          tokens: Math.round((data.text?.length ?? 0) / 4),
          durationMs: Date.now() - sentAt,
        });
        setLastAnalysisHash(computeReanalyzeHash(strategy ?? null, backtestConfig ?? null));
        // Q7: clear any history-snapshot view now that a fresh analysis arrived.
        setViewingHistoryEntry(null);
        if (history.hydrated) {
          const entry = history.add({
            prompt: systemPrompt,
            diagnosis: parsed.diagnosis,
            recommendations: parsed.recommendations,
            raw: parsed.raw,
            ...(strategy?.name ? { strategyName: strategy.name } : {}),
            snapshotKpis: baselineKpis as HistorySnapshotKpis,
          });
          lastHistoryEntryIdRef.current = entry.id;
        }
        setPhase('done');
        abortRef.current = null;
        dismissTimerRef.current = setTimeout(() => {
          setPhase((current) => (current === 'done' ? 'idle' : current));
          dismissTimerRef.current = null;
        }, 1200);
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') {
          setAnalysisError('Request cancelled.');
        } else {
          // BTCAAAAA-38466 — generic fetch failure (DNS, CORS, server
          // crash). Surface via the existing analysisError banner; the
          // preflight classifier will fall through to "none" because the
          // kind is not timeout.
          setLastPreflightError({
            kind: 'network',
            message: err instanceof Error ? err.message : 'The analyze request failed.',
          });
          setLastPreflightDurationMs(Date.now() - sentAt);
          setAnalysisError(
            err instanceof Error ? err.message : 'The analyze request failed.',
          );
        }
        setPhase('error');
        abortRef.current = null;
      }
    },
    [
      hasTrades,
      analyzing,
      result,
      strategy,
      backtestConfig,
      activeRec,
      blockCatalog,
      settings.provider,
      settings.model,
      settings.apiKeys,
      settings.ollamaBaseUrl,
      history,
      baselineKpis,
    ],
  );

  // The Approve & Send button is the AC7 entry point — clicking it opens the
  // optimization-goal modal; the actual analyze fetch runs after the user
  // confirms a goal.
  const handleApproveAndSendClick = useCallback(() => {
    if (!hasTrades || !hasProvider || analyzing) return;
    setGoalModalOpen(true);
  }, [hasTrades, hasProvider, analyzing]);

  const handleGoalConfirm = useCallback(
    (goal: string) => {
      setGoalModalOpen(false);
      void runApproveAndSend(goal);
    },
    [runApproveAndSend],
  );

  const handleGoalCancel = useCallback(() => {
    setGoalModalOpen(false);
  }, []);


  const handleClearActiveRec = useCallback(() => {
    setActiveRec(null);
  }, []);

  // BTCAAAAA-38300 — AI Response tab "Copy" button. Copies the most recent
  // raw model reply (history.entries[0].raw, falling back to the in-memory
  // aiAnalysis raw) to the clipboard. Falls back to a hidden textarea +
  // execCommand for browsers without async clipboard support.
  const handleCopyResponse = useCallback(async () => {
    const text =
      history.entries[0]?.raw ||
      aiAnalysis?.raw ||
      '';
    if (!text) return;
    try {
      if (
        typeof navigator !== 'undefined' &&
        navigator.clipboard &&
        typeof navigator.clipboard.writeText === 'function'
      ) {
        await navigator.clipboard.writeText(text);
      } else if (typeof document !== 'undefined') {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
      }
      setResponseCopied(true);
      window.setTimeout(() => setResponseCopied(false), 1500);
    } catch {
      // best-effort copy; silent fail keeps the button click non-blocking
    }
  }, [history.entries, aiAnalysis]);

  // AC15-AC20: per-tile toggle. A click on an "off" card applies just that
  // rec through the orchestrator (one-element recs array), captures the
  // pre-apply strategy snapshot for AC18 rollback, and flips the card into
  // its enabled state. A click on an "on" card rolls back to the snapshot
  // locally (AC18) — server-side rollback is a follow-up backend ticket
  // since webui-only phase forbids backend touches.
  //
  // Apply runs are independent per-rec (AC19) so multiple cards can be
  // toggled in parallel; per-tile spinners and per-tile errors keep the UX
  // honest about which rec is in flight or failed.
  //
  // The async + transition-emission logic lives in `applyOrchestrator.ts`
  // so this handler stays a thin React-state applier. The panel still owns
  // the spinner UX (set eagerly so the click feels instant), and the
  // `finally` block that clears `perTileApplying` regardless of outcome.
  const handleToggleRec = useCallback(
    async (rec: ParsedRec) => {
      if (!strategy?.id) return;

      const deps: ApplyOrchestratorDeps = {
        fetchFn: (url, init) => fetch(url as RequestInfo, init),
        getAuthToken: () => {
          if (typeof window === 'undefined') return undefined;
          return window.localStorage.getItem('auth_token') ?? undefined;
        },
        onHistoryStatusChange: (_recId, status) => {
          const entryId = lastHistoryEntryIdRef.current;
          if (entryId) history.updateStatus(entryId, status);
        },
        onStrategyApplied: (updated) => {
          if (onStrategyUpdated) onStrategyUpdated(updated);
        },
      };

      // Optimistic spinner flip — the orchestrator's `markApplying`
      // transition is intentionally a no-op here (the spinner is already
      // on) so the user sees instant feedback before the network round-trip.
      setPerTileApplying((prev) => [...prev, rec.id]);

      try {
        const result = await executeApply(
          { rec, strategy, appliedRecIds, preApplySnapshots },
          deps,
        );

        for (const tx of result.transitions) {
          switch (tx.kind) {
            case 'snapshot':
              setPreApplySnapshots((prev) => [...prev, tx.entry]);
              break;
            case 'markApplying':
              // Already set eagerly above; no-op keeps the transition
              // stream uniform with the rest of the panel's lifecycle.
              break;
            case 'clearError':
              setPerTileError((prev) => {
                if (!(tx.recId in prev)) return prev;
                const next = { ...prev };
                delete next[tx.recId];
                return next;
              });
              break;
            case 'markApplied':
              setAppliedRecIds((prev) =>
                prev.includes(tx.recId) ? prev : [...prev, tx.recId],
              );
              break;
            case 'markRollback':
              if (onStrategyUpdated) onStrategyUpdated(tx.restoredStrategy);
              setAppliedRecIds((prev) => prev.filter((id) => id !== tx.recId));
              setPreApplySnapshots((prev) =>
                prev.filter(([id]) => id !== tx.recId),
              );
              break;
            case 'setError':
              setPerTileError((prev) => ({ ...prev, [tx.recId]: tx.message }));
              break;
            case 'dropSnapshot':
              setPreApplySnapshots((prev) =>
                prev.filter(([id]) => id !== tx.recId),
              );
              break;
          }
        }
      } finally {
        setPerTileApplying((prev) => prev.filter((id) => id !== rec.id));
      }
    },
    [strategy, appliedRecIds, preApplySnapshots, onStrategyUpdated, history],
  );

  // AC22: explicit rerun invalidates the per-tile apply state because the
  // new analysis may have a different rec set / different rec ids. The
  // cache-write effect (above) will overwrite the sessionStorage entry on
  // the next render with the new aiAnalysis + empty applied state. We
  // track a ref of the previous aiAnalysis so the very first non-null
  // value (whether from cache hydration or the initial run) does not
  // trip the "reset" branch — only an actual transition from a prior
  // analysis to a different one should wipe the toggle state.
  const lastAiAnalysisRef = useRef<typeof aiAnalysis>(null);
  useEffect(() => {
    const prev = lastAiAnalysisRef.current;
    lastAiAnalysisRef.current = aiAnalysis;
    if (!aiAnalysis) return;
    if (prev === null) return;
    if (
      prev.diagnosis === aiAnalysis.diagnosis &&
      prev.recommendations === aiAnalysis.recommendations &&
      prev.raw === aiAnalysis.raw
    ) {
      return;
    }
    setAppliedRecIds([]);
    setPreApplySnapshots([]);
    setPerTileError({});
  }, [aiAnalysis]);

  // AC3: history Load → hydrate current analysis view AND set first parsed
  // rec as the active rec so the user can re-send with that context.
  // Q7 (BTCAAAAA-38564): also stores the entry so the KPI bar renders the
  // snapshot's before-values and the banner is shown.
  const loadHistoryIntoCurrent = useCallback(
    (entry: AiRecsHistoryEntry) => {
      // BTCAAAAA-36917 v4 UX: user explicitly loaded a history entry —
      // dismiss any active preview/demo state first.
      setPreviewMode(false);
      setDemoMode(false);
      setAiAnalysis({
        diagnosis: entry.diagnosis,
        recommendations: entry.recommendations,
        raw: entry.raw,
      });
      // Q7: track which entry is being viewed so snapshot KPIs can be shown.
      setViewingHistoryEntry(entry);
      // Reset apply state — the loaded recs may have different IDs than the
      // current session's recs, so stale toggles would be misleading.
      setAppliedRecIds([]);
      setPreApplySnapshots([]);
      const recs = parseRecommendations(entry.recommendations);
      const first = recs[0];
      if (first) {
        setActiveRec({
          id: first.id,
          title: first.title,
          raw: first.raw,
          ...(first.confidence ? { confidence: first.confidence } : {}),
          ...(first.rationale ? { rationale: first.rationale } : {}),
          suggestedParams: first.suggestedParams,
        });
      } else {
        setActiveRec(null);
      }
      setView('current');
      setAnalysisError(null);
      setAnalysisDetail(null);
    },
    [setView],
  );

  const canSend = hasTrades && hasProvider && !analyzing && aiSettingsHydrated;

  // BTCAAAAA-38466 (Stream 5, B2) — pure classifier over the live context.
  // Returns one of 5 PreflightState variants; the JSX below maps each to a
  // distinct banner with a one-click affordance.
  const preflightState = useMemo(
    () =>
      classifyPreflight({
        hydrated: aiSettingsHydrated,
        hasTrades,
        hasProvider,
        providerLabel: providerLabel || settings.provider,
        lastError: lastPreflightError,
        lastDurationMs: lastPreflightDurationMs,
        lastRawResponse,
        lastParseResult,
      }),
    [
      aiSettingsHydrated,
      hasTrades,
      hasProvider,
      providerLabel,
      settings.provider,
      lastPreflightError,
      lastPreflightDurationMs,
      lastRawResponse,
      lastParseResult,
    ],
  );

  // BTCAAAAA-38466 — banner affordances. Each handler is intentionally
  // tiny: scroll-to-backtest uses the existing InfoTooltip id, settings
  // navigation uses next/navigation, retry re-runs runApproveAndSend, and
  // copy-unparseable writes the raw response to the clipboard with a
  // textarea fallback for older browsers.
  const handleRunBacktestClick = useCallback(() => {
    scrollToBacktestButton();
  }, []);

  const handleOpenSettingsClick = useCallback(() => {
    router.push(DEFAULT_SETTINGS_HREF);
  }, [router]);

  const handleRetryClick = useCallback(() => {
    // Clear the timeout markers so classifyPreflight returns to "none" on
    // next paint, then kick off a fresh send using the most recent goal.
    setLastPreflightError(null);
    setLastPreflightDurationMs(null);
    void runApproveAndSend(optimizationGoal);
  }, [runApproveAndSend, optimizationGoal]);

  const [copyUnparseableFeedback, setCopyUnparseableFeedback] = useState(false);
  const handleCopyUnparseableClick = useCallback(async () => {
    const text =
      preflightState.kind === 'unparseable' ? preflightState.raw : '';
    if (!text) return;
    try {
      if (
        typeof navigator !== 'undefined' &&
        navigator.clipboard &&
        typeof navigator.clipboard.writeText === 'function'
      ) {
        await navigator.clipboard.writeText(text);
      } else if (typeof document !== 'undefined') {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
      }
      setCopyUnparseableFeedback(true);
      window.setTimeout(() => setCopyUnparseableFeedback(false), 1500);
    } catch {
      // best-effort copy; silent fail keeps the button click non-blocking
    }
  }, [preflightState]);

  // BTCAAAAA-37773 / Sprint A1 — Re-analyze button dirty-hash gating.
  const currentHash = useMemo(
    () => computeReanalyzeHash(strategy ?? null, backtestConfig ?? null),
    [strategy, backtestConfig],
  );
  // Dirty when we have a previous analysis hash AND it differs from current.
  // No previous hash → not dirty (no cached analysis to compare against).
  const isDirty = lastAnalysisHash !== null && lastAnalysisHash !== currentHash;
  const reanalyzeDisabled = !canSend || (!isDirty && lastAnalysisHash !== null);
  const reanalyzeTooltip = !hasTrades
    ? 'Run a backtest with trades first.'
    : !hasProvider
      ? 'No AI provider configured — open Settings → AI to set one up.'
      : analyzing
        ? 'AI request in flight…'
        : lastAnalysisHash === null
          ? 'Run an analysis first.'
          : isDirty
            ? 'Strategy or backtest config changed — re-run'
            : 'No changes since last analysis';

  const handleReanalyzeClick = useCallback(
    (e: React.MouseEvent<HTMLButtonElement>) => {
      if (!canSend) return;
      const forceRerun = e.metaKey || e.ctrlKey;
      // Equal hash + not forced → button is already disabled, but guard
      // anyway in case a stale ref fires the click.
      if (!forceRerun && !isDirty && lastAnalysisHash !== null) return;
      setGoalModalOpen(true);
    },
    [canSend, isDirty, lastAnalysisHash],
  );

  const handlePopOut = useCallback(() => {
    if (typeof window === 'undefined') return;
    window.open(window.location.href, '_blank', 'noopener,width=1200,height=800');
  }, []);

  const showProgress = phase !== 'idle' && phase !== 'error';
  const progressPercent = phase === 'idle' || phase === 'error' ? 0 : PHASE_INFO[phase as Exclude<SendPhase, 'idle' | 'error'>].percent;
  const progressLabel =
    phase === 'idle' || phase === 'error'
      ? ''
      : PHASE_INFO[phase as Exclude<SendPhase, 'idle' | 'error'>].label;

  const requestClearAll = useCallback(() => {
    if (history.entries.length === 0) return;
    setConfirmation({ type: 'clear-all' });
  }, [history.entries.length]);

  const requestDelete = useCallback((id: string) => {
    setConfirmation({ type: 'delete', entryId: id });
  }, []);

  const cancelConfirmation = useCallback(() => setConfirmation(null), []);

  const confirmClearAll = useCallback(() => {
    history.clear();
    setConfirmation(null);
  }, [history]);

  const confirmDelete = useCallback(() => {
    if (confirmation?.entryId) {
      history.deleteEntry(confirmation.entryId);
    }
    setConfirmation(null);
  }, [confirmation, history]);

  const currentView = view;

  // A5: Right-rail "Strategy after changes" — merge today's parsed recs with
  // staged items carried over from prior applied history entries for the same
  // strategy. The rail's toggle reuses handleToggleRec so apply/rollback paths
  // stay identical to the per-card flow.
  const afterChangesItems = useMemo(
    () =>
      mergeStrategyAfterChanges({
        currentRecs: parsedRecs.map((r) => ({ id: r.id, title: r.title })),
        appliedRecIds,
        historyEntries: history.entries,
        currentStrategyName: strategy?.name ?? null,
      }),
    [parsedRecs, appliedRecIds, history.entries, strategy?.name],
  );

  const appliedRecIdSet = useMemo(() => new Set(appliedRecIds), [appliedRecIds]);

  const handleRailToggleCurrent = useCallback(
    (recId: string) => {
      const rec = parsedRecs.find((r) => r.id === recId);
      if (!rec) return;
      void handleToggleRec(rec);
    },
    [parsedRecs, handleToggleRec],
  );

  const handleRailJumpToOriginEntry = useCallback(
    (_historyEntryId: string) => {
      // id is intentionally ignored — panel only switches view; scroll-to-entry lives in HistoryView
      void _historyEntryId;
      setView('history');
    },
    [setView],
  );

  // BTCAAAAA-38566: stable refs for tab focus management (WAI-ARIA APG roving-tabindex pattern)
  const mainTabRefs = useRef<Map<View, HTMLButtonElement>>(new Map());
  const rightTabRefs = useRef<Map<'recs' | 'diagnose', HTMLButtonElement>>(new Map());

  const handleMainTabKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLButtonElement>, v: View) => {
      const idx = VIEW_ORDER.indexOf(v);
      let next: View | null = null;
      if (e.key === 'ArrowRight') next = VIEW_ORDER[(idx + 1) % VIEW_ORDER.length];
      else if (e.key === 'ArrowLeft') next = VIEW_ORDER[(idx - 1 + VIEW_ORDER.length) % VIEW_ORDER.length];
      else if (e.key === 'Home') next = VIEW_ORDER[0];
      else if (e.key === 'End') next = VIEW_ORDER[VIEW_ORDER.length - 1];
      if (next !== null) {
        e.preventDefault();
        setView(next);
        const nextTab = next;
        Promise.resolve().then(() => mainTabRefs.current.get(nextTab)?.focus());
      }
    },
    [setView],
  );

  const handleRightTabKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLButtonElement>, t: 'recs' | 'diagnose') => {
      const tabs = ['recs', 'diagnose'] as const;
      const idx = tabs.indexOf(t);
      let next: 'recs' | 'diagnose' | null = null;
      if (e.key === 'ArrowRight') next = tabs[(idx + 1) % tabs.length];
      else if (e.key === 'ArrowLeft') next = tabs[(idx - 1 + tabs.length) % tabs.length];
      if (next !== null) {
        e.preventDefault();
        setRightTab(next);
        const nextTab = next;
        Promise.resolve().then(() => rightTabRefs.current.get(nextTab)?.focus());
      }
    },
    [setRightTab],
  );

  // BTCAAAAA-37771 review — the progress indicator is shared by the AI Request
  // (leftPane) and Current Analysis (rightPane) views. Re-analyze can be
  // triggered from the Current Analysis header, so its live status must render
  // there too — otherwise the button just greys out silently and looks frozen.
  const progressIndicator = showProgress ? (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      data-testid="ai-recs-progress"
      className="rounded p-2 flex flex-col gap-1"
      style={{
        background: 'var(--bg-elevated)',
        border: '1px solid var(--border)',
      }}
    >
      <div className="flex items-center justify-between text-xs">
        <span
          data-testid="ai-recs-progress-label"
          style={{ color: 'var(--text-secondary)' }}
        >
          {progressLabel}
        </span>
        <span className="flex items-center gap-2">
          {phase === 'awaiting-provider' && awaitingEta !== null && (
            <span
              data-testid="ai-recs-progress-eta"
              aria-live="off"
              style={{
                color: 'var(--text-muted)',
                fontFamily: 'var(--font-mono, monospace)',
              }}
            >
              ~{awaitingEta}s
            </span>
          )}
          <span
            data-testid="ai-recs-progress-percent"
            style={{
              color: 'var(--text-muted)',
              fontFamily: 'var(--font-mono, monospace)',
            }}
          >
            {progressPercent}%
          </span>
        </span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={progressPercent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="AI recommendation request progress"
        className="w-full h-1.5 rounded overflow-hidden"
        style={{ background: 'var(--bg-card)' }}
      >
        <div
          data-testid="ai-recs-progress-bar"
          className="h-full rounded"
          style={{
            width: `${progressPercent}%`,
            background:
              phase === 'done'
                ? 'var(--accent-green)'
                : 'var(--accent-blue)',
            transition: 'width 200ms ease-out',
          }}
        />
      </div>
    </div>
  ) : null;

  // BTCAAAAA-37771 review — Test Connection result banner is shared so the
  // button works from both the AI Request and Current Analysis views.
  const testResultBanner = testResult ? (
    <div
      role="status"
      data-testid="ai-test-result"
      className="rounded p-2 text-xs"
      style={{
        background: testResult.ok
          ? 'var(--accent-green-tint)'
          : 'var(--accent-red-tint)',
        color: testResult.ok ? 'var(--accent-green)' : 'var(--accent-red)',
        border: `1px solid ${
          testResult.ok ? 'var(--accent-green)' : 'var(--accent-red)'
        }`,
      }}
    >
      <span className="font-semibold">{testResult.ok ? '✓ ' : '✗ '}</span>
      {testResult.message}
      {testResult.detail && (
        <span className="block mt-1" style={{ color: 'var(--text-muted)' }}>
          {testResult.detail}
        </span>
      )}
    </div>
  ) : null;

  // ── LEFT pane: config + active-form + Approve flow ──
  const leftPane = (
    <div className="flex flex-col gap-3">
      {/* BTCAAAAA-38300 — REQUEST PREVIEW promoted above the fold to match
          the BTC-37748 mockup. Per operator "must look exactly the same as
          this" (comment f2b214b2, 2026-06-24), all 5 sections are now
          default-open so the operator sees the full request layout at a
          glance, matching mockup 03. Existing banners, AI settings, and
          Approve flow still render below. */}
      <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
        REQUEST PREVIEW
      </p>

      {(() => {
        const strategyText = formatStrategyConfig(strategy);
        const backtestText = formatBacktestConfig(backtestConfig);
        const tradesText = formatTrades(result?.trades);
        const metricsText = formatMetrics(result);
        const blocksText = blockCatalog
          ? JSON.stringify(blockCatalog, null, 2)
          : 'Loading block catalog…';
        return (
          <>
            <CollapsibleSection
              title="1. Strategy Configuration"
              description="Complete strategy setup including blocks and parameters"
              copyText={strategyText}
            >
              <PreviewText text={strategyText} />
            </CollapsibleSection>

            <CollapsibleSection
              title="2. Backtest Configuration"
              description="How the backtest was configured (timeframe, SL/TP, position sizing)"
              copyText={backtestText}
            >
              <PreviewText text={backtestText} />
            </CollapsibleSection>

            <CollapsibleSection
              title="3. Trade Results"
              description="All trades executed with entry/exit details"
              copyText={tradesText}
            >
              <PreviewText text={tradesText} />
            </CollapsibleSection>

            <CollapsibleSection
              title="4. Metrics & Ratings"
              description="Performance metrics"
              copyText={metricsText}
            >
              <PreviewText text={metricsText} />
            </CollapsibleSection>

            <CollapsibleSection
              title="5. Available Building Blocks"
              description="Block catalog visible to AI for recommendations"
              copyText={blocksText}
            >
              <PreviewText text={blockCatalog ? `${blockCatalog.length} blocks available\n\n${blocksText}` : blocksText} />
            </CollapsibleSection>
          </>
        );
      })()}

      {/* Active rec banner (AC2 surface) */}
      {activeRec && (
        <div
          data-testid="active-rec-banner"
          className="rounded p-2 text-xs flex flex-col gap-1"
          style={{
            background: 'var(--accent-blue-soft)',
            border: '1px solid var(--accent-blue)',
            color: 'var(--text-secondary)',
          }}
        >
          <div className="flex items-center justify-between gap-2">
            <span
              className="text-[10px] font-semibold uppercase tracking-wide"
              style={{ color: 'var(--accent-blue)' }}
            >
              Active recommendation
            </span>
            <button
              type="button"
              onClick={handleClearActiveRec}
              data-testid="active-rec-clear"
              className="px-1.5 py-0.5 rounded text-[10px] font-medium"
              style={{
                background: 'var(--bg-elevated)',
                color: 'var(--text-muted)',
                border: '1px solid var(--border)',
                cursor: 'pointer',
              }}
            >
              <X size={10} style={{ display: 'inline', marginRight: 4 }} />
              Clear
            </button>
          </div>
          <p className="text-xs font-semibold">{activeRec.title}</p>
          {activeRec.suggestedParams.length > 0 && (
            <p
              className="text-[11px]"
              style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono, monospace)' }}
            >
              {activeRec.suggestedParams
                .map((p) => `${p.key} = ${p.value}`)
                .join(', ')}
            </p>
          )}
        </div>
      )}

      {/* Optimization goal pill (AC7 surface) */}
      {optimizationGoal && (
        <div
          data-testid="optimization-goal-pill"
          className="rounded p-2 text-[11px]"
          style={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
            color: 'var(--text-muted)',
            fontFamily: 'var(--font-mono, monospace)',
          }}
        >
          <span
            className="text-[10px] font-semibold uppercase tracking-wide mr-1"
            style={{ color: 'var(--text-muted)' }}
          >
            Optimization goal:
          </span>
          {optimizationGoal}
        </div>
      )}

      {/* Analysis error banner */}
      {analysisError && (
        <div
          className="rounded p-2 text-xs"
          role="alert"
          style={{
            background: 'var(--bg-elevated)',
            color: 'var(--accent-red)',
            border: '1px solid var(--accent-red)',
          }}
        >
          <p className="font-semibold">AI analysis failed</p>
          <p className="mt-1">{analysisError}</p>
          {analysisDetail && (
            <p className="mt-1" style={{ color: 'var(--text-faint)' }}>
              {analysisDetail}
            </p>
          )}
        </div>
      )}

      {/* Auto-apply success banner */}
      {applySuccess && (
        <div
          className="rounded p-2 text-xs"
          role="status"
          data-testid="ai-recs-apply-success"
          style={{
            background: 'var(--accent-green-soft)',
            color: 'var(--accent-green-on)',
            border: '1px solid var(--accent-green-on)',
            opacity: applySuccessVisible ? 1 : 0,
            transition: 'opacity 300ms ease-out',
          }}
        >
          {applySuccess}
        </div>
      )}

      {/* Stats bar */}
      {result && (
        <div
          className="rounded p-2 text-xs"
          style={{
            background: 'var(--bg-elevated)',
            color: 'var(--text-muted)',
            border: '1px solid var(--border)',
            fontFamily: 'var(--font-mono, monospace)',
          }}
        >
          {(() => {
            const payload = buildRequestPayload(
              result,
              strategy,
              backtestConfig,
              activeRec,
              optimizationGoal,
            );
            const kb = (payload.length / 1024).toFixed(1);
            const tokens = Math.round(payload.length / 4);
            return `Strategy blocks: ${strategy?.blocks?.length ?? 0} | Trades: ${result.totalTrades} | Request size: ${kb} KB (~${tokens} tokens)`;
          })()}
        </div>
      )}

      {/* Progress indicator (shared with Current Analysis view) */}
      {progressIndicator}

      {/* BTCAAAAA-38466 (Stream 5, B2) — preflight validation banners. The
          classifier is the single source of truth for which banner to
          render. Each variant ships its own one-click affordance:
            no-trades    → scroll the Run Backtest button into view
            no-provider  → push the user to Settings → AI
            timeout      → retry the most recent request
            unparseable  → copy the raw reply so the user can paste
                           it into another tool manually */}
      {preflightState.kind === 'no-trades' && (
        <div
          className="rounded p-2 text-xs flex items-start justify-between gap-2"
          role="status"
          data-testid="ai-recs-no-trades-warning"
          style={{
            background: 'var(--bg-elevated)',
            color: 'var(--accent-orange)',
            border: '1px solid var(--accent-orange)',
          }}
        >
          <div>
            <p className="font-semibold">No trades recorded</p>
            <p className="mt-1" style={{ color: 'var(--text-secondary)' }}>
              Run a backtest first before sending to AI.
            </p>
          </div>
          <button
            type="button"
            onClick={handleRunBacktestClick}
            data-testid="ai-recs-no-trades-action"
            className="px-2 py-1 rounded text-[11px] font-medium shrink-0"
            style={{
              background: 'var(--accent-orange)',
              color: 'var(--text-on-accent, #fff)',
              border: '1px solid var(--accent-orange)',
              cursor: 'pointer',
            }}
          >
            Run Backtest
          </button>
        </div>
      )}
      {preflightState.kind === 'no-provider' && (
        <div
          className="rounded p-2 text-xs flex items-start justify-between gap-2"
          role="status"
          data-testid="ai-recs-no-provider-warning"
          style={{
            background: 'var(--bg-elevated)',
            color: 'var(--accent-orange)',
            border: '1px solid var(--accent-orange)',
          }}
        >
          <div>
            <p className="font-semibold">No AI provider configured</p>
            <p className="mt-1" style={{ color: 'var(--text-secondary)' }}>
              {preflightState.providerLabel} is not set up. Open Settings → AI to configure one.
            </p>
          </div>
          <button
            type="button"
            onClick={handleOpenSettingsClick}
            data-testid="ai-recs-no-provider-action"
            className="px-2 py-1 rounded text-[11px] font-medium shrink-0"
            style={{
              background: 'var(--accent-orange)',
              color: 'var(--text-on-accent, #fff)',
              border: '1px solid var(--accent-orange)',
              cursor: 'pointer',
            }}
          >
            Open Settings
          </button>
        </div>
      )}
      {preflightState.kind === 'timeout' && (
        <div
          className="rounded p-2 text-xs flex items-start justify-between gap-2"
          role="status"
          data-testid="ai-recs-timeout-warning"
          style={{
            background: 'var(--bg-elevated)',
            color: 'var(--accent-orange)',
            border: '1px solid var(--accent-orange)',
          }}
        >
          <div>
            <p className="font-semibold">AI provider timed out</p>
            <p className="mt-1" style={{ color: 'var(--text-secondary)' }}>
              The provider did not respond in{' '}
              {preflightState.durationMs ? Math.round(preflightState.durationMs / 1000) : '?'}s.
            </p>
          </div>
          <button
            type="button"
            onClick={handleRetryClick}
            data-testid="ai-recs-timeout-action"
            className="px-2 py-1 rounded text-[11px] font-medium shrink-0"
            style={{
              background: 'var(--accent-orange)',
              color: 'var(--text-on-accent, #fff)',
              border: '1px solid var(--accent-orange)',
              cursor: 'pointer',
            }}
          >
            Retry
          </button>
        </div>
      )}
      {preflightState.kind === 'unparseable' && (
        <div
          className="rounded p-2 text-xs flex items-start justify-between gap-2"
          role="status"
          data-testid="ai-recs-unparseable-warning"
          style={{
            background: 'var(--bg-elevated)',
            color: 'var(--accent-orange)',
            border: '1px solid var(--accent-orange)',
          }}
        >
          <div>
            <p className="font-semibold">Provider response could not be parsed</p>
            <p className="mt-1" style={{ color: 'var(--text-secondary)' }}>
              The provider replied, but the response did not include a DIAGNOSIS or RECOMMENDATIONS section. Copy the raw reply and paste it into another tool if you need it.
            </p>
          </div>
          <button
            type="button"
            onClick={handleCopyUnparseableClick}
            data-testid="ai-recs-unparseable-action"
            className="px-2 py-1 rounded text-[11px] font-medium shrink-0"
            style={{
              background: 'var(--accent-orange)',
              color: 'var(--text-on-accent, #fff)',
              border: '1px solid var(--accent-orange)',
              cursor: 'pointer',
            }}
          >
            {copyUnparseableFeedback ? 'Copied' : 'Copy Response'}
          </button>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-2 justify-end mt-1 flex-wrap">
        <button
          type="button"
          onClick={handleTestConnection}
          disabled={!aiSettingsHydrated || testing}
          title="Verifies the saved AI provider/model respond to a minimal live request."
          className="px-3 py-1.5 rounded text-xs font-medium"
          style={{
            background: 'var(--bg-card)',
            color: aiSettingsHydrated && !testing ? 'var(--text-secondary)' : 'var(--text-faint)',
            border: '1px solid var(--border)',
            opacity: aiSettingsHydrated && !testing ? 1 : 0.5,
            cursor: aiSettingsHydrated && !testing ? 'pointer' : 'not-allowed',
          }}
        >
          {testing ? 'Testing…' : 'Test Connection'}
        </button>
        <button
          type="button"
          onClick={handleExport}
          disabled={!hasTrades || !isAdmin}
          title={
            !isAdmin
              ? 'Export to JSON requires an admin login.'
              : !hasTrades
                ? 'Run a backtest with trades to enable Export to JSON.'
                : 'Download the request payload as JSON.'
          }
          className="px-3 py-1.5 rounded text-xs font-medium"
          style={{
            background: 'var(--bg-card)',
            color: hasTrades && isAdmin ? 'var(--text-secondary)' : 'var(--text-faint)',
            border: '1px solid var(--border)',
            opacity: hasTrades && isAdmin ? 1 : 0.5,
            cursor: hasTrades && isAdmin ? 'pointer' : 'not-allowed',
          }}
        >
          Export to JSON
        </button>
        {analyzing && (
          <button
            type="button"
            onClick={handleCancel}
            data-testid="ai-recs-cancel"
            className="px-3 py-1.5 rounded text-xs font-medium"
            style={{
              background: 'var(--bg-card)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border)',
              cursor: 'pointer',
            }}
            title="Cancel the in-flight AI request"
          >
            Cancel
          </button>
        )}
        <button
          type="button"
          onClick={handleApproveAndSendClick}
          disabled={!canSend}
          title={
            analyzing
              ? 'Sending the request preview to the configured AI provider…'
              : 'Pick an optimization goal and send the request preview to the configured AI provider.'
          }
          className="px-3 py-1.5 rounded text-xs font-medium"
          style={{
            background: canSend ? 'var(--accent-blue)' : 'var(--bg-card)',
            color: canSend ? 'var(--text-on-accent)' : 'var(--text-faint)',
            border: '1px solid var(--border)',
            opacity: canSend ? 1 : 0.5,
            cursor: canSend ? 'pointer' : 'not-allowed',
          }}
        >
          {analyzing
            ? 'Sending…'
            : phase === 'done'
              ? 'Send Again'
              : phase === 'error'
                ? 'Retry'
                : 'Approve & Send to AI'}
        </button>
      </div>
      {testResultBanner}
    </div>
  );

  // ── RIGHT pane: per-rec Compare-style toggle cards (AC15-AC22) ──
  //
  // v3 redesign: each ParsedRec renders as its own card in the same
  // visual language as ComparePanel RunCard. Clicking the card toggles
  // the rec's apply state — applied cards have a green accent + ON badge;
  // unapplied cards are dimmed. Per-tile apply/rollback (AC18) goes
  // through the existing /api/ai/auto-apply orchestrator with a single
  // rec payload, so AC20 (real strategy save) is preserved. Rollback is
  // local-only against the snapshot we capture before each apply (server
  // rollback is a follow-up backend ticket; see AC18 inline notes).
  const rightPane = (
    <div className="flex flex-col gap-3">
      {/* BTCAAAAA-37780 / Sprint A6 — right-rail sub-tabs. The recs tab
          keeps the existing diagnosis-summary card + per-rec toggle grid;
          the diagnose tab renders the orchestrator markdown plus a
          reported-vs-per-entry metrics table and the pinned-impact
          sentence. */}
      <div
        role="tablist"
        aria-label="Right-rail views"
        data-testid="ai-recs-right-tabs"
        className="flex items-center gap-1 border-b"
        style={{ borderColor: 'var(--border)' }}
      >
        {(['recs', 'diagnose'] as const).map((t) => {
          const isActive = rightTab === t;
          const label = t === 'recs' ? 'Recommendations' : 'Diagnose';
          return (
            <button
              key={t}
              id={`ai-recs-right-tab-${t}`}
              type="button"
              role="tab"
              aria-selected={isActive}
              aria-controls={`ai-recs-right-panel-${t}`}
              tabIndex={isActive ? 0 : -1}
              onClick={() => setRightTab(t)}
              onKeyDown={(e) => handleRightTabKeyDown(e, t)}
              ref={(el) => { if (el) rightTabRefs.current.set(t, el); else rightTabRefs.current.delete(t); }}
              data-testid={`ai-recs-right-tab-${t}`}
              className="px-3 py-1.5 text-xs font-medium rounded-t"
              style={{
                background: isActive ? 'var(--bg-card)' : 'transparent',
                color: isActive ? 'var(--text-secondary)' : 'var(--text-faint)',
                border: '1px solid var(--border)',
                borderBottom: isActive ? '1px solid var(--bg-card)' : '1px solid var(--border)',
                marginBottom: isActive ? '-1px' : '0',
                cursor: 'pointer',
              }}
            >
              {label}
            </button>
          );
        })}
      </div>

      {rightTab === 'recs' && (<div id="ai-recs-right-panel-recs" role="tabpanel" aria-labelledby="ai-recs-right-tab-recs">
      {/* Diagnosis card: compact summary at the top so the grid below has
          room. The detailed prose is still rendered in full; we just do
          not crowd it next to the per-rec cards. */}
      <div
        className="rounded p-3"
        style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
      >
        <p
          className="text-xs font-semibold uppercase tracking-wide mb-2"
          style={{ color: 'var(--text-muted)' }}
        >
          STRATEGY DIAGNOSIS
        </p>
        {aiAnalysis?.diagnosis ? (
          <p
            className="text-xs whitespace-pre-wrap"
            style={{ color: 'var(--text-secondary)' }}
          >
            {aiAnalysis.diagnosis}
          </p>
        ) : aiAnalysis?.raw ? (
          <p
            className="text-xs whitespace-pre-wrap"
            style={{ color: 'var(--text-secondary)' }}
          >
            {aiAnalysis.raw}
          </p>
        ) : (
          <p className="text-xs" style={{ color: 'var(--text-faint)' }}>
            {result
              ? 'Awaiting AI analysis. Use “Approve & Send to AI” below once the request preview is verified.'
              : 'Run a backtest first, then use “Approve & Send to AI” to receive a strategy diagnosis.'}
          </p>
        )}
      </div>

      {/* Q7 (BTCAAAAA-38564): when viewing a past analysis, show a read-only
          banner above the KPI bar so the user knows they're in snapshot mode. */}
      {viewingHistoryEntry && (
        <div
          data-testid="ai-recs-history-snapshot-banner"
          className="rounded px-3 py-2 text-xs flex items-center justify-between gap-2"
          style={{
            background: 'var(--accent-blue-soft)',
            border: '1px solid var(--accent-blue)',
            color: 'var(--text-secondary)',
          }}
        >
          <span>
            Viewing past analysis —{' '}
            <span style={{ color: 'var(--text-muted)' }}>
              Re-analyze to return to live mode.
            </span>
          </span>
          <button
            type="button"
            onClick={() => setViewingHistoryEntry(null)}
            className="text-[10px] px-2 py-0.5 rounded"
            style={{
              background: 'var(--bg-elevated)',
              color: 'var(--text-muted)',
              border: '1px solid var(--border)',
              cursor: 'pointer',
            }}
          >
            Dismiss
          </button>
        </div>
      )}

      {/* BTCAAAAA-37774 Sprint A2 — Strategy Impact KPI bar.
          Q7: when viewing a history snapshot use the stored KPIs; otherwise
          fall back to the live backtest result.
          BTCAAAAA-37772 Sprint B/B4 — reProjectFn wires in the real endpoint. */}
      {(result || viewingHistoryEntry?.snapshotKpis || demoMode) && (
        <StrategyImpactKpiBar
          baseline={viewingHistoryEntry?.snapshotKpis ?? baselineKpis}
          appliedImpacts={viewingHistoryEntry ? [] : appliedImpacts}
          reProjectFn={viewingHistoryEntry || demoMode ? undefined : reProjectFn}
        />
      )}

      {/* AC15: RECOMMENDATIONS header + card grid (ComparePanel layout). */}
      <div className="flex flex-col gap-2">
        <div className="flex items-baseline justify-between">
          <p
            className="text-xs font-semibold uppercase tracking-wide"
            style={{ color: 'var(--text-muted)' }}
          >
            RECOMMENDATIONS
            {parsedRecs.length > 0 && (
              <span
                className="ml-1.5 text-[10px] font-normal"
                style={{ color: 'var(--text-faint)' }}
              >
                {demoMode
                  ? `· ${appliedRecIds.length} on`
                  : `(${visibleRecs.length} · ${appliedRecIds.length} applied${
                      hiddenRecCount > 0 ? ` · ${hiddenRecCount} hidden` : ''
                    })`}
              </span>
            )}
            {/* BTCAAAAA-38464 (Stream 3, L2): low-confidence disclosure toggle.
                Only meaningful when there is actually something hidden by the
                floor; rendering the button when `hiddenRecCount === 0` would
                just add visual noise without a payload. */}
            {hiddenRecCount > 0 && (
              <button
                type="button"
                onClick={() => setShowLowConfidenceRecs((v) => !v)}
                data-testid="ai-recs-toggle-low-confidence"
                aria-pressed={showLowConfidenceRecs}
                className="ml-2 px-1.5 py-0.5 text-[10px] rounded underline"
                style={{
                  background: 'transparent',
                  color: 'var(--accent-blue)',
                  border: 'none',
                  cursor: 'pointer',
                }}
                title={
                  showLowConfidenceRecs
                    ? 'Hide recs below the confidence floor'
                    : 'Show all recs, including those below the confidence floor'
                }
              >
                {showLowConfidenceRecs
                  ? 'Hide low-confidence recs'
                  : 'Show low-confidence recs'}
              </button>
            )}
          </p>
          {/* BTCAAAAA-36917 v4 UX: surfaced only when demoMode is true so
              the user can return to a clean empty state without a page
              reload. Clicking it nulls aiAnalysis + resets both flags. */}
          {demoMode && (
            <button
              type="button"
              onClick={() => {
                setDemoMode(false);
                setPreviewMode(false);
                setAiAnalysis(null);
              }}
              className="text-[10px] underline"
              style={{
                background: 'transparent',
                color: 'var(--text-faint)',
                border: 'none',
                cursor: 'pointer',
                padding: 0,
              }}
              data-testid="ai-recs-exit-demo-btn"
              title="Clear the demo data and return to the empty state."
            >
              Exit demo
            </button>
          )}
        </div>
        {parsedRecs.length === 0 ? (
          <div
            className="rounded p-3"
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderTop: '3px solid var(--accent-blue)',
            }}
          >
            {/* When there IS recommendations text but parsing didn't split it
                into individual cards, show the raw text rather than an empty
                placeholder. The user gets readable content; the toggle-card
                feature message explains why cards aren't showing. */}
            {aiAnalysis?.recommendations ? (
              <div className="flex flex-col gap-2">
                <p className="text-[10px]" style={{ color: 'var(--text-faint)' }}>
                  Could not split into individual toggle-cards. Showing the raw recommendations below.
                </p>
                <pre
                  className="text-xs rounded p-2 overflow-auto max-h-64 whitespace-pre-wrap break-words"
                  style={{
                    background: 'var(--bg-elevated)',
                    color: 'var(--text-secondary)',
                    border: '1px solid var(--border)',
                    fontFamily: 'var(--font-mono, monospace)',
                  }}
                >
                  {aiAnalysis.recommendations}
                </pre>
              </div>
            ) : (
              <p className="text-xs" style={{ color: 'var(--text-faint)' }}>
                {aiAnalysis
                  ? 'No recommendations yet. Recommendations appear here after AI analysis completes.'
                  : result
                    ? 'No recommendations yet. Recommendations appear here after AI analysis completes.'
                    : 'No results yet. Run a backtest to generate recommendations.'}
              </p>
            )}

            {/* BTCAAAAA-36917 v4 UX: empty-state preview + demo affordances.
                Visible whenever parsedRecs is empty. Preview renders one
                static card inline without touching aiAnalysis; Demo
                populates aiAnalysis with the hardcoded sample payload
                (the cache persistence effect skips writes while demoMode
                is true, so neither path pollutes sessionStorage). */}
            {!previewMode && !demoMode && (
              <div
                className="mt-2 flex flex-wrap gap-2"
                data-testid="ai-recs-empty-actions"
              >
                <button
                  type="button"
                  onClick={() => setPreviewMode(true)}
                  className="px-2 py-1 text-[11px] rounded"
                  style={{
                    background: 'var(--bg-elevated)',
                    color: 'var(--text-secondary)',
                    border: '1px solid var(--border)',
                    cursor: 'pointer',
                  }}
                  data-testid="ai-recs-preview-btn"
                  title="Show one sample card so you can see the v3 layout without running a backtest."
                >
                  Preview the new layout
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setDemoMode(true);
                    setAiAnalysis({
                      diagnosis: SAMPLE_DIAGNOSIS,
                      recommendations: SAMPLE_RECOMMENDATIONS,
                      raw: `DIAGNOSIS: ${SAMPLE_DIAGNOSIS}\n\nRECOMMENDATIONS: ${SAMPLE_RECOMMENDATIONS}`,
                    });
                  }}
                  className="px-2 py-1 text-[11px] rounded"
                  style={{
                    background: 'var(--bg-elevated)',
                    color: 'var(--text-secondary)',
                    border: '1px solid var(--border)',
                    cursor: 'pointer',
                  }}
                  data-testid="ai-recs-demo-btn"
                  title="Seed sample diagnosis + recommendations to explore the v3 toggle-card grid."
                >
                  Load demo data
                </button>
              </div>
            )}

            {previewMode && (
              <div className="mt-2 flex flex-col gap-2">
                <div
                  className="rounded p-2 text-left text-[11px] flex flex-col gap-1.5"
                  style={{
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border)',
                    borderTop: '3px solid var(--accent-blue)',
                    opacity: 0.85,
                  }}
                  data-testid="ai-recs-preview-card"
                  data-preview-rec="1"
                  aria-label="Preview of a v3 toggle-card (sample data)"
                >
                  <div
                    className="flex items-center justify-between gap-2"
                    data-testid="ai-recs-preview-header"
                  >
                    <p
                      className="text-[10px] font-semibold uppercase tracking-wide"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      Request preview
                    </p>
                    <span
                      className="text-[9px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded"
                      style={{
                        background: 'var(--accent-blue-soft)',
                        color: 'var(--accent-blue)',
                        border: '1px solid var(--accent-blue)',
                      }}
                      data-testid="ai-recs-preview-outcome-pill"
                      title="Outcome of the request preview"
                    >
                      Request outcome · Ready
                    </span>
                  </div>
                  <div className="flex items-start justify-between gap-1.5">
                    <p
                      className="font-semibold truncate flex-1"
                      style={{ color: 'var(--text-secondary)' }}
                      title="Widen the EMA trend filter window"
                    >
                      Widen the EMA trend filter window
                    </p>
                    <span
                      className="text-[9px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded"
                      style={{
                        background: 'var(--bg-card)',
                        color: 'var(--text-faint)',
                        border: '1px solid var(--border)',
                      }}
                      data-testid="ai-recs-toggle-badge"
                    >
                      OFF
                    </span>
                  </div>
                  <p
                    className="text-[10px] truncate"
                    style={{ color: 'var(--text-faint)' }}
                    title="type: signal"
                  >
                    signal
                  </p>
                  <ul
                    className="flex flex-col gap-0.5"
                    data-testid="ai-recs-toggle-params"
                  >
                    <li
                      className="font-mono text-[10px] truncate"
                      style={{ color: 'var(--text-secondary)' }}
                      title="ema_window = 100"
                    >
                      ema_window = 100
                    </li>
                  </ul>
                  <p
                    className="text-[10px] line-clamp-2"
                    style={{ color: 'var(--text-faint)' }}
                    title="50-period EMA is too restrictive in the current chop; wider window lets more setups through."
                  >
                    50-period EMA is too restrictive in the current chop; wider window lets more setups through.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setPreviewMode(false)}
                    className="px-2 py-1 text-[11px] rounded"
                    style={{
                      background: 'transparent',
                      color: 'var(--text-faint)',
                      border: '1px solid var(--border)',
                      cursor: 'pointer',
                    }}
                    data-testid="ai-recs-preview-close"
                  >
                    Hide preview
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setPreviewMode(false);
                      setDemoMode(true);
                      setAiAnalysis({
                        diagnosis: SAMPLE_DIAGNOSIS,
                        recommendations: SAMPLE_RECOMMENDATIONS,
                        raw: `DIAGNOSIS: ${SAMPLE_DIAGNOSIS}\n\nRECOMMENDATIONS: ${SAMPLE_RECOMMENDATIONS}`,
                      });
                    }}
                    className="px-2 py-1 text-[11px] rounded"
                    style={{
                      background: 'var(--bg-elevated)',
                      color: 'var(--text-secondary)',
                      border: '1px solid var(--border)',
                      cursor: 'pointer',
                    }}
                    data-testid="ai-recs-demo-btn-inline"
                  >
                    Load demo data instead
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {/* BTCAAAAA-38438: per-tile error strip above the row so the
                error pill does not collide with the mockup-aligned toggle
                inside the card body. BTCAAAAA-38468 feedback capture flows
                through the `dataAttributes` spread on RecommendationCard. */}
            {parsedRecs.some((r) => perTileError[r.id]) && (
              <ul
                className="flex flex-col gap-1"
                data-testid="ai-recs-error-strip"
              >
                {parsedRecs.map((rec) => {
                  const errMsg = perTileError[rec.id];
                  if (!errMsg) return null;
                  return (
                    <li
                      key={`err-${rec.id}`}
                      className="text-[11px] flex items-center gap-2 rounded px-2 py-1"
                      style={{
                        background: 'var(--accent-red-soft)',
                        color: 'var(--accent-red)',
                        border: '1px solid var(--accent-red)',
                      }}
                      data-testid="ai-recs-toggle-error"
                      role="alert"
                    >
                      <span className="font-semibold">{rec.title}:</span>
                      <span>{errMsg}</span>
                    </li>
                  );
                })}
              </ul>
            )}
            <RecommendationsRow
              analysisId={lastAnalysisHash ?? strategy?.id ?? ''}
              recommendations={(() => {
                const conflictMap = detectConflicts(parsedRecs);
                return parsedRecs.map((rec) => {
                  const isApplied = appliedRecIds.includes(rec.id);
                  const isApplyingThis = perTileApplying.includes(rec.id);
                  const isStructural = STRUCTURAL_TYPES.has((rec.type ?? '').toUpperCase());
                  const isAutoApplicable = isStructural || !!(rec.parameter && rec.suggestedValue);
                  const recConflict = conflictMap.get(rec.id);
                  const isConflictLoser = !!recConflict?.isConflictLoser;
                  const base = toCardData(rec, {
                    applied: isApplied,
                    isApplyingThis,
                    isAutoApplicable,
                    onToggleApplied: () => {
                      if (!strategy?.id || isApplyingThis || !isAutoApplicable || isConflictLoser) return;
                      handleToggleRec(rec);
                    },
                    preApplySnapshots,
                    analysisId: lastAnalysisHash ?? strategy?.id ?? '',
                  });
                  if (!isConflictLoser) {
                    return { ...base, dataAttributes: { ...base.dataAttributes, 'data-conflict-loser': 'false' } };
                  }
                  return {
                    ...base,
                    disabled: true,
                    conflictBadge: { label: 'Conflict', tooltip: recConflict?.conflictTooltip ?? '' },
                    dataAttributes: {
                      ...base.dataAttributes,
                      'data-conflict-loser': 'true',
                      'aria-disabled': 'true',
                      title: recConflict?.conflictTooltip ?? '',
                    },
                  };
                });
              })()}
            />
          </div>
        )}
      </div>

      {/* Per-tile saves are now the action surface (AC20). No more
          sticky "Apply all" footer — apply is per-card. */}
      </div>)}

      {!demoMode && parsedRecs.length > 0 && (
        <ReverseViewBanner pattern={extractReverseViewPattern(reverseViewInputs)} />
      )}

      {rightTab === 'diagnose' && (
        <div id="ai-recs-right-panel-diagnose" role="tabpanel" aria-labelledby="ai-recs-right-tab-diagnose">
          <DiagnosePane
            diagnosis={aiAnalysis?.diagnosis ?? aiAnalysis?.raw ?? ''}
            rows={diagnoseRows}
            stagedSentence={stagedSentence}
            hasResult={!!result}
          />
        </div>
      )}
    </div>
  );

  const entriesChip = result?.totalTrades ?? 0;
  const pfChip = formatPF(result?.profitFactor);
  const wrChip = formatWR(result?.winRate);

  return (
    <div className="flex flex-col gap-3">
      {/* BTCAAAAA-37773 / Sprint A1 — persistent header row.
          Left: realtime applied-changes indicator.
          Right: entries · PF · WR · Re-analyze · Pop Out ↗ */}
      <div
        data-testid="ai-recs-header"
        className="flex items-center justify-between gap-3 flex-wrap"
      >
        <div
          data-testid="ai-recs-realtime"
          className="flex items-center gap-1.5 text-[11px]"
          style={{
            color: 'var(--text-muted)',
            fontFamily: 'var(--font-mono, monospace)',
          }}
          title="Number of recommendations currently applied to the strategy."
        >
          <span
            aria-hidden="true"
            className="inline-block w-1.5 h-1.5 rounded-full"
            style={{ background: 'var(--accent-green)' }}
          />
          <span>Realtime</span>
          <span style={{ color: 'var(--text-faint)' }} aria-hidden="true">·</span>
          <span data-testid="ai-recs-realtime-count">
            {appliedRecIds.length} {appliedRecIds.length === 1 ? 'change' : 'changes'} applied
          </span>
        </div>
        <div
          data-testid="ai-recs-header-chips"
          className="flex items-center gap-2 text-[11px]"
          style={{
            color: 'var(--text-muted)',
            fontFamily: 'var(--font-mono, monospace)',
          }}
        >
          <span data-testid="ai-recs-chip-entries" title="Trade count from the last backtest">
            {entriesChip} entries
          </span>
          <span style={{ color: 'var(--text-faint)' }} aria-hidden="true">·</span>
          <span data-testid="ai-recs-chip-pf" title="Profit factor">PF {pfChip}</span>
          <span style={{ color: 'var(--text-faint)' }} aria-hidden="true">·</span>
          <span data-testid="ai-recs-chip-wr" title="Win rate">WR {wrChip}</span>
          <span style={{ color: 'var(--text-faint)' }} aria-hidden="true">·</span>
          <button
            type="button"
            onClick={handleReanalyzeClick}
            disabled={reanalyzeDisabled}
            title={reanalyzeTooltip}
            data-testid="ai-recs-reanalyze"
            data-dirty={isDirty ? 'true' : 'false'}
            data-analyzing={analyzing ? 'true' : 'false'}
            aria-busy={analyzing}
            className="px-2 py-1 rounded text-[11px] font-medium inline-flex items-center gap-1"
            style={{
              background: analyzing || !reanalyzeDisabled ? 'var(--accent-blue)' : 'var(--bg-card)',
              color: analyzing || !reanalyzeDisabled ? 'var(--text-on-accent)' : 'var(--text-faint)',
              border: '1px solid var(--border)',
              opacity: analyzing ? 0.9 : reanalyzeDisabled ? 0.5 : 1,
              cursor: reanalyzeDisabled ? 'not-allowed' : 'pointer',
            }}
          >
            {analyzing ? (
              <>
                <span
                  aria-hidden="true"
                  className="inline-block w-3 h-3 rounded-full animate-spin"
                  style={{
                    border: '2px solid var(--text-on-accent)',
                    borderTopColor: 'transparent',
                  }}
                />
                <span>{progressLabel || 'Analyzing'}{progressPercent ? ` ${progressPercent}%` : '…'}</span>
              </>
            ) : (
              'Re-analyze'
            )}
          </button>
          <button
            type="button"
            onClick={handleTestConnection}
            disabled={!aiSettingsHydrated || testing}
            title="Verifies the saved AI provider/model respond to a minimal live request."
            data-testid="ai-recs-test-connection-header"
            className="px-2 py-1 rounded text-[11px] font-medium"
            style={{
              background: 'var(--bg-card)',
              color: aiSettingsHydrated && !testing ? 'var(--text-secondary)' : 'var(--text-faint)',
              border: '1px solid var(--border)',
              opacity: aiSettingsHydrated && !testing ? 1 : 0.5,
              cursor: aiSettingsHydrated && !testing ? 'pointer' : 'not-allowed',
            }}
          >
            {testing ? 'Testing…' : 'Test Connection'}
          </button>
          <button
            type="button"
            onClick={handlePopOut}
            title="Open this panel in a detached window"
            data-testid="ai-recs-popout"
            className="px-2 py-1 rounded text-[11px] font-medium flex items-center gap-1"
            style={{
              background: 'var(--bg-card)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border)',
              cursor: 'pointer',
            }}
          >
            Pop Out
            <ExternalLink size={11} aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* BTCAAAAA-37771 review — live status for Re-analyze / Test Connection
          triggered from this header. Only the AI Request tab renders these
          inline in leftPane, so guard against double-rendering there. */}
      {currentView !== 'request' && progressIndicator}
      {currentView !== 'request' && testResultBanner}

      {/* Tabs */}
      <div
        role="tablist"
        aria-label="AI recommendations views"
        className="flex items-center gap-1 border-b"
        style={{ borderColor: 'var(--border)' }}
      >
        {VIEW_ORDER.map((v) => {
          const isActive = view === v;
          return (
            <button
              key={v}
              id={`ai-recs-tab-${v}`}
              type="button"
              role="tab"
              aria-selected={isActive}
              aria-controls={`ai-recs-panel-${v}`}
              tabIndex={isActive ? 0 : -1}
              onClick={() => setView(v)}
              onKeyDown={(e) => handleMainTabKeyDown(e, v)}
              ref={(el) => { if (el) mainTabRefs.current.set(v, el); else mainTabRefs.current.delete(v); }}
              data-testid={`ai-recs-tab-${v}`}
              className="px-3 py-1.5 text-xs font-medium rounded-t"
              style={{
                background: isActive ? 'var(--bg-card)' : 'transparent',
                color: isActive ? 'var(--text-secondary)' : 'var(--text-faint)',
                border: '1px solid var(--border)',
                borderBottom: isActive ? '1px solid var(--bg-card)' : '1px solid var(--border)',
                marginBottom: isActive ? '-1px' : '0',
                cursor: 'pointer',
              }}
            >
              {VIEW_LABELS[v]}
              {v === 'history' && history.hydrated && history.entries.length > 0 && (
                <span className="ml-1.5 text-[10px]" style={{ color: 'var(--text-faint)' }}>
                  ({history.entries.length})
                </span>
              )}
            </button>
          );
        })}
      </div>

{currentView === 'current' ? (
        <div
          id="ai-recs-panel-current"
          role="tabpanel"
          aria-labelledby="ai-recs-tab-current"
          data-testid="ai-recs-current-with-rail"
          className="flex gap-3"
          style={{ flexWrap: 'wrap', alignItems: 'flex-start' }}
        >
          <div style={{ flex: '1 1 0', minWidth: 0 }}>
            {rightPane}
          </div>
          {/* marginTop offsets the sub-tab bar (py-1.5 + text-xs + border-b ≈ 29px) plus gap-3 (12px)
              so the rail top-edge aligns with the Strategy Diagnosis card below the tabs. */}
          <div style={{ marginTop: '41px' }}>
            <StrategyAfterChangesRail
              items={afterChangesItems}
              toggleOn={appliedRecIdSet}
              onToggleCurrent={handleRailToggleCurrent}
              onJumpToOriginEntry={handleRailJumpToOriginEntry}
              demoLegs={demoMode ? DEMO_RAIL_LEGS : undefined}
            />
          </div>
        </div>
      ) : currentView === 'request' ? (
        <div id="ai-recs-panel-request" role="tabpanel" aria-labelledby="ai-recs-tab-request" data-testid="ai-recs-view-request">{leftPane}</div>
      ) : currentView === 'response' ? (
        (() => {
          const rawReply =
            history.entries[0]?.raw || aiAnalysis?.raw || '';
          return (
            <div
              id="ai-recs-panel-response"
              role="tabpanel"
              aria-labelledby="ai-recs-tab-response"
              data-testid="ai-recs-view-response"
              className="flex flex-col gap-2"
            >
              {/* BTCAAAAA-38300 — header row matching BTC-37748 mockup
                  (mockup 04.png): AI RESPONSE label · RAW MODEL REPLY
                  badge · provider/tokens/duration · Copy button. */}
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <div className="flex items-center gap-2 flex-wrap">
                  <span
                    className="text-xs font-semibold uppercase tracking-wide"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    AI RESPONSE
                  </span>
                  <span
                    data-testid="ai-recs-raw-badge"
                    className="text-[10px] px-1.5 py-0.5 rounded font-semibold uppercase tracking-wide"
                    style={{
                      background: 'var(--accent-blue-soft)',
                      color: 'var(--accent-blue)',
                      border: '1px solid var(--accent-blue)',
                    }}
                  >
                    RAW MODEL REPLY
                  </span>
                  {responseMeta && (
                    <span
                      data-testid="ai-recs-response-meta"
                      className="text-[11px]"
                      style={{
                        color: 'var(--text-faint)',
                        fontFamily: 'var(--font-mono, monospace)',
                      }}
                    >
                      {responseMeta.provider}, {responseMeta.tokens} tokens ·{' '}
                      {(responseMeta.durationMs / 1000).toFixed(1)}s
                    </span>
                  )}
                </div>
                <button
                  type="button"
                  onClick={handleCopyResponse}
                  disabled={!rawReply}
                  data-testid="ai-recs-copy-response"
                  className="px-2 py-1 rounded text-[10px] font-medium"
                  style={{
                    background: 'var(--bg-elevated)',
                    color: responseCopied
                      ? 'var(--accent-green-on)'
                      : 'var(--text-secondary)',
                    border: '1px solid var(--border)',
                    cursor: rawReply ? 'pointer' : 'not-allowed',
                    opacity: rawReply ? 1 : 0.5,
                  }}
                >
                  {responseCopied ? 'Copied' : 'Copy'}
                </button>
              </div>
              {rawReply ? (
                <pre
                  data-testid="ai-recs-raw-reply"
                  className="rounded p-3 text-xs whitespace-pre-wrap"
                  style={{
                    background: 'var(--bg-elevated)',
                    color: 'var(--text-secondary)',
                    border: '1px solid var(--border)',
                    fontFamily: 'var(--font-mono, monospace)',
                    minHeight: 360,
                    maxHeight: '70vh',
                    overflow: 'auto',
                  }}
                >
                  {rawReply}
                </pre>
              ) : (
                <div
                  className="rounded p-4 text-xs text-center"
                  style={{
                    background: 'var(--bg-card)',
                    color: 'var(--text-faint)',
                    border: '1px solid var(--border)',
                  }}
                >
                  No AI response yet — run an analysis from the Current Analysis tab.
                </div>
              )}
            </div>
          );
        })()
      ) : (
        <div id="ai-recs-panel-history" role="tabpanel" aria-labelledby="ai-recs-tab-history" style={{ minWidth: 0, overflow: 'hidden' }}>
          <HistoryView
            entries={history.entries}
            hydrated={history.hydrated}
            onUpdateStatus={history.updateStatus}
            onUpdateNotes={history.updateNotes}
            onRequestDelete={requestDelete}
            onRequestClearAll={requestClearAll}
            onLoadIntoCurrent={loadHistoryIntoCurrent}
          />
        </div>
      )}

      {confirmation && (
        <ConfirmationModal
          confirmation={confirmation}
          onCancel={cancelConfirmation}
          onConfirmClearAll={confirmClearAll}
          onConfirmDelete={confirmDelete}
        />
      )}

      {goalModalOpen && (
        <OptimizationGoalModal
          onCancel={handleGoalCancel}
          onConfirm={handleGoalConfirm}
        />
      )}
    </div>
  );
}
