"""
Mapper for IndexFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import IndexFactorModel
from src.domain.entities.factor.finance.financial_assets.index_factor import IndexFactor
from .base_factor_mapper import BaseFactorMapper


class IndexFactorMapper(BaseFactorMapper):
    """Mapper for IndexFactor domain entity and ORM model conversion."""
    @property
    def discriminator(self):
        return 'index'
    
    def get_factor_model(self):
        return IndexFactorModel
    
    
    
    def get_factor_entity(self):
        return IndexFactor
    
    
    def to_domain(self, orm_model: Optional[IndexFactorModel]) -> Optional[IndexFactor]:
        """Convert ORM model to IndexFactor domain entity."""
        if not orm_model:
            return None
        
        return IndexFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id,
        )
    
    
    def to_orm(self, domain_entity: IndexFactor) -> IndexFactorModel:
        """Convert IndexFactor domain entity to ORM model."""
        return IndexFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )