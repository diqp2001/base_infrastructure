"""
Mapper for ShareTargetFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import FactorModel
from src.domain.entities.factor.finance.financial_assets.share_factor.share_target_factor import ShareTargetFactor
from .base_factor_mapper import BaseFactorMapper


class ShareTargetFactorMapper(BaseFactorMapper):
    """Mapper for ShareTargetFactor domain entity and ORM model conversion."""
    
    def get_factor_model(self):
        return FactorModel
    
    def get_factor_entity(self):
        return ShareTargetFactor
    
    @classmethod
    def to_domain(cls, orm_model: Optional[FactorModel]) -> Optional[ShareTargetFactor]:
        """Convert ORM model to ShareTargetFactor domain entity."""
        if not orm_model:
            return None
        
        return ShareTargetFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id,
        )
    
    @classmethod
    def to_orm(cls, domain_entity: ShareTargetFactor) -> FactorModel:
        """Convert ShareTargetFactor domain entity to ORM model."""
        return FactorModel(
            id=domain_entity.id,
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
            entity_type='share_target'
        )