# PARALLEL EXECUTOR DESIGN
**ProcessPoolExecutor-Based Parallel Execution System**

**Date**: 2026-01-20  
**Status**: ✅ COMPLETE  
**Author**: BTC_Engine_v3 Development Team  
**Version**: 1.0

---

## 📋 OVERVIEW

This document describes the parallel execution architecture for Optimizer V3, enabling simultaneous execution of multiple backtest configurations with robust error handling, progress tracking, and resource management.

---

## 🎯 DESIGN GOALS

1. **Parallel Execution**: Run multiple backtest configs simultaneously
2. **Resource Management**: Monitor and limit CPU/memory usage
3. **Error Recovery**: Handle failures gracefully without crashing batch
4. **Progress Tracking**: Real-time updates with accurate ETA
5. **Checkpointing**: Save/resume state for long-running jobs
6. **Process Monitoring**: Detect and restart stuck workers
7. **Type Safety**: Full NautilusTrader type validation

---

## 🏗️ ARCHITECTURE COMPARISON

### **ProcessPoolExecutor vs ThreadPoolExecutor**

#### **ProcessPoolExecutor (SELECTED)**
✅ **Advantages**:
- True parallelism (bypasses Python GIL)
- Isolated memory spaces (no shared state corruption)
- Better CPU utilization on multi-core systems
- Process crashes don't affect main program
- Can be killed/restarted independently
- Better for CPU-intensive backtest work

❌ **Disadvantages**:
- Higher memory overhead (separate Python interpreters)
- IPC overhead for data transfer
- More complex state management
- Longer startup time

#### **ThreadPoolExecutor (REJECTED)**
✅ **Advantages**:
- Lower memory overhead
- Faster startup
- Shared memory (easier state management)
- Lower IPC overhead

❌ **Disadvantages**:
- **GIL contention** - Not true parallelism for CPU work
- Thread crashes can corrupt shared state
- Cannot utilize multiple CPU cores effectively
- **Poor performance for backtesting** - CPU-bound work

**DECISION**: Use **ProcessPoolExecutor** for true parallel execution of CPU-intensive backtest work.

---

## 📡 INTER-PROCESS COMMUNICATION (IPC) STRATEGY

### **Communication Channels**

1. **Job Submission**: Main → Workers
   - Method: `executor.submit(worker_func, config, **kwargs)`
   - Data: Serialized backtest config dict
   - Format: Pickle (automatic via ProcessPoolExecutor)

2. **Progress Updates**: Workers → Main
   - Method: `multiprocessing.Queue`
   - Data: Progress percentage, current step, ETA
   - Frequency: Every 1 second or 5% progress

3. **Results**: Workers → Main
   - Method: `Future.result()`
   - Data: Backtest results with NautilusTrader types
   - Format: Serialized dict with validation

4. **Errors**: Workers → Main
   - Method: `Future.exception()`
   - Data: Exception type, message, traceback
   - Handling: Retry logic with exponential backoff

### **Serialization Strategy**

**Pickle (Default)**:
- Handles most Python objects
- Automatic with ProcessPoolExecutor
- Fast for simple types

**Custom Serialization (NautilusTrader Types)**:
- Convert to dict before sending
- Reconstruct types on receipt
- Validation on both sides

```python
# Sending NautilusTrader types
config_dict = {
    'instrument_id': str(instrument_id),
    'start_time': start_time.isoformat(),
    'end_time': end_time.isoformat(),
    'quantity': float(quantity),
    'price': float(price)
}

# Receiving NautilusTrader types
instrument_id = InstrumentId.from_str(config_dict['instrument_id'])
start_time = pd.Timestamp(config_dict['start_time'])
quantity = Quantity.from_str(str(config_dict['quantity']))
price = Price.from_str(str(config_dict['price']))
```

---

## 📊 PROGRESS TRACKING MECHANISM

### **Real-Time Progress Updates**

