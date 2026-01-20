"""
Mapper for Share domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.finance.financial_assets.share.share import Share as DomainShare
from src.infrastructure.models.finance.financial_assets.share import ShareModel as ORMShare


class ShareMapper:
    """Mapper for Share domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMShare) -> DomainShare:
        """Convert ORM model to domain entity."""
        return DomainShare(
            id=orm_obj.id,
            name=orm_obj.name,
            symbol=orm_obj.symbol,
            exchange_id=orm_obj.exchange_id,
            start_date=orm_obj.start_date,
            end_date=orm_obj.end_date
        )

    @staticmethod
    def to_orm(domain_obj: DomainShare, orm_obj: Optional[ORMShare] = None) -> ORMShare:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMShare(
                asset_type='share',  # Set polymorphic identity
                name=domain_obj.name,
                symbol=domain_obj.symbol,
                exchange_id=domain_obj.exchange_id
            )
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.name = domain_obj.name
        orm_obj.symbol = domain_obj.symbol
        orm_obj.exchange_id = domain_obj.exchange_id
        orm_obj.start_date = domain_obj.start_date
        orm_obj.end_date = domain_obj.end_date
        
        # Set polymorphic identity
        orm_obj.asset_type = 'share'
        
        return orm_obj