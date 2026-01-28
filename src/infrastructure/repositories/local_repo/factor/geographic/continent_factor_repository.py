"""
Repository class for Continent factor entities.
"""

from sqlalchemy.orm import Session
from src.infrastructure.repositories.mappers.factor.factor_mapper import FactorMapper
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper
from ..base_factor_repository import BaseFactorRepository


class ContinentFactorRepository(BaseFactorRepository):
    """Repository for Continent factor entities with CRUD operations."""
    
    def __init__(self, session: Session,factory=None):
        super().__init__(session)
        self.factory = factory

    def get_factor_model(self):
        return FactorMapper().get_factor_model()
    
    def get_factor_entity(self):
        return FactorMapper().get_factor_entity()
    
    def get_factor_value_model(self):
        return FactorValueMapper().get_factor_value_model()
    
    def get_factor_value_entity(self):
        return FactorValueMapper().get_factor_value_entity()

    def get_or_create(self, primary_key: str, **kwargs):
        """
        Get or create a continent factor with dependency resolution.
        
        Args:
            primary_key: Factor name identifier
            **kwargs: Additional parameters for factor creation
            
        Returns:
            Factor entity or None if creation failed
        """
        try:
            # Check existing by primary identifier (factor name)
            existing = self.get_by_name(primary_key)
            if existing:
                return existing
            
            # Create new factor using base _create_or_get method
            return self._create_or_get(
                name=primary_key,
                group=kwargs.get('group', 'geographic'),
                subgroup=kwargs.get('subgroup', 'continent'),
                data_type=kwargs.get('data_type', 'categorical'),
                source=kwargs.get('source', 'geographic_data'),
                definition=kwargs.get('definition', f'Continent factor: {primary_key}'),
                entity_type=kwargs.get('entity_type', 'continent')
            )
            
        except Exception as e:
            print(f"Error in get_or_create for continent factor {primary_key}: {e}")
            return None