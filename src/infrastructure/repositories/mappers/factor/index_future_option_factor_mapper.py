"""
Mapper for IndexFutureOptionFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import IndexFutureOptionFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.index_future_option_factor import IndexFutureOptionFactor
from .base_factor_mapper import BaseFactorMapper


class IndexFutureOptionFactorMapper(BaseFactorMapper):
    """Mapper for IndexFutureOptionFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'index_future_option_factor'
    
    @property
    def model_class(self):
        return IndexFutureOptionFactorModel
    
    def get_factor_model(self):
        return IndexFutureOptionFactorModel
    
    def get_factor_entity(self):
        return IndexFutureOptionFactor
    
    @classmethod
    def to_domain(cls, orm_model: Optional[IndexFutureOptionFactorModel]) -> Optional[IndexFutureOptionFactor]:
        """Convert ORM model to IndexFutureOptionFactor domain entity."""
        if not orm_model:
            return None
        
        return IndexFutureOptionFactor(
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
    def to_orm(cls, domain_entity: IndexFutureOptionFactor):
        """Convert IndexFutureOptionFactor domain entity to ORM model."""
        return IndexFutureOptionFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )