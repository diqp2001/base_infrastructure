"""
IBKR Share Factor Mapper - Mapper for ShareFactor domain entities and ORM models.
"""

from typing import Optional
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper
from src.infrastructure.models.factor.factor import FactorModel, ShareFactorModel
from src.domain.entities.factor.finance.financial_assets.share_factor.share_factor import ShareFactor


class IBKRShareFactorMapper(BaseFactorMapper):
    """Mapper for IBKR ShareFactor domain entity and ORM model conversion."""
    
    def get_factor_model(self):
        return FactorModel
    
    def get_factor_entity(self):
        return ShareFactor

    @staticmethod
    def to_domain(orm_model: Optional[FactorModel]) -> Optional[ShareFactor]:
        """Convert ORM model to ShareFactor domain entity."""
        if not orm_model:
            return None
        
        return ShareFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id,
        )

    @staticmethod
    def to_orm(domain_entity: ShareFactor) -> ShareFactorModel:
        """Convert ShareFactor domain entity to ORM model."""
        return ShareFactorModel(
            id=domain_entity.id,
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )