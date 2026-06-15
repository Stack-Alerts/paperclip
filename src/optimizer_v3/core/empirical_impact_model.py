"""
Empirical Impact Model (BTCAAAAA-36473, parent BTCAAAAA-36465 R0).

The "evidence layer" of the AI recommendation harness. It mines the existing
corpus of (strategy config -> backtest/test result) tuples to learn how config
and signal changes ACTUALLY move performance metrics, producing confidence-banded,
data-derived effect estimates that are meant to REPLACE the hardcoded improvement
constants:

  - block_intelligence_extractor.py :: PURPOSE_METRICS_MAP
  - building_blocks_intelligence.py :: BUILDING_BLOCK_IMPROVEMENTS

Design contract:
  * Read-only against the optimizer_v3 corpus (strategy_versions, strategy_test_results,
    ai_recommendations). It NEVER writes and NEVER touches src/detectors/building_blocks/**.
  * Every estimate carries an explicit confidence band and an `insufficient_data`
    state. When the data is too thin for a change type, the API falls back to a
    CLEARLY LABELED heuristic (the legacy literals) rather than silently fabricating.
  * The DB layer degrades gracefully: if the corpus is unreachable, the model holds
    zero observations and every request returns a labeled heuristic fallback.

This module is foundational for P0 (BTCAAAAA-36468): the rec engine consumes
`EmpiricalImpactModel.estimate_impact(...)` instead of literal constants.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Metrics whose improvement means the value goes DOWN (drawdown, losses).
# Used only for human-readable interpretation; the raw signed relative effect is stored as-is.
_LOWER_IS_BETTER = {
    "max_drawdown_pct",
    "max_drawdown",
    "avg_loss",
    "max_consecutive_losses",
}

# Minimum observations before an empirical estimate is considered trustworthy.
DEFAULT_MIN_SAMPLES = 5
# If a metric baseline is smaller than this in absolute value, a relative change is
# numerically unstable, so the observation is dropped from relative-effect aggregation.
_BASELINE_EPSILON = 1e-9


class ChangeType(str, Enum):
    """Taxonomy of config changes whose impact we estimate."""

    ADD_BLOCK = "ADD_BLOCK"
    REMOVE_BLOCK = "REMOVE_BLOCK"
    ADJUST_PARAM = "ADJUST_PARAM"
    LOGIC_CHANGE = "LOGIC_CHANGE"


REGIME_ALL = "ALL"


@dataclass(frozen=True)
class ConfigResultObservation:
    """One mined (config, result) tuple: a single strategy version and its metrics.

    The config is the strategy's block list; metrics is a flat {metric_key: value}
    mapping (win_rate, profit_factor, sharpe_ratio, max_drawdown_pct, ...).
    """

    strategy_id: str
    version_number: int
    blocks: List[Dict[str, Any]]
    metrics: Dict[str, float]
    regime: str = REGIME_ALL


@dataclass(frozen=True)
class ChangeObservation:
    """A single realized effect: one change event paired with one metric's relative delta.

    `relative_effect` = (after - before) / abs(before), matching the fractional
    convention of the legacy improvement literals (e.g. +0.12 == +12% win_rate;
    -0.25 max_drawdown_pct == 25% reduction).
    """

    change_type: ChangeType
    metric: str
    relative_effect: float
    block_name: Optional[str] = None
    regime: str = REGIME_ALL


@dataclass
class ImpactEstimate:
    """A confidence-banded improvement estimate for a proposed change.

    `sufficient` is False when there were not enough observations to learn the effect
    empirically; in that case `source` is a heuristic label and the rec path should
    present the estimate as a heuristic, not as data-derived evidence.
    """

    change_type: ChangeType
    metric: str
    block_name: Optional[str]
    regime: str
    value: Optional[float]
    ci_low: Optional[float]
    ci_high: Optional[float]
    std: Optional[float]
    n_samples: int
    sufficient: bool
    source: str  # "empirical" | "empirical_broadened" | "heuristic_fallback" | "none"
    detail: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "change_type": self.change_type.value,
            "metric": self.metric,
            "block_name": self.block_name,
            "regime": self.regime,
            "value": self.value,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "std": self.std,
            "n_samples": self.n_samples,
            "sufficient": self.sufficient,
            "source": self.source,
            "detail": self.detail,
        }


# ---------------------------------------------------------------------------
# Config diffing
# ---------------------------------------------------------------------------


def _block_index(blocks: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Map block name -> block dict (last write wins on duplicate names)."""
    index: Dict[str, Dict[str, Any]] = {}
    for b in blocks or []:
        name = b.get("name")
        if name:
            index[name] = b
    return index


def _numeric_leaves(obj: Any, prefix: str = "") -> Dict[str, float]:
    """Flatten numeric leaf values of a nested block dict into dotted paths.

    Booleans are excluded (treated as logic flags, not tunable params).
    """
    out: Dict[str, float] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(_numeric_leaves(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(_numeric_leaves(v, f"{prefix}[{i}]"))
    elif isinstance(obj, bool):
        return out
    elif isinstance(obj, (int, float)):
        out[prefix] = float(obj)
    return out


@dataclass(frozen=True)
class ChangeEvent:
    """A structural change detected between two configs (metric-agnostic)."""

    change_type: ChangeType
    block_name: Optional[str] = None


class ConfigDiffer:
    """Detects ADD/REMOVE/ADJUST/LOGIC change events between two block configs."""

    @staticmethod
    def diff(before_blocks: List[Dict[str, Any]], after_blocks: List[Dict[str, Any]]) -> List[ChangeEvent]:
        before = _block_index(before_blocks)
        after = _block_index(after_blocks)
        events: List[ChangeEvent] = []

        for name in after.keys() - before.keys():
            events.append(ChangeEvent(ChangeType.ADD_BLOCK, name))
        for name in before.keys() - after.keys():
            events.append(ChangeEvent(ChangeType.REMOVE_BLOCK, name))

        for name in before.keys() & after.keys():
            b_block, a_block = before[name], after[name]
            if str(b_block.get("logic", "AND")) != str(a_block.get("logic", "AND")):
                events.append(ChangeEvent(ChangeType.LOGIC_CHANGE, name))
            if _numeric_leaves(b_block) != _numeric_leaves(a_block):
                events.append(ChangeEvent(ChangeType.ADJUST_PARAM, name))

        return events


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def _confidence_band(values: List[float]) -> Tuple[float, Optional[float], Optional[float], Optional[float]]:
    """Return (mean, std, ci_low, ci_high) for a 95% normal-approx interval.

    For n < 2 the band is undefined (None) — a single point is not evidence of a band.
    """
    n = len(values)
    mean = sum(values) / n
    if n < 2:
        return mean, None, None, None
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    std = math.sqrt(var)
    se = std / math.sqrt(n)
    half = 1.96 * se
    return mean, std, mean - half, mean + half


# ---------------------------------------------------------------------------
# Empirical model
# ---------------------------------------------------------------------------


class EmpiricalImpactModel:
    """Learns confidence-banded effect estimates from mined (config, result) tuples.

    Usage:
        model = EmpiricalImpactModel.from_database()       # mines the live corpus
        est = model.estimate_impact(ChangeType.ADD_BLOCK, "win_rate", block_name="vwap")
        if est.sufficient:
            ...use est.value with [est.ci_low, est.ci_high]...
        else:
            ...est.source == "heuristic_fallback": present as a heuristic...

    Tests inject observations directly via the constructor (no live DB needed).
    """

    def __init__(
        self,
        observations: Optional[List[ConfigResultObservation]] = None,
        min_samples: int = DEFAULT_MIN_SAMPLES,
    ):
        self.min_samples = max(2, int(min_samples))
        self._observations: List[ConfigResultObservation] = list(observations or [])
        self._changes: List[ChangeObservation] = []
        self._rebuild()

    # -- construction --------------------------------------------------------

    @classmethod
    def from_database(cls, min_samples: int = DEFAULT_MIN_SAMPLES) -> "EmpiricalImpactModel":
        """Mine the live optimizer_v3 corpus. Degrades to an empty model on any failure."""
        obs = cls._load_observations_from_db()
        return cls(observations=obs, min_samples=min_samples)

    # -- learning ------------------------------------------------------------

    def _rebuild(self) -> None:
        """Form natural-experiment pairs (consecutive versions per strategy) and
        derive per-change, per-metric relative effects."""
        self._changes = []
        by_strategy: Dict[str, List[ConfigResultObservation]] = {}
        for o in self._observations:
            by_strategy.setdefault(o.strategy_id, []).append(o)

        for versions in by_strategy.values():
            versions.sort(key=lambda o: o.version_number)
            for prev, curr in zip(versions, versions[1:]):
                events = ConfigDiffer.diff(prev.blocks, curr.blocks)
                if not events:
                    continue
                for metric, after_val in curr.metrics.items():
                    before_val = prev.metrics.get(metric)
                    if before_val is None or after_val is None:
                        continue
                    if abs(before_val) < _BASELINE_EPSILON:
                        continue
                    rel = (after_val - before_val) / abs(before_val)
                    for ev in events:
                        self._changes.append(
                            ChangeObservation(
                                change_type=ev.change_type,
                                metric=metric,
                                relative_effect=rel,
                                block_name=ev.block_name,
                                regime=curr.regime,
                            )
                        )

    def add_recommendation_outcomes(self, outcomes: Iterable[Dict[str, Any]]) -> None:
        """Fold in applied-recommendation before/after pairs (ai_recommendations).

        Each outcome: {change_type, block_name, metrics_before, metrics_after, regime?}.
        These are the cleanest labeled effects when they exist.
        """
        for oc in outcomes:
            try:
                ct = ChangeType(oc["change_type"])
            except (KeyError, ValueError):
                continue
            before = oc.get("metrics_before") or {}
            after = oc.get("metrics_after") or {}
            regime = oc.get("regime", REGIME_ALL)
            block = oc.get("block_name")
            for metric, after_val in after.items():
                before_val = before.get(metric)
                if before_val is None or after_val is None:
                    continue
                if abs(before_val) < _BASELINE_EPSILON:
                    continue
                rel = (after_val - before_val) / abs(before_val)
                self._changes.append(
                    ChangeObservation(ct, metric, rel, block, regime)
                )

    # -- query ---------------------------------------------------------------

    def _gather(
        self,
        change_type: ChangeType,
        metric: str,
        block_name: Optional[str],
        regime: str,
    ) -> List[float]:
        out = []
        for c in self._changes:
            if c.change_type != change_type or c.metric != metric:
                continue
            if block_name is not None and c.block_name != block_name:
                continue
            if regime != REGIME_ALL and c.regime != regime:
                continue
            out.append(c.relative_effect)
        return out

    def estimate_impact(
        self,
        change_type: ChangeType,
        metric: str,
        block_name: Optional[str] = None,
        regime: str = REGIME_ALL,
    ) -> ImpactEstimate:
        """Return a confidence-banded, data-derived estimate, broadening the query
        when the most specific slice is too thin, and finally falling back to a
        clearly-labeled heuristic when data is insufficient at every granularity."""
        if isinstance(change_type, str):
            change_type = ChangeType(change_type)

        # Specificity ladder: narrow -> broad. Each rung is tried for sufficiency.
        rungs: List[Tuple[Optional[str], str, str]] = [
            (block_name, regime, "empirical"),
            (block_name, REGIME_ALL, "empirical_broadened"),
            (None, regime, "empirical_broadened"),
            (None, REGIME_ALL, "empirical_broadened"),
        ]
        seen: set = set()
        best_partial: Optional[ImpactEstimate] = None

        for bn, rg, source in rungs:
            key = (bn, rg)
            if key in seen:
                continue
            seen.add(key)
            values = self._gather(change_type, metric, bn, rg)
            n = len(values)
            if n == 0:
                continue
            mean, std, lo, hi = _confidence_band(values)
            sufficient = n >= self.min_samples
            est = ImpactEstimate(
                change_type=change_type,
                metric=metric,
                block_name=bn,
                regime=rg,
                value=mean,
                ci_low=lo,
                ci_high=hi,
                std=std,
                n_samples=n,
                sufficient=sufficient,
                source=source,
                detail=self._interpret(metric, mean, n, sufficient),
            )
            if sufficient:
                return est
            # Keep the most-populated partial in case nothing reaches sufficiency.
            if best_partial is None or n > best_partial.n_samples:
                best_partial = est

        fallback = self._heuristic_fallback(change_type, metric, block_name, regime)
        if best_partial is not None:
            fallback.detail = (
                f"insufficient empirical data (best slice n={best_partial.n_samples} "
                f"< {self.min_samples}); {fallback.detail}"
            )
        return fallback

    # -- heuristic fallback --------------------------------------------------

    def _heuristic_fallback(
        self,
        change_type: ChangeType,
        metric: str,
        block_name: Optional[str],
        regime: str,
    ) -> ImpactEstimate:
        """Clearly-labeled legacy-literal estimate. Only ADD_BLOCK has literals."""
        value: Optional[float] = None
        detail = "no empirical or heuristic data for this change type"
        source = "none"

        if change_type == ChangeType.ADD_BLOCK:
            value = self._literal_add_block_improvement(block_name, metric)
            if value is not None:
                source = "heuristic_fallback"
                detail = (
                    "HEURISTIC (legacy hardcoded literal, NOT data-derived) — "
                    "use only as a weak prior"
                )

        return ImpactEstimate(
            change_type=change_type,
            metric=metric,
            block_name=block_name,
            regime=regime,
            value=value,
            ci_low=None,
            ci_high=None,
            std=None,
            n_samples=0,
            sufficient=False,
            source=source,
            detail=detail,
        )

    @staticmethod
    def _literal_add_block_improvement(block_name: Optional[str], metric: str) -> Optional[float]:
        """Pull the legacy literal for adding a block, preferring the per-block table,
        then the per-purpose table. Imported lazily to avoid a hard dependency."""
        # Per-block table (building_blocks_intelligence.BUILDING_BLOCK_IMPROVEMENTS)
        if block_name:
            try:
                from src.optimizer_v3.core.building_blocks_intelligence import (
                    get_block_intelligence,
                )

                intel = get_block_intelligence(block_name)
                if intel:
                    imp = (intel.get("average_improvement") or {}).get(metric)
                    if imp is not None:
                        return float(imp)
            except Exception:  # pragma: no cover - defensive
                logger.debug("per-block literal lookup failed", exc_info=True)

        # Per-purpose table (block_intelligence_extractor.PURPOSE_METRICS_MAP)
        if block_name:
            try:
                from src.optimizer_v3.core.block_intelligence_extractor import (
                    BlockIntelligenceExtractor,
                )

                extractor = BlockIntelligenceExtractor()
                category = None
                try:
                    from src.detectors.building_blocks.registry import BlockRegistry

                    meta = BlockRegistry.get_block(block_name)
                    category = getattr(meta, "category", None)
                except Exception:
                    category = None
                if category:
                    purpose = extractor.CATEGORY_PURPOSE_MAP.get(category)
                    purpose_data = extractor.PURPOSE_METRICS_MAP.get(purpose, {})
                    imp = (purpose_data.get("improvements") or {}).get(metric)
                    if imp is not None:
                        return float(imp)
            except Exception:  # pragma: no cover - defensive
                logger.debug("per-purpose literal lookup failed", exc_info=True)

        return None

    @staticmethod
    def _interpret(metric: str, value: float, n: int, sufficient: bool) -> str:
        direction = "lower-is-better" if metric in _LOWER_IS_BETTER else "higher-is-better"
        good = (value < 0) if metric in _LOWER_IS_BETTER else (value > 0)
        verdict = "improves" if good else "worsens"
        tag = "data-derived" if sufficient else "data-derived (thin sample)"
        return f"{tag}: {verdict} {metric} ({direction}) by {value:+.1%} mean over n={n}"

    # -- introspection -------------------------------------------------------

    def coverage(self) -> Dict[str, Any]:
        """Summarize what the model learned — for the data-inventory deliverable."""
        by_type: Dict[str, int] = {}
        metrics: set = set()
        blocks: set = set()
        for c in self._changes:
            by_type[c.change_type.value] = by_type.get(c.change_type.value, 0) + 1
            metrics.add(c.metric)
            if c.block_name:
                blocks.add(c.block_name)
        return {
            "n_observations": len(self._observations),
            "n_change_events": len(self._changes),
            "by_change_type": by_type,
            "metrics_covered": sorted(metrics),
            "distinct_blocks": len(blocks),
            "min_samples_threshold": self.min_samples,
        }

    # -- DB mining -----------------------------------------------------------

    @staticmethod
    def _load_observations_from_db() -> List[ConfigResultObservation]:
        """Read strategy_versions (config + metrics) and backfill metrics from
        strategy_test_results. Read-only; returns [] if the corpus is unreachable."""
        try:
            from sqlalchemy import create_engine, text

            from src.optimizer_v3.database.settings import get_database_settings
        except Exception:
            logger.warning("empirical_impact_model: SQLAlchemy/settings unavailable")
            return []

        try:
            engine = create_engine(get_database_settings().database_url())
        except Exception:
            logger.warning("empirical_impact_model: could not build DB engine", exc_info=True)
            return []

        # Metric columns on strategy_test_results we can backfill from.
        _TR_METRICS = (
            "total_return_pct",
            "sharpe_ratio",
            "max_drawdown_pct",
            "win_rate",
            "profit_factor",
            "total_trades",
        )
        observations: List[ConfigResultObservation] = []
        try:
            with engine.connect() as conn:
                # Per-version metrics from test results (averaged across tests for that version).
                tr_by_version: Dict[str, Dict[str, float]] = {}
                try:
                    cols = ", ".join(f"avg({m}) as {m}" for m in _TR_METRICS)
                    rows = conn.execute(
                        text(
                            f"SELECT version_id::text, {cols} "
                            "FROM strategy_test_results GROUP BY version_id"
                        )
                    )
                    for row in rows.mappings():
                        vid = row["version_id"]
                        tr_by_version[vid] = {
                            m: float(row[m]) for m in _TR_METRICS if row[m] is not None
                        }
                except Exception:
                    logger.debug("test-result metric backfill skipped", exc_info=True)

                rows = conn.execute(
                    text(
                        "SELECT version_id::text, strategy_id, version_number, blocks, metrics "
                        "FROM strategy_versions"
                    )
                )
                for row in rows.mappings():
                    metrics: Dict[str, float] = {}
                    raw_metrics = row["metrics"]
                    if isinstance(raw_metrics, dict):
                        for k, v in raw_metrics.items():
                            if isinstance(v, (int, float)) and not isinstance(v, bool):
                                metrics[k] = float(v)
                    # Backfill / supplement with test-result metrics.
                    for k, v in tr_by_version.get(row["version_id"], {}).items():
                        metrics.setdefault(k, v)
                    if not metrics:
                        continue
                    blocks = row["blocks"] if isinstance(row["blocks"], list) else []
                    observations.append(
                        ConfigResultObservation(
                            strategy_id=str(row["strategy_id"]),
                            version_number=int(row["version_number"]),
                            blocks=blocks,
                            metrics=metrics,
                            regime=REGIME_ALL,
                        )
                    )
        except Exception:
            logger.warning("empirical_impact_model: DB mining failed", exc_info=True)
            return []

        logger.info("empirical_impact_model: mined %d observations", len(observations))
        return observations
