"""
Repository class for Country factor entities.
"""

from sqlalchemy.orm import Session
from src.infrastructure.repositories.mappers.factor.country_factor_mapper import CountryFactorMapper
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper
from .base_factor_repository import BaseFactorRepository


class CountryFactorRepository(BaseFactorRepository):
    """Repository for Country factor entities with CRUD operations."""
    
    def __init__(self, session: Session):
        super().__init__(session)
        self.mapper = CountryFactorMapper()

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
        return CountryFactorMapper.to_domain(infra_obj)
    
    def _to_model(self, entity):
        """Convert domain entity to ORM model."""
        return CountryFactorMapper.to_orm(entity)

    def get_or_create(self, primary_key: str, **kwargs):
        """
        Get or create a country factor with dependency resolution.
        
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
                group=kwargs.get('group', 'country'),
                subgroup=kwargs.get('subgroup', 'geography'),
                data_type=kwargs.get('data_type', 'string'),
                source=kwargs.get('source', 'geography_data'),
                definition=kwargs.get('definition', f'Country factor: {primary_key}'),
                entity_type=kwargs.get('entity_type', 'country')
            )
            
        except Exception as e:
            print(f"Error in get_or_create for country factor {primary_key}: {e}")
            return None