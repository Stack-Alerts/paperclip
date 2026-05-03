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
