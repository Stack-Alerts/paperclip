# SPRINT 1.6.1: DATABASE-FIRST MIGRATION - CHECKLIST PART 2
**Continuation of Implementation Checklist**

---

## 📋 PHASE 2 CONTINUED: STRATEGY BROWSER UI

#### Task 2.2.2: Update StrategyBuilderMainWindow - Open Strategy (CONTINUED)

**Unit Tests**:
- [ ] **File**: `tests/ui/test_main_window_open_strategy.py`
- [ ] Test: Open dialog launches
- [ ] Test: Strategy loads from database
- [ ] Test: All panels populate correctly
- [ ] Test: Window title updates
- [ ] Test: Handles non-existent strategy gracefully

**Rollback**: Uncomment old code, comment new code

**Sign-off**: ________ Date: ________

---

#### Task 2.2.3: Update StrategyBuilderMainWindow - Save Strategy
- [ ] **File**: `src/strategy_builder/ui/strategy_builder_main_window.py`
- [ ] **Action**: Replace "Save" functionality

**OLD CODE** (Comment out):
```python
# def _save_strategy(self):
#     """Save strategy to JSON file"""
```

**NEW CODE**:
```python
def _save_strategy(self):
    """Save strategy to database (create new version)"""
    if not hasattr(self, 'current_strategy_id') or not self.current_strategy_id:
        # No strategy loaded - prompt for new strategy creation
        self._save_strategy_as()
        return
    
    # Collect current strategy data from all panels
    strategy_data = {
        'strategy_id': self.current_strategy_id,
        'name': self.strategy_info_panel.get_strategy_name(),
        'description': self.strategy_info_panel.get_description(),
        'blocks': self.strategy_blocks_panel.get_blocks_data(),
        'signals': self.strategy_blocks_panel.get_signals_data(),
        'parameters': self.strategy_info_panel.get_parameters(),
        'entry_conditions': {},  # TODO: Get from entry panel
        'exit_conditions': {},   # TODO: Get from exit panel
        'risk_management': {},   # TODO: Get from risk panel
        'backtest_config': self.backtest_panel.get_config() if hasattr(self, 'backtest_panel') else {},
        'tags': self.strategy_info_panel.get_tags()
    }
    
    # Calculate config hash
    db = get_db_manager()
    config_hash = db.strategy_manager.calculate_config_hash(strategy_data)
    
    # Check for duplicate
    existing_version_id = db.strategy_manager.find_version_by_hash(config_hash)
    if existing_version_id:
        reply = QMessageBox.question(
            self,
            "Duplicate Configuration",
            "This exact configuration already exists. Save as new version anyway?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.No:
            return
    
    # Add config hash
    strategy_data['config_hash'] = config_hash
    
    # Get git commit hash
    try:
        import subprocess
        git_hash = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        strategy_data['git_commit_hash'] = git_hash
    except:
        pass
    
    # Create new version
    version_id = db.strategy_manager.create_strategy_version(strategy_data)
    
    # Update current version number
    version = db.strategy_manager.get_strategy_version(version_id)
    self.current_version_number = version['version_number']
    
    self.status_bar.showMessage(
        f"Saved {strategy_data['name']} as version {self.current_version_number}"
    )
```

**Unit Tests**:
- [ ] **File**: `tests/ui/test_main_window_save_strategy.py`
- [ ] Test: Save creates new version
- [ ] Test: Version number increments
- [ ] Test: Duplicate detection works
- [ ] Test: Git hash captured
- [ ] Test: All panel data saved
- [ ] Test: Status message displays

**Rollback**: Uncomment old code, comment new code

**Sign-off**: ________ Date: ________

---

#### Task 2.2.4: Add "Save As" for New Strategy Name
- [ ] **File**: `src/strategy_builder/ui/strategy_builder_main_window.py`
- [ ] **Action**: Implement "Save As" functionality

```python
def _save_strategy_as(self):
    """Save strategy with new name (creates new strategy in database)"""
    dialog = NewStrategyDialog(self)
    
    # Pre-populate with current data if exists
    if hasattr(self, 'current_strategy_id'):
        current_name = self.strategy_info_panel.get_strategy_name()
        dialog.name_input.setText(f"{current_name} (Copy)")
    
    if dialog.exec() == QDialog.DialogCode.Accepted:
        data = dialog.get_strategy_data()
        
        # Create new strategy
        db = get_db_manager()
        new_strategy_id = db.strategy_manager.create_strategy(data['name'])
        
        # Collect current configuration
        strategy_data = {
            'strategy_id': new_strategy_id,
            'name': data['name'],
            'description': data['description'],
            'blocks': self.strategy_blocks_panel.get_blocks_data(),
            'signals': self.strategy_blocks_panel.get_signals_data(),
            'parameters': self.strategy_info_panel.get_parameters(),
            'entry_conditions': {},
            'exit_conditions': {},
            'risk_management': {},
            'backtest_config': {},
            'tags': data['tags']
        }
        
        # Create first version
        version_id = db.strategy_manager.create_strategy_version(strategy_data)
        
        # Switch to new strategy
        self.current_strategy_id = new_strategy_id
        self.current_version_number = 1
        
        self.status_bar.showMessage(f"Saved as new strategy: {data['name']}")
```

**Unit Tests**:
- [ ] **File**: `tests/ui/test_main_window_save_as.py`
- [ ] Test: Creates new strategy
- [ ] Test: Copies current configuration
- [ ] Test: Switches to new strategy
- [ ] Test: Original strategy unchanged

**Rollback**: Remove code

**Sign-off**: ________ Date: ________

---

### **STAGE 2.3: Import Legacy JSON Strategies** ⏱️ 6 hours

#### Task 2.3.1: Create JSON Importer Utility
- [ ] **File**: `src/strategy_builder/utils/json_strategy_importer.py` (NEW)
- [ ] **Action**: Create importer for legacy JSON files

```python
from pathlib import Path
from typing import List, Dict, Optional
import json
from datetime import datetime

class JSONStrategyImporter:
    """Import legacy JSON strategy files into database"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def import_strategy_file(self, json_file: Path) -> Optional[str]:
        """
        Import single JSON strategy file
        Returns strategy_id if successful
        """
        try:
            with open(json_file, 'r') as f:
                strategy_data = json.load(f)
            
            # Extract strategy name from filename or data
            name = strategy_data.get('name', json_file.stem)
            
            # Create strategy in database
            strategy_id = self.db.strategy_manager.create_strategy(name)
            
            # Convert JSON format to database format
            version_data = self._convert_json_to_db_format(
                strategy_data,
                strategy_id
            )
            
            # Add import metadata
            version_data['notes'] = f"Imported from {json_file.name}"
            version_data['tags'] = version_data.get('tags', []) + ['imported']
            
            # Create version
            version_id = self.db.strategy_manager.create_strategy_version(version_data)
            
            print(f"✅ Imported {json_file.name} → {strategy_id} (v1)")
            return strategy_id
            
        except Exception as e:
            print(f"❌ Failed to import {json_file.name}: {str(e)}")
            return None
    
    def _convert_json_to_db_format(self, json_data: Dict, strategy_id: str) -> Dict:
        """Convert legacy JSON format to database format"""
        return {
            'strategy_id': strategy_id,
            'name': json_data.get('name', 'Unnamed Strategy'),
            'description': json_data.get('description', ''),
            'blocks': json_data.get('blocks', []),
            'signals': json_data.get('signals', {}),
            'parameters': json_data.get('parameters', {}),
            'entry_conditions': json_data.get('entry_conditions', {}),
            'exit_conditions': json_data.get('exit_conditions', {}),
            'risk_management': json_data.get('risk_management', {}),
            'backtest_config': json_data.get('backtest_config', {}),
            'tags': json_data.get('tags', [])
        }
    
    def import_directory(self, directory: Path, pattern: str = "strategy_*.json") -> Dict[str, int]:
        """
        Import all strategies from directory
        Returns stats: {'success': N, 'failed': M}
        """
        stats = {'success': 0, 'failed': 0}
        
        for json_file in directory.glob(pattern):
            result = self.import_strategy_file(json_file)
            if result:
                stats['success'] += 1
            else:
                stats['failed'] += 1
        
        return stats
    
    def import_from_folders(self, base_dir: Path) -> Dict[str, int]:
        """Import from all strategy folders (drafts, unpublished, published)"""
        folders = [
            base_dir / 'drafts',
            base_dir / 'unpublished',
            base_dir / 'published'
        ]
        
        total_stats = {'success': 0, 'failed': 0}
        
        for folder in folders:
            if folder.exists():
                folder_stats = self.import_directory(folder)
                total_stats['success'] += folder_stats['success']
                total_stats['failed'] += folder_stats['failed']
                print(f"📁 {folder.name}: {folder_stats['success']} imported, {folder_stats['failed']} failed")
        
        return total_stats
```

