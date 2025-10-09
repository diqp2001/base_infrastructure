"""
Mapper for converting between FinancialAssetFactorValue domain entities and ORM models.
"""

from typing import Optional
from decimal import Decimal
from domain.entities.factor.finance.financial_assets.financial_asset_factor_value import FinancialAssetFactorValue as FinancialAssetFactorValueEntity
from infrastructure.models.factor.factor_model import FactorValue as FactorValueModel


class FinancialAssetFactorValueMapper:
    """Mapper for FinancialAssetFactorValue domain entity and ORM model conversion."""

    @staticmethod
    def to_domain(orm_model: Optional[FactorValueModel]) -> Optional[FinancialAssetFactorValueEntity]:
        """Convert ORM model to domain entity."""
        if not orm_model:
            return None
        
        return FinancialAssetFactorValueEntity(
            id=orm_model.id,
            factor_id=orm_model.factor_id,
            entity_id=orm_model.entity_id,
            date=orm_model.date,
            value=Decimal(str(orm_model.value)) if orm_model.value is not None else Decimal('0'),
            # FinancialAssetFactorValue specific fields - would typically come from other sources
            asset_class=None,     # Could be determined from the entity type or factor metadata
            market_value=None,    # Could be the same as value for price factors
            currency=None,        # Default assumption, could be determined from entity
            is_adjusted=False     # Default assumption
        )

    @staticmethod
    def to_orm(domain_entity: FinancialAssetFactorValueEntity) -> FactorValueModel:
        """Convert domain entity to ORM model."""
        return FactorValueModel(
            id=domain_entity.id,
            factor_id=domain_entity.factor_id,
            entity_id=domain_entity.entity_id,
            date=domain_entity.date,
            value=domain_entity.value
        )