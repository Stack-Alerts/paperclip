"""
Block Search and Selection Panel - UI Component for Strategy Builder

This panel allows users to browse and search building blocks from the registry:
- Search bar with filtering
- Block list with signal counts from historical data
- Expandable signal details
- Add to Strategy functionality
- Multi-criteria filtering (name, category, type)

Author: Strategy Builder Team
Date: 2026-01-16
"""

from typing import Optional, List, Dict
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QGroupBox, QSizePolicy, QSpacerItem,
    QComboBox, QTextEdit, QScrollArea, QFrame, QCheckBox
)
from PyQt5.QtCore import pyqtSignal, Qt, QEvent
from PyQt5.QtGui import QFont, QWheelEvent

from src.strategy_builder.integration.strategy_builder_orchestrator import (
    StrategyBuilderOrchestrator
)
from src.strategy_builder.core.registry_interface import BlockInfo, SearchFilters

# Import centralized styles
from src.strategy_builder.ui.styles import (
    get_label_style, get_expand_button_style, get_add_button_style,
    get_checkbox_style, get_success_button_stylesheet, get_color,
    get_exit_button_stylesheet, get_and_button_stylesheet, get_or_button_stylesheet
)

# Import exit condition dialog
from src.strategy_builder.ui.exit_condition_dialog import ExitConditionDialog

# Import institutional logger
try:
    from src.strategy_builder.utils import logger, LogComponent
    LOGGER_AVAILABLE = True
except ImportError:
    LOGGER_AVAILABLE = False
    logger = None
    LogComponent = None

# Import signal statistics loader
from src.strategy_builder.utils.signal_statistics_loader import (
    SignalStatisticsLoader,
    load_statistics,
    get_signal_display,
    is_statistics_loaded
)
# Import universal combo box fix
from src.strategy_builder.ui.combobox_fix import fix_combobox_white_bars


class BlockListItem(QWidget):
    """
    Custom widget for displaying a block with expandable signal details and selection.
    
    NEW: Phase 1 - Signal Selection UI
    - Shows checkboxes for each signal
    - "Add as AND" and "Add as OR" buttons
    - Emits: (block_name, selected_signals, logic_type)
    """
    
    # NEW SIGNAL: Emits block_name, list of selected signal names, and logic type ("AND" or "OR")
    block_with_signals_selected = pyqtSignal(str, list, str)
    
    # EXIT SIGNAL: Emits signal_name and dialog_config when added as exit condition
    signal_added_as_exit = pyqtSignal(str, dict)
    
    def __init__(self, block_info: BlockInfo, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.block_info = block_info
        self.expanded = False
        
        # Track signal checkboxes
        self.signal_checkboxes: Dict[str, QCheckBox] = {}
        
        # Track which signals have been added (to disable them)
        self.added_signals: set = set()
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI for this block item."""
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Main info layout - removed horizontal split, stack vertically
        
        # Block name and category
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        # Name (bold and larger)
        name_label = QLabel(f"📊 {self.block_info.name}")
        name_font = QFont()
        name_font.setBold(True)
        name_font.setPointSize(12)
        name_label.setFont(name_font)
        name_label.setStyleSheet(get_label_style('default'))
        info_layout.addWidget(name_label)
        
        # Category and Type
        meta_text = f"Category: {self.block_info.category} | Type: {self.block_info.block_type}"
        if hasattr(self.block_info, 'default_weight') and self.block_info.default_weight:
            meta_text += f" | Weight: {self.block_info.default_weight} points"
        meta_label = QLabel(meta_text)
        meta_label.setStyleSheet(get_label_style('muted') + " font-size: 9pt;")
        info_layout.addWidget(meta_label)
        
        layout.addLayout(info_layout)
        
        # Filter visible signals
        self.visible_signals = [
            s for s in self.block_info.signals 
            if getattr(s, 'ui_visible', True) is not False
        ]
        
        # Expand/Collapse signals button - FULL WIDTH, TALL  
        self.expand_button = QPushButton(f"▶ Show Signals ({len(self.visible_signals)})")
        self.expand_button.setMinimumHeight(72)
        self.expand_button.setMaximumHeight(72)
        self.expand_button.setStyleSheet("""
            QPushButton {
                background-color: #2D3748;
                color: #A0AEC0;
                border: 1px solid #374151;
                border-radius: 6px;
                padding: 12px 20px;
                font-size: 11pt;
                text-align: left;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #374151;
                border-color: #00D9FF;
            }
        """)
        self.expand_button.clicked.connect(self._toggle_signals)
        layout.addWidget(self.expand_button)
        
        # Signals section (initially hidden) - NEW: With checkboxes
        self.signals_widget = QWidget()
        signals_layout = QVBoxLayout()
        signals_layout.setContentsMargins(20, 10, 20, 10)
        signals_layout.setSpacing(8)
        
        # Header with instruction
        signals_header = QLabel("Select signals to add:")
        signals_header.setStyleSheet(f"font-weight: bold; color: {get_color('primary')}; font-size: 10pt;")
        signals_layout.addWidget(signals_header)
        
        # Display signals with checkboxes (filter out hidden signals)
        visible_signals = [s for s in self.block_info.signals 
                          if not hasattr(s, 'ui_visible') or s.ui_visible != False]
        
        for signal_info in visible_signals:
            # Create checkbox for this signal
            checkbox_layout = QVBoxLayout()
            checkbox_layout.setSpacing(4)
            
            # Checkbox with signal name and count
            signal_text = signal_info.name
            
            # Add occurrence count if available
            if hasattr(signal_info, 'occurrences') and signal_info.occurrences is not None:
                if hasattr(signal_info, 'total_candles') and signal_info.total_candles > 0:
                    percentage = (signal_info.occurrences / signal_info.total_candles) * 100
                    signal_text += f"  ({signal_info.occurrences:,} found, {percentage:.1f}%)"
                else:
                    signal_text += f"  ({signal_info.occurrences:,} occurrences)"
            
            checkbox = QCheckBox(signal_text)
            checkbox.setStyleSheet("""
                QCheckBox {
                    color: #A0AEC0;
                    font-size: 10pt;
                    font-weight: bold;
                    padding: 4px;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid #374151;
                    border-radius: 4px;
                    background-color: #1A202C;
                }
                QCheckBox::indicator:checked {
                    background-color: #00D9FF;
                    border-color: #00D9FF;
                }
                QCheckBox::indicator:hover {
                    border-color: #00D9FF;
                }
            """)
            
            # Store checkbox reference
            self.signal_checkboxes[signal_info.name] = checkbox
            checkbox_layout.addWidget(checkbox)
            
            # Add signal description with proper indentation using container
            if hasattr(signal_info, 'description') and signal_info.description:
                # Create container widget for indentation
                desc_container = QWidget()
                desc_container_layout = QHBoxLayout(desc_container)
                desc_container_layout.setContentsMargins(40, 0, 0, 0)  # 95px left indent to align properly
                desc_container_layout.setSpacing(0)
                
                desc_label = QLabel(signal_info.description)
                desc_label.setWordWrap(True)
                desc_label.setStyleSheet(get_label_style('muted') + " font-size: 9pt; font-style: italic;")
                desc_container_layout.addWidget(desc_label)
                
                checkbox_layout.addWidget(desc_container)
            
            signals_layout.addLayout(checkbox_layout)
        
        # Buttons section - AND/OR choices
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        buttons_layout.setContentsMargins(0, 15, 0, 10)
        
        # Add as AND button (required) - using centralized style
        self.and_button = QPushButton("➕ Add as AND (Required)")
        self.and_button.setMinimumHeight(40)
        self.and_button.setStyleSheet(get_and_button_stylesheet())
        self.and_button.clicked.connect(lambda: self._add_with_logic("AND"))
        buttons_layout.addWidget(self.and_button)
        
        # Add as OR button (optional/booster) - using centralized style
        self.or_button = QPushButton("➕ Add as OR (Optional)")
        self.or_button.setMinimumHeight(40)
        self.or_button.setStyleSheet(get_or_button_stylesheet())
        self.or_button.clicked.connect(lambda: self._add_with_logic("OR"))
        buttons_layout.addWidget(self.or_button)
        
        # Add as Exit button (Sprint 1.8 - Task 1.8.47)
        self.exit_button = QPushButton("➕ Add as Exit")
        self.exit_button.setMinimumHeight(40)
        self.exit_button.setStyleSheet(get_exit_button_stylesheet())
        self.exit_button.clicked.connect(self._add_as_exit)
        self.exit_button.setToolTip("Add selected signal as exit condition with percentage-based partial exit")
        buttons_layout.addWidget(self.exit_button)
        
        buttons_container.setLayout(buttons_layout)
        signals_layout.addWidget(buttons_container)
        
        # Note about data source
        note_label = QLabel("Note: Signal counts based on last 180 days of BTC data")
        note_label.setStyleSheet(get_label_style('muted') + " font-size: 9pt; font-style: italic; padding-top: 8px;")
        signals_layout.addWidget(note_label)
        
        self.signals_widget.setLayout(signals_layout)
        self.signals_widget.setVisible(False)  # Hidden by default
        layout.addWidget(self.signals_widget)
        
        # Border for the item - dark theme
        self.setStyleSheet("""
            BlockListItem {
                background-color: #1E2128;
                border: 1px solid #3C4149;
                border-radius: 8px;
            }
        """)
        
        self.setLayout(layout)
    
    def _toggle_signals(self):
        """Toggle the visibility of the signals section."""
        self.expanded = not self.expanded
        self.signals_widget.setVisible(self.expanded)
        
        # Use visible signals count (not total)
        visible_count = len(self.visible_signals)
        if self.expanded:
            self.expand_button.setText(f"▼ Hide Signals ({visible_count})")
        else:
            self.expand_button.setText(f"▶ Show Signals ({visible_count})")
    
    def _add_with_logic(self, logic_type: str):
        """
        Handle adding block with selected signals and AND/OR logic.
        
        NEW: Allows multiple additions from same block - marks added signals as disabled.
        
        Args:
            logic_type: "AND" or "OR"
        """
        # Collect selected signals (only unchecked, non-added ones)
        selected_signals = []
        for signal_name, checkbox in self.signal_checkboxes.items():
            if checkbox.isChecked() and signal_name not in self.added_signals:
                selected_signals.append(signal_name)
        
        # Validate at least one signal selected
        if not selected_signals:
            if LOGGER_AVAILABLE and logger:
                logger.warning(LogComponent.SEARCH_PANEL, 
                             f"No NEW signals selected for block {self.block_info.name}")
            return
        
        # Log the selection
        if LOGGER_AVAILABLE and logger:
            logger.info(LogComponent.SEARCH_PANEL,
                       f"Adding signals to block",
                       {
                           'block': self.block_info.name,
                           'signals': selected_signals,
                           'logic': logic_type,
                           'previously_added': list(self.added_signals)
                       })
        
        # Emit the new signal with block name, selected signals, and logic type
        self.block_with_signals_selected.emit(
            self.block_info.name,
            selected_signals,
           logic_type
        )
        
        # NEW: Mark signals as added and disable their checkboxes
        for signal_name in selected_signals:
            self.added_signals.add(signal_name)
            checkbox = self.signal_checkboxes[signal_name]
            checkbox.setChecked(False)  # Uncheck
            checkbox.setEnabled(False)  # Disable
            
            # Update styling to show as added
            checkbox.setStyleSheet("""
                QCheckBox {
                    color: #666666;
                    font-size: 10pt;
                    padding: 4px;
                    text-decoration: line-through;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid #3C4149;
                    border-radius: 4px;
                    background-color: #3C4149;
                }
            """)
        
        # Update expand button text to show added count
        added_count = len(self.added_signals)
        total_count = len(self.visible_signals)
        remaining = total_count - added_count
        
        if remaining > 0:
            if self.expanded:
                self.expand_button.setText(f"▼ Hide Signals ({remaining} available, {added_count} added)")
            else:
                self.expand_button.setText(f"▶ Show Signals ({remaining} available, {added_count} added)")
        else:
            # All signals added - now disable everything
            self.expand_button.setText(f"✓ All Signals Added ({added_count})")
            self.expand_button.setEnabled(False)
            self.and_button.setEnabled(False)
            self.or_button.setEnabled(False)
        
        # Don't collapse - allow adding more signals
        # User can collapse manually if desired
    
    def _add_as_exit(self):
        """
        Handle adding selected signal as exit condition.
        Sprint 1.8 Task 1.8.47
        
        Opens ExitConditionDialog for configuring the exit condition.
        Only allows selecting ONE signal for exit conditions.
        """
        # Collect selected signals (only ONE allowed for exits)
        selected_signals = []
        for signal_name, checkbox in self.signal_checkboxes.items():
            if checkbox.isChecked() and signal_name not in self.added_signals:
                selected_signals.append(signal_name)
        
        # Validate exactly one signal selected
        if len(selected_signals) == 0:
            if LOGGER_AVAILABLE and logger:
                logger.warning(LogComponent.SEARCH_PANEL, 
                             f"No signal selected for exit condition")
            print("\n⚠️  Please select ONE signal to add as exit condition\n")
            return
        
        if len(selected_signals) > 1:
            if LOGGER_AVAILABLE and logger:
                logger.warning(LogComponent.SEARCH_PANEL, 
                             f"Multiple signals selected for exit - only one allowed")
            print("\n⚠️  Exit conditions support ONE signal at a time. Please select only one signal.\n")
            return
        
        signal_name = selected_signals[0]
        
        # Open ExitConditionDialog
        dialog = ExitConditionDialog(
            signal_name=signal_name,
            parent=self
        )
        
        if dialog.exec_():
            # User accepted - GET DIALOG CONFIG (BUG FIX)
            dialog_config = dialog.get_config()
            
            # Emit signal with signal name AND config
            self.signal_added_as_exit.emit(signal_name, dialog_config)
            
            # Mark signal as added
            self.added_signals.add(signal_name)
            checkbox = self.signal_checkboxes[signal_name]
            checkbox.setChecked(False)
            checkbox.setEnabled(False)
            
            # Update styling to show as added
            checkbox.setStyleSheet("""
                QCheckBox {
                    color: #666666;
                    font-size: 10pt;
                    padding: 4px;
                    text-decoration: line-through;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid #3C4149;
                    border-radius: 4px;
                    background-color: #3C4149;
                }
            """)
            
            if LOGGER_AVAILABLE and logger:
                logger.info(LogComponent.SEARCH_PANEL,
                           f"Signal added as exit condition",
                           {
                               'signal': signal_name,
                               'block': self.block_info.name
                           })
    
    # NOTE: disable_add_button() and enable_add_button() methods removed
    # The old "Add to Strategy" button no longer exists
    # Blocks are now disabled via the expand button after selection


class BlockSearchPanel(QWidget):
    """
    Panel for searching and selecting building blocks from the registry.
    
    Signals:
        block_selected: Emitted when a block is selected to be added to strategy (str: block_name)
    """
    
    block_selected = pyqtSignal(str)
    
    def __init__(self, orchestrator: StrategyBuilderOrchestrator, parent: Optional[QWidget] = None):
        """
        Initialize the Block Search Panel.
        
        Args:
            orchestrator: StrategyBuilderOrchestrator instance for backend communication
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.orchestrator = orchestrator
        
        # Track added blocks to disable their "Add" buttons
        self.added_blocks: set = set()
        
        # UI Components
        self.search_input: Optional[QLineEdit] = None
        self.category_filter: Optional[QComboBox] = None
        self.type_filter: Optional[QComboBox] = None
        self.blocks_scroll_area: Optional[QScrollArea] = None
        self.blocks_container: Optional[QWidget] = None
        self.blocks_layout: Optional[QVBoxLayout] = None
        
        # Block items cache
        self.block_items: Dict[str, BlockListItem] = {}
        
        # Load signal statistics
        self.stats_loader = SignalStatisticsLoader()
        self.stats_loaded = self.stats_loader.load()
        
        if self.stats_loaded:
            print("✅ Signal statistics loaded successfully")
        else:
            print("⚠️  Signal statistics not available - run: python scripts/analyze_signal_occurrences.py")
        
        self._init_ui()
        self._load_blocks()
    
    def _init_ui(self):
        """Initialize the user interface components."""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Group box
        group_box = QGroupBox("🔧 Available Building Blocks")
        
        # Set title font programmatically (CSS doesn't work for QGroupBox::title)
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        group_box.setFont(title_font)
        
        group_layout = QVBoxLayout()
        group_layout.setSpacing(15)
        group_layout.setContentsMargins(15, 20, 15, 15)  # Match backtest panel padding
        
        # Reset font for content (only title should be 12pt)
        # CRITICAL: Make it instance variable so it persists!
        self.content_font = QFont()
        self.content_font.setPointSize(10)
        self.content_font.setBold(False)  # Explicitly not bold
        
        # Search and filter controls - increased spacing
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(20)  # More space between search and filters
        
        # Search bar
        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)
        search_label = QLabel("🔍 Search:")
        search_label.setFont(self.content_font)
        search_label.setStyleSheet(get_label_style('muted'))
        search_label.setMinimumWidth(70)
        self.search_input = QLineEdit()
        self.search_input.setFont(self.content_font)
        self.search_input.setPlaceholderText("Search by block name, description, or signal...")
        self.search_input.setMinimumHeight(36)  # Bigger input
        self.search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input, stretch=1)
        controls_layout.addLayout(search_layout)
        
        # Filters
        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(15)  # Space between filter elements
        
        # Category filter
        category_label = QLabel("Category:")
        category_label.setFont(self.content_font)
        category_label.setStyleSheet(get_label_style('muted'))
        filters_layout.addWidget(category_label)
        self.category_filter = QComboBox()
        self.category_filter.setFont(self.content_font)
        self.category_filter.addItem("All Categories")
        fix_combobox_white_bars(self.category_filter)  # Comprehensive fix
        self.category_filter.currentTextChanged.connect(self._on_filter_changed)
        filters_layout.addWidget(self.category_filter)
        
        # Type filter
        type_label = QLabel("Type:")
        type_label.setFont(self.content_font)
        type_label.setStyleSheet(get_label_style('muted'))
        filters_layout.addWidget(type_label)
        self.type_filter = QComboBox()
        self.type_filter.setFont(self.content_font)
        self.type_filter.addItem("All Types")
        fix_combobox_white_bars(self.type_filter)  # Comprehensive fix
        self.type_filter.currentTextChanged.connect(self._on_filter_changed)
        filters_layout.addWidget(self.type_filter)
        
        filters_layout.addStretch()
        controls_layout.addLayout(filters_layout)
        
        group_layout.addLayout(controls_layout)
        
        # Scroll area for blocks
        self.blocks_scroll_area = QScrollArea()
        self.blocks_scroll_area.setWidgetResizable(True)
        self.blocks_scroll_area.setMinimumHeight(400)
        
        # Container widget for blocks
        self.blocks_container = QWidget()
        self.blocks_layout = QVBoxLayout()
        self.blocks_layout.setSpacing(5)  # Reduced from 10 to 5
        self.blocks_layout.setContentsMargins(5, 5, 5, 5)
        self.blocks_container.setLayout(self.blocks_layout)
        
        self.blocks_scroll_area.setWidget(self.blocks_container)
        
        # Install event filter to speed up scrolling
        self.blocks_scroll_area.viewport().installEventFilter(self)
        
        group_layout.addWidget(self.blocks_scroll_area)
        
        group_box.setLayout(group_layout)
        layout.addWidget(group_box)
        
        self.setLayout(layout)
    
    def eventFilter(self, obj, event):
        """
        Event filter to make scrolling ultra fast (400x speed).
        
        Args:
            obj: Object that received the event
            event: The event
            
        Returns:
            True if event was handled, False otherwise
        """
        if event.type() == QEvent.Wheel and obj == self.blocks_scroll_area.viewport():
            # Get the wheel event
            wheel_event = event
            
            # Get current scroll position
            scrollbar = self.blocks_scroll_area.verticalScrollBar()
            
            # Multiply the scroll delta by 400 for ultra fast scrolling
            delta = wheel_event.angleDelta().y()
            scrollbar.setValue(scrollbar.value() - (delta * 400 // 120))
            
            # Mark event as handled
            return True
        
        # Pass other events to base class
        return super().eventFilter(obj, event)
    
    def _enrich_signals_with_stats(self, block_info: BlockInfo, block_name: str):
        """
        Enrich signal objects with occurrence statistics from loader.
        
        Args:
            block_info: Block information object with signals
            block_name: Name of the block
        """
        # Get all signal statistics for this block
        all_stats = self.stats_loader.get_all_signals_for_block(block_name)
        
        if not all_stats:
            return
        
        # Enrich each signal with its statistics
        for signal in block_info.signals:
            signal_name = signal.name
            
            if signal_name in all_stats:
                stats = all_stats[signal_name]
                
                # Add occurrence data directly to signal object
                signal.occurrences = stats.get('count', 0)
                signal.occurrence_percentage = stats.get('percentage', 0.0)
                signal.total_candles = stats.get('total_candles', 0)
    
    def _load_blocks(self):
        """Load all blocks from the registry and populate the UI."""
        if LOGGER_AVAILABLE and logger:
            logger.info(LogComponent.SEARCH_PANEL, "Starting to load blocks from registry")
        
        try:
            # Get all blocks from orchestrator's registry interface
            if LOGGER_AVAILABLE and logger:
                logger.debug(LogComponent.SEARCH_PANEL, "Calling orchestrator.search_blocks()")
            
            search_results = self.orchestrator.search_blocks("")  # Empty query returns all
            
            if LOGGER_AVAILABLE and logger:
                logger.info(LogComponent.SEARCH_PANEL, f"Retrieved {len(search_results) if search_results else 0} search results")
            
            if not search_results:
                # Show empty state
                if LOGGER_AVAILABLE and logger:
                    logger.warning(LogComponent.SEARCH_PANEL, "No blocks found in registry")
                
                empty_label = QLabel("No blocks found in registry.")
                empty_label.setAlignment(Qt.AlignCenter)
                empty_label.setStyleSheet(get_label_style('muted') + " font-size: 12pt; padding: 50px;")
                self.blocks_layout.addWidget(empty_label)
                return
            
            # Get block details for each block
            categories = set()
            types = set()
            
            for idx, search_result in enumerate(search_results):
                try:
                    # Extract block name from SearchResult object
                    block_name = search_result.block_name
                    
                    if LOGGER_AVAILABLE and logger and idx == 0:
                        logger.debug(LogComponent.SEARCH_PANEL, f"Processing first block: {block_name}")
                    
                    # Use registry_interface to get proper BlockInfo object (not raw dict)
                    block_info = self.orchestrator.registry_interface.get_block(block_name)
                    
                    if block_info:
                        # Add to categories and types sets
                        if hasattr(block_info, 'category'):
                            categories.add(block_info.category)
                        if hasattr(block_info, 'block_type'):
                            types.add(block_info.block_type)
                        
                        # Enrich signals with occurrence statistics
                        if self.stats_loaded:
                            self._enrich_signals_with_stats(block_info, block_name)
                        
                        # Create block item widget
                        block_item = BlockListItem(block_info)
                        
                        # NEW: Connect to signal with AND/OR logic
                        block_item.block_with_signals_selected.connect(self._on_block_with_signals_selected)
                        
                        # Sprint 1.8 Task 1.8.47: Connect exit signal
                        block_item.signal_added_as_exit.connect(self._on_signal_added_as_exit)
                        
                        # Store reference
                        self.block_items[block_name] = block_item
                        
                        # Add to layout
                        self.blocks_layout.addWidget(block_item)
                    else:
                        if LOGGER_AVAILABLE and logger:
                            logger.warning(LogComponent.SEARCH_PANEL, f"Block info not found for {block_name}")
                
                except Exception as block_error:
                    if LOGGER_AVAILABLE and logger:
                        logger.exception(LogComponent.SEARCH_PANEL, f"Error processing block {idx}", block_error)
            
            # Add stretch at the end
            self.blocks_layout.addStretch()
            
            if LOGGER_AVAILABLE and logger:
                logger.info(LogComponent.SEARCH_PANEL, f"Successfully loaded {len(self.block_items)} blocks", {
                    'categories': list(categories),
                    'types': list(types)
                })
            
            # Populate filter dropdowns
            for category in sorted(categories):
                self.category_filter.addItem(category)
            
            for block_type in sorted(types):
                self.type_filter.addItem(block_type)
                
        except Exception as e:
            # Log the error with full details
            if LOGGER_AVAILABLE and logger:
                logger.exception(LogComponent.SEARCH_PANEL, "Critical error loading blocks", e)
            
            # Show error state
            error_label = QLabel(f"Error loading blocks: {str(e)}")
            error_label.setStyleSheet(get_label_style('error') + " font-size: 11pt; padding: 20px;")
            error_label.setWordWrap(True)
            self.blocks_layout.addWidget(error_label)
    
    def _on_search_changed(self, text: str):
        """Handle search text changes."""
        self._apply_filters()
    
    def _on_filter_changed(self):
        """Handle filter dropdown changes."""
        self._apply_filters()
    
    def _apply_filters(self):
        """Apply current search and filter criteria to visible blocks."""
        search_text = self.search_input.text().lower()
        category = self.category_filter.currentText()
        block_type = self.type_filter.currentText()
        
        # Show/hide blocks based on filters
        for block_name, block_item in self.block_items.items():
            block_info = block_item.block_info
            
            # Check search text
            matches_search = True
            if search_text:
                matches_search = (
                    search_text in block_name.lower() or
                    (hasattr(block_info, 'description') and block_info.description and 
                     search_text in block_info.description.lower()) or
                    any(search_text in signal.name.lower() for signal in block_info.signals)
                )
            
            # Check category filter
            matches_category = (
                category == "All Categories" or
                (hasattr(block_info, 'category') and block_info.category == category)
            )
            
            # Check type filter
            matches_type = (
                block_type == "All Types" or
                (hasattr(block_info, 'block_type') and block_info.block_type == block_type)
            )
            
            # Show/hide based on all criteria
            block_item.setVisible(matches_search and matches_category and matches_type)
    
    def _on_block_with_signals_selected(self, block_name: str, signals: List[str], logic_type: str):
        """
        NEW: Handle when block is added with selected signals and AND/OR logic.
        
        Uses the institutional-grade add_block_with_signals() method that handles
        both new blocks and adding signals to existing blocks.
        
        Args:
            block_name: Name of the block
            signals: List of selected signal names
            logic_type: "AND" or "OR"
        """
        if LOGGER_AVAILABLE and logger:
            logger.info(LogComponent.SEARCH_PANEL,
                       f"Block added with signals",
                       {
                           'block': block_name,
                           'signals': signals,
                           'logic': logic_type,
                           'signal_count': len(signals)
                       })
        
        # Use the new institutional-grade method that handles both cases
        result = self.orchestrator.add_block_with_signals(
            block_name=block_name,
            signal_names=signals,
            block_logic=logic_type,
            signal_logic=logic_type
        )
        
        if result.success:
            # Mark as added
            self.added_blocks.add(block_name)
            
            # Emit for backward compatibility
            self.block_selected.emit(block_name)
            
            if LOGGER_AVAILABLE and logger:
                logger.info(LogComponent.SEARCH_PANEL,
                           f"Successfully added to strategy",
                           {
                               'block': block_name,
                               'signals_added': result.data.get('signals_added') if result.data else signals,
                               'block_existed': result.data.get('block_existed') if result.data else False
                           })
            
            print(f"\n✅ BLOCK ADDED: {block_name}")
            print(f"✅ SIGNALS: {signals}")
            print(f"✅ LOGIC: {logic_type}")
            print(f"✅ Message: {result.message}\n")
        else:
            if LOGGER_AVAILABLE and logger:
                logger.error(LogComponent.SEARCH_PANEL,
                            f"Failed to add block with signals",
                            {
                                'block': block_name,
                                'signals': signals,
                                'errors': result.errors
                            })
            
            print(f"\n❌ FAILED: {block_name}")
            print(f"❌ Error: {result.message}")
            print(f"❌ Details: {result.errors}\n")
    
    def _on_signal_added_as_exit(self, signal_name: str, dialog_config: dict):
        """
        Handle when signal is added as exit condition.
        Sprint 1.8 Task 1.8.47 + Integration - BUG FIX
        
        Calls orchestrator to add exit condition with USER'S dialog configuration.
        
        Args:
            signal_name: Name of the signal added as exit condition
            dialog_config: Configuration from ExitConditionDialog.get_config()
        """
        # Validate config
        if not dialog_config or not dialog_config.get('signal_name'):
            if LOGGER_AVAILABLE and logger:
                logger.error(LogComponent.SEARCH_PANEL, "Invalid dialog configuration")
            print("\n❌ FAILED: Invalid exit condition configuration\n")
            return
        
        # Call orchestrator with USER'S actual configuration values
        # Include block_name and parent_signal_name for BLOCK/SIGNAL binding levels
        result = self.orchestrator.add_exit_condition(
            signal_name=dialog_config['signal_name'],
            percentage=dialog_config.get('percentage', 0.5),  # Use dialog value
            binding_level=dialog_config.get('binding_level', 'STRATEGY'),  # Use dialog value
            exit_mode=dialog_config.get('exit_mode', 'ABSOLUTE'),  # Use dialog value
            tp_proximity_threshold=dialog_config.get('tp_proximity_threshold', 2.0),
            reversal_trigger=dialog_config.get('reversal_trigger', 0.5),
            block_name=dialog_config.get('block_name'),  # For BLOCK/SIGNAL binding
            parent_signal_name=dialog_config.get('parent_signal_name')  # For SIGNAL binding
        )
        
        if result.success:
            if LOGGER_AVAILABLE and logger:
                logger.info(LogComponent.SEARCH_PANEL,
                           f"Signal added as exit condition",
                           {
                               'signal': signal_name,
                               'result': result.message
                           })
            
            print(f"\n✅ EXIT CONDITION ADDED: {signal_name}")
            print(f"✅ Added to strategy-level exits")
            print(f"✅ {result.message}\n")
            
            # CRITICAL: Emit signal to refresh blocks panel UI
            self.block_selected.emit("EXIT_CONDITION_ADDED")
        else:
            if LOGGER_AVAILABLE and logger:
                logger.error(LogComponent.SEARCH_PANEL,
                            f"Failed to add exit condition",
                            {
                                'signal': signal_name,
                                'errors': result.errors
                            })
            
            print(f"\n❌ FAILED TO ADD EXIT: {signal_name}")
            print(f"❌ Error: {result.message}")
            if result.errors:
                print(f"❌ Details: {result.errors}\n")
    
    def mark_block_as_added(self, block_name: str):
        """
        Mark a block as added.
        
        NOTE: Old button disabling removed - blocks now disabled via expand button.
        
        Args:
            block_name: Name of the block to mark as added
        """
        self.added_blocks.add(block_name)
        # No button to disable anymore - handled in BlockListItem._add_with_logic()
    
    def mark_block_as_removed(self, block_name: str):
        """
        Mark a block as removed (would need to re-enable UI).
        
        NOTE: Currently blocks can't be removed after adding (buttons stay disabled).
        
        Args:
            block_name: Name of the block to mark as removed
        """
        if block_name in self.added_blocks:
            self.added_blocks.remove(block_name)
        
        # NOTE: Would need to re-enable the expand button and reset checkboxes
        # This is a TODO for later - for now blocks remain disabled after adding
    
    def get_added_blocks(self) -> List[str]:
        """
        Get list of blocks that have been added to the strategy.
        
        Returns:
            List of block names
        """
        return list(self.added_blocks)
    
    def clear_added_blocks(self):
        """Clear all added blocks and re-enable all add buttons."""
        for block_name in list(self.added_blocks):
            self.mark_block_as_removed(block_name)
    
    def get_search_text(self) -> str:
        """Get the current search text."""
        return self.search_input.text()
    
    def get_selected_category(self) -> str:
        """Get the currently selected category filter."""
        return self.category_filter.currentText()
    
    def get_selected_type(self) -> str:
        """Get the currently selected type filter."""
        return self.type_filter.currentText()
    
    def get_visible_blocks_count(self) -> int:
        """Get the count of currently visible blocks."""
        return sum(1 for item in self.block_items.values() if item.isVisible())