**Unit Tests**:
- [ ] **File**: `tests/utils/test_json_strategy_importer.py`
- [ ] Test: Import single JSON file
- [ ] Test: Convert JSON to DB format correctly
- [ ] Test: Import directory of files
- [ ] Test: Import from multiple folders
- [ ] Test: Handle malformed JSON
- [ ] Test: Handle missing fields
- [ ] Test: Duplicate strategy names handled
- [ ] Test: Import metadata added

**Rollback**: Remove file

**Sign-off**: ________ Date: ________

---

#### Task 2.3.2: Create Import CLI Command
- [ ] **File**: `scripts/import_legacy_strategies.py` (NEW)
- [ ] **Action**: Create CLI tool for bulk import

```python
#!/usr/bin/env python3
"""
Import legacy JSON strategies into database

Usage:
    python scripts/import_legacy_strategies.py
    python scripts/import_legacy_strategies.py --dry-run
    python scripts/import_legacy_strategies.py --folder user_strategies/published
"""

import argparse
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.optimizer_v3.database.manager import get_db_manager
from src.strategy_builder.utils.json_strategy_importer import JSONStrategyImporter

def main():
    parser = argparse.ArgumentParser(description='Import legacy JSON strategies')
    parser.add_argument('--folder', type=str, help='Specific folder to import')
    parser.add_argument('--dry-run', action='store_true', help='Preview import without executing')
    parser.add_argument('--pattern', type=str, default='strategy_*.json', help='File pattern to match')
    
    args = parser.parse_args()
    
    # Get database manager
    db = get_db_manager()
    importer = JSONStrategyImporter(db)
    
    # Determine import path
    if args.folder:
        import_path = Path(args.folder)
    else:
        import_path = project_root / 'user_strategies'
    
    if not import_path.exists():
        print(f"❌ Error: Path does not exist: {import_path}")
        return 1
    
    print(f"🔍 Scanning for strategies in: {import_path}")
    
    if args.dry_run:
        # Count files that would be imported
        if import_path.is_file():
            print(f"Would import: {import_path}")
            return 0
        
        count = len(list(import_path.rglob(args.pattern)))
        print(f"Would import {count} strategy files")
        return 0
    
    # Perform import
    if import_path.is_file():
        result = importer.import_strategy_file(import_path)
        if result:
            print(f"✅ Import successful: {result}")
            return 0
        else:
            print("❌ Import failed")
            return 1
    else:
        stats = importer.import_from_folders(import_path)
        print(f"\n📊 Import Summary:")
        print(f"   ✅ Success: {stats['success']}")
        print(f"   ❌ Failed: {stats['failed']}")
        return 0 if stats['failed'] == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
```

**Unit Tests**:
- [ ] **File**: `tests/scripts/test_import_legacy_strategies.py`
- [ ] Test: CLI runs without errors
- [ ] Test: Dry-run mode works
- [ ] Test: Single file import
- [ ] Test: Directory import
- [ ] Test: Pattern matching works
- [ ] Test: Stats reported correctly

**Rollback**: Remove file

**Sign-off**: ________ Date: ________

---

#### Task 2.3.3: Add Import UI to Main Window
- [ ] **File**: `src/strategy_builder/ui/strategy_builder_main_window.py`
- [ ] **Action**: Add "Import Legacy Strategies" menu item

```python
def _init_menus(self):
    # ... existing code ...
    
    # File menu
    file_menu = self.menuBar().addMenu("&File")
    
    # ... New, Open, Save actions ...
    
    # Add separator
    file_menu.addSeparator()
    
    # Import action
    import_action = QAction("&Import Legacy Strategies...", self)
    import_action.triggered.connect(self._import_legacy_strategies)
    file_menu.addAction(import_action)

def _import_legacy_strategies(self):
    """Import legacy JSON strategies using file dialog"""
    dialog = QFileDialog(self)
    dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
    dialog.setNameFilter("JSON Files (*.json)")
    dialog.setWindowTitle("Select Legacy Strategies to Import")
    
    if dialog.exec() == QDialog.DialogCode.Accepted:
        files = dialog.selectedFiles()
        
        # Create importer
        db = get_db_manager()
        importer = JSONStrategyImporter(db)
        
        # Import with progress dialog
        progress = QProgressDialog(
            "Importing strategies...",
            "Cancel",
            0,
            len(files),
            self
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        
        success_count = 0
        failed_count = 0
        
        for i, file_path in enumerate(files):
            if progress.wasCanceled():
                break
            
            progress.setValue(i)
            progress.setLabelText(f"Importing {Path(file_path).name}...")
            
            result = importer.import_strategy_file(Path(file_path))
            if result:
                success_count += 1
            else:
                failed_count += 1
        
        progress.setValue(len(files))
        
        # Show summary
        QMessageBox.information(
            self,
            "Import Complete",
            f"Import Summary:\n"
            f"✅ Success: {success_count}\n"
            f"❌ Failed: {failed_count}"
        )
```

