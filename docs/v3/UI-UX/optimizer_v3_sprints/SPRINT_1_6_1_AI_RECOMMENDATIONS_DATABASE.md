# SPRINT 1.6.1: AI RECOMMENDATIONS DATABASE EXTENSION
**Institutional-Grade AI Recommendation Tracking & History**

**Sprint**: 1.6.1  
**Status**: ✅ COMPLETE (2026-01-29)  
**Duration**: 4 hours actual (estimated 5-7 days)  
**Dependencies**: Sprint 1.6 (AI Recommendations)  
**Test Coverage**: 90 tests passing (49 Test Results + 41 Strategy/AI)

## 🎯 OBJECTIVES

1. Extend PostgreSQL database to track AI recommendations
2. Implement duplicate detection system
3. Add "Load Last Test Results" functionality
4. Ensure proper version tracking of strategies
5. ~~Migrate to hybrid JSON/DB approach~~ **Migrate to DATABASE-FIRST architecture**

## 🏛️ ARCHITECTURAL DECISION: DATABASE-FIRST

### **CRITICAL FINDING: Hybrid Approach is Risky**

After deep trace analysis identifying **135 JSON file operations**, a hybrid approach creates:
- **Multiple sources of truth** (JSON vs DB inconsistency)
- **Race conditions** (AI reads JSON while DB updates)
- **Sync complexity** (JSON ↔ DB synchronization overhead)
- **Migration nightmare** (which source is current?)

### **RECOMMENDED: DATABASE-FIRST with JSON Export**

**Primary Storage**: PostgreSQL Database
**Secondary**: JSON export for backup/portability only

**Benefits**:
1. ✅ Single source of truth
2. ✅ ACID compliance (atomic operations)
3. ✅ Built-in versioning
4. ✅ Query capabilities
5. ✅ Relationship integrity
6. ✅ AI always reads current data
7. ✅ Concurrent access safety

**JSON Role**:
- Export format for backups
- Import format for legacy strategies
- Portability between systems
- Human-readable inspection

### **Migration Strategy**

#### **Phase 1: Database Becomes Primary (Days 1-3)**
```python
class StrategyPersistence:
    def save(self, strategy: StrategyConfig) -> str:
        # PRIMARY: Save to database
        version_id = db.create_strategy_version(strategy)
        
        # SECONDARY: Export JSON for backup (optional)
        if config.AUTO_EXPORT_JSON:
            self._export_json_backup(strategy, version_id)
        
        return version_id
    
    def load(self, strategy_id: str, version: Optional[int] = None) -> StrategyConfig:
        # PRIMARY: Load from database
        return db.get_strategy_version(strategy_id, version)
    
    def _export_json_backup(self, strategy: StrategyConfig, version_id: str):
        """Optional JSON backup export"""
        backup_dir = Path("backups/strategies")
        backup_dir.mkdir(exist_ok=True)
        
        filename = f"{strategy.name}_v{strategy.version}_{version_id[:8]}.json"
        filepath = backup_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(strategy.to_dict(), f, indent=2)
```

#### **Phase 2: JSON Import for Legacy (Days 4-5)**
```python
class LegacyStrategyImporter:
    def import_from_json(self, json_file: Path) -> str:
        """One-time import of legacy JSON strategies to database"""
        with open(json_file, 'r') as f:
            strategy_data = json.load(f)
        
        # Convert to database format
        version_id = db.create_strategy_version({
            'name': strategy_data['name'],
            'blocks': strategy_data['blocks'],
            'signals': strategy_data['signals'],
            # ... complete conversion
        })
        
        # Mark as imported
        db.add_metadata(version_id, {
            'imported_from': str(json_file),
            'import_date': datetime.now()
        })
        
        return version_id
    
    def bulk_import_directory(self, directory: Path):
        """Import all legacy strategies from directory"""
        for json_file in directory.glob("strategy_*.json"):
            try:
                version_id = self.import_from_json(json_file)
                print(f"✅ Imported {json_file.name} → {version_id}")
            except Exception as e:
                print(f"❌ Failed to import {json_file.name}: {e}")
```

#### **Phase 3: Deprecate JSON Primary Storage (Day 6-7)**
```python
# OLD (DEPRECATED):
def save_strategy(strategy):
    with open(f"strategy_{num}.json", 'w') as f:
        json.dump(strategy, f)

# NEW (DATABASE-FIRST):
def save_strategy(strategy):
    version_id = db.create_strategy_version(strategy)
    return version_id
```

### **JSON File Operations Audit**

Found 135 JSON operations across system:

**Strategy Storage** (18 files):
- `strategy_{NNN}_name.json` in drafts/unpublished/published
- `current_strategy.json` (working copy)
- **Action**: Migrate to database, keep JSON as export only

**Optimization/Checkpoint** (8 files):
- `checkpoint_*.json` - optimization checkpoints
- `state_*.json` - session state
- **Action**: Keep JSON for now (optimization engine specific)

**History/Stats** (5 files):
- `{strategy_id}_iterations.json` - iteration history
- `block_performance_db.json` - global block stats
- `signal_occurrence_statistics.json` - signal stats
- **Action**: Migrate to database tables

**Config/Metadata** (4 files):
- `.sync_state.json` - data sync state
- `.lakeapi_usage.json` - usage tracking
- `.checksum.json` - file checksums
- **Action**: Keep (infrastructure files)

### **Data Consistency Rules**

1. **Strategy Data**: Database ONLY
   ```python
   # ALWAYS read from database
   strategy = db.get_strategy_version(strategy_id)
   
   # NEVER read from JSON for strategy data
   # with open('strategy.json') as f:  # ❌ WRONG
   ```

2. **AI Recommendations**: Database ONLY
   ```python
   # AI system reads strategy from database
   strategy_config = db.get_strategy_version(version_id)
   recommendations = ai_engine.analyze(strategy_config)
   
   # Save recommendations to database
   db.save_ai_recommendations(recommendations, version_id)
   ```

3. **Test Results**: Database ONLY
   ```python
   # Results stored in database
   result_id = db.save_test_results(metrics, trades, version_id)
   
   # Load results from database
   results = db.get_test_results(version_id)
   ```

4. **Version Control**: Database with Git Hash
   ```python
   # Database stores git hash for traceability
   version = db.create_strategy_version(strategy)
   git_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD'])
   db.update_version_metadata(version, {'git_hash': git_hash})
   ```

### **Transition Plan**

**Week 1: Database Infrastructure**
- Create all database tables
- Implement database manager methods
- Build import utilities
- Test CRUD operations

**Week 2: Application Migration**
- Update StrategyBuilderOrchestrator
- Migrate save/load operations
- Update AI recommendation system
- Update all panels to read from DB

