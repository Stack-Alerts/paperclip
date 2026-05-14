# Requirements Documentation — Central Index

**Owner:** DocWriter
**Last updated:** 2026-05-14
**Issue:** BTCAAAAA-26490

Central index for all requirements-related documentation across the BTC Trade Engine project.

## Process & Governance

| Document | Description |
|----------|-------------|
| [REQUIREMENTS_TRACEABILITY.md](../architecture/REQUIREMENTS_TRACEABILITY.md) | End-to-end traceability framework — goal→requirement→implementation→QA→deployment lifecycle, status definitions, atomic blocker policy, quarterly audit procedures |
| [REQUIREMENT-AND-OR-SIGNAL-LOGIC.md](../architecture/REQUIREMENT-AND-OR-SIGNAL-LOGIC.md) | Technical spec for AND/OR signal logic with order and dependency enforcement — layered enforcement, timing chains, recheck validation |

## Requirements Registry

| Document | Description |
|----------|-------------|
| [requirements_registry.json](../../requirements_registry.json) | Canonical JSON registry mapping requirements → source modules → test files → issues (1514 lines, 40+ requirements across DATA, TRADE, SIGNAL, ITM, STRAT, QA, UI domains) |
| [requirements_registry.schema.md](../architecture/requirements_registry.schema.md) | Schema documentation for the registry JSON format — RequirementEntry fields, types, and validation rules |
| [requirements_registry_ci_integration.md](../architecture/requirements_registry_ci_integration.md) | CI integration spec — lock gate, impact gate, gap scanner integration, output format, automation workflows |

## Architecture Decision Records

| Document | Description |
|----------|-------------|
| [ADR-0002: Test-to-Requirements Traceability](../architecture/adr/ADR-0002-test-to-requirements-traceability.md) | Decision to implement lightweight JSON registry with pytest marker integration — context, alternatives considered, decision rationale |
| [ADR-0002: Traceability Schema — Requirement → Test Case → Issue](../architecture/adr/ADR-0002-traceability-schema-requirement-test-issue.md) | Detailed schema design for bidirectional traceability — file path conventions, marker conventions, upgrade path |

## Related Infrastructure

| Document | Description |
|----------|-------------|
| [Impact Gate](../architecture/IMPACT_GATE.md) | FR acceptance + bug regression gating — uses registry to cross-reference touched files against requirements |
| [Lock Gate](../lock-gate.md) | Locked module protection — registry integration lists affected requirements on locked-module changes |
| [QA Fact-Check Pipeline](../qa/FACT_CHECK_PIPELINE.md) | Automated verification pipeline for claims made by AI Consultant against requirements |

## Quick Links

- **All active requirements:** [`requirements_registry.json`](../../requirements_registry.json) (search for `"status": "active"`)
- **Draft/pending requirements:** search for `"status": "draft"` in the registry
- **Critical-priority requirements:** search for `"priority": "critical"` in the registry
- **Locked-module requirements:** search for `"locked-module"` in the registry tags

## Maintenance

| Action | Frequency | Owner |
|--------|-----------|-------|
| Registry completeness audit | Quarterly | DocWriter |
| Traceability gap report | Per major release | DocWriter |
| CI integration verification | Per CI workflow change | AutomationEngineer |
| ADR review | Per new requirement | Architect |
