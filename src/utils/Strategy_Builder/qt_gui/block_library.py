"""
Strategy Builder - Block Library Panel

Tree view of available building blocks organized by category.

Author: Strategy Builder v3.0
Date: 2026-01-10
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QTreeWidget,
    QTreeWidgetItem, QLabel
)
from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtGui import QDrag

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from src.utils.Strategy_Builder import RegistryBridge


class BlockLibraryPanel(QWidget):
    """Panel displaying available building blocks in a tree view"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize registry bridge
        self.registry = RegistryBridge()
        
        # Setup UI
        self.init_ui()
        self.load_blocks()
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Title
        title = QLabel("📚 Building Blocks Library")
        title.setStyleSheet("font-size: 11pt; font-weight: bold; color: #ffffff;")
        layout.addWidget(title)
        
        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Search blocks...")
        self.search_box.textChanged.connect(self.filter_blocks)
        layout.addWidget(self.search_box)
        
        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Block Name", "Category"])
        self.tree.setColumnWidth(0, 250)
        self.tree.setDragEnabled(True)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.tree)
        
        # Info label
        self.info_label = QLabel("80 blocks available")
        self.info_label.setStyleSheet("font-size: 9pt; color: #888;")
        layout.addWidget(self.info_label)
        
    def load_blocks(self):
        """Load building blocks from registry"""
        self.tree.clear()
        
        # Get all blocks
        all_blocks = self.registry.list_all_blocks()
        
        # Group by category
        categories = {}
        for block in all_blocks:
            category = block.category
            if category not in categories:
                categories[category] = []
            categories[category].append(block)
        
        # Add to tree
        for category, blocks in sorted(categories.items()):
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
        
        # Update count
        total = len(all_blocks)
        self.info_label.setText(f"{total} blocks available")
        
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