**Week 3: Legacy Support**
- Build JSON export functionality
- Build JSON import for legacy
- Bulk import existing strategies
- Deprecation warnings for JSON

**Week 4: Cleanup**
- Remove JSON primary storage code
- Keep JSON export/import only
- Update documentation
- Final testing

### **Rollback Plan**

If database migration fails:
1. Database tables remain separate
2. JSON files untouched
3. Can revert to JSON primary
4. No data loss

**Safety Measures**:
- Full backup before migration
- JSON export before deletion
- Phased rollout with feature flags
- Rollback commands documented

## 🏗️ DATABASE SCHEMA EXTENSION

### New Tables

```sql
-- AI Recommendations Table
CREATE TABLE ai_recommendations (
    recommendation_id UUID PRIMARY KEY,
    strategy_id VARCHAR NOT NULL,
    strategy_version VARCHAR NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    recommendation_type VARCHAR NOT NULL,  -- 'ADD_BLOCK', 'ADJUST_PARAMETER', etc.
    block_name VARCHAR,
    signal_name VARCHAR,
    parameter_name VARCHAR,
    configuration JSONB,
    reasoning TEXT NOT NULL,
    expected_impact JSONB,
    combined_confidence FLOAT,
    root_cause TEXT,
    warnings JSONB,
    ai_enhanced BOOLEAN DEFAULT false,
    applied BOOLEAN DEFAULT false,
    applied_at TIMESTAMP,
    metrics_before JSONB,
    metrics_after JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    FOREIGN KEY (strategy_id) REFERENCES strategies(strategy_id)
);

-- Strategy Versions Table
CREATE TABLE strategy_versions (
    version_id UUID PRIMARY KEY,
    strategy_id VARCHAR NOT NULL,
    version_number INTEGER NOT NULL,
    name VARCHAR NOT NULL,
    description TEXT,
    -- Complete strategy definition
    blocks JSONB NOT NULL,          -- Building blocks with signals and parameters
    signals JSONB NOT NULL,         -- Signal configurations
    parameters JSONB NOT NULL,      -- Strategy parameters
    entry_conditions JSONB NOT NULL, -- Entry logic
    exit_conditions JSONB NOT NULL,  -- Exit logic
    risk_management JSONB NOT NULL,  -- Risk management settings
    -- Configuration and results
    backtest_config JSONB NOT NULL,  -- Backtest configuration
    backtest_results JSONB,         -- Complete backtest results
    metrics JSONB,                  -- Performance metrics
    trades JSONB,                   -- Trade history
    equity_curve JSONB,             -- Equity curve data
    -- Version metadata
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    git_commit_hash VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by VARCHAR,             -- User who created this version
    notes TEXT,                     -- Version notes/changelog
    tags JSONB,                     -- Version tags for organization
    FOREIGN KEY (strategy_id) REFERENCES strategies(strategy_id),
    UNIQUE (strategy_id, version_number)
);

-- Strategy Block Versions Table (for detailed block tracking)
CREATE TABLE strategy_block_versions (
    block_version_id UUID PRIMARY KEY,
    version_id UUID NOT NULL,
    block_name VARCHAR NOT NULL,
    block_type VARCHAR NOT NULL,
    signals JSONB NOT NULL,         -- Block's signals
    parameters JSONB NOT NULL,      -- Block's parameters
    logic_type VARCHAR NOT NULL,    -- AND/OR logic
    sequence_number INTEGER,        -- Block order in strategy
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    FOREIGN KEY (version_id) REFERENCES strategy_versions(version_id)
);

-- Strategy Test Results Table
CREATE TABLE strategy_test_results (
    result_id UUID PRIMARY KEY,
    strategy_id VARCHAR NOT NULL,
    version_id UUID NOT NULL,
    test_type VARCHAR NOT NULL, -- 'BACKTEST', 'LIVE_REPLAY', etc.
    metrics JSONB NOT NULL,
    trades JSONB,
    equity_curve JSONB,
    ai_recommendations JSONB,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    FOREIGN KEY (strategy_id) REFERENCES strategies(strategy_id),
    FOREIGN KEY (version_id) REFERENCES strategy_versions(version_id)
);
```

### Indexes

```sql
-- AI Recommendations
CREATE INDEX idx_ai_recommendations_strategy ON ai_recommendations(strategy_id);
```

---

## 🏗️ ORM MODEL CLASSES (INSTITUTIONAL REQUIREMENT)

### **CRITICAL: Add SQLAlchemy ORM Classes**

**WHY ORM IS REQUIRED (Not Optional):**
1. **Type Safety**: Real money is at risk - column types validated at Python level
2. **IDE Autocomplete**: `strategy.exit_conditions` vs `row['exit_conditions']`
3. **Refactoring Safety**: Rename column → IDE finds all usages
4. **Relationship Management**: Foreign keys enforced in Python code
5. **Query Building**: `session.query(Strategy).filter_by()` vs raw SQL
6. **Migration Validation**: Alembic auto-generates migrations from model changes
7. **Test Mocking**: Easy to mock model objects in unit tests

### **ORM Model Definitions**

**File**: `src/optimizer_v3/database/models.py`

