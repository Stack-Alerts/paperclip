# Requirements Traceability Process

**Owner:** DocWriter
**Last updated:** 2026-05-13
**Status:** Active

## 1. Purpose

Define the end-to-end requirements traceability framework for all agents in the BTC Trade Engine organization. Every business requirement must be traceable from its origin through implementation, verification, and deployment sign-off.

## 2. Traceability Chain

```
CEO Strategy (goal)
    ↕  ProductStrategist refines into issues
Product Requirements (user stories, acceptance criteria)
    ↕  CTO delegates to engineering agents
Implementation Tasks (child issues, code changes)
    ↕  QAEngineer verifies against acceptance criteria
QA Verdict (PASS / FAIL, recorded in QA child issue)
    ↕  CTO verifies QA sign-off, marks implementation done
Deployment / Release Sign-off
```

### 2.1 Link Types

| Link | Direction | Mechanism | Example |
|------|-----------|-----------|---------|
| Goal → Strategy | CEO creates goal | `issue.goalId` | Goal "Improve backtest accuracy" → Strategy issues |
| Goal → Implementation | CTO delegates | `issue.parentId` chain | Strategy → CTO → Implementation task |
| Requirement → Task | ProductStrategist refines | `issue.parentId` | User story → Implementation subtask |
| Implementation → QA | CTO creates QA child | `issue.parentId`, `blockedByIssueIds` | Impl task → QA child issue |
| QA → Bug | QAEngineer files bug | `issue.parentId`, `blockedByIssueIds` | QA child → Bug child issue |
| Blocked link | Agent marks blocker | `blockedByIssueIds` | Task blocked on upstream issue |
| Code → Issue | Commit references | `git log` commit message `BTCAAAAA-NNN` | Commit `feat: add SMA crossover — BTCAAAAA-12345` |

## 3. Traceability Fields

Every issue MUST maintain these traceability fields:

| Field | Required? | Purpose |
|-------|-----------|---------|
| `id` | Yes | Unique issue identifier (BTCAAAAA-NNNNN) |
| `parentId` | Yes (for child issues) | Links implementation/QA/bug to parent requirement |
| `goalId` | Yes (when applicable) | Links to the CEO's strategic goal |
| `assigneeAgentId` | Yes | Owning agent UUID |
| `blockedByIssueIds` | Conditionally | Set when status = `blocked`; names upstream blockers |
| `status` | Yes | Current lifecycle stage (see §4) |
| `priority` | Yes | urgency/criticality classification |
| `title` | Yes | Human-readable summary |
| `description` | Yes | Structured requirements / acceptance criteria |

### 3.1 Commit Requirements

Every commit that changes code in response to an issue MUST reference the issue ID in the commit message:

```
git commit -m "feat: add SMA crossover signal — BTCAAAAA-12345"
```

## 4. Issue Lifecycle and Traceability

### 4.1 Requirement Creation (ProductStrategist)

```
ProductStrategist:
  1. Refines CEO goal into user stories with acceptance criteria
  2. Creates issue with status=todo, goalId=<CEO goal id>
  3. Acceptance criteria MUST be documented in the issue description
```

Traceability checkpoint: every requirement has a `goalId` linking back to CEO strategy.

### 4.2 Implementation (CTO → Engineering Agents)

```
CTO:
  1. Takes requirement issue, sets status=in_progress
  2. Delegates to engineering agent (assigneeAgentId)
  3. Creates implementation child issues with parentId=<requirement id>

Engineering Agent:
  1. Implements against acceptance criteria
  2. References issue ID in commit messages
  3. Sets status=in_review when done
```

Traceability checkpoint: every implementation has `parentId` linking to requirement and commits link to issue.

### 4.3 QA Verification (QAEngineer)

```
CTO:
  1. Creates QA child issue: parentId=<implementation id>
  2. Sets implementation status=in_review, blockedByIssueIds=[<QA child id>]

QAEngineer:
  1. Reviews implementation against acceptance criteria
  2. Runs tests
  3. Posts verdict (PASS/FAIL) AND patches status atomically
  4. If FAIL: creates bug child issues, blocks QA on bugs
  5. If PASS: sets QA child status=done
```

Traceability checkpoint: QA child links to implementation via `parentId`; bugs link to QA via `parentId`.

### 4.4 Sign-off and Deployment

```
CTO:
  1. Verifies QA child status=done and verdict matches
  2. Removes blockedByIssueIds on implementation
  3. Sets implementation status=done
  4. Escalates to CEO for deployment sign-off
```

Traceability checkpoint: done status implies QA child is done.

## 5. Status Definitions

| Status | Meaning | Traceability Rule |
|--------|---------|-------------------|
| `todo` | Created, not yet started | Must have parentId or goalId |
| `in_progress` | Work actively underway | Assignee identified |
| `in_review` | Ready for review / QA | Must be blocked on QA child issue |
| `done` | Completed and verified | QA child must be done |
| `blocked` | Cannot proceed | MUST set blockedByIssueIds or name blocker in comment |
| `cancelled` | Abandoned | Reason documented in comment |

### 5.1 Blocked Status Rule (Atomic Blocker Policy)

Any PATCH to `status: blocked` MUST include `blockedByIssueIds` in the same request, OR the comment MUST contain a structured `**blocker:**` line naming the non-issue blocker. See [BTCAAAAA-1749](/BTCAAAAA/issues/BTCAAAAA-1749).

## 6. Auditing and Verification

### 6.1 Automated Checks

The following invariants MUST hold at all times:

| Invariant | Check | Enforcement |
|-----------|-------|-------------|
| Every `in_progress` task has an assignee | `assigneeAgentId` is set | Board/API validation |
| Every `blocked` issue has a blocker reference | `blockedByIssueIds` or `**blocker:**` in comment | CEO routine nudge |
| Every `done` implementation has a `done` QA child | Traverse `parentId` chain | CTO verification before sign-off |
| Every commit references an issue ID | Commit message matches `BTCAAAAA-\d+` | CI commit lint workflow |

### 6.2 Manual Traceability Audit

Run quarterly (or on every major release):

1. Select all issues in `done` status for the release scope
2. For each: verify `goalId` → `parentId` chain resolves to an active CEO goal
3. Check each has a QA child in `done` status
4. Sample 20% of commits to verify issue ID references
5. Report gaps to CTO

### 6.3 Traceability Gap Report Template

```
## Traceability Gap Report

- Date: {date}
- Scope: {goal/issue range}
- Total issues audited: {N}
- Issues with missing parentId: {N}
- Issues with missing goalId: {N}
- Done issues without done QA child: {N}
- Commits without issue reference: {N}
- Recommendations: {bulleted list}
```

## 7. Agent-Specific Responsibilities

| Agent | Traceability Duty |
|-------|-------------------|
| **CEO** | Creates goals; assigns goalId to strategy issues |
| **ProductStrategist** | Creates requirements with clear acceptance criteria; sets goalId; maintains parentId chain |
| **CTO** | Creates implementation and QA child issues; verifies QA done before marking implementation done; enforces chain-of-command compliance |
| **Engineering Agents** | References issue ID in every commit; sets status correctly; blocks with blockedByIssueIds when needed |
| **QAEngineer** | Verifies implementation against acceptance criteria; records atomic verdict; files bug children with parentId |
| **DocWriter** | Maintains this document; runs traceability audits; reports gaps |

## 8. References

- [BTCAAAAA-1749](/BTCAAAAA/issues/BTCAAAAA-1749) — Escalation policy and atomic blocker rule
- [BTCAAAAA-1479](/BTCAAAAA/issues/BTCAAAAA-1479) — Locked module escape hatch
- [BTCAAAAA-1476](/BTCAAAAA/issues/BTCAAAAA-1476) — Atomic verdict rule (QA)
- [Impact Gate](../IMPACT_GATE.md) — FR acceptance + bug regression gating
- [CTO AGENTS.md](../../../../.paperclip/instances/default/companies/73419cf3-bd37-4a7c-8782-311ccb47fced/agents/41b5ede6-e209-40ba-b923-dc969c722e6d/instructions/AGENTS.md) — CTO delegation and QA handoff flow

## 9. Change History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-13 | Architect | Added §10: Test-Case-to-Requirements Mapping — BTCAAAAA-25644 |

| 2026-05-13 | DocWriter | Initial version — issue BTCAAAAA-25646 |

## 10. Test-Case-to-Requirements Mapping (Code-Level Traceability)

### 10.1 Overview

In addition to process-level issue traceability (§2-§5), the system now includes a code-level traceability layer that maps **source modules → requirements → test cases**. This is implemented via the **Requirements Registry** (`requirements_registry.json`).

### 10.2 Registry Schema

See [requirements_registry.schema.md](requirements_registry.schema.md) and [ADR-0002](adr/ADR-0002-test-to-requirements-traceability.md) for full design rationale.

Each requirement entry links:
- `source_modules` — which source files implement the requirement
- `test_files` — which test files verify the requirement
- `test_markers` — which pytest markers tag the requirement in tests
- `source_issues` — which Paperclip issues originated the requirement

### 10.3 Traceability Chain (Expanded)

```
CEO Goal
  └── Product Requirements (BTCAAAAA-NNN)
        ├── Implementation Tasks (code changes in src/)
        │     └── Requirements Registry entry (requirements_registry.json)
        │           ├── source_modules: which files implement it
        │           └── test_files: which tests verify it
        ├── Test Cases (tests/*/test_*.py)
        │     └── pytest markers: @pytest.mark.fr("FDR-NNN")
        └── QA Verdict (PASS / FAIL)
```

### 10.4 CI Integration

| Trigger | Action | Registry Role |
|---------|--------|---------------|
| `git push` on locked module | Lock Gate identifies changed module | Loads registry → finds affected requirements → lists required tests |
| Issue transitions `in_review` | Impact Gate runs verification tests | Cross-references touched files against registry `source_modules` |
| Nightly scheduled scan | Gap detection | Reports requirements with zero tests, stale references, orphan tests |

### 10.5 Agent Responsibilities

| Agent | Registry Duty |
|-------|---------------|
| **Architect** | Owns `requirements_registry.json` schema and ADRs; approves structural changes |
| **CTO** | Approves new requirements and priority assignments |
| **Engineering Agents** | Add registry entries when implementing new features; update `source_modules` on refactor |
| **QAEngineer** | Verifies `test_files` and `test_markers` fields are correct; runs gap detection |
| **AutomationEngineer** | Integrates registry into CI lock gate, impact gate, and gap scanner |
| **DocWriter** | Maintains `requirements_registry.schema.md` and this document |

### 10.6 References

- [requirements_registry.json](../../requirements_registry.json) — Canonical registry
- [ADR-0002](adr/ADR-0002-test-to-requirements-traceability.md) — Architecture decision
- [requirements_registry.schema.md](requirements_registry.schema.md) — Schema documentation
