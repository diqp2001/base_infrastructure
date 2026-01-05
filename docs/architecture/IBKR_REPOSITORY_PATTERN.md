# IBKR Repository Architecture Pattern

## Overview

This document describes the architectural pattern for implementing Interactive Brokers (IBKR) data repositories alongside local persistence repositories. The pattern ensures clean separation of concerns between data acquisition and persistence while maintaining consistency through common interfaces.

## Architecture Principles

### Dual Repository Pattern

The winning pattern implements two repositories per asset type, each with clearly defined responsibilities:

1. **Local Repository** (`infrastructure.repositories.local_repo.*`)
   - Responsible for persistence operations
   - Handles SQLAlchemy models and ORM mapping
   - Manages database constraints and lifecycle
   - Maps between ORM entities and domain entities

2. **IBKR Repository** (`infrastructure.repositories.ibkr_repo.*`)
   - Responsible for data acquisition and normalization
   - Interfaces with Interactive Brokers API (`ibapi.contract.Contract`, `ContractDetails`)
   - Applies IBKR-specific business rules (symbol resolution, exchanges, multipliers, expiries)
   - Translates IBKR objects directly into domain entities
   - Delegates persistence to local repository

### Data Flow Pattern

```
IBKR API → IBKR Repository → Domain Entities → Local Repository → Database
```

**Critical**: The IBKR repository does NOT follow this anti-pattern:
```
IBKR API → ORM → Database → ORM → Domain Entity  ❌
```

Instead, it follows the correct pattern:
```
IBKR API → Domain Entity → Local Repository → Database  ✅
```

## Implementation Structure

### 1. Common Ports (Interfaces)

All repositories implement the same port interface, ensuring the service layer remains infrastructure-agnostic.

**Location**: `src/domain/ports/`

```python
# src/domain/ports/financial_assets/index_future_port.py
from abc import ABC, abstractmethod
from typing import Optional
from src.domain.entities.finance.financial_assets.derivatives.future.index_future import IndexFuture

class IndexFuturePort(ABC):
    """Port interface for Index Future repositories"""
    
    @abstractmethod
    def get_or_create(self, symbol: str) -> Optional[IndexFuture]:
        """Get or create an index future by symbol"""
        pass
    
    @abstractmethod
    def get_by_symbol(self, symbol: str) -> Optional[IndexFuture]:
        """Get index future by symbol"""
        pass
```

### 2. Local Repository Implementation

**Location**: `src/infrastructure/repositories/local_repo/finance/financial_assets/`

```python
# Example: IndexFutureRepository (already exists)
from src.domain.ports.financial_assets.index_future_port import IndexFuturePort

class IndexFutureRepository(FutureRepository, IndexFuturePort):
    def __init__(self, session: Session):
        super().__init__(session)
    
    def get_or_create(self, symbol: str) -> Optional[IndexFuture]:
        # Implementation handles SQLAlchemy persistence
        # Maps between ORM models and domain entities
        pass
```

### 3. IBKR Repository Implementation

**Location**: `src/infrastructure/repositories/ibkr_repo/finance/financial_assets/`

```python
# Example: IBKRIndexFutureRepository (partially exists)
from ibapi.contract import Contract
from src.domain.ports.financial_assets.index_future_port import IndexFuturePort

class IBKRIndexFutureRepository(IndexFuturePort):
    def __init__(self, ibkr_client, local_repo: IndexFuturePort):
        self.ibkr = ibkr_client
        self.local_repo = local_repo
    
    def get_or_create(self, symbol: str) -> Optional[IndexFuture]:
        # 1. Fetch from IBKR API
        contract = self._fetch_contract(symbol)
        # 2. Apply IBKR-specific rules
        contract_details = self._apply_ibkr_rules(contract)
        # 3. Convert to domain entity
        entity = self._contract_to_domain(contract_details)
        # 4. Delegate persistence to local repository
        return self.local_repo.get_or_create_entity(entity)
        
    def _fetch_contract(self, symbol: str) -> Contract:
        # IBKR API interaction
        pass
        
    def _apply_ibkr_rules(self, contract: Contract) -> ContractDetails:
        # Symbol resolution, exchange mapping, multipliers, etc.
        pass
        
    def _contract_to_domain(self, contract_details: ContractDetails) -> IndexFuture:
        # Direct translation to domain entity
        pass
```