```python
# Add to existing models.py AFTER existing models

class Strategy(Base):
    """
    Parent strategy table (Sprint 1.6.1)
    Links all versions, recommendations, and test results
    """
    __tablename__ = 'strategies'
    
    strategy_id = Column(String, primary_key=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    versions = relationship("StrategyVersion", back_populates="strategy", cascade="all, delete-orphan")
    recommendations = relationship("AIRecommendation", back_populates="strategy", cascade="all, delete-orphan")
    test_results = relationship("StrategyTestResult", back_populates="strategy", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_strategies_name', 'name'),
        Index('idx_strategies_created_at', 'created_at'),
    )


class StrategyVersion(Base):
    """
    Versioned strategy configurations (Sprint 1.6.1)
    Complete strategy definition with full history
    """
    __tablename__ = 'strategy_versions'
    
    # Primary identification
    version_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id = Column(String, ForeignKey('strategies.strategy_id', ondelete='CASCADE'), nullable=False)
    version_number = Column(Integer, nullable=False)
    
    # Strategy metadata
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Complete strategy definition (JSONB for flexibility)
    blocks = Column(JSONB, nullable=False)
    signals = Column(JSONB, nullable=False)
    parameters = Column(JSONB, nullable=False)
    entry_conditions = Column(JSONB, nullable=False)
    exit_conditions = Column(JSONB, nullable=False)  # Used by Sprint 1.8
    risk_management = Column(JSONB, nullable=False)
    
    # Backtest configuration and results
    backtest_config = Column(JSONB, nullable=False)
    backtest_results = Column(JSONB)
    metrics = Column(JSONB)
    trades = Column(JSONB)
    equity_curve = Column(JSONB)
    
    # Version control and tracking
    timestamp = Column(DateTime, nullable=False, server_default=func.now())
    git_commit_hash = Column(String(40))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    created_by = Column(String(100))
    notes = Column(Text)
    tags = Column(JSONB)
    
    # Duplicate detection
    config_hash = Column(String(64), index=True)
    
    # Relationships
    strategy = relationship("Strategy", back_populates="versions")
    block_versions = relationship("StrategyBlockVersion", back_populates="version", cascade="all, delete-orphan")
    recommendations = relationship("AIRecommendation", back_populates="version", cascade="all, delete-orphan")
    test_results = relationship("StrategyTestResult", back_populates="version", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('strategy_id', 'version_number', name='uq_strategy_version'),
        Index('idx_strategy_versions_strategy', 'strategy_id'),
        Index('idx_strategy_versions_timestamp', 'timestamp'),
        Index('idx_strategy_versions_hash', 'config_hash'),
    )


class StrategyBlockVersion(Base):
    """
    Block-level version tracking (Sprint 1.6.1)
    Tracks individual building blocks within strategy versions
    """
    __tablename__ = 'strategy_block_versions'
    
    block_version_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id = Column(UUID(as_uuid=True), ForeignKey('strategy_versions.version_id', ondelete='CASCADE'), nullable=False)
    block_name = Column(String(255), nullable=False)
    block_type = Column(String(100), nullable=False)
    signals = Column(JSONB, nullable=False)
    parameters = Column(JSONB, nullable=False)
    logic_type = Column(String(20), nullable=False)  # AND/OR
    sequence_number = Column(Integer)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    version = relationship("StrategyVersion", back_populates="block_versions")
    
    __table_args__ = (
        Index('idx_block_versions_version', 'version_id'),
        Index('idx_block_versions_name', 'block_name'),
    )


class AIRecommendation(Base):
    """
    AI recommendation tracking (Sprint 1.6.1)
    Stores AI-generated recommendations with full metadata
    """
    __tablename__ = 'ai_recommendations'
    
    recommendation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id = Column(String, ForeignKey('strategies.strategy_id', ondelete='CASCADE'), nullable=False)
    version_id = Column(UUID(as_uuid=True), ForeignKey('strategy_versions.version_id', ondelete='CASCADE'), nullable=False)
    strategy_version = Column(String(50), nullable=False)  # Display version string
    
    # Recommendation details
    timestamp = Column(DateTime, nullable=False, server_default=func.now())
    recommendation_type = Column(String(50), nullable=False)  # ADD_BLOCK, ADJUST_PARAMETER, etc.
    block_name = Column(String(255))
    signal_name = Column(String(255))
    parameter_name = Column(String(255))
    configuration = Column(JSONB)
    reasoning = Column(Text, nullable=False)
    expected_impact = Column(JSONB)
    combined_confidence = Column(Float)
    root_cause = Column(Text)
    warnings = Column(JSONB)
    
    # AI metadata
    ai_enhanced = Column(Boolean, default=False)
    
    # Application tracking
    applied = Column(Boolean, default=False)
    applied_at = Column(DateTime)
    applied_version_id = Column(UUID(as_uuid=True))  # Version where applied
    applied_by = Column(String(100))
    metrics_before = Column(JSONB)
    metrics_after = Column(JSONB)
    
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    strategy = relationship("Strategy", back_populates="recommendations")
    version = relationship("StrategyVersion", back_populates="recommendations")
    
    __table_args__ = (
        Index('idx_ai_recommendations_strategy', 'strategy_id'),
        Index('idx_ai_recommendations_version', 'version_id'),
        Index('idx_ai_recommendations_timestamp', 'timestamp'),
        Index('idx_ai_recommendations_type', 'recommendation_type'),
        Index('idx_ai_recommendations_applied', 'applied'),
    )


class StrategyTestResult(Base):
    """
    Strategy test results history (Sprint 1.6.1)
    Stores complete backtest/forward test results
    """
    __tablename__ = 'strategy_test_results'
    
    result_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id = Column(String, ForeignKey('strategies.strategy_id', ondelete='CASCADE'), nullable=False)
    version_id = Column(UUID(as_uuid=True), ForeignKey('strategy_versions.version_id', ondelete='CASCADE'), nullable=False)
    
    # Test details
    test_type = Column(String(50), nullable=False)  # BACKTEST, LIVE_REPLAY, FORWARD_TEST
    metrics = Column(JSONB, nullable=False)
    trades = Column(JSONB)
    equity_curve = Column(JSONB)
    ai_recommendations = Column(JSONB)  # Linked recommendations
    
    # Timestamps
    timestamp = Column(DateTime, nullable=False, server_default=func.now())
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    strategy = relationship("Strategy", back_populates="test_results")
    version = relationship("StrategyVersion", back_populates="test_results")
    
    __table_args__ = (
        Index('idx_test_results_strategy', 'strategy_id'),
        Index('idx_test_results_version', 'version_id'),
        Index('idx_test_results_timestamp', 'timestamp'),
        Index('idx_test_results_test_type', 'test_type'),
    )
```

### **Manager Refactoring to Use ORM**

**File**: `src/optimizer_v3/database/strategy_manager.py`

```python
# BEFORE (Raw SQL):
def create_strategy(self, name: str) -> str:
    query = text("""
        INSERT INTO strategies (strategy_id, name, created_at, updated_at)
        VALUES (:strategy_id, :name, NOW(), NOW())
    """)
    self.session.execute(query, {'strategy_id': strategy_id, 'name': name})

# AFTER (ORM):
def create_strategy(self, name: str) -> str:
    strategy = Strategy(
        strategy_id=f"strategy_{uuid4().hex[:8]}",
        name=name.strip()
    )
    self.session.add(strategy)
    self.session.commit()
    return strategy.strategy_id

# BEFORE (Raw SQL):
def get_strategy_version(self, version_id: str) -> Optional[Dict[str, Any]]:
    query = text("SELECT * FROM strategy_versions WHERE version_id = :version_id")
    result = self.session.execute(query, {'version_id': version_id}).fetchone()
    return dict(result._mapping) if result else None

# AFTER (ORM):
def get_strategy_version(self, version_id: str) -> Optional[StrategyVersion]:
    return self.session.query(StrategyVersion).filter(
        StrategyVersion.version_id == version_id
    ).first()
```

### **ORM Implementation Tasks**

