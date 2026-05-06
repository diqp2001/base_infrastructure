"""
New Repository Factory - Clean, type-based repository factory using registry pattern.

This is the redesigned factory that replaces the massive RepositoryFactory with:
- Type-based dependency resolution (no string keys)
- Clean provider pattern for local vs IBKR repositories
- Minimal boilerplate and easy extensibility
- DDD-compliant dependency injection
"""

from typing import TypeVar, Type, Optional, Dict, Any
from sqlalchemy.orm import Session

from .registry.repository_registry import RepositoryRegistry
from .providers.local_repository_provider import LocalRepositoryProvider
from .providers.ibkr_repository_provider import IBKRRepositoryProvider

# Domain ports for type hints
from src.domain.ports.finance.instrument_port import InstrumentPort
from src.domain.ports.finance.financial_assets.financial_asset_port import FinancialAssetPort

T = TypeVar('T')


class RepositoryFactory:
    """
    Clean repository factory using registry pattern.
    
    Features:
    - Type-based resolution: factory.get(InstrumentPort)
    - Provider pattern for local/IBKR separation
    - No string keys, no boilerplate properties
    - Easy extensibility for new data sources
    
    Usage:
        factory = RepositoryFactory(session, ibkr_client)
        instrument_repo = factory.get(InstrumentPort)
        company_share_repo = factory.get(CompanyShareRepository)
    """
    
    def __init__(self, session: Session, ibkr_client=None):
        """
        Initialize repository factory with data sources.
        
        Args:
            session: SQLAlchemy session for local repositories
            ibkr_client: Optional Interactive Brokers client
        """
        self.session = session
        self.ibkr_client = ibkr_client
        
        # Create central registry
        self.registry = RepositoryRegistry()
        
        # Create and register providers
        self.local_provider = LocalRepositoryProvider(self.registry, session)
        self.local_provider.register_repositories()
        self.registry.register_provider('local', self.local_provider)
        
        # Register IBKR provider if client is available
        if ibkr_client:
            self.ibkr_provider = IBKRRepositoryProvider(self.registry, ibkr_client)
            self.ibkr_provider.register_repositories()
            self.registry.register_provider('ibkr', self.ibkr_provider)
        else:
            self.ibkr_provider = None
    
    def get(self, repository_type: Type[T]) -> Optional[T]:
        """
        Get repository by type.
        
        Args:
            repository_type: Repository interface or concrete class
            
        Returns:
            Repository instance or None if not found
            
        Example:
            instrument_repo = factory.get(InstrumentPort)
            ibkr_instrument_repo = factory.get(IBKRInstrumentRepository)
        """
        return self.registry.get(repository_type)
    
    def get_local(self, repository_type: Type[T]) -> Optional[T]:
        """
        Get local (SQLAlchemy) repository by type.
        
        Args:
            repository_type: Repository interface or concrete class
            
        Returns:
            Local repository instance or None if not found
        """
        if self.local_provider:
            return self.local_provider.get_repository(repository_type)
        return None
    
    def get_ibkr(self, repository_type: Type[T]) -> Optional[T]:
        """
        Get IBKR repository by type.
        
        Args:
            repository_type: Repository interface or concrete class
            
        Returns:
            IBKR repository instance or None if not found or no IBKR client
        """
        if self.ibkr_provider:
            return self.ibkr_provider.get_repository(repository_type)
        return None
    
    def has_ibkr_client(self) -> bool:
        """Check if IBKR client is available."""
        return self.ibkr_client is not None
    
    def list_available_types(self) -> list:
        """Get list of all registered repository types."""
        return self.registry.list_registered_types()
    
    def create_ibkr_client(self) -> Optional[Any]:
        """
        Create IBKR client if not already provided (fallback method).
        
        Returns:
            IBKR client instance or None if creation failed
        """
        if self.ibkr_client:
            return self.ibkr_client
            
        try:
            from src.application.services.misbuffet.brokers.broker_factory import create_interactive_brokers_broker
            
            ib_config = {
                'host': "127.0.0.1",
                'port': 7497,
                'client_id': 1,
                'timeout': 60,
                'account_id': 'DEFAULT',
                'enable_logging': True
            }
            
            client = create_interactive_brokers_broker(**ib_config)
            client.connect()
            
            self.ibkr_client = client
            
            # Register IBKR provider now that client is available
            if not self.ibkr_provider:
                self.ibkr_provider = IBKRRepositoryProvider(self.registry, client)
                self.ibkr_provider.register_repositories()
                self.registry.register_provider('ibkr', self.ibkr_provider)
            
            return client
            
        except Exception as e:
            print(f"Error creating IBKR client: {e}")
            return None


# Convenience factory function
def create_repository_factory(session: Session, ibkr_client=None) -> RepositoryFactory:
    """
    Create a repository factory with the given data sources.
    
    Args:
        session: SQLAlchemy session
        ibkr_client: Optional Interactive Brokers client
        
    Returns:
        Configured RepositoryFactory instance
    """
    return RepositoryFactory(session, ibkr_client)


# Migration helpers for existing code
class LegacyFactoryAdapter:
    """
    Adapter to help migrate from old string-based factory to new type-based factory.
    
    This provides backward compatibility during migration.
    """
    
    def __init__(self, new_factory: RepositoryFactory):
        """Initialize with new factory instance."""
        self.factory = new_factory
        
        # String-to-type mapping for migration
        self._type_mapping = {
            'instrument': InstrumentPort,
            'financial_asset': FinancialAssetPort,
            # Add more mappings as needed during migration
        }
    
    def get_by_string(self, repository_name: str):
        """
        Get repository by string name (legacy compatibility).
        
        Args:
            repository_name: String name from old factory
            
        Returns:
            Repository instance or None
        """
        repo_type = self._type_mapping.get(repository_name)
        if repo_type:
            return self.factory.get(repo_type)
        return None
    
    def __getattr__(self, name: str):
        """
        Handle legacy property access like factory.instrument_local_repo.
        
        Args:
            name: Property name
            
        Returns:
            Repository instance or raises AttributeError
        """
        # Handle legacy property patterns
        if name.endswith('_local_repo'):
            repo_name = name.replace('_local_repo', '')
            return self.get_by_string(repo_name)
        elif name.endswith('_ibkr_repo'):
            repo_name = name.replace('_ibkr_repo', '')
            # Would need IBKR-specific mapping
            pass
        
        raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")