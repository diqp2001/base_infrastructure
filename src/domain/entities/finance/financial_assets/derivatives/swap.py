"""
Swap classes for swap contracts.
Includes Interest Rate Swaps, Currency Swaps, and other swap instruments.
"""

from typing import Optional, List, Dict
from datetime import date
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

from .derivative import Derivative


class Swap(Derivative):
    """
    Base Swap entity.
    No leg notionals or rates (these go to a factor table).
    """
    def __init__(
            self,
            id: Optional[int],
            name: Optional[str],
            symbol: Optional[str],
            currency_id: Optional[int] = None,
            underlying_asset_id: Optional[int] = None,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
            
        ):

        super().__init__(id=id, name=name, symbol=symbol, underlying_asset_id=underlying_asset_id, start_date=start_date, end_date=end_date)
        self.currency_id = currency_id
    