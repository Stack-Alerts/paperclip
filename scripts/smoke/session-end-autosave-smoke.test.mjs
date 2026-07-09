#!/usr/bin/env node
// session-end-autosave-smoke.test.mjs
//
// Verifies the exit-code matrix of scripts/session_end_autosave.py without
// touching the live repo. Each case builds an isolated git fixture under
// .smoke-fixtures/, runs the script with the right inputs, asserts the
// expected exit code, and cleans up.
//
// Exit codes under test (per scripts/session_end_autosave.py docstring):
//   0 = success, nothing-to-commit, non-protected branch, detached HEAD
//   2 = git invocation failed
//   3 = opted out via --no-autosave or PAPERCLIP_NO_AUTOSAVE=1
//   4 = no .git reachable from cwd

import { mkdtempSync, rmSync, writeFileSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import assert from "node:assert/strict";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(HERE, "..", "..");
const SCRIPT = join(REPO_ROOT, "scripts", "session_end_autosave.py");
const PYTHON = process.env.PYTHON ?? "python3";

const FIXTURE_ROOT = mkdtempSync(join(tmpdir(), "paperclip-autosave-smoke-"));
const failures = [];

function fixture(name) {
  const dir = join(FIXTURE_ROOT, name);
  mkdirSync(dir, { recursive: true });
  return dir;
}

function runScript(cwd, extraEnv = {}, args = []) {
  return spawnSync(PYTHON, [SCRIPT, "--cwd", cwd, ...args], {
    env: { ...process.env, ...extraEnv },
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
}

function git(cwd, args) {
  return spawnSync("git", args, {
    cwd,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
}

function initRepo(cwd, branch) {
  git(cwd, ["init", "-q", "-b", branch]);
  git(cwd, ["config", "user.email", "smoke@paperclip.ing"]);
  git(cwd, ["config", "user.name", "Paperclip Smoke"]);
  writeFileSync(join(cwd, ".paperclip-marker"), "1\n");
  git(cwd, ["add", "-A"]);
  git(cwd, ["commit", "-q", "-m", "init"]);
}

function caseNoGit() {
  const dir = fixture("no-git");
  const res = runScript(dir);
  assert.equal(res.status, 4, `expected exit 4 (no repo), got ${res.status}\nstderr=${res.stderr}`);
}

function caseOptOutFlag() {
  const dir = fixture("opt-out-flag");
  initRepo(dir, "feat/BTCAAAAA-99999-fixture");
  writeFileSync(join(dir, "extra.txt"), "dirty\n");
  const res = runScript(dir, {}, ["--no-autosave"]);
  assert.equal(res.status, 3, `expected exit 3 (opt-out), got ${res.status}\nstderr=${res.stderr}`);
  const status = git(dir, ["status", "--porcelain"]);
  assert.ok(status.stdout.includes("extra.txt"), "expected uncommitted change to persist on opt-out");
}

function caseOptOutEnv() {
  const dir = fixture("opt-out-env");
  initRepo(dir, "feat/BTCAAAAA-99999-fixture");
  const res = runScript(dir, { PAPERCLIP_NO_AUTOSAVE: "1" });
  assert.equal(res.status, 3, `expected exit 3 (env opt-out), got ${res.status}\nstderr=${res.stderr}`);
}

function caseNonProtectedBranch() {
  const dir = fixture("non-protected");
  initRepo(dir, "main");
  writeFileSync(join(dir, "scratch.txt"), "wip\n");
  const res = runScript(dir);
  assert.equal(res.status, 0, `expected exit 0 (no-op on main), got ${res.status}\nstderr=${res.stderr}`);
  const status = git(dir, ["status", "--porcelain"]);
  assert.ok(status.stdout.includes("scratch.txt"), "expected scratch.txt to remain uncommitted");
}

function caseNothingToCommit() {
  const dir = fixture("clean-protected");
  initRepo(dir, "fix/BTCAAAAA-99999-clean");
  const res = runScript(dir);
  assert.equal(res.status, 0, `expected exit 0 (clean tree), got ${res.status}\nstderr=${res.stderr}`);
}

function caseDetachedHead() {
  const dir = fixture("detached");
  initRepo(dir, "fix/BTCAAAAA-99999-detach");
  const headSha = git(dir, ["rev-parse", "HEAD"]).stdout.trim();
  git(dir, ["checkout", "-q", "--detach", headSha]);
  const res = runScript(dir);
  assert.equal(res.status, 0, `expected exit 0 (detached skip), got ${res.status}\nstderr=${res.stderr}`);
}

function caseProtectedBranchPushFails() {
  // Without a configured remote, git push will fail. The script must
  // commit locally then return exit 2 so callers can surface the push error.
  const dir = fixture("protected-no-remote");
  initRepo(dir, "fix/BTCAAAAA-99999-fixture");
  writeFileSync(join(dir, "work.txt"), "in-progress\n");
  const res = runScript(dir);
  assert.equal(res.status, 2, `expected exit 2 (push failed), got ${res.status}\nstderr=${res.stderr}`);
  const log = git(dir, ["log", "--oneline"]);
  assert.match(log.stdout, /WIP.*auto-snapshot/, "expected WIP commit even when push fails");
}

const cases = [
  ["no-git", caseNoGit],
  ["--no-autosave flag", caseOptOutFlag],
  ["PAPERCLIP_NO_AUTOSAVE env", caseOptOutEnv],
  ["non-protected branch", caseNonProtectedBranch],
  ["clean protected branch", caseNothingToCommit],
  ["detached HEAD", caseDetachedHead],
  ["protected branch with dirty work (push fails)", caseProtectedBranchPushFails],
];

for (const [name, fn] of cases) {
  try {
    fn();
    process.stdout.write(`ok  - ${name}\n`);
  } catch (err) {
    failures.push({ name, err });
    process.stdout.write(`FAIL- ${name}: ${err.message}\n`);
  }
}

try {
  rmSync(FIXTURE_ROOT, { recursive: true, force: true });
} catch {
  // best-effort cleanup
}

if (failures.length > 0) {
  process.exit(1);
}
process.stdout.write(`\nAll ${cases.length} smoke cases passed.\n`);