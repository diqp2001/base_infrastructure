"""
Option classes for options contracts.
Includes base Option class and specialized types for different option strategies.
"""

from typing import Optional
from datetime import date
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

from src.domain.entities.finance.financial_assets.derivatives.option.option_type import OptionType
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset
from ..derivative import Derivative

from enum import Enum



class Option(Derivative):
    """
    Pure identification Option.
    Greeks, IV, moneyness, etc. live elsewhere (factors).
    """
    def __init__(
            self,
            id: Optional[int],
            name: Optional[str],
            symbol: Optional[str],
            underlying_asset: FinancialAsset,
            option_type: OptionType,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
            
        ):

        super().__init__(id =id,underlying_asset = underlying_asset, name=name, symbol=symbol, start_date=start_date, end_date=end_date)
    
    
        self.option_type = option_type