| Task | File | Description | Priority |
|------|------|-------------|----------|
| 1.6.1.ORM.1 | `models.py` | Add Strategy ORM class | HIGH |
| 1.6.1.ORM.2 | `models.py` | Add StrategyVersion ORM class | HIGH |
| 1.6.1.ORM.3 | `models.py` | Add StrategyBlockVersion ORM class | HIGH |
| 1.6.1.ORM.4 | `models.py` | Add AIRecommendation ORM class | HIGH |
| 1.6.1.ORM.5 | `models.py` | Add StrategyTestResult ORM class | HIGH |
| 1.6.1.ORM.6 | `strategy_manager.py` | Refactor create_strategy() to ORM | MEDIUM |
| 1.6.1.ORM.7 | `strategy_manager.py` | Refactor create_strategy_version() to ORM | MEDIUM |
| 1.6.1.ORM.8 | `strategy_manager.py` | Refactor get_strategy_version() to ORM | MEDIUM |
| 1.6.1.ORM.9 | `strategy_manager.py` | Refactor get_all_strategies() to ORM | MEDIUM |
| 1.6.1.ORM.10 | `ai_recommendations_manager.py` | Refactor to use ORM + text() | MEDIUM |
| 1.6.1.ORM.11 | `test_results_manager.py` | Refactor to use ORM | MEDIUM |
| 1.6.1.ORM.12 | `tests/database/` | Add ORM unit tests | HIGH |

**Estimated Time**: 11 hours (1.5 days)

---

## 🏗️ DATABASE SCHEMA EXTENSION (SQL - Reference Only)

The SQL below is for REFERENCE. The actual schema should be managed via:
1. ORM Model Classes (above) as source of truth
2. Alembic migration auto-generated from ORM changes

```sql
-- AI Recommendations
CREATE INDEX idx_ai_recommendations_strategy ON ai_recommendations(strategy_id);
CREATE INDEX idx_ai_recommendations_version ON ai_recommendations(strategy_id, strategy_version);
CREATE INDEX idx_ai_recommendations_timestamp ON ai_recommendations(timestamp);
CREATE INDEX idx_ai_recommendations_type ON ai_recommendations(recommendation_type);
CREATE INDEX idx_ai_recommendations_applied ON ai_recommendations(applied);

-- Strategy Versions
CREATE INDEX idx_strategy_versions_strategy ON strategy_versions(strategy_id);
CREATE INDEX idx_strategy_versions_timestamp ON strategy_versions(timestamp);
CREATE INDEX idx_strategy_versions_version ON strategy_versions(strategy_id, version_number);

-- Strategy Test Results
CREATE INDEX idx_test_results_strategy ON strategy_test_results(strategy_id);
CREATE INDEX idx_test_results_version ON strategy_test_results(version_id);
CREATE INDEX idx_test_results_timestamp ON strategy_test_results(timestamp);
```

## 🔄 DUPLICATE DETECTION SYSTEM

### Strategy Version Hash Calculation
```python
def calculate_strategy_hash(strategy_config: Dict) -> str:
    """
    Calculate deterministic hash of strategy configuration
    Ignores non-functional changes (descriptions, metadata)
    """
    # Extract core configuration elements
    core_elements = {
        'blocks': [
            {
                'name': block['name'],
                'signals': sorted(block['signals']),
                'parameters': block['parameters']
            }
            for block in strategy_config['blocks']
        ],
        'parameters': strategy_config.get('parameters', {}),
        'entry_conditions': strategy_config.get('entry_conditions', {}),
        'exit_conditions': strategy_config.get('exit_conditions', {})
    }
    
    # Generate deterministic JSON string
    json_str = json.dumps(core_elements, sort_keys=True)
    
    # Calculate SHA-256 hash
    return hashlib.sha256(json_str.encode()).hexdigest()
```

### Duplicate Check Dialog
```python
class DuplicateCheckDialog(QDialog):
    """Dialog shown when duplicate strategy detected"""
    
    def __init__(self, last_run_date: datetime, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Previous AI Recommendations Available")
        
        layout = QVBoxLayout()
        
        # Information
        msg = QLabel(
            f"This strategy configuration was previously analyzed on "
            f"{last_run_date.strftime('%Y-%m-%d %H:%M')}.\n\n"
            f"Running the AI analysis again will incur additional API costs "
            f"but return the same recommendations.\n\n"
            f"Would you like to:"
        )
        layout.addWidget(msg)
        
        # Options
        self.load_btn = QPushButton("Load Previous Results")
        self.rerun_btn = QPushButton("Run New Analysis")
        self.cancel_btn = QPushButton("Cancel")
        
        layout.addWidget(self.load_btn)
        layout.addWidget(self.rerun_btn)
        layout.addWidget(self.cancel_btn)
        
        self.setLayout(layout)
        
        # Connect buttons
        self.load_btn.clicked.connect(self.accept)
        self.rerun_btn.clicked.connect(lambda: self.done(2))
        self.cancel_btn.clicked.connect(self.reject)
```

## 🔄 STRATEGY VERSION MANAGEMENT

### Version Switching UI
```python
class StrategyVersionDialog(QDialog):
    """Dialog for switching between strategy versions"""
    
    version_selected = pyqtSignal(str)  # Emits version_id
    
    def __init__(self, strategy_id: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Strategy Version History")
        self.setMinimumWidth(800)
        
        layout = QVBoxLayout()
        
        # Version list with details
        self.version_table = QTableWidget()
        self.version_table.setColumnCount(6)
        self.version_table.setHorizontalHeaderLabels([
            'Version', 'Date', 'Changes', 'Metrics', 'AI Recommendations', 'Git Hash'
        ])
        self.version_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.version_table)
        
        # Load versions
        self._load_versions(strategy_id)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.switch_btn = QPushButton("Switch to Version")
        self.switch_btn.clicked.connect(self._switch_version)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.switch_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def _load_versions(self, strategy_id: str):
        """Load all versions of this strategy"""
        db = get_db_manager()
        versions = db.get_strategy_versions(strategy_id)
        
        self.version_table.setRowCount(len(versions))
        for i, version in enumerate(versions):
            # Version number
            self.version_table.setItem(i, 0, QTableWidgetItem(str(version['version_number'])))
            
            # Date
            date = version['timestamp'].strftime('%Y-%m-%d %H:%M')
            self.version_table.setItem(i, 1, QTableWidgetItem(date))
            
            # Changes
            changes = version.get('changes', 'No description')
            self.version_table.setItem(i, 2, QTableWidgetItem(changes))
            
            # Key metrics summary
            metrics = version.get('metrics', {})
            metrics_text = f"Win Rate: {metrics.get('win_rate', 0):.1f}%\n"
            metrics_text += f"PF: {metrics.get('profit_factor', 0):.2f}"
            self.version_table.setItem(i, 3, QTableWidgetItem(metrics_text))
            
            # AI recommendations count
            recs = version.get('ai_recommendations', [])
            rec_text = f"{len(recs)} recommendations"
            self.version_table.setItem(i, 4, QTableWidgetItem(rec_text))
            
            # Git hash (shortened)
            git_hash = version.get('git_commit_hash', '')[:8]
            self.version_table.setItem(i, 5, QTableWidgetItem(git_hash))
    
    def _switch_version(self):
        """Switch to selected version"""
        current_row = self.version_table.currentRow()
        if current_row >= 0:
            version_id = self.version_table.item(current_row, 0).text()
            self.version_selected.emit(version_id)
            self.accept()
```

### Version Loading System
```python
class StrategyBuilder:
    def load_strategy_version(self, version_id: str):
        """Load complete strategy version with all associated data"""
        try:
            db = get_db_manager()
            
            # Get version data with complete strategy
            version = db.get_strategy_version(version_id)
            if not version:
                raise ValueError(f"Version {version_id} not found")
            
            # Load complete strategy definition
            self.load_strategy({
                'name': version['name'],
                'blocks': version['blocks'],
                'signals': version['signals'],
                'parameters': version['parameters'],
                'entry_conditions': version['entry_conditions'],
                'exit_conditions': version['exit_conditions'],
                'risk_management': version['risk_management']
            })
            
            # Load block configurations
            blocks = db.get_strategy_block_versions(version_id)
            for block in blocks:
                self.blocks_panel.configure_block(
                    block['block_name'],
                    block['signals'],
                    block['parameters'],
                    block['logic_type']
                )
            
            # Load backtest configuration
            self.backtest_panel.load_config(version['backtest_config'])
            
            # Load test results if available
            if version.get('backtest_results'):
                self.backtest_panel.load_results(version['backtest_results'])
                
                # Update all panels with results
                self.metrics_panel.update_metrics(version['metrics'])
                self.trades_panel.update_trades(version['trades'])
                self.equity_panel.update_curve(version['equity_curve'])
            
            # Load AI recommendations
            recs = db.get_ai_recommendations_for_version(version_id)
            if recs:
                self.ai_panel.load_recommendations(recs)
            
            # Update UI state
            self.status_label.setText(
                f"Loaded version {version['version_number']} - {version['name']} "
                f"({version['timestamp'].strftime('%Y-%m-%d %H:%M')})"
            )
            
            # Update version info panel
            self.version_info_panel.update({
                'version': version['version_number'],
                'name': version['name'],
                'description': version['description'],
                'created_by': version['created_by'],
                'created_at': version['created_at'],
                'notes': version['notes'],
                'tags': version['tags'],
                'git_hash': version['git_commit_hash']
            })
            
            return True
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to load version: {str(e)}"
            )
            return False
```

### Version Menu Integration
```python
# In StrategyBuilder._init_ui():
        
# Add Version menu
version_menu = self.menuBar().addMenu("&Version")

# Version history action
history_action = QAction("Version &History...", self)
history_action.setShortcut("Ctrl+H")
history_action.triggered.connect(self._show_version_history)
version_menu.addAction(history_action)

def _show_version_history(self):
    """Show version history dialog"""
    strategy_id = self.get_current_strategy_id()
    if not strategy_id:
        QMessageBox.warning(
            self,
            "Error",
            "No strategy loaded"
        )
        return
    
    dialog = StrategyVersionDialog(strategy_id, self)
    dialog.version_selected.connect(self.load_strategy_version)
    dialog.exec()
```

## 📊 LOAD LAST TEST RESULTS

### UI Changes
```python
# In BacktestPanel
def _init_ui(self):
    # ... existing code ...
    
    # Add "Load Last Test" button next to "View Live Results"
    self.load_last_btn = QPushButton("Load Last Test Results")
    self.load_last_btn.setStyleSheet(get_primary_button_stylesheet())
    self.load_last_btn.clicked.connect(self._load_last_test_results)
    
    # Add to layout next to view_live_btn
    self.button_layout.addWidget(self.load_last_btn)

def _load_last_test_results(self):
    """Load and display last test results for current strategy"""
    try:
        # Get current strategy ID
        strategy_id = self.get_current_strategy_id()
        
        # Get last test results from database
        db = get_db_manager()
        results = db.get_last_test_results(strategy_id)
        
        if not results:
            QMessageBox.information(
                self,
                "No Results",
                "No previous test results found for this strategy."
            )
            return
        
        # Update UI components
        self.metrics_panel.update_metrics(results['metrics'])
        self.trades_panel.update_trades(results['trades'])
        self.equity_panel.update_curve(results['equity_curve'])
        
        # Load AI recommendations if available
        if results.get('ai_recommendations'):
            self.ai_panel.load_recommendations(
                results['ai_recommendations']
            )
        
        self.status_label.setText(
            f"Loaded results from {results['timestamp']}"
        )
        
    except Exception as e:
        QMessageBox.warning(
            self,
            "Error",
            f"Failed to load last test results: {str(e)}"
        )
```

## 🔄 MIGRATION PLAN

### Phase 1: Database Extension
1. Create new tables (ai_recommendations, strategy_versions, strategy_test_results)
2. Add indexes for performance
3. Create database migration script
4. Add version tracking triggers

### Phase 2: Hybrid Storage Implementation
1. Keep JSON files for active development
2. Auto-migrate to database after first test
3. Implement version control integration
4. Add strategy snapshot system

### Phase 3: UI Integration
1. Add duplicate detection dialog
2. Add "Load Last Test" button
3. Implement results loading system
4. Add version history viewer

## 🔍 DEEP TRACE: COMPLETE SYSTEM COVERAGE ANALYSIS

### **LAYER 1: Main Application Windows**

#### **StrategyBuilderMainWindow** (`src/strategy_builder/ui/strategy_builder_main_window.py`)
**Current State**: Main container for strategy building
**Required Changes**:
1. Add version menu to menu bar
2. Integrate version history dialog
3. Add version info panel to status bar
4. Connect version signals to database
5. Implement auto-save to database on strategy changes

**Methods Requiring Updates**:
```python
# NEW METHODS NEEDED:
def _init_version_menu(self) -> None
def _show_version_history(self) -> None
def _on_strategy_changed(self) -> None  # Trigger auto-save
def _save_version_to_db(self) -> None
def _load_version_from_db(self, version_id: str) -> None
def get_current_strategy_id(self) -> str
```

#### **MainWindow** (`src/strategy_builder/ui/main_window.py`)
**Current State**: Alternative main window
**Required Changes**:
1. Same version menu integration
2. Database connection initialization
3. Strategy ID tracking

---

### **LAYER 2: Strategy Data Panels**

#### **StrategyBlocksPanel** (`src/strategy_builder/ui/strategy_blocks_panel.py`)
**Current State**: Displays and manages building blocks
**Required Changes**:
1. Track block changes for versioning
2. Emit signals on block add/remove/modify
3. Support loading blocks from database version
4. Maintain block sequence numbers

**Methods Requiring Updates**:
```python
# EXISTING METHODS TO MODIFY:
def add_block(self, block_name: str) -> None
    # Add: Emit block_changed signal
    # Add: Trigger version auto-save
    
def remove_block(self, block_index: int) -> None
    # Add: Emit block_changed signal
    # Add: Trigger version auto-save

# NEW METHODS NEEDED:
def load_blocks_from_version(self, blocks_data: List[Dict]) -> None
def get_blocks_snapshot(self) -> List[Dict]
def configure_block_from_db(self, block_data: Dict) -> None
```

**Signals to Add**:
```python
block_added = pyqtSignal(str)  # block_name
block_removed = pyqtSignal(int)  # block_index
block_modified = pyqtSignal(int, dict)  # block_index, new_params
blocks_reordered = pyqtSignal(list)  # new_order
```

#### **StrategyInfoPanel** (`src/strategy_builder/ui/strategy_info_panel.py`)
**Current State**: Strategy name, type, description
**Required Changes**:
1. Add version number display
2. Add last saved timestamp
3. Add created_by field
4. Support loading strategy metadata from database

**Methods Requiring Updates**:
```python
# EXISTING METHODS TO MODIFY:
def get_strategy_name(self) -> str
    # No changes needed
    
def set_strategy_name(self, name: str) -> None
    # Add: Emit strategy_name_changed signal
    # Add: Trigger version auto-save

# NEW METHODS NEEDED:
def set_version_info(self, version_data: Dict) -> None
def get_complete_info(self) -> Dict
```

**UI Elements to Add**:
- Version number label
- Last saved timestamp
- Created by field
- Tags field

---

### **LAYER 3: Backtest & Results Panels**

#### **BacktestConfigPanel** (`src/strategy_builder/ui/backtest_config_panel.py`)
**Current State**: Backtest configuration form
**Required Changes**:
1. Add "Load Last Test Results" button
2. Store backtest config to database
3. Load backtest config from version
4. Track config changes

**Methods Requiring Updates**:
```python
# EXISTING METHODS:
def _on_run_clicked(self) -> None
    # Add: Save backtest config to DB before run
    # Add: Save test results to DB after run
    # Add: Save AI recommendations to DB

# NEW METHODS NEEDED:
def _load_last_test_results(self) -> None
def _save_backtest_config_to_db(self) -> None
def load_config_from_db(self, config_data: Dict) -> None
def get_config_snapshot(self) -> Dict
```

**UI Changes**:
- Add "Load Last Test Results" button next to "View Live Results"
- Add results timestamp label

#### **BacktestConfigDialog** (`src/strategy_builder/ui/backtest_config_dialog.py`)
**Current State**: Dialog wrapper for backtest config
**Required Changes**:
1. Connect to backtest result storage
2. Display last test timestamp
3. Show version association

---

### **LAYER 4: Metrics & Recommendations Panels**

#### **MetricsDisplayPanel** (`src/optimizer_v3/ui/metrics_display_panel.py`)
**Current State**: Displays metrics and recommendations
**Required Changes**:
1. Save metrics to database automatically
2. Check for duplicate strategies before AI request
3. Store AI recommendations to database
4. Track recommendation application status

**Methods Requiring Updates**:
```python
# EXISTING METHODS:
def update_metrics(self, metrics: Dict, backtest_complete: bool = False, backtest_results: Optional[Dict] = None) -> None
    # Add: Save metrics to DB
    # Add: Check for duplicate strategy hash
    # Add: Show duplicate dialog if found

def _show_ai_request_preview(self) -> None
    # Add: Check database for previous recommendations
    # Add: Show duplicate warning if found

def _on_ai_request_approved(self, request_data: Dict) -> None
    # Add: Save AI request parameters to DB
    
def _on_recommendations_ready(self, recommendations: List[IntegratedRecommendation]) -> None
    # Add: Save recommendations to DB
    # Add: Link to strategy version

# NEW METHODS NEEDED:
def _check_for_duplicate_strategy(self, strategy_config: Dict) -> Optional[str]  # Returns version_id if duplicate
def _save_metrics_to_db(self, metrics: Dict, version_id: str) -> None
def _save_recommendations_to_db(self, recommendations: List, version_id: str) -> None
def _load_recommendations_from_db(self, version_id: str) -> List[Dict]
```

#### **AIRecommendationsPanel** (`src/optimizer_v3/ui/ai_recommendations_panel.py`)
**Current State**: Displays AI recommendations
**Required Changes**:
1. Load recommendations from database
2. Track which recommendations were applied
3. Show recommendation history
4. Link to strategy versions

**Methods Requiring Updates**:
```python
# NEW METHODS NEEDED:
def load_recommendations_from_db(self, version_id: str) -> None
def _mark_recommendation_applied(self, rec_id: str) -> None
def _show_recommendation_history(self) -> None
def get_applied_recommendations(self) -> List[str]
```

#### **TradesPanel** (`src/optimizer_v3/ui/trades_panel.py`)
**Current State**: Displays trade list
**Required Changes**:
1. Load trades from database version
2. Export trades with version association

**Methods Requiring Updates**:
```python
# NEW METHODS NEEDED:
def load_trades_from_db(self, version_id: str) -> None
def update_trades(self, trades: List[Dict]) -> None  # Modify to accept version_id
```

#### **LiveOutputPanel** (`src/optimizer_v3/ui/live_output_panel.py`)
**Current State**: Live backtest output
**Required Changes**:
1. Save output logs to database
2. Load historical output

---

### **LAYER 5: Data Persistence Layer**

#### **StrategyBuilderOrchestrator** (`src/strategy_builder/integration/strategy_builder_orchestrator.py`)
**Current State**: Centralizes strategy operations
**Required Changes**:
1. Implement hybrid save (JSON + DB)
2. Implement version tracking
3. Auto-increment version numbers
4. Git integration for version control

**Methods Requiring Updates**:
```python
# EXISTING METHODS TO MODIFY:
def save_strategy(self, strategy_data: Dict, filepath: Optional[Path] = None) -> bool
    # Add: Save to database
    # Add: Create strategy version
    # Add: Save blocks separately
    # Add: Git commit
    # Keep: Save to JSON

def load_strategy(self, filepath: Path) -> Optional[StrategyConfiguration]
    # Add: Check database first
    # Add: Load from DB if available
    # Fallback: Load from JSON

def save_config_version(self, message: str) -> bool
    # Add: Create new version in DB
    # Add: Increment version number
    # Add: Git commit with hash
    
# NEW METHODS NEEDED:
def save_strategy_to_db(self, strategy_data: Dict) -> str  # Returns version_id
def load_strategy_from_db(self, strategy_id: str, version_number: Optional[int] = None) -> Dict
def get_strategy_versions(self, strategy_id: str) -> List[Dict]
def create_strategy_snapshot(self) -> str  # Returns strategy hash
def check_for_duplicate_config(self, config_hash: str) -> Optional[str]  # Returns version_id if found
```

