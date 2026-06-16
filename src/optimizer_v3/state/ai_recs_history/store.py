"""
JSON-backed persistent store for AI recommendations.

Records survive session close. The store is intentionally lightweight
(no SQL) — recommendations are small JSON payloads, writes are rare
(once per AI analysis), and the data must round-trip through
``json.loads`` cleanly because the panel reads it back at panel init.

Layout on disk::

    {
      "schema_version": 1,
      "records": [
        {
          "id": "rec-2026-06-16T12:34:56.123Z-abcdef",
          "created_at": "2026-06-16T12:34:56.123Z",
          "source_snapshot_id": "btc-2026-06-16T12:00:00Z",
          "strategy_name": "HOD Rejection Test",
          "type": "ADD_BLOCK",
          "block_name": "atr",
          "signal_name": "HIGH_VOLATILITY",
          "confidence": 0.82,
          "ai_enhanced": true,
          "reasoning": "...",
          "expected_impact": {...},
          "status": "new",         # new | applied | dismissed
          "status_updated_at": null,
          "user_notes": ""
        },
        ...
      ]
    }
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1
_VALID_STATUSES = {"new", "applied", "dismissed"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


class RecStatus:
    """Status enum string set (kept as a class for namespacing)."""

    NEW = "new"
    APPLIED = "applied"
    DISMISSED = "dismissed"


@dataclass
class AiRecsRecord:
    """A single AI recommendation with its lifecycle metadata."""

    type: str
    strategy_name: str = ""
    source_snapshot_id: str = ""
    block_name: str = ""
    signal_name: str = ""
    confidence: float = 0.0
    ai_enhanced: bool = False
    reasoning: str = ""
    expected_impact: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: f"rec-{_now_iso()}-{uuid.uuid4().hex[:6]}")
    created_at: str = field(default_factory=_now_iso)
    status: str = RecStatus.NEW
    status_updated_at: Optional[str] = None
    user_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _coerce_record(raw: Dict[str, Any]) -> AiRecsRecord:
    """Best-effort coerce a raw dict into an AiRecsRecord (legacy records may be missing fields)."""
    status = raw.get("status", RecStatus.NEW)
    if status not in _VALID_STATUSES:
        status = RecStatus.NEW
    return AiRecsRecord(
        id=raw.get("id") or f"rec-{_now_iso()}-{uuid.uuid4().hex[:6]}",
        created_at=raw.get("created_at") or _now_iso(),
        type=raw.get("type", "UNKNOWN"),
        strategy_name=raw.get("strategy_name", ""),
        source_snapshot_id=raw.get("source_snapshot_id", ""),
        block_name=raw.get("block_name", ""),
        signal_name=raw.get("signal_name", ""),
        confidence=float(raw.get("confidence", 0.0) or 0.0),
        ai_enhanced=bool(raw.get("ai_enhanced", False)),
        reasoning=raw.get("reasoning", "") or "",
        expected_impact=dict(raw.get("expected_impact") or {}),
        status=status,
        status_updated_at=raw.get("status_updated_at"),
        user_notes=raw.get("user_notes", "") or "",
    )


def _recommendation_to_dict(rec: Any) -> Dict[str, Any]:
    """Normalize a recommendation (object or dict) into the canonical store shape."""
    if isinstance(rec, dict):
        return {
            "type": rec.get("type", "UNKNOWN"),
            "block_name": rec.get("block_name", "") or "",
            "signal_name": rec.get("signal_name", "") or "",
            "confidence": float(
                rec.get("combined_confidence") or rec.get("confidence", 0) or 0.0
            ),
            "ai_enhanced": bool(rec.get("ai_enhanced", False)),
            "reasoning": rec.get("reasoning", "") or "",
            "expected_impact": dict(rec.get("expected_impact") or {}),
        }
    return {
        "type": getattr(rec, "type", "UNKNOWN"),
        "block_name": getattr(rec, "block_name", "") or "",
        "signal_name": getattr(rec, "signal_name", "") or "",
        "confidence": float(
            getattr(rec, "combined_confidence", 0)
            or getattr(rec, "confidence", 0)
            or 0.0
        ),
        "ai_enhanced": bool(getattr(rec, "ai_enhanced", False)),
        "reasoning": getattr(rec, "reasoning", "") or "",
        "expected_impact": dict(getattr(rec, "expected_impact", None) or {}),
    }


class AiRecsHistoryStore:
    """Thread-safe JSON file store for AI recommendations history."""

    DEFAULT_PATH = Path.home() / ".btc_trade_engine" / "ai_recs_history.json"
    ENV_PATH = "BTC_AI_RECS_HISTORY_PATH"

    def __init__(self, path: Optional[Path] = None) -> None:
        env_path = os.environ.get(self.ENV_PATH)
        if path is not None:
            self._path = Path(path)
        elif env_path:
            self._path = Path(env_path)
        else:
            self._path = self.DEFAULT_PATH
        self._lock = threading.Lock()
        self._records: List[AiRecsRecord] = []
        self._loaded = False

    @property
    def path(self) -> Path:
        return self._path

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            if self._path.exists():
                try:
                    payload = json.loads(self._path.read_text(encoding="utf-8"))
                    raw_records = payload.get("records", [])
                    self._records = [_coerce_record(r) for r in raw_records]
                    logger.info(
                        "[AiRecsStore] Loaded %d records from %s",
                        len(self._records),
                        self._path,
                    )
                except (json.JSONDecodeError, OSError) as exc:
                    logger.warning(
                        "[AiRecsStore] Failed to load %s: %s — starting empty",
                        self._path,
                        exc,
                    )
                    self._records = []
            else:
                self._records = []
            self._loaded = True

    def _flush(self) -> None:
        # Restrict the parent dir to owner-only at first write — the file holds
        # recommendation notes and strategy metadata that should not be
        # world-readable. ``exist_ok`` is implicit because we mkdir -p above.
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self._path.parent, 0o700)
        except OSError:
            pass
        payload = {
            "schema_version": SCHEMA_VERSION,
            "records": [r.to_dict() for r in self._records],
        }
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        # Open with mode 0o600 so the secure perms are set atomically at
        # create-time — no chmod race window where the file is world-readable.
        fd = os.open(
            str(tmp),
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW,
            0o600,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, indent=2, sort_keys=True))
        except Exception:
            # If the write failed, best-effort remove the temp file so we
            # don't leave a 0-byte artifact behind.
            try:
                tmp.unlink()
            except OSError:
                pass
            raise
        # After the atomic rename, also enforce 0o600 on the final path in
        # case the umask or prior file inherited looser permissions.
        os.replace(tmp, self._path)
        try:
            os.chmod(self._path, 0o600)
        except OSError:
            pass

    def all(self) -> List[AiRecsRecord]:
        self._ensure_loaded()
        with self._lock:
            return list(self._records)

    def by_status(self, status: str) -> List[AiRecsRecord]:
        self._ensure_loaded()
        with self._lock:
            return [r for r in self._records if r.status == status]

    def get(self, rec_id: str) -> Optional[AiRecsRecord]:
        self._ensure_loaded()
        with self._lock:
            for r in self._records:
                if r.id == rec_id:
                    return r
        return None

    def add_recommendations(
        self,
        recommendations: List[Any],
        strategy_name: str = "",
        source_snapshot_id: str = "",
    ) -> List[AiRecsRecord]:
        """Append a batch of recommendations to history. Returns the new records."""
        self._ensure_loaded()
        new_records: List[AiRecsRecord] = []
        with self._lock:
            for rec in recommendations or []:
                payload = _recommendation_to_dict(rec)
                record = AiRecsRecord(
                    strategy_name=strategy_name,
                    source_snapshot_id=source_snapshot_id,
                    **payload,
                )
                self._records.append(record)
                new_records.append(record)
            self._flush()
        logger.info(
            "[AiRecsStore] Added %d records (now %d total) to %s",
            len(new_records),
            len(self._records),
            self._path,
        )
        return new_records

    def update_status(
        self, rec_id: str, status: str, user_notes: Optional[str] = None
    ) -> Optional[AiRecsRecord]:
        if status not in _VALID_STATUSES:
            raise ValueError(
                f"status must be one of {sorted(_VALID_STATUSES)}, got {status!r}"
            )
        self._ensure_loaded()
        with self._lock:
            for r in self._records:
                if r.id == rec_id:
                    r.status = status
                    r.status_updated_at = _now_iso()
                    if user_notes is not None:
                        r.user_notes = user_notes
                    self._flush()
                    return r
        return None

    def update_notes(self, rec_id: str, user_notes: str) -> Optional[AiRecsRecord]:
        self._ensure_loaded()
        with self._lock:
            for r in self._records:
                if r.id == rec_id:
                    r.user_notes = user_notes
                    r.status_updated_at = _now_iso()
                    self._flush()
                    return r
        return None

    def clear(self) -> None:
        """Wipe the store. Used by the panel Reset button."""
        self._ensure_loaded()
        with self._lock:
            self._records = []
            self._flush()
