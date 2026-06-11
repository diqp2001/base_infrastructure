from __future__ import annotations

from datetime import datetime
from typing import Optional

from src.domain.entities.finance.holding.portfolio_holding import PortfolioHolding
from src.domain.entities.finance.holding.position import Position
from src.domain.entities.finance.portfolio.currency_portfolio import CurrencyPortfolio
from src.domain.entities.finance.portfolio.portfolio import Portfolio


class CurrencyPortfolioPortfolioHolding(PortfolioHolding):
    """
    A holding that represents a CurrencyPortfolio (asset) held within a Portfolio (container).

    Mirrors CompanySharePortfolioPortfolioHolding — enables a main portfolio to hold
    a CurrencyPortfolio as a sub-portfolio node in the 3-layer hierarchy:

        Portfolio (main)
          └─ CurrencyPortfolioPortfolioHolding
               └─ asset = CurrencyPortfolio (sub-portfolio)
                    └─ CurrencyPortfolioHolding → USD position
    """

    def __init__(
        self,
        id: int,
        portfolio: Portfolio,
        currency_portfolio: CurrencyPortfolio,
        position: Position,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ):
        super().__init__(
            id=id,
            portfolio=portfolio,
            asset=currency_portfolio,
            position=position,
            start_date=start_date,
            end_date=end_date,
        )
        self.currency_portfolio = currency_portfolio
