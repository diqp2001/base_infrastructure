# Repository Local: _create_or_get Pattern Documentation

## Overview
Local repositories implement the `_create_or_get` pattern for entity deduplication, ensuring that entities are created only if they don't already exist in the database. This pattern is fundamental to maintaining data integrity while supporting idempotent operations across the financial asset management system.

## Core Architecture

### Repository Hierarchy
```
BaseLocalRepository[DomainEntity, OrmModel] (Generic Base)
├── BaseFactorRepository (Factor-specific base)
│   ├── IndexFactorRepository
│   ├── CompanyShareFactorRepository  
│   ├── IndexFutureFactorRepository
│   └── ... (other factor repositories)
├── FinancialAssetRepository (Asset-specific base)
│   ├── IndexRepository
│   ├── CompanyShareRepository
│   ├── IndexFutureRepository
│   └── ... (other asset repositories)
└── UtilityRepository
    ├── FactorValueRepository
    ├── PortfolioRepository
    └── ... (other utility repositories)
```

### Base Local Repository Pattern
```python
from typing import Generic, TypeVar, Optional, List
from abc import ABC, abstractmethod
from sqlalchemy.orm import Session

DomainEntity = TypeVar('DomainEntity')
OrmModel = TypeVar('OrmModel')

class BaseLocalRepository(Generic[DomainEntity, OrmModel], ABC):
    """Base repository with common local database operations."""
    
    def __init__(self, session: Session):
        self.session = session
        
    @property
    @abstractmethod
    def entity_class(self) -> type:
        """Return the domain entity class."""
        pass
        
    @property  
    @abstractmethod
    def model_class(self) -> type:
        """Return the ORM model class."""
        pass
    
    @abstractmethod
    def _to_entity(self, orm_model: OrmModel) -> DomainEntity:
        """Convert ORM model to domain entity using mapper."""
        pass
        
    @abstractmethod
    def _to_model(self, entity: DomainEntity) -> OrmModel:
        """Convert domain entity to ORM model using mapper."""
        pass
```

## _create_or_get Pattern Analysis

### Standard _create_or_get Implementation

#### Example: IndexRepository._create_or_get
**File**: `/src/infrastructure/repositories/local_repo/finance/financial_assets/index_repository.py`

```python
def _create_or_get(self, symbol: str, name: str = None, 
                   index_type: str = 'Stock', currency: str = 'USD',
                   exchange: str = 'CBOE', **kwargs) -> Index_Entity:
    """
    Create index entity if it doesn't exist, otherwise return existing.
    Follows the same pattern as CompanyShareRepository._create_or_get().
    
    Args:
        symbol: Unique index symbol (primary identifier)
        name: Human-readable index name
        index_type: Type of index ('Stock', 'Bond', 'Commodity', etc.)
        currency: Base currency for index values
        exchange: Primary exchange for index
        **kwargs: Additional index-specific parameters
        
    Returns:
        Index_Entity: Created or existing index entity
        
    Raises:
        DatabaseError: If database operation fails
        ValidationError: If required parameters are invalid
    """
    try:
        # Step 1: Check if entity already exists by unique identifier
        existing_index = self.get_by_symbol(symbol)
        if existing_index:
            self.logger.debug(f"Index {symbol} already exists, returning existing entity")
            return existing_index
        
        # Step 2: Create new entity if not found
        self.logger.info(f"Creating new index: {symbol}")
        
        # Handle name defaulting
        if not name:
            name = symbol
            
        # Create domain entity
        new_index = Index_Entity(
            symbol=symbol,
            name=name,
            index_type=index_type,
            currency=currency,
            exchange=exchange,
            **kwargs
        )
        
        # Step 3: Convert to ORM model and persist
        index_model = self.mapper.to_orm(new_index)
        
        self.session.add(index_model)
        self.session.commit()
        
        # Step 4: Convert back to domain entity with database ID
        persisted_entity = self.mapper.to_domain(index_model)
        
        self.logger.info(f"Successfully created index {symbol} with ID {persisted_entity.entity_id}")
        return persisted_entity
        
    except Exception as e:
        self.session.rollback()
        self.logger.error(f"Error creating/getting index {symbol}: {str(e)}")
        raise
```

**Key Pattern Elements**:
- **Unique Identifier Check**: Uses primary unique field (symbol) to check existence
- **Idempotent Operation**: Returns existing entity without modification if found
- **Domain Entity Creation**: Creates rich domain object with business rules
- **Mapper Usage**: Converts between domain and ORM representations
- **Transaction Safety**: Proper rollback on errors
- **Logging**: Comprehensive logging for debugging and monitoring

### Factor Repository _create_or_get Pattern

#### Example: FactorRepository._create_or_get
**File**: `/src/infrastructure/repositories/local_repo/factor/factor_repository.py`

```python
def _create_or_get(self, name: str, group: str, subgroup: str) -> Factor:
    """
    Create or get a factor. Enhanced to handle dependencies if factor config is found.
    
    Args:
        name: Factor name (unique identifier)
        group: Factor group classification
        subgroup: Factor subgroup classification
        
    Returns:
        Factor: Created or existing factor entity
    """
    try:
        # Step 1: Try to get factor config from library
        factor_config = self._get_factor_config_from_library(name)
        
        if factor_config:
            # Use config-based creation with dependencies
            return self._create_or_get_with_config(name, factor_config)
        
        # Step 2: Check if factor already exists
        existing_factor = self.get_by_name(name)
        if existing_factor:
            return existing_factor
        
        # Step 3: Create basic factor without config
        self.logger.info(f"Creating basic factor: {name}")
        
        new_factor = Factor(
            name=name,
            group=group,
            subgroup=subgroup,
            frequency='daily',  # Default values
            data_type='decimal',
            source='manual'
        )
        
        # Step 4: Persist and return
        factor_model = self.mapper.to_orm(new_factor)
        self.session.add(factor_model)
        self.session.commit()
        
        return self.mapper.to_domain(factor_model)
        
    except Exception as e:
        self.session.rollback()
        self.logger.error(f"Error creating/getting factor {name}: {e}")
        raise

def _create_or_get_with_config(self, name: str, factor_config: Dict[str, Any]) -> Factor:
    """
    Create or get a factor using its configuration from the factor library.
    Handles dependencies recursively.
    """
    # Check if factor already exists
    existing_factor = self.get_by_name(name)
    if existing_factor:
        return existing_factor
        
    # Extract config values with defaults
    group = factor_config.get("group", "unknown")
    subgroup = factor_config.get("subgroup", "")
    frequency = factor_config.get("frequency", "daily")
    data_type = factor_config.get("data_type", "decimal")
    source = factor_config.get("source", "calculated")
    definition = factor_config.get("definition", "")
    
    # Step 1: Create or get dependencies first
    dependencies = self._create_or_get_dependencies(factor_config)
    
    # Step 2: Create the factor
    new_factor = Factor(
        name=name,
        group=group,
        subgroup=subgroup,
        frequency=frequency,
        data_type=data_type,
        source=source,
        definition=definition
    )
    
    # Step 3: Persist factor
    factor_model = self.mapper.to_orm(new_factor)
    self.session.add(factor_model)
    self.session.commit()
    
    factor_entity = self.mapper.to_domain(factor_model)
    
    # Step 4: Create dependency relationships
    self._create_factor_dependencies(factor_entity, dependencies)
    
    return factor_entity
```

### Geographic Entity _create_or_get Pattern

#### Example: CountryRepository._create_or_get
**File**: `/src/infrastructure/repositories/local_repo/geographic/country_repository.py`

