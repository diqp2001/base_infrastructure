"""
Mapper for converting between CountryFactorValue domain entities and ORM models.
"""

from typing import Optional
from decimal import Decimal
from domain.entities.factor.country_factor_value import CountryFactorValue as CountryFactorValueEntity
from infrastructure.models.factor.factor_model import FactorValue as FactorValueModel


class CountryFactorValueMapper:
    """Mapper for CountryFactorValue domain entity and ORM model conversion."""

    @staticmethod
    def to_domain(orm_model: Optional[FactorValueModel]) -> Optional[CountryFactorValueEntity]:
        """Convert ORM model to domain entity."""
        if not orm_model:
            return None
        
        return CountryFactorValueEntity(
            id=orm_model.id,
            factor_id=orm_model.factor_id,
            entity_id=orm_model.entity_id,
            date=orm_model.date,
            value=Decimal(str(orm_model.value)) if orm_model.value is not None else Decimal('0'),
            # CountryFactorValue specific fields - would typically come from other sources or entity data
            country_code=None,        # Would be determined from the entity or factor metadata
            currency=None,            # Would be determined from the country or factor metadata
            inflation_adjusted=False, # Default assumption
            gdp_relative=False        # Default assumption
        )

    @staticmethod
    def to_orm(domain_entity: CountryFactorValueEntity) -> FactorValueModel:
        """Convert domain entity to ORM model."""
        return FactorValueModel(
            id=domain_entity.id,
            factor_id=domain_entity.factor_id,
            entity_id=domain_entity.entity_id,
            date=domain_entity.date,
            value=domain_entity.value
        )