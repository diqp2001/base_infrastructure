# 🏭 Repository Factory Pattern - Implementation Guide

## 🎯 Purpose

This document outlines the **Repository Factory Pattern** used throughout the `base_infrastructure` project to enable proper dependency injection, reduce tight coupling, and improve testability in repository implementations.

---

## 📋 Core Pattern Structure

### 1. 🏗️ Repository Constructor Pattern

**All repositories (both local and IBKR) should follow this constructor signature:**

```python
class MyRepository(BaseRepository, MyPort):
    def __init__(self, session_or_client, local_repo=None, factory=None, **legacy_params):
        """
        Standard repository constructor.
        
        Args:
            session_or_client: Database session (local repos) or IBKR client (IBKR repos)
            local_repo: Local repository for persistence (IBKR repos only)
            factory: Repository factory for dependency injection (RECOMMENDED)
            **legacy_params: Backward compatibility for direct dependency injection
        """
        self.session = session_or_client  # or self.ib_broker for IBKR
        self.local_repo = local_repo  # IBKR repos only
        self.factory = factory
        # Store legacy params if provided for backward compatibility
```

### 2. 🔌 Dependency Resolution Pattern

**Use factory-first approach with graceful fallbacks:**

```python
def _get_or_create_dependency(self, dependency_type: str, *args) -> Optional[Any]:
    """
    Get or create dependency using factory-first approach.
    
    Args:
        dependency_type: Type of dependency (e.g., 'currency', 'company', 'exchange')
        *args: Arguments for dependency creation
        
    Returns:
        Dependency instance or fallback creation
    """
    try:
        # 1. Try factory approach (PREFERRED)
        if self.factory:
            if hasattr(self.factory, f'{dependency_type}_repo'):
                repo = getattr(self.factory, f'{dependency_type}_repo')
                if repo:
                    result = repo.get_or_create(*args)
                    if result:
                        return result
            
            # Alternative: Use factory's create_local_repositories()
            local_repos = self.factory.create_local_repositories()
            repo = local_repos.get(dependency_type)
            if repo:
                result = repo.get_or_create(*args)
                if result:
                    return result
        
        # 2. Fallback to direct repository creation (LEGACY SUPPORT)
        if hasattr(self, f'{dependency_type}_repo') and getattr(self, f'{dependency_type}_repo'):
            return getattr(self, f'{dependency_type}_repo').get_or_create(*args)
        
        # 3. Ultimate fallback - direct entity creation
        print(f"Creating {dependency_type} directly (no factory available)")
        return self._create_direct_entity(*args)
        
    except Exception as e:
        print(f"Error resolving {dependency_type} dependency: {e}")
        return self._create_direct_entity(*args)
```

---

## 🚀 Implementation Examples

### Example 1: IBKR Repository with Currency Dependency

```python
class IBKRCompanyShareRepository(IBKRFinancialAssetRepository, CompanySharePort):
    def __init__(self, ibkr_client, local_repo: CompanySharePort, factory=None, currency_repo=None):
        self.ib_broker = ibkr_client
        self.local_repo = local_repo
        self.factory = factory
        self.currency_repo = currency_repo  # Legacy support
    
    def _get_or_create_currency(self, iso_code: str, name: str) -> Currency:
        """Get or create currency using factory pattern."""
        try:
            # Factory approach (preferred)
            if self.factory and hasattr(self.factory, 'currency_repo'):
                currency_repo = self.factory.currency_repo
                if currency_repo:
                    currency = currency_repo.get_or_create(iso_code, name)
                    if currency:
                        return currency
            
            # Legacy fallback
            if self.currency_repo:
                return self.currency_repo.get_or_create(iso_code, name)
            
            # Direct creation fallback
            return Currency(id=None, name=name, symbol=iso_code)
        except Exception as e:
            print(f"Error getting currency {iso_code}: {e}")
            return Currency(id=None, name=name, symbol=iso_code)
```

### Example 2: Local Repository with Multiple Dependencies

```python
class CompanyShareRepository(FinancialAssetRepository, CompanySharePort):
    def __init__(self, session: Session, factory=None, company_repo=None, exchange_repo=None):
        super().__init__(session)
        self.factory = factory
        self.company_repo = company_repo  # Legacy
        self.exchange_repo = exchange_repo  # Legacy
    
    def _get_or_create_company(self, company_name: str) -> Company:
        """Get or create company using factory pattern."""
        try:
            if self.factory:
                local_repos = self.factory.create_local_repositories()
                company_repo = local_repos.get('company')
                if company_repo:
                    return company_repo.get_or_create(company_name)
            
            # Legacy fallback
            if self.company_repo:
                return self.company_repo.get_or_create(company_name)
            
            # Direct repository creation
            from src.infrastructure.repositories.local_repo.finance.company_repository import CompanyRepository
            company_repo = CompanyRepository(self.session)
            return company_repo.get_or_create(company_name)
        except Exception as e:
            print(f"Error resolving company dependency: {e}")
            return None
```

---

