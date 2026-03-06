# FinancialAsset Entity and Domain Work Documentation

## Overview
This documentation covers the FinancialAsset entity architecture and domain work patterns, particularly focusing on the Factor system as demonstrated by the `IndexFactor` and `IndexPriceReturnFactor` patterns. The architecture follows Domain-Driven Design (DDD) principles with clear separation between domain entities, factors, and their computational logic.

## Core Architecture

### Entity Hierarchy
```
FinancialAsset (Base)
├── Security
│   ├── Share
│   │   ├── CompanyShare  
│   │   └── ETFShare
│   └── Index
├── Derivative
│   ├── Future
│   │   └── IndexFuture
│   └── Option  
│       └── IndexFutureOption
├── Cash
├── Currency
├── Bond
└── Commodity
```

### Factor Hierarchy (Following IndexFactor Pattern)
```
Factor (Base)
├── SecurityFactor
│   ├── IndexFactor
│   │   └── IndexPriceReturnFactor (example implementation)
│   ├── CompanyShareFactor
│   │   └── CompanySharePriceReturnFactor
│   ├── EquityFactor
│   └── BondFactor
├── DerivativeFactor
│   ├── FutureFactor
│   │   ├── IndexFutureFactor  
│   │   └── IndexFuturePriceReturnFactor
│   └── OptionFactor
│       ├── IndexFutureOptionFactor
│       ├── IndexFutureOptionPriceReturnFactor
│       ├── IndexFutureOptionPriceFactor
│       └── IndexFutureOptionDeltaFactor
└── PortfolioFactor
    ├── PortfolioCompanyShareOptionFactor
    ├── PortfolioCompanyShareOptionPriceFactor  
    ├── PortfolioCompanyShareOptionPriceReturnFactor
    └── PortfolioCompanyShareOptionDeltaFactor
```

## IndexFactor Pattern Analysis

### Base Class: `IndexFactor`
**File**: `/src/domain/entities/factor/finance/financial_assets/index/index_factor.py`

```python
class IndexFactor(SecurityFactor):
    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        frequency: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            frequency=frequency,
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,
        )
```

**Key Characteristics**:
- **Inheritance-based Design**: Extends `SecurityFactor` for index-specific functionality
- **Parameter Forwarding**: Delegates all initialization to parent class
- **Domain Purity**: No infrastructure dependencies (no SQLAlchemy)
- **Metadata Rich**: Supports classification (group, subgroup, frequency, data_type)

### Concrete Implementation: `IndexPriceReturnFactor`
**File**: `/src/domain/entities/factor/finance/financial_assets/index/index_price_return_factor.py`

```python
class IndexPriceReturnFactor(IndexFactor):
    """Annualized price return factor."""

    def __init__(self, factor_id: Optional[int] = None, **kwargs):
        super().__init__(
            factor_id=factor_id,
            **kwargs
        )

    def calculate(
        self,
        start_price: float,
        end_price: float,
        method: str = "geometric"
    ) -> Optional[float]:
        """
        Calculate return between two price observations.

        Parameters
        ----------
        start_price : float
            Initial price
        end_price : float  
            Final price
        method : str
            'geometric' (default) or 'simple'

        Returns
        -------
        float | None
        """
        if start_price <= 0 or end_price <= 0:
            return None

        if method == "geometric":
            # (P_end / P_start) - 1
            return (end_price / start_price) - 1

        elif method == "simple":
            # Same formula in a two-point case
            return (end_price - start_price) / start_price

        else:
            raise ValueError("Method must be 'geometric' or 'simple'")
```

**Key Characteristics**:
- **Business Logic**: Contains actual calculation methods
- **Validation**: Input validation for price data
- **Multiple Algorithms**: Supports different calculation methods
- **Error Handling**: Graceful handling of invalid inputs
- **Pure Functions**: Stateless calculations

## Factor Pattern Generalization

### Template for New Factor Classes

Based on the IndexFactor pattern, here's the template for creating new factor classes:

