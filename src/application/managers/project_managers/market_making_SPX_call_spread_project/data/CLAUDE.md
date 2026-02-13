# CLAUDE.md – Factor Creation for SPX Call Spread Market Making

## 🎯 Purpose

This document explains how to use the **factor definition configuration system** to create and manage factors for the SPX Call Spread Market Making Project. It demonstrates the integration between the factor definition config (`factor_definition_config.py`), the domain entity system (`factor_dependency.py`), and the repository infrastructure to build a comprehensive factor ecosystem.

## 🏗️ Factor Architecture Overview

The factor creation system follows Domain-Driven Design (DDD) principles with clear separation of concerns:

```
Factor Creation Architecture:
├── Domain Layer
│   └── factor_dependency.py          # Pure domain entities and business rules
├── Infrastructure Layer  
│   ├── models/factor_dependency.py   # SQLAlchemy ORM models
│   └── repositories/factor_dependency_repository.py  # Data persistence
├── Application Layer
│   └── data/factor_definition_config.py  # Factor configuration and metadata
└── Ports Layer
    └── factor_dependency_port.py     # Repository interface contracts
```

## 📋 Factor Definition System

### Core Configuration Structure

The `factor_definition_config.py` contains the `FACTOR_LIBRARY` dictionary that defines all available factors for the SPX market making project:

```python
from src.application.managers.project_managers.market_making_SPX_call_spread_project.data.factor_definition_config import FACTOR_LIBRARY, get_factor_config

# Each factor has a standardized structure:
factor_config = {
    "group": "price|technical|volatility|market",     # High-level category
    "subgroup": "specific_type",                      # Detailed classification
    "data_type": "numeric|categorical|binary",        # Data type
    "description": "Human-readable description",      # Purpose and usage
    "dependencies": ["factor1", "factor2"],           # Required input factors
    "parameters": {"param1": value1, "param2": value2}  # Configuration parameters
}
```

### Available Factor Categories

#### 1. Price-Based Factors (`group: "price"`)
- **OHLCV Data**: `open`, `high`, `low`, `close`, `volume`
- **Subgroup**: `minutes` (minute-level data)
- **Dependencies**: None (raw market data)
- **Usage**: Foundation for all other factor calculations

```python
# Example: Close price factor
"close": {
    "group": "price",
    "subgroup": "minutes", 
    "data_type": "numeric",
    "description": "Minute-level close price",
    "dependencies": [],
    "parameters": {}
}
```

#### 2. Technical Indicators (`group: "technical"`)
- **Trend Indicators**: `sma_10`, `sma_20` (Simple Moving Averages)
- **Momentum Indicators**: `rsi`, `macd` (Relative Strength Index, MACD)
- **Volatility Indicators**: `bb_upper`, `bb_lower` (Bollinger Bands)

```python
# Example: RSI factor with dependencies
"rsi": {
    "group": "technical",
    "subgroup": "momentum",
    "data_type": "numeric", 
    "description": "Relative Strength Index",
    "dependencies": ["close"],        # Depends on close price
    "parameters": {"period": 14}      # 14-period RSI
}
```

#### 3. Volatility Measures (`group: "volatility"`)
- **Realized Volatility**: `realized_vol_10`, `realized_vol_20`
- **Implied Volatility**: `vix`, `term_structure`
- **Dependencies**: Typically require `close` price data

#### 4. Market-Wide Factors (`group: "market"`)
- **Sentiment Indicators**: `put_call_ratio`, `skew`
- **Market Structure**: `term_structure_slope`

## 🔗 Factor Dependency Management

### Domain Entity: FactorDependency

The `FactorDependency` entity (`src/domain/entities/factor/factor_dependency.py`) represents dependency relationships between factors:

```python
from src.domain.entities.factor.factor_dependency import FactorDependency

# Creating a factor dependency relationship
dependency = FactorDependency(
    dependent_factor_id=5,      # Factor that depends on another
    independent_factor_id=1     # Factor that is depended upon
)

# Built-in validation:
# - A factor cannot depend on itself
# - Factor IDs must be positive integers
```

