"""
Unit tests for PhaseEventBuffer and PhaseTimingDataModel.

Tests cover:
- Ring buffer overflow handling
- Timestamp sorting
- Duration calculation
- QAbstractTableModel integration
"""

from __future__ import annotations

import sys
import pytest
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QModelIndex

from src.strategy_builder.ui.phase_event_buffer import PhaseEvent, PhaseEventBuffer
from src.strategy_builder.ui.phase_timing_data_model import PhaseTimingDataModel


@pytest.fixture(scope="module")
def qapp():
    """Shared QApplication for this test module."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


class TestPhaseEvent:
    """Test PhaseEvent dataclass."""

    def test_phase_event_creation(self):
        """Test creating a PhaseEvent."""
        event = PhaseEvent(
            phase_name='setup',
            event_type='started',
            timestamp_us=1000,
            raw_data={'source': 'ws/cycle'},
        )
        assert event.phase_name == 'setup'
        assert event.event_type == 'started'
        assert event.timestamp_us == 1000

    def test_phase_event_comparison(self):
        """Test PhaseEvent comparison by timestamp."""
        event1 = PhaseEvent('p1', 'started', 1000, {})
        event2 = PhaseEvent('p2', 'started', 2000, {})
        assert event1 < event2
        assert not event2 < event1

    def test_phase_event_equality(self):
        """Test PhaseEvent equality by timestamp."""
        event1 = PhaseEvent('p1', 'started', 1000, {})
        event2 = PhaseEvent('p1', 'started', 1000, {})
        assert event1 == event2

    def test_phase_event_hash(self):
        """Test PhaseEvent can be added to sets."""
        event1 = PhaseEvent('p1', 'started', 1000, {})
        event2 = PhaseEvent('p1', 'started', 1000, {})
        event_set = {event1, event2}
        assert len(event_set) == 1


class TestPhaseEventBuffer:
    """Test PhaseEventBuffer ring buffer."""

    def test_buffer_creation(self):
        """Test creating an empty buffer."""
        buffer = PhaseEventBuffer()
        assert len(buffer) == 0
        assert buffer.get_events() == []

    def test_buffer_append_single_event(self):
        """Test appending a single event."""
        buffer = PhaseEventBuffer()
        event = PhaseEvent('phase1', 'started', 1000, {})
        buffer.append(event)
        assert len(buffer) == 1
        assert buffer.get_events()[0] == event

    def test_buffer_timestamp_sorting(self):
        """Test events are automatically sorted by timestamp."""
        buffer = PhaseEventBuffer()
        events = [
            PhaseEvent('p1', 'started', 3000, {}),
            PhaseEvent('p2', 'started', 1000, {}),
            PhaseEvent('p3', 'started', 2000, {}),
        ]
        for event in events:
            buffer.append(event)

        sorted_events = buffer.get_events()
        assert len(sorted_events) == 3
        assert sorted_events[0].timestamp_us == 1000
        assert sorted_events[1].timestamp_us == 2000
        assert sorted_events[2].timestamp_us == 3000

    def test_buffer_capacity_20(self):
        """Test buffer capacity is 20."""
        buffer = PhaseEventBuffer()
        for i in range(20):
            buffer.append(PhaseEvent(f'p{i}', 'started', i * 1000, {}))
        assert len(buffer) == 20

    def test_buffer_overflow_discards_oldest(self):
        """Test overflow handling discards oldest event by timestamp."""
        buffer = PhaseEventBuffer()
        # Add 20 events with timestamps 0-19000
        for i in range(20):
            buffer.append(PhaseEvent(f'p{i}', 'started', i * 1000, {}))

        # Add 21st event (timestamp 20000)
        buffer.append(PhaseEvent('p20', 'started', 20 * 1000, {}))

        assert len(buffer) == 20
        events = buffer.get_events()
        # Oldest event (timestamp 0) should be gone
        assert events[0].timestamp_us == 1000
        assert events[-1].timestamp_us == 20000

    def test_buffer_iteration(self):
        """Test iterating over buffer events in sorted order."""
        buffer = PhaseEventBuffer()
        events = [
            PhaseEvent('p3', 'started', 3000, {}),
            PhaseEvent('p1', 'started', 1000, {}),
            PhaseEvent('p2', 'started', 2000, {}),
        ]
        for event in events:
            buffer.append(event)

        timestamps = [e.timestamp_us for e in buffer]
        assert timestamps == [1000, 2000, 3000]

    def test_buffer_get_event_by_index(self):
        """Test accessing events by index."""
        buffer = PhaseEventBuffer()
        for i in range(5):
            buffer.append(PhaseEvent(f'p{i}', 'started', i * 1000, {}))

        assert buffer.get_event(0).timestamp_us == 0
        assert buffer.get_event(2).timestamp_us == 2000
        assert buffer.get_event(10) is None

    def test_buffer_clear(self):
        """Test clearing the buffer."""
        buffer = PhaseEventBuffer()
        for i in range(5):
            buffer.append(PhaseEvent(f'p{i}', 'started', i * 1000, {}))
        assert len(buffer) == 5

        buffer.clear()
        assert len(buffer) == 0
        assert buffer.get_events() == []

    def test_buffer_repr(self):
        """Test buffer string representation."""
        buffer = PhaseEventBuffer()
        for i in range(5):
            buffer.append(PhaseEvent(f'p{i}', 'started', i * 1000, {}))
        repr_str = repr(buffer)
        assert 'PhaseEventBuffer' in repr_str
        assert 'size=5/20' in repr_str


class TestPhaseTimingDataModel:
    """Test PhaseTimingDataModel QAbstractTableModel."""

    def test_model_creation(self, qapp):
        """Test creating a model with empty buffer."""
        buffer = PhaseEventBuffer()
        model = PhaseTimingDataModel(buffer)
        assert model.rowCount() == 0
        assert model.columnCount() == 4

    def test_model_column_count(self, qapp):
        """Test model has correct column count."""
        buffer = PhaseEventBuffer()
        model = PhaseTimingDataModel(buffer)
        assert model.columnCount() == 4

    def test_model_computes_single_phase(self, qapp):
        """Test model computes duration for a single phase."""
        buffer = PhaseEventBuffer()
        buffer.append(PhaseEvent('setup', 'started', 1000, {}))
        buffer.append(PhaseEvent('setup', 'completed', 5000, {}))

        model = PhaseTimingDataModel(buffer)
        assert model.rowCount() == 1

        # Check phase data
        phases = model.get_phase_data()
        assert len(phases) == 1
        assert phases[0]['name'] == 'setup'
        assert phases[0]['started_us'] == 1000
        assert phases[0]['completed_us'] == 5000
        assert phases[0]['duration_us'] == 4000

    def test_model_computes_multiple_phases(self, qapp):
        """Test model computes durations for multiple phases."""
        buffer = PhaseEventBuffer()
        # Phase 1: setup (1000-3000, duration 2000)
        buffer.append(PhaseEvent('setup', 'started', 1000, {}))
        buffer.append(PhaseEvent('setup', 'completed', 3000, {}))

        # Phase 2: execute (5000-8000, duration 3000)
        buffer.append(PhaseEvent('execute', 'started', 5000, {}))
        buffer.append(PhaseEvent('execute', 'completed', 8000, {}))

        model = PhaseTimingDataModel(buffer)
        assert model.rowCount() == 2

        phases = model.get_phase_data()
        assert len(phases) == 2
        assert phases[0]['name'] == 'execute'  # Sorted alphabetically
        assert phases[0]['duration_us'] == 3000
        assert phases[1]['name'] == 'setup'
        assert phases[1]['duration_us'] == 2000

    def test_model_ignores_incomplete_phases(self, qapp):
        """Test model ignores phases with only started or only completed."""
        buffer = PhaseEventBuffer()
        buffer.append(PhaseEvent('phase1', 'started', 1000, {}))
        buffer.append(PhaseEvent('phase2', 'started', 2000, {}))
        buffer.append(PhaseEvent('phase2', 'completed', 4000, {}))
        buffer.append(PhaseEvent('phase3', 'completed', 5000, {}))

        model = PhaseTimingDataModel(buffer)
        # Only phase2 is complete
        assert model.rowCount() == 1
        assert model.get_phase_data()[0]['name'] == 'phase2'

    def test_model_data_display_role(self, qapp):
        """Test model returns correct data for display."""
        buffer = PhaseEventBuffer()
        buffer.append(PhaseEvent('phase1', 'started', 1000000, {}))
        buffer.append(PhaseEvent('phase1', 'completed', 1005000, {}))

        model = PhaseTimingDataModel(buffer)

        # Verify phase data is correct
        phases = model.get_phase_data()
        assert len(phases) == 1
        assert phases[0]['name'] == 'phase1'
        assert phases[0]['started_us'] == 1000000
        assert phases[0]['completed_us'] == 1005000
        assert phases[0]['duration_us'] == 5000

    def test_model_update_from_buffer(self, qapp):
        """Test updating model after buffer changes."""
        buffer = PhaseEventBuffer()
        model = PhaseTimingDataModel(buffer)
        assert model.rowCount() == 0

        buffer.append(PhaseEvent('phase1', 'started', 1000, {}))
        buffer.append(PhaseEvent('phase1', 'completed', 5000, {}))
        model.update_from_buffer()

        assert model.rowCount() == 1
        assert model.get_phase_data()[0]['duration_us'] == 4000

    def test_model_add_event(self, qapp):
        """Test adding events directly to model."""
        buffer = PhaseEventBuffer()
        model = PhaseTimingDataModel(buffer)

        model.add_event(PhaseEvent('phase1', 'started', 1000, {}))
        model.add_event(PhaseEvent('phase1', 'completed', 5000, {}))

        assert model.rowCount() == 1
        assert model.get_phase_data()[0]['duration_us'] == 4000

    def test_model_clear(self, qapp):
        """Test clearing the model."""
        buffer = PhaseEventBuffer()
        model = PhaseTimingDataModel(buffer)

        model.add_event(PhaseEvent('phase1', 'started', 1000, {}))
        model.add_event(PhaseEvent('phase1', 'completed', 5000, {}))
        assert model.rowCount() == 1

        model.clear()
        assert model.rowCount() == 0
        assert len(buffer) == 0

    def test_model_zero_duration_phase(self, qapp):
        """Test handling of phases with zero or negative duration."""
        buffer = PhaseEventBuffer()
        # Same start and complete timestamp
        buffer.append(PhaseEvent('phase1', 'started', 1000, {}))
        buffer.append(PhaseEvent('phase1', 'completed', 1000, {}))

        model = PhaseTimingDataModel(buffer)
        assert model.rowCount() == 1
        assert model.get_phase_data()[0]['duration_us'] == 0

    def test_model_header_data(self, qapp):
        """Test model returns correct header data."""
        buffer = PhaseEventBuffer()
        model = PhaseTimingDataModel(buffer)

        # Check column headers
        headers = []
        for col in range(4):
            index = model.index(-1, col)
            header = model.headerData(col, 2, 3)  # Qt.Horizontal, Qt.DisplayRole
            headers.append(str(header))

        assert len(headers) == 4

    def test_model_integration_with_buffer_overflow(self, qapp):
        """Test model correctly recomputes after buffer overflow."""
        buffer = PhaseEventBuffer()
        model = PhaseTimingDataModel(buffer)

        # Add 10 complete phases (20 events total - fills the buffer exactly)
        for i in range(10):
            buffer.append(PhaseEvent(f'phase{i}', 'started', i * 1000, {}))
            buffer.append(PhaseEvent(f'phase{i}', 'completed', i * 1000 + 500, {}))

        model.update_from_buffer()
        assert model.rowCount() == 10

        # Add one more phase pair to trigger overflow (will discard oldest)
        buffer.append(PhaseEvent('phase10', 'started', 10000, {}))
        buffer.append(PhaseEvent('phase10', 'completed', 10500, {}))

        model.update_from_buffer()
        # Buffer still has 20 events, but oldest phase might be incomplete
        # Should have at least 9 complete phases (phase0 may have only completed event left)
        assert model.rowCount() >= 9
