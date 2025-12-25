from datetime import date
from typing import Optional
from src.domain.entities.finance.financial_assets.security import Security


class Equity(Security):
    def __init__(self,
                 id: int,
                 start_date: date,
                 end_date: Optional[date]):
        
        super().__init__(id, start_date, end_date)