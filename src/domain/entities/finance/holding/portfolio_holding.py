
from __future__ import annotations
from datetime import datetime
from typing import Optional
from decimal import Decimal

from domain.entities.finance.holding.holding import Holding
from domain.entities.finance.financial_assets.financial_asset import FinancialAsset


class PortfolioHolding(Holding):
    """
    Base class for holdings inside a portfolio.
    Extends the basic Holding with portfolio-specific attributes.
    """
    
    def __init__(
        self,
        id: int,
        portfolio_id: int,
        asset_id: int,
        quantity: Decimal,
        average_cost: Optional[Decimal] = None,
        current_price: Optional[Decimal] = None,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        asset: Optional[FinancialAsset] = None
    ):
        super().__init__(
            id=id,
            asset=asset,
            container_id=portfolio_id,
            start_date=start_date,
            end_date=end_date
        )
        
        self.portfolio_id = portfolio_id
        self.asset_id = asset_id
        self.quantity = quantity
        self.average_cost = average_cost
        self.current_price = current_price
    
    @property
    def market_value(self) -> Optional[Decimal]:
        """Calculate current market value."""
        if self.current_price and self.quantity:
            return self.current_price * self.quantity
        return None
    
    @property
    def unrealized_pnl(self) -> Optional[Decimal]:
        """Calculate unrealized profit/loss."""
        if self.average_cost and self.current_price and self.quantity:
            return (self.current_price - self.average_cost) * self.quantity
        return None
