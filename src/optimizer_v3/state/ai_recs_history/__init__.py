"""
AI recommendations history store.

Persists AI recommendations across sessions in a JSON file under
~/.btc_trade_engine/ai_recs_history.json (overridable via env var).
Each record captures the full recommendation payload plus lifecycle
metadata: timestamp, source snapshot id, applied/dismissed status,
user notes.
"""

from .store import AiRecsHistoryStore, AiRecsRecord, RecStatus

__all__ = ["AiRecsHistoryStore", "AiRecsRecord", "RecStatus"]
