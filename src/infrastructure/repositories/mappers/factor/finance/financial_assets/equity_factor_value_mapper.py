"""
Mapper for converting between EquityFactorValue domain entities and ORM models.
"""

from typing import Optional
from decimal import Decimal
from domain.entities.factor.finance.financial_assets.equity_factor_value import EquityFactorValue as EquityFactorValueEntity
from infrastructure.models.factor.finance.financial_assets.equity_factors import EquityFactorValue as EquityFactorValueModel


class EquityFactorValueMapper:
    """Mapper for EquityFactorValue domain entity and ORM model conversion."""

    @staticmethod
    def to_domain(orm_model: Optional[EquityFactorValueModel]) -> Optional[EquityFactorValueEntity]:
        """Convert ORM model to domain entity."""
        if not orm_model:
            return None
        
        return EquityFactorValueEntity(
            id=orm_model.id,
            factor_id=orm_model.factor_id,
            entity_id=orm_model.entity_id,
            date=orm_model.date,
            value=Decimal(str(orm_model.value)) if orm_model.value is not None else Decimal('0'),
            # Inherit from SecurityFactorValue
            asset_class="equity",
            market_value=None,    # Could be the same as value for price factors
            currency="USD",       # Default assumption, could be determined from entity
            is_adjusted=False,    # Default assumption
            security_type="equity",
            ticker_symbol=None,   # Would come from the equity entity
            exchange=None,        # Would come from the equity entity
            volume=None,          # Would come from other factors or sources
            # EquityFactorValue specific fields - would typically come from other sources
            equity_type="common", # Default assumption
            dividend_yield=None,  # Would come from other factors or sources
            pe_ratio=None,        # Would come from other factors or sources
            market_cap=None,      # Would be calculated from price * shares_outstanding
            beta=None             # Would come from other factors or sources
        )

    @staticmethod
    def to_orm(domain_entity: EquityFactorValueEntity) -> EquityFactorValueModel:
        """Convert domain entity to ORM model."""
        return EquityFactorValueModel(
            id=domain_entity.id,
            factor_id=domain_entity.factor_id,
            entity_id=domain_entity.entity_id,
            date=domain_entity.date,
            value=domain_entity.value
        )