### Key Features:
- **Validation**: Automatic validation of dependency relationships
- **Type Safety**: Strong typing with dataclass structure
- **Domain Purity**: No infrastructure dependencies in the domain layer

## 🗃️ Repository Integration

### Repository Pattern Implementation

The factor dependency system uses the repository pattern for data persistence:

```python
from src.infrastructure.repositories.local_repo.factor.factor_dependency_repository import FactorDependencyRepository
from src.domain.entities.factor.factor_dependency import FactorDependency

# Initialize repository (requires SQLAlchemy session)
repo = FactorDependencyRepository(session)

# Create and persist a dependency
dependency = FactorDependency(
    dependent_factor_id=rsi_factor_id,
    independent_factor_id=close_price_factor_id
)
persisted_dependency = repo.add(dependency)

# Query dependencies
rsi_dependencies = repo.get_by_dependent_factor_id(rsi_factor_id)
factors_depending_on_close = repo.get_by_independent_factor_id(close_price_factor_id)
```

### Available Repository Methods:
- `get_by_id(entity_id)`: Get specific dependency by ID
- `get_by_dependent_factor_id(factor_id)`: Get all dependencies for a factor
- `get_by_independent_factor_id(factor_id)`: Get all factors that depend on this factor
- `get_all()`: Get all factor dependencies
- `add(entity)`: Persist a new dependency
- `update(entity)`: Update existing dependency
- `delete(entity_id)`: Remove a dependency
- `exists(dependent_id, independent_id)`: Check if dependency exists

## 🛠️ Creating Factors: Step-by-Step Guide

### Step 1: Define Factor Configuration

First, add your factor to the `FACTOR_LIBRARY` in `factor_definition_config.py`:

```python
# Add to FACTOR_LIBRARY dictionary
"my_custom_indicator": {
    "group": "technical",
    "subgroup": "custom",
    "data_type": "numeric",
    "description": "My custom technical indicator",
    "dependencies": ["close", "volume"],  # Requires close price and volume
    "parameters": {
        "lookback_period": 20,
        "smoothing_factor": 0.1
    }
}
```

### Step 2: Create Factor Entity (if needed)

Create the actual factor entity in the database using the appropriate factor service/repository.

### Step 3: Establish Dependencies

Use the FactorDependency system to create dependency relationships:

```python
# Example: Creating dependencies for RSI indicator
from src.domain.entities.factor.factor_dependency import FactorDependency

# Assuming we have factor IDs:
close_factor_id = 1
rsi_factor_id = 5

# Create dependency: RSI depends on close price
rsi_dependency = FactorDependency(
    dependent_factor_id=rsi_factor_id,
    independent_factor_id=close_factor_id
)

# Persist the dependency
repo = FactorDependencyRepository(session)
persisted_dependency = repo.add(rsi_dependency)
```

### Step 4: Validation and Testing

```python
# Validate factor configuration
factor_config = get_factor_config("rsi")
assert factor_config["dependencies"] == ["close"]
assert factor_config["parameters"]["period"] == 14

# Validate dependency relationships
assert repo.exists(rsi_factor_id, close_factor_id) == True

# Check dependency chain
rsi_deps = repo.get_by_dependent_factor_id(rsi_factor_id)
assert len(rsi_deps) == 1
assert rsi_deps[0].independent_factor_id == close_factor_id
```

## 🔄 Dependency Resolution Algorithm

For complex factors with multiple dependencies, you'll need to resolve the dependency graph:

```python
def resolve_factor_dependencies(factor_name: str) -> List[str]:
    """
    Resolve all dependencies for a factor, including transitive dependencies.
    Returns factors in calculation order (dependencies first).
    """
    config = get_factor_config(factor_name)
    resolved = []
    
    def resolve_recursive(name: str, visited: set):
        if name in visited:
            raise ValueError(f"Circular dependency detected involving {name}")
        
        visited.add(name)
        factor_config = get_factor_config(name)
        
        # Resolve dependencies first
        for dep in factor_config.get("dependencies", []):
            if dep not in resolved:
                resolve_recursive(dep, visited)
        
        # Add current factor if not already resolved
        if name not in resolved:
            resolved.append(name)
        
        visited.remove(name)
    
    resolve_recursive(factor_name, set())
    return resolved

# Example usage:
rsi_deps = resolve_factor_dependencies("rsi")
# Returns: ["close", "rsi"] - close must be calculated before RSI

macd_deps = resolve_factor_dependencies("macd") 
# Returns: ["close", "macd"] - close must be calculated before MACD
```

## 📊 Factor Calculation Pipeline

### Integration with SPX Market Making Strategy

```python
from src.application.managers.project_managers.market_making_SPX_call_spread_project.data.factor_definition_config import FACTOR_LIBRARY

class FactorCalculationPipeline:
    """Pipeline for calculating factors in dependency order."""
    
    def __init__(self, factor_dependency_repo: FactorDependencyRepository):
        self.dependency_repo = factor_dependency_repo
    
    def calculate_factors_for_strategy(self, required_factors: List[str]) -> Dict[str, np.ndarray]:
        """Calculate all factors needed for the strategy."""
        # Step 1: Resolve all dependencies
        all_factors_needed = []
        for factor in required_factors:
            dependencies = resolve_factor_dependencies(factor)
            all_factors_needed.extend(dependencies)
        
        # Remove duplicates while preserving order
        unique_factors = []
        seen = set()
        for factor in all_factors_needed:
            if factor not in seen:
                unique_factors.append(factor)
                seen.add(factor)
        
        # Step 2: Calculate factors in dependency order
        calculated_factors = {}
        for factor_name in unique_factors:
            config = get_factor_config(factor_name)
            calculated_factors[factor_name] = self._calculate_factor(
                factor_name, config, calculated_factors
            )
        
        return calculated_factors
    
    def _calculate_factor(self, name: str, config: Dict, available_factors: Dict) -> np.ndarray:
        """Calculate individual factor based on its configuration."""
        if config["group"] == "price":
            # Load raw price data
            return self._load_price_data(name)
        elif config["group"] == "technical":
            return self._calculate_technical_indicator(name, config, available_factors)
        elif config["group"] == "volatility":
            return self._calculate_volatility_measure(name, config, available_factors)
        elif config["group"] == "market":
            return self._calculate_market_factor(name, config, available_factors)
```

## 🧪 Testing Factor Creation

### Unit Tests for Factor Dependencies

```python
import unittest
from src.domain.entities.factor.factor_dependency import FactorDependency

class TestFactorDependency(unittest.TestCase):
    
    def test_valid_dependency_creation(self):
        """Test creating a valid factor dependency."""
        dep = FactorDependency(dependent_factor_id=5, independent_factor_id=1)
        self.assertEqual(dep.dependent_factor_id, 5)
        self.assertEqual(dep.independent_factor_id, 1)
        self.assertIsNone(dep.id)
    
    def test_self_dependency_validation(self):
        """Test that factors cannot depend on themselves."""
        with self.assertRaises(ValueError):
            FactorDependency(dependent_factor_id=1, independent_factor_id=1)
    
    def test_negative_id_validation(self):
        """Test that factor IDs must be positive."""
        with self.assertRaises(ValueError):
            FactorDependency(dependent_factor_id=-1, independent_factor_id=1)
        
        with self.assertRaises(ValueError):
            FactorDependency(dependent_factor_id=1, independent_factor_id=0)

class TestFactorConfiguration(unittest.TestCase):
    
    def test_get_factor_config(self):
        """Test retrieving factor configuration."""
        rsi_config = get_factor_config("rsi")
        
        self.assertEqual(rsi_config["group"], "technical")
        self.assertEqual(rsi_config["subgroup"], "momentum")
        self.assertEqual(rsi_config["dependencies"], ["close"])
        self.assertEqual(rsi_config["parameters"]["period"], 14)
    
    def test_nonexistent_factor_config(self):
        """Test handling of nonexistent factor."""
        config = get_factor_config("nonexistent_factor")
        self.assertEqual(config, {})
```

