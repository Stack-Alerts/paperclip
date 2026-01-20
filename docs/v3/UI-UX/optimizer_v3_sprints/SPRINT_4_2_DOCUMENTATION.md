# SPRINT 4.2: DOCUMENTATION
**User Guides, API Docs, Architecture, Tutorials**

**Duration**: 2 days  
**Tasks**: 7  
**Dependencies**: Sprint 4.1 complete  
**Status**: ☐ Not Started

**Integration Documents**:
1. **[OPTIMIZER_V3_UI_STYLING_GUIDE.md](../OPTIMIZER_V3_UI_STYLING_GUIDE.md)**
   - Central stylesheet enforcement
   - Zero hardcoded styles
   - Style constants and helpers
   - Dark theme support
   - Style validation
   - Pre-commit hooks

---

## 📋 SPRINT OVERVIEW

**Purpose**: Complete all documentation:
- User guide
- API documentation
- Architecture guide
- Tutorial videos
- FAQ document
- Troubleshooting guide

---

## ✅ TASK CHECKLIST

- [ ] 4.2.1 User guide
- [ ] 4.2.2 API documentation
- [ ] 4.2.3 Architecture guide
- [ ] 4.2.4 Tutorial videos
- [ ] 4.2.5 FAQ document
- [ ] 4.2.6 Troubleshooting guide
- [ ] 4.2.7 Sprint sign-off

---

## 📝 TASK DETAILS

### **Environment Configuration**
**Duration**: 1 hour  
**Dependencies**: Sprint 4.1 complete

**Implementation**:
```bash
# Add to .env file

# Documentation Generation
DOC_AUTO_GENERATE=true  # auto-generate docs
DOC_OUTPUT_PATH=docs/v3/optimizer  # output directory
DOC_INCLUDE_DIAGRAMS=true  # include diagrams
DOC_INCLUDE_EXAMPLES=true  # include examples
DOC_STYLE_CHECK=true  # check doc style
DOC_LINK_CHECK=true  # verify documentation links

# API Documentation
API_DOC_STYLE=google  # docstring style
API_DOC_PRIVATE=false  # include private members
API_DOC_INHERITED=true  # include inherited members
API_DOC_UNDOC_MEMBERS=false  # include undocumented members
API_DOC_COVERAGE_MIN=100  # minimum coverage percent

# Code Examples
EXAMPLE_MAX_LENGTH=50  # maximum lines per example
EXAMPLE_CHECK_SYNTAX=true  # verify example syntax
EXAMPLE_RUN_TESTS=true  # run example code tests
EXAMPLE_TIMEOUT=30  # seconds per example test
EXAMPLE_PYTHON_VERSION=3.9  # Python version for examples

# Tutorial Videos
VIDEO_MAX_LENGTH=600  # seconds per video
VIDEO_MIN_QUALITY=1080  # minimum resolution
VIDEO_FORMAT=mp4  # video format
VIDEO_UPLOAD_PATH=docs/v3/optimizer/videos  # video storage
VIDEO_BACKUP=true  # backup videos

# Document Validation
DOC_SPELLCHECK=true  # check spelling
DOC_GRAMMAR_CHECK=true  # check grammar
DOC_LINK_TIMEOUT=30  # seconds for link check
DOC_MIN_WORDS=50  # minimum words per section
DOC_MAX_WORDS=500  # maximum words per section

# Style Guide Validation
STYLE_CHECK_SPACING=true  # check spacing
STYLE_CHECK_IMPORTS=true  # check import order
STYLE_CHECK_NAMING=true  # check naming conventions
STYLE_CHECK_COMMENTS=true  # check comment style
STYLE_MAX_LINE_LENGTH=80  # maximum line length

# FAQ Generation
FAQ_MIN_QUESTIONS=20  # minimum questions
FAQ_AUTO_UPDATE=true  # auto-update from issues
FAQ_CATEGORIES=["general","performance","troubleshooting"]  # FAQ categories
FAQ_UPDATE_INTERVAL=86400  # seconds between updates
FAQ_BACKUP=true  # backup FAQ document

# Resource Management
RESOURCE_MAX_MEMORY=4096  # MB maximum memory usage
RESOURCE_MAX_CPU=90  # maximum CPU usage
RESOURCE_CHECK_INTERVAL=60  # seconds between checks
RESOURCE_CLEANUP_ENABLED=true  # auto cleanup
RESOURCE_BACKUP_ENABLED=true  # backup before changes

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
LOG_PATH=logs/documentation
LOG_ROTATION=5  # number of files to keep
LOG_MAX_SIZE=10  # MB per log file
```

