import { totalmem } from "node:os";
import postgres from "postgres";

const MEGABYTE = 1024 * 1024;
const GIGABYTE = 1024 * MEGABYTE;

const SHARED_BUFFERS_FRACTION = 0.25;
const SHARED_BUFFERS_MIN_BYTES = 128 * MEGABYTE;
const SHARED_BUFFERS_MAX_BYTES = 8 * GIGABYTE;

const EFFECTIVE_CACHE_SIZE_FRACTION = 0.75;
const EFFECTIVE_CACHE_SIZE_MIN_BYTES = 512 * MEGABYTE;
const EFFECTIVE_CACHE_SIZE_MAX_BYTES = 32 * GIGABYTE;

const MAINTENANCE_WORK_MEM_FRACTION = 0.0625;
const MAINTENANCE_WORK_MEM_MIN_BYTES = 64 * MEGABYTE;
const MAINTENANCE_WORK_MEM_MAX_BYTES = 2 * GIGABYTE;

const WORK_MEM_BYTES = 64 * MEGABYTE;

export type EmbeddedPostgresTuning = {
  shared_buffers: string;
  effective_cache_size: string;
  maintenance_work_mem: string;
  work_mem: string;
  autovacuum_vacuum_scale_factor: string;
  autovacuum_analyze_scale_factor: string;
  autovacuum_vacuum_insert_scale_factor: string;
  autovacuum_naptime: string;
  autovacuum_max_workers: string;
  log_min_duration_statement: string;
};

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function formatMegabytes(bytes: number): string {
  return `${Math.max(1, Math.floor(bytes / MEGABYTE))}MB`;
}

export function computeEmbeddedPostgresTuning(totalMemoryBytes: number): EmbeddedPostgresTuning {
  const usableTotalMemory = Number.isFinite(totalMemoryBytes) && totalMemoryBytes > 0
    ? totalMemoryBytes
    : 4 * GIGABYTE;

  const sharedBuffersBytes = clamp(
    Math.round(usableTotalMemory * SHARED_BUFFERS_FRACTION),
    SHARED_BUFFERS_MIN_BYTES,
    SHARED_BUFFERS_MAX_BYTES,
  );
  const effectiveCacheSizeBytes = clamp(
    Math.round(usableTotalMemory * EFFECTIVE_CACHE_SIZE_FRACTION),
    EFFECTIVE_CACHE_SIZE_MIN_BYTES,
    EFFECTIVE_CACHE_SIZE_MAX_BYTES,
  );
  const maintenanceWorkMemBytes = clamp(
    Math.round(usableTotalMemory * MAINTENANCE_WORK_MEM_FRACTION),
    MAINTENANCE_WORK_MEM_MIN_BYTES,
    MAINTENANCE_WORK_MEM_MAX_BYTES,
  );

  return {
    shared_buffers: formatMegabytes(sharedBuffersBytes),
    effective_cache_size: formatMegabytes(effectiveCacheSizeBytes),
    maintenance_work_mem: formatMegabytes(maintenanceWorkMemBytes),
    work_mem: formatMegabytes(WORK_MEM_BYTES),
    // With stock 0.2 scale_factor, autovacuum never fires on a fast-growing table
    // until it has doubled in size. 0.02 reacts in minutes, not days.
    autovacuum_vacuum_scale_factor: "0.02",
    autovacuum_analyze_scale_factor: "0.01",
    autovacuum_vacuum_insert_scale_factor: "0.02",
    autovacuum_naptime: "15s",
    autovacuum_max_workers: "4",
    log_min_duration_statement: "500ms",
  };
}

export type ApplyEmbeddedPostgresTuningResult = {
  applied: EmbeddedPostgresTuning;
  reloaded: boolean;
};

export type ApplyEmbeddedPostgresTuningOptions = {
  totalMemoryBytes?: number;
  overrides?: Partial<EmbeddedPostgresTuning>;
};

export async function applyEmbeddedPostgresTuning(
  adminUrl: string,
  options: ApplyEmbeddedPostgresTuningOptions = {},
): Promise<ApplyEmbeddedPostgresTuningResult> {
  const tuning = {
    ...computeEmbeddedPostgresTuning(options.totalMemoryBytes ?? totalmem()),
    ...options.overrides,
  };

  const sql = postgres(adminUrl, { max: 1, onnotice: () => {} });
  try {
    for (const [setting, value] of Object.entries(tuning)) {
      await sql.unsafe(`ALTER SYSTEM SET ${setting} = ${quoteLiteral(value)}`);
    }
    await sql.unsafe("SELECT pg_reload_conf()");
  } finally {
    await sql.end();
  }

  return { applied: tuning, reloaded: true };
}

function quoteLiteral(value: string): string {
  return `'${value.replaceAll("'", "''")}'`;
}
