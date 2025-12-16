from __future__ import annotations

from datetime import date
from typing import List, Optional

from domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from .portfolio import Portfolio


class PortfolioCompanyShare(Portfolio):
    """
    Portfolio composed exclusively of company shares (equities).

    Identification-only entity.
    Position sizing, allocation, and analytics are handled elsewhere.
    """

    def __init__(
        self,
        id: int,
        name: str,
        underlying_assets: List[CompanyShare],
        start_date: date,
        end_date: Optional[date] = None,
    ):
        super().__init__(
            id=id,
            name=name,
            underlying_assets=underlying_assets,
            start_date=start_date,
            end_date=end_date,
        )
