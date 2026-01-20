"""
Mapper for Derivative domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.finance.financial_assets.derivatives.derivative import Derivative as DomainDerivative
from src.infrastructure.models.finance.financial_assets.derivative.derivatives import DerivativeModel as ORMDerivative


class DerivativeMapper:
    """Mapper for Derivative domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMDerivative) -> DomainDerivative:
        """Convert ORM model to domain entity."""
        return DomainDerivative(
            id=orm_obj.id,
            name=orm_obj.name,
            symbol=orm_obj.symbol,
            underlying_asset_id=orm_obj.underlying_asset_id,
            start_date=orm_obj.start_date,
            end_date=orm_obj.end_date
        )

    @staticmethod
    def to_orm(domain_obj: DomainDerivative, orm_obj: Optional[ORMDerivative] = None) -> ORMDerivative:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMDerivative(
                asset_type='derivative',  # Set polymorphic identity
                name=domain_obj.name,
                symbol=domain_obj.symbol,
                underlying_asset_id=domain_obj.underlying_asset_id,
                currency_id=getattr(domain_obj, 'currency_id', 1)  # Default currency if not specified
            )
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.name = domain_obj.name
        orm_obj.symbol = domain_obj.symbol
        orm_obj.underlying_asset_id = domain_obj.underlying_asset_id
        orm_obj.start_date = domain_obj.start_date
        orm_obj.end_date = domain_obj.end_date
        
        # Set polymorphic identity
        orm_obj.asset_type = 'derivative'
        
        # Map optional attributes if they exist
        if hasattr(domain_obj, 'currency_id'):
            orm_obj.currency_id = domain_obj.currency_id
        
        return orm_obj