**Configuration Loading**:
```python
from dotenv import load_dotenv
import os
from typing import Dict, Any

def get_doc_config() -> Dict[str, Any]:
    """Load documentation configuration from environment"""
    load_dotenv()
    
    return {
        'generation': {
            'auto_generate': os.getenv('DOC_AUTO_GENERATE').lower() == 'true',
            'output_path': os.getenv('DOC_OUTPUT_PATH'),
            'include_diagrams': os.getenv('DOC_INCLUDE_DIAGRAMS').lower() == 'true',
            'include_examples': os.getenv('DOC_INCLUDE_EXAMPLES').lower() == 'true',
            'style_check': os.getenv('DOC_STYLE_CHECK').lower() == 'true',
            'link_check': os.getenv('DOC_LINK_CHECK').lower() == 'true'
        },
        'api': {
            'doc_style': os.getenv('API_DOC_STYLE'),
            'private': os.getenv('API_DOC_PRIVATE').lower() == 'true',
            'inherited': os.getenv('API_DOC_INHERITED').lower() == 'true',
            'undoc_members': os.getenv('API_DOC_UNDOC_MEMBERS').lower() == 'true',
            'coverage_min': int(os.getenv('API_DOC_COVERAGE_MIN'))
        },
        'examples': {
            'max_length': int(os.getenv('EXAMPLE_MAX_LENGTH')),
            'check_syntax': os.getenv('EXAMPLE_CHECK_SYNTAX').lower() == 'true',
            'run_tests': os.getenv('EXAMPLE_RUN_TESTS').lower() == 'true',
            'timeout': int(os.getenv('EXAMPLE_TIMEOUT')),
            'python_version': os.getenv('EXAMPLE_PYTHON_VERSION')
        },
        'videos': {
            'max_length': int(os.getenv('VIDEO_MAX_LENGTH')),
            'min_quality': int(os.getenv('VIDEO_MIN_QUALITY')),
            'format': os.getenv('VIDEO_FORMAT'),
            'upload_path': os.getenv('VIDEO_UPLOAD_PATH'),
            'backup': os.getenv('VIDEO_BACKUP').lower() == 'true'
        },
        'validation': {
            'spellcheck': os.getenv('DOC_SPELLCHECK').lower() == 'true',
            'grammar_check': os.getenv('DOC_GRAMMAR_CHECK').lower() == 'true',
            'link_timeout': int(os.getenv('DOC_LINK_TIMEOUT')),
            'min_words': int(os.getenv('DOC_MIN_WORDS')),
            'max_words': int(os.getenv('DOC_MAX_WORDS'))
        },
        'style': {
            'check_spacing': os.getenv('STYLE_CHECK_SPACING').lower() == 'true',
            'check_imports': os.getenv('STYLE_CHECK_IMPORTS').lower() == 'true',
            'check_naming': os.getenv('STYLE_CHECK_NAMING').lower() == 'true',
            'check_comments': os.getenv('STYLE_CHECK_COMMENTS').lower() == 'true',
            'max_line_length': int(os.getenv('STYLE_MAX_LINE_LENGTH'))
        },
        'faq': {
            'min_questions': int(os.getenv('FAQ_MIN_QUESTIONS')),
            'auto_update': os.getenv('FAQ_AUTO_UPDATE').lower() == 'true',
            'categories': os.getenv('FAQ_CATEGORIES').strip('[]').split(','),
            'update_interval': int(os.getenv('FAQ_UPDATE_INTERVAL')),
            'backup': os.getenv('FAQ_BACKUP').lower() == 'true'
        },
        'resources': {
            'max_memory': int(os.getenv('RESOURCE_MAX_MEMORY')),
            'max_cpu': int(os.getenv('RESOURCE_MAX_CPU')),
            'check_interval': int(os.getenv('RESOURCE_CHECK_INTERVAL')),
            'cleanup_enabled': os.getenv('RESOURCE_CLEANUP_ENABLED').lower() == 'true',
            'backup_enabled': os.getenv('RESOURCE_BACKUP_ENABLED').lower() == 'true'
        },
        'logging': {
            'level': os.getenv('LOG_LEVEL'),
            'format': os.getenv('LOG_FORMAT'),
            'path': os.getenv('LOG_PATH'),
            'rotation': int(os.getenv('LOG_ROTATION')),
            'max_size': int(os.getenv('LOG_MAX_SIZE'))
        }
    }
```

