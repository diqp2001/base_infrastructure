from __future__ import annotations
from typing import Optional
from datetime import date
from decimal import Decimal

from ..derivative import Derivative


class Future(Derivative):
    """
    Pure identification Future.
    Margin, daily settlement, and other metrics live elsewhere (factors).
    """
        
    def __init__(
            self,
            id: Optional[int],
            name: Optional[str],
            symbol: Optional[str],
            currency_id: Optional[int] = None,
            exchange_id: Optional[int] = None,
            underlying_asset_id: Optional[int] = None,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
            
        ):

        super().__init__(id=id, underlying_asset_id=underlying_asset_id, name=name, symbol=symbol, start_date=start_date, end_date=end_date)
        self.currency_id = currency_id
        self.exchange_id = exchange_id