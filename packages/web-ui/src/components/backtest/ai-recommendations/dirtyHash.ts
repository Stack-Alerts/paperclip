// Dirty-hash gating for the Re-analyze button (BTCAAAAA-37773 / Sprint A1).
//
// Given the current Strategy + backtest config, produce a stable string hash.
// The button compares this against the hash captured at the time of the last
// cached analysis to decide whether re-running would produce different input
// (enabled) or is a no-op (disabled).

function stableStringify(value: unknown): string {
  if (value === null || typeof value !== 'object') {
    const s = JSON.stringify(value);
    return s ?? 'null';
  }
  if (Array.isArray(value)) {
    return `[${value.map(stableStringify).join(',')}]`;
  }
  const keys = Object.keys(value as Record<string, unknown>).sort();
  const body = keys
    .map(
      (k) =>
        `${JSON.stringify(k)}:${stableStringify(
          (value as Record<string, unknown>)[k],
        )}`,
    )
    .join(',');
  return `{${body}}`;
}

function djb2(input: string): string {
  let h = 5381;
  for (let i = 0; i < input.length; i++) {
    h = ((h << 5) + h + input.charCodeAt(i)) | 0;
  }
  return (h >>> 0).toString(16);
}

export function computeReanalyzeHash(
  strategy: unknown,
  backtestConfig: unknown,
): string {
  return djb2(stableStringify({ strategy, backtestConfig }));
}
