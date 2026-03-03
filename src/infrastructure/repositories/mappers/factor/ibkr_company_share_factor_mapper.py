"""
IBKR Company Share Factor Mapper - Mapper for CompanyShareFactor domain entities and ORM models.
"""

from typing import Optional
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper
from src.infrastructure.models.factor.factor import FactorModel
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import CompanyShareFactor


class IBKRCompanyShareFactorMapper(BaseFactorMapper):
    """Mapper for IBKR CompanyShareFactor domain entity and ORM model conversion."""
    
    def get_factor_model(self):
        return FactorModel
    
    def get_factor_entity(self):
        return CompanyShareFactor

    @staticmethod
    def to_domain(orm_model: Optional[FactorModel]) -> Optional[CompanyShareFactor]:
        """Convert ORM model to CompanyShareFactor domain entity."""
        if not orm_model:
            return None
        
        return CompanyShareFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id,
        )

    @staticmethod
    def to_orm(domain_entity: CompanyShareFactor) -> FactorModel:
        """Convert CompanyShareFactor domain entity to ORM model."""
        return FactorModel(
            id=domain_entity.id,
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )