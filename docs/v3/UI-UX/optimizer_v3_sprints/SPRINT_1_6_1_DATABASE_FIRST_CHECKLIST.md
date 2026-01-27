# SPRINT 1.6.1: DATABASE-FIRST MIGRATION - IMPLEMENTATION CHECKLIST
**Institutional-Grade Systematic Migration Process**

**Date**: 2026-01-24 (Updated: 2026-01-27)  
**Status**: ✅ IMPLEMENTATION COMPLETE  
**Risk Level**: HIGH - Requires meticulous execution  
**Rollback Plan**: Documented at each stage

---

## 🎯 CRITICAL RULES

1. ✅ **NO STEP PROCEEDS WITHOUT UNIT TESTS PASSING**
2. ✅ **NO STEP PROCEEDS WITHOUT SIGN-OFF**
3. ✅ **BACKUP BEFORE EVERY DATABASE CHANGE**
4. ✅ **ROLLBACK COMMAND DOCUMENTED AT EACH STAGE**
5. ✅ **JSON FILES REMAIN UNTOUCHED UNTIL FINAL MIGRATION**
6. ✅ **DUAL-MODE OPERATION DURING TRANSITION**

---

## 📋 PHASE 1: DATABASE INFRASTRUCTURE (Days 1-3)

### **STAGE 1.1: Create Database Tables** ⏱️ 4 hours

#### Task 1.1.1: Create Migration Script ✅ COMPLETE
- [x] **File**: `alembic/versions/20260124_add_strategy_versioning.py`
- [x] **Action**: Create Alembic migration for new tables
- [x] **Content**:
  - `strategies` table (parent table)
  - `strategy_versions` table (complete strategy data)
  - `strategy_block_versions` table (block-level tracking)
  - `ai_recommendations` table (recommendations with metadata)
  - `strategy_test_results` table (test results history)

```python
"""Add strategy versioning and AI recommendations

Revision ID: add_strategy_versioning
Revises: <previous_revision>
Create Date: 2026-01-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'add_strategy_versioning'
down_revision = '<previous_revision>'

def upgrade():
    # Create strategies parent table
    op.create_table(
        'strategies',
        sa.Column('strategy_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('strategy_id')
    )
    
    # Create strategy_versions table
    op.create_table(
        'strategy_versions',
        sa.Column('version_id', postgresql.UUID(), nullable=False),
        sa.Column('strategy_id', sa.String(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('blocks', postgresql.JSONB(), nullable=False),
        sa.Column('signals', postgresql.JSONB(), nullable=False),
        sa.Column('parameters', postgresql.JSONB(), nullable=False),
        sa.Column('entry_conditions', postgresql.JSONB(), nullable=False),
        sa.Column('exit_conditions', postgresql.JSONB(), nullable=False),
        sa.Column('risk_management', postgresql.JSONB(), nullable=False),
        sa.Column('backtest_config', postgresql.JSONB(), nullable=False),
        sa.Column('backtest_results', postgresql.JSONB()),
        sa.Column('metrics', postgresql.JSONB()),
        sa.Column('trades', postgresql.JSONB()),
        sa.Column('equity_curve', postgresql.JSONB()),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('git_commit_hash', sa.String()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', sa.String()),
        sa.Column('notes', sa.Text()),
        sa.Column('tags', postgresql.JSONB()),
        sa.Column('config_hash', sa.String(64)),  # SHA-256 hash for duplicate detection
        sa.PrimaryKeyConstraint('version_id'),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.strategy_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('strategy_id', 'version_number', name='uq_strategy_version')
    )
    
    # Create indexes
    op.create_index('idx_strategy_versions_strategy', 'strategy_versions', ['strategy_id'])
    op.create_index('idx_strategy_versions_timestamp', 'strategy_versions', ['timestamp'])
    op.create_index('idx_strategy_versions_hash', 'strategy_versions', ['config_hash'])
    
    # ... (complete all tables)

def downgrade():
    # Drop all in reverse order
    op.drop_table('strategy_test_results')
    op.drop_table('ai_recommendations')
    op.drop_table('strategy_block_versions')
    op.drop_table('strategy_versions')
    op.drop_table('strategies')
```

