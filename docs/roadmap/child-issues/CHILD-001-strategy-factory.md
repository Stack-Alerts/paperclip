# CHILD-001: Strategy Factory — Template-based Generator

**Parent:** BTCAAAAA-25426  
**Priority:** P0  
**Owner:** Dev  
**Estimate:** 3 days  
**Dependencies:** None  
**CEO Decision:** Template-based generator first, composable v2 later

---

## User Story

As a **strategy developer**, I want to **generate a production-ready NautilusTrader strategy from a building block configuration file** so that I can produce 10+ strategies per week instead of 1 per week.

## Acceptance Criteria

### AC-1: Configuration-driven strategy definition
- A JSON/YAML config file defines:
  - Strategy name, number, category, timeframe
  - Building blocks to include (by registry name) with their weight/points
  - Confluence threshold (minimum points for entry)
  - Entry logic rules (AND/OR combinations between blocks)
  - Exit logic (TP1/TP2/TP3 ratios, SL placement rule)
  - Risk parameters (position size, max leverage, max bars held)
- A default template exists with sensible defaults for all fields

### AC-2: Production code generation
- Generator produces a valid `.py` file with:
  - Complete `Strategy` subclass extending NautilusTrader's `Strategy`
  - CORRECT imports for all specified building blocks from `src.detectors.building_blocks.*`
  - Imports for `RiskEnforcer`, `ConfluenceCalculator`, `SignalAccumulator`
  - `on_bar()` method that instantiates blocks, collects signals, checks confluence
  - Proper position management (entry, SL, TP1/TP2/TP3)
  - Docstring with strategy metadata matching existing conventions
- Generated file follows existing strategy conventions (see `strategy_01_reversal_m_pattern.py`, `strategy_04_ema_trend_continuation.py`)

### AC-3: Abstraction for future backend swap
- Generated code calls a `strategy_template.py` base class or generator functions
- The strategy logic (block combination → signal → trade) is driven by the config, not by hand-edited switches
- This enables swapping the generator backend later without rewriting strategies

### AC-4: Validation on generation
- Generator validates:
  - All referenced building blocks exist in the registry
  - Block signals match what the block actually emits
  - Confluence threshold is achievable (sum of max points >= threshold)
  - No duplicate blocks
- Generator prints a summary of what was generated

### AC-5: Batch generation
- Generator accepts `--start N --end M` to generate a range of strategies
- Generator reads from a `strategy_definitions/` directory of config files

## Design Notes

- Model the generator after the existing strategies' structure (identical boilerplate pattern)
- The only thing that varies between strategies is: imports, block instantiation, signal collection, confluence threshold, and exit logic — everything else is identical boilerplate
- Store templates in `src/strategy_builder/templates/`
- Output goes to `src/strategies/`

## Definition of Done
- [ ] Generator CLI works: `python scripts/generate_strategy.py --config strategy.json`
- [ ] Generated strategy file has correct imports and compiles
- [ ] Generated strategy passes NautilusTrader strategy validation
- [ ] Batch generation produces N files in under 10 seconds
- [ ] README updated with generator usage
- [ ] At least 3 existing strategies regenerated from config (proving backward compat)

## References
- Existing production strategies: `src/strategies/strategy_01_reversal_m_pattern.py`, `src/strategies/strategy_04_ema_trend_continuation.py`, `src/strategies/strategy_06_range_breakout.py`
- Building block registry: `src/detectors/building_blocks/registry.py`
- Building block categories: 17 categories, 83 blocks
- Strategy definitions (150 strategies): `docs/strategies/150_STRATEGIES_MASTER_LIST.md`
- Strategy implementation status: `docs/strategies/IMPLEMENTATION_STATUS.md`
