"""
Phase Timing Data Model — QAbstractTableModel for phase duration computation.

Computes per-phase durations from adjacent PhaseStarted/PhaseCompleted pairs.
Displays phase events in tabular format with computed microsecond durations.
"""

from __future__ import annotations

from typing import Optional
import logging

from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant
from PyQt5.QtGui import QColor

from .phase_event_buffer import PhaseEvent, PhaseEventBuffer
from .styles import (
    COLORS,
    PHASE_TIMING,
    PHASE_TIMING_TABLE_COLUMNS,
    get_phase_timing_data_model_font,
)

logger = logging.getLogger(__name__)


class PhaseTimingDataModel(QAbstractTableModel):
    """
    QAbstractTableModel for phase timing display.

    Rows: One row per phase (computed from adjacent start/completed pairs)
    Columns: Phase name, started timestamp (µs), completed timestamp (µs), duration (µs)

    Automatically computes durations from buffer events.
    """

    def __init__(self, buffer: PhaseEventBuffer, parent=None):
        super().__init__(parent)
        self._buffer = buffer
        self._phases: list[dict] = []  # Cache of computed phases
        self._refresh_phases()

    def _refresh_phases(self) -> None:
        """
        Compute phase data from buffer events.

        Scans buffer for adjacent PhaseStarted/PhaseCompleted pairs and computes durations.
        """
        self._phases.clear()
        events = self._buffer.get_events()

        # Build a map: phase_name -> best PhaseCompleted event data
        # Backend provides duration_ms and outcome in the 'completed' event.
        phase_map: dict[str, dict] = {}
        for event in events:
            if event.phase_name not in phase_map:
                phase_map[event.phase_name] = {}

            if event.event_type == 'started':
                phase_map[event.phase_name]['started'] = True
            elif event.event_type == 'completed':
                raw = event.raw_data or {}
                phase_map[event.phase_name]['duration_ms'] = float(raw.get('duration_ms', 0.0))
                phase_map[event.phase_name]['outcome'] = raw.get('outcome', 'success')

        # Include phases that have at least a 'completed' event
        for phase_name in sorted(phase_map.keys()):
            data = phase_map[phase_name]
            if 'duration_ms' in data:
                self._phases.append({
                    'name': phase_name,
                    'duration_ms': data['duration_ms'],
                    'outcome': data.get('outcome', 'success'),
                })

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of computed phases."""
        if parent.isValid():
            return 0
        return len(self._phases)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of columns."""
        if parent.isValid():
            return 0
        return len(PHASE_TIMING_TABLE_COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> QVariant:
        """Return cell data."""
        if not index.isValid() or index.row() >= len(self._phases):
            return QVariant()

        phase = self._phases[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:  # Phase name
                return QVariant(phase['name'])
            elif col == 1:  # Duration in ms
                return QVariant(f"{phase['duration_ms']:.3f}")
            elif col == 2:  # Outcome
                return QVariant(phase['outcome'])

        elif role == Qt.TextAlignmentRole:
            return QVariant(int(Qt.AlignCenter | Qt.AlignVCenter))

        elif role == Qt.ForegroundRole:
            if col == 0:
                return QVariant(QColor(COLORS['panel_title']))
            else:
                return QVariant(QColor(COLORS['text_primary']))

        elif role == Qt.BackgroundRole:
            if index.row() % 2 == 0:
                return QVariant(QColor(COLORS['bg_medium']))
            else:
                return QVariant(QColor(COLORS['bg_light']))

        elif role == Qt.FontRole:
            is_bold = col == 0
            return QVariant(get_phase_timing_data_model_font(bold=is_bold, size=10))

        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> QVariant:
        """Return header data."""
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                if section < len(PHASE_TIMING_TABLE_COLUMNS):
                    return QVariant(PHASE_TIMING_TABLE_COLUMNS[section]['name'])
            elif role == Qt.TextAlignmentRole:
                return QVariant(int(Qt.AlignCenter | Qt.AlignVCenter))
            elif role == Qt.BackgroundRole:
                return QVariant(QColor(COLORS['bg_secondary']))
            elif role == Qt.ForegroundRole:
                return QVariant(QColor(COLORS['panel_title']))
            elif role == Qt.FontRole:
                return QVariant(get_phase_timing_data_model_font(bold=True, size=10))

        return QVariant()

    def update_from_buffer(self) -> None:
        """
        Update model data from buffer (called after buffer changes).

        Emits appropriate signals to notify views of data changes.
        """
        self.beginResetModel()
        self._refresh_phases()
        self.endResetModel()

    def add_event(self, event: PhaseEvent) -> None:
        """
        Add event to buffer and refresh model.

        Args:
            event: PhaseEvent to add to the buffer
        """
        self._buffer.append(event)
        self.update_from_buffer()

    def clear(self) -> None:
        """Clear all data."""
        self.beginResetModel()
        self._buffer.clear()
        self._phases.clear()
        self.endResetModel()

    def get_phase_data(self) -> list[dict]:
        """Return list of computed phase data."""
        return list(self._phases)
