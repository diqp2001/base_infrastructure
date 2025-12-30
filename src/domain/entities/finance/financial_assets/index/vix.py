from datetime import date
from typing import Optional
from domain.entities.finance.financial_assets.index.index import Index


class Vix(Index):
    def __init__(self,
                 id: int,
                 start_date: date,
                 end_date: Optional[date]):
        
        super().__init__(id, start_date, end_date)