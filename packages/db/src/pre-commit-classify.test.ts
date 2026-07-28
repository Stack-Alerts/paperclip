import { describe, expect, it } from "vitest";
import { classifyFailure } from "../../../.githooks/pre-commit-classify.mjs";

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

  it("returns a hard failure for an unrelated migration-check error", () => {
    expect(
      classifyFailure({
        staged: ["packages/db/src/migrations/0136_example.sql"],
        stagedTags: new Set(["0136_example"]),
        headTags: new Set(["0135_previous"]),
      }),
    ).toMatchObject({ kind: "failure" });
  });
});