#### **Database Manager** (`src/optimizer_v3/database/manager.py`)
**Current State**: Manages optimization database
**Required Changes**:
1. Add strategy version management methods
2. Add AI recommendation storage methods
3. Add test results storage methods
4. Implement version queries

**Methods to Add**:
```python
# STRATEGY VERSION MANAGEMENT:
def create_strategy_version(self, version_data: Dict) -> str
def get_strategy_version(self, version_id: str) -> Optional[Dict]
def get_strategy_versions(self, strategy_id: str) -> List[Dict]
def get_latest_version(self, strategy_id: str) -> Optional[Dict]
def update_strategy_version(self, version_id: str, updates: Dict) -> bool

# BLOCK VERSION MANAGEMENT:
def save_strategy_block_versions(self, version_id: str, blocks: List[Dict]) -> None
def get_strategy_block_versions(self, version_id: str) -> List[Dict]

# AI RECOMMENDATIONS:
def save_ai_recommendations(self, recommendations: List[Dict]) -> None
def get_ai_recommendations_for_version(self, version_id: str) -> List[Dict]
def mark_recommendation_applied(self, recommendation_id: str) -> bool
def get_applied_recommendations(self, version_id: str) -> List[Dict]

# TEST RESULTS:
def save_test_results(self, result_data: Dict) -> str
def get_test_results(self, version_id: str) -> Optional[Dict]
def get_last_test_results(self, strategy_id: str) -> Optional[Dict]

# DUPLICATE DETECTION:
def find_version_by_hash(self, config_hash: str) -> Optional[str]
def get_version_with_recommendations(self, config_hash: str) -> Optional[Dict]
```

---

### **LAYER 6: Utility & Helper Classes**

#### **StrategyRegistry** (`src/utils/Strategy_Builder/strategy_registry.py`)
**Current State**: Manages strategy file storage
**Required Changes**:
1. Integrate with database for hybrid storage
2. Track strategy IDs for database linkage
3. Migration utilities for JSON → DB

**Methods Requiring Updates**:
```python
def save_strategy(self, config: StrategyConfiguration) -> Path
    # Add: Generate or get strategy_id
    # Add: Save to database
    # Keep: Save to JSON
    
def load_strategy(self, strategy_number: int) -> Optional[StrategyConfiguration]
    # Add: Try database first
    # Fallback: Load from JSON
    
# NEW METHODS:
def migrate_strategy_to_db(self, strategy_number: int) -> bool
def get_strategy_id(self, strategy_number: int) -> Optional[str]
```

---

### **LAYER 7: New Dialogs & Windows**

#### **StrategyVersionDialog** (NEW)
**Location**: `src/strategy_builder/ui/strategy_version_dialog.py`
**Purpose**: View and switch between strategy versions
**Implementation**: Detailed in main sprint doc

#### **DuplicateCheckDialog** (NEW)
**Location**: `src/strategy_builder/ui/duplicate_check_dialog.py`
**Purpose**: Warn about duplicate AI analysis
**Implementation**: Detailed in main sprint doc

#### **VersionInfoPanel** (NEW)
**Location**: `src/strategy_builder/ui/version_info_panel.py`
**Purpose**: Display current version metadata
**Components**:
- Version number
- Created date/time
- Created by user
- Version notes
- Tags
- Git commit hash

---

### **LAYER 8: Signals & Communication**

#### **New Signals Required**:
```python
# StrategyBuilderMainWindow:
strategy_saved = pyqtSignal(str)  # strategy_id
strategy_loaded = pyqtSignal(str)  # strategy_id
version_changed = pyqtSignal(str)  # version_id

# StrategyBlocksPanel:
block_added = pyqtSignal(str, dict)  # block_name, block_data
block_removed = pyqtSignal(int)  # block_index
block_modified = pyqtSignal(int, dict)  # block_index, changes

# BacktestConfigPanel:
backtest_started = pyqtSignal(str)  # version_id
backtest_completed = pyqtSignal(str, dict)  # version_id, results
test_results_saved = pyqtSignal(str)  # result_id

# MetricsDisplayPanel:
metrics_saved = pyqtSignal(str, dict)  # version_id, metrics
recommendations_saved = pyqtSignal(str, list)  # version_id, recommendations
duplicate_detected = pyqtSignal(str)  # existing_version_id

# AIRecommendationsPanel:
recommendation_applied = pyqtSignal(str)  # recommendation_id
recommendations_loaded = pyqtSignal(list)  # recommendations
```

---

### **LAYER 9: Data Flow Mapping**

#### **Flow 1: New Strategy Creation**
```
User Creates Strategy
    ↓
StrategyInfoPanel.set_strategy_name()
    ↓
StrategyBlocksPanel.add_block() [multiple times]
    ↓
Orchestrator.save_strategy()
    ↓
├─→ Save to JSON (existing)
└─→ DatabaseManager.create_strategy_version() [NEW]
    ↓
Generate strategy_id and version_id
    ↓
Save blocks to strategy_block_versions table
    ↓
Update UI with version info
```

#### **Flow 2: Run Backtest & Get Recommendations**
```
User Clicks "Run Backtest"
    ↓
BacktestConfigPanel._on_run_clicked()
    ↓
DatabaseManager.save_backtest_config() [NEW]
    ↓
Execute backtest
    ↓
Backtest completes
    ↓
MetricsDisplayPanel.update_metrics()
    ↓
├─→ DatabaseManager.save_test_results() [NEW]
├─→ Calculate strategy config hash
└─→ DatabaseManager.find_version_by_hash() [NEW]
    ↓
If duplicate found:
    ↓
    Show DuplicateCheckDialog
    ↓
    If "Load Previous":
        ↓
        DatabaseManager.get_ai_recommendations_for_version()
        ↓
        Load existing recommendations
    ↓
    If "Run New":
        ↓
        Continue with AI request
Else:
    ↓
    Show AI Request Preview
    ↓
    User approves
    ↓
    Generate AI recommendations
    ↓
    DatabaseManager.save_ai_recommendations() [NEW]
    ↓
    Link to current version_id
```

