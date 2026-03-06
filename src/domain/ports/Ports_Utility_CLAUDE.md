# Domain Ports Utility Documentation

## Overview
Domain Ports serve as abstract interfaces that define contracts for repository operations in the Domain-Driven Design (DDD) architecture. They provide the boundary between the domain layer (pure business logic) and the infrastructure layer (data access implementations), enabling dependency inversion and testability.

## Core Architecture

### Port Definition Pattern
**Location**: `/src/domain/ports/`

Ports follow the Abstract Base Class (ABC) pattern with abstractmethod decorators:

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from domain.entities.{entity_path} import {EntityClass}

class {Entity}Port(ABC):
    """Abstract interface for {Entity} repository operations."""
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[{EntityClass}]:
        """Get {Entity} by ID."""
        pass
        
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[{EntityClass}]:
        """Get {Entity} by name."""
        pass
        
    # Additional abstract methods...
```

### Example: IndexFactorPort
**File**: `/src/domain/ports/factor/index_factor_port.py`

```python
"""
Index Factor Port - Domain interface for IndexFactor repository operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from domain.entities.factor.finance.financial_assets.index.index_factor import IndexFactor

class IndexFactorPort(ABC):
    """Abstract interface for IndexFactor repository operations."""

    # Currently commented out but shows the standard pattern:
    # @abstractmethod
    # def get_by_id(self, entity_id: int) -> Optional[IndexFactor]:
    #     """Get IndexFactor by ID."""
    #     pass

    # @abstractmethod  
    # def get_by_name(self, name: str) -> Optional[IndexFactor]:
    #     """Get IndexFactor by name."""
    #     pass

    # @abstractmethod
    # def get_by_group(self, group: str) -> List[IndexFactor]:
    #     """Get IndexFactor entities by group."""
    #     pass
```

## Port Categories and Hierarchy

### 1. Factor Ports (`/src/domain/ports/factor/`)
**Purpose**: Define interfaces for factor-related repository operations

**Structure**:
```
factor/
├── factor_port.py                               # Base factor operations
├── factor_value_port.py                         # Factor value operations  
├── factor_dependency_port.py                    # Factor dependency management
├── index_factor_port.py                         # Index-specific factors
├── company_share_factor_port.py                 # Company share factors
├── currency_factor_port.py                      # Currency factors
├── derivative_factor_port.py                    # Derivative factors
├── future_factor_port.py                        # Future factors
├── index_future_factor_port.py                  # Index future factors
├── index_future_option_factor_port.py           # Index future option factors
├── index_future_option_delta_factor_port.py     # Option Greeks
├── index_future_option_price_factor_port.py     # Option pricing
├── security_factor_port.py                      # Security factor base
└── ... (additional factor ports)
```

**Common Methods**:
```python
@abstractmethod
def get_by_id(self, entity_id: int) -> Optional[FactorEntity]
def get_by_name(self, name: str) -> Optional[FactorEntity]
def get_by_group(self, group: str) -> List[FactorEntity]
def get_by_subgroup(self, subgroup: str) -> List[FactorEntity]
def get_all(self) -> List[FactorEntity]
def add(self, entity: FactorEntity) -> Optional[FactorEntity]
def update(self, entity_id: int, **kwargs) -> Optional[FactorEntity]
def delete(self, entity_id: int) -> bool
```

### 2. Financial Asset Ports (`/src/domain/ports/finance/financial_assets/`)
**Purpose**: Define interfaces for financial asset repository operations

**Structure**:
```
financial_assets/
├── financial_asset_port.py                     # Base financial asset
├── security_port.py                            # Security base class
├── bond_port.py                                # Bond operations
├── cash_port.py                                # Cash operations  
├── commodity_port.py                           # Commodity operations
├── crypto_port.py                              # Cryptocurrency operations
├── currency_port.py                            # Currency operations
├── equity_port.py                              # Equity operations
├── index/
│   ├── index_port.py                          # Index operations
│   └── vix_port.py                            # VIX-specific operations
├── share/
│   ├── share_port.py                          # Share base operations
│   ├── company_share/
│   │   └── company_share_port.py              # Company share operations
│   └── etf_share_port.py                      # ETF share operations
└── derivatives/
    ├── derivative_port.py                      # Derivative base
    ├── future/
    │   ├── future_port.py                     # Future operations
    │   ├── index_future_port.py               # Index future operations
    │   └── ... (other future types)
    └── option/
        ├── option_port.py                      # Option base operations
        ├── index_future_option_port.py         # Index future option operations
        └── ... (other option types)
```

### 3. Geographic Ports (`/src/domain/ports/`)
**Purpose**: Define interfaces for geographic entity operations

**Structure**:
```
├── continent_port.py                           # Continent operations
├── country_port.py                             # Country operations  
├── sector_port.py                              # Sector operations
└── industry_port.py                            # Industry operations
```

### 4. Financial Infrastructure Ports (`/src/domain/ports/finance/`)
**Purpose**: Define interfaces for financial infrastructure operations

**Structure**:
```
finance/
├── company_port.py                             # Company operations
├── exchange_port.py                            # Exchange operations
├── instrument_port.py                          # Financial instrument operations
├── position_port.py                            # Position operations
├── financial_statements/
│   └── financial_statement_port.py            # Financial statement operations
├── holding/
│   ├── holding_port.py                        # Holding operations
│   ├── portfolio_holding_port.py              # Portfolio holding operations
│   └── portfolio_company_share_holding_port.py # Company share holdings
└── portfolio/
    ├── portfolio_port.py                      # Portfolio operations
    └── portfolio_company_share_port.py        # Portfolio company shares
```

## Port Utility Functions

### 1. Repository Contract Definition
Ports define the exact interface that repository implementations must follow:

```python
class CompanySharePort(ABC):
    """Abstract interface for CompanyShare repository operations."""
    
    @abstractmethod
    def get_by_symbol(self, symbol: str) -> Optional[CompanyShare]:
        """Get company share by trading symbol."""
        pass
        
    @abstractmethod
    def get_by_ticker(self, ticker: str) -> Optional[CompanyShare]:
        """Get company share by ticker (alias for get_by_symbol)."""
        pass
        
    @abstractmethod
    def get_by_company_name(self, company_name: str) -> List[CompanyShare]:
        """Get company shares by company name."""
        pass
        
    @abstractmethod
    def get_by_sector(self, sector: str) -> List[CompanyShare]:
        """Get company shares by sector."""
        pass
        
    @abstractmethod
    def create_or_get(self, symbol: str, **kwargs) -> Optional[CompanyShare]:
        """Create company share if it doesn't exist, otherwise return existing."""
        pass
