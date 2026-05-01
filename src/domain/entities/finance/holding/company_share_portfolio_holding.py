from __future__ import annotations
from datetime import datetime
from typing import Optional

from domain.entities.finance.holding.position import Position
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.domain.entities.finance.holding.portfolio_holding import PortfolioHolding
from domain.entities.finance.portfolio.company_share_portfolio import CompanySharePortfolio



class CompanySharePortfolioHolding(PortfolioHolding):
    """
    CompanyShare held inside a PortfolioCompanyShare.
    """

    def __init__(
        self,
        id: int,
        asset: CompanyShare,
        portfolio: CompanySharePortfolio,
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

