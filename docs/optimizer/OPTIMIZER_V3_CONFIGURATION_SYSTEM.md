# OPTIMIZER V3 - CONFIGURATION SYSTEM
**Configuration Management & Runtime Behavior**

**Date**: 2026-01-20  
**Status**: 🎨 DESIGN PHASE  
**Purpose**: Define how configurations work during test execution and optimizations

## 🔄 CONFIGURATION HIERARCHY

1. **Default Values** (.env.example)
   - Base configuration
   - Documentation of all options
   - Safe default values

2. **User Configuration** (.env)
   - User's customized settings
   - Overrides defaults
   - Persists between sessions

3. **Runtime Configuration** (Memory)
   - Active during optimization
   - Can be temporarily modified
   - Reverts to .env on restart

## 🎯 CONFIGURATION CATEGORIES

### 1. Block Optimization Settings
```ini
# Maximum combinations to test
BLOCK_MAX_COMBINATIONS=100

# Minimum impact threshold (0.01-1.0)
BLOCK_MIN_IMPACT=0.01

# Performance requirements
PERF_MIN_IMPROVEMENT=0.05
PERF_MIN_WIN_RATE=0.55
```

### 2. Signal Logic Settings
```ini
# Maximum signals per strategy
LOGIC_MAX_SIGNALS=5

# Minimum required trades
LOGIC_MIN_TRADES=30

# Timing windows
TIMING_MIN_WINDOW=5
TIMING_MAX_WINDOW=30
TIMING_STEP=5
```

### 3. Market Condition Settings
```ini
# Session times (UTC)
SESSION_ASIA_START=0
SESSION_ASIA_END=8
SESSION_LONDON_START=8
SESSION_LONDON_END=16
SESSION_NY_START=13
SESSION_NY_END=21

# Volatility thresholds
VOL_LOW_THRESHOLD=0.5
VOL_HIGH_THRESHOLD=2.0
```

### 4. System Integration Settings
```ini
# Threading
SYSTEM_MAX_THREADS=8
SYSTEM_TIMEOUT=7200

# Memory limits
MEMORY_LIMIT_GB=16
CACHE_SIZE_MB=512

# Database
DB_MAX_CONNECTIONS=10
DB_TIMEOUT=30
```

### 5. Security Settings
```ini
# Security scanning
SECURITY_SCAN_ENABLED=true
SECURITY_MIN_SCORE=90

# Risk limits
MAX_POSITION_SIZE=1.0
MIN_POSITION_SIZE=0.001
STOP_LOSS_PERCENT=2.0
```

### 6. Monitoring Settings
```ini
# Monitoring
MONITOR_ENABLED=true
MONITOR_INTERVAL=60

# Alerts
ALERT_EMAIL=user@example.com
ALERT_SLACK_WEBHOOK=https://hooks.slack.com/...
```

## 🔄 RUNTIME BEHAVIOR

### During Test Execution

1. **Configuration Loading**
```python
def load_config():
    # 1. Load defaults
    config = load_defaults()
    
    # 2. Override with .env
    config.update(load_env_file())
    
    # 3. Apply runtime modifications
    config.update(runtime_overrides)
    
    return config
```

2. **Parameter Validation**
```python
def validate_config(config):
    # Check all required params exist
    assert all(required_params)
    
    # Validate ranges
    assert 0 < config.BLOCK_MIN_IMPACT <= 1.0
    assert 0 < config.PERF_MIN_WIN_RATE <= 1.0
    
    # Check dependencies
    assert config.TIMING_MIN_WINDOW < config.TIMING_MAX_WINDOW
```

3. **Runtime Modifications**
```python
def modify_runtime_config(param, value):
    # Store original
    original = current_config[param]
    
    try:
        # Apply change
        current_config[param] = value
        validate_config(current_config)
        
    except ValidationError:
        # Revert on error
        current_config[param] = original
        raise
```

### During Optimization

1. **Parameter Space Generation**
```python
def generate_param_space():
    space = []
    
    # Timing windows
    for window in range(
        config.TIMING_MIN_WINDOW,
        config.TIMING_MAX_WINDOW + 1,
        config.TIMING_STEP
    ):
        space.append({
            'param': 'timing_window',
            'value': window
        })
    
    # Other parameters...
    return space
```

2. **Configuration Snapshots**
```python
def create_config_snapshot():
    return {
        'timestamp': datetime.now(),
        'config': deepcopy(current_config),
        'results': current_results
    }
```

3. **Results Association**
```python
def store_results(config_id, results):
    db.execute("""
        INSERT INTO optimization_results
        (config_id, sharpe, win_rate, pnl)
        VALUES (?, ?, ?, ?)
    """, (config_id, results.sharpe, results.win_rate, results.pnl))
```

## 🖥️ UI INTEGRATION

### System Configuration Window

1. **Access**
   - Via Tools > System Configuration
   - Keyboard shortcut: Ctrl+Shift+S

2. **Layout**
   - Tab-based interface
   - GroupBox organization
   - Real-time validation

3. **Features**
   - Load/Save configurations
   - Import/Export settings
   - Reset to defaults
   - Validation feedback

### Configuration Editor

1. **Parameter Groups**
```python
class ConfigGroup(QGroupBox):
    def __init__(self, title):
        super().__init__(title)
        self.setStyleSheet(get_groupbox_header_stylesheet())
        
        # Add form layout
        self.form = QFormLayout()
        self.setLayout(self.form)
        
        # Add parameter widgets
        self.add_parameters()
    
    def add_parameters(self):
        for param in self.get_parameters():
            widget = self.create_widget(param)
            self.form.addRow(param.label, widget)
```

2. **Parameter Widgets**
```python
def create_widget(self, param):
    if param.type == 'int':
        widget = QSpinBox()
        widget.setRange(param.min, param.max)
        widget.setValue(param.default)
        widget.setStyleSheet(get_spinbox_button_stylesheet())
        
    elif param.type == 'float':
        widget = QDoubleSpinBox()
        widget.setRange(param.min, param.max)
        widget.setSingleStep(param.step)
        widget.setValue(param.default)
        
    elif param.type == 'bool':
        widget = QCheckBox()
        widget.setChecked(param.default)
        widget.setStyleSheet(get_checkbox_style())
        
    return widget
```

3. **Validation**
```python
def validate_input(self):
    try:
        # Get all values
        values = self.get_values()
        
        # Validate
        validate_config(values)
        
        # Show success
        self.status_label.setText("Valid configuration")
        self.status_label.setStyleSheet(
            get_label_style('success')
        )
        
        return True
        
    except ValidationError as e:
        # Show error
        self.status_label.setText(str(e))
        self.status_label.setStyleSheet(
            get_label_style('error')
        )
        
        return False
```

## 📊 CONFIGURATION STORAGE

### 1. Environment File (.env)
- Primary configuration storage
- Human-readable/editable
- Version controlled (.env.example)
- Loaded at startup

### 2. Database
- Historical configurations
- Optimization results
- Performance metrics
- Audit trail

### 3. Memory Cache
- Runtime modifications
- Temporary overrides
- Quick access
- Reset on restart

## 🔒 SECURITY CONSIDERATIONS

1. **Parameter Validation**
   - Range checking
   - Type validation
   - Dependency verification
   - Prevent invalid combinations

2. **Access Control**
   - Read-only defaults
   - User-specific .env
   - Runtime isolation

3. **Audit Trail**
   - Configuration changes logged
   - User attribution
   - Timestamp tracking
   - Change reasons

## 📈 MONITORING & ALERTS

1. **Configuration Changes**
   - Track modifications
   - Alert on critical changes
   - Record user actions

2. **Performance Impact**
   - Monitor metric changes
   - Alert on degradation
   - Track correlations

3. **System Health**
   - Resource usage
   - Error rates
   - Response times

## 🎯 IMPLEMENTATION CHECKLIST

1. **Core System**
   - [ ] Configuration loader
   - [ ] Validation system
   - [ ] Runtime manager
   - [ ] Storage interface

2. **UI Components**
   - [ ] System Configuration window
   - [ ] Parameter editors
   - [ ] Validation feedback
   - [ ] Status indicators

3. **Database Integration**
   - [ ] Schema creation
   - [ ] Migration system
   - [ ] Query interface
   - [ ] Results storage

4. **Security Features**
   - [ ] Access control
   - [ ] Audit logging
   - [ ] Validation rules
   - [ ] Error handling

5. **Monitoring**
   - [ ] Metric collection
   - [ ] Alert system
   - [ ] Dashboard
   - [ ] Reports

---

**Status**: 🎨 Ready for implementation  
**Next Step**: Begin with System Configuration window implementation  
**Priority**: High - Required for Optimizer v3 functionality
