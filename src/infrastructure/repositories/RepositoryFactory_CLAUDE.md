# RepositoryFactory Documentation: Centralized Repository Creation and Dependency Injection

## Overview
The `RepositoryFactory` serves as the central hub for creating and managing repository instances throughout the application. It implements the Factory pattern with dependency injection, providing both local and IBKR repository implementations while managing database sessions and IBKR client connections. This factory enables clean separation between the application layer and infrastructure layer while supporting the Domain-Driven Design architecture.

## Core Architecture

### Factory Class Structure
**File**: `/src/infrastructure/repositories/repository_factory.py`

```python
class RepositoryFactory:
    """
    Repository Factory - Centralized creation and dependency injection for repositories.
    
    This factory manages the creation of local and IBKR repositories with proper dependency injection,
    following the Domain-Driven Design principles and eliminating direct parameter passing.
    """
    
    def __init__(self, session: Session, ibkr_client=None):
        """
        Initialize the factory with session and optional IBKR client.
        
        Args:
            session: SQLAlchemy database session
            ibkr_client: Optional Interactive Brokers client
        """
        self.session = session
        self.ibkr_client = ibkr_client
        
        # Repository caches for performance
        self._local_repositories = {}
        self._ibkr_repositories = {}
        
        # Initialize repository mappings
        self._init_repository_mappings()
```

### Repository Mapping Architecture
The factory maintains comprehensive mappings between domain entities and their corresponding repository implementations:

```python
def _init_repository_mappings(self):
    """Initialize mappings between domain entities and repository classes."""
    
    # Local repository mappings
    self.local_repository_mapping = {
        # Factor entities
        Factor: FactorRepository,
        FactorValue: FactorValueRepository,
        IndexFactor: IndexFactorRepository,
        CompanyShareFactor: CompanyShareFactorRepository,
        IndexPriceReturnFactor: IndexPriceReturnFactorRepository,
        IndexFutureFactor: IndexFutureFactorRepository,
        IndexFutureOptionFactor: IndexFutureOptionFactorRepository,
        
        # Financial asset entities
        Index: IndexRepository,
        CompanyShare: CompanyShareRepository,
        IndexFuture: IndexFutureRepository,
        IndexFutureOption: IndexFutureOptionRepository,
        Bond: BondRepository,
        Cash: CashRepository,
        Currency: CurrencyRepository,
        Commodity: CommodityRepository,
        
        # Geographic entities
        Country: CountryRepository,
        Continent: ContinentRepository,
        Sector: SectorRepository,
        Industry: IndustryRepository,
        
        # Portfolio entities
        Portfolio: PortfolioRepository,
        Position: PositionRepository,
        Holding: HoldingRepository,
        
        # ... 50+ total mappings
    }
    
    # IBKR repository mappings
    self.ibkr_repository_mapping = {
        # Factor entities with IBKR integration
        IndexFactor: IBKRIndexFactorRepository,
        CompanyShareFactor: IBKRShareFactorRepository,
        IndexFutureFactor: IBKRIndexFutureFactorRepository,
        IndexFutureOptionFactor: IBKRIndexFutureOptionFactorRepository,
        
        # Financial asset entities with IBKR integration
        Index: IBKRIndexRepository,
        CompanyShare: IBKRCompanyShareRepository,
        IndexFuture: IBKRIndexFutureRepository,
        IndexFutureOption: IBKRIndexFutureOptionRepository,
        Bond: IBKRBondRepository,
        Currency: IBKRCurrencyRepository,
        
        # ... 25+ IBKR mappings
    }
```

## Key Factory Methods

### 1. `get_local_repository(entity_class: type)`
**Purpose**: Returns the local repository instance for a given domain entity class

```python
def get_local_repository(self, entity_class: type):
    """
    Return the repository associated with a given domain entity class.
    
    Args:
        entity_class: Domain entity class (e.g. FactorValue, Index)
        
    Returns:
        Repository instance managing that entity
        
    Raises:
        ValueError: If no repository is registered for the entity class
    """
    try:
        # Check cache first
        if entity_class in self._local_repositories:
            return self._local_repositories[entity_class]
        
        # Get repository class from mapping
        repo_class = self.local_repository_mapping.get(entity_class)
        if not repo_class:
            raise ValueError(f"No local repository registered for entity class: {entity_class.__name__}")
        
        # Create repository instance
        repository = repo_class(self.session, factory=self)
        
        # Cache for future use
        self._local_repositories[entity_class] = repository
        
        self.logger.debug(f"Created local repository for {entity_class.__name__}")
        return repository
        
    except Exception as e:
        self.logger.error(f"Error creating local repository for {entity_class.__name__}: {e}")
        raise
```

### 2. `get_ibkr_repository(entity_class: type)`  
**Purpose**: Returns the IBKR repository instance for a given entity class

```python
def get_ibkr_repository(self, entity_class: type):
    """
    Return the IBKR repository associated with a given domain entity class.
    
    Args:
        entity_class: Domain entity class (e.g. IndexFactor, CompanyShare)
        
    Returns:
        IBKR Repository instance or None if no IBKR client available
    """
    try:
        # Check if IBKR client is available
        if not self.ibkr_client:
            self.logger.debug(f"No IBKR client available for {entity_class.__name__}")
            return None
        
        # Check cache first
        if entity_class in self._ibkr_repositories:
            return self._ibkr_repositories[entity_class]
        
        # Get IBKR repository class from mapping
        repo_class = self.ibkr_repository_mapping.get(entity_class)
        if not repo_class:
            self.logger.debug(f"No IBKR repository available for {entity_class.__name__}")
            return None
        
        # Create IBKR repository instance
        repository = repo_class(self.session, ibkr_client=self.ibkr_client, factory=self)
        
        # Cache for future use
        self._ibkr_repositories[entity_class] = repository
        
        self.logger.debug(f"Created IBKR repository for {entity_class.__name__}")
        return repository
        
    except Exception as e:
        self.logger.error(f"Error creating IBKR repository for {entity_class.__name__}: {e}")
        return None
```

### 3. `create_local_repositories()` 
**Purpose**: Legacy method for backward compatibility - creates all local repositories

```python
def create_local_repositories(self) -> dict:
    """
    Legacy method for backward compatibility.
    Creates all available local repositories.
    
    Returns:
        Dictionary with local repository implementations
    """
    repositories = {}
    
    try:
        for entity_class, repo_class in self.local_repository_mapping.items():
            try:
                repo_instance = self.get_local_repository(entity_class)
                repositories[entity_class.__name__.lower()] = repo_instance
            except Exception as e:
                self.logger.warning(f"Failed to create repository for {entity_class.__name__}: {e}")
        
        self.logger.info(f"Created {len(repositories)} local repositories")
        return repositories
        
    except Exception as e:
        self.logger.error(f"Error creating local repositories: {e}")
        return {}
```

### 4. `create_ibkr_repositories(ibkr_client=None)`
**Purpose**: Creates all IBKR repositories with optional client override

```python
def create_ibkr_repositories(self, ibkr_client=None) -> Optional[dict]:
    """
    Legacy method for backward compatibility.
    Creates all available IBKR repositories.
    
    Args:
        ibkr_client: Optional IBKR client override
        
    Returns:
        Dictionary with IBKR repository implementations or None if no client
    """
    # Use provided client or fall back to factory client
    client = ibkr_client or self.ibkr_client
    if not client:
        self.logger.warning("No IBKR client available for repository creation")
        return None
    
    repositories = {}
    
    try:
        for entity_class, repo_class in self.ibkr_repository_mapping.items():
            try:
                repo_instance = repo_class(self.session, ibkr_client=client, factory=self)
                repositories[entity_class.__name__.lower()] = repo_instance
                self._ibkr_repositories[entity_class] = repo_instance
            except Exception as e:
                self.logger.warning(f"Failed to create IBKR repository for {entity_class.__name__}: {e}")
        
        self.logger.info(f"Created {len(repositories)} IBKR repositories")
        return repositories
        
    except Exception as e:
        self.logger.error(f"Error creating IBKR repositories: {e}")
        return {}
```

### 5. `create_ibkr_client()`
**Purpose**: Creates or returns existing IBKR client

```python
def create_ibkr_client(self):
    """
    Legacy method for backward compatibility.
    Creates or returns existing IBKR client.
    
    Returns:
        IBKR client instance or None if creation fails
    """
    try:
        if not self.ibkr_client:
            # Import here to avoid circular dependencies
            from src.infrastructure.external.ibkr.ibkr_client import IBKRClient
            
            self.ibkr_client = IBKRClient()
            self.logger.info("Created new IBKR client")
        
        return self.ibkr_client
        
    except Exception as e:
        self.logger.error(f"Error creating IBKR client: {e}")
        return None
```

## Repository Creation Patterns

### Lazy Initialization Pattern
```python
def get_repository_lazy(self, entity_class: type, prefer_ibkr: bool = True):
    """
    Get repository with lazy initialization and IBKR preference.
    
    Args:
        entity_class: Domain entity class
        prefer_ibkr: If True, try IBKR repository first
        
    Returns:
        Best available repository for the entity class
    """
    try:
        # Try IBKR repository first if preferred and available
        if prefer_ibkr:
            ibkr_repo = self.get_ibkr_repository(entity_class)
            if ibkr_repo:
                return ibkr_repo
        
        # Fall back to local repository
        local_repo = self.get_local_repository(entity_class)
        return local_repo
        
    except Exception as e:
        self.logger.error(f"Error getting repository for {entity_class.__name__}: {e}")
        raise
```

### Batch Repository Creation
```python
def create_repositories_for_entities(self, entity_classes: List[type], 
                                   include_ibkr: bool = True) -> Dict[type, Any]:
    """
    Create repositories for specific entity classes.
    
    Args:
        entity_classes: List of entity classes needing repositories
        include_ibkr: Whether to include IBKR repositories
        
    Returns:
        Dictionary mapping entity classes to repository instances
    """
    repositories = {}
    
    for entity_class in entity_classes:
        try:
            # Get local repository
            local_repo = self.get_local_repository(entity_class)
            repositories[entity_class] = local_repo
            
            # Get IBKR repository if requested and available
            if include_ibkr:
                ibkr_repo = self.get_ibkr_repository(entity_class)
                if ibkr_repo:
                    # Store IBKR repo with special key
                    ibkr_key = f"{entity_class.__name__}_IBKR"
                    repositories[ibkr_key] = ibkr_repo
                    
        except Exception as e:
            self.logger.warning(f"Failed to create repository for {entity_class.__name__}: {e}")
    
    return repositories
```

## Factory Implications and Benefits

### 1. **Dependency Injection**
The factory eliminates the need for repositories to manage their own dependencies:

```python
# Before factory (tightly coupled)
class IndexFactorRepository:
    def __init__(self):
        self.session = create_session()  # Hard-coded dependency
        self.mapper = IndexFactorMapper()  # Hard-coded dependency

# After factory (dependency injection)
class IndexFactorRepository:
    def __init__(self, session: Session, factory=None):
        self.session = session  # Injected dependency
        self.factory = factory  # Injected factory for other repositories
        self.mapper = IndexFactorMapper()
```

### 2. **Centralized Configuration**
All repository creation logic is centralized, making it easy to:
- Add new repository types
- Modify repository dependencies
- Configure different environments (test, production)
- Manage IBKR client availability

```python
# Easy to add new repository type
class NewEntityRepository(BaseLocalRepository):
    pass

# Just add to factory mapping
self.local_repository_mapping[NewEntity] = NewEntityRepository
```

### 3. **Resource Management**
The factory manages expensive resources efficiently:

```python
def __init__(self, session: Session, ibkr_client=None):
    self.session = session  # Single shared session
    self.ibkr_client = ibkr_client  # Single shared IBKR client
    
    # Repository caches prevent duplicate instances
    self._local_repositories = {}
    self._ibkr_repositories = {}
```

### 4. **Environment Flexibility**
Different configurations for different environments:

```python
# Production factory with IBKR
production_factory = RepositoryFactory(
    session=production_session,
    ibkr_client=live_ibkr_client
)

# Test factory without IBKR
test_factory = RepositoryFactory(
    session=test_session,
    ibkr_client=None  # No IBKR in tests
)

# Mock factory for unit tests
mock_factory = RepositoryFactory(
    session=mock_session,
    ibkr_client=mock_ibkr_client
)
```

## Advanced Factory Features

### 1. **Repository Decorators**
```python
def with_transaction(func):
    """Decorator to wrap repository operations in transactions."""
    def wrapper(self, *args, **kwargs):
        try:
            result = func(self, *args, **kwargs)
            self.session.commit()
            return result
        except Exception as e:
            self.session.rollback()
            raise
    return wrapper

def with_retry(max_retries=3):
    """Decorator to retry operations on failure."""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(self, *args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(2 ** attempt)  # Exponential backoff
        return wrapper
    return decorator

# Enhanced factory with decorators
class EnhancedRepositoryFactory(RepositoryFactory):
    def get_local_repository_with_features(self, entity_class: type, 
                                         features: List[str] = None):
        """Get repository with additional features."""
        repo = self.get_local_repository(entity_class)
        
        if features:
            if 'transactions' in features:
                repo._create_or_get = with_transaction(repo._create_or_get)
            if 'retry' in features:
                repo._create_or_get = with_retry()(repo._create_or_get)
        
        return repo
```

### 2. **Dynamic Repository Registration**
```python
def register_repository(self, entity_class: type, repo_class: type, 
                       repo_type: str = 'local'):
    """
    Dynamically register a new repository type.
    
    Args:
        entity_class: Domain entity class
        repo_class: Repository implementation class
        repo_type: 'local' or 'ibkr'
    """
    if repo_type == 'local':
        self.local_repository_mapping[entity_class] = repo_class
        # Clear cache to force recreation
        if entity_class in self._local_repositories:
            del self._local_repositories[entity_class]
    elif repo_type == 'ibkr':
        self.ibkr_repository_mapping[entity_class] = repo_class
        if entity_class in self._ibkr_repositories:
            del self._ibkr_repositories[entity_class]
    
    self.logger.info(f"Registered {repo_type} repository {repo_class.__name__} for {entity_class.__name__}")

def unregister_repository(self, entity_class: type, repo_type: str = 'local'):
    """Remove repository registration."""
    if repo_type == 'local':
        self.local_repository_mapping.pop(entity_class, None)
        self._local_repositories.pop(entity_class, None)
    elif repo_type == 'ibkr':
        self.ibkr_repository_mapping.pop(entity_class, None)  
        self._ibkr_repositories.pop(entity_class, None)
```

### 3. **Repository Health Checking**
```python
def health_check(self) -> Dict[str, Any]:
    """
    Perform health check on factory and repositories.
    
    Returns:
        Health status report
    """
    report = {
        'timestamp': datetime.utcnow(),
        'database_session': {
            'status': 'connected' if self.session.is_active else 'disconnected',
            'connection_info': str(self.session.get_bind().url) if self.session.get_bind() else None
        },
        'ibkr_client': {
            'available': self.ibkr_client is not None,
            'connected': self.ibkr_client.ib_connection.connected_flag if self.ibkr_client else False
        },
        'repositories': {
            'local_cached': len(self._local_repositories),
            'ibkr_cached': len(self._ibkr_repositories),
            'local_available': len(self.local_repository_mapping),
            'ibkr_available': len(self.ibkr_repository_mapping)
        }
    }
    
    # Test a sample repository
    try:
        sample_repo = self.get_local_repository(Factor)
        report['sample_repository_test'] = 'success'
    except Exception as e:
        report['sample_repository_test'] = f'failed: {str(e)}'
    
    return report
```

## Integration with EntityService

### EntityService Integration Pattern
```python
class EntityService:
    def __init__(self, database_service: Optional[DatabaseService] = None, 
                 db_type: str = 'sqlite', ibkr_client=None):
        # ... initialization code ...
        
        # Create factory with optional IBKR client
        self.repository_factory = RepositoryFactory(self.session, ibkr_client)
    
    def get_local_repository(self, entity_class: type):
        """Delegate to repository factory."""
        return self.repository_factory.get_local_repository(entity_class)
    
    def get_ibkr_repository(self, entity_class: type):  
        """Delegate to repository factory."""
        return self.repository_factory.get_ibkr_repository(entity_class)
```

## Error Handling and Resilience

### Factory Error Handling
```python
class RepositoryFactoryError(Exception):
    """Base exception for repository factory errors."""
    pass

class RepositoryNotFoundError(RepositoryFactoryError):
    """Raised when no repository is found for an entity class."""
    pass

class RepositoryCreationError(RepositoryFactoryError):
    """Raised when repository creation fails."""
    pass

class RepositoryFactory:
    def get_local_repository_safe(self, entity_class: type) -> Optional[Any]:
        """
        Safe version that returns None instead of raising exceptions.
        """
        try:
            return self.get_local_repository(entity_class)
        except RepositoryFactoryError as e:
            self.logger.warning(f"Repository factory error for {entity_class.__name__}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error creating repository for {entity_class.__name__}: {e}")
            return None
    
    def get_best_repository(self, entity_class: type) -> Optional[Any]:
        """
        Get the best available repository (IBKR preferred, local fallback).
        """
        # Try IBKR first
        ibkr_repo = self.get_ibkr_repository(entity_class)
        if ibkr_repo:
            return ibkr_repo
        
        # Fall back to local
        try:
            return self.get_local_repository(entity_class)
        except Exception as e:
            self.logger.error(f"Failed to get any repository for {entity_class.__name__}: {e}")
            return None
```

## Testing the Factory

### Unit Testing
```python
class TestRepositoryFactory(unittest.TestCase):
    def setUp(self):
        self.session = create_test_session()
        self.factory = RepositoryFactory(self.session)
    
    def test_get_local_repository(self):
        """Test local repository creation."""
        repo = self.factory.get_local_repository(IndexFactor)
        
        assert repo is not None
        assert isinstance(repo, IndexFactorRepository)
        assert repo.session == self.session
        assert repo.factory == self.factory
    
    def test_repository_caching(self):
        """Test that repositories are cached."""
        repo1 = self.factory.get_local_repository(IndexFactor)
        repo2 = self.factory.get_local_repository(IndexFactor)
        
        assert repo1 is repo2  # Same instance
    
    def test_ibkr_repository_without_client(self):
        """Test IBKR repository when no client available."""
        repo = self.factory.get_ibkr_repository(IndexFactor)
        
        assert repo is None
    
    def test_ibkr_repository_with_client(self):
        """Test IBKR repository with mock client."""
        mock_client = MockIBKRClient()
        factory_with_ibkr = RepositoryFactory(self.session, mock_client)
        
        repo = factory_with_ibkr.get_ibkr_repository(IndexFactor)
        
        assert repo is not None
        assert isinstance(repo, IBKRIndexFactorRepository)
        assert repo.ibkr_client == mock_client
    
    def test_unknown_entity_class(self):
        """Test error handling for unknown entity class."""
        class UnknownEntity:
            pass
        
        with pytest.raises(ValueError):
            self.factory.get_local_repository(UnknownEntity)
    
    def test_health_check(self):
        """Test factory health check."""
        health = self.factory.health_check()
        
        assert 'timestamp' in health
        assert 'database_session' in health
        assert 'ibkr_client' in health
        assert 'repositories' in health
        assert health['database_session']['status'] == 'connected'
```

### Integration Testing
```python
class TestFactoryIntegration(unittest.TestCase):
    def test_factory_with_entity_service(self):
        """Test factory integration with EntityService."""
        entity_service = EntityService()
        
        # Factory should be created automatically
        assert entity_service.repository_factory is not None
        
        # Should be able to get repositories through EntityService
        repo = entity_service.get_local_repository(IndexFactor)
        assert repo is not None
        
        # Should be able to create entities
        factor = entity_service._create_or_get(
            IndexFactor, "test_factor", group="test"
        )
        assert factor is not None
```

## Performance Considerations

### Memory Management
- **Repository Caching**: Prevents duplicate instances
- **Lazy Loading**: Repositories created only when needed
- **Resource Sharing**: Single session and IBKR client shared across repositories

### Scalability
- **Thread Safety**: Factory can be used in multi-threaded applications
- **Connection Pooling**: Delegates connection management to database layer
- **Resource Cleanup**: Proper cleanup of IBKR connections

## Best Practices

### 1. **Factory Usage**
- Always use factory for repository creation
- Don't instantiate repositories directly
- Use appropriate repository type (local vs IBKR)

### 2. **Error Handling**
- Use safe methods when uncertain about entity support
- Handle factory errors appropriately
- Log repository creation issues

### 3. **Testing**
- Mock factory for unit tests
- Use separate factory instances for different test scenarios
- Test both successful and error cases

The `RepositoryFactory` provides a robust, scalable foundation for repository management while maintaining clean architecture principles and supporting both local and IBKR integration patterns throughout the financial asset management system.