# Factor Dependency Migration Guide

## 🎯 Problem Statement

The factor calculation system was experiencing issues where the `return_daily` factor couldn't find proper dependencies (only found `['close']` instead of structured `start_price` and `end_price` with lags). This occurred because:

1. **FACTOR_LIBRARY Configuration**: Properly defined structured dependencies with parameter names and lag information
2. **Database Reality**: FactorDependencyModel table was missing the corresponding dependency records
3. **Resolution Gap**: System only looked in database, found minimal dependencies, failed calculations

## 💡 Solution: Single-Source Database Approach

Instead of maintaining dual resolution systems (config + database), we implement a **single source of truth in the database** by populating FactorDependencyModel with FACTOR_LIBRARY configuration.

### Architecture Benefits

- ✅ **Single Source of Truth**: All dependency resolution comes from database
- ✅ **Clean Architecture**: No dual-path logic in resolution code
- ✅ **Proper Lag Handling**: `timedelta` objects stored as database `Interval` types
- ✅ **Maintainable**: Changes to FACTOR_LIBRARY can be synced to database
- ✅ **Performant**: No config parsing during factor calculations

## 🛠️ Migration Tools

### 1. Population Script: `populate_factor_dependencies.py`

**Purpose**: Sync FACTOR_LIBRARY configuration → FactorDependencyModel database table

**Features**:
- Extracts dependencies from all FACTOR_LIBRARY sections (INDEX_LIBRARY, FUTURE_INDEX_LIBRARY, etc.)
- Maps dependency parameter names (`start_price`, `end_price`) to database relationships
- Converts `timedelta` lag objects to database `Interval` columns
- Avoids duplicates by checking existing dependencies
- Provides detailed progress reporting and error handling

**Usage**:
```bash
python populate_factor_dependencies.py
```

**Example Output**:
```
🔄 Populating factor dependencies from FACTOR_LIBRARY...

📚 Processing index_library...
  🔍 Processing factor: return_daily
    ✅ Found dependent factor: return_daily (ID: 14)
      ⏰ Found lag: 2 days, 0:00:00
      ✅ Created dependency: return_daily → close (lag: 2 days, 0:00:00)
      ⏰ Found lag: 1 day, 0:00:00
      ✅ Created dependency: return_daily → close (lag: 1 day, 0:00:00)

📊 Summary:
  Total factors processed: 25
  Dependencies created: 8
  Errors: 0
  Success rate: 100.0%

✅ Successfully populated 8 factor dependencies!
```

### 2. Diagnostic Script: `test_current_dependency_resolution.py`

**Purpose**: Validate database state vs FACTOR_LIBRARY expectations

**Features**:
- Checks if `return_daily` factor exists in database
- Counts actual dependencies vs expected dependencies
- Shows lag information and factor relationships
- Compares database reality with FACTOR_LIBRARY configuration
- Provides clear diagnostic output for troubleshooting

**Usage**:
```bash
python test_current_dependency_resolution.py
```

**Example Output**:
```
🧪 Testing Current Dependency Resolution State

🔍 Testing current dependency resolution for return_daily factor...
✅ Found return_daily factor: ID=14, group=return, subgroup=daily
📊 Dependencies found in database: 2
  - close (ID: 4, lag: 2 days, 0:00:00)
  - close (ID: 4, lag: 1 day, 0:00:00)
✅ return_daily has expected 2 dependencies - system should work correctly

📚 FACTOR_LIBRARY configuration for return_daily:
  Name: return_daily
  Group: return
  Subgroup: daily
  Dependencies (2):
    - start_price: close (lag: 2 days, 0:00:00)
    - end_price: close (lag: 1 day, 0:00:00)

✅ System should work correctly - dependencies are properly configured!
```

## 🔄 Migration Process

1. **Backup Database** (if needed):
   ```bash
   cp database.sqlite database.sqlite.backup
   ```

2. **Run Diagnostic** to check current state:
   ```bash
   python test_current_dependency_resolution.py
   ```

3. **Populate Dependencies** from FACTOR_LIBRARY:
   ```bash
   python populate_factor_dependencies.py
   ```

4. **Verify Migration** success:
   ```bash
   python test_current_dependency_resolution.py
   ```

5. **Test Factor Calculations** to ensure `return_daily` works correctly

## 📊 Database Schema

### FactorDependencyModel Structure

```python
class FactorDependencyModel(Base):
    __tablename__ = 'factor_dependencies'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dependent_factor_id = Column(Integer, ForeignKey('factors.id'), nullable=False)  # return_daily
    independent_factor_id = Column(Integer, ForeignKey('factors.id'), nullable=False)  # close
    lag = Column(Interval, nullable=True)  # timedelta(days=1) or timedelta(days=2)
```

### Example Records After Migration

| id | dependent_factor_id | independent_factor_id | lag |
|----|--------------------|--------------------|-----|
| 1  | 14 (return_daily)  | 4 (close)         | 2 days |
| 2  | 14 (return_daily)  | 4 (close)         | 1 day |

## 🎯 Expected Results

After migration, the factor calculation system should:

1. **Find 2 Dependencies**: `return_daily` will have proper start_price and end_price dependencies
2. **Apply Correct Lags**: t-2 close price as start_price, t-1 close price as end_price  
3. **Calculate Successfully**: `IndexPriceReturnFactor.calculate(start_price=X, end_price=Y)`
4. **Output**: `"Factor return_daily has 2 dependencies - using calculate function"` instead of errors

## 🔧 Maintenance

- **Adding New Factors**: Update FACTOR_LIBRARY, then run population script
- **Modifying Dependencies**: Update FACTOR_LIBRARY, clear affected dependencies, re-run population
- **Debugging**: Use diagnostic script to compare database vs configuration

## 🚀 Integration

This approach integrates with the existing DDD architecture:
- **Domain Layer**: FactorDependency entity remains pure
- **Infrastructure Layer**: FactorDependencyModel handles persistence with Interval lag storage
- **Application Layer**: Factor calculation logic uses single database source
- **Repository Pattern**: FactorDependencyRepository provides clean access interface