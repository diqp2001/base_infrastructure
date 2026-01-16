from datetime import date
from typing import Optional
from decimal import Decimal
from src.domain.entities.finance.financial_assets.security import Security


class Index(Security):
    def __init__(self,
                 id: Optional[int] = None,
                 symbol: str = "",
                 name: str = "",
                 description: Optional[str] = None,
                 start_date: Optional[date] = None,
                 end_date: Optional[date] = None,
                 is_tradeable : Optional[bool] = None,
                 is_active : Optional[bool] = None,):
        
        super().__init__(id or 0, start_date or date.today(), end_date)
        
        # Core index properties
        self.symbol = symbol
        self.name = name
        self.description = description
        self.is_tradeable = is_tradeable
        self.is_active = is_active