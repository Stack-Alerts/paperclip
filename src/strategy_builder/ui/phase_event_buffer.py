"""
Phase Event Buffer — ring buffer for phase timing events.

Implements a fixed-capacity ring buffer (20 events) that stores PhaseStarted and
PhaseCompleted events, maintains timestamp ordering, and handles overflow.

Input: Unstructured PhaseStarted/PhaseCompleted events from /ws/cycle
Output: Sorted phase events with microsecond-precision timestamps
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import logging

from .styles import PHASE_TIMING

logger = logging.getLogger(__name__)


@dataclass
class PhaseEvent:
    """Represents a single phase event (started or completed)."""

    phase_name: str
    event_type: str  # 'started' or 'completed'
    timestamp_us: int  # Timestamp in microseconds
    raw_data: dict  # Original event data from /ws/cycle

    def __lt__(self, other: PhaseEvent) -> bool:
        """Compare events by timestamp for sorting."""
        return self.timestamp_us < other.timestamp_us

    def __eq__(self, other: object) -> bool:
        """Compare events by timestamp."""
        if not isinstance(other, PhaseEvent):
            return NotImplemented
        return self.timestamp_us == other.timestamp_us

    def __hash__(self) -> int:
        """Hash by timestamp for set operations."""
        return hash(self.timestamp_us)


class PhaseEventBuffer:
    """
    Ring buffer for phase events with overflow handling and timestamp sorting.

    Capacity: Fixed at 20 events (from styles.PHASE_TIMING)
    Behavior:
    - When buffer is full, the oldest event is discarded on next append
    - Events are automatically sorted by timestamp
    - Provides ordered iteration and direct access
    """

    def __init__(self):
        self._capacity = PHASE_TIMING['event_buffer_capacity']
        self._events: list[PhaseEvent] = []
        self._insertion_order: list[int] = []  # Track insertion order for tie-breaking
        self._overflow_count = 0

    def append(self, event: PhaseEvent) -> None:
        """
        Append event to buffer, handling overflow.

        If buffer is at capacity, the oldest event (by timestamp) is discarded.
        """
        if len(self._events) >= self._capacity:
            self._discard_oldest()
            self._overflow_count += 1

        self._events.append(event)
        self._insertion_order.append(len(self._insertion_order))
        self._sort()

    def _discard_oldest(self) -> None:
        """Remove the oldest event by timestamp."""
        if self._events:
            oldest_idx = min(range(len(self._events)), key=lambda i: self._events[i].timestamp_us)
            self._events.pop(oldest_idx)

    def _sort(self) -> None:
        """Sort events by timestamp in ascending order."""
        self._events.sort(key=lambda e: e.timestamp_us)

    def get_events(self) -> list[PhaseEvent]:
        """Return a sorted copy of all events in the buffer."""
        return sorted(self._events, key=lambda e: e.timestamp_us)

    def get_event(self, index: int) -> Optional[PhaseEvent]:
        """Get event by index (sorted order)."""
        if 0 <= index < len(self._events):
            return sorted(self._events, key=lambda e: e.timestamp_us)[index]
        return None

    def clear(self) -> None:
        """Clear all events from the buffer."""
        self._events.clear()
        self._insertion_order.clear()
        self._overflow_count = 0

    def __len__(self) -> int:
        """Return number of events in buffer."""
        return len(self._events)

    def __iter__(self):
        """Iterate over events in sorted order."""
        return iter(self.get_events())

    def __repr__(self) -> str:
        return f"PhaseEventBuffer(size={len(self._events)}/{self._capacity}, overflows={self._overflow_count})"
