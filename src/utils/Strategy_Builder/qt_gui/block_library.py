"""
Strategy Builder - Block Library Panel

Tree view of available building blocks organized by category.

Author: Strategy Builder v3.0
Date: 2026-01-10
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QTreeWidget,
    QTreeWidgetItem, QLabel, QTextEdit, QSplitter
)
from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtGui import QDrag

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from src.utils.Strategy_Builder import RegistryBridge


class BlockLibraryPanel(QWidget):
    """Panel displaying available building blocks in a tree view"""
    
    def __init__(self, parent=None, orientation='horizontal'):
        """
        Initialize block library panel
        
        Args:
            parent: Parent widget
            orientation: 'horizontal' or 'vertical' splitter orientation
        """
        super().__init__(parent)
        
        # Initialize registry bridge
        self.registry = RegistryBridge()
        
        # Store orientation
        self.orientation = orientation
        
        # Setup UI
        self.init_ui()
        self.load_blocks()
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Search bar with count
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)  # Add spacing between search box and label
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Search blocks...")
        self.search_box.textChanged.connect(self.filter_blocks)
        search_layout.addWidget(self.search_box)
        
        self.info_label = QLabel("80 blocks")
        self.info_label.setStyleSheet("font-size: 8pt; color: #888; padding-left: 3px; padding-right: 8px;")
        search_layout.addWidget(self.info_label)
        
        layout.addLayout(search_layout, 0)  # 0 stretch = minimum height
        
        # Splitter for tree and details (configurable orientation)
        if self.orientation == 'vertical':
            splitter = QSplitter(Qt.Orientation.Horizontal)  # Side-by-side
        else:
            splitter = QSplitter(Qt.Orientation.Vertical)  # Top-bottom (default)
        
        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Block Name", "Category"])
        self.tree.setColumnWidth(0, 250)
        self.tree.setDragEnabled(True)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.tree.itemSelectionChanged.connect(self.on_block_selected)
        splitter.addWidget(self.tree)
        
        # Details panel
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setPlaceholderText(
            "Select a block to view details...\n\n"
            "• What the block does\n"
            "• Signals it returns\n"
            "• Usage examples"
        )
        splitter.addWidget(self.details_text)
        
        # Set initial sizes based on orientation
        if self.orientation == 'vertical':
            # For vertical orientation: 50/50 side-by-side
            splitter.setSizes([500, 500])
        else:
            # For horizontal orientation: 60/40 top-bottom
            splitter.setSizes([600, 400])
        
        layout.addWidget(splitter, 1)  # 1 stretch = take all remaining space!
        
    def load_blocks(self):
        """Load building blocks from registry"""
        self.tree.clear()
        
        # Get blocks by category (already grouped)
        blocks_by_category = self.registry.get_blocks_by_category()
        
        # Add to tree
        total_blocks = 0
        for category, blocks in sorted(blocks_by_category.items()):
            # Create category item
            category_item = QTreeWidgetItem([category, ""])
            category_item.setFlags(category_item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled)
            self.tree.addTopLevelItem(category_item)
            
            # Add blocks
            for block in sorted(blocks, key=lambda b: b.name):
                block_item = QTreeWidgetItem([block.name, category])
                block_item.setData(0, Qt.ItemDataRole.UserRole, block)
                category_item.addChild(block_item)
            
            # Expand category
            category_item.setExpanded(True)
            total_blocks += len(blocks)
        
        # Update count
        self.info_label.setText(f"{total_blocks} blocks available")
        
    def filter_blocks(self, text):
        """Filter blocks based on search text"""
        if not text:
            # Show all
            for i in range(self.tree.topLevelItemCount()):
                category_item = self.tree.topLevelItem(i)
                category_item.setHidden(False)
                for j in range(category_item.childCount()):
                    category_item.child(j).setHidden(False)
            return
        
        text = text.lower()
        visible_count = 0
        
        # Filter
        for i in range(self.tree.topLevelItemCount()):
            category_item = self.tree.topLevelItem(i)
            category_visible = False
            
            for j in range(category_item.childCount()):
                block_item = category_item.child(j)
                block_name = block_item.text(0).lower()
                
                if text in block_name:
                    block_item.setHidden(False)
                    category_visible = True
                    visible_count += 1
                else:
                    block_item.setHidden(True)
            
            category_item.setHidden(not category_visible)
        
        # Update count
        self.info_label.setText(f"{visible_count} blocks found")
    
    def on_block_selected(self):
        """Display details when a block is selected"""
        selected_items = self.tree.selectedItems()
        if not selected_items:
            self.details_text.clear()
            return
        
        item = selected_items[0]
        
        # Skip category items
        if item.parent() is None:
            self.details_text.clear()
            return
        
        # Get block data
        block = item.data(0, Qt.ItemDataRole.UserRole)
        if not block:
            return
        
        # Build details text
        details = f"""<h3 style='color: #4ec9b0;'>{block.display_name}</h3>

<p style='color: #ce9178;'><b>Category:</b> {block.category}</p>
<p style='color: #ce9178;'><b>Type:</b> {block.block_type}</p>
<p style='color: #ce9178;'><b>Default Weight:</b> {block.default_weight} points</p>

<h4 style='color: #569cd6;'>Description</h4>
<p style='color: #d4d4d4;'>{block.description}</p>

<h4 style='color: #569cd6;'>Returns (Signals)</h4>
<ul style='color: #d4d4d4;'>
"""
        
        # Add signals
        if block.signals:
            for signal in block.signals:
                details += f"<li><b>{signal}</b></li>\n"
        else:
            details += "<li><i>No specific signals (context block)</i></li>\n"
        
        details += "</ul>\n"
        
        # Add usage tip
        details += f"""
<h4 style='color: #569cd6;'>Usage Tip</h4>
<p style='color: #d4d4d4;'><i>This is a reference library for browsing blocks. To add blocks to your strategy, open the Strategy Editor and use the "Available Blocks" section there.</i></p>
"""
        
        self.details_text.setHtml(details)
