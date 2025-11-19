"""
Mapper for converting between Factor domain entities and ORM models.
"""

from abc import abstractmethod
from typing import Optional
from infrastructure.models.factor.factor_model import FactorModel as FactorModel
from domain.entities.factor.factor import Factor as FactorEntity



class FactorMapper:
    """Mapper for Factor domain entity and ORM model conversion."""
    @abstractmethod
    def get_factor_model(self):
        return FactorModel
    
    @abstractmethod
    def get_factor_entity(self):
        return FactorEntity

    
    @staticmethod
    def to_domain(orm_model: Optional[FactorModel]) -> Optional[FactorEntity]:
        """Convert ORM model to domain entity."""
        if not orm_model:
            return None
        
        # Since FactorBase is abstract, we'll create a concrete implementation
        # This is a generic factor that implements the abstract calculate method
        class GenericFactor(FactorEntity):
            def calculate(self, *args, **kwargs):
                # Generic implementation - could be overridden by specific factors
                from decimal import Decimal
                return Decimal('0')
        
        return GenericFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=str(orm_model.id) if orm_model.id else None
        )

    @staticmethod
    def to_orm(domain_entity: FactorEntity) -> FactorModel:
        """Convert domain entity to ORM model."""
        return FactorModel(
            id=int(domain_entity.id) if domain_entity.id and domain_entity.id.isdigit() else None,
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )
    