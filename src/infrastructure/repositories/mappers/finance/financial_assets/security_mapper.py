"""
Mapper for Security domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.finance.financial_assets.security import Security as DomainSecurity
from src.infrastructure.models.finance.financial_assets.security import SecurityModel as ORMSecurity


class SecurityMapper:
    """Mapper for Security domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMSecurity) -> DomainSecurity:
        """Convert ORM model to domain entity."""
        return DomainSecurity(
            id=orm_obj.id,
            name=orm_obj.name,
            symbol=orm_obj.symbol,
            start_date=orm_obj.start_date,
            end_date=orm_obj.end_date,
            portfolio_id=orm_obj.portfolio_id
        )

    @staticmethod
    def to_orm(domain_obj: DomainSecurity, orm_obj: Optional[ORMSecurity] = None) -> ORMSecurity:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMSecurity(
                asset_type='security',  # Set polymorphic identity
                name=domain_obj.name,
                symbol=domain_obj.symbol,
                portfolio_id=domain_obj.portfolio_id
            )
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.name = domain_obj.name
        orm_obj.symbol = domain_obj.symbol
        orm_obj.start_date = domain_obj.start_date
        orm_obj.end_date = domain_obj.end_date
        orm_obj.portfolio_id = domain_obj.portfolio_id
        
        # Set polymorphic identity
        orm_obj.asset_type = 'security'
        
        return orm_obj