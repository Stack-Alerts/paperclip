#!/usr/bin/env node
import { execFileSync } from "node:child_process";

const JOURNAL = "packages/db/src/migrations/meta/_journal.json";
const MIGRATION_PREFIX = "packages/db/src/migrations/";

function git(repo, args, options = {}) {
  return execFileSync("git", ["-C", repo, ...args], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", options.allowFailure ? "pipe" : "ignore"],
  }).trim();
}

function isMigrationSql(file) {
  const relative = file.startsWith(MIGRATION_PREFIX) ? file.slice(MIGRATION_PREFIX.length) : "";
  return relative.length > 4 && !relative.includes("/") && relative.endsWith(".sql");
}

function journalTags(raw) {
  const parsed = JSON.parse(raw);
  if (!parsed || typeof parsed !== "object" || !Array.isArray(parsed.entries)) {
    throw new Error("migration journal does not contain an entries array");
  }
  return new Set(parsed.entries.map((entry) => entry?.tag).filter((tag) => typeof tag === "string"));
}

function stagedPaths(repo) {
  return git(repo, ["diff", "--cached", "--name-only", "--diff-filter=ACMR"])
    .split("\n")
    .filter(Boolean);
}

function stagedJournal(repo, journalPath, journalIsStaged) {
  if (!journalIsStaged) return headJournal(repo);
  return git(repo, ["show", `:${journalPath}`]);
}

function headJournal(repo) {
  try {
    return git(repo, ["show", `HEAD:${JOURNAL}`]);
  } catch {
    return "{\"entries\":[]}";
  }
}

export function classifyFailure({ staged, stagedTags, headTags }) {
  const stagedSql = staged
    .filter(isMigrationSql)
    .map((file) => file.slice(MIGRATION_PREFIX.length, -4));
  const journalIsStaged = staged.includes(JOURNAL);
  const sqlOrphans = stagedSql.filter((tag) => !journalIsStaged || !stagedTags.has(tag));
  const headSqlOrphans = sqlOrphans.filter((tag) => headTags.has(tag));
  const newJournalTags = [...stagedTags].filter((tag) => !headTags.has(tag));
  const journalOrphans = newJournalTags.filter(
    (tag) => !stagedSql.includes(tag) && !headTags.has(tag),
  );

  if (sqlOrphans.length === 0 && journalOrphans.length === 0) {
    return { kind: "failure", sqlOrphans, headSqlOrphans, journalOrphans };
  }
  if (
    sqlOrphans.length > 0 &&
    headSqlOrphans.length === sqlOrphans.length &&
    journalOrphans.length === 0
  ) {
    return { kind: "warning", sqlOrphans, headSqlOrphans, journalOrphans };
  }
  return { kind: "abort", sqlOrphans, headSqlOrphans, journalOrphans };
}

export function main(repo = process.argv[2] ?? process.cwd()) {
  const staged = stagedPaths(repo);
  const migrationPaths = staged.filter(
    (file) => isMigrationSql(file) || file === JOURNAL,
  );
  if (migrationPaths.length === 0) return 0;

  const stagedTags = journalTags(stagedJournal(repo, JOURNAL, staged.includes(JOURNAL)));
  const headTags = journalTags(headJournal(repo));
  const result = classifyFailure({ staged, stagedTags, headTags });

  if (result.kind === "warning") {
    process.stderr.write(
      `[pre-commit] warning: staged migration file(s) are already journaled in HEAD; re-stage the matching journal if needed:\n  ${result.headSqlOrphans.join("\n  ")}\n`,
    );
    return 0;
  }

  process.stderr.write("[pre-commit] refusing commit: migration files and journal are inconsistent\n");
  if (result.sqlOrphans.length > 0) {
    process.stderr.write(`  SQL missing from staged journal:\n  ${result.sqlOrphans.join("\n  ")}\n`);
  }
  if (result.journalOrphans.length > 0) {
    process.stderr.write(`  Journal entries missing staged SQL:\n  ${result.journalOrphans.join("\n  ")}\n`);
  }
  process.stderr.write(
    "  Fix: stage the matching migration and packages/db/src/migrations/meta/_journal.json, then retry the commit.\n",
  );
  return 1;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  try {
    process.exitCode = main();
  } catch (error) {
    process.stderr.write(`[pre-commit] unable to classify migration mismatch: ${error.message}\n`);
    process.exitCode = 1;
  }
}
