from datetime import date
from typing import Optional
from domain.entities.finance.financial_assets.index.index import Index


class Vix(Index):
    def __init__(
            self,
            id: Optional[int],
            name: Optional[str],
            symbol: Optional[str],
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
        ):

        super().__init__(id, name, symbol, start_date, end_date)