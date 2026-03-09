from datetime import date
from typing import Optional

from domain.entities.finance.financial_assets.share.share import Share


class CompanyShare(Share):

    def __init__(
        self,
        id: Optional[int],
        symbol: str,
        currency_id:int,
        company_id: int,
        exchange_id: int,
        name: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ):
        super().__init__(
            id = id,  name=name, symbol=symbol, start_date=start_date, end_date=end_date
        )

        self.company_id = company_id
        self.exchange_id = exchange_id
        self.currency_id = currency_id

  