"""
Dependency Registry - Central registry for managing repository dependencies and automatic resolution.

This registry manages all repository instances and their dependencies to enable automatic
foreign key dependency resolution when _create_or_get methods are called.
"""

from typing import Dict, Any, Optional, Type
from sqlalchemy.orm import Session
from src.infrastructure.repositories.dependency_resolver_mixin import DependencyResolverMixin


class DependencyRegistry:
    """
    Central registry for managing repository dependencies.
    
    This registry:
    1. Maintains instances of all repositories
    2. Maps foreign key relationships to appropriate repositories
    3. Provides automatic dependency resolution for any repository operation
    """
    
    def __init__(self, session: Session):
        self.session = session
        self._repositories: Dict[str, Any] = {}
        self._dependency_map: Dict[str, str] = {}
        self._initialize_repositories()
        self._setup_dependency_mappings()
    
    def _initialize_repositories(self):
        """Initialize all repository instances."""
        # Import repositories here to avoid circular imports
        from src.infrastructure.repositories.local_repo.geographic.country_repository import CountryRepository
        from src.infrastructure.repositories.local_repo.geographic.industry_repository import IndustryRepository
        from src.infrastructure.repositories.local_repo.finance.company_repository import CompanyRepository
        from src.infrastructure.repositories.local_repo.finance.exchange_repository import ExchangeRepository
        from src.infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository
        from src.infrastructure.repositories.local_repo.finance.financial_assets.index_repository import IndexRepository
        from src.infrastructure.repositories.local_repo.finance.financial_assets.future_repository import FutureRepository
        
        # Initialize all repositories
        self._repositories['country'] = CountryRepository(self.session)
        self._repositories['industry'] = IndustryRepository(self.session)
        self._repositories['company'] = CompanyRepository(self.session)
        self._repositories['exchange'] = ExchangeRepository(self.session)
        self._repositories['company_share'] = CompanyShareRepository(self.session)
        self._repositories['index'] = IndexRepository(self.session)
        self._repositories['future'] = FutureRepository(self.session)
    
    def _setup_dependency_mappings(self):
        """Setup mappings from foreign key columns to repository names."""
        self._dependency_map = {
            'country_id': 'country',
            'industry_id': 'industry', 
            'company_id': 'company',
            'exchange_id': 'exchange',
            'index_id': 'index',
            'sector_id': 'sector',
            'continent_id': 'continent'
        }
    
    def get_repository(self, repository_name: str):
        """Get a repository instance by name."""
        return self._repositories.get(repository_name)
    
    def resolve_dependencies_for_entity(self, entity_type: str, **entity_kwargs) -> Dict[str, Any]:
        """
        Resolve all dependencies for a specific entity type.
        
        Args:
            entity_type: Type of entity being created ('company_share', 'company', etc.)
            **entity_kwargs: Entity creation parameters
            
        Returns:
            Dict with resolved foreign key values
        """
        repository = self.get_repository(entity_type)
        if not repository:
            return entity_kwargs
        
        # Get foreign key dependencies for this repository
        dependencies = self._get_dependencies_for_repository(repository)
        
        resolved_kwargs = entity_kwargs.copy()
        
        for fk_column, dependency_repo_name in dependencies.items():
            if fk_column in resolved_kwargs and resolved_kwargs[fk_column] is not None:
                continue
                
            dependency_repo = self.get_repository(dependency_repo_name)
            if dependency_repo:
                resolved_id = self._resolve_dependency(fk_column, dependency_repo, entity_kwargs)
                if resolved_id:
                    resolved_kwargs[fk_column] = resolved_id
        
        return resolved_kwargs
    
    def _get_dependencies_for_repository(self, repository) -> Dict[str, str]:
        """
        Get dependency mappings for a specific repository.
        
        Args:
            repository: Repository instance
            
        Returns:
            Dict mapping FK columns to repository names
        """
        dependencies = {}
        
        if not hasattr(repository, 'model_class'):
            return dependencies
        
        # Get foreign keys from the model
        from sqlalchemy.inspection import inspect
        
        try:
            mapper = inspect(repository.model_class)
            for column in mapper.columns:
                if column.foreign_keys:
                    fk_column = column.name
                    if fk_column in self._dependency_map:
                        dependencies[fk_column] = self._dependency_map[fk_column]
        except Exception as e:
            print(f"Error getting dependencies for {type(repository).__name__}: {str(e)}")
        
        return dependencies
    
    def _resolve_dependency(self, fk_column: str, dependency_repo, entity_kwargs: Dict[str, Any]) -> Optional[int]:
        """
        Resolve a single dependency by calling the appropriate _create_or_get method.
        
        Args:
            fk_column: Foreign key column name
            dependency_repo: Repository that handles this dependency
            entity_kwargs: Original entity parameters
            
        Returns:
            ID of resolved entity or None
        """
        try:
            if fk_column == 'country_id':
                # Resolve Country dependency
                country = dependency_repo._create_or_get(
                    name=entity_kwargs.get('country_name', 'United States'),
                    iso_code=entity_kwargs.get('country_code', 'US'),
                    continent=entity_kwargs.get('continent', 'North America'),
                    currency=entity_kwargs.get('currency', 'USD')
                )
                return country.id if country else 1
                
            elif fk_column == 'industry_id':
                # Resolve Industry dependency
                industry = dependency_repo._create_or_get(
                    name=entity_kwargs.get('industry_name', 'Technology'),
                    sector_name=entity_kwargs.get('sector_name', 'Information Technology'),
                    classification_system=entity_kwargs.get('classification_system', 'GICS')
                )
                return industry.id if industry else 1
                
            elif fk_column == 'company_id':
                # Resolve Company dependency - with recursive dependency resolution
                company_kwargs = {
                    'name': entity_kwargs.get('company_name', f"{entity_kwargs.get('ticker', 'UNKNOWN')} Inc."),
                    'legal_name': entity_kwargs.get('company_legal_name'),
                    'country_id': entity_kwargs.get('country_id'),
                    'industry_id': entity_kwargs.get('industry_id'),
                    'country_name': entity_kwargs.get('country_name', 'United States'),
                    'industry_name': entity_kwargs.get('industry_name', 'Technology')
                }
                
                # Recursively resolve Company's dependencies
                resolved_company_kwargs = self.resolve_dependencies_for_entity('company', **company_kwargs)
                
                company = dependency_repo._create_or_get(**resolved_company_kwargs)
                return company.id if company else 1
                
            elif fk_column == 'exchange_id':
                # Resolve Exchange dependency - with recursive dependency resolution
                exchange_kwargs = {
                    'name': entity_kwargs.get('exchange_name', 'NASDAQ'),
                    'legal_name': entity_kwargs.get('exchange_legal_name'),
                    'country_id': entity_kwargs.get('country_id'),
                    'country_name': entity_kwargs.get('country_name', 'United States')
                }
                
                # Recursively resolve Exchange's dependencies
                resolved_exchange_kwargs = self.resolve_dependencies_for_entity('exchange', **exchange_kwargs)
                
                exchange = dependency_repo._create_or_get(**resolved_exchange_kwargs)
                return exchange.id if exchange else 1
                
            else:
                # Generic fallback
                name = entity_kwargs.get(f"{fk_column.replace('_id', '')}_name", 'Default')
                entity = dependency_repo._create_or_get(name=name)
                return entity.id if entity else 1
                
        except Exception as e:
            print(f"Error resolving dependency {fk_column}: {str(e)}")
            return 1  # Return default ID on error
    
    def create_or_get_with_dependencies(self, entity_type: str, **entity_kwargs):
        """
        High-level method to create or get an entity with full dependency resolution.
        
        Args:
            entity_type: Type of entity to create
            **entity_kwargs: Entity parameters
            
        Returns:
            Created or existing entity
        """
        # Get the repository for this entity type
        repository = self.get_repository(entity_type)
        if not repository:
            raise ValueError(f"No repository found for entity type: {entity_type}")
        
        # Resolve all dependencies
        resolved_kwargs = self.resolve_dependencies_for_entity(entity_type, **entity_kwargs)
        
        # Call the repository's _create_or_get method
        if hasattr(repository, '_create_or_get'):
            return repository._create_or_get(**resolved_kwargs)
        else:
            raise ValueError(f"Repository {type(repository).__name__} does not have _create_or_get method")