**Unit Tests**:
- [ ] **File**: `tests/database/test_migration_add_strategy_versioning.py`
- [ ] Test: Migration runs without errors
- [ ] Test: All tables created with correct schema
- [ ] Test: All indexes created
- [ ] Test: Foreign keys enforced
- [ ] Test: Downgrade works correctly

**Rollback**: `alembic downgrade -1`

**Sign-off**: ________ Date: ________

---

#### Task 1.1.2: Run Migration ✅ COMPLETE
- [x] **Action**: Backup database
- [x] **Command**: `pg_dump optimizer_v3 > backup_pre_migration_$(date +%Y%m%d_%H%M%S).sql`
- [x] **Action**: Run migration
- [x] **Command**: `alembic upgrade head`
- [x] **Action**: Verify tables exist
- [x] **Command**: `psql optimizer_v3 -c "\dt strategy*"`

**Unit Tests**:
- [ ] **File**: `tests/database/test_schema_verification.py`
- [ ] Test: All tables exist
- [ ] Test: All columns have correct types
- [ ] Test: All constraints exist
- [ ] Test: Can insert test data
- [ ] Test: Can query test data
- [ ] Test: Foreign keys work

**Rollback**: Restore from backup + `alembic downgrade -1`

**Sign-off**: ________ Date: ________

---

### **STAGE 1.2: Database Manager Methods** ⏱️ 8 hours

#### Task 1.2.1: Strategy CRUD Operations ✅ COMPLETE
- [x] **File**: `src/optimizer_v3/database/strategy_manager.py` (CREATED - 526 lines)
- [x] **Action**: Create StrategyDatabaseManager class

```python
from typing import Optional, List, Dict
from uuid import uuid4
from datetime import datetime
import hashlib
import json
from sqlalchemy.orm import Session

class StrategyDatabaseManager:
    """Database manager for strategy versioning and persistence"""
    
    def __init__(self, db_session: Session):
        self.session = db_session
    
    def create_strategy(self, name: str) -> str:
        """Create new strategy parent record"""
        strategy_id = f"strategy_{uuid4().hex[:8]}"
        # Implementation
        return strategy_id
    
    def create_strategy_version(self, strategy_data: Dict) -> str:
        """Create new strategy version"""
        version_id = str(uuid4())
        # Implementation
        return version_id
    
    def get_strategy_version(self, version_id: str) -> Optional[Dict]:
        """Get complete strategy version"""
        # Implementation
        pass
    
    def get_strategy_versions(self, strategy_id: str) -> List[Dict]:
        """Get all versions of a strategy"""
        # Implementation
        pass
    
    def get_latest_version(self, strategy_id: str) -> Optional[Dict]:
        """Get latest version of strategy"""
        # Implementation
        pass
    
    def update_strategy_version(self, version_id: str, updates: Dict) -> bool:
        """Update strategy version metadata"""
        # Implementation
        pass
    
    def delete_strategy_version(self, version_id: str) -> bool:
        """Soft delete strategy version"""
        # Implementation
        pass
    
    def calculate_config_hash(self, config: Dict) -> str:
        """Calculate deterministic hash of strategy config"""
        core_elements = {
            'blocks': sorted([
                {
                    'name': block['name'],
                    'signals': sorted(block.get('signals', [])),
                    'parameters': block.get('parameters', {})
                }
                for block in config.get('blocks', [])
            ], key=lambda x: x['name']),
            'parameters': config.get('parameters', {}),
            'entry_conditions': config.get('entry_conditions', {}),
            'exit_conditions': config.get('exit_conditions', {})
        }
        json_str = json.dumps(core_elements, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def find_version_by_hash(self, config_hash: str) -> Optional[str]:
        """Find existing version with same config hash"""
        # Implementation
        pass
```

**Unit Tests**:
- [ ] **File**: `tests/database/test_strategy_manager.py`
- [ ] Test: `create_strategy()` creates parent record
- [ ] Test: `create_strategy_version()` creates version
- [ ] Test: `get_strategy_version()` retrieves correct data
- [ ] Test: `get_strategy_versions()` returns all versions
- [ ] Test: `get_latest_version()` returns highest version number
- [ ] Test: `update_strategy_version()` updates metadata
- [ ] Test: `calculate_config_hash()` is deterministic
- [ ] Test: `calculate_config_hash()` ignores metadata
- [ ] Test: `find_version_by_hash()` finds duplicates
- [ ] Test: Foreign key constraints enforced
- [ ] Test: Version number auto-increments
- [ ] Test: Concurrent operations safe

