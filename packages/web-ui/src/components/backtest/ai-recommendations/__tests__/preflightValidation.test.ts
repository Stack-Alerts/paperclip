import {
  classifyPreflight,
  isUnparseableResponse,
  scrollToBacktestButton,
  DEFAULT_SETTINGS_HREF,
  PreflightContext,
} from '../preflightValidation';

function baseCtx(overrides: Partial<PreflightContext> = {}): PreflightContext {
  return {
    hydrated: true,
    hasTrades: true,
    hasProvider: true,
    providerLabel: 'Claude',
    lastError: null,
    lastDurationMs: null,
    lastRawResponse: null,
    lastParseResult: null,
    ...overrides,
  };
}

describe('classifyPreflight', () => {
  it('returns { kind: "no-trades" } when hasTrades is false (and hydrated)', () => {
    const state = classifyPreflight(baseCtx({ hasTrades: false }));
    expect(state).toEqual({ kind: 'no-trades' });
  });

  it('returns { kind: "no-provider" } with providerLabel when hasProvider is false', () => {
    const state = classifyPreflight(
      baseCtx({ hasProvider: false, providerLabel: 'OpenAI' }),
    );
    expect(state).toEqual({ kind: 'no-provider', providerLabel: 'OpenAI' });
  });

  it('returns { kind: "timeout" } with durationMs when lastError.kind is timeout', () => {
    const state = classifyPreflight(
      baseCtx({
        lastError: { message: 'The AI provider did not respond in 30s.', kind: 'timeout' },
        lastDurationMs: 30_000,
      }),
    );
    expect(state).toEqual({ kind: 'timeout', durationMs: 30_000 });
  });

  it('returns { kind: "unparseable" } with raw when response has no parseable sections', () => {
    const raw = 'Sorry, I cannot help with that request.';
    const state = classifyPreflight(
      baseCtx({
        lastRawResponse: raw,
        lastParseResult: { diagnosis: '', recommendations: '' },
      }),
    );
    expect(state).toEqual({ kind: 'unparseable', raw });
  });

  it('returns { kind: "none" } when hydrated but everything is fine', () => {
    const state = classifyPreflight(baseCtx());
    expect(state).toEqual({ kind: 'none' });
  });

  it('returns { kind: "none" } when not yet hydrated (avoids first-paint flash)', () => {
    const state = classifyPreflight(baseCtx({ hydrated: false, hasTrades: false }));
    expect(state).toEqual({ kind: 'none' });
  });

  it('does NOT classify a generic HTTP error as one of the 4 banner states', () => {
    // Generic errors fall through to the existing analysisError banner.
    const state = classifyPreflight(
      baseCtx({
        lastError: { message: 'HTTP 500', kind: 'http' },
        lastDurationMs: 1_200,
      }),
    );
    expect(state).toEqual({ kind: 'none' });
  });

  it('precedence: no-trades wins over no-provider', () => {
    const state = classifyPreflight(
      baseCtx({ hasTrades: false, hasProvider: false, providerLabel: 'Anthropic' }),
    );
    expect(state).toEqual({ kind: 'no-trades' });
  });
});

describe('isUnparseableResponse', () => {
  it('returns true for empty-ish short text', () => {
    expect(
      isUnparseableResponse('ok', { diagnosis: '', recommendations: '' }),
    ).toBe(true);
  });

  it('returns false for empty raw', () => {
    expect(
      isUnparseableResponse('', { diagnosis: '', recommendations: '' }),
    ).toBe(false);
  });

  it('returns false when the parser extracted a diagnosis', () => {
    const raw = 'DIAGNOSIS: looks good\n\nRECOMMENDATIONS: tweak stop loss';
    expect(
      isUnparseableResponse(raw, {
        diagnosis: 'looks good',
        recommendations: 'tweak stop loss',
      }),
    ).toBe(false);
  });

  it('returns true for a refusal longer than the threshold with no sections', () => {
    const raw = 'I am sorry, but I cannot help you with that request right now.';
    expect(
      isUnparseableResponse(raw, { diagnosis: '', recommendations: '' }),
    ).toBe(true);
  });
});

describe('scrollToBacktestButton', () => {
  it('returns false (no-op) when no element with id="run-backtest-btn" exists', () => {
    expect(scrollToBacktestButton()).toBe(false);
  });

  it('scrolls and returns true when the target exists', () => {
    const scrollIntoView = jest.fn();
    const fakeEl = { scrollIntoView } as unknown as HTMLElement;
    const getElementById = jest
      .spyOn(document, 'getElementById')
      .mockReturnValue(fakeEl);
    try {
      expect(scrollToBacktestButton()).toBe(true);
      expect(scrollIntoView).toHaveBeenCalledWith({
        behavior: 'smooth',
        block: 'center',
      });
    } finally {
      getElementById.mockRestore();
    }
  });
});

describe('DEFAULT_SETTINGS_HREF', () => {
  it('points at /settings', () => {
    expect(DEFAULT_SETTINGS_HREF).toBe('/settings');
  });
});
