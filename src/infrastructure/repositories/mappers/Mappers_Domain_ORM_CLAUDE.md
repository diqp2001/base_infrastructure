# Mappers Documentation: Domain ↔ ORM Conversion

## Overview
Mappers provide the critical translation layer between pure domain entities and SQLAlchemy ORM models, enabling clean separation between business logic and data persistence. They follow the Data Mapper pattern to convert between domain objects and infrastructure models while maintaining the integrity of both layers.

## Core Architecture

### Mapper Hierarchy
```
BaseMapper (Abstract)
├── BaseFactorMapper (Factor-specific base)
│   ├── IndexFactorMapper
│   ├── CompanyShareFactorMapper
│   ├── IndexPriceReturnFactorMapper
│   ├── IndexFutureFactorMapper
│   └── ... (other factor mappers)
├── BaseFinancialAssetMapper
│   ├── IndexMapper
│   ├── CompanyShareMapper
│   ├── IndexFutureMapper
│   └── ... (other asset mappers)
└── BaseUtilityMapper
    ├── FactorValueMapper
    ├── PortfolioMapper
    └── ... (other utility mappers)
```

## IndexFactor Mapper Pattern Analysis

### Example: IndexFactorMapper
**File**: `/src/infrastructure/repositories/mappers/factor/index_factor_mapper.py`

```python
"""
Mapper for IndexFactor domain entity and ORM model conversion.
"""

from typing import Optional
from src.infrastructure.models.factor.factor import IndexFactorModel
from src.domain.entities.factor.finance.financial_assets.index.index_factor import IndexFactor
from .base_factor_mapper import BaseFactorMapper

class IndexFactorMapper(BaseFactorMapper):
    """Mapper for IndexFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'index'
    
    def get_factor_model(self):
        return IndexFactorModel
    
    @property
    def model_class(self):
        return IndexFactorModel
    
    def get_factor_entity(self):
        return IndexFactor
    
    def to_domain(self, orm_model: Optional[IndexFactorModel]) -> Optional[IndexFactor]:
        """Convert ORM model to IndexFactor domain entity."""
        if not orm_model:
            return None
        
        return IndexFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id,
        )
    
    def to_orm(self, domain_entity: IndexFactor) -> IndexFactorModel:
        """Convert IndexFactor domain entity to ORM model."""
        return IndexFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )
```

**Key Characteristics**:
- **Bidirectional Conversion**: `to_domain()` and `to_orm()` methods
- **Type Safety**: Strong typing with Optional return types
- **Null Handling**: Graceful handling of None values
- **Identity Mapping**: Proper handling of entity IDs
- **Polymorphic Support**: Discriminator property for inheritance

## Mapper Patterns and Templates

### 1. Base Factor Mapper Pattern

```python
from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Generic

DomainEntity = TypeVar('DomainEntity')
OrmModel = TypeVar('OrmModel')

class BaseFactorMapper(Generic[DomainEntity, OrmModel], ABC):
    """Abstract base class for factor mappers."""
    
    @property
    @abstractmethod
    def discriminator(self) -> str:
        """Return the polymorphic discriminator value."""
        pass
    
    @abstractmethod
    def get_factor_model(self) -> type:
        """Return the ORM model class."""
        pass
    
    @abstractmethod
    def get_factor_entity(self) -> type:
        """Return the domain entity class."""
        pass
    
    @abstractmethod
    def to_domain(self, orm_model: Optional[OrmModel]) -> Optional[DomainEntity]:
        """Convert ORM model to domain entity."""
        pass
    
    @abstractmethod
    def to_orm(self, domain_entity: DomainEntity) -> OrmModel:
        """Convert domain entity to ORM model."""
        pass
    
    def batch_to_domain(self, orm_models: List[OrmModel]) -> List[DomainEntity]:
        """Convert list of ORM models to domain entities."""
        return [self.to_domain(model) for model in orm_models if model is not None]
    
    def batch_to_orm(self, domain_entities: List[DomainEntity]) -> List[OrmModel]:
        """Convert list of domain entities to ORM models."""
        return [self.to_orm(entity) for entity in domain_entities if entity is not None]
```

### 2. Concrete Mapper Template

Based on the IndexFactorMapper pattern, here's a template for new mappers:

```python
class {EntityType}FactorMapper(BaseFactorMapper):
    """Mapper for {EntityType}Factor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return '{entity_type_lower}'
    
    def get_factor_model(self):
        return {EntityType}FactorModel
    
    @property 
    def model_class(self):
        return {EntityType}FactorModel
    
    def get_factor_entity(self):
        return {EntityType}Factor
    
    def to_domain(self, orm_model: Optional[{EntityType}FactorModel]) -> Optional[{EntityType}Factor]:
        """Convert ORM model to {EntityType}Factor domain entity."""
        if not orm_model:
            return None
        
        return {EntityType}Factor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id,
            # Add entity-specific fields here
        )
    
    def to_orm(self, domain_entity: {EntityType}Factor) -> {EntityType}FactorModel:
        """Convert {EntityType}Factor domain entity to ORM model."""
        return {EntityType}FactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
            # Add entity-specific fields here
        )
```

## Concrete Mapper Examples

### 1. CompanyShareFactorMapper
```python
class CompanyShareFactorMapper(BaseFactorMapper):
    """Mapper for CompanyShareFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'company_share'
    
    def get_factor_model(self):
        return CompanyShareFactorModel
    
    def get_factor_entity(self):
        return CompanyShareFactor
    
    def to_domain(self, orm_model: Optional[CompanyShareFactorModel]) -> Optional[CompanyShareFactor]:
        """Convert ORM model to CompanyShareFactor domain entity."""
        if not orm_model:
            return None
        
        return CompanyShareFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id,
            # Company-specific fields could be added here
            sector=getattr(orm_model, 'sector', None),
            industry=getattr(orm_model, 'industry', None)
        )
    
    def to_orm(self, domain_entity: CompanyShareFactor) -> CompanyShareFactorModel:
        """Convert CompanyShareFactor domain entity to ORM model."""
        return CompanyShareFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
            # Company-specific fields
            sector=getattr(domain_entity, 'sector', None),
            industry=getattr(domain_entity, 'industry', None)
        )
```

### 2. IndexFutureOptionFactorMapper
```python
class IndexFutureOptionFactorMapper(BaseFactorMapper):
    """Mapper for IndexFutureOptionFactor with complex derivative parameters."""
    
    @property
    def discriminator(self):
        return 'index_future_option'
    
    def get_factor_model(self):
        return IndexFutureOptionFactorModel
    
    def get_factor_entity(self):
        return IndexFutureOptionFactor
    
    def to_domain(self, orm_model: Optional[IndexFutureOptionFactorModel]) -> Optional[IndexFutureOptionFactor]:
        """Convert ORM model with option-specific fields."""
        if not orm_model:
            return None
        
        return IndexFutureOptionFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id,
            # Option-specific fields
            option_type=getattr(orm_model, 'option_type', None),
            strike_price=getattr(orm_model, 'strike_price', None),
            expiry_date=getattr(orm_model, 'expiry_date', None),
            underlying_symbol=getattr(orm_model, 'underlying_symbol', None)
        )
    
    def to_orm(self, domain_entity: IndexFutureOptionFactor) -> IndexFutureOptionFactorModel:
        """Convert domain entity with option parameters to ORM."""
        return IndexFutureOptionFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
            # Option-specific fields
            option_type=getattr(domain_entity, 'option_type', None),
            strike_price=getattr(domain_entity, 'strike_price', None),
            expiry_date=getattr(domain_entity, 'expiry_date', None),
            underlying_symbol=getattr(domain_entity, 'underlying_symbol', None)
        )
```

## IBKR Mappers Pattern

### IBKR-Specific Mapping
**Example**: `IBKRIndexFactorMapper`

```python
class IBKRIndexFactorMapper(BaseFactorMapper):
    """Mapper for IBKR-specific IndexFactor data."""
    
    @property
    def discriminator(self):
        return 'ibkr_index'
    
    def get_factor_model(self):
        return IndexFactorModel  # Same model, different source
    
    def get_factor_entity(self):
        return IndexFactor
    
    def to_domain(self, orm_model: Optional[IndexFactorModel]) -> Optional[IndexFactor]:
        """Convert IBKR ORM model to domain entity."""
        if not orm_model:
            return None
        
        return IndexFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source='ibkr',  # Force IBKR source
            definition=orm_model.definition,
            factor_id=orm_model.id,
        )
    
    def to_orm(self, domain_entity: IndexFactor) -> IndexFactorModel:
        """Convert domain entity to IBKR-marked ORM model."""
        return IndexFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source='ibkr',  # Mark as IBKR source
            definition=domain_entity.definition
        )
    
    def from_ibkr_contract(self, ibkr_contract_data: dict) -> IndexFactor:
        """Convert IBKR contract data directly to domain entity."""
        return IndexFactor(
            name=ibkr_contract_data.get('symbol', 'unknown'),
            group='market_data',
            subgroup='contract',
            frequency='real_time',
            data_type='contract',
            source='ibkr',
            definition=f"IBKR contract for {ibkr_contract_data.get('longName', 'Unknown')}"
        )
```

## FactorValue Mapper

### FactorValueMapper Pattern
```python
class FactorValueMapper:
    """Mapper for FactorValue domain entity and ORM model conversion."""
    
    def get_factor_value_model(self):
        return FactorValueModel
    
    def get_factor_value_entity(self):
        return FactorValue
    
    def to_domain(self, orm_model: Optional[FactorValueModel]) -> Optional[FactorValue]:
        """Convert ORM model to FactorValue domain entity."""
        if not orm_model:
            return None
        
        return FactorValue(
            factor_id=orm_model.factor_id,
            entity_id=orm_model.entity_id,
            date=orm_model.date,
            value=float(orm_model.value) if orm_model.value is not None else None,
            source=orm_model.source,
            quality_score=orm_model.quality_score,
            created_at=orm_model.created_at,
            updated_at=orm_model.updated_at
        )
    
    def to_orm(self, domain_entity: FactorValue) -> FactorValueModel:
        """Convert FactorValue domain entity to ORM model."""
        from decimal import Decimal
        
        return FactorValueModel(
            factor_id=domain_entity.factor_id,
            entity_id=domain_entity.entity_id,
            date=domain_entity.date,
            value=Decimal(str(domain_entity.value)) if domain_entity.value is not None else None,
            source=domain_entity.source,
            quality_score=domain_entity.quality_score
        )
    
    def batch_to_domain_with_factors(self, orm_models_with_factors: List[Tuple[FactorValueModel, FactorModel]]) -> List[Tuple[FactorValue, Factor]]:
        """Convert joined query results to domain entities."""
        results = []
        for value_model, factor_model in orm_models_with_factors:
            if value_model and factor_model:
                value_entity = self.to_domain(value_model)
                factor_entity = self._factor_mapper_for_type(factor_model.factor_type).to_domain(factor_model)
                results.append((value_entity, factor_entity))
        return results
    
    def _factor_mapper_for_type(self, factor_type: str):
        """Get appropriate factor mapper based on type."""
        mapper_registry = {
            'index_factor': IndexFactorMapper(),
            'company_share_factor': CompanyShareFactorMapper(),
            'index_future_option_factor': IndexFutureOptionFactorMapper(),
            # ... other mappings
        }
        return mapper_registry.get(factor_type, IndexFactorMapper())
```

## Financial Asset Mappers

### IndexMapper (Non-Factor Asset)
```python
class IndexMapper:
    """Mapper for Index financial asset entity."""
    
    def to_domain(self, orm_model: Optional[IndexModel]) -> Optional[Index]:
        """Convert Index ORM model to domain entity."""
        if not orm_model:
            return None
        
        return Index(
            symbol=orm_model.symbol,
            name=orm_model.name,
            index_type=orm_model.index_type,
            currency=orm_model.currency,
            exchange=orm_model.exchange,
            entity_id=orm_model.id,
            start_date=orm_model.start_date,
            end_date=orm_model.end_date
        )
    
    def to_orm(self, domain_entity: Index) -> IndexModel:
        """Convert Index domain entity to ORM model."""
        return IndexModel(
            symbol=domain_entity.symbol,
            name=domain_entity.name,
            index_type=domain_entity.index_type,
            currency=domain_entity.currency,
            exchange=domain_entity.exchange,
            start_date=domain_entity.start_date,
            end_date=domain_entity.end_date
        )
```

