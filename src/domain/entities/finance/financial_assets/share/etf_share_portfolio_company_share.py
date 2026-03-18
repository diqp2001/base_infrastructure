from datetime import date
from typing import Optional
from .share import Share


class ETFSharePortfolioCompanyShare(Share):
    def __init__(
    self,
    id: Optional[int],
    name: Optional[str],
    symbol: Optional[str],
    exchange_id :int,
    currency_id: Optional[int] = None,
    underlying_asset_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
        
        super().__init__(id = id,  name=name, symbol=symbol, start_date=start_date, end_date=end_date)
    
        self.exchange_id = exchange_id
        self.currency_id =currency_id
        self.underlying_asset_id = underlying_asset_id