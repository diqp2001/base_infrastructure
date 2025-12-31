from datetime import date
from typing import Optional
from domain.entities.finance.exchange import Exchange
from src.domain.entities.finance.financial_assets.security import Security


class Share(Security):
    def __init__(self,
                 id: int,
                 exchange :Exchange,
                 start_date: date,
                 end_date: Optional[date]):
        
        super().__init__(id, start_date, end_date)
        self.exchange = exchange