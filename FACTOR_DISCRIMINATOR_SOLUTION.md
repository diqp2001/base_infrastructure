# Factor Discriminator Solution: Resolving Bid/Ask Price Uniqueness

## Problem Statement

The user identified a critical design issue with the discriminator-based factor dependency system:

**External factors from IBKR** (like `OptionFactor` or `OptionPriceFactor`) that fetch data directly without needing a `calculate()` method would all share the same discriminator if we only use the factor class as identification. For example:

- **Bid Price** → Uses `OptionFactor` class, discriminator: `OPTION_PRICE:v1`
- **Ask Price** → Uses `OptionFactor` class, discriminator: `OPTION_PRICE:v1` 
- **Last Price** → Uses `OptionFactor` class, discriminator: `OPTION_PRICE:v1`

This creates **discriminator collision** - multiple distinct factor values sharing the same discriminator, making them indistinguishable.

## Solution: Enhanced Discriminator Structure

### 1. Granular Discriminator Design

The solution introduces a `data_field` component to the discriminator structure:

```python
@dataclass
class FactorDiscriminator:
    code: str              # Base factor code: "OPTION_PRICE"
    version: str           # Version: "v1" 
    data_field: Optional[str] = None  # Field: "bid", "ask", "last"
    source: Optional[str] = None      # Source: "IBKR", "model"
    
    def to_key(self) -> str:
        """Unique key: OPTION_PRICE:v1:bid:IBKR"""
        key_parts = [self.code, self.version]
        if self.data_field:
            key_parts.append(self.data_field)
        if self.source:
            key_parts.append(self.source)
        return ":".join(key_parts)
```

### 2. Factor Type Classification

```python
class FactorType(Enum):
    EXTERNAL = "external"     # Fetched from external sources (IBKR)
    CALCULATED = "calculated" # Computed using calculate() method
```

- **External factors**: Use `data_field` to specify which IBKR field to extract
- **Calculated factors**: Use unique `code` without `data_field`

### 3. Dependency Declaration Format

The enhanced system supports your exact dependency format with `data_field`:

```python
dependencies = {
    "bid_price": {
        "factor": {
            "discriminator": {
                "code": "OPTION_PRICE",
                "version": "v1", 
                "data_field": "bid",    # Specifies bid price
                "source": "IBKR"
            },
            "name": "Option Bid Price",
            "group": "Market Price",
            "subgroup": "Options",
            "source": "IBKR",
        },
        "required": True,
    },
    "ask_price": {
        "factor": {
            "discriminator": {
                "code": "OPTION_PRICE",
                "version": "v1",
                "data_field": "ask",    # Specifies ask price  
                "source": "IBKR"
            },
            "name": "Option Ask Price",
            "group": "Market Price",
            "subgroup": "Options", 
            "source": "IBKR",
        },
        "required": True,
    }
}
```

### 4. Unique Discriminator Keys

With the enhanced structure:

- **Bid Price**: `OPTION_PRICE:v1:bid:IBKR`
- **Ask Price**: `OPTION_PRICE:v1:ask:IBKR`
- **Last Price**: `OPTION_PRICE:v1:last:IBKR`
- **Delta Factor**: `OPTION_DELTA:v1:model`

All discriminators are now **uniquely identifiable**.

## Implementation Architecture

### 1. FactorRegistry with Field Mappings

```python
class FactorRegistry:
    def register_external_field_mapping(self, 
                                       base_code: str,
                                       version: str, 
                                       source: str,
                                       field_mappings: Dict[str, str]):
        """
        Maps discriminator data_fields to IBKR field names:
        
        "bid" → "bid"           # IBKR tick field name
        "ask" → "ask"           # IBKR tick field name
        "last" → "last"         # IBKR tick field name
        """
```

### 2. IBKRFactorDependencyResolver

The resolver handles both external and calculated factors:

```python
class IBKRFactorDependencyResolver:
    def _resolve_external_factor(self, discriminator: FactorDiscriminator):
        """
        Uses discriminator.data_field to fetch specific IBKR field:
        - discriminator.data_field = "bid" → fetches bid price
        - discriminator.data_field = "ask" → fetches ask price  
        - discriminator.data_field = "last" → fetches last price
        """
        
    def _resolve_calculated_factor(self, discriminator: FactorDiscriminator):
        """
        Recursively resolves dependencies and calls calculate() method
        """
```

### 3. Enhanced IBKRFactorValueRepository Integration

The enhanced `_create_or_get` function uses discriminator-based resolution:

```python
def _create_or_get_with_discriminator(self, factor_entity, financial_asset_entity, timestamp):
    # 1. Extract dependencies from factor class
    dependencies = self._get_factor_dependencies(factor_entity)
    
    if dependencies:
        # 2. Resolve dependencies using discriminator system
        resolved_deps = self.dependency_resolver.resolve_dependencies_for_factor(...)
        
        # 3. Call calculate() with resolved dependencies
        calculated_value = factor_entity.calculate(**resolved_deps)
    else:
        # 4. External factor - fetch directly from IBKR using data_field
        calculated_value = self._fetch_external_factor_from_ibkr(...)
```

## Usage Examples

### External Factors (IBKR Data)

```python
# Different OptionFactor instances with unique discriminators
class ExternalOptionPriceFactor:
    def __init__(self, data_field: str):
        self.data_field = data_field  # "bid", "ask", "last"
    
    @property
    def discriminator(self):
        return FactorDiscriminator(
            code="OPTION_PRICE", 
            version="v1",
            data_field=self.data_field,  # Makes each instance unique
            source="IBKR"
        )

# Usage:
bid_factor = ExternalOptionPriceFactor("bid")      # OPTION_PRICE:v1:bid:IBKR
ask_factor = ExternalOptionPriceFactor("ask")      # OPTION_PRICE:v1:ask:IBKR
last_factor = ExternalOptionPriceFactor("last")    # OPTION_PRICE:v1:last:IBKR
```

### Calculated Factors with Dependencies

```python
class CalculatedOptionDeltaFactor:
    dependencies = {
        "option_price": {
            "factor": {
                "discriminator": {
                    "code": "OPTION_PRICE",
                    "version": "v1",
                    "data_field": "last",  # Use last price for delta calculation
                    "source": "IBKR"
                }
                # ... metadata ...
            }
        }
    }
    
    def calculate(self, option_price: float, **kwargs) -> float:
        # Delta calculation using resolved option_price dependency
        pass
```

## Integration with IBKRFactorValueRepository

The solution integrates with your existing `_create_or_get` function:

1. **Dependency Detection**: Automatically detects discriminator vs legacy format
2. **External Factor Resolution**: Uses `data_field` to fetch specific IBKR fields  
3. **Calculated Factor Resolution**: Recursively resolves dependencies using discriminators
4. **Backward Compatibility**: Supports existing legacy dependency format

## Benefits

1. **Unique Discrimination**: Bid/ask prices have unique discriminators despite same class
2. **IBKR Integration**: Direct mapping from `data_field` to IBKR field names
3. **Type Safety**: Clear distinction between external vs calculated factors
4. **Exact Format Support**: Supports your specified dependency declaration format
5. **Extensible**: Easy to add new external factor types and fields

## Files Created

1. **`src/domain/entities/factor/factor_dependency_system.py`** - Enhanced discriminator system
2. **`src/infrastructure/repositories/ibkr_repo/factor/ibkr_factor_dependency_resolver.py`** - IBKR integration
3. **`FACTOR_DISCRIMINATOR_SOLUTION.md`** - This documentation

The solution directly addresses your concern about discriminator uniqueness for external factors while maintaining the exact dependency format you specified.