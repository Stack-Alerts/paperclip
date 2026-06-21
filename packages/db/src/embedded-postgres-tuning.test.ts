import { describe, expect, it } from "vitest";
import { computeEmbeddedPostgresTuning } from "./embedded-postgres-tuning.js";

const MB = 1024 * 1024;
const GB = 1024 * MB;

function parseMb(value: string): number {
  const match = value.match(/^(\d+)MB$/);
  if (!match) throw new Error(`Unexpected size string: ${value}`);
  return Number(match[1]);
}

describe("computeEmbeddedPostgresTuning", () => {
  it("scales shared_buffers to 25% of RAM up to an 8 GB cap", () => {
    const tuning = computeEmbeddedPostgresTuning(64 * GB);
    expect(parseMb(tuning.shared_buffers)).toBe(8 * 1024);
    expect(parseMb(tuning.effective_cache_size)).toBe(32 * 1024);
  });

  it("does not over-allocate on a 2 GB host", () => {
    const tuning = computeEmbeddedPostgresTuning(2 * GB);
    const sharedBuffersMb = parseMb(tuning.shared_buffers);
    const effectiveCacheMb = parseMb(tuning.effective_cache_size);

    expect(sharedBuffersMb).toBeLessThanOrEqual(2 * 1024 * 0.25 + 1);
    expect(sharedBuffersMb).toBeGreaterThanOrEqual(128);
    expect(effectiveCacheMb).toBeLessThanOrEqual(2 * 1024 * 0.75 + 1);
    expect(effectiveCacheMb).toBeGreaterThanOrEqual(512);
  });

  it("uses tight autovacuum defaults that catch runaway insert workloads", () => {
    const tuning = computeEmbeddedPostgresTuning(16 * GB);
    expect(tuning.autovacuum_vacuum_scale_factor).toBe("0.02");
    expect(tuning.autovacuum_analyze_scale_factor).toBe("0.01");
    expect(tuning.autovacuum_vacuum_insert_scale_factor).toBe("0.02");
    expect(tuning.autovacuum_naptime).toBe("15s");
    expect(tuning.autovacuum_max_workers).toBe("4");
    expect(tuning.log_min_duration_statement).toBe("500ms");
  });

  it("falls back to a safe default when host RAM is unknown", () => {
    const tuning = computeEmbeddedPostgresTuning(Number.NaN);
    expect(parseMb(tuning.shared_buffers)).toBeGreaterThanOrEqual(128);
    expect(parseMb(tuning.effective_cache_size)).toBeGreaterThanOrEqual(512);
  });
});