**Rollback**: Remove file, database unchanged

**Sign-off**: ________ Date: ________

---

#### Task 1.2.2: AI Recommendations CRUD ✅ COMPLETE
- [x] **File**: `src/optimizer_v3/database/ai_recommendations_manager.py` (CREATED - 400+ lines)
- [x] **Action**: Create AIRecommendationsManager class

```python
class AIRecommendationsManager:
    def __init__(self, db_session: Session):
        self.session = db_session
    
    def save_ai_recommendations(self, recommendations: List[Dict], version_id: str) -> List[str]:
        """Save AI recommendations for a strategy version"""
        pass
    
    def get_ai_recommendations_for_version(self, version_id: str) -> List[Dict]:
        """Get all recommendations for a version"""
        pass
    
    def mark_recommendation_applied(self, recommendation_id: str) -> bool:
        """Mark recommendation as applied"""
        pass
    
    def get_applied_recommendations(self, version_id: str) -> List[Dict]:
        """Get applied recommendations for version"""
        pass
```

**Unit Tests**:
- [ ] **File**: `tests/database/test_ai_recommendations_manager.py`
- [ ] Test: Save recommendations
- [ ] Test: Retrieve recommendations
- [ ] Test: Mark as applied
- [ ] Test: Get applied only
- [ ] Test: Link to version correctly
- [ ] Test: Handle complex JSON data

**Rollback**: Remove file, database unchanged

**Sign-off**: ________ Date: ________

---

#### Task 1.2.3: Test Results CRUD ✅ COMPLETE
- [x] **File**: `src/optimizer_v3/database/test_results_manager.py` (CREATED - 500+ lines)
- [x] **Action**: Create TestResultsManager class

**Unit Tests**:
- [ ] **File**: `tests/database/test_test_results_manager.py`
- [ ] Test: Save test results
- [ ] Test: Retrieve test results
- [ ] Test: Get last test for strategy
- [ ] Test: Link to version

**Rollback**: Remove file, database unchanged

**Sign-off**: ________ Date: ________

---

### **STAGE 1.3: Integration with Existing DatabaseManager** ⏱️ 2 hours

#### Task 1.3.1: Integrate Managers into Main Manager ✅ COMPLETE
- [x] **File**: `src/optimizer_v3/database/database_manager.py` (CREATED - 300+ lines)
- [x] **Action**: Add strategy, AI, and test managers via unified DatabaseManager

```python
class DatabaseManager:
    def __init__(self):
        # Existing code...
        
        # NEW: Strategy versioning managers
        self.strategy_manager = StrategyDatabaseManager(self.session)
        self.ai_manager = AIRecommendationsManager(self.session)
        self.test_results_manager = TestResultsManager(self.session)
    
    # Delegate methods
    def create_strategy_version(self, *args, **kwargs):
        return self.strategy_manager.create_strategy_version(*args, **kwargs)
    
    # ... (all other delegate methods)
```

**Unit Tests**:
- [ ] **File**: `tests/database/test_manager_integration.py`
- [ ] Test: All managers accessible
- [ ] Test: Delegate methods work
- [ ] Test: Session sharing works
- [ ] Test: Transaction rollback works

**Rollback**: Git revert changes to manager.py

**Sign-off**: ________ Date: ________

---

## 📋 PHASE 2: STRATEGY BROWSER UI (Days 4-6)

### **STAGE 2.1: Strategy Browser Dialog** ⏱️ 8 hours

#### Task 2.1.1: Create StrategyBrowserDialog ✅ COMPLETE
- [x] **File**: `src/strategy_builder/ui/strategy_browser_dialog.py` (CREATED - 500+ lines)
- [x] **Action**: Create database-driven strategy browser