```

### 2. Dependency Inversion Support
Ports enable the domain layer to depend on abstractions rather than concrete implementations:

```python
# Domain Service using port abstraction
class PortfolioAnalysisService:
    def __init__(self, company_share_port: CompanySharePort, 
                 factor_port: FactorPort):
        self.company_share_port = company_share_port
        self.factor_port = factor_port
    
    def analyze_portfolio_risk(self, symbols: List[str]) -> Dict[str, float]:
        """Analyze portfolio risk using injected ports."""
        results = {}
        
        for symbol in symbols:
            # Use port interface, not concrete implementation
            company_share = self.company_share_port.get_by_symbol(symbol)
            if company_share:
                volatility_factor = self.factor_port.get_by_name(f"{symbol}_volatility")
                results[symbol] = volatility_factor.value if volatility_factor else 0.0
                
        return results
```

### 3. Testing Support
Ports enable easy mocking and testing:

```python
class MockCompanySharePort(CompanySharePort):
    """Mock implementation for testing."""
    
    def __init__(self):
        self.shares = {}
    
    def get_by_symbol(self, symbol: str) -> Optional[CompanyShare]:
        return self.shares.get(symbol)
    
    def create_or_get(self, symbol: str, **kwargs) -> Optional[CompanyShare]:
        if symbol not in self.shares:
            self.shares[symbol] = CompanyShare(symbol=symbol, **kwargs)
        return self.shares[symbol]

# Test usage
def test_portfolio_analysis():
    mock_port = MockCompanySharePort()
    mock_factor_port = MockFactorPort()
    
    service = PortfolioAnalysisService(mock_port, mock_factor_port)
    results = service.analyze_portfolio_risk(['AAPL', 'MSFT'])
    
    assert 'AAPL' in results
    assert 'MSFT' in results
