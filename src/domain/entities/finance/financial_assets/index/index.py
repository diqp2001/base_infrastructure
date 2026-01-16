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
                 index_type: str = "EQUITY",
                 base_value: Optional[Decimal] = None,
                 base_date: Optional[date] = None,
                 currency: str = "USD",
                 weighting_method: Optional[str] = None,
                 calculation_method: Optional[str] = None,
                 # IBKR-specific fields
                 ibkr_contract_id: Optional[int] = None,
                 ibkr_local_symbol: str = "",
                 ibkr_exchange: Optional[str] = None,
                 ibkr_min_tick: Optional[Decimal] = None,
                 ibkr_market_name: Optional[str] = None,
                 ibkr_valid_exchanges: Optional[str] = None,
                 ibkr_trading_hours: Optional[str] = None,
                 ibkr_liquid_hours: Optional[str] = None,
                 ibkr_time_zone: Optional[str] = None,
                 # Legacy parameters for backwards compatibility
                 start_date: Optional[date] = None,
                 end_date: Optional[date] = None):
        
        super().__init__(id or 0, start_date or date.today(), end_date)
        
        # Index-specific attributes
        self.symbol = symbol
        self.name = name
        self.description = description
        self.index_type = index_type
        self.base_value = base_value
        self.base_date = base_date
        self.currency = currency
        self.weighting_method = weighting_method
        self.calculation_method = calculation_method
        
        # IBKR-specific attributes
        self.ibkr_contract_id = ibkr_contract_id
        self.ibkr_local_symbol = ibkr_local_symbol
        self.ibkr_exchange = ibkr_exchange
        self.ibkr_min_tick = ibkr_min_tick
        self.ibkr_market_name = ibkr_market_name
        self.ibkr_valid_exchanges = ibkr_valid_exchanges
        self.ibkr_trading_hours = ibkr_trading_hours
        self.ibkr_liquid_hours = ibkr_liquid_hours
        self.ibkr_time_zone = ibkr_time_zone
    
    @property
    def asset_type(self):
        return "Index"
    
    def __repr__(self):
        return f"<Index(id={self.id}, symbol={self.symbol}, name={self.name})>"