```python
def _create_or_get(self, name: str, iso_code: Optional[str] = None,
                  continent_id: Optional[int] = None, currency: Optional[str] = None) -> Optional[Country]:
    """
    Create country entity if it doesn't exist, otherwise return existing.
    Follows the same pattern as BaseFactorRepository._create_or_get_factor().
    
    Args:
        name: Country name (primary unique identifier)
        iso_code: ISO country code (secondary identifier)
        continent_id: Foreign key to continent
        currency: Default currency code
        
    Returns:
        Country: Created or existing country entity
    """
    try:
        # Step 1: Check by primary identifier (name)
        existing_country = self.get_by_name(name)
        if existing_country:
            self.logger.debug(f"Country {name} already exists")
            return existing_country
        
        # Step 2: Check by secondary identifier if provided
        if iso_code:
            existing_by_iso = self.get_by_iso_code(iso_code)
            if existing_by_iso:
                self.logger.debug(f"Country with ISO {iso_code} already exists as {existing_by_iso.name}")
                return existing_by_iso
        
        # Step 3: Create new country
        self.logger.info(f"Creating new country: {name}")
        
        # Handle continent relationship
        if continent_id is None and hasattr(self, 'continent_repository'):
            # Default to 'Unknown' continent
            unknown_continent = self.continent_repository._create_or_get(
                name='Unknown', 
                description='Countries with unknown continent'
            )
            continent_id = unknown_continent.id
        
        new_country = Country(
            name=name,
            iso_code=iso_code,
            continent_id=continent_id,
            currency=currency
        )
        
        # Step 4: Persist
        country_model = self.mapper.to_orm(new_country)
        self.session.add(country_model)
        self.session.commit()
        
        return self.mapper.to_domain(country_model)
        
    except Exception as e:
        self.session.rollback()
        self.logger.error(f"Error creating/getting country {name}: {e}")
        return None
```

## Complex _create_or_get Patterns

### 1. Multi-Field Uniqueness
```python
def _create_or_get(self, entity_symbol: str, strike_price: float, 
                  expiry: str, option_type: str, **kwargs) -> IndexFutureOption:
    """
    Create IndexFutureOption with composite unique key.
    
    Args:
        entity_symbol: Underlying symbol
        strike_price: Option strike price
        expiry: Expiry date string (YYYYMMDD)
        option_type: 'C' for call, 'P' for put
    """
    try:
        # Step 1: Check composite uniqueness
        existing_option = self.get_by_composite_key(
            entity_symbol, strike_price, expiry, option_type
        )
        if existing_option:
            return existing_option
        
        # Step 2: Validate parameters
        if strike_price <= 0:
            raise ValueError("Strike price must be positive")
        if option_type not in ['C', 'P']:
            raise ValueError("Option type must be 'C' or 'P'")
        if not self._validate_expiry_format(expiry):
            raise ValueError("Expiry must be in YYYYMMDD format")
        
        # Step 3: Create entity with validation
        new_option = IndexFutureOption(
            symbol=entity_symbol,
            strike_price=strike_price,
            expiry_date=datetime.strptime(expiry, '%Y%m%d').date(),
            option_type=option_type,
            **kwargs
        )
        
        # Step 4: Persist
        option_model = self.mapper.to_orm(new_option)
        self.session.add(option_model)
        self.session.commit()
        
        return self.mapper.to_domain(option_model)
        
    except Exception as e:
        self.session.rollback()
        raise

def get_by_composite_key(self, symbol: str, strike: float, 
                        expiry: str, option_type: str) -> Optional[IndexFutureOption]:
    """Get option by composite unique key."""
    model = self.session.query(self.model_class)\
        .filter(
            self.model_class.symbol == symbol,
            self.model_class.strike_price == strike,
            self.model_class.expiry == expiry,
            self.model_class.option_type == option_type
        ).first()
    
    return self.mapper.to_domain(model) if model else None
```

### 2. Hierarchical Entity Creation
```python
def _create_or_get(self, ticker: str, company_name: Optional[str] = None,
                  sector: Optional[str] = None, industry: Optional[str] = None,
                  exchange_name: Optional[str] = None, **kwargs) -> CompanyShare:
    """
    Create company share with hierarchical relationships.
    Creates dependent entities (sector, industry, exchange) as needed.
    """
    try:
        # Step 1: Check if company share exists
        existing_share = self.get_by_ticker(ticker)
        if existing_share:
            return existing_share
        
        # Step 2: Create or get related entities
        sector_entity = None
        if sector:
            sector_entity = self.sector_repository._create_or_get(
                name=sector,
                classification_system='GICS'
            )
        
        industry_entity = None
        if industry and sector_entity:
            industry_entity = self.industry_repository._create_or_get(
                name=industry,
                sector_name=sector,
                classification_system='GICS'
            )
        
        exchange_entity = None
        if exchange_name:
            exchange_entity = self.exchange_repository._create_or_get(
                name=exchange_name,
                country_id=1  # Default to US
            )
        
        # Step 3: Create company if needed
        company_entity = None
        if company_name:
            company_entity = self.company_repository._create_or_get(
                name=company_name,
                sector_id=sector_entity.id if sector_entity else None,
                industry_id=industry_entity.id if industry_entity else None
            )
        
        # Step 4: Create company share
        new_share = CompanyShare(
            ticker=ticker,
            company_id=company_entity.id if company_entity else None,
            exchange_id=exchange_entity.id if exchange_entity else None,
            **kwargs
        )
        
        # Step 5: Persist
        share_model = self.mapper.to_orm(new_share)
        self.session.add(share_model)
        self.session.commit()
        
        return self.mapper.to_domain(share_model)
        
    except Exception as e:
        self.session.rollback()
        self.logger.error(f"Error creating company share {ticker}: {e}")
        raise
```

## Batch _create_or_get Operations

### Batch Processing Pattern
```python
def batch_create_or_get(self, entities_data: List[Dict[str, Any]]) -> List[DomainEntity]:
    """
    Efficiently create or get multiple entities in batch.
    
    Args:
        entities_data: List of dictionaries with entity parameters
        
    Returns:
        List of created/retrieved entities
    """
    results = []
    
    try:
        # Step 1: Batch check for existing entities
        unique_identifiers = [data.get('symbol') for data in entities_data]
        existing_entities = self._get_existing_by_identifiers(unique_identifiers)
        existing_map = {entity.symbol: entity for entity in existing_entities}
        
        # Step 2: Identify entities to create
        to_create = []
        for entity_data in entities_data:
            identifier = entity_data.get('symbol')
            if identifier in existing_map:
                results.append(existing_map[identifier])
            else:
                to_create.append(entity_data)
        
        # Step 3: Batch create new entities
        if to_create:
            new_entities = self._batch_create_new(to_create)
            results.extend(new_entities)
        
        return results
        
    except Exception as e:
        self.session.rollback()
        self.logger.error(f"Error in batch create or get: {e}")
        raise

def _get_existing_by_identifiers(self, identifiers: List[str]) -> List[DomainEntity]:
    """Get existing entities by list of identifiers."""
    models = self.session.query(self.model_class)\
        .filter(self.model_class.symbol.in_(identifiers))\
        .all()
    
    return [self.mapper.to_domain(model) for model in models]

def _batch_create_new(self, entities_data: List[Dict]) -> List[DomainEntity]:
    """Create new entities in batch."""
    new_models = []
    
    for entity_data in entities_data:
        domain_entity = self.entity_class(**entity_data)
        orm_model = self.mapper.to_orm(domain_entity)
        new_models.append(orm_model)
    
    # Bulk insert
    self.session.add_all(new_models)
    self.session.commit()
    
    # Convert back to domain entities
    return [self.mapper.to_domain(model) for model in new_models]
```

## Error Handling and Validation

### Comprehensive Error Handling
```python
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import Optional

def _create_or_get_with_validation(self, **kwargs) -> Optional[DomainEntity]:
    """Create or get with comprehensive error handling and validation."""
    
    try:
        # Step 1: Input validation
        validation_errors = self._validate_input_parameters(**kwargs)
        if validation_errors:
            raise ValidationError(f"Invalid parameters: {validation_errors}")
        
        # Step 2: Business rule validation
        business_errors = self._validate_business_rules(**kwargs)
        if business_errors:
            raise BusinessRuleError(f"Business rule violations: {business_errors}")
        
        # Step 3: Check for existing entity
        unique_identifier = kwargs.get(self._get_unique_field_name())
        existing_entity = self._get_by_unique_identifier(unique_identifier)
        
        if existing_entity:
            # Step 4: Handle existing entity (update vs return)
            if self._should_update_existing():
                return self._update_existing_entity(existing_entity, **kwargs)
            else:
                return existing_entity
        
        # Step 5: Create new entity
        return self._create_new_entity(**kwargs)
        
    except IntegrityError as e:
        self.session.rollback()
        if "unique constraint" in str(e).lower():
            # Race condition: entity created by another process
            self.logger.warning(f"Race condition detected for {unique_identifier}, retrying...")
            return self._get_by_unique_identifier(unique_identifier)
        else:
            self.logger.error(f"Database integrity error: {e}")
            raise
            
    except SQLAlchemyError as e:
        self.session.rollback()
        self.logger.error(f"Database error in _create_or_get: {e}")
        raise
        
    except (ValidationError, BusinessRuleError) as e:
        self.logger.warning(f"Validation error in _create_or_get: {e}")
        raise
        
    except Exception as e:
        self.session.rollback()
        self.logger.error(f"Unexpected error in _create_or_get: {e}")
        raise

def _validate_input_parameters(self, **kwargs) -> List[str]:
    """Validate input parameters."""
    errors = []
    
    # Required field validation
    required_fields = self._get_required_fields()
    for field in required_fields:
        if field not in kwargs or kwargs[field] is None:
            errors.append(f"Missing required field: {field}")
    
    # Type validation
    for field, value in kwargs.items():
        expected_type = self._get_field_type(field)
        if expected_type and not isinstance(value, expected_type):
            errors.append(f"Field {field} must be of type {expected_type.__name__}")
    
    return errors

def _validate_business_rules(self, **kwargs) -> List[str]:
    """Validate business rules."""
    errors = []
    
    # Example: Strike price must be positive for options
    if 'strike_price' in kwargs and kwargs['strike_price'] <= 0:
        errors.append("Strike price must be positive")
    
    # Example: Expiry date must be in future
    if 'expiry_date' in kwargs:
        from datetime import date
        if kwargs['expiry_date'] <= date.today():
            errors.append("Expiry date must be in the future")
    
    return errors
```

## Performance Optimization

### Query Optimization
```python
def _create_or_get_optimized(self, identifier: str, **kwargs) -> DomainEntity:
    """Optimized version with minimal database queries."""
    
    # Use efficient existence check
    exists_query = self.session.query(self.model_class.id)\
        .filter(self.model_class.symbol == identifier)\
        .first()
    
    if exists_query:
        # Entity exists, retrieve it
        model = self.session.query(self.model_class)\
            .filter(self.model_class.symbol == identifier)\
            .first()
        return self.mapper.to_domain(model)
    
    # Entity doesn't exist, create it
    return self._create_new_optimized(identifier, **kwargs)

def _create_new_optimized(self, identifier: str, **kwargs) -> DomainEntity:
    """Optimized entity creation."""
    
    # Create domain entity
    domain_entity = self.entity_class(symbol=identifier, **kwargs)
    
    # Convert to ORM with optimizations
    orm_model = self.mapper.to_orm(domain_entity)
    
    # Use merge() for better handling of concurrent access
    merged_model = self.session.merge(orm_model)
    self.session.commit()
    
    return self.mapper.to_domain(merged_model)
```

### Caching Layer
```python
from functools import lru_cache
from threading import RLock

class CachedRepository(BaseLocalRepository):
    """Repository with caching layer for frequently accessed entities."""
    
    def __init__(self, session: Session):
        super().__init__(session)
        self._cache = {}
        self._cache_lock = RLock()
    
    def _create_or_get_cached(self, identifier: str, **kwargs) -> DomainEntity:
        """Create or get with caching support."""
        
        # Check cache first
        with self._cache_lock:
            if identifier in self._cache:
                self.logger.debug(f"Cache hit for {identifier}")
                return self._cache[identifier]
        
        # Not in cache, check database
        entity = self._create_or_get_uncached(identifier, **kwargs)
        
        # Update cache
        with self._cache_lock:
            self._cache[identifier] = entity
        
        return entity
    
    def _invalidate_cache(self, identifier: str):
        """Invalidate cache entry."""
        with self._cache_lock:
            self._cache.pop(identifier, None)
    
    def _clear_cache(self):
        """Clear entire cache."""
        with self._cache_lock:
            self._cache.clear()
```