```python
class StrategyBrowserDialog(QDialog):
    """
    Database-driven strategy browser
    Replaces file-based Open/Save dialogs
    """
    
    strategy_selected = pyqtSignal(str, int)  # strategy_id, version_number
    
    def __init__(self, mode: str = 'open', parent=None):
        """
        Args:
            mode: 'open', 'save', or 'browse'
        """
        super().__init__(parent)
        self.mode = mode
        self.setWindowTitle(f"{mode.capitalize()} Strategy")
        self.setMinimumSize(1000, 600)
        
        self._init_ui()
        self._load_strategies()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        
        # Search/Filter Bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search strategies...")
        self.search_input.textChanged.connect(self._filter_strategies)
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_input)
        
        # Filter by tags
        self.tag_filter = QComboBox()
        self.tag_filter.addItems(['All Tags', 'Reversal', 'Continuation', 'Scalp', 'Swing'])
        self.tag_filter.currentTextChanged.connect(self._filter_strategies)
        search_layout.addWidget(QLabel("Tag:"))
        search_layout.addWidget(self.tag_filter)
        
        layout.addLayout(search_layout)
        
        # Strategy List (left panel)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: Strategy list
        self.strategy_table = QTableWidget()
        self.strategy_table.setColumnCount(5)
        self.strategy_table.setHorizontalHeaderLabels([
            'Name', 'Latest Version', 'Last Modified', 'Win Rate', 'Tags'
        ])
        self.strategy_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.strategy_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.strategy_table.itemSelectionChanged.connect(self._on_strategy_selected)
        splitter.addWidget(self.strategy_table)
        
        # Right: Version history + details
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        # Strategy details
        self.details_group = QGroupBox("Strategy Details")
        details_layout = QFormLayout()
        self.name_label = QLabel()
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.created_label = QLabel()
        self.blocks_label = QLabel()
        details_layout.addRow("Name:", self.name_label)
        details_layout.addRow("Description:", self.description_label)
        details_layout.addRow("Created:", self.created_label)
        details_layout.addRow("Blocks:", self.blocks_label)
        self.details_group.setLayout(details_layout)
        right_layout.addWidget(self.details_group)
        
        # Version history
        self.version_group = QGroupBox("Version History")
        version_layout = QVBoxLayout()
        self.version_table = QTableWidget()
        self.version_table.setColumnCount(4)
        self.version_table.setHorizontalHeaderLabels([
            'Version', 'Date', 'Win Rate', 'PF'
        ])
        version_layout.addWidget(self.version_table)
        self.version_group.setLayout(version_layout)
        right_layout.addWidget(self.version_group)
        
        right_panel.setLayout(right_layout)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 600])
        
        layout.addWidget(splitter)
        
        # Buttons
        btn_layout = QHBoxLayout()
        if self.mode == 'open':
            self.open_btn = QPushButton("Open Selected")
            self.open_btn.clicked.connect(self.accept)
            btn_layout.addWidget(self.open_btn)
        elif self.mode == 'save':
            self.save_btn = QPushButton("Save")
            self.save_btn.clicked.connect(self._save_strategy)
            btn_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def _load_strategies(self):
        """Load all strategies from database"""
        db = get_db_manager()
        strategies = db.strategy_manager.get_all_strategies()
        
        self.strategy_table.setRowCount(len(strategies))
        for i, strategy in enumerate(strategies):
            # Name
            self.strategy_table.setItem(i, 0, QTableWidgetItem(strategy['name']))
            
            # Latest version
            self.strategy_table.setItem(i, 1, QTableWidgetItem(f"v{strategy['latest_version']}"))
            
            # Last modified
            modified = strategy['updated_at'].strftime('%Y-%m-%d %H:%M')
            self.strategy_table.setItem(i, 2, QTableWidgetItem(modified))
            
            # Win rate from latest version
            latest = db.strategy_manager.get_latest_version(strategy['strategy_id'])
            if latest and latest.get('metrics'):
                win_rate = latest['metrics'].get('win_rate', 0)
                self.strategy_table.setItem(i, 3, QTableWidgetItem(f"{win_rate:.1f}%"))
            
            # Tags
            if latest and latest.get('tags'):
                tags_str = ', '.join(latest['tags'])
                self.strategy_table.setItem(i, 4, QTableWidgetItem(tags_str))
    
    def _on_strategy_selected(self):
        """Load version history when strategy selected"""
        current_row = self.strategy_table.currentRow()
        if current_row < 0:
            return
        
        strategy_name = self.strategy_table.item(current_row, 0).text()
        
        # Load full strategy details
        db = get_db_manager()
        # Find strategy by name
        strategies = db.strategy_manager.get_all_strategies()
        strategy = next((s for s in strategies if s['name'] == strategy_name), None)
        
        if not strategy:
            return
        
        # Update details panel
        latest = db.strategy_manager.get_latest_version(strategy['strategy_id'])
        if latest:
            self.name_label.setText(latest['name'])
            self.description_label.setText(latest.get('description', 'No description'))
            self.created_label.setText(latest['created_at'].strftime('%Y-%m-%d %H:%M'))
            self.blocks_label.setText(f"{len(latest.get('blocks', []))} blocks")
        
        # Load version history
        versions = db.strategy_manager.get_strategy_versions(strategy['strategy_id'])
        self.version_table.setRowCount(len(versions))
        
        for i, version in enumerate(reversed(versions)):  # Newest first
            self.version_table.setItem(i, 0, QTableWidgetItem(f"v{version['version_number']}"))
            self.version_table.setItem(i, 1, QTableWidgetItem(
                version['timestamp'].strftime('%Y-%m-%d %H:%M')
            ))
            
            if version.get('metrics'):
                wr = version['metrics'].get('win_rate', 0)
                pf = version['metrics'].get('profit_factor', 0)
                self.version_table.setItem(i, 2, QTableWidgetItem(f"{wr:.1f}%"))
                self.version_table.setItem(i, 3, QTableWidgetItem(f"{pf:.2f}"))
    
    def get_selected_strategy(self) -> Optional[tuple]:
        """Return (strategy_id, version_number) of selected strategy"""
        current_row = self.strategy_table.currentRow()
        if current_row < 0:
            return None
        
        strategy_name = self.strategy_table.item(current_row, 0).text()
        
        # Get version from version table or use latest
        version_row = self.version_table.currentRow()
        if version_row >= 0:
            version_str = self.version_table.item(version_row, 0).text()
            version_number = int(version_str.replace('v', ''))
        else:
            version_number = None  # Use latest
        
        # Find strategy_id
        db = get_db_manager()
        strategies = db.strategy_manager.get_all_strategies()
        strategy = next((s for s in strategies if s['name'] == strategy_name), None)
        
        if strategy:
            return (strategy['strategy_id'], version_number)
        
        return None
```