```python
class {EntityType}Factor({ParentFactor}):
    """Base factor class for {EntityType} entities."""

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        frequency: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            frequency=frequency,
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,
        )
```

### Template for Concrete Factor Implementations

```python
class {EntityType}{SpecificMetric}Factor({EntityType}Factor):
    """{Description of specific calculation}."""

    def __init__(self, factor_id: Optional[int] = None, **kwargs):
        super().__init__(
            factor_id=factor_id,
            **kwargs
        )

    def calculate(
        self,
        # Specific parameters for this calculation
        parameter1: float,
        parameter2: float,
        method: str = "default_method"
    ) -> Optional[float]:
        """
        Calculate {specific metric} between observations.

        Parameters
        ----------
        parameter1 : float
            Description of parameter1
        parameter2 : float
            Description of parameter2
        method : str
            Available calculation methods

        Returns
        -------
        float | None
            Calculated value or None if invalid inputs
        """
        # Input validation
        if self._validate_inputs(parameter1, parameter2):
            return None

        # Method-specific calculations
        if method == "method1":
            return self._calculate_method1(parameter1, parameter2)
        elif method == "method2":
            return self._calculate_method2(parameter1, parameter2)
        else:
            raise ValueError(f"Unknown method: {method}")

    def _validate_inputs(self, *args) -> bool:
        """Validate input parameters."""
        # Implementation specific validation
        pass

    def _calculate_method1(self, param1, param2):
        """Specific calculation method implementation."""
        pass
```

## Concrete Factor Examples

### CompanyShareFactor Pattern
```python
class CompanyShareFactor(SecurityFactor):
    """Base factor class for company share entities."""
    # Same initialization pattern as IndexFactor

class CompanySharePriceReturnFactor(CompanyShareFactor):
    """Price return calculation for company shares."""
    
    def calculate(self, start_price: float, end_price: float, 
                 dividend: float = 0.0, method: str = "total_return") -> Optional[float]:
        """Calculate company share returns including dividends."""
        if start_price <= 0 or end_price <= 0:
            return None
            
        if method == "total_return":
            # Include dividend in return calculation
            return ((end_price + dividend) / start_price) - 1
        elif method == "price_return":
            # Price return only (same as IndexPriceReturnFactor)
            return (end_price / start_price) - 1
        else:
            raise ValueError("Method must be 'total_return' or 'price_return'")
```

### DerivativeFactor Pattern
```python
class IndexFutureOptionDeltaFactor(IndexFutureOptionFactor):
    """Delta calculation for index future options."""
    
    def calculate(self, spot_price: float, strike_price: float, 
                 time_to_expiry: float, volatility: float, 
                 risk_free_rate: float = 0.02, option_type: str = "call") -> Optional[float]:
        """Calculate option delta using Black-Scholes model."""
        if any(x <= 0 for x in [spot_price, strike_price, time_to_expiry, volatility]):
            return None
            
        import math
        from scipy.stats import norm
        
        # Black-Scholes delta calculation
        d1 = (math.log(spot_price / strike_price) + 
              (risk_free_rate + 0.5 * volatility**2) * time_to_expiry) / \
             (volatility * math.sqrt(time_to_expiry))
        
        if option_type.lower() == "call":
            return norm.cdf(d1)
        elif option_type.lower() == "put":
            return norm.cdf(d1) - 1
        else:
            raise ValueError("option_type must be 'call' or 'put'")
```

## Factor Dependencies Pattern

### Dependency Structure
Based on the repository implementation, factors can have dependencies on other factors:

```python
class ComplexFactor(SecurityFactor):
    """Factor that depends on other factors."""
    
    def __init__(self, factor_id: Optional[int] = None, **kwargs):
        super().__init__(factor_id=factor_id, **kwargs)
        self.dependencies = []  # Will be populated by repository
        
    def calculate_with_dependencies(self, entity_data: Dict, factor_values: Dict) -> Optional[float]:
        """Calculate using dependent factor values."""
        # Check if all dependencies are available
        required_factors = ['high', 'low', 'close', 'volume']
        for factor_name in required_factors:
            if factor_name not in factor_values:
                return None
                
        # Perform calculation using dependent factor values
        high = factor_values['high']
        low = factor_values['low'] 
        close = factor_values['close']
        volume = factor_values['volume']
        
        # Example: Average True Range calculation
        if len(factor_values.get('close_history', [])) > 0:
            prev_close = factor_values['close_history'][-1]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            return tr
        
        return high - low  # Simple range if no history
```

### Dependency Configuration
Factors can be configured with dependencies in the factor library:

```python
# Example factor configuration with dependencies
{
    "name": "average_true_range",
    "class": CompanyShareATRFactor,
    "group": "volatility",
    "subgroup": "range",
    "dependencies": [
        {"name": "high", "group": "price"},
        {"name": "low", "group": "price"},
        {"name": "close", "group": "price"}
    ],
    "parameters": {
        "period": 14,
        "method": "exponential"
    }
}
```

## Entity-Factor Mapping

### Relationship Pattern
Each financial asset entity type has corresponding factor types:

```python
# Entity-Factor mapping (from factor_mapper.py)
ENTITY_FACTOR_MAPPING = {
    Index: [IndexFactor],
    CompanyShare: [CompanyShareFactor],
    IndexFuture: [IndexFutureFactor],
    IndexFutureOption: [IndexFutureOptionFactor],
    Bond: [BondFactor],
    Currency: [CurrencyFactor],
    # ... additional mappings
}
```

### Usage Pattern
```python
# Get appropriate factor class for entity
entity = Index(symbol="SPX", name="S&P 500")
entity_factor_classes = ENTITY_FACTOR_MAPPING[type(entity)]
primary_factor_class = entity_factor_classes[0]  # IndexFactor

# Create factor instance
price_return_factor = IndexPriceReturnFactor(
    name="price_return",
    group="price",
    subgroup="return"
)
```

## Domain Work Patterns

### Calculation Orchestration
```python
class FactorCalculationService:
    """Domain service for orchestrating factor calculations."""
    
    def calculate_factor_value(self, factor: Factor, entity: FinancialAsset, 
                             market_data: Dict, dependencies: Dict = None) -> Optional[float]:
        """Calculate factor value for given entity and market data."""
        
        if isinstance(factor, IndexPriceReturnFactor):
            start_price = market_data.get('previous_close')
            end_price = market_data.get('current_close')
            if start_price and end_price:
                return factor.calculate(start_price, end_price)
                
        elif isinstance(factor, IndexFutureOptionDeltaFactor):
            spot_price = market_data.get('underlying_price')
            strike_price = entity.strike_price if hasattr(entity, 'strike_price') else None
            time_to_expiry = self._calculate_time_to_expiry(entity.expiry_date)
            volatility = dependencies.get('implied_volatility', 0.2)
            
            if all([spot_price, strike_price, time_to_expiry]):
                return factor.calculate(
                    spot_price, strike_price, time_to_expiry, 
                    volatility, option_type=entity.option_type
                )
        
        # Add more factor types as needed
        return None
        
    def _calculate_time_to_expiry(self, expiry_date) -> float:
        """Calculate time to expiry in years."""
        from datetime import datetime
        if not expiry_date:
            return 0.0
        days_to_expiry = (expiry_date - datetime.now().date()).days
        return max(0.0, days_to_expiry / 365.0)
```

### Validation Patterns
```python
class FactorValidationService:
    """Domain service for factor validation."""
    
    @staticmethod
    def validate_price_data(start_price: float, end_price: float) -> bool:
        """Validate price data for calculations."""
        return all([
            start_price is not None,
            end_price is not None,
            start_price > 0,
            end_price > 0,
            not math.isnan(start_price),
            not math.isnan(end_price)
        ])
    
    @staticmethod  
    def validate_option_parameters(spot: float, strike: float, 
                                 time_to_expiry: float, volatility: float) -> bool:
        """Validate option calculation parameters."""
        return all([
            spot > 0,
            strike > 0, 
            time_to_expiry >= 0,
            volatility > 0,
            not any(math.isnan(x) for x in [spot, strike, time_to_expiry, volatility])
        ])
```

