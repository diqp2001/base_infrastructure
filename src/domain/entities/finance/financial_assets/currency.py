from datetime import date
from typing import Optional
from src.domain.entities.finance.financial_assets.security import Security


class Currency(Security):
    def __init__(
            self,
            id: Optional[int],
            name: Optional[str],
            symbol: Optional[str],
            country_id: Optional[int] = None,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
        ):

        super().__init__(id, name, symbol, start_date, end_date)
        self.country_id = country_id
