"""
Dependency Resolver Mixin - Handles automatic foreign key dependency resolution for repository _create_or_get methods.

This mixin ensures that when _create_or_get is called for any repository, all dependent entities 
(based on foreign keys in the model) get their _create_or_get methods called automatically.
"""

from typing import Dict, Any, Optional, Type
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session
from sqlalchemy import ForeignKey


class DependencyResolverMixin:
    """
    Mixin that provides automatic foreign key dependency resolution.
    
    When _create_or_get is called on a repository, this mixin will:
    1. Analyze the model's foreign key relationships
    2. Automatically resolve dependencies by calling _create_or_get on dependent repositories
    3. Return the resolved foreign key values for use in entity creation
    """
    
    def __init__(self, session: Session, **kwargs):
        self.session = session
        self._dependency_repositories = {}
        super().__init__(**kwargs)
    
    def register_dependency_repository(self, foreign_key_column: str, repository_instance):
        """
        Register a repository instance for handling a specific foreign key dependency.
        
        Args:
            foreign_key_column: The column name of the foreign key (e.g., 'country_id')
            repository_instance: Repository instance that handles the dependency
        """
        self._dependency_repositories[foreign_key_column] = repository_instance
    
    def resolve_dependencies(self, entity_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve all foreign key dependencies automatically.
        
        Args:
            entity_kwargs: Dictionary containing entity creation parameters
            
        Returns:
            Dict with resolved foreign key values
        """
        resolved_kwargs = entity_kwargs.copy()
        
        # Get foreign key columns for the model
        foreign_keys = self._get_foreign_key_dependencies()
        
        for fk_column, fk_info in foreign_keys.items():
            # Check if FK value is already provided
            if fk_column in resolved_kwargs and resolved_kwargs[fk_column] is not None:
                continue
                
            # Try to resolve dependency
            resolved_id = self._resolve_single_dependency(fk_column, fk_info, entity_kwargs)
            if resolved_id:
                resolved_kwargs[fk_column] = resolved_id
        
        return resolved_kwargs
    
    def _get_foreign_key_dependencies(self) -> Dict[str, Dict[str, Any]]:
        """
        Extract foreign key information from the model class.
        
        Returns:
            Dict mapping FK column names to FK metadata
        """
        if not hasattr(self, 'model_class'):
            return {}
            
        model = self.model_class
        foreign_keys = {}
        
        # Use SQLAlchemy inspection to get foreign keys
        mapper = inspect(model)
        
        for column in mapper.columns:
            if column.foreign_keys:
                for fk in column.foreign_keys:
                    foreign_keys[column.name] = {
                        'column': column.name,
                        'referenced_table': fk.column.table.name,
                        'referenced_column': fk.column.name,
                        'foreign_key': fk
                    }
        
        return foreign_keys
    
    def _resolve_single_dependency(self, fk_column: str, fk_info: Dict[str, Any], 
                                  entity_kwargs: Dict[str, Any]) -> Optional[int]:
        """
        Resolve a single foreign key dependency.
        
        Args:
            fk_column: Foreign key column name
            fk_info: Foreign key metadata
            entity_kwargs: Original entity creation parameters
            
        Returns:
            Resolved foreign key ID or None if unable to resolve
        """
        referenced_table = fk_info['referenced_table']
        
        # Check if we have a registered repository for this dependency
        if fk_column in self._dependency_repositories:
            repository = self._dependency_repositories[fk_column]
            return self._call_dependency_create_or_get(repository, fk_column, entity_kwargs)
        
        # Try to resolve using default strategies based on table name
        return self._resolve_by_table_name(referenced_table, entity_kwargs)
    
    def _call_dependency_create_or_get(self, repository, fk_column: str, 
                                     entity_kwargs: Dict[str, Any]) -> Optional[int]:
        """
        Call _create_or_get on the dependency repository with appropriate parameters.
        
        Args:
            repository: Repository instance to call
            fk_column: Foreign key column being resolved
            entity_kwargs: Original entity creation parameters
            
        Returns:
            ID of created/existing entity or None
        """
        try:
            # Map common parameter patterns based on foreign key type
            if fk_column == 'country_id':
                entity = repository._create_or_get(
                    name=entity_kwargs.get('country_name', 'United States'),
                    iso_code=entity_kwargs.get('country_code', 'US'),
                    continent=entity_kwargs.get('continent', 'North America'),
                    currency=entity_kwargs.get('currency', 'USD')
                )
            elif fk_column == 'industry_id':
                entity = repository._create_or_get(
                    name=entity_kwargs.get('industry_name', 'Technology'),
                    sector_name=entity_kwargs.get('sector_name', 'Information Technology'),
                    classification_system=entity_kwargs.get('classification_system', 'GICS')
                )
            elif fk_column == 'company_id':
                entity = repository._create_or_get(
                    name=entity_kwargs.get('company_name', f"{entity_kwargs.get('ticker', 'UNKNOWN')} Inc."),
                    legal_name=entity_kwargs.get('company_legal_name'),
                    country_id=entity_kwargs.get('country_id', 1),
                    industry_id=entity_kwargs.get('industry_id', 1)
                )
            elif fk_column == 'exchange_id':
                entity = repository._create_or_get(
                    name=entity_kwargs.get('exchange_name', 'NASDAQ'),
                    legal_name=entity_kwargs.get('exchange_legal_name'),
                    country_id=entity_kwargs.get('country_id', 1)
                )
            else:
                # Generic fallback - try to call with name parameter
                name = entity_kwargs.get(f"{fk_column.replace('_id', '')}_name", 'Default')
                entity = repository._create_or_get(name=name)
            
            return entity.id if entity else None
            
        except Exception as e:
            print(f"Error resolving dependency {fk_column}: {str(e)}")
            return None
    
    def _resolve_by_table_name(self, referenced_table: str, 
                              entity_kwargs: Dict[str, Any]) -> Optional[int]:
        """
        Fallback resolution strategy based on referenced table name.
        
        Args:
            referenced_table: Name of the referenced table
            entity_kwargs: Original entity creation parameters
            
        Returns:
            Default ID for the table type
        """
        # Provide default IDs for common tables
        default_ids = {
            'countries': 1,    # Default to USA
            'industries': 1,   # Default to Technology
            'exchanges': 1,    # Default to NYSE/NASDAQ
            'companies': 1,    # Default company
            'indices': 1,      # Default index
            'sectors': 1,      # Default sector
            'continents': 1    # Default continent
        }
        
        return default_ids.get(referenced_table, 1)
    
    def create_with_dependency_resolution(self, create_method, **entity_kwargs):
        """
        Wrapper method that resolves dependencies before calling the actual create method.
        
        Args:
            create_method: The actual _create_or_get method to call
            **entity_kwargs: Entity creation parameters
            
        Returns:
            Created/existing entity
        """
        # Resolve all dependencies
        resolved_kwargs = self.resolve_dependencies(entity_kwargs)
        
        # Call the actual create method with resolved parameters
        return create_method(**resolved_kwargs)