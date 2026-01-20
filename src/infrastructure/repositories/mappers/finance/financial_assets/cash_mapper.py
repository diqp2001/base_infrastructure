"""
Mapper for Cash domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.finance.financial_assets.cash import Cash as DomainCash
from src.infrastructure.models.finance.financial_assets.cash import CashModel as ORMCash


class CashMapper:
    """Mapper for Cash domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMCash) -> DomainCash:
        """Convert ORM model to domain entity."""
        domain_entity = DomainCash(
            id=orm_obj.id,
            currency_id=orm_obj.currency_id,
            name=getattr(orm_obj, 'name', f"Cash_{orm_obj.currency_id}"),
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
    def to_orm(domain_obj: DomainCash, orm_obj: Optional[ORMCash] = None) -> ORMCash:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMCash()
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.currency_id = domain_obj.currency_id
        
        # Map optional financial asset attributes
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