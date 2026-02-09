# Factor Dependency System Documentation

## Overview

The Factor Dependency System implements discriminator-based factor-to-factor dependencies as requested in issue #369. This system enables deterministic factor resolution, explicit dependency graphs, and supports caching, backtests, real-time feeds, and cycle detection.

## Key Design Goals

✅ **Deterministic factor resolution** - Using stable discriminator codes  
✅ **Explicit factor dependency graph (DAG)** - With cycle detection  
✅ **No duplication of metadata** - Discriminators reference factors, metadata is hints only  
✅ **Timestamp handled by execution context** - Not stored in dependency definitions  
✅ **Future support for caching, backtests, real-time feeds** - Extensible architecture  

## Core Components

### 1. FactorDiscriminator

Stable technical identifier for factors using code + version:

```python
discriminator = FactorDiscriminator(
    code="MARKET_SPOT_PRICE",  # Technical, stable
    version="v1"                # Version for evolution
)
```

### 2. FactorReference

Complete factor reference with discriminator and optional human metadata:

```python
factor_ref = FactorReference(
    discriminator=FactorDiscriminator("MARKET_SPOT_PRICE", "v1"),
    name="Spot Price",          # Human hint only
    group="Market Price",       # Human hint only
    subgroup="Spot",           # Human hint only
    source="IBKR"              # Human hint only
)
```

### 3. Factor Dependencies Declaration

Factors declare class-level dependencies in the exact format specified:

```python
class FutureContangoFactor(FutureFactor):
    """Example factor with discriminator-based dependencies."""
    
    dependencies = {
        "spot_price": {
            "factor": {
                "discriminator": {
                    "code": "MARKET_SPOT_PRICE",
                    "version": "v1",
                },
                "name": "Spot Price",
                "group": "Market Price", 
                "subgroup": "Spot",
                "source": "IBKR",
            },
            "required": True,
        },
        "future_price": {
            "factor": {
                "discriminator": {
                    "code": "MARKET_FUTURE_PRICE", 
                    "version": "v1",
                },
                "name": "Future Price",
                "group": "Market Price",
                "subgroup": "Future", 
                "source": "IBKR",
            },
            "required": True,
        },
        "T": {
            "factor": {
                "discriminator": {
                    "code": "FUTURE_TIME_TO_MATURITY",
                    "version": "v1",
                },
                "name": "Time To Maturity",
                "group": "Future Factor",
                "subgroup": "Contract",
                "source": "model",
            },
            "required": True,
        },
    }
    
    def calculate(self, spot_price: float, future_price: float, T: float) -> Optional[float]:
        """Calculate using resolved dependencies."""
        if spot_price <= 0 or T <= 0:
            return None
        
        raw_contango = (future_price - spot_price) / spot_price
        return raw_contango / T  # Annualized contango rate
```

## Execution Flow

### 1. Factor Value Request

When `IBKRFactorValueRepository._create_or_get()` is called:

```python
factor_value = repo._create_or_get(
    entity_symbol="AAPL",
    factor=contango_factor,
    entity=aapl_entity, 
    date="2026-02-09"
)
```

### 2. Dependency Resolution

The system automatically:

1. **Extracts dependencies** from factor class definition
2. **Resolves recursively** using discriminator registry lookup
3. **Fetches factor values** for the given timestamp from IBKR/database
4. **Calls `calculate(**resolved_values)`** with resolved parameters
5. **Stores result** in database

### 3. Resolution Context

Timestamps and execution context are handled separately:

```python
context = DependencyResolutionContext(
    timestamp=datetime(2026, 2, 9),
    entity_id=aapl_entity.id,
    instrument_id=instrument.id
)

resolved_value = resolver.calculate_factor_with_dependencies(factor, context)
```

## Registry System

### FactorDependencyRegistry

Maps discriminators to actual factor entities:

```python
registry = InMemoryFactorDependencyRegistry()

# Register factors with their discriminators
spot_discriminator = FactorDiscriminator("MARKET_SPOT_PRICE", "v1")
registry.register_factor(spot_price_factor, spot_discriminator)

# Resolve by discriminator
resolved_factor = registry.resolve_factor(spot_discriminator)
```

### Standard Factor Registration

IBKR repository automatically registers common market factors:

```python
# Automatically registered on initialization
standard_factors = [
    ("MARKET_SPOT_PRICE", "v1", "open", "Market Price", "Spot", "IBKR"),
    ("MARKET_FUTURE_PRICE", "v1", "close", "Market Price", "Future", "IBKR"),
    ("MARKET_HIGH_PRICE", "v1", "high", "Market Price", "High", "IBKR"),
    ("MARKET_LOW_PRICE", "v1", "low", "Market Price", "Low", "IBKR"),
    ("MARKET_VOLUME", "v1", "volume", "Market Data", "Volume", "IBKR"),
    ("MARKET_VOLATILITY", "v1", "HISTORICAL_VOLATILITY", "Market Data", "Volatility", "IBKR"),
]
```

## DAG Validation and Cycle Detection

### Automatic Validation

The system prevents cyclic dependencies:

```python
validator = FactorDependencyValidator(registry)

try:
    validator.validate_dag([factor_a, factor_b, factor_c])
except CyclicDependencyError as e:
    print(f"Cycle detected: {e.cycle_path}")
```

### Example Cycle Detection

```python
# This would be detected as a cycle:
# Factor A depends on Factor B
# Factor B depends on Factor C  
# Factor C depends on Factor A

# CyclicDependencyError: Factor A -> Factor B -> Factor C -> Factor A
```

## Integration with IBKRFactorValueRepository

### Enhanced _create_or_get Method

The existing method now supports discriminator-based dependencies:

```python
def _create_or_get(self, entity_symbol, **kwargs):
    # ... existing code ...
    
    dependencies = self._get_factor_dependencies(factor_entity)
    
    if dependencies:
        # NEW: Use discriminator-based resolution
        context = DependencyResolutionContext(
            timestamp=date_obj,
            entity_id=entity_id,
            instrument_id=kwargs.get('instrument_id')
        )
        
        calculated_value = self.dependency_resolver.calculate_factor_with_dependencies(
            factor=factor_entity,
            context=context,
            **kwargs
        )
        
        # Create and persist factor value
        factor_value = FactorValue(...)
        return self.local_repo.add(factor_value)
```

### Discriminator Format Detection

The system automatically detects and handles both formats:

```python
def _get_factor_dependencies(self, factor_entity):
    dependencies = getattr(factor_entity.__class__, 'dependencies', {})
    
    # Check if this is the new discriminator format
    is_discriminator_format = any(
        isinstance(dep_data, dict) and 
        "factor" in dep_data and 
        "discriminator" in dep_data["factor"]
        for dep_data in dependencies.values()
    )
    
    if is_discriminator_format:
        return dependencies  # New format
    else:
        return convert_legacy_dependencies(dependencies)  # Legacy
```

## Usage Examples

### 1. Simple Market Factor (No Dependencies)

```python
class MarketPriceFactor(Factor):
    """Direct market data factor - no dependencies."""
    
    def __init__(self):
        super().__init__(
            name="Market Price",
            group="Market Data", 
            source="IBKR"
        )
    
    # No dependencies declared - fetched directly from IBKR
```

### 2. Calculated Factor (With Dependencies)

```python
class VolatilityRiskFactor(Factor):
    """Factor requiring multiple dependencies."""
    
    dependencies = {
        "price_volatility": {
            "factor": {
                "discriminator": {"code": "MARKET_VOLATILITY", "version": "v1"},
                "name": "Historical Volatility"
            },
            "required": True
        },
        "volume": {
            "factor": {
                "discriminator": {"code": "MARKET_VOLUME", "version": "v1"}, 
                "name": "Trading Volume"
            },
            "required": True
        },
        "market_cap": {
            "factor": {
                "discriminator": {"code": "COMPANY_MARKET_CAP", "version": "v1"},
                "name": "Market Capitalization"
            },
            "required": False,
            "default_value": 1000000000  # $1B default
        }
    }
    
    def calculate(self, price_volatility: float, volume: float, 
                  market_cap: float = 1000000000) -> float:
        """Calculate volatility-adjusted risk score."""
        liquidity_factor = min(volume / 1000000, 1.0)  # Cap at 1M volume
        size_factor = min(market_cap / 10000000000, 1.0)  # Cap at 10B market cap
        
        return price_volatility * (2.0 - liquidity_factor) * (2.0 - size_factor)
```

### 3. Future Pricing Factor (Complex Dependencies)