**Unit Tests**:
- [ ] **File**: `tests/ui/test_main_window_import.py`
- [ ] Test: Import menu item exists
- [ ] Test: Import dialog opens
- [ ] Test: Files import correctly
- [ ] Test: Progress dialog updates
- [ ] Test: Summary dialog shows
- [ ] Test: Cancel works

**Rollback**: Remove code from _init_menus and _import_legacy_strategies

**Sign-off**: ________ Date: ________

---

## 📋 PHASE 3: PANEL INTEGRATION (Days 7-10)

### **STAGE 3.1: StrategyInfoPanel Integration** ⏱️ 2 hours

#### Task 3.1.1: Add Database Load/Save Methods
- [ ] **File**: `src/strategy_builder/ui/strategy_info_panel.py`
- [ ] **Action**: Add methods for database integration

```python
def load_from_db(self, version_data: Dict) -> None:
    """Load strategy info from database version"""
    self.name_input.setText(version_data.get('name', ''))
    self.description_input.setPlainText(version_data.get('description', ''))
    
    # Set type if exists
    strategy_type = version_data.get('type', 'Custom')
    index = self.type_combo.findText(strategy_type)
    if index >= 0:
        self.type_combo.setCurrentIndex(index)
    
    # Set tags
    tags = version_data.get('tags', [])
    self.tags_input.setText(', '.join(tags))
    
    # Set version info (read-only display)
    if hasattr(self, 'version_label'):
        version_num = version_data.get('version_number', 1)
        self.version_label.setText(f"v{version_num}")
    
    if hasattr(self, 'modified_label'):
        modified = version_data.get('timestamp', datetime.now())
        if isinstance(modified, str):
            modified = datetime.fromisoformat(modified)
        self.modified_label.setText(modified.strftime('%Y-%m-%d %H:%M'))

def get_data_for_db(self) -> Dict:
    """Get current data for database save"""
    tags = [t.strip() for t in self.tags_input.text().split(',') if t.strip()]
    return {
        'name': self.name_input.text(),
        'description': self.description_input.toPlainText(),
        'type': self.type_combo.currentText(),
        'tags': tags
    }
```

**Unit Tests**:
- [ ] **File**: `tests/ui/test_strategy_info_panel.py`
- [ ] Test: load_from_db() populates all fields
- [ ] Test: get_data_for_db() returns correct dict
- [ ] Test: Tags parsing works
- [ ] Test: Version info displays

**Rollback**: Remove methods

**Sign-off**: ________ Date: ________

---

### **STAGE 3.2: StrategyBlocksPanel Integration** ⏱️ 4 hours

#### Task 3.2.1: Add Database Load/Save Methods
- [ ] **File**: `src/strategy_builder/ui/strategy_blocks_panel.py`
- [ ] **Action**: Add database integration methods

```python
def load_blocks_from_db(self, blocks_data: List[Dict]) -> None:
    """Load blocks from database version"""
    # Clear existing blocks
    self.clear_all_blocks()
    
    # Add each block
    for block_data in blocks_data:
        self.add_block_from_data(block_data)

def add_block_from_data(self, block_data: Dict) -> None:
    """Add block from database data"""
    block_name = block_data.get('name')
    if not block_name:
        return
    
    # Add block using existing method
    self.add_block(block_name)
    
    # Configure block with saved data
    block_index = len(self.blocks) - 1
    if block_index >= 0:
        # Set signals
        if 'signals' in block_data:
            self.blocks[block_index].set_signals(block_data['signals'])
        
        # Set parameters
        if 'parameters' in block_data:
            self.blocks[block_index].set_parameters(block_data['parameters'])
        
        # Set logic type
        if 'logic_type' in block_data:
            self.blocks[block_index].set_logic_type(block_data['logic_type'])

def get_blocks_data(self) -> List[Dict]:
    """Get all blocks data for database save"""
    blocks_data = []
    for block in self.blocks:
        blocks_data.append({
            'name': block.get_name(),
            'signals': block.get_signals(),
            'parameters': block.get_parameters(),
            'logic_type': block.get_logic_type(),
            'sequence_number': block.get_sequence_number()
        })
    return blocks_data

def get_signals_data(self) -> Dict:
    """Get aggregated signals data"""
    # Implementation depends on your signal structure
    pass
```

