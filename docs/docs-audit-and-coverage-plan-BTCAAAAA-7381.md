# Documentation Audit & Coverage Plan

**Issue:** BTCAAAAA-7381
**Author:** DocWriter
**Date:** 2026-05-12

---

## 1. Executive Summary

**818 Markdown files** across **65 doc directories** covering **389 Python source files** in 14 src modules.

| Metric | Value |
|---|---|
| Total doc files | 818 |
| Total source files | 389 |
| Doc:Source ratio | 2.1:1 |
| Active (non-archived) doc dirs | ~30 |
| Archival/legacy doc dirs | ~35 |
| CI/CD workflows | 15 (3 documented) |
| Runbooks | 6 |

**Verdict:** The project has *extensive* documentation — far above average — but coverage is uneven. Building-blocks, strategy-builder, and optimizer are over-documented. Several critical operational areas have zero or stale docs.

---

## 2. Coverage by Module

### 2.1 Source Modules — Doc Coverage Matrix

| Source Module | Files | Doc Coverage | Status | Action |
|---|---|---|---|---|
| `src/optimizer_v3/` (10 subdirs) | ~60 | Optimizer docs (50+ files) | ✅ Good | Maintain |
| `src/strategy_builder/` (10 subdirs) | ~50 | Strategy builder docs (58 files) | ✅ Good | Maintain |
| `src/detectors/building_blocks/` | ~40 | Building blocks docs (28 dirs) | ✅ Good | Maintain |
| `src/touch_index/` | 9 | 2 architecture docs, 2 runbooks | ⚠️ Partial | Needs quality.py, git_extractor, paperclip_client docs |
| `src/blast_radius/` | 7 | 1 runbook, 1 architecture doc | ⚠️ Partial | Needs API server docs |
| `src/data_manager/` | ~30 | Data-manager arch docs exist | ⚠️ Adequate | Minor gaps in binance/ and processing/ subdirs |
| `src/strategies/` | ~20 | Strategy dev guide, 150 master list | ⚠️ Adequate | Individual strategy docs (strategy_001-015) are light |
| `src/itm/` (7 subdirs) | ~25 | Archived ITM spec docs only | 🔴 Gap | No active ITM architecture doc |
| `src/ai_consultant/` | 6 | None | 🔴 Gap | No AI consultant docs at all |
| `src/impact_gate/` | 1 | 1 runbook (scan-done) | ⚠️ Partial | No worker architecture doc |
| `src/detectors/utilities/` | ~5 | Via building-blocks docs | ⚠️ Adequate | Covered by building blocks ref |
| `src/indicators/` | ~5 | Via building-blocks | ⚠️ Adequate | Covered |
| `src/debugger_logger/` | 4 | 4 debugger docs | ✅ Good | Maintain |
| `src/utils/` | 3 | None | 🔴 Gap | confluence_calculator, mtf_alignment_checker, advanced_data_loader |

### 2.2 Infrastructure & CI/CD — Doc Coverage

| Area | Files | Doc Coverage | Status | Action |
|---|---|---|---|---|
| CI/CD workflows (15 .yml) | 15 | 3 runbooks | 🔴 Gap | Needs a CI/CD overview doc |
| Branch protection | `setup_branch_protection.py` | 1 assessment doc | ⚠️ Partial | Needs runbook for setup |
| Dependency graph | `dep-graph-refresh.yml` | None | 🔴 Gap | Needs dep graph runbook |
| OpenCode watchdog | 3 files | 1 README | ⚠️ Partial | Needs runbook |
| Lock gate | `lock-gate.yml`, `lock_gate.py` | 2 docs | ✅ Good | Maintain |
| Alembic migrations | `alembic/`, `manage_migrations.py` | None | 🔴 Gap | Needs migration runbook |
| Security | GitHub templates | 1 security audit doc | ⚠️ Partial | Needs incident response runbook |

### 2.3 Runbooks — Coverage

| Runbook | Exists | Status |
|---|---|---|
| Backup/restore | ✅ | Update needed (stale) |
| Key rotation | ✅ | Current |
| Module lock | ✅ | Current |
| Touch-index bug worker | ✅ | Current |
| Touch-index FR worker | ✅ | Current |
| Blast radius worker | ✅ | Current |
| Impact gate scan done | ✅ | Current |
| CI/CD workflows | ❌ | **GAP** |
| Database migration | ❌ | **GAP** |
| Incident response | ❌ | **GAP** |
| Deployment | ❌ | **GAP** |
| OpenCode watchdog | ❌ | **GAP** |

### 2.4 Architecture Decision Records

| Topic | Exists | Status |
|---|---|---|
| Database architecture | ✅ DATABASE_GUIDE.md | Good |
| Git workflow | ✅ GIT_WORKFLOW.md | Good |
| Touch Index FR | ✅ TOUCH_INDEX_FR_WORKER.md | Good |
| Touch Index Bug | ✅ TOUCH_INDEX_BUG_WORKER.md | Good |
| Blast Radius | ✅ BLAST_RADIUS_WORKER.md | Good |
| ITM Engine | ❌ | **GAP** |
| AI Consultant | ❌ | **GAP** |
| Impact Gate | ❌ | **GAP** |
| Data Manager design | Partial | Needs update |