### 4. Service Layer (Infrastructure-Agnostic)

**Location**: `src/application/services/`

```python
class FinancialAssetService:
    def __init__(self, index_future_port: IndexFuturePort):
        self.index_futures = index_future_port
    
    def get_or_create_index_future(self, symbol: str) -> Optional[IndexFuture]:
        return self.index_futures.get_or_create(symbol)
```

**Key Points**:
- Service does NOT know if data comes from IBKR
- Service does NOT know if data comes from local database  
- Service does NOT know how creation rules differ
- This is intentional and correct

### 5. Composition Root (Configuration)

The choice between repositories is made ONCE at application startup:

**Local-only Configuration**:
```python
local_repo = IndexFutureRepository(session)
service = FinancialAssetService(index_future_port=local_repo)
```

**IBKR-backed Configuration**:
```python
local_repo = IndexFutureRepository(session)
ibkr_repo = IBKRIndexFutureRepository(
    ibkr_client=ibkr_client,
    local_repo=local_repo
)
service = FinancialAssetService(index_future_port=ibkr_repo)
```

## Benefits of This Design

### 1. Clean Separation of Concerns
- **Local repositories**: Focus solely on persistence
- **IBKR repositories**: Focus solely on data acquisition and normalization
- **Service layer**: Focus solely on business logic

### 2. Infrastructure Agnostic
- Service layer code never changes regardless of data source
- Easy to swap between local and IBKR implementations
- Testing becomes trivial (mock ports)

### 3. Correct Data Flow
- No wasteful IBKR → ORM → DB → ORM → Domain transformations
- Direct path from external API to domain entities
- Persistence is delegated, not duplicated

### 4. Scalability
- Can easily add more data sources (Bloomberg, Reuters, etc.)
- Each data source follows the same pattern
- Service layer remains unchanged

### 5. Parameter Consistency
- Creation rules differ because data sources differ
- No parameter mismatches between repositories
- Each repository knows its own context

## Implementation Guidelines

### Repository Responsibilities

**Local Repository SHOULD**:
- Handle SQLAlchemy models and sessions
- Manage database constraints and relationships
- Implement caching strategies
- Handle transaction management
- Map between ORM and domain entities

**Local Repository should NOT**:
- Know about external APIs
- Implement business rules specific to data sources
- Handle data normalization from external sources

**IBKR Repository SHOULD**:
- Interface with IBKR API
- Apply IBKR-specific business rules
- Handle IBKR error conditions
- Normalize IBKR data to domain entities
- Delegate persistence to local repository

**IBKR Repository should NOT**:
- Know about SQLAlchemy or database details
- Implement generic business logic
- Handle persistence directly

### Error Handling

**IBKR Repository**: Handle IBKR-specific errors (connection issues, invalid symbols, rate limits)
**Local Repository**: Handle database errors (constraint violations, connection issues)
**Service Layer**: Handle business logic errors

### Testing Strategy

**Unit Testing**:
- Mock the ports in service layer tests
- Test repositories in isolation
- Use in-memory databases for local repository tests

**Integration Testing**:
- Test IBKR repository with real IBKR API (if available)
- Test full composition with both repositories

## Migration Path

For existing implementations:

1. **Create Port Interfaces**: Define common interfaces first
2. **Update Local Repositories**: Implement the ports
3. **Create IBKR Repositories**: Implement IBKR-specific logic
4. **Update Service Layer**: Use ports instead of concrete classes
5. **Update Composition Root**: Configure repository choice at startup

This pattern provides a robust, scalable, and maintainable architecture for handling multiple data sources while keeping the domain logic clean and testable.