"""
Mapper for Equity domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.finance.financial_assets.equity import Equity as DomainEquity
from src.infrastructure.models.finance.financial_assets.equity import EquityModel as ORMEquity


class EquityMapper:
    """Mapper for Equity domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMEquity) -> DomainEquity:
        """Convert ORM model to domain entity."""
        return DomainEquity(
            id=orm_obj.id,
            name=orm_obj.name,
            symbol=orm_obj.symbol,
            start_date=orm_obj.start_date,
            end_date=orm_obj.end_date
        )

    @staticmethod
    def to_orm(domain_obj: DomainEquity, orm_obj: Optional[ORMEquity] = None) -> ORMEquity:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMEquity(
                asset_type='equity',  # Set polymorphic identity
                name=domain_obj.name,
                symbol=domain_obj.symbol
            )
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.name = domain_obj.name
        orm_obj.symbol = domain_obj.symbol
        orm_obj.start_date = domain_obj.start_date
        orm_obj.end_date = domain_obj.end_date
        
        # Set polymorphic identity
        orm_obj.asset_type = 'equity'
        
        return orm_obj