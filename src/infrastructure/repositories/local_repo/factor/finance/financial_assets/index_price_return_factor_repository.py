"""
Repository class for IndexPriceReturnFactor entities.
"""

from sqlalchemy.orm import Session
from src.infrastructure.repositories.mappers.factor.index_price_return_factor_mapper import IndexPriceReturnFactorMapper
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper
from ...base_factor_repository import BaseFactorRepository


class IndexPriceReturnFactorRepository(BaseFactorRepository):
    """Repository for IndexPriceReturnFactor entities with CRUD operations."""
    
    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = IndexPriceReturnFactorMapper()
        self.mapper_value = FactorValueMapper()

    @property
    def entity_class(self):
        return self.get_factor_entity()

    def get_factor_model(self):
        return self.mapper.get_factor_model()
    
    def get_factor_entity(self):
        return self.mapper.get_factor_entity()

    def get_factor_value_model(self):
        return self.mapper_value.get_factor_value_model()
    
    def get_factor_value_entity(self):
        return self.mapper_value.get_factor_value_entity()

    def _to_entity(self, infra_obj):
        """Convert ORM model to domain entity."""
        return self.mapper.to_domain(infra_obj)
    
    def _to_model(self, entity):
        """Convert domain entity to ORM model."""
        return self.mapper.to_orm(entity)

    def _create_or_get(self,entity_cls, primary_key: str, **kwargs):
        """
        Get or create an index price return factor with dependency resolution.
        
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
            
            domain_factor = self.get_factor_entity()(
                name=primary_key,
                group=kwargs.get('group', 'return'),
                subgroup=kwargs.get('subgroup', 'daily'),
                data_type=kwargs.get('data_type', 'numeric'),
                source=kwargs.get('source', 'calculated'),
                definition=kwargs.get('definition', f'{self.mapper.discriminator} factor: {primary_key}')
            )
            
            # Use FactorMapper to convert domain entity to ORM model
            # This ensures entity_type is properly set
            orm_factor = self._to_model(domain_factor)
            
            self.session.add(orm_factor)
            self.session.commit()
            if orm_factor:
                return self._to_entity(orm_factor)
            
        except Exception as e:
            print(f"Error in get_or_create for index price return factor {primary_key}: {e}")
            return None