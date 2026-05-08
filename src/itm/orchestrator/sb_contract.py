"""
ITM Section D — Strategy Builder Export Contract & Importer
============================================================
Defines the JSON/YAML interface contract between the Strategy Builder (SB) and
the ITM, and implements the ``SBExportImporter`` that parses the SB export
format into ``StrategyConfig`` objects ready for the ``StrategyRegistry``.

SB Export Format (JSON / YAML)
-------------------------------
The Strategy Builder exports a dict with the following top-level structure::

    {
      "sb_export_version": "1.0",
      "exported_at": "2026-05-08T12:00:00Z",        # ISO-8601 UTC
      "strategies": [
        {
          "id": "uuid-or-slug",
          "name": "My Momentum Strategy",
          "instrument": {
            "symbol": "BTC/USDT",
            "exchange": "binance",
            "contract_type": "spot"
          },
          "capital_allocation_pct": 0.5,             # 0-1 fraction of total capital
          "risk": {
            "max_drawdown_pct": 0.05,                # auto-pause threshold
            "max_position_qty": 0.1,
            "heat_limit": 5.0,
            "max_daily_loss": 500.0,
            "max_leverage": 1.0                       # MUST be 1.0
          },
          "signal_confidence_threshold": 0.6,        # minimum signal strength accepted
          "tags": ["momentum", "15m"],                # optional, informational only
          "metadata": {}                              # arbitrary pass-through
        }
      ]
    }

Contract invariants (enforced on import)
-----------------------------------------
* ``sb_export_version`` must be "1.0" (currently only version supported).
* Each strategy must have a unique ``id``.
* ``capital_allocation_pct`` across all strategies in a single export must sum
  to ≤ 1.0.
* ``max_leverage`` must equal 1.0.
* ``max_drawdown_pct`` must be in (0, 1].
* ``max_position_qty`` must be ≤ 1.0 (institutional hard limit).
* ``max_daily_loss`` must be ≤ 500.0 (institutional hard limit in USDT).

Usage
-----
::

    importer = SBExportImporter()

    # From a JSON string
    configs = importer.from_json(raw_json_str)

    # From a YAML file
    configs = importer.from_yaml_file("/path/to/export.yaml")

    # From a Python dict
    configs = importer.from_dict(export_dict)

"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — institutional hard limits
# ---------------------------------------------------------------------------

SB_EXPORT_VERSION = "1.0"
MAX_POSITION_QTY_HARD_LIMIT = Decimal("1.0")     # 1.0 BTC absolute cap
MAX_DAILY_LOSS_HARD_LIMIT = Decimal("500.0")      # $500 USD per day
REQUIRED_MAX_LEVERAGE = Decimal("1.0")            # no margin, ever


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_decimal(value: Any, field_name: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError(
            f"SB export field '{field_name}' is not a valid decimal: {value!r}"
        ) from exc


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# StrategyConfig — the domain representation of one SB-exported strategy
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StrategyInstrumentConfig:
    """Instrument specification from the SB export."""
    symbol: str
    exchange: str
    contract_type: str  # "spot" / "perpetual" / "futures" / "inverse_perpetual"

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("StrategyInstrumentConfig.symbol must not be empty")
        if not self.exchange:
            raise ValueError("StrategyInstrumentConfig.exchange must not be empty")
        valid_types = {"spot", "perpetual", "futures", "inverse_perpetual"}
        if self.contract_type not in valid_types:
            raise ValueError(
                f"StrategyInstrumentConfig.contract_type must be one of {valid_types}, "
                f"got {self.contract_type!r}"
            )


@dataclass(frozen=True)
class StrategyRiskConfig:
    """Per-strategy risk parameters from the SB export.

    All monetary values in USDT; quantities in BTC.
    """
    max_drawdown_pct: Decimal       # 0 < x ≤ 1  — auto-pause threshold
    max_position_qty: Decimal       # BTC — absolute hard ceiling
    heat_limit: Decimal             # dimensionless heat units
    max_daily_loss: Decimal         # USDT per day
    max_leverage: Decimal           # must be 1.0

    def __post_init__(self) -> None:
        if not (Decimal("0") < self.max_drawdown_pct <= Decimal("1")):
            raise ValueError(
                f"StrategyRiskConfig.max_drawdown_pct must be in (0, 1], "
                f"got {self.max_drawdown_pct}"
            )
        if self.max_position_qty <= Decimal("0"):
            raise ValueError("StrategyRiskConfig.max_position_qty must be positive")
        if self.max_position_qty > MAX_POSITION_QTY_HARD_LIMIT:
            raise ValueError(
                f"StrategyRiskConfig.max_position_qty {self.max_position_qty} "
                f"exceeds institutional hard limit of {MAX_POSITION_QTY_HARD_LIMIT} BTC"
            )
        if self.heat_limit <= Decimal("0"):
            raise ValueError("StrategyRiskConfig.heat_limit must be positive")
        if self.max_daily_loss <= Decimal("0"):
            raise ValueError("StrategyRiskConfig.max_daily_loss must be positive")
        if self.max_daily_loss > MAX_DAILY_LOSS_HARD_LIMIT:
            raise ValueError(
                f"StrategyRiskConfig.max_daily_loss {self.max_daily_loss} "
                f"exceeds institutional hard limit of {MAX_DAILY_LOSS_HARD_LIMIT} USDT"
            )
        if self.max_leverage != REQUIRED_MAX_LEVERAGE:
            raise ValueError(
                f"StrategyRiskConfig.max_leverage must be {REQUIRED_MAX_LEVERAGE} "
                f"(no margin), got {self.max_leverage}"
            )


@dataclass(frozen=True)
class StrategyConfig:
    """Complete per-strategy configuration loaded from a Strategy Builder export.

    This is the canonical domain object passed to ``StrategyRegistry.load()``
    and stored in the running orchestrator.
    """
    strategy_id: str
    name: str
    instrument: StrategyInstrumentConfig
    capital_allocation_pct: Decimal     # fraction of total ITM capital, 0 < x ≤ 1
    risk: StrategyRiskConfig
    signal_confidence_threshold: Decimal  # minimum acceptable signal strength, 0-1
    tags: tuple[str, ...]               # informational only
    metadata: dict                       # pass-through from SB
    imported_at: datetime = field(default_factory=_now_utc)
    source_version: str = SB_EXPORT_VERSION

    def __post_init__(self) -> None:
        if not self.strategy_id:
            raise ValueError("StrategyConfig.strategy_id must not be empty")
        if not self.name:
            raise ValueError("StrategyConfig.name must not be empty")
        if not (Decimal("0") < self.capital_allocation_pct <= Decimal("1")):
            raise ValueError(
                f"StrategyConfig.capital_allocation_pct must be in (0, 1], "
                f"got {self.capital_allocation_pct}"
            )
        if not (Decimal("0") <= self.signal_confidence_threshold <= Decimal("1")):
            raise ValueError(
                f"StrategyConfig.signal_confidence_threshold must be in [0, 1], "
                f"got {self.signal_confidence_threshold}"
            )

    def __repr__(self) -> str:
        return (
            f"StrategyConfig(id={self.strategy_id!r}, name={self.name!r}, "
            f"instrument={self.instrument.symbol!r}, "
            f"alloc_pct={self.capital_allocation_pct})"
        )


# ---------------------------------------------------------------------------
# SBExportImporter
# ---------------------------------------------------------------------------

class SBExportImportError(Exception):
    """Raised when the SB export document is invalid or violates contracts."""


class SBExportImporter:
    """Parses Strategy Builder export documents into ``StrategyConfig`` lists.

    Validates:
    - Schema version
    - Per-strategy field types and institutional limits
    - Total capital allocation ≤ 1.0 across all strategies in one export
    - No duplicate strategy IDs within a single export
    """

    def from_dict(self, export_dict: dict) -> list[StrategyConfig]:
        """Parse a pre-loaded dict (from JSON or YAML) into StrategyConfig list.

        Parameters
        ----------
        export_dict:
            The top-level SB export document as a Python dict.

        Returns
        -------
        list[StrategyConfig]
            Validated strategy configurations; order matches input.

        Raises
        ------
        SBExportImportError
            If the document fails schema validation or violates risk constraints.
        """
        logger.info("Parsing SB export document")

        # --- Version check ---
        version = export_dict.get("sb_export_version")
        if version != SB_EXPORT_VERSION:
            raise SBExportImportError(
                f"Unsupported SB export version: {version!r}. "
                f"Expected {SB_EXPORT_VERSION!r}."
            )

        raw_strategies = export_dict.get("strategies")
        if not isinstance(raw_strategies, list) or len(raw_strategies) == 0:
            raise SBExportImportError(
                "SB export 'strategies' must be a non-empty list"
            )

        configs: list[StrategyConfig] = []
        seen_ids: set[str] = set()
        total_alloc = Decimal("0")

        for i, raw in enumerate(raw_strategies):
            try:
                config = self._parse_strategy(raw, i)
            except (ValueError, KeyError, TypeError) as exc:
                raise SBExportImportError(
                    f"Strategy at index {i} failed validation: {exc}"
                ) from exc

            if config.strategy_id in seen_ids:
                raise SBExportImportError(
                    f"Duplicate strategy_id {config.strategy_id!r} at index {i}"
                )
            seen_ids.add(config.strategy_id)
            total_alloc += config.capital_allocation_pct
            configs.append(config)

        if total_alloc > Decimal("1"):
            raise SBExportImportError(
                f"Total capital_allocation_pct across all strategies is "
                f"{total_alloc}, which exceeds 1.0 (100 %). "
                f"Reduce individual allocations."
            )

        logger.info(
            "SB export parsed successfully: %d strategies, total_alloc=%.4f",
            len(configs), float(total_alloc),
        )
        return configs

    def from_json(self, json_str: str) -> list[StrategyConfig]:
        """Parse a raw JSON string into StrategyConfig list.

        Parameters
        ----------
        json_str:
            UTF-8 JSON document string.

        Returns
        -------
        list[StrategyConfig]
        """
        try:
            export_dict = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise SBExportImportError(
                f"SB export is not valid JSON: {exc}"
            ) from exc
        if not isinstance(export_dict, dict):
            raise SBExportImportError(
                "SB export JSON root must be an object (dict), "
                f"got {type(export_dict).__name__}"
            )
        return self.from_dict(export_dict)

    def from_yaml_file(self, path: str | Path) -> list[StrategyConfig]:
        """Parse a YAML file into StrategyConfig list.

        Parameters
        ----------
        path:
            Filesystem path to the YAML export file.

        Returns
        -------
        list[StrategyConfig]
        """
        try:
            import yaml  # optional dependency — only needed for YAML import
        except ImportError as exc:
            raise SBExportImportError(
                "PyYAML is required for YAML imports: pip install pyyaml"
            ) from exc

        path = Path(path)
        if not path.exists():
            raise SBExportImportError(f"SB export file not found: {path}")

        with path.open("r", encoding="utf-8") as fh:
            try:
                export_dict = yaml.safe_load(fh)
            except yaml.YAMLError as exc:
                raise SBExportImportError(
                    f"SB export YAML parse error: {exc}"
                ) from exc

        if not isinstance(export_dict, dict):
            raise SBExportImportError(
                "SB export YAML root must be a mapping (dict), "
                f"got {type(export_dict).__name__}"
            )
        return self.from_dict(export_dict)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _parse_strategy(self, raw: dict, index: int) -> StrategyConfig:
        """Parse a single strategy dict into a StrategyConfig."""
        if not isinstance(raw, dict):
            raise ValueError(f"Strategy at index {index} must be a dict, got {type(raw).__name__}")

        strategy_id = raw.get("id")
        if not strategy_id:
            # Auto-generate a stable ID if missing (SB may omit it in early versions)
            strategy_id = str(uuid.uuid4())
            logger.warning(
                "Strategy at index %d has no 'id' field; generated %s",
                index, strategy_id,
            )
        strategy_id = str(strategy_id)

        name = raw.get("name", f"strategy_{index}")
        if not name:
            name = f"strategy_{index}"

        # Instrument
        raw_instr = raw.get("instrument", {})
        if not isinstance(raw_instr, dict):
            raise ValueError("'instrument' must be a dict")
        instrument = StrategyInstrumentConfig(
            symbol=raw_instr.get("symbol", "BTC/USDT"),
            exchange=raw_instr.get("exchange", "binance"),
            contract_type=raw_instr.get("contract_type", "spot"),
        )

        # Capital allocation
        capital_allocation_pct = _to_decimal(
            raw.get("capital_allocation_pct", "0.5"),
            "capital_allocation_pct",
        )

        # Risk sub-config
        raw_risk = raw.get("risk", {})
        if not isinstance(raw_risk, dict):
            raise ValueError("'risk' must be a dict")
        risk = StrategyRiskConfig(
            max_drawdown_pct=_to_decimal(
                raw_risk.get("max_drawdown_pct", "0.05"), "risk.max_drawdown_pct"
            ),
            max_position_qty=_to_decimal(
                raw_risk.get("max_position_qty", "0.1"), "risk.max_position_qty"
            ),
            heat_limit=_to_decimal(
                raw_risk.get("heat_limit", "5.0"), "risk.heat_limit"
            ),
            max_daily_loss=_to_decimal(
                raw_risk.get("max_daily_loss", "500.0"), "risk.max_daily_loss"
            ),
            max_leverage=_to_decimal(
                raw_risk.get("max_leverage", "1.0"), "risk.max_leverage"
            ),
        )

        # Signal confidence threshold
        signal_confidence_threshold = _to_decimal(
            raw.get("signal_confidence_threshold", "0.6"),
            "signal_confidence_threshold",
        )

        # Tags and metadata
        tags = tuple(str(t) for t in raw.get("tags", []))
        metadata = raw.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        return StrategyConfig(
            strategy_id=strategy_id,
            name=name,
            instrument=instrument,
            capital_allocation_pct=capital_allocation_pct,
            risk=risk,
            signal_confidence_threshold=signal_confidence_threshold,
            tags=tags,
            metadata=metadata,
        )
