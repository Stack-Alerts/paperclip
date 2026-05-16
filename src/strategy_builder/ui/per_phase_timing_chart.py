"""
PerPhaseTimingChart — per-phase ITM cycle timing Gantt-style chart (P2 B1).

Displays a horizontal bar chart where each phase occupies one row on the Y-axis
and bars extend along the X-axis showing cumulative microseconds from cycle start.
Colors come from PHASE_COLORS in styles.py; dimensions from PHASE_TIMING.

Reads from: PhaseTimingDataModel (provided by caller)
Colors:     styles.PHASE_COLORS (never hardcoded here)
Dimensions: styles.PHASE_TIMING['chart_height'], styles.PHASE_TIMING['label_width']
"""

from __future__ import annotations

from PyQt5.QtCore import Qt, QRect, QSize
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import QWidget, QToolTip

from .phase_timing_data_model import PhaseTimingDataModel
from .styles import (
    COLORS,
    PHASE_COLORS,
    PHASE_TIMING,
    get_per_phase_timing_chart_label_font,
    get_per_phase_timing_chart_value_font,
)


class PerPhaseTimingChart(QWidget):
    """
    Horizontal Gantt-style bar chart showing per-phase ITM cycle timing.

    X-axis: cumulative microseconds from cycle start (0 → total cycle duration).
    Y-axis: phase names, left-aligned in PHASE_TIMING['label_width'] px column.
    Hover:  tooltip shows exact µs duration for the hovered phase bar.
    Resize: repaints automatically via resizeEvent.

    Parameters
    ----------
    model:
        PhaseTimingDataModel populated by DecisionCycleMonitor.
    parent:
        Optional Qt parent.
    """

    _PADDING = 8
    _BAR_GAP = 4
    _BAR_RADIUS = 3
    _AXIS_HEIGHT = 20
    _TICK_COUNT = 5

    def __init__(self, model: PhaseTimingDataModel, parent: QWidget | None = None):
        super().__init__(parent)
        self._model = model
        self._hovered_phase: str | None = None
        self._phase_rects: list[tuple[str, QRect, int]] = []  # (name, rect, duration_us)
        self.setMouseTracking(True)
        self.setMinimumHeight(PHASE_TIMING['chart_height'])

    def sizeHint(self) -> QSize:
        return QSize(400, PHASE_TIMING['chart_height'])

    def refresh(self) -> None:
        """Trigger visual refresh (call after model is updated by caller)."""
        self.update()

    # ------------------------------------------------------------------
    # Qt event overrides
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        phases = self._model.get_phase_data()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if not phases:
            self._draw_empty(painter)
            return

        label_w = PHASE_TIMING['label_width']
        pad = self._PADDING
        axis_h = self._AXIS_HEIGHT
        w = self.width()
        h = self.height()

        chart_x = pad + label_w
        chart_w = w - chart_x - pad
        chart_y = pad
        chart_h = h - pad - axis_h

        if chart_w <= 0 or chart_h <= 0:
            return

        total_us = sum(p['duration_ms'] * 1000 for p in phases)
        if total_us == 0:
            self._draw_empty(painter)
            return

        n = len(phases)
        bar_h = max(8, (chart_h - self._BAR_GAP * (n - 1)) // n)

        self._phase_rects.clear()
        cumulative_us = 0.0

        for i, phase in enumerate(phases):
            duration_us = phase['duration_ms'] * 1000
            name = phase['name']
            color_hex = PHASE_COLORS.get(name, COLORS['info'])

            bar_y = chart_y + i * (bar_h + self._BAR_GAP)

            # Phase label — left column, vertically centred
            label_rect = QRect(pad, bar_y, label_w - 6, bar_h)
            painter.setFont(get_per_phase_timing_chart_label_font())
            painter.setPen(QColor(COLORS['text_primary']))
            label_text = name.replace('_', ' ')
            painter.drawText(label_rect, Qt.AlignVCenter | Qt.AlignLeft, label_text)

            # Horizontal bar
            x_start = chart_x + int(cumulative_us / total_us * chart_w)
            bar_w = max(2, int(duration_us / total_us * chart_w))
            bar_rect = QRect(x_start, bar_y, bar_w, bar_h)

            bar_color = QColor(color_hex)
            if name == self._hovered_phase:
                bar_color = bar_color.lighter(130)
            painter.setBrush(bar_color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(bar_rect, self._BAR_RADIUS, self._BAR_RADIUS)

            # Inline µs label when bar is wide enough
            if bar_w >= 44:
                painter.setFont(get_per_phase_timing_chart_value_font())
                painter.setPen(Qt.black)
                us_int = int(duration_us)
                painter.drawText(
                    bar_rect.adjusted(4, 0, -4, 0),
                    Qt.AlignVCenter | Qt.AlignLeft,
                    f'{us_int}µs',
                )

            self._phase_rects.append((name, bar_rect, int(duration_us)))
            cumulative_us += duration_us

        self._draw_x_axis(painter, chart_x, chart_y + chart_h + 4, chart_w, total_us)

    def mouseMoveEvent(self, event) -> None:
        pos = event.pos()
        for name, rect, duration_us in self._phase_rects:
            if rect.contains(pos):
                if self._hovered_phase != name:
                    self._hovered_phase = name
                    self.update()
                label = name.replace('_', ' ')
                QToolTip.showText(event.globalPos(), f'{label}: {duration_us}µs', self)
                return
        if self._hovered_phase is not None:
            self._hovered_phase = None
            self.update()
        QToolTip.hideText()

    def leaveEvent(self, event) -> None:
        if self._hovered_phase is not None:
            self._hovered_phase = None
            self.update()

    def resizeEvent(self, event) -> None:
        self.update()
        super().resizeEvent(event)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _draw_empty(self, painter: QPainter) -> None:
        painter.setPen(QColor(COLORS['text_secondary']))
        painter.setFont(get_per_phase_timing_chart_label_font())
        painter.drawText(self.rect(), Qt.AlignCenter, 'No phase data')

    def _draw_x_axis(
        self, painter: QPainter, x: int, y: int, w: int, total_us: float
    ) -> None:
        painter.setFont(get_per_phase_timing_chart_value_font())
        painter.setPen(QColor(COLORS['text_secondary']))
        for i in range(self._TICK_COUNT + 1):
            tick_x = x + int(i / self._TICK_COUNT * w)
            tick_us = int(i / self._TICK_COUNT * total_us)
            label = f'{tick_us}µs' if tick_us < 1000 else f'{tick_us / 1000:.1f}ms'
            painter.drawText(QRect(tick_x - 26, y, 52, 16), Qt.AlignCenter, label)
