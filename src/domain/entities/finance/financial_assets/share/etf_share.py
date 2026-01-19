from datetime import date
from typing import Optional
from .share import Share


class ETFShare(Share):
    def __init__(
    self,
    id: Optional[int],
    name: Optional[str],
    symbol: Optional[str],
    exchange_id :int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
        
        super().__init__(id, name, symbol, start_date, end_date)
    
        self.exchange_id = exchange_id