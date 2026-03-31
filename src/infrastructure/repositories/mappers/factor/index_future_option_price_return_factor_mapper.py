"""
Mapper for IndexFutureOptionPriceReturnFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import IndexFutureOptionPriceReturnFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.index_future_option_price_return_factor import IndexFutureOptionPriceReturnFactor
from .base_factor_mapper import BaseFactorMapper


class IndexFutureOptionPriceReturnFactorMapper(BaseFactorMapper):
    """Mapper for IndexFutureOptionPriceReturnFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'index_future_option'
    
    @property
    def model_class(self):
        return IndexFutureOptionPriceReturnFactorModel
    
    def get_factor_model(self):
        return IndexFutureOptionPriceReturnFactorModel
    
    def get_factor_entity(self):
        return IndexFutureOptionPriceReturnFactor
    
    @classmethod
    def to_domain(cls, orm_model: Optional[IndexFutureOptionPriceReturnFactorModel]) -> Optional[IndexFutureOptionPriceReturnFactor]:
        """Convert ORM model to IndexFutureOptionPriceReturnFactor domain entity."""
        if not orm_model:
            return None
        
        return IndexFutureOptionPriceReturnFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id
        )
    
    @classmethod
    def to_orm(cls, domain_entity: IndexFutureOptionPriceReturnFactor):
        """Convert IndexFutureOptionPriceReturnFactor domain entity to ORM model."""
        return IndexFutureOptionPriceReturnFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )