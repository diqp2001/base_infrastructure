"""
Mapper for converting between ShareFactorValue domain entities and ORM models.
"""

from typing import Optional
from decimal import Decimal
from domain.entities.factor.finance.financial_assets.share_factor.share_factor_value import ShareFactorValue as ShareFactorValueEntity
from infrastructure.models.factor.finance.financial_assets.share_factors import ShareFactorValue as ShareFactorValueModel


class ShareFactorValueMapper:
    """Mapper for ShareFactorValue domain entity and ORM model conversion."""

    @staticmethod
    def to_domain(orm_model: Optional[ShareFactorValueModel]) -> Optional[ShareFactorValueEntity]:
        """Convert ORM model to domain entity."""
        if not orm_model:
            return None
        
        return ShareFactorValueEntity(
            id=orm_model.id,
            factor_id=orm_model.factor_id,
            entity_id=orm_model.entity_id,
            date=orm_model.date,
            value=Decimal(str(orm_model.value)) if orm_model.value is not None else Decimal('0'),
            # Inherit from EquityFactorValue - these would typically come from other sources or tables
            asset_class="equity",
            market_value=None,    # Could be the same as value for price factors
            currency="USD",       # Default assumption, could be determined from entity
            is_adjusted=False,    # Default assumption
            security_type="stock",
            ticker_symbol=None,   # Would come from the share entity
            exchange=None,        # Would come from the share entity
            volume=None,          # Would come from other factors or sources
            equity_type="common", # Default assumption
            dividend_yield=None,  # Would come from other factors or sources
            pe_ratio=None,        # Would come from other factors or sources
            market_cap=None,      # Would be calculated from price * shares_outstanding
            beta=None,            # Would come from other factors or sources
            # ShareFactorValue specific fields - would typically come from other sources
            share_class=None,
            shares_outstanding=None,
            float_shares=None,
            voting_rights_per_share=1,  # Default assumption for common shares
            par_value=None
        )

    @staticmethod
    def to_orm(domain_entity: ShareFactorValueEntity) -> ShareFactorValueModel:
        """Convert domain entity to ORM model."""
        return ShareFactorValueModel(
            id=domain_entity.id,
            factor_id=domain_entity.factor_id,
            entity_id=domain_entity.entity_id,
            date=domain_entity.date,
            value=domain_entity.value
        )