import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import {
  ORPHAN_FILE_SANITY_LIMIT,
  resolveMode,
  runCheck,
  runRepairOnce,
} from "./check-migration-numbering.js";

type MigrationTree = {
  root: string;
  repoRoot: string;
  migrationsDir: string;
  journalPath: string;
};

const tempRoots: string[] = [];

function createMigrationTree(files: string[], journalTags: string[]): MigrationTree {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "paperclip-migration-check-"));
  tempRoots.push(root);
  const migrationsDir = path.join(root, "migrations");
  const journalPath = path.join(migrationsDir, "meta", "_journal.json");
  fs.mkdirSync(path.dirname(journalPath), { recursive: true });

  for (const file of files) {
    fs.writeFileSync(path.join(migrationsDir, file), "-- synthetic migration\n");
  }

  fs.writeFileSync(
    journalPath,
    `${JSON.stringify(
      {
        version: "7",
        dialect: "postgresql",
        entries: journalTags.map((tag, idx) => ({
          idx,
          version: "7",
          when: 1770000000000 + idx,
          tag,
          breakpoints: true,
        })),
      },
      null,
      2,
    )}\n`,
  );

  return { root, repoRoot: root, migrationsDir, journalPath };
}

function appendJournalTag(journalPath: string, tag: string) {
  const journal = JSON.parse(fs.readFileSync(journalPath, "utf8")) as {
    entries: Array<Record<string, unknown>>;
  };
  const idx = journal.entries.length;
  journal.entries.push({
    idx,
    version: "7",
    when: 1770000000000 + idx,
    tag,
    breakpoints: true,
  });
  fs.writeFileSync(journalPath, `${JSON.stringify(journal, null, 2)}\n`);
}

function journalTags(journalPath: string): string[] {
  const journal = JSON.parse(fs.readFileSync(journalPath, "utf8")) as {
    entries: Array<{ tag: string }>;
  };
  return journal.entries.map((entry) => entry.tag);
}

afterEach(() => {
  for (const root of tempRoots.splice(0)) {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

describe("migration numbering check modes", () => {
  it("repairs an orphan migration file by delegating and rechecking", async () => {
    const tree = createMigrationTree(["0000_alpha.sql", "0001_beta.sql"], ["0000_alpha"]);
    const calls: Array<{ command: string; args: string[]; cwd: string }> = [];

    await runRepairOnce({
      ...tree,
      repairCmd: "scripts/db-repair-journal.sh",
      repairArgs: ["--apply"],
      execRepair: (command, args, cwd) => {
        calls.push({ command, args, cwd });
        appendJournalTag(tree.journalPath, "0001_beta");
      },
    });

    expect(calls).toEqual([
      {
        command: "scripts/db-repair-journal.sh",
        args: ["--apply"],
        cwd: tree.root,
      },
    ]);
    await expect(runCheck(tree)).resolves.toBeUndefined();
  });

  it("does not delete journal-only entries when repair cannot resolve the mismatch", async () => {
    const tree = createMigrationTree(["0000_alpha.sql"], ["0000_alpha", "0001_beta"]);
    const before = journalTags(tree.journalPath);

    await expect(
      runRepairOnce({
        ...tree,
        repairCmd: "scripts/db-repair-journal.sh",
        repairArgs: ["--apply"],
        execRepair: () => undefined,
      }),
    ).rejects.toThrow();

    expect(journalTags(tree.journalPath)).toEqual(before);
  });

  it("is idempotent after the orphan file has been journaled", async () => {
    const tree = createMigrationTree(["0000_alpha.sql", "0001_beta.sql"], ["0000_alpha"]);
    let repairCalls = 0;
    const deps = {
      ...tree,
      repairCmd: "scripts/db-repair-journal.sh",
      repairArgs: ["--apply"],
      execRepair: () => {
        repairCalls += 1;
        appendJournalTag(tree.journalPath, "0001_beta");
      },
    };

    await runRepairOnce(deps);
    await runRepairOnce(deps);

    expect(repairCalls).toBe(1);
    await expect(runCheck(tree)).resolves.toBeUndefined();
  });

  it("keeps check mode as the default strict behavior", async () => {
    expect(resolveMode([], {})).toBe("check");

    const tree = createMigrationTree(["0000_alpha.sql", "0001_beta.sql"], ["0000_alpha"]);
    await expect(runCheck(tree)).rejects.toThrow(/count mismatch/);
  });

  it("refuses repair when the journal is unreadable", async () => {
    const tree = createMigrationTree(["0000_alpha.sql"], ["0000_alpha"]);
    fs.writeFileSync(tree.journalPath, "not-json\n");
    let repairCalls = 0;

    await expect(
      runRepairOnce({
        ...tree,
        repairCmd: "scripts/db-repair-journal.sh",
        repairArgs: ["--apply"],
        execRepair: () => {
          repairCalls += 1;
        },
      }),
    ).rejects.toThrow(/journal/i);
    expect(repairCalls).toBe(0);
  });

  it("refuses repair when orphan files exceed the safety limit", async () => {
    const files = Array.from(
      { length: ORPHAN_FILE_SANITY_LIMIT + 1 },
      (_, idx) => `${String(idx).padStart(4, "0")}_orphan.sql`,
    );
    const tree = createMigrationTree(files, []);
    let repairCalls = 0;

    await expect(
      runRepairOnce({
        ...tree,
        repairCmd: "scripts/db-repair-journal.sh",
        repairArgs: ["--apply"],
        execRepair: () => {
          repairCalls += 1;
        },
      }),
    ).rejects.toThrow(new RegExp(`>\\s*${ORPHAN_FILE_SANITY_LIMIT}`));
    expect(repairCalls).toBe(0);
  });
});
