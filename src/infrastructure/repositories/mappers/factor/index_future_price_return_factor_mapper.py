"""
Mapper for IndexFuturePriceReturnFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import IndexFuturePriceReturnFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.future.index_future_price_return_factor import IndexFuturePriceReturnFactor
from .base_factor_mapper import BaseFactorMapper


class IndexFuturePriceReturnFactorMapper(BaseFactorMapper):
    """Mapper for IndexFuturePriceReturnFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'index_future'
    
    @property
    def model_class(self):
        return IndexFuturePriceReturnFactorModel
    
    def get_factor_model(self):
        return IndexFuturePriceReturnFactorModel
    
    def get_factor_entity(self):
        return IndexFuturePriceReturnFactor
    
    def to_domain(self, orm_model: Optional[IndexFuturePriceReturnFactorModel]) -> Optional[IndexFuturePriceReturnFactor]:
        """Convert ORM model to IndexFuturePriceReturnFactor domain entity."""
        if not orm_model:
            return None
        
        return IndexFuturePriceReturnFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition
        )
    
    def to_orm(self, domain_entity: IndexFuturePriceReturnFactor) -> IndexFuturePriceReturnFactorModel:
        """Convert IndexFuturePriceReturnFactor domain entity to ORM model."""
        return IndexFuturePriceReturnFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )