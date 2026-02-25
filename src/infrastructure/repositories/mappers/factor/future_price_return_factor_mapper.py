"""
Mapper for FuturePriceReturnFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import FuturePriceReturnFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.future.future_price_return_factor import FuturePriceReturnFactor
from .base_factor_mapper import BaseFactorMapper


class FuturePriceReturnFactorMapper(BaseFactorMapper):
    """Mapper for FuturePriceReturnFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'future'
    @property
    def model_class(self):
        return FuturePriceReturnFactorModel
    
    def get_factor_model(self):
        return FuturePriceReturnFactorModel
    
    def get_factor_entity(self):
        return FuturePriceReturnFactor
    
    def to_domain(self, orm_model: Optional[FuturePriceReturnFactorModel]) -> Optional[FuturePriceReturnFactor]:
        """Convert ORM model to FuturePriceReturnFactor domain entity."""
        if not orm_model:
            return None
        
        return FuturePriceReturnFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            #frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition
        )
    
    def to_orm(self, domain_entity: FuturePriceReturnFactor) -> FuturePriceReturnFactorModel:
        """Convert FuturePriceReturnFactor domain entity to ORM model."""
        return FuturePriceReturnFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            #frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )