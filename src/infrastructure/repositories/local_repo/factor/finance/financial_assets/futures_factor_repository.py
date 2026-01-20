"""
Repository class for Futures factor entities.
"""

from src.infrastructure.repositories.mappers.factor.factor_mapper import FactorMapper
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper
from ...base_factor_repository import BaseFactorRepository



class FuturesFactorRepository(BaseFactorRepository):
    """Repository for Futures factor entities with CRUD operations."""
    
    def __init__(self, db_type='sqlite'):
        super().__init__(db_type)

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
        Get or create a futures factor with dependency resolution.
        
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
                group=kwargs.get('group', 'derivatives'),
                subgroup=kwargs.get('subgroup', 'futures'),
                data_type=kwargs.get('data_type', 'numeric'),
                source=kwargs.get('source', 'market_data'),
                definition=kwargs.get('definition', f'Futures factor: {primary_key}'),
                entity_type=kwargs.get('entity_type', 'FuturesFactor')
            )
            
        except Exception as e:
            print(f"Error in get_or_create for futures factor {primary_key}: {e}")
            return None
