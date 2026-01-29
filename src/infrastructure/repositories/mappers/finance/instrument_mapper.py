"""
Mapper for Instrument domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.finance.instrument.instrument import Instrument as DomainInstrument
from src.infrastructure.models.finance.instrument import InstrumentModel as ORMInstrument
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset


class GenericFinancialAsset(FinancialAsset):
    """Simple concrete implementation of FinancialAsset for mapping purposes."""
    
    def __init__(self, id, name, symbol, start_date=None, end_date=None, asset_type="generic"):
        super().__init__(id, name, symbol, start_date, end_date)
        self._asset_type = asset_type
    
    @property
    def asset_type(self) -> str:
        return self._asset_type


class InstrumentMapper:
    """Mapper for Instrument domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMInstrument) -> DomainInstrument:
        """Convert ORM model to domain entity."""
        if not orm_obj:
            return None

        # Create a minimal FinancialAsset entity from the relationship
        # In a real implementation, you might want to use a FinancialAssetMapper
        financial_asset = None
        if orm_obj.asset:
            # Create a simple FinancialAsset entity with basic info
            financial_asset = GenericFinancialAsset(
                id=orm_obj.asset.id,
                name=getattr(orm_obj.asset, 'name', None),
                symbol=getattr(orm_obj.asset, 'symbol', None),
                start_date=getattr(orm_obj.asset, 'start_date', None),
                end_date=getattr(orm_obj.asset, 'end_date', None),
                asset_type=getattr(orm_obj.asset, 'asset_type', 'generic')
            )
        elif orm_obj.asset_id:
            # If no asset relationship loaded, create a placeholder
            financial_asset = GenericFinancialAsset(
                id=orm_obj.asset_id,
                name=f"Asset_{orm_obj.asset_id}",
                symbol=f"SYM_{orm_obj.asset_id}",
                start_date=None,
                end_date=None,
                asset_type='generic'
            )

        # Create domain entity
        domain_entity = DomainInstrument(
            id=orm_obj.id,
            asset=financial_asset,
            source=orm_obj.source,
            date=orm_obj.date
        )
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainInstrument, orm_obj: Optional[ORMInstrument] = None) -> ORMInstrument:
        """Convert domain entity to ORM model."""
        if not domain_obj:
            return None

        if orm_obj is None:
            # Create new ORM object
            orm_obj = ORMInstrument(
                asset_id=domain_obj.asset_id,
                source=domain_obj.source,
                date=domain_obj.date
            )
        
        # Map fields from domain to ORM
        if domain_obj.id is not None:
            orm_obj.id = domain_obj.id
            
        orm_obj.asset_id = domain_obj.asset_id
        orm_obj.source = domain_obj.source
        orm_obj.date = domain_obj.date
        
        # Handle timestamps - only set created_at if it's a new record
        if not hasattr(orm_obj, 'created_at') or orm_obj.created_at is None:
            orm_obj.created_at = datetime.utcnow()
        
        # Always update the updated_at timestamp
        orm_obj.updated_at = datetime.utcnow()
        
        return orm_obj

    @staticmethod
    def to_infrastructure(domain_obj: DomainInstrument) -> ORMInstrument:
        """Alias for to_orm for backward compatibility."""
        return InstrumentMapper.to_orm(domain_obj)

    @staticmethod
    def update_orm_from_domain(orm_obj: ORMInstrument, domain_obj: DomainInstrument) -> ORMInstrument:
        """Update an existing ORM object with data from a domain entity."""
        if not orm_obj or not domain_obj:
            return orm_obj
            
        # Update fields
        orm_obj.asset_id = domain_obj.asset_id
        orm_obj.source = domain_obj.source
        orm_obj.date = domain_obj.date
        orm_obj.updated_at = datetime.utcnow()
        
        return orm_obj