from __future__ import annotations

from datetime import datetime
from typing import Optional

from src.domain.entities.finance.holding.portfolio_holding import PortfolioHolding
from src.domain.entities.finance.holding.position import Position
from src.domain.entities.finance.portfolio.company_share_portfolio import CompanySharePortfolio
from src.domain.entities.finance.portfolio.portfolio import Portfolio


class CompanySharePortfolioPortfolioHolding(PortfolioHolding):
    """
    A holding that represents a CompanySharePortfolio (asset) held within a Portfolio (container).
    
    This allows portfolios to contain other portfolios as positions, creating a hierarchical 
    portfolio structure where a main portfolio can hold sub-portfolios of company shares.
    """

    def __init__(
        self,
        id: int,
        portfolio: Portfolio,
        company_share_portfolio: CompanySharePortfolio,
        position: Position,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ):
        super().__init__(
            id=id,
            portfolio=portfolio,
            asset=company_share_portfolio,
            position=position,
            start_date=start_date,
            end_date=end_date,
        )
        self.company_share_portfolio = company_share_portfolio