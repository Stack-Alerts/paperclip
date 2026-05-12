# BTC-Trade-Engine Documentation

This directory contains all documentation for the BTC-Trade-Engine-PaperClip project.
Pre-migration historical docs are preserved under [`archive/`](archive/).

## Navigation

| Folder | Description |
|--------|-------------|
| [`architecture/`](architecture/) | System design, ADRs, data manager docs, database guide, git workflow |
| [`building-blocks/`](building-blocks/) | Signal/block reference docs, registry architecture, expert reviews |
| [`debugger/`](debugger/) | Debugger and logger documentation |
| [`integrations/`](integrations/) | External API integration docs (LakeAPI, Lake paths) |
| [`optimizer/`](optimizer/) | Optimizer V3 — design, user guide, sprint history |
| [`strategies/`](strategies/) | Strategy development, universal optimizer guide, trade manager |
| [`strategy-builder/`](strategy-builder/) | Strategy Builder UI — architecture, component specs, NautilusTrader integration |
| [`ui/`](ui/) | UI/UX design specs, color palette, stylesheet guides |
| [`archive/`](archive/) | Completed session notes, sprint handoffs, legacy docs, test results |

## Key Reference Documents

- **Building Blocks API**: [`building-blocks/BUILDING_BLOCKS_API_REFERENCE.md`](building-blocks/BUILDING_BLOCKS_API_REFERENCE.md)
- **Registry Architecture**: [`building-blocks/REGISTRY_ARCHITECTURE.md`](building-blocks/REGISTRY_ARCHITECTURE.md)
- **Signal Reference**: [`building-blocks/BUILDING_BLOCK_SIGNAL_REFERENCE.md`](building-blocks/BUILDING_BLOCK_SIGNAL_REFERENCE.md)
- **Optimizer User Guide**: [`optimizer/USER_GUIDE.md`](optimizer/USER_GUIDE.md)
- **Strategy Builder Architecture**: [`strategy-builder/ARCHITECTURE_V1.0.md`](strategy-builder/ARCHITECTURE_V1.0.md)
- **Strategy Developer Guide**: [`architecture/data-manager/STRATEGY_DEVELOPER_GUIDE.md`](architecture/data-manager/STRATEGY_DEVELOPER_GUIDE.md)
- **Database Guide**: [`architecture/DATABASE_GUIDE.md`](architecture/DATABASE_GUIDE.md)
- **Git Workflow**: [`architecture/GIT_WORKFLOW.md`](architecture/GIT_WORKFLOW.md)
- **Touch Index FR Worker**: [`docs/architecture/TOUCH_INDEX_FR_WORKER.md`](architecture/TOUCH_INDEX_FR_WORKER.md) — FR ingestion pipeline architecture, triggers, data quality SLAs, runbooks
- **Touch Index Bug Worker**: [`docs/architecture/TOUCH_INDEX_BUG_WORKER.md`](architecture/TOUCH_INDEX_BUG_WORKER.md) — bug-close ingestion worker, file dependency tracking ([`DATABASE_GUIDE §9`](architecture/DATABASE_GUIDE.md#9-touch_index_bug_files), [`Bug CI`](../.github/workflows/touch-index-bug-worker.yml))
- **Blast Radius Worker**: [`../.github/workflows/blast-radius-worker.yml`](../.github/workflows/blast-radius-worker.yml) — detects fix→in_review transitions and posts Blast Radius Reports ([`src/blast_radius/`](../src/blast_radius/))
- **Impact Gate Worker**: [`../.github/workflows/impact-gate-worker.yml`](../.github/workflows/impact-gate-worker.yml) — gates in_review fixes through Impact Gate validation ([`src/impact_gate/`](../src/impact_gate/))
- **Expert Reviews**: [`building-blocks/expert-reviews/`](building-blocks/expert-reviews/) — 80 signal expert analysis docs
- **LakeAPI Integration**: [`integrations/`](integrations/)

## Archive Structure

- `archive/ui-ux/` — session notes and gap analyses from UI-UX development
- `archive/integration-results/` — backtest forensic and wiring analysis reports
- `archive/test-notes/` — building blocks registry test session notes
- `archive/optimizer/sprints/` — completed optimizer sprint docs (→ see [`optimizer/sprints/`](optimizer/sprints/))
- `archive/v3-legacy/` — pre-v3 layered architecture docs
- `archive/v3-archived/` — v3 top-level archived files
- `archive/root-archived/` — root-level archived session and rule files

## Runbooks

| Runbook | Purpose |
|---------|---------|
| [`runbook-ci-cd.md`](runbook-ci-cd.md) | CI/CD pipeline — all 15 workflows, triggers, failure remediation |
| [`runbook-database-migration.md`](runbook-database-migration.md) | Alembic migration lifecycle — create, apply, rollback, recovery |
| [`runbook-incident-response.md`](runbook-incident-response.md) | Sev1–3 incident response flow, escalation matrix |
| [`runbook-backup-restore.md`](runbook-backup-restore.md) | Database backup and restore procedures |
| [`runbook-module-lock.md`](runbook-module-lock.md) | Lock gate operations and exception process |
| [`runbook-blast-radius-worker.md`](runbook-blast-radius-worker.md) | Blast Radius worker operations |
| [`runbook-touch-index-bug-worker.md`](runbook-touch-index-bug-worker.md) | Touch Index Bug worker operations |
| [`runbook-touch-index-fr-worker.md`](runbook-touch-index-fr-worker.md) | Touch Index FR worker operations |
| [`runbook-impact-gate-scan-done.md`](runbook-impact-gate-scan-done.md) | Impact Gate scan-done operations |
| [`runbooks/key-rotation.md`](runbooks/key-rotation.md) | API key rotation procedure |

## Planning & Audits

| Document | Purpose |
|----------|---------|
| [`docs-audit-and-coverage-plan-BTCAAAAA-7381.md`](docs-audit-and-coverage-plan-BTCAAAAA-7381.md) | Documentation audit and gap analysis (BTCAAAAA-7381) |
