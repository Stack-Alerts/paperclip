import { validateStrategyLocal, enrichReportWithNarrative } from '../validation';
import {
  BlockType,
  StrategyStatus,
  ValidationSeverity,
  type Block,
  type Strategy,
  type ValidationReport,
} from '../types';

// jsdom in this project does not expose `fetch` on globalThis (and may not
// expose `Response` either), so install a no-op polyfill before any test that
// needs to spy on it. validateStrategyLocal must not call fetch (regression
// for BTC-32994); the polyfill lets us assert that explicitly. We use a
// structurally-typed fake instead of `new Response(...)` so the polyfill is
// safe to evaluate even when `Response` is missing from the global scope.
if (typeof globalThis.fetch !== 'function') {
  const fakeResponse = {
    ok: true,
    status: 200,
    statusText: 'OK',
    json: () => Promise.resolve({}),
    text: () => Promise.resolve('{}'),
  } as unknown as Response;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (globalThis as any).fetch = () => Promise.resolve(fakeResponse);
}

function makeStrategy(overrides: Partial<{
  name: string;
  blocks: Block[];
  timeframe: string | undefined;
  targetMarket: string | undefined;
  status: StrategyStatus;
}> = {}): Strategy {
  const blocks: Block[] = overrides.blocks ?? [
    {
      id: 'entry-1',
      type: BlockType.INDICATOR,
      index: 0,
      data: {
        name: 'Entry Block',
        category: 'required',
        logic: 'AND',
        signals: [
          {
            id: 'sig-1',
            name: 'BULLISH_BREAK',
            weight: 1,
          },
        ],
      },
    },
    {
      id: 'exit-1',
      type: BlockType.EXIT_CONDITION,
      index: 1,
      data: {
        signalName: 'TAKE_PROFIT',
        exitMode: 'ABSOLUTE',
        percentage: 0.5,
      },
    },
  ];
  return {
    id: 'strat-1',
    name: overrides.name ?? 'Test Strategy',
    status: overrides.status ?? StrategyStatus.DRAFT,
    blocks,
    settings: {
      // Use `in` rather than `??` so callers can explicitly set
      // timeframe/targetMarket to `undefined` and exercise the
      // missing-timeframe / missing-target-market warning paths.
      // `validateStrategyLocal` checks `!settings.timeframe` (truthy), so
      // undefined at runtime still triggers the warning; the type assertion
      // here is a strict-mode concession that the helper lies about the
      // never-undefined invariant of StrategySettings.timeframe.
      timeframe: ('timeframe' in overrides ? overrides.timeframe : '1h') as string,
      targetMarket: ('targetMarket' in overrides ? overrides.targetMarket : 'BTC/USDT') as string,
    },
    createdAt: '2026-06-23T10:00:00.000Z',
    updatedAt: '2026-06-23T10:00:00.000Z',
  };
}

describe('validateStrategyLocal — BTC-32994 regression', () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  // The pre-fix bug wired useStrategyStore.validateStrategy() to
  // POST /strategies/{id}/validate (a non-existent endpoint), so the UI
  // surfaced an "api error" instead of a ValidationReport. The fix routes
  // the call to validateStrategyLocal(), a pure synchronous function that
  // must always return a usable ValidationReport.
  it('returns a usable ValidationReport shape for a well-formed strategy (no API call)', () => {
    const fetchSpy = jest.spyOn(globalThis, 'fetch').mockImplementation(() => {
      throw new Error('validateStrategyLocal must not hit the network');
    });

    const report = validateStrategyLocal(makeStrategy());

    expect(report).toBeDefined();
    expect(typeof report.is_valid).toBe('boolean');
    expect(typeof report.timestamp).toBe('string');
    expect(report.strategy_summary.name).toBe('Test Strategy');
    expect(Array.isArray(report.critical_issues)).toBe(true);
    expect(Array.isArray(report.errors)).toBe(true);
    expect(Array.isArray(report.warnings)).toBe(true);
    expect(Array.isArray(report.notices)).toBe(true);
    expect(Array.isArray(report.info)).toBe(true);
    expect(report.complexity_metrics.complexity_score).toBeGreaterThanOrEqual(0);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('always emits the backend_validation_unavailable info notice (local-fallback marker)', () => {
    const report = validateStrategyLocal(makeStrategy());
    const infoRules = report.info.map((i) => i.rule_id);
    expect(infoRules).toContain('backend_validation_unavailable');
    const notice = report.info.find((i) => i.rule_id === 'backend_validation_unavailable');
    expect(notice?.severity).toBe(ValidationSeverity.INFO);
  });

  it('flags missing entry condition as a CRITICAL issue', () => {
    const strategy = makeStrategy({
      blocks: [
        {
          id: 'exit-1',
          type: BlockType.EXIT_CONDITION,
          index: 0,
          data: { signalName: 'TAKE_PROFIT', exitMode: 'ABSOLUTE', percentage: 0.5 },
        },
      ],
    });
    const report = validateStrategyLocal(strategy);

    const ruleIds = report.critical_issues.map((i) => i.rule_id);
    expect(ruleIds).toContain('missing_entry_condition');
    expect(report.is_valid).toBe(false);
  });

  it('flags missing exit condition as a CRITICAL issue', () => {
    const strategy = makeStrategy({
      blocks: [
        {
          id: 'entry-1',
          type: BlockType.INDICATOR,
          index: 0,
          data: {
            name: 'Entry Block',
            category: 'required',
            logic: 'AND',
            signals: [{ id: 'sig-1', name: 'BULLISH_BREAK', weight: 1 }],
          },
        },
      ],
    });
    const report = validateStrategyLocal(strategy);

    const ruleIds = report.critical_issues.map((i) => i.rule_id);
    expect(ruleIds).toContain('missing_exit_condition');
    expect(report.is_valid).toBe(false);
  });

  it('flags missing timeframe as a WARNING with auto_fix marker', () => {
    const strategy = makeStrategy({ timeframe: undefined });
    const report = validateStrategyLocal(strategy);

    const timeframeWarn = report.warnings.find((i) => i.rule_id === 'missing_timeframe');
    expect(timeframeWarn).toBeDefined();
    expect(timeframeWarn?.severity).toBe(ValidationSeverity.WARNING);
    expect(timeframeWarn?.auto_fix_available).toBe(true);
  });

  it('flags missing target market as a WARNING with auto_fix marker', () => {
    const strategy = makeStrategy({ targetMarket: undefined });
    const report = validateStrategyLocal(strategy);

    const marketWarn = report.warnings.find((i) => i.rule_id === 'missing_target_market');
    expect(marketWarn).toBeDefined();
    expect(marketWarn?.severity).toBe(ValidationSeverity.WARNING);
    expect(marketWarn?.auto_fix_available).toBe(true);
  });

  it('flags unnamed strategy as a WARNING', () => {
    const strategy = makeStrategy({ name: '   ' });
    const report = validateStrategyLocal(strategy);

    const nameWarn = report.warnings.find((i) => i.rule_id === 'missing_strategy_name');
    expect(nameWarn).toBeDefined();
    expect(nameWarn?.severity).toBe(ValidationSeverity.WARNING);
  });

  it('returns is_valid=true and emits narrative (executionFlow/confluenceScoring/scenarios) for a complete strategy', () => {
    const report = validateStrategyLocal(makeStrategy());

    expect(report.is_valid).toBe(true);
    expect(report.critical_issues).toHaveLength(0);
    expect(report.errors).toHaveLength(0);
    expect(report.executionFlow).toBeDefined();
    expect(report.executionFlow?.blocks.length).toBeGreaterThan(0);
    expect(report.executionFlow?.strategyLevelExits.length).toBeGreaterThan(0);
    expect(report.confluenceScoring).toBeDefined();
    expect(report.scenarios).toBeDefined();
  });

  it('does not make any HTTP/fetch call (regression: pre-fix called non-existent POST endpoint)', () => {
    // Use a structurally-typed fake Response — jsdom in this project does not
    // expose the `Response` constructor, so `new Response(...)` throws. The
    // return value is irrelevant here: we only assert the spy was not called.
    const fakeResponse = { ok: true, status: 200 } as unknown as Response;
    const fetchSpy = jest.spyOn(globalThis, 'fetch').mockResolvedValue(fakeResponse);

    validateStrategyLocal(makeStrategy());

    expect(fetchSpy).not.toHaveBeenCalled();
  });
});

describe('enrichReportWithNarrative', () => {
  it('merges narrative fields onto a backend ValidationReport without losing backend issues', () => {
    const strategy = makeStrategy();
    const backendReport: ValidationReport = {
      is_valid: true,
      timestamp: '2026-06-23T10:00:00.000Z',
      strategy_summary: { name: strategy.name, version: '1' },
      critical_issues: [],
      errors: [],
      warnings: [],
      notices: [],
      info: [],
      complexity_metrics: { complexity_score: 10 },
    };

    const merged = enrichReportWithNarrative(backendReport, strategy);

    expect(merged.critical_issues).toEqual(backendReport.critical_issues);
    expect(merged.warnings).toEqual(backendReport.warnings);
    expect(merged.executionFlow).toBeDefined();
    expect(merged.confluenceScoring).toBeDefined();
    expect(merged.scenarios).toBeDefined();
  });

  it('returns the original report unchanged when narrative generation throws', () => {
    const backendReport: ValidationReport = {
      is_valid: true,
      timestamp: '2026-06-23T10:00:00.000Z',
      strategy_summary: { name: 'x' },
      critical_issues: [],
      errors: [],
      warnings: [],
      notices: [],
      info: [],
      complexity_metrics: { complexity_score: 0 },
    };

    // The strategy.blocks array is non-iterable (frozen symbol) which makes
    // Array.isArray(...).filter throw. enrichReportWithNarrative must catch.
    const badStrategy = {
      ...makeStrategy(),
      get blocks() {
        return 42 as unknown as Block[];
      },
    } as unknown as Strategy;

    const out = enrichReportWithNarrative(backendReport, badStrategy);
    expect(out).toBe(backendReport);
  });
});