**Unit Tests**:
- [ ] **File**: `tests/ui/test_strategy_blocks_panel.py`
- [ ] Test: load_blocks_from_db() clears and loads
- [ ] Test: add_block_from_data() configures correctly
- [ ] Test: get_blocks_data() returns complete data
- [ ] Test: Sequence numbers preserved
- [ ] Test: Signals and parameters preserved

**Rollback**: Remove methods

**Sign-off**: ________ Date: ________

---

### **STAGE 3.3: BacktestConfigPanel Integration** ⏱️ 3 hours

#### Task 3.3.1: Add Auto-Save to Database After Backtest
- [ ] **File**: `src/strategy_builder/ui/backtest_config_panel.py`
- [ ] **Action**: Save results to database automatically

```python
def _on_backtest_complete(self, results: Dict) -> None:
    """Handle backtest completion - save to database"""
    # Existing result handling...
    
    # NEW: Save to database
    if hasattr(self.parent(), 'current_strategy_id'):
        strategy_id = self.parent().current_strategy_id
        version_number = getattr(self.parent(), 'current_version_number', None)
        
        db = get_db_manager()
        
        # Get current version
        if version_number:
            version = db.strategy_manager.get_strategy_version_by_number(
                strategy_id, version_number
            )
            version_id = version['version_id']
            
            # Update version with results
            db.strategy_manager.update_strategy_version(version_id, {
                'backtest_results': results,
                'metrics': results.get('metrics', {}),
                'trades': results.get('trades', []),
                'equity_curve': results.get('equity_curve', [])
            })
            
            # Save to test_results table
            db.test_results_manager.save_test_results({
                'strategy_id': strategy_id,
                'version_id': version_id,
                'test_type': 'BACKTEST',
                'metrics': results.get('metrics', {}),
                'trades': results.get('trades', []),
                'equity_curve': results.get('equity_curve', [])
            })
```

**Unit Tests**:
- [ ] **File**: `tests/ui/test_backtest_config_panel.py`
- [ ] Test: Results save to database
- [ ] Test: Version updated with metrics
- [ ] Test: Test results table updated
- [ ] Test: Handles missing strategy_id

**Rollback**: Remove auto-save code

**Sign-off**: ________ Date: ________

---

#### Task 3.3.2: Add "Load Last Test Results" Button
- [ ] **File**: `src/strategy_builder/ui/backtest_config_panel.py`
- [ ] **Action**: Implement load button

```python
def _init_ui(self):
    # ... existing code ...
    
    # Add "Load Last Test" button
    self.load_last_btn = QPushButton("📊 Load Last Test Results")
    self.load_last_btn.clicked.connect(self._load_last_test_results)
    # Add to button layout

def _load_last_test_results(self):
    """Load most recent test results from database"""
    if not hasattr(self.parent(), 'current_strategy_id'):
        QMessageBox.information(self, "No Strategy", "No strategy loaded")
        return
    
    strategy_id = self.parent().current_strategy_id
    
    db = get_db_manager()
    results = db.test_results_manager.get_last_test_results(strategy_id)
    
    if not results:
        QMessageBox.information(
            self,
            "No Results",
            "No previous test results found for this strategy"
        )
        return
    
    # Load results into UI
    self.parent().metrics_panel.update_metrics(results['metrics'])
    self.parent().trades_panel.update_trades(results['trades'])
    
    # Show timestamp
    timestamp = results['timestamp'].strftime('%Y-%m-%d %H:%M')
    self.status_label.setText(f"Loaded results from {timestamp}")
```

**Unit Tests**:
- [ ] **File**: `tests/ui/test_backtest_load_last.py`
- [ ] Test: Button exists
- [ ] Test: Loads last results
- [ ] Test: Updates all panels
- [ ] Test: Shows timestamp
- [ ] Test: Handles no results gracefully

**Rollback**: Remove button and method

**Sign-off**: ________ Date: ________

---

## 📋 PHASE 4: AI RECOMMENDATIONS INTEGRATION (Days 11-12)

### **STAGE 4.1: Metrics Panel Duplicate Detection** ⏱️ 4 hours

#### Task 4.1.1: Add Duplicate Check Before AI Request
- [ ] **File**: `src/optimizer_v3/ui/metrics_display_panel.py`
- [ ] **Action**: Check database before showing AI request preview

```python
def _show_ai_request_preview(self) -> None:
    """Show AI request preview - check for duplicates first"""
    # Get current strategy config
    if not hasattr(self.parent(), 'current_strategy_id'):
        # No strategy ID - proceed normally
        self._show_ai_preview_dialog()
        return
    
    strategy_id = self.parent().current_strategy_id
    
    # Collect current config
    config_data = self._collect_strategy_config()
    
    # Calculate hash
    db = get_db_manager()
    config_hash = db.strategy_manager.calculate_config_hash(config_data)
    
    # Check for duplicate
    existing_version_id = db.strategy_manager.find_version_by_hash(config_hash)
    
    if existing_version_id:
        # Get existing recommendations
        recommendations = db.ai_manager.get_ai_recommendations_for_version(
            existing_version_id
        )
        
        if recommendations:
            # Show duplicate dialog
            self._show_duplicate_recommendations_dialog(
                existing_version_id,
                recommendations
            )
            return
    
    # No duplicate - proceed with AI request
    self._show_ai_preview_dialog()

def _collect_strategy_config(self) -> Dict:
    """Collect current strategy configuration"""
    parent = self.parent()
    return {
        'blocks': parent.strategy_blocks_panel.get_blocks_data(),
        'signals': parent.strategy_blocks_panel.get_signals_data(),
        'parameters': parent.strategy_info_panel.get_parameters() if hasattr(parent.strategy_info_panel, 'get_parameters') else {},
        'entry_conditions': {},
        'exit_conditions': {}
    }

def _show_duplicate_recommendations_dialog(self, version_id: str, recommendations: List[Dict]):
    """Show dialog when duplicate configuration found"""
    dialog = QDialog(self)
    dialog.setWindowTitle("Previous AI Recommendations Found")
    dialog.setMinimumWidth(600)
    
    layout = QVBoxLayout()
    
    # Message
    msg = QLabel(
        "This exact strategy configuration was previously analyzed.\n"
        "Previous AI recommendations are available.\n\n"
        "Running a new analysis will incur additional API costs "
        "and return similar recommendations."
    )
    msg.setWordWrap(True)
    layout.addWidget(msg)
    
    # Show previous recommendations summary
    summary = QTextEdit()
    summary.setReadOnly(True)
    summary.setMaximumHeight(200)
    summary.setPlainText(self._format_recommendations_summary(recommendations))
    layout.addWidget(QLabel("Previous Recommendations:"))
    layout.addWidget(summary)
    
    # Buttons
    btn_layout = QHBoxLayout()
    load_btn = QPushButton("Load Previous Recommendations")
    new_btn = QPushButton("Run New Analysis Anyway")
    cancel_btn = QPushButton("Cancel")
    
    load_btn.clicked.connect(lambda: self._load_existing_recommendations(recommendations, dialog))
    new_btn.clicked.connect(lambda: self._proceed_with_new_analysis(dialog))
    cancel_btn.clicked.connect(dialog.reject)
    
    btn_layout.addWidget(load_btn)
    btn_layout.addWidget(new_btn)
    btn_layout.addWidget(cancel_btn)
    
    layout.addLayout(btn_layout)
    dialog.setLayout(layout)
    dialog.exec()

def _load_existing_recommendations(self, recommendations: List[Dict], dialog: QDialog):
    """Load existing recommendations into panel"""
    # Load into AI recommendations panel
    parent = self.parent()
    if hasattr(parent, 'ai_recommendations_panel'):
        parent.ai_recommendations_panel.load_recommendations_from_db(recommendations)
    
    dialog.accept()
    
    QMessageBox.information(
        self,
        "Recommendations Loaded",
        f"Loaded {len(recommendations)} previous recommendations"
    )
```

**Unit Tests**:
- [ ] **File**: `tests/ui/test_metrics_duplicate_detection.py`
- [ ] Test: Duplicate detection runs
- [ ] Test: Hash calculation correct
- [ ] Test: Duplicate dialog shows
- [ ] Test: Load previous recommendations works
- [ ] Test: New analysis proceeds
- [ ] Test: No duplicate proceeds normally

**Rollback**: Remove duplicate check code

**Sign-off**: ________ Date: ________

---

#### Task 4.1.2: Save AI Recommendations to Database