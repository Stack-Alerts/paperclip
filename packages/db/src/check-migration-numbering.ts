import { execFileSync } from "node:child_process";
import { readdir, readFile } from "node:fs/promises";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

const migrationsDir = fileURLToPath(new URL("./migrations", import.meta.url));
const journalPath = fileURLToPath(new URL("./migrations/meta/_journal.json", import.meta.url));
const repoRoot = path.resolve(fileURLToPath(new URL("../../../", import.meta.url)));
const repairCommand = "scripts/db-repair-journal.sh";

export const ORPHAN_FILE_SANITY_LIMIT = 100;

export type CheckMode = "check" | "repair";
export type ExecRepair = (command: string, args: string[], cwd: string) => void;

export type JournalEntry = {
  idx?: number;
  tag?: string;
};

export type JournalFile = {
  version?: string;
  dialect?: string;
  entries?: JournalEntry[];
};

export type CheckInput = {
  migrationsDir: string;
  journalPath: string;
};

export type RepairDeps = CheckInput & {
  repoRoot: string;
  repairCmd: string;
  repairArgs: string[];
  execRepair: ExecRepair;
};

export type MainInput = Partial<CheckInput> & {
  repoRoot?: string;
  mode?: CheckMode;
  argv?: string[];
  env?: NodeJS.ProcessEnv;
  execRepair?: ExecRepair;
};

export class MigrationJournalFileMismatchError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "MigrationJournalFileMismatchError";
  }
}

export function migrationNumber(value: string): string | null {
  const match = value.match(/^(\d{4})_/);
  return match ? match[1] : null;
}

export function ensureNoDuplicates(values: string[], label: string): void {
  const seen = new Map<string, string>();

  for (const value of values) {
    const number = migrationNumber(value);
    if (!number) {
      throw new Error(`${label} entry does not start with a 4-digit migration number: ${value}`);
    }
    const existing = seen.get(number);
    if (existing) {
      throw new Error(`Duplicate migration number ${number} in ${label}: ${existing}, ${value}`);
    }
    seen.set(number, value);
  }
}

export function ensureStrictlyOrdered(values: string[], label: string): void {
  const sorted = [...values].sort();
  for (let index = 0; index < values.length; index += 1) {
    if (values[index] !== sorted[index]) {
      throw new Error(
        `${label} are out of order at position ${index}: expected ${sorted[index]}, found ${values[index]}`,
      );
    }
  }
}

export function ensureJournalMatchesFiles(migrationFiles: string[], journalTags: string[]): void {
  const journalFiles = journalTags.map((tag) => `${tag}.sql`);

  if (journalFiles.length !== migrationFiles.length) {
    const migrationFileSet = new Set(migrationFiles);
    const journalFileSet = new Set(journalFiles);
    const filesMissingFromJournal = migrationFiles.filter((file) => !journalFileSet.has(file));
    const journalFilesMissingFromDisk = journalFiles.filter((file) => !migrationFileSet.has(file));
    const details = [
      filesMissingFromJournal.length > 0 ? `journal missing: ${filesMissingFromJournal.join(", ")}` : "",
      journalFilesMissingFromDisk.length > 0
        ? `files missing: ${journalFilesMissingFromDisk.join(", ")}`
        : "",
    ].filter((detail) => detail.length > 0);

    throw new MigrationJournalFileMismatchError(
      `Migration journal/file count mismatch: journal has ${journalFiles.length}, files have ${migrationFiles.length}${
        details.length > 0 ? `; ${details.join("; ")}` : ""
      }`,
    );
  }

  for (let index = 0; index < migrationFiles.length; index += 1) {
    const migrationFile = migrationFiles[index];
    const journalFile = journalFiles[index];
    if (migrationFile !== journalFile) {
      throw new Error(
        `Migration journal/file order mismatch at position ${index}: journal has ${journalFile}, files have ${migrationFile}`,
      );
    }
  }
}

function formatError(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

async function readJournal(journalFilePath: string): Promise<JournalFile> {
  let rawJournal: string;
  try {
    rawJournal = await readFile(journalFilePath, "utf8");
  } catch (error) {
    throw new Error(`Unable to read migration journal ${journalFilePath}: ${formatError(error)}`);
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(rawJournal);
  } catch (error) {
    throw new Error(`Migration journal is not valid JSON at ${journalFilePath}: ${formatError(error)}`);
  }

  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(`Migration journal must be a JSON object at ${journalFilePath}`);
  }

  const journal = parsed as JournalFile;
  if (journal.entries !== undefined && !Array.isArray(journal.entries)) {
    throw new Error(`Migration journal entries must be an array at ${journalFilePath}`);
  }
  return journal;
}

export async function listMigrationFiles(migrationsDirectory: string): Promise<string[]> {
  return (await readdir(migrationsDirectory)).filter((entry) => entry.endsWith(".sql")).sort();
}

export async function readJournalTags(journalFilePath: string): Promise<string[]> {
  const journal = await readJournal(journalFilePath);
  return (journal.entries ?? []).map((entry, index) => {
    if (entry === null || typeof entry !== "object" || typeof entry.tag !== "string" || entry.tag.length === 0) {
      throw new Error(`Migration journal entry ${index} is missing a tag`);
    }
    return entry.tag;
  });
}

export async function assertJournalReadable(journalFilePath: string): Promise<void> {
  await readJournalTags(journalFilePath);
}

export async function countOrphanFiles(
  migrationsDirectory: string,
  journalTags: string[],
): Promise<number> {
  const migrationFiles = await listMigrationFiles(migrationsDirectory);
  const journalFiles = new Set(journalTags.map((tag) => `${tag}.sql`));
  return migrationFiles.filter((file) => !journalFiles.has(file)).length;
}

export async function assertOrphanCountWithinLimit(
  migrationsDirectory: string,
  journalTags: string[],
  limit = ORPHAN_FILE_SANITY_LIMIT,
): Promise<void> {
  const orphanCount = await countOrphanFiles(migrationsDirectory, journalTags);
  if (orphanCount > limit) {
    throw new Error(
      `Migration journal repair refused: orphan migration file count ${orphanCount} > ${limit} safety limit`,
    );
  }
}

export async function runCheck(input: CheckInput): Promise<void> {
  const migrationFiles = await listMigrationFiles(input.migrationsDir);
  ensureNoDuplicates(migrationFiles, "migration files");
  ensureStrictlyOrdered(migrationFiles, "migration files");

  const journalTags = await readJournalTags(input.journalPath);
  ensureNoDuplicates(journalTags, "migration journal");
  ensureStrictlyOrdered(journalTags, "migration journal");
  ensureJournalMatchesFiles(migrationFiles, journalTags);
}

export async function runRepairOnce(deps: RepairDeps): Promise<void> {
  await assertJournalReadable(deps.journalPath);

  let mismatch: unknown;
  try {
    await runCheck(deps);
    return;
  } catch (error) {
    mismatch = error;
    if (!(error instanceof MigrationJournalFileMismatchError)) {
      throw error;
    }
  }

  const journalTags = await readJournalTags(deps.journalPath);
  await assertOrphanCountWithinLimit(deps.migrationsDir, journalTags);

  process.stderr.write("check: journal/file mismatch detected\n");
  process.stderr.write(`check: invoking ${deps.repairCmd} ${deps.repairArgs.join(" ")}\n`);
  try {
    deps.execRepair(deps.repairCmd, deps.repairArgs, deps.repoRoot);
  } catch (error) {
    throw new Error(`Migration journal repair command failed: ${formatError(error)}`);
  }
  process.stderr.write("check: reapplied, re-running check\n");

  try {
    await runCheck(deps);
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw mismatch;
  }
}

export function resolveMode(argv: string[] = process.argv.slice(2), env: NodeJS.ProcessEnv = process.env): CheckMode {
  const repairFlag = argv.includes("--repair");
  const checkFlag = argv.includes("--check");
  if (repairFlag && checkFlag) {
    throw new Error("Migration check mode cannot include both --check and --repair");
  }
  if (repairFlag) return "repair";
  if (checkFlag) return "check";

  const configuredMode = env.DB_MIGRATION_CHECK_MODE?.trim().toLowerCase();
  if (!configuredMode || configuredMode === "check") return "check";
  if (configuredMode === "repair") return "repair";
  throw new Error(`Unsupported DB_MIGRATION_CHECK_MODE: ${configuredMode}`);
}

function defaultExecRepair(command: string, args: string[], cwd: string): void {
  execFileSync(command, args, { cwd, stdio: "inherit" });
}

export async function main(input: MainInput = {}): Promise<void> {
  const checkInput: CheckInput = {
    migrationsDir: input.migrationsDir ?? migrationsDir,
    journalPath: input.journalPath ?? journalPath,
  };
  const selectedMode = input.mode ?? resolveMode(input.argv, input.env);
  const env = input.env ?? process.env;

  if (selectedMode === "repair" && env.NODE_ENV === "production") {
    throw new Error(
      "Migration journal repair mode is disabled when NODE_ENV=production: refusing to mutate the journal even if DB_MIGRATION_CHECK_MODE=repair or --repair is set",
    );
  }

  await assertJournalReadable(checkInput.journalPath);

  if (selectedMode === "repair") {
    await runRepairOnce({
      ...checkInput,
      repoRoot: input.repoRoot ?? repoRoot,
      repairCmd: repairCommand,
      repairArgs: ["--apply"],
      execRepair: input.execRepair ?? defaultExecRepair,
    });
    return;
  }

  await runCheck(checkInput);
}

function isDirectInvocation(): boolean {
  if (process.argv[1] === undefined) return false;
  try {
    return path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url));
  } catch {
    return false;
  }
}

if (isDirectInvocation()) {
  try {
    await main();
  } catch (error) {
    process.stderr.write(`${formatError(error)}\n`);
    process.exitCode = 1;
  }
}