### **Task 4.2.1: User Guide & UI Style Documentation**
**Duration**: 4 hours  
**Dependencies**: Sprint 4.1 complete

**Deliverables**: 
1. `docs/v3/optimizer/COMPLETE_USER_GUIDE.md`
2. `docs/v3/optimizer/UI_STYLE_GUIDE.md`

**Contents**:
- Getting started
- Core optimization workflow
- Automated trainer usage
- Signal intelligence dashboard
- ML strategy generation
- Advanced features
- Best practices
- UI styling guidelines
  - Component styling from styles.py
  - Dark theme compatibility
  - Visual consistency
  - Memory efficiency
  - Style validation

**UI Style Guide Example**:
```python
# Example of proper UI styling
from src.strategy_builder.ui.styles import (
    WINDOW_STYLE,
    PANEL_STYLE,
    CHART_STYLE,
    TABLE_STYLE,
    SPACING_UNIT,
    create_font,
    PRIMARY_COLOR,
    SECONDARY_COLOR
)

class OptimizedComponent(QWidget):
    """Example of properly styled component"""
    
    def __init__(self):
        super().__init__()
        self.setStyleSheet(WINDOW_STYLE)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(SPACING_UNIT)
        
        # Panel with consistent styling
        panel = QWidget()
        panel.setStyleSheet(PANEL_STYLE)
        
        # Table with proper styling
        table = QTableWidget()
        table.setStyleSheet(TABLE_STYLE)
        table.setFont(create_font())
        
        # Chart with theme support
        chart = PlotlyChart()
        chart.setStyleSheet(CHART_STYLE)
        
        layout.addWidget(panel)
        layout.addWidget(table)
        layout.addWidget(chart)
        self.setLayout(layout)
```

**Acceptance Criteria**:
- [ ] Complete guide written
- [ ] Screenshots included
- [ ] UI styling guide complete
- [ ] Style examples provided
- [ ] Dark theme documentation
- [ ] Style validation guide
- [ ] Reviewed by team

**Sign-off**: ☐ Developer ☐ Lead ☐ Tech Writer ☐ UI Designer

---

### **Task 4.2.2: API Documentation**
**Duration**: 3 hours  
**Dependencies**: 4.2.1

**Deliverable**: `docs/v3/optimizer/API_COMPLETE_REFERENCE.md`

**Contents**:
- All public APIs
- Method signatures
- Parameters
- Return types
- Code examples

**Acceptance Criteria**:
- [ ] All APIs documented

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 4.2.3: Architecture Guide**
**Duration**: 3 hours  
**Dependencies**: 4.2.2

**Deliverable**: `docs/v3/optimizer/ARCHITECTURE_COMPLETE.md`

**Contents**:
- System architecture
- Component interactions
- Data flows
- Database schema
- Design decisions

**Acceptance Criteria**:
- [ ] Architecture documented

**Sign-off**: ☐ Developer ☐ Lead ☐ Architect

---

### **Task 4.2.3A: NautilusTrader Integration Guide**
**Duration**: 4 hours  
**Dependencies**: 4.2.3

**Deliverable**: `docs/v3/optimizer/NAUTILUS_INTEGRATION_GUIDE.md`

**Contents**:
```markdown
# NautilusTrader Integration Guide
**Institutional-Grade Type System & Risk Management**

## 1. Type System Integration

### Core Types
```python
from nautilus_trader.model.objects import Quantity, Price, Money
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.enums import OrderSide, PositionSide

# Always use NautilusTrader types for financial values:
position_size = Quantity('0.1')      # NOT float
entry_price = Price('50000')         # NOT float
pnl = Money('500', 'USD')           # NOT float
```

### Type Conversion
```python
# Converting from strings/floats
quantity = Quantity(str(0.1))
price = Price(str(50000))
money = Money(str(500), 'USD')

# Converting to strings for storage
quantity_str = quantity.to_string()
price_str = price.to_string()
money_str = money.to_string()
```

### Database Storage
```python
class NautilusTradeEvent(Base):
    """Store NautilusTrader types as strings"""
    quantity = Column(String)  # Store as string
    price = Column(String)     # Store as string
    money = Column(String)     # Store as string
    
    @property
    def quantity_obj(self) -> Quantity:
        return Quantity.from_string(self.quantity)
```

## 2. Risk Management Integration

### Position Limits
```python
MAX_POSITION_SIZE = Quantity('1.0')    # 1.0 BTC
MIN_POSITION_SIZE = Quantity('0.001')  # 0.001 BTC

def validate_position_size(quantity: Quantity):
    if quantity < MIN_POSITION_SIZE:
        raise ValueError(f"Below minimum: {quantity}")
    if quantity > MAX_POSITION_SIZE:
        raise ValueError(f"Exceeds maximum: {quantity}")
```

### Loss Limits
```python
DAILY_LOSS_LIMIT = Money('500', 'USD')  # $500/day

def validate_daily_loss(current_loss: Money):
    if current_loss <= -DAILY_LOSS_LIMIT:
        raise ValueError(f"Daily loss limit reached: {current_loss}")
```

### Stop Loss Calculation
```python
STOP_LOSS_PERCENT = Decimal('0.02')  # 2%

def calculate_stop_loss(entry_price: Price, side: OrderSide) -> Price:
    if side == OrderSide.BUY:
        return Price(str(entry_price.as_decimal() * (1 - STOP_LOSS_PERCENT)))
    else:
        return Price(str(entry_price.as_decimal() * (1 + STOP_LOSS_PERCENT)))
```

## 3. Performance Metrics

### PnL Calculation
```python
def calculate_pnl(trades: List[dict]) -> Money:
    total = Money('0', 'USD')
    for trade in trades:
        total += trade['pnl']  # Money type arithmetic
    return total
```

### Position Tracking
```python
class PositionTracker:
    def __init__(self):
        self.current_position = Quantity('0')
        self.entry_price = Price('0')
    
    def update(self, quantity: Quantity, price: Price):
        self.current_position += quantity  # Quantity arithmetic
        self.entry_price = price
```

## 4. Best Practices

### NEVER Use Floating Point
❌ **Wrong**:
```python
position = 0.1
price = 50000.0
pnl = 500.0
```

✅ **Correct**:
```python
position = Quantity('0.1')
price = Price('50000')
pnl = Money('500', 'USD')
```

### ALWAYS Use Type Validation
```python
def validate_trade_input(event: dict):
    assert isinstance(event['quantity'], Quantity)
    assert isinstance(event['price'], Price)
    assert isinstance(event['pnl'], Money)
```

### ALWAYS Use Safe Arithmetic
❌ **Wrong**:
```python
total_pnl = sum(t['pnl'] for t in trades)  # Float arithmetic!
```

✅ **Correct**:
```python
total_pnl = Money('0', 'USD')
for trade in trades:
    total_pnl += trade['pnl']  # Money arithmetic
```

## 5. Testing Guidelines

### Type Conversion Tests
```python
def test_type_conversion():
    quantity = Quantity('0.1')
    assert quantity.to_string() == '0.1'
    
    price = Price('50000')
    assert price.to_string() == '50000'
```

### Risk Management Tests
```python
def test_position_limits():
    with pytest.raises(ValueError):
        validate_position_size(Quantity('2.0'))  # Too large
        
    with pytest.raises(ValueError):
        validate_position_size(Quantity('0.0001'))  # Too small
```

### Database Tests
```python
def test_database_roundtrip():
    event = NautilusTradeEvent(quantity='0.1')
    assert isinstance(event.quantity_obj, Quantity)
    assert event.quantity_obj.to_string() == '0.1'
```

## 6. Common Pitfalls

### Mixing Types
❌ **Wrong**:
```python
def calculate_value(quantity: float, price: Price):
    return quantity * price  # Type mismatch!
```

✅ **Correct**:
```python
def calculate_value(quantity: Quantity, price: Price) -> Money:
    return Money(str(quantity.as_decimal() * price.as_decimal()), 'USD')
```

### String Conversion
❌ **Wrong**:
```python
quantity_str = str(quantity)  # Don't use str()
```

✅ **Correct**:
```python
quantity_str = quantity.to_string()  # Use to_string()
```

### Database Storage
❌ **Wrong**:
```python
quantity = Column(Float)  # Don't store as float
```

✅ **Correct**:
```python
quantity = Column(String)  # Store as string
```

## 7. Troubleshooting

### Common Issues
1. **TypeError**: Mixing NautilusTrader types with floats
   - Solution: Convert all values to proper types
   
2. **ValueError**: Invalid string format
   - Solution: Use proper string formatting (e.g., '0.1' not '0,1')
   
3. **AssertionError**: Wrong type used
   - Solution: Validate all inputs are correct NautilusTrader types

### Debug Tips
1. Enable type checking:
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from nautilus_trader.model.objects import Quantity
```

