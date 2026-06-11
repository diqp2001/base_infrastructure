from __future__ import annotations

from datetime import datetime
from typing import Optional

from src.domain.entities.finance.financial_assets.currency import Currency
from src.domain.entities.finance.holding.portfolio_holding import PortfolioHolding
from src.domain.entities.finance.holding.position import Position
from src.domain.entities.finance.portfolio.currency_portfolio import CurrencyPortfolio


class CurrencyPortfolioHolding(PortfolioHolding):
    """
    Currency held inside a CurrencyPortfolio.

    Mirrors CompanySharePortfolioHolding:
      asset     = Currency          (the currency being held)
      container = CurrencyPortfolio (the sub-portfolio that groups currency positions)
    """

    def __init__(
        self,
        id: int,
        asset: Currency,
        portfolio: CurrencyPortfolio,
        position: Position,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ):
        super().__init__(
            id=id,
            asset=asset,
            container=portfolio,
            position=position,
            start_date=start_date,
            end_date=end_date,
        )