## Design Principles

### Domain-Driven Design
- **Pure Domain Logic**: No infrastructure dependencies in domain entities
- **Rich Domain Models**: Entities contain business logic, not just data
- **Ubiquitous Language**: Uses financial terminology consistently
- **Bounded Context**: Clear separation between financial asset and factor contexts

### Single Responsibility  
- **Factor Hierarchy**: Each factor class has single calculation responsibility
- **Method Specificity**: Calculate methods focus on single metric
- **Validation Separation**: Input validation separated from calculation logic
- **Dependency Management**: Dependencies handled through composition, not inheritance

### Open/Closed Principle
- **Extension Points**: Easy to add new factor types through inheritance
- **Method Variants**: Support multiple calculation methods per factor
- **Parameter Flexibility**: Flexible parameter passing through **kwargs
- **Algorithm Pluggability**: Different calculation algorithms via method parameter

## Testing Patterns

### Unit Testing
```python
class TestIndexPriceReturnFactor(unittest.TestCase):
    def setUp(self):
        self.factor = IndexPriceReturnFactor(name="test_return", group="price")
    
    def test_geometric_return_calculation(self):
        result = self.factor.calculate(100.0, 110.0, method="geometric")
        self.assertAlmostEqual(result, 0.1, places=6)
    
    def test_simple_return_calculation(self):
        result = self.factor.calculate(100.0, 110.0, method="simple")
        self.assertAlmostEqual(result, 0.1, places=6)
        
    def test_invalid_prices(self):
        result = self.factor.calculate(-100.0, 110.0)
        self.assertIsNone(result)
        
    def test_zero_prices(self):
        result = self.factor.calculate(0.0, 110.0)
        self.assertIsNone(result)
        
    def test_invalid_method(self):
        with self.assertRaises(ValueError):
            self.factor.calculate(100.0, 110.0, method="invalid")
```

### Integration Testing
```python
class TestFactorIntegration(unittest.TestCase):
    def test_factor_with_entity_service(self):
        """Test factor creation and calculation with real entity service."""
        entity_service = EntityService()
        
        # Create index entity
        index = entity_service._create_or_get(
            Index, "SPX", index_type="Stock", currency="USD"
        )
        
        # Create factor
        factor = IndexPriceReturnFactor(name="daily_return", group="price")
        
        # Test calculation
        result = factor.calculate(4500.0, 4550.0)
        self.assertAlmostEqual(result, 0.0111, places=3)
```

## Performance Considerations

### Calculation Optimization
- **Lazy Evaluation**: Calculations performed only when needed
- **Result Caching**: Cache calculation results where appropriate
- **Batch Processing**: Support batch calculations for multiple entities
- **Numerical Stability**: Use appropriate numerical methods for financial calculations

### Memory Management
- **Stateless Calculations**: Factor calculations are stateless for memory efficiency
- **Dependency Injection**: Dependencies provided externally rather than stored
- **Data Structures**: Use efficient data structures for price history
- **Garbage Collection**: Minimize object creation in calculation loops

## Migration and Evolution

### Adding New Factor Types
1. Create base factor class following IndexFactor pattern
2. Implement concrete calculation classes
3. Add to ENTITY_FACTOR_MAPPING
4. Update repository factory
5. Add corresponding ORM models
6. Create mappers for domain ↔ ORM conversion

### Extending Calculation Methods  
1. Add new method parameter to existing calculate() method
2. Implement new calculation algorithm
3. Add validation for new method
4. Update documentation and tests
5. Maintain backward compatibility

This comprehensive documentation provides the foundation for understanding and extending the FinancialAsset entity and factor system architecture based on the proven IndexFactor patterns.