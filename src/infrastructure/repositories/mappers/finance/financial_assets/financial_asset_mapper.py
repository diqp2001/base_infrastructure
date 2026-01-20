"""
Mapper for FinancialAsset domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset as DomainFinancialAsset
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel as ORMFinancialAsset


class FinancialAssetMapper:
    """Mapper for FinancialAsset domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMFinancialAsset) -> DomainFinancialAsset:
        """Convert ORM model to domain entity."""
        # Note: This returns the base FinancialAsset, but in practice you'd want
        # to use polymorphic mapping to return the correct subclass
        return DomainFinancialAsset(
            id=orm_obj.id,
            name=orm_obj.name,
            symbol=orm_obj.symbol,
            start_date=orm_obj.start_date,
            end_date=orm_obj.end_date
        )

    @staticmethod
    def to_orm(domain_obj: DomainFinancialAsset, orm_obj: Optional[ORMFinancialAsset] = None) -> ORMFinancialAsset:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMFinancialAsset(
                asset_type=domain_obj.asset_type,  # Use the domain entity's asset_type
                name=domain_obj.name,
                symbol=domain_obj.symbol,
                description=getattr(domain_obj, 'description', None)
            )
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.name = domain_obj.name
        orm_obj.symbol = domain_obj.symbol
        orm_obj.start_date = domain_obj.start_date
        orm_obj.end_date = domain_obj.end_date
        
        # Map optional attributes if they exist
        if hasattr(domain_obj, 'description'):
            orm_obj.description = domain_obj.description
        if hasattr(domain_obj, 'asset_type'):
            orm_obj.asset_type = domain_obj.asset_type
            
        return orm_obj