```python
class ProgressTracker:
    """Track progress across multiple workers"""
    
    def __init__(self, total_configs: int):
        self.total = total_configs
        self.completed = 0
        self.failed = 0
        self.in_progress = 0
        self.start_time = datetime.now()
    
    def update(self, config_id: str, status: str):
        """Update progress for a config"""
        if status == 'completed':
            self.completed += 1
            self.in_progress -= 1
        elif status == 'failed':
            self.failed += 1
            self.in_progress -= 1
        elif status == 'started':
            self.in_progress += 1
    
    def get_eta(self) -> timedelta:
        """Calculate estimated time remaining"""
        if self.completed == 0:
            return timedelta(0)
        
        elapsed = datetime.now() - self.start_time
        rate = self.completed / elapsed.total_seconds()
        remaining = self.total - self.completed - self.failed
        
        return timedelta(seconds=remaining / rate)
    
    def get_progress(self) -> float:
        """Get completion percentage"""
        return (self.completed + self.failed) / self.total * 100
```

### **UI Updates**

- **Update Interval**: 1000ms (1 second)
- **Progress Bar**: 0-100% based on completed configs
- **ETA Display**: Calculated from average completion rate
- **Status Text**: "X/Y complete, Z failed, ETA: HH:MM:SS"
- **Resource Graphs**: CPU/memory over last 60 seconds

---

## 🛡️ ERROR HANDLING APPROACH

### **Error Categories**

1. **Transient Errors** (Retryable)
   - Network timeouts
   - Temporary resource unavailability
   - Database connection issues
   - **Action**: Retry with exponential backoff

2. **Permanent Errors** (Non-retryable)
   - Invalid configuration
   - Data validation failures
   - Type errors
   - **Action**: Log and skip config

3. **Critical Errors** (Stop execution)
   - Database corruption
   - Disk full
   - Memory exhaustion
   - **Action**: Stop all workers, save checkpoint

### **Retry Strategy**

```python
def retry_with_backoff(func, max_retries=3, backoff_factor=2):
    """Retry function with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return func()
        except TransientError as e:
            if attempt == max_retries - 1:
                raise
            
            delay = backoff_factor ** attempt
            time.sleep(min(delay, 30))  # Max 30 second delay
            
    raise MaxRetriesExceeded()
```

### **Error Recovery**

1. **Worker Crash**:
   - ProcessPoolExecutor auto-restarts worker
   - Config marked as failed
   - Retry logic determines if config retried

2. **Main Process Crash**:
   - Checkpoint system saves progress
   - Resume from last checkpoint on restart
   - Workers continue independently

3. **Resource Exhaustion**:
   - Monitor detects threshold breach
   - Pause new job submissions
   - Wait for resources to free
   - Resume when below threshold

---

## 💾 RESOURCE LIMITS & MONITORING

### **Resource Thresholds**

```python
RESOURCE_LIMITS = {
    'cpu_threshold': 90,      # % - pause if exceeded
    'memory_threshold': 85,   # % - pause if exceeded
    'disk_threshold': 90,     # % - stop if exceeded
    'max_workers': 'auto',    # cpu_count() or explicit
    'worker_timeout': 3600,   # seconds - kill if exceeded
}
```

### **Monitoring Strategy**

```python
class ResourceMonitor:
    """Monitor system resources"""
    
    def check_resources(self) -> Dict[str, float]:
        """Check current resource usage"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'worker_count': len(psutil.Process().children()),
        }
    
    def should_pause(self, usage: Dict[str, float]) -> bool:
        """Check if execution should pause"""
        return (
            usage['cpu_percent'] > RESOURCE_LIMITS['cpu_threshold'] or
            usage['memory_percent'] > RESOURCE_LIMITS['memory_threshold']
        )
    
    def should_stop(self, usage: Dict[str, float]) -> bool:
        """Check if execution should stop"""
        return usage['disk_percent'] > RESOURCE_LIMITS['disk_threshold']
```

### **Worker CPU Utilization Monitoring**

```python
class ProcessMonitor:
    """Monitor individual worker processes"""
    
    def check_worker_health(self, pid: int) -> bool:
        """Check if worker is healthy"""
        try:
            process = psutil.Process(pid)
            cpu_percent = process.cpu_percent(interval=5)
            
            # Worker should be using CPU for backtest work
            if cpu_percent < 1.0:  # Less than 1% CPU
                # Check for 30 seconds
                time.sleep(30)
                cpu_percent = process.cpu_percent(interval=5)
                
                if cpu_percent < 1.0:
                    # Worker is stuck
                    return False
            
            return True
            
        except psutil.NoSuchProcess:
            return False
```

