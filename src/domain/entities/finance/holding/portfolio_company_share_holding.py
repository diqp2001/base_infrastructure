from __future__ import annotations
from datetime import datetime
from typing import Optional

from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.domain.entities.finance.holding.portfolio_holding import PortfolioHolding
from src.domain.entities.finance.portfolio.portfolio_company_share import PortfolioCompanyShare



class PortfolioCompanyShareHolding(PortfolioHolding):
    """
    CompanyShare held inside a PortfolioCompanyShare.
    """

    def __init__(
        self,
        id: int,
        asset: CompanyShare,
        portfolio: PortfolioCompanyShare,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ):
        super().__init__(
            id=id,
            asset=asset,
            container=portfolio,
            start_date=start_date,
            end_date=end_date,
        )

