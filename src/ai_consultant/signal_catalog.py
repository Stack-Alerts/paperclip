"""
Signal Catalog Service — AI Consultant Phase 1.1
=================================================

Loads the full building block registry, augments with live signal stats
from the DB, and produces a compressed context string for LLM system prompts.

Provides:
- SignalCatalogService.context_string()  →  ~5K-token compressed catalog
- SignalCatalogService.search(query)     →  ranked dict list for tool calls
- SignalCatalogService.get_signal_info() →  single signal lookup
- SignalCatalogService.list_signals_by_type() →  category listing
"""

from __future__ import annotations

import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class SignalStats:
    signal_name: str
    total_occurrences: int = 0
    trades_triggered: int = 0
    trigger_rate: float | None = None
    win_rate: float | None = None
    profit_factor: float | None = None
    avg_pnl: str | None = None
    best_timeframe: str | None = None


@dataclass
class CatalogEntry:
    name: str
    category: str
    weight: int
    direction: str
    description: str
    valid_signals: list[str]
    signal_tiers: dict[str, Any]
    tags: list[str]
    # Filled by _augment_with_live_stats
    stats: dict[str, SignalStats] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "category": self.category,
            "weight": self.weight,
            "direction": self.direction,
            "description": self.description,
            "signals": self.valid_signals,
            "tags": self.tags,
            "stats": {
                sig: {
                    "occurrences": s.total_occurrences,
                    "trigger_rate": s.trigger_rate,
                    "win_rate": s.win_rate,
                    "profit_factor": s.profit_factor,
                }
                for sig, s in self.stats.items()
            },
        }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class SignalCatalogService:
    """
    Loads the building block registry and optionally augments with live
    signal stats from signal_metrics / signal_events tables.

    Usage:
        svc = SignalCatalogService(db_url="postgresql://...")
        svc.load()
        prompt_ctx = svc.context_string()
        results    = svc.search("momentum oscillator")
        info       = svc.get_signal_info("RSI_OVERSOLD")
    """

    VERSION = "1.1"

    def __init__(self, db_url: str | None = None):
        self._db_url = db_url
        self._entries: dict[str, CatalogEntry] = {}
        self._signal_index: dict[str, list[str]] = {}   # signal → [block_names]
        self._global_stats: dict[str, SignalStats] = {}  # signal → aggregated stats
        self._total_signal_declarations: int = 0  # sum of valid_signals across all blocks
        self._loaded = False
        self._loaded_at: datetime | None = None
        self._stats_source: str = "none"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, with_live_stats: bool = True) -> "SignalCatalogService":
        """Load registry then optionally pull live DB stats."""
        self._load_registry()
        if with_live_stats and self._db_url:
            try:
                self._load_live_stats()
            except Exception as exc:
                logger.warning("Live stats unavailable (%s); catalog loaded without stats.", exc)
                self._stats_source = "none"
        self._loaded = True
        self._loaded_at = datetime.now(timezone.utc)
        logger.info(
            "SignalCatalogService loaded: %d blocks, %d unique signals, stats=%s",
            len(self._entries), len(self._signal_index), self._stats_source,
        )
        return self

    def context_string(self) -> str:
        """
        Return a compressed catalog string (~5K tokens) for LLM system prompts.

        Format uses structured tables with abbreviations to maximise
        information density within the token budget.
        """
        self._require_loaded()
        sections = [
            self._ctx_header(),
            self._ctx_categories(),
            self._ctx_blocks_table(),
            self._ctx_signal_stats_table(),
            self._ctx_footer(),
        ]
        return "\n".join(s for s in sections if s)

    def search(self, query: str) -> list[dict]:
        """
        Search blocks and signals by keyword, category, direction, or signal name.

        Returns ranked list of CatalogEntry dicts — blocks first, then
        individual signals that match but whose block didn't.
        """
        self._require_loaded()
        q = query.lower().strip()
        tokens = re.split(r"[\s,;]+", q)

        scored: list[tuple[int, CatalogEntry]] = []
        for entry in self._entries.values():
            score = self._score_entry(entry, tokens)
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: -x[0])
        return [e.to_dict() for _, e in scored]

    def get_signal_info(self, signal_name: str) -> dict | None:
        """
        Tool-call handler: return info about a specific signal.

        Returns dict with emitting blocks, signal tiers, and live stats,
        or None if signal is unknown.
        """
        self._require_loaded()
        sig_upper = signal_name.upper()
        blocks = self._signal_index.get(sig_upper, [])
        if not blocks:
            return None

        tiers: dict[str, Any] = {}
        for bname in blocks:
            entry = self._entries[bname]
            if sig_upper in entry.signal_tiers:
                tiers[bname] = entry.signal_tiers[sig_upper]

        stats = self._global_stats.get(sig_upper)

        return {
            "signal": sig_upper,
            "emitted_by": blocks,
            "tiers": tiers,
            "stats": {
                "occurrences": stats.total_occurrences if stats else None,
                "trigger_rate": stats.trigger_rate if stats else None,
                "win_rate": stats.win_rate if stats else None,
                "profit_factor": stats.profit_factor if stats else None,
            } if stats else None,
        }

    def list_signals_by_type(self, signal_type: str) -> list[dict]:
        """
        Tool-call handler: list all signals from blocks in a given category.

        signal_type can be a category name (OSCILLATORS, PATTERNS …)
        or a direction keyword (BULLISH, BEARISH, NEUTRAL).
        """
        self._require_loaded()
        q = signal_type.upper().strip()

        # Check if it matches a category
        category_match = {
            name: entry for name, entry in self._entries.items()
            if entry.category == q or q in entry.category
        }
        if category_match:
            results = []
            seen: set[str] = set()
            for entry in category_match.values():
                for sig in entry.valid_signals:
                    if sig in seen:
                        continue
                    seen.add(sig)
                    stats = self._global_stats.get(sig)
                    results.append({
                        "signal": sig,
                        "block": entry.name,
                        "category": entry.category,
                        "stats": {
                            "occurrences": stats.total_occurrences if stats else None,
                            "win_rate": stats.win_rate if stats else None,
                        } if stats else None,
                    })
            return sorted(results, key=lambda x: x["signal"])

        # Direction filter
        if q in ("BULLISH", "BEARISH", "NEUTRAL"):
            results = []
            for entry in self._entries.values():
                if entry.direction == q:
                    for sig in entry.valid_signals:
                        stats = self._global_stats.get(sig)
                        results.append({
                            "signal": sig,
                            "block": entry.name,
                            "category": entry.category,
                            "direction": entry.direction,
                            "stats": {
                                "occurrences": stats.total_occurrences if stats else None,
                                "win_rate": stats.win_rate if stats else None,
                            } if stats else None,
                        })
            return sorted(results, key=lambda x: x["signal"])

        return []

    def get_block_info(self, block_name: str) -> dict | None:
        """Return full block metadata dict, or None if unknown."""
        self._require_loaded()
        entry = self._entries.get(block_name.lower())
        return entry.to_dict() if entry else None

    @property
    def block_count(self) -> int:
        return len(self._entries)

    @property
    def signal_count(self) -> int:
        """Unique signal names across all blocks."""
        return len(self._signal_index)

    @property
    def total_signal_declarations(self) -> int:
        """Total signal declarations (sum of valid_signals per block; counts duplicates)."""
        return self._total_signal_declarations

    @property
    def categories(self) -> list[str]:
        return sorted({e.category for e in self._entries.values()})

    # ------------------------------------------------------------------
    # Registry loading
    # ------------------------------------------------------------------

    def _load_registry(self) -> None:
        # Ensure project root is on sys.path for block imports
        project_root = Path(__file__).parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        from src.detectors.building_blocks.registry import BlockRegistry  # noqa: PLC0415

        all_blocks = BlockRegistry.get_all_blocks()
        self._entries = {}
        self._signal_index = {}

        for name, meta in all_blocks.items():
            entry = CatalogEntry(
                name=name,
                category=meta.category,
                weight=meta.default_weight,
                direction=meta.direction,
                description=meta.description,
                valid_signals=meta.valid_signals,
                signal_tiers=meta.signal_tiers,
                tags=meta.tags or [],
            )
            self._entries[name] = entry

            for sig in meta.valid_signals:
                self._signal_index.setdefault(sig, []).append(name)

        self._total_signal_declarations = sum(len(e.valid_signals) for e in self._entries.values())
        logger.debug(
            "Registry loaded: %d blocks, %d unique signals, %d total declarations",
            len(self._entries), len(self._signal_index), self._total_signal_declarations,
        )

    # ------------------------------------------------------------------
    # Live stats loading
    # ------------------------------------------------------------------

    def _load_live_stats(self) -> None:
        from sqlalchemy import create_engine, text  # noqa: PLC0415

        engine = create_engine(self._db_url, pool_pre_ping=True)
        with engine.connect() as conn:
            # Try signal_metrics table first (pre-aggregated)
            try:
                rows = conn.execute(text(
                    """
                    SELECT signal_name,
                           SUM(total_occurrences) AS total_occurrences,
                           SUM(trades_triggered)  AS trades_triggered,
                           AVG(trigger_rate)      AS trigger_rate,
                           AVG(win_rate)          AS win_rate,
                           AVG(profit_factor)     AS profit_factor,
                           MODE() WITHIN GROUP (ORDER BY best_timeframe) AS best_timeframe
                    FROM signal_metrics
                    GROUP BY signal_name
                    """
                )).fetchall()
                if rows:
                    for row in rows:
                        self._global_stats[row.signal_name] = SignalStats(
                            signal_name=row.signal_name,
                            total_occurrences=int(row.total_occurrences or 0),
                            trades_triggered=int(row.trades_triggered or 0),
                            trigger_rate=float(row.trigger_rate) if row.trigger_rate else None,
                            win_rate=float(row.win_rate) if row.win_rate else None,
                            profit_factor=float(row.profit_factor) if row.profit_factor else None,
                            best_timeframe=row.best_timeframe,
                        )
                    self._stats_source = "signal_metrics"
                    logger.debug("Loaded stats for %d signals from signal_metrics", len(rows))
                    return
            except Exception:
                pass  # Table may not exist or be empty; fall through

            # Fallback: aggregate from signal_events
            try:
                rows = conn.execute(text(
                    """
                    SELECT signal_name,
                           COUNT(*)                                    AS total_occurrences,
                           SUM(CASE WHEN led_to_trade THEN 1 ELSE 0 END) AS trades_triggered,
                           AVG(CASE WHEN led_to_trade THEN 1.0 ELSE 0.0 END) AS trigger_rate,
                           AVG(CASE WHEN trade_result = 'win' THEN 1.0
                                    WHEN trade_result IN ('loss','breakeven') THEN 0.0
                                    END) AS win_rate
                    FROM signal_events
                    WHERE led_to_trade IS NOT NULL
                    GROUP BY signal_name
                    HAVING COUNT(*) >= 10
                    ORDER BY total_occurrences DESC
                    LIMIT 500
                    """
                )).fetchall()
                for row in rows:
                    self._global_stats[row.signal_name] = SignalStats(
                        signal_name=row.signal_name,
                        total_occurrences=int(row.total_occurrences or 0),
                        trades_triggered=int(row.trades_triggered or 0),
                        trigger_rate=float(row.trigger_rate) if row.trigger_rate else None,
                        win_rate=float(row.win_rate) if row.win_rate else None,
                    )
                self._stats_source = "signal_events" if rows else "none"
                logger.debug("Loaded stats for %d signals from signal_events", len(rows))
            except Exception as exc:
                logger.warning("Could not load stats from signal_events: %s", exc)
                self._stats_source = "none"

    # ------------------------------------------------------------------
    # Context string helpers
    # ------------------------------------------------------------------

    def _ctx_header(self) -> str:
        ts = self._loaded_at.strftime("%Y-%m-%d %H:%M") if self._loaded_at else "n/a"
        stats_note = f"stats:{self._stats_source}" if self._stats_source != "none" else "stats:none"
        return (
            f"=== SIGNAL CATALOG v{self.VERSION} | "
            f"{len(self._entries)} blocks | "
            f"{self._total_signal_declarations} sig-decls ({len(self._signal_index)} unique) | "
            f"{len(self.categories)} cats | "
            f"{ts}UTC | {stats_note} ==="
        )

    def _ctx_categories(self) -> str:
        counts: dict[str, int] = {}
        for e in self._entries.values():
            counts[e.category] = counts.get(e.category, 0) + 1
        parts = [f"{cat}({n})" for cat, n in sorted(counts.items())]
        return "CATS: " + " ".join(parts)

    def _ctx_blocks_table(self) -> str:
        # Columns: name | cat_abbrev | wt | dir_abbrev | granular_signals (non-simple)
        # Cap signal list per block to save tokens
        SKIP_SIGNALS = {"BULLISH", "BEARISH", "NEUTRAL", "ERROR", "INSUFFICIENT_DATA", "NO_SIGNAL"}
        CAT_ABBREV = {
            "PATTERNS": "PAT", "OSCILLATORS": "OSC", "PRICE_LEVELS": "PLV",
            "SESSIONS": "SES", "MOVING_AVERAGES": "MA", "MARKET_STRUCTURE": "MS",
            "VOLATILITY": "VOL", "INSTITUTIONAL": "INS", "SMC_ICT": "SMC",
            "ELLIOTT_WAVE": "EW", "FIBONACCI": "FIB", "PRICE_ACTION": "PA",
            "RISK_MANAGEMENT": "RM", "SIGNALS": "SIG", "SUPPLY_DEMAND": "SD",
            "TREND": "TRD", "WYCKOFF": "WYC",
        }
        DIR_ABBREV = {"BULLISH": "BULL", "BEARISH": "BEAR", "NEUTRAL": "NEUT"}

        lines = ["", "BLOCKS [name|cat|wt|dir|key_signals]:"]
        for name, entry in sorted(self._entries.items()):
            cat = CAT_ABBREV.get(entry.category, entry.category[:4])
            dir_ = DIR_ABBREV.get(entry.direction, entry.direction[:4])
            granular = [s for s in entry.valid_signals if s not in SKIP_SIGNALS][:8]
            sig_str = ",".join(granular) if granular else "-"
            lines.append(f"  {name}|{cat}|{entry.weight}|{dir_}|{sig_str}")
        return "\n".join(lines)

    def _ctx_signal_stats_table(self) -> str:
        if not self._global_stats:
            return ""

        # Top 80 signals by occurrences
        top = sorted(self._global_stats.values(), key=lambda s: s.total_occurrences, reverse=True)[:80]
        lines = ["", "SIGNAL STATS [signal|fires|wr%|pf]:"]
        for s in top:
            wr = f"{s.win_rate*100:.0f}%" if s.win_rate is not None else "?"
            pf = f"{s.profit_factor:.2f}" if s.profit_factor is not None else "?"
            lines.append(f"  {s.signal_name}|{s.total_occurrences}|{wr}|{pf}")
        return "\n".join(lines)

    def _ctx_footer(self) -> str:
        return (
            "\nUSAGE: get_signal_info(name) | list_signals_by_type(cat_or_dir) | "
            "search blocks by keyword. Simple sigs: BULLISH/BEARISH/NEUTRAL always available."
        )

    # ------------------------------------------------------------------
    # Search scoring
    # ------------------------------------------------------------------

    def _score_entry(self, entry: CatalogEntry, tokens: list[str]) -> int:
        score = 0
        searchable = " ".join([
            entry.name,
            entry.category,
            entry.direction,
            entry.description,
            " ".join(entry.tags),
            " ".join(entry.valid_signals),
        ]).lower()
        for tok in tokens:
            if not tok:
                continue
            if tok in entry.name:
                score += 10
            if tok == entry.category.lower():
                score += 8
            if tok in searchable:
                score += 3
        return score

    def _require_loaded(self) -> None:
        if not self._loaded:
            raise RuntimeError("Call .load() before using SignalCatalogService")
