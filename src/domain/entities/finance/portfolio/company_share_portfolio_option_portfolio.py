from __future__ import annotations

from datetime import date
from typing import Optional

from .portfolio import Portfolio


class CompanySharePortfolioOptionPortfolio(Portfolio):
    """
    Portfolio composed of options on a portfolio of company shares.
    """

    def __init__(
        self,
        id: int,
        name: str,
        start_date: date,
        end_date: Optional[date] = None,
    ):
        super().__init__(
            id=id,
            name=name,
            start_date=start_date,
            end_date=end_date,
        )