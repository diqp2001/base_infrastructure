# Cross-Sectional Project: Spatiotemporal Trainer AttributeError Analysis

## 🐛 Problem Description

**Error Location**: `src/application/managers/project_managers/cross_sectionnal_project/backtesting/base_project_algorithm.py:323`

**Error Type**: `AttributeError: 'BaseProjectAlgorithm' object has no attribute 'spatiotemporal_trainer'`

**Error Context**: The error occurs when the algorithm's `on_data()` method is called and tries to execute:
```python
if not self.spatiotemporal_trainer:  # Line 323
    self.log(f"⚠️ on_data called but dependencies not fully injected - trainer: {self.spatiotemporal_trainer is not None}")
```

## 🔍 Root Cause Analysis

### 1. **Missing Attribute Initialization**
The `BaseProjectAlgorithm` class never initializes the `spatiotemporal_trainer` attribute in its `__init__()` or `initialize()` methods.

**File**: `base_project_algorithm.py`, lines 46-88
```python
def initialize(self):
    """Initialize the algorithm following MyAlgorithm pattern."""
    # ... other initializations ...
    
    # Model storage - both ML models and traditional models
    self.models = {}  # Traditional RandomForest models per ticker
    self.spatiotemporal_model = None  # Our TFT/MLP ensemble model
    self.ml_signal_generator = None
    
    # ❌ MISSING: self.spatiotemporal_trainer = None
    # ❌ MISSING: self.factor_manager = None  
    # ❌ MISSING: self.momentum_strategy = None
```

### 2. **Dependency Injection Timing Issue**
The dependencies are injected via setter methods that are called AFTER the algorithm is instantiated:

**File**: `backtest_runner.py`, lines 167-170
```python
if self.model_trainer:
    algorithm.set_spatiotemporal_trainer(self.model_trainer)  # Called AFTER instantiation
    self.logger.info("✅ Spatiotemporal trainer injected into algorithm")
```

**File**: `base_project_algorithm.py`, lines 529-532
```python
def set_spatiotemporal_trainer(self, trainer):
    """Inject spatiotemporal trainer from the BacktestRunner."""
    self.spatiotemporal_trainer = trainer  # This creates the attribute
    self.log("✅ Spatiotemporal trainer injected successfully")
```

### 3. **Race Condition**
The `on_data()` method can be called by the Misbuffet framework BEFORE the dependency injection happens, causing the AttributeError when trying to access an uninitialized attribute.

## 📋 Object Lifecycle Timeline

1. **Algorithm Instantiation** (`backtest_runner.py:158`)
   ```python
   algorithm = BaseProjectAlgorithm()  # Creates object
   ```

2. **Algorithm Initialization** (`base_project_algorithm.py:46-88`)
   ```python
   def initialize(self):
       # Initializes models, config, etc.
       # ❌ Does NOT initialize spatiotemporal_trainer
   ```

3. **Misbuffet Framework Starts** 
   - Framework may call `on_data()` immediately
   - Line 323: `if not self.spatiotemporal_trainer:` → **AttributeError**

4. **Dependency Injection** (`backtest_runner.py:167-170`)
   ```python
   algorithm.set_spatiotemporal_trainer(self.model_trainer)  # Too late!
   ```

## ✅ Solution

### **Fix 1: Initialize Missing Dependencies**
Add missing attribute initialization to the `initialize()` method:

**File**: `base_project_algorithm.py`, after line 79
```python
# Dependencies (will be injected later by BacktestRunner)
self.spatiotemporal_trainer = None
self.factor_manager = None  
self.momentum_strategy = None
```

### **Fix 2: Safe Attribute Checking**
Replace direct attribute access with `hasattr()` checks:

**Before (Line 323)**:
```python
if not self.spatiotemporal_trainer:
```

**After (Better defensive programming)**:
```python
if not hasattr(self, 'spatiotemporal_trainer') or not self.spatiotemporal_trainer:
```

### **Fix 3: Alternative - Use `getattr()` with Default**
```python
if not getattr(self, 'spatiotemporal_trainer', None):
```

## 🔧 Implementation Details

### **Current Dependency Injection Pattern**
```python
# backtest_runner.py:149-182
def create_algorithm_instance(self) -> BaseProjectAlgorithm:
    algorithm = BaseProjectAlgorithm()
    
    # Dependency injection after instantiation
    if self.factor_manager:
        algorithm.set_factor_manager(self.factor_manager)
    if self.model_trainer:
        algorithm.set_spatiotemporal_trainer(self.model_trainer)
    if self.momentum_strategy:
        algorithm.set_momentum_strategy(self.momentum_strategy)
        
    return algorithm
```

### **Setter Methods Pattern**
```python
# base_project_algorithm.py:523-538
def set_factor_manager(self, factor_manager):
    self.factor_manager = factor_manager
    
def set_spatiotemporal_trainer(self, trainer):
    self.spatiotemporal_trainer = trainer
    
def set_momentum_strategy(self, strategy):
    self.momentum_strategy = strategy
```

## 🎯 Recommended Solution

**Apply Fix 1** - Initialize all dependency attributes to `None` in the `initialize()` method. This is the cleanest solution that:

1. ✅ Prevents AttributeError on first access
2. ✅ Maintains existing dependency injection pattern
3. ✅ Follows Python best practices for attribute initialization
4. ✅ Makes the code more robust and predictable

## 🔗 Related Files

- **Primary**: `src/application/managers/project_managers/cross_sectionnal_project/backtesting/base_project_algorithm.py`
- **Secondary**: `src/application/managers/project_managers/cross_sectionnal_project/backtesting/backtest_runner.py`
- **Pattern Used**: Dependency injection via setter methods
- **Framework**: Misbuffet backtesting framework

## 🧪 Testing Verification

After implementing the fix, verify that:
1. Algorithm initializes without errors
2. `on_data()` can be called before dependency injection
3. Dependencies are properly injected and accessible
4. All three dependencies work correctly: `factor_manager`, `spatiotemporal_trainer`, `momentum_strategy`

---

*Generated with [Claude Code](https://claude.ai/code) - Issue Analysis for Cross-Sectional Project*