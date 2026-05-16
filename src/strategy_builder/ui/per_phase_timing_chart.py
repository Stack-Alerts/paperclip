"""
PerPhaseTimingChart — per-phase ITM cycle timing view (P2 B1).

Displays a QTableView backed by PhaseTimingDataModel, with per-phase row
coloring drawn from PHASE_COLORS so each of the 11 ITM phases is
immediately recognisable at a glance.

Reads from: PhaseTimingDataModel (provided by caller)
Colors: styles.PHASE_COLORS (never hardcoded here)
"""

from __future__ import annotations

from PyQt5.QtCore import Qt, QModelIndex
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QTableView,
    QHeaderView,
    QStyledItemDelegate,
    QStyleOptionViewItem,
)

from .phase_timing_data_model import PhaseTimingDataModel
from .styles import COLORS, PHASE_COLORS, PHASE_TIMING, PHASE_TIMING_TABLE_COLUMNS


class _PhaseColorDelegate(QStyledItemDelegate):
    """Applies PHASE_COLORS to table rows based on phase name in column 0."""

    def initStyleOption(self, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        super().initStyleOption(option, index)
        phase_name = index.siblingAtColumn(0).data(Qt.DisplayRole) or ""
        color_hex = PHASE_COLORS.get(phase_name)
        if color_hex:
            option.backgroundBrush = QColor(color_hex)
            option.palette.setColor(option.palette.Base, QColor(color_hex))

    def paint(self, painter, option, index):
        phase_name = index.siblingAtColumn(0).data(Qt.DisplayRole) or ""
        color_hex = PHASE_COLORS.get(phase_name)
        if color_hex:
            bg = QColor(color_hex)
            bg.setAlpha(50)
            painter.fillRect(option.rect, bg)
        super().paint(painter, option, index)


class PerPhaseTimingChart(QWidget):
    """
    Widget showing per-phase ITM cycle timing as a styled QTableView.

    Shows 11-phase breakdown when PhaseStarted/PhaseCompleted events are
    available via PhaseTimingDataModel.  Each row is color-coded by phase
    using PHASE_COLORS from styles.py.

    Parameters
    ----------
    model:
        PhaseTimingDataModel populated by DecisionCycleMonitor.
    parent:
        Optional Qt parent.
    """

    def __init__(self, model: PhaseTimingDataModel, parent: QWidget | None = None):
        super().__init__(parent)
        self._model = model
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        title = QLabel("B1 Cycle Phases")
        title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['panel_title']}; padding: 2px 4px;")
        layout.addWidget(title)

        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setItemDelegate(_PhaseColorDelegate(self._table))
        self._table.setAlternatingRowColors(False)
        self._table.setShowGrid(False)
        self._table.setSelectionMode(QTableView.NoSelection)
        self._table.setFocusPolicy(Qt.NoFocus)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setHighlightSections(False)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        row_h = PHASE_TIMING['table_row_height']
        hdr_h = PHASE_TIMING['table_header_height']
        self._table.verticalHeader().setDefaultSectionSize(row_h)
        self._table.horizontalHeader().setFixedHeight(hdr_h)

        self._table.setStyleSheet(f"""
            QTableView {{
                background: {COLORS['bg_dark']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                gridline-color: transparent;
            }}
            QHeaderView::section {{
                background: {COLORS['bg_secondary']};
                color: {COLORS['panel_title']};
                font-weight: bold;
                border: none;
                border-bottom: 1px solid {COLORS['border']};
                padding: 4px;
            }}
        """)

        for col, cfg in enumerate(PHASE_TIMING_TABLE_COLUMNS):
            self._table.setColumnWidth(col, cfg['width'])

        layout.addWidget(self._table)

    def refresh(self) -> None:
        """Trigger a visual refresh (model already updated by caller)."""
        self._table.viewport().update()
