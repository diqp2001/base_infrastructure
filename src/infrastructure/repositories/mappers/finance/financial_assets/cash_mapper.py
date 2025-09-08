"""
Mapper for Cash domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime
from decimal import Decimal

from src.domain.entities.finance.financial_assets.cash import Cash as DomainCash
from src.infrastructure.models.finance.financial_assets.cash import Cash as ORMCash


class CashMapper:
    """Mapper for Cash domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMCash) -> DomainCash:
        """Convert ORM model to domain entity."""
        # Create domain entity
        domain_entity = DomainCash(
            asset_id=orm_obj.asset_id,
            name=orm_obj.name,
            amount=float(orm_obj.amount),
            currency=orm_obj.currency
        )
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainCash, orm_obj: Optional[ORMCash] = None) -> ORMCash:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMCash()
        
        # Map basic fields
        orm_obj.asset_id = domain_obj.asset_id
        orm_obj.name = domain_obj.name
        orm_obj.amount = Decimal(str(domain_obj.amount))
        orm_obj.currency = domain_obj.currency
        
        # Set defaults for ORM-specific fields
        if not orm_obj.last_updated:
            orm_obj.last_updated = datetime.now()
        
        if orm_obj.account_type is None:
            orm_obj.account_type = 'checking'
        
        if orm_obj.interest_rate is None:
            orm_obj.interest_rate = Decimal('0.0')
        
        if orm_obj.maintenance_fee is None:
            orm_obj.maintenance_fee = Decimal('0.0')
        
        # Set availability status
        if orm_obj.is_available is None:
            orm_obj.is_available = True
        
        if orm_obj.is_locked is None:
            orm_obj.is_locked = False
        
        return orm_obj