```

### 4. Multi-Implementation Support
Ports allow multiple repository implementations (local, IBKR, external APIs):

```python
# Local database implementation
class LocalCompanyShareRepository(CompanySharePort):
    def get_by_symbol(self, symbol: str) -> Optional[CompanyShare]:
        return self.session.query(CompanyShareModel).filter_by(symbol=symbol).first()

# IBKR API implementation  
class IBKRCompanyShareRepository(CompanySharePort):
    def get_by_symbol(self, symbol: str) -> Optional[CompanyShare]:
        contract_details = self.ibkr_client.get_contract_details(symbol)
        return self._map_to_domain_entity(contract_details)

# External API implementation
class AlphaVantageCompanyShareRepository(CompanySharePort):
    def get_by_symbol(self, symbol: str) -> Optional[CompanyShare]:
        api_data = self.alpha_vantage_client.get_company_overview(symbol)
        return self._map_to_domain_entity(api_data)
```

## Standard Port Method Patterns

### 1. Query Methods
```python
# Single entity retrieval
@abstractmethod
def get_by_id(self, entity_id: int) -> Optional[Entity]:
def get_by_name(self, name: str) -> Optional[Entity]: 
def get_by_symbol(self, symbol: str) -> Optional[Entity]:

# Multiple entity retrieval
@abstractmethod  
def get_by_group(self, group: str) -> List[Entity]:
def get_by_criteria(self, **criteria) -> List[Entity]:
def get_all(self) -> List[Entity]:

# Existence checks
@abstractmethod
def exists_by_id(self, entity_id: int) -> bool:
def exists_by_name(self, name: str) -> bool:
```

### 2. Command Methods
```python
# Entity creation
@abstractmethod
def add(self, entity: Entity) -> Optional[Entity]:
def create(self, **kwargs) -> Optional[Entity]:
def create_or_get(self, unique_field: Any, **kwargs) -> Optional[Entity]:

# Entity updates
@abstractmethod
def update(self, entity_id: int, **kwargs) -> Optional[Entity]:
def update_by_criteria(self, criteria: Dict, **updates) -> int:

# Entity deletion
@abstractmethod
def delete(self, entity_id: int) -> bool:
def delete_by_criteria(self, **criteria) -> int:
```

### 3. Specialized Methods
```python
# Factor-specific methods
@abstractmethod
def get_factors_by_entity(self, entity_id: int) -> List[Factor]:
def get_factor_values(self, factor_id: int, start_date: date, end_date: date) -> List[FactorValue]:
def calculate_factor_dependencies(self, factor_id: int) -> List[Factor]:

# Financial asset-specific methods  
@abstractmethod
def get_active_securities(self, as_of_date: date) -> List[Security]:
def get_by_exchange(self, exchange_name: str) -> List[Security]:
def get_by_currency(self, currency_code: str) -> List[Security]:

# Portfolio-specific methods
@abstractmethod
def get_holdings(self, portfolio_id: int, as_of_date: date) -> List[Holding]:
def get_positions(self, portfolio_id: int) -> List[Position]:
def calculate_portfolio_value(self, portfolio_id: int, as_of_date: date) -> Decimal:
```

## Port Implementation Guidelines

### 1. Interface Segregation
Each port should focus on a specific entity type and its related operations:

```python
# Good: Focused on IndexFactor operations only
class IndexFactorPort(ABC):
    @abstractmethod
    def get_by_index_id(self, index_id: int) -> List[IndexFactor]:
        pass
    
    @abstractmethod  
    def get_price_factors(self, index_id: int) -> List[IndexFactor]:
        pass

# Bad: Mixing concerns from multiple entity types
class MixedPort(ABC):
    @abstractmethod
    def get_index_factor(self, factor_id: int) -> IndexFactor:
        pass
        
    @abstractmethod
    def get_company_share(self, share_id: int) -> CompanyShare:  # Wrong!
        pass
