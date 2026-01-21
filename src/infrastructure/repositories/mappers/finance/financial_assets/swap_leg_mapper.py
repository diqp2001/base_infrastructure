"""
Mapper for SwapLeg domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.finance.financial_assets.derivatives.swap_leg import SwapLeg as DomainSwapLeg
from src.infrastructure.models.finance.financial_assets.derivative.swap.swap_leg import SwapLegModel as ORMSwapLeg


class SwapLegMapper:
    """Mapper for SwapLeg domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMSwapLeg) -> DomainSwapLeg:
        """Convert ORM model to domain entity."""
        domain_entity = DomainSwapLeg(
            id=orm_obj.id,
            swap_id=orm_obj.swap_id,
            currency_id=getattr(orm_obj, 'currency_id', None),
            underlying_asset_id=getattr(orm_obj, 'underlying_asset_id', None),
            ticker=getattr(orm_obj, 'ticker', None),
            name=getattr(orm_obj, 'name', None),
            symbol=getattr(orm_obj, 'symbol', None),
            isin=getattr(orm_obj, 'isin', None)
        )
        
        # Set additional properties if available
        if hasattr(orm_obj, 'current_price') and orm_obj.current_price:
            domain_entity.set_current_price(orm_obj.current_price)
        if hasattr(orm_obj, 'last_update') and orm_obj.last_update:
            domain_entity.set_last_update(orm_obj.last_update)
        if hasattr(orm_obj, 'is_tradeable') and orm_obj.is_tradeable is not None:
            domain_entity.set_is_tradeable(orm_obj.is_tradeable)
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainSwapLeg, orm_obj: Optional[ORMSwapLeg] = None) -> ORMSwapLeg:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMSwapLeg()
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.swap_id = domain_obj.swap_id
        
        # Map optional fields
        if hasattr(domain_obj, 'currency_id'):
            orm_obj.currency_id = domain_obj.currency_id
        if hasattr(domain_obj, 'underlying_asset_id'):
            orm_obj.underlying_asset_id = domain_obj.underlying_asset_id
        if hasattr(domain_obj, 'ticker'):
            orm_obj.ticker = domain_obj.ticker
        if hasattr(domain_obj, 'name'):
            orm_obj.name = domain_obj.name
        if hasattr(domain_obj, 'symbol'):
            orm_obj.symbol = domain_obj.symbol
        if hasattr(domain_obj, 'isin'):
            orm_obj.isin = domain_obj.isin
        if hasattr(domain_obj, 'current_price'):
            orm_obj.current_price = domain_obj.current_price
        if hasattr(domain_obj, 'last_update'):
            orm_obj.last_update = domain_obj.last_update
        if hasattr(domain_obj, 'is_tradeable'):
            orm_obj.is_tradeable = domain_obj.is_tradeable
        
        # Set timestamps if they exist on the model
        if hasattr(orm_obj, 'created_at') and not orm_obj.created_at:
            orm_obj.created_at = datetime.now()
        if hasattr(orm_obj, 'updated_at'):
            orm_obj.updated_at = datetime.now()
        
        return orm_obj