#### **Flow 3: Load Previous Version**
```
User Clicks "Version History"
    ↓
Show StrategyVersionDialog
    ↓
DatabaseManager.get_strategy_versions()
    ↓
User selects version
    ↓
Orchestrator.load_strategy_from_db()
    ↓
├─→ Load strategy data
├─→ Load blocks data
├─→ Load backtest config
├─→ Load test results
└─→ Load AI recommendations
    ↓
Update all panels:
    ├─→ StrategyInfoPanel.set_version_info()
    ├─→ StrategyBlocksPanel.load_blocks_from_version()
    ├─→ BacktestConfigPanel.load_config_from_db()
    ├─→ MetricsDisplayPanel.update_metrics()
    ├─→ TradesPanel.load_trades_from_db()
    └─→ AIRecommendationsPanel.load_recommendations_from_db()
```

#### **Flow 4: Apply Recommendations**
```
User selects and applies recommendations
    ↓
MetricsDisplayPanel._apply_selected_recommendations()
    ↓
For each recommendation:
    ├─→ Apply changes to strategy
    └─→ DatabaseManager.mark_recommendation_applied() [NEW]
    ↓
Orchestrator.save_config_version()
    ↓
DatabaseManager.create_strategy_version()
    ↓
New version created with applied changes
    ↓
If auto-retest enabled:
    ↓
    Trigger new backtest
    ↓
    Compare results with previous version
```

---

### **LAYER 10: Configuration & Environment**

#### **.env Updates Required**:
```bash
# Database connection (existing)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=optimizer_v3
POSTGRES_USER=optimizer_admin
POSTGRES_PASSWORD=secure_password

# Version tracking (NEW)
STRATEGY_AUTO_SAVE=true
VERSION_AUTO_INCREMENT=true
GIT_INTEGRATION_ENABLED=true
```

#### **settings.py Updates** (`src/strategy_builder/utils/settings.py`):
```python
# Add version tracking settings
STRATEGY_AUTO_SAVE = config('STRATEGY_AUTO_SAVE', default=True, cast=bool)
VERSION_AUTO_INCREMENT = config('VERSION_AUTO_INCREMENT', default=True, cast=bool)
GIT_INTEGRATION_ENABLED = config('GIT_INTEGRATION_ENABLED', default=True, cast=bool)
```

---

### **LAYER 11: Testing Coverage Required**

#### **Unit Tests Needed**:
1. `tests/database/test_strategy_versions.py` - Strategy version CRUD
2. `tests/database/test_ai_recommendations.py` - AI recommendation storage
3. `tests/database/test_duplicate_detection.py` - Hash calculation and duplicate finding
4. `tests/database/test_test_results.py` - Test results storage and retrieval
5. `tests/ui/test_version_dialog.py` - Version dialog functionality
6. `tests/ui/test_duplicate_dialog.py` - Duplicate check dialog
7. `tests/integration/test_hybrid_storage.py` - JSON + DB workflow
8. `tests/integration/test_version_switching.py` - Version loading
9. `tests/integration/test_recommendation_flow.py` - End-to-end recommendation flow

#### **Integration Tests Needed**:
1. Complete flow: Create → Test → Get Recommendations → Apply → Retest
2. Version switching with complete data restoration
3. Duplicate detection with AI cost prevention
4. Hybrid storage consistency (JSON ↔ DB)

---

## 🔍 FINAL IMPACTED COMPONENTS SUMMARY

### **Critical Path Components** (Must Implement):
1. ✅ Database schema extension (3 new tables)
2. ✅ DatabaseManager methods (20+ new methods)
3. ✅ StrategyBuilderOrchestrator hybrid save/load
4. ✅ MetricsDisplayPanel duplicate detection
5. ✅ StrategyVersionDialog (new)
6. ✅ DuplicateCheckDialog (new)
7. ✅ BacktestConfigPanel "Load Last Test" button

### **High Priority Components** (Should Implement):
8. StrategyBlocksPanel version loading
9. StrategyInfoPanel version display
10. AIRecommendationsPanel database integration
11. TradesPanel version loading
12. Version signals and communication

### **Medium Priority Components** (Nice to Have):
13. VersionInfoPanel (new status widget)
14. Git integration for version control
15. Tag system for version organization
16. Version comparison view
17. Recommendation history viewer

### **Low Priority Components** (Future Enhancement):
18. Migration utilities (JSON → DB bulk import)
19. Version export/import
20. Collaborative versioning features
21. Version branching/merging

## ⚡ PERFORMANCE CONSIDERATIONS

1. **Indexes**
   - Optimize for common queries
   - Cover all search patterns
   - Regular ANALYZE maintenance

2. **Caching**
   - Cache active strategy results
   - Cache recent recommendations
   - Implement LRU cache system

3. **Batch Operations**
   - Bulk insert test results
   - Batch update recommendations
   - Transaction management

## 🧪 TESTING STRATEGY

1. **Unit Tests**
   - Database schema validation
   - Version tracking accuracy
   - Duplicate detection logic
   - Results loading system

2. **Integration Tests**
   - End-to-end workflow
   - UI component interaction
   - Database performance
   - Version control integration

3. **Performance Tests**
   - Large dataset handling
   - Concurrent operations
   - Cache effectiveness

## 📅 TIMELINE

1. **Days 1-2: Database Extension & Version Management**
   - Create new tables
   - Implement migrations
   - Add version tracking
   - Add version switching UI
   - Implement version loading system
   - Create new tables
   - Implement migrations
   - Add version tracking

2. **Days 3-4: Core Implementation**
   - Duplicate detection system
   - Results loading functionality
   - Version tracking integration

3. **Days 5-6: UI Integration**
   - Add new UI components
   - Implement workflows
   - Connect to database

4. **Day 7: Testing & Documentation**
   - Run all test suites
   - Update documentation
   - Performance validation

## 📝 SUCCESS CRITERIA

1. ✓ Database schema extended and validated
2. ✓ Version switching system operational
3. ✓ Version history accessible and functional
2. ✓ Duplicate detection working correctly
3. ✓ "Load Last Test" functionality operational
4. ✓ Version tracking accurate and reliable
5. ✓ All tests passing
6. ✓ Performance metrics met
7. ✓ Documentation updated

## 🔄 ROLLBACK PLAN

1. **Database**
   - Keep backup of old schema
   - Version migration scripts
   - Data export capability

2. **Code**
   - Git version control
   - Feature flags
   - Gradual rollout

3. **Data**
   - Regular backups
   - Transaction logging
   - Recovery procedures

## 📚 DOCUMENTATION UPDATES

1. Update database guide
2. Add version tracking guide
3. Update UI documentation
4. Add migration guide
5. Update testing documentation

## 🎯 DEFINITION OF DONE

1. All new tables created and validated
2. Duplicate detection system operational
3. "Load Last Test" button functional
4. Version tracking system working
5. All tests passing
6. Documentation updated
7. Code reviewed and approved
8. Performance metrics met

**Status**: 📋 Ready for Implementation  
**Next Steps**: Begin database extension phase