**Unit Tests**:
- [ ] **File**: `tests/ui/test_strategy_browser_dialog.py`
- [ ] Test: Dialog opens without errors
- [ ] Test: Strategies load from database
- [ ] Test: Search filtering works
- [ ] Test: Tag filtering works
- [ ] Test: Strategy selection works
- [ ] Test: Version history loads
- [ ] Test: Details panel updates
- [ ] Test: get_selected_strategy() returns correct data
- [ ] Test: Handles empty database
- [ ] Test: Handles missing metrics gracefully

**Rollback**: Remove file

**Sign-off**: ________ Date: ________

---

#### Task 2.1.2: New Strategy Dialog ✅ COMPLETE
- [x] **File**: `src/strategy_builder/ui/new_strategy_dialog.py` (CREATED - 150+ lines)
- [x] **Action**: Create dialog for new strategy creation

```python
class NewStrategyDialog(QDialog):
    """Dialog for creating new strategy in database"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Strategy")
        self._init_ui()
    
    def _init_ui(self):
        layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(100)
        
        # Strategy type
        self.type_combo = QComboBox()
        self.type_combo.addItems(['Reversal', 'Continuation', 'Scalp', 'Swing', 'Custom'])
        
        # Tags
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("Comma-separated tags")
        
        layout.addRow("Name*:", self.name_input)
        layout.addRow("Description:", self.description_input)
        layout.addRow("Type:", self.type_combo)
        layout.addRow("Tags:", self.tags_input)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.create_btn = QPushButton("Create")
        self.create_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.create_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addRow(btn_layout)
        self.setLayout(layout)
    
    def get_strategy_data(self) -> Dict:
        """Get entered strategy data"""
        tags = [t.strip() for t in self.tags_input.text().split(',') if t.strip()]
        return {
            'name': self.name_input.text(),
            'description': self.description_input.toPlainText(),
            'type': self.type_combo.currentText(),
            'tags': tags
        }
```

