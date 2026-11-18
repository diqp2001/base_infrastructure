from __future__ import annotations

from datetime import datetime
from typing import Optional

from src.domain.entities.finance.holding.portfolio_holding import PortfolioHolding
from src.domain.entities.finance.holding.position import Position
from src.domain.entities.finance.portfolio.etf_share_option_portfolio import ETFShareOptionPortfolio
from src.domain.entities.finance.portfolio.portfolio import Portfolio


class ETFShareOptionPortfolioPortfolioHolding(PortfolioHolding):
    """
    A holding that represents a ETFShareOptionPortfolio (asset) held within a
    Portfolio (container), linking the option sub-portfolio into the main portfolio tree.
    """

    def __init__(
        self,
        id: int,
        portfolio: Portfolio,
        etf_share_option_portfolio: ETFShareOptionPortfolio,
        position: Position,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ):
        super().__init__(
            id=id,
            portfolio=portfolio,
            asset=etf_share_option_portfolio,
            position=position,
            start_date=start_date,
            end_date=end_date,
        )
        self.etf_share_option_portfolio = etf_share_option_portfolio
