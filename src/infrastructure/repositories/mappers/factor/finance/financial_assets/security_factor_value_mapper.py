"""
Mapper for converting between SecurityFactorValue domain entities and ORM models.
"""

from typing import Optional
from decimal import Decimal
from domain.entities.factor.finance.financial_assets.security_factor_value import SecurityFactorValue as SecurityFactorValueEntity
from infrastructure.models.factor.finance.financial_assets.security_factors import SecurityFactorValue as SecurityFactorValueModel


class SecurityFactorValueMapper:
    """Mapper for SecurityFactorValue domain entity and ORM model conversion."""

    @staticmethod
    def to_domain(orm_model: Optional[SecurityFactorValueModel]) -> Optional[SecurityFactorValueEntity]:
        """Convert ORM model to domain entity."""
        if not orm_model:
            return None
        
        return SecurityFactorValueEntity(
            id=orm_model.id,
            factor_id=orm_model.factor_id,
            entity_id=orm_model.entity_id,
            date=orm_model.date,
            value=Decimal(str(orm_model.value)) if orm_model.value is not None else Decimal('0'),
            # Inherit from FinancialAssetFactorValue
            asset_class="security",
            market_value=None,    # Could be the same as value for price factors
            currency="USD",       # Default assumption, could be determined from entity
            is_adjusted=False,    # Default assumption
            # SecurityFactorValue specific fields - would typically come from other sources
            security_type="security",  # Default
            ticker_symbol=None,        # Would come from the security entity
            exchange=None,             # Would come from the security entity
            volume=None                # Would come from other factors or sources
        )

    @staticmethod
    def to_orm(domain_entity: SecurityFactorValueEntity) -> SecurityFactorValueModel:
        """Convert domain entity to ORM model."""
        return SecurityFactorValueModel(
            id=domain_entity.id,
            factor_id=domain_entity.factor_id,
            entity_id=domain_entity.entity_id,
            date=domain_entity.date,
            value=domain_entity.value
        )