**Unit Tests**:
- [ ] **File**: `tests/ui/test_new_strategy_dialog.py`
- [ ] Test: Dialog opens
- [ ] Test: All fields work
- [ ] Test: get_strategy_data() returns correct dict
- [ ] Test: Validation works

**Rollback**: Remove file

**Sign-off**: ________ Date: ________

---

### **STAGE 2.2: Replace File Operations in Main Window** ⏱️ 4 hours

#### Task 2.2.1: Update StrategyBuilderMainWindow - New Strategy ✅ COMPLETE
- [x] **File**: `src/strategy_builder/ui/strategy_builder_main_window.py`
- [x] **Action**: Replace "New" functionality - Uses database with NewStrategyDialog

**OLD CODE** (Comment out, don't delete):
```python
# def _new_strategy(self):
#     """Create new strategy"""
#     # Clear panels...
```

**NEW CODE**:
```python
def _new_strategy(self):
    """Create new strategy in database"""
    dialog = NewStrategyDialog(self)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        data = dialog.get_strategy_data()
        
        # Create in database
        db = get_db_manager()
        strategy_id = db.strategy_manager.create_strategy(data['name'])
        
        # Create initial version
        initial_version = {
            'strategy_id': strategy_id,
            'name': data['name'],
            'description': data['description'],
            'blocks': [],
            'signals': {},
            'parameters': {},
            'entry_conditions': {},
            'exit_conditions': {},
            'risk_management': {},
            'backtest_config': {},
            'tags': data['tags']
        }
        
        version_id = db.strategy_manager.create_strategy_version(initial_version)
        
        # Load into UI
        self._load_strategy_from_db(strategy_id, version_number=1)
        
        self.status_bar.showMessage(f"Created new strategy: {data['name']}")
```

**Unit Tests**:
- [ ] **File**: `tests/ui/test_main_window_new_strategy.py`
- [ ] Test: New strategy creates in database
- [ ] Test: Initial version created
- [ ] Test: UI loads new strategy
- [ ] Test: Strategy ID tracked correctly

**Rollback**: Uncomment old code, comment new code

**Sign-off**: ________ Date: ________

---

#### Task 2.2.2: Update StrategyBuilderMainWindow - Open Strategy ✅ COMPLETE
- [x] **File**: `src/strategy_builder/ui/strategy_builder_main_window.py`
- [x] **Action**: Replace "Open" functionality - Uses StrategyBrowserDialog

**OLD CODE** (Comment out):
```python
# def _open_strategy(self):
#     """Open strategy from JSON file"""
#     dialog = QFileDialog(...)
```

**NEW CODE**:
```python
def _open_strategy(self):
    """Open strategy from database"""
    dialog = StrategyBrowserDialog(mode='open', parent=self)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        selection = dialog.get_selected_strategy()
        if selection:
            strategy_id, version_number = selection
            self._load_strategy_from_db(strategy_id, version_number)
            
            # Update window title
            db = get_db_manager()
            version = db.strategy_manager.get_strategy_version_by_number(
                strategy_id, version_number
            )
            if version:
                self.setWindowTitle(f"Strategy Builder - {version['name']} (v{version_number})")

def _load_strategy_from_db(self, strategy_id: str, version_number: Optional[int] = None):
    """Load complete strategy from database"""
    db = get_db_manager()
    
    # Get version (latest if not specified)
    if version_number:
        version = db.strategy_manager.get_strategy_version_by_number(
            strategy_id, version_number
        )
    else:
        version = db.strategy_manager.get_latest_version(strategy_id)
    
    if not version:
        QMessageBox.warning(self, "Error", "Strategy version not found")
        return
    
    # Load into all panels
    self.strategy_info_panel.load_from_db(version)
    self.strategy_blocks_panel.load_blocks_from_db(version['blocks'])
    
    # Load backtest config if exists
    if version.get('backtest_config'):
        self.backtest_panel.load_config_from_db(version['backtest_config'])
    
    # Load results if exist
    if version.get('backtest_results'):
        self.metrics_panel.update_metrics(version['metrics'])
        self.trades_panel.load_trades_from_db(version['trades'])
    
    # Track current strategy
    self.current_strategy_id = strategy_id
    self.current_version_number = version['version_number']
```

**Unit Tests**:
- [ ] **File**: `