## Testing _create_or_get Methods

### Unit Testing
```python
class TestRepositoryCreateOrGet(unittest.TestCase):
    def setUp(self):
        self.session = create_test_session()
        self.repository = IndexRepository(self.session)
    
    def test_create_new_entity(self):
        """Test creating new entity when none exists."""
        index = self.repository._create_or_get(
            symbol="TEST_INDEX",
            name="Test Index",
            index_type="Stock"
        )
        
        assert index is not None
        assert index.symbol == "TEST_INDEX"
        assert index.entity_id is not None
    
    def test_get_existing_entity(self):
        """Test retrieving existing entity."""
        # Create first entity
        index1 = self.repository._create_or_get(
            symbol="EXISTING_INDEX",
            name="Existing Index"
        )
        
        # Try to create same entity again
        index2 = self.repository._create_or_get(
            symbol="EXISTING_INDEX",
            name="Different Name"  # Should be ignored
        )
        
        assert index1.entity_id == index2.entity_id
        assert index2.name == "Existing Index"  # Original name preserved
    
    def test_concurrent_creation(self):
        """Test handling of concurrent creation attempts."""
        import threading
        
        results = []
        errors = []
        
        def create_entity():
            try:
                entity = self.repository._create_or_get(
                    symbol="CONCURRENT_TEST",
                    name="Concurrent Test"
                )
                results.append(entity)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads trying to create same entity
        threads = [threading.Thread(target=create_entity) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Should have 5 results, all with same entity ID, no errors
        assert len(results) == 5
        assert len(errors) == 0
        assert all(r.entity_id == results[0].entity_id for r in results)
    
    def test_validation_errors(self):
        """Test proper handling of validation errors."""
        with pytest.raises(ValidationError):
            self.repository._create_or_get(
                symbol="",  # Empty symbol should fail validation
                name="Invalid Test"
            )
    
    def test_rollback_on_error(self):
        """Test that session is rolled back on errors."""
        original_count = self.session.query(self.repository.model_class).count()
        
        # Mock an error during creation
        with patch.object(self.session, 'commit', side_effect=Exception("Mock error")):
            with pytest.raises(Exception):
                self.repository._create_or_get(symbol="ERROR_TEST", name="Error Test")
        
        # Count should be unchanged
        final_count = self.session.query(self.repository.model_class).count()
        assert final_count == original_count
```

### Integration Testing
```python
class TestRepositoryIntegration(unittest.TestCase):
    def test_create_or_get_with_dependencies(self):
        """Test _create_or_get with dependent entity creation."""
        entity_service = EntityService()
        
        # This should create sector, industry, exchange, and company as needed
        company_share = entity_service._create_or_get(
            CompanyShare,
            symbol="INTEGRATION_TEST",
            company_name="Integration Test Corp",
            sector="Technology",
            industry="Software",
            exchange_name="NASDAQ"
        )
        
        assert company_share is not None
        assert company_share.ticker == "INTEGRATION_TEST"
        # Verify dependent entities were created
        assert company_share.company_id is not None
        assert company_share.exchange_id is not None
```

## Best Practices

### 1. **Consistency**
- Use consistent parameter naming across all `_create_or_get` methods
- Follow the same error handling patterns
- Maintain consistent logging levels and messages

### 2. **Performance**
- Use efficient existence checks before creation
- Implement batch operations for bulk processing
- Consider caching for frequently accessed entities

### 3. **Reliability**
- Handle race conditions gracefully
- Implement proper transaction management
- Include comprehensive error handling

### 4. **Maintainability**
- Keep validation logic separate and testable
- Document unique identifier strategies
- Use consistent mapper patterns

The `_create_or_get` pattern is fundamental to maintaining data integrity while supporting idempotent operations across the financial asset management system, ensuring that entities are created exactly once while providing efficient retrieval of existing entities.