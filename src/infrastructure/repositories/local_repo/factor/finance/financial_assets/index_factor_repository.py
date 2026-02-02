"""
Repository class for Index factor entities.
"""

from sqlalchemy.orm import Session
from src.infrastructure.repositories.mappers.factor.index_factor_mapper import IndexFactorMapper
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper
from ...base_factor_repository import BaseFactorRepository



class IndexFactorRepository(BaseFactorRepository):
    """Repository for Index factor entities with CRUD operations."""
    
    def __init__(self, session: Session,factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = IndexFactorMapper()
        self.mapper_value = FactorValueMapper()

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

    def _create_or_get(self, primary_key: str, **kwargs):
        """
        Get or create an index factor with dependency resolution.
        
        Args:
            primary_key: Factor name identifier
            **kwargs: Additional parameters for factor creation
            
        Returns:
            Factor entity or None if creation failed
        """
        try:
            # Check existing by primary identifier (factor name)
            existing = self.get_by_all(name =primary_key,group=kwargs.get('group', 'index'),
                subgroup=kwargs.get('subgroup', 'daily'),
                data_type=kwargs.get('data_type', 'numeric'),
                source=kwargs.get('source', 'market_data'))
            if existing:
                return existing
            domain_factor = self.get_factor_entity()(name=primary_key,
                group=kwargs.get('group', 'index'),
                subgroup=kwargs.get('subgroup', 'daily'),
                data_type=kwargs.get('data_type', 'numeric'),
                source=kwargs.get('source', 'market_data'),
                definition=kwargs.get('definition', f'{self.mapper.discriminator} factor: {primary_key}')
                )
            
            # # Use sequential ID generation if factor doesn't have an ID
            # if not hasattr(domain_factor, 'id') or domain_factor.id is None:
            #     next_id = self._get_next_available_factor_id()
            #     domain_factor.id = next_id
            
            # Use FactorMapper to convert domain entity to ORM model
            # This ensures entity_type is properly set
            orm_factor = self._to_model(domain_factor)
            
            self.session.add(orm_factor)
            self.session.commit()
            if orm_factor:
                    #print(f"Created new index factor: {created_factor.name} (ID: {created_factor.id})")
                    return self._to_domain_factor(orm_factor)
            
        
            
            
        except Exception as e:
            print(f"Error in get_or_create for index factor {primary_key}: {e}")
            return None