## Mapper Utilities and Helpers

### 1. Entity-Factor Mapping Integration
```python
# Integration with ENTITY_FACTOR_MAPPING
from src.infrastructure.repositories.mappers.factor.factor_mapper import ENTITY_FACTOR_MAPPING

class MapperRegistry:
    """Central registry for all mappers."""
    
    def __init__(self):
        self.factor_mappers = {
            'index': IndexFactorMapper(),
            'company_share': CompanyShareFactorMapper(),
            'index_future_option': IndexFutureOptionFactorMapper(),
            # ... other factor mappers
        }
        
        self.asset_mappers = {
            'index': IndexMapper(),
            'company_share': CompanyShareMapper(),
            'index_future': IndexFutureMapper(),
            # ... other asset mappers
        }
        
        self.value_mapper = FactorValueMapper()
    
    def get_factor_mapper(self, entity_class: type) -> BaseFactorMapper:
        """Get appropriate factor mapper for entity class."""
        factor_classes = ENTITY_FACTOR_MAPPING.get(entity_class, [])
        if not factor_classes:
            raise ValueError(f"No factor mapping found for {entity_class.__name__}")
        
        factor_class = factor_classes[0]  # Use primary factor class
        discriminator = self._get_discriminator_from_class(factor_class)
        
        return self.factor_mappers.get(discriminator, IndexFactorMapper())
    
    def get_asset_mapper(self, entity_class: type):
        """Get appropriate asset mapper for entity class."""
        class_name = entity_class.__name__.lower()
        return self.asset_mappers.get(class_name)
    
    def _get_discriminator_from_class(self, factor_class: type) -> str:
        """Extract discriminator from factor class name."""
        class_name = factor_class.__name__.lower()
        if 'index' in class_name:
            return 'index'
        elif 'companyshare' in class_name:
            return 'company_share'
        elif 'indexfutureoption' in class_name:
            return 'index_future_option'
        # ... other mappings
        return 'unknown'
```

### 2. Validation and Error Handling
```python
class ValidatingMapper(BaseFactorMapper):
    """Base mapper with validation capabilities."""
    
    def to_domain(self, orm_model: Optional[OrmModel]) -> Optional[DomainEntity]:
        """Convert with validation."""
        if not orm_model:
            return None
        
        # Validate ORM model before conversion
        self._validate_orm_model(orm_model)
        
        domain_entity = self._do_to_domain_conversion(orm_model)
        
        # Validate domain entity after conversion
        self._validate_domain_entity(domain_entity)
        
        return domain_entity
    
    def to_orm(self, domain_entity: DomainEntity) -> OrmModel:
        """Convert with validation."""
        # Validate domain entity before conversion
        self._validate_domain_entity(domain_entity)
        
        orm_model = self._do_to_orm_conversion(domain_entity)
        
        # Validate ORM model after conversion
        self._validate_orm_model(orm_model)
        
        return orm_model
    
    def _validate_orm_model(self, orm_model):
        """Validate ORM model constraints."""
        if not hasattr(orm_model, 'name') or not orm_model.name:
            raise ValueError("ORM model must have a non-empty name")
        
        if hasattr(orm_model, 'value') and orm_model.value is not None:
            if not isinstance(orm_model.value, (int, float, Decimal)):
                raise ValueError("ORM model value must be numeric")
    
    def _validate_domain_entity(self, domain_entity):
        """Validate domain entity business rules."""
        if not hasattr(domain_entity, 'name') or not domain_entity.name:
            raise ValueError("Domain entity must have a non-empty name")
        
        if hasattr(domain_entity, 'factor_id') and domain_entity.factor_id is not None:
            if domain_entity.factor_id <= 0:
                raise ValueError("Domain entity factor_id must be positive")
```