```

### 2. Return Type Consistency
Use consistent return types across all ports:

```python
# Consistent return types
@abstractmethod
def get_by_id(self, entity_id: int) -> Optional[Entity]:        # Single entity or None
def get_by_criteria(self, **criteria) -> List[Entity]:         # List (empty if none found)
def add(self, entity: Entity) -> Optional[Entity]:             # Created entity or None
def delete(self, entity_id: int) -> bool:                      # Success/failure boolean
def count_by_criteria(self, **criteria) -> int:               # Count as integer
```

### 3. Parameter Validation
Ports should define parameter contracts clearly:

```python
@abstractmethod
def get_factor_values(self, factor_id: int, start_date: date, 
                     end_date: date) -> List[FactorValue]:
    """
    Get factor values within date range.
    
    Args:
        factor_id: Must be positive integer
        start_date: Must be valid date, cannot be future date
        end_date: Must be >= start_date
        
    Returns:
        List of FactorValue entities ordered by date
        
    Raises:
        ValueError: If date range is invalid
        EntityNotFoundError: If factor_id doesn't exist
    """
    pass
```

## Repository Implementation Requirements

### 1. Port Compliance
All repository implementations must implement their corresponding port:

```python
class LocalIndexFactorRepository(BaseFactorRepository, IndexFactorPort):
    """Local database implementation of IndexFactorPort."""
    
    def get_by_id(self, entity_id: int) -> Optional[IndexFactor]:
        model = self.session.query(IndexFactorModel).filter_by(id=entity_id).first()
        return self.mapper.to_domain(model) if model else None
        
    def get_by_name(self, name: str) -> Optional[IndexFactor]:
        model = self.session.query(IndexFactorModel).filter_by(name=name).first()
        return self.mapper.to_domain(model) if model else None
        
    # ... implement all abstract methods from IndexFactorPort
```

### 2. Error Handling Consistency
All implementations should handle errors consistently:

```python
def get_by_id(self, entity_id: int) -> Optional[IndexFactor]:
    try:
        if entity_id <= 0:
            raise ValueError("entity_id must be positive")
            
        model = self.session.query(IndexFactorModel).filter_by(id=entity_id).first()
        return self.mapper.to_domain(model) if model else None
        
    except SQLAlchemyError as e:
        self.logger.error(f"Database error retrieving IndexFactor {entity_id}: {e}")
        return None
    except Exception as e:
        self.logger.error(f"Unexpected error retrieving IndexFactor {entity_id}: {e}")
        return None
```

## Integration with Repository Factory

### Port-Based Repository Creation
The RepositoryFactory uses ports to ensure implementation compliance:

```python
class RepositoryFactory:
    def get_local_repository(self, entity_class: type) -> Optional[Any]:
        """Get local repository implementing appropriate port."""
        
        if entity_class == IndexFactor:
            repo = IndexFactorRepository(self.session, self)
            assert isinstance(repo, IndexFactorPort), "Repository must implement IndexFactorPort"
            return repo
            
        elif entity_class == CompanyShare:
            repo = CompanyShareRepository(self.session, self)
            assert isinstance(repo, CompanySharePort), "Repository must implement CompanySharePort"
            return repo
            
        # ... additional entity types
        
        return None
```

## Benefits of Port Pattern

### 1. **Testability**
- Easy mocking for unit tests
- Isolated testing of domain logic
- Dependency injection support

### 2. **Flexibility**
- Swap implementations without changing domain code
- Support multiple data sources (local DB, APIs, files)
- Easy to add new repository implementations

### 3. **Maintainability** 
- Clear contracts between layers
- Compile-time interface checking
- Consistent method signatures across implementations

### 4. **Domain Purity**
- Domain layer free of infrastructure concerns
- Business logic focused on business rules
- Clean architecture compliance

## Future Evolution

### Adding New Ports
1. Create new port interface extending appropriate base
2. Define abstract methods for entity-specific operations
3. Add to repository factory mapping
4. Implement concrete repositories for local and IBKR
5. Update documentation and tests

### Extending Existing Ports
1. Add new abstract methods to port interface
2. Update all existing implementations
3. Maintain backward compatibility
4. Add integration tests for new methods
5. Update usage documentation

The Domain Ports pattern provides a robust foundation for maintaining clean architecture while enabling flexibility and testability throughout the financial asset management system.