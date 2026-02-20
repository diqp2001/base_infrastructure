"""
Mapper for IndexPriceReturnFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import FactorModel
from src.domain.entities.factor.finance.financial_assets.index.index_price_return_factor import IndexPriceReturnFactor
from .base_factor_mapper import BaseFactorMapper


class IndexPriceReturnFactorMapper(BaseFactorMapper):
    """Mapper for IndexPriceReturnFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'index_price_return'
    
    def get_factor_model(self):
        return FactorModel
    
    def get_factor_entity(self):
        return IndexPriceReturnFactor
    
    def to_domain(self, orm_model: Optional[FactorModel]) -> Optional[IndexPriceReturnFactor]:
        """Convert ORM model to IndexPriceReturnFactor domain entity."""
        if not orm_model:
            return None
        
        return IndexPriceReturnFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id,
        )
    
    def to_orm(self, domain_entity: IndexPriceReturnFactor) -> FactorModel:
        """Convert IndexPriceReturnFactor domain entity to ORM model."""
        return FactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )