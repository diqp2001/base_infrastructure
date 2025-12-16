from __future__ import annotations
from datetime import datetime
from typing import Optional
from decimal import Decimal

from domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from domain.entities.finance.holding.portfolio_holding import PortfolioHolding
from domain.entities.finance.portfolio.portfolio_company_share import PortfolioCompanyShare


class PortfolioCompanyShareHolding(PortfolioHolding):
    """
    CompanyShare held inside a PortfolioCompanyShare.
    Specialized holding for company shares with additional trading information.
    """

    def __init__(
        self,
        id: int,
        portfolio_id: int,
        company_share_id: int,
        symbol: str,
        quantity: Decimal,
        average_cost: Optional[Decimal] = None,
        current_price: Optional[Decimal] = None,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        asset: Optional[CompanyShare] = None,
        portfolio: Optional[PortfolioCompanyShare] = None
    ):
        super().__init__(
            id=id,
            portfolio_id=portfolio_id,
            asset_id=company_share_id,
            quantity=quantity,
            average_cost=average_cost,
            current_price=current_price,
            start_date=start_date,
            end_date=end_date,
            asset=asset
        )

        self.company_share_id = company_share_id
        self.symbol = symbol
        self.portfolio = portfolio
    
    @property
    def company_share(self) -> Optional[CompanyShare]:
        """Get the company share asset."""
        return self.asset if isinstance(self.asset, CompanyShare) else None
