"""
Mapper for Commodity domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime
from decimal import Decimal

from src.domain.entities.finance.financial_assets.commodity import Commodity as DomainCommodity
from src.infrastructure.models.finance.financial_assets.commodity import Commodity as ORMCommodity


class CommodityMapper:
    """Mapper for Commodity domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMCommodity) -> DomainCommodity:
        """Convert ORM model to domain entity."""
        # Create domain entity
        domain_entity = DomainCommodity(
            ticker=orm_obj.ticker,
            name=orm_obj.name,
            market=orm_obj.market,
            price=float(orm_obj.current_price) if orm_obj.current_price else 0.0
        )
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainCommodity, orm_obj: Optional[ORMCommodity] = None) -> ORMCommodity:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMCommodity()
        
        # Map basic fields
        orm_obj.ticker = domain_obj.ticker
        orm_obj.name = domain_obj.name
        orm_obj.market = domain_obj.market
        orm_obj.current_price = Decimal(str(domain_obj.price))
        
        # Set defaults for ORM-specific fields
        if not orm_obj.last_updated:
            orm_obj.last_updated = datetime.now()
        
        if orm_obj.currency is None:
            orm_obj.currency = 'USD'
        
        # Determine commodity type based on ticker/name patterns
        if not orm_obj.commodity_type:
            ticker_upper = domain_obj.ticker.upper()
            if any(energy in ticker_upper for energy in ['CL', 'NG', 'HO', 'RB']):
                orm_obj.commodity_type = 'Energy'
            elif any(metal in ticker_upper for metal in ['GC', 'SI', 'HG', 'PL', 'PA']):
                orm_obj.commodity_type = 'Metals'
            elif any(agri in ticker_upper for agri in ['C', 'W', 'S', 'CT', 'CC', 'KC', 'SB']):
                orm_obj.commodity_type = 'Agricultural'
            elif any(live in ticker_upper for live in ['LC', 'LH', 'FC']):
                orm_obj.commodity_type = 'Livestock'
            else:
                orm_obj.commodity_type = 'Other'
        
        # Set unit of measure based on commodity type
        if not orm_obj.unit_of_measure:
            if orm_obj.commodity_type == 'Energy':
                orm_obj.unit_of_measure = 'barrel' if 'CL' in ticker_upper else 'mmbtu'
            elif orm_obj.commodity_type == 'Metals':
                orm_obj.unit_of_measure = 'ounce'
            elif orm_obj.commodity_type == 'Agricultural':
                orm_obj.unit_of_measure = 'bushel'
            else:
                orm_obj.unit_of_measure = 'unit'
        
        # Set default contract size
        if orm_obj.contract_size is None:
            orm_obj.contract_size = Decimal('1000')
        
        # Set tick size
        if orm_obj.tick_size is None:
            orm_obj.tick_size = Decimal('0.01')
        
        # Set price per unit to current price if not set
        if orm_obj.price_per_unit is None:
            orm_obj.price_per_unit = orm_obj.current_price
        
        # Set status fields
        if orm_obj.is_tradeable is None:
            orm_obj.is_tradeable = True
        
        if orm_obj.is_active is None:
            orm_obj.is_active = True
        
        return orm_obj