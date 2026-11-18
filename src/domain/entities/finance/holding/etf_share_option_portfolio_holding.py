from __future__ import annotations
from datetime import datetime
from typing import Optional

from src.domain.entities.finance.holding.position import Position
from src.domain.entities.finance.financial_assets.derivatives.option.etf_share_option import ETFShareOption
from src.domain.entities.finance.holding.portfolio_holding import PortfolioHolding
from src.domain.entities.finance.portfolio.etf_share_option_portfolio import ETFShareOptionPortfolio


class ETFShareOptionPortfolioHolding(PortfolioHolding):
    """
    ETFShareOption held inside a ETFShareOptionPortfolio.
    """

    def __init__(
        self,
        id: int,
        asset: ETFShareOption,
        portfolio: ETFShareOptionPortfolio,
        position: Position,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ):
        super().__init__(
            id=id,
            asset=asset,
            portfolio=portfolio,
            position=position,
            start_date=start_date,
            end_date=end_date,
        )