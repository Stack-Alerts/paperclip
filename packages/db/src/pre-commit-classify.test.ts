import { execFileSync } from "node:child_process";
import { chmodSync, mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { classifyFailure, main } from "../../../.githooks/pre-commit-classify.mjs";

const gitEnv = {
  ...process.env,
  GIT_AUTHOR_NAME: "Migration Hook Test",
  GIT_AUTHOR_EMAIL: "migration-hook@example.test",
  GIT_COMMITTER_NAME: "Migration Hook Test",
  GIT_COMMITTER_EMAIL: "migration-hook@example.test",
};

function git(repo: string, args: string[]) {
  return execFileSync("git", ["-C", repo, ...args], { env: gitEnv, encoding: "utf8" });
}

describe("pre-commit migration failure classification", () => {
  it("aborts when a staged SQL file is absent from the staged journal", () => {
    expect(
      classifyFailure({
        staged: ["packages/db/src/migrations/0136_example.sql", "packages/db/src/migrations/meta/_journal.json"],
        stagedTags: new Set(["0135_previous"]),
        headTags: new Set(["0135_previous"]),
      }),
    ).toMatchObject({ kind: "abort", sqlOrphans: ["0136_example"] });
  });

  it("aborts when a new staged journal entry has no staged SQL file", () => {
    expect(
      classifyFailure({
        staged: ["packages/db/src/migrations/meta/_journal.json"],
        stagedTags: new Set(["0135_previous", "0136_example"]),
        headTags: new Set(["0135_previous"]),
      }),
    ).toMatchObject({ kind: "abort", journalOrphans: ["0136_example"] });
  });

  it("warns when a staged SQL file is already journaled in HEAD", () => {
    expect(
      classifyFailure({
        staged: ["packages/db/src/migrations/0136_example.sql"],
        stagedTags: new Set(["0135_previous"]),
        headTags: new Set(["0135_previous", "0136_example"]),
      }),
    ).toMatchObject({ kind: "warning", headSqlOrphans: ["0136_example"] });
  });

  it("uses HEAD when an unstaged journal edit adds unrelated entries", () => {
    const repo = mkdtempSync(path.join(os.tmpdir(), "migration-hook-"));
    const migrations = path.join(repo, "packages/db/src/migrations/meta");
    mkdirSync(migrations, { recursive: true });
    writeFileSync(path.join(migrations, "_journal.json"), JSON.stringify({ entries: [{ tag: "0135_previous" }, { tag: "0136_example" }] }));
    writeFileSync(path.join(repo, "packages/db/src/migrations/0136_example.sql"), "CREATE TABLE example (id integer);\n");

    try {
      git(repo, ["init", "-q"]);
      git(repo, ["config", "user.name", "Migration Hook Test"]);
      git(repo, ["config", "user.email", "migration-hook@example.test"]);
      git(repo, ["add", "."]);
      git(repo, ["commit", "-qm", "seed migration"]);
      writeFileSync(path.join(migrations, "_journal.json"), JSON.stringify({ entries: [{ tag: "0135_previous" }, { tag: "0136_example" }, { tag: "9999_unrelated" }] }));
      writeFileSync(path.join(repo, "packages/db/src/migrations/0136_example.sql"), "CREATE TABLE example (id integer);\n-- restaged\n");
      git(repo, ["add", "packages/db/src/migrations/0136_example.sql"]);

      expect(main(repo)).toBe(0);
    } finally {
      rmSync(repo, { recursive: true, force: true });
    }
  });

  it("checks staged pairing before the worktree migration checker", () => {
    const repo = mkdtempSync(path.join(os.tmpdir(), "migration-hook-"));
    const migrations = path.join(repo, "packages/db/src/migrations");
    const hooks = path.join(repo, ".githooks");
    const scripts = path.join(repo, "scripts");
    mkdirSync(path.join(migrations, "meta"), { recursive: true });
    mkdirSync(hooks);
    mkdirSync(scripts);
    writeFileSync(path.join(migrations, "meta/_journal.json"), JSON.stringify({ entries: [{ tag: "0135_previous" }] }));

    try {
      git(repo, ["init", "-q"]);
      git(repo, ["config", "user.name", "Migration Hook Test"]);
      git(repo, ["config", "user.email", "migration-hook@example.test"]);
      git(repo, ["add", "."]);
      git(repo, ["commit", "-qm", "seed journal"]);
      writeFileSync(path.join(hooks, "pre-commit"), readFileSync(new URL("../../../.githooks/pre-commit", import.meta.url)));
      writeFileSync(path.join(scripts, "check-db-migration-staging.sh"), readFileSync(new URL("../../../scripts/check-db-migration-staging.sh", import.meta.url)));
      chmodSync(path.join(hooks, "pre-commit"), 0o755);
      chmodSync(path.join(scripts, "check-db-migration-staging.sh"), 0o755);
      writeFileSync(path.join(migrations, "meta/_journal.json"), JSON.stringify({ entries: [{ tag: "0135_previous" }, { tag: "0136_example" }] }));
      writeFileSync(path.join(migrations, "0136_example.sql"), "CREATE TABLE example (id integer);\n");
      git(repo, ["add", "packages/db/src/migrations/0136_example.sql"]);

      let hookError: { status?: number; stderr?: string | Buffer } | undefined;
      try {
        execFileSync("/bin/sh", [path.join(hooks, "pre-commit")], {
          cwd: repo,
          env: { ...gitEnv, PATH: "/usr/bin:/bin" },
          encoding: "utf8",
          stdio: "pipe",
        });
      } catch (error) {
        hookError = error as { status?: number; stderr?: string | Buffer };
      }

      expect(hookError?.status, String(hookError?.stderr)).toBe(1);
      expect(String(hookError?.stderr)).toContain("migration staged without matching journal entry");
    } finally {
      rmSync(repo, { recursive: true, force: true });
    }
  });

  it("returns a hard failure for an unrelated migration-check error", () => {
    expect(
      classifyFailure({
        staged: ["packages/db/src/migrations/0136_example.sql", "packages/db/src/migrations/meta/_journal.json"],
        stagedTags: new Set(["0136_example"]),
        headTags: new Set(["0135_previous"]),
      }),
    ).toMatchObject({ kind: "failure" });
  });
});