### 3. Performance Optimization
```python
class BatchOptimizedMapper:
    """Mapper with batch operation optimizations."""
    
    def __init__(self):
        self._conversion_cache = {}
    
    def batch_to_domain_optimized(self, orm_models: List[OrmModel]) -> List[DomainEntity]:
        """Optimized batch conversion with caching."""
        results = []
        
        # Group by model type for optimized processing
        models_by_type = {}
        for model in orm_models:
            model_type = type(model).__name__
            if model_type not in models_by_type:
                models_by_type[model_type] = []
            models_by_type[model_type].append(model)
        
        # Process each type in batch
        for model_type, models in models_by_type.items():
            mapper = self._get_mapper_for_type(model_type)
            batch_results = mapper.batch_to_domain(models)
            results.extend(batch_results)
        
        return results
    
    def _get_mapper_for_type(self, model_type: str):
        """Get cached mapper for model type."""
        if model_type not in self._conversion_cache:
            self._conversion_cache[model_type] = self._create_mapper_for_type(model_type)
        return self._conversion_cache[model_type]
```

## Testing Mappers

### 1. Unit Testing
```python
class TestIndexFactorMapper(unittest.TestCase):
    def setUp(self):
        self.mapper = IndexFactorMapper()
        
    def test_to_domain_conversion(self):
        """Test ORM to domain conversion."""
        orm_model = IndexFactorModel(
            id=1,
            name="daily_return",
            group="price",
            subgroup="return",
            frequency="daily",
            data_type="percentage",
            source="calculated",
            definition="Daily price return calculation"
        )
        
        domain_entity = self.mapper.to_domain(orm_model)
        
        assert domain_entity is not None
        assert domain_entity.name == "daily_return"
        assert domain_entity.group == "price"
        assert domain_entity.factor_id == 1
        
    def test_to_orm_conversion(self):
        """Test domain to ORM conversion."""
        domain_entity = IndexFactor(
            name="daily_return",
            group="price",
            subgroup="return",
            frequency="daily",
            data_type="percentage",
            source="calculated",
            definition="Daily price return calculation",
            factor_id=None  # Will be set by database
        )
        
        orm_model = self.mapper.to_orm(domain_entity)
        
        assert orm_model is not None
        assert orm_model.name == "daily_return"
        assert orm_model.group == "price"
        assert orm_model.factor_type == "index_factor"
        
    def test_roundtrip_conversion(self):
        """Test that conversions are symmetric."""
        original_domain = IndexFactor(
            name="test_factor",
            group="test_group",
            factor_id=None
        )
        
        # Convert to ORM and back
        orm_model = self.mapper.to_orm(original_domain)
        orm_model.id = 42  # Simulate database ID assignment
        converted_domain = self.mapper.to_domain(orm_model)
        
        assert converted_domain.name == original_domain.name
        assert converted_domain.group == original_domain.group
        assert converted_domain.factor_id == 42
        
    def test_null_handling(self):
        """Test graceful handling of None values."""
        assert self.mapper.to_domain(None) is None
        
        # Test partial data
        partial_orm = IndexFactorModel(name="partial", group="test")
        domain_entity = self.mapper.to_domain(partial_orm)
        assert domain_entity.name == "partial"
        assert domain_entity.subgroup is None
```

### 2. Integration Testing
```python
class TestMapperIntegration(unittest.TestCase):
    def test_mapper_with_repository(self):
        """Test mapper integration with repository operations."""
        entity_service = EntityService()
        repository = entity_service.get_local_repository(IndexFactor)
        
        # Create domain entity
        factor = IndexFactor(name="integration_test", group="test")
        
        # Save through repository (uses mapper internally)
        saved_factor = repository.add(factor)
        
        # Retrieve through repository (uses mapper internally)
        retrieved_factor = repository.get_by_name("integration_test")
        
        assert retrieved_factor is not None
        assert retrieved_factor.name == factor.name
        assert retrieved_factor.group == factor.group
        assert retrieved_factor.factor_id is not None
```

## Best Practices

### 1. **Consistency**
- Use consistent method names across all mappers
- Follow the same parameter ordering patterns
- Maintain consistent error handling approaches

### 2. **Performance**
- Cache mapper instances when possible
- Use batch operations for large datasets
- Minimize object creation in conversion loops

### 3. **Maintainability**
- Keep mappers focused on single entity types
- Use composition for complex mapping scenarios
- Document any business logic embedded in conversions

### 4. **Testing**
- Test both conversion directions
- Test null/edge case handling
- Include roundtrip tests to verify symmetry

The mapper pattern provides a clean, testable way to maintain separation between domain and infrastructure layers while enabling efficient data conversion in both directions.