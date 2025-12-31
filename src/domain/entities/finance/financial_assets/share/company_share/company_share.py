from datetime import date
from typing import Optional

from domain.entities.finance.company import Company
from domain.entities.finance.exchange import Exchange
from ..share import Share


class CompanyShare(Share):
    def __init__(self,id: int,exchange_id :int,company_id : int,start_date: date,end_date: Optional[date]):
        
        super().__init__(id,exchange_id, start_date, end_date)
        self.company_id = company_id


