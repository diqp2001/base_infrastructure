"""
Repository class for Index Future factor entities.
"""

from sqlalchemy.orm import Session
from src.infrastructure.repositories.mappers.factor.index_future_factor_mapper import IndexFutureFactorMapper
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper
from ...base_factor_repository import BaseFactorRepository



class IndexFutureFactorRepository(BaseFactorRepository):
    """Repository for Index Future factor entities with CRUD operations."""
    
    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = IndexFutureFactorMapper()
    @property
    def entity_class(self):
        return self.get_factor_entity()
    def get_factor_model(self):
        return self.mapper.get_factor_model()
    
    def get_factor_entity(self):
        return self.mapper.get_factor_entity()

    
    def get_factor_value_model(self):
        return FactorValueMapper().get_factor_value_model()
    
    def get_factor_value_entity(self):
        return FactorValueMapper().get_factor_value_entity()

    def _to_entity(self, infra_obj):
        """Convert ORM model to domain entity."""
        return IndexFutureFactorMapper.to_domain(infra_obj)
    
    def _to_model(self, entity):
        """Convert domain entity to ORM model."""
        return IndexFutureFactorMapper.to_orm(entity)

    def get_or_create(self, primary_key: str, **kwargs):
        """
        Get or create an index future factor with dependency resolution.
        
        Args:
            primary_key: Factor name identifier
            **kwargs: Additional parameters for factor creation
            
        Returns:
            Factor entity or None if creation failed
        """
        try:
            # Check existing by primary identifier (factor name)
            existing = self.get_by_all(
                name=primary_key,
                group=kwargs.get('group', 'return'),
                subgroup=kwargs.get('subgroup', 'daily'),
                factor_type=kwargs.get('factor_type', 'index_price_return'),
                data_type=self.mapper.discriminator,
                source=kwargs.get('source', 'calculated')
            )
            if existing:
                
                return self._to_entity(existing)
            
            # Create new factor using base _create_or_get method
            return self._create_or_get(
                name=primary_key,
                group=kwargs.get('group', 'derivatives'),
                subgroup=kwargs.get('subgroup', 'index_futures'),
                data_type=kwargs.get('data_type', 'numeric'),
                source=kwargs.get('source', 'market_data'),
                definition=kwargs.get('definition', f'Index Future factor: {primary_key}'),
                entity_type=kwargs.get('entity_type', 'IndexFuturesFactor'),
                underlying_index=kwargs.get('underlying_index')
            )
            
        except Exception as e:
            print(f"Error in get_or_create for index future factor {primary_key}: {e}")
            return None