```python
class FutureTheoreticalPriceFactor(FutureFactor):
    """Theoretical futures pricing using cost-of-carry model."""
    
    dependencies = {
        "S": {  # Spot price
            "factor": {
                "discriminator": {"code": "MARKET_SPOT_PRICE", "version": "v1"},
                "name": "Underlying Spot Price"
            },
            "required": True
        },
        "r": {  # Risk-free rate
            "factor": {
                "discriminator": {"code": "RISK_FREE_RATE", "version": "v1"},
                "name": "Risk-Free Interest Rate"
            },
            "required": True
        },
        "q": {  # Dividend yield
            "factor": {
                "discriminator": {"code": "DIVIDEND_YIELD", "version": "v1"},
                "name": "Dividend Yield"
            },
            "required": False,
            "default_value": 0.0
        },
        "T": {  # Time to maturity
            "factor": {
                "discriminator": {"code": "FUTURE_TIME_TO_MATURITY", "version": "v1"},
                "name": "Time To Maturity"
            },
            "required": True
        },
        "storage_cost": {  # Storage costs (for commodities)
            "factor": {
                "discriminator": {"code": "STORAGE_COST_RATE", "version": "v1"},
                "name": "Storage Cost Rate"
            },
            "required": False,
            "default_value": 0.0
        }
    }
    
    def calculate(self, S: float, r: float, T: float, 
                  q: float = 0.0, storage_cost: float = 0.0) -> Optional[float]:
        """
        Calculate theoretical future price using cost-of-carry model.
        
        F = S * exp((r - q + storage_cost) * T)
        """
        if S <= 0 or T <= 0:
            return None
            
        import math
        cost_of_carry = r - q + storage_cost
        return S * math.exp(cost_of_carry * T)
```

## Error Handling

### Dependency Resolution Errors

```python
try:
    factor_value = repo._create_or_get(...)
except FactorDependencyResolutionError as e:
    print(f"Failed to resolve dependencies: {e}")
    # Handle missing dependencies
```

### Cycle Detection

```python
try:
    validator.validate_dag([factors])
except CyclicDependencyError as e:
    print(f"Circular dependency detected: {' -> '.join(e.cycle_path)}")
    # Handle circular dependencies
```

## Performance Considerations

### Caching

The system includes resolution caching within execution context:

```python
context = DependencyResolutionContext(
    timestamp=datetime.now(),
    entity_id=entity_id,
    resolved_cache={}  # Shared cache for this execution
)

# Dependencies resolved once and cached for subsequent use
```

### Recursive Resolution Depth

Protection against infinite recursion:

```python
context = DependencyResolutionContext(
    timestamp=datetime.now(),
    max_depth=10,  # Prevent infinite recursion
    resolution_depth=0
)
```

## Testing

Comprehensive test suite covers:

- ✅ Discriminator creation and validation
- ✅ Factor reference serialization
- ✅ Dependency graph creation from issue format
- ✅ Registry factor registration and resolution
- ✅ DAG validation and cycle detection  
- ✅ End-to-end dependency resolution
- ✅ Integration with IBKR repository
- ✅ Error handling scenarios

Run tests:

```bash
python -m unittest tests.test_factor_dependency_system
```

## Future Enhancements

### Database-Backed Registry

Replace in-memory registry with database persistence:

```python
class DatabaseFactorDependencyRegistry(FactorDependencyRegistry):
    """Database-backed factor registry for persistence."""
    
    def register_factor(self, factor, discriminator):
        # Store in database with discriminator mapping
        pass
    
    def resolve_factor(self, discriminator):
        # Query database by discriminator
        pass
```

### Real-Time Data Integration

Support for real-time factor value streams:

```python
class RealtimeFactorDependencyResolver(FactorDependencyResolver):
    """Real-time dependency resolver with streaming data."""
    
    def resolve_dependencies(self, factor, context):
        # Subscribe to real-time data feeds for dependencies
        pass
```

### Backtesting Support

Historical dependency resolution for backtests:

```python
context = DependencyResolutionContext(
    timestamp=historical_date,
    backtest_mode=True,
    historical_data_source=backtest_data_provider
)
```

## Migration Guide

### From Legacy Dependencies

Old format:
```python
dependencies = {
    'price_data': {'name': 'price_data', 'required': True},
    'volume_data': {'name': 'volume_data', 'required': True}
}
```

New format:
```python
dependencies = {
    "price_data": {
        "factor": {
            "discriminator": {"code": "MARKET_SPOT_PRICE", "version": "v1"},
            "name": "Spot Price"
        },
        "required": True
    },
    "volume_data": {
        "factor": {
            "discriminator": {"code": "MARKET_VOLUME", "version": "v1"},
            "name": "Trading Volume" 
        },
        "required": True
    }
}
```

The system automatically handles both formats during transition.