2. Add runtime type validation:
```python
def validate_types(event: dict):
    for key, expected_type in TYPE_MAP.items():
        assert isinstance(event[key], expected_type)
```

3. Log type information:
```python
logger.debug(f"Type check: {type(quantity)}")
```

## 8. Performance Considerations

### Memory Usage
- NautilusTrader types are more memory-efficient than floats
- String storage in database is optimal for precision
- Use bulk operations for large datasets

### Optimization Tips
1. Cache converted types:
```python
@lru_cache(maxsize=1000)
def get_quantity(value: str) -> Quantity:
    return Quantity(value)
```

2. Batch database operations:
```python
with db.session_scope() as session:
    session.bulk_insert_mappings(NautilusTradeEvent, events)
```

3. Use appropriate indexes:
```sql
CREATE INDEX idx_trade_events_quantity 
ON nautilus_trade_events(quantity);
```

## 9. Migration Guide

### From Float-Based System
1. Identify all float usage:
```bash
grep -r "float" src/
```

2. Replace with NautilusTrader types:
```python
# Before
position = 0.1

# After
position = Quantity('0.1')
```

3. Update database schema:
```sql
ALTER TABLE trades 
ALTER COLUMN quantity TYPE VARCHAR,
ALTER COLUMN price TYPE VARCHAR;
```

4. Convert existing data:
```python
def migrate_data():
    for row in db.query(Trade).all():
        row.quantity = str(row.quantity)
        row.price = str(row.price)
    db.commit()
```

## 10. Support Resources

### Documentation
- NautilusTrader API: https://nautilustrader.io/docs/latest/
- Type System: https://nautilustrader.io/docs/latest/api/types/
- Risk Management: https://nautilustrader.io/docs/latest/api/risk/

### Testing Resources
- Test data generators
- Mock trade events
- Validation utilities

### Contact
- Slack: #nautilus-integration
- Email: support@nautilustrader.io
```

**Acceptance Criteria**:
- [ ] Type system integration documented
- [ ] Risk management integration documented
- [ ] Performance metrics integration documented
- [ ] Best practices documented
- [ ] Testing guidelines documented
- [ ] Common pitfalls documented
- [ ] Troubleshooting guide included
- [ ] Migration guide included
- [ ] Code examples for all sections
- [ ] Reviewed by NautilusTrader team

**Sign-off**: ☐ Developer ☐ Lead ☐ NautilusTrader Expert

---

### **Task 4.2.4: Tutorial Videos**
**Duration**: 4 hours  
**Dependencies**: 4.2.3

**Deliverables**:
- How to optimize a strategy (5min)
- How to train building blocks (8min)
- Understanding signal intelligence (6min)
- Generating strategies with ML (7min)

**Acceptance Criteria**:
- [ ] 4 videos recorded
- [ ] Uploaded to documentation

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 4.2.5: FAQ Document**
**Duration**: 2 hours  
**Dependencies**: 4.2.4

**Deliverable**: `docs/v3/optimizer/FAQ.md`

**Contents**:
- Common questions
- Troubleshooting
- Performance tips

**Acceptance Criteria**:
- [ ] 20+ FAQs documented

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 4.2.6: Troubleshooting Guide**
**Duration**: 2 hours  
**Dependencies**: 4.2.5

**Deliverable**: `docs/v3/optimizer/TROUBLESHOOTING.md`

**Contents**:
- Common errors
- Solutions
- Debug procedures

**Acceptance Criteria**:
- [ ] Complete guide

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 4.2.7: Sprint Sign-off**
**Duration**: 1 hour  
**Dependencies**: 4.2.6

**Final Checklist**:
- [ ] All 7 documentation tasks complete
- [ ] All documents reviewed
- [ ] Videos uploaded
- [ ] Documentation accessible

**Sign-off**: ☐ Developer ☐ Lead ☐ Tech Writer

---

## 🎯 SPRINT SIGN-OFF

**Complete When**:
- [ ] All 7 tasks done
- [ ] All documentation complete
- [ ] Reviewed and approved

**Sign-off**: ☐ Developer ☐ Lead ☐ Tech Writer

**Next Sprint**: `SPRINT_4_3_PRODUCTION.md` (FINAL SPRINT)
