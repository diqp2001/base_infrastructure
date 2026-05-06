"""
Repository Registry - Type-based dependency resolution for repositories.

This registry provides clean, type-safe dependency injection without string keys.
Usage: registry.get(InstrumentRepository) -> InstrumentRepository instance
"""

from typing import TypeVar, Type, Optional, Dict, Any, Union
from abc import ABC
import inspect

T = TypeVar('T')


class RepositoryRegistry:
    """
    Central registry for repository instances with type-based resolution.
    
    Features:
    - Type-safe dependency resolution: registry.get(InstrumentRepository)
    - Automatic registration by type
    - Support for multiple data sources (local, IBKR)
    - No string keys, no boilerplate
    """
    
    def __init__(self):
        """Initialize empty repository registry."""
        self._repositories: Dict[Type, Any] = {}
        self._providers: Dict[str, 'RepositoryProvider'] = {}
    
    def register(self, repository_type: Type[T], instance: T) -> None:
        """
        Register a repository instance by its type.
        
        Args:
            repository_type: The repository interface/class type
            instance: The repository instance
        """
        if not repository_type or not instance:
            raise ValueError("Both repository_type and instance are required")
            
        self._repositories[repository_type] = instance
    
    def get(self, repository_type: Type[T]) -> Optional[T]:
        """
        Get repository instance by type.
        
        Args:
            repository_type: The repository interface/class type
            
        Returns:
            Repository instance or None if not found
        """
        return self._repositories.get(repository_type)
    
    def register_provider(self, name: str, provider: 'RepositoryProvider') -> None:
        """
        Register a repository provider (for local/IBKR abstraction).
        
        Args:
            name: Provider name (e.g., 'local', 'ibkr')
            provider: RepositoryProvider instance
        """
        self._providers[name] = provider
    
    def get_provider(self, name: str) -> Optional['RepositoryProvider']:
        """Get provider by name."""
        return self._providers.get(name)
    
    def has(self, repository_type: Type[T]) -> bool:
        """Check if repository type is registered."""
        return repository_type in self._repositories
    
    def list_registered_types(self) -> list:
        """Get list of all registered repository types."""
        return list(self._repositories.keys())
    
    def clear(self) -> None:
        """Clear all registered repositories (useful for testing)."""
        self._repositories.clear()
        self._providers.clear()


class RepositoryProvider(ABC):
    """
    Abstract base class for repository providers.
    
    Providers handle different data sources (local SQLAlchemy, IBKR, etc.)
    and register their repositories with the registry.
    """
    
    def __init__(self, registry: RepositoryRegistry):
        """
        Initialize provider with registry reference.
        
        Args:
            registry: The central repository registry
        """
        self.registry = registry
    
    def register_repositories(self) -> None:
        """Register all repositories provided by this provider."""
        raise NotImplementedError("Subclasses must implement register_repositories")
    
    def get_repository(self, repository_type: Type[T]) -> Optional[T]:
        """
        Get repository by type (convenience method).
        
        Args:
            repository_type: The repository interface/class type
            
        Returns:
            Repository instance or None if not found
        """
        return self.registry.get(repository_type)


def auto_register_repositories(
    registry: RepositoryRegistry,
    repository_instances: Dict[str, Any],
    type_mapping: Optional[Dict[str, Type]] = None
) -> None:
    """
    Automatically register repositories based on their class types.
    
    Args:
        registry: The repository registry
        repository_instances: Dict mapping names to repository instances
        type_mapping: Optional explicit type mappings for interface resolution
    """
    for name, instance in repository_instances.items():
        if not instance:
            continue
            
        # Get the repository type - prefer interface over implementation
        repo_type = None
        
        # Try explicit mapping first
        if type_mapping and name in type_mapping:
            repo_type = type_mapping[name]
        else:
            # Auto-detect based on class hierarchy
            instance_class = type(instance)
            
            # Look for port/interface implementations
            for base in inspect.getmro(instance_class):
                if base.__name__.endswith('Port') and base != ABC:
                    repo_type = base
                    break
            
            # Fallback to concrete class if no port found
            if not repo_type:
                repo_type = instance_class
        
        if repo_type:
            registry.register(repo_type, instance)


# Utility decorator for automatic repository registration
def repository(registry: RepositoryRegistry):
    """
    Decorator to automatically register repository classes.
    
    Usage:
        @repository(my_registry)
        class MyRepository(MyRepositoryPort):
            pass
    """
    def decorator(cls):
        # This would be used if instantiating repositories via decorator
        # For now, we'll use the factory pattern instead
        return cls
    return decorator