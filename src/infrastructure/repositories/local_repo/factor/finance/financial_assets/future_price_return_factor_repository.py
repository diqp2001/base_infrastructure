"""
Repository class for FuturePriceReturnFactor entities.
"""

from typing import Optional
from sqlalchemy.orm import Session
from src.infrastructure.repositories.mappers.factor.future_price_return_factor_mapper import FuturePriceReturnFactorMapper
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper
from ...base_factor_repository import BaseFactorRepository


class FuturePriceReturnFactorRepository(BaseFactorRepository):
    """Repository for FuturePriceReturnFactor entities with CRUD operations."""
    
    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = FuturePriceReturnFactorMapper()
        self.mapper_value = FactorValueMapper()

    @property
    def entity_class(self):
        return self.get_factor_entity()
    @property
    def model_class(self):
        return self.mapper.model_class
    def get_by_id(self, id: int):
        entity = self._to_entity(self.session
            .query(self.model_class)
            .filter(self.model_class.id == id)
            .one_or_none())
        return entity
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

    def get_or_create(self, primary_key: str, **kwargs):
        """
        Get or create a future price return factor with dependency resolution.
        
        Args:
            primary_key: Factor name identifier
            **kwargs: Additional parameters for factor creation
            
        Returns:
            FuturePriceReturnFactor entity
        """
        # Try to get existing entity first
        existing_entity = self.get_by_name(primary_key)
        
        if existing_entity:
            return existing_entity
        
        # Create new entity with default values
        new_entity = self.get_factor_entity()(
            name=primary_key,
            group=kwargs.get('group', 'financial_assets'),
            subgroup=kwargs.get('subgroup', 'derivatives'),
            frequency=kwargs.get('frequency', 'daily'),
            data_type=kwargs.get('data_type', 'float'),
            source=kwargs.get('source', 'calculated'),
            definition=kwargs.get('definition', 'Future price return factor')
        )
        
        # Save to database
        model = self._to_model(new_entity)
        self.session.add(model)
        self.session.flush()  # Flush to get the ID
        
        # Return entity with ID
        new_entity.factor_id = model.id
        return new_entity
    
    def get_by_name(self, name: str):
        """Get factor by name."""
        model = self.session.query(self.model_class).filter(
            self.model_class.name == name
        ).one_or_none()
        
        if model:
            return self._to_entity(model)
        return None