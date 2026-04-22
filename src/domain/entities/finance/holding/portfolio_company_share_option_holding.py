from __future__ import annotations
from datetime import datetime
from typing import Optional

from src.domain.entities.finance.holding.position import Position
from src.domain.entities.finance.financial_assets.derivatives.option.company_share_option import CompanyShareOption
from src.domain.entities.finance.holding.portfolio_holding import PortfolioHolding
from src.domain.entities.finance.portfolio.portfolio_company_share_option import PortfolioCompanyShareOption


class PortfolioCompanyShareOptionHolding(PortfolioHolding):
    """
    CompanyShareOption held inside a PortfolioCompanyShareOption.
    """

    def __init__(
        self,
        id: int,
        asset: CompanyShareOption,
        portfolio: PortfolioCompanyShareOption,
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