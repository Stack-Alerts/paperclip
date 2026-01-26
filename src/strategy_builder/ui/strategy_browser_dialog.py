"""
Strategy Browser Dialog
SPRINT 1.6.1 - Phase 2 Day 4-5

Database-backed strategy browser replacing file dialogs.
Provides visual browsing, version management, and quick actions.

Uses institutional-grade DATABASE-FIRST architecture.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QComboBox, QWidget, QHeaderView,
    QAbstractItemView, QStyledItemDelegate, QStyleOptionViewItem, QGridLayout,
    QFrame, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QSettings, QModelIndex, QRectF
from PyQt5.QtGui import QFont, QTextDocument, QAbstractTextDocumentLayout, QPalette

from src.optimizer_v3.database import get_database_manager
from .styles import (
    get_main_stylesheet,
    get_primary_button_stylesheet,
    get_secondary_button_stylesheet,
    get_danger_button_stylesheet,
    get_input_field_stylesheet,
    get_table_stylesheet,
    create_font,
    get_color
)
# Import universal combo box fix (EXACTLY like block_search_panel.py)
from src.strategy_builder.ui.combobox_fix import fix_combobox_white_bars


class HTMLDelegate(QStyledItemDelegate):
    """Custom delegate to render HTML in table cells"""
    
    def paint(self, painter, option: QStyleOptionViewItem, index: QModelIndex):
        """Paint HTML content"""
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        
        painter.save()
        
        # Create text document for HTML rendering
        doc = QTextDocument()
        doc.setHtml(options.text)
        
        # Set text color from palette
        doc.setDefaultStyleSheet("body { color: #FFFFFF; }")
        
        # Clear text in options (we'll draw it ourselves)
        options.text = ""
        
        # Draw background and borders
        options.widget.style().drawControl(options.widget.style().ControlElement.CE_ItemViewItem, options, painter)
        
        # Draw HTML text
        painter.translate(options.rect.left(), options.rect.top())
        clip = options.rect.adjusted(0, 0, -options.rect.left(), -options.rect.top())
        doc.setTextWidth(clip.width())
        # Convert QRect to QRectF for drawContents
        doc.drawContents(painter, QRectF(clip))
        
        painter.restore()
    
    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex):
        """Calculate size hint for HTML content"""
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        
        doc = QTextDocument()
        doc.setHtml(options.text)
        doc.setTextWidth(option.rect.width())
        
        return doc.size().toSize()


class StrategyBrowserDialog(QMainWindow):
    """
    Strategy browser window for database-backed strategy management
    
    Features:
    - Visual table of all strategies with metadata
    - Search and filter capabilities
    - Version information display
    - Quick actions (Open, Delete, Duplicate)
    - Double-click to open
    
    Signals:
        strategy_selected: Emitted when strategy selected (strategy_id, version_id)
    """
    
    strategy_selected = pyqtSignal(str, str)  # strategy_id, version_id
    
    def __init__(self, parent: Optional[QWidget] = None, mode: str = 'open'):
        """
        Initialize strategy browser
        
        Args:
            parent: Parent widget
            mode: Dialog mode ('open' or 'save_as')
        """
        super().__init__(parent)
        self.mode = mode
        self.selected_strategy_id = None
        self.selected_version_id = None
        self.db = None
        
        self._init_ui()
        self._restore_settings()
        self._load_strategies()
    
    def _init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle("Strategy Browser" if self.mode == 'open' else "Save Strategy As")
        self.setMinimumSize(900, 600)
        self.setStyleSheet(get_main_stylesheet())
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("📚 Strategy Browser" if self.mode == 'open' else "💾 Save Strategy As")
        title_label.setFont(create_font(16, bold=True))
        title_label.setStyleSheet("color: #095983; font-size: 16pt; font-weight: bold;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Search box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search strategies...")
        self.search_input.setStyleSheet(get_input_field_stylesheet())
        self.search_input.setMinimumWidth(250)
        self.search_input.textChanged.connect(self._on_search_changed)
        header_layout.addWidget(self.search_input)
        
        layout.addLayout(header_layout)
        
        # Filter row
        filter_layout = QHBoxLayout()
        
        filter_label = QLabel("Strategy Type:")
        filter_label.setFont(create_font(10))
        filter_label.setStyleSheet(f"color: {get_color('text_secondary')};")
        filter_layout.addWidget(filter_label)
        
        self.type_filter = QComboBox()
        self.type_filter.addItems(["All", "Bullish", "Bearish"])
        fix_combobox_white_bars(self.type_filter)
        self.type_filter.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.type_filter)
        
        filter_layout.addStretch()
        
        # Strategy count
        self.count_label = QLabel("0 strategies")
        self.count_label.setFont(create_font(9))
        self.count_label.setStyleSheet(f"color: {get_color('text_tertiary')};")
        filter_layout.addWidget(self.count_label)
        
        layout.addLayout(filter_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Strategy Name", "Type", "Version", "Last Modified", "Tests", "Performance"
        ])
        self.table.setStyleSheet(get_table_stylesheet())
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        
        # Column widths - Make columns 2x wider minimum
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Name (flexible)
        header.setMinimumSectionSize(120)  # Minimum width for all columns
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # Type
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)  # Version
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)  # Modified
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)  # Tests
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)  # Performance
        
        # Set initial widths (2x wider than before)
        header.resizeSection(1, 240)  # Type
        header.resizeSection(2, 240)  # Version
        header.resizeSection(3, 400)  # Last Modified
        header.resizeSection(4, 150)  # Tests
        header.resizeSection(5, 240)  # Performance
        
        # Enable sorting (clickable headers with sort indicators)
        self.table.setSortingEnabled(True)
        
        # Set HTML delegate for name column (column 0) to render rich text
        self.table.setItemDelegateForColumn(0, HTMLDelegate(self.table))
        
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.itemDoubleClicked.connect(self._on_double_click)
        
        layout.addWidget(self.table)
        
        # Strategy Details Panel (450px, 3-column grid, institutional-grade)
        self.details_frame = QFrame()
        self.details_frame.setFixedHeight(450)
        # Match GroupBox styling from styles.py (#1E2128 background)
        self.details_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {get_color('bg_medium')};
                border: 1px solid {get_color('border')};
                border-radius: 8px;
            }}
        """)
        self.details_frame.setVisible(False)  # Hidden until selection
        
        details_layout = QGridLayout(self.details_frame)
        details_layout.setSpacing(20)
        details_layout.setContentsMargins(20, 16, 20, 16)
        
        # Create labels with proper styling FROM STYLES.PY ONLY
        self.detail_labels = {}
        
        # Column 1: Strategy Info
        col1_title = QLabel("📊 STRATEGY INFORMATION")
        col1_title.setFont(create_font(10, bold=True))
        # Use exact GroupBox title color from styles.py
        col1_title.setStyleSheet("color: #095983; padding-bottom: 8px;")
        details_layout.addWidget(col1_title, 0, 0)
        
        self.detail_labels['name'] = QLabel("Select a strategy to view details")
        self.detail_labels['name'].setFont(create_font(10))
        self.detail_labels['name'].setStyleSheet(f"color: {get_color('text_primary')}; padding: 4px 0px;")
        self.detail_labels['name'].setWordWrap(True)
        details_layout.addWidget(self.detail_labels['name'], 1, 0, 1, 1)
        
        self.detail_labels['description'] = QLabel("Description will appear here")
        self.detail_labels['description'].setFont(create_font(9))
        self.detail_labels['description'].setStyleSheet(f"color: {get_color('text_secondary')}; padding: 4px 0px;")
        self.detail_labels['description'].setWordWrap(True)
        details_layout.addWidget(self.detail_labels['description'], 2, 0, 1, 1)
        
        self.detail_labels['meta'] = QLabel("No metadata")
        self.detail_labels['meta'].setFont(create_font(9))
        self.detail_labels['meta'].setStyleSheet(f"color: {get_color('text_muted')}; padding: 4px 0px;")
        details_layout.addWidget(self.detail_labels['meta'], 3, 0, 1, 1)
        
        # Column 2: Configuration
        col2_title = QLabel("⚙️ CONFIGURATION")
        col2_title.setFont(create_font(10, bold=True))
        # Use exact GroupBox title color from styles.py
        col2_title.setStyleSheet("color: #095983; padding-bottom: 8px;")
        details_layout.addWidget(col2_title, 0, 1)
        
        self.detail_labels['blocks'] = QLabel("No blocks configured")
        self.detail_labels['blocks'].setFont(create_font(9))
        self.detail_labels['blocks'].setStyleSheet(f"color: {get_color('text_secondary')}; padding: 4px 0px;")
        self.detail_labels['blocks'].setWordWrap(True)
        details_layout.addWidget(self.detail_labels['blocks'], 1, 1, 2, 1)
        
        self.detail_labels['signals'] = QLabel("No signals configured")
        self.detail_labels['signals'].setFont(create_font(9))
        self.detail_labels['signals'].setStyleSheet(f"color: {get_color('text_muted')}; padding: 4px 0px;")
        self.detail_labels['signals'].setWordWrap(True)
        details_layout.addWidget(self.detail_labels['signals'], 3, 1, 1, 1)
        
        # Column 3: Performance & Metrics
        col3_title = QLabel("📈 PERFORMANCE")
        col3_title.setFont(create_font(10, bold=True))
        # Use exact GroupBox title color from styles.py
        col3_title.setStyleSheet("color: #095983; padding-bottom: 8px;")
        details_layout.addWidget(col3_title, 0, 2)
        
        self.detail_labels['tests'] = QLabel("No tests run")
        self.detail_labels['tests'].setFont(create_font(9))
        self.detail_labels['tests'].setStyleSheet(f"color: {get_color('text_muted')}; padding: 4px 0px;")
        details_layout.addWidget(self.detail_labels['tests'], 1, 2, 1, 1)
        
        self.detail_labels['performance'] = QLabel("Run backtest to see metrics")
        self.detail_labels['performance'].setFont(create_font(9))
        self.detail_labels['performance'].setStyleSheet(f"color: {get_color('text_secondary')}; padding: 4px 0px;")
        self.detail_labels['performance'].setWordWrap(True)
        details_layout.addWidget(self.detail_labels['performance'], 2, 2, 1, 1)
        
        self.detail_labels['status'] = QLabel("Status: Unknown")
        self.detail_labels['status'].setFont(create_font(9))
        self.detail_labels['status'].setStyleSheet(f"color: {get_color('text_muted')}; padding: 4px 0px;")
        details_layout.addWidget(self.detail_labels['status'], 3, 2, 1, 1)
        
        # Set column stretches for equal width
        details_layout.setColumnStretch(0, 1)
        details_layout.setColumnStretch(1, 1)
        details_layout.setColumnStretch(2, 1)
        
        # Set row stretches for better spacing
        details_layout.setRowStretch(1, 2)
        details_layout.setRowStretch(2, 2)
        details_layout.setRowStretch(3, 1)
        
        layout.addWidget(self.details_frame)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        # Left side actions
        if self.mode == 'open':
            self.delete_btn = QPushButton("🗑️ Delete")
            self.delete_btn.setStyleSheet(get_danger_button_stylesheet())
            self.delete_btn.setEnabled(False)
            self.delete_btn.clicked.connect(self._on_delete)
            button_layout.addWidget(self.delete_btn)
            
            self.duplicate_btn = QPushButton("📋 Duplicate")
            self.duplicate_btn.setStyleSheet(get_secondary_button_stylesheet())
            self.duplicate_btn.setEnabled(False)
            self.duplicate_btn.clicked.connect(self._on_duplicate)
            button_layout.addWidget(self.duplicate_btn)
            
            self.export_btn = QPushButton("📥 Export to JSON")
            self.export_btn.setStyleSheet(get_secondary_button_stylesheet())
            self.export_btn.setEnabled(False)
            self.export_btn.clicked.connect(self._on_export)
            button_layout.addWidget(self.export_btn)
        
        button_layout.addStretch()
        
        # Right side actions
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet(get_secondary_button_stylesheet())
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.open_btn = QPushButton("Open" if self.mode == 'open' else "Save Here")
        self.open_btn.setStyleSheet(get_primary_button_stylesheet())
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.open_btn)
        
        layout.addLayout(button_layout)
    
    def _load_strategies(self):
        """Load strategies from database"""
        try:
            self.db = get_database_manager()
            
            # CRITICAL: Clear any previous failed transaction state
            self.db.strategy.session.rollback()

            # Get all strategies with latest version info
            strategies = self.db.strategy.get_all_strategies()

            self.all_strategies = []

            for strategy in strategies:
                try:
                    # Get latest version details
                    latest = self.db.strategy.get_latest_version(strategy['strategy_id'])

                    if latest:
                        # Get test results count (handle missing table gracefully)
                        try:
                            tests = self.db.test_results.get_version_test_results(latest['version_id'])
                            test_count = len(tests)
                        except Exception:
                            # Table doesn't exist yet or schema mismatch - no tests run yet
                            tests = []
                            test_count = 0

                        # Get best test result
                        best_perf = "N/A"
                        if tests:
                            best_test = max(tests, key=lambda t: t.get('sharpe_ratio', 0) or 0)
                            sharpe = best_test.get('sharpe_ratio')
                            if sharpe:
                                best_perf = f"Sharpe: {sharpe:.2f}"

                        # Extract strategy_type and blocks summary
                        strategy_type = "Unknown"
                        blocks_summary = ""
                        blocks_data = latest.get('blocks', [])
                        
                        if blocks_data and len(blocks_data) > 0:
                            # Build blocks summary: block_name [signals]
                            block_parts = []
                            for block in blocks_data[:3]:  # Limit to first 3 blocks
                                block_name = block.get('name', 'unknown')
                                signals = block.get('signals', [])
                                
                                # Get key signal names
                                signal_names = []
                                for signal in signals[:2]:  # Max 2 signals per block
                                    sig_name = signal.get('name', '') if isinstance(signal, dict) else str(signal)
                                    if sig_name:
                                        # Clean up signal name (remove common prefixes)
                                        clean_name = sig_name.replace('_', ' ').title()
                                        signal_names.append(clean_name)
                                
                                if signal_names:
                                    block_parts.append(f"{block_name} [{', '.join(signal_names)}]")
                                else:
                                    block_parts.append(block_name)
                            
                            if block_parts:
                                blocks_summary = " | ".join(block_parts)
                                if len(blocks_data) > 3:
                                    blocks_summary += f" + {len(blocks_data) - 3} more"
                        
                        # Detect strategy type from name
                        name_upper = latest['name'].upper()
                        if 'BULLISH' in name_upper:
                            strategy_type = "Bullish"
                        elif 'BEARISH' in name_upper:
                            strategy_type = "Bearish"
                        elif 'HOD' in name_upper or 'HIGH' in name_upper or 'RESISTANCE' in name_upper:
                            strategy_type = "Bearish"  # HOD rejection is bearish
                        elif 'LOD' in name_upper or 'LOW' in name_upper or 'SUPPORT' in name_upper:
                            strategy_type = "Bullish"  # LOD rejection is bullish
                        
                        # Build enriched display name with HTML color coding
                        display_name = latest['name']
                        if blocks_summary:
                            # Color-coded format for readability
                            # Strategy name: light grey (#CCCCCC) - readable on dark background
                            # Block names: cyan (#00BCD4)
                            # Signals: light green (#81C784)
                            # Separators: dim gray (#666666)
                            
                            # Parse blocks_summary and add colors
                            colored_blocks = []
                            for block_part in blocks_summary.split(' | '):
                                if '[' in block_part and ']' in block_part:
                                    # Has signals
                                    block_name, signals_part = block_part.split(' [', 1)
                                    signals = signals_part.rstrip(']')
                                    colored_blocks.append(
                                        f'<span style="color: #00BCD4;">{block_name}</span> '
                                        f'<span style="color: #666666;">[</span>'
                                        f'<span style="color: #81C784;">{signals}</span>'
                                        f'<span style="color: #666666;">]</span>'
                                    )
                                else:
                                    # No signals, just block name
                                    colored_blocks.append(f'<span style="color: #00BCD4;">{block_part}</span>')
                            
                            colored_summary = ' <span style="color: #666666;">|</span> '.join(colored_blocks)
                            display_name = f'<span style="color: #CCCCCC;">{latest["name"]}</span> <span style="color: #666666;">-</span> {colored_summary}'
                        
                        self.all_strategies.append({
                            'strategy_id': strategy['strategy_id'],
                            'version_id': latest['version_id'],
                            'name': latest['name'],
                            'display_name': display_name,  # Enriched name with blocks
                            'description': latest.get('description', ''),
                            'version_number': latest['version_number'],
                            'created_at': latest['created_at'],
                            'test_count': test_count,
                            'performance': best_perf,
                            'tags': latest.get('tags', []),
                            'strategy_type': strategy_type
                        })
                    
                except Exception as e:
                    # Skip strategies that fail to load (data corruption or missing versions)
                    # Rollback to clear failed state and continue with next strategy
                    self.db.strategy.session.rollback()
                    print(f"⚠️ Skipping strategy {strategy.get('strategy_id', 'unknown')}: {e}")
                    continue

            self._populate_table(self.all_strategies)

        except Exception as e:
            print(f"❌ Error loading strategies: {e}")
            self.all_strategies = []
    
    def _populate_table(self, strategies: List[Dict[str, Any]]):
        """Populate table with strategies"""
        self.table.setRowCount(0)
        
        for strategy in strategies:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Name - Use enriched display name with blocks (HTML formatted)
            display_name = strategy.get('display_name', strategy['name'])
            name_item = QTableWidgetItem()
            name_item.setData(Qt.ItemDataRole.DisplayRole, display_name) 
            name_item.setData(Qt.ItemDataRole.UserRole, strategy)
            # Enable HTML/rich text rendering
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 0, name_item)
            
            # Type - Show Bullish/Bearish from stored strategy_type (centered)
            strategy_type = strategy.get('strategy_type', 'Unknown')
            type_item = QTableWidgetItem(strategy_type)
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, type_item)
            
            # Version - Create dropdown with all versions
            version_combo = QComboBox()
            
            # Get all versions for this strategy
            all_versions = self.db.strategy.get_strategy_versions(strategy['strategy_id'])
            
            current_version_index = 0
            for i, ver in enumerate(all_versions):
                version_label = f"v{ver['version_number']}"
                version_combo.addItem(version_label, ver['version_id'])
                
                # Mark current version
                if ver['version_id'] == strategy['version_id']:
                    current_version_index = i
            
            # CRITICAL: Apply fix AFTER items added (same as filter dropdowns)
            fix_combobox_white_bars(version_combo)
            
            version_combo.setCurrentIndex(current_version_index)
            version_combo.currentIndexChanged.connect(
                lambda idx, r=row: self._on_table_version_changed(r, idx)
            )
            
            self.table.setCellWidget(row, 2, version_combo)
            
            # Last Modified (centered)
            created_at = strategy['created_at']
            if isinstance(created_at, datetime):
                time_str = created_at.strftime("%Y-%m-%d %H:%M")
            else:
                time_str = str(created_at)[:16]
            modified_item = QTableWidgetItem(time_str)
            modified_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, modified_item)
            
            # Tests (centered)
            tests_item = QTableWidgetItem(str(strategy['test_count']))
            tests_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, tests_item)
            
            # Performance (centered)
            perf_item = QTableWidgetItem(strategy['performance'])
            perf_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 5, perf_item)
        
        self._update_count_label(len(strategies))
    
    def _on_search_changed(self, text: str):
        """Handle search text change"""
        self._apply_filters()
    
    def _apply_filters(self):
        """Apply search and filters with multi-field search"""
        search_text = self.search_input.text().lower()
        type_filter = self.type_filter.currentText()
        
        filtered = []
        
        for strategy in self.all_strategies:
            # Multi-field search: name, description, type, date
            if search_text:
                # Search in name
                name_match = search_text in strategy['name'].lower()
                
                # Search in description
                desc_match = search_text in strategy.get('description', '').lower()
                
                # Search in strategy type (bullish/bearish)
                type_text = strategy.get('strategy_type', 'Unknown').lower()
                type_match = search_text in type_text
                
                # Search in date
                created_at = strategy['created_at']
                if isinstance(created_at, datetime):
                    date_str = created_at.strftime("%Y-%m-%d").lower()
                else:
                    date_str = str(created_at).lower()
                date_match = search_text in date_str
                
                # Search in blocks (if blocks data available)
                blocks_match = False
                # TODO: Could search in blocks data when we have access to it
                
                # If no match in any field, skip
                if not (name_match or desc_match or type_match or date_match or blocks_match):
                    continue
            
            # Apply type filter (Bullish/Bearish)
            if type_filter != "All":
                if type_filter != strategy.get('strategy_type', 'Unknown'):
                    continue
            
            filtered.append(strategy)
        
        self._populate_table(filtered)
    
    def _update_count_label(self, count: int):
        """Update strategy count label"""
        self.count_label.setText(f"{count} strateg{'y' if count == 1 else 'ies'}")
    
    def _populate_details_panel(self, version_id: str):
        """Populate details panel with strategy information from database"""
        try:
            # Get full version data from database
            version = self.db.strategy.get_strategy_version(version_id)
            if not version:
                return
            
            # Detect strategy type from version name
            name_upper = version['name'].upper()
            if 'BULLISH' in name_upper:
                strategy_type = "Bullish"
            elif 'BEARISH' in name_upper:
                strategy_type = "Bearish"
            elif 'HOD' in name_upper or 'HIGH' in name_upper or 'RESISTANCE' in name_upper:
                strategy_type = "Bearish"  # HOD rejection is bearish
            elif 'LOD' in name_upper or 'LOW' in name_upper or 'SUPPORT' in name_upper:
                strategy_type = "Bullish"  # LOD rejection is bullish
            else:
                strategy_type = "Unknown"
            
            # Column 1: Strategy Info
            type_badge = f"{'🟢' if strategy_type == 'Bullish' else '🔴'} {strategy_type}"
            self.detail_labels['name'].setText(f"{version['name']} ({type_badge})")
            
            desc = version.get('description', 'No description')
            self.detail_labels['description'].setText(desc if desc else 'No description')
            
            created = version['created_at']
            if isinstance(created, datetime):
                date_str = created.strftime("%Y-%m-%d %H:%M")
            else:
                date_str = str(created)[:16]
            
            tags = ', '.join(version.get('tags', [])) if version.get('tags') else 'None'
            meta_text = f"<b>Version:</b> v{version['version_number']}<br><b>Created:</b> {date_str}<br><b>Tags:</b> {tags}"
            self.detail_labels['meta'].setText(meta_text)
            
            # Column 2: Configuration
            blocks = version.get('blocks', [])
            block_count = len(blocks)
            
            # Count actual signals by looking inside blocks
            total_entry_signals = 0
            total_exit_signals = 0
            
            for block in blocks:
                signals = block.get('signals', [])
                for signal in signals:
                    if isinstance(signal, dict):
                        position = signal.get('position', 'entry')
                        if position == 'entry':
                            total_entry_signals += 1
                        elif position == 'exit':
                            total_exit_signals += 1
                        elif position == 'both':
                            total_entry_signals += 1
                            total_exit_signals += 1
            
            block_names = [b.get('name', 'unknown') for b in blocks[:5]]
            block_text = f"<b>{block_count} Building Blocks:</b><br>"
            block_text += "<br>".join([f"• {name}" for name in block_names])
            if block_count > 5:
                block_text += f"<br>• ... and {block_count - 5} more"
            self.detail_labels['blocks'].setText(block_text)
            
            # Signals summary with actual counts
            risk_mgmt = version.get('risk_management', {})
            
            sig_text = f"<b>Entry:</b> {total_entry_signals} signal{'s' if total_entry_signals != 1 else ''}<br>"
            sig_text += f"<b>Exit:</b> {total_exit_signals} signal{'s' if total_exit_signals != 1 else ''}<br>"
            sig_text += f"<b>Risk:</b> SL/TP configured" if risk_mgmt else "<b>Risk:</b> Not set"
            self.detail_labels['signals'].setText(sig_text)
            
            # Column 3: Performance & Metrics
            try:
                tests = self.db.test_results.get_version_test_results(version_id)
                test_count = len(tests)
                
                if tests:
                    # Get best test by Sharpe
                    best = max(tests, key=lambda t: t.get('sharpe_ratio', 0) or 0)
                    sharpe = best.get('sharpe_ratio', 0)
                    win_rate = best.get('win_rate', 0)
                    total_trades = best.get('total_trades', 0)
                    
                    # Calculate wins and losses
                    wins = int(total_trades * win_rate / 100) if total_trades > 0 else 0
                    losses = total_trades - wins
                    
                    # Show trade breakdown
                    test_text = f"<b>Trades:</b> {total_trades}<br>"
                    test_text += f"<b>Win:</b> {wins} | <b>Loss:</b> {losses}"
                    self.detail_labels['tests'].setText(test_text)
                    
                    perf_text = f"<b>Best Performance:</b><br>"
                    perf_text += f"• Sharpe: {sharpe:.2f}<br>"
                    perf_text += f"• Win Rate: {win_rate:.1f}%"
                    self.detail_labels['performance'].setText(perf_text)
                    
                    # Quality badge based on Sharpe
                    if sharpe > 1.5:
                        quality = "🟢 Excellent"
                    elif sharpe > 1.0:
                        quality = "🟡 Good"
                    elif sharpe > 0.5:
                        quality = "🟠 Fair"
                    else:
                        quality = "🔴 Poor"
                    self.detail_labels['status'].setText(f"<b>Quality:</b> {quality}")
                else:
                    self.detail_labels['tests'].setText(f"<b>Tests Run:</b> 0<br>⚠️ No backtest data")
                    self.detail_labels['performance'].setText("<b>Run backtest to see:</b><br>• Sharpe Ratio<br>• Win Rate<br>• Trade Stats")
                    self.detail_labels['status'].setText("<b>Quality:</b> 🔵 Untested")
                    
            except Exception as e:
                print(f"Error loading test results: {e}")
                self.detail_labels['tests'].setText(f"<b>Tests:</b> Error loading")
                self.detail_labels['performance'].setText("<b>Database error</b><br>Check logs for details")
                self.detail_labels['status'].setText("<b>Quality:</b> ⚠️ Error")
            
            # Show the panel
            self.details_frame.setVisible(True)
            
        except Exception as e:
            print(f"Error populating details: {e}")
            import traceback
            traceback.print_exc()
            self.details_frame.setVisible(False)
    
    def _on_selection_changed(self):
        """Handle table selection change"""
        selected = self.table.selectedItems()
        
        if selected:
            row = selected[0].row()
            name_item = self.table.item(row, 0)
            strategy_data = name_item.data(Qt.ItemDataRole.UserRole)
            
            self.selected_strategy_id = strategy_data['strategy_id']
            self.selected_version_id = strategy_data['version_id']
            
            # Populate details panel with selected strategy
            self._populate_details_panel(self.selected_version_id)
            
            self.open_btn.setEnabled(True)
            if self.mode == 'open':
                self.delete_btn.setEnabled(True)
                self.duplicate_btn.setEnabled(True)
                self.export_btn.setEnabled(True)
        else:
            self.selected_strategy_id = None
            self.selected_version_id = None
            self.details_frame.setVisible(False)
            self.open_btn.setEnabled(False)
            if self.mode == 'open':
                self.delete_btn.setEnabled(False)
                self.duplicate_btn.setEnabled(False)
                self.export_btn.setEnabled(False)
    
    def _on_double_click(self, item: QTableWidgetItem):
        """Handle double-click on table item"""
        self.accept()
    
    def _on_delete(self):
        """Handle delete button click"""
        if not self.selected_strategy_id:
            return
        
        # Show confirmation dialog
        from .alert_dialog import ask_question
        
        result = ask_question(
            self,
            "Delete Strategy",
            "Confirm Deletion",
            "Are you sure you want to delete this strategy and ALL its versions?\n\n"
            "This action cannot be undone.",
            icon="warning"
        )
        
        if result == 'yes':
            try:
                # Delete entire strategy and all versions
                deleted = self.db.strategy.delete_strategy(self.selected_strategy_id)
                
                if deleted:
                    # Reload strategies to refresh list
                    self._load_strategies()
                    
                    from .alert_dialog import show_success
                    show_success(self, "Delete Strategy", "Success", "Strategy deleted successfully")
                else:
                    from .alert_dialog import show_error
                    show_error(self, "Delete Strategy", "Error", "Strategy not found")
                
            except Exception as e:
                from .alert_dialog import show_error
                show_error(self, "Delete Strategy", "Error", f"Failed to delete strategy:\n{e}")
    
    def _on_duplicate(self):
        """Handle duplicate button click"""
        if not self.selected_version_id:
            return
        
        try:
            # Get current version
            version = self.db.strategy.get_strategy_version(self.selected_version_id)
            
            if version:
                # Create new strategy with duplicated data
                new_strategy_id = self.db.strategy.create_strategy(f"{version['name']} (Copy)")
                
                # Create new version with same config
                version_data = {
                    'strategy_id': new_strategy_id,
                    'name': f"{version['name']} (Copy)",
                    'description': version.get('description', ''),
                    'blocks': version['blocks'],
                    'signals': version['signals'],
                    'parameters': version['parameters'],
                    'entry_conditions': version['entry_conditions'],
                    'exit_conditions': version['exit_conditions'],
                    'risk_management': version['risk_management'],
                    'backtest_config': version['backtest_config'],
                    'tags': version.get('tags', [])
                }
                
                self.db.strategy.create_strategy_version(version_data)
                
                # Reload strategies
                self._load_strategies()
                
                from .alert_dialog import show_success
                show_success(self, "Duplicate Strategy", "Success", "Strategy duplicated successfully")
                
        except Exception as e:
            from .alert_dialog import show_error
            show_error(self, "Duplicate Strategy", "Error", f"Failed to duplicate strategy:\n{e}")
    
    def _on_export(self):
        """Handle export to JSON button click"""
        if not self.selected_version_id:
            return
        
        try:
            from PyQt5.QtWidgets import QFileDialog
            
            # Get strategy version
            version = self.db.strategy.get_strategy_version(self.selected_version_id)
            
            if not version:
                from .alert_dialog import show_error
                show_error(self, "Export Failed", "Error", "Strategy version not found")
                return
            
            # Get save filename
            settings = QSettings("BTC_Engine", "StrategyBuilder")
            last_dir = settings.value("lastDirectory", "")
            
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export Strategy to JSON",
                f"{last_dir}/{version['name']}.json",
                "Strategy Files (*.json);;All Files (*)"
            )
            
            if not filename:
                return  # User cancelled
            
            # Prepare export data (convert from persistence format to file format)
            from src.strategy_builder.integration.strategy_builder_orchestrator import StrategyBuilderOrchestrator
            
            # Create temporary orchestrator for export
            orch = StrategyBuilderOrchestrator()
            
            # Build config dict for export
            export_dict = {
                'name': version['name'],
                'description': version.get('description', ''),
                'blocks': version['blocks']
            }
            
            # Use persistence to convert to full config then back to file format
            config = orch.persistence._dict_to_config(export_dict)
            
            # Now save using orchestrator's save method
            result = orch.save_strategy(filename)
            
            if result.success:
                from .alert_dialog import show_success
                show_success(
                    self,
                    "Export Successful",
                    "Success",
                    f"Strategy exported to:\n{filename}"
                )
            else:
                from .alert_dialog import show_error
                show_error(self, "Export Failed", "Error", f"Failed to export:\n{result.message}")
                
        except Exception as e:
            from .alert_dialog import show_error
            show_error(self, "Export Failed", "Error", f"Error exporting strategy:\n{e}")
            import traceback
            traceback.print_exc()
    
    def _on_table_version_changed(self, row: int, index: int):
        """Handle version dropdown change in table"""
        if index < 0:
            return
        
        # Get the combo box from the table
        version_combo = self.table.cellWidget(row, 2)
        if not version_combo:
            return
        
        # Get the version_id from combo box
        version_id = version_combo.itemData(index)
        
        if version_id:
            # Update the selected version_id for this row
            name_item = self.table.item(row, 0)
            if name_item:
                strategy_data = name_item.data(Qt.ItemDataRole.UserRole)
                strategy_data['version_id'] = version_id
                name_item.setData(Qt.ItemDataRole.UserRole, strategy_data)
                
                # If this row is selected, update the selected_version_id AND refresh panel
                if row == self.table.currentRow():
                    self.selected_version_id = version_id
                    # Refresh details panel with new version
                    self._populate_details_panel(version_id)
    
    def _on_version_changed(self, index: int):
        """Handle version selector change"""
        if index < 0:
            return
        
        # Get version_id from combo box data
        version_id = self.version_selector.itemData(index)
        
        if version_id:
            self.selected_version_id = version_id
            # Could update table row to show selected version details
    
    def get_selected_strategy(self) -> tuple[Optional[str], Optional[str]]:
        """
        Get selected strategy and version IDs
        
        Returns:
            Tuple of (strategy_id, version_id) or (None, None)
        """
        return (self.selected_strategy_id, self.selected_version_id)
    
    def accept(self):
        """Handle accept - emit signal and close"""
        if self.selected_strategy_id and self.selected_version_id:
            # Convert version_id to string (may be UUID from database)
            self.strategy_selected.emit(
                str(self.selected_strategy_id), 
                str(self.selected_version_id)
            )
        self._save_settings()
        self.close()
    
    def reject(self):
        """Handle reject - just close"""
        self._save_settings()
        self.close()
    
    def _restore_settings(self):
        """Restore window geometry and state"""
        settings = QSettings("BTC_Engine", "StrategyBuilder")
        
        # Restore geometry
        geometry = settings.value("strategyBrowser/geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            # Default size if no saved geometry
            self.resize(1200, 800)
        
        # Restore window state
        window_state = settings.value("strategyBrowser/windowState")
        if window_state:
            self.restoreState(window_state)
    
    def _save_settings(self):
        """Save window geometry and state"""
        settings = QSettings("BTC_Engine", "StrategyBuilder")
        settings.setValue("strategyBrowser/geometry", self.saveGeometry())
        settings.setValue("strategyBrowser/windowState", self.saveState())
    
    def closeEvent(self, event):
        """Handle window close"""
        self._save_settings()
        if self.db:
            self.db.close()
        super().closeEvent(event)