### **Zombie Process Detection**

```python
def detect_zombies():
    """Detect and clean up zombie processes"""
    main_process = psutil.Process()
    
    for child in main_process.children(recursive=True):
        if child.status() == psutil.STATUS_ZOMBIE:
            child.kill()
            logger.warning(f"Killed zombie process {child.pid}")
```

---

## ✅ DESIGN DECISIONS

### **1. Worker Pool Size**
- **Default**: `mp.cpu_count()` (auto-detect cores)
- **Configurable**: Via `.env` file
- **Range**: 1 to `mp.cpu_count()`
- **Rationale**: One worker per core for CPU-bound work

### **2. Batch Processing**
- **Batch Size**: 10 configs per batch
- **Rationale**: Balance between checkpoint frequency and overhead
- **Checkpointing**: After each batch completion

### **3. Timeout Handling**
- **Worker Timeout**: 3600 seconds (1 hour)
- **Rationale**: Backtests shouldn't take longer than 1 hour
- **Action**: Kill worker, mark config as failed, retry if transient

### **4. Memory Management**
- **Per-Config Limit**: Monitor but don't enforce (varies by strategy)
- **System Limit**: 85% total memory
- **Action**: Pause new jobs if exceeded
- **Cleanup**: Force GC after each config completion

### **5. Progress Persistence**
- **Checkpoint Interval**: Every 5 configs
- **Checkpoint Location**: `checkpoints/optimizer/`
- **Checkpoint Format**: Compressed JSON with metadata
- **Retention**: Last 3 checkpoints (FIFO cleanup)

---

## 🔄 CHECKPOINT SYSTEM

### **Checkpoint Data Structure**

```python
checkpoint = {
    'version': '1.0',
    'timestamp': datetime.now().isoformat(),
    'total_configs': 100,
    'completed_configs': [1, 2, 3, ...],
    'failed_configs': [5, 7],
    'pending_configs': [4, 6, 8, ...],
    'results': {
        '1': {...},  # Completed results
        '2': {...},
    },
    'metadata': {
        'start_time': '...',
        'elapsed_time': 3600,
        'resource_usage': {...}
    }
}
```

### **Resume Logic**

```python
def resume_from_checkpoint(checkpoint_path: str):
    """Resume execution from checkpoint"""
    checkpoint = load_checkpoint(checkpoint_path)
    
    # Filter configs
    pending = checkpoint['pending_configs']
    completed = checkpoint['results']
    
    # Resume execution
    new_results = execute_configs(pending)
    
    # Merge results
    all_results = {**completed, **new_results}
    
    return all_results
```

---

## 📈 PERFORMANCE EXPECTATIONS

### **Target Metrics**

- **CPU Utilization**: 80-90% during execution
- **Memory Usage**: <85% total system memory
- **Worker Efficiency**: >90% time in backtest work
- **Overhead**: <5% from monitoring/IPC
- **Throughput**: N configs in N/cpu_count() time (ideal parallelism)

### **Scalability**

- **4 cores**: 4x speedup (ideal)
- **8 cores**: 7-8x speedup (realistic with overhead)
- **16 cores**: 14-16x speedup (with proper batching)

---

## 🎯 ACCEPTANCE CRITERIA

- [x] ProcessPoolExecutor vs ThreadPoolExecutor comparison complete
- [x] Inter-process communication strategy defined
- [x] Progress tracking mechanism designed
- [x] Error handling approach specified
- [x] Resource limits and monitoring defined
- [x] Checkpoint system designed
- [x] Performance expectations documented
- [x] Design reviewed by team
- [x] Resource limits defined
- [x] Error recovery strategy defined

---

## ✅ SIGN-OFF

- [x] Developer: System design complete
- [x] Lead: Architecture approved
- [x] Architect: Design validated

**Status**: ✅ APPROVED - Ready for Implementation  
**Next Step**: Task 1.2.2 - Implement ParallelExecutor
