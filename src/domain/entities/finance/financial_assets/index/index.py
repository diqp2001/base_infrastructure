from datetime import date
from typing import Optional
from decimal import Decimal
from src.domain.entities.finance.financial_assets.security import Security


class Index(Security):
    def __init__(self,
                 id: Optional[int] = None,
                 symbol: str = "",
                 name: str = "",
                 currency: str = "USD",
                 base_value: Optional[Decimal] = None,
                 base_date: Optional[date] = None,
                 description: Optional[str] = None,
                 index_type: str = "EQUITY",
                 weighting_method: str = "MARKET_CAP",
                 calculation_method: str = "CAPITALIZATION_WEIGHTED",
                 ibkr_contract_id: Optional[int] = None,
                 ibkr_local_symbol: str = "",
                 ibkr_exchange: str = "",
                 ibkr_min_tick: Optional[Decimal] = None,
                 start_date: Optional[date] = None,
                 end_date: Optional[date] = None):
        
        super().__init__(id or 0, start_date or date.today(), end_date)
        
        # Core index properties
        self.symbol = symbol
        self.name = name
        self.currency = currency
        self.description = description
        self.index_type = index_type
        
        # Index calculation properties
        self.base_value = base_value
        self.base_date = base_date
        self.weighting_method = weighting_method
        self.calculation_method = calculation_method
        
        # IBKR-specific properties
        self.ibkr_contract_id = ibkr_contract_id
        self.ibkr_local_symbol = ibkr_local_symbol
        self.ibkr_exchange = ibkr_exchange
        self.ibkr_min_tick = ibkr_min_tick
        
        # Optional derived values
        self._level = None
        self._last_update = None