## 🏭 Factory Implementation

### Repository Factory Class

```python
class RepositoryFactory:
    def __init__(self, session: Session, ibkr_client=None):
        self.session = session
        self.ibkr_client = ibkr_client
        self._local_repositories = {}
        self._ibkr_repositories = {}

    def create_local_repositories(self) -> Dict[str, Any]:
        """Create local repositories with factory injection."""
        if not self._local_repositories:
            self._local_repositories = {
                'currency': CurrencyRepository(self.session, factory=self),
                'company_share': CompanyShareRepository(self.session, factory=self),
                'index': IndexRepository(self.session, factory=self),
                # ... add all repositories with factory=self
            }
        return self._local_repositories

    def create_ibkr_repositories(self, ibkr_client=None) -> Optional[Dict[str, Any]]:
        """Create IBKR repositories with factory injection."""
        client = ibkr_client or self.ibkr_client
        if not client:
            return None
            
        if not self._ibkr_repositories:
            local_repos = self.create_local_repositories()
            
            self._ibkr_repositories = {
                'company_share': IBKRCompanyShareRepository(
                    ibkr_client=client,
                    local_repo=local_repos['company_share'],
                    factory=self  # Pass factory for dependency injection
                ),
                'currency': IBKRCurrencyRepository(
                    ibkr_client=client,
                    local_repo=local_repos['currency'],
                    factory=self
                ),
                # ... all IBKR repos with factory=self
            }
        return self._ibkr_repositories

    @property
    def currency_repo(self):
        """Provide direct access to currency repository."""
        local_repos = self.create_local_repositories()
        return local_repos.get('currency')
```

---

## ✅ Benefits of This Pattern

### 🎯 **Improved Dependency Injection**
- Repositories can access other repositories through the factory
- Centralized dependency management
- Easier to mock dependencies in tests

### 🔗 **Reduced Coupling**
- No direct instantiation of dependencies within repositories
- Factory manages the object graph
- Single responsibility principle maintained

### 🧪 **Enhanced Testability**
- Easy to inject mock factories in unit tests
- Dependencies can be controlled and verified
- Isolated testing of repository logic

### 🔄 **Backward Compatibility**
- Legacy parameter injection still supported
- Gradual migration path for existing code
- No breaking changes to existing implementations

### 🛠️ **Maintainability**
- Single place to configure repository dependencies
- Consistent pattern across all repositories
- Easy to add new dependencies through factory

---

## 🗂️ Repository Categories

### 🏠 **Local Repositories** 
*(Session-based, persist to database)*
- Constructor: `__init__(self, session: Session, factory=None)`
- Dependencies: Other local repositories via factory
- Examples: `CurrencyRepository`, `CompanyShareRepository`, `IndexRepository`

### 🔌 **IBKR Repositories** 
*(API-based, delegate to local repositories)*
- Constructor: `__init__(self, ibkr_client, local_repo, factory=None)`
- Dependencies: Other repositories via factory (both IBKR and local)
- Examples: `IBKRCompanyShareRepository`, `IBKRCurrencyRepository`

---

## 📚 Usage Guidelines

### ✅ **DO:**
- Always add `factory=None` parameter to new repository constructors
- Use factory-first approach in dependency resolution methods
- Provide graceful fallbacks for backward compatibility
- Pass `factory=self` when creating repositories in the factory

### ❌ **DON'T:**
- Directly instantiate repositories inside other repositories (use factory)
- Remove legacy parameters until all code is migrated
- Assume factory is always available (provide fallbacks)
- Create circular dependencies between repositories

---

## 🧪 Testing with Factory Pattern

```python
# Mock factory for testing
class MockRepositoryFactory:
    def __init__(self):
        self.currency_repo = MagicMock()
        
    def create_local_repositories(self):
        return {'currency': self.currency_repo}

# Test repository with mock factory
def test_company_share_repository():
    mock_factory = MockRepositoryFactory()
    repo = CompanyShareRepository(session, factory=mock_factory)
    
    # Test that factory dependency is used
    result = repo._get_or_create_currency("USD", "US Dollar")
    mock_factory.currency_repo.get_or_create.assert_called_once_with("USD", "US Dollar")
```

---

## 🔄 Migration Strategy

1. **Phase 1**: Add `factory=None` parameter to all repository constructors
2. **Phase 2**: Update `RepositoryFactory` to pass `factory=self` to all repositories  
3. **Phase 3**: Implement factory-based dependency resolution in repositories
4. **Phase 4**: Gradually remove legacy parameter usage
5. **Phase 5**: Clean up legacy parameters once migration is complete

---

## 🎓 Key Takeaways

- **Factory Pattern** enables clean dependency injection in repositories
- **Graceful degradation** ensures backward compatibility during migration
- **Consistent structure** across all repository implementations
- **Improved testability** through dependency injection
- **Single source of truth** for repository configuration and dependencies

This pattern transforms our repository layer from tightly-coupled direct instantiation to a flexible, testable, and maintainable dependency injection system.