## 🔮 Advanced Usage Patterns

### Dynamic Factor Creation

```python
def create_dynamic_moving_average(period: int, base_factor: str = "close") -> str:
    """
    Dynamically create a moving average factor with specified parameters.
    """
    factor_name = f"sma_{period}"
    
    # Add to factor library
    FACTOR_LIBRARY[factor_name] = {
        "group": "technical",
        "subgroup": "trend",
        "data_type": "numeric",
        "description": f"Simple Moving Average ({period} periods)",
        "dependencies": [base_factor],
        "parameters": {"period": period}
    }
    
    return factor_name

# Usage
sma_50 = create_dynamic_moving_average(50)
sma_200 = create_dynamic_moving_average(200)
```

### Factor Versioning and Updates

```python
def update_factor_parameters(factor_name: str, new_parameters: Dict):
    """Update parameters for an existing factor."""
    if factor_name in FACTOR_LIBRARY:
        FACTOR_LIBRARY[factor_name]["parameters"].update(new_parameters)
        # Log the change for audit trail
        print(f"Updated {factor_name} parameters: {new_parameters}")
    else:
        raise ValueError(f"Factor {factor_name} not found in library")

# Example: Update RSI period from 14 to 21
update_factor_parameters("rsi", {"period": 21})
```

## 📈 Integration with SPX Strategy

### Factor Selection for Market Making

The SPX Call Spread Market Making strategy uses specific factors:

```python
# Core factors for SPX market making
SPX_MARKET_MAKING_FACTORS = [
    # Price foundations
    "open", "high", "low", "close", "volume",
    
    # Technical indicators for trend analysis
    "sma_10", "sma_20", "rsi", "macd",
    
    # Volatility measures for options pricing
    "realized_vol_10", "realized_vol_20", "vix",
    
    # Market sentiment factors
    "put_call_ratio", "skew", "term_structure_slope"
]

def initialize_spx_factors(dependency_repo: FactorDependencyRepository):
    """Initialize all factors needed for SPX market making."""
    pipeline = FactorCalculationPipeline(dependency_repo)
    return pipeline.calculate_factors_for_strategy(SPX_MARKET_MAKING_FACTORS)
```

## 📋 Maintenance and Best Practices

### Factor Library Maintenance

1. **Regular Review**: Periodically review factor definitions for accuracy
2. **Performance Monitoring**: Track calculation performance of complex factors
3. **Dependency Validation**: Ensure dependency graphs remain acyclic
4. **Documentation Updates**: Keep descriptions current and accurate

### Development Guidelines

1. **Naming Conventions**: Use consistent naming for similar factor types
2. **Parameter Documentation**: Document all parameters with clear descriptions
3. **Dependency Management**: Always specify dependencies accurately
4. **Testing**: Write comprehensive tests for new factors
5. **Version Control**: Track changes to factor definitions

### Performance Optimization

1. **Caching**: Cache frequently calculated factors
2. **Batch Processing**: Calculate related factors together
3. **Memory Management**: Clean up intermediate calculations
4. **Database Indexing**: Ensure proper indexing on factor_id fields

---

## 🎯 Summary

The SPX Call Spread Market Making project's factor creation system provides:

1. **Structured Configuration**: Standardized factor definitions with metadata
2. **Dependency Management**: Robust dependency tracking and resolution  
3. **Repository Pattern**: Clean separation between domain and infrastructure
4. **Type Safety**: Strong typing and validation throughout the system
5. **Extensibility**: Easy addition of new factors and factor types

This system ensures that factors are created systematically, dependencies are properly managed, and the calculation pipeline maintains data integrity throughout the SPX market making strategy execution.