---

## 3. Prioritized Gap List

### P0 — Must create (blocks operations)

| # | Doc | Rationale |
|---|---|---|
| 1 | `docs/runbook-ci-cd.md` | 15 workflows, no ops guide |
| 2 | `docs/runbook-database-migration.md` | Alembic in use, no procedure |
| 3 | `docs/runbook-incident-response.md` | No escalation/rollback procedure |
| 4 | `docs/architecture/ITM_ENGINE.md` | ITM module has 7 subdirs, zero active docs |

### P1 — High value (onboarding, maintainability)

| # | Doc | Rationale |
|---|---|---|
| 5 | `docs/architecture/AI_CONSULTANT.md` | AI consultant module undocumented |
| 6 | `docs/runbook-deployment.md` | No deployment procedure exists |
| 7 | `docs/architecture/IMPACT_GATE.md` | Impact gate worker arch missing |
| 8 | `docs/runbook-dep-graph.md` | dep-graph-refresh workflow undocumented |
| 9 | `docs/runbook-opencode-watchdog.md` | Watchdog timer/service undocumented |

### P2 — Nice to have (fills minor gaps)

| # | Doc | Rationale |
|---|---|---|
| 10 | `docs/architecture/DATA_MANAGER_ARCH.md` (update) | Refresh stale data-manager docs |
| 11 | `docs/architecture/TOUCH_INDEX_QUALITY.md` | quality.py module undocumented |
| 12 | `docs/touch-index-git-extractor.md` | git_extractor.py logic undocumented |
| 13 | Onboarding guide updates | Cross-reference new docs |

---

## 4. Action Plan

### Sprint A — Runbook Foundation (P0 items 1-3)

1. **`docs/runbook-ci-cd.md`**
   - Document all 15 workflows with trigger, purpose, failure-remediation
   - Include `lint.yml`, `test.yml`, `lock-gate.yml`, all worker workflows
2. **`docs/runbook-database-migration.md`**
   - Alembic migration lifecycle: create, review, apply, rollback
   - Migration safety checklist
3. **`docs/runbook-incident-response.md`**
   - Detection → Triage → Contain → Resolve → Postmortem
   - Escalation matrix

### Sprint B — Architecture Docs (P0 item 4 + P1 items 5-7)

4. **`docs/architecture/ITM_ENGINE.md`**
   - ITM domain model, engine lifecycle, orchestrator flow, risk model, state machine
5. **`docs/architecture/AI_CONSULTANT.md`**
   - Consultant service, signal catalog, audit writer, provider interface
6. **`docs/architecture/IMPACT_GATE.md`**
   - Worker logic, validation pipeline, integration with issue lifecycle
7. **`docs/touch-index-quality.md`**
   - quality.py purpose, data quality SLAs, alerting

### Sprint C — Runbook Expansion (P1 items 6, 8, 9)

8. **`docs/runbook-deployment.md`**
   - Build, test, stage, production promotion, rollback
9. **`docs/runbook-dep-graph.md`**
   - Purpose, how to refresh, interpreting output
10. **`docs/runbook-opencode-watchdog.md`**
    - Service file, timer, log inspection, recovery

### Sprint D — Polish (P2 items 10-13)

11. Update `docs/architecture/data-manager/` with current state
12. Create `docs/touch-index-git-extractor.md` — git extraction pipeline
13. Update onboarding guide with cross-references to new docs

---

## 5. Doc Health — Existing Doc Quality Assessment

| Doc Area | Quality | Notes |
|---|---|---|
| Strategy Builder (58 files) | ✅ Excellent | Comprehensive, well-structured |
| Building Blocks (28 subdirs) | ✅ Excellent | Deep signal coverage |
| Optimizer (50+ files) | ✅ Excellent | Full sprint history + user guide |
| UI docs (16 files) | ✅ Good | Design system, stylesheet guide |
| Runbooks (6 files) | ⚠️ Fair | Core ones exist, many gaps |
| Architecture docs | ⚠️ Fair | Some areas over-covered, others bare |
| Integrations | ✅ Good | Lake API well documented |
| Debugger (4 files) | ✅ Good | Complete |
| Archive docs | ⚠️ Mixed | Valuable history, needs pruning |

---

## 6. Recommendations

1. **Add `docs/DOCS_INVENTORY.md`** — a machine-parseable doc inventory for CI tooling
2. **Establish an ADR convention** — formal Architecture Decision Records under `docs/architecture/adr/`
3. **Reduce archive bloat** — ~35 archive dirs with many duplicates; run a dedup pass
4. **Add doc CI check** — workflow that validates links in new/updated docs
5. **Doc review cadence** — quarterly review of runbooks and architecture docs

---

## 7. Effort Estimate

| Sprint | Docs | Est. Effort |
|---|---|---|
| A — Runbook Foundation | 3 | 4-6 hours |
| B — Architecture Docs | 4 | 6-8 hours |
| C — Runbook Expansion | 3 | 4-6 hours |
| D — Polish | 3 | 3-4 hours |
| **Total** | **13 new/updated docs** | **17-24 hours** |
