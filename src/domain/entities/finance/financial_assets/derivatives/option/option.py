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
from ..derivative import Derivative, UnderlyingAsset

from enum import Enum



class Option(Derivative):
    """
    Pure identification Option.
    Greeks, IV, moneyness, etc. live elsewhere (factors).
    """

    def __init__(self,
                 id: int,
                 underlying_asset: FinancialAsset,
                 expiration_date: date,
                 option_type: OptionType,
                 start_date: date,
                 end_date: Optional[date] = None):
        
        super().__init__(id, underlying_asset, start_date, end_date)

        self.expiration_date = expiration_date
        self.option_type = option_type
