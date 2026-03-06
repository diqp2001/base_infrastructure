"""
Repository class for Company Share Option Price Return factor entities.
"""

from typing import Optional
from sqlalchemy.orm import Session
from src.domain.entities.factor.factor_dependency import FactorDependency
from src.infrastructure.repositories.mappers.factor.company_share_option_price_return_factor_mapper import CompanyShareOptionPriceReturnFactorMapper
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper
from ...base_factor_repository import BaseFactorRepository


class CompanyShareOptionPriceReturnFactorRepository(BaseFactorRepository):
    """Repository for Company Share Option Price Return factor entities with CRUD operations."""
    
    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = CompanyShareOptionPriceReturnFactorMapper()

    @property
    def entity_class(self):
        return self.get_factor_entity()

    def get_factor_model(self):
        return self.mapper.get_factor_model()
    
    def get_factor_entity(self):
        return self.mapper.get_factor_entity()

    @property
    def model_class(self):
        return self.mapper.model_class

    def get_by_id(self, id: int):
        return (
            self.session
            .query(self.model_class)
            .filter(self.model_class.id == id)
            .one_or_none()
        )
    
    def get_factor_value_model(self):
        return FactorValueMapper().get_factor_value_model()
    
    def get_factor_value_entity(self):
        return FactorValueMapper().get_factor_value_entity()

    def _to_entity(self, infra_obj):
        """Convert ORM model to domain entity."""
        return self.mapper.to_domain(infra_obj)
    
    def _to_infra(self, entity):
        """Convert domain entity to ORM model."""
        return self.mapper.to_orm(entity)