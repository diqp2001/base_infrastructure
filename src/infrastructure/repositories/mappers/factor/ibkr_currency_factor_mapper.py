"""
IBKR Currency Factor Mapper - Mapper for CurrencyFactor domain entities and ORM models.
"""

from typing import Optional
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper
from src.infrastructure.models.factor.factor import FactorModel, CurrencyFactorModel
from src.domain.entities.factor.finance.financial_assets.currency_factor import CurrencyFactor


class IBKRCurrencyFactorMapper(BaseFactorMapper):
    """Mapper for IBKR CurrencyFactor domain entity and ORM model conversion."""
    
    def get_factor_model(self):
        return FactorModel
    
    def get_factor_entity(self):
        return CurrencyFactor

    @staticmethod
    def to_domain(orm_model: Optional[FactorModel]) -> Optional[CurrencyFactor]:
        """Convert ORM model to CurrencyFactor domain entity."""
        if not orm_model:
            return None
        
        return CurrencyFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id,
        )

    @staticmethod
    def to_orm(domain_entity: CurrencyFactor) -> CurrencyFactorModel:
        """Convert CurrencyFactor domain entity to ORM model."""
        return CurrencyFactorModel(
            id=domain_entity.id,
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )