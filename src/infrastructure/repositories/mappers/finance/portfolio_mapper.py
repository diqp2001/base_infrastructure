"""
Mapper for Portfolio domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime, date
from decimal import Decimal
import json

# Since the domain entity appears to be empty/minimal, we'll create a basic mapper
# that can work with a minimal domain interface
from src.infrastructure.models.finance.portfolio import Portfolio as ORMPortfolio


class PortfolioMapper:
    """Mapper for Portfolio domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMPortfolio):
        """Convert ORM model to domain entity."""
        # Since the domain entity is minimal, we'll create a simple object
        # with the essential properties
        class MinimalPortfolio:
            def __init__(self, id, name, total_value=None):
                self.id = id
                self.name = name
                self.total_value = total_value or 0
                self.cash_balance = 0
                self.positions = []
        
        domain_entity = MinimalPortfolio(
            id=orm_obj.id,
            name=orm_obj.name,
            total_value=float(orm_obj.total_value) if orm_obj.total_value else 0
        )
        
        if orm_obj.cash_balance:
            domain_entity.cash_balance = float(orm_obj.cash_balance)
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj, orm_obj: Optional[ORMPortfolio] = None) -> ORMPortfolio:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMPortfolio()
        
        # Map basic fields
        if hasattr(domain_obj, 'id'):
            orm_obj.id = domain_obj.id
        if hasattr(domain_obj, 'name'):
            orm_obj.name = domain_obj.name
        if hasattr(domain_obj, 'total_value'):
            orm_obj.total_value = Decimal(str(domain_obj.total_value))
        if hasattr(domain_obj, 'cash_balance'):
            orm_obj.cash_balance = Decimal(str(domain_obj.cash_balance))
        
        # Set defaults for required fields
        if not orm_obj.portfolio_type:
            orm_obj.portfolio_type = 'STANDARD'
        
        if not orm_obj.currency:
            orm_obj.currency = 'USD'
        
        if not orm_obj.inception_date:
            orm_obj.inception_date = date.today()
        
        # Set default values
        if orm_obj.invested_amount is None:
            orm_obj.invested_amount = Decimal('0')
        
        if orm_obj.total_return is None:
            orm_obj.total_return = Decimal('0')
        
        if orm_obj.unrealized_pnl is None:
            orm_obj.unrealized_pnl = Decimal('0')
        
        if orm_obj.realized_pnl is None:
            orm_obj.realized_pnl = Decimal('0')
        
        if orm_obj.management_fee_rate is None:
            orm_obj.management_fee_rate = Decimal('0')
        
        if orm_obj.total_fees_paid is None:
            orm_obj.total_fees_paid = Decimal('0')
        
        # Set timestamps
        if not orm_obj.created_at:
            orm_obj.created_at = datetime.now()
        orm_obj.updated_at = datetime.now()
        
        if not orm_obj.last_valuation_date:
            orm_obj.last_valuation_date = datetime.now()
        
        # Set status
        if orm_obj.is_active is None:
            orm_obj.is_active = True
        
        return orm_obj