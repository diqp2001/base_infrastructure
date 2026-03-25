"""
Mapper for IndexFutureOptionDeltaFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import IndexFutureOptionDeltaFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.index_future_option_delta_factor import IndexFutureOptionDeltaFactor
from .base_factor_mapper import BaseFactorMapper


class IndexFutureOptionDeltaFactorMapper(BaseFactorMapper):
    """Mapper for IndexFutureOptionDeltaFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'index_future_option_delta_factor'
    
    @property
    def model_class(self):
        return IndexFutureOptionDeltaFactorModel
    
    def get_factor_model(self):
        return IndexFutureOptionDeltaFactorModel
    
    def get_factor_entity(self):
        return IndexFutureOptionDeltaFactor
    
    @classmethod
    def to_domain(cls, orm_model: Optional[IndexFutureOptionDeltaFactorModel]) -> Optional[IndexFutureOptionDeltaFactor]:
        """Convert ORM model to IndexFutureOptionDeltaFactor domain entity."""
        if not orm_model:
            return None
        
        return IndexFutureOptionDeltaFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id
        )
    
    @classmethod
    def to_orm(cls, domain_entity: IndexFutureOptionDeltaFactor):
        """Convert IndexFutureOptionDeltaFactor domain entity to ORM model."""
        return IndexFutureOptionDeltaFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )