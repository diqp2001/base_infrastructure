"""
Mapper for Position domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime, date
from decimal import Decimal

# Since the domain entity appears to be empty/minimal, we'll create a basic mapper
from src.infrastructure.models.finance.position import Position as ORMPosition


class PositionMapper:
    """Mapper for Position domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMPosition):
        """Convert ORM model to domain entity."""
        # Since the domain entity is minimal, we'll create a simple object
        # with the essential properties
        class MinimalPosition:
            def __init__(self, id, portfolio_id, asset_id, quantity, average_cost):
                self.id = id
                self.portfolio_id = portfolio_id
                self.asset_id = asset_id
                self.quantity = quantity
                self.average_cost = average_cost
                self.current_price = 0
                self.market_value = 0
                self.unrealized_pnl = 0
        
        domain_entity = MinimalPosition(
            id=orm_obj.id,
            portfolio_id=orm_obj.portfolio_id,
            asset_id=orm_obj.asset_id,
            quantity=float(orm_obj.quantity),
            average_cost=float(orm_obj.average_cost)
        )
        
        if orm_obj.current_price:
            domain_entity.current_price = float(orm_obj.current_price)
        
        if orm_obj.market_value:
            domain_entity.market_value = float(orm_obj.market_value)
        
        if orm_obj.unrealized_pnl:
            domain_entity.unrealized_pnl = float(orm_obj.unrealized_pnl)
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj, orm_obj: Optional[ORMPosition] = None) -> ORMPosition:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMPosition()
        
        # Map basic fields
        if hasattr(domain_obj, 'id'):
            orm_obj.id = domain_obj.id
        if hasattr(domain_obj, 'portfolio_id'):
            orm_obj.portfolio_id = domain_obj.portfolio_id
        if hasattr(domain_obj, 'asset_id'):
            orm_obj.asset_id = domain_obj.asset_id
        if hasattr(domain_obj, 'quantity'):
            orm_obj.quantity = Decimal(str(domain_obj.quantity))
        if hasattr(domain_obj, 'average_cost'):
            orm_obj.average_cost = Decimal(str(domain_obj.average_cost))
        if hasattr(domain_obj, 'current_price'):
            orm_obj.current_price = Decimal(str(domain_obj.current_price))
        
        # Set asset type if available
        if hasattr(domain_obj, 'asset_type'):
            orm_obj.asset_type = domain_obj.asset_type
        else:
            orm_obj.asset_type = 'UNKNOWN'
        
        # Calculate derived values
        if orm_obj.quantity and orm_obj.average_cost:
            orm_obj.cost_basis = orm_obj.quantity * orm_obj.average_cost
        
        if orm_obj.quantity and orm_obj.current_price:
            orm_obj.market_value = orm_obj.quantity * orm_obj.current_price
        
        if orm_obj.market_value and orm_obj.cost_basis:
            orm_obj.unrealized_pnl = orm_obj.market_value - orm_obj.cost_basis
        
        if orm_obj.cost_basis and orm_obj.cost_basis != 0:
            orm_obj.unrealized_pnl_percent = (orm_obj.unrealized_pnl / orm_obj.cost_basis) * Decimal('100')
        
        # Set defaults
        if not orm_obj.position_type:
            orm_obj.position_type = 'LONG'
        
        if not orm_obj.currency:
            orm_obj.currency = 'USD'
        
        if orm_obj.leverage is None:
            orm_obj.leverage = Decimal('1')
        
        if orm_obj.total_commissions is None:
            orm_obj.total_commissions = Decimal('0')
        
        if orm_obj.total_fees is None:
            orm_obj.total_fees = Decimal('0')
        
        if orm_obj.realized_pnl is None:
            orm_obj.realized_pnl = Decimal('0')
        
        # Calculate total P&L
        if orm_obj.unrealized_pnl is not None and orm_obj.realized_pnl is not None:
            orm_obj.total_pnl = orm_obj.unrealized_pnl + orm_obj.realized_pnl
        
        # Set timestamps
        if not orm_obj.created_at:
            orm_obj.created_at = datetime.now()
        orm_obj.updated_at = datetime.now()
        
        if not orm_obj.last_valuation_date:
            orm_obj.last_valuation_date = datetime.now()
        
        if not orm_obj.entry_date:
            orm_obj.entry_date = date.today()
        
        # Set status
        if orm_obj.is_active is None:
            orm_obj.is_active = True
        
        if orm_obj.is_closed is None:
            orm_obj.is_closed = False
        
        return orm_obj