from datetime import date
from typing import Optional

from domain.entities.finance.company import Company
from domain.entities.finance.exchange import Exchange
from ..share import Share


class CompanyShare(Share):
    def __init__(self,id: int,exchange :Exchange,company : Company,start_date: date,end_date: Optional[date]):
        
        super().__init__(id,exchange, start_date, end_date)
        self.company = company


